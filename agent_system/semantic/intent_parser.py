"""
Intent Parser - 使用 LLM 将自然语言解析为结构化意图

支持基于规则回退的意图解析，在 LLM 不可用时使用关键词匹配。
"""

from __future__ import annotations

import json
import logging
import os
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class IntentType(StrEnum):
    """可识别的意图类型枚举。"""

    QUEUE_HEALTH = "queue_health"
    SYSTEM_AUDIT = "system_audit"
    STATUS_REPORT = "status_report"
    FIX_ISSUE = "fix_issue"
    DEPLOY = "deploy"
    AUTORESEARCH = "autoresearch"
    UNKNOWN = "unknown"


class ParsedIntent(BaseModel):
    """LLM 解析后的结构化意图。"""

    intent: IntentType = Field(description="分类后的意图类型")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度 0.0-1.0")
    entities: dict[str, Any] = Field(default_factory=dict, description="从文本中提取的实体，如 queue_name, target 等")
    raw_text: str = Field(default="", description="原始输入文本")
    explanation: str = Field(default="", description="解析说明（LLM 模式下提供）")


# ------------------------------------------------------------------
# 关键词 → 意图回退规则
# ------------------------------------------------------------------

_KEYWORD_RULES: list[tuple[IntentType, list[str]]] = [
    (
        IntentType.QUEUE_HEALTH,
        ["队列", "queue", "健康", "health", "检查队列", "队列状态", "queue status", "停滞", "stalled", "积压", "backlog"],
    ),
    (
        IntentType.SYSTEM_AUDIT,
        ["审计", "audit", "系统审计", "system audit", "安全检查", "security check", "审查", "inspect"],
    ),
    (
        IntentType.STATUS_REPORT,
        ["状态", "status", "报告", "report", "概要", "summary", "概况", "overview", "仪表板", "dashboard"],
    ),
    (
        IntentType.FIX_ISSUE,
        ["修复", "fix", "问题", "issue", "解决", "resolve", "错误", "error", "失败", "failed", "卡住", "stuck"],
    ),
    (
        IntentType.DEPLOY,
        ["部署", "deploy", "发布", "release", "上线", "launch", "推送", "push"],
    ),
    (
        IntentType.AUTORESEARCH,
        ["autoresearch", "auto_research", "自动研究", "自动分析", "research engine", "研究引擎", "自我优化", "self-optimize", "优化建议", "研究一下", "调研一下", "帮我研究", "分析一下", "查一下资料"],
    ),
]


def _keyword_match(text: str) -> tuple[IntentType, dict[str, Any]]:
    """基于关键词匹配的意图识别回退。"""
    text_lower = text.lower()
    best_match = IntentType.UNKNOWN
    best_score = 0
    matched_keywords: list[str] = []

    for intent_type, keywords in _KEYWORD_RULES:
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > best_score:
            best_score = score
            best_match = intent_type
            matched_keywords = [kw for kw in keywords if kw.lower() in text_lower]

    # 提取基础实体
    entities: dict[str, Any] = {"matched_keywords": matched_keywords}

    # 尝试提取 queue_name
    import re

    queue_match = re.search(r"(?:队列|queue)\s*(?:名称|name)?\s*[:：]?\s*(\w+)", text, re.IGNORECASE)
    if queue_match:
        entities["queue_name"] = queue_match.group(1)

    # 置信度：匹配的关键词越多，置信度越高
    confidence = min(best_score / 3.0, 1.0) if best_match != IntentType.UNKNOWN else 0.3

    return best_match, entities, confidence


def _llm_parse(text: str) -> ParsedIntent | None:
    """使用 LLM 解析意图。返回 None 表示 LLM 不可用。"""
    try:
        import requests

        api_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")

        if not api_key:
            logger.debug("No LLM API key configured, using keyword fallback")
            return None

        intent_types_desc = "\n".join(f"- {t.value}: {t.name}" for t in IntentType)
        prompt = f"""You are an intent parser. Classify the user's NL input into one intent type.

Intent types:
{intent_types_desc}

Input: {text}

Respond ONLY with a JSON object:
{{"intent": "<type>", "confidence": <0.0-1.0>, "entities": {{}}, "explanation": "<brief>"}}"""

        response = requests.post(
            f"{api_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
            timeout=15,
        )
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"].strip()

        # 提取 JSON（可能被 markdown 代码块包裹）
        if "```" in content:
            # 去掉 markdown 代码块标记
            lines = [ln for ln in content.split("\n") if not ln.startswith("```")]
            content = "\n".join(lines)

        data = json.loads(content)
        return ParsedIntent(
            intent=IntentType(data.get("intent", "unknown")),
            confidence=float(data.get("confidence", 0.5)),
            entities=data.get("entities", {}),
            raw_text=text,
            explanation=data.get("explanation", ""),
        )
    except Exception as e:
        logger.warning(f"LLM parse failed, using keyword fallback: {e}")
        return None


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def parse_intent(text: str, use_llm: bool = True) -> ParsedIntent:
    """解析自然语言为结构化意图。

    Args:
        text: 用户输入的自然语言文本
        use_llm: 是否尝试使用 LLM 解析（失败时回退到关键词匹配）

    Returns:
        ParsedIntent 包含意图类型、置信度和提取实体
    """
    if not text or not text.strip():
        return ParsedIntent(intent=IntentType.UNKNOWN, confidence=0.0, raw_text=text)

    text = text.strip()

    # 优先尝试 LLM
    if use_llm:
        result = _llm_parse(text)
        if result is not None:
            return result

    # 关键词回退
    intent_type, entities, confidence = _keyword_match(text)
    return ParsedIntent(
        intent=intent_type,
        confidence=confidence,
        entities=entities,
        raw_text=text,
        explanation=f"Keyword-based classification ({len(entities.get('matched_keywords', []))} keywords matched)",
    )


class IntentParser:
    """意图解析器（可实例化版本，用于需要状态管理的场景）。"""

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm

    def parse(self, text: str) -> ParsedIntent:
        return parse_intent(text, use_llm=self.use_llm)
