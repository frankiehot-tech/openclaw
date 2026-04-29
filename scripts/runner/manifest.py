#!/usr/bin/env python3
"""manifest"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_scripts_dir = Path(__file__).resolve().parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

try:
    pass
except ImportError:
    import sys

import contextlib

from .config import AUTO_ARCHIVE_COMPLETED, archive_dir_from_config, load_plan_config

# queue_route_by_mode imported lazily inside append_generated_queue_items to avoid circular deps
from .route_state import load_route_state, route_current_item_ids, route_state_path
from .utils import (
    is_instruction_under_plan_dir,
    is_pid_alive,
    now_iso,
    read_json,
    slugify,
    write_json,
)


def load_manifest_items(route: dict[str, Any]) -> list[dict[str, Any]]:
    manifest_path = Path(str(route.get("manifest_path", "") or ""))
    manifest = read_json(manifest_path, default={"items": []}) or {"items": []}
    items = manifest.get("items")
    return items if isinstance(items, list) else []


def manifest_item_depends_on(manifest_item: dict[str, Any]) -> list[str]:
    metadata = (
        manifest_item.get("metadata") if isinstance(manifest_item.get("metadata"), dict) else {}
    )
    depends_on = metadata.get("depends_on")
    if not isinstance(depends_on, list):
        return []
    return [str(dep_id) for dep_id in depends_on if str(dep_id or "").strip()]


def materialize_route_items(
    route: dict[str, Any], route_state: dict[str, Any]
) -> list[dict[str, Any]]:
    items_state = route_state.get("items") or {}
    manifest_items = load_manifest_items(route)
    materialized: list[dict[str, Any]] = []
    for manifest_item in manifest_items:
        item_id = str(manifest_item.get("id", "") or "")
        title = str(manifest_item.get("title", item_id) or item_id)
        stage = str(manifest_item.get("entry_stage", "build") or "build")
        instruction_path = str(manifest_item.get("instruction_path", "") or "")
        metadata = (
            manifest_item.get("metadata") if isinstance(manifest_item.get("metadata"), dict) else {}
        )
        state_item = items_state.get(item_id)
        state_item = state_item if isinstance(state_item, dict) else {}
        status = str(state_item.get("status", "") or "pending")
        manual_override_autostart = bool(state_item.get("manual_override_autostart"))
        if (
            metadata.get("autostart") is False
            and status in {"", "pending"}
            and not manual_override_autostart
        ):
            status = "manual_hold"
        materialized.append(
            {
                "id": item_id,
                "title": title,
                "entry_stage": stage,
                "instruction_path": instruction_path,
                "status": status,
                "depends_on": manifest_item_depends_on(manifest_item),
                "runner_pid": state_item.get("runner_pid"),
            }
        )
    return materialized


def compute_route_counts_and_status(
    route: dict[str, Any], route_state: dict[str, Any]
) -> tuple[dict[str, int], str]:
    items = materialize_route_items(route, route_state)
    counts = {
        "pending": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "manual_hold": 0,
    }
    for item in items:
        status = str(item.get("status", "") or "pending")
        counts[status] = counts.get(status, 0) + 1

    pending_items = [item for item in items if item.get("status") == "pending"]
    running_items = [item for item in items if item.get("status") == "running"]
    manual_hold_items = [item for item in items if item.get("status") == "manual_hold"]

    if not pending_items and not running_items:
        return counts, "manual_hold" if manual_hold_items else "empty"

    if any(is_pid_alive(item.get("runner_pid")) for item in running_items):
        return counts, "running"

    item_by_id = {str(item.get("id", "")): item for item in items}
    blocked = False
    for item in pending_items:
        for dep_id in item.get("depends_on", []):
            dep_item = item_by_id.get(str(dep_id))
            if not dep_item or dep_item.get("status") != "completed":
                blocked = True
                break
        if blocked:
            break

    if blocked:
        return counts, "dependency_blocked"
    if pending_items:
        return counts, "no_consumer"
    return counts, "empty"


def update_manifest_instruction_path(
    route: dict[str, Any], item_id: str, instruction_path: str
) -> None:
    manifest_path = Path(str(route.get("manifest_path", "") or ""))
    payload = read_json(manifest_path, default=None)
    if not isinstance(payload, dict):
        return
    items = payload.get("items")
    if not isinstance(items, list):
        return
    changed = False
    for manifest_item in items:
        if str(manifest_item.get("id", "") or "") != item_id:
            continue
        if str(manifest_item.get("instruction_path", "") or "") == instruction_path:
            return
        manifest_item["instruction_path"] = instruction_path
        changed = True
        break
    if changed:
        write_json(manifest_path, payload)


def archive_instruction_path_if_needed(instruction_path: str) -> str:
    if not AUTO_ARCHIVE_COMPLETED or not instruction_path:
        return instruction_path
    path = Path(instruction_path)
    if not path.exists():
        return instruction_path
    archive_dir = archive_dir_from_config()
    if archive_dir is None or not is_instruction_under_plan_dir(path):
        return instruction_path
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / path.name
    try:
        if path.resolve() == target.resolve():
            return str(target)
    except FileNotFoundError:
        return instruction_path

    if target.exists():
        try:
            source_text = path.read_text(encoding="utf-8")
            if target.read_text(encoding="utf-8") != source_text:
                target.write_text(source_text, encoding="utf-8")
        except Exception:
            shutil.copy2(path, target)
        with contextlib.suppress(Exception):
            path.unlink()
    else:
        shutil.move(str(path), str(target))
    return str(target)


def upsert_manifest_item(manifest_path: Path, manifest_item: dict[str, Any]) -> None:
    manifest = read_json(manifest_path, default={"items": []}) or {"items": []}
    items = manifest.get("items")
    if not isinstance(items, list):
        items = []
    item_id = str(manifest_item.get("id", "") or "")
    replaced = False
    for idx, existing in enumerate(items):
        if str(existing.get("id", "") or "") == item_id:
            items[idx] = manifest_item
            replaced = True
            break
    if not replaced:
        items.append(manifest_item)
    manifest["items"] = items
    write_json(manifest_path, manifest)


def normalize_generated_queue_item(raw_item: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw_item, dict):
        return None
    title = str(raw_item.get("title", "") or "").strip()
    instruction_path = str(raw_item.get("instruction_path", "") or "").strip()
    entry_stage = str(raw_item.get("entry_stage", "") or "build").strip().lower()
    if not title or not instruction_path or entry_stage not in {"build", "review"}:
        return None
    lane_default = "build_auto" if entry_stage == "build" else "review_auto"
    item_id = str(raw_item.get("id", "") or "").strip() or slugify(title).replace("-", "_")
    return {
        "id": item_id,
        "title": title,
        "instruction_path": instruction_path,
        "entry_stage": entry_stage,
        "risk_level": str(raw_item.get("risk_level", "") or "medium"),
        "unattended_allowed": bool(raw_item.get("autostart", True)),
        "targets": [],
        "metadata": {
            "priority": str(
                raw_item.get("priority", "") or ("P2" if entry_stage == "build" else "R2")
            ),
            "lane": str(raw_item.get("lane", "") or lane_default),
            "epic": str(raw_item.get("epic", "") or "generated_plan"),
            "category": str(raw_item.get("category", "") or "generated"),
            "rationale": str(
                raw_item.get("rationale", "") or "由 codex_plan_runner 从策划文档自动拆出。"
            ),
            "depends_on": [
                str(dep).strip() for dep in (raw_item.get("depends_on") or []) if str(dep).strip()
            ],
            "autostart": bool(raw_item.get("autostart", True)),
            "generated_by": "codex_plan_runner",
        },
    }


def upsert_route_state_item(
    route: dict[str, Any], manifest_item: dict[str, Any], summary: str
) -> None:
    route_state = load_route_state(route)
    item_id = str(manifest_item.get("id", "") or "")
    state_item = dict((route_state.get("items") or {}).get(item_id, {}))
    state_item.update(
        {
            "title": str(manifest_item.get("title", item_id) or item_id),
            "stage": str(manifest_item.get("entry_stage", "build") or "build"),
            "instruction_path": str(manifest_item.get("instruction_path", "") or ""),
            "status": str(state_item.get("status", "") or "pending"),
            "progress_percent": int(state_item.get("progress_percent", 0) or 0),
            "summary": str(state_item.get("summary", "") or summary),
            "error": str(state_item.get("error", "") or ""),
            "finished_at": str(state_item.get("finished_at", "") or ""),
            "pipeline_summary": str(
                state_item.get("pipeline_summary", "") or "queued_from_codex_plan"
            ),
        }
    )
    route_state.setdefault("items", {})[item_id] = state_item
    route_state["updated_at"] = now_iso()
    write_json(route_state_path(route), route_state)


def append_generated_queue_items(
    generated_items: list[dict[str, Any]],
) -> list[dict[str, str]]:
    from .executor import queue_route_by_mode

    build_route = queue_route_by_mode("opencode_build")
    review_route = queue_route_by_mode("codex_review")
    queued: list[dict[str, str]] = []
    for raw_item in generated_items:
        manifest_item = normalize_generated_queue_item(raw_item)
        if not manifest_item:
            continue
        instruction_path = Path(str(manifest_item.get("instruction_path", "") or ""))
        if not instruction_path.exists():
            continue
        target_route = build_route if manifest_item["entry_stage"] == "build" else review_route
        if not target_route:
            continue
        manifest_path = Path(str(target_route.get("manifest_path", "") or ""))
        if not str(manifest_path):
            continue
        upsert_manifest_item(manifest_path, manifest_item)
        upsert_route_state_item(
            target_route,
            manifest_item,
            "由自动策划 runner 生成，等待后续自动执行。",
        )
        queued.append(
            {
                "id": str(manifest_item["id"]),
                "stage": str(manifest_item["entry_stage"]),
                "instruction_path": str(manifest_item["instruction_path"]),
            }
        )
    return queued


def find_manifest_item(route: dict[str, Any], item_id: str) -> dict[str, Any] | None:
    for item in load_manifest_items(route):
        if str(item.get("id", "") or "") == item_id:
            return item
    return None


def active_route_item_ids(route_state: dict[str, Any]) -> list[str]:
    current_ids = route_current_item_ids(route_state)
    items = route_state.get("items") or {}
    running_ids = [
        str(item_id)
        for item_id, state_item in items.items()
        if isinstance(state_item, dict) and str(state_item.get("status", "")) == "running"
    ]
    if current_ids:
        filtered = [
            item_id
            for item_id in current_ids
            if item_id not in items
            or str((items.get(item_id) or {}).get("status", "")) == "running"
        ]
        return filtered or running_ids
    return running_ids


def find_manifest_item_with_normalization(
    route: dict[str, Any], item_id: str
) -> dict[str, Any] | None:
    """查找manifest条目，支持规范化ID匹配

    TaskIdentityContract集成：解决ID以'-'开头被argparse误识别问题
    深度审计发现：13个以'-'开头的任务ID（占6.74%）
    此函数处理规范化ID与原始manifest ID的映射
    """
    # 1. 首先尝试精确匹配
    item = find_manifest_item(route, item_id)
    if item:
        return item

    # 2. 如果精确匹配失败，尝试规范化匹配（处理以'-'开头的ID）
    try:
        # 动态导入TaskIdentityContract
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from contracts.task_identity import TaskIdentity

        # 2.1 如果item_id是规范化后的ID，尝试在manifest中查找原始ID
        # 规范化过程可能移除了开头的'-'或进行了其他转换
        for manifest_item in load_manifest_items(route):
            manifest_id = str(manifest_item.get("id", "") or "")
            if not manifest_id:
                continue

            # 尝试规范化manifest中的ID，与传入的item_id比较
            try:
                normalized_manifest = TaskIdentity.normalize(manifest_id)
                if normalized_manifest.id == item_id:
                    print(
                        f"⚠️  规范化匹配: '{item_id}' 匹配manifest条目 '{manifest_id}'",
                        file=sys.stderr,
                    )
                    return manifest_item
            except Exception:
                continue

        # 2.2 如果item_id可能是原始ID（以'-'开头），规范化后查找
        if item_id.startswith("-") or item_id.startswith("+"):
            try:
                normalized = TaskIdentity.normalize(item_id)
                # 使用规范化ID再次精确查找
                for manifest_item in load_manifest_items(route):
                    manifest_id = str(manifest_item.get("id", "") or "")
                    if manifest_id == normalized.id:
                        print(
                            f"⚠️  逆向规范化匹配: 原始ID '{item_id}' 通过规范化ID '{normalized.id}' 找到条目",
                            file=sys.stderr,
                        )
                        return manifest_item
            except Exception:
                pass

    except Exception as e:
        print(f"⚠️  TaskIdentityContract规范化匹配失败: {e}", file=sys.stderr)

    # 3. 所有尝试都失败
    return None


def route_index_by_item_id(
    routes: list[dict[str, Any]] | None = None,
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    route_map: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    config_routes = routes if routes is not None else list(load_plan_config().get("routes", []))
    for route in config_routes:
        route_state = load_route_state(route)
        for item_id, state_item in (route_state.get("items") or {}).items():
            if isinstance(state_item, dict):
                route_map[str(item_id)] = (route, state_item)
    return route_map
