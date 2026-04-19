#!/usr/bin/env python3
"""
测试路径解析逻辑
"""

import os
from pathlib import Path


def test_path_resolution():
    """测试各种链接的路径解析"""

    # 模拟的测试用例
    test_cases = [
        {
            "current_file": "/Volumes/1TB-M2/openclaw/docs/user/claude-code-config.md",
            "link": "user/contributing.md",
            "expected": "/Volumes/1TB-M2/openclaw/docs/user/contributing.md",
            "description": "user/contributing.md from docs/user/claude-code-config.md",
        },
        {
            "current_file": "/Volumes/1TB-M2/openclaw/docs/user/claude-code-config.md",
            "link": "contributing.md",
            "expected": "/Volumes/1TB-M2/openclaw/docs/user/contributing.md",
            "description": "contributing.md from docs/user/claude-code-config.md",
        },
        {
            "current_file": "/Volumes/1TB-M2/openclaw/docs/user/getting-started.md",
            "link": "architecture/system-design.md",
            "expected": "/Volumes/1TB-M2/openclaw/docs/architecture/system-design.md",
            "description": "architecture/system-design.md from docs/user/getting-started.md",
        },
        {
            "current_file": "/Volumes/1TB-M2/openclaw/docs/user/contributing.md",
            "link": "../architecture/system-architecture.md",
            "expected": "/Volumes/1TB-M2/openclaw/docs/architecture/system-architecture.md",
            "description": "../architecture/system-architecture.md from docs/user/contributing.md",
        },
    ]

    base_dir = "/Volumes/1TB-M2/openclaw/docs"

    for test_case in test_cases:
        current_file = test_case["current_file"]
        link = test_case["link"]
        expected = test_case["expected"]
        description = test_case["description"]

        # 方法1：相对于当前文件目录
        link_file_dir = os.path.dirname(current_file)
        if link.startswith("/"):
            target_path = os.path.join(base_dir, link.lstrip("/"))
        else:
            target_path = os.path.join(link_file_dir, link)

        # 规范化路径
        target_path = os.path.normpath(target_path)

        # 检查文件是否存在
        exists = os.path.exists(target_path)

        print(f"测试: {description}")
        print(f"  链接: {link}")
        print(f"  当前文件目录: {link_file_dir}")
        print(f"  解析路径: {target_path}")
        print(f"  预期路径: {expected}")
        print(f"  文件存在: {exists}")
        print(f"  匹配预期: {'✅' if target_path == expected else '❌'}")

        # 检查预期的文件是否存在
        expected_exists = os.path.exists(expected)
        print(f"  预期文件存在: {expected_exists}")
        print()


if __name__ == "__main__":
    test_path_resolution()
