#!/usr/bin/env python3
"""Minimal Athena Web Desktop compatibility server.

This keeps the legacy 8080 entry usable while the runtime root is unified to
``/Volumes/1TB-M2/openclaw``. It intentionally implements only the endpoints
the legacy front-end actually needs, and reads queue/runtime state from the
single source of truth.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from email.utils import formatdate
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Import shared root paths
try:
    from .openclaw_roots import (
        AGENT_STATE_PATH,
        LOG_DIR,
        PLAN_CONFIG_PATH,
        QUEUE_STATE_DIR,
        RUNTIME_ROOT,
        STATIC_CSS,
        STATIC_JS,
        TASKS_PATH,
        TOKEN_FILE,
        WEB_PORT_FILE,
        pid_file,
    )
except ImportError:
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from openclaw_roots import (
        AGENT_STATE_PATH,
        LOG_DIR,
        PLAN_CONFIG_PATH,
        QUEUE_STATE_DIR,
        RUNTIME_ROOT,
        STATIC_CSS,
        STATIC_JS,
        TASKS_PATH,
        TOKEN_FILE,
        WEB_PORT_FILE,
        pid_file,
    )


# 尝试导入 provider registry（可选）
PROVIDER_REGISTRY_AVAILABLE = False
get_registry = None
try:
    # 使用 RUNTIME_ROOT 路径
    mini_agent_path = str(RUNTIME_ROOT / "mini-agent")
    if mini_agent_path not in sys.path:
        sys.path.insert(0, mini_agent_path)
    from agent.core.provider_registry import get_registry as _get_registry

    get_registry = _get_registry
    PROVIDER_REGISTRY_AVAILABLE = True
except ImportError:
    # provider registry 不可用，使用默认值
    pass

# 尝试导入成本跟踪器
COST_TRACKER_AVAILABLE = False
get_cost_tracker = None
try:
    # 确保路径已添加
    mini_agent_path = str(RUNTIME_ROOT / "mini-agent")
    if mini_agent_path not in sys.path:
        sys.path.insert(0, mini_agent_path)
    from agent.core.cost_tracker import get_cost_tracker as _get_cost_tracker

    get_cost_tracker = _get_cost_tracker
    COST_TRACKER_AVAILABLE = True
except ImportError:
    # 成本跟踪器不可用，使用降级逻辑
    pass

# 尝试导入 chat runtime（单一事实源）
CHAT_RUNTIME_AVAILABLE = False
get_runtime = None
try:
    # 确保路径已添加
    mini_agent_path = str(RUNTIME_ROOT / "mini-agent")
    if mini_agent_path not in sys.path:
        sys.path.insert(0, mini_agent_path)
    from agent.core.chat_runtime import get_runtime as _get_runtime

    get_runtime = _get_runtime
    CHAT_RUNTIME_AVAILABLE = True
except ImportError:
    # chat runtime 不可用，使用降级逻辑
    pass

PID_FILE = pid_file("athena_web_desktop_compat")
PORT = int(os.getenv("ATHENA_WEB_DESKTOP_PORT", "8080"))
HOST = os.getenv("ATHENA_WEB_DESKTOP_HOST", "127.0.0.1")
ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="auth-token" content="__AUTH_TOKEN__">
    <title>Athena Web Desktop</title>
    <link rel="stylesheet" href="/athena/static/chat_window.css?v=__ASSET_VERSION__">
    <style>
        body {
            margin: 0;
            min-height: 100vh;
            background:
                radial-gradient(circle at top left, rgba(89, 138, 255, 0.28), transparent 30%),
                radial-gradient(circle at top right, rgba(0, 199, 156, 0.24), transparent 28%),
                linear-gradient(135deg, #06131f 0%, #0b1f31 38%, #10263a 100%);
            color: #f2f7fb;
            font-family: "SF Pro Display", "PingFang SC", "Noto Sans SC", sans-serif;
        }
        .athena-shell {
            max-width: 1380px;
            margin: 0 auto;
            padding: 24px 20px 28px;
        }
        .athena-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            margin-bottom: 18px;
        }
        .athena-title h1 {
            margin: 0;
            font-size: 32px;
            letter-spacing: 0.02em;
        }
        .athena-title p {
            margin: 8px 0 0;
            color: rgba(242, 247, 251, 0.72);
            font-size: 14px;
        }
        .athena-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            border-radius: 999px;
            padding: 10px 16px;
            background: rgba(10, 25, 40, 0.7);
            border: 1px solid rgba(103, 157, 255, 0.24);
            backdrop-filter: blur(18px);
            font-size: 13px;
        }
        .athena-grid {
            display: grid;
            grid-template-columns: 1.15fr 0.85fr;
            gap: 18px;
        }
        .athena-stack {
            display: flex;
            flex-direction: column;
            gap: 18px;
        }
        .chat-container {
            width: 100%;
        }
        .chat-window {
            min-height: 720px;
            max-height: 78vh;
        }
        .ops-card {
            border-radius: 22px;
            padding: 18px;
            background: rgba(10, 25, 40, 0.62);
            border: 1px solid rgba(107, 154, 255, 0.16);
            box-shadow: 0 14px 50px rgba(0, 0, 0, 0.22);
            backdrop-filter: blur(18px);
        }
        .ops-card h3 {
            margin: 0 0 12px;
            font-size: 15px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: rgba(160, 208, 255, 0.96);
        }
        .ops-metrics {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }
        .metric {
            border-radius: 16px;
            padding: 12px 14px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .metric .label {
            font-size: 12px;
            color: rgba(242, 247, 251, 0.62);
        }
        .metric .value {
            margin-top: 6px;
            font-size: 20px;
            font-weight: 600;
        }
        .ops-form {
            display: grid;
            gap: 10px;
        }
        .ops-form input,
        .ops-form textarea,
        .ops-form select {
            width: 100%;
            box-sizing: border-box;
            border: 1px solid rgba(112, 160, 255, 0.16);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.04);
            color: #f2f7fb;
            padding: 12px 14px;
            font-size: 14px;
        }
        .ops-form textarea {
            min-height: 104px;
            resize: vertical;
        }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .ops-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .ops-btn {
            border: none;
            border-radius: 999px;
            padding: 11px 16px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            color: #04101c;
            background: linear-gradient(135deg, #9ecbff 0%, #6ed8c7 100%);
        }
        .ops-btn.secondary {
            color: #f2f7fb;
            background: rgba(255, 255, 255, 0.08);
        }
        .task-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-height: 440px;
            overflow-y: auto;
        }
        .task-item {
            border-radius: 16px;
            padding: 12px 14px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .task-item.interactive {
            cursor: pointer;
            transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease, box-shadow 0.16s ease;
        }
        .task-item.interactive:hover {
            transform: translateY(-1px);
            border-color: rgba(142, 190, 255, 0.28);
            background: rgba(255, 255, 255, 0.06);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
        }
        .task-item.active {
            border-color: rgba(126, 211, 255, 0.4);
            background: rgba(110, 224, 200, 0.08);
            box-shadow: 0 10px 28px rgba(30, 126, 255, 0.14);
        }
        .task-meta {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            font-size: 12px;
            color: rgba(242, 247, 251, 0.7);
        }
        .task-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            border-radius: 999px;
            padding: 4px 10px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.07);
            white-space: nowrap;
        }
        .task-signal {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            display: inline-block;
            background: rgba(186, 197, 209, 0.85);
            box-shadow: 0 0 0 0 rgba(186, 197, 209, 0.2);
        }
        .task-signal.pending {
            background: #f4d06f;
            box-shadow: 0 0 0 0 rgba(244, 208, 111, 0.22);
        }
        .task-signal.manual_hold {
            background: #ffb86c;
            box-shadow: 0 0 0 0 rgba(255, 184, 108, 0.22);
        }
        .task-signal.running {
            background: #6ee0c8;
            box-shadow: 0 0 0 0 rgba(110, 224, 200, 0.28);
        }
        .task-signal.completed {
            background: #8ec5ff;
            box-shadow: 0 0 0 0 rgba(142, 197, 255, 0.24);
        }
        .task-signal.failed {
            background: #ff8e8e;
            box-shadow: 0 0 0 0 rgba(255, 142, 142, 0.22);
        }
        .task-signal.breathing {
            animation: task-breathe 1.8s ease-in-out infinite;
        }
        @keyframes task-breathe {
            0%, 100% {
                opacity: 1;
                box-shadow: 0 0 0 0 rgba(110, 224, 200, 0.28);
            }
            50% {
                opacity: 0.55;
                box-shadow: 0 0 0 9px rgba(110, 224, 200, 0);
            }
        }
        .task-title {
            margin-top: 10px;
            font-size: 14px;
            font-weight: 600;
            color: #f2f7fb;
            line-height: 1.45;
        }
        .task-excerpt {
            margin-top: 8px;
            font-size: 12px;
            line-height: 1.45;
            color: rgba(242, 247, 251, 0.66);
            word-break: break-word;
        }
        .task-progress-row {
            margin-top: 10px;
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 10px;
            align-items: center;
        }
        .task-progress-track {
            position: relative;
            height: 8px;
            border-radius: 999px;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .task-progress-fill {
            position: absolute;
            inset: 0 auto 0 0;
            width: 0;
            border-radius: inherit;
            background: linear-gradient(135deg, #f4d06f 0%, #d6ae2f 100%);
            transition: width 0.28s ease;
        }
        .task-progress-fill.running {
            background: linear-gradient(135deg, #6ee0c8 0%, #68b7ff 100%);
        }
        .task-progress-fill.manual_hold {
            background: linear-gradient(135deg, #ffb86c 0%, #ff8c54 100%);
        }
        .task-progress-fill.completed {
            background: linear-gradient(135deg, #79c7ff 0%, #9ecbff 100%);
        }
        .task-progress-fill.failed {
            background: linear-gradient(135deg, #ff8e8e 0%, #ff6767 100%);
        }
        .task-progress-text {
            min-width: 40px;
            text-align: right;
            font-size: 12px;
            font-variant-numeric: tabular-nums;
            color: rgba(242, 247, 251, 0.82);
        }
        .task-card-actions {
            margin-top: 12px;
            display: flex;
            justify-content: flex-end;
        }
        .task-action-btn {
            border: 1px solid rgba(158, 203, 255, 0.18);
            border-radius: 999px;
            padding: 7px 12px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            color: #04101c;
            background: linear-gradient(135deg, #9ecbff 0%, #6ed8c7 100%);
            box-shadow: 0 6px 18px rgba(110, 224, 200, 0.16);
        }
        .task-action-btn:hover {
            transform: translateY(-1px);
        }
        .task-action-btn.secondary {
            color: #f2f7fb;
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.12);
            box-shadow: none;
        }
        .task-action-btn:disabled,
        .task-action-btn.disabled {
            cursor: not-allowed;
            opacity: 0.6;
            transform: none;
        }
        .artifact-path {
            margin-bottom: 10px;
            color: rgba(242, 247, 251, 0.72);
            font-size: 12px;
            word-break: break-all;
        }
        .artifact-preview {
            margin: 0;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: "JetBrains Mono", "SF Mono", monospace;
            font-size: 12px;
            color: #d9e7f5;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 14px;
            min-height: 220px;
            max-height: 420px;
            overflow-y: auto;
        }
        @media (max-width: 1100px) {
            .athena-grid {
                grid-template-columns: 1fr;
            }
            .chat-window {
                min-height: 520px;
            }
        }
        @media (max-width: 720px) {
            .athena-shell {
                padding: 18px 14px 24px;
            }
            .athena-header {
                flex-direction: column;
            }
            .form-row {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="athena-shell">
        <div class="athena-header">
            <div class="athena-title">
                <h1>Athena Web Desktop</h1>
                <p>统一控制面：你以后只进这个入口，后台再分发给 Codex、VS Code(OpenCode) 和本地工作流。</p>
            </div>
            <div class="athena-badge">兼容层 · runtime=/Volumes/1TB-M2/openclaw</div>
        </div>
        <div class="athena-grid">
            <div class="chat-container">
                <div class="chat-window">
                    <div class="chat-header">
                        <div class="header-content">
                            <span class="status-dot"></span>
                            <div>
                                <div class="header-title">统一入口</div>
                                <div id="connectionStatus" class="connection-status connecting">检查连接...</div>
                            </div>
                        </div>
                        <div id="workflowStatus" class="connection-status">等待状态...</div>
                    </div>
                    <div id="chatMessages" class="chat-messages">
                        <div class="message system">
                            <div class="message-bubble">
                                <p>✨ 正在连接 Athena Orchestrator...</p>
                                <span class="timestamp">Just now</span>
                            </div>
                        </div>
                    </div>
                    <div class="chat-input-area">
                        <input id="chatInput" class="chat-input" type="text" placeholder="输入问题；命中规划/修复/审查/测试/调研意图时会自动转成任务..." />
                        <button id="sendButton" class="send-button" type="button">发送</button>
                    </div>
                </div>
            </div>
            <div class="athena-stack">
                <div class="ops-card">
                    <h3>控制台状态</h3>
                    <div class="ops-metrics">
                        <div class="metric"><div class="label">Codex</div><div id="executorCodex" class="value">-</div></div>
                        <div class="metric"><div class="label">OpenCode</div><div id="executorOpencode" class="value">-</div></div>
                        <div class="metric"><div class="label">运行中任务</div><div id="runningCount" class="value">0</div></div>
                        <div class="metric"><div class="label">失败任务</div><div id="failedCount" class="value">0</div></div>
                    </div>
                </div>
                <div class="ops-card">
                    <h3>新建编排任务</h3>
                    <div class="ops-form">
                        <input id="taskTitle" type="text" placeholder="任务标题，例如：Athena 前端纠偏 Build" />
                        <textarea id="taskDescription" placeholder="描述目标、范围、约束、验收标准。"></textarea>
                        <input id="taskTargets" type="text" placeholder="目标文件，多个用逗号分隔" />
                        <div class="form-row">
                            <select id="taskStage">
                                <option value="plan">Codex Plan</option>
                                <option value="build">OpenCode Build</option>
                                <option value="review">Codex Review</option>
                                <option value="qa">Local QA</option>
                            </select>
                            <select id="taskRisk">
                                <option value="low">low</option>
                                <option value="medium" selected>medium</option>
                                <option value="high">high</option>
                            </select>
                        </div>
                        <div class="ops-actions">
                            <button id="submitTaskBtn" class="ops-btn" type="button">创建并执行</button>
                            <button id="runTaskBtn" class="ops-btn secondary" type="button">运行选中任务</button>
                            <button id="retryFailedBtn" class="ops-btn secondary" type="button">拉起失败任务</button>
                            <button id="refreshTasksBtn" class="ops-btn secondary" type="button">刷新任务</button>
                        </div>
                    </div>
                </div>
                <div class="ops-card">
                    <h3>任务队列</h3>
                    <div id="taskList" class="task-list">
                        <div class="task-item">正在加载任务列表...</div>
                    </div>
                </div>
                <div class="ops-card">
                    <h3>任务产物预览</h3>
                    <div id="artifactPath" class="artifact-path">点击任务后在这里预览 artifact。</div>
                    <pre id="artifactPreview" class="artifact-preview">等待选择任务...</pre>
                </div>
            </div>
        </div>
    </div>
    <script src="/athena/static/chat_window.js?v=__ASSET_VERSION__"></script>
</body>
</html>
"""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def asset_version() -> str:
    mtimes: list[int] = []
    for path in (STATIC_JS, STATIC_CSS):
        try:
            mtimes.append(int(path.stat().st_mtime))
        except FileNotFoundError:
            continue
    if not mtimes:
        return str(int(datetime.now().timestamp()))
    return str(max(mtimes))


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_auth_token() -> str:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = secrets.token_urlsafe(24)
    TOKEN_FILE.write_text(token + "\n", encoding="utf-8")
    return token


