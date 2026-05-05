from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class FailureMode(BaseModel):
    mode_id: UUID = Field(default_factory=uuid4)
    error_pattern: str
    recovery_strategy: str
    auto_fixable: bool = False
    frequency: int = 0
    last_seen: str | None = None


class ToolSemanticEntry(BaseModel):
    tool_id: str
    mcp_schema: dict = Field(default_factory=dict)

    capability_embedding: list[float] = Field(default_factory=list)
    nl_descriptions: list[str] = Field(default_factory=list)
    usage_patterns: list[str] = Field(default_factory=list)
    failure_semantics: list[FailureMode] = Field(default_factory=list)

    avg_latency_ms: float = 0.0
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    token_cost: int = 0

    server_id: str | None = None
    category: str = "general"


class ToolSemanticSearchResult(BaseModel):
    tool: ToolSemanticEntry
    similarity_score: float
    match_reason: str


class ToolExecutionPlan(BaseModel):
    plan_id: UUID = Field(default_factory=uuid4)
    execution_code: str
    tools: list[ToolSemanticEntry] = Field(default_factory=list)
    estimated_tokens: int = 0
    fallback_plan: str | None = None
