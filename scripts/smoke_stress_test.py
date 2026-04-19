#!/usr/bin/env python3
"""Smoke test for OpenHuman 24h stress runner.

Runs a very short stress test (2 minutes) to verify the runner works,
generates reports, and writes PID/logs/output directories.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    from openhuman_24h_stress_runner import StressConfig, StressRunner
except ImportError as e:
    print(f"Error: Failed to import stress runner: {e}")
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-minutes", type=float, default=2.0)
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    duration_hours = args.duration_minutes / 60.0

    # Use temporary output directory if not specified
    if args.output_dir:
        output_root = Path(args.output_dir)
    else:
        output_root = Path("/Volumes/1TB-M2/openclaw/workspace/stress_test_smoke")

    # Create a unique report path
    report_dir = Path("/Volumes/1TB-M2/openclaw/workspace")
    report_path = (
        report_dir / f"stress_test_smoke_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )

    print("=== OpenHuman Stress Test Smoke Test ===")
    print(f"Duration: {args.duration_minutes} minutes ({duration_hours:.3f} hours)")
    print(f"Output root: {output_root}")
    print(f"Report path: {report_path}")
    print()

    # Create config
    config = StressConfig(
        duration_hours=duration_hours,
        sample_seconds=30,  # sample every 30 seconds
        performance_seconds=60,
        stability_seconds=60,
        autoresearch_seconds=60,
        report_path=str(report_path),
        output_root=str(output_root),
    )

    # Create and run runner
    runner = StressRunner(config)

    print("Starting stress runner...")
    start_time = time.time()

    # Set up signal handling for early exit
    stop_requested = False

    def signal_handler(signum, frame):
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the runner manually (simplified)
    runner.log_event("smoke_test_started", {"config": vars(args)})

    # Collect initial profile
    profile = runner.best_state_profile()
    print("Initial M4 best state profile collected:")
    print(f"  Recommended build workers: {profile.get('recommended_max_build_workers')}")
    print(f"  Recommendation: {profile.get('recommended_parallel_model')}")

    # Write profile
    profile_path = output_root / "smoke_test_m4_best_state_profile.json"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Profile saved to: {profile_path}")

    # Run a few cycles
    cycle = 0
    max_cycles = int((args.duration_minutes * 60) / config.sample_seconds) + 1

    while not stop_requested and cycle < max_cycles:
        elapsed = time.time() - start_time
        if elapsed >= duration_hours * 3600:
            break

        print(f"\nCycle {cycle + 1}/{max_cycles}")

        # Collect resource sample
        resource = runner.collect_resource_sample()
        print(f"  Resource sample: CPU {resource.get('cpu', {}).get('usage_percent', '?')}%")

        # Run performance monitor if needed
        runner.maybe_run_performance_monitor()
        if runner.latest_performance:
            print(f"  Performance monitor: returncode {runner.latest_performance['returncode']}")

        # Run stability metrics if needed
        runner.maybe_run_stability_metrics()
        if runner.latest_stability:
            print(f"  Stability metrics: returncode {runner.latest_stability['returncode']}")

        # Run autoresearch if needed
        runner.maybe_run_autoresearch()
        if runner.latest_autoresearch:
            print(f"  AutoResearch: returncode {runner.latest_autoresearch['returncode']}")

        # Emit report
        phase = {"name": "smoke_test", "load_strength": "100%"}
        runner.emit_report(phase)
        print(f"  Report updated: {report_path}")

        # Write state
        runner.write_state(phase)

        # Sleep for sample interval
        time.sleep(config.sample_seconds)
        cycle += 1

    # Finalize
    runner.log_event("smoke_test_completed", {"elapsed_seconds": time.time() - start_time})

    # Final report
    runner.emit_report({"name": "completed", "load_strength": "0%"})

    print("\n=== Smoke Test Complete ===")
    print(f"Total elapsed time: {time.time() - start_time:.1f} seconds")
    print(f"Report generated: {report_path}")
    print(f"Output directory: {output_root}")

    # Verify files exist
    required_files = [
        report_path,
        profile_path,
        output_root / "state.json",
        output_root / "events.jsonl",
    ]

    print("\nFile verification:")
    all_exist = True
    for filepath in required_files:
        exists = filepath.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {filepath}")
        if not exists:
            all_exist = False

    if all_exist:
        print("\n✅ All checks passed!")
        return 0
    else:
        print("\n❌ Some files missing!")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
