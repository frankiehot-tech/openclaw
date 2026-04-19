#!/usr/bin/env python3
"""
测试豆包图像生成器与Clawra生产系统的集成
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from clawra_production_system import (
    ClawraProductionSystem,
    ProductionSystemConfig,
    ProductionSystemMode,
)


def test_doubao_image_generator_integration():
    """测试豆包图像生成器集成"""
    print("=== 豆包图像生成器集成测试 ===")

    # 创建配置 - 启用豆包CLI但禁用其他组件以加快测试
    config = ProductionSystemConfig(
        mode=ProductionSystemMode.VALIDATION,
        enable_roma_maref=False,  # 禁用ROMO-MAREF以加快测试
        enable_kdenlive=False,  # 禁用Kdenlive
        enable_doubao_cli=True,  # 启用豆包CLI
        enable_github_workflow=False,
        quality_preset="standard",
        log_level="INFO",
    )

    print(f"配置创建完成: 豆包CLI启用={config.enable_doubao_cli}")

    # 创建生产系统
    print("\n初始化生产系统...")
    production_system = ClawraProductionSystem(config)

    # 检查系统状态
    status = production_system.get_system_status()
    print(f"系统状态:")
    print(f"  模式: {status['system']['mode']}")
    print(f"  组件状态:")

    components = status.get("components", {})
    # 组件状态是简单的布尔值字典
    doubao_cli_available = components.get("doubao_cli", False)
    doubao_image_generator_available = components.get("doubao_image_generator", False)

    print(f"   豆包CLI: {'✅ 可用' if doubao_cli_available else '❌ 不可用'}")
    print(f"   豆包图像生成器: {'✅ 可用' if doubao_image_generator_available else '❌ 不可用'}")

    if not doubao_image_generator_available:
        print("\n❌ 豆包图像生成器不可用，测试终止")
        return False

    print("\n🎯 测试图像生成功能...")

    # 测试1: 使用text_to_image内容类型生成图像
    print("\n1. 测试text_to_image内容类型...")
    test_prompt = "一只可爱的卡通猫，蓝色眼睛，简单背景"

    success, result = production_system.generate_content_with_doubao(
        topic=test_prompt,
        content_type="text_to_image",
        target_audience="通用",
        tone="可爱卡通风格",
        image_style="cartoon",
        image_size="1024x1024",
        num_images=1,
    )

    if success:
        print(f"✅ 图像生成成功!")
        print(f"   生成图像数量: {len(result.get('generated_images', []))}")
        print(f"   图像URL: {result.get('generated_images', [])[:1]}...")

        # 保存结果 - 确保datetime对象转换为字符串
        def make_serializable(obj):
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            elif isinstance(obj, tuple):
                return tuple(make_serializable(item) for item in obj)
            elif hasattr(obj, "isoformat"):  # datetime对象
                return obj.isoformat()
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                try:
                    return str(obj)
                except:
                    return f"<non-serializable: {type(obj).__name__}>"

        serializable_result = make_serializable(result)
        output_file = f"test_image_generation_{int(time.time())}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(serializable_result, f, ensure_ascii=False, indent=2)
        print(f"   结果已保存到: {output_file}")

        # 测试2: 验证生成的元数据
        print("\n2. 验证生成结果元数据...")
        required_fields = ["success", "prompt", "style", "size", "generated_images", "timestamp"]
        missing_fields = [field for field in required_fields if field not in result]

        if not missing_fields:
            print("✅ 所有必需字段都存在")
        else:
            print(f"❌ 缺少字段: {missing_fields}")

        return True
    else:
        print(f"❌ 图像生成失败: {result.get('error', '未知错误')}")

        # 测试3: 测试文本生成（确保原有功能仍然工作）
        print("\n3. 测试文本内容生成（原有功能）...")
        text_success, text_result = production_system.generate_content_with_doubao(
            topic="Python编程简介",
            content_type="blog_post",
            target_audience="开发者",
            tone="专业且易懂",
        )

        if text_success:
            print("✅ 文本生成功能仍然工作")
            return False  # 图像生成失败，但文本生成成功
        else:
            print("❌ 文本生成也失败")
            return False


def main():
    """主函数"""
    print("豆包图像生成器集成测试")
    print("=" * 60)

    try:
        test_passed = test_doubao_image_generator_integration()

        print("\n" + "=" * 60)
        print("测试结果")
        print("=" * 60)

        if test_passed:
            print("✅ 豆包图像生成器集成测试通过!")
            print("\n🎯 下一步:")
            print("1. 检查生成的图像文件")
            print("2. 在生产系统中运行完整测试")
            print("3. 扩展更多图像风格和参数支持")
        else:
            print("❌ 豆包图像生成器集成测试失败")
            print("\n🔧 故障排除:")
            print("1. 检查豆包应用是否安装并运行")
            print("2. 验证豆包CLI控制是否工作")
            print("3. 检查网络连接")
            print("4. 查看错误日志以获取详细信息")

        return test_passed

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
