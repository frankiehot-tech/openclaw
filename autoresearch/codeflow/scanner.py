"""CodeFlow scanner — watches approved directories for new tasks.

Scans configured directories for approved AI plans and determines if they
should trigger automated execution via the ratchet loop pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ScanTarget:
    path: str
    approved: bool
    auto_execute: bool
    priority: str = "normal"
    description: str = ""


@dataclass
class ScanResult:
    target: ScanTarget
    new_items: int
    total_items: int
    requires_manual: bool
    details: dict[str, Any] = field(default_factory=dict)


DEFAULT_TARGETS: list[dict[str, Any]] = [
    {
        "path": "Athena知识库/执行项目/2026/003-open human（碳硅基共生）/019-工作台/收件箱/已批准/",
        "approved": True,
        "auto_execute": False,
        "description": "OpenHuman v0.2.0 approved consumption inbox",
        "priority": "high",
    },
    {
        "path": "Athena知识库/执行项目/2026/003-open human（碳硅基共生）/019-工作台/收件箱/完成/v0.2.0 归档/",
        "approved": True,
        "auto_execute": False,
        "description": "OpenHuman v0.2.0 completed archive",
        "priority": "high",
    },
    {
        "path": "Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/",
        "approved": True,
        "auto_execute": False,
        "description": "OpenHuman approved AI plans",
    },
    {
        "path": ".openclaw/plans/approved/",
        "approved": True,
        "auto_execute": True,
        "description": "openclaw approved execution plans",
    },
]


class DirectoryScanner:
    """Scans approved directories for new or pending tasks."""

    def __init__(self, root_path: str | Path | None = None, targets: list[dict[str, Any]] | None = None) -> None:
        self.root = Path(root_path or "/Volumes/1TB-M2")
        self._targets: list[ScanTarget] = []
        for t in (targets or DEFAULT_TARGETS):
            self._targets.append(ScanTarget(
                path=t["path"],
                approved=t.get("approved", True),
                auto_execute=t.get("auto_execute", False),
                priority=t.get("priority", "normal"),
                description=t.get("description", ""),
            ))
        self._state_file = Path.cwd() / ".openclaw" / "scanner_state.json"

    def scan(self) -> list[ScanResult]:
        results: list[ScanResult] = []
        for target in self._targets:
            full_path = self.root / target.path
            if not full_path.exists():
                continue
            items = list(full_path.glob("*.md"))
            item_count = len(items)
            known_count = self._load_known_count(target.path)
            new_items = max(0, item_count - known_count)
            requires_manual = not target.auto_execute and target.approved
            results.append(ScanResult(
                target=target,
                new_items=new_items,
                total_items=item_count,
                requires_manual=requires_manual,
                details={
                    "path": str(full_path),
                    "items": [str(p.name) for p in items[-5:]],
                    "previously_known": known_count,
                },
            ))
            self._save_known_count(target.path, item_count)
        return results

    def has_new_tasks(self) -> bool:
        return any(r.new_items > 0 for r in self.scan())

    def _load_known_count(self, path: str) -> int:
        state = self._read_state()
        return state.get(path, 0)

    def _save_known_count(self, path: str, count: int) -> None:
        state = self._read_state()
        state[path] = count
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _read_state(self) -> dict[str, int]:
        if self._state_file.exists():
            try:
                with open(self._state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}
