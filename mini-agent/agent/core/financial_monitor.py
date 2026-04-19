#!/usr/bin/env python3
"""
金融监控模型 - 最小资金监控骨架

定义 remaining_budget、daily_budget、burn_rate、severity 等字段，
支持 warning / critical 两级告警。

与现有预算引擎集成，提供简化的监控接口。
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== 枚举定义 ====================


class FinancialSeverity(Enum):
    """金融告警严重级别"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class FinancialAlertType(Enum):
    """金融告警类型"""

    BUDGET_REMAINING_LOW = "budget_remaining_low"
    BURN_RATE_HIGH = "burn_rate_high"
    DAILY_BUDGET_EXCEEDED = "daily_budget_exceeded"
    PROJECTED_OVERSPEND = "projected_overspend"
    MODE_CHANGE = "mode_change"


# ==================== 数据类定义 ====================


@dataclass
class FinancialMetrics:
    """金融监控指标"""

    # 预算指标
    remaining_budget: float = 0.0
    daily_budget: float = 0.0
    weekly_budget: float = 0.0
    monthly_budget: float = 0.0

    # 消费指标
    burn_rate: float = 0.0  # 元/小时
    daily_spent: float = 0.0
    weekly_spent: float = 0.0
    monthly_spent: float = 0.0

    # 使用率指标
    utilization: float = 0.0  # 0.0-1.0
    days_until_reset: int = 0

    # 模式与状态
    current_mode: str = "normal"
    mode_reason: str = ""

    # 时间戳
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    period_start: str = ""
    period_end: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FinancialAlert:
    """金融告警"""

    alert_id: str
    alert_type: FinancialAlertType
    severity: FinancialSeverity
    message: str

    # 触发指标
    triggered_by: Dict[str, Any] = field(default_factory=dict)
    threshold: float = 0.0
    actual_value: float = 0.0

    # 时间戳
    triggered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    resolved: bool = False

    # 建议措施
    recommended_action: str = ""
    requires_human_intervention: bool = False

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["alert_type"] = self.alert_type.value
        result["severity"] = self.severity.value
        return result


@dataclass
class FinancialMonitorConfig:
    """金融监控配置"""

    # 告警阈值
    warning_threshold_remaining: float = 0.2  # 剩余预算20%时警告
    critical_threshold_remaining: float = 0.05  # 剩余预算5%时严重告警

    warning_burn_rate_multiplier: float = 1.5  # 燃烧率超过预算/24小时1.5倍时警告
    critical_burn_rate_multiplier: float = 3.0  # 超过3倍时严重告警

    # 监控选项
    check_interval_minutes: int = 60
    enable_auto_alerts: bool = True
    enable_projection: bool = True

    # 通知选项
    notify_on_warning: bool = True
    notify_on_critical: bool = True
    dry_run: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==================== 金融监控引擎 ====================


