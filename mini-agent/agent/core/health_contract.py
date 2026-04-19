#!/usr/bin/env python3
"""
Agent/Worker Health Contract - 健康评分契约

定义 agent/worker 健康评分字段、状态分类和评分算法。
至少支持活跃度、最近 heartbeat、失败率、可用性等评分维度。
区分 healthy / degraded / unavailable 状态。
"""

import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class WorkerHealthStatus(Enum):
    """Worker 健康状态枚举"""

    HEALTHY = "healthy"  # 健康：可正常接受任务
    DEGRADED = "degraded"  # 降级：部分能力受损，可接受轻量任务
    UNAVAILABLE = "unavailable"  # 不可用：不应接受任务
    UNKNOWN = "unknown"  # 未知：无足够数据


class HealthDimension(Enum):
    """健康维度"""

    AVAILABILITY = "availability"  # 可用性：是否在线可响应
    LATENCY = "latency"  # 延迟：响应时间
    SUCCESS_RATE = "success_rate"  # 成功率：任务成功比例
    HEARTBEAT_FRESHNESS = "heartbeat_freshness"  # 心跳新鲜度
    LOAD = "load"  # 负载：当前任务数/资源使用


@dataclass
class HealthMetric:
    """健康指标"""

    dimension: HealthDimension
    value: float  # 归一化值 0-1，1 表示最好
    weight: float = 1.0  # 权重
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkerHealthScore:
    """Worker 健康评分"""

    worker_id: str
    role: str  # 角色类型：build_worker, researcher, reviewer 等
    overall_status: WorkerHealthStatus
    overall_score: float  # 综合评分 0-1

    # 各维度指标
    metrics: Dict[HealthDimension, HealthMetric]

    # 关键数据点
    last_heartbeat_at: Optional[float] = None
    last_success_at: Optional[float] = None
    last_failure_at: Optional[float] = None

    # 统计
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0

    # 负载信息
    current_load: int = 0  # 当前运行中的任务数
    max_capacity: int = 1  # 最大容量

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "worker_id": self.worker_id,
            "role": self.role,
            "overall_status": self.overall_status.value,
            "overall_score": self.overall_score,
            "metrics": {
                dim.value: {
                    "value": metric.value,
                    "weight": metric.weight,
                    "timestamp": metric.timestamp,
                }
                for dim, metric in self.metrics.items()
            },
            "last_heartbeat_at": self.last_heartbeat_at,
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.success_rate,
            "current_load": self.current_load,
            "max_capacity": self.max_capacity,
            "load_ratio": self.load_ratio,
            "metadata": self.metadata,
        }

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_tasks == 0:
            return 1.0
        return self.successful_tasks / self.total_tasks

    @property
    def load_ratio(self) -> float:
        """计算负载率"""
        if self.max_capacity == 0:
            return 0.0
        return self.current_load / self.max_capacity

    @property
    def is_overloaded(self) -> bool:
        """是否过载"""
        return self.load_ratio >= 0.8

    @property
    def heartbeat_age_seconds(self) -> Optional[float]:
        """心跳年龄（秒）"""
        if self.last_heartbeat_at is None:
            return None
        return time.time() - self.last_heartbeat_at


