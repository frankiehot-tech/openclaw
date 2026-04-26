#!/usr/bin/env python3
"""
MAREF沙箱管理器

基于控制论原理的智能工作流演化系统。
集成了64卦状态系统和超稳定性原则，确保系统在演化过程中保持可控和可预测。

架构组件：
1. 沙箱管理器 (SandboxManager) - 本文件
2. 反馈控制器 (FeedbackController) - 质量监控和PID控制
3. 演化引擎 (EvolutionEngine) - 生成候选状态转换
4. 监控系统 (SandboxMonitor) - 记录状态转换和性能指标
"""

import sys
sys.path.insert(0, "/Volumes/1TB-M2/openclaw")

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from integrated_hexagram_state_manager import IntegratedHexagramStateManager, HetuState
from hexagram_cache import HexagramCacheManager
from evolution_strategies import create_strategy


class EvolutionStrategy(Enum):
    """演化策略枚举"""

    GREEDY = "greedy"  # 贪心策略：选择立即质量提升最大的转换
    SIMULATED_ANNEALING = "simulated_annealing"  # 模拟退火：允许暂时质量下降
    GENETIC = "genetic"  # 遗传算法：组合多个质量维度
    MULTI_OBJECTIVE = "multi_objective"  # 多目标优化：同时优化质量、稳定性和多样性


@dataclass
class SystemState:
    """系统状态数据结构"""

    current_state: str  # 当前6位二进制状态
    quality_score: float  # 质量评分 (0-10)
    stability_index: float  # 稳定性指数 (0-1)
    active_dimensions: List[bool]  # 激活的质量维度
    hetu_state: HetuState  # 对应的河图状态
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EvolutionResult:
    """演化结果数据结构"""

    success: bool  # 是否成功达到目标质量
    final_quality: float  # 最终质量评分
    target_quality: float  # 目标质量评分
    iterations: int  # 迭代次数
    execution_time: float  # 执行时间（秒）
    path: List[str]  # 演化路径（状态序列）
    quality_timeline: List[float]  # 质量时间线
    stability_violations: int = 0  # 稳定性约束违反次数
    strategy_used: EvolutionStrategy = EvolutionStrategy.GREEDY


@dataclass
class ControlSignal:
    """控制论反馈信号"""

    quality_error: float  # 质量误差：目标质量 - 当前质量
    cumulative_error: float  # 累积误差（积分项）
    error_rate: float  # 误差变化率（微分项）
    control_signal: float  # PID控制信号
    timestamp: datetime = field(default_factory=datetime.now)


class FeedbackController:
    """反馈控制器 - 基于PID控制原理"""

    def __init__(
        self,
        sandbox_manager: "SandboxManager",
        kp: float = 0.8,
        ki: float = 0.1,
        kd: float = 0.2,
    ):
        """
        初始化反馈控制器

        Args:
            sandbox_manager: 沙箱管理器引用
            kp: 比例系数 (默认0.8)
            ki: 积分系数 (默认0.1)
            kd: 微分系数 (默认0.2)
        """
        self.sandbox_manager = sandbox_manager
        self.kp = kp
        self.ki = ki
        self.kd = kd

        # PID控制状态
        self.previous_error = 0.0
        self.cumulative_error = 0.0
        self.last_update = datetime.now()

        # 历史记录
        self.control_history: List[ControlSignal] = []

    def calculate_control_signal(
        self, current_quality: float, target_quality: float
    ) -> ControlSignal:
        """
        计算PID控制信号

        Args:
            current_quality: 当前质量评分
            target_quality: 目标质量评分

        Returns:
            ControlSignal: 包含PID计算结果的反馈信号
        """
        now = datetime.now()

        # 计算质量误差
        quality_error = target_quality - current_quality

        # 更新累积误差（积分项）
        self.cumulative_error += quality_error

        # 计算误差变化率（微分项）
        time_delta = (now - self.last_update).total_seconds()
        if time_delta > 0:
            error_rate = (quality_error - self.previous_error) / time_delta
        else:
            error_rate = 0.0

        # PID控制信号
        control_signal = (
            self.kp * quality_error  # 比例项
            + self.ki * self.cumulative_error  # 积分项
            + self.kd * error_rate  # 微分项
        )

        # 创建控制信号记录
        signal = ControlSignal(
            quality_error=quality_error,
            cumulative_error=self.cumulative_error,
            error_rate=error_rate,
            control_signal=control_signal,
        )

        # 更新状态
        self.previous_error = quality_error
        self.last_update = now
        self.control_history.append(signal)

        return signal

    def adjust_evolution_parameters(
        self, control_signal: ControlSignal
    ) -> Dict[str, Any]:
        """
        根据控制信号调整演化参数

        Args:
            control_signal: 控制信号

        Returns:
            调整后的演化参数
        """
        # 基于控制信号调整演化步长
        # 控制信号越大，演化步长应该越小（更保守）
        base_step_size = 1.0  # 基础步长（汉明距离）

        # 归一化控制信号到[0.1, 2.0]范围
        normalized_signal = abs(control_signal.control_signal)
        if normalized_signal > 5.0:
            normalized_signal = 5.0
        elif normalized_signal < 0.1:
            normalized_signal = 0.1

        # 逆相关：控制信号越大，步长越小
        step_size = base_step_size / normalized_signal

        # 限制步长范围
        if step_size < 0.1:
            step_size = 0.1
        elif step_size > 5.0:
            step_size = 5.0

        return {
            "step_size": step_size,
            "exploration_rate": 0.3 / normalized_signal,  # 探索率
            "quality_threshold": 0.1 * normalized_signal,  # 质量阈值
        }


