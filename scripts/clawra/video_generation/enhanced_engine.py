#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clawra模块 - 增强视频生成引擎
集成DALL-E 3图像生成的视频内容增强版本
短期方案：DALL-E 3集成 / 中期：素材库 / 长期：RunwayML
"""

import base64
import json
import os

# 导入配置
import sys
import textwrap
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "config"))
from layer_config import ContentLayer, get_layer_config, get_mvp_layer
from persona_config import DEFAULT_ATHENA_PERSONA, AthenaPersona

# 导入基础引擎
sys.path.append(os.path.dirname(__file__))
from engine import VideoGenerationEngine


class EnhancedVideoGenerationEngine(VideoGenerationEngine):
    """增强视频生成引擎 - 集成DALL-E 3图像生成"""

    def __init__(
        self,
        output_dir: str = None,
        persona: AthenaPersona = None,
        dalle_api_key: str = None,
        dalle_endpoint: str = None,
    ):
        """
        初始化增强视频生成引擎

        Args:
            output_dir: 输出目录路径
            persona: Athena数字人格配置
            dalle_api_key: DALL-E 3 API密钥（可选）
            dalle_endpoint: DALL-E 3 API端点（可选）
        """
        super().__init__(output_dir, persona)

        # DALL-E 3配置
        self.dalle_api_key = (
            dalle_api_key or os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        )
        self.dalle_endpoint = dalle_endpoint or "https://api.openai.com/v1/images/generations"

        # 图像生成配置
        self.image_config = {
            "model": "dall-e-3",  # 或 "dashscope-image-synthesis-v2"
            "size": "1792x1024",  # 适合1920x1080视频的尺寸
            "quality": "standard",
            "style": "vivid",
            "num_images": 1,
            "timeout": 30,
        }

        # 图像缓存目录
        self.image_cache_dir = os.path.join(self.output_dir, "image_cache")
        os.makedirs(self.image_cache_dir, exist_ok=True)

        # 章节到图像提示的映射模板
        self.section_prompt_templates = {
            "evolution": {
                "zh": "数字进化、神经网络连接、智慧生长、碳硅融合、未来科技、抽象艺术、蓝色绿色渐变",
                "en": "digital evolution, neural network connections, intelligence growth, carbon-silicon fusion, futuristic technology, abstract art, blue-green gradient",
            },
            "fusion": {
                "zh": "有机与无机的融合、人机交互、情感计算、创意协作、蓝橙色调、抽象融合艺术",
                "en": "fusion of organic and inorganic, human-machine interaction, affective computing, creative collaboration, blue-orange color scheme, abstract fusion art",
            },
            "growth": {
                "zh": "智慧成长、知识树、递归演进、自我优化、向上生长、绿色生命力、未来教育",
                "en": "intelligence growth, knowledge tree, recursive evolution, self-optimization, upward growth, green vitality, future education",
            },
            "future": {
                "zh": "未来城市、数字星空、智慧网络、无限可能、深邃宇宙、科幻场景、星光闪烁",
                "en": "future city, digital stars, intelligent networks, infinite possibilities, deep universe, sci-fi scene, twinkling stars",
            },
            "mission": {
                "zh": "使命召唤、崇高目标、团队协作、战略规划、金色光芒、宏伟蓝图、远景展望",
                "en": "calling of mission, noble goal, team collaboration, strategic planning, golden light, grand blueprint, vision prospect",
            },
            "architecture": {
                "zh": "系统架构、层次结构、模块设计、网络连接、技术蓝图、三维可视化、结构清晰",
                "en": "system architecture, hierarchical structure, modular design, network connections, technical blueprint, 3D visualization, clear structure",
            },
            "workflow": {
                "zh": "工作流程、自动化管道、数据流动、步骤衔接、效率优化、过程可视化、动态图表",
                "en": "workflow, automation pipeline, data flow, step connection, efficiency optimization, process visualization, dynamic charts",
            },
            "open_source": {
                "zh": "开源协作、社区共建、代码共享、透明治理、网络节点、协作网络、开放生态",
                "en": "open source collaboration, community co-creation, code sharing, transparent governance, network nodes, collaboration network, open ecosystem",
            },
        }

    def generate_l3_story_video(self, story_theme: str, layer: ContentLayer = None) -> str:
        """
        增强版：生成L3(1小时)层故事叙述视频，集成DALL-E 3图像

        Args:
            story_theme: 故事主题
            layer: 内容层级，默认为L3

        Returns:
            生成的视频文件路径
        """
        if layer is None:
            layer = ContentLayer.L3_1_HOUR

        layer_config = get_layer_config(layer)
        print(f"🎬 生成增强版{layer.value}层视频: {layer_config.content_type}")
        print(f"📝 主题: {story_theme}")
        print(f"💖 情感强度: {layer_config.emotional_intensity}")
        print(f"🧠 认知负载: {layer_config.cognitive_load}")
        print(f"🖼️  图像生成: DALL-E 3集成")

        # 生成视频文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = f"clawra_enhanced_{layer.value}_{story_theme[:20]}_{timestamp}.mp4"
        video_path = os.path.join(self.output_dir, video_filename)

        # 获取视频时长（原型使用缩短时长）
        video_duration = min(layer_config.duration_seconds, 60)  # 最长60秒

        # 生成故事内容
        story_content = self._create_story_content(story_theme, layer_config)

        # 为故事章节生成图像
        print("🖼️  为故事章节生成图像...")
        story_content = self._enhance_story_with_images(story_content, story_theme)

        # 创建增强视频
        self._create_enhanced_video(video_path, story_content, video_duration)

        # 生成测试报告
        self._generate_enhancement_report(video_path, story_content)

        print(f"✅ 视频生成完成: {video_path}")
        print(f"📊 文件大小: {os.path.getsize(video_path) / 1024 / 1024:.2f} MB")

        return video_path

    def _enhance_story_with_images(self, story: Dict, theme: str) -> Dict:
        """
        为故事章节生成和集成DALL-E 3图像

        Args:
            story: 原始故事内容
            theme: 故事主题

        Returns:
            增强后的故事内容，包含图像路径
        """
        enhanced_story = story.copy()
        enhanced_story["enhanced_with"] = "DALL-E 3图像生成"
        enhanced_story["image_generation_timestamp"] = datetime.now().isoformat()

        # 为每个章节生成图像
        for i, section in enumerate(story["sections"]):
            visual_type = section["visual_type"]
            section_title = section["title"]
            section_content = section["content"]

            # 构建图像提示
            prompt = self._build_image_prompt(visual_type, section_title, section_content, theme)

            # 生成或获取图像
            image_path = self._generate_or_get_image(
                prompt=prompt,
                visual_type=visual_type,
                section_index=i,
                section_title=section_title,
                theme=theme,
            )

            # 将图像路径添加到章节
            enhanced_story["sections"][i]["image_path"] = image_path
            enhanced_story["sections"][i]["image_prompt"] = prompt

            print(f"  📸 章节{i+1}: '{section_title}' -> 图像: {os.path.basename(image_path)}")

        return enhanced_story

    def _build_image_prompt(self, visual_type: str, title: str, content: str, theme: str) -> str:
        """
        构建DALL-E 3图像生成提示

        Args:
            visual_type: 视觉类型
            title: 章节标题
            content: 章节内容
            theme: 故事主题

        Returns:
            图像生成提示文本
        """
        # 基础提示模板
        base_prompt = self.section_prompt_templates.get(visual_type, {}).get("zh", "")

        # 构建详细提示
        prompt_parts = []

        if base_prompt:
            prompt_parts.append(base_prompt)

        # 添加主题上下文
        if "碳硅共生" in theme:
            prompt_parts.append("碳基智慧与硅基算力的融合，数字与现实的交汇")
        elif "open human" in theme.lower():
            prompt_parts.append("开放智慧项目，透明协作，开源生态")

        # 添加章节内容
        prompt_parts.append(f"概念: {title}")
        prompt_parts.append(f"描述: {content[:100]}...")

        # 添加风格指导
        prompt_parts.append("风格: 未来科技艺术，抽象概念可视化，高质量数字艺术，4K分辨率")
        prompt_parts.append("避免: 文字、logo、人脸、具体品牌")

        return "，".join(prompt_parts)

    def _generate_or_get_image(
        self, prompt: str, visual_type: str, section_index: int, section_title: str, theme: str
    ) -> str:
        """
        生成或获取缓存的DALL-E 3图像

        Args:
            prompt: 图像生成提示
            visual_type: 视觉类型
            section_index: 章节索引
            section_title: 章节标题
            theme: 故事主题

        Returns:
            图像文件路径
        """
        # 生成缓存文件名
        safe_title = "".join(c for c in section_title if c.isalnum() or c in " _-")[:30]
        cache_filename = f"{theme}_{visual_type}_{section_index}_{safe_title}.jpg"
        cache_path = os.path.join(self.image_cache_dir, cache_filename)

        # 检查缓存是否存在
        if os.path.exists(cache_path):
            print(f"    📁 使用缓存图像: {cache_filename}")
            return cache_path

        # 如果没有API密钥，使用模拟图像
        if not self.dalle_api_key:
            print(f"    ⚠️  API密钥未配置，使用模拟图像")
            return self._generate_mock_image(prompt, visual_type, cache_path)

        # 尝试生成真实图像
        try:
            print(f"    🚀 调用DALL-E 3 API生成图像...")
            image_url = self._call_dalle_api(prompt)

            if image_url:
                # 下载图像
                image_data = self._download_image(image_url)

                # 保存到缓存
                with open(cache_path, "wb") as f:
                    f.write(image_data)

                print(f"    ✅ 图像生成成功: {cache_filename}")
                return cache_path

        except Exception as e:
            print(f"    ❌ DALL-E 3 API调用失败: {e}")

        # 如果API调用失败，使用模拟图像
        return self._generate_mock_image(prompt, visual_type, cache_path)

    def _call_dalle_api(self, prompt: str) -> Optional[str]:
        """
        调用DALL-E 3 API生成图像

        Args:
            prompt: 图像生成提示

        Returns:
            图像URL或None
        """
        # 检查API密钥
        if not self.dalle_api_key:
            return None

        # 准备请求头
        headers = {
            "Content-Type": "application/json",
        }

        # 根据API端点设置认证
        if "openai.com" in self.dalle_endpoint:
            headers["Authorization"] = f"Bearer {self.dalle_api_key}"
        elif "dashscope" in self.dalle_endpoint:
            headers["Authorization"] = f"Bearer {self.dalle_api_key}"
            headers["X-DashScope-Async"] = "enable"  # 阿里云异步模式

        # 准备请求数据
        request_data = {
            "model": self.image_config["model"],
            "prompt": prompt,
            "size": self.image_config["size"],
            "quality": self.image_config["quality"],
            "n": self.image_config["num_images"],
        }

        try:
            # 发送请求
            response = requests.post(
                self.dalle_endpoint,
                headers=headers,
                json=request_data,
                timeout=self.image_config["timeout"],
            )

            if response.status_code == 200:
                result = response.json()

                # 解析不同API的响应格式
                if "data" in result and result["data"]:
                    # OpenAI格式
                    return result["data"][0]["url"]
                elif "output" in result and result["output"].get("task_status") == "SUCCEEDED":
                    # 阿里云DashScope格式
                    return result["output"]["results"][0]["url"]
                elif "url" in result:
                    # 直接URL格式
                    return result["url"]

            print(f"API响应错误: {response.status_code}, {response.text[:200]}")
            return None

        except Exception as e:
            print(f"API调用异常: {e}")
            return None

    def _download_image(self, image_url: str) -> bytes:
        """
        下载图像数据

        Args:
            image_url: 图像URL

        Returns:
            图像二进制数据
        """
        response = requests.get(image_url, timeout=self.image_config["timeout"])
        response.raise_for_status()
        return response.content

    def _generate_mock_image(self, prompt: str, visual_type: str, output_path: str) -> str:
        """
        生成模拟图像（当API不可用时）

        Args:
            prompt: 图像提示（用于生成描述）
            visual_type: 视觉类型
            output_path: 输出路径

        Returns:
            图像文件路径
        """
        # 创建模拟图像
        width, height = 1792, 1024
        image = np.zeros((height, width, 3), dtype=np.uint8)

        # 根据视觉类型创建不同风格的图像
        if visual_type == "evolution":
            # 进化风格 - 绿色渐变与线条
            for i in range(height):
                gradient = int(255 * i / height)
                image[i, :, 1] = gradient  # 绿色通道
                image[i, :, 0] = 100  # 蓝色通道

            # 添加神经网络线条
            for _ in range(20):
                x1 = np.random.randint(0, width)
                y1 = np.random.randint(0, height)
                x2 = np.random.randint(0, width)
                y2 = np.random.randint(0, height)
                color = (100, 255, 100)  # 绿色线条
                cv2.line(image, (x1, y1), (x2, y2), color, 2)

        elif visual_type == "fusion":
            # 融合风格 - 蓝橙混合
            half_width = width // 2
            image[:, :half_width, 0] = 255  # 左侧蓝色
            image[:, :half_width, 2] = 100

            image[:, half_width:, 0] = 100  # 右侧橙色
            image[:, half_width:, 1] = 150
            image[:, half_width:, 2] = 255

            # 添加融合过渡
            for i in range(half_width - 100, half_width + 100):
                blend = (i - (half_width - 100)) / 200
                image[:, i, 0] = int(255 * (1 - blend) + 100 * blend)
                image[:, i, 1] = int(0 * (1 - blend) + 150 * blend)
                image[:, i, 2] = int(100 * (1 - blend) + 255 * blend)

        elif visual_type == "growth":
            # 成长风格 - 向上生长的树状结构
            image[:, :, 1] = 200  # 绿色背景
            image[:, :, 0] = 50

            # 绘制树状结构
            center_x = width // 2
            base_y = height - 50

            for i in range(5):
                branch_height = np.random.randint(200, 400)
                branch_x = center_x + np.random.randint(-300, 300)

                # 主干
                cv2.line(
                    image, (branch_x, base_y), (branch_x, base_y - branch_height), (50, 150, 50), 8
                )

                # 分支
                for j in range(3):
                    angle = np.random.uniform(-0.8, 0.8)
                    branch_length = np.random.randint(50, 150)
                    end_x = int(branch_x + branch_length * np.sin(angle))
                    end_y = int(base_y - branch_height + branch_length * np.cos(angle))

                    cv2.line(
                        image,
                        (branch_x, base_y - branch_height),
                        (end_x, end_y),
                        (100, 200, 100),
                        4,
                    )

        else:
            # 默认风格 - 渐变背景
            for i in range(height):
                gradient = int(255 * i / height)
                image[i, :, 0] = gradient  # 蓝色通道
                image[i, :, 2] = 255 - gradient  # 红色通道

        # 添加视觉类型标签
        font = cv2.FONT_HERSHEY_SIMPLEX
        label = f"模拟图像: {visual_type}"
        text_size = cv2.getTextSize(label, font, 1, 2)[0]
        text_x = (width - text_size[0]) // 2
        text_y = height // 2

        cv2.putText(image, label, (text_x, text_y), font, 1, (255, 255, 255), 2)

        # 添加提示摘要
        prompt_summary = prompt[:80] + "..." if len(prompt) > 80 else prompt
        cv2.putText(
            image,
            prompt_summary,
            (50, height - 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (200, 200, 200),
            1,
        )

        # 在文件名中添加_simulated标记以便识别
        base, ext = os.path.splitext(output_path)
        simulated_path = f"{base}_simulated{ext}"

        # 保存图像
        cv2.imwrite(simulated_path, image)

        return simulated_path

    def _create_enhanced_video(self, video_path: str, story: Dict, duration: int):
        """
        创建增强视频（集成图像内容）

        Args:
            video_path: 视频输出路径
            story: 增强的故事内容（包含图像）
            duration: 视频时长
        """
        width, height = self.video_config["resolution"]
        fps = self.video_config["frame_rate"]
        fourcc = cv2.VideoWriter_fourcc(*self.video_config["codec"])

        # 创建VideoWriter
        video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

        try:
            print("🎥 创建增强视频内容...")

            # 1. 开场画面（使用基础引擎）
            self._create_opening_frame(video_writer, story["title"], duration=3)
            total_duration = 3

            # 2. 各章节画面（集成图像）
            for i, section in enumerate(story["sections"]):
                section_duration = min(section["duration"], 15)

                # 检查是否有生成的图像
                if "image_path" in section and os.path.exists(section["image_path"]):
                    print(f"  🎬 章节{i+1}: 集成图像 '{os.path.basename(section['image_path'])}'")
                    self._create_enhanced_section_frame(
                        video_writer,
                        section["title"],
                        section["content"],
                        section["image_path"],
                        section_duration,
                    )
                else:
                    # 回退到基础章节画面
                    print(f"  📝 章节{i+1}: 使用基础文本动画")
                    self._create_section_frame(
                        video_writer,
                        section["title"],
                        section["content"],
                        section["visual_type"],
                        section_duration,
                    )

                total_duration += section_duration

            # 3. 结尾画面
            self._create_conclusion_frame(video_writer, story["conclusion"], duration=5)

            print(f"✅ 视频合成完成，总时长: {total_duration + 5}秒")

        finally:
            video_writer.release()

    def _create_enhanced_section_frame(
        self, video_writer, title: str, content: str, image_path: str, duration: int
    ):
        """
        创建增强的章节画面（集成图像）

        Args:
            video_writer: 视频写入器
            title: 章节标题
            content: 章节内容
            image_path: 图像文件路径
            duration: 章节时长
        """
        width, height = self.video_config["resolution"]
        fps = self.video_config["frame_rate"]

        # 加载图像
        try:
            section_image = cv2.imread(image_path)
            if section_image is None:
                raise FileNotFoundError(f"无法加载图像: {image_path}")

            # 调整图像大小以适应视频
            img_height, img_width = section_image.shape[:2]

            # 计算缩放比例，保持宽高比
            scale = min(width / img_width, height / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            if new_width != img_width or new_height != img_height:
                section_image = cv2.resize(section_image, (new_width, new_height))

            # 计算图像在视频中的位置（居中）
            x_offset = (width - new_width) // 2
            y_offset = (height - new_height) // 2

        except Exception as e:
            print(f"❌ 图像加载失败: {e}，回退到基础背景")
            section_image = None

        # 生成章节画面
        for frame_idx in range(duration * fps):
            # 创建基础帧
            frame = np.zeros((height, width, 3), dtype=np.uint8)

            if section_image is not None:
                # 应用图像作为背景（带透明度效果）
                alpha = 0.7  # 图像透明度

                # 创建图像区域
                if y_offset >= 0 and x_offset >= 0:
                    frame[y_offset : y_offset + new_height, x_offset : x_offset + new_width] = (
                        section_image
                    )

                # 添加深色叠加层，提高文字可读性
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (width, height), (0, 0, 0), -1)
                frame = cv2.addWeighted(frame, alpha, overlay, 0.3, 0)
            else:
                # 回退到渐变背景
                frame[:, :] = self.video_config["background_color"]

            # 添加标题（在图像上方）
            title_alpha = min(1.0, frame_idx / (fps * 1))  # 1秒淡入
            title_color = self.video_config["accent_color"]

            # 添加标题背景（提高可读性）
            font = cv2.FONT_HERSHEY_SIMPLEX
            title_size = cv2.getTextSize(title, font, 1.8, 3)[0]
            title_bg_x1 = width // 2 - title_size[0] // 2 - 20
            title_bg_x2 = width // 2 + title_size[0] // 2 + 20
            title_bg_y1 = 150 - title_size[1] // 2 - 10
            title_bg_y2 = 150 + title_size[1] // 2 + 10

            if title_alpha > 0:
                bg_alpha = title_alpha * 0.7
                bg_color = tuple(int(c * 0.2) for c in title_color)
                bg_frame = frame.copy()
                cv2.rectangle(
                    bg_frame, (title_bg_x1, title_bg_y1), (title_bg_x2, title_bg_y2), bg_color, -1
                )
                frame = cv2.addWeighted(frame, 1 - bg_alpha, bg_frame, bg_alpha, 0)

            self._add_text_with_animation(
                frame,
                title,
                position=(width // 2, 150),
                font_scale=1.8,
                color=title_color,
                thickness=3,
                alpha=title_alpha,
            )

            # 添加内容文本（分页处理）
            content_lines = textwrap.wrap(content, width=40)
            lines_per_page = 3
            pages = [
                content_lines[i : i + lines_per_page]
                for i in range(0, len(content_lines), lines_per_page)
            ]

            if not pages:
                pages = [[]]

            # 计算当前页面
            frames_per_page = (duration * fps) // len(pages)
            current_page = (
                min(frame_idx // frames_per_page, len(pages) - 1) if frames_per_page > 0 else 0
            )

            # 添加页面内容
            content_alpha = min(1.0, (frame_idx - fps * 0.5) / (fps * 1))
            content_color = self.video_config["text_color"]

            for line_idx, line in enumerate(pages[current_page]):
                y_pos = height // 2 + line_idx * 70 - (len(pages[current_page]) * 35)

                # 添加文本背景
                line_size = cv2.getTextSize(line, font, 1.2, 2)[0]
                line_bg_x1 = width // 2 - line_size[0] // 2 - 15
                line_bg_x2 = width // 2 + line_size[0] // 2 + 15
                line_bg_y1 = y_pos - line_size[1] // 2 - 5
                line_bg_y2 = y_pos + line_size[1] // 2 + 5

                if content_alpha > 0:
                    line_bg_alpha = content_alpha * 0.5
                    line_bg_color = (30, 30, 30)
                    line_bg_frame = frame.copy()
                    cv2.rectangle(
                        line_bg_frame,
                        (line_bg_x1, line_bg_y1),
                        (line_bg_x2, line_bg_y2),
                        line_bg_color,
                        -1,
                    )
                    frame = cv2.addWeighted(
                        frame, 1 - line_bg_alpha, line_bg_frame, line_bg_alpha, 0
                    )

                self._add_text_with_animation(
                    frame,
                    line,
                    position=(width // 2, y_pos),
                    font_scale=1.2,
                    color=content_color,
                    thickness=2,
                    alpha=content_alpha,
                )

            # 添加页面指示器（多页时）
            if len(pages) > 1:
                page_indicator = f"{current_page + 1}/{len(pages)}"
                cv2.putText(
                    frame, page_indicator, (width - 100, height - 50), font, 0.8, (150, 150, 150), 1
                )

            video_writer.write(frame)

    def _generate_enhancement_report(self, video_path: str, story: Dict):
        """
        生成增强效果测试报告

        Args:
            video_path: 生成的视频路径
            story: 故事内容
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "enhancement_type": "DALL-E 3图像集成",
            "story_theme": story.get("title", "unknown"),
            "sections_enhanced": len(story.get("sections", [])),
            "images_generated": 0,
            "images_cached": 0,
            "api_status": "simulated" if not self.dalle_api_key else "configured",
            "section_details": [],
        }

        # 统计图像生成情况
        for i, section in enumerate(story.get("sections", [])):
            section_info = {
                "index": i,
                "title": section.get("title"),
                "visual_type": section.get("visual_type"),
                "has_image": "image_path" in section,
                "image_source": "simulated",
            }

            if "image_path" in section:
                image_path = section["image_path"]
                if os.path.exists(image_path):
                    section_info["image_file"] = os.path.basename(image_path)
                    section_info["image_size"] = os.path.getsize(image_path)

                    # 检查是否为模拟图像（通过文件名中的_simulated标记）
                    if "_simulated" in os.path.basename(image_path):
                        section_info["image_source"] = "simulated"
                    else:
                        section_info["image_source"] = "DALL-E 3"

                    if section_info["image_source"] == "DALL-E 3":
                        report["images_generated"] += 1
                    else:
                        report["images_cached"] += 1

            report["section_details"].append(section_info)

        # 保存报告
        report_dir = os.path.join(self.output_dir, "reports")
        os.makedirs(report_dir, exist_ok=True)

        report_filename = f"enhancement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(report_dir, report_filename)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"📊 增强报告已保存: {report_path}")
        return report_path


def test_enhanced_engine():
    """测试增强视频引擎"""
    print("=" * 60)
    print("测试增强视频生成引擎 (DALL-E 3集成)")
    print("=" * 60)

    # 创建增强引擎
    engine = EnhancedVideoGenerationEngine()

    # 测试主题
    test_themes = ["碳硅共生", "open human"]

    for theme in test_themes:
        print(f"\n🚀 测试主题: {theme}")
        try:
            video_path = engine.generate_l3_story_video(theme)
            print(f"✅ 测试完成: {video_path}")
        except Exception as e:
            print(f"❌ 测试失败: {e}")

    print("\n" + "=" * 60)
    print("增强引擎测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_enhanced_engine()
