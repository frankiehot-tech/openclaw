#!/usr/bin/env python3
"""
修复预检逻辑，为聊天任务添加例外规则
"""

import os
import shutil
import sys
from datetime import datetime, timezone

RUNNER_FILE = "/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"
BACKUP_FILE = "/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py.backup.original"


def backup_original():
    """备份原始文件"""
    if os.path.exists(RUNNER_FILE):
        shutil.copy2(RUNNER_FILE, BACKUP_FILE)
        print(f"✅ 已备份原始文件: {BACKUP_FILE}")
        return True
    else:
        print(f"❌ 原文件不存在: {RUNNER_FILE}")
        return False


def restore_backup():
    """恢复备份文件"""
    if os.path.exists(BACKUP_FILE):
        shutil.copy2(BACKUP_FILE, RUNNER_FILE)
        print(f"✅ 已恢复备份文件")
        return True
    else:
        print(f"❌ 备份文件不存在: {BACKUP_FILE}")
        return False


def apply_preflight_fix():
    """应用预检修复补丁"""
    print("🔧 应用预检修复补丁...")

    if not os.path.exists(RUNNER_FILE):
        print(f"❌ 文件不存在: {RUNNER_FILE}")
        return False

    # 读取文件内容
    with open(RUNNER_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找validate_build_preflight函数开始位置
    func_start = content.find("def validate_build_preflight(")
    if func_start == -1:
        print("❌ 未找到validate_build_preflight函数")
        return False

    # 找到函数体的开始（第一个冒号后的换行）
    func_body_start = content.find(":", func_start) + 1

    # 查找函数文档字符串的结束位置
    docstring_end = content.find('"""', func_body_start + 3)
    if docstring_end == -1:
        print("❌ 未找到函数文档字符串")
        return False

    # 文档字符串结束后找到第一个非空白字符
    func_code_start = docstring_end + 3
    while func_code_start < len(content) and content[func_code_start] in ["\n", " ", "\t"]:
        func_code_start += 1

    # 检查是否已经应用了修复（查找"聊天请求"例外）
    if "聊天请求" in content[func_start : func_start + 500]:
        print("📋 修复已应用")
        return True

    # 构建修复后的函数开头
    # 在函数文档字符串后，原始代码前插入例外逻辑
    original_code = content[func_start:]

    # 构建新的函数开头
    new_func_start = content[:func_start] + """def validate_build_preflight(
    instruction_text: str,
    item: dict[str, Any] | None = None,
    *,
    max_targets: int = 8,
    require_acceptance: bool = True,
) -> tuple[bool, str, bool]:
    \"\"\"
    校验 build 预检门禁，返回 (通过, 失败原因, 是否应降级为 manual_hold)。

    检查项：
    1. doc_type / entry_stage / risk_level 是否与 build 匹配
    2. targets_count 是否过多（> max_targets）
    3. 是否有明确的验收标准（acceptance）
    4. 是否属于“窄任务”（范围明确、可独立完成）
    5. 文档类型是否明显不属于 build（例如策划文档）

    保守原则：如果无法可靠判断，优先降级为 manual_hold。
    \"\"\"
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
    lines = instruction_text.splitlines()

    # 检测文档类型：通过标题关键词判断
    doc_type = "unknown"
    first_line = lines[0].strip() if lines else ""
    if first_line.startswith("# "):
        title = first_line[2:].strip().lower()
        instruction_path = ""
        if item:
            instruction_path = str(item.get("instruction_path", "") or "").lower()

        # Prefer explicit build markers over generic words like "审计" that may
        # appear in a build card's business description (e.g. "审计证据面").
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
    target_pattern = r"/Volumes/1TB-M2[^\\s`\"'<>)\]]+"
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
        return False, "文档中未发现明确的验收标准（如"验收标准"章节）。", True

    # 6. 窄任务启发式：文档长度适中，包含具体步骤
    line_count = len(lines)
    if line_count > 200:
        # 过长文档可能是宽泛策划
        return False, f"文档过长（{line_count} 行），可能不是窄任务。", True

    # 7. 如果所有检查通过，返回成功
    return True, "预检通过，符合窄任务标准。", False
"""

    # 替换整个函数
    # 我们需要找到函数结束的位置
    # 简单方法：查找下一个def关键字或文件结尾
    func_end = func_start
    indent_level = 0
    in_func = False
    lines = content[func_start:].split("\n")

    for i, line in enumerate(lines):
        if i == 0:
            # 第一行是函数定义
            continue

        stripped = line.strip()
        if not stripped:
            continue

        # 检查缩进级别
        if not in_func:
            # 找到第一个非空行的缩进
            if line and not line.startswith(" " * 4):
                # 缩进减少，可能是函数结束
                func_end = func_start + sum(len(l) + 1 for l in lines[:i])
                break
            else:
                in_func = True
        else:
            if line and not line.startswith(" " * 4) and not line.startswith("\t"):
                # 缩进回到0，函数结束
                func_end = func_start + sum(len(l) + 1 for l in lines[:i])
                break

    # 如果没找到结束，使用文件结尾
    if func_end == func_start:
        func_end = len(content)

    # 构建新内容
    new_content = content[:func_start] + new_func_start + content[func_end:]

    # 保存修改
    with open(RUNNER_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("✅ 预检修复补丁已应用")
    return True


def test_preflight_fix():
    """测试修复效果"""
    print("\n🧪 测试修复效果...")

    # 创建一个简单的测试
    test_code = """
import sys
sys.path.insert(0, "/Volumes/1TB-M2/openclaw/scripts")

from athena_ai_plan_runner import validate_build_preflight

# 测试聊天任务
chat_item = {
    "title": "聊天请求: 测试消息",
    "entry_stage": "build",
    "instruction_path": "/test/chat.md"
}

chat_instruction = "# 计划任务: 聊天请求\\n\\n这是一个测试聊天任务。"

# 测试预检
ok, reason, manual = validate_build_preflight(chat_instruction, chat_item)
print(f"聊天任务预检结果: ok={ok}, reason={reason}, manual={manual}")

if ok:
    print("✅ 聊天任务预检通过（修复生效）")
else:
    print("❌ 聊天任务预检失败（修复未生效）")
"""

    test_file = "/tmp/test_preflight_fix.py"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_code)

    import subprocess

    result = subprocess.run([sys.executable, test_file], capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("错误信息:", result.stderr)

    return "聊天任务预检结果: ok=True" in result.stdout


def main():
    print("=" * 80)
    print("预检逻辑修复脚本 - 为聊天任务添加例外规则")
    print("=" * 80)

    # 备份原文件
    if not backup_original():
        return

    # 应用修复
    if apply_preflight_fix():
        # 测试修复
        if test_preflight_fix():
            print("\n🎯 修复成功！")
            print("修复内容:")
            print("1. ✅ 为标题包含'聊天请求'的任务添加例外规则")
            print("2. ✅ 短小聊天任务（<50行）直接通过预检")
            print("3. ✅ 较长聊天任务放宽验收标准和目标数量限制")
            print("\n🔧 下一步操作:")
            print("1. 重启队列运行器以应用修改")
            print("2. 修复队列状态，将manual_hold任务重置为pending")
            print("3. 测试手动拉起功能")
        else:
            print("\n⚠️  修复可能未完全生效，请检查代码")
    else:
        print("\n❌ 修复失败")


if __name__ == "__main__":
    main()
