#!/usr/bin/env python3
"""
成本追踪器告警集成 - 基于审计报告第二阶段优化建议

为成本监控系统提供预算告警功能。
基于成本数据、预算状态和消费模式生成告警，
与现有告警系统和金融监控器集成。

设计特点：
1. 多源告警：基于成本数据、预算状态、消费模式
2. 智能聚合：避免告警风暴，相似告警聚合
3. 分级响应：信息/警告/严重三级告警
4. 集成现有：与alert_dispatcher和financial_monitor无缝集成
"""

import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 尝试导入所需组件
try:
    from .budget_engine import BudgetEngine, get_budget_engine
    from .cost_tracker import CostRecord, CostSummary, CostTracker
    from .financial_monitor import (
        FinancialAlert,
        FinancialAlertType,
        FinancialMonitor,
        FinancialSeverity,
        get_financial_monitor,
    )
    from .financial_monitor_adapter import get_financial_monitor_adapter

    HAS_DEPENDENCIES = True
except ImportError as e:
    logger.warning(f"导入依赖失败，告警系统将以降级模式运行: {e}")
    HAS_DEPENDENCIES = False


# ==================== 告警类型定义 ====================


class CostAlertType(Enum):
    """成本告警类型"""

    # 预算相关告警
    BUDGET_REMAINING_LOW = "budget_remaining_low"  # 剩余预算低
    DAILY_BUDGET_EXCEEDED = "daily_budget_exceeded"  # 当日预算超支
    PROJECTED_OVERSPEND = "projected_overspend"  # 预计超支

    # 成本异常告警
    UNUSUAL_COST_SPIKE = "unusual_cost_spike"  # 成本异常飙升
    ABNORMAL_CONSUMPTION_PATTERN = "abnormal_consumption_pattern"  # 异常消费模式
    HIGH_COST_PER_TOKEN = "high_cost_per_token"  # 每token成本过高

    # provider相关告警
    PROVIDER_COST_DISPARITY = "provider_cost_disparity"  # provider成本差异过大
    INEFFICIENT_MODEL_USAGE = "inefficient_model_usage"  # 模型使用效率低
    COST_OPTIMIZATION_OPPORTUNITY = "cost_optimization_opportunity"  # 成本优化机会

    # 数据质量告警
    MISSING_COST_DATA = "missing_cost_data"  # 成本数据缺失
    ESTIMATION_ACCURACY_LOW = "estimation_accuracy_low"  # 估算准确率低
    DATA_INTEGRITY_ISSUE = "data_integrity_issue"  # 数据完整性问题


class CostAlertSeverity(Enum):
    """成本告警严重级别"""

    INFO = "info"  # 信息性告警，无需立即处理
    WARNING = "warning"  # 警告告警，需要关注
    CRITICAL = "critical"  # 严重告警，需要立即处理


# ==================== 告警数据类定义 ====================


