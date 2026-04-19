#!/usr/bin/env python3
"""
Route Scoring Engine - 智能路由评分引擎

提供基于多维度信号（健康度、负载、缓存命中、资源门控）的规则化评分。
输出可解释的路由评分与决策依据，支持A/B评估与安全回退。

核心原则：
1. 可解释规则化评分：避免黑盒，每个维度权重明确
2. 安全回退保证：异常输入或信号缺失时降级到安全默认策略
3. 增量可优化：保留后续机器学习算法集成入口
"""

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from .codex_cache import CacheMatchResult, CacheStatus, get_cache
from .health_contract import HealthDimension
from .parallel_build_gate import (
    AdmissionDecision,
    check_parallel_admission,
    get_global_gate,
)
from .worker_health_tracker import WorkerHealthScore, get_global_health_tracker


class ScoringDimension(Enum):
    """评分维度枚举"""

    HEALTH = "health"  # 健康度综合评分
    LOAD = "load"  # 负载压力（越低越好）
    CACHE = "cache"  # 缓存命中潜力
    RESOURCE_GATE = "resource_gate"  # 资源门控准入
    FRESHNESS = "freshness"  # 心跳新鲜度
    SUCCESS_RATE = "success_rate"  # 历史成功率


class RouteScoreStatus(Enum):
    """路由评分状态枚举"""

    OPTIMAL = "optimal"  # 最优路由
    ACCEPTABLE = "acceptable"  # 可接受路由
    DEGRADED = "degraded"  # 降级路由（有风险）
    UNAVAILABLE = "unavailable"  # 不可用
    FALLBACK = "fallback"  # 安全回退


@dataclass
class DimensionScore:
    """维度评分"""

    dimension: ScoringDimension
    raw_value: float  # 原始值（0-1或实际值）
    normalized_score: float  # 归一化得分（0-1，越高越好）
    weight: float  # 权重（0-1）
    explanation: str  # 解释说明
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteScore:
    """路由评分结果"""

    worker_id: str
    role: str
    overall_score: float  # 综合评分（0-1）
    status: RouteScoreStatus
    dimension_scores: Dict[ScoringDimension, DimensionScore]

    # 决策依据
    primary_reason: str
    secondary_reasons: List[str] = field(default_factory=list)

    # 时间戳
    timestamp: float = field(default_factory=time.time)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "worker_id": self.worker_id,
            "role": self.role,
            "overall_score": self.overall_score,
            "status": self.status.value,
            "primary_reason": self.primary_reason,
            "secondary_reasons": self.secondary_reasons,
            "timestamp": self.timestamp,
            "dimension_scores": {
                dim.value: {
                    "raw_value": score.raw_value,
                    "normalized_score": score.normalized_score,
                    "weight": score.weight,
                    "explanation": score.explanation,
                    "metadata": score.metadata,
                }
                for dim, score in self.dimension_scores.items()
            },
            "metadata": self.metadata,
        }


@dataclass
class SystemRouteScore:
    """系统级路由评分（用于决策并行/串行）"""

    # 准入决策
    admission_decision: Union[AdmissionDecision, str]
    allowed_workers: int

    # 系统评分
    system_health_score: float  # 系统健康度（0-1）
    cache_potential_score: float  # 缓存潜力（0-1）
    resource_availability_score: float  # 资源可用性（0-1）

    # 综合决策得分
    decision_score: float  # 决策得分（越高越适合并行）

    # 推荐策略
    recommended_strategy: str  # "parallel", "serial", "degraded_parallel"
    strategy_reason: str

    # 时间戳
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "admission_decision": (
                self.admission_decision.value
                if hasattr(self.admission_decision, "value")
                else self.admission_decision
            ),
            "allowed_workers": self.allowed_workers,
            "system_health_score": self.system_health_score,
            "cache_potential_score": self.cache_potential_score,
            "resource_availability_score": self.resource_availability_score,
            "decision_score": self.decision_score,
            "recommended_strategy": self.recommended_strategy,
            "strategy_reason": self.strategy_reason,
            "timestamp": self.timestamp,
        }


