#!/usr/bin/env python3
"""调试JSON文件内容"""

import json
import os
import sys

import requests

sys.path.append(os.path.dirname(__file__))

from code_search_prompts import get_file_content_from_item, search_code_files


def debug_file_content():
    query = "prompt extension:json"
    files = search_code_files(query, per_page=3)

    if not files:
        print("没有找到文件")
        return

    for i, file_item in enumerate(files):
        repo_name = file_item["repository"]["full_name"]
        file_name = file_item["name"]
        print(f"\n=== 文件 {i+1}: {repo_name} - {file_name} ===")

        content = get_file_content_from_item(file_item)
        if not content:
            print("无法获取内容")
            continue

        print(f"内容长度: {len(content)} 字符")
        print(f"前500字符:")
        print(content[:500])
        print("...")

        # 尝试解析JSON
        try:
            data = json.loads(content)
            print(f"JSON解析成功")
            print(f"数据类型: {type(data)}")
            if isinstance(data, dict):
                print(f"字典键: {list(data.keys())[:10]}")
                # 检查是否有prompt字段
                if "prompt" in data:
                    print(f"找到'prompt'字段: {data['prompt'][:100]}")
            elif isinstance(data, list):
                print(f"列表长度: {len(data)}")
                if len(data) > 0:
                    print(f"第一个元素类型: {type(data[0])}")
                    if isinstance(data[0], dict):
                        print(f"第一个元素的键: {list(data[0].keys())[:10]}")
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            # 可能是其他格式，检查是否包含prompt文本
            if "prompt" in content.lower():
                print("内容中包含'prompt'文本")

        print("-" * 50)


if __name__ == "__main__":
    debug_file_content()
