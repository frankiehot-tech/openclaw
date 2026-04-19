#!/usr/bin/env python3
"""机器人元素点击探索器 - 尝试点击机器人应用并查找webhook URL"""

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


def navigate_to_apps() -> bool:
    """导航到应用管理页面"""
    print("导航到应用管理页面...")
    js_navigate = """
    (function() {
        window.location.hash = '#/apps';
        return JSON.stringify({success: true, hash: window.location.hash});
    })();
    """

    result = execute_javascript(js_navigate)
    if result.startswith("SUCCESS:"):
        print("✅ 已导航到应用管理页面")
        time.sleep(3)  # 等待SPA加载
        return True
    else:
        print(f"❌ 导航失败: {result}")
        return False


def find_and_click_robot() -> dict:
    """查找并点击机器人应用"""
    print("\n查找机器人应用...")

    # 首先查找所有可能的机器人元素
    js_find_robots = """
    (function() {
        const robotElements = [];

        // 查找之前发现的"消息推送"元素
        const roomRobotSelectors = [
            '.js_appList_roomRobot',
            '.app_index_item_Open',
            '.app_index_item',
            'a[class*="robot"]',
            'a[class*="bot"]',
            'a:contains("消息推送")',
            'div:contains("消息推送")'
        ];

        for (let selector of roomRobotSelectors) {
            try {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    const text = el.textContent.trim();
                    if (text.includes('消息推送') || el.className.includes('roomRobot')) {
                        // 获取元素详细信息
                        const rect = el.getBoundingClientRect();
                        const isVisible = rect.width > 0 && rect.height > 0;

                        robotElements.push({
                            selector: selector,
                            text: text.substring(0, 100),
                            className: el.className,
                            id: el.id || '',
                            tagName: el.tagName,
                            isVisible: isVisible,
                            isClickable: el.tagName === 'A' || el.tagName === 'BUTTON' ||
                                        el.onclick || el.getAttribute('onclick'),
                            dataAttributes: {}
                        });

                        // 收集data-*属性
                        for (let attr of el.attributes) {
                            if (attr.name.startsWith('data-')) {
                                robotElements[robotElements.length-1].dataAttributes[attr.name] = attr.value;
                            }
                        }
                    }
                });
            } catch(e) {
                // 忽略无效选择器
            }
        }

        return JSON.stringify({
            found: robotElements.length,
            elements: robotElements
        });
    })();
    """

    result = execute_javascript(js_find_robots)
    if not result.startswith("SUCCESS:"):
        print(f"❌ 查找机器人失败: {result}")
        return {"success": False, "error": "查找失败"}

    try:
        data = json.loads(result[8:])
        print(f"找到 {data['found']} 个机器人相关元素")

        if data["found"] == 0:
            return {"success": False, "error": "未找到机器人元素"}

        # 显示找到的元素
        for i, element in enumerate(data["elements"]):
            print(f"\n元素 {i+1}:")
            print(f"  选择器: {element['selector']}")
            print(f"  文本: {element['text']}")
            print(f"  类名: {element['className']}")
            print(f"  标签: {element['tagName']}")
            print(f"  是否可见: {element['isVisible']}")
            print(f"  是否可点击: {element['isClickable']}")

            # 检查data属性中是否有webhook URL
            data_attrs = element.get("dataAttributes", {})
            if data_attrs:
                print(f"  数据属性: {json.dumps(data_attrs, ensure_ascii=False)}")

                # 检查是否有webhook URL
                for key, value in data_attrs.items():
                    if "webhook" in key.lower() or "key" in key.lower():
                        print(f"  ⚠️  发现可能的webhook数据属性: {key}={value[:50]}...")
                        # 检查是否是完整的webhook URL（在JavaScript中已检查）

        # 尝试点击第一个元素
        first_element = data["elements"][0]
        print(f"\n尝试点击第一个元素: {first_element['text']}")

        # 根据元素类型选择点击方法
        click_method = ""

        # 优先使用js_appList_roomRobot类，因为它更特定
        if "js_appList_roomRobot" in first_element["className"]:
            click_method = ".js_appList_roomRobot"
        elif first_element["selector"].startswith("."):
            # 类选择器
            class_name = first_element["className"].split(" ")[0]
            if class_name:
                click_method = f".{class_name}"

        # 如果没有特定的选择器，使用文本内容
        if not click_method:
            # 注意：JavaScript中的:contains选择器可能不是标准CSS
            # 我们使用属性选择器作为备选
            click_method = f"a[class*='{' '.join(first_element['className'].split()[:1])}']"

        print(f"使用选择器点击: {click_method}")

        # 点击元素
        js_click = f"""
        (function() {{
            try {{
                const element = document.querySelector("{click_method}");
                if (!element) {{
                    return JSON.stringify({{success: false, error: "元素不存在: {click_method}"}});
                }}

                console.log("点击元素:", element);

                // 触发点击事件
                const clickEvent = new MouseEvent('click', {{
                    view: window,
                    bubbles: true,
                    cancelable: true
                }});
                element.dispatchEvent(clickEvent);

                // 如果元素有click方法，也调用它
                if (typeof element.click === 'function') {{
                    element.click();
                }}

                // 返回点击结果
                return JSON.stringify({{
                    success: true,
                    element: {{
                        text: element.textContent.trim().substring(0, 100),
                        tagName: element.tagName,
                        href: element.href || element.getAttribute('href') || ''
                    }},
                    afterClickUrl: window.location.href
                }});
            }} catch (e) {{
                return JSON.stringify({{success: false, error: e.toString()}});
            }}
        }})();
        """

        click_result = execute_javascript(js_click)
        if click_result.startswith("SUCCESS:"):
            try:
                click_data = json.loads(click_result[8:])
                if click_data.get("success"):
                    print(f"✅ 点击成功")
                    print(f"   点击后URL: {click_data.get('afterClickUrl', '未知')}")

                    # 等待内容加载
                    print("等待内容加载...")
                    time.sleep(3)

                    return {
                        "success": True,
                        "clicked_element": click_data.get("element"),
                        "new_url": click_data.get("afterClickUrl"),
                    }
                else:
                    print(f"❌ 点击失败: {click_data.get('error')}")
            except:
                print(f"❌ 点击结果解析失败: {click_result[:100]}")
        else:
            print(f"❌ 点击执行失败: {click_result}")

    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        print(f"原始响应: {result[:200]}")

    return {"success": False, "error": "点击过程失败"}


