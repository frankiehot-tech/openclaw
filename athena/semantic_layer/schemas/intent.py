import hashlib
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .proto_mixin import ProtoConvertible


class CognitiveMode(StrEnum):
    INSTANT = "instant"
    THINKING = "thinking"
    AGENT = "agent"
    SWARM = "swarm"
    CARBON_SILICON = "carbon-silicon"


class SecurityLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionVerb(StrEnum):
    ANALYZE = "analyze"
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    SEARCH = "search"
    EXPLAIN = "explain"
    CONFIGURE = "configure"
    DEPLOY = "deploy"
    AUDIT = "audit"
    DEBUG = "debug"
    TEST = "test"
    DOCUMENT = "document"
    REVIEW = "review"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    CONVERT = "convert"


class SemanticObject(BaseModel):
    object_type: str = Field(default="", description="Entity type: file, function, class, database, config, etc.")
    object_name: str = ""
    object_path: str | None = None
    object_metadata: dict[str, str] = Field(default_factory=dict)


class ContextFrame(BaseModel):
    domain: str = Field(default="general", description="Knowledge domain: coding, security, data, infra, etc.")
    tags: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    conversation_round: int = 0


class SemanticFrame(BaseModel):
    action_verb: ActionVerb = ActionVerb.ANALYZE
    action_object: SemanticObject = Field(default_factory=SemanticObject)
    action_context: ContextFrame = Field(default_factory=ContextFrame)
    expected_modalities: list[Literal["text", "code", "image", "video", "audio"]] = ["text"]
    intent_fingerprint: str = ""


class AmbiguityVector(BaseModel):
    scope_ambiguity: float = Field(default=0.0, ge=0.0, le=1.0, description="Unclear reference scope")
    target_ambiguity: float = Field(default=0.0, ge=0.0, le=1.0, description="Unclear operation target")
    modality_ambiguity: float = Field(default=0.0, ge=0.0, le=1.0, description="Unclear expected modality")
    authority_ambiguity: float = Field(default=0.0, ge=0.0, le=1.0, description="Unclear permission scope")

    def needs_clarification(self, threshold: float = 0.7) -> bool:
        return any(
            v > threshold
            for v in [self.scope_ambiguity, self.target_ambiguity, self.modality_ambiguity]
        )

    @property
    def primary_dimension(self) -> str | None:
        values = {
            "scope": self.scope_ambiguity,
            "target": self.target_ambiguity,
            "modality": self.modality_ambiguity,
        }
        if max(values.values()) < 0.7:
            return None
        return max(values, key=lambda k: values[k])


class TokenBudget(BaseModel):
    total: int = Field(default=50000, ge=0)
    consumed: int = Field(default=0, ge=0)
    reserved: int = Field(default=5000, ge=0)

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.consumed - self.reserved)


class IntentPacket(BaseModel, ProtoConvertible):
    intent_id: UUID = Field(default_factory=uuid4)
    raw_input: str
    timestamp: float = Field(default_factory=lambda: __import__("time").time())

    mode_recommendation: CognitiveMode = CognitiveMode.INSTANT
    urgency_level: float = Field(default=0.5, ge=0.0, le=1.0)

    semantic_frame: SemanticFrame = Field(default_factory=SemanticFrame)
    ambiguity_vector: AmbiguityVector = Field(default_factory=AmbiguityVector)

    required_clearance: SecurityLevel = SecurityLevel.LOW
    target_agent_pool: list[str] = Field(default_factory=list)
    execution_budget: TokenBudget = Field(default_factory=TokenBudget)

    context_tags: list[str] = Field(default_factory=list)

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        data["intent_fingerprint"] = self.compute_fingerprint()
        return data

    def compute_fingerprint(self) -> str:
        content = (
            f"{self.semantic_frame.action_verb.value}:"
            f"{self.semantic_frame.action_object.object_type}:"
            f"{self.semantic_frame.action_context.domain}"
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]
