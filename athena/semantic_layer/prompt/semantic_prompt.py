import hashlib
from dataclasses import dataclass, field
from typing import Any

from ..schemas.intent import AmbiguityVector, IntentPacket
from ..schemas.state import SemanticStateSnapshot
from .prompt_segments import PromptSegmentType


@dataclass
class PromptSegmentData:
    seg_type: PromptSegmentType
    data: Any
    token_budget_override: int | None = None


@dataclass
class ClarificationQuestion:
    dimension: str
    template: str
    options: list[str] = field(default_factory=list)


@dataclass
class AmbiguityContext:
    overall_clarity: float
    questions: list[ClarificationQuestion]
    suggested_mode: str


class AmbiguityInjector:
    _TARGET_TEMPLATES = [
        "'{}' 具体指代以下哪个？",
        "你提到的目标存在歧义，请确认：",
        "哪个对象需要操作？",
    ]

    _SCOPE_TEMPLATES = [
        "你希望操作的范围是？",
        "请明确影响区域：",
        "此操作应在哪个范围内执行？",
    ]

    _MODALITY_TEMPLATES = [
        "你期望的输出格式是？",
        "请指定需要的产出类型：",
        "输出应该是什么样的？",
    ]

    _AUTHORITY_TEMPLATES = [
        "此操作需要权限确认。是否授权？",
        "该操作涉及敏感区域，请确认权限级别：",
        "需要你的授权才能继续，是否允许？",
    ]

    def inject(self, vector: AmbiguityVector, intent: IntentPacket | None = None) -> AmbiguityContext:
        clarifications = []
        seed = self._seed_from_intent(intent)

        if vector.target_ambiguity > 0.7:
            clarifications.append(
                ClarificationQuestion(
                    dimension="target",
                    template=self._pick_template(seed, self._TARGET_TEMPLATES, 0),
                    options=self._resolve_target_options(vector, intent),
                )
            )

        if vector.scope_ambiguity > 0.7:
            clarifications.append(
                ClarificationQuestion(
                    dimension="scope",
                    template=self._pick_template(seed, self._SCOPE_TEMPLATES, 1),
                    options=["当前文件", "整个项目", "指定目录", "不确定"],
                )
            )

        if vector.modality_ambiguity > 0.7:
            clarifications.append(
                ClarificationQuestion(
                    dimension="modality",
                    template=self._pick_template(seed, self._MODALITY_TEMPLATES, 2),
                    options=["纯文本说明", "可执行代码", "图表/可视化", "不确定"],
                )
            )

        if vector.authority_ambiguity > 0.7:
            clarifications.append(
                ClarificationQuestion(
                    dimension="authority",
                    template=self._pick_template(seed, self._AUTHORITY_TEMPLATES, 3),
                    options=["确认授权", "预览效果后决定", "取消"],
                )
            )

        overall = 1.0 - max(
            vector.scope_ambiguity,
            vector.target_ambiguity,
            vector.modality_ambiguity,
            vector.authority_ambiguity,
        )

        high_dims = sum(
            1 for v in [vector.scope_ambiguity, vector.target_ambiguity,
                        vector.modality_ambiguity, vector.authority_ambiguity]
            if v > 0.7
        )

        suggested = "carbon-silicon" if high_dims >= 2 else "thinking"

        return AmbiguityContext(
            overall_clarity=overall,
            questions=clarifications,
            suggested_mode=suggested,
        )

    @staticmethod
    def _pick_template(seed: int, templates: list[str], dim_offset: int) -> str:
        idx = (seed + dim_offset) % len(templates)
        return templates[idx]

    @staticmethod
    def _seed_from_intent(intent: IntentPacket | None) -> int:
        if intent is None:
            return 0
        return int(hashlib.sha256(intent.raw_input.encode()).hexdigest()[:8], 16)

    def _resolve_target_options(
        self,
        vector: AmbiguityVector,
        intent: IntentPacket | None = None,
    ) -> list[str]:
        if intent and intent.semantic_frame.action_context.related_entities:
            return intent.semantic_frame.action_context.related_entities[:5]
        return ["当前上下文", "请指定具体目标"]

    @staticmethod
    def needs_carbon_silicon(vector: AmbiguityVector, threshold: float = 0.7) -> bool:
        return sum(
            1 for v in [vector.scope_ambiguity, vector.target_ambiguity,
                        vector.modality_ambiguity, vector.authority_ambiguity]
            if v > threshold
        ) >= 2


@dataclass
class SemanticPromptGraph:
    segments: dict[PromptSegmentType, Any] = field(default_factory=dict)
    schema_version: str = "men0.semantic.v1"
    created_at: float = 0.0

    def set_segment(self, seg_type: PromptSegmentType, data: Any) -> None:
        self.segments[seg_type] = data

    def get_segment(self, seg_type: PromptSegmentType) -> Any | None:
        return self.segments.get(seg_type)

    def set_role(self, role_text: str) -> None:
        self.set_segment(PromptSegmentType.ROLE_DEFINITION, role_text)

    def set_intent(self, intent: IntentPacket) -> None:
        self.set_segment(PromptSegmentType.USER_INTENT, intent.model_dump())

    def set_memory(self, snapshot: SemanticStateSnapshot) -> None:
        self.set_segment(PromptSegmentType.MEMORY_SNAPSHOT, snapshot.model_dump())

    def set_mode(self, mode: str) -> None:
        self.set_segment(PromptSegmentType.MODE_DECLARATION, {"current_mode": mode})

    def set_task_graph(self, dag: Any) -> None:
        self.set_segment(PromptSegmentType.TASK_GRAPH, dag)

    def set_tool_registry(self, tools: list) -> None:
        self.set_segment(PromptSegmentType.TOOL_REGISTRY, {"tools": tools})

    def set_ambiguity(self, vector: AmbiguityVector, intent: IntentPacket | None = None) -> None:
        injector = AmbiguityInjector()
        ctx = injector.inject(vector, intent)
        self.set_segment(PromptSegmentType.AMBIGUITY_CONTEXT, {
            "overall_clarity": ctx.overall_clarity,
            "questions": [
                {"dimension": q.dimension, "template": q.template, "options": q.options}
                for q in ctx.questions
            ],
            "suggested_mode": ctx.suggested_mode,
        })