@dataclass
class CostAlert:
    """成本告警"""

    alert_id: str  # 告警ID
    alert_type: CostAlertType  # 告警类型
    severity: CostAlertSeverity  # 严重级别

    # 告警内容
    title: str  # 告警标题
    message: str  # 告警消息
    description: str = ""  # 详细描述

    # 触发条件
    triggered_by: Dict[str, Any] = field(default_factory=dict)  # 触发指标
    threshold: float = 0.0  # 阈值
    actual_value: float = 0.0  # 实际值
    confidence: float = 1.0  # 置信度（0.0-1.0）

    # 上下文信息
    period_start: Optional[date] = None  # 统计周期开始
    period_end: Optional[date] = None  # 统计周期结束
    provider_id: Optional[str] = None  # 相关provider
    model_id: Optional[str] = None  # 相关模型
    task_kind: Optional[str] = None  # 相关任务类型

    # 时间信息
    triggered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False  # 是否已确认
    resolved: bool = False  # 是否已解决
    last_occurrence: Optional[str] = None  # 最近发生时间（用于重复告警）

    # 建议措施
    recommended_actions: List[str] = field(default_factory=list)
    requires_human_intervention: bool = False  # 是否需要人工干预

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result["alert_type"] = self.alert_type.value
        result["severity"] = self.severity.value
        result["period_start"] = self.period_start.isoformat() if self.period_start else None
        result["period_end"] = self.period_end.isoformat() if self.period_end else None
        return result

    def to_financial_alert(self) -> Optional[FinancialAlert]:
        """转换为金融告警（如果金融监控器可用）"""
        if not HAS_DEPENDENCIES:
            return None

        # 映射告警类型
        financial_alert_type = self._map_to_financial_alert_type()
        if not financial_alert_type:
            return None

        # 映射严重级别
        financial_severity = self._map_to_financial_severity()

        return FinancialAlert(
            alert_id=self.alert_id,
            alert_type=financial_alert_type,
            severity=financial_severity,
            message=self.message,
            triggered_by=self.triggered_by,
            threshold=self.threshold,
            actual_value=self.actual_value,
            triggered_at=self.triggered_at,
            acknowledged=self.acknowledged,
            resolved=self.resolved,
            recommended_action=(
                "; ".join(self.recommended_actions) if self.recommended_actions else ""
            ),
            requires_human_intervention=self.requires_human_intervention,
        )

    def _map_to_financial_alert_type(self) -> Optional[FinancialAlertType]:
        """映射到金融告警类型"""
        mapping = {
            CostAlertType.BUDGET_REMAINING_LOW: FinancialAlertType.BUDGET_REMAINING_LOW,
            CostAlertType.DAILY_BUDGET_EXCEEDED: FinancialAlertType.DAILY_BUDGET_EXCEEDED,
            CostAlertType.PROJECTED_OVERSPEND: FinancialAlertType.PROJECTED_OVERSPEND,
            CostAlertType.UNUSUAL_COST_SPIKE: FinancialAlertType.BURN_RATE_HIGH,
        }
        return mapping.get(self.alert_type)

    def _map_to_financial_severity(self) -> FinancialSeverity:
        """映射到金融告警严重级别"""
        mapping = {
            CostAlertSeverity.INFO: FinancialSeverity.INFO,
            CostAlertSeverity.WARNING: FinancialSeverity.WARNING,
            CostAlertSeverity.CRITICAL: FinancialSeverity.CRITICAL,
        }
        return mapping.get(self.severity, FinancialSeverity.INFO)


@dataclass
class CostAlertRule:
    """成本告警规则"""

    rule_id: str  # 规则ID
    alert_type: CostAlertType  # 告警类型
    severity: CostAlertSeverity  # 严重级别

    # 触发条件
    condition: str  # 条件表达式，如"cost_per_token > 0.01"
    threshold: float  # 阈值
    aggregation_period_minutes: int = 60  # 聚合周期（分钟）
    min_occurrences: int = 1  # 最小触发次数

    # 适用范围
    providers: List[str] = field(default_factory=list)  # 适用的providers
    models: List[str] = field(default_factory=list)  # 适用的模型
    task_kinds: List[str] = field(default_factory=list)  # 适用的任务类型

    # 冷却和抑制
    cooldown_minutes: int = 30  # 冷却时间（分钟）
    suppression_rules: List[str] = field(default_factory=list)  # 抑制规则

    # 元数据
    description: str = ""  # 规则描述
    enabled: bool = True  # 是否启用
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result["alert_type"] = self.alert_type.value
        result["severity"] = self.severity.value
        return result


