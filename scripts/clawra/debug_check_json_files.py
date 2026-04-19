#!/usr/bin/env python3
"""
检查easydiffusion/easydiffusion仓库中的JSON文件
"""

import json
import os
import sys

sys.path.append(os.path.dirname(__file__))

from github_prompt_collector import GitHubPromptCollector


def check_json_files(repo_full_name):
    """检查仓库中的所有JSON文件"""
    print(f"=== 检查 {repo_full_name} 中的JSON文件 ===")

    collector = GitHubPromptCollector()

    # 获取仓库内容并查找JSON文件
    def find_json_files(path=""):
        json_files = []
        contents = collector.get_repo_contents(repo_full_name, path)
        if not contents:
            return json_files

        for item in contents:
            if item["type"] == "file" and item["name"].endswith(".json"):
                filepath = f"{path}/{item['name']}" if path else item["name"]
                json_files.append((filepath, item))
            elif item["type"] == "dir":
                dirpath = f"{path}/{item['name']}" if path else item["name"]
                json_files.extend(find_json_files(dirpath))

        return json_files

    json_files = find_json_files()
    print(f"找到 {len(json_files)} 个JSON文件")

    for i, (filepath, item) in enumerate(json_files[:10]):  # 限制前10个
        print(f"\n{i+1}. {filepath}")
        try:
            content = collector.download_file(item["download_url"])
            if content:
                # 尝试解析JSON
                try:
                    data = json.loads(content)
                    print(f"  内容类型: {type(data)}")

                    # 检查是否可能是提示词集合
                    if isinstance(data, list):
                        print(f"  列表长度: {len(data)}")
                        if data:
                            # 检查第一个元素
                            first_item = data[0]
                            if isinstance(first_item, dict):
                                print(f"  第一个元素键: {list(first_item.keys())[:5]}")
                                # 检查是否包含提示词相关键
                                prompt_keys = [
                                    k
                                    for k in first_item.keys()
                                    if "prompt" in k.lower()
                                    or "text" in k.lower()
                                    or "input" in k.lower()
                                ]
                                if prompt_keys:
                                    print(f"  可能包含提示词键: {prompt_keys}")
                                    # 预览提示词内容
                                    for key in prompt_keys[:2]:
                                        value = first_item[key]
                                        if isinstance(value, str) and len(value) < 200:
                                            print(f"    示例提示词: {value[:100]}...")
                    elif isinstance(data, dict):
                        print(f"  字典键: {list(data.keys())[:10]}")
                        # 检查是否有包含提示词的嵌套结构
                        for key in list(data.keys())[:5]:
                            if "prompt" in key.lower():
                                print(f"  发现提示词键: {key}")
                except json.JSONDecodeError as e:
                    print(f"  JSON解析错误: {e}")
                    print(f"  内容预览: {content[:200]}...")
            else:
                print(f"  无法下载内容")
        except Exception as e:
            print(f"  错误: {e}")

    return json_files


def check_yml_yaml_files(repo_full_name):
    """检查YAML/YML文件"""
    print(f"\n=== 检查 {repo_full_name} 中的YAML/YML文件 ===")

    collector = GitHubPromptCollector()

    def find_yaml_files(path=""):
        yaml_files = []
        contents = collector.get_repo_contents(repo_full_name, path)
        if not contents:
            return yaml_files

        for item in contents:
            name_lower = item["name"].lower()
            if item["type"] == "file" and (
                name_lower.endswith(".yaml") or name_lower.endswith(".yml")
            ):
                filepath = f"{path}/{item['name']}" if path else item["name"]
                yaml_files.append((filepath, item))
            elif item["type"] == "dir":
                dirpath = f"{path}/{item['name']}" if path else item["name"]
                yaml_files.extend(find_yaml_files(dirpath))

        return yaml_files

    yaml_files = find_yaml_files()
    print(f"找到 {len(yaml_files)} 个YAML/YML文件")

    for i, (filepath, item) in enumerate(yaml_files[:5]):
        print(f"\n{i+1}. {filepath}")
        try:
            content = collector.download_file(item["download_url"])
            if content:
                print(f"  内容预览: {content[:300]}...")
            else:
                print(f"  无法下载内容")
        except Exception as e:
            print(f"  错误: {e}")

    return yaml_files


def main():
    repo_name = "easydiffusion/easydiffusion"

    # 检查JSON文件
    json_files = check_json_files(repo_name)

    # 检查YAML文件
    yaml_files = check_yml_yaml_files(repo_name)

    if not json_files and not yaml_files:
        print(f"\n=== 未找到JSON/YAML文件，检查TXT和MD文件 ===")
        collector = GitHubPromptCollector()

        # 查找TXT和MD文件
        def find_text_files(path=""):
            text_files = []
            contents = collector.get_repo_contents(repo_name, path)
            if not contents:
                return text_files

            for item in contents:
                name_lower = item["name"].lower()
                if item["type"] == "file" and (
                    name_lower.endswith(".txt") or name_lower.endswith(".md")
                ):
                    filepath = f"{path}/{item['name']}" if path else item["name"]
                    text_files.append((filepath, item))
                elif item["type"] == "dir":
                    dirpath = f"{path}/{item['name']}" if path else item["name"]
                    text_files.extend(find_text_files(dirpath))

            return text_files

        text_files = find_text_files()
        print(f"找到 {len(text_files)} 个TXT/MD文件")

        # 检查前几个文件是否包含提示词
        for i, (filepath, item) in enumerate(text_files[:5]):
            print(f"\n{i+1}. {filepath}")
            content = collector.download_file(item["download_url"])
            if content:
                # 检查是否包含提示词关键词
                content_lower = content.lower()
                prompt_indicators = [
                    "prompt:",
                    "image of",
                    "photo of",
                    "portrait of",
                    "landscape of",
                    "high quality",
                    "highly detailed",
                ]
                found = [ind for ind in prompt_indicators if ind in content_lower]
                if found:
                    print(f"  包含提示词指示器: {found[:3]}")
                    print(f"  内容预览: {content[:200]}...")
                else:
                    print(f"  不包含明显的提示词指示器")
            else:
                print(f"  无法下载内容")


if __name__ == "__main__":
    main()
