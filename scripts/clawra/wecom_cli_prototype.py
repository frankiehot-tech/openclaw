#!/usr/bin/env python3
"""
企业微信CLI原型
基于AppleScript的CLI-Anything包装器，用于企业微信相关问题解决
"""

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

import click
import requests


def run_applescript(script: str) -> str:
    """运行AppleScript并返回结果"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            raise RuntimeError(f"AppleScript错误: {result.stderr}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError("AppleScript执行超时")


def escape_for_applescript(text: str) -> str:
    """转义字符串用于AppleScript"""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return escaped


class WeComCLI:
    """企业微信CLI控制器"""

    def __init__(self, browser: str = "Safari"):
        self.browser = browser
        # 企业微信管理后台
        self.admin_url = "https://work.weixin.qq.com/wework_admin/loginpage_wx"
        # 企业微信应用管理页面模板
        self.app_management_url = "https://work.weixin.qq.com/wework_admin/frame#apps"
        # 用户提供的配置
        self.corp_id = "ww02c09b741b716c32"
        self.agent_id = "1000002"
        self.secret = "REDACTED_WECOM_SECRET"
        self.webhook = "http://127.0.0.1:18789/wecom/webhook"
        self.token = "6XeXrzS9AbblMaNY3ht8jv"
        self.encoding_aes_key = "pdSSqKddM6cmqL5xjrIfhx8wkgwyignjcfT5OlraXCc"

    def activate_browser(self):
        """激活浏览器"""
        script = f'tell application "{self.browser}" to activate'
        run_applescript(script)
        time.sleep(1)
        return f"{self.browser}已激活"

    def open_admin(self) -> str:
        """打开企业微信管理后台"""
        return self.open_url(self.admin_url)

    def open_url(self, url: str) -> str:
        """在浏览器中打开URL"""
        script = f"""
        tell application "{self.browser}"
            activate
            delay 0.5
            make new document with properties {{URL:"{url}"}}
            delay 2
            set docCount to count of documents
            if docCount > 0 then
                set firstDoc to document 1
                set docTitle to name of firstDoc
                return "打开页面: " & docTitle
            else
                return "页面已打开"
            end if
        end tell
        """
        return run_applescript(script)

    def test_webhook(self) -> Dict[str, Any]:
        """测试企业微信webhook连接"""
        print(f"测试webhook: {self.webhook}")

        results = {"webhook_url": self.webhook, "tests": []}

        # 测试1: GET请求
        try:
            response = requests.get(self.webhook, timeout=5)
            test_result = {
                "name": "GET请求",
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "content_type": response.headers.get("Content-Type", ""),
                "note": "返回404，说明这不是webhook接收端点",
            }
            if response.status_code == 200:
                if "text/html" in response.headers.get("Content-Type", ""):
                    if "OpenClaw" in response.text:
                        test_result["note"] = "这是OpenClaw Control Web界面，不是webhook接收器"
            results["tests"].append(test_result)
        except Exception as e:
            results["tests"].append({"name": "GET请求", "success": False, "error": str(e)})

        # 测试2: POST请求（简单JSON）
        payload = {"msgtype": "text", "text": {"content": "测试消息"}}
        try:
            response = requests.post(self.webhook, json=payload, timeout=5)
            test_result = {
                "name": "POST请求",
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.text[:200] if response.text else "",
            }
            results["tests"].append(test_result)
        except Exception as e:
            results["tests"].append({"name": "POST请求", "success": False, "error": str(e)})

        # 测试3: 带Token的POST请求
        headers = {
            "Content-Type": "application/json",
            "X-WeCom-Token": self.token,
            "X-WeCom-Encoding-AES-Key": self.encoding_aes_key,
        }
        try:
            response = requests.post(self.webhook, json=payload, headers=headers, timeout=5)
            test_result = {
                "name": "带Token的POST请求",
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.text[:200] if response.text else "",
            }
            results["tests"].append(test_result)
        except Exception as e:
            results["tests"].append(
                {"name": "带Token的POST请求", "success": False, "error": str(e)}
            )

        return results

    def test_app_api(self) -> Dict[str, Any]:
        """测试企业微信应用API"""
        print(f"测试应用API，CorpID: {self.corp_id}")

        results = {"corp_id": self.corp_id, "agent_id": self.agent_id, "tests": []}

        # 测试1: 获取Access Token
        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.secret}"
        try:
            response = requests.get(token_url, timeout=10)
            data = response.json()

            test_result = {
                "name": "获取Access Token",
                "status_code": response.status_code,
                "success": data.get("errcode") == 0,
                "errcode": data.get("errcode"),
                "errmsg": data.get("errmsg"),
                "note": "",
            }

            if data.get("errcode") == 0:
                access_token = data.get("access_token")
                test_result["access_token"] = access_token[:20] + "..." if access_token else None
                test_result["expires_in"] = data.get("expires_in")
                results["access_token"] = access_token

                # 测试2: 发送消息
                send_url = (
                    f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
                )
                payload = {
                    "touser": "@all",
                    "msgtype": "text",
                    "agentid": self.agent_id,
                    "text": {"content": "MAREF通知测试消息"},
                    "safe": 0,
                }

                send_response = requests.post(send_url, json=payload, timeout=10)
                send_data = send_response.json()

                send_test = {
                    "name": "发送消息",
                    "status_code": send_response.status_code,
                    "success": send_data.get("errcode") == 0,
                    "errcode": send_data.get("errcode"),
                    "errmsg": send_data.get("errmsg"),
                    "note": "",
                }

                if send_data.get("errcode") == 60020:
                    send_test["note"] = "IP白名单错误：服务器IP不在企业微信应用白名单中"
                    send_test["recommendation"] = "需要在企业微信管理后台添加服务器IP到白名单"

                results["tests"].append(send_test)
            else:
                if data.get("errcode") == 40001:
                    test_result["note"] = "Secret错误或已过期"
                elif data.get("errcode") == 40013:
                    test_result["note"] = "CorpID错误"

            results["tests"].insert(0, test_result)

        except Exception as e:
            results["tests"].append({"name": "获取Access Token", "success": False, "error": str(e)})

        return results

    def get_server_ip(self) -> str:
        """获取当前服务器公网IP"""
        try:
            response = requests.get("https://api.ipify.org?format=json", timeout=5)
            data = response.json()
            return data.get("ip", "未知")
        except Exception as e:
            print(f"获取服务器IP失败: {e}")
            # 备用IP获取方式
            try:
                response = requests.get("https://ifconfig.me/ip", timeout=5)
                return response.text.strip()
            except:
                return "124.240.115.101"  # 使用之前已知的IP

    def diagnose_problems(self) -> Dict[str, Any]:
        """诊断企业微信问题"""
        print("诊断企业微信配置问题...")

        diagnosis = {"problems": [], "solutions": [], "server_ip": self.get_server_ip()}

        # 测试webhook
        webhook_results = self.test_webhook()
        webhook_success = any(test.get("success", False) for test in webhook_results["tests"])

        if not webhook_success:
            diagnosis["problems"].append(
                {
                    "type": "webhook",
                    "description": "Webhook端点不可用（返回404）",
                    "details": "http://127.0.0.1:18789/wecom/webhook 不是有效的webhook接收端点",
                    "severity": "high",
                }
            )
            diagnosis["solutions"].append(
                {
                    "type": "webhook",
                    "description": "寻找正确的webhook端点",
                    "steps": [
                        "1. 检查OpenClaw Control的API文档",
                        "2. 查找正确的webhook接收URL",
                        "3. 更新.env文件中的WECOM_WEBHOOK_URL",
                    ],
                }
            )

        # 测试应用API
        api_results = self.test_app_api()
        api_success = any(test.get("success", False) for test in api_results.get("tests", []))

        if not api_success:
            # 检查具体错误
            for test in api_results.get("tests", []):
                if test.get("errcode") == 60020:
                    diagnosis["problems"].append(
                        {
                            "type": "api_ip_whitelist",
                            "description": "IP白名单限制",
                            "details": f"服务器IP {diagnosis['server_ip']} 不在企业微信应用白名单中",
                            "severity": "high",
                        }
                    )
                    diagnosis["solutions"].append(
                        {
                            "type": "api_ip_whitelist",
                            "description": "添加服务器IP到企业微信应用白名单",
                            "steps": [
                                "1. 登录企业微信管理后台 (https://work.weixin.qq.com)",
                                f"2. 找到应用ID: {self.agent_id}",
                                f"3. 添加IP: {diagnosis['server_ip']} 到白名单",
                                "4. 保存配置并等待生效（可能需要几分钟）",
                            ],
                            "cli_anything_option": "使用浏览器自动化添加IP白名单",
                        }
                    )
                elif test.get("errcode") in [40001, 40013]:
                    diagnosis["problems"].append(
                        {
                            "type": "api_credentials",
                            "description": "API凭据错误",
                            "details": f"错误代码: {test.get('errcode')}, 消息: {test.get('errmsg')}",
                            "severity": "critical",
                        }
                    )
                    diagnosis["solutions"].append(
                        {
                            "type": "api_credentials",
                            "description": "验证和更新企业微信凭据",
                            "steps": [
                                "1. 登录企业微信管理后台",
                                "2. 检查CorpID、AgentId、Secret是否正确",
                                "3. 如有必要，重新生成Secret",
                                "4. 更新.env文件中的凭据",
                            ],
                        }
                    )

        # 如果两个渠道都失败
        if not webhook_success and not api_success:
            diagnosis["solutions"].append(
                {
                    "type": "alternative",
                    "description": "使用替代方案：企业微信机器人webhook",
                    "steps": [
                        "1. 在企业微信群聊中添加机器人",
                        "2. 获取机器人webhook URL",
                        "3. 更新通知器配置使用机器人webhook",
                        "4. 测试消息发送",
                    ],
                    "note": "此方案不受IP白名单限制，但只能发送到特定群聊",
                }
            )

        return diagnosis

    def create_cli_anything_guide(self) -> str:
        """创建CLI-Anything解决方案指南"""
        guide = """# 企业微信CLI-Anything解决方案指南

