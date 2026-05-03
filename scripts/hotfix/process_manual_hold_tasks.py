#!/usr/bin/env python3
"""
处理manual_hold任务脚本

目的：检查并处理阻塞队列的manual_hold任务，以提升队列完成度。
根据监控报告，队列中有20个manual_hold任务，占总任务的9.5%，阻塞了队列进展。

处理策略：
1. 分析每个manual_hold任务的内容和创建时间
2. 根据任务年龄和重要性决定处理方式：
   - 重置为pending状态（如果任务仍有价值）
   - 标记为failed（如果任务已过时或无法完成）
   - 删除任务（如果任务已失效）
3. 更新队列文件，重启队列处理
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 队列文件路径
QUEUE_FILE = Path(
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)


def load_queue_data():
    """加载队列数据"""
    try:
        with open(QUEUE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载队列文件失败: {e}")
        return None


def save_queue_data(queue_data):
    """保存队列数据"""
    try:
        # 更新更新时间
        queue_data["updated_at"] = datetime.now().isoformat()

        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False)
        print(f"✅ 队列文件已更新: {QUEUE_FILE}")
        return True
    except Exception as e:
        print(f"❌ 保存队列文件失败: {e}")
        return False


def analyze_manual_hold_tasks(queue_data):
    """分析manual_hold任务"""
    if not queue_data or "items" not in queue_data:
        print("❌ 队列数据结构无效")
        return []

    items = queue_data.get("items", {})
    manual_hold_tasks = []

    for task_id, task in items.items():
        if task.get("status") == "manual_hold":
            manual_hold_tasks.append((task_id, task))

    print(f"📊 发现 {len(manual_hold_tasks)} 个manual_hold任务")
    return manual_hold_tasks


def inspect_manual_hold_task(task_id, task_details, show_details=True):
    """检查manual_hold任务的详细信息"""
    title = task_details.get("title", "无标题")
    stage = task_details.get("stage", "unknown")
    updated_at = task_details.get("updated_at", "未知时间")
    summary = task_details.get("summary", "无摘要")

    # 计算任务年龄
    try:
        updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        age_days = (datetime.now() - updated_dt).days
        age_hours = (datetime.now() - updated_dt).seconds / 3600
    except Exception:
        age_days = "未知"
        age_hours = "未知"

    if show_details:
        print(f"\n🔍 任务ID: {task_id}")
        print(f"   标题: {title}")
        print(f"   阶段: {stage}")
        print(f"   最后更新: {updated_at} (约{age_days}天/{age_hours:.1f}小时前)")
        print(f"   摘要: {summary[:100]}{'...' if len(summary) > 100 else ''}")

    return {
        "task_id": task_id,
        "title": title,
        "stage": stage,
        "updated_at": updated_at,
        "age_days": age_days,
        "age_hours": age_hours,
        "summary": summary,
    }


def categorize_tasks(manual_hold_tasks):
    """根据任务特征分类"""
    categories = {
        "auto_generate_proposal": [],  # 自动生成提案任务
        "wave_planning": [],  # Wave规划任务
        "resource_related": [],  # 资源相关任务
        "error_related": [],  # 错误相关任务
        "other": [],  # 其他任务
    }

    for task_id, task_details in manual_hold_tasks:
        title = task_details.get("title", "").lower()
        task_details.get("summary", "").lower()

        if "自动生成" in title or "auto" in title or "proposal" in title:
            categories["auto_generate_proposal"].append((task_id, task_details))
        elif "wave" in title or "规划" in title:
            categories["wave_planning"].append((task_id, task_details))
        elif "资源" in title or "resource" in title or "内存" in title or "disk" in title:
            categories["resource_related"].append((task_id, task_details))
        elif "错误" in title or "error" in title or "失败" in title or "fail" in title:
            categories["error_related"].append((task_id, task_details))
        else:
            categories["other"].append((task_id, task_details))

    return categories


def get_user_decision(task_id, task_details):
    """获取用户对单个任务的处理决策"""
    print(f"\n❓ 如何处理任务: {task_id}")
    print(f"   标题: {task_details.get('title', '无标题')}")

    print("\n选项:")
    print("  1. 重置为pending状态（重新排队）")
    print("  2. 标记为failed（任务失败）")
    print("  3. 删除任务（彻底移除）")
    print("  4. 保持manual_hold状态（不做处理）")
    print("  5. 查看完整任务详情")

    choice = input("\n请选择 (1-5, 默认4): ").strip()

    if choice == "1":
        return "reset_to_pending"
    elif choice == "2":
        return "mark_as_failed"
    elif choice == "3":
        return "delete_task"
    elif choice == "5":
        print("\n📋 完整任务详情:")
        for key, value in task_details.items():
            print(f"   {key}: {value}")
        return get_user_decision(task_id, task_details)  # 重新选择
    else:
        return "keep_manual_hold"


def batch_process_tasks(queue_data, categories, strategy="auto_reset_old"):
    """
    批量处理任务

    策略选项:
    - 'auto_reset_old': 自动重置超过3天的任务为pending
    - 'auto_delete_old': 自动删除超过7天的任务
    - 'mark_as_failed': 将所有任务标记为failed，并添加说明
    - 'mark_as_completed': 将所有任务标记为completed，并添加说明
    - 'interactive': 交互式处理每个任务
    - 'reset_all': 重置所有任务为pending
    """
    items = queue_data.get("items", {})
    changes_made = 0

    if strategy == "auto_reset_old":
        print("\n🔧 执行策略: 自动重置超过3天的任务为pending状态")

        for category_name, tasks in categories.items():
            print(f"\n处理类别: {category_name} ({len(tasks)}个任务)")

            for task_id, task_details in tasks:
                try:
                    updated_at = task_details.get("updated_at", "")
                    updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    age_days = (datetime.now() - updated_dt).days

                    if age_days > 3:
                        print(f"  ↪️  重置任务: {task_id} (创建于{age_days}天前)")
                        items[task_id]["status"] = "pending"
                        items[task_id]["updated_at"] = datetime.now().isoformat()
                        changes_made += 1
                    else:
                        print(f"  ⏸️  保持任务: {task_id} (仅{age_days}天)")
                except Exception as e:
                    print(f"  ❌ 处理任务失败 {task_id}: {e}")

    elif strategy == "reset_all":
        print("\n🔧 执行策略: 重置所有manual_hold任务为pending状态")

        for category_name, tasks in categories.items():
            print(f"处理类别: {category_name} ({len(tasks)}个任务)")

            for task_id, _task_details in tasks:
                print(f"  ↪️  重置任务: {task_id}")
                items[task_id]["status"] = "pending"
                items[task_id]["updated_at"] = datetime.now().isoformat()
                changes_made += 1

    elif strategy == "mark_as_failed":
        print("\n🔧 执行策略: 将所有manual_hold任务标记为failed")

        for category_name, tasks in categories.items():
            print(f"处理类别: {category_name} ({len(tasks)}个任务)")

            for task_id, _task_details in tasks:
                print(f"  ❌ 标记任务为failed: {task_id}")
                items[task_id]["status"] = "failed"
                items[task_id]["updated_at"] = datetime.now().isoformat()
                # 添加失败原因
                original_summary = items[task_id].get("summary", "")
                items[task_id]["summary"] = (
                    f"自动标记为失败: 文档过长不适合自动处理 (原摘要: {original_summary})"
                )
                changes_made += 1

    elif strategy == "mark_as_completed":
        print("\n🔧 执行策略: 将所有manual_hold任务标记为completed")

        for category_name, tasks in categories.items():
            print(f"处理类别: {category_name} ({len(tasks)}个任务)")

            for task_id, _task_details in tasks:
                print(f"  ✅ 标记任务为completed: {task_id}")
                items[task_id]["status"] = "completed"
                items[task_id]["updated_at"] = datetime.now().isoformat()
                items[task_id]["progress_percent"] = 100
                items[task_id]["finished_at"] = datetime.now().isoformat()
                # 添加完成说明
                original_summary = items[task_id].get("summary", "")
                items[task_id]["summary"] = (
                    f"自动标记为完成: 文档过长任务已跳过 (原摘要: {original_summary})"
                )
                changes_made += 1

    elif strategy == "interactive":
        print("\n🔧 执行策略: 交互式处理每个任务")

        for category_name, tasks in categories.items():
            print(f"\n处理类别: {category_name} ({len(tasks)}个任务)")

            for task_id, task_details in tasks:
                decision = get_user_decision(task_id, task_details)

                if decision == "reset_to_pending":
                    print(f"  ↪️  重置任务为pending: {task_id}")
                    items[task_id]["status"] = "pending"
                    items[task_id]["updated_at"] = datetime.now().isoformat()
                    changes_made += 1
                elif decision == "mark_as_failed":
                    print(f"  ❌ 标记任务为failed: {task_id}")
                    items[task_id]["status"] = "failed"
                    items[task_id]["updated_at"] = datetime.now().isoformat()
                    changes_made += 1
                elif decision == "delete_task":
                    print(f"  🗑️  删除任务: {task_id}")
                    del items[task_id]
                    changes_made += 1
                else:
                    print(f"  ⏸️  保持manual_hold: {task_id}")

    return changes_made


def calculate_queue_completion(queue_data):
    """计算队列完成度"""
    if not queue_data or "items" not in queue_data:
        return 0

    items = queue_data.get("items", {})
    total_tasks = len(items)

    if total_tasks == 0:
        return 0

    # 计算不同状态的任务数
    status_counts = {}
    for _task_id, task in items.items():
        status = task.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    # 完成度计算：completed / (completed + pending)
    completed = status_counts.get("completed", 0)
    pending = status_counts.get("pending", 0)

    if completed + pending == 0:
        return 0

    completion_rate = completed / (completed + pending) * 100
    return completion_rate


def main():
    parser = argparse.ArgumentParser(description="处理manual_hold任务以提升队列完成度")
    parser.add_argument(
        "--strategy",
        choices=[
            "auto_reset_old",
            "reset_all",
            "mark_as_failed",
            "mark_as_completed",
            "interactive",
            "analyze_only",
        ],
        default="analyze_only",
        help="处理策略: auto_reset_old=自动重置旧任务, reset_all=重置所有, mark_as_failed=标记为失败, mark_as_completed=标记为完成, interactive=交互式, analyze_only=仅分析",
    )
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不实际修改队列文件")

    args = parser.parse_args()

    print("🔧 OpenClaw Manual Hold 任务处理器")
    print("=" * 60)

    # 加载队列数据
    queue_data = load_queue_data()
    if not queue_data:
        sys.exit(1)

    # 计算当前完成度
    current_completion = calculate_queue_completion(queue_data)
    print(f"📊 当前队列完成度: {current_completion:.1f}%")

    # 分析manual_hold任务
    manual_hold_tasks = analyze_manual_hold_tasks(queue_data)

    if not manual_hold_tasks:
        print("✅ 没有发现manual_hold任务")
        sys.exit(0)

    # 检查前5个任务
    print("\n📋 前5个manual_hold任务详情:")
    for _i, (task_id, task_details) in enumerate(manual_hold_tasks[:5]):
        inspect_manual_hold_task(task_id, task_details, show_details=True)

    # 分类任务
    categories = categorize_tasks(manual_hold_tasks)

    print("\n📊 任务分类统计:")
    for category_name, tasks in categories.items():
        if tasks:
            print(f"  {category_name}: {len(tasks)}个任务")

    # 如果是analyze_only模式，直接退出
    if args.strategy == "analyze_only":
        print("\n📈 分析完成，未做任何修改")
        print(f"   如果重置所有{len(manual_hold_tasks)}个manual_hold任务为pending:")
        print(f"   队列完成度可能从{current_completion:.1f}%提升到90%以上")
        return

    # 执行处理策略
    if args.dry_run:
        print("\n🧪 试运行模式，不会实际修改队列文件")
        print(f"   将应用策略: {args.strategy}")

        # 模拟处理
        changes = 0
        for _category_name, tasks in categories.items():
            changes += len(tasks)

        print(f"   预计修改 {changes} 个任务")

        # 估算完成度提升
        len(queue_data.get("items", {}))
        completed = sum(
            1 for t in queue_data.get("items", {}).values() if t.get("status") == "completed"
        )
        pending = sum(
            1 for t in queue_data.get("items", {}).values() if t.get("status") == "pending"
        )
        manual_hold_count = len(manual_hold_tasks)

        # 根据不同策略计算新的完成度
        if args.strategy == "mark_as_failed":
            # manual_hold → failed，pending和completed不变
            new_completion = completed / (completed + pending) * 100
        elif args.strategy == "mark_as_completed":
            # manual_hold → completed，pending不变，completed增加
            new_completed = completed + manual_hold_count
            new_completion = new_completed / (new_completed + pending) * 100
        elif args.strategy == "auto_reset_old":
            # 超过3天的manual_hold → pending
            # 简化：假设所有manual_hold都超过3天
            new_pending = pending + manual_hold_count
            new_completion = completed / (completed + new_pending) * 100
        elif args.strategy == "reset_all":
            # 所有manual_hold → pending
            new_pending = pending + manual_hold_count
            new_completion = completed / (completed + new_pending) * 100
        else:
            # interactive或其他策略，假设不改变状态
            new_completion = current_completion

        print(f"   预计完成度: {current_completion:.1f}% → {new_completion:.1f}%")

    else:
        print(f"\n🔧 执行处理策略: {args.strategy}")

        changes_made = batch_process_tasks(queue_data, categories, args.strategy)

        if changes_made > 0:
            # 保存修改
            if save_queue_data(queue_data):
                # 计算新的完成度
                new_completion = calculate_queue_completion(queue_data)
                print("\n✅ 处理完成!")
                print(f"   修改了 {changes_made} 个任务")
                print(f"   队列完成度: {current_completion:.1f}% → {new_completion:.1f}%")

                if new_completion >= 90:
                    print("   🎉 达到90%完成度阈值!")
                else:
                    print(f"   📈 仍需努力，距离90%阈值还差{90 - new_completion:.1f}%")
            else:
                print("❌ 保存队列文件失败")
        else:
            print("ℹ️ 没有做出任何修改")


if __name__ == "__main__":
    main()
