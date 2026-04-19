#!/usr/bin/env python3
"""
修复所有队列停止问题
综合解决队列状态被意外重置问题
"""

import json
import os
import subprocess
import time
from datetime import datetime


def check_all_queues():
    """检查所有队列状态"""

    print("🔍 检查所有队列状态...")

    queue_dir = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue"

    if not os.path.exists(queue_dir):
        print(f"❌ 队列目录不存在: {queue_dir}")
        return None

    # 获取所有队列文件
    queue_files = []
    for file in os.listdir(queue_dir):
        if file.endswith(".json") and not file.endswith(".lock"):
            queue_files.append(os.path.join(queue_dir, file))

    print(f"📋 发现 {len(queue_files)} 个队列文件")

    queue_statuses = {}

    for queue_file in queue_files:
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                queue_state = json.load(f)

            queue_id = queue_state.get("queue_id", "unknown")
            status = queue_state.get("queue_status", "unknown")
            current_item = queue_state.get("current_item_id", "")

            queue_statuses[queue_id] = {
                "file": queue_file,
                "status": status,
                "current_item": current_item,
                "state": queue_state,
            }

            print(f"   {queue_id}: {status} (当前任务: {current_item if current_item else '无'})")

        except Exception as e:
            print(f"❌ 读取队列文件失败 {queue_file}: {e}")

    return queue_statuses


def check_queue_runners():
    """检查队列运行器状态"""

    print("\n🔍 检查队列运行器状态...")

    runners = [
        "athena_ai_plan_runner.py",
        "athena_ai_plan_runner_build.py",
        "athena_ai_plan_runner_codex.py",
    ]

    runner_status = {}

    for runner in runners:
        try:
            result = subprocess.run(["pgrep", "-f", runner], capture_output=True, text=True)

            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                runner_status[runner] = {"running": True, "pids": pids}
                print(f"✅ {runner}: 运行中 (PID: {', '.join(pids)})")
            else:
                runner_status[runner] = {"running": False, "pids": []}
                print(f"❌ {runner}: 未运行")

        except Exception as e:
            print(f"❌ 检查运行器 {runner} 失败: {e}")
            runner_status[runner] = {"running": False, "pids": []}

    return runner_status


def fix_queue_stopped(queue_statuses):
    """修复队列停止问题"""

    print("\n🔧 修复队列停止问题...")

    fixes_applied = []

    for queue_id, queue_info in queue_statuses.items():
        queue_file = queue_info["file"]
        status = queue_info["status"]
        current_item = queue_info["current_item"]
        queue_state = queue_info["state"]

        # 检查是否需要修复
        needs_fix = False

        if status in ["manual_hold", "stopped", "unknown"]:
            needs_fix = True
            print(f"⚠️ 队列 {queue_id} 状态异常: {status}")

        if not current_item:
            needs_fix = True
            print(f"⚠️ 队列 {queue_id} 当前任务为空")

        if needs_fix:
            try:
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

                    print(f"✅ 队列 {queue_id} 已修复，当前任务: {executable_tasks[0]}")
                    fixes_applied.append(queue_id)

                else:
                    print(f"⚠️ 队列 {queue_id} 没有发现可执行任务")

            except Exception as e:
                print(f"❌ 修复队列 {queue_id} 失败: {e}")
        else:
            print(f"✅ 队列 {queue_id} 状态正常")

    return fixes_applied


