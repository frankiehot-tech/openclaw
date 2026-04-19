#!/usr/bin/env python3
"""
查找提示词输入框和生成按钮
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def find_prompt_input():
    """查找提示词输入框"""
    print("🔧 查找提示词输入框...")

    cli = DoubaoCLIEnhanced()

    # 方法1：查找包含特定文本的元素
    find_by_text_js = """
    // 查找包含"描述"或"画面"文本的元素
    var promptElements = [];
    var allElements = document.querySelectorAll('*');

    for (var i = 0; i < allElements.length; i++) {
        var elem = allElements[i];
        if (elem.offsetParent !== null) { // 可见
            var text = (elem.textContent || elem.innerText || '').trim();
            if (text.includes('描述你所想象的画面') ||
                text.includes('描述') && text.includes('画面') ||
                text.includes('Prompt') ||
                text.includes('提示词') ||
                text.includes('输入描述')) {
                var info = {
                    tagName: elem.tagName,
                    text: text.substring(0, 100),
                    className: (elem.className || '').substring(0, 100),
                    id: elem.id || '',
                    isInput: elem.tagName === 'TEXTAREA' || elem.tagName === 'INPUT' || elem.hasAttribute('contenteditable'),
                    isLikelyPromptArea: false
                };

                // 检查父元素是否为输入区域
                var parent = elem.parentElement;
                while (parent) {
                    var parentTag = parent.tagName;
                    if (parentTag === 'TEXTAREA' || parentTag === 'INPUT' ||
                        parent.hasAttribute('contenteditable') ||
                        (parent.className || '').toLowerCase().includes('input') ||
                        (parent.className || '').toLowerCase().includes('text')) {
                        info.isLikelyPromptArea = true;
                        break;
                    }
                    parent = parent.parentElement;
                }

                promptElements.push(info);
            }
        }
    }

    JSON.stringify({
        totalElements: allElements.length,
        promptElements: promptElements,
        promptElementCount: promptElements.length
    });
    """

    result = cli.execute_javascript_enhanced(find_by_text_js)
    print(f"查找文本元素结果: success={result.success}, output={repr(result.output)}")

    # 方法2：直接查找所有文本区域和输入框
    find_inputs_js = """
    // 查找所有可能的输入区域
    var allInputs = [];
    var inputs = document.querySelectorAll('textarea, input[type="text"], input[type="search"], [contenteditable="true"]');

    for (var i = 0; i < inputs.length; i++) {
        var input = inputs[i];
        if (input.offsetParent !== null) {
            var info = {
                index: i,
                tagName: input.tagName,
                type: input.type || '',
                placeholder: input.placeholder || '',
                value: (input.value || '').substring(0, 200),
                className: (input.className || '').substring(0, 100),
                id: input.id || '',
                ariaLabel: input.getAttribute('aria-label') || '',
                isContentEditable: input.hasAttribute('contenteditable'),
                isVisible: true,
                rect: ''
            };

            // 获取位置信息
            try {
                var rect = input.getBoundingClientRect();
                info.rect = rect.top + ',' + rect.left + ',' + rect.width + ',' + rect.height;
            } catch(e) {
                info.rect = 'error';
            }

            allInputs.push(info);
        }
    }

    JSON.stringify({
        totalInputs: inputs.length,
        visibleInputs: allInputs.length,
        inputs: allInputs
    });
    """

    result2 = cli.execute_javascript_enhanced(find_inputs_js)
    print(f"查找输入框结果: success={result2.success}, output={repr(result2.output)}")

    # 方法3：查找生成按钮
    find_generate_js = """
    // 查找生成按钮
    var generateButtons = [];
    var buttons = document.querySelectorAll('button, [role="button"]');

    for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        if (btn.offsetParent !== null && !btn.disabled) {
            var text = (btn.textContent || btn.innerText || '').trim();
            var className = (btn.className || '').toLowerCase();
            var ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();

            // 检查是否是生成按钮
            var isGenerateButton = (
                text.includes('生成') || text.includes('创作') || text.includes('画') ||
                text.includes('draw') || text.includes('paint') || text.includes('create') ||
                text.includes('generate') || className.includes('generate') ||
                className.includes('create') || ariaLabel.includes('生成')
            );

            if (isGenerateButton || text) {  // 显示所有有文本的按钮
                var info = {
                    index: i,
                    tagName: btn.tagName,
                    text: text,
                    className: (btn.className || '').substring(0, 100),
                    id: btn.id || '',
                    ariaLabel: btn.getAttribute('aria-label') || '',
                    isGenerateButton: isGenerateButton,
                    disabled: btn.disabled,
                    visible: true
                };
                generateButtons.push(info);
            }
        }
    }

    JSON.stringify({
        totalButtons: buttons.length,
        generateButtons: generateButtons,
        generateButtonCount: generateButtons.length
    });
    """

    result3 = cli.execute_javascript_enhanced(find_generate_js)
    print(f"查找生成按钮结果: success={result3.success}, output={repr(result3.output)}")

    # 解析结果
    try:
        text_result = (
            json.loads(cli._clean_js_output(result.output))
            if result.success and result.output and result.output != "missing value"
            else {}
        )
        inputs_result = (
            json.loads(cli._clean_js_output(result2.output))
            if result2.success and result2.output and result2.output != "missing value"
            else {}
        )
        buttons_result = (
            json.loads(cli._clean_js_output(result3.output))
            if result3.success and result3.output and result3.output != "missing value"
            else {}
        )

        print("\n📋 查找结果摘要:")
        print(f"   包含'描述'文本的元素: {text_result.get('promptElementCount', 0)}")
        print(f"   可见输入框: {inputs_result.get('visibleInputs', 0)}")
        print(f"   可能的生成按钮: {buttons_result.get('generateButtonCount', 0)}")

        # 显示包含'描述'文本的元素
        prompt_elements = text_result.get("promptElements", [])
        if prompt_elements:
            print(f"\n📋 包含'描述'文本的元素:")
            for i, elem in enumerate(prompt_elements[:5]):
                print(f"   {i+1}. 标签: {elem.get('tagName')}")
                print(f"       文本: '{elem.get('text')}'")
                print(f"       类名: {elem.get('className')}")
                print(f"       是输入框: {elem.get('isInput')}")
                print(f"       可能是提示区域: {elem.get('isLikelyPromptArea')}")

        # 显示输入框
        inputs = inputs_result.get("inputs", [])
        if inputs:
            print(f"\n📋 输入框详情:")
            for i, inp in enumerate(inputs[:5]):
                print(f"   {i+1}. 标签: {inp.get('tagName')}, 类型: {inp.get('type')}")
                print(f"       占位符: '{inp.get('placeholder')}'")
                print(f"       值: '{inp.get('value')}'")
                print(f"       类名: {inp.get('className')}")
                print(f"       ID: {inp.get('id')}")
                print(f"       可编辑: {inp.get('isContentEditable')}")

        # 显示生成按钮
        buttons = buttons_result.get("generateButtons", [])
        if buttons:
            print(f"\n📋 可能的生成按钮:")
            for i, btn in enumerate(buttons[:10]):
                if btn.get("text") or btn.get("isGenerateButton"):
                    print(f"   {i+1}. 文本: '{btn.get('text')}'")
                    print(f"       标签: {btn.get('tagName')}")
                    print(f"       类名: {btn.get('className')}")
                    print(f"       是生成按钮: {btn.get('isGenerateButton')}")
                    print(f"       禁用: {btn.get('disabled')}")

        return {
            "text_elements": prompt_elements,
            "inputs": inputs,
            "buttons": buttons,
            "has_prompt_elements": len(prompt_elements) > 0,
            "has_inputs": len(inputs) > 0,
            "has_generate_buttons": any(b.get("isGenerateButton") for b in buttons),
        }

    except Exception as e:
        print(f"解析查找结果失败: {e}")
        return None


def try_input_prompt():
    """尝试输入提示词"""
    print("\n🔧 尝试输入提示词...")

    cli = DoubaoCLIEnhanced()

    # 尝试找到并输入提示词
    input_js = """
    // 尝试输入提示词
    var result = {success: false, message: "未找到输入区域"};

    // 方法1：查找textarea
    var textareas = document.querySelectorAll('textarea');
    for (var i = 0; i < textareas.length; i++) {
        var ta = textareas[i];
        if (ta.offsetParent !== null) {
            console.log('找到textarea，尝试输入');
            ta.value = "一只可爱的卡通猫咪，蓝色眼睛，戴着红色蝴蝶结，背景有彩虹";
            ta.dispatchEvent(new Event('input', { bubbles: true }));
            ta.dispatchEvent(new Event('change', { bubbles: true }));
            result = {success: true, message: "已输入到textarea", element: "textarea"};
            break;
        }
    }

    // 方法2：查找可编辑区域
    if (!result.success) {
        var editable = document.querySelectorAll('[contenteditable="true"]');
        for (var i = 0; i < editable.length; i++) {
            var elem = editable[i];
            if (elem.offsetParent !== null) {
                console.log('找到可编辑区域，尝试输入');
                elem.textContent = "一只可爱的卡通猫咪，蓝色眼睛，戴着红色蝴蝶结，背景有彩虹";
                elem.dispatchEvent(new Event('input', { bubbles: true }));
                result = {success: true, message: "已输入到可编辑区域", element: "contenteditable"};
                break;
            }
        }
    }

    // 方法3：查找任何可能的输入
    if (!result.success) {
        // 查找包含"描述"文本的元素，尝试点击
        var allElements = document.querySelectorAll('*');
        for (var i = 0; i < allElements.length; i++) {
            var elem = allElements[i];
            if (elem.offsetParent !== null) {
                var text = (elem.textContent || elem.innerText || '').trim();
                if (text.includes('描述') || text.includes('输入')) {
                    console.log('找到描述元素，尝试点击');
                    elem.click();
                    result = {success: true, message: "已点击描述元素", element: "description"};
                    break;
                }
            }
        }
    }

    JSON.stringify(result);
    """

    result = cli.execute_javascript_enhanced(input_js)
    print(f"输入提示词结果: success={result.success}, output={repr(result.output)}")

    # 等待一下
    time.sleep(2)

    return result.success and result.output and "success" in result.output


def main():
    """主函数"""
    print("🎯 查找提示词输入框和生成按钮")
    print("=" * 60)

    try:
        # 1. 查找元素
        print("\n📋 步骤1: 查找界面元素")
        findings = find_prompt_input()

        if not findings:
            print("❌ 无法查找界面元素")
            return 1

        # 2. 如果找到元素，尝试输入提示词
        if findings.get("has_inputs") or findings.get("has_prompt_elements"):
            print("\n📋 步骤2: 尝试输入提示词")
            input_success = try_input_prompt()

            if input_success:
                print("\n✅ 成功输入提示词")
            else:
                print("\n❌ 未能输入提示词")
        else:
            print("\n⚠️  未找到输入元素")

        print("\n" + "=" * 60)
        print("📊 测试完成")
        print("=" * 60)

        return 0 if findings else 1

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
