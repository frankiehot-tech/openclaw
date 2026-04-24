"""
僵尸任务处理器 — 替代 fix_zombie_running.py 等 4 个脚本

故障模式:
- 任务状态为 "running" 但对应进程已不存在
- 任务运行时间超过超时阈值
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from ops.fault_handler.registry import (
    BaseFaultHandler,
    FaultContext,
    FaultRegistry,
    FaultSeverity,
)

logger = logging.getLogger(__name__)
PLAN_QUEUE_DIR = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue"
ZOMBIE_TIMEOUT_MINUTES = 30


class ZombieTaskHandler(BaseFaultHandler):
    fault_type = "zombie_task"
    severity = FaultSeverity.HIGH
    max_retries = 1

    def detect(self, ctx: FaultContext) -> bool:
        queue_files = list(Path(PLAN_QUEUE_DIR).glob("*.json"))
        for qf in queue_files:
            with open(qf) as f:
                state = json.load(f)
            for item_id, item in state.get("items", {}).items():
                if item.get("status") == "running":
                    ctx.metadata["queue_file"] = str(qf)
                    ctx.metadata["task_id"] = item_id
                    logger.warning(f"发现可疑运行中任务: {item_id}")
                    return True
        return False

    def diagnose(self, ctx: FaultContext) -> Dict[str, Any]:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True
        )
        running_processes = result.stdout

        task_id = ctx.metadata.get("task_id", "")
        queue_file = ctx.metadata.get("queue_file", "")

        is_dead = task_id not in running_processes
        return {
            "process_alive": not is_dead,
            "task_id": task_id,
            "queue_file": queue_file,
        }

    def repair(self, ctx: FaultContext) -> bool:
        queue_file = ctx.metadata.get("queue_file", "")
        task_id = ctx.metadata.get("task_id", "")
        if not queue_file or not task_id:
            return False

        with open(queue_file) as f:
            state = json.load(f)

        if task_id in state.get("items", {}):
            item = state["items"][task_id]
            item["status"] = "failed"
            item["fail_reason"] = "zombie_task: process not found"
            logger.info(f"已标记为僵尸: {task_id}")

        with open(queue_file, 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        return True

    def verify(self, ctx: FaultContext) -> bool:
        queue_file = ctx.metadata.get("queue_file", "")
        task_id = ctx.metadata.get("task_id", "")
        if not queue_file or not task_id:
            return False

        with open(queue_file) as f:
            state = json.load(f)

        item = state.get("items", {}).get(task_id, {})
        return item.get("status") == "failed"


FaultRegistry.register(ZombieTaskHandler)
