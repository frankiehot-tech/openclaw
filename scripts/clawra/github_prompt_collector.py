#!/usr/bin/env python3
"""
GitHub提示词收集器
用于搜索GitHub上的高质量文生图、图生视频提示词库

功能：
1. GitHub API搜索相关仓库
2. 提示词质量评估和筛选
3. 结构化存储到知识库
4. 去重和分类管理

搜索策略（质量优先）：
- 搜索高质量提示词工程仓库
- 优先考虑结构清晰的代码（JSON/YAML格式）
- 关注有质量评估机制的仓库
- 选择维护活跃、文档完整的项目

修改记录：
- 2026-04-14: 集成到Clawra系统，与prompt_knowledge_base.py兼容
"""

import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests
import yaml

# 添加当前目录到路径以便导入
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志 - 需要在导入知识库之前配置
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 导入知识库模块
try:
    from prompt_knowledge_base import (
        PromptCategory,
    )
    from prompt_knowledge_base import PromptEntry as KBPromptEntry
    from prompt_knowledge_base import (
        PromptKnowledgeBase,
        PromptSource,
        PromptSubcategory,
        QualityLevel,
    )

    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"无法导入知识库模块: {e}")
    KNOWLEDGE_BASE_AVAILABLE = False
    KNOWLEDGE_BASE_AVAILABLE = False
    # 定义替代类型
    from enum import Enum

    class PromptCategory(Enum):
        TEXT_TO_IMAGE = "text_to_image"
        IMAGE_TO_VIDEO = "image_to_video"
        TEXT_TO_VIDEO = "text_to_video"
        OTHER = "other"

    class PromptSubcategory(Enum):
        GENERAL = "general"
        ANIME = "anime"
        REALISTIC = "realistic"
        PRODUCT = "product"
        LANDSCAPE = "landscape"
        PORTRAIT = "portrait"

    class PromptSource(Enum):
        GITHUB = "github"
        COMMUNITY = "community"
        MANUAL = "manual"
        GENERATED = "generated"

    class QualityLevel(Enum):
        UNRATED = 1
        POOR = 2
        AVERAGE = 3
        GOOD = 4
        EXCELLENT = 5


@dataclass
class GitHubRepo:
    """GitHub仓库信息"""

    name: str
    full_name: str
    description: str
    url: str
    stars: int
    forks: int
    updated_at: str
    language: str
    topics: List[str]


@dataclass
class PromptEntry:
    """提示词条目（中间表示，用于GitHub收集）"""

    id: str  # 唯一标识符
    category: str  # text_to_image, image_to_video, text_to_video
    subcategory: str  # anime, realistic, product, landscape, portrait, etc.
    prompt_text: str  # 原始提示词文本
    parameters: Dict[str, Any]  # 标准化参数（尺寸、模型、风格等）
    model_compatibility: List[str]  # 兼容的模型列表
    quality_score: float  # 质量评分（0-1）
    source: str  # 来源仓库
    source_url: str  # 来源URL
    examples: List[Dict]  # 示例输出信息
    tags: List[str]  # 标签
    created_at: str  # 创建时间
    updated_at: str  # 更新时间

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    def to_kb_prompt_entry(self) -> Any:
        """
        转换为知识库的PromptEntry

        Returns:
            知识库PromptEntry实例（如果知识库可用）
        """
        if not KNOWLEDGE_BASE_AVAILABLE:
            return None

        try:
            # 转换类别
            try:
                kb_category = PromptCategory(self.category)
            except ValueError:
                kb_category = PromptCategory.TEXT_TO_IMAGE

            # 转换子类别
            try:
                kb_subcategory = PromptSubcategory(self.subcategory)
            except ValueError:
                kb_subcategory = PromptSubcategory.GENERAL

            # 转换来源
            try:
                kb_source = PromptSource.GITHUB  # 默认为GitHub
            except ValueError:
                kb_source = PromptSource.GITHUB

            # 转换质量等级
            quality_level = QualityLevel.UNRATED
            if self.quality_score >= 0.8:
                quality_level = QualityLevel.EXCELLENT
            elif self.quality_score >= 0.6:
                quality_level = QualityLevel.GOOD
            elif self.quality_score >= 0.4:
                quality_level = QualityLevel.AVERAGE
            elif self.quality_score >= 0.2:
                quality_level = QualityLevel.POOR
            else:
                quality_level = QualityLevel.UNRATED

            # 创建知识库PromptEntry
            kb_entry = KBPromptEntry(
                id=self.id,
                prompt_text=self.prompt_text,
                category=kb_category,
                subcategory=kb_subcategory,
                model_compatibility=self.model_compatibility,
                parameters=self.parameters,
                base_quality_score=self.quality_score,
                quality_level=quality_level,
                source=kb_source,
                source_url=self.source_url,
                author=self.source,
                examples=self.examples,
                references=[self.source_url],
                language="en",  # 默认为英文
                version="1.0",
            )

            # 添加标签
            for tag in self.tags:
                kb_entry.add_tag(tag)

            return kb_entry

        except Exception as e:
            logger.error(f"转换为知识库PromptEntry失败: {e}")
            return None


