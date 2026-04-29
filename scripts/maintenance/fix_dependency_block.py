#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复队列依赖阻塞问题

问题：openhuman_aiplan_build_priority队列中3个任务因依赖athena_enterprise_architecture_audit而阻塞，
但该依赖任务实际上在openhuman_aiplan_codex_audit队列中已完成。

解决方案：检查所有队列，找到已完成但被其他任务依赖的任务，更新依赖引用或移除无效依赖。
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path

# 队列文件目录
QUEUE_DIR = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue"


def load_all_queues():
    """加载所有队列文件"""
    queues = {}

    for file_path in Path(QUEUE_DIR).glob("*.json"):
        try:
            with open(file_path, encoding="utf-8") as f:
                queue_data = json.load(f)
            queue_id = queue_data.get("queue_id", file_path.stem)

            items = queue_data.get("items", {})
            # 确保items是字典格式
            if isinstance(items, list):
                # 将列表转换为字典，使用task_id作为键
                items_dict = {}
                for item in items:
                    if isinstance(item, dict):
                        task_id = item.get("task_id") or item.get("id") or str(hash(str(item)))
                        items_dict[task_id] = item
                items = items_dict
            elif not isinstance(items, dict):
                # 如果既不是列表也不是字典，设为空字典
                items = {}

            queues[queue_id] = {
                "file_path": str(file_path),
                "data": queue_data,
                "items": items,
                "counts": queue_data.get("counts", {}),
            }
        except Exception as e:
            print(f"警告：加载队列文件 {file_path} 失败: {e}")

    return queues


def extract_dependencies_from_summary(summary):
    """从summary字段提取依赖任务ID"""
    if not summary:
        return []

    # 匹配模式：被依赖项阻塞：task_id(pending)
    pattern = r"被依赖项阻塞：([^(]+)\(pending\)"
    matches = re.findall(pattern, summary)
    return [match.strip() for match in matches]


def find_all_dependencies(queues):
    """查找所有任务的依赖关系"""
    all_dependencies = defaultdict(list)  # 任务 -> [依赖的任务]
    task_info = {}  # 任务ID -> (队列ID, 状态, 任务数据)

    for queue_id, queue_info in queues.items():
        items = queue_info["items"]

        for task_id, task_data in items.items():
            status = task_data.get("status", "unknown")
            task_info[task_id] = (queue_id, status, task_data)

            # 从summary提取依赖
            summary = task_data.get("summary", "")
            deps = extract_dependencies_from_summary(summary)

            # 从metadata提取依赖（如果存在）
            metadata = task_data.get("metadata", {})
            if "depends_on" in metadata:
                deps.extend(metadata["depends_on"])

            if deps:
                all_dependencies[task_id] = deps

    return all_dependencies, task_info


def find_dependency_blocks(all_dependencies, task_info):
    """查找依赖阻塞问题"""
    blocks = []

    for task_id, deps in all_dependencies.items():
        task_queue, task_status, task_data = task_info[task_id]

        # 只关注pending状态的任务
        if task_status != "pending":
            continue

        blocked_by = []
        for dep in deps:
            if dep not in task_info:
                # 依赖任务不存在
                blocked_by.append((dep, "不存在"))
            else:
                dep_queue, dep_status, _ = task_info[dep]
                if dep_status != "completed":
                    # 依赖任务未完成
                    blocked_by.append((dep, dep_status))

        if blocked_by:
            blocks.append(
                {
                    "task_id": task_id,
                    "task_queue": task_queue,
                    "task_status": task_status,
                    "blocked_by": blocked_by,
                    "dependency_count": len(deps),
                    "blocked_count": len(blocked_by),
                }
            )

    return blocks


def find_completed_dependencies_in_other_queues(all_dependencies, task_info):
    """查找在其他队列中已完成的依赖任务"""
    completed_in_other_queue = []

    for task_id, deps in all_dependencies.items():
        task_queue, task_status, _ = task_info[task_id]

        for dep in deps:
            if dep in task_info:
                dep_queue, dep_status, _ = task_info[dep]
                if dep_status == "completed" and dep_queue != task_queue:
                    # 依赖任务在其他队列中已完成
                    completed_in_other_queue.append(
                        {
                            "task_id": task_id,
                            "task_queue": task_queue,
                            "task_status": task_status,
                            "dep_task": dep,
                            "dep_queue": dep_queue,
                            "dep_status": dep_status,
                        }
                    )

    return completed_in_other_queue


