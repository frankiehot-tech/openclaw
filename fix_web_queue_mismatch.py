#!/usr/bin/env python3
"""
修复Web界面与队列状态不匹配问题
彻底解决无法定位当前队列项错误
"""

import json
import os
import subprocess
import time
from datetime import datetime

import requests


def check_web_interface_state():
    """检查Web界面实际状态"""

    print("🌐 检查Web界面实际状态...")

    try:
        # 尝试访问Web界面API获取队列状态
        response = requests.get("http://127.0.0.1:8080/api/queues", timeout=10)

        if response.status_code == 200:
            web_data = response.json()
            print("✅ Web界面API访问成功")

            # 分析Web界面返回的队列状态
            if "routes" in web_data:
                for route in web_data["routes"]:
                    if route.get("queue_id") == "openhuman_aiplan_plan_manual_20260328":
                        print(f"📊 Web界面队列状态: {route.get('queue_status', 'unknown')}")
                        print(f"🎯 Web界面当前任务: {route.get('current_item_id', '无')}")
                        print(f"📈 Web界面任务计数: {route.get('counts', {})}")
                        return route

            return web_data
        else:
            print(f"❌ Web界面API响应异常: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ 访问Web界面API失败: {e}")

        # 尝试直接访问页面
        try:
            response = requests.get("http://127.0.0.1:8080", timeout=10)
            if response.status_code == 200:
                print("✅ Web界面页面访问成功")
                return {"status": "web_accessible"}
            else:
                print(f"❌ Web界面页面响应异常: {response.status_code}")
                return None
        except Exception as e2:
            print(f"❌ 访问Web界面页面失败: {e2}")
            return None


def check_actual_queue_state():
    """检查实际队列状态"""

    print("\n📊 检查实际队列状态...")

    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    if not os.path.exists(queue_file):
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return None

    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            queue_state = json.load(f)

        print(f"📊 实际队列状态: {queue_state.get('queue_status', 'unknown')}")
        print(f"🎯 实际当前任务: {queue_state.get('current_item_id', '无')}")
        print(f"📈 实际任务计数: {queue_state.get('counts', {})}")

        return queue_state

    except Exception as e:
        print(f"❌ 读取实际队列状态失败: {e}")
        return None


def check_web_server_config():
    """检查Web服务器配置"""

    print("\n🔧 检查Web服务器配置...")

    web_script = "/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py"

    if not os.path.exists(web_script):
        print(f"❌ Web服务器脚本不存在: {web_script}")
        return False

    try:
        # 读取Web服务器代码
        with open(web_script, "r", encoding="utf-8") as f:
            web_code = f.read()

        # 检查队列读取逻辑
        if "load_route_state" in web_code:
            print("✅ Web服务器包含队列状态读取函数")
        else:
            print("❌ Web服务器缺少队列状态读取函数")

        # 检查队列状态路径生成
        if "route_state_path" in web_code:
            print("✅ Web服务器包含队列状态路径生成逻辑")
        else:
            print("❌ Web服务器缺少队列状态路径生成逻辑")

        # 检查队列ID匹配
        if "queue_id" in web_code:
            print("✅ Web服务器包含队列ID匹配逻辑")
        else:
            print("❌ Web服务器缺少队列ID匹配逻辑")

        # 检查缓存机制
        if "cache" in web_code.lower() or "cache" in web_code:
            print("⚠️ Web服务器可能包含缓存机制")
        else:
            print("✅ Web服务器无缓存机制")

        return True

    except Exception as e:
        print(f"❌ 检查Web服务器配置失败: {e}")
        return False


