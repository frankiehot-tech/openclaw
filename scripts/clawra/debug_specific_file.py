#!/usr/bin/env python3
"""调试特定文件"""

import json
import os
import sys

import requests

sys.path.append(os.path.dirname(__file__))

from code_search_prompts import (
    extract_prompts_from_json,
    get_file_content_from_item,
    search_code_files,
)
from final_prompt_collector import StrictPromptExtractor


def debug_file(repo_full_name: str, file_path: str):
    """调试特定仓库的文件"""
    # 手动构建文件项
    file_item = {
        "repository": {"full_name": repo_full_name, "default_branch": "main"},
        "path": file_path,
        "name": os.path.basename(file_path),
        "url": f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}",
    }

    print(f"调试文件: {repo_full_name}/{file_path}")

    content = get_file_content_from_item(file_item)
    if not content:
        print("无法获取内容")
        return

    print(f"内容长度: {len(content)} 字符")
    print("\n前1000字符:")
    print(content[:1000])
    print("\n...")

    # 尝试解析JSON
    try:
        data = json.loads(content)
        print(f"\nJSON解析成功")
        print(f"数据类型: {type(data)}")

        # 使用extract_prompts_from_json
        prompts = extract_prompts_from_json(content)
        print(f"\nextract_prompts_from_json提取到 {len(prompts)} 个提示词:")
        for i, prompt in enumerate(prompts):
            print(f"{i+1}. {prompt[:100]}...")
            print(f"   长度: {len(prompt)} 字符")

        # 验证
        extractor = StrictPromptExtractor()
        print(f"\n验证结果:")
        for i, prompt in enumerate(prompts):
            is_valid = extractor._validate_prompt(prompt)
            is_image = extractor._is_image_generation_prompt(prompt)
            print(f"{i+1}. 有效: {is_valid}, 图像生成: {is_image}")
            if not is_valid:
                print(f"   验证失败原因: 可能包含排除词")
                # 检查排除词
                prompt_lower = prompt.lower()
                for exclude_word in ["format", "style", "color", "template"]:  # 常见排除词
                    if exclude_word in prompt_lower:
                        print(f"   包含排除词: {exclude_word}")
            if not is_image:
                print(f"   非图像生成提示词特征")

    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")


def main():
    # 调试第一个有问题的文件
    debug_file("anderlli0053/AppArchive", "stable-diffusion-prompt-reader_(1).json")


if __name__ == "__main__":
    main()
