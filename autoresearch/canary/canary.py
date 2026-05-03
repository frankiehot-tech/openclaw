"""Canary deployment — gradual rollout with automatic rollback triggers."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)


class CanaryState(Enum):
    PREPARING = auto()
    CANARY_ACTIVE = auto()
    ROLLING_OUT = auto()
    FULL_ROLLOUT = auto()
    ROLLED_BACK = auto()
    FAILED = auto()


@dataclass
class CanaryConfig:
    feature_name: str
    initial_percent: int = 5
    increment_percent: int = 10
    increment_interval_minutes: int = 30
    max_percent: int = 100
    error_rate_threshold: float = 0.05
    latency_p95_threshold_ms: float = 500.0
    min_observations: int = 100


@dataclass
class CanaryMetrics:
    total_requests: int = 0
    errors: int = 0
    latency_p95_ms: float = 0.0
    error_rate: float = 0.0

    @property
    def healthy(self) -> bool:
        return self.error_rate <= 0.05


class CanaryDeployment:
    """Manages canary rollout with automatic health checks and rollback."""

    def __init__(self, config: CanaryConfig) -> None:
        self.config = config
        self.state = CanaryState.PREPARING
        self.current_percent = 0
        self._start_time: float = 0.0
        self._last_increment_time: float = 0.0
        self._metrics = CanaryMetrics()

    def start(self) -> None:
        self.state = CanaryState.CANARY_ACTIVE
        self.current_percent = self.config.initial_percent
        self._start_time = time.time()
        self._last_increment_time = time.time()
        logger.info(f"Canary started for {self.config.feature_name} at {self.current_percent}%")

    def update_metrics(self, total: int, errors: int, latency_p95_ms: float) -> None:
        self._metrics.total_requests = total
        self._metrics.errors = errors
        self._metrics.latency_p95_ms = latency_p95_ms
        self._metrics.error_rate = errors / total if total > 0 else 0.0

    def tick(self) -> CanaryState:
        if self.state in (CanaryState.FULL_ROLLOUT, CanaryState.ROLLED_BACK, CanaryState.FAILED):
            return self.state

        if self.state == CanaryState.CANARY_ACTIVE:
            if self._should_rollback():
                return self.rollback("Health check failed during canary")
            if self._can_increment():
                return self._increment()
            if self.current_percent >= self.config.max_percent:
                return self._complete()

        if self.state == CanaryState.ROLLING_OUT:
            if self._should_rollback():
                return self.rollback("Health check failed during rollout")
            if self.current_percent >= self.config.max_percent:
                return self._complete()

        return self.state

    def rollback(self, reason: str) -> CanaryState:
        logger.warning(f"ROLLBACK: {self.config.feature_name} — {reason}")
        self.state = CanaryState.ROLLED_BACK
        self.current_percent = 0
        return self.state

    def _should_rollback(self) -> bool:
        m = self._metrics
        if m.total_requests < self.config.min_observations:
            return False
        if m.error_rate > self.config.error_rate_threshold:
            logger.warning(f"Error rate {m.error_rate:.2%} exceeds threshold {self.config.error_rate_threshold:.2%}")
            return True
        if m.latency_p95_ms > self.config.latency_p95_threshold_ms:
            logger.warning(f"P95 latency {m.latency_p95_ms:.0f}ms exceeds threshold {self.config.latency_p95_threshold_ms:.0f}ms")
            return True
        return False

    def _can_increment(self) -> bool:
        elapsed = (time.time() - self._last_increment_time) / 60
        return elapsed >= self.config.increment_interval_minutes

    def _increment(self) -> CanaryState:
        self.state = CanaryState.ROLLING_OUT
        self.current_percent = min(
            self.current_percent + self.config.increment_percent,
            self.config.max_percent,
        )
        self._last_increment_time = time.time()
        logger.info(f"Canary: {self.config.feature_name} at {self.current_percent}%")
        return self.state

    def _complete(self) -> CanaryState:
        self.state = CanaryState.FULL_ROLLOUT
        self.current_percent = 100
        elapsed = (time.time() - self._start_time) / 60
        logger.info(f"Canary complete: {self.config.feature_name} fully rolled out in {elapsed:.0f}min")
        return self.state
