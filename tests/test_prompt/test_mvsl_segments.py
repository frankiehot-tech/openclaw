from athena.semantic_layer.prompt.prompt_segments import (
    PromptSegmentType,
    SegmentRegistry,
    compile_memory,
    compile_meta,
    compile_role,
    compile_routing,
    create_mvsl_registry,
)


class TestMVSLRegistry:
    def test_create_mvsl_registry(self):
        registry = create_mvsl_registry()
        assert PromptSegmentType.ROLE_DEFINITION in registry.registered_types
        assert PromptSegmentType.MEMORY_SNAPSHOT in registry.registered_types
        assert PromptSegmentType.ROUTING_SIGNALS in registry.registered_types
        assert PromptSegmentType.META in registry.registered_types
        assert len(registry.registered_types) == 4

    def test_get_compiler_returns_callable(self):
        registry = create_mvsl_registry()
        for seg_type in registry.registered_types:
            fn = registry.get_compiler(seg_type)
            assert fn is not None
            assert callable(fn)

    def test_get_token_limit_uses_default(self):
        registry = create_mvsl_registry()
        assert registry.get_token_limit(PromptSegmentType.ROLE_DEFINITION) == 2000
        assert registry.get_token_limit(PromptSegmentType.MEMORY_SNAPSHOT) == 5000
        assert registry.get_token_limit(PromptSegmentType.ROUTING_SIGNALS) == 500
        assert registry.get_token_limit(PromptSegmentType.META) == 300

    def test_token_limit_override(self):
        registry = SegmentRegistry()
        registry.register(PromptSegmentType.ROLE_DEFINITION, compile_role, token_limit_override=4000)
        assert registry.get_token_limit(PromptSegmentType.ROLE_DEFINITION) == 4000


class TestCompileRole:
    def test_with_text(self):
        result = compile_role("You are a code reviewer.")
        assert "Role" in result
        assert "code reviewer" in result

    def test_empty_fallback(self):
        result = compile_role("")
        assert "Athena" in result

    def test_respects_max_tokens(self):
        result = compile_role("x" * 10000, max_tokens=100)
        assert len(result) <= 100 * 2 + 20


class TestCompileMemory:
    def test_with_facts(self):
        data = {
            "facts": [
                {"subject": "server", "predicate": "status", "obj": "healthy"},
                {"subject": "deploy", "predicate": "version", "obj": "v2.3.1"},
            ],
            "summary": "System is operational",
        }
        result = compile_memory(data)
        assert "Memory" in result
        assert "System is operational" in result
        assert "healthy" in result
        assert "v2.3.1" in result

    def test_empty_facts(self):
        result = compile_memory({})
        assert "Memory" in result

    def test_uses_queryable_facts_fallback(self):
        data = {"queryable_facts": [{"subject": "x", "predicate": "y", "obj": "z"}]}
        result = compile_memory(data)
        assert "y" in result


class TestCompileRouting:
    def test_with_signals(self):
        data = {"mode": "thinking", "model": "deepseek-v4", "complexity": "0.6"}
        result = compile_routing(data)
        assert "Routing" in result
        assert "thinking" in result
        assert "deepseek-v4" in result

    def test_empty_dict(self):
        result = compile_routing({})
        assert "Routing" in result


class TestCompileMeta:
    def test_default_version(self):
        result = compile_meta({})
        assert "men0.semantic.v1" in result

    def test_with_flags(self):
        data = {
            "schema_version": "men0.semantic.v2",
            "feature_flags": {"mvsl_enabled": True},
        }
        result = compile_meta(data)
        assert "men0.semantic.v2" in result
        assert "mvsl_enabled" in result
