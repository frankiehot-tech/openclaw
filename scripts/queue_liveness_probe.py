#!/usr/bin/env python3
"""
队列活性探针脚本 - 用于检查所有plan_queue的活性和心跳机制
实现实施方案中的1.1.3任务
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

# 配置
PLAN_QUEUE_DIR = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue"
HEARTBEAT_THRESHOLD_MINUTES = 1  # 心跳超过1分钟视为异常（从5分钟优化到1分钟，与ProcessLifecycleContract的30秒心跳检测保持一致）
RUNNER_PROCESS_NAME = "athena_ai_plan_runner.py"


def check_runner_process():
    """检查athena_ai_plan_runner进程状态"""
    print("🔍 检查Runner进程状态...")

    try:
        # 使用pgrep检查进程
        result = subprocess.run(
            ["pgrep", "-f", RUNNER_PROCESS_NAME], capture_output=True, text=True
        )

        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            print(f"✅ Runner进程正在运行，PID(s): {', '.join(pids)}")

            # 获取详细进程信息
            for pid in pids:
                if pid:
                    try:
                        proc_info = subprocess.run(
                            ["ps", "-p", pid, "-o", "pid,time,command"],
                            capture_output=True,
                            text=True,
                        )
                        print(
                            f"  进程 {pid}: {proc_info.stdout.strip().split('\n')[-1] if len(proc_info.stdout.strip().split('\n')) > 1 else '无信息'}"
                        )
                    except Exception as e:
                        print(f"  获取进程{pid}信息失败: {e}")

            return True, len([p for p in pids if p])
        else:
            print("❌ Runner进程未运行")
            return False, 0

    except Exception as e:
        print(f"❌ 检查Runner进程失败: {e}")
        return False, 0


def check_queue_files():
    """检查所有队列文件的状态和心跳"""
    print(f"\n🔍 检查队列目录: {PLAN_QUEUE_DIR}")

    if not os.path.exists(PLAN_QUEUE_DIR):
        print(f"❌ 队列目录不存在: {PLAN_QUEUE_DIR}")
        return []

    queue_files = [f for f in os.listdir(PLAN_QUEUE_DIR) if f.endswith(".json")]
    print(f"📊 找到 {len(queue_files)} 个队列文件")

    results = []
    now = datetime.now(timezone.utc)

    for queue_file in queue_files:
        file_path = os.path.join(PLAN_QUEUE_DIR, queue_file)
        print(f"\n📄 检查队列: {queue_file}")

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # 检查队列状态
            queue_status = data.get("queue_status", "unknown")
            pause_reason = data.get("pause_reason", "")
            updated_at = data.get("updated_at", "")

            print(f"   状态: {queue_status} | 暂停原因: {pause_reason}")
            print(f"   最后更新: {updated_at}")

            # 检查队列中的任务状态 - 支持字典和列表两种格式
            raw_items = data.get("items", {})

            # 将items转换为字典格式处理
            items_dict = {}
            if isinstance(raw_items, list):
                # 列表格式: 每个元素是字典，使用'id'字段作为键
                for item in raw_items:
                    if isinstance(item, dict):
                        item_id = item.get("id", "")
                        if item_id:
                            items_dict[item_id] = item
                        else:
                            # 如果没有id字段，生成一个临时ID
                            items_dict[f"item_{len(items_dict)}"] = item
            elif isinstance(raw_items, dict):
                items_dict = raw_items
            else:
                print(f"   ⚠️  items字段格式无效: {type(raw_items)}")
                items_dict = {}

            status_counts = {
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "manual_hold": 0,
            }

            all_heartbeats_valid = True
            stale_heartbeats = []

            for item_id, item in items_dict.items():
                status = item.get("status", "unknown")
                if status in status_counts:
                    status_counts[status] += 1

                # 只检查running状态任务的心跳，completed/failed任务不需要心跳检测
                if status == "running":
                    heartbeat_at = item.get("runner_heartbeat_at", "")
                    runner_pid = item.get("runner_pid", "")

                    if heartbeat_at and runner_pid:
                        try:
                            # 解析时间戳
                            heartbeat_time = datetime.fromisoformat(
                                heartbeat_at.replace("Z", "+00:00")
                            )
                            if heartbeat_time.tzinfo is None:
                                heartbeat_time = heartbeat_time.replace(tzinfo=timezone.utc)

                            age_minutes = (now - heartbeat_time).total_seconds() / 60

                            if age_minutes > HEARTBEAT_THRESHOLD_MINUTES:
                                stale_heartbeats.append(
                                    {
                                        "item_id": item_id,
                                        "heartbeat_age_minutes": round(age_minutes, 1),
                                        "runner_pid": runner_pid,
                                    }
                                )
                                all_heartbeats_valid = False

                        except Exception as e:
                            print(f"   任务 {item_id}: 心跳时间解析失败: {e}")
                            all_heartbeats_valid = False
                    elif runner_pid:  # running状态但没有心跳，也视为异常
                        stale_heartbeats.append(
                            {
                                "item_id": item_id,
                                "heartbeat_age_minutes": float("inf"),
                                "runner_pid": runner_pid,
                            }
                        )
                        all_heartbeats_valid = False

            # 打印状态统计
            print(
                f"   任务统计: Pending: {status_counts['pending']}, Running: {status_counts['running']}, "
                f"Completed: {status_counts['completed']}, Failed: {status_counts['failed']}, "
                f"Manual Hold: {status_counts['manual_hold']}"
            )

            # 检查是否有陈旧的心跳
            if stale_heartbeats:
                print(f"   ⚠️  发现 {len(stale_heartbeats)} 个陈旧心跳:")
                for stale in stale_heartbeats:
                    print(
                        f"     任务 {stale['item_id']}: 心跳已过期 {stale['heartbeat_age_minutes']} 分钟, PID: {stale['runner_pid']}"
                    )

            # 检查自动重试计数
            for item_id, item in items_dict.items():
                auto_retry_count = item.get("auto_retry_count", 0)
                if auto_retry_count > 0:
                    print(f"   🔄 任务 {item_id}: 自动重试 {auto_retry_count} 次")

            results.append(
                {
                    "queue_file": queue_file,
                    "queue_status": queue_status,
                    "all_heartbeats_valid": all_heartbeats_valid,
                    "stale_heartbeat_count": len(stale_heartbeats),
                    "status_counts": status_counts,
                    "total_items": len(items_dict),
                }
            )

        except Exception as e:
            print(f"❌ 解析队列文件失败: {e}")
            results.append({"queue_file": queue_file, "error": str(e)})

    return results


def generate_summary_report(runner_ok, runner_count, queue_results):
    """生成汇总报告"""
    print("\n" + "=" * 60)
    print("📋 队列活性探针汇总报告")
    print("=" * 60)

    # Runner状态
    runner_status = "✅ 正常" if runner_ok else "❌ 异常"
    print(f"Runner进程状态: {runner_status} (共 {runner_count} 个进程)")

    # 队列状态汇总
    total_queues = len(queue_results)
    healthy_queues = sum(
        1 for r in queue_results if "all_heartbeats_valid" in r and r["all_heartbeats_valid"]
    )
    total_stale_heartbeats = sum(
        r.get("stale_heartbeat_count", 0) for r in queue_results if "stale_heartbeat_count" in r
    )
    total_items = sum(r.get("total_items", 0) for r in queue_results if "total_items" in r)

    print(f"\n队列健康状态: {healthy_queues}/{total_queues} 个队列心跳正常")
    print(f"陈旧心跳总数: {total_stale_heartbeats}")
    print(f"总任务数: {total_items}")

    # 详细队列状态
    for result in queue_results:
        if "error" in result:
            print(f"\n队列 {result['queue_file']}: ❌ 错误 - {result['error']}")
        else:
            heartbeat_status = (
                "✅ 正常"
                if result["all_heartbeats_valid"]
                else f"⚠️  异常 ({result['stale_heartbeat_count']} 个陈旧心跳)"
            )
            print(
                f"\n队列 {result['queue_file']}: {result['queue_status']} | 心跳: {heartbeat_status}"
            )
            counts = result["status_counts"]
            print(
                f"  任务状态: Pending: {counts['pending']}, Running: {counts['running']}, "
                f"Completed: {counts['completed']}, Failed: {counts['failed']}, "
                f"Manual Hold: {counts['manual_hold']}"
            )

    # 系统可用性评估
    print("\n" + "=" * 60)
    print("🎯 系统可用性评估")
    print("=" * 60)

    availability_score = (
        100 if runner_ok and total_stale_heartbeats == 0 else (50 if runner_ok else 0)
    )

    if availability_score == 100:
        print("✅ 系统可用性: 优秀 (>99.9%)")
        print("所有Runner进程正常运行，无陈旧心跳")
    elif availability_score == 50:
        print("⚠️  系统可用性: 需要关注 (<99.9%)")
        print("Runner进程运行正常，但存在陈旧心跳，建议检查")
    else:
        print("❌ 系统可用性: 异常 (0%)")
        print("Runner进程未运行，系统不可用")

    # 建议
    print("\n" + "=" * 60)
    print("💡 建议")
    print("=" * 60)

    if not runner_ok:
        print("1. 启动athena_ai_plan_runner进程:")
        print(
            "   screen -dmS athena_plan_runner python3 /Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"
        )

    if total_stale_heartbeats > 0:
        print("2. 处理陈旧心跳:")
        print("   - 检查相关Runner进程是否正常")
        print("   - 检查网络和系统负载")
        print("   - 考虑重启异常的Runner进程")

    # 检查队列依赖阻塞
    for result in queue_results:
        if "queue_status" in result and "dependency_blocked" in result["queue_status"].lower():
            print(f"3. 队列 {result['queue_file']} 处于依赖阻塞状态，需要手动介入")

    return availability_score


def main():
    """主函数"""
    print("🚀 开始队列活性探针检查")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"心跳阈值: {HEARTBEAT_THRESHOLD_MINUTES} 分钟")

    # 1. 检查Runner进程
    runner_ok, runner_count = check_runner_process()

    # 2. 检查队列文件
    queue_results = check_queue_files()

    # 3. 生成报告
    availability_score = generate_summary_report(runner_ok, runner_count, queue_results)

    # 4. 输出退出码
    if availability_score >= 99:
        print("\n✅ 探针检查通过")
        sys.exit(0)
    elif availability_score >= 50:
        print("\n⚠️  探针检查警告")
        sys.exit(1)
    else:
        print("\n❌ 探针检查失败")
        sys.exit(2)


if __name__ == "__main__":
    main()
