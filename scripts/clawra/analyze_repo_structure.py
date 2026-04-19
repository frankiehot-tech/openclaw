#!/usr/bin/env python3
"""分析GitHub仓库结构，了解文件组织方式"""

import json
import sys

import requests


def get_repo_contents(repo_full_name, path=""):
    """获取仓库内容"""
    url = (
        f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
        if path
        else f"https://api.github.com/repos/{repo_full_name}/contents"
    )

    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"获取仓库内容失败: {e}")
        return None


def analyze_repository(repo_name):
    """分析仓库结构"""
    print(f"\n=== 分析仓库: {repo_name} ===")

    # 检查根目录
    print("\n1. 根目录内容:")
    root_contents = get_repo_contents(repo_name)
    if not root_contents:
        print("  无法获取根目录内容")
        return

    if isinstance(root_contents, list):
        files = [item for item in root_contents if item["type"] == "file"]
        dirs = [item for item in root_contents if item["type"] == "dir"]

        print(f"  文件: {len(files)} 个, 目录: {len(dirs)} 个")

        # 显示所有文件
        print("\n  文件列表:")
        for file in files[:20]:  # 限制显示数量
            size_kb = file.get("size", 0) / 1024
            print(f"    📄 {file['name']} ({size_kb:.1f} KB)")

        if len(files) > 20:
            print(f"    ... 还有 {len(files) - 20} 个文件未显示")

        # 显示目录
        print("\n  目录列表:")
        for directory in dirs[:10]:
            print(f"    📁 {directory['name']}/")

        # 检查是否有README或说明文件
        readme_files = [f for f in files if "readme" in f["name"].lower()]
        if readme_files:
            print(f"\n  发现README文件: {[f['name'] for f in readme_files]}")

        # 检查文件扩展名
        extensions = {}
        for file in files:
            name = file["name"]
            if "." in name:
                ext = name.split(".")[-1].lower()
                extensions[ext] = extensions.get(ext, 0) + 1

        if extensions:
            print(f"\n  文件扩展名统计:")
            for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"    .{ext}: {count} 个")

    else:
        print("  根目录是单个文件")

    # 检查常见提示词目录
    print("\n2. 检查常见提示词目录:")
    common_prompt_dirs = ["prompts", "prompt", "examples", "data", "dataset", "wildcards", "text"]
    for dir_name in common_prompt_dirs:
        dir_contents = get_repo_contents(repo_name, dir_name)
        if dir_contents and isinstance(dir_contents, list):
            print(f"  📁 {dir_name}/ - 找到 {len(dir_contents)} 个条目")
            # 显示前几个文件
            files_in_dir = [item for item in dir_contents if item["type"] == "file"][:3]
            for file in files_in_dir:
                print(f"      📄 {file['name']}")


def main():
    """主函数"""
    if len(sys.argv) > 1:
        repo_names = sys.argv[1:]
    else:
        # 默认检查未成功处理的仓库
        repo_names = [
            "poloclub/diffusiondb",
            "awesome-ai-tools/curated-midjourney-prompts",
            "526christian/AI-Image-PromptGenerator",
            "LearnPrompt/LearnPrompt",
            "altryne/awesome-ai-art-image-synthesis",
            "promptslab/Awesome-Prompt-Engineering",
        ]

    print("=== GitHub仓库结构分析 ===")

    for repo_name in repo_names:
        analyze_repository(repo_name)

    print("\n=== 分析完成 ===")


if __name__ == "__main__":
    main()
