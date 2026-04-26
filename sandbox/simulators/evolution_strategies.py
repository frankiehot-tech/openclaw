#!/usr/bin/env python3
"""演化策略扩展模块：遗传算法和多目标优化"""

import random
import math
from typing import List, Tuple, Dict, Any, Optional
from enum import Enum


class GeneticAlgorithmStrategy:
    """遗传算法演化策略"""

    def __init__(self, sandbox_manager: "SandboxManager"):
        """
        初始化遗传算法策略

        Args:
            sandbox_manager: 沙箱管理器引用
        """
        self.sandbox_manager = sandbox_manager
        self.population_size = 10
        self.generations = 5
        self.mutation_rate = 0.1
        self.crossover_rate = 0.8
        self.selection_pressure = 2.0

    def select_best_transition(
        self, current_state: str, candidates: List[str]
    ) -> Optional[str]:
        """
        使用遗传算法选择最优状态转换

        Args:
            current_state: 当前状态（6位二进制）
            candidates: 候选状态列表（汉明距离为1）

        Returns:
            最优目标状态，或None（如果没有有效转换）
        """
        if not candidates:
            return None

        # 如果候选太少，直接使用贪心策略
        if len(candidates) <= 2:
            return self._greedy_fallback(current_state, candidates)

        # 初始化种群：从候选状态中随机选择
        population = self._initialize_population(current_state, candidates)

        # 运行遗传算法
        for generation in range(self.generations):
            # 评估适应度
            fitness_scores = self._evaluate_population(current_state, population)

            # 选择父代
            parents = self._select_parents(population, fitness_scores)

            # 生成子代（交叉和变异）
            offspring = self._crossover_and_mutate(parents, candidates)

            # 合并种群并选择下一代
            population = self._select_next_generation(
                current_state, population + offspring, fitness_scores
            )

        # 返回最佳个体
        return self._select_best_individual(current_state, population)

    def _initialize_population(
        self, current_state: str, candidates: List[str]
    ) -> List[str]:
        """初始化种群"""
        # 从候选状态中随机选择，确保多样性
        population_size = min(self.population_size, len(candidates))
        population = random.sample(candidates, population_size)

        # 确保当前状态也在种群中（精英保留）
        if current_state not in population:
            population[0] = current_state

        return population

    def _evaluate_population(
        self, current_state: str, population: List[str]
    ) -> List[float]:
        """评估种群适应度"""
        fitness_scores = []

        for individual in population:
            # 计算转换评估
            evaluation = self.sandbox_manager.evolution_engine.evaluate_transition(
                current_state, individual
            )

            if evaluation["valid"]:
                # 适应度 = 收益 + 稳定性奖励
                benefit = evaluation["benefit"]
                stability_bonus = 1.0 if evaluation.get("stable", True) else 0.0
                fitness = benefit + stability_bonus
            else:
                fitness = -1000  # 无效转换的惩罚

            fitness_scores.append(fitness)

        return fitness_scores

    def _select_parents(
        self, population: List[str], fitness_scores: List[float]
    ) -> List[str]:
        """选择父代（锦标赛选择）"""
        parents = []
        tournament_size = max(2, len(population) // 4)

        for _ in range(len(population)):
            # 随机选择锦标赛参与者
            tournament_indices = random.sample(range(len(population)), tournament_size)
            tournament_fitness = [fitness_scores[i] for i in tournament_indices]

            # 选择适应度最高的作为胜者
            winner_index = tournament_indices[
                tournament_fitness.index(max(tournament_fitness))
            ]
            parents.append(population[winner_index])

        return parents

    def _crossover_and_mutate(
        self, parents: List[str], candidates: List[str]
    ) -> List[str]:
        """交叉和变异生成子代"""
        offspring = []

        for i in range(0, len(parents) - 1, 2):
            parent1 = parents[i]
            parent2 = parents[i + 1]

            # 决定是否交叉
            if random.random() < self.crossover_rate:
                child1, child2 = self._crossover(parent1, parent2)
            else:
                child1, child2 = parent1, parent2

            # 变异
            child1 = self._mutate(child1, candidates)
            child2 = self._mutate(child2, candidates)

            offspring.extend([child1, child2])

        return offspring

    def _crossover(self, parent1: str, parent2: str) -> Tuple[str, str]:
        """单点交叉"""
        # 确保是6位二进制字符串
        assert len(parent1) == 6 and len(parent2) == 6

        # 随机选择交叉点
        crossover_point = random.randint(1, 5)

        child1 = parent1[:crossover_point] + parent2[crossover_point:]
        child2 = parent2[:crossover_point] + parent1[crossover_point:]

        return child1, child2

    def _mutate(self, individual: str, candidates: List[str]) -> str:
        """变异：随机翻转一位"""
        if random.random() < self.mutation_rate:
            # 从候选状态中随机选择一个（这些状态与当前状态汉明距离为1）
            if candidates:
                return random.choice(candidates)

        return individual

    def _select_next_generation(
        self,
        current_state: str,
        combined_population: List[str],
        fitness_scores: List[float],
    ) -> List[str]:
        """选择下一代（精英选择）"""
        # 计算适应度
        fitness_map = {}
        for i, individual in enumerate(combined_population):
            if i < len(fitness_scores):
                fitness_map[individual] = fitness_scores[i]
            else:
                # 对新个体评估适应度
                evaluation = self.sandbox_manager.evolution_engine.evaluate_transition(
                    current_state, individual
                )
                fitness_map[individual] = (
                    evaluation["benefit"] if evaluation["valid"] else -1000
                )

        # 按适应度排序
        sorted_individuals = sorted(
            combined_population, key=lambda x: fitness_map[x], reverse=True
        )

        # 选择前population_size个
        next_generation = sorted_individuals[: self.population_size]

        # 确保多样性：如果种群太相似，添加随机个体
        if len(set(next_generation)) < len(next_generation) // 2:
            # 添加一些随机候选状态
            all_candidates = self._get_all_candidates(current_state)
            if all_candidates:
                random_candidate = random.choice(all_candidates)
                if random_candidate not in next_generation:
                    next_generation[-1] = random_candidate

        return next_generation

    def _select_best_individual(
        self, current_state: str, population: List[str]
    ) -> Optional[str]:
        """从种群中选择最佳个体"""
        best_individual = None
        best_fitness = float("-inf")

        for individual in population:
            evaluation = self.sandbox_manager.evolution_engine.evaluate_transition(
                current_state, individual
            )

            if evaluation["valid"] and evaluation["benefit"] > best_fitness:
                best_fitness = evaluation["benefit"]
                best_individual = individual

        return best_individual

    def _greedy_fallback(
        self, current_state: str, candidates: List[str]
    ) -> Optional[str]:
        """回退到贪心策略"""
        best_state = None
        best_benefit = float("-inf")

        for candidate in candidates:
            evaluation = self.sandbox_manager.evolution_engine.evaluate_transition(
                current_state, candidate
            )

            if evaluation["valid"] and evaluation["benefit"] > best_benefit:
                best_benefit = evaluation["benefit"]
                best_state = candidate

        return best_state

    def _get_all_candidates(self, current_state: str) -> List[str]:
        """获取所有可能的候选状态（汉明距离为1）"""
        all_states = list(self.sandbox_manager.state_manager._by_binary.keys())
        max_distance = self.sandbox_manager.stability_constraints[
            "max_hamming_distance"
        ]

        candidates = []
        for state in all_states:
            distance = self.sandbox_manager.state_manager.hamming_distance(
                current_state, state
            )
            if distance == max_distance and distance > 0:
                candidates.append(state)

        return candidates


class MultiObjectiveOptimizer:
    """多目标优化器"""

    def __init__(self, sandbox_manager: "SandboxManager"):
        self.sandbox_manager = sandbox_manager
        self.objectives = ["quality", "stability", "diversity"]

    def evaluate_transition(
        self, current_state: str, target_state: str
    ) -> Dict[str, Any]:
        """多目标评估转换"""
        # 基础评估
        base_evaluation = self.sandbox_manager.evolution_engine.evaluate_transition(
            current_state, target_state
        )

        if not base_evaluation["valid"]:
            return {"valid": False}

        # 计算多目标分数
        quality_score = base_evaluation["benefit"]
        stability_score = self._calculate_stability_score(current_state, target_state)
        diversity_score = self._calculate_diversity_score(current_state, target_state)

        # 加权求和（可根据需求调整权重）
        weights = {"quality": 0.5, "stability": 0.3, "diversity": 0.2}
        combined_score = (
            weights["quality"] * quality_score
            + weights["stability"] * stability_score
            + weights["diversity"] * diversity_score
        )

        return {
            "valid": True,
            "quality_score": quality_score,
            "stability_score": stability_score,
            "diversity_score": diversity_score,
            "combined_score": combined_score,
            "quality_delta": base_evaluation["quality_delta"],
            "cost": base_evaluation["cost"],
            "benefit": combined_score,  # 使用综合收益
        }

    def _calculate_stability_score(
        self, current_state: str, target_state: str
    ) -> float:
        """计算稳定性分数"""
        # 基于汉明距离的稳定性评估
        distance = self.sandbox_manager.state_manager.hamming_distance(
            current_state, target_state
        )
        max_distance = self.sandbox_manager.stability_constraints[
            "max_hamming_distance"
        ]

        # 距离越小越稳定
        stability = 1.0 - (distance / max_distance) if max_distance > 0 else 1.0

        # 考虑历史转换频率
        transition_count = self._count_transition_frequency(current_state, target_state)
        frequency_penalty = 1.0 / (1.0 + transition_count)  # 转换越频繁，惩罚越大

        return stability * frequency_penalty

    def _calculate_diversity_score(
        self, current_state: str, target_state: str
    ) -> float:
        """计算多样性分数"""
        # 检查目标状态是否在最近的历史中出现过
        recent_states = (
            self.sandbox_manager.monitor.state_transitions[-10:]
            if hasattr(self.sandbox_manager, "monitor")
            else []
        )

        # 计算目标状态在历史中的出现次数
        occurrence_count = sum(
            1
            for transition in recent_states
            if transition.get("to_state") == target_state
        )

        # 出现次数越少，多样性分数越高
        diversity = 1.0 / (1.0 + occurrence_count)

        return diversity

    def _count_transition_frequency(self, from_state: str, to_state: str) -> int:
        """计算状态转换频率"""
        if not hasattr(self.sandbox_manager, "monitor"):
            return 0

        transitions = self.sandbox_manager.monitor.state_transitions
        count = 0

        for transition in transitions:
            if (
                transition.get("from_state") == from_state
                and transition.get("to_state") == to_state
            ):
                count += 1

        return count


# 策略工厂
def create_strategy(strategy_name: str, sandbox_manager: "SandboxManager") -> Any:
    """创建演化策略实例"""
    if strategy_name == "genetic":
        return GeneticAlgorithmStrategy(sandbox_manager)
    elif strategy_name == "multi_objective":
        return MultiObjectiveOptimizer(sandbox_manager)
    else:
        raise ValueError(f"未知策略: {strategy_name}")


if __name__ == "__main__":
    print("演化策略扩展模块")
    print("=" * 50)
    print("包含:")
    print("1. 遗传算法策略 (GeneticAlgorithmStrategy)")
    print("2. 多目标优化器 (MultiObjectiveOptimizer)")
    print("3. 策略工厂 (create_strategy)")
