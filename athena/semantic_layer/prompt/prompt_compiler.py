from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from ..infra.tokenizer import Tokenizer
from .prompt_segments import PromptSegmentType, SegmentRegistry

_tokenizer = Tokenizer()


@dataclass
class CompiledSegment:
    seg_type: PromptSegmentType
    text: str
    token_count: int
    hash: str
    cache_anchor: int = 0


@dataclass
class CompiledPrompt:
    text: str
    segment_boundaries: dict[PromptSegmentType, tuple[int, int]]
    cache_anchors: list[int]
    fingerprint: str
    total_tokens: int = 0
    segments: list[CompiledSegment] = field(default_factory=list)


@dataclass
class PromptDiff:
    changed_segments: list[PromptSegmentType]
    added_segments: list[PromptSegmentType]
    removed_segments: list[PromptSegmentType]
    token_delta: int
    cache_invalidated: bool
    summary: str


class SemanticPromptCompiler:
    def __init__(self, segment_registry: SegmentRegistry):
        self.registry = segment_registry
        self.compiled_segments: dict[PromptSegmentType, CompiledSegment] = {}
        self.segment_hashes: dict[PromptSegmentType, str] = {}

    def compile(self, semantic_graph: Any) -> CompiledPrompt:
        segments: list[CompiledSegment] = []
        all_text_parts: list[str] = []
        boundaries: dict[PromptSegmentType, tuple[int, int]] = {}
        cache_anchors: list[int] = []
        current_pos = 0
        total_tokens = 0

        compile_order = self._compile_order()

        for seg_type in compile_order:
            seg_data = semantic_graph.segments.get(seg_type)
            if seg_data is None:
                continue

            compile_fn = self.registry.get_compiler(seg_type)
            if compile_fn is None:
                continue

            seg_hash = self._compute_hash(seg_data)
            if seg_hash == self.segment_hashes.get(seg_type):
                compiled = self.compiled_segments[seg_type]
            else:
                max_tokens = self.registry.get_token_limit(seg_type)
                compiled_text = compile_fn(seg_data, max_tokens)
                compiled = CompiledSegment(
                    seg_type=seg_type,
                    text=compiled_text,
                    token_count=self._estimate_tokens(compiled_text),
                    hash=seg_hash,
                )
                self.compiled_segments[seg_type] = compiled
                self.segment_hashes[seg_type] = seg_hash

            marker = f"\n<!-- {seg_type.value}_start -->\n"
            end_marker = f"\n<!-- {seg_type.value}_end -->\n"

            start = current_pos
            all_text_parts.append(marker)
            current_pos += len(marker)

            cache_anchor = 0
            if seg_type.is_cacheable:
                cache_anchor = current_pos

            all_text_parts.append(compiled.text)
            current_pos += len(compiled.text)

            all_text_parts.append(end_marker)
            current_pos += len(end_marker)

            boundaries[seg_type] = (start, current_pos)
            if cache_anchor > 0:
                cache_anchors.append(cache_anchor)
            total_tokens += compiled.token_count
            segments.append(compiled)

        full_text = "".join(all_text_parts)

        return CompiledPrompt(
            text=full_text,
            segment_boundaries=boundaries,
            cache_anchors=cache_anchors,
            fingerprint=self._compute_overall_fingerprint(segments),
            total_tokens=total_tokens,
            segments=segments,
        )

    def inject(
        self,
        seg_type: PromptSegmentType,
        semantic_object: Any,
    ) -> None:
        """子系统注入语义对象到对应段。需要配合 compile() 使用。"""
        self.segment_hashes.pop(seg_type, None)

    def diff(
        self,
        old_prompt: CompiledPrompt,
        new_prompt: CompiledPrompt,
    ) -> PromptDiff:
        old_seg_types = set(old_prompt.segment_boundaries.keys())
        new_seg_types = set(new_prompt.segment_boundaries.keys())

        changed = []
        for seg_type in old_seg_types & new_seg_types:
            old_hash = next(
                (s.hash for s in old_prompt.segments if s.seg_type == seg_type),
                "",
            )
            new_hash = next(
                (s.hash for s in new_prompt.segments if s.seg_type == seg_type),
                "",
            )
            if old_hash != new_hash:
                changed.append(seg_type)

        added = list(new_seg_types - old_seg_types)
        removed = list(old_seg_types - new_seg_types)

        token_delta = new_prompt.total_tokens - old_prompt.total_tokens

        cache_invalidated = any(
            t in changed or t in added or t in removed
            for t in PromptSegmentType
            if t.is_cacheable
        )

        summary_parts = []
        if changed:
            summary_parts.append(f"{len(changed)} segments changed")
        if added:
            summary_parts.append(f"{len(added)} segments added")
        if removed:
            summary_parts.append(f"{len(removed)} segments removed")

        return PromptDiff(
            changed_segments=changed,
            added_segments=added,
            removed_segments=removed,
            token_delta=token_delta,
            cache_invalidated=cache_invalidated,
            summary="; ".join(summary_parts) if summary_parts else "no changes",
        )

    def _compile_order(self) -> list[PromptSegmentType]:
        return [
            PromptSegmentType.META,
            PromptSegmentType.ROLE_DEFINITION,
            PromptSegmentType.CAPABILITY_MANIFEST,
            PromptSegmentType.CONSTRAINT_SET,
            PromptSegmentType.TOOL_REGISTRY,
            PromptSegmentType.TASK_GRAPH,
            PromptSegmentType.MEMORY_SNAPSHOT,
            PromptSegmentType.AMBIGUITY_CONTEXT,
            PromptSegmentType.DECISION_QUEUE,
            PromptSegmentType.USER_INTENT,
            PromptSegmentType.MODE_DECLARATION,
            PromptSegmentType.ROUTING_SIGNALS,
        ]

    def _compute_hash(self, seg_data: Any) -> str:
        import hashlib
        import json
        if isinstance(seg_data, BaseModel):
            content = seg_data.model_dump_json()
        elif isinstance(seg_data, dict):
            content = json.dumps(seg_data, sort_keys=True, default=str)
        else:
            content = str(seg_data)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _estimate_tokens(self, text: str) -> int:
        return _tokenizer.count(text)

    def _compute_overall_fingerprint(self, segments: list[CompiledSegment]) -> str:
        import hashlib
        combined = "|".join(
            f"{s.seg_type.value}:{s.hash}" for s in sorted(segments, key=lambda s: s.seg_type)
        )
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
