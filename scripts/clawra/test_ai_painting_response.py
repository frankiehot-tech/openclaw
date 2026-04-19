#!/usr/bin/env python3
"""
检查AI绘画响应后的页面状态
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def check_ai_painting_interface():
    """检查AI绘画界面"""
    print("🔧 检查AI绘画响应后的页面状态...")

    cli = DoubaoCLIEnhanced()

    # 详细检查页面，特别是AI绘画相关的元素
    detail_check_js = """
    // 详细检查AI绘画界面
    var aiPaintingCheck = {
        // 页面基本信息
        pageInfo: {
            title: document.title,
            url: window.location.href,
            path: window.location.pathname
        },

        // 所有按钮信息
        buttons: [],

        // 输入框和文本区域
        inputs: [],
        textareas: [],

        // AI绘画特定元素
        aiPaintingElements: {
            // 可能的生成相关按钮
            generateButtons: [],
            // 提示词输入框
            promptInputs: [],
            // 风格选择器
            styleSelectors: [],
            // 尺寸选择器
            sizeSelectors: [],
            // 模型选择器
            modelSelectors: [],
            // 画布或预览区域
            canvasOrPreview: []
        },

        // 页面文本分析
        textAnalysis: {
            fullText: (document.body.innerText || '').substring(0, 5000),
            hasAIPaintingKeywords: false,
            keywordsFound: [],
            hasGenerationOptions: false,
            hasStyleOptions: false,
            hasSizeOptions: false
        }
    };

    // 检查AI绘画关键词
    var aiKeywords = ['AI绘画', 'AI创作', '绘画', '画图', '生成', '创作', 'prompt', '提示词', '风格', '尺寸', '质量', '模型', '画布', '预览', '生成图片', '生成图像'];
    var fullText = aiPaintingCheck.textAnalysis.fullText.toLowerCase();
    for (var i = 0; i < aiKeywords.length; i++) {
        var keyword = aiKeywords[i].toLowerCase();
        if (fullText.includes(keyword)) {
            aiPaintingCheck.textAnalysis.hasAIPaintingKeywords = true;
            aiPaintingCheck.textAnalysis.keywordsFound.push(aiKeywords[i]);
        }
    }

    // 检查生成选项
    if (fullText.includes('生成') || fullText.includes('generate') || fullText.includes('创作') || fullText.includes('create')) {
        aiPaintingCheck.textAnalysis.hasGenerationOptions = true;
    }

    // 检查风格选项
    if (fullText.includes('风格') || fullText.includes('style') || fullText.includes('艺术')) {
        aiPaintingCheck.textAnalysis.hasStyleOptions = true;
    }

    // 检查尺寸选项
    if (fullText.includes('尺寸') || fullText.includes('size') || fullText.includes('分辨率')) {
        aiPaintingCheck.textAnalysis.hasSizeOptions = true;
    }

    // 收集所有按钮信息
    var buttons = document.querySelectorAll('button');
    for (var i = 0; i < Math.min(buttons.length, 100); i++) {
        var btn = buttons[i];
        var text = (btn.textContent || btn.innerText || '').trim();
        var info = {
            index: i,
            tagName: btn.tagName,
            text: text,
            className: (btn.className || '').substring(0, 100),
            id: btn.id || '',
            ariaLabel: btn.getAttribute('aria-label') || '',
            disabled: btn.disabled,
            visible: btn.offsetParent !== null,
            isAIPaintingButton: false
        };

        // 检查是否是AI绘画相关按钮
        var btnTextLower = text.toLowerCase();
        if (btnTextLower.includes('生成') || btnTextLower.includes('创作') || btnTextLower.includes('画') ||
            btnTextLower.includes('draw') || btnTextLower.includes('paint') || btnTextLower.includes('create') ||
            btnTextLower.includes('generate')) {
            info.isAIPaintingButton = true;
            aiPaintingCheck.aiPaintingElements.generateButtons.push(info);
        }

        aiPaintingCheck.buttons.push(info);
    }

    // 收集输入框和文本区域
    var inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
    for (var i = 0; i < Math.min(inputs.length, 50); i++) {
        var input = inputs[i];
        var info = {
            index: i,
            tagName: input.tagName,
            type: input.type || '',
            placeholder: (input.placeholder || '').substring(0, 200),
            value: (input.value || '').substring(0, 500),
            className: (input.className || '').substring(0, 100),
            id: input.id || '',
            ariaLabel: input.getAttribute('aria-label') || '',
            visible: input.offsetParent !== null,
            isPromptInput: false
        };

        // 检查是否是提示词输入框
        var placeholderLower = info.placeholder.toLowerCase();
        if (placeholderLower.includes('提示词') || placeholderLower.includes('prompt') ||
            placeholderLower.includes('描述') || placeholderLower.includes('描述您想画的')) {
            info.isPromptInput = true;
            aiPaintingCheck.aiPaintingElements.promptInputs.push(info);
        }

        if (input.tagName === 'TEXTAREA') {
            aiPaintingCheck.textareas.push(info);
        } else {
            aiPaintingCheck.inputs.push(info);
        }
    }

    // 查找特定选择器元素
    var selectors = document.querySelectorAll('select, [role="listbox"], [class*="select"], [class*="Select"]');
    for (var i = 0; i < Math.min(selectors.length, 20); i++) {
        var selector = selectors[i];
        var info = {
            index: i,
            tagName: selector.tagName,
            className: (selector.className || '').substring(0, 100),
            id: selector.id || '',
            ariaLabel: selector.getAttribute('aria-label') || '',
            visible: selector.offsetParent !== null,
            type: 'unknown'
        };

        // 尝试确定选择器类型
        var className = info.className.toLowerCase();
        var ariaLabel = info.ariaLabel.toLowerCase();
        var id = info.id.toLowerCase();

        if (className.includes('style') || ariaLabel.includes('style') || id.includes('style')) {
            info.type = 'style';
            aiPaintingCheck.aiPaintingElements.styleSelectors.push(info);
        } else if (className.includes('size') || ariaLabel.includes('size') || id.includes('size')) {
            info.type = 'size';
            aiPaintingCheck.aiPaintingElements.sizeSelectors.push(info);
        } else if (className.includes('model') || ariaLabel.includes('model') || id.includes('model')) {
            info.type = 'model';
            aiPaintingCheck.aiPaintingElements.modelSelectors.push(info);
        }

        // 默认为风格选择器
        if (info.type === 'unknown') {
            info.type = 'style';
            aiPaintingCheck.aiPaintingElements.styleSelectors.push(info);
        }
    }

    // 查找画布或预览区域
    var canvasElements = document.querySelectorAll('canvas, [class*="canvas"], [class*="Canvas"], [class*="preview"], [class*="Preview"]');
    for (var i = 0; i < Math.min(canvasElements.length, 10); i++) {
        var canvas = canvasElements[i];
        var info = {
            index: i,
            tagName: canvas.tagName,
            className: (canvas.className || '').substring(0, 100),
            id: canvas.id || '',
            ariaLabel: canvas.getAttribute('aria-label') || '',
            visible: canvas.offsetParent !== null
        };
        aiPaintingCheck.aiPaintingElements.canvasOrPreview.push(info);
    }

    JSON.stringify(aiPaintingCheck);
    """

    result = cli.execute_javascript_enhanced(detail_check_js)
    print(f"详细检查结果: success={result.success}, output={repr(result.output)}")

    if result.success and result.output and result.output != "missing value":
        try:
            ai_check = json.loads(cli._clean_js_output(result.output))
            return ai_check
        except Exception as e:
            print(f"解析AI检查结果失败: {e}")
            return None
    else:
        print(f"获取AI检查结果失败")
        return None


def analyze_ai_painting_interface(ai_check):
    """分析AI绘画界面"""
    if not ai_check:
        print("❌ 无数据可分析")
        return False

    print("\n📋 页面基本信息:")
    page_info = ai_check.get("pageInfo", {})
    print(f"   标题: {page_info.get('title')}")
    print(f"   路径: {page_info.get('path')}")
    print(f"   URL: {page_info.get('url')}")

    print("\n📋 文本分析:")
    text_analysis = ai_check.get("textAnalysis", {})
    print(f"   有AI绘画关键词: {text_analysis.get('hasAIPaintingKeywords')}")
    print(f"   找到的关键词: {', '.join(text_analysis.get('keywordsFound', []))}")
    print(f"   有生成选项: {text_analysis.get('hasGenerationOptions')}")
    print(f"   有风格选项: {text_analysis.get('hasStyleOptions')}")
    print(f"   有尺寸选项: {text_analysis.get('hasSizeOptions')}")

    print(f"\n📋 元素统计:")
    print(f"   总按钮数: {len(ai_check.get('buttons', []))}")
    print(f"   输入框数: {len(ai_check.get('inputs', []))}")
    print(f"   文本区域数: {len(ai_check.get('textareas', []))}")

    ai_elements = ai_check.get("aiPaintingElements", {})
    print(f"\n📋 AI绘画特定元素:")
    print(f"   生成按钮: {len(ai_elements.get('generateButtons', []))}")
    print(f"   提示词输入框: {len(ai_elements.get('promptInputs', []))}")
    print(f"   风格选择器: {len(ai_elements.get('styleSelectors', []))}")
    print(f"   尺寸选择器: {len(ai_elements.get('sizeSelectors', []))}")
    print(f"   模型选择器: {len(ai_elements.get('modelSelectors', []))}")
    print(f"   画布/预览区域: {len(ai_elements.get('canvasOrPreview', []))}")

    # 显示生成按钮
    generate_buttons = ai_elements.get("generateButtons", [])
    if generate_buttons:
        print(f"\n📋 可能的生成按钮:")
        for i, btn in enumerate(generate_buttons[:10]):
            print(
                f"   {i+1}. '{btn.get('text')}' (类名: {btn.get('className', 'N/A')}, 可见: {btn.get('visible')})"
            )

    # 显示提示词输入框
    prompt_inputs = ai_elements.get("promptInputs", [])
    if prompt_inputs:
        print(f"\n📋 可能的提示词输入框:")
        for i, inp in enumerate(prompt_inputs[:5]):
            print(f"   {i+1}. 占位符: '{inp.get('placeholder')}'")
            print(f"       值: '{inp.get('value', '')[:100]}...'")
            print(
                f"       类型: {inp.get('tagName')}/{inp.get('type')}, 可见: {inp.get('visible')}"
            )

    # 判断是否是AI绘画界面
    is_ai_painting_interface = text_analysis.get("hasAIPaintingKeywords") and (
        len(generate_buttons) > 0 or len(prompt_inputs) > 0
    )

    print(f"\n🔍 综合分析:")
    print(f"   是AI绘画界面: {is_ai_painting_interface}")

    if is_ai_painting_interface:
        print(f"\n✅ 成功进入AI绘画界面!")
    else:
        print(f"\n⚠️  可能是聊天界面中的AI绘画功能，但尚未完全进入绘画界面")

    return is_ai_painting_interface


def try_click_generate_button():
    """尝试点击生成按钮"""
    print("\n🔧 尝试点击生成按钮...")

    cli = DoubaoCLIEnhanced()

    # 查找并点击生成按钮
    click_js = """
    // 查找生成按钮
    var buttons = document.querySelectorAll('button');
    var generateButton = null;

    for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        if (btn.offsetParent !== null) { // 可见
            var text = (btn.textContent || btn.innerText || '').trim().toLowerCase();
            if (text.includes('生成') || text.includes('创作') || text.includes('画') ||
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
        "点击生成按钮成功: " + generateButton.textContent;
    } else {
        "未找到生成按钮";
    }
    """

    result = cli.execute_javascript_enhanced(click_js)
    print(f"点击结果: success={result.success}, output={repr(result.output)}")

    # 等待响应
    time.sleep(3)

    return result.success and result.output and "点击生成按钮成功" in result.output


def main():
    """主函数"""
    print("🎯 AI绘画响应页面检查")
    print("=" * 60)

    try:
        # 1. 检查当前页面状态
        print("\n📋 步骤1: 检查页面状态")
        ai_check = check_ai_painting_interface()

        if not ai_check:
            print("❌ 无法检查页面状态")
            return 1

        # 2. 分析AI绘画界面
        print("\n📋 步骤2: 分析AI绘画界面")
        is_ai_interface = analyze_ai_painting_interface(ai_check)

        if is_ai_interface:
            # 3. 尝试点击生成按钮
            print("\n📋 步骤3: 尝试交互")
            click_success = try_click_generate_button()

            if click_success:
                print("\n✅ 成功点击生成按钮")
                print("\n💡 等待图像生成...")
                time.sleep(5)

                # 检查是否有图像生成
                print("\n📋 步骤4: 检查图像生成")
                image_check_js = """
                // 检查图像元素
                var imageInfo = {
                    images: document.querySelectorAll('img').length,
                    hasGeneratedImages: false,
                    imageUrls: []
                };

                var images = document.querySelectorAll('img');
                for (var i = 0; i < images.length; i++) {
                    var img = images[i];
                    var src = img.src || '';
                    if (src && !src.includes('data:image/svg+xml')) { // 排除SVG图标
                        imageInfo.imageUrls.push(src.substring(0, 200));
                        imageInfo.hasGeneratedImages = true;
                    }
                }

                JSON.stringify(imageInfo);
                """

                cli = DoubaoCLIEnhanced()
                image_result = cli.execute_javascript_enhanced(image_check_js)
                if (
                    image_result.success
                    and image_result.output
                    and image_result.output != "missing value"
                ):
                    try:
                        image_info = json.loads(cli._clean_js_output(image_result.output))
                        print(f"图像数量: {image_info.get('images')}")
                        print(f"有生成的图像: {image_info.get('hasGeneratedImages')}")
                        if image_info.get("hasGeneratedImages"):
                            print(f"✅ 检测到生成的图像!")
                            urls = image_info.get("imageUrls", [])
                            for i, url in enumerate(urls[:3]):
                                print(f"   图像 {i+1}: {url}")
                        else:
                            print(f"⚠️  未检测到生成的图像，可能需要更多时间")
                    except Exception as e:
                        print(f"解析图像信息失败: {e}")
            else:
                print("\n❌ 未能点击生成按钮")
        else:
            print("\n⚠️  可能尚未进入完整的AI绘画界面")
            print("\n💡 建议:")
            print("1. 等待豆包进一步响应")
            print("2. 尝试在聊天中输入更具体的指令，如'开始AI绘画'")
            print("3. 查找页面中的AI绘画入口按钮")

        print("\n" + "=" * 60)
        print("📊 检查完成")
        print("=" * 60)

        return 0 if is_ai_interface else 1

    except Exception as e:
        print(f"\n❌ 检查出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