def scan_after_click() -> dict:
    """点击后扫描页面内容"""
    print("\n扫描点击后的页面内容...")

    # 深度扫描webhook URL
    js_scan = """
    (function() {
        const results = {
            current_url: window.location.href,
            current_hash: window.location.hash,
            page_title: document.title,
            webhook_urls: [],
            modal_dialogs: [],
            input_fields: [],
            found_details: false
        };

        // 1. 扫描所有文本中的webhook URL
        const webhookPattern = /https:\\/\\/qyapi\\.weixin\\.qq\\.com\\/cgi-bin\\/webhook\\/send\\?key=[a-zA-Z0-9\\-]+/g;
        const allText = document.body.textContent;
        const urlMatches = allText.match(webhookPattern);

        if (urlMatches) {
            results.webhook_urls = urlMatches;
        }

        // 2. 检查是否有模态对话框打开
        const modals = document.querySelectorAll('.modal, .dialog, .popup, [role="dialog"]');
        modals.forEach(modal => {
            const rect = modal.getBoundingClientRect();
            if (rect.width > 100 && rect.height > 50) {  // 合理的模态框尺寸
                results.modal_dialogs.push({
                    className: modal.className,
                    text: modal.textContent.trim().substring(0, 200)
                });
            }
        });

        // 3. 查找输入框（可能包含webhook URL）
        const inputs = document.querySelectorAll('input[type="text"], input[type="url"], textarea, .input-text, .form-control');
        inputs.forEach(input => {
            if (input.value && webhookPattern.test(input.value)) {
                results.input_fields.push({
                    value: input.value,
                    id: input.id || '',
                    className: input.className || '',
                    placeholder: input.placeholder || ''
                });
            }
        });

        // 4. 检查页面是否有机器人详情
        const detailTexts = ['机器人详情', 'webhook', 'Webhook', '消息推送配置', '群机器人'];
        detailTexts.forEach(text => {
            if (allText.includes(text)) {
                results.found_details = true;
            }
        });

        // 5. 查找复制按钮
        const copyButtons = document.querySelectorAll('button, .btn');
        results.copy_buttons = [];
        copyButtons.forEach(btn => {
            const btnText = btn.textContent || btn.getAttribute('title') || btn.getAttribute('aria-label') || '';
            if (btnText.includes('复制') || btnText.includes('Copy') || btnText.includes('copy')) {
                // 检查按钮附近是否有webhook URL
                const parentText = btn.parentElement ? btn.parentElement.textContent : '';
                if (parentText && webhookPattern.test(parentText)) {
                    const match = parentText.match(webhookPattern);
                    if (match) {
                        results.webhook_urls.push(match[0]);
                    }
                }
            }
        });

        return JSON.stringify(results);
    })();
    """

    result = execute_javascript(js_scan)
    if result.startswith("SUCCESS:"):
        try:
            scan_data = json.loads(result[8:])
            print(f"当前URL: {scan_data.get('current_url')}")
            print(f"当前Hash: {scan_data.get('current_hash')}")
            print(f"页面标题: {scan_data.get('page_title')}")

            webhook_urls = scan_data.get("webhook_urls", [])
            if webhook_urls:
                print(f"🎉 找到 {len(webhook_urls)} 个webhook URL!")
                for url in webhook_urls:
                    print(f"  • {url}")
                return {"success": True, "webhook_urls": webhook_urls, "scan_data": scan_data}

            # 虽然没有webhook，但可能有其他发现
            if scan_data.get("modal_dialogs", []):
                print(f"⚠️  发现 {len(scan_data['modal_dialogs'])} 个模态对话框")
                for modal in scan_data["modal_dialogs"][:2]:
                    print(f"  模态框: {modal.get('text', '')[:100]}...")

            if scan_data.get("input_fields", []):
                print(f"⚠️  发现 {len(scan_data['input_fields'])} 个输入框")

            if scan_data.get("found_details"):
                print("⚠️  页面包含机器人详情内容")

        except json.JSONDecodeError as e:
            print(f"❌ 扫描结果解析错误: {e}")
    else:
        print(f"❌ 扫描失败: {result}")

    return {"success": False, "scan_data": {}}


