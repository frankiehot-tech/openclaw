#!/usr/bin/env python3
"""OpenHuman 24h stress runner.

Launches a safe, local-first 24 hour soak test for Athena/Open Human.
The runner is intentionally non-destructive for a live workstation:
- no process killing
- no network partition injection
- no config mutation outside this runner's own output paths

It continuously collects:
- system resource facts
- queue state snapshots
- stability metrics
- performance monitor outputs
- AutoResearch dry-run cycles

It also keeps a live markdown report inside AIplan so the human can read the
current state without digging through workspace artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from . import system_resource_facts
    from .openclaw_roots import PLAN_DIR, QUEUE_STATE_DIR, RUNTIME_ROOT, pid_file
except ImportError:
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import system_resource_facts
    from openclaw_roots import PLAN_DIR, QUEUE_STATE_DIR, RUNTIME_ROOT, pid_file


STOP_REQUESTED = False

DEFAULT_REPORT_PATH = PLAN_DIR / "OpenHuman-Athena-24小时压力测试执行报告.md"
DEFAULT_OUTPUT_ROOT = RUNTIME_ROOT / "workspace" / "stress_test"
PID_FILE = pid_file("openhuman_24h_stress_runner")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def signal_handler(signum: int, frame: Any) -> None:
    del signum, frame
    global STOP_REQUESTED
    STOP_REQUESTED = True


def queue_state_paths() -> list[Path]:
    if QUEUE_STATE_DIR.exists():
        return list(QUEUE_STATE_DIR.glob("*.json"))
    fallback = [
        RUNTIME_ROOT / ".openclaw" / "plan_queue" / "openhuman_aiplan_build_priority_20260328.json",
        RUNTIME_ROOT / ".openclaw" / "plan_queue" / "openhuman_aiplan_codex_audit_20260328.json",
        RUNTIME_ROOT / ".openclaw" / "plan_queue" / "openhuman_aiplan_plan_manual_20260328.json",
    ]
    return [p for p in fallback if p.exists()]


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def top_memory_processes(limit: int = 8) -> list[dict[str, Any]]:
    cmd = [
        "ps",
        "-ax",
        "-o",
        "pid,%cpu,%mem,rss,command",
    ]
    run = subprocess.run(cmd, capture_output=True, text=True, check=False)
    lines = run.stdout.splitlines()[1:]
    records: list[dict[str, Any]] = []
    for raw in lines:
        parts = raw.strip().split(None, 4)
        if len(parts) < 5:
            continue
        pid, cpu, mem, rss, command = parts
        try:
            records.append(
                {
                    "pid": int(pid),
                    "cpu_percent": float(cpu),
                    "mem_percent": float(mem),
                    "rss_mb": round(int(rss) / 1024, 1),
                    "command": command,
                }
            )
        except Exception:
            continue
    records.sort(key=lambda item: item["rss_mb"], reverse=True)
    return records[:limit]


def determine_phase(elapsed_seconds: float, duration_seconds: float) -> dict[str, Any]:
    ratio = 0.0 if duration_seconds <= 0 else elapsed_seconds / duration_seconds
    checkpoints = [
        (
            2 / 24,
            {
                "name": "预热阶段（0-2小时）",
                "load_strength": "20%",
                "goal": "基础功能验证、系统启动稳定性",
            },
        ),
        (
            4 / 24,
            {
                "name": "负载提升阶段（2-4小时）",
                "load_strength": "50%-100%",
                "goal": "系统扩展性、资源使用效率",
            },
        ),
        (
            20 / 24,
            {
                "name": "稳定运行阶段（4-20小时）",
                "load_strength": "100%",
                "goal": "长时间稳定性、资源泄漏、性能衰减",
            },
        ),
        (
            22 / 24,
            {
                "name": "峰值压力阶段（20-22小时）",
                "load_strength": "150%",
                "goal": "极限能力、故障恢复速度",
            },
        ),
        (
            1.1,
            {
                "name": "冷却阶段（22-24小时）",
                "load_strength": "20%",
                "goal": "系统恢复能力、资源释放",
            },
        ),
    ]
    for boundary, payload in checkpoints:
        if ratio < boundary:
            return payload
    return checkpoints[-1][1]


def queue_summary() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in queue_state_paths():
        state = read_json(path, default={})
        if not state:
            continue
        rows.append(
            {
                "queue": state.get("name") or path.stem,
                "queue_status": state.get("queue_status", "unknown"),
                "counts": state.get("counts", {}),
                "current_item_ids": state.get("current_item_ids", []),
            }
        )
    return rows


def run_subprocess(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env,
            check=False,
            timeout=timeout,
        )
        returncode = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
        timed_out = False
    except subprocess.TimeoutExpired:
        returncode = -1
        stdout = ""
        stderr = f"Subprocess timeout after {timeout} seconds"
        timed_out = True
    except Exception as e:
        returncode = -2
        stdout = ""
        stderr = f"Subprocess failed: {e}"
        timed_out = False
    duration = round(time.time() - started, 3)
    return {
        "cmd": cmd,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "duration_seconds": duration,
        "timed_out": timed_out,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass
class StressConfig:
    duration_hours: float
    sample_seconds: int
    performance_seconds: int
    stability_seconds: int
    autoresearch_seconds: int
    report_path: str
    output_root: str


class StressRunner:
    def __init__(self, config: StressConfig):
        self.config = config
        self.duration_seconds = int(config.duration_hours * 3600)
        self.started_at = time.time()
        self.run_id = f"stress-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.output_dir = Path(config.output_root) / self.run_id
        self.samples_dir = self.output_dir / "samples"
        self.samples_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir = self.output_dir / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.interim_reports_dir = self.output_dir / "interim_reports"
        self.interim_reports_dir.mkdir(parents=True, exist_ok=True)
        self.report_path = Path(config.report_path)
        self.state_path = self.output_dir / "state.json"
        self.events_path = self.output_dir / "events.jsonl"
        self.last_performance = 0.0
        self.last_stability = 0.0
        self.last_autoresearch = 0.0
        self.last_interim_summary = 0.0
        self.latest_performance: dict[str, Any] | None = None
        self.latest_stability: dict[str, Any] | None = None
        self.latest_autoresearch: dict[str, Any] | None = None
        self.checkpoints: list[dict[str, Any]] = []
        self.anomaly_windows: list[dict[str, Any]] = []
        self.recovery_windows: list[dict[str, Any]] = []
        self.current_anomaly: dict[str, Any] | None = None
        self.run_status = "running"
        self.stop_reason = ""
        self.last_error: dict[str, Any] | None = None

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": now_iso(),
            "type": event_type,
            "payload": payload,
        }
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def best_state_profile(self) -> dict[str, Any]:
        facts = system_resource_facts.collect_resource_facts()
        runner = facts.get("runner", {})
        return {
            "sampled_at": facts.get("sampled_at"),
            "machine_profile": "local_m4_safe_mode",
            "recommended_max_build_workers": runner.get("budget", 1),
            "recommended_parallel_model": (
                "2 build workers + existing review/plan consumers"
                if runner.get("budget", 1) >= 2
                else "single build worker"
            ),
            "recommended_changes": [
                "保持 Athena build worker 上限为当前动态预算，不额外手工提并发。",
                "压测期间 AutoResearch 只跑 dry-run，不允许自动应用修改。",
                "压测期间禁用破坏性混沌实验，仅保留安全观测与证据采集。",
            ],
            "resource_snapshot": facts,
            "top_memory_processes": top_memory_processes(),
        }

    def emit_report(self, current_phase: dict[str, Any], is_final: bool = False) -> None:
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        elapsed = int(time.time() - self.started_at)
        latest_resource = read_json(self.output_dir / "latest_resource.json", {})
        queue_rows = queue_summary()
        lines = [
            "# OpenHuman-Athena-24小时压力测试执行报告",
            "",
            f"- run_id: `{self.run_id}`",
            f"- started_at: `{datetime.fromtimestamp(self.started_at).astimezone().isoformat(timespec='seconds')}`",
            f"- elapsed_seconds: `{elapsed}`",
            f"- target_duration_hours: `{self.config.duration_hours}`",
            f"- current_phase: `{current_phase['name']}`",
            f"- phase_load_strength: `{current_phase['load_strength']}`",
            f"- output_dir: `{self.output_dir}`",
            f"- 测试状态: `{self.run_status}`",
            f"- 停止原因: `{self.stop_reason or ('计划完成' if is_final else 'N/A')}`",
            "",
            "## 本地 M4 最佳态",
            "",
            f"- 当前推荐 build 并发: `{latest_resource.get('runner', {}).get('budget', 'unknown')}`",
            f"- CPU usage: `{latest_resource.get('cpu', {}).get('usage_percent', 'unknown')}%`",
            f"- Memory free pressure: `{latest_resource.get('memory', {}).get('pressure_free_percent', 'unknown')}%`",
            f"- Ollama CPU: `{latest_resource.get('runner', {}).get('ollama_cpu_percent', 'unknown')}`",
            "",
            "## 队列状态",
            "",
        ]
        for row in queue_rows:
            lines.append(
                f"- `{row['queue']}`: status=`{row['queue_status']}` counts=`{row['counts']}` current=`{row['current_item_ids']}`"
            )

        if self.latest_stability:
            lines.extend(
                [
                    "",
                    "## 最新稳定性报告",
                    "",
                    f"- returncode: `{self.latest_stability['returncode']}`",
                    f"- report_path: `{self.latest_stability.get('report_path', '')}`",
                ]
            )

        if self.latest_performance:
            lines.extend(
                [
                    "",
                    "## 最新性能报告",
                    "",
                    f"- returncode: `{self.latest_performance['returncode']}`",
                    f"- markdown_path: `{self.latest_performance.get('markdown_path', '')}`",
                ]
            )

        if self.latest_autoresearch:
            lines.extend(
                [
                    "",
                    "## 最新 AutoResearch 轮次",
                    "",
                    f"- returncode: `{self.latest_autoresearch['returncode']}`",
                    f"- summary: `{self.latest_autoresearch.get('summary', '')}`",
                ]
            )

        if self.last_error:
            lines.extend(
                [
                    "",
                    "## 最近错误",
                    "",
                    f"- type: `{self.last_error.get('type', '')}`",
                    f"- message: `{self.last_error.get('message', '')}`",
                ]
            )

        # 异常窗口摘要
        lines.extend(
            [
                "",
                "## 异常窗口摘要",
                "",
            ]
        )
        if self.anomaly_windows:
            for idx, window in enumerate(self.anomaly_windows, 1):
                lines.append(
                    f"- 窗口 {idx}: started_at=`{window.get('started_at')}` ended_at=`{window.get('ended_at', 'ongoing')}` anomalies=`{window.get('anomalies', [])}`"
                )
        else:
            lines.append("- 暂无异常窗口")

        # 恢复表现
        lines.extend(
            [
                "",
                "## 恢复表现",
                "",
            ]
        )
        if self.recovery_windows:
            for idx, recovery in enumerate(self.recovery_windows, 1):
                lines.append(
                    f"- 恢复 {idx}: started_at=`{recovery.get('started_at')}` ended_at=`{recovery.get('ended_at')}` anomalies=`{recovery.get('anomalies', [])}`"
                )
        else:
            lines.append("- 暂无恢复窗口")

        # 未覆盖风险
        lines.extend(
            [
                "",
                "## 未覆盖风险",
                "",
                "- 当前压测仅覆盖本地 M4 安全模式，未模拟网络分区、进程 kill、磁盘满等极端场景。",
                "- 未对 Athena 核心调度器进行故障注入测试。",
                "- 未覆盖多租户并发场景下的资源争用与隔离问题。",
                "",
            ]
        )

        # 最终结论（仅最终报告）
        if is_final:
            lines.extend(
                [
                    "",
                    "## 最终结论",
                    "",
                    f"- 压测总时长: {elapsed} 秒 ({elapsed / 3600:.1f} 小时)",
                    f"- 异常窗口总数: {len(self.anomaly_windows)}",
                    f"- 恢复窗口总数: {len(self.recovery_windows)}",
                    f"- 检查点总数: {len(self.checkpoints)}",
                    "- 结论: 压测执行完成，详细证据见 output_dir 下的样本与事件日志。",
                    "",
                ]
            )

        lines.extend(
            [
                "",
                "## 说明",
                "",
                "- 当前是 live workspace 的安全压测版本，不执行 kill agent / 网络分区 / 配置破坏类混沌实验。",
                "- 24 小时结束后会把最终总结、异常窗口和证据索引回写到本报告。",
                "- 本报告已为 Codex 审计准备，包含异常窗口、恢复表现、未覆盖风险和最终结论章节。",
                "- 详细数据（完整异常窗口、恢复窗口、检查点）见 output_dir 下的 final_state.json 和 state.json。",
                "",
            ]
        )
        self.report_path.write_text("\n".join(lines), encoding="utf-8")

    def collect_resource_sample(self) -> dict[str, Any]:
        try:
            payload = self.best_state_profile()["resource_snapshot"]
        except Exception as e:
            payload = {
                "sampled_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "error": str(e),
                "resource_snapshot_unavailable": True,
            }
            self.log_event("resource_sample_error", {"error": str(e)})
        write_json(self.output_dir / "latest_resource.json", payload)
        sample_path = self.samples_dir / f"resource_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        write_json(sample_path, payload)
        return payload

    def record_checkpoint(self, phase: dict[str, Any], resource_snapshot: dict[str, Any]) -> None:
        anomaly_result = self.detect_anomalies(resource_snapshot)
        checkpoint = {
            "timestamp": now_iso(),
            "phase": phase,
            "resource_snapshot_summary": {
                "cpu_usage_percent": resource_snapshot.get("cpu", {}).get("usage_percent"),
                "memory_pressure_free_percent": resource_snapshot.get("memory", {}).get(
                    "pressure_free_percent"
                ),
                "runner_budget": resource_snapshot.get("runner", {}).get("budget"),
            },
            "anomaly_detected": anomaly_result["count"] > 0,
            "anomalies": anomaly_result["anomalies"],
            "recovery_observed": False,
        }
        self.checkpoints.append(checkpoint)
        self.log_event("checkpoint", checkpoint)
        checkpoint_file = (
            self.checkpoints_dir / f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        write_json(checkpoint_file, checkpoint)
        if anomaly_result["count"] > 0:
            self.handle_anomaly_detection(anomaly_result, phase, resource_snapshot)
        else:
            self.handle_recovery_detection(phase, resource_snapshot)

    def detect_anomalies(self, resource_snapshot: dict[str, Any]) -> dict[str, Any]:
        anomalies = []
        cpu = resource_snapshot.get("cpu", {})
        memory = resource_snapshot.get("memory", {})
        if cpu.get("usage_percent", 0) > 90:
            anomalies.append("cpu_usage_high")
        if memory.get("pressure_free_percent", 100) < 10:
            anomalies.append("memory_pressure_high")
        runner = resource_snapshot.get("runner", {})
        if runner.get("budget", 1) < 1:
            anomalies.append("runner_budget_low")
        return {"anomalies": anomalies, "count": len(anomalies)}

    def handle_anomaly_detection(
        self,
        anomaly_result: dict[str, Any],
        phase: dict[str, Any],
        resource_snapshot: dict[str, Any],
    ) -> None:
        timestamp = now_iso()
        if self.current_anomaly is None:
            self.current_anomaly = {
                "started_at": timestamp,
                "phase": phase["name"],
                "anomalies": anomaly_result["anomalies"],
                "resource_snapshot": resource_snapshot,
            }
            self.log_event("anomaly_window_started", self.current_anomaly)
        else:
            self.current_anomaly["last_observed"] = timestamp
            self.current_anomaly["anomalies"] = list(
                set(self.current_anomaly["anomalies"]) | set(anomaly_result["anomalies"])
            )

    def handle_recovery_detection(
        self, phase: dict[str, Any], resource_snapshot: dict[str, Any]
    ) -> None:
        if self.current_anomaly is not None:
            recovery_window = {
                "started_at": self.current_anomaly["started_at"],
                "ended_at": now_iso(),
                "phase": self.current_anomaly["phase"],
                "anomalies": self.current_anomaly["anomalies"],
                "recovery_phase": phase["name"],
                "resource_snapshot": resource_snapshot,
            }
            self.recovery_windows.append(recovery_window)
            self.log_event("recovery_window_ended", recovery_window)
            self.current_anomaly = None

    def maybe_run_performance_monitor(self) -> None:
        if time.time() - self.last_performance < self.config.performance_seconds:
            return
        self.last_performance = time.time()
        result = run_subprocess(
            ["python3", str(RUNTIME_ROOT / "scripts" / "performance_monitor.py")],
            timeout=60,
        )
        perf_dir = RUNTIME_ROOT / "workspace" / "performance"
        latest_md = ""
        try:
            md_files = sorted(perf_dir.glob("performance_report_*.md"))
            latest_md = str(md_files[-1]) if md_files else ""
        except Exception:
            latest_md = ""
        result["markdown_path"] = latest_md
        self.latest_performance = result
        self.log_event("performance_monitor", result)

    def maybe_run_stability_metrics(self) -> None:
        if time.time() - self.last_stability < self.config.stability_seconds:
            return
        self.last_stability = time.time()
        result = run_subprocess(
            ["python3", str(RUNTIME_ROOT / "scripts" / "collect_stability_metrics.py")],
            timeout=60,
        )
        result["report_path"] = str(RUNTIME_ROOT / "workspace" / "stability_report.json")
        self.latest_stability = result
        self.log_event("stability_metrics", result)

    def maybe_run_autoresearch(self) -> None:
        if time.time() - self.last_autoresearch < self.config.autoresearch_seconds:
            return
        self.last_autoresearch = time.time()
        env = dict(os.environ)
        env["ATHENA_AUTORESEARCH_ENABLED"] = "1"
        env["ATHENA_AUTORESEARCH_DRY_RUN"] = "1"
        result = run_subprocess(
            [
                "python3",
                str(RUNTIME_ROOT / "scripts" / "athena_autoresearch_runner.py"),
                "run-once",
                "--dry-run",
            ],
            env=env,
            timeout=120,
        )
        summary = ""
        for line in (result["stdout"] + "\n" + result["stderr"]).splitlines():
            if "completed successfully" in line or "Recommendations:" in line:
                summary = (summary + " " + line).strip()
        result["summary"] = summary
        self.latest_autoresearch = result
        self.log_event("autoresearch", result)

    def maybe_emit_interim_summary(self) -> None:
        interim_interval = 4 * 3600  # 4 hours in seconds
        if time.time() - self.last_interim_summary < interim_interval:
            return
        self.last_interim_summary = time.time()
        elapsed = int(time.time() - self.started_at)
        elapsed_hours = elapsed / 3600
        summary = {
            "timestamp": now_iso(),
            "elapsed_seconds": elapsed,
            "elapsed_hours": round(elapsed_hours, 2),
            "phase": determine_phase(elapsed, self.duration_seconds),
            "anomaly_windows_count": len(self.anomaly_windows),
            "recovery_windows_count": len(self.recovery_windows),
            "checkpoints_count": len(self.checkpoints),
            "current_anomaly_active": self.current_anomaly is not None,
            "anomaly_windows": self.anomaly_windows[-5:],  # last 5 anomaly windows
            "recovery_windows": self.recovery_windows[-5:],  # last 5 recovery windows
            "latest_resource_snapshot": read_json(self.output_dir / "latest_resource.json", {}),
            "system_health": self._calculate_system_health(),
        }
        summary_file = (
            self.interim_reports_dir
            / f"interim_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        write_json(summary_file, summary)
        self.log_event("interim_summary", summary)

        # 也生成一个人类可读的Markdown报告
        self._write_interim_markdown(summary, summary_file)

    def _calculate_system_health(self) -> dict[str, Any]:
        try:
            latest_resource = read_json(self.output_dir / "latest_resource.json", {})
            cpu = latest_resource.get("cpu", {})
            memory = latest_resource.get("memory", {})
            health_score = 100
            if cpu.get("usage_percent", 0) > 90:
                health_score -= 30
            elif cpu.get("usage_percent", 0) > 70:
                health_score -= 15
            if memory.get("pressure_free_percent", 100) < 10:
                health_score -= 30
            elif memory.get("pressure_free_percent", 100) < 20:
                health_score -= 15
            return {
                "score": health_score,
                "status": (
                    "healthy"
                    if health_score >= 70
                    else "degraded" if health_score >= 40 else "critical"
                ),
                "cpu_usage_percent": cpu.get("usage_percent"),
                "memory_pressure_free_percent": memory.get("pressure_free_percent"),
            }
        except Exception:
            return {
                "score": 0,
                "status": "unknown",
                "error": "failed to calculate health",
            }

    def _write_interim_markdown(self, summary: dict[str, Any], summary_file: Path) -> None:
        lines = [
            f"# 中期压力测试总结 ({summary['timestamp']})",
            "",
            f"- 运行时长: {summary['elapsed_hours']} 小时",
            f"- 当前阶段: {summary['phase']['name']}",
            f"- 系统健康度: {summary['system_health']['status']} (得分: {summary['system_health']['score']})",
            f"- 异常窗口数: {summary['anomaly_windows_count']}",
            f"- 恢复窗口数: {summary['recovery_windows_count']}",
            f"- 检查点总数: {summary['checkpoints_count']}",
            f"- 当前是否存在异常: {'是' if summary['current_anomaly_active'] else '否'}",
            "",
            "## 最近异常窗口",
        ]
        if summary["anomaly_windows"]:
            for idx, window in enumerate(summary["anomaly_windows"], 1):
                lines.append(
                    f"{idx}. 开始: {window.get('started_at')}, 异常: {', '.join(window.get('anomalies', []))}"
                )
        else:
            lines.append("暂无异常窗口")

        lines.extend(
            [
                "",
                "## 最近恢复窗口",
            ]
        )
        if summary["recovery_windows"]:
            for idx, recovery in enumerate(summary["recovery_windows"], 1):
                lines.append(
                    f"{idx}. 开始: {recovery.get('started_at')}, 结束: {recovery.get('ended_at')}, 异常: {', '.join(recovery.get('anomalies', []))}"
                )
        else:
            lines.append("暂无恢复窗口")

        lines.extend(
            [
                "",
                "## 系统资源概览",
                f"- CPU使用率: {summary['system_health'].get('cpu_usage_percent', 'N/A')}%",
                f"- 内存空闲压力: {summary['system_health'].get('memory_pressure_free_percent', 'N/A')}%",
                "",
                "## 原始数据",
                f"- JSON摘要文件: `{summary_file}`",
                f"- 完整检查点目录: `{self.checkpoints_dir}`",
                f"- 事件日志: `{self.events_path}`",
            ]
        )

        markdown_file = summary_file.with_suffix(".md")
        markdown_file.write_text("\n".join(lines), encoding="utf-8")

    def write_state(self, phase: dict[str, Any]) -> None:
        payload = {
            "run_id": self.run_id,
            "started_at": datetime.fromtimestamp(self.started_at)
            .astimezone()
            .isoformat(timespec="seconds"),
            "updated_at": now_iso(),
            "elapsed_seconds": int(time.time() - self.started_at),
            "duration_hours": self.config.duration_hours,
            "phase": phase,
            "stopped": STOP_REQUESTED,
            "status": self.run_status,
            "stop_reason": self.stop_reason,
            "report_path": str(self.report_path),
            "output_dir": str(self.output_dir),
            "latest_performance": self.latest_performance,
            "latest_stability": self.latest_stability,
            "latest_autoresearch": self.latest_autoresearch,
            "checkpoints": self.checkpoints[-10:],  # last 10 checkpoints
            "anomaly_windows": self.anomaly_windows,
            "recovery_windows": self.recovery_windows,
            "current_anomaly": self.current_anomaly,
            "last_error": self.last_error,
        }
        write_json(self.state_path, payload)

    def run(self) -> int:
        self.log_event("run_started", {"config": asdict(self.config)})
        profile = self.best_state_profile()
        write_json(self.output_dir / "m4_best_state_profile.json", profile)
        phase = determine_phase(0, self.duration_seconds)
        exit_code = 0
        try:
            while not STOP_REQUESTED:
                elapsed = time.time() - self.started_at
                phase = determine_phase(elapsed, self.duration_seconds)
                resource_snapshot = self.collect_resource_sample()
                self.record_checkpoint(phase, resource_snapshot)
                self.maybe_run_performance_monitor()
                self.maybe_run_stability_metrics()
                self.maybe_run_autoresearch()
                self.maybe_emit_interim_summary()
                self.write_state(phase)
                self.emit_report(phase)
                self.log_event(
                    "heartbeat",
                    {
                        "elapsed_seconds": int(elapsed),
                        "phase": phase["name"],
                        "status": self.run_status,
                    },
                )
                if elapsed >= self.duration_seconds:
                    self.run_status = "completed"
                    self.stop_reason = "completed_planned"
                    break
                time.sleep(self.config.sample_seconds)

            if STOP_REQUESTED and self.run_status == "running":
                self.run_status = "stopped"
                self.stop_reason = "signal_received"
        except Exception as exc:
            exit_code = 1
            self.run_status = "crashed"
            self.stop_reason = "unhandled_exception"
            self.last_error = {
                "type": exc.__class__.__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            self.log_event("run_crashed", self.last_error)

        self.log_event(
            "run_finished",
            {
                "elapsed_seconds": int(time.time() - self.started_at),
                "stopped": STOP_REQUESTED,
                "status": self.run_status,
                "stop_reason": self.stop_reason,
            },
        )
        # 写入最终状态
        final_phase = determine_phase(self.duration_seconds, self.duration_seconds)
        final_state_path = self.output_dir / "final_state.json"
        write_json(
            final_state_path,
            {
                "run_id": self.run_id,
                "started_at": datetime.fromtimestamp(self.started_at)
                .astimezone()
                .isoformat(timespec="seconds"),
                "ended_at": now_iso(),
                "elapsed_seconds": int(time.time() - self.started_at),
                "duration_hours": self.config.duration_hours,
                "completion_status": self.run_status,
                "stopped": STOP_REQUESTED,
                "stop_reason": self.stop_reason
                or ("manual" if STOP_REQUESTED else "completed_planned"),
                "anomaly_windows": self.anomaly_windows,
                "recovery_windows": self.recovery_windows,
                "checkpoints": self.checkpoints[-50:],  # 保留最近50个检查点
                "anomaly_windows_count": len(self.anomaly_windows),
                "recovery_windows_count": len(self.recovery_windows),
                "checkpoints_count": len(self.checkpoints),
                "output_dir": str(self.output_dir),
                "report_path": str(self.report_path),
                "state_path": str(self.state_path),
                "events_path": str(self.events_path),
                "checkpoints_dir": str(self.checkpoints_dir),
                "interim_reports_dir": str(self.interim_reports_dir),
                "samples_dir": str(self.samples_dir),
                "last_error": self.last_error,
            },
        )
        self.write_state(final_phase)
        self.emit_report(final_phase, is_final=True)
        return exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a safe 24h OpenHuman stress test")
    parser.add_argument("--duration-hours", type=float, default=24.0)
    parser.add_argument("--sample-seconds", type=int, default=300)
    parser.add_argument("--performance-seconds", type=int, default=900)
    parser.add_argument("--stability-seconds", type=int, default=900)
    parser.add_argument("--autoresearch-seconds", type=int, default=3600)
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--write-pid", action="store_true", default=False)
    return parser.parse_args()


def main() -> int:
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    args = parse_args()
    cfg = StressConfig(
        duration_hours=args.duration_hours,
        sample_seconds=args.sample_seconds,
        performance_seconds=args.performance_seconds,
        stability_seconds=args.stability_seconds,
        autoresearch_seconds=args.autoresearch_seconds,
        report_path=args.report_path,
        output_root=args.output_root,
    )
    if args.write_pid:
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    runner = StressRunner(cfg)
    try:
        return runner.run()
    finally:
        if args.write_pid and PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
