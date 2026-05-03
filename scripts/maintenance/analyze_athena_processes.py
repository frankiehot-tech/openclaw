#!/usr/bin/env python3
"""
分析Athena相关进程分类
确定40个Athena进程的身份和类型
"""

import sys
import time
from datetime import datetime

import psutil


def categorize_athena_processes():
    """分类Athena相关进程"""
    print("🔍 分析Athena相关进程分类...")

    process_categories = {
        "queue_runner": [],
        "web_server": [],
        "monitor_dashboard": [],
        "other_athena": [],
        "unknown": [],
    }

    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline", "status", "create_time"]):
            try:
                cmdline = proc.info["cmdline"]
                if not cmdline:
                    continue

                cmdline_str = " ".join(cmdline).lower()

                # 检查是否为Athena相关进程
                is_athena = any(
                    keyword in cmdline_str
                    for keyword in ["athena", "openclaw", "claude", "openhuman", "gsd"]
                )

                if not is_athena:
                    continue

                pid = proc.info["pid"]
                name = proc.info["name"]
                status = proc.info["status"]
                create_time = proc.info["create_time"]

                # 分类逻辑
                if "athena_ai_plan_runner.py" in cmdline_str:
                    category = "queue_runner"
                elif "flask" in cmdline_str or "web" in cmdline_str or "server" in cmdline_str:
                    category = "web_server"
                elif "dashboard" in cmdline_str or "monitor" in cmdline_str:
                    category = "monitor_dashboard"
                elif any(keyword in cmdline_str for keyword in ["run", "task", "build", "exec"]):
                    category = "other_athena"
                else:
                    category = "unknown"

                # 进程年龄计算
                age_seconds = time.time() - create_time if create_time else 0
                age_minutes = age_seconds / 60

                process_info = {
                    "pid": pid,
                    "name": name,
                    "cmdline_short": " ".join(cmdline[:3]) + ("..." if len(cmdline) > 3 else ""),
                    "status": status,
                    "age_minutes": round(age_minutes, 2),
                    "category": category,
                    "full_cmdline": cmdline,
                }

                process_categories[category].append(process_info)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                print(f"   处理进程异常: {e}")
                continue

    except Exception as e:
        print(f"   枚举进程失败: {e}")

    return process_categories


def print_category_report(process_categories):
    """打印分类报告"""
    print("\n" + "=" * 60)
    print("📊 Athena进程分类报告")
    print("=" * 60)

    total_processes = sum(len(procs) for procs in process_categories.values())
    print(f"总Athena进程数: {total_processes}")

    for category, processes in process_categories.items():
        print(f"\n{category.upper()} 类别: {len(processes)}个进程")

        if processes:
            for proc in processes[:5]:  # 只显示前5个
                print(
                    f"  PID:{proc['pid']} | {proc['status']} | {proc['age_minutes']}分钟 | {proc['cmdline_short']}"
                )

            if len(processes) > 5:
                print(f"  ... 还有{len(processes) - 5}个进程")

    # 特别关注队列运行器
    queue_runners = process_categories["queue_runner"]
    if queue_runners:
        print(f"\n✅ 发现 {len(queue_runners)} 个队列运行器进程:")
        for proc in queue_runners:
            print(f"  PID:{proc['pid']} - {proc['cmdline_short']}")
    else:
        print("\n⚠️ 未发现队列运行器进程")

    # 检查是否有僵尸进程
    zombie_count = 0
    for _category, processes in process_categories.items():
        for proc in processes:
            if proc["status"] == psutil.STATUS_ZOMBIE:
                zombie_count += 1

    if zombie_count > 0:
        print(f"\n⚠️ 发现 {zombie_count} 个僵尸进程")

    return total_processes


def check_process_health():
    """检查进程健康状态"""
    print("\n" + "=" * 60)
    print("❤️ 进程健康检查")
    print("=" * 60)

    try:
        # 检查队列运行器心跳
        from contracts.process_lifecycle import ProcessContract

        print("检查ProcessLifecycleContract健康状态...")

        # 测试进程契约
        test_command = "echo 'ProcessContract健康检查' && sleep 1"
        contract = ProcessContract(
            command=test_command, env={"TEST_ENV": "true"}, heartbeat_interval=30
        )

        success, pid, error = contract.spawn()

        if success and pid:
            print(f"✅ ProcessContract健康检查通过: PID={pid}")

            # 快速健康检查
            time.sleep(0.5)
            health = contract.monitor(pid)
            print(f"   进程健康状态: {health}")

            # 清理测试进程
            try:
                if psutil.pid_exists(pid):
                    psutil.Process(pid).terminate()
            except Exception:
                pass
        else:
            print(f"⚠️ ProcessContract健康检查警告: {error}")

    except ImportError as e:
        print(f"❌ 无法导入ProcessLifecycleContract: {e}")
    except Exception as e:
        print(f"❌ 进程健康检查异常: {e}")


def main():
    """主函数"""
    print("🚀 Athena进程分类分析开始")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 分类进程
    process_categories = categorize_athena_processes()

    # 2. 打印报告
    total_processes = print_category_report(process_categories)

    # 3. 进程健康检查
    check_process_health()

    # 4. 结论
    print("\n" + "=" * 60)
    print("🎯 分析结论")
    print("=" * 60)

    if total_processes == 0:
        print("❌ 未找到Athena相关进程")
        return 1
    elif total_processes == 40:
        print("✅ 确认找到40个Athena相关进程")

        queue_runners = len(process_categories["queue_runner"])
        if queue_runners == 0:
            print(f"⚠️ 队列中没有运行中的任务，但有{total_processes}个Athena进程")
            print("   这可能包括:")
            print(f"   - Web服务器进程: {len(process_categories['web_server'])}个")
            print(f"   - 监控仪表板进程: {len(process_categories['monitor_dashboard'])}个")
            print(f"   - 其他Athena进程: {len(process_categories['other_athena'])}个")
            print(f"   - 未知进程: {len(process_categories['unknown'])}个")
            print("\n   如果队列运行器进程为0，说明队列可能已停止或没有任务在执行")
        else:
            print(f"✅ 发现{queue_runners}个队列运行器进程")
            print("   队列状态正常，进程包括:")
            for category, count in [
                (cat, len(procs)) for cat, procs in process_categories.items() if procs
            ]:
                print(f"   - {category}: {count}个进程")

    else:
        print(f"⚠️ 找到{total_processes}个Athena进程（非预期的40个）")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 分析脚本异常: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(3)
