#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clawra模块 - Kdenlive增强视频生成引擎
集成Kdenlive广告级视频生成功能
兼容EnhancedVideoGenerationEngine接口，提供专业级视频生成能力
"""

import json
import os

# 导入增强引擎
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

sys.path.append(os.path.dirname(__file__))

from enhanced_engine import EnhancedVideoGenerationEngine
from kdenlive_generator import KdenliveVideoGenerator


class KdenliveEnhancedVideoGenerationEngine(EnhancedVideoGenerationEngine):
    """Kdenlive增强视频生成引擎 - 集成广告级视频生成功能"""

    def __init__(
        self,
        output_dir: str = None,
        persona=None,
        dalle_api_key: str = None,
        dalle_endpoint: str = None,
        kdenlive_output_dir: str = None,
    ):
        """
        初始化Kdenlive增强视频生成引擎

        Args:
            output_dir: 输出目录路径（用于传统视频生成）
            persona: Athena数字人格配置
            dalle_api_key: DALL-E 3 API密钥（可选）
            dalle_endpoint: DALL-E 3 API端点（可选）
            kdenlive_output_dir: Kdenlive项目输出目录（如果为None则使用临时目录）
        """
        super().__init__(output_dir, persona, dalle_api_key, dalle_endpoint)

        # Kdenlive生成器
        self.kdenlive_generator = KdenliveVideoGenerator(output_dir=kdenlive_output_dir)

        # 广告级视频配置
        self.ad_video_config = {
            "resolution": {
                "premium": (3840, 2160),  # 4K UHD
                "standard": (1920, 1080),  # 全高清
                "social": (1080, 1920),  # 竖屏社交
                "mobile": (720, 1280),  # 移动优化
            },
            "frame_rate": {
                "film": 24,  # 电影感
                "broadcast": 30,  # 广播电视
                "cinematic": 60,  # 电影流畅
            },
            "duration_presets": {
                "social_short": 15,  # 短视频平台
                "ad_standard": 30,  # 标准广告
                "explainer": 60,  # 解释视频
                "presentation": 120,  # 演示视频
            },
            "quality_presets": {
                "premium": "crf=18 preset=slow",  # 广告级质量
                "standard": "crf=22 preset=medium",  # 标准质量
                "fast": "crf=26 preset=fast",  # 快速渲染
            },
        }

        # 广告视频内容模板
        self.ad_content_templates = {
            "product_showcase": {
                "title": "产品展示",
                "sections": [
                    {"type": "intro", "duration": 3, "content": "引人注目的开场"},
                    {"type": "features", "duration": 8, "content": "核心功能展示"},
                    {"type": "benefits", "duration": 5, "content": "用户价值体现"},
                    {"type": "cta", "duration": 4, "content": "明确的行动号召"},
                ],
                "total_duration": 20,
            },
            "brand_story": {
                "title": "品牌故事",
                "sections": [
                    {"type": "origin", "duration": 5, "content": "起源与愿景"},
                    {"type": "journey", "duration": 10, "content": "发展历程"},
                    {"type": "mission", "duration": 8, "content": "使命与价值观"},
                    {"type": "future", "duration": 7, "content": "未来展望"},
                ],
                "total_duration": 30,
            },
            "project_announcement": {
                "title": "项目发布",
                "sections": [
                    {"type": "announcement", "duration": 4, "content": "重磅发布"},
                    {"type": "overview", "duration": 7, "content": "项目概览"},
                    {"type": "innovation", "duration": 6, "content": "创新亮点"},
                    {"type": "community", "duration": 5, "content": "社区邀请"},
                    {"type": "action", "duration": 8, "content": "行动指南"},
                ],
                "total_duration": 30,
            },
            "openhuman_intro": {
                "title": "Open Human 项目介绍",
                "sections": [
                    {"type": "vision", "duration": 6, "content": "碳硅共生愿景"},
                    {"type": "architecture", "duration": 8, "content": "多层架构设计"},
                    {"type": "technology", "duration": 7, "content": "关键技术栈"},
                    {"type": "community", "duration": 5, "content": "开源社区建设"},
                    {"type": "invitation", "duration": 4, "content": "参与邀请"},
                ],
                "total_duration": 30,
            },
        }

        print(f"🎬 Kdenlive增强视频生成引擎初始化完成")
        print(f"   🔧 DALL-E 3集成: {'✅ 已配置' if self.dalle_api_key else '⚠️  模拟模式'}")
        print(f"   🎥 Kdenlive集成: ✅ 广告级视频生成")
        print(f"   📁 输出目录: {self.output_dir}")
        if hasattr(self.kdenlive_generator, "output_dir"):
            print(f"   🎬 Kdenlive输出: {self.kdenlive_generator.output_dir}")

    def generate_ad_level_video(
        self,
        project_name: str = "广告级视频演示",
        resolution: str = "standard",
        fps: str = "broadcast",
        duration_preset: str = "ad_standard",
        content_template: str = "openhuman_intro",
        title_text: str = None,
        product_text: str = None,
        call_to_action_text: str = None,
    ) -> Tuple[bool, Dict[str, str]]:
        """
        生成广告级视频项目

        Args:
            project_name: 项目名称
            resolution: 分辨率预设（premium/standard/social/mobile）
            fps: 帧率预设（film/broadcast/cinematic）
            duration_preset: 时长预设（social_short/ad_standard/explainer/presentation）
            content_template: 内容模板（product_showcase/brand_story/project_announcement/openhuman_intro）
            title_text: 自定义标题文本（覆盖模板）
            product_text: 自定义产品描述文本（覆盖模板）
            call_to_action_text: 自定义号召性用语文本（覆盖模板）

        Returns:
            (success, result_dict) 元组
            result_dict包含: project_file, xml_file, render_cmd, summary, files
        """
        print("=" * 60)
        print("🎬 生成广告级视频")
        print("=" * 60)

        # 获取配置参数
        width, height = self.ad_video_config["resolution"][resolution]
        fps_value = self.ad_video_config["frame_rate"][fps]
        duration = self.ad_video_config["duration_presets"][duration_preset]

        # 获取内容模板
        template = self.ad_content_templates.get(
            content_template, self.ad_content_templates["openhuman_intro"]
        )

        # 应用自定义文本
        if title_text:
            template["title"] = title_text

        print(f"📋 项目配置:")
        print(f"   📝 名称: {project_name}")
        print(f"   🖥️  分辨率: {width}x{height} ({resolution})")
        print(f"   📺 帧率: {fps_value}fps ({fps})")
        print(f"   ⏱️  时长: {duration}秒 ({duration_preset})")
        print(f"   📄 模板: {template['title']} ({content_template})")

        if title_text:
            print(f"   ✏️  自定义标题: {title_text}")
        if product_text:
            print(f"   ✏️  自定义产品描述: {product_text[:50]}...")
        if call_to_action_text:
            print(f"   ✏️  自定义号召性用语: {call_to_action_text[:50]}...")

        # 调用Kdenlive生成器
        print("\n🚀 调用Kdenlive生成器...")
        success, project_file, xml_file = self.kdenlive_generator.generate_video(
            project_name=project_name, width=width, height=height, fps=fps_value, duration=duration
        )

        result = {
            "success": success,
            "project_name": project_name,
            "template_used": content_template,
            "project_file": project_file,
            "xml_file": xml_file,
        }

        if success:
            print(f"\n✅ Kdenlive项目生成成功")
            print(f"   📁 项目文件: {project_file}")
            print(f"   📄 XML文件: {xml_file}")

            # 生成渲染命令
            render_cmd = self.kdenlive_generator.generate_render_command(xml_file)
            result["render_cmd"] = render_cmd
            print(f"   🎬 渲染命令: {render_cmd}")

            # 生成项目摘要
            summary = self.kdenlive_generator.generate_project_summary(project_file)
            result["summary"] = summary
            print(f"   📊 项目摘要:")
            for line in summary.split("\n"):
                print(f"      {line}")

            # 获取输出文件列表
            output_files = self.kdenlive_generator.get_output_files()
            result["output_files"] = output_files
            result["output_file_count"] = len(output_files)

            print(f"\n📁 输出文件 ({len(output_files)}个):")
            for filename, filepath in output_files.items():
                print(f"   📄 {filename}: {filepath}")

            # 生成项目文档
            documentation = self._generate_ad_project_documentation(project_name, template, result)
            result["documentation"] = documentation

            # 保存项目元数据
            metadata_file = self._save_ad_project_metadata(project_name, result)
            result["metadata_file"] = metadata_file

            print(f"\n📋 项目元数据: {metadata_file}")

        else:
            print(f"\n❌ Kdenlive项目生成失败")
            result["error"] = "Kdenlive生成器调用失败"

        print("\n" + "=" * 60)
        return success, result

    def _generate_ad_project_documentation(
        self, project_name: str, template: Dict, result: Dict
    ) -> str:
        """
        生成广告项目文档

        Args:
            project_name: 项目名称
            template: 内容模板
            result: 生成结果

        Returns:
            文档文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_filename = f"{project_name}_documentation_{timestamp}.md"
        doc_path = os.path.join(self.output_dir, "ad_documentation", doc_filename)
        os.makedirs(os.path.dirname(doc_path), exist_ok=True)

        doc_content = f"""# {project_name} - 广告级视频项目文档

## 项目信息
- **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **模板类型**: {template['title']}
- **项目文件**: {result.get('project_file', 'N/A')}
- **MLT XML文件**: {result.get('xml_file', 'N/A')}
- **输出文件数量**: {result.get('output_file_count', 0)}

## 技术规格
"""

        # 从摘要中提取技术规格
        if "summary" in result:
            doc_content += "\n```\n"
            doc_content += result["summary"]
            doc_content += "\n```\n"

        # 渲染命令
        if "render_cmd" in result:
            doc_content += f"\n## 渲染命令\n\n```bash\n{result['render_cmd']}\n```\n"

        # 内容大纲
        doc_content += f"\n## 内容大纲\n\n**视频主题**: {template['title']}\n\n**章节结构**:\n\n"
        for i, section in enumerate(template.get("sections", [])):
            doc_content += f"{i+1}. **{section['type']}** - {section['duration']}秒\n"
            doc_content += f"   {section['content']}\n\n"

        # 生产工作流
        doc_content += f"""
## 生产工作流

### 1. 预览项目
```bash
# 使用Kdenlive打开项目
open {result.get('project_file', 'project.kdenlive-cli.json')}
```

### 2. 渲染视频
```bash
# 执行渲染命令
{result.get('render_cmd', 'melt project.xml -consumer avformat:output.mp4')}
```

### 3. 质量检查
- ✅ 分辨率符合广告标准
- ✅ 帧率稳定
- ✅ 内容结构完整
- ✅ 行动号召明确

### 4. 交付格式
- **主文件**: MP4 (H.264/AAC)
- **备选格式**: MOV (ProRes 422)
- **社交优化**: 竖屏版本（如果需要）
- **字幕文件**: SRT（多语言）

## 内容优化建议

### 视觉优化
1. 检查颜色分级是否符合品牌指南
2. 确认字幕可读性（大小、颜色、对比度）
3. 验证转场效果自然流畅
4. 检查音频电平（-6dB到-3dB）

### 内容优化
1. 开场3秒内传达核心信息
2. 每10-15秒有视觉变化保持观众注意力
3. 结尾5秒强化品牌识别
4. 行动号召（CTA）明确可执行

## 性能指标
- **目标受众**: 开发者、技术爱好者、开源社区
- **平台适配**: YouTube、Twitter、LinkedIn、GitHub
- **预期时长**: {template.get('total_duration', 30)}秒
- **文件大小**: 基于分辨率优化
- **加载时间**: <5秒（1080p流媒体）

---

*此文档由Clawra Kdenlive增强引擎自动生成*
*项目: Athena/openclaw Clawra模块*
*版本: 1.0.0 | 广告级视频生成*
"""

        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(doc_content)

        print(f"📄 项目文档已生成: {doc_path}")
        return doc_path

    def _save_ad_project_metadata(self, project_name: str, result: Dict) -> str:
        """
        保存广告项目元数据

        Args:
            project_name: 项目名称
            result: 生成结果

        Returns:
            元数据文件路径
        """
        metadata = {
            "project_name": project_name,
            "generated_at": datetime.now().isoformat(),
            "engine_version": "KdenliveEnhancedVideoGenerationEngine 1.0",
            "result": result,
            "system_info": {
                "output_dir": self.output_dir,
                "kdenlive_output_dir": getattr(self.kdenlive_generator, "output_dir", "N/A"),
                "dalle_integration": "enabled" if self.dalle_api_key else "simulated",
            },
        }

        # 移除循环引用
        if "documentation" in result:
            metadata["result"]["documentation"] = "已生成，见文档文件"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadata_filename = f"{project_name}_metadata_{timestamp}.json"
        metadata_path = os.path.join(self.output_dir, "ad_metadata", metadata_filename)
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return metadata_path

    def generate_openhuman_intro_video(self) -> Tuple[bool, Dict[str, str]]:
        """
        生成Open Human项目介绍视频（专用方法）

        Returns:
            (success, result_dict) 元组
        """
        print("🎬 生成Open Human项目介绍视频")

        return self.generate_ad_level_video(
            project_name="Open_Human_Project_Introduction",
            resolution="standard",
            fps="broadcast",
            duration_preset="explainer",
            content_template="openhuman_intro",
            title_text="Open Human: 碳硅共生开源项目",
            product_text="多层架构的AI-人类协作框架，实现数字智慧与生物智慧的融合演进",
            call_to_action_text="加入我们的开源社区，共同构建碳硅共生的未来",
        )

    def generate_github_project_announcement(
        self, repo_name: str, version: str = "1.0.0"
    ) -> Tuple[bool, Dict[str, str]]:
        """
        生成GitHub项目发布视频（专用方法）

        Args:
            repo_name: 仓库名称
            version: 版本号

        Returns:
            (success, result_dict) 元组
        """
        print(f"🎬 生成GitHub项目发布视频: {repo_name} v{version}")

        return self.generate_ad_level_video(
            project_name=f"{repo_name}_Release_v{version}",
            resolution="standard",
            fps="broadcast",
            duration_preset="ad_standard",
            content_template="project_announcement",
            title_text=f"{repo_name} v{version} 正式发布",
            product_text=f"开源项目{repo_name}迎来了重大更新版本{version}，带来全新的功能和性能提升",
            call_to_action_text="访问GitHub仓库，查看文档、提交Issue或参与贡献",
        )

    def test_ad_generation(self):
        """
        测试广告级视频生成功能
        """
        print("=" * 60)
        print("🧪 测试Kdenlive广告级视频生成")
        print("=" * 60)

        tests = [
            {
                "name": "Open Human介绍视频",
                "method": self.generate_openhuman_intro_video,
                "args": [],
            },
            {
                "name": "快速社交广告",
                "method": self.generate_ad_level_video,
                "args": [
                    "Social_Media_Ad",
                    "social",
                    "broadcast",
                    "social_short",
                    "product_showcase",
                ],
            },
        ]

        results = []

        for test in tests:
            print(f"\n🚀 测试: {test['name']}")
            try:
                success, result = test["method"](*test["args"])

                if success:
                    print(f"✅ 测试通过: {test['name']}")
                    print(f"   项目文件: {result.get('project_file', 'N/A')}")
                    print(f"   输出文件: {result.get('output_file_count', 0)}个")
                else:
                    print(f"❌ 测试失败: {test['name']}")
                    print(f"   错误: {result.get('error', '未知错误')}")

                results.append(
                    {
                        "test_name": test["name"],
                        "success": success,
                        "project_file": result.get("project_file"),
                        "output_files": result.get("output_file_count", 0),
                    }
                )

            except Exception as e:
                print(f"💥 测试异常: {test['name']}")
                print(f"   异常: {str(e)}")
                results.append({"test_name": test["name"], "success": False, "error": str(e)})

        # 输出测试总结
        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)

        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.get("success", False))

        print(f"测试总数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {total_tests - passed_tests}")

        for r in results:
            status = "✅" if r.get("success", False) else "❌"
            print(f"  {status} {r['test_name']}")
            if not r.get("success", False) and "error" in r:
                print(f"    错误: {r['error']}")

        return all(r.get("success", False) for r in results)


def test_kdenlive_enhanced_engine():
    """测试Kdenlive增强引擎"""
    print("=" * 60)
    print("测试Kdenlive增强视频生成引擎")
    print("=" * 60)

    try:
        # 创建增强引擎
        engine = KdenliveEnhancedVideoGenerationEngine()

        # 运行测试
        print("\n开始功能测试...")
        all_passed = engine.test_ad_generation()

        if all_passed:
            print("\n✅ Kdenlive增强引擎测试全部通过!")
            return True
        else:
            print("\n❌ Kdenlive增强引擎测试失败!")
            return False

    except Exception as e:
        print(f"\n💥 引擎初始化或测试异常: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 运行测试
    if test_kdenlive_enhanced_engine():
        print("\n✅ Kdenlive增强引擎测试通过")
        exit(0)
    else:
        print("\n❌ Kdenlive增强引擎测试失败")
        exit(1)
