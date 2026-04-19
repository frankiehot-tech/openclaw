#!/usr/bin/env python3
"""专门处理526christian/AI-Image-PromptGenerator仓库"""

import json
import logging
import os
import sys
from dataclasses import asdict

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import FinalGitHubPromptCollector, FinalGitHubRepo


def process_526christian_repo():
    """处理526christian/AI-Image-PromptGenerator仓库"""
    print("=== 处理526christian/AI-Image-PromptGenerator仓库 ===")

    # 设置详细日志
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    collector = FinalGitHubPromptCollector()

    # 修改配置以更好地处理此仓库
    collector.max_files_per_repo = 100  # 增加文件限制
    collector.timeout_seconds = 120  # 增加超时时间

    repo_name = "526christian/AI-Image-PromptGenerator"
    description = "A flexible UI script to help create and expand on prompts"

    print(f"仓库: {repo_name}")
    print(f"描述: {description}")

    # 检查API限制
    try:
        import requests

        response = requests.get("https://api.github.com/rate_limit", headers=collector.headers)
        if response.status_code == 200:
            limits = response.json()["resources"]["core"]
            print(f"API速率限制: {limits['remaining']}/{limits['limit']}")
    except Exception as e:
        print(f"速率限制检查失败: {e}")

    # 创建仓库对象
    repo = FinalGitHubRepo(
        full_name=repo_name,
        description=description,
        stars=100,  # 默认值
        language="Python",  # 主要语言
        topics=["ai", "prompt", "image-generation"],  # 猜测的主题
        updated_at="2023-01-01T00:00:00Z",  # 默认值
        fork=False,
        size=1000,
    )

    print("\n开始处理仓库...")

    try:
        # 使用改进的方法处理此仓库
        prompts = collector.process_repository(repo)

        print(f"\n提取到 {len(prompts)} 个提示词")

        if prompts:
            # 显示前10个提示词作为示例
            print("\n前10个提示词:")
            for i, prompt in enumerate(prompts[:10]):
                print(f"  {i+1}. {prompt.prompt_text[:80]}...")
                print(f"     类别: {prompt.category}, 子类别: {prompt.subcategory}")
                print(f"     质量: {prompt.quality_score:.2f}")

            # 保存到文件
            output_file = "526christian_prompts.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump([asdict(p) for p in prompts], f, indent=2, ensure_ascii=False)

            print(f"\n提示词已保存到: {output_file}")

            # 统计信息
            categories = {}
            for prompt in prompts:
                cat = prompt.category
                categories[cat] = categories.get(cat, 0) + 1

            print("\n类别统计:")
            for cat, count in categories.items():
                print(f"  {cat}: {count} 个")

            return prompts
        else:
            print("⚠️  未提取到提示词")
            return []

    except Exception as e:
        print(f"❌ 处理仓库时出错: {e}")
        import traceback

        traceback.print_exc()
        return []


def explore_prompts_directory():
    """直接探索prompts目录"""
    print("\n=== 直接探索prompts目录 ===")

    import requests

    # prompts目录的URL
    url = "https://api.github.com/repos/526christian/AI-Image-PromptGenerator/contents/prompts"

    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        contents = response.json()

        print(f"prompts目录包含 {len(contents)} 个条目:")

        prompts_data = []

        for item in contents:
            if item["type"] == "file":
                print(f"\n📄 文件: {item['name']}")
                print(f"  大小: {item['size']} 字节")
                print(f"  URL: {item.get('download_url', '无')}")

                # 尝试下载文件内容
                if "download_url" in item and item["download_url"]:
                    try:
                        file_response = requests.get(item["download_url"], timeout=30)
                        file_response.raise_for_status()
                        content = file_response.text
                        print(f"  内容预览: {content[:200]}...")

                        # 尝试解析为JSON
                        if item["name"].endswith(".json"):
                            try:
                                json_data = json.loads(content)
                                print(
                                    f"  JSON条目数: {len(json_data) if isinstance(json_data, list) else '非列表'}"
                                )
                                prompts_data.append(json_data)
                            except json.JSONDecodeError:
                                print(f"  不是有效的JSON")
                    except Exception as e:
                        print(f"  下载失败: {e}")
            elif item["type"] == "dir":
                print(f"\n📁 目录: {item['name']}/")

        return prompts_data

    except Exception as e:
        print(f"探索prompts目录失败: {e}")
        return []


if __name__ == "__main__":
    # 方法1: 使用收集器
    prompts1 = process_526christian_repo()

    # 方法2: 直接探索prompts目录
    prompts2 = explore_prompts_directory()

    if prompts1:
        print(f"\n✅ 通过收集器获得 {len(prompts1)} 个提示词")
        sys.exit(0)
    elif prompts2:
        print(f"\n✅ 通过直接探索获得数据")
        sys.exit(0)
    else:
        print(f"\n⚠️  未获得提示词")
        sys.exit(1)
