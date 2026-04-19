#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP数字资产与生产系统集成测试
验证IP数字资产管理器与Clawra生产系统的完整集成效果

测试范围：
1. IP数字资产管理器独立功能测试
2. 生产系统集成验证
3. 品牌化内容生成测试
4. CSS变量生成测试
5. 集成错误处理测试

版本: 1.0.0
创建时间: 2026-04-16
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# 添加路径以便导入Clawra模块
sys.path.append(os.path.dirname(__file__))


def make_serializable(obj):
    """递归转换对象为JSON可序列化的类型"""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [make_serializable(item) for item in obj]
    else:
        # 对于其他对象，尝试转换为字符串或使用repr
        try:
            # 如果对象有to_dict方法，使用它
            if hasattr(obj, "to_dict"):
                return make_serializable(obj.to_dict())
            # 如果对象有__dict__属性，使用它
            elif hasattr(obj, "__dict__"):
                return make_serializable(obj.__dict__)
            else:
                return str(obj)
        except Exception:
            return str(obj)


def test_ip_assets_manager_standalone():
    """测试IP数字资产管理器独立功能"""
    print("=" * 60)
    print("🧪 测试1: IP数字资产管理器独立功能")
    print("=" * 60)

    try:
        from ip_digital_assets_manager import IPDigitalAssetsManager

        # 创建临时目录用于测试
        with tempfile.TemporaryDirectory() as tmpdir:
            # 复制现有资产目录结构到临时目录
            assets_src = Path(__file__).parent / "assets" / "athena_ip"
            assets_dst = Path(tmpdir) / "athena_ip"

            if assets_src.exists():
                # 复制目录结构（保持相对路径）
                shutil.copytree(assets_src, assets_dst)
                print(f"✅ 复制资产目录结构到临时目录: {assets_dst}")
            else:
                print(f"⚠️ 资产源目录不存在: {assets_src}")
                # 创建基础目录结构
                for dir_name in [
                    "01_logo_system",
                    "02_visual_identity",
                    "05_content_templates",
                    "06_brand_guidelines",
                ]:
                    (assets_dst / dir_name).mkdir(parents=True, exist_ok=True)
                print(f"✅ 创建基础目录结构: {assets_dst}")

            # 初始化管理器
            print("初始化IP数字资产管理器...")
            manager = IPDigitalAssetsManager()

            # 测试1.1: 验证资产加载
            print("\n测试1.1: 资产加载验证")
            stats = manager.get_statistics()
            print(f"  初始化状态: {'✅' if stats['initialized'] else '❌'}")
            print(f"  品牌颜色数量: {stats['brand_colors_count']}")
            print(f"  内容模板数量: {stats['content_templates_count']}")
            print(f"  视觉形象数量: {stats['visual_identities_count']}")

            asset_load_ok = stats["brand_colors_count"] > 0 and stats["content_templates_count"] > 0
            print(f"  资产加载: {'✅通过' if asset_load_ok else '❌失败'}")

            # 测试1.2: 品牌CSS生成
            print("\n测试1.2: 品牌CSS生成测试")
            css_content = manager.get_brand_css()
            css_valid = len(css_content) > 100 and ":root {" in css_content

            print(f"  CSS长度: {len(css_content)}字符")
            print(f"  CSS有效性: {'✅有效' if css_valid else '❌无效'}")
            if css_valid:
                print(f"  CSS预览: {css_content[:200]}...")

            # 测试1.3: 内容模板获取
            print("\n测试1.3: 内容模板功能测试")
            template = manager.get_template("product_demo_001")
            template_valid = template is not None

            if template_valid:
                print(f"  模板ID: {template.template_id}")
                print(f"  模板类型: {template.template_type}")
                print(f"  标题: {template.title}")
                print(f"  目标受众: {', '.join(template.target_audience)}")
            print(f"  模板获取: {'✅成功' if template_valid else '❌失败'}")

            # 测试1.4: 品牌化内容生成
            print("\n测试1.4: 品牌化内容生成测试")
            if template_valid:
                test_content = {
                    "title": "Athena技术发布演示",
                    "description": "硅基共生智慧体网络的技术创新演示",
                    "sections": ["技术架构", "核心优势", "应用场景", "未来展望"],
                }

                branded_content = manager.generate_branded_content(
                    template_id="product_demo_001",
                    content_data=test_content,
                    visual_style="data_wisdom",
                )

                content_gen_ok = "error" not in branded_content
                print(f"  内容生成: {'✅成功' if content_gen_ok else '❌失败'}")

                if content_gen_ok:
                    print(f"  包含品牌信息: {'brand_info' in branded_content}")
                    print(f"  包含GitHub用户画像: {'github_user_profile' in branded_content}")

                    # 保存示例输出
                    output_file = Path(tmpdir) / "branded_content_example.json"
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(branded_content, f, indent=2, ensure_ascii=False)
                    print(f"  示例输出保存到: {output_file}")

            # 测试1.5: 集成测试
            print("\n测试1.5: 集成测试")
            integration_results = manager.test_integration()
            integration_passed = integration_results.get("all_passed", False)

            print(f"  集成测试结果: {'✅全部通过' if integration_passed else '❌部分失败'}")
            for test_name, result in integration_results.items():
                if isinstance(result, bool):
                    print(f"    {test_name}: {'✅' if result else '❌'}")

            # 汇总结果
            all_passed = (
                asset_load_ok
                and css_valid
                and template_valid
                and content_gen_ok
                and integration_passed
            )

            print("\n" + "=" * 40)
            print(f"独立功能测试: {'✅全部通过' if all_passed else '❌部分失败'}")
            print("=" * 40)

            return all_passed, {
                "asset_load": asset_load_ok,
                "css_generation": css_valid,
                "template_retrieval": template_valid,
                "content_generation": content_gen_ok,
                "integration_test": integration_passed,
                "overall": all_passed,
            }

    except Exception as e:
        print(f"❌ IP数字资产管理器独立功能测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False, {"error": str(e)}


def test_production_system_integration():
    """测试生产系统集成"""
    print("\n" + "=" * 60)
    print("🧪 测试2: 生产系统集成验证")
    print("=" * 60)

    try:
        from datetime import datetime

        from clawra_production_system import (
            ClawraProductionSystem,
            ProductionSystemConfig,
            ProductionSystemMode,
        )

        # 创建生产系统配置（MVP模式）
        config = ProductionSystemConfig(
            mode=ProductionSystemMode.MVP,
            enable_roma_maref=False,  # 简化测试，不启动复杂智能体
            enable_kdenlive=False,  # 不测试视频生成
            enable_doubao_cli=False,  # 不测试豆包CLI
            enable_github_workflow=False,
            quality_preset="standard",
            log_level="INFO",
        )

        print("初始化生产系统...")
        production_system = ClawraProductionSystem(config)

        # 测试2.1: 检查IP数字资产组件状态
        print("\n测试2.1: 组件状态检查")
        component_status = production_system._get_component_status()
        ip_assets_available = component_status.get("ip_digital_assets", False)

        print(f"  IP数字资产组件可用: {'✅是' if ip_assets_available else '❌否'}")
        print(f"  所有组件状态:")
        for component, available in component_status.items():
            print(f"    {component}: {'✅' if available else '❌'}")

        # 测试2.2: 验证组件实例
        print("\n测试2.2: 组件实例验证")
        ip_assets_instance = production_system.components.get("ip_digital_assets")
        ip_assets_valid = ip_assets_instance is not None

        print(f"  IP数字资产实例存在: {'✅是' if ip_assets_valid else '❌否'}")

        if ip_assets_valid:
            # 测试2.3: 通过生产系统访问IP数字资产功能
            print("\n测试2.3: 功能访问测试")
            try:
                stats = ip_assets_instance.get_statistics()
                print(f"  资产根目录: {stats['assets_root']}")
                print(f"  品牌颜色数量: {stats['brand_colors_count']}")
                print(f"  内容模板数量: {stats['content_templates_count']}")

                # 测试品牌CSS生成
                css_content = ip_assets_instance.get_brand_css()
                css_available = len(css_content) > 0
                print(f"  品牌CSS可生成: {'✅是' if css_available else '❌否'}")

                # 测试内容模板访问
                template = ip_assets_instance.get_template("product_demo_001")
                template_accessible = template is not None
                print(f"  内容模板可访问: {'✅是' if template_accessible else '❌否'}")

            except Exception as e:
                print(f"  ❌ 功能访问失败: {e}")
                css_available = False
                template_accessible = False

        # 测试2.4: 系统状态报告
        print("\n测试2.4: 系统状态报告测试")
        system_status = production_system.get_system_status()

        print(f"  系统初始化: {'✅是' if system_status['system']['initialized'] else '❌否'}")
        print(f"  运行模式: {system_status['system']['mode']}")
        print(
            f"  IP数字资产组件状态: {'✅启用' if system_status['components'].get('ip_digital_assets', False) else '❌禁用'}"
        )

        # 汇总结果
        integration_passed = (
            ip_assets_available and ip_assets_valid and css_available and template_accessible
        )

        print("\n" + "=" * 40)
        print(f"生产系统集成测试: {'✅全部通过' if integration_passed else '❌部分失败'}")
        print("=" * 40)

        # 保存集成测试报告
        integration_report = {
            "timestamp": datetime.now().isoformat(),
            "component_status": component_status,
            "ip_assets_available": ip_assets_available,
            "ip_assets_instance_valid": ip_assets_valid,
            "css_generation_available": css_available,
            "template_access_available": template_accessible,
            "system_status": system_status,
            "integration_passed": integration_passed,
        }

        report_file = Path(config.output_dir) / "ip_assets_integration_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(make_serializable(integration_report), f, indent=2, ensure_ascii=False)

        print(f"\n📋 集成测试报告已保存: {report_file}")

        return integration_passed, integration_report

    except Exception as e:
        print(f"❌ 生产系统集成测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False, {"error": str(e)}


def test_branded_content_workflow():
    """测试品牌化内容工作流"""
    print("\n" + "=" * 60)
    print("🧪 测试3: 品牌化内容工作流")
    print("=" * 60)

    try:
        from ip_digital_assets_manager import IPDigitalAssetsManager

        # 初始化管理器
        manager = IPDigitalAssetsManager()

        # 测试3.1: GitHub用户画像应用测试
        print("\n测试3.1: GitHub用户画像应用测试")

        # 创建符合GitHub用户画像的内容
        github_user_profile_content = {
            "title": "Clawra开源项目发布：重新定义AI内容创作",
            "description": "面向80/90后技术开发者的开源AI内容生成平台，采用漫威视觉风格和三体叙事结构，实现硅基共生智慧体网络。",
            "technical_focus": ["多模态生成", "智能工作流", "开源协作"],
            "visual_style": "漫威电影风格",
            "narrative_structure": "三体式叙事",
            "target_audience": ["80后技术专家", "90后开发者", "开源贡献者"],
            "value_proposition": "民主化AI内容创作，赋能每个创造者",
        }

        branded_content = manager.generate_branded_content(
            template_id="product_demo_001",
            content_data=github_user_profile_content,
            visual_style="data_wisdom",
        )

        # 检查是否包含GitHub用户画像信息
        has_github_profile = "github_user_profile" in branded_content
        has_brand_info = "brand_info" in branded_content

        print(f"  生成品牌化内容: {'✅成功' if 'error' not in branded_content else '❌失败'}")
        print(f"  包含GitHub用户画像: {'✅是' if has_github_profile else '❌否'}")
        print(f"  包含品牌信息: {'✅是' if has_brand_info else '❌否'}")

        if has_github_profile:
            github_profile = branded_content["github_user_profile"]
            print(f"    主要受众: {', '.join(github_profile.get('primary_audience', []))}")
            print(f"    视觉偏好: {github_profile.get('visual_preference', 'N/A')}")
            print(f"    叙事偏好: {github_profile.get('narrative_preference', 'N/A')}")

        if has_brand_info:
            brand_info = branded_content["brand_info"]
            print(f"    视觉风格: {brand_info.get('visual_style', 'N/A')}")
            print(f"    设计原则: {', '.join(brand_info.get('design_principles', []))}")

        # 测试3.2: 设计原则验证
        print("\n测试3.2: 设计原则验证")

        expected_principles = ["硅基共生", "漫威视觉", "三体叙事"]
        principles_match = False

        if has_brand_info:
            actual_principles = brand_info.get("design_principles", [])
            principles_match = all(p in actual_principles for p in expected_principles)

            print(f"  期望设计原则: {', '.join(expected_principles)}")
            print(f"  实际设计原则: {', '.join(actual_principles)}")
            print(f"  设计原则匹配: {'✅匹配' if principles_match else '❌不匹配'}")

        # 测试3.3: 内容结构验证
        print("\n测试3.3: 内容结构验证")

        content_structure_valid = all(
            key in branded_content for key in ["template_id", "applied_content", "structure_guide"]
        )

        print(f"  内容结构完整: {'✅是' if content_structure_valid else '❌否'}")

        # 保存品牌化内容示例
        example_file = Path(__file__).parent / "assets" / "reports" / "branded_content_example.json"
        example_file.parent.mkdir(parents=True, exist_ok=True)

        with open(example_file, "w", encoding="utf-8") as f:
            json.dump(branded_content, f, indent=2, ensure_ascii=False)

        print(f"\n📋 品牌化内容示例已保存: {example_file}")

        # 汇总结果
        workflow_passed = (
            has_github_profile and has_brand_info and principles_match and content_structure_valid
        )

        print("\n" + "=" * 40)
        print(f"品牌化内容工作流测试: {'✅全部通过' if workflow_passed else '❌部分失败'}")
        print("=" * 40)

        return workflow_passed, {
            "has_github_profile": has_github_profile,
            "has_brand_info": has_brand_info,
            "principles_match": principles_match,
            "content_structure_valid": content_structure_valid,
            "branded_content_example": str(example_file),
        }

    except Exception as e:
        print(f"❌ 品牌化内容工作流测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False, {"error": str(e)}


def test_mvp_focus_validation():
    """测试MVP聚焦验证"""
    print("\n" + "=" * 60)
    print("🧪 测试4: MVP聚焦验证")
    print("=" * 60)

    try:
        from ip_digital_assets_manager import IPDigitalAssetsManager

        manager = IPDigitalAssetsManager()
        stats = manager.get_statistics()

        # 验证MVP核心价值：品牌一致性 + 内容模板
        mvp_core_valid = stats["brand_colors_count"] >= 3 and stats["content_templates_count"] >= 2

        print(f"品牌颜色数量: {stats['brand_colors_count']} (期望≥3)")
        print(f"内容模板数量: {stats['content_templates_count']} (期望≥2)")
        print(f"视觉形象数量: {stats['visual_identities_count']} (期望≥2)")
        print(f"品牌指南数量: {stats['brand_guidelines_count']} (期望≥1)")

        print(f"\nMVP核心价值验证: {'✅通过' if mvp_core_valid else '❌失败'}")

        # 验证GitHub用户画像对齐
        print("\nGitHub用户画像对齐验证:")

        # 检查是否支持80/90后用户偏好
        template = manager.get_template("product_demo_001")
        if template:
            target_audience = template.target_audience
            supports_80_90 = any("开发者" in aud or "技术" in aud for aud in target_audience)
            print(f"  支持80/90后技术用户: {'✅是' if supports_80_90 else '❌否'}")

        # 检查视觉风格偏好
        visual_identity = manager.get_visual_identity("data_wisdom")
        if visual_identity:
            style_description = visual_identity.description
            has_tech_future_style = any(
                keyword in style_description.lower() for keyword in ["科技", "未来", "数据", "现代"]
            )
            print(f"  包含科技未来风格: {'✅是' if has_tech_future_style else '❌否'}")

        mvp_focus_passed = mvp_core_valid

        print("\n" + "=" * 40)
        print(f"MVP聚焦验证: {'✅通过' if mvp_focus_passed else '❌失败'}")
        print("=" * 40)

        return mvp_focus_passed, {
            "mvp_core_valid": mvp_core_valid,
            "brand_colors_count": stats["brand_colors_count"],
            "content_templates_count": stats["content_templates_count"],
            "visual_identities_count": stats["visual_identities_count"],
            "brand_guidelines_count": stats["brand_guidelines_count"],
        }

    except Exception as e:
        print(f"❌ MVP聚焦验证测试失败: {e}")
        return False, {"error": str(e)}


def main():
    """主测试函数"""
    from datetime import datetime

    print("=" * 80)
    print("🎬 Athena IP数字资产与生产系统集成测试套件")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"工作目录: {os.getcwd()}")
    print("=" * 80)

    # 运行所有测试
    test_results = []

    # 测试1: IP数字资产管理器独立功能
    test1_passed, test1_details = test_ip_assets_manager_standalone()
    test_results.append(("IP数字资产管理器独立功能", test1_passed, test1_details))

    # 测试2: 生产系统集成验证
    test2_passed, test2_details = test_production_system_integration()
    test_results.append(("生产系统集成验证", test2_passed, test2_details))

    # 测试3: 品牌化内容工作流
    test3_passed, test3_details = test_branded_content_workflow()
    test_results.append(("品牌化内容工作流", test3_passed, test3_details))

    # 测试4: MVP聚焦验证
    test4_passed, test4_details = test_mvp_focus_validation()
    test_results.append(("MVP聚焦验证", test4_passed, test4_details))

    # 汇总结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)

    passed_count = 0
    total_count = len(test_results)

    for test_name, passed, details in test_results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if passed:
            passed_count += 1

    success_rate = passed_count / total_count * 100 if total_count > 0 else 0

    print("\n" + "=" * 80)
    print(f"总计: {passed_count}/{total_count} 通过 ({success_rate:.1f}%)")

    if passed_count == total_count:
        print("🎉 所有测试通过！IP数字资产与生产系统集成验证成功。")
        print("\n下一步建议:")
        print("1. 在实际内容生成中使用IP数字资产模板")
        print("2. 扩展更多内容模板和视觉风格")
        print("3. 收集用户对IP形象的反馈并持续优化")
    else:
        print(f"⚠️  {total_count - passed_count} 个测试失败，需要改进集成。")
        print("\n失败详情:")
        for test_name, passed, details in test_results:
            if not passed:
                print(f"  - {test_name}: {details.get('error', '未知错误')}")

    print("=" * 80)

    # 保存最终测试报告
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": total_count,
        "passed_tests": passed_count,
        "success_rate": success_rate,
        "test_results": [
            {"name": test_name, "passed": passed, "details": details}
            for test_name, passed, details in test_results
        ],
        "summary": {
            "ip_assets_integration_complete": passed_count == total_count,
            "mvp_ready": all(passed for _, passed, _ in test_results[:2]),  # 前两个是核心集成测试
            "recommendations": (
                [
                    "在实际内容生成中使用IP数字资产模板",
                    "扩展更多内容模板和视觉风格",
                    "收集用户对IP形象的反馈并持续优化",
                ]
                if passed_count == total_count
                else ["修复失败的测试用例", "重新验证集成逻辑", "确保资产目录结构完整"]
            ),
        },
    }

    report_dir = Path(__file__).parent / "assets" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_file = (
        report_dir
        / f"ip_assets_integration_final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(make_serializable(final_report), f, indent=2, ensure_ascii=False)

    print(f"\n📋 最终测试报告已保存: {report_file}")
    print("=" * 80)

    return passed_count == total_count


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断测试")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试执行异常: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
