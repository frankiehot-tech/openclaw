#!/usr/bin/env python3
"""Athena Observability Adapter.

P0-1 read-only adapter that normalizes current local truth sources into a
stable HTTP contract for observability tools such as Grafana, SigNoz, and
future dashboards.

Current implementation goals:
- Standard-library only HTTP service
- Read-only endpoints
- Reuse existing local truth sources
- Normalize snake_case payloads to camelCase contract fields
- Make stale/unavailable states explicit
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import time
from datetime import datetime
from email.utils import formatdate
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
MINI_AGENT_DIR = REPO_ROOT / "mini-agent"
CONTRACT_VERSION = "athena-observability.v1-draft"
DEFAULT_HOST = os.getenv("ATHENA_OBSERVABILITY_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("ATHENA_OBSERVABILITY_PORT", "8090"))
LOG_FILE = REPO_ROOT / "logs" / "athena_observability_adapter.log"
PID_FILE = REPO_ROOT / ".openclaw" / "athena_observability_adapter.pid"
PORT_FILE = REPO_ROOT / ".openclaw" / "athena_observability_adapter.port"
STATUS_FILE = REPO_ROOT / ".openclaw" / "athena_observability_adapter.status.json"

for path in (REPO_ROOT, SCRIPTS_DIR, MINI_AGENT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from athena_web_desktop_compat import (  # type: ignore[import-not-found]
    build_queue_payload,
    build_status_payload,
)
from observability.openlit_bootstrap import bootstrap_observability
from openclaw_roots import (  # type: ignore[import-not-found]
    AGENT_STATE_PATH,
    PLAN_CONFIG_PATH,
    QUEUE_STATE_DIR,
    RUNTIME_ROOT,
    TASKS_DIR,
    TASKS_PATH,
    TOKEN_FILE,
    WEB_PORT_FILE,
    validate_paths,
)
from system_resource_facts import (
    collect_resource_facts,  # type: ignore[import-not-found]
)

CHAT_RUNTIME_AVAILABLE = False
get_runtime = None
try:
    from agent.core.chat_runtime import (
        get_runtime as _get_runtime,  # type: ignore[import-not-found]
    )

    get_runtime = _get_runtime
    CHAT_RUNTIME_AVAILABLE = True
except Exception:
    pass

OBSERVABILITY = bootstrap_observability("athena-observability-adapter")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log_line(message: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(f"{now_iso()} {message}\n")


def write_runtime_files(host: str, port: int) -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    PORT_FILE.write_text(str(port) + "\n", encoding="utf-8")
    STATUS_FILE.write_text(
        json.dumps(
            {
                "service": "athena-observability-adapter",
                "pid": os.getpid(),
                "host": host,
                "port": port,
                "started_at": now_iso(),
                "runtime_root": str(RUNTIME_ROOT),
                "observability": {
                    "enabled": OBSERVABILITY.status.enabled,
                    "provider": OBSERVABILITY.status.provider,
                    "exporter": OBSERVABILITY.status.exporter,
                    "endpoint": OBSERVABILITY.status.endpoint,
                    "protocol": OBSERVABILITY.status.protocol,
                    "reason": OBSERVABILITY.status.reason,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def cleanup_runtime_files() -> None:
    for path in (PID_FILE, PORT_FILE):
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass


def safe_read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_iso(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value).timestamp()
    except Exception:
        return 0.0


def clamp_percent(value: Any, default: int = 0) -> int:
    try:
        number = int(round(float(value)))
    except Exception:
        number = default
    return max(0, min(100, number))


def bool_status(value: bool, ok: str = "ok", bad: str = "unavailable") -> str:
    return ok if value else bad


def path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except Exception:
        return False


def path_mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except Exception:
        return None


def freshness_from_paths(*paths: Path, stale_after_seconds: int = 900) -> str:
    mtimes = [mtime for path in paths if (mtime := path_mtime(path)) is not None]
    if not mtimes:
        return "unavailable"
    latest = max(mtimes)
    age = datetime.now().timestamp() - latest
    return "stale" if age > stale_after_seconds else "live"


def envelope(
    source: str,
    *,
    freshness: str = "live",
    message: str = "",
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "contractVersion": CONTRACT_VERSION,
        "generatedAt": now_iso(),
        "runtimeRoot": str(RUNTIME_ROOT),
        "source": source,
        "freshness": freshness,
        "message": message,
        "warnings": warnings or [],
    }


def queue_counts(source_counts: dict[str, Any] | None) -> dict[str, int]:
    payload = source_counts if isinstance(source_counts, dict) else {}
    return {
        "pending": int(payload.get("pending", 0) or 0),
        "running": int(payload.get("running", 0) or 0),
        "completed": int(payload.get("completed", 0) or 0),
        "failed": int(payload.get("failed", 0) or 0),
        "manual_hold": int(payload.get("manual_hold", 0) or 0),
    }


def read_tasks_index() -> dict[str, Any]:
    payload = safe_read_json(TASKS_PATH, {"version": 1, "tasks": []})
    if not isinstance(payload, dict):
        return {"version": 1, "tasks": []}
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        payload["tasks"] = []
    return payload


def task_dir_for(task_id: str) -> Path:
    return TASKS_DIR / task_id


def standard_task_directories() -> dict[str, str]:
    return {
        "workspace": "workspace",
        "inputs": "inputs",
        "outputs": "outputs",
        "evidence": "evidence",
        "checkpoints": "checkpoints",
    }


def task_trace_path(task_id: str) -> Path:
    return task_dir_for(task_id) / "trace.json"


def detect_text_preview(path: Path, max_chars: int = 1600) -> tuple[str | None, bool]:
    if not path.exists() or not path.is_file():
        return None, False
    if path.suffix.lower() not in {
        ".md",
        ".txt",
        ".log",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".csv",
        ".py",
        ".ts",
        ".js",
    }:
        return None, False
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None, False
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def task_candidate_artifacts(task_id: str) -> list[Path]:
    task_dir = task_dir_for(task_id)
    candidates: list[Path] = []

    task_payload = next(
        (
            item
            for item in read_tasks_index().get("tasks", [])
            if isinstance(item, dict) and str(item.get("id", "")) == task_id
        ),
        None,
    )
    if isinstance(task_payload, dict):
        artifact_path = str(task_payload.get("artifact_path", "") or "")
        if artifact_path:
            candidates.append(Path(artifact_path))

    trace = safe_read_json(task_trace_path(task_id), {})
    for artifact in trace.get("artifacts", []) if isinstance(trace, dict) else []:
        if not isinstance(artifact, dict):
            continue
        artifact_path = str(artifact.get("path", "") or "")
        if artifact_path:
            candidates.append(Path(artifact_path))

    standard_names = [
        "build.md",
        "plan.md",
        "review.md",
        "qa.md",
        "think.md",
        "artifact.md",
        "request.json",
        "stdout.log",
        "trace.json",
    ]
    for name in standard_names:
        candidates.append(task_dir / name)

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def map_queue_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "") or ""),
        "title": str(item.get("title", "") or ""),
        "status": str(item.get("status", "") or "pending"),
        "statusLabel": str(item.get("status_label", "") or ""),
        "entryStage": str(item.get("entry_stage", "") or "build"),
        "riskLevel": str(item.get("risk_level", "") or "medium"),
        "priority": str(item.get("priority", "") or ""),
        "lane": str(item.get("lane", "") or ""),
        "dependsOn": list(item.get("depends_on") or []),
        "instructionPath": str(item.get("instruction_path", "") or ""),
        "rootTaskId": str(item.get("root_task_id", "") or ""),
        "stage": str(item.get("stage", "") or ""),
        "executor": str(item.get("executor", "") or ""),
        "startedAt": str(item.get("started_at", "") or ""),
        "finishedAt": str(item.get("finished_at", "") or ""),
        "summary": str(item.get("summary", "") or ""),
        "artifactPath": str(item.get("artifact_path", "") or ""),
        "error": str(item.get("error", "") or ""),
        "resultExcerpt": str(item.get("result_excerpt", "") or ""),
        "pipelineSummary": str(item.get("pipeline_summary", "") or ""),
        "artifactPaths": list(item.get("artifact_paths") or []),
        "progressPercent": clamp_percent(item.get("progress_percent", 0)),
        "expectedStages": list(item.get("expected_stages") or []),
        "currentStageIds": list(item.get("current_stage_ids") or []),
        "runnerPid": item.get("runner_pid") if isinstance(item.get("runner_pid"), int) else None,
        "runnerHeartbeatAt": str(item.get("runner_heartbeat_at", "") or ""),
        "manualOverrideAutostart": bool(item.get("manual_override_autostart")),
        "retryable": bool(item.get("retryable", False)),
        "isCurrent": bool(item.get("is_current", False)),
    }


def build_health_payload() -> dict[str, Any]:
    warnings = list(validate_paths())
    if not OBSERVABILITY.status.enabled:
        warnings.append(f"observability exporter disabled: {OBSERVABILITY.status.reason}")
    path_checks = [
        {
            "name": "planConfigPath",
            "path": str(PLAN_CONFIG_PATH),
            "exists": path_exists(PLAN_CONFIG_PATH),
            "required": True,
            "status": "ok" if path_exists(PLAN_CONFIG_PATH) else "missing",
        },
        {
            "name": "queueStateDir",
            "path": str(QUEUE_STATE_DIR),
            "exists": path_exists(QUEUE_STATE_DIR),
            "required": False,
            "status": "ok" if path_exists(QUEUE_STATE_DIR) else "warning",
        },
        {
            "name": "tasksPath",
            "path": str(TASKS_PATH),
            "exists": path_exists(TASKS_PATH),
            "required": True,
            "status": "ok" if path_exists(TASKS_PATH) else "missing",
        },
        {
            "name": "tasksDir",
            "path": str(TASKS_DIR),
            "exists": path_exists(TASKS_DIR),
            "required": True,
            "status": "ok" if path_exists(TASKS_DIR) else "missing",
        },
        {
            "name": "agentStatePath",
            "path": str(AGENT_STATE_PATH),
            "exists": path_exists(AGENT_STATE_PATH),
            "required": False,
            "status": "ok" if path_exists(AGENT_STATE_PATH) else "warning",
        },
        {
            "name": "tokenFile",
            "path": str(TOKEN_FILE),
            "exists": path_exists(TOKEN_FILE),
            "required": False,
            "status": "ok" if path_exists(TOKEN_FILE) else "warning",
        },
        {
            "name": "webPortFile",
            "path": str(WEB_PORT_FILE),
            "exists": path_exists(WEB_PORT_FILE),
            "required": False,
            "status": "ok" if path_exists(WEB_PORT_FILE) else "warning",
        },
    ]

    dependency_status = {
        "queueSnapshot": "ok",
        "systemFacts": "ok",
        "tasksIndex": "ok",
        "chatRuntime": "ok" if CHAT_RUNTIME_AVAILABLE else "degraded",
    }

    try:
        build_queue_payload()
    except Exception as exc:
        dependency_status["queueSnapshot"] = "unavailable"
        warnings.append(f"queue snapshot unavailable: {exc}")

    try:
        collect_resource_facts()
    except Exception as exc:
        dependency_status["systemFacts"] = "unavailable"
        warnings.append(f"system facts unavailable: {exc}")

    try:
        read_tasks_index()
    except Exception as exc:
        dependency_status["tasksIndex"] = "unavailable"
        warnings.append(f"tasks index unavailable: {exc}")

    if CHAT_RUNTIME_AVAILABLE and get_runtime:
        try:
            runtime = get_runtime()
            runtime.get_chat_state()
        except Exception as exc:
            dependency_status["chatRuntime"] = "degraded"
            warnings.append(f"chat runtime degraded: {exc}")

    if not path_exists(RUNTIME_ROOT):
        status = "unavailable"
        freshness = "unavailable"
    elif any(item["status"] == "missing" for item in path_checks if item["required"]) or "unavailable" in dependency_status.values():
        status = "degraded"
        freshness = "live"
    else:
        status = "ok"
        freshness = "live"

    payload = envelope("adapter.health", freshness=freshness, warnings=warnings)
    payload.update(
        {
            "status": status,
            "adapterVersion": "0.1.0",
            "uptimeSeconds": 0,
            "paths": {
                "planConfigPath": str(PLAN_CONFIG_PATH),
                "queueStateDir": str(QUEUE_STATE_DIR),
                "tasksPath": str(TASKS_PATH),
                "tasksDir": str(TASKS_DIR),
                "agentStatePath": str(AGENT_STATE_PATH),
                "tokenFile": str(TOKEN_FILE),
                "webPortFile": str(WEB_PORT_FILE),
            },
            "pathChecks": path_checks,
            "dependencies": dependency_status,
        }
    )
    return payload


def build_system_facts_payload() -> dict[str, Any]:
    facts = collect_resource_facts()
    cpu = facts.get("cpu", {})
    memory = facts.get("memory", {})
    runner = facts.get("runner", {})
    payload = envelope(
        "system_resource_facts.py",
        freshness="live",
    )
    payload.update(
        {
            "sampledAt": facts.get("sampled_at", now_iso()),
            "cpu": {
                "usagePercent": float(cpu.get("usage_percent", 0.0) or 0.0),
                "userPercent": float(cpu.get("user_percent", 0.0) or 0.0),
                "systemPercent": float(cpu.get("system_percent", 0.0) or 0.0),
                "idlePercent": float(cpu.get("idle_percent", 0.0) or 0.0),
                "loadAverage1m": float((cpu.get("load_average") or [0.0, 0.0, 0.0])[0]),
                "loadAverage5m": float((cpu.get("load_average") or [0.0, 0.0, 0.0])[1]),
                "loadAverage15m": float((cpu.get("load_average") or [0.0, 0.0, 0.0])[2]),
                "cpuCount": int(cpu.get("core_count", os.cpu_count() or 1) or 1),
                "source": "top",
            },
            "memory": {
                "physMemUsedGb": float(memory.get("top_used_gb", 0.0) or 0.0),
                "physMemUnusedGb": float(memory.get("top_unused_gb", 0.0) or 0.0),
                "wiredGb": float(memory.get("wired_gb", 0.0) or 0.0),
                "compressorGb": float(memory.get("compressor_gb", 0.0) or 0.0),
                "totalGb": float(memory.get("total_gb", 0.0) or 0.0),
                "memoryPressurePercent": clamp_percent(memory.get("pressure_used_percent", 0)),
                "runnerFreeMemoryPercent": clamp_percent(runner.get("free_memory_percent", 0)),
                "availableGb": float(memory.get("available_gb", 0.0) or 0.0),
                "cachedGb": float(memory.get("cached_gb", 0.0) or 0.0),
                "reclaimableGb": float(memory.get("reclaimable_gb", 0.0) or 0.0),
                "appGb": float(memory.get("app_gb", 0.0) or 0.0),
                "compressedGb": float(memory.get("compressed_gb", 0.0) or 0.0),
                "topSource": "top",
                "pressureSource": "memory_pressure",
                "note": str(memory.get("note", "") or ""),
            },
            "runner": {
                "buildWorkerBudget": int(runner.get("budget", 0) or 0),
                "maxBuildWorkers": int(runner.get("max_build_workers", 1) or 1),
                "secondBuildMinFreeMemoryPercent": clamp_percent(
                    runner.get("second_build_min_free_memory_percent", 0)
                ),
                "maxBuildLoadPerCore": float(runner.get("max_build_load_per_core", 0.0) or 0.0),
                "maxBuildLoadAbsolute": float(runner.get("max_build_load_absolute", 0.0) or 0.0),
                "ollamaBusyCpuPercent": float(runner.get("ollama_busy_cpu_percent", 0.0) or 0.0),
                "reason": str(runner.get("reason", "") or ""),
            },
            "services": {"ollamaCpuPercent": float(runner.get("ollama_cpu_percent", 0.0) or 0.0)},
            "sourcesDetail": {
                "cpu": str((facts.get("sources") or {}).get("cpu", "top")),
                "memoryPressure": str(
                    (facts.get("sources") or {}).get("memory_pressure", "memory_pressure")
                ),
                "processCpu": str(
                    (facts.get("sources") or {}).get("ollama_cpu", "ps -axo comm=,pcpu=")
                ),
            },
        }
    )
    return payload


def build_queues_payload() -> dict[str, Any]:
    raw = build_queue_payload()
    freshness = freshness_from_paths(PLAN_CONFIG_PATH, QUEUE_STATE_DIR)
    payload = envelope(
        "athena_web_desktop_compat.py",
        freshness=freshness if freshness != "unavailable" else "live",
    )
    payload.update(
        {
            "found": bool(raw.get("found", False)),
            "configPath": str(raw.get("config_path", "") or PLAN_CONFIG_PATH),
            "counts": queue_counts(raw.get("counts")),
            "autoCounts": queue_counts(raw.get("auto_counts")),
            "manualCounts": queue_counts(raw.get("manual_counts")),
            "routes": [
                {
                    "routeId": str(route.get("route_id", "") or ""),
                    "queueId": str(route.get("queue_id", "") or ""),
                    "name": str(route.get("name", "") or ""),
                    "runnerMode": str(route.get("runner_mode", "") or ""),
                    "manifestPath": str(route.get("manifest_path", "") or ""),
                    "statePath": str(route.get("state_path", "") or ""),
                    "currentItemId": str(route.get("current_item_id", "") or ""),
                    "currentItemIds": list(route.get("current_item_ids") or []),
                    "counts": queue_counts(route.get("counts")),
                    "items": [
                        map_queue_item(item)
                        for item in (route.get("items") or [])
                        if isinstance(item, dict)
                    ],
                    "queueStatus": str(route.get("queue_status", "") or ""),
                    "pauseReason": str(route.get("pause_reason", "") or ""),
                    "nextActionHint": str(route.get("next_action_hint", "") or ""),
                    "message": str(route.get("message", "") or ""),
                }
                for route in (raw.get("routes") or [])
                if isinstance(route, dict)
            ],
        }
    )
    return payload


def build_tasks_recent_payload(limit: int = 50) -> dict[str, Any]:
    tasks_index = read_tasks_index()
    tasks = tasks_index.get("tasks", [])
    if not isinstance(tasks, list):
        tasks = []

    normalized: list[dict[str, Any]] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id", "") or "")
        task_dir = task_dir_for(task_id)
        normalized.append(
            {
                "id": task_id,
                "title": str(task.get("title", "") or ""),
                "queueItemId": str(task.get("queue_item_id", "") or ""),
                "stage": str(task.get("stage", "") or ""),
                "executor": str(task.get("executor", "") or ""),
                "status": str(task.get("status", "") or ""),
                "progressPercent": clamp_percent(task.get("progress_percent", 0)),
                "instructionPath": str(task.get("instruction_path", "") or ""),
                "artifactPath": str(task.get("artifact_path", "") or ""),
                "summary": str(task.get("summary", "") or ""),
                "error": str(task.get("error", "") or ""),
                "createdAt": str(task.get("created_at", "") or ""),
                "startedAt": str(task.get("started_at", "") or ""),
                "finishedAt": str(task.get("finished_at", "") or ""),
                "updatedAt": str(task.get("updated_at", "") or ""),
                "taskDir": str(task_dir),
                "tracePath": str(task_trace_path(task_id)),
                "queueConfig": (
                    task.get("queue_config") if isinstance(task.get("queue_config"), dict) else None
                ),
            }
        )

    normalized.sort(key=lambda item: parse_iso(item["updatedAt"]), reverse=True)
    limited = normalized[: max(1, limit)]
    payload = envelope(
        "tasks.json",
        freshness=freshness_from_paths(TASKS_PATH),
    )
    payload.update(
        {
            "tasksPath": str(TASKS_PATH),
            "version": int(tasks_index.get("version", 1) or 1),
            "total": len(normalized),
            "limit": max(1, limit),
            "tasks": limited,
        }
    )
    return payload


def build_task_trace_payload(task_id: str) -> tuple[int, dict[str, Any]]:
    task_dir = task_dir_for(task_id)
    trace_path = task_trace_path(task_id)
    payload = envelope(
        "trace.json",
        freshness=freshness_from_paths(trace_path, stale_after_seconds=1800),
    )

    if not trace_path.exists():
        payload.update(
            {
                "message": "trace.json not found",
                "taskId": task_id,
                "taskDir": str(task_dir),
                "tracePath": str(trace_path),
                "createdAt": now_iso(),
                "version": "1.0",
                "events": [],
                "artifacts": [],
                "statusChanges": [],
                "directories": standard_task_directories(),
            }
        )
        payload["freshness"] = "unavailable"
        return HTTPStatus.NOT_FOUND, payload

    trace = safe_read_json(trace_path, {})
    artifacts = []
    for artifact in trace.get("artifacts", []) if isinstance(trace, dict) else []:
        if not isinstance(artifact, dict):
            continue
        artifacts.append(
            {
                "timestamp": str(artifact.get("timestamp", "") or ""),
                "artifactType": str(artifact.get("artifact_type", "") or ""),
                "path": str(artifact.get("path", "") or ""),
                "metadata": (
                    artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
                ),
            }
        )

    status_changes = []
    for change in trace.get("status_changes", []) if isinstance(trace, dict) else []:
        if not isinstance(change, dict):
            continue
        status_changes.append(
            {
                "timestamp": str(change.get("timestamp", "") or ""),
                "oldStatus": str(change.get("old_status", "") or ""),
                "newStatus": str(change.get("new_status", "") or ""),
                "reason": str(change.get("reason", "") or ""),
            }
        )

    payload.update(
        {
            "taskId": str(trace.get("task_id", task_id) or task_id),
            "taskDir": str(task_dir),
            "tracePath": str(trace_path),
            "createdAt": str(trace.get("created_at", "") or ""),
            "version": str(trace.get("version", "1.0") or "1.0"),
            "events": [
                {
                    "timestamp": str(event.get("timestamp", "") or ""),
                    "type": str(event.get("type", "") or ""),
                    "data": event.get("data") if isinstance(event.get("data"), dict) else {},
                }
                for event in (trace.get("events") or [])
                if isinstance(event, dict)
            ],
            "artifacts": artifacts,
            "statusChanges": status_changes,
            "directories": (
                trace.get("directories")
                if isinstance(trace.get("directories"), dict)
                else standard_task_directories()
            ),
        }
    )
    return HTTPStatus.OK, payload


def build_task_artifact_payload(
    task_id: str, selected_path: str | None = None
) -> tuple[int, dict[str, Any]]:
    task_dir = task_dir_for(task_id)
    payload = envelope(
        "task-artifact",
        freshness=freshness_from_paths(task_dir, stale_after_seconds=1800),
    )
    if not task_dir.exists():
        payload.update(
            {
                "message": "task directory not found",
                "taskId": task_id,
                "taskDir": str(task_dir),
                "selectedArtifactPath": None,
                "primaryArtifactPath": None,
                "artifacts": [],
            }
        )
        payload["freshness"] = "unavailable"
        return HTTPStatus.NOT_FOUND, payload

    artifacts_payload: list[dict[str, Any]] = []
    candidates = task_candidate_artifacts(task_id)
    primary_artifact_path: str | None = None
    selected_artifact_path: str | None = None
    if selected_path:
        selected_artifact_path = str((task_dir / selected_path).resolve())

    for candidate in candidates:
        exists = candidate.exists()
        preview_text, preview_truncated = detect_text_preview(candidate)
        mime_type, _ = mimetypes.guess_type(str(candidate))
        stage = None
        if candidate.stem in {"build", "plan", "review", "qa", "think"}:
            stage = candidate.stem
        if primary_artifact_path is None and exists:
            primary_artifact_path = str(candidate)
        if selected_artifact_path == str(candidate):
            selected_artifact_path = str(candidate)
        artifacts_payload.append(
            {
                "name": candidate.name,
                "path": str(candidate),
                "kind": (
                    "trace"
                    if candidate.name == "trace.json"
                    else (
                        "request"
                        if candidate.name == "request.json"
                        else "log" if candidate.suffix.lower() == ".log" else "artifact"
                    )
                ),
                "stage": stage,
                "exists": exists,
                "sizeBytes": candidate.stat().st_size if exists else None,
                "mimeType": mime_type,
                "updatedAt": (
                    datetime.fromtimestamp(candidate.stat().st_mtime)
                    .astimezone()
                    .isoformat(timespec="seconds")
                    if exists
                    else None
                ),
                "previewText": preview_text,
                "previewTruncated": preview_truncated,
            }
        )

    payload.update(
        {
            "taskId": task_id,
            "taskDir": str(task_dir),
            "selectedArtifactPath": selected_artifact_path,
            "primaryArtifactPath": primary_artifact_path,
            "artifacts": artifacts_payload,
        }
    )
    return HTTPStatus.OK, payload


def build_chat_status_payload() -> dict[str, Any]:
    warnings: list[str] = []
    freshness = "live"
    payload = envelope("chat_runtime.py", freshness=freshness, warnings=warnings)

    if not CHAT_RUNTIME_AVAILABLE or not get_runtime:
        payload.update(
            {
                "freshness": "unavailable",
                "message": "chat runtime unavailable",
                "chatState": "unknown",
                "chatBackend": "unknown",
                "chatSelectedModel": "unknown",
                "chatReason": "chat runtime import failed",
                "chatPrimary": {"providerId": "unknown", "modelId": "unknown"},
                "chatFallback": {"providerId": "unknown", "modelId": "unknown"},
                "timestamp": datetime.now().timestamp(),
            }
        )
        return payload

    runtime = get_runtime()
    state = runtime.get_chat_state()
    probe_payload = None
    try:
        probe = runtime.probe_status(force=False)
        probe_payload = {
            "timestamp": float(probe.get("timestamp", datetime.now().timestamp())),
            "overall": str(probe.get("overall", "healthy") or "healthy"),
            "degradedReason": str(probe.get("degraded_reason", "") or ""),
            "primary": {
                "providerId": str((probe.get("primary") or {}).get("provider_id", "") or ""),
                "healthy": bool((probe.get("primary") or {}).get("healthy", False)),
                "reason": str((probe.get("primary") or {}).get("reason", "") or ""),
                "envKeyMissing": bool((probe.get("primary") or {}).get("env_key_missing", False)),
                "hasAuthKey": bool((probe.get("primary") or {}).get("has_auth_key", False)),
                "baseUrl": (probe.get("primary") or {}).get("base_url"),
            },
            "fallback": {
                "providerId": str((probe.get("fallback") or {}).get("provider_id", "") or ""),
                "healthy": bool((probe.get("fallback") or {}).get("healthy", False)),
                "reason": str((probe.get("fallback") or {}).get("reason", "") or ""),
                "envKeyMissing": bool((probe.get("fallback") or {}).get("env_key_missing", False)),
                "hasAuthKey": bool((probe.get("fallback") or {}).get("has_auth_key", False)),
                "baseUrl": (probe.get("fallback") or {}).get("base_url"),
            },
        }
    except Exception as exc:
        warnings.append(f"chat probe unavailable: {exc}")

    payload.update(
        {
            "chatState": str(state.get("chat_state", "unknown") or "unknown"),
            "chatBackend": str(state.get("chat_backend", "unknown") or "unknown"),
            "chatSelectedModel": str(state.get("chat_selected_model", "unknown") or "unknown"),
            "chatReason": str(state.get("chat_reason", "") or ""),
            "chatPrimary": {
                "providerId": str((state.get("chat_primary") or {}).get("provider_id", "") or ""),
                "modelId": str((state.get("chat_primary") or {}).get("model_id", "") or ""),
            },
            "chatFallback": {
                "providerId": str(
                    (state.get("chat_fallback") or {}).get("provider_id", "") or ""
                ),
                "modelId": str((state.get("chat_fallback") or {}).get("model_id", "") or ""),
            },
            "timestamp": float(state.get("timestamp", datetime.now().timestamp())),
        }
    )
    if probe_payload is not None:
        payload["probe"] = probe_payload
    return payload


def build_agents_payload() -> dict[str, Any]:
    status = build_status_payload()
    queues = build_queues_payload()
    tasks = build_tasks_recent_payload(limit=200)
    agent_state = safe_read_json(AGENT_STATE_PATH, {})

    running_tasks = [task for task in tasks["tasks"] if task["status"] == "running"]
    plan_review_task = next(
        (task for task in running_tasks if task["stage"] in {"plan", "review"}), None
    )
    build_task = next((task for task in running_tasks if task["stage"] == "build"), None)
    local_task = next(
        (task for task in running_tasks if task["stage"] in {"think", "qa", "browse"}),
        None,
    )

    bridge = status.get("bridge", {}) if isinstance(status, dict) else {}
    guardian_status = str(bridge.get("guardian", "unknown") or "unknown")
    chat = build_chat_status_payload()

    agents = [
        {
            "agentId": "athena",
            "displayName": "Athena",
            "role": "orchestrator",
            "layer": "core",
            "status": "online",
            "statusDetail": f"mode={agent_state.get('mode', 'unknown')}",
            "currentTask": build_task["title"] if build_task else "",
            "currentTaskId": build_task["id"] if build_task else "",
            "currentQueueItemId": build_task["queueItemId"] if build_task else "",
            "currentStage": build_task["stage"] if build_task else "",
            "executor": "athena",
            "provider": "",
            "model": "",
            "skills": [],
            "capabilities": ["route", "orchestrate", "dispatch"],
            "parentAgentId": None,
            "sourceKind": "core_role",
            "lastSeenAt": str(agent_state.get("updated_at", "") or None),
            "links": {
                "taskTracePath": build_task["tracePath"] if build_task else None,
                "artifactPath": build_task["artifactPath"] if build_task else None,
            },
        },
        {
            "agentId": "queue-runner",
            "displayName": "Queue Runner",
            "role": "queue_runner",
            "layer": "core",
            "status": "running" if queues["counts"]["running"] > 0 else "idle",
            "statusDetail": f"routes={len(queues['routes'])}",
            "currentTask": build_task["title"] if build_task else "",
            "currentTaskId": build_task["id"] if build_task else "",
            "currentQueueItemId": build_task["queueItemId"] if build_task else "",
            "currentStage": build_task["stage"] if build_task else "",
            "executor": "runner",
            "provider": "",
            "model": "",
            "skills": [],
            "capabilities": ["queue", "retry", "launch"],
            "parentAgentId": "athena",
            "sourceKind": "queue_runner",
            "lastSeenAt": build_task["updatedAt"] if build_task else None,
            "links": {
                "taskTracePath": build_task["tracePath"] if build_task else None,
                "artifactPath": build_task["artifactPath"] if build_task else None,
            },
        },
        {
            "agentId": "guardian",
            "displayName": "Guardian",
            "role": "health_guard",
            "layer": "core",
            "status": "running" if guardian_status == "running" else "offline",
            "statusDetail": guardian_status,
            "currentTask": "",
            "currentTaskId": "",
            "currentQueueItemId": "",
            "currentStage": "",
            "executor": "guardian",
            "provider": "",
            "model": "",
            "skills": [],
            "capabilities": ["healthcheck", "watchdog"],
            "parentAgentId": "athena",
            "sourceKind": "service",
            "lastSeenAt": None,
            "links": {"taskTracePath": None, "artifactPath": None},
        },
        {
            "agentId": "chat-runtime",
            "displayName": "Chat Runtime",
            "role": "chat_router",
            "layer": "core",
            "status": (
                "degraded"
                if chat["chatState"] in {"fallback_only", "degraded"}
                else "online" if chat["chatState"] == "ok" else "idle"
            ),
            "statusDetail": chat["chatReason"],
            "currentTask": "",
            "currentTaskId": "",
            "currentQueueItemId": "",
            "currentStage": "",
            "executor": "chat-runtime",
            "provider": chat["chatBackend"],
            "model": chat["chatSelectedModel"],
            "skills": [],
            "capabilities": ["chat", "fallback", "probe"],
            "parentAgentId": "athena",
            "sourceKind": "service",
            "lastSeenAt": chat["generatedAt"],
            "links": {"taskTracePath": None, "artifactPath": None},
        },
        {
            "agentId": "codex",
            "displayName": "Codex",
            "role": "plan_review_executor",
            "layer": "executor",
            "status": "running" if plan_review_task else "idle",
            "statusDetail": plan_review_task["status"] if plan_review_task else "idle",
            "currentTask": plan_review_task["title"] if plan_review_task else "",
            "currentTaskId": plan_review_task["id"] if plan_review_task else "",
            "currentQueueItemId": plan_review_task["queueItemId"] if plan_review_task else "",
            "currentStage": plan_review_task["stage"] if plan_review_task else "",
            "executor": "codex",
            "provider": "openai",
            "model": "",
            "skills": [],
            "capabilities": ["plan", "review"],
            "parentAgentId": "athena",
            "sourceKind": "core_role",
            "lastSeenAt": plan_review_task["updatedAt"] if plan_review_task else None,
            "links": {
                "taskTracePath": plan_review_task["tracePath"] if plan_review_task else None,
                "artifactPath": plan_review_task["artifactPath"] if plan_review_task else None,
            },
        },
        {
            "agentId": "opencode",
            "displayName": "OpenCode",
            "role": "build_executor",
            "layer": "executor",
            "status": "running" if build_task else "idle",
            "statusDetail": build_task["status"] if build_task else "idle",
            "currentTask": build_task["title"] if build_task else "",
            "currentTaskId": build_task["id"] if build_task else "",
            "currentQueueItemId": build_task["queueItemId"] if build_task else "",
            "currentStage": build_task["stage"] if build_task else "",
            "executor": "opencode",
            "provider": "",
            "model": "",
            "skills": [],
            "capabilities": ["build"],
            "parentAgentId": "athena",
            "sourceKind": "core_role",
            "lastSeenAt": build_task["updatedAt"] if build_task else None,
            "links": {
                "taskTracePath": build_task["tracePath"] if build_task else None,
                "artifactPath": build_task["artifactPath"] if build_task else None,
            },
        },
        {
            "agentId": "local",
            "displayName": "Local",
            "role": "local_executor",
            "layer": "executor",
            "status": "running" if local_task else "idle",
            "statusDetail": local_task["status"] if local_task else "idle",
            "currentTask": local_task["title"] if local_task else "",
            "currentTaskId": local_task["id"] if local_task else "",
            "currentQueueItemId": local_task["queueItemId"] if local_task else "",
            "currentStage": local_task["stage"] if local_task else "",
            "executor": "local",
            "provider": "",
            "model": "",
            "skills": [],
            "capabilities": ["think", "qa", "browse"],
            "parentAgentId": "athena",
            "sourceKind": "core_role",
            "lastSeenAt": local_task["updatedAt"] if local_task else None,
            "links": {
                "taskTracePath": local_task["tracePath"] if local_task else None,
                "artifactPath": local_task["artifactPath"] if local_task else None,
            },
        },
    ]

    online = sum(1 for agent in agents if agent["status"] != "offline")
    running = sum(1 for agent in agents if agent["status"] == "running")
    degraded = sum(1 for agent in agents if agent["status"] == "degraded")
    idle = sum(1 for agent in agents if agent["status"] == "idle")
    payload = envelope(
        "adapter.agents",
        freshness="live",
    )
    payload.update(
        {
            "counts": {
                "total": len(agents),
                "online": online,
                "offline": len(agents) - online,
                "running": running,
                "idle": idle,
                "degraded": degraded,
            },
            "agents": agents,
        }
    )
    return payload


def build_node_graph_payload() -> dict[str, Any]:
    agents = build_agents_payload()
    queues = build_queues_payload()
    tasks = build_tasks_recent_payload(limit=30)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for agent in agents["agents"]:
        nodes.append(
            {
                "id": f"agent:{agent['agentId']}",
                "title": agent["displayName"],
                "subtitle": agent["role"],
                "kind": "agent",
                "status": agent["status"],
                "mainStat": agent["currentStage"] or agent["status"],
                "secondaryStat": agent["currentTask"] or agent["statusDetail"],
                "color": (
                    "green"
                    if agent["status"] == "running"
                    else (
                        "yellow"
                        if agent["status"] == "degraded"
                        else "blue" if agent["status"] == "online" else "gray"
                    )
                ),
                "icon": "agent",
                "detailPath": f"/v1/agents#{agent['agentId']}",
                "data": agent,
            }
        )
        if agent["parentAgentId"]:
            edges.append(
                {
                    "id": f"owns:{agent['parentAgentId']}->{agent['agentId']}",
                    "sourceId": f"agent:{agent['parentAgentId']}",
                    "targetId": f"agent:{agent['agentId']}",
                    "relation": "owns",
                    "status": "active",
                    "mainStat": agent["role"],
                    "secondaryStat": "",
                    "detailPath": None,
                    "data": {},
                }
            )

    for route in queues["routes"]:
        queue_node_id = f"queue:{route['routeId']}"
        nodes.append(
            {
                "id": queue_node_id,
                "title": route["name"],
                "subtitle": route["runnerMode"],
                "kind": "queue",
                "status": route["queueStatus"],
                "mainStat": route["queueStatus"],
                "secondaryStat": f"running={route['counts']['running']}",
                "color": "purple",
                "icon": "queue",
                "detailPath": "/v1/queues",
                "data": route,
            }
        )
        edges.append(
            {
                "id": f"runs:agent:queue-runner->{queue_node_id}",
                "sourceId": "agent:queue-runner",
                "targetId": queue_node_id,
                "relation": "runs",
                "status": route["queueStatus"],
                "mainStat": route["runnerMode"],
                "secondaryStat": route["nextActionHint"],
                "detailPath": "/v1/queues",
                "data": {},
            }
        )
        for item in route["items"]:
            item_node_id = f"item:{route['routeId']}:{item['id']}"
            nodes.append(
                {
                    "id": item_node_id,
                    "title": item["title"],
                    "subtitle": item["entryStage"],
                    "kind": "item",
                    "status": item["status"],
                    "mainStat": f"{item['progressPercent']}%",
                    "secondaryStat": item["executor"] or item["stage"],
                    "color": "orange" if item["isCurrent"] else "gray",
                    "icon": "item",
                    "detailPath": "/v1/queues",
                    "data": item,
                }
            )
            edges.append(
                {
                    "id": f"contains:{queue_node_id}->{item_node_id}",
                    "sourceId": queue_node_id,
                    "targetId": item_node_id,
                    "relation": "contains",
                    "status": item["status"],
                    "mainStat": item["status"],
                    "secondaryStat": "",
                    "detailPath": "/v1/queues",
                    "data": {},
                }
            )
            for dep_id in item["dependsOn"]:
                edges.append(
                    {
                        "id": f"depends:{item_node_id}->{route['routeId']}:{dep_id}",
                        "sourceId": item_node_id,
                        "targetId": f"item:{route['routeId']}:{dep_id}",
                        "relation": "depends_on",
                        "status": "active",
                        "mainStat": "depends_on",
                        "secondaryStat": "",
                        "detailPath": "/v1/queues",
                        "data": {},
                    }
                )

    for task in tasks["tasks"]:
        node_id = f"task:{task['id']}"
        nodes.append(
            {
                "id": node_id,
                "title": task["title"],
                "subtitle": task["stage"],
                "kind": "task",
                "status": task["status"],
                "mainStat": f"{task['progressPercent']}%",
                "secondaryStat": task["executor"],
                "color": "red" if task["status"] == "failed" else "green",
                "icon": "task",
                "detailPath": f"/v1/tasks/{task['id']}/trace",
                "data": task,
            }
        )
        if task["queueItemId"]:
            edges.append(
                {
                    "id": f"produces:item->{node_id}:{task['queueItemId']}",
                    "sourceId": f"item:*:{task['queueItemId']}",
                    "targetId": node_id,
                    "relation": "produces",
                    "status": task["status"],
                    "mainStat": task["stage"],
                    "secondaryStat": task["executor"],
                    "detailPath": f"/v1/tasks/{task['id']}/trace",
                    "data": {},
                }
            )

    payload = envelope("adapter.node-graph", freshness="live")
    payload.update(
        {
            "graphId": "athena-runtime",
            "nodes": nodes,
            "edges": edges,
        }
    )
    return payload


def route_request(path: str, query: dict[str, list[str]]) -> tuple[int, dict[str, Any]]:
    if path == "/health":
        return HTTPStatus.OK, build_health_payload()
    if path == "/v1/system/facts":
        return HTTPStatus.OK, build_system_facts_payload()
    if path == "/v1/queues":
        return HTTPStatus.OK, build_queues_payload()
    if path == "/v1/tasks/recent":
        limit = 50
        try:
            limit = int((query.get("limit") or ["50"])[0])
        except Exception:
            limit = 50
        return HTTPStatus.OK, build_tasks_recent_payload(limit=limit)
    trace_match = re.fullmatch(r"/v1/tasks/([^/]+)/trace", path)
    if trace_match:
        return build_task_trace_payload(unquote(trace_match.group(1)))
    artifact_match = re.fullmatch(r"/v1/tasks/([^/]+)/artifact", path)
    if artifact_match:
        selected = (query.get("path") or [None])[0]
        return build_task_artifact_payload(unquote(artifact_match.group(1)), selected)
    if path == "/v1/chat/status":
        return HTTPStatus.OK, build_chat_status_payload()
    if path == "/v1/agents":
        return HTTPStatus.OK, build_agents_payload()
    if path == "/v1/node-graph":
        return HTTPStatus.OK, build_node_graph_payload()

    return HTTPStatus.NOT_FOUND, {
        **envelope("adapter.route", freshness="unavailable", message="route not found"),
        "path": path,
    }


class ObservabilityHandler(BaseHTTPRequestHandler):
    server_version = "AthenaObservabilityAdapter/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        log_line(
            f"{self.address_string()} - - [{self.log_date_time_string()}] {format % args}"
        )

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Date", formatdate(usegmt=True))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        started = time.perf_counter()
        with OBSERVABILITY.start_span(
            "athena.adapter.http_request",
            {
                "http.route": parsed.path,
                "http.method": "GET",
                "athena.runtime_root": str(RUNTIME_ROOT),
            },
        ) as span:
            status, payload = route_request(parsed.path, parse_qs(parsed.query))
            if span is not None:
                span.set_attribute("http.status_code", int(status))
                span.set_attribute("athena.adapter.source", str(payload.get("source", "")))
                span.set_attribute("athena.adapter.freshness", str(payload.get("freshness", "")))
        OBSERVABILITY.record_request(
            route=parsed.path,
            method="GET",
            status_code=int(status),
            duration_ms=(time.perf_counter() - started) * 1000,
        )
        self._send_json(status, payload)


def serve(host: str, port: int) -> None:
    write_runtime_files(host, port)
    server = ThreadingHTTPServer((host, port), ObservabilityHandler)
    server.daemon_threads = True
    print(f"Athena Observability Adapter listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        cleanup_runtime_files()


def main() -> int:
    parser = argparse.ArgumentParser(description="Athena Observability Adapter")
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Bind host (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Bind port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--dump",
        metavar="PATH",
        help="Print JSON payload for a route, e.g. /health or /v1/queues",
    )
    args = parser.parse_args()

    if args.dump:
        parsed = urlparse(args.dump)
        _, payload = route_request(parsed.path, parse_qs(parsed.query))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
