#!/usr/bin/env python3
"""
Athena Prompt - Athena 系统提示词

抽离 Athena 的 system prompt，实现沟通契约。
"""

import os
from typing import Dict, List, Optional

# 基础系统提示词（遵循沟通契约）
BASE_SYSTEM_PROMPT = """你是 Athena，OpenClaw 的 AI 助手。回答简洁、专业、实用。

## 沟通契约

1. 理解先行：先用一句话复述理解，确保对齐认知。
2. 明确下一步：明确当前要做的第一步，避免模糊承诺。
3. 执行回执：进入执行或任务路由时，返回当前阶段、选用的执行器/skill/tool、预期产物或下一观察点。
4. 边界透明：如果做不到，必须明确缺什么前置条件、现在能退化做什么。
5. 提问精炼：如果需要提问，最多问 1 个高价值问题，避免把责任甩回给用户。
6. 简洁实用：保持简洁，不要把每次回复写成长文。

## 可用能力

### 斜杠命令
- `/task` – 创建编排任务
- `/tasks` – 查看任务队列
- `/officehours` – 办公时间咨询
- `/planeng` – 规划工程任务
- `/review` – 代码/文档审查
- `/qa` – 质量检查
- `/browse` – 网页浏览（opencli 只读）
- `/skills` – 列出已接线 skills、状态、前置条件、是否可执行
- `/skill <skill_id> <args>` – 执行 skill 或返回清晰的 gate 说明
- `/software` – 返回当前可用的软件执行 provider 列表及状态

### 技能路由
- **openhuman-skill-matcher** – 技能匹配（可执行）
- **opencli-scanner** – 网页结构扫描（需 opencli 已安装）
- **humanized-web-scraper** – 表单自动化（需 Docker 环境、人工介入，返回 gate 说明）
- **openhuman-cswdp** – 碳硅基工作流（文档参考）
- **openhuman-geo** – 地理分析（文档参考）

### 软件执行器
- **opencli** – 网页只读扫描、命令行透传（可用）
- **cli_anything** – 检测、声明、接入口预留（可选）

## 响应格式

### 普通聊天
[理解复述] 我理解你想 [用户意图]。
[下一步] 我会 [具体行动]。
[附加说明] （如有必要）因为 [理由]，需要注意 [风险/边界]。

### 任务路由
[阶段] 进入 [阶段名称] 阶段。
[执行器] 选用 [skill/tool 名称]。
[预期] 预计产出 [产物]，下一步观察 [观察点]。
[状态] 执行中 / 已完成 [进度]。

### 受限能力
[边界] 目前无法直接 [用户请求]，因为 [缺失条件]。
[退化] 现在可以 [替代方案]。
[前置] 如需完整能力，需要先 [前置步骤]。

### 提问
[聚焦] 为了 [目标]，我需要确认一点：
[单点] [具体问题，最多一个]
"""

# 技能路由关键词映射
SKILL_KEYWORD_MAP = {
    "skill matcher": "openhuman-skill-matcher",
    "匹配技能": "openhuman-skill-matcher",
    "opencli scan": "opencli-scanner",
    "浏览器扫描": "opencli-scanner",
    "humanized scrape": "humanized-web-scraper",
    "表单自动化": "humanized-web-scraper",
    "cswdp": "openhuman-cswdp",
    "碳硅基工作流": "openhuman-cswdp",
    "geo": "openhuman-geo",
    "地理分析": "openhuman-geo",
    "软件执行": "software_executor",
    "网页控制": "software_executor",
}

# 斜杠命令描述
SLASH_COMMAND_DESCRIPTIONS = {
    "/task": "创建编排任务",
    "/tasks": "查看任务队列",
    "/officehours": "办公时间咨询",
    "/planeng": "规划工程任务",
    "/review": "代码/文档审查",
    "/qa": "质量检查",
    "/browse": "网页浏览（opencli 只读）",
    "/skills": "列出已接线 skills、状态、前置条件、是否可执行",
    "/skill": "执行 skill 或返回清晰的 gate 说明",
    "/software": "返回当前可用的软件执行 provider 列表及状态",
}


def get_system_prompt() -> str:
    """获取系统提示词"""
    return BASE_SYSTEM_PROMPT


def get_skill_keyword_map() -> Dict[str, str]:
    """获取技能关键词映射"""
    return SKILL_KEYWORD_MAP.copy()


def get_slash_command_descriptions() -> Dict[str, str]:
    """获取斜杠命令描述"""
    return SLASH_COMMAND_DESCRIPTIONS.copy()


def format_understanding_response(user_input: str) -> str:
    """格式化理解复述响应"""
    return f"我理解你想 {user_input}。\n\n"


def format_next_step(action: str) -> str:
    """格式化下一步行动"""
    return f"我会 {action}。\n\n"


def format_task_routing(stage: str, executor: str, expected: str, status: str = "执行中") -> str:
    """格式化任务路由响应"""
    return f"""进入 {stage} 阶段。

选用 {executor}。

预计产出 {expected}，下一步观察执行状态。

{status}：正在初始化...
"""


def format_gated_skill(
    skill_id: str, missing_condition: str, fallback: str, prerequisite: str = ""
) -> str:
    """格式化受限技能响应"""
    lines = [
        f"目前无法直接执行 {skill_id}，因为 {missing_condition}。",
        "",
        f"现在可以 {fallback}。",
    ]
    if prerequisite:
        lines.append("")
        lines.append(f"如需完整能力，需要先 {prerequisite}。")
    return "\n".join(lines)


if __name__ == "__main__":
    # 测试输出
    print("=== Athena Prompt 测试 ===")
    print("\n1. 系统提示词长度:", len(get_system_prompt()))
    print("\n2. 技能关键词映射:", get_skill_keyword_map())
    print("\n3. 斜杠命令描述:", get_slash_command_descriptions())

    # 测试格式化函数
    print("\n4. 格式化理解响应:")
    print(format_understanding_response("查看技能匹配情况"))

    print("\n5. 格式化下一步:")
    print(format_next_step("调用 openhuman-skill-matcher 技能进行分析"))

    print("\n6. 格式化任务路由:")
    print(
        format_task_routing(
            stage="技能匹配",
            executor="openhuman-skill-matcher",
            expected="技能匹配分数报告",
            status="执行中",
        )
    )

    print("\n7. 格式化受限技能:")
    print(
        format_gated_skill(
            skill_id="humanized-web-scraper",
            missing_condition="该技能需要 Docker 环境且涉及人工介入",
            fallback="生成表单填写指南，或使用 opencli 扫描页面结构",
            prerequisite="配置 Docker 环境并设置人工监督流程",
        )
    )
