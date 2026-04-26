#!/usr/bin/env python3
"""
测试链接解析逻辑
"""

import os


def test_resolution():
    """测试各种链接的路径解析"""

    # 模拟索引文件在 docs/audit/summary-index.md
    current_file = "/Volumes/1TB-M2/openclaw/docs/audit/summary-index.md"
    base_dir = "/Volumes/1TB-M2/openclaw/docs"

    test_links = [
        "2026-04/deep-audit-report-2026-04.md",  # 相对路径
        "audit-findings.md",  # 相对路径（同目录）
        "../architecture/system-design.md",  # 传统相对路径
        "./audit-findings.md",  # 当前目录
        "docs/architecture/gstack-integration.md",  # 看起来是绝对路径但其实是相对路径
    ]

    for link in test_links:
        print(f"\n链接: {link}")

        # 当前文件所在目录
        link_file_dir = os.path.dirname(current_file)

        # 尝试解析
        if link.startswith("/"):
            target_path = os.path.join(base_dir, link.lstrip("/"))
        elif link.startswith("./"):
            # 相对于当前文件目录
            target_path = os.path.join(link_file_dir, link[2:])
        elif ".." in link:
            # 相对于当前文件目录（传统相对路径）
            target_path = os.path.join(link_file_dir, link)
        else:
            # 检查是否看起来像相对于docs根目录的路径
            # 如果包含/但不以./或../开头
            if "/" in link:
                # 可能是相对于当前文件目录
                target_path = os.path.join(link_file_dir, link)
                # 也可能是相对于docs根目录
                target_path2 = os.path.join(base_dir, link)
                print(f"  选项1（相对于当前文件目录）: {target_path}")
                print(f"  选项2（相对于docs根目录）: {target_path2}")
                continue
            else:
                # 单个文件，相对于当前文件目录
                target_path = os.path.join(link_file_dir, link)

        target_path = os.path.normpath(target_path)
        exists = os.path.exists(target_path)
        print(f"  解析路径: {target_path}")
        print(f"  文件存在: {exists}")


if __name__ == "__main__":
    test_resolution()
