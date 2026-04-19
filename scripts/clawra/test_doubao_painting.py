#!/usr/bin/env python3
"""
测试豆包AI绘画功能
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def test_ai_creation_button():
    print("=== 测试豆包AI创作按钮 ===")

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

    print("\n2. 查找并点击'AI 创作'按钮...")

    # 使用增强版查找并点击按钮
    try:
        # 首先使用文本查找按钮
        click_result = doubao.enhanced.executor.click_button("AI 创作")

        if click_result.success:
            print(f"✅ 点击成功: {click_result.output}")
            time.sleep(3)  # 等待新界面加载

            # 探索新出现的界面
            print("\n3. 探索AI创作界面...")

            explore_js = """
            (function() {
                // 查找所有可见的输入框和按钮
                var inputs = Array.from(document.querySelectorAll('textarea, input, [contenteditable="true"]'));
                var buttons = Array.from(document.querySelectorAll('button, [role="button"]'));

                var inputInfo = inputs.map((input, idx) => ({
                    index: idx,
                    tagName: input.tagName,
                    type: input.type || 'N/A',
                    placeholder: input.placeholder || '',
                    id: input.id || '',
                    className: input.className.substring(0, 50),
                    value: input.value || '',
                    isVisible: input.offsetWidth > 0 && input.offsetHeight > 0
                })).filter(info => info.isVisible);

                var buttonInfo = buttons.map((btn, idx) => ({
                    index: idx,
                    tagName: btn.tagName,
                    text: (btn.textContent || btn.value || btn.innerText || '').trim().substring(0, 50),
                    id: btn.id || '',
                    className: btn.className.substring(0, 50),
                    isVisible: btn.offsetWidth > 0 && btn.offsetHeight > 0
                })).filter(info => info.isVisible && info.text);

                // 查找绘画相关元素
                var paintingElements = Array.from(document.querySelectorAll('*')).filter(el => {
                    var text = (el.textContent || el.value || el.innerText || '').toLowerCase();
                    return text.includes('绘画') || text.includes('画图') || text.includes('image') ||
                           text.includes('生成图片') || text.includes('文生图') || text.includes('绘图');
                }).map(el => ({
                    tagName: el.tagName,
                    text: (el.textContent || el.value || el.innerText || '').trim().substring(0, 100),
                    id: el.id || '',
                    className: el.className.substring(0, 50)
                }));

                return JSON.stringify({
                    inputs: inputInfo,
                    buttons: buttonInfo,
                    paintingElements: paintingElements,
                    inputCount: inputInfo.length,
                    buttonCount: buttonInfo.length,
                    paintingCount: paintingElements.length
                });
            })()
            """

            result = doubao.execute_javascript(1, 1, explore_js)
            if "JavaScript执行结果: " in result:
                json_str = result.split("JavaScript执行结果: ", 1)[1]
                data = json.loads(json_str)

                print(f"界面分析结果:")
                print(f"输入框数量: {data['inputCount']}")
                print(f"按钮数量: {data['buttonCount']}")
                print(f"绘画相关元素: {data['paintingCount']}")

                if data["inputs"]:
                    print("\n输入框:")
                    for inp in data["inputs"]:
                        print(
                            f"  - {inp['tagName']}[type={inp['type']}]: placeholder='{inp['placeholder']}', value='{inp['value']}'"
                        )

                if data["buttons"]:
                    print("\n按钮:")
                    for btn in data["buttons"][:10]:  # 只显示前10个
                        print(f"  - {btn['tagName']}: '{btn['text']}'")

                if data["paintingElements"]:
                    print("\n绘画相关元素:")
                    for el in data["paintingElements"][:5]:
                        print(f"  - {el['tagName']}: '{el['text']}'")

            return True
        else:
            print(f"❌ 点击失败: {click_result.error_message}")

            # 尝试直接使用JavaScript点击
            print("\n尝试使用JavaScript直接点击...")
            click_js = """
            (function() {
                // 查找包含'AI 创作'文本的元素
                var elements = Array.from(document.querySelectorAll('*'));
                var target = elements.find(el => {
                    var text = el.textContent || el.innerText || '';
                    return text.includes('AI 创作') && el.offsetWidth > 0 && el.offsetHeight > 0;
                });

                if (target) {
                    target.click();
                    return "成功点击'AI 创作'元素";
                } else {
                    return "未找到'AI 创作'元素";
                }
            })()
            """

            js_result = doubao.execute_javascript(1, 1, click_js)
            print(f"JavaScript点击结果: {js_result}")

            if "成功" in js_result:
                time.sleep(3)
                return True
            else:
                return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_image_generation():
    print("\n=== 测试图像生成功能 ===")

    doubao = DoubaoCLI()

    # 尝试发送图像生成命令
    print("尝试发送图像生成命令...")

    # 可能需要在输入框中输入特定命令
    # 首先查找输入框
    try:
        element, find_result = doubao.enhanced.executor.find_input_element()
        if element:
            print(f"找到输入框: {element.selector}")

            # 输入图像生成命令
            image_prompt = "生成一张日式动漫风格的猫咪图片，可爱，大眼睛，背景是樱花树"
            fill_result = doubao.enhanced.executor.fill_input(image_prompt)

            if fill_result.success:
                print(f"✅ 输入成功: {fill_result.output}")

                # 尝试点击发送按钮
                click_result = doubao.enhanced.executor.click_button("发送")
                if click_result.success:
                    print(f"✅ 发送成功: {click_result.output}")

                    # 等待生成完成
                    print("等待15秒让图像生成...")
                    time.sleep(15)

                    # 检查是否有图像生成
                    check_js = """
                    (function() {
                        // 查找最新消息中的图像
                        var messages = document.querySelectorAll('.message, .chat-message, .bubble');
                        if (messages.length > 0) {
                            var lastMessage = messages[messages.length - 1];
                            var images = lastMessage.querySelectorAll('img');
                            return JSON.stringify({
                                success: true,
                                messageCount: messages.length,
                                hasImages: images.length > 0,
                                imageCount: images.length,
                                lastMessageText: lastMessage.textContent.trim().substring(0, 100)
                            });
                        }
                        return JSON.stringify({success: false, message: '未找到消息'});
                    })()
                    """

                    result = doubao.execute_javascript(1, 1, check_js)
                    print(f"图像检查结果: {result}")

                    return True
                else:
                    print(f"❌ 发送失败: {click_result.error_message}")
                    return False
            else:
                print(f"❌ 输入失败: {fill_result.error_message}")
                return False
        else:
            print(f"❌ 未找到输入框: {find_result.error_message}")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("豆包AI绘画功能测试")
    print("=" * 50)

    # 测试AI创作按钮
    if test_ai_creation_button():
        print("\n✅ AI创作按钮测试完成")

        # 测试图像生成
        print("\n开始测试图像生成功能...")
        test_image_generation()
    else:
        print("\n❌ AI创作按钮测试失败")
        sys.exit(1)
