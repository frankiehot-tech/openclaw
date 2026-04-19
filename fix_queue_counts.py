#!/usr/bin/env python3
"""
队列计数修复脚本 - P0紧急修复任务
功能：修复队列文件中counts与items状态不一致的问题
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# 配置路径
QUEUE_FILE = Path(
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)
BACKUP_SUFFIX = ".backup_fix_counts_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def load_queue():
    """加载队列文件"""
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载队列文件失败: {e}")
        return None


def analyze_counts_discrepancy(queue_data):
    """分析计数不一致问题"""
    print("🔍 队列计数不一致分析")
    print("=" * 60)

    if not queue_data or "items" not in queue_data or "counts" not in queue_data:
        print("❌ 队列数据结构不完整")
        return

    items = queue_data.get("items", {})
    counts = queue_data.get("counts", {})

    print(f"📊 当前计数 (counts):")
    for status, count in counts.items():
        print(f"  {status}: {count}")

    # 计算实际的统计
    actual_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

    for task_id, task in items.items():
        status = task.get("status", "pending")
        if status in actual_counts:
            actual_counts[status] += 1
        else:
            print(f"⚠️  未知状态: {task_id} -> {status}")

    print(f"\n📊 实际统计 (从items计算):")
    for status, count in actual_counts.items():
        print(f"  {status}: {count}")

    # 比较差异
    print(f"\n📈 差异分析:")
    has_discrepancy = False
    for status in actual_counts.keys():
        expected = actual_counts[status]
        actual = counts.get(status, 0)
        if expected != actual:
            has_discrepancy = True
            diff = expected - actual
            print(f"  ⚠️  {status}: 期望 {expected}, 实际 {actual}, 差异 {diff:+d}")
        else:
            print(f"  ✅ {status}: 一致 ({expected})")

    return has_discrepancy, actual_counts


def fix_counts(queue_data, actual_counts):
    """修复计数"""
    print(f"\n🔧 修复计数:")
    print("=" * 40)

    # 更新counts
    queue_data["counts"] = actual_counts
    queue_data["updated_at"] = datetime.now().isoformat()

    print("📝 更新后的计数:")
    for status, count in actual_counts.items():
        print(f"  {status}: {count}")

    return queue_data


def save_queue(queue_data):
    """保存队列文件（先备份）"""
    try:
        # 创建备份
        backup_path = QUEUE_FILE.with_suffix(QUEUE_FILE.suffix + BACKUP_SUFFIX)
        shutil.copy2(QUEUE_FILE, backup_path)
        print(f"📂 已创建备份: {backup_path}")

        # 自定义JSON编码器处理datetime对象
        def datetime_handler(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        # 保存新文件
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False, default=datetime_handler)

        return True
    except Exception as e:
        print(f"❌ 保存队列文件失败: {e}")
        return False


def verify_fix():
    """验证修复结果"""
    print(f"\n✅ 验证修复结果:")
    print("=" * 40)

    queue_data = load_queue()
    if not queue_data:
        print("❌ 无法加载队列文件进行验证")
        return False

    has_discrepancy, actual_counts = analyze_counts_discrepancy(queue_data)

    if has_discrepancy:
        print("❌ 修复后仍然存在不一致")
        return False
    else:
        print("✅ 修复成功，计数完全一致")
        return True


def main():
    """主函数"""
    print("🔧 OpenClaw队列计数修复脚本 - P0紧急修复")
    print("=" * 60)

    # 检查文件
    if not QUEUE_FILE.exists():
        print(f"❌ 队列文件不存在: {QUEUE_FILE}")
        return

    # 加载队列
    queue_data = load_queue()
    if not queue_data:
        return

    # 分析不一致
    has_discrepancy, actual_counts = analyze_counts_discrepancy(queue_data)

    if not has_discrepancy:
        print(f"\n✅ 队列计数已一致，无需修复")
        return

    # 询问用户确认
    print(f"\n❓ 是否执行修复？")
    print(f"  输入 'yes' 执行实际修复")
    print(f"  输入 'no' 或直接回车进行模拟修复")

    try:
        user_input = input("  你的选择: ").strip().lower()
    except EOFError:
        user_input = "no"

    dry_run = user_input != "yes"

    if dry_run:
        print(f"\n📝 模拟修复:")
    else:
        print(f"\n🔧 执行实际修复:")

    # 修复计数
    fixed_data = fix_counts(queue_data.copy() if dry_run else queue_data, actual_counts)

    if not dry_run:
        # 实际保存
        if save_queue(fixed_data):
            print(f"\n✅ 队列文件已修复")

            # 验证修复
            if verify_fix():
                print(f"\n🎉 修复成功完成")
            else:
                print(f"\n⚠️  修复验证失败，请手动检查")
        else:
            print(f"\n❌ 保存修复失败")
    else:
        print(f"\n📝 模拟修复完成（未实际修改文件）")

        # 显示修复后的完整数据结构示例
        print(f"\n🔍 修复后的数据结构示例 (前3个任务):")
        items = list(fixed_data.get("items", {}).items())[:3]
        for task_id, task in items:
            print(f"\n  {task_id[:50]}...")
            print(f"    状态: {task.get('status', 'unknown')}")
            print(f"    标题: {task.get('title', '')[:50]}...")

    # 生成报告
    print(f"\n📊 修复报告:")
    print(f"  文件: {QUEUE_FILE}")
    print(f"  备份: {QUEUE_FILE.name}{BACKUP_SUFFIX}")
    print(f"  操作: {'模拟修复' if dry_run else '实际修复'}")
    print(f"  状态: {'一致' if not has_discrepancy else '已修复' if not dry_run else '模拟修复'}")

    # 建议
    print(f"\n🎯 后续建议:")
    print(f"  1. 监控队列健康度: 使用 analyze_pending_tasks.py 定期检查")
    print(
        f"  2. 修复其他队列文件: 检查 openhuman_aiplan_priority_execution_20260414_deduplicated.json"
    )
    print(f"  3. 建立自动化检查: 将此检查集成到监控系统中")
    print(f"  4. 定期验证: 每周至少验证一次队列数据一致性")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 脚本执行失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
