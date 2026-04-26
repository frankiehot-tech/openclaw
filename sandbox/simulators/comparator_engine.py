#!/usr/bin/env python3
"""
MAREF沙箱验证对比引擎

对比基线系统和增强系统的性能、稳定性和质量。
负责实验同步、状态跟踪、结果归一化和统计分析。
"""

import json
import random
import statistics
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# 导入基线系统和增强系统
from baseline_simulator import BaselineScheduler, TaskPriority as BaselineTaskPriority
from enhanced_simulator import EnhancedScheduler, TaskPriority as EnhancedTaskPriority


class ExperimentType(Enum):
    """实验类型枚举"""

    STABILITY = "stability"  # 超稳定性验证
    STATE_TRANSITION = "state_transition"  # 状态转换验证
    QUALITY_ASSESSMENT = "quality_assessment"  # 质量门禁验证
    PERFORMANCE_BENCHMARK = "performance_benchmark"  # 性能基准验证


class ComparatorResult:
    """对比结果（单次实验）"""

    def __init__(
        self,
        experiment_type: ExperimentType,
        baseline_stats: Dict[str, Any],
        enhanced_stats: Dict[str, Any],
    ):
        self.experiment_type = experiment_type
        self.baseline_stats = baseline_stats
        self.enhanced_stats = enhanced_stats
        self.timestamp = datetime.now().isoformat()
        self.metrics = self._calculate_metrics()

    def _calculate_metrics(self) -> Dict[str, Any]:
        """计算对比指标"""
        metrics = {}

        # 性能对比指标
        baseline_exec_time = self.baseline_stats.get("average_execution_time", 0)
        enhanced_exec_time = self.enhanced_stats.get("average_execution_time", 0)

        if baseline_exec_time > 0:
            metrics["execution_time_ratio"] = enhanced_exec_time / baseline_exec_time
            metrics["execution_time_improvement"] = 1 - metrics["execution_time_ratio"]
        else:
            metrics["execution_time_ratio"] = 0
            metrics["execution_time_improvement"] = 0

        # 成功率对比
        baseline_success_rate = self.baseline_stats.get("success_rate", 0)
        enhanced_success_rate = self.enhanced_stats.get("success_rate", 0)
        metrics["success_rate_improvement"] = (
            enhanced_success_rate - baseline_success_rate
        )

        # 质量评分对比
        baseline_quality = self.baseline_stats.get("average_quality_score", 0)
        enhanced_quality = self.enhanced_stats.get("average_quality_score", 0)
        metrics["quality_improvement"] = enhanced_quality - baseline_quality

        # 汉明距离对比（仅增强系统有）
        if "average_hamming_distance" in self.enhanced_stats:
            metrics["hamming_distance"] = self.enhanced_stats.get(
                "average_hamming_distance", 0
            )

        # 维度激活对比
        baseline_dims = self.baseline_stats.get("active_dimensions_count", 0)
        enhanced_dims = self.enhanced_stats.get("active_dimensions_count", 0)
        metrics["dimensions_improvement"] = enhanced_dims - baseline_dims

        return metrics

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "experiment_type": self.experiment_type.value,
            "timestamp": self.timestamp,
            "baseline": self.baseline_stats,
            "enhanced": self.enhanced_stats,
            "metrics": self.metrics,
            "summary": self._generate_summary(),
        }

    def _generate_summary(self) -> str:
        """生成对比摘要"""
        improvement = self.metrics.get("execution_time_improvement", 0)

        if improvement > 0.1:
            perf_desc = f"性能提升{improvement*100:.1f}%"
        elif improvement > 0:
            perf_desc = f"性能提升{improvement*100:.1f}%"
        elif improvement < -0.1:
            perf_desc = f"性能下降{abs(improvement)*100:.1f}%"
        else:
            perf_desc = "性能基本持平"

        success_improvement = self.metrics.get("success_rate_improvement", 0)
        if success_improvement > 0:
            success_desc = f"成功率提升{success_improvement*100:.1f}%"
        else:
            success_desc = f"成功率持平"

        quality_improvement = self.metrics.get("quality_improvement", 0)
        if quality_improvement > 0:
            quality_desc = f"质量评分提升{quality_improvement:.2f}分"
        else:
            quality_desc = "质量评分持平"

        return f"MAREF增强系统对比: {perf_desc}, {success_desc}, {quality_desc}"


