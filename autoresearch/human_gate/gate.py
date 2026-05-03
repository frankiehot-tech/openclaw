"""Human Gate v2 — 3-layer blocking architecture with Exit Code 2 protocol.

Layer 1: Agent layer — Agent detects high-risk operations and requests approval
Layer 2: Protocol layer — Men0 Protocol enforces approval status, rejects unapproved
Layer 3: Caller layer — Must complete human approval before restarting agent

Exit Code 2: Protocol-layer signal meaning "human approval required before continuation".
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from .identity import IdentityManager

logger = logging.getLogger(__name__)

EXIT_CODE_HUMAN_GATE = 2

HIGH_RISK_ACTIONS = {
    "delete_production_data",
    "modify_permissions",
    "change_budget_limit",
    "deploy_to_production",
    "rotate_secrets",
    "modify_identity_roles",
    "change_approval_policy",
}


class GateAction(Enum):
    APPROVED = auto()
    REJECTED = auto()
    PENDING = auto()
    TIMED_OUT = auto()


class GateLayer(Enum):
    AGENT = 1
    PROTOCOL = 2
    CALLER = 3


@dataclass
class GateRequest:
    request_id: str
    action: str
    requester_id: str
    details: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    approval_chain: list[dict] = field(default_factory=list)
    status: GateAction = GateAction.PENDING
    blocked_layer: GateLayer | None = None


class AgentLayer:
    """Layer 1: Agent detects high-risk ops and exits with code 2."""

    def check_action(self, action: str, identity_id: str) -> GateRequest | None:
        if action in HIGH_RISK_ACTIONS:
            request = GateRequest(
                request_id=f"{identity_id}-{int(time.time())}",
                action=action,
                requester_id=identity_id,
                details={"risk_level": "high", "action": action},
            )
            request.blocked_layer = GateLayer.AGENT
            return request
        return None

    def exit_for_approval(self, request: GateRequest) -> None:
        logger.warning(f"Gate Layer 1 blocked: {request.action} by {request.requester_id}")
        request.status = GateAction.PENDING
        sys.exit(EXIT_CODE_HUMAN_GATE)
        # Never reaches here — caller must handle exit code 2


class ProtocolLayer:
    """Layer 2: Protocol enforces approval — no bypass possible."""

    def __init__(self, storage_path: str | Path = ".openclaw/gate_requests") -> None:
        self._storage = Path(storage_path)
        self._storage.mkdir(parents=True, exist_ok=True)

    def require_approval(self, request: GateRequest) -> bool:
        path = self._storage / f"{request.request_id}.json"
        if not path.exists():
            return False
        with open(path) as f:
            saved = json.load(f)
        return saved.get("status") == GateAction.APPROVED.name

    def reject_if_unapproved(self, request: GateRequest) -> GateRequest:
        if not self.require_approval(request):
            request.blocked_layer = GateLayer.PROTOCOL
            request.status = GateAction.REJECTED
            logger.warning(f"Gate Layer 2 blocked: {request.action} — no approval found")
            return request
        request.status = GateAction.APPROVED
        return request

    def persist(self, request: GateRequest) -> None:
        path = self._storage / f"{request.request_id}.json"
        path.write_text(json.dumps({
            "request_id": request.request_id,
            "action": request.action,
            "requester_id": request.requester_id,
            "details": request.details,
            "timestamp": request.timestamp,
            "approval_chain": request.approval_chain,
            "status": request.status.name,
        }, indent=2, ensure_ascii=False))


class CallerLayer:
    """Layer 3: Must complete human approval before restarting agent."""

    def __init__(self, storage_path: str | Path = ".openclaw/gate_requests") -> None:
        self._storage = Path(storage_path)

    def must_approve_before_restart(self, agent_id: str) -> list[GateRequest]:
        pending: list[GateRequest] = []
        for path in self._storage.glob("*.json"):
            with open(path) as f:
                data = json.load(f)
            if data.get("status") == GateAction.PENDING.name:
                pending.append(GateRequest(
                    request_id=data["request_id"],
                    action=data["action"],
                    requester_id=data["requester_id"],
                    details=data.get("details", {}),
                    timestamp=data.get("timestamp", 0.0),
                    status=GateAction.PENDING,
                ))
        return pending

    def approve(self, request_id: str, reviewer_id: str) -> bool:
        path = self._storage / f"{request_id}.json"
        if not path.exists():
            return False
        with open(path) as f:
            data = json.load(f)
        data["status"] = GateAction.APPROVED.name
        data.setdefault("approval_chain", []).append({
            "reviewer": reviewer_id,
            "timestamp": time.time(),
            "action": "approved",
        })
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return True

    def reject(self, request_id: str, reviewer_id: str, reason: str = "") -> bool:
        path = self._storage / f"{request_id}.json"
        if not path.exists():
            return False
        with open(path) as f:
            data = json.load(f)
        data["status"] = GateAction.REJECTED.name
        data.setdefault("approval_chain", []).append({
            "reviewer": reviewer_id,
            "timestamp": time.time(),
            "action": "rejected",
            "reason": reason,
        })
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return True


class HumanGate:
    """Orchestrates the 3-layer Human Gate v2 approval pipeline."""

    def __init__(
        self,
        identity_manager: IdentityManager | None = None,
        storage_path: str | Path = ".openclaw/gate_requests",
    ) -> None:
        self.identities = identity_manager or IdentityManager()
        self.layer1 = AgentLayer()
        self.layer2 = ProtocolLayer(storage_path)
        self.layer3 = CallerLayer(storage_path)

    def check_and_block(self, action: str, identity_id: str) -> GateRequest:
        request = self.layer1.check_action(action, identity_id)
        if request is None:
            return GateRequest(
                request_id="", action=action, requester_id=identity_id,
                status=GateAction.APPROVED,
            )
        self.layer2.persist(request)
        return request

    def verify_or_reject(self, request: GateRequest) -> GateRequest:
        if request.status == GateAction.APPROVED:
            return request
        return self.layer2.reject_if_unapproved(request)

    def human_approve(self, request_id: str, reviewer_id: str) -> bool:
        if not self.identities.authorize(reviewer_id, "approve"):
            logger.warning(f"Identity {reviewer_id} not authorized to approve")
            return False
        return self.layer3.approve(request_id, reviewer_id)

    def human_reject(self, request_id: str, reviewer_id: str, reason: str = "") -> bool:
        if not self.identities.authorize(reviewer_id, "reject"):
            return False
        return self.layer3.reject(request_id, reviewer_id, reason)

    def pending_approvals(self) -> list[GateRequest]:
        return self.layer3.must_approve_before_restart("")
