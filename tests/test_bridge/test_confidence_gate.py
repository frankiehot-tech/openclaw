from datetime import UTC, datetime

from athena.semantic_layer.bridge.confidence_gate import ConfidenceGatedMemoryStore
from athena.semantic_layer.schemas.memory import SharedSemanticFact


def make_fact(content: str, verification: int = 0, contradictions: int = 0,
              source_agents: list[str] | None = None) -> SharedSemanticFact:
    return SharedSemanticFact(
        content=content,
        verification_count=verification,
        contradiction_count=contradictions,
        source_agents=source_agents or ["agent-1"],
    )


class TestConfidenceGatedMemoryStore:
    def setup_method(self):
        self.store = ConfidenceGatedMemoryStore()

    def test_ingest_high_confidence_promotes(self):
        fact = make_fact("earth is round", verification=50)
        promoted = self.store.ingest(fact)
        assert promoted is True
        assert fact.is_global is True
        assert len(self.store.global_facts) == 1

    def test_ingest_low_confidence_does_not_promote(self):
        fact = make_fact("maybe it rains", verification=0)
        promoted = self.store.ingest(fact)
        assert promoted is False
        assert fact.is_global is False

    def test_promote_to_global(self):
        fact = make_fact("important fact")
        self.store.ingest(fact)
        assert self.store.promote_to_global(str(fact.fact_id)) is True
        assert fact.is_global is True

    def test_demote(self):
        fact = make_fact("important fact", verification=50)
        self.store.ingest(fact)
        assert self.store.demote(str(fact.fact_id)) is True
        assert fact.is_global is False
        assert fact.contradiction_count == 1

    def test_demote_unknown_fact(self):
        assert self.store.demote("nonexistent") is False

    def test_status(self):
        self.store.ingest(make_fact("f1", verification=50))
        self.store.ingest(make_fact("f2", verification=0, contradictions=10))
        s = self.store.status
        assert s["total_facts"] == 2
        assert s["global_count"] >= 1
        assert s["pending_count"] >= 0

    def test_compute_confidence_high(self):
        fact = make_fact("verified", verification=100, source_agents=["a", "b", "c"])
        conf = self.store.compute_confidence(fact)
        assert conf > 0.8

    def test_compute_confidence_low(self):
        fact = make_fact("unverified", verification=0, contradictions=5)
        conf = self.store.compute_confidence(fact)
        assert conf < 0.5

    def test_old_fact_lower_confidence(self):
        old = datetime(2020, 1, 1, tzinfo=UTC)
        fact = make_fact("old news", verification=0, contradictions=10)
        fact.created_at = old
        conf = self.store.compute_confidence(fact)
        assert conf < 0.3
