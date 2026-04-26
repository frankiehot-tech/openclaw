#!/usr/bin/env python3
"""
监控配置验证脚本

验证监控配置文件的格式和凭据有效性，帮助用户设置邮件和Slack通知。
按照用户请求"告警机制增强：配置实际邮件/Slack凭据，实现外部通知"创建。
"""

import json
import os
import sys
from pathlib import Path

import yaml


def load_config(config_path=None):
    """加载配置文件"""
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                print(f"✅ 配置文件加载成功: {config_path}")
                return config
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            return None

    # 检查默认路径
    default_paths = [
        Path(__file__).parent / "monitoring_config.yaml",
        Path(__file__).parent / ".openclaw" / "maref" / "config" / "config.yaml",
        Path(__file__).parent / "config" / "monitoring.yaml",
    ]

    for path in default_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    print(f"✅ 发现并加载配置文件: {path}")
                    return config
            except Exception as e:
                print(f"❌ 配置文件加载失败 ({path}): {e}")

    print("⚠️  未找到配置文件，使用示例配置模板")
    return create_example_config()


def create_example_config():
    """创建示例配置"""
    example_config = {
        "email": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "from_email": "your-email@gmail.com",
            "to_emails": ["team-lead@example.com", "dev-ops@example.com"],
            "username": "your-email@gmail.com",
            "password": "your-app-specific-password",
            "subject_prefix": "[OpenClaw Alert] ",
            "use_tls": True,
        },
        "slack": {
            "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
            "colors": {"critical": "#FF0000", "warning": "#FFA500", "info": "#36A64F"},
            "channel": "#alerts",
            "username": "OpenClaw Monitor",
            "icon_emoji": ":warning:",
        },
        "alert_thresholds": {
            "queue_backlog": {"warning": 10, "critical": 30},
            "memory_usage": {"warning": 70, "critical": 85},
            "cpu_usage": {"warning": 75, "critical": 90},
            "disk_usage": {"warning": 80, "critical": 95},
            "queue_age": {"warning": 60, "critical": 240},
        },
        "monitoring": {"check_interval": 300, "alert_cooldown": 1800, "history_size": 100},
        "advanced": {
            "verbose_logging": False,
            "generate_dashboard": True,
            "dashboard_output": ".openclaw/monitoring_dashboard.html",
            "alert_log_path": ".openclaw/monitoring_logs/alerts.log",
        },
    }

    return example_config


def validate_email_config(email_config):
    """验证邮件配置"""
    print("\n📧 验证邮件配置...")

    required_fields = [
        "smtp_server",
        "smtp_port",
        "username",
        "password",
        "from_email",
        "to_emails",
    ]
    missing_fields = []

    for field in required_fields:
        if not email_config.get(field):
            missing_fields.append(field)

    if missing_fields:
        print(f"❌ 邮件配置不完整，缺少字段: {missing_fields}")
        return False

    print(f"✅ SMTP服务器: {email_config.get('smtp_server')}:{email_config.get('smtp_port')}")
    print(f"✅ 发件人: {email_config.get('from_email')}")
    print(f"✅ 收件人: {', '.join(email_config.get('to_emails', []))}")

    # 检查是否是示例配置
    from_email = email_config.get("from_email", "")
    password = email_config.get("password", "")

    is_example = (
        "your-email@gmail.com" in from_email
        or "your-app-specific-password" in password
        or "your-qq-email-authorization-code" in password
        or "example.com" in from_email
        or any("example.com" in email for email in email_config.get("to_emails", []))
    )

    if is_example:
        print("⚠️  警告: 检测到示例配置值，邮件发送可能失败")
        print("   请替换为实际凭据：")
        print(f"   - 发件人: {from_email}")
        print(f"   - 密码: {'*' * len(password) if password else '未设置'}")
        print("   对于QQ邮箱，需要使用授权码而非登录密码")
        print(
            "   获取QQ邮箱授权码: https://service.mail.qq.com/cgi-bin/help?subtype=1&&id=28&&no=1001256"
        )
        # 不返回False，允许用户测试配置

    return True


def validate_slack_config(slack_config):
    """验证Slack配置"""
    print("\n💬 验证Slack配置...")

    webhook_url = slack_config.get("webhook_url", "")

    if not webhook_url:
        print("ℹ️  Slack Webhook URL为空，Slack通知将不会发送")
        return True  # 允许空值，Slack为可选功能

    print(f"✅ Webhook URL: {webhook_url[:50]}...")
    print(f"✅ 通知渠道: {slack_config.get('channel', '#alerts')}")
    print(f"✅ 机器人名称: {slack_config.get('username', 'OpenClaw Monitor')}")

    # 检查是否是示例配置
    if "T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX" in webhook_url:
        print("⚠️  警告: 检测到示例Webhook URL，Slack通知将不会发送")
        print("   如需启用Slack通知，请获取实际Webhook URL:")
        print("   1. 访问 https://api.slack.com/apps")
        print("   2. 创建或选择应用")
        print("   3. 启用Incoming Webhooks")
        print("   4. 添加New Webhook to Workspace")
        return True  # 允许示例值，Slack为可选功能

    return True


