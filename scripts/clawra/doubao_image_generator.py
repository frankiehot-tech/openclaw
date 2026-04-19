#!/usr/bin/env python3
"""
豆包AI图像生成器 v1.0
基于已验证的豆包CLI实现文生图功能
"""

import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


@dataclass
class ImageGenerationResult:
    """图像生成结果"""

    success: bool
    image_urls: List[str]
    prompt: str
    style: str
    timestamp: datetime
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "image_urls": self.image_urls,
            "prompt": self.prompt,
            "style": self.style,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
            "metadata": self.metadata or {},
        }


class DoubaoImageGenerator:
    """
    豆包AI图像生成器

    功能：
    1. 启动豆包应用
    2. 打开AI创作界面
    3. 发送图像生成提示
    4. 等待并获取生成结果
    5. 下载生成的图像（可选）
    """

    def __init__(self, auto_start_app: bool = True):
        """
        初始化图像生成器

        Args:
            auto_start_app: 是否自动启动豆包应用
        """
        self.doubao = DoubaoCLI()
        self.auto_start_app = auto_start_app
        self.initialized = False

    def ensure_doubao_running(self) -> bool:
        """确保豆包应用正在运行"""
        print("检查豆包应用状态...")

        try:
            # 检查豆包应用是否运行
            check_script = """
            tell application "System Events"
                try
                    get name of every process whose background only is false
                on error
                    return "error"
                end try
            end tell
            """

            result = subprocess.run(
                ["osascript", "-e", check_script], capture_output=True, text=True, timeout=5
            )

            if "豆包" in result.stdout:
                print("✅ 豆包应用正在运行")
                return True
            else:
                print("⚠️ 豆包应用未运行")

                if self.auto_start_app:
                    print("尝试启动豆包应用...")
                    start_script = """
                    tell application "豆包"
                        activate
                        delay 2
                    end tell
                    """

                    try:
                        subprocess.run(
                            ["osascript", "-e", start_script], capture_output=True, timeout=10
                        )
                        print("✅ 已启动豆包应用")
                        time.sleep(3)  # 等待应用启动
                        return True
                    except Exception as e:
                        print(f"❌ 启动豆包应用失败: {e}")
                        return False
                else:
                    print("请手动启动豆包应用")
                    return False

        except Exception as e:
            print(f"❌ 检查应用状态失败: {e}")
            return False

    def initialize(self) -> bool:
        """初始化图像生成器"""
        if self.initialized:
            return True

        print("初始化豆包图像生成器...")

        # 1. 确保豆包应用运行
        if not self.ensure_doubao_running():
            print("❌ 无法确保豆包应用运行")
            return False

        # 2. 打开豆包AI页面
        print("打开豆包AI页面...")
        try:
            result = self.doubao.open_doubao_ai()
            print(f"✅ {result}")
            time.sleep(3)  # 等待页面加载
        except Exception as e:
            print(f"❌ 打开AI页面失败: {e}")
            return False

        # 3. 进入AI创作界面
        print("进入AI创作界面...")
        try:
            click_result = self.doubao.enhanced.executor.click_button("AI 创作")
            if click_result.success:
                print(f"✅ 进入AI创作界面")
                time.sleep(3)
            else:
                print(f"❌ 进入AI创作界面失败: {click_result.error_message}")
                return False
        except Exception as e:
            print(f"❌ 进入AI创作界面失败: {e}")
            return False

        self.initialized = True
        print("✅ 图像生成器初始化完成")
        return True

    def generate_image(
        self,
        prompt: str,
        style: str = "realistic",
        size: str = "1024x1024",
        quality: str = "standard",
        num_images: int = 1,
        wait_time: int = 60,
    ) -> ImageGenerationResult:
        """
        生成图像

        Args:
            prompt: 图像描述提示词
            style: 图像风格 (realistic, anime, artistic, cartoon, etc.)
            size: 图像尺寸 (1024x1024, 512x512, etc.)
            quality: 图像质量 (standard, high, premium)
            num_images: 生成图像数量
            wait_time: 等待生成时间（秒）

        Returns:
            ImageGenerationResult: 生成结果
        """
        print(f"开始生成图像: {prompt}")

        # 确保已初始化
        if not self.initialized and not self.initialize():
            return ImageGenerationResult(
                success=False,
                image_urls=[],
                prompt=prompt,
                style=style,
                timestamp=datetime.now(),
                error_message="初始化失败",
            )

        try:
            # 1. 构建完整的提示词
            full_prompt = self._build_full_prompt(prompt, style, size, quality, num_images)
            print(f"完整提示词: {full_prompt}")

            # 2. 发送提示词
            print("发送图像生成请求...")
            result = self.doubao.enhanced.send_message_to_ai(full_prompt, use_enhanced=True)
            print(f"发送结果: {result}")

            if "消息发送成功" not in result:
                return ImageGenerationResult(
                    success=False,
                    image_urls=[],
                    prompt=prompt,
                    style=style,
                    timestamp=datetime.now(),
                    error_message=f"发送消息失败: {result}",
                )

            # 3. 等待图像生成
            print(f"等待{wait_time}秒让AI生成图像...")
            time.sleep(wait_time)

            # 4. 获取生成的图像
            print("获取生成的图像...")
            image_urls = self._extract_generated_images()

            if image_urls:
                print(f"🎉 成功生成 {len(image_urls)} 张图像")
                return ImageGenerationResult(
                    success=True,
                    image_urls=image_urls,
                    prompt=prompt,
                    style=style,
                    timestamp=datetime.now(),
                    metadata={
                        "full_prompt": full_prompt,
                        "size": size,
                        "quality": quality,
                        "num_requested": num_images,
                        "num_generated": len(image_urls),
                        "generation_time_seconds": wait_time,
                    },
                )
            else:
                print("⚠️ 未检测到生成的图像")
                return ImageGenerationResult(
                    success=False,
                    image_urls=[],
                    prompt=prompt,
                    style=style,
                    timestamp=datetime.now(),
                    error_message="未检测到生成的图像",
                )

        except Exception as e:
            print(f"❌ 图像生成失败: {e}")
            import traceback

            traceback.print_exc()

            return ImageGenerationResult(
                success=False,
                image_urls=[],
                prompt=prompt,
                style=style,
                timestamp=datetime.now(),
                error_message=str(e),
            )

    def _build_full_prompt(
        self, prompt: str, style: str, size: str, quality: str, num_images: int
    ) -> str:
        """构建完整的提示词"""
        # 基础提示词
        full_prompt = prompt

        # 添加风格指令
        style_instructions = {
            "realistic": "写实风格，细节丰富，真实感强",
            "anime": "动漫风格，日式动画，可爱或帅气",
            "artistic": "艺术风格，油画/水彩效果，有艺术感",
            "cartoon": "卡通风格，简洁线条，色彩鲜艳",
            "cyberpunk": "赛博朋克风格，霓虹灯，未来感",
            "fantasy": "奇幻风格，魔法，神话元素",
            "minimalist": "极简风格，简洁干净，留白",
            "photorealistic": "照片级真实，细节完美",
        }

        if style in style_instructions:
            full_prompt += f"，{style_instructions[style]}"
        else:
            full_prompt += f"，{style}风格"

        # 添加尺寸和质量要求
        full_prompt += f"，尺寸{size}，{quality}质量"

        # 添加数量要求（如果大于1）
        if num_images > 1:
            full_prompt += f"，生成{num_images}张不同版本的图片"

        return full_prompt

    def _extract_generated_images(self) -> List[str]:
        """提取生成的图像URL"""
        extract_js = """
        (function() {
            // 基于调试分析改进的图像检测逻辑
            var allImages = document.querySelectorAll('img');
            var generatedImages = [];

            allImages.forEach((img, idx) => {
                // 基本检查：图像已加载且尺寸足够大
                if (!img.complete) return;
                if (img.naturalWidth < 300 || img.naturalHeight < 300) return;

                var src = img.src || '';
                if (!src) return;

                // 过滤掉非生成图像（头像、logo、图标等）
                if (src.includes('avatar') || src.includes('logo') ||
                    src.includes('icon') || src.includes('samantha') ||
                    src.includes('static') || src.includes('intro')) {
                    return;
                }

                // 检查URL模式：生成图像通常包含这些域名
                var isLikelyGenerated = src.includes('byteimg.com') ||
                                       src.includes('bytecdn.com') ||
                                       src.includes('cloud') ||
                                       src.includes('tos') ||
                                       src.includes('flow');

                if (!isLikelyGenerated) return;

                // 检查图像可见性
                if (img.offsetWidth <= 0 || img.offsetHeight <= 0) return;

                // 可选：检查是否在对话相关区域
                // 不再强制要求isInMessage，因为豆包界面可能使用不同的DOM结构
                var isInRelevantArea = false;
                var parent = img.parentElement;

                // 检查父元素是否包含某些特定类或属性
                while (parent && parent !== document.body) {
                    var className = parent.className || '';
                    var role = parent.getAttribute('role') || '';
                    var dataTestId = parent.getAttribute('data-testid') || '';

                    // 检查是否是对话、消息或内容相关区域
                    if (className.includes('message') ||
                        className.includes('chat') ||
                        className.includes('content') ||
                        className.includes('bubble') ||
                        role.includes('article') ||
                        dataTestId.includes('message') ||
                        dataTestId.includes('chat') ||
                        parent.getAttribute('data-message-id')) {
                        isInRelevantArea = true;
                        break;
                    }
                    parent = parent.parentElement;
                }

                // 即使不在特定区域，如果URL匹配且尺寸足够也认为是生成的图像
                // 放宽条件：允许不在特定区域的图像
                if (isLikelyGenerated && img.naturalWidth >= 300 && img.naturalHeight >= 300) {
                    generatedImages.push({
                        index: idx,
                        src: src,
                        width: img.naturalWidth,
                        height: img.naturalHeight,
                        alt: img.alt || '',
                        timestamp: Date.now(),
                        isInRelevantArea: isInRelevantArea,
                        visible: img.offsetWidth > 0 && img.offsetHeight > 0
                    });
                }
            });

            // 按时间戳排序（假设后生成的图像时间戳更大）
            generatedImages.sort((a, b) => b.timestamp - a.timestamp);

            // 返回URL列表
            return JSON.stringify({
                success: true,
                images: generatedImages,
                count: generatedImages.length,
                urls: generatedImages.map(img => img.src),
                summary: {
                    totalChecked: allImages.length,
                    filteredBySize: generatedImages.filter(img => img.width >= 300 && img.height >= 300).length,
                    inRelevantArea: generatedImages.filter(img => img.isInRelevantArea).length,
                    visible: generatedImages.filter(img => img.visible).length
                }
            });
        })()
        """

        try:
            result = self.doubao.execute_javascript(1, 1, extract_js)
            print(f"JavaScript执行结果长度: {len(result)}")

            if "JavaScript执行结果: " in result:
                json_str = result.split("JavaScript执行结果: ", 1)[1]
                data = json.loads(json_str)

                if data.get("success"):
                    print(
                        f"图像检测结果: 检查了{data.get('summary', {}).get('totalChecked', 0)}张图像, 找到{len(data.get('urls', []))}张可能生成的图像"
                    )

                    if data.get("urls"):
                        print(f"✅ 找到 {len(data['urls'])} 张生成的图像")
                        for i, url in enumerate(data["urls"][:3]):  # 只显示前3个
                            print(f"  图像{i+1}: {url[:80]}...")
                        if len(data["urls"]) > 3:
                            print(f"  还有 {len(data['urls']) - 3} 张图像未显示")
                        return data["urls"]
                    else:
                        print(f"⚠️ 未检测到生成的图像")
                        # 输出详细调试信息
                        if data.get("summary"):
                            summary = data["summary"]
                            print(
                                f"  详细: 总检查{summary.get('totalChecked', 0)}, 尺寸过滤{summary.get('filteredBySize', 0)}, 相关区域{summary.get('inRelevantArea', 0)}"
                            )
                else:
                    print(f"⚠️ JavaScript执行返回失败状态")
            else:
                print(f"❌ JavaScript执行结果格式错误: {result[:200]}...")

        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"原始结果: {result[:500]}...")
        except Exception as e:
            print(f"❌ 提取图像URL失败: {e}")
            import traceback

            traceback.print_exc()

        return []

    def generate_with_retry(
        self, prompt: str, max_retries: int = 3, **kwargs
    ) -> ImageGenerationResult:
        """
        带重试的图像生成

        Args:
            prompt: 图像描述提示词
            max_retries: 最大重试次数
            **kwargs: 传递给generate_image的其他参数

        Returns:
            ImageGenerationResult: 生成结果
        """
        for attempt in range(max_retries):
            print(f"\n尝试 {attempt + 1}/{max_retries}...")

            result = self.generate_image(prompt, **kwargs)

            if result.success:
                print(f"✅ 第{attempt + 1}次尝试成功")
                return result
            else:
                print(f"❌ 第{attempt + 1}次尝试失败: {result.error_message}")

                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10  # 递增等待时间
                    print(f"等待{wait_time}秒后重试...")
                    time.sleep(wait_time)

                    # 重新初始化（可能界面状态变了）
                    self.initialized = False

        print(f"⚠️ 所有{max_retries}次尝试都失败")
        return result

    def save_result(self, result: ImageGenerationResult, output_dir: str = "generated_images"):
        """保存生成结果"""
        if not result.success:
            print("无法保存失败的结果")
            return

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 生成唯一ID
        prompt_hash = hashlib.md5(result.prompt.encode()).hexdigest()[:8]
        timestamp = result.timestamp.strftime("%Y%m%d_%H%M%S")
        base_name = f"doubao_{timestamp}_{prompt_hash}"

        # 保存元数据
        metadata_file = os.path.join(output_dir, f"{base_name}_metadata.json")
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

        print(f"✅ 元数据已保存: {metadata_file}")

        # 保存图像URL列表
        urls_file = os.path.join(output_dir, f"{base_name}_urls.txt")
        with open(urls_file, "w", encoding="utf-8") as f:
            for i, url in enumerate(result.image_urls):
                f.write(f"Image {i+1}: {url}\n")

        print(f"✅ URL列表已保存: {urls_file}")
        print(f"🎉 生成结果已保存到目录: {output_dir}")
        print(f"   生成时间: {result.timestamp}")
        print(f"   图像数量: {len(result.image_urls)}")
        print(f"   风格: {result.style}")


