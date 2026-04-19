#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Athena IP数字资产管理器
管理Athena IP数字资产体系，包括品牌标识、视觉形象、动态资产、语音系统、内容模板等

设计理念：
- 硅基共生：人工智能与人类智慧的协作进化
- 漫威视觉：科技感、未来感、视觉冲击力
- 三体叙事：宏大视角、硬核深度、哲学思考

GitHub用户画像：
- 第一梯队：80后和90后（技术成熟期）
- 第二梯队：70后和10后（技术影响者和新生代）
- 视觉偏好：漫威电影风格
- 叙事偏好：三体风格

版本: 1.0.0
创建时间: 2026-04-16
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IPAssetType(Enum):
    """IP数字资产类型"""

    LOGO_SYSTEM = "logo_system"  # Logo系统
    VISUAL_IDENTITY = "visual_identity"  # 视觉形象
    DYNAMIC_ASSETS = "dynamic_assets"  # 动态资产
    VOICE_SYSTEM = "voice_system"  # 语音系统
    CONTENT_TEMPLATES = "content_templates"  # 内容模板
    BRAND_GUIDELINES = "brand_guidelines"  # 品牌指南


@dataclass
class BrandColor:
    """品牌颜色"""

    name: str
    hex_code: str
    rgb: Tuple[int, int, int]
    description: str
    usage: str  # primary, secondary, accent, background, text

    def to_css(self) -> str:
        """转换为CSS变量格式"""
        var_name = f"--athena-{self.name.lower().replace(' ', '-')}"
        return f"{var_name}: {self.hex_code};"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "hex_code": self.hex_code,
            "rgb": self.rgb,
            "description": self.description,
            "usage": self.usage,
        }


