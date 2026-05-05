from athena.semantic_layer.prompt.prompt_compiler import (
    CompiledPrompt,
    PromptDiff,
    SemanticPromptCompiler,
)
from athena.semantic_layer.prompt.prompt_segments import PromptSegmentType, create_mvsl_registry
from athena.semantic_layer.prompt.semantic_prompt import AmbiguityInjector, SemanticPromptGraph
from athena.semantic_layer.schemas.intent import AmbiguityVector, IntentPacket
from athena.semantic_layer.schemas.state import SemanticStateSnapshot


class TestSemanticPromptCompiler:
    def setup_method(self):
        self.registry = create_mvsl_registry()
        self.compiler = SemanticPromptCompiler(self.registry)

    def test_compile_mvsl_full(self):
        graph = SemanticPromptGraph()
        graph.set_segment(PromptSegmentType.META, {"schema_version": "men0.semantic.v1", "feature_flags": {"mvsl": True}})
        graph.set_role("You are Athena, a helpful AI assistant.")
        graph.set_memory(SemanticStateSnapshot(
            agent_id="athena-1",
            human_summary="Working on task analysis",
            queryable_facts=[],
        ))
        graph.set_segment(PromptSegmentType.ROUTING_SIGNALS, {"mode": "thinking", "priority": "normal"})

        result = self.compiler.compile(graph)
        assert isinstance(result, CompiledPrompt)
        assert result.segments is not None
        assert result.text is not None
        assert len(result.segment_boundaries) == 4  # meta + role + memory + routing
        assert result.total_tokens > 0

        for seg_type in [PromptSegmentType.META, PromptSegmentType.ROLE_DEFINITION,
                         PromptSegmentType.MEMORY_SNAPSHOT, PromptSegmentType.ROUTING_SIGNALS]:
            assert seg_type in result.segment_boundaries, f"Missing segment: {seg_type}"

    def test_compile_with_cache_hit(self):
        graph = SemanticPromptGraph()
        graph.set_role("You are an AI.")
        graph.set_memory(SemanticStateSnapshot(agent_id="test", human_summary="idle"))
        graph.set_segment(PromptSegmentType.ROUTING_SIGNALS, {"mode": "instant"})
        graph.set_segment(PromptSegmentType.META, {"schema_version": "men0.semantic.v1", "feature_flags": {}})

        result1 = self.compiler.compile(graph)
        result2 = self.compiler.compile(graph)

        assert result1.total_tokens == result2.total_tokens
        assert result1.fingerprint == result2.fingerprint

    def test_compile_incremental_change(self):
        graph = SemanticPromptGraph()
        graph.set_role("You are an AI.")
        graph.set_segment(PromptSegmentType.META, {"schema_version": "men0.semantic.v1", "feature_flags": {}})

        result1 = self.compiler.compile(graph)

        graph.set_memory(SemanticStateSnapshot(agent_id="test", human_summary="new context"))
        result2 = self.compiler.compile(graph)

        assert result1.fingerprint != result2.fingerprint

    def test_compile_empty_graph(self):
        result = self.compiler.compile(SemanticPromptGraph())
        assert result.total_tokens >= 0
        assert len(result.segment_boundaries) == 0
        assert result.text == ""

    def test_diff_between_compilations(self):
        graph = SemanticPromptGraph()
        graph.set_segment(PromptSegmentType.META, {"schema_version": "men0.semantic.v1", "feature_flags": {}})

        result1 = self.compiler.compile(graph)

        graph.set_segment(PromptSegmentType.ROLE_DEFINITION, "You are an AI.")
        result2 = self.compiler.compile(graph)

        diff = self.compiler.diff(result1, result2)
        assert isinstance(diff, PromptDiff)
        assert len(diff.added_segments) >= 1
        assert PromptSegmentType.ROLE_DEFINITION in diff.added_segments

    def test_inject_invalidates_cache(self):
        graph = SemanticPromptGraph()
        graph.set_role("You are an AI.")

        result1 = self.compiler.compile(graph)
        self.compiler.inject(PromptSegmentType.ROLE_DEFINITION, "new role text")
        graph.set_role("new role text")
        result2 = self.compiler.compile(graph)

        assert result1.fingerprint != result2.fingerprint

    def test_cache_anchors_in_immutable_segments(self):
        graph = SemanticPromptGraph()
        graph.set_role("You are an AI.")
        graph.set_segment(PromptSegmentType.META, {"schema_version": "men0.semantic.v1", "feature_flags": {}})

        result = self.compiler.compile(graph)
        assert len(result.cache_anchors) >= 1
        for anchor in result.cache_anchors:
            assert isinstance(anchor, int)
            assert anchor >= 0


