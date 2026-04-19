#!/usr/bin/env python3
"""
OpenHuman Validation - 验证对象模型与最小引擎

提供统一的验证对象模型（ValidationCase、EvidenceBundle 等）和最小验证引擎。
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ValidationDecision(Enum):
    """验证决策"""

    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVISION = "needs_revision"
    HITL = "hitl"  # 需要人工介入


class RiskLevel(Enum):
    """风险等级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationCase:
    """验证案例"""

    validation_case_id: str
    task_id: str
    stage: str
    risk_level: str  # 使用 RiskLevel 枚举值
    trace_id: Optional[str] = None
    decision: str = ValidationDecision.PASS.value  # 决策枚举值
    decision_reason: str = ""
    applied_rules: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class EvidenceBundle:
    """证据包"""

    task_id: str
    stage: str
    artifact_paths: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)  # 必需字段列表
    missing_fields: List[str] = field(default_factory=list)  # 缺失字段列表
    summary: str = ""
    evidence_data: Dict[str, Any] = field(default_factory=dict)  # 结构化证据数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def check_missing_fields(self) -> List[str]:
        """检查缺失的必需字段，更新 missing_fields"""
        missing = []
        for field_name in self.required_fields:
            if field_name not in self.evidence_data:
                missing.append(field_name)
        self.missing_fields = missing
        return missing