class RouteScoringEngine:
    """路由评分引擎"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化评分引擎

        Args:
            config: 配置字典，可覆盖默认权重和阈值
        """
        self.config = config or {}

        # 默认权重配置（可被config覆盖）
        self.weights = self.config.get(
            "weights",
            {
                ScoringDimension.HEALTH: 0.30,
                ScoringDimension.LOAD: 0.25,
                ScoringDimension.CACHE: 0.20,
                ScoringDimension.RESOURCE_GATE: 0.15,
                ScoringDimension.FRESHNESS: 0.05,
                ScoringDimension.SUCCESS_RATE: 0.05,
            },
        )

        # 阈值配置
        self.thresholds = self.config.get(
            "thresholds",
            {
                RouteScoreStatus.OPTIMAL: 0.8,
                RouteScoreStatus.ACCEPTABLE: 0.6,
                RouteScoreStatus.DEGRADED: 0.4,
                # 低于0.4为UNAVAILABLE
            },
        )

        # 缓存潜力基线（全局缓存命中率）
        self.cache_baseline_hit_rate = 0.0

        # 依赖组件
        self.health_tracker = get_global_health_tracker()

        # 缓存组件（可选）
        try:
            self.cache = get_cache()
        except Exception:
            # 创建模拟缓存对象
            class MockCache:
                def get_stats(self):
                    return {"hit_rate": 0.0, "total_hits": 0, "total_misses": 0}

            self.cache = MockCache()

        # 资源门控组件（可选）
        try:
            self.gate = get_global_gate()
        except Exception:
            # 创建模拟门控对象
            class MockGate:
                def check_admission(self, requested_workers: int = 2):
                    class AdmissionResult:
                        decision = "approved"  # 使用字符串
                        allowed_workers = requested_workers
                        reason = "模拟门控：默认批准"

                    return AdmissionResult()

            self.gate = MockGate()

        # 初始化缓存基线
        self._update_cache_baseline()

    def score_worker(
        self,
        worker_id: str,
        task_context: Optional[Dict[str, Any]] = None,
    ) -> RouteScore:
        """
        为单个worker计算路由评分

        Args:
            worker_id: worker ID
            task_context: 任务上下文（可选，可包含任务类型、预期缓存等）

        Returns:
            路由评分结果
        """
        # 获取worker健康评分
        health_score = self.health_tracker.get_worker_health(worker_id)
        if not health_score:
            # worker不存在或未注册，返回不可用评分
            return self._create_unavailable_score(worker_id, "worker未注册")

        # 计算各维度评分
        dimension_scores = {}

        # 1. 健康度维度
        health_dim_score = self._score_health_dimension(health_score)
        dimension_scores[ScoringDimension.HEALTH] = health_dim_score

        # 2. 负载维度
        load_dim_score = self._score_load_dimension(health_score)
        dimension_scores[ScoringDimension.LOAD] = load_dim_score

        # 3. 缓存维度
        cache_dim_score = self._score_cache_dimension(worker_id, task_context)
        dimension_scores[ScoringDimension.CACHE] = cache_dim_score

        # 4. 资源门控维度
        gate_dim_score = self._score_resource_gate_dimension()
        dimension_scores[ScoringDimension.RESOURCE_GATE] = gate_dim_score

        # 5. 新鲜度维度
        freshness_dim_score = self._score_freshness_dimension(health_score)
        dimension_scores[ScoringDimension.FRESHNESS] = freshness_dim_score

        # 6. 成功率维度
        success_dim_score = self._score_success_rate_dimension(health_score)
        dimension_scores[ScoringDimension.SUCCESS_RATE] = success_dim_score

        # 计算综合评分
        overall_score = self._compute_overall_score(dimension_scores)

        # 确定状态
        status = self._determine_status(overall_score)

        # 生成主要原因
        primary_reason = self._generate_primary_reason(overall_score, status, dimension_scores)

        # 生成次要原因
        secondary_reasons = self._generate_secondary_reasons(dimension_scores)

        # 构建结果
        score = RouteScore(
            worker_id=worker_id,
            role=health_score.role,
            overall_score=overall_score,
            status=status,
            dimension_scores=dimension_scores,
            primary_reason=primary_reason,
            secondary_reasons=secondary_reasons,
            metadata={
                "health_score": health_score.to_dict(),
                "task_context": task_context,
                "cache_baseline_hit_rate": self.cache_baseline_hit_rate,
            },
        )

        return score

    def score_system_routing(self) -> SystemRouteScore:
        """
        计算系统级路由评分（用于并行/串行决策）

        Returns:
            系统路由评分
        """
        # 获取资源门控决策
        admission_result = self.gate.check_admission()

        # 计算系统健康度（基于所有worker的平均健康评分）
        system_health = self._compute_system_health()

        # 计算缓存潜力
        cache_potential = self._compute_cache_potential()

        # 计算资源可用性
        resource_availability = self._compute_resource_availability(admission_result)

        # 计算决策得分
        decision_score = system_health * 0.4 + cache_potential * 0.3 + resource_availability * 0.3

        # 确定推荐策略
        # 获取决策字符串（支持枚举和字符串）
        decision = admission_result.decision
        decision_str = decision.value if hasattr(decision, "value") else decision

        if decision_str == "approved":
            if decision_score >= 0.7:
                recommended = "parallel"
                reason = "资源充足且系统健康，推荐并行执行"
            else:
                recommended = "degraded_parallel"
                reason = "资源充足但系统健康度一般，建议降级并行"
        elif decision_str == "degraded":
            recommended = "serial"
            reason = "资源有限，建议串行执行"
        else:  # rejected or manual_hold
            recommended = "serial"
            reason = "资源不足或需要人工审批，必须串行执行"

        # 构建结果
        system_score = SystemRouteScore(
            admission_decision=admission_result.decision,
            allowed_workers=admission_result.allowed_workers,
            system_health_score=system_health,
            cache_potential_score=cache_potential,
            resource_availability_score=resource_availability,
            decision_score=decision_score,
            recommended_strategy=recommended,
            strategy_reason=reason,
        )

        return system_score

    def compare_strategies(
        self,
        baseline_scores: List[RouteScore],
        tuned_scores: List[RouteScore],
    ) -> Dict[str, Any]:
        """
        比较基线策略与调优策略（A/B评估入口）

        Args:
            baseline_scores: 基线评分列表
            tuned_scores: 调优评分列表

        Returns:
            对比结果
        """
        if not baseline_scores or not tuned_scores:
            return {"error": "缺少评分数据"}

        # 计算平均分
        baseline_avg = sum(s.overall_score for s in baseline_scores) / len(baseline_scores)
        tuned_avg = sum(s.overall_score for s in tuned_scores) / len(tuned_scores)

        # 计算状态分布
        baseline_status_dist = {}
        tuned_status_dist = {}

        for status in RouteScoreStatus:
            baseline_count = sum(1 for s in baseline_scores if s.status == status)
            tuned_count = sum(1 for s in tuned_scores if s.status == status)
            baseline_status_dist[status.value] = baseline_count / len(baseline_scores)
            tuned_status_dist[status.value] = tuned_count / len(tuned_scores)

        # 确定改进方向
        improvement = tuned_avg - baseline_avg
        if improvement > 0.1:
            conclusion = "调优策略显著优于基线策略"
        elif improvement > 0:
            conclusion = "调优策略略优于基线策略"
        elif improvement == 0:
            conclusion = "调优策略与基线策略持平"
        else:
            conclusion = "基线策略优于调优策略"

        return {
            "baseline_avg_score": baseline_avg,
            "tuned_avg_score": tuned_avg,
            "improvement": improvement,
            "conclusion": conclusion,
            "baseline_status_distribution": baseline_status_dist,
            "tuned_status_distribution": tuned_status_dist,
            "comparison_timestamp": time.time(),
        }

    def _score_health_dimension(self, health_score: WorkerHealthScore) -> DimensionScore:
        """计算健康度维度评分"""
        raw_value = health_score.overall_score
        normalized = raw_value  # 已经是0-1

        explanation = f"健康评分: {raw_value:.3f} ({health_score.overall_status.value})"

        return DimensionScore(
            dimension=ScoringDimension.HEALTH,
            raw_value=raw_value,
            normalized_score=normalized,
            weight=self.weights[ScoringDimension.HEALTH],
            explanation=explanation,
            metadata={
                "health_status": health_score.overall_status.value,
                "metrics": {
                    dim.value: metric.value for dim, metric in health_score.metrics.items()
                },
            },
        )

    def _score_load_dimension(self, health_score: WorkerHealthScore) -> DimensionScore:
        """计算负载维度评分"""
        load_ratio = health_score.load_ratio
        # 负载越低越好，所以归一化得分为 (1 - load_ratio)
        normalized = 1.0 - min(load_ratio, 1.0)

        explanation = f"负载率: {load_ratio:.1%}, 归一化得分: {normalized:.3f}"

        return DimensionScore(
            dimension=ScoringDimension.LOAD,
            raw_value=load_ratio,
            normalized_score=normalized,
            weight=self.weights[ScoringDimension.LOAD],
            explanation=explanation,
            metadata={
                "current_load": health_score.current_load,
                "max_capacity": health_score.max_capacity,
                "is_overloaded": health_score.is_overloaded,
            },
        )

    def _score_cache_dimension(
        self,
        worker_id: str,
        task_context: Optional[Dict[str, Any]],
    ) -> DimensionScore:
        """计算缓存维度评分"""
        # 使用全局缓存命中率作为基线
        cache_stats = self.cache.get_stats()
        hit_rate = cache_stats.get("hit_rate", 0.0)

        # 如果有任务上下文，可以细化评估
        cache_potential = hit_rate

        # 如果任务上下文包含可缓存提示，提升潜力
        if task_context and task_context.get("cacheable", False):
            cache_potential = min(1.0, hit_rate + 0.2)

        explanation = f"全局缓存命中率: {hit_rate:.1%}, 评估潜力: {cache_potential:.3f}"

        return DimensionScore(
            dimension=ScoringDimension.CACHE,
            raw_value=hit_rate,
            normalized_score=cache_potential,
            weight=self.weights[ScoringDimension.CACHE],
            explanation=explanation,
            metadata={
                "global_hit_rate": hit_rate,
                "task_cacheable": task_context.get("cacheable", False) if task_context else False,
                "cache_stats": cache_stats,
            },
        )

    def _score_resource_gate_dimension(self) -> DimensionScore:
        """计算资源门控维度评分"""
        admission_result = self.gate.check_admission()

        # 将准入决策映射为评分
        # 决策到评分的映射（支持枚举和字符串）
        decision_scores = {
            AdmissionDecision.APPROVED: 1.0,
            AdmissionDecision.DEGRADED: 0.5,
            AdmissionDecision.REJECTED: 0.0,
            AdmissionDecision.MANUAL_HOLD: 0.2,
            "approved": 1.0,
            "degraded": 0.5,
            "rejected": 0.0,
            "manual_hold": 0.2,
        }

        # 获取决策值（枚举或字符串）
        decision = admission_result.decision
        # 如果决策是枚举，获取其值用于查找
        decision_key = decision.value if hasattr(decision, "value") else decision

        normalized = decision_scores.get(decision_key, 0.0)

        # 获取显示值
        display_decision = decision.value if hasattr(decision, "value") else decision

        explanation = (
            f"资源门控决策: {display_decision}, "
            f"允许worker数: {admission_result.allowed_workers}"
        )

        return DimensionScore(
            dimension=ScoringDimension.RESOURCE_GATE,
            raw_value=admission_result.allowed_workers / 2.0,  # 归一化到0-1
            normalized_score=normalized,
            weight=self.weights[ScoringDimension.RESOURCE_GATE],
            explanation=explanation,
            metadata={
                "admission_decision": display_decision,
                "allowed_workers": admission_result.allowed_workers,
                "reason": admission_result.reason,
            },
        )

    def _score_freshness_dimension(self, health_score: WorkerHealthScore) -> DimensionScore:
        """计算新鲜度维度评分"""
        if health_score.last_heartbeat_at is None:
            heartbeat_age = float("inf")
            freshness = 0.0
            explanation = "无心跳记录"
        else:
            heartbeat_age = health_score.heartbeat_age_seconds or 0
            # 5分钟内为1.0，超过递减，30分钟以上为0.0
            freshness = max(0.0, 1.0 - (heartbeat_age / 1800))
            explanation = f"心跳年龄: {heartbeat_age:.0f}秒, 新鲜度: {freshness:.3f}"

        return DimensionScore(
            dimension=ScoringDimension.FRESHNESS,
            raw_value=heartbeat_age,
            normalized_score=freshness,
            weight=self.weights[ScoringDimension.FRESHNESS],
            explanation=explanation,
            metadata={
                "last_heartbeat_at": health_score.last_heartbeat_at,
                "heartbeat_age_seconds": health_score.heartbeat_age_seconds,
            },
        )

    def _score_success_rate_dimension(self, health_score: WorkerHealthScore) -> DimensionScore:
        """计算成功率维度评分"""
        success_rate = health_score.success_rate
        normalized = success_rate

        explanation = f"历史成功率: {success_rate:.1%}"

        return DimensionScore(
            dimension=ScoringDimension.SUCCESS_RATE,
            raw_value=success_rate,
            normalized_score=normalized,
            weight=self.weights[ScoringDimension.SUCCESS_RATE],
            explanation=explanation,
            metadata={
                "total_tasks": health_score.total_tasks,
                "successful_tasks": health_score.successful_tasks,
                "failed_tasks": health_score.failed_tasks,
            },
        )

    def _compute_overall_score(
        self,
        dimension_scores: Dict[ScoringDimension, DimensionScore],
    ) -> float:
        """计算综合评分"""
        weighted_sum = 0.0
        total_weight = 0.0

        for dim, score in dimension_scores.items():
            weighted_sum += score.normalized_score * score.weight
            total_weight += score.weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _determine_status(self, overall_score: float) -> RouteScoreStatus:
        """根据综合评分确定状态"""
        if overall_score >= self.thresholds[RouteScoreStatus.OPTIMAL]:
            return RouteScoreStatus.OPTIMAL
        elif overall_score >= self.thresholds[RouteScoreStatus.ACCEPTABLE]:
            return RouteScoreStatus.ACCEPTABLE
        elif overall_score >= self.thresholds[RouteScoreStatus.DEGRADED]:
            return RouteScoreStatus.DEGRADED
        else:
            return RouteScoreStatus.UNAVAILABLE

    def _generate_primary_reason(
        self,
        overall_score: float,
        status: RouteScoreStatus,
        dimension_scores: Dict[ScoringDimension, DimensionScore],
    ) -> str:
        """生成主要原因"""
        # 找出得分最低的维度
        worst_dim = None
        worst_score = 1.0

        for dim, score in dimension_scores.items():
            if score.normalized_score < worst_score:
                worst_score = score.normalized_score
                worst_dim = dim

        if worst_dim and worst_score < 0.5:
            return f"评分{overall_score:.2f} ({status.value})，主要限制: {worst_dim.value}"
        else:
            return f"评分{overall_score:.2f} ({status.value})，各维度均衡"

    def _generate_secondary_reasons(
        self,
        dimension_scores: Dict[ScoringDimension, DimensionScore],
    ) -> List[str]:
        """生成次要原因列表"""
        reasons = []

        for dim, score in dimension_scores.items():
            if score.normalized_score < 0.7:
                reasons.append(
                    f"{dim.value}: {score.explanation} (得分: {score.normalized_score:.2f})"
                )

        return reasons

    def _create_unavailable_score(
        self,
        worker_id: str,
        reason: str,
    ) -> RouteScore:
        """创建不可用评分"""
        dimension_scores = {
            ScoringDimension.HEALTH: DimensionScore(
                dimension=ScoringDimension.HEALTH,
                raw_value=0.0,
                normalized_score=0.0,
                weight=1.0,
                explanation="Worker未注册或不可用",
            )
        }

        return RouteScore(
            worker_id=worker_id,
            role="unknown",
            overall_score=0.0,
            status=RouteScoreStatus.UNAVAILABLE,
            dimension_scores=dimension_scores,
            primary_reason=reason,
            secondary_reasons=[f"Worker {worker_id} 不可用: {reason}"],
        )

    def _compute_system_health(self) -> float:
        """计算系统健康度（所有worker的平均健康评分）"""
        workers = self.health_tracker.workers

        if not workers:
            return 0.5  # 默认中等健康度

        total_score = 0.0
        count = 0

        for worker_id, worker in workers.items():
            if worker.health_score:
                total_score += worker.health_score.overall_score
                count += 1

        return total_score / count if count > 0 else 0.5

    def _compute_cache_potential(self) -> float:
        """计算缓存潜力"""
        cache_stats = self.cache.get_stats()
        hit_rate = cache_stats.get("hit_rate", 0.0)

        # 基于命中率评估潜力
        if hit_rate > 0.3:
            return 0.8 + (hit_rate - 0.3) * 0.5  # 缩放
        else:
            return hit_rate * 2.0  # 低命中率时线性映射

    def _compute_resource_availability(
        self,
        admission_result,
    ) -> float:
        """计算资源可用性"""
        # 获取决策值（支持枚举和字符串）
        decision = admission_result.decision
        decision_key = decision.value if hasattr(decision, "value") else decision

        decision_scores = {
            AdmissionDecision.APPROVED: 1.0,
            AdmissionDecision.DEGRADED: 0.6,
            AdmissionDecision.REJECTED: 0.2,
            AdmissionDecision.MANUAL_HOLD: 0.4,
            "approved": 1.0,
            "degraded": 0.6,
            "rejected": 0.2,
            "manual_hold": 0.4,
        }

        return decision_scores.get(decision_key, 0.0)

    def _update_cache_baseline(self):
        """更新缓存基线"""
        try:
            cache_stats = self.cache.get_stats()
            self.cache_baseline_hit_rate = cache_stats.get("hit_rate", 0.0)
        except Exception:
            self.cache_baseline_hit_rate = 0.0


