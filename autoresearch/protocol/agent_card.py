"""Men0 Protocol v2 — AgentCard service discovery with JWS signature."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field


@dataclass
class AgentCard:
    agent_id: str
    name: str
    skills: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    version: str = "2.0"
    endpoint: str = ""
    jws_signature: str = ""
    created: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def sign(self, secret: str) -> str:
        payload = json.dumps({
            "agent_id": self.agent_id,
            "name": self.name,
            "version": self.version,
            "created": self.created,
        }, sort_keys=True)
        self.jws_signature = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return self.jws_signature

    def verify(self, secret: str) -> bool:
        expected = hmac.new(
            secret.encode(),
            json.dumps({
                "agent_id": self.agent_id,
                "name": self.name,
                "version": self.version,
                "created": self.created,
            }, sort_keys=True).encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, self.jws_signature)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "skills": self.skills,
            "capabilities": self.capabilities,
            "version": self.version,
            "endpoint": self.endpoint,
            "jws_signature": self.jws_signature,
            "created": self.created,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentCard:
        return cls(
            agent_id=data.get("agent_id", ""),
            name=data.get("name", ""),
            skills=data.get("skills", []),
            capabilities=data.get("capabilities", []),
            version=data.get("version", "2.0"),
            endpoint=data.get("endpoint", ""),
            jws_signature=data.get("jws_signature", ""),
            created=data.get("created", time.time()),
            metadata=data.get("metadata", {}),
        )


class AgentRegistry:
    """In-memory AgentCard registry for service discovery."""

    def __init__(self) -> None:
        self._cards: dict[str, AgentCard] = {}

    def register(self, card: AgentCard, secret: str = "") -> None:
        if secret:
            card.sign(secret)
        self._cards[card.agent_id] = card

    def discover(self, agent_id: str) -> AgentCard | None:
        return self._cards.get(agent_id)

    def discover_by_skill(self, skill: str) -> list[AgentCard]:
        return [c for c in self._cards.values() if skill in c.skills]

    def discover_by_capability(self, capability: str) -> list[AgentCard]:
        return [c for c in self._cards.values() if capability in c.capabilities]

    def all_agents(self) -> dict[str, AgentCard]:
        return dict(self._cards)
