#!/usr/bin/env python3
"""
技能成本估算契约 - 预算化技能执行核心组件

根据技能定义、参数、复杂度估算执行成本，为预算检查提供输入。
与现有 BudgetEngine 集成，提供结构化成本估算。

设计原则：
- 最小闭环：先提供基础成本映射，再逐步引入参数权重和复杂度系数
- 协议优先：定义清晰的成本估算接口，支持未来扩展
- 审计追踪：所有成本估算可审计、可调整
"""

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== 枚举定义 ====================


class CostComponent(Enum):
    """成本构成枚举"""

    BASE = "base"  # 基础成本
    COMPLEXITY = "complexity"  # 复杂度系数
    PARAMETERS = "parameters"  # 参数权重
    EXTERNAL = "external"  # 外部依赖成本
    OVERHEAD = "overhead"  # 系统开销


class ComplexityLevel(Enum):
    """复杂度等级枚举"""

    LOW = "low"  # 低复杂度：简单查询、文档读取
    MEDIUM = "medium"  # 中等复杂度：数据处理、API调用
    HIGH = "high"  # 高复杂度：计算密集型、多步工作流
    CRITICAL = "critical"  # 关键复杂度：涉及外部支付、人工介入


# ==================== 数据类定义 ====================


@dataclass
class CostEstimate:
    """成本估算结果"""

    total: float  # 总成本（元）
    components: Dict[str, float]  # 各组件成本
    confidence: float  # 置信度 (0.0-1.0)
    assumptions: List[str]  # 假设条件
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = asdict(self)
        result["components"] = {k: v for k, v in self.components.items()}
        return result

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class SkillCostRequest:
    """技能成本估算请求"""

    skill_id: str
    skill_metadata: Dict[str, Any]  # 技能元数据（类型、分类等）
    parameters: Optional[Dict[str, Any]] = None  # 执行参数
    context: Optional[Dict[str, Any]] = None  # 执行上下文（任务ID、用户等）
    estimation_mode: str = "default"  # 估算模式：default, conservative, optimistic

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class SkillCostConfig:
    """技能成本配置"""

    base_costs: Dict[str, float]  # 技能基础成本映射（技能ID -> 基础成本）
    complexity_factors: Dict[str, float]  # 复杂度系数映射（复杂度等级 -> 系数）
    parameter_weights: Dict[str, float]  # 参数权重映射（参数类型 -> 权重）
    category_multipliers: Dict[str, float]  # 分类乘数（技能分类 -> 乘数）
    external_cost_rules: Dict[str, Any]  # 外部成本规则

    @classmethod
    def from_dict(cls, data: Dict) -> "SkillCostConfig":
        """从字典创建实例"""
        return cls(
            base_costs=data.get("base_costs", {}),
            complexity_factors=data.get("complexity_factors", {}),
            parameter_weights=data.get("parameter_weights", {}),
            category_multipliers=data.get("category_multipliers", {}),
            external_cost_rules=data.get("external_cost_rules", {}),
        )

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


# ==================== 核心估算器类 ====================


