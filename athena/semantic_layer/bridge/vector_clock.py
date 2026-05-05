from __future__ import annotations

from typing import Any


class LamportClock:
    """单调递增逻辑时钟，用于对并发事件进行偏序排序。"""

    def __init__(self, initial: int = 0):
        self._time = initial

    def tick(self) -> int:
        self._time += 1
        return self._time

    def witness(self, received_time: int) -> int:
        self._time = max(self._time, received_time) + 1
        return self._time

    @property
    def time(self) -> int:
        return self._time


class VectorClock:
    """分布式向量时钟，用于检测并发冲突和因果关系。"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._clock: dict[str, int] = {agent_id: 0}

    def tick(self) -> dict[str, int]:
        self._clock[self.agent_id] = self._clock.get(self.agent_id, 0) + 1
        return dict(self._clock)

    def merge(self, remote: dict[str, int]) -> dict[str, int]:
        for agent, counter in remote.items():
            self._clock[agent] = max(self._clock.get(agent, 0), counter)
        self._clock[self.agent_id] = self._clock.get(self.agent_id, 0) + 1
        return dict(self._clock)

    def is_concurrent_with(self, remote: dict[str, int]) -> bool:
        """两个事件是并发的（没有因果 → 前后关系）。"""
        local_gt = any(
            self._clock.get(a, 0) > remote.get(a, 0)
            for a in set(self._clock) | set(remote)
        )
        remote_gt = any(
            remote.get(a, 0) > self._clock.get(a, 0)
            for a in set(self._clock) | set(remote)
        )
        return local_gt and remote_gt

    def happened_before(self, remote: dict[str, int]) -> bool:
        return all(
            self._clock.get(a, 0) <= remote.get(a, 0)
            for a in self._clock
        )

    @property
    def snapshot(self) -> dict[str, int]:
        return dict(self._clock)

    def to_dict(self) -> dict[str, Any]:
        return {"agent_id": self.agent_id, "clock": dict(self._clock)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VectorClock:
        vc = cls(data["agent_id"])
        vc._clock = dict(data["clock"])
        return vc
