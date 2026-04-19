#!/usr/bin/env python3
"""
企业微信AI代理 - 全自动化管理方案
无需用户GUI操作，AI直接管理企业微信机器人配置
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
import requests


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


class WeComAIAgent:
    """企业微信AI代理 - 全自动化管理器"""

    def __init__(self):
        self.browser = "Safari"
        self.project_dir = Path(__file__).parent
        self.env_file = self.project_dir / ".env"

        # 企业微信配置
        self.corp_id = "ww02c09b741b716c32"
        self.agent_id = "1000002"
        self.secret = "REDACTED_WECOM_SECRET"
        self.current_webhook = "http://127.0.0.1:18789/wecom/webhook"

        # 目标页面URLs
        self.work_weixin_url = "https://work.weixin.qq.com"
        self.work_weixin_admin_url = "https://work.weixin.qq.com/wework_admin/frame"
        self.user_provided_url = (
            "https://work.weixin.qq.com/wework_admin/frame#/business/mall/index/apply"
        )
        self.robot_management_url = "https://work.weixin.qq.com/wework_admin/robot/manage"
        self.customer_groups_url = "https://work.weixin.qq.com/wework_admin/frame#/customer/group"
        self.app_management_url = "https://work.weixin.qq.com/wework_admin/frame#/app/manage"
        self.create_group_url = (
            "https://work.weixin.qq.com/wework_admin/frame#contacts/department/action/addChat"
        )

    def check_safari_javascript_permission(self) -> bool:
        """检查Safari JavaScript权限是否启用"""
        test_script = """
        tell application "Safari"
            try
                set result to do JavaScript "document.title" in tab 1 of window 1
                return "SUCCESS:" & result
            on error errMsg
                return "ERROR:" & errMsg
            end try
        end tell
        """

        try:
            result = run_applescript(test_script, timeout=10)
            # 更灵活的错误信息匹配
            if "ERROR:" in result and "Allow JavaScript from Apple Events" in result:
                return False
            return True
        except:
            return False

    def activate_browser(self) -> str:
        """激活浏览器"""
        script = f'tell application "{self.browser}" to activate'
        run_applescript(script)
        time.sleep(1)
        return f"{self.browser}已激活"

    def find_wecom_tab(self) -> Tuple[bool, str]:
        """在所有标签页中查找企业微信页面"""
        script = """
        tell application "Safari"
            set wecomTabs to {}
            repeat with w in windows
                repeat with t in tabs of w
                    if "work.weixin.qq.com" is in URL of t then
                        set end of wecomTabs to {window:w, tab:t, url:URL of t}
                    end if
                end repeat
            end repeat

            if length of wecomTabs > 0 then
                set firstTab to item 1 of wecomTabs
                set index of window of firstTab to 1
                set current tab of window of firstTab to tab of firstTab
                return "FOUND:" & URL of tab of firstTab
            else
                return "NOT_FOUND"
            end if
        end tell
        """

        try:
            result = run_applescript(script, timeout=15)
            if result.startswith("FOUND:"):
                url = result[6:]
                return True, url
            return False, "未找到企业微信标签页"
        except Exception as e:
            return False, f"查找失败: {e}"

    def navigate_to_wecom(self) -> str:
        """导航到企业微信管理后台"""
        # 直接使用用户提供的URL（用户已登录）
        script = f"""
        tell application "{self.browser}"
            activate
            delay 1
            make new document with properties {{URL:"{self.user_provided_url}"}}
            delay 3
            return "已打开企业微信管理后台"
        end tell
        """

        return run_applescript(script)

    def execute_javascript(self, js_code: str, tab_idx: int = 1, window_idx: int = 1) -> str:
        """在指定标签页执行JavaScript"""
        escaped_js = escape_for_applescript(js_code)

        script = f"""
        tell application "{self.browser}"
            set targetWindow to window {window_idx}
            set targetTab to tab {tab_idx} of targetWindow

            try
                set result to do JavaScript "{escaped_js}" in targetTab
                return "SUCCESS:" & result
            on error errMsg
                return "ERROR:" & errMsg
            end try
        end tell
        """

        return run_applescript(script)

    def scan_for_webhook_url(self) -> Dict[str, Any]:
        """扫描页面查找webhook URL"""
        results = {"found": False, "webhook_url": None, "method": None, "details": {}}

        # JavaScript代码：查找webhook URL
        find_webhook_js = """
        (function() {
            // 查找包含webhook URL的元素
            const webhookPattern = /https:\\/\\/qyapi\\.weixin\\.qq\\.com\\/cgi-bin\\/webhook\\/send\\?key=[a-zA-Z0-9\\-]+/;

            // 方法1：查找所有文本内容
            const allElements = document.querySelectorAll('*');
            for (let el of allElements) {
                if (el.textContent && webhookPattern.test(el.textContent)) {
                    const match = el.textContent.match(webhookPattern);
                    if (match) {
                        return JSON.stringify({method: "text_content", url: match[0], element: el.tagName});
                    }
                }
            }

            // 方法2：查找输入框的值
            const inputs = document.querySelectorAll('input[type="text"], input[type="url"], textarea');
            for (let input of inputs) {
                if (input.value && webhookPattern.test(input.value)) {
                    return JSON.stringify({method: "input_value", url: input.value, id: input.id});
                }
            }

            // 方法3：查找机器人相关元素
            const robotElements = document.querySelectorAll('[class*="robot"], [id*="robot"], [data-testid*="robot"]');
            if (robotElements.length > 0) {
                // 尝试在这些元素中查找
                for (let el of robotElements) {
                    if (el.textContent && webhookPattern.test(el.textContent)) {
                        const match = el.textContent.match(webhookPattern);
                        if (match) {
                            return JSON.stringify({method: "robot_element", url: match[0], element: el.tagName});
                        }
                    }
                }
                return JSON.stringify({method: "robot_elements_found", count: robotElements.length});
            }

            // 方法4：查找复制按钮
            const copyButtons = document.querySelectorAll('button[class*="copy"], button[onclick*="copy"]');
            for (let btn of copyButtons) {
                // 检查按钮周围的文本
                const parentText = btn.parentElement ? btn.parentElement.textContent : '';
                if (parentText && webhookPattern.test(parentText)) {
                    const match = parentText.match(webhookPattern);
                    if (match) {
                        return JSON.stringify({method: "copy_button", url: match[0]});
                    }
                }
            }

            return JSON.stringify({method: "not_found", reason: "未找到webhook URL"});
        })();
        """

        try:
            js_result = self.execute_javascript(find_webhook_js)
            if js_result.startswith("SUCCESS:"):
                result_json = js_result[8:]
                try:
                    data = json.loads(result_json)

                    if data.get("url"):
                        results["found"] = True
                        results["webhook_url"] = data["url"]
                        results["method"] = data["method"]
                        results["details"] = data
                    elif data.get("method") == "robot_elements_found":
                        results["details"] = {
                            "message": f"找到{data.get('count', 0)}个机器人相关元素",
                            "suggestion": "需要进一步检查机器人详情",
                        }
                    else:
                        results["details"] = data

                except json.JSONDecodeError:
                    results["details"] = {"raw_result": result_json}
            else:
                results["details"] = {"error": js_result}

        except Exception as e:
            results["details"] = {"exception": str(e)}

        return results

    def navigate_to_robot_management(self) -> str:
        """导航到机器人管理页面"""
        script = f"""
        tell application "{self.browser}"
            activate
            delay 1
            set current tab of window 1 to make new tab with properties {{URL:"{self.robot_management_url}"}}
            delay 3
            return "已导航到机器人管理页面"
        end tell
        """

        return run_applescript(script)

    def navigate_to_customer_groups(self) -> str:
        """导航到客户群页面"""
        script = f"""
        tell application "{self.browser}"
            activate
            delay 1
            set current tab of window 1 to make new tab with properties {{URL:"{self.customer_groups_url}"}}
            delay 3
            return "已导航到客户群页面"
        end tell
        """

        return run_applescript(script)

    def navigate_to_app_management(self) -> str:
        """导航到应用管理页面"""
        script = f"""
        tell application "{self.browser}"
            activate
            delay 1
            set current tab of window 1 to make new tab with properties {{URL:"{self.app_management_url}"}}
            delay 3
            return "已导航到应用管理页面"
        end tell
        """

        return run_applescript(script)

    def get_current_page_info(self) -> Dict[str, str]:
        """获取当前页面信息"""
        result = {"url": "", "title": "", "success": False}

        # 获取URL
        url_script = f"""
        tell application "{self.browser}"
            if (count of windows) > 0 then
                set targetWindow to window 1
                if (count of tabs of targetWindow) > 0 then
                    set targetTab to tab 1 of targetWindow
                    return URL of targetTab
                end if
            end if
            return ""
        end tell
        """

        # 获取标题
        title_script = f"""
        tell application "{self.browser}"
            if (count of windows) > 0 then
                set targetWindow to window 1
                if (count of tabs of targetWindow) > 0 then
                    set targetTab to tab 1 of targetWindow
                    return name of targetTab
                end if
            end if
            return ""
        end tell
        """

        try:
            url = run_applescript(url_script, timeout=10)
            title = run_applescript(title_script, timeout=10)

            result["url"] = url
            result["title"] = title
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)

        return result

    def validate_webhook_url(self, url: str) -> bool:
        """验证webhook URL格式"""
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
                # 保持原有格式
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

        # 备份原文件
        import shutil

        backup_file = self.env_file.with_suffix(".env.backup_ai_agent")
        shutil.copy2(self.env_file, backup_file)

        # 写入文件
        with open(self.env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return True

    def test_webhook_connection(self, webhook_url: str) -> Dict[str, Any]:
        """测试webhook连接"""
        results = {"webhook_url": webhook_url, "tests": []}

        # 测试POST请求
        payload = {"msgtype": "text", "text": {"content": "MAREF通知系统测试 - AI代理自动化配置"}}

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

    def run_full_automation(self) -> Dict[str, Any]:
        """运行全自动化流程"""
        results = {"success": False, "webhook_url": None, "steps": [], "errors": []}

        print("=== 企业微信AI代理全自动化流程 ===")

        # 步骤1: 检查权限
        print("\n1. 检查Safari JavaScript权限...")
        if not self.check_safari_javascript_permission():
            results["steps"].append(
                {"name": "权限检查", "status": "失败", "error": "Safari JavaScript权限未启用"}
            )
            results["errors"].append(
                "需要启用Safari JavaScript权限：Safari → 偏好设置 → 高级 → 允许JavaScript来自Apple事件"
            )
            print("❌ Safari JavaScript权限未启用")
            print("   请手动启用: Safari → 偏好设置 → 高级 → 允许JavaScript来自Apple事件")
            return results
        results["steps"].append({"name": "权限检查", "status": "成功"})
        print("✅ Safari JavaScript权限已启用")

        # 步骤2: 激活浏览器
        print("\n2. 激活浏览器...")
        try:
            self.activate_browser()
            time.sleep(2)
            results["steps"].append({"name": "激活浏览器", "status": "成功"})
            print("✅ 浏览器已激活")
        except Exception as e:
            results["steps"].append({"name": "激活浏览器", "status": "失败", "error": str(e)})
            results["errors"].append(f"激活浏览器失败: {e}")
            print(f"❌ 激活浏览器失败: {e}")

        # 步骤3: 导航到企业微信
        print("\n3. 导航到企业微信管理后台...")
        try:
            nav_result = self.navigate_to_wecom()
            results["steps"].append(
                {"name": "导航到企业微信", "status": "成功", "details": nav_result}
            )
            print(f"✅ {nav_result}")

            # 等待页面加载
            time.sleep(3)

            # 获取当前页面信息
            page_info = self.get_current_page_info()
            print(f"   当前页面: {page_info.get('url', '未知')}")
            print(f"   页面标题: {page_info.get('title', '未知')}")

        except Exception as e:
            results["steps"].append({"name": "导航到企业微信", "status": "失败", "error": str(e)})
            results["errors"].append(f"导航失败: {e}")
            print(f"❌ 导航失败: {e}")

        # 步骤4: 扫描webhook URL
        print("\n4. 扫描webhook URL...")
        scan_results = self.scan_for_webhook_url()
        results["steps"].append(
            {
                "name": "扫描webhook",
                "status": "成功" if scan_results["found"] else "未找到",
                "details": scan_results,
            }
        )

        if scan_results["found"]:
            webhook_url = scan_results["webhook_url"]
            print(f"✅ 找到webhook URL: {webhook_url}")
            print(f"   发现方式: {scan_results.get('method', '未知')}")

            # 步骤5: 验证URL格式
            print("\n5. 验证webhook URL格式...")
            if self.validate_webhook_url(webhook_url):
                results["steps"].append({"name": "验证格式", "status": "成功"})
                print("✅ webhook URL格式正确")

                # 步骤6: 更新配置文件
                print("\n6. 更新配置文件...")
                if self.update_env_file(webhook_url):
                    results["steps"].append({"name": "更新配置", "status": "成功"})
                    print("✅ 配置文件已更新")

                    # 步骤7: 测试连接
                    print("\n7. 测试webhook连接...")
                    test_results = self.test_webhook_connection(webhook_url)

                    success_tests = [t for t in test_results["tests"] if t.get("success", False)]
                    if len(success_tests) > 0:
                        results["steps"].append({"name": "连接测试", "status": "成功"})
                        results["success"] = True
                        results["webhook_url"] = webhook_url
                        print("✅ webhook连接测试通过")
                    else:
                        results["steps"].append(
                            {"name": "连接测试", "status": "失败", "details": test_results}
                        )
                        results["success"] = True  # 配置已更新，可后续测试
                        results["webhook_url"] = webhook_url
                        print("⚠️  webhook连接测试失败，但配置已更新")
                else:
                    results["steps"].append({"name": "更新配置", "status": "失败"})
                    results["errors"].append("更新配置文件失败")
                    print("❌ 更新配置文件失败")
            else:
                results["steps"].append({"name": "验证格式", "status": "失败"})
                results["errors"].append(f"webhook URL格式不正确: {webhook_url}")
                print(f"❌ webhook URL格式不正确: {webhook_url}")
        else:
            print("❌ 未找到webhook URL")
            print(f"   扫描详情: {scan_results.get('details', {})}")

            # 尝试导航到其他页面再次扫描
            print("\n尝试其他导航路径...")
            navigation_methods = [
                ("机器人管理页面", self.navigate_to_robot_management),
                ("客户群页面", self.navigate_to_customer_groups),
                ("应用管理页面", self.navigate_to_app_management),
            ]

            for page_name, nav_func in navigation_methods:
                print(f"\n尝试导航到{page_name}...")
                try:
                    nav_result = nav_func()
                    print(f"✅ {nav_result}")
                    time.sleep(3)

                    # 再次扫描
                    scan_results = self.scan_for_webhook_url()
                    if scan_results["found"]:
                        webhook_url = scan_results["webhook_url"]
                        print(f"🎉 在{page_name}找到webhook URL: {webhook_url}")

                        # 立即更新配置
                        if self.validate_webhook_url(webhook_url) and self.update_env_file(
                            webhook_url
                        ):
                            results["webhook_url"] = webhook_url
                            results["success"] = True
                            results["steps"].append(
                                {
                                    "name": f"在{page_name}找到webhook",
                                    "status": "成功",
                                    "url": webhook_url,
                                }
                            )
                            break
                    else:
                        print(f"❌ 在{page_name}未找到webhook URL")

                except Exception as e:
                    print(f"❌ 导航到{page_name}失败: {e}")

        return results


@click.group()
def cli():
    """企业微信AI代理 - 全自动化管理工具"""
    pass


@cli.command()
def auto():
    """全自动化查找和配置企业微信机器人"""
    agent = WeComAIAgent()
    results = agent.run_full_automation()

    print("\n" + "=" * 50)
    print("自动化流程结果汇总")
    print("=" * 50)

    for step in results["steps"]:
        emoji = "✅" if step["status"] == "成功" else "❌" if step["status"] == "失败" else "⚠️"
        print(f"{emoji} {step['name']}: {step['status']}")
        if step.get("error"):
            print(f"   错误: {step['error']}")
        if step.get("details") and isinstance(step["details"], dict):
            for key, value in step["details"].items():
                if key not in ["error"]:
                    print(f"   {key}: {value}")

    if results.get("success"):
        print(f"\n🎉 自动化配置成功！")
        print(f"webhook URL: {results['webhook_url']}")
        print(f"配置文件已更新: {agent.env_file}")
        print("\n下一步: 运行完整系统测试")
        print("命令: python3 test_notification_channels_final.py")
    else:
        print(f"\n❌ 自动化配置失败")
        if results.get("errors"):
            print("错误列表:")
            for error in results["errors"]:
                print(f"  • {error}")

        print("\n备用方案:")
        print(
            "1. 手动获取webhook URL后运行: python3 wecom_robot_creator.py update --webhook-url YOUR_URL"
        )
        print("2. 或使用基础通知渠道: 邮件 + 控制台 + 文件日志")


@cli.command()
def check_permission():
    """检查Safari JavaScript权限"""
    agent = WeComAIAgent()
    has_permission = agent.check_safari_javascript_permission()

    if has_permission:
        print("✅ Safari JavaScript权限已启用")
    else:
        print("❌ Safari JavaScript权限未启用")
        print("\n请手动启用:")
        print("1. 打开Safari浏览器")
        print("2. Safari → 偏好设置 → 高级")
        print("3. 勾选'在菜单栏中显示开发菜单'")
        print("4. 开发 → 允许JavaScript来自Apple事件")
        print("\n或运行命令:")
        print("defaults write com.apple.Safari AllowJavaScriptFromAppleEvents -bool true")


@cli.command()
def scan():
    """扫描当前页面查找webhook URL"""
    agent = WeComAIAgent()

    # 先检查权限
    if not agent.check_safari_javascript_permission():
        print("❌ 需要启用Safari JavaScript权限")
        return

    results = agent.scan_for_webhook_url()

    print("=== 页面扫描结果 ===")
    if results["found"]:
        print(f"✅ 找到webhook URL: {results['webhook_url']}")
        print(f"发现方式: {results.get('method', '未知')}")
        print(f"详情: {json.dumps(results.get('details', {}), ensure_ascii=False, indent=2)}")
    else:
        print("❌ 未找到webhook URL")
        print(f"扫描详情: {json.dumps(results.get('details', {}), ensure_ascii=False, indent=2)}")

        # 显示当前页面信息
        page_info = agent.get_current_page_info()
        print(f"\n当前页面信息:")
        print(f"  URL: {page_info.get('url', '未知')}")
        print(f"  标题: {page_info.get('title', '未知')}")


@cli.command()
def page_info():
    """获取当前页面信息"""
    agent = WeComAIAgent()
    page_info = agent.get_current_page_info()

    print("=== 当前页面信息 ===")
    if page_info.get("success"):
        print(f"URL: {page_info.get('url', '未知')}")
        print(f"标题: {page_info.get('title', '未知')}")
    else:
        print(f"❌ 获取页面信息失败: {page_info.get('error', '未知错误')}")


if __name__ == "__main__":
    cli()
