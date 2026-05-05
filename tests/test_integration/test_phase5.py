import asyncio
import time
import tempfile
from pathlib import Path

from athena.semantic_layer.prompt.prompt_segments import (
    PromptSegmentType,
    create_full_registry,
    create_mvsl_registry,
)
from athena.semantic_layer.prompt.prompt_compiler import SemanticPromptCompiler
from athena.semantic_layer.prompt.semantic_prompt import SemanticPromptGraph
from athena.semantic_layer.schemas.intent import AmbiguityVector, ActionVerb, IntentPacket
from athena.semantic_layer.schemas.state import CognitiveState, FactTriple, SemanticStateSnapshot
from athena.semantic_layer.core.intent_core import AthenaIntentCore
from athena.semantic_layer.core.mode_switcher import ModeSwitchingEngine
from athena.semantic_layer.core.state_codec import AthenaStateCodec
from athena.semantic_layer.crdt.lww_register import LWWRegisterStore
from athena.semantic_layer.bridge.vector_clock import VectorClock
from athena.semantic_layer.bridge.confidence_gate import ConfidenceGatedMemoryStore
from athena.semantic_layer.men0 import Men0Bridge
from athena.semantic_layer.schemas.memory import SharedSemanticFact


def build_full_graph() -> SemanticPromptGraph:
    g = SemanticPromptGraph()
    g.set_segment(PromptSegmentType.META, {"schema_version": "men0.semantic.v1", "feature_flags": {"mvsl": True}})
    g.set_role("You are Athena.")
    g.set_segment(PromptSegmentType.CAPABILITY_MANIFEST, {"capabilities": ["search", "deploy", "audit", "review"]})
    g.set_segment(PromptSegmentType.CONSTRAINT_SET, {"constraints": ["must validate", "max_parallel=3"]})
    g.set_segment(PromptSegmentType.TOOL_REGISTRY, {"tools": [{"id": f"tool-{i}", "category": "data"} for i in range(20)]})
    g.set_segment(PromptSegmentType.TASK_GRAPH, {"nodes": [{"id": f"T{i}", "status": "pending"} for i in range(5)]})
    g.set_memory(SemanticStateSnapshot(agent_id="test", human_summary="Working", queryable_facts=[
        FactTriple(subject=f"s{i}", predicate="has", obj=f"o{i}") for i in range(3)
    ]))
    g.set_segment(PromptSegmentType.AMBIGUITY_CONTEXT, {"overall_clarity": 0.8, "suggested_mode": "instant"})
    g.set_segment(PromptSegmentType.DECISION_QUEUE, {"decisions": []})
    intent = IntentPacket(raw_input="benchmark test input")
    intent.semantic_frame.action_verb = ActionVerb.ANALYZE
    g.set_intent(intent)
    g.set_segment(PromptSegmentType.MODE_DECLARATION, {"current_mode": "instant"})
    g.set_segment(PromptSegmentType.ROUTING_SIGNALS, {"mode": "instant", "priority": "low"})
    return g


