#!/usr/bin/env python3
"""
简单检查页面状态
"""

import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def simple_page_check():
    """简单检查页面状态"""
    print("🔧 简单检查页面状态...")

    cli = DoubaoCLIEnhanced()

    # 简单获取页面信息
    simple_js = """
    // 简单页面信息获取
    var pageInfo = {
        title: document.title,
        url: window.location.href,
        path: window.location.pathname,
        buttons: document.querySelectorAll('button').length,
        textareas: document.querySelectorAll('textarea').length,
        hasAIKeywords: (function() {
            var text = document.body.innerText || '';
            return text.includes('AI') || text.includes('绘画') || text.includes('Draw');
        })()
    };

    JSON.stringify(pageInfo);
    """

    result = cli.execute_javascript_enhanced(simple_js)
    print(f"执行结果: success={result.success}, output={repr(result.output)}")

    if result.success and result.output and result.output != "missing value":
        try:
            page_info = json.loads(cli._clean_js_output(result.output))
            print(f"\n📋 页面信息:")
            print(f"   标题: {page_info.get('title')}")
            print(f"   URL: {page_info.get('url')}")
            print(f"   路径: {page_info.get('path')}")
            print(f"   按钮数量: {page_info.get('buttons')}")
            print(f"   文本区域数量: {page_info.get('textareas')}")
            print(f"   有AI关键词: {page_info.get('hasAIKeywords')}")
            return page_info
        except Exception as e:
            print(f"解析页面信息失败: {e}")
            return None
    else:
        print(f"获取页面信息失败")
        return None


def main():
    """主函数"""
    print("🎯 简单页面状态检查")
    print("=" * 60)

    try:
        page_info = simple_page_check()

        print("\n" + "=" * 60)
        print("📊 检查总结")
        print("=" * 60)

        if page_info:
            path = page_info.get("path", "")
            title = page_info.get("title", "")

            # 检查是否是AI绘画页面
            is_ai_page = (
                "ai" in path.lower()
                or "draw" in path.lower()
                or "paint" in path.lower()
                or "ai" in title.lower()
                or "绘画" in title
                or "draw" in title.lower()
                or page_info.get("hasAIKeywords") == True
            )

            print(f"当前页面路径: {path}")
            print(f"当前页面标题: {title}")
            print(f"是AI绘画页面: {is_ai_page}")

            if not is_ai_page:
                print("\n🔧 建议:")
                print("1. 尝试导航到其他URL，如 /ai/draw, /painting, /draw")
                print("2. 尝试在聊天中输入'AI绘画'或'画画'来打开AI绘画功能")
                print("3. 检查豆包侧边栏是否有AI绘画入口")
        else:
            print("无法获取页面信息")

        return 0 if page_info else 1

    except Exception as e:
        print(f"\n❌ 检查出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
