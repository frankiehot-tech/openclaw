#!/usr/bin/env python3
"""task"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_scripts_dir = Path(__file__).resolve().parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

try:
    from .openclaw_roots import (
        LOG_DIR,
        PLAN_CONFIG_PATH,
        PLAN_DIR,
        QUEUE_STATE_DIR,
        RUNTIME_ROOT,
        TASKS_DIR,
        TASKS_PATH,
        pid_file,
    )
except ImportError:
    import sys
    from openclaw_roots import (
        TASKS_PATH,
    )

from .route_state import mutate_route_state, route_current_item_ids, load_route_state

from .state import record_performance_metric
from .utils import now_iso, read_json, write_json, clip


def load_tasks_payload() -> dict[str, Any]:
    payload = read_json(TASKS_PATH, default={"version": 1, "tasks": []}) or {
        "version": 1,
        "tasks": [],
    }
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        payload["tasks"] = []
    return payload


def save_tasks_payload(payload: dict[str, Any]) -> None:
    write_json(TASKS_PATH, payload)


def upsert_task_record(task_record: dict[str, Any]) -> None:
    payload = load_tasks_payload()
    tasks = payload.setdefault("tasks", [])
    task_id = str(task_record.get("id", "") or "")
    replaced = False
    for index, task in enumerate(tasks):
        if str(task.get("id", "") or "") == task_id:
            merged = dict(task)
            merged.update(task_record)
            tasks[index] = merged
            replaced = True
            break
    if not replaced:
        tasks.append(task_record)
    save_tasks_payload(payload)


def set_task_status(
    task_id: str,
    *,
    title: str,
    queue_item_id: str,
    stage: str,
    status: str,
    progress_percent: int,
    instruction_path: str,
    executor: str = "opencode",
    artifact_path: str = "",
    summary: str = "",
    error: str = "",
    started_at: str = "",
    finished_at: str = "",
) -> None:
    created_at = started_at or now_iso()
    upsert_task_record(
        {
            "id": task_id,
            "title": title,
            "queue_item_id": queue_item_id,
            "stage": stage,
            "executor": executor,
            "status": status,
            "progress_percent": int(progress_percent),
            "instruction_path": instruction_path,
            "artifact_path": artifact_path,
            "summary": summary,
            "error": error,
            "created_at": created_at,
            "started_at": started_at,
            "finished_at": finished_at,
            "updated_at": now_iso(),
        }
    )

    # Record performance metrics for completed/failed tasks
    try:
        if finished_at and finished_at.strip() and status in ("completed", "failed"):
            # Calculate response time in seconds
            try:
                from datetime import datetime

                start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                finish_dt = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
                response_time_seconds = (finish_dt - start_dt).total_seconds()
                if response_time_seconds >= 0:
                    record_performance_metric(
                        dimension="RESPONSE_TIME",
                        value=response_time_seconds,
                        labels={
                            "queue_item_id": queue_item_id,
                            "stage": stage,
                            "executor": executor,
                            "status": status,
                        },
                        metadata={"task_id": task_id},
                    )
            except Exception:
                pass  # Silently ignore timestamp parsing errors

            # Record failure rate (1 for failed, 0 for completed)
            failure_rate = 1.0 if status == "failed" else 0.0
            record_performance_metric(
                dimension="FAILURE_RATE",
                value=failure_rate,
                labels={
                    "queue_item_id": queue_item_id,
                    "stage": stage,
                    "executor": executor,
                },
                metadata={"task_id": task_id},
            )

            # Record success rate (0 for failed, 1 for completed)
            success_rate = 0.0 if status == "failed" else 1.0
            record_performance_metric(
                dimension="SUCCESS_RATE",
                value=success_rate,
                labels={
                    "queue_item_id": queue_item_id,
                    "stage": stage,
                    "executor": executor,
                },
                metadata={"task_id": task_id},
            )

            # Update concurrency: task finished, decrement active count
            # We record concurrency as 0 for finished task (indicates task end)
            # The global collector will aggregate active counts from start/end events
            record_performance_metric(
                dimension="CONCURRENCY",
                value=0.0,
                labels={
                    "queue_item_id": queue_item_id,
                    "stage": stage,
                    "executor": executor,
                    "action": "end",
                },
                metadata={"task_id": task_id, "status": status},
            )
    except Exception:
        pass  # Silently ignore metric recording errors


def set_route_item_state(
    route: dict[str, Any], route_state: dict[str, Any], item_id: str, **updates: Any
) -> None:
    # 尝试使用StateSyncContract进行原子状态更新
    queue_id = route.get("queue_id")
    if queue_id:
        try:
            # 获取Athena状态同步适配器
            adapter = get_athena_state_sync_adapter(queue_id)

            # 使用atomic_update进行原子状态更新
            # 注意：StateSyncContract会自动添加updated_at时间戳
            success = adapter.atomic_update(item_id, updates)

            if success:
                # StateSyncContract更新成功，同时也会更新Web界面和manifest
                # 记录日志以便调试
                logger.debug(
                    f"StateSyncContract原子状态更新成功: queue_id={queue_id}, item_id={item_id}, updates={updates}"
                )
                return
            else:
                logger.warning(
                    f"StateSyncContract原子状态更新失败，回退到原机制: queue_id={queue_id}, item_id={item_id}"
                )
        except Exception as e:
            # StateSyncContract失败，回退到原机制
            logger.warning(f"StateSyncContract异常，回退到原机制: {str(e)}")

    # 回退到原来的mutate_route_state实现
    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        items = state.setdefault("items", {})
        state_item = dict(items.get(item_id, {}))
        state_item.update(updates)
        items[item_id] = state_item
        state["updated_at"] = now_iso()
        return state

    mutate_route_state(route, _mutate, fallback=route_state)


def add_route_current_item(route: dict[str, Any], item_id: str) -> dict[str, Any]:
    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        current_ids = route_current_item_ids(state)
        if item_id not in current_ids:
            current_ids.append(item_id)
        state["current_item_ids"] = current_ids
        state["current_item_id"] = current_ids[0] if current_ids else ""
        state["updated_at"] = now_iso()
        return state

    return mutate_route_state(route, _mutate)


def remove_route_current_item(route: dict[str, Any], item_id: str) -> dict[str, Any]:
    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        current_ids = [current for current in route_current_item_ids(state) if current != item_id]
        state["current_item_ids"] = current_ids
        state["current_item_id"] = current_ids[0] if current_ids else ""
        state["updated_at"] = now_iso()
        return state

    return mutate_route_state(route, _mutate)


def replace_route_current_items(route: dict[str, Any], item_ids: list[str]) -> dict[str, Any]:
    normalized = []
    for item_id in item_ids:
        value = str(item_id or "").strip()
        if value and value not in normalized:
            normalized.append(value)

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        state["current_item_ids"] = normalized
        state["current_item_id"] = normalized[0] if normalized else ""
        state["updated_at"] = now_iso()
        return state

    return mutate_route_state(route, _mutate)


def reset_failed_item_for_auto_retry(
    route: dict[str, Any],
    item_id: str,
    state_item: dict[str, Any],
    reason: str,
    *,
    rescue: bool = False,
) -> None:

    retry_count_key = "blocked_rescue_retry_count" if rescue else "auto_retry_count"
    retry_at_key = "last_blocked_rescue_retry_at" if rescue else "last_auto_retry_at"
    retry_reason_key = "last_blocked_rescue_retry_reason" if rescue else "last_auto_retry_reason"
    retry_limit = BLOCKED_RESCUE_RETRY_LIMIT if rescue else AUTO_RETRY_LIMIT
    retry_count = int(state_item.get(retry_count_key, 0) or 0) + 1
    preserved_excerpt = clip(failure_text(state_item), 240)
    retry_label = "阻塞自救重试" if rescue else "自动重试"
    set_route_item_state(
        route,
        load_route_state(route),
        item_id,
        status="pending",
        summary=f"系统{retry_label}第 {retry_count}/{retry_limit} 次：{reason}",
        error="",
        result_excerpt=preserved_excerpt,
        pipeline_summary="blocked_rescue_retry_pending" if rescue else "auto_retry_pending",
        artifact_paths=[],
        finished_at="",
        root_task_id="",
        progress_percent=0,
        current_stage_ids=[],
        runner_pid="",
        runner_heartbeat_at="",
        **{
            retry_count_key: retry_count,
            retry_at_key: now_iso(),
            retry_reason_key: reason,
        },
    )
    remove_route_current_item(route, item_id)
