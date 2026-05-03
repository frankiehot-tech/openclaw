"""Men0 Protocol v2 — 9-state task machine.

Compatible with A2A v1.0.0 task states:
  UNSPECIFIED → WORKING → INPUT_REQUIRED | AUTH_REQUIRED
  → COMPLETED | FAILED | CANCELED | REJECTED
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class State(Enum):
    UNSPECIFIED = auto()
    WORKING = auto()
    INPUT_REQUIRED = auto()
    AUTH_REQUIRED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELED = auto()
    REJECTED = auto()


VALID_TRANSITIONS: dict[State, set[State]] = {
    State.UNSPECIFIED: {State.WORKING, State.CANCELED},
    State.WORKING: {
        State.INPUT_REQUIRED,
        State.AUTH_REQUIRED,
        State.COMPLETED,
        State.FAILED,
        State.CANCELED,
    },
    State.INPUT_REQUIRED: {State.WORKING, State.CANCELED, State.FAILED},
    State.AUTH_REQUIRED: {State.WORKING, State.REJECTED, State.CANCELED, State.FAILED},
    State.COMPLETED: set(),
    State.FAILED: {State.WORKING},
    State.CANCELED: {State.WORKING},
    State.REJECTED: {State.WORKING},
}


@dataclass
class TaskState:
    task_id: str
    state: State = State.UNSPECIFIED
    history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def transition(self, new_state: State, reason: str = "") -> bool:
        if new_state not in VALID_TRANSITIONS.get(self.state, set()):
            return False
        self.history.append({
            "from": self.state.name,
            "to": new_state.name,
            "reason": reason,
        })
        self.state = new_state
        return True

    @property
    def terminal(self) -> bool:
        return self.state in {
            State.COMPLETED,
            State.FAILED,
            State.CANCELED,
            State.REJECTED,
        }

    @property
    def a2a_state(self) -> str:
        mapping = {
            State.UNSPECIFIED: "unspecified",
            State.WORKING: "working",
            State.INPUT_REQUIRED: "input-required",
            State.AUTH_REQUIRED: "auth-required",
            State.COMPLETED: "completed",
            State.FAILED: "failed",
            State.CANCELED: "canceled",
            State.REJECTED: "rejected",
        }
        return mapping.get(self.state, "unspecified")


class TaskStateManager:
    """Manages task state machines for multiple tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskState] = {}

    def create(self, task_id: str, metadata: dict[str, Any] | None = None) -> TaskState:
        task = TaskState(task_id=task_id, metadata=metadata or {})
        self._tasks[task_id] = task
        task.transition(State.WORKING, "Task created")
        return task

    def get(self, task_id: str) -> TaskState | None:
        return self._tasks.get(task_id)

    def transition(self, task_id: str, new_state: State, reason: str = "") -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        return task.transition(new_state, reason)

    def all_tasks(self) -> dict[str, TaskState]:
        return dict(self._tasks)

    def active_tasks(self) -> dict[str, TaskState]:
        return {k: v for k, v in self._tasks.items() if not v.terminal}
