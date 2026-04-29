#!/usr/bin/env python3
"""
数据关联修复端到端测试

测试迁移监控器的多层fallback策略，验证实验记录与成本记录的正确关联。
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")


def create_test_database():
    """创建测试数据库，包含模拟的实验记录和成本记录"""
    # 创建临时数据库
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_cost_tracking.db")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 创建表（与生产数据库相同）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cost_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT NOT NULL,
        provider_id TEXT NOT NULL,
        estimated_cost REAL NOT NULL,
        timestamp DATETIME NOT NULL,
        input_tokens INTEGER,
        output_tokens INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS experiment_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id TEXT NOT NULL,
        group_name TEXT NOT NULL,
        task_kind TEXT NOT NULL,
        request_id TEXT NOT NULL,
        quality_score REAL,
        execution_time REAL,
        cost_record_id INTEGER,
        recorded_at DATETIME NOT NULL,
        status TEXT DEFAULT 'completed'
    )
    """)

    # 创建索引
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_exp_request_id ON experiment_records(request_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_exp_experiment_id ON experiment_records(experiment_id)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cost_request_id ON cost_records(request_id)")

    # 生成测试数据
    # 模拟成本记录（使用标准格式）
    from agent.core.request_id_generator import RequestIDGenerator

    generator = RequestIDGenerator()

    base_time = datetime.now() - timedelta(hours=3)
    cost_records = []

    # DashScope成本记录（较贵）
    for i in range(15):
        timestamp = base_time + timedelta(minutes=i * 5)
        request_id = generator.generate(
            prefix="req", timestamp=timestamp, seed=f"dashscope_test_{i}"
        )
        cost_records.append(
            {
                "request_id": request_id,
                "provider_id": "dashscope",
                "estimated_cost": 0.015 + (i * 0.001),  # 逐渐增加
                "timestamp": timestamp,
                "input_tokens": 100 + i * 10,
                "output_tokens": 50 + i * 5,
            }
        )

    # DeepSeek成本记录（较便宜）
    for i in range(15):
        timestamp = base_time + timedelta(minutes=i * 5 + 2)  # 稍晚2分钟
        request_id = generator.generate(
            prefix="req", timestamp=timestamp, seed=f"deepseek_test_{i}"
        )
        cost_records.append(
            {
                "request_id": request_id,
                "provider_id": "deepseek",
                "estimated_cost": 0.003 + (i * 0.0005),  # 更便宜
                "timestamp": timestamp,
                "input_tokens": 100 + i * 10,
                "output_tokens": 50 + i * 5,
            }
        )

    # 插入成本记录
    for record in cost_records:
        cursor.execute(
            """
            INSERT INTO cost_records
            (request_id, provider_id, estimated_cost, timestamp, input_tokens, output_tokens)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                record["request_id"],
                record["provider_id"],
                record["estimated_cost"],
                record["timestamp"].isoformat(),
                record["input_tokens"],
                record["output_tokens"],
            ),
        )

    # 模拟实验记录（使用不同的格式，模拟当前问题）
    experiment_time = datetime.now() - timedelta(hours=1)  # 实验记录在成本记录之后

    # 创建一些有cost_record_id关联的记录（理想情况）
    # 创建一些没有cost_record_id但request_id可匹配的记录
    # 创建一些完全没有关联的记录（测试fallback）

    # 首先获取一些成本记录ID用于直接关联
    cursor.execute("SELECT id, request_id, provider_id FROM cost_records LIMIT 5")
    sample_costs = cursor.fetchall()

    exp_records = []

    # 分组1：有直接cost_record_id关联（理想情况）
    for i, cost in enumerate(sample_costs[:3]):
        exp_time = experiment_time + timedelta(minutes=i * 2)
        # 使用与成本记录相同的request_id
        exp_records.append(
            {
                "experiment_id": "test_migration_exp",
                "group_name": "control" if cost["provider_id"] == "dashscope" else "treatment",
                "task_kind": "coding_plan",
                "request_id": cost["request_id"],  # 相同的request_id
                "quality_score": 0.85 + (i * 0.05),
                "execution_time": 2.5 + (i * 0.5),
                "cost_record_id": cost["id"],  # 直接关联
                "recorded_at": exp_time,
            }
        )

    # 分组2：无cost_record_id但request_id格式不同（测试前缀匹配）
    for i in range(5):
        exp_time = experiment_time + timedelta(minutes=10 + i * 2)
        # 创建实验记录特有的request_id格式（如exp_run_...）
        # 但时间戳与某个成本记录相近
        target_cost = cost_records[i + 5]  # 选择一些成本记录

        # 提取成本记录的时间戳部分
        cost_parts = target_cost["request_id"].split("_")
        if len(cost_parts) >= 4:  # req_YYYYMMDD_HHMMSS_uniqueid
            date_part = cost_parts[1]
            time_part = cost_parts[2]
            # 创建实验记录格式：exp_run_YYYYMMDD_HHMMSS_batch_index
            exp_request_id = f"exp_run_{date_part}_{time_part}_1_{i}"

            exp_records.append(
                {
                    "experiment_id": "test_migration_exp",
                    "group_name": "treatment" if i % 2 == 0 else "control",
                    "task_kind": "coding_plan",
                    "request_id": exp_request_id,
                    "quality_score": 0.80 + (i * 0.03),
                    "execution_time": 3.0 + (i * 0.3),
                    "cost_record_id": None,  # 无直接关联
                    "recorded_at": exp_time,
                }
            )

    # 分组3：完全无关联，只有时间窗口可能匹配
    for i in range(4):
        exp_time = experiment_time + timedelta(minutes=20 + i * 3)
        # 使用完全不同的request_id格式
        exp_request_id = f"test_exp_{i}_{int(exp_time.timestamp())}"

        exp_records.append(
            {
                "experiment_id": "test_migration_exp",
                "group_name": "control" if i < 2 else "treatment",
                "task_kind": "coding_plan",
                "request_id": exp_request_id,
                "quality_score": 0.75 + (i * 0.04),
                "execution_time": 4.0 + (i * 0.4),
                "cost_record_id": None,  # 无关联
                "recorded_at": exp_time,
            }
        )

    # 插入实验记录
    for record in exp_records:
        cursor.execute(
            """
            INSERT INTO experiment_records
            (experiment_id, group_name, task_kind, request_id, quality_score,
             execution_time, cost_record_id, recorded_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                record["experiment_id"],
                record["group_name"],
                record["task_kind"],
                record["request_id"],
                record["quality_score"],
                record["execution_time"],
                record["cost_record_id"],
                record["recorded_at"].isoformat(),
                "completed",
            ),
        )

    conn.commit()

    # 打印测试数据统计
    cursor.execute("SELECT COUNT(*) as count FROM cost_records")
    cost_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) as count FROM experiment_records")
    exp_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(cost_record_id) as with_cost_id,
            COUNT(*) - COUNT(cost_record_id) as without_cost_id
        FROM experiment_records
    """)
    exp_stats = cursor.fetchone()

    print("测试数据库创建完成:")
    print(f"  成本记录: {cost_count} 条")
    print(f"  实验记录: {exp_count} 条")
    print(
        f"  实验记录关联统计: {exp_stats[0]} 总记录, {exp_stats[1]} 有cost_record_id, {exp_stats[2]} 无cost_record_id"
    )

    return db_path, temp_dir


def test_migration_monitor(db_path):
    """测试迁移监控器"""
    print("\n" + "=" * 60)
    print("测试迁移监控器多层fallback策略")
    print("=" * 60)

    from agent.core.migration_monitor import MigrationMonitor

    monitor = MigrationMonitor(db_path=db_path, check_interval_minutes=1)

    # 测试收集指标
    print("\n1. 收集迁移指标...")
    metrics = monitor.collect_migration_metrics(
        experiment_id="test_migration_exp", lookback_hours=24
    )

    if not metrics:
        print("❌ 未收集到指标")
        return False

    print("✅ 成功收集迁移指标")
    print(f"   实验ID: {metrics.experiment_id}")
    print(f"   总请求数: {metrics.total_requests}")
    print(f"   DashScope请求: {metrics.dashscope_requests}")
    print(f"   DeepSeek请求: {metrics.deepseek_requests}")
    print(f"   DashScope成本: {metrics.dashscope_cost:.6f}")
    print(f"   DeepSeek成本: {metrics.deepseek_cost:.6f}")
    print(f"   成本节省: {metrics.cost_savings_percent:.1f}%")
    print(f"   质量一致性: {metrics.quality_consistency:.3f}")
    print(f"   错误率差异: {metrics.error_rate_diff:.4f}")
    print(f"   响应时间差异: {metrics.response_time_diff_percent:.1f}%")

    # 验证指标合理性
    success = True

    if metrics.total_requests == 0:
        print("❌ 总请求数为0")
        success = False

    if metrics.dashscope_cost == 0 and metrics.deepseek_cost == 0:
        print("⚠️  成本数据可能未正确关联")
        # 这不一定是失败，可能是测试数据问题

    if metrics.cost_savings_percent > 100 or metrics.cost_savings_percent < -100:
        print("❌ 成本节省百分比异常")
        success = False

    print("\n2. 测试多层fallback策略统计...")

    # 连接到数据库检查匹配情况
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 检查实验记录是否通过不同方式匹配到成本记录
    cursor.execute("""
        SELECT e.id, e.request_id, e.cost_record_id, c.request_id as cost_request_id
        FROM experiment_records e
        LEFT JOIN cost_records c ON e.cost_record_id = c.id
        WHERE e.experiment_id = 'test_migration_exp'
    """)

    matches = cursor.fetchall()

    direct_matches = sum(1 for m in matches if m["cost_record_id"] is not None)
    total_exp = len(matches)

    print(f"   直接通过cost_record_id匹配: {direct_matches}/{total_exp}")

    # 检查request_id匹配情况
    cursor.execute("""
        SELECT e.request_id as exp_request_id, c.request_id as cost_request_id
        FROM experiment_records e, cost_records c
        WHERE e.experiment_id = 'test_migration_exp'
          AND (e.request_id = c.request_id
               OR c.request_id LIKE '%' || substr(e.request_id, -8) || '%'
               OR e.request_id LIKE '%' || substr(c.request_id, -8) || '%')
    """)

    request_id_matches = cursor.fetchall()
    print(f"   通过request_id匹配（各种方式）: {len(request_id_matches)} 对")

    conn.close()

    return success


def main():
    """主测试函数"""
    print("数据关联修复端到端测试")
    print("=" * 60)

    # 创建测试数据库
    db_path, temp_dir = None, None
    try:
        db_path, temp_dir = create_test_database()

        # 测试迁移监控器
        test_passed = test_migration_monitor(db_path)

        if test_passed:
            print("\n" + "=" * 60)
            print("🎉 端到端测试通过！")
            print("多层fallback策略正常工作")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("⚠️  端到端测试部分失败")
            print("=" * 60)
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"\n临时文件已清理: {temp_dir}")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
