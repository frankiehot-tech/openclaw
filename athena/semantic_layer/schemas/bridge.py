from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .intent import IntentPacket
from .memory import SharedSemanticFact
from .proto_mixin import ProtoConvertible
from .state import SemanticStateSnapshot


class PayloadType(StrEnum):
    INTENT_DELEGATE = "intent_delegate"
    STATE_SYNC = "state_sync"
    FACT_ASSERTION = "fact_assertion"
    CONSTRAINT_UPDATE = "constraint_update"
    CLARIFICATION_REQUEST = "clarification_request"
    MEMORY_DIFF = "memory_diff"


class Constraint(BaseModel):
    constraint_id: UUID = Field(default_factory=uuid4)
    rule: str
    scope: Literal["global", "agent", "task"] = "global"
    priority: int = 5
    active: bool = True


class ClarificationRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    source_agent: str
    question: str
    context: str
    options: list[str] = Field(default_factory=list)
    deadline: datetime | None = None


class SemanticMessage(BaseModel, ProtoConvertible):
    message_id: UUID = Field(default_factory=uuid4)
    source_agent: str
    target_agent: str = ""  # 空表示广播

    payload_type: str = PayloadType.STATE_SYNC

    payload: IntentPacket | SemanticStateSnapshot | SharedSemanticFact | Constraint | ClarificationRequest | dict | None = None

    vector_clock: dict[str, int] = Field(default_factory=dict)
    schema_version: str = "men0.semantic.v1"
    timestamp: datetime = Field(default_factory=datetime.now)


class Men0SharedState(BaseModel):
    context_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_vector_clock: dict[str, int] = Field(default_factory=dict)

    shared_intents: list[IntentPacket] = Field(default_factory=list)
    shared_facts: list[SharedSemanticFact] = Field(default_factory=list)
    shared_constraints: list[Constraint] = Field(default_factory=list)


class SharedSemanticState(BaseModel):
    state_id: UUID = Field(default_factory=uuid4)
    facts: list[SharedSemanticFact] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    agent_states: dict[str, SemanticStateSnapshot] = Field(default_factory=dict)
    version: int = 1
