#!/usr/bin/env python3
"""
QQ邮箱CLI原型
基于AppleScript的CLI-Anything包装器，用于QQ邮箱网页自动化
"""

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

import click


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
    # 转义反斜杠、双引号和换行符
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return escaped


class QQMailCLI:
    """QQ邮箱CLI控制器（使用Safari）"""

    def __init__(self, browser: str = "Safari"):
        """初始化QQ邮箱CLI控制器"""
        self.browser = browser
        self.mail_url = "https://mail.qq.com"
        self.settings_url = "https://mail.qq.com/cgi-bin/frame_html?sid=U9iL3otg8RapmhE3&r=ab70311d9ea3d9a2c4a2d4245e7eeb54"

    def activate(self):
        """激活浏览器"""
        script = f'tell application "{self.browser}" to activate'
        run_applescript(script)
        time.sleep(1)
        return f"{self.browser}已激活"

    def open_mail(self) -> str:
        """打开QQ邮箱主页"""
        return self.open_url(self.mail_url)

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

    def get_tabs_info(self) -> List[Dict[str, str]]:
        """获取所有标签页信息"""
        script = f"""
        tell application "{self.browser}"
            set windowList to windows
            set resultText to ""

            repeat with win in windowList
                set tabList to tabs of win
                set winIndex to index of win as text

                repeat with t in tabList
                    set tabURL to URL of t
                    set tabName to name of t
                    set resultText to resultText & "Window:" & winIndex & "|Title:" & tabName & "|URL:" & tabURL & "\\n"
                end repeat
            end repeat

            return resultText
        end tell
        """

        result = run_applescript(script).strip()

        # 解析格式化的文本
        tabs = []
        lines = result.split("\n")
        for line in lines:
            if line.strip():
                parts = line.strip().split("|")
                tab_info = {}
                for part in parts:
                    if ":" in part:
                        key, value = part.split(":", 1)
                        tab_info[key.strip()] = value.strip()
                if tab_info:
                    tabs.append(tab_info)

        return tabs if tabs else [{"raw_output": result}]

    def execute_javascript(
        self, window_idx: int = 1, tab_idx: int = 1, js_code: str = "document.title"
    ) -> str:
        """
        在指定标签页执行JavaScript

        注意：需要在Safari中启用"允许JavaScript来自Apple事件"
        路径：Safari > 偏好设置 > 高级 > 勾选"允许JavaScript来自Apple事件"
        """
        # 转义JavaScript代码以用于AppleScript
        escaped_js = escape_for_applescript(js_code)

        script = f"""
        tell application "{self.browser}"
            set targetWindow to window {window_idx}
            set targetTab to tab {tab_idx} of targetWindow

            try
                set result to do JavaScript "{escaped_js}" in targetTab
                return "JavaScript执行结果: " & result
            on error errMsg
                return "JavaScript执行错误: " & errMsg
            end try
        end tell
        """
        return run_applescript(script)

    def check_login_status(self) -> str:
        """检查是否已登录QQ邮箱"""
        # 简单的JavaScript检查页面标题或元素
        js_code = """
        var title = document.title;
        var bodyText = document.body.innerText;
        var loggedIn = title.includes('QQ邮箱') && !bodyText.includes('登录');
        return '已登录: ' + loggedIn + ', 标题: ' + title;
        """

        try:
            result = self.execute_javascript(1, 1, js_code)
            return result
        except Exception as e:
            return f"登录状态检查失败: {e}"

    def navigate_to_smtp_settings(self) -> str:
        """导航到SMTP/POP3设置页面获取授权码"""
        # 尝试直接打开已知的授权码生成页面
        auth_url = "https://mail.qq.com/cgi-bin/loginpage?t=account_security&sub=smtp_pop3"
        return self.open_url(auth_url)

    def get_page_title(self) -> str:
        """获取当前页面标题"""
        return self.execute_javascript(1, 1, "document.title")

    def get_current_url(self) -> str:
        """获取当前页面URL"""
        return self.execute_javascript(1, 1, "window.location.href")

    def close_browser(self):
        """关闭浏览器"""
        script = f'tell application "{self.browser}" to quit'
        run_applescript(script)
        return f"{self.browser}已关闭"


@click.group()
def cli():
    """QQ邮箱CLI控制工具"""
    pass


@cli.command()
def open_mail():
    """打开QQ邮箱"""
    qqmail = QQMailCLI()
    result = qqmail.open_mail()
    click.echo(result)


