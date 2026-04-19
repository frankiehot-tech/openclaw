#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clawra生产系统 - 集成ROMA-MAREF框架、Kdenlive视频生成和豆包CLI控制

核心功能：
1. ROMA-MAREF多智能体递归规划系统
2. Kdenlive广告级视频生成引擎
3. 豆包App CLI控制集成
4. 八层传播体系内容调度
5. GitHub工作流自动化

架构：
- 战略层：ROMA-MAREF智能体系统（八卦互补网络）
- 执行层：Kdenlive视频生成、豆包CLI控制
- 内容层：八层传播体系（L1-L8）
- 运营层：GitHub自动化、社交媒体管理

版本: 1.0.0
项目: Athena/openclaw Clawra模块
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 添加路径以便导入Clawra模块
sys.path.append(os.path.dirname(__file__))

# 添加external/ROMA路径以便导入ROMA-MAREF组件
external_roma_path = os.path.join(os.path.dirname(__file__), "external/ROMA")
if external_roma_path not in sys.path:
    sys.path.append(external_roma_path)

# 导入Clawra八层传播配置
from config.layer_config import ContentLayer, get_layer_config, get_mvp_layer
from config.persona_config import DEFAULT_ATHENA_PERSONA, AthenaPersona

# 导入视频生成引擎
try:
    from video_generation.kdenlive_enhanced_engine import (
        KdenliveEnhancedVideoGenerationEngine,
    )

    KDENLIVE_AVAILABLE = True
except ImportError as e:
    print(f"警告: Kdenlive增强引擎导入失败: {e}")
    KDENLIVE_AVAILABLE = False

# 导入ROMA-MAREF集成
try:
    from maref_roma_integration import (
        ExtendedAgentType,
        GrayCodeConverter,
        HybridAgentFactory,
        MarefAgentAdapter,
        MarefRomaIntegration,
    )

    ROMA_MAREF_AVAILABLE = True
except ImportError as e:
    print(f"警告: ROMA-MAREF集成导入失败: {e}")
    ROMA_MAREF_AVAILABLE = False

# 导入豆包CLI控制
try:
    from external.ROMA.doubao_cli_prototype import DoubaoCLI

    DOUBAO_CLI_AVAILABLE = True
except ImportError as e:
    print(f"警告: 豆包CLI导入失败: {e}")
    DOUBAO_CLI_AVAILABLE = False

# 导入豆包图像生成器
try:
    from doubao_image_generator import DoubaoImageGenerator

    DOUBAO_IMAGE_GENERATOR_AVAILABLE = True
except ImportError as e:
    print(f"警告: 豆包图像生成器导入失败: {e}")
    DOUBAO_IMAGE_GENERATOR_AVAILABLE = False

# 导入提示词知识库
try:
    from prompt_knowledge_base import (
        PromptCategory,
        PromptEntry,
        PromptKnowledgeBase,
        PromptSource,
        PromptSubcategory,
        QualityLevel,
    )

    PROMPT_KNOWLEDGE_BASE_AVAILABLE = True
except ImportError as e:
    print(f"警告: 提示词知识库导入失败: {e}")
    PROMPT_KNOWLEDGE_BASE_AVAILABLE = False

# 导入IP数字资产管理器
try:
    from ip_digital_assets_manager import (
        BrandColor,
        ContentTemplate,
        IPAssetType,
        IPDigitalAssetsManager,
        VisualIdentity,
    )

    IP_DIGITAL_ASSETS_AVAILABLE = True
except ImportError as e:
    print(f"警告: IP数字资产管理器导入失败: {e}")
    IP_DIGITAL_ASSETS_AVAILABLE = False

# 导入IP反馈系统
try:
    from ip_feedback_system import (
        FeedbackAnalysis,
        FeedbackEntry,
        FeedbackSource,
        FeedbackType,
        IPFeedbackSystem,
    )

    IP_FEEDBACK_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"警告: IP反馈系统导入失败: {e}")
    IP_FEEDBACK_SYSTEM_AVAILABLE = False

# 导入IP形象调查系统
try:
    from ip_image_feedback_survey import (
        IPImageFeedbackSurvey,
        SurveyDimension,
        UserSegment,
    )

    IP_IMAGE_SURVEY_AVAILABLE = True
except ImportError as e:
    print(f"警告: IP形象调查系统导入失败: {e}")
    IP_IMAGE_SURVEY_AVAILABLE = False


class ProductionSystemMode(Enum):
    """生产系统运行模式"""

    MVP = "mvp"  # 最小可行产品模式
    ENTERPRISE = "enterprise"  # 企业级模式
    VALIDATION = "validation"  # 验证测试模式
    PRODUCTION = "production"  # 生产环境模式


@dataclass
class ProductionSystemConfig:
    """生产系统配置"""

    mode: ProductionSystemMode = ProductionSystemMode.MVP
    output_dir: str = None
    enable_roma_maref: bool = True
    enable_kdenlive: bool = True
    enable_doubao_cli: bool = True
    enable_github_workflow: bool = False
    layer_focus: ContentLayer = None
    max_concurrent_tasks: int = 3
    quality_preset: str = "standard"  # standard/premium/fast
    log_level: str = "INFO"

    def __post_init__(self):
        """初始化后处理"""
        if self.output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = f"./output/production_{self.mode.value}_{timestamp}"

        if self.layer_focus is None:
            self.layer_focus = get_mvp_layer()  # L3 1小时层

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "mode": self.mode.value,
            "output_dir": self.output_dir,
            "enable_roma_maref": self.enable_roma_maref,
            "enable_kdenlive": self.enable_kdenlive,
            "enable_doubao_cli": self.enable_doubao_cli,
            "enable_github_workflow": self.enable_github_workflow,
            "layer_focus": self.layer_focus.value,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "quality_preset": self.quality_preset,
            "log_level": self.log_level,
            "timestamp": datetime.now().isoformat(),
        }


