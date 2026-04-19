#!/usr/bin/env python3
"""豆包JavaScript执行诊断测试"""

import logging
import os
import sys
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def test_simple_javascript():
    """测试简单的JavaScript执行"""
    print("=== 测试简单JavaScript执行 ===")

    cli = DoubaoCLIEnhanced()

    # 测试1: 获取页面标题
    print("\n1. 测试获取页面标题:")
    result = cli.execute_javascript_enhanced("document.title")
    print(f"   成功: {result.success}")
    print(f"   输出: {result.output}")
    print(f"   错误: {result.error_message}")

    # 测试2: 获取URL
    print("\n2. 测试获取页面URL:")
    result = cli.execute_javascript_enhanced("window.location.href")
    print(f"   成功: {result.success}")
    print(f"   输出: {result.output}")
    print(f"   错误: {result.error_message}")

    # 测试3: 简单的JSON返回
    print("\n3. 测试JSON返回:")
    result = cli.execute_javascript_enhanced("JSON.stringify({test: 'value', number: 123})")
    print(f"   成功: {result.success}")
    print(f"   输出: {result.output}")
    print(f"   错误: {result.error_message}")

    # 测试4: 检查DOM元素数量
    print("\n4. 测试DOM查询:")
    result = cli.execute_javascript_enhanced("document.querySelectorAll('img').length")
    print(f"   成功: {result.success}")
    print(f"   输出: {result.output}")
    print(f"   错误: {result.error_message}")

    # 测试5: 增强检测逻辑的简化版
    print("\n5. 测试增强检测逻辑（简化）:")
    simple_js = """
    (function() {
        var images = document.querySelectorAll('img');
        var urls = [];
        for (var i = 0; i < images.length; i++) {
            if (images[i].src && images[i].src.startsWith('http')) {
                urls.push(images[i].src);
            }
        }
        return JSON.stringify({
            image_count: urls.length,
            urls: urls
        });
    })()
    """
    result = cli.execute_javascript_enhanced(simple_js)
    print(f"   成功: {result.success}")
    print(f"   输出: {result.output}")
    print(f"   错误: {result.error_message}")

    # 测试6: 检查是否存在特定元素
    print("\n6. 检查AI绘画相关元素:")
    check_js = """
    // 检查可能的AI绘画界面元素
    var elements = {
        textareas: document.querySelectorAll('textarea').length,
        inputs: document.querySelectorAll('input[type="text"]').length,
        buttons: document.querySelectorAll('button').length,
        progress: document.querySelectorAll('[role="progressbar"], .progress, .loading').length,
        resultContainers: document.querySelectorAll('[class*="result"], [class*="output"]').length
    };
    return JSON.stringify(elements);
    """
    result = cli.execute_javascript_enhanced(check_js)
    print(f"   成功: {result.success}")
    print(f"   输出: {result.output}")
    print(f"   错误: {result.error_message}")

    return True


def test_navigation_to_painting():
    """测试导航到绘画界面"""
    print("\n=== 测试导航到AI绘画界面 ===")

    cli = DoubaoCLIEnhanced()

    # 获取当前状态
    print("当前状态:")
    title_result = cli.execute_javascript_enhanced("document.title")
    url_result = cli.execute_javascript_enhanced("window.location.href")

    print(f"  标题: {title_result.output if title_result.success else '获取失败'}")
    print(f"  URL: {url_result.output if url_result.success else '获取失败'}")

    # 尝试打开绘画界面
    print("\n尝试打开AI绘画界面...")
    open_result = cli._open_painting_interface()
    print(f"  打开结果: {open_result}")

    time.sleep(3)  # 等待页面加载

    # 检查新状态
    print("\n导航后状态:")
    title_result = cli.execute_javascript_enhanced("document.title")
    url_result = cli.execute_javascript_enhanced("window.location.href")

    print(f"  标题: {title_result.output if title_result.success else '获取失败'}")
    print(f"  URL: {url_result.output if url_result.success else '获取失败'}")

    # 检查页面内容
    print("\n页面内容分析:")
    content_js = """
    // 获取页面关键元素
    var bodyText = document.body.innerText.substring(0, 300);
    var hasAIKeywords = bodyText.includes('AI') || bodyText.includes('绘画') ||
                       bodyText.includes('生成') || bodyText.includes('创作');
    return JSON.stringify({
        text_preview: bodyText,
        has_ai_keywords: hasAIKeywords,
        body_length: document.body.innerText.length
    });
    """
    result = cli.execute_javascript_enhanced(content_js)
    if result.success:
        import json

        try:
            content = json.loads(result.output)
            print(f"  文本预览: {content.get('text_preview', '')}")
            print(f"  包含AI关键词: {content.get('has_ai_keywords', False)}")
            print(f"  页面长度: {content.get('body_length', 0)} 字符")
        except:
            print(f"  解析失败: {result.output}")
    else:
        print(f"  内容检查失败: {result.error_message}")

    return open_result


def test_input_prompt():
    """测试输入提示词"""
    print("\n=== 测试输入提示词 ===")

    cli = DoubaoCLIEnhanced()

    test_prompt = "测试提示词"
    print(f"尝试输入提示词: '{test_prompt}'")

    result = cli._input_prompt(test_prompt)
    print(f"  输入结果: {result}")

    # 验证输入
    verify_js = """
    // 检查是否有textarea或input包含文本
    var textareas = document.querySelectorAll('textarea, input[type="text"]');
    var foundText = '';
    for (var i = 0; i < textareas.length; i++) {
        if (textareas[i].value && textareas[i].value.length > 0) {
            foundText = textareas[i].value;
            break;
        }
    }
    return foundText || '未找到输入文本';
    """

    verify_result = cli.execute_javascript_enhanced(verify_js)
    print(f"  验证结果: {verify_result.output if verify_result.success else '验证失败'}")

    return result


def main():
    """主诊断函数"""
    print("豆包JavaScript执行诊断测试\n")

    # 用户确认
    print("此测试将在豆包中执行JavaScript代码。")
    print("请确保豆包App正在运行并已登录。")
    print()

    response = input("是否继续？(y/n): ")
    if response.lower() != "y":
        print("测试取消")
        return 0

    # 运行测试
    tests = [test_simple_javascript, test_navigation_to_painting, test_input_prompt]

    for test in tests:
        try:
            print("\n" + "=" * 60)
            test()
            time.sleep(2)
        except Exception as e:
            print(f"测试失败: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("诊断测试完成")
    print("请检查以上输出以确定问题所在")

    return 0


if __name__ == "__main__":
    sys.exit(main())
