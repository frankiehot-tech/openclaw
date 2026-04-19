#!/usr/bin/env python3
"""
分析实验记录和成本记录的request_id格式
"""

import sqlite3
from datetime import datetime

DB_PATH = "/Volumes/1TB-M2/openclaw/mini-agent/data/cost_tracking.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=== 实验记录的request_id格式分析 ===")

    # 获取实验记录的request_id样本
    cursor.execute("""
        SELECT request_id, recorded_at, COUNT(*) as count
        FROM experiment_records
        WHERE experiment_id = 'coding_plan_deepseek_coder_ab'
        GROUP BY request_id
        ORDER BY recorded_at
        LIMIT 10
    """)

    print("实验记录request_id样本:")
    exp_requests = []
    for row in cursor.fetchall():
        request_id = row["request_id"]
        exp_requests.append(request_id)
        print(f"  - {request_id} (记录时间: {row['recorded_at']}, 出现次数: {row['count']})")

    # 分析实验记录request_id的模式
    if exp_requests:
        print(f"\n实验记录request_id模式分析:")
        print(f"  样本数量: {len(exp_requests)}")
        print(f"  前缀: {[r[:10] for r in exp_requests[:3]]}...")
        print(
            f"  长度范围: {min(len(r) for r in exp_requests)}-{max(len(r) for r in exp_requests)}"
        )

        # 检查是否包含特定模式
        patterns = ["exp_", "run_", "req_"]
        for pattern in patterns:
            count = sum(1 for r in exp_requests if pattern in r)
            print(f"  包含'{pattern}': {count}/{len(exp_requests)}")

    print("\n=== 成本记录的request_id格式分析 ===")

    # 获取成本记录的request_id样本
    cursor.execute("""
        SELECT request_id, timestamp, provider_id, COUNT(*) as count
        FROM cost_records
        GROUP BY request_id
        ORDER BY timestamp
        LIMIT 10
    """)

    print("成本记录request_id样本:")
    cost_requests = []
    for row in cursor.fetchall():
        request_id = row["request_id"]
        cost_requests.append(request_id)
        print(
            f"  - {request_id} (时间: {row['timestamp']}, provider: {row['provider_id']}, 次数: {row['count']})"
        )

    # 分析成本记录request_id的模式
    if cost_requests:
        print(f"\n成本记录request_id模式分析:")
        print(f"  样本数量: {len(cost_requests)}")
        print(f"  前缀: {[r[:10] for r in cost_requests[:3]]}...")
        print(
            f"  长度范围: {min(len(r) for r in cost_requests)}-{max(len(r) for r in cost_requests)}"
        )

        # 检查是否包含特定模式
        patterns = ["req_", "exp_", "run_"]
        for pattern in patterns:
            count = sum(1 for r in cost_requests if pattern in r)
            print(f"  包含'{pattern}': {count}/{len(cost_requests)}")

    print("\n=== 时间窗口对比 ===")

    # 查找同时间窗口内的记录
    cursor.execute("""
        SELECT
            MIN(e.recorded_at) as exp_min_time,
            MAX(e.recorded_at) as exp_max_time,
            MIN(c.timestamp) as cost_min_time,
            MAX(c.timestamp) as cost_max_time
        FROM experiment_records e, cost_records c
        WHERE e.experiment_id = 'coding_plan_deepseek_coder_ab'
    """)

    time_info = cursor.fetchone()
    print(f"实验记录时间范围: {time_info['exp_min_time']} 到 {time_info['exp_max_time']}")
    print(f"成本记录时间范围: {time_info['cost_min_time']} 到 {time_info['cost_max_time']}")

    # 检查是否有重叠的时间窗口
    exp_min = datetime.fromisoformat(time_info["exp_min_time"])
    exp_max = datetime.fromisoformat(time_info["exp_max_time"])
    cost_min = datetime.fromisoformat(time_info["cost_min_time"])
    cost_max = datetime.fromisoformat(time_info["cost_max_time"])

    if exp_min <= cost_max and exp_max >= cost_min:
        print("✅ 时间窗口有重叠")
    else:
        print("❌ 时间窗口没有重叠")

    print("\n=== 尝试直接关联测试 ===")

    # 尝试几种关联方法
    print("1. 直接request_id相等测试:")
    cursor.execute("""
        SELECT COUNT(*) as match_count
        FROM experiment_records e
        JOIN cost_records c ON e.request_id = c.request_id
        WHERE e.experiment_id = 'coding_plan_deepseek_coder_ab'
    """)
    direct_match = cursor.fetchone()
    print(f"   直接匹配数量: {direct_match['match_count']}")

    print("\n2. request_id部分匹配测试:")

    # 检查实验记录是否包含成本记录的request_id的一部分
    test_queries = [
        ("实验request_id包含成本request_id", "e.request_id LIKE '%' || c.request_id || '%'"),
        ("成本request_id包含实验request_id", "c.request_id LIKE '%' || e.request_id || '%'"),
        ("共享相同的时间戳部分", "e.request_id LIKE '%' || substr(c.request_id, -8) || '%'"),
    ]

    for desc, condition in test_queries:
        cursor.execute(f"""
            SELECT COUNT(DISTINCT e.id) as match_count
            FROM experiment_records e
            JOIN cost_records c ON {condition}
            WHERE e.experiment_id = 'coding_plan_deepseek_coder_ab'
        """)
        result = cursor.fetchone()
        print(f"   {desc}: {result['match_count']}")

    print("\n3. 按时间窗口和provider匹配:")

    # 检查同时间窗口内的成本记录
    cursor.execute("""
        SELECT
            e.group_name,
            COUNT(DISTINCT e.id) as exp_count,
            COUNT(DISTINCT c.id) as cost_count
        FROM experiment_records e
        LEFT JOIN cost_records c ON (
            c.timestamp BETWEEN datetime(e.recorded_at, '-5 minutes')
            AND datetime(e.recorded_at, '+5 minutes')
        )
        WHERE e.experiment_id = 'coding_plan_deepseek_coder_ab'
        GROUP BY e.group_name
    """)

    print("   5分钟时间窗口内的成本记录:")
    for row in cursor.fetchall():
        print(
            f"     分组 {row['group_name']}: {row['exp_count']} 个实验记录, {row['cost_count']} 个成本记录"
        )

    conn.close()


if __name__ == "__main__":
    main()
