#!/usr/bin/env python3
"""
更新manifest文件中任务的状态，使其与队列状态文件同步
将manifest中对应队列状态文件中pending任务的状态更新为pending
"""

import json
import sys
from pathlib import Path


def main():
    # 路径
    manifest_path = Path(
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    )
    queue_state_path = Path(
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    )

    print(f"读取manifest文件: {manifest_path}")
    print(f"读取队列状态文件: {queue_state_path}")

    # 读取manifest文件
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    # 读取队列状态文件
    with open(queue_state_path, encoding="utf-8") as f:
        queue_state = json.load(f)

    # 从队列状态文件中提取pending任务的ID
    pending_task_ids = []
    if "items" in queue_state:
        for task_id, task_data in queue_state["items"].items():
            if task_data.get("status") == "pending":
                pending_task_ids.append(task_id)

    print(f"找到 {len(pending_task_ids)} 个pending任务:")
    for task_id in pending_task_ids:
        print(f"  - {task_id}")

    # 更新manifest中的任务状态
    updated_count = 0
    if "items" in manifest:
        for task in manifest["items"]:
            task_id = task.get("id")
            if task_id in pending_task_ids:
                # 检查当前状态
                current_status = task.get("status", "unknown")
                if current_status != "pending":
                    task["status"] = "pending"
                    task["progress_percent"] = 0
                    task["updated_at"] = queue_state["items"][task_id].get(
                        "updated_at", "2026-04-18T00:00:00.000000"
                    )
                    updated_count += 1
                    print(f"  更新任务 {task_id}: {current_status} -> pending")

    print(f"更新了 {updated_count} 个任务的状态")

    # 保存更新后的manifest
    if updated_count > 0:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"已保存更新到 {manifest_path}")
    else:
        print("没有需要更新的任务")

    return 0


if __name__ == "__main__":
    sys.exit(main())
