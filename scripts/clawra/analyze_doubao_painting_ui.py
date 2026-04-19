#!/usr/bin/env python3
"""
详细分析豆包AI绘画界面结构
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def analyze_painting_interface():
    print("=== 详细分析豆包AI绘画界面 ===")

    # 创建实例
    doubao = DoubaoCLI()

    print("1. 打开豆包AI页面...")
    try:
        result = doubao.open_doubao_ai()
        print(f"✅ {result}")
        time.sleep(3)  # 等待页面加载
    except Exception as e:
        print(f"❌ 打开AI页面失败: {e}")
        return False

    print("\n2. 点击'AI 创作'按钮进入创作界面...")
    try:
        # 点击AI创作按钮
        click_result = doubao.enhanced.executor.click_button("AI 创作")
        if click_result.success:
            print(f"✅ 点击成功: {click_result.output}")
            time.sleep(3)  # 等待界面加载
        else:
            print(f"❌ 点击失败: {click_result.error_message}")
            return False
    except Exception as e:
        print(f"❌ 点击AI创作按钮失败: {e}")
        return False

    print("\n3. 分析界面结构和功能...")

    # 详细分析界面的JavaScript代码
    analyze_js = """
    (function() {
        // 捕获完整的DOM结构进行分析
        var analysis = {
            inputs: [],
            buttons: [],
            images: [],
            iframes: [],
            sections: [],
            specialElements: []
        };

        // 查找所有输入元素
        var inputElements = document.querySelectorAll('textarea, input[type="text"], input[type="search"], input[type="email"], [contenteditable="true"]');
        inputElements.forEach((el, idx) => {
            if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                analysis.inputs.push({
                    index: idx,
                    tagName: el.tagName,
                    type: el.type || 'N/A',
                    placeholder: el.placeholder || '',
                    id: el.id || '',
                    className: el.className.substring(0, 30),
                    value: el.value || '',
                    name: el.name || '',
                    isVisible: el.offsetWidth > 0 && el.offsetHeight > 0,
                    selector: generateSelector(el)
                });
            }
        });

        // 查找所有按钮
        var buttonElements = document.querySelectorAll('button, [role="button"], [onclick], .btn, .button');
        buttonElements.forEach((el, idx) => {
            if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                var text = (el.textContent || el.value || el.innerText || '').trim();
                analysis.buttons.push({
                    index: idx,
                    tagName: el.tagName,
                    text: text.substring(0, 100),
                    id: el.id || '',
                    className: el.className.substring(0, 30),
                    type: el.type || '',
                    isVisible: el.offsetWidth > 0 && el.offsetHeight > 0,
                    selector: generateSelector(el),
                    hasClickHandler: !!(el.onclick || el.getAttribute('onclick'))
                });
            }
        });

        // 查找所有图像
        var imgElements = document.querySelectorAll('img, [data-image], .image, .img');
        imgElements.forEach((el, idx) => {
            if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                analysis.images.push({
                    index: idx,
                    tagName: el.tagName,
                    src: el.src || el.getAttribute('src') || '',
                    alt: el.alt || el.getAttribute('alt') || '',
                    className: el.className.substring(0, 30),
                    isVisible: el.offsetWidth > 0 && el.offsetHeight > 0,
                    selector: generateSelector(el)
                });
            }
        });

        // 查找iframe和嵌入内容
        var iframeElements = document.querySelectorAll('iframe, embed, object');
        iframeElements.forEach((el, idx) => {
            analysis.iframes.push({
                index: idx,
                tagName: el.tagName,
                src: el.src || el.getAttribute('src') || '',
                className: el.className.substring(0, 30),
                isVisible: el.offsetWidth > 0 && el.offsetHeight > 0
            });
        });

        // 查找可能的AI绘画功能区域
        var specialSelectors = [
            '[data-testid*="image"]',
            '[data-testid*="paint"]',
            '[data-testid*="generate"]',
            '[data-testid*="draw"]',
            '[aria-label*="image"]',
            '[aria-label*="paint"]',
            '[aria-label*="generate"]',
            '[aria-label*="draw"]',
            '.image-generation',
            '.text-to-image',
            '.ai-drawing',
            '.drawing-tool',
            '.painting-interface'
        ];

        specialSelectors.forEach(selector => {
            try {
                var elements = document.querySelectorAll(selector);
                elements.forEach((el, idx) => {
                    if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                        var text = (el.textContent || el.value || el.innerText || '').trim();
                        analysis.specialElements.push({
                            selector: selector,
                            tagName: el.tagName,
                            text: text.substring(0, 100),
                            className: el.className.substring(0, 30),
                            isVisible: el.offsetWidth > 0 && el.offsetHeight > 0
                        });
                    }
                });
            } catch(e) {
                // 忽略无效选择器
            }
        });

        // 查找所有区域/容器
        var sectionKeywords = ['绘画', '画图', '生成', '创作', 'image', 'draw', 'paint', 'generate'];
        var allElements = document.querySelectorAll('div, section, main, article, aside, header, footer');
        allElements.forEach((el, idx) => {
            if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                var text = (el.textContent || el.innerText || '').toLowerCase();
                var hasKeyword = sectionKeywords.some(keyword => text.includes(keyword));
                var id = el.id || '';
                var className = el.className || '';

                if (hasKeyword || id.includes('image') || id.includes('draw') || id.includes('paint') ||
                    className.includes('image') || className.includes('draw') || className.includes('paint')) {

                    analysis.sections.push({
                        index: idx,
                        tagName: el.tagName,
                        id: id,
                        className: className.substring(0, 30),
                        text: (el.textContent || el.innerText || '').trim().substring(0, 200),
                        isVisible: el.offsetWidth > 0 && el.offsetHeight > 0,
                        selector: generateSelector(el)
                    });
                }
            }
        });

        // 辅助函数：生成CSS选择器
        function generateSelector(element) {
            if (element.id) return '#' + element.id;

            var path = [];
            while (element && element.nodeType === Node.ELEMENT_NODE) {
                var selector = element.tagName.toLowerCase();
                if (element.className && typeof element.className === 'string') {
                    var classes = element.className.split(/\s+/).filter(c => c.length > 0);
                    if (classes.length > 0) {
                        selector += '.' + classes.join('.');
                    }
                }

                // 添加索引区分
                var parent = element.parentNode;
                if (parent) {
                    var siblings = Array.from(parent.children).filter(child =>
                        child.tagName === element.tagName &&
                        (child.className === element.className ||
                         (child.className && element.className &&
                          child.className.toString() === element.className.toString()))
                    );
                    if (siblings.length > 1) {
                        var index = siblings.indexOf(element) + 1;
                        selector += ':nth-child(' + index + ')';
                    }
                }

                path.unshift(selector);
                if (element.id) break; // 有ID就停止
                element = element.parentNode;
            }

            return path.length > 0 ? path.join(' > ') : '';
        }

        // 分析页面标题和元数据
        analysis.pageTitle = document.title;
        analysis.pageURL = window.location.href;
        analysis.viewportWidth = window.innerWidth;
        analysis.viewportHeight = window.innerHeight;

        return JSON.stringify(analysis, null, 2);

    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, analyze_js)
        print(f"JavaScript执行结果: {result[:500]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n=== 界面分析报告 ===")
            print(f"页面标题: {data.get('pageTitle', 'N/A')}")
            print(f"页面URL: {data.get('pageURL', 'N/A')}")
            print(f"视口尺寸: {data['viewportWidth']}x{data['viewportHeight']}")

            print(f"\n输入框数量: {len(data['inputs'])}")
            if data["inputs"]:
                print("输入框详情:")
                for inp in data["inputs"][:5]:  # 显示前5个
                    print(f"  [{inp['index']}] {inp['tagName']}[type={inp['type']}]:")
                    print(f"     占位符: '{inp['placeholder']}'")
                    print(f"     值: '{inp['value']}'")
                    print(f"     选择器: {inp['selector']}")

            print(f"\n按钮数量: {len(data['buttons'])}")
            if data["buttons"]:
                print("按钮详情 (前10个):")
                for btn in data["buttons"][:10]:
                    print(f"  [{btn['index']}] {btn['tagName']}: '{btn['text']}'")
                    print(f"     选择器: {btn['selector']}")
                    print(f"     有点击处理器: {btn['hasClickHandler']}")

            print(f"\n图像数量: {len(data['images'])}")
            if data["images"]:
                print("图像详情 (前5个):")
                for img in data["images"][:5]:
                    print(f"  [{img['index']}] {img['tagName']}: src='{img['src'][:50]}...'")

            print(f"\n特殊元素数量: {len(data['specialElements'])}")
            if data["specialElements"]:
                print("特殊元素详情:")
                for el in data["specialElements"]:
                    print(f"  - {el['selector']}: {el['tagName']} - '{el['text']}'")

            print(f"\n绘画相关区域: {len(data['sections'])}")
            if data["sections"]:
                print("相关区域详情:")
                for section in data["sections"][:3]:
                    print(f"  [{section['index']}] {section['tagName']}[id={section['id']}]:")
                    print(f"     文本: {section['text'][:100]}...")
                    print(f"     选择器: {section['selector']}")

            # 保存分析结果到文件
            with open("doubao_painting_analysis.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 分析结果已保存到: doubao_painting_analysis.json")

            return True

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return False


