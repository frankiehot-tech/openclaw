from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class PromptSegmentType(StrEnum):
    ROLE_DEFINITION = "role"
    CAPABILITY_MANIFEST = "capability"
    CONSTRAINT_SET = "constraint"
    TOOL_REGISTRY = "tools"

    TASK_GRAPH = "task"
    MEMORY_SNAPSHOT = "memory"
    AMBIGUITY_CONTEXT = "ambiguity"
    DECISION_QUEUE = "decisions"

    USER_INTENT = "intent"
    MODE_DECLARATION = "mode"
    ROUTING_SIGNALS = "routing"

    META = "meta"

    @property
    def is_immutable(self) -> bool:
        return self in (
            PromptSegmentType.ROLE_DEFINITION,
            PromptSegmentType.CAPABILITY_MANIFEST,
            PromptSegmentType.CONSTRAINT_SET,
        )

    @property
    def is_session_scoped(self) -> bool:
        return self in (
            PromptSegmentType.TASK_GRAPH,
            PromptSegmentType.MEMORY_SNAPSHOT,
            PromptSegmentType.AMBIGUITY_CONTEXT,
            PromptSegmentType.DECISION_QUEUE,
        )

    @property
    def is_request_scoped(self) -> bool:
        return self in (
            PromptSegmentType.USER_INTENT,
            PromptSegmentType.MODE_DECLARATION,
            PromptSegmentType.ROUTING_SIGNALS,
        )

    @property
    def is_cacheable(self) -> bool:
        return self.is_immutable

    @property
    def default_token_budget(self) -> int:
        budgets = {
            PromptSegmentType.ROLE_DEFINITION: 2000,
            PromptSegmentType.CAPABILITY_MANIFEST: 3000,
            PromptSegmentType.CONSTRAINT_SET: 1500,
            PromptSegmentType.TOOL_REGISTRY: 8000,
            PromptSegmentType.TASK_GRAPH: 4000,
            PromptSegmentType.MEMORY_SNAPSHOT: 5000,
            PromptSegmentType.AMBIGUITY_CONTEXT: 1000,
            PromptSegmentType.DECISION_QUEUE: 2000,
            PromptSegmentType.USER_INTENT: 2000,
            PromptSegmentType.MODE_DECLARATION: 500,
            PromptSegmentType.ROUTING_SIGNALS: 500,
            PromptSegmentType.META: 300,
        }
        return budgets.get(self, 1000)

    @property
    def display_name(self) -> str:
        names = {
            PromptSegmentType.ROLE_DEFINITION: "Role Definition",
            PromptSegmentType.CAPABILITY_MANIFEST: "Capabilities",
            PromptSegmentType.CONSTRAINT_SET: "Constraints",
            PromptSegmentType.TOOL_REGISTRY: "Available Tools",
            PromptSegmentType.TASK_GRAPH: "Task Graph",
            PromptSegmentType.MEMORY_SNAPSHOT: "Memory",
            PromptSegmentType.AMBIGUITY_CONTEXT: "Ambiguity Context",
            PromptSegmentType.DECISION_QUEUE: "Pending Decisions",
            PromptSegmentType.USER_INTENT: "User Intent",
            PromptSegmentType.MODE_DECLARATION: "Current Mode",
            PromptSegmentType.ROUTING_SIGNALS: "Routing Signals",
            PromptSegmentType.META: "Metadata",
        }
        return names.get(self, self.value)


@dataclass
class SegmentRegistry:
    segments: dict[PromptSegmentType, dict[str, Any]] = field(default_factory=dict)

    def register(
        self,
        seg_type: PromptSegmentType,
        compile_fn: Callable[..., Any],
        schema: type[BaseModel] | None = None,
        token_limit_override: int | None = None,
    ) -> None:
        self.segments[seg_type] = {
            "compile_fn": compile_fn,
            "schema": schema,
            "token_limit": token_limit_override or seg_type.default_token_budget,
        }

    def get_compiler(self, seg_type: PromptSegmentType) -> Callable[..., Any] | None:
        entry = self.segments.get(seg_type)
        return entry["compile_fn"] if entry else None

    def get_token_limit(self, seg_type: PromptSegmentType) -> int:
        entry = self.segments.get(seg_type)
        return entry["token_limit"] if entry else seg_type.default_token_budget

    @property
    def registered_types(self) -> list[PromptSegmentType]:
        return list(self.segments.keys())


# ── MVSL 编译函数 ─────────────────────────────────────────────────


