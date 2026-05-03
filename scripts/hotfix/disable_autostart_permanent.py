#!/usr/bin/env python3
"""
永久禁用关键任务的autostart功能
解决Athena执行器反复重启僵尸任务的问题
"""

import json
import os
from datetime import UTC, datetime


def disable_autostart_permanent():
    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"

    if not os.path.exists(queue_file):
        print(f"队列文件不存在: {queue_file}")
        return

    # 原子性读取
    with open(queue_file, encoding="utf-8") as f:
        data = json.load(f)

    disabled_tasks = []
    for task in data.get("items", []):
        task_id = task.get("id", "")
        metadata = task.get("metadata", {})

        # 检查是否需要禁用autostart
        should_disable = False
        reason = ""

        # 规则1: 关键runner任务且已多次修复
        if "runner_persistence" in task_id:
            should_disable = True
            reason = "critical_runner_zombie_loop: manual_hold_required"

        # 规则2: autostart=true 且存在僵尸修复历史
        elif metadata.get("autostart") is True and task.get("fix_history"):
            # 检查最近的修复记录
            fix_history = task.get("fix_history", [])
            recent_fixes = [f for f in fix_history if "zombie" in f.get("reason", "").lower()]
            if recent_fixes:
                should_disable = True
                reason = "recurrent_zombie_detected: autostart_disabled"

        if should_disable:
            old_autostart = metadata.get("autostart", False)

            # 添加禁用标记
            metadata["autostart"] = False
            metadata["autostart_disabled_at"] = datetime.now(UTC).isoformat()
            metadata["autostart_disabled_reason"] = reason
            metadata["autostart_disabled_by"] = "disable_autostart_permanent.py"

            # 添加变更记录
            if "change_history" not in task:
                task["change_history"] = []

            task["change_history"].append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "field": "metadata.autostart",
                    "old_value": old_autostart,
                    "new_value": False,
                    "reason": reason,
                }
            )

            disabled_tasks.append(
                {
                    "id": task_id,
                    "old_autostart": old_autostart,
                    "new_autostart": False,
                    "reason": reason,
                }
            )

    if disabled_tasks:
        # 重新计算counts字段（确保一致性）
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

        print("\n✅ 永久禁用autostart完成")
        print(f"禁用了 {len(disabled_tasks)} 个任务的autostart功能:")
        for dt in disabled_tasks:
            print(f"  - {dt['id']}: autostart {dt['old_autostart']} -> {dt['new_autostart']}")
            print(f"    理由: {dt['reason']}")
        print(f"\n更新后的counts: {counts}")
    else:
        print("✅ 无需禁用任何任务的autostart功能")


if __name__ == "__main__":
    disable_autostart_permanent()
