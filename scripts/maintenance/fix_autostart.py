#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复autostart和manual_override_autostart
"""

import json
import sys
from datetime import datetime


def main():
    task_id = "-Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313"

    # 1. 修复manifest中的autostart
    manifest_file = ".openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    print(f"修复manifest: {manifest_file}")

    with open(manifest_file, encoding="utf-8") as f:
        manifest_data = json.load(f)

    manifest_items = manifest_data.get("items", [])
    updated_manifest = False
    for item in manifest_items:
        if item.get("id") == task_id:
            metadata = item.get("metadata", {})
            if metadata.get("autostart") is False:
                metadata["autostart"] = True
                item["metadata"] = metadata
                updated_manifest = True
                print("✅ 设置manifest中autostart=True")
            elif "autostart" not in metadata:
                metadata["autostart"] = True
                item["metadata"] = metadata
                updated_manifest = True
                print("✅ 添加manifest中autostart=True")
            break

    if updated_manifest:
        import shutil

        backup = manifest_file + ".backup_autostart_fix"
        shutil.copy2(manifest_file, backup)
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        print("✅ manifest更新完成")

    # 2. 修复状态文件中的manual_override_autostart
    state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    print(f"\n修复状态文件: {state_file}")

    with open(state_file, encoding="utf-8") as f:
        state_data = json.load(f)

    items = state_data.get("items", {})
    if task_id in items:
        items[task_id]["manual_override_autostart"] = True
        # 确保状态是pending
        items[task_id]["status"] = "pending"
        items[task_id]["error"] = ""

        print("✅ 设置状态文件中manual_override_autostart=True")
        print("✅ 确保状态为pending")

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

        backup = state_file + ".backup_autostart_fix"
        shutil.copy2(state_file, backup)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
        print("✅ 状态文件更新完成")
        print(f"  counts: {json.dumps(counts, ensure_ascii=False, indent=4)}")
    else:
        print("❌ 任务不在状态文件中")

    # 3. 验证修复
    print("\n🔍 验证修复...")
    try:
        sys.path.insert(0, "scripts")
        from athena_ai_plan_runner import materialize_route_items

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
            for item in materialized:
                if item.get("id") == task_id:
                    print(f"  目标任务在materialized中状态: {item.get('status')}")
                    print(f"  任务metadata: {item.get('metadata', {})}")
                    break
    except Exception as e:
        print(f"验证失败: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
