
import asyncio

from ..schemas.intent import IntentPacket
from ..schemas.state import SemanticStateSnapshot
from ..schemas.tool import ToolExecutionPlan, ToolSemanticEntry, ToolSemanticSearchResult


class ToolSemanticRegistry:
    def __init__(self):
        self.tools: list[ToolSemanticEntry] = []

    def register(self, tool: ToolSemanticEntry) -> None:
        self.tools.append(tool)

    def register_batch(self, tools: list[ToolSemanticEntry]) -> None:
        self.tools.extend(tools)

    def semantic_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        threshold: float = 0.6,
    ) -> list[ToolSemanticSearchResult]:
        results = []
        for tool in self.tools:
            if not tool.capability_embedding:
                continue
            score = self._cosine_similarity(query_vector, tool.capability_embedding)
            if score >= threshold:
                results.append(
                    ToolSemanticSearchResult(
                        tool=tool,
                        similarity_score=score,
                        match_reason=tool.nl_descriptions[0] if tool.nl_descriptions else "",
                    )
                )
        results.sort(key=lambda r: r.similarity_score, reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def get_by_category(self, category: str) -> list[ToolSemanticEntry]:
        return [t for t in self.tools if t.category == category]

    @property
    def total_tools(self) -> int:
        return len(self.tools)


class AthenaToolRouter:
    def __init__(self, mcp_client=None, code_proxy=None):
        self.semantic_registry = ToolSemanticRegistry()
        self.mcp_client = mcp_client
        self.code_proxy = code_proxy

    async def route(self, intent: IntentPacket, state: SemanticStateSnapshot | None = None) -> ToolExecutionPlan:
        intent_vector = self._encode_intent(intent)
        candidates = self.semantic_registry.semantic_search(intent_vector, top_k=5)

        if self.mcp_client:
            for result in candidates:
                tool = result.tool
                if tool.server_id and not self._is_connected(tool.server_id):
                    await self._lazy_connect(tool.server_id)

        execution_code = await self._generate_tool_code(intent, [r.tool for r in candidates])

        return ToolExecutionPlan(
            tools=[r.tool for r in candidates],
            execution_code=execution_code,
            estimated_tokens=sum(r.tool.token_cost for r in candidates) + len(execution_code) // 4,
        )

    def _encode_intent(self, intent: IntentPacket) -> list[float]:
        verb_embedding = self._verb_to_vector(intent.semantic_frame.action_verb.value)
        obj_embedding = self._type_to_vector(intent.semantic_frame.action_object.object_type)
        combined = verb_embedding + obj_embedding
        return combined

    def _verb_to_vector(self, verb: str) -> list[float]:
        verbs = [
            "analyze", "create", "modify", "delete", "search", "explain",
            "configure", "deploy", "audit", "debug", "test", "document",
            "review", "summarize", "translate", "convert",
        ]
        if verb in verbs:
            idx = verbs.index(verb)
            vector = [0.0] * 8
            vector[idx // 2] = 1.0
            return vector
        return [0.0] * 8

    def _type_to_vector(self, obj_type: str) -> list[float]:
        types = ["file", "code", "database", "config", "network", "security", "document", "general"]
        if obj_type in types:
            idx = types.index(obj_type)
            vector = [0.0] * 8
            vector[idx] = 1.0
            return vector
        return [0.0] * 7 + [1.0]

    def _is_connected(self, server_id: str) -> bool:
        if self.mcp_client:
            return getattr(self.mcp_client, "is_connected", lambda x: False)(server_id)
        return False

    async def _lazy_connect(self, server_id: str) -> None:
        if self.mcp_client:
            fn = getattr(self.mcp_client, "lazy_connect", None)
            if fn:
                result = fn(server_id)
                if asyncio.iscoroutine(result):
                    await result

    async def _generate_tool_code(self, intent: IntentPacket, tools: list[ToolSemanticEntry]) -> str:
        if not tools:
            return "# No tools matched"

        tool_names = [t.tool_id for t in tools]
        lines = [
            "# Auto-generated tool execution code",
            f"# Intent: {intent.semantic_frame.action_verb.value} on {intent.semantic_frame.action_object.object_type}",
            f"# Matched tools: {', '.join(tool_names)}",
        ]
        return "\n".join(lines)
