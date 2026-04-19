#!/usr/bin/env python3
"""
探索豆包AI可用的命令和技能
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def explore_commands_and_skills():
    print("=== 探索豆包AI命令和技能 ===")

    # 创建实例
    doubao = DoubaoCLI()

    print("1. 打开豆包AI页面...")
    try:
        result = doubao.open_doubao_ai()
        print(f"✅ {result}")
        time.sleep(3)
    except Exception as e:
        print(f"❌ 打开AI页面失败: {e}")
        return False

    print("\n2. 探索输入框的提示和可用命令...")

    # 检查输入框的placeholder和可能的命令提示
    explore_js = """
    (function() {
        // 查找输入框
        var textarea = document.querySelector('textarea');
        if (!textarea) {
            return JSON.stringify({success: false, message: "未找到输入框"});
        }

        var analysis = {
            placeholder: textarea.placeholder || '',
            value: textarea.value || '',
            className: textarea.className || '',
            dataset: {},
            surroundingElements: [],
            commandSuggestions: []
        };

        // 获取data属性
        for (var key in textarea.dataset) {
            analysis.dataset[key] = textarea.dataset[key];
        }

        // 查找周围的元素，可能包含命令提示
        var parent = textarea.parentElement;
        for (var i = 0; i < 5 && parent; i++) {
            var siblings = Array.from(parent.children || []);
            analysis.surroundingElements.push({
                level: i,
                tagName: parent.tagName,
                className: parent.className.substring(0, 50),
                childCount: siblings.length
            });
            parent = parent.parentElement;
        }

        // 查找可能的命令建议或技能列表
        var allElements = document.querySelectorAll('*');
        var commandElements = [];
        var skillKeywords = ['技能', '命令', 'command', 'skill', '功能', 'feature', '/'];

        allElements.forEach(el => {
            if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                var text = (el.textContent || el.innerText || '').toLowerCase();
                var placeholder = (el.placeholder || '').toLowerCase();
                var ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();

                var combined = text + ' ' + placeholder + ' ' + ariaLabel;
                if (skillKeywords.some(keyword => combined.includes(keyword))) {
                    commandElements.push({
                        tagName: el.tagName,
                        text: (el.textContent || el.innerText || '').trim().substring(0, 100),
                        placeholder: el.placeholder || '',
                        ariaLabel: el.getAttribute('aria-label') || '',
                        className: el.className.substring(0, 30),
                        selector: generateSelector(el)
                    });
                }
            }
        });

        analysis.commandSuggestions = commandElements;

        // 检查是否有下拉或自动完成组件
        var dropdowns = document.querySelectorAll('[role="listbox"], [role="menu"], .dropdown, .autocomplete');
        analysis.dropdowns = Array.from(dropdowns).map((d, idx) => ({
            index: idx,
            role: d.getAttribute('role') || '',
            className: d.className.substring(0, 30),
            isVisible: d.offsetWidth > 0 && d.offsetHeight > 0
        }));

        return JSON.stringify(analysis, null, 2);

        function generateSelector(element) {
            if (element.id) return '#' + element.id;
            var selector = element.tagName.toLowerCase();
            if (element.className) {
                var classes = element.className.split(/\\s+/).filter(c => c.length > 0);
                if (classes.length > 0) {
                    selector += '.' + classes.join('.');
                }
            }
            return selector;
        }
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, explore_js)
        print(f"JavaScript执行结果: {result[:500]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n=== 输入框分析 ===")
            print(f"占位符: {data['placeholder']}")
            print(f"当前值: {data['value']}")
            print(f"类名: {data['className']}")

            if data["dataset"]:
                print(f"数据属性: {json.dumps(data['dataset'], ensure_ascii=False)}")

            print(f"\n命令建议元素数量: {len(data['commandSuggestions'])}")
            if data["commandSuggestions"]:
                print("命令建议元素:")
                for cmd in data["commandSuggestions"][:10]:
                    print(f"  - {cmd['tagName']}: {cmd['text']}")
                    if cmd["placeholder"]:
                        print(f"    占位符: {cmd['placeholder']}")
                    if cmd["ariaLabel"]:
                        print(f"    aria-label: {cmd['ariaLabel']}")

            print(f"\n下拉菜单数量: {len(data['dropdowns'])}")
            for dd in data["dropdowns"]:
                print(f"  - [{dd['index']}] role={dd['role']}, visible={dd['isVisible']}")

            return data

    except Exception as e:
        print(f"❌ 探索失败: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_slash_commands():
    print("\n=== 测试斜杠命令 ===")

    doubao = DoubaoCLI()

    # 常见的斜杠命令
    slash_commands = [
        "/help",
        "/draw",
        "/image",
        "/生成图片",
        "/文生图",
        "/绘画",
        "/画图",
        "/ai draw",
        "/ai image",
    ]

    for cmd in slash_commands:
        print(f"\n测试命令: {cmd}")
        try:
            # 先清除输入框
            clear_js = """
            (function() {
                var textarea = document.querySelector('textarea');
                if (textarea) {
                    textarea.value = '';
                    return "已清除输入框";
                }
                return "未找到输入框";
            })()
            """
            doubao.execute_javascript(1, 1, clear_js)
            time.sleep(1)

            # 输入命令
            result = doubao.enhanced.send_message_to_ai(cmd, use_enhanced=True)
            print(f"发送结果: {result}")
            time.sleep(2)

            # 检查是否有响应或下拉菜单出现
            check_response_js = """
            (function() {
                // 检查是否有命令建议出现
                var suggestions = document.querySelectorAll('[role="option"], .command-suggestion, .suggestion-item');
                var suggestionTexts = Array.from(suggestions).map(s => ({
                    text: (s.textContent || s.innerText || '').trim(),
                    isVisible: s.offsetWidth > 0 && s.offsetHeight > 0
                })).filter(s => s.isVisible && s.text);

                // 检查是否有错误消息
                var errors = document.querySelectorAll('.error, .warning, [role="alert"]');
                var errorTexts = Array.from(errors).map(e => ({
                    text: (e.textContent || e.innerText || '').trim(),
                    isVisible: e.offsetWidth > 0 && e.offsetHeight > 0
                })).filter(e => e.isVisible && e.text);

                return JSON.stringify({
                    suggestions: suggestionTexts,
                    errors: errorTexts,
                    suggestionCount: suggestionTexts.length,
                    errorCount: errorTexts.length
                });
            })()
            """

            result2 = doubao.execute_javascript(1, 1, check_response_js)
            print(f"响应检查: {result2}")

        except Exception as e:
            print(f"❌ 命令测试失败: {e}")


def explore_ai_creation_features():
    print("\n=== 探索AI创作功能 ===")

    doubao = DoubaoCLI()

    # 点击AI创作按钮
    print("点击AI创作按钮...")
    try:
        click_result = doubao.enhanced.executor.click_button("AI 创作")
        if click_result.success:
            print(f"✅ 进入AI创作界面")
            time.sleep(3)

            # 探索AI创作界面特有的功能
            explore_features_js = """
            (function() {
                // 查找AI创作特有的功能
                var features = {
                    tools: [],
                    templates: [],
                    styles: [],
                    settings: []
                };

                // 查找工具按钮
                var toolButtons = document.querySelectorAll('[data-testid*="tool"], [aria-label*="工具"], .tool-button');
                toolButtons.forEach((btn, idx) => {
                    if (btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                        features.tools.push({
                            index: idx,
                            text: (btn.textContent || btn.innerText || '').trim(),
                            ariaLabel: btn.getAttribute('aria-label') || '',
                            className: btn.className.substring(0, 30),
                            isVisible: true
                        });
                    }
                });

                // 查找模板
                var templateElements = document.querySelectorAll('[data-testid*="template"], .template, .preset');
                templateElements.forEach((el, idx) => {
                    if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                        features.templates.push({
                            index: idx,
                            text: (el.textContent || el.innerText || '').trim().substring(0, 50),
                            className: el.className.substring(0, 30),
                            isVisible: true
                        });
                    }
                });

                // 查找样式选项
                var styleElements = document.querySelectorAll('[data-testid*="style"], .style-option, [aria-label*="风格"]');
                styleElements.forEach((el, idx) => {
                    if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                        features.styles.push({
                            index: idx,
                            text: (el.textContent || el.innerText || '').trim().substring(0, 50),
                            ariaLabel: el.getAttribute('aria-label') || '',
                            className: el.className.substring(0, 30),
                            isVisible: true
                        });
                    }
                });

                // 查找设置选项
                var settingElements = document.querySelectorAll('[data-testid*="setting"], .setting, [aria-label*="设置"]');
                settingElements.forEach((el, idx) => {
                    if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                        features.settings.push({
                            index: idx,
                            text: (el.textContent || el.innerText || '').trim().substring(0, 50),
                            ariaLabel: el.getAttribute('aria-label') || '',
                            className: el.className.substring(0, 30),
                            isVisible: true
                        });
                    }
                });

                return JSON.stringify(features, null, 2);
            })()
            """

            result = doubao.execute_javascript(1, 1, explore_features_js)
            print(f"功能探索结果: {result[:300]}...")

            if "JavaScript执行结果: " in result:
                json_str = result.split("JavaScript执行结果: ", 1)[1]
                features = json.loads(json_str)

                print(f"\nAI创作功能总结:")
                print(f"工具数量: {len(features['tools'])}")
                print(f"模板数量: {len(features['templates'])}")
                print(f"样式数量: {len(features['styles'])}")
                print(f"设置数量: {len(features['settings'])}")

                # 显示一些示例
                if features["tools"]:
                    print("\n可用工具:")
                    for tool in features["tools"][:5]:
                        print(f"  - {tool['text']} (aria-label: {tool['ariaLabel']})")

                if features["templates"]:
                    print("\n可用模板:")
                    for template in features["templates"][:3]:
                        print(f"  - {template['text']}")

        else:
            print(f"❌ 进入AI创作界面失败: {click_result.error_message}")

    except Exception as e:
        print(f"❌ 探索AI创作功能失败: {e}")


if __name__ == "__main__":
    print("豆包AI命令和技能探索")
    print("=" * 50)

    data = explore_commands_and_skills()
    if data:
        print("\n✅ 命令探索完成")

        # 根据探索结果决定下一步
        if data.get("commandSuggestions"):
            print("\n发现命令建议元素，尝试测试斜杠命令...")
            test_slash_commands()

        print("\n探索AI创作功能...")
        explore_ai_creation_features()
    else:
        print("\n❌ 命令探索失败")
        sys.exit(1)
