from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

from ..schemas.memory import SharedSemanticFact


@dataclass
class ConfidenceGatedMemoryStore:
    """置信度门控记忆存储 — Engram Gated Fusion 思想的系统级实现。

    借鉴 DeepSeek V4 Engram 的 σ(W·[hidden, memory]) 门控机制：
    - confidence > 0.8 → auto_promote 为全局事实
    - 0.5-0.8 → 标记为"待验证"
    - < 0.5 → 仅保留在源Agent上下文
    - 矛盾检测 → 自动降级 + 触发澄清
    """

    alpha: float = 0.4   # 确认率权重
    beta: float = 0.35   # 一致性权重
    gamma: float = 0.25  # 新鲜度权重

    high_threshold: float = 0.8
    medium_threshold: float = 0.5
    max_age_seconds: float = 86400.0  # 24小时

    def __post_init__(self):
        self._facts: dict[str, SharedSemanticFact] = {}
        self._promoted: set[str] = set()
        self._pending: set[str] = set()

    def ingest(self, fact: SharedSemanticFact) -> bool:
        """接收一个事实，计算置信度并决定处理策略。"""
        key = str(fact.fact_id)
        self._facts[key] = fact
        confidence = self.compute_confidence(fact)

        if confidence >= self.high_threshold:
            fact.is_global = True
            self._promoted.add(key)
            self._pending.discard(key)
            return True
        elif confidence >= self.medium_threshold:
            self._pending.add(key)
            self._promoted.discard(key)
            return False
        else:
            self._promoted.discard(key)
            self._pending.discard(key)
            return False

    def compute_confidence(self, fact: SharedSemanticFact) -> float:
        confirm_ratio = min(1.0, max(0.0, fact.verification_count / max(1, len(fact.source_agents) + fact.verification_count)))
        consistency = max(0.0, 1.0 - (fact.contradiction_count / max(1, fact.verification_count + fact.contradiction_count)))

        age = time.time() - fact.created_at.timestamp()
        freshness = max(0.0, 1.0 - (age / self.max_age_seconds))

        raw = self.alpha * confirm_ratio + self.beta * consistency + self.gamma * freshness
        return 1.0 / (1.0 + math.exp(-6 * (raw - 0.5)))

    def detect_contradiction(self, fact_a: SharedSemanticFact, fact_b: SharedSemanticFact) -> bool:
        if fact_a.ngram_signature and fact_b.ngram_signature:
            return fact_a.ngram_signature == fact_b.ngram_signature and fact_a.content != fact_b.content
        return fact_a.content != fact_b.content and fact_a.ngram_signature == fact_b.ngram_signature

    def promote_to_global(self, fact_id: str) -> bool:
        fact = self._facts.get(fact_id)
        if not fact:
            return False
        fact.is_global = True
        self._promoted.add(fact_id)
        self._pending.discard(fact_id)
        return True

    def demote(self, fact_id: str) -> bool:
        fact = self._facts.get(fact_id)
        if not fact:
            return False
        fact.is_global = False
        fact.contradiction_count += 1
        self._promoted.discard(fact_id)
        self._pending.add(fact_id)
        return True

    @property
    def global_facts(self) -> list[SharedSemanticFact]:
        return [self._facts[fid] for fid in self._promoted]

    @property
    def pending_facts(self) -> list[SharedSemanticFact]:
        return [self._facts[fid] for fid in self._pending]

    def get_fact(self, fact_id: str) -> SharedSemanticFact | None:
        return self._facts.get(fact_id)

    @property
    def status(self) -> dict[str, Any]:
        return {
            "total_facts": len(self._facts),
            "global_count": len(self._promoted),
            "pending_count": len(self._pending),
            "thresholds": {
                "high": self.high_threshold,
                "medium": self.medium_threshold,
            },
        }
