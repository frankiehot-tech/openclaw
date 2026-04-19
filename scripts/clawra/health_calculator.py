#!/usr/bin/env python3
"""
MAREF智能体健康度计算器
基于实际性能指标动态计算智能体健康度

健康度指标:
1. 响应时间: 智能体响应请求的时间 (权重: 0.3)
2. 成功率: 任务执行成功率 (权重: 0.4)
3. 资源使用: CPU/内存使用率 (权重: 0.2)
4. 可用性: 智能体在线状态 (权重: 0.1)
"""

import logging
import statistics
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentHealthCalculator:
    """
    智能体健康度计算器

    基于实际性能指标计算智能体健康度分数 (0.0-1.0)
    """

    def __init__(self, history_window_hours: int = 24):
        """
        初始化健康度计算器

        Args:
            history_window_hours: 历史数据窗口（小时）
        """
        self.history_window_hours = history_window_hours

        # 指标权重配置
        self.metrics_weights = {
            "response_time": 0.3,  # 响应时间权重
            "success_rate": 0.4,  # 成功率权重
            "resource_usage": 0.2,  # 资源使用权重
            "availability": 0.1,  # 可用性权重
        }

        # 指标阈值配置
        self.metrics_thresholds = {
            "response_time": {
                "excellent": 0.1,  # < 0.1秒: 优秀
                "good": 0.5,  # 0.1-0.5秒: 良好
                "fair": 1.0,  # 0.5-1.0秒: 一般
                "poor": 5.0,  # > 1.0秒: 差
            },
            "success_rate": {
                "excellent": 0.99,  # > 99%: 优秀
                "good": 0.95,  # 95-99%: 良好
                "fair": 0.90,  # 90-95%: 一般
                "poor": 0.80,  # < 80%: 差
            },
            "resource_usage": {
                "excellent": 0.3,  # < 30%: 优秀
                "good": 0.6,  # 30-60%: 良好
                "fair": 0.8,  # 60-80%: 一般
                "poor": 0.9,  # > 80%: 差
            },
            "availability": {
                "excellent": 0.999,  # > 99.9%: 优秀
                "good": 0.99,  # 99-99.9%: 良好
                "fair": 0.95,  # 95-99%: 一般
                "poor": 0.90,  # < 90%: 差
            },
        }

        # 指标历史存储（实际实现中应从数据库获取）
        self.metrics_history = {}

        logger.info(f"健康度计算器初始化完成，历史窗口: {history_window_hours}小时")

    def calculate_metric_score(self, metric_name: str, metric_value: float) -> float:
        """
        计算单个指标分数 (0.0-1.0)

        Args:
            metric_name: 指标名称
            metric_value: 指标值

        Returns:
            指标分数 (0.0-1.0)
        """
        thresholds = self.metrics_thresholds.get(metric_name, {})

        if not thresholds:
            logger.warning(f"未知指标: {metric_name}")
            return 0.5  # 默认中等分数

        # 根据阈值计算分数
        if metric_name == "response_time":
            # 响应时间：越低越好
            if metric_value <= thresholds["excellent"]:
                return 1.0
            elif metric_value <= thresholds["good"]:
                return 0.8
            elif metric_value <= thresholds["fair"]:
                return 0.6
            elif metric_value <= thresholds["poor"]:
                return 0.3
            else:
                return 0.1

        elif metric_name == "success_rate":
            # 成功率：越高越好
            if metric_value >= thresholds["excellent"]:
                return 1.0
            elif metric_value >= thresholds["good"]:
                return 0.8
            elif metric_value >= thresholds["fair"]:
                return 0.6
            elif metric_value >= thresholds["poor"]:
                return 0.3
            else:
                return 0.1

        elif metric_name == "resource_usage":
            # 资源使用：越低越好
            if metric_value <= thresholds["excellent"]:
                return 1.0
            elif metric_value <= thresholds["good"]:
                return 0.8
            elif metric_value <= thresholds["fair"]:
                return 0.6
            elif metric_value <= thresholds["poor"]:
                return 0.3
            else:
                return 0.1

        elif metric_name == "availability":
            # 可用性：越高越好
            if metric_value >= thresholds["excellent"]:
                return 1.0
            elif metric_value >= thresholds["good"]:
                return 0.8
            elif metric_value >= thresholds["fair"]:
                return 0.6
            elif metric_value >= thresholds["poor"]:
                return 0.3
            else:
                return 0.1

        else:
            # 未知指标类型
            return 0.5

    def calculate_health(self, agent_metrics: Dict[str, Any]) -> float:
        """
        计算智能体综合健康度

        Args:
            agent_metrics: 智能体指标字典，包含:
                - response_time: 平均响应时间（秒）
                - success_rate: 成功率（0.0-1.0）
                - resource_usage: 资源使用率（0.0-1.0）
                - availability: 可用性（0.0-1.0）
                - 其他自定义指标

        Returns:
            综合健康度分数 (0.0-1.0)
        """
        # 提取指标值（提供默认值）
        response_time = agent_metrics.get("response_time", 0.5)  # 默认0.5秒
        success_rate = agent_metrics.get("success_rate", 0.95)  # 默认95%
        resource_usage = agent_metrics.get("resource_usage", 0.5)  # 默认50%
        availability = agent_metrics.get("availability", 0.99)  # 默认99%

        # 计算各指标分数
        scores = {
            "response_time": self.calculate_metric_score("response_time", response_time),
            "success_rate": self.calculate_metric_score("success_rate", success_rate),
            "resource_usage": self.calculate_metric_score("resource_usage", resource_usage),
            "availability": self.calculate_metric_score("availability", availability),
        }

        # 计算加权综合分数
        total_score = 0.0
        total_weight = 0.0

        for metric, weight in self.metrics_weights.items():
            score = scores.get(metric, 0.5)
            total_score += score * weight
            total_weight += weight

        # 归一化（确保权重总和为1.0）
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0.5

        # 记录计算详情（用于调试）
        logger.debug(f"健康度计算详情: {scores}, 综合分数: {final_score:.3f}")

        return round(final_score, 3)

    def calculate_from_history(
        self, agent_id: str, metrics_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        基于历史数据计算健康度

        Args:
            agent_id: 智能体ID
            metrics_history: 历史指标列表

        Returns:
            健康度报告
        """
        if not metrics_history:
            return {
                "agent_id": agent_id,
                "health_score": 0.5,
                "metrics": {},
                "calculation_time": datetime.now().isoformat(),
                "error": "无历史数据",
            }

        # 聚合历史数据（最近N条）
        recent_history = metrics_history[-50:]  # 最近50条

        # 计算平均指标
        response_times = [
            m.get("response_time", 0.5) for m in recent_history if "response_time" in m
        ]
        success_rates = [m.get("success_rate", 0.95) for m in recent_history if "success_rate" in m]
        resource_usages = [
            m.get("resource_usage", 0.5) for m in recent_history if "resource_usage" in m
        ]
        availabilities = [
            m.get("availability", 0.99) for m in recent_history if "availability" in m
        ]

        avg_metrics = {
            "response_time": statistics.mean(response_times) if response_times else 0.5,
            "success_rate": statistics.mean(success_rates) if success_rates else 0.95,
            "resource_usage": statistics.mean(resource_usages) if resource_usages else 0.5,
            "availability": statistics.mean(availabilities) if availabilities else 0.99,
        }

        # 计算健康度
        health_score = self.calculate_health(avg_metrics)

        # 趋势分析（简单线性趋势）
        trend = "stable"
        if len(recent_history) >= 10:
            recent_scores = []
            for i in range(0, len(recent_history), max(1, len(recent_history) // 10)):
                sample = recent_history[i]
                sample_metrics = {
                    "response_time": sample.get("response_time", 0.5),
                    "success_rate": sample.get("success_rate", 0.95),
                    "resource_usage": sample.get("resource_usage", 0.5),
                    "availability": sample.get("availability", 0.99),
                }
                sample_score = self.calculate_health(sample_metrics)
                recent_scores.append(sample_score)

            if len(recent_scores) >= 2:
                first_half = statistics.mean(recent_scores[: len(recent_scores) // 2])
                second_half = statistics.mean(recent_scores[len(recent_scores) // 2 :])
                if second_half > first_half + 0.05:
                    trend = "improving"
                elif second_half < first_half - 0.05:
                    trend = "declining"

        return {
            "agent_id": agent_id,
            "health_score": health_score,
            "metrics": avg_metrics,
            "trend": trend,
            "calculation_time": datetime.now().isoformat(),
            "samples_used": len(recent_history),
        }

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """
        更新指标权重

        Args:
            new_weights: 新权重字典
        """
        for metric, weight in new_weights.items():
            if metric in self.metrics_weights:
                self.metrics_weights[metric] = weight
                logger.info(f"更新 {metric} 权重为: {weight}")
            else:
                logger.warning(f"忽略未知指标权重: {metric}")

    def update_thresholds(self, metric_name: str, new_thresholds: Dict[str, float]) -> None:
        """
        更新指标阈值

        Args:
            metric_name: 指标名称
            new_thresholds: 新阈值字典
        """
        if metric_name in self.metrics_thresholds:
            self.metrics_thresholds[metric_name] = new_thresholds
            logger.info(f"更新 {metric_name} 阈值")
        else:
            logger.warning(f"未知指标: {metric_name}")


def simulate_agent_metrics() -> Dict[str, Any]:
    """
    生成模拟智能体指标（用于测试）

    Returns:
        模拟指标字典
    """
    import random

    return {
        "response_time": random.uniform(0.05, 1.5),  # 0.05-1.5秒
        "success_rate": random.uniform(0.85, 0.999),  # 85%-99.9%
        "resource_usage": random.uniform(0.2, 0.9),  # 20%-90%
        "availability": random.uniform(0.95, 0.999),  # 95%-99.9%
        "timestamp": datetime.now().isoformat(),
    }


def test_health_calculator():
    """测试健康度计算器"""
    print("=== 测试健康度计算器 ===")

    # 初始化计算器
    calculator = AgentHealthCalculator()

    # 测试1: 优秀指标
    print("\n1. 测试优秀指标:")
    excellent_metrics = {
        "response_time": 0.05,  # 0.05秒
        "success_rate": 0.995,  # 99.5%
        "resource_usage": 0.25,  # 25%
        "availability": 0.999,  # 99.9%
    }
    score = calculator.calculate_health(excellent_metrics)
    print(f"   优秀指标健康度: {score:.3f} (期望: >0.9)")

    # 测试2: 一般指标
    print("\n2. 测试一般指标:")
    average_metrics = {
        "response_time": 0.7,  # 0.7秒
        "success_rate": 0.92,  # 92%
        "resource_usage": 0.65,  # 65%
        "availability": 0.97,  # 97%
    }
    score = calculator.calculate_health(average_metrics)
    print(f"   一般指标健康度: {score:.3f} (期望: ~0.6-0.7)")

    # 测试3: 差指标
    print("\n3. 测试差指标:")
    poor_metrics = {
        "response_time": 3.0,  # 3.0秒
        "success_rate": 0.75,  # 75%
        "resource_usage": 0.95,  # 95%
        "availability": 0.85,  # 85%
    }
    score = calculator.calculate_health(poor_metrics)
    print(f"   差指标健康度: {score:.3f} (期望: <0.4)")

    # 测试4: 部分缺失指标
    print("\n4. 测试部分缺失指标:")
    partial_metrics = {
        "response_time": 0.3,
        "success_rate": 0.98,
        # 缺失 resource_usage 和 availability
    }
    score = calculator.calculate_health(partial_metrics)
    print(f"   部分指标健康度: {score:.3f} (使用默认值)")

    # 测试5: 历史数据计算
    print("\n5. 测试历史数据计算:")
    history = []
    for i in range(20):
        history.append(simulate_agent_metrics())

    report = calculator.calculate_from_history("test_agent_001", history)
    print(f"   历史数据健康度报告:")
    print(f"     智能体ID: {report['agent_id']}")
    print(f"     健康分数: {report['health_score']:.3f}")
    print(f"     趋势: {report['trend']}")
    print(f"     使用样本数: {report['samples_used']}")

    print("\n✅ 健康度计算器测试完成")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    test_health_calculator()
