#!/usr/bin/env python3
"""
调试GitHub提示词收集器的过滤逻辑
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from github_prompt_collector import GitHubPromptCollector


def test_text_extraction():
    """测试文本提取功能"""
    print("=== 测试文本提取功能 ===")

    collector = GitHubPromptCollector()
    source_info = {
        "repo": "test/repo",
        "url": "https://github.com/test/repo",
        "description": "Test repository",
    }

    # 测试用例1: 真正的提示词
    test_cases = [
        ("A beautiful sunset over mountains, highly detailed, 8k resolution", "真正的提示词"),
        ("prompt: A cute cat playing with yarn ball, cartoon style", "带prompt:前缀"),
        ('"prompt": "Futuristic city at night, neon lights, cyberpunk style"', "JSON格式的提示词"),
        ("text: Portrait of an old wise man, realistic, detailed wrinkles", "带text:前缀"),
        ("A simple cat", "过短的提示词（应该被过滤）"),
        ("This is a readme file content that should be excluded", "README内容（应该被过滤）"),
        ("# Installation Guide", "Markdown标题（应该被过滤）"),
        ("Installation: pip install -r requirements.txt", "安装说明（应该被过滤）"),
        ("Copyright 2023 Some Author", "版权信息（应该被过滤）"),
        ("https://github.com/user/repo", "URL（应该被过滤）"),
        ("def generate_prompt():", "代码（应该被过滤）"),
        ('{ "model": "stable-diffusion" }', "JSON配置（应该被过滤）"),
        ("not ie <= 11", "browserslist（应该被过滤）"),
    ]

    for text, description in test_cases:
        print(f"\n测试: {description}")
        print(f"文本: {text}")

        # 模拟extract_prompts_from_text的逻辑
        prompts = collector.extract_prompts_from_text(text, source_info)

        if prompts:
            print(f"✅ 提取到提示词: {len(prompts)} 个")
            for i, prompt in enumerate(prompts):
                print(f"  提示词 {i+1}: {prompt.prompt_text[:80]}...")
                print(f"    质量评分: {prompt.quality_score:.2f}")
        else:
            print("❌ 未提取到提示词")

    # 测试更长的文本
    print("\n=== 测试多行文本 ===")
    multi_line_text = """
# README.md
This is a repository for Stable Diffusion prompts.

## Installation
pip install -r requirements.txt

## Usage
Here are some example prompts:

prompt: A majestic eagle soaring in the sky, detailed feathers, 4k
text: Abstract geometric patterns, vibrant colors, modern art

prompt: Product photo of a smartphone on marble table, studio lighting

## Configuration
You can configure the model in config.json:
{
  "model": "stable-diffusion",
  "size": "512x512"
}

## License
MIT License
"""

    print("多行文本测试:")
    prompts = collector.extract_prompts_from_text(multi_line_text, source_info)
    print(f"提取到 {len(prompts)} 个提示词")
    for i, prompt in enumerate(prompts):
        print(f"  {i+1}. {prompt.prompt_text}")


def test_file_type_based_filtering():
    """测试基于文件类型的过滤"""
    print("\n=== 测试基于文件类型的过滤 ===")

    collector = GitHubPromptCollector()
    source_info = {
        "repo": "test/repo",
        "url": "https://github.com/test/repo",
        "description": "Test repository",
        "filepath": "prompts.json",
    }

    # JSON内容测试
    json_content = """
[
  {
    "prompt": "A beautiful sunset over mountains, highly detailed, 8k",
    "model": "stable-diffusion",
    "size": "1024x1024"
  },
  {
    "text": "Cute anime character with blue eyes, pastel colors",
    "model": "midjourney"
  }
]
"""

    print("JSON文件测试:")
    prompts = collector.extract_prompts_from_json(json_content, source_info)
    print(f"从JSON提取到 {len(prompts)} 个提示词")

    # YAML内容测试
    yaml_content = """
- prompt: "Futuristic city at night, neon lights, cyberpunk style"
  model: dall-e
  size: "512x512"

- prompt: "Portrait of an old wise man, realistic, detailed wrinkles"
  model: "stable-diffusion"
"""

    print("\nYAML文件测试:")
    prompts = collector.extract_prompts_from_yaml(yaml_content, source_info)
    print(f"从YAML提取到 {len(prompts)} 个提示词")


def test_is_config_content():
    """测试_is_config_content方法"""
    print("\n=== 测试_is_config_content方法 ===")

    collector = GitHubPromptCollector()

    test_cases = [
        ("conda-forge", True),
        ("pip install torch", True),
        ("requirements.txt", True),
        ("name: mypackage", True),
        ("version: 1.0.0", True),
        ("license: MIT", True),
        ("import torch", True),
        ("def generate():", True),
        ("class Prompt:", True),
        ("A beautiful sunset", False),
        ("{", True),  # 特殊字符
        ("localhost:8080", True),
        ("http://example.com", True),
        ("/path/to/file.json", True),
    ]

    for text, expected in test_cases:
        result = collector._is_config_content(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text[:30]}...' -> 预期: {expected}, 实际: {result}")


def main():
    """主调试函数"""
    print("GitHub提示词收集器过滤逻辑调试")
    print("=" * 60)

    test_is_config_content()
    test_text_extraction()
    test_file_type_based_filtering()

    print("\n" + "=" * 60)
    print("调试完成")
    print("建议: 如果过滤过于严格，可以调整extract_prompts_from_text中的排除规则")


if __name__ == "__main__":
    main()
