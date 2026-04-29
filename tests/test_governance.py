"""Tests for governance/* modules — queue management, health, repair, orchestration."""

import json

from governance.repair_tools import RepairTools
from governance.task_orchestrator import TaskOrchestrator

from governance.queue_manager import QueueManager
from governance.system_health import QueueHealthMonitor, QueueProtector, SystemHealth

# =========================================================================
# QueueManager tests
# =========================================================================

class TestQueueManagerLoad:
    def test_load_nonexistent_returns_none(self):
        qm = QueueManager("/tmp/nonexistent_openclaw_root")
        assert qm.load_queue("no_such_queue") is None

    def test_compute_counts_all_pending(self):
        items = {
            "t1": {"status": "pending"},
            "t2": {"status": "pending"},
        }
        counts = QueueManager.compute_counts(items)
        assert counts["pending"] == 2
        assert counts["running"] == 0
        assert counts["completed"] == 0

    def test_compute_counts_mixed(self):
        items = {
            "t1": {"status": "pending"},
            "t2": {"status": "running"},
            "t3": {"status": "completed"},
            "t4": {"status": "failed"},
            "t5": {"status": "manual_hold"},
        }
        counts = QueueManager.compute_counts(items)
        assert counts == {"pending": 1, "running": 1, "completed": 1, "failed": 1, "manual_hold": 1}

    def test_compute_counts_unknown_status_defaults_to_pending(self):
        items = {"t1": {"status": "alien_status"}}
        counts = QueueManager.compute_counts(items)
        assert counts["pending"] == 1


class TestQueueManagerDeriveStatus:
    def test_running_when_running_tasks(self):
        status, reason = QueueManager.derive_queue_status({"running": 1})
        assert status == "running"
        assert reason == ""

    def test_dependency_blocked(self):
        status, reason = QueueManager.derive_queue_status({"pending": 2}, has_dependency_block=True)
        assert status == "dependency_blocked"
        assert reason == "dependency_block"

    def test_manual_hold_with_pending(self):
        status, reason = QueueManager.derive_queue_status({"pending": 2, "manual_hold": 2})
        assert status == "manual_hold"

    def test_completed(self):
        status, reason = QueueManager.derive_queue_status({"completed": 5, "pending": 0, "running": 0})
        assert status == "completed"

    def test_empty(self):
        status, reason = QueueManager.derive_queue_status({"pending": 0, "running": 0, "completed": 0})
        assert status == "empty"


class TestQueueManagerListQueues:
    def test_list_queues_nonexistent_dir(self):
        qm = QueueManager("/tmp/nonexistent_xyz_root")
        assert qm.list_queues() == []

    def test_list_queues_skips_backups(self, tmp_path):
        qdir = tmp_path / ".openclaw" / "plan_queue"
        qdir.mkdir(parents=True)
        (qdir / "queue.json").write_text("{}")
        (qdir / "queue.backup_2024.json").write_text("{}")
        (qdir / "queue.lock").write_text("")
        qm = QueueManager(tmp_path)
        names = {f.name for f in qm.list_queues()}
        assert "queue.json" in names
        assert "queue.backup_2024.json" not in names
        assert "queue.lock" not in names


# =========================================================================
# SystemHealth tests
# =========================================================================

class TestQueueHealthMonitor:
    def test_sample_empty_dir(self, tmp_path):
        qdir = tmp_path / ".openclaw" / "plan_queue"
        qdir.mkdir(parents=True)
        monitor = QueueHealthMonitor(tmp_path)
        samples = monitor.sample()
        assert samples == []

    def test_check_returns_structure(self, tmp_path):
        qdir = tmp_path / ".openclaw" / "plan_queue"
        qdir.mkdir(parents=True)
        data = {
            "queue_id": "test_q",
            "queue_status": "running",
            "counts": {"pending": 1, "running": 1, "completed": 0, "failed": 0, "manual_hold": 0},
            "current_item_id": "task_1",
        }
        (qdir / "test_q.json").write_text(json.dumps(data))
        monitor = QueueHealthMonitor(tmp_path)
        result = monitor.check(raise_alerts=False)
        assert "samples" in result
        assert "stats" in result
        assert "anomalies" in result
        assert result["samples"] == 1
        assert result["stats"].get("running") == 1

    def test_check_detects_no_current_item(self, tmp_path):
        qdir = tmp_path / ".openclaw" / "plan_queue"
        qdir.mkdir(parents=True)
        data = {
            "queue_id": "test_q",
            "queue_status": "running",
            "counts": {"pending": 0, "running": 1, "completed": 0, "failed": 0, "manual_hold": 0},
            "current_item_id": "",
        }
        (qdir / "test_q.json").write_text(json.dumps(data))
        monitor = QueueHealthMonitor(tmp_path)
        result = monitor.check(raise_alerts=False)
        assert len(result["anomalies"]) == 1
        assert result["anomalies"][0]["type"] == "no_current_item"

    def test_register_alert_handler_fires(self, tmp_path):
        qdir = tmp_path / ".openclaw" / "plan_queue"
        qdir.mkdir(parents=True)
        data = {
            "queue_id": "test_q",
            "queue_status": "manual_hold",
            "counts": {"pending": 2, "running": 0, "completed": 0, "failed": 0, "manual_hold": 1},
            "current_item_id": "",
        }
        (qdir / "test_q.json").write_text(json.dumps(data))
        monitor = QueueHealthMonitor(tmp_path)
        fired = []
        monitor.register_alert_handler(lambda qid, atype, alert: fired.append((qid, atype)))
        monitor.check(raise_alerts=True)
        assert len(fired) >= 1

    def test_check_cpu_returns_dict(self):
        result = QueueHealthMonitor.check_cpu()
        assert isinstance(result, dict)

    def test_check_memory_returns_dict(self):
        result = QueueHealthMonitor.check_memory()
        assert isinstance(result, dict)


