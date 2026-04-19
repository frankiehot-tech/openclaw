#!/usr/bin/env python3
"""
测试修复JavaScript返回语句
"""

import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def test_return_fix():
    """测试修复return语句后的JavaScript执行"""
    print("🔧 测试修复JavaScript返回语句...")

    cli = DoubaoCLIEnhanced()

    # 测试1: 原始的return语句（应该失败）
    print("\n📋 测试1: 原始return语句")
    js1 = "return '测试返回值';"
    result1 = cli.execute_javascript_enhanced(js1)
    print(f"   结果: {repr(result1.output)}")
    print(f"   missing value: {'missing value' in str(result1.output)}")

    # 测试2: 修复后的表达式（应该成功）
    print("\n📋 测试2: 修复为表达式")
    js2 = "'测试返回值';"
    result2 = cli.execute_javascript_enhanced(js2)
    print(f"   结果: {repr(result2.output)}")
    print(f"   missing value: {'missing value' in str(result2.output)}")

    # 测试3: 带try-catch的return语句
    print("\n📋 测试3: 带try-catch的return语句")
    js3 = """
    try {
        return "成功";
    } catch(e) {
        return "失败: " + e.toString();
    }
    """
    result3 = cli.execute_javascript_enhanced(js3)
    print(f"   结果: {repr(result3.output)}")
    print(f"   missing value: {'missing value' in str(result3.output)}")

    # 测试4: 带try-catch的表达式
    print("\n📋 测试4: 带try-catch的表达式")
    js4 = """
    try {
        var result = "成功";
        result;
    } catch(e) {
        "失败: " + e.toString();
    }
    """
    result4 = cli.execute_javascript_enhanced(js4)
    print(f"   结果: {repr(result4.output)}")
    print(f"   missing value: {'missing value' in str(result4.output)}")

    # 测试5: 实际AI绘画导航代码的简化版（带return）
    print("\n📋 测试5: 实际导航代码（带return）")
    js5 = """
    try {
        var searchInput = document.querySelector('input[placeholder*="搜索"]');
        if (searchInput) {
            searchInput.value = "AI绘画";
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
            return "通过搜索打开AI绘画";
        } else {
            return "未找到搜索框";
        }
    } catch (e) {
        return "搜索方法出错: " + e.toString();
    }
    """
    result5 = cli.execute_javascript_enhanced(js5)
    print(f"   结果: {repr(result5.output)}")
    print(f"   missing value: {'missing value' in str(result5.output)}")

    # 测试6: 修复后的实际导航代码（不带return）
    print("\n📋 测试6: 修复后的导航代码（不带return）")
    js6 = """
    try {
        var searchInput = document.querySelector('input[placeholder*="搜索"]');
        if (searchInput) {
            searchInput.value = "AI绘画";
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
            "通过搜索打开AI绘画";
        } else {
            "未找到搜索框";
        }
    } catch (e) {
        "搜索方法出错: " + e.toString();
    }
    """
    result6 = cli.execute_javascript_enhanced(js6)
    print(f"   结果: {repr(result6.output)}")
    print(f"   missing value: {'missing value' in str(result6.output)}")

    print("\n" + "=" * 60)
    print("📊 结果分析")
    print("=" * 60)

    # 分析结果
    missing_count = sum(
        [
            "missing value" in str(result1.output),
            "missing value" in str(result2.output),
            "missing value" in str(result3.output),
            "missing value" in str(result4.output),
            "missing value" in str(result5.output),
            "missing value" in str(result6.output),
        ]
    )

    print(f"总测试数: 6")
    print(f"返回'missing value'的测试: {missing_count}")
    print(f"成功的测试: {6 - missing_count}")

    print("\n💡 结论:")
    if missing_count >= 3:
        print("✅ return语句确实会导致'missing value'问题")
        print("✅ 修复为表达式可以解决这个问题")
    else:
        print("⚠️  测试结果与预期不符，可能需要进一步调查")


def main():
    """主函数"""
    print("🎯 JavaScript返回语句修复测试")
    print("=" * 60)

    try:
        test_return_fix()
        return 0
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
