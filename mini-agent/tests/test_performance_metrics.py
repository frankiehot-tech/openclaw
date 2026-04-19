#!/usr/bin/env python3
"""
Performance Metrics Tests - 性能指标测试

验证性能指标收集器、指标样本、聚合功能的基本功能。
"""

import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import MagicMock, patch

from agent.core.performance_metrics import (
    MetricAggregation,
    MetricDimension,
    MetricSample,
    MetricType,
    PerformanceMetricsCollector,
    get_global_collector,
    record_metric,
)


class TestMetricSample(unittest.TestCase):
    """MetricSample 测试"""

    def test_sample_creation(self):
        """测试 MetricSample 创建"""
        sample = MetricSample(
            dimension=MetricDimension.RESPONSE_TIME,
            value=1.5,
            metric_type=MetricType.HISTOGRAM,
            labels={"queue_id": "test_queue"},
            metadata={"unit": "seconds"},
        )

        self.assertEqual(sample.dimension, MetricDimension.RESPONSE_TIME)
        self.assertEqual(sample.value, 1.5)
        self.assertEqual(sample.metric_type, MetricType.HISTOGRAM)
        self.assertEqual(sample.labels, {"queue_id": "test_queue"})
        self.assertEqual(sample.metadata, {"unit": "seconds"})
        self.assertGreater(sample.timestamp, 0)

    def test_sample_to_dict(self):
        """测试 MetricSample 字典转换"""
        sample = MetricSample(
            dimension=MetricDimension.QUEUE_LENGTH,
            value=10.0,
            metric_type=MetricType.GAUGE,
            labels={"queue_id": "test"},
            metadata={"unit": "tasks"},
        )

        sample_dict = sample.to_dict()

        self.assertEqual(sample_dict["dimension"], "queue_length")
        self.assertEqual(sample_dict["value"], 10.0)
        self.assertEqual(sample_dict["metric_type"], "gauge")
        self.assertEqual(sample_dict["labels"], {"queue_id": "test"})
        self.assertEqual(sample_dict["metadata"], {"unit": "tasks"})
        self.assertIn("timestamp", sample_dict)


class TestMetricAggregation(unittest.TestCase):
    """MetricAggregation 测试"""

    def test_aggregation_creation(self):
        """测试 MetricAggregation 创建"""
        agg = MetricAggregation(
            dimension=MetricDimension.RESPONSE_TIME,
            metric_type=MetricType.HISTOGRAM,
            labels={"queue_id": "test"},
            count=5,
            sum=25.0,
            min=2.0,
            max=8.0,
            avg=5.0,
            p50=4.5,
            p90=7.5,
            p99=8.0,
        )

        self.assertEqual(agg.dimension, MetricDimension.RESPONSE_TIME)
        self.assertEqual(agg.metric_type, MetricType.HISTOGRAM)
        self.assertEqual(agg.labels, {"queue_id": "test"})
        self.assertEqual(agg.count, 5)
        self.assertEqual(agg.sum, 25.0)
        self.assertEqual(agg.avg, 5.0)

    def test_aggregation_update(self):
        """测试 MetricAggregation 更新"""
        agg = MetricAggregation(
            dimension=MetricDimension.QUEUE_LENGTH,
            metric_type=MetricType.GAUGE,
            labels={},
        )

        # 第一个样本
        sample1 = MetricSample(
            dimension=MetricDimension.QUEUE_LENGTH,
            value=5.0,
            metric_type=MetricType.GAUGE,
        )
        agg.update(sample1)

        self.assertEqual(agg.count, 1)
        self.assertEqual(agg.sum, 5.0)
        self.assertEqual(agg.min, 5.0)
        self.assertEqual(agg.max, 5.0)
        self.assertEqual(agg.avg, 5.0)

        # 第二个样本
        sample2 = MetricSample(
            dimension=MetricDimension.QUEUE_LENGTH,
            value=15.0,
            metric_type=MetricType.GAUGE,
        )
        agg.update(sample2)

        self.assertEqual(agg.count, 2)
        self.assertEqual(agg.sum, 20.0)
        self.assertEqual(agg.min, 5.0)
        self.assertEqual(agg.max, 15.0)
        self.assertEqual(agg.avg, 10.0)

    def test_aggregation_to_dict(self):
        """测试 MetricAggregation 字典转换"""
        agg = MetricAggregation(
            dimension=MetricDimension.RESPONSE_TIME,
            metric_type=MetricType.HISTOGRAM,
            labels={"queue_id": "test"},
            count=3,
            sum=30.0,
            min=5.0,
            max=15.0,
            avg=10.0,
        )

        agg_dict = agg.to_dict()

        self.assertEqual(agg_dict["dimension"], "response_time")
        self.assertEqual(agg_dict["metric_type"], "histogram")
        self.assertEqual(agg_dict["labels"], {"queue_id": "test"})
        self.assertEqual(agg_dict["count"], 3)
        self.assertEqual(agg_dict["avg"], 10.0)


