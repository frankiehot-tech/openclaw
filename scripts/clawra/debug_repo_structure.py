#!/usr/bin/env python3
"""
调试GitHub仓库文件结构，了解easydiffusion/easydiffusion仓库的内容
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from github_prompt_collector import GitHubPromptCollector


def explore_repo_structure(repo_full_name):
    """探索仓库的文件结构"""
    print(f"=== 探索仓库: {repo_full_name} ===")

    collector = GitHubPromptCollector()

    # 获取仓库内容
    contents = collector.get_repo_contents(repo_full_name)
    if not contents:
        print(f"❌ 无法获取仓库内容")
        return

    print(f"根目录有 {len(contents)} 个条目")

    # 分析文件类型
    file_extensions = {}
    prompt_files = []
    non_prompt_files = []

    def process_directory(path="", max_depth=3, current_depth=0):
        if current_depth >= max_depth:
            return

        dir_contents = collector.get_repo_contents(repo_full_name, path)
        if not dir_contents:
            return

        for item in dir_contents:
            if item["type"] == "file":
                filename = item["name"]
                filepath = f"{path}/{filename}" if path else filename

                # 分析文件扩展名
                if "." in filename:
                    ext = filename.split(".")[-1].lower()
                    file_extensions[ext] = file_extensions.get(ext, 0) + 1
                else:
                    file_extensions["无扩展名"] = file_extensions.get("无扩展名", 0) + 1

                # 检查是否是提示词文件（基于收集器的逻辑）
                if any(
                    filename.endswith(ext.replace("*", ""))
                    for ext in collector.prompt_file_patterns
                ):
                    # 进一步检查文件名是否包含提示词关键词
                    filename_lower = filename.lower()
                    prompt_keywords = ["prompt", "example", "sample", "collection", "gallery"]
                    negative_keywords = [
                        "readme",
                        "license",
                        "changelog",
                        "contributing",
                        "config",
                        "setup",
                    ]

                    if any(neg in filename_lower for neg in negative_keywords):
                        non_prompt_files.append(filepath)
                    elif any(keyword in filename_lower for keyword in prompt_keywords):
                        prompt_files.append(filepath)
                    else:
                        non_prompt_files.append(filepath)
                else:
                    non_prompt_files.append(filepath)

            elif item["type"] == "dir" and current_depth < max_depth - 1:
                dirpath = f"{path}/{item['name']}" if path else item["name"]
                process_directory(dirpath, max_depth, current_depth + 1)

    # 处理根目录，深度为3
    process_directory("", max_depth=3, current_depth=0)

    # 输出分析结果
    print(f"\n=== 文件扩展名统计 ===")
    for ext, count in sorted(file_extensions.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {ext}: {count}")

    print(f"\n=== 可能包含提示词的文件 ({len(prompt_files)}) ===")
    for file in prompt_files[:10]:
        print(f"  {file}")
    if len(prompt_files) > 10:
        print(f"  ... 还有 {len(prompt_files) - 10} 个文件")

    print(f"\n=== 非提示词文件 ({len(non_prompt_files)}) ===")
    for file in non_prompt_files[:10]:
        print(f"  {file}")
    if len(non_prompt_files) > 10:
        print(f"  ... 还有 {len(non_prompt_files) - 10} 个文件")

    # 检查具体的文件内容
    print(f"\n=== 检查前3个可能提示词文件的内容 ===")
    for i, filepath in enumerate(prompt_files[:3]):
        print(f"\n文件 {i+1}: {filepath}")
        try:
            # 查找文件的实际下载URL
            # 简化：直接获取文件内容
            dir_contents = collector.get_repo_contents(
                repo_full_name, os.path.dirname(filepath) if "/" in filepath else ""
            )
            if dir_contents:
                for item in dir_contents:
                    if item["name"] == os.path.basename(filepath):
                        content = collector.download_file(item["download_url"])
                        if content:
                            print(f"  内容预览: {content[:200]}...")
                        else:
                            print(f"  无法下载内容")
                        break
        except Exception as e:
            print(f"  错误: {e}")

    return prompt_files, non_prompt_files, file_extensions


def test_prompt_extraction_on_file(repo_full_name, filepath):
    """测试在特定文件上提取提示词"""
    print(f"\n=== 测试提示词提取: {repo_full_name}/{filepath} ===")

    collector = GitHubPromptCollector()

    # 获取文件内容
    dirpath = os.path.dirname(filepath) if "/" in filepath else ""
    filename = os.path.basename(filepath)

    dir_contents = collector.get_repo_contents(repo_full_name, dirpath)
    if not dir_contents:
        print(f"❌ 无法获取目录内容")
        return

    for item in dir_contents:
        if item["name"] == filename:
            content = collector.download_file(item["download_url"])
            if not content:
                print(f"❌ 无法下载文件内容")
                return

            source_info = {
                "repo": repo_full_name,
                "url": f"https://github.com/{repo_full_name}",
                "description": "测试仓库",
                "filepath": filepath,
            }

            # 根据文件类型提取
            if filename.endswith(".json"):
                prompts = collector.extract_prompts_from_json(content, source_info)
            elif filename.endswith((".yaml", ".yml")):
                prompts = collector.extract_prompts_from_yaml(content, source_info)
            else:
                prompts = collector.extract_prompts_from_text(content, source_info)

            print(f"提取到 {len(prompts)} 个提示词")
            for i, prompt in enumerate(prompts[:5]):
                print(f"  提示词 {i+1}: {prompt.prompt_text[:100]}...")
                print(f"    质量评分: {prompt.quality_score:.2f}")
            return

    print(f"❌ 找不到文件: {filename}")


def main():
    """主函数"""
    repo_name = "easydiffusion/easydiffusion"

    # 探索仓库结构
    prompt_files, non_prompt_files, extensions = explore_repo_structure(repo_name)

    # 如果没有找到可能的提示词文件，尝试其他方式
    if not prompt_files:
        print(f"\n=== 未找到可能的提示词文件，尝试搜索包含'prompt'的文件 ===")
        # 我们可以搜索仓库中所有包含"prompt"关键词的文件
        # 但为了简化，我们先检查一些常见的提示词文件位置
        common_prompt_locations = [
            "prompts.json",
            "examples.json",
            "samples.json",
            "prompts.txt",
            "examples.txt",
            "samples.txt",
            "prompts.md",
            "examples.md",
        ]

        for location in common_prompt_locations:
            print(f"尝试查找: {location}")
            # 这里简化处理，实际应该递归搜索
            # 但为了演示，我们只是列出

    # 如果有找到可能的提示词文件，测试提取
    if prompt_files:
        test_prompt_extraction_on_file(repo_name, prompt_files[0])
    else:
        print(f"\n未找到提示词文件进行测试")


if __name__ == "__main__":
    main()