class SkillCostEstimator:
    """技能成本估算器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化成本估算器

        Args:
            config_path: 配置文件路径，默认为 mini-agent/config/skill_costs.yaml
        """
        if config_path is None:
            # 计算默认配置文件路径：mini-agent/config/skill_costs.yaml
            config_path = str(Path(__file__).parent.parent.parent / "config" / "skill_costs.yaml")
        self.config_path = config_path
        self.config = self._load_config()

        logger.info(
            f"技能成本估算器初始化完成，已加载 {len(self.config.base_costs)} 个技能基础成本"
        )

    def _load_config(self) -> SkillCostConfig:
        """加载配置文件"""
        default_config = SkillCostConfig(
            base_costs={
                "openhuman-skill-matcher": 5.0,
                "opencli-scanner": 8.0,
                "humanized-web-scraper": 15.0,
                "openspace-adapter": 10.0,
                "openhuman-cswdp": 0.0,
                "openhuman-geo": 0.0,
            },
            complexity_factors={
                "low": 1.0,
                "medium": 1.5,
                "high": 2.5,
                "critical": 4.0,
            },
            parameter_weights={
                "string": 0.1,
                "number": 0.2,
                "list": 0.3,
                "object": 0.5,
                "file": 1.0,
            },
            category_multipliers={
                "matching": 1.0,
                "web_automation": 1.2,
                "documentation": 0.0,
                "openspace_integration": 1.3,
            },
            external_cost_rules={
                "docker": {"base_cost": 2.0, "per_minute": 0.1},
                "api_call": {"base_cost": 0.5, "per_request": 0.01},
                "human_intervention": {"base_cost": 50.0, "approval_required": True},
            },
        )

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
                return SkillCostConfig.from_dict(config_data)
            except Exception as e:
                logger.warning(f"无法加载技能成本配置 {self.config_path}: {e}，使用默认配置")
                return default_config
        else:
            logger.info(f"技能成本配置文件不存在 {self.config_path}，使用默认配置")
            return default_config

    def save_config(self) -> bool:
        """保存当前配置到文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.config.to_dict(), f, allow_unicode=True, indent=2)
            logger.info(f"技能成本配置已保存到 {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"保存技能成本配置失败: {e}")
            return False

    def estimate_cost(self, request: SkillCostRequest) -> CostEstimate:
        """
        估算技能执行成本

        Args:
            request: 技能成本估算请求

        Returns:
            成本估算结果
        """
        # 初始化组件成本
        components = {}

        # 1. 基础成本
        base_cost = self._get_base_cost(request.skill_id)
        components[CostComponent.BASE.value] = base_cost

        # 2. 复杂度系数
        complexity_factor = self._calculate_complexity_factor(request)
        components[CostComponent.COMPLEXITY.value] = base_cost * (complexity_factor - 1.0)

        # 3. 参数权重
        param_cost = self._calculate_parameter_cost(request)
        components[CostComponent.PARAMETERS.value] = param_cost

        # 4. 外部依赖成本
        external_cost = self._calculate_external_cost(request)
        components[CostComponent.EXTERNAL.value] = external_cost

        # 5. 系统开销（固定百分比）
        overhead = (base_cost + param_cost + external_cost) * 0.1
        components[CostComponent.OVERHEAD.value] = overhead

        # 计算总成本
        total = sum(components.values())

        # 计算置信度
        confidence = self._calculate_confidence(request)

        # 收集假设条件
        assumptions = self._collect_assumptions(request)

        logger.info(
            f"技能成本估算: {request.skill_id} = {total:.2f} 元, "
            f"置信度: {confidence:.1%}, 组件: {components}"
        )

        return CostEstimate(
            total=total,
            components=components,
            confidence=confidence,
            assumptions=assumptions,
            metadata={
                "skill_id": request.skill_id,
                "estimation_mode": request.estimation_mode,
                "timestamp": self._get_timestamp(),
            },
        )

    def _get_base_cost(self, skill_id: str) -> float:
        """获取技能基础成本"""
        # 直接匹配
        if skill_id in self.config.base_costs:
            return self.config.base_costs[skill_id]

        # 尝试小写匹配
        skill_id_lower = skill_id.lower()
        if skill_id_lower in self.config.base_costs:
            return self.config.base_costs[skill_id_lower]

        # 默认成本
        logger.warning(f"技能 {skill_id} 无基础成本配置，使用默认值 10.0")
        return 10.0

    def _calculate_complexity_factor(self, request: SkillCostRequest) -> float:
        """计算复杂度系数"""
        # 默认中等复杂度
        default_complexity = "medium"

        # 基于技能分类判断复杂度
        category = request.skill_metadata.get("category", "")
        if category in ["documentation"]:
            complexity = "low"
        elif category in ["matching", "openspace_integration"]:
            complexity = "medium"
        elif category in ["web_automation"]:
            complexity = "high"
        else:
            complexity = default_complexity

        # 基于参数数量调整
        if request.parameters and len(request.parameters) > 5:
            # 参数多则复杂度提高一级
            if complexity == "low":
                complexity = "medium"
            elif complexity == "medium":
                complexity = "high"
            elif complexity == "high":
                complexity = "critical"

        # 获取系数
        factor = self.config.complexity_factors.get(complexity, 1.0)

        # 应用分类乘数
        if category in self.config.category_multipliers:
            factor *= self.config.category_multipliers[category]

        return factor

    def _calculate_parameter_cost(self, request: SkillCostRequest) -> float:
        """计算参数成本"""
        if not request.parameters:
            return 0.0

        total = 0.0
        for param_name, param_value in request.parameters.items():
            # 简单估算：基于参数类型
            param_type = type(param_value).__name__
            weight = self.config.parameter_weights.get(param_type, 0.1)

            # 考虑参数值大小
            if isinstance(param_value, (list, dict)):
                size = len(param_value)
                weight *= min(1.0 + size * 0.1, 3.0)  # 上限3倍

            total += weight

        return total

    def _calculate_external_cost(self, request: SkillCostRequest) -> float:
        """计算外部依赖成本"""
        # 简化的外部成本估算
        # 实际实现应检查技能依赖（docker、API等）
        skill_id = request.skill_id

        # 基于技能ID的简单规则
        if "docker" in skill_id.lower():
            rule = self.config.external_cost_rules.get("docker", {})
            return rule.get("base_cost", 2.0)
        elif "api" in skill_id.lower() or "web" in skill_id.lower():
            rule = self.config.external_cost_rules.get("api_call", {})
            return rule.get("base_cost", 0.5)
        elif "human" in skill_id.lower():
            rule = self.config.external_cost_rules.get("human_intervention", {})
            return rule.get("base_cost", 50.0)

        return 0.0

    def _calculate_confidence(self, request: SkillCostRequest) -> float:
        """计算估算置信度"""
        confidence = 0.8  # 基础置信度

        # 有配置的技能置信度更高
        if request.skill_id in self.config.base_costs:
            confidence += 0.1

        # 有历史数据的置信度更高（暂未实现）
        # 参数简单的置信度更高
        if request.parameters and len(request.parameters) <= 3:
            confidence += 0.05

        # 限制在0.0-1.0之间
        return max(0.0, min(1.0, confidence))

    def _collect_assumptions(self, request: SkillCostRequest) -> List[str]:
        """收集假设条件"""
        assumptions = []

        # 基础成本假设
        if request.skill_id not in self.config.base_costs:
            assumptions.append(f"技能 {request.skill_id} 使用默认基础成本")

        # 复杂度假设
        category = request.skill_metadata.get("category", "")
        if category not in self.config.category_multipliers:
            assumptions.append(f"技能分类 {category} 使用默认乘数 1.0")

        # 外部依赖假设
        if "docker" in request.skill_id.lower():
            assumptions.append("假设Docker容器运行时间在预期范围内")

        # 参数假设
        if request.parameters and len(request.parameters) > 5:
            assumptions.append("多参数可能增加实际执行成本")

        return assumptions

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime

        return datetime.now().isoformat()

    def update_base_cost(self, skill_id: str, cost: float) -> bool:
        """更新技能基础成本"""
        self.config.base_costs[skill_id] = max(0.0, cost)
        logger.info(f"更新技能基础成本: {skill_id} = {cost:.2f}")
        return self.save_config()

    def get_cost_report(self) -> Dict[str, Any]:
        """获取成本配置报告"""
        return {
            "config_summary": {
                "skill_count": len(self.config.base_costs),
                "complexity_levels": len(self.config.complexity_factors),
                "parameter_types": len(self.config.parameter_weights),
                "categories": len(self.config.category_multipliers),
            },
            "sample_costs": {
                skill_id: cost for skill_id, cost in list(self.config.base_costs.items())[:5]
            },
            "config_path": self.config_path,
            "config_exists": os.path.exists(self.config_path),
        }


# ==================== 全局单例实例 ====================

_estimator_instance: Optional[SkillCostEstimator] = None


def get_cost_estimator() -> SkillCostEstimator:
    """获取全局成本估算器实例"""
    global _estimator_instance
    if _estimator_instance is None:
        _estimator_instance = SkillCostEstimator()
    return _estimator_instance


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=== Skill Cost Estimator 测试 ===")

    estimator = SkillCostEstimator()

    print("\n1. 配置报告:")
    report = estimator.get_cost_report()
    print(f"   技能数量: {report['config_summary']['skill_count']}")
    print(f"   配置文件存在: {report['config_exists']}")
    print(f"   示例成本: {report['sample_costs']}")

    print("\n2. 测试成本估算:")

    test_requests = [
        SkillCostRequest(
            skill_id="openhuman-skill-matcher",
            skill_metadata={"category": "matching"},
            parameters={
                "profile_skills": ["Python", "React"],
                "required_skills": ["Python", "AWS"],
            },
        ),
        SkillCostRequest(
            skill_id="opencli-scanner",
            skill_metadata={"category": "web_automation"},
            parameters={"url": "https://example.com", "scan_type": "structure"},
        ),
        SkillCostRequest(
            skill_id="humanized-web-scraper",
            skill_metadata={"category": "web_automation"},
            parameters={"url": "https://example.com", "form_selector": "#login-form"},
        ),
        SkillCostRequest(
            skill_id="openhuman-cswdp",
            skill_metadata={"category": "documentation"},
            parameters={},
        ),
    ]

    for req in test_requests:
        estimate = estimator.estimate_cost(req)
        print(f"\n   技能: {req.skill_id}")
        print(f"     总成本: {estimate.total:.2f} 元")
        print(f"     置信度: {estimate.confidence:.1%}")
        print(f"     组件: {estimate.components}")

    print("\n3. 测试配置更新:")
    success = estimator.update_base_cost("test-skill", 25.0)
    print(f"   更新结果: {'成功' if success else '失败'}")

    print("\n=== 测试完成 ===")
