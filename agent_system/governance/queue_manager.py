"""
Queue Manager Module - 队列管理 stub

提供队列状态查询、队列操作等基础功能。
在完整实现中，此模块将对接 athena_ai_plan_runner 和 plan_queue。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from scripts.openclaw_roots import QUEUE_STATE_DIR
except ImportError:
    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
    import sys

    sys.path.insert(0, str(scripts_dir))
    from openclaw_roots import QUEUE_STATE_DIR


class QueueManager:
    """队列管理器 — 提供队列健康检查与操作接口。"""

    def get_all_queues(self) -> dict[str, Any]:
        """获取所有队列的当前状态摘要。"""
        if not QUEUE_STATE_DIR.exists():
            return {"queues": {}, "error": "Queue state directory not found"}

        result: dict[str, Any] = {}
        exclude_keywords = [
            "backup", "dedup", "report", "monitor_backup",
            "batch_reset", "manual_hold_fix", "dependency_fix",
        ]

        for queue_file in QUEUE_STATE_DIR.glob("*.json"):
            fname = queue_file.name.lower()
            if any(kw in fname for kw in exclude_keywords):
                continue
            if queue_file.name.endswith(".backup"):
                continue

            try:
                with open(queue_file) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            result[queue_file.stem] = {
                "status": data.get("queue_status", "unknown"),
                "item_count": len(data.get("items", {})),
                "updated_at": data.get("updated_at", ""),
                "current_item_id": data.get("current_item_id", ""),
            }

        return {"queues": result, "total": len(result)}

    def get_queue_detail(self, queue_name: str) -> dict[str, Any]:
        """获取指定队列的详细信息。"""
        queue_path = QUEUE_STATE_DIR / f"{queue_name}.json"
        if not queue_path.exists():
            return {"error": f"Queue '{queue_name}' not found"}

        try:
            with open(queue_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return {"error": f"Failed to read queue: {e}"}

    def get_queue_counts(self) -> dict[str, dict[str, int]]:
        """获取各队列的任务计数统计。"""
        counts: dict[str, dict[str, int]] = {}

        all_queues = self.get_all_queues()
        for name, _info in all_queues.get("queues", {}).items():
            detail = self.get_queue_detail(name)
            if "error" in detail:
                continue

            items = detail.get("items", {})
            if isinstance(items, list):
                item_list = items
            elif isinstance(items, dict):
                item_list = list(items.values())
            else:
                item_list = []

            status_counts: dict[str, int] = {
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "manual_hold": 0,
            }
            for item in item_list:
                if isinstance(item, dict):
                    s = str(item.get("status", "pending")).lower()
                    if s in status_counts:
                        status_counts[s] += 1

            counts[name] = status_counts

        return counts


_queue_manager_instance: QueueManager | None = None


def get_queue_manager() -> QueueManager:
    """获取 QueueManager 单例。"""
    global _queue_manager_instance
    if _queue_manager_instance is None:
        _queue_manager_instance = QueueManager()
    return _queue_manager_instance
