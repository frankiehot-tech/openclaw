#!/usr/bin/env python3
"""
最终通知渠道测试
测试所有配置的通知渠道，包括环境变量配置
"""

import json
import os
import smtplib
import ssl
import sys
from datetime import datetime

import requests

# 加载.env文件
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_file):
    print(f"加载环境变量文件: {env_file}")
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                os.environ[key] = value

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from maref_notifier import MAREFNotifier


def test_wecom_webhook():
    """测试企业微信webhook"""
    print("\n=== 企业微信Webhook测试 ===")
    webhook_url = os.getenv("WECOM_WEBHOOK_URL")
    if not webhook_url:
        print("❌ 未配置企业微信Webhook URL")
        return False

    print(f"测试Webhook: {webhook_url}")

    # 测试GET请求
    try:
        response = requests.get(webhook_url, timeout=5)
        print(f"GET请求: {response.status_code}")
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" in content_type:
                print("⚠️  返回HTML内容，可能不是API端点")
                # 检查内容是否包含OpenClaw
                if "OpenClaw" in response.text:
                    print("⚠️  检测到OpenClaw Control界面，不是webhook接收器")
            else:
                print(f"✅ 返回非HTML内容: {content_type}")
        else:
            print(f"❌ GET请求失败: {response.status_code}")
    except Exception as e:
        print(f"❌ GET请求异常: {e}")

    # 测试POST请求
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": "## 测试消息\n\n这是来自MAREF通知系统的测试消息\n\n**时间**: "
            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        print(f"POST请求: {response.status_code}")
        if response.status_code == 200:
            print("✅ Webhook POST请求成功")
            try:
                data = response.json()
                print(f"响应: {data}")
                return True
            except:
                print(f"响应文本: {response.text[:200]}")
                return True
        else:
            print(f"❌ POST请求失败: {response.status_code}")
            print(f"响应: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ POST请求异常: {e}")
        return False


