#!/usr/bin/env python3
"""
SubAgent Registry - 子代理注册表

定义子代理角色、工具边界、产出契约，为 SubAgentBus 提供角色型约束。
基于现有 stage registry 模式扩展，但专注角色而非阶段。
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SubAgentRole(Enum):
    """子代理角色枚举"""

    PLANNER = "planner"  # 规划者：制定方案、拆解任务
    RESEARCHER = "researcher"  # 研究者：调研分析、信息收集
    BUILD_WORKER = "build_worker"  # 构建者：执行构建、编写代码
    REVIEWER = "reviewer"  # 审查者：审查评估、质量检查
    VALIDATOR = "validator"  # 验证者：验证结果、验收测试
    # 兼容现有角色
    BUILDER = "builder"  # 构建者（旧称）
    OPERATOR = "operator"  # 运维者（旧称）


@dataclass
class RoleDefinition:
    """角色定义"""

    id: str  # 角色ID（与 SubAgentRole 值一致）
    label: str  # 显示标签
    description: str  # 角色描述
    default_responsibilities: List[str] = field(default_factory=list)  # 默认职责列表
    allowed_tools: List[str] = field(default_factory=list)  # 允许使用的工具列表
    denied_tools: List[str] = field(default_factory=list)  # 显式禁止的工具列表
    output_schema: Dict[str, Any] = field(default_factory=dict)  # 产出契约 schema
    # 产出契约要求：至少包含的字段
    required_output_fields: List[str] = field(default_factory=list)
    handoff_protocol: str = "structured_json"  # handoff 协议类型

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "default_responsibilities": self.default_responsibilities,
            "allowed_tools": self.allowed_tools,
            "denied_tools": self.denied_tools,
            "output_schema": self.output_schema,
            "required_output_fields": self.required_output_fields,
            "handoff_protocol": self.handoff_protocol,
        }


class SubAgentRegistry:
    """子代理注册表"""

    def __init__(self):
        self.roles: Dict[str, RoleDefinition] = {}
        self._init_roles()

    def _init_roles(self):
        """初始化角色定义"""
        # 工具分类定义（参考当前系统可用工具）
        # 核心工具（所有角色默认允许，除非显式禁止）
        core_tools = ["read", "glob", "grep", "todowrite", "todoread"]
        # 高风险工具（需角色显式允许）
        high_risk_tools = ["bash", "edit", "write", "webfetch", "task", "skill"]
        # 特殊技能工具
        skill_tools = [
            "openhuman-skill-matcher",
            "opencli-scanner",
            "humanized-web-scraper",
        ]

        roles_data = [
            {
                "id": "planner",
                "label": "规划者",
                "description": "制定方案、拆解任务、定义验收标准",
                "default_responsibilities": [
                    "任务拆解与依赖分析",
                    "制定实施方案与时间预估",
                    "定义验收标准与成功指标",
                    "资源规划与风险识别",
                ],
                "allowed_tools": core_tools + ["webfetch", "task"],  # 可调研、可委派任务
                "denied_tools": ["bash", "edit", "write"],  # 不能直接修改代码
                "required_output_fields": [
                    "plan",
                    "tasks",
                ],
                "output_schema": {
                    "type": "object",
                    "required": ["plan", "tasks"],
                    "properties": {
                        "plan": {"type": "string", "description": "总体方案描述"},
                        "tasks": {"type": "array", "description": "拆解后的任务列表"},
                        "dependencies": {
                            "type": "array",
                            "description": "任务依赖关系",
                        },
                        "acceptance_criteria": {
                            "type": "array",
                            "description": "验收标准",
                        },
                        "estimated_time": {
                            "type": "number",
                            "description": "预估时间（小时）",
                        },
                        "risks": {"type": "array", "description": "风险列表"},
                    },
                },
            },
            {
                "id": "researcher",
                "label": "研究者",
                "description": "调研分析、信息收集、竞品研究",
                "default_responsibilities": [
                    "收集相关技术资料与文档",
                    "分析竞品与行业最佳实践",
                    "整理调研报告与关键发现",
                    "提出技术选型建议",
                ],
                "allowed_tools": core_tools + ["webfetch", "task"],  # 可搜索、可委派任务
                "denied_tools": ["bash", "edit", "write"],  # 不能直接修改代码
                "required_output_fields": [
                    "research_topic",
                    "findings",
                ],
                "output_schema": {
                    "type": "object",
                    "required": ["research_topic", "findings"],
                    "properties": {
                        "research_topic": {"type": "string", "description": "研究主题"},
                        "findings": {"type": "array", "description": "研究发现"},
                        "sources": {"type": "array", "description": "信息来源"},
                        "confidence_score": {
                            "type": "number",
                            "description": "置信度评分 0-1",
                        },
                        "recommendations": {"type": "array", "description": "建议行动"},
                    },
                },
            },
            {
                "id": "build_worker",
                "label": "构建者",
                "description": "执行构建、编写代码、运行测试",
                "default_responsibilities": [
                    "根据方案实现代码",
                    "编写单元测试与集成测试",
                    "执行构建与打包",
                    "修复代码缺陷",
                ],
                "allowed_tools": core_tools
                + ["bash", "edit", "write", "skill"],  # 可执行命令、编辑文件、调用技能
                "denied_tools": [],  # 构建者需要高风险工具
                "required_output_fields": [
                    "component",
                    "build_status",
                ],
                "output_schema": {
                    "type": "object",
                    "required": ["component", "build_status"],
                    "properties": {
                        "component": {"type": "string", "description": "组件名称"},
                        "build_status": {"type": "string", "description": "构建状态"},
                        "artifacts": {"type": "array", "description": "产出物列表"},
                        "tests_passed": {
                            "type": "boolean",
                            "description": "测试是否通过",
                        },
                        "code_coverage": {
                            "type": "number",
                            "description": "代码覆盖率",
                        },
                        "warnings": {"type": "array", "description": "警告列表"},
                    },
                },
            },
            {
                "id": "reviewer",
                "label": "审查者",
                "description": "审查评估、质量检查、代码审查",
                "default_responsibilities": [
                    "代码质量审查",
                    "安全漏洞扫描",
                    "性能评估",
                    "架构合规性检查",
                ],
                "allowed_tools": core_tools + ["webfetch"],  # 可搜索参考，不能修改代码
                "denied_tools": ["bash", "edit", "write"],  # 审查者不能修改代码
                "required_output_fields": [
                    "review_target",
                    "review_status",
                ],
                "output_schema": {
                    "type": "object",
                    "required": ["review_target", "review_status"],
                    "properties": {
                        "review_target": {"type": "string", "description": "审查目标"},
                        "review_status": {"type": "string", "description": "审查状态"},
                        "findings": {"type": "array", "description": "审查发现"},
                        "issues_found": {"type": "integer", "description": "问题数量"},
                        "critical_issues": {
                            "type": "integer",
                            "description": "严重问题数量",
                        },
                        "recommendations": {"type": "array", "description": "改进建议"},
                        "approval": {"type": "boolean", "description": "是否批准"},
                    },
                },
            },
            {
                "id": "validator",
                "label": "验证者",
                "description": "验证结果、验收测试、性能验证",
                "default_responsibilities": [
                    "执行验收测试",
                    "验证性能指标",
                    "检查安全合规性",
                    "生成验证报告",
                ],
                "allowed_tools": core_tools + ["bash", "skill"],  # 可执行测试命令，调用验证技能
                "denied_tools": ["edit", "write"],  # 不能修改代码
                "required_output_fields": [
                    "validation_target",
                    "validation_status",
                ],
                "output_schema": {
                    "type": "object",
                    "required": ["validation_target", "validation_status"],
                    "properties": {
                        "validation_target": {
                            "type": "string",
                            "description": "验证目标",
                        },
                        "validation_status": {
                            "type": "string",
                            "description": "验证状态",
                        },
                        "metrics": {"type": "object", "description": "验证指标"},
                        "passed": {"type": "boolean", "description": "是否通过"},
                        "failures": {"type": "array", "description": "失败项"},
                        "evidence": {"type": "array", "description": "证据文件列表"},
                    },
                },
            },
            # 兼容现有角色
            {
                "id": "builder",
                "label": "构建者（旧称）",
                "description": "构建实现（兼容现有 SubAgentBus 角色）",
                "default_responsibilities": [
                    "根据方案实现代码",
                    "编写单元测试与集成测试",
                    "执行构建与打包",
                ],
                "allowed_tools": core_tools + ["bash", "edit", "write", "skill"],
                "denied_tools": [],
                "required_output_fields": ["component", "build_status", "artifacts"],
                "output_schema": {
                    "type": "object",
                    "required": ["component", "build_status"],
                    "properties": {
                        "component": {"type": "string", "description": "组件名称"},
                        "build_status": {"type": "string", "description": "构建状态"},
                        "artifacts": {"type": "array", "description": "产出物列表"},
                    },
                },
            },
            {
                "id": "operator",
                "label": "运维者",
                "description": "运维执行、部署发布、监控响应",
                "default_responsibilities": [
                    "执行部署操作",
                    "监控系统状态",
                    "响应故障事件",
                    "执行运维脚本",
                ],
                "allowed_tools": core_tools + ["bash", "skill"],
                "denied_tools": ["edit", "write"],  # 不能修改代码，但可执行命令
                "required_output_fields": ["operation", "status", "output", "metrics"],
                "output_schema": {
                    "type": "object",
                    "required": ["operation", "status"],
                    "properties": {
                        "operation": {"type": "string", "description": "操作名称"},
                        "status": {"type": "string", "description": "执行状态"},
                        "output": {"type": "string", "description": "输出结果"},
                        "metrics": {"type": "object", "description": "执行指标"},
                        "logs": {"type": "array", "description": "日志条目"},
                    },
                },
            },
        ]

        for data in roles_data:
            role = RoleDefinition(
                id=data["id"],
                label=data["label"],
                description=data["description"],
                default_responsibilities=data.get("default_responsibilities", []),
                allowed_tools=data.get("allowed_tools", []),
                denied_tools=data.get("denied_tools", []),
                output_schema=data.get("output_schema", {}),
                required_output_fields=data.get("required_output_fields", []),
                handoff_protocol=data.get("handoff_protocol", "structured_json"),
            )
            self.roles[data["id"]] = role

    def get_role(self, role_id: str) -> Optional[RoleDefinition]:
        """获取角色定义"""
        return self.roles.get(role_id)

    def list_roles(self) -> List[RoleDefinition]:
        """列出所有角色"""
        return list(self.roles.values())

    def check_tool_guardrail(self, role_id: str, tool_name: str) -> Dict[str, Any]:
        """
        检查工具在指定角色下是否允许使用

        Args:
            role_id: 角色ID
            tool_name: 工具名称

        Returns:
            dict with keys: allowed, decision, reason, policy_violations
        """
        role = self.get_role(role_id)
        if not role:
            return {
                "allowed": False,
                "decision": "reject",
                "reason": f"角色不存在: {role_id}",
                "policy_violations": ["role_not_found"],
                "role_id": role_id,
                "tool_name": tool_name,
            }

        violations = []

        # 1. 检查工具是否在显式禁止列表中
        if tool_name in role.denied_tools:
            violations.append(f"tool_explicitly_denied: {tool_name} in denied_tools")

        # 2. 检查工具是否在允许列表中（如果允许列表非空）
        if role.allowed_tools and tool_name not in role.allowed_tools:
            violations.append(f"tool_not_in_allowed_list: {tool_name} not in {role.allowed_tools}")

        # 决策逻辑
        if violations:
            return {
                "allowed": False,
                "decision": "reject",
                "reason": f"工具使用违反策略: {', '.join(violations)}",
                "policy_violations": violations,
                "role_id": role_id,
                "tool_name": tool_name,
                "role_config": {
                    "allowed_tools": role.allowed_tools,
                    "denied_tools": role.denied_tools,
                },
            }
        else:
            return {
                "allowed": True,
                "decision": "allow",
                "reason": "工具允许使用",
                "policy_violations": [],
                "role_id": role_id,
                "tool_name": tool_name,
                "role_config": {
                    "allowed_tools": role.allowed_tools,
                    "denied_tools": role.denied_tools,
                },
            }

    def validate_output_schema(
        self, role_id: str, output_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        验证产出是否符合角色产出契约（简化实现）

        Args:
            role_id: 角色ID
            output_data: 产出数据

        Returns:
            (valid, errors)
        """
        role = self.get_role(role_id)
        if not role:
            return False, [f"角色不存在: {role_id}"]

        errors = []

        # 检查必需字段
        for field in role.required_output_fields:
            if field not in output_data:
                errors.append(f"缺少必需字段: {field}")

        # 简单类型检查（可选）
        # 这里可以扩展为完整的 JSON schema 验证

        return len(errors) == 0, errors

    def get_role_summary(self) -> Dict[str, Any]:
        """获取角色摘要"""
        total = len(self.roles)
        return {
            "total_roles": total,
            "roles": [role.to_dict() for role in self.roles.values()],
            "tool_boundary_enabled": True,
            "output_schema_enabled": True,
        }

    def map_stage_to_role(self, stage: str) -> Optional[str]:
        """
        将工程阶段映射到子代理角色

        Args:
            stage: 工程阶段 (plan, build, review, think, qa, browse)

        Returns:
            角色ID，如果阶段不支持则返回 None
        """
        stage_to_role = {
            "plan": "planner",
            "build": "build_worker",
            "review": "reviewer",
            "think": "researcher",
            "qa": "validator",
            "browse": "researcher",
        }
        return stage_to_role.get(stage)


