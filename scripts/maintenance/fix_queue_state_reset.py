#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复队列状态被意外重置问题
解决无法定位当前队列项错误
"""

import json
import os
from datetime import datetime


def diagnose_queue_state_reset():
    """诊断队列状态被意外重置问题"""

    print("🔍 诊断队列状态被意外重置问题...")

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
        print(f"🎯 当前任务ID: {queue_state.get('current_item_id', '空')}")
        print(f"📋 当前任务列表: {queue_state.get('current_item_ids', [])}")

        # 检查是否有任务被意外重置
        items = queue_state.get("items", {})

        print("\n📋 任务状态详细分析:")
        for task_id, task in items.items():
            status = task.get("status", "unknown")
            stage = task.get("stage", "unknown")
            progress = task.get("progress_percent", 0)
            print(f"   {task_id}: {status} (阶段: {stage}, 进度: {progress}%)")

        # 检查OpenCode CLI任务状态
        opencode_task = items.get("opencode_cli_optimization", {})
        if opencode_task:
            print("\n🔍 OpenCode CLI任务详细状态:")
            print(f"   状态: {opencode_task.get('status', 'unknown')}")
            print(f"   阶段: {opencode_task.get('stage', 'unknown')}")
            print(f"   进度: {opencode_task.get('progress_percent', 0)}%")
            print(f"   文件: {opencode_task.get('instruction_path', '未设置')}")

        return queue_state

    except Exception as e:
        print(f"❌ 诊断队列状态重置问题失败: {e}")
        return None


def fix_queue_state_reset():
    """修复队列状态被意外重置问题"""

    print("\n🔧 修复队列状态被意外重置问题...")

    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    try:
        with open(queue_file, encoding="utf-8") as f:
            queue_state = json.load(f)

        items = queue_state.get("items", {})

        # 检查OpenCode CLI任务状态
        opencode_task = items.get("opencode_cli_optimization", {})

        if opencode_task and opencode_task.get("status") == "pending":
            print("✅ OpenCode CLI任务状态正常，可以激活为当前任务")

            # 激活OpenCode CLI任务
            queue_state["current_item_id"] = "opencode_cli_optimization"
            queue_state["current_item_ids"] = ["opencode_cli_optimization"]
            queue_state["queue_status"] = "running"
            queue_state["pause_reason"] = ""

            # 确保任务状态正确
            opencode_task["status"] = "pending"
            opencode_task["progress_percent"] = 0

            print("✅ OpenCode CLI任务已激活为当前任务")

        else:
            print("❌ OpenCode CLI任务状态异常，需要检查其他任务")

            # 查找其他可执行任务
            executable_tasks = []
            for task_id, task in items.items():
                status = task.get("status", "")
                if status in ["pending", ""]:
                    executable_tasks.append(task_id)

            if executable_tasks:
                current_task = executable_tasks[0]
                queue_state["current_item_id"] = current_task
                queue_state["current_item_ids"] = executable_tasks
                queue_state["queue_status"] = "running"
                queue_state["pause_reason"] = ""

                print(f"✅ 激活任务: {current_task}")
            else:
                print("❌ 没有发现可执行任务")
                return False

        # 更新任务计数
        counts = queue_state.get("counts", {})
        counts["pending"] = len([t for t in items.values() if t.get("status") in ["pending", ""]])
        counts["running"] = 1 if queue_state["current_item_id"] else 0
        counts["manual_hold"] = len([t for t in items.values() if t.get("status") == "manual_hold"])
        queue_state["counts"] = counts

        # 更新时间戳
        queue_state["updated_at"] = datetime.now().isoformat()

        # 保存修复后的状态
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(queue_state, f, indent=2, ensure_ascii=False)

        print("✅ 队列状态重置问题已修复")
        print(f"📊 新队列状态: {queue_state['queue_status']}")
        print(f"🎯 当前任务: {queue_state['current_item_id']}")

        return True

    except Exception as e:
        print(f"❌ 修复队列状态重置问题失败: {e}")
        return False


def check_web_server_queue_reading():
    """检查Web服务器队列读取逻辑"""

    print("\n🌐 检查Web服务器队列读取逻辑...")

    web_script = "/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py"

    if not os.path.exists(web_script):
        print(f"❌ Web服务器脚本不存在: {web_script}")
        return False

    try:
        # 读取Web服务器代码，检查队列读取逻辑
        with open(web_script, encoding="utf-8") as f:
            web_code = f.read()

        # 检查队列状态读取函数
        if "load_route_state" in web_code:
            print("✅ Web服务器包含队列状态读取函数")

            # 检查队列状态路径生成逻辑
            if "route_state_path" in web_code:
                print("✅ Web服务器包含队列状态路径生成逻辑")

                # 检查队列ID匹配逻辑
                if "queue_id" in web_code:
                    print("✅ Web服务器包含队列ID匹配逻辑")
                    return True
                else:
                    print("❌ Web服务器缺少队列ID匹配逻辑")
                    return False
            else:
                print("❌ Web服务器缺少队列状态路径生成逻辑")
                return False
        else:
            print("❌ Web服务器缺少队列状态读取函数")
            return False

    except Exception as e:
        print(f"❌ 检查Web服务器队列读取逻辑失败: {e}")
        return False


def create_queue_state_protection():
    """创建队列状态保护机制"""

    print("\n🛡️ 创建队列状态保护机制...")

    protection_script = '''#!/usr/bin/env python3
"""队列状态保护脚本
防止队列状态被意外重置
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

