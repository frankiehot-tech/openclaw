from athena.semantic_layer.schemas.bridge import PayloadType, SemanticMessage
from athena.semantic_layer.schemas.intent import ActionVerb, IntentPacket
from athena.semantic_layer.schemas.state import CognitiveState, FactTriple, SemanticStateSnapshot


class TestProtoConvertibleIntentPacket:
    def test_to_proto(self):
        packet = IntentPacket(raw_input="analyze server logs")
        packet.semantic_frame.action_verb = ActionVerb.ANALYZE
        proto = packet.to_proto()
        assert isinstance(proto, dict)
        assert proto["raw_input"] == "analyze server logs"

    def test_from_proto(self):
        data = {"raw_input": "test", "urgency_level": 0.8}
        packet = IntentPacket.from_proto(data)
        assert packet.raw_input == "test"
        assert packet.urgency_level == 0.8

    def test_roundtrip(self):
        original = IntentPacket(raw_input="deploy app to staging")
        original.semantic_frame.action_verb = ActionVerb.DEPLOY
        original.urgency_level = 0.9

        restored = IntentPacket.from_proto(original.to_proto())
        assert restored.raw_input == original.raw_input
        assert restored.urgency_level == original.urgency_level
        assert restored.semantic_frame.action_verb == original.semantic_frame.action_verb


class TestProtoConvertibleSnapshot:
    def test_roundtrip(self):
        original = SemanticStateSnapshot(
            agent_id="agent-42",
            cognitive_state=CognitiveState.EXECUTING,
            human_summary="Working on T-1",
            token_budget_remaining=40000,
            queryable_facts=[
                FactTriple(subject="deploy", predicate="status", obj="healthy"),
            ],
        )
        restored = SemanticStateSnapshot.from_proto(original.to_proto())
        assert restored.agent_id == original.agent_id
        assert restored.cognitive_state == original.cognitive_state
        assert restored.human_summary == original.human_summary
        assert restored.token_budget_remaining == original.token_budget_remaining


class TestProtoConvertibleMessage:
    def test_roundtrip(self):
        original = SemanticMessage(
            source_agent="agent-1",
            target_agent="agent-2",
            payload_type=PayloadType.INTENT_DELEGATE,
            payload={"task": "analyze"},
        )
        restored = SemanticMessage.from_proto(original.to_proto())
        assert restored.source_agent == original.source_agent
        assert restored.target_agent == original.target_agent
        assert restored.payload_type == original.payload_type
        assert restored.payload == original.payload
