"""Coordinator Mode v0.2.0 — Git Worktree isolation per agent.

Each agent runs in its own git worktree to prevent concurrent write conflicts.
The coordinator manages worktree lifecycle: create → use → cleanup.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Worktree:
    agent_id: str
    path: Path
    branch: str
    created: float = field(default_factory=time.time)
    active: bool = True


class WorktreeIsolation:
    """Manages git worktrees for agent isolation."""

    def __init__(self, base_repo: str | Path | None = None, base_branch: str = "main") -> None:
        self.base_repo = Path(base_repo or Path.cwd())
        self.base_branch = base_branch
        self._worktrees: dict[str, Worktree] = {}
        self._base_dir = self.base_repo / ".openclaw" / "worktrees"

    def create(self, agent_id: str, source_branch: str | None = None) -> Worktree:
        branch = source_branch or self.base_branch
        wt_path = self._base_dir / f"{agent_id}-{int(time.time())}"
        wt_path.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["git", "worktree", "add", str(wt_path), branch],
            cwd=self.base_repo, capture_output=True, text=True, timeout=30, check=True,
        )
        wt = Worktree(agent_id=agent_id, path=wt_path, branch=branch)
        self._worktrees[agent_id] = wt
        logger.info(f"Worktree created: {agent_id} → {wt_path}")
        return wt

    def get(self, agent_id: str) -> Worktree | None:
        return self._worktrees.get(agent_id)

    def remove(self, agent_id: str) -> bool:
        wt = self._worktrees.pop(agent_id, None)
        if not wt:
            return False
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt.path)],
            cwd=self.base_repo, capture_output=True, text=True, timeout=30,
        )
        if wt.path.exists():
            shutil.rmtree(wt.path, ignore_errors=True)
        logger.info(f"Worktree removed: {agent_id}")
        return True

    def prune(self) -> int:
        proc = subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.base_repo, capture_output=True, text=True, timeout=30,
        )
        return proc.returncode

    def list_worktrees(self) -> list[str]:
        proc = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.base_repo, capture_output=True, text=True, timeout=10,
        )
        return [line for line in proc.stdout.split("\n") if line.strip()]
