#!/usr/bin/env python3
"""
测试改进后的豆包图像生成器
"""

import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from doubao_image_generator import DoubaoImageGenerator


def test_basic_generation():
    """测试基础图像生成"""
    print("=== 测试改进后的豆包图像生成器 ===")

    # 创建生成器
    generator = DoubaoImageGenerator(auto_start_app=True)

    # 测试一个简单的提示词
    test_prompt = "一只简单的红色猫，卡通风格"
    test_style = "cartoon"

    print(f"测试提示词: {test_prompt}")
    print(f"风格: {test_style}")

    # 生成图像（缩短等待时间进行测试）
    result = generator.generate_with_retry(
        prompt=test_prompt,
        style=test_style,
        size="512x512",  # 使用较小尺寸以加快生成
        quality="standard",
        num_images=1,
        wait_time=30,  # 缩短等待时间
        max_retries=1,  # 单次尝试
    )

    if result.success:
        print(f"✅ 生成成功!")
        print(f"   图像数量: {len(result.image_urls)}")
        print(f"   提示词: {result.prompt}")
        print(f"   风格: {result.style}")
        print(f"   生成时间: {result.timestamp}")

        # 显示图像URL
        for i, url in enumerate(result.image_urls[:3]):
            print(f"   图像{i+1}: {url[:100]}...")

        # 保存结果
        generator.save_result(result, "test_generated_images")
        return True
    else:
        print(f"❌ 生成失败: {result.error_message}")
        return False


def test_image_extraction():
    """单独测试图像提取功能"""
    print("\n=== 测试图像提取功能 ===")

    # 创建生成器但不初始化（假设页面已打开）
    generator = DoubaoImageGenerator(auto_start_app=False)

    # 手动初始化（假设豆包已运行）
    if not generator.initialize():
        print("❌ 初始化失败")
        return False

    print("✅ 生成器初始化完成")

    # 测试图像提取
    print("测试图像提取...")
    image_urls = generator._extract_generated_images()

    if image_urls:
        print(f"✅ 找到 {len(image_urls)} 张图像")
        for i, url in enumerate(image_urls[:3]):
            print(f"   图像{i+1}: {url[:100]}...")
    else:
        print("⚠️ 未找到图像")

    return len(image_urls) > 0


if __name__ == "__main__":
    print("改进版豆包图像生成器测试")
    print("=" * 50)

    # 首先测试图像提取功能（不生成新图像）
    print("先测试图像提取功能...")
    extraction_ok = test_image_extraction()

    if extraction_ok:
        print("\n✅ 图像提取功能正常")
    else:
        print("\n⚠️ 图像提取功能可能有问题，但继续测试生成")

    # 然后测试完整生成流程
    print("\n测试完整图像生成流程...")
    success = test_basic_generation()

    if success:
        print("\n✅ 测试成功!")
        sys.exit(0)
    else:
        print("\n❌ 测试失败")
        sys.exit(1)
