#!/usr/bin/env python3
"""调试GitHub仓库内容"""

import os
import sys

import requests

sys.path.append(os.path.dirname(__file__))

from direct_prompt_collector import DirectPromptCollector


def main():
    print("=== 调试仓库内容 ===")

    collector = DirectPromptCollector()

    # 获取仓库内容
    repo_full_name = "AUTOMATIC1111/stable-diffusion-webui"
    print(f"\n获取仓库 {repo_full_name} 的内容...")

    contents = collector.get_repo_contents(repo_full_name)

    if not contents:
        print("无内容返回")
        return

    print(f"找到 {len(contents)} 个项目:")

    for i, item in enumerate(contents[:20]):
        item_type = item.get("type", "unknown")
        name = item.get("name", "unknown")
        size = item.get("size", 0)

        print(f"  {i+1}. {name} ({item_type}, {size} bytes)")

        # 如果是文件，检查是否可能包含提示词
        if item_type == "file":
            filename = name.lower()
            is_prompt_file = "prompt" in filename
            valid_extensions = (".json", ".txt", ".md", ".yaml", ".yml", ".csv")

            if is_prompt_file or filename.endswith(valid_extensions):
                print(f"      -> 可能包含提示词")

    # 特别检查是否有prompt相关文件
    print(f"\n可能包含提示词的文件:")
    prompt_files = []
    for item in contents:
        if item.get("type") == "file":
            filename = item["name"].lower()
            if "prompt" in filename:
                prompt_files.append(item["name"])

    if prompt_files:
        for filename in prompt_files:
            print(f"  - {filename}")
    else:
        print("  没有找到文件名包含'prompt'的文件")

    # 检查常见的提示词文件扩展名
    print(f"\nJSON和文本文件:")
    json_txt_files = []
    for item in contents:
        if item.get("type") == "file":
            filename = item["name"].lower()
            if filename.endswith((".json", ".txt", ".md")):
                json_txt_files.append(item["name"])

    for filename in json_txt_files[:10]:
        print(f"  - {filename}")

    if len(json_txt_files) > 10:
        print(f"  还有 {len(json_txt_files) - 10} 个文件未显示")


if __name__ == "__main__":
    main()
