#!/usr/bin/env python3
"""
上下文预算与约束恢复基础层 - 核心模块

提供上下文预算管理、渐进式披露/重置、约束检测与恢复的基础骨架。
与现有 Athena 运行时集成，遵循控制面优先级策略。
"""

import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== 枚举定义 ====================


class ConstraintType(Enum):
    """约束类型枚举"""

    SYNTAX = "syntax"
    ARCHITECTURE = "architecture"
    BEHAVIORAL = "behavioral"


class ConstraintSeverity(Enum):
    """约束严重程度枚举"""

    ERROR = "error"
    WARNING = "warning"


class RecoveryActionType(Enum):
    """恢复动作类型枚举"""

    RETRY = "retry"
    RESET = "reset"
    SPLIT = "split"
    HUMAN_ESCALATION = "human_escalation"


class ContextLayerType(Enum):
    """上下文层类型枚举"""

    FULL = "full"
    SUMMARY = "summary"
    MINIMAL = "minimal"


class ResetTrigger(Enum):
    """重置触发器枚举"""

    UTILIZATION_EXCEEDS = "utilization_exceeds"
    CONSTRAINT_VIOLATION = "constraint_violation"
    MANUAL_INTERVENTION = "manual_intervention"


# ==================== 数据类定义 ====================


@dataclass
class UtilizationThresholds:
    """使用率阈值配置"""

    warning: float = 0.7
    critical: float = 0.85
    reset: float = 0.95

    def check(self, utilization: float) -> Tuple[str, Optional[float]]:
        """检查使用率并返回状态和超出比例"""
        if utilization >= self.reset:
            return "reset", utilization - self.reset
        elif utilization >= self.critical:
            return "critical", utilization - self.critical
        elif utilization >= self.warning:
            return "warning", utilization - self.warning
        else:
            return "normal", None


@dataclass
class StageBudget:
    """阶段特定预算配置"""

    max_tokens: int
    critical_reserve: int
    utilization_thresholds: UtilizationThresholds

    @classmethod
    def from_dict(cls, data: Dict) -> "StageBudget":
        """从字典创建实例"""
        thresholds = UtilizationThresholds(**data.get("utilization_thresholds", {}))
        return cls(
            max_tokens=data["max_tokens"],
            critical_reserve=data["critical_reserve"],
            utilization_thresholds=thresholds,
        )

    def get_available_tokens(self, used_tokens: int) -> int:
        """计算可用token数量（考虑保留部分）"""
        available = self.max_tokens - used_tokens
        # 确保不低于关键保留值
        if available < self.critical_reserve:
            return 0
        return available - self.critical_reserve

    def get_utilization(self, used_tokens: int) -> float:
        """计算使用率（0.0-1.0）"""
        if self.max_tokens <= 0:
            return 0.0
        return min(1.0, used_tokens / self.max_tokens)


@dataclass
class Constraint:
    """约束表示"""

    type: ConstraintType
    severity: ConstraintSeverity
    message: str
    detection_source: str
    violation_context: Dict[str, Any]
    suggested_fix: Optional[str] = None
    related_files: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "detection_source": self.detection_source,
            "violation_context": self.violation_context,
            "suggested_fix": self.suggested_fix,
            "related_files": self.related_files,
            "metrics": self.metrics,
        }


@dataclass
class RecoveryAction:
    """恢复动作表示"""

    type: RecoveryActionType
    parameters: Dict[str, Any]
    applicability: List[str]

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "type": self.type.value,
            "parameters": self.parameters,
            "applicability": self.applicability,
        }


@dataclass
class ContextLayer:
    """上下文层表示"""

    name: ContextLayerType
    description: str
    retention_policy: str
    disclosure_priority: int

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name.value,
            "description": self.description,
            "retention_policy": self.retention_policy,
            "disclosure_priority": self.disclosure_priority,
        }


# ==================== 核心管理类 ====================


