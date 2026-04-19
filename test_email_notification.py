#!/usr/bin/env python3
"""
邮件通知功能测试脚本
测试监控系统的邮件发送功能
"""

import os
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path

import yaml


def load_config():
    """加载监控配置"""
    config_path = Path(__file__).parent / "monitoring_config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None


def test_email_connection(config):
    """测试邮件连接"""
    email_config = config.get("email", {})

    if not email_config:
        print("❌ 邮件配置为空")
        return False

    required_fields = [
        "smtp_server",
        "smtp_port",
        "username",
        "password",
        "from_email",
        "to_emails",
    ]
    for field in required_fields:
        if not email_config.get(field):
            print(f"❌ 缺少必要字段: {field}")
            return False

    # 隐藏密码显示
    masked_password = "*" * len(email_config["password"]) if email_config["password"] else "未设置"

    print("📧 邮件配置信息:")
    print(f"  SMTP服务器: {email_config['smtp_server']}:{email_config['smtp_port']}")
    print(f"  发件人: {email_config['from_email']}")
    print(f"  收件人: {', '.join(email_config['to_emails'])}")
    print(f"  用户名: {email_config['username']}")
    print(f"  密码: {masked_password}")
    print(f"  使用TLS: {email_config.get('use_tls', True)}")

    # 检查是否是示例配置
    if "your-qq-email-authorization-code" in email_config.get(
        "password", ""
    ) or "your-app-specific-password" in email_config.get("password", ""):
        print("⚠️  警告: 检测到示例密码配置")
        print("   如需测试实际发送功能，请替换为实际授权码")
        return False

    return True


def send_test_email(config):
    """发送测试邮件"""
    email_config = config.get("email", {})

    # 创建邮件
    subject = "🔔 OpenClaw 监控测试邮件"
    body = f"""
<html>
<body>
<h2>OpenClaw 监控系统测试邮件</h2>
<p>这是一封测试邮件，用于验证监控系统的邮件通知功能。</p>
<ul>
<li><strong>发送时间:</strong> {formatdate(localtime=True)}</li>
<li><strong>SMTP服务器:</strong> {email_config['smtp_server']}:{email_config['smtp_port']}</li>
<li><strong>发送者:</strong> {email_config['from_email']}</li>
<li><strong>接收者:</strong> {', '.join(email_config['to_emails'])}</li>
</ul>
<p>如果收到此邮件，说明监控系统的邮件通知功能正常工作。</p>
<hr>
<p><em>此邮件由 OpenClaw 监控系统自动发送</em></p>
</body>
</html>
"""

    msg = MIMEMultipart()
    msg["From"] = email_config["from_email"]
    msg["To"] = ", ".join(email_config["to_emails"])
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = email_config.get("subject_prefix", "[OpenClaw Alert] ") + subject

    msg.attach(MIMEText(body, "html", "utf-8"))

    try:
        # 创建SSL上下文
        context = ssl.create_default_context()

        # 连接SMTP服务器
        print(f"🔗 连接到 {email_config['smtp_server']}:{email_config['smtp_port']}...")
        if email_config.get("use_tls", True):
            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
            server.starttls(context=context)
        else:
            server = smtplib.SMTP_SSL(
                email_config["smtp_server"], email_config["smtp_port"], context=context
            )

        # 登录
        print(f"🔐 登录到 {email_config['username']}...")
        server.login(email_config["username"], email_config["password"])

        # 发送邮件
        print(f"📤 发送邮件到 {email_config['to_emails']}...")
        server.sendmail(email_config["from_email"], email_config["to_emails"], msg.as_string())

        # 关闭连接
        server.quit()

        print("✅ 测试邮件发送成功！")
        print(f"  请检查收件箱 {email_config['to_emails'][0]} 是否收到测试邮件")
        return True

    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False


def main():
    """主函数"""
    print("📧 OpenClaw 邮件通知功能测试")
    print("=" * 60)

    # 加载配置
    config = load_config()
    if not config:
        print("❌ 无法加载配置文件")
        return False

    # 测试邮件连接
    if not test_email_connection(config):
        print("❌ 邮件配置验证失败")
        return False

    # 根据用户要求，跳过实际发送测试邮件（用户已确认能正常发送）
    print("\n" + "=" * 60)
    print("⏭️  跳过实际邮件发送测试")
    print("✅ 邮件配置验证通过")
    print("   密码已更新为实际授权码，配置验证通过")
    print("   根据用户说明，邮件功能已正常工作")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
