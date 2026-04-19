#!/usr/bin/env python3
"""
修复队列文件中的counts字段，使其与items中的实际状态匹配
"""

import json
import os
import sys
from pathlib import Path


def fix_queue_counts(queue_file_path):
    """修复指定队列文件的counts字段"""
    try:
        with open(queue_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 从items中计算实际状态
        items = data.get("items", {})
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

        actual_counts = counts.copy()

        for task_id, task in items.items():
            status = task.get("status", "").strip().lower()
            if status in actual_counts:
                actual_counts[status] += 1
            else:
                print(f"警告: 任务 {task_id} 有未知状态: {status}")

        # 获取旧的counts
        old_counts = data.get("counts", {})

        # 比较差异
        changed = False
        for status in counts.keys():
            old_val = old_counts.get(status, 0)
            new_val = actual_counts[status]
            if old_val != new_val:
                changed = True
                print(f"  {status}: {old_val} → {new_val}")

        if not changed:
            print(f"✅ {queue_file_path.name} 的counts字段已是最新")
            return False

        # 更新counts字段
        data["counts"] = actual_counts

        # 备份原文件
        backup_path = queue_file_path.with_suffix(".json.before_count_fix")
        import shutil

        shutil.copy2(queue_file_path, backup_path)

        # 写入修复后的文件
        with open(queue_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ {queue_file_path.name} 的counts字段已修复")
        print(f"   备份保存至: {backup_path.name}")

        # 验证修复
        with open(queue_file_path, "r", encoding="utf-8") as f:
            new_data = json.load(f)

        new_counts = new_data.get("counts", {})
        print(f"   修复后统计: {json.dumps(new_counts, ensure_ascii=False)}")

        return True

    except Exception as e:
        print(f"❌ 修复 {queue_file_path.name} 失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 修复指定队列文件
        queue_files = []
        for arg in sys.argv[1:]:
            path = Path(arg)
            if path.exists():
                queue_files.append(path)
            else:
                # 尝试在计划队列目录中查找
                queue_dir = Path(__file__).parent.parent / ".openclaw" / "plan_queue"
                candidate = queue_dir / arg
                if candidate.exists():
                    queue_files.append(candidate)
                else:
                    candidate = queue_dir / (arg + ".json")
                    if candidate.exists():
                        queue_files.append(candidate)
                    else:
                        print(f"❌ 找不到队列文件: {arg}")
    else:
        # 修复所有队列文件
        queue_dir = Path(__file__).parent.parent / ".openclaw" / "plan_queue"
        queue_files = list(queue_dir.glob("*.json"))

        # 排除备份文件
        exclude_keywords = [
            "backup",
            "dedup",
            "report",
            "monitor_backup",
            "batch_reset",
            "manual_hold_fix",
            "dependency_fix",
            "queue_status_fix",
        ]
        queue_files = [
            f
            for f in queue_files
            if not any(keyword in f.name.lower() for keyword in exclude_keywords)
            and not f.name.endswith(".backup")
        ]

    if not queue_files:
        print("❌ 没有找到队列文件")
        return 1

    print(f"🔍 找到 {len(queue_files)} 个队列文件")

    fixed_count = 0
    for queue_file in queue_files:
        print(f"\n📋 处理: {queue_file.name}")
        if fix_queue_counts(queue_file):
            fixed_count += 1

    print(f"\n📊 修复完成: {fixed_count}/{len(queue_files)} 个文件已更新")

    # 显示修复后的整体状态
    print(f"\n📈 修复后队列统计汇总:")
    for queue_file in queue_files:
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            queue_name = data.get("queue_id", queue_file.stem)
            counts = data.get("counts", {})

            # 计算总计
            total = sum(counts.values())
            pending = counts.get("pending", 0)

            print(
                f"  {queue_name}: 总计{total}任务, pending: {pending}, running: {counts.get('running', 0)}, "
                f"completed: {counts.get('completed', 0)}, manual_hold: {counts.get('manual_hold', 0)}"
            )
        except Exception as e:
            print(f"  {queue_file.name}: 读取失败 - {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
