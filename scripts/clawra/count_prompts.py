#!/usr/bin/env python3
"""统计所有提示词文件中的提示词数量"""

import glob
import json
import os


def count_prompts_in_file(file_path):
    """统计单个文件中的提示词数量"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return len(data)
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return 0


def main():
    """主函数"""
    # 查找所有包含提示词的JSON文件
    prompt_files = glob.glob("*prompts.json")

    print("=== 提示词文件统计 ===")

    total_prompts = 0
    file_stats = []

    for file_path in prompt_files:
        count = count_prompts_in_file(file_path)
        file_stats.append((file_path, count))
        total_prompts += count
        print(f"{file_path}: {count} 个提示词")

    print(f"\n总计: {total_prompts} 个提示词")

    # 按数量排序
    print("\n=== 按数量排序 ===")
    for file_path, count in sorted(file_stats, key=lambda x: x[1], reverse=True):
        print(f"{file_path}: {count} 个提示词")

    return total_prompts


if __name__ == "__main__":
    main()
