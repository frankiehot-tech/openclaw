#!/usr/bin/env python3
"""executor"""

from __future__ import annotations

import logging
import os
import sys
import time
import json
import subprocess
from datetime import datetime, timezone
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
        LOG_DIR,
        PLAN_DIR,
        RUNTIME_ROOT,
        TASKS_DIR,
    )

from .utils import (
    now_iso,
    clip,
    extract_structured_result,
    codex_executable,
    terminate_process_tree,
    is_pid_alive,
    resource_gate_message,
    root_task_id_for,
)
from .state import emit_event, record_performance_metric
from .manifest import (
    load_manifest_items,
    update_manifest_instruction_path,
    archive_instruction_path_if_needed,
    active_route_item_ids,
    append_generated_queue_items,
)
from .route_state import (
    route_runner_mode,
    load_route_state,
    route_matches_runner_modes,
    add_route_current_item,
    remove_route_current_item,
)
from .task import set_task_status, set_route_item_state
from .preflight import (
    build_preflight_warnings,
    review_preflight_warnings,
    plan_preflight_warnings,
    validate_build_preflight,
    render_prompt,
    render_review_prompt,
    render_plan_prompt,
)
from .failure import failure_markdown, success_markdown, mark_stale_failed
from .trace import create_task_workspace, update_trace_status_change, add_trace_artifact
from .config import load_plan_config


def spawn_build_worker(
    route: dict[str, Any], item: dict[str, Any], telemetry: dict[str, Any]
) -> int:
    item_id = str(item.get("id", "") or "")
    title = str(item.get("title", item_id) or item_id)
    instruction_path = str(item.get("instruction_path", "") or "")
    stage = str(item.get("entry_stage", "build") or "build")

    # 计算任务ID和目录
    task_id = root_task_id_for(item, stage)
    task_dir = TASKS_DIR / task_id

    # TaskIdentityContract集成 - 规范化item_id以确保argparse安全
    # 深度审计发现：13个以'-'开头的任务ID（占6.74%）会导致argparse解析失败
    normalized_item_id = item_id
    if item_id and (item_id.startswith("-") or item_id.startswith("+")):
        try:
            # 动态导入TaskIdentityContract，避免循环依赖
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from contracts.task_identity import TaskIdentity

            # 规范化ID：移除开头的'-'或'+'，确保argparse安全
            normalized = TaskIdentity.normalize(item_id)
            print(
                f"⚠️  [TaskIdentityContract] 检测到问题ID '{item_id}'，已规范化为: {normalized.id}",
                flush=True,
            )
            normalized_item_id = normalized.id
        except Exception as e:
            print(f"⚠️  [TaskIdentityContract] 规范化失败: {e}", file=sys.stderr)
            print(f"⚠️  [TaskIdentityContract] 使用快速修复: 添加'task_'前缀", file=sys.stderr)
            # 快速回退修复
            if item_id.startswith("-") or item_id.startswith("+"):
                normalized_item_id = "task_" + item_id[1:]

    # 注册任务到并行构建门控
    try:
        gate = get_global_gate()
        registered = gate.register_task(task_id, task_dir)
        if not registered:
            # 任务已注册（重复），记录警告但继续
            print(f"[parallel-build-gate] 任务 {task_id} 已注册，可能重复启动", flush=True)

        # 验证隔离约束（基本检查）
        # 注意：此时还不知道worker将访问的具体路径，仅验证工作目录不冲突
        isolation_ok, violations = gate.validate_isolation(task_id, [str(task_dir)])
        if not isolation_ok:
            print(f"[parallel-build-gate] 隔离约束违规: {violations}", flush=True)
            # 仍继续，但记录警告
    except Exception as e:
        # 门控不可用或出错，不影响现有功能
        print(f"[parallel-build-gate] 注册任务失败: {e}", flush=True)

    import shlex

    command_parts = [
        sys.executable,
        str(Path(__file__).resolve()),
        "run-item",
        str(route.get("queue_id", "") or ""),
        normalized_item_id,  # 使用规范化后的ID
    ]
    # 对每个部分进行shell转义，然后连接成字符串
    command = " ".join(shlex.quote(part) for part in command_parts)
    log_path = LOG_DIR / "athena_ai_plan_build_worker.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 使用ProcessLifecycleContract启动进程 - 解决进程可靠性契约缺失问题
    try:
        # 动态导入，避免循环依赖（与TaskIdentityContract模式一致）
        from contracts.process_lifecycle import ProcessLifecycleContract

        contract_manager = ProcessLifecycleContract()

        # 准备环境变量
        env = {
            "PYTHONPATH": str(RUNTIME_ROOT),
            "OPENCLAW_ROOT": str(RUNTIME_ROOT),
            "TELEMETRY_BUDGET": str(telemetry.get("budget", 1)),
        }

        # 使用契约启动进程，设置30秒超时（与心跳检测优化保持一致）
        process_info = contract_manager.spawn_with_contract(
            command=command,
            env=env,
            cwd=str(RUNTIME_ROOT),
            timeout_seconds=30,  # 30秒超时，与心跳检测目标一致
        )

        if process_info.get("success") and process_info.get("pid"):
            # 进程启动成功，更新状态为running
            pid = process_info["pid"]

            # 打开日志文件记录启动信息
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(
                    f"[ProcessLifecycleContract] 进程启动成功: PID={pid}, 命令={command}\n"
                )

            add_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="running",
                title=title,
                stage=stage,
                executor="opencode",
                instruction_path=instruction_path,
                progress_percent=2,
                summary=clip(
                    "已分配 build worker，正在启动 OpenCode。"
                    f" 当前并发预算={telemetry.get('budget', 1)}，"
                    f"load1={telemetry.get('load_average_1m', '-')}, "
                    f"free_mem={telemetry.get('free_memory_percent', '-')}, "
                    f"ollama_cpu={telemetry.get('ollama_cpu_percent', '-')}"
                ),
                error="",
                finished_at="",
                artifact_paths=[],
                result_excerpt="",
                pipeline_summary=f"worker_launching:{telemetry.get('reason', '')}",
                current_stage_ids=[stage],
                runner_pid=pid,
                runner_heartbeat_at=now_iso(),
                started_at=now_iso(),
            )
            print(
                f"[ProcessLifecycleContract] 进程启动成功，状态已更新为running: PID={pid}",
                flush=True,
            )
            return pid
        else:
            # 进程启动失败，记录错误但不更新状态
            error_msg = process_info.get("error", "未知错误")
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(
                    f"[ProcessLifecycleContract] 进程启动失败: {error_msg}, 命令={command}\n"
                )

            print(f"[ProcessLifecycleContract] 进程启动失败: {error_msg}", flush=True)
            # 返回0表示启动失败，保持与现有错误处理兼容
            return 0

    except ImportError as e:
        # contracts模块不可用，直接失败而不是回退到原始实现
        error_msg = f"ProcessLifecycleContract导入失败: {e}. contracts模块必须可用。"
        print(f"[ProcessLifecycleContract] {error_msg}", flush=True)
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(
                f"[ProcessLifecycleContract] 进程启动失败: {error_msg}, 命令={command}\n"
            )
        # 返回0表示启动失败，与契约失败处理保持一致
        return 0
    except Exception as e:
        # 其他异常，记录错误并返回0
        error_msg = f"进程启动异常: {str(e)}"
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[ProcessLifecycleContract] 异常: {error_msg}, 命令={command}\n")

        print(f"[ProcessLifecycleContract] 异常: {error_msg}", flush=True)
        return 0


