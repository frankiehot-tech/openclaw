from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4


class ORSet:
    """Observed-Remove Set — 用于跨Agent意图队列。

    每个元素有唯一标识符，移除操作不会因并发添加而被逆转为恢复。
    适用于：意图委托队列、待办列表、分布式任务分配。
    """

    def __init__(self):
        self._elements: dict[str, _ORElement] = {}
        self._tombstones: set[str] = set()

    def add(self, item: Any, element_id: str = "") -> str:
        eid = element_id or str(uuid4())
        self._elements[eid] = _ORElement(id=eid, value=item)
        self._tombstones.discard(eid)
        return eid

    def remove(self, element_id: str) -> bool:
        if element_id in self._elements:
            del self._elements[element_id]
            self._tombstones.add(element_id)
            return True
        return False

    def contains(self, element_id: str) -> bool:
        return element_id in self._elements

    def get_all(self) -> list[dict[str, Any]]:
        return [
            {"id": elem.id, "value": elem.value, "added_by": elem.added_by, "timestamp": elem.timestamp}
            for elem in self._elements.values()
        ]

    def merge(self, remote: ORSet) -> int:
        added = 0
        for eid, elem in remote._elements.items():
            if eid not in self._tombstones and eid not in self._elements:
                self._elements[eid] = elem
                added += 1
        for eid in remote._tombstones:
            if eid not in self._tombstones:
                self._elements.pop(eid, None)
                self._tombstones.add(eid)
        return added

    def to_dict(self) -> dict[str, Any]:
        return {
            "elements": {eid: elem.to_dict() for eid, elem in self._elements.items()},
            "tombstones": list(self._tombstones),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ORSet:
        s = cls()
        for eid, elem_data in data.get("elements", {}).items():
            s._elements[eid] = _ORElement.from_dict(elem_data)
        s._tombstones = set(data.get("tombstones", []))
        return s

    def __len__(self) -> int:
        return len(self._elements)


@dataclass
class _ORElement:
    id: str
    value: Any
    added_by: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "value": self.value,
            "added_by": self.added_by,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> _ORElement:
        return cls(**data)
