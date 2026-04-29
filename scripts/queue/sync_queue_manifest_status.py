#!/usr/bin/env python3
"""
同步队列状态文件与manifest状态
解决Athena Web Desktop显示待执行任务问题
"""

import json
import sys
from pathlib import Path


def load_json(file_path):
    """加载JSON文件"""
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载文件失败 {file_path}: {e}")
        return None


def save_json(file_path, data):
    """保存JSON文件"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ 保存文件失败 {file_path}: {e}")
        return False


def sync_status(queue_file, manifest_file):
    """同步队列状态文件与manifest状态"""
    print("📊 开始同步状态...")
    print(f"   队列文件: {queue_file}")
    print(f"   Manifest文件: {manifest_file}")

    # 加载数据
    queue_data = load_json(queue_file)
    manifest_data = load_json(manifest_file)

    if not queue_data or not manifest_data:
        return False

    # 从manifest构建任务状态映射
    manifest_items = manifest_data.get("items", [])
    manifest_status_map = {}

    for item in manifest_items:
        item_id = item.get("id")
        if item_id:
            manifest_status_map[item_id] = item.get("status", "pending")

    print(f"   📋 Manifest中找到 {len(manifest_status_map)} 个任务")

    # 更新队列文件中的状态
    queue_items = queue_data.get("items", {})
    updated_count = 0
    pending_to_failed = 0
    pending_to_completed = 0

    for item_id, item_data in queue_items.items():
        queue_status = item_data.get("status", "pending")
        manifest_status = manifest_status_map.get(item_id)

        if manifest_status and queue_status != manifest_status:
            # 特别关注pending -> failed/completed的同步
            if queue_status == "pending" and manifest_status in ["failed", "completed"]:
                print(f"   🔄 同步任务: {item_id}")
                print(f"      队列状态: {queue_status} -> Manifest状态: {manifest_status}")
                item_data["status"] = manifest_status

                # 更新进度百分比
                if manifest_status in ["completed", "failed"]:
                    item_data["progress_percent"] = 100

                # 更新时间戳
                from datetime import datetime

                item_data["updated_at"] = datetime.now().isoformat()

                updated_count += 1
                if manifest_status == "failed":
                    pending_to_failed += 1
                elif manifest_status == "completed":
                    pending_to_completed += 1

    # 更新队列计数
    counts = queue_data.get("counts", {})
    if counts:
        original_pending = counts.get("pending", 0)
        original_failed = counts.get("failed", 0)
        original_completed = counts.get("completed", 0)

        # 调整计数
        counts["pending"] = max(0, original_pending - pending_to_failed - pending_to_completed)
        counts["failed"] = original_failed + pending_to_failed
        counts["completed"] = original_completed + pending_to_completed

        print("   📈 更新队列计数:")
        print(f"      pending: {original_pending} -> {counts['pending']}")
        print(f"      failed: {original_failed} -> {counts['failed']}")
        print(f"      completed: {original_completed} -> {counts['completed']}")

        # 如果pending=0，考虑更新队列状态
        if counts["pending"] == 0 and queue_data.get("queue_status") == "no_consumer":
            queue_data["queue_status"] = "empty"
            queue_data["pause_reason"] = ""
            print("   ✅ 队列已清空，更新状态: no_consumer -> empty")

    # 保存更新
    if updated_count > 0:
        if save_json(queue_file, queue_data):
            print(f"✅ 同步完成! 更新了 {updated_count} 个任务状态")
            print(
                f"   📊 统计: {pending_to_failed}个pending->failed, {pending_to_completed}个pending->completed"
            )
            return True
        else:
            print("❌ 保存失败")
            return False
    else:
        print("ℹ️  无需同步，所有任务状态已一致")
        return True


def main():
    """主函数"""
    # 文件路径
    queue_file = Path(
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    )
    manifest_file = Path(
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    )

    if not queue_file.exists():
        print(f"❌ 队列文件不存在: {queue_file}")
        return 1

    if not manifest_file.exists():
        print(f"❌ Manifest文件不存在: {manifest_file}")
        return 1

    # 执行同步
    success = sync_status(queue_file, manifest_file)

    if success:
        print("\n🎉 状态同步完成!")
        print("   Athena Web Desktop现在应该显示正确的任务状态")
        print("   队列状态已更新，pending任务数量已调整")
        return 0
    else:
        print("\n❌ 状态同步失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
