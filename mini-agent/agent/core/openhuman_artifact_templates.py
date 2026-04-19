#!/usr/bin/env python3
"""
OpenHuman Artifact Templates - OpenHuman 领域产物模板

为 OpenHuman 6个阶段提供标准化的产物模板。
Phase 1 仅提供模板结构，不包含实际业务执行逻辑。

模板使用要求：
1. 模板包含 ${variable} 占位符，运行时填充
2. 每个阶段有对应的默认模板
3. 支持自定义模板扩展
4. 模板与阶段注册表的 expected_artifact 字段对齐

文档参考：
- DOMAIN_MODEL.md：领域对象定义
- OPENHUMAN_RUNTIME_CONTRACTS.md：运行时契约
- openhuman_stage_registry.py：阶段定义
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ArtifactTemplate:
    """产物模板定义"""

    stage_id: str
    stage_label: str
    template_name: str = "default"
    description: str = ""
    content_template: str = ""
    required_fields: List[str] = field(default_factory=list)
    metadata_schema: Dict[str, Any] = field(default_factory=dict)

    def render(self, context: Dict[str, Any]) -> str:
        """
        渲染模板

        Args:
            context: 包含 ${variable} 替换值的上下文

        Returns:
            渲染后的内容
        """
        if not self.content_template:
            return ""

        # 简单变量替换
        content = self.content_template
        for key, value in context.items():
            placeholder = f"${{{key}}}"
            if placeholder in content:
                content = content.replace(placeholder, str(value))

        return content

    def validate_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证上下文并返回缺失的必需字段

        Args:
            context: 待验证的上下文

        Returns:
            {"valid": bool, "missing_fields": List[str], "extra_fields": List[str]}
        """
        missing = []
        extra = []

        # 检查必需字段
        for field_name in self.required_fields:
            if field_name not in context:
                missing.append(field_name)

        # 检查模板中引用的字段
        template_fields = re.findall(r"\$\{(\w+)\}", self.content_template)
        for field_name in template_fields:
            if field_name not in context and field_name not in missing:
                missing.append(field_name)

        # 检查多余的字段（非必需且模板未引用）
        for field_name in context.keys():
            if field_name not in self.required_fields and field_name not in template_fields:
                extra.append(field_name)

        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
            "extra_fields": extra,
            "template_fields": template_fields,
        }


