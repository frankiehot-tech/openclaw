#!/usr/bin/env python3
"""trace"""

from __future__ import annotations

import logging
import sys
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

from .utils import now_iso, read_json, write_json


def create_task_workspace(task_dir: Path) -> dict[str, Path]:
    """
    为任务创建结构化工作目录并返回路径映射。

    Returns:
        dict with keys: workspace, inputs, outputs, evidence, checkpoints, trace
    """
    subdirs = {
        "workspace": task_dir / "workspace",
        "inputs": task_dir / "inputs",
        "outputs": task_dir / "outputs",
        "evidence": task_dir / "evidence",
        "checkpoints": task_dir / "checkpoints",
    }
    for subpath in subdirs.values():
        subpath.mkdir(parents=True, exist_ok=True)

    trace_path = task_dir / "trace.json"
    if not trace_path.exists():
        write_json(
            trace_path,
            {
                "task_id": task_dir.name,
                "created_at": now_iso(),
                "version": "1.0",
                "events": [],
                "artifacts": [],
                "status_changes": [],
                "directories": {
                    key: str(path.relative_to(task_dir)) for key, path in subdirs.items()
                },
            },
        )

    return {**subdirs, "trace": trace_path}


def update_trace_event(task_dir: Path, event_type: str, data: dict[str, Any]) -> None:
    """在 trace.json 中追加一个事件记录"""
    trace_path = task_dir / "trace.json"
    if not trace_path.exists():
        return
    try:
        trace = read_json(trace_path, default={"events": []})
        if not isinstance(trace, dict):
            trace = {"events": []}
        events = trace.setdefault("events", [])
        events.append({"timestamp": now_iso(), "type": event_type, "data": data})
        write_json(trace_path, trace)
    except Exception:
        pass


def update_trace_status_change(
    task_dir: Path, old_status: str, new_status: str, reason: str = ""
) -> None:
    """记录状态变化到 trace.json"""
    update_trace_event(
        task_dir,
        "status_change",
        {"old_status": old_status, "new_status": new_status, "reason": reason},
    )
    # 同时更新 trace 中的 status_changes 列表
    trace_path = task_dir / "trace.json"
    if not trace_path.exists():
        return
    try:
        trace = read_json(trace_path, default={"status_changes": []})
        if not isinstance(trace, dict):
            trace = {"status_changes": []}
        changes = trace.setdefault("status_changes", [])
        changes.append(
            {
                "timestamp": now_iso(),
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
            }
        )
        write_json(trace_path, trace)
    except Exception:
        pass


def add_trace_artifact(
    task_dir: Path,
    artifact_type: str,
    path: str,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """向 trace.json 添加产物记录"""
    update_trace_event(
        task_dir,
        "artifact_added",
        {"artifact_type": artifact_type, "path": path, "metadata": metadata or {}},
    )
    trace_path = task_dir / "trace.json"
    if not trace_path.exists():
        return
    try:
        trace = read_json(trace_path, default={"artifacts": []})
        if not isinstance(trace, dict):
            trace = {"artifacts": []}
        artifacts = trace.setdefault("artifacts", [])
        artifacts.append(
            {
                "timestamp": now_iso(),
                "artifact_type": artifact_type,
                "path": path,
                "metadata": metadata or {},
            }
        )
        write_json(trace_path, trace)
    except Exception:
        pass
