#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复队列停止和手动拉起按钮无响应问题
问题诊断：队列处于manual_hold状态，没有可自动执行的任务
"""

import json
import os
import time
from datetime import datetime


def diagnose_queue_problems():
    """诊断队列问题"""

    print("🔍 开始诊断队列停止和手动拉起问题...")

    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    if not os.path.exists(queue_file):
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return None

    try:
        with open(queue_file, encoding="utf-8") as f:
            queue_state = json.load(f)

        print(f"📊 队列状态: {queue_state.get('queue_status', 'unknown')}")
        print(f"⏸️  暂停原因: {queue_state.get('pause_reason', 'unknown')}")
        print(f"🎯 当前任务: {queue_state.get('current_item_id', '无')}")

        # 分析任务状态
        counts = queue_state.get("counts", {})
        print(
            f"📈 任务统计: pending={counts.get('pending', 0)}, running={counts.get('running', 0)}, completed={counts.get('completed', 0)}, manual_hold={counts.get('manual_hold', 0)}"
        )

        # 检查OpenCode CLI任务状态
        items = queue_state.get("items", {})
        opencode_task = items.get("opencode_cli_optimization", {})

        if opencode_task:
            print(f"🔍 OpenCode CLI任务状态: {opencode_task.get('status', 'unknown')}")
            print(f"📁 文件路径: {opencode_task.get('instruction_path', '未设置')}")
        else:
            print("❌ OpenCode CLI任务未找到")

        return queue_state

    except Exception as e:
        print(f"❌ 诊断队列问题失败: {e}")
        return None


def fix_queue_manual_hold():
    """修复队列手动保留状态"""

    print("\n🔧 开始修复队列手动保留状态...")

    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    try:
        with open(queue_file, encoding="utf-8") as f:
            queue_state = json.load(f)

        # 检查是否有可自动执行的任务
        items = queue_state.get("items", {})
        auto_ready_tasks = []

        for task_id, task in items.items():
            status = task.get("status", "")
            if status in ["pending", ""]:
                auto_ready_tasks.append(task_id)

        print(f"🔍 发现可自动执行的任务: {auto_ready_tasks}")

        if auto_ready_tasks:
            # 修复队列状态
            queue_state["queue_status"] = "running"
            queue_state["pause_reason"] = ""
            queue_state["current_item_id"] = auto_ready_tasks[0]
            queue_state["current_item_ids"] = auto_ready_tasks
            queue_state["updated_at"] = datetime.now().isoformat()

            # 更新任务计数
            counts = queue_state.get("counts", {})
            counts["pending"] = len(auto_ready_tasks)
            counts["running"] = 1
            queue_state["counts"] = counts

            # 保存修复后的状态
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump(queue_state, f, indent=2, ensure_ascii=False)

            print("✅ 队列手动保留状态已修复")
            print(f"🎯 当前任务: {auto_ready_tasks[0]}")
            print(f"📊 新队列状态: {queue_state['queue_status']}")

            return True
        else:
            print("⚠️ 没有发现可自动执行的任务，需要创建新任务")
            return False

    except Exception as e:
        print(f"❌ 修复队列手动保留状态失败: {e}")
        return False


def activate_opencode_task():
    """激活OpenCode CLI任务"""

    print("\n🚀 激活OpenCode CLI任务...")

    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    try:
        with open(queue_file, encoding="utf-8") as f:
            queue_state = json.load(f)

        items = queue_state.get("items", {})
        opencode_task = items.get("opencode_cli_optimization", {})

        if opencode_task:
            # 激活OpenCode CLI任务
            opencode_task["status"] = "pending"
            opencode_task["progress_percent"] = 0
            opencode_task["started_at"] = ""
            opencode_task["finished_at"] = ""
            opencode_task["runner_pid"] = ""
            opencode_task["runner_heartbeat_at"] = ""

            # 设置当前任务
            queue_state["current_item_id"] = "opencode_cli_optimization"
            queue_state["current_item_ids"] = ["opencode_cli_optimization"]

            # 更新队列状态
            queue_state["queue_status"] = "running"
            queue_state["pause_reason"] = ""
            queue_state["updated_at"] = datetime.now().isoformat()

            # 更新任务计数
            counts = queue_state.get("counts", {})
            counts["pending"] = 1
            counts["running"] = 1
            counts["manual_hold"] = counts.get("manual_hold", 0) - 1
            queue_state["counts"] = counts

            # 保存更新
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump(queue_state, f, indent=2, ensure_ascii=False)

            print("✅ OpenCode CLI任务已激活")
            print("🎯 当前任务: opencode_cli_optimization")
            print(f"📊 队列状态: {queue_state['queue_status']}")

            return True
        else:
            print("❌ OpenCode CLI任务未找到，需要重新添加")
            return False

    except Exception as e:
        print(f"❌ 激活OpenCode CLI任务失败: {e}")
        return False


def check_web_server():
    """检查Web服务器状态"""

    print("\n🌐 检查Web服务器状态...")

    try:
        import requests

        # 检查Web服务器是否响应
        response = requests.get("http://127.0.0.1:8080", timeout=5)

        if response.status_code == 200:
            print("✅ Web服务器正常运行")
            return True
        else:
            print(f"⚠️ Web服务器响应异常: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Web服务器检查失败: {e}")
        print("💡 建议重启Web服务器: python3 scripts/athena_web_desktop_compat.py")
        return False


def restart_queue_runner():
    """重启队列运行器"""

    print("\n🔄 重启队列运行器...")

    runner_script = "/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"

    if not os.path.exists(runner_script):
        print(f"❌ 队列运行器脚本不存在: {runner_script}")
        return False

    try:
        import subprocess

        # 停止现有运行器
        subprocess.run(["pkill", "-f", "athena_ai_plan_runner.py"], capture_output=True)

        # 等待一下
        time.sleep(2)

        # 启动新的运行器
        subprocess.Popen(
            ["python3", runner_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        print("✅ 队列运行器已重启")
        return True

    except Exception as e:
        print(f"❌ 重启队列运行器失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 队列停止和手动拉起问题修复工具")
    print("=" * 60)

    # 诊断问题
    queue_state = diagnose_queue_problems()
    if not queue_state:
        print("❌ 诊断失败，无法继续修复")
        return

    # 检查Web服务器
    if not check_web_server():
        print("⚠️ Web服务器可能存在问题，建议重启")

    # 修复队列手动保留状态
    if not fix_queue_manual_hold():
        print("\n🔄 尝试激活OpenCode CLI任务...")
        if not activate_opencode_task():
            print("❌ 所有修复尝试失败")
            return

    # 重启队列运行器
    if not restart_queue_runner():
        print("⚠️ 队列运行器重启失败，但队列状态已修复")

    print("\n🎯 修复完成，下一步操作:")
    print("1. 访问 http://127.0.0.1:8080 验证队列状态")
    print("2. 测试手动拉起按钮功能")
    print("3. 监控OpenCode CLI任务执行进度")


if __name__ == "__main__":
    main()
