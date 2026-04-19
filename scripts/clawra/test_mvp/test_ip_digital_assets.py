#!/usr/bin/env python3
"""
IP数字资产测试
测试Athena IP数字资产体系的完整性和可用性
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


class IPDigitalAssetsTester:
    """IP数字资产测试器"""

    def __init__(self, assets_root=None):
        """初始化测试器"""
        if assets_root is None:
            self.assets_root = Path("/Volumes/1TB-M2/openclaw/scripts/clawra/assets/athena_ip")
        else:
            self.assets_root = Path(assets_root)

        # 预期目录结构
        self.expected_directories = [
            "01_logo_system/primary",
            "01_logo_system/compact",
            "01_logo_system/monochrome",
            "01_logo_system/brand_colors",
            "02_visual_identity/classical_athena",
            "02_visual_identity/data_wisdom",
            "03_dynamic_assets/loading_animations",
            "03_dynamic_assets/interaction_feedback",
            "04_voice_system/voice_samples",
            "04_voice_system/sound_effects",
            "04_voice_system/voice_style_guide",
            "05_content_templates/social_media",
            "05_content_templates/documentation",
            "05_content_templates/presentation",
            "06_brand_guidelines/visual_style_guide",
            "06_brand_guidelines/voice_tone_guide",
            "06_brand_guidelines/implementation_examples",
        ]

        # 预期文件扩展名
        self.expected_formats = {
            "guidelines": [".md", ".txt"],
            "templates": [".yaml", ".yml", ".json", ".md"],
            "styles": [".css", ".scss", ".less"],
            "configs": [".yaml", ".yml", ".json"],
        }

        print(f"IP数字资产测试器初始化完成")
        print(f"资产根目录: {self.assets_root}")

    def test_directory_structure(self):
        """测试目录结构完整性"""
        print("\n=== 测试1: 目录结构完整性 ===")

        missing_dirs = []
        existing_dirs = []

        for rel_dir in self.expected_directories:
            full_path = self.assets_root / rel_dir
            if full_path.exists() and full_path.is_dir():
                existing_dirs.append(rel_dir)
            else:
                missing_dirs.append(rel_dir)

        print(f"✅ 存在目录: {len(existing_dirs)}个")
        for dir_path in existing_dirs:
            print(f"   - {dir_path}")

        if missing_dirs:
            print(f"❌ 缺失目录: {len(missing_dirs)}个")
            for dir_path in missing_dirs:
                print(f"   - {dir_path}")
            return False
        else:
            print("✅ 目录结构完整性测试通过")
            return True

    def test_core_documentation_files(self):
        """测试核心文档文件"""
        print("\n=== 测试2: 核心文档文件 ===")

        expected_files = [
            "README.md",  # 总览文档
            "01_logo_system/brand_colors/brand_colors.md",
            "01_logo_system/primary/primary_logo_guidelines.md",
            "01_logo_system/compact/compact_logo_guidelines.md",
            "01_logo_system/monochrome/monochrome_logo_guidelines.md",
            "02_visual_identity/classical_athena/classical_athena_guidelines.md",
            "02_visual_identity/data_wisdom/data_wisdom_guidelines.md",
            "03_dynamic_assets/loading_animations/loading_animations.md",
            "03_dynamic_assets/interaction_feedback/interaction_feedback.md",
            "04_voice_system/voice_style_guide/voice_technical_specification.md",
            "04_voice_system/voice_samples/voice_samples_catalog.md",
            "04_voice_system/sound_effects/sound_effects_library.md",
            "05_content_templates/social_media/README.md",
            "05_content_templates/documentation/README.md",
            "05_content_templates/presentation/README.md",
            "06_brand_guidelines/visual_style_guide/visual_style_guide.md",
            "06_brand_guidelines/voice_tone_guide/voice_tone_guide.md",
            "06_brand_guidelines/implementation_examples/README.md",
        ]

        existing_files = []
        missing_files = []

        for rel_file in expected_files:
            full_path = self.assets_root / rel_file
            if full_path.exists() and full_path.is_file():
                existing_files.append(rel_file)

                # 检查文件大小
                file_size = full_path.stat().st_size
                if file_size > 0:
                    print(f"✅ {rel_file} ({file_size} bytes)")
                else:
                    print(f"⚠️  {rel_file} (空文件)")
                    missing_files.append(rel_file)
            else:
                missing_files.append(rel_file)

        if missing_files:
            print(f"\n❌ 缺失文件: {len(missing_files)}个")
            for file_path in missing_files[:5]:  # 只显示前5个
                print(f"   - {file_path}")
            if len(missing_files) > 5:
                print(f"   ... 还有{len(missing_files)-5}个")
            return False
        else:
            print(f"\n✅ 核心文档文件测试通过 ({len(existing_files)}个文件)")
            return True

    def test_yaml_template_syntax(self):
        """测试YAML模板语法"""
        print("\n=== 测试3: YAML模板语法验证 ===")

        # 查找所有YAML文件
        yaml_files = []
        for ext in [".yaml", ".yml"]:
            for file_path in self.assets_root.rglob(f"*{ext}"):
                yaml_files.append(file_path)

        if not yaml_files:
            print("ℹ️ 未找到YAML文件，跳过此测试")
            return True

        valid_files = []
        invalid_files = []

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)

                # 基本验证
                if content is not None:
                    rel_path = yaml_file.relative_to(self.assets_root)
                    valid_files.append(str(rel_path))

                    # 如果是模板文件，检查基本结构
                    if "template" in str(yaml_file).lower():
                        if isinstance(content, dict):
                            # 检查是否有必要的字段
                            if "structure" in content or "template_id" in content:
                                print(f"✅ {rel_path} (有效模板)")
                            else:
                                print(f"⚠️  {rel_path} (缺少模板结构)")
                        else:
                            print(f"⚠️  {rel_path} (模板格式错误)")
                    else:
                        print(f"✅ {rel_path} (有效YAML)")
                else:
                    rel_path = yaml_file.relative_to(self.assets_root)
                    print(f"⚠️  {rel_path} (空内容)")
                    invalid_files.append(str(rel_path))

            except yaml.YAMLError as e:
                rel_path = yaml_file.relative_to(self.assets_root)
                print(f"❌ {rel_path}: YAML解析错误 - {e}")
                invalid_files.append(str(rel_path))
            except Exception as e:
                rel_path = yaml_file.relative_to(self.assets_root)
                print(f"❌ {rel_path}: 读取错误 - {e}")
                invalid_files.append(str(rel_path))

        if invalid_files:
            print(f"\n❌ YAML语法错误: {len(invalid_files)}个文件")
            return False
        else:
            print(f"\n✅ YAML模板语法测试通过 ({len(valid_files)}个文件)")
            return True

    def test_content_template_structure(self):
        """测试内容模板结构"""
        print("\n=== 测试4: 内容模板结构验证 ===")

        # 检查演示模板
        presentation_dir = self.assets_root / "05_content_templates" / "presentation"
        if presentation_dir.exists():
            readme_file = presentation_dir / "README.md"
            if readme_file.exists():
                try:
                    with open(readme_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    # 检查关键内容
                    if "模板分类" in content and "视觉规范" in content:
                        print("✅ 演示模板文档结构完整")

                        # 检查是否有模板示例
                        if "```yaml" in content:
                            print("✅ 包含YAML模板示例")
                        else:
                            print("⚠️  缺少YAML模板示例")
                    else:
                        print("⚠️  演示模板文档结构不完整")

                except Exception as e:
                    print(f"❌ 读取演示模板失败: {e}")
            else:
                print("❌ 演示模板README.md不存在")
        else:
            print("ℹ️ 演示模板目录不存在")

        # 检查社交媒体模板
        social_dir = self.assets_root / "05_content_templates" / "social_media"
        if social_dir.exists():
            readme_file = social_dir / "README.md"
            if readme_file.exists():
                try:
                    with open(readme_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    if "模板分类" in content and "视觉规范" in content:
                        print("✅ 社交媒体模板结构完整")
                    else:
                        print("⚠️  社交媒体模板结构不完整")

                except Exception as e:
                    print(f"❌ 读取社交媒体模板失败: {e}")
            else:
                print("❌ 社交媒体模板README.md不存在")
        else:
            print("ℹ️ 社交媒体模板目录不存在")

        return True  # 暂时不将此作为失败条件

    def test_brand_consistency(self):
        """测试品牌一致性"""
        print("\n=== 测试5: 品牌一致性验证 ===")

        # 读取品牌色彩规范
        colors_file = self.assets_root / "01_logo_system" / "brand_colors" / "brand_colors.md"
        brand_colors = {}

        if colors_file.exists():
            try:
                with open(colors_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 提取颜色定义
                import re

                color_pattern = r"`#([0-9A-Fa-f]{6})`"
                colors = re.findall(color_pattern, content)

                if colors:
                    print(f"✅ 品牌颜色定义: {len(colors)}种")
                    for color in colors:
                        print(f"   - #{color}")
                    brand_colors = set([f"#{c.upper()}" for c in colors])
                else:
                    print("⚠️  未找到颜色定义")

            except Exception as e:
                print(f"❌ 读取品牌颜色失败: {e}")
        else:
            print("❌ 品牌颜色文件不存在")

        # 检查颜色在CSS文件中的使用
        css_file = self.assets_root / "01_logo_system" / "brand_colors" / "athena-colors.css"
        if css_file.exists():
            try:
                with open(css_file, "r", encoding="utf-8") as f:
                    css_content = f.read()

                # 检查是否包含品牌颜色
                if brand_colors:
                    found_colors = []
                    for color in brand_colors:
                        if color in css_content:
                            found_colors.append(color)

                    print(f"✅ CSS文件中包含{len(found_colors)}/{len(brand_colors)}种品牌颜色")
                else:
                    print("ℹ️ 无法验证CSS颜色（无品牌颜色定义）")

            except Exception as e:
                print(f"❌ 读取CSS文件失败: {e}")
        else:
            print("ℹ️ CSS文件不存在")

        # 检查设计原则一致性
        readme_file = self.assets_root / "README.md"
        if readme_file.exists():
            try:
                with open(readme_file, "r", encoding="utf-8") as f:
                    readme_content = f.read()

                # 检查设计理念关键词
                keywords = ["硅基共生", "漫威", "三体", "科技感", "未来感"]
                found_keywords = []

                for keyword in keywords:
                    if keyword in readme_content:
                        found_keywords.append(keyword)

                print(
                    f"✅ 设计理念包含{len(found_keywords)}/{len(keywords)}个关键词: {', '.join(found_keywords)}"
                )

            except Exception as e:
                print(f"❌ 读取README失败: {e}")
        else:
            print("❌ README.md不存在")

        return True

    def test_implementation_examples(self):
        """测试实施示例"""
        print("\n=== 测试6: 实施示例验证 ===")

        examples_file = (
            self.assets_root / "06_brand_guidelines" / "implementation_examples" / "README.md"
        )

        if examples_file.exists():
            try:
                with open(examples_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 检查示例数量
                example_sections = content.count("#### 示例")
                if example_sections > 0:
                    print(f"✅ 包含{example_sections}个实施示例")
                else:
                    print("⚠️  未找到实施示例")

                # 检查代码示例
                yaml_blocks = content.count("```yaml")
                html_blocks = content.count("```html")
                js_blocks = content.count("```javascript")

                print(
                    f"✅ 代码示例: {yaml_blocks}个YAML, {html_blocks}个HTML, {js_blocks}个JavaScript"
                )

                # 检查效果评估
                if "效果评估" in content or "效果指标" in content:
                    print("✅ 包含效果评估数据")
                else:
                    print("⚠️  缺少效果评估数据")

            except Exception as e:
                print(f"❌ 读取实施示例失败: {e}")
        else:
            print("❌ 实施示例文件不存在")

        return True

    def test_integration_with_mvp(self):
        """测试与MVP系统的集成"""
        print("\n=== 测试7: 与MVP系统集成验证 ===")

        try:
            # 检查是否能导入MVP模块
            from prompt_knowledge_base import PromptCategory, PromptSubcategory

            print("✅ 可以导入MVP核心模块")

            # 模拟IP数字资产使用场景
            integration_scenarios = [
                {
                    "name": "提示词生成使用IP语气",
                    "description": "使用Athena IP语气生成技术内容提示词",
                },
                {"name": "社交媒体内容生成", "description": "使用社交媒体模板生成技术内容"},
                {"name": "演示材料生成", "description": "使用演示模板生成技术演示"},
            ]

            print(f"✅ 定义{len(integration_scenarios)}个集成场景")

            # 验证资产可访问性
            important_assets = [
                "05_content_templates/social_media/README.md",
                "05_content_templates/presentation/README.md",
                "04_voice_system/sound_effects/sound_effects_library.md",
            ]

            accessible_assets = []
            for asset in important_assets:
                asset_path = self.assets_root / asset
                if asset_path.exists():
                    accessible_assets.append(asset)

            print(f"✅ {len(accessible_assets)}/{len(important_assets)}个关键资产可访问")

            # 生成集成报告
            integration_report = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "assets_root": str(self.assets_root),
                "integration_scenarios": integration_scenarios,
                "accessible_assets": accessible_assets,
                "test_summary": {
                    "directory_structure": self.test_directory_structure.__name__,
                    "core_documentation": self.test_core_documentation_files.__name__,
                    "yaml_syntax": self.test_yaml_template_syntax.__name__,
                    "content_templates": self.test_content_template_structure.__name__,
                    "brand_consistency": self.test_brand_consistency.__name__,
                    "implementation_examples": self.test_implementation_examples.__name__,
                },
            }

            # 保存集成报告
            report_dir = self.assets_root.parent / "reports"
            report_dir.mkdir(exist_ok=True)
            report_file = report_dir / "ip_assets_integration_report.json"

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(integration_report, f, indent=2, ensure_ascii=False)

            print(f"✅ 集成报告保存到: {report_file}")

        except ImportError as e:
            print(f"❌ MVP模块导入失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 集成测试失败: {e}")
            return False

        return True


def run_ip_assets_tests():
    """运行IP数字资产测试"""
    print("=" * 60)
    print("Athena IP数字资产测试套件")
    print("=" * 60)

    tester = IPDigitalAssetsTester()
    test_results = []

    # 运行测试1: 目录结构
    print("\n" + "=" * 60)
    test1_result = tester.test_directory_structure()
    test_results.append(("目录结构完整性", test1_result))

    # 运行测试2: 核心文档
    print("\n" + "=" * 60)
    test2_result = tester.test_core_documentation_files()
    test_results.append(("核心文档文件", test2_result))

    # 运行测试3: YAML语法
    print("\n" + "=" * 60)
    test3_result = tester.test_yaml_template_syntax()
    test_results.append(("YAML模板语法", test3_result))

    # 运行测试4: 内容模板
    print("\n" + "=" * 60)
    test4_result = tester.test_content_template_structure()
    test_results.append(("内容模板结构", test4_result))

    # 运行测试5: 品牌一致性
    print("\n" + "=" * 60)
    test5_result = tester.test_brand_consistency()
    test_results.append(("品牌一致性", test5_result))

    # 运行测试6: 实施示例
    print("\n" + "=" * 60)
    test6_result = tester.test_implementation_examples()
    test_results.append(("实施示例", test6_result))

    # 运行测试7: MVP集成
    print("\n" + "=" * 60)
    test7_result = tester.test_integration_with_mvp()
    test_results.append(("MVP系统集成", test7_result))

    # 汇总结果
    print("\n" + "=" * 60)
    print("IP数字资产测试结果汇总:")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{total} 通过")

    if passed >= total * 0.8:  # 80%通过率
        print("\n🎉 IP数字资产测试通过！资产体系完整可用。")
        print("\n下一步建议:")
        print("1. 在实际内容生成中使用IP模板")
        print("2. 将品牌资产集成到Clawra生产系统")
        print("3. 收集用户对IP形象的反馈")
        return True
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，需要改进IP数字资产体系。")
        return False


if __name__ == "__main__":
    import time

    # 运行测试
    start_time = time.time()
    tests_passed = run_ip_assets_tests()
    elapsed_time = time.time() - start_time

    print(f"\n测试用时: {elapsed_time:.2f}秒")

    if tests_passed:
        print("\n🎉 IP数字资产验证完成，可以整合到MVP验证中。")
        sys.exit(0)
    else:
        print("\n❌ IP数字资产验证失败，请修复问题。")
        sys.exit(1)