class EvolutionEngine:
    """演化引擎 - 生成候选状态转换"""

    def __init__(self, sandbox_manager: "SandboxManager"):
        """
        初始化演化引擎

        Args:
            sandbox_manager: 沙箱管理器引用
        """
        self.sandbox_manager = sandbox_manager
        self.strategy = EvolutionStrategy.GREEDY

        # 初始化策略实例缓存
        self._strategy_instances = {}

        # 预初始化遗传算法和多目标优化器
        try:
            self._strategy_instances["genetic"] = create_strategy(
                "genetic", sandbox_manager
            )
            self._strategy_instances["multi_objective"] = create_strategy(
                "multi_objective", sandbox_manager
            )
        except Exception as e:
            print(f"⚠️  无法初始化高级策略: {e}")
            print("  将继续使用贪心和模拟退火策略")

    def set_strategy(self, strategy: EvolutionStrategy):
        """设置演化策略"""
        self.strategy = strategy

    def generate_candidate_transitions(
        self, current_state: str, step_size: float = 1.0
    ) -> List[str]:
        """
        生成候选状态转换

        Args:
            current_state: 当前状态（6位二进制）
            step_size: 演化步长（汉明距离）

        Returns:
            候选状态列表
        """
        # 获取所有可能的状态
        all_states = list(self.sandbox_manager.state_manager._by_binary.keys())

        # 根据超稳定性约束筛选状态（汉明距离必须为1）
        max_distance = self.sandbox_manager.stability_constraints[
            "max_hamming_distance"
        ]
        candidates = []
        for state in all_states:
            # 计算汉明距离
            distance = self.sandbox_manager.state_manager.hamming_distance(
                current_state, state
            )

            # 距离必须满足格雷编码约束
            if distance == max_distance and distance > 0:
                candidates.append(state)

        # 如果候选集太大，随机抽样
        max_candidates = 20
        if len(candidates) > max_candidates:
            import random

            candidates = random.sample(candidates, max_candidates)

        return candidates

    def evaluate_transition(self, from_state: str, to_state: str) -> Dict[str, Any]:
        """
        评估状态转换的成本-收益

        Args:
            from_state: 源状态
            to_state: 目标状态

        Returns:
            包含成本和收益的评估结果
        """
        # 分析两个状态
        from_analysis = self.sandbox_manager.state_manager.analyze_state(from_state)
        to_analysis = self.sandbox_manager.state_manager.analyze_state(to_state)

        if not from_analysis or not to_analysis:
            return {
                "cost": float("inf"),
                "benefit": 0.0,
                "quality_delta": 0.0,
                "valid": False,
            }

        # 质量变化
        quality_delta = to_analysis.quality_score - from_analysis.quality_score

        # 计算成本：汉明距离（状态变化幅度）
        distance = self.sandbox_manager.state_manager.hamming_distance(
            from_state, to_state
        )

        # 收益函数：质量提升 - 成本惩罚
        benefit = quality_delta - (distance * 0.1)  # 距离惩罚系数0.1

        # 检查约束
        valid = self.sandbox_manager._check_constraints(from_state, to_state)

        return {
            "cost": distance,
            "benefit": benefit,
            "quality_delta": quality_delta,
            "valid": valid,
            "from_quality": from_analysis.quality_score,
            "to_quality": to_analysis.quality_score,
        }

    def select_best_transition(
        self,
        current_state: str,
        candidates: List[str],
        strategy: EvolutionStrategy = None,
    ) -> Optional[str]:
        """
        选择最优状态转换

        Args:
            current_state: 当前状态
            candidates: 候选状态列表
            strategy: 演化策略（默认使用引擎策略）

        Returns:
            最优目标状态，或None（如果没有有效转换）
        """
        if not candidates:
            return None

        strategy = strategy or self.strategy

        if strategy == EvolutionStrategy.GREEDY:
            return self._greedy_selection(current_state, candidates)
        elif strategy == EvolutionStrategy.SIMULATED_ANNEALING:
            return self._simulated_annealing_selection(current_state, candidates)
        elif strategy == EvolutionStrategy.GENETIC:
            return self._genetic_selection(current_state, candidates)
        elif strategy == EvolutionStrategy.MULTI_OBJECTIVE:
            return self._multi_objective_selection(current_state, candidates)
        else:
            # 默认使用贪心策略
            return self._greedy_selection(current_state, candidates)

    def _greedy_selection(
        self, current_state: str, candidates: List[str]
    ) -> Optional[str]:
        """贪心策略：选择立即质量提升最大的转换"""
        best_state = None
        best_benefit = float("-inf")

        for candidate in candidates:
            evaluation = self.evaluate_transition(current_state, candidate)
            if evaluation["valid"] and evaluation["benefit"] > best_benefit:
                best_benefit = evaluation["benefit"]
                best_state = candidate

        return best_state

    def _simulated_annealing_selection(
        self, current_state: str, candidates: List[str], temperature: float = 1.0
    ) -> Optional[str]:
        """
        模拟退火策略：允许暂时质量下降以跳出局部最优

        Args:
            temperature: 温度参数（越高越可能接受劣质解）
        """
        import random
        import math

        if not candidates:
            return None

        # 评估所有候选
        evaluations = []
        for candidate in candidates:
            eval_result = self.evaluate_transition(current_state, candidate)
            if eval_result["valid"]:
                evaluations.append((candidate, eval_result))

        if not evaluations:
            return None

        # 按收益排序
        evaluations.sort(key=lambda x: x[1]["benefit"], reverse=True)

        # 以一定概率接受非最优解
        best_candidate, best_eval = evaluations[0]

        # 温度衰减（随着迭代次数增加而降低）
        effective_temp = temperature

        # 随机决定是否接受次优解
        if len(evaluations) > 1 and random.random() < 0.3:  # 30%概率探索
            # 从次优解中随机选择一个
            idx = random.randint(1, min(3, len(evaluations) - 1))
            candidate, eval_result = evaluations[idx]

            # 计算接受概率（基于收益差和温度）
            benefit_diff = best_eval["benefit"] - eval_result["benefit"]
            if benefit_diff > 0:
                acceptance_prob = math.exp(-benefit_diff / effective_temp)
                if random.random() < acceptance_prob:
                    return candidate

        return best_candidate

    def _genetic_selection(
        self, current_state: str, candidates: List[str]
    ) -> Optional[str]:
        """
        遗传算法策略：使用遗传算法选择最优状态转换

        Args:
            current_state: 当前状态
            candidates: 候选状态列表

        Returns:
            最优目标状态，或None（如果没有有效转换）
        """
        try:
            # 获取遗传算法策略实例
            genetic_strategy = self._strategy_instances.get("genetic")
            if genetic_strategy is None:
                # 如果没有预初始化，尝试动态创建
                genetic_strategy = create_strategy("genetic", self.sandbox_manager)
                self._strategy_instances["genetic"] = genetic_strategy

            # 调用遗传算法的选择方法
            return genetic_strategy.select_best_transition(current_state, candidates)

        except Exception as e:
            print(f"⚠️  遗传算法策略失败，回退到贪心策略: {e}")
            # 回退到贪心策略
            return self._greedy_selection(current_state, candidates)

    def _multi_objective_selection(
        self, current_state: str, candidates: List[str]
    ) -> Optional[str]:
        """
        多目标优化策略：使用多目标评估选择最优状态转换

        Args:
            current_state: 当前状态
            candidates: 候选状态列表

        Returns:
            最优目标状态，或None（如果没有有效转换）
        """
        try:
            # 获取多目标优化器实例
            multi_objective_optimizer = self._strategy_instances.get("multi_objective")
            if multi_objective_optimizer is None:
                # 如果没有预初始化，尝试动态创建
                multi_objective_optimizer = create_strategy(
                    "multi_objective", self.sandbox_manager
                )
                self._strategy_instances["multi_objective"] = multi_objective_optimizer

            # 使用多目标评估进行贪心选择
            best_state = None
            best_score = float("-inf")

            for candidate in candidates:
                # 使用多目标优化器的评估方法
                evaluation = multi_objective_optimizer.evaluate_transition(
                    current_state, candidate
                )
                if evaluation["valid"] and evaluation["benefit"] > best_score:
                    best_score = evaluation["benefit"]
                    best_state = candidate

            return best_state

        except Exception as e:
            print(f"⚠️  多目标优化策略失败，回退到贪心策略: {e}")
            # 回退到贪心策略
            return self._greedy_selection(current_state, candidates)


