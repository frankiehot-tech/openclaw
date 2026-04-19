#!/usr/bin/env python3
"""
测试豆包图像生成功能 v2
使用正确的发送按钮选择器
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def test_image_generation_with_correct_button():
    print("=== 测试豆包图像生成功能 (v2) ===")

    # 创建实例
    doubao = DoubaoCLI()

    print("1. 打开豆包AI页面并进入AI创作界面...")
    try:
        result = doubao.open_doubao_ai()
        print(f"✅ {result}")
        time.sleep(3)

        # 点击AI创作按钮
        click_result = doubao.enhanced.executor.click_button("AI 创作")
        if click_result.success:
            print(f"✅ 进入AI创作界面: {click_result.output}")
            time.sleep(3)
        else:
            print(f"❌ 进入AI创作界面失败: {click_result.error_message}")
            return False
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False

    print("\n2. 查找输入框并输入绘画提示...")
    try:
        # 查找输入框
        element, find_result = doubao.enhanced.executor.find_input_element()
        if element:
            print(f"找到输入框: {element.selector}")

            # 清除现有内容（如果有）
            clear_js = f"document.querySelector('{element.selector}').value = '';"
            doubao.execute_javascript(1, 1, clear_js)
            time.sleep(1)

            # 输入新的图像生成提示
            image_prompt = "/draw 一只可爱的卡通猫咪在花园里玩耍，阳光明媚，色彩鲜艳，动漫风格"
            print(f"输入提示: {image_prompt}")

            fill_result = doubao.enhanced.executor.fill_input(image_prompt)
            if fill_result.success:
                print(f"✅ 输入成功: {fill_result.output}")
                time.sleep(2)
            else:
                print(f"❌ 输入失败: {fill_result.error_message}")
                return False
        else:
            print(f"❌ 未找到输入框: {find_result.error_message}")
            return False
    except Exception as e:
        print(f"❌ 输入处理失败: {e}")
        return False

    print("\n3. 使用正确的发送按钮选择器发送消息...")
    try:
        # 方法1: 使用ID选择器点击发送按钮
        send_button_id = "#flow-end-msg-send"
        click_js = f"""
        (function() {{
            var btn = document.querySelector('{send_button_id}');
            if (btn) {{
                btn.click();
                return JSON.stringify({{success: true, message: "成功点击发送按钮(ID: {send_button_id})"}});
            }} else {{
                // 尝试其他可能的选择器
                var buttons = document.querySelectorAll('button');
                var sendButtons = Array.from(buttons).filter(b => {{
                    var text = (b.textContent || b.innerText || '').toLowerCase();
                    return text.includes('发送') || text.includes('send') ||
                           b.getAttribute('aria-label') && b.getAttribute('aria-label').toLowerCase().includes('send');
                }});

                if (sendButtons.length > 0) {{
                    sendButtons[0].click();
                    return JSON.stringify({{success: true, message: "成功点击文本包含'发送'的按钮"}});
                }} else {{
                    return JSON.stringify({{success: false, message: "未找到发送按钮"}});
                }}
            }}
        }})()
        """

        result = doubao.execute_javascript(1, 1, click_js)
        print(f"JavaScript执行结果: {result}")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            try:
                data = json.loads(json_str)
                if data.get("success"):
                    print(f"✅ {data['message']}")

                    # 等待图像生成
                    print("\n4. 等待图像生成（30秒）...")
                    time.sleep(30)

                    # 检查生成的图像
                    check_images_js = """
                    (function() {
                        // 查找所有图像，特别是新生成的
                        var allImages = document.querySelectorAll('img');
                        var generatedImages = [];
                        var messageImages = [];

                        // 查找消息区域中的图像
                        var messages = document.querySelectorAll('.message, .chat-message, .bubble, [data-message]');
                        messages.forEach(msg => {
                            var imgs = msg.querySelectorAll('img');
                            imgs.forEach(img => {
                                if (img.src && !img.src.includes('logo') && !img.src.includes('avatar')) {
                                    messageImages.push({
                                        src: img.src.substring(0, 100),
                                        alt: img.alt || '',
                                        width: img.naturalWidth,
                                        height: img.naturalHeight,
                                        parentText: msg.textContent.substring(0, 100)
                                    });
                                }
                            });
                        });

                        // 过滤掉logo和头像
                        allImages.forEach(img => {
                            if (img.src && img.naturalWidth > 100 && img.naturalHeight > 100) {
                                if (!img.src.includes('logo') && !img.src.includes('avatar') &&
                                    !img.src.includes('icon')) {
                                    generatedImages.push({
                                        src: img.src.substring(0, 100),
                                        alt: img.alt || '',
                                        width: img.naturalWidth,
                                        height: img.naturalHeight,
                                        complete: img.complete
                                    });
                                }
                            }
                        });

                        return JSON.stringify({
                            success: true,
                            totalImages: allImages.length,
                            generatedImages: generatedImages,
                            messageImages: messageImages,
                            generatedCount: generatedImages.length,
                            messageImageCount: messageImages.length
                        });
                    })()
                    """

                    result2 = doubao.execute_javascript(1, 1, check_images_js)
                    print(f"\n图像检查结果: {result2}")

                    if "JavaScript执行结果: " in result2:
                        json_str2 = result2.split("JavaScript执行结果: ", 1)[1]
                        data2 = json.loads(json_str2)

                        if (
                            data2.get("generatedCount", 0) > 0
                            or data2.get("messageImageCount", 0) > 0
                        ):
                            print(f"\n🎉 成功生成图像!")
                            print(f"生成图像数量: {data2.get('generatedCount', 0)}")
                            print(f"消息中图像数量: {data2.get('messageImageCount', 0)}")

                            # 显示图像信息
                            if data2.get("generatedImages"):
                                print("\n生成图像详情:")
                                for img in data2["generatedImages"][:3]:
                                    print(f"  - 尺寸: {img['width']}x{img['height']}")
                                    print(f"    源: {img['src']}...")
                                    print(f"    替代文本: {img['alt']}")

                            return True
                        else:
                            print(f"\n⚠️ 未检测到新生成的图像")
                            print(f"总图像数: {data2.get('totalImages', 0)}")
                            return False

                else:
                    print(f"❌ 发送失败: {data.get('message', '未知错误')}")
                    return False
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"原始响应: {json_str}")
                return False
        else:
            print(f"❌ JavaScript执行失败: {result}")
            return False

    except Exception as e:
        print(f"❌ 发送失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_alternative_sending_methods():
    print("\n=== 测试替代发送方法 ===")

    doubao = DoubaoCLI()

    # 方法1: 按Enter键发送
    print("\n方法1: 模拟Enter键发送...")
    try:
        enter_js = """
        (function() {
            var event = new KeyboardEvent('keydown', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            });

            var textarea = document.querySelector('textarea');
            if (textarea) {
                textarea.dispatchEvent(event);
                return JSON.stringify({success: true, message: "已发送Enter键事件到输入框"});
            } else {
                return JSON.stringify({success: false, message: "未找到输入框"});
            }
        })()
        """

        result = doubao.execute_javascript(1, 1, enter_js)
        print(f"Enter键发送结果: {result}")
        return True
    except Exception as e:
        print(f"❌ Enter键发送失败: {e}")
        return False


if __name__ == "__main__":
    print("豆包图像生成功能测试 v2")
    print("=" * 50)

    if test_image_generation_with_correct_button():
        print("\n✅ 图像生成测试完成")
        sys.exit(0)
    else:
        print("\n❌ 图像生成测试失败，尝试替代方法...")

        if test_alternative_sending_methods():
            print("\n✅ 替代发送方法测试完成")
            sys.exit(0)
        else:
            print("\n❌ 所有测试方法都失败")
            sys.exit(1)
