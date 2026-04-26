#!/usr/bin/env python3
"""
修复nanobot依赖链的过时阻塞警告
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
    fixed_count = 0

    # 修复nanobot_auto_repair_bridge - 检查nanobot_health_incident_contract状态
    bridge_id = "nanobot_auto_repair_bridge"
    smoke_id = "nanobot_auto_repair_smoke"
    route_id = "nanobot_inspection_auto_route"
    health_id = "nanobot_health_incident_contract"

    if bridge_id in items:
        bridge_task = items[bridge_id]
        if bridge_task.get("status") == "pending" and "dependency blocked" in bridge_task.get(
            "pipeline_summary", ""
        ):
            print(f"🔧 检查任务: {bridge_id}")
            print(f"   当前摘要: {bridge_task.get('summary', '')}")

            # 检查nanobot_health_incident_contract状态
            if health_id in items:
                health_task = items[health_id]
                health_status = health_task.get("status", "unknown")
                print(f"   依赖任务 {health_id} 状态: {health_status}")

                if health_status == "completed":
                    print(f"   ✅ {health_id} 已标记为completed，解除阻塞")
                    # 更新摘要，移除阻塞信息
                    bridge_task["summary"] = "依赖已解除，等待执行"
                    bridge_task["pipeline_summary"] = "pending"
                    fixed_count += 1
                else:
                    print(f"   ⚠️  {health_id} 状态为 {health_status}，仍需处理")
            else:
                print(f"   ⚠️  {health_id} 任务不存在")

    # 检查并修复整个依赖链
    if smoke_id in items:
        smoke_task = items[smoke_id]
        if smoke_task.get("status") == "pending" and "dependency blocked" in smoke_task.get(
            "pipeline_summary", ""
        ):
            print(f"\n🔧 检查任务: {smoke_id}")
            print(f"   当前摘要: {smoke_task.get('summary', '')}")

            # 检查nanobot_auto_repair_bridge状态
            if bridge_id in items:
                bridge_task = items[bridge_id]
                bridge_status = bridge_task.get("status", "unknown")
                print(f"   依赖任务 {bridge_id} 状态: {bridge_status}")

                if bridge_status == "pending" and bridge_task.get("pipeline_summary") == "pending":
                    # 如果桥接任务已经被修复为pending（非阻塞状态），则修复烟熏任务
                    print(f"   ✅ {bridge_id} 已解除阻塞，修复{smoke_id}")
                    smoke_task["summary"] = "依赖已解除，等待执行"
                    smoke_task["pipeline_summary"] = "pending"
                    fixed_count += 1

    if route_id in items:
        route_task = items[route_id]
        if route_task.get("status") == "pending" and "dependency blocked" in route_task.get(
            "pipeline_summary", ""
        ):
            print(f"\n🔧 检查任务: {route_id}")
            print(f"   当前摘要: {route_task.get('summary', '')}")

            # 检查nanobot_auto_repair_smoke状态
            if smoke_id in items:
                smoke_task = items[smoke_id]
                smoke_status = smoke_task.get("status", "unknown")
                print(f"   依赖任务 {smoke_id} 状态: {smoke_status}")

                if smoke_status == "pending" and smoke_task.get("pipeline_summary") == "pending":
                    # 如果烟熏任务已经被修复为pending（非阻塞状态），则修复路由任务
                    print(f"   ✅ {smoke_id} 已解除阻塞，修复{route_id}")
                    route_task["summary"] = "依赖已解除，等待执行"
                    route_task["pipeline_summary"] = "pending"
                    fixed_count += 1

    if fixed_count > 0:
        # 更新队列状态
        data["updated_at"] = datetime.now().isoformat()

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

        if pending_items or running_items:
            data["queue_status"] = "running"
            data["pause_reason"] = ""
        else:
            data["queue_status"] = "empty"
            data["pause_reason"] = "empty"

        # 创建备份
        backup = state_file + f'.nanobot_fix_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2(state_file, backup)
        print(f"\n✅ 创建备份: {backup}")

        # 保存更新
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n📊 修复完成:")
        print(f"  修复任务数: {fixed_count}")
        print(f"  新counts: {json.dumps(counts, ensure_ascii=False)}")
        print(f"  新queue_status: {data['queue_status']}")
    else:
        print(f"\n⚠️  没有需要修复的nanobot依赖链阻塞")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
