#!/usr/bin/env python3
"""
修复Web服务器配置与实际队列状态不一致问题
解决无法定位当前队列项错误
"""

import json
import os
import shutil
from datetime import datetime


def check_config_sync():
    """检查配置同步状态"""

    print("🔍 检查Web服务器配置与实际队列状态同步...")

    # Web服务器配置路径
    web_config_path = "/Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/.athena-auto-queue.json"

    # 实际队列状态文件路径
    queue_state_path = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    # 检查文件存在性
    if not os.path.exists(web_config_path):
        print(f"❌ Web服务器配置文件不存在: {web_config_path}")
        return False

    if not os.path.exists(queue_state_path):
        print(f"❌ 队列状态文件不存在: {queue_state_path}")
        return False

    # 读取Web配置
    try:
        with open(web_config_path, "r", encoding="utf-8") as f:
            web_config = json.load(f)

        print("✅ Web服务器配置文件读取成功")
    except Exception as e:
        print(f"❌ 读取Web服务器配置失败: {e}")
        return False

    # 读取队列状态
    try:
        with open(queue_state_path, "r", encoding="utf-8") as f:
            queue_state = json.load(f)

        print("✅ 队列状态文件读取成功")
    except Exception as e:
        print(f"❌ 读取队列状态文件失败: {e}")
        return False

    # 检查队列ID一致性
    web_queue_id = None
    for route in web_config.get("routes", []):
        if route.get("queue_id") == "openhuman_aiplan_plan_manual_20260328":
            web_queue_id = route.get("queue_id")
            break

    actual_queue_id = queue_state.get("queue_id")

    print(f"🔍 Web配置队列ID: {web_queue_id}")
    print(f"🔍 实际队列ID: {actual_queue_id}")

    if web_queue_id != actual_queue_id:
        print("❌ 队列ID不一致!")
        return False

    print("✅ 队列ID一致")
    return True


def fix_queue_state_for_web():
    """修复队列状态以匹配Web服务器配置"""

    print("\n🔧 修复队列状态以匹配Web服务器配置...")

    queue_state_path = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    try:
        with open(queue_state_path, "r", encoding="utf-8") as f:
            queue_state = json.load(f)

        # 分析当前状态
        items = queue_state.get("items", {})

        print("📊 当前队列状态分析:")
        for task_id, task in items.items():
            status = task.get("status", "unknown")
            print(f"   {task_id}: {status}")

        # 查找需要修复的任务
        manual_hold_tasks = []
        pending_tasks = []

        for task_id, task in items.items():
            status = task.get("status", "")
            if status == "manual_hold":
                manual_hold_tasks.append(task_id)
            elif status in ["pending", ""]:
                pending_tasks.append(task_id)

        print(f"🔍 手动保留任务: {manual_hold_tasks}")
        print(f"🔍 待执行任务: {pending_tasks}")

        # 修复策略：如果只有手动任务，激活第一个作为当前任务
        if not pending_tasks and manual_hold_tasks:
            print("⚠️ 只有手动保留任务，需要激活一个作为当前任务")

            # 激活第一个手动任务
            first_task = manual_hold_tasks[0]
            items[first_task]["status"] = "pending"
            items[first_task]["progress_percent"] = 0

            # 更新队列状态
            queue_state["current_item_id"] = first_task
            queue_state["current_item_ids"] = [first_task]
            queue_state["queue_status"] = "running"
            queue_state["pause_reason"] = ""

            print(f"✅ 激活手动任务: {first_task}")

        # 更新任务计数
        counts = queue_state.get("counts", {})
        counts["pending"] = len([t for t in items.values() if t.get("status") in ["pending", ""]])
        counts["running"] = 1 if queue_state["current_item_id"] else 0
        counts["manual_hold"] = len([t for t in items.values() if t.get("status") == "manual_hold"])
        queue_state["counts"] = counts

        # 更新时间戳
        queue_state["updated_at"] = datetime.now().isoformat()

        # 保存修复后的状态
        with open(queue_state_path, "w", encoding="utf-8") as f:
            json.dump(queue_state, f, indent=2, ensure_ascii=False)

        print("✅ 队列状态修复完成")
        print(f"📊 新队列状态: {queue_state['queue_status']}")
        print(f"🎯 当前任务: {queue_state['current_item_id']}")

        return True

    except Exception as e:
        print(f"❌ 修复队列状态失败: {e}")
        return False


