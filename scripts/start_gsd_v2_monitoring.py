#!/usr/bin/env python3
"""GSD V2 实施监控启动脚本"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path


class GSDV2Monitor:
    """GSD V2 实施监控器"""

    def __init__(self):
        self.base_dir = Path("/Volumes/1TB-M2/openclaw")
        self.gsd_v2_dir = Path.home() / ".openclaw"
        self.monitor_dir = self.base_dir / "workspace" / "gsd_v2_monitoring"
        self.monitor_dir.mkdir(parents=True, exist_ok=True)

    def start_environment_monitor(self):
        """启动环境监控"""
        print("🔍 启动GSD V2环境监控...")

        # 创建环境监控脚本
        monitor_script = self.monitor_dir / "environment_monitor.py"

        monitor_code = '''#!/usr/bin/env python3
"""GSD V2 环境监控脚本"""

import time
import psutil
import requests
import json
from datetime import datetime
from pathlib import Path

def monitor_claude_code_router():
    """监控Claude Code Router状态"""
    try:
        response = requests.get("http://127.0.0.1:3000/health", timeout=5)
        return {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "response_time": response.elapsed.total_seconds(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unreachable",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def monitor_system_resources():
    """监控系统资源"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage("/").percent,
        "timestamp": datetime.now().isoformat()
    }

def monitor_gsd_v2_status():
    """监控GSD V2状态"""
    gsd_v2_dir = Path.home() / ".openclaw"
    
    status = {
        "directories_exist": {},
        "files_exist": {},
        "state_machine_status": "unknown",
        "timestamp": datetime.now().isoformat()
    }
    
    # 检查目录
    required_dirs = ["core", "config", "workflows", "logs", "state"]
    for dir_name in required_dirs:
        dir_path = gsd_v2_dir / dir_name
        status["directories_exist"][dir_name] = dir_path.exists()
    
    # 检查关键文件
    required_files = ["core/state-machine.sh", "config/base_config.yaml", "version.json"]
    for file_path in required_files:
        full_path = gsd_v2_dir / file_path
        status["files_exist"][file_path] = full_path.exists()
    
    # 检查状态机
    state_machine = gsd_v2_dir / "core" / "state-machine.sh"
    if state_machine.exists():
        try:
            result = subprocess.run([str(state_machine), "status"], capture_output=True, text=True, timeout=10)
            status["state_machine_status"] = "running" if result.returncode == 0 else "error"
        except Exception:
            status["state_machine_status"] = "error"
    
    return status

