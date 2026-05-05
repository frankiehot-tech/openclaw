from __future__ import annotations

from athena.semantic_layer.schemas.bridge import (
    ClarificationRequest,
    Constraint,
    Men0SharedState,
    PayloadType,
    SemanticMessage,
    SharedSemanticState,
)


class TestPayloadType:
    def test_all_types_defined(self):
        expected = {
            "intent_delegate",
            "state_sync",
            "fact_assertion",
            "constraint_update",
            "clarification_request",
            "memory_diff",
        }
        assert set(PayloadType) == expected


class TestSemanticMessage:
    def test_minimal_creation(self):
        msg = SemanticMessage(source_agent="agent-1")
        assert msg.source_agent == "agent-1"
        assert msg.target_agent == ""
        assert msg.payload_type == PayloadType.STATE_SYNC
        assert msg.schema_version == "men0.semantic.v1"
        assert msg.message_id is not None
        assert msg.vector_clock == {}

    def test_targeted_message(self):
        msg = SemanticMessage(
            source_agent="agent-1",
            target_agent="agent-2",
            payload_type=PayloadType.INTENT_DELEGATE,
            payload={"task": "analyze_file", "path": "/src/main.py"},
        )
        assert msg.target_agent == "agent-2"
        assert msg.payload_type == PayloadType.INTENT_DELEGATE
        assert msg.payload == {"task": "analyze_file", "path": "/src/main.py"}

    def test_broadcast_message(self):
        msg = SemanticMessage(
            source_agent="agent-1",
            target_agent="",
            payload_type=PayloadType.FACT_ASSERTION,
        )
        assert msg.target_agent == ""
        assert msg.payload_type == PayloadType.FACT_ASSERTION


class TestConstraint:
    def test_default_constraint(self):
        c = Constraint(rule="must validate input")
        assert c.rule == "must validate input"
        assert c.scope == "global"
        assert c.priority == 5
        assert c.active is True

    def test_scoped_constraint(self):
        c = Constraint(rule="must use sandbox", scope="agent", priority=1)
        assert c.scope == "agent"
        assert c.priority == 1


class TestClarificationRequest:
    def test_minimal_request(self):
        cr = ClarificationRequest(
            source_agent="agent-1",
            question="Which version?",
            context="deployment target",
        )
        assert cr.source_agent == "agent-1"
        assert cr.question == "Which version?"
        assert cr.context == "deployment target"
        assert cr.options == []

    def test_request_with_options(self):
        cr = ClarificationRequest(
            source_agent="agent-1",
            question="Which env?",
            context="deployment",
            options=["staging", "production", "canary"],
        )
        assert len(cr.options) == 3
        assert "production" in cr.options


class TestMen0SharedState:
    def test_empty_state(self):
        state = Men0SharedState()
        assert state.context_id is not None
        assert state.shared_intents == []
        assert state.shared_facts == []
        assert state.shared_constraints == []
        assert state.agent_vector_clock == {}


class TestSharedSemanticState:
    def test_minimal_state(self):
        state = SharedSemanticState()
        assert state.state_id is not None
        assert state.facts == []
        assert state.constraints == []
        assert state.agent_states == {}
        assert state.version == 1
