#!/usr/bin/env python3
"""
质量评估器 - 自动化代码质量评估流程

功能：
1. 从实验记录中获取代码输出
2. 使用CodeQualityAssessor评估代码质量
3. 与参考解决方案比较
4. 生成质量对比报告
5. 进行统计显著性检验

与实验记录器的集成：
- 从experiment_logger.py获取实验记录
- 为每个记录添加质量评分
- 更新数据库中的质量信息
"""

import json
import logging
import math
import os
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_agent_dir = os.path.dirname(os.path.dirname(current_dir))  # mini-agent
project_root = os.path.dirname(project_agent_dir)  # openclaw
sys.path.insert(0, project_root)
sys.path.insert(0, project_agent_dir)

from agent.core.experiment_logger import (
    ExperimentDataQuality,
    ExperimentLogger,
    ExperimentRecord,
    ExperimentRecordStatus,
    get_experiment_logger,
)
from agent.core.quality_assessment import (
    CodeQualityAssessment,
    CodeQualityAssessor,
    QualityDimension,
    QualityScore,
)
from agent.core.statistical_analysis import (
    ExperimentStatistician,
    StatisticalTestResult,
)
from agent.core.test_cases_library import (
    ProgrammingTask,
    TestCaseLibrary,
    get_test_case_library,
)

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class QualityComparison:
    """质量对比结果"""

    experiment_id: str
    group_name: str
    request_id: str
    task_id: str
    code_output: str
    reference_solution: str
    quality_assessment: CodeQualityAssessment
    reference_quality: Optional[CodeQualityAssessment] = None
    quality_difference: Optional[float] = None  # 当前质量 - 参考质量

    def calculate_difference(self):
        """计算质量差异"""
        if self.quality_assessment and self.reference_quality:
            self.quality_difference = (
                self.quality_assessment.overall_score.score
                - self.reference_quality.overall_score.score
            )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        if self.quality_assessment:
            data["quality_assessment"] = self.quality_assessment.to_dict()
        if self.reference_quality:
            data["reference_quality"] = self.reference_quality.to_dict()
        return data


@dataclass
class GroupQualitySummary:
    """分组质量摘要"""

    group_name: str
    sample_count: int
    overall_scores: List[float]
    correctness_scores: List[float]
    complexity_scores: List[float]
    style_scores: List[float]
    readability_scores: List[float]
    maintainability_scores: List[float]

    @property
    def avg_overall(self) -> float:
        """平均总体质量"""
        return statistics.mean(self.overall_scores) if self.overall_scores else 0.0

    @property
    def avg_correctness(self) -> float:
        """平均正确性"""
        return statistics.mean(self.correctness_scores) if self.correctness_scores else 0.0

    @property
    def avg_complexity(self) -> float:
        """平均复杂度"""
        return statistics.mean(self.complexity_scores) if self.complexity_scores else 0.0

    @property
    def avg_style(self) -> float:
        """平均风格"""
        return statistics.mean(self.style_scores) if self.style_scores else 0.0

    @property
    def avg_readability(self) -> float:
        """平均可读性"""
        return statistics.mean(self.readability_scores) if self.readability_scores else 0.0

    @property
    def avg_maintainability(self) -> float:
        """平均可维护性"""
        return statistics.mean(self.maintainability_scores) if self.maintainability_scores else 0.0

    @property
    def std_overall(self) -> float:
        """总体质量标准差"""
        return statistics.stdev(self.overall_scores) if len(self.overall_scores) > 1 else 0.0


@dataclass
class ExperimentQualityReport:
    """实验质量报告"""

    experiment_id: str
    generated_at: str
    total_samples: int
    control_summary: GroupQualitySummary
    treatment_summary: GroupQualitySummary
    quality_comparisons: List[QualityComparison]
    statistical_significance: Optional[StatisticalTestResult] = None

    @property
    def overall_quality_difference(self) -> float:
        """总体质量差异（实验组 - 控制组）"""
        return self.treatment_summary.avg_overall - self.control_summary.avg_overall

    @property
    def quality_improvement_percentage(self) -> float:
        """质量提升百分比"""
        if self.control_summary.avg_overall == 0:
            return 0.0
        return (self.overall_quality_difference / self.control_summary.avg_overall) * 100

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["control_summary"] = asdict(self.control_summary)
        data["treatment_summary"] = asdict(self.treatment_summary)
        data["quality_comparisons"] = [qc.to_dict() for qc in self.quality_comparisons]
        if self.statistical_significance:
            data["statistical_significance"] = asdict(self.statistical_significance)
        return data


