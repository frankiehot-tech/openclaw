#!/usr/bin/env python3
"""
Worker Health Tracker - Worker 健康状态跟踪器

跟踪 worker 的心跳、任务执行状态、负载，维护健康评分。
提供健康状态查询和故障检测。
"""

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .health_contract import (
    HealthDimension,
    HealthMetric,
    HealthScoringEngine,
    WorkerHealthScore,
    WorkerHealthStatus,
    get_health_scoring_engine,
)


@dataclass
class WorkerInfo:
    """Worker 基本信息"""

    worker_id: str
    role: str
    host: str = "localhost"
    pid: Optional[int] = None
    started_at: float = field(default_factory=time.time)

    # 健康状态
    health_score: Optional[WorkerHealthScore] = None

    # 最后一次心跳
    last_heartbeat_at: Optional[float] = None

    # 任务统计
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0

    # 当前负载
    current_load: int = 0  # 当前运行中的任务数
    max_capacity: int = 1  # 最大并发任务数

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 1.0
        return self.successful_tasks / self.total_tasks

    @property
    def is_alive(self) -> bool:
        """是否存活（基于心跳）"""
        if self.last_heartbeat_at is None:
            return False
        # 心跳超时 5 分钟视为死亡
        return (time.time() - self.last_heartbeat_at) < 300

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "role": self.role,
            "host": self.host,
            "pid": self.pid,
            "started_at": self.started_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "is_alive": self.is_alive,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.success_rate,
            "current_load": self.current_load,
            "max_capacity": self.max_capacity,
            "load_ratio": self.current_load / self.max_capacity if self.max_capacity > 0 else 0.0,
            "health_score": self.health_score.to_dict() if self.health_score else None,
            "metadata": self.metadata,
        }