class TestQueueProtector:
    def test_protect_all_queues_no_dir(self, tmp_path):
        protector = QueueProtector(tmp_path / "nonexistent")
        result = protector.protect_all_queues(dry_run=True)
        assert result["success"] is False
        assert "error" in result

    def test_check_runners_returns_dict(self):
        protector = QueueProtector()
        result = protector.check_runners()
        assert isinstance(result, dict)


class TestSystemHealth:
    def test_full_check_returns_structure(self, tmp_path):
        (tmp_path / ".openclaw" / "plan_queue").mkdir(parents=True)
        health = SystemHealth(tmp_path)
        result = health.full_check()
        assert "queues" in result
        assert "runners" in result
        assert "resources" in result
        assert "timestamp" in result


# =========================================================================
# RepairTools tests
# =========================================================================

class TestRepairTools:
    def test_extract_dependency_refs_empty(self):
        assert RepairTools.extract_dependency_refs("") == []
        assert RepairTools.extract_dependency_refs("no deps here") == []

    def test_extract_dependency_refs_finds_refs(self):
        summary = "some work\n被依赖项阻塞：task_abc(pending)\nmore text"
        refs = RepairTools.extract_dependency_refs(summary)
        assert refs == ["task_abc"]

    def test_extract_dependency_refs_multiple(self):
        summary = "被依赖项阻塞：task_a(pending) and 被依赖项阻塞：task_b(pending)"
        refs = RepairTools.extract_dependency_refs(summary)
        assert len(refs) == 2

    def test_find_stale_tasks_empty_dir(self, tmp_path):
        rt = RepairTools(tmp_path / "nonexistent")
        assert rt.find_stale_tasks() == []

    def test_fix_manifest_duplicates_missing_file(self):
        rt = RepairTools()
        result = rt.fix_manifest_duplicates("/tmp/nonexistent_manifest_xyz.json", dry_run=True)
        assert result["success"] is False

    def test_fix_manifest_duplicates_removes_dupes(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({
            "items": [
                {"id": "a", "data": 1},
                {"id": "a", "data": 2},
                {"id": "b", "data": 3},
            ]
        }))
        rt = RepairTools(tmp_path)
        result = rt.fix_manifest_duplicates(str(manifest), dry_run=True)
        assert result["success"] is True
        assert result["duplicates_removed"] == 1
        assert result["remaining"] == 2

    def test_check_process_returns_bool(self):
        result = RepairTools.check_process("python")
        assert isinstance(result, bool)


# =========================================================================
# TaskOrchestrator tests
# =========================================================================

class TestTaskOrchestrator:
    def test_reset_task_nonexistent_queue(self):
        to = TaskOrchestrator("/tmp/nonexistent_orch_root")
        result = to.reset_task("no_queue", "task_1", dry_run=True)
        assert result["success"] is False
        assert "error" in result

    def test_reset_task_nonexistent_task(self, tmp_path):
        qdir = tmp_path / ".openclaw" / "plan_queue"
        qdir.mkdir(parents=True)
        (qdir / "queue.json").write_text(json.dumps({"items": {"t1": {"status": "running"}}}))
        to = TaskOrchestrator(tmp_path)
        result = to.reset_task("queue", "nonexistent_task", dry_run=True)
        assert result["success"] is False

    def test_compute_completion_rate_missing(self):
        to = TaskOrchestrator("/tmp/nonexistent_orch_root")
        assert to.compute_completion_rate("no_queue") == 0.0

    def test_compute_completion_rate_half(self, tmp_path):
        qdir = tmp_path / ".openclaw" / "plan_queue"
        qdir.mkdir(parents=True)
        (qdir / "q.json").write_text(json.dumps({
            "items": {
                "t1": {"status": "completed"},
                "t2": {"status": "pending"},
            }
        }))
        to = TaskOrchestrator(tmp_path)
        rate = to.compute_completion_rate("q")
        assert rate == 50.0

    def test_normalize_task_ids_strips_whitespace(self):
        data = {"items": {" task_1 ": {"status": "pending"}, "task_2": {"status": "running"}}}
        changes = TaskOrchestrator.normalize_task_ids(data)
        assert changes == 1
        assert "task_1" in data["items"]
        assert " task_1 " not in data["items"]

    def test_remove_task_nonexistent(self):
        to = TaskOrchestrator("/tmp/nonexistent_orch_root")
        result = to.remove_task("no_queue", "task_1", dry_run=True)
        assert result["success"] is False

    def test_mark_tasks_completed(self, tmp_path):
        qdir = tmp_path / ".openclaw" / "plan_queue"
        qdir.mkdir(parents=True)
        (qdir / "q.json").write_text(json.dumps({
            "items": {
                "t1": {"status": "pending"},
                "t2": {"status": "pending"},
            }
        }))
        to = TaskOrchestrator(tmp_path)
        result = to.mark_tasks_completed("q", ["t1", "t2"], reason="test", dry_run=True)
        assert result["success"] is True
        assert result["marked"] == 2
