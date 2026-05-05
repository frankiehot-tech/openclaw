from dataclasses import dataclass, field
from typing import Any

from ..schemas.intent import AmbiguityVector, CognitiveMode
from ..schemas.state import SemanticStateSnapshot


@dataclass
class ModeDecision:
    target_mode: CognitiveMode
    reason: str
    local_only: bool = True
    max_agents: int = 1
    pause_for_human: bool = False
    estimated_latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ModeSwitchingEngine:
    CARBON_SILICON_AMBIGUITY_THRESHOLD = 0.7
    CARBON_SILICON_MIN_DIMS = 2

    def __init__(self, default_mode: CognitiveMode = CognitiveMode.INSTANT):
        self.current_mode = default_mode
        self.mode_history: list[ModeDecision] = []

    def evaluate_transition(
        self,
        complexity_score: float,
        tool_demand: int,
        parallelism_opportunity: float,
        human_attention_required: bool = False,
        ambiguity_vector: AmbiguityVector | None = None,
        current_state: SemanticStateSnapshot | None = None,
    ) -> ModeDecision:
        if ambiguity_vector and self._should_enter_carbon_silicon(ambiguity_vector):
            return ModeDecision(
                target_mode=CognitiveMode.CARBON_SILICON,
                reason=f"High ambiguity in {self._count_high_dims(ambiguity_vector)} dimensions: scope={ambiguity_vector.scope_ambiguity:.2f}, target={ambiguity_vector.target_ambiguity:.2f}",
                pause_for_human=True,
                estimated_latency_ms=float("inf"),
                metadata={"ambiguity_vector": ambiguity_vector.model_dump()},
            )

        if human_attention_required or (
            current_state and current_state.cognitive_state == "awaiting_human"
        ):
            return ModeDecision(
                target_mode=CognitiveMode.CARBON_SILICON,
                reason="Human attention required for pending decisions",
                pause_for_human=True,
                estimated_latency_ms=float("inf"),
            )

        if complexity_score > 0.7 and parallelism_opportunity > 0.6:
            return ModeDecision(
                target_mode=CognitiveMode.SWARM,
                reason=f"High complexity ({complexity_score:.2f}) + parallelizable ({parallelism_opportunity:.2f})",
                local_only=False,
                max_agents=min(100, max(1, int(parallelism_opportunity * 100))),
                estimated_latency_ms=1500.0,
            )

        if tool_demand > 2 and complexity_score > 0.4:
            return ModeDecision(
                target_mode=CognitiveMode.AGENT,
                reason=f"Tool-heavy ({tool_demand} tools) + moderate complexity ({complexity_score:.2f})",
                local_only=False,
                estimated_latency_ms=800.0,
            )

        if complexity_score > 0.4 and tool_demand == 0:
            return ModeDecision(
                target_mode=CognitiveMode.THINKING,
                reason=f"Reasoning required (complexity={complexity_score:.2f}) without tool usage",
                local_only=False,
                estimated_latency_ms=500.0,
            )

        return ModeDecision(
            target_mode=CognitiveMode.INSTANT,
            reason="Simple query, instant response sufficient",
            local_only=True,
            estimated_latency_ms=100.0,
        )

    def _should_enter_carbon_silicon(self, vector: AmbiguityVector) -> bool:
        return self._count_high_dims(vector) >= self.CARBON_SILICON_MIN_DIMS

    @staticmethod
    def _count_high_dims(vector: AmbiguityVector) -> int:
        return sum(
            1 for v in [vector.scope_ambiguity, vector.target_ambiguity,
                        vector.modality_ambiguity, vector.authority_ambiguity]
            if v > ModeSwitchingEngine.CARBON_SILICON_AMBIGUITY_THRESHOLD
        )

    def assess_complexity(self, intent_urgency: float, ambiguity_max: float, context_tags: list[str]) -> float:
        base = intent_urgency * 0.4 + ambiguity_max * 0.3
        complex_tags = {"security", "database", "deploy", "architecture", "performance"}
        tag_bonus = 0.1 * len(set(context_tags) & complex_tags)
        return min(1.0, base + tag_bonus)

    def assess_tool_requirements(self, action_verb: str, object_type: str) -> int:
        tool_heavy_actions = {"create", "modify", "delete", "deploy", "audit", "test", "debug"}
        tool_heavy_objects = {"file", "database", "config", "deployment", "code"}
        count = 0
        if action_verb in tool_heavy_actions:
            count += 2
        if object_type in tool_heavy_objects:
            count += 1
        return count

    def assess_parallelism(self, context_tags: list[str]) -> float:
        parallel_tags = {"batch", "search", "analysis", "research", "documentation", "testing"}
        if not context_tags:
            return 0.0
        return len(set(context_tags) & parallel_tags) / max(len(context_tags), 1)

    def switch(self, decision: ModeDecision) -> CognitiveMode:
        self.mode_history.append(decision)
        self.current_mode = decision.target_mode
        return self.current_mode
