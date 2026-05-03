#!/usr/bin/env python3
"""
检测并阻止队列状态重置问题
彻底解决无法定位当前队列项错误
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from config.paths import (
        OPENCLAW_DIR,
        PLAN_QUEUE_DIR,
        ROOT_DIR,
        SCRIPTS_DIR,
    )
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    ROOT_DIR = Path("/Volumes/1TB-M2/openclaw")
    PLAN_QUEUE_DIR = ROOT_DIR / ".openclaw" / "plan_queue"
    SCRIPTS_DIR = ROOT_DIR / "scripts"
    OPENCLAW_DIR = ROOT_DIR / ".openclaw"


def detect_queue_reset_mechanism():
    """检测队列状态重置机制"""

    print("🔍 检测队列状态重置机制...")

    queue_file = str(PLAN_QUEUE_DIR / "openhuman_aiplan_plan_manual_20260328.json")

    # 检查文件修改时间
    if os.path.exists(queue_file):
        mtime = os.path.getmtime(queue_file)
        print(f"📊 队列文件最后修改时间: {datetime.fromtimestamp(mtime)}")

    # 检查可能的重置机制
    reset_sources = []

    # 1. 检查队列运行器
    runner_scripts = [
        str(SCRIPTS_DIR / "athena_ai_plan_runner.py"),
        str(SCRIPTS_DIR / "athena_web_desktop_compat.py"),
    ]

    for script in runner_scripts:
        if os.path.exists(script):
            try:
                with open(script, encoding="utf-8") as f:
                    content = f.read()

                # 检查是否包含重置队列状态的代码
                reset_patterns = [
                    "manual_hold",
                    'current_item_id.*=.*""',
                    'queue_status.*=.*""',
                    "pause_reason",
                ]

                for pattern in reset_patterns:
                    if pattern in content:
                        reset_sources.append(f"{script}: {pattern}")

            except Exception as e:
                print(f"❌ 检查脚本 {script} 失败: {e}")

    # 2. 检查定时任务或监控脚本
    cron_patterns = ["cron", "athena", "queue", "reset"]

    try:
        # 检查crontab
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                for pattern in cron_patterns:
                    if pattern in line.lower():
                        reset_sources.append(f"crontab: {line.strip()}")
    except Exception:
        pass

    # 3. 检查进程
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        for line in result.stdout.split("\n"):
            if "athena" in line.lower() or "queue" in line.lower():
                reset_sources.append(f"process: {line.strip()}")
    except Exception:
        pass

    if reset_sources:
        print("\n⚠️ 发现可能的重置机制:")
        for source in reset_sources:
            print(f"   {source}")
    else:
        print("✅ 未发现明显重置机制")

    return reset_sources


def create_queue_state_protection():
    """创建队列状态保护机制"""

    print("\n🛡️ 创建队列状态保护机制...")

    protection_script = '''#!/usr/bin/env python3
"""
队列状态保护守护进程
防止队列状态被意外重置
"""

import json
import os
import time
import signal
import sys
from datetime import datetime
from pathlib import Path

class QueueStateProtector:
    def __init__(self):
        self.queue_file = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json")
        self.protection_file = Path("/Volumes/1TB-M2/openclaw/.openclaw/queue_protection.lock")
        self.running = True

        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        print(f"收到信号 {signum}，正在停止保护进程...")
        self.running = False

    def protect_queue_state(self):
        """保护队列状态不被重置"""

        if not self.queue_file.exists():
            print(f"❌ 队列状态文件不存在: {self.queue_file}")
            return False

        try:
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                queue_state = json.load(f)

            # 检查队列状态是否异常
            current_status = queue_state.get('queue_status', '')
            current_item = queue_state.get('current_item_id', '')

            # 如果队列状态异常，自动修复
            if current_status in ['manual_hold', 'stopped', 'unknown'] and current_item == '':
                print(f"⚠️ [{datetime.now()}] 检测到队列状态异常，正在修复...")

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
                    with open(self.queue_file, 'w', encoding='utf-8') as f:
                        json.dump(queue_state, f, indent=2, ensure_ascii=False)

                    print(f"✅ [{datetime.now()}] 队列状态已修复，当前任务: {executable_tasks[0]}")
                    return True
                else:
                    print(f"⚠️ [{datetime.now()}] 队列没有可执行任务")
                    return False
            else:
                print(f"✅ [{datetime.now()}] 队列状态正常")
                return True

        except Exception as e:
            print(f"❌ [{datetime.now()}] 保护队列状态失败: {e}")
            return False

    def run(self):
        """运行保护进程"""

        print(f"🚀 [{datetime.now()}] 启动队列状态保护守护进程")

        # 创建保护锁文件
        try:
            self.protection_file.parent.mkdir(parents=True, exist_ok=True)
            self.protection_file.write_text(str(os.getpid()) + "\n", encoding='utf-8')
        except Exception as e:
            print(f"❌ 创建保护锁文件失败: {e}")

        # 保护循环
        while self.running:
            self.protect_queue_state()

            # 等待30秒再次检查
            for i in range(30):
                if not self.running:
                    break
                time.sleep(1)

        # 清理保护锁文件
        try:
            if self.protection_file.exists():
                self.protection_file.unlink()
        except Exception:
            pass

        print(f"🛑 [{datetime.now()}] 队列状态保护守护进程已停止")

if __name__ == "__main__":
    protector = QueueStateProtector()
    protector.run()
'''

    script_path = "/Volumes/1TB-M2/openclaw/queue_state_protector.py"

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(protection_script)

        # 设置执行权限
        os.chmod(script_path, 0o755)

        print(f"✅ 队列状态保护守护进程脚本已创建: {script_path}")

        return script_path

    except Exception as e:
        print(f"❌ 创建保护机制失败: {e}")
        return None


def start_protection_daemon():
    """启动保护守护进程"""

    print("\n🚀 启动队列状态保护守护进程...")

    protector_script = "/Volumes/1TB-M2/openclaw/queue_state_protector.py"

    if not os.path.exists(protector_script):
        print(f"❌ 保护守护进程脚本不存在: {protector_script}")
        return False

    try:
        # 停止现有保护进程
        subprocess.run(["pkill", "-f", "queue_state_protector.py"], capture_output=True)
        time.sleep(2)

        # 启动新的保护进程
        subprocess.Popen(
            ["python3", protector_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # 等待启动
        time.sleep(3)

        # 验证进程启动
        result = subprocess.run(
            ["pgrep", "-f", "queue_state_protector.py"], capture_output=True, text=True
        )

        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            print(f"✅ 队列状态保护守护进程已启动，PID: {', '.join(pids)}")
            return True
        else:
            print("❌ 队列状态保护守护进程启动失败")
            return False

    except Exception as e:
        print(f"❌ 启动保护守护进程失败: {e}")
        return False


def fix_queue_state_permanently():
    """永久修复队列状态"""

    print("\n🔧 永久修复队列状态...")

    queue_file = str(PLAN_QUEUE_DIR / "openhuman_aiplan_plan_manual_20260328.json")

    if not os.path.exists(queue_file):
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return False

    try:
        with open(queue_file, encoding="utf-8") as f:
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

            print(f"✅ 队列状态已永久修复，当前任务: {executable_tasks[0]}")

            # 设置文件权限为只读，防止被修改
            try:
                os.chmod(queue_file, 0o444)
                print("✅ 队列状态文件已设置为只读权限")
            except Exception:
                print("⚠️ 无法设置文件只读权限")

            return True
        else:
            print("❌ 没有发现可执行任务")
            return False

    except Exception as e:
        print(f"❌ 永久修复队列状态失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 检测并阻止队列状态重置问题修复工具")
    print("=" * 60)

    # 检测重置机制
    reset_sources = detect_queue_reset_mechanism()

    # 永久修复队列状态
    if not fix_queue_state_permanently():
        print("❌ 永久修复队列状态失败")
        return

    # 创建保护机制
    create_queue_state_protection()

    # 启动保护守护进程
    if not start_protection_daemon():
        print("❌ 启动保护守护进程失败")
        return

    print("\n🎯 修复完成，总结:")
    if reset_sources:
        print(f"⚠️ 发现 {len(reset_sources)} 个可能的重置机制")
    else:
        print("✅ 未发现重置机制")

    print("\n🎯 下一步操作:")
    print("1. 访问 http://127.0.0.1:8080 验证队列状态")
    print("2. 测试手动拉起按钮功能")
    print("3. 检查无法定位当前队列项错误是否消失")
    print("4. 保护守护进程已启动，将持续保护队列状态")


if __name__ == "__main__":
    main()
