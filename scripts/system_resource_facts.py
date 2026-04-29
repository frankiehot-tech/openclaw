#!/usr/bin/env python3
"""Unified local system resource facts for Athena and TenacitOS.

Single-source probe for:
- CPU usage from macOS `top`
- load average from `os.getloadavg`
- memory pressure from macOS `memory_pressure`
- Ollama CPU activity from `ps`
- build worker budget parity with athena_ai_plan_runner
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime
from typing import Any

TOP_CPU_RE = re.compile(
    r"CPU usage:\s+([0-9.]+)% user,\s+([0-9.]+)% sys,\s+([0-9.]+)% idle",
    re.IGNORECASE,
)
TOP_MEM_RE = re.compile(
    r"PhysMem:\s+([0-9.]+[KMGTP]) used(?:\s+\(([^)]*)\))?,\s+([0-9.]+[KMGTP]) unused\.",
    re.IGNORECASE,
)
MEMORY_HEADER_RE = re.compile(
    r"The system has\s+(\d+).+page size of\s+(\d+)\)\.",
    re.IGNORECASE,
)
FREE_PERCENT_RE = re.compile(
    r"System-wide memory free percentage:\s+(\d+)%",
    re.IGNORECASE,
)
VM_STAT_PAGE_SIZE_RE = re.compile(
    r"page size of\s+(\d+)\s+bytes",
    re.IGNORECASE,
)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def round_gb(value: float) -> float:
    return round(value / 1024 / 1024 / 1024, 2)


def size_token_to_bytes(token: str) -> int:
    token = token.strip().upper()
    match = re.match(r"([0-9.]+)\s*([KMGTP])", token)
    if not match:
        return 0
    value = float(match.group(1))
    unit = match.group(2)
    multipliers = {
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
        "P": 1024**5,
    }
    return int(value * multipliers[unit])


def _run_text(command: list[str]) -> str:
    return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL)


def top_snapshot() -> dict[str, Any]:
    try:
        output = _run_text(["top", "-l", "1", "-n", "0"])
    except Exception:
        return {
            "user_percent": 0.0,
            "system_percent": 0.0,
            "idle_percent": 0.0,
            "usage_percent": 0.0,
            "top_used_gb": 0.0,
            "top_unused_gb": 0.0,
            "wired_gb": 0.0,
            "compressor_gb": 0.0,
            "source": "top",
        }

    cpu_user = cpu_system = cpu_idle = 0.0
    cpu_match = TOP_CPU_RE.search(output)
    if cpu_match:
        cpu_user = float(cpu_match.group(1))
        cpu_system = float(cpu_match.group(2))
        cpu_idle = float(cpu_match.group(3))

    top_used = top_unused = wired = compressor = 0
    mem_match = TOP_MEM_RE.search(output)
    if mem_match:
        top_used = size_token_to_bytes(mem_match.group(1))
        top_unused = size_token_to_bytes(mem_match.group(3))
        details = mem_match.group(2) or ""
        for chunk in details.split(","):
            part = chunk.strip()
            if not part:
                continue
            if "wired" in part.lower():
                wired = size_token_to_bytes(part.split()[0])
            elif "compressor" in part.lower():
                compressor = size_token_to_bytes(part.split()[0])

    return {
        "user_percent": round(cpu_user, 2),
        "system_percent": round(cpu_system, 2),
        "idle_percent": round(cpu_idle, 2),
        "usage_percent": round(max(0.0, 100.0 - cpu_idle), 2),
        "top_used_gb": round_gb(top_used),
        "top_unused_gb": round_gb(top_unused),
        "wired_gb": round_gb(wired),
        "compressor_gb": round_gb(compressor),
        "source": "top",
    }


def _page_metric(stdout: str, label: str) -> int:
    match = re.search(rf"{label}:\s+([\d,]+)", stdout, re.IGNORECASE)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def vm_stat_snapshot() -> dict[str, Any]:
    try:
        output = _run_text(["vm_stat"])
    except Exception:
        return {
            "page_size": 0,
            "free_gb": 0.0,
            "active_gb": 0.0,
            "inactive_gb": 0.0,
            "speculative_gb": 0.0,
            "wired_gb": 0.0,
            "purgeable_gb": 0.0,
            "file_backed_gb": 0.0,
            "anonymous_gb": 0.0,
            "compressed_gb": 0.0,
            "activity_monitor_app_gb": 0.0,
            "activity_monitor_used_gb": 0.0,
            "source": "vm_stat",
            "note": "vm_stat unavailable",
        }

    page_size_match = VM_STAT_PAGE_SIZE_RE.search(output)
    page_size = int(page_size_match.group(1)) if page_size_match else 4096

    free_pages = _page_metric(output, "Pages free")
    active_pages = _page_metric(output, "Pages active")
    inactive_pages = _page_metric(output, "Pages inactive")
    speculative_pages = _page_metric(output, "Pages speculative")
    wired_pages = _page_metric(output, "Pages wired down")
    purgeable_pages = _page_metric(output, "Pages purgeable")
    file_backed_pages = _page_metric(output, "File-backed pages")
    anonymous_pages = _page_metric(output, "Anonymous pages")
    compressed_pages = _page_metric(output, "Pages occupied by compressor") or _page_metric(
        output, "Pages used by compressor"
    )

    activity_monitor_app_bytes = (anonymous_pages + purgeable_pages) * page_size
    activity_monitor_used_bytes = (
        anonymous_pages + purgeable_pages + wired_pages + compressed_pages
    ) * page_size

    return {
        "page_size": page_size,
        "free_gb": round_gb(free_pages * page_size),
        "active_gb": round_gb(active_pages * page_size),
        "inactive_gb": round_gb(inactive_pages * page_size),
        "speculative_gb": round_gb(speculative_pages * page_size),
        "wired_gb": round_gb(wired_pages * page_size),
        "purgeable_gb": round_gb(purgeable_pages * page_size),
        "file_backed_gb": round_gb(file_backed_pages * page_size),
        "anonymous_gb": round_gb(anonymous_pages * page_size),
        "compressed_gb": round_gb(compressed_pages * page_size),
        "activity_monitor_app_gb": round_gb(activity_monitor_app_bytes),
        "activity_monitor_used_gb": round_gb(activity_monitor_used_bytes),
        "source": "vm_stat",
        "note": "Activity Monitor estimate from vm_stat anonymous + purgeable + wired + compressed",
    }


def memory_pressure_snapshot() -> dict[str, Any]:
    try:
        output = _run_text(["memory_pressure"])
    except Exception:
        return {
            "total_gb": (
                round_gb(float(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")))
                if hasattr(os, "sysconf")
                else 0.0
            ),
            "pressure_free_percent": None,
            "pressure_used_percent": None,
            "available_gb": 0.0,
            "cached_gb": 0.0,
            "reclaimable_gb": 0.0,
            "app_gb": 0.0,
            "compressed_gb": 0.0,
            "source": "memory_pressure",
            "note": "memory_pressure unavailable",
        }

    header_match = MEMORY_HEADER_RE.search(output)
    free_percent_match = FREE_PERCENT_RE.search(output)
    if not header_match or not free_percent_match:
        return {
            "total_gb": 0.0,
            "pressure_free_percent": None,
            "pressure_used_percent": None,
            "available_gb": 0.0,
            "cached_gb": 0.0,
            "reclaimable_gb": 0.0,
            "app_gb": 0.0,
            "compressed_gb": 0.0,
            "source": "memory_pressure",
            "note": "memory_pressure parse failed",
        }

    total_bytes = int(header_match.group(1))
    page_size = int(header_match.group(2))
    pressure_free_percent = max(0, min(100, int(free_percent_match.group(1))))
    pressure_used_percent = 100 - pressure_free_percent

    free_pages = _page_metric(output, "Pages free")
    purgeable_pages = _page_metric(output, "Pages purgeable")
    speculative_pages = _page_metric(output, "Pages speculative")
    inactive_pages = _page_metric(output, "Pages inactive")
    active_pages = _page_metric(output, "Pages active")
    wired_pages = _page_metric(output, "Pages wired down")
    compressed_pages = _page_metric(output, "Pages occupied by compressor") or _page_metric(
        output, "Pages used by compressor"
    )

    available_bytes = total_bytes * (pressure_free_percent / 100)
    reclaimable_bytes = (free_pages + purgeable_pages + speculative_pages) * page_size
    cache_like_bytes = (purgeable_pages + speculative_pages + inactive_pages) * page_size
    app_bytes = (active_pages + wired_pages + compressed_pages) * page_size
    compressed_bytes = compressed_pages * page_size

    return {
        "total_gb": round_gb(total_bytes),
        "pressure_free_percent": pressure_free_percent,
        "pressure_used_percent": pressure_used_percent,
        "available_gb": round_gb(available_bytes),
        "cached_gb": round_gb(cache_like_bytes),
        "reclaimable_gb": round_gb(reclaimable_bytes),
        "app_gb": round_gb(app_bytes),
        "compressed_gb": round_gb(compressed_bytes),
        "source": "memory_pressure",
        "note": "Pressure-based estimate from macOS memory_pressure",
    }


def system_free_memory_percent() -> int | None:
    value = memory_pressure_snapshot().get("pressure_free_percent")
    if value is None:
        return None
    return int(value)


def system_load_average() -> tuple[float, float, float] | None:
    try:
        load = os.getloadavg()
        return float(load[0]), float(load[1]), float(load[2])
    except Exception:
        return None


def ollama_active_cpu_percent() -> float:
    try:
        output = _run_text(["ps", "-axo", "comm=,pcpu="])
    except Exception:
        return 0.0

    total = 0.0
    for line in output.splitlines():
        parts = line.strip().rsplit(None, 1)
        if len(parts) != 2:
            continue
        command, cpu_text = parts
        if "ollama" not in command.lower():
            continue
        try:
            total += float(cpu_text)
        except ValueError:
            continue
    return round(total, 1)


def dynamic_build_worker_budget(
    *,
    max_build_workers: int,
    second_build_min_free_memory_percent: int,
    max_build_load_per_core: float,
    max_build_load_absolute: float,
    ollama_busy_cpu_percent: float,
) -> tuple[int, dict[str, Any]]:
    cpu_count = max(1, int(os.cpu_count() or 1))
    free_memory = system_free_memory_percent()
    load_avg = system_load_average()
    ollama_cpu = ollama_active_cpu_percent()
    max_load = min(max_build_load_absolute, cpu_count * max_build_load_per_core)

    budget = 1
    reason = "默认单 worker。"
    if max_build_workers <= 1:
        reason = "已通过配置固定为单 worker。"
    elif free_memory is not None and free_memory < second_build_min_free_memory_percent:
        reason = (
            f"可用内存约 {free_memory}% ，低于双 worker 阈值 "
            f"{second_build_min_free_memory_percent}% 。"
        )
    elif load_avg is not None and load_avg[0] > max_load:
        reason = f"1 分钟 load={load_avg[0]:.2f} ，高于双 worker 阈值 {max_load:.2f} 。"
    elif ollama_cpu >= ollama_busy_cpu_percent:
        reason = f"Ollama 活跃 CPU≈{ollama_cpu:.1f}% ，高于阈值 {ollama_busy_cpu_percent:.1f}% 。"
    else:
        budget = min(2, max_build_workers)
        reason = "load / memory / ollama 均在安全区间，启用双 worker。"

    telemetry = {
        "budget": budget,
        "cpu_count": cpu_count,
        "free_memory_percent": free_memory,
        "load_average_1m": load_avg[0] if load_avg else None,
        "load_average_5m": load_avg[1] if load_avg else None,
        "load_average_15m": load_avg[2] if load_avg else None,
        "ollama_cpu_percent": ollama_cpu,
        "reason": reason,
        "second_build_min_free_memory_percent": second_build_min_free_memory_percent,
        "max_build_workers": max_build_workers,
        "max_build_load_per_core": max_build_load_per_core,
        "max_build_load_absolute": max_build_load_absolute,
        "ollama_busy_cpu_percent": ollama_busy_cpu_percent,
    }
    return budget, telemetry


def collect_resource_facts() -> dict[str, Any]:
    top = top_snapshot()
    pressure = memory_pressure_snapshot()
    vm_stats = vm_stat_snapshot()
    load_avg = system_load_average() or (0.0, 0.0, 0.0)
    cpu_count = max(1, int(os.cpu_count() or 1))
    _, runner = dynamic_build_worker_budget(
        max_build_workers=max(1, int(os.getenv("ATHENA_AI_PLAN_MAX_BUILD_WORKERS", "2"))),
        second_build_min_free_memory_percent=int(
            os.getenv("ATHENA_AI_PLAN_SECOND_BUILD_MIN_FREE_MEMORY_PERCENT", "40")
        ),
        max_build_load_per_core=float(os.getenv("ATHENA_AI_PLAN_MAX_BUILD_LOAD_PER_CORE", "0.6")),
        max_build_load_absolute=float(os.getenv("ATHENA_AI_PLAN_MAX_BUILD_LOAD_ABSOLUTE", "6.0")),
        ollama_busy_cpu_percent=float(os.getenv("ATHENA_AI_PLAN_OLLAMA_BUSY_CPU_PERCENT", "35")),
    )

    return {
        "sampled_at": now_iso(),
        "sources": {
            "cpu": "top -l 1 -n 0",
            "memory_top": "top -l 1 -n 0",
            "memory_pressure": "memory_pressure",
            "memory_vm_stat": "vm_stat",
            "load_average": "os.getloadavg",
            "ollama_cpu": "ps -axo comm=,pcpu=",
            "runner_budget": "athena_ai_plan_runner parity",
        },
        "cpu": {
            "usage_percent": top["usage_percent"],
            "user_percent": top["user_percent"],
            "system_percent": top["system_percent"],
            "idle_percent": top["idle_percent"],
            "load_average": [round(load_avg[0], 3), round(load_avg[1], 3), round(load_avg[2], 3)],
            "core_count": cpu_count,
        },
        "memory": {
            "total_gb": pressure["total_gb"],
            "pressure_free_percent": pressure["pressure_free_percent"],
            "pressure_used_percent": pressure["pressure_used_percent"],
            "available_gb": pressure["available_gb"],
            "cached_gb": pressure["cached_gb"],
            "reclaimable_gb": pressure["reclaimable_gb"],
            "app_gb": pressure["app_gb"],
            "compressed_gb": pressure["compressed_gb"],
            "top_used_gb": top["top_used_gb"],
            "top_unused_gb": top["top_unused_gb"],
            "wired_gb": vm_stats["wired_gb"] or top["wired_gb"],
            "compressor_gb": vm_stats["compressed_gb"] or top["compressor_gb"],
            "activity_monitor_app_gb": vm_stats["activity_monitor_app_gb"],
            "activity_monitor_used_gb": vm_stats["activity_monitor_used_gb"],
            "anonymous_gb": vm_stats["anonymous_gb"],
            "purgeable_gb": vm_stats["purgeable_gb"],
            "file_backed_gb": vm_stats["file_backed_gb"],
            "inactive_gb": vm_stats["inactive_gb"],
            "note": f"{pressure['note']}; {vm_stats['note']}",
        },
        "runner": runner,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Emit JSON facts")
    args = parser.parse_args()
    payload = collect_resource_facts()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
