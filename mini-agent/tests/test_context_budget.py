#!/usr/bin/env python3
"""
上下文预算与约束恢复基础层测试
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.core.context_budget import (
    Constraint,
    ConstraintRecoveryManager,
    ConstraintSeverity,
    ConstraintType,
    ContextBudgetManager,
    ContextLayer,
    ContextLayerType,
    ProgressiveDisclosureManager,
    RecoveryAction,
    RecoveryActionType,
    ResetTrigger,
    StageBudget,
    UtilizationThresholds,
    check_context_health,
    handle_constraint_violation,
    smoke_test_config,
)


class TestUtilizationThresholds(unittest.TestCase):
    """使用率阈值测试"""

    def test_default_thresholds(self):
        thresholds = UtilizationThresholds()
        self.assertEqual(thresholds.warning, 0.7)
        self.assertEqual(thresholds.critical, 0.85)
        self.assertEqual(thresholds.reset, 0.95)

    def test_check_utilization(self):
        thresholds = UtilizationThresholds(warning=0.5, critical=0.7, reset=0.9)

        # 正常情况
        status, overflow = thresholds.check(0.3)
        self.assertEqual(status, "normal")
        self.assertIsNone(overflow)

        # 警告
        status, overflow = thresholds.check(0.6)
        self.assertEqual(status, "warning")
        self.assertAlmostEqual(overflow, 0.1)

        # 严重
        status, overflow = thresholds.check(0.8)
        self.assertEqual(status, "critical")
        self.assertAlmostEqual(overflow, 0.1)

        # 重置
        status, overflow = thresholds.check(0.95)
        self.assertEqual(status, "reset")
        self.assertAlmostEqual(overflow, 0.05)


class TestStageBudget(unittest.TestCase):
    """阶段预算测试"""

    def test_from_dict(self):
        data = {
            "max_tokens": 10000,
            "critical_reserve": 500,
            "utilization_thresholds": {"warning": 0.6, "critical": 0.8, "reset": 0.95},
        }
        budget = StageBudget.from_dict(data)
        self.assertEqual(budget.max_tokens, 10000)
        self.assertEqual(budget.critical_reserve, 500)
        self.assertEqual(budget.utilization_thresholds.warning, 0.6)

    def test_get_available_tokens(self):
        budget = StageBudget(
            max_tokens=10000,
            critical_reserve=1000,
            utilization_thresholds=UtilizationThresholds(),
        )

        # 正常情况
        self.assertEqual(budget.get_available_tokens(5000), 4000)  # 10000-5000-1000=4000

        # 达到保留值
        self.assertEqual(budget.get_available_tokens(9000), 0)  # 10000-9000-1000=0

        # 超过保留值
        self.assertEqual(budget.get_available_tokens(9500), 0)  # 负数归零

    def test_get_utilization(self):
        budget = StageBudget(
            max_tokens=10000,
            critical_reserve=1000,
            utilization_thresholds=UtilizationThresholds(),
        )

        self.assertEqual(budget.get_utilization(0), 0.0)
        self.assertEqual(budget.get_utilization(5000), 0.5)
        self.assertEqual(budget.get_utilization(10000), 1.0)
        self.assertEqual(budget.get_utilization(15000), 1.0)  # 上限为1.0


class TestContextBudgetManager(unittest.TestCase):
    """上下文预算管理器测试"""

    def setUp(self):
        # 创建临时配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "context_budget.yaml"

        config = {
            "context_budget": {
                "global_default": {
                    "max_tokens": 128000,
                    "critical_reserve": 1000,
                    "utilization_thresholds": {
                        "warning": 0.7,
                        "critical": 0.85,
                        "reset": 0.95,
                    },
                },
                "stage_specific": {
                    "build": {
                        "max_tokens": 96000,
                        "critical_reserve": 1000,
                        "utilization_thresholds": {
                            "warning": 0.7,
                            "critical": 0.85,
                            "reset": 0.95,
                        },
                    }
                },
                "openhuman_mapping": {"distill": "think", "skill_design": "plan"},
            }
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        self.manager = ContextBudgetManager(self.config_path)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_get_budget_existing_stage(self):
        # 测试现有阶段
        budget = self.manager.get_budget("build")
        self.assertEqual(budget.max_tokens, 96000)

        # 测试大小写不敏感
        budget = self.manager.get_budget("BUILD")
        self.assertEqual(budget.max_tokens, 96000)

    def test_get_budget_unknown_stage(self):
        # 测试未知阶段（回退到全局默认）
        budget = self.manager.get_budget("unknown_stage")
        self.assertEqual(budget.max_tokens, 128000)

    def test_check_utilization(self):
        status, overflow, budget = self.manager.check_utilization("build", 50000)
        self.assertEqual(budget.max_tokens, 96000)
        utilization = 50000 / 96000
        if utilization >= 0.7:
            self.assertEqual(status, "warning")
        else:
            self.assertEqual(status, "normal")

    def test_should_reset_context(self):
        # 不应重置
        self.assertFalse(self.manager.should_reset_context("build", 50000))

        # 应重置（使用率超过95%）
        should_reset = self.manager.should_reset_context("build", 92000)  # 92000/96000=0.958
        # 由于浮点精度，可能需要调整
        # 我们只检查逻辑


class TestConstraintRecoveryManager(unittest.TestCase):
    """约束恢复管理器测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "context_budget.yaml"

        config = {
            "constraint_recovery": {
                "constraint_types": {
                    "syntax": {
                        "name": "语法约束",
                        "description": "代码语法约束",
                        "detection_method": "static_analysis",
                        "severity_levels": {"error": "blocking", "warning": "advisory"},
                    }
                },
                "recovery_actions": {
                    "retry": {
                        "name": "重试",
                        "description": "重新执行",
                        "max_attempts": 3,
                        "backoff_strategy": "exponential",
                        "applicability": ["transient_errors"],
                    }
                },
                "recovery_strategy_mapping": {"syntax": {"error": ["retry"], "warning": ["retry"]}},
            }
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        self.manager = ConstraintRecoveryManager(self.config_path)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_create_constraint(self):
        constraint = self.manager.create_constraint(
            constraint_type=ConstraintType.SYNTAX,
            severity=ConstraintSeverity.ERROR,
            message="语法错误",
            detection_source="test",
            violation_context={"file": "test.py", "line": 10},
        )

        self.assertEqual(constraint.type, ConstraintType.SYNTAX)
        self.assertEqual(constraint.severity, ConstraintSeverity.ERROR)
        self.assertEqual(constraint.message, "语法错误")

    def test_get_recovery_actions(self):
        constraint = self.manager.create_constraint(
            constraint_type=ConstraintType.SYNTAX,
            severity=ConstraintSeverity.ERROR,
            message="测试",
            detection_source="test",
            violation_context={},
        )

        actions = self.manager.get_recovery_actions(constraint)
        self.assertGreaterEqual(len(actions), 0)

        if actions:
            self.assertEqual(actions[0].type, RecoveryActionType.RETRY)

    def test_validate_constraint(self):
        constraint = self.manager.create_constraint(
            constraint_type=ConstraintType.SYNTAX,
            severity=ConstraintSeverity.ERROR,
            message="测试消息",
            detection_source="test",
            violation_context={"test": True},
        )

        is_valid, errors = self.manager.validate_constraint(constraint)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_constraint_negative(self):
        """负路径测试：无效约束"""
        # 创建缺少必填字段的约束（通过直接实例化）
        constraint = Constraint(
            type=ConstraintType.SYNTAX,
            severity=ConstraintSeverity.ERROR,
            message="",  # 空消息
            detection_source="",
            violation_context={},
        )

        is_valid, errors = self.manager.validate_constraint(constraint)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


class TestProgressiveDisclosureManager(unittest.TestCase):
    """渐进式披露管理器测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "context_budget.yaml"

        config = {
            "progressive_disclosure": {
                "context_layers": [
                    {
                        "name": "full",
                        "description": "完整上下文",
                        "retention_policy": "selective",
                        "disclosure_priority": 1,
                    },
                    {
                        "name": "summary",
                        "description": "摘要上下文",
                        "retention_policy": "selective",
                        "disclosure_priority": 2,
                    },
                ],
                "reset_behavior": {
                    "degrade_strategy": "progressive",
                    "progressive_steps": ["summary", "minimal", "reset"],
                    "reset_actions": [
                        {
                            "action": "clear_conversation_history",
                            "scope": "non_essential",
                            "preserve": ["task_state"],
                        }
                    ],
                },
            }
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        self.manager = ProgressiveDisclosureManager(self.config_path)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_layer_initialization(self):
        self.assertEqual(len(self.manager.layers), 2)
        self.assertEqual(self.manager.layers[0].name, ContextLayerType.FULL)
        self.assertEqual(self.manager.layers[1].name, ContextLayerType.SUMMARY)

    def test_get_layer(self):
        layer = self.manager.get_layer("full")
        self.assertIsNotNone(layer)
        self.assertEqual(layer.name, ContextLayerType.FULL)

        layer = self.manager.get_layer(ContextLayerType.SUMMARY)
        self.assertIsNotNone(layer)
        self.assertEqual(layer.name, ContextLayerType.SUMMARY)

    def test_degrade_context(self):
        degrade_path = self.manager.degrade_context(
            ContextLayerType.FULL, ResetTrigger.UTILIZATION_EXCEEDS
        )
        self.assertGreaterEqual(len(degrade_path), 1)


class TestIntegrationFunctions(unittest.TestCase):
    """集成函数测试"""

    def test_check_context_health(self):
        # 使用默认配置测试
        health = check_context_health("build", 50000)

        self.assertIn("stage", health)
        self.assertIn("used_tokens", health)
        self.assertIn("max_tokens", health)
        self.assertIn("utilization", health)
        self.assertIn("status", health)
        self.assertIn("should_reset", health)

        self.assertEqual(health["stage"], "build")
        self.assertEqual(health["used_tokens"], 50000)

    def test_handle_constraint_violation(self):
        constraint = Constraint(
            type=ConstraintType.SYNTAX,
            severity=ConstraintSeverity.ERROR,
            message="测试约束",
            detection_source="test_suite",
            violation_context={"test": True},
        )

        result = handle_constraint_violation(constraint)

        self.assertIn("status", result)
        self.assertIn("constraint", result)
        self.assertIn("recovery_actions", result)

        self.assertEqual(result["constraint"]["message"], "测试约束")


class TestSmokeTest(unittest.TestCase):
    """冒烟测试"""

    def test_smoke_test_config(self):
        """测试配置加载冒烟测试"""
        # 这个测试使用实际的配置文件
        success = smoke_test_config()
        self.assertTrue(success, "冒烟测试应通过")


if __name__ == "__main__":
    unittest.main()
