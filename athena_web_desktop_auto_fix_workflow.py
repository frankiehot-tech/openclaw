#!/usr/bin/env python3
"""
Athena Web Desktop 工作流自动修复任务
无人值守跑通工作流，自动诊断并修复任务队列停止问题
"""

import json
import os
import subprocess
import time
from datetime import datetime

import requests


class AthenaWorkflowAutoFix:
    """Athena工作流自动修复类"""

    def __init__(self):
        self.web_url = "http://127.0.0.1:8080"
        self.queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
        self.runner_script = "/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"
        self.web_server_script = "/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py"

    def check_web_service(self):
        """检查Web服务状态"""
        print("🌐 检查Athena Web Desktop服务状态...")

        try:
            # 尝试访问根路径
            response = requests.get(self.web_url, timeout=10)

            if response.status_code == 200:
                print("✅ Web服务正常运行")
                return True
            else:
                print(f"⚠️ Web服务响应异常: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Web服务连接失败: {e}")
            return False

    def check_queue_status(self):
        """检查队列状态"""
        print("\n📊 检查任务队列状态...")

        if not os.path.exists(self.queue_file):
            print(f"❌ 队列状态文件不存在: {self.queue_file}")
            return None

        try:
            with open(self.queue_file, encoding="utf-8") as f:
                queue_state = json.load(f)

            status = queue_state.get("queue_status", "unknown")
            current_item = queue_state.get("current_item_id", "")
            counts = queue_state.get("counts", {})

            print(f"📊 队列状态: {status}")
            print(f"⏸️  暂停原因: {queue_state.get('pause_reason', 'unknown')}")
            print(f"🎯 当前任务: {current_item}")
            print(
                f"📈 任务统计: pending={counts.get('pending', 0)}, running={counts.get('running', 0)}, completed={counts.get('completed', 0)}, manual_hold={counts.get('manual_hold', 0)}"
            )

            return queue_state

        except Exception as e:
            print(f"❌ 检查队列状态失败: {e}")
            return None

    def check_runner_process(self):
        """检查队列运行器进程"""
        print("\n🔍 检查队列运行器进程...")

        try:
            result = subprocess.run(
                ["pgrep", "-f", "athena_ai_plan_runner.py"], capture_output=True, text=True
            )

            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                print(f"✅ 队列运行器正在运行，PID: {', '.join(pids)}")
                return True
            else:
                print("❌ 队列运行器未运行")
                return False

        except Exception as e:
            print(f"❌ 检查运行器进程失败: {e}")
            return False

    def diagnose_queue_problems(self):
        """诊断队列问题"""
        print("\n🔧 开始诊断队列问题...")

        problems = []

        # 检查Web服务
        if not self.check_web_service():
            problems.append("web_service_down")

        # 检查队列状态
        queue_state = self.check_queue_status()
        if not queue_state:
            problems.append("queue_state_invalid")
        elif queue_state.get("queue_status") == "manual_hold":
            problems.append("queue_manual_hold")
        elif queue_state.get("current_item_id") == "":
            problems.append("no_current_task")

        # 检查运行器进程
        if not self.check_runner_process():
            problems.append("runner_not_running")

        return problems, queue_state

    def fix_web_service(self):
        """修复Web服务"""
        print("\n🔄 修复Web服务...")

        if not os.path.exists(self.web_server_script):
            print(f"❌ Web服务器脚本不存在: {self.web_server_script}")
            return False

        try:
            # 停止现有Web服务
            subprocess.run(["pkill", "-f", "athena_web_desktop_compat.py"], capture_output=True)
            time.sleep(2)

            # 启动新的Web服务
            subprocess.Popen(
                ["python3", self.web_server_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # 等待服务启动
            time.sleep(5)

            # 验证服务启动
            if self.check_web_service():
                print("✅ Web服务修复成功")
                return True
            else:
                print("❌ Web服务修复失败")
                return False

        except Exception as e:
            print(f"❌ 修复Web服务失败: {e}")
            return False

    def fix_queue_manual_hold(self, queue_state):
        """修复队列手动保留状态"""
        print("\n🔧 修复队列手动保留状态...")

        try:
            with open(self.queue_file, encoding="utf-8") as f:
                queue_state = json.load(f)

            # 查找可自动执行的任务
            items = queue_state.get("items", {})
            auto_ready_tasks = []

            for task_id, task in items.items():
                status = task.get("status", "")
                if status in ["pending", ""]:
                    auto_ready_tasks.append(task_id)

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
                with open(self.queue_file, "w", encoding="utf-8") as f:
                    json.dump(queue_state, f, indent=2, ensure_ascii=False)

                print(f"✅ 队列手动保留状态已修复，当前任务: {auto_ready_tasks[0]}")
                return True
            else:
                print("⚠️ 没有发现可自动执行的任务")
                return False

        except Exception as e:
            print(f"❌ 修复队列手动保留状态失败: {e}")
            return False

    def restart_queue_runner(self):
        """重启队列运行器"""
        print("\n🔄 重启队列运行器...")

        if not os.path.exists(self.runner_script):
            print(f"❌ 队列运行器脚本不存在: {self.runner_script}")
            return False

        try:
            # 停止现有运行器
            subprocess.run(["pkill", "-f", "athena_ai_plan_runner.py"], capture_output=True)
            time.sleep(2)

            # 启动新的运行器
            subprocess.Popen(
                ["python3", self.runner_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # 等待运行器启动
            time.sleep(3)

            # 验证运行器启动
            if self.check_runner_process():
                print("✅ 队列运行器重启成功")
                return True
            else:
                print("❌ 队列运行器重启失败")
                return False

        except Exception as e:
            print(f"❌ 重启队列运行器失败: {e}")
            return False

    def auto_fix_workflow(self):
        """自动修复工作流"""
        print("=" * 60)
        print("🚀 Athena Web Desktop 工作流自动修复任务")
        print("=" * 60)

        # 诊断问题
        problems, queue_state = self.diagnose_queue_problems()

        if not problems:
            print("\n✅ 工作流状态正常，无需修复")
            return True

        print(f"\n🔍 发现 {len(problems)} 个问题: {problems}")

        # 执行修复
        fixes_applied = []

        if "web_service_down" in problems and self.fix_web_service():
            fixes_applied.append("web_service")

        if "runner_not_running" in problems and self.restart_queue_runner():
            fixes_applied.append("queue_runner")

        if "queue_manual_hold" in problems and self.fix_queue_manual_hold(queue_state):
            fixes_applied.append("queue_status")

        if "no_current_task" in problems and self.fix_queue_manual_hold(queue_state):
            fixes_applied.append("current_task")

        # 验证修复结果
        print("\n🔍 验证修复结果...")
        final_problems, _ = self.diagnose_queue_problems()

        if not final_problems:
            print("\n✅ 工作流自动修复成功!")
            print(f"📋 应用的修复: {fixes_applied}")
            return True
        else:
            print(f"\n⚠️ 部分问题未解决: {final_problems}")
            print(f"📋 已应用的修复: {fixes_applied}")
            return False

    def create_monitoring_script(self):
        """创建无人值守监控脚本"""
        print("\n📋 创建无人值守监控脚本...")

        script_content = """#!/bin/bash
# Athena工作流无人值守监控脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTO_FIX_SCRIPT="$SCRIPT_DIR/athena_web_desktop_auto_fix_workflow.py"
LOG_FILE="$SCRIPT_DIR/workflow_monitor.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 监控循环
monitor_workflow() {
    while true; do
        log "🔍 检查工作流状态..."

        # 运行自动修复脚本
        python3 "$AUTO_FIX_SCRIPT" >> "$LOG_FILE" 2>&1

        if [ $? -eq 0 ]; then
            log "✅ 工作流状态正常"
        else
            log "⚠️ 工作流存在问题，已尝试修复"
        fi

        # 等待5分钟再次检查
        sleep 300
    done
}

# 启动监控
log "🚀 启动Athena工作流无人值守监控"
monitor_workflow
"""

        script_path = "/Volumes/1TB-M2/openclaw/monitor_athena_workflow.sh"

        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            # 设置执行权限
            os.chmod(script_path, 0o755)

            print(f"✅ 监控脚本已创建: {script_path}")
            print("💡 使用方法: nohup bash monitor_athena_workflow.sh &")

            return script_path

        except Exception as e:
            print(f"❌ 创建监控脚本失败: {e}")
            return None


def main():
    """主函数"""

    # 创建工作流自动修复实例
    workflow_fix = AthenaWorkflowAutoFix()

    # 执行自动修复
    success = workflow_fix.auto_fix_workflow()

    # 创建无人值守监控脚本
    if success:
        workflow_fix.create_monitoring_script()

    print("\n🎯 下一步操作:")
    print("1. 访问 http://127.0.0.1:8080 验证工作流状态")
    print("2. 启动无人值守监控: nohup bash monitor_athena_workflow.sh &")
    print("3. 监控日志文件: tail -f workflow_monitor.log")


if __name__ == "__main__":
    main()
