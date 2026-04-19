#!/usr/bin/env python3
"""
验证MAREF成本提取修复效果
测试修复后的成本提取方法是否能正确提取成本数据
"""

import json
import logging
import os
import sys

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
    get_maref_experiment_assessor,
)


def test_cost_extraction():
    """测试成本提取功能"""
    print("🧪 测试成本提取功能")
    print("-" * 60)

    try:
        # 获取实验记录器
        experiment_logger = get_experiment_logger()

        # 获取有质量评分的记录
        records = experiment_logger.storage.get_experiment_records(
            experiment_id="coding_plan_deepseek_coder_ab", min_data_quality="minimal", limit=10
        )

        print(f"📊 获取到 {len(records)} 个实验记录")

        # 创建评估器（测试成本提取方法）
        assessor = MarefExperimentQualityAssessor()

        # 测试提取每条记录的成本
        print("\n📝 成本提取测试:")
        total_records = 0
        successful_extraction = 0

        for i, record in enumerate(records[:5]):  # 测试前5条记录
            print(f"\n  记录 {i+1}: {record.id}")
            print(f"    分组: {record.group_name}")
            print(f"    质量评分: {record.quality_score}")

            # 提取成本
            cost = assessor._extract_cost_from_record(record)
            print(f"    提取成本: {cost}")

            total_records += 1
            if cost is not None:
                successful_extraction += 1
                print(f"    提取成功: {cost:.6f} CNY")
            else:
                print(f"    提取失败")

            # 显示原始cost_info（前200字符）
            if record.cost_info:
                cost_info_str = str(record.cost_info)
                if len(cost_info_str) > 100:
                    print(f"    原始cost_info: {cost_info_str[:100]}...")
                else:
                    print(f"    原始cost_info: {cost_info_str}")

        success_rate = (successful_extraction / total_records) * 100 if total_records > 0 else 0
        print(f"\n✅ 成本提取成功率: {successful_extraction}/{total_records} ({success_rate:.1f}%)")

        return success_rate > 80  # 成功率大于80%视为通过

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_quality_cost_report():
    """测试质量-成本分析报告生成"""
    print("\n🧪 测试质量-成本分析报告生成")
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
        print(f"   总记录数: {report.get('total_records', 0)}")

        # 显示组统计
        if "groups" in report:
            print()
            print(f"📊 组统计:")
            for group_name, stats in report["groups"].items():
                print(f"   {group_name.upper()}组:")
                print(f"     记录数: {stats['record_count']}")

                # 质量统计
                quality_stats = stats.get("quality_score", {})
                print(f"     平均质量: {quality_stats.get('mean', 0):.2f}/10")
                print(f"     质量标准差: {quality_stats.get('std', 0):.2f}")

                # 成本统计
                cost_stats = stats.get("cost", {})
                print(f"     平均成本: {cost_stats.get('mean', 0):.6f} CNY")
                print(f"     成本标准差: {cost_stats.get('std', 0):.6f} CNY")
                if cost_stats.get("total", 0) > 0:
                    print(f"     总成本: {cost_stats.get('total', 0):.6f} CNY")

                # 质量成本比
                qcr_stats = stats.get("quality_cost_ratio", {})
                print(f"     平均QCR: {qcr_stats.get('mean', 0):.2f}")
                print()

        # 显示比较结果
        if "comparison" in report and report["comparison"]:
            comp = report["comparison"]
            print(f"📊 组间比较:")

            if "quality_difference" in comp:
                qd = comp["quality_difference"]
                print(
                    f"   质量差异: {qd.get('absolute', 0):.2f} ({qd.get('percent', 0):.1f}%) - {qd.get('interpretation', 'N/A')}"
                )

            if "cost_difference" in comp:
                cd = comp["cost_difference"]
                print(
                    f"   成本差异: {cd.get('absolute', 0):.6f} CNY ({cd.get('percent', 0):.1f}%) - {cd.get('interpretation', 'N/A')}"
                )

            if "quality_cost_ratio_difference" in comp:
                qcrd = comp["quality_cost_ratio_difference"]
                print(
                    f"   质量成本比差异: {qcrd.get('absolute', 0):.2f} ({qcrd.get('percent', 0):.1f}%) - {qcrd.get('interpretation', 'N/A')}"
                )

        # 显示建议
        if "recommendations" in report and report["recommendations"]:
            print()
            print(f"💡 优化建议:")
            for i, rec in enumerate(report["recommendations"]):
                print(f"   {i+1}. [{rec.get('type', 'info').upper()}] {rec.get('message', 'N/A')}")
                print(f"      行动: {rec.get('action', 'N/A')}")
                print()

        # 验证成本数据不为0
        has_valid_costs = False
        if "groups" in report:
            for group_name, stats in report["groups"].items():
                cost_mean = stats.get("cost", {}).get("mean", 0)
                if cost_mean > 0.000001:  # 大于0.000001 CNY
                    has_valid_costs = True
                    break

        if has_valid_costs:
            print("✅ 验证通过：成本数据已正确提取（不为0）")
            return True
        else:
            print("❌ 验证失败：成本数据仍为0或接近0")
            return False

    except Exception as e:
        print(f"❌ 报告测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 MAREF成本提取修复验证")
    print("=" * 70)

    # 运行测试
    tests = [
        ("成本提取功能", test_cost_extraction),
        ("质量-成本分析报告", test_quality_cost_report),
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
        print("🎉 所有测试通过！成本提取修复成功！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查修复实现")
        return 1


if __name__ == "__main__":
    sys.exit(main())
