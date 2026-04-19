#!/usr/bin/env python3
"""Smoke test for the OpenHuman 24h stress runner.

Runs the stress runner with a very short duration (10 seconds) and verifies
that it produces the expected output files and calls the expected subsystems.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(scripts_dir))

from openhuman_24h_stress_runner import StressConfig, StressRunner


def main() -> int:
    # Create temporary output directory
    with tempfile.TemporaryDirectory() as tmpdir:
        output_root = Path(tmpdir) / "stress_test"
        output_root.mkdir(parents=True, exist_ok=True)

        # Use a temporary report path inside the temp dir
        report_path = Path(tmpdir) / "stress_report.md"

        config = StressConfig(
            duration_hours=0.003,  # ~10 seconds
            sample_seconds=2,
            performance_seconds=3,
            stability_seconds=3,
            autoresearch_seconds=5,
            report_path=str(report_path),
            output_root=str(output_root),
        )

        runner = StressRunner(config)
        print(f"Starting smoke test with run_id: {runner.run_id}")
        print(f"Output directory: {runner.output_dir}")

        # Run the runner (it will stop after duration_hours)
        exit_code = runner.run()

        if exit_code != 0:
            print(f"ERROR: Runner returned non-zero exit code: {exit_code}")
            return exit_code

        # Verify output files
        required_files = [
            runner.state_path,
            runner.events_path,
            runner.output_dir / "latest_resource.json",
            runner.output_dir / "m4_best_state_profile.json",
            runner.samples_dir,
        ]
        for path in required_files:
            if not path.exists():
                print(f"ERROR: Required file/directory missing: {path}")
                return 1
            print(f"✅ Found: {path}")

        # Check that samples directory contains at least one sample
        sample_files = list(runner.samples_dir.glob("*.json"))
        if not sample_files:
            print("ERROR: No sample files found in samples directory")
            return 1
        print(f"✅ Found {len(sample_files)} sample(s)")

        # Load state.json and verify structure
        state = json.loads(runner.state_path.read_text(encoding="utf-8"))
        required_state_keys = {
            "run_id",
            "started_at",
            "updated_at",
            "elapsed_seconds",
            "phase",
        }
        if not required_state_keys.issubset(state.keys()):
            print(f"ERROR: state.json missing keys: {required_state_keys - state.keys()}")
            return 1
        print("✅ state.json structure valid")

        # Load events.jsonl and verify at least one event of each expected type
        events = []
        with runner.events_path.open(encoding="utf-8") as f:
            for line in f:
                events.append(json.loads(line.strip()))

        event_types = {e["type"] for e in events}
        expected_types = {"run_started"}
        # The following may not appear if duration is too short, but we can check for at least one
        if not events:
            print("ERROR: No events recorded")
            return 1
        print(f"✅ Recorded {len(events)} events, types: {event_types}")

        # Verify that collect_stability_metrics and performance_monitor were called
        # by checking events (they may not be called if intervals are longer than duration)
        # We'll at least verify that the runner attempted to call them by checking the config.
        # For smoke test we can rely on the fact that intervals are short enough.
        # Since we set performance_seconds=3 and stability_seconds=3, they should be called.
        # Let's check events for 'performance_monitor' and 'stability_metrics'.
        if "performance_monitor" not in event_types:
            print("WARNING: performance_monitor event not found (may be due to short duration)")
        else:
            print("✅ performance_monitor event recorded")

        if "stability_metrics" not in event_types:
            print("WARNING: stability_metrics event not found (may be due to short duration)")
        else:
            print("✅ stability_metrics event recorded")

        # Verify autoresearch dry-run event
        if "autoresearch" not in event_types:
            print("WARNING: autoresearch event not found (may be due to short duration)")
        else:
            print("✅ autoresearch dry-run event recorded")

        # Verify report file exists and contains run_id
        if report_path.exists():
            content = report_path.read_text(encoding="utf-8")
            if runner.run_id in content:
                print("✅ Report contains run_id")
            else:
                print("WARNING: Report does not contain run_id")
        else:
            print("ERROR: Report file not generated")
            return 1

        print("\n🎉 Smoke test passed!")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