def execute_build_item(route: dict[str, Any], item: dict[str, Any]) -> None:
    item_id = str(item.get("id", "") or "")
    title = str(item.get("title", item_id) or item_id)
    instruction_path = str(item.get("instruction_path", "") or "")
    stage = str(item.get("entry_stage", "build") or "build")
    started_at = now_iso()
    runner_pid = os.getpid()
    task_id = root_task_id_for(item, stage)
    task_dir = TASKS_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    workspace_paths = create_task_workspace(task_dir)
    stdout_log = task_dir / "stdout.log"
    request_json = task_dir / "request.json"
    build_md = task_dir / "build.md"
    update_trace_status_change(task_dir, "pending", "created", "task directory initialized")

    add_route_current_item(route, item_id)
    route_state = load_route_state(route)
    set_route_item_state(
        route,
        route_state,
        item_id,
        status="running",
        title=title,
        stage=stage,
        executor="opencode",
        root_task_id=task_id,
        started_at=started_at,
        finished_at="",
        artifact_paths=[],
        progress_percent=8,
        summary="队列 runner 已接手，正在做执行前检查。",
        error="",
        result_excerpt="",
        pipeline_summary="OpenCode preflight",
        current_stage_ids=[stage],
        instruction_path=instruction_path,
        runner_pid=runner_pid,
        runner_heartbeat_at=now_iso(),
    )
    update_trace_status_change(task_dir, "created", "running", "task started execution")
    # Emit task start event
    emit_event(
        EventType.TASK,
        {
            "task_id": task_id,
            "queue_item_id": item_id,
            "stage": stage,
            "task_dir": str(task_dir),
        },
        {"status": "running", "title": title, "instruction_path": instruction_path},
        {"hook_point": HookPoint.TASK_START},
    )
    set_task_status(
        task_id,
        title=title,
        queue_item_id=item_id,
        stage=stage,
        status="running",
        progress_percent=8,
        instruction_path=instruction_path,
        summary="队列 runner 已接手，正在做执行前检查。",
        started_at=started_at,
    )

    if not instruction_path or not Path(instruction_path).exists():
        error = f"instruction_path 不存在：{instruction_path or '(空路径)'}"
        build_md.write_text(
            failure_markdown(title, task_id, instruction_path, error, warnings=[]),
            encoding="utf-8",
        )
        remove_route_current_item(route, item_id)
        set_route_item_state(
            route,
            load_route_state(route),
            item_id,
            status="failed",
            progress_percent=100,
            summary=error,
            error=error,
            finished_at=now_iso(),
            artifact_paths=[str(build_md)],
            pipeline_summary="OpenCode preflight failed",
        )
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="failed",
            progress_percent=100,
            instruction_path=instruction_path,
            artifact_path=str(build_md),
            summary=error,
            error=error,
            started_at=started_at,
            finished_at=now_iso(),
        )
        return

    instruction_text = Path(instruction_path).read_text(encoding="utf-8")
    warnings = build_preflight_warnings(instruction_text)
    gate_reason = resource_gate_message()
    if gate_reason:
        remove_route_current_item(route, item_id)
        set_route_item_state(
            route,
            load_route_state(route),
            item_id,
            status="pending",
            progress_percent=0,
            summary=gate_reason,
            error="",
            finished_at="",
            artifact_paths=[],
            pipeline_summary="waiting_for_resources",
        )
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="pending",
            progress_percent=0,
            instruction_path=instruction_path,
            summary=gate_reason,
            started_at=started_at,
        )
        return

    # 新增：结构化 preflight gate 校验
    preflight_ok, preflight_reason, should_be_manual = validate_build_preflight(
        instruction_text, item
    )
    if not preflight_ok:
        remove_route_current_item(route, item_id)
        new_status = "manual_hold" if should_be_manual else "failed"
        pipeline_summary = (
            "preflight_reject_manual" if should_be_manual else "preflight_reject_failed"
        )
        set_route_item_state(
            route,
            load_route_state(route),
            item_id,
            status=new_status,
            progress_percent=100 if new_status == "failed" else 0,
            summary=preflight_reason,
            error=preflight_reason if new_status == "failed" else "",
            finished_at=now_iso() if new_status == "failed" else "",
            artifact_paths=[],
            pipeline_summary=pipeline_summary,
        )
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status=new_status,
            progress_percent=100 if new_status == "failed" else 0,
            instruction_path=instruction_path,
            summary=preflight_reason,
            error=preflight_reason if new_status == "failed" else "",
            started_at=started_at,
            finished_at=now_iso() if new_status == "failed" else "",
        )
        return

    prompt = render_prompt(item, instruction_text, warnings)
    request_json.write_text(
        json.dumps(
            {
                "queue_item": item,
                "instruction_path": instruction_path,
                "prompt": prompt,
                "warnings": warnings,
                "runtime_root": str(RUNTIME_ROOT),
                "created_at": now_iso(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # Emit artifact written event
    emit_event(
        EventType.ARTIFACT,
        {
            "task_id": task_id,
            "queue_item_id": item_id,
            "stage": stage,
            "task_dir": str(task_dir),
        },
        {
            "artifact_type": "request_json",
            "path": str(request_json),
            "size": request_json.stat().st_size if request_json.exists() else 0,
        },
        {"hook_point": HookPoint.ARTIFACT_WRITTEN},
    )

    command = [
        "/Volumes/1TB-M2/openclaw/bin/opencode-athena",
        "run",
        "--format",
        "default",
        "--title",
        title,
        "--model",
        "alibaba/qwen3.5-plus",
        prompt,
    ]
    # Emit pre-tool event
    emit_event(
        EventType.TOOL,
        {
            "task_id": task_id,
            "queue_item_id": item_id,
            "stage": stage,
            "task_dir": str(task_dir),
        },
        {"tool": "opencode", "command": command, "status": "starting"},
        {"hook_point": HookPoint.PRE_TOOL},
    )
    process = subprocess.Popen(
        command,
        cwd=str(RUNTIME_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    selector = selectors.DefaultSelector()
    assert process.stdout is not None
    selector.register(process.stdout, selectors.EVENT_READ)
    start_time = time.time()
    last_update = 0.0
    last_output_at = start_time
    output_lines: list[str] = []

    while True:
        if STOP_REQUESTED:
            terminate_process_tree(process, grace_seconds=8)
            error = "runner 收到停止信号，当前执行已中断。"
            stdout_log.write_text("".join(output_lines), encoding="utf-8")
            build_md.write_text(
                failure_markdown(
                    title,
                    task_id,
                    instruction_path,
                    error,
                    warnings,
                    clip("".join(output_lines), 3000),
                ),
                encoding="utf-8",
            )
            remove_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="failed",
                progress_percent=100,
                summary=error,
                error=error,
                finished_at=now_iso(),
                artifact_paths=[str(build_md), str(stdout_log), str(request_json)],
                result_excerpt=clip("".join(output_lines), 280),
                pipeline_summary="runner_stopped",
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="failed",
                progress_percent=100,
                instruction_path=instruction_path,
                artifact_path=str(build_md),
                summary=error,
                error=error,
                started_at=started_at,
                finished_at=now_iso(),
            )
            return

        for key, _ in selector.select(timeout=1.5):
            line = key.fileobj.readline()
            if line:
                output_lines.append(line)
                last_output_at = time.time()

        elapsed = time.time() - start_time
        if elapsed > BUILD_TIMEOUT_SECONDS and process.poll() is None:
            terminate_process_tree(process, grace_seconds=12)
            output_text = "".join(output_lines)
            stdout_log.write_text(output_text, encoding="utf-8")
            error = f"OpenCode 超时：超过 {BUILD_TIMEOUT_SECONDS}s 仍未完成。"
            build_md.write_text(
                failure_markdown(
                    title,
                    task_id,
                    instruction_path,
                    error,
                    warnings,
                    clip(output_text, 3000),
                ),
                encoding="utf-8",
            )
            remove_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="failed",
                progress_percent=100,
                summary=error,
                error=error,
                finished_at=now_iso(),
                artifact_paths=[str(build_md), str(stdout_log), str(request_json)],
                result_excerpt=clip(output_text, 280),
                pipeline_summary="OpenCode timeout",
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="failed",
                progress_percent=100,
                instruction_path=instruction_path,
                artifact_path=str(build_md),
                summary=error,
                error=error,
                started_at=started_at,
                finished_at=now_iso(),
            )
            return

        silent_for = time.time() - last_output_at
        if (
            STALL_OUTPUT_TIMEOUT_SECONDS > 0
            and silent_for > STALL_OUTPUT_TIMEOUT_SECONDS
            and process.poll() is None
        ):
            terminate_process_tree(process, grace_seconds=12)
            output_text = "".join(output_lines)
            stdout_log.write_text(output_text, encoding="utf-8")
            error = (
                f"OpenCode 长时间无新输出：超过 {STALL_OUTPUT_TIMEOUT_SECONDS}s，"
                "判定为卡住并提前终止。"
            )
            build_md.write_text(
                failure_markdown(
                    title,
                    task_id,
                    instruction_path,
                    error,
                    warnings,
                    clip(output_text, 3000),
                ),
                encoding="utf-8",
            )
            remove_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="failed",
                progress_percent=100,
                summary=error,
                error=error,
                finished_at=now_iso(),
                artifact_paths=[str(build_md), str(stdout_log), str(request_json)],
                result_excerpt=clip(output_text, 280),
                pipeline_summary="OpenCode stalled",
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="failed",
                progress_percent=100,
                instruction_path=instruction_path,
                artifact_path=str(build_md),
                summary=error,
                error=error,
                started_at=started_at,
                finished_at=now_iso(),
            )
            return

        if process.poll() is not None:
            break

        if (time.time() - last_update) >= 5:
            progress = min(92, 20 + int((elapsed / max(BUILD_TIMEOUT_SECONDS, 1)) * 60))
            latest = ""
            for line in reversed(output_lines[-8:]):
                if line.strip():
                    latest = line.strip()
                    break
            summary = clip(
                latest
                or (
                    f"OpenCode 正在执行，已运行 {int(elapsed)}s，最近输出约 {int(silent_for)}s 前。"
                )
            )
            add_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="running",
                progress_percent=progress,
                summary=summary,
                pipeline_summary="OpenCode running",
                result_excerpt=clip("".join(output_lines[-16:]), 280),
                runner_heartbeat_at=now_iso(),
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="running",
                progress_percent=progress,
                instruction_path=instruction_path,
                summary=summary,
                started_at=started_at,
            )
            last_update = time.time()
    # Emit post-tool event
    emit_event(
        EventType.TOOL,
        {
            "task_id": task_id,
            "queue_item_id": item_id,
            "stage": stage,
            "task_dir": str(task_dir),
        },
        {"tool": "opencode", "exit_code": process.returncode, "status": "finished"},
        {"hook_point": HookPoint.POST_TOOL},
    )
    output_text = "".join(output_lines)
    stdout_log.write_text(output_text, encoding="utf-8")
    # Emit artifact written event
    emit_event(
        EventType.ARTIFACT,
        {
            "task_id": task_id,
            "queue_item_id": item_id,
            "stage": stage,
            "task_dir": str(task_dir),
        },
        {
            "artifact_type": "stdout_log",
            "path": str(stdout_log),
            "size": len(output_text),
        },
        {"hook_point": HookPoint.ARTIFACT_WRITTEN},
    )
    finished_at = now_iso()
    remove_route_current_item(route, item_id)
    route_state = load_route_state(route)
    final_instruction_path = instruction_path
    artifact_paths = [str(build_md), str(stdout_log), str(request_json)]

    if process.returncode == 0:
        build_md.write_text(
            success_markdown(title, task_id, instruction_path, warnings, output_text),
            encoding="utf-8",
        )
        # Emit artifact written event
        emit_event(
            EventType.ARTIFACT,
            {
                "task_id": task_id,
                "queue_item_id": item_id,
                "stage": stage,
                "task_dir": str(task_dir),
            },
            {
                "artifact_type": "build_md",
                "path": str(build_md),
                "size": build_md.stat().st_size if build_md.exists() else 0,
            },
            {"hook_point": HookPoint.ARTIFACT_WRITTEN},
        )
        final_instruction_path = finalize_completed_instruction(route, item_id, instruction_path)
        summary = clip(
            next(
                (line.strip() for line in reversed(output_lines) if line.strip()),
                "OpenCode 已完成。",
            )
        )
        set_route_item_state(
            route,
            route_state,
            item_id,
            status="completed",
            progress_percent=100,
            summary=summary,
            finished_at=finished_at,
            artifact_paths=artifact_paths,
            error="",
            pipeline_summary="OpenCode completed",
            result_excerpt=clip(output_text, 280),
            instruction_path=final_instruction_path,
        )
        update_trace_status_change(task_dir, "running", "completed", "task succeeded")
        # Emit task finish event
        emit_event(
            EventType.TASK,
            {
                "task_id": task_id,
                "queue_item_id": item_id,
                "stage": stage,
                "task_dir": str(task_dir),
            },
            {
                "status": "completed",
                "summary": summary,
                "exit_code": process.returncode,
            },
            {"hook_point": HookPoint.TASK_FINISH},
        )
        for artifact_path in artifact_paths:
            add_trace_artifact(task_dir, "output", artifact_path, {"stage": stage})
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="completed",
            progress_percent=100,
            instruction_path=final_instruction_path,
            artifact_path=str(build_md),
            summary=summary,
            started_at=started_at,
            finished_at=finished_at,
        )
        # 写入 daily memory 记录
        append_to_daily_memory(
            title=title,
            root_task_id=task_id,
            queue_item_id=item_id,
            stage=stage,
            instruction_path=final_instruction_path,
            summary=summary,
            warnings=warnings,
            status="completed",
        )
    else:
        error = clip(
            next(
                (line.strip() for line in reversed(output_lines) if line.strip()),
                f"OpenCode 退出码 {process.returncode}",
            )
        )
        build_md.write_text(
            failure_markdown(
                title,
                task_id,
                instruction_path,
                error,
                warnings,
                clip(output_text, 3000),
            ),
            encoding="utf-8",
        )
        set_route_item_state(
            route,
            route_state,
            item_id,
            status="failed",
            progress_percent=100,
            summary=error,
            error=error,
            finished_at=finished_at,
            artifact_paths=artifact_paths,
            pipeline_summary="OpenCode failed",
            result_excerpt=clip(output_text, 280),
        )
        update_trace_status_change(
            task_dir,
            "running",
            "failed",
            f"task failed with exit code {process.returncode}",
        )
        # Emit task finish event
        emit_event(
            EventType.TASK,
            {
                "task_id": task_id,
                "queue_item_id": item_id,
                "stage": stage,
                "task_dir": str(task_dir),
            },
            {"status": "failed", "summary": error, "exit_code": process.returncode},
            {"hook_point": HookPoint.TASK_FINISH},
        )
        for artifact_path in artifact_paths:
            add_trace_artifact(task_dir, "output", artifact_path, {"stage": stage})
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="failed",
            progress_percent=100,
            instruction_path=instruction_path,
            artifact_path=str(build_md),
            summary=error,
            error=error,
            started_at=started_at,
            finished_at=finished_at,
        )
        # 写入 daily memory 记录
        append_to_daily_memory(
            title=title,
            root_task_id=task_id,
            queue_item_id=item_id,
            stage=stage,
            instruction_path=instruction_path,
            summary=error,
            warnings=warnings,
            status="failed",
        )


