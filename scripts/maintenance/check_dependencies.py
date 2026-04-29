#!/usr/bin/env python3
"""
检查队列中的依赖关系，找出dependency_blocked的原因
"""

import json


def main():
    state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"

    print(f"加载状态文件: {state_file}")
    with open(state_file, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", {})

    # 创建任务ID到任务的映射
    item_by_id = {str(task_id): task for task_id, task in items.items()}

    print(f"总任务数: {len(items)}")
    print(f"pending任务数: {sum(1 for task in items.values() if task.get('status') == 'pending')}")
    print(f"running任务数: {sum(1 for task in items.values() if task.get('status') == 'running')}")
    print(
        f"completed任务数: {sum(1 for task in items.values() if task.get('status') == 'completed')}"
    )
    print(f"failed任务数: {sum(1 for task in items.values() if task.get('status') == 'failed')}")
    print(
        f"manual_hold任务数: {sum(1 for task in items.values() if task.get('status') == 'manual_hold')}"
    )

    # 检查dependency_blocked的逻辑
    blocked = False
    blocked_tasks = []

    pending_items = [
        (task_id, task) for task_id, task in items.items() if task.get("status") == "pending"
    ]

    print("\n检查pending任务的依赖关系...")
    for task_id, task in pending_items:
        depends_on = task.get("depends_on", [])
        if depends_on:
            print(f"\n任务: {task_id}")
            print(f"  摘要: {task.get('summary', '')[:80]}...")
            print(f"  依赖: {depends_on}")

            for dep_id in depends_on:
                dep_task = item_by_id.get(str(dep_id))
                if dep_task:
                    dep_status = dep_task.get("status", "unknown")
                    if dep_status != "completed":
                        print(f"    ⚠️  {dep_id}: 状态={dep_status} (未完成)")
                        blocked_tasks.append((task_id, dep_id, dep_status))
                        blocked = True
                else:
                    print(f"    ❌ {dep_id}: 任务不存在")
                    blocked_tasks.append((task_id, dep_id, "not_found"))
                    blocked = True

    if blocked:
        print("\n❌ 队列被阻塞，原因:")
        for task_id, dep_id, dep_status in blocked_tasks:
            print(f"  - {task_id} 被 {dep_id} 阻塞 (状态: {dep_status})")
    else:
        print("\n✅ 队列未被依赖阻塞")

        # 检查是否有pending但非依赖阻塞的任务
        if pending_items:
            print(f"  有 {len(pending_items)} 个pending任务，但无依赖阻塞")
            for task_id, task in pending_items[:5]:  # 只显示前5个
                print(f"  - {task_id}: {task.get('summary', '')[:60]}...")
            if len(pending_items) > 5:
                print(f"  ... 还有 {len(pending_items) - 5} 个任务")

    # 检查queue_status
    print("\n📊 队列状态:")
    print(f"  queue_status: {data.get('queue_status', 'unknown')}")
    print(f"  counts: {json.dumps(data.get('counts', {}), ensure_ascii=False)}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
