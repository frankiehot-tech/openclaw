#!/usr/bin/env python3
"""
企业微信机器人创建CLI工具
基于CLI-Anything方法，通过浏览器自动化创建企业微信机器人并获取webhook URL
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click


def run_applescript(script: str, timeout: int = 30) -> str:
    """运行AppleScript并返回结果"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            raise RuntimeError(f"AppleScript错误: {result.stderr}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError("AppleScript执行超时")
    except Exception as e:
        raise RuntimeError(f"AppleScript执行失败: {e}")


def escape_for_applescript(text: str) -> str:
    """转义字符串用于AppleScript"""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return escaped


class WeComRobotCreator:
    """企业微信机器人创建器（使用Safari）"""

    def __init__(self, browser: str = "Safari"):
        """初始化企业微信机器人创建器"""
        self.browser = browser
        self.project_dir = Path(__file__).parent
        self.env_file = self.project_dir / ".env"

        # 企业微信相关URL
        self.work_weixin_url = "https://work.weixin.qq.com"
        self.robot_management_url = "https://work.weixin.qq.com/wework_admin/robot/manage"
        self.group_creation_url = (
            "https://work.weixin.qq.com/wework_admin/frame#contacts/department/action/addChat"
        )

    def activate_browser(self) -> str:
        """激活浏览器"""
        script = f'tell application "{self.browser}" to activate'
        run_applescript(script)
        time.sleep(1)
        return f"{self.browser}已激活"

    def open_url(self, url: str) -> str:
        """在浏览器中打开URL"""
        script = f"""
        tell application "{self.browser}"
            activate
            delay 0.5
            make new document with properties {{URL:"{url}"}}
            delay 3
            return "已打开URL: {url}"
        end tell
        """
        return run_applescript(script)

    def open_work_weixin(self) -> str:
        """打开企业微信管理后台"""
        return self.open_url(self.work_weixin_url)

    def open_robot_management(self) -> str:
        """打开机器人管理页面"""
        return self.open_url(self.robot_management_url)

    def open_group_creation(self) -> str:
        """打开群聊创建页面"""
        return self.open_url(self.group_creation_url)

    def get_current_url(self) -> str:
        """获取当前页面URL"""
        script = f"""
        tell application "{self.browser}"
            if (count of windows) > 0 then
                set targetWindow to window 1
                if (count of tabs of targetWindow) > 0 then
                    set targetTab to tab 1 of targetWindow
                    return URL of targetTab
                end if
            end if
            return "无法获取URL"
        end tell
        """
        return run_applescript(script)

    def get_page_title(self) -> str:
        """获取当前页面标题"""
        script = f"""
        tell application "{self.browser}"
            if (count of windows) > 0 then
                set targetWindow to window 1
                if (count of tabs of targetWindow) > 0 then
                    set targetTab to tab 1 of targetWindow
                    return name of targetTab
                end if
            end if
            return "无法获取标题"
        end tell
        """
        return run_applescript(script)

    def execute_javascript(self, js_code: str, window_idx: int = 1, tab_idx: int = 1) -> str:
        """在指定标签页执行JavaScript"""
        escaped_js = escape_for_applescript(js_code)

        script = f"""
        tell application "{self.browser}"
            set targetWindow to window {window_idx}
            set targetTab to tab {tab_idx} of targetWindow

            try
                set result to do JavaScript "{escaped_js}" in targetTab
                return "JavaScript执行成功: " & result
            on error errMsg
                return "JavaScript执行错误: " & errMsg
            end try
        end tell
        """
        return run_applescript(script)

    def check_login_status(self) -> Dict[str, Any]:
        """检查企业微信登录状态"""
        # 尝试通过页面标题和URL判断登录状态
        current_url = self.get_current_url()
        page_title = self.get_page_title()

        result = {
            "logged_in": False,
            "current_url": current_url,
            "page_title": page_title,
            "details": {},
        }

        # 判断登录状态的启发式规则
        if "loginpage" in current_url.lower():
            result["logged_in"] = False
            result["details"]["reason"] = "在登录页面"
        elif "wework_admin" in current_url.lower():
            result["logged_in"] = True
            result["details"]["reason"] = "在管理后台页面"
        elif "验证" in page_title or "登录" in page_title:
            result["logged_in"] = False
            result["details"]["reason"] = "页面标题显示需要验证"
        else:
            result["logged_in"] = True
            result["details"]["reason"] = "可能已登录"

        return result

    def create_interactive_guide(self) -> str:
        """创建交互式机器人创建指南"""
        guide = """# 企业微信机器人创建指南

## 步骤1: 登录企业微信
1. 浏览器已打开企业微信管理后台
2. 使用企业微信APP扫码登录
3. 登录后请返回此窗口继续

## 步骤2: 创建群聊（可选）
如果已有群聊可跳过此步骤：
1. 在左侧菜单选择"客户联系" → "群聊"
2. 点击"创建群聊"
3. 选择成员，创建群聊
4. 记录群聊名称

## 步骤3: 添加机器人
1. 在群聊设置中找到"群机器人"
2. 点击"添加机器人"
3. 设置机器人名称（如: MAREF通知机器人）
4. 点击"添加"

## 步骤4: 获取webhook URL
1. 添加成功后，复制webhook URL
2. URL格式: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
3. 将此URL保存到安全的地方

## 步骤5: 测试机器人
1. 使用webhook URL发送测试消息
2. 确认机器人能正常接收和发送消息

## 注意事项
- webhook URL包含敏感密钥，请妥善保管
- 机器人只能发送到其所在的群聊
- 建议为不同用途创建不同的机器人
- 定期检查机器人权限和安全设置
"""
        return guide

    def display_guide_interactively(self) -> str:
        """显示交互式指南并等待用户操作"""
        guide = self.create_interactive_guide()

        # 先显示指南
        print(guide)

        # 打开企业微信管理后台
        print("正在打开企业微信管理后台...")
        self.open_work_weixin()
        time.sleep(3)

        # 检查登录状态
        login_status = self.check_login_status()
        print(f"当前登录状态: {'已登录' if login_status['logged_in'] else '未登录'}")
        print(f"当前页面: {login_status['current_url']}")

        # 提供交互式选项
        script = """
        display dialog "请按以下步骤操作：\\n\\n1. 扫码登录企业微信\\n2. 创建群聊或选择现有群聊\\n3. 添加机器人并获取webhook URL\\n\\n完成后点击'我已获取webhook URL'" with title "企业微信机器人创建指南" buttons {"我已获取webhook URL", "取消"} default button 1
        """

        try:
            result = run_applescript(script, timeout=300)  # 5分钟超时
            if "button returned:我已获取webhook URL" in result:
                return "用户确认已获取webhook URL"
            else:
                return "用户取消操作"
        except Exception as e:
            return f"对话框交互失败: {e}"

    def get_webhook_via_dialog(self) -> str:
        """通过对话框获取用户输入的webhook URL"""
        script = """
        display dialog "请输入您获取的企业微信机器人webhook URL：" default answer "" with title "输入webhook URL" buttons {"确定", "取消"} default button 1
        """

        try:
            result = run_applescript(script)
            # 解析AppleScript返回结果
            if "button returned:确定" in result and "text returned:" in result:
                import re

                match = re.search(r"text returned:(.+)", result)
                if match:
                    webhook_url = match.group(1).strip()
                    # 验证webhook URL格式
                    if self.validate_webhook_url(webhook_url):
                        return webhook_url
                    else:
                        raise ValueError(f"webhook URL格式不正确: {webhook_url}")
        except Exception as e:
            print(f"对话框输入失败: {e}")

        return None

    def validate_webhook_url(self, url: str) -> bool:
        """验证webhook URL格式"""
        # 企业微信机器人webhook URL格式
        patterns = [
            r"https://qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=[a-zA-Z0-9\-]+",
            r"https://qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=",
        ]

        for pattern in patterns:
            if re.match(pattern, url):
                return True

        return False

    def update_env_file(self, webhook_url: str) -> bool:
        """更新.env文件中的企业微信webhook配置"""
        if not self.env_file.exists():
            print(f"错误: 找不到.env文件: {self.env_file}")
            return False

        # 读取整个文件
        with open(self.env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 查找并更新WECOM_WEBHOOK_URL行
        updated = False
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("WECOM_WEBHOOK_URL="):
                # 保持原有格式（引号等）
                if '"' in line:
                    new_line = f'WECOM_WEBHOOK_URL="{webhook_url}"\n'
                elif "'" in line:
                    new_line = f"WECOM_WEBHOOK_URL='{webhook_url}'\n"
                else:
                    new_line = f"WECOM_WEBHOOK_URL={webhook_url}\n"
                new_lines.append(new_line)
                updated = True
            else:
                new_lines.append(line)

        # 如果没找到，添加到文件末尾
        if not updated:
            new_lines.append(f'\n# 更新于 {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
            new_lines.append(f"WECOM_WEBHOOK_URL={webhook_url}\n")

        # 写入文件
        with open(self.env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return True

    def test_webhook_connection(self, webhook_url: str) -> Dict[str, Any]:
        """测试webhook连接"""
        import requests

        results = {"webhook_url": webhook_url, "tests": []}

        # 测试1: GET请求（企业微信webhook只接受POST）
        try:
            response = requests.get(webhook_url, timeout=5)
            test_result = {
                "name": "GET请求",
                "status_code": response.status_code,
                "success": response.status_code == 405,  # 应该返回405 Method Not Allowed
                "note": "GET请求应返回405，表示只接受POST",
            }
            results["tests"].append(test_result)
        except Exception as e:
            results["tests"].append({"name": "GET请求", "success": False, "error": str(e)})

        # 测试2: POST请求（简单文本消息）
        payload = {"msgtype": "text", "text": {"content": "MAREF通知系统测试消息"}}

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            test_result = {
                "name": "POST请求",
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.text[:200] if response.text else "",
            }

            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("errcode") == 0:
                        test_result["note"] = "webhook连接成功，消息发送成功"
                    else:
                        test_result["note"] = (
                            f"webhook连接成功，但消息发送失败: {data.get('errmsg')}"
                        )
                except:
                    test_result["note"] = "webhook连接成功"
            else:
                test_result["note"] = f"webhook连接失败，状态码: {response.status_code}"

            results["tests"].append(test_result)

        except Exception as e:
            results["tests"].append({"name": "POST请求", "success": False, "error": str(e)})

        return results

    def create_robot_interactively(self) -> Dict[str, Any]:
        """交互式创建企业微信机器人"""
        results = {"success": False, "webhook_url": None, "steps": []}

        print("=== 企业微信机器人交互式创建 ===")

        # 步骤1: 显示指南并打开企业微信
        print("\n1. 显示创建指南并打开企业微信...")
        guide_result = self.display_guide_interactively()
        results["steps"].append({"name": "显示指南", "result": guide_result})

        if "用户取消操作" in guide_result:
            print("❌ 用户取消操作")
            return results

        # 步骤2: 获取webhook URL
        print("\n2. 获取webhook URL...")
        webhook_url = self.get_webhook_via_dialog()

        if not webhook_url:
            print("❌ 未获取到有效的webhook URL")
            results["steps"].append({"name": "获取webhook URL", "result": "失败"})
            return results

        print(f"✅ 获取到webhook URL: {webhook_url}")
        results["steps"].append({"name": "获取webhook URL", "result": "成功", "url": webhook_url})

        # 步骤3: 验证webhook URL格式
        print("\n3. 验证webhook URL格式...")
        if self.validate_webhook_url(webhook_url):
            print("✅ webhook URL格式正确")
            results["steps"].append({"name": "验证格式", "result": "成功"})
        else:
            print(f"⚠️  webhook URL格式可能不正确: {webhook_url}")
            results["steps"].append(
                {"name": "验证格式", "result": "警告", "note": "格式可能不正确"}
            )

        # 步骤4: 更新配置文件
        print("\n4. 更新.env配置文件...")
        if self.update_env_file(webhook_url):
            print("✅ 配置文件更新成功")
            results["steps"].append({"name": "更新配置", "result": "成功"})
        else:
            print("❌ 配置文件更新失败")
            results["steps"].append({"name": "更新配置", "result": "失败"})
            return results

        # 步骤5: 测试webhook连接
        print("\n5. 测试webhook连接...")
        test_results = self.test_webhook_connection(webhook_url)

        success_tests = [t for t in test_results["tests"] if t.get("success", False)]
        if len(success_tests) > 0:
            print("✅ webhook连接测试通过")
            results["steps"].append({"name": "连接测试", "result": "成功"})
            results["success"] = True
            results["webhook_url"] = webhook_url
        else:
            print("⚠️  webhook连接测试失败，但配置已更新")
            results["steps"].append({"name": "连接测试", "result": "失败"})
            results["success"] = True  # 配置已更新，可后续测试
            results["webhook_url"] = webhook_url

        return results


@click.group()
def cli():
    """企业微信机器人创建CLI工具"""
    pass


@cli.command()
def guide():
    """显示企业微信机器人创建指南"""
    creator = WeComRobotCreator()
    guide_text = creator.create_interactive_guide()
    click.echo(guide_text)


@cli.command()
def open_wecom():
    """打开企业微信管理后台"""
    creator = WeComRobotCreator()
    result = creator.open_work_weixin()
    click.echo(result)


@cli.command()
def check_login():
    """检查企业微信登录状态"""
    creator = WeComRobotCreator()
    login_status = creator.check_login_status()

    click.echo("=== 企业微信登录状态检查 ===")
    click.echo(f"当前页面URL: {login_status['current_url']}")
    click.echo(f"当前页面标题: {login_status['page_title']}")
    click.echo(f"登录状态: {'✅ 已登录' if login_status['logged_in'] else '❌ 未登录'}")
    click.echo(f"判断依据: {login_status['details'].get('reason', '未知')}")


@cli.command()
def interactive():
    """交互式创建企业微信机器人"""
    creator = WeComRobotCreator()
    results = creator.create_robot_interactively()

    click.echo("\n=== 创建结果汇总 ===")
    for step in results["steps"]:
        emoji = "✅" if step["result"] == "成功" else "❌" if step["result"] == "失败" else "⚠️"
        click.echo(f"{emoji} {step['name']}: {step['result']}")

    if results.get("success"):
        click.echo(f"\n🎉 企业微信机器人创建完成！")
        click.echo(f"webhook URL: {results['webhook_url']}")
        click.echo(f"配置文件已更新: {creator.env_file}")
        click.echo("\n下一步: 运行完整通知测试验证配置")
        click.echo("命令: python3 test_notification_channels_final.py")
    else:
        click.echo(f"\n❌ 企业微信机器人创建失败")
        click.echo("请检查网络连接或手动配置webhook URL")


@cli.command()
@click.option("--webhook-url", prompt=True, help="企业微信机器人webhook URL")
def update(webhook_url):
    """更新企业微信机器人webhook配置"""
    creator = WeComRobotCreator()

    # 验证URL格式
    if not creator.validate_webhook_url(webhook_url):
        click.echo(f"❌ webhook URL格式不正确: {webhook_url}")
        click.echo(
            "正确格式: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        )
        return

    # 备份原文件
    import shutil

    backup_file = creator.env_file.with_suffix(".env.backup_robot")
    shutil.copy2(creator.env_file, backup_file)
    click.echo(f"✅ 已备份原文件到: {backup_file}")

    # 更新文件
    if creator.update_env_file(webhook_url):
        click.echo(f"✅ 已更新.env文件中的WECOM_WEBHOOK_URL")

        # 测试连接
        click.echo("\n=== 测试webhook连接 ===")
        test_results = creator.test_webhook_connection(webhook_url)

        for test in test_results["tests"]:
            emoji = "✅" if test.get("success") else "❌"
            click.echo(f"{emoji} {test['name']}: 状态码 {test.get('status_code', 'N/A')}")
            if test.get("note"):
                click.echo(f"   备注: {test['note']}")

        success_tests = [t for t in test_results["tests"] if t.get("success", False)]
        if len(success_tests) > 0:
            click.echo("\n🎉 webhook配置更新成功！")
        else:
            click.echo("\n⚠️  webhook配置已更新，但连接测试失败")
            click.echo("   请检查webhook URL是否正确，或稍后重试")
    else:
        click.echo("❌ 更新.env文件失败")


@cli.command()
def test():
    """测试企业微信机器人CLI功能"""
    click.echo("=== 企业微信机器人CLI功能测试 ===")

    creator = WeComRobotCreator()

    # 测试1: 激活浏览器
    click.echo("\n1. 测试激活浏览器...")
    try:
        result = creator.activate_browser()
        click.echo(f"✅ {result}")
    except Exception as e:
        click.echo(f"❌ 激活浏览器失败: {e}")

    # 测试2: 获取页面信息
    click.echo("\n2. 测试获取页面信息...")
    try:
        url = creator.get_current_url()
        title = creator.get_page_title()
        click.echo(f"✅ 当前URL: {url}")
        click.echo(f"✅ 当前标题: {title}")
    except Exception as e:
        click.echo(f"❌ 获取页面信息失败: {e}")

    # 测试3: 检查登录状态
    click.echo("\n3. 测试检查登录状态...")
    try:
        login_status = creator.check_login_status()
        click.echo(f"✅ 登录状态检查完成: {login_status['logged_in']}")
    except Exception as e:
        click.echo(f"❌ 检查登录状态失败: {e}")

    click.echo("\n=== 测试完成 ===")
    click.echo("\n下一步:")
    click.echo("1. 运行 'python3 wecom_robot_creator.py interactive' 创建机器人")
    click.echo(
        "2. 或运行 'python3 wecom_robot_creator.py update --webhook-url YOUR_URL' 直接更新配置"
    )


if __name__ == "__main__":
    cli()
