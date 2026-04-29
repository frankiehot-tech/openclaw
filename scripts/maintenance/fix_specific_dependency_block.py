#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复特定任务的依赖阻塞状态
"""

import json
import shutil
from datetime import datetime


def main():
    state_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"

    print(f"加载状态文件: {state_file}")
    with open(state_file, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", {})

    # 需要修复的任务链
    task_chain = [
        "athena_p0_schema_hitl_dispatch",
        "athena_skill_wiring_cli_anything",
        "athena_validation_moat_build",
    ]

    fixed_count = 0

    for task_id in task_chain:
        if task_id in items:
            task = items[task_id]
            if task.get("pipeline_summary") == "dependency blocked":
                print(f"🔧 修复任务: {task_id}")
                print(f"   当前摘要: {task.get('summary', '')}")
                print(f"   当前状态: {task.get('status', 'unknown')}")

                # 检查依赖是否已满足
                # 对于athena_p0_schema_hitl_dispatch，检查phase1_runtime_closeout状态
                if task_id == "athena_p0_schema_hitl_dispatch":
                    dep_id = "phase1_runtime_closeout"
                    if dep_id in items:
                        dep_task = items[dep_id]
                        dep_status = dep_task.get("status", "unknown")
                        print(f"   依赖任务 {dep_id} 状态: {dep_status}")

                        if dep_status == "completed":
                            print("   ✅ 依赖已满足，解除阻塞")
                            # 更新摘要
                            task["summary"] = "依赖已解除，等待执行"
                            task["pipeline_summary"] = "pending"
                            fixed_count += 1
                        else:
                            print(f"   ⚠️  依赖状态为 {dep_status}，仍需处理")

                # 对于依赖athena_p0_schema_hitl_dispatch的任务
                elif task_id in [
                    "athena_skill_wiring_cli_anything",
                    "athena_validation_moat_build",
                ]:
                    dep_id = "athena_p0_schema_hitl_dispatch"
                    if dep_id in items:
                        dep_task = items[dep_id]
                        dep_status = dep_task.get("status", "unknown")
                        dep_pipeline = dep_task.get("pipeline_summary", "")
                        print(f"   依赖任务 {dep_id} 状态: {dep_status}, pipeline: {dep_pipeline}")

                        # 如果依赖任务已经解除阻塞（pipeline_summary不是dependency blocked）
                        if dep_pipeline != "dependency blocked" and dep_status == "pending":
                            print("   ✅ 依赖已解除，解除阻塞")
                            task["summary"] = "依赖已解除，等待执行"
                            task["pipeline_summary"] = "pending"
                            fixed_count += 1
                        else:
                            print("   ⚠️  依赖仍被阻塞")

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

        # 更新queue_status - 检查是否还有dependency blocked任务
        has_dependency_blocked = False
        for task_id, task in items.items():
            if task.get("pipeline_summary") == "dependency blocked":
                has_dependency_blocked = True
                break

        pending_items = [task for task_id, task in items.items() if task.get("status") == "pending"]
        running_items = [task for task_id, task in items.items() if task.get("status") == "running"]

        if has_dependency_blocked:
            data["queue_status"] = "dependency_blocked"
            data["pause_reason"] = "dependency_blocked"
        elif pending_items or running_items:
            data["queue_status"] = "running"
            data["pause_reason"] = ""
        else:
            data["queue_status"] = "empty"
            data["pause_reason"] = "empty"

        # 创建备份
        backup = (
            state_file
            + f".specific_dependency_fix_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        shutil.copy2(state_file, backup)
        print(f"\n✅ 创建备份: {backup}")

        # 保存更新
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("\n📊 修复完成:")
        print(f"  修复任务数: {fixed_count}")
        print(f"  新counts: {json.dumps(counts, ensure_ascii=False)}")
        print(f"  新queue_status: {data['queue_status']}")
        print(f"  pause_reason: {data.get('pause_reason', '')}")
    else:
        print("\n⚠️  没有需要修复的依赖阻塞任务")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
