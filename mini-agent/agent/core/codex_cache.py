#!/usr/bin/env python3
"""
Codex Semantic Cache - 语义缓存与命中基线

提供最小缓存契约、相似性匹配入口、命中统计与成本/时延基线。
不依赖外部向量数据库或复杂语义服务，优先基于关键词/规范化签名匹配。

核心功能:
1. 内存+磁盘两级缓存 (JSON文件存储)
2. 任务签名规范化与相似性匹配
3. 命中统计与节省估算
4. TTL过期清理
"""

import hashlib
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# 添加项目根目录到路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


class CacheSource(Enum):
    """缓存来源枚举"""

    CODEX_PLAN = "codex_plan"
    CODEX_REVIEW = "codex_review"
    MANUAL_PLAN = "manual_plan"
    MANUAL_REVIEW = "manual_review"
    TASK_ANALYSIS = "task_analysis"
    UNKNOWN = "unknown"


class MatchStrategy(Enum):
    """匹配策略枚举"""

    EXACT = "exact"  # 精确匹配
    KEYWORD = "keyword"  # 关键词匹配
    SIGNATURE = "signature"  # 规范化签名匹配
    HYBRID = "hybrid"  # 混合匹配（签名+轻量语义）


class CacheStatus(Enum):
    """缓存状态枚举"""

    HIT = "hit"
    MISS = "miss"
    STALE = "stale"
    EXPIRED = "expired"
    INVALID = "invalid"


@dataclass
class CacheEntry:
    """缓存条目契约"""

    key: str  # 缓存键 (hash of normalized signature)
    normalized_signature: str  # 规范化任务签名
    raw_input: str  # 原始输入文本
    payload: Dict[str, Any]  # 缓存负载 (任务结果、分析等)
    source: str  # 来源 (CacheSource.value)
    created_at: str  # 创建时间 ISO格式
    updated_at: str  # 更新时间 ISO格式
    ttl_seconds: int = 3600  # 生存时间 (秒), 默认1小时
    hit_count: int = 0  # 命中次数
    last_accessed: Optional[str] = None  # 最后访问时间
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    estimated_save_seconds: float = 0.0  # 估算节省时间(秒)
    estimated_save_tokens: int = 0  # 估算节省token数

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """从字典创建实例"""
        return cls(**data)

    def is_expired(self) -> bool:
        """检查是否过期"""
        now = datetime.now()
        updated = datetime.fromisoformat(self.updated_at)
        return (now - updated).total_seconds() > self.ttl_seconds

    def is_stale(self) -> bool:
        """检查是否陈旧（超过TTL的一半）"""
        now = datetime.now()
        updated = datetime.fromisoformat(self.updated_at)
        half_ttl = self.ttl_seconds / 2
        return (now - updated).total_seconds() > half_ttl

    def record_hit(self, save_seconds: float = 0.0, save_tokens: int = 0):
        """记录命中"""
        self.hit_count += 1
        self.last_accessed = datetime.now().isoformat()
        self.estimated_save_seconds += save_seconds
        self.estimated_save_tokens += save_tokens
        self.updated_at = self.last_accessed


@dataclass
class CacheMatchResult:
    """缓存匹配结果"""

    status: CacheStatus
    entry: Optional[CacheEntry] = None
    match_strategy: Optional[MatchStrategy] = None
    similarity_score: float = 0.0
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "status": self.status.value,
            "similarity_score": self.similarity_score,
            "explanation": self.explanation,
        }
        if self.match_strategy:
            result["match_strategy"] = self.match_strategy.value
        if self.entry:
            result["entry_key"] = self.entry.key
            result["entry_source"] = self.entry.source
            result["entry_hit_count"] = self.entry.hit_count
        return result


