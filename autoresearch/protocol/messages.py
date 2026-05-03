"""Men0 Protocol v2 — JSONL message format and message types.

Message types:
  ROUTE    — Route a task to an agent
  SCHEDULE — Schedule execution time/resources
  ACTIVATE — Activate/deactivate capabilities

All messages are JSONL (one JSON object per line, newline-delimited).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class MessageType(Enum):
    ROUTE = "ROUTE"
    SCHEDULE = "SCHEDULE"
    ACTIVATE = "ACTIVATE"
    HEARTBEAT = "HEARTBEAT"
    STATUS = "STATUS"
    APPROVAL = "APPROVAL"
    CANCEL = "CANCEL"
    ERROR = "ERROR"
    ACK = "ACK"


class TaskStatus(Enum):
    UNSPECIFIED = "UNSPECIFIED"
    WORKING = "WORKING"
    INPUT_REQUIRED = "INPUT_REQUIRED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


@dataclass
class Men0Message:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: MessageType = MessageType.HEARTBEAT
    sender: str = ""
    recipient: str = ""
    task_id: str = ""
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = ""
    version: str = "2.0"

    def to_jsonl(self) -> str:
        data = {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "task_id": self.task_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "version": self.version,
        }
        return json.dumps(data, ensure_ascii=False) + "\n"

    @classmethod
    def from_jsonl(cls, line: str) -> Men0Message | None:
        try:
            data = json.loads(line.strip())
            return cls(
                id=data.get("id", ""),
                type=MessageType(data.get("type", "HEARTBEAT")),
                sender=data.get("sender", ""),
                recipient=data.get("recipient", ""),
                task_id=data.get("task_id", ""),
                payload=data.get("payload", {}),
                timestamp=data.get("timestamp", time.time()),
                correlation_id=data.get("correlation_id", ""),
                version=data.get("version", "2.0"),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None


def route_message(agent_id: str, task_id: str, payload: dict | None = None) -> Men0Message:
    return Men0Message(
        type=MessageType.ROUTE,
        recipient=agent_id,
        task_id=task_id,
        payload=payload or {},
    )


def schedule_message(agent_id: str, task_id: str, schedule_at: float | None = None) -> Men0Message:
    return Men0Message(
        type=MessageType.SCHEDULE,
        recipient=agent_id,
        task_id=task_id,
        payload={"schedule_at": schedule_at or time.time()},
    )


def activate_message(agent_id: str, capability: str, enabled: bool = True) -> Men0Message:
    return Men0Message(
        type=MessageType.ACTIVATE,
        recipient=agent_id,
        payload={"capability": capability, "enabled": enabled},
    )


def approval_message(task_id: str, approved: bool, reviewer: str = "") -> Men0Message:
    return Men0Message(
        type=MessageType.APPROVAL,
        task_id=task_id,
        sender=reviewer,
        payload={"approved": approved, "reviewer": reviewer},
    )
