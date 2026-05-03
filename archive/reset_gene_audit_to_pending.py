#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py task <command>
"""直接将gene_mgmt_audit任务状态重置为pending"""

import json
import shutil
from datetime import datetime


def main() -> None:
    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
    )

    print(f"配置重置任务状态: {queue_file}")

    # 备份原文件
    backup_file = queue_file + ".backup_reset"
    shutil.copy2(queue_file, backup_file)
    print(f"已创建备份: {backup_file}")

    # 读取队列文件
    with open(queue_file, encoding="utf-8") as f:
        queue_data = json.load(f)

    # 检查gene_mgmt_audit任务
    if "gene_mgmt_audit" not in queue_data.get("items", {}):
        print("未找到gene_mgmt_audit任务")
        return

    task_data = queue_data["items"]["gene_mgmt_audit"]
    print("当前任务状态:")
    print(f"   状态: {task_data.get('status')}")

    # 重置任务状态
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

    task_data["status"] = "pending"
    task_data["progress_percent"] = 0
    task_data["error"] = ""
    task_data["summary"] = "任务已重置为pending，等待执行"
    task_data["started_at"] = ""
    task_data["finished_at"] = ""
    task_data["runner_pid"] = ""
    task_data["runner_heartbeat_at"] = ""
    task_data["pipeline_summary"] = "OpenCode pending"
    task_data["artifact_paths"] = []

    if "retry_count" not in task_data:
        task_data["retry_count"] = 0
    else:
        task_data["retry_count"] += 1
        task_data["last_retry_at"] = now

    # 更新队列计数
    counts = queue_data.get("counts", {})
    counts["pending"] = counts.get("pending", 0) + 1
    queue_data["counts"] = counts

    # 更新队列状态
    queue_data["queue_status"] = "running"
    queue_data["current_item_id"] = "gene_mgmt_audit"
    queue_data["current_item_ids"] = ["gene_mgmt_audit"]
    queue_data["updated_at"] = now

    if "paused_reason" in queue_data:
        del queue_data["paused_reason"]

    # 写回文件
    with open(queue_file, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, indent=2, ensure_ascii=False)

    print("任务已重置为pending状态")


if __name__ == "__main__":
    main()
