#!/usr/bin/env python3
"""
企业微信页面探索器 - 自动化查找webhook URL
通过系统性的页面探索和深度扫描，实现完全免手动的webhook URL发现
"""

import json
import re
import subprocess
import time
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


class WeComExplorer:
    """企业微信页面探索器"""

    def __init__(self):
        self.browser = "Safari"
        self.results = {
            "exploration_started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pages_explored": [],
            "webhook_urls_found": [],
            "errors": [],
        }

        # 企业微信页面URL模式
        self.base_url = "https://work.weixin.qq.com/wework_admin/frame"

        # 需要探索的页面路径（基于常见的企业微信管理后台结构）
        self.page_paths = [
            # 应用相关
            {"name": "应用管理", "hash": "#/apps", "priority": 10},
            {"name": "应用详情", "hash": "#/app/manage", "priority": 9},
            {"name": "应用列表", "hash": "#/app/list", "priority": 8},
            # 客户联系相关
            {"name": "客户群聊", "hash": "#/customer/group", "priority": 10},
            {"name": "客户联系", "hash": "#/customer", "priority": 7},
            {"name": "群聊管理", "hash": "#/group", "priority": 9},
            # 机器人相关
            {"name": "机器人管理", "hash": "#/robot", "priority": 10},
            {"name": "群机器人", "hash": "#/group/robot", "priority": 10},
            {"name": "机器人设置", "hash": "#/robot/settings", "priority": 9},
            # 通讯录相关
            {"name": "通讯录", "hash": "#/contacts", "priority": 5},
            {"name": "部门管理", "hash": "#/department", "priority": 4},
            # 其他可能包含机器人的页面
            {"name": "管理工具", "hash": "#/manage/tools", "priority": 6},
            {"name": "集成设置", "hash": "#/integration", "priority": 7},
            {"name": "API管理", "hash": "#/api", "priority": 8},
            {"name": "Webhook设置", "hash": "#/webhook", "priority": 10},
        ]

    def execute_javascript(self, js_code: str) -> str:
        """在Safari中执行JavaScript"""
        escaped_js = js_code.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

        script = f"""
        tell application "{self.browser}"
            set targetWindow to window 1
            set targetTab to tab 1 of targetWindow

            try
                set result to do JavaScript "{escaped_js}" in targetTab
                return "SUCCESS:" & result
            on error errMsg
                return "ERROR:" & errMsg
            end try
        end tell
        """

        return run_applescript(script)

    def navigate_to_hash(self, hash_path: str) -> bool:
        """导航到指定的hash路径"""
        print(f"  导航到: {hash_path}")

        js_navigate = f"""
        (function() {{
            try {{
                window.location.hash = "{hash_path}";

                // 等待hash变化
                return JSON.stringify({{
                    success: true,
                    new_hash: window.location.hash,
                    url: window.location.href
                }});
            }} catch (e) {{
                return JSON.stringify({{
                    success: false,
                    error: e.toString()
                }});
            }}
        }})();
        """

        result = self.execute_javascript(js_navigate)
        if result.startswith("SUCCESS:"):
            try:
                data = json.loads(result[8:])
                if data.get("success"):
                    # 等待页面内容加载（SPA可能需要时间）
                    time.sleep(3)
                    return True
            except:
                pass

        print(f"  导航失败: {result[:100]}")
        return False

    def get_page_info(self) -> Dict[str, Any]:
        """获取当前页面信息"""
        js_info = """
        (function() {
            return JSON.stringify({
                url: window.location.href,
                hash: window.location.hash,
                title: document.title,
                body_text_length: document.body.textContent.length,
                has_sidebar: !!document.querySelector('.sidebar, .side-nav, [class*="sidebar"]'),
                has_content: document.body.textContent.trim().length > 100
            });
        })();
        """

        result = self.execute_javascript(js_info)
        if result.startswith("SUCCESS:"):
            try:
                return json.loads(result[8:])
            except:
                pass

        return {"error": "获取页面信息失败"}

    def deep_scan_for_webhook(self) -> Dict[str, Any]:
        """深度扫描页面查找webhook URL"""
        js_deep_scan = """
        (function() {
            const results = {
                webhook_urls: [],
                robot_elements: [],
                athena_references: [],
                copy_buttons: [],
                input_fields: []
            };

            // 1. 正则表达式匹配webhook URL
            const webhookPattern = /https:\\/\\/qyapi\\.weixin\\.qq\\.com\\/cgi-bin\\/webhook\\/send\\?key=[a-zA-Z0-9\\-]+/g;
            const allText = document.body.textContent;
            const urlMatches = allText.match(webhookPattern);

            if (urlMatches) {
                results.webhook_urls = urlMatches;
            }

            // 2. 查找机器人相关元素
            const robotSelectors = [
                '*[class*="robot"]',
                '*[id*="robot"]',
                '*[data-testid*="robot"]',
                '*[class*="bot"]',
                '*:contains("机器人")',
                '*:contains("Robot")',
                '*:contains("robot")'
            ];

            robotSelectors.forEach(selector => {
                try {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        if (el.textContent && el.textContent.trim()) {
                            results.robot_elements.push({
                                selector: selector,
                                text: el.textContent.trim().substring(0, 200),
                                tagName: el.tagName,
                                className: el.className || '',
                                id: el.id || ''
                            });
                        }
                    });
                } catch(e) {
                    // 忽略无效选择器
                }
            });

            // 3. 查找Athena相关文本
            if (allText.includes('Athena') || allText.includes('athena')) {
                // 查找包含Athena的元素
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );

                let node;
                while (node = walker.nextNode()) {
                    if (node.textContent.includes('Athena') || node.textContent.includes('athena')) {
                        const parent = node.parentElement;
                        results.athena_references.push({
                            text: node.textContent.trim().substring(0, 200),
                            parentTag: parent.tagName,
                            parentClass: parent.className || ''
                        });
                    }
                }
            }

            // 4. 查找复制按钮（可能用于复制webhook）
            const copyButtons = document.querySelectorAll('button, .btn, [class*="copy"], [class*="Copy"]');
            copyButtons.forEach(btn => {
                const text = btn.textContent || btn.getAttribute('title') || btn.getAttribute('aria-label') || '';
                if (text.includes('复制') || text.includes('Copy') || text.includes('copy')) {
                    results.copy_buttons.push({
                        text: text.substring(0, 100),
                        tagName: btn.tagName,
                        className: btn.className || ''
                    });
                }
            });

            // 5. 查找输入框（可能包含webhook URL）
            const inputs = document.querySelectorAll('input[type="text"], input[type="url"], textarea');
            inputs.forEach(input => {
                if (input.value && webhookPattern.test(input.value)) {
                    results.input_fields.push({
                        value: input.value,
                        id: input.id || '',
                        className: input.className || '',
                        tagName: input.tagName
                    });
                }
            });

            // 总结
            results.summary = {
                found_webhooks: results.webhook_urls.length,
                found_robots: results.robot_elements.length,
                found_athena: results.athena_references.length,
                found_copy_buttons: results.copy_buttons.length,
                found_input_fields: results.input_fields.length
            };

            return JSON.stringify(results);
        })();
        """

        result = self.execute_javascript(js_deep_scan)
        if result.startswith("SUCCESS:"):
            try:
                return json.loads(result[8:])
            except json.JSONDecodeError as e:
                return {"error": f"JSON解析错误: {e}", "raw_result": result[:200]}

        return {"error": f"扫描失败: {result[:200]}"}

    def explore_page(self, page_info: Dict[str, Any]) -> Dict[str, Any]:
        """探索单个页面"""
        page_result = {
            "page_name": page_info["name"],
            "hash": page_info["hash"],
            "explored_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scan_results": None,
            "page_info": None,
            "success": False,
        }

        print(f"\n探索页面: {page_info['name']} ({page_info['hash']})")

        # 导航到页面
        if not self.navigate_to_hash(page_info["hash"]):
            page_result["error"] = "导航失败"
            return page_result

        # 获取页面信息
        page_info_data = self.get_page_info()
        page_result["page_info"] = page_info_data

        # 检查页面是否有内容
        if not page_info_data.get("has_content", False):
            print(f"  页面无内容，跳过深度扫描")
            return page_result

        # 深度扫描
        print(f"  深度扫描中...")
        scan_results = self.deep_scan_for_webhook()
        page_result["scan_results"] = scan_results

        # 检查是否找到webhook
        if scan_results.get("summary", {}).get("found_webhooks", 0) > 0:
            page_result["success"] = True
            webhook_urls = scan_results.get("webhook_urls", [])
            print(f"  ✅ 找到 {len(webhook_urls)} 个webhook URL!")
            for url in webhook_urls:
                print(f"    • {url}")

            # 保存到总结果
            for url in webhook_urls:
                if url not in self.results["webhook_urls_found"]:
                    self.results["webhook_urls_found"].append(
                        {
                            "url": url,
                            "found_on_page": page_info["name"],
                            "found_at": page_result["explored_at"],
                        }
                    )

        else:
            # 虽然没有webhook，但可能有其他有用信息
            summary = scan_results.get("summary", {})
            if summary.get("found_robots", 0) > 0:
                print(f"  ⚠️  找到 {summary['found_robots']} 个机器人相关元素")
            if summary.get("found_athena", 0) > 0:
                print(f"  ⚠️  找到 {summary['found_athena']} 个Athena引用")
            if summary.get("found_copy_buttons", 0) > 0:
                print(f"  ⚠️  找到 {summary['found_copy_buttons']} 个复制按钮")

        return page_result

    def explore_all_pages(self) -> Dict[str, Any]:
        """探索所有预定义的页面"""
        print("=" * 60)
        print("企业微信页面探索器 - 开始系统探索")
        print("=" * 60)

        # 按优先级排序页面
        sorted_pages = sorted(self.page_paths, key=lambda x: x["priority"], reverse=True)

        # 记录开始状态
        start_info = self.get_page_info()
        print(f"起始页面: {start_info.get('title', '未知')}")
        print(f"起始URL: {start_info.get('url', '未知')}")
        print(f"起始Hash: {start_info.get('hash', '未知')}")

        # 探索每个页面
        explored_count = 0
        for page in sorted_pages:
            if explored_count >= 10:  # 限制探索页面数量
                print(f"\n已达到最大探索页面数 (10)")
                break

            page_result = self.explore_page(page)
            self.results["pages_explored"].append(page_result)
            explored_count += 1

            # 如果找到了webhook，可以提前结束
            if page_result.get("success") and self.results["webhook_urls_found"]:
                print(f"\n🎉 已找到webhook URL，提前结束探索")
                break

            # 短暂等待，避免请求过快
            time.sleep(2)

        # 总结结果
        print("\n" + "=" * 60)
        print("探索完成")
        print("=" * 60)

        total_webhooks = len(self.results["webhook_urls_found"])
        total_pages = len(self.results["pages_explored"])
        successful_pages = len([p for p in self.results["pages_explored"] if p.get("success")])

        print(f"探索页面数: {total_pages}")
        print(f"成功找到内容的页面: {successful_pages}")
        print(f"找到的webhook URL数量: {total_webhooks}")

        if total_webhooks > 0:
            print(f"\n找到的webhook URL:")
            for i, webhook in enumerate(self.results["webhook_urls_found"]):
                print(f"  {i+1}. {webhook['url']}")
                print(f"     发现于: {webhook['found_on_page']}")
                print(f"     发现时间: {webhook['found_at']}")

        self.results["exploration_completed"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.results["summary"] = {
            "total_pages_explored": total_pages,
            "successful_pages": successful_pages,
            "total_webhooks_found": total_webhooks,
        }

        return self.results

    def smart_explore(self) -> Dict[str, Any]:
        """智能探索：先尝试已知的机器人相关页面，再扩展"""
        print("=" * 60)
        print("企业微信智能探索 - 优先查找机器人相关页面")
        print("=" * 60)

        # 第一优先级：机器人相关页面
        robot_pages = [
            p for p in self.page_paths if "robot" in p["name"].lower() or "bot" in p["name"].lower()
        ]
        print(f"找到 {len(robot_pages)} 个机器人相关页面")

        # 第二优先级：群聊相关页面
        group_pages = [
            p for p in self.page_paths if "群" in p["name"] or "group" in p["name"].lower()
        ]
        print(f"找到 {len(group_pages)} 个群聊相关页面")

        # 第三优先级：应用相关页面
        app_pages = [
            p for p in self.page_paths if "应用" in p["name"] or "app" in p["name"].lower()
        ]
        print(f"找到 {len(app_pages)} 个应用相关页面")

        # 合并并去重
        all_priority_pages = []
        seen_hashes = set()

        for page in robot_pages + group_pages + app_pages:
            if page["hash"] not in seen_hashes:
                seen_hashes.add(page["hash"])
                all_priority_pages.append(page)

        print(f"总计需要探索 {len(all_priority_pages)} 个优先级页面")

        # 探索优先级页面
        for page in all_priority_pages:
            page_result = self.explore_page(page)
            self.results["pages_explored"].append(page_result)

            # 如果找到了webhook，提前结束
            if page_result.get("success") and self.results["webhook_urls_found"]:
                print(f"\n🎉 在优先级探索中找到webhook URL")
                break

            time.sleep(2)

        # 如果没有找到，再探索其他页面
        if not self.results["webhook_urls_found"]:
            print(f"\n未在优先级页面中找到webhook，开始探索其他页面...")

            # 获取未探索的页面
            explored_hashes = {p["hash"] for p in self.results["pages_explored"]}
            remaining_pages = [p for p in self.page_paths if p["hash"] not in explored_hashes]

            # 按优先级排序并探索
            remaining_pages.sort(key=lambda x: x["priority"], reverse=True)

            for i, page in enumerate(remaining_pages[:5]):  # 只探索前5个剩余页面
                print(f"\n探索剩余页面 {i+1}/{min(5, len(remaining_pages))}: {page['name']}")
                page_result = self.explore_page(page)
                self.results["pages_explored"].append(page_result)

                if page_result.get("success") and self.results["webhook_urls_found"]:
                    break

                time.sleep(2)

        return self.results


@click.group()
def cli():
    """企业微信页面探索器 - 自动化查找webhook URL"""
    pass


@cli.command()
def explore_all():
    """探索所有预定义的企业微信页面"""
    explorer = WeComExplorer()
    results = explorer.explore_all_pages()

    # 保存结果到文件
    import os

    results_file = os.path.join(os.path.dirname(__file__), "exploration_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n探索结果已保存到: {results_file}")


@cli.command()
def smart():
    """智能探索：优先查找机器人相关页面"""
    explorer = WeComExplorer()
    results = explorer.smart_explore()

    # 保存结果到文件
    import os

    results_file = os.path.join(os.path.dirname(__file__), "smart_exploration_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n智能探索结果已保存到: {results_file}")


@cli.command()
def test():
    """测试探索器功能"""
    print("测试企业微信页面探索器...")

    explorer = WeComExplorer()

    # 测试获取当前页面信息
    print("\n1. 测试获取页面信息...")
    page_info = explorer.get_page_info()
    print(f"   当前页面: {page_info.get('title', '未知')}")
    print(f"   当前URL: {page_info.get('url', '未知')}")
    print(f"   当前Hash: {page_info.get('hash', '未知')}")

    # 测试深度扫描
    print("\n2. 测试深度扫描...")
    scan_results = explorer.deep_scan_for_webhook()
    summary = scan_results.get("summary", {})
    print(f"   扫描完成:")
    print(f"     • Webhook URL: {summary.get('found_webhooks', 0)}个")
    print(f"     • 机器人元素: {summary.get('found_robots', 0)}个")
    print(f"     • Athena引用: {summary.get('found_athena', 0)}个")

    # 显示找到的webhook URL（如果有）
    if summary.get("found_webhooks", 0) > 0:
        print(f"\n   找到的webhook URL:")
        for url in scan_results.get("webhook_urls", [])[:3]:
            print(f"     • {url}")


@cli.command()
def current():
    """显示当前页面信息"""
    explorer = WeComExplorer()
    page_info = explorer.get_page_info()

    print("=== 当前企业微信页面信息 ===")
    print(f"URL: {page_info.get('url', '未知')}")
    print(f"Hash: {page_info.get('hash', '未知')}")
    print(f"标题: {page_info.get('title', '未知')}")
    print(f"正文长度: {page_info.get('body_text_length', 0)} 字符")
    print(f"是否有侧边栏: {'是' if page_info.get('has_sidebar') else '否'}")
    print(f"是否有内容: {'是' if page_info.get('has_content') else '否'}")


if __name__ == "__main__":
    cli()
