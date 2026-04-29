#!/usr/bin/env python3
"""
将OpenCode CLI优化任务添加到Athena队列
设置最高优先级，确保立即执行

使用统一的路径配置，避免硬编码路径
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from config.paths import PLAN_QUEUE_DIR, QUEUE_FILES, ROOT_DIR, SCRIPTS_DIR
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    ROOT_DIR = Path("/Volumes/1TB-M2/openclaw")
    PLAN_QUEUE_DIR = ROOT_DIR / ".openclaw" / "plan_queue"
    SCRIPTS_DIR = ROOT_DIR / "scripts"
    QUEUE_FILES = {
        "plan_manual": PLAN_QUEUE_DIR / "openhuman_aiplan_plan_manual_20260328.json",
    }


def add_opencode_task_to_queue():
    """将OpenCode CLI优化任务添加到队列"""

    print("🚀 开始添加OpenCode CLI优化任务到队列...")

    # 使用统一的路径配置
    queue_file = QUEUE_FILES.get(
        "plan_manual", PLAN_QUEUE_DIR / "openhuman_aiplan_plan_manual_20260328.json"
    )

    # 检查队列文件是否存在
    if not os.path.exists(queue_file):
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return False

    try:
        # 加载当前队列状态
        with open(queue_file, encoding="utf-8") as f:
            queue_state = json.load(f)

        print(f"📊 当前队列状态: {queue_state.get('queue_status', 'unknown')}")
        print(f"📋 当前任务数量: {len(queue_state.get('items', {}))}")

        # 创建OpenCode CLI优化任务
        opencode_task = {
            "status": "pending",
            "progress_percent": 0,
            "title": "OpenHuman-OpenCode-CLI-优化与Athena深度集成方案",
            "stage": "build",
            "executor": "opencode",
            "summary": "立即优化OpenCode CLI执行能力，修复队列连续执行问题",
            "error": "",
            "instruction_path": str(
                ROOT_DIR / "OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md"
            ),
            "pipeline_summary": "OpenCode CLI优化任务",
            "current_stage_ids": ["build"],
            "runner_pid": "",
            "runner_heartbeat_at": "",
            "started_at": "",
            "finished_at": "",
        }

        # 添加到队列items
        items = queue_state.get("items", {})
        items["opencode_cli_optimization"] = opencode_task
        queue_state["items"] = items

        # 设置当前任务
        queue_state["current_item_id"] = "opencode_cli_optimization"
        queue_state["current_item_ids"] = ["opencode_cli_optimization"]

        # 更新队列状态为运行中
        queue_state["queue_status"] = "running"
        queue_state["pause_reason"] = ""
        queue_state["updated_at"] = datetime.now().isoformat()

        # 更新任务计数
        counts = queue_state.get("counts", {})
        counts["pending"] = counts.get("pending", 0) + 1
        counts["running"] = 1
        counts["completed"] = counts.get("completed", 0)
        counts["manual_hold"] = counts.get("manual_hold", 0)
        queue_state["counts"] = counts

        # 保存更新后的队列状态
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(queue_state, f, indent=2, ensure_ascii=False)

        print("✅ OpenCode CLI优化任务已成功添加到队列")
        print("🎯 当前任务: opencode_cli_optimization")
        print(f"📊 新队列状态: {queue_state['queue_status']}")
        print(f"📈 任务计数: pending={counts['pending']}, running={counts['running']}")

        return True

    except Exception as e:
        print(f"❌ 添加任务失败: {e}")
        return False


def start_queue_runner():
    """启动队列运行器"""

    print("\n🚀 启动队列运行器...")

    runner_script = str(SCRIPTS_DIR / "athena_ai_plan_runner.py")

    if not os.path.exists(runner_script):
        print(f"❌ 队列运行器脚本不存在: {runner_script}")
        return False

    try:
        # 检查是否已有运行器在运行
        import subprocess

        result = subprocess.run(
            ["pgrep", "-f", "athena_ai_plan_runner.py"], capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✅ 队列运行器已在运行中")
            return True
        else:
            print("🔧 启动新的队列运行器...")
            # 在后台启动运行器
            subprocess.Popen(
                ["python3", runner_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print("✅ 队列运行器已启动")
            return True

    except Exception as e:
        print(f"❌ 启动队列运行器失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 OpenCode CLI优化任务队列集成工具")
    print("=" * 60)

    # 添加任务到队列
    if add_opencode_task_to_queue():
        print("\n✅ 任务添加成功")
    else:
        print("\n❌ 任务添加失败")
        return

    # 启动队列运行器
    if start_queue_runner():
        print("✅ 队列运行器启动成功")
    else:
        print("❌ 队列运行器启动失败")

    print("\n🎯 下一步操作:")
    print("1. 访问 http://127.0.0.1:8080 查看队列状态")
    print("2. 监控OpenCode CLI优化任务执行进度")
    print("3. 验证队列连续执行功能")


if __name__ == "__main__":
    main()
