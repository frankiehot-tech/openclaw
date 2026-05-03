"""DeerFlow v2 — Symphony polling-declaration protocol.

Symphony protocol enables agents to:
  1. Poll for ready tasks (declarative subscription)
  2. Claim tasks with optimistic locking
  3. Report completion with structured output
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class TaskState(Enum):
    UNCLAIMED = auto()
    CLAIMED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    WAITING_APPROVAL = auto()


@dataclass
class SymphonyTask:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    description: str = ""
    state: TaskState = TaskState.UNCLAIMED
    claimed_by: str = ""
    claimed_at: float = 0.0
    completed_at: float = 0.0
    result: dict = field(default_factory=dict)
    approval_required: bool = False
    approved_by: str = ""
    priority: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def stale(self) -> bool:
        if self.state == TaskState.CLAIMED:
            return (time.time() - self.claimed_at) > 600
        return False


class SymphonyBoard:
    """Shared task board for Symphony polling protocol."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self._tasks: dict[str, SymphonyTask] = {}
        self._storage = Path(storage_path or ".openclaw/symphony_tasks.json")
        self.load()

    def publish(self, task: SymphonyTask) -> None:
        self._tasks[task.task_id] = task
        self.save()

    def poll(self, agent_id: str, tags: list[str] | None = None, limit: int = 5) -> list[SymphonyTask]:
        available: list[SymphonyTask] = []
        for task in self._tasks.values():
            if task.state != TaskState.UNCLAIMED:
                continue
            if task.stale:
                task.state = TaskState.UNCLAIMED
                task.claimed_by = ""
            if tags and not any(t in task.tags for t in tags):
                continue
            available.append(task)

        available.sort(key=lambda t: (-t.priority, t.task_id))
        return available[:limit]

    def claim(self, task_id: str, agent_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.state != TaskState.UNCLAIMED:
            return False
        task.state = TaskState.CLAIMED
        task.claimed_by = agent_id
        task.claimed_at = time.time()
        self.save()
        return True

    def report(self, task_id: str, agent_id: str, success: bool, result: dict | None = None) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.claimed_by != agent_id:
            return False
        task.state = TaskState.COMPLETED if success else TaskState.FAILED
        task.completed_at = time.time()
        task.result = result or {}
        if task.approval_required and success:
            task.state = TaskState.WAITING_APPROVAL
        self.save()
        return True

    def approve(self, task_id: str, reviewer_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.state != TaskState.WAITING_APPROVAL:
            return False
        task.state = TaskState.COMPLETED
        task.approved_by = reviewer_id
        self.save()
        return True

    def save(self) -> None:
        self._storage.parent.mkdir(parents=True, exist_ok=True)
        data = {
            tid: {
                "task_id": t.task_id,
                "name": t.name,
                "state": t.state.name,
                "claimed_by": t.claimed_by,
                "claimed_at": t.claimed_at,
                "completed_at": t.completed_at,
                "priority": t.priority,
                "tags": t.tags,
            }
            for tid, t in self._tasks.items()
        }
        self._storage.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def load(self) -> None:
        if self._storage.exists():
            with open(self._storage) as f:
                data = json.load(f)
            for tid, tdata in data.items():
                task = SymphonyTask(task_id=tid, name=tdata.get("name", ""))
                task.state = TaskState[tdata.get("state", "UNCLAIMED")]
                task.claimed_by = tdata.get("claimed_by", "")
                task.claimed_at = tdata.get("claimed_at", 0.0)
                task.completed_at = tdata.get("completed_at", 0.0)
                task.priority = tdata.get("priority", 0)
                task.tags = tdata.get("tags", [])
                self._tasks[tid] = task

    @property
    def stats(self) -> dict:
        states = {s.name: 0 for s in TaskState}
        for t in self._tasks.values():
            states[t.state.name] += 1
        states["total"] = len(self._tasks)
        return states
