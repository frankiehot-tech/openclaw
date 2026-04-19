#!/usr/bin/env python3
"""
探索豆包AI绘画功能
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def explore_painting_ui():
    print("=== 探索豆包AI绘画界面 ===")

    # 创建实例
    doubao = DoubaoCLI()

    print("1. 打开豆包AI页面...")
    try:
        result = doubao.open_doubao_ai()
        print(f"✅ {result}")
        time.sleep(3)  # 等待页面加载
    except Exception as e:
        print(f"❌ 打开AI页面失败: {e}")
        return False

    print("\n2. 探索页面结构...")

    # 查找所有按钮和可能的绘画功能入口
    explore_js = """
    (function() {
        // 查找所有按钮
        var buttons = Array.from(document.querySelectorAll('button, [role="button"], .btn, .button'));
        var buttonInfo = [];

        for (var i = 0; i < buttons.length; i++) {
            var btn = buttons[i];
            var text = btn.textContent || btn.value || btn.innerText || '';
            var id = btn.id || '';
            var className = btn.className || '';
            var isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;

            if (text.trim() && isVisible) {
                buttonInfo.push({
                    index: i,
                    text: text.trim(),
                    id: id,
                    className: className.substring(0, 50),
                    tagName: btn.tagName
                });
            }
        }

        // 查找绘画相关关键词
        var paintingKeywords = ['绘画', '画图', '生成图片', 'AI绘画', '文生图', 'image', 'draw', 'paint', 'generate'];
        var paintingButtons = buttonInfo.filter(btn =>
            paintingKeywords.some(keyword => btn.text.includes(keyword))
        );

        return JSON.stringify({
            totalButtons: buttons.length,
            visibleButtons: buttonInfo.length,
            buttonInfo: buttonInfo,
            paintingButtons: paintingButtons,
            paintingKeywordsFound: paintingButtons.length > 0
        });
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, explore_js)
        print(f"JavaScript执行结果: {result}")

        # 解析结果
        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n页面分析结果:")
            print(f"总按钮数: {data['totalButtons']}")
            print(f"可见按钮数: {data['visibleButtons']}")
            print(f"发现绘画相关按钮: {data['paintingKeywordsFound']}")

            if data["paintingButtons"]:
                print("\n绘画相关按钮:")
                for btn in data["paintingButtons"]:
                    print(
                        f"  - [{btn['index']}] {btn['text']} (id: {btn['id']}, class: {btn['className']})"
                    )
            else:
                print("\n未找到明显的绘画按钮，尝试搜索其他元素...")

                # 搜索输入框和生成相关元素
                search_js = """
                (function() {
                    // 搜索绘画相关文本
                    var elements = Array.from(document.querySelectorAll('*'));
                    var paintingElements = [];

                    var keywords = ['绘画', '画图', '生成图片', 'AI绘画', '文生图', 'image', 'draw', 'paint', 'generate', '图片', '图像'];

                    for (var i = 0; i < elements.length; i++) {
                        var el = elements[i];
                        var text = el.textContent || el.value || el.innerText || '';
                        var placeholder = el.placeholder || '';
                        var isVisible = el.offsetWidth > 0 && el.offsetHeight > 0;

                        if (isVisible && (text.trim() || placeholder.trim())) {
                            var combinedText = (text + ' ' + placeholder).toLowerCase();
                            if (keywords.some(keyword => combinedText.includes(keyword.toLowerCase()))) {
                                paintingElements.push({
                                    index: i,
                                    tagName: el.tagName,
                                    text: text.trim().substring(0, 50),
                                    placeholder: placeholder.substring(0, 50),
                                    id: el.id || '',
                                    className: el.className.substring(0, 50)
                                });
                            }
                        }
                    }

                    return JSON.stringify({
                        paintingElements: paintingElements,
                        count: paintingElements.length
                    });
                })()
                """

                result2 = doubao.execute_javascript(1, 1, search_js)
                if "JavaScript执行结果: " in result2:
                    json_str2 = result2.split("JavaScript执行结果: ", 1)[1]
                    data2 = json.loads(json_str2)

                    if data2["paintingElements"]:
                        print(f"\n找到 {data2['count']} 个绘画相关元素:")
                        for el in data2["paintingElements"][:10]:  # 只显示前10个
                            print(
                                f"  - {el['tagName']}: {el['text']} (placeholder: {el['placeholder']})"
                            )
                    else:
                        print("\n未找到绘画相关元素，可能需要手动探索。")
        else:
            print(f"原始输出: {result}")

        return True

    except Exception as e:
        print(f"❌ 探索失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_painting_workflow():
    print("\n=== 测试绘画工作流 ===")

    doubao = DoubaoCLI()

    # 尝试使用增强版发送绘画提示
    print("尝试发送绘画提示...")

    # 绘画提示示例
    painting_prompt = "/draw 一只可爱的猫咪在花园里玩耍，阳光明媚，细节丰富，动漫风格"

    try:
        result = doubao.enhanced.send_message_to_ai(painting_prompt, use_enhanced=True)
        print(f"发送结果: {result}")

        # 等待响应
        print("等待10秒查看是否有绘画响应...")
        time.sleep(10)

        # 检查最新消息
        check_js = """
        (function() {
            // 查找最新的消息
            var messages = document.querySelectorAll('.message, .chat-message, .bubble');
            if (messages.length > 0) {
                var lastMessage = messages[messages.length - 1];
                return JSON.stringify({
                    success: true,
                    messageCount: messages.length,
                    lastMessageText: lastMessage.textContent.trim().substring(0, 200),
                    hasImages: lastMessage.querySelectorAll('img').length > 0
                });
            }
            return JSON.stringify({
                success: false,
                message: '未找到消息'
            });
        })()
        """

        result2 = doubao.execute_javascript(1, 1, check_js)
        print(f"检查结果: {result2}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("豆包AI绘画功能探索")
    print("请确保豆包App已打开且JavaScript执行已启用")
    print("=" * 50)

    if explore_painting_ui():
        print("\n✅ 探索完成")

        # 询问是否测试绘画工作流
        response = input("\n是否测试绘画工作流？(y/n): ")
        if response.lower() == "y":
            test_painting_workflow()
    else:
        print("\n❌ 探索失败")
        sys.exit(1)