class SandboxMonitor:
    """沙箱监控系统 - 记录状态转换和性能指标"""

    def __init__(self, sandbox_manager: "SandboxManager"):
        """
        初始化监控系统

        Args:
            sandbox_manager: 沙箱管理器引用
        """
        self.sandbox_manager = sandbox_manager

        # 监控记录
        self.state_transitions: List[Dict] = []
        self.performance_metrics: Dict[str, List] = {
            "iteration_times": [],
            "quality_changes": [],
            "control_signals": [],
            "constraint_violations": [],
        }

        # 时间跟踪
        self.start_time = None

    def start_monitoring(self):
        """开始监控"""
        self.start_time = datetime.now()
        print("📊 沙箱监控系统启动")

    def log_transition(
        self, from_state: str, to_state: str, evaluation: Dict[str, Any], iteration: int
    ):
        """
        记录状态转换

        Args:
            from_state: 源状态
            to_state: 目标状态
            evaluation: 转换评估结果
            iteration: 迭代次数
        """
        transition_record = {
            "iteration": iteration,
            "timestamp": datetime.now(),
            "from_state": from_state,
            "to_state": to_state,
            "quality_delta": evaluation.get("quality_delta", 0.0),
            "cost": evaluation.get("cost", 0.0),
            "benefit": evaluation.get("benefit", 0.0),
            "valid": evaluation.get("valid", False),
        }

        self.state_transitions.append(transition_record)

    def log_performance(
        self,
        iteration_time: float,
        quality_change: float,
        control_signal: float = None,
        constraint_violation: bool = False,
    ):
        """
        记录性能指标

        Args:
            iteration_time: 迭代耗时（秒）
            quality_change: 质量变化
            control_signal: 控制信号值
            constraint_violation: 是否违反约束
        """
        self.performance_metrics["iteration_times"].append(iteration_time)
        self.performance_metrics["quality_changes"].append(quality_change)

        if control_signal is not None:
            self.performance_metrics["control_signals"].append(control_signal)

        self.performance_metrics["constraint_violations"].append(constraint_violation)

    def generate_report(self) -> Dict[str, Any]:
        """生成监控报告"""
        if not self.state_transitions:
            return {"status": "no_data"}

        total_iterations = len(self.state_transitions)
        total_time = (datetime.now() - self.start_time).total_seconds()

        # 计算成功率
        successful_transitions = [t for t in self.state_transitions if t["valid"]]
        success_rate = (
            len(successful_transitions) / total_iterations
            if total_iterations > 0
            else 0
        )

        # 平均质量提升
        quality_deltas = [
            t["quality_delta"] for t in self.state_transitions if t["valid"]
        ]
        avg_quality_change = (
            sum(quality_deltas) / len(quality_deltas) if quality_deltas else 0
        )

        # 约束违反次数
        constraint_violations = sum(self.performance_metrics["constraint_violations"])

        # 平均迭代时间
        iteration_times = self.performance_metrics["iteration_times"]
        avg_iteration_time = (
            sum(iteration_times) / len(iteration_times) if iteration_times else 0
        )

        report = {
            "monitoring_duration_seconds": total_time,
            "total_iterations": total_iterations,
            "success_rate": success_rate,
            "average_quality_change": avg_quality_change,
            "constraint_violations": constraint_violations,
            "average_iteration_time_seconds": avg_iteration_time,
            "system_stability_index": (
                1.0 - (constraint_violations / total_iterations)
                if total_iterations > 0
                else 1.0
            ),
            "timestamp": datetime.now(),
        }

        return report

    def save_report(self, filepath: str = "sandbox_monitor_report.json"):
        """保存监控报告到文件"""
        report = self.generate_report()

        # 转换datetime为字符串
        def datetime_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                report, f, default=datetime_serializer, indent=2, ensure_ascii=False
            )

        print(f"📄 监控报告已保存到: {filepath}")


