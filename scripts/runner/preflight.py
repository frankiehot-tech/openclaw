#!/usr/bin/env python3
"""preflight"""

from __future__ import annotations

import logging
import sys
import shutil
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


_scripts_dir = Path(__file__).resolve().parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

try:
    from .openclaw_roots import (
        LOG_DIR,
        PLAN_CONFIG_PATH,
        PLAN_DIR,
        QUEUE_STATE_DIR,
        RUNTIME_ROOT,
        TASKS_DIR,
        TASKS_PATH,
        pid_file,
    )
except ImportError:
    import sys
    from openclaw_roots import (
        PLAN_DIR,
        RUNTIME_ROOT,
    )

from .utils import extract_referenced_paths, codex_executable
from .config import load_control_plane_config


def common_preflight_warnings(instruction_text: str) -> list[str]:
    warnings: list[str] = []
    # 控制面配置检查
    control_plane = load_control_plane_config()
    if not control_plane.get("available"):
        warnings.append(f"控制面配置不可用: {control_plane.get('reason', '未知原因')}")
    else:
        # 添加控制面作用域信息（仅信息性，非警告）
        scope_summary = control_plane.get("scope_summary", {})
        active_scopes = [scope for scope, enabled in scope_summary.items() if enabled]
        if active_scopes:
            warnings.append(
                f"控制面作用域已激活: {', '.join(active_scopes)} (优先级: {' > '.join(control_plane.get('configuration_priority', []))})"
            )

    if not (RUNTIME_ROOT / ".git").exists():
        warnings.append(
            f"当前运行根 {RUNTIME_ROOT} 不是 Git 仓库；请避免依赖 Git-only 工作流，优先直接在现有目录完成可运行改动。"
        )
    referenced_paths = extract_referenced_paths(instruction_text)
    missing = [path for path in referenced_paths if not Path(path).exists()]
    if missing:
        preview = ", ".join(missing[:6])
        if len(missing) > 6:
            preview += f" 等 {len(missing)} 个路径"
        warnings.append(
            f"任务文档中引用了不存在的路径：{preview}。请基于当前工作区最相近位置继续实现，并在结果中诚实说明路径漂移。"
        )
    critical_missing = [
        path
        for path in missing
        if path.endswith("/AGENTS/STANDARD_ENGINEERING_WORKFLOW.md")
        or path.endswith("/AGENTS/WORKFLOW.md")
        or path.endswith("/AGENTS/RUNTIME_CONTRACTS.md")
    ]
    if critical_missing:
        warnings.append(
            "任务文档要求读取的部分标准流程文档在当前运行根不存在；不要持续搜索这些文件，直接读取 AGENTS.md、现有 agent 契约和最相关代码模块继续。"
        )
    return warnings


def build_preflight_warnings(instruction_text: str) -> list[str]:
    warnings = common_preflight_warnings(instruction_text)
    if not shutil.which("opencode"):
        warnings.append("本机未发现 opencode 可执行文件，build 无法启动。")
    return warnings


def review_preflight_warnings(instruction_text: str) -> list[str]:
    warnings = common_preflight_warnings(instruction_text)
    if not codex_executable():
        warnings.append("本机未发现 codex 可执行文件，review 无法启动。")
    return warnings


def plan_preflight_warnings(instruction_text: str) -> list[str]:
    warnings = common_preflight_warnings(instruction_text)
    if not codex_executable():
        warnings.append("本机未发现 codex 可执行文件，plan 无法启动。")
    if not PLAN_DIR.exists():
        warnings.append(f"AI plan 目录不存在：{PLAN_DIR}")
    return warnings