def restart_queue_runners(runner_status):
    """重启队列运行器"""

    print("\n🔄 重启队列运行器...")

    scripts_dir = "/Volumes/1TB-M2/openclaw/scripts"

    if not os.path.exists(scripts_dir):
        print(f"❌ 脚本目录不存在: {scripts_dir}")
        return False

    runners_restarted = []

    for runner_name, status in runner_status.items():
        if not status["running"]:
            runner_script = os.path.join(scripts_dir, runner_name)

            if os.path.exists(runner_script):
                try:
                    # 启动运行器
                    subprocess.Popen(
                        ["python3", runner_script],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

                    # 等待启动
                    time.sleep(3)

                    # 验证启动
                    result = subprocess.run(
                        ["pgrep", "-f", runner_name], capture_output=True, text=True
                    )

                    if result.returncode == 0:
                        print(f"✅ {runner_name} 重启成功")
                        runners_restarted.append(runner_name)
                    else:
                        print(f"❌ {runner_name} 重启失败")

                except Exception as e:
                    print(f"❌ 重启 {runner_name} 失败: {e}")
            else:
                print(f"⚠️ 运行器脚本不存在: {runner_script}")
        else:
            print(f"✅ {runner_name} 已在运行")

    return runners_restarted


def create_comprehensive_protection():
    """创建全面保护机制"""

    print("\n🛡️ 创建全面队列保护机制...")

    protection_script = '''#!/usr/bin/env python3
"""
全面队列保护脚本
防止所有队列状态被意外重置
"""

import json
import os
import time
from datetime import datetime
import subprocess

def protect_all_queues():
    """保护所有队列状态"""
    
    queue_dir = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue"
    
    if not os.path.exists(queue_dir):
        print(f"❌ 队列目录不存在: {queue_dir}")
        return False
    
    # 获取所有队列文件
    queue_files = []
    for file in os.listdir(queue_dir):
        if file.endswith('.json') and not file.endswith('.lock'):
            queue_files.append(os.path.join(queue_dir, file))
    
    protected_count = 0
    
    for queue_file in queue_files:
        try:
            with open(queue_file, 'r', encoding='utf-8') as f:
                queue_state = json.load(f)
            
            queue_id = queue_state.get('queue_id', 'unknown')
            status = queue_state.get('queue_status', '')
            current_item = queue_state.get('current_item_id', '')
            
            # 检查队列状态是否异常
            if status in ['manual_hold', 'stopped', 'unknown'] and current_item == '':
                print(f"⚠️ 检测到队列 {queue_id} 状态异常，正在修复...")
                
                # 查找可执行任务
                items = queue_state.get('items', {})
                executable_tasks = []
                
                for task_id, task in items.items():
                    task_status = task.get('status', '')
                    if task_status in ['pending', '']:
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
        'athena_ai_plan_runner.py',
        'athena_ai_plan_runner_build.py',
        'athena_ai_plan_runner_codex.py'
    ]
    
    scripts_dir = "/Volumes/1TB-M2/openclaw/scripts"
    
    for runner in runners:
        try:
            result = subprocess.run(['pgrep', '-f', runner], 
                                 capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"⚠️ {runner} 未运行，正在启动...")
                
                runner_script = os.path.join(scripts_dir, runner)
                if os.path.exists(runner_script):
                    subprocess.Popen(['python3', runner_script], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
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
'''

    script_path = "/Volumes/1TB-M2/openclaw/protect_all_queues.py"

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(protection_script)

        # 设置执行权限
        os.chmod(script_path, 0o755)

        print(f"✅ 全面队列保护脚本已创建: {script_path}")

        # 创建监控脚本
        monitor_script = """#!/bin/bash
# 全面队列保护监控脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROTECT_SCRIPT="$SCRIPT_DIR/protect_all_queues.py"
LOG_FILE="$SCRIPT_DIR/all_queues_protection.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 保护监控循环
monitor_protection() {
    while true; do
        log "🔍 检查所有队列状态保护..."
        
        # 运行保护脚本
        python3 "$PROTECT_SCRIPT" >> "$LOG_FILE" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ 所有队列状态保护正常"
        else:
            log "⚠️ 队列状态保护异常"
        fi
        
        # 等待2分钟再次检查
        sleep 120
    done
}

# 启动监控
log "🛡️ 启动全面队列状态保护监控"
monitor_protection
"""

        monitor_path = "/Volumes/1TB-M2/openclaw/monitor_all_queues_protection.sh"

        with open(monitor_path, "w", encoding="utf-8") as f:
            f.write(monitor_script)

        os.chmod(monitor_path, 0o755)

        print(f"✅ 全面队列保护监控脚本已创建: {monitor_path}")

        return script_path, monitor_path

    except Exception as e:
        print(f"❌ 创建全面保护机制失败: {e}")
        return None, None


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 所有队列停止问题综合修复工具")
    print("=" * 60)

    # 检查所有队列状态
    queue_statuses = check_all_queues()
    if not queue_statuses:
        print("❌ 检查队列状态失败")
        return

    # 检查队列运行器状态
    runner_status = check_queue_runners()

    # 修复队列停止问题
    fixes_applied = fix_queue_stopped(queue_statuses)

    # 重启队列运行器
    runners_restarted = restart_queue_runners(runner_status)

    # 创建全面保护机制
    protect_script, monitor_script = create_comprehensive_protection()

    print("\n🎯 修复完成，总结:")
    print(f"📊 修复了 {len(fixes_applied)} 个队列: {fixes_applied}")
    print(f"🔄 重启了 {len(runners_restarted)} 个运行器: {runners_restarted}")

    print("\n🎯 下一步操作:")
    print("1. 访问 http://127.0.0.1:8080 验证所有队列状态")
    print("2. 测试手动拉起按钮功能")
    print("3. 检查无法定位当前队列项错误是否消失")
    print("4. 启动全面队列保护监控: nohup bash monitor_all_queues_protection.sh &")


if __name__ == "__main__":
    main()
