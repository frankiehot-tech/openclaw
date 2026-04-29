#!/usr/bin/env python3
"""Queue Manager - unified queue state reading, writing, and status fixing.

Merges: direct_queue_fix, manual_queue_fix, quick_fix_queue_stall,
        fix_queue_counts, fix_queue_dependency, fix_queue_stage_sync,
        fix_queue_stopping_and_manual_launch, fix_queue_manually,
        fix_queue_item_location, fix_all_queues_stopped, fix_queue_state_reset,
        fix_all_manual_hold, fix_gene_management_queue_manual_hold,
        fix_queue_continuous_execution, fix_counts.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class QueueManager:
    """Centralized queue state management for .openclaw/plan_queue/*.json files."""

    def __init__(self, root_dir: str | Path | None = None):
        if root_dir is None:
            root_dir = Path(__file__).resolve().parent.parent
        self.root = Path(root_dir)
        self.plan_queue_dir = self.root / ".openclaw" / "plan_queue"

    @property
    def queue_dir_path(self) -> Path:
        return self.plan_queue_dir

    # ------------------------------------------------------------------
    # I/O helpers
    # ------------------------------------------------------------------

    def load_queue(self, queue_id_or_path: str, suffix: str = ".json") -> dict[str, Any] | None:
        """Load a queue JSON file by queue_id or full path, returning parsed data or None."""
        path = self._resolve_path(queue_id_or_path, suffix)
        if not path or not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def save_queue(self, queue_id_or_path: str, data: dict[str, Any], suffix: str = ".json") -> Path:
        """Save queue data, backing up the original first."""
        path = self._resolve_path(queue_id_or_path, suffix)
        if not path:
            raise FileNotFoundError(f"Cannot resolve queue path for {queue_id_or_path}")
        self._backup(path)
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(str(tmp), str(path))
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
        return path

    def _resolve_path(self, ref: str, suffix: str = ".json") -> Path | None:
        p = Path(ref)
        if p.is_absolute():
            return p if p.exists() else None
        candidate = self.plan_queue_dir / ref
        if not candidate.suffix:
            candidate = candidate.with_suffix(suffix)
        return candidate

    def _backup(self, path: Path) -> Path | None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = path.with_suffix(f".gov_backup_{stamp}")
        if path.exists():
            shutil.copy2(str(path), str(backup))
        return backup

    def list_queues(self) -> list[Path]:
        """Return list of .json queue files (excluding backups/locks)."""
        results: list[Path] = []
        if not self.plan_queue_dir.exists():
            return results
        for f in sorted(self.plan_queue_dir.iterdir()):
            if f.suffix != ".json" or f.name.endswith(".lock"):
                continue
            if any(kw in f.name.lower() for kw in ("backup", "before_", "tmp")):
                continue
            results.append(f)
        return results

    # ------------------------------------------------------------------
    # Counts & status calculation
    # ------------------------------------------------------------------

    @staticmethod
    def compute_counts(items: dict[str, dict[str, Any]]) -> dict[str, int]:
        """Recalculate status counts from items dict."""
        counts: dict[str, int] = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
        for task in items.values():
            st = task.get("status", "pending")
            if st in counts:
                counts[st] += 1
            else:
                counts["pending"] += 1
        return counts

    @staticmethod
    def derive_queue_status(
        counts: dict[str, int],
        items: dict[str, dict[str, Any]] | None = None,
        has_dependency_block: bool = False,
    ) -> tuple[str, str]:
        """Derive queue_status and pause_reason from counts.

        Returns (queue_status, pause_reason).
        """
        if counts.get("running", 0) > 0:
            return "running", ""
        if has_dependency_block:
            return "dependency_blocked", "dependency_block"
        if counts.get("pending", 0) > 0 and counts.get("manual_hold", 0) == 0:
            return "running", ""
        if counts.get("pending", 0) > 0 and counts.get("manual_hold", 0) > 0:
            return "manual_hold", "manual_hold"
        if counts.get("manual_hold", 0) > 0:
            return "manual_hold", "manual_hold"
        if counts.get("pending", 0) == 0 and counts.get("running", 0) == 0:
            completed = counts.get("completed", 0)
            total = sum(counts.values())
            if completed == total and total > 0:
                return "completed", ""
            return "empty", ""
        return "unknown", ""

    # ------------------------------------------------------------------
    # Status fixing
    # ------------------------------------------------------------------

    def fix_queue_status(self, queue_id_or_path: str, dry_run: bool = False) -> dict[str, Any]:
        """Auto-fix a queue stuck in manual_hold/stopped/dependency_blocked.

        - Recalculates counts
        - Finds executable pending tasks
        - Updates queue_status and current_item_id
        """
        data = self.load_queue(queue_id_or_path)
        if data is None:
            return {"success": False, "error": "Queue file not found"}

        items: dict[str, dict[str, Any]] = data.setdefault("items", {})
        counts = self.compute_counts(items)
        data["counts"] = counts

        # Detect dependency blocks
        dep_blocked = self._has_dependency_blocks(items)
        new_status, pause_reason = self.derive_queue_status(counts, items, dep_blocked)

        # Find pending tasks
        pending_ids = [tid for tid, t in items.items() if t.get("status") == "pending"]
        if pending_ids and new_status in ("running", "ready"):
            data["current_item_id"] = pending_ids[0]
            data["current_item_ids"] = pending_ids
        elif not pending_ids:
            data["current_item_id"] = ""
            data["current_item_ids"] = []

        data["queue_status"] = new_status
        data["pause_reason"] = pause_reason
        data["updated_at"] = datetime.now(UTC).isoformat()

        if not dry_run:
            self.save_queue(queue_id_or_path, data)

        return {
            "success": True,
            "queue_id": data.get("queue_id"),
            "new_status": new_status,
            "counts": counts,
            "pending_ids": pending_ids,
            "dependency_blocked": dep_blocked,
        }

    def fix_all_queues(self, dry_run: bool = False) -> list[dict[str, Any]]:
        """Fix all known queue files."""
        results: list[dict[str, Any]] = []
        for qf in self.list_queues():
            results.append(self.fix_queue_status(str(qf), dry_run=dry_run))
        return results

    @staticmethod
    def _has_dependency_blocks(items: dict[str, dict[str, Any]]) -> bool:
        dep_pattern = re.compile(r"被依赖项阻塞：([^(]+)\(pending\)")
        for task in items.values():
            summary = task.get("summary", "")
            if dep_pattern.search(summary):
                return True
        return False

    # ------------------------------------------------------------------
    # Cross-queue dependency resolution
    # ------------------------------------------------------------------

    def find_completed_deps_across_queues(self, exclude_ids: list[str] | None = None) -> dict[str, dict[str, Any]]:
        """Find tasks completed in *other* queues that might block the target."""
        exclude = set(exclude_ids or [])
        completed: dict[str, dict[str, Any]] = {}
        for qf in self.list_queues():
            qid = qf.stem
            if qid in exclude:
                continue
            data = self.load_queue(str(qf))
            if not data:
                continue
            items = self._normalize_items(data.get("items", {}))
            for tid, t in items.items():
                if t.get("status") == "completed":
                    completed[tid] = {"queue": qid, "data": t}
        return completed

    def resolve_cross_queue_deps(self, queue_id_or_path: str, dry_run: bool = False) -> dict[str, Any]:
        """Remove dependency-block references where the target has completed elsewhere."""
        data = self.load_queue(queue_id_or_path)
        if data is None:
            return {"success": False, "error": "Queue file not found"}

        items = self._normalize_items(data.setdefault("items", {}))
        qid = data.get("queue_id", "")
        completed_deps = self.find_completed_deps_across_queues(exclude_ids=[qid])
        dep_pattern = re.compile(r"被依赖项阻塞：([^(]+)\(pending\)")

        fixed = 0
        for _tid, task in items.items():
            if task.get("status") != "pending":
                continue
            summary = task.get("summary", "")
            matches = dep_pattern.findall(summary)
            new_summary = summary
            for dep in matches:
                dep = dep.strip()
                if dep in completed_deps:
                    new_summary = re.sub(
                        rf"被依赖项阻塞：{re.escape(dep)}\(pending\)",
                        "",
                        new_summary,
                    ).strip()
                    fixed += 1
            if new_summary != summary:
                task["summary"] = new_summary

        data["items"] = items
        data["counts"] = self.compute_counts(items)

        if not dry_run:
            self.save_queue(queue_id_or_path, data)

        return {
            "success": True,
            "dependencies_resolved": fixed,
            "completed_deps_found": len(completed_deps),
        }

    @staticmethod
    def _normalize_items(items: Any) -> dict[str, dict[str, Any]]:
        if isinstance(items, dict):
            return dict(items)
        if isinstance(items, list):
            result: dict[str, dict[str, Any]] = {}
            for item in items:
                if isinstance(item, dict):
                    tid = item.get("task_id") or item.get("id") or str(hash(str(item)))
                    result[tid] = item
            return result
        return {}