class QualityEvaluator:
    """质量评估器"""

    def __init__(
        self,
        experiment_logger: Optional[ExperimentLogger] = None,
        quality_assessor: Optional[CodeQualityAssessor] = None,
        test_case_library: Optional[TestCaseLibrary] = None,
    ):
        """初始化"""
        self.experiment_logger = experiment_logger or get_experiment_logger()
        self.quality_assessor = quality_assessor or CodeQualityAssessor()
        self.test_case_library = test_case_library or get_test_case_library()
        self.statistician = ExperimentStatistician()

    def evaluate_experiment_outputs(
        self,
        experiment_id: str = "coding_plan_deepseek_coder_ab",
        min_data_quality: str = "complete",
        limit: int = 100,
    ) -> ExperimentQualityReport:
        """
        评估实验输出质量

        Args:
            experiment_id: 实验ID
            min_data_quality: 最小数据质量（complete/partial/minimal）
            limit: 最大样本数

        Returns:
            实验质量报告
        """
        logger.info(f"开始评估实验输出质量: {experiment_id}")

        # 获取实验记录
        records = self.experiment_logger.storage.get_experiment_records(
            experiment_id=experiment_id, min_data_quality=min_data_quality, limit=limit
        )

        logger.info(f"获取到 {len(records)} 条实验记录")

        if len(records) < 2:
            logger.warning(f"样本数量不足: {len(records)}，需要至少2个样本")
            return self._create_empty_report(experiment_id)

        # 分组评估
        control_records = [r for r in records if r.group_name == "control"]
        treatment_records = [r for r in records if r.group_name == "treatment"]

        logger.info(f"控制组: {len(control_records)} 个样本")
        logger.info(f"实验组: {len(treatment_records)} 个样本")

        # 评估控制组
        control_comparisons = []
        for record in control_records:
            comparison = self._evaluate_record(record)
            if comparison:
                control_comparisons.append(comparison)

        # 评估实验组
        treatment_comparisons = []
        for record in treatment_records:
            comparison = self._evaluate_record(record)
            if comparison:
                treatment_comparisons.append(comparison)

        # 创建分组摘要
        control_summary = self._create_group_summary("control", control_comparisons)
        treatment_summary = self._create_group_summary("treatment", treatment_comparisons)

        # 合并所有比较
        all_comparisons = control_comparisons + treatment_comparisons

        # 创建报告
        report = ExperimentQualityReport(
            experiment_id=experiment_id,
            generated_at=datetime.now().isoformat(),
            total_samples=len(all_comparisons),
            control_summary=control_summary,
            treatment_summary=treatment_summary,
            quality_comparisons=all_comparisons,
        )

        # 进行统计显著性检验
        if len(control_comparisons) >= 2 and len(treatment_comparisons) >= 2:
            report.statistical_significance = self._analyze_statistical_significance(
                control_comparisons, treatment_comparisons, experiment_id
            )

        # 更新实验记录中的质量评分
        self._update_experiment_quality_scores(all_comparisons)

        return report

    def _evaluate_record(self, record: ExperimentRecord) -> Optional[QualityComparison]:
        """评估单个实验记录"""
        try:
            # 提取代码输出
            code_output = record.output_response
            if not code_output:
                logger.warning(f"记录 {record.id} 缺少代码输出")
                return None

            # 尝试从输入中推断任务ID
            task_id = self._infer_task_id(record.input_prompt)

            # 获取参考解决方案
            reference_solution = ""
            if task_id:
                task = self.test_case_library.get_task(task_id)
                if task:
                    reference_solution = task.reference_solution

            # 评估代码质量
            quality_assessment = self.quality_assessor.assess_code_quality(code_output)

            # 评估参考解决方案质量（如果可用）
            reference_quality = None
            if reference_solution:
                reference_quality = self.quality_assessor.assess_code_quality(reference_solution)

            # 创建比较结果
            comparison = QualityComparison(
                experiment_id=record.experiment_id,
                group_name=record.group_name,
                request_id=record.request_id,
                task_id=task_id or "unknown",
                code_output=code_output,
                reference_solution=reference_solution,
                quality_assessment=quality_assessment,
                reference_quality=reference_quality,
            )

            comparison.calculate_difference()

            logger.debug(
                f"评估完成: 记录 {record.id}, 总体质量: {quality_assessment.overall_score.score:.2f}"
            )

            return comparison

        except Exception as e:
            logger.error(f"评估记录 {record.id} 失败: {e}")
            return None

    def _infer_task_id(self, input_prompt: Optional[str]) -> Optional[str]:
        """从输入提示中推断任务ID"""
        if not input_prompt:
            return None

        # 简单关键词匹配
        prompt_lower = input_prompt.lower()

        task_keywords = {
            "fibonacci": "fibonacci",
            "斐波那契": "fibonacci",
            "reverse": "reverse_string",
            "反转": "reverse_string",
            "duplicate": "remove_duplicates",
            "去重": "remove_duplicates",
            "prime": "is_prime",
            "质数": "is_prime",
            "file": "count_lines",
            "文件": "count_lines",
            "student": "student_management",
            "学生": "student_management",
            "api": "api_client",
            "download": "threaded_downloader",
            "下载": "threaded_downloader",
            "cache": "cache_decorator",
            "缓存": "cache_decorator",
            "validate": "data_validator",
            "验证": "data_validator",
        }

        for keyword, task_id in task_keywords.items():
            if keyword in prompt_lower:
                return task_id

        return None

    def _create_group_summary(
        self, group_name: str, comparisons: List[QualityComparison]
    ) -> GroupQualitySummary:
        """创建分组质量摘要"""
        overall_scores = []
        correctness_scores = []
        complexity_scores = []
        style_scores = []
        readability_scores = []
        maintainability_scores = []

        for comparison in comparisons:
            if comparison.quality_assessment:
                assessment = comparison.quality_assessment
                overall_scores.append(assessment.overall_score.score)

                # 提取各个维度评分
                for dimension_score in assessment.dimension_scores:
                    if dimension_score.dimension == QualityDimension.CORRECTNESS.value:
                        correctness_scores.append(dimension_score.score)
                    elif dimension_score.dimension == QualityDimension.COMPLEXITY.value:
                        complexity_scores.append(dimension_score.score)
                    elif dimension_score.dimension == QualityDimension.STYLE.value:
                        style_scores.append(dimension_score.score)
                    elif dimension_score.dimension == QualityDimension.READABILITY.value:
                        readability_scores.append(dimension_score.score)
                    elif dimension_score.dimension == QualityDimension.MAINTAINABILITY.value:
                        maintainability_scores.append(dimension_score.score)

        return GroupQualitySummary(
            group_name=group_name,
            sample_count=len(comparisons),
            overall_scores=overall_scores,
            correctness_scores=correctness_scores,
            complexity_scores=complexity_scores,
            style_scores=style_scores,
            readability_scores=readability_scores,
            maintainability_scores=maintainability_scores,
        )

    def _analyze_statistical_significance(
        self,
        control_comparisons: List[QualityComparison],
        treatment_comparisons: List[QualityComparison],
        experiment_id: str,
    ) -> StatisticalTestResult:
        """分析质量评分的统计显著性"""
        try:
            # 提取总体质量评分
            control_scores = []
            for comp in control_comparisons:
                if comp.quality_assessment:
                    control_scores.append(comp.quality_assessment.overall_score.score)

            treatment_scores = []
            for comp in treatment_comparisons:
                if comp.quality_assessment:
                    treatment_scores.append(comp.quality_assessment.overall_score.score)

            if len(control_scores) < 2 or len(treatment_scores) < 2:
                logger.warning("样本数量不足，无法进行统计检验")
                return None

            # 使用ExperimentStatistician进行分析
            self.statistician.experiment_data = {
                "control": control_scores,
                "treatment": treatment_scores,
            }

            # 执行独立样本t检验
            t_statistic, p_value = self.statistician.t_test_independent()

            # 计算效应量
            cohens_d = self.statistician.calculate_cohens_d()

            # 计算置信区间
            ci_lower, ci_upper = self.statistician.calculate_confidence_interval(
                confidence_level=0.95
            )

            # 创建结果
            result = StatisticalTestResult(
                experiment_id=experiment_id,
                test_type="independent_t_test_quality",
                sample_size_control=len(control_scores),
                sample_size_treatment=len(treatment_scores),
                mean_control=statistics.mean(control_scores) if control_scores else 0,
                mean_treatment=statistics.mean(treatment_scores) if treatment_scores else 0,
                std_control=statistics.stdev(control_scores) if len(control_scores) > 1 else 0,
                std_treatment=(
                    statistics.stdev(treatment_scores) if len(treatment_scores) > 1 else 0
                ),
                t_statistic=t_statistic,
                p_value=p_value,
                degrees_of_freedom=len(control_scores) + len(treatment_scores) - 2,
                effect_size=cohens_d,
                effect_size_interpretation=self.statistician.interpret_effect_size(cohens_d),
                confidence_interval_lower=ci_lower,
                confidence_interval_upper=ci_upper,
                statistical_significance=p_value < 0.05,
                statistical_power=self.statistician.calculate_statistical_power(
                    effect_size=cohens_d,
                    sample_size_control=len(control_scores),
                    sample_size_treatment=len(treatment_scores),
                ),
            )

            logger.info(f"质量统计显著性分析完成: p-value={p_value:.6f}, Cohen's d={cohens_d:.3f}")

            return result

        except Exception as e:
            logger.error(f"统计显著性分析失败: {e}")
            return None

    def _update_experiment_quality_scores(self, comparisons: List[QualityComparison]):
        """更新实验记录中的质量评分"""
        updated_count = 0

        for comparison in comparisons:
            try:
                # 查找对应的实验记录
                records = self.experiment_logger.storage.get_experiment_records(
                    request_id=comparison.request_id, limit=1
                )

                if not records:
                    continue

                record = records[0]

                # 更新质量评分
                if comparison.quality_assessment:
                    assessment = comparison.quality_assessment

                    quality_breakdown = {}
                    for dim_score in assessment.dimension_scores:
                        quality_breakdown[dim_score.dimension] = dim_score.score

                    # 记录质量评估结果
                    success = self.experiment_logger.log_experiment_quality(
                        request_id=comparison.request_id,
                        quality_assessment={
                            "quality_score": assessment.overall_score.score,
                            "quality_breakdown": quality_breakdown,
                            "quality_assessor": "auto_quality_evaluator",
                            "metadata": {
                                "evaluated_at": datetime.now().isoformat(),
                                "task_id": comparison.task_id,
                                "comparison_with_reference": comparison.reference_quality
                                is not None,
                            },
                        },
                    )

                    if success:
                        updated_count += 1

            except Exception as e:
                logger.error(f"更新记录 {comparison.request_id} 质量评分失败: {e}")

        logger.info(f"更新了 {updated_count} 条记录的质量评分")

    def _create_empty_report(self, experiment_id: str) -> ExperimentQualityReport:
        """创建空报告（当样本不足时）"""
        empty_summary = GroupQualitySummary(
            group_name="",
            sample_count=0,
            overall_scores=[],
            correctness_scores=[],
            complexity_scores=[],
            style_scores=[],
            readability_scores=[],
            maintainability_scores=[],
        )

        return ExperimentQualityReport(
            experiment_id=experiment_id,
            generated_at=datetime.now().isoformat(),
            total_samples=0,
            control_summary=empty_summary,
            treatment_summary=empty_summary,
            quality_comparisons=[],
        )

    def generate_quality_report(
        self, report: ExperimentQualityReport, output_format: str = "text"
    ) -> str:
        """
        生成质量报告

        Args:
            report: 实验质量报告
            output_format: 输出格式（text/json/markdown）

        Returns:
            报告字符串
        """
        if output_format == "json":
            return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)

        elif output_format == "markdown":
            return self._generate_markdown_report(report)

        else:  # text
            return self._generate_text_report(report)

    def _generate_text_report(self, report: ExperimentQualityReport) -> str:
        """生成文本格式报告"""
        lines = []

        lines.append("=" * 80)
        lines.append(f"实验质量评估报告")
        lines.append("=" * 80)
        lines.append(f"实验ID: {report.experiment_id}")
        lines.append(f"生成时间: {report.generated_at}")
        lines.append(f"总样本数: {report.total_samples}")
        lines.append(f"控制组样本: {report.control_summary.sample_count}")
        lines.append(f"实验组样本: {report.treatment_summary.sample_count}")
        lines.append("")

        # 质量对比表格
        lines.append("质量评分对比:")
        lines.append("-" * 60)
        lines.append(f"{'维度':<15} {'控制组':<12} {'实验组':<12} {'差异':<12} {'提升%':<12}")
        lines.append("-" * 60)

        metrics = [
            ("总体质量", report.control_summary.avg_overall, report.treatment_summary.avg_overall),
            (
                "正确性",
                report.control_summary.avg_correctness,
                report.treatment_summary.avg_correctness,
            ),
            (
                "复杂度",
                report.control_summary.avg_complexity,
                report.treatment_summary.avg_complexity,
            ),
            ("代码风格", report.control_summary.avg_style, report.treatment_summary.avg_style),
            (
                "可读性",
                report.control_summary.avg_readability,
                report.treatment_summary.avg_readability,
            ),
            (
                "可维护性",
                report.control_summary.avg_maintainability,
                report.treatment_summary.avg_maintainability,
            ),
        ]

        for name, control_avg, treatment_avg in metrics:
            diff = treatment_avg - control_avg
            if control_avg != 0:
                percent = (diff / control_avg) * 100
            else:
                percent = 0.0

            lines.append(
                f"{name:<15} {control_avg:<12.2f} {treatment_avg:<12.2f} "
                f"{diff:>+8.2f} {percent:>+8.1f}%"
            )

        lines.append("-" * 60)
        lines.append("")

        # 统计显著性
        if report.statistical_significance:
            sig = report.statistical_significance
            lines.append("统计显著性分析:")
            lines.append(
                f"  样本量: 控制组={sig.sample_size_control}, 实验组={sig.sample_size_treatment}"
            )
            lines.append(f"  均值差异: {report.overall_quality_difference:.3f} 分")
            lines.append(f"  t统计量: {sig.t_statistic:.3f}, p值: {sig.p_value:.6f}")
            lines.append(
                f"  效应量 (Cohen's d): {sig.effect_size:.3f} ({sig.effect_size_interpretation})"
            )
            lines.append(
                f"  95%置信区间: [{sig.confidence_interval_lower:.3f}, {sig.confidence_interval_upper:.3f}]"
            )
            lines.append(f"  统计功效: {sig.statistical_power:.3f}")
            lines.append(f"  统计显著: {'是' if sig.statistical_significance else '否'}")
            lines.append("")

        # 质量分布
        if report.control_summary.sample_count > 0 and report.treatment_summary.sample_count > 0:
            lines.append("质量分布:")
            lines.append(f"  控制组标准差: {report.control_summary.std_overall:.3f}")
            lines.append(f"  实验组标准差: {report.treatment_summary.std_overall:.3f}")
            lines.append("")

        # 决策建议
        lines.append("质量决策建议:")
        if report.total_samples >= 20:
            if (
                report.statistical_significance
                and report.statistical_significance.statistical_significance
            ):
                if report.overall_quality_difference > 0.5:  # 质量提升显著
                    lines.append("  ✅ 实验组质量显著优于控制组（p<0.05），质量提升明显")
                elif report.overall_quality_difference < -0.5:  # 质量下降显著
                    lines.append("  ⚠️  实验组质量显著低于控制组，需谨慎迁移")
                else:
                    lines.append("  ⚠️  质量无显著差异，可基于成本节省决策")
            else:
                lines.append("  ⚠️  质量差异无统计显著性，需要更多样本")
        else:
            lines.append("  ⚠️  样本数量不足（<20），建议收集更多数据")

        if report.quality_improvement_percentage >= 10:
            lines.append(f"  ✅ 质量提升显著: +{report.quality_improvement_percentage:.1f}%")
        elif report.quality_improvement_percentage <= -10:
            lines.append(f"  ⚠️  质量下降明显: {report.quality_improvement_percentage:.1f}%")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _generate_markdown_report(self, report: ExperimentQualityReport) -> str:
        """生成Markdown格式报告"""
        lines = []

        lines.append(f"# 实验质量评估报告")
        lines.append("")
        lines.append(f"**实验ID**: {report.experiment_id}  ")
        lines.append(f"**生成时间**: {report.generated_at}  ")
        lines.append(f"**总样本数**: {report.total_samples}  ")
        lines.append(f"**控制组样本**: {report.control_summary.sample_count}  ")
        lines.append(f"**实验组样本**: {report.treatment_summary.sample_count}  ")
        lines.append("")

        # 质量对比表格
        lines.append("## 质量评分对比")
        lines.append("")
        lines.append("| 维度 | 控制组 | 实验组 | 差异 | 提升% |")
        lines.append("|------|--------|--------|------|-------|")

        metrics = [
            ("总体质量", report.control_summary.avg_overall, report.treatment_summary.avg_overall),
            (
                "正确性",
                report.control_summary.avg_correctness,
                report.treatment_summary.avg_correctness,
            ),
            (
                "复杂度",
                report.control_summary.avg_complexity,
                report.treatment_summary.avg_complexity,
            ),
            ("代码风格", report.control_summary.avg_style, report.treatment_summary.avg_style),
            (
                "可读性",
                report.control_summary.avg_readability,
                report.treatment_summary.avg_readability,
            ),
            (
                "可维护性",
                report.control_summary.avg_maintainability,
                report.treatment_summary.avg_maintainability,
            ),
        ]

        for name, control_avg, treatment_avg in metrics:
            diff = treatment_avg - control_avg
            if control_avg != 0:
                percent = (diff / control_avg) * 100
            else:
                percent = 0.0

            diff_sign = "+" if diff > 0 else ""
            percent_sign = "+" if percent > 0 else ""

            lines.append(
                f"| {name} | {control_avg:.2f} | {treatment_avg:.2f} | "
                f"{diff_sign}{diff:.2f} | {percent_sign}{percent:.1f}% |"
            )

        lines.append("")

        # 统计显著性
        if report.statistical_significance:
            sig = report.statistical_significance
            lines.append("## 统计显著性分析")
            lines.append("")
            lines.append(
                f"- **样本量**: 控制组={sig.sample_size_control}, 实验组={sig.sample_size_treatment}"
            )
            lines.append(f"- **均值差异**: {report.overall_quality_difference:.3f} 分")
            lines.append(f"- **t统计量**: {sig.t_statistic:.3f}, **p值**: {sig.p_value:.6f}")
            lines.append(
                f"- **效应量 (Cohen's d)**: {sig.effect_size:.3f} ({sig.effect_size_interpretation})"
            )
            lines.append(
                f"- **95%置信区间**: [{sig.confidence_interval_lower:.3f}, {sig.confidence_interval_upper:.3f}]"
            )
            lines.append(f"- **统计功效**: {sig.statistical_power:.3f}")
            lines.append(f"- **统计显著**: {'✅ 是' if sig.statistical_significance else '❌ 否'}")
            lines.append("")

        # 决策建议
        lines.append("## 质量决策建议")
        lines.append("")

        if report.total_samples >= 20:
            if (
                report.statistical_significance
                and report.statistical_significance.statistical_significance
            ):
                if report.overall_quality_difference > 0.5:
                    lines.append("✅ **实验组质量显著优于控制组** (p<0.05)，质量提升明显")
                elif report.overall_quality_difference < -0.5:
                    lines.append("⚠️ **实验组质量显著低于控制组**，需谨慎迁移")
                else:
                    lines.append("⚠️ **质量无显著差异**，可基于成本节省决策")
            else:
                lines.append("⚠️ **质量差异无统计显著性**，需要更多样本")
        else:
            lines.append("⚠️ **样本数量不足** (<20)，建议收集更多数据")

        if report.quality_improvement_percentage >= 10:
            lines.append(f"✅ **质量提升显著**: +{report.quality_improvement_percentage:.1f}%")
        elif report.quality_improvement_percentage <= -10:
            lines.append(f"⚠️ **质量下降明显**: {report.quality_improvement_percentage:.1f}%")

        lines.append("")

        return "\n".join(lines)


