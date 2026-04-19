#!/usr/bin/env python3
"""
Performance Metrics Specification and Collection for Athena Agent/Runners.

Defines minimal performance metrics specification:
- Response time (latency)
- Queue length (pending tasks)
- Failure rate
- Concurrency (active tasks)
- Resource usage (CPU, memory, disk)

Supports structured metric collection, aggregation, and export.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Type of metric (gauge, counter, histogram, summary)."""

    GAUGE = "gauge"  # instantaneous value (e.g., queue length)
    COUNTER = "counter"  # monotonically increasing (e.g., total tasks)
    HISTOGRAM = "histogram"  # distribution of values (e.g., response times)
    SUMMARY = "summary"  # quantiles over sliding window


class MetricDimension(Enum):
    """Dimensions for categorizing metrics.

    Each dimension defines a specific performance metric with its unit and sampling specification:

    - RESPONSE_TIME: Task execution latency (seconds). Sampled per completed task as (finished_at - started_at).
    - QUEUE_LENGTH: Number of pending tasks in a queue (count). Sampled per queue polling cycle.
    - FAILURE_RATE: Ratio of failed tasks to total executed tasks (0-1). Sampled per task completion.
    - CONCURRENCY: Number of actively running tasks (count). Sampled per task start/end.
    - CPU_USAGE: System CPU utilization percentage (0-100). Sampled from system metrics.
    - MEMORY_USAGE: System memory utilization percentage (0-100). Sampled from system metrics.
    - DISK_USAGE: Disk space utilization percentage (0-100). Sampled from system metrics.
    - THROUGHPUT: Tasks completed per hour (tasks/hour). Sampled over sliding 24-hour window.
    - SUCCESS_RATE: Ratio of successful tasks to total executed tasks (0-1). Sampled per task completion.
    - HEARTBEAT_FRESHNESS: Seconds since last heartbeat signal (seconds). Sampled per heartbeat.
    - LOAD: Normalized system load (0-1). Sampled from system load average.
    - ERROR_COUNT: Count of error occurrences (count). Sampled per error event.
    - CACHE_HIT_RATE: Ratio of cache hits to total cache accesses (0-1). Sampled per cache operation.
    """

    RESPONSE_TIME = "response_time"  # seconds
    QUEUE_LENGTH = "queue_length"  # count
    FAILURE_RATE = "failure_rate"  # ratio (0-1)
    CONCURRENCY = "concurrency"  # active tasks
    CPU_USAGE = "cpu_usage"  # percentage (0-100)
    MEMORY_USAGE = "memory_usage"  # percentage (0-100)
    DISK_USAGE = "disk_usage"  # percentage (0-100)
    THROUGHPUT = "throughput"  # tasks per hour
    SUCCESS_RATE = "success_rate"  # ratio (0-1)
    HEARTBEAT_FRESHNESS = "heartbeat_freshness"  # seconds since last heartbeat
    LOAD = "load"  # normalized load (0-1)
    ERROR_COUNT = "error_count"  # count of errors
    CACHE_HIT_RATE = "cache_hit_rate"  # ratio (0-1)


@dataclass
class MetricSample:
    """A single sample of a metric."""

    dimension: MetricDimension
    value: float
    metric_type: MetricType = MetricType.GAUGE
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "value": self.value,
            "metric_type": self.metric_type.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
            "metadata": self.metadata,
        }


@dataclass
class MetricAggregation:
    """Aggregated metric over a time window."""

    dimension: MetricDimension
    metric_type: MetricType
    labels: Dict[str, str]

    # Aggregated values
    count: int = 0
    sum: float = 0.0
    min: float = 0.0
    max: float = 0.0
    avg: float = 0.0
    p50: Optional[float] = None
    p90: Optional[float] = None
    p99: Optional[float] = None

    # Time window
    window_start: float = 0.0
    window_end: float = 0.0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update(self, sample: MetricSample) -> None:
        """Update aggregation with a new sample."""
        self.count += 1
        self.sum += sample.value
        if self.count == 1:
            self.min = sample.value
            self.max = sample.value
            self.avg = sample.value
        else:
            self.min = min(self.min, sample.value)
            self.max = max(self.max, sample.value)
            self.avg = self.sum / self.count

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["dimension"] = self.dimension.value
        result["metric_type"] = self.metric_type.value
        return result


