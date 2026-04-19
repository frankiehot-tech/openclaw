#!/usr/bin/env python3
"""
探索豆包DOM结构，找到正确的元素
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def explore_all_buttons(doubao):
    """探索所有按钮文本"""
    print("\n=== 探索所有按钮 ===")

    js_code = """
    (function() {
        var buttons = document.querySelectorAll('button, [role="button"], [onclick], .btn, button-like');
        var buttonData = [];

        buttons.forEach(function(btn, idx) {
            // 获取按钮文本
            var text = (btn.innerText || btn.textContent || btn.getAttribute('aria-label') || '').trim();

            // 获取可见性信息
            var style = window.getComputedStyle(btn);
            var isVisible = style.display !== 'none' && style.visibility !== 'hidden' && btn.offsetWidth > 0;

            // 获取类和属性
            var className = btn.className || '';
            var hasOnClick = !!btn.onclick || btn.hasAttribute('onclick');

            if (text || className || hasOnClick) {
                buttonData.push({
                    index: idx,
                    text: text.substring(0, 50),
                    className: className.substring(0, 50),
                    tagName: btn.tagName,
                    isVisible: isVisible,
                    disabled: btn.disabled,
                    hasOnClick: hasOnClick,
                    // 检查是否与AI/创作相关
                    isAICreation: text.includes('创作') || text.includes('生成') || text.includes('Create') || text.includes('AI'),
                    isImage: text.includes('图片') || text.includes('图像') || text.includes('Image'),
                    isVideo: text.includes('视频') || text.includes('Video')
                });
            }
        });

        // 排序：可见的、有文本的在前
        buttonData.sort(function(a, b) {
            if (a.isVisible !== b.isVisible) return b.isVisible - a.isVisible;
            if (a.text && !b.text) return -1;
            if (!a.text && b.text) return 1;
            return 0;
        });

        return JSON.stringify({
            totalButtons: buttons.length,
            allButtons: buttonData,
            visibleButtons: buttonData.filter(b => b.isVisible),
            aiButtons: buttonData.filter(b => b.isAICreation),
            imageButtons: buttonData.filter(b => b.isImage),
            videoButtons: buttonData.filter(b => b.isVideo)
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, js_code)
        print(f"按钮探索结果长度: {len(result)}")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]

            if json_str.strip() == "missing value":
                print("⚠️ 返回'missing value'，尝试备用方案...")
                return explore_all_buttons_fallback(doubao)

            data = json.loads(json_str)
            print(f"✅ 找到 {data['totalButtons']} 个按钮元素")
            print(f"   可见按钮: {len(data['visibleButtons'])}")
            print(f"   AI创作相关按钮: {len(data['aiButtons'])}")
            print(f"   图像相关按钮: {len(data['imageButtons'])}")
            print(f"   视频相关按钮: {len(data['videoButtons'])}")

            # 打印前10个可见按钮
            print(f"\n前10个可见按钮:")
            for i, btn in enumerate(data["visibleButtons"][:10]):
                print(
                    f"  {i+1}. '{btn['text']}' (类: {btn['className']}, 标签: {btn['tagName']}, 禁用: {btn['disabled']})"
                )

            # 打印AI创作相关按钮
            if data["aiButtons"]:
                print(f"\nAI创作相关按钮:")
                for i, btn in enumerate(data["aiButtons"]):
                    print(
                        f"  {i+1}. '{btn['text']}' (可见: {btn['isVisible']}, 类: {btn['className']})"
                    )

            return data

    except Exception as e:
        print(f"❌ 按钮探索失败: {e}")
        return None


def explore_all_buttons_fallback(doubao):
    """备用方案：更简单的按钮探索"""
    print("\n尝试备用按钮探索...")

    js_code = """
    (function() {
        // 简单方法：查找所有可点击元素
        var clickables = document.querySelectorAll('button, a, [role="button"], [onclick]');
        var results = [];

        for (var i = 0; i < clickables.length; i++) {
            var el = clickables[i];
            var text = (el.innerText || el.textContent || '').trim().substring(0, 30);
            if (text) {
                results.push({
                    index: i,
                    text: text,
                    tagName: el.tagName,
                    className: (el.className || '').substring(0, 30)
                });
            }
        }

        return JSON.stringify({
            total: clickables.length,
            withText: results.length,
            elements: results.slice(0, 20)
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, js_code)
        print(f"备用探索结果: {result[:300]}...")
        return result
    except Exception as e:
        print(f"❌ 备用探索失败: {e}")
        return None


def explore_input_elements(doubao):
    """探索所有输入元素"""
    print("\n=== 探索输入元素 ===")

    js_code = """
    (function() {
        var inputs = document.querySelectorAll('input, textarea, [contenteditable="true"], [role="textbox"]');
        var inputData = [];

        inputs.forEach(function(input, idx) {
            var type = input.type || 'unknown';
            var placeholder = input.placeholder || '';
            var value = input.value || '';
            var tagName = input.tagName;

            // 检查可见性
            var style = window.getComputedStyle(input);
            var isVisible = style.display !== 'none' && style.visibility !== 'hidden' && input.offsetWidth > 0;

            inputData.push({
                index: idx,
                tagName: tagName,
                type: type,
                placeholder: placeholder.substring(0, 50),
                value: value.substring(0, 50),
                isVisible: isVisible,
                className: (input.className || '').substring(0, 30),
                id: input.id || '',
                name: input.name || '',
                // 检查是否为聊天输入
                isChatInput: placeholder.includes('输入') || placeholder.includes('说点什么') ||
                           placeholder.includes('聊天') || placeholder.includes('message') ||
                           className.includes('chat') || className.includes('input')
            });
        });

        // 排序：可见的在前
        inputData.sort(function(a, b) {
            if (a.isVisible !== b.isVisible) return b.isVisible - a.isVisible;
            if (a.isChatInput !== b.isChatInput) return b.isChatInput - a.isChatInput;
            return 0;
        });

        return JSON.stringify({
            totalInputs: inputs.length,
            allInputs: inputData,
            visibleInputs: inputData.filter(i => i.isVisible),
            chatInputs: inputData.filter(i => i.isChatInput)
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, js_code)
        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"✅ 找到 {data['totalInputs']} 个输入元素")
            print(f"   可见输入: {len(data['visibleInputs'])}")
            print(f"   聊天输入: {len(data['chatInputs'])}")

            if data["visibleInputs"]:
                print(f"\n可见输入元素:")
                for i, inp in enumerate(data["visibleInputs"][:5]):
                    print(f"  {i+1}. {inp['tagName']} 类型: {inp['type']}")
                    print(f"     占位符: '{inp['placeholder']}'")
                    print(f"     值: '{inp['value']}'")
                    print(f"     类: {inp['className']}")
                    print(f"     是否为聊天输入: {inp['isChatInput']}")

            return data

    except Exception as e:
        print(f"❌ 输入元素探索失败: {e}")
        return None


def explore_message_elements(doubao):
    """探索消息元素"""
    print("\n=== 探索消息元素 ===")

    js_code = """
    (function() {
        // 尝试多种选择器查找消息
        var selectors = [
            '[data-message-id]',
            '.message',
            '.chat-message',
            '[role="article"]',
            '.message-item',
            '.bubble',
            '.chat-bubble',
            '[class*="message"]',
            '[class*="chat"]'
        ];

        var allMessages = [];
        var seenTexts = new Set();

        selectors.forEach(function(selector) {
            var elements = document.querySelectorAll(selector);
            elements.forEach(function(el) {
                var text = (el.innerText || el.textContent || '').trim();
                if (text && text.length > 2 && !seenTexts.has(text)) {
                    seenTexts.add(text);

                    // 检查消息类型
                    var isUser = text.includes('你好') || text.includes('Hello') ||
                                el.classList.contains('user') || el.getAttribute('data-sender') === 'user';
                    var isAI = !isUser && (text.length > 10 || el.classList.contains('assistant') ||
                                el.getAttribute('data-sender') === 'assistant');

                    allMessages.push({
                        selector: selector,
                        text: text.substring(0, 200),
                        length: text.length,
                        isUser: isUser,
                        isAI: isAI,
                        className: (el.className || '').substring(0, 50),
                        hasImages: el.querySelectorAll('img').length > 0
                    });
                }
            });
        });

        // 如果没有找到，尝试更通用的方法
        if (allMessages.length === 0) {
            console.log("使用通用消息查找...");
            var allElements = document.querySelectorAll('div, p, span, article');
            for (var i = 0; i < allElements.length; i++) {
                var el = allElements[i];
                var text = (el.innerText || el.textContent || '').trim();
                if (text && text.length > 10 && text.length < 1000) {
                    // 检查是否是对话消息（包含常见对话模式）
                    var isConversation = text.includes('：') || text.includes(':') ||
                                       text.includes('?') || text.includes('？') ||
                                       text.includes('!') || text.includes('！');

                    if (isConversation && !seenTexts.has(text)) {
                        seenTexts.add(text);
                        allMessages.push({
                            selector: el.tagName + (el.className ? '.' + el.className.split(' ')[0] : ''),
                            text: text.substring(0, 200),
                            length: text.length,
                            isUser: text.includes('你好') || text.includes('Hello'),
                            isAI: !text.includes('你好') && !text.includes('Hello'),
                            className: (el.className || '').substring(0, 50),
                            hasImages: el.querySelectorAll('img').length > 0
                        });
                    }
                }
            }
        }

        // 按文本长度排序（长的可能是AI回复）
        allMessages.sort(function(a, b) {
            return b.length - a.length;
        });

        return JSON.stringify({
            totalMessages: allMessages.length,
            messages: allMessages.slice(0, 10),  // 前10个
            userMessages: allMessages.filter(m => m.isUser),
            aiMessages: allMessages.filter(m => m.isAI),
            hasUserMessages: allMessages.some(m => m.isUser),
            hasAiMessages: allMessages.some(m => m.isAI)
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, js_code)
        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"✅ 找到 {data['totalMessages']} 个可能的消息元素")
            print(f"   用户消息: {len(data['userMessages'])}")
            print(f"   AI消息: {len(data['aiMessages'])}")
            print(f"   有用户消息: {data['hasUserMessages']}")
            print(f"   有AI消息: {data['hasAiMessages']}")

            if data["messages"]:
                print(f"\n前{len(data['messages'])}个消息:")
                for i, msg in enumerate(data["messages"]):
                    msg_type = "用户" if msg.isUser else "AI" if msg.isAI else "未知"
                    print(f"  {i+1}. [{msg_type}] {msg['text'][:80]}...")
                    print(f"     选择器: {msg['selector']}, 类: {msg['className']}")

            return data

    except Exception as e:
        print(f"❌ 消息元素探索失败: {e}")
        return None


def explore_ai_creation_section(doubao):
    """探索AI创作区域"""
    print("\n=== 探索AI创作区域 ===")

    js_code = """
    (function() {
        // 查找所有可能包含"创作"、"生成"等关键词的区域
        var keywords = ['创作', '生成', 'Create', 'Generate', 'AI', '图片', '图像', '视频', '绘画'];
        var foundSections = [];

        // 方法1：按文本内容查找
        keywords.forEach(function(keyword) {
            var elements = document.querySelectorAll('*');
            elements.forEach(function(el) {
                var text = (el.innerText || el.textContent || '').trim();
                if (text.includes(keyword)) {
                    // 获取父级容器
                    var parent = el;
                    for (var i = 0; i < 3; i++) {
                        if (parent.parentElement) parent = parent.parentElement;
                    }

                    var sectionText = (parent.innerText || parent.textContent || '').trim().substring(0, 300);
                    if (sectionText && !foundSections.some(s => s.text === sectionText)) {
                        foundSections.push({
                            keyword: keyword,
                            text: sectionText,
                            elementText: text.substring(0, 100),
                            className: (parent.className || '').substring(0, 50),
                            tagName: parent.tagName,
                            childrenCount: parent.children.length
                        });
                    }
                }
            });
        });

        // 方法2：按类名查找
        var aiClasses = document.querySelectorAll('[class*="create"], [class*="generate"], [class*="ai"], [class*="image"], [class*="video"]');
        aiClasses.forEach(function(el) {
            var text = (el.innerText || el.textContent || '').trim().substring(0, 200);
            if (text) {
                foundSections.push({
                    keyword: 'class_match',
                    text: text,
                    elementText: '类名匹配',
                    className: (el.className || '').substring(0, 50),
                    tagName: el.tagName,
                    childrenCount: el.children.length
                });
            }
        });

        return JSON.stringify({
            totalSections: foundSections.length,
            sections: foundSections.slice(0, 10)
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, js_code)
        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"✅ 找到 {data['totalSections']} 个可能的相关区域")

            if data["sections"]:
                print(f"\n相关区域:")
                for i, section in enumerate(data["sections"]):
                    print(f"  {i+1}. 关键词: {section['keyword']}")
                    print(f"     文本: {section['text'][:80]}...")
                    print(f"     元素文本: {section['elementText']}")
                    print(f"     类名: {section['className']}")
                    print(f"     标签: {section['tagName']}, 子元素数: {section['childrenCount']}")

            return data

    except Exception as e:
        print(f"❌ AI创作区域探索失败: {e}")
        return None


def main():
    print("豆包DOM结构探索工具")
    print("=" * 60)

    doubao = DoubaoCLI()

    # 打开页面
    print("打开豆包页面...")
    doubao.open_doubao_ai()
    time.sleep(3)

    # 探索各个部分
    button_data = explore_all_buttons(doubao)
    input_data = explore_input_elements(doubao)
    message_data = explore_message_elements(doubao)
    creation_data = explore_ai_creation_section(doubao)

    print("\n" + "=" * 60)
    print("探索结果摘要")
    print("=" * 60)

    summary = {
        "buttons_found": button_data.get("totalButtons", 0) if button_data else 0,
        "visible_buttons": len(button_data.get("visibleButtons", [])) if button_data else 0,
        "ai_buttons": len(button_data.get("aiButtons", [])) if button_data else 0,
        "inputs_found": input_data.get("totalInputs", 0) if input_data else 0,
        "chat_inputs": len(input_data.get("chatInputs", [])) if input_data else 0,
        "messages_found": message_data.get("totalMessages", 0) if message_data else 0,
        "ai_messages": len(message_data.get("aiMessages", [])) if message_data else 0,
        "creation_sections": creation_data.get("totalSections", 0) if creation_data else 0,
    }

    print(
        f"按钮总数: {summary['buttons_found']} (可见: {summary['visible_buttons']}, AI相关: {summary['ai_buttons']})"
    )
    print(f"输入元素: {summary['inputs_found']} (聊天输入: {summary['chat_inputs']})")
    print(f"消息元素: {summary['messages_found']} (AI消息: {summary['ai_messages']})")
    print(f"创作区域: {summary['creation_sections']}")

    print("\n📝 发现和建议:")

    if summary["ai_buttons"] > 0:
        print("✅ 发现AI创作相关按钮")
        print(f"   按钮文本: {[btn['text'] for btn in button_data.get('aiButtons', [])[:3]]}")
    else:
        print("⚠️ 未发现明显的AI创作按钮")
        print("   可能原因: 按钮文本不同、需要先点击其他菜单、界面布局已更新")

    if summary["chat_inputs"] > 0:
        print("✅ 发现聊天输入框")
    else:
        print("⚠️ 未发现明确的聊天输入框")

    if summary["ai_messages"] > 0:
        print("✅ 发现AI消息，对话功能正常")
    else:
        print("⚠️ 未发现AI消息，可能AI未正确响应")

    # 保存结果
    result_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "button_details": button_data,
        "input_details": input_data,
        "message_details": message_data,
        "creation_details": creation_data,
    }

    result_file = "dom_exploration_results.json"
    try:
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print(f"\n详细结果已保存到: {result_file}")
    except Exception as e:
        print(f"❌ 保存结果失败: {e}")

    print("\n🎯 下一步行动建议:")
    if summary["ai_buttons"] > 0:
        print("1. 使用发现的AI按钮文本更新click_button调用")
        print("2. 测试点击这些按钮进入创作界面")
    else:
        print("1. 手动查看豆包界面，找到创作功能的位置")
        print("2. 更新按钮文本匹配逻辑")

    if summary["ai_messages"] == 0:
        print("3. 改进消息检测逻辑，等待更长时间让AI响应")
        print("4. 检查AI响应是否被渲染到不同位置")

    print("\n✅ DOM探索完成")


if __name__ == "__main__":
    main()