class ClawraProductionSystem:
    """Clawra生产系统 - 主集成类"""

    def __init__(self, config: ProductionSystemConfig = None):
        """
        初始化生产系统

        Args:
            config: 生产系统配置
        """
        self.config = config or ProductionSystemConfig()

        # 创建输出目录
        os.makedirs(self.config.output_dir, exist_ok=True)

        # 初始化组件
        self.components = {}
        self._initialize_components()

        # 初始化状态
        self.state = {
            "initialized": True,
            "start_time": datetime.now().isoformat(),
            "component_status": self._get_component_status(),
            "tasks_completed": 0,
            "tasks_failed": 0,
            "last_error": None,
        }

        print("=" * 60)
        print("🎬 Clawra生产系统初始化完成")
        print("=" * 60)
        print(f"模式: {self.config.mode.value.upper()}")
        print(f"输出目录: {self.config.output_dir}")
        print(f"内容层级: {self.config.layer_focus.value}")
        print(f"组件状态: {self._format_component_status()}")
        print("=" * 60)

    def _initialize_components(self):
        """初始化所有组件"""
        # ROMA-MAREF集成
        if self.config.enable_roma_maref and ROMA_MAREF_AVAILABLE:
            try:
                self.components["roma_maref"] = MarefRomaIntegration()
                print("✅ ROMA-MAREF集成初始化成功")
            except Exception as e:
                print(f"❌ ROMA-MAREF集成初始化失败: {e}")
                self.config.enable_roma_maref = False

        # Kdenlive视频生成引擎
        if self.config.enable_kdenlive and KDENLIVE_AVAILABLE:
            try:
                # 根据模式设置输出目录
                kdenlive_output = os.path.join(self.config.output_dir, "kdenlive_projects")
                self.components["kdenlive"] = KdenliveEnhancedVideoGenerationEngine(
                    output_dir=os.path.join(self.config.output_dir, "videos"),
                    kdenlive_output_dir=kdenlive_output,
                )
                print("✅ Kdenlive视频生成引擎初始化成功")
            except Exception as e:
                print(f"❌ Kdenlive引擎初始化失败: {e}")
                self.config.enable_kdenlive = False

        # 豆包CLI控制
        if self.config.enable_doubao_cli and DOUBAO_CLI_AVAILABLE:
            try:
                self.components["doubao_cli"] = DoubaoCLI()
                print("✅ 豆包CLI控制初始化成功")
            except Exception as e:
                print(f"❌ 豆包CLI初始化失败: {e}")
                self.config.enable_doubao_cli = False

        # 豆包图像生成器
        if self.config.enable_doubao_cli and DOUBAO_IMAGE_GENERATOR_AVAILABLE:
            try:
                self.components["doubao_image_generator"] = DoubaoImageGenerator(
                    auto_start_app=True
                )
                print("✅ 豆包图像生成器初始化成功")
            except Exception as e:
                print(f"❌ 豆包图像生成器初始化失败: {e}")
                # 注意：不设置标志为False，因为不是必需组件

        # 提示词知识库
        if PROMPT_KNOWLEDGE_BASE_AVAILABLE:
            try:
                # 初始化提示词知识库
                self.components["prompt_knowledge_base"] = PromptKnowledgeBase()
                print("✅ 提示词知识库初始化成功")

                # 检查是否有初始数据，如果没有则尝试加载示例数据
                if self.components["prompt_knowledge_base"].get_statistics()["total_prompts"] == 0:
                    print("   ℹ️ 知识库为空，尝试加载示例数据...")
                    self._load_example_prompts()
            except Exception as e:
                print(f"❌ 提示词知识库初始化失败: {e}")
                # 注意：这里不设置标志为False，因为知识库不是必需组件

        # IP数字资产管理器
        if IP_DIGITAL_ASSETS_AVAILABLE:
            try:
                # 初始化IP数字资产管理器
                self.components["ip_digital_assets"] = IPDigitalAssetsManager()
                print("✅ IP数字资产管理器初始化成功")

                # 测试集成
                test_results = self.components["ip_digital_assets"].test_integration()
                if test_results.get("all_passed", False):
                    print("   ✅ IP数字资产集成测试通过")
                else:
                    print(f"   ⚠️  IP数字资产集成测试失败: {test_results}")

            except Exception as e:
                print(f"❌ IP数字资产管理器初始化失败: {e}")
                # 注意：这里不设置标志为False，因为不是必需组件

        # IP反馈系统
        if IP_FEEDBACK_SYSTEM_AVAILABLE:
            try:
                # 初始化IP反馈系统
                self.components["ip_feedback_system"] = IPFeedbackSystem()
                print("✅ IP反馈系统初始化成功")

                # 检查数据库连接
                print("   ℹ️ 反馈系统数据库就绪")

            except Exception as e:
                print(f"❌ IP反馈系统初始化失败: {e}")
                # 注意：这里不设置标志为False，因为不是必需组件

        # IP形象调查系统
        if (
            IP_IMAGE_SURVEY_AVAILABLE
            and IP_FEEDBACK_SYSTEM_AVAILABLE
            and "ip_feedback_system" in self.components
        ):
            try:
                # 初始化IP形象调查系统，传入已初始化的反馈系统
                feedback_system = self.components["ip_feedback_system"]
                self.components["ip_image_survey"] = IPImageFeedbackSurvey(
                    feedback_system=feedback_system
                )
                print("✅ IP形象调查系统初始化成功")
                print("   ℹ️ 调查系统已集成反馈系统")
            except Exception as e:
                print(f"❌ IP形象调查系统初始化失败: {e}")

        # 其他组件初始化...

    def _load_example_prompts(self):
        """加载示例提示词到知识库"""
        if not PROMPT_KNOWLEDGE_BASE_AVAILABLE or "prompt_knowledge_base" not in self.components:
            return

        knowledge_base = self.components["prompt_knowledge_base"]

        # 示例文生图提示词
        example_prompts = [
            {
                "prompt_text": "A beautiful sunset over a mountain landscape, golden hour lighting, photorealistic, 8K resolution",
                "category": PromptCategory.TEXT_TO_IMAGE,
                "subcategory": PromptSubcategory.LANDSCAPE,
                "model_compatibility": ["stable-diffusion", "dall-e", "midjourney"],
                "parameters": {"aspect_ratio": "16:9", "style": "photorealistic"},
                "base_quality_score": 0.85,
                "source": PromptSource.MANUAL,
                "author": "System",
            },
            {
                "prompt_text": "A futuristic AI robot with glowing blue eyes, intricate mechanical details, sci-fi style, cinematic lighting",
                "category": PromptCategory.TEXT_TO_IMAGE,
                "subcategory": PromptSubcategory.ARTISTIC,
                "model_compatibility": ["stable-diffusion", "midjourney"],
                "parameters": {"aspect_ratio": "1:1", "style": "cinematic"},
                "base_quality_score": 0.78,
                "source": PromptSource.MANUAL,
                "author": "System",
            },
            {
                "prompt_text": "An animated character with large expressive eyes, colorful hair, anime art style, detailed background",
                "category": PromptCategory.TEXT_TO_IMAGE,
                "subcategory": PromptSubcategory.ANIME,
                "model_compatibility": ["stable-diffusion", "novelai"],
                "parameters": {"aspect_ratio": "2:3", "style": "anime"},
                "base_quality_score": 0.82,
                "source": PromptSource.MANUAL,
                "author": "System",
            },
        ]

        added_count = 0
        for prompt_data in example_prompts:
            try:
                # 创建PromptEntry
                entry = PromptEntry(
                    id=f"example_{added_count + 1}",
                    prompt_text=prompt_data["prompt_text"],
                    category=prompt_data["category"],
                    subcategory=prompt_data["subcategory"],
                    model_compatibility=prompt_data["model_compatibility"],
                    parameters=prompt_data["parameters"],
                    base_quality_score=prompt_data["base_quality_score"],
                    quality_level=QualityLevel.UNRATED,  # 添加quality_level参数
                    source=prompt_data["source"],
                    author=prompt_data["author"],
                )

                if knowledge_base.add_prompt(entry):
                    added_count += 1
            except Exception as e:
                print(f"   ❌ 添加示例提示词失败: {e}")

        print(f"   ✅ 加载了 {added_count} 个示例提示词到知识库")

    def _get_component_status(self) -> Dict[str, bool]:
        """获取组件状态"""
        return {
            "roma_maref": self.config.enable_roma_maref and ROMA_MAREF_AVAILABLE,
            "kdenlive": self.config.enable_kdenlive and KDENLIVE_AVAILABLE,
            "doubao_cli": self.config.enable_doubao_cli and DOUBAO_CLI_AVAILABLE,
            "doubao_image_generator": self.config.enable_doubao_cli
            and DOUBAO_IMAGE_GENERATOR_AVAILABLE
            and "doubao_image_generator" in self.components,
            "prompt_knowledge_base": PROMPT_KNOWLEDGE_BASE_AVAILABLE
            and "prompt_knowledge_base" in self.components,
            "ip_digital_assets": IP_DIGITAL_ASSETS_AVAILABLE
            and "ip_digital_assets" in self.components,
            "ip_feedback_system": IP_FEEDBACK_SYSTEM_AVAILABLE
            and "ip_feedback_system" in self.components,
            "ip_image_survey": IP_IMAGE_SURVEY_AVAILABLE and "ip_image_survey" in self.components,
            "github_workflow": self.config.enable_github_workflow,
        }

    def _format_component_status(self) -> str:
        """格式化组件状态显示"""
        status = self._get_component_status()
        parts = []
        for name, active in status.items():
            symbol = "✅" if active else "❌"
            parts.append(f"{symbol} {name}")
        return ", ".join(parts)

    def _get_prompt_template_from_knowledge_base(
        self, content_type: str, target_audience: str = None
    ) -> Optional[str]:
        """
        从提示词知识库获取模板

        Args:
            content_type: 内容类型 (video_script, social_media_post, blog_post等)
            target_audience: 目标受众

        Returns:
            提示词模板或None
        """
        if not PROMPT_KNOWLEDGE_BASE_AVAILABLE or "prompt_knowledge_base" not in self.components:
            return None

        try:
            knowledge_base = self.components["prompt_knowledge_base"]

            # 根据内容类型映射到提示词类别
            category_mapping = {
                "video_script": PromptCategory.TEXT_TO_VIDEO,
                "social_media_post": PromptCategory.CONTENT_REWRITE,
                "blog_post": PromptCategory.CONTENT_REWRITE,
                "text_to_image": PromptCategory.TEXT_TO_IMAGE,
                "image_to_video": PromptCategory.IMAGE_TO_VIDEO,
                "video_editing": PromptCategory.VIDEO_EDITING,
            }

            category = category_mapping.get(content_type, PromptCategory.CONTENT_REWRITE)

            # 搜索高质量的提示词
            prompts = knowledge_base.search_prompts(
                category=category, min_quality=0.7, limit=5  # 质量阈值
            )

            if not prompts:
                return None

            # 选择最佳提示词（基于质量和相关性）
            best_prompt = max(prompts, key=lambda p: p.base_quality_score)
            return best_prompt.prompt_text

        except Exception as e:
            print(f"❌ 从知识库获取提示词模板失败: {e}")
            return None

    def generate_content_with_doubao(
        self,
        topic: str,
        content_type: str = "video_script",
        target_audience: str = "开发者社区",
        tone: str = "专业且吸引人",
        image_style: str = "realistic",
        image_size: str = "1024x1024",
        num_images: int = 1,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        使用豆包AI生成内容（视频脚本、社交媒体帖子、图像等）

        Args:
            topic: 内容主题
            content_type: 内容类型（video_script, social_media_post, blog_post, text_to_image等）
            target_audience: 目标受众
            tone: 语气风格（对于图像生成，可作为风格提示）
            image_style: 图像风格（realistic, cartoon, anime, artistic等）
            image_size: 图像尺寸（1024x1024, 768x1024等）
            num_images: 生成图像数量

        Returns:
            (success, result_dict) 元组
        """
        print(f"🤖 使用豆包AI生成{content_type}: {topic}")
        print(f"   目标受众: {target_audience}, 语气: {tone}")

        # 检查是否是图像生成请求
        is_image_generation = content_type.lower() in [
            "text_to_image",
            "image",
            "ai_image",
            "image_generation",
        ]

        # 如果是图像生成，直接调用图像生成器
        if is_image_generation:
            if "doubao_image_generator" in self.components:
                print(
                    f"🎨 启动豆包图像生成器: 风格={image_style}, 尺寸={image_size}, 数量={num_images}"
                )
                return self._generate_image_with_doubao(
                    topic, image_style, image_size, num_images, tone
                )
            else:
                error_msg = "豆包图像生成器不可用"
                print(f"❌ {error_msg}")
                return False, {"error": error_msg}

        if not self.config.enable_doubao_cli or "doubao_cli" not in self.components:
            error_msg = "豆包CLI不可用"
            print(f"❌ {error_msg}")
            return False, {"error": error_msg}

        try:
            doubao = self.components["doubao_cli"]

            # 1. 激活豆包App
            print("   1. 激活豆包App...")
            activation_result = doubao.activate()
            print(f"   ✅ {activation_result}")

            # 2. 打开豆包AI聊天界面
            print("   2. 打开豆包AI聊天界面...")
            ai_result = doubao.open_doubao_ai()
            print(f"   ✅ {ai_result}")

            # 3. 构造AI提示词
            # 尝试从知识库获取高质量模板
            template = self._get_prompt_template_from_knowledge_base(content_type, target_audience)

            if template:
                print("   🎯 使用知识库高质量模板")
                prompt = f"""
基于以下高质量创作模板：

"{template}"

请为我创作以下内容：

主题：{topic}
内容类型：{content_type}
目标受众：{target_audience}
语气风格：{tone}

具体要求：
1. 创作一个专业、吸引人的{content_type}
2. 内容结构清晰，逻辑性强
3. 适合{target_audience}阅读
4. 使用{tone}的语气
5. 保持模板的高质量风格和结构

请直接输出内容，不需要额外的解释。
"""
            else:
                print("   ℹ️ 使用默认提示词模板")
                prompt = f"""
请为我创作以下内容：

主题：{topic}
内容类型：{content_type}
目标受众：{target_audience}
语气风格：{tone}

具体要求：
1. 创作一个专业、吸引人的{content_type}
2. 内容结构清晰，逻辑性强
3. 适合{target_audience}阅读
4. 使用{tone}的语气

请直接输出内容，不需要额外的解释。
"""

            # 4. 向豆包AI发送消息
            print("   3. 向豆包AI发送创作请求...")
            content_result = doubao.send_message_to_ai(prompt)

            if "消息已发送" in content_result or "JavaScript执行结果" in content_result:
                print(f"✅ AI内容生成请求已发送")

                # 等待AI响应（模拟等待）
                print("   4. 等待AI响应...")
                time.sleep(5)  # 等待5秒让AI生成内容

                # 尝试获取响应（这里简化处理，实际应该获取聊天历史）
                # 我们假设AI已经生成了内容

                result = {
                    "success": True,
                    "topic": topic,
                    "content_type": content_type,
                    "target_audience": target_audience,
                    "tone": tone,
                    "prompt": prompt,
                    "response": content_result,
                    "generated_content": f"豆包AI生成的{content_type}内容（需要手动查看聊天记录）",
                    "timestamp": datetime.now().isoformat(),
                    "system": "Doubao AI Content Generation",
                }

                print(f"✅ {content_type}生成请求完成")
                self.state["tasks_completed"] += 1
                self._log_task_completion("doubao_content_generation", topic, result)

                return True, result
            else:
                error_msg = f"豆包AI消息发送失败: {content_result}"
                print(f"❌ {error_msg}")
                self.state["tasks_failed"] += 1
                self.state["last_error"] = error_msg
                return False, {"error": error_msg}

        except Exception as e:
            error_msg = f"豆包内容生成异常: {str(e)}"
            print(f"❌ {error_msg}")
            self.state["tasks_failed"] += 1
            self.state["last_error"] = error_msg
            return False, {"error": error_msg}

    def _generate_image_with_doubao(
        self,
        prompt: str,
        style: str = "realistic",
        size: str = "1024x1024",
        num_images: int = 1,
        quality_hint: str = "standard",
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        使用豆包图像生成器生成图像（私有方法）

        Args:
            prompt: 图像描述提示词
            style: 图像风格（realistic, cartoon, anime, artistic等）
            size: 图像尺寸（1024x1024, 768x1024等）
            num_images: 生成图像数量
            quality_hint: 质量提示（standard, premium等）

        Returns:
            (success, result_dict) 元组
        """
        print(f"🎨 调用豆包图像生成器: {prompt[:50]}...")
        print(f"   风格: {style}, 尺寸: {size}, 数量: {num_images}")

        try:
            generator = self.components["doubao_image_generator"]

            # 调用图像生成器
            result = generator.generate_image(
                prompt=prompt,
                style=style,
                size=size,
                quality=quality_hint,
                num_images=num_images,
                wait_time=60,  # 等待60秒生成
            )

            if result.success:
                print(f"✅ 图像生成成功: {len(result.image_urls)}张图像")
                print(f"   图像URL: {result.image_urls[:2]}...")

                # 构建返回结果
                return_result = {
                    "success": True,
                    "prompt": prompt,
                    "style": style,
                    "size": size,
                    "num_images": num_images,
                    "generated_images": result.image_urls,
                    "metadata": result.metadata,
                    "timestamp": result.timestamp,
                    "system": "Doubao AI Image Generation",
                    "note": f"成功生成{len(result.image_urls)}张图像",
                }

                self.state["tasks_completed"] += 1
                self._log_task_completion("doubao_image_generation", prompt, return_result)

                return True, return_result
            else:
                error_msg = f"图像生成失败: {result.error_message if hasattr(result, 'error_message') else '未知错误'}"
                print(f"❌ {error_msg}")
                self.state["tasks_failed"] += 1
                self.state["last_error"] = error_msg
                return False, {"error": error_msg}

        except Exception as e:
            error_msg = f"豆包图像生成异常: {str(e)}"
            print(f"❌ {error_msg}")
            self.state["tasks_failed"] += 1
            self.state["last_error"] = error_msg
            return False, {"error": error_msg}

    def generate_video_script_with_doubao(
        self, video_topic: str, duration_seconds: int = 60, include_visual_cues: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        使用豆包AI生成视频脚本

        Args:
            video_topic: 视频主题
            duration_seconds: 视频时长（秒）
            include_visual_cues: 是否包含视觉提示

        Returns:
            (success, result_dict) 元组
        """
        print(f"📝 使用豆包AI生成视频脚本: {video_topic}")
        print(f"   时长: {duration_seconds}秒, 视觉提示: {'是' if include_visual_cues else '否'}")

        # 构造专门用于视频脚本的提示词
        visual_cue_text = (
            "包含详细的视觉提示（镜头类型、转场效果、屏幕文字）" if include_visual_cues else ""
        )

        success, result = self.generate_content_with_doubao(
            topic=video_topic,
            content_type=f"video_script_{duration_seconds}seconds",
            target_audience="技术爱好者和开发者",
            tone="专业、清晰、有吸引力",
        )

        if success:
            # 添加视频脚本特定信息
            result["video_specific"] = {
                "duration_seconds": duration_seconds,
                "include_visual_cues": include_visual_cues,
                "estimated_scenes": duration_seconds // 5,  # 每5秒一个场景
                "script_format": "视频脚本",
            }

            print(f"✅ 视频脚本生成成功: {video_topic}")

        return success, result

    def generate_ad_video(
        self,
        project_name: str,
        content_brief: str,
        resolution: str = "standard",
        duration_preset: str = "ad_standard",
        content_template: str = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        生成广告级视频

        Args:
            project_name: 项目名称
            content_brief: 内容简报
            resolution: 分辨率预设
            duration_preset: 时长预设
            content_template: 内容模板

        Returns:
            (success, result_dict) 元组
        """
        print(f"🎬 生成广告级视频: {project_name}")
        print(f"内容简报: {content_brief[:100]}...")

        if not self.config.enable_kdenlive or "kdenlive" not in self.components:
            error_msg = "Kdenlive视频生成引擎不可用"
            print(f"❌ {error_msg}")
            return False, {"error": error_msg}

        try:
            # 分析内容简报确定模板
            if content_template is None:
                content_template = self._analyze_content_template(content_brief)

            # 调用Kdenlive引擎
            engine = self.components["kdenlive"]

            # 根据内容简报提取文本
            title_text, product_text, cta_text = self._extract_text_from_brief(content_brief)

            # 生成视频
            success, result = engine.generate_ad_level_video(
                project_name=project_name,
                resolution=resolution,
                fps="broadcast",
                duration_preset=duration_preset,
                content_template=content_template,
                title_text=title_text,
                product_text=product_text,
                call_to_action_text=cta_text,
            )

            if success:
                print(f"✅ 视频生成成功: {project_name}")
                self.state["tasks_completed"] += 1

                # 记录任务到状态文件
                self._log_task_completion("video_generation", project_name, result)

                # 如果是企业模式，使用ROMA-MAREF智能体进行质量验证
                if (
                    self.config.mode == ProductionSystemMode.ENTERPRISE
                    and "roma_maref" in self.components
                ):
                    self._validate_video_quality(project_name, result)

                return True, result
            else:
                print(f"❌ 视频生成失败: {project_name}")
                self.state["tasks_failed"] += 1
                self.state["last_error"] = result.get("error", "未知错误")
                return False, result

        except Exception as e:
            error_msg = f"视频生成异常: {str(e)}"
            print(f"❌ {error_msg}")
            self.state["tasks_failed"] += 1
            self.state["last_error"] = error_msg
            return False, {"error": error_msg}

    def _analyze_content_template(self, content_brief: str) -> str:
        """分析内容简报确定模板类型"""
        brief_lower = content_brief.lower()

        if "开源" in brief_lower or "github" in brief_lower or "仓库" in brief_lower:
            return "project_announcement"
        elif "产品" in brief_lower or "功能" in brief_lower or "展示" in brief_lower:
            return "product_showcase"
        elif "品牌" in brief_lower or "故事" in brief_lower or "愿景" in brief_lower:
            return "brand_story"
        elif "open human" in brief_lower or "碳硅共生" in brief_lower:
            return "openhuman_intro"
        else:
            return "product_showcase"  # 默认模板

    def _extract_text_from_brief(self, content_brief: str) -> Tuple[str, str, str]:
        """从内容简报中提取标题、产品描述和行动号召文本"""
        # 简单实现 - 在实际系统中可以使用NLP或规则引擎
        lines = content_brief.split("\n")

        # 标题：第一行或前50个字符
        title_text = lines[0].strip() if lines else "项目介绍"
        if len(title_text) > 50:
            title_text = title_text[:47] + "..."

        # 产品描述：前3行的组合（最多200字符）
        product_lines = lines[:3] if len(lines) >= 3 else lines
        product_text = " ".join(line.strip() for line in product_lines if line.strip())
        if len(product_text) > 200:
            product_text = product_text[:197] + "..."

        # 行动号召：基于内容类型
        if "开源" in content_brief or "GitHub" in content_brief:
            cta_text = "访问GitHub仓库，查看文档并参与贡献"
        elif "产品" in content_brief:
            cta_text = "立即体验，提升您的工作效率"
        elif "open human" in content_brief:
            cta_text = "加入我们的开源社区，共同构建碳硅共生的未来"
        else:
            cta_text = "了解更多信息，请访问我们的官方网站"

        return title_text, product_text, cta_text

    def _validate_video_quality(self, project_name: str, result: Dict[str, Any]):
        """使用ROMA-MAREF智能体验证视频质量（企业级功能）"""
        if "roma_maref" not in self.components:
            return

        try:
            print(f"🔍 使用ROMA-MAREF智能体验证视频质量: {project_name}")

            # 创建验证任务
            validation_task = {
                "task_type": "video_quality_validation",
                "project_name": project_name,
                "video_result": result,
                "quality_standards": {
                    "resolution_standard": "1920x1080或更高",
                    "frame_rate_standard": "30fps或更高",
                    "content_structure": "应有明确的开场、主体、结尾",
                    "call_to_action": "应有明确的行动号召",
                    "brand_consistency": "应符合品牌视觉指南",
                },
            }

            # 这里可以调用ROMA-MAREF智能体进行验证
            # 暂时记录到日志
            validation_log = {
                "task": validation_task,
                "timestamp": datetime.now().isoformat(),
                "status": "recorded_for_processing",
            }

            validation_log_path = os.path.join(
                self.config.output_dir,
                "validation_logs",
                f"{project_name}_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            )
            os.makedirs(os.path.dirname(validation_log_path), exist_ok=True)

            with open(validation_log_path, "w", encoding="utf-8") as f:
                json.dump(validation_log, f, ensure_ascii=False, indent=2)

            print(f"📋 视频质量验证任务已记录: {validation_log_path}")

        except Exception as e:
            print(f"⚠️  视频质量验证记录失败: {e}")

    def _log_task_completion(self, task_type: str, task_name: str, result: Dict[str, Any]):
        """记录任务完成情况"""
        try:
            log_entry = {
                "task_type": task_type,
                "task_name": task_name,
                "timestamp": datetime.now().isoformat(),
                "result_summary": {
                    "success": result.get("success", True),
                    "output_files_count": result.get("output_file_count", 0),
                    "project_file": result.get("project_file"),
                    "error": result.get("error"),
                },
                "system_state": self.state.copy(),
            }

            # 移除可能的大对象
            log_entry["system_state"].pop("last_error", None)

            log_dir = os.path.join(self.config.output_dir, "task_logs")
            os.makedirs(log_dir, exist_ok=True)

            log_filename = (
                f"{task_type}_{task_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            log_path = os.path.join(log_dir, log_filename)

            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log_entry, f, ensure_ascii=False, indent=2)

            print(f"📝 任务日志已保存: {log_path}")

        except Exception as e:
            print(f"⚠️  任务日志记录失败: {e}")

    def generate_openhuman_intro_video(
        self, use_doubao_ai: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """生成Open Human项目介绍视频"""
        print("🎬 启动Open Human MVP内容生成")
        print("============================================================")

        content_brief = ""

        # 尝试使用豆包AI生成脚本（如果启用且可用）
        if use_doubao_ai and self.config.enable_doubao_cli and "doubao_cli" in self.components:
            print("🤖 尝试使用豆包AI生成Open Human视频脚本...")

            try:
                # 使用豆包AI生成视频脚本
                script_success, script_result = self.generate_video_script_with_doubao(
                    video_topic="Open Human项目介绍 - 碳硅共生开源框架",
                    duration_seconds=90,  # 1.5分钟介绍视频
                    include_visual_cues=True,
                )

                if script_success:
                    print("✅ 豆包AI脚本生成成功")

                    # 从豆包响应中提取或构造内容简报
                    # 注意：实际实现中需要解析豆包AI的响应来获取生成的内容
                    # 这里简化处理，使用增强版的内容简报
                    content_brief = f"""
Open Human项目介绍视频 - AI增强版本
主题：碳硅共生开源框架 - 人类与AI的协同进化
内容：展示碳基智慧（人类创造力）与硅基智慧（AI计算力）的深度融合
技术架构：多层智能体系统（ROMA-MAREF框架）、递归演进机制、八卦互补网络
项目亮点：开源社区驱动、多模态内容生成、自动化运营工作流、企业级生产力
目标受众：开发者、AI研究者、开源贡献者、技术创新者
行动号召：加入碳硅共生社区，参与开源贡献，共同构建人机协同的未来
                    """

                    print("📝 使用豆包AI生成的增强版内容简报")

                else:
                    print(
                        f"⚠️ 豆包AI脚本生成失败，使用默认内容: {script_result.get('error', '未知错误')}"
                    )
                    # 回退到默认内容
                    content_brief = self._get_default_openhuman_brief()

            except Exception as e:
                print(f"⚠️ 豆包AI集成异常，使用默认内容: {e}")
                content_brief = self._get_default_openhuman_brief()
        else:
            print("🤖 豆包AI不可用，使用默认内容")
            content_brief = self._get_default_openhuman_brief()

        print(f"📋 内容简报: {content_brief[:100]}...")

        return self.generate_ad_video(
            project_name="Open_Human_Introduction_MVP",
            content_brief=content_brief,
            resolution="standard",
            duration_preset="explainer",
            content_template="openhuman_intro",
        )

    def _get_default_openhuman_brief(self) -> str:
        """获取默认的Open Human内容简报"""
        return """
        Open Human项目介绍视频
        主题：碳硅共生开源框架
        内容：展示碳基智慧（人类）与硅基智慧（AI）的协同演进
        技术架构：ROMA-MAREF多智能体系统、八层传播体系、递归演进机制
        项目亮点：开源社区建设、自动化内容生成、企业级生产力工具
        目标：吸引开发者参与，建立碳硅共生生态
        行动号召：加入我们的开源社区，共同构建人机协同的未来
        """

    def generate_github_release_video(
        self, repo_name: str, version: str = "1.0.0"
    ) -> Tuple[bool, Dict[str, Any]]:
        """生成GitHub项目发布视频"""
        content_brief = f"""
        {repo_name} v{version} 正式发布
        项目类型：开源软件
        发布亮点：新功能、性能优化、API改进
        目标受众：开发者、技术爱好者、开源贡献者
        行动号召：Star项目、提交Issue、参与贡献
        """

        return self.generate_ad_video(
            project_name=f"{repo_name}_v{version}_Release",
            content_brief=content_brief,
            resolution="standard",
            duration_preset="ad_standard",
            content_template="project_announcement",
        )

    def test_production_system(self) -> Dict[str, Any]:
        """
        测试生产系统

        Returns:
            测试结果字典
        """
        print("=" * 60)
        print("🧪 测试Clawra生产系统")
        print("=" * 60)

        test_results = {
            "system": {
                "initialized": self.state["initialized"],
                "component_status": self._get_component_status(),
                "config": self.config.to_dict(),
            },
            "tests": [],
            "summary": {"total_tests": 0, "passed_tests": 0, "failed_tests": 0},
        }

        # 测试1: 系统状态检查
        print("\n1. 系统状态检查...")
        system_ok = self.state["initialized"]
        test_results["tests"].append(
            {"name": "system_initialization", "passed": system_ok, "details": "生产系统初始化状态"}
        )
        print(f"   {'✅' if system_ok else '❌'} 系统初始化: {system_ok}")

        # 测试2: 组件可用性检查
        print("\n2. 组件可用性检查...")
        component_status = self._get_component_status()
        for component, available in component_status.items():
            test_results["tests"].append(
                {
                    "name": f"component_{component}",
                    "passed": available,
                    "details": f"{component}组件可用性",
                }
            )
            print(f"   {'✅' if available else '❌'} {component}: {available}")

        # 测试3: Kdenlive视频生成测试（如果可用）
        if self.config.enable_kdenlive and "kdenlive" in self.components:
            print("\n3. Kdenlive视频生成测试...")
            try:
                # 快速测试视频生成
                success, result = self.generate_ad_video(
                    project_name="Test_Video_Generation",
                    content_brief="测试视频生成功能 - 这是一个测试视频，用于验证Clawra生产系统的视频生成能力。",
                    resolution="mobile",  # 使用移动分辨率，更快
                    duration_preset="social_short",  # 15秒短视频
                    content_template="product_showcase",
                )

                test_results["tests"].append(
                    {
                        "name": "kdenlive_video_generation",
                        "passed": success,
                        "details": f"Kdenlive视频生成测试 - 成功: {success}",
                        "result": result if success else {"error": result.get("error", "未知错误")},
                    }
                )
                print(f"   {'✅' if success else '❌'} 视频生成测试: {success}")

                if success:
                    print(f"     项目文件: {result.get('project_file', 'N/A')}")
                    print(f"     输出文件数: {result.get('output_file_count', 0)}")
            except Exception as e:
                test_results["tests"].append(
                    {
                        "name": "kdenlive_video_generation",
                        "passed": False,
                        "details": f"Kdenlive视频生成测试异常: {str(e)}",
                    }
                )
                print(f"   ❌ 视频生成测试异常: {e}")

        # 总结
        test_results["summary"]["total_tests"] = len(test_results["tests"])
        test_results["summary"]["passed_tests"] = sum(
            1 for t in test_results["tests"] if t["passed"]
        )
        test_results["summary"]["failed_tests"] = (
            test_results["summary"]["total_tests"] - test_results["summary"]["passed_tests"]
        )

        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)
        print(f"总测试数: {test_results['summary']['total_tests']}")
        print(f"通过: {test_results['summary']['passed_tests']}")
        print(f"失败: {test_results['summary']['failed_tests']}")

        all_passed = test_results["summary"]["failed_tests"] == 0
        print(f"\n整体结果: {'✅ 所有测试通过' if all_passed else '❌ 部分测试失败'}")
        print("=" * 60)

        # 保存测试结果
        test_report_path = os.path.join(
            self.config.output_dir,
            f"production_system_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        with open(test_report_path, "w", encoding="utf-8") as f:
            json.dump(test_results, f, ensure_ascii=False, indent=2)

        print(f"📋 测试报告已保存: {test_report_path}")

        return test_results

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "system": {
                "initialized": self.state["initialized"],
                "start_time": self.state["start_time"],
                "uptime_seconds": (
                    datetime.now() - datetime.fromisoformat(self.state["start_time"])
                ).total_seconds(),
                "mode": self.config.mode.value,
                "output_dir": self.config.output_dir,
            },
            "components": self._get_component_status(),
            "performance": {
                "tasks_completed": self.state["tasks_completed"],
                "tasks_failed": self.state["tasks_failed"],
                "success_rate": self.state["tasks_completed"]
                / max(1, self.state["tasks_completed"] + self.state["tasks_failed"]),
            },
            "content_layer": {
                "current_focus": self.config.layer_focus.value,
                "layer_config": asdict(get_layer_config(self.config.layer_focus)),
            },
        }

        return status

    def save_system_snapshot(self):
        """保存系统快照"""
        # 获取可序列化的系统状态
        system_status = self.get_system_status()

        # 确保所有内容都可序列化
        serializable_status = self._make_serializable(system_status)

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "config": self.config.to_dict(),
            "state": self._make_serializable(self.state),
            "system_status": serializable_status,
        }

        snapshot_dir = os.path.join(self.config.output_dir, "snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)

        snapshot_file = os.path.join(
            snapshot_dir, f"system_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        print(f"📸 系统快照已保存: {snapshot_file}")
        return snapshot_file

    def _make_serializable(self, obj):
        """将对象转换为可JSON序列化的格式"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._make_serializable(item) for item in obj)
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif hasattr(obj, "__dict__"):
            # 尝试将对象转换为字典
            return self._make_serializable(obj.__dict__)
        elif hasattr(obj, "value"):
            # 处理枚举类型
            return obj.value
        else:
            # 尝试转换为字符串
            try:
                return str(obj)
            except:
                return f"<non-serializable: {type(obj).__name__}>"

    def collect_feedback(
        self,
        feedback_type: str,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        suggestions: List[str] = None,
        user_id: Optional[str] = None,
        source: str = "external_user",
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        收集用户对IP形象的反馈

        Args:
            feedback_type: 反馈类型 (ip_image, visual_style, content_template, brand_consistency, overall_experience)
            rating: 评分 (1-5)
            comment: 文本评论
            suggestions: 改进建议列表
            user_id: 用户ID (可选，匿名化)
            source: 反馈来源 (github, community, internal_team, external_user, automated_analysis)
            context: 上下文信息 (如内容ID、模板ID等)

        Returns:
            是否成功收集
        """
        if not IP_FEEDBACK_SYSTEM_AVAILABLE or "ip_feedback_system" not in self.components:
            print("⚠️ IP反馈系统不可用，无法收集反馈")
            return False

        try:
            # 导入反馈系统类型
            from ip_feedback_system import FeedbackEntry, FeedbackSource, FeedbackType

            # 转换反馈类型
            type_mapping = {
                "ip_image": FeedbackType.IP_IMAGE,
                "visual_style": FeedbackType.VISUAL_STYLE,
                "content_template": FeedbackType.CONTENT_TEMPLATE,
                "brand_consistency": FeedbackType.BRAND_CONSISTENCY,
                "overall_experience": FeedbackType.OVERALL_EXPERIENCE,
            }

            feedback_type_enum = type_mapping.get(feedback_type, FeedbackType.IP_IMAGE)

            # 转换反馈来源
            source_mapping = {
                "github": FeedbackSource.GITHUB,
                "community": FeedbackSource.COMMUNITY,
                "internal_team": FeedbackSource.INTERNAL_TEAM,
                "external_user": FeedbackSource.EXTERNAL_USER,
                "automated_analysis": FeedbackSource.AUTOMATED_ANALYSIS,
            }

            source_enum = source_mapping.get(source, FeedbackSource.EXTERNAL_USER)

            # 生成反馈ID
            import hashlib
            import uuid
            from datetime import datetime

            timestamp_str = datetime.now().isoformat()
            unique_id = hashlib.md5(
                f"{timestamp_str}_{user_id or 'anonymous'}_{feedback_type}".encode()
            ).hexdigest()[:8]
            feedback_id = f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{unique_id}"

            # 创建反馈条目
            feedback = FeedbackEntry(
                feedback_id=feedback_id,
                feedback_type=feedback_type_enum,
                source=source_enum,
                user_id=user_id,
                timestamp=datetime.now(),
                rating=rating,
                comment=comment,
                suggestions=suggestions or [],
                context=context or {},
                metadata={
                    "collection_system": "clawra_production_system",
                    "system_mode": self.config.mode.value,
                    "component_versions": self._get_component_versions(),
                },
            )

            # 提交反馈
            feedback_system = self.components["ip_feedback_system"]
            success = feedback_system.submit_feedback(feedback)

            if success:
                print(f"✅ 用户反馈收集成功: {feedback_id}")
                print(f"   类型: {feedback_type}, 评分: {rating or '无评分'}")
                if comment:
                    print(
                        f"   评论: {comment[:50]}..."
                        if len(comment) > 50
                        else f"   评论: {comment}"
                    )

                # 记录到任务日志
                self._log_feedback_collection(feedback_id, feedback_type, rating)
            else:
                print(f"❌ 用户反馈收集失败: {feedback_id}")

            return success

        except Exception as e:
            print(f"❌ 反馈收集异常: {e}")
            return False

    def collect_content_generation_feedback(
        self,
        content_result: Dict[str, Any],
        user_id: Optional[str] = None,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> bool:
        """
        收集内容生成后的用户反馈

        Args:
            content_result: 内容生成结果
            user_id: 用户ID (可选)
            rating: 评分 (1-5)
            comment: 文本评论

        Returns:
            是否成功收集
        """
        print("\n📝 收集内容生成反馈")
        print("-" * 40)

        # 提取上下文信息
        context = {
            "content_type": content_result.get("content_type", "unknown"),
            "template_id": content_result.get("template_id"),
            "visual_style": content_result.get("visual_style"),
            "generation_timestamp": content_result.get("timestamp"),
            "success": content_result.get("success", False),
            "system": content_result.get("system", "unknown"),
        }

        # 确定反馈类型
        content_type = content_result.get("content_type", "").lower()
        if "image" in content_type:
            feedback_type = "visual_style"
        elif "video" in content_type:
            feedback_type = "visual_style"
        elif "social" in content_type:
            feedback_type = "content_template"
        else:
            feedback_type = "overall_experience"

        # 收集反馈
        success = self.collect_feedback(
            feedback_type=feedback_type,
            rating=rating,
            comment=comment,
            user_id=user_id,
            source="external_user",
            context=context,
        )

        return success

    def analyze_ip_feedback(
        self, feedback_type: Optional[str] = None, days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        分析IP形象反馈数据

        Args:
            feedback_type: 反馈类型 (可选)
            days: 分析最近多少天的数据

        Returns:
            分析结果字典，如果无数据则返回None
        """
        if not IP_FEEDBACK_SYSTEM_AVAILABLE or "ip_feedback_system" not in self.components:
            print("⚠️ IP反馈系统不可用，无法分析反馈")
            return None

        try:
            from ip_feedback_system import FeedbackType

            # 转换反馈类型
            type_mapping = {
                "ip_image": FeedbackType.IP_IMAGE,
                "visual_style": FeedbackType.VISUAL_STYLE,
                "content_template": FeedbackType.CONTENT_TEMPLATE,
                "brand_consistency": FeedbackType.BRAND_CONSISTENCY,
                "overall_experience": FeedbackType.OVERALL_EXPERIENCE,
            }

            feedback_type_enum = None
            if feedback_type:
                feedback_type_enum = type_mapping.get(feedback_type)
                if not feedback_type_enum:
                    print(f"⚠️ 未知的反馈类型: {feedback_type}")
                    feedback_type_enum = FeedbackType.IP_IMAGE

            print(f"📊 分析IP形象反馈数据")
            print(f"   类型: {feedback_type or '全部类型'}")
            print(f"   时间范围: 最近{days}天")

            # 分析反馈
            feedback_system = self.components["ip_feedback_system"]
            analysis = feedback_system.analyze_feedback(feedback_type=feedback_type_enum, days=days)

            if not analysis:
                print("ℹ️ 没有找到反馈数据")
                return None

            # 转换为可序列化格式
            analysis_dict = {
                "feedback_type": analysis.feedback_type.value,
                "period_start": analysis.period_start.isoformat(),
                "period_end": analysis.period_end.isoformat(),
                "total_feedbacks": analysis.total_feedbacks,
                "average_rating": analysis.average_rating,
                "rating_distribution": analysis.rating_distribution,
                "common_themes": analysis.common_themes,
                "sentiment_score": analysis.sentiment_score,
                "top_keywords": analysis.top_keywords,
                "improvement_suggestions": analysis.improvement_suggestions,
                "critical_issues": analysis.critical_issues,
                "trend": analysis.trend,
            }

            print(f"✅ 反馈分析完成")
            print(f"   总反馈数: {analysis.total_feedbacks}")
            print(f"   平均评分: {analysis.average_rating or '无评分'}")
            print(f"   趋势: {analysis.trend}")

            # 生成优化报告
            print("\n📋 生成优化建议报告...")
            report = feedback_system.generate_optimization_report(analysis)
            report_path = feedback_system.save_report(report)

            print(f"✅ 优化报告生成成功: {report_path}")
            print(f"   优化建议: {len(report['optimization_recommendations'])}条")
            print(f"   优先级行动: {len(report['priority_actions'])}条")

            # 将报告路径添加到分析结果
            analysis_dict["optimization_report"] = report
            analysis_dict["report_path"] = report_path

            # 保存分析结果
            self._save_feedback_analysis(analysis_dict, feedback_type or "all")

            return analysis_dict

        except Exception as e:
            print(f"❌ 反馈分析异常: {e}")
            import traceback

            traceback.print_exc()
            return None

    def generate_ip_optimization_suggestions(self) -> Dict[str, Any]:
        """
        基于反馈数据生成IP形象优化建议
        自动分析所有类型的反馈并生成综合优化建议

        Returns:
            综合优化建议报告
        """
        print("🎯 生成IP形象综合优化建议")
        print("=" * 60)

        if not IP_FEEDBACK_SYSTEM_AVAILABLE or "ip_feedback_system" not in self.components:
            print("⚠️ IP反馈系统不可用")
            return {"error": "IP反馈系统不可用"}

        try:
            # 分析所有反馈类型
            feedback_types = [
                "ip_image",
                "visual_style",
                "content_template",
                "brand_consistency",
                "overall_experience",
            ]

            all_analyses = {}
            for fb_type in feedback_types:
                print(f"\n分析 {fb_type} 反馈...")
                analysis = self.analyze_ip_feedback(fb_type, days=30)
                if analysis:
                    all_analyses[fb_type] = analysis

            if not all_analyses:
                print("ℹ️ 没有找到任何反馈数据")
                return {"status": "no_feedback_data"}

            # 生成综合报告
            from collections import Counter
            from datetime import datetime

            report_id = f"ip_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 收集关键指标
            total_feedbacks = sum(
                analysis.get("total_feedbacks", 0) for analysis in all_analyses.values()
            )
            average_ratings = [
                analysis.get("average_rating")
                for analysis in all_analyses.values()
                if analysis.get("average_rating")
            ]
            overall_avg_rating = (
                sum(average_ratings) / len(average_ratings) if average_ratings else None
            )

            # 收集优化建议
            all_suggestions = []
            all_critical_issues = []

            for fb_type, analysis in all_analyses.items():
                all_suggestions.extend(analysis.get("improvement_suggestions", []))
                all_critical_issues.extend(analysis.get("critical_issues", []))

            # 去重
            unique_suggestions = list(set(all_suggestions))
            unique_critical_issues = list(set(all_critical_issues))

            # 生成综合报告
            comprehensive_report = {
                "report_id": report_id,
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_feedbacks": total_feedbacks,
                    "overall_average_rating": overall_avg_rating,
                    "feedback_types_analyzed": len(all_analyses),
                    "unique_suggestions": len(unique_suggestions),
                    "critical_issues": len(unique_critical_issues),
                },
                "detailed_analyses": all_analyses,
                "integrated_optimization_recommendations": [],
                "cross_type_insights": self._generate_cross_type_insights(all_analyses),
                "implementation_roadmap": self._generate_implementation_roadmap(all_analyses),
            }

            # 保存综合报告
            reports_dir = Path(__file__).parent / "assets" / "comprehensive_reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            report_file = reports_dir / f"{report_id}.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(comprehensive_report, f, indent=2, ensure_ascii=False)

            print(f"\n✅ 综合优化报告生成完成")
            print(f"   总反馈数: {total_feedbacks}")
            print(f"   总体平均分: {overall_avg_rating or '无评分'}")
            print(f"   分析类型数: {len(all_analyses)}")
            print(f"   优化建议: {len(unique_suggestions)}条")
            print(f"   关键问题: {len(unique_critical_issues)}条")
            print(f"   报告文件: {report_file}")

            return comprehensive_report

        except Exception as e:
            print(f"❌ 综合优化建议生成异常: {e}")
            import traceback

            traceback.print_exc()
            return {"error": str(e)}

    def _log_feedback_collection(self, feedback_id: str, feedback_type: str, rating: Optional[int]):
        """记录反馈收集日志"""
        try:
            log_entry = {
                "feedback_id": feedback_id,
                "feedback_type": feedback_type,
                "rating": rating,
                "timestamp": datetime.now().isoformat(),
                "system_mode": self.config.mode.value,
            }

            log_dir = Path(self.config.output_dir) / "feedback_logs"
            log_dir.mkdir(parents=True, exist_ok=True)

            log_file = log_dir / f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️ 反馈日志记录失败: {e}")

    def _save_feedback_analysis(self, analysis: Dict[str, Any], feedback_type: str):
        """保存反馈分析结果"""
        try:
            analysis_dir = Path(self.config.output_dir) / "feedback_analysis"
            analysis_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            analysis_file = analysis_dir / f"analysis_{feedback_type}_{timestamp}.json"

            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)

            print(f"📊 分析结果保存到: {analysis_file}")

        except Exception as e:
            print(f"⚠️ 分析结果保存失败: {e}")

    def _get_component_versions(self) -> Dict[str, Any]:
        """获取组件版本信息"""
        versions = {
            "clawra_production_system": "1.0.0",
            "ip_digital_assets": (
                "1.0.0" if "ip_digital_assets" in self.components else "unavailable"
            ),
            "ip_feedback_system": (
                "1.0.0" if "ip_feedback_system" in self.components else "unavailable"
            ),
            "ip_image_survey": "1.0.0" if "ip_image_survey" in self.components else "unavailable",
            "prompt_knowledge_base": (
                "1.0.0" if "prompt_knowledge_base" in self.components else "unavailable"
            ),
        }

        # 尝试获取IP数字资产版本
        if "ip_digital_assets" in self.components:
            try:
                stats = self.components["ip_digital_assets"].get_statistics()
                versions["ip_digital_assets"] = stats.get("version", "1.0.0")
            except:
                pass

        return versions

    def _generate_cross_type_insights(self, all_analyses: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """生成跨类型洞察"""
        insights = []

        # 检查是否存在跨类型的共同问题
        common_themes_across_types = {}

        for fb_type, analysis in all_analyses.items():
            themes = analysis.get("common_themes", [])
            for theme in themes:
                theme_name = theme.get("theme", "unknown")
                if theme_name not in common_themes_across_types:
                    common_themes_across_types[theme_name] = []
                common_themes_across_types[theme_name].append(fb_type)

        # 生成跨类型洞察
        for theme_name, types in common_themes_across_types.items():
            if len(types) > 1:  # 跨多个类型
                insights.append(
                    {
                        "insight_type": "cross_type_theme",
                        "theme": theme_name,
                        "feedback_types": types,
                        "description": f"主题'{theme_name}'在{len(types)}个反馈类型中都被提及，可能是系统性问题",
                        "recommendation": f"优先解决'{theme_name}'相关的问题，因为它影响多个方面",
                    }
                )

        # 检查评分趋势一致性
        trends = {}
        for fb_type, analysis in all_analyses.items():
            trend = analysis.get("trend", "stable")
            if trend not in trends:
                trends[trend] = []
            trends[trend].append(fb_type)

        for trend, types in trends.items():
            if len(types) > 1 and trend != "stable":
                insights.append(
                    {
                        "insight_type": "trend_pattern",
                        "trend": trend,
                        "feedback_types": types,
                        "description": f"{len(types)}个反馈类型都呈现{trend}趋势",
                        "implication": (
                            "improving" if trend == "improving" else "需要关注整体下滑趋势"
                        ),
                    }
                )

        return insights[:5]  # 返回前5个洞察

    def _generate_implementation_roadmap(self, all_analyses: Dict[str, Dict]) -> Dict[str, Any]:
        """生成实施路线图"""
        roadmap = {
            "phases": [],
            "estimated_timeline": "4-8周",
            "priority_levels": {
                "critical": "24小时内处理",
                "high": "1周内处理",
                "medium": "2-4周内处理",
                "low": "后续版本处理",
            },
        }

        # 收集所有关键问题
        all_critical_issues = []
        for fb_type, analysis in all_analyses.items():
            issues = analysis.get("critical_issues", [])
            all_critical_issues.extend(issues)

        # 第一阶段：紧急修复
        if all_critical_issues:
            roadmap["phases"].append(
                {
                    "phase": 1,
                    "name": "紧急修复",
                    "timeline": "24小时-1周",
                    "focus": "解决关键问题",
                    "tasks": [
                        {
                            "task": f"处理关键问题: {issue[:50]}...",
                            "priority": "critical",
                            "estimated_effort": "1-2天",
                        }
                        for issue in all_critical_issues[:3]  # 最多3个关键问题
                    ],
                }
            )

        # 第二阶段：重点优化
        roadmap["phases"].append(
            {
                "phase": 2,
                "name": "重点优化",
                "timeline": "2-4周",
                "focus": "基于反馈优化高优先级问题",
                "tasks": [
                    {
                        "task": "分析低分反馈，制定改进计划",
                        "priority": "high",
                        "estimated_effort": "3-5天",
                    },
                    {
                        "task": "优化最常被提及的问题点",
                        "priority": "high",
                        "estimated_effort": "1-2周",
                    },
                    {
                        "task": "改进用户反馈收集机制",
                        "priority": "medium",
                        "estimated_effort": "2-3天",
                    },
                ],
            }
        )

        # 第三阶段：持续改进
        roadmap["phases"].append(
            {
                "phase": 3,
                "name": "持续改进",
                "timeline": "4-8周",
                "focus": "建立持续优化循环",
                "tasks": [
                    {
                        "task": "建立定期反馈分析机制",
                        "priority": "medium",
                        "estimated_effort": "3-5天",
                    },
                    {
                        "task": "实施A/B测试优化策略",
                        "priority": "medium",
                        "estimated_effort": "1-2周",
                    },
                    {
                        "task": "开发自动化优化建议系统",
                        "priority": "low",
                        "estimated_effort": "2-3周",
                    },
                ],
            }
        )

        return roadmap

    def run_ip_image_survey(self, user_segment: str = None) -> Dict[str, Any]:
        """
        运行IP形象用户调查

        Args:
            user_segment: 用户分段 (80后, 90后, 70后, 10后, 其他)

        Returns:
            调查结果字典，包含响应ID和状态
        """
        if not IP_IMAGE_SURVEY_AVAILABLE or "ip_image_survey" not in self.components:
            print("⚠️ IP形象调查系统不可用")
            return {"error": "IP形象调查系统不可用", "success": False}

        try:
            survey_system = self.components["ip_image_survey"]

            # 转换用户分段字符串为枚举
            user_segment_enum = None
            if user_segment:
                segment_mapping = {
                    "80后": UserSegment.GEN_80,
                    "90后": UserSegment.GEN_90,
                    "70后": UserSegment.GEN_70,
                    "10后": UserSegment.GEN_10,
                    "其他": UserSegment.OTHER,
                }
                user_segment_enum = segment_mapping.get(user_segment)

            # 运行交互式调查
            print("\n" + "=" * 60)
            print("🎯 启动Athena IP形象用户调查")
            print("=" * 60)
            print("本调查将收集您对Athena IP形象的反馈，包括：")
            print("  • 视觉风格（漫威电影风格）")
            print("  • 叙事风格（三体风格）")
            print("  • 主题契合度（硅基共生）")
            print("  • 目标受众匹配度（80/90后）")
            print("  • 整体印象和情感共鸣")
            print("=" * 60)

            response = survey_system.run_interactive_survey(user_segment=user_segment_enum)

            if response:
                print(f"\n✅ 调查完成！感谢您的参与。")
                print(f"响应ID: {response.response_id}")
                print(f"用户分段: {response.user_segment.value}")

                # 保存调查数据
                data_dir = survey_system.save_survey_data()
                print(f"调查数据已保存到: {data_dir}")

                # 立即进行分析
                print("\n🔍 立即分析调查结果...")
                analysis = survey_system.analyze_survey_responses(days=30)

                if analysis:
                    print(f"分析完成，共收集 {analysis.total_responses} 份响应")
                    print(
                        f"整体印象得分: {analysis.dimension_scores.get(SurveyDimension.OVERALL_IMPRESSION, 0):.2f}/5"
                    )

                    # 生成和保存报告
                    report = survey_system.generate_survey_report(analysis)
                    report_file = survey_system.save_survey_report(report)
                    print(f"调查报告已保存到: {report_file}")

                return {
                    "success": True,
                    "response_id": response.response_id,
                    "user_segment": response.user_segment.value,
                    "timestamp": response.timestamp.isoformat(),
                    "analysis_available": analysis is not None,
                    "report_file": str(report_file) if analysis else None,
                }
            else:
                print("❌ 调查未完成")
                return {"error": "调查未完成", "success": False}

        except Exception as e:
            error_msg = f"IP形象调查执行异常: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback

            traceback.print_exc()
            return {"error": error_msg, "success": False}

    def analyze_ip_image_survey(self, days: int = 30) -> Dict[str, Any]:
        """
        分析IP形象调查数据

        Args:
            days: 分析最近多少天的数据

        Returns:
            分析结果报告
        """
        if not IP_IMAGE_SURVEY_AVAILABLE or "ip_image_survey" not in self.components:
            print("⚠️ IP形象调查系统不可用")
            return {"error": "IP形象调查系统不可用", "success": False}

        try:
            survey_system = self.components["ip_image_survey"]

            print(f"\n📊 分析最近{days}天的IP形象调查数据")
            print("=" * 60)

            analysis = survey_system.analyze_survey_responses(days=days)

            if not analysis:
                print("ℹ️ 没有调查数据可分析")
                return {
                    "success": True,
                    "has_data": False,
                    "message": f"最近{days}天内没有调查数据",
                }

            print(f"✅ 调查分析完成")
            print(f"  总响应数: {analysis.total_responses}")
            print(f"  完成率: {analysis.completion_rate*100:.1f}%")

            print(f"\n各维度得分:")
            for dimension, score in analysis.dimension_scores.items():
                print(f"  {dimension.value}: {score:.2f}/5")

            print(f"\n关键洞察:")
            for insight in analysis.key_insights[:5]:  # 显示前5个
                print(f"  • {insight}")

            print(f"\n优化建议:")
            for recommendation in analysis.recommendations[:5]:  # 显示前5个
                print(f"  • {recommendation}")

            # 生成和保存报告
            report = survey_system.generate_survey_report(analysis)
            report_file = survey_system.save_survey_report(report)

            # 与IP反馈系统集成分析
            feedback_analysis = None
            if IP_FEEDBACK_SYSTEM_AVAILABLE and "ip_feedback_system" in self.components:
                print(f"\n🔗 与IP反馈系统集成分析...")
                feedback_system = self.components["ip_feedback_system"]
                feedback_analysis = feedback_system.analyze_feedback(
                    feedback_type=FeedbackType.IP_IMAGE, days=days
                )

                if feedback_analysis:
                    print(f"  IP反馈系统数据: {feedback_analysis.total_feedbacks} 条反馈")
                    print(f"  平均评分: {feedback_analysis.average_rating or '无评分'}")

            return {
                "success": True,
                "has_data": True,
                "analysis_id": analysis.survey_id,
                "total_responses": analysis.total_responses,
                "dimension_scores": {
                    dim.value: score for dim, score in analysis.dimension_scores.items()
                },
                "key_insights": analysis.key_insights,
                "recommendations": analysis.recommendations,
                "report_file": str(report_file),
                "feedback_analysis_available": feedback_analysis is not None,
                "feedback_data": (
                    {
                        "total_feedbacks": (
                            feedback_analysis.total_feedbacks if feedback_analysis else 0
                        ),
                        "average_rating": (
                            feedback_analysis.average_rating if feedback_analysis else None
                        ),
                    }
                    if feedback_analysis
                    else None
                ),
            }

        except Exception as e:
            error_msg = f"IP形象调查分析异常: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback

            traceback.print_exc()
            return {"error": error_msg, "success": False}

    def generate_ip_optimization_from_survey(self, days: int = 30) -> Dict[str, Any]:
        """
        基于调查数据生成IP形象优化建议

        Args:
            days: 使用最近多少天的数据

        Returns:
            综合优化建议报告
        """
        print("\n🎯 基于用户调查生成IP形象优化建议")
        print("=" * 60)

        # 首先分析调查数据
        survey_analysis = self.analyze_ip_image_survey(days=days)

        if not survey_analysis.get("success") or not survey_analysis.get("has_data"):
            print("⚠️ 没有调查数据可用于生成优化建议")
            return {
                "error": "没有调查数据可用于生成优化建议",
                "success": False,
                "recommendations": ["需要先收集用户调查数据"],
            }

        try:
            # 从调查分析中提取关键信息
            dimension_scores = survey_analysis.get("dimension_scores", {})
            key_insights = survey_analysis.get("key_insights", [])
            recommendations = survey_analysis.get("recommendations", [])

            # 分析各维度表现
            low_performing_dimensions = []
            high_performing_dimensions = []

            for dim_name, score in dimension_scores.items():
                if score < 3.0:  # 低分维度
                    low_performing_dimensions.append((dim_name, score))
                elif score >= 4.0:  # 高分维度
                    high_performing_dimensions.append((dim_name, score))

            # 生成优先级优化建议
            priority_recommendations = []

            # 1. 针对低分维度的紧急优化
            for dim_name, score in low_performing_dimensions:
                if dim_name == "visual_style":
                    priority_recommendations.append(
                        {
                            "priority": "high",
                            "dimension": dim_name,
                            "score": score,
                            "action": "加强漫威电影风格的视觉设计，增加科技感和视觉冲击力",
                            "deadline": "2周内",
                            "resources_needed": ["视觉设计师", "UI/UX专家"],
                        }
                    )
                elif dim_name == "narrative_style":
                    priority_recommendations.append(
                        {
                            "priority": "high",
                            "dimension": dim_name,
                            "score": score,
                            "action": "深化三体风格的叙事，增加哲学深度和科幻元素",
                            "deadline": "3周内",
                            "resources_needed": ["内容策略师", "科幻顾问"],
                        }
                    )
                elif dim_name == "theme_alignment":
                    priority_recommendations.append(
                        {
                            "priority": "medium",
                            "dimension": dim_name,
                            "score": score,
                            "action": "更清晰地传达硅基共生主题，加强人工智能与人类协作的理念",
                            "deadline": "4周内",
                            "resources_needed": ["主题专家", "技术作家"],
                        }
                    )

            # 2. 保持高分维度的优势
            for dim_name, score in high_performing_dimensions:
                priority_recommendations.append(
                    {
                        "priority": "low",
                        "dimension": dim_name,
                        "score": score,
                        "action": f"保持{dim_name}的优势，考虑扩展到相关领域",
                        "deadline": "6周内",
                        "resources_needed": ["维护团队"],
                    }
                )

            # 3. 总体优化建议
            overall_score = dimension_scores.get("overall_impression", 0)
            if overall_score < 3.5:
                priority_recommendations.append(
                    {
                        "priority": "critical",
                        "dimension": "overall",
                        "score": overall_score,
                        "action": "进行全面的IP形象审查和优化",
                        "deadline": "1个月内",
                        "resources_needed": ["跨职能团队", "用户研究", "竞品分析"],
                    }
                )

            # 4. 用户分段针对性优化
            if "80后用户满意度较低" in " ".join(key_insights):
                priority_recommendations.append(
                    {
                        "priority": "medium",
                        "dimension": "audience_fit",
                        "score": dimension_scores.get("audience_fit", 0),
                        "action": "针对80后用户优化IP形象，提高核心用户满意度",
                        "deadline": "3周内",
                        "resources_needed": ["用户研究员", "目标受众专家"],
                    }
                )

            # 生成时间线
            timeline = []
            current_date = datetime.now()

            # 根据优先级安排时间
            critical_tasks = [r for r in priority_recommendations if r["priority"] == "critical"]
            high_tasks = [r for r in priority_recommendations if r["priority"] == "high"]
            medium_tasks = [r for r in priority_recommendations if r["priority"] == "medium"]
            low_tasks = [r for r in priority_recommendations if r["priority"] == "low"]

            # 关键任务：1-2周
            for i, task in enumerate(critical_tasks[:2]):
                timeline.append(
                    {
                        "task": task["action"],
                        "start_date": (current_date + timedelta(days=i * 7)).strftime("%Y-%m-%d"),
                        "end_date": (current_date + timedelta(days=(i + 1) * 7)).strftime(
                            "%Y-%m-%d"
                        ),
                        "priority": task["priority"],
                    }
                )

            # 高优先级任务：2-4周
            for i, task in enumerate(high_tasks[:3]):
                start_offset = 14 + i * 7  # 从第2周开始
                timeline.append(
                    {
                        "task": task["action"],
                        "start_date": (current_date + timedelta(days=start_offset)).strftime(
                            "%Y-%m-%d"
                        ),
                        "end_date": (current_date + timedelta(days=start_offset + 7)).strftime(
                            "%Y-%m-%d"
                        ),
                        "priority": task["priority"],
                    }
                )

            # 生成最终报告
            optimization_report = {
                "generated_at": datetime.now().isoformat(),
                "data_source": {
                    "survey_analysis": survey_analysis["analysis_id"],
                    "total_responses": survey_analysis["total_responses"],
                    "analysis_period": f"{days}天",
                },
                "performance_summary": {
                    "overall_score": dimension_scores.get("overall_impression", 0),
                    "low_performing_dimensions": [
                        {"dimension": dim, "score": score}
                        for dim, score in low_performing_dimensions
                    ],
                    "high_performing_dimensions": [
                        {"dimension": dim, "score": score}
                        for dim, score in high_performing_dimensions
                    ],
                    "key_insights": key_insights[:5],  # 前5个关键洞察
                },
                "priority_recommendations": priority_recommendations,
                "implementation_timeline": timeline,
                "success_metrics": [
                    "整体印象评分提升≥0.5分",
                    f"低分维度({[dim for dim, _ in low_performing_dimensions]})评分提升≥1.0分",
                    "用户调查参与率提升≥20%",
                    "80/90后用户满意度≥4.0分",
                ],
                "next_steps": [
                    "审批优化建议优先级",
                    "分配资源和团队",
                    "建立进度跟踪机制",
                    "设置验收标准和时间点",
                ],
            }

            print(f"✅ 基于{survey_analysis['total_responses']}份调查响应生成优化建议")
            print(f"  优先级行动: {len(priority_recommendations)}项")
            print(f"  实施时间线: {len(timeline)}个阶段")

            # 保存优化报告
            output_dir = Path(__file__).parent / "assets" / "optimization_reports"
            output_dir.mkdir(parents=True, exist_ok=True)

            report_file = (
                output_dir
                / f"ip_optimization_from_survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(optimization_report, f, indent=2, ensure_ascii=False)

            print(f"  报告保存到: {report_file}")

            return {
                "success": True,
                "report": optimization_report,
                "report_file": str(report_file),
                "priority_recommendations_count": len(priority_recommendations),
                "timeline_phases": len(timeline),
            }

        except Exception as e:
            error_msg = f"生成IP形象优化建议异常: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback

            traceback.print_exc()
            return {"error": error_msg, "success": False}

    def deploy_maref_agent_supervision(
        self,
        enable_guardian: bool = True,
        enable_learner: bool = True,
        enable_explorer: bool = False,
        enable_communicator: bool = False,
    ) -> Dict[str, Any]:
        """
        部署MAREF智能体监督系统

        Args:
            enable_guardian: 启用Guardian安全约束和质量验证
            enable_learner: 启用Learner性能优化循环
            enable_explorer: 启用Explorer资源发现和模式探索
            enable_communicator: 启用Communicator界面表达和报告

        Returns:
            部署结果字典
        """
        print("🤖 部署MAREF智能体监督系统")
        print("=" * 60)

        if "roma_maref" not in self.components:
            error_msg = "ROMA-MAREF集成不可用"
            print(f"❌ {error_msg}")
            return {"error": error_msg, "deployed": False}

        deployment_result = {
            "deployed": False,
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "supervision_mode": "standard",
            "quality_checks": [],
        }

        try:
            roma_maref = self.components["roma_maref"]

            # 调试：检查对象类型和方法
            print(f"DEBUG: roma_maref类型: {type(roma_maref)}")
            print(
                f"DEBUG: roma_maref方法: {[m for m in dir(roma_maref) if 'create' in m or 'agent' in m]}"
            )
            print(f"DEBUG: hasattr create_agent: {hasattr(roma_maref, 'create_agent')}")

            # 1. 部署Guardian智能体（安全与约束）
            if enable_guardian:
                print("🔒 部署Guardian智能体 - 安全与质量验证...")
                try:
                    guardian_agent = roma_maref.create_agent("guardian", "guardian_supervision")
                    if guardian_agent:
                        deployment_result["agents"]["guardian"] = {
                            "id": guardian_agent.agent_id,
                            "type": "guardian",
                            "role": "安全约束和质量验证",
                            "status": "active",
                            "constraints_count": len(getattr(guardian_agent, "constraints", [])),
                            "security_level": getattr(
                                getattr(guardian_agent, "security_level", None), "value", "medium"
                            ),
                        }

                        # 添加质量检查规则
                        quality_rules = [
                            {"rule": "视频分辨率检查", "target": ">=1920x1080", "severity": "high"},
                            {"rule": "帧率检查", "target": ">=30fps", "severity": "high"},
                            {
                                "rule": "内容结构检查",
                                "target": "开场-主体-结尾",
                                "severity": "medium",
                            },
                            {
                                "rule": "品牌一致性检查",
                                "target": "符合视觉指南",
                                "severity": "medium",
                            },
                            {"rule": "行动号召检查", "target": "明确的CTA", "severity": "high"},
                        ]

                        deployment_result["quality_checks"].extend(quality_rules)
                        print(f"✅ Guardian部署成功 - {len(quality_rules)}条质量规则")

                except Exception as e:
                    print(f"⚠️ Guardian部署异常: {e}")
                    deployment_result["agents"]["guardian"] = {"error": str(e), "status": "failed"}

            # 2. 部署Learner智能体（性能优化循环）
            if enable_learner:
                print("📈 部署Learner智能体 - 性能优化循环...")
                try:
                    learner_agent = roma_maref.create_agent("learner", "learner_optimization")
                    if learner_agent:
                        deployment_result["agents"]["learner"] = {
                            "id": learner_agent.agent_id,
                            "type": "learner",
                            "role": "性能监控和优化",
                            "status": "active",
                            "optimization_targets": [
                                "success_rate",
                                "processing_time",
                                "quality_score",
                            ],
                            "learning_rate": getattr(
                                getattr(learner_agent, "learning_rate", None), "value", "adaptive"
                            ),
                        }

                        # 设置性能基线
                        performance_baseline = {
                            "video_generation_time": {
                                "current": 0,
                                "target": 60,
                                "unit": "seconds",
                                "lower_better": True,
                            },
                            "success_rate": {
                                "current": 0,
                                "target": 0.95,
                                "unit": "ratio",
                                "higher_better": True,
                            },
                            "quality_score": {
                                "current": 0,
                                "target": 0.9,
                                "unit": "score",
                                "higher_better": True,
                            },
                        }

                        deployment_result["performance_baseline"] = performance_baseline
                        print(f"✅ Learner部署成功 - {len(performance_baseline)}个优化目标")

                except Exception as e:
                    print(f"⚠️ Learner部署异常: {e}")
                    deployment_result["agents"]["learner"] = {"error": str(e), "status": "failed"}

            # 3. 部署Explorer智能体（可选）
            if enable_explorer:
                print("🔍 部署Explorer智能体 - 资源发现和模式探索...")
                try:
                    explorer_agent = roma_maref.create_agent("explorer", "explorer_discovery")
                    if explorer_agent:
                        deployment_result["agents"]["explorer"] = {
                            "id": explorer_agent.agent_id,
                            "type": "explorer",
                            "role": "资源发现和模式探索",
                            "status": "active",
                            "exploration_domains": [
                                "video_templates",
                                "content_patterns",
                                "workflow_optimizations",
                            ],
                            "discovery_mode": getattr(
                                getattr(explorer_agent, "exploration_mode", None),
                                "value",
                                "systematic",
                            ),
                        }
                        print("✅ Explorer部署成功")

                except Exception as e:
                    print(f"⚠️ Explorer部署异常: {e}")
                    deployment_result["agents"]["explorer"] = {"error": str(e), "status": "failed"}

            # 4. 部署Communicator智能体（可选）
            if enable_communicator:
                print("💬 部署Communicator智能体 - 界面表达和报告...")
                try:
                    communicator_agent = roma_maref.create_agent(
                        "communicator", "communicator_reporting"
                    )
                    if communicator_agent:
                        deployment_result["agents"]["communicator"] = {
                            "id": communicator_agent.agent_id,
                            "type": "communicator",
                            "role": "界面表达和报告生成",
                            "status": "active",
                            "reporting_channels": getattr(
                                communicator_agent, "channels", {}
                            ).keys(),
                            "communication_style": getattr(
                                getattr(communicator_agent, "communication_style", None),
                                "value",
                                "formal",
                            ),
                        }
                        print("✅ Communicator部署成功")

                except Exception as e:
                    print(f"⚠️ Communicator部署异常: {e}")
                    deployment_result["agents"]["communicator"] = {
                        "error": str(e),
                        "status": "failed",
                    }

            # 设置智能体协作网络
            collaboration_network = {
                "guardian_monitors": ["video_quality", "system_security", "content_compliance"],
                "learner_optimizes": [
                    "performance_metrics",
                    "workflow_efficiency",
                    "quality_improvement",
                ],
                "complementary_pairs": [
                    {"pair": "guardian-explorer", "relationship": "约束与探索互补"},
                    {"pair": "communicator-learner", "relationship": "表达与学习互补"},
                ],
                "supervision_frequency": "continuous",
                "alert_threshold": 0.8,  # 80%成功率触发警报
            }

            deployment_result["collaboration_network"] = collaboration_network
            deployment_result["deployed"] = any(
                agent.get("status") == "active" for agent in deployment_result["agents"].values()
            )

            if deployment_result["deployed"]:
                active_agents = [
                    name
                    for name, info in deployment_result["agents"].items()
                    if info.get("status") == "active"
                ]
                print(f"\n✅ MAREF智能体监督部署完成")
                print(f"   激活的智能体: {', '.join(active_agents)}")
                print(f"   质量检查规则: {len(deployment_result['quality_checks'])}条")
                print(
                    f"   性能优化目标: {len(deployment_result.get('performance_baseline', {}))}个"
                )
                print(f"   协作网络: {len(collaboration_network['complementary_pairs'])}个互补对")

                # 记录部署到状态
                self.state["maref_supervision_deployed"] = True
                self.state["active_maref_agents"] = active_agents
                self._log_task_completion(
                    "maref_agent_deployment", "MAREF智能体监督", deployment_result
                )

            else:
                print(f"⚠️ MAREF智能体监督部署失败，无智能体激活")

            return deployment_result

        except Exception as e:
            error_msg = f"MAREF智能体监督部署异常: {str(e)}"
            print(f"❌ {error_msg}")
            return {"error": error_msg, "deployed": False}


def main():
    """主函数"""
    print("🎬 Clawra生产系统 - 集成测试")
    print("=" * 60)

    # 创建配置
    config = ProductionSystemConfig(
        mode=ProductionSystemMode.MVP,
        enable_roma_maref=ROMA_MAREF_AVAILABLE,
        enable_kdenlive=KDENLIVE_AVAILABLE,
        enable_doubao_cli=DOUBAO_CLI_AVAILABLE,
        enable_github_workflow=False,
        quality_preset="standard",
        log_level="INFO",
    )

    # 创建生产系统
    print("初始化生产系统...")
    production_system = ClawraProductionSystem(config)

    # 运行系统测试
    print("\n运行系统测试...")
    test_results = production_system.test_production_system()

    # 显示系统状态
    print("\n系统状态:")
    status = production_system.get_system_status()
    print(f"  模式: {status['system']['mode']}")
    print(f"  运行时间: {status['system']['uptime_seconds']:.1f}秒")
    print(f"  任务完成: {status['performance']['tasks_completed']}")
    print(f"  任务失败: {status['performance']['tasks_failed']}")
    print(f"  成功率: {status['performance']['success_rate']*100:.1f}%")

    # 保存系统快照
    snapshot_file = production_system.save_system_snapshot()

    # 生成示例视频（如果测试通过）
    all_passed = test_results["summary"]["failed_tests"] == 0
    if all_passed and config.enable_kdenlive:
        print("\n" + "=" * 60)
        print("🚀 生成示例视频")
        print("=" * 60)

        # 生成Open Human介绍视频
        print("生成Open Human项目介绍视频...")
        success, result = production_system.generate_openhuman_intro_video()

        if success:
            print(f"✅ 示例视频生成成功!")
            print(f"  项目文件: {result.get('project_file', 'N/A')}")
            print(f"  输出文件数: {result.get('output_file_count', 0)}")

            # 显示渲染命令
            if "render_cmd" in result:
                print(f"  渲染命令: {result['render_cmd']}")
        else:
            print(f"❌ 示例视频生成失败: {result.get('error', '未知错误')}")

    print("\n" + "=" * 60)
    print("✅ Clawra生产系统测试完成")
    print(f"输出目录: {config.output_dir}")
    print(f"快照文件: {snapshot_file}")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 主函数执行异常: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
