#!/usr/bin/env python3
"""
测试不同的导航URL
"""

import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def test_navigation_urls():
    """测试不同的导航URL"""
    print("🔧 测试不同的导航URL...")

    cli = DoubaoCLIEnhanced()

    # 测试不同的URL路径
    test_urls = [
        "/ai/painting",
        "/ai/draw",
        "/draw",
        "/painting",
        "/ai/create",
        "/create",
        "/ai/paint",
        "/ai/art",
        "/ai/generate",
        "/generate",
        "/ai/img",
        "/img",
    ]

    results = []
    for url in test_urls:
        print(f"\n📋 测试导航到: {url}")

        # 创建JavaScript代码导航到该URL
        nav_js = f"""
        try {{
            console.log('尝试导航到: {url}');
            window.location.href = '{url}';
            "导航到{url}";
        }} catch (e) {{
            "导航出错: " + e.toString();
        }}
        """

        result = cli.execute_javascript_enhanced(nav_js)
        success = result.success and result.output and result.output != "missing value"

        print(f"   成功: {success}")
        print(f"   输出: {repr(result.output)}")

        # 等待2秒让页面加载
        import time

        time.sleep(2)

        # 检查当前页面状态
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
                print(
                    f"   当前页面: 标题='{page_info.get('title')}', 路径='{page_info.get('path')}'"
                )

                # 检查是否是绘画页面（简化检查）
                is_painting_page = (
                    page_info.get("title", "").lower().find("绘画") != -1
                    or page_info.get("title", "").lower().find("draw") != -1
                    or page_info.get("title", "").lower().find("paint") != -1
                    or page_info.get("path", "").find("painting") != -1
                    or page_info.get("path", "").find("draw") != -1
                )
                print(f"   是绘画页面: {is_painting_page}")

                results.append(
                    {
                        "url": url,
                        "success": success,
                        "output": result.output,
                        "final_path": page_info.get("path"),
                        "final_title": page_info.get("title"),
                        "is_painting_page": is_painting_page,
                    }
                )
            except Exception as e:
                print(f"   解析页面信息失败: {e}")
                results.append(
                    {
                        "url": url,
                        "success": success,
                        "output": result.output,
                        "error": str(e),
                        "is_painting_page": False,
                    }
                )
        else:
            print(f"   检查页面状态失败")
            results.append(
                {
                    "url": url,
                    "success": success,
                    "output": result.output,
                    "error": "check_failed",
                    "is_painting_page": False,
                }
            )

    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)

    successful_navs = [r for r in results if r.get("success")]
    painting_pages = [r for r in results if r.get("is_painting_page")]

    print(f"总测试URL数: {len(test_urls)}")
    print(f"成功导航: {len(successful_navs)}")
    print(f"找到绘画页面: {len(painting_pages)}")

    if painting_pages:
        print("\n✅ 找到的有效绘画页面URL:")
        for result in painting_pages:
            print(
                f"  - {result['url']} (路径: {result.get('final_path', 'N/A')}, 标题: {result.get('final_title', 'N/A')})"
            )
    else:
        print("\n❌ 未找到有效的绘画页面URL")
        print("\n💡 建议:")
        print("1. 可能需要手动在豆包中找到AI绘画功能")
        print("2. 尝试使用不同的关键词搜索")
        print("3. 检查豆包版本是否支持AI绘画")

    return painting_pages


def main():
    """主函数"""
    print("🎯 导航URL测试")
    print("=" * 60)

    try:
        painting_pages = test_navigation_urls()

        if painting_pages:
            print("\n✅ 测试成功，找到了有效的绘画页面URL")
            print("\n💡 下一步:")
            print("1. 更新_open_painting_interface方法使用找到的URL")
            print("2. 修复JavaScript代码中的return语句")
            print("3. 测试完整的图像生成流程")
        else:
            print("\n❌ 测试失败，未找到有效的绘画页面URL")
            print("\n🔧 可能的解决方案:")
            print("1. 需要手动探索豆包界面找到AI绘画入口")
            print("2. 可能需要登录或特定权限")
            print("3. 豆包版本可能不支持AI绘画功能")

        return 0 if painting_pages else 1

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
