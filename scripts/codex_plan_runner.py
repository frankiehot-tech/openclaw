#!/usr/bin/env python3
"""Dedicated Codex planning runner for Athena AI plan queues."""

from __future__ import annotations

import argparse
from pathlib import Path

from athena_ai_plan_runner import daemon_mode, run_once_mode, status_mode
from openclaw_roots import RUNTIME_ROOT, pid_file

PID_FILE = pid_file("codex_plan_runner")
ACCEPTED_RUNNER_MODES = {"codex_plan", "manual_plan"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Athena Codex plan queue runner")
    parser.add_argument(
        "command",
        nargs="?",
        default="daemon",
        choices=["daemon", "run-once", "status"],
        help="Command to execute: daemon (default), run-once, status",
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="For run-once/status: queue state file path, queue ID, or route ID",
    )
    parser.add_argument(
        "--queue-id",
        help="Queue ID to operate on (if target not provided)",
    )
    args = parser.parse_args()

    if args.command in ("run-once", "status") and not args.target and not args.queue_id:
        parser.error("run-once 和 status 需要 target 或 --queue-id")

    target = args.target or args.queue_id
    if args.command == "daemon":
        return daemon_mode(
            accepted_runner_modes=ACCEPTED_RUNNER_MODES,
            pid_file=PID_FILE,
            runner_name="codex_plan_runner",
        )
    if args.command == "run-once":
        assert target is not None
        return run_once_mode(target, accepted_runner_modes=ACCEPTED_RUNNER_MODES)
    if args.command == "status":
        assert target is not None
        return status_mode(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
