#!/usr/bin/env python3
"""System Health - queue monitoring, protection, and health checks.

Merges: protect_all_queues, protect_queue_state, monitor_queue,
        monitor_queue_health, monitor_gene_management.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# QueueHealthMonitor
# ---------------------------------------------------------------------------

@dataclass
class QueueSample:
    queue_id: str
    status: str
    counts: dict[str, int]
    paused_reason: str = ""
    current_item: str = ""
    sample_time: str = field(default_factory=_now_iso)


class QueueHealthMonitor:
    """Poll queue files and report health metrics including anomalies."""

    def __init__(self, root_dir: str | Path | None = None):
        self.root = Path(root_dir) if root_dir else _root_dir()
        self.plan_queue_dir = self.root / ".openclaw" / "plan_queue"
        self.log_dir = self.root / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._alert_handlers: list[Callable[[str, str, dict[str, Any]], None]] = []

    # -- I/O ----------------------------------------------------------------

    def _load_json(self, path: Path) -> dict[str, Any] | None:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _queue_files(self) -> list[Path]:
        if not self.plan_queue_dir.exists():
            return []
        results: list[Path] = []
        for f in sorted(self.plan_queue_dir.iterdir()):
            if f.suffix == ".json" and not f.name.endswith(".lock"):
                results.append(f)
        return results

    # -- Sampling -----------------------------------------------------------

    def sample(self) -> list[QueueSample]:
        """Return a snapshot of every queue."""
        samples: list[QueueSample] = []
        for qf in self._queue_files():
            data = self._load_json(qf)
            if not data:
                continue
            samples.append(
                QueueSample(
                    queue_id=data.get("queue_id", qf.stem),
                    status=data.get("queue_status", "unknown"),
                    counts=data.get("counts", {}),
                    paused_reason=data.get("pause_reason", ""),
                    current_item=data.get("current_item_id", ""),
                )
            )
        return samples

    def check(self, raise_alerts: bool = True) -> dict[str, Any]:
        """Run a full health check and optionally raise alerts."""
        samples = self.sample()
        anomalies: list[dict[str, Any]] = []
        stats: dict[str, int] = {
            "running": 0, "manual_hold": 0, "empty": 0, "stopped": 0, "dependency_blocked": 0
        }

        for s in samples:
            st = s.status
            stats[st] = stats.get(st, 0) + 1

            # Anomaly: manual_hold with pending tasks
            if st == "manual_hold" and s.counts.get("pending", 0) > 0:
                anomalies.append({
                    "queue_id": s.queue_id,
                    "type": "manual_hold_with_pending",
                    "severity": "warning",
                    "pending_tasks": s.counts["pending"],
                })

            # Anomaly: dependency_blocked
            if st == "dependency_blocked":
                anomalies.append({
                    "queue_id": s.queue_id,
                    "type": "dependency_blocked",
                    "severity": "warning",
                })

            # Anomaly: no current item but running
            if st == "running" and not s.current_item:
                anomalies.append({
                    "queue_id": s.queue_id,
                    "type": "no_current_item",
                    "severity": "warning",
                })

        if raise_alerts and anomalies:
            for alert in anomalies:
                sev = alert.get("severity", "info")
                f"[{sev.upper()}] {alert['queue_id']}: {alert['type']}"
                for handler in self._alert_handlers:
                    with contextlib.suppress(Exception):
                        handler(alert["queue_id"], alert["type"], alert)

        return {"samples": len(samples), "stats": stats, "anomalies": anomalies}

    def register_alert_handler(self, handler: Callable[[str, str, dict[str, Any]], None]) -> None:
        self._alert_handlers.append(handler)

    def monitor_loop(self, interval: int = 60, max_iterations: int | None = None) -> None:
        """Continuous monitoring loop."""
        i = 0
        while max_iterations is None or i < max_iterations:
            try:
                report = self.check(raise_alerts=True)
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] {report['samples']} queues | anomalies: {len(report['anomalies'])}")
            except KeyboardInterrupt:
                print("\nMonitoring stopped.")
                break
            except Exception as e:
                print(f"Health check error: {e}")
            time.sleep(interval)
            i += 1

    # -- Resource checks ----------------------------------------------------

    @staticmethod
    def check_cpu(threshold: float = 80.0) -> dict[str, Any]:
        """Check CPU usage percentage."""
        try:
            import psutil
            pct = psutil.cpu_percent(interval=1)
            return {"cpu_percent": pct, "alert": pct > threshold}
        except ImportError:
            return {"error": "psutil not available"}

    @staticmethod
    def check_memory(threshold_pct: float = 80.0, threshold_free_gb: float = 2.0) -> dict[str, Any]:
        """Check memory usage."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            free_gb = mem.available / (1024**3)
            return {
                "percent": mem.percent,
                "free_gb": round(free_gb, 2),
                "alert_pct": mem.percent > threshold_pct,
                "alert_free": free_gb < threshold_free_gb,
            }
        except ImportError:
            return {"error": "psutil not available"}

    @staticmethod
    def check_disk(threshold: float = 85.0, path: str = "/") -> dict[str, Any]:
        """Check disk usage."""
        try:
            import psutil
            usage = psutil.disk_usage(path)
            return {"percent": usage.percent, "free_gb": round(usage.free / (1024**3), 2), "alert": usage.percent > threshold}
        except ImportError:
            return {"error": "psutil not available"}


