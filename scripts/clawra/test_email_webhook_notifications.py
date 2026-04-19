#!/usr/bin/env python3
"""
邮件和Webhook告警通知测试脚本
验证生产环境中的邮件和webhook告警渠道配置

此脚本执行以下测试：
1. 验证邮件和webhook配置格式
2. 模拟测试邮件发送逻辑
3. 模拟测试webhook发送逻辑
4. 提供实际配置指南

注意：此脚本不会实际发送邮件或调用真实webhook，
而是验证配置和提供测试方法。
"""

import json
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests


def load_production_config():
    """加载生产环境配置"""
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from config.production_config import ALERT_CONFIG

        return ALERT_CONFIG
    except ImportError as e:
        print(f"❌ 无法加载生产配置: {e}")
        return None


def validate_email_config(alert_config):
    """验证邮件配置"""
    print("\n=== 邮件通知配置验证 ===")

    notification_channels = alert_config.get("notification_channels", [])
    notification_settings = alert_config.get("notification_settings", {})

    if "email" not in notification_channels:
        print("❌ 邮件通知未在通知渠道中启用")
        print("  请在ALERT_CONFIG['notification_channels']中添加'email'")
        return False

    email_recipients = notification_settings.get("email_recipients", [])
    if not email_recipients:
        print("❌ 邮件收件人未配置")
        print("  请在ALERT_CONFIG['notification_settings']['email_recipients']中配置收件人列表")
        return False

    print(f"✅ 邮件通知已启用")
    print(f"✅ 邮件收件人: {', '.join(email_recipients)}")

    # 检查邮件服务器配置（需要在实际环境中配置）
    print("\n⚠️  邮件服务器配置检查:")
    print("  邮件服务器配置未在生产配置中指定")
    print("  需要在maref_notifier.py的配置文件中配置以下信息:")
    print("  - email_smtp_server: SMTP服务器地址")
    print("  - email_smtp_port: SMTP端口 (通常587或465)")
    print("  - email_sender: 发件人邮箱")
    print("  - email_password: 发件人邮箱密码或应用专用密码")

    return True


def validate_webhook_config(alert_config):
    """验证Webhook配置"""
    print("\n=== Webhook通知配置验证 ===")

    notification_channels = alert_config.get("notification_channels", [])
    notification_settings = alert_config.get("notification_settings", {})

    if "webhook" not in notification_channels:
        print("❌ Webhook通知未在通知渠道中启用")
        print("  请在ALERT_CONFIG['notification_channels']中添加'webhook'")
        return False

    webhook_url = notification_settings.get("webhook_url", "")
    if not webhook_url:
        print("❌ Webhook URL未配置")
        print("  请在ALERT_CONFIG['notification_settings']['webhook_url']中配置webhook URL")
        return False

    print(f"✅ Webhook通知已启用")
    print(f"✅ Webhook URL: {webhook_url}")

    # 检查URL格式
    if not webhook_url.startswith(("http://", "https://")):
        print("⚠️  Webhook URL应以http://或https://开头")

    return True


def test_email_simulation():
    """模拟邮件发送测试（不实际发送）"""
    print("\n=== 邮件发送模拟测试 ===")

    # 构建测试邮件
    test_subject = "MAREF告警通知测试邮件"
    test_body = f"""
    MAREF告警通知系统测试

    测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    这是一封测试邮件，用于验证MAREF系统的邮件通知功能。

    如果您收到此邮件，说明:
    1. 邮件服务器配置正确
    2. SMTP认证通过
    3. 发件人权限正常
    4. 收件人地址有效

    邮件内容:
    - 主题: {test_subject}
    - 发送时间: {datetime.now().isoformat()}

    实际告警邮件将包含:
    - 告警类型（红色/黄色）
    - 告警详情
    - 受影响系统
    - 建议操作
    - 相关指标

    此邮件由MAREF监控系统自动生成。
    """

    print("✅ 测试邮件内容构建完成")
    print(f"主题: {test_subject}")
    print(f"正文长度: {len(test_body)} 字符")

    # 显示邮件发送步骤
    print("\n📋 实际邮件发送步骤:")
    print("1. 配置SMTP服务器信息到maref_notifier.py的配置文件中")
    print("2. 确保发件人邮箱已启用SMTP服务")
    print("3. 使用应用专用密码而非邮箱登录密码")
    print("4. 测试发送:")
    print(
        "   python3 -c \"from maref_notifier import MAREFNotifier; n=MAREFNotifier(); n.send_email_notification('测试', '测试内容')\""
    )

    return True


def test_webhook_simulation(alert_config):
    """模拟Webhook发送测试（不实际调用）"""
    print("\n=== Webhook发送模拟测试 ===")

    # 构建测试webhook payload
    test_payload = {
        "system": "maref",
        "alert_type": "test",
        "timestamp": datetime.now().isoformat(),
        "test": True,
        "message": "MAREF告警通知系统测试",
        "details": {
            "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "purpose": "验证webhook通知功能",
            "expected_format": "JSON payload",
        },
        "alerts": [
            {
                "id": "TEST_ALERT_001",
                "title": "测试告警",
                "description": "这是一条测试告警，用于验证webhook通知功能",
                "priority": "info",
                "timestamp": datetime.now().isoformat(),
            }
        ],
    }

    print("✅ 测试Webhook payload构建完成")
    print(f"Payload格式: JSON")
    print(f"Payload大小: {len(json.dumps(test_payload))} 字节")

    # 显示webhook测试步骤
    print("\n📋 实际Webhook测试步骤:")
    print("1. 使用curl命令测试webhook端点:")
    print(f"   curl -X POST -H 'Content-Type: application/json' \\")
    print(f"        -d '{json.dumps(test_payload, indent=2)}' \\")
    webhook_url = alert_config.get("notification_settings", {}).get(
        "webhook_url", "YOUR_WEBHOOK_URL"
    )
    print(f"        {webhook_url}")
    print("\n2. 检查响应状态码应为200或201")
    print("3. 查看接收端是否收到测试消息")

    return True


