#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py task <command>
"""
移除幽灵依赖，修复队列阻塞
1. 识别并移除指向不存在任务的依赖关系
2. 修复manifest中completed但队列中pending的任务状态
3. 确保队列可以运行
"""

import json
import os
import shutil
from datetime import datetime

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)
MANIFEST_FILE = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"


def read_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def write_json(file_path, data):
    temp_file = f"{file_path}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp_file, file_path)


def main():
    print("=" * 60)
    print("👻 移除幽灵依赖，修复队列阻塞")
    print("=" * 60)

    # 备份原文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_queue = f"{QUEUE_FILE}.ghost_deps_fix_backup_{timestamp}"
    if os.path.exists(QUEUE_FILE) and not os.path.exists(backup_queue):
        shutil.copy2(QUEUE_FILE, backup_queue)
        print(f"📁 队列文件备份: {backup_queue}")

    # 读取队列文件
    print("\n📊 读取队列文件...")
    queue_data = read_json(QUEUE_FILE)
    items = queue_data.get("items", {})
    print(f"队列中任务数: {len(items)}")

    # 读取manifest文件
    print("\n📋 读取manifest文件...")
    manifest_data = read_json(MANIFEST_FILE)
    manifest_items = manifest_data.get("items", [])
    print(f"manifest中任务数: {len(manifest_items)}")

    # 创建任务ID集合（队列中存在的任务）
    existing_task_ids = set(items.keys())

    # 创建manifest任务映射
    manifest_task_map = {}
    for item in manifest_items:
        task_id = str(item.get("id", ""))
        manifest_task_map[task_id] = item

    print("\n🔍 检查幽灵依赖...")

    # 收集所有需要修复的任务
    tasks_to_fix = []

    for task_id, task_data in items.items():
        # 从manifest获取该任务的依赖关系
        manifest_item = manifest_task_map.get(task_id)
        if not manifest_item:
            continue

        manifest_metadata = manifest_item.get("metadata", {})
        depends_on = manifest_metadata.get("depends_on", [])

        # 检查每个依赖是否存在
        ghost_deps = []
        valid_deps = []

        for dep_id in depends_on:
            if dep_id not in existing_task_ids:
                ghost_deps.append(dep_id)
            else:
                valid_deps.append(dep_id)

        if ghost_deps:
            tasks_to_fix.append(
                {
                    "task_id": task_id,
                    "queue_status": task_data.get("status", "pending"),
                    "manifest_status": manifest_item.get("status", "pending"),
                    "original_deps": depends_on,
                    "ghost_deps": ghost_deps,
                    "valid_deps": valid_deps,
                    "manifest_item": manifest_item,
                }
            )

    print(f"发现 {len(tasks_to_fix)} 个任务有幽灵依赖:")
    for task in tasks_to_fix:
        print(
            f"  {task['task_id']}: 队列={task['queue_status']}, manifest={task['manifest_status']}"
        )
        print(f"    幽灵依赖: {task['ghost_deps']}")
        print(f"    有效依赖: {task['valid_deps']}")

    # 修复策略：移除幽灵依赖
    print("\n🔄 移除幽灵依赖...")
    fixed_ghost_deps = 0

    for task in tasks_to_fix:
        task_id = task["task_id"]

        # 获取manifest中的metadata
        manifest_item = task["manifest_item"]
        metadata = manifest_item.get("metadata", {}).copy()  # 创建副本

        # 从depends_on中移除幽灵依赖
        original_deps = metadata.get("depends_on", [])
        new_deps = [dep for dep in original_deps if dep not in task["ghost_deps"]]

        if len(new_deps) != len(original_deps):
            metadata["depends_on"] = new_deps
            fixed_ghost_deps += len(original_deps) - len(new_deps)
            print(f"  ✅ {task_id}: 移除幽灵依赖 {task['ghost_deps']}")
            print(f"     依赖: {original_deps} → {new_deps}")

            # 更新队列中的metadata（如果队列中的metadata为空）
            if not items[task_id].get("metadata"):
                items[task_id]["metadata"] = {}
            items[task_id]["metadata"]["depends_on"] = new_deps
            items[task_id]["metadata"]["_ghost_deps_removed"] = task["ghost_deps"]
            items[task_id]["updated_at"] = datetime.now().isoformat()

    print(f"\n✅ 总共移除了 {fixed_ghost_deps} 个幽灵依赖")

    # 现在检查manifest状态为completed但队列状态不为completed的任务
    print("\n🔄 同步manifest状态到队列...")
    synced_tasks = 0

    for task_id, task_data in items.items():
        manifest_item = manifest_task_map.get(task_id)
        if not manifest_item:
            continue

        manifest_status = manifest_item.get("status", "pending")
        queue_status = task_data.get("status", "pending")

        # 如果manifest状态为completed但队列状态不是completed
        if manifest_status == "completed" and queue_status != "completed":
            # 检查依赖是否都已满足（现在只检查有效依赖）
            metadata = manifest_item.get("metadata", {})
            depends_on = metadata.get("depends_on", [])

            all_deps_completed = True
            for dep_id in depends_on:
                dep_task = items.get(dep_id)
                if not dep_task or dep_task.get("status") != "completed":
                    all_deps_completed = False
                    break

            if all_deps_completed:
                print(f"  ✅ {task_id}: {queue_status} → completed (依赖已满足)")
                items[task_id]["status"] = "completed"
                items[task_id]["progress_percent"] = 100
                items[task_id]["updated_at"] = datetime.now().isoformat()
                items[task_id]["summary"] = "从manifest同步状态: 依赖已满足，标记为completed"
                synced_tasks += 1
            else:
                print(f"  ⚠️  {task_id}: 不能标记为completed，依赖未满足: {depends_on}")

    print(f"✅ 同步了 {synced_tasks} 个任务的状态")

    # 重新计算计数
    print("\n🧮 重新计算计数...")
    status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

    for _task_id, task_data in items.items():
        status = task_data.get("status", "pending")
        if status in status_counts:
            status_counts[status] += 1

    print("修复后的状态分布:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    # 检查依赖阻塞
    print("\n🔗 检查依赖阻塞...")
    blocked = False
    blocked_reason = ""
    pending_tasks = [(tid, task) for tid, task in items.items() if task.get("status") == "pending"]

    for task_id, _task_data in pending_tasks:
        # 从manifest获取依赖关系
        manifest_item = manifest_task_map.get(task_id)
        if not manifest_item:
            continue

        depends_on = manifest_item.get("metadata", {}).get("depends_on", [])
        for dep_id in depends_on:
            dep_task = items.get(dep_id)
            if not dep_task:
                blocked = True
                blocked_reason = f"任务 {task_id} 依赖于 {dep_id} (不存在)"
                break
            elif dep_task.get("status") != "completed":
                blocked = True
                blocked_reason = f"任务 {task_id} 依赖于 {dep_id} (状态: {dep_task.get('status')})"
                break
        if blocked:
            break

    # 设置队列状态
    queue_data.get("queue_status", "unknown")
    queue_data.get("pause_reason", "")

    if blocked:
        new_status = "dependency_blocked"
        new_pause = "dependency_blocked"
        print(f"\n⚠️  队列仍存在依赖阻塞: {blocked_reason}")
        print(f"状态保持: {new_status}")
    else:
        new_status = "running"
        new_pause = ""
        print(f"\n✅ 无依赖阻塞，状态设置为: {new_status}")

    # 更新队列文件
    queue_data["items"] = items
    queue_data["counts"] = status_counts
    queue_data["queue_status"] = new_status
    queue_data["pause_reason"] = new_pause
    queue_data["updated_at"] = datetime.now().isoformat()

    # 设置当前任务（如果没有）
    if not queue_data.get("current_item_id") and status_counts["pending"] > 0:
        pending_tasks = [tid for tid, task in items.items() if task.get("status") == "pending"]
        if pending_tasks:
            queue_data["current_item_id"] = pending_tasks[0]
            print(f"设置当前任务: {queue_data['current_item_id']}")

    # 保存队列文件
    write_json(QUEUE_FILE, queue_data)
    print(f"\n💾 已保存修复后的队列文件: {QUEUE_FILE}")

    # 验证修复
    print("\n✅ 验证修复...")
    saved_data = read_json(QUEUE_FILE)
    saved_counts = saved_data.get("counts", {})
    saved_status = saved_data.get("queue_status", "unknown")

    if saved_counts == status_counts:
        print(f"  ✅ 计数修复成功: {json.dumps(saved_counts, ensure_ascii=False)}")
    else:
        print("  ❌ 计数修复失败")
        print(f"    期望: {json.dumps(status_counts, ensure_ascii=False)}")
        print(f"    实际: {json.dumps(saved_counts, ensure_ascii=False)}")

    if saved_status == new_status:
        print(f"  ✅ 状态修复成功: {saved_status}")
    else:
        print(f"  ❌ 状态修复失败: 期望 {new_status}, 实际 {saved_status}")

    # 输出总结
    print("\n🎉 修复完成总结:")
    print(f"  移除的幽灵依赖数: {fixed_ghost_deps}")
    print(f"  同步的任务状态数: {synced_tasks}")
    print(f"  最终队列状态: {new_status}")

    if new_status == "running":
        print("\n📋 下一步: 队列状态已修复为running，可以开始执行任务")
        print("  1. 建议重启队列运行器以应用修复")
        print("  2. 开始24小时监控验证")
        print("  3. 观察新架构在生产流量下的表现")
    else:
        print(f"\n📋 仍需解决的问题: {blocked_reason}")
        print("  可能需要进一步分析依赖关系或创建缺失的任务")

    print("=" * 60)


if __name__ == "__main__":
    main()
