#!/usr/bin/env python3
"""Unified governance CLI - single entry point for all queue/system management tasks.

Usage:
  python3 governance_cli.py queue  status [--queue QUEUE] [--all] [--dry-run]
  python3 governance_cli.py queue  fix [--queue QUEUE] [--all] [--dry-run]
  python3 governance_cli.py queue  deps [--queue QUEUE] [--dry-run]
  python3 governance_cli.py queue  protect [--all] [--dry-run]
  python3 governance_cli.py health [--loop] [--interval SECONDS]
  python3 governance_cli.py runners [--restart] [--dry-run]
  python3 governance_cli.py task   reset --queue QUEUE --task-id TASK_ID [--dry-run]
  python3 governance_cli.py task   unhold --queue QUEUE [--dry-run]
  python3 governance_cli.py task   mark --queue QUEUE --task-id TASK_ID,... [--dry-run]
  python3 governance_cli.py task   remove --queue QUEUE --task-id TASK_ID [--dry-run]
  python3 governance_cli.py task   zombies [--queue QUEUE] [--fix] [--dry-run]
  python3 governance_cli.py repair deps --queue QUEUE [--dry-run]
  python3 governance_cli.py repair stale [--queue QUEUE] [--fix] [--dry-run]
  python3 governance_cli.py repair state --queue QUEUE [--dry-run]
  python3 governance_cli.py repair ghost --queue QUEUE [--dry-run]
  python3 governance_cli.py repair manifest --file PATH [--dry-run]
  python3 governance_cli.py repair gene-management [--dry-run]
  python3 governance_cli.py system full-check

Replaces: ~51 scattered fix_/monitor_/protect_/quick_/direct_/reset_/retry_ scripts.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from governance.repair_tools import RepairTools
from governance.task_orchestrator import TaskOrchestrator

from governance.queue_manager import QueueManager
from governance.system_health import QueueHealthMonitor, QueueProtector, SystemHealth


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


# ======================================================================
# Handlers
# ======================================================================


def cmd_queue_status(args: argparse.Namespace) -> int:
    qm = QueueManager()
    if args.queue:
        data = qm.load_queue(args.queue)
        if data is None:
            print(f"Queue not found: {args.queue}")
            return 1
        print(f"Queue: {data.get('queue_id')}  Status: {data.get('queue_status')}")
        print(f"Counts: {json.dumps(data.get('counts', {}), ensure_ascii=False)}")
        print(f"Current item: {data.get('current_item_id', '')}")
        print(f"Pause reason: {data.get('pause_reason', '')}")
    elif args.all:
        for qf in qm.list_queues():
            data = qm.load_queue(str(qf))
            if data:
                c = data.get("counts", {})
                st = data.get('queue_status', 'unknown') or 'unknown'
                print(f"{qf.stem}: {st:20s} P:{c.get('pending',0)} R:{c.get('running',0)} C:{c.get('completed',0)} F:{c.get('failed',0)} H:{c.get('manual_hold',0)}")
    else:
        _print_json(qm.list_queues())
    return 0


def cmd_queue_fix(args: argparse.Namespace) -> int:
    qm = QueueManager()
    if args.all:
        results = qm.fix_all_queues(dry_run=args.dry_run)
        _print_json(results)
    elif args.queue:
        result = qm.fix_queue_status(args.queue, dry_run=args.dry_run)
        _print_json(result)
    else:
        print("Use --queue QUEUE or --all")
        return 1
    return 0


def cmd_queue_deps(args: argparse.Namespace) -> int:
    qm = QueueManager()
    if not args.queue:
        print("--queue QUEUE is required")
        return 1
    result = qm.resolve_cross_queue_deps(args.queue, dry_run=args.dry_run)
    _print_json(result)
    return 0


def cmd_queue_protect(args: argparse.Namespace) -> int:
    qp = QueueProtector()
    result = qp.protect_all_queues(dry_run=args.dry_run)
    _print_json(result)
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    monitor = QueueHealthMonitor()
    if args.loop:
        monitor.monitor_loop(interval=args.interval or 60)
        return 0
    report = monitor.check(raise_alerts=True)
    _print_json(report)
    return 0


def cmd_runners(args: argparse.Namespace) -> int:
    qp = QueueProtector()
    if args.restart:
        result = qp.check_and_restart_runners()
    else:
        result = qp.check_runners()
    _print_json(result)
    return 0


def cmd_task_reset(args: argparse.Namespace) -> int:
    to = TaskOrchestrator()
    if not args.queue or not args.task_id:
        print("--queue QUEUE and --task-id TASK_ID are required")
        return 1
    result = to.reset_task(args.queue, args.task_id, dry_run=args.dry_run)
    _print_json(result)
    return 0


def cmd_task_unhold(args: argparse.Namespace) -> int:
    to = TaskOrchestrator()
    if not args.queue:
        print("--queue QUEUE is required")
        return 1
    result = to.reset_all_manual_hold(args.queue, dry_run=args.dry_run)
    _print_json(result)
    return 0


def cmd_task_mark(args: argparse.Namespace) -> int:
    to = TaskOrchestrator()
    if not args.queue or not args.task_id:
        print("--queue QUEUE and --task-id TASK_ID,... required")
        return 1
    task_ids = [t.strip() for t in args.task_id.split(",")]
    result = to.mark_tasks_completed(args.queue, task_ids, dry_run=args.dry_run)
    _print_json(result)
    return 0


def cmd_task_remove(args: argparse.Namespace) -> int:
    to = TaskOrchestrator()
    if not args.queue or not args.task_id:
        print("--queue QUEUE and --task-id TASK_ID required")
        return 1
    result = to.remove_task(args.queue, args.task_id, dry_run=args.dry_run)
    _print_json(result)
    return 0


def cmd_task_zombies(args: argparse.Namespace) -> int:
    to = TaskOrchestrator()
    if args.fix:
        result: dict | list = to.fix_zombie_tasks(args.queue, dry_run=args.dry_run)
    else:
        result = to.find_zombie_tasks(args.queue)
    _print_json(result)
    return 0


def cmd_repair_deps(args: argparse.Namespace) -> int:
    rt = RepairTools()
    if not args.queue:
        print("--queue QUEUE required")
        return 1
    result = rt.fix_dependency_blocks(args.queue, dry_run=args.dry_run)
    _print_json(result)
    return 0


def cmd_repair_stale(args: argparse.Namespace) -> int:
    rt = RepairTools()
    if args.fix:
        result: dict | list = rt.fix_stale_tasks(args.queue, dry_run=args.dry_run)
    else:
        result = rt.find_stale_tasks(args.queue)
    _print_json(result)
    return 0


def cmd_repair_state(args: argparse.Namespace) -> int:
    rt = RepairTools()
    if not args.queue:
        print("--queue QUEUE required")
        return 1
    result = rt.repair_state_file(args.queue, dry_run=args.dry_run)
    _print_json(result)
    return 0


def cmd_repair_ghost(args: argparse.Namespace) -> int:
    rt = RepairTools()
    if not args.queue:
        print("--queue QUEUE required")
        return 1
    result = rt.remove_ghost_dependencies(args.queue, dry_run=args.dry_run)
    _print_json(result)
    return 0


def cmd_repair_manifest(args: argparse.Namespace) -> int:
    rt = RepairTools()
    if not args.file:
        print("--file PATH required")
        return 1
    result = rt.fix_manifest_duplicates(args.file, dry_run=args.dry_run)
    _print_json(result)
    return 0


def cmd_repair_gene_management(args: argparse.Namespace) -> int:
    rt = RepairTools()
    result = rt.fix_gene_management_all_issues(dry_run=args.dry_run)
    _print_json(result)
    return 0


def cmd_system_full_check(args: argparse.Namespace) -> int:
    sh = SystemHealth()
    report = sh.full_check()
    _print_json(report)
    return 0


# ======================================================================
# CLI definition
# ======================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="governance_cli",
        description="Unified OpenClaw governance CLI for queue/system management.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- queue ----------------------------------------------------------
    qp = sub.add_parser("queue", help="Queue state operations")
    qs = qp.add_subparsers(dest="subcommand", required=True)

    _add = qs.add_parser("status", help="Show queue status")
    _add.add_argument("--queue")
    _add.add_argument("--all", action="store_true")
    _add.set_defaults(func=cmd_queue_status)

    _add = qs.add_parser("fix", help="Fix queue status")
    _add.add_argument("--queue")
    _add.add_argument("--all", action="store_true")
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_queue_fix)

    _add = qs.add_parser("deps", help="Resolve cross-queue dependencies")
    _add.add_argument("--queue", required=True)
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_queue_deps)

    _add = qs.add_parser("protect", help="Protect all queues from reset")
    _add.add_argument("--all", action="store_true")
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_queue_protect)

    # -- health ---------------------------------------------------------
    hp = sub.add_parser("health", help="Health monitoring")
    hp.add_argument("--loop", action="store_true", help="Continuous monitoring loop")
    hp.add_argument("--interval", type=int, default=60, help="Loop interval in seconds")
    hp.set_defaults(func=cmd_health)

    # -- runners --------------------------------------------------------
    rp = sub.add_parser("runners", help="Runner process management")
    rp.add_argument("--restart", action="store_true", help="Restart dead runners")
    rp.set_defaults(func=cmd_runners)

    # -- task -----------------------------------------------------------
    tp = sub.add_parser("task", help="Task lifecycle operations")
    ts = tp.add_subparsers(dest="subcommand", required=True)

    _add = ts.add_parser("reset", help="Reset a task to pending")
    _add.add_argument("--queue", required=True)
    _add.add_argument("--task-id", required=True)
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_task_reset)

    _add = ts.add_parser("unhold", help="Reset all manual_hold tasks to pending")
    _add.add_argument("--queue", required=True)
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_task_unhold)

    _add = ts.add_parser("mark", help="Mark task(s) as completed")
    _add.add_argument("--queue", required=True)
    _add.add_argument("--task-id", required=True, help="Comma-separated task IDs")
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_task_mark)

    _add = ts.add_parser("remove", help="Remove a task from the queue")
    _add.add_argument("--queue", required=True)
    _add.add_argument("--task-id", required=True)
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_task_remove)

    _add = ts.add_parser("zombies", help="Detect/fix zombie running tasks")
    _add.add_argument("--queue")
    _add.add_argument("--fix", action="store_true")
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_task_zombies)

    # -- repair ---------------------------------------------------------
    rp2 = sub.add_parser("repair", help="Repair operations")
    rs = rp2.add_subparsers(dest="subcommand", required=True)

    _add = rs.add_parser("deps", help="Fix dependency blocks")
    _add.add_argument("--queue", required=True)
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_repair_deps)

    _add = rs.add_parser("stale", help="Find/fix stale tasks")
    _add.add_argument("--queue")
    _add.add_argument("--fix", action="store_true")
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_repair_stale)

    _add = rs.add_parser("state", help="Repair queue state file structure")
    _add.add_argument("--queue", required=True)
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_repair_state)

    _add = rs.add_parser("ghost", help="Remove ghost dependency references")
    _add.add_argument("--queue", required=True)
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_repair_ghost)

    _add = rs.add_parser("manifest", help="Fix manifest duplicates")
    _add.add_argument("--file", required=True)
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_repair_manifest)

    _add = rs.add_parser("gene-management", help="Fix all gene management queue issues")
    _add.add_argument("--dry-run", action="store_true")
    _add.set_defaults(func=cmd_repair_gene_management)

    # -- system ---------------------------------------------------------
    sp = sub.add_parser("system", help="System-wide operations")
    ss = sp.add_subparsers(dest="subcommand", required=True)

    _add = ss.add_parser("full-check", help="Run all health checks")
    _add.set_defaults(func=cmd_system_full_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        return args.func(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
