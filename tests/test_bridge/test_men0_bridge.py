import tempfile
from pathlib import Path

from athena.semantic_layer.men0 import Men0Bridge
from athena.semantic_layer.schemas.bridge import PayloadType
from athena.semantic_layer.schemas.intent import ActionVerb, IntentPacket
from athena.semantic_layer.schemas.memory import SharedSemanticFact
from athena.semantic_layer.schemas.state import CognitiveState, SemanticStateSnapshot


class TestMen0Bridge:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.bridge = Men0Bridge("agent-1", Path(self.tmpdir))

    def test_register_peer(self):
        self.bridge.register_peer("agent-2")
        assert self.bridge.status["peers"] == 1

    def test_publish_fact(self):
        fact = SharedSemanticFact(content="server is healthy", verification_count=50,
                                   source_agents=["agent-1"])
        msg = self.bridge.publish_fact(fact)
        assert msg.payload_type == PayloadType.FACT_ASSERTION
        assert msg.source_agent == "agent-1"
        assert len(msg.vector_clock) >= 1
        assert self.bridge.status["confidence_gate"]["total_facts"] == 1

    def test_publish_and_promote_fact(self):
        fact = SharedSemanticFact(content="verified truth", verification_count=100,
                                   source_agents=["agent-1", "agent-2", "agent-3"])
        self.bridge.publish_fact(fact)
        assert self.bridge.status["confidence_gate"]["global_count"] == 1

    def test_publish_state(self):
        state = SemanticStateSnapshot(
            agent_id="agent-1",
            cognitive_state=CognitiveState.EXECUTING,
            human_summary="Working on task",
        )
        msg = self.bridge.publish_state(state)
        assert msg.payload_type == PayloadType.STATE_SYNC

    def test_publish_intent(self):
        intent = IntentPacket(raw_input="analyze data")
        intent.semantic_frame.action_verb = ActionVerb.ANALYZE
        msg = self.bridge.publish_intent("agent-2", intent)
        assert msg.payload_type == PayloadType.INTENT_DELEGATE
        assert msg.target_agent == "agent-2"

    def test_sync_state(self):
        fact = SharedSemanticFact(content="global truth", verification_count=50)
        self.bridge.publish_fact(fact)
        state = self.bridge.sync_state()
        assert state is not None
        assert len(state.facts) >= 0

    def test_status(self):
        s = self.bridge.status
        assert s["agent_id"] == "agent-1"
        assert s["peers"] == 0
        assert "vector_clock" in s
        assert "confidence_gate" in s
