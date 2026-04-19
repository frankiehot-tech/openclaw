#!/usr/bin/env python3
"""
检查/create-image页面的AI绘画界面
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def check_create_image_page():
    """检查/create-image页面"""
    print("🔧 检查/create-image页面...")

    cli = DoubaoCLIEnhanced()

    # 详细检查AI绘画生成界面
    check_js = """
    // 详细检查AI绘画生成界面
    var pageAnalysis = {
        // 页面基本信息
        pageInfo: {
            title: document.title,
            url: window.location.href,
            path: window.location.pathname
        },

        // 输入框
        inputElements: [],

        // 按钮
        buttonElements: [],

        // 选择器
        selectorElements: [],

        // 其他可能元素
        otherElements: [],

        // 关键元素检测
        keyFeatures: {
            hasPromptInput: false,
            hasGenerateButton: false,
            hasStyleSelector: false,
            hasSizeSelector: false,
            hasModelSelector: false,
            hasCanvasOrPreview: false,
            hasImageGallery: false
        }
    };

    // 检查输入框
    var inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
    for (var i = 0; i < Math.min(inputs.length, 20); i++) {
        var input = inputs[i];
        var info = {
            type: 'input',
            tagName: input.tagName,
            inputType: input.type || '',
            placeholder: input.placeholder || '',
            value: input.value || '',
            className: input.className || '',
            id: input.id || '',
            ariaLabel: input.getAttribute('aria-label') || '',
            visible: input.offsetParent !== null,
            isPromptInput: false
        };

        // 检查是否是提示词输入框
        var placeholderLower = info.placeholder.toLowerCase();
        if (placeholderLower.includes('提示词') || placeholderLower.includes('prompt') ||
            placeholderLower.includes('描述') || placeholderLower.includes('输入') ||
            placeholderLower.includes('写点什么')) {
            info.isPromptInput = true;
            pageAnalysis.keyFeatures.hasPromptInput = true;
        }

        pageAnalysis.inputElements.push(info);
    }

    // 检查按钮
    var buttons = document.querySelectorAll('button, [role="button"]');
    for (var i = 0; i < Math.min(buttons.length, 30); i++) {
        var btn = buttons[i];
        var info = {
            type: 'button',
            tagName: btn.tagName,
            text: (btn.textContent || btn.innerText || '').trim(),
            className: btn.className || '',
            id: btn.id || '',
            ariaLabel: btn.getAttribute('aria-label') || '',
            role: btn.getAttribute('role') || '',
            disabled: btn.disabled,
            visible: btn.offsetParent !== null,
            isGenerateButton: false
        };

        // 检查是否是生成按钮
        var textLower = info.text.toLowerCase();
        if (textLower.includes('生成') || textLower.includes('创作') || textLower.includes('开始') ||
            textLower.includes('draw') || textLower.includes('paint') || textLower.includes('create') ||
            textLower.includes('generate')) {
            info.isGenerateButton = true;
            pageAnalysis.keyFeatures.hasGenerateButton = true;
        }

        pageAnalysis.buttonElements.push(info);
    }

    // 检查选择器
    var selectors = document.querySelectorAll('select, [role="listbox"], [class*="select"], [class*="Select"], [class*="dropdown"], [class*="Dropdown"]');
    for (var i = 0; i < Math.min(selectors.length, 10); i++) {
        var selector = selectors[i];
        var info = {
            type: 'selector',
            tagName: selector.tagName,
            text: (selector.textContent || selector.innerText || '').trim(),
            className: selector.className || '',
            id: selector.id || '',
            ariaLabel: selector.getAttribute('aria-label') || '',
            role: selector.getAttribute('role') || '',
            visible: selector.offsetParent !== null,
            selectorType: 'unknown'
        };

        // 确定选择器类型
        var textLower = info.text.toLowerCase();
        var classNameLower = info.className.toLowerCase();
        var ariaLabelLower = info.ariaLabel.toLowerCase();

        if (textLower.includes('风格') || classNameLower.includes('style') || ariaLabelLower.includes('style')) {
            info.selectorType = 'style';
            pageAnalysis.keyFeatures.hasStyleSelector = true;
        } else if (textLower.includes('尺寸') || textLower.includes('大小') || classNameLower.includes('size') || ariaLabelLower.includes('size')) {
            info.selectorType = 'size';
            pageAnalysis.keyFeatures.hasSizeSelector = true;
        } else if (textLower.includes('模型') || classNameLower.includes('model') || ariaLabelLower.includes('model')) {
            info.selectorType = 'model';
            pageAnalysis.keyFeatures.hasModelSelector = true;
        }

        pageAnalysis.selectorElements.push(info);
    }

    // 检查画布和预览
    var canvasElements = document.querySelectorAll('canvas, [class*="canvas"], [class*="Canvas"], [class*="preview"], [class*="Preview"], [class*="image"], [class*="Image"]');
    for (var i = 0; i < Math.min(canvasElements.length, 10); i++) {
        var canvas = canvasElements[i];
        var info = {
            type: 'canvas/preview',
            tagName: canvas.tagName,
            className: canvas.className || '',
            id: canvas.id || '',
            ariaLabel: canvas.getAttribute('aria-label') || '',
            visible: canvas.offsetParent !== null
        };
        pageAnalysis.otherElements.push(info);
        pageAnalysis.keyFeatures.hasCanvasOrPreview = true;
    }

    // 检查图像库
    var images = document.querySelectorAll('img');
    if (images.length > 0) {
        pageAnalysis.keyFeatures.hasImageGallery = true;
    }

    JSON.stringify(pageAnalysis);
    """

    result = cli.execute_javascript_enhanced(check_js)
    print(
        f"页面分析结果: success={result.success}, output={repr(result.output[:200]) if result.output else 'None'}"
    )

    if result.success and result.output and result.output != "missing value":
        try:
            analysis = json.loads(cli._clean_js_output(result.output))
            return analysis
        except Exception as e:
            print(f"解析页面分析失败: {e}")
            return None
    else:
        print(f"获取页面分析失败")
        return None


def analyze_page(analysis):
    """分析页面内容"""
    if not analysis:
        print("❌ 无分析数据")
        return False

    print(f"\n📋 页面基本信息:")
    page_info = analysis.get("pageInfo", {})
    print(f"   标题: {page_info.get('title')}")
    print(f"   路径: {page_info.get('path')}")
    print(f"   URL: {page_info.get('url')}")

    print(f"\n📋 关键元素检测:")
    key_features = analysis.get("keyFeatures", {})
    for key, value in key_features.items():
        print(f"   {key}: {value}")

    print(f"\n📋 元素统计:")
    print(f"   输入框: {len(analysis.get('inputElements', []))}")
    print(f"   按钮: {len(analysis.get('buttonElements', []))}")
    print(f"   选择器: {len(analysis.get('selectorElements', []))}")
    print(f"   其他元素: {len(analysis.get('otherElements', []))}")

    # 显示提示词输入框
    prompt_inputs = []
    for inp in analysis.get("inputElements", []):
        if inp.get("isPromptInput"):
            prompt_inputs.append(inp)

    if prompt_inputs:
        print(f"\n📋 提示词输入框:")
        for i, inp in enumerate(prompt_inputs):
            print(f"   {i+1}. 占位符: '{inp.get('placeholder')}'")
            print(f"       值: '{inp.get('value', '')[:100]}...'")
            print(f"       类型: {inp.get('tagName')}/{inp.get('inputType')}")
            print(f"       可见: {inp.get('visible')}")

    # 显示生成按钮
    generate_buttons = []
    for btn in analysis.get("buttonElements", []):
        if btn.get("isGenerateButton"):
            generate_buttons.append(btn)

    if generate_buttons:
        print(f"\n📋 生成按钮:")
        for i, btn in enumerate(generate_buttons):
            print(f"   {i+1}. 文本: '{btn.get('text')}'")
            print(f"       类名: {btn.get('className', '')[:50]}...")
            print(f"       ID: {btn.get('id')}")
            print(f"       可见: {btn.get('visible')}")
            print(f"       禁用: {btn.get('disabled')}")

    # 显示选择器
    selectors = analysis.get("selectorElements", [])
    if selectors:
        print(f"\n📋 选择器:")
        for i, selector in enumerate(selectors):
            print(f"   {i+1}. 类型: {selector.get('selectorType')}")
            print(f"       文本: '{selector.get('text')}'")
            print(f"       类名: {selector.get('className', '')[:50]}...")
            print(f"       ID: {selector.get('id')}")
            print(f"       可见: {selector.get('visible')}")

    # 判断是否是真正的AI绘画生成界面
    is_real_ai_painting_interface = (
        key_features.get("hasPromptInput")
        or key_features.get("hasGenerateButton")
        or key_features.get("hasStyleSelector")
    )

    print(f"\n🔍 综合分析:")
    print(f"   是真正的AI绘画生成界面: {is_real_ai_painting_interface}")

    return is_real_ai_painting_interface


def try_interact_with_interface():
    """尝试与界面交互"""
    print("\n🔧 尝试与界面交互...")

    cli = DoubaoCLIEnhanced()

    # 先尝试查找并输入提示词
    input_js = """
    // 查找提示词输入框
    var promptInput = null;
    var inputs = document.querySelectorAll('textarea, input[type="text"], [contenteditable="true"]');

    for (var i = 0; i < inputs.length; i++) {
        var input = inputs[i];
        if (input.offsetParent !== null) {
            var placeholder = input.placeholder || '';
            if (placeholder.toLowerCase().includes('提示词') ||
                placeholder.toLowerCase().includes('prompt') ||
                placeholder.toLowerCase().includes('描述') ||
                placeholder.toLowerCase().includes('写点什么')) {
                promptInput = input;
                break;
            }
        }
    }

    if (promptInput) {
        console.log('找到提示词输入框');

        // 输入测试提示词
        var testPrompt = "一只可爱的卡通猫咪，蓝色眼睛，戴着红色蝴蝶结，背景有彩虹";

        if (promptInput.tagName === 'TEXTAREA' || promptInput.tagName === 'INPUT') {
            promptInput.value = testPrompt;
            promptInput.dispatchEvent(new Event('input', { bubbles: true }));
            promptInput.dispatchEvent(new Event('change', { bubbles: true }));
        } else if (promptInput.hasAttribute('contenteditable')) {
            promptInput.textContent = testPrompt;
            promptInput.dispatchEvent(new Event('input', { bubbles: true }));
        }

        "已输入提示词: " + testPrompt.substring(0, 50) + "...";
    } else {
        "未找到提示词输入框";
    }
    """

    result = cli.execute_javascript_enhanced(input_js)
    print(f"输入提示词结果: success={result.success}, output={repr(result.output)}")

    # 等待一下
    time.sleep(1)

    # 尝试查找并点击生成按钮
    generate_js = """
    // 查找生成按钮
    var generateButton = null;
    var buttons = document.querySelectorAll('button, [role="button"]');

    for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        if (btn.offsetParent !== null && !btn.disabled) {
            var text = (btn.textContent || btn.innerText || '').trim().toLowerCase();
            if (text.includes('生成') || text.includes('创作') || text.includes('开始') ||
                text.includes('draw') || text.includes('paint') || text.includes('create') ||
                text.includes('generate')) {
                generateButton = btn;
                break;
            }
        }
    }

    if (generateButton) {
        console.log('找到生成按钮: ' + generateButton.textContent);
        generateButton.click();
        "点击生成按钮: " + generateButton.textContent;
    } else {
        "未找到生成按钮";
    }
    """

    generate_result = cli.execute_javascript_enhanced(generate_js)
    print(
        f"点击生成按钮结果: success={generate_result.success}, output={repr(generate_result.output)}"
    )

    # 等待生成
    print("\n⏳ 等待图像生成...")
    time.sleep(5)

    return (
        generate_result.success
        and generate_result.output
        and "点击生成按钮" in generate_result.output
    )


def main():
    """主函数"""
    print("🎯 AI绘画生成界面检查")
    print("=" * 60)

    try:
        # 1. 检查当前页面
        print("\n📋 步骤1: 检查/create-image页面")
        analysis = check_create_image_page()

        if not analysis:
            print("❌ 无法分析页面")
            return 1

        # 2. 分析页面
        print("\n📋 步骤2: 分析页面内容")
        is_real_interface = analyze_page(analysis)

        if is_real_interface:
            # 3. 尝试交互
            print("\n📋 步骤3: 尝试交互")
            interact_success = try_interact_with_interface()

            if interact_success:
                print("\n✅ 成功触发生成!")
                print("\n💡 等待图像生成完成...")
                time.sleep(10)

                # 检查是否有生成的图像
                check_images_js = """
                // 检查图像
                var imageCheck = {
                    totalImages: document.querySelectorAll('img').length,
                    generatedImages: []
                };

                var images = document.querySelectorAll('img');
                for (var i = 0; i < Math.min(images.length, 10); i++) {
                    var img = images[i];
                    var src = img.src || '';
                    if (src && !src.includes('data:image/svg+xml') && src.includes('http')) {
                        imageCheck.generatedImages.push({
                            src: src.substring(0, 200),
                            alt: img.alt || '',
                            className: img.className || ''
                        });
                    }
                }

                JSON.stringify(imageCheck);
                """

                cli = DoubaoCLIEnhanced()
                images_result = cli.execute_javascript_enhanced(check_images_js)
                if (
                    images_result.success
                    and images_result.output
                    and images_result.output != "missing value"
                ):
                    try:
                        image_check = json.loads(cli._clean_js_output(images_result.output))
                        print(f"\n📋 图像生成检查:")
                        print(f"   总图像数: {image_check.get('totalImages')}")
                        print(f"   生成的图像: {len(image_check.get('generatedImages', []))}")

                        if image_check.get("generatedImages"):
                            print(f"\n✅ 检测到生成的图像!")
                            for i, img in enumerate(image_check.get("generatedImages", [])):
                                print(f"   图像 {i+1}: {img.get('src', '')[:100]}...")
                        else:
                            print(f"\n⚠️  未检测到生成的图像，可能需要更多时间")
                    except Exception as e:
                        print(f"解析图像检查失败: {e}")
            else:
                print("\n❌ 未能成功交互")
        else:
            print("\n⚠️  可能不是真正的AI绘画生成界面")

        print("\n" + "=" * 60)
        print("📊 测试完成")
        print("=" * 60)

        return 0 if is_real_interface else 1

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