class GitHubPromptCollector:
    """GitHub提示词收集器"""

    def __init__(self, github_token: Optional[str] = None):
        """
        初始化收集器

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

        # 搜索关键词
        self.search_keywords = [
            # 文生图
            "stable diffusion prompt",
            "midjourney prompt",
            "dall-e prompt",
            "text-to-image prompt",
            "AI绘画提示词",
            "AI art prompt",
            # 图生视频
            "image-to-video prompt",
            "gen-2 prompt",
            "runwayml prompt",
            "pika labs prompt",
            # 提示词工程
            "prompt engineering",
            "prompt library",
            "prompt collection",
        ]

        # 文件扩展名模式（大小写不敏感）
        self.prompt_file_patterns = [
            "*.json",
            "*.yaml",
            "*.yml",
            "*.txt",
            "*.md",
            "*.csv",
            "*.tsv",
            "*.prompt",
            "*.prompts",
            "*.list",
            "*.data",
            # 大写版本
            "*.JSON",
            "*.YAML",
            "*.YML",
            "*.TXT",
            "*.MD",
            "*.CSV",
            "*.TSV",
        ]

        # 已处理的仓库缓存
        self.processed_repos: Set[str] = set()

        # 收集到的提示词
        self.collected_prompts: List[PromptEntry] = []

    def search_repositories(self, keyword: str, per_page: int = 30) -> List[GitHubRepo]:
        """
        搜索包含关键词的GitHub仓库

        Args:
            keyword: 搜索关键词
            per_page: 每页结果数

        Returns:
            GitHubRepo列表
        """
        url = f"{self.base_url}/search/repositories"
        params = {"q": keyword, "sort": "stars", "order": "desc", "per_page": per_page}

        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            repos = []

            for item in data.get("items", []):
                repo = GitHubRepo(
                    name=item["name"],
                    full_name=item["full_name"],
                    description=item.get("description", ""),
                    url=item["html_url"],
                    stars=item["stargazers_count"],
                    forks=item["forks_count"],
                    updated_at=item["updated_at"],
                    language=item.get("language", ""),
                    topics=item.get("topics", []),
                )
                repos.append(repo)

            logger.info(f"搜索 '{keyword}' 找到 {len(repos)} 个仓库")
            return repos

        except requests.exceptions.RequestException as e:
            logger.error(f"搜索仓库失败: {e}")
            return []

    def get_repo_contents(self, repo_full_name: str, path: str = "") -> List[Dict]:
        """
        获取仓库内容

        Args:
            repo_full_name: 仓库完整名称（owner/repo）
            path: 路径

        Returns:
            内容列表
        """
        url = f"{self.base_url}/repos/{repo_full_name}/contents/{path}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"获取仓库内容失败 {repo_full_name}/{path}: {e}")
            return []

    def download_file(self, download_url: str) -> Optional[str]:
        """
        下载文件内容

        Args:
            download_url: 下载URL

        Returns:
            文件内容或None
        """
        try:
            response = requests.get(download_url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"下载文件失败 {download_url}: {e}")
            return None

    def extract_prompts_from_json(self, content: str, source_info: Dict) -> List[PromptEntry]:
        """
        从JSON文件提取提示词

        Args:
            content: JSON内容
            source_info: 来源信息

        Returns:
            提示词条目列表
        """
        prompts = []

        try:
            data = json.loads(content)

            # 尝试不同格式
            if isinstance(data, list):
                # 格式1: 提示词列表
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        prompt = self._parse_prompt_dict(item, source_info, i)
                        if prompt:
                            prompts.append(prompt)
                    elif isinstance(item, str):
                        # 确定类别
                        category = (
                            self._determine_category(item, source_info)
                            if hasattr(self, "_determine_category")
                            else "text_to_image"
                        )
                        prompt = self._create_prompt_from_text(item, source_info, i, category)
                        if prompt:
                            prompts.append(prompt)

            elif isinstance(data, dict):
                # 格式2: 按类别组织的字典
                for category, items in data.items():
                    if isinstance(items, list):
                        for i, item in enumerate(items):
                            if isinstance(item, dict):
                                prompt = self._parse_prompt_dict(item, source_info, i, category)
                                if prompt:
                                    prompts.append(prompt)
                            elif isinstance(item, str):
                                prompt = self._create_prompt_from_text(
                                    item, source_info, i, category
                                )
                                if prompt:
                                    prompts.append(prompt)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}")

        return prompts

    def extract_prompts_from_yaml(self, content: str, source_info: Dict) -> List[PromptEntry]:
        """
        从YAML文件提取提示词，添加智能过滤排除非提示词YAML文件

        Args:
            content: YAML内容
            source_info: 来源信息

        Returns:
            提示词条目列表
        """
        prompts = []

        try:
            data = yaml.safe_load(content)
            if not data:
                return prompts

            # 检查是否是真正的提示词YAML文件
            # 排除常见的非提示词YAML文件类型
            if isinstance(data, dict):
                # 检查是否是conda环境文件、配置文件等
                conda_keys = {"channels", "dependencies", "name"}
                config_keys = {"version", "config", "settings", "options"}
                docker_keys = {"FROM", "RUN", "COPY", "WORKDIR"}

                data_keys = set(data.keys())

                # 如果包含conda、配置或Docker特定键，跳过处理
                if (data_keys & conda_keys) or (data_keys & config_keys):
                    logger.debug(f"跳过非提示词YAML文件: {source_info.get('filepath', 'unknown')}")
                    return prompts

                # 检查是否有看起来像提示词的数据结构
                # 真正的提示词YAML通常包含"prompts"、"prompt_list"、"examples"等键
                prompt_like_keys = {"prompts", "prompt_list", "examples", "samples", "collection"}
                if not (data_keys & prompt_like_keys):
                    # 如果没有提示词相关键，检查值是否包含提示词
                    # 有些YAML可能直接以类别作为键，值是提示词列表
                    has_prompt_lists = False
                    for key, value in data.items():
                        if isinstance(value, list) and len(value) > 0:
                            # 检查列表中的项是否是字符串或包含prompt字段的字典
                            sample = value[0] if value else None
                            if isinstance(sample, str) and len(sample) > 10:
                                has_prompt_lists = True
                                break
                            elif isinstance(sample, dict) and (
                                "prompt" in sample or "text" in sample
                            ):
                                has_prompt_lists = True
                                break

                    if not has_prompt_lists:
                        logger.debug(
                            f"跳过非提示词YAML字典: {source_info.get('filepath', 'unknown')}"
                        )
                        return prompts

            # YAML处理逻辑类似JSON
            if isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        prompt = self._parse_prompt_dict(item, source_info, i)
                        if prompt:
                            prompts.append(prompt)
                    elif isinstance(item, str):
                        # 检查是否是真正的提示词字符串
                        if len(item) > 10 and not self._is_config_content(item):
                            category = (
                                self._determine_category(item, source_info)
                                if hasattr(self, "_determine_category")
                                else "text_to_image"
                            )
                            prompt = self._create_prompt_from_text(item, source_info, i, category)
                            if prompt:
                                prompts.append(prompt)

            elif isinstance(data, dict):
                for category, items in data.items():
                    if isinstance(items, list):
                        for i, item in enumerate(items):
                            if isinstance(item, dict):
                                prompt = self._parse_prompt_dict(item, source_info, i, category)
                                if prompt:
                                    prompts.append(prompt)
                            elif isinstance(item, str):
                                # 检查是否是真正的提示词字符串
                                if len(item) > 10 and not self._is_config_content(item):
                                    prompt = self._create_prompt_from_text(
                                        item, source_info, i, category
                                    )
                                    if prompt:
                                        prompts.append(prompt)

        except yaml.YAMLError as e:
            logger.warning(f"YAML解析失败: {e}")

        return prompts

    def _is_prompt_file_by_name(self, filename: str) -> bool:
        """
        基于文件名判断是否是提示词文件

        Args:
            filename: 文件名

        Returns:
            True如果是提示词文件
        """
        filename_lower = filename.lower()

        # 文件名中包含提示词关键词
        prompt_keywords = ["prompt", "example", "sample", "collection", "gallery"]
        negative_keywords = ["readme", "license", "changelog", "contributing", "config", "setup"]

        # 检查负面关键词
        if any(neg in filename_lower for neg in negative_keywords):
            return False

        # 检查正面关键词
        if any(keyword in filename_lower for keyword in prompt_keywords):
            return True

        # 特定文件扩展名模式
        if filename_lower.endswith((".prompts.txt", ".prompts.md", "_prompts.txt")):
            return True

        return False

    def _is_likely_prompt_repository(self, repo: GitHubRepo) -> bool:
        """
        评估仓库是否可能包含提示词

        Args:
            repo: GitHub仓库

        Returns:
            True如果可能包含提示词
        """
        # 基于仓库描述的关键词
        prompt_keywords = [
            "prompt",
            "prompts",
            "collection",
            "dataset",
            "library",
            "gallery",
            "example",
            "examples",
            "sample",
            "samples",
            "text-to-image",
            "text-to-video",
            "image-to-video",
            "stable diffusion",
            "midjourney",
            "dall-e",
            "ai art",
            "ai绘画",
        ]

        # 检查描述
        description = (repo.description or "").lower()
        if any(keyword in description for keyword in prompt_keywords):
            return True

        # 检查主题
        topics = [topic.lower() for topic in (repo.topics or [])]
        topic_keywords = ["prompt", "prompts", "ai", "ai-art", "stable-diffusion", "midjourney"]
        if any(any(keyword in topic for keyword in topic_keywords) for topic in topics):
            return True

        # 检查仓库名称
        repo_name = repo.full_name.lower()
        if any(keyword in repo_name for keyword in ["prompt", "prompts", "sd-prompt", "ai-prompt"]):
            return True

        return False

    def extract_prompts_from_text(self, content: str, source_info: Dict) -> List[PromptEntry]:
        """
        从文本文件提取提示词，使用智能过滤排除非提示词内容
        基于文件名应用不同的过滤严格度

        Args:
            content: 文本内容
            source_info: 来源信息（应包含filepath）

        Returns:
            提示词条目列表
        """
        prompts = []
        lines = content.split("\n")
        import re

        # 提示词检测模式 - 结构化格式
        prompt_patterns = [
            # 各种prompt格式（大小写不敏感）
            r"(?i)prompt:\s*(.+)",  # prompt: xxx (不区分大小写)
            r'(?i)"prompt":\s*"([^"]+)"',  # "prompt": "xxx"
            r"(?i)'prompt':\s*'([^']+)'",  # 'prompt': 'xxx'
            r'(?i)prompt":\s*"([^"]+)"',  # prompt": "xxx" (没有外层引号)
            r"(?i)prompt':\s*'([^']+)'",  # prompt': 'xxx'
            r"(?i)text:\s*(.+)",  # text: xxx
            r"(?i)description:\s*(.+)",  # description: xxx
            r"(?i)input:\s*(.+)",  # input: xxx
            r"(?i)caption:\s*(.+)",  # caption: xxx
            r"(?i)positive_prompt:\s*(.+)",  # positive_prompt: xxx
            r"(?i)negative_prompt:\s*(.+)",  # negative_prompt: xxx
            # JSON/YAML样式（键可能没有引号）
            r'(?i)["\']?prompt["\']?\s*:\s*["\']([^"\']+)["\']',  # "prompt": "xxx" 或 'prompt': 'xxx' 或 prompt: "xxx"
            r'(?i)["\']?text["\']?\s*:\s*["\']([^"\']+)["\']',  # "text": "xxx"
            r'(?i)["\']?description["\']?\s*:\s*["\']([^"\']+)["\']',  # "description": "xxx"
        ]

        # 提示词关键词 - 真正的提示词常用词
        prompt_keywords = [
            "image of",
            "photo of",
            "picture of",
            "portrait of",
            "landscape of",
            "drawing of",
            "painting of",
            "illustration of",
            "rendering of",
            "view of",
            "scene of",
            "aesthetic",
            "high quality",
            "highly detailed",
            "8k",
            "4k",
            "ultra detailed",
            "cinematic",
            "professional",
            "artwork",
            "concept art",
            "digital art",
            "watercolor",
            "oil painting",
            # 更多常见提示词词汇
            "masterpiece",
            "best quality",
            "detailed",
            "sharp focus",
            "studio lighting",
            "dramatic lighting",
            "beautiful",
            "stunning",
            "epic",
            "fantasy",
            "sci-fi",
            "cyberpunk",
            "steampunk",
            "anime",
            "cartoon",
            "realistic",
            "hyperrealistic",
            "surreal",
            "abstract",
            "minimalist",
            "vintage",
            "retro",
        ]

        # 基于文件名的过滤严格度调整
        filepath = source_info.get("filepath", "")
        filename = filepath.split("/")[-1] if filepath else ""
        is_likely_prompt_file = self._is_prompt_file_by_name(filename)

        # 如果是提示词文件，应用较宽松的过滤；否则应用较严格的过滤
        if is_likely_prompt_file:
            # 宽松过滤：主要排除明显的非提示词内容
            min_length = 10  # 更短的提示词也接受
            max_length = 500  # 更长的提示词也接受
            strict_exclude = False
        else:
            # 严格过滤：排除更多可能不是提示词的内容
            min_length = 25
            max_length = 300
            strict_exclude = True

        # 排除规则 - 非提示词内容
        exclude_patterns = [
            r"^#+",  # Markdown标题
            r"^<[^>]+>",  # HTML标签
            r"^!\[.*\]\(.*\)",  # Markdown图片
            r"^```",  # 代码块
            r"^\s*$",  # 空行
            r"^[0-9]+\.[0-9]+\.[0-9]+",  # 版本号
            r"^version\s+",  # 版本信息
            r"^copyright",  # 版权信息
            r"^license",  # 许可证
            r"^http[s]?://",  # URL
            r"^@\w+",  # @提及
            r"^\w+/\w+@",  # 包名@版本
            r"^\[.*\]\(.*\)",  # 链接
        ]

        # 排除关键词 - 文档/技术内容（基于严格度调整）
        if strict_exclude:
            # 严格模式：排除更多可能不是提示词的内容
            exclude_keywords = [
                "readme",
                "install",
                "usage",
                "example",
                "documentation",
                "configuration",
                "license",
                "copyright",
                "contributing",
                "changelog",
                "release",
                "version",
                "github",
                "repository",
                "clone",
                "npm",
                "pip",
                "docker",
                "requirements",
                "not ie <= 11",
                "not op_mini all",  # browserslist特定内容
                "setup",
                "test",
                "build",
                "ci",
                "cd",
                "api",
                "endpoint",
                "function",
                "class",
                "import",
                "from",
                "def ",
                "const ",
                "let ",
                "var ",
            ]
        else:
            # 宽松模式：只排除最明显的非提示词内容
            exclude_keywords = [
                "readme",
                "license",
                "copyright",
                "changelog",
                "contributing",
                "not ie <= 11",
                "not op_mini all",
            ]

        for i, line in enumerate(lines):
            line = line.strip()
            if len(line) < min_length or len(line) > max_length:  # 基于文件类型的动态长度范围
                continue

            line_lower = line.lower()

            # 检查排除规则
            if any(re.search(pattern, line_lower) for pattern in exclude_patterns):
                continue

            if any(keyword in line_lower for keyword in exclude_keywords):
                continue

            # 检查是否是真正的提示词
            is_prompt = False
            prompt_text = None

            # 1. 检查模式匹配
            for pattern in prompt_patterns:
                match = re.search(pattern, line_lower)
                if match:
                    is_prompt = True
                    prompt_text = match.group(1).strip()
                    break

            # 2. 检查关键词和启发式规则（如果不是通过模式匹配找到的）
            if not is_prompt:
                # 真正的提示词通常以描述性语言开头
                descriptive_starters = [
                    "a ",
                    "an ",
                    "the ",
                    "in ",
                    "on ",
                    "at ",
                    "with ",
                    "without ",
                    "close-up of",
                    "macro of",
                ]
                starts_with_descriptive = any(
                    line_lower.startswith(starter) for starter in descriptive_starters
                )

                has_prompt_keywords = any(keyword in line_lower for keyword in prompt_keywords)
                has_ai_terms = any(
                    term in line_lower
                    for term in [
                        "stable diffusion",
                        "midjourney",
                        "dall-e",
                        "chatgpt",
                        "ai",
                        "artificial intelligence",
                    ]
                )

                # 额外的启发式：检查是否看起来像自然语言描述
                # 计算单词数（简单的启发式）
                words = line.split()
                word_count = len(words)

                # 检查是否有逗号（提示词常使用逗号分隔修饰词）
                has_commas = "," in line

                # 检查是否包含常见标点但不包含代码符号
                has_normal_punctuation = any(c in line for c in ",.!?")
                has_code_symbols = any(c in line for c in "{}=;:@#$%^&*")

                # 改进的启发式规则：
                # 1. 如果以描述性开头并且有合理的长度，可能是提示词
                # 2. 如果包含提示词关键词并且看起来像自然语言，可能是提示词
                # 3. 如果包含AI术语并且是描述性文本，可能是提示词

                # 计算提示词可能性分数（简单启发式）
                score = 0
                if starts_with_descriptive:
                    score += 2
                if has_prompt_keywords:
                    score += 1
                if has_ai_terms:
                    score += 0.5
                if has_commas:
                    score += 1  # 逗号通常表示修饰词列表
                if 3 <= word_count <= 30:  # 合理的提示词长度范围
                    score += 1
                if not has_code_symbols:
                    score += 1

                # 如果是提示词文件，降低阈值；否则提高阈值
                threshold = 3.0 if is_likely_prompt_file else 4.0

                if score >= threshold:
                    is_prompt = True
                    prompt_text = line
                    # 调试日志
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"启发式匹配: '{line[:50]}...' 分数: {score:.1f}, 阈值: {threshold}"
                        )

            # 3. 额外的质量检查
            if is_prompt and prompt_text:
                # 排除看起来像代码或配置的内容
                if any(
                    indicator in prompt_text.lower()
                    for indicator in [
                        "{",
                        "}",
                        "=",
                        ":",
                        ";",
                        "//",
                        "/*",
                        "*/",
                        "def ",
                        "function ",
                        "class ",
                    ]
                ):
                    continue

                # 排除包含太多特殊字符（可能是代码）
                special_char_count = sum(1 for c in prompt_text if c in "{}[]()<>;:=@#$%^&*")
                if special_char_count > 5:
                    continue

                # 使用原始文本或提取的文本
                final_text = prompt_text if prompt_text != line else line

                # 确定类别 - 改进的分类逻辑
                category = self._determine_category(final_text, source_info)

                prompt = self._create_prompt_from_text(final_text, source_info, i, category)
                if prompt:
                    prompts.append(prompt)

        return prompts

    def _parse_prompt_dict(
        self, data: Dict, source_info: Dict, index: int, category: str = ""
    ) -> Optional[PromptEntry]:
        """
        从字典解析提示词

        Args:
            data: 提示词数据字典
            source_info: 来源信息
            index: 索引
            category: 类别

        Returns:
            PromptEntry或None
        """
        try:
            # 提取提示词文本
            prompt_text = (
                data.get("prompt")
                or data.get("text")
                or data.get("description")
                or data.get("input")
            )
            if not prompt_text or not isinstance(prompt_text, str):
                return None

            # 提取参数
            parameters = {
                "model": data.get("model", "unknown"),
                "size": data.get("size", "512x512"),
                "steps": data.get("steps", 20),
                "cfg_scale": data.get("cfg_scale", 7.5),
                "sampler": data.get("sampler", ""),
                "negative_prompt": data.get("negative_prompt", ""),
                "style": data.get("style", ""),
            }

            # 确定类别
            if not category:
                category = data.get("category", "text_to_image")

            # 确定子类别
            subcategory = data.get("subcategory", "")
            if not subcategory:
                # 从提示词中推断
                prompt_lower = prompt_text.lower()
                if "anime" in prompt_lower or "漫画" in prompt_lower:
                    subcategory = "anime"
                elif (
                    "realistic" in prompt_lower or "real" in prompt_lower or "真实" in prompt_lower
                ):
                    subcategory = "realistic"
                elif "product" in prompt_lower or "产品" in prompt_lower:
                    subcategory = "product"
                elif "landscape" in prompt_lower or "风景" in prompt_lower:
                    subcategory = "landscape"
                elif "portrait" in prompt_lower or "肖像" in prompt_lower:
                    subcategory = "portrait"
                else:
                    subcategory = "general"

            # 生成ID
            prompt_id = f"{source_info['repo'].replace('/', '_')}_{category}_{index}"

            # 质量评分（初步）
            quality_score = self._assess_prompt_quality(prompt_text, data)

            entry = PromptEntry(
                id=prompt_id,
                category=category,
                subcategory=subcategory,
                prompt_text=prompt_text,
                parameters=parameters,
                model_compatibility=[parameters.get("model", "stable-diffusion")],
                quality_score=quality_score,
                source=source_info["repo"],
                source_url=f"{source_info['url']}#L{index}",
                examples=data.get("examples", []),
                tags=data.get("tags", []),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )

            return entry

        except Exception as e:
            logger.warning(f"解析提示词字典失败: {e}")
            return None

    def _create_prompt_from_text(
        self, text: str, source_info: Dict, index: int, category: str = "text_to_image"
    ) -> Optional[PromptEntry]:
        """
        从文本创建提示词条目

        Args:
            text: 提示词文本
            source_info: 来源信息
            index: 索引
            category: 类别

        Returns:
            PromptEntry或None
        """
        try:
            # 清理文本
            text = text.strip()
            if len(text) < 10:  # 太短
                return None

            # 生成ID
            prompt_id = f"{source_info['repo'].replace('/', '_')}_{category}_{index}"

            # 确定子类别
            prompt_lower = text.lower()
            if "anime" in prompt_lower or "漫画" in prompt_lower:
                subcategory = "anime"
            elif "realistic" in prompt_lower or "real" in prompt_lower or "真实" in prompt_lower:
                subcategory = "realistic"
            elif "product" in prompt_lower or "产品" in prompt_lower:
                subcategory = "product"
            elif "landscape" in prompt_lower or "风景" in prompt_lower:
                subcategory = "landscape"
            elif "portrait" in prompt_lower or "肖像" in prompt_lower:
                subcategory = "portrait"
            else:
                subcategory = "general"

            # 质量评分
            quality_score = self._assess_prompt_quality(text, {})

            entry = PromptEntry(
                id=prompt_id,
                category=category,
                subcategory=subcategory,
                prompt_text=text,
                parameters={},
                model_compatibility=["stable-diffusion"],
                quality_score=quality_score,
                source=source_info["repo"],
                source_url=source_info["url"],
                examples=[],
                tags=[],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )

            return entry

        except Exception as e:
            logger.warning(f"从文本创建提示词失败: {e}")
            return None

    def _determine_category(self, text: str, source_info: Dict) -> str:
        """
        根据文本内容确定提示词类别

        Args:
            text: 提示词文本
            source_info: 来源信息

        Returns:
            类别字符串
        """
        text_lower = text.lower()
        source_repo = source_info.get("repo", "").lower()

        # 基于文件名的类别判断
        if source_info.get("filepath", ""):
            filepath = source_info["filepath"].lower()
            if any(keyword in filepath for keyword in ["video", "movie", "clip", "animation"]):
                return "image_to_video"
            elif any(keyword in filepath for keyword in ["image", "photo", "picture", "painting"]):
                return "text_to_image"
            elif any(keyword in filepath for keyword in ["prompt", "prompts", "collection"]):
                return "text_to_image"

        # 基于仓库名称的类别判断
        if any(
            keyword in source_repo
            for keyword in ["video", "animation", "movie", "clip", "gen-2", "runway"]
        ):
            return "image_to_video"
        elif any(
            keyword in source_repo
            for keyword in ["image", "photo", "stable-diffusion", "dall-e", "midjourney"]
        ):
            return "text_to_image"

        # 基于内容的关键词判断
        video_keywords = [
            "video",
            "animation",
            "motion",
            "moving",
            "clip",
            "film",
            "movie",
            "timelapse",
        ]
        image_keywords = [
            "image",
            "photo",
            "picture",
            "painting",
            "drawing",
            "illustration",
            "render",
        ]

        video_count = sum(1 for keyword in video_keywords if keyword in text_lower)
        image_count = sum(1 for keyword in image_keywords if keyword in text_lower)

        if video_count > image_count:
            return "image_to_video"
        else:
            return "text_to_image"  # 默认为文生图

    def _is_config_content(self, text: str) -> bool:
        """
        检查文本是否是配置内容而非提示词

        Args:
            text: 要检查的文本

        Returns:
            True如果是配置内容，False如果是可能的提示词
        """
        text_lower = text.lower()

        # 配置/环境内容的关键词
        config_keywords = [
            "conda-forge",
            "pip",
            "python=",
            "torch",
            "tensorflow",
            "requirements",
            "dependencies",
            "environment",
            "name:",
            "version:",
            "author:",
            "license:",
            "#",
            "//",
            "/*",
            "*/",
            "--",
            "import ",
            "from ",
            "def ",
            "class ",
            "function ",
            "const ",
            "let ",
            "var ",
            "install",
            "setup",
            "build",
            "test",
            "ci/cd",
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "port",
        ]

        # 检查是否是配置内容
        for keyword in config_keywords:
            if keyword in text_lower:
                return True

        # 检查是否包含太多特殊字符（可能是代码）
        special_chars = sum(1 for c in text if c in "{}[]()<>;:=@#$%^&*|\\")
        if special_chars > 3:
            return True

        # 检查是否看起来像URL或路径
        if text_lower.startswith(("http://", "https://", "www.", "ftp://")):
            return True

        if "/" in text and ("." in text.split("/")[-1] or text.count("/") > 2):
            return True

        return False

    def _assess_prompt_quality(self, prompt_text: str, metadata: Dict) -> float:
        """
        评估提示词质量（0-1）

        Args:
            prompt_text: 提示词文本
            metadata: 元数据

        Returns:
            质量评分
        """
        score = 0.5  # 基础分

        # 长度评分
        length = len(prompt_text)
        if 50 <= length <= 300:
            score += 0.2
        elif length > 300:
            score += 0.1

        # 具体性评分（检查是否有具体描述）
        specific_indicators = [
            "highly detailed",
            "detailed",
            "intricate",
            "photorealistic",
            "4k",
            "8k",
            "professional",
            "award-winning",
        ]

        specific_count = sum(
            1 for indicator in specific_indicators if indicator in prompt_text.lower()
        )
        score += min(specific_count * 0.05, 0.2)

        # 结构评分（检查是否有逗号分隔的结构）
        comma_count = prompt_text.count(",")
        if comma_count >= 2:
            score += 0.1

        # 艺术术语评分
        art_terms = ["composition", "lighting", "shadows", "texture", "contrast", "depth"]
        art_count = sum(1 for term in art_terms if term in prompt_text.lower())
        score += min(art_count * 0.03, 0.15)

        # 元数据加分
        if metadata.get("examples"):
            score += 0.1
        if metadata.get("negative_prompt"):
            score += 0.05
        if metadata.get("parameters"):
            score += 0.1

        return min(score, 1.0)  # 确保不超过1.0

    def process_repository(
        self, repo: GitHubRepo, max_files: int = 100, timeout_seconds: int = 120
    ) -> List[PromptEntry]:
        """
        处理单个仓库，提取提示词

        Args:
            repo: GitHub仓库
            max_files: 最大处理文件数
            timeout_seconds: 超时时间（秒）

        Returns:
            提取的提示词列表
        """
        if repo.full_name in self.processed_repos:
            logger.info(f"仓库 {repo.full_name} 已处理，跳过")
            return []

        logger.info(
            f"处理仓库: {repo.full_name} (最大文件数: {max_files}, 超时: {timeout_seconds}秒)"
        )
        self.processed_repos.add(repo.full_name)

        source_info = {"repo": repo.full_name, "url": repo.url, "description": repo.description}

        all_prompts = []
        start_time = time.time()

        # 获取仓库根目录内容
        contents = self.get_repo_contents(repo.full_name)
        if not contents:
            logger.warning(f"仓库 {repo.full_name} 内容为空")
            return []

        # 递归处理文件
        file_queue = [(item, "") for item in contents if item["type"] == "file"]
        dir_queue = [(item, "") for item in contents if item["type"] == "dir"]
        processed_files = 0

        # 限制最大目录深度和文件数
        max_dirs = 50
        dirs_processed = 0

        while dir_queue and dirs_processed < max_dirs:
            # 超时检查
            if time.time() - start_time > timeout_seconds:
                logger.warning(f"仓库 {repo.full_name} 处理超时 ({timeout_seconds}秒)")
                break

            item, base_path = dir_queue.pop(0)
            dir_path = f"{base_path}/{item['name']}" if base_path else item["name"]
            dir_contents = self.get_repo_contents(repo.full_name, dir_path)

            if dir_contents:
                dirs_processed += 1
                for subitem in dir_contents:
                    if subitem["type"] == "file":
                        file_queue.append((subitem, dir_path))
                    elif subitem["type"] == "dir":
                        dir_queue.append((subitem, dir_path))

        logger.info(f"找到 {len(file_queue)} 个文件待处理")

        # 处理文件（限制数量）
        for i, (item, path) in enumerate(file_queue):
            # 超时检查
            if time.time() - start_time > timeout_seconds:
                logger.warning(f"仓库 {repo.full_name} 处理超时 ({timeout_seconds}秒)")
                break

            # 最大文件数限制
            if processed_files >= max_files:
                logger.info(f"达到最大文件数限制: {max_files}")
                break

            file_name = item["name"]
            file_path = f"{path}/{file_name}" if path else file_name

            # 检查文件类型（大小写不敏感）
            file_name_lower = file_name.lower()
            if not any(
                file_name_lower.endswith(ext.replace("*", "").lower())
                for ext in self.prompt_file_patterns
            ):
                continue

            # 下载文件
            content = self.download_file(item["download_url"])
            if not content:
                continue

            # 根据文件类型提取提示词
            prompts = []

            # 创建包含文件路径信息的source_info
            file_source_info = {
                "repo": source_info["repo"],
                "url": source_info["url"],
                "description": source_info["description"],
                "filepath": file_path,  # 添加文件路径信息
            }

            if file_name.endswith(".json"):
                prompts = self.extract_prompts_from_json(content, file_source_info)
            elif file_name.endswith((".yaml", ".yml")):
                prompts = self.extract_prompts_from_yaml(content, file_source_info)
            elif file_name.endswith((".txt", ".md")):
                prompts = self.extract_prompts_from_text(content, file_source_info)

            if prompts:
                logger.info(f"从 {file_path} 提取到 {len(prompts)} 个提示词")
                all_prompts.extend(prompts)

            processed_files += 1

            # 进度报告
            if processed_files % 10 == 0:
                elapsed = time.time() - start_time
                logger.info(
                    f"进度: {processed_files}/{min(len(file_queue), max_files)} 文件, {len(all_prompts)} 提示词, {elapsed:.1f}秒"
                )

            # 遵守GitHub API速率限制
            time.sleep(0.1)

        elapsed = time.time() - start_time
        logger.info(
            f"仓库 {repo.full_name} 处理完成: {processed_files} 文件, {len(all_prompts)} 提示词, {elapsed:.1f}秒"
        )
        return all_prompts

    def collect_prompts(self, max_repos: int = 20, prompts_target: int = 500) -> List[PromptEntry]:
        """
        收集提示词

        Args:
            max_repos: 最大处理仓库数
            prompts_target: 目标提示词数量

        Returns:
            收集到的提示词列表
        """
        logger.info(f"开始收集提示词，目标: {prompts_target}个")

        # 搜索仓库
        all_repos = []
        for keyword in self.search_keywords:
            if len(all_repos) >= max_repos * 2:  # 留出选择空间
                break
            repos = self.search_repositories(keyword, per_page=20)
            all_repos.extend(repos)

        # 去重和排序（按stars）
        unique_repos = {}
        for repo in all_repos:
            if repo.full_name not in unique_repos:
                unique_repos[repo.full_name] = repo

        sorted_repos = sorted(unique_repos.values(), key=lambda x: x.stars, reverse=True)[
            :max_repos
        ]

        # 处理仓库
        total_prompts = []
        for i, repo in enumerate(sorted_repos):
            if len(total_prompts) >= prompts_target:
                logger.info(f"已达到目标提示词数量: {prompts_target}")
                break

            logger.info(f"处理仓库 {i+1}/{len(sorted_repos)}: {repo.full_name}")
            prompts = self.process_repository(repo, max_files=50, timeout_seconds=60)
            total_prompts.extend(prompts)

            # 进度报告
            logger.info(f"当前进度: {len(total_prompts)}/{prompts_target}")

            # 遵守GitHub API速率限制
            time.sleep(1)

        # 去重（基于提示词文本）
        unique_prompts = {}
        for prompt in total_prompts:
            # 简单的文本哈希作为键
            text_hash = hash(prompt.prompt_text[:100])
            if text_hash not in unique_prompts:
                unique_prompts[text_hash] = prompt

        final_prompts = list(unique_prompts.values())

        logger.info(f"收集完成，共获得 {len(final_prompts)} 个唯一提示词")
        return final_prompts

    def save_to_json(self, prompts: List[PromptEntry], output_path: str):
        """
        保存提示词到JSON文件

        Args:
            prompts: 提示词列表
            output_path: 输出路径
        """
        data = [prompt.to_dict() for prompt in prompts]

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"提示词已保存到: {output_path}")
        except Exception as e:
            logger.error(f"保存提示词失败: {e}")

    def import_to_knowledge_base(
        self, prompts: List[PromptEntry], db_path: str = "prompt_knowledge_base.db"
    ) -> int:
        """
        导入提示词到知识库

        Args:
            prompts: 提示词列表
            db_path: 知识库数据库路径

        Returns:
            成功导入的数量
        """
        if not KNOWLEDGE_BASE_AVAILABLE:
            logger.error("知识库模块不可用，无法导入")
            return 0

        try:
            # 创建知识库实例
            kb = PromptKnowledgeBase(db_path)
            imported_count = 0

            for prompt in prompts:
                try:
                    # 转换为知识库格式
                    kb_entry = prompt.to_kb_prompt_entry()
                    if kb_entry and kb.add_prompt(kb_entry):
                        imported_count += 1

                        # 每50条记录日志一次
                        if imported_count % 50 == 0:
                            logger.info(f"已导入 {imported_count}/{len(prompts)} 个提示词")

                except Exception as e:
                    logger.warning(f"导入单个提示词失败 {prompt.id}: {e}")

            kb.close()
            logger.info(f"成功导入 {imported_count}/{len(prompts)} 个提示词到知识库")
            return imported_count

        except Exception as e:
            logger.error(f"导入知识库失败: {e}")
            return 0

    def load_from_json(self, input_path: str) -> List[PromptEntry]:
        """
        从JSON文件加载提示词

        Args:
            input_path: 输入路径

        Returns:
            提示词列表
        """
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            prompts = []
            for item in data:
                # 确保必需字段存在
                required_fields = ["id", "category", "prompt_text"]
                if all(field in item for field in required_fields):
                    # 创建PromptEntry对象
                    prompt = PromptEntry(**item)
                    prompts.append(prompt)

            logger.info(f"从 {input_path} 加载了 {len(prompts)} 个提示词")
            return prompts

        except Exception as e:
            logger.error(f"加载提示词失败: {e}")
            return []


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="GitHub提示词收集器")
    parser.add_argument("--token", help="GitHub API令牌")
    parser.add_argument("--max-repos", type=int, default=20, help="最大处理仓库数")
    parser.add_argument("--target", type=int, default=500, help="目标提示词数量")
    parser.add_argument("--output", default="prompts_collected.json", help="输出文件路径")
    parser.add_argument("--resume", action="store_true", help="继续之前的收集")

    args = parser.parse_args()

    # 创建收集器
    collector = GitHubPromptCollector(github_token=args.token)

    # 检查是否继续
    if args.resume and os.path.exists(args.output):
        print(f"从 {args.output} 继续收集...")
        existing_prompts = collector.load_from_json(args.output)
        collector.collected_prompts = existing_prompts

    # 收集提示词
    prompts = collector.collect_prompts(max_repos=args.max_repos, prompts_target=args.target)

    # 保存结果
    collector.save_to_json(prompts, args.output)

    # 输出统计信息
    print(f"\n=== 收集统计 ===")
    print(f"总提示词数: {len(prompts)}")

    # 按类别统计
    categories = {}
    for prompt in prompts:
        categories[prompt.category] = categories.get(prompt.category, 0) + 1

    print("\n按类别统计:")
    for category, count in categories.items():
        print(f"  {category}: {count}")

    # 质量分布
    quality_levels = {"优秀 (>0.8)": 0, "良好 (0.6-0.8)": 0, "一般 (<0.6)": 0}
    for prompt in prompts:
        if prompt.quality_score > 0.8:
            quality_levels["优秀 (>0.8)"] += 1
        elif prompt.quality_score > 0.6:
            quality_levels["良好 (0.6-0.8)"] += 1
        else:
            quality_levels["一般 (<0.6)"] += 1

    print("\n质量分布:")
    for level, count in quality_levels.items():
        print(f"  {level}: {count}")


if __name__ == "__main__":
    main()
