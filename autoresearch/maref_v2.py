"""MAREF v0.2.0 — 16-state Gray Code governance machine.

Expands from 10-state to 16-state with single-bit transition guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MarefState(Enum):
    """16-state Gray code governance states (v0.2.0)."""

    INIT = 0
    REGISTER = 1
    DISCOVER = 2
    CONNECT = 3
    OBSERVE = 4
    COLLECT = 5
    ANALYZE = 6
    EVALUATE = 7
    PLAN = 8
    DECIDE = 9
    ACT = 10
    VERIFY = 11
    STABILIZE = 12
    REPORT = 13
    ARCHIVE = 14
    HALT = 15

    def gray_neighbors(self) -> list[MarefState]:
        current_bits = self.value
        neighbors: list[MarefState] = []
        for bit in range(4):
            neighbor_bits = current_bits ^ (1 << bit)
            for state in MarefState:
                if state.value == neighbor_bits:
                    neighbors.append(state)
                    break
        return neighbors

    def can_transition_to(self, target: MarefState) -> bool:
        hamming = (self.value ^ target.value).bit_count()
        return hamming == 1


VALID_TRANSITIONS: dict[MarefState, list[MarefState]] = {
    s: [t for t in MarefState if s.can_transition_to(t)]
    for s in MarefState
}


@dataclass
class StateTransition:
    from_state: MarefState
    to_state: MarefState
    timestamp: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Maref16StateMachine:
    """16-state governance machine with DRF fair scheduling."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self.state = MarefState.INIT
        self._history: list[StateTransition] = []
        self._entropy: float = 0.0

    def transition(self, target: MarefState, reason: str = "") -> bool:
        import time
        if not self.state.can_transition_to(target):
            return False
        trans = StateTransition(
            from_state=self.state,
            to_state=target,
            timestamp=time.time(),
            reason=reason,
        )
        self.state = target
        self._history.append(trans)
        return True

    def history(self) -> list[StateTransition]:
        return list(self._history)

    @property
    def terminal(self) -> bool:
        return self.state == MarefState.HALT

    def entropy(self) -> float:
        return self._entropy


class DRFFairScheduler:
    """Dominant Resource Fairness scheduler for multi-agent resource allocation."""

    def __init__(self) -> None:
        self._allocations: dict[str, dict[str, float]] = {}
        self._resources = ["cpu", "memory", "tokens"]
        self._total_capacity = {"cpu": 100.0, "memory": 100.0, "tokens": 50000.0}

    def allocate(self, agent_id: str, demands: dict[str, float]) -> bool:
        if agent_id not in self._allocations:
            self._allocations[agent_id] = dict.fromkeys(self._resources, 0.0)
        for r, demand in demands.items():
            if self._remaining(r) < demand:
                return False
            self._allocations[agent_id][r] += demand
        return True

    def release(self, agent_id: str) -> None:
        self._allocations.pop(agent_id, None)

    def dominant_share(self, agent_id: str) -> float:
        alloc = self._allocations.get(agent_id, {})
        if not alloc:
            return 0.0
        return max(
            alloc.get(r, 0.0) / self._total_capacity[r]
            for r in self._resources
        )

    def _remaining(self, resource: str) -> float:
        used = sum(a.get(resource, 0.0) for a in self._allocations.values())
        return self._total_capacity[resource] - used

    def fair_share(self) -> dict[str, float]:
        if not self._allocations:
            return {}
        return {aid: self.dominant_share(aid) for aid in self._allocations}


class GEPAEvaluator:
    """GEPA (Green Evaluation for Policy Assessment) — cheap policy pre-screening."""

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold
        self._cache: dict[str, float] = {}

    def evaluate(self, policy: dict, context: dict | None = None) -> float:
        key = str(sorted(policy.items()))
        if key in self._cache:
            return self._cache[key]

        scores = {
            "safety": self._score_safety(policy),
            "efficiency": self._score_efficiency(policy),
            "fairness": self._score_fairness(policy),
            "stability": self._score_stability(policy),
        }
        overall = sum(scores.values()) / len(scores)
        self._cache[key] = overall
        return overall

    def passes(self, policy: dict) -> bool:
        return self.evaluate(policy) >= self.threshold

    def _score_safety(self, policy: dict) -> float:
        risk_actions = policy.get("risk_actions", [])
        return max(0.0, 1.0 - len(risk_actions) * 0.15)

    def _score_efficiency(self, policy: dict) -> float:
        timeout = policy.get("timeout", 300)
        return min(1.0, 60.0 / max(timeout, 1))

    def _score_fairness(self, policy: dict) -> float:
        return policy.get("fairness_weight", 0.5)

    def _score_stability(self, policy: dict) -> float:
        retries = policy.get("max_retries", 1)
        return min(1.0, retries / 5.0)


class FaultInjector:
    """MAREF v0.2.0 Chaos Engineering — 8 fault mode injection."""

    FAULT_TYPES = {
        "network_partition": "Simulate network split between agent groups",
        "node_crash": "Force agent process termination",
        "resource_exhaustion": "Deplete memory/CPU/tokens",
        "clock_skew": "Manipulate agent clock timing",
        "message_loss": "Drop protocol messages",
        "state_corruption": "Corrupt agent state data",
        "cascade_failure": "Chain failure propagation",
        "slow_recovery": "Delay agent restart",
    }

    def __init__(self) -> None:
        self._active_faults: dict[str, dict] = {}

    def inject(self, fault_type: str, target_agent: str, params: dict | None = None) -> bool:
        if fault_type not in self.FAULT_TYPES:
            return False
        self._active_faults[target_agent] = {
            "type": fault_type,
            "params": params or {},
            "timestamp": __import__("time").time(),
        }
        return True

    def remove(self, target_agent: str) -> bool:
        if target_agent in self._active_faults:
            del self._active_faults[target_agent]
            return True
        return False

    def active_faults(self) -> dict[str, dict]:
        return dict(self._active_faults)

    def fault_count(self) -> int:
        return len(self._active_faults)
