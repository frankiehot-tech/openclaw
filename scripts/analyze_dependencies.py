#!/usr/bin/env python3
"""
分析队列依赖关系，找出阻塞的根本原因
"""

import json
import os


def load_json(filepath):
    """加载JSON文件"""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def main():
    print("分析队列依赖关系...")

    # 加载manifest
    manifest_path = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    if not os.path.exists(manifest_path):
        print(f"Manifest文件不存在: {manifest_path}")
        return

    manifest = load_json(manifest_path)
    items = manifest.get("items", [])

    # 加载队列状态
    queue_state_path = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    if not os.path.exists(queue_state_path):
        print(f"队列状态文件不存在: {queue_state_path}")
        return

    queue_state = load_json(queue_state_path)
    queue_items = queue_state.get("items", {})

    print(f"Manifest中有 {len(items)} 个任务")
    print(f"队列状态中有 {len(queue_items)} 个任务")

    # 创建任务ID到状态的映射
    task_status = {}
    for task_id, task_data in queue_items.items():
        task_status[task_id] = task_data.get("status", "unknown")

    # 对于manifest中但不在队列状态中的任务，使用manifest状态
    for item in items:
        task_id = item.get("id")
        if task_id not in task_status:
            task_status[task_id] = item.get("status", "unknown")

    # 分析依赖关系
    blocked_tasks = []
    blocking_deps = {}

    for item in items:
        task_id = item.get("id")
        depends_on = item.get("metadata", {}).get("depends_on", [])

        if not depends_on:
            continue

        status = task_status.get(task_id, "unknown")
        if status == "pending":
            # 检查依赖项是否完成
            for dep_id in depends_on:
                dep_status = task_status.get(dep_id, "unknown")
                if dep_status not in ["completed", "failed"]:
                    # 依赖项未完成，任务被阻塞
                    blocked_tasks.append(task_id)
                    if task_id not in blocking_deps:
                        blocking_deps[task_id] = []
                    blocking_deps[task_id].append((dep_id, dep_status))

    print(f"\n被阻塞的任务数量: {len(blocked_tasks)}")
    if blocked_tasks:
        print("\n被阻塞的任务列表:")
        for task_id in blocked_tasks[:20]:  # 最多显示20个
            deps = blocking_deps.get(task_id, [])
            deps_str = ", ".join([f"{dep_id} ({status})" for dep_id, status in deps])
            print(f"  - {task_id}: 依赖项未完成 [{deps_str}]")

        if len(blocked_tasks) > 20:
            print(f"  ... 以及另外 {len(blocked_tasks) - 20} 个任务")

    # 找出阻塞链的根节点
    print("\n分析阻塞根节点...")
    root_blockers = {}

    for task_id, deps in blocking_deps.items():
        for dep_id, dep_status in deps:
            if dep_status == "pending":
                # 检查这个依赖项是否也被阻塞
                if dep_id in blocked_tasks:
                    # 传递性阻塞
                    pass
                else:
                    # 可能是根阻塞节点
                    if dep_id not in root_blockers:
                        root_blockers[dep_id] = []
                    root_blockers[dep_id].append(task_id)

    print(f"阻塞根节点数量: {len(root_blockers)}")
    for blocker_id, blocking_tasks in list(root_blockers.items())[:10]:
        blocker_status = task_status.get(blocker_id, "unknown")
        print(f"  - {blocker_id} ({blocker_status}) 阻塞了 {len(blocking_tasks)} 个任务")

    # 输出总体统计
    status_counts = {}
    for status in task_status.values():
        status_counts[status] = status_counts.get(status, 0) + 1

    print("\n任务状态统计:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    # 检查特定任务的状态
    critical_tasks = [
        "aiplan_queue_runner_persistence",
        "aiplan_queue_runner_closeout",
        "phase1_runtime_closeout",
        "athena_p0_schema_hitl_dispatch",
        "athena_validation_moat_build",
    ]

    print("\n关键任务状态:")
    for task_id in critical_tasks:
        status = task_status.get(task_id, "not_found")
        depends_on = None
        for item in items:
            if item.get("id") == task_id:
                depends_on = item.get("metadata", {}).get("depends_on", [])
                break
        print(f"  {task_id}: {status}, 依赖项: {depends_on}")


if __name__ == "__main__":
    main()