class ContextBudgetManager:
    """上下文预算管理器"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = (
            config_path or Path(__file__).parent.parent / "config" / "context_budget.yaml"
        )
        self.config = self._load_config()
        self._budget_cache: Dict[str, StageBudget] = {}
        self._init_budgets()

    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"无法加载上下文预算配置: {e}")
            # 返回默认配置
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "context_budget": {
                "global_default": {
                    "max_tokens": 128000,
                    "critical_reserve": 1000,
                    "utilization_thresholds": {
                        "warning": 0.7,
                        "critical": 0.85,
                        "reset": 0.95,
                    },
                }
            }
        }

    def _init_budgets(self):
        """初始化预算缓存"""
        budget_config = self.config.get("context_budget", {})
        global_default = StageBudget.from_dict(budget_config.get("global_default", {}))

        # 设置全局默认
        self._budget_cache["global"] = global_default

        # 设置阶段特定预算
        stage_specific = budget_config.get("stage_specific", {})
        for stage_name, stage_config in stage_specific.items():
            self._budget_cache[stage_name] = StageBudget.from_dict(stage_config)

        # 设置OpenHuman映射
        openhuman_mapping = budget_config.get("openhuman_mapping", {})
        for openhuman_stage, engineering_stage in openhuman_mapping.items():
            if engineering_stage in self._budget_cache:
                self._budget_cache[openhuman_stage] = self._budget_cache[engineering_stage]

    def get_budget(self, stage: str) -> StageBudget:
        """获取指定阶段的预算配置"""
        # 直接匹配
        if stage in self._budget_cache:
            return self._budget_cache[stage]

        # 尝试小写匹配
        stage_lower = stage.lower()
        if stage_lower in self._budget_cache:
            return self._budget_cache[stage_lower]

        # 回退到全局默认
        logger.warning(f"未找到阶段 '{stage}' 的预算配置，使用全局默认")
        return self._budget_cache["global"]

    def check_utilization(
        self, stage: str, used_tokens: int
    ) -> Tuple[str, Optional[float], StageBudget]:
        """检查使用率并返回状态、超出比例和预算配置"""
        budget = self.get_budget(stage)
        utilization = budget.get_utilization(used_tokens)
        status, overflow = budget.utilization_thresholds.check(utilization)
        return status, overflow, budget

    def get_available_tokens(self, stage: str, used_tokens: int) -> int:
        """获取可用token数量"""
        budget = self.get_budget(stage)
        return budget.get_available_tokens(used_tokens)

    def should_reset_context(self, stage: str, used_tokens: int) -> bool:
        """判断是否需要重置上下文"""
        status, _, _ = self.check_utilization(stage, used_tokens)
        return status == "reset"


class ProgressiveDisclosureManager:
    """渐进式披露管理器"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = (
            config_path or Path(__file__).parent.parent / "config" / "context_budget.yaml"
        )
        self.config = self._load_config()
        self.layers = self._init_layers()

    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"无法加载渐进式披露配置: {e}")
            return {}

    def _init_layers(self) -> List[ContextLayer]:
        """初始化上下文层"""
        layers_config = self.config.get("progressive_disclosure", {}).get("context_layers", [])
        layers = []
        for layer_config in layers_config:
            try:
                layer = ContextLayer(
                    name=ContextLayerType(layer_config["name"]),
                    description=layer_config.get("description", ""),
                    retention_policy=layer_config.get("retention_policy", "selective"),
                    disclosure_priority=layer_config.get("disclosure_priority", 1),
                )
                layers.append(layer)
            except Exception as e:
                logger.error(f"无法初始化上下文层 {layer_config}: {e}")

        # 按优先级排序
        layers.sort(key=lambda x: x.disclosure_priority)
        return layers

    def get_layer(self, name: Union[str, ContextLayerType]) -> Optional[ContextLayer]:
        """获取指定名称的上下文层"""
        if isinstance(name, str):
            name = ContextLayerType(name)

        for layer in self.layers:
            if layer.name == name:
                return layer
        return None

    def degrade_context(
        self, current_layer: ContextLayerType, trigger: ResetTrigger
    ) -> List[ContextLayerType]:
        """根据触发器降级上下文，返回降级路径"""
        reset_config = self.config.get("progressive_disclosure", {}).get("reset_behavior", {})
        degrade_strategy = reset_config.get("degrade_strategy", "immediate")

        if degrade_strategy == "immediate":
            # 立即重置到最小层
            return [ContextLayerType.MINIMAL]

        elif degrade_strategy == "progressive":
            # 渐进式降级
            steps = reset_config.get("progressive_steps", [])
            current_idx = None
            for i, step in enumerate(steps):
                if step == current_layer.value:
                    current_idx = i
                    break

            if current_idx is not None and current_idx + 1 < len(steps):
                return [ContextLayerType(step) for step in steps[current_idx + 1 :]]
            else:
                return [ContextLayerType.MINIMAL]

        else:  # hybrid
            # 混合策略：根据触发器决定
            if trigger == ResetTrigger.UTILIZATION_EXCEEDS:
                return [ContextLayerType.SUMMARY, ContextLayerType.MINIMAL]
            else:
                return [ContextLayerType.MINIMAL]

    def get_reset_actions(self, trigger: ResetTrigger) -> List[Dict[str, Any]]:
        """获取重置动作配置"""
        reset_config = self.config.get("progressive_disclosure", {}).get("reset_behavior", {})
        actions = reset_config.get("reset_actions", [])

        filtered_actions = []
        for action in actions:
            # 可以根据触发器过滤动作
            filtered_actions.append(action)

        return filtered_actions


