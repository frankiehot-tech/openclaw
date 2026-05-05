from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    ollama_base_url: str = "http://localhost:11434"
    openai_base_url: str = "https://api.openai.com/v1"
    l1_model: str = "gemma4:2b"
    l2_model: str = "deepseek-v4-pro"
    request_timeout: float = 60.0
    max_retries: int = 2
    default_temperature: float = 0.0


class TokenBudgetConfig(BaseModel):
    preset_total: int = 50000
    reserved: int = 5000
    segment_overrides: dict[str, int] = Field(default_factory=dict)


class AmbiguityConfig(BaseModel):
    threshold: float = 0.7
    carbon_silicon_dims: int = 2
    max_clarification_rounds: int = 3


class CacheConfig(BaseModel):
    mvsl_hit_rate_target: float = 0.85
    immutable_segment_ttl_seconds: int = 3600
    cache_anchor_count: int = 4


class SemanticConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    token_budget: TokenBudgetConfig = Field(default_factory=TokenBudgetConfig)
    ambiguity: AmbiguityConfig = Field(default_factory=AmbiguityConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)

    schema_version: str = "men0.semantic.v1"
    log_level: str = "INFO"
    feature_flags: dict[str, bool] = Field(
        default_factory=lambda: {
            "semantic_layer_mvsl_enabled": False,
            "semantic_layer_cache_v2": False,
            "men0_bridge_enabled": False,
            "semantic_carbon_silicon": False,
            "semantic_tool_router": False,
        }
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> SemanticConfig:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        data = yaml.safe_load(path.read_text())
        return cls(**data)


def load_config(config_path: str | Path | None = None) -> SemanticConfig:
    if config_path:
        path = Path(config_path)
        if path.exists():
            return SemanticConfig.from_yaml(path)
        return SemanticConfig()

    search_paths: list[Path] = [
        Path("config/semantic_config.yaml"),
        Path("athena/semantic_layer/config/semantic_config.yaml"),
    ]
    for p in search_paths:
        if p.exists():
            return SemanticConfig.from_yaml(p)

    return SemanticConfig()
