from __future__ import annotations

from typing import Any


class TwoPhaseSet:
    """Two-Phase Set — 用于跨Agent约束集的同步。

    分为 Added 和 Removed 两个集合。先添加，后移除。
    并发移除不会因并发添加而逆转为恢复（移除的优先级高于添加）。
    适用于：全局约束规则集、安全策略列表、黑名单/白名单。
    """

    def __init__(self):
        self._added: set[str] = set()
        self._removed: set[str] = set()

    def add(self, item: str) -> bool:
        if item in self._removed:
            return False
        self._added.add(item)
        return True

    def remove(self, item: str) -> bool:
        self._removed.add(item)
        self._added.discard(item)
        return True

    def contains(self, item: str) -> bool:
        return item in self._added and item not in self._removed

    def get_all(self) -> list[str]:
        return list(self._added - self._removed)

    def merge(self, remote: TwoPhaseSet) -> int:
        added_count = 0
        for item in remote._added:
            if item not in self._added and item not in self._removed:
                self._added.add(item)
                added_count += 1
        for item in remote._removed:
            if item not in self._removed:
                self._removed.add(item)
                self._added.discard(item)
        return added_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "added": list(self._added),
            "removed": list(self._removed),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TwoPhaseSet:
        s = cls()
        s._added = set(data.get("added", []))
        s._removed = set(data.get("removed", []))
        return s

    def __len__(self) -> int:
        return len(self._added - self._removed)