def fix_dependency_block(queues, blocks, completed_in_other_queue):
    """修复依赖阻塞问题"""
    fixed_tasks = []

    for block in blocks:
        task_id = block["task_id"]
        task_queue = block["task_queue"]

        if task_queue not in queues:
            print(f"警告：队列 {task_queue} 不在内存中，跳过任务 {task_id}")
            continue

        queue_info = queues[task_queue]
        items = queue_info["items"]

        if task_id not in items:
            print(f"警告：任务 {task_id} 不在队列 {task_queue} 中")
            continue

        task_data = items[task_id]
        summary = task_data.get("summary", "")

        # 检查每个阻塞的依赖
        for dep, dep_status in block["blocked_by"]:
            # 检查这个依赖是否在其他队列中已完成
            matching_completed = [
                item
                for item in completed_in_other_queue
                if item["task_id"] == task_id and item["dep_task"] == dep
            ]

            if matching_completed:
                # 依赖在其他队列中已完成，从summary中移除依赖信息
                print(f"修复：任务 {task_id} 依赖 {dep} 在其他队列中已完成，移除依赖引用")

                # 从summary中移除依赖信息
                old_summary = summary
                pattern = rf"被依赖项阻塞：{re.escape(dep)}\(pending\)"
                new_summary = re.sub(pattern, "", summary).strip()

                if new_summary != old_summary:
                    task_data["summary"] = new_summary
                    fixed_tasks.append(
                        {
                            "task_id": task_id,
                            "queue": task_queue,
                            "action": "remove_dependency_reference",
                            "dependency": dep,
                            "old_summary": (
                                old_summary[:100] + "..." if len(old_summary) > 100 else old_summary
                            ),
                            "new_summary": (
                                new_summary[:100] + "..." if len(new_summary) > 100 else new_summary
                            ),
                        }
                    )
            elif dep_status == "不存在":
                # 依赖任务不存在，检查是否应该创建或移除
                print(f"警告：任务 {task_id} 依赖不存在的任务 {dep}")
                # 这里可以根据业务逻辑决定是创建任务还是移除依赖
                # 目前先记录，让用户决定

    return fixed_tasks, queues


def save_queues(queues):
    """保存更新后的队列文件"""
    saved_files = []

    for _queue_id, queue_info in queues.items():
        file_path = queue_info["file_path"]
        data = queue_info["data"]

        try:
            # 备份原文件
            backup_path = f"{file_path}.backup"
            if os.path.exists(file_path) and not os.path.exists(backup_path):
                import shutil

                shutil.copy2(file_path, backup_path)

            # 更新计数（如果需要）
            pending_count = sum(
                1 for task in data["items"].values() if task.get("status") == "pending"
            )
            running_count = sum(
                1 for task in data["items"].values() if task.get("status") == "running"
            )
            completed_count = sum(
                1 for task in data["items"].values() if task.get("status") == "completed"
            )
            failed_count = sum(
                1 for task in data["items"].values() if task.get("status") == "failed"
            )
            manual_hold_count = sum(
                1 for task in data["items"].values() if task.get("status") == "manual_hold"
            )

            if "counts" not in data:
                data["counts"] = {}

            data["counts"]["pending"] = pending_count
            data["counts"]["running"] = running_count
            data["counts"]["completed"] = completed_count
            data["counts"]["failed"] = failed_count
            data["counts"]["manual_hold"] = manual_hold_count

            # 保存文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            saved_files.append(file_path)
            print(f"保存队列文件: {file_path}")

        except Exception as e:
            print(f"错误：保存队列文件 {file_path} 失败: {e}")

    return saved_files


