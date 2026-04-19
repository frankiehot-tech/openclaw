#!/usr/bin/env python3
"""
探索豆包AI多模态功能
- 图像上传功能
- 图生文能力
- 文生视频能力
- 多模态对话
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def explore_multimodal_features():
    print("=== 探索豆包AI多模态功能 ===")

    # 创建实例
    doubao = DoubaoCLI()

    print("1. 打开豆包AI页面...")
    try:
        result = doubao.open_doubao_ai()
        print(f"✅ {result}")
        time.sleep(3)
    except Exception as e:
        print(f"❌ 打开AI页面失败: {e}")
        return False

    print("\n2. 探索图像上传功能...")

    # 查找图像上传相关元素
    explore_upload_js = """
    (function() {
        // 查找文件上传输入框
        var fileInputs = document.querySelectorAll('input[type="file"]');
        var fileInputData = Array.from(fileInputs).map((input, idx) => ({
            index: idx,
            accept: input.accept || '',
            multiple: input.multiple,
            className: input.className.substring(0, 30),
            isVisible: input.offsetWidth > 0 && input.offsetHeight > 0
        }));

        // 查找图像上传按钮
        var uploadButtons = document.querySelectorAll('button, [role="button"], [data-testid*="upload"], [aria-label*="上传"], [aria-label*="图片"], [aria-label*="image"]');
        var buttonData = Array.from(uploadButtons).map((btn, idx) => ({
            index: idx,
            text: (btn.textContent || btn.innerText || '').trim(),
            ariaLabel: btn.getAttribute('aria-label') || '',
            className: btn.className.substring(0, 30),
            isVisible: btn.offsetWidth > 0 && btn.offsetHeight > 0,
            isUploadRelated: (btn.textContent || btn.innerText || '').toLowerCase().includes('上传') ||
                            (btn.getAttribute('aria-label') || '').toLowerCase().includes('upload') ||
                            (btn.getAttribute('aria-label') || '').toLowerCase().includes('image') ||
                            (btn.getAttribute('aria-label') || '').toLowerCase().includes('图片')
        }));

        // 查找图像预览区域
        var previewAreas = document.querySelectorAll('[data-testid*="preview"], .preview, .image-preview, .upload-preview');
        var previewData = Array.from(previewAreas).map((area, idx) => ({
            index: idx,
            className: area.className.substring(0, 50),
            hasImages: area.querySelectorAll('img').length > 0,
            isVisible: area.offsetWidth > 0 && area.offsetHeight > 0
        }));

        return JSON.stringify({
            fileInputs: fileInputData,
            uploadButtons: buttonData,
            previewAreas: previewData,
            hasFileInput: fileInputs.length > 0,
            hasUploadButton: buttonData.some(b => b.isUploadRelated && b.isVisible),
            hasPreviewArea: previewAreas.length > 0
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, explore_upload_js)
        print(f"JavaScript执行结果: {result[:500]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n=== 图像上传功能分析 ===")
            print(f"有文件输入框: {data['hasFileInput']}")
            print(f"有上传按钮: {data['hasUploadButton']}")
            print(f"有预览区域: {data['hasPreviewArea']}")

            if data["fileInputs"]:
                print(f"\n文件输入框:")
                for inp in data["fileInputs"]:
                    print(
                        f"  - [{inp['index']}] accept={inp['accept']}, multiple={inp['multiple']}"
                    )

            if data["uploadButtons"]:
                print(f"\n上传相关按钮 (过滤后):")
                upload_related = [
                    b for b in data["uploadButtons"] if b["isUploadRelated"] and b["isVisible"]
                ]
                for btn in upload_related[:5]:
                    print(
                        f"  - [{btn['index']}] 文本='{btn['text']}', aria-label='{btn['ariaLabel']}'"
                    )

            return data
        else:
            print(f"原始输出: {result}")
            return None

    except Exception as e:
        print(f"❌ 探索上传功能失败: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_image_to_text():
    print("\n=== 测试图生文功能 ===")

    doubao = DoubaoCLI()

    # 如果有图像上传功能，尝试上传图像
    print("1. 检查图生文功能...")

    # 查找可能的图生文命令或按钮
    find_image_to_text_js = """
    (function() {
        // 查找图生文相关元素
        var imageToTextElements = document.querySelectorAll('[data-testid*="image-to-text"], [aria-label*="图生文"], [aria-label*="image to text"], button:contains("图片描述"), button:contains("分析图片")');
        var elements = Array.from(imageToTextElements).map((el, idx) => ({
            index: idx,
            tagName: el.tagName,
            text: (el.textContent || el.innerText || '').trim(),
            ariaLabel: el.getAttribute('aria-label') || '',
            className: el.className.substring(0, 30),
            isVisible: el.offsetWidth > 0 && el.offsetHeight > 0
        }));

        // 检查是否有相关命令提示
        var textarea = document.querySelector('textarea');
        var placeholder = textarea ? textarea.placeholder || '' : '';

        // 查找命令建议
        var commandSuggestions = document.querySelectorAll('[role="option"], .suggestion-item, .command-suggestion');
        var suggestions = Array.from(commandSuggestions).map((s, idx) => ({
            index: idx,
            text: (s.textContent || s.innerText || '').trim(),
            isVisible: s.offsetWidth > 0 && s.offsetHeight > 0
        }));

        return JSON.stringify({
            imageToTextElements: elements,
            textareaPlaceholder: placeholder,
            commandSuggestions: suggestions.filter(s => s.isVisible),
            hasImageToText: elements.some(el => el.isVisible),
            hasCommandSuggestions: suggestions.some(s => s.isVisible)
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, find_image_to_text_js)
        print(f"JavaScript执行结果: {result[:300]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n图生文功能分析:")
            print(f"有图生文元素: {data['hasImageToText']}")
            print(f"输入框占位符: {data['textareaPlaceholder']}")
            print(f"有命令建议: {data['hasCommandSuggestions']}")

            if data["imageToTextElements"]:
                print(f"\n图生文元素:")
                for el in data["imageToTextElements"]:
                    if el["isVisible"]:
                        print(
                            f"  - {el['tagName']}: '{el['text']}' (aria-label: '{el['ariaLabel']}')"
                        )

            if data["commandSuggestions"]:
                print(f"\n命令建议:")
                for s in data["commandSuggestions"][:5]:
                    print(f"  - {s['text']}")

            # 尝试发送图生文请求
            if data["hasImageToText"] or "/image" in data["textareaPlaceholder"].toLowerCase():
                print("\n尝试发送图生文请求...")
                test_prompt = "请描述这张图片的内容"
                result_msg = doubao.enhanced.send_message_to_ai(test_prompt, use_enhanced=True)
                print(f"发送结果: {result_msg}")

                print("等待20秒查看响应...")
                time.sleep(20)

                # 检查响应
                check_response_js = """
                (function() {
                    var messages = document.querySelectorAll('[data-message-id], .message, .chat-message');
                    var lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;

                    if (lastMessage) {
                        var text = (lastMessage.textContent || lastMessage.innerText || '').trim();
                        var hasImages = lastMessage.querySelectorAll('img').length > 0;

                        return JSON.stringify({
                            success: true,
                            text: text.substring(0, 200),
                            hasImages: hasImages,
                            isFromAssistant: lastMessage.classList.contains('assistant-message') ||
                                            lastMessage.getAttribute('data-role') === 'assistant' ||
                                            text.length > 0 && !text.includes('请描述这张图片的内容')
                        });
                    }

                    return JSON.stringify({
                        success: false,
                        message: "没有找到消息"
                    });
                })()
                """

                result2 = doubao.execute_javascript(1, 1, check_response_js)
                print(f"响应检查: {result2}")

                if "JavaScript执行结果: " in result2:
                    json_str2 = result2.split("JavaScript执行结果: ", 1)[1]
                    response = json.loads(json_str2)

                    if response.get("success") and response.get("isFromAssistant"):
                        print(f"✅ 收到助手响应: {response['text']}")
                        return True
                    else:
                        print(f"⚠️ 未收到助手响应: {response.get('message', '未知')}")
                        return False
            else:
                print("⚠️ 未发现图生文功能")
                return False

        else:
            print(f"原始输出: {result}")
            return False

    except Exception as e:
        print(f"❌ 测试图生文失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def explore_video_generation():
    print("\n=== 探索视频生成功能 ===")

    doubao = DoubaoCLI()

    # 查找视频生成相关元素
    explore_video_js = """
    (function() {
        // 查找视频生成相关元素
        var videoElements = document.querySelectorAll('[data-testid*="video"], [aria-label*="视频"], [aria-label*="video"], button:contains("视频"), button:contains("生成视频")');
        var elements = Array.from(videoElements).map((el, idx) => ({
            index: idx,
            tagName: el.tagName,
            text: (el.textContent || el.innerText || '').trim(),
            ariaLabel: el.getAttribute('aria-label') || '',
            className: el.className.substring(0, 30),
            isVisible: el.offsetWidth > 0 && el.offsetHeight > 0
        }));

        // 检查命令建议中的视频相关命令
        var allElements = document.body.querySelectorAll('*');
        var videoKeywords = ['视频', 'video', '生成视频', 'video generation', '文生视频', 'text to video'];
        var videoRelated = [];

        allElements.forEach(el => {
            if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                var text = (el.textContent || el.innerText || '').toLowerCase();
                var ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();

                if (videoKeywords.some(keyword => text.includes(keyword) || ariaLabel.includes(keyword))) {
                    videoRelated.push({
                        tagName: el.tagName,
                        text: (el.textContent || el.innerText || '').trim().substring(0, 50),
                        ariaLabel: el.getAttribute('aria-label') || '',
                        className: el.className.substring(0, 30)
                    });
                }
            }
        });

        return JSON.stringify({
            videoElements: elements,
            videoRelatedElements: videoRelated.slice(0, 10),
            hasVideoElements: elements.some(el => el.isVisible),
            hasVideoRelated: videoRelated.length > 0
        }, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, explore_video_js)
        print(f"JavaScript执行结果: {result[:300]}...")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n视频生成功能分析:")
            print(f"有视频元素: {data['hasVideoElements']}")
            print(f"有视频相关元素: {data['hasVideoRelated']}")

            if data["videoElements"]:
                print(f"\n视频生成元素:")
                for el in data["videoElements"]:
                    if el["isVisible"]:
                        print(f"  - {el['tagName']}: '{el['text']}'")

            if data["videoRelatedElements"]:
                print(f"\n视频相关元素:")
                for el in data["videoRelatedElements"][:5]:
                    print(f"  - {el['tagName']}: '{el['text']}' (aria-label: '{el['ariaLabel']}')")

            # 尝试发送视频生成请求
            print("\n尝试发送视频生成请求...")
            video_prompt = "/video 生成一个美丽的风景视频，有瀑布和森林"
            result_msg = doubao.enhanced.send_message_to_ai(video_prompt, use_enhanced=True)
            print(f"发送结果: {result_msg}")

            print("等待30秒查看响应...")
            time.sleep(30)

            # 检查是否有视频相关响应
            check_video_response_js = """
            (function() {
                // 查找视频元素
                var videos = document.querySelectorAll('video');
                var videoData = Array.from(videos).map((vid, idx) => ({
                    index: idx,
                    src: vid.src.substring(0, 100),
                    poster: vid.poster || '',
                    width: vid.videoWidth,
                    height: vid.videoHeight,
                    duration: vid.duration,
                    isPlaying: !vid.paused
                }));

                // 查找视频链接
                var links = document.querySelectorAll('a');
                var videoLinks = Array.from(links).filter(link => {
                    var href = link.href || '';
                    return href.includes('.mp4') || href.includes('.mov') || href.includes('.avi') ||
                           href.includes('video') || href.includes('视频');
                }).map((link, idx) => ({
                    index: idx,
                    text: (link.textContent || link.innerText || '').trim(),
                    href: link.href.substring(0, 100)
                }));

                return JSON.stringify({
                    videos: videoData,
                    videoLinks: videoLinks,
                    hasVideos: videos.length > 0,
                    hasVideoLinks: videoLinks.length > 0
                });
            })()
            """

            result2 = doubao.execute_javascript(1, 1, check_video_response_js)
            print(f"视频响应检查: {result2}")

            if "JavaScript执行结果: " in result2:
                json_str2 = result2.split("JavaScript执行结果: ", 1)[1]
                response = json.loads(json_str2)

                if response.get("hasVideos") or response.get("hasVideoLinks"):
                    print(f"🎉 检测到视频元素!")
                    if response["videos"]:
                        print(f"视频数量: {len(response['videos'])}")
                    if response["videoLinks"]:
                        print(f"视频链接数量: {len(response['videoLinks'])}")
                    return True
                else:
                    print(f"⚠️ 未检测到视频元素")
                    return False

        else:
            print(f"原始输出: {result}")
            return False

    except Exception as e:
        print(f"❌ 探索视频生成失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("豆包AI多模态功能探索")
    print("=" * 50)

    # 探索图像上传功能
    upload_data = explore_multimodal_features()

    if upload_data:
        print("\n✅ 多模态功能探索完成")

        # 根据探索结果决定下一步
        if upload_data.get("hasFileInput") or upload_data.get("hasUploadButton"):
            print("\n发现图像上传功能，测试图生文...")
            test_image_to_text()
        else:
            print("\n未发现图像上传功能，直接测试图生文...")
            test_image_to_text()

        # 探索视频生成功能
        print("\n探索视频生成功能...")
        explore_video_generation()
    else:
        print("\n❌ 多模态功能探索失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
