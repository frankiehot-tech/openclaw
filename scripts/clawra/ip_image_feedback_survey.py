#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Athena IP形象用户调查系统
针对IP形象的各个维度收集用户反馈，支持持续优化

功能：
1. IP形象多维度调查问卷设计
2. 用户反馈收集界面（CLI和API）
3. 调查结果存储和分析
4. 与IP反馈系统集成
5. 自动生成优化建议

调查维度：
1. 视觉风格评估（漫威电影风格）
2. 叙事风格评估（三体风格）
3. 主题契合度评估（硅基共生）
4. 目标受众匹配度（80/90后，70/10后）
5. 整体印象和情感共鸣

版本: 1.0.0
创建时间: 2026-04-16
"""

import json
import random
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 导入反馈系统
sys.path.append(str(Path(__file__).parent))
from ip_feedback_system import (
    FeedbackEntry,
    FeedbackSource,
    FeedbackType,
    IPFeedbackSystem,
    logger,
)


class SurveyDimension(Enum):
    """调查维度"""

    VISUAL_STYLE = "visual_style"  # 视觉风格
    NARRATIVE_STYLE = "narrative_style"  # 叙事风格
    THEME_ALIGNMENT = "theme_alignment"  # 主题契合度
    AUDIENCE_FIT = "audience_fit"  # 受众匹配度
    EMOTIONAL_IMPACT = "emotional_impact"  # 情感共鸣
    OVERALL_IMPRESSION = "overall_impression"  # 整体印象


class UserSegment(Enum):
    """用户分段"""

    GEN_80 = "80后"  # 80后
    GEN_90 = "90后"  # 90后
    GEN_70 = "70后"  # 70后
    GEN_10 = "10后"  # 10后
    OTHER = "其他"  # 其他


@dataclass
class SurveyQuestion:
    """调查问题"""

    dimension: SurveyDimension
    question_id: str
    question_text: str
    description: str  # 问题描述
    options: List[Tuple[str, int]]  # 选项文本和分值
    weight: float = 1.0  # 权重（1.0为基准）


@dataclass
class SurveyResponse:
    """调查响应"""

    response_id: str
    user_segment: UserSegment
    timestamp: datetime
    answers: Dict[str, int]  # question_id -> 评分（1-5）
    comments: Dict[str, str] = field(default_factory=dict)  # 可选评论
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SurveyAnalysis:
    """调查分析结果"""

    survey_id: str
    total_responses: int
    completion_rate: float  # 完成率
    dimension_scores: Dict[SurveyDimension, float]  # 各维度平均分
    segment_breakdown: Dict[UserSegment, Dict[SurveyDimension, float]]  # 用户分段得分
    key_insights: List[str]  # 关键洞察
    recommendations: List[str]  # 优化建议
    timestamp: datetime


class IPImageFeedbackSurvey:
    """IP形象用户调查系统"""

    def __init__(self, feedback_system: Optional[IPFeedbackSystem] = None):
        """初始化调查系统"""
        self.feedback_system = feedback_system or IPFeedbackSystem()
        self.survey_questions = self._create_survey_questions()
        self.survey_responses = []  # 内存中存储调查响应

    def _create_survey_questions(self) -> List[SurveyQuestion]:
        """创建IP形象调查问卷"""
        questions = [
            # 视觉风格评估（漫威电影风格）
            SurveyQuestion(
                dimension=SurveyDimension.VISUAL_STYLE,
                question_id="visual_marvel",
                question_text="您如何看待Athena的漫威电影风格视觉设计？",
                description="评估IP形象是否成功应用了漫威电影的视觉元素和科技感",
                options=[
                    ("非常不喜欢，不符合漫威风格", 1),
                    ("不太喜欢，视觉冲击力不足", 2),
                    ("一般，有一些漫威元素", 3),
                    ("喜欢，有明显的漫威风格", 4),
                    ("非常喜欢，完美呈现漫威电影质感", 5),
                ],
                weight=1.2,  # 视觉风格权重较高
            ),
            # 叙事风格评估（三体风格）
            SurveyQuestion(
                dimension=SurveyDimension.NARRATIVE_STYLE,
                question_id="narrative_three_body",
                question_text="您认为Athena的三体风格叙事是否成功传达了硅基共生主题？",
                description="评估叙事是否具有三体风格的宏大视角、硬核深度和哲学思考",
                options=[
                    ("完全不符合，叙事平淡", 1),
                    ("有一些三体元素，但深度不足", 2),
                    ("中等水平，有科幻感", 3),
                    ("较好，有三体风格的感觉", 4),
                    ("非常出色，完美体现三体叙事精髓", 5),
                ],
                weight=1.1,
            ),
            # 主题契合度评估（硅基共生）
            SurveyQuestion(
                dimension=SurveyDimension.THEME_ALIGNMENT,
                question_id="theme_silicon_symbiosis",
                question_text="硅基共生主题在Athena IP形象中的体现如何？",
                description="评估人工智能与人类智慧协作进化的主题是否清晰传达",
                options=[
                    ("主题不明确，难以理解", 1),
                    ("主题有一定体现，但不够突出", 2),
                    ("主题清晰，有体现", 3),
                    ("主题突出，很好地传达了理念", 4),
                    ("主题非常突出，深刻体现硅基共生理念", 5),
                ],
                weight=1.0,
            ),
            # 目标受众匹配度（80/90后）
            SurveyQuestion(
                dimension=SurveyDimension.AUDIENCE_FIT,
                question_id="audience_8090",
                question_text="作为80/90后用户，您觉得Athena IP形象是否符合您的审美和兴趣？",
                description="评估IP形象是否吸引核心技术用户群体（80后、90后）",
                options=[
                    ("完全不符合我的审美", 1),
                    ("不太符合，有些元素不喜欢", 2),
                    ("一般，可以接受", 3),
                    ("比较符合，挺喜欢的", 4),
                    ("非常符合，正是我喜欢的风格", 5),
                ],
                weight=0.9,
            ),
            # 情感共鸣评估
            SurveyQuestion(
                dimension=SurveyDimension.EMOTIONAL_IMPACT,
                question_id="emotional_resonance",
                question_text="Athena IP形象是否引起了您的情感共鸣？",
                description="评估IP形象是否能引起用户的情感连接和认同感",
                options=[
                    ("毫无共鸣，感觉很陌生", 1),
                    ("共鸣较弱，缺乏情感连接", 2),
                    ("有一些共鸣", 3),
                    ("有较强的共鸣", 4),
                    ("强烈共鸣，完全认同IP形象", 5),
                ],
                weight=1.0,
            ),
            # 整体印象评估
            SurveyQuestion(
                dimension=SurveyDimension.OVERALL_IMPRESSION,
                question_id="overall_impression",
                question_text="总体而言，您对Athena IP形象的印象如何？",
                description="整体评价，综合所有维度的感受",
                options=[
                    ("非常负面，需要彻底重做", 1),
                    ("比较负面，有较大改进空间", 2),
                    ("中立，可以接受", 3),
                    ("比较正面，整体不错", 4),
                    ("非常正面，超出期望", 5),
                ],
                weight=1.3,  # 整体印象权重最高
            ),
        ]

        return questions

    def run_interactive_survey(self, user_segment: UserSegment = None) -> Optional[SurveyResponse]:
        """运行交互式调查（命令行界面）"""
        print("\n" + "=" * 60)
        print("Athena IP形象用户调查")
        print("=" * 60)
        print("\n欢迎参与Athena IP形象调查！")
        print("本次调查将收集您对Athena IP形象的反馈，帮助我们持续优化。")
        print("请根据您的真实感受回答以下问题（1-5分）。\n")

        # 如果没有提供用户分段，询问用户
        if user_segment is None:
            user_segment = self._ask_user_segment()

        answers = {}
        comments = {}

        # 逐一提问
        for question in self.survey_questions:
            print(f"\n[{question.dimension.value}] {question.question_text}")
            print(f"  描述: {question.description}")
            print("\n选项:")
            for i, (option_text, score) in enumerate(question.options, 1):
                print(f"  {i}. {option_text} ({score}分)")

            # 获取用户评分
            while True:
                try:
                    answer = input(
                        f"\n请输入您的选择 (1-{len(question.options)})，或直接输入分值 (1-5): "
                    ).strip()

                    if answer.isdigit():
                        answer_int = int(answer)
                        if 1 <= answer_int <= len(question.options):
                            # 用户选择了选项编号
                            _, score = question.options[answer_int - 1]
                            answers[question.question_id] = score
                            break
                        elif 1 <= answer_int <= 5:
                            # 用户直接输入了分值
                            answers[question.question_id] = answer_int
                            break
                        else:
                            print(f"请输入1-{len(question.options)}之间的数字")
                    else:
                        print("请输入有效的数字")
                except ValueError:
                    print("请输入有效的数字")

            # 询问是否有额外评论
            comment = input(
                f"是否有关于'{question.question_text}'的额外评论？(直接回车跳过): "
            ).strip()
            if comment:
                comments[question.question_id] = comment

        # 收集总体评论
        print("\n" + "=" * 40)
        overall_comment = input("请提供对Athena IP形象的总体评论和建议: ").strip()
        if overall_comment:
            comments["overall"] = overall_comment

        # 创建调查响应
        response_id = (
            f"survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        )
        response = SurveyResponse(
            response_id=response_id,
            user_segment=user_segment,
            timestamp=datetime.now(),
            answers=answers,
            comments=comments,
        )

        # 存储响应
        self.survey_responses.append(response)

        # 转换为反馈条目并存储到反馈系统
        self._store_response_as_feedback(response)

        print(f"\n✅ 调查完成！感谢您的参与。")
        print(f"您的响应ID: {response_id}")

        return response

    def _ask_user_segment(self) -> UserSegment:
        """询问用户所属分段"""
        print("\n请选择您所属的年龄段:")
        segments = list(UserSegment)
        for i, segment in enumerate(segments, 1):
            print(f"  {i}. {segment.value}")

        while True:
            try:
                choice = input(f"请选择 (1-{len(segments)}): ").strip()
                if choice.isdigit():
                    choice_int = int(choice)
                    if 1 <= choice_int <= len(segments):
                        return segments[choice_int - 1]
                print(f"请输入1-{len(segments)}之间的数字")
            except ValueError:
                print("请输入有效的数字")

    def _store_response_as_feedback(self, response: SurveyResponse):
        """将调查响应转换为反馈条目并存储"""
        try:
            # 为每个维度创建单独的反馈条目
            for question in self.survey_questions:
                if question.question_id in response.answers:
                    feedback_entry = FeedbackEntry(
                        feedback_id=f"{response.response_id}_{question.question_id}",
                        feedback_type=FeedbackType.IP_IMAGE,
                        source=FeedbackSource.EXTERNAL_USER,
                        user_id=f"survey_user_{response.user_segment.value}",
                        timestamp=response.timestamp,
                        rating=response.answers[question.question_id],
                        comment=response.comments.get(question.question_id, ""),
                        suggestions=[],  # 调查响应的建议已在评论中
                        context={
                            "survey_dimension": question.dimension.value,
                            "question_id": question.question_id,
                            "user_segment": response.user_segment.value,
                            "response_id": response.response_id,
                        },
                        metadata={"survey_response": True, "question_weight": question.weight},
                    )

                    # 提交到反馈系统
                    self.feedback_system.submit_feedback(feedback_entry)

            # 如果有总体评论，创建总体反馈
            if "overall" in response.comments:
                overall_feedback = FeedbackEntry(
                    feedback_id=f"{response.response_id}_overall",
                    feedback_type=FeedbackType.OVERALL_EXPERIENCE,
                    source=FeedbackSource.EXTERNAL_USER,
                    user_id=f"survey_user_{response.user_segment.value}",
                    timestamp=response.timestamp,
                    rating=self._calculate_overall_rating(response),
                    comment=response.comments.get("overall", ""),
                    suggestions=[],
                    context={
                        "survey_type": "ip_image_comprehensive",
                        "user_segment": response.user_segment.value,
                        "response_id": response.response_id,
                    },
                    metadata={"survey_response": True},
                )
                self.feedback_system.submit_feedback(overall_feedback)

            logger.info(f"调查响应 {response.response_id} 已成功存储为反馈条目")

        except Exception as e:
            logger.error(f"存储调查响应为反馈条目失败: {e}")

    def _calculate_overall_rating(self, response: SurveyResponse) -> Optional[int]:
        """计算总体评分（加权平均）"""
        if not response.answers:
            return None

        weighted_sum = 0
        total_weight = 0

        for question in self.survey_questions:
            if question.question_id in response.answers:
                weighted_sum += response.answers[question.question_id] * question.weight
                total_weight += question.weight

        if total_weight > 0:
            return round(weighted_sum / total_weight)
        return None

    def analyze_survey_responses(self, days: int = 30) -> Optional[SurveyAnalysis]:
        """分析调查响应"""
        # 过滤时间范围内的响应
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_responses = [r for r in self.survey_responses if r.timestamp >= cutoff_date]

        if not recent_responses:
            logger.info(f"过去{days}天内没有调查响应数据")
            return None

        # 计算各维度得分
        dimension_scores = {}
        segment_breakdown = {}

        for dimension in SurveyDimension:
            # 收集该维度的所有评分
            dimension_responses = []
            for response in recent_responses:
                for question in self.survey_questions:
                    if question.dimension == dimension and question.question_id in response.answers:
                        dimension_responses.append(
                            {
                                "score": response.answers[question.question_id],
                                "segment": response.user_segment,
                                "weight": question.weight,
                            }
                        )

            if dimension_responses:
                # 加权平均
                weighted_sum = sum(r["score"] * r["weight"] for r in dimension_responses)
                total_weight = sum(r["weight"] for r in dimension_responses)
                dimension_scores[dimension] = weighted_sum / total_weight

                # 按用户分段分析
                for segment in UserSegment:
                    segment_responses = [r for r in dimension_responses if r["segment"] == segment]
                    if segment_responses:
                        if segment not in segment_breakdown:
                            segment_breakdown[segment] = {}

                        seg_weighted_sum = sum(r["score"] * r["weight"] for r in segment_responses)
                        seg_total_weight = sum(r["weight"] for r in segment_responses)
                        segment_breakdown[segment][dimension] = seg_weighted_sum / seg_total_weight

        # 生成关键洞察
        key_insights = self._generate_insights(
            dimension_scores, segment_breakdown, len(recent_responses)
        )

        # 生成优化建议
        recommendations = self._generate_recommendations(dimension_scores, segment_breakdown)

        # 计算完成率（假设所有问题都回答了）
        completion_rate = 1.0  # 交互式调查确保完成所有问题

        # 创建分析结果
        analysis = SurveyAnalysis(
            survey_id=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            total_responses=len(recent_responses),
            completion_rate=completion_rate,
            dimension_scores=dimension_scores,
            segment_breakdown=segment_breakdown,
            key_insights=key_insights,
            recommendations=recommendations,
            timestamp=datetime.now(),
        )

        return analysis

    def _generate_insights(
        self,
        dimension_scores: Dict[SurveyDimension, float],
        segment_breakdown: Dict[UserSegment, Dict[SurveyDimension, float]],
        total_responses: int,
    ) -> List[str]:
        """生成关键洞察"""
        insights = []

        # 总体洞察
        overall_score = dimension_scores.get(SurveyDimension.OVERALL_IMPRESSION, 0)
        if overall_score >= 4.0:
            insights.append(f"总体印象非常好（{overall_score:.2f}/5），IP形象受到用户认可")
        elif overall_score >= 3.0:
            insights.append(f"总体印象中等（{overall_score:.2f}/5），有改进空间")
        else:
            insights.append(f"总体印象较差（{overall_score:.2f}/5），需要重点优化")

        # 各维度洞察
        for dimension, score in dimension_scores.items():
            if score >= 4.5:
                insights.append(f"{dimension.value}表现优秀（{score:.2f}/5），是IP形象的强项")
            elif score <= 2.5:
                insights.append(f"{dimension.value}表现较弱（{score:.2f}/5），需要优先改进")

        # 用户分段洞察
        if segment_breakdown:
            for segment, scores in segment_breakdown.items():
                segment_overall = scores.get(SurveyDimension.OVERALL_IMPRESSION, 0)
                if segment_overall >= 4.0:
                    insights.append(
                        f"{segment.value}用户对IP形象满意度高（{segment_overall:.2f}/5）"
                    )
                elif segment_overall <= 2.5:
                    insights.append(
                        f"{segment.value}用户满意度较低（{segment_overall:.2f}/5），需要针对性优化"
                    )

        insights.append(f"共收集到{total_responses}份有效调查响应")

        return insights

    def _generate_recommendations(
        self,
        dimension_scores: Dict[SurveyDimension, float],
        segment_breakdown: Dict[UserSegment, Dict[SurveyDimension, float]],
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 基于低分维度生成建议
        low_score_threshold = 3.0
        for dimension, score in dimension_scores.items():
            if score < low_score_threshold:
                if dimension == SurveyDimension.VISUAL_STYLE:
                    recommendations.append("加强漫威电影风格的视觉设计，增加科技感和视觉冲击力")
                elif dimension == SurveyDimension.NARRATIVE_STYLE:
                    recommendations.append("深化三体风格的叙事，增加哲学深度和科幻元素")
                elif dimension == SurveyDimension.THEME_ALIGNMENT:
                    recommendations.append("更清晰地传达硅基共生主题，加强人工智能与人类协作的理念")
                elif dimension == SurveyDimension.AUDIENCE_FIT:
                    recommendations.append("针对80/90后用户优化视觉和叙事元素，提高吸引力")
                elif dimension == SurveyDimension.EMOTIONAL_IMPACT:
                    recommendations.append("增加情感共鸣点，让IP形象更容易引发用户认同")

        # 基于用户分段差异生成建议
        if segment_breakdown:
            for segment in [UserSegment.GEN_80, UserSegment.GEN_90]:
                if segment in segment_breakdown:
                    seg_score = segment_breakdown[segment].get(
                        SurveyDimension.OVERALL_IMPRESSION, 0
                    )
                    if seg_score < 3.5:
                        recommendations.append(
                            f"针对{segment.value}用户进行专项优化，提高核心用户满意度"
                        )

        # 通用建议
        if not recommendations:  # 如果所有维度都很好
            recommendations.append("保持当前设计水准，考虑扩展更多IP形象变体")
            recommendations.append("探索新的视觉风格和叙事方式，丰富IP形象层次")

        recommendations.append("定期进行用户调查，持续收集反馈并优化")

        return recommendations

    def save_survey_data(self, output_dir: Optional[Path] = None) -> Path:
        """保存调查数据到文件"""
        if output_dir is None:
            output_dir = Path(__file__).parent / "assets" / "survey_data"

        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存调查响应
        responses_file = output_dir / f"survey_responses_{datetime.now().strftime('%Y%m%d')}.json"
        serializable_responses = []
        for response in self.survey_responses:
            response_dict = asdict(response)
            response_dict["timestamp"] = response.timestamp.isoformat()
            response_dict["user_segment"] = response.user_segment.value
            serializable_responses.append(response_dict)

        with open(responses_file, "w", encoding="utf-8") as f:
            json.dump(serializable_responses, f, indent=2, ensure_ascii=False)

        logger.info(f"调查响应数据保存到: {responses_file}")

        # 保存调查问卷定义
        questions_file = output_dir / "survey_questions.json"
        serializable_questions = []
        for question in self.survey_questions:
            question_dict = asdict(question)
            question_dict["dimension"] = question.dimension.value
            # 转换options格式
            question_dict["options"] = [
                {"text": text, "score": score} for text, score in question.options
            ]
            serializable_questions.append(question_dict)

        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(serializable_questions, f, indent=2, ensure_ascii=False)

        return output_dir

    def load_survey_data(self, input_file: Path) -> bool:
        """从文件加载调查数据"""
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.survey_responses = []
            for item in data:
                # 解析响应
                response = SurveyResponse(
                    response_id=item["response_id"],
                    user_segment=UserSegment(item["user_segment"]),
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    answers=item["answers"],
                    comments=item.get("comments", {}),
                    metadata=item.get("metadata", {}),
                )
                self.survey_responses.append(response)

            logger.info(f"从 {input_file} 加载了 {len(self.survey_responses)} 条调查响应")
            return True

        except Exception as e:
            logger.error(f"加载调查数据失败: {e}")
            return False

    def generate_survey_report(self, analysis: SurveyAnalysis) -> Dict[str, Any]:
        """生成调查报告"""
        report = {
            "report_id": analysis.survey_id,
            "generated_at": datetime.now().isoformat(),
            "analysis_period": f"{analysis.timestamp.strftime('%Y-%m-%d')}",
            "summary": {
                "total_responses": analysis.total_responses,
                "completion_rate": analysis.completion_rate,
                "overall_score": analysis.dimension_scores.get(
                    SurveyDimension.OVERALL_IMPRESSION, 0
                ),
            },
            "dimension_scores": {
                dim.value: score for dim, score in analysis.dimension_scores.items()
            },
            "segment_analysis": {},
            "key_insights": analysis.key_insights,
            "recommendations": analysis.recommendations,
        }

        # 用户分段分析
        for segment, scores in analysis.segment_breakdown.items():
            report["segment_analysis"][segment.value] = {
                dim.value: score for dim, score in scores.items()
            }

        return report

    def save_survey_report(self, report: Dict[str, Any]) -> Path:
        """保存调查报告"""
        output_dir = Path(__file__).parent / "assets" / "survey_reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        report_file = (
            output_dir / f"ip_image_survey_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"调查报告保存到: {report_file}")
        return report_file


def test_interactive_survey():
    """测试交互式调查"""
    print("测试IP形象用户调查系统...")

    survey = IPImageFeedbackSurvey()

    # 模拟几个调查响应（用于测试）
    print("\n模拟调查响应收集...")

    # 模拟一个80后用户的响应
    response_80 = SurveyResponse(
        response_id="test_survey_001",
        user_segment=UserSegment.GEN_80,
        timestamp=datetime.now(),
        answers={
            "visual_marvel": 4,
            "narrative_three_body": 5,
            "theme_silicon_symbiosis": 4,
            "audience_8090": 5,
            "emotional_resonance": 4,
            "overall_impression": 4,
        },
        comments={
            "visual_marvel": "漫威风格很明显，科技感十足",
            "overall": "作为80后很喜欢这个IP形象，很有科技感",
        },
    )
    survey.survey_responses.append(response_80)
    survey._store_response_as_feedback(response_80)

    # 模拟一个90后用户的响应
    response_90 = SurveyResponse(
        response_id="test_survey_002",
        user_segment=UserSegment.GEN_90,
        timestamp=datetime.now(),
        answers={
            "visual_marvel": 5,
            "narrative_three_body": 4,
            "theme_silicon_symbiosis": 3,
            "audience_8090": 4,
            "emotional_resonance": 5,
            "overall_impression": 4,
        },
        comments={
            "theme_silicon_symbiosis": "硅基共生的主题可以更突出一些",
            "overall": "视觉效果很棒，但主题传达可以加强",
        },
    )
    survey.survey_responses.append(response_90)
    survey._store_response_as_feedback(response_90)

    # 分析调查数据
    print("\n分析调查数据...")
    analysis = survey.analyze_survey_responses(days=30)

    if analysis:
        print(f"✅ 调查分析完成")
        print(f"  总响应数: {analysis.total_responses}")
        print(f"  各维度得分:")
        for dimension, score in analysis.dimension_scores.items():
            print(f"    {dimension.value}: {score:.2f}/5")

        print(f"  关键洞察:")
        for insight in analysis.key_insights[:3]:  # 显示前3个
            print(f"    • {insight}")

        print(f"  优化建议:")
        for recommendation in analysis.recommendations[:3]:  # 显示前3个
            print(f"    • {recommendation}")

        # 生成和保存报告
        report = survey.generate_survey_report(analysis)
        report_file = survey.save_survey_report(report)
        print(f"  报告保存到: {report_file}")

        # 保存调查数据
        data_dir = survey.save_survey_data()
        print(f"  调查数据保存到: {data_dir}")
    else:
        print("ℹ️ 没有调查数据可分析")

    return survey


if __name__ == "__main__":
    # 直接运行测试
    test_interactive_survey()