@dataclass
class CacheStats:
    """缓存统计"""

    total_entries: int = 0
    total_hits: int = 0
    total_misses: int = 0
    total_stale: int = 0
    total_expired: int = 0
    total_size_bytes: int = 0

    # 节省估算
    total_save_seconds: float = 0.0
    total_save_tokens: int = 0
    avg_save_seconds_per_hit: float = 0.0

    # 命中率
    hit_rate: float = 0.0

    # 按来源统计
    by_source: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def update(self, match_result: CacheMatchResult, entry: Optional[CacheEntry] = None):
        """更新统计"""
        if match_result.status == CacheStatus.HIT:
            self.total_hits += 1
            if entry:
                self.total_save_seconds += entry.estimated_save_seconds
                self.total_save_tokens += entry.estimated_save_tokens
        elif match_result.status == CacheStatus.MISS:
            self.total_misses += 1
        elif match_result.status == CacheStatus.STALE:
            self.total_stale += 1
        elif match_result.status == CacheStatus.EXPIRED:
            self.total_expired += 1

        self.hit_rate = self.total_hits / max(1, self.total_hits + self.total_misses)
        if self.total_hits > 0:
            self.avg_save_seconds_per_hit = self.total_save_seconds / self.total_hits

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class TaskSignatureNormalizer:
    """任务签名规范化器"""

    def __init__(self):
        self.stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "can",
            "could",
            "may",
            "might",
            "must",
        }

    def normalize(self, text: str) -> str:
        """
        规范化文本为签名

        步骤:
        1. 转换为小写
        2. 移除标点符号
        3. 移除停用词
        4. 按字母顺序排序单词
        5. 连接为字符串
        """
        if not text:
            return ""

        # 转换为小写
        text = text.lower()

        # 移除标点符号
        import re

        text = re.sub(r"[^\w\s]", " ", text)

        # 分割单词
        words = text.split()

        # 移除停用词和短词
        words = [w for w in words if w not in self.stop_words and len(w) > 2]

        # 排序并去重
        words = sorted(set(words))

        # 连接为规范化签名
        return " ".join(words)

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """提取关键词（简单的词频统计）"""
        if not text:
            return []

        text = text.lower()
        import re

        text = re.sub(r"[^\w\s]", " ", text)
        words = text.split()

        # 过滤停用词和短词
        words = [w for w in words if w not in self.stop_words and len(w) > 2]

        # 简单词频统计
        from collections import Counter

        word_counts = Counter(words)

        # 返回最常见的关键词
        return [word for word, _ in word_counts.most_common(max_keywords)]


