#!/usr/bin/env python3
"""
调试GitHub提示词收集器
"""

import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from github_prompt_collector import GitHubPromptCollector, GitHubRepo


def test_search():
    """测试搜索功能"""
    print("=== 测试GitHub搜索功能 ===")

    collector = GitHubPromptCollector()

    # 测试搜索关键词
    keyword = "stable diffusion prompt"
    print(f"搜索关键词: '{keyword}'")

    try:
        repos = collector.search_repositories(keyword, per_page=5)
        print(f"找到仓库数量: {len(repos)}")

        if repos:
            print("\n前3个仓库:")
            for i, repo in enumerate(repos[:3]):
                print(f"  {i+1}. {repo.full_name}")
                print(f"     描述: {repo.description[:80] if repo.description else '无'}")
                print(f"     Stars: {repo.stars}, 语言: {repo.language}")
                print(f"     更新: {repo.updated_at}")
                print(f"     主题: {', '.join(repo.topics[:3]) if repo.topics else '无'}")

            return repos[0] if repos else None
        else:
            print("❌ 未找到仓库")
            return None

    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_repo_processing(repo):
    """测试仓库处理"""
    print(f"\n=== 测试仓库处理: {repo.full_name} ===")

    collector = GitHubPromptCollector()

    try:
        print("开始处理仓库...")
        start_time = time.time()

        prompts = collector.process_repository(repo)

        elapsed = time.time() - start_time
        print(f"处理完成，耗时: {elapsed:.2f}秒")
        print(f"提取提示词数量: {len(prompts)}")

        if prompts:
            print("\n前3个提取的提示词:")
            for i, prompt in enumerate(prompts[:3]):
                print(f"  {i+1}. {prompt.prompt_text[:80]}...")
                print(f"     类别: {prompt.category}, 子类别: {prompt.subcategory}")
                print(f"     质量分: {prompt.quality_score:.2f}")
                print(f"     参数: {prompt.parameters}")

        return prompts

    except Exception as e:
        print(f"❌ 仓库处理失败: {e}")
        import traceback

        traceback.print_exc()
        return []


def test_api_rate_limit():
    """测试API速率限制"""
    print("\n=== 测试API速率限制 ===")

    collector = GitHubPromptCollector()

    try:
        import requests

        # 使用相同的headers
        headers = collector.headers

        # 获取速率限制
        response = requests.get("https://api.github.com/rate_limit", headers=headers)
        if response.status_code == 200:
            limits = response.json()["resources"]["core"]
            print(f"速率限制: {limits['remaining']}/{limits['limit']}")
            print(f"重置时间: {limits['reset']} ({time.ctime(limits['reset'])})")
            return limits["remaining"]
        else:
            print(f"❌ 获取速率限制失败: {response.status_code}")
            return 0

    except Exception as e:
        print(f"❌ 速率限制检查失败: {e}")
        return 0


def main():
    """主调试函数"""
    print("GitHub提示词收集器调试")
    print("=" * 60)

    # 检查API速率限制
    remaining = test_api_rate_limit()
    if remaining < 10:
        print(f"⚠️  剩余API调用次数较少: {remaining}")
        return False

    # 测试搜索
    repo = test_search()
    if not repo:
        print("❌ 搜索测试失败")
        return False

    # 测试仓库处理
    prompts = test_repo_processing(repo)

    # 最终检查
    print("\n" + "=" * 60)
    print("调试结果:")
    print(f"  搜索测试: {'✅ 通过' if repo else '❌ 失败'}")
    print(f"  仓库处理: {'✅ 通过' if prompts else '⚠️ 未提取到提示词'}")
    print(f"  提取数量: {len(prompts)}")

    if prompts:
        print("\n🎯 调试成功！收集器可以正常工作。")
        return True
    else:
        print("\n⚠️  调试完成，但未提取到提示词。")
        print("   可能原因:")
        print("   1. 仓库中不包含标准格式的提示词")
        print("   2. 文件格式不支持")
        print("   3. 提取逻辑需要调整")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
