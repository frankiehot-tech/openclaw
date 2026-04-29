#!/usr/bin/env python3
"""
更新队列状态，根据实际任务状态重新计算queue_status
"""

import json
import shutil
from datetime import datetime


def main():
    state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"

    print(f"加载状态文件: {state_file}")
    with open(state_file, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", {})

    # 重新计算counts
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
    for _task_id, task in items.items():
        status = task.get("status", "pending")
        if status in counts:
            counts[status] += 1
        else:
            counts["pending"] += 1

    data["counts"] = counts

    # 根据实际状态更新queue_status
    pending_items = [task for task_id, task in items.items() if task.get("status") == "pending"]
    running_items = [task for task_id, task in items.items() if task.get("status") == "running"]
    manual_hold_items = [
        task for task_id, task in items.items() if task.get("status") == "manual_hold"
    ]

    print("📊 任务统计:")
    print(f"  pending: {len(pending_items)}")
    print(f"  running: {len(running_items)}")
    print(f"  completed: {counts['completed']}")
    print(f"  failed: {counts['failed']}")
    print(f"  manual_hold: {len(manual_hold_items)}")

    # 检查是否有正在运行的任务
    has_running = len(running_items) > 0

    # 检查是否有pending任务
    has_pending = len(pending_items) > 0

    # 简单的queue_status逻辑
    if not has_pending and not has_running:
        if manual_hold_items:
            data["queue_status"] = "manual_hold"
            data["pause_reason"] = "manual_hold"
        else:
            data["queue_status"] = "empty"
            data["pause_reason"] = "empty"
    elif has_running:
        data["queue_status"] = "running"
        data["pause_reason"] = ""
    else:
        # 只有pending任务，没有running任务
        # 检查是否被依赖阻塞
        # 这里简化处理：如果有pending任务且没有running任务，标记为running让队列继续
        data["queue_status"] = "running"
        data["pause_reason"] = ""

    data["updated_at"] = datetime.now().isoformat()

    # 创建备份
    backup = state_file + f".queue_status_fix_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(state_file, backup)
    print(f"✅ 创建备份: {backup}")

    # 保存更新
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n📊 队列状态更新完成:")
    print(f"  新counts: {json.dumps(counts, ensure_ascii=False)}")
    print(f"  新queue_status: {data['queue_status']}")
    print(f"  pause_reason: {data.get('pause_reason', '')}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
