#!/usr/bin/env python3
"""
探索AI创作界面，查找文生图功能
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def explore_ai_creation_page():
    """探索AI创作界面"""
    print("🔧 探索AI创作界面...")

    cli = DoubaoCLIEnhanced()

    # 详细探索界面
    explore_js = """
    // 探索AI创作界面
    var exploration = {
        // 页面基本信息
        pageInfo: {
            title: document.title,
            url: window.location.href,
            path: window.location.pathname
        },

        // 所有选项卡或模式切换器
        tabs: [],

        // 所有文本输入区域
        textInputs: [],

        // 所有按钮
        buttons: [],

        // 所有图像区域
        imageAreas: [],

        // 页面文本分析
        textContent: (document.body.innerText || '').substring(0, 3000),

        // 可能的生成模式
        possibleModes: []
    };

    // 查找选项卡
    var tabElements = document.querySelectorAll('[role="tab"], [class*="tab"], [class*="Tab"], [class*="mode"], [class*="Mode"]');
    for (var i = 0; i < tabElements.length; i++) {
        var tab = tabElements[i];
        if (tab.offsetParent !== null) {
            var info = {
                index: i,
                tagName: tab.tagName,
                text: (tab.textContent || tab.innerText || '').trim(),
                className: tab.className || '',
                id: tab.id || '',
                ariaLabel: tab.getAttribute('aria-label') || '',
                role: tab.getAttribute('role') || '',
                selected: tab.getAttribute('aria-selected') === 'true' || tab.classList.contains('selected'),
                visible: true
            };
            exploration.tabs.push(info);
        }
    }

    // 查找所有可能的文本输入区域
    var inputElements = document.querySelectorAll('input, textarea, [contenteditable="true"], [class*="input"], [class*="Input"], [class*="text"], [class*="Text"], [class*="prompt"], [class*="Prompt"]');
    for (var i = 0; i < inputElements.length; i++) {
        var input = inputElements[i];
        if (input.offsetParent !== null) {
            var info = {
                index: i,
                tagName: input.tagName,
                type: input.type || '',
                placeholder: input.placeholder || '',
                value: input.value || '',
                className: input.className || '',
                id: input.id || '',
                ariaLabel: input.getAttribute('aria-label') || '',
                contentEditable: input.contentEditable || '',
                visible: true,
                isLikelyPromptInput: false
            };

            // 判断是否是提示词输入框
            var placeholderLower = info.placeholder.toLowerCase();
            var classNameLower = info.className.toLowerCase();
            var ariaLabelLower = info.ariaLabel.toLowerCase();

            if (placeholderLower.includes('提示词') || placeholderLower.includes('prompt') ||
                placeholderLower.includes('描述') || placeholderLower.includes('输入') ||
                placeholderLower.includes('写点什么') || placeholderLower.includes('生成') ||
                placeholderLower.includes('创作') || classNameLower.includes('prompt') ||
                classNameLower.includes('input') || ariaLabelLower.includes('prompt')) {
                info.isLikelyPromptInput = true;
            }

            exploration.textInputs.push(info);
        }
    }

    // 查找所有按钮
    var buttonElements = document.querySelectorAll('button, [role="button"], [class*="btn"], [class*="Btn"], [class*="button"], [class*="Button"]');
    for (var i = 0; i < buttonElements.length; i++) {
        var btn = buttonElements[i];
        if (btn.offsetParent !== null) {
            var info = {
                index: i,
                tagName: btn.tagName,
                text: (btn.textContent || btn.innerText || '').trim(),
                className: btn.className || '',
                id: btn.id || '',
                ariaLabel: btn.getAttribute('aria-label') || '',
                role: btn.getAttribute('role') || '',
                disabled: btn.disabled,
                visible: true,
                isLikelyGenerateButton: false
            };

            // 判断是否是生成按钮
            var textLower = info.text.toLowerCase();
            var classNameLower = info.className.toLowerCase();
            var ariaLabelLower = info.ariaLabel.toLowerCase();

            if (textLower.includes('生成') || textLower.includes('创作') || textLower.includes('开始') ||
                textLower.includes('draw') || textLower.includes('paint') || textLower.includes('create') ||
                textLower.includes('generate') || classNameLower.includes('generate') ||
                classNameLower.includes('create') || ariaLabelLower.includes('生成')) {
                info.isLikelyGenerateButton = true;
            }

            exploration.buttons.push(info);
        }
    }

    // 查找所有图像区域
    var imageElements = document.querySelectorAll('img, canvas, [class*="image"], [class*="Image"], [class*="canvas"], [class*="Canvas"], [class*="preview"], [class*="Preview"], [class*="result"], [class*="Result"]');
    for (var i = 0; i < imageElements.length; i++) {
        var img = imageElements[i];
        if (img.offsetParent !== null) {
            var info = {
                index: i,
                tagName: img.tagName,
                src: img.src || '',
                alt: img.alt || '',
                className: img.className || '',
                id: img.id || '',
                ariaLabel: img.getAttribute('aria-label') || '',
                visible: true
            };
            exploration.imageAreas.push(info);
        }
    }

    // 分析文本内容，查找可能的模式
    var text = exploration.textContent.toLowerCase();
    if (text.includes('文生图') || text.includes('text to image') || text.includes('文字生成图片')) {
        exploration.possibleModes.push('text_to_image');
    }
    if (text.includes('图生图') || text.includes('image to image')) {
        exploration.possibleModes.push('image_to_image');
    }
    if (text.includes('图像编辑') || text.includes('image editing') || text.includes('图片编辑')) {
        exploration.possibleModes.push('image_editing');
    }
    if (text.includes('图像增强') || text.includes('image enhancement')) {
        exploration.possibleModes.push('image_enhancement');
    }

    JSON.stringify(exploration);
    """

    result = cli.execute_javascript_enhanced(explore_js)
    print(
        f"探索结果: success={result.success}, output={repr(result.output[:200]) if result.output else 'None'}"
    )

    if result.success and result.output and result.output != "missing value":
        try:
            exploration = json.loads(cli._clean_js_output(result.output))
            return exploration
        except Exception as e:
            print(f"解析探索结果失败: {e}")
            return None
    else:
        print(f"获取探索结果失败")
        return None


def analyze_exploration(exploration):
    """分析探索结果"""
    if not exploration:
        print("❌ 无探索数据")
        return None

    print(f"\n📋 页面信息:")
    page_info = exploration.get("pageInfo", {})
    print(f"   标题: {page_info.get('title')}")
    print(f"   路径: {page_info.get('path')}")

    print(f"\n📋 可能的生成模式:")
    modes = exploration.get("possibleModes", [])
    if modes:
        for mode in modes:
            print(f"   - {mode}")
    else:
        print("   （未检测到明确的生成模式）")

    print(f"\n📋 选项卡/模式切换器:")
    tabs = exploration.get("tabs", [])
    if tabs:
        for i, tab in enumerate(tabs[:10]):
            print(f"   {i+1}. '{tab.get('text')}'")
            print(f"       类型: {tab.get('tagName')}, 角色: {tab.get('role')}")
            print(f"       类名: {tab.get('className', '')[:50]}...")
            print(f"       选中: {tab.get('selected')}")
    else:
        print("   （未找到选项卡）")

    print(f"\n📋 可能的提示词输入框:")
    prompt_inputs = []
    for inp in exploration.get("textInputs", []):
        if inp.get("isLikelyPromptInput"):
            prompt_inputs.append(inp)

    if prompt_inputs:
        for i, inp in enumerate(prompt_inputs[:5]):
            print(f"   {i+1}. 占位符: '{inp.get('placeholder')}'")
            print(f"       值: '{inp.get('value', '')[:100]}...'")
            print(f"       类型: {inp.get('tagName')}/{inp.get('type')}")
            print(f"       类名: {inp.get('className', '')[:50]}...")
    else:
        print("   （未找到提示词输入框）")

    print(f"\n📋 可能的生成按钮:")
    generate_buttons = []
    for btn in exploration.get("buttons", []):
        if btn.get("isLikelyGenerateButton"):
            generate_buttons.append(btn)

    if generate_buttons:
        for i, btn in enumerate(generate_buttons[:5]):
            print(f"   {i+1}. 文本: '{btn.get('text')}'")
            print(f"       类型: {btn.get('tagName')}, 角色: {btn.get('role')}")
            print(f"       类名: {btn.get('className', '')[:50]}...")
            print(f"       禁用: {btn.get('disabled')}")
    else:
        print("   （未找到生成按钮）")

    print(f"\n📋 图像区域:")
    image_areas = exploration.get("imageAreas", [])
    print(f"   找到 {len(image_areas)} 个图像区域")
    if image_areas:
        # 显示前几个
        for i, img in enumerate(image_areas[:3]):
            if img.get("tagName") == "IMG":
                print(f"   {i+1}. 图像: src='{img.get('src', '')[:100]}...'")
            else:
                print(f"   {i+1}. 画布/预览: 类型={img.get('tagName')}")

    # 分析界面类型
    text_content = exploration.get("textContent", "").lower()

    is_text_to_image = False
    is_image_editing = False

    if "文生图" in text_content or "text to image" in text_content:
        is_text_to_image = True
    if "图像编辑" in text_content or "image editing" in text_content:
        is_image_editing = True

    print(f"\n🔍 界面类型分析:")
    print(f"   可能是文生图界面: {is_text_to_image}")
    print(f"   可能是图像编辑界面: {is_image_editing}")

    return {
        "is_text_to_image": is_text_to_image,
        "is_image_editing": is_image_editing,
        "has_prompt_inputs": len(prompt_inputs) > 0,
        "has_generate_buttons": len(generate_buttons) > 0,
        "tabs": tabs,
        "prompt_inputs": prompt_inputs,
        "generate_buttons": generate_buttons,
    }


def try_switch_to_text_to_image(analysis):
    """尝试切换到文生图模式"""
    if not analysis:
        return False

    tabs = analysis.get("tabs", [])
    if not tabs:
        print("❌ 没有可切换的选项卡")
        return False

    print("\n🔧 尝试切换到文生图模式...")

    cli = DoubaoCLIEnhanced()

    # 查找文生图相关的选项卡
    text_to_image_tabs = []
    for tab in tabs:
        text = tab.get("text", "").lower()
        if "文生图" in text or "text" in text or "文字" in text or "生成" in text:
            text_to_image_tabs.append(tab)

    if not text_to_image_tabs:
        print("❌ 未找到文生图选项卡")
        return False

    # 尝试点击第一个文生图选项卡
    target_tab = text_to_image_tabs[0]
    print(f"尝试点击选项卡: '{target_tab.get('text')}'")

    click_js = f"""
    // 尝试点击选项卡
    var clicked = false;
    var targetText = "{target_tab.get('text')}";

    // 方法1: 通过文本查找
    var allElements = document.querySelectorAll('button, div, span, [role="tab"]');
    for (var i = 0; i < allElements.length; i++) {{
        var elem = allElements[i];
        if (elem.offsetParent !== null) {{
            var text = (elem.textContent || elem.innerText || '').trim();
            if (text === targetText) {{
                console.log('找到选项卡，点击: ' + text);
                elem.click();
                clicked = true;
                break;
            }}
        }}
    }}

    clicked ? "点击选项卡成功" : "点击选项卡失败";
    """

    result = cli.execute_javascript_enhanced(click_js)
    print(f"点击结果: success={result.success}, output={repr(result.output)}")

    # 等待页面响应
    time.sleep(3)

    return result.success and result.output and "点击选项卡成功" in result.output


def try_direct_text_to_image():
    """尝试直接进行文生图"""
    print("\n🔧 尝试直接进行文生图...")

    cli = DoubaoCLIEnhanced()

    # 首先尝试在页面中搜索可能的输入区域
    search_js = """
    // 搜索所有可能的输入区域
    var foundInput = null;
    var allElements = document.querySelectorAll('*');

    for (var i = 0; i < allElements.length; i++) {
        var elem = allElements[i];
        if (elem.offsetParent !== null) {
            var placeholder = elem.placeholder || '';
            var ariaLabel = elem.getAttribute('aria-label') || '';
            var className = elem.className || '';

            if (placeholder.toLowerCase().includes('提示词') ||
                placeholder.toLowerCase().includes('prompt') ||
                placeholder.toLowerCase().includes('描述') ||
                ariaLabel.toLowerCase().includes('提示词') ||
                ariaLabel.toLowerCase().includes('prompt') ||
                className.toLowerCase().includes('prompt')) {
                foundInput = elem;
                break;
            }
        }
    }

    if (foundInput) {
        console.log('找到可能的输入区域: ' + foundInput.tagName);

        // 尝试输入文本
        var testPrompt = "一只可爱的卡通猫咪，蓝色眼睛，戴着红色蝴蝶结，背景有彩虹，动漫风格";

        if (foundInput.tagName === 'TEXTAREA' || foundInput.tagName === 'INPUT') {
            foundInput.value = testPrompt;
            foundInput.dispatchEvent(new Event('input', { bubbles: true }));
            foundInput.dispatchEvent(new Event('change', { bubbles: true }));
            "已输入提示词到输入框: " + testPrompt.substring(0, 30) + "...";
        } else if (foundInput.hasAttribute('contenteditable')) {
            foundInput.textContent = testPrompt;
            foundInput.dispatchEvent(new Event('input', { bubbles: true }));
            "已输入提示词到可编辑区域: " + testPrompt.substring(0, 30) + "...";
        } else {
            "找到区域但不是标准输入框: " + foundInput.tagName;
        }
    } else {
        "未找到提示词输入区域";
    }
    """

    input_result = cli.execute_javascript_enhanced(search_js)
    print(f"搜索并输入结果: success={input_result.success}, output={repr(input_result.output)}")

    # 等待一下
    time.sleep(1)

    # 尝试查找生成按钮
    generate_js = """
    // 查找生成按钮
    var generateButton = null;
    var buttons = document.querySelectorAll('button, [role="button"]');

    for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        if (btn.offsetParent !== null && !btn.disabled) {
            var text = (btn.textContent || btn.innerText || '').trim();
            if (text.includes('生成') || text.includes('创作') || text.includes('开始') ||
                text.includes('Draw') || text.includes('Paint') || text.includes('Create') ||
                text.includes('Generate')) {
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
    print(f"生成按钮结果: success={generate_result.success}, output={repr(generate_result.output)}")

    # 等待生成
    if (
        generate_result.success
        and generate_result.output
        and "点击生成按钮" in generate_result.output
    ):
        print("\n⏳ 等待图像生成...")
        time.sleep(8)
        return True
    else:
        return False


def main():
    """主函数"""
    print("🎯 AI创作界面深度探索")
    print("=" * 60)

    try:
        # 1. 探索界面
        print("\n📋 步骤1: 探索AI创作界面")
        exploration = explore_ai_creation_page()

        if not exploration:
            print("❌ 无法探索界面")
            return 1

        # 2. 分析探索结果
        print("\n📋 步骤2: 分析界面结构")
        analysis = analyze_exploration(exploration)

        # 3. 尝试切换到文生图模式（如果有选项卡）
        if analysis.get("tabs"):
            print("\n📋 步骤3: 尝试切换模式")
            switch_success = try_switch_to_text_to_image(analysis)
            if switch_success:
                print("✅ 成功切换模式")
                # 重新探索
                time.sleep(2)
                exploration = explore_ai_creation_page()
                analysis = analyze_exploration(exploration)

        # 4. 尝试直接进行文生图
        print("\n📋 步骤4: 尝试直接文生图")
        generate_success = try_direct_text_to_image()

        if generate_success:
            print("\n✅ 已触发生成!")
            print("\n💡 检查生成结果...")

            # 检查是否有新图像
            check_js = """
            // 检查新生成的图像
            var newImages = [];
            var images = document.querySelectorAll('img');

            for (var i = 0; i < images.length; i++) {
                var img = images[i];
                var src = img.src || '';
                // 排除静态资源和图标
                if (src && src.includes('http') &&
                    !src.includes('logo') &&
                    !src.includes('icon') &&
                    !src.includes('static') &&
                    !src.includes('example')) {
                    newImages.push({
                        src: src.substring(0, 150),
                        alt: img.alt || '',
                        className: img.className || ''
                    });
                }
            }

            JSON.stringify({
                totalImages: images.length,
                newImages: newImages.length,
                imageUrls: newImages.map(img => img.src)
            });
            """

            cli = DoubaoCLIEnhanced()
            result = cli.execute_javascript_enhanced(check_js)
            if result.success and result.output and result.output != "missing value":
                try:
                    check_result = json.loads(cli._clean_js_output(result.output))
                    print(f"图像检查结果:")
                    print(f"   总图像数: {check_result.get('totalImages')}")
                    print(f"   新图像数: {check_result.get('newImages')}")

                    if check_result.get("newImages", 0) > 0:
                        print(f"\n✅ 成功生成新图像!")
                        urls = check_result.get("imageUrls", [])
                        for i, url in enumerate(urls[:3]):
                            print(f"   图像 {i+1}: {url}")
                    else:
                        print(f"\n⚠️  未检测到新生成的图像")
                except Exception as e:
                    print(f"解析图像检查结果失败: {e}")
        else:
            print("\n❌ 未能成功生成图像")

        print("\n" + "=" * 60)
        print("📊 探索完成")
        print("=" * 60)

        return 0 if generate_success else 1

    except Exception as e:
        print(f"\n❌ 探索出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
