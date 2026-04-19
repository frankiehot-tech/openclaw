#!/usr/bin/env python3
"""测试SPA页面导航和内容发现"""

import json
import re
import subprocess
import time


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


def execute_javascript(js_code: str) -> str:
    """在Safari中执行JavaScript"""
    escaped_js = js_code.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    script = f"""
    tell application "Safari"
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


def wait_for_element(selector: str, timeout: int = 10) -> bool:
    """等待元素出现"""
    js_wait = f"""
    (function() {{
        const startTime = Date.now();
        const timeout = {timeout} * 1000;

        function check() {{
            const element = document.querySelector("{selector}");
            if (element) {{
                return JSON.stringify({{
                    found: true,
                    tagName: element.tagName,
                    text: element.textContent.trim().substring(0, 200)
                }});
            }}

            if (Date.now() - startTime > timeout) {{
                return JSON.stringify({{found: false, reason: "timeout"}});
            }}

            // 继续等待
            return "waiting";
        }}

        let result = check();
        while (result === "waiting") {{
            // 短暂等待后重试
            const waitMs = 500;
            const start = Date.now();
            while (Date.now() - start < waitMs) {{
                // 空循环等待
            }}
            result = check();
        }}

        return result;
    }})();
    """

    start_time = time.time()
    while time.time() - start_time < timeout:
        result = execute_javascript(js_wait)
        if result.startswith("SUCCESS:"):
            try:
                data = json.loads(result[8:])
                if data.get("found"):
                    print(f"✅ 找到元素: {selector}")
                    return True
                elif data.get("reason") == "timeout":
                    break
            except:
                pass
        time.sleep(1)

    print(f"❌ 等待元素超时: {selector}")
    return False


def click_element(selector: str) -> bool:
    """点击元素"""
    js_click = f"""
    (function() {{
        try {{
            const element = document.querySelector("{selector}");
            if (!element) {{
                return JSON.stringify({{success: false, error: "元素不存在: {selector}"}});
            }}

            // 模拟点击事件
            const clickEvent = new MouseEvent('click', {{
                view: window,
                bubbles: true,
                cancelable: true
            }});
            element.dispatchEvent(clickEvent);

            // 也调用click方法
            if (typeof element.click === 'function') {{
                element.click();
            }}

            return JSON.stringify({{
                success: true,
                element: {{
                    tagName: element.tagName,
                    text: element.textContent.trim().substring(0, 100)
                }}
            }});
        }} catch (e) {{
            return JSON.stringify({{success: false, error: e.toString()}});
        }}
    }})();
    """

    result = execute_javascript(js_click)
    if result.startswith("SUCCESS:"):
        try:
            data = json.loads(result[8:])
            if data.get("success"):
                print(f"✅ 点击成功: {data.get('element', {}).get('text', '未知元素')}")
                return True
            else:
                print(f"❌ 点击失败: {data.get('error')}")
        except:
            print(f"❌ 点击解析失败: {result[:100]}")
    else:
        print(f"❌ 点击执行失败: {result}")

    return False


def navigate_to_apps() -> bool:
    """导航到应用管理页面"""
    print("=== 导航到应用管理页面 ===")

    # 方法1: 直接设置URL
    print("1. 尝试直接设置URL...")
    js_set_url = """
    (function() {
        window.location.hash = '#/apps';
        return JSON.stringify({success: true, url: window.location.href});
    })();
    """

    result = execute_javascript(js_set_url)
    if result.startswith("SUCCESS:"):
        print("✅ URL已设置")
        time.sleep(3)  # 等待SPA加载
        return True
    else:
        print(f"❌ 设置URL失败: {result}")

    # 方法2: 查找并点击应用管理链接
    print("\n2. 尝试查找应用管理链接...")
    js_find_apps_link = """
    (function() {
        // 查找包含"应用管理"的链接
        const links = document.querySelectorAll('a');
        for (let link of links) {
            const text = link.textContent.trim();
            const href = link.href || link.getAttribute('href') || '';

            if (text.includes('应用管理') || href.includes('#/apps')) {
                return JSON.stringify({
                    found: true,
                    text: text,
                    href: href,
                    element: {
                        tagName: link.tagName,
                        className: link.className || ''
                    }
                });
            }
        }
        return JSON.stringify({found: false});
    })();
    """

    result = execute_javascript(js_find_apps_link)
    if result.startswith("SUCCESS:"):
        try:
            data = json.loads(result[8:])
            if data.get("found"):
                print(f"✅ 找到应用管理链接: {data.get('text')}")
                print(f"   链接: {data.get('href')}")

                # 尝试点击
                # 需要更精确的选择器
                return click_element(f'a:contains("应用管理")')
        except:
            pass

    print("❌ 导航失败")
    return False


def explore_apps_page() -> dict:
    """探索应用管理页面"""
    print("\n=== 探索应用管理页面 ===")

    # 等待页面加载
    print("等待页面加载...")
    time.sleep(3)

    # 获取页面内容
    js_get_content = """
    (function() {
        const result = {
            url: window.location.href,
            title: document.title,
            apps: []
        };

        // 查找应用列表
        const appSelectors = [
            '.app-list', '.app-item', '[class*="app"]',
            '.card', '.list-item', 'table tr'
        ];

        for (let selector of appSelectors) {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                // 检查是否是应用列表
                const sampleText = elements[0].textContent.trim().substring(0, 200);
                if (sampleText.length > 20) {
                    result.containerSelector = selector;
                    result.containerCount = elements.length;
                    break;
                }
            }
        }

        // 查找Athena机器人
        const allText = document.body.textContent;
        const athenaMatches = allText.match(/Athena|机器人|robot/gi);
        if (athenaMatches) {
            result.hasAthenaReferences = true;
            result.athenaMatches = athenaMatches.length;
        }

        // 查找可能的webhook模式
        const webhookPattern = /https:\\/\\/qyapi\\.weixin\\.qq\\.com\\/cgi-bin\\/webhook\\/send\\?key=[a-zA-Z0-9\\-]+/g;
        const webhookMatches = allText.match(webhookPattern);
        if (webhookMatches) {
            result.webhookUrls = webhookMatches;
        }

        return JSON.stringify(result);
    })();
    """

    result = execute_javascript(js_get_content)
    if result.startswith("SUCCESS:"):
        try:
            data = json.loads(result[8:])
            print(f"页面URL: {data.get('url')}")
            print(f"页面标题: {data.get('title')}")

            if data.get("containerSelector"):
                print(
                    f"找到容器: {data.get('containerSelector')} ({data.get('containerCount')}个元素)"
                )

            if data.get("hasAthenaReferences"):
                print(f"✅ 找到Athena相关引用: {data.get('athenaMatches')}处")

            if data.get("webhookUrls"):
                print(f"🎉 找到webhook URLs: {len(data['webhookUrls'])}个")
                for url in data["webhookUrls"][:3]:
                    print(f"  • {url}")

            return data

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
    else:
        print(f"获取内容失败: {result}")

    return {}


def find_and_click_athena_app() -> bool:
    """查找并点击Athena应用"""
    print("\n=== 查找Athena应用 ===")

    js_find_athena = """
    (function() {
        // 查找包含Athena或机器人的元素
        const elements = document.querySelectorAll('*');
        const clickableElements = [];

        for (let el of elements) {
            const text = el.textContent.trim();
            if (text && (text.includes('Athena') || text.includes('机器人'))) {
                // 检查是否可点击
                const tagName = el.tagName;
                const isClickable = tagName === 'A' || tagName === 'BUTTON' ||
                                   el.onclick || el.getAttribute('onclick') ||
                                   el.classList.contains('clickable') ||
                                   el.parentElement.tagName === 'A';

                if (isClickable) {
                    clickableElements.push({
                        text: text.substring(0, 100),
                        tagName: tagName,
                        className: el.className || '',
                        id: el.id || ''
                    });
                }
            }
        }

        return JSON.stringify({
            found: clickableElements.length,
            elements: clickableElements.slice(0, 10)
        });
    })();
    """

    result = execute_javascript(js_find_athena)
    if result.startswith("SUCCESS:"):
        try:
            data = json.loads(result[8:])
            print(f"找到 {data['found']} 个可点击的Athena相关元素")

            if data["elements"]:
                print("前几个元素:")
                for i, el in enumerate(data["elements"]):
                    print(f"  {i+1}. [{el['tagName']}] {el['text']}")

                # 尝试点击第一个
                first_el = data["elements"][0]
                if first_el.get("id"):
                    return click_element(f"#{first_el['id']}")
                elif first_el.get("className"):
                    # 使用类选择器
                    class_selector = f".{first_el['className'].split(' ')[0]}"
                    return click_element(class_selector)

        except:
            pass

    print("❌ 未找到可点击的Athena应用")
    return False


if __name__ == "__main__":
    try:
        print("企业微信SPA页面导航测试")
        print("=" * 50)

        # 先获取当前页面信息
        js_current = """
        (function() {
            return JSON.stringify({
                url: window.location.href,
                title: document.title,
                hash: window.location.hash
            });
        })();
        """

        result = execute_javascript(js_current)
        if result.startswith("SUCCESS:"):
            try:
                current = json.loads(result[8:])
                print(f"当前页面: {current.get('title')}")
                print(f"当前URL: {current.get('url')}")
                print(f"当前Hash: {current.get('hash')}")
            except:
                pass

        # 如果不在应用管理页面，尝试导航
        if not current.get("hash", "").startswith("#/apps"):
            if navigate_to_apps():
                print("✅ 成功导航到应用管理")
            else:
                print("❌ 导航失败，尝试直接扫描")

        # 探索应用管理页面
        explore_apps_page()

        # 尝试查找Athena应用
        find_and_click_athena_app()

        # 最后再次扫描webhook
        print("\n=== 最终扫描webhook URL ===")
        js_final_scan = """
        (function() {
            const webhookPattern = /https:\\/\\/qyapi\\.weixin\\.qq\\.com\\/cgi-bin\\/webhook\\/send\\?key=[a-zA-Z0-9\\-]+/g;
            const allText = document.body.textContent;
            const matches = allText.match(webhookPattern);

            return JSON.stringify({
                found: matches ? matches.length : 0,
                urls: matches || []
            });
        })();
        """

        result = execute_javascript(js_final_scan)
        if result.startswith("SUCCESS:"):
            try:
                scan_data = json.loads(result[8:])
                if scan_data.get("found", 0) > 0:
                    print(f"🎉 找到 {scan_data['found']} 个webhook URL!")
                    for url in scan_data["urls"]:
                        print(f"  • {url}")
                else:
                    print("❌ 最终扫描未找到webhook URL")
            except:
                print("❌ 最终扫描解析失败")

    except Exception as e:
        print(f"测试过程出错: {e}")
        import traceback

        traceback.print_exc()
