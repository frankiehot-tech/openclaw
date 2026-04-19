#!/usr/bin/env python3
"""
通过聊天激活AI绘画功能
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def click_return_home():
    """点击返回首页按钮"""
    print("🔧 点击返回首页按钮...")

    cli = DoubaoCLIEnhanced()

    # 查找并点击"返回首页"按钮
    click_js = """
    // 查找返回首页按钮
    var buttons = document.querySelectorAll('button');
    var homeButton = null;
    for (var i = 0; i < buttons.length; i++) {
        var text = buttons[i].textContent || buttons[i].innerText || '';
        if (text.trim() === '返回首页') {
            homeButton = buttons[i];
            break;
        }
    }

    if (homeButton) {
        console.log('找到返回首页按钮，点击');
        homeButton.click();
        "点击返回首页按钮成功";
    } else {
        "未找到返回首页按钮";
    }
    """

    result = cli.execute_javascript_enhanced(click_js)
    print(f"点击结果: success={result.success}, output={repr(result.output)}")

    # 等待页面加载
    time.sleep(2)

    # 检查当前页面
    check_js = """
    var pageInfo = {
        title: document.title,
        url: window.location.href,
        path: window.location.pathname
    };
    JSON.stringify(pageInfo);
    """

    check_result = cli.execute_javascript_enhanced(check_js)
    if check_result.success and check_result.output and check_result.output != "missing value":
        try:
            page_info = json.loads(cli._clean_js_output(check_result.output))
            print(f"当前页面: 标题='{page_info.get('title')}', 路径='{page_info.get('path')}'")
            return True
        except Exception as e:
            print(f"解析页面信息失败: {e}")
            return False
    else:
        print(f"检查页面失败")
        return False


def check_chat_interface():
    """检查聊天界面"""
    print("\n🔧 检查聊天界面...")

    cli = DoubaoCLIEnhanced()

    # 检查聊天界面元素
    chat_check_js = """
    // 检查聊天界面
    var chatInfo = {
        // 聊天输入框
        hasChatInput: false,
        chatInputs: [],

        // 发送按钮
        hasSendButton: false,
        sendButtons: [],

        // 消息区域
        hasMessageArea: false,
        messageAreas: [],

        // 所有可能的聊天相关元素
        allElements: []
    };

    // 查找聊天输入框
    var chatInputs = document.querySelectorAll('[contenteditable="true"], textarea, input[type="text"]');
    for (var i = 0; i < chatInputs.length; i++) {
        var input = chatInputs[i];
        var info = {
            type: 'chatInput',
            tagName: input.tagName,
            placeholder: input.placeholder || '',
            className: input.className || '',
            id: input.id || '',
            visible: input.offsetParent !== null
        };
        chatInfo.chatInputs.push(info);
        chatInfo.allElements.push(info);
    }
    chatInfo.hasChatInput = chatInputs.length > 0;

    // 查找发送按钮
    var buttons = document.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        var text = btn.textContent || btn.innerText || '';
        if (text.includes('发送') || text.includes('Send') ||
            text.includes('enter') || text.includes('Enter') ||
            btn.getAttribute('aria-label') && (btn.getAttribute('aria-label').includes('发送') || btn.getAttribute('aria-label').includes('Send'))) {
            var info = {
                type: 'sendButton',
                tagName: btn.tagName,
                text: text,
                className: btn.className || '',
                id: btn.id || '',
                ariaLabel: btn.getAttribute('aria-label') || '',
                visible: btn.offsetParent !== null
            };
            chatInfo.sendButtons.push(info);
            chatInfo.allElements.push(info);
        }
    }
    chatInfo.hasSendButton = chatInfo.sendButtons.length > 0;

    // 查找消息区域
    var messageAreas = document.querySelectorAll('[class*="message"], [class*="Message"], [class*="chat"], [class*="Chat"], [role="log"]');
    for (var i = 0; i < messageAreas.length; i++) {
        var area = messageAreas[i];
        var info = {
            type: 'messageArea',
            tagName: area.tagName,
            className: area.className || '',
            id: area.id || '',
            visible: area.offsetParent !== null
        };
        chatInfo.messageAreas.push(info);
        chatInfo.allElements.push(info);
    }
    chatInfo.hasMessageArea = chatInfo.messageAreas.length > 0;

    JSON.stringify(chatInfo);
    """

    result = cli.execute_javascript_enhanced(chat_check_js)
    print(f"聊天检查结果: success={result.success}, output={repr(result.output)}")

    if result.success and result.output and result.output != "missing value":
        try:
            chat_info = json.loads(cli._clean_js_output(result.output))
            print(
                f"聊天输入框: {chat_info.get('hasChatInput')} ({len(chat_info.get('chatInputs', []))}个)"
            )
            print(
                f"发送按钮: {chat_info.get('hasSendButton')} ({len(chat_info.get('sendButtons', []))}个)"
            )
            print(
                f"消息区域: {chat_info.get('hasMessageArea')} ({len(chat_info.get('messageAreas', []))}个)"
            )

            # 显示聊天输入框详情
            for i, inp in enumerate(chat_info.get("chatInputs", [])):
                print(f"\n   聊天输入框 {i+1}:")
                print(f"      标签: {inp.get('tagName')}")
                print(f"      占位符: '{inp.get('placeholder')}'")
                print(f"      类名: {inp.get('className')[:50]}...")
                print(f"      是否可见: {inp.get('visible')}")

            # 显示发送按钮详情
            for i, btn in enumerate(chat_info.get("sendButtons", [])):
                print(f"\n   发送按钮 {i+1}:")
                print(f"      文本: '{btn.get('text')}'")
                print(f"      标签: {btn.get('tagName')}")
                print(f"      aria-label: '{btn.get('ariaLabel')}'")
                print(f"      是否可见: {btn.get('visible')}")

            return chat_info
        except Exception as e:
            print(f"解析聊天信息失败: {e}")
            return None
    else:
        print(f"获取聊天信息失败")
        return None


def try_send_message():
    """尝试发送消息"""
    print("\n🔧 尝试发送消息'AI绘画'...")

    cli = DoubaoCLIEnhanced()

    # 首先查找聊天输入框
    find_input_js = """
    // 查找聊天输入框
    var inputs = document.querySelectorAll('[contenteditable="true"], textarea, input[type="text"]');
    if (inputs.length > 0) {
        var targetInput = null;
        for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent !== null) {
                targetInput = inputs[i];
                break;
            }
        }

        if (targetInput) {
            console.log('找到可见的聊天输入框');

            // 尝试输入文本
            if (targetInput.tagName === 'TEXTAREA' || targetInput.tagName === 'INPUT') {
                targetInput.value = 'AI绘画';
                targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                targetInput.dispatchEvent(new Event('change', { bubbles: true }));
            } else if (targetInput.hasAttribute('contenteditable')) {
                targetInput.textContent = 'AI绘画';
                targetInput.dispatchEvent(new Event('input', { bubbles: true }));
            }

            "已输入'AI绘画'到聊天框";
        } else {
            "未找到可见的聊天输入框";
        }
    } else {
        "未找到聊天输入框";
    }
    """

    result = cli.execute_javascript_enhanced(find_input_js)
    print(f"输入消息结果: success={result.success}, output={repr(result.output)}")

    # 等待一下
    time.sleep(1)

    # 尝试发送消息
    send_js = """
    // 尝试发送消息
    var sent = false;

    // 方法1: 查找发送按钮
    var buttons = document.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        var text = btn.textContent || btn.innerText || '';
        if (text.includes('发送') || text.includes('Send') ||
            btn.getAttribute('aria-label') && (btn.getAttribute('aria-label').includes('发送') || btn.getAttribute('aria-label').includes('Send'))) {
            if (btn.offsetParent !== null) {
                console.log('找到发送按钮，点击');
                btn.click();
                sent = true;
                break;
            }
        }
    }

    // 方法2: 尝试回车键
    if (!sent) {
        var inputs = document.querySelectorAll('[contenteditable="true"], textarea, input[type="text"]');
        for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent !== null) {
                console.log('尝试在输入框上触发回车键');
                var event = new KeyboardEvent('keydown', {
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13,
                    bubbles: true
                });
                inputs[i].dispatchEvent(event);
                sent = true;
                break;
            }
        }
    }

    sent ? "已尝试发送消息" : "未能发送消息";
    """

    send_result = cli.execute_javascript_enhanced(send_js)
    print(f"发送消息结果: success={send_result.success}, output={repr(send_result.output)}")

    # 等待响应
    time.sleep(3)

    return send_result.success


def main():
    """主函数"""
    print("🎯 通过聊天激活AI绘画功能测试")
    print("=" * 60)

    try:
        # 1. 首先返回首页
        print("\n📋 步骤1: 返回首页")
        if not click_return_home():
            print("❌ 无法返回首页")
            return 1

        # 2. 检查聊天界面
        print("\n📋 步骤2: 检查聊天界面")
        chat_info = check_chat_interface()

        if not chat_info:
            print("❌ 无法检查聊天界面")
            return 1

        # 3. 如果聊天界面存在，尝试发送消息
        if chat_info.get("hasChatInput"):
            print("\n📋 步骤3: 尝试发送'AI绘画'消息")
            send_success = try_send_message()

            if send_success:
                print("\n✅ 已发送'AI绘画'消息")
                print("\n💡 等待AI响应，可能需要等待几秒钟...")

                # 等待更长时间
                time.sleep(5)

                # 检查页面是否有变化
                print("\n📋 步骤4: 检查页面变化")
                final_check_js = """
                var pageCheck = {
                    title: document.title,
                    path: window.location.pathname,
                    buttons: document.querySelectorAll('button').length,
                    hasAIPaintingElements: (function() {
                        var text = document.body.innerText || '';
                        return text.includes('AI绘画') || text.includes('绘画') || text.includes('画图');
                    })()
                };
                JSON.stringify(pageCheck);
                """

                cli = DoubaoCLIEnhanced()
                final_result = cli.execute_javascript_enhanced(final_check_js)
                if (
                    final_result.success
                    and final_result.output
                    and final_result.output != "missing value"
                ):
                    try:
                        page_check = json.loads(cli._clean_js_output(final_result.output))
                        print(f"当前页面:")
                        print(f"   标题: {page_check.get('title')}")
                        print(f"   路径: {page_check.get('path')}")
                        print(f"   按钮数量: {page_check.get('buttons')}")
                        print(f"   有AI绘画元素: {page_check.get('hasAIPaintingElements')}")
                    except Exception as e:
                        print(f"解析最终页面检查失败: {e}")
            else:
                print("❌ 未能发送消息")
        else:
            print("\n❌ 未找到聊天输入框")
            print("\n🔧 可能需要手动在豆包中打开聊天界面")

        print("\n" + "=" * 60)
        print("📊 测试完成")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
