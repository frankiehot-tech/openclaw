#!/usr/bin/env python3
"""
Run one safe auto-repair cycle from latest.json.

This is a stable entrypoint for heartbeat/automation/cron use:
- no incident
- non-repairable incident
- existing mapping
- newly created task
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.athena_auto_repair_router import IncidentRouter  # noqa: E402
from scripts.workflow_state import (  # noqa: E402
    describe_incident_status,
    get_task_for_incident,
    update_incident_state_from_task,
)


def load_incident(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one latest.json auto-repair cycle")
    parser.add_argument(
        "--latest",
        type=Path,
        default=PROJECT_ROOT / ".openclaw" / "health" / "events" / "latest.json",
        help="Path to latest incident snapshot",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON summary",
    )
    args = parser.parse_args()

    latest_path = args.latest
    summary: dict[str, object] = {
        "latest_path": str(latest_path),
        "outcome": "",
    }

    if not latest_path.exists():
        summary["outcome"] = "no_event_file"
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(f"ℹ️ 未找到 latest 事件文件: {latest_path}")
        return 0

    try:
        incident = load_incident(latest_path)
    except Exception as exc:
        summary["outcome"] = "invalid_event_file"
        summary["error"] = str(exc)
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(f"❌ latest 事件文件无法解析: {exc}")
        return 1

    incident_id = str(incident.get("id", "") or "").strip()
    summary["incident_id"] = incident_id
    summary["category"] = incident.get("category")
    summary["repairable"] = bool(incident.get("repairable", False))

    router = IncidentRouter()
    valid, reason = router.validate_incident(incident)
    if not valid:
        summary["outcome"] = "skipped"
        summary["reason"] = reason
        summary["incident_status"] = describe_incident_status(incident_id)
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(f"⏭️ 跳过 incident {incident_id}: {reason}")
        return 0

    existing_task_id = get_task_for_incident(incident_id)
    if existing_task_id:
        updated = update_incident_state_from_task(existing_task_id, incident_id)
        summary["outcome"] = "existing_mapping"
        summary["task_id"] = existing_task_id
        summary["state_synced"] = bool(updated)
        summary["incident_status"] = describe_incident_status(incident_id)
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(f"♻️ 已存在映射: {incident_id} -> {existing_task_id}")
        return 0

    success, message, result = router.route_incident(latest_path)
    summary["outcome"] = "created_task" if success else "route_failed"
    summary["message"] = message
    if result:
        summary["result"] = result
    summary["incident_status"] = describe_incident_status(incident_id)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        if success:
            task_id = (result or {}).get("task_id")
            print(f"✅ 已创建修复任务: {task_id}")
        else:
            print(f"⚠️ 路由失败: {message}")
    return 0 if success or "已有对应任务" in str(message) else 1


if __name__ == "__main__":
    raise SystemExit(main())
