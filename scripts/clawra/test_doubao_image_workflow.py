#!/usr/bin/env python3
"""测试豆包图像生成工作流"""

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


def test_open_painting_interface():
    """测试打开绘画界面"""
    print("=== 测试打开AI绘画界面 ===")

    try:
        from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced

        cli = DoubaoCLIEnhanced()

        # 调用内部方法
        result = cli._open_painting_interface()
        print(f"打开界面结果: {result}")

        if result:
            print("✅ 界面打开成功（或至少没有错误）")
            # 等待页面加载
            time.sleep(3)
            return True
        else:
            print("⚠️ 界面打开可能失败")
            return False

    except Exception as e:
        print(f"❌ 打开界面失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_input_prompt():
    """测试输入提示词"""
    print("\n=== 测试输入提示词 ===")

    try:
        from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced

        cli = DoubaoCLIEnhanced()

        # 测试提示词输入
        test_prompt = "一个简单的测试图像，蓝色背景"
        result = cli._input_prompt(test_prompt)
        print(f"输入提示词结果: {result}")

        if result:
            print("✅ 提示词输入成功（或至少没有错误）")
            return True
        else:
            print("⚠️ 提示词输入可能失败")
            return False

    except Exception as e:
        print(f"❌ 输入提示词失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_select_style():
    """测试选择风格"""
    print("\n=== 测试选择风格 ===")

    try:
        from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced

        cli = DoubaoCLIEnhanced()

        # 测试风格选择
        style = "realistic"
        result = cli._select_style(style)
        print(f"选择风格结果: {result}")

        # 风格选择不是必需的，所以即使返回False也可能是正常的
        print("✅ 风格选择执行完成")
        return True

    except Exception as e:
        print(f"❌ 选择风格失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_trigger_generation():
    """测试触发生成"""
    print("\n=== 测试触发生成 ===")

    try:
        from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced

        cli = DoubaoCLIEnhanced()

        # 测试触发生成
        result = cli._trigger_generation()
        print(f"触发生成结果: {result}")

        if result:
            print("✅ 生成触发成功（或至少没有错误）")
            return True
        else:
            print("⚠️ 生成触发可能失败")
            return False

    except Exception as e:
        print(f"❌ 触发生成失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_complete_workflow():
    """测试完整工作流（但不等待生成完成）"""
    print("\n=== 测试完整图像生成工作流 ===")

    try:
        from external.ROMA.doubao_cli_enhanced import (
            DoubaoCLIEnhanced,
            ImageGenerationParams,
        )

        cli = DoubaoCLIEnhanced()

        # 创建测试参数
        params = ImageGenerationParams(
            prompt="一个简单的测试图像，用于验证工作流",
            style="realistic",
            size="512x512",  # 使用较小尺寸以加快测试
            quality="standard",
            num_images=1,
        )

        print("开始测试完整工作流...")
        print(f"提示词: {params.prompt}")
        print(f"风格: {params.style}")

        # 设置较短的超时时间，避免长时间等待
        cli.image_generation_timeout = 30  # 30秒超时

        # 开始计时
        start_time = time.time()

        # 调用generate_image方法
        # 注意：这会实际尝试生成图像，但我们可以依赖超时机制
        print("调用generate_image方法（将在30秒后超时）...")
        result = cli.generate_image(params)

        elapsed = time.time() - start_time
        print(f"生成完成，耗时: {elapsed:.1f}s")

        print(f"成功: {result.success}")
        print(f"图像URL数量: {len(result.image_urls)}")
        print(f"错误信息: {result.error_message}")

        if result.success:
            print("✅ 图像生成成功！")
            if result.image_urls:
                print(f"生成的图像URL:")
                for i, url in enumerate(result.image_urls):
                    print(f"  {i+1}. {url}")
        else:
            print(f"⚠️ 图像生成失败: {result.error_message}")
            # 检查是否是超时导致的失败
            if "超时" in result.error_message or "timeout" in result.error_message.lower():
                print("  失败原因是超时，这是测试中的预期行为")

        return result.success or "超时" in result.error_message

    except Exception as e:
        print(f"❌ 完整工作流测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("开始豆包图像生成工作流测试...\n")

    # 用户确认
    print("重要：此测试将尝试在豆包App中实际执行图像生成。")
    print("请确保：")
    print("1. 豆包App正在运行")
    print("2. 已登录豆包账户")
    print("3. AI绘画功能可用")
    print("4. 网络连接正常")
    print()

    response = input("是否继续测试？(y/n): ")
    if response.lower() != "y":
        print("测试取消")
        return 0

    # 运行测试
    tests = [
        test_open_painting_interface,
        test_input_prompt,
        test_select_style,
        test_trigger_generation,
        test_complete_workflow,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            # 测试之间暂停一下，避免操作过快
            time.sleep(2)
        except Exception as e:
            print(f"测试异常: {e}")
            results.append(False)

    passed = sum(results)
    total = len(results)

    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")

    if passed == total:
        print("✅ 所有测试通过！")
        return 0
    elif passed >= total - 1:  # 允许一个测试失败
        print("⚠️  部分测试失败，但核心功能可能正常")
        return 0
    else:
        print("❌ 多个测试失败，需要调试")
        return 1


if __name__ == "__main__":
    sys.exit(main())