def main():
    print("🔍 开始分析队列依赖阻塞问题...")

    # 1. 加载所有队列
    queues = load_all_queues()
    print(f"已加载 {len(queues)} 个队列文件")

    # 2. 查找所有依赖关系
    all_dependencies, task_info = find_all_dependencies(queues)
    print(f"分析 {len(all_dependencies)} 个任务的依赖关系")

    # 3. 查找阻塞问题
    blocks = find_dependency_blocks(all_dependencies, task_info)
    if blocks:
        print(f"🔴 发现 {len(blocks)} 个依赖阻塞问题:")
        for i, block in enumerate(blocks[:10], 1):
            print(f"  {i}. 任务: {block['task_id']} (队列: {block['task_queue']})")
            for dep, dep_status in block["blocked_by"]:
                print(f"     被阻塞于: {dep} ({dep_status})")

        if len(blocks) > 10:
            print(f"  ... 以及另外 {len(blocks) - 10} 个阻塞问题")
    else:
        print("✅ 未发现依赖阻塞问题")

    # 4. 查找在其他队列中已完成的依赖
    completed_in_other_queue = find_completed_dependencies_in_other_queues(
        all_dependencies, task_info
    )
    if completed_in_other_queue:
        print(f"📝 发现 {len(completed_in_other_queue)} 个在其他队列中已完成的依赖:")
        for i, item in enumerate(completed_in_other_queue[:5], 1):
            print(f"  {i}. 任务 {item['task_id']} 依赖 {item['dep_task']}")
            print(f"     依赖任务在队列 {item['dep_queue']} 中状态为 {item['dep_status']}")

        if len(completed_in_other_queue) > 5:
            print(f"  ... 以及另外 {len(completed_in_other_queue) - 5} 个")

    # 5. 修复问题
    if completed_in_other_queue:
        print("\n🔧 开始修复依赖阻塞问题...")

        # 为completed_in_other_queue中的每个项创建阻塞条目
        blocks_from_completed = []
        for item in completed_in_other_queue:
            blocks_from_completed.append(
                {
                    "task_id": item["task_id"],
                    "task_queue": item["task_queue"],
                    "task_status": item["task_status"],
                    "blocked_by": [(item["dep_task"], "completed_in_other_queue")],
                    "dependency_count": 1,
                    "blocked_count": 1,
                }
            )

        fixed_tasks, updated_queues = fix_dependency_block(
            queues, blocks_from_completed, completed_in_other_queue
        )

        if fixed_tasks:
            print(f"✅ 修复了 {len(fixed_tasks)} 个任务:")
            for i, fix in enumerate(fixed_tasks, 1):
                print(f"  {i}. 任务: {fix['task_id']}")
                print(f"     队列: {fix['queue']}")
                print(f"     操作: {fix['action']}")
                print(f"     依赖: {fix['dependency']}")

            # 保存更新
            saved_files = save_queues(updated_queues)
            print(f"💾 已保存 {len(saved_files)} 个队列文件")

            # 更新队列状态（如果队列变为空，可能需要更新queue_status）
            for queue_id, queue_info in updated_queues.items():
                data = queue_info["data"]
                pending_count = data.get("counts", {}).get("pending", 0)
                running_count = data.get("counts", {}).get("running", 0)

                if pending_count == 0 and running_count == 0:
                    if data.get("queue_status") in ["running", "dependency_blocked"]:
                        data["queue_status"] = "completed"
                        print(f"🔄 队列 {queue_id} 已无任务，状态更新为 completed")
                elif pending_count > 0:
                    if data.get("queue_status") == "dependency_blocked":
                        # 检查是否还有依赖阻塞
                        updated_blocks = find_dependency_blocks(
                            find_all_dependencies({queue_id: queue_info})[0],
                            find_all_dependencies({queue_id: queue_info})[1],
                        )
                        if not updated_blocks:
                            data["queue_status"] = "running"
                            print(f"🔄 队列 {queue_id} 依赖阻塞已解决，状态更新为 running")
        else:
            print("⚠️ 没有需要修复的任务")
    else:
        print("⚠️ 没有发现可修复的依赖阻塞问题")

    # 6. 统计信息
    print("\n📊 队列状态统计:")
    for queue_id, queue_info in queues.items():
        counts = queue_info["counts"]
        queue_status = queue_info["data"].get("queue_status", "unknown")
        print(f"  {queue_id}: {queue_status}")
        print(
            f"    任务: pending={counts.get('pending', 0)}, running={counts.get('running', 0)}, "
            f"completed={counts.get('completed', 0)}, failed={counts.get('failed', 0)}"
        )

    print("\n🎉 依赖阻塞分析完成！")


if __name__ == "__main__":
    main()