class PerformanceMetricsCollector:
    """Collects and aggregates performance metrics from agents/runners."""

    def __init__(self, retention_seconds: int = 3600):
        self.retention_seconds = retention_seconds
        self.samples: List[MetricSample] = []
        self.aggregations: Dict[str, MetricAggregation] = {}
        self.lock = threading.RLock()

        # Register default metric dimensions with collection intervals
        self.default_dimensions = [
            MetricDimension.RESPONSE_TIME,
            MetricDimension.QUEUE_LENGTH,
            MetricDimension.FAILURE_RATE,
            MetricDimension.CONCURRENCY,
            MetricDimension.SUCCESS_RATE,
            MetricDimension.HEARTBEAT_FRESHNESS,
            MetricDimension.LOAD,
        ]

        logger.info(f"Performance metrics collector initialized (retention: {retention_seconds}s)")

    def record_sample(self, sample: MetricSample) -> None:
        """Record a metric sample."""
        with self.lock:
            self.samples.append(sample)
            self._cleanup_old_samples()

            # Update aggregation
            agg_key = self._get_aggregation_key(sample)
            if agg_key not in self.aggregations:
                self.aggregations[agg_key] = MetricAggregation(
                    dimension=sample.dimension,
                    metric_type=sample.metric_type,
                    labels=sample.labels,
                    window_start=time.time() - 300,  # 5-minute window
                    window_end=time.time(),
                )
            self.aggregations[agg_key].update(sample)
            self.aggregations[agg_key].window_end = time.time()

    def record(
        self,
        dimension: MetricDimension,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Convenience method to record a metric."""
        sample = MetricSample(
            dimension=dimension,
            value=value,
            metric_type=metric_type,
            labels=labels or {},
            metadata=metadata or {},
        )
        self.record_sample(sample)

    def record_response_time(self, seconds: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record response time (latency)."""
        self.record(
            dimension=MetricDimension.RESPONSE_TIME,
            value=seconds,
            metric_type=MetricType.HISTOGRAM,
            labels=labels,
            metadata={"unit": "seconds"},
        )

    def record_queue_length(self, count: int, queue_id: str) -> None:
        """Record queue length."""
        self.record(
            dimension=MetricDimension.QUEUE_LENGTH,
            value=float(count),
            labels={"queue_id": queue_id},
            metadata={"unit": "tasks"},
        )

    def record_failure_rate(self, rate: float, component: str) -> None:
        """Record failure rate (0-1)."""
        self.record(
            dimension=MetricDimension.FAILURE_RATE,
            value=rate,
            labels={"component": component},
            metadata={"unit": "ratio"},
        )

    def record_concurrency(self, count: int, worker_type: str) -> None:
        """Record concurrency (active tasks)."""
        self.record(
            dimension=MetricDimension.CONCURRENCY,
            value=float(count),
            labels={"worker_type": worker_type},
            metadata={"unit": "tasks"},
        )

    def record_success_rate(self, rate: float, component: str) -> None:
        """Record success rate (0-1)."""
        self.record(
            dimension=MetricDimension.SUCCESS_RATE,
            value=rate,
            labels={"component": component},
            metadata={"unit": "ratio"},
        )

    def record_heartbeat_freshness(self, seconds_since: float, worker_id: str) -> None:
        """Record heartbeat freshness (seconds since last heartbeat)."""
        self.record(
            dimension=MetricDimension.HEARTBEAT_FRESHNESS,
            value=seconds_since,
            labels={"worker_id": worker_id},
            metadata={"unit": "seconds"},
        )

    def record_load(self, load: float, component: str) -> None:
        """Record normalized load (0-1)."""
        self.record(
            dimension=MetricDimension.LOAD,
            value=load,
            labels={"component": component},
            metadata={"unit": "ratio"},
        )

    def _cleanup_old_samples(self) -> None:
        """Remove samples older than retention period."""
        cutoff = time.time() - self.retention_seconds
        self.samples = [s for s in self.samples if s.timestamp >= cutoff]

    def _get_aggregation_key(self, sample: MetricSample) -> str:
        """Generate key for aggregations."""
        labels_str = ",".join(f"{k}={v}" for k, v in sorted(sample.labels.items()))
        return f"{sample.dimension.value}:{sample.metric_type.value}:{labels_str}"

    def get_samples(
        self,
        dimension: Optional[MetricDimension] = None,
        labels: Optional[Dict[str, str]] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 1000,
    ) -> List[MetricSample]:
        """Get metric samples filtered by criteria."""
        with self.lock:
            filtered = self.samples

            if dimension:
                filtered = [s for s in filtered if s.dimension == dimension]

            if labels:
                filtered = [
                    s for s in filtered if all(s.labels.get(k) == v for k, v in labels.items())
                ]

            if start_time:
                filtered = [s for s in filtered if s.timestamp >= start_time]

            if end_time:
                filtered = [s for s in filtered if s.timestamp <= end_time]

            # Sort by timestamp descending (newest first)
            filtered.sort(key=lambda s: s.timestamp, reverse=True)

            return filtered[:limit]

    def get_aggregations(
        self,
        dimension: Optional[MetricDimension] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[MetricAggregation]:
        """Get current metric aggregations."""
        with self.lock:
            aggregations = list(self.aggregations.values())

            if dimension:
                aggregations = [a for a in aggregations if a.dimension == dimension]

            if labels:
                aggregations = [
                    a for a in aggregations if all(a.labels.get(k) == v for k, v in labels.items())
                ]

            return aggregations

    def export_summary(self) -> Dict[str, Any]:
        """Export summary of current metrics."""
        with self.lock:
            aggregations = self.get_aggregations()

            summary = {
                "timestamp": time.time(),
                "sample_count": len(self.samples),
                "aggregation_count": len(aggregations),
                "metrics_by_dimension": {},
            }

            for agg in aggregations:
                dim = agg.dimension.value
                if dim not in summary["metrics_by_dimension"]:
                    summary["metrics_by_dimension"][dim] = []

                summary["metrics_by_dimension"][dim].append(
                    {
                        "labels": agg.labels,
                        "count": agg.count,
                        "avg": agg.avg,
                        "min": agg.min,
                        "max": agg.max,
                    }
                )

            return summary

    def export_json(self, filepath: Optional[Path] = None) -> Dict[str, Any]:
        """Export all metrics as JSON-serializable dict."""
        with self.lock:
            data = {
                "export_timestamp": time.time(),
                "export_version": "1.0",
                "sample_count": len(self.samples),
                "aggregation_count": len(self.aggregations),
                "samples": [s.to_dict() for s in self.samples[-1000:]],  # last 1000 samples
                "aggregations": [a.to_dict() for a in self.aggregations.values()],
            }

            if filepath:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logger.info(f"Metrics exported to {filepath}")

            return data

    def clear(self) -> None:
        """Clear all collected metrics."""
        with self.lock:
            self.samples.clear()
            self.aggregations.clear()


# Global collector instance
_global_collector: Optional[PerformanceMetricsCollector] = None


def get_global_collector() -> PerformanceMetricsCollector:
    """Get global performance metrics collector instance."""
    global _global_collector
    if _global_collector is None:
        _global_collector = PerformanceMetricsCollector()
    return _global_collector


def record_metric(
    dimension: MetricDimension,
    value: float,
    metric_type: MetricType = MetricType.GAUGE,
    labels: Optional[Dict[str, str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record a metric using the global collector."""
    collector = get_global_collector()
    collector.record(dimension, value, metric_type, labels, metadata)
