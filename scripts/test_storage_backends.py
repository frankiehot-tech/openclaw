#!/usr/bin/env python3
"""
测试成本跟踪存储后端

验证所有存储后端实现：
1. SQLite存储后端
2. JSON文件存储后端
3. 内存存储后端

确保它们都正确实现StorageBackend接口，并能与CostTracker集成。
"""

import os
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta

# 添加mini-agent到路径
sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")

from agent.core.cost_tracker import (
    CostRecord,
    CostRecordStatus,
    CostSummary,
    CostTracker,
    SQLiteStorageBackend,
    StorageBackend,
)
from agent.core.cost_tracker_json_storage import JSONStorageBackend
from agent.core.cost_tracker_memory_storage import MemoryStorageBackend


def test_sqlite_backend():
    """测试SQLite存储后端"""
    print("🧪 测试SQLite存储后端...")

    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # 创建后端实例
        backend = SQLiteStorageBackend(db_path=db_path)

        # 测试初始化
        assert backend.conn is not None
        print("  ✅ 数据库连接成功")

        # 创建测试记录
        test_record = CostRecord(
            id="test_sqlite_001",
            request_id="req_test_001",
            timestamp=datetime.now(),
            recorded_at=datetime.now(),
            provider_id="deepseek",
            model_id="deepseek-chat",
            task_kind="testing",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.0015,
            estimated_tokens=False,
            actual_cost=None,
            cost_mode="estimated",
            status=CostRecordStatus.RECORDED.value,
            metadata={"test": "sqlite_backend"},
        )

        # 测试记录成本
        success = backend.record_cost(test_record)
        assert success
        print("  ✅ 记录成本成功")

        # 测试查询记录
        records = backend.get_records(limit=10)
        assert len(records) == 1
        assert records[0].id == "test_sqlite_001"
        print(f"  ✅ 查询记录成功: 找到 {len(records)} 条记录")

        # 测试查询摘要
        summary = backend.get_summary()
        assert isinstance(summary, CostSummary)
        print(f"  ✅ 查询摘要成功: 总成本 ${summary.total_cost:.6f}")

        # 测试清理（保留所有数据）
        backend.cleanup(days_to_keep=0)  # 不清理任何数据
        print("  ✅ 清理操作成功")

        print("✅ SQLite存储后端测试通过")
        return True

    except Exception as e:
        print(f"  ❌ SQLite存储后端测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_json_backend():
    """测试JSON存储后端"""
    print("\n🧪 测试JSON存储后端...")

    # 创建临时JSON文件
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        json_path = tmp.name

    try:
        # 创建后端实例
        backend = JSONStorageBackend(file_path=json_path, compress=False)

        # 测试初始化
        assert hasattr(backend, "file_path")
        print("  ✅ JSON文件初始化成功")

        # 创建测试记录
        test_record = CostRecord(
            id="test_json_001",
            request_id="req_test_002",
            timestamp=datetime.now(),
            recorded_at=datetime.now(),
            provider_id="dashscope",
            model_id="qwen3.5-plus",
            task_kind="testing",
            input_tokens=200,
            output_tokens=100,
            estimated_cost=0.0030,
            estimated_tokens=True,
            actual_cost=None,
            cost_mode="estimated",
            status=CostRecordStatus.ESTIMATED.value,
            metadata={"test": "json_backend"},
        )

        # 测试记录成本
        success = backend.record_cost(test_record)
        assert success
        print("  ✅ 记录成本成功")

        # 测试查询记录
        records = backend.get_records(limit=10)
        assert len(records) == 1
        assert records[0].id == "test_json_001"
        print(f"  ✅ 查询记录成功: 找到 {len(records)} 条记录")

        # 测试查询摘要
        summary = backend.get_summary()
        assert isinstance(summary, CostSummary)
        print(f"  ✅ 查询摘要成功: 总成本 ${summary.total_cost:.6f}")

        # 测试数据持久化
        backend2 = JSONStorageBackend(file_path=json_path, compress=False)
        records2 = backend2.get_records(limit=10)
        assert len(records2) == 1
        print("  ✅ 数据持久化验证成功")

        print("✅ JSON存储后端测试通过")
        return True

    except Exception as e:
        print(f"  ❌ JSON存储后端测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        if os.path.exists(json_path):
            os.unlink(json_path)
        # 清理备份目录
        backup_dir = os.path.join(os.path.dirname(json_path), "backups")
        if os.path.exists(backup_dir):
            import shutil

            shutil.rmtree(backup_dir, ignore_errors=True)


def test_memory_backend():
    """测试内存存储后端"""
    print("\n🧪 测试内存存储后端...")

    try:
        # 创建后端实例
        backend = MemoryStorageBackend()

        # 测试初始化
        assert hasattr(backend, "max_records")
        print("  ✅ 内存存储初始化成功")

        # 创建测试记录
        test_record = CostRecord(
            id="test_memory_001",
            request_id="req_test_003",
            timestamp=datetime.now(),
            recorded_at=datetime.now(),
            provider_id="deepseek",
            model_id="deepseek-chat",
            task_kind="testing",
            input_tokens=150,
            output_tokens=75,
            estimated_cost=0.00225,
            estimated_tokens=False,
            actual_cost=0.0020,
            cost_mode="verified",
            status=CostRecordStatus.VERIFIED.value,
            metadata={"test": "memory_backend"},
        )

        # 测试记录成本
        success = backend.record_cost(test_record)
        assert success
        print("  ✅ 记录成本成功")

        # 测试查询记录
        records = backend.get_records(limit=10)
        assert len(records) == 1
        assert records[0].id == "test_memory_001"
        print(f"  ✅ 查询记录成功: 找到 {len(records)} 条记录")

        # 测试查询摘要
        summary = backend.get_summary()
        assert isinstance(summary, CostSummary)
        print(f"  ✅ 查询摘要成功: 总成本 ${summary.total_cost:.6f}")

        # 测试清理
        backend.cleanup(days_to_keep=0)  # 不清理任何数据
        print("  ✅ 清理操作成功")

        print("✅ 内存存储后端测试通过")
        return True

    except Exception as e:
        print(f"  ❌ 内存存储后端测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cost_tracker_integration():
    """测试CostTracker与不同存储后端的集成"""
    print("\n🧪 测试CostTracker集成...")

    try:
        # 测试SQLite后端
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        tracker_sqlite = CostTracker(storage_backend="sqlite", config={"db_path": db_path})

        # 记录请求
        record_id = tracker_sqlite.record_request(
            request_id="req_integration_001",
            provider_id="deepseek",
            model_id="deepseek-chat",
            task_kind="integration_test",
            input_tokens=120,
            output_tokens=60,
            estimated_tokens=False,
            metadata={"test": "integration"},
        )

        assert record_id is not None
        print(f"  ✅ CostTracker SQLite集成: 记录ID {record_id}")

        # 清理
        tracker_sqlite.storage.cleanup(days_to_keep=0)

        # 测试内存后端
        tracker_memory = CostTracker(storage_backend="memory")

        record_id2 = tracker_memory.record_request(
            request_id="req_integration_002",
            provider_id="dashscope",
            model_id="qwen3.5-plus",
            task_kind="integration_test",
            input_tokens=180,
            output_tokens=90,
            estimated_tokens=True,
        )

        assert record_id2 is not None
        print(f"  ✅ CostTracker 内存集成: 记录ID {record_id2}")

        # 获取记录
        records = tracker_memory.storage.get_records(limit=5)
        assert len(records) >= 1
        print(f"  ✅ 内存后端记录查询: {len(records)} 条记录")

        print("✅ CostTracker集成测试通过")

        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)

        return True

    except Exception as e:
        print(f"  ❌ CostTracker集成测试失败: {e}")
        import traceback

        traceback.print_exc()

        # 清理临时文件
        if "db_path" in locals() and os.path.exists(db_path):
            os.unlink(db_path)

        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("🏗️  成本跟踪存储后端测试")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("SQLite存储后端", test_sqlite_backend()))
    results.append(("JSON存储后端", test_json_backend()))
    results.append(("内存存储后端", test_memory_backend()))
    results.append(("CostTracker集成", test_cost_tracker_integration()))

    # 输出总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有存储后端测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查实现")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生未预期错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
