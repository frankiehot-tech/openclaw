#!/usr/bin/env python3
"""
MAREF沙箱简单监控模块

收集和记录系统、应用和业务指标。
支持实时监控、历史数据存储和简单告警。
"""

import json
import os
import time
import threading
from collections import deque
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable


class MetricType(Enum):
    """指标类型枚举"""

    SYSTEM = "system"  # 系统指标（CPU、内存、IO等）
    APPLICATION = "application"  # 应用指标（吞吐量、延迟等）
    BUSINESS = "business"  # 业务指标（质量评分、转换效率等）


class MetricCategory(Enum):
    """指标分类枚举"""

    COUNTER = "counter"  # 计数器（只增不减）
    GAUGE = "gauge"  # 计量器（可增可减）
    HISTOGRAM = "histogram"  # 直方图（统计分布）


class SimpleMonitor:
    """简单监控器"""

    def __init__(self, retention_period: int = 300, collection_interval: int = 5):
        """
        初始化监控器

        Args:
            retention_period: 数据保留时间（秒）
            collection_interval: 指标收集间隔（秒）
        """
        self.retention_period = retention_period
        self.collection_interval = collection_interval

        # 指标存储
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.history: Dict[str, deque] = {}

        # 告警配置
        self.alerts: Dict[str, Dict[str, Any]] = {}

        # 监控线程
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None

        # 回调函数
        self.callbacks: Dict[str, List[Callable]] = {
            "metric_updated": [],
            "alert_triggered": [],
            "error_occurred": [],
        }

        # 初始化默认指标
        self._init_default_metrics()

        print(f"🚀 简单监控器初始化完成")
        print(f"   数据保留时间: {retention_period}秒")
        print(f"   收集间隔: {collection_interval}秒")

    def _init_default_metrics(self) -> None:
        """初始化默认指标"""
        # 系统指标
        self.register_metric(
            "system.cpu_usage",
            MetricType.SYSTEM,
            MetricCategory.GAUGE,
            description="CPU使用率 (%)",
            unit="percent",
            min_value=0,
            max_value=100,
        )
        self.register_metric(
            "system.memory_usage",
            MetricType.SYSTEM,
            MetricCategory.GAUGE,
            description="内存使用率 (%)",
            unit="percent",
            min_value=0,
            max_value=100,
        )
        self.register_metric(
            "system.disk_io",
            MetricType.SYSTEM,
            MetricCategory.GAUGE,
            description="磁盘IO (KB/s)",
            unit="KB/s",
            min_value=0,
        )
        self.register_metric(
            "system.network_traffic",
            MetricType.SYSTEM,
            MetricCategory.GAUGE,
            description="网络流量 (KB/s)",
            unit="KB/s",
            min_value=0,
        )

        # 应用指标
        self.register_metric(
            "application.queue_depth",
            MetricType.APPLICATION,
            MetricCategory.GAUGE,
            description="队列深度",
            unit="tasks",
            min_value=0,
        )
        self.register_metric(
            "application.throughput",
            MetricType.APPLICATION,
            MetricCategory.GAUGE,
            description="吞吐量",
            unit="tasks/minute",
            min_value=0,
        )
        self.register_metric(
            "application.latency",
            MetricType.APPLICATION,
            MetricCategory.GAUGE,
            description="延迟",
            unit="seconds",
            min_value=0,
        )
        self.register_metric(
            "application.error_rate",
            MetricType.APPLICATION,
            MetricCategory.GAUGE,
            description="错误率",
            unit="percent",
            min_value=0,
            max_value=100,
        )

        # 业务指标
        self.register_metric(
            "business.task_completion_rate",
            MetricType.BUSINESS,
            MetricCategory.GAUGE,
            description="任务完成率",
            unit="percent",
            min_value=0,
            max_value=100,
        )
        self.register_metric(
            "business.quality_score",
            MetricType.BUSINESS,
            MetricCategory.GAUGE,
            description="质量评分",
            unit="score",
            min_value=0,
            max_value=10,
        )
        self.register_metric(
            "business.state_transition_efficiency",
            MetricType.BUSINESS,
            MetricCategory.GAUGE,
            description="状态转换效率",
            unit="ratio",
            min_value=0,
        )
        self.register_metric(
            "business.hamming_distance",
            MetricType.BUSINESS,
            MetricCategory.GAUGE,
            description="汉明距离",
            unit="bits",
            min_value=0,
            max_value=6,
        )

    def register_metric(
        self,
        name: str,
        metric_type: MetricType,
        category: MetricCategory,
        description: str = "",
        unit: str = "",
        **kwargs,
    ) -> bool:
        """
        注册指标

        Args:
            name: 指标名称（如 "system.cpu_usage"）
            metric_type: 指标类型
            category: 指标分类
            description: 指标描述
            unit: 指标单位
            **kwargs: 额外参数（min_value, max_value等）

        Returns:
            是否成功注册
        """
        if name in self.metrics:
            return False

        self.metrics[name] = {
            "name": name,
            "type": metric_type.value,
            "category": category.value,
            "description": description,
            "unit": unit,
            "current_value": 0.0,
            "last_updated": datetime.now().isoformat(),
            "config": kwargs,
        }

        # 初始化历史记录
        self.history[name] = deque(
            maxlen=self.retention_period // self.collection_interval
        )

        return True

    def update_metric(
        self, name: str, value: float, timestamp: Optional[str] = None
    ) -> bool:
        """
        更新指标值

        Args:
            name: 指标名称
            value: 指标值
            timestamp: 时间戳（ISO格式），如为None则使用当前时间

        Returns:
            是否成功更新
        """
        if name not in self.metrics:
            return False

        metric = self.metrics[name]
        old_value = metric["current_value"]

        # 验证值范围
        config = metric["config"]
        min_value = config.get("min_value")
        max_value = config.get("max_value")

        if min_value is not None and value < min_value:
            value = min_value
        if max_value is not None and value > max_value:
            value = max_value

        # 更新当前值
        metric["current_value"] = value
        metric["last_updated"] = timestamp or datetime.now().isoformat()

        # 记录历史
        history_entry = {
            "timestamp": metric["last_updated"],
            "value": value,
            "old_value": old_value,
        }
        self.history[name].append(history_entry)

        # 触发回调
        self._trigger_callback(
            "metric_updated",
            {
                "metric_name": name,
                "old_value": old_value,
                "new_value": value,
                "timestamp": metric["last_updated"],
            },
        )

        # 检查告警
        self._check_alerts(name, value)

        return True

    def _check_alerts(self, metric_name: str, value: float) -> None:
        """检查告警条件"""
        for alert_name, alert_config in self.alerts.items():
            if alert_config.get("metric") != metric_name:
                continue

            condition = alert_config.get("condition")
            threshold = alert_config.get("threshold")
            severity = alert_config.get("severity", "warning")

            triggered = False
            alert_message = ""

            if condition == "above":
                if value > threshold:
                    triggered = True
                    alert_message = f"{metric_name} ({value}) 高于阈值 {threshold}"
            elif condition == "below":
                if value < threshold:
                    triggered = True
                    alert_message = f"{metric_name} ({value}) 低于阈值 {threshold}"
            elif condition == "equal":
                if value == threshold:
                    triggered = True
                    alert_message = f"{metric_name} ({value}) 等于阈值 {threshold}"
            elif condition == "change_percent":
                old_value = alert_config.get("last_value", value)
                change_percent = (
                    abs((value - old_value) / old_value * 100) if old_value != 0 else 0
                )
                if change_percent > threshold:
                    triggered = True
                    alert_message = f"{metric_name} 变化 {change_percent:.1f}% 超过阈值 {threshold}%"

            if triggered:
                alert_data = {
                    "alert_name": alert_name,
                    "metric_name": metric_name,
                    "metric_value": value,
                    "threshold": threshold,
                    "condition": condition,
                    "severity": severity,
                    "message": alert_message,
                    "timestamp": datetime.now().isoformat(),
                }

                # 更新告警最后触发时间
                self.alerts[alert_name]["last_triggered"] = alert_data["timestamp"]
                self.alerts[alert_name]["trigger_count"] = (
                    self.alerts[alert_name].get("trigger_count", 0) + 1
                )

                # 触发回调
                self._trigger_callback("alert_triggered", alert_data)

                print(f"⚠️  告警触发: {alert_message}")

    def register_alert(
        self,
        name: str,
        metric: str,
        condition: str,
        threshold: float,
        severity: str = "warning",
        description: str = "",
    ) -> bool:
        """
        注册告警

        Args:
            name: 告警名称
            metric: 监控的指标名称
            condition: 条件（"above", "below", "equal", "change_percent"）
            threshold: 阈值
            severity: 严重程度（"info", "warning", "critical"）
            description: 告警描述

        Returns:
            是否成功注册
        """
        if metric not in self.metrics:
            return False

        self.alerts[name] = {
            "metric": metric,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "last_triggered": None,
            "trigger_count": 0,
        }

        return True

    def get_metric(self, name: str) -> Optional[Dict[str, Any]]:
        """获取指标当前值"""
        return self.metrics.get(name)

    def get_metric_history(
        self, name: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取指标历史数据"""
        if name not in self.history:
            return []

        history = list(self.history[name])
        if limit and limit > 0:
            history = history[-limit:]

        return history

    def get_metric_statistics(
        self, name: str, window: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取指标统计信息"""
        if name not in self.history:
            return {}

        history = self.get_metric_history(name, window)
        if not history:
            return {}

        values = [entry["value"] for entry in history]

        import statistics

        stats = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "last": values[-1] if values else 0,
        }

        if len(values) > 1:
            stats["std_dev"] = statistics.stdev(values)

        return stats

    def start_monitoring(self) -> bool:
        """启动监控线程"""
        if self.is_running:
            return False

        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitor_thread.start()

        print(f"▶️  监控线程已启动 (间隔: {self.collection_interval}秒)")
        return True

    def stop_monitoring(self) -> bool:
        """停止监控线程"""
        if not self.is_running:
            return False

        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)

        print("⏸️  监控线程已停止")
        return True

    def _monitoring_loop(self) -> None:
        """监控循环（模拟系统指标收集）"""
        while self.is_running:
            try:
                # 模拟系统指标更新
                self._collect_simulated_metrics()

                # 等待下一个收集周期
                time.sleep(self.collection_interval)

            except Exception as e:
                self._trigger_callback(
                    "error_occurred",
                    {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
                time.sleep(1)  # 错误后稍等

    def _collect_simulated_metrics(self) -> None:
        """收集模拟的系统指标"""
        import random

        # 模拟CPU使用率（40-80%之间波动）
        cpu_usage = 40 + random.random() * 40
        self.update_metric("system.cpu_usage", cpu_usage)

        # 模拟内存使用率（50-90%之间波动）
        memory_usage = 50 + random.random() * 40
        self.update_metric("system.memory_usage", memory_usage)

        # 模拟磁盘IO（0-1000 KB/s）
        disk_io = random.random() * 1000
        self.update_metric("system.disk_io", disk_io)

        # 模拟网络流量（0-500 KB/s）
        network_traffic = random.random() * 500
        self.update_metric("system.network_traffic", network_traffic)

    def register_callback(self, event: str, callback: Callable) -> bool:
        """
        注册回调函数

        Args:
            event: 事件类型（"metric_updated", "alert_triggered", "error_occurred"）
            callback: 回调函数

        Returns:
            是否成功注册
        """
        if event not in self.callbacks:
            return False

        self.callbacks[event].append(callback)
        return True

    def _trigger_callback(self, event: str, data: Dict[str, Any]) -> None:
        """触发回调函数"""
        if event not in self.callbacks:
            return

        for callback in self.callbacks[event]:
            try:
                callback(data)
            except Exception as e:
                print(f"回调函数执行错误: {e}")

    def export_metrics(self, export_dir: str = "./monitoring_data") -> str:
        """
        导出所有指标数据

        Args:
            export_dir: 导出目录

        Returns:
            导出的文件路径
        """
        os.makedirs(export_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(export_dir, f"metrics_export_{timestamp}.json")

        export_data = {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "total_metrics": len(self.metrics),
                "retention_period": self.retention_period,
                "collection_interval": self.collection_interval,
            },
            "metrics": {},
            "alerts": self.alerts,
        }

        # 导出每个指标的当前状态和历史
        for name, metric in self.metrics.items():
            export_data["metrics"][name] = {
                "current": metric,
                "history": list(self.history.get(name, [])),
                "statistics": self.get_metric_statistics(name),
            }

        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"📊 指标数据已导出: {filepath}")
        print(f"   指标数量: {len(self.metrics)}")
        print(f"   告警数量: {len(self.alerts)}")

        return filepath

    def generate_monitoring_report(self) -> Dict[str, Any]:
        """生成监控报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_metrics": len(self.metrics),
                "active_alerts": sum(
                    1 for alert in self.alerts.values() if alert.get("last_triggered")
                ),
                "system_metrics": {},
                "application_metrics": {},
                "business_metrics": {},
            },
            "metric_details": {},
            "alert_details": [],
        }

        # 按类型分类指标
        for name, metric in self.metrics.items():
            metric_type = metric["type"]
            stats = self.get_metric_statistics(name, window=60)  # 最近60秒

            if metric_type == "system":
                report["summary"]["system_metrics"][name] = stats.get("mean", 0)
            elif metric_type == "application":
                report["summary"]["application_metrics"][name] = stats.get("mean", 0)
            elif metric_type == "business":
                report["summary"]["business_metrics"][name] = stats.get("mean", 0)

            report["metric_details"][name] = {
                "current_value": metric["current_value"],
                "last_updated": metric["last_updated"],
                "statistics": stats,
            }

        # 告警详情
        for alert_name, alert_config in self.alerts.items():
            if alert_config.get("last_triggered"):
                report["alert_details"].append(
                    {
                        "name": alert_name,
                        "metric": alert_config["metric"],
                        "severity": alert_config["severity"],
                        "last_triggered": alert_config["last_triggered"],
                        "trigger_count": alert_config.get("trigger_count", 0),
                        "description": alert_config.get("description", ""),
                    }
                )

        return report


def test_simple_monitor():
    """测试简单监控器"""
    print("=== 简单监控器测试 ===")

    monitor = SimpleMonitor(retention_period=60, collection_interval=2)

    # 注册自定义指标
    monitor.register_metric(
        "custom.requests_per_second",
        MetricType.APPLICATION,
        MetricCategory.GAUGE,
        description="每秒请求数",
        unit="requests/s",
    )

    # 注册告警
    monitor.register_alert(
        "high_cpu", "system.cpu_usage", "above", 75.0, "warning", "CPU使用率过高"
    )
    monitor.register_alert(
        "low_memory", "system.memory_usage", "below", 20.0, "critical", "内存不足"
    )

    # 定义回调函数
    def on_metric_updated(data):
        print(f"   指标更新: {data['metric_name']} = {data['new_value']:.2f}")

    def on_alert_triggered(data):
        print(f"   🚨 告警: {data['message']} (严重度: {data['severity']})")

    monitor.register_callback("metric_updated", on_metric_updated)
    monitor.register_callback("alert_triggered", on_alert_triggered)

    # 启动监控
    monitor.start_monitoring()

    print("\n📈 模拟指标更新...")
    for i in range(10):
        # 更新自定义指标
        monitor.update_metric("custom.requests_per_second", i * 10)

        # 模拟高CPU和低内存
        if i == 3:
            monitor.update_metric("system.cpu_usage", 80.0)  # 触发告警
        if i == 6:
            monitor.update_metric("system.memory_usage", 15.0)  # 触发告警

        time.sleep(1)

    # 停止监控
    monitor.stop_monitoring()

    # 导出数据
    export_file = monitor.export_metrics("./test_monitoring")

    # 生成报告
    report = monitor.generate_monitoring_report()
    print(f"\n📊 监控报告摘要:")
    print(f"   系统指标: {report['summary']['system_metrics']}")
    print(f"   应用指标: {report['summary']['application_metrics']}")
    print(f"   告警详情: {len(report['alert_details'])} 个告警")

    print("\n✅ 监控器测试完成!")
    return True


if __name__ == "__main__":
    test_simple_monitor()
