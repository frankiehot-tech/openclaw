#!/usr/bin/env python3
"""
重置目标任务状态为pending
"""

import json
import shutil
from datetime import datetime


def main():
    state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    task_id = "-Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313"

    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if task_id not in data.get("items", {}):
        print(f"❌ 任务 {task_id} 不在状态文件中")
        return 1

    task = data["items"][task_id]
    print(f'当前任务状态: {task.get("status")}')
    print(f'当前错误: {task.get("error", "空")}')

    # 重置任务状态
    task["status"] = "pending"
    task["error"] = ""
    task["finished_at"] = ""
    task["started_at"] = ""
    task["progress_percent"] = 0

    # 清除执行相关字段（如果存在）
    for field in [
        "summary",
        "result_excerpt",
        "pipeline_summary",
        "runner_pid",
        "runner_heartbeat_at",
        "artifact_paths",
        "root_task_id",
        "last_auto_retry_reason",
        "blocked_rescue_retry_count",
        "last_blocked_rescue_retry_at",
        "last_blocked_rescue_retry_reason",
    ]:
        if field in task:
            if field == "artifact_paths":
                task[field] = []
            else:
                task[field] = ""

    # 确保manual_override_autostart为true
    task["manual_override_autostart"] = True

    # 重新计算counts
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
    for item_id, item in data.get("items", {}).items():
        status = item.get("status", "pending")
        if status in counts:
            counts[status] += 1
        else:
            counts["pending"] += 1

    data["counts"] = counts
    data["queue_status"] = "running"
    data["pause_reason"] = ""
    data["updated_at"] = datetime.now().isoformat()

    # 保存备份
    backup = state_file + ".reset_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(state_file, backup)
    print(f"✅ 创建备份: {backup}")

    # 写入文件
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ 任务状态重置为pending")
    print("✅ 设置manual_override_autostart=True")
    print(f"✅ counts: {json.dumps(counts, ensure_ascii=False, indent=2)}")

    # 验证manifest中的autostart
    manifest_file = ".openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    for item in manifest_data.get("items", []):
        if item.get("id") == task_id:
            metadata = item.get("metadata", {})
            if metadata.get("autostart") != True:
                print("⚠️  manifest中autostart不为True，正在修复...")
                metadata["autostart"] = True
                item["metadata"] = metadata

                manifest_backup = (
                    manifest_file + ".reset_" + datetime.now().strftime("%Y%m%d_%H%M%S")
                )
                shutil.copy2(manifest_file, manifest_backup)
                with open(manifest_file, "w", encoding="utf-8") as f:
                    json.dump(manifest_data, f, ensure_ascii=False, indent=2)
                print(f"✅ 修复manifest autostart=True")
            else:
                print("✅ manifest中autostart已为True")
            break

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
