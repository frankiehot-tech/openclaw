#!/usr/bin/env python3
"""
诊断预检失败原因脚本
分析所有任务的预检失败具体原因，为修复提供依据
"""

import json
import os

MANIFEST_FILE = "/Volumes/1TB-M2/openclaw/scripts/gene_management_queue_manifest.json"
QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
)


def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def read_instruction_file(file_path):
    """读取指令文件内容"""
    if not os.path.exists(file_path):
        return None, f"文件不存在: {file_path}"

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        return content, "成功读取"
    except Exception as e:
        return None, f"读取失败: {e}"


def analyze_preflight_failure(task_id, task, instruction_content):
    """分析单个任务的预检失败原因"""
    if not instruction_content:
        return ["指令文件无法读取"]

    lines = instruction_content.splitlines()
    line_count = len(lines)

    failure_reasons = []

    # 1. 检查验收标准
    has_acceptance = False
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in ["验收标准", "acceptance"]):
            has_acceptance = True
            break

    if not has_acceptance:
        failure_reasons.append("缺少验收标准章节")

    # 2. 检查文档行数
    if line_count > 200:
        failure_reasons.append(f"文档过长 ({line_count} 行 > 200 行限制)")

    # 3. 检查标题关键词
    first_line = lines[0].strip() if lines else ""
    doc_type = "unknown"

    if first_line.startswith("# "):
        title = first_line[2:].strip().lower()
        instruction_path = task.get("instruction_path", "").lower()

        build_keywords = ["vscode执行指令", "执行指令", "build", "实现"]
        review_keywords = ["codex审计指令", "审计"]
        plan_keywords = ["策划", "方案", "规划"]

        is_build = any(
            keyword in title or keyword in instruction_path for keyword in build_keywords
        )
        is_review = any(
            keyword in title or keyword in instruction_path for keyword in review_keywords
        )
        is_plan = any(keyword in title for keyword in plan_keywords)

        if is_build:
            doc_type = "build"
        elif is_review:
            doc_type = "review"
        elif is_plan:
            doc_type = "plan"

        if doc_type != "build":
            failure_reasons.append(f"文档类型为 '{doc_type}'，不是build类型")

    # 4. 检查entry_stage/stage字段
    entry_stage = task.get("entry_stage", task.get("stage", ""))
    if entry_stage and entry_stage != "build":
        failure_reasons.append(f"entry_stage/stage字段为 '{entry_stage}'，不是'build'")

    return failure_reasons


def main():
    print("=" * 80)
    print("预检失败诊断脚本")
    print("=" * 80)

    if not os.path.exists(QUEUE_FILE):
        print(f"❌ 队列文件不存在: {QUEUE_FILE}")
        return

    # 加载队列状态
    state = load_json_file(QUEUE_FILE)
    items = state.get("items", {})

    print(f"📊 队列状态: {state.get('queue_status')}")
    print(f"📊 任务总数: {len(items)}")
    print()

    # 按状态分类任务
    tasks_by_status = {
        "manual_hold": [],
        "failed": [],
        "pending": [],
        "running": [],
        "completed": [],
    }

    for task_id, task in items.items():
        status = task.get("status", "unknown")
        if status in tasks_by_status:
            tasks_by_status[status].append((task_id, task))
        else:
            tasks_by_status["unknown"].append((task_id, task))

    # 分析manual_hold任务
    print("🔍 分析 manual_hold 任务:")
    print("-" * 80)

    manual_hold_tasks = tasks_by_status["manual_hold"]
    for task_id, task in manual_hold_tasks:
        print(f"\n📝 任务: {task_id}")
        print(f"   标题: {task.get('title', '无标题')}")
        print(f"   summary: {task.get('summary', '无摘要')}")
        print(f"   pipeline_summary: {task.get('pipeline_summary', '无')}")

        instruction_path = task.get("instruction_path", "")
        if instruction_path:
            print(f"   指令文件: {instruction_path}")

            # 读取指令文件
            content, status_msg = read_instruction_file(instruction_path)
            if content:
                failure_reasons = analyze_preflight_failure(task_id, task, content)
                if failure_reasons:
                    print("   ❌ 预检失败原因:")
                    for reason in failure_reasons:
                        print(f"      - {reason}")
                else:
                    print("   ✅ 指令文件看起来符合要求")
            else:
                print(f"   ❌ 指令文件读取失败: {status_msg}")
        else:
            print("   ❌ 无指令文件路径")

    # 分析failed任务
    print("\n🔍 分析 failed 任务:")
    print("-" * 80)

    failed_tasks = tasks_by_status["failed"]
    for task_id, task in failed_tasks:
        print(f"\n📝 任务: {task_id}")
        print(f"   标题: {task.get('title', '无标题')}")
        print(f"   error: {task.get('error', '无错误信息')}")
        print(f"   summary: {task.get('summary', '无摘要')}")

        # 检查是否是API key错误
        error = task.get("error", "")
        if "API" in error or "api" in error.lower():
            print("   ⚠️  疑似API key配置问题")

    # 总结分析结果
    print("\n" + "=" * 80)
    print("诊断总结")
    print("=" * 80)

    print("📊 任务状态分布:")
    for status, task_list in tasks_by_status.items():
        if task_list:
            print(f"   {status}: {len(task_list)} 个任务")

    print("\n🎯 核心问题分析:")
    print(f"   1. {len(manual_hold_tasks)} 个manual_hold任务 - 预检失败，需要手动拉起")
    print(f"   2. {len(failed_tasks)} 个failed任务 - 执行失败，需要修复配置")

    print("\n🔧 建议修复方案:")
    print("   A. 对于manual_hold任务:")
    print("      - 方案1: 修改预检逻辑，放宽对聊天任务的要求")
    print("      - 方案2: 为聊天任务添加验收标准章节")
    print("      - 方案3: 将任务状态手动重置为pending")

    print("   B. 对于failed任务:")
    print("      - 检查DASHSCOPE_API_KEY环境变量配置")
    print("      - 确保API key正确且未过期")

    print("\n💡 立即行动建议:")
    print("   1. 创建修复脚本，修改预检逻辑或添加验收标准")
    print("   2. 修复队列状态，将manual_hold任务重置为pending")
    print("   3. 重启队列运行器")
    print("   4. 测试手动拉起功能")


if __name__ == "__main__":
    main()
