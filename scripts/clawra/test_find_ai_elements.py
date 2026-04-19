#!/usr/bin/env python3
"""
查找AI绘画界面元素
"""

import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def find_ai_elements():
    """查找AI绘画界面元素"""
    print("🔧 查找AI绘画界面元素...")

    cli = DoubaoCLIEnhanced()

    # 首先，尝试更全面地探索页面
    print("\n📋 全面页面探索")
    explore_js = """
    // 全面探索页面结构
    var exploration = {
        // 所有可见元素
        allElements: {
            buttons: [],
            inputs: [],
            textareas: [],
            links: [],
            divs: [],
            spans: [],
            sections: [],
            navs: [],
            menus: []
        },

        // 文本内容分析
        textContent: {
            fullText: document.body.innerText || '',
            hasAIPaintingKeywords: false,
            aiKeywordsFound: []
        },

        // 页面结构
        pageStructure: {
            hasMainContent: document.querySelector('main, [role="main"], #main, .main') !== null,
            hasSidebar: document.querySelector('aside, [role="complementary"], .sidebar, .side-nav') !== null,
            hasHeader: document.querySelector('header, [role="banner"]') !== null,
            hasFooter: document.querySelector('footer, [role="contentinfo"]') !== null,
            hasNavigation: document.querySelector('nav, [role="navigation"]') !== null,
            hasMenu: document.querySelector('menu, [role="menu"], .menu') !== null
        },

        // 特定AI相关元素
        aiSpecific: {
            // 聊天界面元素
            hasChatInput: document.querySelector('[contenteditable="true"], .chat-input, [placeholder*="输入"]') !== null,
            hasSendButton: document.querySelector('button:contains("发送"), button:contains("Send")') !== null,
            hasMessageList: document.querySelector('.messages, .chat-history, [role="log"]') !== null,

            // AI绘画特定元素
            hasModelSelector: document.querySelector('select[name*="model"], [class*="model-select"]') !== null,
            hasStyleGrid: document.querySelector('.style-grid, .style-selector, [class*="style-options"]') !== null,
            hasSizeOptions: document.querySelector('.size-options, [class*="size-selector"]') !== null,
            hasGenerateArea: document.querySelector('.generate-area, .result-area, .output-area') !== null
        }
    };

    // 检查AI关键词
    var aiKeywords = ['AI绘画', 'AI创作', '绘画', '画图', '生成', '创作', 'prompt', '提示词', '模型', '风格', '尺寸', '质量'];
    var fullText = exploration.textContent.fullText.toLowerCase();
    for (var i = 0; i < aiKeywords.length; i++) {
        if (fullText.includes(aiKeywords[i].toLowerCase())) {
            exploration.textContent.hasAIPaintingKeywords = true;
            exploration.textContent.aiKeywordsFound.push(aiKeywords[i]);
        }
    }

    // 收集按钮信息（前50个）
    var buttons = document.querySelectorAll('button, [role="button"], [onclick]');
    for (var i = 0; i < Math.min(buttons.length, 50); i++) {
        var btn = buttons[i];
        var info = {
            tagName: btn.tagName,
            text: (btn.textContent || btn.innerText || '').trim().substring(0, 100),
            className: (btn.className || '').substring(0, 100),
            id: btn.id || '',
            ariaLabel: btn.getAttribute('aria-label') || '',
            onClick: btn.hasAttribute('onclick'),
            hasClickHandler: typeof btn.onclick === 'function',
            visible: btn.offsetParent !== null, // 是否可见
            disabled: btn.disabled
        };
        exploration.allElements.buttons.push(info);
    }

    // 收集输入框和文本区域（前30个）
    var inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
    for (var i = 0; i < Math.min(inputs.length, 30); i++) {
        var input = inputs[i];
        var info = {
            tagName: input.tagName,
            type: input.type || '',
            placeholder: (input.placeholder || '').substring(0, 100),
            value: (input.value || '').substring(0, 200),
            className: (input.className || '').substring(0, 100),
            id: input.id || '',
            ariaLabel: input.getAttribute('aria-label') || '',
            visible: input.offsetParent !== null
        };
        if (input.tagName === 'TEXTAREA') {
            exploration.allElements.textareas.push(info);
        } else {
            exploration.allElements.inputs.push(info);
        }
    }

    // 收集链接（前30个）
    var links = document.querySelectorAll('a[href]');
    for (var i = 0; i < Math.min(links.length, 30); i++) {
        var link = links[i];
        var info = {
            text: (link.textContent || link.innerText || '').trim().substring(0, 100),
            href: link.getAttribute('href') || '',
            className: (link.className || '').substring(0, 100),
            visible: link.offsetParent !== null
        };
        exploration.allElements.links.push(info);
    }

    // 收集重要的div和section（前20个）
    var importantContainers = document.querySelectorAll('div[class], section[class], main[class], aside[class]');
    for (var i = 0; i < Math.min(importantContainers.length, 20); i++) {
        var container = importantContainers[i];
        var info = {
            tagName: container.tagName,
            className: (container.className || '').substring(0, 100),
            id: container.id || '',
            text: (container.textContent || container.innerText || '').trim().substring(0, 200),
            visible: container.offsetParent !== null
        };
        if (container.tagName === 'DIV') {
            exploration.allElements.divs.push(info);
        } else if (container.tagName === 'SECTION') {
            exploration.allElements.sections.push(info);
        }
    }

    // 尝试查找任何菜单或导航项
    var menuItems = document.querySelectorAll('[role="menuitem"], .menu-item, nav a, [class*="nav-item"]');
    for (var i = 0; i < Math.min(menuItems.length, 20); i++) {
        var item = menuItems[i];
        var info = {
            text: (item.textContent || item.innerText || '').trim().substring(0, 100),
            tagName: item.tagName,
            className: (item.className || '').substring(0, 100),
            href: item.getAttribute('href') || '',
            role: item.getAttribute('role') || '',
            visible: item.offsetParent !== null
        };
        exploration.allElements.menus.push(info);
    }

    JSON.stringify(exploration);
    """

    result = cli.execute_javascript_enhanced(explore_js)
    if result.success and result.output and result.output != "missing value":
        try:
            exploration = json.loads(cli._clean_js_output(result.output))

            print(
                f"   页面标题: {exploration.get('textContent', {}).get('fullText', '').split('\\n')[0].strip()[:100]}..."
            )
            print(f"   URL: 需要从页面获取")

            print(f"   \n   页面结构:")
            structure = exploration.get("pageStructure", {})
            print(f"     有主要内容区: {structure.get('hasMainContent')}")
            print(f"     有侧边栏: {structure.get('hasSidebar')}")
            print(f"     有页眉: {structure.get('hasHeader')}")
            print(f"     有页脚: {structure.get('hasFooter')}")
            print(f"     有导航栏: {structure.get('hasNavigation')}")
            print(f"     有菜单: {structure.get('hasMenu')}")

            print(f"   \n   AI特定元素:")
            ai_specific = exploration.get("aiSpecific", {})
            print(f"     有聊天输入框: {ai_specific.get('hasChatInput')}")
            print(f"     有发送按钮: {ai_specific.get('hasSendButton')}")
            print(f"     有消息列表: {ai_specific.get('hasMessageList')}")
            print(f"     有模型选择器: {ai_specific.get('hasModelSelector')}")
            print(f"     有风格网格: {ai_specific.get('hasStyleGrid')}")
            print(f"     有尺寸选项: {ai_specific.get('hasSizeOptions')}")
            print(f"     有生成区域: {ai_specific.get('hasGenerateArea')}")

            print(f"   \n   AI关键词:")
            text_content = exploration.get("textContent", {})
            print(f"     包含AI绘画关键词: {text_content.get('hasAIPaintingKeywords')}")
            print(f"     找到的关键词: {', '.join(text_content.get('aiKeywordsFound', []))}")

            print(
                f"   \n   按钮统计 ({len(exploration.get('allElements', {}).get('buttons', []))}个):"
            )
            buttons = exploration.get("allElements", {}).get("buttons", [])
            visible_buttons = [btn for btn in buttons if btn.get("visible")]
            print(f"     可见按钮: {len(visible_buttons)}个")

            print(f"   \n   可见按钮文本:")
            for i, btn in enumerate(visible_buttons[:15]):
                text = btn.get("text", "").strip()
                if text:
                    print(
                        f"     {i+1}. '{text}' (类名: {btn.get('className', 'N/A')}, 标签: {btn.get('tagName')})"
                    )

            print(
                f"   \n   输入框/文本区域 ({len(exploration.get('allElements', {}).get('inputs', [])) + len(exploration.get('allElements', {}).get('textareas', []))}个):"
            )
            inputs = exploration.get("allElements", {}).get("inputs", [])
            textareas = exploration.get("allElements", {}).get("textareas", [])

            all_inputs = inputs + textareas
            visible_inputs = [inp for inp in all_inputs if inp.get("visible")]
            print(f"     可见输入框: {len(visible_inputs)}个")

            for i, inp in enumerate(visible_inputs[:10]):
                placeholder = inp.get("placeholder", "").strip()
                value = inp.get("value", "").strip()
                if placeholder or value:
                    print(
                        f"     {i+1}. 占位符: '{placeholder}', 值: '{value[:50]}...', 类型: {inp.get('type', 'N/A')}"
                    )

            print(f"   \n   链接 ({len(exploration.get('allElements', {}).get('links', []))}个):")
            links = exploration.get("allElements", {}).get("links", [])
            visible_links = [link for link in links if link.get("visible")]
            print(f"     可见链接: {len(visible_links)}个")

            for i, link in enumerate(visible_links[:10]):
                text = link.get("text", "").strip()
                href = link.get("href", "").strip()
                if text or href:
                    print(f"     {i+1}. 文本: '{text}', 链接: '{href}'")

            print(
                f"   \n   菜单/导航项 ({len(exploration.get('allElements', {}).get('menus', []))}个):"
            )
            menus = exploration.get("allElements", {}).get("menus", [])
            visible_menus = [menu for menu in menus if menu.get("visible")]
            print(f"     可见菜单项: {len(visible_menus)}个")

            for i, menu in enumerate(visible_menus[:10]):
                text = menu.get("text", "").strip()
                href = menu.get("href", "").strip()
                if text:
                    print(f"     {i+1}. '{text}' (链接: '{href}', 角色: {menu.get('role', 'N/A')})")

            # 分析是否为AI绘画界面
            is_ai_interface = (
                text_content.get("hasAIPaintingKeywords")
                or ai_specific.get("hasModelSelector")
                or ai_specific.get("hasStyleGrid")
                or ai_specific.get("hasGenerateArea")
            )

            print(f"   \n   🔍 综合分析:")
            print(f"     可能是AI绘画界面: {is_ai_interface}")

            # 如果有聊天输入框，可能是聊天界面而不是绘画界面
            if ai_specific.get("hasChatInput"):
                print(f"     ⚠️  检测到聊天输入框，可能是聊天界面而不是专门的绘画界面")

            return exploration, is_ai_interface

        except Exception as e:
            print(f"   解析探索结果失败: {e}")
            import traceback

            traceback.print_exc()
            return None, False
    else:
        print(f"   获取页面探索结果失败: success={result.success}, output={repr(result.output)}")
        return None, False


def main():
    """主函数"""
    print("🎯 AI绘画界面元素探索")
    print("=" * 60)

    try:
        exploration, is_ai_interface = find_ai_elements()

        print("\n" + "=" * 60)
        print("📊 探索总结")
        print("=" * 60)

        if is_ai_interface:
            print("✅ 可能在AI绘画界面或相关界面")
            print("\n💡 下一步:")
            print("1. 尝试输入提示词")
            print("2. 查找生成按钮")
            print("3. 测试图像生成功能")
        else:
            print("❌ 不在AI绘画界面")
            print("\n🔧 问题分析:")
            print("1. 豆包可能显示的是普通聊天界面")
            print("2. AI绘画功能可能需要特定操作才能显示")
            print("3. 可能需要手动在豆包中找到AI绘画入口")
            print("\n💡 解决方案:")
            print("1. 尝试在聊天中输入'AI绘画'或'画画'")
            print("2. 查找侧边栏或菜单中的AI绘画选项")
            print("3. 检查豆包是否支持AI绘画功能")

        return 0 if is_ai_interface else 1

    except Exception as e:
        print(f"\n❌ 探索出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
