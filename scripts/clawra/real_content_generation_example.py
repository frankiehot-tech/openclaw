#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Athena IP数字资产实际内容生成示例
演示如何在真实内容生成场景中使用IP数字资产模板

功能：
1. 使用product_demo_001模板生成技术演示脚本
2. 使用tech_social_001模板生成社交媒体内容
3. 展示不同视觉风格的效果（data_wisdom vs classical_athena）
4. 保存生成的品牌化内容为JSON文件

此脚本对应测试报告中的建议#1：在实际内容生成中使用IP数字资产模板

版本: 1.0.0
创建时间: 2026-04-16
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# 添加当前目录到路径，以便导入本地模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ip_digital_assets_manager import IPDigitalAssetsManager


class RealContentGenerator:
    """实际内容生成器"""

    def __init__(self, output_dir: str = None):
        """初始化内容生成器"""
        # 初始化IP数字资产管理器
        print("=" * 60)
        print("Athena IP数字资产实际内容生成示例")
        print("=" * 60)

        self.manager = IPDigitalAssetsManager()

        # 检查管理器是否成功初始化
        stats = self.manager.get_statistics()
        if not stats["initialized"]:
            print("❌ IP数字资产管理器初始化失败")
            print(f"加载错误: {stats['load_errors']}")
            raise RuntimeError("IP数字资产管理器初始化失败")

        print("✅ IP数字资产管理器初始化成功")
        print(f"资产根目录: {stats['assets_root']}")
        print(f"可用模板: {stats['content_templates_count']}个")
        print(f"可用视觉风格: {stats['visual_identities_count']}个")

        # 设置输出目录
        if output_dir is None:
            self.output_dir = Path(__file__).parent / "assets" / "generated_content"
        else:
            self.output_dir = Path(output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"输出目录: {self.output_dir}")

    def generate_tech_demo_script(self) -> Dict[str, Any]:
        """
        生成技术演示脚本
        使用product_demo_001模板和data_wisdom视觉风格
        """
        print("\n" + "-" * 60)
        print("生成技术演示脚本")
        print("-" * 60)

        # 创建技术演示内容数据
        content_data = {
            "title": "Athena v2.0：硅基共生智慧体网络正式发布",
            "subtitle": "重新定义人工智能与人类智慧的协作边界",
            "date": datetime.now().strftime("%Y年%m月%d日"),
            "author": "Athena技术团队",
            "sections": [
                {
                    "title": "开场震撼：数据智能体的视觉交响曲",
                    "content": "演示开场将展示数据流如何汇聚成雅典娜的智慧之眼，象征AI与人类智慧的共生进化。",
                    "visual_elements": [
                        "深空紫渐变为科技蓝的动态数据流",
                        "能量橙点缀的关键技术突破点",
                        "三体式叙事结构：提出问题 → 展示解决方案 → 揭示未来愿景",
                    ],
                    "duration_seconds": 45,
                },
                {
                    "title": "核心技术：硅基共生架构解析",
                    "content": "深入讲解Athena的分布式智慧体网络如何实现人类意图与AI能力的无缝协作。",
                    "visual_elements": [
                        "交互式架构图展示智慧体协作网络",
                        "实时数据流可视化演示",
                        "对比传统AI系统的性能优势图表",
                    ],
                    "duration_seconds": 90,
                },
                {
                    "title": "实际应用：Clawra生产系统演示",
                    "content": "现场演示Clawra如何自动化内容生成流程，从提示词优化到品牌化内容输出。",
                    "visual_elements": [
                        "实时内容生成演示",
                        "品牌一致性对比展示",
                        "生成效率数据可视化",
                    ],
                    "duration_seconds": 120,
                },
                {
                    "title": "未来愿景：硅基共生的新纪元",
                    "content": "展望Athena生态系统如何赋能开发者社区，推动AI技术的民主化进程。",
                    "visual_elements": [
                        "生态系统扩展路线图",
                        "开发者工具套件预览",
                        "社区贡献者增长预测",
                    ],
                    "duration_seconds": 60,
                },
            ],
            "target_audience": ["CTO/技术决策者", "投资者", "开发者社区领袖", "技术布道者"],
            "key_messages": [
                "Athena不是替代人类的AI，而是增强人类智慧的共生伙伴",
                "硅基共生架构实现了意图与能力的最优匹配",
                "Clawra证明了Athena在实际生产环境中的价值",
                "开源生态将加速AI技术的民主化进程",
            ],
            "success_metrics": [
                "现场互动率 > 30%",
                "技术深度评分 > 4.5/5",
                "行动号召转化率 > 15%",
                "社交媒体提及增长 > 200%",
            ],
        }

        # 使用IP数字资产模板生成品牌化内容
        print(f"使用模板: product_demo_001")
        print(f"视觉风格: data_wisdom")

        branded_content = self.manager.generate_branded_content(
            template_id="product_demo_001", content_data=content_data, visual_style="data_wisdom"
        )

        # 保存生成的内容
        output_file = self.output_dir / "tech_demo_script.json"
        self._save_content(branded_content, output_file)

        print(f"✅ 技术演示脚本生成完成")
        print(f"保存到: {output_file}")

        return branded_content

    def generate_social_media_content(self) -> Dict[str, Any]:
        """
        生成社交媒体内容
        使用tech_social_001模板和classical_athena视觉风格
        """
        print("\n" + "-" * 60)
        print("生成社交媒体内容")
        print("-" * 60)

        # 创建社交媒体内容数据
        content_data = {
            "platform": "LinkedIn + Twitter",
            "campaign_title": "#硅基共生革命",
            "post_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "content_type": "技术深度文章 + 视觉海报",
            "sections": [
                {
                    "type": "hook",
                    "content": "如果AI不再是工具，而是智慧共生的伙伴，会发生什么？\n\nAthena v2.0的硅基共生架构给出了答案。",
                    "hashtags": ["#AI", "#人工智能", "#技术创新"],
                },
                {
                    "type": "insight",
                    "content": "传统AI系统是单向的：人类输入，AI输出。\n\nAthena的共生网络是双向的：人类意图与AI能力实时协同，形成智慧增强回路。",
                    "hashtags": ["#硅基共生", "#人机协作", "#未来科技"],
                },
                {
                    "type": "demo",
                    "content": "Clawra生产系统演示：\n• 从自然语言描述到品牌化视频内容，全流程自动化\n• 保持Athena IP视觉一致性：漫威风格 + 三体叙事\n• GitHub用户画像驱动的内容优化",
                    "hashtags": ["#Clawra", "#内容生成", "#自动化"],
                },
                {
                    "type": "cta",
                    "content": "加入Athena开发者社区：\n• 探索开源代码库\n• 贡献提示词知识库\n• 参与硅基共生实验\n\n🔗 链接在评论区",
                    "hashtags": ["#开源", "#开发者社区", "#加入我们"],
                },
            ],
            "visual_elements": {
                "main_image_style": "漫威电影开场风格",
                "color_scheme": "深空紫 + 能量橙冲击",
                "typography": "科技感无衬线字体 + 动态数据可视化",
                "animation": "数据智能体协作网络构建过程",
            },
            "engagement_strategy": {
                "post_timing": "技术社区活跃时段（UTC+8 20:00-22:00）",
                "engagement_tactics": ["问题引导", "技术挑战", "抽奖互动", "AMA问答"],
                "success_metrics": ["互动率 > 5%", "分享率 > 2%", "转化率 > 1%"],
            },
            "target_audience_segments": [
                {
                    "segment": "核心开发者",
                    "interests": ["AI/ML", "开源项目", "技术架构"],
                    "platforms": ["GitHub", "Hacker News", "Reddit r/MachineLearning"],
                },
                {
                    "segment": "技术决策者",
                    "interests": ["企业AI应用", "技术投资回报", "竞争差异化"],
                    "platforms": ["LinkedIn", "行业报告", "技术峰会"],
                },
                {
                    "segment": "AI爱好者",
                    "interests": ["前沿科技", "未来趋势", "创新应用"],
                    "platforms": ["Twitter", "YouTube", "技术博客"],
                },
            ],
        }

        # 使用IP数字资产模板生成品牌化内容
        print(f"使用模板: tech_social_001")
        print(f"视觉风格: classical_athena")

        branded_content = self.manager.generate_branded_content(
            template_id="tech_social_001",
            content_data=content_data,
            visual_style="classical_athena",
        )

        # 保存生成的内容
        output_file = self.output_dir / "social_media_content.json"
        self._save_content(branded_content, output_file)

        print(f"✅ 社交媒体内容生成完成")
        print(f"保存到: {output_file}")

        return branded_content

    def demonstrate_template_variations(self) -> List[Dict[str, Any]]:
        """
        演示模板和视觉风格的变体
        展示相同内容在不同模板和风格下的差异
        """
        print("\n" + "-" * 60)
        print("演示模板和视觉风格变体")
        print("-" * 60)

        # 基础内容数据
        base_content = {
            "title": "Athena智慧体网络的核心优势",
            "description": "硅基共生架构如何实现1+1>2的智慧增强效果",
            "key_points": ["意图与能力的最优匹配", "分布式智慧体协作网络", "实时学习和适应性优化"],
        }

        variations = []

        # 变体1: product_demo_001 + data_wisdom
        print(f"\n变体1: product_demo_001 + data_wisdom")
        variation1 = self.manager.generate_branded_content(
            template_id="product_demo_001", content_data=base_content, visual_style="data_wisdom"
        )
        variations.append(
            {
                "name": "product_demo_001 + data_wisdom",
                "content": variation1,
                "style_description": "科技感、未来感、数据驱动的现代智慧形象",
            }
        )

        # 变体2: product_demo_001 + classical_athena
        print(f"变体2: product_demo_001 + classical_athena")
        variation2 = self.manager.generate_branded_content(
            template_id="product_demo_001",
            content_data=base_content,
            visual_style="classical_athena",
        )
        variations.append(
            {
                "name": "product_demo_001 + classical_athena",
                "content": variation2,
                "style_description": "古典智慧女神形象，哲学深度和永恒价值",
            }
        )

        # 变体3: tech_social_001 + data_wisdom
        print(f"变体3: tech_social_001 + data_wisdom")
        variation3 = self.manager.generate_branded_content(
            template_id="tech_social_001", content_data=base_content, visual_style="data_wisdom"
        )
        variations.append(
            {
                "name": "tech_social_001 + data_wisdom",
                "content": variation3,
                "style_description": "社交媒体优化的科技视觉风格",
            }
        )

        # 保存变体演示
        output_file = self.output_dir / "template_variations.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(variations, f, indent=2, ensure_ascii=False)

        print(f"✅ 模板变体演示生成完成")
        print(f"保存到: {output_file}")

        return variations

    def _save_content(self, content: Dict[str, Any], output_file: Path) -> None:
        """保存内容到JSON文件"""
        # 确保输出目录存在
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

    def run_all_examples(self) -> Dict[str, Any]:
        """运行所有内容生成示例"""
        print("\n" + "=" * 60)
        print("开始运行所有内容生成示例")
        print("=" * 60)

        results = {}

        try:
            # 1. 生成技术演示脚本
            results["tech_demo"] = self.generate_tech_demo_script()

            # 2. 生成社交媒体内容
            results["social_media"] = self.generate_social_media_content()

            # 3. 演示模板变体
            results["variations"] = self.demonstrate_template_variations()

            # 生成总结报告
            summary = {
                "timestamp": datetime.now().isoformat(),
                "examples_generated": len(results),
                "output_directory": str(self.output_dir),
                "files_created": [str(f) for f in self.output_dir.glob("*.json")],
                "templates_used": ["product_demo_001", "tech_social_001"],
                "visual_styles_used": ["data_wisdom", "classical_athena"],
                "content_types": ["技术演示脚本", "社交媒体内容", "模板变体演示"],
            }

            # 保存总结报告
            summary_file = self.output_dir / "generation_summary.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            results["summary"] = summary

            print("\n" + "=" * 60)
            print("🎉 所有内容生成示例完成!")
            print("=" * 60)
            print(f"生成的示例: {len(results)}个")
            print(f"输出目录: {self.output_dir}")
            print(f"创建的文件:")
            for file_path in self.output_dir.glob("*.json"):
                print(f"  - {file_path.name}")

            return results

        except Exception as e:
            print(f"❌ 内容生成失败: {e}")
            import traceback

            traceback.print_exc()
            raise


def main():
    """主函数"""
    try:
        # 创建内容生成器
        generator = RealContentGenerator()

        # 运行所有示例
        results = generator.run_all_examples()

        print("\n" + "=" * 60)
        print("建议的下一步操作:")
        print("=" * 60)
        print("1. 查看生成的内容文件:")
        print(f"   cd {generator.output_dir}")
        print("   ls -la *.json")
        print("\n2. 在Clawra生产系统中使用这些模板:")
        print("   from ip_digital_assets_manager import IPDigitalAssetsManager")
        print("   manager = IPDigitalAssetsManager()")
        print("   content = manager.generate_branded_content(...)")
        print("\n3. 扩展更多模板和视觉风格（建议#2）:")
        print("   - 添加新的ContentTemplate实例")
        print("   - 创建新的VisualIdentity")
        print("   - 更新品牌指南文档")
        print("\n4. 收集用户反馈（建议#3）:")
        print("   - 设计用户反馈收集机制")
        print("   - 集成到Clawra生产系统中")
        print("   - 定期分析反馈并优化IP形象")

        return 0

    except Exception as e:
        print(f"❌ 主程序执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
