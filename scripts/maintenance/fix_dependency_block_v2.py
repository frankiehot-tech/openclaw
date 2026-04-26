#!/usr/bin/env python3
"""
修复依赖阻塞问题 v2
修复athena_p0_schema_hitl_dispatch任务的依赖阻塞
"""

import json
import os
import shutil
from datetime import datetime


def main():
    state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"

    print(f"加载状态文件: {state_file}")
    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", {})

    # 修复athena_p0_schema_hitl_dispatch的依赖阻塞
    task_id = "athena_p0_schema_hitl_dispatch"
    if task_id in items:
        task = items[task_id]
        if task.get("status") == "pending" and "dependency blocked" in task.get(
            "pipeline_summary", ""
        ):
            print(f"🔧 修复任务: {task_id}")
            print(f"   当前状态: {task.get('status')}")
            print(f"   当前摘要: {task.get('summary', '')}")
            print(f"   当前pipeline_summary: {task.get('pipeline_summary', '')}")

            # 检查是否真的被阻塞
            summary = task.get("summary", "")
            if "phase1_runtime_closeout" in summary:
                # 检查phase1_runtime_closeout状态
                if "phase1_runtime_closeout" in items:
                    blocker_task = items["phase1_runtime_closeout"]
                    if blocker_task.get("status") == "completed":
                        print(f"   ✅ phase1_runtime_closeout状态为completed，解除阻塞")
                        # 更新摘要，移除阻塞信息
                        task["summary"] = "依赖已解除，等待执行"
                        task["pipeline_summary"] = "pending"
                        print(f"   → 更新摘要，移除阻塞信息")
                    else:
                        print(
                            f"   ⚠️  phase1_runtime_closeout状态为{blocker_task.get('status')}，可能需要修复"
                        )
                else:
                    print(f"   ⚠️  phase1_runtime_closeout任务不存在")
            else:
                print(f"   ℹ️  摘要中未提及phase1_runtime_closeout阻塞")

    # 重新计算counts
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
    for task_id, task in items.items():
        status = task.get("status", "pending")
        if status in counts:
            counts[status] += 1
        else:
            counts["pending"] += 1

    data["counts"] = counts

    # 更新queue_status
    pending_items = [task for task_id, task in items.items() if task.get("status") == "pending"]
    running_items = [task for task_id, task in items.items() if task.get("status") == "running"]
    manual_hold_items = [
        task for task_id, task in items.items() if task.get("status") == "manual_hold"
    ]

    if pending_items or running_items:
        data["queue_status"] = "running"
        data["pause_reason"] = ""
    elif manual_hold_items:
        data["queue_status"] = "manual_hold"
        data["pause_reason"] = "manual_hold"
    else:
        data["queue_status"] = "empty"
        data["pause_reason"] = "empty"

    data["updated_at"] = datetime.now().isoformat()

    # 创建备份
    backup = state_file + f'.dependency_fix_v2_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    shutil.copy2(state_file, backup)
    print(f"✅ 创建备份: {backup}")

    # 保存更新
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n📊 修复完成:")
    print(f"  新counts: {json.dumps(counts, ensure_ascii=False, indent=2)}")
    print(f"  新queue_status: {data['queue_status']}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
