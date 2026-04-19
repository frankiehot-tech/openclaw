#!/usr/bin/env python3
"""从所有已知仓库收集提示词（增量处理）"""

import json
import logging
import os
import sys
import time
from dataclasses import asdict

sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import FinalGitHubPromptCollector, FinalGitHubRepo


def collect_from_all_known_repos():
    """从所有已知仓库收集提示词"""
    print("=== 从所有已知仓库收集提示词 ===")

    # 设置详细日志
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    collector = FinalGitHubPromptCollector()

    # 修改配置以适应大型仓库
    collector.max_files_per_repo = 50  # 每个仓库最多处理50个文件
    collector.timeout_seconds = 90  # 增加超时时间
    collector.max_content_length = 1000000  # 增加最大内容长度

    print(f"已知仓库数量: {len(collector.known_prompt_repos)}")
    print("已知仓库列表:")
    for i, (repo_name, description) in enumerate(collector.known_prompt_repos):
        print(f"  {i+1}. {repo_name} - {description}")

    # 检查API限制
    try:
        import requests

        response = requests.get("https://api.github.com/rate_limit", headers=collector.headers)
        if response.status_code == 200:
            limits = response.json()["resources"]["core"]
            print(f"\nAPI速率限制: {limits['remaining']}/{limits['limit']}")
            if limits["remaining"] < 50:
                print("⚠️  API限制较低，考虑等待或分批处理")
    except Exception as e:
        print(f"速率限制检查失败: {e}")

    all_prompts = []
    processed_repos = []

    # 排除已经处理过的仓库
    already_processed = [
        "mehakjain07/stable-diffusion-prompts-collection",
        "Avaray/stable-diffusion-simple-wildcards",
    ]

    print(f"\n排除已处理的仓库: {already_processed}")

    # 处理每个仓库（跳过已处理的）
    for repo_name, description in collector.known_prompt_repos:
        if repo_name in already_processed:
            print(f"\n跳过已处理仓库: {repo_name}")
            continue

        print(f"\n=== 处理仓库: {repo_name} ===")
        print(f"描述: {description}")

        try:
            # 创建仓库对象
            repo = FinalGitHubRepo(
                full_name=repo_name,
                description=description,
                stars=100,  # 默认值
                language="Text",  # 默认值
                topics=[],  # 默认为空
                updated_at="2023-01-01T00:00:00Z",  # 默认值
                fork=False,
                size=1000,
            )

            # 处理仓库（有超时保护）
            start_time = time.time()
            prompts = collector.process_repository(repo)
            elapsed = time.time() - start_time

            print(f"从 {repo_name} 提取到 {len(prompts)} 个提示词 (耗时: {elapsed:.1f}s)")

            if prompts:
                # 添加到总列表
                all_prompts.extend(prompts)
                processed_repos.append(repo_name)

                # 显示前3个提示词作为示例
                print("示例提示词:")
                for i, prompt in enumerate(prompts[:3]):
                    print(f"  {i+1}. {prompt.prompt_text[:60]}...")
                    print(f"     类别: {prompt.category}, 质量: {prompt.quality_score:.2f}")

                # 每处理完一个仓库就保存一次（增量保存）
                incremental_file = (
                    f"incremental_{len(processed_repos)}_{repo_name.replace('/', '_')}_prompts.json"
                )
                with open(incremental_file, "w", encoding="utf-8") as f:
                    json.dump([asdict(p) for p in prompts], f, indent=2, ensure_ascii=False)
                print(f"增量保存到: {incremental_file}")

            else:
                print(f"⚠️  未从 {repo_name} 提取到提示词")

            # 避免API速率限制：处理完每个仓库后暂停一下
            print("暂停5秒以避免速率限制...")
            time.sleep(5)

        except Exception as e:
            print(f"❌ 处理仓库 {repo_name} 时出错: {e}")
            import traceback

            traceback.print_exc()

        # 如果已经收集到足够多的提示词，可以提前停止
        if len(all_prompts) >= 300:
            print(f"\n已收集 {len(all_prompts)} 个提示词，达到阈值，提前停止")
            break

    # 保存所有收集的提示词
    if all_prompts:
        output_file = "all_known_repos_prompts.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in all_prompts], f, indent=2, ensure_ascii=False)

        print(f"\n✅ 收集完成！")
        print(f"共处理 {len(processed_repos)} 个仓库: {processed_repos}")
        print(f"总共收集 {len(all_prompts)} 个提示词")
        print(f"保存到: {output_file}")

        # 统计信息
        categories = {}
        for prompt in all_prompts:
            cat = prompt.category
            categories[cat] = categories.get(cat, 0) + 1

        print("\n=== 最终类别统计 ===")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count} 个")

        return all_prompts
    else:
        print("\n⚠️  未收集到任何提示词")
        return []


if __name__ == "__main__":
    prompts = collect_from_all_known_repos()
    if prompts:
        print(f"\n✅ 成功！从已知仓库收集到 {len(prompts)} 个提示词")
        sys.exit(0)
    else:
        print(f"\n⚠️  未收集到提示词")
        sys.exit(1)
