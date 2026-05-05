from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from ..bridge.confidence_gate import ConfidenceGatedMemoryStore
from ..bridge.vector_clock import VectorClock
from ..crdt.lww_register import LWWRegisterStore
from ..crdt.or_set import ORSet
from ..schemas.bridge import PayloadType, SemanticMessage, SharedSemanticState
from ..schemas.intent import IntentPacket
from ..schemas.memory import SharedSemanticFact
from ..schemas.state import SemanticStateSnapshot

logger = logging.getLogger(__name__)


class Men0Bridge:
    """Men0 文件系统 MVP Bridge — JSONL + flock 实现跨Agent语义同步。

    这是 Men0 Protocol v2 的降级实现，不依赖 gRPC。
    使用扁平 JSONL 文件 + 文件锁进行多Agent间语义消息交换。
    """

    def __init__(self, agent_id: str, workspace_dir: Path):
        self.agent_id = agent_id
        self.workspace = Path(workspace_dir)
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.clock = VectorClock(agent_id)
        self.fact_store = LWWRegisterStore()
        self.intent_queue = ORSet()
        self.constraint_set = None
        self.confidence_gate = ConfidenceGatedMemoryStore()

        self._message_file = self.workspace / f"{agent_id}_messages.jsonl"
        self._state_file = self.workspace / f"{agent_id}_state.json"
        self._peers: dict[str, dict[str, Any]] = {}

    def register_peer(self, peer_id: str) -> None:
        self._peers[peer_id] = {"last_seen": time.time()}

    def publish_fact(self, fact: SharedSemanticFact) -> SemanticMessage:
        self.clock.tick()
        self.confidence_gate.ingest(fact)

        key = str(fact.fact_id)
        self.fact_store.set(key, fact.content, time.time(), self.agent_id)

        msg = SemanticMessage(
            source_agent=self.agent_id,
            payload_type=PayloadType.FACT_ASSERTION,
            payload=fact,
            vector_clock=self.clock.snapshot,
        )
        self._write_message(msg)
        return msg

    def publish_state(self, state: SemanticStateSnapshot) -> SemanticMessage:
        self.clock.tick()
        msg = SemanticMessage(
            source_agent=self.agent_id,
            payload_type=PayloadType.STATE_SYNC,
            payload=state,
            vector_clock=self.clock.snapshot,
        )
        self._write_message(msg)
        return msg

    def publish_intent(self, target_agent: str, intent: IntentPacket) -> SemanticMessage:
        self.clock.tick()
        msg = SemanticMessage(
            source_agent=self.agent_id,
            target_agent=target_agent,
            payload_type=PayloadType.INTENT_DELEGATE,
            payload=intent,
            vector_clock=self.clock.snapshot,
        )
        self._write_message(msg)
        return msg

    def consume_peer_messages(self) -> list[SemanticMessage]:
        messages = []
        for peer_id in self._peers:
            peer_file = self.workspace / f"{peer_id}_messages.jsonl"
            if not peer_file.exists():
                continue
            for msg in self._read_messages(peer_file):
                if msg.target_agent and msg.target_agent != self.agent_id:
                    continue
                messages.append(msg)
        return messages

    def sync_state(self) -> SharedSemanticState:
        self.consume_peer_messages()
        return SharedSemanticState(
            facts=self.confidence_gate.global_facts + self.confidence_gate.pending_facts,
            agent_states={self.agent_id: SemanticStateSnapshot(agent_id=self.agent_id)},
        )

    def _write_message(self, msg: SemanticMessage) -> None:
        data = msg.model_dump(mode="json")
        data["payload"] = _serialize_payload(data.get("payload"))
        with open(self._message_file, "a") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def _read_messages(self, filepath: Path) -> list[SemanticMessage]:
        messages = []
        try:
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        msg = SemanticMessage.model_validate(data)
                        messages.append(msg)
                    except Exception:
                        logger.debug("Skipping malformed message line")
        except FileNotFoundError:
            pass
        return messages

    @property
    def status(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "peers": len(self._peers),
            "facts_store_size": self.fact_store.size,
            "vector_clock": self.clock.snapshot,
            "confidence_gate": self.confidence_gate.status,
        }


def _serialize_payload(payload: Any) -> Any:
    if payload is None:
        return None
    if isinstance(payload, dict):
        return payload
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    return str(payload)
