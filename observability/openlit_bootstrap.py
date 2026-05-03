#!/usr/bin/env python3
"""Minimal observability bootstrap for Athena services.

Design goals:
- Service keeps working when OpenLIT / OpenTelemetry packages are absent.
- SigNoz OTLP export can be enabled purely through env vars.
- OpenLIT is optional sugar on top of OTel, not a hard dependency.
"""

from __future__ import annotations

import inspect
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

_BOOTSTRAP_LOCK = __import__("threading").Lock()
_BOOTSTRAP_STATE: dict[str, Any] = {
    "initialized": False,
    "status": None,
    "trace_api": None,
    "metrics_api": None,
}


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_otlp_endpoint(endpoint: str, signal: str, protocol: str) -> str:
    endpoint = endpoint.rstrip("/")
    if protocol == "http/protobuf":
        suffix = f"/v1/{signal}"
        if endpoint.endswith(suffix):
            return endpoint
        return endpoint + suffix
    return endpoint


@dataclass
class BootstrapStatus:
    enabled: bool
    provider: str
    exporter: str
    service_name: str
    endpoint: str
    protocol: str
    reason: str


class NullMetrics:
    def add(self, *args: Any, **kwargs: Any) -> None:
        return

    def record(self, *args: Any, **kwargs: Any) -> None:
        return