def execute_review_item(route: dict[str, Any], item: dict[str, Any]) -> None:
    item_id = str(item.get("id", "") or "")
    title = str(item.get("title", item_id) or item_id)
    instruction_path = str(item.get("instruction_path", "") or "")
    stage = str(item.get("entry_stage", "review") or "review")
    started_at = now_iso()
    runner_pid = os.getpid()
    task_id = root_task_id_for(item, stage)
    task_dir = TASKS_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = task_dir / "stdout.log"
    request_json = task_dir / "request.json"
    review_md = task_dir / "review.md"
    final_message = task_dir / "last_message.md"

    add_route_current_item(route, item_id)
    route_state = load_route_state(route)
    set_route_item_state(
        route,
        route_state,
        item_id,
        status="running",
        title=title,
        stage=stage,
        executor="codex",
        root_task_id=task_id,
        started_at=started_at,
        finished_at="",
        artifact_paths=[],
        progress_percent=8,
        summary="Codex review runner 已接手，正在做执行前检查。",
        error="",
        result_excerpt="",
        pipeline_summary="Codex review preflight",
        current_stage_ids=[stage],
        instruction_path=instruction_path,
        runner_pid=runner_pid,
        runner_heartbeat_at=now_iso(),
    )
    set_task_status(
        task_id,
        title=title,
        queue_item_id=item_id,
        stage=stage,
        status="running",
        progress_percent=8,
        instruction_path=instruction_path,
        executor="codex",
        summary="Codex review runner 已接手，正在做执行前检查。",
        started_at=started_at,
    )

    if not instruction_path or not Path(instruction_path).exists():
        error = f"instruction_path 不存在：{instruction_path or '(空路径)'}"
        review_md.write_text(
            failure_markdown(title, task_id, instruction_path, error, warnings=[]),
            encoding="utf-8",
        )
        remove_route_current_item(route, item_id)
        set_route_item_state(
            route,
            load_route_state(route),
            item_id,
            status="failed",
            progress_percent=100,
            summary=error,
            error=error,
            finished_at=now_iso(),
            artifact_paths=[str(review_md)],
            pipeline_summary="Codex review preflight failed",
        )
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="failed",
            progress_percent=100,
            instruction_path=instruction_path,
            executor="codex",
            artifact_path=str(review_md),
            summary=error,
            error=error,
            started_at=started_at,
            finished_at=now_iso(),
        )
        return

    instruction_text = Path(instruction_path).read_text(encoding="utf-8")
    warnings = review_preflight_warnings(instruction_text)
    gate_reason = resource_gate_message()
    if gate_reason:
        remove_route_current_item(route, item_id)
        set_route_item_state(
            route,
            load_route_state(route),
            item_id,
            status="pending",
            progress_percent=0,
            summary=gate_reason,
            error="",
            finished_at="",
            artifact_paths=[],
            pipeline_summary="waiting_for_resources",
        )
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="pending",
            progress_percent=0,
            instruction_path=instruction_path,
            executor="codex",
            summary=gate_reason,
            started_at=started_at,
        )
        return

    prompt = render_review_prompt(item, instruction_text, warnings)
    request_json.write_text(
        json.dumps(
            {
                "queue_item": item,
                "instruction_path": instruction_path,
                "prompt": prompt,
                "warnings": warnings,
                "runtime_root": str(RUNTIME_ROOT),
                "created_at": now_iso(),
                "executor": "codex",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    codex_bin = codex_executable()
    command = [
        codex_bin,
        "-a",
        "never",
        "-s",
        "danger-full-access",
        "exec",
        "--skip-git-repo-check",
        "-C",
        str(RUNTIME_ROOT),
        "--output-last-message",
        str(final_message),
        prompt,
    ]
    process = subprocess.Popen(
        command,
        cwd=str(RUNTIME_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    selector = selectors.DefaultSelector()
    assert process.stdout is not None
    selector.register(process.stdout, selectors.EVENT_READ)
    start_time = time.time()
    last_update = 0.0
    last_output_at = start_time
    output_lines: list[str] = []

    while True:
        if STOP_REQUESTED:
            terminate_process_tree(process, grace_seconds=8)
            error = "review runner 收到停止信号，当前执行已中断。"
            stdout_log.write_text("".join(output_lines), encoding="utf-8")
            review_md.write_text(
                failure_markdown(
                    title,
                    task_id,
                    instruction_path,
                    error,
                    warnings,
                    clip("".join(output_lines), 3000),
                ),
                encoding="utf-8",
            )
            remove_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="failed",
                progress_percent=100,
                summary=error,
                error=error,
                finished_at=now_iso(),
                artifact_paths=[
                    str(review_md),
                    str(final_message),
                    str(stdout_log),
                    str(request_json),
                ],
                result_excerpt=clip("".join(output_lines), 280),
                pipeline_summary="review_runner_stopped",
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="failed",
                progress_percent=100,
                instruction_path=instruction_path,
                executor="codex",
                artifact_path=str(review_md),
                summary=error,
                error=error,
                started_at=started_at,
                finished_at=now_iso(),
            )
            return

        for key, _ in selector.select(timeout=1.5):
            line = key.fileobj.readline()
            if line:
                output_lines.append(line)
                last_output_at = time.time()

        elapsed = time.time() - start_time
        if elapsed > REVIEW_TIMEOUT_SECONDS and process.poll() is None:
            terminate_process_tree(process, grace_seconds=12)
            output_text = "".join(output_lines)
            stdout_log.write_text(output_text, encoding="utf-8")
            error = f"Codex 审计超时：超过 {REVIEW_TIMEOUT_SECONDS}s 仍未完成。"
            review_md.write_text(
                failure_markdown(
                    title,
                    task_id,
                    instruction_path,
                    error,
                    warnings,
                    clip(output_text, 3000),
                ),
                encoding="utf-8",
            )
            remove_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="failed",
                progress_percent=100,
                summary=error,
                error=error,
                finished_at=now_iso(),
                artifact_paths=[
                    str(review_md),
                    str(final_message),
                    str(stdout_log),
                    str(request_json),
                ],
                result_excerpt=clip(output_text, 280),
                pipeline_summary="Codex review timeout",
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="failed",
                progress_percent=100,
                instruction_path=instruction_path,
                executor="codex",
                artifact_path=str(review_md),
                summary=error,
                error=error,
                started_at=started_at,
                finished_at=now_iso(),
            )
            return

        silent_for = time.time() - last_output_at
        if (
            STALL_OUTPUT_TIMEOUT_SECONDS > 0
            and silent_for > STALL_OUTPUT_TIMEOUT_SECONDS
            and process.poll() is None
        ):
            terminate_process_tree(process, grace_seconds=12)
            output_text = "".join(output_lines)
            stdout_log.write_text(output_text, encoding="utf-8")
            error = (
                f"Codex 长时间无新输出：超过 {STALL_OUTPUT_TIMEOUT_SECONDS}s，"
                "判定为卡住并提前终止。"
            )
            review_md.write_text(
                failure_markdown(
                    title,
                    task_id,
                    instruction_path,
                    error,
                    warnings,
                    clip(output_text, 3000),
                ),
                encoding="utf-8",
            )
            remove_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="failed",
                progress_percent=100,
                summary=error,
                error=error,
                finished_at=now_iso(),
                artifact_paths=[
                    str(review_md),
                    str(final_message),
                    str(stdout_log),
                    str(request_json),
                ],
                result_excerpt=clip(output_text, 280),
                pipeline_summary="Codex review stalled",
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="failed",
                progress_percent=100,
                instruction_path=instruction_path,
                executor="codex",
                artifact_path=str(review_md),
                summary=error,
                error=error,
                started_at=started_at,
                finished_at=now_iso(),
            )
            return

        if process.poll() is not None:
            break

        if (time.time() - last_update) >= 5:
            progress = min(92, 20 + int((elapsed / max(REVIEW_TIMEOUT_SECONDS, 1)) * 60))
            latest = ""
            for line in reversed(output_lines[-8:]):
                if line.strip():
                    latest = line.strip()
                    break
            summary = clip(
                latest
                or (f"Codex 正在审计，已运行 {int(elapsed)}s，最近输出约 {int(silent_for)}s 前。")
            )
            add_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="running",
                progress_percent=progress,
                summary=summary,
                pipeline_summary="Codex review running",
                result_excerpt=clip("".join(output_lines[-16:]), 280),
                runner_heartbeat_at=now_iso(),
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="running",
                progress_percent=progress,
                instruction_path=instruction_path,
                executor="codex",
                summary=summary,
                started_at=started_at,
            )
            last_update = time.time()

    output_text = "".join(output_lines)
    stdout_log.write_text(output_text, encoding="utf-8")
    finished_at = now_iso()
    remove_route_current_item(route, item_id)
    route_state = load_route_state(route)
    final_instruction_path = instruction_path
    final_output = ""
    if final_message.exists():
        final_output = final_message.read_text(encoding="utf-8").strip()
    artifact_paths = [
        str(review_md),
        str(final_message),
        str(stdout_log),
        str(request_json),
    ]

    if process.returncode == 0:
        review_md.write_text(
            success_markdown(
                title,
                task_id,
                instruction_path,
                warnings,
                final_output or output_text,
                output_heading="Codex 审计输出",
            ),
            encoding="utf-8",
        )
        final_instruction_path = finalize_completed_instruction(route, item_id, instruction_path)
        summary = clip(
            final_output.splitlines()[0]
            if final_output.strip()
            else next(
                (line.strip() for line in reversed(output_lines) if line.strip()),
                "Codex 审计已完成。",
            )
        )
        set_route_item_state(
            route,
            route_state,
            item_id,
            status="completed",
            progress_percent=100,
            summary=summary,
            finished_at=finished_at,
            artifact_paths=artifact_paths,
            error="",
            pipeline_summary="Codex review completed",
            result_excerpt=clip(final_output or output_text, 280),
            instruction_path=final_instruction_path,
        )
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="completed",
            progress_percent=100,
            instruction_path=final_instruction_path,
            executor="codex",
            artifact_path=str(review_md),
            summary=summary,
            started_at=started_at,
            finished_at=finished_at,
        )
        # 写入 daily memory 记录
        append_to_daily_memory(
            title=title,
            root_task_id=task_id,
            queue_item_id=item_id,
            stage=stage,
            instruction_path=final_instruction_path,
            summary=summary,
            warnings=warnings,
            status="completed",
        )
    else:
        error = clip(
            next(
                (line.strip() for line in reversed(output_lines) if line.strip()),
                f"Codex 退出码 {process.returncode}",
            )
        )
        review_md.write_text(
            failure_markdown(
                title,
                task_id,
                instruction_path,
                error,
                warnings,
                clip(final_output or output_text, 3000),
            ),
            encoding="utf-8",
        )
        set_route_item_state(
            route,
            route_state,
            item_id,
            status="failed",
            progress_percent=100,
            summary=error,
            error=error,
            finished_at=finished_at,
            artifact_paths=artifact_paths,
            pipeline_summary="Codex review failed",
            result_excerpt=clip(final_output or output_text, 280),
        )
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="failed",
            progress_percent=100,
            instruction_path=instruction_path,
            executor="codex",
            artifact_path=str(review_md),
            summary=error,
            error=error,
            started_at=started_at,
            finished_at=finished_at,
        )
        # 写入 daily memory 记录
        append_to_daily_memory(
            title=title,
            root_task_id=task_id,
            queue_item_id=item_id,
            stage=stage,
            instruction_path=instruction_path,
            summary=error,
            warnings=warnings,
            status="failed",
        )


