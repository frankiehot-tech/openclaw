#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Athena IP形象反馈模拟脚本
模拟不同用户分段对Athena IP形象的反馈，演示完整的反馈收集和分析工作流

功能：
1. 模拟多个用户分段的调查响应
2. 生成模拟调查数据
3. 分析调查结果
4. 生成优化建议
5. 展示持续优化循环

版本: 1.0.0
创建时间: 2026-04-16
"""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加路径
sys.path.append(str(Path(__file__).parent))

from ip_feedback_system import IPFeedbackSystem
from ip_image_feedback_survey import (
    IPImageFeedbackSurvey,
    SurveyDimension,
    SurveyResponse,
    UserSegment,
)


def create_simulated_responses(feedback_system, survey_system, num_responses=10):
    """
    创建模拟调查响应

    Args:
        feedback_system: IP反馈系统实例
        survey_system: IP形象调查系统实例
        num_responses: 模拟响应数量

    Returns:
        模拟响应列表
    """
    print(f"📊 创建{num_responses}个模拟调查响应...")

    # 用户分段分布
    segments = [
        (UserSegment.GEN_80, 0.35),  # 80后: 35%
        (UserSegment.GEN_90, 0.35),  # 90后: 35%
        (UserSegment.GEN_70, 0.15),  # 70后: 15%
        (UserSegment.GEN_10, 0.10),  # 10后: 10%
        (UserSegment.OTHER, 0.05),  # 其他: 5%
    ]

    # 各维度的基准分数（基于分段有差异）
    base_scores = {
        UserSegment.GEN_80: {
            SurveyDimension.VISUAL_STYLE: 4.2,  # 80后喜欢漫威风格
            SurveyDimension.NARRATIVE_STYLE: 4.0,  # 熟悉三体
            SurveyDimension.THEME_ALIGNMENT: 4.1,  # 理解硅基共生
            SurveyDimension.AUDIENCE_FIT: 4.3,  # 高度匹配
            SurveyDimension.EMOTIONAL_IMPACT: 3.8,  # 有一定情感共鸣
            SurveyDimension.OVERALL_IMPRESSION: 4.1,  # 整体正面
        },
        UserSegment.GEN_90: {
            SurveyDimension.VISUAL_STYLE: 4.5,  # 90后非常喜欢漫威
            SurveyDimension.NARRATIVE_STYLE: 4.2,  # 喜欢科幻
            SurveyDimension.THEME_ALIGNMENT: 4.0,  # 理解主题
            SurveyDimension.AUDIENCE_FIT: 4.4,  # 高度匹配
            SurveyDimension.EMOTIONAL_IMPACT: 4.1,  # 较强情感共鸣
            SurveyDimension.OVERALL_IMPRESSION: 4.3,  # 整体非常正面
        },
        UserSegment.GEN_70: {
            SurveyDimension.VISUAL_STYLE: 3.5,  # 70后可能觉得太花哨
            SurveyDimension.NARRATIVE_STYLE: 3.8,  # 欣赏深度叙事
            SurveyDimension.THEME_ALIGNMENT: 4.2,  # 理解深度主题
            SurveyDimension.AUDIENCE_FIT: 3.2,  # 匹配度一般
            SurveyDimension.EMOTIONAL_IMPACT: 3.5,  # 共鸣一般
            SurveyDimension.OVERALL_IMPRESSION: 3.7,  # 整体中性偏正面
        },
        UserSegment.GEN_10: {
            SurveyDimension.VISUAL_STYLE: 4.8,  # 10后超喜欢炫酷风格
            SurveyDimension.NARRATIVE_STYLE: 3.5,  # 可能觉得三体太深奥
            SurveyDimension.THEME_ALIGNMENT: 3.0,  # 对主题理解有限
            SurveyDimension.AUDIENCE_FIT: 4.6,  # 非常匹配炫酷风格
            SurveyDimension.EMOTIONAL_IMPACT: 4.5,  # 强情感共鸣
            SurveyDimension.OVERALL_IMPRESSION: 4.3,  # 整体非常正面
        },
        UserSegment.OTHER: {
            SurveyDimension.VISUAL_STYLE: 3.8,  # 其他用户中等评价
            SurveyDimension.NARRATIVE_STYLE: 3.6,
            SurveyDimension.THEME_ALIGNMENT: 3.7,
            SurveyDimension.AUDIENCE_FIT: 3.5,
            SurveyDimension.EMOTIONAL_IMPACT: 3.6,
            SurveyDimension.OVERALL_IMPRESSION: 3.7,
        },
    }

    simulated_responses = []

    for i in range(num_responses):
        # 随机选择用户分段（按分布）
        rand_val = random.random()
        cumulative = 0
        selected_segment = UserSegment.GEN_80
        for segment, prob in segments:
            cumulative += prob
            if rand_val <= cumulative:
                selected_segment = segment
                break

        # 创建响应ID
        response_id = f"simulated_{datetime.now().strftime('%Y%m%d')}_{i+1:03d}"

        # 生成答案（基于基准分数加随机波动）
        answers = {}
        comments = {}

        # 获取调查问题
        survey_questions = survey_system.survey_questions

        for question in survey_questions:
            base_score = base_scores[selected_segment][question.dimension]
            # 添加随机波动（-0.5到+0.5）
            score = max(1, min(5, round(base_score + random.uniform(-0.5, 0.5))))
            answers[question.question_id] = score

            # 30%的概率添加评论
            if random.random() < 0.3:
                if score >= 4:
                    comments[question.question_id] = random.choice(
                        [f"这个维度很棒！", f"非常满意，继续保持", f"这正是我期待的"]
                    )
                elif score <= 2:
                    comments[question.question_id] = random.choice(
                        [f"这个方面需要改进", f"感觉还可以更好", f"希望能看到更多变化"]
                    )

        # 创建调查响应
        response = SurveyResponse(
            response_id=response_id,
            user_segment=selected_segment,
            timestamp=datetime.now() - timedelta(days=random.randint(0, 30)),
            answers=answers,
            comments=comments,
            metadata={"simulated": True, "iteration": i + 1},
        )

        simulated_responses.append(response)

        # 存储到调查系统（模拟）
        survey_system.survey_responses.append(response)

        # 转换为反馈条目并存储到反馈系统
        survey_system._store_response_as_feedback(response)

    print(f"✅ 成功创建{len(simulated_responses)}个模拟响应")
    print(f"  用户分段分布:")
    segment_counts = {}
    for resp in simulated_responses:
        segment_counts[resp.user_segment.value] = segment_counts.get(resp.user_segment.value, 0) + 1

    for segment, count in segment_counts.items():
        print(f"    {segment}: {count}个 ({count/len(simulated_responses)*100:.1f}%)")

    return simulated_responses


def analyze_simulated_data(survey_system):
    """分析模拟调查数据"""
    print("\n" + "=" * 60)
    print("🔍 分析模拟调查数据")
    print("=" * 60)

    # 分析最近30天的数据
    analysis = survey_system.analyze_survey_responses(days=30)

    if not analysis:
        print("⚠️ 没有可分析的数据")
        return None

    print(f"📈 分析完成，共 {analysis.total_responses} 份响应")
    print(f"  完成率: {analysis.completion_rate:.1%}")

    print("\n📊 各维度得分:")
    for dimension, score in analysis.dimension_scores.items():
        print(f"  {dimension.value}: {score:.2f}/5")

    print("\n👥 用户分段分析:")
    for segment, segment_scores in analysis.segment_breakdown.items():
        print(f"  {segment.value}:")
        for dimension, score in segment_scores.items():
            print(f"    {dimension.value}: {score:.2f}/5")

    print("\n💡 关键洞察:")
    for i, insight in enumerate(analysis.key_insights, 1):
        print(f"  {i}. {insight}")

    print("\n🎯 优化建议:")
    for i, recommendation in enumerate(analysis.recommendations, 1):
        print(f"  {i}. {recommendation}")

    return analysis


def generate_optimization_report(survey_system, analysis):
    """生成优化报告"""
    print("\n" + "=" * 60)
    print("📋 生成优化报告")
    print("=" * 60)

    report = survey_system.generate_survey_report(analysis)

    if not report:
        print("⚠️ 报告生成失败")
        return None

    print(f"📄 报告生成成功:")
    print(f"  报告ID: {report.get('report_id', '未知')}")
    print(f"  生成时间: {report.get('generated_at', '未知')}")
    print(f"  分析期间: {report.get('analysis_period_days', '未知')}天")
    print(f"  关键发现: {len(report.get('key_findings', []))}条")
    print(f"  优化建议: {len(report.get('optimization_recommendations', []))}条")
    print(f"  优先级行动: {len(report.get('priority_actions', []))}条")

    # 保存报告
    report_file = survey_system.save_survey_report(report)
    if report_file:
        print(f"💾 报告已保存到: {report_file}")

    return report


def demonstrate_feedback_loop():
    """演示完整的反馈循环"""
    print("=" * 60)
    print("🔄 Athena IP形象反馈循环演示")
    print("=" * 60)

    # 初始化反馈系统
    print("\n1️⃣ 初始化反馈系统...")
    feedback_system = IPFeedbackSystem()
    print("✅ IP反馈系统初始化成功")

    # 初始化调查系统
    print("\n2️⃣ 初始化调查系统...")
    survey_system = IPImageFeedbackSurvey(feedback_system=feedback_system)
    print("✅ IP形象调查系统初始化成功")

    # 创建模拟响应
    print("\n3️⃣ 创建模拟用户响应...")
    responses = create_simulated_responses(feedback_system, survey_system, num_responses=15)

    # 分析数据
    print("\n4️⃣ 分析调查数据...")
    analysis = analyze_simulated_data(survey_system)

    # 生成优化报告
    print("\n5️⃣ 生成优化报告...")
    report = generate_optimization_report(survey_system, analysis)

    # 展示反馈循环
    print("\n" + "=" * 60)
    print("🎉 反馈循环演示完成")
    print("=" * 60)
    print("\n📋 演示总结:")
    print(f"  • 模拟用户响应: {len(responses)}个")
    print(f"  • 分析维度: {len(analysis.dimension_scores if analysis else [])}个")
    print(
        f"  • 生成建议: {len(report.get('optimization_recommendations', []) if report else [])}条"
    )

    print("\n🔄 持续优化流程:")
    print("  1. 收集用户反馈 → 2. 分析数据 → 3. 生成建议 → 4. 实施优化 → 5. 重新收集反馈")

    print("\n🚀 下一步行动建议:")
    print("  1. 在实际用户中运行IP形象调查")
    print("  2. 基于真实数据优化IP形象设计")
    print("  3. 定期运行反馈循环（建议每月一次）")
    print("  4. 监控优化效果并迭代改进")

    return {
        "responses_count": len(responses),
        "analysis_available": analysis is not None,
        "report_generated": report is not None,
        "feedback_system": feedback_system,
        "survey_system": survey_system,
    }


def main():
    """主函数"""
    try:
        results = demonstrate_feedback_loop()

        # 验证反馈系统数据
        print("\n" + "=" * 60)
        print("✅ 验证反馈系统数据")
        print("=" * 60)

        feedback_system = results["feedback_system"]
        stats = feedback_system.get_feedback_statistics()

        print(f"📊 反馈系统统计:")
        print(f"  总反馈数: {stats.get('total_feedbacks', 0)}")
        print(f"  平均评分: {stats.get('average_rating', 'N/A')}")
        print(f"  IP形象反馈数: {stats.get('ip_image_feedbacks', 0)}")

        # 验证调查系统数据
        survey_system = results["survey_system"]
        print(f"\n📋 调查系统统计:")
        print(f"  调查响应数: {len(survey_system.survey_responses)}")

        return 0

    except Exception as e:
        print(f"❌ 演示执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