## 当前问题分析
1. **Webhook端点错误**: 配置的webhook返回404，不是有效的接收端点
2. **API IP白名单限制**: 服务器IP不在企业微信应用白名单中 (errcode: 60020)

## CLI-Anything自动化方案

### 方案A: 浏览器自动化添加IP白名单
**目标**: 自动登录企业微信管理后台，添加服务器IP到应用白名单

**实现步骤**:
1. 使用AppleScript控制Safari/Chrome打开企业微信管理后台
2. 自动填充登录凭据（如果保存了cookie或可提供）
3. 导航到应用管理页面
4. 找到目标应用，进入白名单设置
5. 添加服务器IP到白名单
6. 保存配置

**技术挑战**:
- 需要处理登录验证（可能需二维码扫描）
- 页面元素定位可能变化
- 需要启用JavaScript执行权限

### 方案B: 模拟webhook接收器
**目标**: 创建一个本地的webhook接收器，模拟OpenClaw Control的接口

**实现步骤**:
1. 创建一个简单的HTTP服务器监听 `http://127.0.0.1:18789/wecom/webhook`
2. 接收企业微信格式的消息
3. 将消息转发到真正的企业微信API（使用应用API方式）
4. 或者将消息显示在控制台/日志中

**优点**:
- 无需修改现有配置
- 可以绕过IP白名单限制（通过API转发）
- 实现相对简单