class TestPerformanceBenchmarks:

    BURN_IN = 3
    ITERATIONS = 50

    def test_compile_mvsl_latency(self):
        registry = create_mvsl_registry()
        compiler = SemanticPromptCompiler(registry)
        graph = SemanticPromptGraph()
        graph.set_role("You are Athena.")
        graph.set_memory(SemanticStateSnapshot(agent_id="test"))
        graph.set_segment(PromptSegmentType.ROUTING_SIGNALS, {"mode": "instant"})
        graph.set_segment(PromptSegmentType.META, {"schema_version": "men0.semantic.v1", "feature_flags": {}})

        for _ in range(self.BURN_IN):
            compiler.compile(graph)

        times = []
        for _ in range(self.ITERATIONS):
            t0 = time.perf_counter()
            compiler.compile(graph)
            times.append((time.perf_counter() - t0) * 1000)

        avg = sum(times) / len(times)
        p50 = sorted(times)[len(times) // 2]
        p99 = sorted(times)[int(len(times) * 0.99)]
        print(f"\n  MVSL compile: avg={avg:.2f}ms, p50={p50:.2f}ms, p99={p99:.2f}ms")

        assert avg < 50, f"MVSL compile too slow: {avg:.2f}ms (target <50ms)"

    def test_compile_full_latency(self):
        registry = create_full_registry()
        compiler = SemanticPromptCompiler(registry)
        graph = build_full_graph()

        for _ in range(self.BURN_IN):
            compiler.compile(graph)

        times = []
        for _ in range(self.ITERATIONS):
            t0 = time.perf_counter()
            compiler.compile(graph)
            times.append((time.perf_counter() - t0) * 1000)

        avg = sum(times) / len(times)
        p50 = sorted(times)[len(times) // 2]
        print(f"\n  Full compile: avg={avg:.2f}ms, p50={p50:.2f}ms, p99={sorted(times)[int(len(times) * 0.99)]:.2f}ms")

        assert avg < 200, f"Full compile too slow: {avg:.2f}ms (target <200ms)"

    def test_intent_parse_latency(self):
        core = AthenaIntentCore()

        for _ in range(self.BURN_IN):
            time.perf_counter()

        times = []
        for _ in range(self.ITERATIONS):
            t0 = time.perf_counter()
            asyncio.run(core.parse("analyze the server logs for errors"))
            times.append((time.perf_counter() - t0) * 1000)

        avg = sum(times) / len(times)
        print(f"\n  Intent parse: avg={avg:.2f}ms")

        assert avg < 10, f"Intent parse too slow: {avg:.2f}ms (keyword fallback)"

    def test_lww_merge_latency(self):
        store = LWWRegisterStore()
        for i in range(100):
            store.set(f"key-{i}", f"val-{i}", float(i), f"agent-{i % 5}")

        remote = {f"key-{i}": {"key": f"key-{i}", "value": f"updated-{i}",
                               "timestamp": float(i + 1000), "source_agent": "remote"}
                  for i in range(50)}

        for _ in range(self.BURN_IN):
            store.merge_remote(remote)
            for i in range(100):
                store.set(f"key-{i}", f"val-{i}", float(i), f"agent-{i % 5}")

        times = []
        for _ in range(self.ITERATIONS):
            t0 = time.perf_counter()
            store.merge_remote(remote)
            times.append((time.perf_counter() - t0) * 1000)

            for i in range(100):
                store.set(f"key-{i}", f"val-{i}", float(i), f"agent-{i % 5}")

        avg = sum(times) / len(times)
        print(f"\n  LWW merge (50 items): avg={avg:.2f}ms")

        assert avg < 5, f"LWW merge too slow: {avg:.2f}ms"

    def test_confidence_compute_latency(self):
        store = ConfidenceGatedMemoryStore()
        fact = SharedSemanticFact(
            content="benchmark fact", verification_count=50,
            source_agents=[f"agent-{i}" for i in range(10)],
        )

        for _ in range(self.BURN_IN):
            store.compute_confidence(fact)

        times = []
        for _ in range(self.ITERATIONS):
            t0 = time.perf_counter()
            store.compute_confidence(fact)
            times.append((time.perf_counter() - t0) * 1000)

        avg = sum(times) / len(times)
        print(f"\n  Confidence compute: avg={avg:.3f}ms")

        assert avg < 1, f"Confidence compute too slow: {avg:.3f}ms"

    def test_vector_clock_merge_latency(self):
        vc = VectorClock("agent-1")
        remote = {f"agent-{i}": i for i in range(20)}

        for _ in range(self.BURN_IN):
            vc2 = VectorClock("agent-1")
            vc2.merge(remote)

        times = []
        for _ in range(self.ITERATIONS):
            vc2 = VectorClock("agent-1")
            t0 = time.perf_counter()
            vc2.merge(remote)
            times.append((time.perf_counter() - t0) * 1000)

        avg = sum(times) / len(times)
        print(f"\n  VectorClock merge (20dims): avg={avg:.3f}ms")

        assert avg < 1, f"VectorClock merge too slow: {avg:.3f}ms"


class TestIntegrationRegression:

    def test_full_conversation_flow(self):
        output = {}

        # Step 1: Parse user intent
        core = AthenaIntentCore()
        intent = asyncio.run(core.parse("Deploy the new version to staging"))
        output["intent"] = {"mode": intent.mode_recommendation.value, "urgency": intent.urgency_level}
        assert intent.raw_input == "Deploy the new version to staging"
        assert intent.mode_recommendation is not None

        # Step 2: Assess mode switching
        engine = ModeSwitchingEngine()
        ambiguity = intent.ambiguity_vector
        max_ambig = max(ambiguity.scope_ambiguity, ambiguity.target_ambiguity,
                       ambiguity.modality_ambiguity, ambiguity.authority_ambiguity)
        complexity = engine.assess_complexity(intent.urgency_level, max_ambig, intent.context_tags)
        tools = engine.assess_tool_requirements(
            intent.semantic_frame.action_verb.value,
            intent.semantic_frame.action_object.object_type,
        )
        decision = engine.evaluate_transition(complexity, tools, 0.0, ambiguity_vector=ambiguity)
        engine.switch(decision)
        output["mode"] = {"mode": engine.current_mode.value, "reason": decision.reason}
        assert engine.current_mode is not None

        # Step 3: Build semantic prompt graph
        graph = build_full_graph()
        graph.set_segment(PromptSegmentType.META, {"schema_version": "men0.semantic.v1", "feature_flags": {"mvsl": True}})
        graph.set_intent(intent)
        graph.set_segment(PromptSegmentType.MODE_DECLARATION, {"current_mode": engine.current_mode.value})

        # Step 4: Compile to full prompt
        registry = create_full_registry()
        compiler = SemanticPromptCompiler(registry)
        result = compiler.compile(graph)
        output["compile"] = {"tokens": result.total_tokens, "segments": len(result.segment_boundaries)}
        assert result.total_tokens > 0
        assert len(result.segment_boundaries) == 12
        assert result.cache_anchors is not None

        # Step 5: Create state snapshot
        codec = AthenaStateCodec("agent-test")
        snapshot = codec.create_snapshot(
            cognitive_state=CognitiveState.PLANNING,
            human_summary="Starting deployment analysis",
            mode=engine.current_mode.value,
        )
        output["state"] = {"mode": snapshot.mode, "cognitive": snapshot.cognitive_state}

        # Step 6: Publish via Men0 bridge
        tmpdir = tempfile.mkdtemp()
        bridge = Men0Bridge("agent-test", Path(tmpdir))
        fact = SharedSemanticFact(content="deploy status: pending", verification_count=1,
                                   source_agents=["agent-test"])
        bridge.publish_fact(fact)
        bridge.publish_state(snapshot)
        output["men0"] = {"status": bridge.status}
        assert bridge.status["confidence_gate"]["total_facts"] == 1

        # Verify all 12 segment boundaries contain valid positions
        for seg_type, (start, end) in result.segment_boundaries.items():
            assert 0 <= start <= end, f"Segment {seg_type} has invalid boundaries: ({start}, {end})"
            assert end <= len(result.text), f"Segment {seg_type} extends beyond text"

        output["fingerprint"] = result.fingerprint
        print(f"\n  Full conversation flow fingerprint: {result.fingerprint}")
        print(f"  Total tokens: {result.total_tokens}")
        print(f"  Cache anchors: {result.cache_anchors}")
