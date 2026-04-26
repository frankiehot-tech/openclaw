#!/usr/bin/env python3
"""
OpenCode CLI优化方案队列配置更新脚本
更新队列状态文件和配置文件中的文件路径
"""

import json
import os
from datetime import datetime


def update_queue_state_file():
    """更新队列状态文件中的文件路径"""

    queue_state_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    if not os.path.exists(queue_state_file):
        print(f"❌ 队列状态文件不存在: {queue_state_file}")
        return False

    try:
        # 加载队列状态
        with open(queue_state_file, "r", encoding="utf-8") as f:
            queue_state = json.load(f)

        # 更新OpenCode CLI优化任务的instruction_path
        items = queue_state.get("items", {})
        if "opencode_cli_optimization" in items:
            items["opencode_cli_optimization"][
                "instruction_path"
            ] = "/Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md"

            print("✅ 队列状态文件中的文件路径已更新")
        else:
            print("⚠️ 队列状态文件中未找到OpenCode CLI优化任务")

        # 保存更新
        with open(queue_state_file, "w", encoding="utf-8") as f:
            json.dump(queue_state, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        print(f"❌ 更新队列状态文件失败: {e}")
        return False


def main():
    """主函数"""
    print("🔧 OpenCode CLI优化方案队列配置更新工具")

    if update_queue_state_file():
        print("✅ 队列配置更新完成")
    else:
        print("❌ 队列配置更新失败")


if __name__ == "__main__":
    main()
