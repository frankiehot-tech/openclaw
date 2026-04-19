#!/usr/bin/env python3
"""
测试打开AI绘画界面
"""

import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def test_open_ai_interface():
    """测试打开AI绘画界面"""
    print("🔧 测试打开AI绘画界面...")

    cli = DoubaoCLIEnhanced()

    # 测试1: 直接调用_open_painting_interface方法
    print("\n📋 测试1: 直接调用_open_painting_interface")
    try:
        success = cli._open_painting_interface()
        print(f"   结果: {success}")

        # 测试2: 检查是否在AI绘画页面
        print("\n📋 测试2: 检查当前页面状态")
        check_js = """
        var pageInfo = {
            title: document.title,
            url: window.location.href,
            buttons: document.querySelectorAll('button').length,
            textareas: document.querySelectorAll('textarea').length,
            hasPrompt: (function() {
                var textareas = document.querySelectorAll('textarea');
                for (var i = 0; i < textareas.length; i++) {
                    var placeholder = textareas[i].placeholder || '';
                    if (placeholder.includes('提示词') || placeholder.includes('Prompt') || placeholder.includes('描述')) {
                        return true;
                    }
                }
                return false;
            })()
        };
        JSON.stringify(pageInfo);
        """

        result = cli.execute_javascript_enhanced(check_js)
        if result.success and result.output and result.output != "missing value":
            try:
                page_info = json.loads(cli._clean_js_output(result.output))
                print(f"   标题: {page_info.get('title')}")
                print(f"   URL: {page_info.get('url')}")
                print(f"   按钮数量: {page_info.get('buttons')}")
                print(f"   文本区域数量: {page_info.get('textareas')}")
                print(f"   有提示词输入框: {page_info.get('hasPrompt')}")

                # 检查是否为AI绘画页面
                is_ai_page = (
                    page_info.get("title", "").lower().find("ai") != -1
                    or page_info.get("title", "").lower().find("绘画") != -1
                    or page_info.get("title", "").lower().find("draw") != -1
                    or page_info.get("url", "").lower().find("ai") != -1
                    or page_info.get("url", "").lower().find("draw") != -1
                    or page_info.get("hasPrompt") == True
                )
                print(f"   是AI绘画页面: {is_ai_page}")

            except Exception as e:
                print(f"   解析页面信息失败: {e}")
        else:
            print(f"   获取页面信息失败: success={result.success}, output={repr(result.output)}")

    except Exception as e:
        print(f"   调用_open_painting_interface失败: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)

    if success:
        print("✅ 打开AI绘画界面成功")
        print("\n💡 下一步:")
        print("1. 测试输入提示词功能")
        print("2. 测试图像生成功能")
        print("3. 运行完整的Athena图像生成脚本")
    else:
        print("❌ 打开AI绘画界面失败")
        print("\n🔧 建议检查:")
        print("1. 豆包应用是否在前台运行")
        print("2. 豆包是否启用了JavaScript权限")
        print("3. 检查JavaScript代码中的return语句是否已修复")


def main():
    """主函数"""
    print("🎯 AI绘画界面打开测试")
    print("=" * 60)

    try:
        test_open_ai_interface()
        return 0
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
