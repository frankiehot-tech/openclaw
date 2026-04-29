#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复僵尸running任务：标记为running但实际没有进程执行的任务
"""

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


def find_zombie_tasks(queue_file_path, zombie_threshold_hours=2):
    """
    查找指定队列文件中的僵尸running任务
    """
    try:
        with open(queue_file_path, encoding="utf-8") as f:
            data = json.load(f)

        zombies = []

        # 获取items列表
        items = data.get("items", [])
        if isinstance(items, dict):
            items_list = list(items.values())
        elif isinstance(items, list):
            items_list = items
        else:
            print(f"❌ {queue_file_path.name}: items字段格式无效")
            return []

        current_time = datetime.now(UTC)
        threshold = timedelta(hours=zombie_threshold_hours)

        for item in items_list:
            if not isinstance(item, dict):
                continue

            status = item.get("status", "").strip().lower()
            if status != "running":
                continue

            # 检查updated_at时间
            updated_at_str = item.get("updated_at", "")
            if not updated_at_str:
                # 没有更新时间字段，可能是僵尸
                zombies.append(
                    {
                        "task_id": item.get("id", "unknown"),
                        "reason": "missing_updated_at",
                        "item": item,
                    }
                )
                continue

            try:
                # 解析时间字符串
                if "T" in updated_at_str:
                    # ISO格式: 2026-04-17T09:50:21.026775
                    if updated_at_str.endswith("Z"):
                        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    elif "+" in updated_at_str:
                        updated_at = datetime.fromisoformat(updated_at_str)
                    else:
                        # 没有时区信息，假设为UTC
                        updated_at = datetime.fromisoformat(updated_at_str + "+00:00")
                else:
                    # 其他格式，尝试解析
                    updated_at = datetime.strptime(updated_at_str, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"⚠️ 解析时间失败 {item.get('id', 'unknown')}: {e}")
                zombies.append(
                    {
                        "task_id": item.get("id", "unknown"),
                        "reason": "time_parse_error",
                        "item": item,
                    }
                )
                continue

            # 检查是否为时区感知
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)

            # 检查是否超过阈值
            time_diff = current_time - updated_at
            if time_diff > threshold:
                zombies.append(
                    {
                        "task_id": item.get("id", "unknown"),
                        "reason": "stale_running",
                        "age_hours": time_diff.total_seconds() / 3600,
                        "item": item,
                    }
                )
                continue

            # 检查progress_percent是否长时间未更新
            progress = item.get("progress_percent", 0)
            if 0 < progress < 100:
                # 检查是否有runner_pid
                runner_pid = item.get("runner_pid")
                if runner_pid is None:
                    # 没有进程ID，可能是僵尸
                    zombies.append(
                        {
                            "task_id": item.get("id", "unknown"),
                            "reason": "no_runner_pid",
                            "item": item,
                        }
                    )

        return zombies

    except Exception as e:
        print(f"❌ 读取 {queue_file_path.name} 失败: {e}")
        import traceback

        traceback.print_exc()
        return []


def fix_zombie_task(
    queue_file_path, zombie_info, new_status="pending", fix_reason="zombie_running_task"
):
    """
    修复单个僵尸任务
    """
    try:
        with open(queue_file_path, encoding="utf-8") as f:
            data = json.load(f)

        task_id = zombie_info["task_id"]

        # 备份原文件
        backup_path = queue_file_path.with_suffix(".json.before_zombie_fix")
        import shutil

        shutil.copy2(queue_file_path, backup_path)
        print(f"   备份保存至: {backup_path.name}")

        # 查找并更新任务
        items = data.get("items", [])
        if isinstance(items, dict):
            # 字典格式
            if task_id in items:
                task = items[task_id]
                old_status = task.get("status", "")

                # 更新状态
                task["status"] = new_status
                task["updated_at"] = datetime.now(UTC).isoformat()

                # 添加修复记录
                if "fix_history" not in task:
                    task["fix_history"] = []
                task["fix_history"].append(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "old_status": old_status,
                        "new_status": new_status,
                        "reason": f"{fix_reason}: {zombie_info['reason']}",
                        "age_hours": zombie_info.get("age_hours", 0),
                    }
                )

                print(f"   任务 {task_id}: {old_status} → {new_status}")
                print(f"   原因: {zombie_info['reason']}")

        elif isinstance(items, list):
            # 列表格式
            updated = False
            for _i, item in enumerate(items):
                if not isinstance(item, dict):
                    continue

                if item.get("id") == task_id:
                    old_status = item.get("status", "")

                    # 更新状态
                    item["status"] = new_status
                    item["updated_at"] = datetime.now(UTC).isoformat()

                    # 添加修复记录
                    if "fix_history" not in item:
                        item["fix_history"] = []
                    item["fix_history"].append(
                        {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "old_status": old_status,
                            "new_status": new_status,
                            "reason": f"{fix_reason}: {zombie_info['reason']}",
                            "age_hours": zombie_info.get("age_hours", 0),
                        }
                    )

                    print(f"   任务 {task_id}: {old_status} → {new_status}")
                    print(f"   原因: {zombie_info['reason']}")
                    updated = True
                    break

            if not updated:
                print(f"❌ 未找到任务: {task_id}")
                return False

        else:
            print("❌ items字段格式无效")
            return False

        # 写入修复后的文件
        with open(queue_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ 已修复 {task_id}")
        return True

    except Exception as e:
        print(f"❌ 修复任务 {task_id} 失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 指定队列文件
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
        # 检查所有队列文件
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
            "before_count_fix",
            "before_zombie_fix",
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

    print(f"🔍 检查 {len(queue_files)} 个队列文件中的僵尸running任务...")
    print("   阈值: 超过2小时未更新的running任务视为僵尸")
    print()

    total_zombies = 0
    fixed_zombies = 0

    for queue_file in queue_files:
        print(f"\n📋 检查: {queue_file.name}")

        zombies = find_zombie_tasks(queue_file, zombie_threshold_hours=2)

        if not zombies:
            print("   ✅ 未发现僵尸running任务")
            continue

        print(f"   ⚠️ 发现 {len(zombies)} 个僵尸running任务:")
        for zombie in zombies:
            print(f"     - {zombie['task_id']}: {zombie['reason']}")
            if "age_hours" in zombie:
                print(f"       已运行 {zombie['age_hours']:.1f} 小时未更新")

        total_zombies += len(zombies)

        # 询问用户是否修复
        print("\n   是否修复这些任务? (自动修复)")
        for zombie in zombies:
            # 决定新状态：如果是P0任务且依赖链阻塞，设为manual_hold
            task_id = zombie["task_id"]
            if "aiplan_queue_runner_persistence" in task_id:
                new_status = "manual_hold"  # 关键任务，手动处理
                fix_reason = "critical_zombie_requires_manual_intervention"
            elif "checkpoint" in task_id.lower() or "stress" in task_id.lower():
                new_status = "pending"  # 压测检查点任务，重置为pending
                fix_reason = "stress_test_zombie_reset"
            else:
                new_status = "pending"
                fix_reason = "zombie_running_task"

            if fix_zombie_task(queue_file, zombie, new_status=new_status, fix_reason=fix_reason):
                fixed_zombies += 1

    print("\n📊 修复完成:")
    print(f"   发现僵尸任务: {total_zombies}")
    print(f"   修复任务: {fixed_zombies}")

    if total_zombies > 0:
        print("\n🎯 建议后续操作:")
        print("   1. 检查被修复任务的依赖关系")
        print("   2. 运行队列监控脚本验证修复效果")
        print("   3. 调查导致僵尸任务的根本原因")

    return 0


if __name__ == "__main__":
    sys.exit(main())
