#!/usr/bin/env python3
"""
详细检查页面结构
"""

import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def detailed_page_check():
    """详细检查页面结构"""
    print("🔧 详细检查页面结构...")

    cli = DoubaoCLIEnhanced()

    # 检查页面详细结构
    print("\n📋 详细页面检查")
    detail_js = """
    // 详细页面分析
    var pageAnalysis = {
        // 基本页面信息
        title: document.title,
        url: window.location.href,
        path: window.location.pathname,
        hostname: window.location.hostname,

        // 页面元素统计
        buttons: document.querySelectorAll('button').length,
        links: document.querySelectorAll('a').length,
        inputs: document.querySelectorAll('input').length,
        textareas: document.querySelectorAll('textarea').length,
        images: document.querySelectorAll('img').length,

        // 按钮文本（前20个）
        buttonTexts: [],
        // 输入框placeholder（前10个）
        inputPlaceholders: [],
        // 文本区域placeholder（前10个）
        textareaPlaceholders: [],

        // AI绘画相关特征
        hasAIPaintingKeywords: (function() {
            var pageText = document.body.innerText || '';
            var keywords = ['AI绘画', 'AI创作', '绘画', '画图', '生成', '创作', 'prompt', '提示词'];
            for (var i = 0; i < keywords.length; i++) {
                if (pageText.includes(keywords[i])) {
                    return true;
                }
            }
            return false;
        })(),

        // 是否有生成按钮
        hasGenerateButton: (function() {
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var text = buttons[i].textContent || buttons[i].innerText || '';
                if (text.includes('生成') || text.includes('Generate') ||
                    text.includes('创作') || text.includes('Create')) {
                    return true;
                }
            }
            return false;
        })(),

        // 是否有提示词输入框
        hasPromptInput: (function() {
            var inputs = document.querySelectorAll('input, textarea');
            for (var i = 0; i < inputs.length; i++) {
                var placeholder = inputs[i].placeholder || '';
                if (placeholder.includes('提示词') || placeholder.includes('Prompt') ||
                    placeholder.includes('描述')) {
                    return true;
                }
            }
            return false;
        })()
    };

    // 收集按钮文本
    var buttons = document.querySelectorAll('button');
    for (var i = 0; i < Math.min(buttons.length, 20); i++) {
        var text = buttons[i].textContent || buttons[i].innerText || '';
        if (text.trim()) {
            pageAnalysis.buttonTexts.push(text.substring(0, 100));
        }
    }

    // 收集输入框placeholder
    var inputs = document.querySelectorAll('input');
    for (var i = 0; i < Math.min(inputs.length, 10); i++) {
        var placeholder = inputs[i].placeholder || '';
        if (placeholder) {
            pageAnalysis.inputPlaceholders.push(placeholder);
        }
    }

    // 收集文本区域placeholder
    var textareas = document.querySelectorAll('textarea');
    for (var i = 0; i < Math.min(textareas.length, 10); i++) {
        var placeholder = textareas[i].placeholder || '';
        if (placeholder) {
            pageAnalysis.textareaPlaceholders.push(placeholder);
        }
    }

    // 额外检查：查看页面是否有AI绘画的特定元素
    pageAnalysis.specificElements = {
        // 检查常见AI绘画界面的类名或ID
        hasPaintingCanvas: document.querySelectorAll('canvas, [class*="canvas"], [id*="canvas"]').length > 0,
        hasStyleSelector: document.querySelectorAll('[class*="style"], [class*="Style"], [class*="model"]').length > 0,
        hasSizeSelector: document.querySelectorAll('[class*="size"], [class*="Size"], [class*="dimension"]').length > 0,
        hasQualitySelector: document.querySelectorAll('[class*="quality"], [class*="Quality"]').length > 0
    };

    JSON.stringify(pageAnalysis);
    """

    result = cli.execute_javascript_enhanced(detail_js)
    if result.success and result.output and result.output != "missing value":
        try:
            analysis = json.loads(cli._clean_js_output(result.output))

            print(f"   页面标题: {analysis.get('title')}")
            print(f"   URL: {analysis.get('url')}")
            print(f"   路径: {analysis.get('path')}")
            print(f"   主机名: {analysis.get('hostname')}")
            print(f"   \n   页面元素统计:")
            print(f"     按钮: {analysis.get('buttons')}")
            print(f"     链接: {analysis.get('links')}")
            print(f"     输入框: {analysis.get('inputs')}")
            print(f"     文本区域: {analysis.get('textareas')}")
            print(f"     图像: {analysis.get('images')}")
            print(f"   \n   AI绘画特征:")
            print(f"     包含AI绘画关键词: {analysis.get('hasAIPaintingKeywords')}")
            print(f"     有生成按钮: {analysis.get('hasGenerateButton')}")
            print(f"     有提示词输入框: {analysis.get('hasPromptInput')}")

            print(f"   \n   特定元素检查:")
            print(
                f"     有绘画画布: {analysis.get('specificElements', {}).get('hasPaintingCanvas')}"
            )
            print(
                f"     有风格选择器: {analysis.get('specificElements', {}).get('hasStyleSelector')}"
            )
            print(
                f"     有尺寸选择器: {analysis.get('specificElements', {}).get('hasSizeSelector')}"
            )
            print(
                f"     有质量选择器: {analysis.get('specificElements', {}).get('hasQualitySelector')}"
            )

            print(f"   \n   按钮文本:")
            for i, text in enumerate(analysis.get("buttonTexts", [])):
                print(f"     {i+1}. {text}")

            print(f"   \n   输入框占位符:")
            for i, placeholder in enumerate(analysis.get("inputPlaceholders", [])):
                print(f"     {i+1}. {placeholder}")

            print(f"   \n   文本区域占位符:")
            for i, placeholder in enumerate(analysis.get("textareaPlaceholders", [])):
                print(f"     {i+1}. {placeholder}")

            # 判断是否是AI绘画界面
            is_actual_ai_painting = analysis.get("hasAIPaintingKeywords") and (
                analysis.get("hasGenerateButton") or analysis.get("hasPromptInput")
            )

            print(f"   \n   🔍 判断结果:")
            print(f"     是实际AI绘画界面: {is_actual_ai_painting}")

            return is_actual_ai_painting

        except Exception as e:
            print(f"   解析页面分析失败: {e}")
            import traceback

            traceback.print_exc()
            return False
    else:
        print(f"   获取页面分析失败: success={result.success}, output={repr(result.output)}")
        return False


def main():
    """主函数"""
    print("🎯 详细页面结构检查")
    print("=" * 60)

    try:
        is_ai_painting = detailed_page_check()

        print("\n" + "=" * 60)
        print("📊 检查总结")
        print("=" * 60)

        if is_ai_painting:
            print("✅ 确认在AI绘画界面")
            print("\n💡 下一步:")
            print("1. 修复其他JavaScript代码中的return语句")
            print("2. 测试完整的图像生成流程")
            print("3. 运行Athena图像生成脚本")
        else:
            print("❌ 不在AI绘画界面")
            print("\n🔧 问题分析:")
            print("1. 可能只是打开了AI主页，而不是具体的绘画界面")
            print("2. 需要修复导航逻辑，确保能真正打开AI绘画界面")
            print("3. 可能需要手动在豆包中打开AI绘画界面")
            print("\n💡 解决方案:")
            print("1. 优化_open_painting_interface的导航逻辑")
            print("2. 添加更多的导航方法")
            print("3. 考虑使用URL直接导航到AI绘画页面")

        return 0 if is_ai_painting else 1

    except Exception as e:
        print(f"\n❌ 检查出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
