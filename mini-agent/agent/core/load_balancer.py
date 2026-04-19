#!/usr/bin/env python3
"""
Load Balancer - 负载均衡调度选择器

基于健康评分、负载和故障转移规则选择最佳 worker。
提供调度决策和结构化故障转移证据。
"""

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .health_contract import HealthScoringEngine, get_health_scoring_engine
from .route_scoring import RouteScore, get_global_scoring_engine
from .worker_health_tracker import (
    WorkerHealthScore,
    WorkerHealthStatus,
    WorkerHealthTracker,
    get_global_health_tracker,
)


class SelectionStrategy(Enum):
    """选择策略"""

    HEALTH_FIRST = "health_first"  # 健康优先（最高评分）
    LOAD_AWARE = "load_aware"  # 负载感知（低负载优先）
    ROUND_ROBIN = "round_robin"  # 轮询
    RANDOM = "random"  # 随机
    HYBRID = "hybrid"  # 混合策略（健康+负载）
    ROUTE_SCORING = "route_scoring"  # 智能路由评分策略


class FailoverAction(Enum):
    """故障转移动作"""

    RETRY = "retry"  # 重试（相同worker）
    FALLBACK = "fallback"  # 降级（选择次优worker）
    SKIP = "skip"  # 跳过（标记失败）
    QUEUE = "queue"  # 重新排队


@dataclass
class SelectionCriteria:
    """选择标准"""

    role: Optional[str] = None  # 要求的角色
    min_health_score: float = 0.7  # 最低健康评分
    max_load_ratio: float = 0.8  # 最大负载率
    require_heartbeat: bool = True  # 要求有心跳
    strategy: SelectionStrategy = SelectionStrategy.HYBRID

    # 权重配置（用于混合策略）
    health_weight: float = 0.6
    load_weight: float = 0.3
    freshness_weight: float = 0.1

    # 特殊要求
    preferred_workers: List[str] = field(default_factory=list)  # 优先worker列表
    excluded_workers: List[str] = field(default_factory=list)  # 排除worker列表

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "min_health_score": self.min_health_score,
            "max_load_ratio": self.max_load_ratio,
            "require_heartbeat": self.require_heartbeat,
            "strategy": self.strategy.value,
            "health_weight": self.health_weight,
            "load_weight": self.load_weight,
            "freshness_weight": self.freshness_weight,
            "preferred_workers": self.preferred_workers,
            "excluded_workers": self.excluded_workers,
        }


