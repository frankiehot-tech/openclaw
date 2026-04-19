#!/usr/bin/env python3
"""
修复失败任务脚本 - 将error为空的失败任务重置为pending状态
"""

import json
import os
import sys
from datetime import datetime


def fix_failed_tasks(queue_id):
    """修复指定队列的失败任务"""
    print(f"修复队列: {queue_id}")

    state_file = f".openclaw/plan_queue/{queue_id}.json"

    # 加载状态文件
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state_data = json.load(f)
    except Exception as e:
        print(f"❌ 无法加载状态文件 {state_file}: {e}")
        return False

    items = state_data.get("items", {})
    fixed_count = 0

    # 查找失败任务
    for task_id, task in items.items():
        if task.get("status") == "failed":
            error = task.get("error", "")
            summary = task.get("summary", "")

            # 如果错误信息为空，且summary包含"等待 queue runner 接手"，则重置
            if not error and "等待 queue runner 接手" in summary:
                print(f"  重置任务: {task_id[:60]}...")
                print(f"    标题: {task.get('title', '未知')[:80]}")

                # 重置为pending状态
                task["status"] = "pending"
                task["updated_at"] = datetime.now().isoformat()
                task["finished_at"] = ""
                task["started_at"] = ""
                task["runner_pid"] = None
                task["runner_heartbeat_at"] = ""

                fixed_count += 1

    if fixed_count > 0:
        # 重新计算counts
        new_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
        for task_id, task in items.items():
            status = task.get("status", "pending")
            if status in new_counts:
                new_counts[status] += 1
            else:
                new_counts["pending"] += 1

        state_data["counts"] = new_counts

        # 更新队列状态
        pending_items = [task for task_id, task in items.items() if task.get("status") == "pending"]
        running_items = [task for task_id, task in items.items() if task.get("status") == "running"]
        manual_hold_items = [
            task for task_id, task in items.items() if task.get("status") == "manual_hold"
        ]

        if not pending_items and not running_items:
            if manual_hold_items:
                new_queue_status = "manual_hold"
                state_data["pause_reason"] = "manual_hold"
            else:
                new_queue_status = "empty"
                state_data["pause_reason"] = "empty"
        elif running_items:
            new_queue_status = "running"
            state_data["pause_reason"] = ""
        else:
            # 只有pending任务，没有running任务
            new_queue_status = "no_consumer"  # 等待消费者
            state_data["pause_reason"] = ""

        state_data["queue_status"] = new_queue_status
        state_data["updated_at"] = datetime.now().isoformat()

        # 创建备份
        backup_file = state_file + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil

        shutil.copy2(state_file, backup_file)
        print(f"  📋 已创建备份: {backup_file}")

        # 保存修复后的状态
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 已修复 {fixed_count} 个失败任务")
        print(f"📊 新统计: {json.dumps(new_counts, ensure_ascii=False)}")
        print(f"📊 队列状态: {new_queue_status}")

        return True
    else:
        print("ℹ️  没有需要修复的失败任务")
        return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python3 fix_failed_tasks.py <queue_id>")
        print("示例: python3 fix_failed_tasks.py openhuman_aiplan_build_priority_20260328")
        return 1

    queue_id = sys.argv[1]

    print("=" * 60)
    print("失败任务修复脚本")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    success = fix_failed_tasks(queue_id)

    print("=" * 60)
    print("修复完成" if success else "无需修复")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
