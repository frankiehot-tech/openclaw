#!/usr/bin/env python3
"""测试页面探索功能"""

import json
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


def explore_navigation():
    """探索页面导航结构"""
    print("=== 探索企业微信页面导航结构 ===")

    # 1. 获取所有链接
    js_get_links = """
    (function() {
        const links = [];
        const allLinks = document.querySelectorAll('a');

        allLinks.forEach((link, index) => {
            const text = link.textContent.trim();
            const href = link.href || link.getAttribute('href') || '';
            const className = link.className || '';
            const id = link.id || '';

            if (text || href.includes('weixin.qq.com')) {
                links.push({
                    index: index,
                    text: text.substring(0, 50),
                    href: href.substring(0, 200),
                    className: className.substring(0, 100),
                    id: id,
                    tagName: link.tagName
                });
            }
        });

        return JSON.stringify({
            total_links: allLinks.length,
            filtered_links: links.length,
            links: links.slice(0, 30)  // 只返回前30个
        });
    })();
    """

    print("1. 获取页面链接...")
    result = execute_javascript(js_get_links)

    if result.startswith("SUCCESS:"):
        try:
            data = json.loads(result[8:])
            print(f"总共找到 {data['total_links']} 个链接")
            print(f"过滤后 {data['filtered_links']} 个相关链接")

            # 查找可能的导航链接
            nav_keywords = [
                "应用",
                "客户",
                "群",
                "机器人",
                "robot",
                "管理",
                "admin",
                "contact",
                "group",
            ]
            nav_links = []

            for link in data["links"]:
                text = link.get("text", "").lower()
                href = link.get("href", "").lower()

                for keyword in nav_keywords:
                    if keyword in text or keyword in href:
                        nav_links.append(link)
                        break

            print(f"\n找到 {len(nav_links)} 个可能的导航链接:")
            for link in nav_links[:10]:  # 显示前10个
                print(f"  • {link['text']} -> {link['href'][:80]}")

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"原始响应: {result[:200]}")
    else:
        print(f"执行JavaScript失败: {result}")

    # 2. 获取页面结构信息
    print("\n2. 分析页面结构...")
    js_structure = """
    (function() {
        const structure = {
            url: window.location.href,
            title: document.title,
            bodyClasses: document.body.className,
            hasSidebar: false,
            hasNav: false,
            sections: []
        };

        // 检查常见的企业微信元素
        const sidebarSelectors = [
            '.sidebar', '.side-nav', '.nav-sidebar', '.menu-sidebar',
            '[class*="sidebar"]', '[class*="side-nav"]', '[class*="menu"]'
        ];

        sidebarSelectors.forEach(selector => {
            if (document.querySelector(selector)) {
                structure.hasSidebar = true;
            }
        });

        // 查找主要区域
        const mainSelectors = ['main', '.main', '.content', '#content', '.app-main'];
        mainSelectors.forEach(selector => {
            const el = document.querySelector(selector);
            if (el) {
                structure.sections.push({
                    type: 'main',
                    selector: selector,
                    textPreview: el.textContent.substring(0, 200)
                });
            }
        });

        return JSON.stringify(structure);
    })();
    """

    result = execute_javascript(js_structure)
    if result.startswith("SUCCESS:"):
        try:
            structure = json.loads(result[8:])
            print(f"页面标题: {structure.get('title')}")
            print(f"页面URL: {structure.get('url')}")
            print(f"是否有侧边栏: {'是' if structure.get('hasSidebar') else '否'}")
            print(f"Body类名: {structure.get('bodyClasses', '无')}")

            if structure.get("sections"):
                print(f"找到 {len(structure['sections'])} 个主要内容区域")

        except json.JSONDecodeError:
            print(f"结构分析JSON解析错误")
    else:
        print(f"结构分析失败: {result}")

    # 3. 查找机器人相关元素
    print("\n3. 查找机器人相关元素...")
    js_find_robot = """
    (function() {
        const robotElements = [];
        const selectors = [
            '[class*="robot"]',
            '[id*="robot"]',
            '[data-testid*="robot"]',
            '*[class*="bot"]',
            '*[id*="bot"]',
            'a[href*="robot"]',
            'button:contains("机器人")',
            'div:contains("机器人")'
        ];

        // 查找匹配元素
        selectors.forEach(selector => {
            try {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    const text = el.textContent.trim().substring(0, 100);
                    if (text) {
                        robotElements.push({
                            selector: selector,
                            tagName: el.tagName,
                            text: text,
                            className: el.className || '',
                            id: el.id || ''
                        });
                    }
                });
            } catch(e) {
                // 忽略无效选择器
            }
        });

        // 也搜索文本内容
        const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        let node;
        while (node = walker.nextNode()) {
            if (node.textContent.includes('机器人') || node.textContent.includes('robot')) {
                const parent = node.parentElement;
                robotElements.push({
                    selector: 'text-content',
                    tagName: parent.tagName,
                    text: node.textContent.trim().substring(0, 100),
                    className: parent.className || '',
                    id: parent.id || ''
                });
            }
        }

        return JSON.stringify({
            found: robotElements.length,
            elements: robotElements.slice(0, 20)  // 只返回前20个
        });
    })();
    """

    result = execute_javascript(js_find_robot)
    if result.startswith("SUCCESS:"):
        try:
            robot_data = json.loads(result[8:])
            print(f"找到 {robot_data['found']} 个机器人相关元素")

            if robot_data["elements"]:
                print("前5个机器人相关元素:")
                for i, el in enumerate(robot_data["elements"][:5]):
                    print(f"  {i+1}. [{el['tagName']}] {el['text']}")
                    if el["className"]:
                        print(f"     类名: {el['className']}")
                    if el["id"]:
                        print(f"     ID: {el['id']}")
        except json.JSONDecodeError:
            print(f"机器人查找JSON解析错误")
    else:
        print(f"机器人查找失败: {result}")


if __name__ == "__main__":
    try:
        explore_navigation()
    except Exception as e:
        print(f"探索过程出错: {e}")
        import traceback

        traceback.print_exc()