class TestPerformanceMetricsCollector(unittest.TestCase):
    """性能指标收集器测试"""

    def setUp(self):
        self.collector = PerformanceMetricsCollector(retention_seconds=10)

    def tearDown(self):
        self.collector.clear()

    def test_record_sample(self):
        """测试记录指标样本"""
        sample = MetricSample(
            dimension=MetricDimension.RESPONSE_TIME,
            value=2.5,
            metric_type=MetricType.HISTOGRAM,
            labels={"queue_id": "test"},
        )

        self.collector.record_sample(sample)

        samples = self.collector.get_samples()
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].value, 2.5)
        self.assertEqual(samples[0].dimension, MetricDimension.RESPONSE_TIME)

    def test_record_convenience(self):
        """测试便利记录方法"""
        self.collector.record(
            dimension=MetricDimension.QUEUE_LENGTH,
            value=5.0,
            metric_type=MetricType.GAUGE,
            labels={"queue_id": "test_queue"},
            metadata={"unit": "tasks"},
        )

        samples = self.collector.get_samples(dimension=MetricDimension.QUEUE_LENGTH)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].value, 5.0)
        self.assertEqual(samples[0].labels["queue_id"], "test_queue")

    def test_record_response_time(self):
        """测试记录响应时间"""
        self.collector.record_response_time(3.2, labels={"task_type": "build"})

        samples = self.collector.get_samples(dimension=MetricDimension.RESPONSE_TIME)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].value, 3.2)
        self.assertEqual(samples[0].labels.get("task_type"), "build")
        self.assertEqual(samples[0].metric_type, MetricType.HISTOGRAM)

    def test_record_queue_length(self):
        """测试记录队列长度"""
        self.collector.record_queue_length(10, "test_queue")

        samples = self.collector.get_samples(dimension=MetricDimension.QUEUE_LENGTH)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].value, 10.0)
        self.assertEqual(samples[0].labels["queue_id"], "test_queue")

    def test_record_concurrency(self):
        """测试记录并发数"""
        self.collector.record_concurrency(3, "build_worker")

        samples = self.collector.get_samples(dimension=MetricDimension.CONCURRENCY)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].value, 3.0)
        self.assertEqual(samples[0].labels["worker_type"], "build_worker")

    def test_record_success_rate(self):
        """测试记录成功率"""
        self.collector.record_success_rate(0.95, "build_tasks")

        samples = self.collector.get_samples(dimension=MetricDimension.SUCCESS_RATE)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].value, 0.95)
        self.assertEqual(samples[0].labels["component"], "build_tasks")

    def test_get_samples_filtering(self):
        """测试样本过滤"""
        # 记录不同维度的样本
        self.collector.record_queue_length(5, "queue1")
        self.collector.record_queue_length(8, "queue2")
        self.collector.record_response_time(1.5)

        # 按维度过滤
        queue_samples = self.collector.get_samples(dimension=MetricDimension.QUEUE_LENGTH)
        self.assertEqual(len(queue_samples), 2)

        # 按标签过滤
        queue1_samples = self.collector.get_samples(
            dimension=MetricDimension.QUEUE_LENGTH,
            labels={"queue_id": "queue1"},
        )
        self.assertEqual(len(queue1_samples), 1)
        self.assertEqual(queue1_samples[0].value, 5.0)

        # 按时间过滤
        time.sleep(0.1)
        now = time.time()
        self.collector.record_queue_length(3, "queue3")

        recent_samples = self.collector.get_samples(
            dimension=MetricDimension.QUEUE_LENGTH,
            start_time=now - 0.05,
        )
        self.assertEqual(len(recent_samples), 1)
        self.assertEqual(recent_samples[0].labels["queue_id"], "queue3")

    def test_aggregation(self):
        """测试指标聚合"""
        # 记录多个样本
        for i in range(5):
            self.collector.record_queue_length(i + 1, "test_queue")

        aggregations = self.collector.get_aggregations(
            dimension=MetricDimension.QUEUE_LENGTH,
            labels={"queue_id": "test_queue"},
        )

        self.assertEqual(len(aggregations), 1)
        agg = aggregations[0]

        self.assertEqual(agg.dimension, MetricDimension.QUEUE_LENGTH)
        self.assertEqual(agg.count, 5)
        self.assertEqual(agg.min, 1.0)
        self.assertEqual(agg.max, 5.0)
        self.assertEqual(agg.avg, 3.0)  # (1+2+3+4+5)/5 = 3.0

    def test_export_summary(self):
        """测试导出摘要"""
        self.collector.record_queue_length(5, "queue1")
        self.collector.record_queue_length(8, "queue2")
        self.collector.record_response_time(2.5)

        summary = self.collector.export_summary()

        self.assertIn("timestamp", summary)
        self.assertEqual(summary["sample_count"], 3)
        self.assertIn("metrics_by_dimension", summary)
        self.assertIn("queue_length", summary["metrics_by_dimension"])
        self.assertIn("response_time", summary["metrics_by_dimension"])

    def test_export_json(self):
        """测试导出 JSON"""
        self.collector.record_queue_length(5, "queue1")
        self.collector.record_response_time(2.5)

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "metrics.json"
            data = self.collector.export_json(export_path)

            self.assertIn("export_timestamp", data)
            self.assertEqual(data["sample_count"], 2)
            self.assertEqual(len(data["samples"]), 2)
            self.assertEqual(len(data["aggregations"]), 2)

            # 验证文件已创建
            self.assertTrue(export_path.exists())

    def test_cleanup_old_samples(self):
        """测试清理旧样本"""
        # 记录一个旧样本（模拟）
        old_sample = MetricSample(
            dimension=MetricDimension.QUEUE_LENGTH,
            value=5.0,
            metric_type=MetricType.GAUGE,
        )
        old_sample.timestamp = time.time() - 20  # 20秒前

        with patch.object(self.collector, "samples", [old_sample]):
            # 记录一个新样本触发清理
            self.collector.record_queue_length(10, "test_queue")

            samples = self.collector.get_samples()
            # 旧样本应被清理
            self.assertEqual(len(samples), 1)
            self.assertEqual(samples[0].value, 10.0)

    def test_clear(self):
        """测试清空收集器"""
        self.collector.record_queue_length(5, "queue1")
        self.collector.record_response_time(2.5)

        self.assertEqual(len(self.collector.get_samples()), 2)
        self.assertEqual(len(self.collector.get_aggregations()), 2)

        self.collector.clear()

        self.assertEqual(len(self.collector.get_samples()), 0)
        self.assertEqual(len(self.collector.get_aggregations()), 0)


class TestGlobalCollector(unittest.TestCase):
    """全局收集器测试"""

    def test_get_global_collector(self):
        """测试获取全局收集器"""
        collector1 = get_global_collector()
        collector2 = get_global_collector()

        self.assertIs(collector1, collector2)

    def test_record_metric_global(self):
        """测试全局记录指标函数"""
        # 记录指标
        record_metric(
            dimension=MetricDimension.QUEUE_LENGTH,
            value=5.0,
            metric_type=MetricType.GAUGE,
            labels={"queue_id": "test"},
        )

        # 验证
        collector = get_global_collector()
        samples = collector.get_samples(
            dimension=MetricDimension.QUEUE_LENGTH,
            labels={"queue_id": "test"},
        )

        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].value, 5.0)


if __name__ == "__main__":
    unittest.main()
