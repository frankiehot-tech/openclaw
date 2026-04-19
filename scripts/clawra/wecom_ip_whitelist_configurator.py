#!/usr/bin/env python3
"""
企业微信IP白名单配置器 - 尝试自动化配置IP白名单
解决应用API的errcode 60020问题
"""

import json
import subprocess
import sys
import time
from pathlib import Path


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


def navigate_to_apps_page() -> bool:
    """导航到应用管理页面"""
    print("导航到应用管理页面...")

    js_navigate = """
    (function() {
        window.location.hash = '#/apps';
        return JSON.stringify({
            success: true,
            hash: window.location.hash,
            url: window.location.href
        });
    })();
    """

    result = execute_javascript(js_navigate)
    if result.startswith("SUCCESS:"):
        try:
            data = json.loads(result[8:])
            if data.get("success"):
                print(f"✅ 已导航到应用管理页面")
                print(f"   当前URL: {data.get('url', '未知')}")
                time.sleep(3)  # 等待页面加载
                return True
        except:
            pass

    print(f"❌ 导航失败: {result[:100]}")
    return False


def find_application_by_agent_id(agent_id: str = "1000002") -> dict:
    """查找特定AgentId的应用"""
    print(f"查找AgentId为 {agent_id} 的应用...")

    js_find_app = f"""
    (function() {{
        const results = {{
            apps: [],
            exact_matches: [],
            partial_matches: []
        }};

        // 方法1: 搜索所有文本中的AgentId
        const allText = document.body.textContent;
        if (allText.includes("{agent_id}")) {{
            // 查找包含AgentId的元素
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );

            let node;
            while (node = walker.nextNode()) {{
                if (node.textContent.includes("{agent_id}")) {{
                    const parent = node.parentElement;
                    const grandParent = parent ? parent.parentElement : null;

                    // 尝试找到最近的可点击元素（应用卡片）
                    let clickableElement = parent;
                    while (clickableElement &&
                           !['A', 'BUTTON', 'DIV', 'LI'].includes(clickableElement.tagName) &&
                           !clickableElement.className.includes('app') &&
                           !clickableElement.className.includes('card')) {{
                        clickableElement = clickableElement.parentElement;
                    }}

                    if (clickableElement) {{
                        results.apps.push({{
                            text: clickableElement.textContent.trim().substring(0, 200),
                            elementInfo: {{
                                tagName: clickableElement.tagName,
                                className: clickableElement.className || '',
                                id: clickableElement.id || ''
                            }},
                            containsAgentId: true,
                            context: node.textContent.trim().substring(0, 300)
                        }});
                    }}
                }}
            }}
        }}

        // 方法2: 查找应用卡片
        const appSelectors = [
            '.app_card', '.app-item', '.app_card_item',
            '[class*="app"]', '[class*="App"]',
            'div[data-app-id]', 'li[data-app-id]'
        ];

        appSelectors.forEach(selector => {{
            try {{
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {{
                    const text = el.textContent.trim();
                    if (text && text.length > 10) {{  // 合理的应用文本长度
                        const isMatch = text.includes("{agent_id}") || el.getAttribute('data-agentid') === "{agent_id}";

                        results.apps.push({{
                            text: text.substring(0, 200),
                            elementInfo: {{
                                tagName: el.tagName,
                                className: el.className || '',
                                id: el.id || '',
                                selector: selector
                            }},
                            containsAgentId: isMatch,
                            isClickable: el.tagName === 'A' || el.tagName === 'BUTTON' ||
                                        el.onclick || el.getAttribute('onclick')
                        }});

                        if (isMatch) {{
                            results.exact_matches.push(results.apps[results.apps.length-1]);
                        }}
                    }}
                }});
            }} catch(e) {{
                // 忽略无效选择器
            }}
        }});

        return JSON.stringify(results);
    }})();
    """

    result = execute_javascript(js_find_app)
    if result.startswith("SUCCESS:"):
        try:
            data = json.loads(result[8:])
            apps = data.get("apps", [])
            exact_matches = data.get("exact_matches", [])

            print(f"找到 {len(apps)} 个应用")
            print(f"其中 {len(exact_matches)} 个精确匹配AgentId")

            if exact_matches:
                print("\n精确匹配的应用:")
                for i, app in enumerate(exact_matches):
                    print(f"  {i+1}. {app.get('text', '')[:100]}...")
                    print(
                        f"     元素: {app.get('elementInfo', {}).get('tagName')} "
                        f"{app.get('elementInfo', {}).get('className', '')[:50]}"
                    )
                return exact_matches[0]  # 返回第一个匹配项

            # 如果没有精确匹配，返回所有应用
            if apps:
                print("\n找到的应用（可能包含目标）:")
                for i, app in enumerate(apps[:5]):  # 显示前5个
                    print(f"  {i+1}. {app.get('text', '')[:100]}...")
                return apps[0]

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")

    print(f"查找应用失败: {result[:200]}")
    return {}


