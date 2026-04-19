#!/usr/bin/env python3
"""
直接访问已知高质量提示词仓库
绕过搜索不确定性，直接从已验证来源收集提示词
"""

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

from final_prompt_collector import (
    FinalGitHubRepo,
    FinalPromptEntry,
    StrictPromptExtractor,
)

# 已知高质量提示词仓库列表
# 这些是经过验证的、专门收集文生图提示词的仓库
KNOWN_PROMPT_REPOS = [
    # 大型提示词数据集
    ("poloclub/diffusiondb", "DiffusionDB - 1400万稳定扩散提示词数据集"),
    # 专门收集高质量提示词的仓库
    (
        "mehakjain07/stable-diffusion-prompts-collection",
        "精选、分类的高质量稳定扩散、Midjourney、DALL·E、Flux提示词",
    ),
    (
        "awesome-ai-tools/curated-midjourney-prompts",
        "精选的Midjourney、DALL-E、稳定扩散和Flux提示词集合",
    ),
    # 稳定扩散相关仓库（可能包含示例提示词）
    ("AUTOMATIC1111/stable-diffusion-webui", "Stable Diffusion WebUI，包含示例"),
    # 提示词工程指南
    ("dair-ai/Prompt-Engineering-Guide", "提示工程指南，包含示例"),
    # 新发现的仓库
    ("rockbenben/img-prompt", "AI Image Prompt Generator with 5000+ prompts in 18 languages"),
    (
        "526christian/AI-Image-PromptGenerator",
        "A flexible UI script to help create and expand on prompts",
    ),
    ("LearnPrompt/LearnPrompt", "免费开源AIGC课程，包含提示词示例"),
    ("altryne/awesome-ai-art-image-synthesis", "AI艺术资源列表，可能包含提示词"),
    ("promptslab/Awesome-Prompt-Engineering", "提示工程资源，包含示例"),
]