def main():
    """主监控循环"""
    log_file = Path("/Volumes/1TB-M2/openclaw/workspace/gsd_v2_monitoring/environment_monitor.log")
    
    while True:
        try:
            # 收集监控数据
            monitor_data = {
                "claude_code": monitor_claude_code_router(),
                "system_resources": monitor_system_resources(),
                "gsd_v2_status": monitor_gsd_v2_status(),
                "timestamp": datetime.now().isoformat()
            }
            
            # 写入日志
            with open(log_file, "a") as f:
                f.write(json.dumps(monitor_data) + "\n")
            
            # 控制台输出摘要
            print(f"[{monitor_data['timestamp']}] "
                  f"CCR: {monitor_data['claude_code']['status']} | "
                  f"CPU: {monitor_data['system_resources']['cpu_percent']}% | "
                  f"Mem: {monitor_data['system_resources']['memory_percent']}%")
            
            time.sleep(60)  # 每分钟监控一次
            
        except KeyboardInterrupt:
            print("\n🛑 监控停止")
            break
        except Exception as e:
            print(f"监控错误: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
'''

        with open(monitor_script, "w") as f:
            f.write(monitor_code)

        # 设置执行权限
        monitor_script.chmod(0o755)

        return monitor_script

    def start_progress_tracker(self):
        """启动进度跟踪器"""
        print("📊 启动GSD V2进度跟踪...")

        tracker_script = self.monitor_dir / "progress_tracker.py"

        tracker_code = '''#!/usr/bin/env python3
"""GSD V2 进度跟踪脚本"""

import time
import json
from datetime import datetime
from pathlib import Path

def load_aiplan_tasks():
    """加载AIplan任务状态"""
    queue_dir = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
    
    tasks = {}
    if queue_dir.exists():
        for task_file in queue_dir.glob("gsd_v2_implementation*.json"):
            try:
                with open(task_file, 'r') as f:
                    task_data = json.load(f)
                    tasks[task_file.stem] = task_data
            except Exception as e:
                print(f"加载任务文件错误 {task_file}: {e}")
    
    return tasks

def calculate_progress(tasks):
    """计算总体进度"""
    if not tasks:
        return 0
    
    total_phases = 4  # 4个阶段
    completed_phases = 0
    
    for task_data in tasks.values():
        phases = task_data.get("phases", {})
        for phase_name, phase_data in phases.items():
            if phase_data.get("status") == "completed":
                completed_phases += 1
    
    return int((completed_phases / total_phases) * 100)

def generate_progress_report(tasks):
    """生成进度报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_progress": calculate_progress(tasks),
        "phases": {},
        "next_actions": []
    }
    
    # 分析各阶段状态
    phase_status = {
        "phase1_foundation": "pending",
        "phase2_core_integration": "pending", 
        "phase3_workflow_migration": "pending",
        "phase4_optimization": "pending"
    }
    
    for task_data in tasks.values():
        phases = task_data.get("phases", {})
        for phase_name, phase_data in phases.items():
            if phase_name in phase_status:
                phase_status[phase_name] = phase_data.get("status", "pending")
    
    report["phases"] = phase_status
    
    # 生成下一步行动建议
    if phase_status["phase1_foundation"] == "pending":
        report["next_actions"].append("执行Phase 1基础架构准备")
    elif phase_status["phase1_foundation"] == "completed":
        report["next_actions"].append("准备Phase 2核心组件集成")
    
    return report

def main():
    """主跟踪循环"""
    report_file = Path("/Volumes/1TB-M2/openclaw/workspace/gsd_v2_monitoring/progress_tracker.log")
    
    while True:
        try:
            # 加载任务状态
            tasks = load_aiplan_tasks()
            
            # 生成进度报告
            report = generate_progress_report(tasks)
            
            # 保存报告
            with open(report_file, "a") as f:
                f.write(json.dumps(report) + "\n")
            
            # 控制台输出
            print(f"[{report['timestamp']}] "
                  f"总体进度: {report['overall_progress']}% | "
                  f"Phase 1: {report['phases']['phase1_foundation']} | "
                  f"下一步: {report['next_actions'][0] if report['next_actions'] else '无'}")
            
            time.sleep(300)  # 每5分钟跟踪一次
            
        except KeyboardInterrupt:
            print("\n🛑 进度跟踪停止")
            break
        except Exception as e:
            print(f"进度跟踪错误: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
'''

        with open(tracker_script, "w") as f:
            f.write(tracker_code)

        tracker_script.chmod(0o755)

        return tracker_script

    def create_monitoring_dashboard(self):
        """创建实时监控仪表板"""
        print("📈 创建实时监控仪表板...")

        dashboard_script = self.monitor_dir / "real_time_dashboard.py"

        dashboard_code = '''#!/usr/bin/env python3
"""GSD V2 实时监控仪表板"""

import time
import json
import os
from datetime import datetime
from pathlib import Path

def clear_screen():
    """清屏"""
    os.system('clear' if os.name == 'posix' else 'cls')

def load_latest_monitor_data():
    """加载最新监控数据"""
    monitor_file = Path("/Volumes/1TB-M2/openclaw/workspace/gsd_v2_monitoring/environment_monitor.log")
    progress_file = Path("/Volumes/1TB-M2/openclaw/workspace/gsd_v2_monitoring/progress_tracker.log")
    
    data = {
        "environment": {},
        "progress": {},
        "timestamp": datetime.now().isoformat()
    }
    
    # 加载环境监控数据
    if monitor_file.exists():
        try:
            with open(monitor_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    latest_env = json.loads(lines[-1].strip())
                    data["environment"] = latest_env
        except Exception:
            pass
    
    # 加载进度数据
    if progress_file.exists():
        try:
            with open(progress_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    latest_progress = json.loads(lines[-1].strip())
                    data["progress"] = latest_progress
        except Exception:
            pass
    
    return data

def display_dashboard(data):
    """显示监控仪表板"""
    clear_screen()
    
    print("🚀 GSD V2 实时监控仪表板")
    print("=" * 60)
    print(f"更新时间: {data['timestamp']}")
    print()
    
    # 环境状态
    env = data.get("environment", {})
    print("🔍 环境状态:")
    print("-" * 30)
    
    ccr_status = env.get("claude_code", {}).get("status", "unknown")
    ccr_emoji = "✅" if ccr_status == "healthy" else "❌" if ccr_status == "unreachable" else "⚠️"
    print(f"{ccr_emoji} Claude Code Router: {ccr_status}")
    
    resources = env.get("system_resources", {})
    cpu_usage = resources.get("cpu_percent", 0)
    mem_usage = resources.get("memory_percent", 0)
    print(f"📊 系统资源: CPU {cpu_usage}% | 内存 {mem_usage}%")
    
    gsd_status = env.get("gsd_v2_status", {})
    state_machine = gsd_status.get("state_machine_status", "unknown")
    sm_emoji = "✅" if state_machine == "running" else "❌" if state_machine == "error" else "⚠️"
    print(f"{sm_emoji} 状态机: {state_machine}")
    
    print()
    
    # 进度状态
    progress = data.get("progress", {})
    overall_progress = progress.get("overall_progress", 0)
    
    print("📊 实施进度:")
    print("-" * 30)
    print(f"总体完成度: {overall_progress}%")
    
    # 进度条
    bar_length = 30
    filled = int(bar_length * overall_progress / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"[{bar}] {overall_progress}%")
    
    # 阶段状态
    phases = progress.get("phases", {})
    for phase_name, phase_status in phases.items():
        phase_emoji = "✅" if phase_status == "completed" else "🔄" if phase_status == "in_progress" else "⏳"
        print(f"{phase_emoji} {phase_name}: {phase_status}")
    
    print()
    
    # 下一步行动
    next_actions = progress.get("next_actions", [])
    if next_actions:
        print("💡 下一步行动:")
        print("-" * 30)
        for action in next_actions[:3]:  # 显示前3个行动
            print(f"• {action}")
    
    print()
    print("=" * 60)
    print("⏰ 下次更新: 30秒后... (Ctrl+C退出)")

def main():
    """主仪表板循环"""
    try:
        while True:
            data = load_latest_monitor_data()
            display_dashboard(data)
            time.sleep(30)  # 每30秒更新一次
    except KeyboardInterrupt:
        print("\n🛑 监控仪表板退出")

if __name__ == "__main__":
    main()
'''

        with open(dashboard_script, "w") as f:
            f.write(dashboard_code)

        dashboard_script.chmod(0o755)

        return dashboard_script

    def start_all_monitors(self):
        """启动所有监控组件"""
        print("🚀 启动GSD V2实施监控系统...")

        # 创建监控脚本
        env_monitor = self.start_environment_monitor()
        progress_tracker = self.start_progress_tracker()
        dashboard = self.create_monitoring_dashboard()

        # 生成启动脚本
        startup_script = self.monitor_dir / "start_monitoring_system.sh"

        startup_code = f"""#!/bin/bash
# GSD V2 监控系统启动脚本

echo "🚀 启动GSD V2监控系统..."

# 启动环境监控
echo "🔍 启动环境监控..."
python3 {env_monitor} > {self.monitor_dir}/environment_monitor.out 2>&1 &
ENV_MONITOR_PID=$!
echo "环境监控PID: $ENV_MONITOR_PID"

# 启动进度跟踪
echo "📊 启动进度跟踪..."
python3 {progress_tracker} > {self.monitor_dir}/progress_tracker.out 2>&1 &
PROGRESS_TRACKER_PID=$!
echo "进度跟踪PID: $PROGRESS_TRACKER_PID"

# 保存PID文件
echo "$ENV_MONITOR_PID" > {self.monitor_dir}/monitor_pids.txt
echo "$PROGRESS_TRACKER_PID" >> {self.monitor_dir}/monitor_pids.txt

echo ""
echo "🎉 GSD V2监控系统启动完成!"
echo ""
echo "📊 启动实时仪表板:"
echo "python3 {dashboard}"
echo ""
echo "🛑 停止监控系统:"
echo "cat {self.monitor_dir}/monitor_pids.txt | xargs kill"
"""

        with open(startup_script, "w") as f:
            f.write(startup_code)

        startup_script.chmod(0o755)

        print(f"✅ 监控系统准备完成!")
        print(f"📁 监控目录: {self.monitor_dir}")
        print(f"🚀 启动脚本: {startup_script}")
        print(f"📊 仪表板: {dashboard}")

        return startup_script


def main():
    """主函数"""
    monitor = GSDV2Monitor()
    startup_script = monitor.start_all_monitors()

    print("\n" + "=" * 60)
    print("🎉 GSD V2 环境准备工作全部完成!")
    print("=" * 60)
    print("")
    print("📋 环境准备总结:")
    print("-" * 40)
    print("✅ Claude Code Router状态检查")
    print("✅ AIplan系统集成配置")
    print("✅ GSD V2基础架构脚本准备")
    print("✅ 环境验证工具创建")
    print("✅ 实施监控机制建立")
    print("")
    print("🚀 明日Phase 1实施准备:")
    print("-" * 40)
    print("1. 验证环境: python3 scripts/gsd_v2_environment_check.py")
    print("2. 安装依赖: pip install pyyaml")
    print("3. 执行Phase 1: bash scripts/gsd_v2_phase1_setup.sh")
    print("4. 启动监控: bash {startup_script}")
    print("")
    print("📊 实时监控:")
    print("-" * 40)
    print("• 环境状态监控 (每分钟)")
    print("• 实施进度跟踪 (每5分钟)")
    print("• 实时仪表板显示")
    print("")
    print("💡 明日实施将基于此完善的环境准备基础进行!")
    print("=" * 60)


if __name__ == "__main__":
    main()
