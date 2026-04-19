#!/usr/bin/env python3
"""
提示词知识库核心模块

功能：
1. 结构化提示词存储和管理
2. 智能分类和标签系统
3. 质量评估和评分
4. 高级检索和推荐
5. 使用统计和优化

设计原则：
- 高性能：支持快速检索和过滤
- 可扩展：易于添加新的类别和功能
- 数据驱动：基于使用反馈持续优化
- 兼容性：与ROMA框架和现有系统集成
"""

import hashlib
import json
import logging
import os
import pickle
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PromptCategory(Enum):
    """提示词类别枚举"""

    TEXT_TO_IMAGE = "text_to_image"  # 文生图
    IMAGE_TO_VIDEO = "image_to_video"  # 图生视频
    TEXT_TO_VIDEO = "text_to_video"  # 文生视频
    VIDEO_EDITING = "video_editing"  # 视频剪辑
    CONTENT_REWRITE = "content_rewrite"  # 内容重写
    CODE_GENERATION = "code_generation"  # 代码生成
    DATA_ANALYSIS = "data_analysis"  # 数据分析
    OTHER = "other"  # 其他


class PromptSubcategory(Enum):
    """提示词子类别枚举"""

    # 文生图子类别
    REALISTIC = "realistic"  # 写实
    ANIME = "anime"  # 动漫
    ARTISTIC = "artistic"  # 艺术
    PRODUCT = "product"  # 产品
    LANDSCAPE = "landscape"  # 风景
    PORTRAIT = "portrait"  # 肖像
    ARCHITECTURE = "architecture"  # 建筑
    ABSTRACT = "abstract"  # 抽象

    # 图生视频子类别
    ANIMATION = "animation"  # 动画
    CINEMATIC = "cinematic"  # 电影感
    EXPLAINER = "explainer"  # 解说视频
    SOCIAL_MEDIA = "social_media"  # 社交媒体

    # 通用
    GENERAL = "general"  # 通用


class PromptSource(Enum):
    """提示词来源枚举"""

    GITHUB = "github"  # GitHub仓库
    COMMUNITY = "community"  # 社区分享
    MANUAL = "manual"  # 手动添加
    GENERATED = "generated"  # 自动生成
    IMPORTED = "imported"  # 导入


class QualityLevel(Enum):
    """质量等级"""

    EXCELLENT = 5  # 优秀
    GOOD = 4  # 良好
    AVERAGE = 3  # 一般
    POOR = 2  # 较差
    UNRATED = 1  # 未评级


@dataclass
class PromptMetadata:
    """提示词元数据"""

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0  # 使用次数
    success_count: int = 0  # 成功次数
    avg_quality_score: float = 0.0  # 平均质量评分
    user_ratings: Dict[str, float] = field(default_factory=dict)  # 用户评分
    last_used: Optional[datetime] = None  # 最后使用时间
    tags: Set[str] = field(default_factory=set)  # 标签

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "avg_quality_score": self.avg_quality_score,
            "user_ratings": self.user_ratings,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PromptMetadata":
        """从字典创建"""
        metadata = cls()
        metadata.created_at = (
            datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        )
        metadata.updated_at = (
            datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )
        metadata.usage_count = data.get("usage_count", 0)
        metadata.success_count = data.get("success_count", 0)
        metadata.avg_quality_score = data.get("avg_quality_score", 0.0)
        metadata.user_ratings = data.get("user_ratings", {})
        metadata.last_used = (
            datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None
        )
        metadata.tags = set(data.get("tags", []))
        return metadata


