#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
将manual_hold任务状态改为pending，以解除依赖阻塞
"""

import json
import os
import sys
import time


def fix_manual_hold():
    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"

    if not os.path.exists(queue_file):
        print(f"队列文件不存在: {queue_file}")
        return False

    try:
        # 读取文件
        with open(queue_file, encoding="utf-8") as f:
            data = json.load(f)

        modified = False
        items = data.get("items", {})

        # 查找manual_hold任务
        for task_id, task_data in items.items():
            if task_data.get("status") == "manual_hold":
                print(f"找到manual_hold任务: {task_id}")
                print(f"  当前状态: manual_hold, 进度: {task_data.get('progress_percent', 0)}%")
                print(f"  摘要: {task_data.get('summary', '')}")

                # 检查是否有runner_pid
                runner_pid = task_data.get("runner_pid")
                if runner_pid:
                    print(f"  警告: 任务有runner_pid: {runner_pid}")

                # 确认是否要修改
                response = input(f"将任务 '{task_id}' 的状态从 manual_hold 改为 pending? (y/n): ")
                if response.lower() == "y":
                    task_data["status"] = "pending"
                    modified = True
                    print("  已修改状态为 pending")
                else:
                    print("  跳过此任务")

        if not modified:
            print("未找到manual_hold任务或用户取消修改")
            return False

        # 更新counts
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
        for task_data in items.values():
            status = task_data.get("status", "pending")
            if status in counts:
                counts[status] += 1

        data["counts"] = counts
        data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())

        # 写回文件
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("文件已更新")
        print(f"新counts: {counts}")
        return True

    except Exception as e:
        print(f"处理文件时出错: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("修复manual_hold任务状态")
    print("=" * 60)
    success = fix_manual_hold()
    if success:
        print("\n✅ 修复完成")
    else:
        print("\n❌ 修复失败")
        sys.exit(1)
