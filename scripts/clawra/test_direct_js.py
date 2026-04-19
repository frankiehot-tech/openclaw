#!/usr/bin/env python3
"""
直接测试豆包CLI的JavaScript执行
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def test_direct_js():
    """直接测试JavaScript执行"""
    print("🔧 直接测试豆包CLI JavaScript执行...")

    cli = DoubaoCLI()

    # 测试1: 最简单的JavaScript
    print("\n📋 测试1: 返回字符串")
    result1 = cli.execute_javascript(js_code="'hello world'")
    print(f"   结果: {repr(result1)}")

    # 测试2: 返回数字
    print("\n📋 测试2: 返回数字")
    result2 = cli.execute_javascript(js_code="42")
    print(f"   结果: {repr(result2)}")

    # 测试3: 返回document.title
    print("\n📋 测试3: 返回document.title")
    result3 = cli.execute_javascript(js_code="document.title")
    print(f"   结果: {repr(result3)}")

    # 测试4: 返回JSON.stringify
    print("\n📋 测试4: 返回JSON.stringify")
    result4 = cli.execute_javascript(js_code="JSON.stringify({test: 'value'})")
    print(f"   结果: {repr(result4)}")

    # 测试5: 返回null
    print("\n📋 测试5: 返回null")
    result5 = cli.execute_javascript(js_code="null")
    print(f"   结果: {repr(result5)}")

    # 测试6: 返回undefined
    print("\n📋 测试6: 返回undefined")
    result6 = cli.execute_javascript(js_code="undefined")
    print(f"   结果: {repr(result6)}")

    # 测试7: 使用return语句
    print("\n📋 测试7: 使用return语句")
    result7 = cli.execute_javascript(js_code="return 'test return';")
    print(f"   结果: {repr(result7)}")

    print("\n" + "=" * 60)
    print("📊 结果分析")
    print("=" * 60)

    # 分析"missing value"模式
    missing_results = []
    for i, result in enumerate([result1, result2, result3, result4, result5, result6, result7], 1):
        if "missing value" in str(result):
            missing_results.append(i)

    print(f"包含'missing value'的测试: {missing_results}")

    # 检查JavaScript是否执行成功
    print("\n💡 建议:")
    print("1. 确保豆包应用在前台运行")
    print("2. 检查豆包是否启用了'允许Apple事件中的JavaScript'")
    print("3. 尝试不同的JavaScript返回值格式")


def main():
    """主函数"""
    print("🎯 豆包CLI JavaScript直接测试")
    print("=" * 60)

    try:
        test_direct_js()
        return 0
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
