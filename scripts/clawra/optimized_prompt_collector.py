#!/usr/bin/env python3
"""
优化版GitHub提示词收集器

改进点：
1. 更具体的搜索关键词
2. 仓库预过滤（排除非AI仓库）
3. 基于文件名的优先级处理
4. 增强的内容过滤和评分
5. 处理超时和性能优化
"""

import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import requests

# 添加项目路径
sys.path.append(os.path.dirname(__file__))


@dataclass
class OptimizedGitHubRepo:
    """优化的GitHub仓库信息"""

    full_name: str
    description: Optional[str]
    stars: int
    language: Optional[str]
    topics: List[str] = field(default_factory=list)
    updated_at: str = ""
    fork: bool = False
    size: int = 0
    default_branch: str = "main"

    # 新增字段用于评估
    is_ai_prompt_repo: bool = False
    prompt_file_count: int = 0
    estimated_prompts: int = 0
    code_quality_score: float = 0.0


@dataclass
class OptimizedPromptEntry:
    """优化版提示词条目"""

    id: str
    category: str = "text_to_image"
    subcategory: str = "general"
    prompt_text: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    model_compatibility: List[str] = field(default_factory=list)
    quality_score: float = 0.5
    source: str = ""
    source_url: str = ""
    examples: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    # 新增字段
    verification_status: str = "unverified"  # unverified, automated, human_verified
    usage_count: int = 0
    success_rate: float = 0.0