def explore_modal_if_exists() -> dict:
    """如果存在模态框，尝试在其中查找webhook"""
    print("\n检查模态框内容...")

    js_explore_modal = """
    (function() {
        // 查找最可能的模态框
        const modalSelectors = ['.modal-content', '.dialog-content', '.popup-content', '.ant-modal-content'];

        for (let selector of modalSelectors) {
            const modal = document.querySelector(selector);
            if (modal && modal.offsetParent !== null) {  // 可见的
                // 在模态框中查找webhook URL
                const webhookPattern = /https:\\/\\/qyapi\\.weixin\\.qq\\.com\\/cgi-bin\\/webhook\\/send\\?key=[a-zA-Z0-9\\-]+/g;
                const modalText = modal.textContent;
                const matches = modalText.match(webhookPattern);

                return JSON.stringify({
                    found_modal: true,
                    selector: selector,
                    text_preview: modalText.substring(0, 300),
                    webhook_urls: matches || [],
                    total_matches: matches ? matches.length : 0
                });
            }
        }

        return JSON.stringify({found_modal: false});
    })();
    """

    result = execute_javascript(js_explore_modal)
    if result.startswith("SUCCESS:"):
        try:
            modal_data = json.loads(result[8:])
            if modal_data.get("found_modal"):
                print(f"✅ 找到模态框: {modal_data.get('selector')}")
                print(f"   内容预览: {modal_data.get('text_preview', '')[:200]}...")

                webhook_urls = modal_data.get("webhook_urls", [])
                if webhook_urls:
                    print(f"🎉 在模态框中找到 {len(webhook_urls)} 个webhook URL!")
                    for url in webhook_urls:
                        print(f"  • {url}")
                    return {"success": True, "webhook_urls": webhook_urls, "source": "modal"}
                else:
                    print("⚠️  模态框中未找到webhook URL")
            else:
                print("未找到可见的模态框")
        except:
            print("模态框检查解析失败")

    return {"success": False}


