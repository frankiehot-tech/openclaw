#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复athena_enterprise依赖链的过时阻塞警告
"""

import json
import re
import shutil
from datetime import datetime


def main():
    state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"

    print(f"加载状态文件: {state_file}")
    with open(state_file, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", {})
    fixed_count = 0

    # 检查所有pending任务，修复过时的依赖警告
    for task_id, task in items.items():
        if task.get("status") == "pending" and "dependency blocked" in task.get(
            "pipeline_summary", ""
        ):
            summary = task.get("summary", "")

            # 检查摘要中是否包含依赖阻塞信息
            if "被依赖项阻塞：" in summary:
                # 提取所有阻塞的任务ID
                pattern = r"被依赖项阻塞：([\w_-]+)\((\w+)\)"
                matches = re.findall(pattern, summary)

                if matches:
                    print(f"🔧 检查任务: {task_id}")
                    print(f"   摘要: {summary[:80]}...")

                    all_deps_completed = True
                    for dep_id, dep_status in matches:
                        # 检查依赖任务状态
                        dep_task = items.get(dep_id)
                        if dep_task:
                            actual_status = dep_task.get("status", "unknown")
                            print(
                                f"   依赖 {dep_id}: 摘要中状态={dep_status}, 实际状态={actual_status}"
                            )

                            if actual_status != "completed":
                                all_deps_completed = False
                                print(f"   ⚠️  {dep_id} 状态为 {actual_status}，仍需处理")
                        else:
                            print(f"   ⚠️  {dep_id} 任务不存在")
                            all_deps_completed = False

                    if all_deps_completed:
                        print("   ✅ 所有依赖任务已完成，解除阻塞")
                        task["summary"] = "依赖已解除，等待执行"
                        task["pipeline_summary"] = "pending"
                        fixed_count += 1

    if fixed_count > 0:
        # 更新队列状态
        data["updated_at"] = datetime.now().isoformat()

        # 重新计算counts
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
        for _task_id, task in items.items():
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
        backup = (
            state_file + f".athena_enterprise_fix_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
    else:
        print("\n⚠️  没有需要修复的过时依赖警告")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