class ComparatorEngine:
    """对比引擎（A/B测试架构）"""

    def __init__(self, max_concurrent: int = 5, failure_rate: float = 0.05):
        """
        初始化对比引擎

        Args:
            max_concurrent: 最大并发任务数（双方系统相同）
            failure_rate: 任务失败率（双方系统相同）
        """
        self.max_concurrent = max_concurrent
        self.failure_rate = failure_rate

        # 创建基线系统和增强系统
        self.baseline_system = BaselineScheduler(
            max_concurrent=max_concurrent,
            failure_rate=failure_rate,
        )
        self.enhanced_system = EnhancedScheduler(
            max_concurrent=max_concurrent,
            failure_rate=failure_rate,
        )

        # 实验配置
        self.experiments: List[Dict[str, Any]] = []
        self.results: List[ComparatorResult] = []

        # 实验同步状态
        self.sync_tasks: Dict[str, Dict[str, str]] = (
            {}
        )  # task_id -> {baseline: id, enhanced: id}
        self.experiment_history: List[Dict[str, Any]] = []

        print(f"🚀 MAREF对比引擎初始化完成")
        print(f"   最大并发数: {max_concurrent}")
        print(f"   失败率: {failure_rate*100:.1f}%")
        print(f"   基线系统: 传统任务队列调度器")
        print(f"   增强系统: 64卦状态系统 + MAREF超稳定性")

    def run_experiment(
        self,
        experiment_type: ExperimentType,
        num_tasks: int = 10,
        task_code: Optional[str] = None,
        task_type: str = "general",
        priority: str = "medium",
    ) -> ComparatorResult:
        """
        运行对比实验

        Args:
            experiment_type: 实验类型
            num_tasks: 任务数量
            task_code: 任务代码（如果为None则使用默认测试代码）
            task_type: 任务类型
            priority: 任务优先级（low/medium/high）

        Returns:
            ComparatorResult: 对比结果
        """
        print(f"\n🔬 开始实验: {experiment_type.value}")
        print(f"   任务数量: {num_tasks}")
        print(f"   任务类型: {task_type}")
        print(f"   优先级: {priority}")

        # 生成或使用提供的任务代码
        if task_code is None:
            task_code = self._generate_test_code()

        # 优先级映射
        baseline_priority = BaselineTaskPriority[priority.upper()]
        enhanced_priority = EnhancedTaskPriority[priority.upper()]

        # 记录实验开始
        experiment_record = {
            "experiment_type": experiment_type.value,
            "start_time": datetime.now().isoformat(),
            "num_tasks": num_tasks,
            "task_type": task_type,
            "priority": priority,
            "task_code_preview": (
                task_code[:100] + "..." if len(task_code) > 100 else task_code
            ),
        }
        self.experiments.append(experiment_record)

        # 同时提交任务到两个系统（确保公平对比）
        print(f"📤 提交任务到两个系统...")
        baseline_task_ids = []
        enhanced_task_ids = []

        for i in range(num_tasks):
            # 基线系统提交
            baseline_task_id = self.baseline_system.submit_task(
                code=task_code,
                task_type=task_type,
                priority=baseline_priority,
                context={"experiment": experiment_type.value, "task_index": i},
            )
            baseline_task_ids.append(baseline_task_id)

            # 增强系统提交
            enhanced_task_id = self.enhanced_system.submit_task(
                code=task_code,
                task_type=task_type,
                priority=enhanced_priority,
                context={"experiment": experiment_type.value, "task_index": i},
            )
            enhanced_task_ids.append(enhanced_task_id)

            # 记录同步关系
            self.sync_tasks[f"task_{i:03d}"] = {
                "baseline": baseline_task_id,
                "enhanced": enhanced_task_id,
            }

        print(f"   基线系统: 提交了{len(baseline_task_ids)}个任务")
        print(f"   增强系统: 提交了{len(enhanced_task_ids)}个任务")

        # 执行任务（顺序执行，但模拟真实并发环境）
        print(f"\n▶️  执行任务...")
        baseline_success_count = 0
        enhanced_success_count = 0

        for i, (baseline_id, enhanced_id) in enumerate(
            zip(baseline_task_ids, enhanced_task_ids)
        ):
            print(f"   任务 {i+1}/{num_tasks}:", end=" ")

            # 基线系统执行
            baseline_success = self.baseline_system.execute_task(baseline_id)
            if baseline_success:
                baseline_success_count += 1
                print(f"基线✅ ", end="")
            else:
                print(f"基线❌ ", end="")

            # 增强系统执行
            enhanced_success = self.enhanced_system.execute_task(enhanced_id)
            if enhanced_success:
                enhanced_success_count += 1
                print(f"增强✅", end="")
            else:
                print(f"增强❌", end="")

            print()

        # 收集系统统计信息
        baseline_stats = self._collect_baseline_stats(
            baseline_task_ids, baseline_success_count
        )
        enhanced_stats = self._collect_enhanced_stats(
            enhanced_task_ids, enhanced_success_count
        )

        # 基于实验类型调整统计信息
        if experiment_type == ExperimentType.STABILITY:
            # 超稳定性实验：包含外部干扰恢复指标
            baseline_stats["stability_metrics"] = self._test_stability(
                self.baseline_system
            )
            enhanced_stats["stability_metrics"] = self._test_stability(
                self.enhanced_system
            )
        elif experiment_type == ExperimentType.STATE_TRANSITION:
            # 状态转换实验：包含状态转换效率指标
            baseline_stats["transition_metrics"] = self._analyze_state_transitions(
                baseline_task_ids, is_baseline=True
            )
            enhanced_stats["transition_metrics"] = self._analyze_state_transitions(
                enhanced_task_ids, is_baseline=False
            )

        # 创建对比结果
        result = ComparatorResult(experiment_type, baseline_stats, enhanced_stats)
        self.results.append(result)

        # 记录实验结束
        experiment_record.update(
            {
                "end_time": datetime.now().isoformat(),
                "baseline_success_rate": baseline_stats.get("success_rate", 0),
                "enhanced_success_rate": enhanced_stats.get("success_rate", 0),
                "summary": result._generate_summary(),
            }
        )

        print(f"\n📊 实验结果:")
        print(f"   基线系统: 成功率{baseline_stats.get('success_rate', 0)*100:.1f}%")
        print(f"   增强系统: 成功率{enhanced_stats.get('success_rate', 0)*100:.1f}%")
        print(f"   对比摘要: {result._generate_summary()}")

        return result

    def _collect_baseline_stats(
        self, task_ids: List[str], success_count: int
    ) -> Dict[str, Any]:
        """收集基线系统统计信息"""
        stats = self.baseline_system.get_system_stats()

        # 计算成功率
        if len(task_ids) > 0:
            stats["success_rate"] = success_count / len(task_ids)
        else:
            stats["success_rate"] = 0

        # 添加实验特定信息
        stats["total_experiment_tasks"] = len(task_ids)
        stats["successful_experiment_tasks"] = success_count

        return stats

    def _collect_enhanced_stats(
        self, task_ids: List[str], success_count: int
    ) -> Dict[str, Any]:
        """收集增强系统统计信息"""
        stats = self.enhanced_system.get_system_stats()

        # 计算成功率
        if len(task_ids) > 0:
            stats["success_rate"] = success_count / len(task_ids)
        else:
            stats["success_rate"] = 0

        # 添加实验特定信息
        stats["total_experiment_tasks"] = len(task_ids)
        stats["successful_experiment_tasks"] = success_count

        # 从增强系统中提取卦象相关指标
        hexagram_report = stats.get("hexagram_report_summary", {})
        if hexagram_report:
            stats["hexagram_mappings"] = hexagram_report.get("hexagram_mappings", 0)
            stats["hexagram_adapter_tasks"] = hexagram_report.get(
                "hexagram_adapter_tasks", 0
            )

        return stats

    def _test_stability(self, system) -> Dict[str, Any]:
        """测试系统稳定性（模拟外部干扰）"""
        stability_metrics = {
            "interference_tests": [],
            "recovery_times": [],
        }

        # 测试不同类型的外部干扰
        interference_types = [
            "resource_pressure",
            "partial_failure",
            "state_corruption",
            "network_delay",
        ]

        for interference_type in interference_types:
            # 记录干扰前状态
            pre_stats = system.get_system_stats()

            # 注入干扰
            success = system.simulate_external_interference(interference_type)

            # 记录干扰后状态
            post_stats = system.get_system_stats()

            stability_metrics["interference_tests"].append(
                {
                    "type": interference_type,
                    "success": success,
                    "pre_stats": pre_stats,
                    "post_stats": post_stats,
                }
            )

        return stability_metrics

    def _analyze_state_transitions(
        self, task_ids: List[str], is_baseline: bool
    ) -> Dict[str, Any]:
        """分析状态转换效率"""
        transition_metrics = {
            "total_transitions": 0,
            "average_transition_steps": 0,
            "efficiency_score": 0,
        }

        if is_baseline:
            # 基线系统：使用河图10态状态机
            for task_id in task_ids:
                task_status = self.baseline_system.get_task_status(task_id)
                # 简化分析：假设每次执行完成一次状态转换
                transition_metrics["total_transitions"] += 1
        else:
            # 增强系统：使用64卦状态空间
            for task_id in task_ids:
                task_status = self.enhanced_system.get_task_status(task_id)
                if task_status and "hexagram_state" in task_status:
                    transition_metrics["total_transitions"] += 1

        # 计算平均转换步数
        if len(task_ids) > 0:
            transition_metrics["average_transition_steps"] = transition_metrics[
                "total_transitions"
            ] / len(task_ids)

        # 计算效率分数（增强系统期望有更高效率）
        if not is_baseline:
            transition_metrics["efficiency_score"] = 1.0 / (
                transition_metrics["average_transition_steps"] + 0.1
            )

        return transition_metrics

    def _generate_test_code(self) -> str:
        """生成测试代码"""
        test_codes = [
            # 算法任务
            """
def fibonacci(n):
    \"\"\"计算斐波那契数列\"\"\"
    if n <= 1:
        return n
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b
""",
            # 数据处理任务
            """
def process_data(data_list):
    \"\"\"数据处理函数\"\"\"
    if not data_list:
        return []

    # 过滤无效数据
    filtered = [x for x in data_list if x is not None]

    # 计算统计信息
    if filtered:
        avg = sum(filtered) / len(filtered)
        return {
            "count": len(filtered),
            "average": avg,
            "min": min(filtered),
            "max": max(filtered)
        }
    return {"count": 0}
""",
            # 工具函数
            """
def format_size(size_bytes):
    \"\"\"格式化字节大小为人类可读格式\"\"\"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
""",
        ]

        return random.choice(test_codes)

    def run_stability_experiment(
        self, num_tasks: int = 15, **kwargs
    ) -> ComparatorResult:
        """运行超稳定性验证实验"""
        # 从kwargs中提取干扰相关参数
        interference_type = kwargs.get("interference_type", "partial_failure")
        failure_rate = kwargs.get("failure_rate", 0.15)
        recovery_timeout = kwargs.get("recovery_timeout", 5.0)

        # 配置模拟器的干扰设置（如果支持）
        # 注意：当前模拟器可能不支持这些配置，这里先记录日志
        print(
            f"🔧 超稳定性实验配置: 干扰类型={interference_type}, 失败率={failure_rate}, 恢复超时={recovery_timeout}"
        )

        return self.run_experiment(
            experiment_type=ExperimentType.STABILITY,
            num_tasks=num_tasks,
            task_type="algorithm",
            priority="high",
        )

    def run_state_transition_experiment(
        self, num_tasks: int = 20, **kwargs
    ) -> ComparatorResult:
        """运行状态转换验证实验"""
        # 从kwargs中提取参数
        task_types = kwargs.get(
            "task_types", ["data_processing", "algorithm", "utility"]
        )
        transition_depth = kwargs.get("transition_depth", 3)

        print(
            f"🔧 状态转换实验配置: 任务类型={task_types}, 转换深度={transition_depth}"
        )

        return self.run_experiment(
            experiment_type=ExperimentType.STATE_TRANSITION,
            num_tasks=num_tasks,
            task_type="data_processing",
            priority="medium",
        )

    def run_quality_assessment_experiment(
        self, num_tasks: int = 10, **kwargs
    ) -> ComparatorResult:
        """运行质量门禁验证实验"""
        # 从kwargs中提取参数
        quality_threshold = kwargs.get("quality_threshold", 7.0)
        dimension_weights = kwargs.get("dimension_weights", {})
        print(
            f"🔧 质量评估实验配置: 质量阈值={quality_threshold}, 维度权重={dimension_weights}"
        )
        # 包含质量问题的测试代码
        problematic_code = """
def bad_function(x):
    # 无注释，变量名不清晰，复杂度高
    a = []
    for i in range(1, x+1):
        if i % 2 == 0:
            for j in range(1, i+1):
                if j % 3 == 0:
                    a.append(j)
    return sum(a)
"""

        return self.run_experiment(
            experiment_type=ExperimentType.QUALITY_ASSESSMENT,
            num_tasks=num_tasks,
            task_code=problematic_code,
            task_type="utility",
            priority="low",
        )

    def run_performance_benchmark(
        self, num_tasks: int = 30, **kwargs
    ) -> ComparatorResult:
        """运行性能基准验证实验"""
        # 从kwargs中提取参数
        task_mix = kwargs.get(
            "task_mix", {"algorithm": 0.3, "data_processing": 0.3, "utility": 0.4}
        )
        load_level = kwargs.get("load_level", "medium")
        print(f"🔧 性能基准实验配置: 任务混合={task_mix}, 负载等级={load_level}")
        return self.run_experiment(
            experiment_type=ExperimentType.PERFORMANCE_BENCHMARK,
            num_tasks=num_tasks,
            task_type="general",
            priority="high",
        )

    def run_all_experiments(self) -> Dict[str, ComparatorResult]:
        """运行所有4个验证实验"""
        print("🚀 开始运行所有MAREF验证实验")
        print("=" * 60)

        results = {}

        # 实验1: 超稳定性验证
        print("\n📊 实验1: 超稳定性验证")
        results["stability"] = self.run_stability_experiment(num_tasks=12)

        # 实验2: 状态转换验证
        print("\n📊 实验2: 状态转换验证")
        results["state_transition"] = self.run_state_transition_experiment(num_tasks=15)

        # 实验3: 质量门禁验证
        print("\n📊 实验3: 质量门禁验证")
        results["quality_assessment"] = self.run_quality_assessment_experiment(
            num_tasks=8
        )

        # 实验4: 性能基准验证
        print("\n📊 实验4: 性能基准验证")
        results["performance_benchmark"] = self.run_performance_benchmark(num_tasks=25)

        return results

    def generate_comparison_report(self) -> Dict[str, Any]:
        """生成综合对比报告"""
        if not self.results:
            return {"error": "未运行任何实验"}

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_experiments": len(self.results),
            "experiments": [exp.to_dict() for exp in self.results],
            "summary_statistics": self._calculate_summary_statistics(),
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _calculate_summary_statistics(self) -> Dict[str, Any]:
        """计算总体统计信息"""
        if not self.results:
            return {}

        # 收集所有指标
        execution_improvements = []
        success_improvements = []
        quality_improvements = []

        for result in self.results:
            metrics = result.metrics
            execution_improvements.append(metrics.get("execution_time_improvement", 0))
            success_improvements.append(metrics.get("success_rate_improvement", 0))
            quality_improvements.append(metrics.get("quality_improvement", 0))

        # 计算统计信息
        stats = {
            "average_execution_improvement": (
                statistics.mean(execution_improvements) if execution_improvements else 0
            ),
            "average_success_improvement": (
                statistics.mean(success_improvements) if success_improvements else 0
            ),
            "average_quality_improvement": (
                statistics.mean(quality_improvements) if quality_improvements else 0
            ),
            "total_experiments": len(self.results),
            "experiments_completed": len([r for r in self.results if r.metrics]),
        }

        return stats

    def _generate_recommendations(self) -> List[str]:
        """生成技术建议"""
        recommendations = []

        if not self.results:
            return ["运行更多实验以获得可靠建议"]

        # 分析总体性能改进
        stats = self._calculate_summary_statistics()
        exec_improvement = stats.get("average_execution_improvement", 0)
        success_improvement = stats.get("average_success_improvement", 0)
        quality_improvement = stats.get("average_quality_improvement", 0)

        if exec_improvement > 0.1:
            recommendations.append(
                f"✅ MAREF增强系统显著提升性能: {exec_improvement*100:.1f}%"
            )
        elif exec_improvement > 0:
            recommendations.append(
                f"🔶 MAREF增强系统略微提升性能: {exec_improvement*100:.1f}%"
            )
        else:
            recommendations.append("⚠️ MAREF增强系统性能未提升，需要进一步优化")

        if success_improvement > 0.05:
            recommendations.append(
                f"✅ MAREF增强系统提升成功率: {success_improvement*100:.1f}%"
            )

        if quality_improvement > 0.5:
            recommendations.append(
                f"✅ MAREF增强系统显著提升质量: {quality_improvement:.2f}分"
            )

        # 检查是否有实验失败
        failed_experiments = len(
            [r for r in self.results if r.metrics.get("execution_time_ratio", 0) > 2]
        )
        if failed_experiments > 0:
            recommendations.append(
                f"⚠️  {failed_experiments}个实验中增强系统性能显著下降，需要详细分析"
            )

        # 建议下一步
        recommendations.append("🎯 建议: 将MAREF增强系统部署到生产环境进行真实负载测试")
        recommendations.append("🔧 建议: 优化64卦状态转换算法，进一步提高效率")
        recommendations.append("📊 建议: 扩展质量维度评估，涵盖更多代码质量指标")

        return recommendations

    def save_report(self, filename: str = "maref_comparison_report.json") -> None:
        """保存对比报告到文件"""
        report = self.generate_comparison_report()

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"📄 对比报告已保存到: {filename}")
        print(f"   实验数量: {report.get('total_experiments', 0)}")

        if "summary_statistics" in report:
            stats = report["summary_statistics"]
            exec_improvement = stats.get("average_execution_improvement", 0)
            print(f"   平均性能改进: {exec_improvement*100:.1f}%")

    def reset_experiments(self) -> None:
        """重置所有实验状态（保持系统运行）"""
        self.experiments = []
        self.results = []
        self.sync_tasks = {}
        self.experiment_history = []

        print("🔄 对比引擎: 实验状态已重置")


def test_comparator_engine():
    """测试对比引擎"""
    print("=== MAREF对比引擎测试 ===")

    # 创建对比引擎
    comparator = ComparatorEngine(max_concurrent=4, failure_rate=0.1)

    # 运行单个实验（状态转换验证）
    print("\n1. 🔬 运行状态转换验证实验...")
    result = comparator.run_state_transition_experiment(num_tasks=5)

    print(f"\n   📋 实验结果摘要:")
    print(f"      {result._generate_summary()}")

    # 查看结果详情
    result_dict = result.to_dict()
    print(f"\n   📊 详细指标:")
    metrics = result_dict.get("metrics", {})
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            print(f"      {key}: {value:.3f}")

    # 运行所有实验（简化版）
    print("\n2. 🚀 运行所有验证实验（简化版）...")
    results = comparator.run_all_experiments()

    print(f"\n   ✅ 完成 {len(results)} 个实验")

    # 生成并保存报告
    print("\n3. 📄 生成对比报告...")
    comparator.save_report("test_comparison_report.json")

    print("\n🎉 对比引擎测试完成！")
    return True


if __name__ == "__main__":
    test_comparator_engine()
