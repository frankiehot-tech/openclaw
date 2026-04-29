"""
Task Queue NL - 自然语言与任务队列的交互接口

提供 TaskQueueNL 类，允许用户通过自然语言与 Athena 任务队列交互。
"""

from __future__ import annotations

import logging
from typing import Any

from .command_map import execute_intent, get_available_commands
from .intent_parser import IntentType, parse_intent

logger = logging.getLogger(__name__)


class TaskQueueNL:
    """自然语言任务队列交互接口。

    用法:
        tq = TaskQueueNL()
        result = tq.process("检查队列健康")
        print(tq.explain(result))
    """

    # 中文映射，用于 NL 输出
    _INTENT_LABELS: dict[IntentType, str] = {
        IntentType.QUEUE_HEALTH: "队列健康检查",
        IntentType.SYSTEM_AUDIT: "系统审计",
        IntentType.STATUS_REPORT: "状态报告",
        IntentType.FIX_ISSUE: "问题修复",
        IntentType.DEPLOY: "部署",
        IntentType.AUTORESEARCH: "自动研究",
        IntentType.UNKNOWN: "未知指令",
    }

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm

    def process(self, text: str) -> dict[str, Any]:
        """处理自然语言输入，执行对应的系统操作。

        Args:
            text: 用户自然语言输入

        Returns:
            包含 intent, result, summary 的完整响应 dict
        """
        intent = parse_intent(text, use_llm=self.use_llm)
        result = execute_intent(intent)

        return {
            "input": text,
            "intent": {
                "type": intent.intent.value,
                "label": self._INTENT_LABELS.get(intent.intent, "未知"),
                "confidence": intent.confidence,
                "entities": intent.entities,
                "explanation": intent.explanation,
            },
            "result": result,
            "summary": result.get("summary", "No summary"),
        }

    def explain(self, processed: dict[str, Any]) -> str:
        """将处理结果格式化为人类可读的自然语言摘要。"""
        intent_info = processed.get("intent", {})
        result = processed.get("result", {})
        summary = processed.get("summary", "")

        lines = [
            f"输入: {processed['input']}",
            f"意图: {intent_info.get('label', '未知')} ({intent_info.get('type', '?')})",
            f"置信度: {intent_info.get('confidence', 0):.0%}",
        ]

        if intent_info.get("explanation"):
            lines.append(f"解析说明: {intent_info['explanation']}")

        lines.append(f"结果: {summary}")

        # 附加详情
        if result.get("action") == "autoresearch" and "cycle_id" in result:
            lines.append(f"研究周期: {result['cycle_id']}")
            lines.append(f"发现: {result.get('findings', 0)} 项")
            lines.append(f"建议: {result.get('recommendations', 0)} 项")
        elif "stalled_queues" in result and result["stalled_queues"]:
            stall = result["stalled_queues"]
            lines.append(f"停滞队列: {len(stall)} 个")
            for sq in stall[:5]:
                lines.append(
                    f"  - {sq['queue_name']}: {sq['age_minutes']}min, p:{sq.get('pending', 0)} r:{sq.get('running', 0)} c:{sq.get('completed', 0)}"
                )
        elif "queues" in result:
            qinfo = result["queues"]
            lines.append(f"队列总数: {qinfo.get('total', 0)}")

        if result.get("error"):
            lines.append(f"错误: {result['error']}")

        return "\n".join(lines)

    def available_commands(self) -> list[str]:
        """获取可用命令列表。"""
        return get_available_commands()

    def get_intent_labels(self) -> dict[str, str]:
        """获取意图类型的中文标签映射。"""
        return {k.value: v for k, v in self._INTENT_LABELS.items()}