class HealthScoringEngine:
    """健康评分引擎"""

    def __init__(self):
        # 默认权重配置
        self.weights = {
            HealthDimension.AVAILABILITY: 0.3,
            HealthDimension.SUCCESS_RATE: 0.25,
            HealthDimension.HEARTBEAT_FRESHNESS: 0.2,
            HealthDimension.LOAD: 0.15,
            HealthDimension.LATENCY: 0.1,
        }

        # 阈值配置
        self.thresholds = {
            WorkerHealthStatus.HEALTHY: 0.7,
            WorkerHealthStatus.DEGRADED: 0.3,
            # 低于 0.3 为 UNAVAILABLE
        }

        # 心跳超时（秒）
        self.heartbeat_timeout = 300  # 5分钟

    def calculate_health_score(
        self,
        worker_id: str,
        role: str,
        metrics: List[HealthMetric],
        last_heartbeat_at: Optional[float] = None,
        total_tasks: int = 0,
        successful_tasks: int = 0,
        current_load: int = 0,
        max_capacity: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkerHealthScore:
        """
        计算健康评分

        Args:
            worker_id: Worker ID
            role: 角色
            metrics: 健康指标列表
            last_heartbeat_at: 最后心跳时间戳
            total_tasks: 总任务数
            successful_tasks: 成功任务数
            current_load: 当前负载
            max_capacity: 最大容量
            metadata: 元数据

        Returns:
            WorkerHealthScore 对象
        """
        # 组织指标
        metric_dict = {}
        for metric in metrics:
            metric_dict[metric.dimension] = metric

        # 确保所有维度都有指标（缺失则使用默认值）
        for dimension in self.weights:
            if dimension not in metric_dict:
                # 默认值：未知维度设为 0.5
                metric_dict[dimension] = HealthMetric(
                    dimension=dimension,
                    value=0.5,
                    weight=self.weights[dimension],
                )

        # 计算加权综合评分
        weighted_sum = 0.0
        total_weight = 0.0

        for dimension, metric in metric_dict.items():
            weight = self.weights.get(dimension, 1.0)
            weighted_sum += metric.value * weight
            total_weight += weight

        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        # 应用特殊规则
        # 1. 心跳超时直接降级
        if last_heartbeat_at:
            heartbeat_age = time.time() - last_heartbeat_at
            if heartbeat_age > self.heartbeat_timeout:
                overall_score = min(overall_score, 0.4)  # 最高为 degraded

        # 2. 过载惩罚
        load_ratio = current_load / max_capacity if max_capacity > 0 else 0.0
        if load_ratio > 0.9:
            overall_score *= 0.7  # 重度过载惩罚
        elif load_ratio > 0.7:
            overall_score *= 0.85  # 中度过载惩罚

        # 确定状态
        overall_status = self._determine_status(overall_score)

        # 创建健康评分对象
        score = WorkerHealthScore(
            worker_id=worker_id,
            role=role,
            overall_status=overall_status,
            overall_score=overall_score,
            metrics=metric_dict,
            last_heartbeat_at=last_heartbeat_at,
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=total_tasks - successful_tasks,
            current_load=current_load,
            max_capacity=max_capacity,
            metadata=metadata or {},
        )

        return score

    def _determine_status(self, score: float) -> WorkerHealthStatus:
        """根据评分确定状态"""
        if score >= self.thresholds[WorkerHealthStatus.HEALTHY]:
            return WorkerHealthStatus.HEALTHY
        elif score >= self.thresholds[WorkerHealthStatus.DEGRADED]:
            return WorkerHealthStatus.DEGRADED
        else:
            return WorkerHealthStatus.UNAVAILABLE

    def create_default_metrics(
        self,
        availability: float = 1.0,
        success_rate: float = 1.0,
        heartbeat_freshness: float = 1.0,
        load: float = 0.0,
        latency: float = 1.0,
    ) -> List[HealthMetric]:
        """创建默认指标集"""
        return [
            HealthMetric(
                dimension=HealthDimension.AVAILABILITY,
                value=availability,
                weight=self.weights[HealthDimension.AVAILABILITY],
            ),
            HealthMetric(
                dimension=HealthDimension.SUCCESS_RATE,
                value=success_rate,
                weight=self.weights[HealthDimension.SUCCESS_RATE],
            ),
            HealthMetric(
                dimension=HealthDimension.HEARTBEAT_FRESHNESS,
                value=heartbeat_freshness,
                weight=self.weights[HealthDimension.HEARTBEAT_FRESHNESS],
            ),
            HealthMetric(
                dimension=HealthDimension.LOAD,
                value=1.0 - min(load, 1.0),  # 负载越高值越低
                weight=self.weights[HealthDimension.LOAD],
            ),
            HealthMetric(
                dimension=HealthDimension.LATENCY,
                value=latency,
                weight=self.weights[HealthDimension.LATENCY],
            ),
        ]


# 全局健康评分引擎实例
_health_scoring_engine: Optional[HealthScoringEngine] = None


def get_health_scoring_engine() -> HealthScoringEngine:
    """获取全局健康评分引擎实例"""
    global _health_scoring_engine
    if _health_scoring_engine is None:
        _health_scoring_engine = HealthScoringEngine()
    return _health_scoring_engine