def click_application(element_info: dict) -> bool:
    """点击应用元素进入详情页面"""
    print("尝试点击应用进入详情...")

    # 构建选择器
    selector = ""
    if element_info.get("id"):
        selector = f"#{element_info['id']}"
    elif element_info.get("className"):
        # 使用第一个类名
        classes = element_info["className"].split()
        if classes:
            selector = f".{classes[0]}"

    if not selector and element_info.get("selector"):
        selector = element_info["selector"]

    if not selector:
        print("无法确定选择器，尝试通用点击方法")
        selector = element_info.get("selector", "")

    if not selector:
        print("❌ 无法确定点击选择器")
        return False

    # 使用更简单的点击方法
    js_click = f"""
    (function() {{
        try {{
            const element = document.querySelector("{selector}");
            if (!element) {{
                return JSON.stringify({{success: false, error: "元素不存在: {selector}"}});
            }}

            console.log("点击应用元素:", element);

            // 记录点击前状态
            const beforeUrl = window.location.href;
            const beforeHash = window.location.hash;

            // 直接调用click方法
            if (typeof element.click === 'function') {{
                element.click();
            }}

            // 也触发鼠标事件
            const clickEvent = new MouseEvent('click', {{
                view: window,
                bubbles: true,
                cancelable: true
            }});
            element.dispatchEvent(clickEvent);

            // 尝试触发mousedown/mouseup事件
            const mouseDownEvent = new MouseEvent('mousedown', {{ bubbles: true, cancelable: true }});
            const mouseUpEvent = new MouseEvent('mouseup', {{ bubbles: true, cancelable: true }});
            element.dispatchEvent(mouseDownEvent);
            element.dispatchEvent(mouseUpEvent);

            // 返回点击结果
            return JSON.stringify({{
                success: true,
                beforeUrl: beforeUrl,
                beforeHash: beforeHash,
                elementClicked: element.textContent.trim().substring(0, 100),
                message: "点击已触发，页面将在几秒内加载"
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
                print(f"✅ 点击应用触发成功")
                print(f"   点击前URL: {data.get('beforeUrl', '未知')}")
                print(f"   点击前Hash: {data.get('beforeHash', '未知')}")
                print(f"   点击元素: {data.get('elementClicked', '未知')}")
                print(f"   提示: {data.get('message', '')}")
                time.sleep(5)  # 等待详情页面加载
                return True
            else:
                print(f"❌ 点击失败: {data.get('error', '未知错误')}")
        except Exception as e:
            print(f"点击结果解析失败: {result[:200]}, 错误: {e}")
    else:
        print(f"❌ 点击执行失败: {result}")

    return False


def find_ip_whitelist_settings() -> dict:
    """在应用详情页面查找IP白名单设置"""
    print("查找IP白名单设置...")

    js_find_ip_settings = """
    (function() {
        const results = {
            ip_settings: [],
            security_settings: [],
            input_fields: [],
            buttons: []
        };

        // 查找IP相关文本
        const ipKeywords = ['IP白名单', '可信IP', 'IP地址', '服务器IP', '安全IP',
                          'whitelist', 'IP whitelist', 'trusted IP'];
        const securityKeywords = ['安全设置', '安全中心', '安全配置', 'security', 'Safety'];

        const allText = document.body.textContent;

        ipKeywords.forEach(keyword => {
            if (allText.includes(keyword)) {
                // 查找包含关键词的元素
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );

                let node;
                while (node = walker.nextNode()) {
                    if (node.textContent.includes(keyword)) {
                        const parent = node.parentElement;

                        // 查找最近的设置区域
                        let settingElement = parent;
                        for (let i = 0; i < 5; i++) {  // 向上查找5层
                            if (settingElement &&
                                (settingElement.tagName === 'DIV' ||
                                 settingElement.tagName === 'SECTION' ||
                                 settingElement.tagName === 'FORM')) {
                                break;
                            }
                            settingElement = settingElement.parentElement;
                        }

                        if (settingElement) {
                            results.ip_settings.push({
                                keyword: keyword,
                                text: node.textContent.trim().substring(0, 200),
                                element: {
                                    tagName: settingElement.tagName,
                                    className: settingElement.className || '',
                                    text: settingElement.textContent.trim().substring(0, 300)
                                }
                            });
                        }
                    }
                }
            }
        });

        // 查找安全设置区域
        securityKeywords.forEach(keyword => {
            if (allText.includes(keyword)) {
                const elements = document.querySelectorAll('a, button, .tab-item, .nav-item');
                elements.forEach(el => {
                    const text = el.textContent.trim();
                    if (text.includes(keyword)) {
                        results.security_settings.push({
                            keyword: keyword,
                            text: text.substring(0, 100),
                            element: {
                                tagName: el.tagName,
                                className: el.className || '',
                                id: el.id || ''
                            }
                        });
                    }
                });
            }
        });

        // 查找IP输入框
        const inputs = document.querySelectorAll('input[type="text"], input[type="ip"], textarea');
        inputs.forEach(input => {
            const placeholder = input.placeholder || '';
            const label = input.previousElementSibling ?
                         input.previousElementSibling.textContent : '';
            const context = input.parentElement ?
                          input.parentElement.textContent.substring(0, 200) : '';

            if (placeholder.includes('IP') || label.includes('IP') || context.includes('IP')) {
                results.input_fields.push({
                    placeholder: placeholder,
                    label: label.trim(),
                    context: context,
                    element: {
                        tagName: input.tagName,
                        id: input.id || '',
                        className: input.className || '',
                        currentValue: input.value || ''
                    }
                });
            }
        });

        // 查找保存/添加按钮
        const buttons = document.querySelectorAll('button, .btn, .button');
        buttons.forEach(btn => {
            const text = btn.textContent.trim();
            const isSave = text.includes('保存') || text.includes('添加') ||
                          text.includes('确认') || text.includes('Submit') ||
                          text.includes('Save') || text.includes('Add');

            if (isSave) {
                results.buttons.push({
                    text: text.substring(0, 50),
                    element: {
                        tagName: btn.tagName,
                        className: btn.className || '',
                        id: btn.id || ''
                    }
                });
            }
        });

        return JSON.stringify(results);
    })();
    """

    result = execute_javascript(js_find_ip_settings)
    if result.startswith("SUCCESS:"):
        try:
            data = json.loads(result[8:])
            print(f"找到IP设置项: {len(data.get('ip_settings', []))}")
            print(f"找到安全设置: {len(data.get('security_settings', []))}")
            print(f"找到输入框: {len(data.get('input_fields', []))}")
            print(f"找到保存按钮: {len(data.get('buttons', []))}")

            return data

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")

    return {}


def configure_ip_whitelist(server_ip: str = "124.240.115.101") -> bool:
    """尝试配置IP白名单"""
    print(f"\n尝试配置IP白名单: {server_ip}")

    # 首先查找IP设置
    ip_settings = find_ip_whitelist_settings()

    if not ip_settings:
        print("❌ 未找到IP白名单设置")
        return False

    # 检查是否有输入框
    input_fields = ip_settings.get("input_fields", [])
    if input_fields:
        print(f"找到 {len(input_fields)} 个IP输入框")

        # 使用第一个输入框
        first_input = input_fields[0]
        input_element = first_input.get("element", {})

        # 尝试设置IP地址
        if input_element.get("id"):
            selector = f"#{input_element['id']}"
        elif input_element.get("className"):
            # 使用第一个类名
            classes = input_element["className"].split()
            if classes:
                selector = f".{classes[0]}"
        else:
            # 使用标签名和类型
            selector = f"input[type='text']"

        print(f"使用选择器: {selector}")

        # 设置IP地址
        js_set_ip = f"""
        (function() {{
            try {{
                const input = document.querySelector("{selector}");
                if (!input) {{
                    return JSON.stringify({{success: false, error: "输入框不存在: {selector}"}});
                }}

                // 设置IP地址
                input.value = "{server_ip}";

                // 触发change事件
                const changeEvent = new Event('change', {{bubbles: true}});
                input.dispatchEvent(changeEvent);

                // 触发input事件
                const inputEvent = new Event('input', {{bubbles: true}});
                input.dispatchEvent(inputEvent);

                return JSON.stringify({{
                    success: true,
                    valueSet: input.value,
                    placeholder: input.placeholder || ''
                }});

            }} catch (e) {{
                return JSON.stringify({{success: false, error: e.toString()}});
            }}
        }})();
        """

        result = execute_javascript(js_set_ip)
        if result.startswith("SUCCESS:"):
            try:
                data = json.loads(result[8:])
                if data.get("success"):
                    print(f"✅ IP地址设置成功: {data.get('valueSet')}")

                    # 查找并点击保存按钮
                    buttons = ip_settings.get("buttons", [])
                    if buttons:
                        first_button = buttons[0]
                        button_element = first_button.get("element", {})

                        if button_element.get("id"):
                            btn_selector = f"#{button_element['id']}"
                        elif button_element.get("className"):
                            btn_classes = button_element["className"].split()
                            if btn_classes:
                                btn_selector = f".{btn_classes[0]}"

                        if btn_selector:
                            print(f"点击保存按钮: {btn_selector}")

                            # 点击保存按钮
                            js_click_save = f"""
                            (function() {{
                                try {{
                                    const button = document.querySelector("{btn_selector}");
                                    if (!button) {{
                                        return JSON.stringify({{success: false, error: "按钮不存在: {btn_selector}"}});
                                    }}

                                    // 触发点击
                                    const clickEvent = new MouseEvent('click', {{
                                        view: window,
                                        bubbles: true,
                                        cancelable: true
                                    }});
                                    button.dispatchEvent(clickEvent);

                                    if (typeof button.click === 'function') {{
                                        button.click();
                                    }}

                                    return JSON.stringify({{
                                        success: true,
                                        buttonText: button.textContent.trim().substring(0, 50)
                                    }});

                                }} catch (e) {{
                                    return JSON.stringify({{success: false, error: e.toString()}});
                                }}
                            }})();
                            """

                            save_result = execute_javascript(js_click_save)
                            if save_result.startswith("SUCCESS:"):
                                print("✅ 保存按钮点击成功")
                                time.sleep(2)  # 等待保存完成
                                return True
                            else:
                                print(f"❌ 保存按钮点击失败: {save_result}")

                    print("⚠️  未找到保存按钮，IP地址已设置但可能需要手动保存")
                    return True

            except:
                print(f"IP设置结果解析失败: {result[:100]}")
    else:
        print("❌ 未找到IP输入框")

    return False


def test_application_api() -> dict:
    """测试应用API是否正常工作"""
    print("\n测试应用API...")

    # 使用verify_wecom_credentials.py中的测试函数
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("❌ 找不到.env文件")
        return {"success": False, "error": "找不到.env文件"}

    # 加载环境变量
    env_vars = {}
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

    corp_id = env_vars.get("WECOM_CORPID", "")
    secret = env_vars.get("WECOM_SECRET", "")
    agent_id = env_vars.get("WECOM_AGENTID", "")

    if not corp_id or not secret or not agent_id:
        print("❌ 缺少企业微信应用凭据")
        return {"success": False, "error": "缺少凭据"}

    import requests

    # 获取access_token
    token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={secret}"

    try:
        response = requests.get(token_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("errcode") == 0:
                access_token = data.get("access_token")

                # 测试发送消息
                send_url = (
                    f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
                )
                payload = {
                    "touser": "@all",
                    "msgtype": "text",
                    "agentid": agent_id,
                    "text": {
                        "content": "IP白名单配置测试 - 如果收到此消息，说明IP白名单已配置成功"
                    },
                    "safe": 0,
                }

                send_response = requests.post(send_url, json=payload, timeout=10)
                if send_response.status_code == 200:
                    send_data = send_response.json()

                    if send_data.get("errcode") == 0:
                        return {
                            "success": True,
                            "message": "✅ 应用API测试成功！IP白名单已生效",
                            "response": send_data,
                        }
                    else:
                        return {
                            "success": False,
                            "error_code": send_data.get("errcode"),
                            "error_msg": send_data.get("errmsg"),
                            "message": f"❌ 消息发送失败: {send_data.get('errmsg')}",
                        }
                else:
                    return {"success": False, "error": f"HTTP请求失败: {send_response.status_code}"}
            else:
                return {
                    "success": False,
                    "error_code": data.get("errcode"),
                    "error_msg": data.get("errmsg"),
                    "message": f"❌ 获取access_token失败: {data.get('errmsg')}",
                }
        else:
            return {"success": False, "error": f"HTTP请求失败: {response.status_code}"}

    except Exception as e:
        return {"success": False, "error": str(e), "message": f"❌ 测试过程出错: {e}"}


def main():
    """主函数"""
    print("=" * 60)
    print("企业微信IP白名单配置器")
    print("=" * 60)
    print("目标: 解决应用API的IP白名单问题 (errcode 60020)")
    print(f"服务器IP: 124.240.115.101")
    print("=" * 60)

    print("\n注意: 此工具尝试自动化配置IP白名单")
    print("      如果自动化失败，请参考手动配置指南")
    print("      wecom_final_solution.md")

    try:
        # 步骤1: 导航到应用管理页面
        if not navigate_to_apps_page():
            print("\n❌ 无法导航到应用管理页面")
            print("请确保:")
            print("1. Safari浏览器已打开并登录企业微信")
            print("2. 当前页面是企业微信管理后台")
            print("3. 侧边栏可见")
            return

        # 步骤2: 查找应用
        app_info = find_application_by_agent_id("1000002")
        if not app_info:
            print("\n❌ 未找到AgentId为1000002的应用")
            print("请手动查找应用并配置IP白名单")
            return

        # 步骤3: 点击进入应用详情
        if not click_application(app_info.get("elementInfo", {})):
            print("\n❌ 无法进入应用详情页面")
            print("请手动点击应用进入详情")
            return

        # 步骤4: 配置IP白名单
        if configure_ip_whitelist():
            print("\n✅ IP白名单配置尝试完成")
            print("等待5秒后测试配置...")
            time.sleep(5)
        else:
            print("\n⚠️  IP白名单自动化配置失败")
            print("可能需要手动配置:")
            print("1. 在应用详情页面找到'安全设置'或'IP白名单'")
            print("2. 添加IP: 124.240.115.101")
            print("3. 保存配置")

        # 步骤5: 测试配置
        print("\n" + "=" * 60)
        print("测试配置结果")
        print("=" * 60)

        test_result = test_application_api()

        if test_result.get("success"):
            print(test_result.get("message", "测试成功"))
            print("\n🎉 企业微信应用API现在可以正常工作!")
            print("可以使用以下方式测试通知:")
            print("  python3 test_notification_channels_final.py")
        else:
            print(test_result.get("message", "测试失败"))
            print(f"错误代码: {test_result.get('error_code', '未知')}")
            print(f"错误信息: {test_result.get('error_msg', '未知')}")

            if test_result.get("error_code") == 60020:
                print("\n❌ IP白名单仍然未生效")
                print("请手动完成IP白名单配置")
                print("参考: wecom_final_solution.md - 方案1")

    except Exception as e:
        print(f"\n❌ 配置过程出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
