import hashlib
import json
import logging
from uuid import uuid4

from ..schemas.intent import (
    AmbiguityVector,
    CognitiveMode,
    IntentPacket,
    SecurityLevel,
    SemanticFrame,
)

logger = logging.getLogger(__name__)

_FALLBACK_L1 = {
    "mode": "thinking",
    "urgency": 0.5,
    "ambiguity": {"scope": 0.0, "target": 0.0, "modality": 0.0, "authority": 0.0},
    "complexity": 0.5,
}


class L1ModeClassifier:

    RETRY_COUNT = 1

    def __init__(self, local_llm=None):
        self.llm = local_llm

    async def classify(self, raw_input: str) -> dict:
        last_error = None
        for attempt in range(self.RETRY_COUNT + 1):
            try:
                return await self._classify_attempt(raw_input)
            except Exception as exc:
                last_error = exc
                logger.warning("L1 classify attempt %d/%d failed: %s", attempt + 1, self.RETRY_COUNT + 1, exc)

        logger.error("L1 classification failed after %d attempts: %s", self.RETRY_COUNT + 1, last_error)
        return dict(_FALLBACK_L1)

    async def _classify_attempt(self, raw_input: str) -> dict:
        if self.llm is None:
            return self._keyword_fallback(raw_input)
        prompt = self._build_prompt(raw_input)
        response = await self.llm.generate(prompt)
        return self._parse_response(response.text if hasattr(response, "text") else str(response))

    def _build_prompt(self, raw_input: str) -> str:
        return f"""Classify this request into mode and urgency.

Modes: instant (simple), thinking (analysis), agent (tools), swarm (parallel), carbon-silicon (needs human)
Urgency: 0.0 (low) to 1.0 (high)

Extract ambiguity in: scope (unclear reference), target (unclear object), modality (unclear format), authority (unclear permissions)
Rate each 0.0 (clear) to 1.0 (highly ambiguous)

Request: {raw_input}

Respond with JSON:
{{"mode": "<mode>", "urgency": <float>, "ambiguity": {{"scope": <float>, "target": <float>, "modality": <float>, "authority": <float>}}, "complexity": <float>}}"""

    def _parse_response(self, response: str) -> dict:
        try:
            text = response.strip()
            if "```" in text:
                lines = [ln for ln in text.split("\n") if not ln.startswith("```")]
                text = "\n".join(lines)
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("L1 JSON parse failed, using fallback: %s", exc)
            return dict(_FALLBACK_L1)

    @staticmethod
    def _keyword_fallback(raw_input: str) -> dict:
        text_lower = raw_input.lower()
        result = dict(_FALLBACK_L1)

        high_urgency = any(
            kw in text_lower for kw in ("紧急", "urgent", "立即", "马上", "asap", "critical")
        )
        if high_urgency:
            result["urgency"] = 0.8

        complex_keywords = ("security", "deploy", "database", "architecture",
                            "安全", "部署", "数据库", "架构", "optimize", "优化")
        if any(kw in text_lower for kw in complex_keywords):
            result["complexity"] = 0.55
            result["mode"] = "thinking"

        simple_keywords = ("what", "how", "list", "show", "explain", "describe",
                           "什么", "怎么", "列表", "显示", "解释", "描述", "help")
        if any(kw in text_lower for kw in simple_keywords) and result.get("complexity", 0.5) <= 0.5:  # type: ignore[operator]
            result["mode"] = "instant"

        return result


class L2SemanticParser:

    RETRY_COUNT = 1

    def __init__(self, cloud_llm=None):
        self.llm = cloud_llm

    async def parse(self, raw_input: str, context: dict | None = None) -> SemanticFrame:
        if self.llm is None:
            logger.debug("L2 parser: no cloud LLM configured, using default frame")
            return SemanticFrame()

        last_error = None
        for attempt in range(self.RETRY_COUNT + 1):
            try:
                prompt = self._build_parse_prompt(raw_input, context)
                response = await self.llm.generate(prompt)
                return self._parse_frame(response.text if hasattr(response, "text") else str(response))
            except Exception as exc:
                last_error = exc
                logger.warning("L2 parse attempt %d/%d failed: %s", attempt + 1, self.RETRY_COUNT + 1, exc)

        logger.error("L2 parsing failed after %d attempts: %s", self.RETRY_COUNT + 1, last_error)
        return SemanticFrame()

    def _build_parse_prompt(self, raw_input: str, context: dict | None = None) -> str:
        ctx_str = ""
        if context:
            ctx_str = "\n".join(f"{k}: {v}" for k, v in context.items())
        return f"""Deep semantic analysis of request.

Context:
{ctx_str or "None"}

Request: {raw_input}

Analyze:
- action_verb: Standardized verb (analyze/create/modify/delete/search/explain/configure/deploy/audit/debug/test/document/review/summarize/translate/convert)
- action_object: What entity is being acted on (type, name, optional path)
- action_context: Domain, relevant tags, related entities
- expected_modalities: text/code/image/video/audio

Respond with JSON matching the SemanticFrame schema."""

    def _parse_frame(self, response: str) -> SemanticFrame:
        try:
            text = response.strip()
            if "```" in text:
                lines = [ln for ln in text.split("\n") if not ln.startswith("```")]
                text = "\n".join(lines)
            data = json.loads(text)
            return SemanticFrame(**data)
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning("L2 frame parse failed: %s", exc)
            return SemanticFrame()


