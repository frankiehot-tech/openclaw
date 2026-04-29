#!/usr/bin/env python3
"""Minimal Athena AI plan queue runner.

Consumes AI plan manifest items from the external knowledge-base queue config,
executes build cards with OpenCode one at a time, and writes honest state back
to `.openclaw/plan_queue` plus task artifacts under `.openclaw/orchestrator/tasks`.

Most implementation functions have been moved to the ``runner/`` package.
This file serves as the entry point, re-exporting functions and running modes.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ── Import root paths ──────────────────────────────────────────────
try:
    from .openclaw_roots import (
        LOG_DIR,
        PLAN_CONFIG_PATH,
        QUEUE_STATE_DIR,
        TASKS_DIR,
        pid_file,
    )
except ImportError:
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from openclaw_roots import (
        LOG_DIR,
        PLAN_CONFIG_PATH,
        QUEUE_STATE_DIR,
        TASKS_DIR,
        pid_file,
    )

PID_FILE = pid_file("athena_ai_plan_runner")


# ── Import extracted modules from runner/ package ────────────────
import contextlib

from .runner.config import (
    HEARTBEAT_TIMEOUT_SECONDS,
    POLL_SECONDS,
    load_plan_config,
)
from .runner.executor import (
    archive_existing_completed_instructions,
    choose_next_item,
    detect_and_cleanup_stale_runs,
    execute_item,
    maybe_mark_restarted_runs_failed,
    route_matches_runner_modes,
    spawn_build_worker,
)
from .runner.failure import (
    auto_retry_blocking_failures,
    mark_stale_failed,
)
from .runner.manifest import (
    active_route_item_ids,
    find_manifest_item_with_normalization,
    load_manifest_items,
)
from .runner.route_state import (
    load_route_state,
    route_runner_mode,
    route_state_path,
    write_route_state,
)
from .runner.state import (
    PARALLEL_BUILD_GATE_AVAILABLE,
    get_global_gate,
    record_performance_metric,
)
from .runner.task import (
    remove_route_current_item,
)

# ── Entry-point functions ────────────────────────────────────────


def handle_signal(signum: int, _frame: Any) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True
    print(f"[athena_ai_plan_runner] received signal {signum}, stopping...", flush=True)


def find_config_route(target: str) -> dict[str, Any] | None:
    config = load_plan_config()
    routes = config.get("routes", [])
    target_path = Path(target).resolve() if Path(target).exists() else None
    for route in routes:
        if str(route.get("queue_id", "") or "") == target:
            return route
        if str(route.get("route_id", "") or "") == target:
            return route
        if target_path is not None:
            try:
                if route_state_path(route).resolve() == target_path:
                    return route
            except Exception:
                continue
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Athena AI plan queue runner")
    parser.add_argument(
        "command",
        nargs="?",
        default="daemon",
        choices=["daemon", "run-once", "run-item", "status"],
        help="Command to execute: daemon (default), run-once, run-item, status",
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="For run-once/run-item/status: path to queue state file or route ID",
    )
    parser.add_argument(
        "item_id",
        nargs="?",
        help="For run-item: explicit queue item ID to execute",
    )
    parser.add_argument(
        "--queue-id",
        help="Queue ID to operate on (if target not provided)",
    )
    args = parser.parse_args()

    # TaskIdentityContract集成 - 解决ID以'-'开头被argparse误识别问题
    # 深度审计发现：13个以'-'开头的任务ID（占6.74%）会导致argparse解析失败
    if args.item_id and (args.item_id.startswith("-") or args.item_id.startswith("+")):
        try:
            # 动态导入TaskIdentityContract，避免循环依赖
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from contracts.task_identity import TaskIdentity

            # 规范化ID：移除开头的'-'或'+'，确保argparse安全
            normalized = TaskIdentity.normalize(args.item_id)
            print(
                f"⚠️  警告: 检测到问题ID '{args.item_id}'，已规范化为: {normalized.id}",
                file=sys.stderr,
            )
            print(f"   原始ID: {normalized.original_id}", file=sys.stderr)
            print(f"   argparse安全: {normalized.is_argparse_safe()}", file=sys.stderr)
            args.item_id = normalized.id
        except Exception as e:
            print(f"⚠️  TaskIdentityContract规范化失败: {e}", file=sys.stderr)
            print("⚠️  使用快速修复: 添加'task_'前缀", file=sys.stderr)
            # 快速回退修复
            if args.item_id.startswith("-") or args.item_id.startswith("+"):
                args.item_id = "task_" + args.item_id[1:]

    if args.command in ("run-once", "run-item", "status") and not args.target and not args.queue_id:
        print(
            "Error: run-once, run-item and status require a target queue state file or --queue-id",
            file=sys.stderr,
        )
        return 1

    if args.command == "daemon":
        return daemon_mode()
    elif args.command == "run-once":
        return run_once_mode(args.target or args.queue_id)
    elif args.command == "run-item":
        if not args.item_id:
            print("Error: run-item requires an explicit item_id", file=sys.stderr)
            return 1
        return run_item_mode(args.target or args.queue_id, args.item_id)
    elif args.command == "status":
        return status_mode(args.target or args.queue_id)
    else:
        return 0


def run_item_mode(
    target: str,
    item_id: str,
    accepted_runner_modes: set[str] | tuple[str, ...] | None = None,
) -> int:
    route = find_config_route(target)
    if route is None:
        print(f"Error: queue route not found for target: {target}", file=sys.stderr)
        return 1
    if not route_matches_runner_modes(route, accepted_runner_modes):
        print(
            f"Queue {target} 不属于当前 runner 负责的模式 {sorted(set(accepted_runner_modes or {'opencode_build'}))}",
            file=sys.stderr,
        )
        return 1
    item = find_manifest_item_with_normalization(route, item_id)
    if not item:
        print(f"Error: item not found in manifest: {item_id}", file=sys.stderr)
        print("⚠️  尝试了规范化匹配但未找到对应条目，请检查ID格式", file=sys.stderr)
        # 列出前5个可用ID供用户参考
        try:
            manifest_items = load_manifest_items(route)
            print("⚠️  可用的manifest条目ID (前5个):", file=sys.stderr)
            for manifest_item in manifest_items[:5]:
                manifest_id = str(manifest_item.get("id", "") or "")
                if manifest_id:
                    print(f"    - {manifest_id}", file=sys.stderr)
        except Exception:
            pass
        return 1
    execute_item(route, item)
    return 0


def run_once_mode(
    target: str, accepted_runner_modes: set[str] | tuple[str, ...] | None = None
) -> int:
    """Execute the current item of a queue once, wait for completion, then exit."""
    route = find_config_route(target)
    if route is None:
        if Path(target).exists():
            queue_state_path = Path(target)
            route = {
                "queue_id": queue_state_path.stem,
                "queue_state_path": str(queue_state_path),
            }
        else:
            queue_state_path = QUEUE_STATE_DIR / f"{target}.json"
            if not queue_state_path.exists():
                print(
                    f"Error: Queue state file not found: {queue_state_path}",
                    file=sys.stderr,
                )
                return 1
            route = {"queue_id": target}
    if not route_matches_runner_modes(route, accepted_runner_modes):
        print(
            f"Queue {target} 不属于当前 runner 负责的模式 {sorted(set(accepted_runner_modes or {'opencode_build'}))}",
            file=sys.stderr,
        )
        return 1

    route_state = load_route_state(route)

    # First, cleanup any stale runs in this specific route. Reload the state
    # afterwards so we do not keep making scheduling decisions from a stale
    # in-memory snapshot that still contains the just-cleaned running item.
    detect_and_cleanup_stale_runs([route])
    route_state = load_route_state(route)

    # Ensure we have a current item
    current_item_ids = active_route_item_ids(route_state)
    if not current_item_ids:
        # No current item, try to choose next
        item = choose_next_item(route, route_state, accepted_runner_modes)
        if not item:
            print("No pending items in this queue.", file=sys.stderr)
            return 0
        # Start execution of this item
        execute_item(route, item)
        return 0
    else:
        # There is already a running item; check if it's still alive via heartbeat
        current_item_id = current_item_ids[0]
        state_item = (route_state.get("items") or {}).get(current_item_id) or {}
        status = str(state_item.get("status", ""))
        if status != "running":
            # Should not happen, but just in case
            print(
                f"Current item status is {status}, not running. Proceeding.",
                file=sys.stderr,
            )
            # Clear current item and retry
            remove_route_current_item(route, current_item_id)
            route_state = load_route_state(route)
            # Try to choose next item
            item = choose_next_item(route, route_state, accepted_runner_modes)
            if item:
                execute_item(route, item)
            return 0

        # Check heartbeat staleness
        runner_heartbeat_at = state_item.get("runner_heartbeat_at")
        if runner_heartbeat_at:
            try:
                heartbeat_time = datetime.fromisoformat(runner_heartbeat_at.replace("Z", "+00:00"))
                if heartbeat_time.tzinfo is None:
                    heartbeat_time = heartbeat_time.replace(tzinfo=UTC)
                now = datetime.now(UTC)
                delta = (now - heartbeat_time).total_seconds()
                if delta > HEARTBEAT_TIMEOUT_SECONDS:
                    print(
                        f"Current running item is stale (heartbeat {int(delta)}s old). Marking failed.",
                        file=sys.stderr,
                    )
                    mark_stale_failed(
                        route,
                        route_state,
                        current_item_id,
                        state_item,
                        f"heartbeat missing for {int(delta)}s",
                    )
                    # After marking failed, choose next item
                    route_state = load_route_state(route)
                    item = choose_next_item(route, route_state, accepted_runner_modes)
                    if item:
                        execute_item(route, item)
                    return 0
            except Exception:
                pass

        # The item is still considered running with recent heartbeat.
        # We could wait for it to finish, but run-once is meant to push one item to completion.
        # Since there is already an active runner (maybe another process), we should not interfere.
        print(
            f"Queue already has a running item with recent heartbeat: {current_item_id}",
            file=sys.stderr,
        )
        print(
            "If this is stuck, use status command to inspect or wait for heartbeat timeout.",
            file=sys.stderr,
        )
        return 1


def status_mode(target: str) -> int:
    """Show current status of a queue."""
    route = find_config_route(target)
    if route is None and Path(target).exists():
        queue_state_path = Path(target)
        # Check if the file is a manifest (has 'items' list) rather than a queue state
        try:
            content = json.loads(queue_state_path.read_text(encoding="utf-8"))
            if (
                isinstance(content, dict)
                and isinstance(content.get("items"), list)
                and "queue_id" not in content
            ):
                print(
                    "Error: The file appears to be a manifest (contains 'items' list), not a queue state file.",
                    file=sys.stderr,
                )
                print(
                    f"Hint: Use the manifest path with the queue runner's daemon mode, or provide a queue state file from {QUEUE_STATE_DIR}.",
                    file=sys.stderr,
                )
                return 1
        except Exception:
            pass  # Not valid JSON or other issue, proceed as queue state
        route = {
            "queue_id": queue_state_path.stem,
            "queue_state_path": str(queue_state_path),
        }
    elif route is None:
        queue_state_path = QUEUE_STATE_DIR / f"{target}.json"
        if not queue_state_path.exists():
            print(
                f"Error: Queue state file not found: {queue_state_path}",
                file=sys.stderr,
            )
            return 1
        route = {"queue_id": target}

    route_state = load_route_state(route)
    print(json.dumps(route_state, ensure_ascii=False, indent=2))
    return 0


def daemon_mode(
    *,
    accepted_runner_modes: set[str] | tuple[str, ...] | None = None,
    pid_file: Path = PID_FILE,
    runner_name: str = "athena_ai_plan_runner",
) -> int:
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_STATE_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    config = load_plan_config()
    routes = [
        route
        for route in config.get("routes", [])
        if route_matches_runner_modes(route, accepted_runner_modes)
    ]
    maybe_mark_restarted_runs_failed(routes)
    detect_and_cleanup_stale_runs(routes)
    for route in routes:
        write_route_state(route, load_route_state(route))
    print(
        f"[{runner_name}] watching {len(routes)} routes from {PLAN_CONFIG_PATH}",
        flush=True,
    )

    while not STOP_REQUESTED:
        did_work = False
        config = load_plan_config()
        routes = [
            route
            for route in config.get("routes", [])
            if route_matches_runner_modes(route, accepted_runner_modes)
        ]
        maybe_mark_restarted_runs_failed(routes)
        detect_and_cleanup_stale_runs(routes)
        for route in routes:
            route_state = load_route_state(route)
            write_route_state(route, route_state)
            # Record queue length metric
            try:
                queue_id = route.get("queue_id") or route.get("route_id") or "unknown"
                pending_items = 0
                if isinstance(route_state, dict):
                    items = route_state.get("items", [])
                    pending_items = len([item for item in items if item.get("status") == "pending"])
                record_performance_metric(
                    dimension="QUEUE_LENGTH",
                    value=pending_items,
                    labels={"queue_id": queue_id},
                )
            except Exception:
                pass  # Silently ignore metric recording errors
        archived = archive_existing_completed_instructions(routes)
        if archived:
            did_work = True
        retried = auto_retry_blocking_failures(routes, accepted_runner_modes=accepted_runner_modes)
        if retried:
            did_work = True
        build_routes = [route for route in routes if route_runner_mode(route) == "opencode_build"]
        active_build_workers = sum(
            len(active_route_item_ids(load_route_state(route))) for route in build_routes
        )
        # 使用并行构建门控获取准入决策
        gate = get_global_gate()
        admission_result = gate.check_admission()
        allowed_workers = admission_result.allowed_workers
        build_telemetry = admission_result.metadata.get("telemetry", {})

        # 记录调度摘要（用于调试）
        if PARALLEL_BUILD_GATE_AVAILABLE:
            try:
                gate.generate_scheduling_summary()
                # 每10次迭代记录一次详细摘要
                if not hasattr(daemon_mode, "_summary_counter"):
                    daemon_mode._summary_counter = 0
                daemon_mode._summary_counter += 1
                if daemon_mode._summary_counter % 10 == 0:
                    print(
                        f"[parallel-build-gate] decision={admission_result.decision.value}, "
                        f"allowed={allowed_workers}, active={active_build_workers}, "
                        f"reason={admission_result.reason}",
                        flush=True,
                    )
                    # 记录完整摘要到日志文件
                    log_path = LOG_DIR / "parallel_build_gate_summary.log"
                    with log_path.open("a", encoding="utf-8") as f:
                        import json

                        f.write(
                            json.dumps(
                                {
                                    "timestamp": time.time(),
                                    "decision": admission_result.decision.value,
                                    "allowed_workers": admission_result.allowed_workers,
                                    "active_build_workers": active_build_workers,
                                    "reason": admission_result.reason,
                                    "resource_checks": [
                                        {
                                            "dimension": check.dimension.value,
                                            "value": check.value,
                                            "threshold": check.threshold,
                                            "passed": check.passed,
                                            "reason": check.reason,
                                        }
                                        for check in admission_result.resource_checks
                                    ],
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
            except Exception:
                pass  # 忽略日志错误

        for route in routes:
            route_state = load_route_state(route)
            runner_mode = route_runner_mode(route)

            if runner_mode == "opencode_build":
                while active_build_workers < allowed_workers:
                    item = choose_next_item(route, route_state, accepted_runner_modes)
                    if not item:
                        break
                    spawn_build_worker(route, item, build_telemetry)
                    did_work = True
                    active_build_workers += 1
                    route_state = load_route_state(route)
                    if STOP_REQUESTED:
                        break
                if STOP_REQUESTED:
                    break
                continue

            if active_route_item_ids(route_state):
                continue
            item = choose_next_item(route, route_state, accepted_runner_modes)
            if not item:
                continue
            execute_item(route, item)
            did_work = True
            if STOP_REQUESTED:
                break
        if STOP_REQUESTED:
            break
        if not did_work:
            time.sleep(POLL_SECONDS)
    with contextlib.suppress(FileNotFoundError):
        pid_file.unlink()
    return 0
