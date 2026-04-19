#!/usr/bin/env python3
"""
OpenHuman MVP 稳定性指标收集器

从现有 runtime/queue/health 证据中收集稳定性指标，评估告警等级。
最小指标面：可用性、响应时间、错误率。
"""

import glob
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import yaml

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


@dataclass
class StabilityMetric:
    """稳定性指标数据类"""

    metric_id: str
    metric_type: str  # availability, response_time, error_rate, data_integrity
    value: float
    unit: str
    source: str
    timestamp: str
    context: Dict[str, Any]


@dataclass
class Alert:
    """告警数据类"""

    alert_id: str
    metric_id: str
    alert_level: str  # P0, P1, P2
    message: str
    threshold: Dict[str, Any]
    timestamp: str
    severity: int  # 0=P0, 1=P1, 2=P2
    actions: List[str]


class StabilityMetricsCollector:
    """稳定性指标收集器"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化收集器"""
        self.config_path = config_path or os.path.join(
            project_root, "mini-agent", "config", "stability_alert_baseline.yaml"
        )
        self.config = self._load_config()
        self.workspace_root = project_root
        logger.info(f"稳定性指标收集器初始化完成，工作区根目录: {self.workspace_root}")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.info(f"配置文件加载成功: {self.config_path}")
                return config or {}
        except Exception as e:
            logger.warning(f"配置文件加载失败，使用默认配置: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "alert_levels": {
                "P0": {"severity": 0, "name": "严重"},
                "P1": {"severity": 1, "name": "警告"},
                "P2": {"severity": 2, "name": "信息"},
            },
            "stability_metrics": {
                "availability": {
                    "thresholds": {
                        "P0": {"condition": "availability == false"},
                        "P1": {"condition": "availability == degraded"},
                        "P2": {"condition": "availability == true but with warnings"},
                    }
                },
                "response_time": {
                    "unit": "seconds",
                    "thresholds": {
                        "P0": {"value": 10.0, "condition": ">"},
                        "P1": {"value": 5.0, "condition": ">"},
                        "P2": {"value": 2.0, "condition": ">"},
                    },
                },
                "error_rate": {
                    "unit": "ratio",
                    "thresholds": {
                        "P0": {"value": 0.3, "condition": ">"},
                        "P1": {"value": 0.1, "condition": ">"},
                        "P2": {"value": 0.05, "condition": ">"},
                    },
                },
            },
        }

    def collect_metrics(self) -> List[StabilityMetric]:
        """收集所有稳定性指标"""
        metrics = []

        # 1. 收集可用性指标
        availability_metric = self._collect_availability()
        if availability_metric:
            metrics.append(availability_metric)

        # 2. 收集响应时间指标
        response_time_metric = self._collect_response_time()
        if response_time_metric:
            metrics.append(response_time_metric)

        # 3. 收集错误率指标
        error_rate_metric = self._collect_error_rate()
        if error_rate_metric:
            metrics.append(error_rate_metric)

        # 4. 收集数据完整性指标
        data_integrity_metric = self._collect_data_integrity()
        if data_integrity_metric:
            metrics.append(data_integrity_metric)

        logger.info(f"共收集到 {len(metrics)} 个稳定性指标")
        return metrics

    def _collect_availability(self) -> Optional[StabilityMetric]:
        """收集可用性指标"""
        try:
            # 方法1: 检查运行时状态（通过 runtime-status.ts 的 TypeScript 实现）
            # 这里简化：检查是否有活动的队列消费者
            queue_status = self._get_queue_consumer_status()
            runtime_status = self._get_runtime_status()

            # 评估可用性
            is_active = runtime_status.get("isActive", False)
            consumer_running = queue_status.get("consumer_status") == "running"
            has_pending_items = queue_status.get("pending_count", 0) > 0

            availability_value = 1.0 if (is_active and consumer_running) else 0.0
            availability_state = "available" if availability_value == 1.0 else "unavailable"

            if is_active and consumer_running:
                if has_pending_items:
                    availability_state = "degraded"
                    availability_value = 0.7

            return StabilityMetric(
                metric_id="system_availability",
                metric_type="availability",
                value=availability_value,
                unit="binary",
                source="runtime-status.ts + queue state",
                timestamp=datetime.now().isoformat(),
                context={
                    "is_active": is_active,
                    "consumer_running": consumer_running,
                    "pending_items": queue_status.get("pending_count", 0),
                    "availability_state": availability_state,
                },
            )
        except Exception as e:
            logger.warning(f"可用性指标收集失败: {e}")
            return None

    def _collect_response_time(self) -> Optional[StabilityMetric]:
        """收集响应时间指标"""
        try:
            # 从 metrics_baseline 文件读取平均延迟
            baseline_files = glob.glob(
                os.path.join(
                    self.workspace_root,
                    "workspace",
                    "autoresearch",
                    "metrics_baseline_*.json",
                )
            )
            if not baseline_files:
                logger.warning("未找到 metrics_baseline 文件")
                return None

            # 读取最新的文件
            latest_file = max(baseline_files, key=os.path.getmtime)
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            avg_latency = data.get("avg_latency_all")
            if avg_latency is None:
                logger.warning("metrics_baseline 中未找到 avg_latency_all 字段")
                return None

            return StabilityMetric(
                metric_id="avg_response_time",
                metric_type="response_time",
                value=float(avg_latency),
                unit="seconds",
                source=f"metrics_baseline: {os.path.basename(latest_file)}",
                timestamp=data.get("timestamp", datetime.now().isoformat()),
                context={
                    "source_file": latest_file,
                    "total_tasks": data.get("total_tasks", 0),
                    "collection_version": data.get("metadata", {}).get(
                        "collection_version", "unknown"
                    ),
                },
            )
        except Exception as e:
            logger.warning(f"响应时间指标收集失败: {e}")
            return None

    def _collect_error_rate(self) -> Optional[StabilityMetric]:
        """收集错误率指标"""
        try:
            # 从 metrics_baseline 文件读取任务统计
            baseline_files = glob.glob(
                os.path.join(
                    self.workspace_root,
                    "workspace",
                    "autoresearch",
                    "metrics_baseline_*.json",
                )
            )
            if not baseline_files:
                logger.warning("未找到 metrics_baseline 文件")
                return None

            latest_file = max(baseline_files, key=os.path.getmtime)
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            total_completed = data.get("total_completed", 0)
            total_failed = data.get("total_failed", 0)

            if total_completed + total_failed == 0:
                error_rate = 0.0
            else:
                error_rate = total_failed / (total_completed + total_failed)

            return StabilityMetric(
                metric_id="task_error_rate",
                metric_type="error_rate",
                value=error_rate,
                unit="ratio",
                source=f"metrics_baseline: {os.path.basename(latest_file)}",
                timestamp=data.get("timestamp", datetime.now().isoformat()),
                context={
                    "source_file": latest_file,
                    "total_completed": total_completed,
                    "total_failed": total_failed,
                    "total_tasks": data.get("total_tasks", 0),
                    "failure_reason_distribution": data.get("failure_reason_distribution", {}),
                },
            )
        except Exception as e:
            logger.warning(f"错误率指标收集失败: {e}")
            return None

    def _collect_data_integrity(self) -> Optional[StabilityMetric]:
        """收集数据完整性指标"""
        try:
            # 检查关键文件是否存在
            critical_files = [
                os.path.join(self.workspace_root, ".openclaw", "agent_state.json"),
                os.path.join(self.workspace_root, ".openclaw", "orchestrator", "tasks.json"),
                os.path.join(self.workspace_root, ".openclaw", "plan_queue"),
            ]

            file_status = {}
            missing_count = 0
            total_count = len(critical_files)

            for file_path in critical_files:
                exists = os.path.exists(file_path)
                file_status[
                    os.path.basename(file_path) if os.path.isfile(file_path) else file_path
                ] = exists
                if not exists:
                    missing_count += 1

            # 完整性评分：存在的文件比例
            integrity_score = (
                (total_count - missing_count) / total_count if total_count > 0 else 0.0
            )

            return StabilityMetric(
                metric_id="data_integrity",
                metric_type="data_integrity",
                value=integrity_score,
                unit="ratio",
                source="file system check",
                timestamp=datetime.now().isoformat(),
                context={
                    "file_status": file_status,
                    "missing_count": missing_count,
                    "total_count": total_count,
                    "critical_files": critical_files,
                },
            )
        except Exception as e:
            logger.warning(f"数据完整性指标收集失败: {e}")
            return None

    def _get_queue_consumer_status(self) -> Dict[str, Any]:
        """获取队列消费者状态（简化实现）"""
        try:
            # 检查队列目录
            queue_dir = os.path.join(self.workspace_root, ".openclaw", "plan_queue")
            if not os.path.exists(queue_dir):
                return {"consumer_status": "empty", "pending_count": 0}

            # 查找最新的队列文件
            queue_files = glob.glob(os.path.join(queue_dir, "*.json"))
            if not queue_files:
                return {"consumer_status": "empty", "pending_count": 0}

            latest_file = max(queue_files, key=os.path.getmtime)
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 解析队列状态
            items = data.get("items", {})
            pending_count = 0
            running_count = 0
            for item_id, item in items.items():
                status = item.get("status", "")
                if status == "pending":
                    pending_count += 1
                elif status == "running":
                    running_count += 1

            consumer_status = "empty"
            if running_count > 0:
                consumer_status = "running"
            elif pending_count > 0:
                consumer_status = "no_consumer"

            return {
                "consumer_status": consumer_status,
                "pending_count": pending_count,
                "running_count": running_count,
                "queue_file": os.path.basename(latest_file),
            }
        except Exception as e:
            logger.warning(f"队列状态获取失败: {e}")
            return {"consumer_status": "unknown", "pending_count": 0}

    def _get_runtime_status(self) -> Dict[str, Any]:
        """获取运行时状态（简化实现）"""
        try:
            # 检查是否有活动的任务或队列
            # 这里简化：检查任务文件的最新修改时间
            tasks_path = os.path.join(
                self.workspace_root, ".openclaw", "orchestrator", "tasks.json"
            )
            if os.path.exists(tasks_path):
                mtime = os.path.getmtime(tasks_path)
                age_minutes = (datetime.now().timestamp() - mtime) / 60

                # 如果任务文件最近5分钟内被修改，认为有活动
                is_active = age_minutes < 5

                return {
                    "isActive": is_active,
                    "last_updated_minutes": age_minutes,
                    "source": "tasks.json",
                }
            else:
                return {"isActive": False, "source": "no tasks file"}
        except Exception as e:
            logger.warning(f"运行时状态获取失败: {e}")
            return {"isActive": False, "source": "error"}

    def evaluate_alerts(self, metrics: List[StabilityMetric]) -> List[Alert]:
        """评估指标，生成告警"""
        alerts = []

        for metric in metrics:
            metric_alerts = self._evaluate_metric_alerts(metric)
            alerts.extend(metric_alerts)

        # 按严重程度排序
        alerts.sort(key=lambda x: x.severity)
        logger.info(f"生成 {len(alerts)} 个告警")
        return alerts

    def _evaluate_metric_alerts(self, metric: StabilityMetric) -> List[Alert]:
        """评估单个指标的告警"""
        alerts = []
        metric_config = self.config.get("stability_metrics", {}).get(metric.metric_type)

        if not metric_config:
            logger.debug(f"指标类型 {metric.metric_type} 无配置，跳过告警评估")
            return alerts

        thresholds = metric_config.get("thresholds", {})

        # 根据指标类型应用不同的评估逻辑
        if metric.metric_type == "availability":
            # 可用性指标：基于值评估
            if metric.value == 0.0:
                # 完全不可用
                alert_level = "P0"
                threshold_info = thresholds.get("P0", {})
                message = "系统完全不可用 - 运行时无活动或队列消费者停止"
            elif metric.value < 0.8:
                # 降级
                alert_level = "P1"
                threshold_info = thresholds.get("P1", {})
                message = "系统降级 - 部分组件异常但仍在运行"
            elif metric.value < 1.0:
                # 有警告
                alert_level = "P2"
                threshold_info = thresholds.get("P2", {})
                message = "系统可用但有警告 - 存在非关键问题"
            else:
                # 完全可用，无告警
                return alerts

            alerts.append(self._create_alert(metric, alert_level, message, threshold_info))

        elif metric.metric_type in ["response_time", "error_rate"]:
            # 数值型指标：与阈值比较
            for level in ["P0", "P1", "P2"]:
                threshold = thresholds.get(level)
                if not threshold:
                    continue

                threshold_value = threshold.get("value")
                condition = threshold.get("condition", ">")

                if threshold_value is None:
                    continue

                # 检查条件
                triggered = False
                if condition == ">":
                    triggered = metric.value > threshold_value
                elif condition == ">=":
                    triggered = metric.value >= threshold_value
                elif condition == "<":
                    triggered = metric.value < threshold_value
                elif condition == "<=":
                    triggered = metric.value <= threshold_value
                elif condition == "==":
                    triggered = metric.value == threshold_value

                if triggered:
                    message = threshold.get("message", f"{metric.metric_id} 触发 {level} 阈值")
                    alerts.append(self._create_alert(metric, level, message, threshold))
                    # 只触发最严重的告警（数值型指标可能同时触发多个等级）
                    break

        elif metric.metric_type == "data_integrity":
            # 数据完整性指标
            if metric.value < 0.5:
                alert_level = "P0"
                threshold_info = thresholds.get("P0", {})
                message = "关键数据源缺失，系统状态不可信"
            elif metric.value < 0.8:
                alert_level = "P1"
                threshold_info = thresholds.get("P1", {})
                message = "数据源不完整，可能影响监控准确性"
            elif metric.value < 1.0:
                alert_level = "P2"
                threshold_info = thresholds.get("P2", {})
                message = "数据源存在格式问题，建议修复"
            else:
                return alerts

            alerts.append(self._create_alert(metric, alert_level, message, threshold_info))

        return alerts

    def _create_alert(
        self,
        metric: StabilityMetric,
        level: str,
        message: str,
        threshold: Dict[str, Any],
    ) -> Alert:
        """创建告警对象"""
        level_severity = {"P0": 0, "P1": 1, "P2": 2}

        # 获取默认处置动作
        default_actions = self.config.get("default_actions", {}).get(level, [])

        return Alert(
            alert_id=f"{metric.metric_id}_{level}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            metric_id=metric.metric_id,
            alert_level=level,
            message=message,
            threshold=threshold,
            timestamp=datetime.now().isoformat(),
            severity=level_severity.get(level, 2),
            actions=default_actions,
        )

    def generate_report(
        self, metrics: List[StabilityMetric], alerts: List[Alert]
    ) -> Dict[str, Any]:
        """生成稳定性报告"""
        # 计算总体稳定性状态
        has_p0 = any(alert.severity == 0 for alert in alerts)
        has_p1 = any(alert.severity == 1 for alert in alerts)

        if has_p0:
            overall_status = "unstable"
            stability_level = "P0"
        elif has_p1:
            overall_status = "degraded"
            stability_level = "P1"
        elif alerts:
            overall_status = "stable_with_warnings"
            stability_level = "P2"
        else:
            overall_status = "stable"
            stability_level = "none"

        # 检查数据完整性
        data_integrity_metric = next(
            (m for m in metrics if m.metric_type == "data_integrity"), None
        )
        has_sufficient_data = data_integrity_metric and data_integrity_metric.value > 0.5

        # 应用门禁规则：没有健康数据时，不能宣称MVP运行稳定
        if not has_sufficient_data:
            overall_status = "unknown"
            stability_level = "P0"

        return {
            "report_id": f"stability_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "stability_level": stability_level,
            "has_sufficient_data": has_sufficient_data,
            "metric_count": len(metrics),
            "alert_count": len(alerts),
            "alerts_by_severity": {
                "P0": len([a for a in alerts if a.severity == 0]),
                "P1": len([a for a in alerts if a.severity == 1]),
                "P2": len([a for a in alerts if a.severity == 2]),
            },
            "metrics": [asdict(m) for m in metrics],
            "alerts": [asdict(a) for a in alerts],
            "mvp_stability_claim": overall_status == "stable",
            "gate_violations": not has_sufficient_data,
            "config_version": "1.0",
        }


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=== OpenHuman MVP 稳定性指标收集器 ===\n")

    # 初始化收集器
    collector = StabilityMetricsCollector()

    # 收集指标
    print("1. 收集稳定性指标...")
    metrics = collector.collect_metrics()

    if not metrics:
        print("   ❌ 未收集到任何指标")
        sys.exit(1)

    print(f"   ✅ 收集到 {len(metrics)} 个指标")
    for metric in metrics:
        print(f"      - {metric.metric_id}: {metric.value} {metric.unit}")

    # 评估告警
    print("\n2. 评估告警等级...")
    alerts = collector.evaluate_alerts(metrics)

    if alerts:
        print(f"   ⚠️  生成 {len(alerts)} 个告警:")
        for alert in alerts:
            print(f"      - {alert.alert_level}: {alert.message}")
    else:
        print("   ✅ 无告警")

    # 生成报告
    print("\n3. 生成稳定性报告...")
    report = collector.generate_report(metrics, alerts)

    # 输出报告摘要
    print(f"   整体状态: {report['overall_status']}")
    print(f"   稳定性等级: {report['stability_level']}")
    print(f"   MVP稳定性声明: {'✅ 稳定' if report['mvp_stability_claim'] else '❌ 不稳定'}")
    print(f"   数据完整性: {'✅ 充足' if report['has_sufficient_data'] else '❌ 不足'}")

    # 保存报告到文件
    report_file = os.path.join(project_root, "workspace", "stability_report.json")
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n4. 报告已保存: {report_file}")

    # 输出门禁检查结果
    if report["gate_violations"]:
        print("\n⚠️  门禁检查失败: 健康数据不足，不能宣称MVP运行稳定")
        sys.exit(1)
    else:
        print("\n✅ 门禁检查通过")

    print("\n=== 稳定性指标收集完成 ===")


if __name__ == "__main__":
    main()
