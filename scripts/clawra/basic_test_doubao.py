#!/usr/bin/env python3
"""
豆包AI基础功能测试
简化版测试，专注于核心功能验证
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def safe_execute_javascript(doubao, js_code, description="执行JavaScript"):
    """安全的JavaScript执行，包含错误处理"""
    print(f"\n{description}...")
    try:
        result = doubao.execute_javascript(1, 1, js_code)
        print(f"原始结果: {result[:200]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1].strip()

            # 处理特殊情况
            if json_str == "missing value":
                print("⚠️ JavaScript返回'missing value'")
                return {"error": "missing_value", "raw": result}

            try:
                parsed = json.loads(json_str)
                return {"success": True, "data": parsed, "raw": result}
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"原始JSON: {json_str[:200]}")
                return {"error": f"json_parse_error: {e}", "raw": result}
        else:
            print(f"❌ 响应格式异常: {result[:200]}")
            return {"error": "invalid_format", "raw": result}

    except Exception as e:
        print(f"❌ JavaScript执行失败: {e}")
        return {"error": f"execution_error: {e}", "raw": ""}


def test_1_launch_and_check():
    """测试1: 启动豆包并检查基础状态"""
    print("\n" + "=" * 60)
    print("测试1: 启动豆包并检查基础状态")
    print("=" * 60)

    doubao = DoubaoCLI()

    # 1. 打开页面
    print("1. 打开豆包AI页面...")
    result = doubao.open_doubao_ai()
    print(f"   结果: {result}")
    time.sleep(5)  # 等待页面加载

    # 2. 检查页面基础信息
    print("\n2. 检查页面基础信息...")
    js_check = """
    (function() {
        var state = {
            title: document.title || "无标题",
            url: window.location.href || "无URL",
            readyState: document.readyState,
            hasBody: !!document.body,
            bodyChildrenCount: document.body ? document.body.children.length : 0,
            // 简单检查几个关键元素
            hasTextarea: !!document.querySelector('textarea'),
            hasInput: !!document.querySelector('input'),
            hasButton: !!document.querySelector('button'),
            allButtonCount: document.querySelectorAll('button').length,
            // 检查可见文本
            visibleText: document.body ? (document.body.innerText || document.body.textContent || '').substring(0, 200) : '无内容'
        };
        return JSON.stringify(state, null, 2);
    })()
    """

    result = safe_execute_javascript(doubao, js_check, "检查页面基础状态")
    if result.get("success"):
        data = result["data"]
        print(f"✅ 页面状态检查成功:")
        print(f"   标题: {data['title']}")
        print(f"   URL: {data['url']}")
        print(f"   准备状态: {data['readyState']}")
        print(f"   有body: {data['hasBody']}")
        print(f"   body子元素数: {data['bodyChildrenCount']}")
        print(f"   有输入框: {data['hasTextarea']}")
        print(f"   有输入元素: {data['hasInput']}")
        print(f"   有按钮: {data['hasButton']} (总数: {data['allButtonCount']})")
        print(f"   可见文本前200字: {data['visibleText'][:100]}...")

        # 关键检查：是否有输入框
        if data["hasTextarea"]:
            print("✅ 发现输入框，可以继续测试")
            return True, "有输入框"
        else:
            print("⚠️ 未发现输入框，可能页面未正确加载或需要登录")
            print(f"   建议：手动检查豆包界面，确认是否显示聊天输入框")
            return False, "无输入框"
    else:
        print(f"❌ 页面状态检查失败: {result.get('error')}")
        return False, f"检查失败: {result.get('error')}"


def test_2_send_simple_message():
    """测试2: 发送简单消息"""
    print("\n" + "=" * 60)
    print("测试2: 发送简单消息")
    print("=" * 60)

    doubao = DoubaoCLI()

    # 发送简单消息
    test_message = "你好"
    print(f"发送测试消息: '{test_message}'")
    result = doubao.enhanced.send_message_to_ai(test_message, use_enhanced=True)
    print(f"发送结果: {result}")

    # 等待响应
    print("等待15秒查看响应...")
    time.sleep(15)

    # 检查是否有新消息
    js_check_messages = """
    (function() {
        // 查找所有包含文本的元素
        var allElements = document.querySelectorAll('*');
        var messages = [];

        allElements.forEach(function(el, idx) {
            var text = (el.innerText || el.textContent || '').trim();
            if (text && text.length > 2 && text.length < 500) {
                // 检查是否是聊天消息
                var isUser = text.includes('你好') || text.includes('Hello');
                var isAI = !isUser && text.length > 5;

                if (isUser || isAI) {
                    messages.push({
                        index: idx,
                        text: text.substring(0, 100),
                        isUser: isUser,
                        isAI: isAI,
                        tagName: el.tagName,
                        className: (el.className || '').substring(0, 30)
                    });
                }
            }
        });

        // 按出现顺序排序，取最近5个
        var recent = messages.slice(-5);

        return JSON.stringify({
            totalFound: messages.length,
            recentMessages: recent,
            hasUserMessage: messages.some(m => m.isUser),
            hasAIMessage: messages.some(m => m.isAI),
            latestAIText: messages.filter(m => m.isAI).pop() ? messages.filter(m => m.isAI).pop().text : "无AI消息"
        }, null, 2);
    })()
    """

    result = safe_execute_javascript(doubao, js_check_messages, "检查消息响应")
    if result.get("success"):
        data = result["data"]
        print(f"\n消息检查结果:")
        print(f"   发现消息总数: {data['totalFound']}")
        print(f"   有用户消息: {data['hasUserMessage']}")
        print(f"   有AI消息: {data['hasAIMessage']}")
        print(f"   最新AI消息: {data['latestAIText'][:80]}...")

        if data["hasAIMessage"]:
            print("✅ AI已响应消息!")
            return True, "AI已响应"
        else:
            print("⚠️ AI未响应消息")
            print(f"   最近消息:")
            for msg in data["recentMessages"][:3]:
                print(f"     [{msg['index']}] {msg['text'][:60]}...")
            return False, "AI未响应"
    else:
        print(f"❌ 消息检查失败: {result.get('error')}")
        return False, f"检查失败: {result.get('error')}"


def test_3_check_ai_interface():
    """测试3: 检查AI创作界面"""
    print("\n" + "=" * 60)
    print("测试3: 检查AI创作界面")
    print("=" * 60)

    doubao = DoubaoCLI()

    # 尝试点击AI创作按钮
    print("尝试进入AI创作界面...")
    click_result = doubao.enhanced.executor.click_button("AI 创作")
    print(f"点击结果: {click_result.success}")

    if click_result.success:
        print("✅ 成功进入AI创作界面")
        time.sleep(3)

        # 检查创作界面元素
        js_check_creation = """
        (function() {
            var state = {
                // 查找创作相关元素
                hasCreationTitle: !!document.querySelector('*:contains("创作"), *:contains("生成"), *:contains("Create")'),
                hasImageOption: !!document.querySelector('*:contains("图片"), *:contains("图像"), *:contains("Image")'),
                hasVideoOption: !!document.querySelector('*:contains("视频"), *:contains("Video")'),
                hasPromptInput: !!document.querySelector('[placeholder*="描述"], [placeholder*="prompt"], [placeholder*="输入"]'),
                // 检查按钮
                allButtons: Array.from(document.querySelectorAll('button')).map(b => ({
                    text: (b.innerText || b.textContent || '').trim().substring(0, 30),
                    disabled: b.disabled
                })).filter(b => b.text)
            };

            return JSON.stringify(state, null, 2);
        })()
        """

        result = safe_execute_javascript(doubao, js_check_creation, "检查创作界面")
        if result.get("success"):
            data = result["data"]
            print(f"创作界面状态:")
            print(f"   有创作标题: {data['hasCreationTitle']}")
            print(f"   有图片选项: {data['hasImageOption']}")
            print(f"   有视频选项: {data['hasVideoOption']}")
            print(f"   有提示词输入框: {data['hasPromptInput']}")
            print(f"   按钮列表 ({len(data['allButtons'])}个):")
            for btn in data["allButtons"][:5]:
                print(f"     - '{btn['text']}' (禁用: {btn['disabled']})")

            if data["hasImageOption"] or data["hasPromptInput"]:
                print("✅ AI创作界面可用")
                return True, "创作界面可用"
            else:
                print("⚠️ 创作界面元素不全")
                return False, "创作界面不完整"
        else:
            print(f"❌ 创作界面检查失败: {result.get('error')}")
            return False, f"检查失败: {result.get('error')}"
    else:
        print(f"❌ 无法进入AI创作界面: {click_result.error_message}")
        return False, "无法进入创作界面"


def main():
    print("豆包AI基础功能测试")
    print("版本: 简化核心测试")
    print("=" * 60)

    results = []

    # 测试1: 基础状态
    test1_ok, test1_msg = test_1_launch_and_check()
    results.append(("启动和基础检查", test1_ok, test1_msg))

    # 只有基础检查通过才继续
    if test1_ok:
        # 测试2: 发送消息
        test2_ok, test2_msg = test_2_send_simple_message()
        results.append(("消息发送测试", test2_ok, test2_msg))

        # 测试3: AI创作界面
        test3_ok, test3_msg = test_3_check_ai_interface()
        results.append(("AI创作界面", test3_ok, test3_msg))
    else:
        print("\n⚠️ 基础检查失败，跳过后续测试")
        results.append(("消息发送测试", False, "跳过（基础检查失败）"))
        results.append(("AI创作界面", False, "跳过（基础检查失败）"))

    # 打印汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    total_tests = len(results)
    passed_tests = sum(1 for _, ok, _ in results if ok)
    failed_tests = total_tests - passed_tests

    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")

    for i, (name, ok, msg) in enumerate(results, 1):
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"\n{i}. {name}: {status}")
        print(f"   详情: {msg}")

    print("\n" + "=" * 60)
    print("结论和建议")
    print("=" * 60)

    if passed_tests == total_tests:
        print("✅ 所有测试通过，豆包AI功能正常")
        print("\n📝 下一步:")
        print("1. 可以继续图像生成测试")
        print("2. 运行doubao_image_generator.py测试完整生成流程")
        print("3. 集成到生产系统")
    else:
        print(f"⚠️ 部分测试失败 ({failed_tests}/{total_tests})")

        if not test1_ok:
            print("\n🔍 问题诊断（基础检查失败）:")
            print("1. 豆包应用可能未完全启动")
            print("2. 页面可能未正确加载")
            print("3. 可能需要登录账户")
            print("4. 输入框可能被隐藏或使用不同元素")
            print("\n📝 解决步骤:")
            print("1. 手动启动豆包应用")
            print("2. 登录账户（如果需要）")
            print("3. 进入AI聊天界面")
            print("4. 确保输入框可见")
            print("5. 重新运行测试")

        elif test1_ok and not test2_ok:
            print("\n🔍 问题诊断（AI未响应消息）:")
            print("1. AI服务可能暂时不可用")
            print("2. 网络连接问题")
            print("3. 免费额度可能已用完")
            print("4. 可能需要特定的消息格式")
            print("\n📝 解决步骤:")
            print("1. 手动在豆包中测试消息发送")
            print("2. 检查网络连接")
            print("3. 尝试不同的消息内容")
            print("4. 等待一段时间后重试")

        elif test2_ok and not test3_ok:
            print("\n🔍 问题诊断（创作界面不可用）:")
            print("1. 按钮文本可能已变化")
            print("2. 创作功能可能需要特定权限")
            print("3. 界面布局可能已更新")
            print("\n📝 解决步骤:")
            print("1. 手动检查AI创作功能")
            print("2. 查看按钮的实际文本")
            print("3. 确认是否有图像生成权限")

        print("\n📋 推荐操作顺序:")
        print("1. 运行start_doubao.py启动和验证豆包")
        print("2. 运行verify_manually.py完成手动验证")
        print("3. 根据手动验证结果解决具体问题")
        print("4. 重新运行此测试脚本")

    # 保存结果
    result_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "details": [
            {
                "test_name": name,
                "passed": ok,
                "message": msg,
                "timestamp": time.strftime("%H:%M:%S"),
            }
            for name, ok, msg in results
        ],
    }

    result_file = "basic_test_results.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"\n详细结果已保存到: {result_file}")

    # 退出码
    if passed_tests == total_tests:
        print("\n✅ 测试完成，所有功能正常")
        sys.exit(0)
    else:
        print("\n❌ 测试完成，发现问题需要解决")
        sys.exit(1)


if __name__ == "__main__":
    main()
