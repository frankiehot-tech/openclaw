#!/usr/bin/env python3
"""
队列备份文件清理脚本 - P0紧急修复任务
功能：清理.openclaw/plan_queue目录中的旧备份文件，保留关键文件
"""

import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config.paths import PLAN_QUEUE_DIR

    QUEUE_DIR = PLAN_QUEUE_DIR
    print("✅ 使用config.paths模块配置路径")
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    QUEUE_DIR = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
BACKUP_PATTERNS = [
    "*.backup*",
    "*.backup_*",
    "*_backup_*",
    "*_backup",
    "*_fix_backup",
    "*_batch_*_backup*",
]

# 关键文件（必须保留）
CRITICAL_FILES = [
    "openhuman_aiplan_build_priority_20260328.json",
    "openhuman_aiplan_priority_execution_20260414.json",
    "openhuman_aiplan_priority_execution_20260414_deduplicated.json",
    "openhuman_aiplan_codex_audit_20260328.json",
    "openhuman_aiplan_gene_management_20260405.json",
    "openhuman_athena_upgrade_20260326.json",
    "gsd_v2_implementation_20260409_094100.json",
]


def get_file_info(file_path: Path) -> dict:
    """获取文件信息"""
    stat = file_path.stat()
    return {
        "path": file_path,
        "name": file_path.name,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime),
        "is_backup": any(file_path.match(pattern) for pattern in BACKUP_PATTERNS),
    }


def is_critical_file(file_name: str) -> bool:
    """检查是否是关键文件"""
    return file_name in CRITICAL_FILES


def analyze_queue_files():
    """分析队列文件"""
    print("🔍 队列备份文件分析")
    print("=" * 60)

    all_files = []
    for file_path in QUEUE_DIR.iterdir():
        if file_path.is_file():
            file_info = get_file_info(file_path)
            all_files.append(file_info)

    print(f"📁 总文件数: {len(all_files)}")

    # 分类
    critical_files = []
    backup_files = []
    other_files = []

    for file_info in all_files:
        if is_critical_file(file_info["name"]):
            critical_files.append(file_info)
        elif file_info["is_backup"]:
            backup_files.append(file_info)
        else:
            other_files.append(file_info)

    print(f"🔑 关键文件: {len(critical_files)}")
    print(f"📦 备份文件: {len(backup_files)}")
    print(f"📄 其他文件: {len(other_files)}")

    # 备份文件分析
    if backup_files:
        print("\n📊 备份文件分析:")
        backup_files.sort(key=lambda x: x["modified"])

        # 按时间分组（最近7天、30天、更早）
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        recent = []
        older = []
        oldest = []

        for file_info in backup_files:
            if file_info["modified"] > week_ago:
                recent.append(file_info)
            elif file_info["modified"] > month_ago:
                older.append(file_info)
            else:
                oldest.append(file_info)

        print(f"  🕒 最近7天: {len(recent)} 个")
        print(f"  🕐 7-30天: {len(older)} 个")
        print(f"  🕛 30天以上: {len(oldest)} 个")

        # 大小分析
        total_size = sum(f["size"] for f in backup_files)
        print(f"  📏 总大小: {total_size / 1024 / 1024:.2f} MB")

        return backup_files, recent, older, oldest

    return [], [], [], []


def create_backup_plan(backup_files, recent, older, oldest):
    """创建备份清理计划"""
    print("\n📋 清理计划建议:")

    # 建议保留最近7天的备份
    keep_files = recent.copy()

    # 从7-30天的备份中，每个关键文件保留最新的一份
    older_by_base = {}
    for file_info in older:
        base_name = extract_base_name(file_info["name"])
        if base_name not in older_by_base:
            older_by_base[base_name] = []
        older_by_base[base_name].append(file_info)

    for base_name, files in older_by_base.items():
        if files:
            # 保留最新的一份
            files.sort(key=lambda x: x["modified"], reverse=True)
            keep_files.append(files[0])
            if len(files) > 1:
                print(f"  ✅ {base_name}: 保留最新备份，清理 {len(files) - 1} 个旧备份")

    # 30天以上的备份建议全部清理
    delete_candidates = oldest.copy()

    # 从7-30天的备份中，排除要保留的
    for file_info in older:
        if file_info not in keep_files:
            delete_candidates.append(file_info)

    print(f"  📌 建议保留: {len(keep_files)} 个备份文件")
    print(f"  🗑️  建议清理: {len(delete_candidates)} 个备份文件")

    if delete_candidates:
        total_delete_size = sum(f["size"] for f in delete_candidates)
        print(f"  💾 可释放空间: {total_delete_size / 1024 / 1024:.2f} MB")

    return keep_files, delete_candidates


