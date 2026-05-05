from __future__ import annotations

from athena.semantic_layer.schemas.state import (
    CognitiveState,
    DecisionPoint,
    FactTriple,
    SemanticStateSnapshot,
    StateDiff,
)


class TestCognitiveState:
    def test_all_states_defined(self):
        expected = {"planning", "executing", "reflecting", "blocked", "ambiguous", "awaiting_human"}
        actual = set(CognitiveState)
        assert actual == expected


class TestSemanticStateSnapshot:
    def test_minimal_creation(self):
        snap = SemanticStateSnapshot(agent_id="agent-1")
        assert snap.agent_id == "agent-1"
        assert snap.snapshot_id is not None
        assert snap.cognitive_state == CognitiveState.PLANNING
        assert snap.working_memory_capacity == 7
        assert snap.working_memory == []
        assert snap.queryable_facts == []
        assert snap.pending_decisions == []

    def test_full_creation(self):
        snap = SemanticStateSnapshot(
            agent_id="agent-2",
            cognitive_state=CognitiveState.EXECUTING,
            token_budget_remaining=30000,
            mode="agent",
            human_summary="Working on task T-42",
        )
        assert snap.cognitive_state == CognitiveState.EXECUTING
        assert snap.token_budget_remaining == 30000
        assert snap.mode == "agent"
        assert snap.human_summary == "Working on task T-42"

    def test_with_facts(self):
        snap = SemanticStateSnapshot(
            agent_id="agent-3",
            queryable_facts=[
                FactTriple(subject="file", predicate="exists", obj="/tmp/x", confidence=0.9),
            ],
        )
        assert len(snap.queryable_facts) == 1
        assert snap.queryable_facts[0].subject == "file"
        assert snap.queryable_facts[0].confidence == 0.9

    def test_with_pending_decisions(self):
        snap = SemanticStateSnapshot(
            agent_id="agent-4",
            pending_decisions=[
                DecisionPoint(
                    question="Deploy to prod?",
                    options=["yes", "no", "later"],
                ),
            ],
        )
        assert len(snap.pending_decisions) == 1
        assert snap.pending_decisions[0].resolved is False


class TestStateDiff:
    def test_default_diff(self):
        diff = StateDiff()
        assert diff.cognitive_shift is False
        assert diff.memory_drift == 0.0
        assert diff.fact_consistency == 1.0
        assert diff.new_facts_count == 0
        assert diff.stale_facts_count == 0
        assert diff.summary == ""

    def test_diff_with_changes(self):
        diff = StateDiff(
            cognitive_shift=True,
            new_facts_count=3,
            stale_facts_count=1,
            summary="Added 3 facts, removed 1",
        )
        assert diff.cognitive_shift is True
        assert diff.new_facts_count == 3
        assert diff.stale_facts_count == 1


class TestFactTriple:
    def test_minimal_fact(self):
        f = FactTriple(subject="agent", predicate="has_mode", obj="thinking")
        assert f.subject == "agent"
        assert f.predicate == "has_mode"
        assert f.obj == "thinking"
        assert f.confidence == 1.0

    def test_fact_with_source(self):
        f = FactTriple(
            subject="queue",
            predicate="has_status",
            obj="healthy",
            confidence=0.85,
            source_agent="monitor-agent",
        )
        assert f.source_agent == "monitor-agent"
        assert f.confidence == 0.85


class TestDecisionPoint:
    def test_unresolved_defaults(self):
        d = DecisionPoint(question="Continue?", options=["yes", "no"])
        assert d.resolved is False
        assert d.resolution is None
        assert d.resolver is None

    def test_resolved_decision(self):
        d = DecisionPoint(
            question="Continue?",
            options=["yes", "no"],
            resolved=True,
            resolution="yes",
            resolver="human:user-1",
        )
        assert d.resolved is True
        assert d.resolution == "yes"
        assert d.resolver == "human:user-1"
