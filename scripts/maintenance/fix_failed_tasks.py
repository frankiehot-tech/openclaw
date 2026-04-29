#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复因instruction_path不存在而失败的任务
将状态从failed重置为pending，清除错误信息
"""

import json
import os
import sys


def fix_failed_tasks():
    """修复失败任务"""
    status_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"

    if not os.path.exists(status_file):
        print(f"错误：状态文件不存在: {status_file}")
        return 1

    # 读取状态文件
    with open(status_file, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", {})
    fixed_count = 0

    for task_id, task_info in items.items():
        if task_info.get("status") == "failed":
            # 检查是否为instruction_path不存在的错误
            error = task_info.get("error", "")
            summary = task_info.get("summary", "")

            if "instruction_path 不存在" in error or "instruction_path 不存在" in summary:
                print(f"修复任务: {task_id}")
                print(f"  标题: {task_info.get('title', 'N/A')}")
                print(f"  原错误: {error[:100]}...")

                # 重置状态
                task_info["status"] = "pending"
                task_info["progress_percent"] = 0
                task_info["summary"] = ""
                task_info["error"] = ""
                task_info["finished_at"] = ""
                task_info["runner_pid"] = None
                task_info["runner_heartbeat_at"] = ""
                task_info["started_at"] = ""

                # 重置重试计数
                task_info["auto_retry_count"] = 0
                task_info["last_auto_retry_at"] = ""
                task_info["last_auto_retry_reason"] = ""
                task_info["blocked_rescue_retry_count"] = 0
                task_info["last_blocked_rescue_retry_at"] = ""
                task_info["last_blocked_rescue_retry_reason"] = ""

                fixed_count += 1

    if fixed_count > 0:
        # 更新队列状态
        print(f"\n共修复 {fixed_count} 个任务")

        # 重新计算counts
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

        for task_info in items.values():
            status = task_info.get("status", "pending")
            if status in counts:
                counts[status] += 1

        data["counts"] = counts

        # 确定队列状态
        if counts["failed"] > 0:
            data["queue_status"] = "dependency_blocked"
        elif counts["running"] > 0:
            data["queue_status"] = "running"
        elif counts["pending"] > 0:
            data["queue_status"] = "ready"
        else:
            data["queue_status"] = "empty"

        # 保存文件
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"更新后的统计: {counts}")
        print(f"队列状态: {data['queue_status']}")
        print("✅ 状态文件已更新")

        # 重启队列运行器
        print("\n🔄 重启队列运行器...")
        os.system("pkill -f athena_ai_plan_runner 2>/dev/null")
        # 稍等后重启
        os.system("sleep 2")
        os.system(
            "cd /Volumes/1TB-M2/openclaw && screen -dmS athena_plan_runner python3 scripts/athena_ai_plan_runner.py"
        )

    else:
        print("未找到需要修复的任务")

    return 0


if __name__ == "__main__":
    sys.exit(fix_failed_tasks())