def extract_base_name(filename: str) -> str:
    """从备份文件名提取基础文件名"""
    # 移除常见的备份后缀
    patterns = [
        r"\.backup.*$",
        r"\.backup_.*$",
        r"_backup.*$",
        r"_fix_backup.*$",
        r"_batch_.*_backup.*$",
        r"\.backup_scan_.*$",
    ]

    for pattern in patterns:
        filename = re.sub(pattern, "", filename)

    return filename


def execute_cleanup(delete_candidates, dry_run=True):
    """执行清理操作"""
    print(f"\n{'🔧 执行清理' if not dry_run else '📝 模拟清理'}:")
    print("=" * 40)

    deleted_count = 0
    deleted_size = 0
    errors = []

    for file_info in delete_candidates:
        file_path = file_info["path"]
        file_size = file_info["size"]

        try:
            if not dry_run:
                # 实际删除
                file_path.unlink()
                print(f"  ✅ 已删除: {file_path.name} ({file_size / 1024:.1f} KB)")
            else:
                # 模拟删除
                print(f"  📝 将删除: {file_path.name} ({file_size / 1024:.1f} KB)")

            deleted_count += 1
            deleted_size += file_size

        except Exception as e:
            errors.append(f"{file_path.name}: {e}")
            print(f"  ❌ 删除失败 {file_path.name}: {e}")

    print("\n📊 清理统计:")
    print(f"  处理文件: {len(delete_candidates)} 个")
    print(f"  成功删除: {deleted_count} 个")
    print(f"  释放空间: {deleted_size / 1024 / 1024:.2f} MB")

    if errors:
        print(f"\n⚠️  错误列表 ({len(errors)} 个):")
        for error in errors[:5]:
            print(f"  {error}")
        if len(errors) > 5:
            print(f"  ... 还有 {len(errors) - 5} 个错误")

    return deleted_count, deleted_size, errors


def main():
    """主函数"""
    print("🧹 OpenClaw队列备份文件清理脚本 - P0紧急修复")
    print("=" * 60)

    # 检查目录
    if not QUEUE_DIR.exists():
        print(f"❌ 队列目录不存在: {QUEUE_DIR}")
        return

    # 分析文件
    backup_files, recent, older, oldest = analyze_queue_files()

    if not backup_files:
        print("✅ 没有找到备份文件，无需清理")
        return

    # 创建清理计划
    keep_files, delete_candidates = create_backup_plan(backup_files, recent, older, oldest)

    if not delete_candidates:
        print("✅ 没有需要清理的备份文件")
        return

    # 询问用户确认
    print("\n❓ 是否执行清理？")
    print("  输入 'yes' 执行实际清理")
    print("  输入 'no' 或直接回车进行模拟清理")

    try:
        user_input = input("  你的选择: ").strip().lower()
    except EOFError:
        user_input = "no"

    dry_run = user_input != "yes"

    # 执行清理
    deleted_count, deleted_size, errors = execute_cleanup(delete_candidates, dry_run=dry_run)

    # 最终建议
    print("\n🎯 后续建议:")
    print("  1. 监控队列健康度: python monitor_queue.py")
    print("  2. 优化pending任务: 分析43个pending任务的原因")
    print("  3. 定期清理: 将此脚本添加到cron job")
    print("  4. 改进备份策略: 建立标准化的备份保留策略")


if __name__ == "__main__":
    main()