def validate_build_preflight(
    instruction_text: str,
    item: dict[str, Any] | None = None,
    *,
    max_targets: int = 8,
    require_acceptance: bool = True,
) -> tuple[bool, str, bool]:
    """
    校验 build 预检门禁，返回 (通过, 失败原因, 是否应降级为 manual_hold)。

    检查项：
    1. doc_type / entry_stage / risk_level 是否与 build 匹配
    2. targets_count 是否过多（> max_targets）
    3. 是否有明确的验收标准（acceptance）
    4. 是否属于“窄任务”（范围明确、可独立完成）
    5. 文档类型是否明显不属于 build（例如策划文档）

    保守原则：如果无法可靠判断，优先降级为 manual_hold。
    """
    # 确保 lines 变量始终被定义
    lines = instruction_text.splitlines()

    # 例外规则：对于聊天任务，放宽预检要求
    if item:
        title = str(item.get("title", "") or "").strip()
        # 如果标题包含"聊天请求"，视为测试任务，放宽要求
        if "聊天请求" in title:
            # 对于短小的聊天任务（< 50行），直接通过
            lines = instruction_text.splitlines()
            if len(lines) < 50:
                return True, "聊天任务例外通过", False
            # 对于较长的聊天任务，只检查最基本的要求
            require_acceptance = False
            max_targets = 20  # 提高目标数量限制

    # 例外规则：对于基因管理审计任务，放宽预检要求 (P0修复)
    if item:
        title = str(item.get("title", "") or "").strip()
        metadata = item.get("metadata", {})
        epic = str(metadata.get("epic", "") or "").strip()

        # 如果是基因管理审计任务，放宽要求
        if "审计" in title and epic == "gene_management":
            # 放宽文档长度限制（审计文档可能较长）
            lines = instruction_text.splitlines()
            if len(lines) < 600:  # 提高到600行
                return True, "基因管理审计任务例外通过", False
            # 对于超长审计文档，放宽其他要求
            require_acceptance = False
            max_targets = 30  # 提高目标数量限制

    # 1. 基础校验：entry_stage 应为 build
    if item:
        entry_stage = str(item.get("entry_stage", "") or "").strip().lower()
        if entry_stage and entry_stage != "build":
            return (
                False,
                f"entry_stage='{entry_stage}' 不属于 build lane，不应进入自动执行。",
                True,
            )

    # 2. 解析文档元数据（简单启发式）
    # lines = instruction_text.splitlines()  # 已移至函数开头

    # 检测文档类型：通过标题关键词判断
    doc_type = "unknown"
    first_line = lines[0].strip() if lines else ""
    if first_line.startswith("# "):
        title = first_line[2:].strip().lower()
        instruction_path = ""
        if item:
            instruction_path = str(item.get("instruction_path", "") or "").lower()

        # Prefer explicit build markers over generic words like “审计” that may
        # appear in a build card's business description (e.g. “审计证据面”).
        if (
            "vscode执行指令" in title
            or "执行指令" in title
            or "build" in title
            or "实现" in title
            or "vscode执行指令" in instruction_path
        ):
            doc_type = "build"
        elif "codex审计指令" in title or "codex审计指令" in instruction_path:
            doc_type = "review"
        elif "策划" in title or "方案" in title or "规划" in title:
            doc_type = "plan"

        # 例外：基因管理审计任务应视为build类型
        if item and "基因管理" in title:
            # 从metadata获取epic
            metadata = item.get("metadata", {})
            epic = str(metadata.get("epic", "") or "").strip()
            if epic == "gene_management":
                doc_type = "build"
        # 例外：工程实施方案应视为build类型
        if item and ("工程实施方案" in title or "方案" in title):
            metadata = item.get("metadata", {})
            category = str(metadata.get("category", "") or "").strip()
            epic = str(metadata.get("epic", "") or "").strip()
            if category == "engineering_plan" or epic == "engineering_implementation":
                doc_type = "build"
        elif "审计" in title or "review" in title:
            doc_type = "review"

    # 如果文档类型明显是策划或审计，降级为 manual
    if doc_type in ("plan", "review"):
        return False, f"文档类型似乎是 '{doc_type}'，不属于 build lane。", True

    # 3. 提取风险等级（如果 item 中有）
    risk_level = ""
    if item:
        risk_level = str(item.get("risk_level", "") or "").strip().lower()
        # 高风险任务可能需要人工审核
        if risk_level == "high":
            return False, f"风险等级为 high，需要人工审核。", True

    # 4. 统计目标文件数量（通过查找路径模式）
    import re

    # 匹配类似 /Volumes/1TB-M2/openclaw/... 的路径
    target_pattern = r"/Volumes/1TB-M2[^\s`\"'<>)\]]+"
    referenced_paths = re.findall(target_pattern, instruction_text)
    # 去重，过滤掉明显非文件路径的匹配
    filtered_paths = []
    for path in referenced_paths:
        path = path.rstrip(".,;:'\"")
        if (
            path.endswith(".md")
            or path.endswith(".py")
            or path.endswith(".json")
            or path.endswith(".txt")
        ):
            filtered_paths.append(path)
        elif "/" in path and len(path) > 20:  # 假设是目录
            filtered_paths.append(path)

    targets_count = len(set(filtered_paths))
    if targets_count > max_targets:
        return (
            False,
            f"引用了 {targets_count} 个目标路径，超过窄任务上限 {max_targets}。",
            True,
        )

    # 5. 检查验收标准
    has_acceptance = False
    acceptance_keywords = ["验收标准", "验收要求", "acceptance", "验证要求", "验证标准"]
    for line in lines:
        line_lower = line.lower()
        for kw in acceptance_keywords:
            if kw in line_lower:
                has_acceptance = True
                break
        if has_acceptance:
            break

    if require_acceptance and not has_acceptance:
        return False, "文档中未发现明确的验收标准（如“验收标准”章节）。", True

    # 6. 窄任务启发式：文档长度适中，包含具体步骤
    line_count = len(lines)
    # 对于基因管理审计任务，放宽长度限制
    if item:
        metadata = item.get("metadata", {})
        epic = str(metadata.get("epic", "") or "").strip()
        category = str(metadata.get("category", "") or "").strip()
        title = str(item.get("title", "") or "").strip()

        if "基因管理" in title and epic == "gene_management" and "审计" in title:
            # 基因管理审计任务允许最多600行
            if line_count > 600:
                return False, f"基因管理审计文档过长（{{line_count}} 行），请拆分为子任务。", True
        elif category == "engineering_plan" or epic == "engineering_implementation":
            # 工程实施方案允许最多400行（通常比一般任务复杂）
            if line_count > 400:
                return False, f"工程实施方案文档过长（{{line_count}} 行），请拆分为子任务。", True
        elif line_count > 200:
            # 其他任务保持200行限制
            return False, f"文档过长（{{line_count}} 行），可能不是窄任务。", True
    elif line_count > 200:
        # 没有item信息时保持200行限制
        return False, f"文档过长（{{line_count}} 行），可能不是窄任务。", True

    # 7. 如果所有检查通过，返回成功
    return True, "预检通过，符合窄任务标准。", False


