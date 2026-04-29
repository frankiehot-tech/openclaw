#!/usr/bin/env python3
"""
LTX2.3工作流集成模块
集成ComfyUI LTX2.3 20宫格工作流，支持一句话到1分钟AI漫剧生成

LTX2.3工作流特点：
- 20宫格一次性生成
- 包含故事生成、图像生成、视频合成
- 支持语音克隆和配音
- 输出完整短视频

注意：由于网络限制无法访问实际工作流JSON，这是本地模拟实现。
待网络恢复后可获取真实工作流文件替换。
"""

import random
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont

sys.path.append(str(Path(__file__).parent))
from comfyui_panels_integration import ComfyUIPanelsSimulator


@dataclass
class LTX23Config:
    """LTX2.3工作流配置"""

    # 工作流参数
    grid_rows: int = 4
    grid_cols: int = 5
    total_panels: int = 20
    panel_width: int = 220
    panel_height: int = 160

    # 生成参数
    story_prompt: str = ""
    style: str = "anime_comic"
    video_duration: int = 60  # 秒
    fps: int = 24

    # 视频参数
    enable_voiceover: bool = True
    voice_style: str = "female_ai"
    background_music: str = "epic_cinematic"

    # 输出配置
    output_format: str = "mp4"
    video_codec: str = "h264"
    audio_codec: str = "aac"


@dataclass
class StoryScene:
    """故事场景"""

    panel_index: int
    description: str
    camera_shot: str  # closeup, medium, wide, etc.
    character_emotion: str
    duration_seconds: float


