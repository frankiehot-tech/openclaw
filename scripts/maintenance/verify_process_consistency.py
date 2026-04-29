#!/usr/bin/env python3
"""
进程状态一致性验证脚本
验证队列文件中的进程状态与实际运行进程的一致性
确保ProcessLifecycleContract正常工作
"""

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import psutil

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config.paths import PLAN_QUEUE_DIR, ROOT_DIR, SCRIPTS_DIR

    QUEUE_DIR = Path(PLAN_QUEUE_DIR)
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    ROOT_DIR = Path("/Volumes/1TB-M2/openclaw")
    QUEUE_DIR = ROOT_DIR / ".openclaw" / "plan_queue"
    SCRIPTS_DIR = ROOT_DIR / "scripts"


def check_queue_processes():
    """检查队列文件中的进程状态"""
    queue_dir = QUEUE_DIR

    if not queue_dir.exists():
        print("❌ 队列目录不存在:", queue_dir)
        return []

    queue_files = list(queue_dir.glob("*.json"))
    print(f"📊 找到 {len(queue_files)} 个队列文件")

    all_processes = []

    for queue_file in queue_files[:5]:  # 限制检查前5个文件以避免过多输出
        print(f"\n📄 检查队列: {queue_file.name}")

        try:
            with open(queue_file, encoding="utf-8") as f:
                data = json.load(f)

            queue_id = data.get("queue_id", "unknown")
            items = data.get("items", {})

            # 处理items（可能是列表或字典）
            if isinstance(items, list):
                items_dict = {}
                for idx, item in enumerate(items):
                    if isinstance(item, dict):
                        item_id = item.get("id", f"item_{idx}")
                        items_dict[item_id] = item
            else:
                items_dict = items

            running_count = 0
            for item_id, item in items_dict.items():
                status = item.get("status", "unknown")
                runner_pid = item.get("runner_pid")
                runner_heartbeat_at = item.get("runner_heartbeat_at")

                if runner_pid and status == "running":
                    running_count += 1

                    # 检查进程是否存在
                    try:
                        pid_exists = psutil.pid_exists(runner_pid)
                    except Exception:
                        pid_exists = False

                    # 检查心跳时间
                    heartbeat_age = None
                    if runner_heartbeat_at:
                        try:
                            heartbeat_time = datetime.fromisoformat(
                                runner_heartbeat_at.replace("Z", "+00:00")
                            )
                            if heartbeat_time.tzinfo is None:
                                heartbeat_time = heartbeat_time.replace(tzinfo=UTC)

                            now = datetime.now(UTC)
                            heartbeat_age = (now - heartbeat_time).total_seconds()
                        except Exception:
                            heartbeat_age = float("inf")

                    process_info = {
                        "queue_id": queue_id,
                        "queue_file": queue_file.name,
                        "item_id": item_id,
                        "status": status,
                        "runner_pid": runner_pid,
                        "pid_exists": pid_exists,
                        "heartbeat_at": runner_heartbeat_at,
                        "heartbeat_age_seconds": heartbeat_age,
                        "item_data": item,
                    }

                    all_processes.append(process_info)

            print(f"   队列状态: {data.get('queue_status', 'unknown')}")
            print(f"   运行中任务: {running_count}/{len(items_dict)}")

        except Exception as e:
            print(f"❌ 解析队列文件失败: {e}")

    return all_processes


def verify_process_lifecycle_contract():
    """验证ProcessLifecycleContract功能"""
    print("\n🔧 验证ProcessLifecycleContract...")

    try:
        from contracts.process_lifecycle import ProcessContract

        # 创建一个简单的测试进程
        test_command = "echo 'ProcessContract测试' && sleep 2"

        contract = ProcessContract(
            command=test_command,
            env={"TEST_ENV": "true"},
            heartbeat_interval=5,  # 测试用短间隔
        )

        print("   测试进程启动...")
        success, pid, error = contract.spawn()

        if success and pid:
            print(f"   ✅ 进程启动成功: PID={pid}")

            # 检查进程状态
            time.sleep(0.5)
            try:
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    print(f"   ✅ 进程存在: PID={pid}, 状态={process.status()}")

                    # 等待进程结束
                    time.sleep(2.5)

                    if not psutil.pid_exists(pid):
                        print("   ✅ 进程正常退出")
                    else:
                        print("   ⚠️ 进程仍在运行")
                        process.terminate()
                else:
                    print("   ❌ 进程不存在")
            except Exception as e:
                print(f"   ❌ 检查进程状态失败: {e}")

            return True, pid
        else:
            print(f"   ❌ 进程启动失败: {error}")
            return False, None

    except ImportError as e:
        print(f"   ❌ 导入ProcessLifecycleContract失败: {e}")
        return False, None
    except Exception as e:
        print(f"   ❌ ProcessLifecycleContract验证失败: {e}")
        return False, None


