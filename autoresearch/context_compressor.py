"""Athena 6-layer progressive context compression.

Layer 1: Time-based micro-compression (real-time, fixed interval)
Layer 2: Reactive compression (triggered by token limit)
Layer 3: Session memory (cross-turn decision summaries)
Layer 4: Full summary (session-end archive)
Layer 5: Pre-compression (background predictive compression during idle)
Layer 6: Session reset (keep core pointers only, extreme condition)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

TOKEN_BUDGET = 50000
SKILLS_BUDGET = 25000
MAX_TOKENS_PER_FILE = 5000
MAX_TOKENS_PER_SKILL = 5000
MAX_FILES_TO_RESTORE = 5


@dataclass
class ContextBlock:
    id: str
    content: str
    token_count: int
    importance: float = 1.0
    created: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    source: str = ""


class ProgressiveCompressor:
    """6-layer context compression engine."""

    def __init__(self, token_budget: int = TOKEN_BUDGET) -> None:
        self.budget = token_budget
        self._blocks: dict[str, ContextBlock] = {}
        self._session_memory: list[str] = []
        self._archive_path = Path(".openclaw/context_archive")
        self._last_micro_compress = time.time()

    def add_block(self, block: ContextBlock) -> None:
        self._blocks[block.id] = block
        self._enforce_budget()

    def layer1_micro_compress(self, interval_seconds: int = 60) -> int:
        """Layer 1: Time-based — compress low-importance blocks at fixed intervals."""
        now = time.time()
        if now - self._last_micro_compress < interval_seconds:
            return 0
        self._last_micro_compress = now
        removed = 0
        for bid, block in list(self._blocks.items()):
            if block.importance < 0.3 and (now - block.last_accessed) > 300:
                self._session_memory.append(f"[MICRO] {block.id}: {block.content[:100]}")
                del self._blocks[bid]
                removed += 1
        return removed

    def layer2_reactive_compress(self, trigger_threshold: float = 0.9) -> int:
        """Layer 2: Reactive — compress when budget usage exceeds threshold."""
        total = self._total_tokens()
        if total < self.budget * trigger_threshold:
            return 0
        return self._compress_by_importance(target_budget=self.budget)

    def layer3_session_memory(self) -> str:
        """Layer 3: Session memory — distill cross-turn decision summaries."""
        if not self._session_memory:
            return ""
        summary = "\n".join(self._session_memory[-20:])
        self._session_memory = self._session_memory[-5:]
        return f"[SESSION SUMMARY]\n{summary}"

    def layer4_full_summary(self) -> str:
        """Layer 4: Full summary — generate at session end."""
        lines = [
            f"[SESSION ARCHIVE] {time.strftime('%Y-%m-%d %H:%M')}",
            f"Blocks: {len(self._blocks)}, Tokens: {self._total_tokens()}/{self.budget}",
            "",
        ]
        for _bid, block in sorted(self._blocks.items(), key=lambda x: -x[1].importance):
            lines.append(f"  [{block.importance:.1f}] {block.id}: {block.content[:120]}")
        summary = "\n".join(lines)
        self._archive(summary)
        return summary

    def layer5_pre_compress(self) -> int:
        """Layer 5: Pre-compression — background predictive during idle."""
        total = self._total_tokens()
        if total < self.budget * 0.5:
            return 0
        target = int(self.budget * 0.4)
        return self._compress_by_importance(target_budget=target)

    def layer6_reset(self) -> int:
        """Layer 6: Session reset — keep only high-importance core pointers."""
        self._blocks = {
            bid: b for bid, b in self._blocks.items()
            if b.importance >= 0.9
        }
        self._session_memory = self._session_memory[-3:]
        return self._total_tokens()

    def _total_tokens(self) -> int:
        return sum(b.token_count for b in self._blocks.values())

    def _enforce_budget(self) -> int:
        return self.layer2_reactive_compress()

    def _compress_by_importance(self, target_budget: int) -> int:
        if not self._blocks:
            return 0
        blocks_sorted = sorted(self._blocks.items(), key=lambda x: (x[1].importance, x[1].last_accessed))
        removed = 0
        for bid, block in blocks_sorted:
            if self._total_tokens() <= target_budget:
                break
            self._session_memory.append(f"[AUTO] {block.id}: {block.content[:100]}")
            del self._blocks[bid]
            removed += 1
        return removed

    def _archive(self, summary: str) -> None:
        self._archive_path.parent.mkdir(parents=True, exist_ok=True)
        date = time.strftime("%Y%m%d-%H%M%S")
        path = self._archive_path / f"session-{date}.md"
        path.write_text(summary)
