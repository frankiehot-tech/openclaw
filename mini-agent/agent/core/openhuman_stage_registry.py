#!/usr/bin/env python3
"""
OpenHuman Stage Registry - OpenHuman 阶段注册表

记录 OpenHuman 各阶段的定义、执行器、产物模板等信息。
Phase 1 仅完成阶段定义和路由，不包含业务执行器。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StageDefinition:
    """阶段定义"""

    id: str
    label: str
    description: str
    domain: str = "openhuman"
    executable: bool = False  # Phase 1 未实现业务执行器
    executor: str = "unknown"
    expected_artifact: str = ""
    dependencies: List[str] = field(default_factory=list)
    gate_conditions: List[Dict[str, str]] = field(default_factory=list)

    # --- P0 新增字段 ---
    allowed_tools: List[str] = field(default_factory=list)
    hitl_required: bool = False
    approval_policy: str = "default"  # default, strict, relaxed
    model_policy: Optional[str] = None  # 指定允许的 provider/model
    evidence_requirements: List[str] = field(default_factory=list)  # 必需证据字段列表
    validation_rule_set: List[str] = field(default_factory=list)  # 验证规则集标识符
    # --- P0 新增字段结束 ---

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "domain": self.domain,
            "executable": self.executable,
            "executor": self.executor,
            "expected_artifact": self.expected_artifact,
            "dependencies": self.dependencies,
            "gate_conditions": self.gate_conditions,
            # --- P0 新增字段 ---
            "allowed_tools": self.allowed_tools,
            "hitl_required": self.hitl_required,
            "approval_policy": self.approval_policy,
            "model_policy": self.model_policy,
            "evidence_requirements": self.evidence_requirements,
            "validation_rule_set": self.validation_rule_set,
            # --- P0 新增字段结束 ---
        }


class OpenHumanStageRegistry:
    """OpenHuman 阶段注册表"""

    def __init__(self):
        self.stages: Dict[str, StageDefinition] = {}
        self._init_stages()

    def _init_stages(self):
        """初始化阶段定义"""
        stages_data = [
            {
                "id": "distill",
                "label": "提炼",
                "description": "从经验、对话、文档中提炼可复用知识",
                "executable": False,
                "executor": "knowledge_distiller",
                "expected_artifact": "提炼报告、知识卡片",
                "allowed_tools": ["knowledge_distillation", "llm_call"],
                "hitl_required": False,
                "approval_policy": "relaxed",
                "model_policy": "minimax",  # 专用蒸馏模型
                "evidence_requirements": [],
                "validation_rule_set": [],
            },
            {
                "id": "skill_design",
                "label": "技能设计",
                "description": "设计技能模板、参数schema、执行流程",
                "executable": False,
                "executor": "skill_designer",
                "expected_artifact": "技能定义文件、参数模板",
                "allowed_tools": ["skill_registry", "schema_design"],
                "hitl_required": False,
                "approval_policy": "default",
                "model_policy": None,
                "evidence_requirements": [],
                "validation_rule_set": [],
            },
            {
                "id": "dispatch",
                "label": "任务分发",
                "description": "发布任务、匹配执行者、分配资源",
                "executable": False,
                "executor": "task_dispatcher",
                "expected_artifact": "任务发布记录、匹配结果",
                "allowed_tools": ["task_queue", "matching_engine"],
                "hitl_required": True,  # 高风险：发布任务涉及资源分配
                "approval_policy": "strict",
                "model_policy": "dashscope",  # 必须使用可信模型
                "evidence_requirements": ["task_spec", "resource_allocation_plan"],
                "validation_rule_set": ["dispatch_risk_check"],
            },
            {
                "id": "acceptance",
                "label": "验收结算",
                "description": "验收任务成果、确认完成、触发结算",
                "executable": False,
                "executor": "acceptance_validator",
                "expected_artifact": "验收报告、结算触发凭证",
                "allowed_tools": ["validation", "payment_trigger"],
                "hitl_required": True,  # 高风险：验收触发支付
                "approval_policy": "strict",
                "model_policy": "dashscope",
                "evidence_requirements": [
                    "acceptance_report",
                    "payment_trigger_evidence",
                ],
                "validation_rule_set": ["acceptance_validation"],
            },
            {
                "id": "settlement",
                "label": "结算分账",
                "description": "计算报酬、分账、支付结算",
                "executable": False,
                "executor": "settlement_engine",
                "expected_artifact": "结算单、支付记录",
                "allowed_tools": ["payment_calculator", "ledger"],
                "hitl_required": True,  # 高风险：直接涉及资金
                "approval_policy": "strict",
                "model_policy": "dashscope",
                "evidence_requirements": ["payment_calculation", "ledger_entry"],
                "validation_rule_set": ["settlement_validation"],
            },
            {
                "id": "audit",
                "label": "审计追溯",
                "description": "审计任务流程、追溯执行记录、生成审计报告",
                "executable": False,
                "executor": "audit_tracker",
                "expected_artifact": "审计报告、追溯记录",
                "allowed_tools": ["log_analysis", "report_generator"],
                "hitl_required": True,  # 高风险：审计涉及敏感数据
                "approval_policy": "strict",
                "model_policy": "dashscope",
                "evidence_requirements": ["audit_logs", "sensitive_data_handling"],
                "validation_rule_set": ["audit_validation"],
            },
        ]

        for data in stages_data:
            stage = StageDefinition(
                id=data["id"],
                label=data["label"],
                description=data["description"],
                executable=data["executable"],
                executor=data["executor"],
                expected_artifact=data["expected_artifact"],
                allowed_tools=data.get("allowed_tools", []),
                hitl_required=data.get("hitl_required", False),
                approval_policy=data.get("approval_policy", "default"),
                model_policy=data.get("model_policy"),
                evidence_requirements=data.get("evidence_requirements", []),
                validation_rule_set=data.get("validation_rule_set", []),
            )
            self.stages[data["id"]] = stage

    def get_stage(self, stage_id: str) -> Optional[StageDefinition]:
        """获取阶段定义"""
        return self.stages.get(stage_id)

    def list_stages(self) -> List[StageDefinition]:
        """列出所有阶段"""
        return list(self.stages.values())

    def get_stage_info(self, stage_id: str) -> Dict[str, Any]:
        """获取阶段信息（字典形式）"""
        stage = self.get_stage(stage_id)
        if stage:
            return stage.to_dict()
        return {"error": f"阶段不存在: {stage_id}"}

    def is_executable(self, stage_id: str) -> bool:
        """检查阶段是否可执行（业务执行器是否已实现）"""
        stage = self.get_stage(stage_id)
        if stage:
            return stage.executable
        return False

    def check_tool_guardrail(self, stage_id: str, tool_name: str) -> Dict[str, Any]:
        """
        检查工具在指定阶段是否允许使用（前置授权检查）

        Args:
            stage_id: 阶段ID
            tool_name: 工具名称

        Returns:
            dict with keys: allowed, decision, reason, hitl_required, policy_violations
        """
        stage = self.get_stage(stage_id)
        if not stage:
            return {
                "allowed": False,
                "decision": "reject",
                "reason": f"阶段不存在: {stage_id}",
                "hitl_required": False,
                "policy_violations": ["stage_not_found"],
            }

        violations = []

        # 1. 检查工具是否在 allowed_tools 中
        if stage.allowed_tools and tool_name not in stage.allowed_tools:
            violations.append(f"tool_not_allowed: {tool_name} not in {stage.allowed_tools}")

        # 2. 检查 HITL 要求
        hitl_required = stage.hitl_required

        # 3. 检查审批策略
        approval_policy = stage.approval_policy

        # 决策逻辑
        if violations:
            if hitl_required:
                return {
                    "allowed": False,
                    "decision": "hitl",
                    "reason": f"需要人工介入: {', '.join(violations)}",
                    "hitl_required": True,
                    "policy_violations": violations,
                    "stage_config": {
                        "allowed_tools": stage.allowed_tools,
                        "hitl_required": stage.hitl_required,
                        "approval_policy": approval_policy,
                    },
                }
            else:
                return {
                    "allowed": False,
                    "decision": "reject",
                    "reason": f"策略违反: {', '.join(violations)}",
                    "hitl_required": False,
                    "policy_violations": violations,
                    "stage_config": {
                        "allowed_tools": stage.allowed_tools,
                        "hitl_required": stage.hitl_required,
                        "approval_policy": approval_policy,
                    },
                }

        # 没有违反策略
        if hitl_required:
            return {
                "allowed": True,
                "decision": "hitl",
                "reason": "阶段需要人工介入",
                "hitl_required": True,
                "policy_violations": [],
                "stage_config": {
                    "allowed_tools": stage.allowed_tools,
                    "hitl_required": stage.hitl_required,
                    "approval_policy": approval_policy,
                },
            }
        else:
            return {
                "allowed": True,
                "decision": "allow",
                "reason": "工具允许使用",
                "hitl_required": False,
                "policy_violations": [],
                "stage_config": {
                    "allowed_tools": stage.allowed_tools,
                    "hitl_required": stage.hitl_required,
                    "approval_policy": approval_policy,
                },
            }

    def get_phase1_summary(self) -> Dict[str, Any]:
        """获取 Phase 1 实现总结"""
        total = len(self.stages)
        executable = sum(1 for stage in self.stages.values() if stage.executable)

        return {
            "phase": 1,
            "description": "OpenHuman 领域路由与任务建模完成",
            "total_stages": total,
            "executable_stages": executable,
            "non_executable_stages": total - executable,
            "implementation_status": "阶段定义、路由识别、任务建模已完成；业务执行器未实现",
            "notes": [
                "Phase 1 完成了 OpenHuman 6 个阶段的定义和路由识别",
                "阶段已接入 Athena 运行时，通过桥接层映射到通用工程阶段",
                "业务执行器（dispatch/acceptance/settlement/audit 等）尚未实现",
                "当前为降级执行：OpenHuman 阶段映射到 think/plan/review 等通用阶段",
            ],
        }


# 全局注册表实例
_registry_instance: Optional[OpenHumanStageRegistry] = None


def get_registry() -> OpenHumanStageRegistry:
    """获取全局注册表实例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = OpenHumanStageRegistry()
    return _registry_instance