def check_actual_processes():
    """检查实际运行的Athena相关进程"""
    print("\n🔍 检查实际运行的Athena进程...")

    athena_processes = []

    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline", "status", "create_time"]):
            try:
                cmdline = proc.info["cmdline"]
                if cmdline and len(cmdline) > 1:
                    # 检查是否为Athena相关进程
                    is_athena = (
                        any("athena" in str(arg).lower() for arg in cmdline)
                        or any("opencode" in str(arg).lower() for arg in cmdline)
                        or any("claude" in str(arg).lower() for arg in cmdline)
                    )

                    if is_athena:
                        create_time = proc.info["create_time"]
                        age_seconds = time.time() - create_time
                        age_minutes = age_seconds / 60

                        process_info = {
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "cmdline_short": " ".join(cmdline[:3])
                            + ("..." if len(cmdline) > 3 else ""),
                            "status": proc.info["status"],
                            "age_minutes": round(age_minutes, 2),
                            "create_time": (
                                datetime.fromtimestamp(create_time).isoformat()
                                if create_time
                                else None
                            ),
                        }

                        athena_processes.append(process_info)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    except Exception as e:
        print(f"   检查进程失败: {e}")

    print(f"   找到 {len(athena_processes)} 个Athena相关进程")

    if athena_processes:
        print("   进程列表:")
        for proc in athena_processes[:10]:  # 只显示前10个
            print(f"     PID:{proc['pid']} | {proc['status']} | {proc['cmdline_short']}")

    return athena_processes


def generate_consistency_report(queue_processes, actual_processes, contract_ok):
    """生成一致性报告"""
    print("\n" + "=" * 60)
    print("📋 进程状态一致性报告")
    print("=" * 60)

    # 统计信息
    total_queue_processes = len(queue_processes)
    {p["pid"] for p in actual_processes}

    # 检查队列进程的实际存在性
    existing_count = sum(1 for p in queue_processes if p["pid_exists"])
    missing_count = total_queue_processes - existing_count

    # 检查心跳状态
    stale_heartbeats = 0
    for proc in queue_processes:
        if (
            proc["heartbeat_age_seconds"] is not None and proc["heartbeat_age_seconds"] > 300
        ):  # 5分钟
            stale_heartbeats += 1

    print(f"队列中标记为running的任务: {total_queue_processes}")
    print(f"实际存在的进程: {existing_count}")
    print(f"缺失的进程: {missing_count}")
    print(f"陈旧心跳(>5分钟): {stale_heartbeats}")
    print(f"ProcessLifecycleContract状态: {'✅ 正常' if contract_ok else '❌ 异常'}")

    # 详细检查
    if missing_count > 0:
        print("\n⚠️ 缺失的进程:")
        for proc in queue_processes:
            if not proc["pid_exists"]:
                print(
                    f"   队列: {proc['queue_id']}, 任务: {proc['item_id']}, PID: {proc['runner_pid']}"
                )

    # 检查是否有僵尸进程
    zombie_count = sum(1 for p in actual_processes if p["status"] == psutil.STATUS_ZOMBIE)
    if zombie_count > 0:
        print(f"\n⚠️ 发现 {zombie_count} 个僵尸进程")
        for proc in actual_processes:
            if proc["status"] == psutil.STATUS_ZOMBIE:
                print(f"   PID:{proc['pid']} - {proc['cmdline_short']}")

    # 一致性评估
    print("\n" + "=" * 60)
    print("🎯 一致性评估")
    print("=" * 60)

    consistency_score = 0

    if existing_count == total_queue_processes and total_queue_processes > 0:
        consistency_score += 40
        print("✅ 所有队列进程都实际存在 (+40分)")
    elif existing_count > 0:
        consistency_score += 20
        print(f"⚠️ 部分进程存在 {existing_count}/{total_queue_processes} (+20分)")
    else:
        print("❌ 没有队列进程实际存在 (0分)")

    if stale_heartbeats == 0:
        consistency_score += 30
        print("✅ 没有陈旧心跳 (+30分)")
    else:
        consistency_score += 10
        print(f"⚠️ 有 {stale_heartbeats} 个陈旧心跳 (+10分)")

    if contract_ok:
        consistency_score += 30
        print("✅ ProcessLifecycleContract工作正常 (+30分)")
    else:
        print("❌ ProcessLifecycleContract异常 (0分)")

    if zombie_count == 0:
        consistency_score += 10
        print("✅ 没有僵尸进程 (+10分)")
    else:
        print(f"⚠️ 有 {zombie_count} 个僵尸进程 (0分)")

    print(f"\n📈 一致性总分: {consistency_score}/110")

    if consistency_score >= 90:
        print("✅ 进程状态一致性: 优秀")
    elif consistency_score >= 70:
        print("⚠️ 进程状态一致性: 良好")
    elif consistency_score >= 50:
        print("⚠️ 进程状态一致性: 需要改进")
    else:
        print("❌ 进程状态一致性: 差")

    return consistency_score


def main():
    """主函数"""
    print("🚀 开始进程状态一致性验证")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 检查队列中的进程
    queue_processes = check_queue_processes()

    # 2. 检查实际进程
    actual_processes = check_actual_processes()

    # 3. 验证ProcessLifecycleContract
    contract_ok, _ = verify_process_lifecycle_contract()

    # 4. 生成报告
    consistency_score = generate_consistency_report(queue_processes, actual_processes, contract_ok)

    # 5. 建议
    print("\n" + "=" * 60)
    print("💡 建议")
    print("=" * 60)

    if consistency_score < 70:
        print("1. 检查队列运行器(athena_ai_plan_runner.py)是否正常运行")
        print("2. 验证ProcessLifecycleContract集成是否正确")
        print("3. 检查心跳检测机制，确保runner_heartbeat_at字段正确更新")
        print("4. 清理僵尸进程和缺失的进程条目")

    # 6. 退出码
    if consistency_score >= 80:
        print("\n✅ 验证通过: 进程状态一致性良好")
        return 0
    elif consistency_score >= 60:
        print("\n⚠️ 验证警告: 进程状态一致性需要关注")
        return 1
    else:
        print("\n❌ 验证失败: 进程状态一致性差")
        return 2


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 验证脚本异常: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(3)
