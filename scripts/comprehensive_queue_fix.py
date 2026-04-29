#!/usr/bin/env python3
"""
综合队列修复脚本
1. 修复计数不一致问题（pending: 3实际 vs 19文件）
2. 同步manifest和队列文件状态
3. 强制设置队列状态为running
4. 确保队列可以开始执行任务
"""

import json
import os
import shutil
from datetime import datetime

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)
MANIFEST_FILE = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
RUNNER_CONFIG = "/Volumes/1TB-M2/openclaw/.athena-auto-queue.json"


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
    print("🔧 综合队列修复脚本")
    print("=" * 60)

    # 1. 备份原文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_queue = f"{QUEUE_FILE}.comprehensive_fix_backup_{timestamp}"
    if os.path.exists(QUEUE_FILE) and not os.path.exists(backup_queue):
        shutil.copy2(QUEUE_FILE, backup_queue)
        print(f"📁 队列文件备份: {backup_queue}")

    # 2. 读取队列文件
    print("\n📊 读取队列文件...")
    queue_data = read_json(QUEUE_FILE)
    if not queue_data:
        print("❌ 无法读取队列文件")
        return

    items = queue_data.get("items", {})
    print(f"队列中任务数: {len(items)}")

    # 3. 读取manifest文件
    print("\n📋 读取manifest文件...")
    manifest_data = read_json(MANIFEST_FILE)
    manifest_items = manifest_data.get("items", [])
    print(f"manifest中任务数: {len(manifest_items)}")

    # 4. 统计manifest任务状态
    manifest_status_counts = {}
    for item in manifest_items:
        status = item.get("status", "pending")
        manifest_status_counts[status] = manifest_status_counts.get(status, 0) + 1

    print("manifest状态分布:")
    for status, count in sorted(manifest_status_counts.items()):
        print(f"  {status}: {count}")

    # 5. 统计队列文件状态
    queue_status_counts = {}
    for task_id, task_data in items.items():
        status = task_data.get("status", "pending")
        queue_status_counts[status] = queue_status_counts.get(status, 0) + 1

    print("\n队列文件状态分布:")
    for status, count in sorted(queue_status_counts.items()):
        print(f"  {status}: {count}")

    # 6. 找出缺失的任务（在manifest中但不在队列中）
    manifest_task_ids = {str(item.get("id", "")) for item in manifest_items}
    queue_task_ids = set(items.keys())
    missing_task_ids = manifest_task_ids - queue_task_ids

    print(f"\n🔍 发现 {len(missing_task_ids)} 个任务在manifest中但不在队列中")
    if missing_task_ids:
        print("前5个缺失任务:")
        for i, task_id in enumerate(list(missing_task_ids)[:5]):
            print(f"  {i + 1}. {task_id}")

    # 7. 修复：为缺失任务添加默认completed状态（如果manifest中状态为completed）
    print("\n🔄 修复缺失任务状态...")
    added_count = 0
    for task_id in missing_task_ids:
        # 在manifest中查找该任务
        manifest_item = None
        for item in manifest_items:
            if str(item.get("id", "")) == task_id:
                manifest_item = item
                break

        if manifest_item:
            manifest_status = manifest_item.get("status", "pending")
            # 如果manifest中状态为completed，添加到队列文件
            if manifest_status == "completed":
                items[task_id] = {
                    "status": "completed",
                    "stage": manifest_item.get("entry_stage", "build"),
                    "progress_percent": 100,
                    "updated_at": manifest_item.get("updated_at", datetime.now().isoformat()),
                    "summary": f"从manifest同步的已完成任务: {manifest_item.get('title', task_id)}",
                    "instruction_path": manifest_item.get("instruction_path", ""),
                    "metadata": manifest_item.get("metadata", {}),
                }
                added_count += 1
            # 如果manifest中状态为failed，添加到队列文件
            elif manifest_status == "failed":
                items[task_id] = {
                    "status": "failed",
                    "stage": manifest_item.get("entry_stage", "build"),
                    "progress_percent": 0,
                    "updated_at": manifest_item.get("updated_at", datetime.now().isoformat()),
                    "summary": f"从manifest同步的失败任务: {manifest_item.get('title', task_id)}",
                    "instruction_path": manifest_item.get("instruction_path", ""),
                    "metadata": manifest_item.get("metadata", {}),
                }
                added_count += 1

    if added_count > 0:
        print(f"✅ 添加了 {added_count} 个缺失任务到队列文件")

    # 8. 重新计算计数
    print("\n🧮 重新计算计数...")
    status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

    for task_id, task_data in items.items():
        status = task_data.get("status", "pending")
        if status in status_counts:
            status_counts[status] += 1

    print("修正后的状态分布:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    # 9. 检查依赖阻塞
    print("\n🔗 检查依赖阻塞...")
    blocked = False
    pending_tasks = [(tid, task) for tid, task in items.items() if task.get("status") == "pending"]

    for task_id, task_data in pending_tasks:
        depends_on = task_data.get("metadata", {}).get("depends_on", [])
        for dep_id in depends_on:
            dep_task = items.get(dep_id)
            if not dep_task or dep_task.get("status") != "completed":
                blocked = True
                print(
                    f"发现阻塞依赖: 任务 {task_id} 依赖于 {dep_id} (状态: {dep_task.get('status') if dep_task else '不存在'})"
                )
                break
        if blocked:
            break

    # 10. 设置队列状态
    queue_data.get("queue_status", "unknown")
    queue_data.get("pause_reason", "")

    if blocked:
        new_status = "dependency_blocked"
        new_pause = "dependency_blocked"
        print(f"队列存在依赖阻塞，状态设置为: {new_status}")
    else:
        new_status = "running"
        new_pause = ""
        print(f"无依赖阻塞，状态设置为: {new_status}")

    # 11. 更新队列文件
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

    # 12. 保存队列文件
    write_json(QUEUE_FILE, queue_data)
    print(f"\n💾 已保存修复后的队列文件: {QUEUE_FILE}")

    # 13. 验证修复
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

    # 14. 建议后续步骤
    print("\n📋 建议后续步骤:")
    if new_status == "running":
        print("  1. 队列状态已修复为running，可以开始执行任务")
        print("  2. 建议重启队列运行器以应用修复")
        print("  3. 开始24小时监控验证")
    else:
        print("  1. 队列仍存在依赖阻塞，需要进一步分析")
        print("  2. 检查pending任务的依赖关系")
        print("  3. 可能需要手动完成依赖任务")

    print("\n🎉 综合修复完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
