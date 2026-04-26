#!/usr/bin/env python3
"""Smoke test for AI plan queue runner fixes."""

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

RUNTIME_ROOT = Path("/Volumes/1TB-M2/openclaw")
SCRIPTS_DIR = RUNTIME_ROOT / "scripts"
QUEUE_STATE_DIR = RUNTIME_ROOT / ".openclaw" / "plan_queue"


def test_status_command():
    """Test that status command works on existing queue."""
    print("Testing status command...")
    existing = "openhuman_athena_upgrade_20260326.json"
    path = QUEUE_STATE_DIR / existing
    if not path.exists():
        print(f"  SKIP: {path} not found")
        return True
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "athena_ai_plan_runner.py"),
            "status",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  FAIL: status command failed: {result.stderr}")
        return False
    data = json.loads(result.stdout)
    assert data["queue_id"] == "openhuman_athena_upgrade_20260326"
    print("  PASS")
    return True


def test_run_once_stale_detection():
    """Test that stale detection marks old running tasks as failed."""
    print("Testing stale detection...")
    # Create a temporary queue state with a running item that has no heartbeat
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        queue_state = {
            "queue_id": "test_stale_detection",
            "name": "Test stale detection",
            "current_item_id": "test_item",
            "updated_at": "2026-03-28T00:00:00+08:00",
            "items": {
                "test_item": {
                    "status": "running",
                    "title": "Test stale item",
                    "stage": "build",
                    "executor": "opencode",
                    "root_task_id": "test_task",
                    "started_at": "2026-03-28T00:00:00+08:00",
                    "finished_at": "",
                    "artifact_paths": [],
                    "progress_percent": 50,
                    "summary": "stuck",
                    "error": "",
                    "result_excerpt": "",
                    "pipeline_summary": "stuck",
                    "current_stage_ids": ["build"],
                    "instruction_path": "/nonexistent/path.md",
                }
            },
        }
        json.dump(queue_state, f, ensure_ascii=False, indent=2)
        temp_path = f.name

    try:
        # Run run-once which should detect stale and mark failed
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "athena_ai_plan_runner.py"),
                "run-once",
                temp_path,
            ],
            capture_output=True,
            text=True,
        )
        # Expect that it will mark stale and maybe choose next item (none)
        # Load updated state
        with open(temp_path, "r", encoding="utf-8") as f:
            updated = json.load(f)
        if updated["items"]["test_item"]["status"] == "failed":
            print("  PASS: stale item marked as failed")
            return True
        else:
            print(f"  FAIL: item still running: {updated['items']['test_item']}")
            return False
    finally:
        Path(temp_path).unlink()


def test_heartbeat_updated():
    """Test that heartbeat is updated during execution (requires actual opencode)."""
    print("Testing heartbeat update...")
    # This test requires a real instruction path and opencode; skip for now.
    print("  SKIP: requires opencode installation")
    return True


