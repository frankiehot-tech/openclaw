from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx


class LLMProvider(StrEnum):
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass
class LLMResponse:
    text: str
    provider: LLMProvider
    model: str
    latency_ms: float
    tokens_used: int = 0
    parsed_json: dict[str, Any] | None = None

    def try_parse_json(self) -> dict[str, Any]:
        if self.parsed_json is not None:
            return self.parsed_json
        text = self.text.strip()
        if "```" in text:
            lines = [ln for ln in text.split("\n") if not ln.startswith("```")]
            text = "\n".join(lines)
        self.parsed_json = json.loads(text)
        return self.parsed_json


@dataclass
class LLMClient:
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    openai_base_url: str = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or ""
    )
    default_model: str = "gpt-4o-mini"
    request_timeout: float = 60.0
    max_retries: int = 2

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        provider: LLMProvider | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        timeout: float | None = None,
    ) -> LLMResponse:
        model = model or self.default_model
        provider = provider or self._infer_provider(model)
        t0 = time.monotonic()

        if provider == LLMProvider.OLLAMA:
            return await self._ollama_generate(prompt, model, temperature, max_tokens, timeout)
        return await self._openai_generate(prompt, model, temperature, max_tokens, timeout, t0)

    async def _ollama_generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float | None = None,
    ) -> LLMResponse:
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=timeout or self.request_timeout) as client:
            resp = await client.post(
                f"{self.ollama_base_url.rstrip('/')}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            latency = (time.monotonic() - t0) * 1000
            return LLMResponse(
                text=data.get("response", ""),
                provider=LLMProvider.OLLAMA,
                model=model,
                latency_ms=latency,
                tokens_used=data.get("eval_count", 0),
            )

    async def _openai_generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float | None = None,
        _start_time: float | None = None,
    ) -> LLMResponse:
        t0 = _start_time or time.monotonic()
        headers = {
            "Content-Type": "application/json",
        }
        if self.openai_api_key:
            headers["Authorization"] = f"Bearer {self.openai_api_key}"

        async with httpx.AsyncClient(timeout=timeout or self.request_timeout) as client:
            resp = await client.post(
                f"{self.openai_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            latency = (time.monotonic() - t0) * 1000
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return LLMResponse(
                text=content,
                provider=LLMProvider.OPENAI_COMPATIBLE,
                model=model,
                latency_ms=latency,
                tokens_used=usage.get("total_tokens", 0),
            )

    @staticmethod
    def _infer_provider(model: str) -> LLMProvider:
        ollama_indicators = ("gemma", "llama", "mistral", "mixtral", "qwen", "phi")
        if any(indicator in model.lower() for indicator in ollama_indicators):
            return LLMProvider.OLLAMA
        return LLMProvider.OPENAI_COMPATIBLE
