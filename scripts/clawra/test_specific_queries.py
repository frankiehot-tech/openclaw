#!/usr/bin/env python3
"""测试更具体的搜索查询"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from code_search_prompts import (
    extract_prompts_from_json,
    get_file_content_from_item,
    search_code_files,
)
from final_prompt_collector import StrictPromptExtractor


def test_query_with_extraction(query: str):
    """测试查询并提取提示词"""
    print(f"\n=== 测试查询: '{query}' ===")

    files = search_code_files(query, per_page=5)
    print(f"找到 {len(files)} 个文件")

    extractor = StrictPromptExtractor()
    valid_prompts = []

    for i, file_item in enumerate(files):
        repo_name = file_item["repository"]["full_name"]
        file_name = file_item["name"]

        print(f"\n{i+1}. {repo_name} - {file_name}")

        content = get_file_content_from_item(file_item)
        if not content:
            print("  无法获取内容")
            continue

        print(f"  内容长度: {len(content)} 字符")

        # 根据文件类型提取
        file_ext = file_name.lower().split(".")[-1]

        if file_ext == "json":
            # 从JSON提取
            json_prompts = extract_prompts_from_json(content)
            print(f"  从JSON提取到 {len(json_prompts)} 个提示词")

            for prompt in json_prompts:
                if extractor._validate_prompt(prompt) and extractor._is_image_generation_prompt(
                    prompt
                ):
                    valid_prompts.append(
                        {"prompt": prompt, "source": repo_name, "file": file_name, "type": "json"}
                    )
                    print(f"    ✓ 有效提示词: {prompt[:60]}...")
        else:
            # 通用提取
            prompts = extractor.extract_prompts(content)
            print(f"  提取到 {len(prompts)} 个候选提示词")

            for prompt in prompts:
                if extractor._validate_prompt(prompt) and extractor._is_image_generation_prompt(
                    prompt
                ):
                    valid_prompts.append(
                        {"prompt": prompt, "source": repo_name, "file": file_name, "type": "text"}
                    )
                    print(f"    ✓ 有效提示词: {prompt[:60]}...")

        # 避免速率限制
        time.sleep(1)

    print(f"\n总计有效提示词: {len(valid_prompts)}")
    return valid_prompts


def main():
    """测试多个查询"""
    # 更具体的查询列表
    queries = [
        "stable diffusion prompt extension:json",
        "midjourney prompt extension:json",
        "dall-e prompt extension:json",
        "text-to-image prompt extension:json",
        "ai art prompt extension:json",
        "image generation prompt extension:json",
        "ai painting prompt extension:json",
    ]

    all_prompts = []

    for query in queries:
        prompts = test_query_with_extraction(query)
        all_prompts.extend(prompts)
        time.sleep(2)  # 查询间延迟

    print(f"\n=== 最终结果 ===")
    print(f"总计收集到 {len(all_prompts)} 个提示词")

    if all_prompts:
        # 保存结果
        output_file = "specific_queries_prompts.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_prompts, f, indent=2, ensure_ascii=False)

        print(f"提示词已保存到 {output_file}")

        # 显示示例
        print("\n前5个提示词:")
        for i, p in enumerate(all_prompts[:5]):
            print(f"{i+1}. {p['prompt'][:80]}...")
            print(f"   来源: {p['source']}, 文件: {p['file']}")


if __name__ == "__main__":
    main()
