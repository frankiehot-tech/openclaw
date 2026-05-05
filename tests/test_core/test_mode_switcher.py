from athena.semantic_layer.core.mode_switcher import ModeDecision, ModeSwitchingEngine
from athena.semantic_layer.schemas.intent import AmbiguityVector, CognitiveMode
from athena.semantic_layer.schemas.state import SemanticStateSnapshot


class TestModeSwitchingEngine:
    def setup_method(self):
        self.engine = ModeSwitchingEngine()

    def test_instant_mode(self):
        decision = self.engine.evaluate_transition(
            complexity_score=0.3, tool_demand=0, parallelism_opportunity=0.0,
        )
        assert decision.target_mode == CognitiveMode.INSTANT
        assert decision.pause_for_human is False

    def test_thinking_mode(self):
        decision = self.engine.evaluate_transition(
            complexity_score=0.5, tool_demand=0, parallelism_opportunity=0.0,
        )
        assert decision.target_mode == CognitiveMode.THINKING

    def test_agent_mode(self):
        decision = self.engine.evaluate_transition(
            complexity_score=0.5, tool_demand=3, parallelism_opportunity=0.0,
        )
        assert decision.target_mode == CognitiveMode.AGENT

    def test_swarm_mode(self):
        decision = self.engine.evaluate_transition(
            complexity_score=0.8, tool_demand=0, parallelism_opportunity=0.8,
        )
        assert decision.target_mode == CognitiveMode.SWARM

    def test_human_attention_triggers_carbon_silicon(self):
        decision = self.engine.evaluate_transition(
            complexity_score=0.3, tool_demand=0, parallelism_opportunity=0.0,
            human_attention_required=True,
        )
        assert decision.target_mode == CognitiveMode.CARBON_SILICON
        assert decision.pause_for_human is True

    def test_awaiting_human_state_triggers_carbon_silicon(self):
        state = SemanticStateSnapshot(agent_id="test", cognitive_state="awaiting_human")
        decision = self.engine.evaluate_transition(
            complexity_score=0.3, tool_demand=0, parallelism_opportunity=0.0,
            current_state=state,
        )
        assert decision.target_mode == CognitiveMode.CARBON_SILICON

    def test_ambiguity_vector_triggers_carbon_silicon(self):
        decision = self.engine.evaluate_transition(
            complexity_score=0.3, tool_demand=0, parallelism_opportunity=0.0,
            ambiguity_vector=AmbiguityVector(scope_ambiguity=0.8, target_ambiguity=0.9),
        )
        assert decision.target_mode == CognitiveMode.CARBON_SILICON
        assert decision.pause_for_human is True

    def test_single_ambiguity_dim_does_not_trigger_carbon_silicon(self):
        decision = self.engine.evaluate_transition(
            complexity_score=0.3, tool_demand=0, parallelism_opportunity=0.0,
            ambiguity_vector=AmbiguityVector(target_ambiguity=0.9),
        )
        assert decision.target_mode == CognitiveMode.INSTANT

    def test_ambiguity_below_threshold_ignored(self):
        decision = self.engine.evaluate_transition(
            complexity_score=0.3, tool_demand=0, parallelism_opportunity=0.0,
            ambiguity_vector=AmbiguityVector(scope_ambiguity=0.6, target_ambiguity=0.6),
        )
        assert decision.target_mode == CognitiveMode.INSTANT

    def test_switch_records_history(self):
        decision = ModeDecision(target_mode=CognitiveMode.THINKING, reason="test")
        self.engine.switch(decision)
        assert self.engine.current_mode == CognitiveMode.THINKING
        assert len(self.engine.mode_history) == 1

    def test_assess_complexity_no_tags(self):
        score = self.engine.assess_complexity(0.5, 0.0, [])
        assert 0.0 < score <= 1.0

    def test_assess_complexity_with_complex_tags(self):
        score = self.engine.assess_complexity(0.5, 0.0, ["security", "deploy"])
        assert score > 0.2

    def test_assess_tool_requirements(self):
        assert self.engine.assess_tool_requirements("deploy", "file") == 3
        assert self.engine.assess_tool_requirements("analyze", "unknown") == 0

    def test_assess_parallelism(self):
        score = self.engine.assess_parallelism(["batch", "security"])
        assert score > 0.0

    def test_parallelism_empty_tags(self):
        assert self.engine.assess_parallelism([]) == 0.0
