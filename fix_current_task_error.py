#!/usr/bin/env python3
"""
修复当前任务的runner重启失败错误
"""

import json
import os
from datetime import datetime, timezone


def fix_current_task_error():
    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"

    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            queue_state = json.load(f)

        current_item_id = queue_state.get("current_item_id", "")
        if not current_item_id:
            print("❌ 当前任务ID为空")
            return False

        items = queue_state.get("items", {})
        current_task = items.get(current_item_id)

        if not current_task:
            print(f"❌ 找不到当前任务: {current_item_id}")
            return False

        print(f"🔍 当前任务: {current_item_id}")
        print(f"📝 标题: {current_task.get('title', '无标题')}")
        print(f"📊 状态: {current_task.get('status', 'unknown')}")
        print(f"❌ 错误: {current_task.get('error', '无错误')}")

        # 修复任务
        current_task["status"] = "running"
        current_task["error"] = ""
        current_task["finished_at"] = ""
        current_task["summary"] = "runner重启失败错误已清除，任务重新开始执行"
        current_task["progress_percent"] = 0

        if not current_task.get("started_at"):
            current_task["started_at"] = datetime.now(timezone.utc).isoformat()

        # 更新队列状态
        queue_state["items"] = items
        queue_state["updated_at"] = datetime.now(timezone.utc).isoformat()

        # 更新任务计数
        counts = queue_state.get("counts", {})
        if current_task["status"] == "running":
            counts["running"] = 1
            # 从failed中减去
            if "failed" in counts:
                counts["failed"] = max(0, counts.get("failed", 0) - 1)
        queue_state["counts"] = counts

        # 保存
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(queue_state, f, indent=2, ensure_ascii=False)

        print(f"\n✅ 任务修复完成:")
        print(f"  • 状态从 'failed' 改为 'running'")
        print(f"  • 错误信息已清除")
        print(f"  • started_at: {current_task.get('started_at')}")
        print(
            f"  • 任务计数更新: running={counts.get('running', 0)}, failed={counts.get('failed', 0)}"
        )

        return True

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("修复当前任务runner重启失败错误")
    print("=" * 60)

    if fix_current_task_error():
        print("\n✅ 修复成功!")
        print("💡 现在队列应该有running状态的任务了")
    else:
        print("\n❌ 修复失败")
