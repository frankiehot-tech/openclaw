#!/usr/bin/env python3
"""测试验证逻辑"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import StrictPromptExtractor


def main():
    extractor = StrictPromptExtractor()

    # 测试文本
    test_texts = [
        "The caching layer gracefully falls back to database queries if Redis fails. Errors are logged but don't break the application. However, this means cache invalidation failures are silent - data may remain stale without any indication.",
        "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),",
        "A beautiful sunset over mountains, masterpiece, detailed, high quality, 8k, trending on artstation",
        "Portrait of a cyberpunk girl with neon hair, in the style of digital painting, by artist Greg Rutkowski",
    ]

    print("测试 _validate_prompt 方法:")
    for text in test_texts:
        result = extractor._validate_prompt(text)
        print(f"\n文本: {text[:80]}...")
        print(f"结果: {result}")

        # 检查是否包含排除词
        text_lower = text.lower()
        if "caching" in text_lower:
            print(f"包含'caching': 是")
        if "database" in text_lower:
            print(f"包含'database': 是")
        if "changelog" in text_lower:
            print(f"包含'changelog': 是")

    print("\n\n测试 _is_image_generation_prompt 方法:")
    for text in test_texts:
        result = extractor._is_image_generation_prompt(text)
        print(f"\n文本: {text[:80]}...")
        print(f"结果: {result}")


if __name__ == "__main__":
    main()
