#!/usr/bin/env python3
"""
Health Contract Tests - 健康评分契约测试

验证健康评分契约、健康跟踪器和负载均衡器的基本功能。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import unittest
from datetime import datetime, timedelta

from agent.core.health_contract import (
    HealthDimension,
    HealthMetric,
    HealthScoringEngine,
    WorkerHealthScore,
    WorkerHealthStatus,
    get_health_scoring_engine,
)
from agent.core.load_balancer import (
    FailoverAction,
    LoadBalancer,
    SelectionCriteria,
    SelectionStrategy,
    get_global_load_balancer,
)
from agent.core.worker_health_tracker import (
    WorkerHealthTracker,
    WorkerInfo,
    get_global_health_tracker,
)


class TestHealthContract(unittest.TestCase):
    """健康评分契约测试"""

    def setUp(self):
        self.scoring_engine = HealthScoringEngine()

    def test_worker_health_score_creation(self):
        """测试 WorkerHealthScore 创建"""
        metrics = {
            HealthDimension.AVAILABILITY: HealthMetric(
                dimension=HealthDimension.AVAILABILITY,
                value=0.9,
            ),
            HealthDimension.SUCCESS_RATE: HealthMetric(
                dimension=HealthDimension.SUCCESS_RATE,
                value=0.8,
            ),
        }

        score = WorkerHealthScore(
            worker_id="test_worker",
            role="build_worker",
            overall_status=WorkerHealthStatus.HEALTHY,
            overall_score=0.85,
            metrics=metrics,
            total_tasks=10,
            successful_tasks=8,
            current_load=2,
            max_capacity=5,
        )

        self.assertEqual(score.worker_id, "test_worker")
        self.assertEqual(score.role, "build_worker")
        self.assertEqual(score.overall_status, WorkerHealthStatus.HEALTHY)
        self.assertEqual(score.overall_score, 0.85)
        self.assertEqual(score.success_rate, 0.8)
        self.assertEqual(score.load_ratio, 0.4)
        self.assertEqual(score.is_overloaded, False)

        # 测试字典转换
        score_dict = score.to_dict()
        self.assertEqual(score_dict["worker_id"], "test_worker")
        self.assertEqual(score_dict["success_rate"], 0.8)
        self.assertEqual(score_dict["load_ratio"], 0.4)

    def test_health_scoring_engine(self):
        """测试健康评分引擎"""
        # 创建测试指标
        metrics = self.scoring_engine.create_default_metrics(
            availability=1.0,
            success_rate=0.9,
            heartbeat_freshness=0.8,
            load=0.3,
            latency=0.95,
        )

        score = self.scoring_engine.calculate_health_score(
            worker_id="test_worker",
            role="build_worker",
            metrics=metrics,
            last_heartbeat_at=time.time(),
            total_tasks=20,
            successful_tasks=18,
            current_load=1,
            max_capacity=3,
        )

        self.assertEqual(score.worker_id, "test_worker")
        self.assertEqual(score.role, "build_worker")
        self.assertGreater(score.overall_score, 0.5)
        self.assertLess(score.overall_score, 1.0)

        # 验证状态分类
        if score.overall_score >= 0.7:
            self.assertEqual(score.overall_status, WorkerHealthStatus.HEALTHY)
        elif score.overall_score >= 0.3:
            self.assertEqual(score.overall_status, WorkerHealthStatus.DEGRADED)
        else:
            self.assertEqual(score.overall_status, WorkerHealthStatus.UNAVAILABLE)

    def test_health_scoring_with_timeout(self):
        """测试心跳超时对评分的影响"""
        metrics = self.scoring_engine.create_default_metrics(
            availability=1.0,
            success_rate=1.0,
            heartbeat_freshness=0.1,  # 心跳不新鲜
            load=0.0,
            latency=1.0,
        )

        # 心跳超时（10分钟前）
        old_heartbeat = time.time() - 600

        score = self.scoring_engine.calculate_health_score(
            worker_id="test_worker",
            role="build_worker",
            metrics=metrics,
            last_heartbeat_at=old_heartbeat,
        )

        # 心跳超时应导致评分降低
        self.assertLess(score.overall_score, 0.7)
        self.assertEqual(score.overall_status, WorkerHealthStatus.DEGRADED)

    def test_health_scoring_with_overload(self):
        """测试过载对评分的影响"""
        metrics = self.scoring_engine.create_default_metrics(
            availability=1.0,
            success_rate=1.0,
            heartbeat_freshness=1.0,
            load=0.95,  # 高负载
            latency=1.0,
        )

        score = self.scoring_engine.calculate_health_score(
            worker_id="test_worker",
            role="build_worker",
            metrics=metrics,
            current_load=9,
            max_capacity=10,
        )

        # 过载应导致评分降低
        self.assertLess(score.overall_score, 0.9)


class TestWorkerHealthTracker(unittest.TestCase):
    """Worker健康跟踪器测试"""

    def setUp(self):
        self.tracker = WorkerHealthTracker()

    def tearDown(self):
        # 清理全局状态
        global_tracker = get_global_health_tracker()
        # 无法直接重置单例，但测试应该使用独立实例

    def test_register_worker(self):
        """测试注册worker"""
        worker = self.tracker.register_worker(
            worker_id="test_worker_1",
            role="build_worker",
            host="localhost",
            pid=12345,
            max_capacity=3,
        )

        self.assertEqual(worker.worker_id, "test_worker_1")
        self.assertEqual(worker.role, "build_worker")
        self.assertEqual(worker.max_capacity, 3)
        self.assertIsNotNone(worker.health_score)

        # 验证已注册
        self.assertIn("test_worker_1", self.tracker.workers)

    def test_record_heartbeat(self):
        """测试记录心跳"""
        self.tracker.register_worker("test_worker_2", "researcher")

        success = self.tracker.record_heartbeat(
            worker_id="test_worker_2",
            current_load=2,
            metadata={"version": "1.0"},
        )

        self.assertTrue(success)
        worker = self.tracker.workers["test_worker_2"]
        self.assertIsNotNone(worker.last_heartbeat_at)
        self.assertEqual(worker.current_load, 2)
        self.assertEqual(worker.metadata.get("version"), "1.0")

    def test_record_task_completion(self):
        """测试记录任务完成"""
        self.tracker.register_worker("test_worker_3", "reviewer", max_capacity=2)

        # 记录任务开始
        self.tracker.record_task_start("test_worker_3", "task_1")
        worker = self.tracker.workers["test_worker_3"]
        self.assertEqual(worker.current_load, 1)

        # 记录任务成功完成
        success = self.tracker.record_task_completion(
            worker_id="test_worker_3",
            task_id="task_1",
            success=True,
            execution_time_ms=1500,
        )

        self.assertTrue(success)
        worker = self.tracker.workers["test_worker_3"]
        self.assertEqual(worker.total_tasks, 1)
        self.assertEqual(worker.successful_tasks, 1)
        self.assertEqual(worker.current_load, 0)  # 负载应减少
        self.assertIn("last_success_at", worker.metadata)

    def test_get_healthy_workers(self):
        """测试获取健康worker"""
        # 注册多个worker
        self.tracker.register_worker("worker1", "build_worker", max_capacity=3)
        self.tracker.register_worker("worker2", "build_worker", max_capacity=5)
        self.tracker.register_worker("worker3", "researcher", max_capacity=2)

        # 记录心跳（使worker存活）
        self.tracker.record_heartbeat("worker1", current_load=1)
        self.tracker.record_heartbeat("worker2", current_load=5)  # 高负载 (5/5=1.0)
        self.tracker.record_heartbeat("worker3", current_load=0)

        # 更新健康评分
        self.tracker.update_all_workers_health()

        # 获取健康的build_worker
        healthy_builders = self.tracker.get_healthy_workers(
            role="build_worker",
            min_score=0.5,
            max_load_ratio=0.8,
        )

        # worker2负载过高(4/5=0.8)，可能被排除
        self.assertEqual(len(healthy_builders), 1)
        self.assertEqual(healthy_builders[0][0], "worker1")  # worker1负载低

    def test_cleanup_stale_workers(self):
        """测试清理过期worker"""
        # 注册worker但不记录心跳
        self.tracker.register_worker("stale_worker", "builder")

        # 模拟worker注册时间在1小时前
        worker = self.tracker.workers["stale_worker"]
        worker.started_at = time.time() - 4000  # 超过1小时

        removed = self.tracker.cleanup_stale_workers(max_age_seconds=3600)

        self.assertIn("stale_worker", removed)
        self.assertNotIn("stale_worker", self.tracker.workers)


class TestLoadBalancer(unittest.TestCase):
    """负载均衡器测试"""

    def setUp(self):
        # 创建独立的健康跟踪器和负载均衡器
        self.scoring_engine = HealthScoringEngine()
        self.tracker = WorkerHealthTracker(scoring_engine=self.scoring_engine)
        self.load_balancer = LoadBalancer(
            health_tracker=self.tracker,
            scoring_engine=self.scoring_engine,
        )

        # 注册测试worker
        self.tracker.register_worker("worker_a", "build_worker", max_capacity=5)
        self.tracker.register_worker("worker_b", "build_worker", max_capacity=3)
        self.tracker.register_worker("worker_c", "researcher", max_capacity=2)

        # 记录心跳和初始负载
        self.tracker.record_heartbeat("worker_a", current_load=2)  # 负载40%
        self.tracker.record_heartbeat("worker_b", current_load=1)  # 负载33%
        self.tracker.record_heartbeat("worker_c", current_load=0)  # 负载0%

        # 记录一些任务完成（影响成功率）
        self.tracker.record_task_completion("worker_a", "task1", success=True)
        self.tracker.record_task_completion("worker_a", "task2", success=False)  # 失败
        self.tracker.record_task_completion("worker_b", "task3", success=True)
        self.tracker.record_task_completion("worker_b", "task4", success=True)

        # 更新健康评分
        self.tracker.update_all_workers_health()

    def test_select_worker_health_first(self):
        """测试健康优先选择策略"""
        criteria = SelectionCriteria(
            role="build_worker",
            strategy=SelectionStrategy.HEALTH_FIRST,
        )

        result = self.load_balancer.select_worker(criteria)

        self.assertIsNotNone(result)
        self.assertIn(result.selected_worker_id, ["worker_a", "worker_b"])
        self.assertGreater(result.selection_score, 0)
        self.assertGreater(len(result.candidates), 0)

        # 验证选择原因
        self.assertIn("health_first", result.selection_reason)

    def test_select_worker_load_aware(self):
        """测试负载感知选择策略"""
        criteria = SelectionCriteria(
            role="build_worker",
            strategy=SelectionStrategy.LOAD_AWARE,
        )

        result = self.load_balancer.select_worker(criteria)

        self.assertIsNotNone(result)
        # worker_b负载更低(1/3=0.33 vs worker_a 2/5=0.4)
        self.assertEqual(result.selected_worker_id, "worker_b")

    def test_select_worker_hybrid(self):
        """测试混合选择策略"""
        criteria = SelectionCriteria(
            role="build_worker",
            strategy=SelectionStrategy.HYBRID,
        )

        result = self.load_balancer.select_worker(criteria)

        self.assertIsNotNone(result)
        self.assertIn(result.selected_worker_id, ["worker_a", "worker_b"])

    def test_select_worker_with_exclusions(self):
        """测试排除worker的选择"""
        criteria = SelectionCriteria(
            role="build_worker",
            excluded_workers=["worker_a"],
        )

        result = self.load_balancer.select_worker(criteria)

        self.assertIsNotNone(result)
        self.assertEqual(result.selected_worker_id, "worker_b")  # worker_a被排除

    def test_select_worker_no_qualified(self):
        """测试无符合条件的worker"""
        criteria = SelectionCriteria(
            role="validator",  # 没有该角色的worker
            min_health_score=0.99,  # 要求极高评分
        )

        result = self.load_balancer.select_worker(criteria)

        self.assertIsNone(result)

    def test_handle_failure_retry(self):
        """测试故障转移重试"""
        decision = self.load_balancer.handle_failure(
            worker_id="worker_a",
            failure_reason="task execution failed",
            task_id="task_123",
            retry_count=0,
        )

        self.assertEqual(decision.original_worker_id, "worker_a")
        self.assertEqual(decision.action, FailoverAction.RETRY)
        self.assertEqual(decision.target_worker_id, "worker_a")
        self.assertIn("重试", decision.decision_reason)

    def test_handle_failure_fallback(self):
        """测试故障转移降级"""
        # 模拟多次重试后
        decision = self.load_balancer.handle_failure(
            worker_id="worker_a",
            failure_reason="task execution failed",
            task_id="task_123",
            retry_count=3,  # 超过重试次数
        )

        self.assertEqual(decision.action, FailoverAction.FALLBACK)
        self.assertNotEqual(decision.target_worker_id, "worker_a")
        self.assertIn("降级", decision.decision_reason)

    def test_handle_failure_skip(self):
        """测试故障转移跳过"""
        decision = self.load_balancer.handle_failure(
            worker_id="worker_a",
            failure_reason="system error: disk full",
            task_id="task_123",
        )

        self.assertEqual(decision.action, FailoverAction.SKIP)
        self.assertIn("跳过", decision.decision_reason)

    def test_get_selection_stats(self):
        """测试获取选择统计"""
        # 先进行一些选择
        criteria = SelectionCriteria(role="build_worker")
        for _ in range(3):
            self.load_balancer.select_worker(criteria)

        stats = self.load_balancer.get_selection_stats()

        self.assertEqual(stats["total_selections"], 3)
        self.assertIn("worker_distribution", stats)
        self.assertIn("strategy_distribution", stats)
        self.assertIn("avg_selection_score", stats)

    def test_get_failover_stats(self):
        """测试获取故障转移统计"""
        # 记录一些故障
        self.load_balancer.handle_failure("worker_a", "timeout")
        self.load_balancer.handle_failure("worker_b", "memory overload")

        stats = self.load_balancer.get_failover_stats()

        self.assertEqual(stats["total_failovers"], 2)
        self.assertIn("action_distribution", stats)
        self.assertIn("reason_distribution", stats)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_global_singletons(self):
        """测试全局单例"""
        engine1 = get_health_scoring_engine()
        engine2 = get_health_scoring_engine()
        self.assertIs(engine1, engine2)

        tracker1 = get_global_health_tracker()
        tracker2 = get_global_health_tracker()
        self.assertIs(tracker1, tracker2)

        balancer1 = get_global_load_balancer()
        balancer2 = get_global_load_balancer()
        self.assertIs(balancer1, balancer2)

    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        # 获取全局实例
        tracker = get_global_health_tracker()
        balancer = get_global_load_balancer()

        # 注册worker
        tracker.register_worker("e2e_worker", "build_worker", max_capacity=3)
        tracker.record_heartbeat("e2e_worker", current_load=1)

        # 选择worker
        result = balancer.select_worker(SelectionCriteria(role="build_worker"))
        self.assertIsNotNone(result)
        self.assertEqual(result.selected_worker_id, "e2e_worker")

        # 记录任务开始
        tracker.record_task_start("e2e_worker", "e2e_task")

        # 模拟故障
        decision = balancer.handle_failure(
            worker_id="e2e_worker",
            failure_reason="test failure",
        )

        self.assertIsNotNone(decision)

        # 记录任务失败完成
        tracker.record_task_completion("e2e_worker", "e2e_task", success=False)

        # 验证状态
        worker_score = tracker.get_worker_health("e2e_worker")
        self.assertIsNotNone(worker_score)
        self.assertEqual(worker_score.total_tasks, 1)
        self.assertEqual(worker_score.successful_tasks, 0)


if __name__ == "__main__":
    unittest.main()