### 方案C: 企业微信机器人webhook自动化
**目标**: 自动化创建企业微信机器人并获取webhook URL

**实现步骤**:
1. 通过浏览器自动化创建企业微信群聊（如需要）
2. 添加机器人到群聊
3. 获取机器人webhook URL
4. 更新系统配置使用新的webhook

## 推荐实施顺序

### 短期方案（立即实施）
1. **实施方案B**: 创建webhook转发器
   - 优点: 快速，不依赖外部服务
   - 缺点: 需要额外的转发层

2. **准备方案A**: 开发IP白名单自动化脚本
   - 先手动添加IP白名单
   - 同时开发自动化脚本供未来使用

### 长期方案
1. **完善方案A**: 完整的浏览器自动化
2. **开发方案C**: 机器人webhook自动化

## 技术实现要点

### AppleScript基础
```applescript
-- 打开Safari并导航到企业微信
tell application "Safari"
    activate
    make new document with properties {URL:"https://work.weixin.qq.com"}
    delay 2
end tell
```

### JavaScript执行
需要在Safari中启用: 偏好设置 > 高级 > 允许JavaScript来自Apple事件

### 页面元素定位
使用JavaScript查询DOM元素:
```javascript
// 查找登录按钮
document.querySelector('button.login-btn')
```

