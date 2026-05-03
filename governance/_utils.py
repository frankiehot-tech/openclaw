from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


def atomic_write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.replace(str(tmp), str(path))


def load_json_safe(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


try:
    import fcntl

    class FileLock:
        def __init__(self, lock_path: Path) -> None:
            self.lock_path = lock_path
            self.fd: int | None = None

        def __enter__(self) -> FileLock:
            self.fd = os.open(str(self.lock_path), os.O_WRONLY | os.O_CREAT)
            fcntl.flock(self.fd, fcntl.LOCK_EX)
            return self

        def __exit__(self, *args: object) -> None:
            if self.fd is not None:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                os.close(self.fd)
                self.fd = None

except ImportError:
    class FileLock:
        def __init__(self, lock_path: Path) -> None:
            self.lock_path = lock_path

        def __enter__(self) -> FileLock:
            return self

        def __exit__(self, *args: object) -> None:
            pass