class TestAmbiguityInjector:
    def test_inject_clear_input(self):
        injector = AmbiguityInjector()
        vector = AmbiguityVector()
        ctx = injector.inject(vector)
        assert ctx.overall_clarity == 1.0
        assert len(ctx.questions) == 0

    def test_inject_target_ambiguity(self):
        injector = AmbiguityInjector()
        vector = AmbiguityVector(target_ambiguity=0.8)
        ctx = injector.inject(vector)
        assert len(ctx.questions) == 1
        assert ctx.questions[0].dimension == "target"

    def test_inject_multiple_dims_triggers_carbon_silicon(self):
        injector = AmbiguityInjector()
        vector = AmbiguityVector(
            scope_ambiguity=0.8,
            target_ambiguity=0.9,
            modality_ambiguity=0.71,
        )
        ctx = injector.inject(vector)
        assert len(ctx.questions) == 3
        assert ctx.suggested_mode == "carbon-silicon"

    def test_inject_with_intent(self):
        injector = AmbiguityInjector()
        vector = AmbiguityVector(target_ambiguity=0.8)
        intent = IntentPacket(raw_input="check the server")
        intent.semantic_frame.action_context.related_entities = ["server-1", "server-2"]
        ctx = injector.inject(vector, intent=intent)
        assert len(ctx.questions) == 1
        assert "server-1" in ctx.questions[0].options

    def test_carbon_silicon_with_exactly_two_dims(self):
        injector = AmbiguityInjector()
        vector = AmbiguityVector(scope_ambiguity=0.8, target_ambiguity=0.9)
        ctx = injector.inject(vector)
        assert ctx.suggested_mode == "carbon-silicon"

    def test_carbon_silicon_not_triggered_with_one_dim(self):
        injector = AmbiguityInjector()
        vector = AmbiguityVector(target_ambiguity=0.8)
        ctx = injector.inject(vector)
        assert ctx.suggested_mode == "thinking"

    def test_needs_carbon_silicon_static(self):
        assert AmbiguityInjector.needs_carbon_silicon(
            AmbiguityVector(scope_ambiguity=0.8, target_ambiguity=0.9)
        ) is True
        assert AmbiguityInjector.needs_carbon_silicon(
            AmbiguityVector(target_ambiguity=0.8)
        ) is False
        assert AmbiguityInjector.needs_carbon_silicon(
            AmbiguityVector(scope_ambiguity=0.8, target_ambiguity=0.9, modality_ambiguity=0.8)
        ) is True

    def test_template_rotation_different_intents(self):
        injector = AmbiguityInjector()
        vector = AmbiguityVector(target_ambiguity=0.8)
        intent_a = IntentPacket(raw_input="AAAA")
        intent_b = IntentPacket(raw_input="BBBB")
        ctx_a = injector.inject(vector, intent=intent_a)
        ctx_b = injector.inject(vector, intent=intent_b)
        assert ctx_a.questions[0].template is not None
        assert ctx_b.questions[0].template is not None


class TestSemanticPromptGraph:
    def test_set_and_get(self):
        graph = SemanticPromptGraph()
        graph.set_role("test role")
        assert graph.get_segment(PromptSegmentType.ROLE_DEFINITION) == "test role"

    def test_set_intent(self):
        graph = SemanticPromptGraph()
        intent = IntentPacket(raw_input="test intent")
        graph.set_intent(intent)
        segment = graph.get_segment(PromptSegmentType.USER_INTENT)
        assert segment is not None
        assert segment["raw_input"] == "test intent"

    def test_set_memory(self):
        graph = SemanticPromptGraph()
        snap = SemanticStateSnapshot(agent_id="test")
        graph.set_memory(snap)
        segment = graph.get_segment(PromptSegmentType.MEMORY_SNAPSHOT)
        assert segment is not None
        assert segment["agent_id"] == "test"
