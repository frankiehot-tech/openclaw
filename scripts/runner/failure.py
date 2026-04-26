#!/usr/bin/env python3
"""failure"""

from __future__ import annotations

import logging
import sys
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

from .utils import now_iso
from .manifest import active_route_item_ids, load_manifest_items, route_index_by_item_id
from .route_state import load_route_state
from .config import load_plan_config
from .task import (
    set_task_status,
    set_route_item_state,
    remove_route_current_item,
    reset_failed_item_for_auto_retry,
)
from .route_state import route_matches_runner_modes


def failure_text(state_item: dict[str, Any]) -> str:
    return " ".join(
        str(state_item.get(key, "") or "")
        for key in ("error", "summary", "pipeline_summary", "result_excerpt")
    ).lower()


def retry_window_open(
    state_item: dict[str, Any],
    *,
    count_key: str,
    limit: int,
    last_key: str,
    cooldown: int,
) -> bool:
    retry_count = int(state_item.get(count_key, 0) or 0)
    if retry_count >= limit:
        return False
    last_retry_at = str(state_item.get(last_key, "") or "").strip()
    if last_retry_at:
        try:
            retry_time = datetime.fromisoformat(last_retry_at.replace("Z", "+00:00"))
            if retry_time.tzinfo is None:
                retry_time = retry_time.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - retry_time).total_seconds() < cooldown:
                return False
        except Exception:
            pass
    return True


def is_retryable_failed_item(state_item: dict[str, Any]) -> bool:
    if str(state_item.get("status", "") or "") != "failed":
        return False
    if not retry_window_open(
        state_item,
        count_key="auto_retry_count",
        limit=AUTO_RETRY_LIMIT,
        last_key="last_auto_retry_at",
        cooldown=AUTO_RETRY_COOLDOWN_SECONDS,
    ):
        return False
    text = failure_text(state_item)
    return any(marker in text for marker in RETRYABLE_FAILURE_MARKERS)


def is_blocked_rescue_retryable_failed_item(state_item: dict[str, Any]) -> bool:
    if str(state_item.get("status", "") or "") != "failed":
        return False
    if not retry_window_open(
        state_item,
        count_key="blocked_rescue_retry_count",
        limit=BLOCKED_RESCUE_RETRY_LIMIT,
        last_key="last_blocked_rescue_retry_at",
        cooldown=BLOCKED_RESCUE_RETRY_COOLDOWN_SECONDS,
    ):
        return False
    text = failure_text(state_item)
    return any(marker in text for marker in BLOCKED_RESCUE_FAILURE_MARKERS)


def failure_markdown(
    title: str,
    task_id: str,
    instruction_path: str,
    error: str,
    warnings: list[str],
    output_tail: str = "",
) -> str:
    warning_text = "\n".join(f"- {warning}" for warning in warnings) if warnings else "- 无"
    parts = [
        f"# {title}",
        "",
        "## 状态",
        "- failed",
        f"- root_task_id: {task_id}",
        f"- instruction_path: {instruction_path}",
        "",
        "## 失败原因",
        error,
        "",
        "## 预检提醒",
        warning_text,
    ]
    if output_tail:
        parts.extend(["", "## 最后输出", output_tail])
    return "\n".join(parts) + "\n"


def success_markdown(
    title: str,
    task_id: str,
    instruction_path: str,
    warnings: list[str],
    output_text: str,
    *,
    output_heading: str = "OpenCode 输出",
) -> str:
    warning_text = "\n".join(f"- {warning}" for warning in warnings) if warnings else "- 无"
    return "\n".join(
        [
            f"# {title}",
            "",
            "## 状态",
            "- completed",
            f"- root_task_id: {task_id}",
            f"- instruction_path: {instruction_path}",
            "",
            "## 预检提醒",
            warning_text,
            "",
            f"## {output_heading}",
            output_text.strip() or "(空输出)",
            "",
        ]
    )


