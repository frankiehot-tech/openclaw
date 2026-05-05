"""Ratchet Loop crash recovery — .autorun_state marker file protocol.

Problem: If the ratchet loop crashes between commit and evaluation, git
history is left in a dirty state (committed but unevaluated). On restart,
step 1 cannot distinguish "normal commit awaiting evaluation" from
"crash residue".

Solution: Write .autorun_state marker before each evaluation, containing
the commit hash. On startup, detect stale markers and recover.

Protocol:
    START → write state{commit,step=evaluating,timestamp}
    EVALUATE → run eval_cmd
    DECIDE → keep/discard → clear state
    CRASH → state persists → next startup detects stale → auto --amend/reset
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

AUTORUN_STATE_FILE = ".autorun_state"


@dataclass
class AutoRunState:
    commit_hash: str
    step: str
    timestamp: float = field(default_factory=time.time)
    target_file: str = ""
    iteration: int = 0

    @property
    def is_stale(self) -> bool:
        return (time.time() - self.timestamp) > 300

    @property
    def is_evaluating(self) -> bool:
        return self.step == "evaluating"


def write_state(state: AutoRunState, workdir: str | Path = ".") -> Path:
    path = Path(workdir) / AUTORUN_STATE_FILE
    path.write_text(json.dumps({
        "commit_hash": state.commit_hash,
        "step": state.step,
        "timestamp": state.timestamp,
        "target_file": state.target_file,
        "iteration": state.iteration,
    }, indent=2))
    logger.debug(f"autorun_state written: commit={state.commit_hash[:7]} step={state.step}")
    return path


def read_state(workdir: str | Path = ".") -> AutoRunState | None:
    path = Path(workdir) / AUTORUN_STATE_FILE
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return AutoRunState(
            commit_hash=data.get("commit_hash", ""),
            step=data.get("step", "unknown"),
            timestamp=data.get("timestamp", 0.0),
            target_file=data.get("target_file", ""),
            iteration=data.get("iteration", 0),
        )
    except (json.JSONDecodeError, OSError):
        return None


def clear_state(workdir: str | Path = ".") -> None:
    path = Path(workdir) / AUTORUN_STATE_FILE
    if path.exists():
        path.unlink()
        logger.debug("autorun_state cleared")


def detect_and_recover(workdir: str | Path = ".") -> str | None:
    """Detect stale autorun state and attempt recovery.

    Returns a human-readable recovery message, or None if no recovery needed.
    """
    state = read_state(workdir)
    if state is None:
        return None
    if not state.is_stale:
        return None

    wd = Path(workdir)
    if state.is_evaluating:
        msg = (
            f"Crash recovery: stale autorun_state detected "
            f"(commit={state.commit_hash[:7]}, step={state.step}, "
            f"age={time.time() - state.timestamp:.0f}s). "
            f"Attempting to complete evaluation..."
        )
        logger.warning(msg)
        if _git_commit_exists(state.commit_hash, wd):
            result = _complete_evaluation(state, wd)
            msg += f" Result: {result}"
        else:
            msg += " Commit no longer exists, skipping."
        clear_state(workdir)
        return msg

    clear_state(workdir)
    return f"Cleaned up stale autorun_state (step={state.step})"


def get_current_commit(workdir: str | Path = ".") -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(workdir), timeout=5,
        )
        return proc.stdout.strip() if proc.returncode == 0 else ""
    except Exception:
        return ""


def _git_commit_exists(commit_hash: str, workdir: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "cat-file", "-e", commit_hash],
            capture_output=True, cwd=str(workdir), timeout=5,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _complete_evaluation(state: AutoRunState, workdir: Path) -> str:
    proc = subprocess.run(
        ["git", "reset", "--soft", "HEAD~1"],
        capture_output=True, text=True, cwd=str(workdir), timeout=10,
    )
    if proc.returncode == 0:
        return "uncommitted (git reset --soft HEAD~1) for re-evaluation"
    return f"reset failed: {proc.stderr.strip()}"
