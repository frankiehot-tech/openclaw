#!/usr/bin/env python3
"""
Smoke test for performance monitoring enhancement.

Validates:
1. Metric collection works (positive path)
2. Alert threshold evaluation (negative path - no alerts expected)
3. Summary output generation (smoke test)
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

try:
    from agent.core.alert_rules import AlertLevel, AlertRule, get_global_alert_engine
    from agent.core.performance_metrics import (
        MetricDimension,
        MetricType,
        PerformanceMetricsCollector,
        get_global_collector,
    )

    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Modules not available: {e}")
    MODULES_AVAILABLE = False


def test_metric_collection() -> bool:
    """Test that metric collection works (positive path)."""
    print("Testing metric collection...")
    if not MODULES_AVAILABLE:
        print("  SKIP: Modules not available")
        return False

    try:
        collector = get_global_collector()

        # Record some test metrics
        collector.record_queue_length(5, "test_queue")
        collector.record_response_time(2.5, labels={"test": "smoke"})
        collector.record_failure_rate(0.05, "test_component")
        collector.record_concurrency(3, "test_worker")
        collector.record_success_rate(0.95, "test_component")

        # Verify samples were recorded
        samples = collector.get_samples(limit=10)
        if len(samples) >= 5:
            print(f"  ✓ Recorded {len(samples)} metric samples")
            return True
        else:
            print(f"  ✗ Only {len(samples)} samples recorded")
            return False
    except Exception as e:
        print(f"  ✗ Metric collection failed: {e}")
        return False


def test_alert_threshold_negative_path() -> bool:
    """Test alert threshold evaluation (negative path - no alerts expected)."""
    print("Testing alert threshold negative path...")
    if not MODULES_AVAILABLE:
        print("  SKIP: Modules not available")
        return False

    try:
        engine = get_global_alert_engine()

        # Clear existing alerts
        engine.alerts.clear()
        engine.last_evaluation.clear()

        # Add a rule with very high threshold that won't be triggered
        high_threshold_rule = AlertRule(
            rule_id="smoke_test_high_threshold",
            metric_dimension=MetricDimension.QUEUE_LENGTH,
            condition=">",
            threshold=1000.0,  # Unlikely to be reached
            alert_level=AlertLevel.CRITICAL,
            description="Smoke test rule",
            cooldown_seconds=0,
        )
        engine.add_rule(high_threshold_rule)

        # Record metric below threshold
        collector = get_global_collector()
        collector.record_queue_length(10, "test_queue")

        # Evaluate alerts
        alerts = engine.evaluate_all()

        # Should have no alerts (negative path)
        if len(alerts) == 0:
            print("  ✓ No alerts generated (negative path passed)")
            # Clean up test rule
            engine.remove_rule("smoke_test_high_threshold")
            return True
        else:
            print(f"  ✗ Unexpected alerts generated: {len(alerts)}")
            for alert in alerts:
                print(f"    - {alert.message}")
            # Clean up test rule
            engine.remove_rule("smoke_test_high_threshold")
            return False
    except Exception as e:
        print(f"  ✗ Alert threshold test failed: {e}")
        return False


def test_summary_output_smoke() -> bool:
    """Test summary output generation (smoke test)."""
    print("Testing summary output generation...")
    if not MODULES_AVAILABLE:
        print("  SKIP: Modules not available")
        return False

    try:
        collector = get_global_collector()
        engine = get_global_alert_engine()

        # Generate summaries
        metrics_summary = collector.export_summary()
        alerts_summary = engine.export_summary()

        # Basic validation
        if not isinstance(metrics_summary, dict):
            print("  ✗ Metrics summary is not a dict")
            return False
        if not isinstance(alerts_summary, dict):
            print("  ✗ Alerts summary is not a dict")
            return False

        # Check required fields
        required_metric_fields = ["timestamp", "sample_count", "aggregation_count"]
        for field in required_metric_fields:
            if field not in metrics_summary:
                print(f"  ✗ Metrics summary missing field: {field}")
                return False

        required_alert_fields = ["timestamp", "active_alert_count", "rule_count"]
        for field in required_alert_fields:
            if field not in alerts_summary:
                print(f"  ✗ Alerts summary missing field: {field}")
                return False

        print("  ✓ Summary output generated and validated")
        return True
    except Exception as e:
        print(f"  ✗ Summary output test failed: {e}")
        return False


def test_performance_monitor_script() -> bool:
    """Test performance_monitor.py script runs without error."""
    print("Testing performance_monitor.py script...")

    script_path = Path(__file__).parent / "performance_monitor.py"
    if not script_path.exists():
        print(f"  SKIP: Script not found at {script_path}")
        return False

    try:
        import subprocess

        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("  ✓ Script runs successfully")
            return True
        else:
            print(f"  ✗ Script failed with return code {result.returncode}")
            print(f"    stderr: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"  ✗ Script test failed: {e}")
        return False


def main() -> int:
    """Run all smoke tests."""
    print("=" * 60)
    print("Performance Monitoring Enhancement Smoke Tests")
    print("=" * 60)

    tests = [
        ("Metric Collection", test_metric_collection),
        ("Alert Threshold Negative Path", test_alert_threshold_negative_path),
        ("Summary Output Smoke", test_summary_output_smoke),
        ("Performance Monitor Script", test_performance_monitor_script),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print("\n❌ Some tests failed")
        return 1
    else:
        print("\n✅ All tests passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
