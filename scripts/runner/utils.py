#!/usr/bin/env python3
"""utils"""

from __future__ import annotations

import logging
import os
import sys
import time
import json
import re
import shutil
import signal
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
        PLAN_CONFIG_PATH,
        PLAN_DIR,
        QUEUE_STATE_DIR,
        RUNTIME_ROOT,
        TASKS_DIR,
        TASKS_PATH,
        pid_file,
    )


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z]+", "-", value).strip("-").lower()
    return slug or "task"


_ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def clip(value: str, limit: int = 240) -> str:
    text = " ".join(_ANSI_RE.sub("", str(value or "")).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_referenced_paths(text: str) -> list[str]:
    candidates = re.findall(r"/Volumes/1TB-M2[^`\n]+", text or "")
    cleaned: list[str] = []
    for raw in candidates:
        path = raw.strip().strip(")>,.;:'\"")
        if path and path not in cleaned:
            cleaned.append(path)
    return cleaned


def is_pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def terminate_process_tree(process: subprocess.Popen[str], grace_seconds: int = 8) -> None:
    try:
        pgid = os.getpgid(process.pid)
    except Exception:
        pgid = None

    try:
        if pgid is not None:
            os.killpg(pgid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        return
    except Exception:
        try:
            process.terminate()
        except Exception:
            return

    try:
        process.wait(timeout=grace_seconds)
        return
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        return

    try:
        if pgid is not None:
            os.killpg(pgid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        return
    except Exception:
        try:
            process.kill()
        except Exception:
            return

    try:
        process.wait(timeout=2)
    except Exception:
        pass


def terminate_pid_tree(pid: int | None, grace_seconds: int = 8) -> None:
    if not pid:
        return
    try:
        pgid = os.getpgid(pid)
    except Exception:
        pgid = None

    try:
        if pgid is not None:
            os.killpg(pgid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            return

    deadline = time.time() + max(grace_seconds, 1)
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        except Exception:
            break
        time.sleep(0.2)

    try:
        if pgid is not None:
            os.killpg(pgid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            return


def is_instruction_under_plan_dir(path: Path) -> bool:
    try:
        resolved = path.resolve()
        plan_root = PLAN_DIR.resolve()
    except FileNotFoundError:
        return False
    return resolved == plan_root or plan_root in resolved.parents


def system_free_memory_percent() -> int | None:
    return resource_facts.system_free_memory_percent()


def system_load_average() -> tuple[float, float, float] | None:
    return resource_facts.system_load_average()


def ollama_active_cpu_percent() -> float:
    return resource_facts.ollama_active_cpu_percent()


def extract_structured_result(
    text: str, begin_marker: str, end_marker: str
) -> dict[str, Any] | None:
    if not text.strip():
        return None
    pattern = re.compile(
        re.escape(begin_marker) + r"\s*(\{.*?\})\s*" + re.escape(end_marker),
        re.DOTALL,
    )
    match = pattern.search(text)
    blob = ""
    if match:
        blob = match.group(1)
    else:
        fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            blob = fenced.group(1)
    if not blob:
        return None
    try:
        parsed = json.loads(blob)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def codex_executable() -> str:
    discovered = shutil.which("codex")
    if discovered:
        return discovered
    if CODEX_APP_PATH.exists():
        return str(CODEX_APP_PATH)
    return ""


def resource_gate_message() -> str:
    free_memory = system_free_memory_percent()
    if free_memory is not None and free_memory < MIN_FREE_MEMORY_PERCENT:
        return f"资源门限暂停：系统可用内存约 {free_memory}% ，低于启动自动任务的安全阈值 {MIN_FREE_MEMORY_PERCENT}% 。"
    return ""


def dynamic_build_worker_budget() -> tuple[int, dict[str, Any]]:
    return resource_facts.dynamic_build_worker_budget(
        max_build_workers=MAX_BUILD_WORKERS,
        second_build_min_free_memory_percent=SECOND_BUILD_MIN_FREE_MEMORY_PERCENT,
        max_build_load_per_core=MAX_BUILD_LOAD_PER_CORE,
        max_build_load_absolute=MAX_BUILD_LOAD_ABSOLUTE,
        ollama_busy_cpu_percent=OLLAMA_BUSY_CPU_PERCENT,
    )


def root_task_id_for(item: dict[str, Any], stage: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{stage}-{slugify(str(item.get('title', item.get('id', 'task'))))[:48]}"
