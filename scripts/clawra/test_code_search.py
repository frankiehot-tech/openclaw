#!/usr/bin/env python3
"""测试GitHub代码搜索功能"""

import logging
import os
import sys

import requests

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import FinalGitHubPromptCollector


def test_code_search():
    """测试代码搜索"""
    print("=== 测试GitHub代码搜索 ===")

    collector = FinalGitHubPromptCollector()

    # 检查API限制
    try:
        response = requests.get("https://api.github.com/rate_limit", headers=collector.headers)
        if response.status_code == 200:
            limits = response.json()["resources"]["core"]
            print(f"API速率限制: {limits['remaining']}/{limits['limit']}")
    except Exception as e:
        print(f"速率限制检查失败: {e}")

    # 测试每个查询
    queries = [
        "prompt extension:json stable-diffusion",
        "prompt extension:json midjourney",
        "prompt extension:json dall-e",
        "masterpiece extension:txt",
        "high quality extension:txt",
        "detailed extension:txt",
        "stable diffusion prompts extension:md",
        "midjourney prompts extension:md",
        "text-to-image prompts",
        "ai art prompts",
        "generative art prompts",
    ]

    for query in queries:
        print(f"\n测试查询: {query}")
        try:
            url = f"{collector.base_url}/search/code"
            params = {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": 5,  # 只获取5个结果
            }

            response = requests.get(url, params=params, headers=collector.headers, timeout=30)
            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"  总结果数: {data.get('total_count', 0)}")

                if data.get("items"):
                    for i, item in enumerate(data["items"][:3]):
                        repo_name = item["repository"]["full_name"]
                        file_name = item["name"]
                        print(f"    {i+1}. {repo_name} - {file_name}")
            elif response.status_code == 422:
                print(f"  错误: 422 Unprocessable Entity")
                print(f"  响应: {response.text[:200]}")
            else:
                print(f"  错误: {response.status_code}")
                print(f"  响应: {response.text[:200]}")

        except Exception as e:
            print(f"  异常: {e}")


def test_search_code_for_prompts():
    """测试search_code_for_prompts方法"""
    print("\n=== 测试search_code_for_prompts方法 ===")

    collector = FinalGitHubPromptCollector()

    try:
        repos = collector.search_code_for_prompts()
        print(f"找到 {len(repos)} 个仓库")

        for i, repo in enumerate(repos[:10]):
            print(f"{i+1}. {repo.full_name}")
            print(f"   描述: {repo.description}")
            print(f"   Stars: {repo.stars}, 语言: {repo.language}")
            print(f"   主题: {repo.topics}")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_code_search()
    test_search_code_for_prompts()
