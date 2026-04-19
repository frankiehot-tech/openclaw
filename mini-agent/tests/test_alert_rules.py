#!/usr/bin/env python3
"""
Alert Rules Tests - 告警规则测试

验证告警规则引擎、规则评估、告警生成和负向路径（失败场景）。
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

from agent.core.alert_rules import (
    Alert,
    AlertEngine,
    AlertLevel,
    AlertRule,
    evaluate_alerts,
    get_global_alert_engine,
)
from agent.core.performance_metrics import (
    MetricDimension,
    MetricType,
    PerformanceMetricsCollector,
    get_global_collector,
)


class TestAlertRule(unittest.TestCase):
    """AlertRule 测试"""

    def test_rule_creation(self):
        """测试 AlertRule 创建"""
        rule = AlertRule(
            rule_id="test_rule",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            condition=">",
            threshold=10.0,
            alert_level=AlertLevel.WARNING,
            description="Queue length warning",
            cooldown_seconds=300,
            labels={"component": "queue"},
            metadata={"owner": "team"},
        )

        self.assertEqual(rule.rule_id, "test_rule")
        self.assertEqual(rule.metric_dimension, MetricDimension.QUEUE_LENGTH)
        self.assertEqual(rule.condition, ">")
        self.assertEqual(rule.threshold, 10.0)
        self.assertEqual(rule.alert_level, AlertLevel.WARNING)
        self.assertEqual(rule.description, "Queue length warning")
        self.assertEqual(rule.cooldown_seconds, 300)
        self.assertEqual(rule.labels, {"component": "queue"})
        self.assertEqual(rule.metadata, {"owner": "team"})

    def test_rule_evaluation(self):
        """测试规则评估"""
        # 测试各种条件
        test_cases = [
            (">", 15.0, 10.0, True),  # 15 > 10 = True
            (">", 5.0, 10.0, False),  # 5 > 10 = False
            (">=", 10.0, 10.0, True),  # 10 >= 10 = True
            (">=", 9.0, 10.0, False),  # 9 >= 10 = False
            ("<", 5.0, 10.0, True),  # 5 < 10 = True
            ("<", 15.0, 10.0, False),  # 15 < 10 = False
            ("<=", 10.0, 10.0, True),  # 10 <= 10 = True
            ("<=", 11.0, 10.0, False),  # 11 <= 10 = False
            ("==", 10.0, 10.0, True),  # 10 == 10 = True
            ("==", 11.0, 10.0, False),  # 11 == 10 = False
            ("!=", 11.0, 10.0, True),  # 11 != 10 = True
            ("!=", 10.0, 10.0, False),  # 10 != 10 = False
        ]

        for condition, value, threshold, expected in test_cases:
            rule = AlertRule(
                rule_id=f"test_{condition}",
                metric_dimension=MetricDimension.QUEUE_LENGTH,
                condition=condition,
                threshold=threshold,
                alert_level=AlertLevel.WARNING,
            )
            result = rule.evaluate(value)
            self.assertEqual(
                result,
                expected,
                f"Failed: {value} {condition} {threshold} should be {expected}",
            )

    def test_rule_evaluation_invalid_condition(self):
        """测试无效条件评估"""
        rule = AlertRule(
            rule_id="test_invalid",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            condition="invalid",  # 无效条件
            threshold=10.0,
            alert_level=AlertLevel.WARNING,
        )

        # 应该返回 False 并记录警告
        with patch("agent.core.alert_rules.logger") as mock_logger:
            result = rule.evaluate(15.0)
            self.assertFalse(result)
            mock_logger.warning.assert_called_once()

    def test_rule_to_dict(self):
        """测试规则字典转换"""
        rule = AlertRule(
            rule_id="test_rule",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            condition=">",
            threshold=10.0,
            alert_level=AlertLevel.WARNING,
        )

        rule_dict = rule.to_dict()

        self.assertEqual(rule_dict["rule_id"], "test_rule")
        self.assertEqual(rule_dict["metric_dimension"], MetricDimension.QUEUE_LENGTH)
        self.assertEqual(rule_dict["condition"], ">")
        self.assertEqual(rule_dict["threshold"], 10.0)
        self.assertEqual(rule_dict["alert_level"], AlertLevel.WARNING)


class TestAlert(unittest.TestCase):
    """Alert 测试"""

    def test_alert_creation(self):
        """测试 Alert 创建"""
        alert = Alert(
            alert_id="alert_123",
            rule_id="queue_length_high",
            alert_level=AlertLevel.CRITICAL,
            message="Queue length critical: 25.0 > 20.0",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            metric_value=25.0,
            threshold=20.0,
            labels={"queue_id": "test_queue"},
            metadata={"owner": "team"},
        )

        self.assertEqual(alert.alert_id, "alert_123")
        self.assertEqual(alert.rule_id, "queue_length_high")
        self.assertEqual(alert.alert_level, AlertLevel.CRITICAL)
        self.assertEqual(alert.message, "Queue length critical: 25.0 > 20.0")
        self.assertEqual(alert.metric_dimension, MetricDimension.QUEUE_LENGTH)
        self.assertEqual(alert.metric_value, 25.0)
        self.assertEqual(alert.threshold, 20.0)
        self.assertEqual(alert.labels, {"queue_id": "test_queue"})
        self.assertEqual(alert.metadata, {"owner": "team"})
        self.assertFalse(alert.acknowledged)
        self.assertGreater(alert.timestamp, 0)

    def test_alert_to_dict(self):
        """测试 Alert 字典转换"""
        alert = Alert(
            alert_id="alert_123",
            rule_id="test_rule",
            alert_level=AlertLevel.WARNING,
            message="Test alert",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            metric_value=15.0,
            threshold=10.0,
        )

        alert_dict = alert.to_dict()

        self.assertEqual(alert_dict["alert_id"], "alert_123")
        self.assertEqual(alert_dict["rule_id"], "test_rule")
        self.assertEqual(alert_dict["alert_level"], "warning")
        self.assertEqual(alert_dict["metric_dimension"], "queue_length")
        self.assertEqual(alert_dict["metric_value"], 15.0)
        self.assertEqual(alert_dict["threshold"], 10.0)


class TestAlertEngineNegativePaths(unittest.TestCase):
    """告警引擎负向路径测试"""

    def setUp(self):
        # 创建独立的收集器和引擎
        self.collector = PerformanceMetricsCollector(retention_seconds=60)
        self.engine = AlertEngine()
        self.engine.collector = self.collector  # 替换为测试收集器

        # 清除默认规则，添加测试规则
        self.engine.rules.clear()
        self.test_rule = AlertRule(
            rule_id="test_warning",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            condition=">",
            threshold=10.0,
            alert_level=AlertLevel.WARNING,
            description="Test warning rule",
            cooldown_seconds=1,  # 短冷却时间便于测试
        )
        self.engine.add_rule(self.test_rule)

    def tearDown(self):
        self.collector.clear()
        self.engine.alerts.clear()
        self.engine.last_evaluation.clear()

    def test_evaluate_no_metrics(self):
        """测试无指标数据时的评估"""
        # 不记录任何指标
        alerts = self.engine.evaluate_all()

        # 应该没有告警
        self.assertEqual(len(alerts), 0)

    def test_evaluate_threshold_not_met(self):
        """测试阈值未达到时的评估"""
        # 记录低于阈值的指标
        self.collector.record_queue_length(5, "test_queue")

        alerts = self.engine.evaluate_all()

        # 应该没有告警
        self.assertEqual(len(alerts), 0)

    def test_evaluate_cooldown_respected(self):
        """测试冷却时间被遵守"""
        # 记录超过阈值的指标
        self.collector.record_queue_length(15, "test_queue")

        # 第一次评估应该生成告警
        alerts1 = self.engine.evaluate_all()
        self.assertEqual(len(alerts1), 1)

        # 立即第二次评估（仍在冷却期内）
        alerts2 = self.engine.evaluate_all()
        self.assertEqual(len(alerts2), 0)  # 应该没有新告警

        # 等待冷却时间
        time.sleep(1.1)

        # 第三次评估应该生成新告警
        alerts3 = self.engine.evaluate_all()
        self.assertEqual(len(alerts3), 1)

    def test_evaluate_duplicate_alerts(self):
        """测试重复告警去重"""
        # 记录超过阈值的指标
        self.collector.record_queue_length(15, "test_queue")

        # 第一次评估
        alerts1 = self.engine.evaluate_all()
        self.assertEqual(len(alerts1), 1)
        alert_id1 = alerts1[0].alert_id

        # 等待冷却时间
        time.sleep(1.1)

        # 记录另一个超过阈值的指标（相同维度、标签）
        self.collector.record_queue_length(16, "test_queue")

        # 第二次评估应该更新现有告警，而不是创建新告警
        alerts2 = self.engine.evaluate_all()
        self.assertEqual(len(alerts2), 0)  # 没有新告警（重复的）

        # 验证现有告警已更新
        self.assertIn(alert_id1, self.engine.alerts)
        self.assertGreater(self.engine.alerts[alert_id1].timestamp, 0)

    def test_evaluate_with_different_labels(self):
        """测试不同标签的指标评估"""
        # 添加带标签的规则
        labeled_rule = AlertRule(
            rule_id="labeled_rule",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            condition=">",
            threshold=5.0,
            alert_level=AlertLevel.WARNING,
            labels={"environment": "production"},
        )
        self.engine.add_rule(labeled_rule)

        # 记录不匹配标签的指标
        self.collector.record_queue_length(10, "test_queue")  # 无环境标签

        # 评估
        alerts = self.engine.evaluate_all()

        # 应该没有告警（标签不匹配）
        self.assertEqual(len(alerts), 0)

        # 记录匹配标签的指标
        self.collector.record(
            dimension=MetricDimension.QUEUE_LENGTH,
            value=10.0,
            labels={"queue_id": "prod_queue", "environment": "production"},
        )

        # 再次评估
        alerts = self.engine.evaluate_all()

        # 现在应该有告警
        self.assertEqual(len(alerts), 1)

    def test_load_config_invalid_path(self):
        """测试加载不存在的配置文件"""
        invalid_path = Path("/nonexistent/config.yaml")

        # 不应该抛出异常
        self.engine.load_config(invalid_path)

    def test_load_config_invalid_yaml(self):
        """测试加载无效的 YAML 配置"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: [}")
            config_path = Path(f.name)

        try:
            # 不应该抛出异常
            self.engine.load_config(config_path)
        finally:
            config_path.unlink()

    def test_load_config_missing_fields(self):
        """测试加载缺少必要字段的配置"""
        config = {
            "alert_rules": [
                {
                    # 缺少 rule_id
                    "metric_dimension": "QUEUE_LENGTH",
                    "condition": ">",
                    "threshold": 10.0,
                    "alert_level": "WARNING",
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = Path(f.name)

        try:
            # 不应该抛出异常（应该跳过无效规则）
            original_rule_count = len(self.engine.rules)
            self.engine.load_config(config_path)

            # 规则数量不应改变
            self.assertEqual(len(self.engine.rules), original_rule_count)
        finally:
            config_path.unlink()

    def test_acknowledge_nonexistent_alert(self):
        """测试确认不存在的告警"""
        result = self.engine.acknowledge_alert("nonexistent_alert")
        self.assertFalse(result)

    def test_resolve_nonexistent_alert(self):
        """测试解决不存在的告警"""
        result = self.engine.resolve_alert("nonexistent_alert")
        self.assertFalse(result)

    def test_get_active_alerts_filtered(self):
        """测试按级别过滤告警"""
        # 创建不同级别的告警
        warning_alert = Alert(
            alert_id="warning_1",
            rule_id="test_warning",
            alert_level=AlertLevel.WARNING,
            message="Warning alert",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            metric_value=15.0,
            threshold=10.0,
        )

        critical_alert = Alert(
            alert_id="critical_1",
            rule_id="test_critical",
            alert_level=AlertLevel.CRITICAL,
            message="Critical alert",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            metric_value=25.0,
            threshold=20.0,
        )

        self.engine.alerts[warning_alert.alert_id] = warning_alert
        self.engine.alerts[critical_alert.alert_id] = critical_alert

        # 过滤警告级别
        warning_alerts = self.engine.get_active_alerts(AlertLevel.WARNING)
        self.assertEqual(len(warning_alerts), 1)
        self.assertEqual(warning_alerts[0].alert_level, AlertLevel.WARNING)

        # 过滤关键级别
        critical_alerts = self.engine.get_active_alerts(AlertLevel.CRITICAL)
        self.assertEqual(len(critical_alerts), 1)
        self.assertEqual(critical_alerts[0].alert_level, AlertLevel.CRITICAL)

    def test_export_summary_empty(self):
        """测试导出空摘要"""
        summary = self.engine.export_summary()

        self.assertIn("timestamp", summary)
        self.assertEqual(summary["active_alert_count"], 0)
        self.assertGreater(summary["rule_count"], 0)
        self.assertIn("alerts_by_level", summary)
        self.assertIn("active_alerts", summary)

    def test_export_json(self):
        """测试导出 JSON"""
        # 添加一个告警
        alert = Alert(
            alert_id="test_alert",
            rule_id="test_rule",
            alert_level=AlertLevel.WARNING,
            message="Test alert",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            metric_value=15.0,
            threshold=10.0,
        )
        self.engine.alerts[alert.alert_id] = alert

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "alerts.json"
            data = self.engine.export_json(export_path)

            self.assertIn("export_timestamp", data)
            self.assertIn("rules", data)
            self.assertIn("active_alerts", data)
            self.assertIn("last_evaluations", data)

            # 验证文件已创建
            self.assertTrue(export_path.exists())


class TestAlertEngineIntegration(unittest.TestCase):
    """告警引擎集成测试"""

    def setUp(self):
        self.collector = get_global_collector()
        self.engine = get_global_alert_engine()

        # 清空现有状态
        self.collector.clear()
        self.engine.alerts.clear()
        self.engine.last_evaluation.clear()

        # 添加测试规则
        self.test_rule = AlertRule(
            rule_id="integration_test",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            condition=">",
            threshold=5.0,
            alert_level=AlertLevel.WARNING,
            cooldown_seconds=0,  # 无冷却时间
        )
        self.engine.add_rule(self.test_rule)

    def tearDown(self):
        self.collector.clear()
        if "integration_test" in self.engine.rules:
            self.engine.remove_rule("integration_test")
        self.engine.alerts.clear()
        self.engine.last_evaluation.clear()

    def test_global_functions(self):
        """测试全局函数"""
        # 记录超过阈值的指标
        self.collector.record_queue_length(10, "test_queue")

        # 使用全局函数评估
        alerts = evaluate_alerts()

        # 应该有告警
        self.assertGreater(len(alerts), 0)

        # 验证全局引擎实例
        engine1 = get_global_alert_engine()
        engine2 = get_global_alert_engine()
        self.assertIs(engine1, engine2)

    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        # 1. 记录正常指标（无告警）
        self.collector.record_queue_length(3, "queue1")
        alerts1 = self.engine.evaluate_all()
        self.assertEqual(len(alerts1), 0)

        # 2. 记录异常指标（生成告警）
        self.collector.record_queue_length(8, "queue1")
        alerts2 = self.engine.evaluate_all()
        self.assertEqual(len(alerts2), 1)

        alert = alerts2[0]
        self.assertEqual(alert.rule_id, "integration_test")
        self.assertEqual(alert.alert_level, AlertLevel.WARNING)

        # 3. 确认告警
        result = self.engine.acknowledge_alert(alert.alert_id)
        self.assertTrue(result)
        self.assertTrue(self.engine.alerts[alert.alert_id].acknowledged)

        # 4. 记录正常指标（告警仍存在但已确认）
        self.collector.record_queue_length(2, "queue1")
        alerts3 = self.engine.evaluate_all()
        self.assertEqual(len(alerts3), 0)  # 没有新告警

        # 5. 解决告警
        result = self.engine.resolve_alert(alert.alert_id)
        self.assertTrue(result)
        self.assertNotIn(alert.alert_id, self.engine.alerts)


if __name__ == "__main__":
    unittest.main()