def test_basic_generation():
    """测试基础图像生成"""
    print("=== 测试豆包AI图像生成功能 ===")

    # 创建生成器
    generator = DoubaoImageGenerator(auto_start_app=True)

    # 测试提示词
    test_prompts = [
        ("一只可爱的卡通猫咪在花园里玩耍", "cartoon"),
        ("宁静的山水风景画，有瀑布和树林", "artistic"),
        ("未来城市的夜景，霓虹灯闪耀", "cyberpunk"),
        ("日式动漫风格的美少女，樱花背景", "anime"),
    ]

    results = []

    for prompt, style in test_prompts:
        print(f"\n{'='*50}")
        print(f"测试: {prompt} [{style}风格]")

        # 生成图像（带重试）
        result = generator.generate_with_retry(
            prompt=prompt,
            style=style,
            size="1024x1024",
            quality="standard",
            num_images=1,
            wait_time=45,
            max_retries=2,
        )

        results.append(result)

        if result.success:
            print(f"✅ 生成成功，获得 {len(result.image_urls)} 张图像")
            # 保存结果
            generator.save_result(result)
        else:
            print(f"❌ 生成失败: {result.error_message}")

    # 汇总结果
    print(f"\n{'='*50}")
    print("测试汇总:")
    successful = sum(1 for r in results if r.success)
    total_images = sum(len(r.image_urls) for r in results if r.success)

    print(f"成功测试: {successful}/{len(test_prompts)}")
    print(f"总生成图像: {total_images}")

    return all(r.success for r in results)


