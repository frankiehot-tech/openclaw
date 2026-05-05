from __future__ import annotations

import pytest

from athena.semantic_layer.schemas.intent import (
    ActionVerb,
    AmbiguityVector,
    CognitiveMode,
    IntentPacket,
    TokenBudget,
)


class TestActionVerb:
    def test_all_verbs_defined(self):
        expected = {"analyze", "create", "modify", "delete", "search", "explain",
                     "configure", "deploy", "audit", "debug", "test", "document",
                     "review", "summarize", "translate", "convert"}
        actual = {v.value for v in ActionVerb}
        assert actual == expected


class TestCognitiveMode:
    def test_all_modes_defined(self):
        expected = {"instant", "thinking", "agent", "swarm", "carbon-silicon"}
        actual = {v.value for v in CognitiveMode}
        assert actual == expected


class TestAmbiguityVector:
    def test_defaults_are_zero(self):
        v = AmbiguityVector()
        assert v.scope_ambiguity == 0.0
        assert v.target_ambiguity == 0.0
        assert v.modality_ambiguity == 0.0
        assert v.authority_ambiguity == 0.0

    def test_needs_clarification_below_threshold(self):
        v = AmbiguityVector(scope_ambiguity=0.5)
        assert v.needs_clarification() is False

    def test_needs_clarification_above_threshold(self):
        v = AmbiguityVector(scope_ambiguity=0.8)
        assert v.needs_clarification() is True

    def test_needs_clarification_only_checks_three_dims(self):
        v = AmbiguityVector(authority_ambiguity=0.9)
        assert v.needs_clarification() is False

    def test_primary_dimension_returns_none_when_clear(self):
        v = AmbiguityVector()
        assert v.primary_dimension is None

    def test_primary_dimension_returns_max(self):
        v = AmbiguityVector(scope_ambiguity=0.3, target_ambiguity=0.8, modality_ambiguity=0.5)
        assert v.primary_dimension == "target"

    def test_values_clamped_0_to_1(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AmbiguityVector(scope_ambiguity=1.5)
        with pytest.raises(ValidationError):
            AmbiguityVector(scope_ambiguity=-0.1)


class TestTokenBudget:
    def test_default_budget(self):
        b = TokenBudget()
        assert b.total == 50000
        assert b.consumed == 0
        assert b.reserved == 5000
        assert b.remaining == 45000

    def test_remaining_never_negative(self):
        b = TokenBudget(total=100, consumed=150, reserved=10)
        assert b.remaining == 0

    def test_remaining_with_consumption(self):
        b = TokenBudget(total=10000, consumed=3000, reserved=2000)
        assert b.remaining == 5000


class TestIntentPacket:
    def test_minimal_creation(self):
        packet = IntentPacket(raw_input="hello")
        assert packet.raw_input == "hello"
        assert packet.intent_id is not None
        assert packet.mode_recommendation == CognitiveMode.INSTANT
        assert packet.urgency_level == 0.5

    def test_fingerprint_stable(self):
        p1 = IntentPacket(raw_input="search for config files")
        p2 = IntentPacket(raw_input="search for config files")
        p1.semantic_frame.action_verb = ActionVerb.SEARCH
        p2.semantic_frame.action_verb = ActionVerb.SEARCH
        assert p1.compute_fingerprint() == p2.compute_fingerprint()

    def test_fingerprint_differs_by_verb(self):
        p1 = IntentPacket(raw_input="search docs")
        p2 = IntentPacket(raw_input="delete docs")
        p1.semantic_frame.action_verb = ActionVerb.SEARCH
        p2.semantic_frame.action_verb = ActionVerb.DELETE
        assert p1.compute_fingerprint() != p2.compute_fingerprint()

    def test_model_dump_includes_fingerprint(self):
        packet = IntentPacket(raw_input="test")
        data = packet.model_dump()
        assert "intent_fingerprint" in data

    def test_default_target_pool_is_empty(self):
        packet = IntentPacket(raw_input="test")
        assert packet.target_agent_pool == []
