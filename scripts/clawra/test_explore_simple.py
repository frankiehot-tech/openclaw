#!/usr/bin/env python3
"""
简化版AI创作界面探索
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def explore_simple():
    """简单探索AI创作界面"""
    print("🔧 简单探索AI创作界面...")

    cli = DoubaoCLIEnhanced()

    # 第1步：基本页面信息
    basic_js = """
    // 获取基本页面信息
    var basicInfo = {
        title: document.title,
        url: window.location.href,
        path: window.location.pathname,
        hasBody: !!document.body
    };
    JSON.stringify(basicInfo);
    """

    result = cli.execute_javascript_enhanced(basic_js)
    print(f"基本页面信息: success={result.success}, output={repr(result.output)}")

    if not result.success or not result.output or result.output == "missing value":
        print("❌ 无法获取基本页面信息")
        return None

    # 第2步：查找按钮数量
    buttons_js = """
    // 统计按钮数量
    var buttons = document.querySelectorAll('button');
    var visibleButtons = 0;
    for (var i = 0; i < buttons.length; i++) {
        if (buttons[i].offsetParent !== null) {
            visibleButtons++;
        }
    }
    var buttonInfo = {
        totalButtons: buttons.length,
        visibleButtons: visibleButtons,
        buttonTexts: []
    };

    // 收集前5个可见按钮的文本
    for (var i = 0; i < Math.min(buttons.length, 5); i++) {
        if (buttons[i].offsetParent !== null) {
            buttonInfo.buttonTexts.push((buttons[i].textContent || buttons[i].innerText || '').trim());
        }
    }

    JSON.stringify(buttonInfo);
    """

    result2 = cli.execute_javascript_enhanced(buttons_js)
    print(f"按钮信息: success={result2.success}, output={repr(result2.output)}")

    # 第3步：查找输入框
    inputs_js = """
    // 查找输入框
    var inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
    var inputInfo = {
        totalInputs: inputs.length,
        inputs: []
    };

    for (var i = 0; i < Math.min(inputs.length, 10); i++) {
        var input = inputs[i];
        if (input.offsetParent !== null) {
            var info = {
                tagName: input.tagName,
                type: input.type || '',
                placeholder: input.placeholder || '',
                value: (input.value || '').substring(0, 100),
                visible: true
            };
            inputInfo.inputs.push(info);
        }
    }

    JSON.stringify(inputInfo);
    """

    result3 = cli.execute_javascript_enhanced(inputs_js)
    print(f"输入框信息: success={result3.success}, output={repr(result3.output)}")

    # 第4步：检查是否有生成相关的元素
    generate_check_js = """
    // 检查生成相关元素
    var generateCheck = {
        hasGenerateText: false,
        hasPromptText: false,
        pageText: (document.body.innerText || '').substring(0, 2000).toLowerCase()
    };

    // 检查文本中是否有生成相关关键词
    var text = generateCheck.pageText;
    if (text.includes('生成') || text.includes('创作') || text.includes('画') ||
        text.includes('draw') || text.includes('paint') || text.includes('create')) {
        generateCheck.hasGenerateText = true;
    }

    if (text.includes('提示词') || text.includes('prompt') || text.includes('描述')) {
        generateCheck.hasPromptText = true;
    }

    JSON.stringify(generateCheck);
    """

    result4 = cli.execute_javascript_enhanced(generate_check_js)
    print(f"生成检查: success={result4.success}, output={repr(result4.output)}")

    # 尝试解析所有结果
    all_data = {}
    try:
        all_data["basic"] = json.loads(cli._clean_js_output(result.output))
        all_data["buttons"] = (
            json.loads(cli._clean_js_output(result2.output))
            if result2.success and result2.output and result2.output != "missing value"
            else {}
        )
        all_data["inputs"] = (
            json.loads(cli._clean_js_output(result3.output))
            if result3.success and result3.output and result3.output != "missing value"
            else {}
        )
        all_data["generate_check"] = (
            json.loads(cli._clean_js_output(result4.output))
            if result4.success and result4.output and result4.output != "missing value"
            else {}
        )

        print("\n📋 探索结果摘要:")
        print(f"   页面标题: {all_data['basic'].get('title')}")
        print(f"   页面路径: {all_data['basic'].get('path')}")
        print(f"   总按钮数: {all_data['buttons'].get('totalButtons', 'N/A')}")
        print(f"   可见按钮数: {all_data['buttons'].get('visibleButtons', 'N/A')}")
        print(f"   总输入框数: {all_data['inputs'].get('totalInputs', 'N/A')}")
        print(f"   有生成文本: {all_data['generate_check'].get('hasGenerateText', 'N/A')}")
        print(f"   有提示词文本: {all_data['generate_check'].get('hasPromptText', 'N/A')}")

        # 显示按钮文本
        button_texts = all_data["buttons"].get("buttonTexts", [])
        if button_texts:
            print(f"\n📋 可见按钮文本:")
            for i, text in enumerate(button_texts):
                print(f"   {i+1}. '{text}'")

        # 显示输入框信息
        inputs = all_data["inputs"].get("inputs", [])
        if inputs:
            print(f"\n📋 输入框信息:")
            for i, inp in enumerate(inputs[:3]):
                print(f"   {i+1}. 标签: {inp.get('tagName')}, 类型: {inp.get('type')}")
                print(f"       占位符: '{inp.get('placeholder')}'")
                print(f"       值: '{inp.get('value')}'")

        return all_data

    except Exception as e:
        print(f"解析探索结果失败: {e}")
        return None


def main():
    """主函数"""
    print("🎯 简化版AI创作界面探索")
    print("=" * 60)

    try:
        result = explore_simple()

        print("\n" + "=" * 60)
        print("📊 探索完成")
        print("=" * 60)

        return 0 if result else 1

    except Exception as e:
        print(f"\n❌ 探索出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
