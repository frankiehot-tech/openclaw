#!/usr/bin/env python3
"""
Kdenlive视频生成器 - 为Clawra提供Kdenlive广告级视频生成功能
兼容EnhancedVideoGenerationEngine接口
"""

import json
import os

# 导入Kdenlive集成
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

sys.path.append(os.path.dirname(__file__))

from kdenlive_integration import create_ad_level_video_project


class KdenliveVideoGenerator:
    """Kdenlive广告级视频生成器"""

    def __init__(self, output_dir: str = None):
        """
        初始化Kdenlive视频生成器

        Args:
            output_dir: 输出目录（如果为None则使用临时目录）
        """
        if output_dir is None:
            self.output_dir = tempfile.mkdtemp(prefix="clawra_kdenlive_")
        else:
            self.output_dir = output_dir
            os.makedirs(self.output_dir, exist_ok=True)

        print(f"Kdenlive视频生成器初始化完成，输出目录: {self.output_dir}")

    def generate_video(
        self,
        project_name: str = "广告级视频",
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        duration: int = 15,
        title_text: str = None,
        product_text: str = None,
        call_to_action_text: str = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        生成广告级视频

        Args:
            project_name: 项目名称
            width: 视频宽度
            height: 视频高度
            fps: 帧率
            duration: 视频时长（秒）
            title_text: 标题文本（暂未实现，使用默认）
            product_text: 产品描述文本（暂未实现，使用默认）
            call_to_action_text: 号召性用语文本（暂未实现，使用默认）

        Returns:
            (success, project_file, xml_file) 元组
        """
        print(f"开始生成Kdenlive广告级视频: {project_name}")

        # 调用Kdenlive集成模块
        success, project_file, xml_file = create_ad_level_video_project(
            output_dir=self.output_dir,
            project_name=project_name,
            width=width,
            height=height,
            fps_num=fps,
            fps_den=1,
            duration=duration,
        )

        if success:
            print(f"✅ 视频生成成功: {project_name}")
            print(f"   项目文件: {project_file}")
            print(f"   XML文件: {xml_file}")

            # 生成渲染命令
            render_cmd = self.generate_render_command(xml_file)
            print(f"   渲染命令: {render_cmd}")

            # 生成项目摘要
            summary = self.generate_project_summary(project_file)
            print(f"   项目摘要:\n{summary}")

            return True, project_file, xml_file
        else:
            print(f"❌ 视频生成失败: {project_name}")
            return False, None, None

    def generate_render_command(self, xml_file: str) -> str:
        """生成melt渲染命令"""
        if not xml_file or not os.path.exists(xml_file):
            return "无有效的XML文件"

        # 基础渲染命令
        output_file = xml_file.replace(".xml", ".mp4")
        cmd = f"melt {xml_file} -consumer avformat:{output_file}"

        # 添加质量参数（广告级）
        cmd += " vcodec=libx264 crf=18 preset=slow acodec=aac ab=192k"

        return cmd

    def generate_project_summary(self, project_file: str) -> str:
        """生成项目摘要"""
        if not os.path.exists(project_file):
            return "项目文件不存在"

        try:
            with open(project_file, "r") as f:
                project_data = json.load(f)

            tracks = project_data.get("tracks", [])
            bin_clips = project_data.get("bin", [])
            profile = project_data.get("profile", {})

            summary_lines = []
            summary_lines.append(f"项目名称: {project_data.get('name', 'N/A')}")
            summary_lines.append(
                f"分辨率: {profile.get('width', 'N/A')}x{profile.get('height', 'N/A')}"
            )
            summary_lines.append(
                f"帧率: {profile.get('fps_num', 'N/A')}/{profile.get('fps_den', 'N/A')}"
            )
            summary_lines.append(f"轨道数: {len(tracks)}")
            summary_lines.append(f"素材库剪辑数: {len(bin_clips)}")

            # 轨道详情
            summary_lines.append("轨道详情:")
            for i, track in enumerate(tracks):
                clip_count = len(track.get("clips", []))
                summary_lines.append(
                    f"  [{i}] {track['name']} ({track['type']}): {clip_count} 个剪辑"
                )

            return "\n".join(summary_lines)

        except Exception as e:
            return f"生成摘要时出错: {str(e)}"

    def get_output_files(self) -> Dict[str, str]:
        """获取输出目录中的所有文件"""
        files = {}
        if os.path.exists(self.output_dir):
            for f in os.listdir(self.output_dir):
                if f.endswith((".json", ".xml", ".mp4", ".mov", ".mkv")):
                    files[f] = os.path.join(self.output_dir, f)
        return files


def test_generator():
    """测试生成器"""
    print("=== 测试Kdenlive视频生成器 ===")

    # 创建生成器
    generator = KdenliveVideoGenerator(output_dir="/tmp/clawra_kdenlive_generator_test")

    # 生成视频
    success, project_file, xml_file = generator.generate_video(
        project_name="测试广告视频", width=1280, height=720, fps=30, duration=10
    )

    if success:
        print(f"\n✅ 生成器测试成功")
        print(f"输出文件:")
        for name, path in generator.get_output_files().items():
            print(f"  {name}: {path}")
        return True
    else:
        print(f"\n❌ 生成器测试失败")
        return False


if __name__ == "__main__":
    import sys

    if test_generator():
        print("\n✅ Kdenlive视频生成器测试通过")
        sys.exit(0)
    else:
        print("\n❌ Kdenlive视频生成器测试失败")
        sys.exit(1)
