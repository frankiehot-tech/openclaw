#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展IP数字资产测试脚本
测试新添加的内容模板和视觉风格

新添加的模板：
1. technical_doc_001 - 技术文档模板
2. product_release_001 - 产品发布模板
3. tutorial_001 - 教程模板
4. community_update_001 - 社区更新模板

新添加的视觉风格：
1. cyberpunk - 赛博朋克风格
2. minimalist - 极简主义风格
3. futuristic - 未来主义风格

版本: 1.0.0
创建时间: 2026-04-16
"""

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from ip_digital_assets_manager import IPDigitalAssetsManager


def test_extended_templates():
    """测试扩展的模板"""
    print("=" * 60)
    print("测试扩展的内容模板")
    print("=" * 60)

    # 初始化管理器
    manager = IPDigitalAssetsManager()
    stats = manager.get_statistics()

    print(f"✅ IP数字资产管理器初始化成功")
    print(f"内容模板总数: {stats['content_templates_count']}")
    print(f"视觉风格总数: {stats['visual_identities_count']}")

    # 测试所有模板
    test_templates = [
        ("product_demo_001", "演示模板"),
        ("tech_social_001", "社交媒体模板"),
        ("technical_doc_001", "技术文档模板"),
        ("product_release_001", "产品发布模板"),
        ("tutorial_001", "教程模板"),
        ("community_update_001", "社区更新模板"),
    ]

    all_passed = True
    for template_id, template_name in test_templates:
        template = manager.get_template(template_id)
        if template:
            print(f"✅ {template_name} ({template_id}) 加载成功")
            print(f"   标题: {template.title}")
            print(f"   类型: {template.template_type}")
            print(f"   目标受众: {', '.join(template.target_audience[:3])}")
        else:
            print(f"❌ {template_name} ({template_id}) 加载失败")
            all_passed = False

    return all_passed


def test_extended_visual_styles():
    """测试扩展的视觉风格"""
    print("\n" + "=" * 60)
    print("测试扩展的视觉风格")
    print("=" * 60)

    manager = IPDigitalAssetsManager()

    test_styles = [
        ("classical_athena", "古典雅典娜风格"),
        ("data_wisdom", "数据智慧风格"),
        ("cyberpunk", "赛博朋克风格"),
        ("minimalist", "极简主义风格"),
        ("futuristic", "未来主义风格"),
    ]

    all_passed = True
    for style_id, style_name in test_styles:
        visual_identity = manager.get_visual_identity(style_id)
        if visual_identity:
            print(f"✅ {style_name} ({style_id}) 加载成功")
            print(f"   描述: {visual_identity.description}")
            print(f"   使用场景: {', '.join(visual_identity.usage_scenarios[:2])}")
        else:
            print(f"❌ {style_name} ({style_id}) 加载失败")
            all_passed = False

    return all_passed


def demonstrate_new_templates():
    """演示新模板的使用"""
    print("\n" + "=" * 60)
    print("演示新模板的内容生成")
    print("=" * 60)

    manager = IPDigitalAssetsManager()

    # 演示技术文档模板
    print("\n📄 演示技术文档模板 (technical_doc_001)")
    tech_doc_content = {
        "title": "Athena API v2.0 技术文档",
        "version": "2.0.0",
        "author": "Athena技术文档团队",
        "sections": [
            {
                "name": "快速开始",
                "content": "如何在5分钟内启动Athena API服务",
                "code_examples": ["安装命令", "配置示例", "验证脚本"],
            },
            {
                "name": "核心API",
                "content": "Athena核心接口的详细说明",
                "endpoints": ["/generate", "/optimize", "/analyze"],
            },
        ],
    }

    tech_doc_result = manager.generate_branded_content(
        template_id="technical_doc_001",
        content_data=tech_doc_content,
        visual_style="minimalist",  # 技术文档适合极简风格
    )

    if "error" not in tech_doc_result:
        print("✅ 技术文档生成成功")
        print(f"   模板: {tech_doc_result.get('template_id')}")
        print(f"   视觉风格: minimalist")
    else:
        print(f"❌ 技术文档生成失败: {tech_doc_result.get('error')}")

    # 演示产品发布模板
    print("\n🚀 演示产品发布模板 (product_release_001)")
    release_content = {
        "product_name": "Athena Clawra v2.0",
        "release_date": "2026年4月16日",
        "version": "2.0.0",
        "tagline": "重新定义AI内容生成的工作流",
        "key_features": [
            "完整的字节跳动工作流集成",
            "智能IP数字资产管理系统",
            "企业级部署就绪架构",
        ],
        "target_users": ["内容创作者", "技术团队", "企业客户"],
    }

    release_result = manager.generate_branded_content(
        template_id="product_release_001",
        content_data=release_content,
        visual_style="futuristic",  # 产品发布适合未来主义风格
    )

    if "error" not in release_result:
        print("✅ 产品发布内容生成成功")
        print(f"   模板: {release_result.get('template_id')}")
        print(f"   视觉风格: futuristic")
    else:
        print(f"❌ 产品发布内容生成失败: {release_result.get('error')}")

    # 演示教程模板
    print("\n🎓 演示教程模板 (tutorial_001)")
    tutorial_content = {
        "tutorial_title": "使用Clawra自动化内容生成工作流",
        "difficulty": "中级",
        "estimated_time": "45分钟",
        "prerequisites": ["Python基础", "GitHub账户", "豆包AI账号"],
        "learning_objectives": ["掌握Clawra核心概念", "配置IP数字资产", "运行自动化内容生成"],
    }

    tutorial_result = manager.generate_branded_content(
        template_id="tutorial_001",
        content_data=tutorial_content,
        visual_style="cyberpunk",  # 教程可以尝试赛博朋克风格
    )

    if "error" not in tutorial_result:
        print("✅ 教程内容生成成功")
        print(f"   模板: {tutorial_result.get('template_id')}")
        print(f"   视觉风格: cyberpunk")
    else:
        print(f"❌ 教程内容生成失败: {tutorial_result.get('error')}")

    # 保存演示结果
    output_dir = Path(__file__).parent / "assets" / "extended_templates_demo"
    output_dir.mkdir(parents=True, exist_ok=True)

    demo_results = {
        "technical_doc": tech_doc_result,
        "product_release": release_result,
        "tutorial": tutorial_result,
    }

    output_file = output_dir / "extended_templates_demo.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(demo_results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 演示结果保存到: {output_file}")

    return all(("error" not in r for r in [tech_doc_result, release_result, tutorial_result]))


def generate_template_usage_guide():
    """生成模板使用指南"""
    print("\n" + "=" * 60)
    print("生成模板使用指南")
    print("=" * 60)

    manager = IPDigitalAssetsManager()

    guide = {
        "timestamp": "2026-04-16",
        "title": "Athena IP数字资产模板使用指南",
        "introduction": "本指南介绍如何使用Athena IP数字资产模板生成品牌化内容",
        "templates": [],
        "visual_styles": [],
        "best_practices": [
            "技术文档建议使用minimalist风格，强调清晰和可读性",
            "产品发布建议使用futuristic风格，突出创新和未来感",
            "社交媒体内容建议使用data_wisdom或cyberpunk风格，增强视觉冲击力",
            "教程内容可以尝试多种风格，根据目标受众选择",
            "社区更新建议使用classical_athena风格，体现社区价值和传承",
        ],
        "integration_examples": [
            "在Clawra生产系统中调用generate_branded_content()方法",
            "使用get_template()获取特定模板进行自定义",
            "使用get_visual_identity()获取视觉风格指南",
            "结合GitHub用户画像优化内容策略",
        ],
    }

    # 收集模板信息
    for template_id in [
        "product_demo_001",
        "tech_social_001",
        "technical_doc_001",
        "product_release_001",
        "tutorial_001",
        "community_update_001",
    ]:
        template = manager.get_template(template_id)
        if template:
            guide["templates"].append(
                {
                    "id": template_id,
                    "title": template.title,
                    "type": template.template_type,
                    "target_audience": template.target_audience,
                    "recommended_styles": _get_recommended_styles(template_id),
                }
            )

    # 收集视觉风格信息
    for style_id in ["classical_athena", "data_wisdom", "cyberpunk", "minimalist", "futuristic"]:
        visual_identity = manager.get_visual_identity(style_id)
        if visual_identity:
            guide["visual_styles"].append(
                {
                    "id": style_id,
                    "name": visual_identity.name,
                    "description": visual_identity.description,
                    "usage_scenarios": visual_identity.usage_scenarios,
                    "suitable_templates": _get_suitable_templates(style_id),
                }
            )

    # 保存指南
    output_dir = Path(__file__).parent / "assets" / "guides"
    output_dir.mkdir(parents=True, exist_ok=True)

    guide_file = output_dir / "ip_assets_template_guide.json"
    with open(guide_file, "w", encoding="utf-8") as f:
        json.dump(guide, f, indent=2, ensure_ascii=False)

    print(f"✅ 模板使用指南生成完成")
    print(f"保存到: {guide_file}")

    return True


def _get_recommended_styles(template_id):
    """获取模板推荐的视觉风格"""
    recommendations = {
        "product_demo_001": ["data_wisdom", "futuristic"],
        "tech_social_001": ["cyberpunk", "data_wisdom"],
        "technical_doc_001": ["minimalist", "classical_athena"],
        "product_release_001": ["futuristic", "cyberpunk"],
        "tutorial_001": ["cyberpunk", "data_wisdom", "minimalist"],
        "community_update_001": ["classical_athena", "data_wisdom"],
    }
    return recommendations.get(template_id, ["data_wisdom"])


def _get_suitable_templates(style_id):
    """获取适合特定视觉风格的模板"""
    suitability = {
        "classical_athena": ["community_update_001", "technical_doc_001"],
        "data_wisdom": ["product_demo_001", "tech_social_001", "tutorial_001"],
        "cyberpunk": ["tech_social_001", "tutorial_001", "product_release_001"],
        "minimalist": ["technical_doc_001", "tutorial_001"],
        "futuristic": ["product_release_001", "product_demo_001"],
    }
    return suitability.get(style_id, [])


def main():
    """主测试函数"""
    print("=" * 60)
    print("扩展IP数字资产测试套件")
    print("=" * 60)

    results = []

    try:
        # 测试1: 扩展模板加载
        results.append(("扩展模板加载测试", test_extended_templates()))

        # 测试2: 扩展视觉风格加载
        results.append(("扩展视觉风格测试", test_extended_visual_styles()))

        # 测试3: 新模板内容生成演示
        results.append(("新模板内容生成演示", demonstrate_new_templates()))

        # 测试4: 生成使用指南
        results.append(("模板使用指南生成", generate_template_usage_guide()))

        # 汇总结果
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{test_name}: {status}")

        print(f"\n总计: {passed}/{total} 通过")

        if passed == total:
            print("\n🎉 所有测试通过！IP数字资产扩展成功。")
            print("\n建议的下一步操作:")
            print("1. 在实际项目中使用新模板")
            print("2. 根据用户反馈优化模板设计")
            print("3. 创建更多视觉风格变体")
            print("4. 将IP数字资产集成到更多工作流中")
            return 0
        else:
            print(f"\n⚠️ {total - passed} 个测试失败，请检查问题。")
            return 1

    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
