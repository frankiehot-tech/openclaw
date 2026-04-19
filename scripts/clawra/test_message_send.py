#!/usr/bin/env python3
"""
测试消息发送和AI响应
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def test_message_send():
    """测试消息发送"""
    print("=== 消息发送测试 ===")

    doubao = DoubaoCLI()

    # 打开页面
    print("打开豆包页面...")
    result = doubao.open_doubao_ai()
    print(f"打开结果: {result}")
    time.sleep(3)

    # 发送简单消息
    test_message = "你好"
    print(f"\n发送消息: '{test_message}'")
    send_result = doubao.enhanced.send_message_to_ai(test_message, use_enhanced=True)
    print(f"发送结果: {send_result}")

    # 等待响应
    print("等待10秒...")
    time.sleep(10)

    # 检查是否有AI响应
    print("\n检查AI响应...")
    js_check = """
    (function() {
        // 查找所有文本元素
        var allElements = document.querySelectorAll('*');
        var messages = [];

        allElements.forEach(function(el, idx) {
            var text = (el.innerText || el.textContent || '').trim();
            if (text && text.length > 2 && text.length < 500) {
                // 检查是否是消息
                var isUser = text.includes('你好') || text === '你好';
                var isAI = !isUser && text.length > 5 && text.length < 1000;

                if (isUser || isAI) {
                    messages.push({
                        index: idx,
                        text: text.substring(0, 200),
                        isUser: isUser,
                        isAI: isAI,
                        tagName: el.tagName,
                        className: (el.className || '').substring(0, 30)
                    });
                }
            }
        });

        // 按位置排序（假设从上到下）
        messages.sort(function(a, b) {
            var rectA = allElements[a.index].getBoundingClientRect();
            var rectB = allElements[b.index].getBoundingClientRect();
            return rectA.top - rectB.top;
        });

        return JSON.stringify({
            total: messages.length,
            userMessages: messages.filter(m => m.isUser),
            aiMessages: messages.filter(m => m.isAI),
            allMessages: messages.slice(-10)  // 最近10条
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, js_check)
        print(f"JavaScript结果: {result}")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1].strip()
            if json_str != "missing value":
                data = json.loads(json_str)
                print(f"\n消息分析:")
                print(f"  总消息数: {data['total']}")
                print(f"  用户消息: {len(data['userMessages'])}")
                print(f"  AI消息: {len(data['aiMessages'])}")

                if data["aiMessages"]:
                    print("✅ AI已响应!")
                    for msg in data["aiMessages"]:
                        print(f"  AI回复: {msg['text'][:100]}...")
                    return True
                else:
                    print("⚠️ AI未响应")
                    if data["userMessages"]:
                        print(f"  用户消息: {data['userMessages'][0]['text'][:50]}")
                    print(f"  所有消息（最多10条）:")
                    for msg in data["allMessages"][:5]:
                        msg_type = "用户" if msg["isUser"] else "AI" if msg["isAI"] else "其他"
                        print(f"    [{msg_type}] {msg['text'][:50]}...")
                    return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def test_draw_command():
    """测试/draw命令"""
    print("\n\n=== /draw命令测试 ===")

    doubao = DoubaoCLI()

    # 打开页面
    print("打开豆包页面...")
    result = doubao.open_doubao_ai()
    print(f"打开结果: {result}")
    time.sleep(3)

    # 发送/draw命令
    draw_command = "/draw 一个红色的圆形"
    print(f"\n发送命令: '{draw_command}'")
    send_result = doubao.enhanced.send_message_to_ai(draw_command, use_enhanced=True)
    print(f"发送结果: {send_result}")

    # 等待更长时间
    print("等待30秒...")
    time.sleep(30)

    # 检查图像
    print("\n检查图像...")
    js_check = """
    (function() {
        var images = document.querySelectorAll('img');
        var imageData = [];

        images.forEach(function(img, idx) {
            if (img.complete && img.naturalWidth > 50) {
                imageData.push({
                    index: idx,
                    src: (img.src || '').substring(0, 100),
                    width: img.naturalWidth,
                    height: img.naturalHeight,
                    alt: img.alt || '',
                    // 排除已知的非生成图像
                    isNotGenerated: img.src.includes('avatar') || img.src.includes('logo') ||
                                    img.src.includes('icon') || img.src.includes('BIZ_BOT_ICON') ||
                                    img.alt.includes('头像') || img.alt.includes('logo')
                });
            }
        });

        return JSON.stringify({
            totalImages: images.length,
            loadedImages: imageData.length,
            generatedCandidates: imageData.filter(img => !img.isNotGenerated),
            allImages: imageData
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, js_check)
        print(f"JavaScript结果: {result}")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1].strip()
            if json_str != "missing value":
                data = json.loads(json_str)
                print(f"\n图像分析:")
                print(f"  总图像数: {data['totalImages']}")
                print(f"  已加载图像: {data['loadedImages']}")
                print(f"  可能生成的图像: {len(data['generatedCandidates'])}")

                if data["generatedCandidates"]:
                    print("🎉 发现可能生成的图像!")
                    for img in data["generatedCandidates"]:
                        print(f"  图像 {img['index']}: {img['width']}x{img['height']}")
                        print(f"    源: {img['src'][:80]}...")
                        print(f"    Alt: {img['alt']}")
                    return True
                else:
                    print("⚠️ 未发现可能生成的图像")
                    if data["allImages"]:
                        print(f"  所有图像:")
                        for img in data["allImages"][:3]:
                            print(
                                f"    图像 {img['index']}: {img['width']}x{img['height']}, 源: {img['src'][:60]}..."
                            )
                    return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def main():
    print("豆包消息发送测试")
    print("=" * 60)

    # 测试消息发送
    message_ok = test_message_send()

    # 如果消息发送成功，测试/draw命令
    if message_ok:
        print("\n消息发送成功，继续测试/draw命令...")
        draw_ok = test_draw_command()
    else:
        print("\n消息发送失败，跳过/draw命令测试")
        draw_ok = False

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"消息发送测试: {'✅ 成功' if message_ok else '❌ 失败'}")
    print(f"/draw命令测试: {'✅ 成功' if draw_ok else '❌ 失败'}")

    # 保存结果
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "message_test": message_ok,
        "draw_test": draw_ok,
        "overall": message_ok and draw_ok,
    }

    with open("message_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到: message_test_results.json")

    if message_ok and draw_ok:
        print("\n🎉 所有测试成功!")
        sys.exit(0)
    else:
        print("\n⚠️ 部分测试失败，需要进一步调查")
        sys.exit(1)


if __name__ == "__main__":
    main()
