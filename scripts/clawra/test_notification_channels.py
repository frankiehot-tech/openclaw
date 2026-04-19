#!/usr/bin/env python3
"""
深度测试通知渠道配置
测试企业微信、邮件等渠道的连通性和配置正确性
"""

import json
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))

from maref_notifier import MAREFNotifier


def test_wecom_webhook(config):
    """测试企业微信webhook"""
    print("=== 测试企业微信webhook ===")

    wecom_enabled = config.get("wecom_enabled", False)
    wecom_webhook = config.get("wecom_webhook", "")

    print(f"企业微信启用: {wecom_enabled}")
    print(f"Webhook地址: {wecom_webhook}")

    if not wecom_enabled or not wecom_webhook:
        print("❌ 企业微信未启用或webhook未配置")
        return False

    # 测试webhook连接
    try:
        print(f"测试连接: {wecom_webhook}")
        response = requests.get(wecom_webhook, timeout=5)
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容类型: {response.headers.get('Content-Type')}")

        if response.status_code == 200:
            print("✅ Webhook端点可达")
            return True
        else:
            print(f"❌ Webhook端点返回非200状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Webhook连接失败: {e}")
        return False


def test_email_smtp(config):
    """测试邮件SMTP配置"""
    print("\n=== 测试邮件SMTP配置 ===")

    email_enabled = config.get("email_enabled", False)
    smtp_server = config.get("email_smtp_server", "")
    smtp_port = config.get("email_smtp_port", 587)
    email_sender = config.get("email_sender", "")
    email_password = config.get("email_password", "")

    print(f"邮件启用: {email_enabled}")
    print(f"SMTP服务器: {smtp_server}:{smtp_port}")
    print(f"发件人: {email_sender}")
    print(f"密码配置: {'已配置' if email_password else '未配置'}")

    if not email_enabled or not smtp_server or not email_sender or not email_password:
        print("❌ 邮件配置不完整")
        return False

    # 测试SMTP连接
    try:
        print(f"测试SMTP连接到 {smtp_server}:{smtp_port}...")

        # 尝试TLS连接
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.ehlo()

        if smtp_port == 587:
            print("使用STARTTLS...")
            server.starttls()
            server.ehlo()
        elif smtp_port == 465:
            print("端口465，可能需要SSL连接...")
            # 对于端口465，需要使用SMTP_SSL
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)

        # 尝试登录
        print(f"尝试登录 {email_sender}...")
        server.login(email_sender, email_password)

        print("✅ SMTP连接和登录成功")
        server.quit()
        return True

    except Exception as e:
        print(f"❌ SMTP连接失败: {e}")

        # 提供特定错误建议
        if "qq.com" in email_sender:
            print("\nQQ邮箱配置建议:")
            print("1. 确认使用的是授权码而非邮箱密码")
            print("2. QQ邮箱SMTP设置:")
            print("   - 服务器: smtp.qq.com")
            print("   - 端口: 587 (STARTTLS) 或 465 (SSL)")
            print("   - 需要开启SMTP服务并获取授权码")
            print("3. 在QQ邮箱设置中开启POP3/SMTP服务")

        return False


def test_athena_integration(config):
    """测试Athena系统集成"""
    print("\n=== 测试Athena系统集成 ===")

    athena_enabled = config.get("athena_integration_enabled", True)
    athena_api = config.get("athena_notification_api", "")

    print(f"Athena集成启用: {athena_enabled}")
    print(f"Athena API地址: {athena_api}")

    if not athena_enabled or not athena_api:
        print("❌ Athena集成未启用或API地址未配置")
        return False

    # 测试API连接
    try:
        print(f"测试连接: {athena_api}")
        response = requests.get(athena_api, timeout=5)
        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            print("✅ Athena API端点可达")
            return True
        else:
            print(f"⚠️  Athena API返回非200状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Athena API连接失败: {e}")
        return False


def test_full_notification_flow():
    """测试完整通知流程"""
    print("\n=== 测试完整通知流程 ===")

    notifier = MAREFNotifier("config/notifier_config.json")

    # 创建测试预警
    test_alerts = [
        {
            "title": "测试红色预警",
            "description": "这是通知系统深度审计的测试预警",
            "recommendation": "请检查通知渠道配置",
            "duration_minutes": 5,
        }
    ]

    print("发送测试预警...")
    result = notifier.send_alert("red", test_alerts)

    print(f"\n发送结果:")
    print(f"  成功渠道: {result['sent']}")
    print(f"  失败渠道: {result['failed']}")
    print(f"  渠道详情:")
    for channel, status in result["channels"].items():
        print(f"    - {channel}: {status}")

    return result["sent"] > 0


def check_security_recommendations(config):
    """检查安全建议"""
    print("\n=== 安全建议检查 ===")

    recommendations = []

    # 检查密码强度
    email_password = config.get("email_password", "")
    if email_password:
        if len(email_password) < 8:
            recommendations.append("邮件密码过短，建议使用至少12位复杂密码")
        if email_password == "REDACTED_SMTP_PASSWORD":
            recommendations.append("检测到默认密码 'REDACTED_SMTP_PASSWORD'，请立即更改")

    # 检查webhook安全性
    wecom_webhook = config.get("wecom_webhook", "")
    if wecom_webhook and wecom_webhook.startswith("http://"):
        recommendations.append("企业微信webhook使用HTTP而非HTTPS，可能存在安全风险")

    # 检查API端点安全性
    athena_api = config.get("athena_notification_api", "")
    if athena_api and athena_api.startswith("http://"):
        recommendations.append("Athena API使用HTTP而非HTTPS，可能存在安全风险")

    if recommendations:
        print("⚠️  安全建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
    else:
        print("✅ 安全检查通过")

    return len(recommendations) == 0


def main():
    """主函数"""
    print("=== MAREF通知系统深度审计 ===\n")

    # 加载配置
    config_path = "config/notifier_config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        print(f"✅ 配置文件加载成功: {config_path}")
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return

    print(f"配置摘要:")
    for key, value in config.items():
        if "password" in key.lower():
            print(f"  {key}: {'*' * len(str(value)) if value else '未设置'}")
        else:
            print(f"  {key}: {value}")

    # 执行测试
    tests = [
        ("企业微信webhook", lambda: test_wecom_webhook(config)),
        ("邮件SMTP配置", lambda: test_email_smtp(config)),
        ("Athena系统集成", lambda: test_athena_integration(config)),
        ("完整通知流程", test_full_notification_flow),
        ("安全建议检查", lambda: check_security_recommendations(config)),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                print(f"✅ {test_name} 通过")
                passed += 1
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")

    # 总结
    print(f"\n{'='*60}")
    print(f"深度审计完成: {passed}/{total} 项测试通过")

    if passed == total:
        print("✅ 所有通知渠道配置正常")
    else:
        print("⚠️  部分通知渠道需要调整配置")
        print("\n建议:")
        print("1. 检查企业微信webhook服务是否正常运行")
        print("2. 验证QQ邮箱SMTP配置和授权码")
        print("3. 确保Athena系统API服务可用")
        print("4. 参考 docs/notification_system_config.md 进行配置")


if __name__ == "__main__":
    main()