def explore_room_robot_page() -> dict:
    """探索群机器人页面，查找Athena机器人"""
    print("\n=== 探索群机器人页面 ===")

    # 扫描页面中的机器人列表
    js_find_robots = """
    (function() {
        const results = {
            robots: [],
            athena_robots: [],
            webhook_urls: []
        };

        // 查找机器人列表
        const robotSelectors = [
            '.robot-item', '.robot-card', '.bot-item',
            'tr[data-type="robot"]', 'li[data-type="robot"]',
            'div[class*="robot"]', 'div[class*="bot"]'
        ];

        robotSelectors.forEach(selector => {
            try {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    const text = el.textContent.trim();
                    if (text && text.length > 0) {
                        const robotInfo = {
                            selector: selector,
                            text: text.substring(0, 200),
                            tagName: el.tagName,
                            className: el.className || '',
                            id: el.id || '',
                            isAthena: text.includes('Athena') || text.includes('athena')
                        };

                        results.robots.push(robotInfo);

                        if (robotInfo.isAthena) {
                            results.athena_robots.push(robotInfo);
                        }
                    }
                });
            } catch(e) {
                // 忽略无效选择器
            }
        });

        // 如果没有找到特定选择器的元素，查找所有包含"机器人"的元素
        if (results.robots.length === 0) {
            const allElements = document.querySelectorAll('*');
            for (let el of allElements) {
                const text = el.textContent.trim();
                if (text && (text.includes('机器人') || text.includes('Robot'))) {
                    // 检查是否可能是机器人项目
                    if (el.tagName === 'DIV' || el.tagName === 'LI' || el.tagName === 'TR') {
                        results.robots.push({
                            selector: 'manual-search',
                            text: text.substring(0, 200),
                            tagName: el.tagName,
                            className: el.className || '',
                            id: el.id || '',
                            isAthena: text.includes('Athena') || text.includes('athena')
                        });
                    }
                }
            }
        }

        // 扫描webhook URL
        const webhookPattern = /https:\\/\\/qyapi\\.weixin\\.qq\\.com\\/cgi-bin\\/webhook\\/send\\?key=[a-zA-Z0-9\\-]+/g;
        const allText = document.body.textContent;
        const urlMatches = allText.match(webhookPattern);

        if (urlMatches) {
            results.webhook_urls = urlMatches;
        }

        return JSON.stringify(results);
    })();
    """

    result = execute_javascript(js_find_robots)
    if result.startswith("SUCCESS:"):
        try:
            data = json.loads(result[8:])
            print(f"找到 {len(data.get('robots', []))} 个机器人")
            print(f"其中 {len(data.get('athena_robots', []))} 个是Athena机器人")

            if data.get("webhook_urls", []):
                print(f"🎉 找到 {len(data['webhook_urls'])} 个webhook URL!")
                for url in data["webhook_urls"]:
                    print(f"  • {url}")
                return {"success": True, "webhook_urls": data["webhook_urls"]}

            # 如果有Athena机器人，尝试点击第一个
            athena_robots = data.get("athena_robots", [])
            if athena_robots:
                print(f"尝试点击Athena机器人: {athena_robots[0].get('text', '')[:50]}")

                # 构建点击选择器
                click_selector = ""
                robot = athena_robots[0]

                if robot.get("id"):
                    click_selector = f"#{robot['id']}"
                elif robot.get("className"):
                    # 使用第一个类名
                    first_class = robot["className"].split(" ")[0]
                    if first_class:
                        click_selector = f".{first_class}"

                if click_selector:
                    # 点击机器人
                    js_click = f"""
                    (function() {{
                        try {{
                            const element = document.querySelector("{click_selector}");
                            if (!element) {{
                                return JSON.stringify({{success: false, error: "元素不存在: {click_selector}"}});
                            }}

                            // 触发点击
                            const clickEvent = new MouseEvent('click', {{
                                view: window,
                                bubbles: true,
                                cancelable: true
                            }});
                            element.dispatchEvent(clickEvent);

                            if (typeof element.click === 'function') {{
                                element.click();
                            }}

                            return JSON.stringify({{
                                success: true,
                                clicked: element.textContent.trim().substring(0, 100)
                            }});
                        }} catch (e) {{
                            return JSON.stringify({{success: false, error: e.toString()}});
                        }}
                    }})();
                    """

                    click_result = execute_javascript(js_click)
                    if click_result.startswith("SUCCESS:"):
                        try:
                            click_data = json.loads(click_result[8:])
                            if click_data.get("success"):
                                print(f"✅ 点击Athena机器人成功")
                                time.sleep(3)  # 等待详情加载
                                return {"success": True, "clicked_athena": True}
                        except:
                            print("点击结果解析失败")
                    else:
                        print(f"点击失败: {click_result}")
                else:
                    print("无法确定点击选择器")
            else:
                print("未找到Athena机器人")

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
    else:
        print(f"探索群机器人页面失败: {result}")

    return {"success": False}


