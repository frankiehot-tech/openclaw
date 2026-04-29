#!/usr/bin/env python3
"""
分析pending任务的依赖关系，找出为什么队列被标记为dependency_blocked
"""

import json

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)


def main():
    print("分析pending任务依赖关系...")

    with open(QUEUE_FILE, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", {})

    # 查找pending任务
    pending_tasks = []
    for task_id, task_data in items.items():
        if task_data.get("status") == "pending":
            pending_tasks.append((task_id, task_data))

    print(f"找到 {len(pending_tasks)} 个pending任务")

    # 检查每个pending任务的依赖关系
    for task_id, task_data in pending_tasks[:20]:  # 只检查前20个
        summary = task_data.get("summary", "")
        metadata = task_data.get("metadata", {})
        depends_on = metadata.get("depends_on", [])

        print(f"\n任务: {task_id}")
        print(f"  summary: {summary[:100]}...")
        print(f"  metadata depends_on: {depends_on}")

        # 检查依赖任务的状态
        if depends_on:
            for dep_id in depends_on:
                dep_task = items.get(dep_id)
                if dep_task:
                    dep_status = dep_task.get("status", "unknown")
                    print(f"    依赖任务 {dep_id}: {dep_status}")
                else:
                    print(f"    依赖任务 {dep_id}: 不存在于队列中")

        # 检查summary中的依赖信息
        if "被依赖项阻塞" in summary:
            print("  summary包含依赖阻塞信息")

    # 检查queue_status设置
    print(f"\n队列状态: {data.get('queue_status')}")
    print(f"暂停原因: {data.get('pause_reason')}")

    # 模拟compute_route_counts_and_status逻辑
    blocked = False
    for task_id, task_data in pending_tasks:
        depends_on = task_data.get("metadata", {}).get("depends_on", [])
        for dep_id in depends_on:
            dep_task = items.get(dep_id)
            if not dep_task or dep_task.get("status") != "completed":
                blocked = True
                print(
                    f"发现阻塞依赖: 任务 {task_id} 依赖于 {dep_id} (状态: {dep_task.get('status') if dep_task else '不存在'})"
                )
                break
        if blocked:
            break

    if blocked:
        print("\n队列被标记为dependency_blocked，因为存在pending任务依赖于非completed状态的任务")
    else:
        print("\n未发现明显的依赖阻塞，可能依赖关系在其他队列中或通过其他机制检查")


if __name__ == "__main__":
    main()