def test_painting_workflow():
    print("\n=== 测试绘画工作流 ===")

    doubao = DoubaoCLI()

    # 测试不同的绘画命令格式
    painting_commands = [
        "/draw 一只可爱的猫咪",
        "生成一张风景图片",
        "画一幅山水画",
        "create an image of a sunset",
        "文生图：一只小狗在草地上玩耍",
    ]

    for i, cmd in enumerate(painting_commands):
        print(f"\n测试命令 {i+1}: {cmd}")
        try:
            result = doubao.enhanced.send_message_to_ai(cmd, use_enhanced=True)
            print(f"发送结果: {result}")
            time.sleep(5)  # 等待响应

            # 检查是否有图像生成
            check_js = """
            (function() {
                // 查找最新生成的图像
                var images = document.querySelectorAll('img');
                var recentImages = [];
                var now = Date.now();

                images.forEach(img => {
                    // 检查是否是新加载的图像
                    if (img.complete && img.naturalWidth > 0) {
                        recentImages.push({
                            src: img.src.substring(0, 100),
                            alt: img.alt || '',
                            width: img.naturalWidth,
                            height: img.naturalHeight
                        });
                    }
                });

                return JSON.stringify({
                    totalImages: images.length,
                    recentImages: recentImages,
                    recentCount: recentImages.length
                });
            })()
            """

            result2 = doubao.execute_javascript(1, 1, check_js)
            print(f"图像检查: {result2}")

        except Exception as e:
            print(f"❌ 命令执行失败: {e}")


if __name__ == "__main__":
    print("豆包AI绘画界面详细分析")
    print("=" * 50)

    if analyze_painting_interface():
        print("\n✅ 界面分析完成")

        # 询问是否测试工作流
        try:
            response = input("\n是否测试绘画工作流？(y/n): ")
            if response.lower() == "y":
                test_painting_workflow()
        except EOFError:
            print("\n在非交互式环境中运行，跳过工作流测试")
    else:
        print("\n❌ 界面分析失败")
        sys.exit(1)