## 风险与注意事项
1. **安全风险**: 自动化脚本可能泄露企业微信凭据
2. **稳定性**: 网页结构变化可能导致脚本失效
3. **维护成本**: 需要定期更新自动化脚本
4. **权限需求**: 需要系统自动化权限

## 下一步行动
1. 评估各方案的技术可行性
2. 选择优先实施方案
3. 开发原型验证概念
4. 集成到MAREF通知系统
"""
        return guide


@click.group()
def cli():
    """企业微信CLI控制工具"""
    pass


@cli.command()
def test_webhook():
    """测试企业微信webhook连接"""
    wecom = WeComCLI()
    results = wecom.test_webhook()

    click.echo("=== Webhook测试结果 ===")
    for test in results["tests"]:
        emoji = "✅" if test.get("success") else "❌"
        click.echo(f"{emoji} {test['name']}: 状态码 {test.get('status_code', 'N/A')}")
        if test.get("note"):
            click.echo(f"   备注: {test['note']}")
        if test.get("error"):
            click.echo(f"   错误: {test['error']}")


@cli.command()
def test_api():
    """测试企业微信应用API"""
    wecom = WeComCLI()
    results = wecom.test_app_api()

    click.echo("=== 应用API测试结果 ===")
    click.echo(f"CorpID: {results['corp_id']}")
    click.echo(f"AgentId: {results['agent_id']}")

    for test in results["tests"]:
        emoji = "✅" if test.get("success") else "❌"
        click.echo(f"\n{emoji} {test['name']}:")
        click.echo(f"   状态码: {test.get('status_code', 'N/A')}")
        click.echo(f"   错误码: {test.get('errcode', 'N/A')}")
        click.echo(f"   错误消息: {test.get('errmsg', 'N/A')}")
        if test.get("note"):
            click.echo(f"   备注: {test['note']}")
        if test.get("recommendation"):
            click.echo(f"   建议: {test['recommendation']}")


@cli.command()
def diagnose():
    """诊断企业微信问题"""
    wecom = WeComCLI()
    diagnosis = wecom.diagnose_problems()

    click.echo("=== 企业微信问题诊断 ===")
    click.echo(f"服务器IP: {diagnosis['server_ip']}")

    click.echo("\n❌ 发现问题:")
    for problem in diagnosis["problems"]:
        click.echo(f"\n{problem['type'].upper()}: {problem['description']}")
        click.echo(f"   详情: {problem['details']}")
        click.echo(f"   严重性: {problem['severity']}")

    click.echo("\n💡 解决方案:")
    for solution in diagnosis["solutions"]:
        click.echo(f"\n{solution['type'].upper()}: {solution['description']}")
        for i, step in enumerate(solution["steps"], 1):
            click.echo(f"   {i}. {step}")
        if solution.get("cli_anything_option"):
            click.echo(f"   CLI-Anything选项: {solution['cli_anything_option']}")


@cli.command()
def cli_anything_guide():
    """显示CLI-Anything解决方案指南"""
    wecom = WeComCLI()
    guide = wecom.create_cli_anything_guide()
    click.echo(guide)


@cli.command()
def open_admin():
    """打开企业微信管理后台"""
    wecom = WeComCLI()
    result = wecom.open_admin()
    click.echo(result)


@cli.command()
def server_ip():
    """获取服务器公网IP"""
    wecom = WeComCLI()
    ip = wecom.get_server_ip()
    click.echo(f"服务器公网IP: {ip}")
    click.echo(f"需要将此IP添加到企业微信应用白名单")


if __name__ == "__main__":
    cli()
