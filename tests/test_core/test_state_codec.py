from uuid import uuid4

from athena.semantic_layer.core.state_codec import AthenaStateCodec
from athena.semantic_layer.schemas.state import (
    CognitiveState,
    FactTriple,
    SemanticChunk,
)


class TestAthenaStateCodec:
    def setup_method(self):
        self.codec = AthenaStateCodec(agent_id="test-agent")

    def test_create_snapshot(self):
        snap = self.codec.create_snapshot(
            cognitive_state=CognitiveState.EXECUTING,
            human_summary="Running task T-42",
            mode="agent",
            token_budget=30000,
        )
        assert snap.agent_id == "test-agent"
        assert snap.cognitive_state == CognitiveState.EXECUTING
        assert snap.human_summary == "Running task T-42"
        assert snap.mode == "agent"
        assert snap.token_budget_remaining == 30000
        assert snap.snapshot_id is not None

    def test_create_snapshot_updates_current(self):
        snap1 = self.codec.create_snapshot(cognitive_state=CognitiveState.PLANNING)
        snap2 = self.codec.create_snapshot(cognitive_state=CognitiveState.EXECUTING)
        assert self.codec._current_snapshot is snap2
        assert self.codec._current_snapshot is not snap1

    def test_diff_cognitive_shift(self):
        a = self.codec.create_snapshot(cognitive_state=CognitiveState.PLANNING)
        b = self.codec.create_snapshot(cognitive_state=CognitiveState.EXECUTING)
        diff = self.codec.diff(a, b)
        assert diff.cognitive_shift is True

    def test_diff_no_shift(self):
        a = self.codec.create_snapshot(cognitive_state=CognitiveState.PLANNING)
        b = self.codec.create_snapshot(cognitive_state=CognitiveState.PLANNING)
        diff = self.codec.diff(a, b)
        assert diff.cognitive_shift is False

    def test_diff_new_facts_counted(self):
        a = self.codec.create_snapshot(facts=[
            FactTriple(subject="x", predicate="y", obj="z"),
        ])
        b = self.codec.create_snapshot(facts=[
            FactTriple(subject="x", predicate="y", obj="z"),
            FactTriple(subject="a", predicate="b", obj="c"),
        ])
        diff = self.codec.diff(a, b)
        assert diff.new_facts_count == 1
        assert diff.stale_facts_count == 0

    def test_diff_stale_facts_counted(self):
        a = self.codec.create_snapshot(facts=[
            FactTriple(subject="x", predicate="y", obj="z"),
            FactTriple(subject="old", predicate="outdated", obj="true"),
        ])
        b = self.codec.create_snapshot(facts=[
            FactTriple(subject="x", predicate="y", obj="z"),
        ])
        diff = self.codec.diff(a, b)
        assert diff.stale_facts_count == 1

    def test_diff_tokens_delta(self):
        a = self.codec.create_snapshot(token_budget=50000)
        b = self.codec.create_snapshot(token_budget=45000)
        diff = self.codec.diff(a, b)
        assert diff.token_budget_delta == -5000

    def test_diff_summary_stable(self):
        a = self.codec.create_snapshot()
        b = self.codec.create_snapshot()
        diff = self.codec.diff(a, b)
        assert diff.summary == "stable"

    def test_is_stuck_with_insufficient_snapshots(self):
        for _ in range(3):
            self.codec.create_snapshot(cognitive_state=CognitiveState.BLOCKED)
        assert self.codec.is_stuck(self.codec._snapshot_history, window=5) is False

    def test_is_stuck_true(self):
        for _ in range(5):
            self.codec.create_snapshot(cognitive_state=CognitiveState.BLOCKED)
        assert self.codec.is_stuck(self.codec._snapshot_history, window=5) is True

    def test_is_stuck_false_mixed(self):
        states = [CognitiveState.BLOCKED, CognitiveState.EXECUTING, CognitiveState.BLOCKED,
                  CognitiveState.BLOCKED, CognitiveState.BLOCKED]
        for s in states:
            self.codec.create_snapshot(cognitive_state=s)
        assert self.codec.is_stuck(self.codec._snapshot_history, window=5) is False

    def test_is_drifting_false_with_few_snapshots(self):
        for _ in range(2):
            self.codec.create_snapshot()
        assert self.codec.is_drifting() is False

    def test_is_drifting_true(self):
        cid = uuid4()
        self.codec.create_snapshot()
        self.codec.create_snapshot(working_memory=[
            SemanticChunk(chunk_id=cid, content="old", chunk_type="fact"),
        ])
        self.codec.create_snapshot(working_memory=[
            SemanticChunk(chunk_id=cid, content="new", chunk_type="fact"),
        ])
        assert self.codec.is_drifting(threshold=0.1) is True

    def test_memory_drift_no_change(self):
        a = self.codec.create_snapshot()
        b = self.codec.create_snapshot()
        diff = self.codec.diff(a, b)
        assert diff.memory_drift == 0.0
