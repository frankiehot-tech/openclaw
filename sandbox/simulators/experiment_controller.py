#!/usr/bin/env python3
"""
MAREF沙箱实验控制脚本

实验控制脚本用于批量运行验证实验，自动化收集和分析结果数据。
支持4个验证实验：超稳定性、状态转换、质量门禁、性能基准。

功能：
1. 实验配置管理
2. 批量实验运行
3. 结果收集和存储
4. 报告生成
5. 错误处理和重试
"""

import json
import os
import random
import sys
import time
import statistics
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 导入对比引擎和模拟器
from comparator_engine import ComparatorEngine, ExperimentType
from baseline_simulator import BaselineScheduler, TaskPriority as BaselineTaskPriority
from enhanced_simulator import EnhancedScheduler, TaskPriority as EnhancedTaskPriority
from simple_monitor import SimpleMonitor, MetricType, MetricCategory


class ExperimentConfig:
    """实验配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化实验配置

        Args:
            config_file: 配置文件路径，如为None则使用默认配置
        """
        self.default_config = {
            # 实验参数
            "experiments": {
                "stability": {
                    "enabled": True,
                    "iterations": 10,
                    "interference_types": [
                        "resource_pressure",
                        "partial_failure",
                        "state_corruption",
                        "network_delay",
                    ],
                    "interference_rate": 0.15,  # 15%失败率
                    "recovery_timeout": 5.0,  # 恢复超时（秒）
                },
                "state_transition": {
                    "enabled": True,
                    "iterations": 50,
                    "num_tasks": 100,
                    "task_types": [
                        "algorithm",
                        "data_processing",
                        "utility",
                        "general",
                    ],
                    "priority_distribution": {"LOW": 0.2, "MEDIUM": 0.6, "HIGH": 0.2},
                },
                "quality_assessment": {
                    "enabled": True,
                    "iterations": 5,
                    "num_samples": 200,
                    "quality_dimensions": [
                        "correctness",
                        "complexity",
                        "style",
                        "readability",
                        "maintainability",
                        "cost_efficiency",
                    ],
                    "validation_method": "cross_validation",
                },
                "performance_benchmark": {
                    "enabled": True,
                    "iterations": 3,
                    "load_levels": [10, 50, 100, 200],  # 任务/分钟
                    "duration_per_level": 30,  # 秒
                    "concurrent_configs": [5, 10, 20],  # 并发配置
                },
            },
            # 系统配置
            "system": {
                "max_concurrent": 5,
                "failure_rate": 0.05,
                "output_dir": "./experiment_results",
                "report_format": "json",
                "log_level": "INFO",
            },
            # 监控配置
            "monitoring": {
                "metrics_collection_interval": 5,  # 秒
                "enable_prometheus": False,
                "enable_grafana_dashboard": False,
                "save_state_history": True,
            },
        }

        if config_file and os.path.exists(config_file):
            with open(config_file, "r") as f:
                user_config = json.load(f)
                self._merge_configs(self.default_config, user_config)

        self.config = self.default_config

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """递归合并配置字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def get_experiment_config(self, experiment_type: ExperimentType) -> Dict[str, Any]:
        """获取指定实验类型的配置"""
        exp_type_str = experiment_type.value
        if exp_type_str in self.config["experiments"]:
            return self.config["experiments"][exp_type_str]
        return {}

    def get_system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self.config["system"]

    def get_monitoring_config(self) -> Dict[str, Any]:
        """获取监控配置"""
        return self.config["monitoring"]


class ExperimentRunner:
    """实验运行器"""

    def __init__(self, config: ExperimentConfig):
        """
        初始化实验运行器

        Args:
            config: 实验配置管理器
        """
        self.config = config
        self.comparator = ComparatorEngine()
        self.results: List[Dict[str, Any]] = []

        # 创建输出目录
        output_dir = config.get_system_config().get(
            "output_dir", "./experiment_results"
        )
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir

        # 初始化日志
        self._init_logging()

        # 初始化监控器
        self.monitor = None
        self._init_monitoring()

    def _init_logging(self) -> None:
        """初始化日志系统"""
        log_file = os.path.join(
            self.output_dir,
            f"experiment_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        self.log_file = log_file

        # 简单的文件日志
        self._log(f"🚀 MAREF沙箱实验开始于 {datetime.now().isoformat()}")
        self._log(f"   输出目录: {self.output_dir}")

    def _init_monitoring(self) -> None:
        """初始化监控器"""
        monitoring_config = self.config.get_monitoring_config()

        # 从配置获取监控参数
        collection_interval = monitoring_config.get("metrics_collection_interval", 5)
        retention_period = monitoring_config.get("retention_period", 300)  # 5分钟

        # 初始化监控器
        self.monitor = SimpleMonitor(
            retention_period=retention_period, collection_interval=collection_interval
        )

        # 注册实验特定指标
        self._register_experiment_metrics()

        self._log(
            f"监控器初始化完成 (间隔: {collection_interval}秒, 保留: {retention_period}秒)"
        )

    def _register_experiment_metrics(self) -> None:
        """注册实验特定指标"""
        if not self.monitor:
            return

        # 实验执行指标
        self.monitor.register_metric(
            "experiment.duration",
            MetricType.APPLICATION,
            MetricCategory.GAUGE,
            description="实验执行时长",
            unit="seconds",
            min_value=0,
        )
        self.monitor.register_metric(
            "experiment.success_rate",
            MetricType.APPLICATION,
            MetricCategory.GAUGE,
            description="实验成功率",
            unit="percent",
            min_value=0,
            max_value=100,
        )
        self.monitor.register_metric(
            "experiment.task_completed",
            MetricType.BUSINESS,
            MetricCategory.COUNTER,
            description="完成任务数量",
            unit="tasks",
            min_value=0,
        )
        self.monitor.register_metric(
            "experiment.task_failed",
            MetricType.BUSINESS,
            MetricCategory.COUNTER,
            description="失败任务数量",
            unit="tasks",
            min_value=0,
        )

        # 性能指标
        self.monitor.register_metric(
            "performance.latency",
            MetricType.APPLICATION,
            MetricCategory.GAUGE,
            description="平均延迟",
            unit="seconds",
            min_value=0,
        )
        self.monitor.register_metric(
            "performance.throughput",
            MetricType.APPLICATION,
            MetricCategory.GAUGE,
            description="吞吐量",
            unit="tasks/second",
            min_value=0,
        )

        # 系统指标（通过监控器自动收集）
        # 注册一些自定义告警
        self.monitor.register_alert(
            "high_failure_rate",
            "experiment.success_rate",
            "below",
            80.0,
            severity="warning",
            description="实验成功率低于80%",
        )
        self.monitor.register_alert(
            "high_latency",
            "performance.latency",
            "above",
            2.0,
            severity="warning",
            description="平均延迟超过2秒",
        )
        self.monitor.register_alert(
            "low_throughput",
            "performance.throughput",
            "below",
            10.0,
            severity="warning",
            description="吞吐量低于10任务/秒",
        )

    def _log(self, message: str, level: str = "INFO") -> None:
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"

        # 输出到控制台
        print(log_entry)

        # 写入日志文件
        with open(self.log_file, "a") as f:
            f.write(log_entry + "\n")

    def _start_monitoring(self) -> bool:
        """启动监控器"""
        if not self.monitor:
            self._log("监控器未初始化，跳过启动", level="WARNING")
            return False

        if self.monitor.is_running:
            self._log("监控器已在运行中", level="INFO")
            return True

        success = self.monitor.start_monitoring()
        if success:
            self._log("监控器已启动")

        return success

    def _stop_monitoring(self) -> bool:
        """停止监控器"""
        if not self.monitor:
            return False

        if not self.monitor.is_running:
            return True

        try:
            # 导出监控数据
            export_dir = os.path.join(self.output_dir, "monitoring_data")
            export_path = self.monitor.export_metrics(export_dir)
            self._log(f"监控数据已导出: {export_path}")
        except Exception as e:
            self._log(f"导出监控数据时出错: {e}", level="ERROR")

        success = self.monitor.stop_monitoring()
        if success:
            self._log("监控器已停止")

        return success

    def _collect_monitoring_data(self) -> Dict[str, Any]:
        """收集监控数据"""
        if not self.monitor:
            return {}

        monitoring_data = {
            "monitor_metrics": {},
            "monitor_alerts": [],
            "monitor_statistics": {},
            "monitor_report": {},
        }

        try:
            # 收集关键指标
            key_metrics = [
                "experiment.duration",
                "experiment.success_rate",
                "performance.latency",
                "performance.throughput",
                "system.cpu_usage",
                "system.memory_usage",
            ]

            for metric_name in key_metrics:
                metric_data = self.monitor.get_metric(metric_name)
                if metric_data:
                    monitoring_data["monitor_metrics"][metric_name] = metric_data

                    # 收集统计信息
                    stats = self.monitor.get_metric_statistics(metric_name, window=60)
                    if stats:
                        monitoring_data["monitor_statistics"][metric_name] = stats

            # 收集告警信息
            for alert_name, alert_config in self.monitor.alerts.items():
                if alert_config.get("last_triggered"):
                    monitoring_data["monitor_alerts"].append(
                        {
                            "name": alert_name,
                            "metric": alert_config.get("metric"),
                            "severity": alert_config.get("severity"),
                            "last_triggered": alert_config.get("last_triggered"),
                            "trigger_count": alert_config.get("trigger_count", 0),
                            "description": alert_config.get("description", ""),
                        }
                    )

            # 生成监控报告
            monitoring_data["monitor_report"] = (
                self.monitor.generate_monitoring_report()
            )

        except Exception as e:
            self._log(f"收集监控数据时出错: {e}", level="ERROR")

        return monitoring_data

    def run_experiment(
        self, experiment_type: ExperimentType, **kwargs
    ) -> Dict[str, Any]:
        """
        运行单个实验

        Args:
            experiment_type: 实验类型
            **kwargs: 实验特定参数

        Returns:
            实验结果字典
        """
        self._log(f"开始实验: {experiment_type.value}")

        start_time = time.time()

        # 启动监控器
        monitoring_started = self._start_monitoring()
        if monitoring_started:
            self._log("实验监控已启用")

        try:
            if experiment_type == ExperimentType.STABILITY:
                result = self._run_stability_experiment(**kwargs)
            elif experiment_type == ExperimentType.STATE_TRANSITION:
                result = self._run_state_transition_experiment(**kwargs)
            elif experiment_type == ExperimentType.QUALITY_ASSESSMENT:
                result = self._run_quality_assessment_experiment(**kwargs)
            elif experiment_type == ExperimentType.PERFORMANCE_BENCHMARK:
                result = self._run_performance_benchmark_experiment(**kwargs)
            else:
                raise ValueError(f"未知的实验类型: {experiment_type}")

            result["experiment_type"] = experiment_type.value
            result["duration_seconds"] = time.time() - start_time
            result["success"] = True

            # 收集监控数据
            if monitoring_started:
                monitoring_data = self._collect_monitoring_data()
                result["monitoring_data"] = monitoring_data
                self._log(
                    f"监控数据收集完成: {len(monitoring_data.get('monitor_alerts', []))} 个告警"
                )

            self.results.append(result)
            self._log(
                f"实验 {experiment_type.value} 完成，耗时 {result['duration_seconds']:.2f} 秒"
            )

            # 保存中间结果
            self._save_intermediate_results()

            return result

        except Exception as e:
            error_result = {
                "experiment_type": experiment_type.value,
                "duration_seconds": time.time() - start_time,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat(),
            }

            # 即使是错误，也收集监控数据
            if monitoring_started:
                monitoring_data = self._collect_monitoring_data()
                error_result["monitoring_data"] = monitoring_data

            self.results.append(error_result)
            self._log(f"实验 {experiment_type.value} 失败: {e}", level="ERROR")

            return error_result

        finally:
            # 确保监控器停止
            if monitoring_started:
                self._stop_monitoring()

    def _run_stability_experiment(self, **kwargs) -> Dict[str, Any]:
        """运行超稳定性实验"""
        exp_config = self.config.get_experiment_config(ExperimentType.STABILITY)

        # 从配置或参数获取设置
        iterations = kwargs.get("iterations", exp_config.get("iterations", 10))
        interference_types = kwargs.get(
            "interference_types", exp_config.get("interference_types", [])
        )

        self._log(f"运行超稳定性实验: {iterations} 次迭代")

        all_results = []
        for i in range(iterations):
            interference_type = (
                random.choice(interference_types)
                if interference_types
                else "partial_failure"
            )

            # 使用对比引擎运行实验
            comparator_result = self.comparator.run_stability_experiment(
                interference_type=interference_type,
                failure_rate=exp_config.get("interference_rate", 0.15),
                recovery_timeout=exp_config.get("recovery_timeout", 5.0),
            )

            experiment_result = {
                "iteration": i + 1,
                "interference_type": interference_type,
                "baseline_stats": comparator_result.baseline_stats,
                "enhanced_stats": comparator_result.enhanced_stats,
                "comparison_metrics": comparator_result.metrics,
                "timestamp": datetime.now().isoformat(),
            }

            all_results.append(experiment_result)

            # 进度日志
            if (i + 1) % 5 == 0 or i == 0 or i == iterations - 1:
                recovery_ratio = comparator_result.metrics.get(
                    "recovery_time_ratio", 1.0
                )
                self._log(
                    f"  迭代 {i + 1}/{iterations}: {interference_type}, 恢复时间比: {recovery_ratio:.2f}"
                )

        return {
            "summary": {
                "total_iterations": iterations,
                "interference_types_used": interference_types,
                "avg_recovery_time_ratio": statistics.mean(
                    [
                        r["comparison_metrics"].get("recovery_time_ratio", 1.0)
                        for r in all_results
                        if "comparison_metrics" in r
                    ]
                ),
                "success_rate": sum(1 for r in all_results if "comparison_metrics" in r)
                / len(all_results),
            },
            "detailed_results": all_results,
        }

    def _run_state_transition_experiment(self, **kwargs) -> Dict[str, Any]:
        """运行状态转换实验"""
        exp_config = self.config.get_experiment_config(ExperimentType.STATE_TRANSITION)

        iterations = kwargs.get("iterations", exp_config.get("iterations", 50))
        num_tasks = kwargs.get("num_tasks", exp_config.get("num_tasks", 100))

        self._log(f"运行状态转换实验: {iterations} 次迭代, {num_tasks} 任务/次")

        all_results = []
        for i in range(iterations):
            comparator_result = self.comparator.run_state_transition_experiment(
                num_tasks=num_tasks,
                task_types=exp_config.get("task_types", ["general"]),
                priority_distribution=exp_config.get(
                    "priority_distribution", {"LOW": 0.2, "MEDIUM": 0.6, "HIGH": 0.2}
                ),
            )

            experiment_result = {
                "iteration": i + 1,
                "num_tasks": num_tasks,
                "baseline_stats": comparator_result.baseline_stats,
                "enhanced_stats": comparator_result.enhanced_stats,
                "comparison_metrics": comparator_result.metrics,
                "timestamp": datetime.now().isoformat(),
            }

            all_results.append(experiment_result)

            # 进度日志
            if (i + 1) % 10 == 0 or i == 0 or i == iterations - 1:
                transition_steps_ratio = comparator_result.metrics.get(
                    "transition_steps_ratio", 1.0
                )
                self._log(
                    f"  迭代 {i + 1}/{iterations}: 转换步数比: {transition_steps_ratio:.2f}"
                )

        return {
            "summary": {
                "total_iterations": iterations,
                "total_tasks": iterations * num_tasks,
                "avg_transition_steps_ratio": statistics.mean(
                    [
                        r["comparison_metrics"].get("transition_steps_ratio", 1.0)
                        for r in all_results
                        if "comparison_metrics" in r
                    ]
                ),
                "avg_success_rate_ratio": statistics.mean(
                    [
                        r["comparison_metrics"].get("success_rate_ratio", 1.0)
                        for r in all_results
                        if "comparison_metrics" in r
                    ]
                ),
            },
            "detailed_results": all_results,
        }

    def _run_quality_assessment_experiment(self, **kwargs) -> Dict[str, Any]:
        """运行质量门禁实验"""
        exp_config = self.config.get_experiment_config(
            ExperimentType.QUALITY_ASSESSMENT
        )

        iterations = kwargs.get("iterations", exp_config.get("iterations", 5))
        num_samples = kwargs.get("num_samples", exp_config.get("num_samples", 200))

        self._log(f"运行质量门禁实验: {iterations} 次迭代, {num_samples} 样本/次")

        # 加载测试代码样本（这里使用模拟样本）
        test_samples = self._generate_test_code_samples(num_samples)

        all_results = []
        for i in range(iterations):
            comparator_result = self.comparator.run_quality_assessment_experiment(
                code_samples=test_samples,
                quality_dimensions=exp_config.get("quality_dimensions", []),
                validation_method=exp_config.get(
                    "validation_method", "cross_validation"
                ),
            )

            experiment_result = {
                "iteration": i + 1,
                "num_samples": num_samples,
                "baseline_stats": comparator_result.baseline_stats,
                "enhanced_stats": comparator_result.enhanced_stats,
                "comparison_metrics": comparator_result.metrics,
                "timestamp": datetime.now().isoformat(),
            }

            all_results.append(experiment_result)

            # 进度日志
            if (i + 1) % 2 == 0 or i == 0 or i == iterations - 1:
                accuracy_ratio = comparator_result.metrics.get("accuracy_ratio", 1.0)
                self._log(
                    f"  迭代 {i + 1}/{iterations}: 准确率比: {accuracy_ratio:.2f}"
                )

        return {
            "summary": {
                "total_iterations": iterations,
                "total_samples": iterations * num_samples,
                "avg_accuracy_ratio": statistics.mean(
                    [
                        r["comparison_metrics"].get("accuracy_ratio", 1.0)
                        for r in all_results
                        if "comparison_metrics" in r
                    ]
                ),
                "avg_defect_detection_ratio": statistics.mean(
                    [
                        r["comparison_metrics"].get("defect_detection_ratio", 1.0)
                        for r in all_results
                        if "comparison_metrics" in r
                    ]
                ),
            },
            "detailed_results": all_results,
        }

    def _run_performance_benchmark_experiment(self, **kwargs) -> Dict[str, Any]:
        """运行性能基准实验"""
        exp_config = self.config.get_experiment_config(
            ExperimentType.PERFORMANCE_BENCHMARK
        )

        iterations = kwargs.get("iterations", exp_config.get("iterations", 3))
        load_levels = kwargs.get(
            "load_levels", exp_config.get("load_levels", [10, 50, 100, 200])
        )

        self._log(f"运行性能基准实验: {iterations} 次迭代, {len(load_levels)} 负载级别")

        all_results = []
        for i in range(iterations):
            load_level_results = []

            for load_level in load_levels:
                comparator_result = self.comparator.run_performance_benchmark(
                    load_level=load_level,
                    duration=exp_config.get("duration_per_level", 30),
                    concurrent_configs=exp_config.get("concurrent_configs", [5]),
                )

                load_result = {
                    "load_level": load_level,
                    "baseline_stats": comparator_result.baseline_stats,
                    "enhanced_stats": comparator_result.enhanced_stats,
                    "comparison_metrics": comparator_result.metrics,
                }
                load_level_results.append(load_result)

                throughput_ratio = comparator_result.metrics.get(
                    "throughput_ratio", 1.0
                )
                self._log(
                    f"    负载 {load_level} 任务/分钟: 吞吐量比 {throughput_ratio:.2f}"
                )

            experiment_result = {
                "iteration": i + 1,
                "load_levels": load_levels,
                "load_results": load_level_results,
                "timestamp": datetime.now().isoformat(),
            }

            all_results.append(experiment_result)

        # 计算汇总统计
        summary_metrics = {}
        for metric in ["throughput_ratio", "latency_ratio", "stability_ratio"]:
            all_values = []
            for iteration_result in all_results:
                for load_result in iteration_result["load_results"]:
                    if metric in load_result["comparison_metrics"]:
                        all_values.append(load_result["comparison_metrics"][metric])

            if all_values:
                summary_metrics[f"avg_{metric}"] = statistics.mean(all_values)
                summary_metrics[f"median_{metric}"] = statistics.median(all_values)

        return {
            "summary": {
                "total_iterations": iterations,
                "load_levels_tested": load_levels,
                **summary_metrics,
            },
            "detailed_results": all_results,
        }

    def _generate_test_code_samples(self, num_samples: int) -> List[str]:
        """生成测试代码样本（模拟函数）"""
        samples = []

        # 简单函数模板
        templates = [
            # 斐波那契数列
            "def fibonacci(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for i in range(2, n + 1):\n        a, b = b, a + b\n    return b",
            # 排序函数
            "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n - i - 1):\n            if arr[j] > arr[j + 1]:\n                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n    return arr",
            # 字符串处理
            "def count_words(text):\n    words = text.split()\n    word_count = {}\n    for word in words:\n        word = word.lower().strip('.,!?')\n        if word:\n            word_count[word] = word_count.get(word, 0) + 1\n    return word_count",
            # 文件操作模拟
            "def process_data(file_path):\n    data = []\n    try:\n        with open(file_path, 'r') as f:\n            for line in f:\n                if line.strip():\n                    data.append(float(line.strip()))\n    except FileNotFoundError:\n        return []\n    return sum(data) / len(data) if data else 0.0",
            # 网络请求模拟
            "def fetch_url(url, timeout=5):\n    import urllib.request\n    try:\n        with urllib.request.urlopen(url, timeout=timeout) as response:\n            return response.read().decode('utf-8')\n    except Exception as e:\n        print(f'Error fetching {url}: {e}')\n        return ''",
        ]

        for i in range(num_samples):
            # 随机选择一个模板并稍微修改
            template = random.choice(templates)
            # 简单修改以生成多样性
            modified = template.replace("def fibonacci", f"def fibonacci_{i}")
            samples.append(modified)

        return samples

    def _save_intermediate_results(self) -> None:
        """保存中间结果到文件"""
        if not self.results:
            return

        result_file = os.path.join(
            self.output_dir,
            f"intermediate_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

        with open(result_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "results": self.results,
                    "metadata": {
                        "total_experiments": len(self.results),
                        "successful_experiments": sum(
                            1 for r in self.results if r.get("success", False)
                        ),
                    },
                },
                f,
                indent=2,
            )

        self._log(f"中间结果已保存到: {result_file}")

    def generate_final_report(self) -> str:
        """生成最终实验报告"""
        self._log("生成最终实验报告...")

        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "experiment_controller_version": "1.0.0",
                "total_experiments": len(self.results),
                "successful_experiments": sum(
                    1 for r in self.results if r.get("success", False)
                ),
                "failed_experiments": sum(
                    1 for r in self.results if not r.get("success", False)
                ),
            },
            "experiment_summary": [],
            "overall_findings": {},
            "recommendations": [],
        }

        # 按实验类型汇总
        experiment_type_results = {}
        for result in self.results:
            exp_type = result.get("experiment_type")
            if exp_type not in experiment_type_results:
                experiment_type_results[exp_type] = []
            experiment_type_results[exp_type].append(result)

        # 生成各实验摘要
        for exp_type, results in experiment_type_results.items():
            successful_results = [r for r in results if r.get("success", False)]

            if not successful_results:
                continue

            # 提取关键指标
            key_metrics = {}
            for result in successful_results:
                if "summary" in result:
                    for key, value in result["summary"].items():
                        if isinstance(value, (int, float)):
                            if key not in key_metrics:
                                key_metrics[key] = []
                            key_metrics[key].append(value)

            # 计算统计
            summary_stats = {}
            for key, values in key_metrics.items():
                if values:
                    summary_stats[f"avg_{key}"] = statistics.mean(values)
                    summary_stats[f"min_{key}"] = min(values)
                    summary_stats[f"max_{key}"] = max(values)

            report["experiment_summary"].append(
                {
                    "experiment_type": exp_type,
                    "total_runs": len(results),
                    "successful_runs": len(successful_results),
                    "success_rate": len(successful_results) / len(results),
                    "key_metrics": summary_stats,
                }
            )

        # 生成整体发现
        overall_metrics = {}
        for exp_summary in report["experiment_summary"]:
            for key, value in exp_summary.get("key_metrics", {}).items():
                if key.startswith("avg_"):
                    metric_name = key[4:]  # 移除"avg_"
                    if metric_name.endswith("_ratio"):
                        overall_metrics[metric_name] = overall_metrics.get(
                            metric_name, []
                        ) + [value]

        # 计算整体性能提升
        performance_improvements = {}
        for metric, values in overall_metrics.items():
            if values:
                performance_improvements[f"median_{metric}"] = statistics.median(values)

        report["overall_findings"] = {
            "performance_improvements": performance_improvements,
            "stability_improvement": performance_improvements.get(
                "median_recovery_time_ratio", 1.0
            ),
            "quality_assessment_improvement": performance_improvements.get(
                "median_accuracy_ratio", 1.0
            ),
            "state_transition_efficiency": performance_improvements.get(
                "median_transition_steps_ratio", 1.0
            ),
            "throughput_improvement": performance_improvements.get(
                "median_throughput_ratio", 1.0
            ),
        }

        # 生成建议
        findings = report["overall_findings"]

        if findings.get("stability_improvement", 1.0) < 0.8:
            report["recommendations"].append(
                "增强系统在超稳定性方面表现优异（恢复时间比 < 0.8），建议在生产环境中采用MAREF超稳定性原则。"
            )

        if findings.get("state_transition_efficiency", 1.0) < 0.9:
            report["recommendations"].append(
                "64卦状态系统的格雷编码转换显著提高了状态转换效率，建议在所有状态管理中采用此方法。"
            )

        if findings.get("quality_assessment_improvement", 1.0) > 1.1:
            report["recommendations"].append(
                "增强系统的质量评估准确率明显更高，建议将64卦质量维度评估纳入代码审查流程。"
            )

        if findings.get("throughput_improvement", 1.0) > 1.05:
            report["recommendations"].append(
                "MAREF增强系统在吞吐量上有显著提升，建议进行大规模部署以验证扩展性。"
            )

        # 保存报告
        report_file = os.path.join(
            self.output_dir,
            f"final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        # 生成可读摘要
        summary_file = os.path.join(
            self.output_dir,
            f"report_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        with open(summary_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("MAREF沙箱验证实验最终报告\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"报告生成时间: {report['metadata']['generated_at']}\n")
            f.write(f"总实验次数: {report['metadata']['total_experiments']}\n")
            f.write(f"成功实验: {report['metadata']['successful_experiments']}\n")
            f.write(f"失败实验: {report['metadata']['failed_experiments']}\n\n")

            f.write("-" * 80 + "\n")
            f.write("各实验类型汇总:\n")
            f.write("-" * 80 + "\n")

            for exp_summary in report["experiment_summary"]:
                f.write(f"\n{exp_summary['experiment_type'].upper()}:\n")
                f.write(
                    f"  运行次数: {exp_summary['total_runs']} (成功率: {exp_summary['success_rate']*100:.1f}%)\n"
                )
                for key, value in exp_summary.get("key_metrics", {}).items():
                    if key.startswith("avg_"):
                        f.write(f"  {key}: {value:.3f}\n")

            f.write("\n" + "-" * 80 + "\n")
            f.write("关键发现:\n")
            f.write("-" * 80 + "\n")

            for key, value in report["overall_findings"].items():
                if isinstance(value, (int, float)):
                    f.write(f"  {key}: {value:.3f}\n")
                elif isinstance(value, dict):
                    f.write(f"  {key}:\n")
                    for subkey, subvalue in value.items():
                        f.write(f"    {subkey}: {subvalue:.3f}\n")

            f.write("\n" + "-" * 80 + "\n")
            f.write("建议:\n")
            f.write("-" * 80 + "\n")

            for i, recommendation in enumerate(report["recommendations"], 1):
                f.write(f"{i}. {recommendation}\n")

            f.write("\n" + "=" * 80 + "\n")

        self._log(f"最终报告已生成: {report_file}")
        self._log(f"报告摘要: {summary_file}")

        return report_file


def main():
    """主函数：批量运行所有实验"""
    import argparse

    parser = argparse.ArgumentParser(description="MAREF沙箱实验控制器")
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument(
        "--experiment",
        "-e",
        choices=[
            "all",
            "stability",
            "state_transition",
            "quality_assessment",
            "performance_benchmark",
        ],
        default="all",
        help="要运行的实验类型",
    )
    parser.add_argument("--output-dir", "-o", help="输出目录")
    parser.add_argument("--iterations", "-i", type=int, help="实验迭代次数（覆盖配置）")
    parser.add_argument("--no-report", action="store_true", help="不生成最终报告")

    args = parser.parse_args()

    # 初始化配置
    config = ExperimentConfig(args.config)

    # 覆盖配置
    if args.output_dir:
        config.config["system"]["output_dir"] = args.output_dir

    # 初始化实验运行器
    runner = ExperimentRunner(config)

    # 确定要运行的实验
    experiments_to_run = []
    if args.experiment == "all":
        for exp_type in ExperimentType:
            exp_config = config.get_experiment_config(exp_type)
            if exp_config.get("enabled", True):
                experiments_to_run.append(exp_type)
    else:
        experiment_map = {
            "stability": ExperimentType.STABILITY,
            "state_transition": ExperimentType.STATE_TRANSITION,
            "quality_assessment": ExperimentType.QUALITY_ASSESSMENT,
            "performance_benchmark": ExperimentType.PERFORMANCE_BENCHMARK,
        }
        if args.experiment in experiment_map:
            experiments_to_run.append(experiment_map[args.experiment])

    # 运行实验
    for exp_type in experiments_to_run:
        kwargs = {}
        if args.iterations:
            kwargs["iterations"] = args.iterations

        runner.run_experiment(exp_type, **kwargs)

    # 生成最终报告
    if not args.no_report and runner.results:
        report_file = runner.generate_final_report()
        print(f"\n✅ 实验完成！最终报告: {report_file}")
    else:
        print(f"\n✅ 实验完成！共运行 {len(runner.results)} 个实验")

    # 总结
    successful = sum(1 for r in runner.results if r.get("success", False))
    print(f"   成功: {successful}, 失败: {len(runner.results) - successful}")


if __name__ == "__main__":
    main()
