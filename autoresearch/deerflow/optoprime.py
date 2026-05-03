"""DeerFlow v2 — OptoPrime node self-optimization.

Learns from execution history to optimize DAG node parameters:
  - Cost estimates (time, tokens)
  - Success probability
  - Optimal retry count
  - Resource allocation
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


@dataclass
class ExecutionRecord:
    node_id: str
    duration: float
    success: bool
    tokens_used: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class NodeProfile:
    node_id: str
    avg_duration: float = 0.0
    success_rate: float = 1.0
    avg_tokens: float = 0.0
    execution_count: int = 0
    optimal_retries: int = 1
    last_updated: float = 0.0


class OptoPrime:
    """Self-optimizing node parameter tuner."""

    def __init__(self, decay_factor: float = 0.9) -> None:
        self.decay = decay_factor
        self._records: list[ExecutionRecord] = []
        self._profiles: dict[str, NodeProfile] = {}

    def record(self, node_id: str, duration: float, success: bool, tokens: int) -> None:
        self._records.append(ExecutionRecord(
            node_id=node_id, duration=duration, success=success, tokens_used=tokens,
        ))
        profile = self._profiles.get(node_id) or NodeProfile(node_id=node_id)
        n = profile.execution_count + 1

        if n == 1:
            profile.avg_duration = duration
            profile.avg_tokens = tokens
        else:
            profile.avg_duration = self.decay * profile.avg_duration + (1 - self.decay) * duration
            profile.avg_tokens = self.decay * profile.avg_tokens + (1 - self.decay) * tokens

        profile.success_rate = (profile.success_rate * (n - 1) + (1 if success else 0)) / n
        profile.execution_count = n
        profile.last_updated = time.time()

        if success:
            profile.optimal_retries = 1
        elif profile.success_rate > 0.5:
            profile.optimal_retries = min(3, profile.optimal_retries + 1)
        else:
            profile.optimal_retries = 3

        self._profiles[node_id] = profile

    def get_profile(self, node_id: str) -> NodeProfile | None:
        return self._profiles.get(node_id)

    def estimate_cost(self, node_id: str) -> float:
        profile = self._profiles.get(node_id)
        if not profile:
            return 10.0
        failure_penalty = (1 - profile.success_rate) * profile.optimal_retries
        return profile.avg_duration * (1 + failure_penalty)

    def suggest_parallelism(self, node_ids: list[str]) -> int:
        if not node_ids:
            return 1
        costs = [self.estimate_cost(nid) for nid in node_ids]
        avg_cost = sum(costs) / len(costs)
        return max(1, min(8, math.ceil(4 * (1 - min(avg_cost / 60, 1)))))

    def reset(self) -> None:
        self._records.clear()
        self._profiles.clear()