def check_javascript_storage() -> dict:
    """检查JavaScript全局变量和存储中是否有webhook信息"""
    print("\n=== 检查JavaScript存储 ===")

    js_check = """
    (function() {
        const results = {
            localStorage: {},
            sessionStorage: {},
            globalVariables: [],
            webhook_urls: []
        };

        // 检查localStorage
        try {
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                const value = localStorage.getItem(key);
                if (key && value && (key.includes('webhook') || key.includes('robot') ||
                                     value.includes('qyapi.weixin.qq.com'))) {
                    results.localStorage[key] = value.substring(0, 200);

                    // 检查是否包含webhook URL
                    const webhookPattern = /https:\\/\\/qyapi\\.weixin\\.qq\\.com\\/cgi-bin\\/webhook\\/send\\?key=[a-zA-Z0-9\\-]+/g;
                    const matches = value.match(webhookPattern);
                    if (matches) {
                        results.webhook_urls.push(...matches);
                    }
                }
            }
        } catch(e) {}

        // 检查sessionStorage
        try {
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                const value = sessionStorage.getItem(key);
                if (key && value && (key.includes('webhook') || key.includes('robot') ||
                                     value.includes('qyapi.weixin.qq.com'))) {
                    results.sessionStorage[key] = value.substring(0, 200);

                    const webhookPattern = /https:\\/\\/qyapi\\.weixin\\.qq\\.com\\/cgi-bin\\/webhook\\/send\\?key=[a-zA-Z0-9\\-]+/g;
                    const matches = value.match(webhookPattern);
                    if (matches) {
                        results.webhook_urls.push(...matches);
                    }
                }
            }
        } catch(e) {}

        // 检查全局变量
        const globalVars = ['webhook', 'robot', 'bot', 'key', 'WEBHOOK', 'ROBOT'];
        globalVars.forEach(varName => {
            try {
                if (window[varName] && typeof window[varName] === 'string') {
                    results.globalVariables.push({
                        name: varName,
                        value: window[varName].substring(0, 200)
                    });

                    const webhookPattern = /https:\\/\\/qyapi\\.weixin\\.qq\\.com\\/cgi-bin\\/webhook\\/send\\?key=[a-zA-Z0-9\\-]+/g;
                    if (webhookPattern.test(window[varName])) {
                        results.webhook_urls.push(window[varName]);
                    }
                }
            } catch(e) {}
        });

        return JSON.stringify(results);
    })();
    """

    result = execute_javascript(js_check)
    if result.startswith("SUCCESS:"):
        try:
            data = json.loads(result[8:])
            print(f"localStorage项: {len(data.get('localStorage', {}))}")
            print(f"sessionStorage项: {len(data.get('sessionStorage', {}))}")
            print(f"全局变量: {len(data.get('globalVariables', []))}")

            webhook_urls = data.get("webhook_urls", [])
            if webhook_urls:
                print(f"🎉 在存储中找到 {len(webhook_urls)} 个webhook URL!")
                for url in webhook_urls:
                    print(f"  • {url}")
                return {"success": True, "webhook_urls": webhook_urls}

            # 显示部分存储内容
            if data.get("localStorage"):
                print("\nlocalStorage相关项:")
                for key, value in list(data["localStorage"].items())[:3]:
                    print(f"  {key}: {value}")

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
    else:
        print(f"检查存储失败: {result}")

    return {"success": False}