if __name__ == "__main__":
    # 测试代码
    print("=== OpenHuman Stage Registry 测试 ===")

    registry = OpenHumanStageRegistry()

    print(f"\n1. 阶段数量: {len(registry.stages)}")

    print("\n2. 阶段列表:")
    for stage in registry.list_stages():
        executable_flag = "✓" if stage.executable else "✗"
        print(f"  {executable_flag} {stage.id}: {stage.label}")
        print(f"     描述: {stage.description}")
        print(f"     执行器: {stage.executor}")
        print(f"     预期产物: {stage.expected_artifact}")

    print("\n3. 阶段信息查询:")
    for stage_id in ["distill", "dispatch", "settlement"]:
        info = registry.get_stage_info(stage_id)
        print(f"  {stage_id}: {info.get('label', 'N/A')}")

    print("\n4. 可执行性检查:")
    for stage_id in ["distill", "dispatch"]:
        executable = registry.is_executable(stage_id)
        print(f"  {stage_id}: {'可执行' if executable else '不可执行'}")

    print("\n5. Phase 1 总结:")
    summary = registry.get_phase1_summary()
    for key, value in summary.items():
        if isinstance(value, list):
            print(f"  {key}:")
            for item in value:
                print(f"    - {item}")
        else:
            print(f"  {key}: {value}")