class FinancialMonitor:
    """金融监控引擎"""

    def __init__(self, config: Optional[FinancialMonitorConfig] = None):
        self.config = config or FinancialMonitorConfig()
        self.alerts: Dict[str, FinancialAlert] = {}
        self.metrics_history: List[FinancialMetrics] = []

        logger.info(
            f"金融监控引擎初始化完成，告警阈值: 警告={self.config.warning_threshold_remaining}, 严重={self.config.critical_threshold_remaining}"
        )

    def _get_budget_engine(self):
        """获取预算引擎实例"""
        try:
            from .budget_engine import get_budget_engine

            return get_budget_engine()
        except ImportError:
            logger.warning("预算引擎不可用，使用模拟数据")
            return None

    def collect_metrics(self) -> FinancialMetrics:
        """收集金融指标"""
        try:
            engine = self._get_budget_engine()

            if engine:
                # 从预算引擎获取状态
                state = engine.get_structured_state()
                budget_state = state["budget_state"]
                health = state["health"]

                # 计算每日预算（简化：使用周期预算/周期天数）
                period_budget = budget_state["period_budget"]
                period_start = datetime.fromisoformat(budget_state["period_start"])
                period_end = datetime.fromisoformat(budget_state["period_end"])
                period_days = max(1, (period_end - period_start).days + 1)
                daily_budget = period_budget / period_days

                # 计算已消费（当日）
                # 简化：假设consumed是当日消费（实际budget_engine中consumed是周期累计）
                daily_spent = budget_state.get("consumed_today", budget_state["consumed"])

                metrics = FinancialMetrics(
                    remaining_budget=budget_state["remaining"],
                    daily_budget=daily_budget,
                    weekly_budget=(
                        period_budget
                        if budget_state.get("reset_period") == "weekly"
                        else daily_budget * 7
                    ),
                    monthly_budget=(
                        period_budget
                        if budget_state.get("reset_period") == "monthly"
                        else daily_budget * 30
                    ),
                    burn_rate=budget_state.get("burn_rate", 0.0),
                    daily_spent=daily_spent,
                    weekly_spent=budget_state.get("consumed_weekly", budget_state["consumed"]),
                    monthly_spent=budget_state.get("consumed_monthly", budget_state["consumed"]),
                    utilization=health["utilization"],
                    days_until_reset=health["days_until_reset"],
                    current_mode=budget_state["current_mode"],
                    mode_reason=budget_state["mode_reason"],
                    period_start=budget_state["period_start"],
                    period_end=budget_state["period_end"],
                )
            else:
                # 模拟数据（用于测试）
                metrics = FinancialMetrics(
                    remaining_budget=150.0,
                    daily_budget=100.0,
                    weekly_budget=700.0,
                    monthly_budget=3000.0,
                    burn_rate=5.2,
                    daily_spent=45.0,
                    weekly_spent=320.0,
                    monthly_spent=1200.0,
                    utilization=0.4,
                    days_until_reset=3,
                    current_mode="normal",
                    mode_reason="模拟数据",
                    period_start=datetime.now().isoformat(),
                    period_end=datetime.now().isoformat(),
                )

            # 保存到历史记录
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 1000:  # 限制历史记录大小
                self.metrics_history = self.metrics_history[-1000:]

            return metrics

        except Exception as e:
            logger.error(f"收集金融指标失败: {e}")
            # 返回空指标
            return FinancialMetrics()

    def evaluate_alerts(self, metrics: FinancialMetrics) -> List[FinancialAlert]:
        """评估指标并生成告警"""
        new_alerts = []

        # 1. 剩余预算告警
        if metrics.remaining_budget > 0:
            remaining_ratio = metrics.remaining_budget / max(metrics.daily_budget, 1.0)

            if remaining_ratio <= self.config.critical_threshold_remaining:
                alert = FinancialAlert(
                    alert_id=f"budget_critical_{datetime.now().timestamp()}",
                    alert_type=FinancialAlertType.BUDGET_REMAINING_LOW,
                    severity=FinancialSeverity.CRITICAL,
                    message=f"剩余预算严重不足: ¥{metrics.remaining_budget:.2f} ({remaining_ratio:.1%})",
                    triggered_by={
                        "metric": "remaining_budget",
                        "value": metrics.remaining_budget,
                    },
                    threshold=self.config.critical_threshold_remaining * metrics.daily_budget,
                    actual_value=metrics.remaining_budget,
                    recommended_action="立即暂停非必要任务，考虑增加预算",
                    requires_human_intervention=True,
                )
                new_alerts.append(alert)

            elif remaining_ratio <= self.config.warning_threshold_remaining:
                alert = FinancialAlert(
                    alert_id=f"budget_warning_{datetime.now().timestamp()}",
                    alert_type=FinancialAlertType.BUDGET_REMAINING_LOW,
                    severity=FinancialSeverity.WARNING,
                    message=f"剩余预算较低: ¥{metrics.remaining_budget:.2f} ({remaining_ratio:.1%})",
                    triggered_by={
                        "metric": "remaining_budget",
                        "value": metrics.remaining_budget,
                    },
                    threshold=self.config.warning_threshold_remaining * metrics.daily_budget,
                    actual_value=metrics.remaining_budget,
                    recommended_action="监控预算消耗，优化任务成本",
                    requires_human_intervention=False,
                )
                new_alerts.append(alert)

        # 2. 燃烧率告警
        if metrics.burn_rate > 0 and metrics.daily_budget > 0:
            hourly_budget = metrics.daily_budget / 24
            burn_rate_ratio = metrics.burn_rate / hourly_budget if hourly_budget > 0 else 0

            if burn_rate_ratio >= self.config.critical_burn_rate_multiplier:
                alert = FinancialAlert(
                    alert_id=f"burnrate_critical_{datetime.now().timestamp()}",
                    alert_type=FinancialAlertType.BURN_RATE_HIGH,
                    severity=FinancialSeverity.CRITICAL,
                    message=f"消费速率过高: ¥{metrics.burn_rate:.2f}/小时 (预算的{burn_rate_ratio:.1f}倍)",
                    triggered_by={"metric": "burn_rate", "value": metrics.burn_rate},
                    threshold=self.config.critical_burn_rate_multiplier * hourly_budget,
                    actual_value=metrics.burn_rate,
                    recommended_action="立即检查任务成本，暂停高消费任务",
                    requires_human_intervention=True,
                )
                new_alerts.append(alert)

            elif burn_rate_ratio >= self.config.warning_burn_rate_multiplier:
                alert = FinancialAlert(
                    alert_id=f"burnrate_warning_{datetime.now().timestamp()}",
                    alert_type=FinancialAlertType.BURN_RATE_HIGH,
                    severity=FinancialSeverity.WARNING,
                    message=f"消费速率较高: ¥{metrics.burn_rate:.2f}/小时 (预算的{burn_rate_ratio:.1f}倍)",
                    triggered_by={"metric": "burn_rate", "value": metrics.burn_rate},
                    threshold=self.config.warning_burn_rate_multiplier * hourly_budget,
                    actual_value=metrics.burn_rate,
                    recommended_action="监控消费速率，优化资源使用",
                    requires_human_intervention=False,
                )
                new_alerts.append(alert)

        # 3. 每日预算超支告警
        if metrics.daily_spent > metrics.daily_budget:
            alert = FinancialAlert(
                alert_id=f"daily_over_{datetime.now().timestamp()}",
                alert_type=FinancialAlertType.DAILY_BUDGET_EXCEEDED,
                severity=FinancialSeverity.WARNING,
                message=f"当日预算超支: 已消费¥{metrics.daily_spent:.2f}，预算¥{metrics.daily_budget:.2f}",
                triggered_by={"metric": "daily_spent", "value": metrics.daily_spent},
                threshold=metrics.daily_budget,
                actual_value=metrics.daily_spent,
                recommended_action="调整当日剩余任务，避免进一步超支",
                requires_human_intervention=False,
            )
            new_alerts.append(alert)

        # 4. 模式变更告警
        if metrics.current_mode in ["critical", "paused"]:
            alert = FinancialAlert(
                alert_id=f"mode_{metrics.current_mode}_{datetime.now().timestamp()}",
                alert_type=FinancialAlertType.MODE_CHANGE,
                severity=(
                    FinancialSeverity.CRITICAL
                    if metrics.current_mode == "paused"
                    else FinancialSeverity.WARNING
                ),
                message=f"预算模式变更: {metrics.current_mode} - {metrics.mode_reason}",
                triggered_by={"metric": "current_mode", "value": metrics.current_mode},
                threshold=0,
                actual_value=0,
                recommended_action="检查预算状态，采取相应措施",
                requires_human_intervention=metrics.current_mode == "paused",
            )
            new_alerts.append(alert)

        # 存储新告警
        for alert in new_alerts:
            self.alerts[alert.alert_id] = alert
            logger.info(
                f"生成金融告警: {alert.alert_type.value} - {alert.severity.value}: {alert.message}"
            )

        return new_alerts

    def get_active_alerts(
        self, severity: Optional[FinancialSeverity] = None
    ) -> List[FinancialAlert]:
        """获取活动告警"""
        alerts = [alert for alert in self.alerts.values() if not alert.resolved]

        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]

        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledged = True
            logger.info(f"告警已确认: {alert_id}")
            return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            logger.info(f"告警已解决: {alert_id}")
            return True
        return False

    def run_monitoring_cycle(self) -> Dict[str, Any]:
        """运行监控周期（收集指标 + 评估告警）"""
        # 收集指标
        metrics = self.collect_metrics()

        # 评估告警
        new_alerts = []
        if self.config.enable_auto_alerts:
            new_alerts = self.evaluate_alerts(metrics)

        # 返回监控结果
        return {
            "metrics": metrics.to_dict(),
            "new_alerts": [alert.to_dict() for alert in new_alerts],
            "active_alert_count": len(self.get_active_alerts()),
            "timestamp": datetime.now().isoformat(),
            "config": self.config.to_dict(),
        }

    def get_dashboard_payload(self) -> Dict[str, Any]:
        """获取仪表板负载（用于运营/资金summary）"""
        metrics = self.collect_metrics()
        active_alerts = self.get_active_alerts()

        # 计算健康评分（简化）
        health_score = 100
        if metrics.current_mode == "paused":
            health_score = 10
        elif metrics.current_mode == "critical":
            health_score = 30
        elif metrics.current_mode == "low":
            health_score = 60
        elif metrics.utilization > 0.8:
            health_score = 70

        # 构建仪表板负载
        return {
            "financial_summary": {
                "budget": {
                    "remaining": metrics.remaining_budget,
                    "daily": metrics.daily_budget,
                    "weekly": metrics.weekly_budget,
                    "monthly": metrics.monthly_budget,
                },
                "spending": {
                    "burn_rate": metrics.burn_rate,
                    "daily": metrics.daily_spent,
                    "weekly": metrics.weekly_spent,
                    "monthly": metrics.monthly_spent,
                },
                "utilization": metrics.utilization,
                "mode": metrics.current_mode,
                "health_score": health_score,
                "days_until_reset": metrics.days_until_reset,
            },
            "alerts_summary": {
                "critical": len(
                    [a for a in active_alerts if a.severity == FinancialSeverity.CRITICAL]
                ),
                "warning": len(
                    [a for a in active_alerts if a.severity == FinancialSeverity.WARNING]
                ),
                "info": len([a for a in active_alerts if a.severity == FinancialSeverity.INFO]),
                "total": len(active_alerts),
            },
            "recommendations": self._generate_recommendations(metrics, active_alerts),
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "source": "financial_monitor",
                "version": "1.0",
                "config": self.config.to_dict(),
            },
        }

    def _generate_recommendations(
        self, metrics: FinancialMetrics, alerts: List[FinancialAlert]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于模式
        if metrics.current_mode == "paused":
            recommendations.append("预算已耗尽，需要手动重置或等待周期重置")
        elif metrics.current_mode == "critical":
            recommendations.append("预算临界，仅执行核心任务，考虑增加预算")
        elif metrics.current_mode == "low":
            recommendations.append("预算较低，启用降级模式，优化任务成本")

        # 基于使用率
        if metrics.utilization > 0.9:
            recommendations.append("预算使用率超过90%，准备暂停非必要任务")
        elif metrics.utilization > 0.7:
            recommendations.append("预算使用率超过70%，监控预算消耗")

        # 基于燃烧率
        if metrics.burn_rate > metrics.daily_budget / 24 * 2:
            recommendations.append("消费速率较高，检查任务成本，优化资源使用")

        # 基于告警
        critical_alerts = [a for a in alerts if a.severity == FinancialSeverity.CRITICAL]
        if critical_alerts:
            recommendations.append(f"有{len(critical_alerts)}个严重告警需要处理")

        return recommendations


# ==================== 全局实例 ====================

_financial_monitor_instance: Optional[FinancialMonitor] = None


def get_financial_monitor() -> FinancialMonitor:
    """获取全局金融监控实例"""
    global _financial_monitor_instance
    if _financial_monitor_instance is None:
        _financial_monitor_instance = FinancialMonitor()
    return _financial_monitor_instance


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=== 金融监控模型测试 ===")

    # 创建监控器
    monitor = FinancialMonitor()

    print("\n1. 测试指标收集:")
    metrics = monitor.collect_metrics()
    print(f"   剩余预算: ¥{metrics.remaining_budget:.2f}")
    print(f"   每日预算: ¥{metrics.daily_budget:.2f}")
    print(f"   燃烧率: ¥{metrics.burn_rate:.2f}/小时")
    print(f"   使用率: {metrics.utilization:.1%}")
    print(f"   当前模式: {metrics.current_mode}")

    print("\n2. 测试告警评估:")
    new_alerts = monitor.evaluate_alerts(metrics)
    print(f"   生成告警数: {len(new_alerts)}")
    for alert in new_alerts[:3]:  # 最多显示3个
        print(f"     - [{alert.severity.value}] {alert.alert_type.value}: {alert.message}")

    print("\n3. 测试仪表板负载:")
    dashboard = monitor.get_dashboard_payload()
    print(f"   财务摘要:")
    print(f"     剩余预算: ¥{dashboard['financial_summary']['budget']['remaining']:.2f}")
    print(f"     健康评分: {dashboard['financial_summary']['health_score']}")
    print(f"   告警摘要:")
    print(
        f"     严重: {dashboard['alerts_summary']['critical']}, 警告: {dashboard['alerts_summary']['warning']}"
    )
    print(f"   建议: {len(dashboard['recommendations'])}条")

    print("\n4. 测试监控周期:")
    cycle_result = monitor.run_monitoring_cycle()
    print(f"   监控周期完成:")
    print(f"     新告警: {len(cycle_result['new_alerts'])}")
    print(f"     活动告警总数: {cycle_result['active_alert_count']}")

    print("\n=== 测试完成 ===")
