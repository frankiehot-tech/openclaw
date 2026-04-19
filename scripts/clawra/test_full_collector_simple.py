#!/usr/bin/env python3
"""测试完整收集器（简化版）"""

import json
import logging
import os
import sys
from dataclasses import asdict

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import FinalGitHubPromptCollector


def test_full_collection():
    """测试完整收集过程"""
    print("=== 测试完整GitHub提示词收集器 ===")

    # 设置详细日志
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    collector = FinalGitHubPromptCollector()

    # 检查API限制
    try:
        response = requests.get("https://api.github.com/rate_limit", headers=collector.headers)
        if response.status_code == 200:
            limits = response.json()["resources"]["core"]
            print(f"API速率限制: {limits['remaining']}/{limits['limit']}")
    except Exception as e:
        print(f"速率限制检查失败: {e}")

    # 修改配置：只处理2个仓库，避免超时
    collector.max_repos = 2
    collector.max_files_per_repo = 10
    collector.timeout_seconds = 30

    print("\n开始收集提示词（最大2个仓库）...")
    prompts = collector.collect_prompts()

    print(f"\n收集完成，共提取 {len(prompts)} 个提示词")

    if prompts:
        print("\n前10个提示词:")
        for i, prompt in enumerate(prompts[:10]):
            print(f"  {i+1}. {prompt.prompt_text[:80]}...")
            print(f"     类别: {prompt.category}, 子类别: {prompt.subcategory}")
            print(f"     质量: {prompt.quality_score:.2f}, 来源: {prompt.source}")

        # 保存到文件
        output_file = "test_collected_prompts.json"
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
    import requests

    prompts = test_full_collection()
    if prompts:
        print(f"\n✅ 成功！收集到 {len(prompts)} 个高质量提示词")
        sys.exit(0)
    else:
        print(f"\n⚠️  未收集到提示词")
        sys.exit(1)
