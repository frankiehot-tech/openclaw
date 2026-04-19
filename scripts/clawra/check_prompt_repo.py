#!/usr/bin/env python3
"""检查提示词仓库结构"""

import json

import requests


def check_repo(repo_full_name):
    url = f"https://api.github.com/repos/{repo_full_name}/contents"
    headers = {"Accept": "application/vnd.github.v3+json"}

    print(f"\n=== 检查仓库: {repo_full_name} ===")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            contents = response.json()
            print(f"找到 {len(contents)} 个文件/目录:")

            md_files = []
            json_files = []
            txt_files = []
            dirs = []

            for item in contents:
                if item["type"] == "file":
                    name = item["name"].lower()
                    if name.endswith(".md"):
                        md_files.append(item["name"])
                    elif name.endswith(".json"):
                        json_files.append(item["name"])
                    elif name.endswith(".txt"):
                        txt_files.append(item["name"])
                elif item["type"] == "dir":
                    dirs.append(item["name"])

            if md_files:
                print(f"  Markdown文件: {md_files}")
            if json_files:
                print(f"  JSON文件: {json_files}")
            if txt_files:
                print(f"  文本文件: {txt_files}")
            if dirs:
                print(f"  目录: {dirs}")

            # 检查是否有prompts目录
            if "prompts" in dirs:
                print(f"\n  检查prompts目录:")
                prompts_url = f"{url}/prompts"
                prompts_response = requests.get(prompts_url, headers=headers, timeout=15)
                if prompts_response.status_code == 200:
                    prompts_contents = prompts_response.json()
                    prompt_files = [
                        item["name"] for item in prompts_contents if item["type"] == "file"
                    ]
                    print(f"    prompts目录文件: {prompt_files[:10]}")
                    if len(prompt_files) > 10:
                        print(f"    ... 还有 {len(prompt_files)-10} 个文件")
        else:
            print(f"错误: {response.status_code}")
            print(response.text[:200])
    except Exception as e:
        print(f"异常: {e}")


if __name__ == "__main__":
    # 检查已知仓库
    repos = [
        "mehakjain07/stable-diffusion-prompts-collection",
        "awesome-ai-tools/curated-midjourney-prompts",
        "AUTOMATIC1111/stable-diffusion-webui",
        "dair-ai/Prompt-Engineering-Guide",
    ]

    for repo in repos:
        check_repo(repo)
