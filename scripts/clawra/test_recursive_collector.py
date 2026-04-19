#!/usr/bin/env python3
"""测试递归收集器"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import FinalGitHubPromptCollector, FinalGitHubRepo


def test_recursive_processing():
    """测试递归处理"""
    collector = FinalGitHubPromptCollector()

    # 创建仓库对象
    repo = FinalGitHubRepo(
        full_name="mehakjain07/stable-diffusion-prompts-collection",
        description="Curated, categorized high-quality Stable Diffusion, Midjourney, DALL·E, Flux prompts.",
        stars=100,
        language="Markdown",
        topics=["prompts", "stable-diffusion", "midjourney", "dall-e", "flux", "ai-art"],
        updated_at="2024-01-01T00:00:00Z",
        fork=False,
        size=1000,
    )

    print(f"测试仓库: {repo.full_name}")
    print(f"描述: {repo.description}")

    print("\n开始处理仓库（递归）...")

    # 处理仓库
    prompts = collector.process_repository(repo)

    print(f"\n提取到 {len(prompts)} 个提示词")

    if prompts:
        print("\n前5个提示词:")
        for i, prompt in enumerate(prompts[:5]):
            print(f"{i+1}. {prompt.prompt_text[:80]}...")
            print(f"   类别: {prompt.category}, 子类别: {prompt.subcategory}")
            print(f"   质量: {prompt.quality_score:.2f}")
    else:
        print("未提取到提示词")

    return prompts


if __name__ == "__main__":
    test_recursive_processing()
