#!/usr/bin/env python3
"""
最终版GitHub提示词收集器
集成严格提取逻辑和优化搜索策略
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

import requests

# 添加项目路径
sys.path.append(os.path.dirname(__file__))


@dataclass
class FinalGitHubRepo:
    """最终版GitHub仓库信息"""

    full_name: str
    description: Optional[str]
    stars: int
    language: Optional[str]
    topics: List[str] = field(default_factory=list)
    updated_at: str = ""
    fork: bool = False
    size: int = 0


@dataclass
class FinalPromptEntry:
    """最终版提示词条目"""

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
    verification_status: str = "automated"


class StrictPromptExtractor:
    """严格提示词提取器"""

    def __init__(self):
        self.strict_prompt_patterns = [
            r'"([^"]{10,300})"',  # 引号内的文本
            r"prompt:\s*(.+)",  # prompt: 前缀
            r"text:\s*(.+)",  # text: 前缀
            r"description:\s*(.+)",  # description: 前缀
            r"input:\s*(.+)",  # input: 前缀
            r'"prompt"\s*:\s*"([^"]+)"',  # JSON格式
            r'"text"\s*:\s*"([^"]+)"',  # JSON格式
            r'\d+\s*:\s*"([^"]+)"',  # 数组格式
        ]

        self.min_length = 10
        self.max_length = 300

    def extract_prompts(self, text: str) -> List[str]:
        """提取提示词"""
        prompts = []

        # 首先提取Markdown代码块中的内容
        code_block_pattern = r"```(?:\w+)?\n(.*?)```"
        code_blocks = re.findall(code_block_pattern, text, re.DOTALL | re.IGNORECASE)

        for block in code_blocks:
            # 处理代码块 - 提取完整提示词
            lines = block.split("\n")
            prompt_lines = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 如果遇到"Negative:"，处理累积的提示词行
                if line.lower().startswith("negative:"):
                    if prompt_lines:
                        prompt_text = " ".join(prompt_lines)
                        # 验证提示词
                        if self.min_length <= len(
                            prompt_text
                        ) <= self.max_length and self._validate_prompt(prompt_text):
                            prompts.append(prompt_text)
                        prompt_lines = []
                    continue

                # 检查是否匹配严格模式（可能在行内）
                matched = False
                for pattern in self.strict_prompt_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match and len(match.groups()) > 0:
                        prompt_text = match.group(1).strip()
                        if self.min_length <= len(
                            prompt_text
                        ) <= self.max_length and self._validate_prompt(prompt_text):
                            prompts.append(prompt_text)
                            matched = True
                            break

                if not matched:
                    # 累积行用于描述性提示词检查
                    prompt_lines.append(line)

            # 处理代码块末尾剩余的累积行（如果没有"Negative:"）
            if prompt_lines:
                prompt_text = " ".join(prompt_lines)
                if (
                    len(prompt_text) >= self.min_length
                    and self._is_descriptive_prompt(prompt_text)
                    and self._validate_prompt(prompt_text)
                ):
                    prompts.append(prompt_text)

        # 如果代码块中没有找到提示词，回退到原始的行处理
        if not prompts:
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 模式匹配
                for pattern in self.strict_prompt_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match and len(match.groups()) > 0:
                        prompt_text = match.group(1).strip()
                        if self.min_length <= len(prompt_text) <= self.max_length:
                            # 验证提示词
                            if self._validate_prompt(prompt_text):
                                prompts.append(prompt_text)
                                break

                # 如果没有模式匹配，检查描述性提示词
                if len(line) >= self.min_length and self._is_descriptive_prompt(line):
                    # 描述性提示词也需要验证
                    if self._validate_prompt(line):
                        prompts.append(line)

        return prompts

    def _validate_prompt(self, text: str) -> bool:
        """验证提示词"""
        text_lower = text.lower()

        # 排除非提示词内容
        non_prompt = [
            "http://",
            "https://",
            "www.",
            ".com",
            ".org",
            ".net",
            "browserslist",
            "not ie <=",
            "def ",
            "function ",
            "class ",
            "import ",
            "export ",
            "install ",
            "setup ",
            "configuration",
            "license",
            "repository",
            "collection",
            "notebook",
            "technique",
            "transform",
            "create",
            "generate",
            "control",
            "movement",
            "ws://",
            "api/",
            "endpoint",
            "route",
            # 技术文档词汇
            "parameter",
            "parameterization",
            "required",
            "optional",
            "default",
            "browser",
            "startup",
            "warrant",
            "warranty",
            "condition",
            "basis",
            "models",
            "version",
            "update",
            "change",
            "bug",
            "fix",
            "issue",
            "pull request",
            "commit",
            "merge",
            "branch",
            "release",
            "dependency",
            "package",
            "npm",
            "yarn",
            "pip",
            "install",
            "documentation",
            "readme",
            "changelog",
            "contributing",
            "license",
            "mit",
            "apache",
            "gpl",
            "copyright",
            "author",
            "test",
            "testing",
            "unit test",
            "integration",
            "ci",
            "cd",
            "docker",
            "container",
            "kubernetes",
            "deploy",
            "production",
            "development",
            "environment",
            "variable",
            "config",
            "setting",
            "log",
            "debug",
            "error",
            "warning",
            "info",
            "exception",
            "stack",
            "trace",
            "crash",
            "failure",
            "success",
            "status",
            "code",
            "source",
            "binary",
            "executable",
            "compiler",
            "interpreter",
            # 更多技术文档词汇
            "caching",
            "cache",
            "database",
            "query",
            "queries",
            "redis",
            "application",
            "layer",
            "error",
            "errors",
            "fail",
            "fails",
            "failure",
            "failures",
            "invalidation",
            "stale",
            "indication",
            "gracefully",
            "logged",
            "break",
            "means",
            "data",
            "remain",
            "changelog",
            "keep a changelog",
            "based on",
            "all notable changes",
            # 系统和技术术语
            "system",
            "software",
            "hardware",
            "network",
            "server",
            "client",
            "user",
            "users",
            "admin",
            "administrator",
            "permission",
            "authentication",
            "authorization",
            "security",
            "encryption",
            "performance",
            "optimization",
            "scalability",
            "reliability",
            "availability",
            "maintenance",
            "backup",
            "restore",
            "recovery",
            # 项目管理术语
            "project",
            "task",
            "milestone",
            "deadline",
            "schedule",
            "budget",
            "resource",
            "team",
            "collaboration",
            "communication",
            "meeting",
            "agenda",
            "minutes",
            "report",
            "dashboard",
            "metrics",
        ]

        if any(indicator in text_lower for indicator in non_prompt):
            return False

        # 检查句子结构
        sentence_indicators = [
            " is ",
            " are ",
            " was ",
            " were ",
            " has ",
            " have ",
            " do ",
            " does ",
            " can ",
            " could ",
            " will ",
            " would ",
            " should ",
            " must ",
            " may ",
            " might ",
        ]
        if any(indicator in text_lower for indicator in sentence_indicators):
            return False

        # 检查动词开头
        verb_starts = [
            "create",
            "generate",
            "transform",
            "install",
            "use",
            "download",
            "configure",
            "setup",
            "run",
            "execute",
        ]
        first_word = text_lower.split()[0] if text_lower.split() else ""
        if first_word in verb_starts:
            return False

        # 检查是否为单个单词
        words = text.split()
        if len(words) < 3:
            return False

        # 检查是否全大写（可能是错误消息或代码）
        if text.isupper():
            return False

        # 检查是否看起来像代码标识符（驼峰命名或下划线命名）
        # 如 imageCount、description、error_message
        if re.match(r"^[a-z]+[A-Z]", text) or "_" in text:
            # 但允许一些常见的下划线用法
            if not ("_of_" in text_lower or "_with_" in text_lower or "_in_" in text_lower):
                return False

        # 检查日期时间格式
        date_patterns = [
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
            r"\d{2}/\d{2}/\d{4}",
        ]
        for pattern in date_patterns:
            if re.search(pattern, text):
                return False

        # 检查是否包含AI提示词常见特征
        prompt_features = [
            "quality",
            "detailed",
            "masterpiece",
            "professional",
            "intricate",
            "sharp",
            "cinematic",
            "epic",
            "beautiful",
            "stunning",
            "amazing",
            "gorgeous",
            "4k",
            "8k",
            "hd",
            "trending",
            "artstation",
            "unreal",
            "octane",
            "vray",
            "high quality",
            "in the style of",
            "by artist",
            # 视觉相关词汇
            "image",
            "photo",
            "picture",
            "portrait",
            "landscape",
            "scene",
            "view",
            "art",
            "painting",
            "illustration",
            "digital art",
            "concept art",
            "drawing",
            "sketch",
            "render",
            "visual",
            "graphic",
            "design",
            "composition",
            "background",
            "foreground",
            "subject",
            "object",
            "character",
            "creature",
            "monster",
            "animal",
            "human",
            "person",
            "woman",
            "man",
            "girl",
            "boy",
            "child",
            "adult",
            "face",
            "head",
            "body",
            "hand",
            "eye",
            "hair",
            "nature",
            "forest",
            "mountain",
            "river",
            "ocean",
            "sky",
            "cloud",
            "sun",
            "moon",
            "star",
            "space",
            "city",
            "building",
            "house",
            "room",
            "interior",
            "exterior",
            "architecture",
            "structure",
            "vehicle",
            "car",
            "boat",
            "airplane",
            "spaceship",
            "robot",
            "fantasy",
            "sci-fi",
            "cyberpunk",
            "steampunk",
            "medieval",
            "futuristic",
            "post-apocalyptic",
            "dystopian",
            "utopian",
        ]

        has_prompt_feature = any(feature in text_lower for feature in prompt_features)

        # 检查描述性结构
        descriptive_structures = [
            " of ",
            " with ",
            " in ",
            " on ",
            " at ",
            " by ",
            " for ",
            " and ",
            " or ",
            " but ",
            ", ",
            " - ",
            " -- ",
        ]
        has_descriptive_structure = any(struct in text for struct in descriptive_structures)

        # 如果没有提示词特征也没有描述性结构，可能是非提示词
        if not has_prompt_feature and not has_descriptive_structure:
            return False

        # 最终检查：是否为真正的图像生成提示词
        if not self._is_image_generation_prompt(text):
            return False

        return True

    def _is_descriptive_prompt(self, text: str) -> bool:
        """检查是否为描述性提示词"""
        text_lower = text.lower()

        # 描述性开头 - 扩展列表以涵盖更多图像生成提示词
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
            "raw photo",
            "professional headshot",
            "oil painting",
            "fantasy",
            "high fashion",
            "editorial",
            "digital art",
            "concept art",
            "character design",
            "environment art",
            "masterpiece",
            "ultra-detailed",
            "high quality",
            "cinematic",
            "photorealistic",
            "realistic",
            "stylized",
            "minimalist",
            "abstract",
            "surreal",
            "impressionist",
        ]

        # 检查是否以描述性开头开头
        has_descriptive_start = any(text_lower.startswith(start) for start in descriptive_starts)

        # 合理的长度
        words = text.split()
        if len(words) < 3 or len(words) > 50:
            return False

        # 包含逗号（修饰词列表）或常见质量关键词
        has_commas = "," in text
        has_quality_keywords = any(
            kw in text_lower for kw in ["detailed", "quality", "resolution", "masterpiece", "high"]
        )

        # 如果文本以描述性开头开头，或者包含质量关键词和逗号，则认为是描述性提示词
        return has_descriptive_start or (has_commas and has_quality_keywords)

    def _is_image_generation_prompt(self, text: str) -> bool:
        """检查是否为图像生成提示词"""
        text_lower = text.lower()
        words = text.split()

        # 长度检查：图像提示词通常在5-50个单词之间
        if len(words) < 5 or len(words) > 50:
            return False

        # 检查是否包含视觉描述词汇
        visual_keywords = [
            "image",
            "photo",
            "picture",
            "portrait",
            "landscape",
            "scene",
            "view",
            "art",
            "painting",
            "illustration",
            "digital art",
            "concept art",
            "drawing",
            "sketch",
            "render",
            "visual",
            "graphic",
            "composition",
            "background",
            "foreground",
            "subject",
            "object",
            "character",
            "creature",
            "monster",
            "animal",
            "human",
            "person",
            "woman",
            "man",
            "girl",
            "boy",
            "child",
            "adult",
            "face",
            "head",
            "body",
            "hand",
            "eye",
            "nature",
            "forest",
            "mountain",
            "river",
            "ocean",
            "sky",
            "cloud",
            "sun",
            "moon",
            "star",
            "space",
            "city",
            "building",
            "house",
            "room",
            "architecture",
            "structure",
            "vehicle",
            "car",
            "boat",
            "airplane",
            "spaceship",
            "robot",
            "fantasy",
            "sci-fi",
            "cyberpunk",
            "steampunk",
            "medieval",
            "futuristic",
            "post-apocalyptic",
            "dystopian",
        ]

        has_visual_keyword = any(keyword in text_lower for keyword in visual_keywords)

        # 检查是否包含质量修饰词
        quality_keywords = [
            "masterpiece",
            "detailed",
            "high quality",
            "professional",
            "intricate",
            "sharp",
            "cinematic",
            "epic",
            "beautiful",
            "stunning",
            "amazing",
            "gorgeous",
            "4k",
            "8k",
            "hd",
            "high resolution",
            "trending",
            "artstation",
            "unreal engine",
            "octane render",
            "vray",
        ]

        has_quality_keyword = any(keyword in text_lower for keyword in quality_keywords)

        # 检查是否包含艺术风格指示
        style_keywords = [
            "in the style of",
            "by artist",
            "style of",
            "inspired by",
            "digital painting",
            "oil painting",
            "watercolor",
            "sketch",
            "charcoal",
            "pencil",
            "ink",
            "vector",
            "pixel art",
            "3d",
            "isometric",
            "low poly",
            "flat design",
            "minimalist",
        ]

        has_style_keyword = any(keyword in text_lower for keyword in style_keywords)

        # 至少满足两个条件：视觉关键词 + (质量关键词 或 风格关键词)
        if not has_visual_keyword:
            return False

        if not (has_quality_keyword or has_style_keyword):
            return False

        # 检查结构：通常包含逗号分隔的修饰词列表
        if "," not in text:
            return False

        # 排除命令式文本
        command_starts = [
            "open",
            "navigate",
            "click",
            "press",
            "select",
            "choose",
            "enter",
            "type",
            "input",
            "output",
            "save",
            "load",
            "export",
            "import",
            "download",
            "upload",
            "install",
            "configure",
            "setup",
            "run",
            "execute",
            "start",
            "stop",
            "do not",
            "don't",
            "please",
            "should",
            "must",
            "need",
        ]

        first_word = words[0].lower()
        if first_word in command_starts:
            return False

        # 排除UI标签和选项文本（包含省略号、冒号、括号）
        if "..." in text or ":" in text or "(" in text or ")" in text:
            # 但允许括号用于权重说明，如 (masterpiece:1.2)
            # 检查是否看起来像权重说明
            if re.search(r"\([^)]*:\d+(\.\d+)?\)", text):
                # 这是权重说明，允许
                pass
            else:
                # 可能是UI标签
                return False

        # 排除许可证和法律文本
        legal_terms = [
            "license",
            "warranty",
            "copyright",
            "terms of service",
            "privacy policy",
            "as is",
            "without warranty",
            "express or implied",
            "liable",
            "damages",
        ]
        if any(term in text_lower for term in legal_terms):
            return False

        # 排除技术文档和系统文本
        technical_terms = [
            "caching",
            "cache",
            "database",
            "query",
            "queries",
            "redis",
            "application",
            "layer",
            "error",
            "errors",
            "fail",
            "fails",
            "failure",
            "failures",
            "invalidation",
            "stale",
            "indication",
            "gracefully",
            "logged",
            "break",
            "means",
            "data",
            "remain",
            "changelog",
            "keep a changelog",
            "based on",
            "the format is based",
            "all notable changes",
            "system",
            "software",
            "hardware",
            "network",
            "server",
            "client",
            "user",
            "users",
            "admin",
            "administrator",
            "permission",
            "authentication",
            "authorization",
            "security",
            "encryption",
            "performance",
            "optimization",
            "scalability",
            "reliability",
            "availability",
            "maintenance",
            "backup",
            "restore",
            "recovery",
            "project",
            "task",
            "milestone",
            "deadline",
            "schedule",
            "budget",
            "resource",
            "team",
            "collaboration",
            "communication",
        ]
        if any(term in text_lower for term in technical_terms):
            return False

        # 通过所有检查
        return True


class FinalGitHubPromptCollector:
    """最终版GitHub提示词收集器"""

    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ClawraPromptCollector/1.0",
        }
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"

        self.base_url = "https://api.github.com"
        self.extractor = StrictPromptExtractor()

        # 专注于文生图的搜索关键词
        self.search_keywords = [
            "stable diffusion prompt collection",
            "midjourney prompt library",
            "DALL-E prompts json",
            "AI art prompts dataset",
            "text-to-image prompt collection",
            "generative art prompts",
            "AI image generation prompts",
            "prompt engineering examples",
        ]

        # 配置
        self.timeout_seconds = 60
        self.max_repos = 5
        self.max_files_per_repo = 20

        # 日志
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # 已知高质量提示词仓库列表
        self.known_prompt_repos = [
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
            # 新发现的仓库
            (
                "rockbenben/img-prompt",
                "AI Image Prompt Generator with 5000+ prompts in 18 languages",
            ),
            (
                "526christian/AI-Image-PromptGenerator",
                "A flexible UI script to help create and expand on prompts",
            ),
            ("LearnPrompt/LearnPrompt", "免费开源AIGC课程，包含提示词示例"),
            ("altryne/awesome-ai-art-image-synthesis", "AI艺术资源列表，可能包含提示词"),
            ("promptslab/Awesome-Prompt-Engineering", "提示工程资源，包含示例"),
            # 从搜索中发现的高质量仓库
            (
                "Avaray/stable-diffusion-simple-wildcards",
                "稳定扩散简单通配符，包含艺术家和风格列表",
            ),
        ]

    def search_repositories(self, keyword: str) -> List[FinalGitHubRepo]:
        """搜索仓库"""
        url = f"{self.base_url}/search/repositories"
        params = {"q": keyword, "sort": "updated", "order": "desc", "per_page": 10}

        try:
            self.logger.info(f"搜索: {keyword}")
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()

            items = response.json().get("items", [])
            repos = []

            for item in items:
                # 过滤：排除fork和小仓库
                if item.get("fork", False) or item.get("size", 0) < 100:
                    continue

                # 检查描述或主题是否包含提示词相关关键词
                desc = item.get("description", "").lower()
                topics = [t.lower() for t in item.get("topics", [])]
                combined_text = desc + " " + " ".join(topics)

                # 严格过滤：只接受文生图相关的仓库
                image_gen_keywords = [
                    "stable diffusion",
                    "midjourney",
                    "dall-e",
                    "text-to-image",
                    "ai art",
                    "generative art",
                    "image generation",
                ]
                # 排除关键词
                exclude_keywords = [
                    "marketing",
                    "coding",
                    "developer",
                    "programming",
                    "chatgpt",
                    "llm",
                    "language model",
                ]

                has_image_gen = any(keyword in combined_text for keyword in image_gen_keywords)
                has_exclude = any(keyword in combined_text for keyword in exclude_keywords)

                if not has_image_gen or has_exclude:
                    continue

                repo = FinalGitHubRepo(
                    full_name=item["full_name"],
                    description=item.get("description"),
                    stars=item.get("stargazers_count", 0),
                    language=item.get("language"),
                    topics=item.get("topics", []),
                    updated_at=item.get("updated_at", ""),
                    fork=item.get("fork", False),
                    size=item.get("size", 0),
                )

                repos.append(repo)
                self.logger.debug(f"接受仓库: {repo.full_name}")

            self.logger.info(f"找到 {len(repos)} 个仓库")
            return repos

        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            return []

    def search_code_for_prompts(self) -> List[FinalGitHubRepo]:
        """使用代码搜索API查找包含提示词的文件"""
        url = f"{self.base_url}/search/code"

        # 搜索包含图像生成提示词的文件
        # 使用更简单的查询语法，避免422错误
        queries = [
            # 简单查询：搜索JSON文件中包含"prompt"字段的内容
            "prompt extension:json stable-diffusion",
            "prompt extension:json midjourney",
            "prompt extension:json dall-e",
            # 搜索文本文件中的提示词
            "masterpiece extension:txt",
            "high quality extension:txt",
            "detailed extension:txt",
            # 搜索Markdown文件中的提示词集合
            "stable diffusion prompts extension:md",
            "midjourney prompts extension:md",
            # 更广泛的搜索
            "text-to-image prompts",
            "ai art prompts",
            "generative art prompts",
        ]

        repos = []
        processed_repos = set()

        for query in queries:
            params = {"q": query, "sort": "updated", "order": "desc", "per_page": 10}

            try:
                self.logger.info(f"代码搜索: {query}")
                response = requests.get(url, params=params, headers=self.headers, timeout=30)
                response.raise_for_status()

                items = response.json().get("items", [])

                for item in items:
                    repo_full_name = item["repository"]["full_name"]

                    # 跳过已处理的仓库
                    if repo_full_name in processed_repos:
                        continue

                    # 获取仓库信息
                    repo_info_url = f"{self.base_url}/repos/{repo_full_name}"
                    repo_response = requests.get(repo_info_url, headers=self.headers, timeout=10)

                    if repo_response.status_code == 200:
                        repo_data = repo_response.json()

                        # 检查仓库是否与图像生成相关
                        desc = repo_data.get("description") or ""
                        desc_lower = desc.lower()
                        topics = [t.lower() for t in repo_data.get("topics", [])]
                        combined_text = desc_lower + " " + " ".join(topics)

                        # 检查图像生成关键词 - 更严格的要求
                        image_gen_keywords = [
                            "stable diffusion",
                            "midjourney",
                            "dall-e",
                            "text-to-image",
                            "ai art",
                            "generative art",
                            "image generation",
                            "prompt",
                            "artificial intelligence art",
                            "ai image",
                            "text2image",
                        ]
                        # 排除关键词 - 更广泛的排除
                        exclude_keywords = [
                            "marketing",
                            "coding",
                            "developer",
                            "programming",
                            "chatgpt",
                            "llm",
                            "language model",
                            "tutorial",
                            "course",
                            "learning",
                            "guide",
                            "documentation",
                            "api",
                            "webui",
                            "interface",
                            "tool",
                            "utility",
                            "application",
                        ]

                        has_image_gen = any(
                            keyword in combined_text for keyword in image_gen_keywords
                        )
                        has_exclude = any(keyword in combined_text for keyword in exclude_keywords)

                        if not has_image_gen or has_exclude:
                            continue

                        repo = FinalGitHubRepo(
                            full_name=repo_data["full_name"],
                            description=repo_data.get("description"),
                            stars=repo_data.get("stargazers_count", 0),
                            language=repo_data.get("language"),
                            topics=repo_data.get("topics", []),
                            updated_at=repo_data.get("updated_at", ""),
                            fork=repo_data.get("fork", False),
                            size=repo_data.get("size", 0),
                        )

                        repos.append(repo)
                        processed_repos.add(repo_full_name)
                        self.logger.debug(f"通过代码搜索找到仓库: {repo.full_name}")

            except Exception as e:
                self.logger.error(f"代码搜索失败 {query}: {e}")
                continue

        self.logger.info(f"代码搜索完成，找到 {len(repos)} 个仓库")
        return repos

    def get_repo_files(self, repo_full_name: str) -> List[Dict[str, Any]]:
        """获取仓库文件列表"""
        url = f"{self.base_url}/repos/{repo_full_name}/contents"

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.error(f"获取文件列表失败: {e}")

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

    def get_file_content_for_item(self, item: Dict[str, Any], repo_full_name: str) -> Optional[str]:
        """获取文件内容，处理多种来源"""
        # 方法1: 使用download_url（如果存在）
        if "download_url" in item and item["download_url"]:
            content = self.download_file(item["download_url"])
            if content:
                return content

        # 方法2: 使用raw.githubusercontent.com
        # 构造原始URL: https://raw.githubusercontent.com/{repo}/{branch}/{path}
        default_branch = "main"  # 假设main分支
        file_path = item.get("path", item.get("name", ""))
        if file_path:
            raw_url = (
                f"https://raw.githubusercontent.com/{repo_full_name}/{default_branch}/{file_path}"
            )
            content = self.download_file(raw_url)
            if content:
                return content

        # 方法3: 使用GitHub API端点
        if "url" in item:
            try:
                response = requests.get(item["url"], headers=self.headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    # 内容可能是base64编码
                    if "content" in data and data.get("encoding") == "base64":
                        import base64

                        return base64.b64decode(data["content"]).decode("utf-8")
                    elif "content" in data:
                        return data["content"]
            except Exception as e:
                self.logger.error(f"API下载失败: {e}")

        return None

    def _process_repository_contents(
        self,
        repo_full_name: str,
        path: str,
        start_time: float,
        prompts: List[FinalPromptEntry],
        repo: FinalGitHubRepo,
    ) -> int:
        """递归处理仓库内容"""
        files_processed = 0

        # 获取当前路径下的内容
        url = (
            f"{self.base_url}/repos/{repo_full_name}/contents/{path}"
            if path
            else f"{self.base_url}/repos/{repo_full_name}/contents"
        )
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code != 200:
                self.logger.debug(f"获取路径 {path} 失败: {response.status_code}")
                return 0

            contents = response.json()
        except Exception as e:
            self.logger.debug(f"获取路径 {path} 异常: {e}")
            return 0

        for item in contents:
            if time.time() - start_time > self.timeout_seconds:
                self.logger.warning("处理超时")
                break

            if item["type"] == "dir":
                # 递归处理子目录
                dir_name = item["name"].lower()
                dir_path = item["path"]

                # 优先处理包含prompt的目录，也处理所有非.git目录
                if "prompt" in dir_name or not dir_name.startswith("."):
                    # 如果目录包含'prompt'，日志记录
                    if "prompt" in dir_name:
                        self.logger.debug(f"处理提示词目录: {dir_path}")
                    sub_files = self._process_repository_contents(
                        repo_full_name, dir_path, start_time, prompts, repo
                    )
                    files_processed += sub_files
                else:
                    self.logger.debug(f"跳过目录: {dir_path}")
            elif item["type"] == "file":
                filename = item["name"].lower()

                # 处理可能包含提示词的文件类型
                # 优先处理文件名包含"prompt"的文件
                is_prompt_file = "prompt" in filename
                valid_extensions = (
                    ".json",
                    ".txt",
                    ".md",
                    ".yaml",
                    ".yml",
                    ".js",
                    ".py",
                    ".csv",
                    ".tsv",
                )

                if not (is_prompt_file or filename.endswith(valid_extensions)):
                    continue

                # 排除README和LICENSE
                if "readme" in filename or "license" in filename:
                    continue

                # 下载文件
                content = self.get_file_content_for_item(item, repo_full_name)
                if not content:
                    self.logger.debug(f"无法下载文件: {item['name']}")
                    continue

                # 提取提示词
                file_prompts = self.extract_prompts_from_content(content, repo, item["name"])
                if file_prompts:
                    prompts.extend(file_prompts)
                    files_processed += 1
                    self.logger.debug(f"文件 {item['path']}: 提取到 {len(file_prompts)} 个提示词")

        return files_processed

    def process_repository(self, repo: FinalGitHubRepo) -> List[FinalPromptEntry]:
        """处理仓库"""
        self.logger.info(f"处理仓库: {repo.full_name}")
        start_time = time.time()

        prompts = []

        try:
            # 递归处理仓库内容
            files_processed = self._process_repository_contents(
                repo.full_name, "", start_time, prompts, repo
            )

            elapsed = time.time() - start_time
            self.logger.info(
                f"处理完成: {files_processed} 个文件, {len(prompts)} 个提示词, 耗时: {elapsed:.1f}秒"
            )

        except Exception as e:
            self.logger.error(f"处理仓库异常: {e}")

        return prompts

    def extract_prompts_from_content(
        self, content: str, repo: FinalGitHubRepo, filename: str
    ) -> List[FinalPromptEntry]:
        """从内容中提取提示词"""
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
                verification_status="automated",
            )

            prompts.append(prompt)

        return prompts

    def _determine_category(self, prompt_text: str) -> Tuple[str, str]:
        """确定类别"""
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
        """计算质量分数"""
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

    def collect_from_known_repos(self, max_repos: Optional[int] = None) -> List[FinalPromptEntry]:
        """从已知仓库收集提示词"""
        all_prompts = []

        limit = max_repos or len(self.known_prompt_repos)
        repos_to_process = self.known_prompt_repos[:limit]

        self.logger.info(f"从 {len(repos_to_process)} 个已知仓库收集提示词")

        for repo_full_name, description in repos_to_process:
            try:
                self.logger.info(f"处理已知仓库: {repo_full_name} - {description}")

                # 创建仓库对象
                repo = self.get_repo_info(repo_full_name)
                if not repo:
                    self.logger.warning(f"无法获取仓库信息: {repo_full_name}")
                    continue

                prompts = self.process_repository(repo)
                if prompts:
                    all_prompts.extend(prompts)
                    self.logger.info(
                        f"  提取到 {len(prompts)} 个提示词，累计 {len(all_prompts)} 个"
                    )
                else:
                    self.logger.warning(f"  未提取到提示词")
            except Exception as e:
                self.logger.error(f"处理仓库 {repo_full_name} 失败: {e}")

        self.logger.info(f"从已知仓库收集完成，共提取 {len(all_prompts)} 个提示词")
        return all_prompts

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

    def collect_prompts(self) -> List[FinalPromptEntry]:
        """收集提示词"""
        all_prompts = []

        self.logger.info("开始收集提示词")

        # 首先从已知仓库收集（质量更高）
        self.logger.info("阶段1: 从已知高质量仓库收集")
        known_prompts = self.collect_from_known_repos(max_repos=3)  # 先处理3个已知仓库
        all_prompts.extend(known_prompts)

        self.logger.info(f"已知仓库收集完成，已收集 {len(known_prompts)} 个提示词")

        # 如果还不够，使用搜索方法
        if len(all_prompts) < 200:  # 目标至少200个提示词
            self.logger.info("阶段2: 使用搜索方法补充收集")

            # 方法1：使用代码搜索API查找包含提示词的文件
            self.logger.info("方法1: 使用代码搜索API")
            code_search_repos = self.search_code_for_prompts()

            # 方法2：传统仓库描述搜索（备用）
            self.logger.info("方法2: 传统仓库描述搜索")
            all_repos = []
            for keyword in self.search_keywords:
                repos = self.search_repositories(keyword)
                all_repos.extend(repos)

                if len(all_repos) >= self.max_repos * 2:
                    break

            # 合并搜索结果
            all_repos.extend(code_search_repos)

            # 去重
            unique_repos = {}
            for repo in all_repos:
                if repo.full_name not in unique_repos:
                    unique_repos[repo.full_name] = repo

            repos_list = list(unique_repos.values())[: self.max_repos]

            self.logger.info(
                f"搜索找到 {len(repos_list)} 个仓库 (代码搜索: {len(code_search_repos)}, 传统搜索: {len(all_repos) - len(code_search_repos)})"
            )

            # 处理仓库
            for i, repo in enumerate(repos_list):
                self.logger.info(f"处理仓库 {i+1}/{len(repos_list)}: {repo.full_name}")

                prompts = self.process_repository(repo)
                if prompts:
                    all_prompts.extend(prompts)
                    self.logger.info(
                        f"  提取到 {len(prompts)} 个提示词，累计 {len(all_prompts)} 个"
                    )

                # 如果已经达到目标，提前停止
                if len(all_prompts) >= 500:
                    self.logger.info(f"已达到目标数量 ({len(all_prompts)} 个提示词)，停止收集")
                    break

        self.logger.info(f"收集完成，共提取 {len(all_prompts)} 个提示词")
        return all_prompts


def main():
    """主函数"""
    print("=== 最终版GitHub提示词收集器 ===")

    # 设置日志
    logging.basicConfig(level=logging.INFO)

    collector = FinalGitHubPromptCollector()

    # 检查API限制
    try:
        response = requests.get("https://api.github.com/rate_limit", headers=collector.headers)
        if response.status_code == 200:
            limits = response.json()["resources"]["core"]
            print(f"API速率限制: {limits['remaining']}/{limits['limit']}")
    except Exception as e:
        print(f"速率限制检查失败: {e}")

    # 收集提示词
    print("\n开始收集提示词...")
    prompts = collector.collect_prompts()

    print(f"\n收集完成，共提取 {len(prompts)} 个提示词")

    if prompts:
        print("\n前10个提示词:")
        for i, prompt in enumerate(prompts[:10]):
            print(f"  {i+1}. {prompt.prompt_text[:80]}...")
            print(f"     类别: {prompt.category}, 子类别: {prompt.subcategory}")
            print(f"     质量: {prompt.quality_score:.2f}, 来源: {prompt.source}")

        # 保存到文件
        output_file = "final_collected_prompts.json"
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
        print(f"\n✅ 成功！收集到 {len(prompts)} 个高质量提示词")
        sys.exit(0)
    else:
        print(f"\n⚠️  未收集到提示词")
        sys.exit(1)
