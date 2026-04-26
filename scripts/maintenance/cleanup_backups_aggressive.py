#!/usr/bin/env python3
"""
队列备份文件激进清理脚本 - P0紧急修复任务
功能：为每个基础队列文件保留最新的5个备份，删除其他备份
"""

import json
import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config.paths import OPENCLAW_DIR, PLAN_QUEUE_DIR, ROOT_DIR

    QUEUE_DIR = PLAN_QUEUE_DIR
    BACKUP_DIR = OPENCLAW_DIR / "backups"
    print(f"✅ 使用config.paths模块配置路径")
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    QUEUE_DIR = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
    BACKUP_DIR = Path("/Volumes/1TB-M2/openclaw/.openclaw/backups")

BACKUPS_TO_KEEP = 5  # 每个基础文件保留的备份数量

# 关键文件（必须保留）
CRITICAL_FILES = [
    "openhuman_aiplan_build_priority_20260328.json",
    "openhuman_aiplan_priority_execution_20260414.json",
    "openhuman_aiplan_priority_execution_20260414_deduplicated.json",
    "openhuman_aiplan_codex_audit_20260328.json",
    "openhuman_aiplan_gene_management_20260405.json",
    "openhuman_athena_upgrade_20260328.json",
    "gsd_v2_implementation_20260409_094100.json",
]


def extract_base_name(filename: str) -> str:
    """从备份文件名提取基础文件名"""
    # 基础文件模式
    base_patterns = [r"^(openhuman_aiplan_.*?\.json)", r"^(gsd_.*?\.json)", r"^(.*?\.json)"]

    for pattern in base_patterns:
        match = re.match(pattern, filename)
        if match:
            return match.group(1)

    # 如果无法提取，返回原文件名
    return filename


def is_backup_file(filename: str) -> bool:
    """检查是否是备份文件"""
    backup_patterns = [r"\.backup", r"_backup", r"\.bak", r"\.old", r"_old", r"\.prev", r"_prev"]

    # 排除关键文件
    if filename in CRITICAL_FILES:
        return False

    return any(pattern in filename for pattern in backup_patterns)


def get_backup_groups():
    """将备份文件按基础文件分组"""
    backup_groups = defaultdict(list)

    for file_path in QUEUE_DIR.iterdir():
        if not file_path.is_file():
            continue

        filename = file_path.name

        # 跳过关键文件
        if filename in CRITICAL_FILES:
            continue

        # 检查是否是备份文件
        if is_backup_file(filename):
            base_name = extract_base_name(filename)
            if base_name:
                stat = file_path.stat()
                backup_groups[base_name].append(
                    {
                        "path": file_path,
                        "name": filename,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                    }
                )

    return backup_groups


def analyze_backup_groups(backup_groups):
    """分析备份分组"""
    print("🔍 备份文件分组分析")
    print("=" * 60)

    total_backups = sum(len(files) for files in backup_groups.values())
    total_groups = len(backup_groups)

    print(f"📊 总体统计:")
    print(f"  备份文件总数: {total_backups}")
    print(f"  基础文件组数: {total_groups}")

    # 显示每个组的情况
    print(f"\n📋 分组详情（前10组）:")
    for i, (base_name, files) in enumerate(list(backup_groups.items())[:10]):
        files.sort(key=lambda x: x["modified"], reverse=True)
        newest = files[0]["modified"].strftime("%Y-%m-%d %H:%M")
        oldest = files[-1]["modified"].strftime("%Y-%m-%d %H:%M")
        total_size = sum(f["size"] for f in files) / 1024 / 1024

        print(f"  {i+1}. {base_name}:")
        print(f"     备份数: {len(files)}")
        print(f"     最新: {newest}")
        print(f"     最旧: {oldest}")
        print(f"     总大小: {total_size:.2f} MB")

    if total_groups > 10:
        print(f"  ... 还有 {total_groups - 10} 个组")

    return total_backups, total_groups