# 全局实例
_quality_evaluator_instance = None


def get_quality_evaluator() -> QualityEvaluator:
    """获取全局质量评估器实例"""
    global _quality_evaluator_instance
    if _quality_evaluator_instance is None:
        _quality_evaluator_instance = QualityEvaluator()
    return _quality_evaluator_instance


if __name__ == "__main__":
    # 测试代码
    import logging

    logging.basicConfig(level=logging.INFO)

    print("🧪 测试质量评估器...")

    evaluator = get_quality_evaluator()

    # 生成质量报告
    report = evaluator.evaluate_experiment_outputs(
        experiment_id="coding_plan_deepseek_coder_ab", limit=50
    )

    # 打印报告
    if report.total_samples > 0:
        text_report = evaluator.generate_quality_report(report, output_format="text")
        print("\n" + text_report)

        # 保存JSON报告
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json_file = f.name

        try:
            json_report = evaluator.generate_quality_report(report, output_format="json")
            with open(json_file, "w", encoding="utf-8") as f:
                f.write(json_report)
            print(f"\n✅ JSON报告已保存到: {json_file}")
        finally:
            if os.path.exists(json_file):
                os.unlink(json_file)
    else:
        print("⚠️  没有找到足够的实验记录进行评估")

    print("\n✅ 质量评估器测试完成")