class ConstraintRecoveryManager:
    """约束恢复管理器"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = (
            config_path or Path(__file__).parent.parent / "config" / "context_budget.yaml"
        )
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"无法加载约束恢复配置: {e}")
            return {}

    def create_constraint(
        self,
        constraint_type: ConstraintType,
        severity: ConstraintSeverity,
        message: str,
        detection_source: str,
        violation_context: Dict[str, Any],
        **kwargs,
    ) -> Constraint:
        """创建约束实例"""
        return Constraint(
            type=constraint_type,
            severity=severity,
            message=message,
            detection_source=detection_source,
            violation_context=violation_context,
            suggested_fix=kwargs.get("suggested_fix"),
            related_files=kwargs.get("related_files", []),
            metrics=kwargs.get("metrics", {}),
        )

    def get_recovery_actions(self, constraint: Constraint) -> List[RecoveryAction]:
        """根据约束获取推荐的恢复动作"""
        recovery_config = self.config.get("constraint_recovery", {})
        strategy_mapping = recovery_config.get("recovery_strategy_mapping", {})

        constraint_type = constraint.type.value
        severity = constraint.severity.value

        # 获取推荐的动作类型
        recommended_types = []
        if constraint_type in strategy_mapping:
            if severity in strategy_mapping[constraint_type]:
                recommended_types = strategy_mapping[constraint_type][severity]

        # 转换为RecoveryAction对象
        actions_config = recovery_config.get("recovery_actions", {})
        actions = []

        for action_type in recommended_types:
            if action_type in actions_config:
                action_config = actions_config[action_type]
                action = RecoveryAction(
                    type=RecoveryActionType(action_type),
                    parameters=action_config.get("parameters", {}),
                    applicability=action_config.get("applicability", []),
                )
                actions.append(action)

        return actions

    def validate_constraint(self, constraint: Constraint) -> Tuple[bool, List[str]]:
        """验证约束是否符合合约"""
        contract_config = self.config.get("constraint_recovery", {}).get("constraint_contract", {})
        required_fields = contract_config.get("required_fields", [])
        validation_rules = contract_config.get("validation_rules", {})

        errors = []

        # 检查必填字段
        constraint_dict = constraint.to_dict()
        for field_name in required_fields:
            if field_name not in constraint_dict or not constraint_dict[field_name]:
                errors.append(f"缺少必填字段: {field_name}")

        # 检查类型枚举
        type_rule = validation_rules.get("type_must_be_one_of", [])
        if type_rule and constraint.type.value not in type_rule:
            errors.append(f"类型必须是 {type_rule} 之一")

        # 检查严重程度枚举
        severity_rule = validation_rules.get("severity_must_be_one_of", [])
        if severity_rule and constraint.severity.value not in severity_rule:
            errors.append(f"严重程度必须是 {severity_rule} 之一")

        # 检查消息非空
        message_rule = validation_rules.get("message_must_be_non_empty", False)
        if message_rule and not constraint.message.strip():
            errors.append("消息不能为空")

        return len(errors) == 0, errors


# ==================== 全局单例实例 ====================

_budget_manager: Optional[ContextBudgetManager] = None
_disclosure_manager: Optional[ProgressiveDisclosureManager] = None
_recovery_manager: Optional[ConstraintRecoveryManager] = None


def get_budget_manager() -> ContextBudgetManager:
    """获取上下文预算管理器单例"""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = ContextBudgetManager()
    return _budget_manager


def get_disclosure_manager() -> ProgressiveDisclosureManager:
    """获取渐进式披露管理器单例"""
    global _disclosure_manager
    if _disclosure_manager is None:
        _disclosure_manager = ProgressiveDisclosureManager()
    return _disclosure_manager


def get_recovery_manager() -> ConstraintRecoveryManager:
    """获取约束恢复管理器单例"""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = ConstraintRecoveryManager()
    return _recovery_manager


# ==================== 工具函数 ====================


def check_context_health(stage: str, used_tokens: int) -> Dict[str, Any]:
    """检查上下文健康状况（综合检查）"""
    budget_manager = get_budget_manager()
    status, overflow, budget = budget_manager.check_utilization(stage, used_tokens)

    available_tokens = budget.get_available_tokens(used_tokens)
    utilization = budget.get_utilization(used_tokens)

    result = {
        "stage": stage,
        "used_tokens": used_tokens,
        "max_tokens": budget.max_tokens,
        "critical_reserve": budget.critical_reserve,
        "available_tokens": available_tokens,
        "utilization": utilization,
        "status": status,
        "overflow": overflow,
        "should_reset": status == "reset",
    }

    # 如果达到重置阈值，添加重置建议
    if status == "reset":
        disclosure_manager = get_disclosure_manager()
        reset_actions = disclosure_manager.get_reset_actions(ResetTrigger.UTILIZATION_EXCEEDS)
        result["reset_actions"] = reset_actions
        result["recommendation"] = "立即进行上下文重置以避免任务失败"

    return result


def handle_constraint_violation(constraint: Constraint) -> Dict[str, Any]:
    """处理约束违规"""
    recovery_manager = get_recovery_manager()

    # 验证约束
    is_valid, errors = recovery_manager.validate_constraint(constraint)
    if not is_valid:
        return {
            "status": "validation_failed",
            "errors": errors,
            "constraint": constraint.to_dict(),
        }

    # 获取恢复动作
    recovery_actions = recovery_manager.get_recovery_actions(constraint)

    result = {
        "status": "handling_required",
        "constraint": constraint.to_dict(),
        "recovery_actions": [action.to_dict() for action in recovery_actions],
        "recommendation": "根据约束类型和严重程度执行相应的恢复动作",
    }

    # 根据严重程度添加额外建议
    if constraint.severity == ConstraintSeverity.ERROR:
        result["priority"] = "high"
        result["suggestion"] = "立即执行恢复动作以避免任务失败"
    else:
        result["priority"] = "medium"
        result["suggestion"] = "建议在下次迭代中修复警告"

    return result


# ==================== 测试辅助函数 ====================


def smoke_test_config() -> bool:
    """冒烟测试配置加载"""
    try:
        budget_manager = get_budget_manager()
        disclosure_manager = get_disclosure_manager()
        recovery_manager = get_recovery_manager()

        # 测试预算管理器
        budget = budget_manager.get_budget("build")
        assert budget.max_tokens > 0

        # 测试披露管理器
        layers = disclosure_manager.layers
        assert len(layers) >= 1

        # 测试恢复管理器
        constraint = recovery_manager.create_constraint(
            constraint_type=ConstraintType.SYNTAX,
            severity=ConstraintSeverity.WARNING,
            message="测试约束",
            detection_source="smoke_test",
            violation_context={"test": True},
        )
        assert constraint.message == "测试约束"

        logger.info("上下文预算配置冒烟测试通过")
        return True
    except Exception as e:
        logger.error(f"上下文预算配置冒烟测试失败: {e}")
        return False


if __name__ == "__main__":
    # 命令行接口：运行冒烟测试
    success = smoke_test_config()
    sys.exit(0 if success else 1)
