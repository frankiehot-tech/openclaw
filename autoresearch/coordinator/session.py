"""Coordinator Mode v0.2.0 — Session matching and agent lifecycle."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    IDLE = auto()
    BUSY = auto()
    ERROR = auto()
    OFFLINE = auto()


@dataclass
class AgentSession:
    agent_id: str
    status: AgentStatus = AgentStatus.IDLE
    worktree_path: str = ""
    started: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    task_count: int = 0
    error_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class SessionContext:
    session_id: str
    agents: list[AgentSession] = field(default_factory=list)
    shared_state: dict = field(default_factory=dict)


class SessionManager:
    """Manages agent sessions and context sharing."""

    def __init__(self, max_agents: int = 8) -> None:
        self.max_agents = max_agents
        self._sessions: dict[str, AgentSession] = {}
        self._contexts: dict[str, SessionContext] = {}

    def register(self, agent_id: str) -> AgentSession:
        if len(self._sessions) >= self.max_agents and agent_id not in self._sessions:
            raise RuntimeError(f"Max agents ({self.max_agents}) reached")
        session = self._sessions.get(agent_id) or AgentSession(agent_id=agent_id)
        session.status = AgentStatus.IDLE
        session.last_heartbeat = time.time()
        self._sessions[agent_id] = session
        return session

    def update_heartbeat(self, agent_id: str) -> None:
        session = self._sessions.get(agent_id)
        if session:
            session.last_heartbeat = time.time()

    def set_status(self, agent_id: str, status: AgentStatus) -> None:
        session = self._sessions.get(agent_id)
        if not session:
            return
        session.status = status
        if status == AgentStatus.ERROR:
            session.error_count += 1

    def get_available(self) -> list[AgentSession]:
        return [s for s in self._sessions.values() if s.status == AgentStatus.IDLE]

    def create_context(self, session_id: str, agents: list[str] | None = None) -> SessionContext:
        ctx = SessionContext(session_id=session_id)
        if agents:
            ctx.agents = [self._sessions[a] for a in agents if a in self._sessions]
        self._contexts[session_id] = ctx
        return ctx

    def share_state(self, session_id: str, key: str, value: object) -> None:
        ctx = self._contexts.get(session_id)
        if ctx:
            ctx.shared_state[key] = value

    def get_context(self, session_id: str) -> SessionContext | None:
        return self._contexts.get(session_id)

    def cleanup_stale(self, max_idle_seconds: float = 600.0) -> int:
        now = time.time()
        stale = [
            aid for aid, s in self._sessions.items()
            if now - s.last_heartbeat > max_idle_seconds
        ]
        for aid in stale:
            self._sessions.pop(aid, None)
        return len(stale)
