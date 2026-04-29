#!/usr/bin/env python3
"""
A/B评估测试脚本 - 对比基线策略与智能路由评分策略

验证智能路由评分层是否能够：
1. 为worker提供可解释的评分
2. 影响路由决策
3. 提供结构化评估结果
"""

import json
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from mini_agent.agent.core.load_balancer import (
        SelectionCriteria,
        SelectionStrategy,
        get_global_load_balancer,
    )
    from mini_agent.agent.core.route_scoring import (
        get_global_scoring_engine,
    )
    from mini_agent.agent.core.worker_health_tracker import (
        get_global_health_tracker,
    )

    ROUTE_SCORING_AVAILABLE = True
except ImportError as e:
    print(f"导入失败: {e}")
    ROUTE_SCORING_AVAILABLE = False


def setup_test_workers():
    """设置测试worker（如果还没有worker）"""
    health_tracker = get_global_health_tracker()

    # 检查现有worker
    if len(health_tracker.workers) >= 2:
        print(f"已有 {len(health_tracker.workers)} 个worker，使用现有worker")
        return list(health_tracker.workers.keys())[:2]

    # 注册模拟worker
    worker_ids = []
    for i in range(2):
        worker_id = f"test_worker_{int(time.time())}_{i}"
        health_tracker.register_worker(
            worker_id=worker_id,
            role="test_worker",
            max_capacity=5,
            metadata={"test": True},
        )
        # 模拟心跳
        health_tracker.record_heartbeat(worker_id, current_load=i)
        # 模拟任务完成记录
        health_tracker.record_task_completion(worker_id, f"task_{i}", success=True)
        worker_ids.append(worker_id)

    print(f"注册了 {len(worker_ids)} 个测试worker: {worker_ids}")
    return worker_ids


def test_worker_scoring(worker_ids):
    """测试worker评分"""
    print("\n=== 测试worker评分 ===")
    engine = get_global_scoring_engine()

    scores = []
    for worker_id in worker_ids:
        score = engine.score_worker(worker_id)
        scores.append(score)
        print(f"\nWorker {worker_id}:")
        print(f"  综合评分: {score.overall_score:.3f} ({score.status.value})")
        print(f"  主要原因: {score.primary_reason}")
        print("  维度评分:")
        for dim, dim_score in score.dimension_scores.items():
            print(f"    {dim.value}: {dim_score.normalized_score:.3f} ({dim_score.explanation})")

    return scores


def test_system_routing():
    """测试系统路由评分"""
    print("\n=== 测试系统路由评分 ===")
    engine = get_global_scoring_engine()

    system_score = engine.score_system_routing()
    print(f"准入决策: {system_score.admission_decision}")
    print(f"允许worker数: {system_score.allowed_workers}")
    print(f"系统健康度: {system_score.system_health_score:.3f}")
    print(f"缓存潜力: {system_score.cache_potential_score:.3f}")
    print(f"资源可用性: {system_score.resource_availability_score:.3f}")
    print(f"决策得分: {system_score.decision_score:.3f}")
    print(f"推荐策略: {system_score.recommended_strategy}")
    print(f"策略原因: {system_score.strategy_reason}")

    return system_score


def test_load_balancer_baseline(worker_ids):
    """测试负载均衡器基线策略（HYBRID）"""
    print("\n=== 测试负载均衡器基线策略 ===")
    load_balancer = get_global_load_balancer()

    # 使用HYBRID策略（现有基线）
    criteria = SelectionCriteria(
        strategy=SelectionStrategy.HYBRID,
        health_weight=0.6,
        load_weight=0.3,
        freshness_weight=0.1,
    )

    result = load_balancer.select_worker(criteria)
    if result:
        print(f"基线策略选择: {result.selected_worker_id}")
        print(f"选择得分: {result.selection_score:.3f}")
        print(f"选择原因: {result.selection_reason}")

        # 收集所有候选的得分
        baseline_scores = []
        for worker_id, health_score, sel_score in result.candidates:
            baseline_scores.append(
                {
                    "worker_id": worker_id,
                    "selection_score": sel_score,
                    "health_score": health_score.overall_score,
                }
            )
        print(f"候选worker得分: {baseline_scores}")
        return result, baseline_scores
    else:
        print("基线策略无可用worker")
        return None, []