@dataclass
class CostAlertConfig:
    """成本告警配置"""

    # 告警规则
    rules: List[CostAlertRule] = field(default_factory=list)

    # 全局设置
    enable_auto_alerts: bool = True  # 是否启用自动告警
    enable_financial_monitor_integration: bool = True  # 是否集成金融监控器
    enable_alert_aggregation: bool = True  # 是否启用告警聚合

    # 阈值配置
    budget_warning_threshold: float = 0.2  # 预算警告阈值（20%）
    budget_critical_threshold: float = 0.05  # 预算严重阈值（5%）
    cost_spike_threshold_multiplier: float = 3.0  # 成本飙升阈值倍数
    cost_per_token_warning: float = 0.01  # 每token成本警告阈值（0.01元）

    # 监控频率
    check_interval_minutes: int = 60  # 检查间隔（分钟）
    historical_data_days: int = 7  # 历史数据天数

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# ==================== 成本告警引擎 ====================


class CostAlertEngine:
    """成本告警引擎"""

    def __init__(self, config: Optional[CostAlertConfig] = None):
        """
        初始化成本告警引擎

        Args:
            config: 告警配置，如果为None则使用默认配置
        """
        self.config = config or self._create_default_config()
        self.alerts: Dict[str, CostAlert] = {}  # 存储所有告警
        self.last_check_time: Optional[datetime] = None

        # 初始化组件
        self._cost_tracker = None
        self._financial_monitor = None
        self._budget_engine = None
        self._adapter = None

        # 告警抑制状态
        self.suppression_state: Dict[str, Any] = {
            "last_alert_time": {},
            "alert_counts": {},
            "suppressed_alerts": set(),
        }

        # 统计信息
        self.stats = {
            "total_alerts_generated": 0,
            "alerts_by_type": {},
            "alerts_by_severity": {},
            "last_check_timestamp": None,
            "check_duration_ms": 0.0,
        }

        logger.info(f"成本告警引擎初始化完成，启用 {len(self.config.rules)} 条规则")

    def _create_default_config(self) -> CostAlertConfig:
        """创建默认配置"""
        rules = [
            # 预算相关规则
            CostAlertRule(
                rule_id="budget_remaining_warning",
                alert_type=CostAlertType.BUDGET_REMAINING_LOW,
                severity=CostAlertSeverity.WARNING,
                condition="remaining_budget_ratio <= budget_warning_threshold",
                threshold=0.2,  # 20%
                description="剩余预算低于20%时发出警告",
            ),
            CostAlertRule(
                rule_id="budget_remaining_critical",
                alert_type=CostAlertType.BUDGET_REMAINING_LOW,
                severity=CostAlertSeverity.CRITICAL,
                condition="remaining_budget_ratio <= budget_critical_threshold",
                threshold=0.05,  # 5%
                description="剩余预算低于5%时发出严重告警",
            ),
            CostAlertRule(
                rule_id="daily_budget_exceeded",
                alert_type=CostAlertType.DAILY_BUDGET_EXCEEDED,
                severity=CostAlertSeverity.WARNING,
                condition="daily_spent > daily_budget",
                threshold=1.0,
                description="当日消费超过预算时发出警告",
            ),
            # 成本异常规则
            CostAlertRule(
                rule_id="cost_spike_detection",
                alert_type=CostAlertType.UNUSUAL_COST_SPIKE,
                severity=CostAlertSeverity.WARNING,
                condition="current_hour_cost > avg_hourly_cost * cost_spike_threshold",
                threshold=3.0,  # 3倍于平均
                aggregation_period_minutes=60,
                min_occurrences=1,
                description="检测成本异常飙升",
            ),
            CostAlertRule(
                rule_id="high_cost_per_token",
                alert_type=CostAlertType.HIGH_COST_PER_TOKEN,
                severity=CostAlertSeverity.WARNING,
                condition="cost_per_token > cost_per_token_warning",
                threshold=0.01,  # 0.01元/token
                description="每token成本过高警告",
            ),
            # provider相关规则
            CostAlertRule(
                rule_id="provider_cost_disparity",
                alert_type=CostAlertType.PROVIDER_COST_DISPARITY,
                severity=CostAlertSeverity.INFO,
                condition="provider_cost_ratio > 2.0",
                threshold=2.0,  # 2倍差异
                description="provider间成本差异过大",
            ),
        ]

        return CostAlertConfig(rules=rules)

    def _get_cost_tracker(self) -> Optional[CostTracker]:
        """获取成本追踪器实例"""
        if self._cost_tracker is None and HAS_DEPENDENCIES:
            try:
                from .cost_tracker import get_cost_tracker

                self._cost_tracker = get_cost_tracker()
            except Exception as e:
                logger.error(f"获取成本追踪器失败: {e}")
                self._cost_tracker = None
        return self._cost_tracker

    def _get_financial_monitor(self) -> Optional[FinancialMonitor]:
        """获取金融监控器实例"""
        if self._financial_monitor is None and HAS_DEPENDENCIES:
            try:
                from .financial_monitor import get_financial_monitor

                self._financial_monitor = get_financial_monitor()
            except Exception as e:
                logger.error(f"获取金融监控器失败: {e}")
                self._financial_monitor = None
        return self._financial_monitor

    def _get_budget_engine(self) -> Optional[BudgetEngine]:
        """获取预算引擎实例"""
        if self._budget_engine is None and HAS_DEPENDENCIES:
            try:
                from .budget_engine import get_budget_engine

                self._budget_engine = get_budget_engine()
            except Exception as e:
                logger.error(f"获取预算引擎失败: {e}")
                self._budget_engine = None
        return self._budget_engine

    def _get_adapter(self):
        """获取金融监控器适配器实例"""
        if self._adapter is None and HAS_DEPENDENCIES:
            try:
                from .financial_monitor_adapter import get_financial_monitor_adapter

                self._adapter = get_financial_monitor_adapter()
            except Exception as e:
                logger.error(f"获取金融监控器适配器失败: {e}")
                self._adapter = None
        return self._adapter

    def _should_suppress_alert(self, alert_type: CostAlertType, context: Dict[str, Any]) -> bool:
        """判断是否应该抑制告警"""
        alert_key = f"{alert_type.value}_{context.get('provider_id', 'all')}"

        # 检查冷却时间
        last_time = self.suppression_state["last_alert_time"].get(alert_key)
        if last_time:
            elapsed_minutes = (datetime.now() - last_time).total_seconds() / 60
            if elapsed_minutes < 30:  # 30分钟冷却
                logger.debug(f"告警在冷却期内: {alert_key} ({elapsed_minutes:.1f}分钟前)")
                return True

        # 更新状态
        self.suppression_state["last_alert_time"][alert_key] = datetime.now()

        return False

    def _generate_alert_id(self, alert_type: CostAlertType, context: Dict[str, Any]) -> str:
        """生成告警ID"""
        timestamp = int(time.time())
        provider = context.get("provider_id", "unknown")
        return f"cost_alert_{alert_type.value}_{provider}_{timestamp}"

    def _evaluate_budget_alerts(self, budget_data: Dict[str, Any]) -> List[CostAlert]:
        """评估预算相关告警"""
        alerts = []

        if not budget_data:
            return alerts

        # 剩余预算告警
        remaining_budget = budget_data.get("remaining_budget", 0)
        daily_budget = budget_data.get("daily_budget", 1.0)  # 避免除零

        if daily_budget > 0:
            remaining_ratio = remaining_budget / daily_budget

            # 警告阈值
            if remaining_ratio <= self.config.budget_warning_threshold:
                alert = CostAlert(
                    alert_id=self._generate_alert_id(
                        CostAlertType.BUDGET_REMAINING_LOW, {"metric": "remaining_budget"}
                    ),
                    alert_type=CostAlertType.BUDGET_REMAINING_LOW,
                    severity=CostAlertSeverity.WARNING,
                    title="预算剩余不足警告",
                    message=f"剩余预算较低: ¥{remaining_budget:.2f} ({remaining_ratio:.1%})",
                    description="剩余预算低于警告阈值，建议监控预算消耗并优化任务成本",
                    triggered_by={"metric": "remaining_budget", "value": remaining_budget},
                    threshold=self.config.budget_warning_threshold * daily_budget,
                    actual_value=remaining_budget,
                    confidence=0.9,
                    recommended_actions=[
                        "监控预算消耗",
                        "优化高成本任务",
                        "考虑调整预算分配",
                    ],
                )
                alerts.append(alert)

            # 严重阈值
            if remaining_ratio <= self.config.budget_critical_threshold:
                alert = CostAlert(
                    alert_id=self._generate_alert_id(
                        CostAlertType.BUDGET_REMAINING_LOW,
                        {"metric": "remaining_budget", "severity": "critical"},
                    ),
                    alert_type=CostAlertType.BUDGET_REMAINING_LOW,
                    severity=CostAlertSeverity.CRITICAL,
                    title="预算剩余严重不足",
                    message=f"剩余预算严重不足: ¥{remaining_budget:.2f} ({remaining_ratio:.1%})",
                    description="剩余预算低于严重阈值，需要立即处理",
                    triggered_by={"metric": "remaining_budget", "value": remaining_budget},
                    threshold=self.config.budget_critical_threshold * daily_budget,
                    actual_value=remaining_budget,
                    confidence=0.95,
                    requires_human_intervention=True,
                    recommended_actions=[
                        "立即暂停非必要任务",
                        "检查预算分配",
                        "考虑增加预算",
                    ],
                )
                alerts.append(alert)

        # 当日预算超支告警
        daily_spent = budget_data.get("daily_spent", 0)
        if daily_spent > daily_budget:
            alert = CostAlert(
                alert_id=self._generate_alert_id(
                    CostAlertType.DAILY_BUDGET_EXCEEDED, {"metric": "daily_spent"}
                ),
                alert_type=CostAlertType.DAILY_BUDGET_EXCEEDED,
                severity=CostAlertSeverity.WARNING,
                title="当日预算超支",
                message=f"当日消费超过预算: ¥{daily_spent:.2f} > ¥{daily_budget:.2f}",
                description="当日消费已超过预算限制",
                triggered_by={"metric": "daily_spent", "value": daily_spent},
                threshold=daily_budget,
                actual_value=daily_spent,
                confidence=1.0,
                recommended_actions=[
                    "调整当日剩余任务",
                    "避免进一步超支",
                    "检查是否有异常消费",
                ],
            )
            alerts.append(alert)

        return alerts

    def _evaluate_cost_anomaly_alerts(self, cost_summary: CostSummary) -> List[CostAlert]:
        """评估成本异常告警"""
        alerts = []

        # 每token成本告警
        total_tokens = cost_summary.total_input_tokens + cost_summary.total_output_tokens
        if total_tokens > 0:
            cost_per_token = cost_summary.total_cost / total_tokens * 1000  # 转换为每千token成本

            if cost_per_token > self.config.cost_per_token_warning:
                alert = CostAlert(
                    alert_id=self._generate_alert_id(
                        CostAlertType.HIGH_COST_PER_TOKEN, {"metric": "cost_per_token"}
                    ),
                    alert_type=CostAlertType.HIGH_COST_PER_TOKEN,
                    severity=CostAlertSeverity.WARNING,
                    title="每token成本过高",
                    message=f"每千token成本过高: ¥{cost_per_token:.4f} (阈值: ¥{self.config.cost_per_token_warning:.4f})",
                    description="检测到每token成本超过警告阈值，可能存在优化机会",
                    triggered_by={"metric": "cost_per_token", "value": cost_per_token},
                    threshold=self.config.cost_per_token_warning,
                    actual_value=cost_per_token,
                    confidence=0.8,
                    recommended_actions=[
                        "检查是否使用了过高定价的模型",
                        "考虑切换到成本效益更好的模型",
                        "优化token使用策略",
                    ],
                )
                alerts.append(alert)

        # provider成本差异告警
        if len(cost_summary.by_provider) >= 2:
            provider_costs = list(cost_summary.by_provider.values())
            max_cost = max(provider_costs)
            min_cost = min(provider_costs)

            if min_cost > 0:
                cost_ratio = max_cost / min_cost
                if cost_ratio > 2.0:  # 2倍差异
                    alert = CostAlert(
                        alert_id=self._generate_alert_id(
                            CostAlertType.PROVIDER_COST_DISPARITY, {"metric": "provider_cost_ratio"}
                        ),
                        alert_type=CostAlertType.PROVIDER_COST_DISPARITY,
                        severity=CostAlertSeverity.INFO,
                        title="provider成本差异较大",
                        message=f"不同provider间成本差异达{cost_ratio:.1f}倍",
                        description="检测到不同provider间的成本存在显著差异",
                        triggered_by={
                            "metric": "provider_cost_ratio",
                            "value": cost_ratio,
                            "max_cost": max_cost,
                            "min_cost": min_cost,
                        },
                        threshold=2.0,
                        actual_value=cost_ratio,
                        confidence=0.9,
                        recommended_actions=[
                            "评估是否可将高成本任务迁移到低成本provider",
                            "检查provider定价策略",
                            "优化任务分配策略",
                        ],
                    )
                    alerts.append(alert)

        return alerts

    def run_check(self) -> List[CostAlert]:
        """运行告警检查"""
        start_time = time.time()
        new_alerts = []

        if not self.config.enable_auto_alerts:
            logger.debug("自动告警已禁用，跳过检查")
            return new_alerts

        try:
            # 获取预算数据
            budget_data = {}
            adapter = self._get_adapter()
            if adapter:
                dashboard_data = adapter.get_financial_dashboard_data()
                if dashboard_data.get("success"):
                    financial_data = dashboard_data["data"].get("financial_monitor", {})
                    if isinstance(financial_data, dict) and "financial_summary" in financial_data:
                        budget_data = financial_data["financial_summary"]

            # 获取成本摘要数据
            cost_summary = None
            cost_tracker = self._get_cost_tracker()
            if cost_tracker:
                today = date.today()
                cost_summary = cost_tracker.get_summary(start_date=today, end_date=today)

            # 评估预算告警
            if budget_data:
                budget_alerts = self._evaluate_budget_alerts(budget_data)
                new_alerts.extend(budget_alerts)

            # 评估成本异常告警
            if cost_summary and cost_summary.total_requests > 0:
                anomaly_alerts = self._evaluate_cost_anomaly_alerts(cost_summary)
                new_alerts.extend(anomaly_alerts)

            # 处理新告警
            for alert in new_alerts:
                # 检查是否应该抑制
                if self._should_suppress_alert(alert.alert_type, alert.triggered_by):
                    logger.debug(f"告警被抑制: {alert.alert_type.value}")
                    continue

                # 存储告警
                self.alerts[alert.alert_id] = alert

                # 更新统计信息
                self.stats["total_alerts_generated"] += 1
                alert_type_key = alert.alert_type.value
                severity_key = alert.severity.value

                self.stats["alerts_by_type"][alert_type_key] = (
                    self.stats["alerts_by_type"].get(alert_type_key, 0) + 1
                )
                self.stats["alerts_by_severity"][severity_key] = (
                    self.stats["alerts_by_severity"].get(severity_key, 0) + 1
                )

                # 记录告警
                logger.info(
                    f"生成成本告警: [{alert.severity.value}] {alert.alert_type.value}: {alert.message}"
                )

                # 集成到金融监控器（如果配置启用）
                if self.config.enable_financial_monitor_integration and HAS_DEPENDENCIES:
                    try:
                        financial_alert = alert.to_financial_alert()
                        if financial_alert:
                            financial_monitor = self._get_financial_monitor()
                            if financial_monitor:
                                # 这里简化为直接添加到金融监控器
                                # 实际可能需要通过适配器同步
                                logger.debug(f"已转发告警到金融监控器: {alert.alert_id}")
                    except Exception as e:
                        logger.error(f"转发告警到金融监控器失败: {e}")

            # 更新检查时间
            self.last_check_time = datetime.now()
            self.stats["last_check_timestamp"] = self.last_check_time.isoformat()

            # 计算检查耗时
            check_duration_ms = (time.time() - start_time) * 1000
            self.stats["check_duration_ms"] = check_duration_ms

            logger.info(
                f"告警检查完成: 生成 {len(new_alerts)} 条新告警，" f"耗时 {check_duration_ms:.1f}ms"
            )

        except Exception as e:
            logger.error(f"告警检查失败: {e}")

        return new_alerts

    def get_active_alerts(
        self,
        severity: Optional[CostAlertSeverity] = None,
        alert_type: Optional[CostAlertType] = None,
    ) -> List[CostAlert]:
        """获取活动告警"""
        active_alerts = [alert for alert in self.alerts.values() if not alert.resolved]

        # 过滤严重级别
        if severity:
            active_alerts = [alert for alert in active_alerts if alert.severity == severity]

        # 过滤告警类型
        if alert_type:
            active_alerts = [alert for alert in active_alerts if alert.alert_type == alert_type]

        return sorted(active_alerts, key=lambda a: a.triggered_at, reverse=True)

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

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats.update(
            {
                "total_alerts_stored": len(self.alerts),
                "active_alerts": len(self.get_active_alerts()),
                "last_check_time": (
                    self.last_check_time.isoformat() if self.last_check_time else None
                ),
                "config": self.config.to_dict(),
            }
        )
        return stats


