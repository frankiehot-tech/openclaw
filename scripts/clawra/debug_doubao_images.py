#!/usr/bin/env python3
"""
调试豆包图像URL模式，改进图像检测逻辑
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def capture_all_images():
    print("=== 捕获豆包页面所有图像信息 ===")

    doubao = DoubaoCLI()

    print("1. 打开豆包AI页面...")
    try:
        result = doubao.open_doubao_ai()
        print(f"✅ {result}")
        time.sleep(3)
    except Exception as e:
        print(f"❌ 打开AI页面失败: {e}")
        return None

    print("2. 进入AI创作界面...")
    try:
        click_result = doubao.enhanced.executor.click_button("AI 创作")
        if click_result.success:
            print(f"✅ 进入AI创作界面")
            time.sleep(3)
        else:
            print(f"❌ 进入AI创作界面失败: {click_result.error_message}")
            return None
    except Exception as e:
        print(f"❌ 进入AI创作界面失败: {e}")
        return None

    print("3. 发送测试图像生成请求...")
    try:
        test_prompt = "/draw 一只简单的测试猫，红色"
        result = doubao.enhanced.send_message_to_ai(test_prompt, use_enhanced=True)
        print(f"发送结果: {result}")
        time.sleep(3)  # 等待可能的下拉菜单
    except Exception as e:
        print(f"❌ 发送测试请求失败: {e}")
        # 继续，可能没有/draw命令

    print("4. 捕获所有图像数据...")

    capture_js = """
    (function() {
        var allImages = document.querySelectorAll('img');
        var imageData = [];

        allImages.forEach((img, idx) => {
            var src = img.src || '';
            var alt = img.alt || '';
            var className = img.className || '';
            var parent = img.parentElement;
            var parentClasses = '';
            var parentTag = '';

            // 获取父元素信息
            if (parent) {
                parentTag = parent.tagName;
                parentClasses = parent.className || '';
            }

            // 检查是否在消息区域
            var isInMessage = false;
            var current = img;
            while (current && current !== document.body) {
                if (current.classList &&
                    (current.classList.contains('message') ||
                     current.classList.contains('chat-message') ||
                     current.classList.contains('bubble') ||
                     current.getAttribute('data-message-id'))) {
                    isInMessage = true;
                    break;
                }
                current = current.parentElement;
            }

            imageData.push({
                index: idx,
                src: src.substring(0, 150),  // 截断长URL
                alt: alt,
                className: className.substring(0, 50),
                width: img.naturalWidth,
                height: img.naturalHeight,
                complete: img.complete,
                parentTag: parentTag,
                parentClasses: parentClasses.substring(0, 50),
                isInMessage: isInMessage,
                isVisible: img.offsetWidth > 0 && img.offsetHeight > 0,
                srcIncludesByteimg: src.includes('byteimg.com'),
                srcIncludesBytecdn: src.includes('bytecdn.com'),
                srcIncludesCloud: src.includes('cloud') || src.includes('tos'),
                srcIncludesFlow: src.includes('flow'),
                srcIncludesStatic: src.includes('static'),
                srcIncludesAvatar: src.includes('avatar'),
                srcIncludesLogo: src.includes('logo'),
                srcIncludesIcon: src.includes('icon')
            });
        });

        // 按尺寸排序
        imageData.sort((a, b) => (b.width * b.height) - (a.width * a.height));

        return JSON.stringify({
            totalImages: allImages.length,
            images: imageData,
            summary: {
                visibleImages: imageData.filter(img => img.isVisible).length,
                largeImages: imageData.filter(img => img.width > 300 && img.height > 300).length,
                inMessageImages: imageData.filter(img => img.isInMessage).length,
                byteimgImages: imageData.filter(img => img.srcIncludesByteimg).length,
                bytecdnImages: imageData.filter(img => img.srcIncludesBytecdn).length,
                cloudImages: imageData.filter(img => img.srcIncludesCloud).length,
                flowImages: imageData.filter(img => img.srcIncludesFlow).length
            }
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, capture_js)
        print(f"JavaScript执行结果长度: {len(result)}")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n=== 图像分析汇总 ===")
            print(f"总图像数: {data['totalImages']}")
            print(f"可见图像: {data['summary']['visibleImages']}")
            print(f"大尺寸图像(>300x300): {data['summary']['largeImages']}")
            print(f"消息区域内图像: {data['summary']['inMessageImages']}")
            print(f"包含byteimg.com: {data['summary']['byteimgImages']}")
            print(f"包含bytecdn.com: {data['summary']['bytecdnImages']}")
            print(f"包含cloud/tos: {data['summary']['cloudImages']}")
            print(f"包含flow: {data['summary']['flowImages']}")

            print(f"\n=== 前10大图像 ===")
            for img in data["images"][:10]:
                print(f"[{img['index']}] {img['width']}x{img['height']} - {img['src']}")
                print(f"    alt: '{img['alt']}', 类名: '{img['className']}'")
                print(f"    父元素: {img['parentTag']} '{img['parentClasses']}'")
                print(f"    在消息中: {img['isInMessage']}, 可见: {img['isVisible']}")
                print()

            return data
        else:
            print(f"原始输出: {result[:500]}...")
            return None

    except Exception as e:
        print(f"❌ 捕获图像失败: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_image_generation_and_capture():
    print("\n=== 测试图像生成并捕获 ===")

    doubao = DoubaoCLI()

    # 确保在AI创作界面
    print("1. 确保在AI创作界面...")

    # 发送明确的图像生成请求
    print("2. 发送图像生成请求...")
    prompt = "请生成一张卡通猫的图片，简单测试"
    try:
        result = doubao.enhanced.send_message_to_ai(prompt, use_enhanced=True)
        print(f"发送结果: {result}")
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return None

    print("3. 等待60秒让AI生成图像...")
    time.sleep(60)

    print("4. 再次捕获图像...")
    data = capture_all_images()

    if data:
        print("\n5. 分析可能的新图像...")
        # 可以比较前后图像差异，但这里简单显示

    return data


def suggest_detection_rules():
    print("\n=== 改进图像检测规则建议 ===")

    print("基于分析，建议以下检测规则：")
    print("1. 尺寸过滤：naturalWidth > 300 && naturalHeight > 300")
    print("2. URL模式：")
    print("   - 包含 'byteimg.com' 或 'bytecdn.com'")
    print("   - 包含 'cloud' 或 'tos'（可能是云存储）")
    print("   - 不包含 'avatar', 'logo', 'icon', 'static'")
    print("3. 位置过滤：")
    print("   - 在消息区域内（.message, .chat-message, .bubble）")
    print("   - 或者父元素有 data-message-id 属性")
    print("4. 可见性：offsetWidth > 0 && offsetHeight > 0")
    print("5. 时间戳：可以记录初始图像集合，然后比较新图像")

    print("\n示例JavaScript检测代码：")
    print("""
    function findGeneratedImages() {
        var allImages = document.querySelectorAll('img');
        var generated = [];

        allImages.forEach(img => {
            if (!img.complete) return;
            if (img.naturalWidth < 300 || img.naturalHeight < 300) return;

            var src = img.src || '';
            if (!src) return;

            // 过滤掉非生成图像
            if (src.includes('avatar') || src.includes('logo') ||
                src.includes('icon') || src.includes('static')) {
                return;
            }

            // 检查URL模式
            var isLikelyGenerated = src.includes('byteimg.com') ||
                                   src.includes('bytecdn.com') ||
                                   src.includes('cloud') ||
                                   src.includes('tos') ||
                                   src.includes('flow');

            if (!isLikelyGenerated) return;

            // 检查是否在消息区域
            var isInMessage = false;
            var parent = img.parentElement;
            while (parent && parent !== document.body) {
                if (parent.classList &&
                    (parent.classList.contains('message') ||
                     parent.classList.contains('chat-message') ||
                     parent.classList.contains('bubble') ||
                     parent.getAttribute('data-message-id'))) {
                    isInMessage = true;
                    break;
                }
                parent = parent.parentElement;
            }

            if (isInMessage) {
                generated.push({
                    src: src,
                    width: img.naturalWidth,
                    height: img.naturalHeight,
                    alt: img.alt || ''
                });
            }
        });

        return generated;
    }
    """)


if __name__ == "__main__":
    print("豆包图像URL模式调试")
    print("=" * 50)

    # 捕获初始图像
    initial_data = capture_all_images()

    if initial_data:
        print("\n✅ 初始图像捕获完成")

        # 等待用户决定是否测试生成
        response = input("\n是否测试图像生成并再次捕获？(y/n): ")
        if response.lower() == "y":
            test_image_generation_and_capture()

    # 提供改进建议
    suggest_detection_rules()

    print("\n完成调试！")