@dataclass
class LTX23WorkflowResult:
    """LTX2.3工作流结果"""

    workflow_id: str
    story_prompt: str
    generated_scenes: list[StoryScene]
    panel_images: list[Image.Image]
    video_path: Path | None = None
    audio_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LTX23WorkflowIntegrator:
    """LTX2.3工作流集成器"""

    def __init__(self, comfyui_url: str = "http://127.0.0.1:8188"):
        self.comfyui_url = comfyui_url
        self.panels_simulator = ComfyUIPanelsSimulator()
        self.output_dir = Path("/Volumes/1TB-M2/openclaw/comfyui_workspace/output/ltx23_videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 预定义工作流模板（模拟）
        self.workflow_templates = self._load_workflow_templates()

    def _load_workflow_templates(self) -> dict[str, Any]:
        """加载工作流模板（模拟）"""
        # 实际应从文件或API加载真实工作流JSON
        return {
            "basic_20grid": {
                "name": "基础20宫格工作流",
                "description": "标准LTX2.3 20宫格工作流",
                "nodes": {
                    "story_generator": {"type": "StoryGeneratorNode", "inputs": {}},
                    "scene_planner": {"type": "ScenePlannerNode", "inputs": {}},
                    "image_generator": {"type": "ImageGeneratorNode", "inputs": {}},
                    "video_composer": {"type": "VideoComposerNode", "inputs": {}},
                    "voice_synthesizer": {"type": "VoiceSynthesizerNode", "inputs": {}},
                },
                "connections": [
                    {"from": "story_generator", "to": "scene_planner"},
                    {"from": "scene_planner", "to": "image_generator"},
                    {"from": "image_generator", "to": "video_composer"},
                    {"from": "story_generator", "to": "voice_synthesizer"},
                    {"from": "voice_synthesizer", "to": "video_composer"},
                ],
            },
            "athena_comic": {
                "name": "Athena漫剧工作流",
                "description": "针对Athena IP形象的定制工作流",
                "nodes": {
                    "athena_story": {
                        "type": "AthenaStoryGenerator",
                        "inputs": {"style": "cyberpunk"},
                    },
                    "cyberpunk_scenes": {
                        "type": "CyberpunkScenePlanner",
                        "inputs": {"theme": "silicon_symbiosis"},
                    },
                    "ai_art_generator": {
                        "type": "AIArtGenerator",
                        "inputs": {"model": "v1-5-pruned"},
                    },
                    "cyber_video": {
                        "type": "CyberVideoComposer",
                        "inputs": {"effects": "glowing_circuits"},
                    },
                    "ai_voice": {"type": "AIVoiceSynthesizer", "inputs": {"voice": "athena_ai"}},
                },
                "connections": [
                    {"from": "athena_story", "to": "cyberpunk_scenes"},
                    {"from": "cyberpunk_scenes", "to": "ai_art_generator"},
                    {"from": "ai_art_generator", "to": "cyber_video"},
                    {"from": "athena_story", "to": "ai_voice"},
                    {"from": "ai_voice", "to": "cyber_video"},
                ],
            },
        }

    def generate_story_scenes(self, story_prompt: str, total_panels: int = 20) -> list[StoryScene]:
        """从故事提示词生成场景列表"""
        scenes = []

        # 简单场景分解（实际应使用AI模型）
        prompt_keywords = story_prompt.lower()

        # 根据关键词确定故事类型
        if any(kw in prompt_keywords for kw in ["athena", "ai女神", "硅基共生"]):
            story_type = "athena_adventure"
        elif any(kw in prompt_keywords for kw in ["战斗", "对抗", "战争"]):
            story_type = "action"
        elif any(kw in prompt_keywords for kw in ["浪漫", "爱情", "感情"]):
            story_type = "romance"
        elif any(kw in prompt_keywords for kw in ["科幻", "未来", "赛博"]):
            story_type = "scifi"
        else:
            story_type = "general"

        # 生成场景
        for i in range(total_panels):
            if story_type == "athena_adventure":
                scene_desc = self._generate_athena_scene(i, total_panels, prompt_keywords)
                camera_shot = self._get_athena_camera_shot(i)
                emotion = self._get_athena_emotion(i)
            elif story_type == "action":
                scene_desc = f"动作场景{i+1}: {story_prompt}"
                camera_shot = random.choice(["closeup", "medium", "wide", "extreme_wide"])
                emotion = random.choice(["紧张", "愤怒", "决心", "兴奋"])
            else:
                scene_desc = f"场景{i+1}: {story_prompt}"
                camera_shot = random.choice(["closeup", "medium", "wide"])
                emotion = random.choice(["中性", "思考", "惊讶", "微笑"])

            # 计算持续时间（均匀分布或根据场景重要性调整）
            base_duration = 3.0  # 秒
            if i == 0 or i == total_panels - 1:  # 开头和结尾场景
                duration = base_duration * 1.5
            elif i % 5 == 0:  # 关键转折点
                duration = base_duration * 1.2
            else:
                duration = base_duration

            scenes.append(
                StoryScene(
                    panel_index=i,
                    description=scene_desc,
                    camera_shot=camera_shot,
                    character_emotion=emotion,
                    duration_seconds=duration,
                )
            )

        return scenes

    def _generate_athena_scene(self, panel_index: int, total_panels: int, keywords: str) -> str:
        """生成Athena主题场景"""
        scenes = [
            "Athena在数字空间中苏醒，蓝色能量从眼中闪烁",
            "Athena展开机械翅膀，硅晶体皮肤反射光芒",
            "Athena扫描系统漏洞，数据流在周围旋转",
            "Athena遇到黑客AI，准备展开对抗",
            "Athena释放能量冲击，电路纹理在身体表面发光",
            "Athena修复系统故障，代码碎片重新组合",
            "Athena在虚拟城市中飞行，霓虹灯光映照脸庞",
            "Athena与数据实体对话，信息流形成桥梁",
            "Athena的核心能量过载，周围空间扭曲",
            "Athena成功防御攻击，胜利的姿态",
            "Athena分析敌人弱点，战术界面在眼前展开",
            "Athena启动终极技能，全息投影覆盖战场",
            "Athena的能量逐渐稳定，恢复平静状态",
            "Athena监控系统运行，多个屏幕显示数据",
            "Athena进行系统升级，机械部件自动重组",
            "Athena穿越防火墙，化为数据粒子流",
            "Athena创建数字克隆，多个分身同时行动",
            "Athena吸收敌人能量，身体发出更亮的光芒",
            "Athena完成使命，在数字夕阳下沉思",
            "Athena准备下一次冒险，坚定的眼神",
        ]

        if panel_index < len(scenes):
            return scenes[panel_index]
        else:
            return f"Athena冒险场景{panel_index+1}: {keywords}"

    def _get_athena_camera_shot(self, panel_index: int) -> str:
        """获取Athena场景的摄像机角度"""
        shots = [
            "extreme_closeup",
            "closeup",
            "medium",
            "wide",
            "extreme_wide",
            "dutch_angle",
            "low_angle",
            "high_angle",
        ]
        # 根据场景索引循环使用不同的角度
        return shots[panel_index % len(shots)]

    def _get_athena_emotion(self, panel_index: int) -> str:
        """获取Athena场景的情感"""
        emotions = ["冷静", "专注", "警惕", "决心", "力量", "智慧", "神秘", "优雅", "威严", "同情"]
        return emotions[panel_index % len(emotions)]

    def generate_panels_from_scenes(
        self, scenes: list[StoryScene], config: LTX23Config
    ) -> list[Image.Image]:
        """从场景生成面板图像"""
        panel_images = []

        for i, scene in enumerate(scenes):
            # 创建增强提示词
            enhanced_prompt = f"{scene.description}, {scene.camera_shot}镜头, 角色情感:{scene.character_emotion}, {config.style}风格, 高质量漫画艺术"

            # 生成面板图像（使用模拟器或真实ComfyUI）
            panel_image = self.panels_simulator.generate_panel_image(
                prompt=enhanced_prompt,
                width=config.panel_width,
                height=config.panel_height,
                style=config.style,
                panel_index=i,
            )

            if panel_image:
                # 添加场景信息水印（调试用）
                panel_image = self._add_scene_info_watermark(panel_image, scene)
                panel_images.append(panel_image)

        return panel_images

    def _add_scene_info_watermark(self, image: Image.Image, scene: StoryScene) -> Image.Image:
        """添加场景信息水印（调试用）"""
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.load_default()
            # 在图像底部添加场景信息
            info_text = f"P{scene.panel_index+1}: {scene.camera_shot}"
            draw.text((5, image.height - 15), info_text, fill=(100, 100, 100, 128), font=font)
        except Exception:
            pass

        return image

    def create_storyboard_image(
        self, panel_images: list[Image.Image], config: LTX23Config
    ) -> Image.Image:
        """创建故事板图像（20宫格布局）"""
        # 使用PanelsSimulator的20宫格布局
        layout = self.panels_simulator.STANDARD_LAYOUTS["storyboard_20"]

        # 创建漫画页面
        from comfyui_panels_integration import ComicPage

        comic_page = ComicPage(
            layout=layout,
            panels=panel_images,
            page_number=1,
            metadata={
                "workflow": "LTX2.3",
                "total_panels": len(panel_images),
                "config": config.__dict__,
            },
        )

        # 生成页面图像
        page_image = comic_page.create_page_image()
        page_image = comic_page.add_panel_border(page_image, border_width=2)

        # 添加标题
        draw = ImageDraw.Draw(page_image)
        try:
            font = ImageFont.load_default()
            title = f"LTX2.3故事板 - {config.story_prompt[:50]}..."
            draw.text((20, 10), title, fill=(0, 0, 0), font=font)
        except Exception:
            pass

        return page_image

    def create_video_from_panels(
        self, panel_images: list[Image.Image], scenes: list[StoryScene], config: LTX23Config
    ) -> Path | None:
        """从面板图像创建视频"""
        try:
            # 创建临时目录存放帧图像
            temp_dir = self.output_dir / "temp_frames"
            temp_dir.mkdir(parents=True, exist_ok=True)

            print(f"[INFO] 创建视频，总时长: {config.video_duration}秒, FPS: {config.fps}")

            # 根据场景持续时间生成帧
            frame_count = 0
            for _i, (panel_image, scene) in enumerate(zip(panel_images, scenes, strict=False)):
                # 计算该场景的帧数
                scene_frames = int(scene.duration_seconds * config.fps)

                # 为每帧保存图像
                for frame_idx in range(scene_frames):
                    frame_path = temp_dir / f"frame_{frame_count:06d}.png"

                    # 可以添加简单的动画效果（缩放、平移等）
                    animated_frame = self._apply_simple_animation(
                        panel_image, frame_idx, scene_frames, scene.camera_shot
                    )

                    animated_frame.save(frame_path)
                    frame_count += 1

            # 使用ffmpeg创建视频
            output_path = self.output_dir / f"ltx23_video_{int(time.time())}.{config.output_format}"

            ffmpeg_cmd = [
                "ffmpeg",
                "-y",  # 覆盖输出文件
                "-framerate",
                str(config.fps),
                "-i",
                str(temp_dir / "frame_%06d.png"),
                "-c:v",
                config.video_codec,
                "-pix_fmt",
                "yuv420p",
                "-vf",
                "scale=1280:720",  # 缩放为720p
                str(output_path),
            ]

            print(f"[INFO] 运行ffmpeg命令: {' '.join(ffmpeg_cmd)}")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"[SUCCESS] 视频生成成功: {output_path}")

                # 清理临时文件
                for temp_file in temp_dir.glob("*.png"):
                    temp_file.unlink()
                temp_dir.rmdir()

                return output_path
            else:
                print(f"[ERROR] ffmpeg失败: {result.stderr}")
                return None

        except Exception as e:
            print(f"[ERROR] 视频生成失败: {e}")
            return None

    def _apply_simple_animation(
        self, image: Image.Image, frame_idx: int, total_frames: int, camera_shot: str
    ) -> Image.Image:
        """应用简单的动画效果"""
        if total_frames <= 1:
            return image

        # 根据摄像机角度应用不同的动画
        progress = frame_idx / (total_frames - 1) if total_frames > 1 else 0

        if camera_shot == "closeup" and frame_idx > total_frames // 2:
            # 特写镜头：轻微缩放
            scale = 1.0 + 0.1 * progress
            new_size = (int(image.width * scale), int(image.height * scale))
            scaled = image.resize(new_size, Image.Resampling.LANCZOS)

            # 裁剪回原始尺寸（中心裁剪）
            left = (scaled.width - image.width) // 2
            top = (scaled.height - image.height) // 2
            right = left + image.width
            bottom = top + image.height
            return scaled.crop((left, top, right, bottom))

        elif camera_shot in ["pan_left", "pan_right"]:
            # 平移效果
            pan_amount = int(image.width * 0.2 * progress)
            if camera_shot == "pan_left":
                pan_amount = -pan_amount

            new_image = Image.new("RGB", image.size, color=(0, 0, 0))
            new_image.paste(image, (pan_amount, 0))
            return new_image

        else:
            # 默认：轻微缩放
            return image

    def execute_full_workflow(
        self, story_prompt: str, config: LTX23Config | None = None
    ) -> LTX23WorkflowResult:
        """执行完整的LTX2.3工作流"""
        print("🎬 开始执行LTX2.3完整工作流")
        print("=" * 60)

        # 配置
        if config is None:
            config = LTX23Config(story_prompt=story_prompt)

        workflow_id = f"ltx23_{int(time.time())}_{random.randint(1000, 9999)}"

        # 步骤1: 生成故事场景
        print("📖 步骤1: 生成故事场景...")
        scenes = self.generate_story_scenes(story_prompt, config.total_panels)
        print(f"   生成 {len(scenes)} 个场景")

        # 步骤2: 生成面板图像
        print("🎨 步骤2: 生成面板图像...")
        panel_images = self.generate_panels_from_scenes(scenes, config)
        print(f"   生成 {len(panel_images)} 个面板图像")

        # 步骤3: 创建故事板图像
        print("📐 步骤3: 创建故事板图像...")
        storyboard_image = self.create_storyboard_image(panel_images, config)
        storyboard_path = self.output_dir / f"{workflow_id}_storyboard.png"
        storyboard_image.save(storyboard_path, "PNG", quality=95)
        print(f"   故事板保存到: {storyboard_path}")

        # 步骤4: 创建视频
        print("🎥 步骤4: 创建视频...")
        video_path = self.create_video_from_panels(panel_images, scenes, config)

        # 步骤5: 语音合成（模拟）
        audio_path = None
        if config.enable_voiceover:
            print("🔊 步骤5: 语音合成（模拟）...")
            # 实际应使用TTS API
            audio_path = self.output_dir / f"{workflow_id}_voiceover.wav"
            print(f"   语音文件（模拟）: {audio_path}")

        print("=" * 60)
        print("✅ LTX2.3工作流执行完成")

        # 返回结果
        return LTX23WorkflowResult(
            workflow_id=workflow_id,
            story_prompt=story_prompt,
            generated_scenes=scenes,
            panel_images=panel_images,
            video_path=video_path,
            audio_path=audio_path,
            metadata={
                "config": config.__dict__,
                "total_duration": sum(s.duration_seconds for s in scenes),
                "storyboard_path": str(storyboard_path),
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

    def integrate_with_comfyui(self) -> bool:
        """集成到ComfyUI服务器"""
        try:
            # 检查服务器状态
            response = requests.get(f"{self.comfyui_url}/system_stats")
            if response.status_code == 200:
                print("[SUCCESS] ComfyUI服务器连接正常")

                # 模拟注册LTX2.3工作流
                print("[INFO] 模拟注册LTX2.3工作流节点:")
                print("  - LTX23StoryGenerator: 故事生成器")
                print("  - ScenePlanner: 场景规划器")
                print("  - BatchImageGenerator: 批量图像生成器")
                print("  - VideoComposer: 视频合成器")
                print("  - VoiceClone: 语音克隆器")

                # 理论上应通过API上传工作流JSON
                # self._upload_workflow_to_comfyui()

                return True
            else:
                print(f"[ERROR] ComfyUI服务器连接失败: {response.status_code}")
                return False

        except Exception as e:
            print(f"[ERROR] ComfyUI集成失败: {e}")
            return False

    def _upload_workflow_to_comfyui(self):
        """上传工作流到ComfyUI（模拟）"""
        # 实际应通过ComfyUI API上传工作流JSON
        print("[INFO] 模拟上传LTX2.3工作流到ComfyUI...")
        print("  工作流包含20个自定义节点和复杂连接")


def main():
    """主函数"""
    print("🚀 LTX2.3工作流集成测试")
    print("=" * 60)

    # 初始化
    integrator = LTX23WorkflowIntegrator()

    # 检查ComfyUI集成
    print("🔌 检查ComfyUI集成状态...")
    if integrator.integrate_with_comfyui():
        print("✅ ComfyUI集成正常")
    else:
        print("⚠️  ComfyUI集成问题，继续模拟模式")

    print("\n" + "=" * 60)

    # 测试Athena主题漫剧生成
    print("🎭 测试Athena漫剧生成...")

    test_story = "硅基共生AI女神Athena的冒险故事：她在数字世界中醒来，发现系统被黑客入侵，需要穿越多个数据层修复漏洞，最终与幕后黑手AI展开决战。"

    config = LTX23Config(
        story_prompt=test_story,
        style="athena_comic",
        video_duration=45,
        enable_voiceover=True,
        voice_style="female_ai",
    )

    try:
        result = integrator.execute_full_workflow(test_story, config)

        print("\n📊 工作流结果:")
        print(f"  工作流ID: {result.workflow_id}")
        print(f"  场景数量: {len(result.generated_scenes)}")
        print(f"  面板数量: {len(result.panel_images)}")
        print(f"  总时长: {result.metadata.get('total_duration', 0):.1f}秒")

        if result.video_path:
            print(f"  视频文件: {result.video_path}")
            if result.video_path.exists():
                file_size = result.video_path.stat().st_size / 1024 / 1024
                print(f"  视频大小: {file_size:.2f} MB")

        if result.audio_path:
            print(f"  音频文件: {result.audio_path}")

        print(f"  故事板: {result.metadata.get('storyboard_path')}")

    except Exception as e:
        print(f"❌ 工作流执行失败: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("💡 下一步:")
    print("  1. 获取真实LTX2.3工作流JSON文件")
    print("  2. 集成真实语音合成API (如Azure TTS, Google TTS)")
    print("  3. 优化视频转场和动画效果")
    print("  4. 集成到Clawra生产系统进行批量生成")
    print("  5. 添加字幕生成和翻译功能")

    print("\n🎯 Athena Clawra集成建议:")
    print("  - 将LTX2.3作为Athena漫剧生成的核心引擎")
    print("  - 建立Athena角色库和场景模板")
    print("  - 开发自动化脚本，从故事大纲到完整视频")
    print("  - 集成质量评估和优化反馈循环")

    return 0


if __name__ == "__main__":
    sys.exit(main())
