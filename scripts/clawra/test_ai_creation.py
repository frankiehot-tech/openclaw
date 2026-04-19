#!/usr/bin/env python3
"""
测试AI创作界面访问
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def test_direct_click():
    """直接点击AI创作按钮"""
    print("=== 直接点击AI创作按钮 ===")

    doubao = DoubaoCLI()

    # 打开页面
    print("1. 打开豆包页面...")
    doubao.open_doubao_ai()
    time.sleep(3)

    # 尝试直接使用现有的click_button方法
    print("2. 尝试点击'AI 创作'按钮...")
    click_result = doubao.enhanced.executor.click_button("AI 创作")
    print(f"点击结果: {click_result.success}")
    print(f"错误信息: {click_result.error_message}")

    if click_result.success:
        print("✅ 点击成功，等待页面响应...")
        time.sleep(3)

        # 检查当前页面状态
        js_check = """
        (function() {
            var state = {
                title: document.title,
                url: window.location.href,
                // 检查是否有创作相关文本
                hasCreationText: document.body.innerText.includes('创作') ||
                                document.body.innerText.includes('生成') ||
                                document.body.innerText.includes('Create'),
                // 查找可能的创作界面元素
                creationElements: [],
                // 查找输入框
                hasPromptInput: !!document.querySelector('[placeholder*="描述"], [placeholder*="输入"], [placeholder*="prompt"]')
            };

            // 查找所有可能相关的元素
            var elements = document.querySelectorAll('div, button, span, a');
            elements.forEach(function(el) {
                var text = (el.innerText || el.textContent || '').trim();
                if (text && (text.includes('图片') || text.includes('图像') || text.includes('Image') ||
                            text.includes('视频') || text.includes('Video') || text.includes('生成'))) {
                    state.creationElements.push({
                        text: text.substring(0, 50),
                        tagName: el.tagName,
                        className: (el.className || '').substring(0, 30)
                    });
                }
            });

            return JSON.stringify(state, null, 2);
        })()
        """

        try:
            result = doubao.execute_javascript(1, 1, js_check)
            print(f"页面检查结果: {result[:300]}...")

            if "JavaScript执行结果: " in result:
                json_str = result.split("JavaScript执行结果: ", 1)[1]
                if json_str.strip() != "missing value":
                    try:
                        data = json.loads(json_str)
                        print(f"\n创作界面状态:")
                        print(f"   标题: {data['title']}")
                        print(f"   URL: {data['url']}")
                        print(f"   有创作文本: {data['hasCreationText']}")
                        print(f"   有提示词输入框: {data['hasPromptInput']}")
                        print(f"   创作相关元素: {len(data['creationElements'])}")

                        if data["creationElements"]:
                            print(f"   前3个元素:")
                            for i, el in enumerate(data["creationElements"][:3]):
                                print(
                                    f"     {i+1}. '{el['text']}' (标签: {el['tagName']}, 类: {el['className']})"
                                )

                        return True
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON解析失败: {e}")
                else:
                    print("⚠️ JavaScript返回'missing value'")
            else:
                print("❌ JavaScript执行结果格式异常")

        except Exception as e:
            print(f"❌ 检查创作界面失败: {e}")

    return False


def test_javascript_click():
    """使用JavaScript直接点击"""
    print("\n=== 使用JavaScript直接点击 ===")

    doubao = DoubaoCLI()

    # 打开页面
    print("1. 打开豆包页面...")
    doubao.open_doubao_ai()
    time.sleep(3)

    # 尝试多种JavaScript点击方式
    click_methods = [
        # 方法1: 通过文本内容查找并点击
        """
        (function() {
            // 查找所有元素
            var allElements = document.querySelectorAll('*');
            var clicked = false;

            for (var i = 0; i < allElements.length; i++) {
                var el = allElements[i];
                var text = (el.innerText || el.textContent || '').trim();

                if (text === 'AI 创作' || text.includes('AI 创作')) {
                    console.log('找到AI创作元素:', el);
                    el.click();
                    clicked = true;
                    break;
                }
            }

            return clicked ? '点击成功' : '未找到元素';
        })()
        """,
        # 方法2: 通过按钮属性查找
        """
        (function() {
            // 查找所有按钮
            var buttons = document.querySelectorAll('button, [role="button"], [onclick]');
            var clicked = false;

            for (var i = 0; i < buttons.length; i++) {
                var btn = buttons[i];
                var text = (btn.innerText || btn.textContent || '').trim();

                if (text === 'AI 创作' || text.includes('AI 创作')) {
                    console.log('找到AI创作按钮:', btn);
                    btn.click();
                    clicked = true;
                    break;
                }
            }

            return clicked ? '按钮点击成功' : '未找到按钮';
        })()
        """,
        # 方法3: 通过类名查找（根据之前的探索结果）
        """
        (function() {
            // 尝试之前的探索中发现的类名
            var selectors = [
                '.mb-22',  // 探索结果中的类名
                '[class*="flex-col"]',
                '[class*="gap-3"]',
                'div'  // 所有div
            ];

            for (var j = 0; j < selectors.length; j++) {
                var elements = document.querySelectorAll(selectors[j]);
                for (var i = 0; i < elements.length; i++) {
                    var el = elements[i];
                    var text = (el.innerText || el.textContent || '').trim();

                    if (text === 'AI 创作' || text.includes('AI 创作')) {
                        console.log('通过选择器找到:', selectors[j], el);
                        el.click();
                        return '通过选择器点击成功: ' + selectors[j];
                    }
                }
            }

            return '所有选择器都未找到';
        })()
        """,
    ]

    for i, js_code in enumerate(click_methods):
        print(f"\n2. 尝试方法 {i+1}...")
        try:
            result = doubao.execute_javascript(1, 1, js_code)
            print(f"点击结果: {result}")

            # 等待页面响应
            time.sleep(2)

            # 检查是否成功
            check_js = """
            (function() {
                var hasChanged = document.title !== "豆包 - 字节跳动旗下 AI 智能助手" ||
                                window.location.href !== "https://www.doubao.com/chat/";
                return JSON.stringify({
                    titleChanged: document.title,
                    urlChanged: window.location.href,
                    hasChanged: hasChanged
                }, null, 2);
            })()
            """

            check_result = doubao.execute_javascript(1, 1, check_js)
            print(f"页面变化检查: {check_result}")

            if "JavaScript执行结果: " in check_result:
                json_str = check_result.split("JavaScript执行结果: ", 1)[1]
                if json_str.strip() != "missing value":
                    try:
                        data = json.loads(json_str)
                        if data["hasChanged"]:
                            print(f"✅ 页面已变化，可能已进入创作界面")
                            print(f"   新标题: {data['titleChanged']}")
                            print(f"   新URL: {data['urlChanged']}")
                            return True
                    except:
                        pass

        except Exception as e:
            print(f"❌ 方法 {i+1} 失败: {e}")

    return False


def test_manual_navigation():
    """测试手动导航到图像生成"""
    print("\n=== 测试手动导航到图像生成 ===")

    doubao = DoubaoCLI()

    # 打开页面
    print("1. 打开豆包页面...")
    doubao.open_doubao_ai()
    time.sleep(3)

    # 首先尝试发送图像生成命令
    print("2. 直接发送图像生成命令...")
    image_command = "/draw 一个红色的圆形"
    result = doubao.enhanced.send_message_to_ai(image_command, use_enhanced=True)
    print(f"发送结果: {result}")

    # 等待响应
    print("3. 等待30秒...")
    time.sleep(30)

    # 检查结果
    js_check = """
    (function() {
        var state = {
            // 检查是否有图像生成相关文本
            hasImageText: document.body.innerText.includes('图片') ||
                         document.body.innerText.includes('图像') ||
                         document.body.innerText.includes('正在生成') ||
                         document.body.innerText.includes('生成中'),
            // 查找图像
            images: [],
            // 查找进度或状态指示器
            hasProgress: !!document.querySelector('[role="progressbar"], .progress, .loading'),
            // 最近的消息
            recentMessages: []
        };

        // 查找图像
        var allImages = document.querySelectorAll('img');
        allImages.forEach(function(img, idx) {
            if (img.complete && img.naturalWidth > 50) {
                state.images.push({
                    index: idx,
                    src: (img.src || '').substring(0, 80),
                    width: img.naturalWidth,
                    height: img.naturalHeight,
                    alt: img.alt || '',
                    isNew: !img.src.includes('avatar') && !img.src.includes('logo') && !img.src.includes('icon')
                });
            }
        });

        // 查找最近的消息
        var allElements = document.querySelectorAll('div, p, span, article');
        for (var i = 0; i < allElements.length; i++) {
            var el = allElements[i];
            var text = (el.innerText || el.textContent || '').trim();
            if (text && text.length > 10 && text.length < 500) {
                state.recentMessages.push({
                    text: text.substring(0, 100),
                    length: text.length
                });
            }
            if (state.recentMessages.length >= 5) break;
        }

        return JSON.stringify(state, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, js_check)
        print(f"图像生成检查: {result[:400]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            if json_str.strip() != "missing value":
                try:
                    data = json.loads(json_str)
                    print(f"\n图像生成状态:")
                    print(f"   有图像相关文本: {data['hasImageText']}")
                    print(f"   有进度指示器: {data['hasProgress']}")
                    print(f"   图像数量: {len(data['images'])}")

                    new_images = [img for img in data["images"] if img["isNew"]]
                    print(f"   新图像数量: {len(new_images)}")

                    if new_images:
                        print(f"🎉 发现可能的新图像!")
                        for img in new_images[:2]:
                            print(f"   图像: {img['width']}x{img['height']}, 源: {img['src']}...")
                        return True

                    if data["recentMessages"]:
                        print(f"   最近消息:")
                        for msg in data["recentMessages"][:3]:
                            print(f"     - {msg['text'][:60]}...")

                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
            else:
                print("⚠️ JavaScript返回'missing value'")
        else:
            print("❌ JavaScript执行结果格式异常")

    except Exception as e:
        print(f"❌ 图像生成检查失败: {e}")

    return False


def main():
    print("AI创作界面访问测试")
    print("=" * 60)

    results = []

    # 测试1: 直接点击
    print("\n测试1: 使用现有click_button方法")
    test1_ok = test_direct_click()
    results.append(("直接点击", test1_ok))

    # 测试2: JavaScript点击
    print("\n测试2: 使用JavaScript点击")
    test2_ok = test_javascript_click()
    results.append(("JavaScript点击", test2_ok))

    # 测试3: 手动导航
    print("\n测试3: 直接发送图像生成命令")
    test3_ok = test_manual_navigation()
    results.append(("直接发送命令", test3_ok))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    total_tests = len(results)
    passed_tests = sum(1 for _, ok in results if ok)

    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {total_tests - passed_tests}")

    for i, (name, ok) in enumerate(results, 1):
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"{i}. {name}: {status}")

    print("\n📝 分析和建议:")

    if passed_tests > 0:
        print("✅ 至少有一种方法有效")
        if test3_ok:
            print("   直接发送图像生成命令可能有效，需要进一步验证")
    else:
        print("⚠️ 所有方法都失败，可能原因:")
        print("   1. 豆包界面结构已更新")
        print("   2. 需要先登录或授权")
        print("   3. 创作功能可能需要特定权限")
        print("   4. 免费额度可能已用完")

    print("\n🎯 下一步:")
    print("1. 手动在豆包中测试图像生成功能")
    print("2. 检查是否有'开始创作'或'图像生成'按钮")
    print("3. 尝试不同的命令格式，如'/draw'、'/生成图片'等")
    print("4. 查看豆包是否有使用限制或需要订阅")

    # 保存结果
    result_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": [
            {"test_name": name, "passed": ok, "timestamp": time.strftime("%H:%M:%S")}
            for name, ok in results
        ],
        "summary": {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
        },
    }

    result_file = "ai_creation_test_results.json"
    try:
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {result_file}")
    except Exception as e:
        print(f"❌ 保存结果失败: {e}")

    if passed_tests > 0:
        print("\n✅ 测试完成，有可行的方法")
        sys.exit(0)
    else:
        print("\n❌ 测试完成，需要进一步调查")
        sys.exit(1)


if __name__ == "__main__":
    main()
