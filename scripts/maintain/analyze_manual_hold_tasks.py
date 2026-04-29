#!/usr/bin/env python3
"""
分析manual_hold任务的原因
"""

import json
import sys
from pathlib import Path

# 配置
ROOT_DIR = Path(__file__).parent.parent
QUEUE_FILE = (
    ROOT_DIR / ".openclaw" / "plan_queue" / "openhuman_aiplan_priority_execution_20260414.json"
)


def analyze_manual_hold_tasks():
    print("🔍 分析manual_hold任务")
    print(f"队列文件: {QUEUE_FILE}")

    if not QUEUE_FILE.exists():
        print("❌ 队列文件不存在")
        return 1

    try:
        with open(QUEUE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取队列文件失败: {e}")
        return 1

    items = data.get("items", [])
    if not items:
        print("❌ 队列中没有任务")
        return 1

    # 分类任务
    manual_hold_tasks = []
    failed_tasks = []
    completed_tasks = []

    for item in items:
        status = item.get("status", "")
        if status == "manual_hold":
            manual_hold_tasks.append(item)
        elif status == "failed":
            failed_tasks.append(item)
        elif status == "completed":
            completed_tasks.append(item)

    print("\n📊 任务统计:")
    print(f"  总任务数: {len(items)}")
    print(f"  manual_hold: {len(manual_hold_tasks)}")
    print(f"  failed: {len(failed_tasks)}")
    print(f"  completed: {len(completed_tasks)}")

    # 分析manual_hold任务的特征
    if manual_hold_tasks:
        print(f"\n📋 manual_hold任务分析 ({len(manual_hold_tasks)}个):")

        # 检查任务ID模式
        id_patterns = {}
        for task in manual_hold_tasks[:20]:  # 只分析前20个
            task_id = task.get("id", "")
            if task_id:
                # 提取ID的模式部分
                if "engineering-plan-" in task_id:
                    pattern = task_id.split("engineering-plan-")[0]
                    id_patterns[pattern] = id_patterns.get(pattern, 0) + 1

        if id_patterns:
            print("  ID模式分布:")
            for pattern, count in sorted(id_patterns.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]:
                print(f"    '{pattern}...': {count}个")

        # 检查标题模式
        title_patterns = {}
        for task in manual_hold_tasks[:20]:
            title = task.get("title", "")
            if "执行工程实施方案:" in title:
                pattern = title.replace("执行工程实施方案:", "").strip()[:30]
                title_patterns[pattern] = title_patterns.get(pattern, 0) + 1

        if title_patterns:
            print("  标题模式分布:")
            for pattern, count in sorted(title_patterns.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]:
                print(f"    '{pattern}...': {count}个")

        # 检查路径模式
        path_patterns = {}
        for task in manual_hold_tasks[:20]:
            path = task.get("instruction_path", "")
            if "/phase1/" in path:
                pattern = path.split("/phase1/")[-1][:40]
                path_patterns[pattern] = path_patterns.get(pattern, 0) + 1

        if path_patterns:
            print("  文件路径模式:")
            for pattern, count in sorted(path_patterns.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]:
                print(f"    '{pattern}...': {count}个")

        # 检查metadata中的phase字段
        phase_counts = {}
        for task in manual_hold_tasks[:20]:
            metadata = task.get("metadata", {})
            phase = metadata.get("phase", "unknown")
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        if phase_counts:
            print("  阶段分布:")
            for phase, count in phase_counts.items():
                print(f"    {phase}: {count}个")

    # 分析failed任务
    if failed_tasks:
        print(f"\n❌ failed任务分析 ({len(failed_tasks)}个):")
        for task in failed_tasks:
            print(f"  - {task.get('id', 'unknown')}")
            print(f"    标题: {task.get('title', 'unknown')}")
            print(f"    指令文件: {task.get('instruction_path', 'unknown')}")

    # 分析completed任务
    if completed_tasks:
        print(f"\n✅ completed任务分析 ({len(completed_tasks)}个):")

        # 检查completed任务的ID模式
        completed_patterns = {}
        for task in completed_tasks[:20]:
            task_id = task.get("id", "")
            if task_id:
                key = task_id.split("-")[0] if "-" in task_id else task_id[:20]
                completed_patterns[key] = completed_patterns.get(key, 0) + 1

        if completed_patterns:
            print("  ID前缀分布:")
            for pattern, count in sorted(
                completed_patterns.items(), key=lambda x: x[1], reverse=True
            )[:10]:
                print(f"    '{pattern}...': {count}个")

    # 检查队列整体状态
    print("\n📈 队列整体状态:")
    print(f"  queue_status: {data.get('queue_status', 'unknown')}")
    print(f"  current_item_id: {data.get('current_item_id', '空')}")
    print(f"  updated_at: {data.get('updated_at', '未知')}")

    # 建议
    print("\n💡 分析建议:")
    if len(manual_hold_tasks) > 0:
        print("  1. manual_hold任务数量很多(143个)，可能原因:")
        print("     • 预检函数(validate_build_preflight)拒绝了这些任务")
        print("     • 任务文档过长、格式不符合要求")
        print("     • 依赖条件不满足")
        print("     • 建议检查预检函数日志和任务指令文件")

    if len(failed_tasks) > 0:
        print("  2. failed任务阻塞了整个队列，需要修复:")
        print("     • 检查失败任务的指令文件是否存在")
        print("     • 查看队列运行器日志了解失败原因")
        print("     • 修复问题后重置任务状态")

    if data.get("queue_status") == "failed":
        print("  3. 队列状态为failed，需要修复:")
        print("     • 检查failed任务并修复")
        print("     • 或者重置队列状态为running")

    return 0


if __name__ == "__main__":
    sys.exit(analyze_manual_hold_tasks())
