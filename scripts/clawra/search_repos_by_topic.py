#!/usr/bin/env python3
"""通过主题和描述搜索提示词仓库"""

import json
import os
import sys
import time
from typing import Any, Dict, List

import requests

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import FinalGitHubPromptCollector


def search_repositories(query: str, per_page: int = 20) -> List[Dict[str, Any]]:
    """搜索GitHub仓库"""
    url = "https://api.github.com/search/repositories"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ClawraPromptCollector/1.0",
    }
    # 如果有token，添加Authorization
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json().get("items", [])
        else:
            print(f"搜索失败: {response.status_code} - {response.text[:200]}")
            return []
    except Exception as e:
        print(f"搜索异常: {e}")
        return []


def get_repository_contents(repo_full_name: str, path: str = "") -> List[Dict[str, Any]]:
    """获取仓库内容"""
    url = (
        f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
        if path
        else f"https://api.github.com/repos/{repo_full_name}/contents"
    )
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ClawraPromptCollector/1.0",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"获取内容失败 {repo_full_name}/{path}: {response.status_code}")
            return []
    except Exception as e:
        print(f"获取内容异常: {e}")
        return []


def find_prompt_files(repo_full_name: str) -> List[Dict[str, Any]]:
    """查找仓库中的提示词文件"""
    prompt_files = []
    contents = get_repository_contents(repo_full_name)
    if not contents:
        return prompt_files

    for item in contents:
        if item["type"] == "file":
            name_lower = item["name"].lower()
            # 检查文件名是否包含prompt或特定扩展名
            if "prompt" in name_lower or name_lower.endswith(
                (".json", ".txt", ".md", ".yaml", ".yml", ".csv")
            ):
                # 排除常见非提示词文件
                if "readme" not in name_lower and "license" not in name_lower:
                    prompt_files.append(item)
        elif item["type"] == "dir":
            # 检查目录名是否包含prompt
            if "prompt" in item["name"].lower():
                # 递归搜索prompt目录
                sub_contents = get_repository_contents(repo_full_name, item["path"])
                for sub_item in sub_contents:
                    if sub_item["type"] == "file":
                        prompt_files.append(sub_item)

    return prompt_files


def main():
    print("=== 搜索提示词仓库 ===")

    # 搜索查询列表
    queries = [
        "stable diffusion prompts",
        "midjourney prompts",
        "dall-e prompts",
        "ai art prompts",
        "text-to-image prompts",
        "prompt collection",
        "prompt dataset",
        "prompt library",
        "ai image generation prompts",
        "generative art prompts",
    ]

    all_repos = {}
    prompt_repos = []  # 包含提示词文件的仓库

    for query in queries:
        print(f"\n搜索: '{query}'")
        repos = search_repositories(query, per_page=15)
        print(f"  找到 {len(repos)} 个仓库")

        for repo in repos:
            full_name = repo["full_name"]
            if full_name in all_repos:
                continue

            all_repos[full_name] = {
                "full_name": full_name,
                "description": repo.get("description", ""),
                "stars": repo.get("stargazers_count", 0),
                "language": repo.get("language", ""),
                "topics": repo.get("topics", []),
                "url": repo["html_url"],
            }

            print(f"  {full_name} ({repo['stargazers_count']} stars)")
            print(f"    描述: {repo.get('description', '')[:80]}")

            # 查找提示词文件
            print(f"    查找提示词文件...")
            prompt_files = find_prompt_files(full_name)
            if prompt_files:
                print(f"    找到 {len(prompt_files)} 个提示词文件")
                prompt_repos.append({"repo": all_repos[full_name], "files": prompt_files})
            else:
                print(f"    未找到提示词文件")

            # 避免速率限制
            time.sleep(1)

        time.sleep(2)  # 查询间延迟

    print(f"\n总计: {len(all_repos)} 个唯一仓库，{len(prompt_repos)} 个包含提示词文件")

    # 保存结果
    with open("searched_repos.json", "w", encoding="utf-8") as f:
        json.dump(
            {"all_repos": list(all_repos.values()), "prompt_repos": prompt_repos},
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("结果已保存到 searched_repos.json")

    # 显示包含提示词文件的仓库
    if prompt_repos:
        print("\n包含提示词文件的仓库:")
        for i, pr in enumerate(prompt_repos[:10]):
            repo = pr["repo"]
            print(f"{i+1}. {repo['full_name']} ({repo['stars']} stars)")
            print(f"   文件: {', '.join([f['name'] for f in pr['files'][:3]])}")
            if len(pr["files"]) > 3:
                print(f"   ... 还有 {len(pr['files']) - 3} 个文件")


if __name__ == "__main__":
    main()
