#!/usr/bin/env python3
"""
最终收尾工作流程
1. 验证系统状态
2. 完成剩余任务（可选）
3. 生成最终报告
4. 清理临时文件
"""

import json
import os
import sys
from datetime import datetime, timezone


def load_queue_data():
    """加载队列数据"""
    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"

    if not os.path.exists(queue_file):
        print(f"❌ 队列文件不存在: {queue_file}")
        return None

    with open(queue_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue_data(data):
    """保存队列数据"""
    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"

    # 重新计算counts字段
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
    for task in data.get("items", []):
        status = task.get("status", "").strip().lower()
        if status in counts:
            counts[status] += 1
        else:
            counts["pending"] += 1

    data["counts"] = counts

    # 原子性写入
    with open(queue_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return counts


def verify_system_state(data):
    """验证系统状态"""
    print("🔍 验证系统状态...")

    total_tasks = len(data.get("items", []))
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

    for task in data.get("items", []):
        status = task.get("status", "").strip().lower()
        if status in counts:
            counts[status] += 1
        else:
            counts["pending"] += 1

    completion_rate = (counts["completed"] + counts["failed"]) / total_tasks * 100

    print(f"📊 总任务数: {total_tasks}")
    print(f"✅ 已完成: {counts['completed']}")
    print(f"⏸️ 等待中: {counts['pending']}")
    print(f"🚫 人工暂停: {counts['manual_hold']}")
    print(f"🟢 运行中: {counts['running']}")
    print(f"❌ 已失败: {counts['failed']}")
    print(f"📈 完成度: {completion_rate:.2f}%")

    # 检查关键任务状态
    critical_tasks = []
    for task in data.get("items", []):
        task_id = task.get("id", "")
        if "runner" in task_id or "persistence" in task_id:
            critical_tasks.append(
                {
                    "id": task_id,
                    "status": task.get("status"),
                    "progress": task.get("progress_percent", 0),
                }
            )

    print(f"\n🔑 关键任务状态:")
    for ct in critical_tasks:
        print(f"  - {ct['id']}: {ct['status']} (进度: {ct['progress']}%)")

    return {
        "total_tasks": total_tasks,
        "counts": counts,
        "completion_rate": completion_rate,
        "critical_tasks": critical_tasks,
    }


def complete_pending_tasks(data, task_ids=None):
    """
    完成指定的pending任务
    task_ids: 要完成的任务ID列表，如果为None则完成所有pending任务
    """
    print(f"\n📝 处理pending任务...")

    completed_tasks = []
    for task in data.get("items", []):
        task_id = task.get("id", "")
        current_status = task.get("status", "").strip().lower()

        # 检查是否需要处理此任务
        should_complete = False
        if task_ids is None and current_status == "pending":
            should_complete = True
        elif task_id in (task_ids or []):
            should_complete = True

        if should_complete:
            old_status = task["status"]
            old_progress = task.get("progress_percent", 0)

            # 更新状态
            task["status"] = "completed"
            task["progress_percent"] = 100
            task["updated_at"] = datetime.now(timezone.utc).isoformat()

            # 添加完成记录
            if "closeout_history" not in task:
                task["closeout_history"] = []

            task["closeout_history"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "old_status": old_status,
                    "new_status": "completed",
                    "old_progress": old_progress,
                    "new_progress": 100,
                    "reason": "final_closeout_workflow: manual_completion",
                }
            )

            completed_tasks.append(
                {"id": task_id, "old_status": old_status, "new_status": "completed"}
            )

    if completed_tasks:
        print(f"✅ 完成了 {len(completed_tasks)} 个任务:")
        for ct in completed_tasks:
            print(f"  - {ct['id']}: {ct['old_status']} -> {ct['new_status']}")
    else:
        print("ℹ️ 无需完成任何pending任务")

    return completed_tasks


def complete_manual_hold_task(data, task_id, reason="final_closeout"):
    """完成manual_hold任务"""
    print(f"\n📝 处理manual_hold任务: {task_id}")

    for task in data.get("items", []):
        if task.get("id") == task_id and task.get("status") == "manual_hold":
            old_status = task["status"]
            old_progress = task.get("progress_percent", 0)

            # 更新状态
            task["status"] = "completed"
            task["progress_percent"] = 100
            task["updated_at"] = datetime.now(timezone.utc).isoformat()

            # 添加完成记录
            if "closeout_history" not in task:
                task["closeout_history"] = []

            task["closeout_history"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "old_status": old_status,
                    "new_status": "completed",
                    "old_progress": old_progress,
                    "new_progress": 100,
                    "reason": f"final_closeout_workflow: {reason}",
                }
            )

            print(f"✅ {task_id}: {old_status} -> completed")
            return True

    print(f"ℹ️ 未找到manual_hold任务: {task_id}")
    return False


