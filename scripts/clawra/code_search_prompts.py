#!/usr/bin/env python3
"""通过代码搜索直接查找提示词文件"""

import json
import os
import re
import sys
import time

import requests

sys.path.append(os.path.dirname(__file__))

from typing import Any, Dict, List, Optional

from final_prompt_collector import StrictPromptExtractor


def search_code_files(query: str, per_page: int = 10) -> List[Dict[str, Any]]:
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
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json().get("items", [])
        else:
            print(f"搜索失败 {query}: {response.status_code} - {response.text[:200]}")
            return []
    except Exception as e:
        print(f"搜索异常 {query}: {e}")
        return []


def get_file_content_from_item(file_item: Dict[str, Any]) -> Optional[str]:
    """从文件项获取内容"""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ClawraPromptCollector/1.0",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    # 方法1: 使用raw.githubusercontent.com
    repo_full_name = file_item["repository"]["full_name"]
    default_branch = file_item["repository"].get("default_branch", "main")
    file_path = file_item["path"]

    raw_url = f"https://raw.githubusercontent.com/{repo_full_name}/{default_branch}/{file_path}"

    try:
        response = requests.get(raw_url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"原始URL下载失败: {e}")

    # 方法2: 使用API端点
    api_url = file_item["url"]
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # 内容可能是base64编码
            if "content" in data and data.get("encoding") == "base64":
                import base64

                return base64.b64decode(data["content"]).decode("utf-8")
            elif "content" in data:
                return data["content"]
    except Exception as e:
        print(f"API下载失败: {e}")

    return None


def download_file(download_url: str) -> Optional[str]:
    """下载文件（保留兼容性）"""
    headers = {"User-Agent": "ClawraPromptCollector/1.0"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        response = requests.get(download_url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"下载失败: {e}")

    return None


def extract_prompts_from_json(content: str) -> List[str]:
    """从JSON内容中提取提示词"""
    prompts = []
    try:
        data = json.loads(content)
        # 如果data是列表，遍历每个元素
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # 查找prompt、text、description字段
                    for key in ["prompt", "text", "description", "input"]:
                        if key in item and isinstance(item[key], str):
                            prompts.append(item[key])
        elif isinstance(data, dict):
            # 查找嵌套的prompt字段
            for key in ["prompt", "text", "description", "input"]:
                if key in data and isinstance(data[key], str):
                    prompts.append(data[key])
                elif key in data and isinstance(data[key], list):
                    # 如果字段是列表
                    for item in data[key]:
                        if isinstance(item, str):
                            prompts.append(item)
    except json.JSONDecodeError:
        # 不是JSON，返回空列表
        pass

    return prompts


def main():
    print("=== 代码搜索提示词 ===")

    extractor = StrictPromptExtractor()
    all_prompts = []

    # 搜索查询
    queries = [
        "prompt extension:json",
        "prompt extension:txt",
        "prompt extension:md",
        "stable diffusion extension:json",
        "midjourney extension:json",
    ]

    for query in queries:
        print(f"\n搜索: '{query}'")
        files = search_code_files(query, per_page=8)
        print(f"  找到 {len(files)} 个文件")

        for i, file_item in enumerate(files):
            repo_name = file_item["repository"]["full_name"]
            file_name = file_item["name"]

            print(f"  {i+1}. {repo_name} - {file_name}")

            # 获取文件内容
            content = get_file_content_from_item(file_item)
            if not content:
                print(f"    下载失败")
                continue

            # 根据文件类型提取提示词
            file_ext = file_name.lower().split(".")[-1]
            if file_ext == "json":
                # 从JSON提取
                json_prompts = extract_prompts_from_json(content)
                print(f"    从JSON提取到 {len(json_prompts)} 个提示词")
                for prompt in json_prompts:
                    # 验证提示词
                    if extractor._validate_prompt(prompt) and extractor._is_image_generation_prompt(
                        prompt
                    ):
                        all_prompts.append(
                            {
                                "prompt": prompt,
                                "source": repo_name,
                                "file": file_name,
                                "type": "json",
                            }
                        )
            else:
                # 使用提取器提取
                prompts = extractor.extract_prompts(content)
                print(f"    提取到 {len(prompts)} 个候选提示词")
                for prompt in prompts:
                    # 验证提示词
                    if extractor._validate_prompt(prompt) and extractor._is_image_generation_prompt(
                        prompt
                    ):
                        all_prompts.append(
                            {
                                "prompt": prompt,
                                "source": repo_name,
                                "file": file_name,
                                "type": "text",
                            }
                        )

            # 避免速率限制
            time.sleep(1.5)

        time.sleep(2)

    print(f"\n总计收集到 {len(all_prompts)} 个提示词")

    if all_prompts:
        # 保存提示词
        output_file = "code_search_prompts.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_prompts, f, indent=2, ensure_ascii=False)

        print(f"提示词已保存到 {output_file}")

        # 显示一些示例
        print("\n前10个提示词:")
        for i, p in enumerate(all_prompts[:10]):
            print(f"{i+1}. {p['prompt'][:80]}...")
            print(f"   来源: {p['source']}, 文件: {p['file']}")

    return all_prompts


if __name__ == "__main__":
    # 修复导入
    from typing import Any, Dict, List, Optional

    main()