def compile_role(role_text: str, max_tokens: int = 2000) -> str:
    lines = [
        "## Role",
        role_text.strip() if role_text else "You are Athena, an intelligent assistant.",
    ]
    text = "\n".join(lines)
    if len(text) > max_tokens * 2:
        text = text[:max_tokens * 2] + "\n... (truncated)"
    return text


def compile_memory(memory_data: dict, max_tokens: int = 5000) -> str:
    facts = memory_data.get("facts", memory_data.get("queryable_facts", []))
    summary = memory_data.get("human_summary", memory_data.get("summary", ""))

    parts = ["## Memory"]
    if summary:
        parts.append(f"Summary: {summary}")
    if facts:
        parts.append("Facts:")
        for f in facts[:20]:
            if isinstance(f, dict):
                parts.append(f"  - {f.get('subject', '?')} {f.get('predicate', 'is')} {f.get('obj', '?')}")
            else:
                parts.append(f"  - {str(f)}")
    text = "\n".join(parts)
    if len(text) > max_tokens * 2:
        text = text[:max_tokens * 2] + "\n... (truncated)"
    return text


def compile_routing(routing_data: dict, max_tokens: int = 500) -> str:
    parts = ["## Routing"]
    for key, val in routing_data.items():
        parts.append(f"{key}: {val}")
    text = "\n".join(parts)
    if len(text) > max_tokens * 2:
        text = text[:max_tokens * 2] + "\n... (truncated)"
    return text


def compile_meta(meta_data: dict, max_tokens: int = 300) -> str:
    version = meta_data.get("schema_version", "men0.semantic.v1")
    flags = meta_data.get("feature_flags", {})
    parts = ["## Meta", f"schema: {version}"]
    for flag, enabled in flags.items():
        parts.append(f"flag/{flag}: {1 if enabled else 0}")
    return "\n".join(parts)


# ── 全量段编译函数 ────────────────────────────────────────────────


def compile_capability(cap_data: dict, max_tokens: int = 3000) -> str:
    caps = cap_data.get("capabilities", cap_data.get("items", []))
    if not caps:
        return "## Capabilities\n(none declared)"
    parts = ["## Capabilities"]
    for c in caps[:30]:
        parts.append(f"- {c}")
    text = "\n".join(parts)
    if len(text) > max_tokens * 2:
        text = text[:max_tokens * 2] + "\n... (truncated)"
    return text


def compile_constraint(cstr_data: dict, max_tokens: int = 1500) -> str:
    rules = cstr_data.get("constraints", cstr_data.get("rules", []))
    if not rules:
        return "## Constraints\n(none)"
    parts = ["## Constraints"]
    for r in rules[:20]:
        parts.append(f"- {r}")
    text = "\n".join(parts)
    if len(text) > max_tokens * 2:
        text = text[:max_tokens * 2] + "\n... (truncated)"
    return text


def compile_tools(tool_data: dict, max_tokens: int = 8000) -> str:
    tools = tool_data.get("tools", [])
    if not tools:
        return "## Available Tools\n(none registered)"
    parts = ["## Available Tools"]
    for t in tools[:40]:
        tid = t.get("id", t.get("tool_id", str(t)))
        cat = t.get("category", "")
        desc = t.get("description", "")
        if cat:
            parts.append(f"- {tid}  [{cat}]")
        else:
            parts.append(f"- {tid}")
        if desc:
            parts.append(f"    {desc}")
    text = "\n".join(parts)
    if len(text) > max_tokens * 2:
        text = text[:max_tokens * 2] + "\n... (truncated)"
    return text


def compile_task(task_data: dict, max_tokens: int = 4000) -> str:
    nodes = task_data.get("nodes", task_data.get("tasks", []))
    edges = task_data.get("edges", [])
    if not nodes:
        return "## Task Graph\n(no active tasks)"
    parts = ["## Task Graph"]
    for n in nodes[:25]:
        tid = n.get("id", n.get("task_id", str(n)))
        status = n.get("status", "pending")
        dep = n.get("depends_on", n.get("dependencies", []))
        dep_str = f"  → depends: {', '.join(dep)}" if dep else ""
        parts.append(f"- {tid} [{status}]{dep_str}")
    if edges:
        parts.append("Edges:")
        for e in edges[:15]:
            parts.append(f"  {e.get('from', '?')} → {e.get('to', '?')}")
    text = "\n".join(parts)
    if len(text) > max_tokens * 2:
        text = text[:max_tokens * 2] + "\n... (truncated)"
    return text


