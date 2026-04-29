#!/usr/bin/env python3
"""route_state"""

from __future__ import annotations

import fcntl
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
        QUEUE_STATE_DIR,
    )
except ImportError:
    import sys

    from openclaw_roots import (
        QUEUE_STATE_DIR,
    )

from .utils import now_iso, read_json, write_json


def route_runner_mode(route: dict[str, Any]) -> str:
    return str(route.get("runner_mode", "opencode_build") or "opencode_build")


def route_matches_runner_modes(
    route: dict[str, Any], accepted_runner_modes: set[str] | tuple[str, ...] | None
) -> bool:
    allowed = set(accepted_runner_modes or {"opencode_build"})
    return route_runner_mode(route) in allowed


def route_state_path(route: dict[str, Any]) -> Path:
    explicit_path = str(route.get("queue_state_path", "") or "")
    if explicit_path:
        return Path(explicit_path)
    queue_id = str(route.get("queue_id", "athena_queue") or "athena_queue")
    return QUEUE_STATE_DIR / f"{queue_id}.json"


def route_state_lock_path(route: dict[str, Any]) -> Path:
    path = route_state_path(route)
    return path.with_name(path.name + ".lock")


def _normalize_route_state(route: dict[str, Any], payload: dict[str, Any] | None) -> dict[str, Any]:
    from .manifest import compute_route_counts_and_status

    state = payload if isinstance(payload, dict) else {}
    items = state.get("items")
    if not isinstance(items, dict):
        items = {}

    current_ids: list[str] = []
    raw_ids = state.get("current_item_ids")
    if isinstance(raw_ids, list):
        for raw_id in raw_ids:
            item_id = str(raw_id or "").strip()
            if item_id and item_id not in current_ids:
                current_ids.append(item_id)

    current_item_id = str(state.get("current_item_id", "") or "").strip()
    if current_item_id and current_item_id not in current_ids:
        current_ids.append(current_item_id)

    running_ids = [
        str(item_id)
        for item_id, state_item in items.items()
        if isinstance(state_item, dict) and str(state_item.get("status", "")) == "running"
    ]
    for item_id in running_ids:
        if item_id not in current_ids:
            current_ids.append(item_id)

    # Keep placeholder ids that were just added before their state item is
    # written, but automatically drop finished/failed residues so the
    # scheduler never treats stale top-level current ids as live work.
    current_ids = [
        item_id
        for item_id in current_ids
        if item_id not in items or str((items.get(item_id) or {}).get("status", "")) == "running"
    ]

    normalized = {
        "queue_id": str(state.get("queue_id", "") or route.get("queue_id", "") or ""),
        "name": str(state.get("name", "") or route.get("name", "") or ""),
        "current_item_id": current_ids[0] if current_ids else "",
        "current_item_ids": current_ids,
        "updated_at": str(state.get("updated_at", "") or now_iso()),
        "items": items,
    }
    counts, queue_status = compute_route_counts_and_status(route, normalized)
    normalized["counts"] = counts
    normalized["queue_status"] = queue_status
    # Determine pause reason based on queue status and other factors
    pause_reason = ""
    if queue_status in {
        "dependency_blocked",
        "manual_hold",
        "failed",
        "no_consumer",
        "human_gate",
        "empty",
    }:
        pause_reason = queue_status
    elif queue_status == "running":
        # Check if there are pending items but no consumer? Actually running means active consumer.
        # No pause reason when running.
        pass
    # Additional human_gate detection could be added here based on item metadata
    normalized["pause_reason"] = pause_reason
    return normalized


def load_route_state(route: dict[str, Any]) -> dict[str, Any]:
    payload = read_json(route_state_path(route), default=None)
    return _normalize_route_state(route, payload)


def write_route_state(route: dict[str, Any], route_state: dict[str, Any]) -> None:
    write_json(route_state_path(route), _normalize_route_state(route, route_state))


def route_current_item_ids(route_state: dict[str, Any]) -> list[str]:
    current_ids = route_state.get("current_item_ids")
    if isinstance(current_ids, list) and current_ids:
        return [str(item_id) for item_id in current_ids if str(item_id or "").strip()]
    current_item_id = str(route_state.get("current_item_id", "") or "").strip()
    return [current_item_id] if current_item_id else []


def mutate_route_state(
    route: dict[str, Any], mutator: Any, *, fallback: dict[str, Any] | None = None
) -> dict[str, Any]:
    path = route_state_path(route)
    lock_path = route_state_lock_path(route)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        payload = read_json(path, default=fallback)
        route_state = _normalize_route_state(route, payload)
        updated = mutator(route_state)
        route_state = _normalize_route_state(
            route, updated if isinstance(updated, dict) else route_state
        )
        write_json(path, route_state)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        return route_state


def add_route_current_item(route: dict[str, Any], item_id: str) -> dict[str, Any]:
    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        current_ids = route_current_item_ids(state)
        if item_id not in current_ids:
            current_ids.append(item_id)
        state["current_item_ids"] = current_ids
        state["current_item_id"] = current_ids[0] if current_ids else ""
        state["updated_at"] = now_iso()
        return state

    return mutate_route_state(route, _mutate)


def remove_route_current_item(route: dict[str, Any], item_id: str) -> dict[str, Any]:
    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        current_ids = [current for current in route_current_item_ids(state) if current != item_id]
        state["current_item_ids"] = current_ids
        state["current_item_id"] = current_ids[0] if current_ids else ""
        state["updated_at"] = now_iso()
        return state

    return mutate_route_state(route, _mutate)


def replace_route_current_items(route: dict[str, Any], item_ids: list[str]) -> dict[str, Any]:
    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        state["current_item_ids"] = item_ids
        state["current_item_id"] = item_ids[0] if item_ids else ""
        state["updated_at"] = now_iso()
        return state

    return mutate_route_state(route, _mutate)


def clear_route_current_items(route: dict[str, Any]) -> dict[str, Any]:
    return replace_route_current_items(route, [])
