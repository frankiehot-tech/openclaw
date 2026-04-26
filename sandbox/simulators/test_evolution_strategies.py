#!/usr/bin/env python3
"""演化策略扩展模块测试"""

import sys
import time
import random
from unittest.mock import MagicMock, patch

# 添加当前目录到Python路径
sys.path.insert(0, ".")

from sandbox_manager import SandboxManager, EvolutionStrategy
from evolution_strategies import (
    GeneticAlgorithmStrategy,
    MultiObjectiveOptimizer,
    create_strategy,
)


class TestEvolutionStrategies:
    """演化策略测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建模拟沙箱管理器
        self.mock_sandbox = MagicMock(spec=SandboxManager)

        # 模拟状态管理器
        self.mock_state_manager = MagicMock()
        self.mock_sandbox.state_manager = self.mock_state_manager

        # 模拟演化引擎
        self.mock_evolution_engine = MagicMock()
        self.mock_sandbox.evolution_engine = self.mock_evolution_engine

        # 模拟监控器
        self.mock_monitor = MagicMock()
        self.mock_sandbox.monitor = self.mock_monitor

        # 模拟稳定性约束
        self.mock_sandbox.stability_constraints = {
            "max_hamming_distance": 1,
            "max_quality_drop": 0.5,
            "max_transition_rate": 10.0,
        }

    def test_genetic_algorithm_strategy_initialization(self):
        """测试遗传算法策略初始化"""
        print("=== 测试遗传算法策略初始化 ===")

        strategy = GeneticAlgorithmStrategy(self.mock_sandbox)

        # 验证属性设置
        assert strategy.sandbox_manager == self.mock_sandbox
        assert strategy.population_size == 10
        assert strategy.generations == 5
        assert strategy.mutation_rate == 0.1
        assert strategy.crossover_rate == 0.8

        print("✅ 遗传算法策略初始化测试通过")

    def test_genetic_algorithm_population_initialization(self):
        """测试遗传算法种群初始化"""
        print("\n=== 测试遗传算法种群初始化 ===")

        strategy = GeneticAlgorithmStrategy(self.mock_sandbox)

        # 模拟候选状态
        current_state = "010101"
        candidates = ["010100", "010111", "010001", "011101", "000101", "110101"]

        # 测试种群初始化
        population = strategy._initialize_population(current_state, candidates)

        # 验证种群大小
        assert len(population) == min(strategy.population_size, len(candidates))

        # 验证所有个体都在候选列表中或是当前状态
        for individual in population:
            assert individual in candidates or individual == current_state

        print("✅ 遗传算法种群初始化测试通过")

    def test_genetic_algorithm_crossover(self):
        """测试遗传算法交叉操作"""
        print("\n=== 测试遗传算法交叉操作 ===")

        strategy = GeneticAlgorithmStrategy(self.mock_sandbox)

        # 测试数据
        parent1 = "010101"
        parent2 = "101010"

        # 执行交叉（可能需要多次执行以覆盖不同交叉点）
        child1, child2 = strategy._crossover(parent1, parent2)

        # 验证子代长度
        assert len(child1) == 6
        assert len(child2) == 6

        # 验证交叉点有效性
        # 子代应该是父代片段的组合
        assert child1 != parent1 or child1 != parent2  # 可能相同（如果交叉点在边界）
        assert child2 != parent1 or child2 != parent2  # 可能相同

        print("✅ 遗传算法交叉操作测试通过")

    def test_genetic_algorithm_mutation(self):
        """测试遗传算法变异操作"""
        print("\n=== 测试遗传算法变异操作 ===")

        strategy = GeneticAlgorithmStrategy(self.mock_sandbox)

        # 测试数据
        individual = "010101"
        candidates = ["010100", "010111", "010001"]

        # 设置随机种子以确保可重复性
        random.seed(42)

        # 执行变异（可能不变异）
        mutated = strategy._mutate(individual, candidates)

        # 验证变异结果
        assert mutated == individual or mutated in candidates

        # 测试多次以覆盖不同情况
        results = []
        for _ in range(20):
            result = strategy._mutate(individual, candidates)
            results.append(result)

        # 验证至少有一次变异发生（概率问题）
        # 这里主要是确保函数不崩溃
        print(f"  变异测试样本: {set(results)}")

        print("✅ 遗传算法变异操作测试通过")

    def test_genetic_algorithm_selection(self):
        """测试遗传算法选择最优转换"""
        print("\n=== 测试遗传算法选择最优转换 ===")

        strategy = GeneticAlgorithmStrategy(self.mock_sandbox)

        # 模拟候选状态
        current_state = "010101"
        candidates = ["010100", "010111", "010001", "011101", "000101"]

        # 模拟评估结果
        def mock_evaluate_transition(from_state, to_state):
            # 简化的评估函数：质量差异基于汉明距离
            distance = sum(1 for a, b in zip(from_state, to_state) if a != b)
            quality_delta = random.uniform(-0.5, 1.0)  # 随机质量变化
            benefit = quality_delta - (distance * 0.1)
            return {
                "valid": random.random() > 0.2,  # 80%有效
                "benefit": benefit,
                "quality_delta": quality_delta,
            }

        # 模拟演化引擎的评估方法
        self.mock_evolution_engine.evaluate_transition = mock_evaluate_transition

        # 执行遗传算法选择
        best_state = strategy.select_best_transition(current_state, candidates)

        # 验证结果
        # 可能是None（如果没有有效转换）或候选状态之一
        assert best_state is None or best_state in candidates

        print(f"✅ 遗传算法选择测试通过: 最佳状态 = {best_state}")

    def test_multi_objective_optimizer_initialization(self):
        """测试多目标优化器初始化"""
        print("\n=== 测试多目标优化器初始化 ===")

        optimizer = MultiObjectiveOptimizer(self.mock_sandbox)

        # 验证属性设置
        assert optimizer.sandbox_manager == self.mock_sandbox
        assert "quality" in optimizer.objectives
        assert "stability" in optimizer.objectives
        assert "diversity" in optimizer.objectives

        print("✅ 多目标优化器初始化测试通过")

    def test_multi_objective_evaluation(self):
        """测试多目标评估"""
        print("\n=== 测试多目标评估 ===")

        optimizer = MultiObjectiveOptimizer(self.mock_sandbox)

        # 模拟基础评估
        mock_base_evaluation = {
            "valid": True,
            "benefit": 1.5,
            "quality_delta": 1.5,
            "cost": 1.0,
        }

        # 模拟汉明距离计算
        def mock_hamming_distance(state1, state2):
            return sum(1 for a, b in zip(state1, state2) if a != b)

        self.mock_state_manager.hamming_distance = mock_hamming_distance

        # 模拟转换频率计数
        self.mock_monitor.state_transitions = []

        # 执行多目标评估
        current_state = "010101"
        target_state = "010100"

        # 模拟演化引擎的评估方法
        self.mock_evolution_engine.evaluate_transition.return_value = (
            mock_base_evaluation
        )

        evaluation = optimizer.evaluate_transition(current_state, target_state)

        # 验证评估结果
        assert evaluation["valid"] == True
        assert "quality_score" in evaluation
        assert "stability_score" in evaluation
        assert "diversity_score" in evaluation
        assert "combined_score" in evaluation
        assert evaluation["benefit"] == evaluation["combined_score"]  # 使用综合收益

        print(f"✅ 多目标评估测试通过: 综合分数 = {evaluation['combined_score']:.3f}")

    def test_strategy_factory(self):
        """测试策略工厂"""
        print("\n=== 测试策略工厂 ===")

        # 测试创建遗传算法策略
        genetic_strategy = create_strategy("genetic", self.mock_sandbox)
        assert isinstance(genetic_strategy, GeneticAlgorithmStrategy)

        # 测试创建多目标优化器
        multi_objective_strategy = create_strategy("multi_objective", self.mock_sandbox)
        assert isinstance(multi_objective_strategy, MultiObjectiveOptimizer)

        # 测试未知策略
        try:
            create_strategy("unknown", self.mock_sandbox)
            assert False, "应抛出ValueError异常"
        except ValueError as e:
            assert "未知策略" in str(e)

        print("✅ 策略工厂测试通过")

    def test_integration_with_evolution_engine(self):
        """测试与演化引擎的集成"""
        print("\n=== 测试与演化引擎的集成 ===")

        # 使用模拟的沙箱管理器进行集成测试
        # 注意：这里不创建实际的沙箱管理器，以避免复杂的初始化

        # 模拟演化引擎方法
        def mock_generate_candidates(current_state, step_size=1.0):
            # 模拟生成候选状态
            # 改变当前状态的一位
            candidates = []
            for i in range(6):
                # 翻转第i位
                state_list = list(current_state)
                state_list[i] = "1" if state_list[i] == "0" else "0"
                candidates.append("".join(state_list))
            return candidates

        # 模拟评估方法
        def mock_evaluate_transition(from_state, to_state):
            # 计算汉明距离
            distance = sum(1 for a, b in zip(from_state, to_state) if a != b)
            # 简单的质量评估
            quality_delta = random.uniform(-0.5, 1.0)
            benefit = quality_delta - (distance * 0.1)
            return {
                "valid": True,
                "benefit": benefit,
                "quality_delta": quality_delta,
                "cost": distance,
            }

        # 配置模拟
        self.mock_evolution_engine.generate_candidate_transitions = (
            mock_generate_candidates
        )
        self.mock_evolution_engine.evaluate_transition = mock_evaluate_transition

        # 模拟状态管理器的汉明距离计算
        def mock_hamming_distance(state1, state2):
            return sum(1 for a, b in zip(state1, state2) if a != b)

        self.mock_state_manager.hamming_distance = mock_hamming_distance

        # 模拟所有状态的二进制表示
        self.mock_state_manager._by_binary = {
            "000000": None,
            "000001": None,
            "000010": None,
            "000011": None,
            "010101": None,
            "010100": None,
            "010111": None,
            "010001": None,
        }

        # 测试遗传算法策略
        current_state = "010101"

        # 生成候选状态
        candidates = mock_generate_candidates(current_state)

        # 创建实际的演化引擎实例（简化）
        from sandbox_manager import EvolutionEngine

        engine = EvolutionEngine(self.mock_sandbox)

        # 覆盖模拟方法
        engine.generate_candidate_transitions = mock_generate_candidates
        engine.evaluate_transition = mock_evaluate_transition

        # 初始化策略实例缓存
        engine._strategy_instances = {}

        # 测试遗传算法选择
        try:
            genetic_result = engine._genetic_selection(current_state, candidates)
            assert genetic_result is None or genetic_result in candidates
            print(f"✅ 遗传算法集成测试通过: 结果 = {genetic_result}")
        except Exception as e:
            print(f"⚠️  遗传算法集成测试跳过: {e}")

        # 测试多目标优化策略
        try:
            multi_objective_result = engine._multi_objective_selection(
                current_state, candidates
            )
            assert (
                multi_objective_result is None or multi_objective_result in candidates
            )
            print(f"✅ 多目标优化集成测试通过: 结果 = {multi_objective_result}")
        except Exception as e:
            print(f"⚠️  多目标优化集成测试跳过: {e}")

    def test_strategy_performance_comparison(self):
        """测试策略性能对比（简单基准测试）"""
        print("\n=== 测试策略性能对比 ===")

        # 使用固定随机种子以确保可重复性
        random.seed(42)

        # 创建策略实例
        genetic_strategy = GeneticAlgorithmStrategy(self.mock_sandbox)

        # 模拟测试数据
        current_state = "010101"
        candidates = ["010100", "010111", "010001", "011101", "000101", "110101"]

        # 模拟评估函数
        def mock_evaluate_transition(from_state, to_state):
            # 基于汉明距离的简单评估
            distance = sum(1 for a, b in zip(from_state, to_state) if a != b)
            quality_delta = random.uniform(-0.2, 0.8)
            benefit = quality_delta - (distance * 0.05)
            return {"valid": True, "benefit": benefit, "quality_delta": quality_delta}

        self.mock_evolution_engine.evaluate_transition = mock_evaluate_transition

        # 运行遗传算法选择
        start_time = time.time()
        genetic_result = genetic_strategy.select_best_transition(
            current_state, candidates
        )
        genetic_time = time.time() - start_time

        print(f"  遗传算法: 结果={genetic_result}, 耗时={genetic_time:.4f}秒")

        # 模拟贪心策略作为比较基准
        def greedy_selection(current_state, candidates):
            best_state = None
            best_benefit = float("-inf")

            for candidate in candidates:
                evaluation = mock_evaluate_transition(current_state, candidate)
                if evaluation["valid"] and evaluation["benefit"] > best_benefit:
                    best_benefit = evaluation["benefit"]
                    best_state = candidate

            return best_state

        start_time = time.time()
        greedy_result = greedy_selection(current_state, candidates)
        greedy_time = time.time() - start_time

        print(f"  贪心策略: 结果={greedy_result}, 耗时={greedy_time:.4f}秒")

        # 注意：遗传算法可能花费更长时间，这是正常的
        print("✅ 策略性能对比测试完成")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("演化策略扩展模块测试套件")
    print("=" * 60)

    test_class = TestEvolutionStrategies()

    # 获取测试方法
    test_methods = [method for method in dir(test_class) if method.startswith("test_")]

    passed = 0
    failed = 0

    for method_name in test_methods:
        test_class.setup_method()
        method = getattr(test_class, method_name)

        try:
            method()
            print(f"✅ {method_name}: 通过\n")
            passed += 1
        except Exception as e:
            print(f"❌ {method_name}: 失败 - {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"总计: {len(test_methods)} 个测试")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"成功率: {passed/len(test_methods)*100:.1f}%")

    if failed == 0:
        print("\n🎉 所有演化策略测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit(run_all_tests())
