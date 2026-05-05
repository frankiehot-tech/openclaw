from datetime import datetime
from uuid import uuid4

from ..schemas.state import (
    CognitiveState,
    DecisionPoint,
    FactTriple,
    SemanticChunk,
    SemanticStateSnapshot,
    StateDiff,
)


class AthenaStateCodec:
    def __init__(self, agent_id: str = "athena-primary", memory_capacity: int = 7):
        self.agent_id = agent_id
        self.memory_capacity = memory_capacity
        self._current_snapshot: SemanticStateSnapshot | None = None
        self._snapshot_history: list[SemanticStateSnapshot] = []

    def create_snapshot(
        self,
        cognitive_state: str = CognitiveState.PLANNING,
        working_memory: list[SemanticChunk] | None = None,
        facts: list[FactTriple] | None = None,
        decisions: list[DecisionPoint] | None = None,
        human_summary: str = "",
        token_budget: int = 50000,
        mode: str = "instant",
    ) -> SemanticStateSnapshot:
        snapshot = SemanticStateSnapshot(
            snapshot_id=uuid4(),
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            cognitive_state=cognitive_state,
            working_memory=working_memory or [],
            working_memory_capacity=self.memory_capacity,
            queryable_facts=facts or [],
            pending_decisions=decisions or [],
            human_summary=human_summary,
            token_budget_remaining=token_budget,
            mode=mode,
        )
        self._current_snapshot = snapshot
        self._snapshot_history.append(snapshot)
        return snapshot

    def diff(
        self,
        state_a: SemanticStateSnapshot,
        state_b: SemanticStateSnapshot,
    ) -> StateDiff:
        cognitive_shift = state_b.cognitive_state != state_a.cognitive_state

        memory_drift = self._calculate_memory_drift(
            state_a.working_memory,
            state_b.working_memory,
        )

        fact_consistency = self._check_fact_consistency(
            state_a.queryable_facts,
            state_b.queryable_facts,
        )

        old_fact_ids = {str(f.subject) + f.predicate + f.obj for f in state_a.queryable_facts}
        new_fact_ids = {str(f.subject) + f.predicate + f.obj for f in state_b.queryable_facts}

        new_facts = len(new_fact_ids - old_fact_ids)
        stale_facts = len(old_fact_ids - new_fact_ids)

        old_decisions = len(state_a.pending_decisions)
        new_decisions = len(state_b.pending_decisions)
        resolved = sum(1 for d in state_b.pending_decisions if d.resolved) - sum(1 for d in state_a.pending_decisions if d.resolved)

        return StateDiff(
            cognitive_shift=cognitive_shift,
            memory_drift=memory_drift,
            fact_consistency=fact_consistency,
            new_facts_count=new_facts,
            stale_facts_count=stale_facts,
            pending_decisions_added=max(0, new_decisions - old_decisions),
            pending_decisions_resolved=max(0, resolved),
            token_budget_delta=state_b.token_budget_remaining - state_a.token_budget_remaining,
            summary=self._generate_diff_summary(cognitive_shift, memory_drift, fact_consistency),
        )

    def _calculate_memory_drift(
        self,
        memory_a: list[SemanticChunk],
        memory_b: list[SemanticChunk],
    ) -> float:
        if not memory_a and not memory_b:
            return 0.0
        if not memory_a or not memory_b:
            return 1.0

        chunks_a = {c.chunk_id: c.content for c in memory_a}
        chunks_b = {c.chunk_id: c.content for c in memory_b}

        all_ids = set(chunks_a.keys()) | set(chunks_b.keys())
        if not all_ids:
            return 0.0

        drift = 0.0
        for cid in all_ids:
            if cid in chunks_a and cid in chunks_b:
                if chunks_a[cid] != chunks_b[cid]:
                    drift += 1.0
            else:
                drift += 1.0

        return drift / len(all_ids)

    def _check_fact_consistency(
        self,
        facts_a: list[FactTriple],
        facts_b: list[FactTriple],
    ) -> float:
        if not facts_b:
            return 1.0

        inconsistencies = 0
        facts_b_map = {(f.subject, f.predicate, f.obj): f for f in facts_b}

        for f_a in facts_a:
            key = (f_a.subject, f_a.predicate, f_a.obj)
            if key in facts_b_map:
                f_b = facts_b_map[key]
                if f_b.confidence < f_a.confidence * 0.5:
                    inconsistencies += 1

        return max(0.0, 1.0 - (inconsistencies / max(len(facts_a), 1)))

    def _generate_diff_summary(
        self,
        cognitive_shift: bool,
        memory_drift: float,
        fact_consistency: float,
    ) -> str:
        parts = []
        if cognitive_shift:
            parts.append("cognitive state changed")
        if memory_drift > 0.3:
            parts.append(f"memory drift={memory_drift:.2f}")
        if fact_consistency < 0.8:
            parts.append(f"fact inconsistency={fact_consistency:.2f}")
        return "; ".join(parts) if parts else "stable"

    def is_stuck(self, snapshots: list[SemanticStateSnapshot], window: int = 5) -> bool:
        if len(snapshots) < window:
            return False
        recent = snapshots[-window:]
        blocked_count = sum(1 for s in recent if s.cognitive_state == CognitiveState.BLOCKED)
        return blocked_count >= window

    def is_drifting(self, threshold: float = 0.3) -> bool:
        if len(self._snapshot_history) < 3:
            return False
        recent_diffs = []
        for i in range(len(self._snapshot_history) - 1):
            diff = self.diff(self._snapshot_history[i], self._snapshot_history[i + 1])
            recent_diffs.append(diff.memory_drift)
        return sum(recent_diffs[-3:]) / 3 > threshold
