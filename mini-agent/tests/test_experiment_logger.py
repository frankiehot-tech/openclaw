#!/usr/bin/env python3
"""
实验日志记录器测试

验证experiment_logger.py的功能：
1. 实验分配记录
2. 实验执行记录
3. 实验质量记录
4. 数据存储和查询
5. 实验摘要统计
"""

import json
import os
import sqlite3
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
project_root = "/Volumes/1TB-M2/openclaw"
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "mini-agent"))

from agent.core.experiment_logger import (
    ExperimentDataQuality,
    ExperimentLogger,
    ExperimentRecord,
    ExperimentRecordStatus,
    SQLiteExperimentStorageBackend,
    get_experiment_logger,
)


def test_sqlite_storage_backend():
    """测试SQLite存储后端"""
    print("🧪 测试SQLite存储后端...")

    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # 初始化存储后端
        storage = SQLiteExperimentStorageBackend(db_path=db_path)

        # 创建实验记录
        record = ExperimentRecord(
            id="test_record_001",
            experiment_id="test_experiment_001",
            request_id="test_request_001",
            cost_record_id=None,
            group_name="control",
            assignment_metadata={
                "experiment_id": "test_experiment_001",
                "group_name": "control",
                "assigned_at": datetime.now().isoformat(),
            },
            task_kind="coding_plan",
            input_prompt="def hello():\n    print('Hello, World!')",
            output_response="def hello():\n    print('Hello, World!')\n\n# 这是一个简单的测试函数",
            input_summary="def hello():...",
            output_summary="def hello():...",
            execution_time=1.23,
            tokens_used={"input": 10, "output": 20},
            cost_info={"estimated_cost": 0.0001, "currency": "CNY"},
            quality_score=8.5,
            quality_breakdown={"correctness": 9.0, "style": 8.0},
            quality_assessor="auto",
            status=ExperimentRecordStatus.COMPLETED.value,
            data_quality=ExperimentDataQuality.COMPLETE.value,
            metadata={"test": True},
        )

        # 测试记录保存
        success = storage.record_experiment(record)
        assert success, "记录保存失败"
        print("  ✅ 记录保存成功")

        # 测试记录查询
        records = storage.get_experiment_records(experiment_id="test_experiment_001")
        assert len(records) == 1, f"期望1条记录，实际{len(records)}条"
        retrieved = records[0]
        assert retrieved.id == record.id, f"ID不匹配: {retrieved.id} != {record.id}"
        print("  ✅ 记录查询成功")

        # 测试实验摘要
        summary = storage.get_experiment_summary("test_experiment_001")
        assert summary is not None, "实验摘要为空"
        assert summary.experiment_id == "test_experiment_001"
        assert summary.total_samples == 1
        assert "control" in summary.group_samples
        assert summary.group_samples["control"] == 1
        print("  ✅ 实验摘要生成成功")

        # 测试数据质量过滤
        partial_records = storage.get_experiment_records(min_data_quality="partial")
        assert len(partial_records) >= 1, "应至少返回部分数据质量的记录"

        # 测试清理功能（不实际删除，只验证调用）
        deleted = storage.cleanup(days_to_keep=1)
        assert isinstance(deleted, int), f"清理返回类型错误: {type(deleted)}"
        print("  ✅ 清理功能正常")

        print("  ✅ SQLite存储后端测试通过")
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


