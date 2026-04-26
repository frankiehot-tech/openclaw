#!/usr/bin/env python3
"""config"""

from __future__ import annotations

import logging
import os
import sys
import time
import json
import re
import shutil
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_scripts_dir = Path(__file__).resolve().parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

try:
    from .openclaw_roots import (
        LOG_DIR,
        PLAN_CONFIG_PATH,
        PLAN_DIR,
        QUEUE_STATE_DIR,
        RUNTIME_ROOT,
        TASKS_DIR,
        TASKS_PATH,
        pid_file,
    )
except ImportError:
    import sys
    from openclaw_roots import (
        LOG_DIR,
        PLAN_CONFIG_PATH,
        PLAN_DIR,
        QUEUE_STATE_DIR,
        RUNTIME_ROOT,
        TASKS_DIR,
        TASKS_PATH,
        pid_file,
    )

from .utils import read_json


POLL_SECONDS = int(os.getenv("ATHENA_AI_PLAN_POLL_SECONDS", "15"))
BUILD_TIMEOUT_SECONDS = int(os.getenv("ATHENA_AI_PLAN_BUILD_TIMEOUT_SECONDS", "1800"))
REVIEW_TIMEOUT_SECONDS = int(os.getenv("ATHENA_CODEX_REVIEW_TIMEOUT_SECONDS", "1200"))
PLAN_TIMEOUT_SECONDS = int(os.getenv("ATHENA_CODEX_PLAN_TIMEOUT_SECONDS", "1500"))
STALL_OUTPUT_TIMEOUT_SECONDS = int(os.getenv("ATHENA_AI_PLAN_STALL_OUTPUT_TIMEOUT_SECONDS", "420"))
MIN_FREE_MEMORY_PERCENT = int(os.getenv("ATHENA_AI_PLAN_MIN_FREE_MEMORY_PERCENT", "8"))
MAX_BUILD_WORKERS = max(1, int(os.getenv("ATHENA_AI_PLAN_MAX_BUILD_WORKERS", "2")))
SECOND_BUILD_MIN_FREE_MEMORY_PERCENT = int(
    os.getenv("ATHENA_AI_PLAN_SECOND_BUILD_MIN_FREE_MEMORY_PERCENT", "35")
)
MAX_BUILD_LOAD_PER_CORE = float(os.getenv("ATHENA_AI_PLAN_MAX_BUILD_LOAD_PER_CORE", "0.6"))
MAX_BUILD_LOAD_ABSOLUTE = float(os.getenv("ATHENA_AI_PLAN_MAX_BUILD_LOAD_ABSOLUTE", "6.0"))
OLLAMA_BUSY_CPU_PERCENT = float(os.getenv("ATHENA_AI_PLAN_OLLAMA_BUSY_CPU_PERCENT", "35"))
HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv("ATHENA_AI_PLAN_HEARTBEAT_TIMEOUT_SECONDS", "30"))
STALE_TASK_TIMEOUT_SECONDS = int(os.getenv("ATHENA_AI_PLAN_STALE_TASK_TIMEOUT_SECONDS", "60"))
AUTO_RETRY_LIMIT = max(0, int(os.getenv("ATHENA_AI_PLAN_AUTO_RETRY_LIMIT", "3")))
AUTO_RETRY_COOLDOWN_SECONDS = int(os.getenv("ATHENA_AI_PLAN_AUTO_RETRY_COOLDOWN_SECONDS", "90"))
BLOCKED_RESCUE_RETRY_LIMIT = max(
    0, int(os.getenv("ATHENA_AI_PLAN_BLOCKED_RESCUE_RETRY_LIMIT", "2"))
)
BLOCKED_RESCUE_RETRY_COOLDOWN_SECONDS = int(
    os.getenv("ATHENA_AI_PLAN_BLOCKED_RESCUE_RETRY_COOLDOWN_SECONDS", "300")
)
AUTO_ARCHIVE_COMPLETED = os.getenv("ATHENA_AI_PLAN_AUTO_ARCHIVE_COMPLETED", "1") != "0"

RETRYABLE_FAILURE_MARKERS = (
    "Connection reset by peer",
    "Connection timed out",
    "Temporary failure in name resolution",
    "Name or service not known",
    "No route to host",
    "Connection refused",
    "403",
    "429",
    "500",
    "502",
    "503",
    "504",
    "rate_limit_exceeded",
    "quota_exceeded",
    "insufficient_quota",
    "billing_hard_limit_reached",
    "api_key_invalid",
    "invalid_api_key",
)

BLOCKED_RESCUE_FAILURE_MARKERS = (
    "blocked",
    "blocked_rescue",
    "Queue capacity reached",
    "too many pending items",
    "resource gate: memory",
    "resource gate: cpu",
    "resource: memory",
    "resource: cpu",
)


def load_plan_config() -> dict[str, Any]:
    return read_json(PLAN_CONFIG_PATH, default={"routes": []}) or {"routes": []}


def load_control_plane_config() -> dict[str, Any]:
    """加载控制面配置，返回摘要信息。"""
    config_path = RUNTIME_ROOT / "mini-agent" / "config" / "control_plane.yaml"
    if not config_path.exists():
        return {
            "available": False,
            "reason": f"控制面配置文件不存在: {config_path}",
            "scopes": ["managed", "project", "local", "session"],
        }

    try:
        import yaml

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        version = config.get("version", "unknown")

        # 检查本地优先策略
        local_first = config.get("local_first_policy", {})
        never_leaves = (
            local_first.get("never_leaves_local", []) if isinstance(local_first, dict) else []
        )
        allowed_remote = (
            local_first.get("allowed_remote_access", []) if isinstance(local_first, dict) else []
        )

        return {
            "available": True,
            "version": version,
            "config_path": str(config_path),
            "scopes": ["managed", "project", "local", "session"],
            "scope_summary": {
                "managed": bool(config.get("managed")),
                "project": bool(config.get("project")),
                "local": bool(config.get("local")),
                "session": bool(config.get("session")),
            },
            "local_first_policy": {
                "never_leaves_local_count": len(never_leaves),
                "allowed_remote_access_count": len(allowed_remote),
            },
            "configuration_priority": config.get("configuration_priority", {}).get(
                "priority_order", []
            ),
        }
    except Exception as e:
        return {
            "available": False,
            "reason": f"加载控制面配置失败: {e}",
            "scopes": ["managed", "project", "local", "session"],
        }


def archive_dir_from_config() -> Path | None:
    config = load_plan_config()
    raw_path = str(config.get("archive_dir", "") or "").strip()
    if not raw_path:
        return None
    return Path(raw_path)


def is_pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def terminate_pid_tree(pid: int | None, grace_seconds: int = 8) -> None:
    if not pid or pid <= 0:
        return
    try:
        import signal

        os.killpg(os.getpgid(pid), signal.SIGTERM)
        time.sleep(0.5)
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    except (ProcessLookupError, PermissionError, OSError):
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        except (ProcessLookupError, PermissionError, OSError):
            pass
