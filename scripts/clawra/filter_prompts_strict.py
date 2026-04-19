#!/usr/bin/env python3
"""
严格过滤收集到的提示词
使用StrictPromptExtractor验证提示词质量，排除误报
"""

import json
import logging
import sys
from typing import Any, Dict, List

from test_strict_prompt_extraction import StrictPromptExtractor


def filter_prompts(input_file: str, output_file: str) -> None:
    """过滤提示词文件"""
    print(f"读取文件: {input_file}")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return

    print(f"原始提示词数量: {len(data)}")

    extractor = StrictPromptExtractor()
    filtered = []
    stats = {"total_processed": 0, "passed_validation": 0, "failed_validation": 0}

    for i, item in enumerate(data):
        stats["total_processed"] += 1
        if i % 100 == 0:
            print(f"处理中: {i}/{len(data)}")

        if not isinstance(item, dict) or "prompt_text" not in item:
            continue

        prompt_text = item["prompt_text"]

        # 使用严格提取器验证
        # 先检查是否是真正的提示词
        if not extractor._validate_prompt(prompt_text):
            stats["failed_validation"] += 1
            continue

        # 尝试提取（如果格式匹配）
        extracted = extractor.extract_strict_prompts(prompt_text)
        if not extracted:
            # 即使没有匹配格式，但验证通过，保留
            stats["passed_validation"] += 1
            filtered.append(item)
        else:
            # 如果提取出提示词，使用提取后的版本
            for extracted_text in extracted:
                new_item = item.copy()
                new_item["prompt_text"] = extracted_text
                new_item["verification_status"] = "strict_validated"
                filtered.append(new_item)
                stats["passed_validation"] += 1

    print(f"\n统计信息:")
    print(f"  总处理数: {stats['total_processed']}")
    print(f"  通过验证: {stats['passed_validation']}")
    print(f"  未通过验证: {stats['failed_validation']}")

    # 去重
    unique_prompts = {}
    for item in filtered:
        prompt_text = item["prompt_text"]
        if prompt_text not in unique_prompts:
            unique_prompts[prompt_text] = item

    filtered_unique = list(unique_prompts.values())
    print(f"  去重后: {len(filtered_unique)} 个提示词")

    # 保存结果
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(filtered_unique, f, indent=2, ensure_ascii=False)

    print(f"\n保存过滤后的提示词到: {output_file}")

    # 显示前10个过滤后的提示词
    if filtered_unique:
        print("\n前10个过滤后的提示词:")
        for i, item in enumerate(filtered_unique[:10]):
            prompt_text = item["prompt_text"]
            source = item.get("source", "unknown")
            print(f"  {i+1}. {prompt_text[:80]}...")
            print(f"     来源: {source}")


def main():
    """主函数"""
    input_file = "final_collected_prompts.json"
    output_file = "strict_filtered_prompts.json"

    print("=== 严格提示词过滤 ===")

    filter_prompts(input_file, output_file)

    # 额外：检查质量分布
    if output_file:
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            print(f"\n最终质量分析:")
            quality_scores = [item.get("quality_score", 0) for item in data]
            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)
                high_quality = len([s for s in quality_scores if s >= 0.7])
                print(f"  平均质量分数: {avg_quality:.2f}")
                print(f"  高质量提示词(≥0.7): {high_quality} 个")
        except Exception as e:
            print(f"质量分析失败: {e}")


if __name__ == "__main__":
    main()
