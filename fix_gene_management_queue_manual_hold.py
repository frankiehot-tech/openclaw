#!/usr/bin/env python3
"""
修复基因管理队列手动保留状态问题
问题诊断：队列处于manual_hold状态，有5个手动任务、6个失败任务
"""

import json
import os
import time
from datetime import datetime


def diagnose_gene_management_queue():
    """诊断基因管理队列问题"""

    print("🔍 开始诊断基因管理队列停止和手动拉起问题...")

    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"

    if not os.path.exists(queue_file):
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return None

    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            queue_state = json.load(f)

        print(f"📊 队列ID: {queue_state.get('queue_id', 'unknown')}")
        print(f"📋 队列名称: {queue_state.get('name', 'unknown')}")
        print(f"📊 队列状态: {queue_state.get('queue_status', 'unknown')}")
        print(f"⏸️  暂停原因: {queue_state.get('pause_reason', 'unknown')}")
        print(f"🎯 当前任务: {queue_state.get('current_item_id', '无')}")
        print(f"🕒 更新时间: {queue_state.get('updated_at', 'unknown')}")

        # 分析任务状态
        counts = queue_state.get("counts", {})
        print(
            f"📈 任务统计: pending={counts.get('pending', 0)}, running={counts.get('running', 0)}, "
            f"completed={counts.get('completed', 0)}, failed={counts.get('failed', 0)}, "
            f"manual_hold={counts.get('manual_hold', 0)}"
        )

        # 列出所有任务
        items = queue_state.get("items", {})
        print(f"📦 总任务数: {len(items)}")

        # 分类任务状态
        manual_hold_tasks = []
        failed_tasks = []
        completed_tasks = []

        for task_id, task in items.items():
            status = task.get("status", "")
            title = task.get("title", task_id)[:50]
            if status == "manual_hold":
                manual_hold_tasks.append((task_id, title))
            elif status == "failed":
                failed_tasks.append((task_id, title))
            elif status == "completed":
                completed_tasks.append((task_id, title))

        print(f"\n🖐️  手动待拉起任务 ({len(manual_hold_tasks)}个):")
        for task_id, title in manual_hold_tasks:
            print(f"   • {task_id}: {title}...")

        print(f"\n❌ 失败任务 ({len(failed_tasks)}个):")
        for task_id, title in failed_tasks:
            task = items.get(task_id, {})
            error = task.get("error", "无错误信息")
            print(f"   • {task_id}: {title}...")
            print(f"     错误: {error[:100]}...")

        print(f"\n✅ 已完成任务 ({len(completed_tasks)}个)")

        return queue_state, items, manual_hold_tasks

    except Exception as e:
        print(f"❌ 诊断队列问题失败: {e}")
        return None, None, None


