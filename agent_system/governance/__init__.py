"""
Governance Module - 系统治理与自愈

提供系统健康检查、队列管理、自愈修复等功能
"""

from .queue_manager import get_queue_manager
from .system_health import SelfHealing

__all__ = [
    "SelfHealing",
    "get_queue_manager",
]
