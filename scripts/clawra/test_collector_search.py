#!/usr/bin/env python3
"""测试收集器的search_code_for_prompts方法"""

import logging
import os
import sys

sys.path.append(os.path.dirname(__file__))

# 配置日志
logging.basicConfig(level=logging.INFO)

from final_prompt_collector import FinalGitHubPromptCollector


def main():
    print("=== 测试FinalGitHubPromptCollector.search_code_for_prompts ===")

    collector = FinalGitHubPromptCollector()

    try:
        repos = collector.search_code_for_prompts()
        print(f"找到 {len(repos)} 个仓库")

        for i, repo in enumerate(repos[:10]):
            print(f"\n{i+1}. {repo.full_name}")
            print(f"   描述: {repo.description}")
            print(f"   Stars: {repo.stars}, 语言: {repo.language}")
            print(f"   主题: {repo.topics}")

    except Exception as e:
        print(f"错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
