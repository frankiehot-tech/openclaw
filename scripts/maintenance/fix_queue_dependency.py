#!/usr/bin/env python3
"""
修复队列依赖阻塞问题：
1. 将缺失状态条目的任务添加到状态文件中（状态为pending）
2. 检查跨队列依赖项，如果已完成，在当前状态文件中添加条目（状态为completed）
3. 更新counts和队列状态
"""
import json
from pathlib import Path
import sys
import shutil
import datetime

# 路径
state_path = Path(".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json")
manifest_path = Path(".openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json")
queue_dir = Path(".openclaw/plan_queue")

# 备份原文件
backup_path = state_path.with_suffix(".json.backup_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
shutil.copy2(state_path, backup_path)
print(f"备份状态文件到 {backup_path}")

# 加载状态和清单
with open(state_path) as f:
    state = json.load(f)
with open(manifest_path) as f:
    manifest = json.load(f)

state_items = state.get("items", {})
manifest_items = manifest.get("items", [])

# 收集所有队列文件中的任务状态
global_status = {}
for queue_file in queue_dir.glob("*.json"):
    if queue_file.name == state_path.name:
        continue
    try:
        with open(queue_file) as f:
            data = json.load(f)
            items = data.get("items", {})
            for item_id, item in items.items():
                status = item.get("status")
                if status:
                    global_status[item_id] = status
    except Exception as e:
        print(f"读取队列文件 {queue_file} 时出错: {e}")

print(f"从其他队列收集到 {len(global_status)} 个任务状态")

# 找出缺失状态条目的任务
missing_ids = []
for item in manifest_items:
    item_id = item.get("id")
    if item_id not in state_items:
        missing_ids.append(item_id)

print(f"缺失状态条目的任务数量: {len(missing_ids)}")

# 为缺失任务添加状态条目（pending）
added_count = 0
for item_id in missing_ids:
    # 在清单中找到对应任务
    manifest_item = next((i for i in manifest_items if i["id"] == item_id), None)
    if not manifest_item:
        continue
    # 创建状态条目
    state_items[item_id] = {
        "status": "pending",
        "title": manifest_item.get("title", item_id),
        "stage": manifest_item.get("entry_stage", "build"),
        "instruction_path": manifest_item.get("instruction_path", ""),
        "updated_at": datetime.datetime.now().isoformat(),
        "metadata": manifest_item.get("metadata", {})
    }
    added_count += 1

print(f"添加了 {added_count} 个状态条目")

# 处理依赖项：检查缺失任务的依赖项是否在其他队列中已完成
deps_added = 0
for item_id in missing_ids:
    manifest_item = next((i for i in manifest_items if i["id"] == item_id), None)
    if not manifest_item:
        continue
    deps = manifest_item.get("metadata", {}).get("depends_on", [])
    for dep_id in deps:
        # 如果依赖项不在状态文件中
        if dep_id not in state_items:
            # 检查全局状态
            dep_status = global_status.get(dep_id)
            if dep_status == "completed":
                # 添加已完成的状态条目
                state_items[dep_id] = {
                    "status": "completed",
                    "title": f"依赖项 {dep_id} (来自其他队列)",
                    "stage": "build",
                    "instruction_path": "",
                    "updated_at": datetime.datetime.now().isoformat(),
                    "finished_at": datetime.datetime.now().isoformat(),
                    "summary": "自动标记为已完成（跨队列依赖）"
                }
                deps_added += 1
                print(f"  添加已完成依赖项: {dep_id}")
            else:
                print(f"  警告: 依赖项 {dep_id} 状态未知或未完成: {dep_status}")

print(f"添加了 {deps_added} 个已完成依赖项")

# 更新状态文件
state["items"] = state_items

# 重新计算counts（模拟队列运行器逻辑）
# 使用简单的计数
counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
for item in state_items.values():
    status = str(item.get("status", "") or "pending")
    if status in counts:
        counts[status] += 1
    else:
        counts["pending"] += 1

state["counts"] = counts

# 根据counts设置队列状态
if counts["pending"] > 0:
    # 检查依赖阻塞
    # 简化：假设没有阻塞
    state["queue_status"] = "no_consumer"
    state["pause_reason"] = ""
else:
    state["queue_status"] = "empty"
    state["pause_reason"] = ""

# 写入更新
with open(state_path, "w") as f:
    json.dump(state, f, indent=2, ensure_ascii=False)

print(f"更新完成。新的counts: {counts}")
print(f"队列状态: {state['queue_status']}")