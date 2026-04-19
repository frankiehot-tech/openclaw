#!/usr/bin/env python3
"""
测试QQ邮箱SMTP配置
探索正确的配置参数
"""

import smtplib
import ssl
from email.mime.text import MIMEText


def test_smtp_connection(server, port, username, password, use_ssl=False, use_tls=True):
    """测试SMTP连接"""
    print(f"测试 {server}:{port} (SSL: {use_ssl}, TLS: {use_tls})...")

    try:
        if use_ssl:
            # SSL连接
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, port, context=context, timeout=10) as server:
                print(f"  SSL连接建立")
                server.login(username, password)
                print(f"  ✅ 登录成功")
                return True
        else:
            # 普通连接，可能使用TLS
            with smtplib.SMTP(server, port, timeout=10) as server:
                print(f"  连接建立")
                server.ehlo()

                if use_tls:
                    print(f"  启用STARTTLS...")
                    server.starttls()
                    server.ehlo()

                print(f"  尝试登录 {username}...")
                server.login(username, password)
                print(f"  ✅ 登录成功")
                return True

    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return False


def test_qq_email_variations():
    """测试QQ邮箱的不同配置组合"""
    username = "athenabot@qq.com"
    password = "REDACTED_SMTP_PASSWORD"  # 可能是授权码

    print("=== QQ邮箱SMTP配置测试 ===\n")

    # QQ邮箱SMTP服务器配置
    test_cases = [
        # (服务器, 端口, SSL, TLS, 描述)
        ("smtp.qq.com", 465, True, False, "标准SSL端口"),
        ("smtp.qq.com", 587, False, True, "标准TLS端口"),
        ("smtp.qq.com", 25, False, True, "传统端口（可能被阻塞）"),
        ("smtp.exmail.qq.com", 465, True, False, "企业邮箱SSL"),
        ("smtp.exmail.qq.com", 587, False, True, "企业邮箱TLS"),
    ]

    successful_tests = []

    for server, port, use_ssl, use_tls, description in test_cases:
        print(f"\n测试: {description}")
        print(f"  服务器: {server}:{port}")

        if test_smtp_connection(server, port, username, password, use_ssl, use_tls):
            successful_tests.append((server, port, use_ssl, use_tls, description))

    # 总结
    print(f"\n{'='*60}")
    print(f"测试完成: {len(successful_tests)}/{len(test_cases)} 配置成功")

    if successful_tests:
        print("\n✅ 可用的配置:")
        for server, port, use_ssl, use_tls, description in successful_tests:
            ssl_mode = "SSL" if use_ssl else "TLS" if use_tls else "无加密"
            print(f"  - {description}: {server}:{port} ({ssl_mode})")

        # 推荐最佳配置
        best = successful_tests[0]
        print(f"\n推荐配置:")
        print(f"  服务器: {best[0]}")
        print(f"  端口: {best[1]}")
        print(f"  SSL: {best[2]}")
        print(f"  TLS: {best[3]}")

        return best
    else:
        print("\n❌ 所有配置测试失败")
        print("\n可能的问题:")
        print("1. 密码错误 - QQ邮箱需要使用授权码而非登录密码")
        print("2. SMTP服务未开启 - 需要在QQ邮箱设置中开启")
        print("3. 网络限制 - 可能被防火墙或ISP阻止")
        print("4. 账号限制 - 可能触发了安全机制")

        return None


def check_qq_email_requirements():
    """检查QQ邮箱要求"""
    print("\n=== QQ邮箱SMTP要求 ===")
    print("1. 启用SMTP服务:")
    print("   - 登录QQ邮箱 → 设置 → 账户")
    print("   - 找到'POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务'")
    print("   - 开启'POP3/SMTP服务'")

    print("\n2. 获取授权码:")
    print("   - 在开启SMTP服务时，会提示生成授权码")
    print("   - 授权码是16位字符串，用于代替密码")
    print("   - 每个授权码对应一个应用，可单独管理")

    print("\n3. 安全注意事项:")
    print("   - 授权码不要泄露，定期更换")
    print("   - 建议使用专用邮箱账户发送通知")
    print("   - 监控发送频率，避免被标记为垃圾邮件")


def test_email_sending(best_config):
    """测试实际邮件发送"""
    if not best_config:
        print("❌ 无可用配置，跳过发送测试")
        return False

    server, port, use_ssl, use_tls, description = best_config
    username = "athenabot@qq.com"
    password = "REDACTED_SMTP_PASSWORD"
    receiver = "athenabot@qq.com"  # 发送给自己测试

    print(f"\n=== 测试邮件发送 ({description}) ===")

    try:
        # 创建邮件
        msg = MIMEText("这是来自MAREF通知系统的测试邮件")
        msg["Subject"] = "MAREF通知测试"
        msg["From"] = username
        msg["To"] = receiver

        # 建立连接
        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, port, context=context, timeout=10) as smtp:
                smtp.login(username, password)
                smtp.sendmail(username, [receiver], msg.as_string())
        else:
            with smtplib.SMTP(server, port, timeout=10) as smtp:
                smtp.ehlo()
                if use_tls:
                    smtp.starttls()
                    smtp.ehlo()
                smtp.login(username, password)
                smtp.sendmail(username, [receiver], msg.as_string())

        print(f"✅ 测试邮件发送成功")
        print(f"  发件人: {username}")
        print(f"  收件人: {receiver}")
        return True

    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False


def main():
    """主函数"""
    print("QQ邮箱SMTP配置深度测试\n")

    # 测试不同配置
    best_config = test_qq_email_variations()

    # 检查要求
    check_qq_email_requirements()

    # 如果找到可用配置，测试发送
    if best_config:
        test_email_sending(best_config)

    print(f"\n{'='*60}")
    print("测试完成总结:")
    if best_config:
        print(f"✅ 找到可用配置: {best_config[4]}")
        print(f"   服务器: {best_config[0]}:{best_config[1]}")
        print("\n更新 config/notifier_config.json:")
        print(f'   "email_smtp_server": "{best_config[0]}",')
        print(f'   "email_smtp_port": {best_config[1]},')
        print(f'   "email_sender": "athenabot@qq.com",')
        if best_config[2]:  # SSL
            print("   # 注意: 端口465需要使用SMTP_SSL")
        elif best_config[3]:  # TLS
            print("   # 注意: 端口587使用STARTTLS")
    else:
        print("❌ 未找到可用配置")
        print("\n建议:")
        print("1. 确认QQ邮箱已开启SMTP服务")
        print("2. 确认使用的是16位授权码而非登录密码")
        print("3. 尝试在QQ邮箱网页版重新生成授权码")
        print("4. 检查网络连接和防火墙设置")


if __name__ == "__main__":
    main()
