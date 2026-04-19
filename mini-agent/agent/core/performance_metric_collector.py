#!/usr/bin/env python3
"""
Performance Metric Collector - 性能指标采集器

从 Athena/runtime/queue 真实执行证据中采集性能指标。
最小指标采集面：执行时长、成功率、资源消耗（近似替代指标）。
"""

import glob
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

# 导入 OpenSpace 数据模型
from mini_agent.agent.core.openspace_adapter import PerformanceMetric

logger = logging.getLogger(__name__)


class MetricSource:
    """指标数据源"""

    def __init__(self, source_type: str, path_pattern: str):
        self.source_type = source_type
        self.path_pattern = path_pattern

    def find_files(self, max_files: int = 10) -> List[str]:
        """查找匹配的文件"""
        files = glob.glob(self.path_pattern, recursive=True)
        # 按修改时间排序，最新的在前
        files.sort(key=os.path.getmtime, reverse=True)
        return files[:max_files]


class PerformanceMetricCollector:
    """性能指标采集器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.sources = self._initialize_sources()
        logger.info("PerformanceMetricCollector 初始化完成")

    def _initialize_sources(self) -> List[MetricSource]:
        """初始化数据源"""
        # 默认数据源：从 workspace/autoresearch/ 读取 metrics_baseline JSON 文件
        # 这些文件包含 Athena 队列执行证据
        workspace_dir = os.path.join(project_root, "workspace", "autoresearch")
        baseline_pattern = os.path.join(workspace_dir, "metrics_baseline_*.json")

        sources = [MetricSource(source_type="athena_queue_metrics", path_pattern=baseline_pattern)]

        # 如果配置了额外数据源，添加它们
        extra_sources = self.config.get("metric_sources", [])
        for src in extra_sources:
            sources.append(MetricSource(**src))

        return sources

    def collect_metrics(
        self, skill_id: Optional[str] = None, time_range_hours: Optional[int] = 24
    ) -> List[PerformanceMetric]:
        """
        采集性能指标

        Args:
            skill_id: 可选的技能ID，用于筛选特定技能指标
            time_range_hours: 时间范围（小时），默认为最近24小时

        Returns:
            性能指标列表
        """
        all_metrics = []

        for source in self.sources:
            try:
                metrics = self._collect_from_source(source, skill_id, time_range_hours)
                all_metrics.extend(metrics)
            except Exception as e:
                logger.warning(f"从数据源 {source.source_type} 采集指标失败: {e}")

        logger.info(f"采集到 {len(all_metrics)} 个性能指标")
        return all_metrics

    def _collect_from_source(
        self,
        source: MetricSource,
        skill_id: Optional[str],
        time_range_hours: Optional[int],
    ) -> List[PerformanceMetric]:
        """从单个数据源采集指标"""
        files = source.find_files(max_files=5)
        if not files:
            logger.debug(f"数据源 {source.source_type} 未找到文件")
            return []

        metrics = []

        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 根据源类型解析数据
                if source.source_type == "athena_queue_metrics":
                    file_metrics = self._parse_athena_queue_metrics(data, skill_id)
                    metrics.extend(file_metrics)

            except Exception as e:
                logger.warning(f"解析文件 {filepath} 失败: {e}")
                continue

        return metrics

    def _parse_athena_queue_metrics(
        self, data: Dict[str, Any], skill_id: Optional[str]
    ) -> List[PerformanceMetric]:
        """解析 Athena 队列指标数据"""
        metrics = []

        # 1. 整体成功率指标
        if "overall_success_rate" in data:
            success_rate_metric = PerformanceMetric(
                metric_id="overall_success_rate",
                metric_type="success_rate",
                values=[
                    {
                        "timestamp": data.get("timestamp", datetime.now().isoformat()),
                        "value": float(data["overall_success_rate"]),
                        "context": {
                            "total_tasks": data.get("total_tasks", 0),
                            "total_completed": data.get("total_completed", 0),
                            "total_failed": data.get("total_failed", 0),
                        },
                    }
                ],
            )
            metrics.append(success_rate_metric)

        # 2. 平均延迟指标
        if "avg_latency_all" in data:
            latency_metric = PerformanceMetric(
                metric_id="avg_execution_latency",
                metric_type="execution_time",
                values=[
                    {
                        "timestamp": data.get("timestamp", datetime.now().isoformat()),
                        "value": float(data["avg_latency_all"]),
                        "context": {"unit": "seconds", "description": "平均执行延迟"},
                    }
                ],
            )
            metrics.append(latency_metric)

        # 3. 队列指标（如果有）
        if "queue_metrics" in data and isinstance(data["queue_metrics"], list):
            for queue in data["queue_metrics"]:
                # 队列成功率
                total = queue.get("total_items", 0)
                completed = queue.get("completed_items", 0)
                if total > 0:
                    queue_success_rate = completed / total
                    queue_metric = PerformanceMetric(
                        metric_id=f"queue_success_rate_{queue.get('queue_id', 'unknown')}",
                        metric_type="success_rate",
                        values=[
                            {
                                "timestamp": data.get("timestamp", datetime.now().isoformat()),
                                "value": queue_success_rate,
                                "context": {
                                    "queue_id": queue.get("queue_id"),
                                    "total_items": total,
                                    "completed_items": completed,
                                    "failed_items": queue.get("failed_items", 0),
                                },
                            }
                        ],
                    )
                    metrics.append(queue_metric)

                # 队列执行延迟
                latency = queue.get("avg_execution_latency")
                if latency is not None:
                    latency_metric = PerformanceMetric(
                        metric_id=f"queue_latency_{queue.get('queue_id', 'unknown')}",
                        metric_type="execution_time",
                        values=[
                            {
                                "timestamp": data.get("timestamp", datetime.now().isoformat()),
                                "value": float(latency) if latency else 0.0,
                                "context": {
                                    "queue_id": queue.get("queue_id"),
                                    "unit": "seconds",
                                },
                            }
                        ],
                    )
                    metrics.append(latency_metric)

        # 4. 资源消耗近似指标（使用吞吐量作为替代）
        if "overall_throughput_24h" in data:
            throughput_metric = PerformanceMetric(
                metric_id="system_throughput",
                metric_type="resource_usage",
                values=[
                    {
                        "timestamp": data.get("timestamp", datetime.now().isoformat()),
                        "value": float(data["overall_throughput_24h"]),
                        "context": {
                            "unit": "tasks_per_hour",
                            "description": "24小时系统吞吐量",
                        },
                    }
                ],
            )
            metrics.append(throughput_metric)

        # 5. 失败原因分布（作为分类指标）
        if "failure_reason_distribution" in data:
            failure_metric = PerformanceMetric(
                metric_id="failure_reason_distribution",
                metric_type="error_distribution",
                values=[
                    {
                        "timestamp": data.get("timestamp", datetime.now().isoformat()),
                        "value": len(data["failure_reason_distribution"]),
                        "context": {
                            "distribution": data["failure_reason_distribution"],
                            "unique_error_types": len(data["failure_reason_distribution"]),
                        },
                    }
                ],
            )
            metrics.append(failure_metric)

        return metrics

    def get_metric_summary(self, metrics: List[PerformanceMetric]) -> Dict[str, Any]:
        """获取指标摘要"""
        if not metrics:
            return {"status": "no_metrics", "count": 0}

        summary = {
            "total_metrics": len(metrics),
            "metric_types": {},
            "timestamp_range": {"min": None, "max": None},
            "recent_metrics_count": 0,
        }

        # 按类型统计
        for metric in metrics:
            m_type = metric.metric_type
            summary["metric_types"][m_type] = summary["metric_types"].get(m_type, 0) + 1

        # 时间范围（如果有时间戳）
        timestamps = []
        for metric in metrics:
            for value in metric.values:
                if "timestamp" in value:
                    try:
                        ts_str = value["timestamp"]
                        if ts_str.endswith("Z"):
                            ts_str = ts_str.replace("Z", "+00:00")
                        ts = datetime.fromisoformat(ts_str)
                        # 确保有时区信息（假设UTC）
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        timestamps.append(ts)
                    except:
                        pass

        if timestamps:
            summary["timestamp_range"]["min"] = min(timestamps).isoformat()
            summary["timestamp_range"]["max"] = max(timestamps).isoformat()

            # 最近24小时内的指标
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_count = sum(1 for ts in timestamps if ts > cutoff)
            summary["recent_metrics_count"] = recent_count

        return summary

    def validate_metrics_for_evolution(
        self, metrics: List[PerformanceMetric], min_metrics: int = 3
    ) -> Tuple[bool, str]:
        """
        验证指标是否足够进行进化分析

        Args:
            metrics: 指标列表
            min_metrics: 所需最小指标数量

        Returns:
            (是否有效, 原因)
        """
        if len(metrics) < min_metrics:
            return False, f"指标数量不足: {len(metrics)} < {min_metrics}"

        # 检查是否包含关键指标类型
        metric_types = {m.metric_type for m in metrics}
        required_types = {"success_rate", "execution_time"}
        missing_types = required_types - metric_types

        if missing_types:
            return False, f"缺少关键指标类型: {missing_types}"

        # 检查指标是否足够新鲜（最近24小时内）
        summary = self.get_metric_summary(metrics)
        recent_count = summary.get("recent_metrics_count", 0)

        if recent_count < min_metrics:
            return False, f"最近24小时内的指标不足: {recent_count} < {min_metrics}"

        return True, "指标验证通过"


# 全局采集器实例
_collector_instance: Optional[PerformanceMetricCollector] = None


def get_collector() -> PerformanceMetricCollector:
    """获取全局采集器实例"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = PerformanceMetricCollector()
    return _collector_instance


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=== Performance Metric Collector 测试 ===")

    collector = PerformanceMetricCollector()

    print("1. 采集指标...")
    metrics = collector.collect_metrics()
    print(f"   采集到 {len(metrics)} 个指标")

    if metrics:
        print("\n2. 指标摘要:")
        summary = collector.get_metric_summary(metrics)
        print(f"   总指标数: {summary['total_metrics']}")
        print(f"   指标类型分布:")
        for m_type, count in summary["metric_types"].items():
            print(f"     - {m_type}: {count}")

        if summary["timestamp_range"]["min"]:
            print(
                f"   时间范围: {summary['timestamp_range']['min']} 到 {summary['timestamp_range']['max']}"
            )
        print(f"   最近24小时指标数: {summary['recent_metrics_count']}")

        print("\n3. 进化验证:")
        valid, reason = collector.validate_metrics_for_evolution(metrics)
        print(f"   是否有效: {valid}")
        print(f"   原因: {reason}")

    print("\n✅ Performance Metric Collector 测试完成")
