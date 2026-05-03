"""Human Gate v2 — 4-layer identity model (Creator/Reviewer/Executor/Observer).

Each identity has distinct permissions and is enforced at all three blocking layers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto


class IdentityRole(Enum):
    CREATOR = auto()
    REVIEWER = auto()
    EXECUTOR = auto()
    OBSERVER = auto()


ROLE_PERMISSIONS: dict[IdentityRole, list[str]] = {
    IdentityRole.CREATOR: ["create", "read", "update", "delete", "approve", "manage"],
    IdentityRole.REVIEWER: ["read", "approve", "reject", "audit"],
    IdentityRole.EXECUTOR: ["read", "execute", "write_logs"],
    IdentityRole.OBSERVER: ["read", "subscribe"],
}


@dataclass
class Identity:
    id: str
    role: IdentityRole
    name: str = ""
    public_key: str = ""
    registered: float = field(default_factory=time.time)

    def can(self, action: str) -> bool:
        return action in ROLE_PERMISSIONS.get(self.role, [])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role.name,
            "name": self.name,
            "public_key": self.public_key,
            "registered": self.registered,
        }


class IdentityManager:
    """Manages identities and enforces role-based access."""

    def __init__(self, secret: str = "") -> None:
        self._identities: dict[str, Identity] = {}
        self._secret = secret

    def register(self, identity: Identity) -> None:
        self._identities[identity.id] = identity

    def get(self, identity_id: str) -> Identity | None:
        return self._identities.get(identity_id)

    def authorize(self, identity_id: str, action: str) -> bool:
        ident = self._identities.get(identity_id)
        if not ident:
            return False
        return ident.can(action)

    def sign_operation(self, identity_id: str, operation: dict) -> str:
        payload = json.dumps(operation, sort_keys=True)
        return hmac.new(
            self._secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
