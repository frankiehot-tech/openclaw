#!/usr/bin/env python3
"""
MAREF备份恢复测试脚本
验证备份文件的完整性和可恢复性
"""

import json
import os
import sqlite3
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path


def test_database_recovery(db_path):
    """测试数据库恢复功能"""
    print(f"测试数据库恢复: {db_path}")

    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"✅ 数据库连接成功，找到 {len(tables)} 个表: {tables}")

        # 检查表行数
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} 行")

        # 检查数据库完整性
        cursor.execute("PRAGMA integrity_check;")
        integrity_result = cursor.fetchone()[0]

        if integrity_result == "ok":
            print(f"✅ 数据库完整性检查通过: {integrity_result}")
        else:
            print(f"⚠️  数据库完整性警告: {integrity_result}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 数据库恢复测试失败: {e}")
        return False


def test_config_recovery(config_path):
    """测试配置文件恢复功能"""
    print(f"测试配置文件恢复: {config_path}")

    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        return False

    try:
        # 解压配置文件到临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            with tarfile.open(config_path, "r:gz") as tar:
                tar.extractall(temp_dir)

            extracted_files = list(Path(temp_dir).rglob("*"))
            print(f"✅ 配置文件解压成功，包含 {len(extracted_files)} 个文件")

            # 检查关键配置文件
            for file_path in extracted_files:
                if file_path.is_file():
                    rel_path = file_path.relative_to(temp_dir)
                    file_size = file_path.stat().st_size
                    print(f"  - {rel_path} ({file_size} 字节)")

        return True

    except Exception as e:
        print(f"❌ 配置文件恢复测试失败: {e}")
        return False


def test_metadata_recovery(metadata_path):
    """测试备份元数据"""
    print(f"测试备份元数据: {metadata_path}")

    if not os.path.exists(metadata_path):
        print(f"❌ 元数据文件不存在: {metadata_path}")
        return False

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        print(f"✅ 元数据文件解析成功")
        backups = metadata.get("backups", [])
        print(f"  备份记录数量: {len(backups)}")

        for i, backup in enumerate(backups):
            print(f"  备份 #{i+1}:")
            print(f"    - 时间戳: {backup.get('timestamp')}")
            print(f"    - 模式: {backup.get('mode')}")
            print(f"    - 数据库文件: {backup.get('database_file')}")
            print(f"    - 大小: {backup.get('size_mb')} MB")
            print(f"    - 完整性检查: {backup.get('integrity_checked')}")

        return True

    except Exception as e:
        print(f"❌ 元数据恢复测试失败: {e}")
        return False


def simulate_restore(db_path, config_path, restore_dir):
    """模拟恢复过程"""
    print(f"\n模拟恢复过程到目录: {restore_dir}")

    try:
        # 创建恢复目录
        restore_path = Path(restore_dir)
        restore_path.mkdir(parents=True, exist_ok=True)

        # 复制数据库文件
        db_dest = restore_path / "maref_memory_restored.db"
        import shutil

        shutil.copy2(db_path, db_dest)
        print(f"✅ 数据库文件已复制到: {db_dest}")

        # 解压配置文件
        config_restore_dir = restore_path / "config_restored"
        config_restore_dir.mkdir(exist_ok=True)

        with tarfile.open(config_path, "r:gz") as tar:
            tar.extractall(config_restore_dir)

        print(f"✅ 配置文件已解压到: {config_restore_dir}")

        # 验证恢复后的文件
        restored_files = list(restore_path.rglob("*"))
        print(f"恢复完成，共 {len(restored_files)} 个文件:")

        for file_path in restored_files:
            if file_path.is_file():
                rel_path = file_path.relative_to(restore_path)
                file_size = file_path.stat().st_size
                print(f"  - {rel_path} ({file_size} 字节)")

        return True

    except Exception as e:
        print(f"❌ 恢复模拟失败: {e}")
        return False


def main():
    """主函数"""
    print("=== MAREF备份恢复测试 ===\n")

    # 查找最新的备份
    backup_dir = Path("./backup")
    if not backup_dir.exists():
        print("❌ 备份目录不存在，请先运行备份脚本")
        sys.exit(1)

    # 查找最新的数据库备份
    db_backups = list(backup_dir.glob("maref_memory_*.db"))
    if not db_backups:
        print("❌ 未找到数据库备份文件")
        sys.exit(1)

    # 使用最新的备份
    latest_db = sorted(db_backups)[-1]

    # 查找对应的配置文件
    timestamp = (
        latest_db.stem.replace("maref_memory_", "")
        .replace("_daily", "")
        .replace("_weekly", "")
        .replace("_monthly", "")
    )
    config_pattern = f"maref_config_{timestamp}*.tar.gz"
    config_backups = list(backup_dir.glob(config_pattern))

    if config_backups:
        latest_config = config_backups[0]
    else:
        print("⚠️  未找到对应的配置文件，仅测试数据库恢复")
        latest_config = None

    # 测试元数据
    metadata_file = backup_dir / "backup_metadata.json"

    # 执行测试
    tests_passed = 0
    tests_total = 3 if latest_config else 2

    # 测试1: 数据库恢复
    print(f"测试1/{tests_total}: 数据库恢复测试")
    if test_database_recovery(latest_db):
        tests_passed += 1

    # 测试2: 配置文件恢复
    if latest_config:
        print(f"\n测试2/{tests_total}: 配置文件恢复测试")
        if test_config_recovery(latest_config):
            tests_passed += 1

    # 测试3: 元数据恢复
    print(f"\n测试3/{tests_total}: 备份元数据测试")
    if test_metadata_recovery(metadata_file):
        tests_passed += 1

    # 模拟恢复过程
    if tests_passed == tests_total:
        print(f"\n✅ 所有基础测试通过 ({tests_passed}/{tests_total})")

        # 模拟恢复过程
        restore_dir = backup_dir / "restore_simulation"
        print(f"\n--- 开始恢复模拟 ---")
        if simulate_restore(latest_db, latest_config, restore_dir):
            print(f"\n✅ 恢复模拟成功完成")
            print(f"恢复文件位于: {restore_dir.absolute()}")
        else:
            print(f"\n⚠️  恢复模拟过程中遇到问题")
    else:
        print(f"\n❌ 测试失败 ({tests_passed}/{tests_total} 通过)")
        sys.exit(1)

    print(f"\n✅ 备份恢复测试完成")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
