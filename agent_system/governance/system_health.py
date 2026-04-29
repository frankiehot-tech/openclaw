"""
System Health Module - 系统健康检查与自愈

实现 SelfHealing 类，提供队列停滞检测、自动修复、升级告警等功能。
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from scripts.openclaw_roots import LOG_DIR, QUEUE_STATE_DIR, RUNTIME_ROOT
except ImportError:
    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
    import sys

    sys.path.insert(0, str(scripts_dir))
    from openclaw_roots import LOG_DIR, QUEUE_STATE_DIR, RUNTIME_ROOT


class SelfHealing:
    """检测停滞队列并执行自动修复。

    检测规则：
    - 队列最后更新时间 > 30 分钟前
    - 队列状态为 running 或有 pending 任务但无进展
    - 最多自动重试 2 次，超过后升级为人工告警
    """

    MAX_RETRIES = 2
    STALL_AGE_MINUTES = 30

    def __init__(self, max_retries: int | None = None):
        self.max_retries = max_retries or self.MAX_RETRIES
        self._heal_log: list[dict[str, Any]] = []
        self._retry_counts: dict[str, int] = {}

    def _load_retry_counts(self) -> None:
        """从持久化文件中加载重试计数。"""
        heal_state_path = RUNTIME_ROOT / ".openclaw" / "heal_state.json"
        if heal_state_path.exists():
            try:
                with open(heal_state_path) as f:
                    self._retry_counts = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._retry_counts = {}
        else:
            self._retry_counts = {}

    def _save_retry_counts(self) -> None:
        """持久化重试计数。"""
        heal_state_path = RUNTIME_ROOT / ".openclaw" / "heal_state.json"
        heal_state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(heal_state_path, "w") as f:
                json.dump(self._retry_counts, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save heal state: {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_stalled_queues(self) -> list[dict[str, Any]]:
        """检测停滞队列：年龄 > 30min 且无进度。

        Returns:
            停滞队列列表，每个元素包含 queue_name, age_minutes, status, reason
        """
        self._load_retry_counts()
        stalled: list[dict[str, Any]] = []

        if not QUEUE_STATE_DIR.exists():
            return stalled

        now = datetime.now(UTC)
        exclude_keywords = [
            "backup", "dedup", "report", "monitor_backup",
            "batch_reset", "manual_hold_fix", "dependency_fix",
            "queue_status_fix", "athena_enterprise_fix",
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

            updated_at_str = data.get("updated_at", "")
            if not updated_at_str:
                continue

            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=UTC)
                else:
                    updated_at = updated_at.astimezone(UTC)
            except ValueError:
                continue

            age_minutes = (now - updated_at).total_seconds() / 60
            if age_minutes < self.STALL_AGE_MINUTES:
                continue

            queue_status = data.get("queue_status", "unknown")
            items = data.get("items", {})
            if isinstance(items, (list, dict)):
                total = len(items)
            else:
                total = 0

            counts = data.get("counts", {})
            pending = counts.get("pending", 0)
            running = counts.get("running", 0)
            completed = counts.get("completed", 0)

            has_work = (queue_status == "running" or pending > 0 or running > 0) and total > 0
            no_progress = completed == 0 and total > 0

            if has_work and no_progress and queue_status != "empty":
                stalled.append({
                    "queue_name": queue_file.stem,
                    "age_minutes": round(age_minutes, 1),
                    "status": queue_status,
                    "pending": pending,
                    "running": running,
                    "completed": completed,
                    "total": total,
                    "retries": self._retry_counts.get(queue_file.stem, 0),
                })

        return stalled

    def auto_heal(self, stalled_queues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """对停滞队列执行自动修复，最多重试 max_retries 次。

        Args:
            stalled_queues: detect_stalled_queues() 的返回值

        Returns:
            修复结果列表
        """
        results: list[dict[str, Any]] = []

        for queue_info in stalled_queues:
            queue_name = queue_info["queue_name"]
            retries = self._retry_counts.get(queue_name, 0)

            result = {
                "queue_name": queue_name,
                "action": "none",
                "success": False,
                "detail": "",
            }

            if retries >= self.max_retries:
                result["action"] = "escalate"
                result["detail"] = f"Max retries ({self.max_retries}) exceeded"
                self._escalate(queue_info)
            elif self._can_auto_heal(queue_info):
                success = self._perform_heal(queue_info)
                self._retry_counts[queue_name] = retries + 1
                self._save_retry_counts()
                result["action"] = "heal"
                result["success"] = success
                result["detail"] = (
                    f"Heal {'succeeded' if success else 'failed'} "
                    f"(attempt {self._retry_counts[queue_name]}/{self.max_retries})"
                )
            else:
                result["action"] = "escalate"
                result["detail"] = "Cannot auto-heal, escalating"
                self._escalate(queue_info)

            self._heal_log.append({**result, "timestamp": datetime.now(UTC).isoformat()})
            results.append(result)

        return results

    def _can_auto_heal(self, queue_info: dict[str, Any]) -> bool:
        """判断队列是否可自动修复。

        可修复条件：
        - 队列文件存在且可写
        - 不存在极端异常状态（如所有任务都 failed）
        - 队列未被手动暂停（pause_reason 为空）
        """
        queue_name = queue_info["queue_name"]
        queue_path = QUEUE_STATE_DIR / f"{queue_name}.json"

        if not queue_path.exists():
            return False

        try:
            with open(queue_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return False

        # 检查是否被手动暂停
        pause_reason = data.get("pause_reason", "")
        if pause_reason and pause_reason not in ("empty", ""):
            logger.info(f"Queue {queue_name} is manually paused: {pause_reason}")
            return False

        # 检查是否所有任务都 failed（不可自动修复）
        items = data.get("items", {})
        if isinstance(items, list):
            item_list = items
        elif isinstance(items, dict):
            item_list = list(items.values())
        else:
            item_list = []

        if item_list:
            all_failed = all(
                item.get("status") == "failed" for item in item_list if isinstance(item, dict)
            )
            if all_failed:
                return False

        return True

    def _perform_heal(self, queue_info: dict[str, Any]) -> bool:
        """执行实际的修复操作。

        修复策略：
        1. 如果队列状态为 running 但没有 current_item，重置为 active
        2. 如果队列状态为 running 且超过阈值年龄，尝试标记当前任务为 stalled 并推进
        """
        queue_name = queue_info["queue_name"]
        queue_path = QUEUE_STATE_DIR / f"{queue_name}.json"

        try:
            with open(queue_path) as f:
                data = json.load(f)

            modified = False

            # 策略1: running 但无 current_item → 重置状态
            if data.get("queue_status") == "running" and not data.get("current_item_id"):
                data["queue_status"] = "active"
                data["updated_at"] = datetime.now(UTC).isoformat()
                modified = True
                logger.info(f"Healed queue {queue_name}: reset status from running to active (no current item)")

            # 策略2: running 且年龄 > 阈值 → 尝试推进
            if data.get("queue_status") == "running":
                items = data.get("items", {})
                if isinstance(items, list):
                    item_list = [(i.get("id"), i) for i in items if isinstance(i, dict)]
                elif isinstance(items, dict):
                    item_list = list(items.items())
                else:
                    item_list = []

                # 找到第一个 pending 任务并推进
                for item_id, item_data in item_list:
                    if isinstance(item_data, dict) and item_data.get("status") == "pending":
                        data["current_item_id"] = item_id
                        if isinstance(items, dict) and item_id in items:
                            items[item_id]["status"] = "running"
                        elif isinstance(items, list):
                            for i in items:
                                if isinstance(i, dict) and i.get("id") == item_id:
                                    i["status"] = "running"
                        data["updated_at"] = datetime.now(UTC).isoformat()
                        modified = True
                        logger.info(
                            f"Healed queue {queue_name}: advanced pending task {item_id} to running"
                        )
                        break
                else:
                    # 没有 pending 任务但状态是 running → 标记为 active
                    data["queue_status"] = "active"
                    data["updated_at"] = datetime.now(UTC).isoformat()
                    modified = True
                    logger.info(f"Healed queue {queue_name}: reset status to active (no pending tasks)")

            if modified:
                # 写入备份
                backup_path = queue_path.with_suffix(".backup")
                with open(backup_path, "w") as f:
                    json.dump(data, f, indent=2)

                # 写入修复后的数据
                with open(queue_path, "w") as f:
                    json.dump(data, f, indent=2)

                return True

            return False

        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to heal queue {queue_name}: {e}")
            return False

    def _escalate(self, queue_info: dict[str, Any]) -> None:
        """升级告警：写入告警日志，当无法自动修复时触发。

        Args:
            queue_info: 停滞队列信息
        """
        queue_name = queue_info["queue_name"]
        alert_entry = {
            "type": "heal_escalation",
            "queue": queue_name,
            "age_minutes": queue_info.get("age_minutes", 0),
            "retries": self._retry_counts.get(queue_name, self.max_retries),
            "message": (
                f"Queue {queue_name} requires manual intervention after "
                f"{self._retry_counts.get(queue_name, self.max_retries)} failed auto-heal attempts"
            ),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        logger.warning(f"ESCALATION: {alert_entry['message']}")

        # 写入告警日志
        alert_log_path = LOG_DIR / "heal_escalations.jsonl"
        alert_log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(alert_log_path, "a") as f:
                f.write(json.dumps(alert_entry, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error(f"Failed to write escalation log: {e}")

    def get_heal_log(self) -> list[dict[str, Any]]:
        """获取自愈操作历史。"""
        return list(self._heal_log)


def get_system_health() -> SelfHealing:
    """获取 SelfHealing 单例。"""
    return SelfHealing()
