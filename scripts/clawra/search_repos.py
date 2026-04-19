#!/usr/bin/env python3
"""搜索提示词仓库"""

import json
import time

import requests


def search_repositories(query, sort="stars", order="desc", per_page=10):
    url = "https://api.github.com/search/repositories"
    headers = {"Accept": "application/vnd.github.v3+json"}
    params = {"q": query, "sort": sort, "order": order, "per_page": per_page}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"错误: {response.status_code}")
            print(response.text[:200])
            return None
    except Exception as e:
        print(f"异常: {e}")
        return None


def main():
    queries = [
        "stable diffusion prompts",
        "midjourney prompts",
        "dall-e prompts",
        "ai art prompts",
        "text-to-image prompts",
        "prompt collection",
        "prompt dataset",
    ]

    all_repos = {}

    for query in queries:
        print(f"\n搜索: '{query}'")
        data = search_repositories(query, per_page=5)
        if data and "items" in data:
            print(f"  找到 {data['total_count']} 个仓库")
            for item in data["items"]:
                full_name = item["full_name"]
                if full_name not in all_repos:
                    all_repos[full_name] = {
                        "full_name": full_name,
                        "description": item.get("description", ""),
                        "stars": item.get("stargazers_count", 0),
                        "language": item.get("language", ""),
                        "topics": item.get("topics", []),
                        "url": item["html_url"],
                    }
                    print(f"    {full_name} ({item['stargazers_count']} stars)")
                    print(f"      描述: {item.get('description', '')[:80]}")
        time.sleep(1)  # 避免速率限制

    print(f"\n共找到 {len(all_repos)} 个唯一仓库")

    # 保存结果
    with open("found_repos.json", "w", encoding="utf-8") as f:
        json.dump(list(all_repos.values()), f, indent=2, ensure_ascii=False)

    print("结果已保存到 found_repos.json")


if __name__ == "__main__":
    main()
