#!/usr/bin/env python3
"""
直接修复counts字段
"""

import json
import os


def main():
    state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"

    print(f"加载状态文件: {state_file}")
    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", {})
    print(f"items数量: {len(items)}")

    # 直接计数
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
    for task_id, task in items.items():
        status = task.get("status", "pending")
        if status in counts:
            counts[status] += 1
        else:
            counts["pending"] += 1

    print(f"实际counts: {json.dumps(counts, ensure_ascii=False)}")
    print(f"当前counts: {json.dumps(data.get('counts', {}), ensure_ascii=False)}")

    # 更新
    data["counts"] = counts

    # 保存
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ counts已更新")

    # 验证
    with open(state_file, "r", encoding="utf-8") as f:
        data2 = json.load(f)
    print(f"验证counts: {json.dumps(data2.get('counts', {}), ensure_ascii=False)}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