class WorkerHealthTracker:
    """Worker 健康状态跟踪器"""

    def __init__(self, scoring_engine: Optional[HealthScoringEngine] = None):
        self.scoring_engine = scoring_engine or get_health_scoring_engine()
        self.workers: Dict[str, WorkerInfo] = {}
        self.lock = threading.RLock()

        # 配置
        self.heartbeat_timeout = 300  # 心跳超时 5 分钟
        self.health_update_interval = 30  # 健康评分更新间隔 30 秒

        # 历史记录
        self.health_history: Dict[str, List[WorkerHealthScore]] = {}

        # 最后更新
        self.last_health_update = 0.0

    def register_worker(
        self,
        worker_id: str,
        role: str,
        host: str = "localhost",
        pid: Optional[int] = None,
        max_capacity: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkerInfo:
        """注册新 worker"""
        with self.lock:
            if worker_id in self.workers:
                # 已存在，更新信息
                worker = self.workers[worker_id]
                worker.role = role
                worker.host = host
                worker.pid = pid
                worker.max_capacity = max_capacity
                if metadata:
                    worker.metadata.update(metadata)
                return worker

            # 创建新 worker
            worker = WorkerInfo(
                worker_id=worker_id,
                role=role,
                host=host,
                pid=pid,
                max_capacity=max_capacity,
                metadata=metadata or {},
            )
            self.workers[worker_id] = worker
            self.health_history[worker_id] = []

            # 立即更新健康评分
            self._update_worker_health(worker_id)

            return worker

    def record_heartbeat(
        self,
        worker_id: str,
        current_load: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """记录心跳"""
        with self.lock:
            if worker_id not in self.workers:
                # 自动注册未知 worker
                self.register_worker(
                    worker_id=worker_id,
                    role="unknown",
                    metadata={"auto_registered": True},
                )

            worker = self.workers[worker_id]
            worker.last_heartbeat_at = time.time()

            if current_load is not None:
                worker.current_load = current_load

            if metadata:
                worker.metadata.update(metadata)

            # 触发健康评分更新
            self._update_worker_health(worker_id)

            return True

    def record_task_start(self, worker_id: str, task_id: str) -> bool:
        """记录任务开始"""
        with self.lock:
            if worker_id not in self.workers:
                return False

            worker = self.workers[worker_id]
            worker.current_load += 1
            return True

    def record_task_completion(
        self,
        worker_id: str,
        task_id: str,
        success: bool,
        execution_time_ms: Optional[float] = None,
    ) -> bool:
        """记录任务完成"""
        with self.lock:
            if worker_id not in self.workers:
                return False

            worker = self.workers[worker_id]
            worker.total_tasks += 1

            if success:
                worker.successful_tasks += 1
                # 记录最后成功时间（通过 metadata）
                worker.metadata["last_success_at"] = time.time()
            else:
                worker.failed_tasks += 1
                worker.metadata["last_failure_at"] = time.time()

            # 减少负载
            worker.current_load = max(0, worker.current_load - 1)

            # 更新健康评分
            self._update_worker_health(worker_id)

            return True

    def get_worker_health(self, worker_id: str) -> Optional[WorkerHealthScore]:
        """获取 worker 健康评分"""
        with self.lock:
            if worker_id not in self.workers:
                return None

            worker = self.workers[worker_id]
            return worker.health_score

    def get_healthy_workers(
        self,
        role: Optional[str] = None,
        min_score: float = 0.7,
        max_load_ratio: float = 0.8,
    ) -> List[Tuple[str, WorkerHealthScore]]:
        """获取健康的 worker 列表"""
        with self.lock:
            results = []

            for worker_id, worker in self.workers.items():
                # 角色过滤
                if role and worker.role != role:
                    continue

                # 健康评分过滤
                if not worker.health_score:
                    continue

                if worker.health_score.overall_score < min_score:
                    continue

                # 负载过滤
                load_ratio = (
                    worker.current_load / worker.max_capacity if worker.max_capacity > 0 else 0.0
                )
                if load_ratio > max_load_ratio:
                    continue

                # 心跳检查
                if not worker.is_alive:
                    continue

                results.append((worker_id, worker.health_score))

            # 按健康评分排序（降序）
            results.sort(key=lambda x: x[1].overall_score, reverse=True)
            return results

    def get_worker_status_summary(self) -> Dict[str, Any]:
        """获取所有 worker 状态摘要"""
        with self.lock:
            summary = {
                "total_workers": len(self.workers),
                "alive_workers": 0,
                "healthy_workers": 0,
                "degraded_workers": 0,
                "unavailable_workers": 0,
                "workers_by_role": {},
                "timestamp": time.time(),
            }

            for worker_id, worker in self.workers.items():
                role = worker.role
                if role not in summary["workers_by_role"]:
                    summary["workers_by_role"][role] = {
                        "total": 0,
                        "alive": 0,
                        "healthy": 0,
                        "degraded": 0,
                        "unavailable": 0,
                    }

                role_stats = summary["workers_by_role"][role]
                role_stats["total"] += 1

                if worker.is_alive:
                    summary["alive_workers"] += 1
                    role_stats["alive"] += 1

                if worker.health_score:
                    status = worker.health_score.overall_status
                    if status == WorkerHealthStatus.HEALTHY:
                        summary["healthy_workers"] += 1
                        role_stats["healthy"] += 1
                    elif status == WorkerHealthStatus.DEGRADED:
                        summary["degraded_workers"] += 1
                        role_stats["degraded"] += 1
                    elif status == WorkerHealthStatus.UNAVAILABLE:
                        summary["unavailable_workers"] += 1
                        role_stats["unavailable"] += 1

            return summary

    def cleanup_stale_workers(self, max_age_seconds: int = 3600) -> List[str]:
        """清理长时间无心跳的 worker"""
        with self.lock:
            removed = []
            current_time = time.time()

            for worker_id, worker in list(self.workers.items()):
                if worker.last_heartbeat_at is None:
                    # 从未心跳，但注册时间超过阈值
                    if current_time - worker.started_at > max_age_seconds:
                        removed.append(worker_id)
                        del self.workers[worker_id]
                        if worker_id in self.health_history:
                            del self.health_history[worker_id]
                else:
                    # 心跳超时
                    if current_time - worker.last_heartbeat_at > max_age_seconds:
                        removed.append(worker_id)
                        del self.workers[worker_id]
                        if worker_id in self.health_history:
                            del self.health_history[worker_id]

            return removed

    def _update_worker_health(self, worker_id: str) -> None:
        """更新 worker 健康评分"""
        with self.lock:
            if worker_id not in self.workers:
                return

            worker = self.workers[worker_id]

            # 准备指标
            metrics = []

            # 1. 可用性指标（基于心跳）
            if worker.last_heartbeat_at:
                heartbeat_age = time.time() - worker.last_heartbeat_at
                # 心跳越新鲜值越高
                freshness = max(0.0, 1.0 - (heartbeat_age / self.heartbeat_timeout))
                metrics.append(
                    HealthMetric(
                        dimension=HealthDimension.HEARTBEAT_FRESHNESS,
                        value=freshness,
                        timestamp=time.time(),
                    )
                )

            # 2. 成功率指标
            success_rate = worker.success_rate
            metrics.append(
                HealthMetric(
                    dimension=HealthDimension.SUCCESS_RATE,
                    value=success_rate,
                    timestamp=time.time(),
                )
            )

            # 3. 负载指标
            load_ratio = (
                worker.current_load / worker.max_capacity if worker.max_capacity > 0 else 0.0
            )
            # 负载越低值越高
            load_value = 1.0 - min(load_ratio, 1.0)
            metrics.append(
                HealthMetric(
                    dimension=HealthDimension.LOAD,
                    value=load_value,
                    timestamp=time.time(),
                )
            )

            # 4. 延迟指标（默认为最佳）
            metrics.append(
                HealthMetric(
                    dimension=HealthDimension.LATENCY,
                    value=1.0,  # 默认最佳
                    timestamp=time.time(),
                )
            )

            # 5. 可用性指标（基于存活状态）
            availability = 1.0 if worker.is_alive else 0.0
            metrics.append(
                HealthMetric(
                    dimension=HealthDimension.AVAILABILITY,
                    value=availability,
                    timestamp=time.time(),
                )
            )

            # 计算健康评分
            health_score = self.scoring_engine.calculate_health_score(
                worker_id=worker_id,
                role=worker.role,
                metrics=metrics,
                last_heartbeat_at=worker.last_heartbeat_at,
                total_tasks=worker.total_tasks,
                successful_tasks=worker.successful_tasks,
                current_load=worker.current_load,
                max_capacity=worker.max_capacity,
                metadata=worker.metadata,
            )

            worker.health_score = health_score

            # 保存历史记录（保留最近100条）
            if worker_id not in self.health_history:
                self.health_history[worker_id] = []

            self.health_history[worker_id].append(health_score)
            if len(self.health_history[worker_id]) > 100:
                self.health_history[worker_id] = self.health_history[worker_id][-100:]

    def update_all_workers_health(self) -> None:
        """更新所有 worker 的健康评分"""
        with self.lock:
            for worker_id in list(self.workers.keys()):
                self._update_worker_health(worker_id)
            self.last_health_update = time.time()


# 全局健康跟踪器实例
_global_tracker: Optional[WorkerHealthTracker] = None


def get_global_health_tracker() -> WorkerHealthTracker:
    """获取全局健康跟踪器实例"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = WorkerHealthTracker()
    return _global_tracker
