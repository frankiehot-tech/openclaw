#!/usr/bin/env python3
"""
MAREF质量评估集成器

基于MAREF理念的高级质量评估集成器，结合：
1. 三才六层模型 (ThreeTalentAssessmentEngine)
2. 河图洛书调度器 (HetuLuoshuScheduler)
3. 格雷编码状态管理器 (GrayCodeStateManager)
4. 八卦代数评估器 (EightTrigramsAssessor)

提供分层质量评估、智能调度、连续演化跟踪和八卦代数分析。
"""

import json
import logging
import os
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = "/Volumes/1TB-M2/openclaw"
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "mini-agent"))

from agent.core.experiment_logger import (
    ExperimentDataQuality,
    ExperimentLogger,
    ExperimentRecord,
    ExperimentRecordStatus,
    get_experiment_logger,
)
from agent.core.maref_quality.eight_trigrams_assessor import (
    EightTrigrams,
    EightTrigramsAssessor,
    HexagramResult,
)
from agent.core.maref_quality.gray_code_state_manager import (
    GrayCodeStateManager,
)
from agent.core.maref_quality.gray_code_state_manager import (
    QualityDimension as GrayQualityDimension,
)
from agent.core.maref_quality.gray_code_state_manager import (
    StateAnalysis,
    StateEvolution,
)
from agent.core.maref_quality.hetu_luoshu_scheduler import (
    AssessmentPriority,
    HetuLuoshuScheduler,
    HetuState,
    LuoshuPosition,
)

# 导入MAREF质量组件
from agent.core.maref_quality.three_talent_engine import (
    EarthLayerAssessor,
    HeavenLayerAssessor,
    HumanLayerAssessor,
    ThreeTalentAssessmentEngine,
    ThreeTalentResult,
)
from agent.core.quality_assessment import (
    CodeQualityAssessment,
    CodeQualityAssessor,
)
from agent.core.quality_assessment import QualityDimension as BaseQualityDimension
from agent.core.quality_assessment import (
    QualityScore,
)

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class MarefQualityResult:
    """MAREF质量评估结果"""

    # 三才评估结果
    human_result: Dict[str, Any]  # 人层：代码级评估
    earth_result: Dict[str, Any]  # 地层：维度聚合
    heaven_result: Dict[str, Any]  # 天层：宏观分析

    # 八卦代数评估
    trigram_scores: Dict[str, Dict[str, Any]]  # 八卦维度评分
    hexagram_result: Optional[HexagramResult] = None  # 六十四卦复合状态

    # 格雷编码状态
    gray_state_analysis: Optional[StateAnalysis] = None  # 状态分析
    evolution_history: List[StateEvolution] = field(default_factory=list)  # 演化历史

    # 调度状态
    current_hetu_state: Optional[str] = None  # 当前河图状态
    task_schedule: List[str] = field(default_factory=list)  # 任务调度路径

    # 汇总指标
    overall_score: float = 0.0
    quality_breakdown: Dict[str, float] = field(default_factory=dict)
    improvement_suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)

        # 转换复杂对象
        if self.hexagram_result:
            data["hexagram_result"] = {
                "hexagram_index": self.hexagram_result.hexagram_index,
                "upper_trigram": (
                    self.hexagram_result.upper_trigram.value
                    if self.hexagram_result.upper_trigram
                    else None
                ),
                "lower_trigram": (
                    self.hexagram_result.lower_trigram.value
                    if self.hexagram_result.lower_trigram
                    else None
                ),
                "upper_binary": self.hexagram_result.upper_binary,
                "lower_binary": self.hexagram_result.lower_binary,
                "combined_binary": self.hexagram_result.combined_binary,
                "interpretation": self.hexagram_result.interpretation,
                "overall_quality": self.hexagram_result.overall_quality,
                "strategic_implications": self.hexagram_result.strategic_implications,
            }

        if self.gray_state_analysis:
            data["gray_state_analysis"] = {
                "state_code": self.gray_state_analysis.state_code,
                "binary_representation": self.gray_state_analysis.binary_representation,
                "gray_code_representation": self.gray_state_analysis.gray_code_representation,
                "quality_score": self.gray_state_analysis.quality_score,
                "evolution_distance": self.gray_state_analysis.evolution_distance,
                "improvement_suggestions": self.gray_state_analysis.improvement_suggestions,
                "dimension_values": self.gray_state_analysis.dimension_values,
            }

        # 转换evolution_history中的datetime对象
        if self.evolution_history:
            data["evolution_history"] = []
            for evolution in self.evolution_history:
                evolution_dict = {
                    "from_state": evolution.from_state,
                    "to_state": evolution.to_state,
                    "changed_dimension": evolution.changed_dimension,
                    "change_magnitude": evolution.change_magnitude,
                    "timestamp": evolution.timestamp.isoformat() if evolution.timestamp else None,
                    "context": evolution.context,
                }
                data["evolution_history"].append(evolution_dict)

        return data