# 全局评分引擎实例
_global_scoring_engine: Optional[RouteScoringEngine] = None


def get_global_scoring_engine() -> RouteScoringEngine:
    """获取全局路由评分引擎实例"""
    global _global_scoring_engine
    if _global_scoring_engine is None:
        _global_scoring_engine = RouteScoringEngine()
    return _global_scoring_engine


def score_worker(
    worker_id: str,
    task_context: Optional[Dict[str, Any]] = None,
) -> RouteScore:
    """为单个worker计算路由评分（便捷函数）"""
    engine = get_global_scoring_engine()
    return engine.score_worker(worker_id, task_context)


def score_system_routing() -> SystemRouteScore:
    """计算系统级路由评分（便捷函数）"""
    engine = get_global_scoring_engine()
    return engine.score_system_routing()


def compare_strategies(
    baseline_scores: List[RouteScore],
    tuned_scores: List[RouteScore],
) -> Dict[str, Any]:
    """比较评分策略（便捷函数）"""
    engine = get_global_scoring_engine()
    return engine.compare_strategies(baseline_scores, tuned_scores)


if __name__ == "__main__":
    # 简单命令行测试
    import json

    engine = RouteScoringEngine()

    print("=== 路由评分引擎测试 ===")

    # 测试系统评分
    print("\n1. 系统路由评分:")
    system_score = engine.score_system_routing()
    print(json.dumps(system_score.to_dict(), ensure_ascii=False, indent=2))

    # 测试worker评分（模拟数据）
    print("\n2. Worker路由评分（模拟）:")

    # 获取一个真实worker（如果有）
    health_tracker = get_global_health_tracker()
    workers = list(health_tracker.workers.keys())

    if workers:
        for i, worker_id in enumerate(workers[:2]):  # 测试前2个worker
            score = engine.score_worker(worker_id)
            print(f"\nWorker {worker_id}:")
            print(f"  综合评分: {score.overall_score:.3f} ({score.status.value})")
            print(f"  主要原因: {score.primary_reason}")
    else:
        print("  没有注册的worker，无法测试worker评分")

    print("\n✅ 路由评分引擎测试完成")