def protect_queue_state():
    """保护队列状态不被意外重置"""

    queue_file = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json")

    if not queue_file.exists():
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return False

    try:
        with open(queue_file, 'r', encoding='utf-8') as f:
            queue_state = json.load(f)

        # 检查队列状态是否被意外重置
        current_status = queue_state.get('queue_status', '')
        current_item = queue_state.get('current_item_id', '')

        # 如果队列状态异常，自动修复
        if current_status == 'manual_hold' and current_item == '':
            print("⚠️ 检测到队列状态被意外重置，正在修复...")

            # 查找可执行任务
            items = queue_state.get('items', {})
            executable_tasks = []

            for task_id, task in items.items():
                status = task.get('status', '')
                if status in ['pending', '']:
                    executable_tasks.append(task_id)

            if executable_tasks:
                # 修复队列状态
                queue_state['queue_status'] = 'running'
                queue_state['current_item_id'] = executable_tasks[0]
                queue_state['current_item_ids'] = executable_tasks
                queue_state['pause_reason'] = ''
                queue_state['updated_at'] = datetime.now().isoformat()

                # 保存修复后的状态
                with open(queue_file, 'w', encoding='utf-8') as f:
                    json.dump(queue_state, f, indent=2, ensure_ascii=False)

                print(f"✅ 队列状态已修复，当前任务: {executable_tasks[0]}")
                return True
            else:
                print("❌ 没有发现可执行任务")
                return False
        else:
            print("✅ 队列状态正常")
            return True

    except Exception as e:
        print(f"❌ 队列状态保护失败: {e}")
        return False

if __name__ == "__main__":
    protect_queue_state()
'''

    script_path = "/Volumes/1TB-M2/openclaw/protect_queue_state.py"

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(protection_script)

        # 设置执行权限
        os.chmod(script_path, 0o755)

        print(f"✅ 队列状态保护脚本已创建: {script_path}")

        # 创建监控脚本
        monitor_script = """#!/bin/bash
# 队列状态保护监控脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROTECT_SCRIPT="$SCRIPT_DIR/protect_queue_state.py"
LOG_FILE="$SCRIPT_DIR/queue_protection.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 保护监控循环
monitor_protection() {
    while true; do
        log "🔍 检查队列状态保护..."

        # 运行保护脚本
        python3 "$PROTECT_SCRIPT" >> "$LOG_FILE" 2>&1

        if [ $? -eq 0 ]; then
            log "✅ 队列状态保护正常"
        else:
            log "⚠️ 队列状态保护异常"
        fi

        # 等待3分钟再次检查
        sleep 180
    done
}

# 启动监控
log "🛡️ 启动队列状态保护监控"
monitor_protection
"""

        monitor_path = "/Volumes/1TB-M2/openclaw/monitor_queue_protection.sh"

        with open(monitor_path, "w", encoding="utf-8") as f:
            f.write(monitor_script)

        os.chmod(monitor_path, 0o755)

        print(f"✅ 队列状态保护监控脚本已创建: {monitor_path}")

        return script_path, monitor_path

    except Exception as e:
        print(f"❌ 创建队列状态保护机制失败: {e}")
        return None, None


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 队列状态被意外重置问题修复工具")
    print("=" * 60)

    # 诊断问题
    queue_state = diagnose_queue_state_reset()
    if not queue_state:
        print("❌ 诊断失败，无法继续修复")
        return

    # 检查Web服务器队列读取逻辑
    if not check_web_server_queue_reading():
        print("⚠️ Web服务器队列读取逻辑可能存在问题")

    # 修复队列状态重置问题
    if fix_queue_state_reset():
        print("\n✅ 队列状态重置问题修复成功")
    else:
        print("\n❌ 队列状态重置问题修复失败")
        return

    # 创建队列状态保护机制
    protect_script, monitor_script = create_queue_state_protection()

    print("\n🎯 修复完成，下一步操作:")
    print("1. 访问 http://127.0.0.1:8080 验证队列状态")
    print("2. 测试手动拉起按钮功能")
    print("3. 检查无法定位当前队列项错误是否消失")
    print("4. 启动队列状态保护监控: nohup bash monitor_queue_protection.sh &")


if __name__ == "__main__":
    main()
