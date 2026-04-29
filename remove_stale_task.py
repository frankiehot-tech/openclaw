#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py task <command>
"""移除陈旧队列任务脚本"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from config.paths import PLAN_QUEUE_DIR, ROOT_DIR, SCRIPTS_DIR
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    ROOT_DIR = Path("/Volumes/1TB-M2/openclaw")
    PLAN_QUEUE_DIR = ROOT_DIR / ".openclaw" / "plan_queue"
    SCRIPTS_DIR = ROOT_DIR / "scripts"


def remove_stale_task():
    """移除陈旧任务"""

    print("🔍 移除陈旧队列任务...")

    queue_file = str(PLAN_QUEUE_DIR / "openhuman_athena_upgrade_20260326.json")

    if not os.path.exists(queue_file):
        print(f"❌ 队列文件不存在: {queue_file}")
        return False

    try:
        # 读取队列文件
        with open(queue_file, encoding="utf-8") as f:
            data = json.load(f)

        task_id = "skill_wiring_and_cli_anything"

        if task_id in data.get("items", {}):
            task_info = data["items"][task_id]
            print("📋 任务信息:")
            print(f"  标题: {task_info.get('title', 'N/A')}")
            print(f"  状态: {task_info.get('status', 'N/A')}")
            print(f"  错误: {task_info.get('error', 'N/A')}")
            print(f"  开始时间: {task_info.get('started_at', 'N/A')}")

            # 检查是否为陈旧任务
            error_msg = task_info.get("error", "").lower()
            if "stale" in error_msg or "no heartbeat" in error_msg:
                print("\n⚠️ 检测到陈旧任务，准备移除...")

                # 从队列中移除任务
                del data["items"][task_id]

                # 更新队列统计信息
                if "counts" not in data:
                    data["counts"] = {}

                # 重新计算任务状态统计
                status_counts = {
                    "pending": 0,
                    "running": 0,
                    "completed": 0,
                    "failed": 0,
                    "manual_hold": 0,
                }
                for _item_id, item_data in data.get("items", {}).items():
                    status = item_data.get("status", "")
                    if status in status_counts:
                        status_counts[status] += 1

                data["counts"] = status_counts

                # 更新队列状态
                if len(data["items"]) == 0:
                    data["queue_status"] = "empty"
                    data["pause_reason"] = "empty"
                else:
                    # 检查是否有运行中的任务
                    running_tasks = [
                        item_id
                        for item_id, item_data in data.get("items", {}).items()
                        if item_data.get("status") == "running"
                    ]
                    if running_tasks:
                        data["queue_status"] = "running"
                        data["pause_reason"] = ""
                    else:
                        data["queue_status"] = "idle"
                        data["pause_reason"] = ""

                # 更新修改时间
                data["updated_at"] = datetime.now().isoformat()

                # 保存更新后的队列文件
                with open(queue_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"✅ 已移除陈旧任务: {task_id}")
                print(f"  更新队列统计: {status_counts}")
                print(f"  队列状态: {data.get('queue_status', 'N/A')}")

                return True
            else:
                print("❌ 任务不是陈旧任务")
                return False
        else:
            print(f"❌ 任务不存在: {task_id}")
            return False

    except Exception as e:
        print(f"❌ 移除任务失败: {e}")
        return False


def verify_removal():
    """验证移除结果"""

    print("\n🔍 验证移除结果...")

    queue_file = str(PLAN_QUEUE_DIR / "openhuman_athena_upgrade_20260326.json")

    if not os.path.exists(queue_file):
        print(f"❌ 队列文件不存在: {queue_file}")
        return False

    try:
        with open(queue_file, encoding="utf-8") as f:
            data = json.load(f)

        task_id = "skill_wiring_and_cli_anything"

        if task_id in data.get("items", {}):
            print(f"❌ 任务仍然存在: {task_id}")
            task_info = data["items"][task_id]
            print(f"  状态: {task_info.get('status', 'N/A')}")
            print(f"  错误: {task_info.get('error', 'N/A')}")
            return False
        else:
            print(f"✅ 任务已成功移除: {task_id}")
            print(f"  队列剩余任务数: {len(data.get('items', {}))}")
            print(f"  队列状态: {data.get('queue_status', 'N/A')}")
            print(f"  任务统计: {data.get('counts', {})}")
            return True

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def main():
    """主函数"""

    print("=" * 60)
    print("陈旧队列任务移除工具")
    print("=" * 60)

    # 移除陈旧任务
    if remove_stale_task():
        print("\n✅ 陈旧任务移除成功")
    else:
        print("\n❌ 陈旧任务移除失败")

    # 验证移除结果
    if verify_removal():
        print("\n🎉 陈旧任务已成功移除")
    else:
        print("\n⚠️ 陈旧任务移除验证失败")

    print("\n下一步建议:")
    print("1. 检查队列运行状态")
    print("2. 如有需要，重新创建并执行该任务")
    print("3. 定期监控队列任务状态")


if __name__ == "__main__":
    main()
