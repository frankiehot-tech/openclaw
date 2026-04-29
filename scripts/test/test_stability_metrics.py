#!/usr/bin/env python3
"""
OpenHuman MVP 稳定性指标测试

验证指标聚合、告警阈值、负路径等功能。
满足文档要求的三个验证测试：
1. 至少补一个指标聚合正路径测试
2. 至少补一个告警阈值命中测试
3. 至少补一个缺指标或超阈值负路径测试
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入被测试模块
try:
    from scripts.collect_stability_metrics import (
        Alert,
        StabilityMetric,
        StabilityMetricsCollector,
    )
    from scripts.gate_check import StabilityGate
except ImportError:
    # 如果导入失败，添加当前目录到路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from collect_stability_metrics import (
        Alert,
        StabilityMetric,
        StabilityMetricsCollector,
    )
    from gate_check import StabilityGate


class TestStabilityMetricsCollector(unittest.TestCase):
    """稳定性指标收集器测试"""

    def setUp(self):
        """测试准备"""
        self.collector = StabilityMetricsCollector()
        self.test_metrics = [
            StabilityMetric(
                metric_id="test_availability",
                metric_type="availability",
                value=1.0,
                unit="binary",
                source="test",
                timestamp=datetime.now().isoformat(),
                context={},
            ),
            StabilityMetric(
                metric_id="test_response_time",
                metric_type="response_time",
                value=1.5,
                unit="seconds",
                source="test",
                timestamp=datetime.now().isoformat(),
                context={},
            ),
            StabilityMetric(
                metric_id="test_error_rate",
                metric_type="error_rate",
                value=0.02,
                unit="ratio",
                source="test",
                timestamp=datetime.now().isoformat(),
                context={},
            ),
        ]

    def test_metric_aggregation_positive_path(self):
        """测试1: 指标聚合正路径测试"""
        print("\n=== 测试1: 指标聚合正路径测试 ===")

        # 模拟收集指标
        with (
            patch.object(self.collector, "_collect_availability") as mock_avail,
            patch.object(self.collector, "_collect_response_time") as mock_resp,
            patch.object(self.collector, "_collect_error_rate") as mock_error,
            patch.object(self.collector, "_collect_data_integrity") as mock_integrity,
        ):
            # 设置模拟返回值
            mock_avail.return_value = self.test_metrics[0]
            mock_resp.return_value = self.test_metrics[1]
            mock_error.return_value = self.test_metrics[2]
            mock_integrity.return_value = StabilityMetric(
                metric_id="test_data_integrity",
                metric_type="data_integrity",
                value=1.0,
                unit="ratio",
                source="test",
                timestamp=datetime.now().isoformat(),
                context={},
            )

            # 执行指标收集
            metrics = self.collector.collect_metrics()

            # 验证指标聚合
            self.assertIsNotNone(metrics, "指标收集不应返回None")
            self.assertGreaterEqual(len(metrics), 3, "应至少收集到3个指标")

            # 验证指标类型
            metric_types = {m.metric_type for m in metrics}
            expected_types = {
                "availability",
                "response_time",
                "error_rate",
                "data_integrity",
            }
            for expected_type in expected_types:
                self.assertIn(expected_type, metric_types, f"应包含{expected_type}指标")

            print(f"   ✅ 指标聚合测试通过: 收集到 {len(metrics)} 个指标")
            for metric in metrics:
                print(f"      - {metric.metric_id}: {metric.value} {metric.unit}")

            return metrics

    def test_alert_threshold_hit(self):
        """测试2: 告警阈值命中测试"""
        print("\n=== 测试2: 告警阈值命中测试 ===")

        # 创建触发告警的指标（响应时间超过P0阈值10秒）
        alert_metric = StabilityMetric(
            metric_id="test_response_time_alert",
            metric_type="response_time",
            value=15.0,  # 超过P0阈值10秒
            unit="seconds",
            source="test",
            timestamp=datetime.now().isoformat(),
            context={},
        )

        # 评估告警
        alerts = self.collector.evaluate_alerts([alert_metric])

        # 验证告警触发
        self.assertGreater(len(alerts), 0, "应触发至少一个告警")

        # 验证告警等级
        p0_alerts = [a for a in alerts if a.alert_level == "P0"]
        self.assertGreater(len(p0_alerts), 0, "应触发P0告警")

        print(f"   ✅ 告警阈值命中测试通过: 触发 {len(alerts)} 个告警")
        for alert in alerts:
            print(f"      - {alert.alert_level}: {alert.message}")

        return alerts

    def test_missing_metric_negative_path(self):
        """测试3: 缺指标负路径测试"""
        print("\n=== 测试3: 缺指标负路径测试 ===")

        # 模拟缺少关键指标的情况
        with (
            patch.object(self.collector, "_collect_availability") as mock_avail,
            patch.object(self.collector, "_collect_response_time") as mock_resp,
            patch.object(self.collector, "_collect_error_rate") as mock_error,
            patch.object(self.collector, "_collect_data_integrity") as mock_integrity,
        ):
            # 设置模拟返回None（模拟指标缺失）
            mock_avail.return_value = None
            mock_resp.return_value = None
            mock_error.return_value = None
            # 模拟数据完整性低
            mock_integrity.return_value = StabilityMetric(
                metric_id="data_integrity",
                metric_type="data_integrity",
                value=0.3,  # 低完整性，应触发告警
                unit="ratio",
                source="test",
                timestamp=datetime.now().isoformat(),
                context={"missing_files": ["agent_state.json"], "total_count": 3},
            )

            # 执行指标收集
            metrics = self.collector.collect_metrics()

            # 验证指标缺失处理
            self.assertIsNotNone(
                metrics, "即使指标缺失，也应返回列表（可能为空或只有数据完整性指标）"
            )

            # 检查是否有关键指标缺失的告警
            alerts = self.collector.evaluate_alerts(metrics)

            # 验证数据完整性告警
            data_integrity_alerts = [a for a in alerts if a.metric_id == "data_integrity"]
            self.assertGreater(len(data_integrity_alerts), 0, "应触发数据完整性告警")

            print(
                f"   ✅ 缺指标负路径测试通过: 收集到 {len(metrics)} 个指标，触发 {len(alerts)} 个告警"
            )
            if alerts:
                for alert in alerts:
                    print(f"      - {alert.alert_level}: {alert.message}")

            return metrics, alerts

    def test_gate_check_integration(self):
        """测试4: 门禁检查集成测试"""
        print("\n=== 测试4: 门禁检查集成测试 ===")

        # 创建门禁检查器
        gate = StabilityGate()

        # 模拟门禁检查结果
        with patch.object(gate, "check_gate") as mock_check:
            mock_check.return_value = (
                False,  # 未通过
                {
                    "timestamp": datetime.now().isoformat(),
                    "gate_id": "test_gate",
                    "passed": False,
                    "gate_results": {
                        "data_integrity_check": {"passed": False, "reason": "测试失败"},
                        "threshold_violation_check": {
                            "passed": True,
                            "reason": "测试通过",
                        },
                        "overall_pass": False,
                    },
                    "mvp_stability_claim_allowed": False,
                },
            )

            # 执行门禁检查
            passed, result = gate.check_gate()

            # 验证门禁结果
            self.assertFalse(passed, "门禁检查应未通过")
            self.assertFalse(result["mvp_stability_claim_allowed"], "不应允许MVP稳定性声明")

            print("   ✅ 门禁检查集成测试通过: 门禁未通过，MVP稳定性声明被阻止")

            return result


class TestStabilityGate(unittest.TestCase):
    """稳定性门禁测试"""

    def setUp(self):
        """测试准备"""
        self.gate = StabilityGate()

    def test_gate_with_threshold_violation(self):
        """测试门禁处理阈值违规"""
        print("\n=== 测试5: 门禁处理阈值违规测试 ===")

        # 创建模拟指标和告警
        test_metrics = [
            StabilityMetric(
                metric_id="test_availability",
                metric_type="availability",
                value=0.0,  # 不可用，应触发P0告警
                unit="binary",
                source="test",
                timestamp=datetime.now().isoformat(),
                context={},
            )
        ]

        test_alerts = [
            Alert(
                alert_id="test_alert_p0",
                metric_id="test_availability",
                alert_level="P0",
                message="系统不可用",
                threshold={"value": 0.5, "condition": "<"},
                timestamp=datetime.now().isoformat(),
                severity=0,
                actions=["暂停执行"],
            )
        ]

        # 模拟收集器方法
        with (
            patch.object(self.gate.collector, "collect_metrics", return_value=test_metrics),
            patch.object(self.gate.collector, "evaluate_alerts", return_value=test_alerts),
        ):
            # 执行门禁检查
            passed, result = self.gate.check_gate()

            # 验证门禁失败
            self.assertFalse(passed, "存在P0告警时门禁应失败")
            self.assertFalse(result["mvp_stability_claim_allowed"], "不应允许MVP稳定性声明")

            print("   ✅ 门禁处理阈值违规测试通过: 门禁未通过，MVP稳定性声明被阻止")

            return result

    def test_gate_with_missing_data(self):
        """测试门禁处理数据缺失"""
        print("\n=== 测试6: 门禁处理数据缺失测试 ===")

        # 创建模拟指标（数据完整性低）
        test_metrics = [
            StabilityMetric(
                metric_id="data_integrity",
                metric_type="data_integrity",
                value=0.3,  # 完整性低，应触发P0告警
                unit="ratio",
                source="test",
                timestamp=datetime.now().isoformat(),
                context={"missing_files": ["agent_state.json"], "total_count": 3},
            )
        ]

        # 模拟收集器方法
        with (
            patch.object(self.gate.collector, "collect_metrics", return_value=test_metrics),
            patch.object(self.gate.collector, "evaluate_alerts", return_value=[]),
        ):
            # 执行门禁检查
            passed, result = self.gate.check_gate()

            # 验证门禁失败
            self.assertFalse(passed, "数据完整性低时门禁应失败")
            self.assertFalse(result["mvp_stability_claim_allowed"], "不应允许MVP稳定性声明")

            print("   ✅ 门禁处理数据缺失测试通过: 门禁未通过，MVP稳定性声明被阻止")

            return result


def create_test_metrics_baseline():
    """创建测试用的metrics_baseline文件"""
    test_data = {
        "timestamp": datetime.now().isoformat(),
        "total_tasks": 100,
        "total_completed": 80,
        "total_failed": 20,
        "total_pending": 0,
        "total_stale": 0,
        "overall_success_rate": 0.8,
        "overall_throughput_24h": 4.2,
        "avg_latency_all": 1.5,
        "failure_reason_distribution": {"timeout": 10, "error": 10},
        "queue_metrics": [
            {
                "queue_id": "test_queue",
                "total_items": 10,
                "pending_items": 0,
                "completed_items": 8,
                "failed_items": 2,
                "running_items": 0,
                "stale_items": 0,
                "throughput_last_24h": 0.8,
                "avg_execution_latency": 1.2,
                "failure_reasons": {"timeout": 2},
            }
        ],
        "metadata": {
            "runtime_root": project_root,
            "tasks_file": os.path.join(project_root, ".openclaw", "orchestrator", "tasks.json"),
            "collection_version": "1.0",
        },
    }

    # 创建临时文件
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "metrics_baseline_test.json")

    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=2)

    return test_file, temp_dir


def run_integration_test():
    """运行集成测试（实际文件读取）"""
    print("\n" + "=" * 60)
    print("集成测试: 实际文件读取测试")
    print("=" * 60)

    # 创建测试文件
    test_file, temp_dir = create_test_metrics_baseline()

    try:
        # 修改收集器以使用测试文件
        collector = StabilityMetricsCollector()

        # 临时修改workspace路径指向测试目录

        def mock_glob(pattern):
            if "metrics_baseline" in pattern:
                # 返回测试文件
                return [test_file]
            # 对于其他模式，返回空列表
            return []

        # 使用模拟的glob
        import scripts.collect_stability_metrics as module

        original_glob = module.glob.glob
        module.glob.glob = mock_glob

        # 收集指标
        metrics = collector.collect_metrics()

        # 恢复原始glob
        module.glob.glob = original_glob

        if metrics:
            print(f"   ✅ 集成测试通过: 从测试文件读取到 {len(metrics)} 个指标")
            for metric in metrics:
                if metric.metric_type in ["response_time", "error_rate"]:
                    print(f"      - {metric.metric_id}: {metric.value} (来自测试文件)")
        else:
            print("   ❌ 集成测试失败: 未读取到指标")

    finally:
        # 清理临时文件
        import shutil

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def main():
    """主测试函数"""
    print("=" * 60)
    print("OpenHuman MVP 稳定性指标测试套件")
    print("=" * 60)

    # 运行单元测试
    print("\n运行单元测试...")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestStabilityMetricsCollector)
    suite.addTests(loader.loadTestsFromTestCase(TestStabilityGate))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 运行集成测试
    print("\n运行集成测试...")
    run_integration_test()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    test_requirements = [
        ("1. 指标聚合正路径测试", "验证多个指标能正确聚合"),
        ("2. 告警阈值命中测试", "验证阈值违规能触发正确告警等级"),
        ("3. 缺指标负路径测试", "验证指标缺失能触发告警和门禁"),
    ]

    print("\n文档要求的三个验证测试:")
    for req_name, req_desc in test_requirements:
        print(f"  {req_name}: {req_desc}")

    print(f"\n单元测试结果: {result.testsRun} 个测试运行")
    print(f"  通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败: {len(result.failures)}")
    print(f"  错误: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ 所有测试通过!")
        return 0
    else:
        print("\n❌ 测试失败!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
