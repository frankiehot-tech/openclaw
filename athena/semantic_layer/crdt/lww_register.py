from __future__ import annotations

from typing import Any


class LWWRegister:
    """Last-Writer-Wins Register — 用于跨Agent的事实同步。

    当多个Agent并发更新同一key时，时间戳大的胜出。
    时间戳平局时，source_agent_id 字典序大的胜出（确定性）。
    """

    def __init__(self, key: str):
        self.key = key
        self.value: Any = None
        self.timestamp: float = 0.0
        self.source_agent: str = ""

    def set(self, value: Any, timestamp: float, source_agent: str) -> bool:
        if timestamp > self.timestamp or (
            timestamp == self.timestamp and source_agent > self.source_agent
        ):
            self.value = value
            self.timestamp = timestamp
            self.source_agent = source_agent
            return True
        return False

    def get(self) -> Any:
        return self.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp,
            "source_agent": self.source_agent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LWWRegister:
        reg = cls(data["key"])
        reg.value = data["value"]
        reg.timestamp = data["timestamp"]
        reg.source_agent = data["source_agent"]
        return reg


class LWWRegisterStore:
    """多个 LWW-Register 的集合，用于跨Agent共享事实管理。"""

    def __init__(self):
        self._registers: dict[str, LWWRegister] = {}

    def set(self, key: str, value: Any, timestamp: float, source_agent: str) -> bool:
        if key not in self._registers:
            self._registers[key] = LWWRegister(key)
        return self._registers[key].set(value, timestamp, source_agent)

    def get(self, key: str) -> Any:
        reg = self._registers.get(key)
        return reg.value if reg else None

    def merge_remote(self, remote: dict[str, dict[str, Any]]) -> int:
        updated = 0
        for key, reg_data in remote.items():
            changed = self.set(
                key,
                reg_data["value"],
                reg_data["timestamp"],
                reg_data["source_agent"],
            )
            if changed:
                updated += 1
        return updated

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {key: reg.to_dict() for key, reg in self._registers.items() if reg.value is not None}

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, Any]]) -> LWWRegisterStore:
        store = cls()
        for key, reg_data in data.items():
            store._registers[key] = LWWRegister.from_dict(reg_data)
        return store

    @property
    def size(self) -> int:
        return len(self._registers)
