from datetime import datetime
from enum import IntEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryLayerLevel(IntEnum):
    L1_PERSISTENT = 1     # athena_memory.md
    L2_ACTIVE_RETRIEVAL = 2  # Semantic Grep
    L3_SEMANTIC_DAEMON = 3   # Background Index
    L4_PROCEDURAL = 4        # Skill Patterns
    L5_SHARED = 5            # Men0 Cross-Agent


class PersistentMemoryEntry(BaseModel):
    entry_id: UUID = Field(default_factory=uuid4)
    section: str  # "project_context", "recent_decisions", "pending_clarifications"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    tags: list[str] = Field(default_factory=list)


class ProgramMemoryPattern(BaseModel):
    pattern_id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    skill_name: str
    trigger_conditions: list[str]
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_token_cost: int = 0
    evolution_history: list[dict] = Field(default_factory=list)


class SharedSemanticFact(BaseModel):
    fact_id: UUID = Field(default_factory=uuid4)
    content: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_agents: list[str] = Field(default_factory=list)
    verification_count: int = 0
    contradiction_count: int = 0
    is_global: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    last_verified: datetime | None = None
    ngram_signature: str = ""


class MemoryQueryResult(BaseModel):
    entries: list[PersistentMemoryEntry] = Field(default_factory=list)
    semantic_scores: list[float] = Field(default_factory=list)
    relevance_summary: str = ""
    total_found: int = 0
    query_time_ms: float = 0.0