def fix_gene_management_queue_manual_hold():
    """修复基因管理队列手动保留状态"""

    print("\n🔧 开始修复基因管理队列手动保留状态...")

    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"

    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            queue_state = json.load(f)

        items = queue_state.get("items", {})

        # 检查manual_hold状态的任务
        manual_hold_tasks = []
        for task_id, task in items.items():
            status = task.get("status", "")
            if status == "manual_hold":
                manual_hold_tasks.append(task_id)

        print(f"🔍 发现{len(manual_hold_tasks)}个manual_hold状态的任务: {manual_hold_tasks}")

        if manual_hold_tasks:
            # 选择第一个任务作为当前任务
            first_task_id = manual_hold_tasks[0]
            first_task = items.get(first_task_id, {})
            print(f"🎯 选择第一个任务作为当前任务: {first_task_id}")
            print(f"📝 任务标题: {first_task.get('title', '无标题')}")

            # 检查任务是否可以自动执行
            stage = first_task.get("stage", "")
            error = first_task.get("error", "")
            summary = first_task.get("summary", "")

            if error:
                print(f"⚠️  任务有错误，需要先修复: {error[:100]}...")
                # 清理错误，设置为pending状态重新尝试
                items[first_task_id]["error"] = ""
                items[first_task_id]["status"] = "pending"
                print(f"✅ 清理错误并设置为pending状态")

            # 修复队列状态
            queue_state["queue_status"] = "running"
            queue_state["pause_reason"] = ""
            queue_state["current_item_id"] = first_task_id
            queue_state["current_item_ids"] = manual_hold_tasks
            queue_state["updated_at"] = datetime.now().isoformat()

            # 更新任务状态
            for task_id in manual_hold_tasks:
                if task_id == first_task_id:
                    items[task_id]["status"] = "running"
                    items[task_id]["progress_percent"] = 0
                    if not items[task_id].get("started_at"):
                        items[task_id]["started_at"] = datetime.now().isoformat()
                else:
                    # 其他manual_hold任务保持原状，等待后续处理
                    pass

            # 更新任务计数
            counts = queue_state.get("counts", {})
            counts["pending"] = len(manual_hold_tasks) - 1  # 除了当前运行的任务
            counts["running"] = 1
            counts["manual_hold"] = 0  # 所有manual_hold任务都转换为pending或running
            queue_state["counts"] = counts
            queue_state["items"] = items

            # 保存修复后的状态
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump(queue_state, f, indent=2, ensure_ascii=False)

            print("✅ 基因管理队列手动保留状态已修复")
            print(f"📊 新队列状态: {queue_state['queue_status']}")
            print(f"🎯 当前任务: {first_task_id}")
            print(
                f"📈 任务统计: pending={counts['pending']}, running={counts['running']}, "
                f"completed={counts.get('completed', 0)}, failed={counts.get('failed', 0)}"
            )

            return True
        else:
            print("⚠️  没有发现manual_hold状态的任务")
            return False

    except Exception as e:
        print(f"❌ 修复队列失败: {e}")
        return False


def restart_queue_runner():
    """重启队列运行器进程"""

    print("\n🔄 检查并重启队列运行器进程...")

    try:
        # 检查是否有运行器进程
        import psutil

        runner_processes = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info["cmdline"]
                if cmdline and any(
                    keyword in " ".join(cmdline) for keyword in ["athena", "codex", "runner"]
                ):
                    runner_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if runner_processes:
            print(f"✅ 发现{len(runner_processes)}个运行器进程:")
            for proc in runner_processes:
                print(f"   • PID {proc['pid']}: {' '.join(proc['cmdline'][:3])}...")
            print("💡 运行器进程已在运行，无需重启")
        else:
            print("⚠️  未发现运行器进程，可能需要手动启动")

    except ImportError:
        print("ℹ️  psutil未安装，跳过运行器进程检查")
    except Exception as e:
        print(f"⚠️  检查运行器进程失败: {e}")


def main():
    """主函数"""

    print("=" * 60)
    print("基因管理队列修复工具")
    print("=" * 60)
    print("目标: 修复OpenHuman AIPlan基因管理队列manual_hold状态")
    print()

    # 诊断队列问题
    queue_state, items, manual_hold_tasks = diagnose_gene_management_queue()

    if queue_state is None:
        print("❌ 无法诊断队列问题，退出")
        return

    # 检查是否需要修复
    queue_status = queue_state.get("queue_status", "")
    pause_reason = queue_state.get("pause_reason", "")

    if queue_status == "manual_hold" and pause_reason == "manual_hold":
        print(f"\n⚠️  队列处于manual_hold状态，需要修复")

        print(f"\n⚠️  队列处于manual_hold状态，开始自动修复...")
        # 修复队列
        success = fix_gene_management_queue_manual_hold()

        if success:
            # 重启队列运行器
            restart_queue_runner()

            print("\n✅ 修复完成!")
            print("💡 请在Athena Web Desktop中检查队列状态是否更新")
            print("💡 如果手动拉起按钮仍然无效，请尝试刷新页面或重启Web服务")
        else:
            print("\n❌ 修复失败，请检查日志")
    elif queue_status == "running":
        print(f"\n✅ 队列已经在running状态")
        print("💡 如果手动拉起按钮仍然无效，可能是其他问题")
        print("   1. 检查Web服务是否正常")
        print("   2. 检查任务是否有错误配置")
        print("   3. 尝试刷新页面")
    else:
        print(f"\n⚠️  队列状态未知: {queue_status}")
        print("💡 可能需要手动检查队列配置")


if __name__ == "__main__":
    main()