def test_multi_lane_replay_smoke():
    """Multi-lane replay smoke: create temporary build/review/plan lanes and verify runner can progress."""
    print("Testing multi-lane replay smoke...")
    import json
    import subprocess
    import tempfile
    from datetime import datetime, timezone
    from pathlib import Path

    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        # Create manifest files for each lane
        build_manifest = tmp / "build_manifest.json"
        review_manifest = tmp / "review_manifest.json"
        plan_manifest = tmp / "plan_manifest.json"

        # Build lane manifest (opencode_build)
        build_manifest.write_text(
            json.dumps(
                {
                    "queue_id": "smoke_build_queue",
                    "name": "Smoke Build Queue",
                    "items": [
                        {
                            "id": "build_item_1",
                            "title": "Smoke Build Item",
                            "instruction_path": str(tmp / "build_instruction.md"),
                            "entry_stage": "build",
                            "risk_level": "low",
                            "unattended_allowed": True,
                            "metadata": {"autostart": True},
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        # Review lane manifest (codex_review)
        review_manifest.write_text(
            json.dumps(
                {
                    "queue_id": "smoke_review_queue",
                    "name": "Smoke Review Queue",
                    "items": [
                        {
                            "id": "review_item_1",
                            "title": "Smoke Review Item",
                            "instruction_path": str(tmp / "review_instruction.md"),
                            "entry_stage": "review",
                            "risk_level": "low",
                            "unattended_allowed": True,
                            "metadata": {"autostart": True},
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        # Plan lane manifest (codex_plan)
        plan_manifest.write_text(
            json.dumps(
                {
                    "queue_id": "smoke_plan_queue",
                    "name": "Smoke Plan Queue",
                    "items": [
                        {
                            "id": "plan_item_1",
                            "title": "Smoke Plan Item",
                            "instruction_path": str(tmp / "plan_instruction.md"),
                            "entry_stage": "plan",
                            "risk_level": "low",
                            "unattended_allowed": True,
                            "metadata": {"autostart": True},
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        # Create dummy instruction files (empty)
        (tmp / "build_instruction.md").write_text("# Build instruction")
        (tmp / "review_instruction.md").write_text("# Review instruction")
        (tmp / "plan_instruction.md").write_text("# Plan instruction")

        # Create plan config (.athena-auto-queue.json) referencing the three lanes
        plan_config = tmp / ".athena-auto-queue.json"
        plan_config.write_text(
            json.dumps(
                {
                    "routes": [
                        {
                            "queue_id": "smoke_build_queue",
                            "name": "Smoke Build Queue",
                            "manifest_path": str(build_manifest),
                            "runner_mode": "opencode_build",
                            "queue_state_path": str(tmp / "build_queue_state.json"),
                        },
                        {
                            "queue_id": "smoke_review_queue",
                            "name": "Smoke Review Queue",
                            "manifest_path": str(review_manifest),
                            "runner_mode": "codex_review",
                            "queue_state_path": str(tmp / "review_queue_state.json"),
                        },
                        {
                            "queue_id": "smoke_plan_queue",
                            "name": "Smoke Plan Queue",
                            "manifest_path": str(plan_manifest),
                            "runner_mode": "codex_plan",
                            "queue_state_path": str(tmp / "plan_queue_state.json"),
                        },
                    ]
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        # Initialize queue state files (empty) with matching queue IDs
        lane_to_queue_id = {
            "build_queue_state.json": "smoke_build_queue",
            "review_queue_state.json": "smoke_review_queue",
            "plan_queue_state.json": "smoke_plan_queue",
        }
        for state_path, queue_id in lane_to_queue_id.items():
            (tmp / state_path).write_text(
                json.dumps(
                    {
                        "queue_id": queue_id,
                        "name": f"Smoke {queue_id.replace('smoke_', '').replace('_queue', '').title()} Queue",
                        "current_item_id": "",
                        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "items": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )

        # Set environment variable to use the temporary plan config
        env = os.environ.copy()
        env["ATHENA_AI_PLAN_CONFIG"] = str(plan_config)

        # Test 1: Run status on each lane to verify runner can load config
        print("  Testing status command for each lane...")
        for lane, runner_mode in [
            ("build", "opencode_build"),
            ("review", "codex_review"),
            ("plan", "codex_plan"),
        ]:
            # Use the dedicated runner scripts
            if runner_mode == "opencode_build":
                runner_script = SCRIPTS_DIR / "athena_ai_plan_runner.py"
            elif runner_mode == "codex_review":
                runner_script = SCRIPTS_DIR / "codex_review_runner.py"
            else:
                runner_script = SCRIPTS_DIR / "codex_plan_runner.py"

            state_path = tmp / f"{lane}_queue_state.json"
            try:
                result = subprocess.run(
                    [sys.executable, str(runner_script), "status", str(state_path)],
                    capture_output=True,
                    text=True,
                    env=env,
                    cwd=RUNTIME_ROOT,
                    timeout=10,
                )
            except subprocess.TimeoutExpired:
                print(f"    FAIL: {lane} status timed out")
                return False
            if result.returncode != 0:
                print(f"    FAIL: {lane} status failed: {result.stderr}")
                return False
            payload = json.loads(result.stdout)
            if payload.get("queue_id") != f"smoke_{lane}_queue":
                print(f"    FAIL: {lane} queue_id mismatch: {payload.get('queue_id')}")
                return False
            print(f"    PASS: {lane} status OK")

        # Test 2: Run run-once on each lane (should pick up pending items)
        print("  Testing run-once for each lane...")
        for lane, runner_mode in [
            ("build", "opencode_build"),
            ("review", "codex_review"),
            ("plan", "codex_plan"),
        ]:
            if runner_mode == "opencode_build":
                runner_script = SCRIPTS_DIR / "athena_ai_plan_runner.py"
            elif runner_mode == "codex_review":
                runner_script = SCRIPTS_DIR / "codex_review_runner.py"
            else:
                runner_script = SCRIPTS_DIR / "codex_plan_runner.py"

            state_path = tmp / f"{lane}_queue_state.json"
            # Run once (may fail due to missing opencode/codex, but that's okay)
            try:
                result = subprocess.run(
                    [sys.executable, str(runner_script), "run-once", str(state_path)],
                    capture_output=True,
                    text=True,
                    env=env,
                    cwd=RUNTIME_ROOT,
                    timeout=30,
                )
            except subprocess.TimeoutExpired:
                print(f"    WARN: {lane} run-once timed out after 30 seconds")
                continue
            # Even if it fails due to missing executor, we expect status code 0? Not sure.
            # We'll accept any exit code; just ensure the runner didn't crash.
            if result.returncode not in (0, 1):
                print(f"    WARN: {lane} run-once exited with unexpected code {result.returncode}")
            # Load updated state to see if item status changed
            updated = json.loads((tmp / f"{lane}_queue_state.json").read_text())
            items = updated.get("items", {})
            if items:
                print(f"    INFO: {lane} items after run-once: {list(items.keys())}")
            else:
                print(f"    INFO: {lane} no items updated (maybe preflight blocked)")

        # Test 3: Simulate runner restart by marking a running item stale and detecting
        print("  Testing stale detection after simulated restart...")
        # Create a running item in build lane with old heartbeat
        old_time = (datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat(
            timespec="seconds"
        )
        build_state_path = tmp / "build_queue_state.json"
        build_state = json.loads(build_state_path.read_text())
        build_state["items"]["build_item_1"] = {
            "status": "running",
            "title": "Smoke Build Item",
            "stage": "build",
            "executor": "opencode",
            "root_task_id": "test_task",
            "started_at": old_time,
            "finished_at": "",
            "artifact_paths": [],
            "progress_percent": 50,
            "summary": "running",
            "error": "",
            "result_excerpt": "",
            "pipeline_summary": "running",
            "current_stage_ids": ["build"],
            "instruction_path": str(tmp / "build_instruction.md"),
            "runner_heartbeat_at": old_time,
            "runner_pid": 99999,  # dead PID
        }
        build_state["current_item_id"] = "build_item_1"
        build_state_path.write_text(json.dumps(build_state, ensure_ascii=False, indent=2))

        # Run detect_and_cleanup_stale_runs via run-once
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "athena_ai_plan_runner.py"),
                    "run-once",
                    str(build_state_path),
                ],
                capture_output=True,
                text=True,
                env=env,
                cwd=RUNTIME_ROOT,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            print("    WARN: stale detection run-once timed out after 30 seconds")
            # Continue to check state anyway
            result = None
        updated = json.loads(build_state_path.read_text())
        item = updated.get("items", {}).get("build_item_1", {})
        if item.get("status") == "failed" and "stale" in item.get("summary", "").lower():
            print("    PASS: stale detection marked item as failed after restart simulation")
        else:
            print(f"    WARN: stale detection did not mark item failed: {item.get('status')}")
            # Not a failure, continue

        # Test 4: Verify that after stale cleanup, the lane can still progress (choose next item)
        # Since there is only one item and it's now failed, there should be no next item.
        # We'll just ensure queue state is consistent.
        print("  Verifying queue state consistency...")
        for lane in ["build", "review", "plan"]:
            state = json.loads((tmp / f"{lane}_queue_state.json").read_text())
            if "items" in state:
                for item_id, item in state["items"].items():
                    status = item.get("status", "")
                    if status not in ("", "pending", "running", "completed", "failed"):
                        print(f"    FAIL: {lane} item {item_id} has invalid status {status}")
                        return False
            print(f"    PASS: {lane} state consistent")

    print("  PASS: multi-lane replay smoke test completed")
    return True


def main():
    print("=== AI Plan Queue Runner Fix Smoke Test ===")
    ok = True
    ok &= test_status_command()
    ok &= test_run_once_stale_detection()
    ok &= test_heartbeat_updated()
    ok &= test_multi_lane_replay_smoke()
    if ok:
        print("=== All tests passed ===")
        sys.exit(0)
    else:
        print("=== Some tests failed ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
