"""Auto-rollback — revert deployments when metrics degrade.

Ties into the git-based KEEP/DISCARD mechanism.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)


class RollbackTrigger(Enum):
    ERROR_RATE = auto()
    LATENCY_SPIKE = auto()
    TEST_FAILURE = auto()
    MANUAL = auto()


@dataclass
class RollbackResult:
    success: bool
    commit_before: str
    commit_after: str
    trigger: RollbackTrigger
    reason: str
    output: str = ""


class AutoRollback:
    """Automatic rollback via git reset --hard to previous commit."""

    def __init__(self, base_path: str | None = None, max_rollbacks: int = 2) -> None:
        self.base_path = base_path or "."
        self.max_rollbacks = max_rollbacks
        self._rollback_count = 0

    def rollback(self, trigger: RollbackTrigger, reason: str) -> RollbackResult:
        if self._rollback_count >= self.max_rollbacks:
            return RollbackResult(
                success=False,
                commit_before="",
                commit_after="",
                trigger=trigger,
                reason=f"Max rollbacks ({self.max_rollbacks}) exceeded",
            )

        try:
            before = self._current_commit()
            subprocess.run(
                ["git", "reset", "--hard", "HEAD~1"],
                capture_output=True, text=True,
                cwd=self.base_path, timeout=30, check=True,
            )
            self._rollback_count += 1
            after = self._current_commit()
            logger.warning(f"AutoRollback: {before[:7]} → {after[:7]} ({trigger.name}: {reason})")

            return RollbackResult(
                success=True,
                commit_before=before,
                commit_after=after,
                trigger=trigger,
                reason=reason,
            )
        except subprocess.CalledProcessError as e:
            return RollbackResult(
                success=False,
                commit_before="",
                commit_after="",
                trigger=trigger,
                reason=f"Git reset failed: {e.stderr[:200]}" if e.stderr else str(e),
            )

    def _current_commit(self) -> str:
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True,
                cwd=self.base_path, timeout=5, check=True,
            )
            return proc.stdout.strip()
        except Exception:
            return "unknown"
