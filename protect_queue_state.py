#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py health 或 governance_cli.py queue protect
"""队列状态保护脚本
防止队列状态被意外重置
"""

import json
from datetime import datetime
from pathlib import Path


def protect_queue_state():
    """保护队列状态不被意外重置"""

    queue_file = Path(
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    if not queue_file.exists():
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return False

    try:
        with open(queue_file, encoding="utf-8") as f:
            queue_state = json.load(f)

        # 检查队列状态是否被意外重置
        current_status = queue_state.get("queue_status", "")
        current_item = queue_state.get("current_item_id", "")

        # 如果队列状态异常，自动修复
        if current_status == "manual_hold" and current_item == "":
            print("⚠️ 检测到队列状态被意外重置，正在修复...")

            # 查找可执行任务
            items = queue_state.get("items", {})
            executable_tasks = []

            for task_id, task in items.items():
                status = task.get("status", "")
                if status in ["pending", ""]:
                    executable_tasks.append(task_id)

            if executable_tasks:
                # 修复队列状态
                queue_state["queue_status"] = "running"
                queue_state["current_item_id"] = executable_tasks[0]
                queue_state["current_item_ids"] = executable_tasks
                queue_state["pause_reason"] = ""
                queue_state["updated_at"] = datetime.now().isoformat()

                # 保存修复后的状态
                with open(queue_file, "w", encoding="utf-8") as f:
                    json.dump(queue_state, f, indent=2, ensure_ascii=False)

                print(f"✅ 队列状态已修复，当前任务: {executable_tasks[0]}")
                return True
            else:
                print("❌ 没有发现可执行任务")
                return False
        else:
            print("✅ 队列状态正常")
            return True

    except Exception as e:
        print(f"❌ 队列状态保护失败: {e}")
        return False


if __name__ == "__main__":
    protect_queue_state()