class SimilarityMatcher:
    """相似性匹配器"""

    def __init__(self, normalizer: Optional[TaskSignatureNormalizer] = None):
        self.normalizer = normalizer or TaskSignatureNormalizer()

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算文本相似度 (0.0-1.0)

        使用基于Jaccard相似度的轻量语义近似
        """
        if not text1 or not text2:
            return 0.0

        # 规范化文本
        norm1 = self.normalizer.normalize(text1)
        norm2 = self.normalizer.normalize(text2)

        # 精确匹配
        if norm1 == norm2:
            return 1.0

        # 关键词提取
        keywords1 = set(self.normalizer.extract_keywords(text1, max_keywords=20))
        keywords2 = set(self.normalizer.extract_keywords(text2, max_keywords=20))

        if not keywords1 or not keywords2:
            return 0.0

        # Jaccard相似度
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)

        jaccard = len(intersection) / len(union) if union else 0.0

        # 添加基于词序的简单惩罚
        words1 = norm1.split()
        words2 = norm2.split()

        # 共同单词的比例
        common_words = set(words1).intersection(set(words2))
        word_overlap = (
            len(common_words) / max(len(set(words1)), len(set(words2))) if words1 or words2 else 0.0
        )

        # 综合相似度
        similarity = 0.7 * jaccard + 0.3 * word_overlap

        return min(1.0, max(0.0, similarity))

    def match_strategy_for_similarity(self, similarity: float) -> MatchStrategy:
        """根据相似度确定匹配策略"""
        if similarity >= 0.95:
            return MatchStrategy.EXACT
        elif similarity >= 0.8:
            return MatchStrategy.SIGNATURE
        elif similarity >= 0.6:
            return MatchStrategy.HYBRID
        else:
            return MatchStrategy.KEYWORD


class CodexCache:
    """Codex语义缓存管理器"""

    def __init__(self, cache_dir: Optional[Path] = None, memory_limit: int = 100):
        """
        初始化缓存

        Args:
            cache_dir: 缓存目录，默认在项目根目录的 .codex_cache/
            memory_limit: 内存中最大缓存条目数
        """
        if cache_dir is None:
            cache_dir = Path(project_root) / ".codex_cache"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

        self.memory_limit = memory_limit
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()

        self.normalizer = TaskSignatureNormalizer()
        self.matcher = SimilarityMatcher(self.normalizer)

        # 缓存文件路径
        self.cache_file = self.cache_dir / "codex_cache.json"
        self.stats_file = self.cache_dir / "cache_stats.json"

        # 加载现有缓存
        self.load()

        logger.info(f"Codex缓存初始化完成，目录: {self.cache_dir}")
        logger.info(
            f"内存缓存: {len(self.memory_cache)} 条目，磁盘缓存: {self.stats.total_entries} 条目"
        )

    def _generate_key(self, normalized_signature: str) -> str:
        """生成缓存键"""
        return hashlib.sha256(normalized_signature.encode()).hexdigest()[:16]

    def load(self):
        """从磁盘加载缓存"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 加载条目
                for entry_data in data.get("entries", []):
                    try:
                        entry = CacheEntry.from_dict(entry_data)
                        # 检查是否过期
                        if not entry.is_expired():
                            self.memory_cache[entry.key] = entry
                        else:
                            self.stats.total_expired += 1
                    except Exception as e:
                        logger.warning(f"加载缓存条目失败: {e}")
                        continue

                # 更新统计
                self.stats.total_entries = len(data.get("entries", []))
                logger.info(f"从磁盘加载 {len(self.memory_cache)} 个有效缓存条目")

            # 加载统计
            if self.stats_file.exists():
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    stats_data = json.load(f)
                    self.stats = CacheStats(**stats_data)

        except Exception as e:
            logger.error(f"加载缓存失败: {e}")

    def save(self):
        """保存缓存到磁盘"""
        try:
            # 准备数据
            data = {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "entries": [entry.to_dict() for entry in self.memory_cache.values()],
            }

            # 写入缓存文件
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # 写入统计文件
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(self.stats.to_dict(), f, indent=2, ensure_ascii=False)

            # 更新统计中的条目数
            self.stats.total_entries = len(self.memory_cache)

            logger.debug(f"缓存已保存，条目数: {len(self.memory_cache)}")

        except Exception as e:
            logger.error(f"保存缓存失败: {e}")

    def cleanup(self):
        """清理过期条目"""
        expired_keys = []
        stale_keys = []

        for key, entry in self.memory_cache.items():
            if entry.is_expired():
                expired_keys.append(key)
                self.stats.total_expired += 1
            elif entry.is_stale():
                stale_keys.append(key)
                self.stats.total_stale += 1

        # 移除过期条目
        for key in expired_keys:
            del self.memory_cache[key]

        logger.info(f"清理完成: 移除 {len(expired_keys)} 个过期条目, {len(stale_keys)} 个陈旧条目")
        return expired_keys, stale_keys

    def get(self, raw_input: str, source: str = CacheSource.CODEX_PLAN.value) -> CacheMatchResult:
        """
        获取缓存条目

        Args:
            raw_input: 原始输入文本
            source: 缓存来源

        Returns:
            缓存匹配结果
        """
        # 规范化签名
        normalized_signature = self.normalizer.normalize(raw_input)
        key = self._generate_key(normalized_signature)

        # 1. 精确匹配
        if key in self.memory_cache:
            entry = self.memory_cache[key]

            if entry.is_expired():
                # 过期但保留统计
                return CacheMatchResult(
                    status=CacheStatus.EXPIRED,
                    entry=entry,
                    match_strategy=MatchStrategy.EXACT,
                    similarity_score=1.0,
                    explanation="缓存条目已过期",
                )

            # 记录命中
            entry.record_hit()
            self.stats.update(CacheMatchResult(status=CacheStatus.HIT), entry)

            return CacheMatchResult(
                status=CacheStatus.HIT,
                entry=entry,
                match_strategy=MatchStrategy.EXACT,
                similarity_score=1.0,
                explanation="精确匹配",
            )

        # 2. 相似性匹配（遍历内存缓存）
        best_match = None
        best_similarity = 0.0

        for entry in self.memory_cache.values():
            if entry.is_expired():
                continue

            # 计算相似度
            similarity = self.matcher.calculate_similarity(raw_input, entry.raw_input)

            if similarity > best_similarity and similarity >= 0.6:  # 相似度阈值
                best_similarity = similarity
                best_match = entry

        if best_match:
            match_strategy = self.matcher.match_strategy_for_similarity(best_similarity)

            # 记录命中
            best_match.record_hit()
            self.stats.update(CacheMatchResult(status=CacheStatus.HIT), best_match)

            return CacheMatchResult(
                status=CacheStatus.HIT,
                entry=best_match,
                match_strategy=match_strategy,
                similarity_score=best_similarity,
                explanation=f"相似性匹配 ({match_strategy.value}, 相似度: {best_similarity:.2f})",
            )

        # 3. 未命中
        self.stats.update(CacheMatchResult(status=CacheStatus.MISS))

        return CacheMatchResult(status=CacheStatus.MISS, explanation="未找到匹配的缓存条目")

    def put(
        self,
        raw_input: str,
        payload: Dict[str, Any],
        source: str = CacheSource.CODEX_PLAN.value,
        ttl_seconds: int = 3600,
        estimated_save_seconds: float = 0.0,
        estimated_save_tokens: int = 0,
    ) -> CacheEntry:
        """
        存入缓存条目

        Args:
            raw_input: 原始输入文本
            payload: 缓存负载
            source: 缓存来源
            ttl_seconds: 生存时间
            estimated_save_seconds: 估算节省时间
            estimated_save_tokens: 估算节省token数

        Returns:
            创建的缓存条目
        """
        # 规范化签名
        normalized_signature = self.normalizer.normalize(raw_input)
        key = self._generate_key(normalized_signature)

        now = datetime.now().isoformat()

        # 创建条目
        entry = CacheEntry(
            key=key,
            normalized_signature=normalized_signature,
            raw_input=raw_input,
            payload=payload,
            source=source,
            created_at=now,
            updated_at=now,
            ttl_seconds=ttl_seconds,
            hit_count=0,
            estimated_save_seconds=estimated_save_seconds,
            estimated_save_tokens=estimated_save_tokens,
            metadata={
                "input_length": len(raw_input),
                "payload_keys": list(payload.keys()),
                "version": "1.0",
            },
        )

        # 存入内存缓存
        self.memory_cache[key] = entry

        # 如果超过内存限制，清理最旧的条目
        if len(self.memory_cache) > self.memory_limit:
            self._evict_oldest()

        # 保存到磁盘
        self.save()

        logger.debug(f"缓存条目已存入: {key}, 来源: {source}")

        return entry

    def _evict_oldest(self):
        """清理最旧的条目（基于最后访问时间）"""
        if not self.memory_cache:
            return

        # 找到最旧未访问的条目
        oldest_key = None
        oldest_time = None

        for key, entry in self.memory_cache.items():
            if entry.last_accessed:
                last_accessed = datetime.fromisoformat(entry.last_accessed)
            else:
                last_accessed = datetime.fromisoformat(entry.created_at)

            if oldest_time is None or last_accessed < oldest_time:
                oldest_time = last_accessed
                oldest_key = key

        if oldest_key:
            del self.memory_cache[oldest_key]
            logger.debug(f"清理最旧缓存条目: {oldest_key}")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        self.stats.total_entries = len(self.memory_cache)

        # 按来源统计
        self.stats.by_source = {}
        for entry in self.memory_cache.values():
            source = entry.source
            if source not in self.stats.by_source:
                self.stats.by_source[source] = {
                    "count": 0,
                    "hits": 0,
                    "save_seconds": 0.0,
                }

            self.stats.by_source[source]["count"] += 1
            self.stats.by_source[source]["hits"] += entry.hit_count
            self.stats.by_source[source]["save_seconds"] += entry.estimated_save_seconds

        return self.stats.to_dict()

    def generate_report(self) -> Dict[str, Any]:
        """生成缓存报告"""
        stats = self.get_stats()

        report = {
            "timestamp": datetime.now().isoformat(),
            "cache_location": str(self.cache_dir),
            "memory_entries": len(self.memory_cache),
            "stats": stats,
            "health": {
                "hit_rate": stats["hit_rate"],
                "avg_save_per_hit": stats["avg_save_seconds_per_hit"],
                "total_savings_seconds": stats["total_save_seconds"],
                "status": "healthy" if stats["hit_rate"] > 0.1 else "underutilized",
            },
            "recommendations": [],
        }

        # 添加建议
        if stats["hit_rate"] < 0.1:
            report["recommendations"].append("缓存命中率低，考虑调整相似性阈值或增加缓存条目")

        if stats["total_expired"] > stats["total_entries"] * 0.5:
            report["recommendations"].append("过期条目过多，考虑增加TTL或改进缓存策略")

        return report