def fix_web_queue_mismatch():
    """修复Web界面与队列状态不匹配问题"""

    print("\n🔧 修复Web界面与队列状态不匹配问题...")

    # 检查实际队列状态
    actual_state = check_actual_queue_state()
    if not actual_state:
        print("❌ 无法获取实际队列状态")
        return False

    # 检查Web界面状态
    web_state = check_web_interface_state()

    # 分析不匹配问题
    actual_status = actual_state.get("queue_status", "")
    actual_item = actual_state.get("current_item_id", "")

    print(f"\n🔍 状态对比分析:")
    print(f"   实际队列状态: {actual_status}")
    print(f"   实际当前任务: {actual_item}")

    if web_state and "queue_status" in web_state:
        web_status = web_state.get("queue_status", "")
        web_item = web_state.get("current_item_id", "")
        print(f"   Web界面状态: {web_status}")
        print(f"   Web界面任务: {web_item}")

        if actual_status != web_status or actual_item != web_item:
            print("❌ Web界面与实际队列状态不匹配!")
    else:
        print("⚠️ 无法获取Web界面状态")

    # 修复策略
    if actual_status == "manual_hold" and actual_item == "":
        print("\n🔧 检测到队列状态异常，正在修复...")

        queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"

        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                queue_state = json.load(f)

            items = queue_state.get("items", {})

            # 查找可执行任务
            executable_tasks = []
            for task_id, task in items.items():
                status = task.get("status", "")
                if status in ["pending", ""]:
                    executable_tasks.append(task_id)

            if executable_tasks:
                # 修复队列状态
                queue_state["queue_status"] = "running"
                queue_state["current_item_id"] = executable_tasks[0]
                queue_state["current_item_ids"] = executable_tasks
                queue_state["pause_reason"] = ""
                queue_state["updated_at"] = datetime.now().isoformat()

                # 更新任务计数
                counts = queue_state.get("counts", {})
                counts["pending"] = len(executable_tasks)
                counts["running"] = 1
                counts["manual_hold"] = len(
                    [t for t in items.values() if t.get("status") == "manual_hold"]
                )
                queue_state["counts"] = counts

                # 保存修复后的状态
                with open(queue_file, "w", encoding="utf-8") as f:
                    json.dump(queue_state, f, indent=2, ensure_ascii=False)

                print(f"✅ 队列状态已修复，当前任务: {executable_tasks[0]}")

                # 重启Web服务器以清除缓存
                print("\n🔄 重启Web服务器以清除缓存...")
                restart_web_server()

                return True
            else:
                print("❌ 没有发现可执行任务")
                return False

        except Exception as e:
            print(f"❌ 修复队列状态失败: {e}")
            return False
    else:
        print("✅ 队列状态正常，无需修复")
        return True


def restart_web_server():
    """重启Web服务器"""

    print("🔄 重启Web服务器...")

    web_script = "/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py"

    if not os.path.exists(web_script):
        print(f"❌ Web服务器脚本不存在: {web_script}")
        return False

    try:
        # 停止现有Web服务器
        subprocess.run(["pkill", "-f", "athena_web_desktop_compat.py"], capture_output=True)

        # 等待停止
        time.sleep(2)

        # 启动新的Web服务器
        subprocess.Popen(
            ["python3", web_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # 等待启动
        time.sleep(5)

        # 验证服务启动
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


def create_web_queue_sync_monitor():
    """创建Web界面与队列状态同步监控"""

    print("\n📋 创建Web界面与队列状态同步监控...")

    monitor_script = """#!/bin/bash
# Web界面与队列状态同步监控脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/fix_web_queue_mismatch.py"
LOG_FILE="$SCRIPT_DIR/web_queue_sync.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 同步检查循环
monitor_sync() {
    while true; do
        log "🔍 检查Web界面与队列状态同步..."
        
        # 运行同步检查脚本
        python3 "$SYNC_SCRIPT" --check-only >> "$LOG_FILE" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ Web界面与队列状态同步正常"
        else:
            log "⚠️ Web界面与队列状态同步异常，尝试修复"
            
            # 运行修复脚本
            python3 "$SYNC_SCRIPT" --fix-only >> "$LOG_FILE" 2>&1
            
            if [ $? -eq 0 ]; then
                log "✅ Web界面与队列状态同步修复成功"
            else:
                log "❌ Web界面与队列状态同步修复失败"
            fi
        fi
        
        # 等待5分钟再次检查
        sleep 300
    done
}

# 启动监控
log "🔄 启动Web界面与队列状态同步监控"
monitor_sync
"""

    script_path = "/Volumes/1TB-M2/openclaw/monitor_web_queue_sync.sh"

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(monitor_script)

        # 设置执行权限
        os.chmod(script_path, 0o755)

        print(f"✅ Web界面与队列状态同步监控脚本已创建: {script_path}")

        return script_path

    except Exception as e:
        print(f"❌ 创建同步监控脚本失败: {e}")
        return None


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 Web界面与队列状态不匹配问题修复工具")
    print("=" * 60)

    # 检查Web服务器配置
    if not check_web_server_config():
        print("❌ Web服务器配置检查失败")
        return

    # 修复Web界面与队列状态不匹配问题
    if fix_web_queue_mismatch():
        print("\n✅ Web界面与队列状态不匹配问题修复成功")
    else:
        print("\n❌ Web界面与队列状态不匹配问题修复失败")
        return

    # 创建同步监控
    create_web_queue_sync_monitor()

    print("\n🎯 修复完成，下一步操作:")
    print("1. 访问 http://127.0.0.1:8080 验证队列状态")
    print("2. 测试手动拉起按钮功能")
    print("3. 检查无法定位当前队列项错误是否消失")
    print("4. 启动同步监控: nohup bash monitor_web_queue_sync.sh &")


if __name__ == "__main__":
    main()
