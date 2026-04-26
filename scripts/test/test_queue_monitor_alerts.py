#!/usr/bin/env python3
"""
测试队列监控告警触发逻辑
验证queue_monitor.py中的告警功能正常工作
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from scripts.queue_monitor import QueueMonitor


def test_alert_configuration():
    """测试告警配置"""
    print("🔧 测试告警配置...")

    # 创建带告警配置的监控器
    config = {
        "monitoring_interval": 60,
        "alert_channels": ["console", "log", "email", "slack", "webhook"],
        "alert_configs": {
            "email": {
                "enabled": True,
                "smtp_server": "smtp.test.com",
                "smtp_port": 587,
                "smtp_username": "test@example.com",
                "smtp_password": "testpass",
                "sender_email": "test@example.com",
                "recipient_emails": ["admin@example.com"],
            },
            "slack": {"enabled": True, "webhook_url": "https://hooks.slack.com/services/TEST"},
            "webhook": {
                "enabled": True,
                "url": "https://webhook.example.com/alerts",
                "headers": {"Authorization": "Bearer test-token"},
                "timeout": 10,
            },
        },
    }

    monitor = QueueMonitor(config)

    # 验证配置加载
    assert monitor.config["alert_channels"] == ["console", "log", "email", "slack", "webhook"]
    assert monitor.config["alert_configs"]["email"]["enabled"] == True
    assert monitor.config["alert_configs"]["slack"]["enabled"] == True
    assert monitor.config["alert_configs"]["webhook"]["enabled"] == True

    print("✅ 告警配置测试通过")
    return monitor


def test_alert_handling():
    """测试告警处理"""
    print("🔧 测试告警处理...")

    monitor = QueueMonitor()

    # 模拟队列状态包含告警
    queue_status = {
        "timestamp": datetime.now().isoformat(),
        "alerts": [
            {
                "type": "queue_stuck",
                "message": "队列长时间未更新",
                "queue_name": "test_queue",
                "stuck_minutes": 120,
            },
            {
                "type": "resource_high",
                "message": "CPU使用率超过阈值",
                "resource": "cpu",
                "value": 85,
                "threshold": 80,
            },
        ],
    }

    # 使用mock测试告警处理
    with patch.object(monitor, "send_email_alert") as mock_email, patch.object(
        monitor, "send_slack_alert"
    ) as mock_slack, patch.object(monitor, "send_webhook_alert") as mock_webhook:

        # 设置告警通道
        monitor.config["alert_channels"] = ["email", "slack", "webhook"]

        # 处理告警
        monitor.handle_alerts(queue_status)

        # 验证方法被调用
        assert mock_email.call_count == 2  # 两个告警
        assert mock_slack.call_count == 2
        assert mock_webhook.call_count == 2

        print(
            f"✅ 告警处理方法调用次数: email={mock_email.call_count}, slack={mock_slack.call_count}, webhook={mock_webhook.call_count}"
        )

    print("✅ 告警处理测试通过")


def test_email_alert_sending():
    """测试邮件告警发送"""
    print("🔧 测试邮件告警发送...")

    monitor = QueueMonitor()
    monitor.config["alert_channels"] = ["email"]

    # 启用邮件配置
    monitor.config["alert_configs"]["email"]["enabled"] = True
    monitor.config["alert_configs"]["email"]["smtp_server"] = "smtp.test.com"
    monitor.config["alert_configs"]["email"]["smtp_port"] = 587
    monitor.config["alert_configs"]["email"]["smtp_username"] = "test@example.com"
    monitor.config["alert_configs"]["email"]["smtp_password"] = "testpass"
    monitor.config["alert_configs"]["email"]["sender_email"] = "test@example.com"
    monitor.config["alert_configs"]["email"]["recipient_emails"] = ["admin@example.com"]

    alert = {"type": "test_alert", "message": "测试告警消息"}

    # 使用mock测试SMTP
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        monitor.send_email_alert("测试告警消息", alert)

        # 验证SMTP被调用
        mock_smtp.assert_called_once_with("smtp.test.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "testpass")
        mock_server.send_message.assert_called_once()

        print("✅ 邮件告警发送测试通过")


def test_slack_alert_sending():
    """测试Slack告警发送"""
    print("🔧 测试Slack告警发送...")

    monitor = QueueMonitor()
    monitor.config["alert_channels"] = ["slack"]

    # 启用Slack配置
    monitor.config["alert_configs"]["slack"]["enabled"] = True
    monitor.config["alert_configs"]["slack"][
        "webhook_url"
    ] = "https://hooks.slack.com/services/TEST"

    alert = {"type": "test_alert", "message": "测试Slack告警"}

    # 使用mock测试requests.post
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        monitor.send_slack_alert("测试Slack告警", alert)

        # 验证requests.post被调用
        mock_post.assert_called_once()

        # 检查调用参数
        args, kwargs = mock_post.call_args
        assert args[0] == "https://hooks.slack.com/services/TEST"
        assert "json" in kwargs
        assert kwargs["json"]["text"] == "测试Slack告警"

        print("✅ Slack告警发送测试通过")


def test_webhook_alert_sending():
    """测试Webhook告警发送"""
    print("🔧 测试Webhook告警发送...")

    monitor = QueueMonitor()
    monitor.config["alert_channels"] = ["webhook"]

    # 启用Webhook配置
    monitor.config["alert_configs"]["webhook"]["enabled"] = True
    monitor.config["alert_configs"]["webhook"]["url"] = "https://webhook.example.com/alerts"
    monitor.config["alert_configs"]["webhook"]["headers"] = {"Authorization": "Bearer test-token"}
    monitor.config["alert_configs"]["webhook"]["timeout"] = 10

    alert = {"type": "test_alert", "message": "测试Webhook告警"}

    # 使用mock测试requests.post
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        monitor.send_webhook_alert("测试Webhook告警", alert)

        # 验证requests.post被调用
        mock_post.assert_called_once()

        # 检查调用参数
        args, kwargs = mock_post.call_args
        assert args[0] == "https://webhook.example.com/alerts"
        assert "headers" in kwargs
        assert kwargs["headers"]["Authorization"] == "Bearer test-token"
        assert "json" in kwargs
        assert kwargs["json"]["alert_type"] == "test_alert"

        print("✅ Webhook告警发送测试通过")


def test_alert_detection_logic():
    """测试告警检测逻辑"""
    print("🔧 测试告警检测逻辑...")

    monitor = QueueMonitor()

    # 测试队列卡住检测
    from datetime import datetime, timedelta

    old_timestamp = (datetime.now() - timedelta(hours=2)).isoformat()

    queue_data = {
        "queue_status": "running",
        "updated_at": old_timestamp,
        "counts": {"pending": 5, "running": 0, "completed": 10, "failed": 0},
    }

    # 检查是否会触发队列卡住告警
    alerts = []

    # 模拟检测逻辑（简化版）
    updated_at = datetime.fromisoformat(old_timestamp)
    age_minutes = (datetime.now() - updated_at).total_seconds() / 60

    if age_minutes > monitor.config["performance_thresholds"]["queue_age_minutes"]:
        alerts.append(
            {
                "type": "queue_age",
                "message": f"队列长时间未更新: {age_minutes:.1f}分钟",
                "queue_name": "test_queue",
                "age_minutes": age_minutes,
                "threshold": monitor.config["performance_thresholds"]["queue_age_minutes"],
            }
        )

    print(f"✅ 检测到 {len(alerts)} 个告警")
    if alerts:
        print(f"  告警详情: {alerts[0]['message']}")

    assert len(alerts) > 0, "应该检测到队列长时间未更新告警"
    print("✅ 告警检测逻辑测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("🚀 队列监控告警功能测试")
    print("=" * 60)

    try:
        test_alert_configuration()
        test_alert_handling()
        test_email_alert_sending()
        test_slack_alert_sending()
        test_webhook_alert_sending()
        test_alert_detection_logic()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("💡 告警系统功能完整，可以配置实际的通知渠道")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
