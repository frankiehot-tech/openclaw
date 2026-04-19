#!/usr/bin/env python3
"""简化图像检测器 - 解决增强检测逻辑返回'missing value'的问题"""

import json
import logging
import os
import sys
import time
from typing import List

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced, ImageGenerationParams


class SimpleImageDetector(DoubaoCLIEnhanced):
    """简化图像检测器 - 基于父类但使用更可靠的检测逻辑"""

    def _wait_for_generation(self, params: ImageGenerationParams) -> List[str]:
        """简化版等待生成完成方法"""
        logger.info(f"等待生成完成（简化检测），超时: {self.image_generation_timeout}s")

        start_wait = time.time()
        image_urls = []
        check_count = 0

        # 简化的等待生成JavaScript代码
        # 重点：避免复杂DOM遍历，使用简单可靠的选择器
        simple_wait_js = """
        // 简化图像生成状态检测
        (function() {
            try {
                // 1. 基本进度检测 - 使用常见的选择器
                var progressSelectors = [
                    '[role="progressbar"]',
                    '.progress',
                    '.loading',
                    '.spinner',
                    '.loader',
                    '[class*="loading"]',
                    '[class*="progress"]'
                ];

                var isGenerating = false;
                for (var i = 0; i < progressSelectors.length; i++) {
                    var elements = document.querySelectorAll(progressSelectors[i]);
                    if (elements.length > 0) {
                        isGenerating = true;
                        break;
                    }
                }

                // 2. 图像检测 - 查找所有img，但过滤小图像和图标
                var allImages = document.querySelectorAll('img');
                var candidateUrls = [];

                for (var i = 0; i < allImages.length; i++) {
                    var img = allImages[i];
                    var src = img.src || '';

                    // 基本过滤条件
                    if (!src || !src.startsWith('http')) {
                        continue;
                    }

                    // 过滤常见的小图像和图标
                    if (src.includes('logo') ||
                        src.includes('icon') ||
                        src.includes('avatar') ||
                        src.includes('favicon')) {
                        continue;
                    }

                    // 检查图像大小（可能是生成的结果）
                    if (img.offsetWidth > 100 && img.offsetHeight > 100) {
                        candidateUrls.push(src);
                    }
                }

                // 3. 也检查特定于豆包的选择器
                var doubaoImages = document.querySelectorAll('img[alt*="生成"], img[alt*="结果"], [class*="generated"] img');
                for (var i = 0; i < doubaoImages.length; i++) {
                    var img = doubaoImages[i];
                    if (img.src && img.src.startsWith('http')) {
                        // 去重
                        if (!candidateUrls.includes(img.src)) {
                            candidateUrls.push(img.src);
                        }
                    }
                }

                return JSON.stringify({
                    success: true,
                    is_generating: isGenerating,
                    image_urls: candidateUrls,
                    image_count: candidateUrls.length,
                    total_images: allImages.length
                });

            } catch (error) {
                return JSON.stringify({
                    success: false,
                    error: error.message,
                    is_generating: false,
                    image_urls: [],
                    image_count: 0
                });
            }
        })()
        """

        logger.info("开始使用简化检测逻辑监控生成状态...")

        while time.time() - start_wait < self.image_generation_timeout:
            check_count += 1
            logger.info(f"第 {check_count} 次检查生成状态...")

            result = self.execute_javascript_enhanced(simple_wait_js)

            if result.success:
                try:
                    cleaned_output = self._clean_js_output(result.output)
                    status = json.loads(cleaned_output)

                    # 检查JavaScript执行是否成功
                    if not status.get("success", True):
                        logger.warning(f"JavaScript执行错误: {status.get('error', '未知错误')}")
                        # 继续等待
                    else:
                        # 记录调试信息
                        logger.info(
                            f"检测状态: 生成中={status.get('is_generating', False)}, "
                            f"候选图像={status.get('image_count', 0)}, "
                            f"总图像={status.get('total_images', 0)}"
                        )

                        # 检查是否生成了足够的图像
                        if (
                            status.get("image_urls")
                            and len(status["image_urls"]) >= params.num_images
                        ):
                            image_urls = status["image_urls"][: params.num_images]
                            logger.info(f"✅ 生成完成，找到 {len(image_urls)} 张图像")
                            break

                        # 检查是否还在生成中
                        if not status.get("is_generating", True):
                            # 不再生成中，检查是否有图像
                            if status.get("image_urls"):
                                image_urls = status["image_urls"][: params.num_images]
                                logger.info(f"✅ 生成似乎已完成，找到 {len(image_urls)} 张图像")
                                break
                            else:
                                logger.info("⚠️  不再生成中，但未找到图像")

                except json.JSONDecodeError as e:
                    logger.warning(f"JSON解析失败: {e}, 原始输出: {result.output[:100]}")
                except Exception as e:
                    logger.error(f"状态检查异常: {e}")
            else:
                logger.warning(f"JavaScript执行失败: {result.error_message}")

            # 等待一段时间再检查
            wait_time = 3  # 3秒检查一次
            logger.info(f"等待 {wait_time} 秒后再次检查...")
            time.sleep(wait_time)

        if not image_urls:
            logger.warning(f"等待超时（{self.image_generation_timeout}s），未找到生成的图像")
            # 最后一次尝试获取页面状态用于调试
            debug_js = """
            // 获取页面状态用于调试
            (function() {
                return JSON.stringify({
                    title: document.title,
                    url: window.location.href,
                    all_images: document.querySelectorAll('img').length,
                    body_length: document.body.innerText.length,
                    body_preview: document.body.innerText.substring(0, 200)
                });
            })()
            """
            debug_result = self.execute_javascript_enhanced(debug_js)
            if debug_result.success:
                try:
                    cleaned = self._clean_js_output(debug_result.output)
                    page_info = json.loads(cleaned)
                    logger.info(
                        f"页面调试信息: 标题='{page_info.get('title')}', "
                        f"URL={page_info.get('url')}, "
                        f"图像总数={page_info.get('all_images')}"
                    )
                except:
                    pass

        return image_urls


