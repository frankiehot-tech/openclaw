#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""Add missing cross-module imports to runner module files."""

from pathlib import Path

RUNNER_DIR = Path(__file__).resolve().parent / "runner"

# Each module: list of import lines to add (after openclaw_roots import)
EXTRA_IMPORTS = {
    "config.py": [
        "from .utils import read_json",
    ],
    "route_state.py": [
        "from .utils import now_iso, read_json, write_json",
    ],
    "trace.py": [
        "from .utils import now_iso, read_json, write_json",
    ],
    "manifest.py": [
        "from .utils import read_json, write_json, slugify, now_iso",
        "from .route_state import route_current_item_ids",
    ],
    "task.py": [
        "from .utils import now_iso, read_json, write_json, clip",
        "from .route_state import mutate_route_state, route_current_item_ids",
        "from .state import record_performance_metric",
        "from .route_state import load_route_state",
        "from .failure import failure_text",
    ],
    "failure.py": [
        "from .utils import now_iso, clip",
    ],
    "executor.py": [
        "from .utils import now_iso, clip, slugify, read_json, write_json, extract_structured_result, codex_executable, terminate_process_tree, is_pid_alive, resource_gate_message, root_task_id_for",
        "from .state import emit_event, record_performance_metric",
        "from .manifest import load_manifest_items, compute_route_counts_and_status, update_manifest_instruction_path, archive_instruction_path_if_needed, find_manifest_item, active_route_item_ids, append_generated_queue_items, manifest_item_depends_on, materialize_route_items",
        "from .route_state import route_runner_mode, load_route_state, write_route_state, route_matches_runner_modes, add_route_current_item, remove_route_current_item, mutate_route_state, route_current_item_ids",
        "from .task import load_tasks_payload, upsert_task_record, set_task_status, set_route_item_state",
        "from .preflight import common_preflight_warnings, build_preflight_warnings, review_preflight_warnings, plan_preflight_warnings, validate_build_preflight, render_prompt, render_review_prompt, render_plan_prompt",
        "from .failure import failure_markdown, success_markdown, mark_stale_failed",
        "from .trace import create_task_workspace, update_trace_status_change, add_trace_artifact",
        "from .config import load_plan_config",
    ],
}

# Fix executor.py — it already has imports but they're in a different format
# Let me check and replace/add
EXECUTOR_REPLACE_IMPORTS = True


def add_imports_after_block(
    filepath: Path, import_lines: list[str], marker: str = "from openclaw_roots import"
):
    """Add import lines after the openclaw_roots import block."""
    content = filepath.read_text()
    lines = content.split("\n")

    # Find the end of the openclaw_roots import block
    # Look for lines that start with `from .openclaw_roots import` or `from openclaw_roots import`
    # and find the closing `)` with the blank line after
    import_end = -1
    for i, line in enumerate(lines):
        if "from openclaw_roots import" in line or marker in line:
            # Walk forward to find the closing ) of the import block
            for j in range(i, len(lines)):
                if lines[j].rstrip().endswith(")"):
                    import_end = j + 1  # after the closing paren
                    break
            break

    if import_end < 0:
        print(f"  WARNING: could not find import block end in {filepath.name}")
        return

    # Check if these imports already exist
    existing = set(lines)
    new_imports = [l for l in import_lines if l not in existing]

    if not new_imports:
        print(f"  OK: {filepath.name} (all imports already present)")
        return

    # Insert after the import block (after the blank line following the closing paren)
    insert_pos = import_end
    while insert_pos < len(lines) and lines[insert_pos].strip() == "":
        insert_pos += 1

    # Add a blank line then the imports
    for imp in reversed(new_imports):
        lines.insert(insert_pos, "")
        lines.insert(insert_pos, imp)

    # Remove duplicate blank lines
    cleaned = []
    prev_blank = False
    for line in lines:
        if line.strip() == "":
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False
        cleaned.append(line)

    filepath.write_text("\n".join(cleaned))
    print(f"  FIXED: {filepath.name} (+{len(new_imports)} import lines)")


def fix_executor_imports(filepath: Path):
    """Replace the executor.py import block with the correct one."""
    content = filepath.read_text()
    lines = content.split("\n")

    # Find and replace the old import block
    # Current executor imports (from generate) have lines like:
    # from .route_state import (
    #     route_runner_mode, load_route_state, ...
    # )
    # But they also have old-style imports that need replacement

    # Replace the entire import block after openclaw_roots
    new_block = """from .utils import now_iso, clip, slugify, read_json, write_json, extract_structured_result, codex_executable, terminate_process_tree, is_pid_alive, resource_gate_message, root_task_id_for
from .state import emit_event, record_performance_metric
from .manifest import load_manifest_items, compute_route_counts_and_status, update_manifest_instruction_path, archive_instruction_path_if_needed, find_manifest_item, active_route_item_ids, append_generated_queue_items, manifest_item_depends_on, materialize_route_items
from .route_state import route_runner_mode, load_route_state, write_route_state, route_matches_runner_modes, add_route_current_item, remove_route_current_item, mutate_route_state, route_current_item_ids
from .task import load_tasks_payload, upsert_task_record, set_task_status, set_route_item_state
from .preflight import common_preflight_warnings, build_preflight_warnings, review_preflight_warnings, plan_preflight_warnings, validate_build_preflight, render_prompt, render_review_prompt, render_plan_prompt
from .failure import failure_markdown, success_markdown, mark_stale_failed
from .trace import create_task_workspace, update_trace_status_change, add_trace_artifact
from .config import load_plan_config"""

    # Find the import block to replace
    # It starts after the openclaw_roots block and ends before the first function def
    # Find openclaw_roots closing paren
    openclaw_end = -1
    for i, line in enumerate(lines):
        if "openclaw_roots import" in line:
            for j in range(i, len(lines)):
                if lines[j].rstrip().endswith(")"):
                    openclaw_end = j
                    break
            break

    if openclaw_end < 0:
        print("  WARNING: could not find openclaw_roots import end in executor.py")
        return

    # Find first function definition after the openclaw_roots block
    first_func = -1
    for i in range(openclaw_end + 1, len(lines)):
        if lines[i].startswith("def ") or lines[i].startswith("async def "):
            first_func = i
            break

    if first_func < 0:
        print("  WARNING: could not find first function in executor.py")
        return

    # Replace everything between openclaw_roots end and first function with new imports
    new_lines = lines[: openclaw_end + 1]
    new_lines.append("")
    for imp_line in new_block.split("\n"):
        new_lines.append(imp_line)
    new_lines.append("")
    new_lines.extend(lines[first_func:])

    # Remove duplicate blank lines
    cleaned = []
    prev_blank = False
    for line in new_lines:
        if line.strip() == "":
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False
        cleaned.append(line)

    filepath.write_text("\n".join(cleaned))
    print("  REPLACED: executor.py import block")


for f in sorted(RUNNER_DIR.glob("*.py")):
    if f.name == "__init__.py":
        continue

    if f.name == "executor.py":
        fix_executor_imports(f)
    elif f.name in EXTRA_IMPORTS:
        add_imports_after_block(f, EXTRA_IMPORTS[f.name])
    else:
        print(f"  OK: {f.name} (no extra imports needed)")
