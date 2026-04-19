#!/usr/bin/env python3
"""
查找真正的生成按钮
"""

import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def find_all_buttons():
    """查找所有按钮"""
    print("🔧 查找所有按钮...")

    cli = DoubaoCLIEnhanced()

    # 查找所有按钮并获取详细信息
    find_js = """
    // 查找所有按钮
    var allButtons = [];
    var elements = document.querySelectorAll('button, [role="button"], div, span, a');

    for (var i = 0; i < elements.length; i++) {
        var elem = elements[i];
        if (elem.offsetParent !== null) { // 可见元素
            var text = (elem.textContent || elem.innerText || '').trim();
            var tagName = elem.tagName;
            var className = elem.className || '';
            var id = elem.id || '';
            var ariaLabel = elem.getAttribute('aria-label') || '';

            // 获取元素位置
            var rect = '';
            try {
                var r = elem.getBoundingClientRect();
                rect = r.top + ',' + r.left + ',' + r.width + ',' + r.height;
            } catch(e) {
                rect = 'error';
            }

            // 检查是否可能是生成按钮
            var isPossibleGenerate = false;
            var textLower = text.toLowerCase();
            var ariaLabelLower = ariaLabel.toLowerCase();
            var classNameLower = className.toLowerCase();

            if (textLower.includes('生成') || textLower.includes('创作') || textLower.includes('开始') ||
                textLower.includes('draw') || textLower.includes('paint') || textLower.includes('create') ||
                textLower.includes('generate') || ariaLabelLower.includes('生成') ||
                classNameLower.includes('generate') || classNameLower.includes('create') ||
                text === '开始创作' || text === '立即生成' || text === '生成图片') {
                isPossibleGenerate = true;
            }

            // 只收集有文本或可能是生成按钮的元素
            if (text || isPossibleGenerate || ariaLabel || id.includes('generate') || id.includes('create')) {
                allButtons.push({
                    index: i,
                    tagName: tagName,
                    text: text,
                    className: className.substring(0, 100),
                    id: id,
                    ariaLabel: ariaLabel,
                    rect: rect,
                    isPossibleGenerate: isPossibleGenerate,
                    visible: true
                });
            }
        }
    }

    // 按位置排序（从上到下，从左到右）
    allButtons.sort(function(a, b) {
        var aRect = a.rect.split(',');
        var bRect = b.rect.split(',');
        var aTop = parseFloat(aRect[0]) || 0;
        var bTop = parseFloat(bRect[0]) || 0;
        var aLeft = parseFloat(aRect[1]) || 0;
        var bLeft = parseFloat(bRect[1]) || 0;

        if (aTop !== bTop) return aTop - bTop;
        return aLeft - bLeft;
    });

    JSON.stringify({
        totalButtons: allButtons.length,
        buttons: allButtons
    });
    """

    result = cli.execute_javascript_enhanced(find_js)
    print(
        f"查找结果: success={result.success}, output={repr(result.output[:300]) if result.output else 'None'}"
    )

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


def analyze_button_locations(data):
    """分析按钮位置"""
    if not data or "buttons" not in data:
        print("❌ 无按钮数据")
        return

    buttons = data["buttons"]

    print(f"\n📋 按钮统计:")
    print(f"   总按钮数: {len(buttons)}")

    # 按位置分组
    position_groups = {}
    for btn in buttons:
        rect = btn.get("rect", "")
        if rect and "," in rect:
            parts = rect.split(",")
            if len(parts) >= 2:
                top = int(float(parts[0]) / 50) * 50  # 按50像素分组
                left = int(float(parts[1]) / 50) * 50
                key = f"{top}-{left}"
                if key not in position_groups:
                    position_groups[key] = []
                position_groups[key].append(btn)

    print(f"\n📋 按钮位置分组:")
    for key in sorted(position_groups.keys()):
        group = position_groups[key]
        if len(group) > 0:
            top, left = key.split("-")
            print(f"  位置: top={top}, left={left}")
            for btn in group[:3]:  # 显示前3个
                text = btn.get("text", "")
                if text:
                    print(f"    - '{text}' ({btn.get('tagName')})")

    # 分析可能的生成按钮
    print(f"\n📋 可能的生成按钮:")
    generate_candidates = []
    for btn in buttons:
        if btn.get("isPossibleGenerate"):
            generate_candidates.append(btn)

    if generate_candidates:
        for i, btn in enumerate(generate_candidates[:10]):
            print(f"  {i+1}. '{btn.get('text')}'")
            print(f"      标签: {btn.get('tagName')}")
            print(f"      ID: {btn.get('id')}")
            print(f"      aria-label: {btn.get('ariaLabel')}")
            print(f"      类名: {btn.get('className', '')[:50]}...")
            print(f"      位置: {btn.get('rect')}")
    else:
        print("  （未找到明确的生成按钮）")

    # 查找文本中包含"生成"或"创作"的按钮
    print(f"\n📋 包含关键词的按钮:")
    keyword_buttons = []
    for btn in buttons:
        text = btn.get("text", "").lower()
        if "生成" in text or "创作" in text or "开始" in text:
            keyword_buttons.append(btn)

    if keyword_buttons:
        for i, btn in enumerate(keyword_buttons):
            print(f"  {i+1}. '{btn.get('text')}'")
            print(f"      标签: {btn.get('tagName')}")
            print(f"      类名: {btn.get('className', '')[:30]}...")
    else:
        print("  （未找到包含关键词的按钮）")


