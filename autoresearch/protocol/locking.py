"""Men0 Protocol v2 — flock-based file locking for agent coordination.

Uses POSIX flock (or Windows msvcrt) for cross-agent mutual exclusion.
Replaces network-based lock management with file-system locks.
"""

from __future__ import annotations

import fcntl
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)

LOCK_DIR = Path.home() / ".openclaw" / "locks"


def _ensure_lock_dir() -> None:
    LOCK_DIR.mkdir(parents=True, exist_ok=True)


def _lock_path(resource_id: str) -> Path:
    _ensure_lock_dir()
    safe_name = resource_id.replace("/", "_").replace(":", "_")
    return LOCK_DIR / f"{safe_name}.lock"


@contextmanager
def file_lock(resource_id: str, timeout_seconds: float = 30.0) -> Iterator[bool]:
    """Acquire an exclusive file lock for the given resource.

    Returns True if lock acquired, False on timeout.
    """
    path = _lock_path(resource_id)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    deadline = time.time() + timeout_seconds
    acquired = False
    try:
        while time.time() < deadline:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except (BlockingIOError, OSError):
                time.sleep(0.1)
        yield acquired
    finally:
        if acquired:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


class LockManager:
    """Manages multiple file locks for agent coordination."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._held: list[str] = []
        self._fds: dict[str, int] = {}

    def acquire(self, resource_id: str, timeout: float = 30.0) -> bool:
        path = _lock_path(resource_id)
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._held.append(resource_id)
                self._fds[resource_id] = fd
                return True
            except (BlockingIOError, OSError):
                time.sleep(0.1)
        os.close(fd)
        return False

    def release(self, resource_id: str) -> None:
        fd = self._fds.pop(resource_id, None)
        if fd:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        if resource_id in self._held:
            self._held.remove(resource_id)

    def release_all(self) -> None:
        for resource_id in list(self._held):
            self.release(resource_id)

    @property
    def held_locks(self) -> list[str]:
        return list(self._held)
