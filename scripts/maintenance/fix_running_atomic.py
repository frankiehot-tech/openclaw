#!/usr/bin/env python3
"""
原子性修复running任务状态
"""

import json
import os
from datetime import datetime, timezone


def fix_running_atomic():
    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"

    if not os.path.exists(queue_file):
        print(f"队列文件不存在: {queue_file}")
        return

    # 原子性读取
    with open(queue_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    fixed = False
    for task in data.get("items", []):
        if task.get("id") == "aiplan_queue_runner_persistence" and task.get("status") == "running":
            print(
                f"原子性修复任务 {task['id']}: running -> manual_hold (progress {task.get('progress_percent', 8)} -> 0)"
            )

            # 保存旧状态
            old_status = task["status"]
            old_progress = task.get("progress_percent", 8)

            # 更新状态
            task["status"] = "manual_hold"
            task["progress_percent"] = 0
            task["updated_at"] = datetime.now(timezone.utc).isoformat()

            # 添加修复记录
            if "fix_history" not in task:
                task["fix_history"] = []

            task["fix_history"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "old_status": old_status,
                    "new_status": "manual_hold",
                    "old_progress": old_progress,
                    "new_progress": 0,
                    "reason": "atomic_intervention: athena_autostart_conflict_resolution",
                }
            )
            fixed = True
            break

    if fixed:
        # 重新计算counts字段
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
        for task in data.get("items", []):
            status = task.get("status", "").strip().lower()
            if status in counts:
                counts[status] += 1
            else:
                counts["pending"] += 1

        data["counts"] = counts

        # 原子性写入
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"原子性修复完成")
        print(f"更新后的counts: {counts}")
    else:
        print("任务状态已正确或不存在")


if __name__ == "__main__":
    fix_running_atomic()
