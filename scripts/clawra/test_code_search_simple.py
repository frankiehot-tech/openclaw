#!/usr/bin/env python3
"""简单测试代码搜索功能"""

import json
import os
import sys
import time

import requests

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import StrictPromptExtractor


def search_code_files(query: str, per_page: int = 5):
    """搜索代码文件"""
    url = "https://api.github.com/search/code"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ClawraPromptCollector/1.0",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    params = {"q": query, "sort": "updated", "order": "desc", "per_page": per_page}

    try:
        print(f"搜索查询: {query}")
        print(f"请求头: {headers}")
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"找到 {data.get('total_count', 0)} 个结果")
            items = data.get("items", [])
            print(f"返回 {len(items)} 个条目")
            return items
        else:
            print(f"错误响应: {response.text[:200]}")
            return []
    except Exception as e:
        print(f"异常: {e}")
        return []


def test_one_query():
    """测试单个查询"""
    query = "prompt extension:json"
    files = search_code_files(query, per_page=3)

    if not files:
        print("没有找到文件")
        return

    print(f"\n找到 {len(files)} 个文件:")
    for i, file_item in enumerate(files):
        repo_name = file_item["repository"]["full_name"]
        file_name = file_item["name"]
        print(f"{i+1}. {repo_name} - {file_name}")

        # 尝试获取内容
        from code_search_prompts import get_file_content_from_item

        content = get_file_content_from_item(file_item)
        if content:
            print(f"   内容长度: {len(content)} 字符")
            # 提取提示词
            extractor = StrictPromptExtractor()
            prompts = extractor.extract_prompts(content)
            print(f"   提取到 {len(prompts)} 个候选提示词")
            valid_prompts = []
            for prompt in prompts:
                if extractor._validate_prompt(prompt) and extractor._is_image_generation_prompt(
                    prompt
                ):
                    valid_prompts.append(prompt)
            print(f"   有效提示词: {len(valid_prompts)}")
            if valid_prompts:
                for p in valid_prompts[:2]:
                    print(f"     - {p[:60]}...")
        else:
            print(f"   无法获取内容")

        print()


if __name__ == "__main__":
    print("=== 测试代码搜索 ===")
    test_one_query()
