#!/usr/bin/env python3
"""
测试MAREF实验质量评估集成模块
验证与实验框架的集成效果
"""

import json
import logging
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = "/Volumes/1TB-M2/openclaw"
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "mini-agent"))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from agent.core.experiment_logger import get_experiment_logger

# 导入测试模块
from agent.core.maref_quality_experiment_integration import (
    MarefExperimentQualityAssessor,
    MarefExperimentQualityResult,
    get_maref_experiment_assessor,
)


def test_single_experiment_assessment():
    """测试单个实验评估"""
    print("🧪 测试单个实验评估")
    print("-" * 60)

    try:
        # 获取实验日志器
        experiment_logger = get_experiment_logger()

        # 获取实验记录（选择有output_response的记录）
        records = experiment_logger.storage.get_experiment_records(
            experiment_id="coding_plan_deepseek_coder_ab", limit=10
        )

        # 找到有output_response的记录
        test_record = None
        for record in records:
            if record.output_response and len(record.output_response) > 100:
                test_record = record
                break

        if not test_record:
            print("❌ 未找到有output_response的实验记录")
            return False

        print(f"📝 测试记录:")
        print(f"   实验ID: {test_record.experiment_id}")
        print(f"   请求ID: {test_record.request_id}")
        print(f"   分组: {test_record.group_name}")
        print(f"   任务类型: {test_record.task_kind}")
        print(f"   输出长度: {len(test_record.output_response)} 字符")
        print(f"   当前质量评分: {test_record.quality_score}")
        print()

        # 创建评估器
        assessor = get_maref_experiment_assessor()

        # 评估单个实验
        print("🔍 开始MAREF质量评估...")
        result = assessor.assess_experiment_by_request_id(test_record.request_id)

        if not result:
            print("❌ 评估失败")
            return False

        print("✅ 评估成功!")
        print()
        print(f"📊 评估结果:")
        print(f"   总体评分: {result.quality_score:.2f}/10")
        print(f"   评估器: {result.quality_assessor}")
        print(f"   评估时间: {result.assessed_at}")

        if result.maref_summary:
            print(f"   MAREF摘要:")
            print(f"     六十四卦索引: {result.maref_summary.get('hexagram_index')}")
            print(f"     格雷状态码: {result.maref_summary.get('gray_state_code')}")

            suggestions = result.maref_summary.get("improvement_suggestions", [])
            if suggestions:
                print(f"     改进建议: {suggestions[0]}")

        # 检查质量分解
        if result.quality_breakdown:
            print(f"   质量分解:")
            for dim, score in list(result.quality_breakdown.items())[:3]:  # 显示前3个维度
                print(f"     {dim}: {score:.2f}")
            if len(result.quality_breakdown) > 3:
                print(f"     ... 还有 {len(result.quality_breakdown) - 3} 个维度")

        # 测试记录到数据库
        print()
        print("💾 测试记录到数据库...")
        success = assessor.assess_and_record_experiment_quality(test_record.request_id)

        if success:
            print("✅ 记录到数据库成功!")

            # 验证记录
            updated_records = experiment_logger.storage.get_experiment_records(
                request_id=test_record.request_id, limit=1
            )
            if updated_records and updated_records[0].quality_score is not None:
                print(f"✅ 数据库验证通过 - 质量评分已更新: {updated_records[0].quality_score:.2f}")
                return True
            else:
                print("❌ 数据库验证失败 - 质量评分未更新")
                return False
        else:
            print("❌ 记录到数据库失败")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_batch_assessment():
    """测试批量评估"""
    print("\n🧪 测试批量评估")
    print("-" * 60)

    try:
        assessor = get_maref_experiment_assessor()

        print("📊 开始批量评估...")
        results = assessor.batch_assess_experiments(
            experiment_id="coding_plan_deepseek_coder_ab",
            limit=5,  # 只评估5个记录，避免耗时过长
            skip_assessed=True,
        )

        print(f"✅ 批量评估完成!")
        print()
        print(f"📈 统计结果:")
        print(f"   总计记录: {results.get('total_records', 0)}")
        print(f"   需要评估: {results.get('records_to_assess', 0)}")
        print(f"   评估成功: {results.get('assessed', 0)}")
        print(f"   评估失败: {results.get('failed', 0)}")

        # 显示评估结果
        if results.get("results"):
            print()
            print(f"📝 评估结果示例:")
            for i, r in enumerate(results["results"][:3]):
                print(f"   {i+1}. {r['request_id']}: {r['quality_score']:.2f}/10")

        return True

    except Exception as e:
        print(f"❌ 批量评估失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_quality_cost_report():
    """测试质量-成本分析报告"""
    print("\n🧪 测试质量-成本分析报告")
    print("-" * 60)

    try:
        assessor = get_maref_experiment_assessor()

        print("📈 生成质量-成本分析报告...")
        report = assessor.generate_quality_cost_report(
            experiment_id="coding_plan_deepseek_coder_ab"
        )

        if "error" in report:
            print(f"❌ 报告生成失败: {report['error']}")
            return False

        print("✅ 报告生成成功!")
        print()
        print(f"📋 报告概览:")
        print(f"   实验ID: {report.get('experiment_id')}")
        print(f"   分析时间: {report.get('analysis_time')}")

        # 显示组统计
        if "groups" in report:
            print()
            print(f"📊 组统计:")
            for group_name, stats in report["groups"].items():
                print(f"   {group_name.upper()}组:")
                print(f"     记录数: {stats['record_count']}")
                print(f"     平均质量: {stats['quality_score']['mean']:.2f}")
                print(f"     平均成本: {stats['cost']['mean']:.4f}")
                if stats["cost"]["total"] > 0:
                    print(f"     总成本: ${stats['cost']['total']:.6f}")
                print(f"     平均QCR: {stats['quality_cost_ratio']['mean']:.2f}")
                print()

        # 显示比较结果
        if "comparison" in report and report["comparison"]:
            comp = report["comparison"]
            print(f"📊 组间比较:")

            if "quality_difference" in comp:
                qd = comp["quality_difference"]
                print(
                    f"   质量差异: {qd['absolute']:.2f} ({qd['percent']:.1f}%) - {qd['interpretation']}"
                )

            if "cost_difference" in comp:
                cd = comp["cost_difference"]
                print(
                    f"   成本差异: ${cd['absolute']:.6f} ({cd['percent']:.1f}%) - {cd['interpretation']}"
                )

            if "quality_cost_ratio_difference" in comp:
                qcrd = comp["quality_cost_ratio_difference"]
                print(
                    f"   质量成本比差异: {qcrd['absolute']:.2f} ({qcrd['percent']:.1f}%) - {qcrd['interpretation']}"
                )

        # 显示建议
        if "recommendations" in report and report["recommendations"]:
            print()
            print(f"💡 优化建议:")
            for i, rec in enumerate(report["recommendations"]):
                print(f"   {i+1}. [{rec['type'].upper()}] {rec['message']}")
                print(f"      行动: {rec['action']}")
                print()

        return True

    except Exception as e:
        print(f"❌ 报告生成失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_maref_result_serialization():
    """测试MAREF结果序列化"""
    print("\n🧪 测试MAREF结果序列化")
    print("-" * 60)

    try:
        # 创建示例MAREF评估结果
        from agent.core.maref_quality_integration import MarefQualityResult

        # 使用示例代码创建评估
        sample_code = '''
def calculate_fibonacci(n: int) -> int:
    """计算斐波那契数列第n项"""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
'''

        # 获取MAREF评估器
        from agent.core.maref_quality_integration import get_maref_quality_evaluator

        maref_evaluator = get_maref_quality_evaluator(enable_advanced_features=True)

        # 评估代码
        maref_result = maref_evaluator.assess_code_quality(
            code=sample_code, context={"task_type": "algorithm_implementation", "difficulty": 3}
        )

        # 转换为实验质量结果
        experiment_result = MarefExperimentQualityResult.from_maref_result(
            maref_result=maref_result,
            request_id="test_request_001",
            experiment_id="test_experiment",
            context={"test": True},
        )

        print("✅ MAREF结果序列化测试:")
        print(f"   总体评分: {experiment_result.quality_score:.2f}")
        print(f"   评估器类型: {experiment_result.quality_assessor}")
        print(f"   质量分解维度数: {len(experiment_result.quality_breakdown)}")
        print(f"   MAREF摘要: {experiment_result.maref_summary.get('overall_score', 'N/A')}")

        # 测试转换为实验格式
        experiment_format = experiment_result.to_experiment_format()
        print(f"   实验格式转换: 成功 (包含 {len(experiment_format)} 个字段)")

        # 验证JSON序列化
        import json

        json_str = json.dumps(experiment_format, ensure_ascii=False, indent=2)
        print(f"   JSON序列化: 成功 ({len(json_str)} 字符)")

        return True

    except Exception as e:
        print(f"❌ 序列化测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 MAREF实验质量评估集成测试")
    print("=" * 70)

    # 运行测试
    tests = [
        ("单个实验评估", test_single_experiment_assessment),
        ("批量评估", test_batch_assessment),
        ("质量-成本分析报告", test_quality_cost_report),
        ("MAREF结果序列化", test_maref_result_serialization),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n▶️  开始测试: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append((test_name, False))

    # 显示测试结果
    print("\n" + "=" * 70)
    print("📊 测试结果汇总")
    print("-" * 70)

    all_passed = True
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {test_name}: {status}")
        if not success:
            all_passed = False

    print("-" * 70)
    if all_passed:
        print("🎉 所有测试通过！MAREF实验质量评估集成成功！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查日志和实现")
        return 1


if __name__ == "__main__":
    sys.exit(main())
