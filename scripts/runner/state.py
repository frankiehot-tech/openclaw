#!/usr/bin/env python3
"""state"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)


_scripts_dir = Path(__file__).resolve().parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

try:
    from .openclaw_roots import (
        RUNTIME_ROOT,
    )
except ImportError:
    import sys

    from openclaw_roots import (
        RUNTIME_ROOT,
    )

try:
    from . import system_resource_facts as resource_facts
except ImportError:
    import system_resource_facts as resource_facts

# ── Module-level stubs (event bus, parallel gate, state sync) ────────────

# # Event bus with fallback stubs
# Import event bus for hook/event system
try:
    mini_agent_path = RUNTIME_ROOT / "mini-agent"
    if str(mini_agent_path) not in sys.path:
        sys.path.insert(0, str(mini_agent_path))
    from agent.core.event_bus import (
        EventEnvelope,
        EventType,
        HookPoint,
        emit,
        get_bus,
    )

    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

    # Create dummy enum-like classes
    class _EventType:
        PROMPT = "prompt"
        TASK = "task"
        TOOL = "tool"
        ARTIFACT = "artifact"
        REVIEW = "review"
        HOOK = "hook"

    EventType = _EventType()

    class _HookPoint:
        PRE_TOOL = "pre-tool"
        POST_TOOL = "post-tool"
        TASK_START = "task-start"
        TASK_FINISH = "task-finish"
        ARTIFACT_WRITTEN = "artifact-written"
        PRE_PROMPT = "pre-prompt"
        POST_PROMPT = "post-prompt"
        PRE_REVIEW = "pre-review"
        POST_REVIEW = "post-review"

    HookPoint = _HookPoint()

    class _EventEnvelope:
        pass

    EventEnvelope = _EventEnvelope

    class _EventBusStub:
        def emit(self, *args, **kwargs):
            return None

        def register_hook(self, *args, **kwargs):
            pass

        def register_event_listener(self, *args, **kwargs):
            pass

    _stub = _EventBusStub()

    def _noop_get_bus():
        return _stub

    get_bus = _noop_get_bus
    emit = _stub.emit

# # State sync contract
# State sync contract for consistent state management
try:
    # Contracts are in the parent directory of scripts
    contracts_dir = Path(__file__).resolve().parent.parent / "contracts"
    if str(contracts_dir) not in sys.path:
        sys.path.insert(0, str(contracts_dir))

    STATE_SYNC_AVAILABLE = True
    logger.info("StateSyncContract available for consistent state management")
except ImportError as e:
    STATE_SYNC_AVAILABLE = False
    logger.warning(f"StateSyncContract not available: {e}. State consistency features disabled.")

# # Parallel build gate with fallback stubs
try:
    from agent.core.parallel_build_gate import (
        AdmissionDecision,
        check_parallel_admission,
        get_global_gate,
        get_scheduling_summary,
    )

    PARALLEL_BUILD_GATE_AVAILABLE = True
except ImportError:
    PARALLEL_BUILD_GATE_AVAILABLE = False

    # Create dummy functions for fallback
    class _ParallelBuildGateStub:
        def check_admission(self, requested_workers=2):
            # Fallback to dynamic_build_worker_budget
            budget, telemetry = resource_facts.dynamic_build_worker_budget(
                max_build_workers=requested_workers,
                second_build_min_free_memory_percent=int(
                    os.getenv("ATHENA_AI_PLAN_SECOND_BUILD_MIN_FREE_MEMORY_PERCENT", "35")
                ),
                max_build_load_per_core=float(
                    os.getenv("ATHENA_AI_PLAN_MAX_BUILD_LOAD_PER_CORE", "0.6")
                ),
                max_build_load_absolute=float(
                    os.getenv("ATHENA_AI_PLAN_MAX_BUILD_LOAD_ABSOLUTE", "6.0")
                ),
                ollama_busy_cpu_percent=float(
                    os.getenv("ATHENA_AI_PLAN_OLLAMA_BUSY_CPU_PERCENT", "35")
                ),
            )
            return type(
                "AdmissionResult",
                (),
                {
                    "decision": (
                        "APPROVED"
                        if budget >= requested_workers
                        else "DEGRADED"
                        if budget >= 1
                        else "REJECTED"
                    ),
                    "allowed_workers": budget,
                    "reason": telemetry.get("reason", "fallback"),
                    "resource_checks": [],
                    "suggested_action": "",
                    "metadata": {"telemetry": telemetry},
                },
            )()

        def register_task(self, task_id, workspace_dir=None):
            return True

        def unregister_task(self, task_id):
            return True

        def validate_isolation(self, task_id, proposed_paths):
            # 存根始终返回通过
            return True, []

        def get_isolation_constraints(self, task_id):
            # 返回空列表
            return []

        def generate_scheduling_summary(self):
            budget, telemetry = resource_facts.dynamic_build_worker_budget(
                max_build_workers=max(1, int(os.getenv("ATHENA_AI_PLAN_MAX_BUILD_WORKERS", "2"))),
                second_build_min_free_memory_percent=int(
                    os.getenv("ATHENA_AI_PLAN_SECOND_BUILD_MIN_FREE_MEMORY_PERCENT", "35")
                ),
                max_build_load_per_core=float(
                    os.getenv("ATHENA_AI_PLAN_MAX_BUILD_LOAD_PER_CORE", "0.6")
                ),
                max_build_load_absolute=float(
                    os.getenv("ATHENA_AI_PLAN_MAX_BUILD_LOAD_ABSOLUTE", "6.0")
                ),
                ollama_busy_cpu_percent=float(
                    os.getenv("ATHENA_AI_PLAN_OLLAMA_BUSY_CPU_PERCENT", "35")
                ),
            )
            return type(
                "SchedulingSummary",
                (),
                {
                    "current_workers": budget,
                    "max_workers": 2,
                    "admission_result": type(
                        "AdmissionResult",
                        (),
                        {
                            "decision": (
                                "APPROVED"
                                if budget >= 2
                                else "DEGRADED"
                                if budget >= 1
                                else "REJECTED"
                            ),
                            "allowed_workers": budget,
                            "reason": telemetry.get("reason", "fallback"),
                        },
                    )(),
                    "active_task_ids": [],
                    "resource_snapshot": telemetry,
                    "generated_at": time.time(),
                },
            )()

    _parallel_gate_stub = _ParallelBuildGateStub()

    def _noop_get_global_gate():
        return _parallel_gate_stub

    get_global_gate = _noop_get_global_gate

    def check_parallel_admission(workers=2):
        return _parallel_gate_stub.check_admission(workers)

    def get_scheduling_summary():
        return _parallel_gate_stub.generate_scheduling_summary()

    AdmissionDecision = type(
        "AdmissionDecision",
        (),
        {
            "APPROVED": "approved",
            "REJECTED": "rejected",
            "DEGRADED": "degraded",
            "MANUAL_HOLD": "manual_hold",
        },
    )

# # Performance metrics
# Performance metrics collection
try:
    from agent.core.performance_metrics import (
        get_global_collector,
    )

    PERFORMANCE_METRICS_AVAILABLE = True
except ImportError:
    PERFORMANCE_METRICS_AVAILABLE = False


def emit_event(event_type, scope, payload, metadata=None, evidence=None, hook_point=None):
    """Emit an event via the bus if available, otherwise no-op."""
    try:
        if EVENT_BUS_AVAILABLE and emit is not None:
            return emit(event_type, scope, payload, metadata, evidence, hook_point)
    except Exception:
        pass
    return None


def record_performance_metric(dimension, value, labels=None, metadata=None):
    """Record a performance metric if metrics collection is available."""
    try:
        if PERFORMANCE_METRICS_AVAILABLE:
            from agent.core.performance_metrics import MetricDimension, MetricType

            # Convert string dimension to enum if needed
            if isinstance(dimension, str):
                dimension = MetricDimension[dimension]
            get_global_collector().record(
                dimension=dimension,
                value=value,
                metric_type=MetricType.GAUGE,
                labels=labels or {},
                metadata=metadata or {},
            )
    except Exception:
        pass  # Silently fail if metrics collection fails
