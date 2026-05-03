"""Provider configuration for LLM Gateway.

Each provider defines endpoint, auth, model list, and capabilities.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ModelSpec:
    model_id: str
    context_window: int
    max_output_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str
    models: list[ModelSpec] = field(default_factory=list)
    default_model: str = ""
    timeout_seconds: int = 120
    max_retries: int = 3

    @property
    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env)

    @property
    def available(self) -> bool:
        return bool(self.api_key)


# Pre-configured providers
PROVIDERS: dict[str, ProviderConfig] = {
    "deepseek": ProviderConfig(
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
        models=[
            ModelSpec(
                model_id="deepseek-chat",
                context_window=65536,
                max_output_tokens=8192,
                cost_per_1k_input=0.014,
                cost_per_1k_output=0.28,
            ),
            ModelSpec(
                model_id="deepseek-reasoner",
                context_window=65536,
                max_output_tokens=8192,
                cost_per_1k_input=0.55,
                cost_per_1k_output=2.19,
            ),
        ],
    ),
    "dashscope": ProviderConfig(
        name="DashScope (百炼)",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
        default_model="qwen-plus",
        models=[
            ModelSpec(
                model_id="qwen-plus",
                context_window=131072,
                max_output_tokens=8192,
                cost_per_1k_input=0.0008,
                cost_per_1k_output=0.002,
            ),
            ModelSpec(
                model_id="qwen-max",
                context_window=32768,
                max_output_tokens=8192,
                cost_per_1k_input=0.02,
                cost_per_1k_output=0.06,
            ),
        ],
    ),
    "anthropic": ProviderConfig(
        name="Anthropic",
        base_url="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        default_model="claude-3-5-haiku-latest",
        models=[
            ModelSpec(
                model_id="claude-3-5-haiku-latest",
                context_window=200000,
                max_output_tokens=8192,
                cost_per_1k_input=0.80,
                cost_per_1k_output=4.00,
            ),
        ],
    ),
}
