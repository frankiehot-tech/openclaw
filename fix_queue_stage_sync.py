#!/usr/bin/env python3
"""
修复队列状态文件中的stage字段，与manifest文件的entry_stage同步
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from config.paths import PLAN_QUEUE_DIR, ROOT_DIR, SCRIPTS_DIR, get_queue_file
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    ROOT_DIR = Path("/Volumes/1TB-M2/openclaw")
    PLAN_QUEUE_DIR = ROOT_DIR / ".openclaw" / "plan_queue"
    SCRIPTS_DIR = ROOT_DIR / "scripts"

MANIFEST_FILE = str(SCRIPTS_DIR / "gene_management_queue_manifest.json")
QUEUE_FILE = str(PLAN_QUEUE_DIR / "openhuman_aiplan_gene_management_20260405.json")


def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(file_path, data):
    """保存JSON文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ 文件已保存: {file_path}")


def sync_stage_fields():
    """同步manifest的entry_stage到队列状态文件的stage字段"""
    print("🔧 同步stage字段...")

    if not os.path.exists(MANIFEST_FILE):
        print(f"❌ manifest文件不存在: {MANIFEST_FILE}")
        return False

    if not os.path.exists(QUEUE_FILE):
        print(f"❌ 队列文件不存在: {QUEUE_FILE}")
        return False

    # 加载文件
    manifest = load_json_file(MANIFEST_FILE)
    state = load_json_file(QUEUE_FILE)

    # 创建任务ID到entry_stage的映射
    task_entry_stage_map = {}
    for item in manifest.get("items", []):
        task_id = item.get("id")
        entry_stage = item.get("entry_stage")
        if task_id and entry_stage:
            task_entry_stage_map[task_id] = entry_stage

    print(f"📋 从manifest读取 {len(task_entry_stage_map)} 个任务的entry_stage配置")

    # 同步stage字段
    items = state.get("items", {})
    fixed_count = 0

    for task_id, task in items.items():
        if task_id in task_entry_stage_map:
            new_stage = task_entry_stage_map[task_id]
            current_stage = task.get("stage", "")

            if current_stage != new_stage:
                task["stage"] = new_stage
                fixed_count += 1
                print(f"  ✅ {task_id}: stage '{current_stage}' → '{new_stage}'")
            else:
                print(f"  ⏭️  {task_id}: stage已正确设置为 '{current_stage}'")

    # 修复队列状态
    if state.get("queue_status") == "manual_hold":
        # 找到第一个可执行的任务
        runnable_tasks = []
        for task_id, task in items.items():
            if task.get("status") in ["pending", "manual_hold"]:
                # 检查stage是否为build
                if task.get("stage") == "build":
                    runnable_tasks.append(task_id)

        if runnable_tasks:
            first_task = runnable_tasks[0]
            state["queue_status"] = "running"
            state["pause_reason"] = ""
            state["current_item_id"] = first_task
            state["current_item_ids"] = runnable_tasks
            state["updated_at"] = datetime.now(timezone.utc).isoformat()

            # 更新第一个任务状态
            items[first_task]["status"] = "running"
            items[first_task]["progress_percent"] = 0
            if not items[first_task].get("started_at"):
                items[first_task]["started_at"] = datetime.now(timezone.utc).isoformat()

            # 其他可执行任务设置为pending
            for i, task_id in enumerate(runnable_tasks):
                if i == 0:
                    continue
                items[task_id]["status"] = "pending"

            print(f"✅ 队列状态修复: manual_hold → running, 当前任务: {first_task}")
        else:
            print("⚠️  未找到可执行的build任务")

    # 重新计算计数
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

    for task_id, task in items.items():
        status = task.get("status")
        if status == "pending":
            counts["pending"] += 1
        elif status == "running":
            counts["running"] += 1
        elif status == "completed":
            counts["completed"] += 1
        elif status == "failed":
            counts["failed"] += 1
        elif status == "manual_hold":
            counts["manual_hold"] += 1

    state["counts"] = counts

    if fixed_count > 0 or state.get("queue_status") != "manual_hold":
        save_json_file(QUEUE_FILE, state)
        print(f"✅ 修复完成: 同步了 {fixed_count} 个任务的stage字段")
        print(f"📊 队列状态: {state.get('queue_status')}, 任务计数: {counts}")
        return True
    else:
        print("📋 无需修复")
        return False


def main():
    print("=" * 80)
    print("队列stage字段同步修复脚本")
    print("=" * 80)

    if sync_stage_fields():
        print("\n🎯 修复完成，建议重启队列运行器:")
        print("  pkill -f 'athena_ai_plan_runner.py daemon'")
        print(
            "  env DASHSCOPE_API_KEY=REDACTED_DASHSCOPE_KEY python3 scripts/athena_ai_plan_runner.py daemon --queue-id openhuman_aiplan_gene_management_20260405 > /tmp/queue_runner.log 2>&1 &"
        )
    else:
        print("\n📋 无需修复")


if __name__ == "__main__":
    main()
