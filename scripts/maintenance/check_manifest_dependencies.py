#!/usr/bin/env python3
"""
检查清单文件中的依赖关系
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

    print(f"\n清单任务数: {len(manifest_items)}")
    print(f"状态任务数: {len(state_items)}")

    # 创建状态映射
    state_by_id = dict(state_items.items())

    # 检查依赖关系
    blocked = False
    blocked_tasks = []

    print("\n检查依赖关系...")
    for item in manifest_items:
        item_id = str(item.get("id", ""))
        depends_on = item.get("metadata", {}).get("depends_on", [])

        if depends_on:
            # 检查每个依赖的状态
            for dep_id in depends_on:
                dep_task = state_by_id.get(str(dep_id))
                if dep_task:
                    dep_status = dep_task.get("status", "unknown")
                    if dep_status != "completed":
                        # 检查源任务状态
                        src_task = state_by_id.get(item_id)
                        src_status = src_task.get("status", "unknown") if src_task else "unknown"
                        if src_status == "pending":
                            print(f"❌ {item_id} 被 {dep_id} 阻塞 (状态: {dep_status})")
                            blocked_tasks.append((item_id, dep_id, dep_status))
                            blocked = True
                else:
                    # 依赖任务在状态文件中不存在
                    print(f"❌ {item_id} 依赖 {dep_id} (状态: 不存在)")
                    blocked_tasks.append((item_id, dep_id, "not_found"))
                    blocked = True

    if blocked:
        print("\n🚫 发现依赖阻塞:")
        for task_id, dep_id, dep_status in blocked_tasks:
            print(f"  - {task_id} → {dep_id} (状态: {dep_status})")

        # 显示具体阻塞链
        print("\n🔗 阻塞链分析:")
        for task_id, dep_id, dep_status in blocked_tasks:
            dep_task = state_by_id.get(str(dep_id))
            if dep_task:
                dep_summary = dep_task.get("summary", "")[:80]
                print(f"  {task_id}")
                print(f"    ↓ 被 {dep_id} 阻塞 ({dep_status}): {dep_summary}...")
    else:
        print("\n✅ 无依赖阻塞")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
