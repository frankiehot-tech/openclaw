#!/usr/bin/env python3
"""
ComfyUI Panels插件集成模块
提供漫画面板生成和布局功能

注意：由于网络限制无法访问GitHub，这是本地模拟实现。
待网络恢复后可用真实插件替换。
"""

import json
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.append(str(Path(__file__).parent))
from comfyui_athena_generator import ComfyUIAthenaGenerator


@dataclass
class PanelLayout:
    """面板布局定义"""

    name: str
    description: str
    rows: int
    cols: int
    panel_sizes: List[Tuple[int, int]]  # 每个面板的(宽,高)
    gutter_size: int = 20  # 面板间距
    margin_size: int = 40  # 页面边距

    def total_size(self) -> Tuple[int, int]:
        """计算总页面尺寸"""
        total_width = self.margin_size * 2
        total_height = self.margin_size * 2

        # 计算最大列宽和行高
        col_widths = [0] * self.cols
        row_heights = [0] * self.rows

        for idx, (width, height) in enumerate(self.panel_sizes):
            row = idx // self.cols
            col = idx % self.cols
            col_widths[col] = max(col_widths[col], width)
            row_heights[row] = max(row_heights[row], height)

        total_width += sum(col_widths) + (self.cols - 1) * self.gutter_size
        total_height += sum(row_heights) + (self.rows - 1) * self.gutter_size

        return total_width, total_height

    def panel_position(self, panel_index: int) -> Tuple[int, int]:
        """计算面板在页面中的位置"""
        if panel_index >= len(self.panel_sizes):
            raise ValueError(f"面板索引超出范围: {panel_index}")

        row = panel_index // self.cols
        col = panel_index % self.cols

        # 计算位置
        x = self.margin_size
        y = self.margin_size

        # 累加前面列的宽度
        for c in range(col):
            # 找到该列所有面板的最大宽度
            col_width = 0
            for r in range(self.rows):
                idx = r * self.cols + c
                if idx < len(self.panel_sizes):
                    col_width = max(col_width, self.panel_sizes[idx][0])
            x += col_width + self.gutter_size

        # 累加前面行的高度
        for r in range(row):
            # 找到该行所有面板的最大高度
            row_height = 0
            for c in range(self.cols):
                idx = r * self.cols + c
                if idx < len(self.panel_sizes):
                    row_height = max(row_height, self.panel_sizes[idx][1])
            y += row_height + self.gutter_size

        return x, y