class MarefQualityEvaluator:
    """MAREF质量评估器"""

    def __init__(
        self,
        experiment_logger: Optional[ExperimentLogger] = None,
        enable_advanced_features: bool = True,
    ):
        """初始化MAREF质量评估器"""

        self.experiment_logger = experiment_logger or get_experiment_logger()
        self.enable_advanced_features = enable_advanced_features

        # 初始化MAREF组件
        logger.info("🔧 初始化MAREF质量评估组件...")

        # 三才评估引擎
        self.three_talent_engine = ThreeTalentAssessmentEngine()
        logger.info("   三才评估引擎初始化完成")

        # 河图洛书调度器
        self.hetu_luoshu_scheduler = HetuLuoshuScheduler()
        logger.info("   河图洛书调度器初始化完成")

        # 格雷编码状态管理器
        self.gray_state_manager = GrayCodeStateManager()
        logger.info("   格雷编码状态管理器初始化完成")

        # 八卦代数评估器
        self.eight_trigrams_assessor = EightTrigramsAssessor()
        logger.info("   八卦代数评估器初始化完成")

        # 传统质量评估器（向后兼容）
        self.legacy_assessor = CodeQualityAssessor()

        # 状态跟踪
        self.current_gray_state = 0  # 初始状态
        self.evolution_history = []

        logger.info("✅ MAREF质量评估器初始化完成")

    def assess_code_quality(
        self, code: str, context: Optional[Dict[str, Any]] = None
    ) -> MarefQualityResult:
        """
        评估代码质量（MAREF综合评估）

        Args:
            code: 要评估的代码
            context: 评估上下文（任务类型、难度等）

        Returns:
            MAREF质量评估结果
        """
        context = context or {}

        logger.info(f"🔍 开始MAREF质量评估 (代码长度: {len(code)} 字符)")

        # 1. 河图洛书调度：确定评估流程
        task_type = context.get("task_type", "code_quality_assessment")
        priority_value = context.get("priority", 3)

        # 将数值优先级转换为AssessmentPriority枚举
        priority_map = {
            1: AssessmentPriority.CRITICAL,
            2: AssessmentPriority.HIGH,
            3: AssessmentPriority.MEDIUM,
            4: AssessmentPriority.LOW,
            5: AssessmentPriority.BATCH,
        }
        priority = priority_map.get(priority_value, AssessmentPriority.MEDIUM)

        # 提交任务到调度器
        task_id = self.hetu_luoshu_scheduler.submit_task(
            code=code, task_type=task_type, priority=priority, context=context
        )

        # 获取任务状态
        task_status = self.hetu_luoshu_scheduler.get_task_status(task_id)
        current_state = task_status.get("state", "INITIAL") if task_status else "INITIAL"

        # 获取调度报告
        system_report = self.hetu_luoshu_scheduler.get_system_report()
        scheduler_status = system_report.get("scheduler_status", {})

        # 生成默认任务调度路径（基于任务类型）
        default_task_schedule = self._generate_default_schedule(task_type)

        logger.info(f"   调度状态: {current_state}")
        logger.info(f"   任务ID: {task_id}")

        # 2. 三才评估：分层质量分析
        logger.info("   执行三才评估...")
        three_talent_result = self.three_talent_engine.assess(code=code, context=context)

        # 3. 八卦代数评估：维度评分
        logger.info("   执行八卦代数评估...")

        # 将HumanLayerResult转换为八卦评估器期望的字典格式
        human_result = three_talent_result.human_result
        code_analysis_dict = {
            "test_coverage": 0.7,  # 默认值，实际应从human_result中提取
            "cyclomatic_complexity": (
                human_result.complexity_metrics.get("cyclomatic_complexity", 5)
                if isinstance(human_result.complexity_metrics, dict)
                else 5
            ),
            "style_score": 7.0,  # 默认值
            "comment_ratio": 0.1,  # 默认值
            "maintainability_index": 6.5,  # 默认值
            "performance_score": 7.0,  # 默认值
            "security_score": 8.0,  # 默认值
            "reliability_score": 7.5,  # 默认值
        }

        trigram_assessments = self.eight_trigrams_assessor.assess_with_trigrams(
            code_analysis=code_analysis_dict, context=context
        )

        # 将TrigramAssessment对象转换为字典格式，便于后续处理
        trigram_scores = {}
        for dimension, assessment in trigram_assessments.items():
            trigram_scores[dimension] = {
                "score": assessment.score,
                "weight": assessment.weight,
                "trigram": (
                    assessment.trigram.value
                    if hasattr(assessment.trigram, "value")
                    else str(assessment.trigram)
                ),
                "dimension": assessment.dimension,
                "binary_representation": assessment.binary_representation,
                "issues": assessment.issues,
                "suggestions": assessment.suggestions,
                "hexagram_contribution": assessment.hexagram_contribution,
            }

        # 4. 复合卦象分析
        hexagram_result = None
        if self.enable_advanced_features and trigram_assessments:
            # 将结果对象转换为字典以用于八卦选择
            heaven_result_dict = {
                "overall_quality": (
                    three_talent_result.heaven_result.cost_quality_ratio * 10
                    if hasattr(three_talent_result.heaven_result, "cost_quality_ratio")
                    else 5.0
                )
            }
            human_result_dict = {
                "complexity_score": code_analysis_dict.get("cyclomatic_complexity", 5.0),
                "style_score": code_analysis_dict.get("style_score", 5.0),
                "overall_quality": (
                    sum(score_info["score"] for score_info in trigram_scores.values())
                    / len(trigram_scores)
                    if trigram_scores
                    else 5.0
                ),
            }

            # 基于质量特征选择上下卦
            upper_trigram_str = self._select_trigram_by_quality(heaven_result_dict, is_upper=True)
            lower_trigram_str = self._select_trigram_by_quality(human_result_dict, is_upper=False)

            # 将字符串转换为EightTrigrams枚举
            upper_trigram = (
                EightTrigrams(upper_trigram_str) if upper_trigram_str else EightTrigrams.QIAN
            )
            lower_trigram = (
                EightTrigrams(lower_trigram_str) if lower_trigram_str else EightTrigrams.KUN
            )

            hexagram_result = self.eight_trigrams_assessor.combine_trigrams(
                upper_trigram=upper_trigram,
                lower_trigram=lower_trigram,
                assessments=trigram_assessments,
            )

            logger.info(
                f"   卦象分析: {hexagram_result.upper_trigram.value}-{hexagram_result.lower_trigram.value}"
            )

        # 5. 格雷编码状态管理
        logger.info("   更新格雷编码状态...")

        # 从八卦评分计算状态
        gray_scores = {}
        # 格雷编码维度列表
        gray_dimensions = [
            "correctness",
            "complexity",
            "style",
            "readability",
            "maintainability",
            "cost_efficiency",
        ]

        for dimension_name, score_info in trigram_scores.items():
            # 如果维度名直接在格雷编码维度中，直接使用
            if dimension_name in gray_dimensions:
                gray_scores[dimension_name] = score_info["score"]
            # 否则进行映射：performance, security, reliability忽略，因为没有对应的格雷编码维度
            # cost_efficiency需要从其他维度计算或使用默认值

        # 确保所有维度都有评分
        for dim in [
            "correctness",
            "complexity",
            "style",
            "readability",
            "maintainability",
            "cost_efficiency",
        ]:
            if dim not in gray_scores:
                gray_scores[dim] = 5.0  # 默认评分

        # 获取格雷编码状态
        new_state = self.gray_state_manager.get_state_from_scores(scores=gray_scores, threshold=6.0)

        # 记录状态演化（如果状态改变）
        if new_state != self.current_gray_state:
            evolution_context = {
                "code_length": len(code),
                "task_type": task_type,
                "trigger": "quality_assessment",
            }

            # 查找需要改进的维度
            changed_dimension = self._find_changed_dimension(self.current_gray_state, new_state)

            if changed_dimension:
                _, evolution = self.gray_state_manager.evolve_state(
                    current_state=self.current_gray_state,
                    dimension=changed_dimension,
                    improvement=0.7,  # 假设中等改进
                    context=evolution_context,
                )
                self.evolution_history.append(evolution)
                self.current_gray_state = new_state

        # 分析当前状态
        state_analysis = self.gray_state_manager.analyze_state(self.current_gray_state)

        # 6. 计算综合质量评分
        overall_score = self._calculate_overall_score(
            three_talent_result=three_talent_result,
            trigram_scores=trigram_scores,
            state_analysis=state_analysis,
        )

        # 7. 生成质量分解和改进建议
        quality_breakdown = self._create_quality_breakdown(trigram_scores)
        improvement_suggestions = self._generate_improvement_suggestions(
            state_analysis=state_analysis, trigram_scores=trigram_scores
        )

        # 8. 创建结果
        result = MarefQualityResult(
            human_result=asdict(three_talent_result.human_result),
            earth_result=asdict(three_talent_result.earth_result),
            heaven_result=asdict(three_talent_result.heaven_result),
            trigram_scores=trigram_scores,
            hexagram_result=hexagram_result,
            gray_state_analysis=state_analysis,
            evolution_history=self.evolution_history[-5:],  # 最近5次演化
            current_hetu_state=current_state,
            task_schedule=default_task_schedule,
            overall_score=overall_score,
            quality_breakdown=quality_breakdown,
            improvement_suggestions=improvement_suggestions,
        )

        logger.info(f"✅ MAREF质量评估完成: 综合评分={overall_score:.2f}/10")
        logger.info(
            f"   格雷状态: {state_analysis.binary_representation} (距离完美: {state_analysis.evolution_distance}步)"
        )

        return result

    def _select_trigram_by_quality(
        self, quality_result: Dict[str, Any], is_upper: bool = True
    ) -> str:
        """基于质量特征选择八卦"""
        if is_upper:
            # 上卦：基于宏观质量特征
            if quality_result.get("overall_quality", 0) >= 8.0:
                return EightTrigrams.QIAN.value  # 乾：完美
            elif quality_result.get("overall_quality", 0) >= 6.0:
                return EightTrigrams.LI.value  # 离：良好
            elif quality_result.get("overall_quality", 0) >= 4.0:
                return EightTrigrams.ZHEN.value  # 震：中等
            else:
                return EightTrigrams.KUN.value  # 坤：较差
        else:
            # 下卦：基于微观代码特征
            complexity_score = quality_result.get("complexity_score", 5.0)
            style_score = quality_result.get("style_score", 5.0)

            if complexity_score <= 3.0 and style_score >= 7.0:
                return EightTrigrams.DUI.value  # 兑：简单优雅
            elif complexity_score >= 7.0 and style_score <= 3.0:
                return EightTrigrams.GEN.value  # 艮：复杂但混乱
            elif complexity_score >= 5.0 and style_score >= 5.0:
                return EightTrigrams.XUN.value  # 巽：平衡
            else:
                return EightTrigrams.KAN.value  # 坎：需要改进

    def _generate_default_schedule(self, task_type: str) -> List[str]:
        """生成默认任务调度路径"""
        # 基于任务类型的默认洛书位置序列
        schedule_mapping = {
            "algorithm_implementation": ["complexity", "correctness", "style", "readability"],
            "utility_class": ["maintainability", "complexity", "style", "readability"],
            "string_processing": ["correctness", "readability", "style"],
            "data_structure": ["complexity", "maintainability", "correctness"],
            "math_operation": ["correctness", "performance", "reliability"],
            "code_quality_assessment": [
                "complexity",
                "style",
                "readability",
                "maintainability",
                "performance",
            ],
        }

        # 获取默认调度或使用通用调度
        default_schedule = schedule_mapping.get(
            task_type, ["complexity", "correctness", "style"]  # 通用调度
        )

        return default_schedule

    def _find_changed_dimension(self, old_state: int, new_state: int) -> Optional[str]:
        """查找状态变化对应的维度"""
        if old_state == new_state:
            return None

        # 计算差异位
        diff = old_state ^ new_state

        # 找到改变的位
        for i in range(6):
            if diff & (1 << i):
                # 映射维度名称
                dimension_mapping = [
                    "correctness",  # 位0
                    "complexity",  # 位1
                    "style",  # 位2
                    "readability",  # 位3
                    "maintainability",  # 位4
                    "cost_efficiency",  # 位5
                ]
                return dimension_mapping[i]

        return None

    def _calculate_overall_score(
        self,
        three_talent_result: ThreeTalentResult,
        trigram_scores: Dict[str, Dict[str, Any]],
        state_analysis: StateAnalysis,
    ) -> float:
        """计算综合质量评分"""

        # 权重分配
        weights = {
            "three_talent": 0.4,  # 三才评估权重
            "trigram": 0.3,  # 八卦代数权重
            "gray_state": 0.3,  # 格雷状态权重
        }

        # 1. 三才评估分数（天层宏观质量）
        if hasattr(three_talent_result.heaven_result, "cost_quality_ratio"):
            heaven_score = three_talent_result.heaven_result.cost_quality_ratio / 10.0
        else:
            heaven_score = 5.0

        # 2. 八卦代数平均分
        trigram_avg = 0.0
        count = 0
        for trigram_info in trigram_scores.values():
            trigram_avg += trigram_info["score"]
            count += 1
        trigram_avg = trigram_avg / count if count > 0 else 5.0

        # 3. 格雷状态质量分（0-10分制）
        gray_score = state_analysis.quality_score

        # 综合评分
        overall = (
            weights["three_talent"] * (heaven_score / 10.0) * 10.0  # 转换为0-10分制
            + weights["trigram"] * trigram_avg
            + weights["gray_state"] * gray_score
        )

        # 限制在0-10范围内
        return max(0.0, min(10.0, overall))

    def _create_quality_breakdown(
        self, trigram_scores: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
        """创建质量分解字典"""
        breakdown = {}

        # 八卦到质量维度的映射
        dimension_mapping = {
            EightTrigrams.QIAN.value: "correctness",
            EightTrigrams.DUI.value: "complexity",
            EightTrigrams.LI.value: "style",
            EightTrigrams.ZHEN.value: "readability",
            EightTrigrams.XUN.value: "maintainability",
            EightTrigrams.KAN.value: "performance",
            EightTrigrams.GEN.value: "security",
            EightTrigrams.KUN.value: "reliability",
        }

        for trigram_name, score_info in trigram_scores.items():
            dim_name = dimension_mapping.get(trigram_name)
            if dim_name:
                breakdown[dim_name] = score_info["score"]

        return breakdown

    def _generate_improvement_suggestions(
        self, state_analysis: StateAnalysis, trigram_scores: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 1. 格雷状态改进建议
        if state_analysis.improvement_suggestions:
            suggestions.extend(state_analysis.improvement_suggestions[:3])

        # 2. 八卦维度改进建议（最低分维度）
        min_trigram_score = float("inf")
        min_trigram_name = None

        for trigram_name, score_info in trigram_scores.items():
            if score_info["score"] < min_trigram_score:
                min_trigram_score = score_info["score"]
                min_trigram_name = trigram_name

        if min_trigram_name and min_trigram_score < 6.0:
            trigram_names = {
                EightTrigrams.QIAN.value: "正确性",
                EightTrigrams.DUI.value: "复杂度",
                EightTrigrams.LI.value: "代码风格",
                EightTrigrams.ZHEN.value: "可读性",
                EightTrigrams.XUN.value: "可维护性",
                EightTrigrams.KAN.value: "性能",
                EightTrigrams.GEN.value: "安全性",
                EightTrigrams.KUN.value: "可靠性",
            }

            dim_name = trigram_names.get(min_trigram_name, min_trigram_name)
            suggestions.append(f"{dim_name}维度评分较低({min_trigram_score:.1f})，建议重点改进")

        # 3. 通用改进建议
        if len(suggestions) < 3:
            suggestions.append("增加测试覆盖率以提高代码正确性")
            suggestions.append("拆分复杂函数以降低圈复杂度")
            suggestions.append("添加注释和文档提高可读性")

        return suggestions[:5]  # 最多5条建议

    def evaluate_experiment_record(
        self, record: ExperimentRecord, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        评估实验记录（集成到实验框架）

        Args:
            record: 实验记录
            context: 评估上下文

        Returns:
            评估结果字典
        """
        context = context or {}

        # 提取代码输出
        code_output = record.output_response
        if not code_output:
            logger.warning(f"记录 {record.id} 缺少代码输出")
            return {"success": False, "error": "缺少代码输出"}

        # 添加实验上下文
        assessment_context = context.copy()
        assessment_context.update(
            {
                "experiment_id": record.experiment_id,
                "group_name": record.group_name,
                "request_id": record.request_id,
                "provider": record.provider,
            }
        )

        # 执行MAREF质量评估
        try:
            result = self.assess_code_quality(code=code_output, context=assessment_context)

            # 转换为实验框架兼容格式
            evaluation_result = {
                "success": True,
                "experiment_id": record.experiment_id,
                "request_id": record.request_id,
                "overall_score": result.overall_score,
                "quality_breakdown": result.quality_breakdown,
                "improvement_suggestions": result.improvement_suggestions,
                "maref_metadata": {
                    "gray_state": (
                        result.gray_state_analysis.state_code if result.gray_state_analysis else 0
                    ),
                    "gray_state_binary": (
                        result.gray_state_analysis.binary_representation
                        if result.gray_state_analysis
                        else ""
                    ),
                    "hexagram": (
                        result.hexagram_result.hexagram_index if result.hexagram_result else None
                    ),
                    "trigram_count": len(result.trigram_scores),
                    "hetu_state": result.current_hetu_state,
                    "assessment_timestamp": datetime.now().isoformat(),
                },
            }

            return evaluation_result

        except Exception as e:
            logger.error(f"评估实验记录失败: {e}")
            return {"success": False, "error": str(e)}

    def generate_maref_report(self, result: MarefQualityResult) -> str:
        """生成MAREF格式质量报告"""

        lines = []
        lines.append("=" * 80)
        lines.append("🧠 MAREF质量评估报告")
        lines.append("=" * 80)

        # 综合评分
        lines.append(f"综合质量评分: {result.overall_score:.2f}/10")
        lines.append("")

        # 格雷编码状态
        if result.gray_state_analysis:
            gray = result.gray_state_analysis
            lines.append("📊 格雷编码状态分析:")
            lines.append(f"   状态编码: {gray.state_code} ({gray.binary_representation})")
            lines.append(f"   格雷编码: {gray.gray_code_representation}")
            lines.append(f"   状态质量: {gray.quality_score:.2f}/10")
            lines.append(f"   距离完美: {gray.evolution_distance} 步")
            lines.append("")

        # 八卦代数评估
        if result.trigram_scores:
            lines.append("☯️ 八卦代数评估:")
            lines.append("-" * 60)
            lines.append(f"{'八卦':<8} {'维度':<12} {'评分':<8} {'权重':<8}")
            lines.append("-" * 60)

            for trigram_name, score_info in result.trigram_scores.items():
                trigram_display = {
                    EightTrigrams.QIAN.value: "乾",
                    EightTrigrams.DUI.value: "兑",
                    EightTrigrams.LI.value: "离",
                    EightTrigrams.ZHEN.value: "震",
                    EightTrigrams.XUN.value: "巽",
                    EightTrigrams.KAN.value: "坎",
                    EightTrigrams.GEN.value: "艮",
                    EightTrigrams.KUN.value: "坤",
                }.get(trigram_name, trigram_name)

                dimension_mapping = {
                    EightTrigrams.QIAN.value: "正确性",
                    EightTrigrams.DUI.value: "复杂度",
                    EightTrigrams.LI.value: "风格",
                    EightTrigrams.ZHEN.value: "可读性",
                    EightTrigrams.XUN.value: "可维护性",
                    EightTrigrams.KAN.value: "性能",
                    EightTrigrams.GEN.value: "安全性",
                    EightTrigrams.KUN.value: "可靠性",
                }

                dim_name = dimension_mapping.get(trigram_name, "未知")

                lines.append(
                    f"{trigram_display:<8} {dim_name:<12} {score_info['score']:<8.2f} {score_info['weight']:<8.2f}"
                )

            lines.append("-" * 60)
            lines.append("")

        # 六十四卦分析
        if result.hexagram_result:
            hexagram = result.hexagram_result
            lines.append(f"䷾ 复合卦象分析:")
            lines.append(f"   卦序: {hexagram.hexagram_index} ({hexagram.combined_binary})")
            lines.append(
                f"   上卦: {hexagram.upper_trigram.value}，下卦: {hexagram.lower_trigram.value}"
            )
            lines.append(
                f"   上卦二进制: {hexagram.upper_binary}，下卦二进制: {hexagram.lower_binary}"
            )
            lines.append(f"   卦辞: {hexagram.interpretation}")
            lines.append(f"   总体质量: {hexagram.overall_quality:.2f}/10")
            lines.append("")

        # 改进建议
        if result.improvement_suggestions:
            lines.append("💡 质量改进建议:")
            for i, suggestion in enumerate(result.improvement_suggestions[:5], 1):
                lines.append(f"   {i}. {suggestion}")
            lines.append("")

        # 河图洛书状态
        if result.current_hetu_state:
            lines.append(f"🌀 评估流程状态: {result.current_hetu_state}")

        if result.task_schedule:
            lines.append(f"   任务调度路径: {' → '.join(result.task_schedule)}")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)


# 全局实例
_maref_quality_evaluator_instance = None


def get_maref_quality_evaluator(enable_advanced_features: bool = True) -> MarefQualityEvaluator:
    """获取全局MAREF质量评估器实例

    Args:
        enable_advanced_features: 是否启用高级功能（八卦评估等）
    """
    global _maref_quality_evaluator_instance
    if _maref_quality_evaluator_instance is None:
        _maref_quality_evaluator_instance = MarefQualityEvaluator(
            enable_advanced_features=enable_advanced_features
        )
        logger.info(f"🔧 创建MAREF质量评估器实例，高级功能: {enable_advanced_features}")
    else:
        # 如果实例已存在，检查参数是否匹配
        if _maref_quality_evaluator_instance.enable_advanced_features != enable_advanced_features:
            logger.warning(
                f"⚠️  MAREF质量评估器实例已存在，enable_advanced_features参数不匹配 "
                f"(现有: {_maref_quality_evaluator_instance.enable_advanced_features}, "
                f"请求: {enable_advanced_features})，返回现有实例"
            )
    return _maref_quality_evaluator_instance


if __name__ == "__main__":
    # 测试代码
    import logging

    logging.basicConfig(level=logging.INFO)

    print("🧪 测试MAREF质量评估器...")

    # 创建评估器实例
    evaluator = MarefQualityEvaluator(enable_advanced_features=True)

    # 测试代码示例
    test_code = '''
def fibonacci(n: int) -> int:
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

# 测试函数
def test_fibonacci():
    """测试斐波那契函数"""
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(5) == 5
    assert fibonacci(10) == 55
    print("所有测试通过！")
'''

    # 执行评估
    print("\n🔍 评估测试代码...")
    result = evaluator.assess_code_quality(
        code=test_code, context={"task_type": "algorithm_implementation", "difficulty": 3}
    )

    # 生成报告
    print("\n" + evaluator.generate_maref_report(result))

    print("\n✅ MAREF质量评估器测试完成")
    print(f"   综合评分: {result.overall_score:.2f}/10")

    # 显示八卦评分
    if result.trigram_scores:
        print("\n📈 八卦维度评分:")
        for trigram_name, score_info in result.trigram_scores.items():
            print(f"   {trigram_name}: {score_info['score']:.2f}")

    print("\n🎉 测试完成！")
