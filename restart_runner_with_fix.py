#!/usr/bin/env python3
"""
重启队列运行器并修复队列状态
1. 停止队列运行器进程
2. 强制更新queue_status为running
3. 重新启动队列运行器
4. 验证修复成功
"""

import json
import os
import signal
import subprocess
import sys
import time

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)
RUNNER_SCRIPT = "/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"
RUNNER_ARGS = ["--queue", "../.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"]


def find_runner_pid():
    """查找队列运行器进程ID"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "athena_ai_plan_runner.py"], capture_output=True, text=True
        )
        if result.stdout:
            pids = result.stdout.strip().split()
            return [int(pid) for pid in pids]
    except Exception as e:
        print(f"查找进程时出错: {e}")
    return []


def stop_runner(pids):
    """停止队列运行器进程"""
    if not pids:
        print("未找到运行器进程")
        return True

    print(f"停止运行器进程: {pids}")
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"已发送SIGTERM到PID {pid}")
        except ProcessLookupError:
            print(f"进程 {pid} 已不存在")
        except Exception as e:
            print(f"停止进程 {pid} 时出错: {e}")
            return False

    # 等待进程退出
    for _ in range(10):
        time.sleep(0.5)
        remaining = find_runner_pid()
        if not remaining:
            print("运行器已停止")
            return True
        print(f"等待进程退出... 剩余: {remaining}")

    print("警告: 进程未完全退出，尝试强制终止")
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except:
            pass
    time.sleep(1)
    return True


def update_queue_status():
    """更新队列状态为running"""
    print("更新队列状态...")

    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        old_status = data.get("queue_status", "unknown")
        print(f"当前queue_status: {old_status}")

        # 强制更新
        data["queue_status"] = "running"
        data["pause_reason"] = ""

        # 确保有当前任务
        if not data.get("current_item_id"):
            items = data.get("items", {})
            pending = [tid for tid, task in items.items() if task.get("status") == "pending"]
            if pending:
                data["current_item_id"] = pending[0]
                print(f"设置当前任务: {data['current_item_id']}")

        # 备份原文件
        backup = f"{QUEUE_FILE}.restart_backup"
        if os.path.exists(QUEUE_FILE) and not os.path.exists(backup):
            import shutil

            shutil.copy2(QUEUE_FILE, backup)
            print(f"备份: {backup}")

        # 写入新文件
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"已更新queue_status: {old_status} -> running")

        # 验证
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)

        if saved.get("queue_status") == "running":
            print("✅ 队列状态更新验证成功")
            return True
        else:
            print(f"❌ 队列状态更新失败: {saved.get('queue_status')}")
            return False

    except Exception as e:
        print(f"更新队列状态时出错: {e}")
        import traceback

        traceback.print_exc()
        return False


def start_runner():
    """启动队列运行器"""
    print("启动队列运行器...")

    try:
        # 切换到脚本目录
        script_dir = os.path.dirname(RUNNER_SCRIPT)
        os.chdir(script_dir)

        # 在后台启动运行器
        cmd = ["python3", "athena_ai_plan_runner.py"] + RUNNER_ARGS
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
        )

        print(f"启动运行器，PID: {process.pid}")
        print(f"命令: {' '.join(cmd)}")

        # 等待一会儿检查进程是否存活
        time.sleep(2)
        if process.poll() is None:
            print("✅ 队列运行器启动成功")
            return process.pid
        else:
            stdout, stderr = process.communicate(timeout=1)
            print(f"❌ 队列运行器启动失败")
            print(f"stdout: {stdout.decode('utf-8', errors='ignore')[:200]}")
            print(f"stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")
            return None

    except Exception as e:
        print(f"启动运行器时出错: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    print("=" * 60)
    print("🔄 重启队列运行器并修复队列状态")
    print("=" * 60)

    # 1. 查找并停止运行器
    pids = find_runner_pid()
    if not stop_runner(pids):
        print("❌ 无法停止运行器，中止")
        sys.exit(1)

    # 2. 更新队列状态
    if not update_queue_status():
        print("❌ 队列状态更新失败，中止")
        sys.exit(1)

    # 3. 重新启动运行器
    new_pid = start_runner()
    if not new_pid:
        print("❌ 运行器启动失败")
        sys.exit(1)

    # 4. 最终验证
    time.sleep(3)
    print("\n🔍 最终验证...")

    # 检查运行器是否在运行
    current_pids = find_runner_pid()
    if current_pids:
        print(f"✅ 队列运行器正在运行: PIDs {current_pids}")
    else:
        print("❌ 队列运行器未运行")

    # 检查队列状态
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        status = data.get("queue_status", "unknown")
        if status == "running":
            print(f"✅ 队列状态为: {status}")
        else:
            print(f"⚠️  队列状态为: {status} (期望: running)")
    except Exception as e:
        print(f"❌ 检查队列状态时出错: {e}")

    print("\n" + "=" * 60)
    print("🎉 重启与修复完成")
    print("=" * 60)
    print("\n📋 后续步骤:")
    print("  1. 检查队列任务是否开始执行")
    print("  2. 监控系统资源使用")
    print("  3. 观察24小时监控验证")
    print("  4. 完善运维文档和告警配置")


if __name__ == "__main__":
    main()
