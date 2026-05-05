from athena.semantic_layer.prompt.prompt_compiler import SemanticPromptCompiler
from athena.semantic_layer.prompt.prompt_segments import (
    PromptSegmentType,
    compile_ambiguity,
    compile_capability,
    compile_constraint,
    compile_decision,
    compile_intent,
    compile_mode,
    compile_task,
    compile_tools,
    create_full_registry,
)
from athena.semantic_layer.prompt.semantic_prompt import SemanticPromptGraph
from athena.semantic_layer.schemas.state import SemanticStateSnapshot


class TestCompileCapability:
    def test_with_items(self):
        result = compile_capability({"capabilities": ["code_review", "deploy", "audit"]})
        assert "Capabilities" in result
        assert "code_review" in result

    def test_empty_fallback(self):
        result = compile_capability({})
        assert "(none declared)" in result


class TestCompileConstraint:
    def test_with_rules(self):
        result = compile_constraint({"constraints": ["must validate", "max_parallel=3"]})
        assert "Constraints" in result
        assert "must validate" in result

    def test_fallback_key(self):
        result = compile_constraint({"rules": ["rule1"]})
        assert "rule1" in result

    def test_empty(self):
        result = compile_constraint({})
        assert "(none)" in result


class TestCompileTools:
    def test_with_tools(self):
        data = {
            "tools": [
                {"id": "search", "category": "data", "description": "Search engine"},
                {"id": "codegen", "category": "code"},
            ]
        }
        result = compile_tools(data)
        assert "Available Tools" in result
        assert "search" in result
        assert "[data]" in result
        assert "Search engine" in result

    def test_empty(self):
        result = compile_tools({})
        assert "(none registered)" in result


class TestCompileTask:
    def test_with_nodes(self):
        data = {
            "nodes": [
                {"id": "T1", "status": "running"},
                {"id": "T2", "status": "pending", "depends_on": ["T1"]},
            ]
        }
        result = compile_task(data)
        assert "Task Graph" in result
        assert "T1" in result
        assert "[running]" in result
        assert "depends" in result

    def test_with_edges(self):
        data = {
            "nodes": [{"id": "T1"}, {"id": "T2"}],
            "edges": [{"from": "T1", "to": "T2"}],
        }
        result = compile_task(data)
        assert "T1 → T2" in result

    def test_empty(self):
        result = compile_task({})
        assert "(no active tasks)" in result


class TestCompileAmbiguity:
    def test_with_questions(self):
        data = {
            "overall_clarity": 0.3,
            "suggested_mode": "carbon-silicon",
            "questions": [
                {"dimension": "scope", "template": "Which scope?", "options": ["a", "b"]},
            ],
        }
        result = compile_ambiguity(data)
        assert "Ambiguity Context" in result
        assert "0.30" in result
        assert "carbon-silicon" in result
        assert "Which scope?" in result

    def test_high_clarity_no_questions(self):
        result = compile_ambiguity({"overall_clarity": 0.95})
        assert "0.95" in result


class TestCompileDecision:
    def test_with_decisions(self):
        data = {
            "decisions": [
                {"decision_id": "D1", "question": "Deploy?", "options": ["yes", "no"]},
            ]
        }
        result = compile_decision(data)
        assert "Pending Decisions" in result
        assert "Deploy?" in result
        assert "yes" in result

    def test_empty(self):
        result = compile_decision({})
        assert "(none)" in result


class TestCompileIntent:
    def test_with_full_data(self):
        data = {
            "raw_input": "check server health",
            "mode_recommendation": "thinking",
            "urgency_level": 0.8,
            "semantic_frame": {
                "action_verb": "analyze",
                "action_object": {"object_name": "server-1", "object_type": "server"},
            },
        }
        result = compile_intent(data)
        assert "User Intent" in result
        assert "check server health" in result
        assert "thinking" in result
        assert "0.80" in result
        assert "server-1" in result

    def test_minimal(self):
        result = compile_intent({"raw_input": "hello"})
        assert "hello" in result


class TestCompileMode:
    def test_current_mode(self):
        result = compile_mode({"current_mode": "thinking"})
        assert "Current Mode" in result
        assert "thinking" in result

    def test_fallback_key(self):
        result = compile_mode({"mode": "agent"})
        assert "agent" in result

    def test_default_mode(self):
        result = compile_mode({})
        assert "instant" in result

    def test_extra_fields(self):
        result = compile_mode({"current_mode": "swarm", "parallelism": "8"})
        assert "swarm" in result
        assert "parallelism: 8" in result


class TestFullRegistry:
    def test_registers_all_12_segments(self):
        registry = create_full_registry()
        expected = {
            PromptSegmentType.META,
            PromptSegmentType.ROLE_DEFINITION,
            PromptSegmentType.CAPABILITY_MANIFEST,
            PromptSegmentType.CONSTRAINT_SET,
            PromptSegmentType.TOOL_REGISTRY,
            PromptSegmentType.TASK_GRAPH,
            PromptSegmentType.MEMORY_SNAPSHOT,
            PromptSegmentType.AMBIGUITY_CONTEXT,
            PromptSegmentType.DECISION_QUEUE,
            PromptSegmentType.USER_INTENT,
            PromptSegmentType.MODE_DECLARATION,
            PromptSegmentType.ROUTING_SIGNALS,
        }
        assert set(registry.registered_types) == expected
        assert len(registry.registered_types) == 12

    def test_all_compilers_callable(self):
        registry = create_full_registry()
        for seg_type in registry.registered_types:
            fn = registry.get_compiler(seg_type)
            assert callable(fn), f"Compiler for {seg_type} is not callable"

    def test_compile_full_12_segments(self):
        registry = create_full_registry()
        compiler = SemanticPromptCompiler(registry)
        graph = SemanticPromptGraph()

        graph.set_segment(PromptSegmentType.META, {"schema_version": "men0.semantic.v1", "feature_flags": {"semantic_layer": True}})
        graph.set_role("You are Athena.")
        graph.set_segment(PromptSegmentType.CAPABILITY_MANIFEST, {"capabilities": ["search", "deploy", "audit"]})
        graph.set_segment(PromptSegmentType.CONSTRAINT_SET, {"constraints": ["must validate", "max_parallel=3"]})
        graph.set_segment(PromptSegmentType.TOOL_REGISTRY, {"tools": [{"id": "search", "category": "data"}]})
        graph.set_segment(PromptSegmentType.TASK_GRAPH, {"nodes": [{"id": "T1", "status": "running"}]})
        graph.set_memory(SemanticStateSnapshot(agent_id="test", human_summary="Working"))
        graph.set_segment(PromptSegmentType.AMBIGUITY_CONTEXT, {"overall_clarity": 0.9, "suggested_mode": "instant"})
        graph.set_segment(PromptSegmentType.DECISION_QUEUE, {"decisions": []})
        graph.set_segment(PromptSegmentType.USER_INTENT, {"raw_input": "analyze system", "mode_recommendation": "thinking"})
        graph.set_segment(PromptSegmentType.MODE_DECLARATION, {"current_mode": "thinking"})
        graph.set_segment(PromptSegmentType.ROUTING_SIGNALS, {"mode": "thinking", "priority": "high"})

        result = compiler.compile(graph)
        assert len(result.segment_boundaries) == 12
        assert result.total_tokens > 0
        assert "role" in result.text
        assert "Capabilities" in result.text
        assert "Constraints" in result.text
        assert "Available Tools" in result.text
        assert "Task Graph" in result.text
        assert "Ambiguity Context" in result.text
        assert "User Intent" in result.text
        assert "Current Mode" in result.text
        assert "Routing" in result.text
