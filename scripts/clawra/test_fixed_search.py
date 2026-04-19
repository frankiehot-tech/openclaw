#!/usr/bin/env python3
"""测试修复后的代码搜索"""

import os
import sys

import requests

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import FinalGitHubPromptCollector


def test_headers():
    collector = FinalGitHubPromptCollector()
    print("Headers:", collector.headers)

    # 测试速率限制
    resp = requests.get("https://api.github.com/rate_limit", headers=collector.headers)
    print("Rate limit:", resp.status_code)
    if resp.status_code == 200:
        limits = resp.json()["resources"]["core"]
        print(f"Limit: {limits['remaining']}/{limits['limit']}")

    # 测试一个简单的代码搜索
    url = "https://api.github.com/search/code"
    params = {"q": "prompt extension:json stable-diffusion", "per_page": 3}

    print(f"\nTesting code search with headers...")
    resp = requests.get(url, params=params, headers=collector.headers, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Total results: {data.get('total_count', 0)}")
        if data.get("items"):
            for i, item in enumerate(data["items"][:3]):
                print(f"  {i+1}. {item['repository']['full_name']} - {item['name']}")
    else:
        print(f"Error: {resp.text[:200]}")


if __name__ == "__main__":
    test_headers()
