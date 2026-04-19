#!/usr/bin/env python3
"""
简单的JavaScript执行测试
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def test_simple_js():
    """测试简单的JavaScript执行"""
    print("🔧 测试简单的JavaScript执行...")

    cli = DoubaoCLIEnhanced()

    # 测试1: 最简单的返回
    simple_js = """
    // 简单的测试
    "Hello from Doubao";
    """

    result = cli.execute_javascript_enhanced(simple_js)
    print(f"测试1结果: success={result.success}, output={repr(result.output)}")

    # 测试2: JSON字符串
    json_js = """
    // 返回JSON字符串
    JSON.stringify({test: "value", number: 42});
    """

    result2 = cli.execute_javascript_enhanced(json_js)
    print(f"测试2结果: success={result2.success}, output={repr(result2.output)}")

    # 测试3: 带变量的复杂JSON
    complex_js = """
    // 更复杂的测试
    var data = {
        pageInfo: {
            title: document.title,
            url: window.location.href
        },
        elements: document.querySelectorAll('*').length
    };
    JSON.stringify(data);
    """

    result3 = cli.execute_javascript_enhanced(complex_js)
    print(f"测试3结果: success={result3.success}, output={repr(result3.output)}")

    # 测试4: 使用立即执行函数表达式(IIFE)
    iife_js = """
    (function() {
        var data = {test: "IIFE test"};
        return JSON.stringify(data);
    })()
    """

    result4 = cli.execute_javascript_enhanced(iife_js)
    print(f"测试4结果: success={result4.success}, output={repr(result4.output)}")

    # 测试5: 没有return语句，只有表达式
    expr_js = """
    (function() {
        var data = {test: "expression test"};
        JSON.stringify(data);
    })()
    """

    result5 = cli.execute_javascript_enhanced(expr_js)
    print(f"测试5结果: success={result5.success}, output={repr(result5.output)}")

    return all([result.success, result2.success, result3.success, result4.success, result5.success])


def main():
    """主函数"""
    print("🎯 简单的JavaScript执行测试")
    print("=" * 60)

    try:
        success = test_simple_js()

        print("\n" + "=" * 60)
        print("📊 测试完成")
        print("=" * 60)

        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
