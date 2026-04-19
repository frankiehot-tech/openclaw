#!/usr/bin/env python3
"""
测试企业微信API调用
探索两种方式：
1. Webhook方式（用户提供的本地webhook）
2. 应用API方式（使用CorpID、AgentId、Secret）
"""

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))

from maref_notifier import MAREFNotifier


def test_wecom_webhook_direct():
    """直接测试企业微信webhook"""
    print("=== 直接测试企业微信webhook ===")

    # 从配置文件读取webhook
    config_path = "config/notifier_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    wecom_webhook = config.get("wecom_webhook", "")
    print(f"Webhook地址: {wecom_webhook}")

    if not wecom_webhook:
        print("❌ Webhook未配置")
        return

    # 测试不同的请求格式
    test_payloads = [
        {"msgtype": "markdown", "markdown": {"content": "# 测试消息\n这是来自MAREF的测试消息"}},
        {
            "msgtype": "text",
            "text": {"content": "测试消息: 来自MAREF通知系统", "mentioned_list": ["@all"]},
        },
        {"text": {"content": "简单文本测试"}},
    ]

    for i, payload in enumerate(test_payloads, 1):
        print(f"\n测试格式 #{i}:")
        print(f"请求体: {json.dumps(payload, ensure_ascii=False)}")

        try:
            response = requests.post(
                wecom_webhook,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )

            print(f"状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")

            if response.status_code == 200:
                print(f"响应内容: {response.text[:200]}")
            else:
                print(f"错误响应: {response.text[:500]}")

        except Exception as e:
            print(f"请求异常: {e}")


def test_wecom_app_api():
    """测试企业微信应用API方式"""
    print("\n=== 测试企业微信应用API ===")

    # 用户提供的凭据
    corp_id = "ww02c09b741b716c32"
    agent_id = "1000002"
    secret = "REDACTED_WECOM_SECRET"

    print(f"CorpID: {corp_id}")
    print(f"AgentId: {agent_id}")
    print(f"Secret: {'*' * len(secret) if secret else '未设置'}")

    # 1. 获取access_token
    token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={secret}"
    print(f"\n1. 获取access_token: {token_url}")

    try:
        response = requests.get(token_url, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"响应: {json.dumps(result, ensure_ascii=False)}")

            if result.get("errcode") == 0:
                access_token = result.get("access_token")
                print(f"✅ Access token获取成功: {access_token[:20]}...")

                # 2. 发送消息
                send_url = (
                    f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
                )
                message_payload = {
                    "touser": "@all",
                    "msgtype": "text",
                    "agentid": agent_id,
                    "text": {"content": "测试消息: MAREF通知系统深度审计"},
                    "safe": 0,
                }

                print(f"\n2. 发送测试消息...")
                print(f"URL: {send_url}")
                print(f"请求体: {json.dumps(message_payload, ensure_ascii=False)}")

                send_response = requests.post(send_url, json=message_payload, timeout=10)
                print(f"状态码: {send_response.status_code}")
                print(f"响应: {json.dumps(send_response.json(), ensure_ascii=False)}")

                return True
            else:
                print(f"❌ Access token获取失败: {result.get('errmsg')}")
                return False
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ API调用异常: {e}")
        return False


def test_wecom_with_token_aes():
    """测试带Token和EncodingAESKey的webhook"""
    print("\n=== 测试带Token和AESKey的webhook ===")

    # 用户提供的Token和EncodingAESKey
    token = "6XeXrzS9AbblMaNY3ht8jv"
    encoding_aes_key = "pdSSqKddM6cmqL5xjrIfhx8wkgwyignjcfT5OlraXCc"
    webhook = "http://127.0.0.1:18789/wecom/webhook"

    print(f"Token: {'*' * len(token) if token else '未设置'}")
    print(f"EncodingAESKey: {'*' * len(encoding_aes_key) if encoding_aes_key else '未设置'}")
    print(f"Webhook: {webhook}")

    # 尝试不同的请求头
    headers = {
        "Content-Type": "application/json",
        "X-WeCom-Token": token,
        "X-WeCom-Encoding-AES-Key": encoding_aes_key,
    }

    payload = {"msgtype": "text", "text": {"content": "测试带Token验证的消息"}}

    try:
        print(f"发送带Token的请求...")
        response = requests.post(webhook, json=payload, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容: {response.text[:500]}")

        return response.status_code == 200
    except Exception as e:
        print(f"请求异常: {e}")
        return False


def check_wecom_configuration():
    """检查企业微信配置建议"""
    print("\n=== 企业微信配置建议 ===")

    print("1. Webhook方式（当前配置）:")
    print("   - 优点: 简单，直接调用")
    print("   - 问题: 404错误表明端点不期望我们的请求格式")
    print("   - 建议: 检查webhook服务期望的请求格式")

    print("\n2. 应用API方式:")
    print("   - 需要: CorpID, AgentId, Secret")
    print("   - 流程: 获取access_token → 发送消息")
    print("   - 优点: 官方标准方式，功能完整")
    print("   - 缺点: 需要实现token管理和刷新")

    print("\n3. 安全建议:")
    print("   - 将Token/Secret存储在环境变量而非配置文件中")
    print("   - 使用HTTPS而非HTTP")
    print("   - 定期轮换Secret")

    # 检查是否需要修改通知器代码
    print("\n4. 代码修改建议:")
    print("   - 如果使用应用API，需要修改maref_notifier.py")
    print("   - 实现get_wecom_access_token()方法")
    print("   - 更新send_wecom_message()使用应用API")


def main():
    """主函数"""
    print("=== 企业微信通知渠道深度诊断 ===\n")

    # 测试当前webhook
    test_wecom_webhook_direct()

    # 测试应用API方式
    test_wecom_app_api()

    # 测试带Token的webhook
    test_wecom_with_token_aes()

    # 提供配置建议
    check_wecom_configuration()

    print("\n✅ 诊断完成")
    print("\n下一步建议:")
    print("1. 确定使用哪种企业微信集成方式")
    print("2. 根据选择更新配置和代码")
    print("3. 重新测试通知功能")


if __name__ == "__main__":
    main()