def create_config_template():
    """创建邮件和webhook配置模板"""
    print("\n=== 配置模板 ===")

    config_template = {
        "wecom_enabled": False,
        "wecom_webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY",
        "email_enabled": True,
        "email_smtp_server": "smtp.gmail.com",
        "email_smtp_port": 587,
        "email_sender": "your-email@gmail.com",
        "email_receivers": ["devops@example.com", "oncall@example.com"],
        "email_password": "YOUR_APP_PASSWORD",  # 使用应用专用密码，不是邮箱密码
        "slack_enabled": False,
        "slack_webhook": "https://hooks.slack.com/services/YOUR/WEBHOOK/PATH",
        "file_log_enabled": True,
        "file_log_path": "/var/log/maref_notifications.log",
        "console_log_enabled": True,
        "athena_integration_enabled": True,
        "athena_notification_api": "http://localhost:8000/api/notifications",
    }

    print("邮件和Webhook配置模板（maref_notifier.py格式）:")
    print(json.dumps(config_template, indent=2, ensure_ascii=False))

    # 保存模板到文件
    template_file = "config/notification_config_template.json"
    Path(template_file).parent.mkdir(parents=True, exist_ok=True)

    with open(template_file, "w", encoding="utf-8") as f:
        json.dump(config_template, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 配置模板已保存到: {template_file}")
    print("使用说明:")
    print(f"1. 复制此模板到实际配置文件")
    print(f"2. 根据实际环境填写配置值")
    print(f"3. 在maref_notifier.py中指定配置文件路径")

    return template_file


def run_actual_notification_test():
    """运行实际通知测试（需要用户手动确认）"""
    print("\n=== 实际通知测试指南 ===")

    print("要实际测试邮件和webhook通知，请按以下步骤操作:\n")

    print("1. 📧 邮件通知测试:")
    print("   a. 创建测试配置文件 config/test_notification_config.json")
    print("   b. 填入实际的SMTP服务器信息和邮箱凭据")
    print("   c. 运行测试:")
    print('      python3 -c """')
    print("      import sys")
    print("      sys.path.insert(0, '.')")
    print("      from maref_notifier import MAREFNotifier")
    print("      notifier = MAREFNotifier('config/test_notification_config.json')")
    print(
        "      test_alerts = [{'title': '测试告警', 'description': '测试邮件功能', 'recommendation': '无需操作'}]"
    )
    print("      result = notifier.send_alert('red', test_alerts)")
    print("      print(f'邮件发送结果: {result}')")
    print('      """\n')

    print("2. 🔗 Webhook通知测试:")
    print("   a. 配置webhook URL到测试配置文件中")
    print("   b. 使用curl测试webhook端点:")
    print("      curl -X POST https://your-webhook-url \\")
    print("           -H 'Content-Type: application/json' \\")
    print('           -d \'{"test": true, "message": "MAREF测试"}\'')
    print("   c. 验证接收端是否收到消息\n")

    print("3. 🧪 集成测试:")
    print("   运行完整的告警集成测试:")
    print("   python3 test_alert_integration.py\n")

    print("⚠️  安全提示:")
    print("   - 不要在版本控制中提交包含凭据的配置文件")
    print("   - 使用环境变量或密钥管理服务存储敏感信息")
    print("   - 测试完成后及时删除测试凭据")

    return True


def main():
    """主函数"""
    print("=" * 60)
    print("MAREF邮件和Webhook告警通知测试")
    print("=" * 60)

    # 加载配置
    alert_config = load_production_config()
    if not alert_config:
        return 1

    print("✅ 生产配置加载成功")

    all_tests_passed = True

    # 验证配置
    if not validate_email_config(alert_config):
        all_tests_passed = False

    if not validate_webhook_config(alert_config):
        all_tests_passed = False

    # 模拟测试
    test_email_simulation()
    test_webhook_simulation(alert_config)

    # 创建配置模板
    template_file = create_config_template()

    # 提供实际测试指南
    run_actual_notification_test()

    # 总结
    print("\n" + "=" * 60)
    print("测试完成总结")
    print("=" * 60)

    if all_tests_passed:
        print("✅ 配置验证通过")
        print("   邮件和webhook配置格式正确")
    else:
        print("⚠️  配置验证未完全通过")
        print("   请根据上述提示修复配置")

    print("\n下一步行动:")
    print("1. 根据模板配置实际邮件和webhook凭据")
    print("2. 运行实际通知测试（参见上述指南）")
    print("3. 验证告警集成: python3 test_alert_integration.py")
    print("4. 配置cron任务: ./setup_weekly_monitor_cron.sh")

    return 0 if all_tests_passed else 1


if __name__ == "__main__":
    sys.exit(main())
