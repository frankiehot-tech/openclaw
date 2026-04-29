"""
Semantic Layer - 自然语言到结构化任务的转换层

将用户自然语言输入解析为结构化意图，映射到系统治理函数，
并通过 NL 接口与任务队列交互。
"""

from .command_map import COMMAND_MAP, execute_intent, get_available_commands
from .intent_parser import IntentParser, IntentType, ParsedIntent, parse_intent
from .task_queue_nl import TaskQueueNL

__all__ = [
    "IntentParser",
    "ParsedIntent",
    "IntentType",
    "parse_intent",
    "COMMAND_MAP",
    "execute_intent",
    "get_available_commands",
    "TaskQueueNL",
]