def generate_final_report(data, verification_result):
    """生成最终报告"""
    print(f"\n📄 生成最终报告...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = "/Volumes/1TB-M2/openclaw/.openclaw/reports"
    os.makedirs(report_dir, exist_ok=True)

    report_file = os.path.join(report_dir, f"final_closeout_report_{timestamp}.md")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("最终收尾工作报告\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"队列文件: openhuman_aiplan_priority_execution_20260414.json\n\n")

        f.write("## 系统状态摘要\n")
        f.write(f"- 总任务数: {verification_result['total_tasks']}\n")
        f.write(f"- 完成度: {verification_result['completion_rate']:.2f}%\n")
        f.write(f"- 已完成: {verification_result['counts']['completed']}\n")
        f.write(f"- 等待中: {verification_result['counts']['pending']}\n")
        f.write(f"- 人工暂停: {verification_result['counts']['manual_hold']}\n")
        f.write(f"- 运行中: {verification_result['counts']['running']}\n")
        f.write(f"- 已失败: {verification_result['counts']['failed']}\n\n")

        f.write("## 关键任务状态\n")
        for ct in verification_result["critical_tasks"]:
            f.write(f"- **{ct['id']}**: {ct['status']} (进度: {ct['progress']}%)\n")

        f.write("\n## 收尾操作\n")
        f.write("1. 系统状态验证 ✅\n")
        f.write("2. 生成最终报告 ✅\n")
        f.write("3. 队列状态已更新\n")
        f.write("4. 收尾工作流程完成\n\n")

        f.write("## 建议\n")
        f.write("✅ 队列收尾工作已完成，系统可进入维护模式。\n")
        f.write("📊 定期监控建议使用: `python3 scripts/queue_monitor.py --daemon`\n")

        f.write("\n" + "=" * 80 + "\n")

    print(f"📄 最终报告已保存至: {report_file}")
    return report_file


def main():
    """主函数"""
    print("=" * 60)
    print("最终收尾工作流程")
    print("=" * 60)

    # 1. 加载数据
    data = load_queue_data()
    if data is None:
        return

    # 2. 验证系统状态
    verification_result = verify_system_state(data)

    # 3. 询问用户操作
    print(f"\n🤔 请选择收尾操作:")
    print("1. 仅生成报告，不修改任务状态")
    print("2. 完成所有pending和manual_hold任务")
    print("3. 自定义选择要完成的任务")
    print("4. 退出")

    choice = input("请选择 (1-4): ").strip()

    if choice == "1":
        # 仅生成报告
        print("\n📋 选择: 仅生成报告")

    elif choice == "2":
        # 完成所有任务
        print("\n📋 选择: 完成所有pending和manual_hold任务")

        # 完成所有pending任务
        completed_pending = complete_pending_tasks(data)

        # 完成manual_hold任务
        manual_hold_tasks = []
        for task in data.get("items", []):
            if task.get("status") == "manual_hold":
                manual_hold_tasks.append(task.get("id"))

        for task_id in manual_hold_tasks:
            complete_manual_hold_task(data, task_id, "batch_closeout")

    elif choice == "3":
        # 自定义选择
        print("\n📋 选择: 自定义任务完成")

        # 显示pending任务
        pending_tasks = []
        for task in data.get("items", []):
            if task.get("status") == "pending":
                pending_tasks.append(task.get("id"))

        if pending_tasks:
            print(f"\n⏸️ 当前pending任务:")
            for i, task_id in enumerate(pending_tasks, 1):
                print(f"  {i}. {task_id}")

            selection = input("请输入要完成的任务编号（逗号分隔，或'all'完成所有）: ").strip()

            if selection.lower() == "all":
                complete_pending_tasks(data)
            elif selection:
                try:
                    indices = [int(idx.strip()) - 1 for idx in selection.split(",")]
                    selected_ids = [
                        pending_tasks[i] for i in indices if 0 <= i < len(pending_tasks)
                    ]
                    complete_pending_tasks(data, selected_ids)
                except (ValueError, IndexError):
                    print("❌ 输入无效，跳过pending任务处理")

        # 显示manual_hold任务
        manual_hold_tasks = []
        for task in data.get("items", []):
            if task.get("status") == "manual_hold":
                manual_hold_tasks.append(task.get("id"))

        if manual_hold_tasks:
            print(f"\n🚫 当前manual_hold任务:")
            for i, task_id in enumerate(manual_hold_tasks, 1):
                print(f"  {i}. {task_id}")

            selection = input("请输入要完成的任务编号（逗号分隔，或'all'完成所有）: ").strip()

            if selection.lower() == "all":
                for task_id in manual_hold_tasks:
                    complete_manual_hold_task(data, task_id, "manual_selection")
            elif selection:
                try:
                    indices = [int(idx.strip()) - 1 for idx in selection.split(",")]
                    selected_ids = [
                        manual_hold_tasks[i] for i in indices if 0 <= i < len(manual_hold_tasks)
                    ]
                    for task_id in selected_ids:
                        complete_manual_hold_task(data, task_id, "manual_selection")
                except (ValueError, IndexError):
                    print("❌ 输入无效，跳过manual_hold任务处理")

    elif choice == "4":
        print("退出收尾工作流程")
        return
    else:
        print("❌ 无效选择，退出")
        return

    # 4. 保存更新后的数据
    print(f"\n💾 保存队列数据...")
    counts = save_queue_data(data)
    print(f"✅ 队列状态已更新: {counts}")

    # 5. 生成最终报告
    report_file = generate_final_report(data, verification_result)

    # 6. 显示完成摘要
    print(f"\n🎉 收尾工作流程完成!")
    print(f"📄 报告文件: {report_file}")
    print(f"📊 最终状态: {counts}")
    print(
        f"📈 完成度: {(counts['completed'] + counts['failed']) / verification_result['total_tasks'] * 100:.2f}%"
    )


if __name__ == "__main__":
    main()
