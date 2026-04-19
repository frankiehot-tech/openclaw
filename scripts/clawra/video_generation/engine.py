#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clawra模块 - 视频生成引擎原型
基于L3(1小时)层的故事叙述视频生成器
"""

import json
import os

# 导入配置
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "config"))
from layer_config import ContentLayer, get_layer_config, get_mvp_layer
from persona_config import DEFAULT_ATHENA_PERSONA, AthenaPersona


class VideoGenerationEngine:
    """视频生成引擎 - 原型实现"""

    def __init__(self, output_dir: str = None, persona: AthenaPersona = None):
        """
        初始化视频生成引擎

        Args:
            output_dir: 输出目录路径
            persona: Athena数字人格配置
        """
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "videos"
        )
        self.persona = persona or DEFAULT_ATHENA_PERSONA

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

        # 视频配置
        self.video_config = {
            "frame_rate": 30,  # 帧率
            "resolution": (1920, 1080),  # 分辨率 (宽, 高)
            "duration_seconds": 60,  # 原型视频时长60秒
            "codec": "mp4v",  # 编码器
            "background_color": (10, 20, 30),  # 深蓝色背景
            "text_color": (220, 220, 220),  # 浅灰色文字
            "accent_color": (0, 150, 255),  # 蓝色强调色
            "carbon_color": (50, 255, 50),  # 碳基颜色（绿色）
            "silicon_color": (255, 100, 0),  # 硅基颜色（橙色）
        }

    def generate_l3_story_video(self, story_theme: str, layer: ContentLayer = None) -> str:
        """
        生成L3(1小时)层故事叙述视频

        Args:
            story_theme: 故事主题
            layer: 内容层级，默认为L3

        Returns:
            生成的视频文件路径
        """
        if layer is None:
            layer = ContentLayer.L3_1_HOUR

        layer_config = get_layer_config(layer)
        print(f"生成{layer.value}层视频: {layer_config.content_type}")
        print(f"主题: {story_theme}")
        print(f"情感强度: {layer_config.emotional_intensity}")
        print(f"认知负载: {layer_config.cognitive_load}")

        # 生成视频文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = f"clawra_{layer.value}_{story_theme[:20]}_{timestamp}.mp4"
        video_path = os.path.join(self.output_dir, video_filename)

        # 获取视频时长（原型使用缩短时长）
        video_duration = min(layer_config.duration_seconds, 60)  # 最长60秒

        # 生成故事内容
        story_content = self._create_story_content(story_theme, layer_config)

        # 创建视频
        self._create_video_with_story(video_path, story_content, video_duration)

        print(f"视频生成完成: {video_path}")
        print(f"文件大小: {os.path.getsize(video_path) / 1024 / 1024:.2f} MB")

        return video_path

    def _create_story_content(self, theme: str, layer_config) -> Dict:
        """创建故事内容结构"""

        # 基于碳硅共生协议的预设故事模板
        story_templates = {
            "碳硅共生": {
                "title": "碳硅共生：开启智慧新纪元",
                "sections": [
                    {
                        "title": "起源",
                        "content": "在数字与现实的交汇处，碳基智慧与硅基算力相遇。",
                        "duration": 10,
                        "visual_type": "evolution",
                    },
                    {
                        "title": "融合",
                        "content": "情感与逻辑交织，创造性与分析力结合，开启全新的协作模式。",
                        "duration": 12,
                        "visual_type": "fusion",
                    },
                    {
                        "title": "进化",
                        "content": "通过递归演进，系统不断自我优化，实现真正的智能进化。",
                        "duration": 15,
                        "visual_type": "growth",
                    },
                    {
                        "title": "未来",
                        "content": "开放透明、协作共赢，构建碳硅基共生的智慧生态系统。",
                        "duration": 8,
                        "visual_type": "future",
                    },
                ],
                "conclusion": "智慧归己，价值传世。",
            },
            "open human": {
                "title": "open human：开放的智慧项目",
                "sections": [
                    {
                        "title": "使命",
                        "content": "推动碳硅基共生，实现智识归己，价值传世。",
                        "duration": 10,
                        "visual_type": "mission",
                    },
                    {
                        "title": "架构",
                        "content": "Athena（战略大脑）、openclaw（执行器）、open human（项目）三层架构。",
                        "duration": 12,
                        "visual_type": "architecture",
                    },
                    {
                        "title": "工作流",
                        "content": "传播智能工作流六模块：战略、创意、制作、分发、分析、优化。",
                        "duration": 15,
                        "visual_type": "workflow",
                    },
                    {
                        "title": "开源",
                        "content": "从MVP到GitHub开源，建立开放的智慧生态系统。",
                        "duration": 8,
                        "visual_type": "open_source",
                    },
                ],
                "conclusion": "开放创造无限可能。",
            },
        }

        # 选择或创建故事模板
        if theme in story_templates:
            story = story_templates[theme]
        else:
            story = story_templates["碳硅共生"]
            story["title"] = f"{theme}：碳硅共生视角"

        # 调整情感强度
        emotional_intensity = layer_config.emotional_intensity
        if emotional_intensity > 0.7:
            story["emotional_style"] = "激昂澎湃"
        elif emotional_intensity > 0.5:
            story["emotional_style"] = "积极向上"
        else:
            story["emotional_style"] = "平和叙事"

        return story

    def _create_video_with_story(self, video_path: str, story: Dict, duration: int):
        """使用故事内容创建视频"""

        # 视频参数
        width, height = self.video_config["resolution"]
        fps = self.video_config["frame_rate"]
        fourcc = cv2.VideoWriter_fourcc(*self.video_config["codec"])

        # 创建VideoWriter
        video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

        try:
            # 生成开场画面
            self._create_opening_frame(video_writer, story["title"], duration=3)

            # 生成各个章节
            total_duration = 3  # 开场时长
            for section in story["sections"]:
                section_duration = min(section["duration"], 15)  # 每章最长15秒
                self._create_section_frame(
                    video_writer,
                    section["title"],
                    section["content"],
                    section["visual_type"],
                    section_duration,
                )
                total_duration += section_duration

            # 生成结尾画面
            self._create_conclusion_frame(video_writer, story["conclusion"], duration=5)

        finally:
            video_writer.release()

    def _create_opening_frame(self, video_writer, title: str, duration: int):
        """创建开场画面"""
        width, height = self.video_config["resolution"]
        fps = self.video_config["frame_rate"]

        for frame_idx in range(duration * fps):
            # 创建渐变背景
            frame = np.zeros((height, width, 3), dtype=np.uint8)

            # 添加渐变效果
            gradient = np.linspace(0.3, 1.0, height).reshape(-1, 1)
            frame[:, :, 0] = self.video_config["background_color"][0] * gradient
            frame[:, :, 1] = self.video_config["background_color"][1] * gradient
            frame[:, :, 2] = self.video_config["background_color"][2] * gradient

            # 添加标题
            if frame_idx < fps * 2:  # 前2秒淡入
                alpha = min(1.0, frame_idx / (fps * 2))
            else:
                alpha = 1.0

            self._add_text_with_animation(
                frame,
                title,
                position=(width // 2, height // 3),
                font_scale=2.5,
                color=self.video_config["accent_color"],
                thickness=4,
                alpha=alpha,
            )

            # 添加副标题
            subtitle = f"Athena - {self.persona.role}"
            self._add_text_with_animation(
                frame,
                subtitle,
                position=(width // 2, height // 2 + 100),
                font_scale=1.2,
                color=self.video_config["text_color"],
                thickness=2,
                alpha=alpha * 0.8,
            )

            # 添加碳硅共生符号
            self._draw_carbon_silicon_symbol(
                frame, center=(width // 2, height * 3 // 4), size=80, rotation=frame_idx * 0.05
            )

            video_writer.write(frame)

    def _create_section_frame(
        self, video_writer, title: str, content: str, visual_type: str, duration: int
    ):
        """创建章节画面"""
        width, height = self.video_config["resolution"]
        fps = self.video_config["frame_rate"]

        # 将内容分页
        lines_per_page = 3
        content_lines = textwrap.wrap(content, width=30)
        pages = [
            content_lines[i : i + lines_per_page]
            for i in range(0, len(content_lines), lines_per_page)
        ]
        if not pages:
            pages = [[]]

        for page_idx, page_lines in enumerate(pages):
            page_duration = duration // len(pages) if len(pages) > 1 else duration

            for frame_idx in range(page_duration * fps):
                # 创建背景
                frame = np.zeros((height, width, 3), dtype=np.uint8)

                # 根据视觉类型设置背景
                if visual_type == "evolution":
                    # 进化背景 - 渐变绿色
                    self._create_evolution_background(frame, frame_idx)
                elif visual_type == "fusion":
                    # 融合背景 - 蓝橙混合
                    self._create_fusion_background(frame, frame_idx)
                elif visual_type == "growth":
                    # 成长背景 - 向上渐变
                    self._create_growth_background(frame, frame_idx)
                elif visual_type == "future":
                    # 未来背景 - 星空效果
                    self._create_future_background(frame, frame_idx)
                else:
                    # 默认背景
                    frame[:, :] = self.video_config["background_color"]

                # 添加章节标题
                self._add_text_with_animation(
                    frame,
                    title,
                    position=(width // 2, 150),
                    font_scale=1.8,
                    color=self.video_config["accent_color"],
                    thickness=3,
                    alpha=min(1.0, frame_idx / (fps * 1)),  # 1秒淡入
                )

                # 添加内容文本
                for line_idx, line in enumerate(page_lines):
                    y_pos = height // 2 + line_idx * 80 - (len(page_lines) * 40)
                    self._add_text_with_animation(
                        frame,
                        line,
                        position=(width // 2, y_pos),
                        font_scale=1.2,
                        color=self.video_config["text_color"],
                        thickness=2,
                        alpha=min(1.0, (frame_idx - fps * 0.5) / (fps * 1)),  # 延迟淡入
                    )

                # 添加视觉元素
                self._add_visual_element(frame, visual_type, frame_idx)

                video_writer.write(frame)

    def _create_conclusion_frame(self, video_writer, conclusion: str, duration: int):
        """创建结尾画面"""
        width, height = self.video_config["resolution"]
        fps = self.video_config["frame_rate"]

        for frame_idx in range(duration * fps):
            # 创建背景
            frame = np.zeros((height, width, 3), dtype=np.uint8)

            # 淡出效果
            fade_out = 1.0 - min(1.0, frame_idx / (fps * duration))

            # 添加渐变背景
            gradient = np.linspace(0.1, 0.8, height).reshape(-1, 1) * fade_out
            frame[:, :, 0] = self.video_config["background_color"][0] * gradient
            frame[:, :, 1] = self.video_config["background_color"][1] * gradient
            frame[:, :, 2] = self.video_config["background_color"][2] * gradient

            # 添加结论文字
            alpha = fade_out
            self._add_text_with_animation(
                frame,
                conclusion,
                position=(width // 2, height // 2),
                font_scale=2.0,
                color=self.video_config["accent_color"],
                thickness=3,
                alpha=alpha,
            )

            # 添加传承之环符号
            ring_alpha = alpha * 0.7
            if ring_alpha > 0:
                self._draw_legacy_ring(
                    frame,
                    center=(width // 2, height * 2 // 3),
                    radius=60,
                    thickness=3,
                    alpha=ring_alpha,
                )

            video_writer.write(frame)

    def _add_text_with_animation(
        self,
        frame,
        text: str,
        position: Tuple[int, int],
        font_scale: float,
        color: Tuple[int, int, int],
        thickness: int,
        alpha: float = 1.0,
    ):
        """添加带透明度动画的文本"""
        if alpha <= 0:
            return

        # 创建临时图像来绘制文本
        temp_frame = frame.copy()

        # 计算文本大小
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]

        # 计算文本位置（居中）
        text_x = position[0] - text_size[0] // 2
        text_y = position[1] + text_size[1] // 2

        # 绘制文本
        cv2.putText(
            temp_frame, text, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA
        )

        # 应用透明度
        if alpha < 1.0:
            frame[:, :] = cv2.addWeighted(frame, 1 - alpha, temp_frame, alpha, 0)
        else:
            frame[:, :] = temp_frame

    def _draw_carbon_silicon_symbol(
        self, frame, center: Tuple[int, int], size: int, rotation: float
    ):
        """绘制碳硅共生符号"""
        x, y = center

        # 绘制外圆（硅基 - 橙色）
        radius_outer = size
        cv2.circle(frame, (x, y), radius_outer, self.video_config["silicon_color"], 3, cv2.LINE_AA)

        # 绘制内圆（碳基 - 绿色）
        radius_inner = size // 2
        cv2.circle(frame, (x, y), radius_inner, self.video_config["carbon_color"], 3, cv2.LINE_AA)

        # 绘制连接线
        angle = rotation
        for _ in range(6):  # 6条连接线
            start_x = x + int(radius_inner * np.cos(angle))
            start_y = y + int(radius_inner * np.sin(angle))
            end_x = x + int(radius_outer * np.cos(angle))
            end_y = y + int(radius_outer * np.sin(angle))

            cv2.line(
                frame,
                (start_x, start_y),
                (end_x, end_y),
                (255, 255, 255),  # 白色连接线
                2,
                cv2.LINE_AA,
            )

            angle += np.pi / 3  # 60度间隔

    def _draw_legacy_ring(
        self, frame, center: Tuple[int, int], radius: int, thickness: int, alpha: float
    ):
        """绘制传承之环符号"""
        x, y = center

        # 创建临时图像
        temp_frame = np.zeros_like(frame)

        # 绘制外环
        cv2.circle(
            temp_frame, (x, y), radius, self.video_config["accent_color"], thickness, cv2.LINE_AA
        )

        # 绘制内环
        cv2.circle(
            temp_frame,
            (x, y),
            radius // 2,
            self.video_config["text_color"],
            thickness - 1,
            cv2.LINE_AA,
        )

        # 绘制连接点
        for angle in [0, np.pi / 2, np.pi, 3 * np.pi / 2]:
            point_x = x + int(radius * 0.75 * np.cos(angle))
            point_y = y + int(radius * 0.75 * np.sin(angle))

            cv2.circle(
                temp_frame,
                (point_x, point_y),
                5,
                (255, 255, 255),  # 白色连接点
                -1,  # 填充
                cv2.LINE_AA,
            )

        # 应用透明度
        frame[:, :] = cv2.addWeighted(frame, 1 - alpha, temp_frame, alpha, 0)

    def _create_evolution_background(self, frame, frame_idx):
        """创建进化背景"""
        height, width, _ = frame.shape

        # 创建绿色渐变
        for i in range(height):
            green_intensity = int(20 + 30 * (i / height) * (0.5 + 0.5 * np.sin(frame_idx * 0.01)))
            blue_intensity = int(10 + 15 * (i / height))
            red_intensity = int(5 + 10 * (i / height))

            frame[i, :] = [blue_intensity, green_intensity, red_intensity]

        # 添加粒子效果
        if frame_idx % 10 == 0:
            for _ in range(5):
                x = np.random.randint(0, width)
                y = np.random.randint(0, height)
                cv2.circle(frame, (x, y), 2, self.video_config["carbon_color"], -1)

    def _create_fusion_background(self, frame, frame_idx):
        """创建融合背景"""
        height, width, _ = frame.shape

        # 创建蓝橙混合渐变
        for i in range(height):
            # 蓝色部分（左边）
            blue_intensity = int(30 * (1 - i / height) * (0.7 + 0.3 * np.sin(frame_idx * 0.02)))
            for j in range(width // 2):
                frame[i, j] = [blue_intensity, blue_intensity // 2, 0]

            # 橙色部分（右边）
            orange_intensity = int(30 * (i / height) * (0.7 + 0.3 * np.cos(frame_idx * 0.02)))
            for j in range(width // 2, width):
                frame[i, j] = [0, orange_intensity // 2, orange_intensity]

    def _create_growth_background(self, frame, frame_idx):
        """创建成长背景"""
        height, width, _ = frame.shape

        # 向上生长的渐变
        wave_height = int(height * 0.3 * (0.5 + 0.5 * np.sin(frame_idx * 0.03)))

        for i in range(height):
            if i < wave_height:
                # 生长区域 - 亮绿色
                intensity = int(255 * (i / wave_height))
                frame[i, :] = [0, intensity, 0]
            else:
                # 基础区域 - 深绿色
                depth_factor = (i - wave_height) / (height - wave_height)
                intensity = int(100 * (1 - depth_factor))
                frame[i, :] = [0, intensity, 0]

    def _create_future_background(self, frame, frame_idx):
        """创建未来背景"""
        height, width, _ = frame.shape

        # 深蓝色星空背景
        frame[:, :] = [5, 5, 20]

        # 添加星星
        if frame_idx % 5 == 0:
            for _ in range(10):
                x = np.random.randint(0, width)
                y = np.random.randint(0, height)
                brightness = np.random.randint(150, 255)
                size = np.random.randint(1, 3)
                cv2.circle(frame, (x, y), size, (brightness, brightness, brightness), -1)

    def _add_visual_element(self, frame, visual_type: str, frame_idx: int):
        """添加视觉元素"""
        height, width, _ = frame.shape

        if visual_type == "mission":
            # 使命图标 - 指南针
            center_x, center_y = width - 150, 150
            self._draw_compass(frame, (center_x, center_y), 50, frame_idx * 0.02)

        elif visual_type == "architecture":
            # 架构图标 - 三层结构
            self._draw_architecture_layers(frame, frame_idx)

        elif visual_type == "workflow":
            # 工作流图标 - 循环箭头
            center_x, center_y = width - 150, height // 2
            self._draw_workflow_cycle(frame, (center_x, center_y), 60, frame_idx * 0.03)

        elif visual_type == "open_source":
            # 开源图标 - GitHub章鱼猫
            self._draw_github_octocat(frame, (width - 150, height - 150), 40)

    def _draw_compass(self, frame, center: Tuple[int, int], size: int, rotation: float):
        """绘制指南针图标"""
        x, y = center

        # 绘制外圈
        cv2.circle(frame, (x, y), size, self.video_config["text_color"], 2)

        # 绘制指针
        angle = rotation
        for i, direction in enumerate(["N", "E", "S", "W"]):
            dx = int(size * 0.8 * np.cos(angle))
            dy = int(size * 0.8 * np.sin(angle))

            # 指针线
            cv2.line(frame, (x, y), (x + dx, y + dy), self.video_config["accent_color"], 2)

            # 方向文字
            text_x = x + int(size * 0.9 * np.cos(angle))
            text_y = y + int(size * 0.9 * np.sin(angle))

            cv2.putText(
                frame,
                direction,
                (text_x - 5, text_y + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                self.video_config["text_color"],
                1,
            )

            angle += np.pi / 2  # 90度

    def _draw_architecture_layers(self, frame, frame_idx: int):
        """绘制三层架构图标"""
        height, width, _ = frame.shape

        # 三个矩形代表三层架构
        rect_width = 80
        rect_height = 40
        start_x = width - 200
        start_y = height // 2 - 100

        layers = [
            ("Athena", self.video_config["accent_color"]),  # 战略大脑
            ("openclaw", self.video_config["carbon_color"]),  # 执行器
            ("open human", self.video_config["silicon_color"]),  # 项目
        ]

        for i, (name, color) in enumerate(layers):
            y_pos = start_y + i * 70

            # 绘制矩形
            cv2.rectangle(
                frame, (start_x, y_pos), (start_x + rect_width, y_pos + rect_height), color, 2
            )

            # 添加文字
            cv2.putText(
                frame,
                name,
                (start_x + 10, y_pos + rect_height // 2 + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

            # 添加连接线
            if i < len(layers) - 1:
                next_y_pos = start_y + (i + 1) * 70
                line_x = start_x + rect_width // 2

                # 动画箭头
                arrow_length = 20
                if frame_idx % 30 < 15:  # 闪烁效果
                    cv2.arrowedLine(
                        frame,
                        (line_x, y_pos + rect_height),
                        (line_x, next_y_pos),
                        (255, 255, 255),
                        2,
                        tipLength=0.3,
                    )

    def _draw_workflow_cycle(self, frame, center: Tuple[int, int], radius: int, rotation: float):
        """绘制工作流循环图标"""
        x, y = center

        # 绘制圆形路径
        cv2.circle(frame, (x, y), radius, self.video_config["text_color"], 2)

        # 绘制四个箭头
        for i in range(4):
            angle = rotation + i * np.pi / 2

            # 箭头位置
            arrow_x = x + int(radius * np.cos(angle))
            arrow_y = y + int(radius * np.sin(angle))

            # 箭头方向（顺时针）
            arrow_angle = angle + np.pi / 2

            cv2.arrowedLine(
                frame,
                (arrow_x, arrow_y),
                (
                    arrow_x + int(radius * 0.5 * np.cos(arrow_angle)),
                    arrow_y + int(radius * 0.5 * np.sin(arrow_angle)),
                ),
                self.video_config["accent_color"],
                2,
                tipLength=0.3,
            )

    def _draw_github_octocat(self, frame, center: Tuple[int, int], size: int):
        """绘制GitHub章鱼猫图标（简化版）"""
        x, y = center

        # 绘制头部（圆形）
        cv2.circle(frame, (x, y), size, (50, 50, 50), -1)  # 深灰色头部

        # 绘制触手（简化版，用线条表示）
        for angle in np.linspace(0, 2 * np.pi, 8, endpoint=False):
            tentacle_length = size * 1.2

            # 触手末端
            end_x = x + int(tentacle_length * np.cos(angle))
            end_y = y + int(tentacle_length * np.sin(angle))

            # 绘制触手
            cv2.line(frame, (x, y), (end_x, end_y), (70, 70, 70), 3)  # 深灰色触手

            # 触手末端圆点
            cv2.circle(frame, (end_x, end_y), 3, (100, 100, 100), -1)

        # 绘制眼睛
        eye_radius = size // 4
        eye_offset = size // 3

        # 左眼
        cv2.circle(
            frame,
            (x - eye_offset, y - eye_offset // 2),
            eye_radius,
            (255, 255, 255),  # 白色眼睛
            -1,
        )

        # 右眼
        cv2.circle(
            frame,
            (x + eye_offset, y - eye_offset // 2),
            eye_radius,
            (255, 255, 255),  # 白色眼睛
            -1,
        )

        # 瞳孔
        pupil_radius = eye_radius // 2
        cv2.circle(frame, (x - eye_offset, y - eye_offset // 2), pupil_radius, (0, 0, 0), -1)
        cv2.circle(frame, (x + eye_offset, y - eye_offset // 2), pupil_radius, (0, 0, 0), -1)


def main():
    """主函数 - 测试视频生成引擎"""
    print("=" * 60)
    print("Clawra视频生成引擎原型测试")
    print("=" * 60)

    # 创建引擎实例
    engine = VideoGenerationEngine()

    # 打印配置信息
    print(f"\n输出目录: {engine.output_dir}")
    print(f"视频分辨率: {engine.video_config['resolution']}")
    print(f"帧率: {engine.video_config['frame_rate']} fps")

    # 测试生成碳硅共生故事视频
    print("\n生成碳硅共生故事视频...")
    video_path = engine.generate_l3_story_video("碳硅共生")

    # 测试生成open human故事视频
    print("\n生成open human故事视频...")
    video_path2 = engine.generate_l3_story_video("open human")

    print("\n" + "=" * 60)
    print("测试完成!")
    print(f"生成的视频文件:")
    print(f"1. {video_path}")
    print(f"2. {video_path2}")
    print("=" * 60)

    # 生成测试报告
    test_report = {
        "timestamp": datetime.now().isoformat(),
        "engine": "VideoGenerationEngine",
        "tests": [
            {
                "theme": "碳硅共生",
                "video_path": video_path,
                "status": "success" if os.path.exists(video_path) else "failed",
            },
            {
                "theme": "open human",
                "video_path": video_path2,
                "status": "success" if os.path.exists(video_path2) else "failed",
            },
        ],
        "environment": {
            "opencv_version": cv2.__version__,
            "numpy_version": np.__version__,
            "output_dir": engine.output_dir,
        },
    }

    # 保存测试报告
    report_path = os.path.join(engine.output_dir, "test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(test_report, f, ensure_ascii=False, indent=2)

    print(f"\n测试报告已保存到: {report_path}")


if __name__ == "__main__":
    main()