def create_cleanup_plan(backup_groups):
    """创建清理计划"""
    print(f"\n📋 清理计划:")
    print("=" * 40)

    keep_files = []
    delete_candidates = []

    for base_name, files in backup_groups.items():
        # 按修改时间排序（最新的在前）
        files.sort(key=lambda x: x["modified"], reverse=True)

        # 保留最新的 BACKUPS_TO_KEEP 个文件
        to_keep = files[:BACKUPS_TO_KEEP]
        to_delete = files[BACKUPS_TO_KEEP:]

        keep_files.extend(to_keep)
        delete_candidates.extend(to_delete)

        if to_delete:
            print(f"  📁 {base_name}:")
            print(f"     保留: {len(to_keep)} 个备份")
            print(f"     清理: {len(to_delete)} 个备份")
            if to_delete:
                delete_size = sum(f["size"] for f in to_delete) / 1024 / 1024
                print(f"     释放空间: {delete_size:.2f} MB")

    print(f"\n📊 总体计划:")
    print(f"  保留备份: {len(keep_files)} 个")
    print(f"  清理备份: {len(delete_candidates)} 个")

    if delete_candidates:
        total_delete_size = sum(f["size"] for f in delete_candidates) / 1024 / 1024
        print(f"  总释放空间: {total_delete_size:.2f} MB")

    return keep_files, delete_candidates


def execute_cleanup(delete_candidates, dry_run=True):
    """执行清理操作"""
    print(f"\n{'🔧 执行清理' if not dry_run else '📝 模拟清理'}:")
    print("=" * 40)

    deleted_count = 0
    deleted_size = 0
    errors = []

    # 按文件大小排序（先删除小的，后删除大的）
    delete_candidates.sort(key=lambda x: x["size"])

    for file_info in delete_candidates:
        file_path = file_info["path"]
        file_size = file_info["size"]

        try:
            if not dry_run:
                # 实际删除
                file_path.unlink()
                status = "✅ 已删除"
            else:
                # 模拟删除
                status = "📝 将删除"

            print(f"  {status}: {file_path.name} ({file_size / 1024:.1f} KB)")

            deleted_count += 1
            deleted_size += file_size

        except Exception as e:
            errors.append(f"{file_path.name}: {e}")
            print(f"  ❌ 删除失败 {file_path.name}: {e}")

    print(f"\n📊 清理统计:")
    print(f"  计划清理: {len(delete_candidates)} 个")
    print(f"  实际清理: {deleted_count} 个")
    print(f"  释放空间: {deleted_size / 1024 / 1024:.2f} MB")

    if errors:
        print(f"\n⚠️  错误列表 ({len(errors)} 个):")
        for error in errors[:5]:
            print(f"  {error}")
        if len(errors) > 5:
            print(f"  ... 还有 {len(errors)-5} 个错误")

    return deleted_count, deleted_size, errors


def main():
    """主函数"""
    print("🧹 OpenClaw队列备份文件激进清理脚本")
    print("=" * 60)
    print(f"配置: 每个基础文件保留 {BACKUPS_TO_KEEP} 个最新备份")
    print()

    # 检查目录
    if not QUEUE_DIR.exists():
        print(f"❌ 队列目录不存在: {QUEUE_DIR}")
        return

    # 获取备份分组
    backup_groups = get_backup_groups()

    if not backup_groups:
        print("✅ 没有找到备份文件，无需清理")
        return

    # 分析备份
    total_backups, total_groups = analyze_backup_groups(backup_groups)

    if total_backups <= BACKUPS_TO_KEEP * total_groups:
        print(f"\n✅ 备份数量合理，无需清理")
        print(f"  当前: {total_backups} 个备份")
        print(f"  目标: ≤ {BACKUPS_TO_KEEP * total_groups} 个备份")
        return

    # 创建清理计划
    keep_files, delete_candidates = create_cleanup_plan(backup_groups)

    if not delete_candidates:
        print("✅ 没有需要清理的备份文件")
        return

    # 询问用户确认
    print(f"\n❓ 是否执行清理？")
    print(f"  输入 'yes' 执行实际清理")
    print(f"  输入 'no' 或直接回车进行模拟清理")

    try:
        user_input = input("  你的选择: ").strip().lower()
    except EOFError:
        user_input = "no"

    dry_run = user_input != "yes"

    # 执行清理
    deleted_count, deleted_size, errors = execute_cleanup(delete_candidates, dry_run=dry_run)

    # 最终建议
    print(f"\n🎯 后续建议:")
    print(f"  1. 建立备份保留策略: 定期清理旧备份")
    print(f"  2. 监控队列健康度: 分析pending任务原因")
    print(f"  3. 优化pending比例: 当前build队列49.4% pending")
    print(f"  4. 将此脚本添加到cron job自动清理")


if __name__ == "__main__":
    main()
