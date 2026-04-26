#!/usr/bin/env python3
"""
修复状态文件queue_status和counts
"""

import json
import sys
from pathlib import Path


def main():
    state_file = Path(".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json")
    print(f"修复状态文件: {state_file}")

    if not state_file.exists():
        print("❌ 状态文件不存在")
        return 1

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 读取状态文件失败: {e}")
        return 1

    print("📊 当前状态:")
    print(f"  queue_status: {data.get('queue_status')}")
    print(f"  pause_reason: {data.get('pause_reason')}")
    print(f"  counts: {json.dumps(data.get('counts', {}), ensure_ascii=False, indent=4)}")

    # 重新计算counts
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

    items = data.get("items", {})
    for task_id, task in items.items():
        status = task.get("status", "pending")
        if status in counts:
            counts[status] += 1
        else:
            print(f"⚠️  未知状态: {task_id} -> {status}")
            counts["pending"] += 1

    print("📊 重新计算的counts:")
    print(json.dumps(counts, ensure_ascii=False, indent=4))

    # 更新数据
    data["queue_status"] = "running"
    data["pause_reason"] = ""
    data["counts"] = counts

    # 确保updated_at是最新的
    from datetime import datetime

    data["updated_at"] = datetime.now().isoformat()

    # 保存备份
    backup_file = state_file.with_suffix(
        f".json.backup_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    import shutil

    shutil.copy2(state_file, backup_file)
    print(f"✅ 创建备份: {backup_file}")

    # 写入修复后的文件
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("✅ 状态文件修复完成")
        print(f"  queue_status: {data['queue_status']}")
        print(f"  pause_reason: {data['pause_reason']}")
        print(f"  counts: {json.dumps(data['counts'], ensure_ascii=False, indent=4)}")
    except Exception as e:
        print(f"❌ 写入状态文件失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
