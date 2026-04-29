#!/usr/bin/env python3
"""Test performance metrics collection.

Includes:
1. Smoke test - normal data collection
2. Negative path test - missing/corrupted data
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from collect_performance_metrics import MetricsCollector, SystemMetrics


def test_smoke_collection() -> None:
    """Smoke test: collect metrics from real data."""
    print("Running smoke test...")

    runtime_root = Path("/Volumes/1TB-M2/openclaw")
    collector = MetricsCollector(runtime_root)

    # This should not raise exceptions
    metrics = collector.collect()

    # Basic validation
    assert isinstance(metrics, SystemMetrics)
    assert metrics.timestamp is not None
    assert metrics.total_tasks >= 0
    assert metrics.total_completed >= 0
    assert metrics.total_failed >= 0
    assert metrics.total_pending >= 0
    assert metrics.total_stale >= 0
    assert 0 <= metrics.overall_success_rate <= 1
    assert metrics.overall_throughput_24h >= 0
    assert metrics.missing_artifacts_count >= 0
    assert metrics.duplicate_tasks_count >= 0
    assert isinstance(metrics.data_quality_issues, list)

    print(f"  ✓ Collected metrics: {metrics.total_tasks} tasks")
    print(f"  ✓ Success rate: {metrics.overall_success_rate:.1%}")
    print(f"  ✓ Missing artifacts: {metrics.missing_artifacts_count}")
    print(f"  ✓ Duplicate tasks: {metrics.duplicate_tasks_count}")
    print(f"  ✓ Data quality issues: {len(metrics.data_quality_issues)}")

    # Test writing baseline
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "baseline.json"
        collector.write_baseline(metrics, output_path)
        assert output_path.exists()

        # Verify JSON can be loaded
        with open(output_path) as f:
            loaded = json.load(f)
        assert "timestamp" in loaded
        print("  ✓ Baseline file written and loadable")

    print("  Smoke test passed")


def test_negative_path_missing_files() -> None:
    """Negative path test: missing tasks.json and queue directory."""
    print("Running negative path test (missing files)...")

    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_root = Path(tmpdir)
        # Create empty .openclaw directory structure
        openclaw_dir = runtime_root / ".openclaw"
        openclaw_dir.mkdir(parents=True)
        (openclaw_dir / "orchestrator").mkdir()
        (openclaw_dir / "plan_queue").mkdir()

        # No tasks.json file
        collector = MetricsCollector(runtime_root)

        # Should not crash
        metrics = collector.collect()

        # Should have zero tasks
        assert metrics.total_tasks == 0
        assert metrics.total_completed == 0
        assert metrics.total_failed == 0
        assert metrics.total_pending == 0
        assert metrics.total_stale == 0
        assert metrics.overall_success_rate == 0.0
        assert metrics.overall_throughput_24h == 0.0
        assert metrics.avg_latency_all is None
        assert metrics.queue_metrics == []

        print("  ✓ Handled missing tasks.json gracefully")

    print("  Negative path test (missing files) passed")


def test_negative_path_corrupted_json() -> None:
    """Negative path test: corrupted tasks.json."""
    print("Running negative path test (corrupted JSON)...")

    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_root = Path(tmpdir)
        openclaw_dir = runtime_root / ".openclaw"
        openclaw_dir.mkdir(parents=True)
        orchestrator_dir = openclaw_dir / "orchestrator"
        orchestrator_dir.mkdir()

        # Write invalid JSON
        tasks_path = orchestrator_dir / "tasks.json"
        with open(tasks_path, "w") as f:
            f.write("{ invalid json }")

        # Create empty plan_queue directory
        (openclaw_dir / "plan_queue").mkdir()

        collector = MetricsCollector(runtime_root)

        # Should not crash
        metrics = collector.collect()

        # Should have zero tasks (due to empty fallback)
        assert metrics.total_tasks == 0
        print("  ✓ Handled corrupted JSON gracefully")

    print("  Negative path test (corrupted JSON) passed")


def test_negative_path_malformed_timestamps() -> None:
    """Negative path test: tasks with malformed timestamps."""
    print("Running negative path test (malformed timestamps)...")

    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_root = Path(tmpdir)
        openclaw_dir = runtime_root / ".openclaw"
        openclaw_dir.mkdir(parents=True)
        orchestrator_dir = openclaw_dir / "orchestrator"
        orchestrator_dir.mkdir()

        # Create tasks with invalid timestamps
        tasks_data = {
            "version": 1,
            "tasks": [
                {
                    "id": "test-1",
                    "status": "completed",
                    "created_at": "not-a-date",
                    "started_at": "2026-01-01T00:00:00",
                    "finished_at": "2026-01-01T01:00:00",
                    "artifact_path": "/tmp/artifact.md",
                    "error": "",
                },
                {
                    "id": "test-2",
                    "status": "pending",
                    "created_at": "2026-01-01T00:00:00",
                    "started_at": "",
                    "finished_at": "",
                    "artifact_path": "",
                    "error": "",
                },
            ],
        }

        tasks_path = orchestrator_dir / "tasks.json"
        with open(tasks_path, "w") as f:
            json.dump(tasks_data, f)

        (openclaw_dir / "plan_queue").mkdir()

        collector = MetricsCollector(runtime_root)

        # Should not crash
        metrics = collector.collect()

        # Should still process what it can
        assert metrics.total_tasks == 2
        assert metrics.total_completed == 1
        assert metrics.total_pending == 1

        # Data quality issues should include timestamp parsing errors
        # (our collector logs but doesn't add to data_quality_issues)
        print("  ✓ Handled malformed timestamps gracefully")

    print("  Negative path test (malformed timestamps) passed")


def main() -> None:
    """Run all tests."""
    print("=" * 60)
    print("Performance Metrics Tests")
    print("=" * 60)

    test_smoke_collection()
    print()

    test_negative_path_missing_files()
    print()

    test_negative_path_corrupted_json()
    print()

    test_negative_path_malformed_timestamps()
    print()

    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
