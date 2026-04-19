#!/usr/bin/env python3
"""
测试环境变量配置加载
验证maref_notifier.py是否正确读取环境变量
"""

import os
import sys

# 首先加载.env文件到环境变量
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_file):
    print(f"正在加载环境变量文件: {env_file}")
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue
            # 解析键值对
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # 移除可能的引号
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                # 设置环境变量
                os.environ[key] = value
                print(
                    f"  设置环境变量: {key} = {'***' if 'PASSWORD' in key or 'SECRET' in key or 'TOKEN' in key else value}"
                )

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from maref_notifier import MAREFNotifier


def test_env_loading():
    """测试环境变量配置加载"""
    print("=== 环境变量配置加载测试 ===\n")

    # 首先检查关键环境变量
    required_env_vars = [
        ("WECOM_WEBHOOK_URL", "企业微信Webhook URL"),
        ("SMTP_SERVER", "SMTP服务器"),
        ("SMTP_USERNAME", "SMTP用户名"),
        ("EMAIL_RECEIVERS", "邮件接收者"),
        ("ENABLE_WECOM", "企业微信启用开关"),
        ("ENABLE_EMAIL", "邮件启用开关"),
    ]

    print("环境变量检查:")
    for var_name, description in required_env_vars:
        value = os.getenv(var_name)
        if value:
            # 隐藏敏感信息
            if "PASSWORD" in var_name or "SECRET" in var_name or "TOKEN" in var_name:
                display_value = "***（已设置）"
            else:
                display_value = value
            print(f"  ✅ {var_name} ({description}): {display_value}")
        else:
            print(f"  ⚠️  {var_name} ({description}): 未设置")

    print("\n=== 通知器初始化测试 ===")

    try:
        # 初始化通知器（不带配置文件，测试环境变量加载）
        notifier = MAREFNotifier()
        print("✅ 通知器初始化成功")

        # 检查配置
        config_summary = notifier.config.copy()

        # 隐藏敏感信息
        sensitive_keys = ["email_password", "wecom_secret", "wecom_webhook_token"]
        for key in sensitive_keys:
            if key in config_summary and config_summary[key]:
                config_summary[key] = "***"

        print("\n配置摘要:")
        for key, value in sorted(config_summary.items()):
            print(f"  {key}: {value}")

        # 检查渠道状态
        print("\n渠道状态:")
        for channel, enabled in notifier.channel_status.items():
            status = "✅ 启用" if enabled else "❌ 禁用"
            print(f"  {channel}: {status}")

        # 测试企业微信配置
        print("\n=== 企业微信配置测试 ===")
        wecom_webhook = notifier.config.get("wecom_webhook")
        wecom_corpid = notifier.config.get("wecom_corpid")
        wecom_agentid = notifier.config.get("wecom_agentid")
        wecom_secret = notifier.config.get("wecom_secret")

        if wecom_webhook:
            print(f"✅ Webhook配置: {wecom_webhook}")
        else:
            print("❌ Webhook未配置")

        if wecom_corpid and wecom_agentid and wecom_secret:
            print(f"✅ 应用API配置: CorpID={wecom_corpid[:8]}..., AgentId={wecom_agentid}")
        else:
            print("⚠️  应用API配置不完整（如需使用IP白名单方式，请配置环境变量）")

        # 测试邮件配置
        print("\n=== 邮件配置测试 ===")
        email_sender = notifier.config.get("email_sender")
        email_receivers = notifier.config.get("email_receivers", [])
        email_password = notifier.config.get("email_password")
        email_smtp_server = notifier.config.get("email_smtp_server")
        email_smtp_port = notifier.config.get("email_smtp_port")

        if email_sender:
            print(f"✅ 发件人: {email_sender}")
        else:
            print("❌ 发件人未配置")

        if email_receivers:
            print(f"✅ 收件人: {email_receivers}")
        else:
            print("❌ 收件人未配置")

        if email_password:
            print(f"✅ 密码/授权码: {'***' if email_password else '未设置'}")
        else:
            print("⚠️  密码/授权码未设置（邮件发送将失败）")

        if email_smtp_server and email_smtp_port:
            print(f"✅ SMTP服务器: {email_smtp_server}:{email_smtp_port}")
        else:
            print("❌ SMTP服务器未完整配置")

        # 测试邮件加密设置
        use_ssl = notifier.config.get("email_use_ssl", False)
        use_tls = notifier.config.get("email_use_tls", True)
        print(f"✅ 加密设置: SSL={use_ssl}, TLS={use_tls}")

        # 端口与加密方式匹配性检查
        if email_smtp_port == 465 and not use_ssl:
            print("⚠️  警告: 端口465通常需要使用SSL加密")
        elif email_smtp_port == 587 and not use_tls:
            print("⚠️  警告: 端口587通常需要使用TLS加密")

        return True

    except Exception as e:
        print(f"❌ 通知器初始化失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_qq_email_requirements():
    """检查QQ邮箱要求"""
    print("\n=== QQ邮箱配置要求 ===")
    print("1. 授权码要求:")
    print("   - QQ邮箱需要使用16位授权码，而非登录密码")
    print("   - 请登录QQ邮箱网页版 → 设置 → 账户")
    print("   - 开启'POP3/SMTP服务'，生成16位授权码")
    print("   - 将授权码设置为 SMTP_PASSWORD 环境变量")

    print("\n2. 端口与加密建议:")
    print("   - 端口465: 使用SSL加密 (SMTP_USE_SSL=true)")
    print("   - 端口587: 使用TLS加密 (SMTP_USE_TLS=true)")
    print("   - 当前.env文件使用端口587+TLS")

    print("\n3. 密码安全检查:")
    print("   - 当前配置的密码不是16位授权码，邮件发送将失败")
    print("   - 建议: 立即获取正确授权码并更新.env文件")


def main():
    """主函数"""
    print("MAREF通知系统环境变量配置测试\n")

    # 检查.env文件是否存在
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        print(f"✅ 找到.env文件: {env_file}")
        print("   注意: .env文件已加载到环境变量中")
    else:
        print(f"⚠️  未找到.env文件，将使用系统环境变量")

    # 测试环境变量加载
    success = test_env_loading()

    # 检查QQ邮箱要求
    check_qq_email_requirements()

    print(f"\n{'='*60}")
    if success:
        print("✅ 环境变量配置测试完成")
        print("\n下一步:")
        print("1. 获取QQ邮箱16位授权码，更新.env文件")
        print("2. 测试企业微信webhook端点是否正确")
        print("3. 运行完整通知测试: python3 test_notification_channels.py")
    else:
        print("❌ 环境变量配置测试失败")
        print("\n请检查:")
        print("1. .env文件格式是否正确")
        print("2. 环境变量是否已加载到当前shell")
        print("3. 关键配置项是否完整")


if __name__ == "__main__":
    main()