class ObservabilityRuntime:
    def __init__(self, status: BootstrapStatus):
        self.status = status
        self.tracer = None
        self.request_counter: Any = NullMetrics()
        self.error_counter: Any = NullMetrics()
        self.duration_histogram: Any = NullMetrics()

    @contextmanager
    def start_span(self, name: str, attributes: dict[str, Any] | None = None):
        if not self.tracer:
            yield None
            return
        with self.tracer.start_as_current_span(name) as span:
            for key, value in (attributes or {}).items():
                if value is None:
                    continue
                span.set_attribute(key, value)
            yield span

    def record_request(
        self,
        *,
        route: str,
        method: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        attrs = {
            "http.route": route,
            "http.method": method,
            "http.status_code": status_code,
            "athena.service": self.status.service_name,
        }
        self.request_counter.add(1, attrs)
        self.duration_histogram.record(duration_ms, attrs)
        if status_code >= 400:
            self.error_counter.add(1, attrs)


def _try_openlit_init(
    *,
    service_name: str,
    endpoint: str,
    headers: str,
    environment: str,
) -> tuple[bool, str]:
    if not _bool_env("ATHENA_OBSERVABILITY_USE_OPENLIT", False):
        return False, "openlit disabled"

    try:
        import openlit  # type: ignore[import-not-found]
    except Exception as exc:
        return False, f"openlit import failed: {exc}"

    kwargs: dict[str, Any] = {}
    signature = inspect.signature(openlit.init)
    supported = set(signature.parameters.keys())
    desired = {
        "application_name": service_name,
        "service_name": service_name,
        "environment": environment,
        "otlp_endpoint": endpoint,
        "otlp_headers": headers,
        "disable_batch": _bool_env("ATHENA_OBSERVABILITY_DISABLE_BATCH", False),
        "capture_message_content": _bool_env("ATHENA_OBSERVABILITY_CAPTURE_MESSAGE_CONTENT", False),
        "otlp_disable_metrics": not _bool_env("ATHENA_OBSERVABILITY_METRICS_ENABLED", True),
    }
    for key, value in desired.items():
        if key in supported and value not in {"", None}:
            kwargs[key] = value
    try:
        openlit.init(**kwargs)
    except Exception as exc:
        return False, f"openlit init failed: {exc}"
    return True, "openlit initialized"


def bootstrap_observability(service_name: str) -> ObservabilityRuntime:
    enabled = _bool_env("ATHENA_OBSERVABILITY_ENABLED", True)
    endpoint = os.getenv("ATHENA_OBSERVABILITY_OTLP_ENDPOINT", "").strip()
    protocol = os.getenv("ATHENA_OBSERVABILITY_OTLP_PROTOCOL", "http/protobuf").strip()
    headers = os.getenv("ATHENA_OBSERVABILITY_OTLP_HEADERS", "").strip()
    environment = os.getenv("ATHENA_OBSERVABILITY_ENVIRONMENT", "local").strip()

    if not enabled:
        return ObservabilityRuntime(
            BootstrapStatus(
                enabled=False,
                provider="none",
                exporter="none",
                service_name=service_name,
                endpoint="",
                protocol=protocol,
                reason="ATHENA_OBSERVABILITY_ENABLED=false",
            )
        )

    if not endpoint:
        return ObservabilityRuntime(
            BootstrapStatus(
                enabled=False,
                provider="none",
                exporter="none",
                service_name=service_name,
                endpoint="",
                protocol=protocol,
                reason="ATHENA_OBSERVABILITY_OTLP_ENDPOINT not set",
            )
        )

    try:
        from opentelemetry import metrics, trace  # type: ignore[import-not-found]
        from opentelemetry.sdk.metrics import (
            MeterProvider,  # type: ignore[import-not-found]
        )
        from opentelemetry.sdk.resources import (
            Resource,  # type: ignore[import-not-found]
        )
        from opentelemetry.sdk.trace import (
            TracerProvider,  # type: ignore[import-not-found]
        )
        from opentelemetry.sdk.trace.export import (  # type: ignore[import-not-found]
            BatchSpanProcessor,
            SimpleSpanProcessor,
        )
    except Exception as exc:
        return ObservabilityRuntime(
            BootstrapStatus(
                enabled=False,
                provider="none",
                exporter="none",
                service_name=service_name,
                endpoint=endpoint,
                protocol=protocol,
                reason=f"OpenTelemetry import failed: {exc}",
            )
        )

    with _BOOTSTRAP_LOCK:
        if not _BOOTSTRAP_STATE["initialized"]:
            resource = Resource.create(
                {
                    "service.name": service_name,
                    "service.namespace": "athena",
                    "deployment.environment": environment,
                }
            )

            exporter_name = "otlp-http"
            metric_exporter: Any = None
            trace_exporter: Any = None

            try:
                if protocol == "grpc":
                    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (  # type: ignore[import-not-found]
                        OTLPMetricExporter,
                    )
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import-not-found]
                        OTLPSpanExporter,
                    )

                    trace_exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
                    if _bool_env("ATHENA_OBSERVABILITY_METRICS_ENABLED", True):
                        metric_exporter = OTLPMetricExporter(endpoint=endpoint, headers=headers)
                    exporter_name = "otlp-grpc"
                else:
                    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (  # type: ignore[import-not-found]
                        OTLPMetricExporter,
                    )
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-not-found]
                        OTLPSpanExporter,
                    )

                    trace_exporter = OTLPSpanExporter(
                        endpoint=_normalize_otlp_endpoint(endpoint, "traces", "http/protobuf"),
                        headers=headers,
                    )
                    if _bool_env("ATHENA_OBSERVABILITY_METRICS_ENABLED", True):
                        metric_exporter = OTLPMetricExporter(
                            endpoint=_normalize_otlp_endpoint(endpoint, "metrics", "http/protobuf"),
                            headers=headers,
                        )
                    exporter_name = "otlp-http"
            except Exception as exc:
                return ObservabilityRuntime(
                    BootstrapStatus(
                        enabled=False,
                        provider="none",
                        exporter="none",
                        service_name=service_name,
                        endpoint=endpoint,
                        protocol=protocol,
                        reason=f"OTLP exporter setup failed: {exc}",
                    )
                )

            tracer_provider = TracerProvider(resource=resource)
            span_processor = (
                SimpleSpanProcessor(trace_exporter)
                if _bool_env("ATHENA_OBSERVABILITY_DISABLE_BATCH", False)
                else BatchSpanProcessor(trace_exporter)
            )
            tracer_provider.add_span_processor(span_processor)
            trace.set_tracer_provider(tracer_provider)

            if metric_exporter is not None:
                from opentelemetry.sdk.metrics.export import (  # type: ignore[import-not-found]
                    PeriodicExportingMetricReader,
                )

                metric_reader = PeriodicExportingMetricReader(metric_exporter)
                meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
                metrics.set_meter_provider(meter_provider)

            openlit_ok, openlit_reason = _try_openlit_init(
                service_name=service_name,
                endpoint=endpoint,
                headers=headers,
                environment=environment,
            )

            provider = "openlit" if openlit_ok else "opentelemetry"
            reason = openlit_reason if openlit_ok else "OpenTelemetry initialized"
            _BOOTSTRAP_STATE["initialized"] = True
            _BOOTSTRAP_STATE["trace_api"] = trace
            _BOOTSTRAP_STATE["metrics_api"] = metrics
            _BOOTSTRAP_STATE["status"] = BootstrapStatus(
                enabled=True,
                provider=provider,
                exporter=exporter_name,
                service_name=service_name,
                endpoint=endpoint,
                protocol=protocol,
                reason=reason,
            )

    runtime = ObservabilityRuntime(
        BootstrapStatus(
            enabled=True,
            provider=_BOOTSTRAP_STATE["status"].provider,
            exporter=_BOOTSTRAP_STATE["status"].exporter,
            service_name=service_name,
            endpoint=endpoint,
            protocol=protocol,
            reason=_BOOTSTRAP_STATE["status"].reason,
        )
    )
    runtime.tracer = _BOOTSTRAP_STATE["trace_api"].get_tracer(service_name, "0.1.0")
    meter = _BOOTSTRAP_STATE["metrics_api"].get_meter(service_name, "0.1.0")
    runtime.request_counter = meter.create_counter(
        "athena_adapter_requests_total",
        description="Total adapter HTTP requests",
    )
    runtime.error_counter = meter.create_counter(
        "athena_adapter_errors_total",
        description="Total adapter HTTP errors",
    )
    runtime.duration_histogram = meter.create_histogram(
        "athena_adapter_request_duration_ms",
        unit="ms",
        description="Adapter HTTP request duration",
    )
    return runtime
