"""
Queue Manager Module - 队列管理

适配层: 将 governance/ 模块的 QueueManager 封装为 command_map.py 所需的 API。
"""

from __future__ import annotations

import logging
from typing import Any

from governance.queue_manager import QueueManager as _QueueManager

logger = logging.getLogger(__name__)


class QueueManager:
    """队列管理器 — 封装 governance.QueueManager 适配 command_map API。"""

    def __init__(self) -> None:
        self._inner = _QueueManager()

    def get_all_queues(self) -> dict[str, Any]:
        queues = self._inner.list_queues()
        items: dict[str, Any] = {}
        for qpath in queues:
            data = self._inner.load_queue(str(qpath))
            if data:
                qid = data.get("queue_id", qpath.stem)
                items[qid] = data
        return {"total": len(items), "queues": items}

    def get_queue_counts(self) -> dict[str, dict[str, int]]:
        queues = self._inner.list_queues()
        counts: dict[str, dict[str, int]] = {}
        for qpath in queues:
            data = self._inner.load_queue(str(qpath))
            if data:
                qid = data.get("queue_id", qpath.stem)
                items = data.get("items", {})
                if isinstance(items, dict):
                    counts[qid] = _QueueManager.compute_counts(items)
                else:
                    counts[qid] = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
        return counts


_queue_manager_instance: QueueManager | None = None


def get_queue_manager() -> QueueManager:
    global _queue_manager_instance
    if _queue_manager_instance is None:
        _queue_manager_instance = QueueManager()
    return _queue_manager_instance
