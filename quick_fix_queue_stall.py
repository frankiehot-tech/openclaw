#!/usr/bin/env python3
"""
快速修复队列停滞问题
直接更新openhuman_aiplan_build_priority_20260328队列
移除已完成的跨队列依赖引用，更新队列状态
"""

import json
import os
import re
from pathlib import Path

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)
BACKUP_FILE = f"{QUEUE_FILE}.backup_quickfix"


def load_queue():
    """加载队列文件"""
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(data):
    """保存队列文件"""
    # 备份原文件
    if os.path.exists(QUEUE_FILE) and not os.path.exists(BACKUP_FILE):
        import shutil

        shutil.copy2(QUEUE_FILE, BACKUP_FILE)
        print(f"📂 已备份原文件: {BACKUP_FILE}")

    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 已保存队列文件: {QUEUE_FILE}")


def find_completed_deps_in_other_queues():
    """查找在其他队列中已完成的依赖任务"""
    queue_dir = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
    completed_tasks = {}

    for file_path in queue_dir.glob("*.json"):
        if file_path.name == "openhuman_aiplan_build_priority_20260328.json":
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                queue_data = json.load(f)

            items = queue_data.get("items", {})
            if isinstance(items, list):
                # 转换为字典
                items_dict = {}
                for item in items:
                    if isinstance(item, dict):
                        task_id = item.get("task_id") or item.get("id") or str(hash(str(item)))
                        items_dict[task_id] = item
                items = items_dict

            for task_id, task_data in items.items():
                if task_data.get("status") == "completed":
                    completed_tasks[task_id] = {
                        "queue": queue_data.get("queue_id", file_path.stem),
                        "data": task_data,
                    }

        except Exception as e:
            print(f"警告：加载队列文件 {file_path} 失败: {e}")

    return completed_tasks


def extract_dependencies_from_summary(summary):
    """从summary字段提取依赖任务ID"""
    if not summary:
        return []

    # 匹配模式：被依赖项阻塞：task_id(pending)
    pattern = r"被依赖项阻塞：([^(]+)\(pending\)"
    matches = re.findall(pattern, summary)
    return [match.strip() for match in matches]


def fix_queue():
    """修复队列停滞问题"""
    print("🔍 开始快速修复队列停滞问题...")

    # 1. 加载队列数据
    queue_data = load_queue()
    items = queue_data.get("items", {})
    if isinstance(items, list):
        # 转换为字典
        items_dict = {}
        for item in items:
            if isinstance(item, dict):
                task_id = item.get("task_id") or item.get("id") or str(hash(str(item)))
                items_dict[task_id] = item
        items = items_dict
        queue_data["items"] = items

    # 2. 查找其他队列中已完成的依赖任务
    completed_deps = find_completed_deps_in_other_queues()
    print(f"📊 在其他队列中找到 {len(completed_deps)} 个已完成的任务")

    # 3. 修复pending任务中的依赖引用
    fixed_count = 0
    pending_tasks = []

    for task_id, task_data in items.items():
        if task_data.get("status") == "pending":
            pending_tasks.append(task_id)
            summary = task_data.get("summary", "")

            # 提取依赖
            deps = extract_dependencies_from_summary(summary)
            if not deps:
                continue

            for dep in deps:
                if dep in completed_deps:
                    # 依赖在其他队列中已完成，移除依赖引用
                    old_summary = summary
                    pattern = rf"被依赖项阻塞：{re.escape(dep)}\(pending\)"
                    new_summary = re.sub(pattern, "", summary).strip()

                    if new_summary != old_summary:
                        task_data["summary"] = new_summary
                        print(f"✅ 修复: 任务 {task_id} - 移除对 {dep} 的依赖引用")
                        print(f"   原summary: {old_summary[:80]}...")
                        print(f"   新summary: {new_summary[:80]}...")
                        fixed_count += 1
                        summary = new_summary  # 更新当前summary，用于后续依赖检查

    print(f"🔧 修复了 {fixed_count} 个任务的依赖引用")
    print(f"📋 队列中有 {len(pending_tasks)} 个pending任务")

    # 4. 更新队列状态
    if fixed_count > 0:
        # 重新计算任务状态计数
        pending_count = sum(1 for task in items.values() if task.get("status") == "pending")
        running_count = sum(1 for task in items.values() if task.get("status") == "running")
        completed_count = sum(1 for task in items.values() if task.get("status") == "completed")
        failed_count = sum(1 for task in items.values() if task.get("status") == "failed")

        # 更新counts
        if "counts" not in queue_data:
            queue_data["counts"] = {}

        queue_data["counts"]["pending"] = pending_count
        queue_data["counts"]["running"] = running_count
        queue_data["counts"]["completed"] = completed_count
        queue_data["counts"]["failed"] = failed_count

        # 检查是否还有依赖阻塞
        has_dependency_block = False
        for task_id, task_data in items.items():
            if task_data.get("status") == "pending":
                summary = task_data.get("summary", "")
                deps = extract_dependencies_from_summary(summary)
                if deps:
                    has_dependency_block = True
                    print(f"⚠️ 任务 {task_id} 仍有依赖阻塞: {deps}")

        # 更新queue_status
        current_status = queue_data.get("queue_status", "unknown")
        if current_status == "dependency_blocked" and not has_dependency_block:
            queue_data["queue_status"] = "running"
            print(f"🔄 队列状态从 dependency_blocked 更新为 running")
        elif current_status == "dependency_blocked" and has_dependency_block:
            print(f"⚠️ 队列仍有依赖阻塞，保持 dependency_blocked 状态")
        else:
            print(f"📊 当前队列状态: {current_status}")

    # 5. 保存更新
    save_queue(queue_data)

    # 6. 输出统计
    pending_count = sum(1 for task in items.values() if task.get("status") == "pending")
    running_count = sum(1 for task in items.values() if task.get("status") == "running")

    print(f"\n📊 修复后统计:")
    print(f"  pending任务: {pending_count}")
    print(f"  running任务: {running_count}")
    print(f"  队列状态: {queue_data.get('queue_status', 'unknown')}")

    if pending_count > 0 and queue_data.get("queue_status") == "running":
        print("🚀 队列已解除阻塞，可以开始执行任务！")
    elif pending_count == 0:
        print("✅ 队列中已无pending任务")

    return queue_data


if __name__ == "__main__":
    fix_queue()
