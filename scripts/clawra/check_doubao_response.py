#!/usr/bin/env python3
"""
检查豆包AI的响应和历史对话
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def check_ai_responses():
    print("=== 检查豆包AI响应 ===")

    doubao = DoubaoCLI()

    print("1. 检查当前对话历史...")

    # 获取对话历史
    check_history_js = """
    (function() {
        // 查找所有消息
        var messages = document.querySelectorAll('[data-message-id], .message, .chat-message, [role="article"]');
        var messageData = [];

        messages.forEach((msg, idx) => {
            if (msg.offsetWidth > 0 && msg.offsetHeight > 0) {
                var text = (msg.textContent || msg.innerText || '').trim();
                var role = msg.getAttribute('role') ||
                           msg.getAttribute('data-role') ||
                           (msg.classList.contains('user-message') ? 'user' :
                            msg.classList.contains('assistant-message') ? 'assistant' : 'unknown');

                // 查找消息中的图像
                var images = msg.querySelectorAll('img');
                var imageData = Array.from(images).map((img, imgIdx) => ({
                    index: imgIdx,
                    src: img.src.substring(0, 100),
                    alt: img.alt || '',
                    width: img.naturalWidth,
                    height: img.naturalHeight
                }));

                messageData.push({
                    index: idx,
                    role: role,
                    text: text.substring(0, 200),
                    hasImages: images.length > 0,
                    imageCount: images.length,
                    images: imageData,
                    timestamp: Date.now()
                });
            }
        });

        // 检查是否有错误或状态消息
        var statusMessages = document.querySelectorAll('.status, .loading, .error, .warning, [role="status"], [aria-live]');
        var statusData = Array.from(statusMessages).map((el, idx) => ({
            index: idx,
            text: (el.textContent || el.innerText || '').trim(),
            role: el.getAttribute('role') || '',
            ariaLive: el.getAttribute('aria-live') || '',
            className: el.className.substring(0, 30)
        }));

        return JSON.stringify({
            totalMessages: messages.length,
            messages: messageData,
            statusMessages: statusData,
            hasUserMessages: messageData.some(m => m.role === 'user' || m.text.includes('/')),
            hasAssistantMessages: messageData.some(m => m.role === 'assistant'),
            hasImages: messageData.some(m => m.hasImages)
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, check_history_js)
        print(f"JavaScript执行结果: {result[:300]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n=== 对话历史分析 ===")
            print(f"总消息数: {data['totalMessages']}")
            print(f"有用户消息: {data['hasUserMessages']}")
            print(f"有助手消息: {data['hasAssistantMessages']}")
            print(f"有图像: {data['hasImages']}")

            if data["messages"]:
                print(f"\n最近消息:")
                for msg in data["messages"][-5:]:  # 显示最后5条消息
                    print(f"  [{msg['index']}] {msg['role']}: {msg['text']}")
                    if msg["hasImages"]:
                        print(f"    包含 {msg['imageCount']} 张图像")

            if data["statusMessages"]:
                print(f"\n状态消息:")
                for status in data["statusMessages"]:
                    print(f"  - {status['text']}")

            return data
        else:
            print(f"原始输出: {result}")
            return None

    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_model_selection():
    print("\n=== 测试模型选择 ===")

    doubao = DoubaoCLI()

    # 检查是否有模型选择器
    check_model_js = """
    (function() {
        // 查找模型选择相关元素
        var modelSelectors = document.querySelectorAll('[data-testid*="model"], .model-selector, [aria-label*="模型"], select');
        var modelData = [];

        modelSelectors.forEach((el, idx) => {
            if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                var options = [];
                if (el.tagName === 'SELECT') {
                    options = Array.from(el.options).map(opt => ({
                        value: opt.value,
                        text: opt.text,
                        selected: opt.selected
                    }));
                }

                modelData.push({
                    index: idx,
                    tagName: el.tagName,
                    text: (el.textContent || el.innerText || '').trim(),
                    placeholder: el.placeholder || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    className: el.className.substring(0, 30),
                    isSelect: el.tagName === 'SELECT',
                    options: options,
                    value: el.value || ''
                });
            }
        });

        // 查找模型切换按钮
        var modelButtons = document.querySelectorAll('[data-testid*="model-switch"], .model-switch, button[aria-label*="模型"]');
        var buttonData = Array.from(modelButtons).map((btn, idx) => ({
            index: idx,
            text: (btn.textContent || btn.innerText || '').trim(),
            ariaLabel: btn.getAttribute('aria-label') || '',
            className: btn.className.substring(0, 30),
            isVisible: btn.offsetWidth > 0 && btn.offsetHeight > 0
        }));

        return JSON.stringify({
            modelSelectors: modelData,
            modelButtons: buttonData,
            hasModelSelector: modelData.length > 0,
            hasModelButton: buttonData.length > 0
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, check_model_js)
        print(f"模型选择检查: {result[:300]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n模型选择分析:")
            print(f"有模型选择器: {data['hasModelSelector']}")
            print(f"有模型按钮: {data['hasModelButton']}")

            if data["modelSelectors"]:
                print(f"\n模型选择器:")
                for selector in data["modelSelectors"]:
                    print(f"  - {selector['tagName']}: {selector['text']}")
                    if selector["options"]:
                        print(f"    选项: {[opt.text for opt in selector['options']]}")

            if data["modelButtons"]:
                print(f"\n模型按钮:")
                for btn in data["modelButtons"]:
                    print(f"  - {btn['text']} (aria-label: {btn['ariaLabel']})")

            return data
        else:
            print(f"原始输出: {result}")
            return None

    except Exception as e:
        print(f"❌ 模型选择检查失败: {e}")
        return None


def test_ai_painting_directly():
    print("\n=== 直接测试AI绘画 ===")

    doubao = DoubaoCLI()

    # 尝试直接发送绘画请求，不通过斜杠命令
    painting_request = "请生成一张卡通猫咪的图片，风格可爱，背景是花园"

    print(f"发送绘画请求: {painting_request}")

    try:
        result = doubao.enhanced.send_message_to_ai(painting_request, use_enhanced=True)
        print(f"发送结果: {result}")

        # 等待更长时间
        print("等待45秒让AI生成图像...")
        time.sleep(45)

        # 再次检查响应
        check_response_js = """
        (function() {
            // 查找最新助手消息
            var messages = document.querySelectorAll('[data-message-id], .message, .chat-message');
            var latestAssistantMsg = null;

            for (var i = messages.length - 1; i >= 0; i--) {
                var msg = messages[i];
                var text = (msg.textContent || msg.innerText || '').toLowerCase();
                if (text.includes('猫') || text.includes('生成') || text.includes('图片')) {
                    latestAssistantMsg = msg;
                    break;
                }
            }

            if (!latestAssistantMsg && messages.length > 0) {
                latestAssistantMsg = messages[messages.length - 1];
            }

            if (latestAssistantMsg) {
                var images = latestAssistantMsg.querySelectorAll('img');
                var imageData = Array.from(images).map((img, idx) => ({
                    index: idx,
                    src: img.src.substring(0, 100),
                    alt: img.alt || '',
                    width: img.naturalWidth,
                    height: img.naturalHeight,
                    complete: img.complete
                }));

                return JSON.stringify({
                    success: true,
                    text: (latestAssistantMsg.textContent || latestAssistantMsg.innerText || '').trim().substring(0, 200),
                    hasImages: images.length > 0,
                    imageCount: images.length,
                    images: imageData
                });
            }

            return JSON.stringify({
                success: false,
                message: "未找到相关消息"
            });
        })()
        """

        result2 = doubao.execute_javascript(1, 1, check_response_js)
        print(f"响应检查: {result2}")

        if "JavaScript执行结果: " in result2:
            json_str = result2.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            if data.get("success") and data.get("hasImages"):
                print(f"🎉 成功生成图像!")
                print(f"消息: {data['text']}")
                print(f"图像数量: {data['imageCount']}")

                for img in data["images"]:
                    print(f"  图像 {img['index']}: {img['width']}x{img['height']}")
                    print(f"    源: {img['src']}...")

                return True
            else:
                print(f"⚠️ 未生成图像")
                print(f"消息: {data.get('text', data.get('message', '无消息'))}")
                return False

    except Exception as e:
        print(f"❌ 绘画测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("豆包AI响应检查")
    print("=" * 50)

    # 检查历史响应
    history_data = check_ai_responses()

    if history_data:
        print("\n✅ 响应检查完成")

        # 如果没有图像，测试模型选择
        if not history_data["hasImages"]:
            print("\n未发现图像，检查模型选择...")
            model_data = test_model_selection()

            if model_data and (model_data["hasModelSelector"] or model_data["hasModelButton"]):
                print("\n发现模型选择功能，但需要进一步测试")
            else:
                print("\n未发现模型选择功能")

        # 直接测试AI绘画
        print("\n进行直接AI绘画测试...")
        test_ai_painting_directly()
    else:
        print("\n❌ 响应检查失败")
        sys.exit(1)
