#!/usr/bin/env python3
"""
清理陈旧心跳脚本
修复实施方案中发现的陈旧心跳问题
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

PLAN_QUEUE_DIR = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue"


def check_process_exists(pid):
    """检查进程是否存在"""
    try:
        # 使用ps检查进程
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "pid="], capture_output=True, text=True
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:
        return False


def cleanup_queue_file(file_path):
    """清理单个队列文件中的陈旧心跳"""
    print(f"📄 处理队列文件: {os.path.basename(file_path)}")

    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        cleaned = False
        items = data.get("items", {})

        for item_id, item in items.items():
            status = item.get("status", "")
            runner_pid = item.get("runner_pid", "")
            heartbeat_at = item.get("runner_heartbeat_at", "")

            # 对于completed任务，清理PID但保留心跳时间
            if status == "completed" and runner_pid:
                print(f"  清理completed任务 {item_id} 的PID: {runner_pid}")
                item["runner_pid"] = ""
                cleaned = True

            # 对于非completed任务，检查进程是否存在
            elif status in ["running", "pending", "manual_hold"] and runner_pid:
                if not check_process_exists(runner_pid):
                    print(f"  ⚠️  任务 {item_id} 的进程不存在 (PID: {runner_pid})")
                    print(f"    状态: {status}, 心跳时间: {heartbeat_at}")

                    # 根据状态决定处理方式
                    if status == "running":
                        # running状态但进程不存在，标记为失败
                        print(f"    ❌ 将running任务标记为failed")
                        item["status"] = "failed"
                        item["error"] = f"进程 {runner_pid} 不存在"
                        item["finished_at"] = datetime.now(timezone.utc).isoformat()
                    elif status == "pending":
                        # pending状态但有心跳，清理PID
                        print(f"    🔧 清理pending任务的陈旧PID")
                        item["runner_pid"] = ""

                    item["runner_heartbeat_at"] = ""
                    cleaned = True

        # 更新队列状态
        if cleaned:
            # 重新计算统计
            counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

            for item_id, item in items.items():
                status = item.get("status", "")
                if status in counts:
                    counts[status] += 1

            data["counts"] = counts

            # 更新队列状态逻辑
            if counts["running"] > 0:
                queue_status = "running"
                pause_reason = ""
            elif counts["pending"] > 0 and counts["manual_hold"] == 0:
                queue_status = "ready"
                pause_reason = ""
            elif counts["pending"] > 0 and counts["manual_hold"] > 0:
                queue_status = "manual_hold"
                pause_reason = "manual_hold"
            elif counts["pending"] == 0 and counts["running"] == 0:
                queue_status = "empty"
                pause_reason = "empty"
            else:
                queue_status = data.get("queue_status", "unknown")
                pause_reason = data.get("pause_reason", "")

            data["queue_status"] = queue_status
            data["pause_reason"] = pause_reason
            data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # 保存文件
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"  ✅ 文件已更新")
            return True
        else:
            print(f"  ✓ 无需清理")
            return False

    except Exception as e:
        print(f"  ❌ 处理失败: {e}")
        return False


def resolve_dependency_blocked(file_path):
    """解决依赖阻塞问题"""
    print(f"\n🔗 检查依赖阻塞: {os.path.basename(file_path)}")

    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        queue_status = data.get("queue_status", "")

        if queue_status != "dependency_blocked":
            print(f"  ✓ 队列无依赖阻塞")
            return False

        # 检查是否有manual_hold任务
        items = data.get("items", {})
        manual_hold_items = []

        for item_id, item in items.items():
            if item.get("status") == "manual_hold":
                manual_hold_items.append((item_id, item))

        if manual_hold_items:
            print(f"  发现 {len(manual_hold_items)} 个manual_hold任务:")

            for item_id, item in manual_hold_items:
                summary = item.get("summary", "")
                pipeline_summary = item.get("pipeline_summary", "")

                print(f"    - {item_id}: {summary}")
                print(f"      原因: {pipeline_summary}")

                # 尝试解决文档过长的问题
                if "文档过长" in summary or "preflight_reject_manual" in pipeline_summary:
                    instruction_path = item.get("instruction_path", "")
                    if instruction_path and os.path.exists(instruction_path):
                        print(f"    📄 检查指令文件: {instruction_path}")

                        # 检查文件大小
                        try:
                            with open(instruction_path, "r") as f:
                                lines = f.readlines()

                            if len(lines) > 100:
                                print(f"    ⚠️  文件确实较长 ({len(lines)} 行)")
                                print(f"    💡 建议: 拆分为多个小任务或调整预处理逻辑")
                            else:
                                print(f"    📏 文件长度可接受 ({len(lines)} 行)")
                                print(f"    🔧 尝试重新标记为pending")
                                item["status"] = "pending"
                                item["runner_pid"] = ""
                                item["runner_heartbeat_at"] = ""

                        except Exception as e:
                            print(f"    ❌ 读取文件失败: {e}")

        # 检查pending任务是否有依赖关系
        pending_items = []
        for item_id, item in items.items():
            if item.get("status") == "pending":
                pending_items.append(item_id)

        if pending_items and not manual_hold_items:
            print(f"  有 {len(pending_items)} 个pending任务但无manual_hold")
            print(f"  🔧 将队列状态从dependency_blocked改为ready")
            data["queue_status"] = "ready"
            data["pause_reason"] = ""
            data["updated_at"] = datetime.now(timezone.utc).isoformat()

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"  ✅ 依赖阻塞已解决")
            return True

        print(f"  ⚠️  需要手动介入解决依赖阻塞")
        return False

    except Exception as e:
        print(f"  ❌ 解决依赖阻塞失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始清理陈旧心跳和解决依赖阻塞")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not os.path.exists(PLAN_QUEUE_DIR):
        print(f"❌ 队列目录不存在: {PLAN_QUEUE_DIR}")
        sys.exit(1)

    queue_files = [f for f in os.listdir(PLAN_QUEUE_DIR) if f.endswith(".json")]
    print(f"📊 找到 {len(queue_files)} 个队列文件")

    cleaned_count = 0
    resolved_count = 0

    for queue_file in queue_files:
        file_path = os.path.join(PLAN_QUEUE_DIR, queue_file)

        # 1. 清理陈旧心跳
        if cleanup_queue_file(file_path):
            cleaned_count += 1

        # 2. 解决依赖阻塞
        if resolve_dependency_blocked(file_path):
            resolved_count += 1

    print("\n" + "=" * 60)
    print("📋 清理完成报告")
    print("=" * 60)
    print(f"✅ 清理了 {cleaned_count}/{len(queue_files)} 个文件的陈旧心跳")
    print(f"✅ 解决了 {resolved_count}/{len(queue_files)} 个文件的依赖阻塞")

    if cleaned_count > 0 or resolved_count > 0:
        print("\n💡 建议运行队列活性探针验证修复效果:")
        print("   python3 scripts/queue_liveness_probe.py")

    sys.exit(0)


if __name__ == "__main__":
    main()
