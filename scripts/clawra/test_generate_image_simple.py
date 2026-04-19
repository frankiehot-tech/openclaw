#!/usr/bin/env python3
"""
简单的图像生成测试
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def find_input_and_buttons():
    """查找输入框和按钮"""
    print("🔧 查找输入框和按钮...")

    cli = DoubaoCLIEnhanced()

    # 查找可编辑区域
    find_input_js = """
    // 查找可编辑的提示词输入区域
    var inputArea = null;
    var inputs = document.querySelectorAll('[contenteditable="true"], textarea, input[type="text"]');

    for (var i = 0; i < inputs.length; i++) {
        var input = inputs[i];
        if (input.offsetParent !== null) {
            // 检查是否在提示词区域附近
            var parent = input;
            while (parent) {
                var parentText = (parent.textContent || parent.innerText || '').toLowerCase();
                if (parentText.includes('描述') || parentText.includes('画面') ||
                    parentText.includes('提示词') || parentText.includes('prompt')) {
                    inputArea = input;
                    break;
                }
                parent = parent.parentElement;
            }
            if (inputArea) break;
        }
    }

    // 查找生成按钮
    var generateButton = null;
    var buttons = document.querySelectorAll('button, [role="button"]');
    var buttonCandidates = [];

    for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        if (btn.offsetParent !== null && !btn.disabled) {
            var text = (btn.textContent || btn.innerText || '').trim();
            if (text.includes('生成') || text.includes('创作') || text.includes('开始') ||
                text.includes('draw') || text.includes('paint') || text.includes('create') ||
                text.includes('generate')) {
                buttonCandidates.push({
                    element: btn,
                    text: text,
                    className: btn.className || '',
                    id: btn.id || ''
                });
            }
        }
    }

    // 返回结果
    var result = {
        inputFound: inputArea !== null,
        inputTag: inputArea ? inputArea.tagName : '',
        inputClass: inputArea ? inputArea.className || '' : '',
        generateButtonCandidates: buttonCandidates.length,
        buttonCandidates: buttonCandidates.map(function(btn) {
            return {
                text: btn.text,
                className: btn.className,
                id: btn.id
            };
        })
    };

    JSON.stringify(result);
    """

    result = cli.execute_javascript_enhanced(find_input_js)
    print(f"查找结果: success={result.success}, output={repr(result.output)}")

    if result.success and result.output and result.output != "missing value":
        try:
            data = json.loads(cli._clean_js_output(result.output))
            return data
        except Exception as e:
            print(f"解析结果失败: {e}")
            return None
    else:
        print(f"查找失败")
        return None


def try_generate_image(prompt="一只可爱的卡通猫咪"):
    """尝试生成图像"""
    print(f"🔧 尝试生成图像: '{prompt}'...")

    cli = DoubaoCLIEnhanced()

    # 首先尝试输入提示词
    input_js = f"""
    // 输入提示词
    var result = {{success: false, message: "未找到输入区域"}};

    // 方法1：查找可编辑区域
    var editables = document.querySelectorAll('[contenteditable="true"]');
    for (var i = 0; i < editables.length; i++) {{
        var elem = editables[i];
        if (elem.offsetParent !== null) {{
            // 检查是否在提示词区域附近
            var parent = elem;
            while (parent) {{
                var parentText = (parent.textContent || parent.innerText || '').toLowerCase();
                if (parentText.includes('描述') || parentText.includes('画面')) {{
                    console.log('找到可编辑提示区域');
                    elem.textContent = "{prompt}";
                    elem.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    elem.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    result = {{success: true, message: "已输入到可编辑区域", element: "contenteditable"}};
                    break;
                }}
                parent = parent.parentElement;
            }}
            if (result.success) break;
        }}
    }}

    // 方法2：查找textarea
    if (!result.success) {{
        var textareas = document.querySelectorAll('textarea');
        for (var i = 0; i < textareas.length; i++) {{
            var ta = textareas[i];
            if (ta.offsetParent !== null) {{
                console.log('找到textarea');
                ta.value = "{prompt}";
                ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                ta.dispatchEvent(new Event('change', {{ bubbles: true }}));
                result = {{success: true, message: "已输入到textarea", element: "textarea"}};
                break;
            }}
        }}
    }}

    JSON.stringify(result);
    """

    input_result = cli.execute_javascript_enhanced(input_js)
    print(f"输入提示词结果: success={input_result.success}, output={repr(input_result.output)}")

    if not input_result.success or not input_result.output or "success" not in input_result.output:
        print("❌ 输入提示词失败")
        return False

    # 等待一下让界面更新
    time.sleep(1)

    # 查找并点击生成按钮
    generate_js = """
    // 查找生成按钮
    var generateButton = null;
    var buttonTexts = ['生成', '创作', '开始', 'draw', 'paint', 'create', 'generate'];
    var buttons = document.querySelectorAll('button, [role="button"]');

    for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        if (btn.offsetParent !== null && !btn.disabled) {
            var text = (btn.textContent || btn.innerText || '').trim().toLowerCase();
            for (var j = 0; j < buttonTexts.length; j++) {
                if (text.includes(buttonTexts[j])) {
                    generateButton = btn;
                    console.log('找到生成按钮: ' + btn.textContent);
                    break;
                }
            }
            if (generateButton) break;
        }
    }

    // 如果没找到明确的生成按钮，尝试找看起来像生成按钮的
    if (!generateButton) {
        for (var i = 0; i < buttons.length; i++) {
            var btn = buttons[i];
            if (btn.offsetParent !== null && !btn.disabled) {
                var text = (btn.textContent || btn.innerText || '').trim();
                // 按钮文本较短且包含某些关键词
                if (text.length <= 8 && (text.includes('画') || text.includes('作') || text.includes('生'))) {
                    generateButton = btn;
                    console.log('找到可能的生成按钮: ' + text);
                    break;
                }
            }
        }
    }

    var result = {success: false, message: "未找到生成按钮"};
    if (generateButton) {
        generateButton.click();
        result = {success: true, message: "已点击生成按钮: " + generateButton.textContent};
    }

    JSON.stringify(result);
    """

    generate_result = cli.execute_javascript_enhanced(generate_js)
    print(
        f"点击生成按钮结果: success={generate_result.success}, output={repr(generate_result.output)}"
    )

    if generate_result.success and generate_result.output and "success" in generate_result.output:
        print("✅ 已触发生成!")
        # 等待生成
        print("⏳ 等待图像生成...")
        time.sleep(8)  # 给生成留出时间

        # 检查是否有新图像生成
        check_js = """
        // 检查新生成的图像
        var newImages = [];
        var images = document.querySelectorAll('img');

        for (var i = 0; i < images.length; i++) {
            var img = images[i];
            var src = img.src || '';
            // 检查是否是生成的结果图像
            if (src && src.includes('http') && !src.includes('logo') && !src.includes('icon')) {
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
            imageList: newImages
        });
        """

        check_result = cli.execute_javascript_enhanced(check_js)
        print(
            f"图像检查结果: success={check_result.success}, output={repr(check_result.output[:200] if check_result.output else 'None')}"
        )

        if check_result.success and check_result.output and check_result.output != "missing value":
            try:
                check_data = json.loads(cli._clean_js_output(check_result.output))
                print(f"\n📋 图像生成检查:")
                print(f"   总图像数: {check_data.get('totalImages')}")
                print(f"   新图像数: {check_data.get('newImages')}")

                if check_data.get("newImages", 0) > 0:
                    print("✅ 检测到新生成的图像!")
                    for i, img in enumerate(check_data.get("imageList", [])):
                        print(f"   图像 {i+1}: {img.get('src', '')[:100]}...")
                else:
                    print("⚠️  未检测到新生成的图像")
            except Exception as e:
                print(f"解析图像检查结果失败: {e}")

        return True
    else:
        print("❌ 未能触发生成")
        return False


def main():
    """主函数"""
    print("🎯 简单的图像生成测试")
    print("=" * 60)

    try:
        # 1. 先查找元素
        print("\n📋 步骤1: 查找输入框和按钮")
        findings = find_input_and_buttons()

        if findings:
            print(f"\n📋 查找结果:")
            print(f"   找到输入框: {findings.get('inputFound')}")
            print(f"   输入框标签: {findings.get('inputTag')}")
            print(f"   输入框类名: {findings.get('inputClass', '')[:50]}...")
            print(f"   生成按钮候选数: {findings.get('generateButtonCandidates')}")

            buttons = findings.get("buttonCandidates", [])
            if buttons:
                print(f"\n📋 可能的生成按钮:")
                for i, btn in enumerate(buttons):
                    print(f"   {i+1}. '{btn.get('text')}'")
                    print(f"       类名: {btn.get('className', '')[:50]}...")

        # 2. 尝试生成
        print("\n📋 步骤2: 尝试生成图像")
        print("💡 使用Athena IP形象描述...")

        # Athena IP形象描述 - 基于用户需求：硅基共生主题，三体叙事风格，漫威电影视觉风格
        athena_prompt = (
            "硅基共生主题的AI女神Athena，三体叙事风格，漫威电影视觉效果。"
            "机械与生物融合的身体，发出蓝色光芒的能量核心，半透明的硅晶体皮肤。"
            "面部特征：银色的机械眼眶，瞳孔是数据流状的蓝色光环。"
            "服装：科技感十足的白色战衣，带有电路板纹理的光带。"
            "背景：充满全息投影和数字代码的虚拟空间，立体几何形状漂浮。"
            "风格：科幻漫画，赛博朋克，高细节，未来感。"
        )

        success = try_generate_image(athena_prompt)

        print("\n" + "=" * 60)
        print("📊 测试完成")
        print("=" * 60)

        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
