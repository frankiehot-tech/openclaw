#!/usr/bin/env python3
"""
调试运行器逻辑，理解为什么队列状态被重置为dependency_blocked
"""

import json
import os
import sys

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)
MANIFEST_FILE = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"


def simulate_materialize_route_items():
    """模拟materialize_route_items函数逻辑"""
    print("模拟materialize_route_items逻辑...")

    # 读取manifest
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    manifest_items = manifest_data.get("items", [])
    print(f"manifest项目数: {len(manifest_items)}")

    # 读取队列状态
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        route_state = json.load(f)
    items_state = route_state.get("items", {})
    print(f"队列状态项目数: {len(items_state)}")

    # 模拟materialize逻辑
    materialized = []
    for manifest_item in manifest_items:
        item_id = str(manifest_item.get("id", "") or "")
        state_item = items_state.get(item_id)
        state_item = state_item if isinstance(state_item, dict) else {}

        # 状态确定逻辑（第821行）
        status = str(state_item.get("status", "") or "pending")

        metadata = manifest_item.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}

        manual_override_autostart = bool(state_item.get("manual_override_autostart"))

        if (
            metadata.get("autostart") is False
            and status in {"", "pending"}
            and not manual_override_autostart
        ):
            status = "manual_hold"

        materialized.append(
            {
                "id": item_id,
                "status": status,
                "depends_on": metadata.get("depends_on", []),
                "title": manifest_item.get("title", item_id),
            }
        )

    return materialized


def simulate_compute_route_counts_and_status(materialized_items):
    """模拟compute_route_counts_and_status函数逻辑"""
    print("\n模拟compute_route_counts_and_status逻辑...")

    counts = {
        "pending": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "manual_hold": 0,
    }

    for item in materialized_items:
        status = str(item.get("status", "") or "pending")
        counts[status] = counts.get(status, 0) + 1

    print(f"计算出的计数: {json.dumps(counts, ensure_ascii=False)}")

    pending_items = [item for item in materialized_items if item.get("status") == "pending"]
    running_items = [item for item in materialized_items if item.get("status") == "running"]
    manual_hold_items = [item for item in materialized_items if item.get("status") == "manual_hold"]

    print(f"pending项目数: {len(pending_items)}")
    print(f"running项目数: {len(running_items)}")
    print(f"manual_hold项目数: {len(manual_hold_items)}")

    if not pending_items and not running_items:
        print("条件1: 没有pending和running项目")
        return counts, "manual_hold" if manual_hold_items else "empty"

    # 模拟is_pid_alive检查（假设没有running项目）
    print("条件2: 检查running项目的进程是否存活...")
    # 假设没有存活的进程

    item_by_id = {str(item.get("id", "")): item for item in materialized_items}
    blocked = False

    for item in pending_items:
        depends_on = item.get("depends_on", [])
        print(f"检查项目 {item.get('id')} 的依赖: {depends_on}")
        for dep_id in depends_on:
            dep_item = item_by_id.get(str(dep_id))
            if not dep_item or dep_item.get("status") != "completed":
                blocked = True
                print(
                    f"  发现阻塞依赖: {item.get('id')} 依赖于 {dep_id} (状态: {dep_item.get('status') if dep_item else '不存在'})"
                )
                break
        if blocked:
            break

    if blocked:
        print("条件3: 发现阻塞依赖")
        return counts, "dependency_blocked"

    if pending_items:
        print("条件4: 有pending项目但没有阻塞依赖")
        return counts, "no_consumer"

    print("条件5: 没有pending项目")
    return counts, "empty"


def main():
    print("调试运行器逻辑...")
    print("=" * 60)

    # 1. 模拟materialize_route_items
    materialized_items = simulate_materialize_route_items()

    # 2. 显示前几个项目的状态
    print("\n前10个项目的状态:")
    for i, item in enumerate(materialized_items[:10]):
        print(f"  {i+1}. {item.get('id')}: {item.get('status')}, 依赖: {item.get('depends_on')}")

    # 3. 统计状态分布
    status_counts = {}
    for item in materialized_items:
        status = item.get("status", "pending")
        status_counts[status] = status_counts.get(status, 0) + 1

    print("\n所有项目的状态分布:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    # 4. 模拟compute_route_counts_and_status
    counts, status = simulate_compute_route_counts_and_status(materialized_items)

    print(f"\n最终状态决策: {status}")

    # 5. 与实际队列状态比较
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        queue_data = json.load(f)

    actual_status = queue_data.get("queue_status", "unknown")
    print(f"\n实际队列状态: {actual_status}")

    if status == actual_status:
        print("✅ 模拟结果与实际状态一致")
    else:
        print(f"⚠️  模拟结果 ({status}) 与实际状态 ({actual_status}) 不一致")
        print("\n可能原因:")
        print("  1. 有running项目的进程存活检查")
        print("  2. 有其他条件未考虑")
        print("  3. 状态被其他逻辑覆盖")

    # 6. 检查pending项目的依赖关系
    print("\n详细检查pending项目的依赖关系:")
    pending_items = [item for item in materialized_items if item.get("status") == "pending"]

    for item in pending_items:
        depends_on = item.get("depends_on", [])
        if depends_on:
            print(f"  {item.get('id')} 依赖于: {depends_on}")
            for dep_id in depends_on:
                # 在materialized_items中查找依赖项
                dep_item = next((i for i in materialized_items if i.get("id") == dep_id), None)
                if dep_item:
                    print(f"    → {dep_id}: {dep_item.get('status')}")
                else:
                    print(f"    → {dep_id}: 不存在")
        else:
            print(f"  {item.get('id')}: 无依赖")


if __name__ == "__main__":
    main()
