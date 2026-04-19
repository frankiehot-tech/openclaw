#!/usr/bin/env python3
"""
探索企业微信webhook服务
尝试发现正确的API端点和请求格式
"""

import json

import requests


def explore_endpoints(base_url="http://127.0.0.1:18789"):
    """探索可能的端点"""
    print(f"=== 探索企业微信服务端点 ({base_url}) ===\n")

    # 测试可能的端点
    endpoints = [
        "/",
        "/wecom",
        "/wecom/",
        "/wecom/webhook",
        "/wecom/api",
        "/wecom/api/webhook",
        "/wecom/bot",
        "/wecom/bot/webhook",
        "/api/wecom",
        "/api/wecom/webhook",
        "/webhook",
        "/webhook/wecom",
    ]

    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"测试: {url}")

        try:
            # 测试GET请求
            response = requests.get(url, timeout=5)
            print(
                f"  GET: {response.status_code} - {response.headers.get('Content-Type', 'unknown')}"
            )

            # 如果返回成功，尝试POST
            if response.status_code == 200:
                print(f"  内容长度: {len(response.text)}")
                if len(response.text) < 500:
                    print(f"  内容预览: {response.text[:200]}")

                # 尝试POST简单消息
                post_payload = {"test": "message"}
                post_response = requests.post(url, json=post_payload, timeout=5)
                print(f"  POST: {post_response.status_code}")

        except Exception as e:
            print(f"  错误: {e}")

        print()


def test_request_formats(webhook_url):
    """测试不同的请求格式"""
    print(f"\n=== 测试请求格式 ({webhook_url}) ===")

    test_cases = [
        ("JSON简单文本", {"text": "测试消息"}),
        ("JSON带msgtype", {"msgtype": "text", "text": {"content": "测试"}}),
        ("JSON带markdown", {"msgtype": "markdown", "markdown": {"content": "# 测试"}}),
        ("Form数据", None),  # 需要不同的content-type
        ("带query参数", None),  # 测试URL参数
    ]

    for name, payload in test_cases:
        print(f"\n测试: {name}")

        try:
            if payload:
                # 测试JSON格式
                response = requests.post(webhook_url, json=payload, timeout=5)
                print(f"  JSON POST: {response.status_code}")
                if response.status_code != 200:
                    print(f"    响应: {response.text[:100]}")

                # 测试不同的Content-Type
                headers = {"Content-Type": "application/json"}
                response2 = requests.post(webhook_url, json=payload, headers=headers, timeout=5)
                if response2.status_code != response.status_code:
                    print(f"  自定义Header POST: {response2.status_code}")
        except Exception as e:
            print(f"  错误: {e}")


def check_service_info(base_url="http://127.0.0.1:18789"):
    """检查服务信息"""
    print(f"\n=== 检查服务信息 ===")

    # 测试常见的管理端点
    admin_endpoints = [
        "/health",
        "/status",
        "/info",
        "/version",
        "/ping",
        "/api/health",
        "/api/status",
    ]

    for endpoint in admin_endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                print(f"✅ {endpoint}: 可用")
                print(f"   响应: {response.text[:200]}")
        except:
            pass


def check_wecom_documentation():
    """提供企业微信配置文档参考"""
    print("\n=== 企业微信配置参考 ===")

    print("1. 企业微信机器人webhook格式:")
    print("   URL格式: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY")
    print("   请求体示例:")
    print('   {"msgtype":"text","text":{"content":"消息内容"}}')

    print("\n2. 企业微信应用API格式:")
    print(
        "   1) 获取token: GET https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=ID&corpsecret=SECRET"
    )
    print(
        "   2) 发送消息: POST https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=TOKEN"
    )
    print("   请求体示例:")
    print('   {"touser":"@all","msgtype":"text","agentid":AGENT_ID,"text":{"content":"消息"}}')

    print("\n3. IP白名单错误 (errcode: 60020):")
    print("   - 原因: 调用API的IP不在企业微信应用的白名单中")
    print("   - 解决: 在企业微信管理后台添加服务器IP到白名单")
    print("   - 或使用webhook方式绕过IP限制")


def main():
    """主函数"""
    print("企业微信服务探索工具\n")

    base_url = "http://127.0.0.1:18789"

    # 1. 探索端点
    explore_endpoints(base_url)

    # 2. 测试请求格式
    webhook_url = "http://127.0.0.1:18789/wecom/webhook"
    test_request_formats(webhook_url)

    # 3. 检查服务信息
    check_service_info(base_url)

    # 4. 提供文档参考
    check_wecom_documentation()

    print("\n=== 探索结果总结 ===")
    print("1. Webhook服务运行在: http://127.0.0.1:18789")
    print("2. GET /wecom/webhook 返回200，但POST返回404")
    print("3. 可能需要不同的端点路径或请求格式")
    print("4. 企业微信应用API可用，但受IP白名单限制")
    print("\n建议:")
    print("- 检查webhook服务的日志或文档")
    print("- 或配置企业微信IP白名单使用应用API")
    print("- 或使用企业微信机器人webhook（如果可用）")


if __name__ == "__main__":
    main()
