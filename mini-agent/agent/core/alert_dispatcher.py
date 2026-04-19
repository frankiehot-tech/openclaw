#!/usr/bin/env python3
"""
告警分发接口 - 最小告警分发骨架

可以是控制台/日志/artifact 先行，不强制真实外部发送。
至少保留 channel 选择和 message 结构。
"""

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== 枚举定义 ====================


class AlertChannel(Enum):
    """告警分发渠道"""

    CONSOLE = "console"
    LOG_FILE = "log_file"
    ARTIFACT_FILE = "artifact_file"
    # 预留外部渠道（未来扩展）
    # DISCORD = "discord"
    # EMAIL = "email"
    # SLACK = "slack"


class AlertPriority(Enum):
    """告警优先级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== 数据类定义 ====================


@dataclass
class AlertMessage:
    """告警消息结构"""

    alert_id: str
    title: str
    message: str
    priority: AlertPriority
    source: str  # 告警来源，如 "budget_monitor", "performance_monitor", "ops_automation"

    # 内容详情
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "warning"  # 兼容旧字段

    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None

    # 元数据
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["priority"] = self.priority.value
        result["source"] = self.source
        return result


@dataclass
class DispatcherConfig:
    """分发器配置"""

    # 启用渠道
    enabled_channels: List[AlertChannel] = field(
        default_factory=lambda: [
            AlertChannel.CONSOLE,
            AlertChannel.LOG_FILE,
            AlertChannel.ARTIFACT_FILE,
        ]
    )

    # 渠道特定配置
    console_show_colors: bool = True
    log_file_path: str = "logs/alerts.log"
    artifact_dir: str = "workspace/alert_artifacts"

    # 过滤规则
    min_priority: AlertPriority = AlertPriority.LOW  # 最低处理优先级
    dry_run: bool = True  # 是否真实发送（dry-run模式下只记录不真实发送）

    # 聚合选项
    deduplicate: bool = True
    deduplication_window_hours: int = 24

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["enabled_channels"] = [c.value for c in self.enabled_channels]
        result["min_priority"] = self.min_priority.value
        return result


# ==================== 渠道处理器 ====================


class ChannelHandler:
    """渠道处理器基类"""

    def __init__(self, config: DispatcherConfig):
        self.config = config

    def send(self, alert: AlertMessage) -> bool:
        """发送告警（子类实现）"""
        raise NotImplementedError

    def format_message(self, alert: AlertMessage) -> str:
        """格式化告警消息"""
        timestamp = datetime.fromisoformat(alert.created_at).strftime("%Y-%m-%d %H:%M:%S")

        # 颜色代码（用于控制台）
        color_codes = {
            AlertPriority.CRITICAL: "\033[91m",  # 红色
            AlertPriority.HIGH: "\033[93m",  # 黄色
            AlertPriority.MEDIUM: "\033[96m",  # 青色
            AlertPriority.LOW: "\033[92m",  # 绿色
        }
        reset_code = "\033[0m"

        # 构建消息
        lines = [
            f"[{timestamp}] [{alert.source.upper()}] [{alert.priority.value.upper()}]",
            f"  {alert.title}",
            f"  {alert.message}",
        ]

        # 添加详情（如果有）
        if alert.details:
            details_str = json.dumps(alert.details, ensure_ascii=False, indent=2)
            lines.append(f"  详情: {details_str}")

        # 添加标签（如果有）
        if alert.labels:
            labels_str = ", ".join([f"{k}={v}" for k, v in alert.labels.items()])
            lines.append(f"  标签: {labels_str}")

        message = "\n".join(lines)

        # 添加颜色（如果支持且启用）
        if hasattr(self.config, "console_show_colors") and self.config.console_show_colors:
            color = color_codes.get(alert.priority, "")
            message = f"{color}{message}{reset_code}"

        return message


class ConsoleHandler(ChannelHandler):
    """控制台处理器"""

    def send(self, alert: AlertMessage) -> bool:
        try:
            message = self.format_message(alert)
            print(message, file=sys.stderr)
            return True
        except Exception as e:
            logger.error(f"控制台发送告警失败: {e}")
            return False


class LogFileHandler(ChannelHandler):
    """日志文件处理器"""

    def __init__(self, config: DispatcherConfig):
        super().__init__(config)
        self.log_file = Path(config.log_file_path)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def send(self, alert: AlertMessage) -> bool:
        try:
            # 转换为JSON格式记录
            log_entry = {
                "timestamp": alert.created_at,
                "source": alert.source,
                "priority": alert.priority.value,
                "title": alert.title,
                "message": alert.message,
                "details": alert.details,
                "labels": alert.labels,
            }

            log_line = json.dumps(log_entry, ensure_ascii=False)

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")

            logger.debug(f"告警已写入日志文件: {self.log_file}")
            return True

        except Exception as e:
            logger.error(f"日志文件发送告警失败: {e}")
            return False


class ArtifactFileHandler(ChannelHandler):
    """Artifact文件处理器"""

    def __init__(self, config: DispatcherConfig):
        super().__init__(config)
        self.artifact_dir = Path(config.artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def send(self, alert: AlertMessage) -> bool:
        try:
            # 每个告警保存为单独的文件
            timestamp = datetime.fromisoformat(alert.created_at).strftime("%Y%m%d_%H%M%S")
            artifact_file = self.artifact_dir / f"alert_{timestamp}_{alert.alert_id}.json"

            artifact_data = {
                "alert": alert.to_dict(),
                "dispatched_at": datetime.now().isoformat(),
                "dispatcher_config": self.config.to_dict(),
                "artifact_version": "1.0",
            }

            with open(artifact_file, "w", encoding="utf-8") as f:
                json.dump(artifact_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"告警已保存为artifact: {artifact_file}")
            return True

        except Exception as e:
            logger.error(f"Artifact文件发送告警失败: {e}")
            return False


# ==================== 核心分发器 ====================


class AlertDispatcher:
    """告警分发器"""

    def __init__(self, config: Optional[DispatcherConfig] = None):
        self.config = config or DispatcherConfig()
        self.handlers = self._create_handlers()
        self.sent_alerts: Dict[str, datetime] = {}  # 用于去重

        logger.info(
            f"告警分发器初始化完成，启用渠道: {[c.value for c in self.config.enabled_channels]}"
        )

    def _create_handlers(self) -> Dict[AlertChannel, ChannelHandler]:
        """创建渠道处理器"""
        handlers = {}

        for channel in self.config.enabled_channels:
            if channel == AlertChannel.CONSOLE:
                handlers[channel] = ConsoleHandler(self.config)
            elif channel == AlertChannel.LOG_FILE:
                handlers[channel] = LogFileHandler(self.config)
            elif channel == AlertChannel.ARTIFACT_FILE:
                handlers[channel] = ArtifactFileHandler(self.config)
            else:
                logger.warning(f"未知的告警渠道: {channel}")

        return handlers

    def _should_deduplicate(self, alert: AlertMessage) -> bool:
        """检查是否应去重"""
        if not self.config.deduplicate:
            return False

        # 基于alert_id去重
        if alert.alert_id in self.sent_alerts:
            sent_time = self.sent_alerts[alert.alert_id]
            window = self.config.deduplication_window_hours
            if (datetime.now() - sent_time).total_seconds() < window * 3600:
                return True

        return False

    def _update_deduplication(self, alert: AlertMessage):
        """更新去重记录"""
        self.sent_alerts[alert.alert_id] = datetime.now()

        # 清理过期记录
        window = self.config.deduplication_window_hours
        cutoff = datetime.now().timestamp() - window * 3600

        self.sent_alerts = {
            alert_id: sent_time
            for alert_id, sent_time in self.sent_alerts.items()
            if sent_time.timestamp() > cutoff
        }

    def dispatch(self, alert: AlertMessage) -> Dict[AlertChannel, bool]:
        """分发告警"""
        results = {}

        # 检查优先级过滤
        priority_order = {
            AlertPriority.CRITICAL: 4,
            AlertPriority.HIGH: 3,
            AlertPriority.MEDIUM: 2,
            AlertPriority.LOW: 1,
        }

        if priority_order.get(alert.priority, 0) < priority_order.get(self.config.min_priority, 0):
            logger.debug(f"告警优先级低于最小阈值，跳过: {alert.alert_id} ({alert.priority.value})")
            return {channel: False for channel in self.handlers.keys()}

        # 检查去重
        if self._should_deduplicate(alert):
            logger.debug(f"告警已去重，跳过: {alert.alert_id}")
            return {channel: False for channel in self.handlers.keys()}

        # 分发到各个渠道
        for channel, handler in self.handlers.items():
            if self.config.dry_run:
                logger.info(f"[DRY-RUN] 将发送告警到 {channel.value}: {alert.title}")
                results[channel] = True
            else:
                try:
                    success = handler.send(alert)
                    results[channel] = success

                    if success:
                        logger.info(f"告警已发送到 {channel.value}: {alert.title}")
                    else:
                        logger.warning(f"告警发送到 {channel.value} 失败: {alert.title}")

                except Exception as e:
                    logger.error(f"告警发送到 {channel.value} 时出错: {e}")
                    results[channel] = False

        # 更新去重记录
        if any(results.values()):
            self._update_deduplication(alert)

        return results

    def dispatch_from_dict(self, alert_dict: Dict[str, Any]) -> Dict[AlertChannel, bool]:
        """从字典分发告警（便捷方法）"""
        try:
            # 转换字典为AlertMessage
            priority = AlertPriority(alert_dict.get("priority", "medium"))
            alert = AlertMessage(
                alert_id=alert_dict.get("alert_id", f"alert_{datetime.now().timestamp()}"),
                title=alert_dict.get("title", "未命名告警"),
                message=alert_dict.get("message", ""),
                priority=priority,
                source=alert_dict.get("source", "unknown"),
                details=alert_dict.get("details", {}),
                severity=alert_dict.get("severity", "warning"),
                labels=alert_dict.get("labels", {}),
                metadata=alert_dict.get("metadata", {}),
            )

            return self.dispatch(alert)

        except Exception as e:
            logger.error(f"从字典创建告警失败: {e}")
            return {}

    def dispatch_budget_alert(self, budget_alert: Dict[str, Any]) -> Dict[AlertChannel, bool]:
        """分发预算告警（适配预算引擎格式）"""
        try:
            # 预算引擎告警格式适配
            level_map = {
                "critical": AlertPriority.CRITICAL,
                "warning": AlertPriority.HIGH,
                "info": AlertPriority.MEDIUM,
            }

            alert = AlertMessage(
                alert_id=budget_alert.get("code", f"budget_{datetime.now().timestamp()}"),
                title=f"预算告警: {budget_alert.get('code', 'unknown')}",
                message=budget_alert.get("message", ""),
                priority=level_map.get(budget_alert.get("level", "warning"), AlertPriority.MEDIUM),
                source="budget_monitor",
                details=budget_alert.get("details", {}),
                severity=budget_alert.get("level", "warning"),
                labels={"alert_type": "budget", "code": budget_alert.get("code", "")},
                metadata=budget_alert,
            )

            return self.dispatch(alert)

        except Exception as e:
            logger.error(f"分发预算告警失败: {e}")
            return {}

    def dispatch_financial_alert(self, financial_alert: Dict[str, Any]) -> Dict[AlertChannel, bool]:
        """分发金融监控告警（适配金融监控格式）"""
        try:
            # 金融监控告警格式适配
            severity_map = {
                "critical": AlertPriority.CRITICAL,
                "warning": AlertPriority.HIGH,
                "info": AlertPriority.LOW,
            }

            alert = AlertMessage(
                alert_id=financial_alert.get("alert_id", f"financial_{datetime.now().timestamp()}"),
                title=f"金融监控: {financial_alert.get('alert_type', 'unknown')}",
                message=financial_alert.get("message", ""),
                priority=severity_map.get(
                    financial_alert.get("severity", "warning"), AlertPriority.MEDIUM
                ),
                source="financial_monitor",
                details={
                    "triggered_by": financial_alert.get("triggered_by", {}),
                    "threshold": financial_alert.get("threshold", 0),
                    "actual_value": financial_alert.get("actual_value", 0),
                },
                severity=financial_alert.get("severity", "warning"),
                labels={"alert_type": "financial", "source": "financial_monitor"},
                metadata=financial_alert,
            )

            return self.dispatch(alert)

        except Exception as e:
            logger.error(f"分发金融告警失败: {e}")
            return {}

    def get_status(self) -> Dict[str, Any]:
        """获取分发器状态"""
        return {
            "config": self.config.to_dict(),
            "enabled_channels": len(self.handlers),
            "sent_alerts_count": len(self.sent_alerts),
            "dry_run": self.config.dry_run,
            "status": "active",
            "timestamp": datetime.now().isoformat(),
        }


# ==================== 全局实例 ====================

_alert_dispatcher_instance: Optional[AlertDispatcher] = None


def get_alert_dispatcher() -> AlertDispatcher:
    """获取全局告警分发器实例"""
    global _alert_dispatcher_instance
    if _alert_dispatcher_instance is None:
        _alert_dispatcher_instance = AlertDispatcher()
    return _alert_dispatcher_instance


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=== 告警分发接口测试 ===")

    # 创建分发器
    dispatcher = AlertDispatcher()

    print("\n1. 测试基本告警分发:")
    test_alert = AlertMessage(
        alert_id="test_alert_001",
        title="测试告警",
        message="这是一个测试告警消息",
        priority=AlertPriority.HIGH,
        source="test_suite",
        details={"test_key": "test_value"},
        labels={"environment": "test"},
    )

    results = dispatcher.dispatch(test_alert)
    print(f"   分发结果:")
    for channel, success in results.items():
        print(f"     {channel.value}: {'成功' if success else '失败'}")

    print("\n2. 测试字典格式告警:")
    dict_alert = {
        "alert_id": "test_dict_alert",
        "title": "字典格式测试",
        "message": "从字典创建的告警",
        "priority": "medium",
        "source": "test_dict",
        "details": {"count": 42},
    }

    results = dispatcher.dispatch_from_dict(dict_alert)
    print(f"   字典告警分发结果: {len(results)} 个渠道")

    print("\n3. 测试预算告警适配:")
    budget_alert = {
        "code": "BUDGET_CRITICAL",
        "level": "critical",
        "message": "预算严重不足",
        "details": {"remaining_budget": 5.0, "utilization": 0.95},
        "action": "需要立即处理",
    }

    results = dispatcher.dispatch_budget_alert(budget_alert)
    print(f"   预算告警分发结果: {sum(results.values())}/{len(results)} 成功")

    print("\n4. 测试金融监控告警适配:")
    financial_alert = {
        "alert_id": "financial_test_001",
        "alert_type": "BUDGET_REMAINING_LOW",
        "severity": "warning",
        "message": "剩余预算较低",
        "triggered_by": {"metric": "remaining_budget", "value": 25.0},
        "threshold": 50.0,
        "actual_value": 25.0,
    }

    results = dispatcher.dispatch_financial_alert(financial_alert)
    print(f"   金融告警分发结果: {sum(results.values())}/{len(results)} 成功")

    print("\n5. 测试状态查询:")
    status = dispatcher.get_status()
    print(f"   分发器状态:")
    print(f"     启用渠道: {status['enabled_channels']}")
    print(f"     已发送告警数: {status['sent_alerts_count']}")
    print(f"     dry_run 模式: {status['dry_run']}")

    print("\n=== 测试完成 ===")
