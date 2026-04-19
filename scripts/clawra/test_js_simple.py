#!/usr/bin/env python3
"""
简单JavaScript执行测试
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def test_simple_js():
    """测试简单JavaScript执行"""
    print("=== 简单JavaScript执行测试 ===")

    doubao = DoubaoCLI()

    # 打开页面
    print("打开豆包页面...")
    result = doubao.open_doubao_ai()
    print(f"打开结果: {result}")
    time.sleep(3)

    # 测试1: 返回document.title
    print("\n测试1: 获取document.title")
    js1 = "document.title"
    try:
        result1 = doubao.execute_javascript(1, 1, js1)
        print(f"结果: {result1}")
    except Exception as e:
        print(f"错误: {e}")

    # 测试2: 返回简单字符串
    print("\n测试2: 返回简单字符串")
    js2 = "'测试成功'"
    try:
        result2 = doubao.execute_javascript(1, 1, js2)
        print(f"结果: {result2}")
    except Exception as e:
        print(f"错误: {e}")

    # 测试3: 返回JSON对象
    print("\n测试3: 返回JSON对象")
    js3 = "JSON.stringify({title: document.title, url: window.location.href})"
    try:
        result3 = doubao.execute_javascript(1, 1, js3)
        print(f"结果: {result3}")
    except Exception as e:
        print(f"错误: {e}")

    # 测试4: 检查是否有输入框
    print("\n测试4: 检查输入框")
    js4 = """
    (function() {
        var inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
        return JSON.stringify({
            count: inputs.length,
            types: Array.from(inputs).map(i => i.tagName + (i.type ? ':' + i.type : '')).slice(0, 5)
        });
    })()
    """
    try:
        result4 = doubao.execute_javascript(1, 1, js4)
        print(f"结果: {result4}")
    except Exception as e:
        print(f"错误: {e}")


def main():
    print("豆包JavaScript执行测试")
    print("=" * 60)
    test_simple_js()
    print("\n✅ 测试完成")


if __name__ == "__main__":
    main()
