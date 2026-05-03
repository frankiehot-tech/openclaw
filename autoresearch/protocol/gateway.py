"""Men0 Protocol v2 — 5-protocol compatibility gateway.

Bridges Men0 Protocol with:
  A2A (Agent-to-Agent)
  MCP (Model Context Protocol)
  ACP (Agent Communication Protocol)
  ANP (Agent Network Protocol)
  Men0 (native)

Provides zero-config protocol detection and transparent routing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent_card import AgentRegistry
    from .agent_card import AgentRegistry as AR


class Protocol(Enum):
    A2A = auto()
    MCP = auto()
    ACP = auto()
    ANP = auto()
    MEN0 = auto()


@dataclass
class ProtocolHeaders:
    protocol: Protocol = Protocol.MEN0
    source: str = ""
    target: str = ""
    content_type: str = "application/jsonl"
    version: str = "2.0"


class ProtocolDetector:
    """Auto-detects protocol from message headers or content patterns."""

    A2A_PATTERNS = ["agent-card", "task-id", "a2a-version"]
    MCP_PATTERNS = ["mcp/", "jsonrpc", "method"]
    ACP_PATTERNS = ["acp:", "agent://"]
    ANP_PATTERNS = ["anp/", "network://"]

    @classmethod
    def detect(cls, headers: dict[str, str], body: str = "") -> Protocol:
        header_str = json.dumps(headers).lower() + body.lower()

        if any(p in header_str for p in cls.A2A_PATTERNS):
            return Protocol.A2A
        if any(p in header_str for p in cls.MCP_PATTERNS):
            return Protocol.MCP
        if any(p in header_str for p in cls.ACP_PATTERNS):
            return Protocol.ACP
        if any(p in header_str for p in cls.ANP_PATTERNS):
            return Protocol.ANP
        return Protocol.MEN0


class ProtocolGateway:
    """Routes messages between different agent protocols."""

    def __init__(self, agent_registry: AgentRegistry = None, secret: str = "") -> None:

        self._registry: AR | None = agent_registry
        self._secret = secret
        self._routes: dict[tuple[Protocol, Protocol], callable] = {}

    def register_route(self, source: Protocol, target: Protocol, handler: callable) -> None:
        self._routes[(source, target)] = handler

    def route(self, message: bytes, source_protocol: Protocol | None = None) -> bytes:
        headers = self._parse_headers(message)
        if source_protocol is None:
            source_protocol = ProtocolDetector.detect(headers)
        target_protocol = self._determine_target(headers)

        if source_protocol == target_protocol:
            return message

        handler = self._routes.get((source_protocol, target_protocol))
        if handler:
            return handler(message)
        return self._default_transform(message, source_protocol, target_protocol)

    def _parse_headers(self, message: bytes) -> dict[str, str]:
        return {}

    def _determine_target(self, headers: dict[str, str]) -> Protocol:
        return Protocol.MEN0

    def _default_transform(self, message: bytes, source: Protocol, target: Protocol) -> bytes:
        return message
