#!/usr/bin/env python3
"""测试假设的提示词仓库是否存在"""

import os
import sys

import requests

sys.path.append(os.path.dirname(__file__))

from direct_prompt_collector import DirectPromptCollector


def test_repository(repo_full_name):
    """测试仓库是否存在并获取信息"""
    collector = DirectPromptCollector()

    print(f"\n测试仓库: {repo_full_name}")

    repo = collector.get_repo_info(repo_full_name)
    if repo:
        print(f"  存在: {repo.full_name}")
        print(f"  描述: {repo.description}")
        print(f"  Stars: {repo.stars}")
        print(f"  语言: {repo.language}")
        print(f"  主题: {repo.topics}")
        print(f"  更新: {repo.updated_at}")
        return True
    else:
        print(f"  不存在或无法访问")
        return False


def main():
    print("=== 测试提示词仓库 ===\n")

    # 假设的提示词仓库列表
    potential_repos = [
        "prompthero/prompthero-prompt-collection",
        "Gustavosta/Stable-Diffusion-Prompts",
        "ai-prompts-collection/stable-diffusion-prompts",
        "nicknochnack/StableDiffusionCheatSheet",
        "JingShing/Stable-Diffusion-Prompt-Book",
        "su77ungr/ChatGPT-Prompts",
        "f/awesome-chatgpt-prompts",
        "Prijector/awesome-stable-diffusion-prompts",
        "TheLastBen/fast-stable-diffusion",
        "AUTOMATIC1111/stable-diffusion-webui",  # 这个我们知道存在
        "CompVis/stable-diffusion",  # 原始模型仓库
        "huggingface/diffusers",  # 扩散模型库
        "Sygil-Dev/sygil-webui",  # 另一个WebUI
        "invoke-ai/InvokeAI",  # 另一个AI图像生成工具
        "lstein/stable-diffusion",  # 另一个实现
        # 尝试一些专门收集提示词的
        "datasciencedojo/awesome-ai-prompt-engineering",
        "dair-ai/Prompt-Engineering-Guide",
        "thinkingjimmy/Learning-Prompt",
        "kai-temp/awesome-llm-prompt-collection",
        "imaurer/awesome-deep-learning-papers",
    ]

    existing_repos = []
    non_existing_repos = []

    for repo_name in potential_repos:
        if test_repository(repo_name):
            existing_repos.append(repo_name)
        else:
            non_existing_repos.append(repo_name)

    print(f"\n=== 总结 ===")
    print(f"存在的仓库: {len(existing_repos)}")
    for repo in existing_repos:
        print(f"  - {repo}")

    print(f"\n不存在的仓库: {len(non_existing_repos)}")
    for repo in non_existing_repos[:10]:  # 只显示前10个
        print(f"  - {repo}")
    if len(non_existing_repos) > 10:
        print(f"  还有 {len(non_existing_repos) - 10} 个...")


if __name__ == "__main__":
    main()
