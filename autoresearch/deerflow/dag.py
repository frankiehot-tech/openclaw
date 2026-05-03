"""DeerFlow v2 — Plan-and-Execute DAG engine.

Nodes represent work units, edges represent dependencies.
Supports parallel execution of independent nodes.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    PENDING = auto()
    READY = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()
    BLOCKED = auto()


@dataclass
class DAGNode:
    node_id: str
    name: str
    action: Callable | None = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: str = ""
    started: float = 0.0
    finished: float = 0.0
    retries: int = 0
    max_retries: int = 1
    cost_estimate: float = 0.0
    priority: int = 0

    @property
    def duration(self) -> float:
        if self.finished and self.started:
            return self.finished - self.started
        return 0.0

    @property
    def ready(self) -> bool:
        return self.status == NodeStatus.READY


class DAGEngine:
    """DAG execution engine with dependency resolution and parallel execution."""

    def __init__(self, max_parallel: int = 4) -> None:
        self.max_parallel = max_parallel
        self._nodes: dict[str, DAGNode] = {}
        self._execution_order: list[str] = []
        self._started: float = 0.0

    def add_node(self, node: DAGNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, from_node: str, to_node: str) -> None:
        if to_node not in self._nodes:
            return
        self._nodes[to_node].depends_on.append(from_node)

    def execute(self) -> dict[str, Any]:
        self._started = time.time()
        results: dict[str, Any] = {}

        while not self._is_complete():
            ready = self._get_ready_nodes()
            if not ready and self._has_running():
                time.sleep(0.1)
                continue
            if not ready and not self._has_running():
                stuck = self._get_stuck_nodes()
                if stuck:
                    logger.error(f"DAG stuck: {[n.node_id for n in stuck]}")
                    break
                break

            for node in ready[:self.max_parallel - self._count_running()]:
                self._execute_node(node)

        for node_id, node in self._nodes.items():
            results[node_id] = {
                "status": node.status.name,
                "result": str(node.result)[:200] if node.result else None,
                "error": node.error,
                "duration": round(node.duration, 3),
            }

        return {
            "status": "completed" if all(n.status in (NodeStatus.COMPLETED, NodeStatus.SKIPPED) for n in self._nodes.values()) else "failed",
            "total_duration": round(time.time() - self._started, 3),
            "nodes": results,
            "execution_order": self._execution_order,
        }

    def _execute_node(self, node: DAGNode) -> None:
        node.status = NodeStatus.RUNNING
        node.started = time.time()
        self._execution_order.append(node.node_id)

        try:
            if node.action:
                node.result = node.action(*node.args, **node.kwargs)
            node.status = NodeStatus.COMPLETED
        except Exception as e:
            node.error = str(e)
            if node.retries < node.max_retries:
                node.retries += 1
                node.status = NodeStatus.READY
                logger.warning(f"Retry {node.node_id} ({node.retries}/{node.max_retries}): {e}")
            else:
                node.status = NodeStatus.FAILED
                logger.error(f"Node {node.node_id} failed: {e}")
        finally:
            node.finished = time.time()

    def _get_ready_nodes(self) -> list[DAGNode]:
        ready: list[DAGNode] = []
        for node in self._nodes.values():
            if node.status != NodeStatus.PENDING:
                continue
            deps_completed = all(
                self._nodes[dep].status == NodeStatus.COMPLETED
                for dep in node.depends_on
                if dep in self._nodes
            )
            if deps_completed:
                node.status = NodeStatus.READY
                ready.append(node)
        ready.sort(key=lambda n: (-n.priority, n.cost_estimate))
        return ready

    def _has_running(self) -> bool:
        return self._count_running() > 0

    def _count_running(self) -> int:
        return sum(1 for n in self._nodes.values() if n.status == NodeStatus.RUNNING)

    def _get_stuck_nodes(self) -> list[DAGNode]:
        stuck: list[DAGNode] = []
        for node in self._nodes.values():
            if node.status != NodeStatus.PENDING:
                continue
            for dep in node.depends_on:
                if dep in self._nodes and self._nodes[dep].status == NodeStatus.FAILED:
                    node.status = NodeStatus.BLOCKED
                    stuck.append(node)
                    break
        return stuck

    def _is_complete(self) -> bool:
        return all(
            n.status in (NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED, NodeStatus.BLOCKED)
            for n in self._nodes.values()
        )

    def reset(self) -> None:
        for node in self._nodes.values():
            node.status = NodeStatus.PENDING
            node.result = None
            node.error = ""
            node.started = 0.0
            node.finished = 0.0
        self._execution_order.clear()