def mark_stale_failed(
    route: dict[str, Any],
    route_state: dict[str, Any],
    item_id: str,
    state_item: dict[str, Any],
    reason: str,
) -> None:
    """Mark a stale running item as failed with appropriate metadata."""
    runner_pid_raw = state_item.get("runner_pid")
    try:
        runner_pid = int(runner_pid_raw) if runner_pid_raw not in ("", None) else None
    except (TypeError, ValueError):
        runner_pid = None
    terminate_pid_tree(runner_pid, grace_seconds=4)

    summary = f"stale queue task: {reason}"
    state_item.update(
        {
            "status": "failed",
            "summary": summary,
            "error": summary,
            "finished_at": now_iso(),
            "progress_percent": 100,
            "runner_heartbeat_at": now_iso(),  # record final heartbeat
        }
    )
    route_state.setdefault("items", {})[item_id] = state_item
    set_route_item_state(route, route_state, item_id, **state_item)
    remove_route_current_item(route, item_id)

    root_task_id = str(state_item.get("root_task_id", "") or "")
    if root_task_id:
        set_task_status(
            root_task_id,
            title=str(state_item.get("title", item_id) or item_id),
            queue_item_id=item_id,
            stage=str(state_item.get("stage", "build") or "build"),
            status="failed",
            progress_percent=100,
            instruction_path=str(state_item.get("instruction_path", "") or ""),
            artifact_path=(state_item.get("artifact_paths") or [""])[0],
            summary=summary,
            error=summary,
            started_at=str(state_item.get("started_at", "") or ""),
            finished_at=str(state_item.get("finished_at", "") or now_iso()),
        )


def auto_retry_blocking_failures(
    target_routes: list[dict[str, Any]],
    *,
    accepted_runner_modes: set[str] | tuple[str, ...] | None = None,
) -> list[str]:
    if AUTO_RETRY_LIMIT <= 0:
        return []
    all_routes = list(load_plan_config().get("routes", []))
    state_index = route_index_by_item_id(all_routes)
    retried: list[str] = []
    retried_ids: set[str] = set()
    for route in target_routes:
        if not route_matches_runner_modes(route, accepted_runner_modes):
            continue
        route_state = load_route_state(route)
        route_queue_status = str(route_state.get("queue_status", "") or "")
        route_has_active_items = bool(active_route_item_ids(route_state))
        items_state = route_state.get("items") or {}
        for item in load_manifest_items(route):
            item_id = str(item.get("id", "") or "")
            state_status = str((items_state.get(item_id) or {}).get("status", "") or "pending")
            if state_status not in {"", "pending"}:
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            manual_override_autostart = bool(
                (items_state.get(item_id) or {}).get("manual_override_autostart")
            )
            if metadata.get("autostart") is False and not manual_override_autostart:
                continue
            depends_on = (
                metadata.get("depends_on") if isinstance(metadata.get("depends_on"), list) else []
            )
            for dep_id in depends_on:
                dep_key = str(dep_id)
                if dep_key in retried_ids:
                    continue
                dep_entry = state_index.get(dep_key)
                if not dep_entry:
                    continue
                dep_route, dep_state = dep_entry
                if is_retryable_failed_item(dep_state):
                    reset_failed_item_for_auto_retry(
                        dep_route,
                        dep_key,
                        dep_state,
                        f"解锁后继任务 {item_id}" if item_id else "依赖阻塞自动解锁",
                    )
                    retried.append(dep_key)
                    retried_ids.add(dep_key)
                    continue
                if (
                    route_queue_status == "dependency_blocked"
                    and not route_has_active_items
                    and is_blocked_rescue_retryable_failed_item(dep_state)
                ):
                    reset_failed_item_for_auto_retry(
                        dep_route,
                        dep_key,
                        dep_state,
                        f"阻塞自救解锁后继任务 {item_id}" if item_id else "依赖阻塞自救解锁",
                        rescue=True,
                    )
                    retried.append(dep_key)
                    retried_ids.add(dep_key)
    return retried