def render_prompt(item: dict[str, Any], instruction_text: str, warnings: list[str]) -> str:
    warning_block = "\n".join(f"- {line}" for line in warnings) if warnings else "- 无额外预警。"
    return f"""你是 OpenClaw 仓库的 VS Code / OpenCode Build Agent。

当前运行根：
- {RUNTIME_ROOT}

当前队列项：
- 标题：{item.get("title", item.get("id", "untitled"))}
- ID：{item.get("id", "")}
- 说明文档：{item.get("instruction_path", "")}

执行要求：
- 先做最小可运行闭环，再补充增量优化。
- 优先基于当前工作区真实结构完成实现，不要因为文档引用旧路径就卡住。
- 若文档里的绝对路径不存在，请在当前工作区最接近的目录落地，并在最终总结里诚实说明路径漂移。
- 若文档要求先读取的标准流程文件不存在，不要在查找这些文件上耗时；改读 AGENTS.md、现有 agent 契约和当前最相关模块后继续。
- 不要编造“已完成”的能力；做不到的地方要明确写出阻塞点。
- 完成后必须输出 4 段：已修改文件、关键变更、验证结果、剩余风险。

预检结果：
{warning_block}

任务说明全文如下：

{instruction_text}
"""


def render_review_prompt(item: dict[str, Any], instruction_text: str, warnings: list[str]) -> str:
    warning_block = "\n".join(f"- {line}" for line in warnings) if warnings else "- 无额外预警。"
    return f"""你是 OpenClaw 仓库的 Codex Review Agent。

当前运行根：
- {RUNTIME_ROOT}

当前队列项：
- 标题：{item.get("title", item.get("id", "untitled"))}
- ID：{item.get("id", "")}
- 审计说明：{item.get("instruction_path", "")}

执行要求：
- 本轮只做审计，不做代码修改。
- 审计结论必须先给 findings，再给 open questions / assumptions、验证范围、剩余风险。
- 优先基于当前工作区真实结构、已有 artifact 和已落地代码给出结论，不要复述空泛建议。
- 若任务文档里的绝对路径不存在，请基于当前工作区最接近的目录审计，并在结论中诚实说明路径漂移。
- 若文档要求先读取的标准流程文件不存在，不要在查找这些文件上耗时；改读 AGENTS.md、现有 agent 契约、最相关代码和 artifact 后继续。
- 如果没有发现问题，必须明确写出“未发现 findings”，并补充残余风险或测试缺口。

预检结果：
{warning_block}

任务说明全文如下：

{instruction_text}
"""


