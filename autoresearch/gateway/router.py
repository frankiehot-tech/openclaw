"""Model router with fallback strategies."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto

from .providers import PROVIDERS, ProviderConfig


class RoutingStrategy(Enum):
    CHEAPEST_FIRST = auto()
    FASTEST_FIRST = auto()
    HIGHEST_QUALITY = auto()
    ROUND_ROBIN = auto()
    PRIMARY_FALLBACK = auto()


@dataclass
class ProviderStatus:
    provider_name: str
    available: bool
    last_error: str | None = None
    last_error_time: float = 0.0
    consecutive_failures: int = 0
    total_requests: int = 0


@dataclass
class RoutingDecision:
    provider: str
    model: str
    fallback_chain: list[str] = field(default_factory=list)
    reason: str = ""


class ModelRouter:
    """Routes requests to best available model with fallback."""

    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.CHEAPEST_FIRST,
        providers: dict[str, ProviderConfig] | None = None,
        cooldown_seconds: int = 60,
        max_consecutive_failures: int = 3,
    ) -> None:
        self.strategy = strategy
        self._providers = providers or PROVIDERS
        self.cooldown_seconds = cooldown_seconds
        self.max_consecutive_failures = max_consecutive_failures
        self._status: dict[str, ProviderStatus] = {}
        self._round_robin_index = 0

    def available_providers(self) -> list[str]:
        now = time.time()
        available: list[str] = []
        for name, config in self._providers.items():
            if not config.available:
                continue
            status = self._get_status(name)
            if status.consecutive_failures >= self.max_consecutive_failures:
                if now - status.last_error_time < self.cooldown_seconds:
                    continue
                status.consecutive_failures = 0
            available.append(name)
        return available

    def route(self, task_complexity: str = "normal") -> RoutingDecision:
        available = self.available_providers()
        if not available:
            raise RuntimeError("No LLM providers available")
        primary = self._select_primary(available)
        fallback_chain = [p for p in available if p != primary]
        config = self._providers[primary]
        return RoutingDecision(
            provider=primary,
            model=config.default_model,
            fallback_chain=fallback_chain,
            reason=f"Strategy: {self.strategy.name}",
        )

    def record_success(self, provider_name: str) -> None:
        status = self._get_status(provider_name)
        status.consecutive_failures = 0
        status.total_requests += 1

    def record_failure(self, provider_name: str, error: str) -> None:
        status = self._get_status(provider_name)
        status.consecutive_failures += 1
        status.last_error = error
        status.last_error_time = time.time()
        status.total_requests += 1

    def _select_primary(self, available: list[str]) -> str:
        if self.strategy == RoutingStrategy.CHEAPEST_FIRST:
            return self._cheapest(available)
        if self.strategy == RoutingStrategy.ROUND_ROBIN:
            return self._round_robin(available)
        return available[0]

    def _cheapest(self, available: list[str]) -> str:
        best_provider = available[0]
        best_cost = float("inf")
        for name in available:
            config = self._providers[name]
            model = next((m for m in config.models if m.model_id == config.default_model), None)
            if model and model.cost_per_1k_input < best_cost:
                best_cost = model.cost_per_1k_input
                best_provider = name
        return best_provider

    def _round_robin(self, available: list[str]) -> str:
        self._round_robin_index = (self._round_robin_index + 1) % len(available)
        return available[self._round_robin_index]

    def _get_status(self, provider_name: str) -> ProviderStatus:
        if provider_name not in self._status:
            config = self._providers.get(provider_name)
            self._status[provider_name] = ProviderStatus(
                provider_name=provider_name,
                available=config.available if config else False,
            )
        return self._status[provider_name]