def execute_plan_item(route: dict[str, Any], item: dict[str, Any]) -> None:
    item_id = str(item.get("id", "") or "")
    title = str(item.get("title", item_id) or item_id)
    instruction_path = str(item.get("instruction_path", "") or "")
    stage = str(item.get("entry_stage", "plan") or "plan")
    started_at = now_iso()
    runner_pid = os.getpid()
    task_id = root_task_id_for(item, stage)
    task_dir = TASKS_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = task_dir / "stdout.log"
    request_json = task_dir / "request.json"
    plan_md = task_dir / "plan.md"
    final_message = task_dir / "last_message.md"

    add_route_current_item(route, item_id)
    route_state = load_route_state(route)
    set_route_item_state(
        route,
        route_state,
        item_id,
        status="running",
        title=title,
        stage=stage,
        executor="codex",
        root_task_id=task_id,
        started_at=started_at,
        finished_at="",
        artifact_paths=[],
        progress_percent=8,
        summary="Codex plan runner 已接手，正在做执行前检查。",
        error="",
        result_excerpt="",
        pipeline_summary="Codex plan preflight",
        current_stage_ids=[stage],
        instruction_path=instruction_path,
        runner_pid=runner_pid,
        runner_heartbeat_at=now_iso(),
    )
    set_task_status(
        task_id,
        title=title,
        queue_item_id=item_id,
        stage=stage,
        status="running",
        progress_percent=8,
        instruction_path=instruction_path,
        executor="codex",
        summary="Codex plan runner 已接手，正在做执行前检查。",
        started_at=started_at,
    )

    if not instruction_path or not Path(instruction_path).exists():
        error = f"instruction_path 不存在：{instruction_path or '(空路径)'}"
        plan_md.write_text(
            failure_markdown(title, task_id, instruction_path, error, warnings=[]),
            encoding="utf-8",
        )
        remove_route_current_item(route, item_id)
        set_route_item_state(
            route,
            load_route_state(route),
            item_id,
            status="failed",
            progress_percent=100,
            summary=error,
            error=error,
            finished_at=now_iso(),
            artifact_paths=[str(plan_md)],
            pipeline_summary="Codex plan preflight failed",
        )
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="failed",
            progress_percent=100,
            instruction_path=instruction_path,
            executor="codex",
            artifact_path=str(plan_md),
            summary=error,
            error=error,
            started_at=started_at,
            finished_at=now_iso(),
        )
        return

    instruction_text = Path(instruction_path).read_text(encoding="utf-8")
    warnings = plan_preflight_warnings(instruction_text)
    gate_reason = resource_gate_message()
    if gate_reason:
        remove_route_current_item(route, item_id)
        set_route_item_state(
            route,
            load_route_state(route),
            item_id,
            status="pending",
            progress_percent=0,
            summary=gate_reason,
            error="",
            finished_at="",
            artifact_paths=[],
            pipeline_summary="waiting_for_resources",
        )
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="pending",
            progress_percent=0,
            instruction_path=instruction_path,
            executor="codex",
            summary=gate_reason,
            started_at=started_at,
        )
        return

    prompt = render_plan_prompt(item, instruction_text, warnings)
    request_json.write_text(
        json.dumps(
            {
                "queue_item": item,
                "instruction_path": instruction_path,
                "prompt": prompt,
                "warnings": warnings,
                "runtime_root": str(RUNTIME_ROOT),
                "plan_dir": str(PLAN_DIR),
                "created_at": now_iso(),
                "executor": "codex",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    codex_bin = codex_executable()
    command = [
        codex_bin,
        "-a",
        "never",
        "-s",
        "danger-full-access",
        "exec",
        "--skip-git-repo-check",
        "-C",
        str(RUNTIME_ROOT),
        "--output-last-message",
        str(final_message),
        prompt,
    ]
    process = subprocess.Popen(
        command,
        cwd=str(RUNTIME_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    selector = selectors.DefaultSelector()
    assert process.stdout is not None
    selector.register(process.stdout, selectors.EVENT_READ)
    start_time = time.time()
    last_update = 0.0
    last_output_at = start_time
    output_lines: list[str] = []

    while True:
        if STOP_REQUESTED:
            terminate_process_tree(process, grace_seconds=8)
            error = "plan runner 收到停止信号，当前执行已中断。"
            stdout_log.write_text("".join(output_lines), encoding="utf-8")
            plan_md.write_text(
                failure_markdown(
                    title,
                    task_id,
                    instruction_path,
                    error,
                    warnings,
                    clip("".join(output_lines), 3000),
                ),
                encoding="utf-8",
            )
            remove_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="failed",
                progress_percent=100,
                summary=error,
                error=error,
                finished_at=now_iso(),
                artifact_paths=[
                    str(plan_md),
                    str(final_message),
                    str(stdout_log),
                    str(request_json),
                ],
                result_excerpt=clip("".join(output_lines), 280),
                pipeline_summary="plan_runner_stopped",
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="failed",
                progress_percent=100,
                instruction_path=instruction_path,
                executor="codex",
                artifact_path=str(plan_md),
                summary=error,
                error=error,
                started_at=started_at,
                finished_at=now_iso(),
            )
            return

        for key, _ in selector.select(timeout=1.5):
            line = key.fileobj.readline()
            if line:
                output_lines.append(line)
                last_output_at = time.time()

        elapsed = time.time() - start_time
        if elapsed > PLAN_TIMEOUT_SECONDS and process.poll() is None:
            terminate_process_tree(process, grace_seconds=12)
            output_text = "".join(output_lines)
            stdout_log.write_text(output_text, encoding="utf-8")
            error = f"Codex 策划超时：超过 {PLAN_TIMEOUT_SECONDS}s 仍未完成。"
            plan_md.write_text(
                failure_markdown(
                    title,
                    task_id,
                    instruction_path,
                    error,
                    warnings,
                    clip(output_text, 3000),
                ),
                encoding="utf-8",
            )
            remove_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="failed",
                progress_percent=100,
                summary=error,
                error=error,
                finished_at=now_iso(),
                artifact_paths=[
                    str(plan_md),
                    str(final_message),
                    str(stdout_log),
                    str(request_json),
                ],
                result_excerpt=clip(output_text, 280),
                pipeline_summary="Codex plan timeout",
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="failed",
                progress_percent=100,
                instruction_path=instruction_path,
                executor="codex",
                artifact_path=str(plan_md),
                summary=error,
                error=error,
                started_at=started_at,
                finished_at=now_iso(),
            )
            return

        silent_for = time.time() - last_output_at
        if (
            STALL_OUTPUT_TIMEOUT_SECONDS > 0
            and silent_for > STALL_OUTPUT_TIMEOUT_SECONDS
            and process.poll() is None
        ):
            terminate_process_tree(process, grace_seconds=12)
            output_text = "".join(output_lines)
            stdout_log.write_text(output_text, encoding="utf-8")
            error = (
                f"Codex 长时间无新输出：超过 {STALL_OUTPUT_TIMEOUT_SECONDS}s，"
                "判定为卡住并提前终止。"
            )
            plan_md.write_text(
                failure_markdown(
                    title,
                    task_id,
                    instruction_path,
                    error,
                    warnings,
                    clip(output_text, 3000),
                ),
                encoding="utf-8",
            )
            remove_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="failed",
                progress_percent=100,
                summary=error,
                error=error,
                finished_at=now_iso(),
                artifact_paths=[
                    str(plan_md),
                    str(final_message),
                    str(stdout_log),
                    str(request_json),
                ],
                result_excerpt=clip(output_text, 280),
                pipeline_summary="Codex plan stalled",
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="failed",
                progress_percent=100,
                instruction_path=instruction_path,
                executor="codex",
                artifact_path=str(plan_md),
                summary=error,
                error=error,
                started_at=started_at,
                finished_at=now_iso(),
            )
            return

        if process.poll() is not None:
            break

        if (time.time() - last_update) >= 5:
            progress = min(92, 20 + int((elapsed / max(PLAN_TIMEOUT_SECONDS, 1)) * 60))
            latest = ""
            for line in reversed(output_lines[-8:]):
                if line.strip():
                    latest = line.strip()
                    break
            summary = clip(
                latest
                or (
                    f"Codex 正在策划编译，已运行 {int(elapsed)}s，"
                    f"最近输出约 {int(silent_for)}s 前。"
                )
            )
            add_route_current_item(route, item_id)
            set_route_item_state(
                route,
                load_route_state(route),
                item_id,
                status="running",
                progress_percent=progress,
                summary=summary,
                pipeline_summary="Codex plan running",
                result_excerpt=clip("".join(output_lines[-16:]), 280),
                runner_heartbeat_at=now_iso(),
            )
            set_task_status(
                task_id,
                title=title,
                queue_item_id=item_id,
                stage=stage,
                status="running",
                progress_percent=progress,
                instruction_path=instruction_path,
                executor="codex",
                summary=summary,
                started_at=started_at,
            )
            last_update = time.time()

    output_text = "".join(output_lines)
    stdout_log.write_text(output_text, encoding="utf-8")
    finished_at = now_iso()
    remove_route_current_item(route, item_id)
    route_state = load_route_state(route)
    final_instruction_path = instruction_path
    final_output = ""
    if final_message.exists():
        final_output = final_message.read_text(encoding="utf-8").strip()
    artifact_paths = [
        str(plan_md),
        str(final_message),
        str(stdout_log),
        str(request_json),
    ]
    plan_result = extract_structured_result(
        final_output or output_text,
        "PLAN_QUEUE_RESULT_BEGIN",
        "PLAN_QUEUE_RESULT_END",
    )
    generated_items = []
    if isinstance(plan_result, dict):
        generated_items = append_generated_queue_items(
            list(plan_result.get("generated_items") or [])
        )

    if process.returncode == 0:
        summary = clip(
            str((plan_result or {}).get("summary", "") or "").strip()
            or (
                final_output.splitlines()[0]
                if final_output.strip()
                else next(
                    (line.strip() for line in reversed(output_lines) if line.strip()),
                    "Codex 策划已完成。",
                )
            )
        )
        if generated_items:
            summary = clip(f"{summary} 已自动生成 {len(generated_items)} 张后续卡。")
        plan_md.write_text(
            success_markdown(
                title,
                task_id,
                instruction_path,
                warnings,
                final_output or output_text,
                output_heading="Codex 策划输出",
            ),
            encoding="utf-8",
        )
        final_instruction_path = finalize_completed_instruction(route, item_id, instruction_path)
        set_route_item_state(
            route,
            route_state,
            item_id,
            status="completed",
            progress_percent=100,
            summary=summary,
            finished_at=finished_at,
            artifact_paths=artifact_paths,
            error="",
            pipeline_summary="Codex plan completed",
            result_excerpt=clip(final_output or output_text, 280),
            instruction_path=final_instruction_path,
        )
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="completed",
            progress_percent=100,
            instruction_path=final_instruction_path,
            executor="codex",
            artifact_path=str(plan_md),
            summary=summary,
            started_at=started_at,
            finished_at=finished_at,
        )
        # 写入 daily memory 记录
        append_to_daily_memory(
            title=title,
            root_task_id=task_id,
            queue_item_id=item_id,
            stage=stage,
            instruction_path=final_instruction_path,
            summary=summary,
            warnings=warnings,
            status="completed",
        )
    else:
        error = clip(
            next(
                (line.strip() for line in reversed(output_lines) if line.strip()),
                f"Codex 退出码 {process.returncode}",
            )
        )
        plan_md.write_text(
            failure_markdown(
                title,
                task_id,
                instruction_path,
                error,
                warnings,
                clip(final_output or output_text, 3000),
            ),
            encoding="utf-8",
        )
        set_route_item_state(
            route,
            route_state,
            item_id,
            status="failed",
            progress_percent=100,
            summary=error,
            error=error,
            finished_at=finished_at,
            artifact_paths=artifact_paths,
            pipeline_summary="Codex plan failed",
            result_excerpt=clip(final_output or output_text, 280),
        )
        set_task_status(
            task_id,
            title=title,
            queue_item_id=item_id,
            stage=stage,
            status="failed",
            progress_percent=100,
            instruction_path=instruction_path,
            executor="codex",
            artifact_path=str(plan_md),
            summary=error,
            error=error,
            started_at=started_at,
            finished_at=finished_at,
        )
        # 写入 daily memory 记录
        append_to_daily_memory(
            title=title,
            root_task_id=task_id,
            queue_item_id=item_id,
            stage=stage,
            instruction_path=instruction_path,
            summary=error,
            warnings=warnings,
            status="failed",
        )


def execute_item(route: dict[str, Any], item: dict[str, Any]) -> None:
    # Record task start metric
    try:
        queue_id = route.get("queue_id") or route.get("route_id") or "unknown"
        item_id = str(item.get("id", "") or "")
        record_performance_metric(
            dimension="CONCURRENCY",
            value=1.0,
            labels={"queue_id": queue_id, "item_id": item_id},
            metadata={"action": "start"},
        )
    except Exception:
        pass

    runner_mode = route_runner_mode(route)
    if runner_mode == "opencode_build":
        execute_build_item(route, item)
        return
    if runner_mode in {"codex_plan", "manual_plan"}:
        execute_plan_item(route, item)
        return
    if runner_mode in {"codex_review", "manual_review"}:
        execute_review_item(route, item)
        return
    raise ValueError(f"unsupported runner_mode: {runner_mode}")


def append_to_daily_memory(
    title: str,
    root_task_id: str,
    queue_item_id: str,
    stage: str,
    instruction_path: str,
    summary: str,
    warnings: list[str],
    status: str,
) -> None:
    """将队列项完成摘要追加到当天的 memory 文件，确保幂等性。

    如果同一条 queue_item_id 当天已存在记录，则跳过写入。
    """
    from datetime import datetime

    memory_dir = RUNTIME_ROOT / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    memory_file = memory_dir / f"{today}.md"

    # 检查是否已存在相同 queue_item_id 的记录
    if memory_file.exists():
        content = memory_file.read_text(encoding="utf-8")
        if f"queue_item_id：{queue_item_id}" in content:
            return  # 已存在，幂等跳过

    # 构建 memory 条目
    warning_text = "\n".join(f"- {warning}" for warning in warnings) if warnings else "- 无"
    entry = f"""## {title} 任务完成

- 状态：{status}
- root_task_id：{root_task_id}
- queue_item_id：{queue_item_id}
- 阶段：{stage}
- 说明文档：{instruction_path}
- 摘要：{summary}
- 预检提醒：
{warning_text}

"""
    # 追加到文件
    with memory_file.open("a", encoding="utf-8") as f:
        f.write(entry)

    # 如果任务完成，尝试蒸馏回流
    if status == "completed":
        try:
            # 延迟导入，避免循环依赖
            from distill_completed import distill_entry

            entry_dict = {
                "title": title,
                "root_task_id": root_task_id,
                "queue_item_id": queue_item_id,
                "stage": stage,
                "instruction_path": instruction_path,
                "summary": summary,
                "status": status,
                "warnings": warnings,
            }
            result = distill_entry(entry_dict)
            if result.get("should_distill"):
                generated = result.get("generated", [])
                if generated:
                    # 可选：记录蒸馏结果到日志
                    pass
        except Exception:
            # 蒸馏失败不应影响主流程
            import traceback

            traceback.print_exc()


def queue_route_by_mode(runner_mode: str) -> dict[str, Any] | None:
    config = load_plan_config()
    for route in config.get("routes", []):
        if route_runner_mode(route) == runner_mode:
            return route
    return None


def detect_and_cleanup_stale_runs(routes: list[dict[str, Any]]) -> None:
    """Identify queue items that are running but have no alive runner or progress.

    This function checks for:
    1. Items with status=running but no recent heartbeat.
    2. Items where the associated task has no artifact and no recent updates.
    3. Items where the runner process is dead (PID check).

    Such items are marked as failed with a clear stale/orphan reason.
    """
    import sys

    print(
        f"[debug] detect_and_cleanup_stale_runs called with {len(routes)} routes",
        file=sys.stderr,
    )
    for route in routes:
        route_state = load_route_state(route)
        items = route_state.get("items") or {}
        for item_id, state_item in items.items():
            status = str(state_item.get("status", ""))
            if status != "running":
                continue

            # Check heartbeat if present
            runner_heartbeat_at = state_item.get("runner_heartbeat_at")
            if runner_heartbeat_at:
                try:
                    heartbeat_time = datetime.fromisoformat(
                        runner_heartbeat_at.replace("Z", "+00:00")
                    )
                    if heartbeat_time.tzinfo is None:
                        heartbeat_time = heartbeat_time.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    delta = (now - heartbeat_time).total_seconds()
                    if delta > HEARTBEAT_TIMEOUT_SECONDS:
                        mark_stale_failed(
                            route,
                            route_state,
                            item_id,
                            state_item,
                            f"runner heartbeat missing for {int(delta)}s",
                        )
                        continue
                except Exception:
                    pass

            # Check task staleness based on updated_at
            updated_at = state_item.get("updated_at")
            if updated_at:
                try:
                    update_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    if update_time.tzinfo is None:
                        update_time = update_time.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    delta = (now - update_time).total_seconds()
                    if delta > STALE_TASK_TIMEOUT_SECONDS:
                        mark_stale_failed(
                            route,
                            route_state,
                            item_id,
                            state_item,
                            f"task has no progress for {int(delta)}s",
                        )
                        continue
                except Exception:
                    pass

            # Check started_at age when no heartbeat present
            if not runner_heartbeat_at:
                started_at = state_item.get("started_at")
                if started_at:
                    try:
                        # Parse ISO timestamp, convert to UTC
                        start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                        if start_time.tzinfo is None:
                            start_time = start_time.replace(tzinfo=timezone.utc)
                        else:
                            start_time = start_time.astimezone(timezone.utc)
                        now = datetime.now(timezone.utc)
                        delta = (now - start_time).total_seconds()
                        if delta > STALE_TASK_TIMEOUT_SECONDS:
                            mark_stale_failed(
                                route,
                                route_state,
                                item_id,
                                state_item,
                                f"task started {int(delta)}s ago with no heartbeat",
                            )
                            continue
                    except Exception:
                        # If parsing fails, ignore this check
                        pass

            # Check if runner process is dead
            runner_pid_raw = state_item.get("runner_pid")
            if runner_pid_raw:
                try:
                    runner_pid = int(runner_pid_raw)
                    if not is_pid_alive(runner_pid):
                        # 检查任务是否在启动宽限期内
                        started_at = state_item.get("started_at")
                        if started_at:
                            try:
                                start_time = datetime.fromisoformat(
                                    started_at.replace("Z", "+00:00")
                                )
                                if start_time.tzinfo is None:
                                    start_time = start_time.replace(tzinfo=timezone.utc)
                                time_since_start = datetime.now(timezone.utc) - start_time
                                # 如果在30秒启动宽限期内，不要标记为失败（从120秒优化）
                                if time_since_start.total_seconds() < 30:
                                    continue
                            except Exception:
                                # 如果时间解析失败，继续正常处理
                                pass

                        mark_stale_failed(
                            route,
                            route_state,
                            item_id,
                            state_item,
                            f"runner process {runner_pid} is dead",
                        )
                        continue
                except (ValueError, TypeError):
                    pass


def maybe_mark_restarted_runs_failed(routes: list[dict[str, Any]]) -> None:
    STARTUP_GRACE_PERIOD_SECONDS = 30  # 任务启动宽限期从120秒优化到30秒

    for route in routes:
        route_state = load_route_state(route)
        for current_item_id in active_route_item_ids(route_state):
            state_item = (route_state.get("items") or {}).get(current_item_id) or {}
            if str(state_item.get("status", "")) != "running":
                continue

            # 检查任务是否在启动宽限期内
            started_at = state_item.get("started_at")
            if started_at:
                try:
                    start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    time_since_start = datetime.now(timezone.utc) - start_time
                    # 如果在启动宽限期内，不要标记为失败
                    if time_since_start.total_seconds() < STARTUP_GRACE_PERIOD_SECONDS:
                        continue
                except Exception:
                    # 如果时间解析失败，继续正常检查
                    pass

            runner_pid = state_item.get("runner_pid")
            try:
                runner_pid_int = int(runner_pid)
            except Exception:
                runner_pid_int = None
            if is_pid_alive(runner_pid_int):
                continue
            root_task_id = str(state_item.get("root_task_id", "") or "")
            summary = "runner 重启恢复：未发现存活执行进程，已标记 failed，等待后续重试。"
            set_route_item_state(
                route,
                route_state,
                current_item_id,
                status="failed",
                summary=summary,
                error=summary,
                finished_at=now_iso(),
                progress_percent=100,
            )
            remove_route_current_item(route, current_item_id)
            if root_task_id:
                set_task_status(
                    root_task_id,
                    title=str(state_item.get("title", current_item_id) or current_item_id),
                    queue_item_id=current_item_id,
                    stage=str(state_item.get("stage", "build") or "build"),
                    status="failed",
                    progress_percent=100,
                    instruction_path=str(state_item.get("instruction_path", "") or ""),
                    artifact_path=(state_item.get("artifact_paths") or [""])[0],
                    summary=summary,
                    error=summary,
                    started_at=str(state_item.get("started_at", "") or ""),
                    finished_at=now_iso(),
                )


def load_dependency_state_index() -> dict[str, dict[str, Any]]:
    dependency_index: dict[str, dict[str, Any]] = {}
    config = load_plan_config()
    for route in config.get("routes", []):
        route_state = load_route_state(route)
        for item_id, state_item in (route_state.get("items") or {}).items():
            dependency_index[str(item_id)] = state_item if isinstance(state_item, dict) else {}
    return dependency_index


def choose_next_item(
    route: dict[str, Any],
    route_state: dict[str, Any],
    accepted_runner_modes: set[str] | tuple[str, ...] | None = None,
) -> dict[str, Any] | None:
    if not route_matches_runner_modes(route, accepted_runner_modes):
        return None
    items_state = route_state.get("items") or {}
    dependency_index = load_dependency_state_index()
    for item in load_manifest_items(route):
        item_id = str(item.get("id", "") or "")
        state_status = str((items_state.get(item_id) or {}).get("status", "") or "pending")
        if state_status in {"", "pending"}:
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            manual_override_autostart = bool(
                (items_state.get(item_id) or {}).get("manual_override_autostart")
            )
            if metadata.get("autostart") is False and not manual_override_autostart:
                continue
            depends_on = (
                metadata.get("depends_on") if isinstance(metadata.get("depends_on"), list) else []
            )
            blocked = False
            for dep_id in depends_on:
                dep_state = items_state.get(str(dep_id)) or dependency_index.get(str(dep_id)) or {}
                if str(dep_state.get("status", "")) != "completed":
                    blocked = True
                    break
            if blocked:
                continue
            return item
    return None


def finalize_completed_instruction(
    route: dict[str, Any],
    item_id: str,
    instruction_path: str,
) -> str:
    archived_path = archive_instruction_path_if_needed(instruction_path)
    if archived_path != instruction_path:
        set_route_item_state(
            route,
            load_route_state(route),
            item_id,
            instruction_path=archived_path,
        )
        update_manifest_instruction_path(route, item_id, archived_path)
    return archived_path


def archive_existing_completed_instructions(
    routes: list[dict[str, Any]],
) -> list[str]:
    archived_items: list[str] = []
    for route in routes:
        route_state = load_route_state(route)
        items_state = route_state.get("items") or {}
        for manifest_item in load_manifest_items(route):
            item_id = str(manifest_item.get("id", "") or "")
            state_item = items_state.get(item_id) or {}
            if str(state_item.get("status", "") or "") != "completed":
                continue
            current_path = str(
                state_item.get("instruction_path") or manifest_item.get("instruction_path") or ""
            ).strip()
            if not current_path:
                continue
            archived_path = finalize_completed_instruction(route, item_id, current_path)
            if archived_path != current_path:
                archived_items.append(item_id)
    return archived_items
