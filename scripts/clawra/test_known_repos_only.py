#!/usr/bin/env python3
"""测试仅从已知仓库收集"""

import json
import logging
import os
import sys
from dataclasses import asdict

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import FinalGitHubPromptCollector


def test_known_repos_only():
    """测试仅从已知仓库收集"""
    print("=== 测试已知仓库收集 ===")

    # 设置日志
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    collector = FinalGitHubPromptCollector()

    # 只处理前2个已知仓库，避免超时
    print(f"已知仓库总数: {len(collector.known_prompt_repos)}")
    print("处理前2个已知仓库...")

    # 直接调用collect_from_known_repos
    prompts = collector.collect_from_known_repos(max_repos=2)

    print(f"\n收集完成，共提取 {len(prompts)} 个提示词")

    if prompts:
        print("\n前10个提示词:")
        for i, prompt in enumerate(prompts[:10]):
            print(f"  {i+1}. {prompt.prompt_text[:80]}...")
            print(f"     类别: {prompt.category}, 子类别: {prompt.subcategory}")
            print(f"     质量: {prompt.quality_score:.2f}, 来源: {prompt.source}")

        # 保存到文件
        output_file = "known_repos_prompts.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in prompts], f, indent=2, ensure_ascii=False)

        print(f"\n提示词已保存到: {output_file}")

        # 统计信息
        categories = {}
        sources = {}
        for prompt in prompts:
            cat = prompt.category
            src = prompt.source
            categories[cat] = categories.get(cat, 0) + 1
            sources[src] = sources.get(src, 0) + 1

        print("\n类别统计:")
        for cat, count in categories.items():
            print(f"  {cat}: {count} 个")

        print("\n来源统计:")
        for src, count in sources.items():
            print(f"  {src}: {count} 个")

    return prompts


if __name__ == "__main__":
    prompts = test_known_repos_only()
    if prompts:
        print(f"\n✅ 成功！从已知仓库收集到 {len(prompts)} 个提示词")
        sys.exit(0)
    else:
        print(f"\n⚠️  未收集到提示词")
        sys.exit(1)
