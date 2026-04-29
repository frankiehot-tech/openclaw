#!/usr/bin/env python3
"""health.py — CLI wrapper for SystemHealth that outputs JSON status."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance.system_health import SystemHealth


def main():
    health = SystemHealth()
    report = health.full_check()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    has_anomalies = len(report.get("queues", {}).get("anomalies", [])) > 0
    has_resource_issues = any(
        r and r.get("alert") for r in report.get("resources", {}).values() if isinstance(r, dict)
    )
    has_dead_runners = not all(report.get("runners", {}).values()) if report.get("runners") else False
    if has_anomalies or has_resource_issues or has_dead_runners:
        sys.exit(1)


if __name__ == "__main__":
    main()