if __name__ == "__main__":
    print("=" * 60)
    print("机器人元素点击探索器")
    print("=" * 60)

    try:
        # 1. 确保在应用管理页面
        if not navigate_to_apps():
            print("❌ 无法导航到应用管理页面，请确保已登录企业微信")
            exit(1)

        # 2. 查找并点击机器人应用
        click_result = find_and_click_robot()

        if not click_result.get("success"):
            print(f"\n❌ 机器人点击失败: {click_result.get('error', '未知错误')}")
            exit(1)

        print(f"\n✅ 机器人点击成功")
        print(f"   点击的元素: {click_result.get('clicked_element', {}).get('text', '未知')}")
        print(f"   新URL: {click_result.get('new_url', '未知')}")

        # 3. 扫描点击后的页面
        scan_result = scan_after_click()

        if scan_result.get("success"):
            print(f"\n🎉 成功找到webhook URL!")
            webhook_urls = scan_result.get("webhook_urls", [])
            for i, url in enumerate(webhook_urls):
                print(f"  {i+1}. {url}")

            # 验证webhook URL格式
            webhook_pattern = (
                r"https://qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=[a-zA-Z0-9\-]+"
            )
            valid_urls = [url for url in webhook_urls if re.match(webhook_pattern, url)]

            if valid_urls:
                print(f"\n✅ 有效的webhook URL: {valid_urls[0]}")
                print("\n下一步: 更新.env配置文件并测试连接")
            else:
                print("\n⚠️  找到的URL格式可能不正确")

        else:
            # 4. 检查是否在群机器人页面
            current_url = click_result.get("new_url", "")
            if "roomRobot" in current_url:
                print("\n在群机器人页面中，尝试深入探索...")
                robot_page_result = explore_room_robot_page()

                if robot_page_result.get("success"):
                    if robot_page_result.get("webhook_urls"):
                        print(f"\n🎉 在群机器人页面中找到webhook URL!")
                        webhook_urls = robot_page_result.get("webhook_urls", [])
                        for i, url in enumerate(webhook_urls):
                            print(f"  {i+1}. {url}")

                        # 验证webhook URL格式
                        webhook_pattern = r"https://qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=[a-zA-Z0-9\-]+"
                        valid_urls = [url for url in webhook_urls if re.match(webhook_pattern, url)]

                        if valid_urls:
                            print(f"\n✅ 有效的webhook URL: {valid_urls[0]}")
                            print("\n下一步: 更新.env配置文件并测试连接")
                            exit(0)
                    elif robot_page_result.get("clicked_athena"):
                        # 点击了Athena机器人，重新扫描
                        print("\n已点击Athena机器人，重新扫描页面...")
                        time.sleep(3)
                        new_scan = scan_after_click()

                        if new_scan.get("success"):
                            webhook_urls = new_scan.get("webhook_urls", [])
                            print(f"\n🎉 点击Athena机器人后找到webhook URL!")
                            for i, url in enumerate(webhook_urls):
                                print(f"  {i+1}. {url}")

                            # 验证webhook URL格式
                            webhook_pattern = r"https://qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=[a-zA-Z0-9\-]+"
                            valid_urls = [
                                url for url in webhook_urls if re.match(webhook_pattern, url)
                            ]

                            if valid_urls:
                                print(f"\n✅ 有效的webhook URL: {valid_urls[0]}")
                                print("\n下一步: 更新.env配置文件并测试连接")
                                exit(0)
                        else:
                            print("\n点击Athena机器人后仍未找到webhook URL")
            else:
                print("\n未在群机器人页面，检查模态框...")

            # 5. 检查JavaScript存储
            print("\n尝试检查JavaScript存储...")
            storage_result = check_javascript_storage()

            if storage_result.get("success"):
                webhook_urls = storage_result.get("webhook_urls", [])
                print(f"\n🎉 在JavaScript存储中找到webhook URL!")
                for i, url in enumerate(webhook_urls):
                    print(f"  {i+1}. {url}")

                # 验证webhook URL格式
                webhook_pattern = (
                    r"https://qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=[a-zA-Z0-9\-]+"
                )
                valid_urls = [url for url in webhook_urls if re.match(webhook_pattern, url)]

                if valid_urls:
                    print(f"\n✅ 有效的webhook URL: {valid_urls[0]}")
                    print("\n下一步: 更新.env配置文件并测试连接")
                    exit(0)

            # 6. 如果没有直接找到，检查模态框
            modal_result = explore_modal_if_exists()

            if not modal_result.get("success"):
                print("\n❌ 探索结束: 未找到webhook URL")
                print("\n可能的原因:")
                print("1. 机器人详情页面需要额外点击才能显示webhook")
                print("2. webhook URL在更深层的配置页面中")
                print("3. 需要不同的导航路径")
                print("\n备用方案:")
                print(
                    "1. 手动获取webhook URL后使用: python3 wecom_robot_creator.py update --webhook-url YOUR_URL"
                )
                print("2. 暂时使用邮件通知渠道")

    except Exception as e:
        print(f"\n❌ 探索过程出错: {e}")
        import traceback

        traceback.print_exc()