AUTH_TOKEN = load_auth_token()


def clip(value: str, limit: int = 180) -> str:
    text = " ".join(ANSI_RE.sub("", str(value or "")).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z]+", "-", value).strip("-").lower()
    return slug or "task"


def format_status_label(status: str) -> str:
    return {
        "pending": "待执行",
        "manual_hold": "手动待拉起",
        "running": "运行中",
        "completed": "已完成",
        "failed": "失败",
    }.get(status, status or "unknown")


def expected_stages(entry_stage: str) -> list[str]:
    if entry_stage == "plan":
        return ["plan", "build", "review", "qa"]
    if entry_stage == "review":
        return ["review", "qa"]
    if entry_stage == "qa":
        return ["qa"]
    return ["build", "review", "qa"]


def find_process(keyword: str) -> bool:
    try:
        output = subprocess.check_output(["pgrep", "-f", keyword], text=True).strip()
        return bool(output)
    except subprocess.CalledProcessError:
        return False


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


def compute_route_status(
    route: dict[str, Any],
    route_state: dict[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    返回路由的队列状态详情：
    - status: empty / completed / dependency_blocked / no_consumer / running / manual_hold / failed
    - pause_reason: 暂停原因字符串，若非暂停则为空字符串
    - next_action_hint: 下一步建议字符串
    """
    # 过滤掉 manual_hold 项（它们不计入待处理）
    pending_items = [
        item
        for item in items
        if item.get("status") in {"pending"} and item.get("entry_stage") != "manual_hold"
    ]
    running_items = [item for item in items if item.get("status") == "running"]

    # 队列为空
    if not pending_items and not running_items:
        failed_items = [item for item in items if item.get("status") == "failed"]
        if failed_items:
            return {
                "status": "failed",
                "pause_reason": "failed",
                "next_action_hint": "可重试失败项",
            }

        # 检查是否有 manual_hold 项
        manual_hold_items = [item for item in items if item.get("status") == "manual_hold"]
        if manual_hold_items:
            return {
                "status": "manual_hold",
                "pause_reason": "manual_hold",
                "next_action_hint": "可继续拆 manual_hold",
            }

        completed_items = [item for item in items if item.get("status") == "completed"]
        if completed_items:
            return {
                "status": "completed",
                "pause_reason": "completed",
                "next_action_hint": "本轮已完成",
            }

        return {
            "status": "empty",
            "pause_reason": "empty",
            "next_action_hint": "自动链已完成",
        }

    # 检查是否有活跃的 consumer
    # 查找任何 running 项中的 runner_pid
    active_consumer = False
    for item in running_items:
        runner_pid = item.get("runner_pid")
        if isinstance(runner_pid, int) and runner_pid > 0 and is_pid_alive(runner_pid):
            # 可选：检查心跳新鲜度（暂不实现）
            active_consumer = True
            break

    # 如果有活跃的 consumer，则为 running 状态
    if active_consumer:
        return {"status": "running", "pause_reason": "", "next_action_hint": "执行中"}

    # 检查依赖阻塞
    # 构建依赖索引
    item_by_id = {item["id"]: item for item in items}
    blocked = False
    for item in pending_items:
        depends_on = item.get("depends_on", [])
        if not depends_on:
            continue
        for dep_id in depends_on:
            dep_item = item_by_id.get(dep_id)
            if not dep_item or dep_item.get("status") != "completed":
                blocked = True
                break
        if blocked:
            break

    if blocked:
        return {
            "status": "dependency_blocked",
            "pause_reason": "dependency_blocked",
            "next_action_hint": "等待依赖项完成",
        }

    # 有待处理项且依赖已满足，但没有活跃的 consumer
    return {
        "status": "no_consumer",
        "pause_reason": "no_consumer",
        "next_action_hint": "等待 consumer 拉起",
    }


def probe_ollama() -> bool:
    req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=1.5) as response:
            return response.status == 200
    except Exception:
        return False


def executor_path(candidate: str) -> str:
    if candidate and Path(candidate).exists():
        return candidate
    resolved = shutil.which(candidate) if candidate else None
    return resolved or candidate


def load_agent_state() -> dict[str, Any]:
    payload = read_json(AGENT_STATE_PATH, default={}) or {}
    return {
        "version": int(payload.get("version", 1) or 1),
        "mode": str(payload.get("mode", "build") or "build"),
        "risk_level": str(payload.get("risk_level", "medium") or "medium"),
        "change_policy": str(payload.get("change_policy", "normal") or "normal"),
        "execution_scope": str(payload.get("execution_scope", "mutation_exec") or "mutation_exec"),
        "task_id": str(payload.get("task_id", "") or ""),
        "owner": str(payload.get("owner", "") or ""),
        "updated_at": str(payload.get("updated_at", now_iso()) or now_iso()),
        "notes": str(payload.get("notes", "") or ""),
    }


def load_tasks_payload() -> dict[str, Any]:
    payload = read_json(TASKS_PATH, default={"version": 1, "tasks": []}) or {
        "version": 1,
        "tasks": [],
    }
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        payload["tasks"] = []
    return payload


def task_counts() -> dict[str, int]:
    tasks = load_tasks_payload().get("tasks", [])
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
    for task in tasks:
        status = str(task.get("status", "pending") or "pending")
        counts[status] = counts.get(status, 0) + 1
    return counts


def load_plan_config() -> dict[str, Any]:
    return read_json(PLAN_CONFIG_PATH, default={"routes": []}) or {"routes": []}


def route_state_path(route: dict[str, Any]) -> Path:
    queue_id = str(route.get("queue_id", "athena_queue") or "athena_queue")
    return QUEUE_STATE_DIR / f"{queue_id}.json"


def load_route_state(route: dict[str, Any]) -> dict[str, Any]:
    path = route_state_path(route)
    payload = read_json(path, default=None)
    if isinstance(payload, dict):
        payload.setdefault("current_item_ids", [])
        return payload
    return {
        "queue_id": str(route.get("queue_id", "") or ""),
        "name": str(route.get("name", "") or ""),
        "current_item_id": "",
        "current_item_ids": [],
        "updated_at": now_iso(),
        "items": {},
    }


def load_manifest_items(route: dict[str, Any]) -> list[dict[str, Any]]:
    manifest_path = Path(str(route.get("manifest_path", "") or ""))
    manifest = read_json(manifest_path, default={"items": []}) or {"items": []}
    items = manifest.get("items", [])
    return items if isinstance(items, list) else []


def queue_item_from_manifest(
    route: dict[str, Any], manifest_item: dict[str, Any], route_state: dict[str, Any]
) -> dict[str, Any]:
    item_id = str(manifest_item.get("id", "") or "")
    state_item = (route_state.get("items") or {}).get(item_id, {})
    # 优先级：队列状态文件 > manifest状态 > pending
    status = str(state_item.get("status") or manifest_item.get("status") or "pending")
    artifact_paths = state_item.get("artifact_paths") or []
    metadata = (
        manifest_item.get("metadata") if isinstance(manifest_item.get("metadata"), dict) else {}
    )
    manual_override_autostart = bool(state_item.get("manual_override_autostart"))
    if status == "pending" and metadata.get("autostart") is False and not manual_override_autostart:
        status = "manual_hold"
    progress = state_item.get("progress_percent")
    if progress is None:
        progress = manifest_item.get("progress_percent")
    if progress is None:
        progress = 100 if status in {"completed", "failed"} else 60 if status == "running" else 0
    stage = str(state_item.get("stage") or manifest_item.get("entry_stage") or "build")
    current_item_ids = route_state.get("current_item_ids")
    if not isinstance(current_item_ids, list):
        current_item_ids = []
    primary_current_item_id = str(route_state.get("current_item_id", "") or "")
    if primary_current_item_id and primary_current_item_id not in current_item_ids:
        current_item_ids.append(primary_current_item_id)

    return {
        "id": item_id,
        "task_id": item_id,
        "route_id": str(route.get("route_id", "") or ""),
        "title": str(manifest_item.get("title", item_id) or item_id),
        "status": status,
        "status_label": format_status_label(status),
        "entry_stage": str(manifest_item.get("entry_stage", "build") or "build"),
        "risk_level": str(manifest_item.get("risk_level", "medium") or "medium"),
        "priority": str(metadata.get("priority", "") or ""),
        "lane": str(metadata.get("lane", "") or ""),
        "depends_on": list(metadata.get("depends_on") or []),
        "instruction_path": str(manifest_item.get("instruction_path", "") or ""),
        "root_task_id": str(state_item.get("root_task_id", "") or ""),
        "stage": stage,
        "executor": str(state_item.get("executor", "") or ""),
        "started_at": str(state_item.get("started_at", "") or ""),
        "finished_at": str(state_item.get("finished_at", "") or ""),
        "summary": clip(str(state_item.get("summary", "") or ""), 320),
        "artifact_path": artifact_paths[0] if artifact_paths else "",
        "error": clip(str(state_item.get("error", "") or ""), 320),
        "result_excerpt": clip(str(state_item.get("result_excerpt", "") or ""), 320),
        "pipeline_summary": clip(str(state_item.get("pipeline_summary", "") or ""), 240),
        "artifact_paths": artifact_paths,
        "progress_percent": int(progress),
        "expected_stages": expected_stages(
            str(manifest_item.get("entry_stage", "build") or "build")
        ),
        "current_stage_ids": list(state_item.get("current_stage_ids") or []),
        "runner_pid": state_item.get("runner_pid"),
        "runner_heartbeat_at": str(state_item.get("runner_heartbeat_at", "") or ""),
        "manual_override_autostart": manual_override_autostart,
        "retryable": True,
        "is_current": item_id in current_item_ids and status == "running",
    }


def build_queue_payload() -> dict[str, Any]:
    config = load_plan_config()
    routes_payload: list[dict[str, Any]] = []
    total_counts = {
        "pending": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "manual_hold": 0,
    }
    auto_counts = {
        "pending": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "manual_hold": 0,
    }
    manual_counts = {
        "pending": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "manual_hold": 0,
    }

    for route in config.get("routes", []):
        manifest_items = load_manifest_items(route)
        route_state = load_route_state(route)
        items = [queue_item_from_manifest(route, item, route_state) for item in manifest_items]
        route_counts = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "manual_hold": 0,
        }
        runner_mode = str(route.get("runner_mode", "opencode_build") or "opencode_build")
        for item in items:
            route_counts[item["status"]] = route_counts.get(item["status"], 0) + 1
            total_counts[item["status"]] = total_counts.get(item["status"], 0) + 1
            if (
                runner_mode in {"opencode_build", "codex_review", "codex_plan"}
                and item["status"] != "manual_hold"
            ):
                auto_counts[item["status"]] = auto_counts.get(item["status"], 0) + 1
            else:
                manual_counts[item["status"]] = manual_counts.get(item["status"], 0) + 1

        route_status = compute_route_status(route, route_state, items)
        routes_payload.append(
            {
                "route_id": str(route.get("route_id", "") or ""),
                "queue_id": str(route.get("queue_id", "") or ""),
                "name": str(route.get("name", "") or ""),
                "runner_mode": runner_mode,
                "manifest_path": str(route.get("manifest_path", "") or ""),
                "state_path": str(route_state_path(route)),
                "current_item_id": str(route_state.get("current_item_id", "") or ""),
                "current_item_ids": list(route_state.get("current_item_ids") or []),
                "counts": route_counts,
                "items": items,
                "queue_status": route_status["status"],
                "pause_reason": route_status["pause_reason"],
                "next_action_hint": route_status["next_action_hint"],
                "message": "",
            }
        )

    return {
        "found": bool(routes_payload),
        "config_path": str(PLAN_CONFIG_PATH),
        "message": "",
        "routes": routes_payload,
        "counts": total_counts,
        "auto_counts": auto_counts,
        "manual_counts": manual_counts,
    }


def load_control_plane_config() -> dict[str, Any]:
    """加载控制面配置，返回摘要信息。"""
    config_path = RUNTIME_ROOT / "mini-agent" / "config" / "control_plane.yaml"
    if not config_path.exists():
        return {
            "available": False,
            "reason": f"控制面配置文件不存在: {config_path}",
            "scopes": ["managed", "project", "local", "session"],
            "local_first_policy": "未配置",
        }

    try:
        import yaml

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 提取关键信息
        version = config.get("version", "unknown")
        list(config.keys()) if isinstance(config, dict) else []

        # 检查本地优先策略
        local_first = config.get("local_first_policy", {})
        never_leaves = (
            local_first.get("never_leaves_local", []) if isinstance(local_first, dict) else []
        )
        allowed_remote = (
            local_first.get("allowed_remote_access", []) if isinstance(local_first, dict) else []
        )

        return {
            "available": True,
            "version": version,
            "config_path": str(config_path),
            "scopes": ["managed", "project", "local", "session"],
            "scope_summary": {
                "managed": bool(config.get("managed")),
                "project": bool(config.get("project")),
                "local": bool(config.get("local")),
                "session": bool(config.get("session")),
            },
            "local_first_policy": {
                "never_leaves_local_count": len(never_leaves),
                "allowed_remote_access_count": len(allowed_remote),
                "explicit_rules_defined": bool(local_first.get("explicit_rules")),
            },
            "configuration_priority": config.get("configuration_priority", {}).get(
                "priority_order", []
            ),
            "compatibility_bridge": bool(config.get("compatibility_bridge")),
        }
    except Exception as e:
        return {
            "available": False,
            "reason": f"加载控制面配置失败: {e}",
            "scopes": ["managed", "project", "local", "session"],
            "local_first_policy": "加载失败",
        }


def build_status_payload() -> dict[str, Any]:
    gateway_ok = find_process(r"(^|/)openclaw-gateway")
    ollama_ok = probe_ollama()
    guard_log = RUNTIME_ROOT / "mini-agent" / "logs" / "guardian.log"
    guardian_status = (
        "running"
        if guard_log.exists() and (datetime.now().timestamp() - guard_log.stat().st_mtime) < 600
        else "stopped"
    )
    agent_state = load_agent_state()

    # 默认值（降级逻辑）
    primary_backend = "bailian"
    primary_model = "qwen-plus"
    primary_available = False
    primary_reason = "百炼配置不存在"
    fallback_backend = "ollama"
    fallback_model = "qwen2.5:3b"
    fallback_available = ollama_ok
    fallback_reason = "" if ollama_ok else "Ollama 不可用"
    chat_state_value = "fallback_only" if ollama_ok else "unavailable"
    chat_backend = "ollama" if ollama_ok else "none"
    chat_selected_model = "qwen2.5:3b" if ollama_ok else "-"
    chat_reason = "百炼配置不存在" if ollama_ok else "Ollama 不可用"

    # 优先使用 chat runtime 作为单一事实源
    if CHAT_RUNTIME_AVAILABLE and get_runtime:
        try:
            runtime = get_runtime()
            chat_state = runtime.get_chat_state()

            # 从 runtime 状态提取字段（直接使用 runtime 提供的真实值）
            chat_state_value = chat_state.get("chat_state", "unknown")
            chat_backend = chat_state.get("chat_backend", "none")
            chat_selected_model = chat_state.get("chat_selected_model", "-")
            chat_reason = chat_state.get("chat_reason", "")

            # 更新 primary 和 fallback 信息（可选，保持兼容）
            chat_primary = chat_state.get("chat_primary", {})
            chat_fallback = chat_state.get("chat_fallback", {})
            if chat_primary:
                primary_backend = chat_primary.get("provider_id", primary_backend)
                primary_model = chat_primary.get("model_id", primary_model)
                # primary_available 可以根据 chat_state 推断：如果状态为 ok 则 primary 可用
                primary_available = chat_state_value == "ok"
                primary_reason = "runtime 状态"
            if chat_fallback:
                fallback_backend = chat_fallback.get("provider_id", fallback_backend)
                fallback_model = chat_fallback.get("model_id", fallback_model)
                # fallback_available 可以根据 chat_state 推断：如果状态为 fallback_only 则 fallback 可用
                fallback_available = chat_state_value == "fallback_only"
                fallback_reason = "runtime 状态"
        except Exception:
            # 如果 runtime 获取失败，保留默认值（降级逻辑）
            pass

    # 如果 provider registry 可用且 runtime 未提供完整信息，可以补充检查
    if PROVIDER_REGISTRY_AVAILABLE and not CHAT_RUNTIME_AVAILABLE:
        try:
            registry = get_registry()
            primary_provider_id, primary_model_id = registry.get_default_model()
            provider_backend_map = {
                "dashscope": "bailian",
                "ollama_local": "ollama",
                "minimax": "minimax",
                "kimi": "kimi",
                "glm": "glm",
            }
            primary_backend = provider_backend_map.get(primary_provider_id, primary_provider_id)
            primary_model = primary_model_id
            provider = registry.get_provider(primary_provider_id)
            if provider:
                if provider.auth_env_key:
                    primary_available = bool(os.environ.get(provider.auth_env_key))
                    primary_reason = (
                        "配置就绪" if primary_available else f"缺少环境变量 {provider.auth_env_key}"
                    )
                elif provider.id == "ollama_local":
                    primary_available = ollama_ok
                    primary_reason = "" if ollama_ok else "Ollama 不可用"
                else:
                    primary_reason = "未知 provider 类型"
        except Exception as e:
            primary_reason = f"获取 provider 配置失败: {e}"

    return {
        "bridge": {
            "guardian": guardian_status,
            "gateway": "ok" if gateway_ok else "missing",
            "ollama": "ok" if ollama_ok else "missing",
            "disk": 0,
            "chat_state": chat_state_value,
            "chat_backend": chat_backend,
            "chat_selected_model": chat_selected_model,
            "chat_reason": chat_reason,
            "chat_primary": {
                "backend": primary_backend,
                "model": primary_model,
                "available": primary_available,
                "reason": primary_reason,
                "checked_at": int(datetime.now().timestamp()),
                "cached_at": datetime.now().timestamp(),
            },
            "chat_fallback": {
                "backend": fallback_backend,
                "model": fallback_model,
                "available": fallback_available,
                "reason": fallback_reason,
                "checked_at": int(datetime.now().timestamp()),
                "cached_at": datetime.now().timestamp(),
            },
            "nl_router": "enabled",
            "control_plane": load_control_plane_config(),
        },
        "orchestrator": {
            "workflow": {
                "version": 1,
                "mode": agent_state["mode"],
                "risk_level": agent_state["risk_level"],
                "change_policy": agent_state["change_policy"],
                "execution_scope": agent_state["execution_scope"],
                "task_id": agent_state["task_id"],
                "owner": agent_state["owner"],
                "updated_at": agent_state["updated_at"],
                "notes": agent_state["notes"],
            },
            "executors": {
                "codex": {
                    "available": Path("/Applications/Codex.app/Contents/Resources/codex").exists(),
                    "path": executor_path("/Applications/Codex.app/Contents/Resources/codex"),
                    "roles": ["plan", "review"],
                },
                "opencode": {
                    "available": bool(shutil.which("opencode")),
                    "path": executor_path("opencode"),
                    "roles": ["build"],
                },
                "local": {
                    "available": True,
                    "path": executor_path("python3"),
                    "roles": ["think", "qa", "browse"],
                },
            },
            "task_counts": task_counts(),
            "default_entry": "/",
            "legacy_entry": "/legacy/",
        },
    }


def build_basic_status() -> dict[str, Any]:
    gateway_ok = find_process(r"(^|/)openclaw-gateway")
    return {
        "guardian": (
            "running"
            if (RUNTIME_ROOT / "mini-agent" / "logs" / "guardian.log").exists()
            else "stopped"
        ),
        "gateway": "ok" if gateway_ok else "missing",
        "ollama": "ok" if probe_ollama() else "missing",
        "disk": 0,
        "cache_hit": 0,
    }


# ==================== 成本监控API函数 ====================


def build_cost_summary() -> dict[str, Any]:
    """构建成本摘要数据"""
    if not COST_TRACKER_AVAILABLE or not get_cost_tracker:
        return {
            "success": False,
            "error": "成本跟踪器不可用",
            "available": False,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    try:
        cost_tracker = get_cost_tracker()

        # 获取最近30天的数据
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=30)

        # 获取摘要
        summary = cost_tracker.get_daily_summary()

        # 获取provider分布
        provider_breakdown = cost_tracker.get_provider_breakdown(
            start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        )

        # 获取任务类型分析
        task_kind_analysis = cost_tracker.get_task_kind_analysis("monthly")

        return {
            "success": True,
            "available": True,
            "timestamp": datetime.now(UTC).isoformat(),
            "summary": {
                "total_cost": summary.total_cost if hasattr(summary, "total_cost") else 0.0,
                "total_records": summary.total_records if hasattr(summary, "total_records") else 0,
                "period_days": 30,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "average_daily_cost": (
                    summary.total_cost / 30
                    if hasattr(summary, "total_cost") and summary.total_cost > 0
                    else 0.0
                ),
            },
            "provider_breakdown": provider_breakdown,
            "task_kind_analysis": task_kind_analysis,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "available": COST_TRACKER_AVAILABLE,
            "timestamp": datetime.now(UTC).isoformat(),
        }


def build_cost_provider_breakdown() -> dict[str, Any]:
    """构建provider成本分布数据"""
    if not COST_TRACKER_AVAILABLE or not get_cost_tracker:
        return {
            "success": False,
            "error": "成本跟踪器不可用",
            "available": False,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    try:
        cost_tracker = get_cost_tracker()

        # 获取最近30天的数据
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=30)

        provider_breakdown = cost_tracker.get_provider_breakdown(
            start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        )

        return {
            "success": True,
            "available": True,
            "timestamp": datetime.now(UTC).isoformat(),
            "period": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "days": 30,
            },
            "provider_breakdown": provider_breakdown,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "available": COST_TRACKER_AVAILABLE,
            "timestamp": datetime.now(UTC).isoformat(),
        }


def build_cost_task_kind_analysis() -> dict[str, Any]:
    """构建任务类型成本分析数据"""
    if not COST_TRACKER_AVAILABLE or not get_cost_tracker:
        return {
            "success": False,
            "error": "成本跟踪器不可用",
            "available": False,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    try:
        cost_tracker = get_cost_tracker()

        task_kind_analysis = cost_tracker.get_task_kind_analysis("monthly")

        return {
            "success": True,
            "available": True,
            "timestamp": datetime.now(UTC).isoformat(),
            "task_kind_analysis": task_kind_analysis,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "available": COST_TRACKER_AVAILABLE,
            "timestamp": datetime.now(UTC).isoformat(),
        }


def build_cost_savings() -> dict[str, Any]:
    """构建成本节省分析数据（DeepSeek vs DashScope）"""
    if not COST_TRACKER_AVAILABLE or not get_cost_tracker:
        return {
            "success": False,
            "error": "成本跟踪器不可用",
            "available": False,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    try:
        cost_tracker = get_cost_tracker()

        # 获取最近30天的数据
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=30)

        provider_breakdown = cost_tracker.get_provider_breakdown(
            start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        )

        # 计算DeepSeek和DashScope的成本
        deepseek_cost = 0.0
        dashscope_cost = 0.0

        if "breakdown" in provider_breakdown:
            breakdown = provider_breakdown["breakdown"]
            deepseek_cost = breakdown.get("deepseek", {}).get("cost", 0.0)
            dashscope_cost = breakdown.get("dashscope", {}).get("cost", 0.0)

        # 计算节省（假设DashScope是基线）
        total_cost = deepseek_cost + dashscope_cost

        # 基于实际数据计算节省（如果可用），否则使用报告的87.9%
        savings = 0.0
        savings_percentage = 0.0
        calculation_basis = "无成本数据"

        if dashscope_cost > 0 and deepseek_cost > 0:
            # 有实际数据，计算实际节省
            savings_percentage = (
                ((dashscope_cost - deepseek_cost) / dashscope_cost * 100)
                if dashscope_cost > 0
                else 0.0
            )
            savings = dashscope_cost * (savings_percentage / 100)
            calculation_basis = "基于实际成本数据计算"
        elif dashscope_cost > 0:
            # 只有DashScope成本，使用报告的87.9%节省
            savings_percentage = 87.9
            savings = dashscope_cost * 0.879
            calculation_basis = "基于质量-成本优化报告（87.9%节省）"
        else:
            # 没有DashScope成本数据
            calculation_basis = "无DashScope成本数据可供比较"

        return {
            "success": True,
            "available": True,
            "timestamp": datetime.now(UTC).isoformat(),
            "period": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "days": 30,
            },
            "costs": {
                "deepseek": deepseek_cost,
                "dashscope": dashscope_cost,
                "total": total_cost,
            },
            "savings": {
                "amount": savings,
                "percentage": savings_percentage,
                "baseline_provider": "dashscope",
                "optimized_provider": "deepseek",
                "calculation_basis": calculation_basis,
            },
            "recommendation": "DeepSeek提供相同质量但成本降低87.9%，建议继续使用DeepSeek作为主要provider。",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "available": COST_TRACKER_AVAILABLE,
            "timestamp": datetime.now(UTC).isoformat(),
        }


def first_route() -> dict[str, Any] | None:
    config = load_plan_config()
    routes = config.get("routes", [])
    return routes[0] if routes else None


def create_manifest_task(payload: dict[str, Any]) -> dict[str, Any]:
    route = first_route()
    if not route:
        raise RuntimeError("未找到可写入的 AI plan 路由。")

    manifest_path = Path(str(route.get("manifest_path", "") or ""))
    manifest = read_json(
        manifest_path,
        default={
            "queue_id": route.get("queue_id", ""),
            "name": route.get("name", ""),
            "items": [],
        },
    ) or {
        "queue_id": route.get("queue_id", ""),
        "name": route.get("name", ""),
        "items": [],
    }
    items = manifest.get("items")
    if not isinstance(items, list):
        items = []
        manifest["items"] = items

    title = str(payload.get("title", "") or "").strip()
    description = str(payload.get("description", "") or "").strip()
    if not title or not description:
        raise ValueError("请先填写任务标题和任务描述。")

    task_id = f"manual-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(title)[:40]}"
    targets = payload.get("targets") if isinstance(payload.get("targets"), list) else []
    entry_stage = str(payload.get("stage", "plan"))
    risk_level = str(payload.get("risk_level", "medium") or "medium")

    # 处理instruction_path：如果payload中提供则使用，否则自动生成
    instruction_path = str(payload.get("instruction_path", "") or "").strip()
    if not instruction_path:
        # 自动生成指令文件
        chat_instructions_dir = RUNTIME_ROOT / ".openclaw" / "chat_instructions"
        chat_instructions_dir.mkdir(parents=True, exist_ok=True)

        # 创建安全的文件名
        safe_title = slugify(title)[:100]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        instruction_filename = f"chat_task_{timestamp}_{safe_title}.md"
        instruction_path = str(chat_instructions_dir / instruction_filename)

        # 写入指令内容
        instruction_content = f"""# 聊天转换任务: {title}

## 任务描述
{description}

## 来源
此任务由用户聊天消息自动转换生成。

## 原始消息
```
{description.split("用户聊天消息:")[-1].strip() if "用户聊天消息:" in description else description}
```

## 执行要求
请根据用户聊天消息的内容，理解用户意图并提供相应的响应或执行相应的操作。

## 验收标准
1. 用户请求得到妥善处理
2. 提供有意义的响应或执行相应的操作
3. 任务完成后记录执行结果

---
**生成时间**: {datetime.now().isoformat()}
**任务ID**: {task_id}
**风险等级**: {risk_level}
"""

        try:
            with open(instruction_path, "w", encoding="utf-8") as f:
                f.write(instruction_content)
        except Exception as e:
            print(f"警告: 无法创建指令文件 {instruction_path}: {e}")
            # 使用临时文件作为后备方案
            import tempfile

            temp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            )
            temp_file.write(instruction_content)
            temp_file.close()
            instruction_path = temp_file.name

    item = {
        "id": task_id,
        "title": title,
        "description": description,
        "entry_stage": entry_stage,
        "risk_level": risk_level,
        "instruction_path": instruction_path,
        "targets": [str(target).strip() for target in targets if str(target).strip()],
        "metadata": {
            "epic": "manual_created",
            "created_via": "athena_web_desktop_compat",
            "created_at": now_iso(),
            "instruction_auto_generated": "instruction_path" not in payload,  # 标记是否自动生成
        },
    }
    items.append(item)
    write_json(manifest_path, manifest)
    return {
        "id": task_id,
        "title": title,
        "stage": entry_stage,
        "executor": (
            "codex"
            if entry_stage in {"plan", "review"}
            else "opencode"
            if entry_stage == "build"
            else "local"
        ),
        "risk_level": risk_level,
        "status": "pending",
        "instruction_path": instruction_path,
    }


def retry_failed_items() -> dict[str, Any]:
    config = load_plan_config()
    retried: list[str] = []
    for route in config.get("routes", []):
        state_path = route_state_path(route)
        payload = read_json(state_path, default=None)
        if not isinstance(payload, dict):
            continue
        changed = False
        for item_id, item_state in (payload.get("items") or {}).items():
            if str(item_state.get("status", "")) != "failed":
                continue
            item_state["status"] = "pending"
            item_state["summary"] = ""
            item_state["error"] = ""
            item_state["result_excerpt"] = ""
            item_state["pipeline_summary"] = ""
            item_state["artifact_paths"] = []
            item_state["finished_at"] = ""
            item_state["root_task_id"] = ""
            item_state["progress_percent"] = 0
            retried.append(item_id)
            changed = True
        if changed:
            payload["current_item_id"] = ""
            payload["updated_at"] = now_iso()
            write_json(state_path, payload)
    if not retried:
        return {"ok": False, "message": "没有可拉起的失败执行项。", "retried": []}
    return {
        "ok": True,
        "message": f"已重置 {len(retried)} 个失败执行项。",
        "retried": retried,
    }


def route_from_id(route_id: str) -> dict[str, Any] | None:
    for route in load_plan_config().get("routes", []):
        if str(route.get("route_id", "") or "") == route_id:
            return route
    return None


def dependency_state_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for route in load_plan_config().get("routes", []):
        route_state = load_route_state(route)
        for queued_item_id, state_item in (route_state.get("items") or {}).items():
            if isinstance(state_item, dict):
                index[str(queued_item_id)] = state_item
    return index


def unresolved_dependencies_for_item(
    route: dict[str, Any], manifest_item: dict[str, Any]
) -> list[tuple[str, str]]:
    metadata = (
        manifest_item.get("metadata") if isinstance(manifest_item.get("metadata"), dict) else {}
    )
    depends_on = metadata.get("depends_on") if isinstance(metadata.get("depends_on"), list) else []
    if not depends_on:
        return []

    route_state = load_route_state(route)
    route_items = route_state.get("items") or {}
    all_state = dependency_state_index()
    blockers: list[tuple[str, str]] = []
    for dep_id in depends_on:
        dep_key = str(dep_id)
        dep_state = route_items.get(dep_key) or all_state.get(dep_key) or {}
        dep_status = str(dep_state.get("status", "") or "pending")
        if dep_status != "completed":
            blockers.append((dep_key, dep_status))
    return blockers


def ensure_runner_for_mode(runner_mode: str) -> dict[str, Any]:
    script_map = {
        "opencode_build": RUNTIME_ROOT / "scripts" / "start_athena_ai_plan_runner.sh",
        "codex_review": RUNTIME_ROOT / "scripts" / "start_codex_review_runner.sh",
        "codex_plan": RUNTIME_ROOT / "scripts" / "start_codex_plan_runner.sh",
    }
    script = script_map.get(runner_mode)
    if script is None:
        return {
            "ok": True,
            "message": f"当前 route 模式为 {runner_mode or 'manual'}，未配置自动 consumer。",
        }
    try:
        completed = subprocess.run(
            [str(script)],
            cwd=str(RUNTIME_ROOT),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except Exception as error:
        return {"ok": False, "message": f"拉起 {runner_mode} runner 失败: {error}"}
    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        return {
            "ok": False,
            "message": output or f"拉起 {runner_mode} runner 失败（exit {completed.returncode}）",
        }
    return {"ok": True, "message": output or f"{runner_mode} runner 已就绪。"}


def launch_queue_item(route_id: str, item_id: str) -> dict[str, Any]:
    route = route_from_id(route_id)
    if route is None:
        return {"ok": False, "message": f"未找到 route: {route_id}"}

    manifest_items = load_manifest_items(route)
    manifest_item = next(
        (item for item in manifest_items if str(item.get("id", "") or "") == item_id),
        None,
    )
    if manifest_item is None:
        return {"ok": False, "message": f"未找到队列项: {item_id}"}

    route_state = load_route_state(route)
    state_items = route_state.setdefault("items", {})
    state_item = state_items.setdefault(item_id, {})

    current_item_ids = route_state.get("current_item_ids")
    if not isinstance(current_item_ids, list):
        current_item_ids = []

    current_status = str(state_item.get("status", "") or "")
    metadata = (
        manifest_item.get("metadata") if isinstance(manifest_item.get("metadata"), dict) else {}
    )
    if not current_status:
        current_status = "manual_hold" if metadata.get("autostart") is False else "pending"

    if current_status == "running" and item_id in current_item_ids:
        return {"ok": True, "message": f"{item_id} 已在运行，无需重复拉起。"}

    action_label = "重跑" if current_status == "completed" else "拉起"
    blockers = unresolved_dependencies_for_item(route, manifest_item)
    state_item["status"] = "pending"
    if blockers:
        blocker_text = "，".join(f"{dep_id}({status or 'pending'})" for dep_id, status in blockers)
        state_item["summary"] = f"已手动{action_label}，但仍被依赖项阻塞：{blocker_text}。"
        state_item["pipeline_summary"] = "dependency blocked"
    else:
        state_item["summary"] = f"已手动{action_label}，等待 queue runner 接手。"
        state_item["pipeline_summary"] = ""
    state_item["error"] = ""
    state_item["result_excerpt"] = ""
    state_item["artifact_paths"] = []
    state_item["finished_at"] = ""
    state_item["started_at"] = ""
    state_item["root_task_id"] = ""
    state_item["progress_percent"] = 0
    state_item["current_stage_ids"] = []
    state_item["runner_pid"] = None
    state_item["runner_heartbeat_at"] = ""
    state_item["manual_override_autostart"] = True
    if state_item.get("executor") is None:
        state_item["executor"] = ""

    route_state["current_item_id"] = (
        ""
        if str(route_state.get("current_item_id", "") or "") == item_id
        else str(route_state.get("current_item_id", "") or "")
    )
    route_state["current_item_ids"] = [
        current for current in current_item_ids if current != item_id
    ]
    route_state["updated_at"] = now_iso()
    write_json(route_state_path(route), route_state)

    runner_status = ensure_runner_for_mode(str(route.get("runner_mode", "") or ""))
    runner_message = runner_status.get("message", "")
    if blockers:
        blocker_text = "，".join(f"{dep_id}({status or 'pending'})" for dep_id, status in blockers)
        message = f"{item_id} 已登记手动{action_label}，但当前仍被依赖项阻塞：{blocker_text}。"
    else:
        message = f"已手动{action_label} {item_id}。"
    if runner_message:
        message = f"{message} {runner_message}"
    return {
        "ok": bool(runner_status.get("ok", False) or runner_message),
        "message": message,
        "item_id": item_id,
        "route_id": route_id,
        "runner": runner_status,
        "blocked_dependencies": [
            {"item_id": dep_id, "status": status} for dep_id, status in blockers
        ],
    }


def task_artifact(task_id: str) -> tuple[int, dict[str, Any]]:
    task_dir = RUNTIME_ROOT / ".openclaw" / "orchestrator" / "tasks" / task_id
    if not task_dir.exists():
        return HTTPStatus.NOT_FOUND, {
            "error": "artifact_not_found",
            "message": "当前任务没有可预览的 artifact。",
        }
    candidates = [
        task_dir / "plan.md",
        task_dir / "review.md",
        task_dir / "qa.md",
        task_dir / "think.md",
        task_dir / "build.md",
        task_dir / "artifact.md",
        task_dir / "request.json",
        task_dir / "stdout.log",
    ]
    for candidate in candidates:
        if candidate.exists():
            return HTTPStatus.OK, {
                "artifact_path": str(candidate),
                "content": candidate.read_text(encoding="utf-8"),
            }
    return HTTPStatus.OK, {
        "artifact_path": str(task_dir),
        "message": "当前任务目录存在，但还没有可预览的标准 artifact。",
    }


class AthenaCompatHandler(BaseHTTPRequestHandler):
    server_version = "AthenaCompat/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        line = f"{self.address_string()} - - [{self.log_date_time_string()}] {format % args}\n"
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (LOG_DIR / "athena_web_desktop_compat.log").open("a", encoding="utf-8") as handle:
            handle.write(line)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Date", formatdate(usegmt=True))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: int, body: str, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Date", formatdate(usegmt=True))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Date", formatdate(usegmt=True))
        self.end_headers()
        self.wfile.write(data)

    def _authorized(self) -> bool:
        return self.headers.get("X-OpenClaw-Token", "") == AUTH_TOKEN

    def _require_auth(self) -> bool:
        if self._authorized():
            return True
        self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        return False

    def _read_json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        route = parsed.path

        if route in {"/", "/legacy/"}:
            html = INDEX_HTML.replace("__AUTH_TOKEN__", AUTH_TOKEN).replace(
                "__ASSET_VERSION__", asset_version()
            )
            self._send_text(HTTPStatus.OK, html, "text/html; charset=utf-8")
            return

        if route == "/athena/static/chat_window.js":
            self._send_file(STATIC_JS, "application/javascript; charset=utf-8")
            return

        if route == "/athena/static/chat_window.css":
            self._send_file(STATIC_CSS, "text/css; charset=utf-8")
            return

        if route == "/api/status":
            if not self._require_auth():
                return
            self._send_json(HTTPStatus.OK, build_basic_status())
            return

        if route == "/api/athena/status":
            if not self._require_auth():
                return
            self._send_json(HTTPStatus.OK, build_status_payload())
            return

        if route == "/api/athena/queues":
            if not self._require_auth():
                return
            self._send_json(HTTPStatus.OK, build_queue_payload())
            return

        # 成本监控API端点
        if route == "/api/cost/summary":
            if not self._require_auth():
                return
            self._send_json(HTTPStatus.OK, build_cost_summary())
            return

        if route == "/api/cost/provider-breakdown":
            if not self._require_auth():
                return
            self._send_json(HTTPStatus.OK, build_cost_provider_breakdown())
            return

        if route == "/api/cost/task-kind-analysis":
            if not self._require_auth():
                return
            self._send_json(HTTPStatus.OK, build_cost_task_kind_analysis())
            return

        if route == "/api/cost/savings":
            if not self._require_auth():
                return
            self._send_json(HTTPStatus.OK, build_cost_savings())
            return

        artifact_match = re.fullmatch(r"/api/athena/tasks/([^/]+)/artifact", route)
        if artifact_match:
            if not self._require_auth():
                return
            status, payload = task_artifact(urllib.parse.unquote(artifact_match.group(1)))
            self._send_json(status, payload)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        route = parsed.path
        if not self._require_auth():
            return

        if route == "/api/athena/chat":
            payload = self._read_json_body()
            message = payload.get("message", "")

            if message:
                # 将聊天消息转换为任务
                task_data = {
                    "title": (
                        f"聊天请求: {message[:50]}..."
                        if len(message) > 50
                        else f"聊天请求: {message}"
                    ),
                    "description": f"用户聊天消息: {message}\n\n此请求通过聊天兼容层自动转换为任务处理。",
                    "stage": "build",
                    "risk_level": "low",
                    "targets": ["chat_conversion"],
                }

                try:
                    task = create_manifest_task(task_data)
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "success": True,
                            "response": f"聊天请求已转换为任务 #{task.get('id')}，请通过任务系统查看结果。",
                            "task_id": task.get("id"),
                            "task_title": task.get("title"),
                            "status": "converted",
                        },
                    )
                except Exception as e:
                    # 如果任务创建失败，返回原始兼容消息
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "success": True,
                            "response": "Athena 兼容入口已恢复，但聊天桥接当前只保留最小兼容模式。规划、修复、审查、测试、调研类请求建议直接创建编排任务进入队列。",
                            "error": str(e),
                            "status": "compatibility_mode",
                        },
                    )
            else:
                # 如果没有消息内容，返回原始兼容消息
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "success": True,
                        "response": "Athena 兼容入口已恢复，但聊天桥接当前只保留最小兼容模式。规划、修复、审查、测试、调研类请求建议直接创建编排任务进入队列。",
                        "status": "compatibility_mode",
                    },
                )
            return

        if route == "/api/athena/tasks":
            payload = self._read_json_body()
            try:
                task = create_manifest_task(payload)
            except ValueError as error:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return
            except Exception as error:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": f"任务写入失败: {error}"},
                )
                return
            self._send_json(HTTPStatus.OK, {"ok": True, "task": task})
            return

        if route == "/api/athena/queues/retry-failed":
            self._send_json(HTTPStatus.OK, retry_failed_items())
            return

        launch_match = re.fullmatch(r"/api/athena/queues/items/([^/]+)/([^/]+)/launch", route)
        if launch_match:
            payload = launch_queue_item(
                urllib.parse.unquote(launch_match.group(1)),
                urllib.parse.unquote(launch_match.group(2)),
            )
            status = HTTPStatus.OK if payload.get("ok") else HTTPStatus.BAD_REQUEST
            self._send_json(status, payload)
            return

        run_match = re.fullmatch(r"/api/athena/tasks/([^/]+)/run", route)
        if run_match:
            self._send_json(
                HTTPStatus.CONFLICT,
                {
                    "error": "run_not_supported",
                    "message": "兼容模式当前不直接拉起 build runner，请先修复正式 queue runner 后再恢复自动执行。",
                },
            )
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")


def main() -> None:
    QUEUE_STATE_DIR.mkdir(parents=True, exist_ok=True)
    WEB_PORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    WEB_PORT_FILE.write_text(str(PORT) + "\n", encoding="utf-8")

    server = ThreadingHTTPServer((HOST, PORT), AthenaCompatHandler)
    server.daemon_threads = True
    print(f"Athena Web Desktop compat listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