class OpenHumanArtifactTemplates:
    """OpenHuman 产物模板管理器"""

    def __init__(self):
        self.templates: Dict[str, ArtifactTemplate] = {}
        self._init_templates()

    def _init_templates(self):
        """初始化所有阶段的默认模板"""

        # distill（提炼）阶段模板
        distill_template = ArtifactTemplate(
            stage_id="distill",
            stage_label="提炼",
            description="从经验文档中提炼可复用知识的报告模板",
            required_fields=["source_document", "distilled_by", "distillation_date"],
            content_template="""# 提炼报告 - ${distillation_date}

## 1. 源文档信息
- **文档标题**: ${source_document_title}
- **文档来源**: ${source_document_source}
- **文档类型**: ${source_document_type}
- **提取时间**: ${distillation_date}
- **提炼人员**: ${distilled_by}

## 2. 提炼摘要
${distillation_summary}

## 3. 关键知识点提取
${key_points}

## 4. 可复用模式识别
${reusable_patterns}

## 5. 建议技能封装
${skill_encapsulation_suggestions}

## 6. 质量评估
- **完整性**: ${completeness_score}/10
- **准确性**: ${accuracy_score}/10
- **可复用性**: ${reusability_score}/10
- **总体评估**: ${overall_assessment}

## 7. 后续行动建议
${next_actions}

---
**生成信息**:
- 模板版本: distill-v1.0
- 生成时间: ${generation_time}
- 阶段: distill（提炼）
- 领域: openhuman
""",
            metadata_schema={
                "type": "object",
                "properties": {
                    "source_document": {"type": "string", "description": "源文档标识符"},
                    "distilled_by": {"type": "string", "description": "提炼人员/系统"},
                    "distillation_date": {"type": "string", "format": "date"},
                    "quality_metrics": {"type": "object", "description": "质量指标"},
                },
                "required": ["source_document", "distilled_by", "distillation_date"],
            },
        )

        # skill_design（技能设计）阶段模板
        skill_design_template = ArtifactTemplate(
            stage_id="skill_design",
            stage_label="技能设计",
            description="技能定义文件与参数模板",
            required_fields=["skill_id", "skill_name", "skill_designer", "design_date"],
            content_template="""# 技能定义文件 - ${skill_id}

## 1. 基础信息
- **技能ID**: ${skill_id}
- **技能名称**: ${skill_name}
- **技能版本**: ${skill_version}
- **设计人员**: ${skill_designer}
- **设计日期**: ${design_date}
- **技能分类**: ${skill_category}
- **难度等级**: ${difficulty_level}/5

## 2. 技能描述
${skill_description}

## 3. 输入参数定义
${input_parameters}

## 4. 输出产物定义
${output_artifacts}

## 5. 执行流程
${execution_workflow}

## 6. 质量门禁标准
${quality_gate_criteria}

## 7. 技能模板文件
${skill_template_files}

## 8. 测试用例
${test_cases}

## 9. 依赖与约束
${dependencies_and_constraints}

## 10. 版本历史
${version_history}

---
**生成信息**:
- 模板版本: skill_design-v1.0
- 生成时间: ${generation_time}
- 阶段: skill_design（技能设计）
- 领域: openhuman
""",
            metadata_schema={
                "type": "object",
                "properties": {
                    "skill_id": {"type": "string", "description": "技能唯一标识符"},
                    "skill_name": {"type": "string", "description": "技能名称"},
                    "skill_designer": {"type": "string", "description": "设计人员"},
                    "design_date": {"type": "string", "format": "date"},
                },
                "required": ["skill_id", "skill_name", "skill_designer", "design_date"],
            },
        )

        # dispatch（任务分发）阶段模板
        dispatch_template = ArtifactTemplate(
            stage_id="dispatch",
            stage_label="任务分发",
            description="任务发布记录与匹配结果",
            required_fields=["task_order_id", "dispatch_time", "dispatched_by"],
            content_template="""# 任务分发记录 - ${task_order_id}

## 1. 分发基本信息
- **任务订单ID**: ${task_order_id}
- **分发时间**: ${dispatch_time}
- **分发人员**: ${dispatched_by}
- **分发批次**: ${dispatch_batch}
- **分发策略**: ${dispatch_strategy}

## 2. 任务详情
${task_details}

## 3. 执行者匹配结果
${worker_matching_results}

## 4. 分发决策依据
${dispatch_decision_basis}

## 5. 风险评估
${risk_assessment}

## 6. 资源分配
${resource_allocation}

## 7. 分发状态跟踪
${dispatch_status_tracking}

## 8. HITL审批记录
${hitl_approval_records}

## 9. 异常处理
${exception_handling}

## 10. 后续跟进
${follow_up_actions}

---
**生成信息**:
- 模板版本: dispatch-v1.0
- 生成时间: ${generation_time}
- 阶段: dispatch（任务分发）
- 领域: openhuman
- **HITL要求**: 需要人工介入（高风险：资源分配）
""",
            metadata_schema={
                "type": "object",
                "properties": {
                    "task_order_id": {"type": "string", "description": "任务订单ID"},
                    "dispatch_time": {"type": "string", "format": "date-time"},
                    "dispatched_by": {"type": "string", "description": "分发人员/系统"},
                    "hitl_approval": {"type": "boolean", "description": "是否经过人工审批"},
                },
                "required": ["task_order_id", "dispatch_time", "dispatched_by"],
            },
        )

        # acceptance（验收结算）阶段模板
        acceptance_template = ArtifactTemplate(
            stage_id="acceptance",
            stage_label="验收结算",
            description="验收报告与结算触发凭证",
            required_fields=["task_order_id", "acceptance_time", "accepted_by"],
            content_template="""# 验收报告 - ${task_order_id}

## 1. 验收基本信息
- **任务订单ID**: ${task_order_id}
- **验收时间**: ${acceptance_time}
- **验收人员**: ${accepted_by}
- **验收批次**: ${acceptance_batch}
- **验收标准**: ${acceptance_criteria}

## 2. 交付物检查
${deliverables_check}

## 3. 质量验证结果
${quality_verification_results}

## 4. 合规性检查
${compliance_check}

## 5. 证据材料审核
${evidence_review}

## 6. 验收决策
${acceptance_decision}

## 7. 结算触发凭证
${settlement_trigger_voucher}

## 8. HITL审批记录
${hitl_approval_records}

## 9. 拒绝理由与改进建议
${rejection_reasons_and_improvements}

## 10. 验收结论
${acceptance_conclusion}

---
**生成信息**:
- 模板版本: acceptance-v1.0
- 生成时间: ${generation_time}
- 阶段: acceptance（验收结算）
- 领域: openhuman
- **HITL要求**: 需要人工介入（高风险：触发支付）
""",
            metadata_schema={
                "type": "object",
                "properties": {
                    "task_order_id": {"type": "string", "description": "任务订单ID"},
                    "acceptance_time": {"type": "string", "format": "date-time"},
                    "accepted_by": {"type": "string", "description": "验收人员/系统"},
                    "hitl_approval": {"type": "boolean", "description": "是否经过人工审批"},
                    "settlement_triggered": {"type": "boolean", "description": "是否触发结算"},
                },
                "required": ["task_order_id", "acceptance_time", "accepted_by"],
            },
        )

        # settlement（结算分账）阶段模板
        settlement_template = ArtifactTemplate(
            stage_id="settlement",
            stage_label="结算分账",
            description="结算单与支付记录",
            required_fields=["settlement_batch_id", "settlement_date", "settled_by"],
            content_template="""# 结算分账单 - ${settlement_batch_id}

## 1. 结算基本信息
- **结算批次ID**: ${settlement_batch_id}
- **结算日期**: ${settlement_date}
- **结算人员**: ${settled_by}
- **结算周期**: ${settlement_period}
- **货币单位**: ${currency}

## 2. 结算任务清单
${settled_tasks_list}

## 3. 报酬计算明细
${compensation_calculation_details}

## 4. 分账分配
${allocation_distribution}

## 5. Founder年金计算
${founder_annuity_calculation}

## 6. 平台服务费
${platform_service_fee}

## 7. 税费计算
${tax_calculation}

## 8. 支付明细
${payment_details}

## 9. HITL审批记录
${hitl_approval_records}

## 10. 结算状态跟踪
${settlement_status_tracking}

## 11. 审计轨迹
${audit_trail}

## 12. 结算总结
${settlement_summary}

---
**生成信息**:
- 模板版本: settlement-v1.0
- 生成时间: ${generation_time}
- 阶段: settlement（结算分账）
- 领域: openhuman
- **HITL要求**: 需要人工介入（高风险：资金处理）
""",
            metadata_schema={
                "type": "object",
                "properties": {
                    "settlement_batch_id": {"type": "string", "description": "结算批次ID"},
                    "settlement_date": {"type": "string", "format": "date"},
                    "settled_by": {"type": "string", "description": "结算人员/系统"},
                    "hitl_approval": {"type": "boolean", "description": "是否经过人工审批"},
                    "payment_status": {"type": "string", "description": "支付状态"},
                },
                "required": ["settlement_batch_id", "settlement_date", "settled_by"],
            },
        )

        # audit（审计追溯）阶段模板
        audit_template = ArtifactTemplate(
            stage_id="audit",
            stage_label="审计追溯",
            description="审计报告与追溯记录",
            required_fields=["audit_id", "audit_date", "auditor"],
            content_template="""# 审计报告 - ${audit_id}

## 1. 审计基本信息
- **审计ID**: ${audit_id}
- **审计日期**: ${audit_date}
- **审计人员**: ${auditor}
- **审计范围**: ${audit_scope}
- **审计期间**: ${audit_period}

## 2. 审计目标与方法
${audit_objectives_and_methodology}

## 3. 流程合规性检查
${process_compliance_check}

## 4. 数据完整性验证
${data_integrity_verification}

## 5. 安全与隐私审计
${security_and_privacy_audit}

## 6. 财务准确性审计
${financial_accuracy_audit}

## 7. 异常检测与追溯
${anomaly_detection_and_traceability}

## 8. HITL合规性检查
${hitl_compliance_check}

## 9. 审计发现与问题
${audit_findings_and_issues}

## 10. 改进建议
${improvement_recommendations}

## 11. 合规证明
${compliance_certification}

## 12. 审计结论
${audit_conclusion}

---
**生成信息**:
- 模板版本: audit-v1.0
- 生成时间: ${generation_time}
- 阶段: audit（审计追溯）
- 领域: openhuman
- **HITL要求**: 需要人工介入（高风险：敏感数据）
""",
            metadata_schema={
                "type": "object",
                "properties": {
                    "audit_id": {"type": "string", "description": "审计ID"},
                    "audit_date": {"type": "string", "format": "date"},
                    "auditor": {"type": "string", "description": "审计人员/系统"},
                    "hitl_approval": {"type": "boolean", "description": "是否经过人工审批"},
                    "sensitive_data_handled": {
                        "type": "boolean",
                        "description": "是否处理敏感数据",
                    },
                },
                "required": ["audit_id", "audit_date", "auditor"],
            },
        )

        # 注册所有模板
        templates = [
            distill_template,
            skill_design_template,
            dispatch_template,
            acceptance_template,
            settlement_template,
            audit_template,
        ]

        for template in templates:
            self.templates[template.stage_id] = template

    def get_template(self, stage_id: str) -> Optional[ArtifactTemplate]:
        """获取指定阶段的默认模板"""
        return self.templates.get(stage_id)

    def list_templates(self) -> List[ArtifactTemplate]:
        """列出所有模板"""
        return list(self.templates.values())

    def render_template(self, stage_id: str, context: Dict[str, Any]) -> str:
        """
        渲染指定阶段的模板

        Args:
            stage_id: 阶段ID
            context: 渲染上下文

        Returns:
            渲染后的内容，如果模板不存在返回空字符串
        """
        template = self.get_template(stage_id)
        if not template:
            return ""

        # 添加生成时间（如果未提供）
        if "generation_time" not in context:
            from datetime import datetime

            context["generation_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return template.render(context)

    def validate_template_context(self, stage_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证指定阶段的模板上下文

        Args:
            stage_id: 阶段ID
            context: 待验证的上下文

        Returns:
            验证结果字典
        """
        template = self.get_template(stage_id)
        if not template:
            return {
                "valid": False,
                "missing_fields": [],
                "extra_fields": [],
                "template_fields": [],
                "error": f"模板不存在: {stage_id}",
            }

        result = template.validate_context(context)
        result["stage_id"] = stage_id
        result["template_name"] = template.template_name

        return result

    def get_template_info(self, stage_id: str) -> Dict[str, Any]:
        """获取模板信息"""
        template = self.get_template(stage_id)
        if not template:
            return {"error": f"模板不存在: {stage_id}"}

        return {
            "stage_id": template.stage_id,
            "stage_label": template.stage_label,
            "template_name": template.template_name,
            "description": template.description,
            "required_fields": template.required_fields,
            "metadata_schema": template.metadata_schema,
        }

    def get_phase1_summary(self) -> Dict[str, Any]:
        """获取 Phase 1 模板实现总结"""
        total = len(self.templates)
        stages_with_templates = list(self.templates.keys())

        return {
            "phase": 1,
            "description": "OpenHuman 领域产物模板完成",
            "total_templates": total,
            "stages_with_templates": stages_with_templates,
            "implementation_status": "6个OpenHuman阶段的标准产物模板已定义",
            "notes": [
                "Phase 1 完成了 OpenHuman 6个阶段的产物模板定义",
                "模板包含变量占位符 ${variable}，运行时填充",
                "每个模板包含必需字段验证和元数据schema",
                "模板与阶段注册表的 expected_artifact 字段对齐",
                "支持模板渲染、上下文验证和模板信息查询",
            ],
        }


# 全局模板管理器实例
_templates_instance: Optional[OpenHumanArtifactTemplates] = None


def get_templates_manager() -> OpenHumanArtifactTemplates:
    """获取全局模板管理器实例"""
    global _templates_instance
    if _templates_instance is None:
        _templates_instance = OpenHumanArtifactTemplates()
    return _templates_instance


if __name__ == "__main__":
    # 测试代码
    print("=== OpenHuman Artifact Templates 测试 ===\n")

    manager = get_templates_manager()

    # 1. 模板列表
    print("1. 模板列表:")
    for template in manager.list_templates():
        print(f"  - {template.stage_id} ({template.stage_label}): {template.description}")

    # 2. 模板信息查询
    print("\n2. 模板信息查询:")
    for stage_id in ["distill", "dispatch", "settlement"]:
        info = manager.get_template_info(stage_id)
        if "error" not in info:
            print(f"  {stage_id}: {info['description']}")
            print(f"    必需字段: {', '.join(info['required_fields'])}")

    # 3. 模板渲染测试
    print("\n3. 模板渲染测试:")
    test_context = {
        "skill_id": "SKILL-001",
        "skill_name": "市场调研分析",
        "skill_designer": "AI Designer",
        "design_date": "2026-04-09",
        "skill_version": "1.0.0",
        "skill_category": "调研分析",
        "difficulty_level": "3",
        "skill_description": "自动化市场调研与竞争分析技能",
        "generation_time": "2026-04-09 15:30:00",
    }

    rendered = manager.render_template("skill_design", test_context)
    if rendered:
        print(f"  技能设计模板渲染成功，长度: {len(rendered)} 字符")
        # 显示前200字符
        preview = rendered[:200] + "..." if len(rendered) > 200 else rendered
        print(f"  预览: {preview}")

    # 4. 上下文验证测试
    print("\n4. 上下文验证测试:")
    validation_result = manager.validate_template_context("skill_design", test_context)
    print(f"  验证结果: {'通过' if validation_result['valid'] else '失败'}")
    if validation_result["missing_fields"]:
        print(f"  缺失字段: {validation_result['missing_fields']}")
    if validation_result["extra_fields"]:
        print(f"  额外字段: {validation_result['extra_fields']}")

    # 5. Phase 1 总结
    print("\n5. Phase 1 总结:")
    summary = manager.get_phase1_summary()
    for key, value in summary.items():
        if isinstance(value, list):
            print(f"  {key}:")
            for item in value:
                print(f"    - {item}")
        else:
            print(f"  {key}: {value}")

    print("\n✅ OpenHuman Artifact Templates 测试完成")