def test_experiment_logger_basic():
    """测试实验记录器基本功能"""
    print("\n🧪 测试实验记录器基本功能...")

    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # 创建存储后端
        storage = SQLiteExperimentStorageBackend(db_path=db_path)
        logger = ExperimentLogger(storage_backend=storage)

        # 测试1: 记录实验分配
        request_id = "test_request_002"
        assignment_metadata = {
            "experiment_id": "coding_plan_deepseek_coder_ab",
            "group_name": "treatment",
            "provider": "deepseek",
            "model": "deepseek-coder",
            "assigned_at": datetime.now().isoformat(),
        }
        input_context = {"prompt": "编写一个Python函数计算斐波那契数列", "task_kind": "coding_plan"}

        record_id = logger.log_experiment_assignment(
            task_kind="coding_plan",
            request_id=request_id,
            assignment_metadata=assignment_metadata,
            input_context=input_context,
        )

        assert record_id is not None, "实验分配记录失败"
        assert record_id.startswith("exp_"), f"记录ID格式错误: {record_id}"
        print("  ✅ 实验分配记录成功")

        # 验证记录已创建
        records = logger.storage.get_experiment_records(request_id=request_id, limit=1)
        assert len(records) == 1, "未找到实验记录"
        record = records[0]
        assert record.experiment_id == "coding_plan_deepseek_coder_ab"
        assert record.group_name == "treatment"
        assert record.status == ExperimentRecordStatus.ASSIGNED.value
        print("  ✅ 实验记录验证成功")

        # 测试2: 记录实验执行
        execution_result = {
            "output_response": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
            "execution_time": 2.5,
            "tokens_used": {"input": 15, "output": 30},
            "cost_info": {"estimated_cost": 0.00005, "currency": "CNY", "provider": "deepseek"},
            "metadata": {"execution_timestamp": datetime.now().isoformat()},
        }

        success = logger.log_experiment_execution(
            request_id=request_id,
            execution_result=execution_result,
            cost_record_id="cost_record_001",
        )

        assert success, "实验执行记录失败"
        print("  ✅ 实验执行记录成功")

        # 验证执行记录
        records = logger.storage.get_experiment_records(request_id=request_id, limit=1)
        record = records[0]
        assert record.output_response is not None
        assert record.execution_time == 2.5
        assert record.cost_record_id == "cost_record_001"
        assert record.status == ExperimentRecordStatus.EXECUTED.value
        print("  ✅ 执行记录验证成功")

        # 测试3: 记录实验质量
        quality_assessment = {
            "quality_score": 9.0,
            "quality_breakdown": {
                "correctness": 9.5,
                "efficiency": 8.0,
                "style": 9.0,
                "documentation": 8.5,
            },
            "quality_assessor": "auto",
            "metadata": {"assessed_at": datetime.now().isoformat()},
        }

        success = logger.log_experiment_quality(
            request_id=request_id, quality_assessment=quality_assessment
        )

        assert success, "实验质量记录失败"
        print("  ✅ 实验质量记录成功")

        # 验证质量记录
        records = logger.storage.get_experiment_records(request_id=request_id, limit=1)
        record = records[0]
        assert record.quality_score == 9.0
        assert record.quality_assessor == "auto"
        assert record.status == ExperimentRecordStatus.EVALUATED.value
        print("  ✅ 质量记录验证成功")

        # 测试4: 标记实验完成
        success = logger.complete_experiment(request_id)
        assert success, "实验完成标记失败"
        print("  ✅ 实验完成标记成功")

        # 验证完成状态
        records = logger.storage.get_experiment_records(request_id=request_id, limit=1)
        record = records[0]
        assert record.status == ExperimentRecordStatus.COMPLETED.value
        print("  ✅ 完成状态验证成功")

        # 测试5: 获取实验状态报告
        status_report = logger.get_experiment_status("coding_plan_deepseek_coder_ab")
        assert status_report is not None
        assert "experiment_id" in status_report
        assert status_report["experiment_id"] == "coding_plan_deepseek_coder_ab"
        assert "total_samples" in status_report
        assert "recommendations" in status_report
        print("  ✅ 实验状态报告生成成功")

        print("  ✅ 实验记录器基本功能测试通过")
        return True

    except Exception as e:
        print(f"  ❌ 实验记录器基本功能测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_data_quality_calculation():
    """测试数据质量等级计算"""
    print("\n🧪 测试数据质量等级计算...")

    try:
        # 测试1: 完整数据
        record_complete = ExperimentRecord(
            id="test_complete",
            experiment_id="test_exp",
            request_id="test_req_001",
            group_name="control",
            assignment_metadata={},
            task_kind="coding_plan",
            input_prompt="test",
            output_response="test",
            execution_time=1.0,
            tokens_used={"input": 10, "output": 20},
            cost_info={"estimated_cost": 0.0001},
            quality_score=8.0,
            status=ExperimentRecordStatus.CREATED.value,
            data_quality=ExperimentDataQuality.MINIMAL.value,
        )

        quality_complete = record_complete.calculate_data_quality()
        assert (
            quality_complete == ExperimentDataQuality.COMPLETE.value
        ), f"完整数据质量应为complete，实际为{quality_complete}"
        print("  ✅ 完整数据质量计算正确")

        # 测试2: 部分数据（缺少质量评分）
        record_partial = ExperimentRecord(
            id="test_partial",
            experiment_id="test_exp",
            request_id="test_req_002",
            group_name="treatment",
            assignment_metadata={},
            task_kind="coding_plan",
            input_prompt="test",
            output_response="test",
            execution_time=1.0,
            tokens_used={"input": 10, "output": 20},
            cost_info={"estimated_cost": 0.0001},
            quality_score=None,  # 缺少质量评分
            status=ExperimentRecordStatus.CREATED.value,
            data_quality=ExperimentDataQuality.MINIMAL.value,
        )

        quality_partial = record_partial.calculate_data_quality()
        assert (
            quality_partial == ExperimentDataQuality.PARTIAL.value
        ), f"部分数据质量应为partial，实际为{quality_partial}"
        print("  ✅ 部分数据质量计算正确")

        # 测试3: 最小数据（仅有成本信息）
        record_minimal = ExperimentRecord(
            id="test_minimal",
            experiment_id="test_exp",
            request_id="test_req_003",
            group_name="control",
            assignment_metadata={},
            task_kind="coding_plan",
            input_prompt=None,
            output_response=None,
            execution_time=None,
            tokens_used=None,
            cost_info={"estimated_cost": 0.0001},  # 仅有成本信息
            quality_score=None,
            status=ExperimentRecordStatus.CREATED.value,
            data_quality=ExperimentDataQuality.MINIMAL.value,
        )

        quality_minimal = record_minimal.calculate_data_quality()
        assert (
            quality_minimal == ExperimentDataQuality.MINIMAL.value
        ), f"最小数据质量应为minimal，实际为{quality_minimal}"
        print("  ✅ 最小数据质量计算正确")

        # 测试4: 不完整数据（缺少关键信息）
        record_incomplete = ExperimentRecord(
            id="test_incomplete",
            experiment_id="test_exp",
            request_id="test_req_004",
            group_name="treatment",
            assignment_metadata={},
            task_kind="coding_plan",
            input_prompt=None,
            output_response=None,
            execution_time=None,
            tokens_used=None,
            cost_info=None,  # 缺少成本信息
            quality_score=None,
            status=ExperimentRecordStatus.CREATED.value,
            data_quality=ExperimentDataQuality.MINIMAL.value,
        )

        quality_incomplete = record_incomplete.calculate_data_quality()
        assert (
            quality_incomplete == ExperimentDataQuality.INCOMPLETE.value
        ), f"不完整数据质量应为incomplete，实际为{quality_incomplete}"
        print("  ✅ 不完整数据质量计算正确")

        print("  ✅ 数据质量等级计算测试通过")
        return True

    except Exception as e:
        print(f"  ❌ 数据质量等级计算测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_experiment_summary_statistics():
    """测试实验摘要统计"""
    print("\n🧪 测试实验摘要统计...")

    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        storage = SQLiteExperimentStorageBackend(db_path=db_path)

        # 创建多个实验记录（控制组和实验组）
        test_records = [
            {
                "id": f"test_summary_{i:03d}",
                "experiment_id": "test_summary_exp",
                "request_id": f"test_req_{i:03d}",
                "group_name": "control" if i % 2 == 0 else "treatment",
                "assignment_metadata": {},
                "task_kind": "coding_plan",
                "input_prompt": f"测试输入 {i}",
                "output_response": f"测试输出 {i}",
                "execution_time": 1.0 + (i * 0.1),
                "tokens_used": {"input": 10 + i, "output": 20 + i},
                "cost_info": {
                    "estimated_cost": 0.0001 * (1.0 if i % 2 == 0 else 0.6)
                },  # 实验组成本更低
                "quality_score": 8.0 + (i * 0.1),
                "status": ExperimentRecordStatus.COMPLETED.value,
                "data_quality": ExperimentDataQuality.COMPLETE.value,
                "recorded_at": datetime.now() - timedelta(days=i),
            }
            for i in range(10)  # 10个样本
        ]

        # 保存所有记录
        for record_data in test_records:
            record = ExperimentRecord(**record_data)
            storage.record_experiment(record)

        # 获取实验摘要
        summary = storage.get_experiment_summary("test_summary_exp")

        assert summary is not None, "实验摘要为空"
        assert summary.experiment_id == "test_summary_exp"
        assert summary.total_samples == 10, f"期望10个样本，实际{summary.total_samples}"
        assert "control" in summary.group_samples, "缺少control组"
        assert "treatment" in summary.group_samples, "缺少treatment组"
        assert (
            summary.group_samples["control"] == 5
        ), f"control组应有5个样本，实际{summary.group_samples['control']}"
        assert (
            summary.group_samples["treatment"] == 5
        ), f"treatment组应有5个样本，实际{summary.group_samples['treatment']}"

        print("  ✅ 样本统计正确")

        # 验证成本统计
        assert "control" in summary.avg_cost_by_group
        assert "treatment" in summary.avg_cost_by_group
        assert summary.avg_cost_by_group["control"] > 0
        assert summary.avg_cost_by_group["treatment"] > 0
        assert (
            summary.avg_cost_by_group["treatment"] < summary.avg_cost_by_group["control"]
        ), f"实验组成本应低于控制组: {summary.avg_cost_by_group}"

        print("  ✅ 成本统计正确")

        # 验证成本节省百分比
        assert summary.cost_savings_percentage is not None
        assert (
            summary.cost_savings_percentage > 0
        ), f"成本节省应为正数，实际{summary.cost_savings_percentage}"
        print(f"    成本节省百分比: {summary.cost_savings_percentage:.1f}%")

        # 验证质量统计
        assert "control" in summary.avg_quality_by_group
        assert "treatment" in summary.avg_quality_by_group
        print(f"    控制组平均质量: {summary.avg_quality_by_group['control']:.1f}")
        print(f"    实验组平均质量: {summary.avg_quality_by_group['treatment']:.1f}")

        # 验证数据质量分布
        assert summary.data_quality_distribution is not None
        assert "complete" in summary.data_quality_distribution
        assert (
            summary.data_quality_distribution["complete"] == 10
        ), f"所有样本应为complete质量，实际{summary.data_quality_distribution}"

        print("  ✅ 数据质量分布正确")

        print("  ✅ 实验摘要统计测试通过")
        return True

    except Exception as e:
        print(f"  ❌ 实验摘要统计测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_global_logger_instance():
    """测试全局日志记录器实例"""
    print("\n🧪 测试全局日志记录器实例...")

    try:
        # 获取全局实例
        logger1 = get_experiment_logger()
        logger2 = get_experiment_logger()

        # 验证是同一个实例
        assert logger1 is logger2, "全局实例应为单例"
        print("  ✅ 全局单例模式正确")

        # 验证实例类型
        assert isinstance(logger1, ExperimentLogger), f"实例类型错误: {type(logger1)}"
        print("  ✅ 实例类型正确")

        # 验证存储后端
        assert logger1.storage is not None, "存储后端为空"
        assert isinstance(
            logger1.storage, SQLiteExperimentStorageBackend
        ), f"存储后端类型错误: {type(logger1.storage)}"
        print("  ✅ 存储后端配置正确")

        print("  ✅ 全局日志记录器实例测试通过")
        return True

    except Exception as e:
        print(f"  ❌ 全局日志记录器实例测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🔍 实验日志记录器测试套件")
    print("=" * 60)

    test_results = []

    # 运行所有测试
    test_results.append(("SQLite存储后端", test_sqlite_storage_backend()))
    test_results.append(("实验记录器基本功能", test_experiment_logger_basic()))
    test_results.append(("数据质量等级计算", test_data_quality_calculation()))
    test_results.append(("实验摘要统计", test_experiment_summary_statistics()))
    test_results.append(("全局日志记录器实例", test_global_logger_instance()))

    # 打印测试结果摘要
    print("\n" + "=" * 60)
    print("📋 测试结果摘要:")

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")

    print(f"\n   总体: {passed}/{total} 个测试通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过！实验日志记录器功能正常。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查问题。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
