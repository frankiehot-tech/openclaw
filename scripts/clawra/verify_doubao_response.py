#!/usr/bin/env python3
"""
验证豆包AI响应能力
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def check_ai_response():
    """检查AI是否响应消息"""
    print("=== 验证豆包AI响应能力 ===")

    doubao = DoubaoCLI()

    # 打开页面
    print("1. 打开豆包AI页面...")
    try:
        result = doubao.open_doubao_ai()
        print(f"✅ {result}")
        time.sleep(3)
    except Exception as e:
        print(f"❌ 打开页面失败: {e}")
        return False

    # 发送简单消息
    print("2. 发送简单测试消息...")
    test_message = "你好，请简单回复'收到'"
    result = doubao.enhanced.send_message_to_ai(test_message, use_enhanced=True)
    print(f"发送结果: {result}")

    # 等待响应
    print("3. 等待20秒查看响应...")
    time.sleep(20)

    # 检查响应
    print("4. 检查响应...")
    check_js = """
    (function() {
        // 查找所有消息元素
        var messages = document.querySelectorAll('[data-message-id], .message, .chat-message, [role="article"], .message-item');
        var messageData = [];

        messages.forEach((msg, idx) => {
            var text = (msg.textContent || msg.innerText || '').trim();
            if (text) {
                messageData.push({
                    index: idx,
                    text: text.substring(0, 200),
                    hasImages: msg.querySelectorAll('img').length > 0,
                    className: msg.className.substring(0, 50),
                    isFromUser: text.includes('你好') || text.includes('请简单回复') || text.includes('收到'),
                    isFromAssistant: !text.includes('你好') && !text.includes('请简单回复') && text.length > 5
                });
            }
        });

        // 查找最新消息
        var recentMessages = messageData.slice(-5); // 最近5条

        return JSON.stringify({
            totalMessages: messages.length,
            allMessages: messageData,
            recentMessages: recentMessages,
            hasUserMessage: messageData.some(m => m.isFromUser),
            hasAssistantMessage: messageData.some(m => m.isFromAssistant),
            assistantResponse: messageData.find(m => m.isFromAssistant)
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, check_js)
        print(f"JavaScript执行结果: {result[:500]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n响应分析:")
            print(f"总消息数: {data['totalMessages']}")
            print(f"有用户消息: {data['hasUserMessage']}")
            print(f"有助手消息: {data['hasAssistantMessage']}")

            if data["hasAssistantMessage"]:
                print(f"✅ AI已响应!")
                assistant = data["assistantResponse"]
                if assistant:
                    print(f"助手回复: {assistant['text']}")
                return True
            else:
                print(f"⚠️ AI未响应")
                print(f"最近消息:")
                for msg in data["recentMessages"]:
                    print(f"  [{msg['index']}] {msg['text'][:80]}...")
                return False

    except Exception as e:
        print(f"❌ 检查响应失败: {e}")
        return False


def check_image_generation_capability():
    """检查图像生成能力"""
    print("\n=== 检查图像生成能力 ===")

    doubao = DoubaoCLI()

    # 已经在AI界面
    print("1. 发送图像生成请求...")
    image_prompt = "/draw 一个红色的圆形，简单测试"
    result = doubao.enhanced.send_message_to_ai(image_prompt, use_enhanced=True)
    print(f"发送结果: {result}")

    # 等待更长时间
    print("2. 等待90秒让AI生成图像...")
    time.sleep(90)

    # 检查图像
    print("3. 检查生成的图像...")
    check_images_js = """
    (function() {
        // 查找所有图像
        var allImages = document.querySelectorAll('img');
        var imageData = [];

        allImages.forEach((img, idx) => {
            if (img.complete) {
                imageData.push({
                    index: idx,
                    src: (img.src || '').substring(0, 150),
                    alt: img.alt || '',
                    width: img.naturalWidth,
                    height: img.naturalHeight,
                    isVisible: img.offsetWidth > 0 && img.offsetHeight > 0,
                    parentText: (img.parentElement ? img.parentElement.textContent || '' : '').substring(0, 100)
                });
            }
        });

        // 查找可能的生成图像（大尺寸，非头像/logo）
        var possibleGenerated = imageData.filter(img => {
            if (img.width < 300 || img.height < 300) return false;
            if (!img.src) return false;
            if (img.src.includes('avatar') || img.src.includes('logo') ||
                img.src.includes('icon') || img.src.includes('samantha')) return false;
            return true;
        });

        return JSON.stringify({
            totalImages: allImages.length,
            allImages: imageData,
            possibleGenerated: possibleGenerated,
            hasPossibleGenerated: possibleGenerated.length > 0,
            possibleGeneratedCount: possibleGenerated.length
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, check_images_js)
        print(f"图像检查结果: {result[:500]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n图像生成分析:")
            print(f"总图像数: {data['totalImages']}")
            print(f"可能生成的图像: {data['possibleGeneratedCount']}")
            print(f"有生成图像: {data['hasPossibleGenerated']}")

            if data["hasPossibleGenerated"]:
                print(f"🎉 检测到可能生成的图像!")
                for img in data["possibleGenerated"]:
                    print(f"  图像: {img['width']}x{img['height']}, 源: {img['src']}...")
                return True
            else:
                print(f"⚠️ 未检测到生成的图像")
                print(f"所有图像:")
                for img in data["allImages"][:5]:
                    print(f"  [{img['index']}] {img['width']}x{img['height']}: {img['src']}...")
                return False

    except Exception as e:
        print(f"❌ 检查图像失败: {e}")
        return False


def main():
    print("豆包AI响应验证")
    print("=" * 50)

    # 检查基础响应
    response_ok = check_ai_response()

    if response_ok:
        print("\n✅ AI响应正常，继续检查图像生成...")
        image_ok = check_image_generation_capability()

        if image_ok:
            print("\n🎉 豆包AI图像生成功能验证成功!")
            return True
        else:
            print("\n⚠️ 豆包AI可能不支持图像生成或需要特定条件")
            return False
    else:
        print("\n❌ AI未响应，需要检查认证或服务状态")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