def check_ai_creation_flow():
    """检查AI创作流程"""
    print("\n🔧 检查AI创作流程元素...")

    cli = DoubaoCLIEnhanced()

    # 检查是否有模型选择、比例选择、风格选择等
    flow_js = """
    // 检查AI创作流程元素
    var flowElements = {
        // 模型选择
        modelSelectors: [],

        // 比例选择
        ratioSelectors: [],

        // 风格选择
        styleSelectors: [],

        // 提示词输入
        promptInputs: [],

        // 生成按钮
        generateButtons: []
    };

    // 查找所有可能的选择器
    var allElements = document.querySelectorAll('button, div, span, [role="button"]');
    for (var i = 0; i < allElements.length; i++) {
        var elem = allElements[i];
        if (elem.offsetParent !== null) {
            var text = (elem.textContent || elem.innerText || '').trim();
            var className = elem.className || '';
            var ariaLabel = elem.getAttribute('aria-label') || '';
            var id = elem.id || '';

            // 模型选择
            if (text.includes('Seedream') || text.includes('模型') ||
                className.includes('model') || ariaLabel.includes('model')) {
                flowElements.modelSelectors.push({
                    text: text,
                    className: className.substring(0, 50),
                    id: id,
                    ariaLabel: ariaLabel
                });
            }

            // 比例选择
            if (text.includes('比例') || text.includes('尺寸') || text.includes('大小') ||
                className.includes('ratio') || className.includes('size') ||
                ariaLabel.includes('ratio') || ariaLabel.includes('size')) {
                flowElements.ratioSelectors.push({
                    text: text,
                    className: className.substring(0, 50),
                    id: id,
                    ariaLabel: ariaLabel
                });
            }

            // 风格选择
            if (text.includes('风格') || text.includes('style') ||
                className.includes('style') || ariaLabel.includes('style')) {
                flowElements.styleSelectors.push({
                    text: text,
                    className: className.substring(0, 50),
                    id: id,
                    ariaLabel: ariaLabel
                });
            }

            // 生成按钮
            if (text.includes('生成') || text.includes('创作') || text.includes('开始') ||
                className.includes('generate') || className.includes('create')) {
                flowElements.generateButtons.push({
                    text: text,
                    className: className.substring(0, 50),
                    id: id,
                    ariaLabel: ariaLabel
                });
            }
        }
    }

    // 查找提示词输入
    var inputs = document.querySelectorAll('[contenteditable="true"], textarea, input[type="text"]');
    for (var i = 0; i < inputs.length; i++) {
        var input = inputs[i];
        if (input.offsetParent !== null) {
            var placeholder = input.placeholder || '';
            var className = input.className || '';
            if (placeholder.includes('描述') || placeholder.includes('提示词') ||
                className.includes('prompt') || className.includes('input')) {
                flowElements.promptInputs.push({
                    tagName: input.tagName,
                    placeholder: placeholder,
                    className: className.substring(0, 50),
                    value: input.value || ''
                });
            }
        }
    }

    JSON.stringify(flowElements);
    """

    result = cli.execute_javascript_enhanced(flow_js)
    print(
        f"流程检查结果: success={result.success}, output={repr(result.output[:300]) if result.output else 'None'}"
    )

    if result.success and result.output and result.output != "missing value":
        try:
            flow_data = json.loads(cli._clean_js_output(result.output))

            print(f"\n📋 AI创作流程元素:")
            print(f"   模型选择器: {len(flow_data.get('modelSelectors', []))}")
            for i, selector in enumerate(flow_data.get("modelSelectors", [])[:3]):
                print(f"     {i+1}. '{selector.get('text')}'")

            print(f"   比例选择器: {len(flow_data.get('ratioSelectors', []))}")
            for i, selector in enumerate(flow_data.get("ratioSelectors", [])[:3]):
                print(f"     {i+1}. '{selector.get('text')}'")

            print(f"   风格选择器: {len(flow_data.get('styleSelectors', []))}")
            for i, selector in enumerate(flow_data.get("styleSelectors", [])[:3]):
                print(f"     {i+1}. '{selector.get('text')}'")

            print(f"   提示词输入: {len(flow_data.get('promptInputs', []))}")
            for i, input in enumerate(flow_data.get("promptInputs", [])):
                print(f"     {i+1}. {input.get('tagName')}: '{input.get('placeholder')}'")

            print(f"   生成按钮: {len(flow_data.get('generateButtons', []))}")
            for i, btn in enumerate(flow_data.get("generateButtons", [])):
                print(f"     {i+1}. '{btn.get('text')}'")

            return flow_data
        except Exception as e:
            print(f"解析流程数据失败: {e}")
            return None
    else:
        print(f"流程检查失败")
        return None


def main():
    """主函数"""
    print("🎯 查找真正的生成按钮")
    print("=" * 60)

    try:
        # 1. 查找所有按钮
        print("\n📋 步骤1: 查找所有按钮")
        button_data = find_all_buttons()

        if button_data:
            # 2. 分析按钮位置
            print("\n📋 步骤2: 分析按钮位置")
            analyze_button_locations(button_data)

        # 3. 检查AI创作流程
        print("\n📋 步骤3: 检查AI创作流程")
        flow_data = check_ai_creation_flow()

        print("\n" + "=" * 60)
        print("📊 分析完成")
        print("=" * 60)

        return 0 if button_data else 1

    except Exception as e:
        print(f"\n❌ 分析出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
