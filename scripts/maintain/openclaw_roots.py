#!/usr/bin/env python3
"""OpenClaw root path helper.

This module provides the single source of truth for all runtime root, plan config,
queue state, and task artifact paths.

Usage:
    from scripts.openclaw_roots import RUNTIME_ROOT, PLAN_CONFIG_PATH, QUEUE_STATE_DIR, TASKS_DIR
"""

from __future__ import annotations

import os
from pathlib import Path

# --- Primary root ---
RUNTIME_ROOT = Path(os.getenv("ATHENA_RUNTIME_ROOT", "/Volumes/1TB-M2/openclaw")).resolve()

# --- AI plan configuration ---
PLAN_CONFIG_PATH = Path(
    os.getenv(
        "ATHENA_AI_PLAN_CONFIG",
        "/Volumes/1TB-M2/openclaw/.athena-auto-queue.json",
    )
)
PLAN_DIR = PLAN_CONFIG_PATH.parent

# --- Queue state directory ---
QUEUE_STATE_DIR = RUNTIME_ROOT / ".openclaw" / "plan_queue"

# --- Task artifacts ---
TASKS_DIR = RUNTIME_ROOT / ".openclaw" / "orchestrator" / "tasks"
TASKS_PATH = RUNTIME_ROOT / ".openclaw" / "orchestrator" / "tasks.json"

# --- Logs ---
LOG_DIR = RUNTIME_ROOT / "logs"

# --- Health events ---
HEALTH_EVENTS_DIR = RUNTIME_ROOT / ".openclaw" / "health" / "events"


# --- PID files (common patterns) ---
def pid_file(name: str) -> Path:
    """Return PID file path for a given service name."""
    return RUNTIME_ROOT / ".openclaw" / f"{name}.pid"


# --- Web desktop compatibility ---
TOKEN_FILE = RUNTIME_ROOT / ".openclaw" / "athena_web_desktop.token"
AGENT_STATE_PATH = RUNTIME_ROOT / ".openclaw" / "agent_state.json"
WEB_PORT_FILE = RUNTIME_ROOT / "mini-agent" / ".web-port"

# --- Static assets ---
STATIC_JS = RUNTIME_ROOT / "workspace" / "chat_window.js"
STATIC_CSS = RUNTIME_ROOT / "workspace" / "chat_window.css"


def validate_paths() -> list[str]:
    """Return warnings for missing critical paths."""
    warnings = []
    if not RUNTIME_ROOT.exists():
        warnings.append(f"RUNTIME_ROOT does not exist: {RUNTIME_ROOT}")
    if not PLAN_CONFIG_PATH.exists():
        warnings.append(f"PLAN_CONFIG_PATH does not exist: {PLAN_CONFIG_PATH}")
    if not PLAN_DIR.exists():
        warnings.append(f"PLAN_DIR does not exist: {PLAN_DIR}")
    return warnings


if __name__ == "__main__":
    print("OpenClaw root helper")
    print(f"RUNTIME_ROOT: {RUNTIME_ROOT}")
    print(f"PLAN_CONFIG_PATH: {PLAN_CONFIG_PATH}")
    print(f"PLAN_DIR: {PLAN_DIR}")
    print(f"QUEUE_STATE_DIR: {QUEUE_STATE_DIR}")
    print(f"TASKS_DIR: {TASKS_DIR}")
    print(f"TASKS_PATH: {TASKS_PATH}")
    print(f"LOG_DIR: {LOG_DIR}")
    warnings = validate_paths()
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("\nAll critical paths exist.")
