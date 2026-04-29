"""
队列卡住处理器 — 替代 fix_queue_stopping_and_manual_launch.py 等 8 个脚本

故障模式:
- 队列状态为 "empty" 但实际有待处理任务
- 队列状态为 "manual_hold" 无法继续
- 队列状态为 "stopped" 需要重启
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from ops.fault_handler.registry import (
    BaseFaultHandler,
    FaultContext,
    FaultRegistry,
    FaultSeverity,
)

logger = logging.getLogger(__name__)

PLAN_QUEUE_DIR = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue"


class QueueStuckHandler(BaseFaultHandler):
    fault_type = "queue_stuck"
    severity = FaultSeverity.HIGH
    max_retries = 2

    def detect(self, ctx: FaultContext) -> bool:
        queue_id = ctx.metadata.get("queue_id")
        if not queue_id:
            return False

        queue_files = list(Path(PLAN_QUEUE_DIR).glob(f"*{queue_id}*.json"))
        if not queue_files:
            logger.debug(f"未找到队列文件: {queue_id}")
            return False

        queue_file = queue_files[0]
        with open(queue_file) as f:
            state = json.load(f)

        queue_status = state.get("queue_status", "")
        counts = state.get("counts", {})
        pending = int(counts.get("pending", 0))
        running = int(counts.get("running", 0))
        failed = int(counts.get("failed", 0))

        total = pending + running + failed
        if queue_status == "empty" and total > 0:
            ctx.metadata["queue_file"] = str(queue_file)
            ctx.metadata["pending_count"] = pending
            ctx.metadata["current_status"] = queue_status
            logger.warning(f"检测到队列状态不一致: status=empty, pending={pending}")
            return True

        if queue_status in ("manual_hold", "stopped"):
            ctx.metadata["queue_file"] = str(queue_file)
            ctx.metadata["current_status"] = queue_status
            logger.warning(f"检测到队列被暂停: status={queue_status}")
            return True

        return False

    def diagnose(self, ctx: FaultContext) -> dict[str, Any]:
        queue_file = ctx.metadata.get("queue_file", "")
        diagnosis = {"root_cause": "unknown", "evidence": []}

        if not queue_file or not os.path.exists(queue_file):
            diagnosis["root_cause"] = "queue_file_missing"
            return diagnosis

        with open(queue_file) as f:
            state = json.load(f)

        items = state.get("items", {})
        blocked_count = sum(
            1
            for item in items.values()
            if item.get("status", "") != "completed" and item.get("depends_on")
        )

        diagnosis.update(
            {
                "total_items": len(items),
                "blocked_items": blocked_count,
                "queue_status": state.get("queue_status"),
                "worker_status": state.get("worker_status"),
            }
        )

        if state.get("queue_status") == "empty" and len(items) > 0:
            diagnosis["root_cause"] = "queue_empty_state_mismatch"
            diagnosis["evidence"].append("队列状态为empty但存在活跃任务项")
        elif state.get("queue_status") == "manual_hold":
            diagnosis["root_cause"] = "manual_hold_active"
            diagnosis["evidence"].append("队列被手动暂停")
        elif state.get("queue_status") == "stopped":
            diagnosis["root_cause"] = "queue_stopped"
            diagnosis["evidence"].append("队列已停止，需要重启运行器")
        elif blocked_count > 0:
            diagnosis["root_cause"] = "dependency_chain_blocked"

        return diagnosis

    def repair(self, ctx: FaultContext) -> bool:
        queue_file = ctx.metadata.get("queue_file", "")
        if not queue_file or not os.path.exists(queue_file):
            return False

        try:
            with open(queue_file) as f:
                state = json.load(f)

            current_status = state.get("queue_status", "")

            if current_status == "empty":
                state["queue_status"] = "running"
                logger.info("已修复: 队列状态 empty -> running")
            elif current_status == "manual_hold":
                for _item_id, item in state.get("items", {}).items():
                    if item.get("status") == "manual_hold":
                        item["status"] = "pending"
                state["queue_status"] = "running"
                logger.info("已修复: 解除手动暂停状态")
            elif current_status == "stopped":
                state["queue_status"] = "running"
                logger.info("已修复: 队列状态 stopped -> running")

            with open(queue_file, "w") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            logger.error(f"修复队列失败: {e}")
            return False

    def verify(self, ctx: FaultContext) -> bool:
        queue_file = ctx.metadata.get("queue_file", "")
        if not queue_file or not os.path.exists(queue_file):
            return False

        with open(queue_file) as f:
            state = json.load(f)

        return state.get("queue_status") == "running"


FaultRegistry.register(QueueStuckHandler)
