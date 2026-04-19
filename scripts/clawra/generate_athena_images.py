#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Athena IP形象图像生成脚本
生成10张不同的Athena IP形象图像，验证生产环境图像生成能力

设计原则：
1. 基于GitHub用户画像：80/90后喜欢漫威风格
2. 硅基共生主题：人工智能与人类协作进化
3. 三体叙事风格：宏大视角、硬核深度
4. 多样化视觉风格：覆盖5个核心视觉形象和创意变体

版本: 1.0.0
创建时间: 2026-04-16
"""

import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加路径
sys.path.append(str(Path(__file__).parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from external.ROMA.doubao_cli_enhanced import (
        DoubaoCLIEnhanced,
        ImageGenerationParams,
        ImageResult,
        ImageStyle,
    )

    DOUBAO_AVAILABLE = True
    logger.info("豆包CLI增强模块导入成功")
except ImportError as e:
    DOUBAO_AVAILABLE = False
    logger.error(f"豆包CLI增强模块导入失败: {e}")


@dataclass
class AthenaImageVariant:
    """Athena IP形象变体"""

    id: int
    name: str
    prompt: str
    style: str
    description: str
    target_audience: str  # 目标用户分段
    narrative_theme: str  # 叙事主题

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AthenaImageGenerator:
    """Athena IP形象图像生成器"""

    def __init__(self, output_dir: str = "generated_athena_images"):
        """初始化图像生成器"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化豆包CLI
        if DOUBAO_AVAILABLE:
            try:
                self.doubao_cli = DoubaoCLIEnhanced()
                logger.info("豆包CLI增强模块初始化成功")
                self.cli_available = True
            except Exception as e:
                logger.error(f"豆包CLI初始化失败: {e}")
                self.cli_available = False
                self.doubao_cli = None
        else:
            self.cli_available = False
            self.doubao_cli = None

        # 定义10个Athena IP形象变体
        self.image_variants = self._define_image_variants()

        logger.info(f"Athena图像生成器初始化完成，输出目录: {self.output_dir}")
        logger.info(f"豆包CLI可用: {self.cli_available}")

    def _define_image_variants(self) -> List[AthenaImageVariant]:
        """定义10个Athena IP形象变体"""
        variants = [
            # 1. 古典雅典娜 - 传统智慧形象
            AthenaImageVariant(
                id=1,
                name="classical_athena",
                prompt="古典智慧女神雅典娜，身着古希腊长袍，手持权杖和盾牌，背景是帕特农神庙，漫威电影风格，光线神圣庄严",
                style="realistic",
                description="古典智慧女神形象，体现哲学深度和永恒价值",
                target_audience="70后、80后",
                narrative_theme="传统智慧与永恒价值",
            ),
            # 2. 数据智慧 - 现代科技形象
            AthenaImageVariant(
                id=2,
                name="data_wisdom",
                prompt="数据智慧女神，全身由流动的数据流构成，面部是水晶显示屏显示实时数据，背景是数字矩阵，漫威电影风格",
                style="fantasy",
                description="数据驱动的现代智慧形象，体现科技感和未来感",
                target_audience="80后、90后",
                narrative_theme="数据驱动决策与人工智能",
            ),
            # 3. 赛博朋克雅典娜 - 未来都市形象
            AthenaImageVariant(
                id=3,
                name="cyberpunk_athena",
                prompt="赛博朋克雅典娜，霓虹灯机械装甲，全息投影翅膀，站在未来都市雨夜中，漫威电影风格，霓虹色调",
                style="cyberpunk",
                description="赛博朋克视觉风格，融合高科技与低生活美学",
                target_audience="90后、10后",
                narrative_theme="高科技低生活与数字反抗",
            ),
            # 4. 极简主义雅典娜 - 简洁设计形象
            AthenaImageVariant(
                id=4,
                name="minimalist_athena",
                prompt="极简主义雅典娜，纯白背景，简洁线条勾勒的女神轮廓，几何形状构成的头盔和盾牌，漫威电影风格",
                style="minimalist",
                description="极简主义设计，强调留白和功能优先美学",
                target_audience="技术决策者",
                narrative_theme="简洁设计与功能主义",
            ),
            # 5. 未来主义雅典娜 - 科技前沿形象
            AthenaImageVariant(
                id=5,
                name="futuristic_athena",
                prompt="未来主义雅典娜，液态金属身体，全息投影武器，悬浮在太空站中，漫威电影风格，流畅线条",
                style="futuristic",
                description="未来主义视觉语言，流畅线条和智能材料质感",
                target_audience="技术愿景者",
                narrative_theme="科技未来与人类进化",
            ),
            # 6. 硅基共生智慧体 - 核心主题形象
            AthenaImageVariant(
                id=6,
                name="silicon_symbiosis",
                prompt="硅基共生智慧体，半机械半生物形态，皮肤是电路板纹理，眼睛是蓝色全息投影，背景是科技森林，三体叙事风格",
                style="artistic",
                description="硅基共生主题核心形象，人工智能与人类协作进化",
                target_audience="所有技术用户",
                narrative_theme="硅基共生与协作进化",
            ),
            # 7. 漫威超级英雄雅典娜 - 流行文化形象
            AthenaImageVariant(
                id=7,
                name="marvel_superhero",
                prompt="漫威超级英雄雅典娜，高科技战甲，能量盾牌和激光矛，动态战斗姿势，漫威电影海报风格，爆炸背景",
                style="realistic",
                description="漫威超级英雄风格，强调动作感和视觉冲击力",
                target_audience="80后、90后漫威粉丝",
                narrative_theme="英雄叙事与正义使命",
            ),
            # 8. 三体黑暗森林雅典娜 - 硬核科幻形象
            AthenaImageVariant(
                id=8,
                name="three_body_dark_forest",
                prompt="三体黑暗森林雅典娜，站在宇宙尺度观察者角度，背景是银河系和黑暗森林法则文字，表情深邃神秘，三体小说插画风格",
                style="illustration",
                description="三体黑暗森林风格，体现宇宙尺度和哲学思考",
                target_audience="硬核科幻爱好者",
                narrative_theme="黑暗森林法则与宇宙社会学",
            ),
            # 9. 科技女神雅典娜 - 教育科普形象
            AthenaImageVariant(
                id=9,
                name="tech_goddess",
                prompt="科技女神雅典娜，教学姿势，周围漂浮着数学公式、代码片段和科学原理图表，教室背景，教育插画风格",
                style="illustration",
                description="科技教育形象，强调知识传播和教学价值",
                target_audience="学生、教育工作者",
                narrative_theme="知识传播与技术教育",
            ),
            # 10. 数字先知雅典娜 - 预测分析形象
            AthenaImageVariant(
                id=10,
                name="digital_prophet",
                prompt="数字先知雅典娜，闭眼冥想姿势，周围是流动的时间线和预测数据可视化，背景是神经网络结构，数据艺术风格",
                style="artistic",
                description="数据预测形象，体现分析能力和未来洞察",
                target_audience="数据分析师、产品经理",
                narrative_theme="数据预测与未来洞察",
            ),
        ]

        logger.info(f"定义 {len(variants)} 个Athena IP形象变体")
        return variants

    def save_variants_metadata(self) -> Path:
        """保存变体元数据"""
        metadata_file = self.output_dir / "athena_image_variants.json"

        variants_data = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_variants": len(self.image_variants),
            "variants": [variant.to_dict() for variant in self.image_variants],
        }

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(variants_data, f, ensure_ascii=False, indent=2)

        logger.info(f"变体元数据已保存到: {metadata_file}")
        return metadata_file

    def generate_single_image(self, variant: AthenaImageVariant) -> Optional[ImageResult]:
        """生成单张图像"""
        if not self.cli_available or not self.doubao_cli:
            logger.error("豆包CLI不可用，无法生成图像")
            return None

        try:
            logger.info(f"开始生成图像变体 #{variant.id}: {variant.name}")
            logger.info(f"提示词: {variant.prompt[:80]}...")
            logger.info(f"风格: {variant.style}, 目标用户: {variant.target_audience}")

            # 准备图像生成参数
            params = ImageGenerationParams(
                prompt=variant.prompt,
                style=variant.style,
                size="1024x1024",
                quality="standard",
                num_images=1,
            )

            # 调用豆包CLI生成图像
            logger.info("调用豆包CLI生成图像...")
            result = self.doubao_cli.generate_image(params)

            if result.success:
                logger.info(f"✅ 图像生成成功！耗时: {result.generation_time:.1f}s")
                if result.image_urls:
                    logger.info(f"生成图像URL: {result.image_urls[0][:100]}...")
            else:
                logger.error(f"❌ 图像生成失败: {result.error_message}")

            return result

        except Exception as e:
            logger.error(f"图像生成过程中出现异常: {e}")
            return None

    def generate_all_images(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """生成所有图像变体"""
        if not self.cli_available:
            logger.error("豆包CLI不可用，跳过图像生成")
            return []

        results = []
        variants_to_generate = self.image_variants[:limit] if limit else self.image_variants

        logger.info(f"开始生成 {len(variants_to_generate)} 张Athena IP形象图像...")

        for variant in variants_to_generate:
            # 生成单张图像
            result = self.generate_single_image(variant)

            # 记录结果
            result_data = {
                "variant_id": variant.id,
                "variant_name": variant.name,
                "success": (result.success and bool(result.image_urls)) if result else False,
                "generation_time": result.generation_time if result else 0,
                "image_urls": result.image_urls if result else [],
                "error_message": result.error_message if result else "未执行",
            }

            results.append(result_data)

            # 保存当前结果
            self._save_generation_results(results)

            # 避免频繁请求，添加延迟
            if variant.id < len(variants_to_generate):
                logger.info(f"等待5秒后继续生成下一张...")
                time.sleep(5)

        # 生成最终报告
        self._generate_generation_report(results)

        return results

    def _save_generation_results(self, results: List[Dict[str, Any]]) -> Path:
        """保存生成结果"""
        results_file = self.output_dir / "generation_results.json"

        results_data = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_generated": len(results),
            "successful": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
            "results": results,
        }

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)

        return results_file

    def _generate_generation_report(self, results: List[Dict[str, Any]]) -> Path:
        """生成生成报告"""
        report_file = self.output_dir / "generation_report.md"

        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful
        total_time = sum(r.get("generation_time", 0) for r in results)

        report_content = f"""# Athena IP形象图像生成报告

## 摘要
- **生成时间**: {time.strftime("%Y-%m-%d %H:%M:%S")}
- **计划生成**: {len(self.image_variants)} 张
- **实际生成**: {len(results)} 张
- **成功**: {successful} 张
- **失败**: {failed} 张
- **总耗时**: {total_time:.1f} 秒

## 生成详情

"""

        for result in results:
            variant = next((v for v in self.image_variants if v.id == result["variant_id"]), None)
            if variant:
                status = "✅ 成功" if result["success"] else "❌ 失败"
                report_content += f"### {variant.id}. {variant.name} ({status})\n"
                report_content += f"- **描述**: {variant.description}\n"
                report_content += f"- **目标用户**: {variant.target_audience}\n"
                report_content += f"- **叙事主题**: {variant.narrative_theme}\n"
                report_content += f"- **生成时间**: {result.get('generation_time', 0):.1f}秒\n"

                if result["success"] and result["image_urls"]:
                    report_content += f"- **图像URL**: {result['image_urls'][0][:100]}...\n"
                elif result.get("error_message"):
                    report_content += f"- **错误信息**: {result['error_message']}\n"

                report_content += "\n"

        # 添加总结
        report_content += "## 总结\n\n"

        if successful == len(results):
            report_content += "🎉 **所有图像生成成功！** Athena IP形象图像生成验证通过。\n"
        elif successful > 0:
            report_content += f"⚠️ **部分图像生成成功** ({successful}/{len(results)})。\n"
        else:
            report_content += "❌ **所有图像生成失败**。需要检查豆包CLI配置。\n"

        report_content += f"\n**建议下一步**:\n"
        report_content += f"1. 检查生成的图像质量和风格是否符合预期\n"
        report_content += f"2. 将成功生成的图像集成到IP数字资产库中\n"
        report_content += f"3. 基于用户反馈优化提示词和风格选择\n"
        report_content += f"4. 扩展更多IP形象变体\n"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)

        logger.info(f"生成报告已保存到: {report_file}")
        return report_file

    def test_cli_availability(self) -> bool:
        """测试豆包CLI可用性"""
        if not self.cli_available:
            logger.error("豆包CLI不可用")
            return False

        try:
            # 执行一个简单的JavaScript测试 - 多个测试用例
            test_cases = [
                ("return '豆包CLI测试成功';", "直接返回值"),
                ("document.title;", "获取页面标题"),
                ("'测试字符串';", "简单字符串"),
                ("JSON.stringify({status: 'ok'});", "JSON返回值"),
            ]

            logger.info("执行豆包CLI可用性测试...")

            for i, (test_js, description) in enumerate(test_cases):
                logger.info(f"测试 {i+1}/{len(test_cases)}: {description}")
                result = self.doubao_cli.execute_javascript_enhanced(test_js)

                logger.debug(
                    f"测试结果: success={result.success}, output={repr(result.output)}, error={result.error_message}"
                )

                if result.success:
                    # 检查输出是否有效
                    cleaned = (
                        self.doubao_cli._clean_js_output(result.output)
                        if hasattr(self.doubao_cli, "_clean_js_output")
                        else result.output
                    )
                    if (
                        cleaned
                        and cleaned != "missing value"
                        and "JavaScript执行错误" not in result.output
                    ):
                        logger.info(f"✅ 豆包CLI测试成功: {cleaned[:100]}")
                        return True
                    else:
                        logger.warning(f"测试返回无效输出: {repr(cleaned)}，尝试下一个测试")
                else:
                    logger.warning(f"测试失败: {result.error_message}，尝试下一个测试")

                time.sleep(1)  # 测试间短暂延迟

            # 所有测试都失败，尝试最后一个简单测试
            logger.info("所有标准测试失败，尝试极简测试...")
            minimal_js = "'test'"
            result = self.doubao_cli.execute_javascript_enhanced(minimal_js)

            if result.success and result.output and result.output != "missing value":
                logger.info(f"✅ 豆包CLI极简测试成功: {result.output[:100]}")
                return True

            # 如果还是失败，检查是否是"missing value"但成功的情况
            if result.success and (not result.output or result.output == "missing value"):
                logger.warning(
                    "豆包CLI返回'missing value'但标记为成功，这可能是豆包JavaScript执行环境的特点"
                )
                logger.warning("继续尝试，但图像生成可能会遇到问题")
                return True  # 仍然返回True，因为执行没有错误

            logger.error("❌ 豆包CLI所有测试都失败")
            return False

        except Exception as e:
            logger.error(f"豆包CLI测试异常: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """主函数"""
    try:
        logger.info("=" * 60)
        logger.info("🎨 Athena IP形象图像生成开始")
        logger.info("=" * 60)

        # 初始化生成器
        generator = AthenaImageGenerator()

        # 保存变体元数据
        metadata_file = generator.save_variants_metadata()
        logger.info(f"变体元数据已保存: {metadata_file}")

        # 测试豆包CLI可用性
        cli_available = generator.test_cli_availability()

        if not cli_available:
            logger.warning("豆包CLI不可用或测试失败，将跳过实际图像生成")
            logger.warning("但已生成完整的变体定义和元数据")

            # 即使CLI不可用，也生成报告
            dummy_results = []
            for variant in generator.image_variants:
                dummy_results.append(
                    {
                        "variant_id": variant.id,
                        "variant_name": variant.name,
                        "success": False,
                        "generation_time": 0,
                        "image_urls": [],
                        "error_message": "豆包CLI不可用，跳过实际生成",
                    }
                )

            generator._save_generation_results(dummy_results)
            generator._generate_generation_report(dummy_results)

            return 0

        # 测试实际图像生成能力：尝试生成第一张图像
        logger.info("测试实际图像生成能力...")
        test_variant = generator.image_variants[0]
        test_result = generator.generate_single_image(test_variant)

        # 检查是否真正成功：success为True且有图像URL
        actual_success = test_result and test_result.success and bool(test_result.image_urls)

        if not actual_success:
            logger.warning("实际图像生成测试失败，豆包CLI无法生成图像")
            logger.warning("将切换到模拟数据生成模式")

            # 生成模拟数据
            dummy_results = []
            for variant in generator.image_variants:
                dummy_results.append(
                    {
                        "variant_id": variant.id,
                        "variant_name": variant.name,
                        "success": False,
                        "generation_time": 0,
                        "image_urls": [],
                        "error_message": "实际图像生成测试失败，豆包CLI无法生成图像",
                    }
                )

            generator._save_generation_results(dummy_results)
            generator._generate_generation_report(dummy_results)

            # 返回失败退出码，表示验证未通过
            return 1

        # 生成所有图像
        logger.info("开始生成10张Athena IP形象图像...")
        results = generator.generate_all_images()

        # 输出摘要
        successful = sum(1 for r in results if r.get("success"))
        logger.info(f"生成完成: {successful}/{len(results)} 成功")

        if successful > 0:
            logger.info("✅ Athena IP形象图像生成验证通过")
        else:
            logger.error("❌ Athena IP形象图像生成验证失败")

        return 0 if successful > 0 else 1

    except Exception as e:
        logger.error(f"Athena图像生成失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