class OptimizedGitHubPromptCollector:
    """优化版GitHub提示词收集器"""

    def __init__(self, github_token: Optional[str] = None):
        """
        初始化优化版收集器

        Args:
            github_token: GitHub API令牌（可选，提高速率限制）
        """
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"

        # API基础URL
        self.base_url = "https://api.github.com"

        # 优化的搜索关键词 - 更具体，更相关
        self.search_keywords = [
            # AI绘画提示词
            '"stable diffusion" prompt collection',
            '"midjourney" prompt library',
            "AI art prompts repository",
            "text-to-image prompts dataset",
            "generative art prompt collection",
            # 图生视频提示词
            "image to video prompts",
            "gen-2 prompts collection",
            "runwayml prompts library",
            "pika labs prompts",
            # 特定格式的提示词库
            "prompts.json repository",
            "prompt dataset github",
            "AI prompt collection github",
            # 中文关键词
            "AI绘画 提示词 仓库",
            "文生图 提示词 库",
            "Stable Diffusion 提示词 合集",
        ]

        # 仓库过滤关键词 - 识别真正的AI提示词仓库
        self.repo_positive_keywords = [
            "prompt",
            "prompts",
            "stable diffusion",
            "midjourney",
            "dall-e",
            "text-to-image",
            "image-to-video",
            "ai art",
            "generative art",
            "stable-diffusion",
            "text2image",
            "image2video",
            "ai绘画",
            "文生图",
        ]

        self.repo_negative_keywords = [
            "tutorial",
            "course",
            "learning",
            "beginner",
            "example",
            "demo",
            "test",
            "sandbox",
            "experiment",
            "playground",
            "framework",
            "library",
            "api",
            "sdk",
            "client",
            "wrapper",
            "webui",
            "interface",
            "gui",
            "frontend",
            "backend",
            "model",
            "training",
            "finetune",
            "dataset",
            "download",
        ]

        # 文件扩展名优先级 - 高优先级文件先处理
        self.high_priority_extensions = [".json", ".yaml", ".yml", ".prompt", ".prompts"]
        self.medium_priority_extensions = [".txt", ".md", ".csv", ".tsv"]
        self.low_priority_extensions = [".py", ".js", ".java", ".cpp", ".html", ".css"]

        # 提示词检测关键词
        self.prompt_keywords = [
            "prompt:",
            "image of",
            "photo of",
            "portrait of",
            "landscape of",
            "high quality",
            "highly detailed",
            "masterpiece",
            "best quality",
            "ultra detailed",
            "professional",
            "sharp focus",
            "cinematic",
            "intricate details",
            "beautiful",
            "stunning",
            "amazing",
            "epic",
            "fantasy",
            "realistic",
            "anime",
            "artwork",
            "in the style of",
            "by artist",
            "trending on artstation",
        ]

        # 非提示词内容关键词
        self.non_prompt_keywords = [
            "browserslist",
            "not ie <=",
            "not op_mini",
            "python_requires",
            "setup.py",
            "requirements.txt",
            "def ",
            "function ",
            "class ",
            "import ",
            "export ",
            "gitignore",
            "license",
            "readme",
            "changelog",
            "install",
            "usage",
            "example:",
            "config",
            "settings",
            "api_key",
            "token",
            "password",
            "secret",
            "credential",
        ]

        # 配置
        self.timeout_seconds = 90  # 单个仓库处理超时
        self.max_files_per_repo = 50  # 每个仓库最大文件数
        self.max_total_prompts = 100  # 单次运行最大提示词数
        self.min_prompt_length = 10  # 最小提示词长度
        self.max_prompt_length = 300  # 最大提示词长度

        # 日志配置
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def search_repositories(self, keyword: str, per_page: int = 20) -> List[OptimizedGitHubRepo]:
        """
        搜索GitHub仓库，使用更严格的过滤

        Args:
            keyword: 搜索关键词
            per_page: 每页结果数

        Returns:
            优化后的GitHubRepo列表
        """
        url = f"{self.base_url}/search/repositories"
        params = {
            "q": keyword,
            "sort": "updated",  # 按最近更新排序，而不是stars
            "order": "desc",
            "per_page": per_page,
        }

        try:
            self.logger.info(f"搜索关键词: '{keyword}'")
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            repos = []
            for item in items:
                # 创建仓库对象
                repo = OptimizedGitHubRepo(
                    full_name=item["full_name"],
                    description=item.get("description", ""),
                    stars=item.get("stargazers_count", 0),
                    language=item.get("language"),
                    topics=item.get("topics", []),
                    updated_at=item.get("updated_at", ""),
                    fork=item.get("fork", False),
                    size=item.get("size", 0),
                    default_branch=item.get("default_branch", "main"),
                )

                # 评估是否为AI提示词仓库
                repo.is_ai_prompt_repo = self._evaluate_repo_for_prompts(repo)
                if repo.is_ai_prompt_repo:
                    repos.append(repo)
                    self.logger.debug(f"✅ 接受仓库: {repo.full_name} (stars: {repo.stars})")
                else:
                    self.logger.debug(f"❌ 过滤仓库: {repo.full_name} (非提示词仓库)")

            self.logger.info(f"搜索完成，找到 {len(items)} 个仓库，接受 {len(repos)} 个")
            return repos

        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            return []

    def _evaluate_repo_for_prompts(self, repo: OptimizedGitHubRepo) -> bool:
        """
        评估仓库是否为AI提示词仓库

        Args:
            repo: 仓库信息

        Returns:
            True如果是提示词仓库
        """
        # 基础检查：排除fork和微小仓库
        if repo.fork or repo.size < 100:  # 太小可能不是真正的提示词库
            return False

        # 检查描述中的关键词
        desc_lower = (repo.description or "").lower()
        name_lower = repo.full_name.lower()

        # 正匹配：必须包含至少一个正面关键词
        positive_match = any(
            keyword in desc_lower or keyword in name_lower
            for keyword in self.repo_positive_keywords
        )

        if not positive_match:
            return False

        # 负匹配：不能包含过多负面关键词
        negative_match_count = sum(
            1
            for keyword in self.repo_negative_keywords
            if keyword in desc_lower or keyword in name_lower
        )

        # 如果包含太多负面关键词，排除
        if negative_match_count > 2:
            return False

        # 语言检查：优先Python、Markdown、JSON相关的仓库
        acceptable_languages = ["Python", "Jupyter Notebook", "Markdown", "JSON", None]
        if repo.language not in acceptable_languages:
            self.logger.debug(f"语言不匹配: {repo.language}")
            return False

        return True

    def get_repo_contents(self, repo_full_name: str, path: str = "") -> List[Dict[str, Any]]:
        """
        获取仓库内容

        Args:
            repo_full_name: 仓库完整名称
            path: 路径

        Returns:
            内容列表
        """
        url = f"{self.base_url}/repos/{repo_full_name}/contents/{path}"

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"获取内容失败: {response.status_code} for {url}")
                return []
        except Exception as e:
            self.logger.error(f"获取内容异常: {e}")
            return []

    def download_file(self, url: str) -> Optional[str]:
        """
        下载文件内容

        Args:
            url: 文件下载URL

        Returns:
            文件内容或None
        """
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                # 检查内容类型
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type or "text/" in content_type:
                    return response.text
                else:
                    self.logger.debug(f"跳过非文本文件: {content_type}")
                    return None
            else:
                self.logger.warning(f"下载文件失败: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"下载文件异常: {e}")
            return None

    def _get_file_priority(self, filename: str) -> int:
        """
        获取文件处理优先级

        Args:
            filename: 文件名

        Returns:
            优先级：3=高，2=中，1=低，0=跳过
        """
        filename_lower = filename.lower()

        # 检查文件名是否包含提示词关键词
        name_has_prompt = any(
            keyword in filename_lower for keyword in ["prompt", "example", "sample", "collection"]
        )

        # 检查扩展名
        for ext in self.high_priority_extensions:
            if filename_lower.endswith(ext):
                return 4 if name_has_prompt else 3

        for ext in self.medium_priority_extensions:
            if filename_lower.endswith(ext):
                return 3 if name_has_prompt else 2

        for ext in self.low_priority_extensions:
            if filename_lower.endswith(ext):
                return 2 if name_has_prompt else 1

        return 0  # 跳过

    def extract_prompts_from_text(
        self, content: str, source_info: Dict[str, Any]
    ) -> List[OptimizedPromptEntry]:
        """
        从文本中提取提示词，使用增强的启发式算法

        Args:
            content: 文本内容
            source_info: 源信息

        Returns:
            提示词列表
        """
        prompts = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < self.min_prompt_length or len(line) > self.max_prompt_length:
                continue

            line_lower = line.lower()

            # 快速排除：非提示词内容
            if any(non_prompt in line_lower for non_prompt in self.non_prompt_keywords):
                continue

            # 检查是否为代码行（包含常见代码符号）
            code_symbols = ["{", "}", ";", "=", "()", "=>", "def ", "function ", "class "]
            if any(symbol in line for symbol in code_symbols):
                continue

            # 计算提示词分数
            score = 0.0

            # 1. 关键词匹配
            for keyword in self.prompt_keywords:
                if keyword in line_lower:
                    score += 0.5

            # 2. 结构特征
            words = line.split()
            word_count = len(words)

            # 合理的长度范围
            if 5 <= word_count <= 25:
                score += 1.0

            # 包含逗号（通常表示修饰词列表）
            if "," in line:
                score += 0.5

            # 包含括号（可能表示权重）
            if "(" in line and ")" in line:
                score += 0.3

            # 3. 内容质量特征
            # 描述性开头
            descriptive_starts = [
                "a ",
                "an ",
                "the ",
                "close-up of",
                "portrait of",
                "landscape of",
                "image of",
                "photo of",
                "picture of",
                "view of",
            ]
            if any(line_lower.startswith(start) for start in descriptive_starts):
                score += 1.0

            # 包含质量描述词
            quality_words = ["high quality", "detailed", "masterpiece", "professional", "beautiful"]
            if any(word in line_lower for word in quality_words):
                score += 0.5

            # 4. 负向特征
            # 太短或太长
            if word_count < 3 or word_count > 50:
                score -= 1.0

            # 看起来像URL或路径
            if "http://" in line_lower or "https://" in line_lower or "/" in line and "." in line:
                score -= 2.0

            # 最终判断
            if score >= 2.0:  # 调整阈值
                # 创建提示词条目
                prompt_id = f"{source_info.get('repo', 'unknown')}_{source_info.get('filepath', 'file')}_{line_num}"

                # 确定类别
                category, subcategory = self._determine_category(line, source_info)

                # 计算质量分数
                quality_score = min(1.0, max(0.1, score / 5.0))

                prompt = OptimizedPromptEntry(
                    id=prompt_id,
                    category=category,
                    subcategory=subcategory,
                    prompt_text=line,
                    parameters={},
                    model_compatibility=["stable-diffusion", "midjourney", "dall-e"],
                    quality_score=quality_score,
                    source=source_info.get("repo", "unknown"),
                    source_url=source_info.get("url", ""),
                    examples=[],
                    tags=[],
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                    verification_status="automated",
                )

                prompts.append(prompt)
                self.logger.debug(f"提取提示词: {line[:60]}... (分数: {score:.2f})")

        return prompts

    def _determine_category(self, prompt_text: str, source_info: Dict[str, Any]) -> Tuple[str, str]:
        """
        确定提示词类别

        Args:
            prompt_text: 提示词文本
            source_info: 源信息

        Returns:
            (category, subcategory) 元组
        """
        prompt_lower = prompt_text.lower()

        # 基于关键词确定类别
        categories = {
            "text_to_image": ["portrait", "landscape", "still life", "photo", "image", "painting"],
            "image_to_video": ["animation", "video", "moving", "dynamic", "cinematic"],
            "character_design": ["character", "person", "human", "face", "figure"],
            "environment": ["environment", "scene", "background", "setting", "landscape"],
            "object": ["object", "item", "thing", "product", "still life"],
            "abstract": ["abstract", "surreal", "fantasy", "dream", "concept"],
        }

        subcategories = {
            "realistic": ["realistic", "photorealistic", "photo", "real life"],
            "anime": ["anime", "manga", "cartoon", "animated"],
            "artistic": ["painting", "artwork", "illustration", "drawing", "sketch"],
            "fantasy": ["fantasy", "magical", "mythical", "legendary"],
            "sci_fi": ["sci-fi", "futuristic", "cyberpunk", "space", "robot"],
        }

        # 确定主类别
        category = "text_to_image"  # 默认
        for cat, keywords in categories.items():
            if any(keyword in prompt_lower for keyword in keywords):
                category = cat
                break

        # 确定子类别
        subcategory = "general"
        for subcat, keywords in subcategories.items():
            if any(keyword in prompt_lower for keyword in keywords):
                subcategory = subcat
                break

        return category, subcategory

    def extract_prompts_from_json(
        self, content: str, source_info: Dict[str, Any]
    ) -> List[OptimizedPromptEntry]:
        """
        从JSON中提取提示词

        Args:
            content: JSON内容
            source_info: 源信息

        Returns:
            提示词列表
        """
        prompts = []

        try:
            data = json.loads(content)

            # 处理不同JSON结构
            if isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        # 查找包含提示词的键
                        prompt_keys = [
                            k
                            for k in item.keys()
                            if "prompt" in k.lower()
                            or "text" in k.lower()
                            or "description" in k.lower()
                        ]
                        for key in prompt_keys:
                            value = item[key]
                            if (
                                isinstance(value, str)
                                and self.min_prompt_length <= len(value) <= self.max_prompt_length
                            ):
                                # 从文本中提取
                                text_prompts = self.extract_prompts_from_text(value, source_info)
                                prompts.extend(text_prompts)
                    elif isinstance(item, str):
                        text_prompts = self.extract_prompts_from_text(item, source_info)
                        prompts.extend(text_prompts)

            elif isinstance(data, dict):
                # 遍历字典值
                for key, value in data.items():
                    if isinstance(value, str) and "prompt" in key.lower():
                        if self.min_prompt_length <= len(value) <= self.max_prompt_length:
                            text_prompts = self.extract_prompts_from_text(value, source_info)
                            prompts.extend(text_prompts)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                text_prompts = self.extract_prompts_from_text(item, source_info)
                                prompts.extend(text_prompts)

        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON解析失败: {e}")

        return prompts

    def extract_prompts_from_yaml(
        self, content: str, source_info: Dict[str, Any]
    ) -> List[OptimizedPromptEntry]:
        """
        从YAML中提取提示词

        Args:
            content: YAML内容
            source_info: 源信息

        Returns:
            提示词列表
        """
        # 简化处理：先尝试作为文本提取
        return self.extract_prompts_from_text(content, source_info)

    def process_repository(
        self, repo: OptimizedGitHubRepo, max_files: Optional[int] = None
    ) -> List[OptimizedPromptEntry]:
        """
        处理仓库，提取提示词

        Args:
            repo: 仓库信息
            max_files: 最大文件数（默认为配置值）

        Returns:
            提示词列表
        """
        if max_files is None:
            max_files = self.max_files_per_repo

        self.logger.info(f"开始处理仓库: {repo.full_name}")
        start_time = time.time()

        prompts = []
        processed_files = 0

        try:
            # 获取仓库文件列表（带优先级）
            files_to_process = self._collect_files_with_priority(repo.full_name)

            # 按优先级排序
            files_to_process.sort(key=lambda x: x[0], reverse=True)

            # 处理文件
            for priority, filepath, item in files_to_process[:max_files]:
                if time.time() - start_time > self.timeout_seconds:
                    self.logger.warning(f"处理超时，已用时 {time.time() - start_time:.1f}秒")
                    break

                if len(prompts) >= self.max_total_prompts:
                    self.logger.info(f"已达到最大提示词数: {self.max_total_prompts}")
                    break

                self.logger.debug(f"处理文件: {filepath} (优先级: {priority})")
                file_prompts = self._process_file(filepath, item, repo)
                prompts.extend(file_prompts)
                processed_files += 1

            elapsed = time.time() - start_time
            self.logger.info(f"仓库处理完成: {repo.full_name}, 耗时: {elapsed:.1f}秒")
            self.logger.info(f"处理文件: {processed_files}, 提取提示词: {len(prompts)}")

        except Exception as e:
            self.logger.error(f"处理仓库异常: {e}")

        return prompts

    def _collect_files_with_priority(
        self, repo_full_name: str, path: str = ""
    ) -> List[Tuple[int, str, Dict[str, Any]]]:
        """
        收集文件并计算优先级

        Args:
            repo_full_name: 仓库名称
            path: 当前路径

        Returns:
            (优先级, 文件路径, 文件信息) 列表
        """
        files = []

        contents = self.get_repo_contents(repo_full_name, path)
        if not contents:
            return files

        for item in contents:
            if item["type"] == "file":
                filename = item["name"]
                filepath = f"{path}/{filename}" if path else filename

                # 计算优先级
                priority = self._get_file_priority(filename)
                if priority > 0:  # 只处理优先级>0的文件
                    files.append((priority, filepath, item))

            elif item["type"] == "dir":
                # 限制递归深度：只处理一级子目录
                if path.count("/") < 1:  # 只处理根目录下的直接子目录
                    dirpath = f"{path}/{item['name']}" if path else item["name"]
                    dir_files = self._collect_files_with_priority(repo_full_name, dirpath)
                    files.extend(dir_files)

        return files

    def _process_file(
        self, filepath: str, item: Dict[str, Any], repo: OptimizedGitHubRepo
    ) -> List[OptimizedPromptEntry]:
        """
        处理单个文件

        Args:
            filepath: 文件路径
            item: 文件信息
            repo: 仓库信息

        Returns:
            提示词列表
        """
        content = self.download_file(item["download_url"])
        if not content:
            return []

        source_info = {
            "repo": repo.full_name,
            "url": f"https://github.com/{repo.full_name}",
            "description": repo.description or "",
            "filepath": filepath,
        }

        filename = item["name"].lower()

        if filename.endswith(".json"):
            return self.extract_prompts_from_json(content, source_info)
        elif filename.endswith((".yaml", ".yml")):
            return self.extract_prompts_from_yaml(content, source_info)
        else:
            return self.extract_prompts_from_text(content, source_info)

    def collect_prompts(self, max_repos: int = 5) -> List[OptimizedPromptEntry]:
        """
        收集提示词的主要入口函数

        Args:
            max_repos: 最大处理仓库数

        Returns:
            提示词列表
        """
        all_prompts = []
        processed_repos = 0

        self.logger.info(f"开始收集提示词，最大处理仓库数: {max_repos}")

        # 搜索仓库
        repos_to_process = []
        for keyword in self.search_keywords:
            if len(repos_to_process) >= max_repos * 2:
                break

            repos = self.search_repositories(keyword, per_page=10)
            repos_to_process.extend(repos)

        # 去重
        unique_repos = {}
        for repo in repos_to_process:
            if repo.full_name not in unique_repos:
                unique_repos[repo.full_name] = repo

        repos_list = list(unique_repos.values())

        self.logger.info(f"找到 {len(repos_list)} 个唯一仓库")

        # 处理仓库
        for repo in repos_list[:max_repos]:
            if processed_repos >= max_repos:
                break

            self.logger.info(f"处理仓库 {processed_repos + 1}/{max_repos}: {repo.full_name}")
            prompts = self.process_repository(repo)

            if prompts:
                all_prompts.extend(prompts)
                self.logger.info(f"  提取到 {len(prompts)} 个提示词，累计 {len(all_prompts)} 个")
            else:
                self.logger.warning(f"  未提取到提示词")

            processed_repos += 1

            # 如果已达到目标数量，提前停止
            if len(all_prompts) >= self.max_total_prompts:
                self.logger.info(f"已达到目标提示词数量: {self.max_total_prompts}")
                break

        self.logger.info(
            f"收集完成，共处理 {processed_repos} 个仓库，提取 {len(all_prompts)} 个提示词"
        )
        return all_prompts


def test_optimized_collector():
    """测试优化版收集器"""
    print("=== 测试优化版GitHub提示词收集器 ===")

    # 设置日志
    logging.basicConfig(level=logging.INFO)

    collector = OptimizedGitHubPromptCollector()

    # 测试API速率限制
    try:
        import requests

        response = requests.get("https://api.github.com/rate_limit", headers=collector.headers)
        if response.status_code == 200:
            limits = response.json()["resources"]["core"]
            print(f"API速率限制: {limits['remaining']}/{limits['limit']}")
    except Exception as e:
        print(f"速率限制检查失败: {e}")

    # 收集提示词
    print("\n开始收集提示词...")
    prompts = collector.collect_prompts(max_repos=3)

    print(f"\n收集完成，共提取 {len(prompts)} 个提示词")

    if prompts:
        print("\n前10个提示词:")
        for i, prompt in enumerate(prompts[:10]):
            print(f"  {i+1}. {prompt.prompt_text[:80]}...")
            print(f"     类别: {prompt.category}, 子类别: {prompt.subcategory}")
            print(f"     质量分: {prompt.quality_score:.2f}")
            print(f"     来源: {prompt.source}")

        # 保存到文件
        output_file = "optimized_collected_prompts_v2.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in prompts], f, indent=2, ensure_ascii=False)

        print(f"\n提示词已保存到: {output_file}")

    return prompts


if __name__ == "__main__":
    prompts = test_optimized_collector()
    if prompts:
        print(f"\n✅ 测试成功！收集到 {len(prompts)} 个提示词")
        sys.exit(0)
    else:
        print(f"\n⚠️  测试完成，但未收集到提示词")
        sys.exit(1)
