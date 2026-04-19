#!/usr/bin/env python3
"""
彻底分析队列状态，找出计数不一致的原因
"""

import json
import os
import sys

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)


def main():
    print("彻底分析队列状态...")

    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", {})
    print(f"总任务数: {len(items)}")

    # 统计状态分布
    status_counts = {}
    status_examples = {}

    for task_id, task_data in items.items():
        status = task_data.get("status", "pending")
        status_counts[status] = status_counts.get(status, 0) + 1

        if status not in status_examples:
            status_examples[status] = task_id

    print("\n实际状态分布:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count} (示例: {status_examples.get(status, 'N/A')})")

    # 文件中的计数
    file_counts = data.get("counts", {})
    print(f"\n文件中的计数: {json.dumps(file_counts, ensure_ascii=False)}")

    # 比较差异
    print("\n计数差异分析:")
    for status in set(list(status_counts.keys()) + list(file_counts.keys())):
        actual = status_counts.get(status, 0)
        file_count = file_counts.get(status, 0)
        if actual != file_count:
            print(f"  {status}: 实际={actual}, 文件={file_count}, 差异={file_count - actual}")

    # 详细检查pending任务
    print("\n详细检查pending任务:")
    pending_tasks = []
    for task_id, task_data in items.items():
        if task_data.get("status") == "pending":
            pending_tasks.append((task_id, task_data))

    print(f"找到 {len(pending_tasks)} 个pending任务:")
    for i, (task_id, task_data) in enumerate(pending_tasks[:10]):
        print(f"  {i+1}. {task_id}")
        print(f"     摘要: {task_data.get('summary', '')[:100]}...")
        print(
            f"     元数据: {json.dumps(task_data.get('metadata', {}), ensure_ascii=False)[:100]}..."
        )

    if len(pending_tasks) > 10:
        print(f"  ...还有 {len(pending_tasks) - 10} 个pending任务未显示")

    # 检查依赖关系
    print("\n依赖关系分析:")
    blocked_tasks = []
    for task_id, task_data in pending_tasks:
        depends_on = task_data.get("metadata", {}).get("depends_on", [])
        if depends_on:
            print(f"  任务 {task_id} 依赖于: {depends_on}")
            for dep_id in depends_on:
                dep_task = items.get(dep_id)
                if dep_task:
                    dep_status = dep_task.get("status", "unknown")
                    if dep_status != "completed":
                        blocked_tasks.append((task_id, dep_id, dep_status))
                        print(f"    → 依赖 {dep_id} 状态为 {dep_status} (阻塞)")
                else:
                    blocked_tasks.append((task_id, dep_id, "不存在"))
                    print(f"    → 依赖 {dep_id} 不存在 (阻塞)")

    if blocked_tasks:
        print(f"\n发现 {len(blocked_tasks)} 个阻塞依赖:")
        for task_id, dep_id, reason in blocked_tasks[:5]:
            print(f"  {task_id} → {dep_id} ({reason})")
    else:
        print("\n未发现阻塞依赖")

    # 检查queue_status
    queue_status = data.get("queue_status", "unknown")
    pause_reason = data.get("pause_reason", "")
    print(f"\n队列状态: {queue_status}")
    print(f"暂停原因: {pause_reason}")

    # 根据分析结果建议
    if blocked_tasks:
        print("\n💡 建议: 队列被标记为dependency_blocked是合理的，存在阻塞依赖")
    elif len(pending_tasks) == 0:
        print("\n💡 建议: 没有pending任务，队列状态应为empty")
    else:
        print("\n💡 建议: 有pending任务但无阻塞依赖，队列状态应为running或no_consumer")

    # 检查是否有running任务
    running_tasks = [tid for tid, task in items.items() if task.get("status") == "running"]
    if running_tasks:
        print(f"有 {len(running_tasks)} 个running任务: {running_tasks[:5]}")

    # 检查是否有manual_hold任务
    manual_hold_tasks = [tid for tid, task in items.items() if task.get("status") == "manual_hold"]
    if manual_hold_tasks:
        print(f"有 {len(manual_hold_tasks)} 个manual_hold任务")


if __name__ == "__main__":
    main()