def render_plan_prompt(item: dict[str, Any], instruction_text: str, warnings: list[str]) -> str:
    warning_block = "\n".join(f"- {line}" for line in warnings) if warnings else "- 无额外预警。"
    return f"""你是 OpenClaw 仓库的 Codex Plan Compiler Agent。

当前运行根：
- {RUNTIME_ROOT}

当前 AI plan 目录：
- {PLAN_DIR}

当前队列项：
- 标题：{item.get("title", item.get("id", "untitled"))}
- ID：{item.get("id", "")}
- 策划文档：{item.get("instruction_path", "")}

你的任务是把这张策划卡尽量编译成后续可执行卡片，而不是复述大词。

执行要求：
- 先判断这张卡应当是 `split_to_cards` 还是 `reference_only`。
- 如果无需新的产品决策、且能安全收敛成更小任务，请直接在 AI plan 目录中新建后续卡片。
- 只允许生成窄范围、单责任的 `build` 或 `review` 卡片；单次最多 4 张。
- 生成的卡片必须使用绝对路径，文件名沿用现有风格，例如 `OpenHuman-...-VSCode执行指令.md` 或 `...-Codex审计指令.md`。
- 如果文档范围仍然过宽、仍需新决策、或只适合作为长期参考，就不要强行拆卡，改判 `reference_only`。
- 不要编造“已经入队”的事实；你只负责生成文档和结构化结果，runner 会负责后续入队。
- 若文档里的绝对路径不存在，请在当前工作区最接近的目录落地，并在说明里诚实写出路径漂移。
- 若文档要求先读取的标准流程文件不存在，不要在查找这些文件上耗时；改读 AGENTS.md、现有 agent 契约和最相关模块继续。

预检结果：
{warning_block}

最终输出要求：
- 正常的自然语言总结后，必须追加如下机器可解析块：
PLAN_QUEUE_RESULT_BEGIN
{{JSON}}
PLAN_QUEUE_RESULT_END

JSON schema:
{{
  "decision": "split_to_cards" | "reference_only",
  "summary": "一句话总结",
  "generated_items": [
    {{
      "id": "snake_case_id",
      "title": "卡片标题",
      "instruction_path": "/绝对路径.md",
      "entry_stage": "build" | "review",
      "risk_level": "low" | "medium" | "high",
      "priority": "P0/P1/P2/R1/S1 ...",
      "lane": "build_auto" | "review_auto",
      "epic": "epic_name",
      "category": "category_name",
      "rationale": "为什么要生成这张卡",
      "depends_on": ["其它 queue item id，可为空"],
      "autostart": true
    }}
  ]
}}

任务说明全文如下：

{instruction_text}
"""