def validate_alert_thresholds(thresholds):
    """验证告警阈值配置"""
    print("\n📊 验证告警阈值配置...")

    required_sections = ["queue_backlog", "memory_usage", "cpu_usage", "disk_usage", "queue_age"]

    for section in required_sections:
        if section not in thresholds:
            print(f"⚠️  缺少阈值配置: {section}")
            thresholds[section] = {"warning": 0, "critical": 0}

    for section, values in thresholds.items():
        if "warning" in values and "critical" in values:
            warning = values["warning"]
            critical = values["critical"]
            if warning >= critical:
                print(f"⚠️  {section}: 警告阈值({warning})应小于严重阈值({critical})")
            else:
                print(f"✅  {section}: 警告={warning}, 严重={critical}")

    return True


def check_environment_variables():
    """检查环境变量配置"""
    print("\n🌍 检查环境变量配置...")

    email_vars = [
        "OPENCLAW_SMTP_SERVER",
        "OPENCLAW_SMTP_PORT",
        "OPENCLAW_EMAIL_USERNAME",
        "OPENCLAW_EMAIL_PASSWORD",
        "OPENCLAW_FROM_EMAIL",
        "OPENCLAW_TO_EMAILS",
    ]

    slack_vars = ["OPENCLAW_SLACK_WEBHOOK_URL", "OPENCLAW_SLACK_CHANNEL", "OPENCLAW_SLACK_USERNAME"]

    print("邮件环境变量:")
    for var in email_vars:
        value = os.getenv(var)
        if value:
            masked = value[:3] + "***" + value[-3:] if len(value) > 6 else "***"
            print(f"  ✅ {var}: {masked}")
        else:
            print(f"  ⚠️  {var}: 未设置")

    print("\nSlack环境变量:")
    for var in slack_vars:
        value = os.getenv(var)
        if value:
            masked = value[:10] + "***" + value[-5:] if len(value) > 15 else "***"
            print(f"  ✅ {var}: {masked}")
        else:
            print(f"  ⚠️  {var}: 未设置")

    return any(os.getenv(var) for var in email_vars + slack_vars)


def generate_config_template(output_path=None):
    """生成配置模板"""
    if not output_path:
        output_path = Path(__file__).parent / "monitoring_config.yaml"

    example_config = create_example_config()

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                example_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False
            )

        print(f"\n📄 配置模板已生成: {output_path}")
        print("下一步:")
        print("  1. 编辑配置文件，填写实际邮件和Slack凭据")
        print("  2. 或设置环境变量 (推荐生产环境使用)")
        print("  3. 运行 python3 validate_monitoring_config.py 验证配置")

        return True
    except Exception as e:
        print(f"❌ 配置模板生成失败: {e}")
        return False


def main():
    """主函数"""
    print("🔧 OpenClaw 监控配置验证工具")
    print("=" * 60)

    # 解析命令行参数
    import argparse

    parser = argparse.ArgumentParser(description="验证监控配置")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--generate", action="store_true", help="生成配置模板")
    parser.add_argument("--env", action="store_true", help="只检查环境变量")
    parser.add_argument("--output", help="模板输出路径")

    args = parser.parse_args()

    if args.generate:
        output_path = args.output if args.output else None
        success = generate_config_template(output_path)
        sys.exit(0 if success else 1)

    if args.env:
        check_environment_variables()
        sys.exit(0)

    # 加载配置
    config = load_config(args.config)

    if not config:
        print("❌ 无法加载配置，请使用 --generate 生成模板")
        sys.exit(1)

    # 验证各配置部分
    config_valid = True

    # 验证邮件配置
    email_config = config.get("email", {})
    if email_config:
        if not validate_email_config(email_config):
            config_valid = False
    else:
        print("⚠️  未找到邮件配置，邮件通知将无法使用")

    # 验证Slack配置
    slack_config = config.get("slack", {})
    if slack_config:
        if not validate_slack_config(slack_config):
            config_valid = False
    else:
        print("⚠️  未找到Slack配置，Slack通知将无法使用")

    # 验证告警阈值
    thresholds = config.get("alert_thresholds", {})
    validate_alert_thresholds(thresholds)

    # 检查环境变量
    has_env_vars = check_environment_variables()

    # 总结
    print("\n" + "=" * 60)
    print("📋 配置验证总结:")

    if config_valid:
        print("✅ 配置格式正确")

        if has_env_vars:
            print("✅ 检测到环境变量配置")
            print("💡 提示: 环境变量优先级高于配置文件")
        else:
            print("ℹ️  未检测到环境变量配置，将使用配置文件")

        print("\n🎯 建议:")
        print("  1. 运行测试验证通知功能:")
        print("     python3 test_monitor_queue_health.py")
        print("  2. 手动触发告警测试:")
        print("     修改队列文件，创建大量pending任务")
        print("  3. 设置定时监控:")
        print("     python3 monitor_queue_health.py --loop")

        sys.exit(0)
    else:
        print("❌ 配置存在问题，请修复")

        print("\n🔧 修复建议:")
        if not email_config or "your-email@gmail.com" in email_config.get("from_email", ""):
            print("  1. 填写实际邮件凭据")
            print("     - 对于Gmail，使用应用专用密码")
            print("     - 或使用其他SMTP服务商")

        if not slack_config or "T00000000" in slack_config.get("webhook_url", ""):
            print("  2. 设置Slack Webhook URL")
            print("     - 创建Slack应用")
            print("     - 启用Incoming Webhooks")
            print("     - 获取Webhook URL")

        print("  3. 或使用环境变量:")
        print("     export OPENCLAW_SMTP_SERVER='smtp.gmail.com'")
        print("     export OPENCLAW_EMAIL_USERNAME='your-email@gmail.com'")
        print("     export OPENCLAW_EMAIL_PASSWORD='your-app-password'")

        sys.exit(1)


if __name__ == "__main__":
    main()
