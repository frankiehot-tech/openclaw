#!/usr/bin/env python3
"""测试增强的收集器（已知仓库 + 搜索）"""

import json
import logging
import os
import sys
from dataclasses import asdict

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import FinalGitHubPromptCollector


def test_enhanced_collection():
    """测试增强收集过程"""
    print("=== 增强版GitHub提示词收集器 ===")

    # 设置详细日志
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    collector = FinalGitHubPromptCollector()

    # 修改配置
    collector.max_repos = 3  # 搜索最多3个仓库
    collector.max_files_per_repo = 30
    collector.timeout_seconds = 45  # 增加超时时间

    print(f"已知仓库数量: {len(collector.known_prompt_repos)}")
    print("配置: 最多处理3个搜索仓库，每个仓库最多30个文件")

    # 检查API限制
    try:
        import requests

        response = requests.get("https://api.github.com/rate_limit", headers=collector.headers)
        if response.status_code == 200:
            limits = response.json()["resources"]["core"]
            print(f"API速率限制: {limits['remaining']}/{limits['limit']}")
    except Exception as e:
        print(f"速率限制检查失败: {e}")

    print("\n开始收集提示词...")
    prompts = collector.collect_prompts()

    print(f"\n收集完成，共提取 {len(prompts)} 个提示词")

    if prompts:
        print("\n前10个提示词:")
        for i, prompt in enumerate(prompts[:10]):
            print(f"  {i+1}. {prompt.prompt_text[:80]}...")
            print(f"     类别: {prompt.category}, 子类别: {prompt.subcategory}")
            print(f"     质量: {prompt.quality_score:.2f}, 来源: {prompt.source}")

        # 保存到文件
        output_file = "enhanced_collected_prompts.json"
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

        # 质量分析
        quality_scores = [p.quality_score for p in prompts]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        high_quality = len([q for q in quality_scores if q >= 0.8])
        print(f"\n质量分析:")
        print(f"  平均质量: {avg_quality:.2f}")
        print(f"  高质量提示词 (≥0.8): {high_quality} 个 ({high_quality/len(prompts)*100:.1f}%)")

    return prompts


if __name__ == "__main__":
    prompts = test_enhanced_collection()
    if prompts:
        print(f"\n✅ 成功！收集到 {len(prompts)} 个高质量提示词")
        sys.exit(0)
    else:
        print(f"\n⚠️  未收集到提示词")
        sys.exit(1)