def compile_ambiguity(ambig_data: dict, max_tokens: int = 1000) -> str:
    clarity = ambig_data.get("overall_clarity", 1.0)
    questions = ambig_data.get("questions", [])
    mode = ambig_data.get("suggested_mode", "thinking")

    parts = ["## Ambiguity Context", f"clarity: {clarity:.2f}", f"suggested_mode: {mode}"]
    if questions:
        parts.append("Clarifications needed:")
        for q in questions[:5]:
            dim = q.get("dimension", "unknown")
            template = q.get("template", "")
            options = q.get("options", [])
            parts.append(f"  [{dim}] {template}")
            if options:
                parts.append(f"    options: {', '.join(options)}")
    text = "\n".join(parts)
    if len(text) > max_tokens * 2:
        text = text[:max_tokens * 2] + "\n... (truncated)"
    return text


def compile_decision(dec_data: dict, max_tokens: int = 2000) -> str:
    decisions = dec_data.get("decisions", dec_data.get("pending_decisions", []))
    if not decisions:
        return "## Pending Decisions\n(none)"
    parts = ["## Pending Decisions"]
    for d in decisions[:10]:
        q = d.get("question", d.get("decision_id", "?"))
        opts = d.get("options", [])
        parts.append(f"- {q}")
        if opts:
            parts.append(f"  options: {', '.join(opts)}")
    text = "\n".join(parts)
    if len(text) > max_tokens * 2:
        text = text[:max_tokens * 2] + "\n... (truncated)"
    return text


def compile_intent(intent_data: dict, max_tokens: int = 2000) -> str:
    raw = intent_data.get("raw_input", "")
    mode = intent_data.get("mode_recommendation", "")
    urgency = intent_data.get("urgency_level", 0.5)
    frame = intent_data.get("semantic_frame", {})

    parts = ["## User Intent"]
    if raw:
        parts.append(f"input: {raw}")
    if mode:
        parts.append(f"mode: {mode}")
    parts.append(f"urgency: {urgency:.2f}")
    verb = frame.get("action_verb", "")
    obj = frame.get("action_object", {})
    if verb:
        parts.append(f"action: {verb}")
        if obj.get("object_name"):
            parts.append(f"target: {obj['object_name']} ({obj.get('object_type', '?')})")
    text = "\n".join(parts)
    if len(text) > max_tokens * 2:
        text = text[:max_tokens * 2] + "\n... (truncated)"
    return text


def compile_mode(mode_data: dict, max_tokens: int = 500) -> str:
    current = mode_data.get("current_mode", mode_data.get("mode", "instant"))
    parts = ["## Current Mode", f"mode: {current}"]
    for k, v in mode_data.items():
        if k not in ("current_mode", "mode"):
            parts.append(f"{k}: {v}")
    text = "\n".join(parts)
    if len(text) > max_tokens * 2:
        text = text[:max_tokens * 2] + "\n... (truncated)"
    return text


def create_mvsl_registry() -> SegmentRegistry:
    registry = SegmentRegistry()
    registry.register(PromptSegmentType.META, compile_meta)
    registry.register(PromptSegmentType.ROLE_DEFINITION, compile_role)
    registry.register(PromptSegmentType.MEMORY_SNAPSHOT, compile_memory)
    registry.register(PromptSegmentType.ROUTING_SIGNALS, compile_routing)
    return registry


def create_full_registry() -> SegmentRegistry:
    registry = SegmentRegistry()
    registry.register(PromptSegmentType.META, compile_meta, token_limit_override=300)
    registry.register(PromptSegmentType.ROLE_DEFINITION, compile_role, token_limit_override=2000)
    registry.register(PromptSegmentType.CAPABILITY_MANIFEST, compile_capability, token_limit_override=3000)
    registry.register(PromptSegmentType.CONSTRAINT_SET, compile_constraint, token_limit_override=1500)
    registry.register(PromptSegmentType.TOOL_REGISTRY, compile_tools, token_limit_override=8000)
    registry.register(PromptSegmentType.TASK_GRAPH, compile_task, token_limit_override=4000)
    registry.register(PromptSegmentType.MEMORY_SNAPSHOT, compile_memory, token_limit_override=5000)
    registry.register(PromptSegmentType.AMBIGUITY_CONTEXT, compile_ambiguity, token_limit_override=1000)
    registry.register(PromptSegmentType.DECISION_QUEUE, compile_decision, token_limit_override=2000)
    registry.register(PromptSegmentType.USER_INTENT, compile_intent, token_limit_override=2000)
    registry.register(PromptSegmentType.MODE_DECLARATION, compile_mode, token_limit_override=500)
    registry.register(PromptSegmentType.ROUTING_SIGNALS, compile_routing, token_limit_override=500)
    return registry
