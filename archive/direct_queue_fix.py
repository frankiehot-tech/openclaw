#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
直接队列修复脚本
修复最后的manual_hold状态和no_consumer问题
"""

import json
import os
from datetime import UTC, datetime

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
)


def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def save_json_file(file_path, data):
    """保存JSON文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ 文件已保存: {file_path}")


def direct_fix():
    """直接修复队列状态"""
    print("🔧 直接修复队列状态...")

    if not os.path.exists(QUEUE_FILE):
        print(f"❌ 队列文件不存在: {QUEUE_FILE}")
        return False

    state = load_json_file(QUEUE_FILE)
    items = state.get("items", {})

    # 1. 重置所有stage="build"且status="manual_hold"的任务
    print("1. 重置manual_hold任务...")
    manual_hold_reset = 0

    for task_id, task in items.items():
        stage = task.get("stage", "")
        status = task.get("status", "")

        if stage == "build" and status == "manual_hold":
            task["status"] = "pending"
            task["error"] = ""
            task["finished_at"] = ""
            task["progress_percent"] = 0

            # 清理runner相关字段
            for field in ["runner_pid", "runner_heartbeat_at"]:
                if field in task:
                    del task[field]

            manual_hold_reset += 1
            print(f"   ✅ {task_id}: manual_hold → pending")

    # 2. 找到可执行的任务 (stage=build, status=pending)
    print("\n2. 选择可执行任务...")
    runnable_tasks = []

    for task_id, task in items.items():
        stage = task.get("stage", "")
        status = task.get("status", "")

        if stage == "build" and status == "pending":
            runnable_tasks.append(task_id)

    print(f"   找到 {len(runnable_tasks)} 个可执行任务")

    # 3. 修复队列状态
    print("\n3. 修复队列状态...")

    if runnable_tasks:
        # 选择第一个任务
        first_task = runnable_tasks[0]

        state["queue_status"] = "running"
        state["pause_reason"] = ""
        state["current_item_id"] = first_task
        state["current_item_ids"] = runnable_tasks
        state["updated_at"] = datetime.now(UTC).isoformat()

        # 设置第一个任务为running
        items[first_task]["status"] = "running"
        items[first_task]["progress_percent"] = 0
        if not items[first_task].get("started_at"):
            items[first_task]["started_at"] = datetime.now(UTC).isoformat()

        print("   ✅ 队列状态: no_consumer → running")
        print(f"   ✅ 当前任务: {first_task}")
    else:
        print("   ⚠️  未找到可执行任务，保持队列为running状态")
        state["queue_status"] = "running"
        state["pause_reason"] = ""
        state["current_item_id"] = ""
        state["current_item_ids"] = []

    # 4. 重新计算计数
    print("\n4. 重新计算任务计数...")

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

    # 5. 保存修复
    print("\n5. 保存修复...")
    save_json_file(QUEUE_FILE, state)

    print("\n🎯 修复完成总结:")
    print(f"   • 重置manual_hold任务: {manual_hold_reset}")
    print(f"   • 可执行任务数量: {len(runnable_tasks)}")
    print(f"   • 队列状态: {state.get('queue_status')}")
    print(f"   • 当前任务: {state.get('current_item_id', '空')}")
    print(f"   • 任务计数: {counts}")

    return True


def main():
    print("=" * 80)
    print("直接队列修复脚本 - 解决最后的manual_hold和no_consumer问题")
    print("=" * 80)

    # 执行修复
    if direct_fix():
        print("\n🔧 修复完成，建议:")
        print("1. 重启队列运行器以确保使用最新状态")
        print("2. 访问 http://127.0.0.1:8080 测试手动拉起功能")
        print("3. 运行监控脚本: python3 scripts/queue_monitor.py --alert")
    else:
        print("\n❌ 修复失败")


if __name__ == "__main__":
    main()
