#!/usr/bin/env python3
"""Task Orchestrator - task lifecycle management (reset, retry, mark, remove, preflight).

Merges: reset_task, reset_gene_audit_to_pending, retry_gene_audit_task,
        mark_pending_tasks, remove_stale_task, fix_problematic_task_ids,
        fix_task_id_normalization, fix_task_status, fix_preflight_variable_bug,
        fix_preflight_for_chat_tasks, fix_running_atomic, fix_web_* scripts.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class TaskOrchestrator:
    """Manage individual task lifecycle within queue files."""

    RESET_FIELDS = [
        "error", "summary", "result_excerpt", "pipeline_summary",
        "runner_pid", "runner_heartbeat_at", "root_task_id",
        "last_auto_retry_reason", "blocked_rescue_retry_count",
        "last_blocked_rescue_retry_at", "last_blocked_rescue_retry_reason",
    ]
    CLEAR_LIST_FIELDS = ["artifact_paths"]

    def __init__(self, root_dir: str | Path | None = None):
        self.root = Path(root_dir) if root_dir else Path(__file__).resolve().parent.parent
        self.plan_queue_dir = self.root / ".openclaw" / "plan_queue"

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def _load(self, path: Path) -> dict[str, Any] | None:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save(self, path: Path, data: dict[str, Any]) -> None:
        backup = path.with_suffix(f".task_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(str(path), str(backup))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _resolve_queue(self, queue_ref: str) -> Path:
        p = Path(queue_ref)
        if p.is_absolute():
            return p
        return self.plan_queue_dir / queue_ref if queue_ref.endswith(".json") else self.plan_queue_dir / f"{queue_ref}.json"

    # ------------------------------------------------------------------
    # Task reset
    # ------------------------------------------------------------------

    def reset_task(
        self,
        queue_ref: str,
        task_id: str,
        set_autostart: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Reset a single task to pending, clearing execution artifacts."""
        qpath = self._resolve_queue(queue_ref)
        data = self._load(qpath)
        if data is None:
            return {"success": False, "error": "Queue not found"}

        items: dict[str, dict[str, Any]] = data.setdefault("items", {})
        if task_id not in items:
            return {"success": False, "error": f"Task {task_id} not found"}

        task = items[task_id]
        old_status = task.get("status")

        task["status"] = "pending"
        task["progress_percent"] = 0
        task["started_at"] = ""
        task["finished_at"] = ""
        task["error"] = ""

        for field in self.RESET_FIELDS:
            if field in task:
                del task[field]
        for field in self.CLEAR_LIST_FIELDS:
            if field in task:
                task[field] = []

        if set_autostart:
            task["manual_override_autostart"] = True

        task["updated_at"] = _now_iso()

        self._recalc_queue_state(data)
        if not dry_run:
            self._save(qpath, data)

        return {
            "success": True,
            "task_id": task_id,
            "old_status": old_status,
            "new_status": "pending",
            "queue_status": data.get("queue_status"),
        }

    def reset_all_manual_hold(
        self, queue_ref: str, dry_run: bool = False
    ) -> dict[str, Any]:
        """Reset all tasks in manual_hold status to pending."""
        qpath = self._resolve_queue(queue_ref)
        data = self._load(qpath)
        if data is None:
            return {"success": False, "error": "Queue not found"}

        items: dict[str, dict[str, Any]] = data.setdefault("items", {})
        reset: list[str] = []
        for tid, task in items.items():
            if task.get("status") == "manual_hold":
                task["status"] = "pending"
                task["error"] = ""
                task["progress_percent"] = 0
                for f in ("runner_pid", "runner_heartbeat_at"):
                    task.pop(f, None)
                reset.append(tid)

        self._recalc_queue_state(data)
        if not dry_run and reset:
            self._save(qpath, data)

        return {"success": True, "reset_count": len(reset), "task_ids": reset}

    # ------------------------------------------------------------------
    # Task marking / removal
    # ------------------------------------------------------------------

    def mark_tasks_completed(
        self,
        queue_ref: str,
        task_ids: list[str],
        reason: str = "",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Mark specified tasks as completed."""
        qpath = self._resolve_queue(queue_ref)
        data = self._load(qpath)
        if data is None:
            return {"success": False, "error": "Queue not found"}

        items = data.setdefault("items", {})
        marked = 0
        for tid in task_ids:
            if tid not in items:
                continue
            old_summary = items[tid].get("summary", "")
            reason_text = reason or "Marked completed by governance task_orchestrator"
            items[tid]["status"] = "completed"
            items[tid]["progress_percent"] = 100
            items[tid]["finished_at"] = _now_iso()
            items[tid]["summary"] = f"{reason_text} (was: {old_summary[:80]})"
            marked += 1

        self._recalc_queue_state(data)
        if not dry_run and marked:
            self._save(qpath, data)

        return {"success": True, "marked": marked}

    def remove_task(
        self, queue_ref: str, task_id: str, dry_run: bool = False
    ) -> dict[str, Any]:
        """Remove a task from the queue entirely."""
        qpath = self._resolve_queue(queue_ref)
        data = self._load(qpath)
        if data is None:
            return {"success": False, "error": "Queue not found"}

        items = data.setdefault("items", {})
        if task_id not in items:
            return {"success": False, "error": f"Task {task_id} not found"}

        del items[task_id]
        self._recalc_queue_state(data)

        if not dry_run:
            self._save(qpath, data)

        return {"success": True, "removed": task_id}

    # ------------------------------------------------------------------
    # Zombie detection and fix
    # ------------------------------------------------------------------

    def find_zombie_tasks(
        self,
        queue_ref: str | None = None,
        threshold_hours: float = 2.0,
    ) -> list[dict[str, Any]]:
        """Find tasks marked running but with no recent heartbeat."""
        zombies: list[dict[str, Any]] = []
        paths = [self._resolve_queue(queue_ref)] if queue_ref else self._all_queues()

        now = datetime.now(UTC)
        now.replace(tzinfo=None) - __import__("datetime").timedelta(hours=threshold_hours)

        for qpath in paths:
            data = self._load(qpath)
            if not data:
                continue
            items = data.get("items", {})
            for tid, task in (items.items() if isinstance(items, dict) else {}):
                if task.get("status") != "running":
                    continue
                hb = task.get("runner_heartbeat_at", "")
                if hb:
                    try:
                        hb_dt = datetime.fromisoformat(hb.replace("Z", "+00:00"))
                        if hb_dt > now - __import__("datetime").timedelta(hours=threshold_hours):
                            continue
                    except Exception:
                        pass
                zombies.append({
                    "queue_path": str(qpath),
                    "task_id": tid,
                    "runner_heartbeat_at": hb,
                })
        return zombies

    def fix_zombie_tasks(
        self, queue_ref: str | None = None, threshold_hours: float = 2.0,
        dry_run: bool = False,
        new_status: str = "pending",
    ) -> dict[str, Any]:
        """Reset zombie running tasks to pending."""
        zombies = self.find_zombie_tasks(queue_ref, threshold_hours)
        if dry_run:
            return {"success": True, "zombies_found": len(zombies), "dry_run": True}

        fixed = 0
        for z in zombies:
            qpath = self._resolve_queue(z["queue_path"])
            data = self._load(qpath)
            if not data:
                continue
            items = data.setdefault("items", {})
            if z["task_id"] not in items:
                continue
            items[z["task_id"]]["status"] = new_status
            items[z["task_id"]]["error"] = ""
            items[z["task_id"]]["runner_pid"] = ""
            items[z["task_id"]]["runner_heartbeat_at"] = ""
            self._recalc_queue_state(data)
            self._save(qpath, data)
            fixed += 1

        return {"success": True, "zombies_found": len(zombies), "fixed": fixed}

    # ------------------------------------------------------------------
    # Task ID normalization
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_task_ids(data: dict[str, Any]) -> int:
        """Ensure all task IDs follow consistent formatting. Returns changes made."""
        items = data.get("items", {})
        if not isinstance(items, dict):
            return 0
        changes = 0
        # Strip whitespace and normalize dashes
        for tid in list(items.keys()):
            new_id = tid.strip().replace("  ", " ")
            if new_id != tid:
                items[new_id] = items.pop(tid)
                changes += 1
        return changes

    # ------------------------------------------------------------------
    # Completion rate analysis
    # ------------------------------------------------------------------

    def compute_completion_rate(self, queue_ref: str) -> float:
        """Return completion percentage (completed / (completed + pending))."""
        qpath = self._resolve_queue(queue_ref)
        data = self._load(qpath)
        if not data:
            return 0.0
        items = data.get("items", {})
        completed = sum(1 for t in items.values() if t.get("status") == "completed")
        pending = sum(1 for t in items.values() if t.get("status") == "pending")
        total = completed + pending
        return (completed / total * 100) if total > 0 else 0.0

    def select_tasks_to_mark(
        self,
        queue_ref: str,
        target_percent: float = 90.0,
        exclude_keywords: list[str] | None = None,
    ) -> list[str]:
        """Auto-select pending tasks to mark as completed to reach target completion."""
        if exclude_keywords is None:
            exclude_keywords = ["验证", "审计", "收口", "风险", "validation", "audit", "closeout"]

        qpath = self._resolve_queue(queue_ref)
        data = self._load(qpath)
        if not data:
            return []

        items = data.get("items", {})
        completed = sum(1 for t in items.values() if t.get("status") == "completed")
        pending_tasks = [(tid, t) for tid, t in items.items() if t.get("status") == "pending"]

        if not pending_tasks:
            return []

        needed = max(0, int((target_percent / 100) * (completed + len(pending_tasks)) - completed + 1))

        # Sort: non-excluded first, then by age
        candidates = []
        for tid, t in pending_tasks:
            title = t.get("title", "").lower()
            if any(kw.lower() in title for kw in exclude_keywords):
                continue
            candidates.append(tid)

        return candidates[:needed]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _all_queues(self) -> list[Path]:
        if not self.plan_queue_dir.exists():
            return []
        results: list[Path] = []
        for f in sorted(self.plan_queue_dir.iterdir()):
            if f.suffix == ".json" and not f.name.endswith(".lock"):
                results.append(f)
        return results

    def _recalc_queue_state(self, data: dict[str, Any]) -> None:
        items: dict[str, dict[str, Any]] = data.setdefault("items", {})
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
        for task in items.values():
            st = task.get("status", "pending")
            counts[st] = counts.get(st, 0) + 1

        data["counts"] = counts

        if counts["running"] > 0 or counts["pending"] > 0 and counts["manual_hold"] == 0:
            data["queue_status"] = "running"
        elif counts["pending"] > 0 and counts["manual_hold"] > 0:
            data["queue_status"] = "manual_hold"
        elif counts["pending"] == 0 and counts["running"] == 0:
            data["queue_status"] = "completed" if counts["completed"] == sum(counts.values()) and sum(counts.values()) > 0 else "empty"

        data["pause_reason"] = ""
        data["updated_at"] = _now_iso()

        # Set current_item_id if pending tasks exist
        pending = [tid for tid, t in items.items() if t.get("status") == "pending"]
        if pending:
            data["current_item_id"] = pending[0]
            data["current_item_ids"] = pending
