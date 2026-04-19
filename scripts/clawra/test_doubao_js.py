#!/usr/bin/env python3
"""
测试豆包JavaScript执行环境
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def test_js_execution():
    """测试豆包JavaScript执行"""
    print("🔧 测试豆包JavaScript执行环境...")

    cli = DoubaoCLIEnhanced()

    # 测试用例
    test_cases = [
        ("document.title", "获取页面标题"),
        ("document.title.length", "获取标题长度"),
        ("typeof document", "检查document类型"),
        ("window.location.href", "获取当前URL"),
        ("document.querySelectorAll('*').length", "获取页面元素总数"),
        ("document.querySelectorAll('button').length", "获取按钮数量"),
        ("document.querySelectorAll('textarea').length", "获取文本框数量"),
        ("JSON.stringify({test: 'value'})", "测试JSON.stringify"),
        ("'test string'", "返回简单字符串"),
        ("42", "返回数字"),
        ("null", "返回null"),
        ("undefined", "返回undefined"),
        ("(function() { return 'function return'; })()", "立即执行函数"),
        ("try { document.title } catch(e) { 'error: ' + e }", "try-catch测试"),
        ("console.log('test'); 'after console'", "console.log后返回"),
    ]

    results = []

    for js_code, description in test_cases:
        print(f"\n📋 测试: {description}")
        print(f"   JavaScript: {js_code[:80]}{'...' if len(js_code) > 80 else ''}")

        result = cli.execute_javascript_enhanced(js_code)

        print(f"   成功: {result.success}")
        print(f"   输出: {repr(result.output) if result.output else 'None'}")
        print(f"   错误: {result.error_message}")

        results.append(
            {
                "description": description,
                "js_code": js_code,
                "success": result.success,
                "output": result.output,
                "error": result.error_message,
            }
        )

        time.sleep(1)  # 避免请求过快

    # 分析结果
    print("\n" + "=" * 60)
    print("📊 测试结果分析")
    print("=" * 60)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"✅ 成功: {len(successful)}/{len(results)}")
    print(f"❌ 失败: {len(failed)}/{len(results)}")

    # 输出成功的测试
    print("\n✅ 成功的测试:")
    for r in successful:
        print(f"  - {r['description']}: {repr(r['output'])}")

    # 输出失败的测试
    if failed:
        print("\n❌ 失败的测试:")
        for r in failed:
            print(f"  - {r['description']}: {r.get('error', 'No error message')}")

    # 检查"missing value"模式
    missing_value_tests = [r for r in results if r["output"] == "missing value"]
    print(f"\n⚠️  'missing value' 输出: {len(missing_value_tests)}/{len(results)}")
    for r in missing_value_tests:
        print(f"  - {r['description']}")

    # 保存结果
    output_file = Path("test_doubao_js_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "tested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_tests": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "missing_value_count": len(missing_value_tests),
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n💾 结果已保存到: {output_file}")

    return results


def test_element_interaction():
    """测试元素交互"""
    print("\n" + "=" * 60)
    print("🖱️  测试元素交互")
    print("=" * 60)

    cli = DoubaoCLIEnhanced()

    # 测试点击按钮
    click_js = """
    // 尝试点击第一个按钮
    var buttons = document.querySelectorAll('button');
    if (buttons.length > 0) {
        var firstButton = buttons[0];
        var buttonText = firstButton.textContent || firstButton.innerText || '';
        firstButton.click();
        return '点击了按钮: ' + buttonText.substring(0, 50);
    } else {
        return '未找到按钮';
    }
    """

    print("测试点击按钮...")
    result = cli.execute_javascript_enhanced(click_js)
    print(f"  结果: {result.success}, 输出: {repr(result.output)}")

    # 测试查找特定元素
    find_ai_js = """
    // 查找AI相关元素
    var aiElements = [];
    var allElements = document.querySelectorAll('*');

    for (var i = 0; i < Math.min(allElements.length, 100); i++) {
        var elem = allElements[i];
        var text = elem.textContent || elem.innerText || '';
        var className = elem.className || '';
        var id = elem.id || '';

        if (text.includes('AI') || text.includes('绘画') || text.includes('创作') ||
            className.includes('ai') || className.includes('draw') ||
            id.includes('ai') || id.includes('draw')) {
            aiElements.push({
                tag: elem.tagName,
                text: text.substring(0, 100),
                className: className.substring(0, 50),
                id: id
            });
        }
    }

    return JSON.stringify({
        ai_element_count: aiElements.length,
        ai_elements: aiElements.slice(0, 5)  // 只返回前5个
    });
    """

    print("\n测试查找AI元素...")
    result = cli.execute_javascript_enhanced(find_ai_js)
    print(
        f"  结果: {result.success}, 输出: {repr(result.output[:200]) if result.output else 'None'}"
    )

    if result.success and result.output and result.output != "missing value":
        try:
            data = json.loads(result.output)
            print(f"  找到 {data.get('ai_element_count', 0)} 个AI相关元素")
            for elem in data.get("ai_elements", []):
                print(f"    - {elem.get('tag')}: {elem.get('text')}")
        except:
            print("  无法解析JSON输出")


def main():
    """主函数"""
    print("🎯 豆包JavaScript执行环境诊断")
    print("=" * 60)

    # 测试基本JavaScript执行
    results = test_js_execution()

    # 测试元素交互
    test_element_interaction()

    # 总结
    print("\n" + "=" * 60)
    print("📋 诊断总结")
    print("=" * 60)

    # 检查豆包应用是否启用JavaScript权限
    print("\n🔧 豆包JavaScript权限检查:")
    print("1. 打开豆包应用")
    print("2. 菜单栏: 查看 > 开发者")
    print("3. 确保勾选: 允许Apple事件中的JavaScript")
    print("4. 如果未启用，JavaScript执行可能受限")

    # 建议
    print("\n💡 建议:")
    print("1. 确保豆包应用在前台运行")
    print("2. 检查豆包应用版本是否支持JavaScript执行")
    print("3. 如果'缺失值'过多，尝试简化JavaScript代码")
    print("4. 复杂的JavaScript可能需要在页面完全加载后执行")

    return 0


if __name__ == "__main__":
    sys.exit(main())
