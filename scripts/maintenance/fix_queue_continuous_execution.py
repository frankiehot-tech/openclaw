#!/usr/bin/env python3
"""
修复Athena任务队列连续执行问题
问题：队列执行完一个任务就停止，状态为manual_hold
解决方案：自动处理手动保留任务，实现连续执行
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path


def load_queue_state():
    """加载队列状态文件"""
    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    if not os.path.exists(queue_file):
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return None

    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载队列状态文件失败: {e}")
        return None


def fix_queue_continuous_execution():
    """修复队列连续执行问题"""

    print("🔧 开始修复队列连续执行问题...")

    # 1. 加载当前队列状态
    queue_state = load_queue_state()
    if not queue_state:
        print("❌ 无法加载队列状态，修复失败")
        return False

    print(f"📊 当前队列状态: {queue_state.get('queue_status', 'unknown')}")
    print(f"⏸️  暂停原因: {queue_state.get('pause_reason', 'unknown')}")

    # 2. 分析问题
    if queue_state.get("queue_status") == "manual_hold":
        print("🔍 检测到队列处于手动保留状态")

        # 检查是否有可以自动执行的任务
        items = queue_state.get("items", {})
        manual_hold_count = 0
        auto_ready_count = 0

        for item_id, item in items.items():
            status = item.get("status", "")
            if status == "manual_hold":
                manual_hold_count += 1
                print(f"   📋 {item_id}: 手动保留")
            elif status in ["pending", ""]:
                auto_ready_count += 1
                print(f"   ✅ {item_id}: 可自动执行")

        print(f"📈 统计: {manual_hold_count}个手动保留, {auto_ready_count}个可自动执行")

        # 3. 修复队列状态
        if auto_ready_count > 0:
            print("🚀 发现可自动执行的任务，修复队列状态...")

            # 修改队列状态为运行中
            queue_state["queue_status"] = "running"
            queue_state["pause_reason"] = ""
            queue_state["updated_at"] = datetime.now().isoformat()

            # 设置第一个可执行任务为当前任务
            for item_id, item in items.items():
                if item.get("status") in ["pending", ""]:
                    queue_state["current_item_id"] = item_id
                    queue_state["current_item_ids"] = [item_id]
                    print(f"🎯 设置当前任务: {item_id}")
                    break

            # 4. 保存修复后的状态
            try:
                with open(queue_file, "w", encoding="utf-8") as f:
                    json.dump(queue_state, f, indent=2, ensure_ascii=False)

                print("✅ 队列状态修复完成")
                print(f"📊 新队列状态: {queue_state['queue_status']}")
                print(f"🎯 当前任务: {queue_state.get('current_item_id', '无')}")

                return True

            except Exception as e:
                print(f"❌ 保存队列状态失败: {e}")
                return False
        else:
            print("⚠️ 没有发现可自动执行的任务，需要手动处理")
            return False
    else:
        print("✅ 队列状态正常，无需修复")
        return True


def create_continuous_execution_script():
    """创建连续执行监控脚本"""

    script_content = """#!/bin/bash
# Athena队列连续执行监控脚本

QUEUE_FILE="/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
RUNNER_SCRIPT="/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"

# 检查队列运行器是否在运行
check_runner() {
    if ! pgrep -f "python3.*athena_ai_plan_runner.py" > /dev/null; then
        echo "🚀 启动队列运行器..."
        python3 "$RUNNER_SCRIPT" &
        sleep 3
    fi
}

# 监控队列状态
monitor_queue() {
    while true; do
        if [ -f "$QUEUE_FILE" ]; then
            STATUS=$(python3 -c "
import json
with open('$QUEUE_FILE', 'r') as f:
    data = json.load(f)
print(data.get('queue_status', 'unknown'))
")
            
            if [ "$STATUS" = "manual_hold" ]; then
                echo "⚠️ 队列处于手动保留状态，尝试自动修复..."
                python3 /Volumes/1TB-M2/openclaw/fix_queue_continuous_execution.py
            fi
        fi
        
        sleep 30
    done
}

# 主循环
main() {
    echo "🔍 开始监控Athena队列连续执行..."
    check_runner
    monitor_queue
}

main "$@"
"""

    script_path = "/Volumes/1TB-M2/openclaw/monitor_queue_continuous.sh"

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # 设置执行权限
        os.chmod(script_path, 0o755)

        print(f"✅ 连续执行监控脚本已创建: {script_path}")
        return script_path

    except Exception as e:
        print(f"❌ 创建监控脚本失败: {e}")
        return None


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 Athena任务队列连续执行修复工具")
    print("=" * 60)

    # 修复队列状态
    if fix_queue_continuous_execution():
        print("\n✅ 队列状态修复成功")
    else:
        print("\n❌ 队列状态修复失败")
        return

    # 创建监控脚本
    script_path = create_continuous_execution_script()
    if script_path:
        print(f"📋 监控脚本位置: {script_path}")
        print("💡 使用方法: bash monitor_queue_continuous.sh")

    print("\n🎯 下一步操作:")
    print("1. 启动队列运行器: python3 scripts/athena_ai_plan_runner.py")
    print("2. 启动监控脚本: bash monitor_queue_continuous.sh")
    print("3. 验证队列连续执行功能")


if __name__ == "__main__":
    main()
