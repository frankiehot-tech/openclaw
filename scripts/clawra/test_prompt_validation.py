#!/usr/bin/env python3
"""测试提示词验证逻辑"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import StrictPromptExtractor


def test_prompts():
    """测试各种提示词"""
    extractor = StrictPromptExtractor()

    # 测试用例
    test_cases = [
        # 真正的图像生成提示词
        (
            "A beautiful sunset over mountains, masterpiece, detailed, high quality, 8k, trending on artstation",
            True,
        ),
        (
            "Portrait of a cyberpunk girl with neon hair, in the style of digital painting, by artist Greg Rutkowski",
            True,
        ),
        (
            "Fantasy landscape with dragons and castles, epic scene, cinematic lighting, unreal engine",
            True,
        ),
        ("Close-up of a cat's face, detailed fur, studio lighting, professional photography", True),
        (
            "Sci-fi cityscape at night, cyberpunk aesthetic, rain, neon lights, by artist Simon Stålenhag",
            True,
        ),
        # 非提示词文本
        ("Open images directory", False),
        ("Prompts from file or textbox", False),
        ("Navigate image viewer with gamepad", False),
        ("do not add watermark to images", False),
        ("Processing complete, redirecting", False),
        ("should throw error for empty title", False),
        ("Continue with Google", False),
        ("A beautiful mountain landscape", False),  # 缺少质量关键词和逗号
        ("^18.17.0 || ^20.3.0 || >=21.0.0", False),
        ("Apache-2.0 AND LGPL-3.0-or-later", False),
        ("The development environment is currently very similar to the one in production", False),
        ("best [tool] for solo founders", False),
    ]

    print("=== 测试提示词验证逻辑 ===\n")

    passed = 0
    failed = 0

    for prompt_text, expected_result in test_cases:
        # 使用_validate_prompt方法（它会调用_is_image_generation_prompt）
        result = extractor._validate_prompt(prompt_text)

        status = "✓" if result == expected_result else "✗"
        if result == expected_result:
            passed += 1
        else:
            failed += 1

        print(f"{status} 预期: {expected_result}, 实际: {result}")
        print(f"  文本: {prompt_text[:80]}...")
        if result != expected_result:
            print(f"  错误: 预期 {expected_result} 但得到 {result}")
        print()

    print(f"\n结果: {passed} 通过, {failed} 失败")

    # 特别测试_is_image_generation_prompt方法
    print("\n=== 单独测试 _is_image_generation_prompt 方法 ===\n")

    # 访问这个方法（如果存在）
    if hasattr(extractor, "_is_image_generation_prompt"):
        for prompt_text, expected_result in test_cases[:5]:  # 只测试前5个
            result = extractor._is_image_generation_prompt(prompt_text)
            print(
                f"{'✓' if result == expected_result else '✗'} _is_image_generation_prompt: {result}"
            )
            print(f"  文本: {prompt_text[:80]}...")
    else:
        print("警告: extractor没有_is_image_generation_prompt方法")


if __name__ == "__main__":
    test_prompts()
