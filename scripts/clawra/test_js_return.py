#!/usr/bin/env python3
"""
测试JavaScript返回格式
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def test_js_return_formats():
    """测试不同的JavaScript返回格式"""
    print("🔧 测试JavaScript返回格式...")

    cli = DoubaoCLI()

    # 测试不同的返回格式
    tests = [
        ("直接字符串", "'hello world'"),
        ("直接数字", "42"),
        ("表达式", "'test' + ' string'"),
        ("对象字面量", "{result: 'test', value: 42}"),
        ("JSON.stringify", "JSON.stringify({test: 'value'})"),
        ("带return语句", "return 'with return';"),
        ("多行表达式", "'first line'; 'second line'; 'final result'"),
        ("多行带变量", "var x = 'test'; x + ' value'"),
        ("函数调用", "(function() { return 'from function'; })()"),
        ("立即执行函数返回值", "(function() { return 'IIFE result'; })()"),
    ]

    results = []
    for name, js_code in tests:
        print(f"\n📋 {name}")
        print(f"   JavaScript: {js_code}")
        result = cli.execute_javascript(js_code=js_code)
        print(f"   结果: {repr(result)}")

        results.append(
            {
                "name": name,
                "js_code": js_code,
                "result": result,
                "has_missing_value": "missing value" in str(result),
            }
        )

    print("\n" + "=" * 60)
    print("📊 结果分析")
    print("=" * 60)

    missing = [r["name"] for r in results if r["has_missing_value"]]
    working = [r["name"] for r in results if not r["has_missing_value"]]

    print(f"✅ 工作正常的格式 ({len(working)}):")
    for name in working:
        print(f"  - {name}")

    print(f"\n❌ 返回'missing value'的格式 ({len(missing)}):")
    for name in missing:
        print(f"  - {name}")

    print("\n💡 发现:")
    print("1. 使用'return'语句会导致'missing value'")
    print("2. 多行JavaScript的最后一行应该是表达式")
    print("3. 函数调用如果返回undefined也会导致'missing value'")


def main():
    """主函数"""
    print("🎯 JavaScript返回格式测试")
    print("=" * 60)

    try:
        test_js_return_formats()
        return 0
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
