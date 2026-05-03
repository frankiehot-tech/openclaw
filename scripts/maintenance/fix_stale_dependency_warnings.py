#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复过时的依赖阻塞警告
更新任务的摘要信息，移除已经解决的依赖阻塞
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
    fixed_count = 0

    # 检查所有pending任务
    for task_id, task in items.items():
        if task.get("status") == "pending":
            summary = task.get("summary", "")

            # 检查摘要中是否包含过时的依赖阻塞信息
            if "被依赖项阻塞" in summary and "pending" in summary:
                # 提取阻塞的任务ID
                import re

                pattern = r"被依赖项阻塞：([\w_-]+)\(pending\)"
                match = re.search(pattern, summary)

                if match:
                    blocker_id = match.group(1)
                    print(f"🔧 检查任务: {task_id}")
                    print(f"   摘要: {summary[:80]}...")
                    print(f"   检测到阻塞任务: {blocker_id}")

                    # 检查阻塞任务的状态
                    blocker_task = items.get(blocker_id)
                    if blocker_task:
                        blocker_status = blocker_task.get("status", "unknown")
                        print(f"   阻塞任务状态: {blocker_status}")

                        if blocker_status == "completed":
                            print(f"   ✅ {blocker_id} 已标记为completed，更新摘要")
                            # 更新摘要，移除阻塞信息
                            task["summary"] = "依赖已解除，等待执行"
                            task["pipeline_summary"] = "pending"
                            fixed_count += 1
                        else:
                            print(f"   ⚠️  {blocker_id} 状态为 {blocker_status}，仍需处理")

    if fixed_count > 0:
        # 更新队列状态
        data["updated_at"] = datetime.now().isoformat()

        # 重新计算counts（简单统计）
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
        for _task_id, task in items.items():
            status = task.get("status", "pending")
            if status in counts:
                counts[status] += 1
            else:
                counts["pending"] += 1

        data["counts"] = counts

        # 简单的queue_status逻辑
        pending_items = [task for task_id, task in items.items() if task.get("status") == "pending"]
        running_items = [task for task_id, task in items.items() if task.get("status") == "running"]

        if pending_items or running_items:
            data["queue_status"] = "running"
            data["pause_reason"] = ""
        else:
            data["queue_status"] = "empty"
            data["pause_reason"] = "empty"

        # 创建备份
        backup = state_file + f".stale_deps_fix_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(state_file, backup)
        print(f"✅ 创建备份: {backup}")

        # 保存更新
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("\n📊 修复完成:")
        print(f"  修复任务数: {fixed_count}")
        print(f"  新queue_status: {data['queue_status']}")
    else:
        print("⚠️  没有需要修复的过时依赖警告")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
