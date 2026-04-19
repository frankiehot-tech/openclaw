#!/usr/bin/env python3
"""
查找真正的可点击元素（按钮、链接）
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def find_real_clickable_elements():
    """查找真正的可点击元素"""
    print("🔧 查找真正的可点击元素...")

    cli = DoubaoCLIEnhanced()

    # 专门查找真正的可点击元素
    find_js = """
    // 查找真正的可点击元素
    var clickableElements = {
        buttons: [],
        links: [],
        clickableDivs: [],
        allClickable: []
    };

    // 1. 所有按钮
    var buttons = document.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        if (btn.offsetParent !== null) { // 可见
            var info = {
                type: 'button',
                index: i,
                tagName: btn.tagName,
                text: (btn.textContent || btn.innerText || '').trim(),
                className: btn.className || '',
                id: btn.id || '',
                ariaLabel: btn.getAttribute('aria-label') || '',
                disabled: btn.disabled,
                visible: true,
                hasStyleKeyword: false,
                isHighPriority: false
            };

            // 检查是否与AI绘画相关
            var textLower = info.text.toLowerCase();
            var classNameLower = info.className.toLowerCase();
            var ariaLabelLower = info.ariaLabel.toLowerCase();

            if (textLower.includes('绘画') || textLower.includes('画图') ||
                textLower.includes('draw') || textLower.includes('paint') ||
                textLower.includes('生成') || textLower.includes('创作') ||
                textLower.includes('开始') || textLower.includes('体验') ||
                textLower.includes('尝试') || textLower.includes('进入') ||
                textLower.includes('style') || textLower.includes('风格')) {
                info.hasStyleKeyword = true;
                info.isHighPriority = true;
            }

            clickableElements.buttons.push(info);
            clickableElements.allClickable.push(info);
        }
    }

    // 2. 所有链接
    var links = document.querySelectorAll('a');
    for (var i = 0; i < links.length; i++) {
        var link = links[i];
        if (link.offsetParent !== null) {
            var info = {
                type: 'link',
                index: i,
                tagName: link.tagName,
                text: (link.textContent || link.innerText || '').trim(),
                href: link.href || '',
                className: link.className || '',
                id: link.id || '',
                ariaLabel: link.getAttribute('aria-label') || '',
                visible: true,
                hasStyleKeyword: false,
                isHighPriority: false
            };

            // 检查是否与AI绘画相关
            var textLower = info.text.toLowerCase();
            var classNameLower = info.className.toLowerCase();

            if (textLower.includes('绘画') || textLower.includes('画图') ||
                textLower.includes('draw') || textLower.includes('paint') ||
                textLower.includes('生成') || textLower.includes('创作') ||
                textLower.includes('开始') || textLower.includes('体验') ||
                textLower.includes('尝试') || textLower.includes('进入')) {
                info.hasStyleKeyword = true;
                info.isHighPriority = true;
            }

            clickableElements.links.push(info);
            clickableElements.allClickable.push(info);
        }
    }

    // 3. 所有可点击的div和span
    var clickableDivs = document.querySelectorAll('div[onclick], span[onclick], [role="button"], [class*="btn"], [class*="Btn"], [class*="button"], [class*="Button"]');
    for (var i = 0; i < clickableDivs.length; i++) {
        var elem = clickableDivs[i];
        if (elem.offsetParent !== null) {
            var info = {
                type: 'clickable-element',
                index: i,
                tagName: elem.tagName,
                text: (elem.textContent || elem.innerText || '').trim(),
                className: elem.className || '',
                id: elem.id || '',
                ariaLabel: elem.getAttribute('aria-label') || '',
                role: elem.getAttribute('role') || '',
                hasOnClick: elem.hasAttribute('onclick'),
                visible: true,
                hasStyleKeyword: false,
                isHighPriority: false
            };

            // 检查是否与AI绘画相关
            var textLower = info.text.toLowerCase();
            var classNameLower = info.className.toLowerCase();

            if (textLower.includes('绘画') || textLower.includes('画图') ||
                textLower.includes('draw') || textLower.includes('paint') ||
                textLower.includes('生成') || textLower.includes('创作') ||
                textLower.includes('开始') || textLower.includes('体验') ||
                textLower.includes('尝试') || textLower.includes('进入') ||
                classNameLower.includes('btn') || classNameLower.includes('button')) {
                info.hasStyleKeyword = true;
                info.isHighPriority = true;
            }

            clickableElements.clickableDivs.push(info);
            clickableElements.allClickable.push(info);
        }
    }

    // 按优先级排序
    clickableElements.allClickable.sort(function(a, b) {
        if (a.isHighPriority && !b.isHighPriority) return -1;
        if (!a.isHighPriority && b.isHighPriority) return 1;
        if (a.text.length > 0 && b.text.length === 0) return -1;
        if (a.text.length === 0 && b.text.length > 0) return 1;
        return 0;
    });

    JSON.stringify(clickableElements);
    """

    result = cli.execute_javascript_enhanced(find_js)
    print(
        f"查找结果: success={result.success}, output={repr(result.output[:200]) if result.output else 'None'}"
    )

    if result.success and result.output and result.output != "missing value":
        try:
            elements = json.loads(cli._clean_js_output(result.output))
            print(f"找到 {len(elements.get('allClickable', []))} 个可点击元素")
            print(f"  按钮: {len(elements.get('buttons', []))}")
            print(f"  链接: {len(elements.get('links', []))}")
            print(f"  可点击元素: {len(elements.get('clickableDivs', []))}")

            return elements
        except Exception as e:
            print(f"解析结果失败: {e}")
            return None
    else:
        print(f"查找可点击元素失败")
        return None


def analyze_and_click(elements):
    """分析和点击最可能的元素"""
    if not elements:
        print("❌ 无元素可分析")
        return False

    clickable = elements.get("allClickable", [])
    if not clickable:
        print("❌ 无可点击元素")
        return False

    print(f"\n📋 前10个可点击元素:")
    for i, elem in enumerate(clickable[:10]):
        print(f"  {i+1}. [{elem.get('type')}] '{elem.get('text')[:50]}'")
        print(f"      类名: {elem.get('className', '')[:50]}")
        print(f"      ID: {elem.get('id')}")
        print(f"      aria-label: {elem.get('ariaLabel')}")
        print(f"      高优先级: {elem.get('isHighPriority')}")
        print()

    # 尝试点击高优先级元素
    cli = DoubaoCLIEnhanced()

    for i, elem in enumerate(clickable):
        if elem.get("isHighPriority") and elem.get("text"):
            print(f"\n🔧 尝试点击高优先级元素 {i+1}: '{elem.get('text')}'")

            # 构建点击脚本
            click_js = f"""
            // 点击特定元素
            var clicked = false;
            var targetText = "{elem.get('text')}";
            var targetType = "{elem.get('type')}";

            if (targetType === 'button') {{
                var buttons = document.querySelectorAll('button');
                for (var j = 0; j < buttons.length; j++) {{
                    var btn = buttons[j];
                    if (btn.offsetParent !== null) {{
                        var text = (btn.textContent || btn.innerText || '').trim();
                        if (text === targetText) {{
                            console.log('点击按钮: ' + text);
                            btn.click();
                            clicked = true;
                            break;
                        }}
                    }}
                }}
            }} else if (targetType === 'link') {{
                var links = document.querySelectorAll('a');
                for (var j = 0; j < links.length; j++) {{
                    var link = links[j];
                    if (link.offsetParent !== null) {{
                        var text = (link.textContent || link.innerText || '').trim();
                        if (text === targetText) {{
                            console.log('点击链接: ' + text);
                            link.click();
                            clicked = true;
                            break;
                        }}
                    }}
                }}
            }} else if (targetType === 'clickable-element') {{
                // 尝试通过文本查找
                var allElements = document.querySelectorAll('div, span');
                for (var j = 0; j < allElements.length; j++) {{
                    var el = allElements[j];
                    if (el.offsetParent !== null) {{
                        var text = (el.textContent || el.innerText || '').trim();
                        if (text === targetText) {{
                            console.log('点击元素: ' + text);
                            el.click();
                            clicked = true;
                            break;
                        }}
                    }}
                }}
            }}

            clicked ? "点击成功" : "点击失败";
            """

            result = cli.execute_javascript_enhanced(click_js)
            print(f"点击结果: success={result.success}, output={repr(result.output)}")

            # 等待页面响应
            time.sleep(3)

            # 检查页面是否有变化
            check_js = """
            var pageCheck = {
                title: document.title,
                path: window.location.pathname,
                hasChanged: window.location.pathname !== window.location.pathname // 简化检查
            };
            JSON.stringify(pageCheck);
            """

            check_result = cli.execute_javascript_enhanced(check_js)
            if (
                check_result.success
                and check_result.output
                and check_result.output != "missing value"
            ):
                try:
                    page_check = json.loads(cli._clean_js_output(check_result.output))
                    print(
                        f"页面变化检查: 标题='{page_check.get('title')}', 路径='{page_check.get('path')}'"
                    )
                except Exception as e:
                    print(f"解析页面检查失败: {e}")

            return True  # 只尝试第一个高优先级元素

    print("❌ 没有高优先级元素可点击")
    return False


def main():
    """主函数"""
    print("🎯 查找真正的可点击元素测试")
    print("=" * 60)

    try:
        # 1. 查找可点击元素
        print("\n📋 步骤1: 查找可点击元素")
        elements = find_real_clickable_elements()

        if not elements:
            print("❌ 无法找到可点击元素")
            return 1

        # 2. 分析和点击
        print("\n📋 步骤2: 分析和点击")
        click_success = analyze_and_click(elements)

        print("\n" + "=" * 60)
        print("📊 测试完成")
        print("=" * 60)

        return 0 if click_success else 1

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
