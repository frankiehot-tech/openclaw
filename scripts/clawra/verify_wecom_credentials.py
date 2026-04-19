#!/usr/bin/env python3
"""
企业微信凭据验证脚本
根据用户选择的选项A（API直接验证），验证Athena机器人凭据的有效性
探索bot id和secret的真正用途
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# 添加当前目录到路径以便导入模块
sys.path.insert(0, str(Path(__file__).parent))


def load_env_vars() -> Dict[str, str]:
    """从.env文件加载环境变量"""
    env_vars = {}
    env_file = Path(__file__).parent / ".env"

    if not env_file.exists():
        print(f"❌ 找不到.env文件: {env_file}")
        return env_vars

    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # 移除引号
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]

                env_vars[key] = value

    return env_vars


def test_webhook_with_key(key: str) -> Dict[str, Any]:
    """测试使用key作为webhook参数"""
    print(f"\n=== 测试webhook key: {key[:20]}... ===")

    # 标准企业微信机器人webhook格式
    webhook_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"

    results = {"key": key, "webhook_url": webhook_url, "tests": [], "success": False}

    # 测试1: GET请求（应该返回405）
    try:
        response = requests.get(webhook_url, timeout=10)
        test_result = {
            "name": "GET请求",
            "status_code": response.status_code,
            "success": response.status_code == 405,
            "note": (
                "GET应返回405 (Method Not Allowed)"
                if response.status_code == 405
                else "意外的状态码"
            ),
        }
        results["tests"].append(test_result)
    except Exception as e:
        results["tests"].append({"name": "GET请求", "success": False, "error": str(e)})

    # 测试2: POST请求（发送测试消息）
    payload = {"msgtype": "text", "text": {"content": "MAREF通知系统凭据验证测试"}}

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        test_result = {
            "name": "POST请求",
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "response_text": response.text[:200] if response.text else "",
        }

        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("errcode") == 0:
                    test_result["note"] = "✅ webhook有效，消息发送成功"
                    results["success"] = True
                else:
                    test_result["note"] = f"webhook返回错误: {data.get('errmsg', '未知错误')}"
            except json.JSONDecodeError:
                test_result["note"] = "webhook返回非JSON响应"
        else:
            test_result["note"] = f"webhook请求失败，状态码: {response.status_code}"

        results["tests"].append(test_result)

    except Exception as e:
        results["tests"].append({"name": "POST请求", "success": False, "error": str(e)})

    return results


def test_app_api(corp_id: str, secret: str, agent_id: str) -> Dict[str, Any]:
    """测试企业微信应用API"""
    print(f"\n=== 测试企业微信应用API ===")
    print(f"CorpID: {corp_id}")
    print(f"AgentId: {agent_id}")
    print(f"Secret: {'*' * len(secret)}")

    results = {"corp_id": corp_id, "agent_id": agent_id, "tests": [], "success": False}

    # 步骤1: 获取access_token
    token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={secret}"

    try:
        response = requests.get(token_url, timeout=10)
        test_result = {
            "name": "获取access_token",
            "status_code": response.status_code,
            "url": token_url,
        }

        if response.status_code == 200:
            try:
                data = response.json()
                test_result["response"] = data

                if data.get("errcode") == 0:
                    access_token = data.get("access_token")
                    expires_in = data.get("expires_in", 7200)
                    test_result["success"] = True
                    test_result["note"] = f"✅ access_token获取成功，有效期: {expires_in}秒"

                    # 保存access_token用于后续测试
                    results["access_token"] = access_token
                    results["access_token_expires"] = expires_in

                    # 步骤2: 发送测试消息
                    send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
                    payload = {
                        "touser": "@all",
                        "msgtype": "text",
                        "agentid": agent_id,
                        "text": {"content": "MAREF通知系统应用API测试"},
                        "safe": 0,
                    }

                    try:
                        send_response = requests.post(send_url, json=payload, timeout=10)
                        send_test = {
                            "name": "发送测试消息",
                            "status_code": send_response.status_code,
                            "url": send_url,
                        }

                        if send_response.status_code == 200:
                            send_data = send_response.json()
                            send_test["response"] = send_data

                            if send_data.get("errcode") == 0:
                                send_test["success"] = True
                                send_test["note"] = "✅ 消息发送成功"
                                results["success"] = True
                            else:
                                send_test["success"] = False
                                send_test["note"] = f"消息发送失败: {send_data.get('errmsg')}"
                                send_test["error_code"] = send_data.get("errcode")
                        else:
                            send_test["success"] = False
                            send_test["note"] = f"HTTP请求失败: {send_response.status_code}"

                        results["tests"].append(send_test)

                    except Exception as e:
                        results["tests"].append(
                            {"name": "发送测试消息", "success": False, "error": str(e)}
                        )

                else:
                    test_result["success"] = False
                    test_result["note"] = f"获取access_token失败: {data.get('errmsg')}"
                    test_result["error_code"] = data.get("errcode")

            except json.JSONDecodeError as e:
                test_result["success"] = False
                test_result["note"] = f"JSON解析失败: {e}"
        else:
            test_result["success"] = False
            test_result["note"] = f"HTTP请求失败: {response.status_code}"

        results["tests"].insert(0, test_result)

    except Exception as e:
        results["tests"].append({"name": "获取access_token", "success": False, "error": str(e)})

    return results


def test_local_webhook_service(
    webhook_url: str, token: str = None, encoding_aes_key: str = None
) -> Dict[str, Any]:
    """测试本地webhook服务（如果配置了的话）"""
    print(f"\n=== 测试本地webhook服务 ===")
    print(f"URL: {webhook_url}")

    results = {"webhook_url": webhook_url, "tests": [], "success": False}

    # 测试1: GET请求检查服务是否运行
    try:
        response = requests.get(webhook_url, timeout=5)
        test_result = {
            "name": "服务连通性",
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "note": (
                "服务运行正常" if response.status_code == 200 else f"服务返回{response.status_code}"
            ),
        }
        results["tests"].append(test_result)
    except Exception as e:
        results["tests"].append({"name": "服务连通性", "success": False, "error": str(e)})
        return results  # 服务不可用，直接返回

    # 测试2: POST请求发送消息
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-WeCom-Token"] = token
    if encoding_aes_key:
        headers["X-WeCom-Encoding-AES-Key"] = encoding_aes_key

    payloads = [
        {"msgtype": "text", "text": {"content": "MAREF本地webhook测试"}},
        {"text": "简单文本测试"},
        {"test": "message"},
    ]

    for i, payload in enumerate(payloads, 1):
        try:
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
            test_result = {
                "name": f"POST测试{i}",
                "status_code": response.status_code,
                "payload_type": type(payload).__name__,
                "success": response.status_code == 200,
                "response_preview": response.text[:100] if response.text else "",
            }

            if response.status_code == 200:
                test_result["note"] = "✅ 请求成功"
                results["success"] = True
            else:
                test_result["note"] = f"请求失败，状态码: {response.status_code}"

            results["tests"].append(test_result)

        except Exception as e:
            results["tests"].append({"name": f"POST测试{i}", "success": False, "error": str(e)})

    return results


def analyze_bot_credentials(bot_id: str, bot_secret: str) -> Dict[str, Any]:
    """分析bot凭据的可能用途"""
    print(f"\n=== 分析Athena机器人凭据 ===")
    print(f"Bot ID: {bot_id}")
    print(f"Bot Secret: {'*' * len(bot_secret)}")

    analysis = {
        "bot_id": bot_id,
        "bot_secret_length": len(bot_secret),
        "possible_uses": [],
        "key_observations": [],
    }

    # 观察bot id格式
    if "-" in bot_id:
        analysis["key_observations"].append("Bot ID包含连字符，可能是自定义标识符")
    if len(bot_id) == 43:
        analysis["key_observations"].append("Bot ID长度为43个字符")

    # 观察secret格式
    if len(bot_secret) == 64:
        analysis["key_observations"].append("Bot Secret长度为64个字符，可能是Base64编码或哈希值")

    # 可能的用途
    analysis["possible_uses"].append(
        {
            "type": "webhook_key",
            "description": "Bot ID可能是企业微信机器人的webhook key",
            "test_method": "直接测试webhook URL",
            "confidence": "中等" if "-" in bot_id else "低",
        }
    )

    analysis["possible_uses"].append(
        {
            "type": "custom_api_auth",
            "description": "Bot ID和Secret可能是自定义API的身份验证凭据",
            "test_method": "需要查看Athena服务文档",
            "confidence": "中等",
        }
    )

    analysis["possible_uses"].append(
        {
            "type": "encryption_keys",
            "description": "可能是用于消息加密解密的密钥对",
            "test_method": "需要实现加密算法测试",
            "confidence": "低",
        }
    )

    return analysis


def generate_possible_webhook_keys(bot_id: str) -> List[str]:
    """基于bot id生成可能的webhook key变体"""
    variants = []

    # 变体1: 直接使用
    variants.append(bot_id)

    # 变体2: 如果是自定义格式，可能包含前缀/后缀
    if "-" in bot_id:
        # 尝试移除可能的前缀
        parts = bot_id.split("-")
        if len(parts) > 1:
            # 假设格式是 "前缀-实际key"
            variants.append(parts[-1])  # 最后一部分
            variants.append("-".join(parts[1:]))  # 移除第一部分

    # 变体3: 尝试不同的分隔符处理
    variants.append(bot_id.replace("-", ""))

    # 变体4: 尝试反转部分
    if len(bot_id) > 20:
        variants.append(bot_id[:32])  # 截断到32位

    return list(set(variants))  # 去重


def main():
    """主函数"""
    print("=" * 60)
    print("企业微信凭据验证工具 - API直接验证（选项A）")
    print("=" * 60)

    # 加载环境变量
    env_vars = load_env_vars()
    if not env_vars:
        print("❌ 无法加载环境变量")
        return

    print(f"加载了 {len(env_vars)} 个环境变量")

    # 提取关键凭据
    wecom_webhook_url = env_vars.get("WECOM_WEBHOOK_URL", "")
    wecom_token = env_vars.get("WECOM_WEBHOOK_TOKEN", "")
    wecom_encoding_aes_key = env_vars.get("WECOM_ENCODING_AES_KEY", "")

    wecom_corpid = env_vars.get("WECOM_CORPID", "")
    wecom_agentid = env_vars.get("WECOM_AGENTID", "")
    wecom_secret = env_vars.get("WECOM_SECRET", "")

    athena_bot_id = env_vars.get("ATHENA_BOT_ID", "")
    athena_bot_secret = env_vars.get("ATHENA_BOT_SECRET", "")

    print(f"\n=== 加载的凭据摘要 ===")
    print(f"1. 企业微信应用API:")
    print(f"   • CorpID: {wecom_corpid[:10]}..." if wecom_corpid else "   • 未设置")
    print(f"   • AgentId: {wecom_agentid}")
    print(f"   • Secret: {'*' * len(wecom_secret) if wecom_secret else '未设置'}")

    print(f"\n2. 本地webhook服务:")
    print(f"   • URL: {wecom_webhook_url}")
    print(f"   • Token: {'*' * len(wecom_token) if wecom_token else '未设置'}")
    print(
        f"   • EncodingAESKey: {'*' * len(wecom_encoding_aes_key) if wecom_encoding_aes_key else '未设置'}"
    )

    print(f"\n3. Athena机器人:")
    print(f"   • Bot ID: {athena_bot_id}")
    print(f"   • Bot Secret: {'*' * len(athena_bot_secret) if athena_bot_secret else '未设置'}")

    # 分析bot凭据
    if athena_bot_id:
        analysis = analyze_bot_credentials(athena_bot_id, athena_bot_secret)

        print(f"\n=== Athena机器人凭据分析 ===")
        for observation in analysis.get("key_observations", []):
            print(f"• {observation}")

        print(f"\n可能的用途:")
        for use in analysis.get("possible_uses", []):
            print(f"  • {use['type']}: {use['description']} (置信度: {use['confidence']})")

    all_results = {}

    # 测试1: 尝试将bot id作为webhook key
    if athena_bot_id:
        print(f"\n" + "=" * 60)
        print("测试1: 尝试将Bot ID作为webhook key")
        print("=" * 60)

        # 生成可能的key变体
        possible_keys = generate_possible_webhook_keys(athena_bot_id)
        print(f"生成 {len(possible_keys)} 个可能的webhook key变体:")
        for i, key in enumerate(possible_keys, 1):
            print(f"  {i}. {key}")

        # 测试每个变体
        webhook_results = []
        for key in possible_keys:
            result = test_webhook_with_key(key)
            webhook_results.append(result)

            # 如果成功，打印详细信息
            if result.get("success"):
                print(f"\n🎉 找到有效的webhook key: {key}")
                print(f"    webhook URL: {result['webhook_url']}")

        all_results["webhook_tests"] = webhook_results

        # 总结webhook测试
        successful_webhooks = [r for r in webhook_results if r.get("success")]
        if successful_webhooks:
            print(f"\n✅ 发现 {len(successful_webhooks)} 个有效的webhook配置")
        else:
            print(f"\n❌ 所有webhook key变体测试失败")

    # 测试2: 测试企业微信应用API
    if wecom_corpid and wecom_secret and wecom_agentid:
        print(f"\n" + "=" * 60)
        print("测试2: 企业微信应用API")
        print("=" * 60)

        app_api_results = test_app_api(wecom_corpid, wecom_secret, wecom_agentid)
        all_results["app_api_tests"] = app_api_results

        if app_api_results.get("success"):
            print(f"\n✅ 企业微信应用API测试成功")
            if "access_token" in app_api_results:
                print(f"   access_token: {app_api_results['access_token'][:20]}...")
                print(f"   有效期: {app_api_results.get('access_token_expires', 0)}秒")
        else:
            print(f"\n❌ 企业微信应用API测试失败")
            for test in app_api_results.get("tests", []):
                if not test.get("success", False):
                    print(f"   • {test['name']}: {test.get('note', '失败')}")

    # 测试3: 测试本地webhook服务
    if wecom_webhook_url:
        print(f"\n" + "=" * 60)
        print("测试3: 本地webhook服务")
        print("=" * 60)

        local_service_results = test_local_webhook_service(
            wecom_webhook_url, wecom_token, wecom_encoding_aes_key
        )
        all_results["local_service_tests"] = local_service_results

        if local_service_results.get("success"):
            print(f"\n✅ 本地webhook服务测试成功")
        else:
            print(f"\n❌ 本地webhook服务测试失败")

    # 总结和下一步建议
    print(f"\n" + "=" * 60)
    print("验证结果总结")
    print("=" * 60)

    successful_tests = []
    if "webhook_tests" in all_results:
        successful_webhooks = [r for r in all_results["webhook_tests"] if r.get("success")]
        if successful_webhooks:
            successful_tests.append(f"webhook验证 ({len(successful_webhooks)}个有效key)")

    if "app_api_tests" in all_results and all_results["app_api_tests"].get("success"):
        successful_tests.append("应用API验证")

    if "local_service_tests" in all_results and all_results["local_service_tests"].get("success"):
        successful_tests.append("本地webhook服务验证")

    if successful_tests:
        print(f"\n✅ 验证成功: {', '.join(successful_tests)}")

        # 提供更新配置的建议
        print(f"\n💡 下一步建议:")
        print("1. 根据验证结果更新配置文件")

        if "webhook_tests" in all_results:
            successful_webhooks = [r for r in all_results["webhook_tests"] if r.get("success")]
            if successful_webhooks:
                first_success = successful_webhooks[0]
                print(f"2. 使用有效的webhook key: {first_success['key']}")
                print(f"   对应的webhook URL: {first_success['webhook_url']}")
                print(f"   更新.env文件中的WECOM_WEBHOOK_URL为: {first_success['webhook_url']}")

        if "app_api_tests" in all_results and all_results["app_api_tests"].get("success"):
            print(f"3. 企业微信应用API可用，可配置IP白名单以获得更稳定连接")

        print(f"\n4. 运行完整通知测试:")
        print(f"   python3 test_notification_channels_final.py")

    else:
        print(f"\n❌ 所有验证测试失败")
        print(f"\n💡 下一步建议:")
        print("1. 检查凭据是否正确（特别是Athena机器人凭据）")
        print("2. 确认企业微信管理后台中机器人是否已正确配置")
        print("3. 检查网络连接，确保能访问企业微信API")
        print("4. 如果使用应用API，确认服务器IP已添加到企业微信白名单")
        print("5. 考虑使用浏览器自动化重新获取webhook URL")
        print(f"\n6. 可尝试手动获取webhook URL:")
        print(f"   a. 登录企业微信管理后台")
        print(f"   b. 找到Athena机器人所在的群聊")
        print(f"   c. 查看机器人设置，获取webhook URL")
        print(f"   d. 格式应为: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx")

    # 保存详细结果到文件
    results_file = Path(__file__).parent / "wecom_credentials_verification_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n📁 详细验证结果已保存到: {results_file}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        import traceback

        traceback.print_exc()