class SandboxManager:
    """MAREF沙箱管理器 - 核心协调组件"""

    def __init__(self, mapping_file: str = "hetu_hexagram_mapping.json"):
        """
        初始化沙箱管理器

        Args:
            mapping_file: 河图-卦象映射文件路径
        """
        print("=" * 60)
        print("🚀 MAREF沙箱环境初始化")
        print("=" * 60)

        # 1. 初始化64卦状态管理器
        print("📊 加载64卦状态系统...")
        self.state_manager = IntegratedHexagramStateManager(mapping_file)
        self.state_manager.initialize_state("000000")  # 默认初始状态
        print(f"   当前状态: {self.state_manager.current_state}")
        print(f"   河图状态: {self.state_manager.get_hetu_state().name}")

        # 2. 预计算分析缓存（优化性能）
        print("🔧 执行预计算优化...")
        try:
            self.state_manager.precompute_all_analysis()
            print(f"   分析缓存大小: {len(self.state_manager._analysis_cache)}/64")
        except AttributeError:
            print("   ⚠️  预计算不可用，跳过...")

        # 3. 初始化各组件
        print("🔄 初始化控制论组件...")
        self.feedback_controller = FeedbackController(self)
        self.evolution_engine = EvolutionEngine(self)
        self.monitor = SandboxMonitor(self)

        # 4. 超稳定性参数
        self.stability_constraints = {
            "max_hamming_distance": 1,  # 最大汉明距离（格雷编码约束）
            "min_quality": 0.0,  # 最小质量评分
            "max_quality": 10.0,  # 最大质量评分
            "max_iterations_per_second": 10,  # 每秒最大转换次数
            "rollback_on_violation": True,  # 违反约束时自动回滚
        }

        # 5. 演化状态
        self.evolution_history: List[SystemState] = []
        self.current_iteration = 0
        self.last_transition_time = None

        print("✅ MAREF沙箱环境初始化完成")
        print("=" * 60)

    def _check_constraints(self, from_state: str, to_state: str) -> bool:
        """
        检查超稳定性约束

        Args:
            from_state: 源状态
            to_state: 目标状态

        Returns:
            bool: 是否满足所有约束
        """
        # 1. 格雷编码约束：汉明距离必须为1
        distance = self.state_manager.hamming_distance(from_state, to_state)
        if distance > self.stability_constraints["max_hamming_distance"]:
            print(
                f"⚠️  约束违反：汉明距离 {distance} > {self.stability_constraints['max_hamming_distance']}"
            )
            return False

        # 2. 质量边界约束
        to_analysis = self.state_manager.analyze_state(to_state)
        if to_analysis:
            quality = to_analysis.quality_score
            if quality < self.stability_constraints["min_quality"]:
                print(
                    f"⚠️  约束违反：质量 {quality} < {self.stability_constraints['min_quality']}"
                )
                return False
            if quality > self.stability_constraints["max_quality"]:
                print(
                    f"⚠️  约束违反：质量 {quality} > {self.stability_constraints['max_quality']}"
                )
                return False

        # 3. 转换速率约束
        if self.last_transition_time:
            current_time = datetime.now()
            time_since_last = (current_time - self.last_transition_time).total_seconds()
            if (
                time_since_last > 0
                and time_since_last
                < 1.0 / self.stability_constraints["max_iterations_per_second"]
            ):
                print(f"⚠️  约束违反：转换过快，间隔 {time_since_last:.2f} 秒")
                return False

        return True

    def _rollback_to_stable_state(self) -> bool:
        """回滚到上一个稳定状态"""
        if len(self.evolution_history) < 2:
            print("⚠️  无法回滚：历史记录不足")
            return False

        # 回滚到上一个状态
        previous_state = self.evolution_history[-2]
        self.state_manager.current_state = previous_state.current_state
        self.evolution_history = self.evolution_history[:-1]  # 移除当前状态

        print(f"↩️  系统回滚到状态: {previous_state.current_state}")
        return True

    def get_system_state(self) -> SystemState:
        """获取完整的系统状态"""
        current_state = self.state_manager.current_state or "000000"

        # 获取质量评分
        analysis = self.state_manager.analyze_state(current_state)
        quality_score = analysis.quality_score if analysis else 0.0

        # 获取河图状态
        hetu_state = self.state_manager.get_hetu_state(current_state)

        # 获取激活维度
        if analysis and hasattr(analysis, "dimension_values"):
            # 按DIMENSIONS顺序获取维度值
            active_dimensions = []
            for dim in self.state_manager.DIMENSIONS:
                val = analysis.dimension_values.get(dim)
                if val is not None:
                    # 确保值为整数
                    try:
                        active_dimensions.append(int(val) > 0)
                    except (ValueError, TypeError):
                        active_dimensions.append(False)
                else:
                    active_dimensions.append(False)
        else:
            active_dimensions = [False] * 6

        # 计算稳定性指数（基于约束违反历史）
        if self.monitor.performance_metrics["constraint_violations"]:
            violations = sum(self.monitor.performance_metrics["constraint_violations"])
            total = len(self.monitor.performance_metrics["constraint_violations"])
            stability_index = 1.0 - (violations / total) if total > 0 else 1.0
        else:
            stability_index = 1.0

        return SystemState(
            current_state=current_state,
            quality_score=quality_score,
            stability_index=stability_index,
            active_dimensions=active_dimensions,
            hetu_state=hetu_state,
        )

    def evolve(
        self,
        target_quality: float,
        max_iterations: int = 100,
        strategy: EvolutionStrategy = EvolutionStrategy.GREEDY,
    ) -> EvolutionResult:
        """
        驱动系统向目标质量演化

        Args:
            target_quality: 目标质量评分 (0-10)
            max_iterations: 最大迭代次数
            strategy: 演化策略

        Returns:
            EvolutionResult: 演化结果
        """
        print("=" * 60)
        print(f"🎯 MAREF演化开始")
        print(f"   目标质量: {target_quality:.1f}/10")
        print(f"   最大迭代次数: {max_iterations}")
        print(f"   演化策略: {strategy.value}")
        print("=" * 60)

        # 初始化监控
        self.monitor.start_monitoring()

        # 设置演化策略
        self.evolution_engine.set_strategy(strategy)

        # 记录开始时间
        start_time = time.time()

        # 初始化演化状态
        self.current_iteration = 0
        evolution_path = []
        quality_timeline = []
        stability_violations = 0

        # 获取初始状态
        initial_state = self.get_system_state()
        evolution_path.append(initial_state.current_state)
        quality_timeline.append(initial_state.quality_score)

        print(
            f"📈 初始状态: {initial_state.current_state}, 质量: {initial_state.quality_score:.2f}"
        )

        # 主演化循环
        while self.current_iteration < max_iterations:
            iteration_start = time.time()

            # 获取当前状态
            current_system_state = self.get_system_state()
            current_quality = current_system_state.quality_score
            current_state_binary = current_system_state.current_state

            # 检查是否达到目标
            if current_quality >= target_quality:
                print(f"✅ 达到目标质量: {current_quality:.2f} >= {target_quality}")
                break

            # 计算PID控制信号
            control_signal = self.feedback_controller.calculate_control_signal(
                current_quality, target_quality
            )

            # 根据控制信号调整演化参数
            evolution_params = self.feedback_controller.adjust_evolution_parameters(
                control_signal
            )
            step_size = evolution_params["step_size"]

            print(f"🔄 迭代 {self.current_iteration+1}/{max_iterations}:")
            print(f"   当前质量: {current_quality:.2f}, 目标: {target_quality:.2f}")
            print(
                f"   控制信号: {control_signal.control_signal:.3f}, 步长: {step_size:.2f}"
            )

            # 生成候选转换
            candidates = self.evolution_engine.generate_candidate_transitions(
                current_state_binary, step_size
            )

            if not candidates:
                print("⚠️  没有可用的候选转换，演化停滞")
                break

            # 选择最优转换
            best_candidate = self.evolution_engine.select_best_transition(
                current_state_binary, candidates, strategy
            )

            if not best_candidate:
                print("⚠️  没有有效的候选转换，演化停滞")
                break

            # 评估转换
            evaluation = self.evolution_engine.evaluate_transition(
                current_state_binary, best_candidate
            )

            # 检查约束
            constraint_satisfied = self._check_constraints(
                current_state_binary, best_candidate
            )

            if not constraint_satisfied:
                stability_violations += 1
                print("⚠️  转换违反稳定性约束")

                if self.stability_constraints["rollback_on_violation"]:
                    self._rollback_to_stable_state()
                    # 继续下一轮迭代
                    self.current_iteration += 1
                    continue
                else:
                    # 跳过这个转换
                    continue

            # 执行状态转换
            transition_success = self.state_manager.transition(best_candidate)

            if not transition_success:
                print("⚠️  状态转换失败")
                self.current_iteration += 1
                continue

            # 记录转换
            self.monitor.log_transition(
                current_state_binary, best_candidate, evaluation, self.current_iteration
            )

            # 记录性能
            iteration_time = time.time() - iteration_start
            quality_change = evaluation.get("quality_delta", 0.0)
            self.monitor.log_performance(
                iteration_time,
                quality_change,
                control_signal.control_signal,
                not constraint_satisfied,
            )

            # 更新系统状态
            new_system_state = self.get_system_state()
            self.evolution_history.append(new_system_state)
            self.last_transition_time = datetime.now()

            # 更新演化路径
            evolution_path.append(best_candidate)
            quality_timeline.append(new_system_state.quality_score)

            print(f"   {current_state_binary} → {best_candidate}")
            print(
                f"   质量变化: +{quality_change:.2f} ({current_quality:.2f} → {new_system_state.quality_score:.2f})"
            )
            print(f"   迭代耗时: {iteration_time:.3f}秒")

            self.current_iteration += 1

        # 演化结束
        execution_time = time.time() - start_time

        # 最终状态
        final_system_state = self.get_system_state()
        final_quality = final_system_state.quality_score

        # 检查是否成功
        success = final_quality >= target_quality

        print("=" * 60)
        print(f"🎯 MAREF演化完成")
        print(f"   最终质量: {final_quality:.2f}/10")
        print(f"   目标质量: {target_quality:.2f}")
        print(f"   迭代次数: {self.current_iteration}/{max_iterations}")
        print(f"   执行时间: {execution_time:.2f}秒")
        print(f"   成功: {'✅' if success else '❌'}")
        print("=" * 60)

        # 生成监控报告
        report = self.monitor.generate_report()
        print(
            f"📊 监控报告: 成功率 {report['success_rate']:.1%}, "
            f"稳定性指数 {report['system_stability_index']:.3f}"
        )

        # 保存报告
        self.monitor.save_report()

        # 返回演化结果
        return EvolutionResult(
            success=success,
            final_quality=final_quality,
            target_quality=target_quality,
            iterations=self.current_iteration,
            execution_time=execution_time,
            path=evolution_path,
            quality_timeline=quality_timeline,
            stability_violations=stability_violations,
            strategy_used=strategy,
        )


if __name__ == "__main__":
    """沙箱管理器示例用法"""

    # 创建沙箱管理器
    sandbox = SandboxManager()

    # 设置目标质量并开始演化
    result = sandbox.evolve(
        target_quality=7.5,
        max_iterations=50,
        strategy=EvolutionStrategy.SIMULATED_ANNEALING,
    )

    print("\n📋 演化结果:")
    print(f"  成功: {result.success}")
    print(f"  最终质量: {result.final_quality:.2f}")
    print(f"  迭代次数: {result.iterations}")
    print(f"  执行时间: {result.execution_time:.2f}秒")
    print(f"  稳定性违反: {result.stability_violations}")
    print(f"  演化路径长度: {len(result.path)}")

    # 获取当前系统状态
    system_state = sandbox.get_system_state()
    print(f"\n📊 系统状态:")
    print(f"  当前卦象: {system_state.current_state}")
    print(f"  质量评分: {system_state.quality_score:.2f}/10")
    print(f"  稳定性指数: {system_state.stability_index:.3f}")
    print(f"  河图状态: {system_state.hetu_state.name}")
    print(f"  激活维度: {system_state.active_dimensions}")
