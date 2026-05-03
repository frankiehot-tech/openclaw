#!/usr/bin/env python3
"""
找出所有被阻塞的任务
"""

import json


def main():
    manifest_file = ".openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"

    print(f"加载清单文件: {manifest_file}")
    with open(manifest_file, encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"加载状态文件: {state_file}")
    with open(state_file, encoding="utf-8") as f:
        state = json.load(f)

    manifest_items = manifest.get("items", [])
    state_items = state.get("items", {})

    # 创建状态映射
    state_by_id = dict(state_items.items())

    print("\n检查所有任务的依赖阻塞...")

    # 找出所有被阻塞的pending任务
    blocked_tasks = []
    unblocked_pending_tasks = []

    for item in manifest_items:
        item_id = str(item.get("id", ""))
        depends_on = item.get("metadata", {}).get("depends_on", [])

        # 检查任务状态
        task_state = state_by_id.get(item_id)
        if not task_state:
            # 任务尚未materialize
            continue

        task_status = task_state.get("status", "unknown")
        if task_status != "pending":
            continue  # 只检查pending任务

        is_blocked = False
        blocking_deps = []

        for dep_id in depends_on:
            dep_task = state_by_id.get(str(dep_id))
            if dep_task:
                dep_status = dep_task.get("status", "unknown")
                if dep_status != "completed":
                    is_blocked = True
                    blocking_deps.append((dep_id, dep_status))
            else:
                # 依赖任务在状态文件中不存在
                is_blocked = True
                blocking_deps.append((dep_id, "not_found"))

        if is_blocked:
            blocked_tasks.append((item_id, blocking_deps))
        else:
            unblocked_pending_tasks.append(item_id)

    print("\n📊 统计:")
    print(f"  总任务数: {len(manifest_items)}")
    print(f"  状态文件中任务数: {len(state_items)}")
    print(
        f"  pending任务数: {sum(1 for task in state_items.values() if task.get('status') == 'pending')}"
    )
    print(f"  被阻塞的pending任务: {len(blocked_tasks)}")
    print(f"  未被阻塞的pending任务: {len(unblocked_pending_tasks)}")

    if blocked_tasks:
        print("\n🚫 被阻塞的任务（阻塞依赖链）:")
        for i, (task_id, blocking_deps) in enumerate(blocked_tasks[:10]):  # 只显示前10个
            task_state = state_by_id.get(task_id)
            summary = task_state.get("summary", "")[:60] if task_state else "N/A"
            print(f"\n{i + 1}. {task_id}")
            print(f"   摘要: {summary}...")
            for dep_id, dep_status in blocking_deps:
                print(f"   被 {dep_id} 阻塞 (状态: {dep_status})")

        if len(blocked_tasks) > 10:
            print(f"\n... 还有 {len(blocked_tasks) - 10} 个被阻塞的任务")

        # 找出阻塞链的根节点
        print("\n🔍 阻塞链根节点（关键阻塞任务）:")
        root_blockers = set()
        for _task_id, blocking_deps in blocked_tasks:
            for dep_id, dep_status in blocking_deps:
                if dep_status in ["pending", "manual_hold", "failed"]:
                    # 检查这个依赖任务本身是否被阻塞
                    dep_task = state_by_id.get(str(dep_id))
                    if dep_task and dep_task.get("status") in ["pending", "manual_hold", "failed"]:
                        root_blockers.add((dep_id, dep_status))

        for dep_id, dep_status in list(root_blockers)[:10]:  # 只显示前10个
            dep_task = state_by_id.get(str(dep_id))
            summary = dep_task.get("summary", "")[:60] if dep_task else "N/A"
            print(f"  - {dep_id} (状态: {dep_status}): {summary}...")

    if unblocked_pending_tasks:
        print("\n✅ 未被阻塞的pending任务（可执行）:")
        for _i, task_id in enumerate(unblocked_pending_tasks[:10]):  # 只显示前10个
            task_state = state_by_id.get(task_id)
            summary = task_state.get("summary", "")[:60] if task_state else "N/A"
            print(f"  - {task_id}: {summary}...")

        if len(unblocked_pending_tasks) > 10:
            print(f"  ... 还有 {len(unblocked_pending_tasks) - 10} 个未被阻塞的任务")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
