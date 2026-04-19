#!/usr/bin/env python3
"""
检查页面按钮详细信息
"""

import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def check_page_buttons():
    """检查页面按钮详细信息"""
    print("🔧 检查页面按钮详细信息...")

    cli = DoubaoCLIEnhanced()

    # 检查页面上的所有按钮
    button_check_js = """
    // 检查所有按钮
    var buttonInfo = {
        total: document.querySelectorAll('button').length,
        buttons: []
    };

    var buttons = document.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        var info = {
            index: i,
            tagName: btn.tagName,
            text: (btn.textContent || btn.innerText || '').trim(),
            className: btn.className || '',
            id: btn.id || '',
            ariaLabel: btn.getAttribute('aria-label') || '',
            disabled: btn.disabled,
            visible: btn.offsetParent !== null,
            onClick: btn.hasAttribute('onclick'),
            hasClickHandler: typeof btn.onclick === 'function'
        };
        buttonInfo.buttons.push(info);
    }

    // 也检查div和a标签，因为它们可能被用作按钮
    var clickableDivs = document.querySelectorAll('div[onclick], a[onclick], [role="button"]');
    for (var i = 0; i < clickableDivs.length; i++) {
        var elem = clickableDivs[i];
        var info = {
            index: buttonInfo.buttons.length + i,
            tagName: elem.tagName,
            text: (elem.textContent || elem.innerText || '').trim(),
            className: elem.className || '',
            id: elem.id || '',
            ariaLabel: elem.getAttribute('aria-label') || '',
            role: elem.getAttribute('role') || '',
            visible: elem.offsetParent !== null,
            onClick: elem.hasAttribute('onclick'),
            hasClickHandler: typeof elem.onclick === 'function'
        };
        buttonInfo.buttons.push(info);
    }

    JSON.stringify(buttonInfo);
    """

    result = cli.execute_javascript_enhanced(button_check_js)
    print(f"执行结果: success={result.success}, output={repr(result.output)}")

    if result.success and result.output and result.output != "missing value":
        try:
            button_info = json.loads(cli._clean_js_output(result.output))
            print(f"\n📋 按钮信息:")
            print(f"   总按钮数量: {button_info.get('total')}")
            print(f"   检查到的可点击元素数量: {len(button_info.get('buttons', []))}")

            for i, btn in enumerate(button_info.get("buttons", [])):
                print(f"\n   {i+1}. 按钮信息:")
                print(f"      标签: {btn.get('tagName')}")
                print(f"      文本: '{btn.get('text')}'")
                print(f"      类名: {btn.get('className')}")
                print(f"      ID: {btn.get('id')}")
                print(f"      aria-label: '{btn.get('ariaLabel')}'")
                print(f"      是否禁用: {btn.get('disabled')}")
                print(f"      是否可见: {btn.get('visible')}")
                print(f"      有onclick属性: {btn.get('onClick')}")
                if btn.get("tagName") != "BUTTON":
                    print(f"      角色: {btn.get('role', 'N/A')}")

            return button_info
        except Exception as e:
            print(f"解析按钮信息失败: {e}")
            return None
    else:
        print(f"获取按钮信息失败")
        return None


def main():
    """主函数"""
    print("🎯 页面按钮检查")
    print("=" * 60)

    try:
        button_info = check_page_buttons()

        print("\n" + "=" * 60)
        print("📊 分析结果")
        print("=" * 60)

        if button_info:
            buttons = button_info.get("buttons", [])
            print(f"找到 {len(buttons)} 个可点击元素")

            # 查找可能的AI绘画入口
            ai_keywords = [
                "绘画",
                "画画",
                "生成",
                "创作",
                "开始",
                "AI",
                "Draw",
                "Paint",
                "Generate",
                "Create",
            ]
            possible_entries = []

            for btn in buttons:
                text = btn.get("text", "").lower()
                aria = btn.get("ariaLabel", "").lower()
                className = btn.get("className", "").lower()

                for keyword in ai_keywords:
                    if (
                        keyword.lower() in text
                        or keyword.lower() in aria
                        or keyword.lower() in className
                    ):
                        possible_entries.append(btn)
                        break

            if possible_entries:
                print(f"\n✅ 找到 {len(possible_entries)} 个可能的AI绘画入口:")
                for i, btn in enumerate(possible_entries):
                    print(f"\n   {i+1}. '{btn.get('text')}'")
                    print(f"      标签: {btn.get('tagName')}")
                    print(f"      类名: {btn.get('className')}")
                    print(f"      是否可见: {btn.get('visible')}")

                    if btn.get("tagName") == "BUTTON":
                        print(f"      类型: 标准按钮")
                    elif btn.get("role") == "button":
                        print(f"      类型: ARIA按钮")
                    elif btn.get("onClick") or btn.get("hasClickHandler"):
                        print(f"      类型: 可点击元素")
                    else:
                        print(f"      类型: 普通元素")
            else:
                print(f"\n❌ 未找到明显的AI绘画入口")
                print(f"\n🔧 建议尝试:")
                print(f"1. 查看页面是否有隐藏的菜单或侧边栏")
                print(f"2. 尝试在页面中搜索'AI绘画'相关文字")
                print(f"3. 检查是否需要在聊天中激活AI绘画功能")

        return 0 if button_info else 1

    except Exception as e:
        print(f"\n❌ 检查出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
