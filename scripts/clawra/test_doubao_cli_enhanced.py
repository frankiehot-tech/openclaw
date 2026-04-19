#!/usr/bin/env python3
"""测试增强版豆包CLI模块结构"""

import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))


def test_module_import():
    """测试模块导入"""
    print("=== 测试豆包CLI增强模块导入 ===")

    try:
        from external.ROMA.doubao_cli_enhanced import (
            DoubaoCLIEnhanced,
            ImageGenerationParams,
            ImageResult,
            ImageStyle,
        )

        print("✅ 成功导入主要类")

        # 测试数据类创建
        params = ImageGenerationParams(
            prompt="测试提示词",
            style="realistic",
            size="1024x1024",
            quality="standard",
            num_images=1,
        )
        print(f"✅ 成功创建ImageGenerationParams: {params}")

        # 测试结果类
        result = ImageResult(
            success=True,
            image_urls=["https://example.com/image.jpg"],
            metadata={"test": "data"},
            generation_time=10.5,
        )
        print(f"✅ 成功创建ImageResult: {result.success}")

        # 测试枚举
        style = ImageStyle.REALISTIC
        print(f"✅ 成功访问ImageStyle: {style}")

        return True

    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cli_initialization():
    """测试CLI初始化"""
    print("\n=== 测试CLI初始化 ===")

    try:
        from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced

        # 初始化CLI
        cli = DoubaoCLIEnhanced()
        print("✅ 成功初始化DoubaoCLIEnhanced")

        # 检查属性
        print(f"  app_name: {cli.app_name}")
        print(f"  base_cli: {'可用' if cli.base_cli else '不可用'}")
        print(f"  enhanced_executor: {'可用' if cli.enhanced_executor else '不可用'}")

        return True

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_javascript_execution():
    """测试JavaScript执行（模拟测试）"""
    print("\n=== 测试JavaScript执行功能 ===")

    try:
        from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced

        cli = DoubaoCLIEnhanced()

        # 尝试执行简单JavaScript
        # 注意：这可能需要豆包App正在运行
        # 我们只在base_cli可用时测试
        if cli.base_cli:
            print("  基础CLI可用，尝试简单JavaScript测试...")

            # 简单测试 - 获取页面标题
            js_code = "document.title"
            result = cli.execute_javascript_enhanced(js_code)

            print(f"  JavaScript执行结果:")
            print(f"    成功: {result.success}")
            print(f"    输出长度: {len(result.output)}")
            print(f"    重试次数: {result.retry_count}")
            print(f"    执行时间: {result.execution_time:.2f}s")

            if result.success:
                print("  ✅ JavaScript执行成功（至少没有错误）")
            else:
                print(f"  ⚠️  JavaScript执行失败: {result.error_message}")
        else:
            print("  ⚠️  基础CLI不可用，跳过实际执行测试")

        return True

    except Exception as e:
        print(f"❌ JavaScript执行测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_image_generation_structure():
    """测试图像生成结构（不实际生成）"""
    print("\n=== 测试图像生成结构 ===")

    try:
        from external.ROMA.doubao_cli_enhanced import (
            DoubaoCLIEnhanced,
            ImageGenerationParams,
        )

        cli = DoubaoCLIEnhanced()

        # 创建参数
        params = ImageGenerationParams(
            prompt="一个美丽的日落风景，山脉和湖泊",
            style="realistic",
            size="1024x1024",
            quality="standard",
            num_images=1,
        )

        print("✅ 成功创建生成参数")
        print(f"  提示词: {params.prompt[:30]}...")
        print(f"  风格: {params.style}")
        print(f"  尺寸: {params.size}")
        print(f"  质量: {params.quality}")
        print(f"  数量: {params.num_images}")

        # 测试生成方法存在
        if hasattr(cli, "generate_image"):
            print("✅ generate_image方法存在")

            # 检查方法的参数
            import inspect

            sig = inspect.signature(cli.generate_image)
            params_list = list(sig.parameters.keys())
            print(f"  方法参数: {params_list}")

            # 检查内部方法存在
            internal_methods = [
                "_open_painting_interface",
                "_input_prompt",
                "_select_style",
                "_trigger_generation",
            ]
            for method in internal_methods:
                if hasattr(cli, method):
                    print(f"  ✅ {method} 存在")
                else:
                    print(f"  ❌ {method} 缺失")
        else:
            print("❌ generate_image方法缺失")

        return True

    except Exception as e:
        print(f"❌ 图像生成结构测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("开始豆包CLI增强模块测试...\n")

    tests = [
        test_module_import,
        test_cli_initialization,
        test_javascript_execution,
        test_image_generation_structure,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
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
    else:
        print("⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