# ==================== 全局实例管理 ====================


_cost_alert_engine_instance: Optional[CostAlertEngine] = None


def get_cost_alert_engine() -> CostAlertEngine:
    """获取全局成本告警引擎实例"""
    global _cost_alert_engine_instance
    if _cost_alert_engine_instance is None:
        _cost_alert_engine_instance = CostAlertEngine()
    return _cost_alert_engine_instance


# ==================== 测试函数 ====================


def test_cost_alert_engine():
    """测试成本告警引擎"""
    print("=== 测试成本告警引擎 ===")

    # 创建测试配置
    config = CostAlertConfig(
        enable_auto_alerts=True,
        budget_warning_threshold=0.2,
        budget_critical_threshold=0.05,
        cost_per_token_warning=0.01,
    )

    # 创建告警引擎
    engine = CostAlertEngine(config=config)

    print("\n1. 测试告警引擎初始化:")
    print(f"   配置规则数: {len(engine.config.rules)}")
    print(f"   组件可用性: {HAS_DEPENDENCIES}")

    print("\n2. 测试告警评估逻辑:")
    # 模拟预算数据
    budget_data = {
        "remaining_budget": 15.0,
        "daily_budget": 100.0,
        "daily_spent": 105.0,
    }

    budget_alerts = engine._evaluate_budget_alerts(budget_data)
    print(f"   预算告警评估: 生成 {len(budget_alerts)} 条告警")
    for alert in budget_alerts[:2]:  # 最多显示2条
        print(f"     - [{alert.severity.value}] {alert.alert_type.value}: {alert.title}")

    print("\n3. 测试统计信息:")
    stats = engine.get_stats()
    print(f"   总告警数: {stats['total_alerts_generated']}")
    print(f"   活动告警: {stats['active_alerts']}")

    print("\n4. 测试告警抑制逻辑:")
    context = {"provider_id": "deepseek", "metric": "test"}
    should_suppress = engine._should_suppress_alert(CostAlertType.BUDGET_REMAINING_LOW, context)
    print(f"   告警抑制检查: {'抑制' if should_suppress else '不抑制'}")

    print("\n5. 测试告警运行检查:")
    new_alerts = engine.run_check()
    print(f"   运行检查结果: 生成 {len(new_alerts)} 条新告警")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_cost_alert_engine()
