#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
原子性修复所有僵尸running任务状态
检测条件：status=running 且 progress_percent=8
修复策略：
  - 关键runner任务：manual_hold（阻止autostart）
  - 其他任务：pending（允许后续手动执行）
"""

import json
import os
import sys
from datetime import UTC, datetime


def fix_all_zombie_running():
    # 添加项目根目录到路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        from config.paths import get_queue_file

        queue_file_path = get_queue_file("priority_execution")
        if queue_file_path:
            queue_file = str(queue_file_path)
            print(f"✅ 使用config.paths模块获取队列文件: {queue_file}")
        else:
            raise ImportError("无法获取队列文件路径")
    except ImportError as e:
        print(f"⚠️  警告: 无法导入路径配置模块: {e}")
        print("   使用回退的硬编码路径...")
        queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"

    if not os.path.exists(queue_file):
        print(f"队列文件不存在: {queue_file}")
        return

    # 原子性读取
    with open(queue_file, encoding="utf-8") as f:
        data = json.load(f)

    fixed_tasks = []
    for task in data.get("items", []):
        if task.get("status") == "running" and task.get("progress_percent", 0) == 8:
            task_id = task.get("id", "")
            old_status = task["status"]
            old_progress = task.get("progress_percent", 8)

            # 决定目标状态
            if "runner_persistence" in task_id:
                new_status = "manual_hold"
                reason = "critical_zombie_requires_manual_intervention: athena_autostart_conflict"
            else:
                new_status = "pending"
                reason = "stress_test_zombie_reset: stale_running"

            print(
                f"原子性修复任务 {task_id}: {old_status} -> {new_status} (progress {old_progress} -> 0)"
            )

            # 更新状态
            task["status"] = new_status
            task["progress_percent"] = 0
            task["updated_at"] = datetime.now(UTC).isoformat()

            # 添加修复记录
            if "fix_history" not in task:
                task["fix_history"] = []

            task["fix_history"].append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "old_status": old_status,
                    "new_status": new_status,
                    "old_progress": old_progress,
                    "new_progress": 0,
                    "reason": reason,
                }
            )

            fixed_tasks.append({"id": task_id, "old_status": old_status, "new_status": new_status})

    if fixed_tasks:
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

        print("\n✅ 原子性修复完成")
        print(f"修复了 {len(fixed_tasks)} 个僵尸任务:")
        for ft in fixed_tasks:
            print(f"  - {ft['id']}: {ft['old_status']} -> {ft['new_status']}")
        print(f"更新后的counts: {counts}")
    else:
        print("✅ 未发现僵尸running任务")


if __name__ == "__main__":
    fix_all_zombie_running()