# ---------------------------------------------------------------------------
# QueueProtector
# ---------------------------------------------------------------------------

class QueueProtector:
    """Protect queue state from accidental resets and restart runners."""

    DEFAULT_RUNNERS = [
        "athena_ai_plan_runner.py",
        "athena_ai_plan_runner_build.py",
        "athena_ai_plan_runner_codex.py",
    ]

    def __init__(self, root_dir: str | Path | None = None):
        self.root = Path(root_dir) if root_dir else _root_dir()
        self.plan_queue_dir = self.root / ".openclaw" / "plan_queue"
        self.scripts_dir = self.root / "scripts"

    # -- Queue state protection --------------------------------------------

    def protect_all_queues(self, dry_run: bool = False) -> dict[str, Any]:
        """Check all queues for abnormal states and auto-repair them."""
        protected = 0
        repaired: list[str] = []

        if not self.plan_queue_dir.exists():
            return {"success": False, "error": "Queue dir not found"}

        for qf in sorted(self.plan_queue_dir.glob("*.json")):
            if qf.name.endswith(".lock"):
                continue
            try:
                if self._protect_one(qf, dry_run=dry_run):
                    repaired.append(qf.stem)
                    protected += 1
            except Exception as e:
                print(f"Protect error {qf.name}: {e}")

        return {"success": True, "queues_protected": protected, "repaired": repaired}

    def _protect_one(self, path: Path, dry_run: bool = False) -> bool:
        """Fix a single queue if it's in a bad state."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        status = data.get("queue_status", "")
        current_item = data.get("current_item_id", "")
        items = data.get("items", {})

        if status not in ("manual_hold", "stopped") or current_item:
            return False

        pending_ids = [tid for tid, t in items.items() if t.get("status") == "pending"]
        if not pending_ids:
            return False

        data["queue_status"] = "running"
        data["current_item_id"] = pending_ids[0]
        data["current_item_ids"] = pending_ids
        data["pause_reason"] = ""
        data["updated_at"] = _now_iso()

        if not dry_run:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Protected queue {data.get('queue_id')}: running -> {pending_ids[0]}")
        return True

    # -- Runner management --------------------------------------------------

    def check_runners(self, runners: list[str] | None = None) -> dict[str, bool]:
        """Check whether each runner process is alive."""
        runners = runners or self.DEFAULT_RUNNERS
        result: dict[str, bool] = {}
        for r in runners:
            try:
                rc = subprocess.run(["pgrep", "-f", r], capture_output=True, text=True)
                result[r] = rc.returncode == 0
            except Exception:
                result[r] = False
        return result

    def restart_runners(self, runners: list[str] | None = None, dry_run: bool = False) -> dict[str, Any]:
        """Start runners that are not currently running."""
        runners = runners or self.DEFAULT_RUNNERS
        started: list[str] = []
        already_running: list[str] = []

        for r in runners:
            script = self.scripts_dir / r
            if not script.exists():
                continue
            alive = next(iter(self.check_runners([r]).values()), False)
            if alive:
                already_running.append(r)
                continue
            if not dry_run:
                subprocess.Popen(
                    [sys.executable, str(script)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            started.append(r)

        return {"started": started, "already_running": already_running}

    def check_and_restart_runners(self, runners: list[str] | None = None) -> dict[str, Any]:
        """Convenience: check + restart all runners."""
        alive = self.check_runners(runners)
        dead = [r for r, ok in alive.items() if not ok]
        if dead:
            return self.restart_runners(dead)
        return {"started": [], "already_running": list(alive.keys())}


# ---------------------------------------------------------------------------
# SystemHealth - aggregate facade
# ---------------------------------------------------------------------------

class SystemHealth:
    """Top-level system health aggregator combining monitor + protector."""

    def __init__(self, root_dir: str | Path | None = None):
        self.monitor = QueueHealthMonitor(root_dir)
        self.protector = QueueProtector(root_dir)

    def full_check(self) -> dict[str, Any]:
        """Run all health checks: queues, CPU, memory, disk."""
        queue_health = self.monitor.check(raise_alerts=False)
        runners = self.protector.check_runners()
        resources: dict[str, Any] = {"cpu": None, "memory": None, "disk": None}

        with contextlib.suppress(Exception):
            resources["cpu"] = self.monitor.check_cpu()
        with contextlib.suppress(Exception):
            resources["memory"] = self.monitor.check_memory()
        with contextlib.suppress(Exception):
            resources["disk"] = self.monitor.check_disk()

        return {
            "queues": queue_health,
            "runners": runners,
            "resources": resources,
            "timestamp": _now_iso(),
        }
