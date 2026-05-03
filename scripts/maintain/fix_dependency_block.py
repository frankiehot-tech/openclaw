#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复依赖阻塞问题
1. 检查manifest中状态为completed但队列中状态为pending的任务
2. 更新这些任务状态为completed（如果依赖已满足）
3. 检查并修复缺失的依赖任务
4. 确保队列可以开始执行
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


def check_dependency_exists(dep_id, items):
    """检查依赖任务是否存在"""
    return dep_id in items


def check_dependency_completed(dep_id, items):
    """检查依赖任务是否完成"""
    if dep_id not in items:
        return False, "不存在"
    dep_task = items[dep_id]
    status = dep_task.get("status", "pending")
    return status == "completed", status


def main():
    print("=" * 60)
    print("🔧 修复依赖阻塞问题")
    print("=" * 60)

    # 备份原文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_queue = f"{QUEUE_FILE}.dependency_fix_backup_{timestamp}"
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

    # 创建manifest任务ID到状态的映射
    manifest_status_map = {}
    manifest_deps_map = {}
    for item in manifest_items:
        task_id = str(item.get("id", ""))
        manifest_status_map[task_id] = item.get("status", "pending")
        manifest_deps_map[task_id] = item.get("metadata", {}).get("depends_on", [])

    # 找出manifest中状态为completed但队列中状态不为completed的任务
    print("\n🔍 检查状态不一致的任务...")
    inconsistent_tasks = []
    for task_id, task_data in items.items():
        queue_status = task_data.get("status", "pending")
        manifest_status = manifest_status_map.get(task_id, "pending")

        if manifest_status == "completed" and queue_status != "completed":
            # 检查依赖是否满足
            depends_on = manifest_deps_map.get(task_id, [])
            all_deps_completed = True
            missing_deps = []
            incomplete_deps = []

            for dep_id in depends_on:
                if not check_dependency_exists(dep_id, items):
                    missing_deps.append(dep_id)
                    all_deps_completed = False
                else:
                    is_completed, dep_status = check_dependency_completed(dep_id, items)
                    if not is_completed:
                        incomplete_deps.append((dep_id, dep_status))
                        all_deps_completed = False

            inconsistent_tasks.append(
                {
                    "id": task_id,
                    "queue_status": queue_status,
                    "manifest_status": manifest_status,
                    "depends_on": depends_on,
                    "all_deps_completed": all_deps_completed,
                    "missing_deps": missing_deps,
                    "incomplete_deps": incomplete_deps,
                }
            )

    print(f"发现 {len(inconsistent_tasks)} 个状态不一致的任务:")
    for task in inconsistent_tasks:
        print(f"  {task['id']}: 队列={task['queue_status']}, manifest={task['manifest_status']}")
        if task["depends_on"]:
            print(f"    依赖: {task['depends_on']}")
        if task["missing_deps"]:
            print(f"    缺失依赖: {task['missing_deps']}")
        if task["incomplete_deps"]:
            print(f"    未完成依赖: {task['incomplete_deps']}")

    # 修复策略
    print("\n🔄 应用修复策略...")
    fixed_count = 0
    dependency_issues = []

    for task in inconsistent_tasks:
        task_id = task["id"]

        if task["missing_deps"]:
            # 有缺失依赖，不能直接标记为completed
            print(f"  ⚠️  任务 {task_id} 有缺失依赖: {task['missing_deps']}")
            dependency_issues.append(
                {
                    "task_id": task_id,
                    "issue": "missing_dependencies",
                    "missing_deps": task["missing_deps"],
                }
            )
            continue

        if task["incomplete_deps"]:
            # 有未完成依赖
            print(f"  ⚠️  任务 {task_id} 有未完成依赖: {task['incomplete_deps']}")
            dependency_issues.append(
                {
                    "task_id": task_id,
                    "issue": "incomplete_dependencies",
                    "incomplete_deps": task["incomplete_deps"],
                }
            )
            continue

        # 所有依赖都已满足，可以更新状态为completed
        print(f"  ✅ 更新任务 {task_id}: {task['queue_status']} → completed")
        items[task_id]["status"] = "completed"
        items[task_id]["progress_percent"] = 100
        items[task_id]["updated_at"] = datetime.now().isoformat()
        items[task_id]["summary"] = "从manifest同步状态: 依赖已满足，标记为completed"
        fixed_count += 1

    # 处理缺失的依赖任务
    print("\n🔗 检查所有任务的依赖完整性...")
    all_missing_deps = set()
    for task in inconsistent_tasks:
        all_missing_deps.update(task.get("missing_deps", []))

    if all_missing_deps:
        print(f"发现 {len(all_missing_deps)} 个缺失的依赖任务:")
        for dep_id in sorted(all_missing_deps):
            print(f"  {dep_id}")

        # 检查这些缺失任务是否在manifest中
        missing_in_manifest = []
        for dep_id in all_missing_deps:
            if dep_id not in manifest_status_map:
                missing_in_manifest.append(dep_id)

        if missing_in_manifest:
            print(f"\n⚠️  以下 {len(missing_in_manifest)} 个缺失依赖在manifest中也不存在:")
            for dep_id in missing_in_manifest:
                print(f"  {dep_id}")

            # 对于在manifest中也不存在的依赖，我们需要决定如何处理
            # 选项1: 创建占位符任务并标记为completed（如果它们是前置条件）
            # 选项2: 从依赖关系中移除这些幽灵依赖
            print("\n💡 建议: 从依赖关系中移除这些不存在的任务")

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
    pending_tasks = [(tid, task) for tid, task in items.items() if task.get("status") == "pending"]

    for task_id, _task_data in pending_tasks:
        # 从manifest获取依赖关系（因为队列中的metadata可能为空）
        depends_on = manifest_deps_map.get(task_id, [])
        for dep_id in depends_on:
            dep_task = items.get(dep_id)
            if not dep_task:
                blocked = True
                print(f"发现阻塞依赖: 任务 {task_id} 依赖于 {dep_id} (不存在)")
                break
            elif dep_task.get("status") != "completed":
                blocked = True
                print(
                    f"发现阻塞依赖: 任务 {task_id} 依赖于 {dep_id} (状态: {dep_task.get('status')})"
                )
                break
        if blocked:
            break

    # 设置队列状态
    queue_data.get("queue_status", "unknown")
    queue_data.get("pause_reason", "")

    if blocked:
        new_status = "dependency_blocked"
        new_pause = "dependency_blocked"
        print(f"\n队列仍存在依赖阻塞，状态保持: {new_status}")
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
    print(f"  修复的任务数: {fixed_count}")
    print(f"  依赖问题数: {len(dependency_issues)}")
    print(f"  最终队列状态: {new_status}")

    if new_status == "running":
        print("\n📋 下一步: 队列状态已修复为running，可以开始执行任务")
        print("  1. 建议重启队列运行器以应用修复")
        print("  2. 开始24小时监控验证")
    else:
        print("\n📋 仍需解决的问题:")
        for issue in dependency_issues:
            if issue["issue"] == "missing_dependencies":
                print(f"  任务 {issue['task_id']} 有缺失依赖: {issue['missing_deps']}")
            elif issue["issue"] == "incomplete_dependencies":
                print(f"  任务 {issue['task_id']} 有未完成依赖: {issue['incomplete_deps']}")

    print("=" * 60)


if __name__ == "__main__":
    main()
