#!/usr/bin/env python3
"""
Workflow State Management

Provides simple JSON‑based state persistence for the Athena repair chain.
Used by the orchestrator and bridge scripts to track incident‑to‑task mapping.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Default location under runtime root
RUNTIME_ROOT = Path(os.getenv("ATHENA_RUNTIME_ROOT", "/Volumes/1TB-M2/openclaw"))
STATE_DIR = RUNTIME_ROOT / ".openclaw" / "workflow_state"
STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_state(key: str, default: Any = None) -> Any:
    """Retrieve a persisted state value."""
    path = STATE_DIR / f"{key}.json"
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def set_state(key: str, value: Any) -> None:
    """Persist a state value."""
    path = STATE_DIR / f"{key}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise RuntimeError(f"Failed to write state {key}: {e}")


def delete_state(key: str) -> bool:
    """Delete a persisted state value."""
    path = STATE_DIR / f"{key}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def list_state_keys(prefix: str = "") -> list[str]:
    """List all state keys, optionally filtered by prefix."""
    keys = []
    for p in STATE_DIR.glob("*.json"):
        key = p.stem
        if prefix and not key.startswith(prefix):
            continue
        keys.append(key)
    return sorted(keys)


# ------------------------------------------------------------
# Incident‑to‑task mapping helpers
# ------------------------------------------------------------


def record_incident_task(incident_id: str, task_id: str) -> None:
    """Record that a given incident has spawned a repair task."""
    mapping = get_state("incident_task_map", {})
    mapping[incident_id] = task_id
    set_state("incident_task_map", mapping)


def get_task_for_incident(incident_id: str) -> Optional[str]:
    """Return the task ID that was created for an incident, if any."""
    mapping = get_state("incident_task_map", {})
    return mapping.get(incident_id)


def remove_incident_mapping(incident_id: str) -> None:
    """Remove the mapping for an incident (e.g., after resolution)."""
    mapping = get_state("incident_task_map", {})
    if incident_id in mapping:
        del mapping[incident_id]
        set_state("incident_task_map", mapping)


# ------------------------------------------------------------
# Incident state tracking
# ------------------------------------------------------------

INCIDENT_STATE_DETECTED = "detected"
INCIDENT_STATE_QUEUED = "queued"
INCIDENT_STATE_RUNNING = "running"
INCIDENT_STATE_COMPLETED = "completed"
INCIDENT_STATE_FAILED = "failed"

VALID_INCIDENT_STATES = {
    INCIDENT_STATE_DETECTED,
    INCIDENT_STATE_QUEUED,
    INCIDENT_STATE_RUNNING,
    INCIDENT_STATE_COMPLETED,
    INCIDENT_STATE_FAILED,
}


def record_incident_detected(
    incident: dict[str, Any], metadata: Optional[dict[str, Any]] = None
) -> None:
    """Persist the first-class 'detected' state for an incident."""
    incident_id = str(incident.get("id", "") or "").strip()
    if not incident_id:
        raise ValueError("incident 缺少 id，无法记录 detected 状态")
    merged_metadata = {
        "source": incident.get("source"),
        "category": incident.get("category"),
        "severity": incident.get("severity"),
        "summary": incident.get("summary"),
        "repairable": incident.get("repairable"),
        "repair_flow": incident.get("repair_flow"),
        "details": incident.get("details", {}),
    }
    if metadata:
        merged_metadata.update(metadata)
    set_incident_state(incident_id, INCIDENT_STATE_DETECTED, merged_metadata)


def set_incident_state(incident_id: str, state: str, metadata: Optional[dict] = None) -> None:
    """Set the state of an incident."""
    if state not in VALID_INCIDENT_STATES:
        raise ValueError(f"Invalid incident state: {state}")
    states = get_state("incident_states", {})
    states[incident_id] = {
        "state": state,
        "updated_at": datetime.now().isoformat(),
        "metadata": metadata or {},
    }
    set_state("incident_states", states)


def get_incident_state(incident_id: str) -> dict:
    """Get the state of an incident."""
    states = get_state("incident_states", {})
    return states.get(incident_id)


def get_incident_state_value(incident_id: str) -> Optional[str]:
    """Get the current state value of an incident."""
    state_info = get_incident_state(incident_id)
    return state_info.get("state") if state_info else None


def describe_incident_status(incident_id: str) -> dict[str, Any]:
    """Return a compact, user-facing snapshot for an incident."""
    state_info = get_incident_state(incident_id) or {}
    metadata = state_info.get("metadata") or {}
    task_id = (
        metadata.get("task_id")
        or metadata.get("existing_task_id")
        or get_task_for_incident(incident_id)
    )
    return {
        "incident_id": incident_id,
        "state": state_info.get("state"),
        "updated_at": state_info.get("updated_at"),
        "task_id": task_id,
        "summary": metadata.get("summary"),
        "category": metadata.get("category"),
        "severity": metadata.get("severity"),
        "last_error": metadata.get("task_error") or metadata.get("error"),
        "metadata": metadata,
    }


def update_incident_state_from_task(task_id: str, incident_id: str) -> bool:
    """Update incident state based on task status from tasks.json."""
    tasks_path = RUNTIME_ROOT / ".openclaw" / "orchestrator" / "tasks.json"
    if not tasks_path.exists():
        return False
    try:
        with open(tasks_path, "r", encoding="utf-8") as f:
            tasks_data = json.load(f)
        task = None
        for t in tasks_data.get("tasks", []):
            if t.get("id") == task_id:
                task = t
                break
        if not task:
            return False
        task_status = task.get("status", "").lower()
        metadata = {
            "task_id": task_id,
            "task_status": task_status,
            "task_summary": task.get("summary"),
            "task_error": task.get("error"),
        }
        if task_status == "running":
            set_incident_state(incident_id, INCIDENT_STATE_RUNNING, metadata)
        elif task_status == "completed":
            set_incident_state(incident_id, INCIDENT_STATE_COMPLETED, metadata)
        elif task_status == "failed":
            set_incident_state(incident_id, INCIDENT_STATE_FAILED, metadata)
        else:
            return False
        return True
    except Exception:
        return False


def cleanup_resolved_incidents(days: int = 7) -> int:
    """Remove incident states and mappings that are completed/failed older than N days."""
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(days=days)
    states = get_state("incident_states", {})
    mapping = get_state("incident_task_map", {})
    removed = 0
    for incident_id in list(states.keys()):
        state_info = states[incident_id]
        state = state_info.get("state")
        updated_str = state_info.get("updated_at")
        if state in (INCIDENT_STATE_COMPLETED, INCIDENT_STATE_FAILED) and updated_str:
            try:
                updated = datetime.fromisoformat(updated_str)
                if updated < cutoff:
                    del states[incident_id]
                    if incident_id in mapping:
                        del mapping[incident_id]
                    removed += 1
            except Exception:
                continue
    set_state("incident_states", states)
    set_state("incident_task_map", mapping)
    return removed


# ------------------------------------------------------------
# Heartbeat / staleness detection
# ------------------------------------------------------------


def update_heartbeat(component: str) -> None:
    """Update the heartbeat timestamp for a component."""
    heartbeats = get_state("heartbeats", {})
    heartbeats[component] = datetime.now().isoformat()
    set_state("heartbeats", heartbeats)


def get_heartbeat(component: str) -> Optional[str]:
    """Get the last heartbeat timestamp for a component."""
    heartbeats = get_state("heartbeats", {})
    return heartbeats.get(component)


# ------------------------------------------------------------
# Module self‑test
# ------------------------------------------------------------

if __name__ == "__main__":
    print("=== workflow_state self‑test ===")
    test_key = "test_workflow_state"
    test_value = {"test": 123, "timestamp": datetime.now().isoformat()}
    set_state(test_key, test_value)
    retrieved = get_state(test_key)
    print(f"set/get: {retrieved == test_value}")
    delete_state(test_key)
    print(f"delete: {not get_state(test_key)}")
    print("---")
    print(f"state directory: {STATE_DIR}")
    print("All basic operations passed.")
