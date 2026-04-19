#!/usr/bin/env python3
"""直接将gene_mgmt_audit任务状态重置为pending"""

import copy
import json
import os
from datetime import datetime

queue_file = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
)

print(f"🔧 重置任务状态: {queue_file}")

# 备份原文件
import shutil

backup_file = queue_file + ".backup_reset"
shutil.copy2(queue_file, backup_file)
print(f"📂 已创建备份: {backup_file}")

# 读取队列文件
with open(queue_file, "r", encoding="utf-8") as f:
    queue_data = json.load(f)

# 检查gene_mgmt_audit任务
if "gene_mgmt_audit" not in queue_data.get("items", {}):
    print("❌ 未找到gene_mgmt_audit任务")
    exit(1)

task_data = queue_data["items"]["gene_mgmt_audit"]
print(f"📋 当前任务状态:")
print(f"   ID: gene_mgmt_audit")
print(f"   标题: {task_data.get('title')}")
print(f"   状态: {task_data.get('status')}")
print(f"   错误: {task_data.get('error', '无')}")
print(f"   进度: {task_data.get('progress_percent', 0)}%")
print(f"   开始时间: {task_data.get('started_at')}")
print(f"   结束时间: {task_data.get('finished_at')}")

# 重置任务状态
now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

# 保留必要字段，重置状态相关字段
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

# 确保有必要的字段
if "retry_count" not in task_data:
    task_data["retry_count"] = 0
else:
    task_data["retry_count"] += 1
    task_data["last_retry_at"] = now

# 更新队列计数
counts = queue_data.get("counts", {})
pending_count = counts.get("pending", 0)
failed_count = counts.get("failed", 0)

if task_data["status"] == "failed":
    failed_count = max(0, failed_count - 1)

counts["pending"] = pending_count + 1
counts["failed"] = failed_count
queue_data["counts"] = counts

# 更新队列状态
queue_data["queue_status"] = "running"
queue_data["current_item_id"] = "gene_mgmt_audit"
queue_data["current_item_ids"] = ["gene_mgmt_audit"]
queue_data["updated_at"] = now

# 更新paused_reason
if "paused_reason" in queue_data:
    del queue_data["paused_reason"]

# 写回文件
with open(queue_file, "w", encoding="utf-8") as f:
    json.dump(queue_data, f, indent=2, ensure_ascii=False)

print(f"\n✅ 任务已重置:")
print(f"   新状态: pending")
print(f"   进度: 0%")
print(f"   重试计数: {task_data.get('retry_count', 0)}")
print(f"   队列状态: running")
print(f"   当前任务ID: gene_mgmt_audit")

# 验证写入
print(f"\n🔍 验证写入...")
with open(queue_file, "r", encoding="utf-8") as f:
    verify_data = json.load(f)

verify_task = verify_data["items"]["gene_mgmt_audit"]
print(f"   验证状态: {verify_task.get('status')}")
print(f"   验证进度: {verify_task.get('progress_percent')}%")

print(f"\n🚀 现在队列运行器应该能自动拾取并执行此任务。")
print(f"💡 提示: 如果任务仍然失败，请检查:")
print(f"   1. 预检验证是否通过 (已修复)")
print(f"   2. 指令文件是否有效")
print(f"   3. 系统资源是否充足")
print(f"   4. API密钥配置是否正确")
