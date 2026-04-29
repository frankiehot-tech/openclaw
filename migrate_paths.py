#!/usr/bin/env python3
"""
批量迁移路径脚本
将 /Volumes/1TB-M2/openclaw 路径引用更新为 /Volumes/1TB-M2/openclaw
"""

import os
from pathlib import Path

# 配置
OLD_PATH = "/Volumes/1TB-M2/openclaw"
NEW_PATH = "/Volumes/1TB-M2/openclaw"

# 需要处理的文件扩展名
EXTENSIONS = {".py", ".md", ".sh", ".json", ".jsonc", ".yaml", ".yml"}

# 排除的目录
EXCLUDE_DIRS = {
    ".git",
    "backups",
    "tools/claude-code-setup",  # 这个目录内部的路径保持原样（它自己就是迁移的组件）
}


def should_process_file(filepath):
    """检查是否应该处理该文件"""
    path_str = str(filepath)

    # 检查排除目录
    for exclude in EXCLUDE_DIRS:
        if exclude in path_str:
            return False

    # 检查扩展名
    return filepath.suffix in EXTENSIONS


def migrate_file(filepath):
    """迁移单个文件中的路径"""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # 检查是否包含旧路径
        if OLD_PATH not in content:
            return False

        # 替换路径
        new_content = content.replace(OLD_PATH, NEW_PATH)

        # 写回文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"  ❌ 处理失败 {filepath}: {e}")
        return False


def main():
    print("=" * 70)
    print("🚀 批量路径迁移工具")
    print("=" * 70)
    print(f"旧路径: {OLD_PATH}")
    print(f"新路径: {NEW_PATH}")
    print("=" * 70)

    # 统计
    total_files = 0
    migrated_files = 0
    failed_files = 0

    # 遍历目录
    base_path = Path("/Volumes/1TB-M2/openclaw")

    for root, dirs, files in os.walk(base_path):
        # 排除目录
        dirs[:] = [
            d
            for d in dirs
            if d not in EXCLUDE_DIRS and not any(ex in str(Path(root) / d) for ex in EXCLUDE_DIRS)
        ]

        for filename in files:
            filepath = Path(root) / filename

            if not should_process_file(filepath):
                continue

            total_files += 1

            if migrate_file(filepath):
                migrated_files += 1
                print(f"✅ {filepath.relative_to(base_path)}")
            else:
                failed_files += 1

    print("\n" + "=" * 70)
    print("📊 迁移统计")
    print("=" * 70)
    print(f"总文件数: {total_files}")
    print(f"成功迁移: {migrated_files}")
    print(f"失败/无需迁移: {failed_files}")
    print("=" * 70)


if __name__ == "__main__":
    main()