def test_wecom_api():
    """测试企业微信应用API"""
    print("\n=== 企业微信应用API测试 ===")
    corpid = os.getenv("WECOM_CORPID")
    secret = os.getenv("WECOM_SECRET")
    agentid = os.getenv("WECOM_AGENTID")

    if not corpid or not secret or not agentid:
        print("❌ 企业微信应用API配置不完整")
        return False

    print(f"CorpID: {corpid}")
    print(f"AgentId: {agentid}")
    print(f"Secret: {'*' * len(secret)}")

    # 1. 获取Access Token
    token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={secret}"
    print(f"\n1. 获取Access Token...")
    try:
        response = requests.get(token_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("errcode") == 0:
                access_token = data.get("access_token")
                expires_in = data.get("expires_in", 7200)
                print(f"✅ Access Token获取成功")
                print(f"   Token: {access_token[:20]}...")
                print(f"   过期时间: {expires_in}秒")
            else:
                print(f"❌ Token获取失败: {data.get('errmsg')}")
                return False
        else:
            print(f"❌ Token请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Token请求异常: {e}")
        return False

    # 2. 发送测试消息
    print(f"\n2. 发送测试消息...")
    api_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    payload = {
        "touser": "@all",
        "msgtype": "text",
        "agentid": agentid,
        "text": {"content": f"MAREF通知测试: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
        "safe": 0,
    }

    try:
        response = requests.post(api_url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            errcode = data.get("errcode")
            errmsg = data.get("errmsg")
            if errcode == 0:
                print(f"✅ 消息发送成功")
                return True
            else:
                print(f"❌ 消息发送失败: {errcode} - {errmsg}")
                if errcode == 60020:
                    print("⚠️  IP白名单错误: 服务器IP不在企业微信应用白名单中")
                    print("   请在企微管理后台添加服务器IP到白名单")
                return False
        else:
            print(f"❌ 消息请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 消息请求异常: {e}")
        return False


def test_email_smtp():
    """测试QQ邮箱SMTP连接"""
    print("\n=== QQ邮箱SMTP测试 ===")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    use_ssl = os.getenv("SMTP_USE_SSL", "").lower() == "true"
    use_tls = os.getenv("SMTP_USE_TLS", "").lower() == "true"

    if not all([smtp_server, smtp_port, username, password]):
        print("❌ SMTP配置不完整")
        return False

    print(f"服务器: {smtp_server}:{smtp_port}")
    print(f"用户名: {username}")
    print(f"密码: {'*' * len(password)}")
    print(f"SSL: {use_ssl}, TLS: {use_tls}")

    # 检查密码长度
    if len(password) != 16:
        print(f"⚠️  警告: 密码长度{len(password)}，QQ邮箱需要16位授权码")
        print("   请登录QQ邮箱网页版生成16位授权码")

    try:
        if use_ssl:
            # SSL连接
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                smtp_server, int(smtp_port), context=context, timeout=10
            ) as server:
                print(f"✅ SSL连接建立")
                server.login(username, password)
                print(f"✅ 登录成功")
                return True
        else:
            # 普通连接
            with smtplib.SMTP(smtp_server, int(smtp_port), timeout=10) as server:
                print(f"✅ 连接建立")
                server.ehlo()

                if use_tls:
                    print(f"  启用STARTTLS...")
                    server.starttls()
                    server.ehlo()

                print(f"  尝试登录...")
                server.login(username, password)
                print(f"✅ 登录成功")
                return True
    except Exception as e:
        print(f"❌ SMTP连接失败: {e}")
        return False


def test_notifier_integration():
    """测试通知器集成"""
    print("\n=== 通知器集成测试 ===")

    try:
        notifier = MAREFNotifier()
        print("✅ 通知器初始化成功")

        # 测试预警数据
        test_alerts = [
            {
                "title": "通知系统配置测试",
                "description": "测试所有通知渠道的连通性",
                "recommendation": "验证企业微信、邮件等渠道配置",
                "duration": 300,
                "priority": "test",
                "metrics_snapshot": {"test": True},
            }
        ]

        print("\n发送测试通知...")
        results = notifier.send_alert("yellow", test_alerts, "/tmp/test_report.md")

        print(f"\n发送结果:")
        print(f"成功渠道: {results['sent']}")
        print(f"失败渠道: {results['failed']}")
        print(f"渠道详情: {results['channels']}")

        # 检查各个渠道状态
        print("\n详细状态:")
        for channel, status in results["channels"].items():
            emoji = "✅" if status == "success" else "❌"
            print(f"  {emoji} {channel}: {status}")

        # 检查失败原因
        failed_channels = [k for k, v in results["channels"].items() if v == "failed"]
        if failed_channels:
            print(f"\n⚠️  以下渠道失败: {failed_channels}")
            print("   可能原因:")
            if "wecom" in failed_channels:
                print("   - 企业微信: webhook端点不正确或应用API受IP限制")
            if "email" in failed_channels:
                print("   - 邮件: SMTP配置错误或密码不正确")

        return results["sent"] > 0

    except Exception as e:
        print(f"❌ 通知器测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("MAREF通知系统最终测试")
    print("=" * 60)

    # 检查环境变量
    print("检查关键环境变量...")
    required_vars = ["WECOM_WEBHOOK_URL", "SMTP_SERVER", "SMTP_USERNAME", "SMTP_PASSWORD"]
    for var in required_vars:
        value = os.getenv(var)
        if value:
            masked = "***" if "PASSWORD" in var else value
            print(f"  ✅ {var}: {masked}")
        else:
            print(f"  ❌ {var}: 未设置")

    print(f"\n{'='*60}")

    # 运行各个测试
    test_results = {}

    # 1. 企业微信webhook测试
    test_results["wecom_webhook"] = test_wecom_webhook()

    # 2. 企业微信应用API测试
    test_results["wecom_api"] = test_wecom_api()

    # 3. 邮件SMTP测试
    test_results["email_smtp"] = test_email_smtp()

    # 4. 通知器集成测试
    test_results["notifier"] = test_notifier_integration()

    print(f"\n{'='*60}")
    print("测试结果汇总:")
    for test_name, result in test_results.items():
        emoji = "✅" if result else "❌"
        print(f"  {emoji} {test_name}: {'通过' if result else '失败'}")

    # 总结建议
    print(f"\n{'='*60}")
    print("问题诊断与建议:")

    if not test_results["wecom_webhook"] and not test_results["wecom_api"]:
        print("\n❌ 企业微信通知不可用:")
        print("   1. Webhook端点不正确 (返回404)")
        print("   2. 应用API受IP白名单限制 (errcode: 60020)")
        print("   建议:")
        print("   - 方案A: 找到正确的webhook端点 (检查OpenClaw Control API文档)")
        print("   - 方案B: 在企业微信管理后台添加服务器IP到白名单")
        print("   - 方案C: 使用企业微信机器人webhook")

    if not test_results["email_smtp"]:
        print("\n❌ 邮件通知不可用:")
        print("   QQ邮箱SMTP连接失败，可能原因:")
        print("   1. 密码错误 - 需要使用16位授权码而非登录密码")
        print("   2. SMTP服务未开启 - 需要在QQ邮箱设置中开启")
        print("   3. 网络限制 - 可能被防火墙阻止")
        print("   建议:")
        print("   - 登录QQ邮箱网页版，生成16位授权码")
        print("   - 更新.env文件中的SMTP_PASSWORD")
        print("   - 测试不同端口(465/587)和加密方式(SSL/TLS)")

    if test_results["notifier"]:
        print("\n✅ 通知器集成测试通过")
        print("   控制台和文件日志渠道正常工作")
    else:
        print("\n⚠️  通知器集成测试部分失败")
        print("   但控制台和文件日志渠道应仍可用")

    print(f"\n{'='*60}")
    print("下一步行动:")
    print("1. 获取QQ邮箱16位授权码，更新.env文件")
    print("2. 确定企业微信集成方案 (A/B/C)")
    print("3. 验证Athena服务是否运行 (启动Athena通知服务)")
    print("4. 测试生产环境日报发送")

    return all(test_results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
