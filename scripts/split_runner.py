#!/usr/bin/env python3
"""Split athena_ai_plan_runner.py into scripts/runner/ package modules.

Usage: python3 scripts/split_runner.py [--dry-run]
"""

import ast
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SOURCE_FILE = SCRIPTS_DIR / "athena_ai_plan_runner.py"
OUTPUT_DIR = SCRIPTS_DIR / "runner"

# ── Module definitions ────────────────────────────────────────────────

# Module-level code blocks (line ranges, 1-indexed) that should be extracted with the state module
STATE_MODULE_SECTIONS = [
    (66, 128, "# Event bus with fallback stubs"),
    (131, 148, "# State sync contract"),
    (151, 271, "# Parallel build gate with fallback stubs"),
    (274, 284, "# Performance metrics"),
]

MODULES = {
    "utils": {
        "functions": [
            "now_iso",
            "slugify",
            "clip",
            "read_json",
            "write_json",
            "extract_referenced_paths",
            "is_pid_alive",
            "terminate_process_tree",
            "terminate_pid_tree",
            "is_instruction_under_plan_dir",
            "system_free_memory_percent",
            "system_load_average",
            "ollama_active_cpu_percent",
            "extract_structured_result",
            "codex_executable",
            "resource_gate_message",
            "dynamic_build_worker_budget",
            "root_task_id_for",
        ],
        "needs_imports": [],  # pure leaf — no cross-module deps
    },
    "config": {
        "functions": [
            "load_plan_config",
            "load_control_plane_config",
            "archive_dir_from_config",
        ],
        "needs_imports": ["read_json"],
    },
    "trace": {
        "functions": [
            "create_task_workspace",
            "update_trace_event",
            "update_trace_status_change",
            "add_trace_artifact",
        ],
        "needs_imports": ["now_iso", "read_json", "write_json"],
    },
    "state": {
        "functions": [
            "emit_event",
            "record_performance_metric",
        ],
        "needs_imports": [],
        "module_sections": STATE_MODULE_SECTIONS,
    },
    "route_state": {
        "functions": [
            "route_runner_mode",
            "route_state_path",
            "route_state_lock_path",
            "_normalize_route_state",
            "load_route_state",
            "write_route_state",
            "route_current_item_ids",
            "mutate_route_state",
        ],
        "needs_imports": [
            "now_iso",
            "read_json",
            "write_json",
            # _normalize_route_state calls compute_route_counts_and_status (in manifest)
        ],
        "extra_imports": ["from .manifest import compute_route_counts_and_status"],
    },
    "manifest": {
        "functions": [
            "load_manifest_items",
            "manifest_item_depends_on",
            "materialize_route_items",
            "compute_route_counts_and_status",
            "update_manifest_instruction_path",
            "archive_instruction_path_if_needed",
            "upsert_manifest_item",
            "normalize_generated_queue_item",
            "upsert_route_state_item",
            "append_generated_queue_items",
            "find_manifest_item",
            "active_route_item_ids",
            "find_manifest_item_with_normalization",
            "route_index_by_item_id",
        ],
        "needs_imports": [
            "read_json",
            "write_json",
            "slugify",
            "now_iso",
        ],
        "extra_imports": [
            "from .config import load_plan_config",
            "from .route_state import route_state_path, load_route_state",
        ],
    },
    "task": {
        "functions": [
            "load_tasks_payload",
            "save_tasks_payload",
            "upsert_task_record",
            "set_task_status",
            "set_route_item_state",
            "add_route_current_item",
            "remove_route_current_item",
            "replace_route_current_items",
            "reset_failed_item_for_auto_retry",
        ],
        "needs_imports": [
            "now_iso",
            "read_json",
            "write_json",
            "clip",
        ],
        "extra_imports": [
            "from .state import record_performance_metric",
            "from .route_state import mutate_route_state",
            "from .utils import now_iso, read_json, write_json, clip",
        ],
    },
    "preflight": {
        "functions": [
            "common_preflight_warnings",
            "build_preflight_warnings",
            "review_preflight_warnings",
            "plan_preflight_warnings",
            "validate_build_preflight",
            "render_prompt",
            "render_review_prompt",
            "render_plan_prompt",
        ],
        "needs_imports": [
            "extract_referenced_paths",
            "load_control_plane_config",
            "codex_executable",
        ],
        "extra_imports": [
            "from .utils import extract_referenced_paths, codex_executable",
            "from .config import load_control_plane_config",
        ],
    },
    "failure": {
        "functions": [
            "failure_text",
            "retry_window_open",
            "is_retryable_failed_item",
            "is_blocked_rescue_retryable_failed_item",
            "failure_markdown",
            "success_markdown",
            "mark_stale_failed",
            "auto_retry_blocking_failures",
        ],
        "needs_imports": [
            "now_iso",
            "clip",
            "failure_text",
        ],
        "extra_imports": [
            "from .utils import now_iso, clip",
            "from .manifest import active_route_item_ids, load_manifest_items, route_index_by_item_id",
            "from .route_state import load_route_state",
            "from .config import load_plan_config",
            "from .task import set_task_status, set_route_item_state, remove_route_current_item, reset_failed_item_for_auto_retry",
            "from .route_state import route_matches_runner_modes",
        ],
    },
    "executor": {
        "functions": [
            "spawn_build_worker",
            "execute_build_item",
            "execute_review_item",
            "execute_plan_item",
            "execute_item",
            "append_to_daily_memory",
            "queue_route_by_mode",
            "detect_and_cleanup_stale_runs",
            "maybe_mark_restarted_runs_failed",
            "load_dependency_state_index",
            "route_matches_runner_modes",
            "choose_next_item",
            "finalize_completed_instruction",
            "archive_existing_completed_instructions",
        ],
        "needs_imports": [
            "now_iso",
            "clip",
            "slugify",
            "read_json",
            "write_json",
            "extract_structured_result",
            "codex_executable",
            "terminate_process_tree",
            "is_pid_alive",
            "resource_gate_message",
            "root_task_id_for",
        ],
        "extra_imports": [
            "from .utils import now_iso, clip, slugify, read_json, write_json, extract_structured_result, codex_executable, terminate_process_tree, is_pid_alive, resource_gate_message, root_task_id_for",
            "from .state import emit_event, record_performance_metric",
            "from .config import load_control_plane_config as _config_lcpc",
            "from .manifest import (",
            "    load_manifest_items, compute_route_counts_and_status,",
            "    update_manifest_instruction_path, archive_instruction_path_if_needed,",
            "    find_manifest_item, active_route_item_ids, append_generated_queue_items,",
            "    manifest_item_depends_on, materialize_route_items",
            ")",
            "from .route_state import (",
            "    route_runner_mode, load_route_state, write_route_state,",
            "    route_matches_runner_modes, add_route_current_item,",
            "    remove_route_current_item, set_route_item_state,",
            "    mutate_route_state, route_current_item_ids",
            ")",
            "from .task import load_tasks_payload, upsert_task_record, set_task_status",
            "from .preflight import (",
            "    common_preflight_warnings, build_preflight_warnings,",
            "    review_preflight_warnings, plan_preflight_warnings,",
            "    validate_build_preflight, render_prompt, render_review_prompt, render_plan_prompt",
            ")",
            "from .failure import failure_markdown, success_markdown, mark_stale_failed",
            "from .trace import create_task_workspace, update_trace_status_change, add_trace_artifact",
            "from .config import load_plan_config",
        ],
    },
}

