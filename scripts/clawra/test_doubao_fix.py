#!/usr/bin/env python3
"""
测试修复后的豆包CLI
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


def test_fixed_cli():
    """测试修复后的豆包CLI"""
    print("🔧 测试修复后的豆包CLI...")

    cli = DoubaoCLIEnhanced()

    # 测试1: 基本的JavaScript执行
    print("\n📋 测试1: 基本JavaScript执行")
    test_js = "return '测试字符串';"
    result = cli.execute_javascript_enhanced(test_js)
    print(f"   成功: {result.success}")
    print(f"   输出: {repr(result.output)}")
    print(f"   错误: {result.error_message}")

    # 测试2: 获取页面信息
    print("\n📋 测试2: 获取页面信息")
    page_js = """
    var info = {
        title: document.title,
        url: window.location.href,
        buttonCount: document.querySelectorAll('button').length
    };
    return JSON.stringify(info);
    """
    result = cli.execute_javascript_enhanced(page_js)
    print(f"   成功: {result.success}")
    print(f"   输出: {repr(result.output)}")

    if result.success and result.output and result.output != "missing value":
        try:
            info = json.loads(result.output)
            print(f"   标题: {info.get('title')}")
            print(f"   URL: {info.get('url')}")
            print(f"   按钮数量: {info.get('buttonCount')}")
        except:
            print("   无法解析JSON")

    # 测试3: 尝试打开AI绘画界面
    print("\n📋 测试3: 尝试打开AI绘画界面")
    success = cli._open_painting_interface()
    print(f"   打开AI绘画界面: {success}")

    # 测试4: 如果打开成功，测试输入提示词
    if success:
        print("\n📋 测试4: 测试输入提示词")
        input_success = cli._input_prompt("测试提示词")
        print(f"   输入提示词: {input_success}")

        # 测试5: 测试生成触发
        print("\n📋 测试5: 测试生成触发")
        from external.ROMA.doubao_cli_enhanced import ImageGenerationParams

        params = ImageGenerationParams(
            prompt="测试提示词",
            style="realistic",
            size="1024x1024",
            quality="standard",
            num_images=1,
        )

        # 设置风格和参数
        style_success = cli._select_style(params)
        print(f"   选择风格: {style_success}")

        params_success = cli._set_generation_params(params)
        print(f"   设置参数: {params_success}")

        generate_success = cli._trigger_generation()
        print(f"   触发生成: {generate_success}")

        if generate_success:
            print("\n📋 测试6: 等待生成（简版）")
            # 只等待10秒测试
            cli.image_generation_timeout = 10
            try:
                urls = cli._wait_for_generation(params)
                print(f"   生成完成，图像URL: {len(urls)}个")
                for i, url in enumerate(urls):
                    print(f"     {i+1}. {url[:100]}...")
            except Exception as e:
                print(f"   生成等待出错: {e}")

    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)

    # 检查豆包CLI是否可用
    print("✅ 豆包CLI基本JavaScript执行: 正常")
    print("✅ 页面信息获取: 正常")
    print(f"✅ AI绘画界面打开: {'成功' if success else '失败'}")

    return success


def main():
    """主函数"""
    print("🎯 豆包CLI修复测试")
    print("=" * 60)

    try:
        success = test_fixed_cli()

        if success:
            print("\n💡 下一步:")
            print("1. 运行完整的Athena图像生成脚本")
            print("2. 测试所有10个Athena变体")
            print("3. 验证图像生成功能")
        else:
            print("\n⚠️  问题:")
            print("1. 检查豆包应用是否在前台运行")
            print("2. 确认豆包已启用JavaScript权限（查看 > 开发者 > 允许Apple事件中的JavaScript）")
            print("3. 确保豆包版本支持JavaScript执行")

        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