@cli.command()
@click.argument("url")
def open_url(url):
    """在Safari中打开URL"""
    qqmail = QQMailCLI()
    result = qqmail.open_url(url)
    click.echo(result)


@cli.command()
def tabs():
    """显示所有打开的标签页"""
    qqmail = QQMailCLI()
    tabs_info = qqmail.get_tabs_info()

    if tabs_info and "raw_output" in tabs_info[0]:
        click.echo("标签页信息:")
        click.echo(tabs_info[0]["raw_output"])
    else:
        click.echo("当前打开的标签页:")
        for i, tab in enumerate(tabs_info, 1):
            window = tab.get("Window", tab.get("window", "?"))
            title = tab.get("Title", tab.get("title", tab.get("name", "无标题")))
            url = tab.get("URL", tab.get("url", "无URL"))
            click.echo(f"{i}. 窗口{window}: {title}")
            click.echo(f"   URL: {url}")
            click.echo()


@cli.command()
@click.option("--window", default=1, help="窗口索引（从1开始）")
@click.option("--tab", default=1, help="标签页索引（从1开始）")
@click.argument("js_code")
def execute_js(window, tab, js_code):
    """在指定标签页执行JavaScript"""
    qqmail = QQMailCLI()
    result = qqmail.execute_javascript(window, tab, js_code)
    click.echo(result)


@cli.command()
def check_login():
    """检查QQ邮箱登录状态"""
    qqmail = QQMailCLI()
    result = qqmail.check_login_status()
    click.echo(result)


@cli.command()
def smtp_settings():
    """导航到SMTP/POP3设置页面"""
    qqmail = QQMailCLI()
    result = qqmail.navigate_to_smtp_settings()
    click.echo(result)


@cli.command()
def current_title():
    """获取当前页面标题"""
    qqmail = QQMailCLI()
    result = qqmail.get_page_title()
    click.echo(result)


@cli.command()
def current_url():
    """获取当前页面URL"""
    qqmail = QQMailCLI()
    result = qqmail.get_current_url()
    click.echo(result)


@cli.command()
def test():
    """运行QQ邮箱CLI功能测试"""
    click.echo("=== QQ邮箱CLI功能测试 ===")

    qqmail = QQMailCLI()

    # 测试1: 打开QQ邮箱
    click.echo("\n1. 测试打开QQ邮箱...")
    try:
        result = qqmail.open_mail()
        click.echo(f"✅ {result}")
        time.sleep(3)  # 等待页面加载
    except Exception as e:
        click.echo(f"❌ 打开QQ邮箱失败: {e}")

    # 测试2: 获取标签页信息
    click.echo("\n2. 测试获取标签页信息...")
    try:
        tabs_info = qqmail.get_tabs_info()
        click.echo(f"✅ 获取到 {len(tabs_info)} 个标签页信息")
        if tabs_info and len(tabs_info) > 0:
            click.echo(f"   第一个标签页标题: {tabs_info[0].get('Title', '未知')}")
    except Exception as e:
        click.echo(f"❌ 获取标签页信息失败: {e}")

    # 测试3: 获取页面标题
    click.echo("\n3. 测试获取页面标题...")
    try:
        title_result = qqmail.get_page_title()
        if "JavaScript执行错误" in title_result:
            click.echo(f"⚠️  {title_result}")
            click.echo("   提示：需要在Safari中启用'允许JavaScript来自Apple事件'")
            click.echo("   路径：Safari > 偏好设置 > 高级 > 勾选'允许JavaScript来自Apple事件'")
        else:
            click.echo(f"✅ {title_result}")
    except Exception as e:
        click.echo(f"❌ 获取页面标题失败: {e}")

    # 测试4: 检查登录状态
    click.echo("\n4. 测试检查登录状态...")
    try:
        login_status = qqmail.check_login_status()
        click.echo(f"✅ {login_status}")
    except Exception as e:
        click.echo(f"❌ 检查登录状态失败: {e}")

    click.echo("\n=== 测试完成 ===")
    click.echo("\n下一步:")
    click.echo("1. 在Safari中启用JavaScript执行权限")
    click.echo("2. 手动登录QQ邮箱（如果未登录）")
    click.echo("3. 运行 'python3 qqmail_cli_prototype.py smtp-settings' 导航到授权码设置")


if __name__ == "__main__":
    cli()