@dataclass
class PromptEntry:
    """提示词条目（核心数据结构）"""

    # 核心标识
    id: str  # 唯一标识符
    prompt_text: str  # 提示词文本

    # 分类信息
    category: PromptCategory  # 主类别
    subcategory: PromptSubcategory  # 子类别

    # 模型和参数
    model_compatibility: List[str]  # 兼容的模型
    parameters: Dict[str, Any]  # 标准化的参数

    # 质量信息
    base_quality_score: float  # 基础质量评分（0-1）
    quality_level: QualityLevel  # 质量等级

    # 来源信息
    source: PromptSource  # 来源
    source_url: Optional[str] = None  # 来源URL
    author: Optional[str] = None  # 作者

    # 示例和参考
    examples: List[Dict] = field(default_factory=list)  # 示例输出
    references: List[str] = field(default_factory=list)  # 参考链接

    # 元数据
    metadata: PromptMetadata = field(default_factory=PromptMetadata)

    # 扩展字段
    language: str = "en"  # 语言
    version: str = "1.0"  # 版本
    is_active: bool = True  # 是否激活

    def __post_init__(self):
        """初始化后处理"""
        # 确保id存在
        if not self.id:
            self.id = self.generate_id()

        # 确保质量等级与分数一致
        if self.base_quality_score >= 0.8:
            self.quality_level = QualityLevel.EXCELLENT
        elif self.base_quality_score >= 0.6:
            self.quality_level = QualityLevel.GOOD
        elif self.base_quality_score >= 0.4:
            self.quality_level = QualityLevel.AVERAGE
        elif self.base_quality_score >= 0.2:
            self.quality_level = QualityLevel.POOR
        else:
            self.quality_level = QualityLevel.UNRATED

    def generate_id(self) -> str:
        """生成唯一ID"""
        # 使用提示词文本的哈希作为基础
        text_hash = hashlib.md5(self.prompt_text.encode()).hexdigest()[:12]
        category_code = self.category.value[:3]
        return f"{category_code}_{text_hash}"

    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        # 处理枚举类型
        data["category"] = self.category.value
        data["subcategory"] = self.subcategory.value
        data["source"] = self.source.value
        data["quality_level"] = self.quality_level.value
        data["metadata"] = self.metadata.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "PromptEntry":
        """从字典创建"""
        # 转换枚举类型
        category = PromptCategory(data["category"])
        subcategory = PromptSubcategory(data["subcategory"])
        source = PromptSource(data["source"])
        quality_level = QualityLevel(data["quality_level"])

        # 处理元数据
        metadata_data = data.get("metadata", {})
        metadata = PromptMetadata.from_dict(metadata_data)

        # 创建实例
        entry = cls(
            id=data["id"],
            prompt_text=data["prompt_text"],
            category=category,
            subcategory=subcategory,
            model_compatibility=data["model_compatibility"],
            parameters=data["parameters"],
            base_quality_score=data["base_quality_score"],
            quality_level=quality_level,
            source=source,
            source_url=data.get("source_url"),
            author=data.get("author"),
            examples=data.get("examples", []),
            references=data.get("references", []),
            metadata=metadata,
            language=data.get("language", "en"),
            version=data.get("version", "1.0"),
            is_active=data.get("is_active", True),
        )

        return entry

    def update_usage(self, success: bool = True, quality_score: Optional[float] = None):
        """更新使用统计"""
        self.metadata.usage_count += 1
        if success:
            self.metadata.success_count += 1

        if quality_score is not None:
            # 更新平均质量评分
            total_score = self.metadata.avg_quality_score * (self.metadata.usage_count - 1)
            total_score += quality_score
            self.metadata.avg_quality_score = total_score / self.metadata.usage_count

        self.metadata.last_used = datetime.now()
        self.metadata.updated_at = datetime.now()

    def add_user_rating(self, user_id: str, rating: float):
        """添加用户评分"""
        self.metadata.user_ratings[user_id] = rating
        self.metadata.updated_at = datetime.now()

    def add_tag(self, tag: str):
        """添加标签"""
        self.metadata.tags.add(tag)
        self.metadata.updated_at = datetime.now()

    def remove_tag(self, tag: str):
        """移除标签"""
        self.metadata.tags.discard(tag)
        self.metadata.updated_at = datetime.now()

    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.metadata.usage_count == 0:
            return 0.0
        return self.metadata.success_count / self.metadata.usage_count

    def get_popularity_score(self) -> float:
        """计算受欢迎程度分数（0-1）"""
        # 基于使用频率、成功率和评分
        usage_factor = min(self.metadata.usage_count / 100, 1.0)  # 最多100次
        success_factor = self.get_success_rate()
        quality_factor = self.metadata.avg_quality_score

        # 加权计算
        score = usage_factor * 0.3 + success_factor * 0.4 + quality_factor * 0.3
        return min(score, 1.0)