def restart_web_server():
    """重启Web服务器"""

    print("\n🔄 重启Web服务器以应用配置更改...")

    web_script = "/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py"

    if not os.path.exists(web_script):
        print(f"❌ Web服务器脚本不存在: {web_script}")
        return False

    try:
        import subprocess

        # 停止现有Web服务器
        subprocess.run(["pkill", "-f", "athena_web_desktop_compat.py"], capture_output=True)

        # 等待停止
        import time

        time.sleep(2)

        # 启动新的Web服务器
        subprocess.Popen(
            ["python3", web_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # 等待启动
        time.sleep(5)

        # 验证服务启动
        import requests

        try:
            response = requests.get("http://127.0.0.1:8080", timeout=10)
            if response.status_code == 200:
                print("✅ Web服务器重启成功")
                return True
            else:
                print(f"⚠️ Web服务器响应异常: {response.status_code}")
                return False
        except:
            print("❌ Web服务器重启后无法访问")
            return False

    except Exception as e:
        print(f"❌ 重启Web服务器失败: {e}")
        return False


def create_config_sync_monitor():
    """创建配置同步监控脚本"""

    print("\n📋 创建配置同步监控脚本...")

    script_content = """#!/bin/bash
# Athena Web配置与队列状态同步监控脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/fix_web_config_sync.py"
LOG_FILE="$SCRIPT_DIR/config_sync_monitor.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查配置同步状态
check_sync() {
    log "🔍 检查配置同步状态..."
    
    # 运行同步检查脚本
    python3 "$SYNC_SCRIPT" --check-only >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        log "✅ 配置同步正常"
        return 0
    else
        log "⚠️ 配置同步异常，尝试修复"
        
        # 运行修复脚本
        python3 "$SYNC_SCRIPT" --fix-only >> "$LOG_FILE" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ 配置同步修复成功"
        else
            log "❌ 配置同步修复失败"
        fi
        
        return 1
    fi
}

# 监控循环
monitor_sync() {
    while true; do
        check_sync
        
        # 等待10分钟再次检查
        sleep 600
    done
}

# 启动监控
log "🚀 启动Athena Web配置同步监控"
monitor_sync
"""

    script_path = "/Volumes/1TB-M2/openclaw/monitor_config_sync.sh"

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # 设置执行权限
        os.chmod(script_path, 0o755)

        print(f"✅ 配置同步监控脚本已创建: {script_path}")

        return script_path

    except Exception as e:
        print(f"❌ 创建配置同步监控脚本失败: {e}")
        return None


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 Athena Web配置与队列状态同步修复工具")
    print("=" * 60)

    # 检查配置同步状态
    if not check_config_sync():
        print("\n❌ 配置同步检查失败")
        return

    # 修复队列状态
    if not fix_queue_state_for_web():
        print("\n❌ 队列状态修复失败")
        return

    # 重启Web服务器
    if not restart_web_server():
        print("\n⚠️ Web服务器重启可能存在问题")

    # 创建配置同步监控脚本
    create_config_sync_monitor()

    print("\n🎯 修复完成，下一步操作:")
    print("1. 访问 http://127.0.0.1:8080 验证队列状态")
    print("2. 测试手动拉起按钮功能")
    print("3. 检查无法定位当前队列项错误是否消失")
    print("4. 启动配置同步监控: nohup bash monitor_config_sync.sh &")


if __name__ == "__main__":
    main()
