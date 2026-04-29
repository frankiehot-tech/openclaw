#!/usr/bin/env python3
"""
批量修复优先队列所有任务的autostart设置
"""

import json
import shutil
from datetime import datetime


def main():
    manifest_file = ".openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    print(f"批量修复manifest: {manifest_file}")

    # 读取manifest
    with open(manifest_file, encoding="utf-8") as f:
        manifest_data = json.load(f)

    manifest_items = manifest_data.get("items", [])
    updated_count = 0
    manual_hold_count = 0
    already_true_count = 0

    for item in manifest_items:
        metadata = item.get("metadata", {})
        item_id = item.get("id", "unknown")

        # 检查当前状态
        if metadata.get("autostart") is False:
            metadata["autostart"] = True
            item["metadata"] = metadata
            updated_count += 1
            print(f"  ✅ 修复 {item_id[:50]}... autostart=false -> true")
        elif "autostart" not in metadata:
            metadata["autostart"] = True
            item["metadata"] = metadata
            updated_count += 1
            print(f"  ✅ 添加 {item_id[:50]}... autostart=true")
        else:
            already_true_count += 1

        # 检查任务是否在manual_hold状态（根据其他条件）
        # 这里可以添加更多逻辑

    print("\n📊 统计:")
    print(f"  总任务数: {len(manifest_items)}")
    print(f"  已修复任务: {updated_count}")
    print(f"  已为true的任务: {already_true_count}")
    print(f"  推测的manual_hold任务: {manual_hold_count}")

    if updated_count > 0:
        # 创建备份
        backup = manifest_file + f".batch_fix_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(manifest_file, backup)
        print(f"\n✅ 创建备份: {backup}")

        # 保存修复后的文件
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        print("✅ manifest批量修复完成")

        # 建议重启队列运行器
        print("\n📋 下一步建议:")
        print("  1. 重启队列运行器进程以加载更新后的manifest")
        print("  2. 运行diagnose_queue.py验证修复效果")
        print("  3. 检查任务状态是否从manual_hold变为pending")
    else:
        print("\n⚠️  没有需要修复的任务，所有任务autostart已为true")

    # 同时修复状态文件中的queue_status
    state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    print(f"\n🔧 检查状态文件: {state_file}")

    try:
        with open(state_file, encoding="utf-8") as f:
            state_data = json.load(f)

        # 确保queue_status为running
        if state_data.get("queue_status") != "running":
            state_data["queue_status"] = "running"
            state_data["pause_reason"] = ""
            state_data["updated_at"] = datetime.now().isoformat()

            state_backup = (
                state_file + f".batch_fix_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            shutil.copy2(state_file, state_backup)

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)

            print("✅ 修复状态文件queue_status为running")
        else:
            print("✅ 状态文件queue_status已为running")

    except Exception as e:
        print(f"❌ 处理状态文件失败: {e}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