class PromptKnowledgeBase:
    """提示词知识库管理器"""

    def __init__(self, db_path: str = "prompt_knowledge_base.db"):
        """
        初始化知识库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.connection = None
        self._init_database()

        # 内存缓存
        self.cache: Dict[str, PromptEntry] = {}
        self.category_index: Dict[PromptCategory, List[str]] = {}
        self.tag_index: Dict[str, List[str]] = {}

        # 加载数据到缓存
        self._load_to_cache()

    def _init_database(self):
        """初始化数据库"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            cursor = self.connection.cursor()

            # 创建提示词表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id TEXT PRIMARY KEY,
                    prompt_text TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT NOT NULL,
                    model_compatibility TEXT,
                    parameters TEXT,
                    base_quality_score REAL,
                    quality_level INTEGER,
                    source TEXT,
                    source_url TEXT,
                    author TEXT,
                    examples TEXT,
                    "references" TEXT,
                    metadata TEXT,
                    language TEXT,
                    version TEXT,
                    is_active BOOLEAN,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON prompts(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_subcategory ON prompts(subcategory)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality ON prompts(base_quality_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON prompts(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_active ON prompts(is_active)")

            self.connection.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")

        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    def _load_to_cache(self):
        """加载数据到缓存"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM prompts WHERE is_active = 1")

            rows = cursor.fetchall()
            for row in rows:
                entry = self._row_to_prompt(row)
                self.cache[entry.id] = entry

                # 更新索引
                category = entry.category
                if category not in self.category_index:
                    self.category_index[category] = []
                self.category_index[category].append(entry.id)

                # 更新标签索引
                for tag in entry.metadata.tags:
                    if tag not in self.tag_index:
                        self.tag_index[tag] = []
                    self.tag_index[tag].append(entry.id)

            logger.info(f"加载了 {len(self.cache)} 个提示词到缓存")

        except sqlite3.Error as e:
            logger.error(f"加载缓存失败: {e}")

    def add_prompt(self, entry: PromptEntry) -> bool:
        """
        添加提示词

        Args:
            entry: 提示词条目

        Returns:
            是否成功
        """
        try:
            # 检查是否已存在
            if entry.id in self.cache:
                logger.warning(f"提示词已存在: {entry.id}")
                return False

            # 保存到数据库
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO prompts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                self._prompt_to_row(entry),
            )

            self.connection.commit()

            # 更新缓存和索引
            self.cache[entry.id] = entry

            category = entry.category
            if category not in self.category_index:
                self.category_index[category] = []
            self.category_index[category].append(entry.id)

            for tag in entry.metadata.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = []
                self.tag_index[tag].append(entry.id)

            logger.info(f"添加提示词: {entry.id}")
            return True

        except sqlite3.Error as e:
            logger.error(f"添加提示词失败: {e}")
            return False

    def update_prompt(self, entry: PromptEntry) -> bool:
        """
        更新提示词

        Args:
            entry: 更新后的提示词条目

        Returns:
            是否成功
        """
        try:
            if entry.id not in self.cache:
                logger.warning(f"提示词不存在: {entry.id}")
                return False

            # 更新数据库
            cursor = self.connection.cursor()
            cursor.execute(
                """
                UPDATE prompts SET
                    prompt_text = ?,
                    category = ?,
                    subcategory = ?,
                    model_compatibility = ?,
                    parameters = ?,
                    base_quality_score = ?,
                    quality_level = ?,
                    source = ?,
                    source_url = ?,
                    author = ?,
                    examples = ?,
                    references = ?,
                    metadata = ?,
                    language = ?,
                    version = ?,
                    is_active = ?,
                    updated_at = ?
                WHERE id = ?
            """,
                self._prompt_to_row(entry)[1:] + (entry.id,),
            )

            self.connection.commit()

            # 更新缓存
            self.cache[entry.id] = entry

            # 更新索引（如果类别改变）
            old_category = None
            for cat, ids in self.category_index.items():
                if entry.id in ids:
                    old_category = cat
                    ids.remove(entry.id)
                    break

            if old_category != entry.category:
                if entry.category not in self.category_index:
                    self.category_index[entry.category] = []
                self.category_index[entry.category].append(entry.id)

            logger.info(f"更新提示词: {entry.id}")
            return True

        except sqlite3.Error as e:
            logger.error(f"更新提示词失败: {e}")
            return False

    def delete_prompt(self, prompt_id: str, soft_delete: bool = True) -> bool:
        """
        删除提示词

        Args:
            prompt_id: 提示词ID
            soft_delete: 是否软删除（标记为非激活）

        Returns:
            是否成功
        """
        try:
            if prompt_id not in self.cache:
                logger.warning(f"提示词不存在: {prompt_id}")
                return False

            if soft_delete:
                # 软删除：标记为非激活
                entry = self.cache[prompt_id]
                entry.is_active = False
                return self.update_prompt(entry)
            else:
                # 硬删除：从数据库移除
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
                self.connection.commit()

                # 从缓存和索引移除
                entry = self.cache.pop(prompt_id, None)
                if entry:
                    # 从类别索引移除
                    for ids in self.category_index.values():
                        if prompt_id in ids:
                            ids.remove(prompt_id)

                    # 从标签索引移除
                    for tag_ids in self.tag_index.values():
                        if prompt_id in tag_ids:
                            tag_ids.remove(prompt_id)

                logger.info(f"删除提示词: {prompt_id}")
                return True

        except sqlite3.Error as e:
            logger.error(f"删除提示词失败: {e}")
            return False

    def get_prompt(self, prompt_id: str) -> Optional[PromptEntry]:
        """
        获取提示词

        Args:
            prompt_id: 提示词ID

        Returns:
            提示词条目或None
        """
        return self.cache.get(prompt_id)

    def search_prompts(
        self,
        query: Optional[str] = None,
        category: Optional[PromptCategory] = None,
        subcategory: Optional[PromptSubcategory] = None,
        min_quality: float = 0.0,
        limit: int = 50,
    ) -> List[PromptEntry]:
        """
        搜索提示词

        Args:
            query: 搜索查询（文本）
            category: 类别筛选
            subcategory: 子类别筛选
            min_quality: 最低质量分数
            limit: 返回数量限制

        Returns:
            提示词列表
        """
        results = []

        # 基础筛选
        for entry in self.cache.values():
            if not entry.is_active:
                continue

            if category and entry.category != category:
                continue

            if subcategory and entry.subcategory != subcategory:
                continue

            if entry.base_quality_score < min_quality:
                continue

            results.append(entry)

        # 文本搜索
        if query:
            query_lower = query.lower()
            scored_results = []

            for entry in results:
                score = 0.0

                # 检查提示词文本
                if query_lower in entry.prompt_text.lower():
                    score += 2.0

                # 检查标签
                for tag in entry.metadata.tags:
                    if query_lower in tag.lower():
                        score += 1.0

                # 检查作者和来源
                if entry.author and query_lower in entry.author.lower():
                    score += 0.5

                if score > 0:
                    scored_results.append((score, entry))

            # 按分数排序
            scored_results.sort(key=lambda x: x[0], reverse=True)
            results = [entry for _, entry in scored_results]
        else:
            # 按质量排序
            results.sort(key=lambda x: x.base_quality_score, reverse=True)

        # 应用限制
        return results[:limit]

    def get_prompts_by_category(
        self, category: PromptCategory, limit: int = 100
    ) -> List[PromptEntry]:
        """
        按类别获取提示词

        Args:
            category: 类别
            limit: 返回数量限制

        Returns:
            提示词列表
        """
        if category not in self.category_index:
            return []

        ids = self.category_index[category][:limit]
        prompts = [self.cache.get(prompt_id) for prompt_id in ids if prompt_id in self.cache]
        return [p for p in prompts if p and p.is_active]

    def get_prompts_by_tag(self, tag: str, limit: int = 100) -> List[PromptEntry]:
        """
        按标签获取提示词

        Args:
            tag: 标签
            limit: 返回数量限制

        Returns:
            提示词列表
        """
        if tag not in self.tag_index:
            return []

        ids = self.tag_index[tag][:limit]
        prompts = [self.cache.get(prompt_id) for prompt_id in ids if prompt_id in self.cache]
        return [p for p in prompts if p and p.is_active]

    def get_recommended_prompts(
        self,
        reference_prompt: Optional[PromptEntry] = None,
        category: Optional[PromptCategory] = None,
        count: int = 10,
    ) -> List[PromptEntry]:
        """
        获取推荐提示词

        Args:
            reference_prompt: 参考提示词（用于相似性推荐）
            category: 类别筛选
            count: 推荐数量

        Returns:
            推荐提示词列表
        """
        # 基础候选集
        if category:
            candidates = self.get_prompts_by_category(category, limit=200)
        else:
            candidates = list(self.cache.values())
            candidates = [c for c in candidates if c.is_active]

        if not reference_prompt:
            # 没有参考：返回最受欢迎的
            candidates.sort(key=lambda x: x.get_popularity_score(), reverse=True)
            return candidates[:count]

        # 有参考：计算相似度并推荐
        scored_candidates = []

        for candidate in candidates:
            if candidate.id == reference_prompt.id:
                continue  # 排除自身

            # 相似度计算（简化版）
            similarity = 0.0

            # 类别相似
            if candidate.category == reference_prompt.category:
                similarity += 0.3
            if candidate.subcategory == reference_prompt.subcategory:
                similarity += 0.2

            # 文本相似（简单重叠）
            ref_words = set(reference_prompt.prompt_text.lower().split())
            cand_words = set(candidate.prompt_text.lower().split())
            overlap = len(ref_words & cand_words)
            similarity += overlap * 0.05

            # 质量加权
            similarity *= candidate.base_quality_score

            if similarity > 0:
                scored_candidates.append((similarity, candidate))

        # 按相似度排序
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [candidate for _, candidate in scored_candidates[:count]]

    def import_from_json(self, json_path: str, source: PromptSource = PromptSource.IMPORTED) -> int:
        """
        从JSON文件导入提示词

        Args:
            json_path: JSON文件路径
            source: 来源类型

        Returns:
            导入的提示词数量
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            imported_count = 0

            for item in data:
                try:
                    # 转换数据格式
                    entry = self._dict_to_prompt(item, source)
                    if self.add_prompt(entry):
                        imported_count += 1

                except Exception as e:
                    logger.warning(f"导入单个提示词失败: {e}")

            logger.info(f"从 {json_path} 导入了 {imported_count} 个提示词")
            return imported_count

        except Exception as e:
            logger.error(f"导入JSON失败: {e}")
            return 0

    def export_to_json(
        self, json_path: str, categories: Optional[List[PromptCategory]] = None
    ) -> int:
        """
        导出提示词到JSON文件

        Args:
            json_path: 输出JSON文件路径
            categories: 要导出的类别列表（None表示全部）

        Returns:
            导出的提示词数量
        """
        try:
            # 筛选提示词
            prompts_to_export = []
            for entry in self.cache.values():
                if not entry.is_active:
                    continue

                if categories and entry.category not in categories:
                    continue

                prompts_to_export.append(entry)

            # 转换为字典列表
            data = [entry.to_dict() for entry in prompts_to_export]

            # 保存到文件
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"导出 {len(data)} 个提示词到 {json_path}")
            return len(data)

        except Exception as e:
            logger.error(f"导出JSON失败: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        stats = {
            "total_prompts": len(self.cache),
            "active_prompts": sum(1 for p in self.cache.values() if p.is_active),
            "by_category": {},
            "by_quality": {},
            "by_source": {},
            "usage_stats": {
                "total_usage": 0,
                "total_success": 0,
                "avg_success_rate": 0.0,
                "most_used": [],
            },
        }

        # 按类别统计
        for entry in self.cache.values():
            if not entry.is_active:
                continue

            cat = entry.category.value
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

            # 按质量等级统计
            quality = entry.quality_level.value
            stats["by_quality"][quality] = stats["by_quality"].get(quality, 0) + 1

            # 按来源统计
            source = entry.source.value
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

            # 使用统计
            stats["usage_stats"]["total_usage"] += entry.metadata.usage_count
            stats["usage_stats"]["total_success"] += entry.metadata.success_count

        # 计算平均成功率
        if stats["usage_stats"]["total_usage"] > 0:
            stats["usage_stats"]["avg_success_rate"] = (
                stats["usage_stats"]["total_success"] / stats["usage_stats"]["total_usage"]
            )

        # 找到最常用的提示词
        most_used = sorted(self.cache.values(), key=lambda x: x.metadata.usage_count, reverse=True)[
            :10
        ]
        stats["usage_stats"]["most_used"] = [
            {"id": entry.id, "usage_count": entry.metadata.usage_count} for entry in most_used
        ]

        return stats

    def cleanup_inactive(self, days_threshold: int = 30) -> int:
        """
        清理非激活的提示词

        Args:
            days_threshold: 非激活天数阈值

        Returns:
            清理的数量
        """
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        cleaned_count = 0

        for entry in list(self.cache.values()):
            if not entry.is_active and entry.metadata.last_used:
                if entry.metadata.last_used < cutoff_date:
                    if self.delete_prompt(entry.id, soft_delete=False):
                        cleaned_count += 1

        logger.info(f"清理了 {cleaned_count} 个非激活提示词")
        return cleaned_count

    def _prompt_to_row(self, entry: PromptEntry) -> tuple:
        """将PromptEntry转换为数据库行"""
        return (
            entry.id,
            entry.prompt_text,
            entry.category.value,
            entry.subcategory.value,
            json.dumps(entry.model_compatibility),
            json.dumps(entry.parameters),
            entry.base_quality_score,
            entry.quality_level.value,
            entry.source.value,
            entry.source_url,
            entry.author,
            json.dumps(entry.examples),
            json.dumps(entry.references),
            json.dumps(entry.metadata.to_dict()),
            entry.language,
            entry.version,
            1 if entry.is_active else 0,
            entry.metadata.created_at.isoformat(),
            entry.metadata.updated_at.isoformat(),
        )

    def _row_to_prompt(self, row: tuple) -> PromptEntry:
        """将数据库行转换为PromptEntry"""
        data = {
            "id": row[0],
            "prompt_text": row[1],
            "category": PromptCategory(row[2]),
            "subcategory": PromptSubcategory(row[3]),
            "model_compatibility": json.loads(row[4]) if row[4] else [],
            "parameters": json.loads(row[5]) if row[5] else {},
            "base_quality_score": row[6],
            "quality_level": QualityLevel(row[7]),
            "source": PromptSource(row[8]),
            "source_url": row[9],
            "author": row[10],
            "examples": json.loads(row[11]) if row[11] else [],
            "references": json.loads(row[12]) if row[12] else [],
            "metadata": (
                PromptMetadata.from_dict(json.loads(row[13])) if row[13] else PromptMetadata()
            ),
            "language": row[14],
            "version": row[15],
            "is_active": bool(row[16]),
        }

        return PromptEntry.from_dict(data)

    def _dict_to_prompt(self, data: Dict, source: PromptSource) -> PromptEntry:
        """将字典转换为PromptEntry"""
        # 确保必需字段存在
        required_fields = ["prompt_text", "category", "subcategory"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"缺少必需字段: {field}")

        # 转换类别
        try:
            category = PromptCategory(data["category"])
        except ValueError:
            category = PromptCategory.OTHER

        # 转换子类别
        try:
            subcategory = PromptSubcategory(data["subcategory"])
        except ValueError:
            subcategory = PromptSubcategory.GENERAL

        # 生成ID（如果不存在）
        prompt_id = data.get("id")
        if not prompt_id:
            temp_entry = PromptEntry(
                id="",
                prompt_text=data["prompt_text"],
                category=category,
                subcategory=subcategory,
                model_compatibility=data.get("model_compatibility", []),
                parameters=data.get("parameters", {}),
                base_quality_score=data.get("base_quality_score", 0.5),
                quality_level=QualityLevel.UNRATED,
                source=source,
                source_url=data.get("source_url"),
                author=data.get("author"),
                examples=data.get("examples", []),
                references=data.get("references", []),
            )
            prompt_id = temp_entry.generate_id()

        # 创建完整的PromptEntry
        entry = PromptEntry(
            id=prompt_id,
            prompt_text=data["prompt_text"],
            category=category,
            subcategory=subcategory,
            model_compatibility=data.get("model_compatibility", []),
            parameters=data.get("parameters", {}),
            base_quality_score=data.get("base_quality_score", 0.5),
            quality_level=QualityLevel.UNRATED,
            source=source,
            source_url=data.get("source_url"),
            author=data.get("author"),
            examples=data.get("examples", []),
            references=data.get("references", []),
            language=data.get("language", "en"),
            version=data.get("version", "1.0"),
        )

        # 添加标签（如果存在）
        tags = data.get("tags", [])
        for tag in tags:
            entry.add_tag(tag)

        return entry

    def close(self):
        """关闭知识库"""
        if self.connection:
            self.connection.close()
            logger.info("知识库已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# 快速使用函数
def create_knowledge_base(db_path: str = "prompt_knowledge_base.db") -> PromptKnowledgeBase:
    """快速创建知识库"""
    return PromptKnowledgeBase(db_path)


def load_sample_data(kb: PromptKnowledgeBase, sample_file: str = "sample_prompts.json"):
    """加载示例数据"""
    if os.path.exists(sample_file):
        kb.import_from_json(sample_file, PromptSource.SAMPLE)
    else:
        logger.warning(f"示例文件不存在: {sample_file}")


# 测试函数
def test_knowledge_base():
    """测试知识库功能"""
    print("=== 测试提示词知识库 ===")

    # 创建临时数据库
    test_db = "test_knowledge_base.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    try:
        # 创建知识库
        kb = PromptKnowledgeBase(test_db)

        # 创建示例提示词
        sample_prompt = PromptEntry(
            id="test_001",
            prompt_text="A beautiful landscape with mountains and lakes, photorealistic, 4k, detailed",
            category=PromptCategory.TEXT_TO_IMAGE,
            subcategory=PromptSubcategory.LANDSCAPE,
            model_compatibility=["stable-diffusion", "dall-e"],
            parameters={"size": "1024x1024", "steps": 30},
            base_quality_score=0.8,
            quality_level=QualityLevel.EXCELLENT,
            source=PromptSource.MANUAL,
            author="Test User",
        )
        sample_prompt.add_tag("landscape")
        sample_prompt.add_tag("photorealistic")

        # 测试添加
        print("\n1. 测试添加提示词...")
        if kb.add_prompt(sample_prompt):
            print("✅ 添加成功")
        else:
            print("❌ 添加失败")

        # 测试获取
        print("\n2. 测试获取提示词...")
        retrieved = kb.get_prompt("test_001")
        if retrieved:
            print(f"✅ 获取成功: {retrieved.prompt_text[:50]}...")
        else:
            print("❌ 获取失败")

        # 测试搜索
        print("\n3. 测试搜索提示词...")
        results = kb.search_prompts("landscape", min_quality=0.5)
        print(f"✅ 搜索到 {len(results)} 个结果")

        # 测试统计
        print("\n4. 测试统计功能...")
        stats = kb.get_statistics()
        print(f"✅ 统计信息: {stats['total_prompts']} 个提示词")

        # 测试更新使用
        print("\n5. 测试更新使用统计...")
        if retrieved:
            retrieved.update_usage(success=True, quality_score=0.9)
            kb.update_prompt(retrieved)
            print(f"✅ 使用统计更新: 使用次数={retrieved.metadata.usage_count}")

        # 测试推荐
        print("\n6. 测试推荐功能...")
        recommendations = kb.get_recommended_prompts(retrieved, count=3)
        print(f"✅ 推荐 {len(recommendations)} 个相关提示词")

        # 关闭知识库
        kb.close()

        print("\n=== 测试完成 ===")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        if os.path.exists(test_db):
            os.remove(test_db)


if __name__ == "__main__":
    # 运行测试
    if test_knowledge_base():
        print("\n✅ 知识库测试通过")
    else:
        print("\n❌ 知识库测试失败")