@dataclass
class ComicPage:
    """漫画页面"""

    layout: PanelLayout
    panels: List[Image.Image]  # 面板图像列表
    page_number: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def create_page_image(
        self, background_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Image.Image:
        """创建完整的页面图像"""
        page_width, page_height = self.layout.total_size()
        page_image = Image.new("RGB", (page_width, page_height), background_color)

        for idx, panel_image in enumerate(self.panels):
            if idx < len(self.layout.panel_sizes):
                x, y = self.layout.panel_position(idx)
                panel_width, panel_height = self.layout.panel_sizes[idx]

                # 调整面板图像大小
                if panel_image.size != (panel_width, panel_height):
                    panel_image = panel_image.resize(
                        (panel_width, panel_height), Image.Resampling.LANCZOS
                    )

                # 粘贴到页面
                page_image.paste(panel_image, (x, y))

        return page_image

    def add_panel_border(
        self,
        page_image: Image.Image,
        border_color: Tuple[int, int, int] = (0, 0, 0),
        border_width: int = 3,
    ) -> Image.Image:
        """为面板添加边框"""
        draw = ImageDraw.Draw(page_image)

        for idx in range(len(self.panels)):
            x, y = self.layout.panel_position(idx)
            panel_width, panel_height = self.layout.panel_sizes[idx]

            # 绘制边框
            draw.rectangle(
                [
                    x - border_width,
                    y - border_width,
                    x + panel_width + border_width,
                    y + panel_height + border_width,
                ],
                outline=border_color,
                width=border_width,
            )

        return page_image


class ComfyUIPanelsSimulator:
    """ComfyUI Panels插件模拟器"""

    # 预定义布局
    STANDARD_LAYOUTS = {
        "single": PanelLayout(
            name="single", description="单面板全页", rows=1, cols=1, panel_sizes=[(900, 1300)]
        ),
        "double_horizontal": PanelLayout(
            name="double_horizontal",
            description="水平双面板",
            rows=1,
            cols=2,
            panel_sizes=[(440, 600), (440, 600)],
        ),
        "double_vertical": PanelLayout(
            name="double_vertical",
            description="垂直双面板",
            rows=2,
            cols=1,
            panel_sizes=[(600, 440), (600, 440)],
        ),
        "four_panel": PanelLayout(
            name="four_panel",
            description="四格漫画",
            rows=2,
            cols=2,
            panel_sizes=[(420, 300), (420, 300), (420, 300), (420, 300)],
        ),
        "storyboard_9": PanelLayout(
            name="storyboard_9",
            description="9宫格故事板",
            rows=3,
            cols=3,
            panel_sizes=[(280, 200)] * 9,
        ),
        "storyboard_20": PanelLayout(
            name="storyboard_20",
            description="20宫格故事板(LTX2.3风格)",
            rows=4,
            cols=5,
            panel_sizes=[(220, 160)] * 20,
        ),
    }

    def __init__(self, comfyui_generator: Optional[ComfyUIAthenaGenerator] = None):
        self.generator = comfyui_generator
        self.output_dir = Path("/Volumes/1TB-M2/openclaw/comfyui_workspace/output/comic_pages")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_available_layouts(self) -> Dict[str, PanelLayout]:
        """获取可用布局"""
        return self.STANDARD_LAYOUTS.copy()

    def generate_panel_image(
        self, prompt: str, width: int, height: int, style: str = "comic_book", panel_index: int = 0
    ) -> Optional[Image.Image]:
        """生成单张面板图像"""
        if self.generator:
            # 使用ComfyUI生成图像
            try:
                # 为漫画面板优化提示词
                comic_prompt = self._enhance_prompt_for_comic(prompt, style, panel_index)

                # TODO: 实现ComfyUI工作流调用
                # 临时返回占位图像
                return self._create_placeholder_panel(width, height, comic_prompt, panel_index)
            except Exception as e:
                print(f"[ERROR] 生成面板图像失败: {e}")
                return self._create_placeholder_panel(width, height, prompt, panel_index)
        else:
            # 创建占位图像
            return self._create_placeholder_panel(width, height, prompt, panel_index)

    def _enhance_prompt_for_comic(self, base_prompt: str, style: str, panel_index: int) -> str:
        """为漫画生成增强提示词"""
        style_keywords = {
            "comic_book": "漫画书风格,动态线条,鲜艳色彩,对话框空间",
            "manga": "日本漫画风格,黑白线条,网点纸效果,夸张表情",
            "webtoon": "韩国网络漫画风格,长条滚动布局,现代画风",
            "graphic_novel": "图像小说风格,写实绘画,深沉色调,文学性",
            "athena_comic": "硅基共生AI女神Athena,赛博朋克漫画,机械生物融合,发光电路纹理",
        }

        style_desc = style_keywords.get(style, "漫画风格")
        panel_desc = f"漫画面板{panel_index+1},分镜画面,叙事性构图"

        return f"{base_prompt}, {style_desc}, {panel_desc}, 高质量漫画艺术, 清晰线条, 叙事性构图"

    def _create_placeholder_panel(
        self, width: int, height: int, prompt: str, panel_index: int
    ) -> Image.Image:
        """创建占位面板图像"""
        img = Image.new("RGB", (width, height), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)

        # 绘制边框
        draw.rectangle([5, 5, width - 5, height - 5], outline=(200, 200, 200), width=3)

        # 绘制面板编号
        try:
            # 尝试使用默认字体
            font = ImageFont.load_default()
            draw.text((20, 20), f"Panel {panel_index+1}", fill=(100, 100, 100), font=font)
        except:
            draw.text((20, 20), f"Panel {panel_index+1}", fill=(100, 100, 100))

        # 绘制提示词摘要
        prompt_summary = prompt[:50] + "..." if len(prompt) > 50 else prompt
        draw.text((width // 2 - 100, height // 2 - 10), prompt_summary, fill=(150, 150, 150))

        # 绘制"待生成"水印
        draw.text((width // 2 - 40, height // 2 + 30), "[待生成]", fill=(180, 180, 180))

        return img

    def generate_comic_page(
        self, layout_name: str, prompts: List[str], style: str = "comic_book", page_number: int = 1
    ) -> ComicPage:
        """生成完整漫画页面"""
        layout = self.STANDARD_LAYOUTS.get(layout_name)
        if not layout:
            raise ValueError(f"未知布局: {layout_name}")

        # 生成所有面板图像
        panels = []
        for idx, (prompt, panel_size) in enumerate(zip(prompts, layout.panel_sizes)):
            if idx >= len(layout.panel_sizes):
                break

            width, height = panel_size
            panel_image = self.generate_panel_image(prompt, width, height, style, idx)
            if panel_image:
                panels.append(panel_image)

        # 如果提示词数量少于面板数量，用默认提示词填充
        while len(panels) < len(layout.panel_sizes):
            default_prompt = f"漫画场景,风格:{style},面板:{len(panels)+1}"
            width, height = layout.panel_sizes[len(panels)]
            panel_image = self.generate_panel_image(
                default_prompt, width, height, style, len(panels)
            )
            panels.append(panel_image)

        # 创建漫画页面
        comic_page = ComicPage(
            layout=layout,
            panels=panels,
            page_number=page_number,
            metadata={
                "layout": layout_name,
                "style": style,
                "prompts": prompts,
                "generated_at": "2026-04-17",
            },
        )

        return comic_page

    def save_comic_page(self, comic_page: ComicPage, filename_prefix: str = "comic_page") -> Path:
        """保存漫画页面"""
        # 生成页面图像
        page_image = comic_page.create_page_image()
        page_image = comic_page.add_panel_border(page_image)

        # 保存文件
        filename = f"{filename_prefix}_{comic_page.page_number:03d}.png"
        output_path = self.output_dir / filename
        page_image.save(output_path, "PNG", quality=95)

        print(f"[SUCCESS] 漫画页面保存到: {output_path}")
        print(f"  布局: {comic_page.layout.name}")
        print(f"  面板数量: {len(comic_page.panels)}")
        print(f"  页面尺寸: {page_image.size}")

        return output_path

    def generate_comic_story(
        self, story_prompts: List[str], layout_name: str = "four_panel", style: str = "comic_book"
    ) -> List[Path]:
        """生成漫画故事（多页面）"""
        layout = self.STANDARD_LAYOUTS.get(layout_name)
        if not layout:
            raise ValueError(f"未知布局: {layout_name}")

        panels_per_page = len(layout.panel_sizes)
        total_panels = len(story_prompts)
        total_pages = math.ceil(total_panels / panels_per_page)

        print(f"[INFO] 生成漫画故事:")
        print(f"  总面板数: {total_panels}")
        print(f"  每页面板数: {panels_per_page}")
        print(f"  总页数: {total_pages}")
        print(f"  风格: {style}")

        saved_pages = []

        for page_num in range(total_pages):
            start_idx = page_num * panels_per_page
            end_idx = min(start_idx + panels_per_page, total_panels)
            page_prompts = story_prompts[start_idx:end_idx]

            print(f"  生成页面 {page_num+1}/{total_pages} (面板 {start_idx+1}-{end_idx})")

            comic_page = self.generate_comic_page(layout_name, page_prompts, style, page_num + 1)
            output_path = self.save_comic_page(comic_page, f"comic_story")
            saved_pages.append(output_path)

        return saved_pages

    def integrate_with_comfyui(self, server_url: str = "http://127.0.0.1:8189") -> bool:
        """集成到ComfyUI服务器"""
        try:
            import requests

            # 检查服务器状态
            response = requests.get(f"{server_url}/system_stats")
            if response.status_code == 200:
                print(f"[SUCCESS] ComfyUI服务器连接正常")

                # 注册自定义节点（模拟）
                # 真实集成需要将节点定义添加到ComfyUI的custom_nodes目录
                print(f"[INFO] 模拟注册ComfyUI Panels节点:")
                print(f"  - PanelLayoutNode: 面板布局定义")
                print(f"  - ComicPageGenerator: 漫画页面生成")
                print(f"  - StoryboardWorkflow: 故事板工作流")

                return True
            else:
                print(f"[ERROR] ComfyUI服务器连接失败: {response.status_code}")
                return False

        except Exception as e:
            print(f"[ERROR] ComfyUI集成失败: {e}")
            return False


def main():
    """主函数"""
    print("🎨 ComfyUI Panels插件集成测试")
    print("=" * 60)

    # 初始化
    simulator = ComfyUIPanelsSimulator()

    # 显示可用布局
    layouts = simulator.get_available_layouts()
    print(f"📐 可用布局 ({len(layouts)}):")
    for name, layout in layouts.items():
        total_width, total_height = layout.total_size()
        print(f"  {name}: {layout.description}")
        print(f"    面板: {layout.rows}x{layout.cols} ({len(layout.panel_sizes)}个)")
        print(f"    页面尺寸: {total_width}x{total_height}")

    print("\n" + "=" * 60)

    # 测试生成单页面
    print("🧪 测试四格漫画页面生成...")

    # 创建测试提示词
    test_prompts = [
        "硅基共生AI女神Athena的机械手臂特写,发光电路纹理",
        "Athena在数字空间中漂浮,周围是数据流和代码",
        "Athena与黑客AI对抗,电光火石的战斗场景",
        "Athena修复系统漏洞,蓝色能量从指尖流出",
    ]

    try:
        comic_page = simulator.generate_comic_page(
            layout_name="four_panel", prompts=test_prompts, style="athena_comic", page_number=1
        )

        output_path = simulator.save_comic_page(comic_page, "test_comic")
        print(f"✅ 测试页面生成成功: {output_path}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")

    print("\n" + "=" * 60)

    # 测试故事板生成
    print("🎬 测试LTX2.3风格故事板生成...")

    # 创建20个面板的简短故事
    story_prompts = []
    for i in range(20):
        story_prompts.append(f"AI女神Athena冒险场景{i+1},赛博朋克城市,动态镜头,漫画分镜")

    try:
        saved_pages = simulator.generate_comic_story(
            story_prompts=story_prompts, layout_name="storyboard_20", style="athena_comic"
        )

        print(f"✅ 故事板生成成功: {len(saved_pages)}页")
        for page_path in saved_pages:
            print(f"   - {page_path.name}")

    except Exception as e:
        print(f"❌ 故事板生成失败: {e}")

    print("\n" + "=" * 60)
    print("💡 下一步:")
    print("  1. 连接真实ComfyUI服务器生成高质量图像")
    print("  2. 获取真实comfyui_panels插件替换模拟器")
    print("  3. 集成到Clawra生产系统")
    print("  4. 添加对话气泡和文字排版")

    return 0


if __name__ == "__main__":
    sys.exit(main())
