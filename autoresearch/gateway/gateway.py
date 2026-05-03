"""LLM Gateway — unified entry point for multi-model routing.

Usage:
    gateway = LLMGateway()
    result = gateway.chat("你好", provider_chain=["deepseek", "dashscope"])
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .providers import PROVIDERS, ProviderConfig
from .router import ModelRouter, RoutingStrategy

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)
    latency_seconds: float = 0.0
    success: bool = True
    error: str = ""
    fallback_used: bool = False


class LLMGateway:
    """Multi-model LLM gateway with automatic fallback."""

    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.CHEAPEST_FIRST,
        providers: dict[str, ProviderConfig] | None = None,
    ) -> None:
        self._providers = providers or PROVIDERS
        self._router = ModelRouter(strategy=strategy, providers=self._providers)
        self._stats: dict[str, int] = {}

    def chat(
        self,
        messages: list[dict[str, str]] | str,
        provider_chain: list[str] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> ChatResponse:
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        if provider_chain is None:
            decision = self._router.route()
            provider_chain = [decision.provider] + decision.fallback_chain
            model = decision.model if model is None else model

        last_error = ""
        fallback_used = False

        for idx, provider_name in enumerate(provider_chain):
            if idx > 0:
                fallback_used = True
                logger.warning(f"Falling back to {provider_name}")

            config = self._providers.get(provider_name)
            if not config or not config.available:
                last_error = f"Provider {provider_name} unavailable"
                self._router.record_failure(provider_name, last_error)
                continue

            model_id = model or config.default_model
            start = time.time()

            try:
                result = self._call_provider(config, model_id, messages, max_tokens, temperature)
                elapsed = time.time() - start
                self._router.record_success(provider_name)
                self._stats[provider_name] = self._stats.get(provider_name, 0) + 1
                return ChatResponse(
                    content=result.get("content", ""),
                    model=model_id,
                    provider=provider_name,
                    usage=result.get("usage", {}),
                    latency_seconds=round(elapsed, 2),
                    fallback_used=fallback_used,
                )
            except Exception as e:
                elapsed = time.time() - start
                last_error = str(e)
                self._router.record_failure(provider_name, last_error)
                logger.warning(f"Provider {provider_name} failed after {elapsed:.1f}s: {last_error}")
                continue

        return ChatResponse(
            content="",
            model=model or "",
            provider="",
            success=False,
            error=f"All providers exhausted. Last error: {last_error}",
        )

    def _call_provider(
        self,
        config: ProviderConfig,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        }
        # Anthropic uses x-api-key header
        if config.name == "Anthropic":
            headers = {
                "Content-Type": "application/json",
                "x-api-key": config.api_key,
                "anthropic-version": "2023-06-01",
            }

        if config.name == "Anthropic":
            body = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }
        else:
            body = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

        data = json.dumps(body).encode("utf-8")
        url = f"{config.base_url}/chat/completions"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=config.timeout_seconds) as resp:
                raw = json.loads(resp.read().decode("utf-8"))

            if config.name == "Anthropic":
                content = raw.get("content", [{}])[0].get("text", "")
                return {
                    "content": content,
                    "usage": raw.get("usage", {}),
                }
            return {
                "content": raw["choices"][0]["message"]["content"],
                "usage": raw.get("usage", {}),
            }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {error_body[:500]}") from e

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)
