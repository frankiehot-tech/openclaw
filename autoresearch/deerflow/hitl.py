"""DeerFlow v2 — HITL (Human-in-the-Loop) graded approval.

Three approval levels:
  P0 (RED)   — BLOCK immediately, human must approve
  P1 (YELLOW)— WARN but auto-continue after timeout
  P2 (GREEN) — Auto-approve, log for audit
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

logger = logging.getLogger(__name__)


class HITLLevel(Enum):
    P0_BLOCK = auto()
    P1_WARN = auto()
    P2_AUTO = auto()


@dataclass
class ApprovalRequest:
    request_id: str
    action: str
    level: HITLLevel
    context: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"
    timeout_seconds: int = 300


class HITLEngine:
    """Human-in-the-Loop approval engine with graded blocking."""

    def __init__(self, storage_path: str | Path | None = None, p1_timeout: int = 300) -> None:
        self._storage = Path(storage_path or ".openclaw/hitl_requests")
        self._storage.mkdir(parents=True, exist_ok=True)
        self.p1_timeout = p1_timeout
        self._p0_rules: list[callable] = []
        self._p1_rules: list[callable] = []

    def register_p0_rule(self, rule: callable) -> None:
        self._p0_rules.append(rule)

    def register_p1_rule(self, rule: callable) -> None:
        self._p1_rules.append(rule)

    def evaluate(self, action: str, context: dict | None = None) -> HITLLevel:
        ctx = context or {}
        for rule in self._p0_rules:
            if rule(action, ctx):
                return HITLLevel.P0_BLOCK
        for rule in self._p1_rules:
            if rule(action, ctx):
                return HITLLevel.P1_WARN
        return HITLLevel.P2_AUTO

    def request_approval(self, action: str, context: dict | None = None) -> ApprovalRequest:
        level = self.evaluate(action, context)
        req = ApprovalRequest(
            request_id=f"hitl-{int(time.time())}",
            action=action,
            level=level,
            context=context or {},
        )

        if level == HITLLevel.P2_AUTO:
            req.status = "auto_approved"
        else:
            req.status = "pending"
            self._persist(req)

        return req

    def approve(self, request_id: str) -> bool:
        path = self._storage / f"{request_id}.json"
        if not path.exists():
            return False
        with open(path) as f:
            data = json.load(f)
        data["status"] = "approved"
        data["approved_at"] = time.time()
        path.write_text(json.dumps(data, indent=2))
        return True

    def reject(self, request_id: str) -> bool:
        path = self._storage / f"{request_id}.json"
        if not path.exists():
            return False
        with open(path) as f:
            data = json.load(f)
        data["status"] = "rejected"
        path.write_text(json.dumps(data, indent=2))
        return True

    def check_timeout(self, request_id: str) -> bool:
        path = self._storage / f"{request_id}.json"
        if not path.exists():
            return False
        with open(path) as f:
            data = json.load(f)
        if data.get("status") != "pending":
            return False
        elapsed = time.time() - data.get("timestamp", 0)
        return elapsed > self.p1_timeout

    def pending(self) -> list[dict]:
        pending_list: list[dict] = []
        for path in self._storage.glob("*.json"):
            with open(path) as f:
                data = json.load(f)
            if data.get("status") == "pending":
                pending_list.append(data)
        return pending_list

    def _persist(self, req: ApprovalRequest) -> None:
        path = self._storage / f"{req.request_id}.json"
        path.write_text(json.dumps({
            "request_id": req.request_id,
            "action": req.action,
            "level": req.level.name,
            "context": req.context,
            "timestamp": req.timestamp,
            "status": req.status,
            "timeout_seconds": req.timeout_seconds,
        }, indent=2, ensure_ascii=False))


def default_p0_rules(action: str, ctx: dict) -> bool:
    p0_actions = [
        "delete_production_data", "modify_security_groups",
        "rotate_master_secrets", "change_billing",
        "drop_database", "modify_iam_policies",
    ]
    return action in p0_actions


def default_p1_rules(action: str, ctx: dict) -> bool:
    p1_actions = [
        "deploy_to_staging", "modify_config",
        "restart_services", "update_dependencies",
        "modify_feature_flags",
    ]
    return action in p1_actions
