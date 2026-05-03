#!/usr/bin/env python3
"""
批量重置失败任务为pending
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
    failed_count = 0
    reset_count = 0

    for task_id, task in items.items():
        if task.get("status") == "failed":
            failed_count += 1
            error = task.get("error", "")

            # 检查是否包含"等待后续重试"或API密钥错误
            if (
                "等待后续重试" in error
                or "Incorrect API key provided" in error
                or "API key" in error
            ):
                print(f"  重置任务: {task_id[:50]}...")
                print(f"    错误: {error[:60]}...")

                # 重置任务状态
                task["status"] = "pending"
                task["error"] = ""
                task["finished_at"] = ""
                task["started_at"] = ""
                task["progress_percent"] = 0

                # 清除执行相关字段
                for field in [
                    "summary",
                    "result_excerpt",
                    "pipeline_summary",
                    "runner_pid",
                    "runner_heartbeat_at",
                    "artifact_paths",
                    "root_task_id",
                    "last_auto_retry_reason",
                    "blocked_rescue_retry_count",
                    "last_blocked_rescue_retry_at",
                    "last_blocked_rescue_retry_reason",
                ]:
                    if field in task:
                        if field == "artifact_paths":
                            task[field] = []
                        else:
                            task[field] = ""

                # 确保manual_override_autostart为true
                task["manual_override_autostart"] = True

                reset_count += 1

    if reset_count > 0:
        # 重新计算counts
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
        for _task_id, task in items.items():
            status = task.get("status", "pending")
            if status in counts:
                counts[status] += 1
            else:
                counts["pending"] += 1

        data["counts"] = counts
        data["queue_status"] = "running"
        data["pause_reason"] = ""
        data["updated_at"] = datetime.now().isoformat()

        # 创建备份
        backup = state_file + f".batch_reset_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(state_file, backup)
        print(f"✅ 创建备份: {backup}")

        # 保存更新
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("\n📊 统计:")
        print(f"  总失败任务: {failed_count}")
        print(f"  已重置任务: {reset_count}")
        print(f"  新counts: {json.dumps(counts, ensure_ascii=False, indent=2)}")
    else:
        print("⚠️  没有需要重置的失败任务")
        print(f"  总失败任务: {failed_count}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