@dataclass
class ContentTemplate:
    """内容模板"""

    template_id: str
    template_type: str  # presentation, documentation, social_media
    title: str
    structure: Dict[str, Any]
    visual_elements: Dict[str, Any]
    narrative_style: str  # 三体式, 故事弧线等
    target_audience: List[str]

    def apply_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用内容数据到模板"""
        # 这里可以实现模板渲染逻辑
        result = {
            "template_id": self.template_id,
            "applied_content": content_data,
            "structure_guide": self.structure,
            "visual_references": self.visual_elements,
        }
        return result


@dataclass
class VisualIdentity:
    """视觉形象"""

    name: str
    style: str  # classical_athena, data_wisdom
    description: str
    usage_scenarios: List[str]
    file_paths: Dict[str, str]  # 各种格式的文件路径

    def get_asset_path(self, asset_type: str) -> Optional[str]:
        """获取指定类型的资源路径"""
        return self.file_paths.get(asset_type)


@dataclass
class IPDigitalAssetsConfig:
    """IP数字资产配置"""

    assets_root: Path
    enabled_asset_types: List[IPAssetType] = field(
        default_factory=lambda: [
            IPAssetType.LOGO_SYSTEM,
            IPAssetType.CONTENT_TEMPLATES,
            IPAssetType.BRAND_GUIDELINES,
        ]
    )
    auto_load_templates: bool = True
    validate_on_load: bool = True


class IPDigitalAssetsManager:
    """IP数字资产管理器"""

    def __init__(self, config: IPDigitalAssetsConfig = None):
        """
        初始化IP数字资产管理器

        Args:
            config: IP数字资产配置，默认为assets/athena_ip目录
        """
        if config is None:
            # 默认配置：使用当前项目目录下的assets/athena_ip
            base_dir = Path(__file__).parent
            assets_root = base_dir / "assets" / "athena_ip"
            config = IPDigitalAssetsConfig(assets_root=assets_root)

        self.config = config
        self.assets_root = config.assets_root

        # 资产缓存
        self.brand_colors: List[BrandColor] = []
        self.content_templates: Dict[str, ContentTemplate] = {}
        self.visual_identities: Dict[str, VisualIdentity] = {}
        self.brand_guidelines: Dict[str, Any] = {}

        # 初始化状态
        self.initialized = False
        self.load_errors = []

        # 自动加载资产
        if config.auto_load_templates:
            self.load_all_assets()

    def load_all_assets(self) -> bool:
        """加载所有IP数字资产"""
        try:
            logger.info(f"开始加载IP数字资产，根目录: {self.assets_root}")

            # 1. 验证目录结构
            if not self.validate_directory_structure():
                logger.error("目录结构验证失败")
                return False

            # 2. 加载品牌颜色
            self.load_brand_colors()

            # 3. 加载内容模板
            self.load_content_templates()

            # 4. 加载视觉形象
            self.load_visual_identities()

            # 5. 加载品牌指南
            self.load_brand_guidelines()

            # 设置初始化状态
            self.initialized = True

            logger.info(f"IP数字资产加载完成:")
            logger.info(f"  - 品牌颜色: {len(self.brand_colors)}种")
            logger.info(f"  - 内容模板: {len(self.content_templates)}个")
            logger.info(f"  - 视觉形象: {len(self.visual_identities)}个")
            logger.info(f"  - 品牌指南: {len(self.brand_guidelines)}份")

            return True

        except Exception as e:
            logger.error(f"加载IP数字资产失败: {e}")
            self.load_errors.append(str(e))
            return False

    def validate_directory_structure(self) -> bool:
        """验证目录结构完整性"""
        expected_dirs = [
            "01_logo_system",
            "02_visual_identity",
            "03_dynamic_assets",
            "04_voice_system",
            "05_content_templates",
            "06_brand_guidelines",
        ]

        for dir_name in expected_dirs:
            dir_path = self.assets_root / dir_name
            if not dir_path.exists():
                logger.warning(f"缺失目录: {dir_name}")
                return False

        logger.info("目录结构验证通过")
        return True

    def load_brand_colors(self) -> bool:
        """加载品牌颜色"""
        colors_file = self.assets_root / "01_logo_system" / "brand_colors" / "brand_colors.md"

        if not colors_file.exists():
            logger.warning(f"品牌颜色文件不存在: {colors_file}")
            return False

        try:
            # 从markdown文件解析品牌颜色
            with open(colors_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 这里实现具体的解析逻辑
            # 简化版：硬编码已知颜色
            self.brand_colors = [
                BrandColor(
                    name="科技蓝",
                    hex_code="#4A90E2",
                    rgb=(74, 144, 226),
                    description="主品牌色，代表科技和创新",
                    usage="primary",
                ),
                BrandColor(
                    name="数据绿",
                    hex_code="#00D4AA",
                    rgb=(0, 212, 170),
                    description="辅助色，代表数据和智能",
                    usage="secondary",
                ),
                BrandColor(
                    name="能量橙",
                    hex_code="#FF6B35",
                    rgb=(255, 107, 53),
                    description="强调色，代表能量和行动",
                    usage="accent",
                ),
                BrandColor(
                    name="深空紫",
                    hex_code="#7B61FF",
                    rgb=(123, 97, 255),
                    description="科技感背景色",
                    usage="background",
                ),
                BrandColor(
                    name="深灰背景",
                    hex_code="#1A1A2E",
                    rgb=(26, 26, 46),
                    description="深色背景",
                    usage="background",
                ),
                BrandColor(
                    name="浅灰背景",
                    hex_code="#F5F7FA",
                    rgb=(245, 247, 250),
                    description="浅色背景",
                    usage="background",
                ),
            ]

            logger.info(f"加载品牌颜色: {len(self.brand_colors)}种")
            return True

        except Exception as e:
            logger.error(f"加载品牌颜色失败: {e}")
            return False

    def load_content_templates(self) -> bool:
        """加载内容模板"""
        templates_dir = self.assets_root / "05_content_templates"

        if not templates_dir.exists():
            logger.warning(f"内容模板目录不存在: {templates_dir}")
            return False

        try:
            # 加载演示模板
            presentation_readme = templates_dir / "presentation" / "README.md"
            if presentation_readme.exists():
                with open(presentation_readme, "r", encoding="utf-8") as f:
                    content = f.read()

                # 解析演示模板（简化版）
                demo_template = ContentTemplate(
                    template_id="product_demo_001",
                    template_type="presentation",
                    title="Athena v2.0：硅基共生智慧体网络发布",
                    structure={
                        "opening_impact": [
                            "开场震撼：数据流汇聚成雅典娜智慧之眼",
                            "核心主张：人工智能与人类智慧的共生进化",
                        ],
                        "narrative_structure": "三体式结构",
                        "visual_style": "漫威电影开场风格",
                    },
                    visual_elements={
                        "color_scheme": "深空紫渐变 + 能量橙冲击",
                        "animation": "数据智能体从分散到协作的网络构建过程",
                    },
                    narrative_style="三体式结构",
                    target_audience=["技术决策者", "投资者", "开发者社区"],
                )
                self.content_templates["product_demo_001"] = demo_template

            # 加载社交媒体模板
            social_readme = templates_dir / "social_media" / "README.md"
            if social_readme.exists():
                social_template = ContentTemplate(
                    template_id="tech_social_001",
                    template_type="social_media",
                    title="技术内容社交媒体模板",
                    structure={
                        "platforms": ["Twitter", "LinkedIn", "Reddit", "Hacker News"],
                        "content_types": ["视觉海报", "技术演示视频", "深度技术文章", "互动问答"],
                        "success_metrics": ["互动率", "分享率", "转化率"],
                    },
                    visual_elements={
                        "style": "漫威风格设计",
                        "animation_style": "data_flow_heroic",
                    },
                    narrative_style="技术民主化 + 社区共建",
                    target_audience=["开发者", "技术布道者", "开源贡献者"],
                )
                self.content_templates["tech_social_001"] = social_template

            # 添加技术文档模板
            technical_doc_template = ContentTemplate(
                template_id="technical_doc_001",
                template_type="documentation",
                title="Athena技术文档模板",
                structure={
                    "document_structure": ["概述", "安装指南", "API参考", "使用示例", "故障排除"],
                    "writing_style": "清晰准确 + 技术深度",
                    "target_readers": ["开发者", "技术文档工程师", "API用户"],
                },
                visual_elements={
                    "diagram_style": "架构图 + 序列图",
                    "code_highlighting": "语法高亮 + 注释规范",
                    "typography": "等宽字体 + 清晰层级",
                },
                narrative_style="逻辑严谨 + 实用导向",
                target_audience=["开发者", "技术写作者", "集成工程师"],
            )
            self.content_templates["technical_doc_001"] = technical_doc_template

            # 添加产品发布模板
            product_release_template = ContentTemplate(
                template_id="product_release_001",
                template_type="announcement",
                title="Athena产品发布模板",
                structure={
                    "announcement_flow": [
                        "重大新闻",
                        "核心功能",
                        "技术突破",
                        "用户价值",
                        "获取方式",
                    ],
                    "emotional_arc": "期待 → 震撼 → 信任 → 行动",
                    "media_elements": ["产品演示视频", "技术架构图", "用户案例", "路线图"],
                },
                visual_elements={
                    "release_visual_style": "发布会级别视觉设计",
                    "animation": "产品功能逐步揭示动画",
                    "typography": "大标题冲击力 + 精细排版",
                },
                narrative_style="史诗级发布叙事",
                target_audience=["用户", "媒体", "投资者", "行业分析师"],
            )
            self.content_templates["product_release_001"] = product_release_template

            # 添加教程模板
            tutorial_template = ContentTemplate(
                template_id="tutorial_001",
                template_type="tutorial",
                title="Athena技术教程模板",
                structure={
                    "learning_path": ["前置知识", "目标设定", "逐步指导", "代码示例", "扩展练习"],
                    "difficulty_curve": "平滑渐进",
                    "interactive_elements": ["可运行代码", "交互式演示", "自我测试"],
                },
                visual_elements={
                    "tutorial_visuals": "步骤截图 + 箭头标注",
                    "code_walkthrough": "代码逐步高亮",
                    "progress_indicator": "学习进度可视化",
                },
                narrative_style="导师式引导 + 成就驱动",
                target_audience=["初学者", "中级开发者", "教育者"],
            )
            self.content_templates["tutorial_001"] = tutorial_template

            # 添加社区更新模板
            community_update_template = ContentTemplate(
                template_id="community_update_001",
                template_type="community",
                title="Athena社区更新模板",
                structure={
                    "update_sections": [
                        "社区动态",
                        "贡献者 spotlight",
                        "项目进展",
                        "未来活动",
                        "参与方式",
                    ],
                    "engagement_focus": "透明度 + 参与感",
                    "community_values": ["开源协作", "知识共享", "互助成长"],
                },
                visual_elements={
                    "community_visuals": "贡献者头像墙 + 项目增长图表",
                    "interactive": "可点击链接 + 社交媒体集成",
                    "typography": "友好亲切 + 社区感",
                },
                narrative_style="社区故事 + 集体成就",
                target_audience=["开源贡献者", "社区成员", "项目关注者"],
            )
            self.content_templates["community_update_001"] = community_update_template

            logger.info(f"加载内容模板: {len(self.content_templates)}个")
            return True

        except Exception as e:
            logger.error(f"加载内容模板失败: {e}")
            return False

    def load_visual_identities(self) -> bool:
        """加载视觉形象"""
        visual_dir = self.assets_root / "02_visual_identity"

        if not visual_dir.exists():
            logger.warning(f"视觉形象目录不存在: {visual_dir}")
            return False

        try:
            # 古典雅典娜风格
            classical_athena = VisualIdentity(
                name="classical_athena",
                style="classical_athena",
                description="古典智慧女神形象，体现哲学深度和永恒价值",
                usage_scenarios=["品牌起源故事", "哲学深度内容", "企业愿景展示"],
                file_paths={
                    "guideline": "02_visual_identity/classical_athena/classical_athena_guidelines.md",
                    "illustrations": "02_visual_identity/classical_athena/illustrations/",
                },
            )
            self.visual_identities["classical_athena"] = classical_athena

            # 数据智慧风格
            data_wisdom = VisualIdentity(
                name="data_wisdom",
                style="data_wisdom",
                description="数据驱动的现代智慧形象，体现科技感和未来感",
                usage_scenarios=["技术产品演示", "数据可视化", "AI应用展示"],
                file_paths={
                    "guideline": "02_visual_identity/data_wisdom/data_wisdom_guidelines.md",
                    "interactive": "02_visual_identity/data_wisdom/data_wisdom_interactive.json",
                },
            )
            self.visual_identities["data_wisdom"] = data_wisdom

            # 赛博朋克风格
            cyberpunk = VisualIdentity(
                name="cyberpunk",
                style="cyberpunk",
                description="赛博朋克视觉风格，融合高科技与低生活美学，霓虹色调与数字网格",
                usage_scenarios=["前沿技术展示", "未来城市概念", "数字艺术创作", "黑客文化内容"],
                file_paths={
                    "guideline": "02_visual_identity/cyberpunk/cyberpunk_guidelines.md",
                    "palette": "02_visual_identity/cyberpunk/cyberpunk_color_palette.json",
                    "textures": "02_visual_identity/cyberpunk/cyberpunk_textures/",
                },
            )
            self.visual_identities["cyberpunk"] = cyberpunk

            # 极简主义风格
            minimalist = VisualIdentity(
                name="minimalist",
                style="minimalist",
                description="极简主义设计，强调留白、清晰层级和功能优先美学",
                usage_scenarios=["技术文档", "API参考", "企业演示", "教育材料"],
                file_paths={
                    "guideline": "02_visual_identity/minimalist/minimalist_guidelines.md",
                    "typography": "02_visual_identity/minimalist/minimalist_typography.css",
                    "layouts": "02_visual_identity/minimalist/minimalist_layout_templates/",
                },
            )
            self.visual_identities["minimalist"] = minimalist

            # 未来主义风格
            futuristic = VisualIdentity(
                name="futuristic",
                style="futuristic",
                description="未来主义视觉语言，流畅线条、全息效果和智能材料质感",
                usage_scenarios=["产品愿景", "科技预测", "概念演示", "创新发布会"],
                file_paths={
                    "guideline": "02_visual_identity/futuristic/futuristic_guidelines.md",
                    "materials": "02_visual_identity/futuristic/futuristic_material_library.json",
                    "animations": "02_visual_identity/futuristic/futuristic_animation_principles.md",
                },
            )
            self.visual_identities["futuristic"] = futuristic

            logger.info(f"加载视觉形象: {len(self.visual_identities)}个")
            return True

        except Exception as e:
            logger.error(f"加载视觉形象失败: {e}")
            return False

    def load_brand_guidelines(self) -> bool:
        """加载品牌指南"""
        guidelines_dir = self.assets_root / "06_brand_guidelines"

        if not guidelines_dir.exists():
            logger.warning(f"品牌指南目录不存在: {guidelines_dir}")
            return False

        try:
            # 加载视觉风格指南
            visual_guide = guidelines_dir / "visual_style_guide" / "visual_style_guide.md"
            if visual_guide.exists():
                with open(visual_guide, "r", encoding="utf-8") as f:
                    content = f.read()
                self.brand_guidelines["visual_style"] = {
                    "title": "视觉风格指南",
                    "content_preview": content[:500] + "..." if len(content) > 500 else content,
                }

            # 加载语音语调指南
            voice_guide = guidelines_dir / "voice_tone_guide" / "voice_tone_guide.md"
            if voice_guide.exists():
                with open(voice_guide, "r", encoding="utf-8") as f:
                    content = f.read()
                self.brand_guidelines["voice_tone"] = {
                    "title": "语音语调指南",
                    "content_preview": content[:500] + "..." if len(content) > 500 else content,
                }

            logger.info(f"加载品牌指南: {len(self.brand_guidelines)}份")
            return True

        except Exception as e:
            logger.error(f"加载品牌指南失败: {e}")
            return False

    def get_brand_css(self) -> str:
        """获取品牌CSS变量定义"""
        css_lines = ["/* Athena品牌CSS变量 */", ":root {"]

        for color in self.brand_colors:
            var_name = f"--athena-{color.name.lower().replace(' ', '-')}"
            css_lines.append(f"  {var_name}: {color.hex_code}; /* {color.description} */")

        css_lines.extend(
            [
                "}",
                "",
                "/* 实用类 */",
                ".athena-primary { color: var(--athena-科技蓝); }",
                ".athena-secondary { color: var(--athena-数据绿); }",
                ".athena-accent { color: var(--athena-能量橙); }",
                ".athena-bg-dark { background-color: var(--athena-深灰背景); color: white; }",
                ".athena-bg-light { background-color: var(--athena-浅灰背景); color: var(--athena-深灰背景); }",
            ]
        )

        return "\n".join(css_lines)

    def get_template(self, template_id: str) -> Optional[ContentTemplate]:
        """获取指定ID的内容模板"""
        return self.content_templates.get(template_id)

    def get_visual_identity(self, style: str) -> Optional[VisualIdentity]:
        """获取指定风格的视觉形象"""
        return self.visual_identities.get(style)

    def generate_branded_content(
        self, template_id: str, content_data: Dict[str, Any], visual_style: str = "data_wisdom"
    ) -> Dict[str, Any]:
        """生成品牌化内容"""
        template = self.get_template(template_id)
        visual_identity = self.get_visual_identity(visual_style)

        if not template:
            return {"error": f"模板不存在: {template_id}"}

        # 应用模板
        result = template.apply_content(content_data)

        # 添加品牌信息
        result["brand_info"] = {
            "visual_style": visual_style,
            "brand_colors": [color.to_dict() for color in self.brand_colors],
            "design_principles": ["硅基共生", "漫威视觉", "三体叙事"],
            "target_audience": template.target_audience,
        }

        # 添加GitHub用户画像信息
        result["github_user_profile"] = {
            "primary_audience": ["80后", "90后"],
            "secondary_audience": ["70后", "10后"],
            "visual_preference": "漫威电影风格",
            "narrative_preference": "三体风格",
            "thematic_focus": "硅基共生智慧体",
        }

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "initialized": self.initialized,
            "assets_root": str(self.assets_root),
            "brand_colors_count": len(self.brand_colors),
            "content_templates_count": len(self.content_templates),
            "visual_identities_count": len(self.visual_identities),
            "brand_guidelines_count": len(self.brand_guidelines),
            "load_errors": self.load_errors,
            "all_assets_loaded": all(
                [
                    len(self.brand_colors) > 0,
                    len(self.content_templates) > 0,
                    len(self.visual_identities) > 0,
                    len(self.brand_guidelines) > 0,
                ]
            ),
        }

    def test_integration(self) -> Dict[str, Any]:
        """测试与生产系统的集成"""
        test_results = {
            "directory_structure": self.validate_directory_structure(),
            "brand_colors_loaded": len(self.brand_colors) > 0,
            "content_templates_loaded": len(self.content_templates) > 0,
            "visual_identities_loaded": len(self.visual_identities) > 0,
            "brand_guidelines_loaded": len(self.brand_guidelines) > 0,
            "css_generation": len(self.get_brand_css()) > 0,
            "content_generation": False,
        }

        # 测试内容生成
        try:
            test_content = {
                "title": "测试内容",
                "description": "这是一个测试内容生成",
                "sections": ["介绍", "主体", "结论"],
            }
            branded_content = self.generate_branded_content(
                "product_demo_001", test_content, "data_wisdom"
            )
            test_results["content_generation"] = "error" not in branded_content
        except Exception as e:
            test_results["content_generation_error"] = str(e)

        test_results["all_passed"] = all(
            [
                test_results["directory_structure"],
                test_results["brand_colors_loaded"],
                test_results["content_templates_loaded"],
                test_results["visual_identities_loaded"],
                test_results["css_generation"],
                test_results["content_generation"],
            ]
        )

        return test_results


# 简单使用示例
if __name__ == "__main__":
    print("=" * 60)
    print("Athena IP数字资产管理器测试")
    print("=" * 60)

    # 创建管理器
    manager = IPDigitalAssetsManager()

    # 获取统计信息
    stats = manager.get_statistics()
    print(f"初始化状态: {'✅' if stats['initialized'] else '❌'}")
    print(f"资产根目录: {stats['assets_root']}")
    print(f"品牌颜色: {stats['brand_colors_count']}种")
    print(f"内容模板: {stats['content_templates_count']}个")
    print(f"视觉形象: {stats['visual_identities_count']}个")

    # 测试集成
    print("\n集成测试结果:")
    test_results = manager.test_integration()
    for test_name, result in test_results.items():
        if isinstance(result, bool):
            status = "✅" if result else "❌"
            print(f"  {test_name}: {status}")

    if test_results.get("all_passed", False):
        print("\n🎉 IP数字资产管理器测试通过!")
    else:
        print("\n⚠️ IP数字资产管理器测试失败")
        if manager.load_errors:
            print("加载错误:", manager.load_errors)

    # 演示品牌CSS生成
    print(f"\n生成的品牌CSS ({len(manager.get_brand_css())} 字符):")
    css_preview = (
        manager.get_brand_css()[:200] + "..."
        if len(manager.get_brand_css()) > 200
        else manager.get_brand_css()
    )
    print(css_preview)

    print("\n" + "=" * 60)
    print("测试完成，可以集成到Clawra生产系统中")
    print("=" * 60)
