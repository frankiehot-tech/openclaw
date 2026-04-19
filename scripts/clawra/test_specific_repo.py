#!/usr/bin/env python3
"""测试特定仓库"""

import json
import logging
import os
import sys
from dataclasses import asdict

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import FinalGitHubPromptCollector, FinalGitHubRepo


def test_specific_repo():
    """测试特定仓库"""
    print("=== 测试特定仓库 ===")

    # 设置日志
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    collector = FinalGitHubPromptCollector()

    # 创建仓库对象
    repo = FinalGitHubRepo(
        full_name="Avaray/stable-diffusion-simple-wildcards",
        description="Simple collection of wildcards for Stable Diffusion WebUI",
        stars=100,
        language="Text",
        topics=["stable-diffusion", "wildcards", "ai-art"],
        updated_at="2023-01-01T00:00:00Z",
        fork=False,
        size=1000,
    )

    print(f"测试仓库: {repo.full_name}")
    print(f"描述: {repo.description}")

    print("\n开始处理仓库...")
    prompts = collector.process_repository(repo)

    print(f"\n提取到 {len(prompts)} 个提示词")

    if prompts:
        print("\n前10个提示词:")
        for i, prompt in enumerate(prompts[:10]):
            print(f"  {i+1}. {prompt.prompt_text[:80]}...")
            print(f"     类别: {prompt.category}, 子类别: {prompt.subcategory}")
            print(f"     质量: {prompt.quality_score:.2f}")

        # 保存到文件
        output_file = "specific_repo_prompts.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in prompts], f, indent=2, ensure_ascii=False)

        print(f"\n提示词已保存到: {output_file}")

        # 统计信息
        categories = {}
        for prompt in prompts:
            cat = prompt.category
            categories[cat] = categories.get(cat, 0) + 1

        print("\n类别统计:")
        for cat, count in categories.items():
            print(f"  {cat}: {count} 个")

    return prompts


if __name__ == "__main__":
    prompts = test_specific_repo()
    if prompts:
        print(f"\n✅ 成功！从 {len(prompts)} 个提示词")
        sys.exit(0)
    else:
        print(f"\n⚠️  未收集到提示词")
        sys.exit(1)
