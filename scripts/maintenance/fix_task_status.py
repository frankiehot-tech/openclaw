#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复目标任务状态为pending
"""

import json
import sys
from datetime import datetime


def main():
    task_id = "-Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313"

    # 1. 修复状态文件
    state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    print(f"修复状态文件: {state_file}")

    with open(state_file, encoding="utf-8") as f:
        state_data = json.load(f)

    items = state_data.get("items", {})
    if task_id not in items:
        print(f"❌ 任务 {task_id} 不在状态文件中")
        return 1

    # 更新任务状态
    items[task_id]["status"] = "pending"
    items[task_id]["error"] = ""
    items[task_id]["finished_at"] = ""
    items[task_id]["started_at"] = ""
    items[task_id]["progress_percent"] = 0

    # 重新计算counts
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
    for task in items.values():
        status = task.get("status", "pending")
        if status in counts:
            counts[status] += 1
        else:
            counts["pending"] += 1

    state_data["counts"] = counts
    state_data["queue_status"] = "running"
    state_data["pause_reason"] = ""
    state_data["updated_at"] = datetime.now().isoformat()

    # 保存备份
    import shutil

    backup = state_file + ".backup_before_fix"
    shutil.copy2(state_file, backup)
    print(f"✅ 状态文件备份: {backup}")

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state_data, f, ensure_ascii=False, indent=2)

    print("✅ 状态文件更新完成")
    print(f"  任务状态: {items[task_id]['status']}")
    print(f"  counts: {json.dumps(counts, ensure_ascii=False, indent=4)}")

    # 2. 修复manifest文件（如果需要）
    manifest_file = ".openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    print(f"\n检查manifest文件: {manifest_file}")

    with open(manifest_file, encoding="utf-8") as f:
        manifest_data = json.load(f)

    manifest_items = manifest_data.get("items", [])
    updated = False
    for item in manifest_items:
        if item.get("id") == task_id:
            if "status" not in item or item.get("status") != "pending":
                item["status"] = "pending"
                updated = True
                print("✅ 更新manifest中任务状态为pending")
            break

    if updated:
        # 保存manifest备份
        manifest_backup = manifest_file + ".backup_before_fix"
        shutil.copy2(manifest_file, manifest_backup)
        print(f"✅ manifest备份: {manifest_backup}")

        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        print("✅ manifest文件更新完成")
    else:
        print("⚠️  manifest中未找到任务或状态已经是pending")

    # 3. 运行诊断确认修复
    print("\n🔍 运行诊断确认修复...")
    try:
        sys.path.insert(0, "scripts")
        from athena_ai_plan_runner import (
            compute_route_counts_and_status,
            materialize_route_items,
        )

        with open(".athena-auto-queue.json", encoding="utf-8") as f:
            config = json.load(f)

        route = None
        for r in config.get("routes", []):
            if r.get("queue_id") == "openhuman_aiplan_build_priority_20260328":
                route = r
                break

        if route:
            with open(state_file, encoding="utf-8") as f:
                route_state = json.load(f)

            materialized = materialize_route_items(route, route_state)
            counts, status = compute_route_counts_and_status(route, route_state)

            print("诊断结果:")
            print(f"  状态: {status}")
            print(f"  counts: {json.dumps(counts, ensure_ascii=False, indent=4)}")

            # 检查目标任务在materialized中的状态
            for item in materialized:
                if item.get("id") == task_id:
                    print(f"  目标任务在materialized中状态: {item.get('status')}")
                    break
    except Exception as e:
        print(f"诊断失败: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
