#!/usr/bin/env python3
"""
测试修改后的GitHub提示词收集器
"""

import logging
import os
import sys
from dataclasses import asdict

sys.path.append(os.path.dirname(__file__))

# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,  # 改为DEBUG级别
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from github_prompt_collector import GitHubPromptCollector


def test_search_and_collect():
    """测试搜索和收集"""
    print("=== 测试修改后的GitHub提示词收集器 ===")

    collector = GitHubPromptCollector()

    # 测试API速率限制
    import requests

    response = requests.get("https://api.github.com/rate_limit", headers=collector.headers)
    if response.status_code == 200:
        limits = response.json()["resources"]["core"]
        print(f"API速率限制: {limits['remaining']}/{limits['limit']}")

    # 搜索提示词仓库 - 使用更具体的搜索词
    keywords = ["prompt collection", "prompt library", "stable diffusion prompts"]
    all_repos = []

    for keyword in keywords[:2]:  # 测试前2个关键词
        print(f"\n搜索关键词: '{keyword}'")
        repos = collector.search_repositories(keyword, per_page=5)
        print(f"找到 {len(repos)} 个仓库")

        if repos:
            for i, repo in enumerate(repos[:3]):
                print(
                    f"  {i+1}. {repo.full_name} - {repo.description[:80] if repo.description else '无描述'}"
                )
                print(f"     Stars: {repo.stars}, 语言: {repo.language}")
                all_repos.append(repo)

    if not all_repos:
        print("❌ 未找到仓库")
        return

    # 处理第一个仓库
    test_repo = all_repos[0]
    print(f"\n=== 测试处理仓库: {test_repo.full_name} ===")

    # 启用收集器的调试模式（如果支持）
    # 处理仓库，限制文件数
    prompts = collector.process_repository(test_repo, max_files=30, timeout_seconds=60)

    print(f"\n提取到 {len(prompts)} 个提示词")

    if prompts:
        print("\n前10个提示词:")
        for i, prompt in enumerate(prompts[:10]):
            print(f"  {i+1}. {prompt.prompt_text[:80]}...")
            print(f"     类别: {prompt.category}, 子类别: {prompt.subcategory}")
            print(f"     质量分: {prompt.quality_score:.2f}")

        # 保存到文件
        output_file = "test_collected_prompts.json"
        import json
        from datetime import datetime

        def make_serializable(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                [asdict(p) for p in prompts],
                f,
                default=make_serializable,
                indent=2,
                ensure_ascii=False,
            )

        print(f"\n提示词已保存到: {output_file}")
    else:
        print("❌ 未提取到任何提示词")
        print("可能原因:")
        print("  1. 仓库不包含标准格式的提示词")
        print("  2. 文件类型不被支持")
        print("  3. 提取逻辑仍然过于严格")

    return prompts


def test_extraction_logic():
    """直接测试提取逻辑"""
    print("\n=== 测试提取逻辑 ===")

    collector = GitHubPromptCollector()

    # 测试用例
    test_cases = [
        ("prompt: A beautiful landscape with mountains", True, "prompt:前缀"),
        ('"prompt": "A cute cat"', True, "JSON格式"),
        ("text: Portrait of a person", True, "text:前缀"),
        ("A simple cat", False, "过短且无关键词"),
        (
            "A majestic eagle soaring in the sky, detailed feathers, 4k resolution",
            True,
            "描述性提示词",
        ),
        ("def generate_image():", False, "代码"),
        ("Installation: pip install package", False, "安装说明"),
        ("not ie <= 11", False, "browserslist"),
        ('{"model": "stable-diffusion"}', False, "JSON配置"),
        (
            "close-up of a beautiful flower, macro photography, detailed petals",
            True,
            "close-up开头",
        ),
    ]

    source_info = {"repo": "test", "url": "https://github.com/test", "description": "test"}

    for text, expected, description in test_cases:
        prompts = collector.extract_prompts_from_text(text, source_info)
        extracted = len(prompts) > 0
        status = "✅" if extracted == expected else "❌"
        print(f"{status} {description}: '{text[:40]}...' -> 提取: {extracted}, 预期: {expected}")


def main():
    """主函数"""
    print("GitHub提示词收集器V2测试")
    print("=" * 60)

    # 测试提取逻辑
    test_extraction_logic()

    # 测试实际收集
    prompts = test_search_and_collect()

    print("\n" + "=" * 60)
    if prompts:
        print(f"✅ 测试成功！收集到 {len(prompts)} 个提示词")
        return True
    else:
        print("⚠️  测试完成，但未收集到提示词")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