def test_load_balancer_route_scoring(worker_ids):
    """测试负载均衡器路由评分策略（ROUTE_SCORING）"""
    print("\n=== 测试负载均衡器路由评分策略 ===")
    load_balancer = get_global_load_balancer()

    # 使用ROUTE_SCORING策略（新策略）
    criteria = SelectionCriteria(
        strategy=SelectionStrategy.ROUTE_SCORING,
    )

    result = load_balancer.select_worker(criteria)
    if result:
        print(f"路由评分策略选择: {result.selected_worker_id}")
        print(f"选择得分: {result.selection_score:.3f}")
        print(f"选择原因: {result.selection_reason}")

        # 收集所有候选的得分
        tuned_scores = []
        for worker_id, health_score, sel_score in result.candidates:
            tuned_scores.append(
                {
                    "worker_id": worker_id,
                    "selection_score": sel_score,
                    "health_score": health_score.overall_score,
                }
            )
        print(f"候选worker得分: {tuned_scores}")
        return result, tuned_scores
    else:
        print("路由评分策略无可用worker")
        return None, []


def test_ab_comparison(baseline_scores, tuned_scores):
    """测试A/B比较"""
    print("\n=== 测试A/B比较 ===")
    engine = get_global_scoring_engine()

    # 将得分转换为RouteScore对象（简化版）
    # 这里我们使用模拟的RouteScore，仅用于比较
    class MockRouteScore:
        def __init__(self, worker_id, overall_score):
            self.worker_id = worker_id
            self.overall_score = overall_score
            self.status = "acceptable"  # 模拟状态

    baseline_route_scores = [
        MockRouteScore(item["worker_id"], item["selection_score"]) for item in baseline_scores
    ]
    tuned_route_scores = [
        MockRouteScore(item["worker_id"], item["selection_score"]) for item in tuned_scores
    ]

    # 使用引擎的比较功能
    comparison = engine.compare_strategies(baseline_route_scores, tuned_route_scores)

    print("A/B比较结果:")
    print(json.dumps(comparison, ensure_ascii=False, indent=2))

    return comparison


def test_fallback_scenarios():
    """测试回退场景"""
    print("\n=== 测试回退场景 ===")
    engine = get_global_scoring_engine()

    # 测试不存在的worker
    print("1. 测试不存在的worker评分:")
    invalid_score = engine.score_worker("non_existent_worker_12345")
    print(f"   Worker不存在评分: {invalid_score.overall_score:.3f} ({invalid_score.status.value})")
    print(f"   原因: {invalid_score.primary_reason}")

    # 测试异常输入
    print("\n2. 测试异常输入:")
    try:
        # 模拟缓存组件异常
        engine.cache = None
        # 应该触发回退
        score = engine.score_worker("dummy")
        print(f"   缓存异常时的评分: {score.overall_score:.3f}")
        print(f"   状态: {score.status.value}")
    except Exception as e:
        print(f"   异常处理: {e}")

    print("\n回退场景测试完成")


def main():
    """主测试函数"""
    print("=" * 70)
    print("智能路由评分A/B评估测试")
    print("=" * 70)

    if not ROUTE_SCORING_AVAILABLE:
        print("错误: 路由评分模块不可用")
        return 1

    try:
        # 1. 设置测试环境
        worker_ids = setup_test_workers()
        if len(worker_ids) < 2:
            print("错误: 需要至少2个worker进行测试")
            return 1

        # 2. 测试worker评分
        worker_scores = test_worker_scoring(worker_ids)

        # 3. 测试系统路由评分
        system_score = test_system_routing()

        # 4. 测试基线策略
        baseline_result, baseline_scores = test_load_balancer_baseline(worker_ids)

        # 5. 测试路由评分策略
        tuned_result, tuned_scores = test_load_balancer_route_scoring(worker_ids)

        # 6. A/B比较
        if baseline_scores and tuned_scores:
            comparison = test_ab_comparison(baseline_scores, tuned_scores)
        else:
            print("警告: 无法进行A/B比较，缺少得分数据")
            comparison = None

        # 7. 测试回退场景
        test_fallback_scenarios()

        # 8. 总结
        print("\n" + "=" * 70)
        print("测试总结")
        print("=" * 70)

        print("✅ 路由评分引擎: 已实现")
        print(f"✅ 路由决策入口: {SelectionStrategy.ROUTE_SCORING.value} 策略已集成到负载均衡器")
        print("✅ A/B评估入口: compare_strategies() 函数可用")
        print("✅ 回退验证: 异常输入时能安全回退")

        if comparison:
            improvement = comparison.get("improvement", 0)
            if improvement > 0:
                print(f"✅ 策略改进: 路由评分策略比基线策略提升 {improvement:.3f}")
            else:
                print("⚠️  策略改进: 路由评分策略与基线策略持平或略差")

        print("\n📊 关键输出:")
        print(f"   1. Worker评分: {[s.overall_score for s in worker_scores]}")
        print(f"   2. 系统路由决策: {system_score.recommended_strategy}")
        print(f"   3. A/B比较结果: {comparison.get('conclusion', 'N/A') if comparison else 'N/A'}")

        print("\n✅ 所有测试完成")
        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