@dataclass
class SelectionResult:
    """选择结果"""

    selected_worker_id: str
    worker_score: WorkerHealthScore
    selection_score: float  # 选择得分（0-1）

    # 候选信息
    candidates: List[Tuple[str, WorkerHealthScore, float]]  # (worker_id, score, selection_score)

    # 决策依据
    criteria: SelectionCriteria
    selection_reason: str

    # 元数据
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_worker_id": self.selected_worker_id,
            "worker_score": self.worker_score.to_dict(),
            "selection_score": self.selection_score,
            "candidates": [
                {
                    "worker_id": worker_id,
                    "health_score": score.to_dict(),
                    "selection_score": sel_score,
                }
                for worker_id, score, sel_score in self.candidates
            ],
            "criteria": self.criteria.to_dict(),
            "selection_reason": self.selection_reason,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class FailoverDecision:
    """故障转移决策"""

    original_worker_id: str
    failure_reason: str
    action: FailoverAction

    # 目标信息
    target_worker_id: Optional[str] = None

    # 决策依据
    decision_reason: str = ""

    # 结构化证据
    health_snapshot: Optional[Dict[str, Any]] = None
    load_snapshot: Optional[Dict[str, Any]] = None

    # 元数据
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_worker_id": self.original_worker_id,
            "failure_reason": self.failure_reason,
            "action": self.action.value,
            "target_worker_id": self.target_worker_id,
            "decision_reason": self.decision_reason,
            "health_snapshot": self.health_snapshot,
            "load_snapshot": self.load_snapshot,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class LoadBalancer:
    """负载均衡器"""

    def __init__(
        self,
        health_tracker: Optional[WorkerHealthTracker] = None,
        scoring_engine: Optional[HealthScoringEngine] = None,
    ):
        self.health_tracker = health_tracker or get_global_health_tracker()
        self.scoring_engine = scoring_engine or get_health_scoring_engine()

        # 故障转移策略配置
        self.failover_policies = {
            "unavailable": FailoverAction.FALLBACK,
            "overloaded": FailoverAction.FALLBACK,
            "heartbeat_timeout": FailoverAction.FALLBACK,
            "task_failure": FailoverAction.RETRY,
            "system_error": FailoverAction.SKIP,
        }

        # 重试配置
        self.max_retries = 3
        self.retry_delay_seconds = 5

        # 历史记录
        self.selection_history: List[SelectionResult] = []
        self.failover_history: List[FailoverDecision] = []

        # 轮询状态
        self.round_robin_index: Dict[str, int] = {}

    def select_worker(
        self,
        criteria: Optional[SelectionCriteria] = None,
    ) -> Optional[SelectionResult]:
        """
        选择最佳 worker

        Args:
            criteria: 选择标准

        Returns:
            SelectionResult 或 None（无可用worker）
        """
        if criteria is None:
            criteria = SelectionCriteria()

        # 获取符合条件的worker
        candidates = self._get_qualified_candidates(criteria)

        if not candidates:
            return None

        # 应用选择策略
        selected_worker_id, selection_score, reason = self._apply_selection_strategy(
            candidates, criteria
        )

        # 获取worker健康评分
        worker_score = self.health_tracker.get_worker_health(selected_worker_id)
        if not worker_score:
            # 不应发生，但安全处理
            return None

        # 创建选择结果
        result = SelectionResult(
            selected_worker_id=selected_worker_id,
            worker_score=worker_score,
            selection_score=selection_score,
            candidates=candidates,
            criteria=criteria,
            selection_reason=reason,
        )

        # 记录历史
        self.selection_history.append(result)
        if len(self.selection_history) > 100:
            self.selection_history = self.selection_history[-100:]

        return result

    def handle_failure(
        self,
        worker_id: str,
        failure_reason: str,
        task_id: Optional[str] = None,
        retry_count: int = 0,
    ) -> FailoverDecision:
        """
        处理 worker 故障

        Args:
            worker_id: 故障 worker ID
            failure_reason: 故障原因
            task_id: 相关任务ID（可选）
            retry_count: 当前重试次数

        Returns:
            故障转移决策
        """
        # 确定故障类型
        failure_type = self._classify_failure(failure_reason)

        # 获取故障worker的健康快照
        worker_score = self.health_tracker.get_worker_health(worker_id)
        health_snapshot = worker_score.to_dict() if worker_score else None

        # 获取负载快照
        load_snapshot = self._get_load_snapshot()

        # 应用故障转移策略
        action = self.failover_policies.get(failure_type, FailoverAction.SKIP)

        # 根据action调整
        target_worker_id = None
        decision_reason = f"故障类型: {failure_type}, 应用策略: {action.value}"

        if action == FailoverAction.RETRY:
            if retry_count >= self.max_retries:
                action = FailoverAction.FALLBACK
                decision_reason = f"超过最大重试次数 ({self.max_retries})，降级到 FALLBACK"
            else:
                target_worker_id = worker_id  # 重试相同worker
                decision_reason = f"重试 {retry_count + 1}/{self.max_retries}"

        elif action == FailoverAction.FALLBACK:
            # 寻找替代worker
            criteria = SelectionCriteria(
                excluded_workers=[worker_id],
                min_health_score=0.5,  # 降低要求
            )
            fallback_result = self.select_worker(criteria)

            if fallback_result:
                target_worker_id = fallback_result.selected_worker_id
                decision_reason += f", 降级到 worker: {target_worker_id}"
            else:
                # 无替代worker，转为SKIP
                action = FailoverAction.SKIP
                decision_reason += ", 无可用替代worker，转为SKIP"

        elif action == FailoverAction.SKIP:
            decision_reason += ", 跳过任务"

        elif action == FailoverAction.QUEUE:
            decision_reason += ", 重新排队"

        # 创建故障转移决策
        decision = FailoverDecision(
            original_worker_id=worker_id,
            failure_reason=failure_reason,
            action=action,
            target_worker_id=target_worker_id,
            decision_reason=decision_reason,
            health_snapshot=health_snapshot,
            load_snapshot=load_snapshot,
            metadata={
                "task_id": task_id,
                "retry_count": retry_count,
                "failure_type": failure_type,
            },
        )

        # 记录历史
        self.failover_history.append(decision)
        if len(self.failover_history) > 100:
            self.failover_history = self.failover_history[-100:]

        return decision

    def get_selection_stats(self) -> Dict[str, Any]:
        """获取选择统计"""
        if not self.selection_history:
            return {"total_selections": 0}

        total = len(self.selection_history)
        recent = self.selection_history[-20:] if total > 20 else self.selection_history

        # 按worker统计
        worker_counts: Dict[str, int] = {}
        for selection in recent:
            worker_id = selection.selected_worker_id
            worker_counts[worker_id] = worker_counts.get(worker_id, 0) + 1

        # 按策略统计
        strategy_counts: Dict[str, int] = {}
        for selection in recent:
            strategy = selection.criteria.strategy.value
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        return {
            "total_selections": total,
            "recent_selections": len(recent),
            "worker_distribution": worker_counts,
            "strategy_distribution": strategy_counts,
            "avg_selection_score": sum(s.selection_score for s in recent) / len(recent),
        }

    def get_failover_stats(self) -> Dict[str, Any]:
        """获取故障转移统计"""
        if not self.failover_history:
            return {"total_failovers": 0}

        total = len(self.failover_history)

        # 按action统计
        action_counts: Dict[str, int] = {}
        for decision in self.failover_history:
            action = decision.action.value
            action_counts[action] = action_counts.get(action, 0) + 1

        # 按failure_reason统计
        reason_counts: Dict[str, int] = {}
        for decision in self.failover_history:
            reason = decision.failure_reason
            # 截断长原因
            if len(reason) > 50:
                reason = reason[:47] + "..."
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        return {
            "total_failovers": total,
            "action_distribution": action_counts,
            "reason_distribution": reason_counts,
        }

    def _get_qualified_candidates(
        self,
        criteria: SelectionCriteria,
    ) -> List[Tuple[str, WorkerHealthScore, float]]:
        """获取符合条件的候选worker"""
        # 获取健康worker列表
        healthy_workers = self.health_tracker.get_healthy_workers(
            role=criteria.role,
            min_score=criteria.min_health_score,
            max_load_ratio=criteria.max_load_ratio,
        )

        # 应用排除列表
        candidates = []
        for worker_id, health_score in healthy_workers:
            if worker_id in criteria.excluded_workers:
                continue

            # 心跳要求
            if criteria.require_heartbeat and not self.health_tracker.workers[worker_id].is_alive:
                continue

            # 计算选择得分
            selection_score = self._calculate_selection_score(health_score, criteria)
            candidates.append((worker_id, health_score, selection_score))

        # 应用优先列表（提升优先级）
        if criteria.preferred_workers:
            # 重新排序，优先worker在前
            preferred = []
            others = []

            for candidate in candidates:
                worker_id, health_score, selection_score = candidate
                if worker_id in criteria.preferred_workers:
                    # 提升选择得分
                    boosted_score = min(1.0, selection_score * 1.2)
                    preferred.append((worker_id, health_score, boosted_score))
                else:
                    others.append(candidate)

            candidates = preferred + others

        return candidates

    def _calculate_selection_score(
        self,
        health_score: WorkerHealthScore,
        criteria: SelectionCriteria,
    ) -> float:
        """计算选择得分"""
        if criteria.strategy == SelectionStrategy.HEALTH_FIRST:
            return health_score.overall_score

        elif criteria.strategy == SelectionStrategy.LOAD_AWARE:
            # 负载越低得分越高
            load_score = 1.0 - health_score.load_ratio
            return load_score

        elif criteria.strategy == SelectionStrategy.ROUND_ROBIN:
            # 轮询策略不关心得分，返回固定值
            return 0.5

        elif criteria.strategy == SelectionStrategy.RANDOM:
            # 随机策略返回随机值
            return random.random()

        elif criteria.strategy == SelectionStrategy.HYBRID:
            # 混合策略：加权组合
            health_component = health_score.overall_score * criteria.health_weight
            load_component = (1.0 - health_score.load_ratio) * criteria.load_weight

            # 心跳新鲜度组件
            freshness_component = 0.0
            if health_score.last_heartbeat_at:
                heartbeat_age = health_score.heartbeat_age_seconds or 0
                # 心跳越新鲜值越高（5分钟内为1.0，超过递减）
                freshness = max(0.0, 1.0 - (heartbeat_age / 300))
                freshness_component = freshness * criteria.freshness_weight

            return health_component + load_component + freshness_component

        elif criteria.strategy == SelectionStrategy.ROUTE_SCORING:
            # 智能路由评分策略
            scoring_engine = get_global_scoring_engine()
            route_score = scoring_engine.score_worker(
                worker_id=health_score.worker_id,
                task_context=None,  # 可扩展：从criteria传递任务上下文
            )
            return route_score.overall_score

        else:
            # 默认使用健康评分
            return health_score.overall_score

    def _apply_selection_strategy(
        self,
        candidates: List[Tuple[str, WorkerHealthScore, float]],
        criteria: SelectionCriteria,
    ) -> Tuple[str, float, str]:
        """应用选择策略"""
        if not candidates:
            raise ValueError("没有候选worker")

        if criteria.strategy == SelectionStrategy.ROUND_ROBIN:
            # 轮询策略
            role_key = criteria.role or "default"
            index = self.round_robin_index.get(role_key, 0)
            selected_index = index % len(candidates)
            selected_worker_id, health_score, selection_score = candidates[selected_index]

            # 更新索引
            self.round_robin_index[role_key] = index + 1

            reason = f"轮询选择 (索引: {selected_index}/{len(candidates)})"
            return selected_worker_id, selection_score, reason

        elif criteria.strategy == SelectionStrategy.RANDOM:
            # 随机策略
            selected_worker_id, health_score, selection_score = random.choice(candidates)
            reason = "随机选择"
            return selected_worker_id, selection_score, reason

        else:
            # 基于得分的策略（健康优先、负载感知、混合）
            # 按选择得分降序排序
            sorted_candidates = sorted(candidates, key=lambda x: x[2], reverse=True)
            selected_worker_id, health_score, selection_score = sorted_candidates[0]

            reason = f"{criteria.strategy.value}策略 (得分: {selection_score:.3f})"

            # 如果有多候选且得分接近，记录备选
            if len(sorted_candidates) > 1:
                second_score = sorted_candidates[1][2]
                if abs(selection_score - second_score) < 0.05:
                    reason += f" (与次优得分接近: {second_score:.3f})"

            return selected_worker_id, selection_score, reason

    def _classify_failure(self, failure_reason: str) -> str:
        """分类故障类型"""
        reason_lower = failure_reason.lower()

        if "timeout" in reason_lower or "heartbeat" in reason_lower:
            return "heartbeat_timeout"
        elif "memory" in reason_lower or "load" in reason_lower or "overload" in reason_lower:
            return "overloaded"
        elif "unavailable" in reason_lower or "offline" in reason_lower:
            return "unavailable"
        elif "task" in reason_lower and "fail" in reason_lower:
            return "task_failure"
        else:
            return "system_error"

    def _get_load_snapshot(self) -> Dict[str, Any]:
        """获取负载快照"""
        summary = self.health_tracker.get_worker_status_summary()

        # 计算总体负载
        total_load = 0
        total_capacity = 0
        for worker_id, worker in self.health_tracker.workers.items():
            total_load += worker.current_load
            total_capacity += worker.max_capacity

        return {
            "total_load": total_load,
            "total_capacity": total_capacity,
            "load_ratio": total_load / total_capacity if total_capacity > 0 else 0.0,
            "worker_summary": summary,
        }


# 全局负载均衡器实例
_global_load_balancer: Optional[LoadBalancer] = None


def get_global_load_balancer() -> LoadBalancer:
    """获取全局负载均衡器实例"""
    global _global_load_balancer
    if _global_load_balancer is None:
        _global_load_balancer = LoadBalancer()
    return _global_load_balancer