# 全局缓存实例
_cache_instance: Optional[CodexCache] = None


def get_cache() -> CodexCache:
    """获取全局缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CodexCache()
    return _cache_instance


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=== Codex Semantic Cache 测试 ===")

    cache = CodexCache()

    # 测试数据
    test_inputs = [
        "How to write a Python function that calculates factorial?",
        "Write a Python function for factorial calculation",
        "Create a function to compute factorial in Python",
        "What is the weather like today?",
        "Check current weather conditions",
    ]

    test_payloads = [
        {
            "answer": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)"
        },
        {
            "answer": "def fact(x):\n    result = 1\n    for i in range(1, x+1):\n        result *= i\n    return result"
        },
        {"solution": "Use recursive or iterative approach"},
        {"answer": "Weather is sunny, 25°C"},
        {"response": "Currently clear skies, temperature 25°C"},
    ]

    print("\n1. 测试缓存写入...")
    for i, (input_text, payload) in enumerate(zip(test_inputs, test_payloads)):
        entry = cache.put(
            raw_input=input_text,
            payload=payload,
            source=CacheSource.CODEX_PLAN.value,
            estimated_save_seconds=2.5,
            estimated_save_tokens=50,
        )
        print(f"   存入: '{input_text[:50]}...' -> 键: {entry.key}")

    print("\n2. 测试缓存读取（精确匹配）...")
    for input_text in test_inputs[:2]:
        result = cache.get(input_text)
        print(f"   查询: '{input_text[:50]}...'")
        print(
            f"   结果: {result.status.value}, 策略: {result.match_strategy.value if result.match_strategy else 'N/A'}"
        )
        if result.entry:
            print(f"   命中次数: {result.entry.hit_count}")

    print("\n3. 测试相似性匹配...")
    similar_queries = [
        "Python factorial function implementation",
        "Get factorial in Python code",
        "Weather forecast for today",
    ]

    for query in similar_queries:
        result = cache.get(query)
        print(f"   查询: '{query}'")
        print(f"   结果: {result.status.value}, 相似度: {result.similarity_score:.2f}")
        if result.entry:
            print(f"   匹配条目: {result.entry.key}, 原始输入: '{result.entry.raw_input[:50]}...'")

    print("\n4. 测试统计...")
    stats = cache.get_stats()
    print(f"   总条目: {stats['total_entries']}")
    print(f"   总命中: {stats['total_hits']}")
    print(f"   总未命中: {stats['total_misses']}")
    print(f"   命中率: {stats['hit_rate']:.2%}")
    print(f"   总节省时间: {stats['total_save_seconds']:.1f} 秒")

    print("\n5. 生成报告...")
    report = cache.generate_report()
    print(f"   缓存健康状态: {report['health']['status']}")
    print(f"   平均每次命中节省: {report['health']['avg_save_per_hit']:.1f} 秒")

    print("\n✅ Codex Semantic Cache 测试完成")
