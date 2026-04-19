#!/usr/bin/env python3
"""
测试通知器配置
"""

import os
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from maref_notifier import MAREFNotifier

    print("✅ 成功导入MAREFNotifier")
except ImportError as e:
    print(f"❌ 导入MAREFNotifier失败: {e}")
    sys.exit(1)


def test_notifier_initialization():
    """测试通知器初始化"""
    print("\n=== 测试通知器初始化 ===")

    # 测试默认配置
    print("1. 使用默认配置:")
    notifier_default = MAREFNotifier()
    status_default = notifier_default.get_notification_status()
    print(f"   渠道状态: {status_default['channel_status']}")
    print(f"   邮件是否启用: {status_default['config_summary']['email_enabled']}")

    # 测试自定义配置文件
    print("\n2. 使用配置文件:")
    config_path = "config/notifier_config.json"
    if Path(config_path).exists():
        notifier_custom = MAREFNotifier(config_path)
        status_custom = notifier_custom.get_notification_status()
        print(f"   渠道状态: {status_custom['channel_status']}")
        print(f"   邮件是否启用: {status_custom['config_summary']['email_enabled']}")
        print(f"   邮件SMTP服务器: {notifier_custom.config.get('email_smtp_server')}")
    else:
        print(f"   ⚠️  配置文件 {config_path} 不存在")

    return notifier_default


def test_notification_sending(notifier):
    """测试通知发送"""
    print("\n=== 测试通知发送 ===")

    test_alerts = [
        {
            "title": "测试红色预警",
            "description": "这是一个测试红色预警",
            "recommendation": "请检查系统状态",
            "duration": 300,
            "priority": "critical",
            "metrics_snapshot": {"test_metric": 95.5},
        },
        {
            "title": "测试黄色预警",
            "description": "这是一个测试黄色预警",
            "recommendation": "请关注系统性能",
            "duration": 1200,
            "priority": "medium",
            "metrics_snapshot": {"test_metric": 75.3},
        },
    ]

    print("发送测试红色预警...")
    results = notifier.send_alert("red", test_alerts, "/tmp/test_report.md")

    print(f"发送结果:")
    print(f"  成功渠道: {results['sent']}")
    print(f"  失败渠道: {results['failed']}")
    print(f"  渠道详情: {results['channels']}")

    return results


def test_notification_history(notifier):
    """测试通知历史记录"""
    print("\n=== 测试通知历史 ===")

    status = notifier.get_notification_status()
    print(f"总通知数: {status['total_notifications']}")

    if status["recent_notifications"]:
        print("最近通知:")
        for notification in status["recent_notifications"]:
            print(f"  时间: {notification['timestamp']}")
            print(f"  类型: {notification['alert_type']}")
            print(f"  数量: {notification['alert_count']}")
            print(f"  渠道: {notification['channels_used']}")
    else:
        print("暂无通知历史")


def main():
    print("=== MAREF通知器配置测试 ===")

    # 测试初始化
    notifier = test_notifier_initialization()

    # 测试通知发送
    results = test_notification_sending(notifier)

    # 测试历史记录
    test_notification_history(notifier)

    print("\n=== 测试总结 ===")
    if results["sent"] > 0:
        print(f"✅ 通知发送测试成功，{results['sent']}个渠道发送成功")
    else:
        print(f"⚠️  通知发送测试警告，无渠道发送成功")
        print("   注意: 当前可能只启用了文件和console渠道，外部渠道需要配置凭据")

    # 提供配置建议
    print("\n=== 配置建议 ===")
    print("1. 编辑 config/notifier_config.json 配置邮件:")
    print("   - 设置 email_enabled: true")
    print("   - 配置 email_sender: 你的邮箱")
    print("   - 配置 email_receivers: 接收邮箱列表")
    print("   - 配置 email_password: 邮箱应用密码")
    print("\n2. 或配置企业微信:")
    print("   - 设置 wecom_enabled: true")
    print("   - 配置 wecom_webhook: 企业微信机器人webhook")
    print("\n3. 或配置Slack:")
    print("   - 设置 slack_enabled: true")
    print("   - 配置 slack_webhook: Slack webhook URL")


if __name__ == "__main__":
    main()