# Entry-point functions that stay in the main file
MAIN_FILE_FUNCTIONS = {
    "handle_signal",
    "find_config_route",
    "main",
    "run_item_mode",
    "run_once_mode",
    "status_mode",
    "daemon_mode",
}


def get_function_ranges(source: str) -> dict[str, tuple[int, int]]:
    tree = ast.parse(source)
    source.split("\n")
    ranges = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno - 1
            end = node.end_lineno
            name = node.name
            for dec in node.decorator_list:
                dec_start = dec.lineno - 1
                if dec_start < start:
                    start = dec_start
            ranges[name] = (start, end)
    return ranges


def generate_module(
    mod_name: str, mod_info: dict, func_ranges: dict, source_lines: list[str]
) -> str | None:
    lines = []
    lines.append("#!/usr/bin/env python3")
    lines.append(f'"""{mod_info.get("description", mod_name)}"""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("import logging")
    lines.append("import os")
    lines.append("import sys")
    lines.append("import time")
    lines.append("from datetime import datetime, timezone")
    lines.append("from pathlib import Path")
    lines.append("from typing import Any")
    lines.append("")
    lines.append("")
    lines.append("logger = logging.getLogger(__name__)")
    lines.append("")

    # Add scripts dir to path
    lines.append("")
    lines.append("_scripts_dir = Path(__file__).resolve().parent.parent")
    lines.append("if str(_scripts_dir) not in sys.path:")
    lines.append("    sys.path.insert(0, str(_scripts_dir))")
    lines.append("")

    # Add openclaw_roots (needed by most functions)
    lines.append("try:")
    lines.append("    from .openclaw_roots import (")
    lines.append("        LOG_DIR,")
    lines.append("        PLAN_CONFIG_PATH,")
    lines.append("        PLAN_DIR,")
    lines.append("        QUEUE_STATE_DIR,")
    lines.append("        RUNTIME_ROOT,")
    lines.append("        TASKS_DIR,")
    lines.append("        TASKS_PATH,")
    lines.append("        pid_file,")
    lines.append("    )")
    lines.append("except ImportError:")
    lines.append("    import sys")
    lines.append("    from openclaw_roots import (")
    lines.append("        LOG_DIR,")
    lines.append("        PLAN_CONFIG_PATH,")
    lines.append("        PLAN_DIR,")
    lines.append("        QUEUE_STATE_DIR,")
    lines.append("        RUNTIME_ROOT,")
    lines.append("        TASKS_DIR,")
    lines.append("        TASKS_PATH,")
    lines.append("        pid_file,")
    lines.append("    )")
    lines.append("")

    # Add module-specific imports
    if mod_name != "state":
        pass  # extra imports handled below
    else:
        # resource_facts is needed by parallel gate stubs
        lines.append("try:")
        lines.append("    from . import system_resource_facts as resource_facts")
        lines.append("except ImportError:")
        lines.append("    import system_resource_facts as resource_facts")
        lines.append("")

    # Add cross-module imports
    extra = mod_info.get("extra_imports", [])
    if extra:
        for imp in extra:
            lines.append(imp)
        lines.append("")

    # Extract function code
    func_names = mod_info.get("functions", [])
    extracted = []
    for name in func_names:
        if name in func_ranges:
            start, end = func_ranges[name]
            code = "\n".join(source_lines[start:end])
            extracted.append(code)

    if not extracted:
        return None

    # For state module: include module-level sections
    if mod_name == "state":
        sections = mod_info.get("module_sections", [])
        lines.append("# ── Module-level stubs (event bus, parallel gate, state sync) ────────────")
        lines.append("")
        for sec_start, sec_end, comment in sections:
            lines.append(f"# {comment}")
            for ln in source_lines[sec_start - 1 : sec_end]:
                lines.append(ln)
            lines.append("")

    for func_code in extracted:
        lines.append(func_code)
        lines.append("")

    return "\n".join(lines)


def generate_main_file(source_lines: list[str], func_ranges: dict) -> str:
    lines = []
    lines.append("#!/usr/bin/env python3")
    lines.append('"""Minimal Athena AI plan queue runner.')
    lines.append("")
    lines.append("Consumes AI plan manifest items from the external knowledge-base queue config,")
    lines.append("executes build cards with OpenCode one at a time, and writes honest state back")
    lines.append(
        "to `.openclaw/plan_queue` plus task artifacts under `.openclaw/orchestrator/tasks`."
    )
    lines.append("")
    lines.append("Most implementation functions have been moved to the ``runner/`` package.")
    lines.append("This file serves as the entry point, re-exporting functions and running modes.")
    lines.append('"""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("import argparse")
    lines.append("import json")
    lines.append("import logging")
    lines.append("import os")
    lines.append("import signal")
    lines.append("import subprocess")
    lines.append("import sys")
    lines.append("import time")
    lines.append("from datetime import datetime, timezone")
    lines.append("from pathlib import Path")
    lines.append("from typing import Any")
    lines.append("")
    lines.append("")
    lines.append("logger = logging.getLogger(__name__)")
    lines.append("")
    lines.append("")
    lines.append("# ── Import root paths ──────────────────────────────────────────────")
    lines.append("try:")
    lines.append("    from .openclaw_roots import (")
    lines.append("        LOG_DIR,")
    lines.append("        PLAN_CONFIG_PATH,")
    lines.append("        PLAN_DIR,")
    lines.append("        QUEUE_STATE_DIR,")
    lines.append("        RUNTIME_ROOT,")
    lines.append("        TASKS_DIR,")
    lines.append("        TASKS_PATH,")
    lines.append("        pid_file,")
    lines.append("    )")
    lines.append("except ImportError:")
    lines.append("    scripts_dir = Path(__file__).resolve().parent")
    lines.append("    if str(scripts_dir) not in sys.path:")
    lines.append("        sys.path.insert(0, str(scripts_dir))")
    lines.append("    from openclaw_roots import (")
    lines.append("        LOG_DIR,")
    lines.append("        PLAN_CONFIG_PATH,")
    lines.append("        PLAN_DIR,")
    lines.append("        QUEUE_STATE_DIR,")
    lines.append("        RUNTIME_ROOT,")
    lines.append("        TASKS_DIR,")
    lines.append("        TASKS_PATH,")
    lines.append("        pid_file,")
    lines.append("    )")
    lines.append("")
    lines.append("")
    lines.append("# ── Import extracted modules from runner/ package ────────────────")
    for mod_name in sorted(MODULES.keys()):
        mod_info = MODULES[mod_name]
        func_names = mod_info["functions"]
        # Only import modules that have functions actually in source
        valid_funcs = [f for f in func_names if f in func_ranges]
        if valid_funcs:
            lines.append(f"from .runner.{mod_name} import (")
            for f in valid_funcs:
                lines.append(f"    {f},")
            lines.append(")")
    lines.append("")

    # Add remaining main entry functions
    lines.append("")
    lines.append("# ── Entry-point functions ────────────────────────────────────────")
    lines.append("")

    for name in [
        "handle_signal",
        "find_config_route",
        "main",
        "run_item_mode",
        "run_once_mode",
        "status_mode",
        "daemon_mode",
    ]:
        if name in func_ranges:
            start, end = func_ranges[name]
            code = "\n".join(source_lines[start:end])
            lines.append(code)
            lines.append("")

    return "\n".join(lines)


def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    print(f"Reading {SOURCE_FILE}...")
    source = SOURCE_FILE.read_text()
    source_lines = source.split("\n")
    print(f"  Total lines: {len(source_lines)}")

    print("\nAnalyzing function ranges...")
    func_ranges = get_function_ranges(source)
    print(f"  Found {len(func_ranges)} functions")

    # Validate function coverage
    assigned = set()
    for mod_name, mod_info in MODULES.items():
        for func_name in mod_info["functions"]:
            if func_name in func_ranges:
                assigned.add(func_name)

    unassigned = set(func_ranges.keys()) - assigned - MAIN_FILE_FUNCTIONS
    if unassigned:
        print(f"\n  WARNING: {len(unassigned)} functions unassigned:")
        for name in sorted(unassigned):
            print(f"    - {name}")

    # Generate module files
    if not dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        init_path = OUTPUT_DIR / "__init__.py"
        if not init_path.exists() or force:
            init_path.write_text('"""runner package — split from athena_ai_plan_runner.py"""\n')
            print(f"\n  Created {init_path}")

    print("\nGenerating modules:")
    total_moved = 0
    for mod_name in sorted(MODULES.keys()):
        mod_info = MODULES[mod_name]
        content = generate_module(mod_name, mod_info, func_ranges, source_lines)
        if not content:
            print(f"  SKIP {mod_name}: no functions found")
            continue

        out_path = OUTPUT_DIR / f"{mod_name}.py"
        if dry_run:
            lc = len(content.split("\n"))
            print(f"  [DRY-RUN] {out_path.name} ({lc} lines)")
        else:
            out_path.write_text(content)
            lc = len(content.split("\n"))
            print(f"  Wrote {out_path.name} ({lc} lines)")
            total_moved += lc

    # Generate updated main file
    print("\nGenerating updated entry point...")
    main_content = generate_main_file(source_lines, func_ranges)
    out_path = SCRIPTS_DIR / "athena_ai_plan_runner.py"
    if dry_run:
        print(
            f"  [DRY-RUN] Updated main file: {len(source_lines)} -> {len(main_content.split(chr(10)))} lines"
        )
    else:
        out_path.write_text(main_content)
        print(
            f"  Wrote updated {out_path.name} ({len(main_content.split(chr(10)))} lines, was {len(source_lines)})"
        )

    print(f"\nDone. Moved {total_moved} lines into {len(MODULES)} modules.")


if __name__ == "__main__":
    main()
