from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .proto_mixin import ProtoConvertible


class CognitiveState(StrEnum):
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    BLOCKED = "blocked"
    AMBIGUOUS = "ambiguous"
    AWAITING_HUMAN = "awaiting_human"


class SemanticChunk(BaseModel):
    chunk_id: UUID = Field(default_factory=uuid4)
    content: str
    chunk_type: Literal["task", "fact", "constraint", "decision", "observation"]
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class ContextVector(BaseModel):
    dimensions: int = 1536
    vector: list[float] = Field(default_factory=list)
    compressed_size: int = 0


class FactTriple(BaseModel):
    subject: str
    predicate: str
    obj: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_agent: str | None = None


class DecisionPoint(BaseModel):
    decision_id: UUID = Field(default_factory=uuid4)
    question: str
    options: list[str] = Field(default_factory=list)
    recommended_option: str | None = None
    deadline: datetime | None = None
    resolved: bool = False
    resolution: str | None = None
    resolver: str | None = None  # "agent" or "human:<user_id>"


class SemanticStateSnapshot(BaseModel, ProtoConvertible):
    snapshot_id: UUID = Field(default_factory=uuid4)
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

    cognitive_state: str = CognitiveState.PLANNING

    working_memory: list[SemanticChunk] = Field(default_factory=list)
    working_memory_capacity: int = 7

    context_vector: ContextVector | None = None

    human_summary: str = ""

    queryable_facts: list[FactTriple] = Field(default_factory=list)

    pending_decisions: list[DecisionPoint] = Field(default_factory=list)

    token_budget_remaining: int = 50000

    mode: str = "instant"


class StateDiff(BaseModel):
    cognitive_shift: bool = False
    memory_drift: float = Field(default=0.0, description="Working memory drift score")
    fact_consistency: float = Field(default=1.0, description="Fact consistency score")
    new_facts_count: int = 0
    stale_facts_count: int = 0
    pending_decisions_added: int = 0
    pending_decisions_resolved: int = 0
    token_budget_delta: int = 0
    summary: str = ""
