#!/usr/bin/env python3
"""
测试预检验证函数
"""

import sys

sys.path.insert(0, "scripts")

from athena_ai_plan_runner import validate_build_preflight

# 模拟任务数据
item = {
    "id": "-Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313",
    "title": "执行工程实施方案: -Agent-基因递归演进-engineering-plan-20260413-095313",
    "instruction_path": "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/008-工程实施方案/phase1/-Agent-基因递归演进-engineering-plan-20260413-095313.md",
    "entry_stage": "build",
    "risk_level": "medium",
    "unattended_allowed": True,
    "targets": [],
    "metadata": {
        "priority": "P1",
        "lane": "engineering_execution",
        "epic": "engineering_implementation",
        "category": "engineering_plan",
        "rationale": "由工程化实施方案生成器自动创建的工程实施任务",
        "depends_on": [],
        "autostart": True,
        "generated_by": "engineering-plan-generator.sh",
        "phase": "phase1",
        "plan_file": "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/008-工程实施方案/phase1/-Agent-基因递归演进-engineering-plan-20260413-095313.md",
        "assigned_agent": "claude-executor",
        "estimated_hours": 8,
        "acceptance_criteria": [
            "完成需求分析与技术选型",
            "实现原型开发与验证",
            "完成完整实现与测试",
            "通过质量审计与部署",
        ],
    },
}

# 读取指令文件
with open(item["instruction_path"], "r", encoding="utf-8") as f:
    instruction_text = f.read()

print("测试预检验证...")
print(f"标题: {item['title']}")
print(f"entry_stage: {item['entry_stage']}")
print(f"risk_level: {item['risk_level']}")

passed, reason, should_manual_hold = validate_build_preflight(instruction_text, item)

print(f"结果: {'通过' if passed else '失败'}")
print(f"原因: {reason}")
print(f"应降级为manual_hold: {should_manual_hold}")
