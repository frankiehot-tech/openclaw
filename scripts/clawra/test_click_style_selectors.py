#!/usr/bin/env python3
"""
检查并点击风格选择器入口
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def get_style_selectors():
    """获取风格选择器元素"""
    print("🔧 获取风格选择器元素...")

    cli = DoubaoCLIEnhanced()

    # 专门获取风格选择器元素
    style_check_js = """
    // 获取所有可能的风格选择器入口
    var styleSelectors = [];

    // 方法1: 查找所有有特定类名的元素
    var possibleStyleElements = document.querySelectorAll('[class*="style"], [class*="Style"], button, a, div[onclick]');

    for (var i = 0; i < possibleStyleElements.length; i++) {
        var elem = possibleStyleElements[i];
        if (elem.offsetParent !== null) { // 只取可见元素
            var text = (elem.textContent || elem.innerText || '').trim();
            var className = elem.className || '';
            var ariaLabel = elem.getAttribute('aria-label') || '';

            // 检查是否有风格相关的文本
            var hasStyleText = (
                text.includes('风格') || text.includes('Style') ||
                text.includes('动漫') || text.includes('二次元') ||
                text.includes('写实') || text.includes('艺术') ||
                text.includes('开始') || text.includes('进入') ||
                text.includes('尝试') || text.includes('体验') ||
                text.includes('画') || text.includes('Draw') ||
                text.includes('Paint')
            );

            // 检查是否有风格相关的类名
            var hasStyleClass = (
                className.includes('style') || className.includes('Style') ||
                className.includes('painting') || className.includes('Painting') ||
                className.includes('draw') || className.includes('Draw')
            );

            if (hasStyleText || hasStyleClass || text) {
                var info = {
                    index: i,
                    tagName: elem.tagName,
                    text: text,
                    className: className.substring(0, 100),
                    id: elem.id || '',
                    ariaLabel: ariaLabel,
                    visible: elem.offsetParent !== null,
                    hasStyleText: hasStyleText,
                    hasStyleClass: hasStyleClass,
                    hasText: !!text,
                    isClickable: elem.tagName === 'BUTTON' || elem.tagName === 'A' || elem.hasAttribute('onclick'),
                    element: null // 不存储实际元素
                };

                // 尝试获取更多上下文
                var parent = elem.parentElement;
                if (parent) {
                    var parentText = (parent.textContent || parent.innerText || '').trim();
                    info.parentText = parentText.substring(0, 200);
                    info.hasAIParentText = parentText.includes('AI') || parentText.includes('绘画') || parentText.includes('生成');
                }

                styleSelectors.push(info);
            }
        }
    }

    // 方法2: 查找所有可见的按钮和有文本的元素
    var allVisibleElements = document.querySelectorAll('button, a, div, span');
    for (var i = 0; i < allVisibleElements.length; i++) {
        var elem = allVisibleElements[i];
        if (elem.offsetParent !== null) {
            var text = (elem.textContent || elem.innerText || '').trim();
            if (text && (text.includes('AI绘画') || text.includes('开始绘画') || text.includes('立即体验') ||
                         text.includes('开始创作') || text.includes('尝试生成'))) {
                var alreadyExists = false;
                for (var j = 0; j < styleSelectors.length; j++) {
                    if (styleSelectors[j].element === elem) {
                        alreadyExists = true;
                        break;
                    }
                }

                if (!alreadyExists) {
                    var info = {
                        index: styleSelectors.length,
                        tagName: elem.tagName,
                        text: text,
                        className: (elem.className || '').substring(0, 100),
                        id: elem.id || '',
                        ariaLabel: elem.getAttribute('aria-label') || '',
                        visible: true,
                        hasStyleText: true,
                        hasStyleClass: false,
                        hasText: true,
                        isClickable: elem.tagName === 'BUTTON' || elem.tagName === 'A' || elem.hasAttribute('onclick'),
                        element: null,
                        isHighPriority: true // 高优先级
                    };

                    styleSelectors.push(info);
                }
            }
        }
    }

    // 去重（基于文本和类名）
    var uniqueSelectors = [];
    var seen = new Set();

    for (var i = 0; i < styleSelectors.length; i++) {
        var selector = styleSelectors[i];
        var key = selector.text + '|' + selector.className;
        if (!seen.has(key)) {
            seen.add(key);
            uniqueSelectors.push(selector);
        }
    }

    // 按优先级排序：高优先级 > 有文本 > 可点击
    uniqueSelectors.sort(function(a, b) {
        if (a.isHighPriority && !b.isHighPriority) return -1;
        if (!a.isHighPriority && b.isHighPriority) return 1;
        if (a.hasText && !b.hasText) return -1;
        if (!a.hasText && b.hasText) return 1;
        if (a.isClickable && !b.isClickable) return -1;
        if (!a.isClickable && b.isClickable) return 1;
        return 0;
    });

    // 只返回前30个
    JSON.stringify(uniqueSelectors.slice(0, 30));
    """

    result = cli.execute_javascript_enhanced(style_check_js)
    print(f"获取风格选择器结果: success={result.success}, output={repr(result.output)}")

    if result.success and result.output and result.output != "missing value":
        try:
            selectors = json.loads(cli._clean_js_output(result.output))
            print(f"找到 {len(selectors)} 个可能的风格选择器入口")
            return selectors
        except Exception as e:
            print(f"解析风格选择器失败: {e}")
            return []
    else:
        print(f"获取风格选择器失败")
        return []


def click_style_selector(selector_info):
    """点击风格选择器"""
    print(f"\n🔧 尝试点击: '{selector_info.get('text')}'")

    cli = DoubaoCLIEnhanced()

    # 构建点击脚本
    click_js = f"""
    // 通过文本查找元素并点击
    var clicked = false;
    var targetText = "{selector_info.get('text')}";
    var targetClassName = "{selector_info.get('className')}";

    // 方法1: 通过文本查找
    var elements = document.querySelectorAll('button, a, div, span');
    for (var i = 0; i < elements.length; i++) {{
        var elem = elements[i];
        var text = (elem.textContent || elem.innerText || '').trim();
        if (text === targetText && elem.offsetParent !== null) {{
            console.log('通过文本找到元素: ' + text);
            elem.click();
            clicked = true;
            break;
        }}
    }}

    // 方法2: 通过类名查找
    if (!clicked && targetClassName) {{
        var classElements = document.querySelectorAll('.' + targetClassName.split(' ')[0]);
        for (var i = 0; i < classElements.length; i++) {{
            var elem = classElements[i];
            if (elem.offsetParent !== null) {{
                console.log('通过类名找到元素: ' + targetClassName.split(' ')[0]);
                elem.click();
                clicked = true;
                break;
            }}
        }}
    }}

    clicked ? "点击成功" : "点击失败，未找到元素";
    """

    result = cli.execute_javascript_enhanced(click_js)
    print(f"点击结果: success={result.success}, output={repr(result.output)}")

    # 等待页面响应
    time.sleep(3)

    return result.success and result.output and "点击成功" in result.output


def check_current_page():
    """检查当前页面状态"""
    print("\n🔧 检查页面状态...")

    cli = DoubaoCLIEnhanced()

    check_js = """
    var pageStatus = {
        title: document.title,
        path: window.location.pathname,
        hasPromptInput: (function() {
            var inputs = document.querySelectorAll('textarea, input[type="text"]');
            for (var i = 0; i < inputs.length; i++) {
                var placeholder = inputs[i].placeholder || '';
                if (placeholder.includes('提示词') || placeholder.includes('描述') || placeholder.includes('Prompt')) {
                    return true;
                }
            }
            return false;
        })(),
        hasGenerateButton: (function() {
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var text = (buttons[i].textContent || buttons[i].innerText || '').trim();
                if (text.includes('生成') || text.includes('创作') || text.includes('生成图片')) {
                    return true;
                }
            }
            return false;
        })()
    };
    JSON.stringify(pageStatus);
    """

    result = cli.execute_javascript_enhanced(check_js)
    if result.success and result.output and result.output != "missing value":
        try:
            page_status = json.loads(cli._clean_js_output(result.output))
            print(f"当前页面:")
            print(f"   标题: {page_status.get('title')}")
            print(f"   路径: {page_status.get('path')}")
            print(f"   有提示词输入框: {page_status.get('hasPromptInput')}")
            print(f"   有生成按钮: {page_status.get('hasGenerateButton')}")
            return page_status
        except Exception as e:
            print(f"解析页面状态失败: {e}")
            return None
    else:
        print(f"检查页面状态失败")
        return None


def main():
    """主函数"""
    print("🎯 检查并点击风格选择器入口")
    print("=" * 60)

    try:
        # 1. 首先检查当前页面
        print("\n📋 步骤1: 当前页面状态")
        current_page = check_current_page()
        if not current_page:
            print("❌ 无法获取当前页面状态")
            return 1

        # 2. 获取风格选择器
        print("\n📋 步骤2: 获取风格选择器入口")
        selectors = get_style_selectors()

        if not selectors:
            print("❌ 未找到风格选择器")
            return 1

        # 显示找到的选择器
        print(f"\n📋 找到 {len(selectors)} 个可能的入口:")
        for i, selector in enumerate(selectors[:20]):
            print(f"   {i+1}. '{selector.get('text')}'")
            print(f"       标签: {selector.get('tagName')}, 可点击: {selector.get('isClickable')}")
            print(f"       类名: {selector.get('className')}")
            if selector.get("parentText"):
                print(f"       父元素文本: {selector.get('parentText')[:100]}...")
            print()

        # 3. 尝试点击前几个选择器
        print("\n📋 步骤3: 尝试点击入口")
        success = False
        clicked_index = -1

        for i, selector in enumerate(selectors[:10]):
            if selector.get("isClickable") and selector.get("text"):
                print(f"\n   尝试入口 {i+1}: '{selector.get('text')}'")
                if click_style_selector(selector):
                    clicked_index = i

                    # 检查页面是否有变化
                    print("\n   检查页面变化...")
                    new_page = check_current_page()

                    # 检查是否是AI绘画界面
                    is_ai_interface = new_page and (
                        new_page.get("hasPromptInput") or new_page.get("hasGenerateButton")
                    )

                    if is_ai_interface:
                        print(f"   ✅ 成功进入AI绘画界面!")
                        success = True
                        break
                    else:
                        print(f"   ⚠️  页面变化但可能不是AI绘画界面")
                        print(f"   💡 继续尝试下一个入口...")
                else:
                    print(f"   ❌ 点击失败")

        # 4. 总结
        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)

        if success:
            print("✅ 成功找到并进入AI绘画界面!")
            print(f"\n💡 下一步:")
            print("1. 测试输入提示词功能")
            print("2. 测试图像生成功能")
            print("3. 开始生成Athena IP形象图像")
        else:
            print("❌ 未能进入AI绘画界面")
            print(f"\n🔧 尝试了 {min(10, len(selectors))} 个入口，均未成功")
            print(f"\n💡 建议:")
            print("1. 等待豆包进一步响应")
            print("2. 尝试在聊天中输入'开始AI绘画'或'我要画画'")
            print("3. 可能需要手动在豆包界面中点击AI绘画入口")

        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