def test_simple_detector(timeout_seconds=30):
    """测试简化图像检测器"""
    print(f"=== 测试简化图像检测器（{timeout_seconds}秒超时） ===")

    try:
        cli = SimpleImageDetector()
        cli.image_generation_timeout = timeout_seconds

        params = ImageGenerationParams(
            prompt="测试简化检测器 - 一个美丽的日落场景",
            style="realistic",
            size="512x512",
            quality="standard",
            num_images=1,
        )

        print(f"生成参数:")
        print(f"  提示词: {params.prompt}")

        print("\n开始图像生成...")
        start_time = time.time()
        result = cli.generate_image(params)
        elapsed = time.time() - start_time

        print(f"\n=== 生成结果 ===")
        print(f"总耗时: {elapsed:.1f}秒")
        print(f"成功: {result.success}")

        if result.success:
            print("✅ 图像生成成功！")
            print(f"生成图像数量: {len(result.image_urls)}")

            if result.image_urls:
                print("图像URL:")
                for i, url in enumerate(result.image_urls):
                    print(f"  {i+1}. {url}")

            return True
        else:
            print(f"❌ 图像生成失败: {result.error_message}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("简化图像检测器测试\n")

    # 用户确认
    print("重要：此测试将在豆包App中实际执行操作。")
    print("请确保豆包App正在运行并已登录。")
    print()

    response = input("是否继续测试？(y/n): ")
    if response.lower() != "y":
        print("测试取消")
        sys.exit(0)

    success = test_simple_detector(30)

    if success:
        print("\n✅ 简化检测器测试成功")
        sys.exit(0)
    else:
        print("\n❌ 简化检测器测试失败")
        sys.exit(1)
