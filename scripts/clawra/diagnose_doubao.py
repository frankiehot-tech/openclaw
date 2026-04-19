#!/usr/bin/env python3
"""
诊断豆包AI应用状态
"""

import json
import os
import subprocess
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def check_doubao_app():
    print("=== 诊断豆包AI应用状态 ===")

    print("1. 检查豆包应用是否运行...")
    try:
        # 使用AppleScript检查应用是否运行
        check_app_js = """
        tell application "System Events"
            set appList to name of every process whose background only is false
            if "豆包" is in appList then
                return "豆包应用正在运行"
            else
                return "豆包应用未运行"
            end if
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", check_app_js], capture_output=True, text=True, timeout=10
        )
        print(f"应用状态: {result.stdout.strip()}")

        if "正在运行" in result.stdout:
            print("✅ 豆包应用正在运行")
            return True
        else:
            print("❌ 豆包应用未运行，需要启动")
            return False

    except Exception as e:
        print(f"❌ 检查应用状态失败: {e}")
        return False


def check_doubao_auth():
    print("\n2. 检查豆包认证状态...")

    doubao = DoubaoCLI()

    try:
        # 打开豆包页面
        result = doubao.open_doubao_ai()
        print(f"打开页面结果: {result}")
        time.sleep(3)

        # 检查页面加载状态
        check_page_js = """
        (function() {
            var state = {
                title: document.title,
                url: window.location.href,
                readyState: document.readyState,
                bodyExists: !!document.body,
                hasContent: document.body && document.body.children.length > 0,
                hasLoginElements: false,
                hasChatInterface: false
            };

            // 检查登录相关元素
            var loginElements = document.querySelectorAll('[data-testid*="login"], .login-button, [href*="login"], button:contains("登录"), button:contains("Log in")');
            state.hasLoginElements = loginElements.length > 0;

            // 检查聊天界面元素
            var chatElements = document.querySelectorAll('textarea, [data-testid*="chat"], .chat-input, .message-list');
            state.hasChatInterface = chatElements.length > 0;

            // 检查错误消息
            var errors = document.querySelectorAll('.error, .alert, [role="alert"]');
            state.errorMessages = Array.from(errors).map(e => ({
                text: (e.textContent || e.innerText || '').trim(),
                className: e.className.substring(0, 30)
            }));

            return JSON.stringify(state, null, 2);
        })()
        """

        result = doubao.execute_javascript(1, 1, check_page_js)
        print(f"页面状态检查: {result[:400]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]

            # 处理"missing value"情况
            if json_str.strip() == "missing value":
                print("⚠️ JavaScript返回'缺失值'，页面可能未完全加载或DOM元素不存在")
                print("建议：等待页面加载完成，或检查登录状态")
                return False

            try:
                state = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"原始响应: {json_str[:200]}")
                return False

            print(f"\n页面状态分析:")
            print(f"标题: {state['title']}")
            print(f"URL: {state['url']}")
            print(f"准备状态: {state['readyState']}")
            print(f"有body元素: {state['bodyExists']}")
            print(f"有内容: {state['hasContent']}")
            print(f"有登录元素: {state['hasLoginElements']}")
            print(f"有聊天界面: {state['hasChatInterface']}")

            if state["errorMessages"]:
                print(f"错误消息: {[e['text'] for e in state['errorMessages'] if e['text']]}")

            # 评估状态
            if state["hasLoginElements"]:
                print("⚠️ 可能需要登录")
                return False
            elif state["hasChatInterface"]:
                print("✅ 聊天界面可用")
                return True
            else:
                print("⚠️ 界面状态未知")
                return False

    except Exception as e:
        print(f"❌ 检查认证状态失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_doubao_model():
    print("\n3. 检查豆包AI模型可用性...")

    doubao = DoubaoCLI()

    try:
        # 发送一个简单的测试消息
        test_message = "你好，请回复'测试成功'"
        print(f"发送测试消息: {test_message}")

        result = doubao.enhanced.send_message_to_ai(test_message, use_enhanced=True)
        print(f"发送结果: {result}")

        # 等待响应
        print("等待10秒查看响应...")
        time.sleep(10)

        # 检查是否有响应
        check_response_js = """
        (function() {
            // 查找所有文本内容
            var allText = document.body.innerText || document.body.textContent || '';

            // 查找最新消息
            var messages = document.querySelectorAll('[data-message-id], .message, .chat-message, [role="article"]');
            var lastMessages = [];

            for (var i = Math.max(0, messages.length - 3); i < messages.length; i++) {
                var msg = messages[i];
                var text = (msg.textContent || msg.innerText || '').trim();
                if (text) {
                    lastMessages.push({
                        index: i,
                        text: text.substring(0, 100),
                        hasImages: msg.querySelectorAll('img').length > 0
                    });
                }
            }

            return JSON.stringify({
                totalMessages: messages.length,
                lastMessages: lastMessages,
                containsTestSuccess: allText.includes('测试成功') || allText.includes('test success'),
                anyResponse: messages.length > 0
            }, null, 2);
        })()
        """

        result2 = doubao.execute_javascript(1, 1, check_response_js)
        print(f"响应检查: {result2}")

        if "JavaScript执行结果: " in result2:
            json_str = result2.split("JavaScript执行结果: ", 1)[1]
            response = json.loads(json_str)

            print(f"\n模型响应分析:")
            print(f"总消息数: {response['totalMessages']}")
            print(f"包含测试成功: {response['containsTestSuccess']}")
            print(f"有任何响应: {response['anyResponse']}")

            if response["lastMessages"]:
                print(f"最近消息:")
                for msg in response["lastMessages"]:
                    print(f"  [{msg['index']}] {msg['text']}")

            if response["containsTestSuccess"] or response["anyResponse"]:
                print("✅ AI模型响应正常")
                return True
            else:
                print("⚠️ AI模型未响应")
                return False

    except Exception as e:
        print(f"❌ 检查模型失败: {e}")
        return False


def test_basic_workflow():
    print("\n4. 测试基础工作流...")

    doubao = DoubaoCLI()

    try:
        # 打开页面
        doubao.open_doubao_ai()
        time.sleep(3)

        # 点击AI创作按钮
        print("点击AI创作按钮...")
        click_result = doubao.enhanced.executor.click_button("AI 创作")
        if click_result.success:
            print(f"✅ 进入AI创作界面")
            time.sleep(3)
        else:
            print(f"❌ 无法进入AI创作界面: {click_result.error_message}")
            return False

        # 发送一个明确的消息
        print("发送明确的消息...")
        message = "请生成一张简单的测试图片，比如一个红色的圆形"
        result = doubao.enhanced.send_message_to_ai(message, use_enhanced=True)
        print(f"发送结果: {result}")

        # 等待长时间
        print("等待60秒让AI处理...")
        time.sleep(60)

        # 检查结果
        check_result_js = """
        (function() {
            // 查找所有图像
            var images = document.querySelectorAll('img');
            var generatedImages = [];

            images.forEach((img, idx) => {
                if (img.complete && img.naturalWidth > 50 && img.naturalHeight > 50) {
                    // 过滤掉logo和头像
                    var src = img.src || '';
                    if (!src.includes('logo') && !src.includes('avatar') && !src.includes('icon')) {
                        generatedImages.push({
                            index: idx,
                            src: src.substring(0, 80),
                            width: img.naturalWidth,
                            height: img.naturalHeight,
                            alt: img.alt || ''
                        });
                    }
                }
            });

            return JSON.stringify({
                totalImages: images.length,
                generatedImages: generatedImages,
                generatedCount: generatedImages.length,
                hasGeneratedImages: generatedImages.length > 0
            }, null, 2);
        })()
        """

        result2 = doubao.execute_javascript(1, 1, check_result_js)
        print(f"结果检查: {result2}")

        if "JavaScript执行结果: " in result2:
            json_str = result2.split("JavaScript执行结果: ", 1)[1]
            result_data = json.loads(json_str)

            print(f"\n工作流测试结果:")
            print(f"总图像数: {result_data['totalImages']}")
            print(f"生成图像数: {result_data['generatedCount']}")
            print(f"有生成图像: {result_data['hasGeneratedImages']}")

            if result_data["hasGeneratedImages"]:
                print("🎉 工作流测试成功!")
                for img in result_data["generatedImages"][:3]:
                    print(f"  图像: {img['width']}x{img['height']}, 源: {img['src']}...")
                return True
            else:
                print("⚠️ 工作流测试未生成图像")
                return False

    except Exception as e:
        print(f"❌ 工作流测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def provide_recommendations(app_running, auth_ok, model_ok, workflow_ok):
    print("\n=== 诊断结果和建议 ===")

    issues = []
    recommendations = []

    if not app_running:
        issues.append("豆包应用未运行")
        recommendations.append("1. 手动启动豆包应用")
        recommendations.append("2. 确保豆包已登录")

    if not auth_ok:
        issues.append("认证状态可能有问题")
        recommendations.append("1. 在浏览器中检查豆包是否已登录")
        recommendations.append("2. 清除浏览器缓存后重新登录")

    if not model_ok:
        issues.append("AI模型未响应")
        recommendations.append("1. 检查网络连接")
        recommendations.append("2. 尝试不同的AI模型（如果有选择）")
        recommendations.append("3. 重启豆包应用")

    if not workflow_ok:
        issues.append("工作流测试失败")
        recommendations.append("1. 手动在豆包中测试图像生成功能")
        recommendations.append("2. 检查豆包是否有图像生成权限")
        recommendations.append("3. 尝试不同的提示词格式")

    if not issues:
        print("✅ 所有检查通过，豆包状态正常")
        return True
    else:
        print(f"⚠️ 发现 {len(issues)} 个问题:")
        for issue in issues:
            print(f"  - {issue}")

        print(f"\n建议的操作:")
        for rec in recommendations:
            print(f"  {rec}")

        return False


if __name__ == "__main__":
    print("豆包AI应用状态诊断")
    print("=" * 50)

    # 执行各项检查
    app_running = check_doubao_app()
    auth_ok = check_doubao_auth()
    model_ok = check_doubao_model()
    workflow_ok = test_basic_workflow()

    # 提供建议
    overall_ok = provide_recommendations(app_running, auth_ok, model_ok, workflow_ok)

    if overall_ok:
        print("\n✅ 诊断完成，状态正常，可以继续开发")
        sys.exit(0)
    else:
        print("\n❌ 诊断完成，需要解决问题后再继续")
        sys.exit(1)