@dataclass
class AcceptanceRule:
    """验收规则"""

    rule_id: str
    description: str
    condition: str  # 条件描述，可以是函数名或规则表达式
    severity: str = "medium"  # high, medium, low
    applies_to_stages: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskPolicy:
    """风险策略"""

    policy_id: str
    stage: str
    risk_level: str  # RiskLevel 枚举值
    hitl_required: bool = False
    approval_policy: str = "default"
    allowed_tools: List[str] = field(default_factory=list)
    evidence_requirements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FailurePattern:
    """失败模式"""

    pattern_id: str
    source_name: str  # failory, google_graveyard, ai_graveyard, cbinsights
    category: str  # 分类：product_market_fit, funding, team, technology, etc.
    signals: List[str] = field(default_factory=list)  # 信号关键词
    risk_hint: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    """验证结果（引擎输出）"""

    decision: str  # ValidationDecision 枚举值
    decision_reason: str
    applied_rules: List[str]
    missing_evidence: List[str]
    risk_flags: List[str]
    validation_case: Optional[ValidationCase] = None
    evidence_bundle: Optional[EvidenceBundle] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "applied_rules": self.applied_rules,
            "missing_evidence": self.missing_evidence,
            "risk_flags": self.risk_flags,
        }
        if self.validation_case:
            result["validation_case"] = self.validation_case.to_dict()
        if self.evidence_bundle:
            result["evidence_bundle"] = self.evidence_bundle.to_dict()
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class OpenHumanValidationEngine:
    """OpenHuman 最小验证引擎"""

    def __init__(self):
        self.rules: Dict[str, AcceptanceRule] = {}
        self.risk_policies: Dict[str, RiskPolicy] = {}
        self.failure_patterns: Dict[str, FailurePattern] = {}
        self._init_defaults()

    def _init_defaults(self):
        """初始化默认规则和策略"""
        # 默认规则
        self.rules = {
            "required_fields_check": AcceptanceRule(
                rule_id="required_fields_check",
                description="检查必需证据字段是否齐全",
                condition="check_required_fields",
                severity="high",
                applies_to_stages=["acceptance", "settlement", "audit"],
                required_fields=[],
            ),
            "status_check": AcceptanceRule(
                rule_id="status_check",
                description="检查状态是否在允许范围内",
                condition="check_status_in",
                severity="medium",
                applies_to_stages=["acceptance"],
                required_fields=["status"],
            ),
            "hitl_check": AcceptanceRule(
                rule_id="hitl_check",
                description="检查是否需要人工介入",
                condition="check_hitl_required",
                severity="high",
                applies_to_stages=["dispatch", "acceptance", "settlement", "audit"],
                required_fields=[],
            ),
            "tool_constraint_check": AcceptanceRule(
                rule_id="tool_constraint_check",
                description="检查工具使用是否符合阶段约束",
                condition="check_tool_constraints",
                severity="medium",
                applies_to_stages=["dispatch", "acceptance", "settlement", "audit"],
                required_fields=["tools_used"],
            ),
        }

        # 默认风险策略（从 stage registry 加载，此处为示例）
        self.risk_policies = {
            "dispatch_high_risk": RiskPolicy(
                policy_id="dispatch_high_risk",
                stage="dispatch",
                risk_level="high",
                hitl_required=True,
                approval_policy="strict",
                allowed_tools=["task_queue", "matching_engine"],
                evidence_requirements=["task_spec", "resource_allocation_plan"],
            ),
            "acceptance_high_risk": RiskPolicy(
                policy_id="acceptance_high_risk",
                stage="acceptance",
                risk_level="high",
                hitl_required=True,
                approval_policy="strict",
                allowed_tools=["validation", "payment_trigger"],
                evidence_requirements=["acceptance_report", "payment_trigger_evidence"],
            ),
        }

    def validate(
        self,
        task_id: str,
        stage: str,
        evidence_bundle: EvidenceBundle,
        stage_config: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        执行验证

        Args:
            task_id: 任务ID
            stage: 阶段ID
            evidence_bundle: 证据包
            stage_config: 阶段配置（可选），包含 allowed_tools、hitl_required、evidence_requirements 等

        Returns:
            ValidationResult: 验证结果
        """
        # 初始化结果
        applied_rules = []
        missing_evidence = []
        risk_flags = []

        # 1. 检查必需证据字段
        missing_fields = evidence_bundle.check_missing_fields()
        if missing_fields:
            missing_evidence.extend(missing_fields)
            applied_rules.append("required_fields_check")

        # 2. 检查状态（如果 evidence_bundle 中有 status 字段）
        if "status" in evidence_bundle.evidence_data:
            status = evidence_bundle.evidence_data.get("status")
            # 简单状态检查：status 应为 "completed" 或 "approved"
            allowed_statuses = ["completed", "approved", "success"]
            if status not in allowed_statuses:
                risk_flags.append(f"status_not_allowed:{status}")
                applied_rules.append("status_check")

        # 3. 检查 HITL 要求（基于 stage_config）
        hitl_required = False
        if stage_config and stage_config.get("hitl_required", False):
            hitl_required = True
            applied_rules.append("hitl_check")
            risk_flags.append("hitl_required")

        # 4. 检查工具约束（如果 evidence_bundle 中有 tools_used）
        if "tools_used" in evidence_bundle.evidence_data and stage_config:
            tools_used = evidence_bundle.evidence_data.get("tools_used", [])
            allowed_tools = stage_config.get("allowed_tools", [])
            # 如果使用了不允许的工具
            disallowed = [tool for tool in tools_used if tool not in allowed_tools]
            if disallowed:
                risk_flags.append(f"disallowed_tools:{disallowed}")
                applied_rules.append("tool_constraint_check")

        # 5. 决策逻辑
        decision = ValidationDecision.PASS.value
        decision_reason = "验证通过"

        if hitl_required:
            decision = ValidationDecision.HITL.value
            decision_reason = "需要人工介入（高风险阶段）"
        elif missing_evidence:
            decision = ValidationDecision.NEEDS_REVISION.value
            decision_reason = f"缺失必需证据字段: {missing_evidence}"
        elif risk_flags and any(
            "disallowed_tools" in flag or "status_not_allowed" in flag for flag in risk_flags
        ):
            decision = ValidationDecision.FAIL.value
            decision_reason = "违反验证规则"

        # 创建验证案例
        validation_case = ValidationCase(
            validation_case_id=f"vc_{task_id}_{stage}",
            task_id=task_id,
            stage=stage,
            risk_level="high" if hitl_required else "medium",
            decision=decision,
            decision_reason=decision_reason,
            applied_rules=applied_rules,
            missing_evidence=missing_evidence,
            risk_flags=risk_flags,
        )

        return ValidationResult(
            decision=decision,
            decision_reason=decision_reason,
            applied_rules=applied_rules,
            missing_evidence=missing_evidence,
            risk_flags=risk_flags,
            validation_case=validation_case,
            evidence_bundle=evidence_bundle,
        )

    def load_failure_patterns_from_source(self, source_name: str) -> List[FailurePattern]:
        """从失败样本源加载失败模式（占位实现）"""
        # 实际实现应从 source_registry.yaml 和相应数据源加载
        return []

    def get_risk_policy_for_stage(self, stage: str) -> Optional[RiskPolicy]:
        """获取阶段的风险策略"""
        for policy in self.risk_policies.values():
            if policy.stage == stage:
                return policy
        return None

    def pre_tool_guardrail(
        self,
        stage_id: str,
        tool_name: str,
        stage_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        前置工具 guardrail 检查，集成 validation_rule_set

        Args:
            stage_id: 阶段ID
            tool_name: 工具名称
            stage_config: 阶段配置（包含 allowed_tools, hitl_required, validation_rule_set 等）

        Returns:
            dict with keys: allowed, decision, reason, validation_rules_applied, policy_violations
        """
        violations = []
        applied_rules = []

        # 1. 检查阶段配置是否存在
        if not stage_config:
            return {
                "allowed": True,
                "decision": "allow",
                "reason": "无阶段配置，默认允许",
                "validation_rules_applied": [],
                "policy_violations": [],
            }

        # 2. 检查工具是否在 allowed_tools 中
        allowed_tools = stage_config.get("allowed_tools", [])
        if allowed_tools and tool_name not in allowed_tools:
            violations.append(f"tool_not_allowed: {tool_name}")
            applied_rules.append("tool_constraint_check")

        # 3. 检查 HITL 要求
        hitl_required = stage_config.get("hitl_required", False)

        # 4. 检查 validation_rule_set 中的规则
        validation_rule_set = stage_config.get("validation_rule_set", [])
        for rule_id in validation_rule_set:
            # 这里可以根据 rule_id 执行特定验证规则
            # 目前简单记录规则应用
            applied_rules.append(f"validation_rule:{rule_id}")

        # 决策逻辑
        if violations:
            if hitl_required:
                return {
                    "allowed": False,
                    "decision": "hitl",
                    "reason": f"需要人工介入: {', '.join(violations)}",
                    "hitl_required": True,
                    "validation_rules_applied": applied_rules,
                    "policy_violations": violations,
                }
            else:
                return {
                    "allowed": False,
                    "decision": "reject",
                    "reason": f"策略违反: {', '.join(violations)}",
                    "hitl_required": False,
                    "validation_rules_applied": applied_rules,
                    "policy_violations": violations,
                }

        # 没有违反策略
        if hitl_required:
            return {
                "allowed": True,
                "decision": "hitl",
                "reason": "阶段需要人工介入",
                "hitl_required": True,
                "validation_rules_applied": applied_rules,
                "policy_violations": [],
            }
        else:
            return {
                "allowed": True,
                "decision": "allow",
                "reason": "工具允许使用",
                "hitl_required": False,
                "validation_rules_applied": applied_rules,
                "policy_violations": [],
            }


# 全局验证引擎实例
_validation_engine_instance: Optional[OpenHumanValidationEngine] = None


def get_validation_engine() -> OpenHumanValidationEngine:
    """获取全局验证引擎实例"""
    global _validation_engine_instance
    if _validation_engine_instance is None:
        _validation_engine_instance = OpenHumanValidationEngine()
    return _validation_engine_instance


if __name__ == "__main__":
    # 测试代码
    print("=== OpenHuman Validation 测试 ===")

    engine = OpenHumanValidationEngine()

    # 测试证据包
    evidence = EvidenceBundle(
        task_id="task_001",
        stage="acceptance",
        artifact_paths=["/tmp/report.pdf"],
        required_fields=["acceptance_report", "payment_trigger_evidence"],
        evidence_data={
            "acceptance_report": "报告内容",
            "status": "completed",
            "tools_used": ["validation"],
        },
    )

    # 测试验证
    stage_config = {
        "hitl_required": True,
        "allowed_tools": ["validation", "payment_trigger"],
        "evidence_requirements": ["acceptance_report", "payment_trigger_evidence"],
    }

    result = engine.validate("task_001", "acceptance", evidence, stage_config)
    print(f"验证结果: {result.decision}")
    print(f"原因: {result.decision_reason}")
    print(f"应用规则: {result.applied_rules}")
    print(f"缺失证据: {result.missing_evidence}")
    print(f"风险标志: {result.risk_flags}")
    print(f"\n完整结果 JSON:")
    print(result.to_json())
