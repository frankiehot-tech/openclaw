#!/usr/bin/env python3
"""
备份完整性验证脚本
"""

import json
import os
import sqlite3
from pathlib import Path


def verify_backup_integrity(backup_file):
    """验证备份文件完整性"""
    try:
        conn = sqlite3.connect(backup_file)
        cursor = conn.cursor()

        # 1. 检查完整性
        cursor.execute("PRAGMA integrity_check;")
        integrity_result = cursor.fetchone()[0]

        # 2. 检查表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        # 3. 检查数据量
        cursor.execute("SELECT COUNT(*) FROM memory_entries;")
        entry_count = cursor.fetchone()[0]

        conn.close()

        return {
            "backup_file": backup_file,
            "integrity_check": integrity_result,
            "tables_found": len(tables),
            "required_tables": ["memory_entries", "sqlite_sequence"],
            "all_tables_present": all(
                tbl in tables for tbl in ["memory_entries", "sqlite_sequence"]
            ),
            "entry_count": entry_count,
            "valid": integrity_result == "ok" and entry_count > 0,
        }

    except Exception as e:
        return {"backup_file": backup_file, "error": str(e), "valid": False}


def main():
    # 查找最新的备份文件
    backup_dir = Path("./backup/maref")
    backup_files = list(backup_dir.glob("maref_memory_*.db"))

    if not backup_files:
        print("❌ 未找到备份文件")
        return 1

    # 验证每个备份文件
    for backup_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
        result = verify_backup_integrity(str(backup_file))

        print(f"\n验证备份: {backup_file.name}")
        if result["valid"]:
            print(f"  ✅ 完整性检查: {result['integrity_check']}")
            print(f"  ✅ 表数量: {result['tables_found']}")
            print(f"  ✅ 内存条目数: {result['entry_count']}")
        else:
            print(f"  ❌ 验证失败: {result.get('error', '未知错误')}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
