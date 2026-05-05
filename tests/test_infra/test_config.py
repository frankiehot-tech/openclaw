from __future__ import annotations

from athena.semantic_layer.infra.config import (
    AmbiguityConfig,
    CacheConfig,
    LLMConfig,
    SemanticConfig,
    TokenBudgetConfig,
    load_config,
)


class TestLLMConfig:
    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.l1_model == "gemma4:2b"
        assert cfg.l2_model == "deepseek-v4-pro"
        assert cfg.request_timeout == 60.0

    def test_custom(self):
        cfg = LLMConfig(l1_model="gemma4:4b", request_timeout=30.0)
        assert cfg.l1_model == "gemma4:4b"
        assert cfg.request_timeout == 30.0


class TestTokenBudgetConfig:
    def test_defaults(self):
        cfg = TokenBudgetConfig()
        assert cfg.preset_total == 50000
        assert cfg.reserved == 5000
        assert cfg.segment_overrides == {}


class TestAmbiguityConfig:
    def test_defaults(self):
        cfg = AmbiguityConfig()
        assert cfg.threshold == 0.7
        assert cfg.carbon_silicon_dims == 2
        assert cfg.max_clarification_rounds == 3


class TestCacheConfig:
    def test_defaults(self):
        cfg = CacheConfig()
        assert cfg.mvsl_hit_rate_target == 0.85
        assert cfg.immutable_segment_ttl_seconds == 3600
        assert cfg.cache_anchor_count == 4


class TestSemanticConfig:
    def test_default_config(self):
        cfg = SemanticConfig()
        assert cfg.schema_version == "men0.semantic.v1"
        assert cfg.log_level == "INFO"
        assert cfg.llm.l1_model == "gemma4:2b"
        assert cfg.token_budget.preset_total == 50000
        assert cfg.ambiguity.threshold == 0.7
        assert cfg.cache.mvsl_hit_rate_target == 0.85

    def test_feature_flags(self):
        cfg = SemanticConfig()
        assert cfg.feature_flags["semantic_layer_mvsl_enabled"] is False
        assert cfg.feature_flags["men0_bridge_enabled"] is False
        assert len(cfg.feature_flags) == 5

    def test_from_yaml_roundtrip(self, tmp_path):
        import yaml

        yaml_path = tmp_path / "config.yaml"
        data = {
            "schema_version": "men0.semantic.v1",
            "log_level": "DEBUG",
            "llm": {"l1_model": "test-model", "l2_model": "test-l2"},
            "token_budget": {"preset_total": 80000},
            "ambiguity": {"threshold": 0.5},
            "cache": {"mvsl_hit_rate_target": 0.9},
            "feature_flags": {"semantic_layer_mvsl_enabled": True},
        }
        yaml_path.write_text(yaml.dump(data))
        cfg = SemanticConfig.from_yaml(yaml_path)
        assert cfg.schema_version == "men0.semantic.v1"
        assert cfg.log_level == "DEBUG"
        assert cfg.llm.l1_model == "test-model"
        assert cfg.token_budget.preset_total == 80000
        assert cfg.ambiguity.threshold == 0.5
        assert cfg.cache.mvsl_hit_rate_target == 0.9
        assert cfg.feature_flags["semantic_layer_mvsl_enabled"] is True


class TestLoadConfig:
    def test_returns_default_when_no_file(self, monkeypatch, tmp_path):
        cfg = load_config(config_path=str(tmp_path / "nonexistent.yaml"))
        assert isinstance(cfg, SemanticConfig)
