#!/usr/bin/env python3
"""
全面队列保护脚本
防止所有队列状态被意外重置
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from config.paths import PLAN_QUEUE_DIR, ROOT_DIR, SCRIPTS_DIR, get_queue_file
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    ROOT_DIR = Path("/Volumes/1TB-M2/openclaw")
    PLAN_QUEUE_DIR = ROOT_DIR / ".openclaw" / "plan_queue"
    SCRIPTS_DIR = ROOT_DIR / "scripts"


def protect_all_queues():
    """保护所有队列状态"""

    queue_dir = str(PLAN_QUEUE_DIR)

    if not os.path.exists(queue_dir):
        print(f"❌ 队列目录不存在: {queue_dir}")
        return False

    # 获取所有队列文件
    queue_files = []
    for file in os.listdir(queue_dir):
        if file.endswith(".json") and not file.endswith(".lock"):
            queue_files.append(os.path.join(queue_dir, file))

    protected_count = 0

    for queue_file in queue_files:
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                queue_state = json.load(f)

            queue_id = queue_state.get("queue_id", "unknown")
            status = queue_state.get("queue_status", "")
            current_item = queue_state.get("current_item_id", "")

            # 检查队列状态是否异常
            if status in ["manual_hold", "stopped", "unknown"] and current_item == "":
                print(f"⚠️ 检测到队列 {queue_id} 状态异常，正在修复...")

                # 查找可执行任务
                items = queue_state.get("items", {})
                executable_tasks = []

                for task_id, task in items.items():
                    task_status = task.get("status", "")
                    if task_status in ["pending", ""]:
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

                    print(f"✅ 队列 {queue_id} 已修复，当前任务: {executable_tasks[0]}")
                    protected_count += 1
                else:
                    print(f"⚠️ 队列 {queue_id} 没有可执行任务")
            else:
                print(f"✅ 队列 {queue_id} 状态正常")

        except Exception as e:
            print(f"❌ 保护队列 {queue_file} 失败: {e}")

    print(f"📊 总共保护了 {protected_count} 个队列")
    return protected_count > 0


def check_and_restart_runners():
    """检查并重启运行器"""

    runners = [
        "athena_ai_plan_runner.py",
        "athena_ai_plan_runner_build.py",
        "athena_ai_plan_runner_codex.py",
    ]

    scripts_dir = str(SCRIPTS_DIR)

    for runner in runners:
        try:
            result = subprocess.run(["pgrep", "-f", runner], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"⚠️ {runner} 未运行，正在启动...")

                runner_script = os.path.join(scripts_dir, runner)
                if os.path.exists(runner_script):
                    subprocess.Popen(
                        ["python3", runner_script],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    print(f"✅ {runner} 已启动")
                else:
                    print(f"❌ {runner} 脚本不存在")
            else:
                print(f"✅ {runner} 已在运行")

        except Exception as e:
            print(f"❌ 检查运行器 {runner} 失败: {e}")


if __name__ == "__main__":
    protect_all_queues()
    check_and_restart_runners()
