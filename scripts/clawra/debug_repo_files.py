#!/usr/bin/env python3
"""调试仓库文件列表"""

import json
import os
import sys

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import FinalGitHubPromptCollector


def debug_repo_files(repo_full_name: str):
    """调试仓库文件"""
    collector = FinalGitHubPromptCollector()

    print(f"获取仓库文件: {repo_full_name}")
    contents = collector.get_repo_files(repo_full_name)

    print(f"返回 {len(contents)} 个条目")

    if contents:
        print("\n前10个文件:")
        for i, item in enumerate(contents[:10]):
            print(f"{i+1}. 名称: {item.get('name')}, 类型: {item.get('type')}")
            print(f"   路径: {item.get('path')}")
            print(f"   download_url: {item.get('download_url', 'N/A')}")
            print(f"   url: {item.get('url')}")
            print()

    # 尝试下载一个已知文件
    test_file = None
    for item in contents:
        if item.get("type") == "file" and "portrait" in item.get("name", "").lower():
            test_file = item
            break

    if test_file:
        print(f"\n测试下载文件: {test_file['name']}")
        content = collector.get_file_content_for_item(test_file, repo_full_name)
        if content:
            print(f"下载成功，长度: {len(content)} 字符")
            print(f"前200字符:")
            print(content[:200])
        else:
            print("下载失败")


if __name__ == "__main__":
    debug_repo_files("mehakjain07/stable-diffusion-prompts-collection")
