"""Coordinator Mode v0.2.0 — Sub-agent fork and teammate monitoring."""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .session import AgentSession, AgentStatus, SessionManager

logger = logging.getLogger(__name__)


@dataclass
class ForkResult:
    success: bool
    agent_id: str
    pid: int
    worktree: str
    error: str = ""


class AgentFork:
    """Forks sub-agents with isolated worktrees and independent contexts."""

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        base_repo: str | Path | None = None,
    ) -> None:
        self.sessions = session_manager or SessionManager()
        self.base_repo = Path(base_repo or Path.cwd())

    def fork(
        self,
        agent_id: str,
        command: list[str] | None = None,
        worktree_path: str = "",
        env: dict[str, str] | None = None,
    ) -> ForkResult:
        session = self.sessions.register(agent_id)

        if worktree_path:
            session.worktree_path = worktree_path
            cwd = worktree_path
        else:
            cwd = str(self.base_repo)

        cmd = command or ["python3", "-c", "print('Agent started')"]
        session.status = AgentStatus.BUSY
        session.task_count += 1

        try:
            import os as _os
            proc_env = _os.environ.copy()
            if env:
                proc_env.update(env)
            proc_env["AGENT_ID"] = agent_id

            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=proc_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            session.metadata["pid"] = proc.pid
            self.sessions.update_heartbeat(agent_id)
            return ForkResult(
                success=True,
                agent_id=agent_id,
                pid=proc.pid,
                worktree=cwd,
            )
        except Exception as e:
            session.status = AgentStatus.ERROR
            session.error_count += 1
            return ForkResult(
                success=False,
                agent_id=agent_id,
                pid=-1,
                worktree=cwd,
                error=str(e),
            )


class TeammateMonitor:
    """Monitors agent teammate status and health."""

    def __init__(self, session_manager: SessionManager | None = None) -> None:
        self.sessions = session_manager or SessionManager()
        self._alerts: list[dict] = []

    def check_all(self) -> list[dict]:
        results: list[dict] = []
        for agent_id, session in self.sessions._sessions.items():
            status = self._check_agent(agent_id, session)
            results.append(status)
        return results

    def _check_agent(self, agent_id: str, session: AgentSession) -> dict:
        result = {
            "agent_id": agent_id,
            "status": session.status.name,
            "healthy": True,
            "issues": [],
        }
        pid = session.metadata.get("pid")
        if pid:
            try:
                import os
                os.kill(pid, 0)
            except (OSError, ProcessLookupError):
                result["healthy"] = False
                result["issues"].append("Process not running")
                session.status = AgentStatus.OFFLINE

        now = time.time()
        if now - session.last_heartbeat > 120:
            result["healthy"] = False
            result["issues"].append(f"No heartbeat for {now - session.last_heartbeat:.0f}s")
            session.status = AgentStatus.ERROR

        if session.error_count > 5:
            result["healthy"] = False
            result["issues"].append(f"Excessive errors ({session.error_count})")

        return result

    def alert(self, agent_id: str, issue: str) -> None:
        self._alerts.append({
            "agent_id": agent_id,
            "issue": issue,
            "timestamp": time.time(),
        })
        logger.warning(f"[Coordinator Alert] {agent_id}: {issue}")