# 全局注册表实例
_registry_instance: Optional[SubAgentRegistry] = None


def get_registry() -> SubAgentRegistry:
    """获取全局注册表实例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = SubAgentRegistry()
    return _registry_instance


if __name__ == "__main__":
    # 测试代码
    print("=== SubAgent Registry 测试 ===")

    registry = SubAgentRegistry()

    print(f"\n1. 角色数量: {len(registry.roles)}")

    print("\n2. 角色列表:")
    for role in registry.list_roles():
        print(f"  {role.id}: {role.label}")
        print(f"     描述: {role.description}")
        print(f"     允许工具: {len(role.allowed_tools)} 个")
        print(f"     禁止工具: {len(role.denied_tools)} 个")

    print("\n3. 工具边界检查:")
    test_cases = [
        ("planner", "bash"),
        ("planner", "webfetch"),
        ("build_worker", "bash"),
        ("build_worker", "edit"),
        ("reviewer", "edit"),
        ("validator", "bash"),
        ("validator", "write"),
    ]
    for role_id, tool_name in test_cases:
        result = registry.check_tool_guardrail(role_id, tool_name)
        allowed_icon = "✓" if result["allowed"] else "✗"
        print(f"  {allowed_icon} {role_id}.{tool_name}: {result['reason']}")

    print("\n4. 产出契约验证:")
    test_outputs = [
        ("planner", {"plan": "测试方案", "tasks": ["任务1", "任务2"]}),
        ("planner", {"tasks": ["任务1"]}),  # 缺少 plan
        ("build_worker", {"component": "test", "build_status": "success"}),
    ]
    for role_id, output in test_outputs:
        valid, errors = registry.validate_output_schema(role_id, output)
        valid_icon = "✓" if valid else "✗"
        print(f"  {valid_icon} {role_id}: {output}")
        if errors:
            print(f"     错误: {errors}")

    print("\n5. 角色摘要:")
    summary = registry.get_role_summary()
    print(f"  总角色数: {summary['total_roles']}")
    print(f"  工具边界启用: {summary['tool_boundary_enabled']}")
    print(f"  产出契约启用: {summary['output_schema_enabled']}")

    print("\n✅ SubAgent Registry 测试完成")