def cli_interface():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="豆包AI图像生成器")
    parser.add_argument("prompt", nargs="?", help="图像描述提示词")
    parser.add_argument(
        "--style",
        default="realistic",
        choices=[
            "realistic",
            "anime",
            "artistic",
            "cartoon",
            "cyberpunk",
            "fantasy",
            "minimalist",
            "photorealistic",
        ],
        help="图像风格",
    )
    parser.add_argument("--size", default="1024x1024", help="图像尺寸")
    parser.add_argument(
        "--quality", default="standard", choices=["standard", "high", "premium"], help="图像质量"
    )
    parser.add_argument("--num-images", type=int, default=1, help="生成图像数量")
    parser.add_argument("--wait-time", type=int, default=60, help="等待生成时间（秒）")
    parser.add_argument("--max-retries", type=int, default=3, help="最大重试次数")
    parser.add_argument("--output-dir", default="generated_images", help="输出目录")
    parser.add_argument("--auto-start", action="store_true", default=True, help="自动启动豆包应用")
    parser.add_argument("--test", action="store_true", help="运行测试")

    args = parser.parse_args()

    if args.test:
        print("运行测试...")
        success = test_basic_generation()
        sys.exit(0 if success else 1)

    # 检查是否提供了提示词
    if not args.prompt:
        parser.error("需要提供提示词（除非使用--test）")

    # 创建生成器
    generator = DoubaoImageGenerator(auto_start_app=args.auto_start)

    # 生成图像
    result = generator.generate_with_retry(
        prompt=args.prompt,
        style=args.style,
        size=args.size,
        quality=args.quality,
        num_images=args.num_images,
        wait_time=args.wait_time,
        max_retries=args.max_retries,
    )

    if result.success:
        print(f"✅ 图像生成成功!")
        print(f"   提示词: {result.prompt}")
        print(f"   风格: {result.style}")
        print(f"   图像数量: {len(result.image_urls)}")
        print(f"   生成时间: {result.timestamp}")

        # 保存结果
        generator.save_result(result, args.output_dir)

        # 显示图像URL
        print(f"\n生成的图像URL:")
        for i, url in enumerate(result.image_urls[:3]):  # 只显示前3个
            print(f"  {i+1}. {url}")
            if i >= 2 and len(result.image_urls) > 3:
                print(f"  ... 还有 {len(result.image_urls) - 3} 张图像")
                break

        sys.exit(0)
    else:
        print(f"❌ 图像生成失败: {result.error_message}")
        sys.exit(1)


if __name__ == "__main__":
    cli_interface()