class L3RuleValidator:

    def __init__(self, rule_engine=None):
        self.rules = {
            "max_urgency_for_instant": lambda i: i.mode_recommendation != CognitiveMode.INSTANT or i.urgency_level <= 0.8,
            "security_for_delete": lambda i: i.semantic_frame.action_verb.value != "delete" or i.required_clearance in (SecurityLevel.HIGH, SecurityLevel.CRITICAL),
            "ambiguity_threshold": lambda i: not i.ambiguity_vector.needs_clarification(0.9) or i.mode_recommendation in (CognitiveMode.AGENT, CognitiveMode.CARBON_SILICON),
        }

    async def validate(self, intent: IntentPacket) -> IntentPacket:
        for rule_name, rule_fn in self.rules.items():
            try:
                if not rule_fn(intent):
                    intent = self._apply_fix(intent, rule_name)
            except Exception:
                logger.warning("L3 rule %s evaluation failed, skipping", rule_name)
        return intent

    def _apply_fix(self, intent: IntentPacket, rule_name: str) -> IntentPacket:
        if rule_name == "max_urgency_for_instant":
            intent.mode_recommendation = CognitiveMode.THINKING
        elif rule_name == "security_for_delete":
            intent.required_clearance = SecurityLevel.CRITICAL
            intent.mode_recommendation = CognitiveMode.CARBON_SILICON
        elif rule_name == "ambiguity_threshold":
            intent.mode_recommendation = CognitiveMode.AGENT
        return intent


class AthenaIntentCore:

    def __init__(self, local_llm=None, cloud_llm=None, rule_engine=None):
        self.l1_classifier = L1ModeClassifier(local_llm)
        self.l2_parser = L2SemanticParser(cloud_llm)
        self.l3_validator = L3RuleValidator(rule_engine)

    async def parse(self, raw_input: str, context: dict | None = None) -> IntentPacket:
        if not raw_input or not raw_input.strip():
            return IntentPacket(raw_input=raw_input or "")

        try:
            l1_result = await self.l1_classifier.classify(raw_input)
        except Exception:
            logger.exception("L1 classification crashed")
            l1_result = dict(_FALLBACK_L1)

        try:
            if l1_result.get("complexity", 0.5) > 0.4:
                l2_frame = await self.l2_parser.parse(raw_input, context)
            else:
                l2_frame = SemanticFrame()
        except Exception:
            logger.exception("L2 parsing crashed")
            l2_frame = SemanticFrame()

        try:
            intent = IntentPacket(
                intent_id=uuid4(),
                raw_input=raw_input,
                mode_recommendation=CognitiveMode(l1_result.get("mode", "instant")),
                urgency_level=l1_result.get("urgency", 0.5),
                semantic_frame=l2_frame,
                ambiguity_vector=AmbiguityVector(**l1_result.get("ambiguity", {})),
                context_tags=l2_frame.action_context.tags if l2_frame.action_context else [],
            )
        except Exception:
            logger.exception("IntentPacket construction failed, using minimal packet")
            intent = IntentPacket(raw_input=raw_input)

        try:
            intent = await self.l3_validator.validate(intent)
        except Exception:
            logger.exception("L3 validation crashed")

        return intent

    def compute_fingerprint(self, intent: IntentPacket) -> str:
        content = (
            f"{intent.semantic_frame.action_verb.value}:"
            f"{intent.semantic_frame.action_object.object_type}:"
            f"{intent.semantic_frame.action_context.domain}"
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]