class DirectPromptCollector:
    """直接提示词收集器"""

    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"

        self.base_url = "https://api.github.com"
        self.extractor = StrictPromptExtractor()

        # 配置
        self.max_files_per_repo = 30
        self.timeout_seconds = 30

        # 日志
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def get_repo_info(self, repo_full_name: str) -> Optional[FinalGitHubRepo]:
        """获取仓库信息"""
        url = f"{self.base_url}/repos/{repo_full_name}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                repo = FinalGitHubRepo(
                    full_name=data["full_name"],
                    description=data.get("description"),
                    stars=data.get("stargazers_count", 0),
                    language=data.get("language"),
                    topics=data.get("topics", []),
                    updated_at=data.get("updated_at", ""),
                    fork=data.get("fork", False),
                    size=data.get("size", 0),
                )
                return repo
        except Exception as e:
            self.logger.error(f"获取仓库信息失败 {repo_full_name}: {e}")

        return None

    def search_repo_for_prompt_files(self, repo_full_name: str) -> List[Dict[str, Any]]:
        """搜索仓库中的提示词文件"""
        # 使用GitHub API搜索仓库中的文件
        search_url = f"{self.base_url}/search/code"

        # 搜索可能包含提示词的文件
        query = f"repo:{repo_full_name} filename:prompt OR filename:prompts OR extension:json OR extension:txt"

        params = {"q": query, "per_page": 20}

        try:
            response = requests.get(search_url, params=params, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return response.json().get("items", [])
        except Exception as e:
            self.logger.error(f"搜索文件失败 {repo_full_name}: {e}")

        return []

    def get_repo_contents(self, repo_full_name: str, path: str = "") -> List[Dict[str, Any]]:
        """获取仓库内容"""
        url = (
            f"{self.base_url}/repos/{repo_full_name}/contents/{path}"
            if path
            else f"{self.base_url}/repos/{repo_full_name}/contents"
        )

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.error(f"获取内容失败 {repo_full_name}/{path}: {e}")

        return []

    def download_file(self, url: str) -> Optional[str]:
        """下载文件"""
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type or "text/" in content_type:
                    return response.text
        except Exception as e:
            self.logger.error(f"下载文件失败: {e}")

        return None

    def process_repository(
        self, repo_full_name: str, description: str = ""
    ) -> List[FinalPromptEntry]:
        """处理仓库"""
        self.logger.info(f"处理已知仓库: {repo_full_name} - {description}")

        # 获取仓库信息
        repo = self.get_repo_info(repo_full_name)
        if not repo:
            self.logger.warning(f"无法获取仓库信息: {repo_full_name}")
            return []

        prompts = []
        files_processed = 0

        # 获取根目录内容
        root_contents = self.get_repo_contents(repo_full_name)
        if not root_contents:
            self.logger.warning(f"仓库无内容: {repo_full_name}")
            return []

        # 收集要处理的文件
        files_to_process = []

        # 处理根目录文件
        for item in root_contents:
            if item["type"] == "file":
                files_to_process.append(item)
            elif item["type"] == "dir" and item["name"].lower() == "prompts":
                # 处理prompts目录
                prompts_contents = self.get_repo_contents(repo_full_name, "prompts")
                if prompts_contents:
                    for sub_item in prompts_contents:
                        if sub_item["type"] == "file":
                            files_to_process.append(sub_item)
                        elif sub_item["type"] == "dir" and sub_item["name"].lower() == "notes":
                            # 处理notes子目录
                            notes_contents = self.get_repo_contents(repo_full_name, "prompts/notes")
                            if notes_contents:
                                for note_item in notes_contents:
                                    if note_item["type"] == "file":
                                        files_to_process.append(note_item)

        # 处理收集到的文件
        for item in files_to_process[: self.max_files_per_repo]:
            filename = item["name"].lower()

            # 处理可能包含提示词的文件
            is_prompt_file = "prompt" in filename
            valid_extensions = (".json", ".txt", ".md", ".yaml", ".yml", ".csv")

            if not (is_prompt_file or filename.endswith(valid_extensions)):
                continue

            # 排除README和LICENSE
            if "readme" in filename or "license" in filename:
                continue

            # 下载文件
            content = self.download_file(item["download_url"])
            if not content:
                continue

            # 提取提示词
            file_prompts = self.extract_prompts_from_content(content, repo, item["name"])
            if file_prompts:
                prompts.extend(file_prompts)
                files_processed += 1
                self.logger.debug(f"文件 {item['name']}: 提取到 {len(file_prompts)} 个提示词")

        self.logger.info(f"仓库处理完成: {files_processed} 个文件, {len(prompts)} 个提示词")
        return prompts

    def extract_prompts_from_content(
        self, content: str, repo: FinalGitHubRepo, filename: str
    ) -> List[FinalPromptEntry]:
        """从内容中提取提示词（复用final_prompt_collector中的逻辑）"""
        prompts = []

        # 使用严格提取器
        prompt_texts = self.extractor.extract_prompts(content)

        for i, prompt_text in enumerate(prompt_texts):
            # 创建提示词条目
            prompt_id = f"{repo.full_name.replace('/', '_')}_{filename}_{i}"

            # 确定类别
            category, subcategory = self._determine_category(prompt_text)

            # 计算质量分数
            quality_score = self._calculate_quality_score(prompt_text)

            prompt = FinalPromptEntry(
                id=prompt_id,
                category=category,
                subcategory=subcategory,
                prompt_text=prompt_text,
                parameters={},
                model_compatibility=["stable-diffusion", "midjourney", "dall-e"],
                quality_score=quality_score,
                source=repo.full_name,
                source_url=f"https://github.com/{repo.full_name}",
                examples=[],
                tags=[],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                verification_status="direct_collection",
            )

            prompts.append(prompt)

        return prompts

    def _determine_category(self, prompt_text: str):
        """确定类别（复用final_prompt_collector中的逻辑）"""
        prompt_lower = prompt_text.lower()

        # 主类别
        if "portrait" in prompt_lower or "face" in prompt_lower or "person" in prompt_lower:
            category = "character_design"
        elif (
            "landscape" in prompt_lower or "scene" in prompt_lower or "environment" in prompt_lower
        ):
            category = "environment"
        elif "animation" in prompt_lower or "video" in prompt_lower or "motion" in prompt_lower:
            category = "image_to_video"
        else:
            category = "text_to_image"

        # 子类别
        if "realistic" in prompt_lower or "photorealistic" in prompt_lower:
            subcategory = "realistic"
        elif "anime" in prompt_lower or "manga" in prompt_lower or "cartoon" in prompt_lower:
            subcategory = "anime"
        elif "fantasy" in prompt_lower or "magical" in prompt_lower:
            subcategory = "fantasy"
        elif "sci-fi" in prompt_lower or "cyberpunk" in prompt_lower:
            subcategory = "sci_fi"
        else:
            subcategory = "general"

        return category, subcategory

    def _calculate_quality_score(self, prompt_text: str) -> float:
        """计算质量分数（复用final_prompt_collector中的逻辑）"""
        score = 0.5  # 基础分数

        prompt_lower = prompt_text.lower()

        # 长度加分
        words = prompt_text.split()
        if 10 <= len(words) <= 25:
            score += 0.2

        # 关键词加分
        quality_keywords = ["high quality", "detailed", "masterpiece", "professional", "4k", "8k"]
        for keyword in quality_keywords:
            if keyword in prompt_lower:
                score += 0.1

        # 结构加分
        if "," in prompt_text:  # 逗号分隔的修饰词
            score += 0.1

        if "(" in prompt_text and ")" in prompt_text:  # 权重说明
            score += 0.1

        # 限制在0.1-1.0之间
        return max(0.1, min(1.0, score))

    def collect_from_known_repos(self) -> List[FinalPromptEntry]:
        """从已知仓库收集提示词"""
        all_prompts = []

        self.logger.info(f"从 {len(KNOWN_PROMPT_REPOS)} 个已知仓库收集提示词")

        for repo_full_name, description in KNOWN_PROMPT_REPOS:
            try:
                prompts = self.process_repository(repo_full_name, description)
                if prompts:
                    all_prompts.extend(prompts)
                    self.logger.info(
                        f"仓库 {repo_full_name}: 提取到 {len(prompts)} 个提示词，累计 {len(all_prompts)} 个"
                    )
                else:
                    self.logger.warning(f"仓库 {repo_full_name}: 未提取到提示词")
            except Exception as e:
                self.logger.error(f"处理仓库 {repo_full_name} 失败: {e}")

        self.logger.info(f"收集完成，共提取 {len(all_prompts)} 个提示词")
        return all_prompts


def main():
    """主函数"""
    print("=== 直接访问已知仓库提示词收集器 ===")

    # 设置日志
    logging.basicConfig(level=logging.INFO)

    collector = DirectPromptCollector()

    # 检查API限制
    try:
        response = requests.get("https://api.github.com/rate_limit", headers=collector.headers)
        if response.status_code == 200:
            limits = response.json()["resources"]["core"]
            print(f"API速率限制: {limits['remaining']}/{limits['limit']}")
    except Exception as e:
        print(f"速率限制检查失败: {e}")

    # 收集提示词
    print("\n从已知仓库收集提示词...")
    prompts = collector.collect_from_known_repos()

    print(f"\n收集完成，共提取 {len(prompts)} 个提示词")

    if prompts:
        print("\n前10个提示词:")
        for i, prompt in enumerate(prompts[:10]):
            print(f"  {i+1}. {prompt.prompt_text[:80]}...")
            print(f"     类别: {prompt.category}, 子类别: {prompt.subcategory}")
            print(f"     质量: {prompt.quality_score:.2f}, 来源: {prompt.source}")

        # 保存到文件
        output_file = "direct_collected_prompts.json"
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


if __name__ == "__main__":
    prompts = main()
    if prompts:
        print(f"\n✅ 成功！从已知仓库收集到 {len(prompts)} 个提示词")
        sys.exit(0)
    else:
        print(f"\n⚠️  未收集到提示词")
        sys.exit(1)
