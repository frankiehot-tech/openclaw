#!/usr/bin/env python3
"""
八卦代数评估器
基于MAREF八卦代数理念的8维度质量评估系统

八卦映射：
- ☰ 乾 (111): 正确性 (correctness)
- ☱ 兑 (110): 复杂度 (complexity)
- ☲ 离 (101): 风格 (style)
- ☳ 震 (100): 可读性 (readability)
- ☴ 巽 (011): 可维护性 (maintainability)
- ☵ 坎 (010): 性能 (performance)
- ☶ 艮 (001): 安全性 (security)
- ☷ 坤 (000): 可靠性 (reliability)

六十四卦：两个八卦组合形成复合评估状态
"""

import json
import math
import typing as t
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EightTrigrams(Enum):
    """八卦枚举"""

    QIAN = "qian"  # ☰ 乾 (111): 正确性
    DUI = "dui"  # ☱ 兑 (110): 复杂度
    LI = "li"  # ☲ 离 (101): 风格
    ZHEN = "zhen"  # ☳ 震 (100): 可读性
    XUN = "xun"  # ☴ 巽 (011): 可维护性
    KAN = "kan"  # ☵ 坎 (010): 性能
    GEN = "gen"  # ☶ 艮 (001): 安全性
    KUN = "kun"  # ☷ 坤 (000): 可靠性


@dataclass
class TrigramInfo:
    """八卦信息"""

    name: str  # 八卦名称
    symbol: str  # 卦象符号
    binary: int  # 二进制表示 (0-7)
    dimension: str  # 对应评估维度
    base_weight: float  # 基础权重
    element: str  # 五行元素
    direction: str  # 方位
    attribute: str  # 属性


@dataclass
class TrigramAssessment:
    """八卦维度评估结果"""

    trigram: EightTrigrams  # 八卦
    dimension: str  # 评估维度
    score: float  # 评分 (0-10)
    weight: float  # 自适应权重
    binary_representation: str  # 二进制表示
    issues: t.List[str] = field(default_factory=list)  # 发现问题
    suggestions: t.List[str] = field(default_factory=list)  # 改进建议
    hexagram_contribution: float = 0.0  # 对六十四卦的贡献度


@dataclass
class HexagramResult:
    """六十四卦复合评估结果"""

    hexagram_index: int  # 卦序 (0-63)
    upper_trigram: EightTrigrams  # 上卦
    lower_trigram: EightTrigrams  # 下卦
    upper_binary: str  # 上卦二进制
    lower_binary: str  # 下卦二进制
    combined_binary: str  # 复合二进制
    interpretation: str  # 卦象解读
    overall_quality: float  # 总体质量评分
    strategic_implications: t.List[str] = field(default_factory=list)  # 战略含义


class EightTrigramsAssessor:
    """八卦代数评估器"""

    # 八卦定义表
    TRIGRAMS_INFO: t.Dict[EightTrigrams, TrigramInfo] = {
        EightTrigrams.QIAN: TrigramInfo(
            name="乾",
            symbol="☰",
            binary=0b111,  # 111
            dimension="correctness",
            base_weight=0.25,
            element="金",
            direction="西北",
            attribute="健",
        ),
        EightTrigrams.DUI: TrigramInfo(
            name="兑",
            symbol="☱",
            binary=0b110,  # 110
            dimension="complexity",
            base_weight=0.15,
            element="金",
            direction="西",
            attribute="悦",
        ),
        EightTrigrams.LI: TrigramInfo(
            name="离",
            symbol="☲",
            binary=0b101,  # 101
            dimension="style",
            base_weight=0.10,
            element="火",
            direction="南",
            attribute="丽",
        ),
        EightTrigrams.ZHEN: TrigramInfo(
            name="震",
            symbol="☳",
            binary=0b100,  # 100
            dimension="readability",
            base_weight=0.15,
            element="木",
            direction="东",
            attribute="动",
        ),
        EightTrigrams.XUN: TrigramInfo(
            name="巽",
            symbol="☴",
            binary=0b011,  # 011
            dimension="maintainability",
            base_weight=0.15,
            element="木",
            direction="东南",
            attribute="入",
        ),
        EightTrigrams.KAN: TrigramInfo(
            name="坎",
            symbol="☵",
            binary=0b010,  # 010
            dimension="performance",
            base_weight=0.10,
            element="水",
            direction="北",
            attribute="陷",
        ),
        EightTrigrams.GEN: TrigramInfo(
            name="艮",
            symbol="☶",
            binary=0b001,  # 001
            dimension="security",
            base_weight=0.05,
            element="土",
            direction="东北",
            attribute="止",
        ),
        EightTrigrams.KUN: TrigramInfo(
            name="坤",
            symbol="☷",
            binary=0b000,  # 000
            dimension="reliability",
            base_weight=0.05,
            element="土",
            direction="西南",
            attribute="顺",
        ),
    }

    # 六十四卦解读数据库（简化版）
    HEXAGRAM_INTERPRETATIONS = {
        # 乾为天 (111-111): 完美代码
        0o77: "䷀ 乾为天：代码完美，所有维度优秀。象征创造力、领导力和卓越质量。",
        # 坤为地 (000-000): 极差代码
        0o00: "䷁ 坤为地：代码质量极差，所有维度都需要改进。象征基础薄弱，需要重建。",
        # 水雷屯 (010-100): 性能好但可读性差
        0o24: "䷂ 水雷屯：性能优秀但可读性不足。象征初创艰难，需要改进文档和注释。",
        # 山水蒙 (001-010): 安全好但性能中等
        0o12: "䷃ 山水蒙：安全性好但性能中等。象征启蒙阶段，需要性能优化。",
        # 水天需 (010-111): 性能好且正确性优秀
        0o27: "䷄ 水天需：性能优秀且正确性高。象征等待时机，只需微调。",
        # 天水讼 (111-010): 正确性高但性能差
        0o72: "䷅ 天水讼：正确性高但性能差。象征争议，需要在性能和质量间权衡。",
        # 地水师 (000-010): 可靠性差但性能中等
        0o02: "䷆ 地水师：可靠性不足但性能可接受。象征团队协作，需要加强测试。",
        # 水地比 (010-000): 性能好但可靠性差
        0o20: "䷇ 水地比：性能优秀但可靠性差。象征亲密合作，需要提高容错性。",
        # 风天小畜 (011-111): 可维护性好且正确性高
        0o37: "䷈ 风天小畜：可维护性优秀且正确性高。象征小有积蓄，接近完美。",
        # 天泽履 (111-110): 正确性高但复杂度高
        0o76: "䷉ 天泽履：正确性高但复杂度高。象征履行责任，需要简化代码。",
    }

    def __init__(self, adaptive_weights: bool = True):
        self.adaptive_weights = adaptive_weights
        self.context_factors: t.Dict[str, float] = {}

        print("🔮 八卦代数评估器初始化完成")
        print("   八卦映射:")
        for trigram, info in self.TRIGRAMS_INFO.items():
            print(f"     {info.symbol} {info.name}: {info.dimension} (权重: {info.base_weight})")

    def assess_with_trigrams(
        self, code_analysis: dict, context: dict
    ) -> t.Dict[str, TrigramAssessment]:
        """使用八卦代数进行评估"""
        results = {}

        # 分析上下文因素
        self._analyze_context_factors(context)

        for trigram, trigram_info in self.TRIGRAMS_INFO.items():
            dimension = trigram_info.dimension

            # 自适应权重调整
            adaptive_weight = self._adjust_weight_by_context(
                trigram_info.base_weight, dimension, context
            )

            # 执行维度评估
            dimension_score = self._assess_dimension(dimension, code_analysis, context)

            # 应用八卦变换（二进制能量注入）
            transformed_score = self._apply_trigram_transform(dimension_score, trigram_info.binary)

            # 生成问题和建议
            issues, suggestions = self._generate_dimension_feedback(
                dimension, transformed_score, context
            )

            # 计算对六十四卦的贡献度
            hexagram_contribution = self._calculate_hexagram_contribution(
                trigram_info.binary, transformed_score
            )

            assessment = TrigramAssessment(
                trigram=trigram,
                dimension=dimension,
                score=transformed_score,
                weight=adaptive_weight,
                binary_representation=bin(trigram_info.binary)[2:].zfill(3),
                issues=issues,
                suggestions=suggestions,
                hexagram_contribution=hexagram_contribution,
            )

            results[dimension] = assessment

        return results

    def combine_trigrams(
        self,
        upper_trigram: EightTrigrams,
        lower_trigram: EightTrigrams,
        assessments: t.Dict[str, TrigramAssessment],
    ) -> HexagramResult:
        """组合上下卦形成六十四卦复合评估"""
        upper_info = self.TRIGRAMS_INFO[upper_trigram]
        lower_info = self.TRIGRAMS_INFO[lower_trigram]

        # 计算复合卦象
        hexagram_binary = (upper_info.binary << 3) | lower_info.binary
        hexagram_index = hexagram_binary  # 0-63

        # 二进制表示
        upper_binary = bin(upper_info.binary)[2:].zfill(3)
        lower_binary = bin(lower_info.binary)[2:].zfill(3)
        combined_binary = bin(hexagram_binary)[2:].zfill(6)

        # 卦象解读
        interpretation = self._interpret_hexagram(hexagram_index)

        # 计算总体质量评分（加权平均）
        overall_quality = self._calculate_overall_quality(assessments)

        # 生成战略含义
        strategic_implications = self._generate_strategic_implications(
            upper_trigram, lower_trigram, assessments, overall_quality
        )

        return HexagramResult(
            hexagram_index=hexagram_index,
            upper_trigram=upper_trigram,
            lower_trigram=lower_trigram,
            upper_binary=upper_binary,
            lower_binary=lower_binary,
            combined_binary=combined_binary,
            interpretation=interpretation,
            overall_quality=overall_quality,
            strategic_implications=strategic_implications,
        )

    def find_optimal_trigram_pair(
        self, assessments: t.Dict[str, TrigramAssessment]
    ) -> t.Tuple[EightTrigrams, EightTrigrams]:
        """寻找最优的八卦组合（基于当前评估结果）"""
        # 根据评分选择上卦（宏观特性）
        upper_candidates = self._select_upper_trigram_candidates(assessments)

        # 根据评分选择下卦（微观特性）
        lower_candidates = self._select_lower_trigram_candidates(assessments)

        # 选择最佳组合（基于互补原则）
        best_pair = None
        best_score = -1

        for upper in upper_candidates:
            for lower in lower_candidates:
                # 计算组合评分
                pair_score = self._evaluate_trigram_pair(upper, lower, assessments)

                if pair_score > best_score:
                    best_score = pair_score
                    best_pair = (upper, lower)

        return best_pair or (EightTrigrams.QIAN, EightTrigrams.KUN)

    def generate_evolution_advice(
        self, current_assessments: t.Dict[str, TrigramAssessment], target_hexagram: HexagramResult
    ) -> t.List[str]:
        """生成演化建议（从当前状态到目标卦象）"""
        advice = []

        # 获取当前最优八卦组合
        current_upper, current_lower = self.find_optimal_trigram_pair(current_assessments)

        # 分析差异
        upper_changed = current_upper != target_hexagram.upper_trigram
        lower_changed = current_lower != target_hexagram.lower_trigram

        if upper_changed:
            current_upper_info = self.TRIGRAMS_INFO[current_upper]
            target_upper_info = self.TRIGRAMS_INFO[target_hexagram.upper_trigram]

            advice.append(f"上卦变化: {current_upper_info.name} → {target_upper_info.name}")
            advice.append(
                f"  宏观策略: {self._get_trigram_transition_advice(current_upper, target_hexagram.upper_trigram)}"
            )

        if lower_changed:
            current_lower_info = self.TRIGRAMS_INFO[current_lower]
            target_lower_info = self.TRIGRAMS_INFO[target_hexagram.lower_trigram]

            advice.append(f"下卦变化: {current_lower_info.name} → {target_lower_info.name}")
            advice.append(
                f"  微观策略: {self._get_trigram_transition_advice(current_lower, target_hexagram.lower_trigram)}"
            )

        # 如果没有变化
        if not upper_changed and not lower_changed:
            advice.append("当前八卦组合已是最优，保持即可")

        # 添加总体建议
        advice.extend(
            self._generate_quality_improvement_advice(
                current_assessments, target_hexagram.overall_quality
            )
        )

        return advice

    def _analyze_context_factors(self, context: dict):
        """分析上下文因素"""
        self.context_factors = {
            "task_type_priority": context.get("task_type_priority", 1.0),
            "time_constraint": context.get("time_constraint", 1.0),
            "quality_requirement": context.get("quality_requirement", 1.0),
            "team_experience": context.get("team_experience", 1.0),
            "project_criticality": context.get("project_criticality", 1.0),
        }

    def _adjust_weight_by_context(self, base_weight: float, dimension: str, context: dict) -> float:
        """根据上下文调整权重"""
        if not self.adaptive_weights:
            return base_weight

        adjustment = 1.0

        # 根据任务类型调整
        task_type = context.get("task_type", "general")
        if dimension == "correctness" and task_type in ["algorithm", "math"]:
            adjustment *= 1.3
        elif dimension == "readability" and task_type == "string":
            adjustment *= 1.2
        elif dimension == "maintainability" and task_type == "data_structure":
            adjustment *= 1.2
        elif dimension == "performance" and task_type in ["algorithm", "data_structure"]:
            adjustment *= 1.1

        # 根据项目关键性调整
        project_criticality = context.get("project_criticality", 1.0)
        if dimension in ["security", "reliability"] and project_criticality > 1.0:
            adjustment *= 1.0 + (project_criticality - 1.0) * 0.5

        # 根据团队经验调整
        team_experience = context.get("team_experience", 1.0)
        if dimension in ["style", "readability"] and team_experience < 1.0:
            adjustment *= 1.2  # 新手团队更需要规范和可读性

        return min(1.0, base_weight * adjustment)  # 确保权重不超过1.0

    def _assess_dimension(self, dimension: str, code_analysis: dict, context: dict) -> float:
        """评估单个维度"""
        # 这里应该调用具体的评估逻辑
        # 简化实现：基于code_analysis计算评分

        score_mapping = {
            "correctness": self._assess_correctness,
            "complexity": self._assess_complexity,
            "style": self._assess_style,
            "readability": self._assess_readability,
            "maintainability": self._assess_maintainability,
            "performance": self._assess_performance,
            "security": self._assess_security,
            "reliability": self._assess_reliability,
        }

        assessor = score_mapping.get(dimension, lambda *args: 5.0)
        return assessor(code_analysis, context)

    def _apply_trigram_transform(self, base_score: float, trigram_binary: int) -> float:
        """应用八卦变换（二进制能量注入）"""
        # 八卦的二进制位影响评分
        binary_str = bin(trigram_binary)[2:].zfill(3)

        # 计算二进制能量（1的数量）
        binary_energy = binary_str.count("1") / 3.0  # 0.0 到 1.0

        # 应用变换：高能量八卦提升评分
        transformed = base_score * (0.7 + 0.3 * binary_energy)

        # 确保在0-10范围内
        return max(0.0, min(10.0, transformed))

    def _generate_dimension_feedback(
        self, dimension: str, score: float, context: dict
    ) -> t.Tuple[t.List[str], t.List[str]]:
        """生成维度反馈（问题和建议）"""
        issues = []
        suggestions = []

        if score < 6.0:
            issues.append(f"{dimension}评分不足 ({score:.1f}/10)")

            # 维度特定建议
            suggestion_map = {
                "correctness": ["增加测试用例", "修复边界条件错误", "验证输入输出"],
                "complexity": ["降低圈复杂度", "拆分大型函数", "减少嵌套层次"],
                "style": ["遵循PEP8规范", "统一命名约定", "添加类型注解"],
                "readability": ["添加函数文档", "改善变量命名", "减少魔法数字"],
                "maintainability": ["提高模块化", "减少耦合", "添加配置管理"],
                "performance": ["优化算法复杂度", "减少内存分配", "使用缓存"],
                "security": ["验证输入数据", "防止注入攻击", "加密敏感数据"],
                "reliability": ["添加错误处理", "实现重试机制", "增加日志记录"],
            }

            suggestions.extend(suggestion_map.get(dimension, ["改进代码质量"]))

        elif score < 8.0:
            suggestions.append(f"{dimension}良好，仍有改进空间")

        else:
            suggestions.append(f"{dimension}优秀，继续保持")

        return issues, suggestions

    def _calculate_hexagram_contribution(self, trigram_binary: int, score: float) -> float:
        """计算对六十四卦的贡献度"""
        # 二进制能量 * 评分比例
        binary_energy = bin(trigram_binary).count("1") / 3.0
        score_ratio = score / 10.0

        return binary_energy * score_ratio

    def _interpret_hexagram(self, hexagram_index: int) -> str:
        """解读六十四卦"""
        # 查找预定义解读
        interpretation = self.HEXAGRAM_INTERPRETATIONS.get(hexagram_index)

        if interpretation:
            return interpretation

        # 动态生成解读
        upper_binary = (hexagram_index >> 3) & 0b111
        lower_binary = hexagram_index & 0b111

        upper_energy = bin(upper_binary).count("1") / 3.0
        lower_energy = bin(lower_binary).count("1") / 3.0

        if upper_energy > 0.8 and lower_energy > 0.8:
            return f"䷊ 卦象 {hexagram_index:02o}: 代码质量优秀，上下卦能量充沛。"
        elif upper_energy < 0.3 and lower_energy < 0.3:
            return f"䷋ 卦象 {hexagram_index:02o}: 代码质量较差，需要全面提升。"
        elif upper_energy > lower_energy:
            return f"䷌ 卦象 {hexagram_index:02o}: 宏观质量优于微观实现，需要关注细节。"
        else:
            return f"䷍ 卦象 {hexagram_index:02o}: 微观实现扎实，但宏观架构有待改进。"

    def _calculate_overall_quality(self, assessments: t.Dict[str, TrigramAssessment]) -> float:
        """计算总体质量评分（加权平均）"""
        total_weight = 0.0
        weighted_sum = 0.0

        for assessment in assessments.values():
            weighted_sum += assessment.score * assessment.weight
            total_weight += assessment.weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def _generate_strategic_implications(
        self,
        upper_trigram: EightTrigrams,
        lower_trigram: EightTrigrams,
        assessments: t.Dict[str, TrigramAssessment],
        overall_quality: float,
    ) -> t.List[str]:
        """生成战略含义"""
        implications = []

        upper_info = self.TRIGRAMS_INFO[upper_trigram]
        lower_info = self.TRIGRAMS_INFO[lower_trigram]

        # 基于上下卦组合
        combo_advice = {
            (EightTrigrams.QIAN, EightTrigrams.QIAN): "追求卓越，设定最高质量标准",
            (EightTrigrams.KUN, EightTrigrams.KUN): "夯实基础，从最基本的质量维度开始改进",
            (EightTrigrams.QIAN, EightTrigrams.KUN): "宏观高标准，微观求稳健",
            (EightTrigrams.KUN, EightTrigrams.QIAN): "微观扎实，宏观逐步提升",
        }

        advice = combo_advice.get((upper_trigram, lower_trigram))
        if advice:
            implications.append(advice)

        # 基于总体质量
        if overall_quality >= 8.0:
            implications.append("质量优秀，可考虑分享最佳实践")
        elif overall_quality >= 7.0:
            implications.append("质量良好，关注最弱维度的改进")
        elif overall_quality >= 6.0:
            implications.append("质量达标，需要系统性质量提升计划")
        else:
            implications.append("质量不足，需要立即进行代码重构和质量培训")

        return implications

    def _select_upper_trigram_candidates(
        self, assessments: t.Dict[str, TrigramAssessment]
    ) -> t.List[EightTrigrams]:
        """选择上卦候选（基于宏观维度评分）"""
        # 上卦关注宏观特性：正确性、可维护性、可靠性
        macro_dimensions = ["correctness", "maintainability", "reliability"]
        candidate_scores = []

        for trigram, info in self.TRIGRAMS_INFO.items():
            if info.dimension in macro_dimensions:
                assessment = assessments.get(info.dimension)
                if assessment:
                    score = assessment.score * assessment.weight
                    candidate_scores.append((trigram, score))

        # 按评分排序，取前3名
        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        return [trigram for trigram, _ in candidate_scores[:3]]

    def _select_lower_trigram_candidates(
        self, assessments: t.Dict[str, TrigramAssessment]
    ) -> t.List[EightTrigrams]:
        """选择下卦候选（基于微观维度评分）"""
        # 下卦关注微观特性：风格、可读性、复杂度
        micro_dimensions = ["style", "readability", "complexity"]
        candidate_scores = []

        for trigram, info in self.TRIGRAMS_INFO.items():
            if info.dimension in micro_dimensions:
                assessment = assessments.get(info.dimension)
                if assessment:
                    score = assessment.score * assessment.weight
                    candidate_scores.append((trigram, score))

        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        return [trigram for trigram, _ in candidate_scores[:3]]

    def _evaluate_trigram_pair(
        self,
        upper: EightTrigrams,
        lower: EightTrigrams,
        assessments: t.Dict[str, TrigramAssessment],
    ) -> float:
        """评估八卦组合的得分"""
        upper_info = self.TRIGRAMS_INFO[upper]
        lower_info = self.TRIGRAMS_INFO[lower]

        # 获取维度评分
        upper_assessment = assessments.get(upper_info.dimension)
        lower_assessment = assessments.get(lower_info.dimension)

        upper_score = upper_assessment.score if upper_assessment else 5.0
        lower_score = lower_assessment.score if lower_assessment else 5.0

        # 组合评分：加权平均 + 互补加成
        base_score = upper_score * 0.6 + lower_score * 0.4

        # 互补加成：上下卦二进制差异适当
        upper_binary = upper_info.binary
        lower_binary = lower_info.binary

        # 计算汉明距离
        hamming_distance = bin(upper_binary ^ lower_binary).count("1")

        # 理想距离：2-4（既不完全相同也不完全相反）
        distance_score = 1.0 - abs(hamming_distance - 3) / 3.0

        return base_score * (0.8 + 0.2 * distance_score)

    def _get_trigram_transition_advice(
        self, from_trigram: EightTrigrams, to_trigram: EightTrigrams
    ) -> str:
        """获取八卦转换建议"""
        from_info = self.TRIGRAMS_INFO[from_trigram]
        to_info = self.TRIGRAMS_INFO[to_trigram]

        advice_map = {
            (EightTrigrams.KUN, EightTrigrams.QIAN): "从坤到乾：需要全面提升所有质量维度",
            (
                EightTrigrams.QIAN,
                EightTrigrams.KUN,
            ): "从乾到坤：过于追求完美，可以适当降低次要维度的要求",
            (EightTrigrams.GEN, EightTrigrams.LI): "从艮到离：加强代码风格规范",
            (EightTrigrams.KAN, EightTrigrams.ZHEN): "从坎到震：提高代码可读性和文档质量",
            (EightTrigrams.DUI, EightTrigrams.XUN): "从兑到巽：降低复杂度以提高可维护性",
        }

        return advice_map.get(
            (from_trigram, to_trigram),
            f"从{from_info.name}到{to_info.name}：关注{to_info.dimension}维度的改进",
        )

    def _generate_quality_improvement_advice(
        self, assessments: t.Dict[str, TrigramAssessment], target_quality: float
    ) -> t.List[str]:
        """生成质量改进建议"""
        advice = []

        # 找出最弱的维度
        weak_dimensions = []
        for dimension, assessment in assessments.items():
            if assessment.score < 6.0:
                weak_dimensions.append((dimension, assessment.score))

        if weak_dimensions:
            weak_dimensions.sort(key=lambda x: x[1])  # 按评分排序
            weakest = weak_dimensions[0][0]
            advice.append(f"最需要改进的维度: {weakest}")

        # 基于目标质量给出建议
        if target_quality > 8.0:
            advice.append("目标为高质量代码，建议进行全面代码审查和重构")
        elif target_quality > 7.0:
            advice.append("目标为良好质量，重点关注最弱3个维度的改进")
        else:
            advice.append("目标为基础质量，确保所有维度达到最低标准")

        return advice

    # 简化的维度评估函数（实际应该调用具体的评估逻辑）
    def _assess_correctness(self, code_analysis: dict, context: dict) -> float:
        """评估正确性"""
        # 简化实现
        return code_analysis.get("test_coverage", 0.5) * 10

    def _assess_complexity(self, code_analysis: dict, context: dict) -> float:
        """评估复杂度"""
        complexity = code_analysis.get("cyclomatic_complexity", 5)
        return max(0, 10 - complexity / 2)

    def _assess_style(self, code_analysis: dict, context: dict) -> float:
        """评估风格"""
        return code_analysis.get("style_score", 7.0)

    def _assess_readability(self, code_analysis: dict, context: dict) -> float:
        """评估可读性"""
        comment_ratio = code_analysis.get("comment_ratio", 0.1)
        return min(10, comment_ratio * 100)

    def _assess_maintainability(self, code_analysis: dict, context: dict) -> float:
        """评估可维护性"""
        return code_analysis.get("maintainability_index", 6.5)

    def _assess_performance(self, code_analysis: dict, context: dict) -> float:
        """评估性能"""
        return code_analysis.get("performance_score", 7.0)

    def _assess_security(self, code_analysis: dict, context: dict) -> float:
        """评估安全性"""
        return code_analysis.get("security_score", 8.0)

    def _assess_reliability(self, code_analysis: dict, context: dict) -> float:
        """评估可靠性"""
        return code_analysis.get("reliability_score", 7.5)


# 使用示例
if __name__ == "__main__":
    print("🔮 八卦代数评估器演示")
    print("=" * 60)

    # 创建评估器
    assessor = EightTrigramsAssessor(adaptive_weights=True)

    # 模拟代码分析结果
    code_analysis = {
        "test_coverage": 0.85,
        "cyclomatic_complexity": 8,
        "style_score": 8.5,
        "comment_ratio": 0.15,
        "maintainability_index": 7.8,
        "performance_score": 7.2,
        "security_score": 9.0,
        "reliability_score": 8.2,
    }

    # 评估上下文
    context = {
        "task_type": "algorithm",
        "project_criticality": 1.2,
        "team_experience": 0.9,
        "time_constraint": 0.8,
    }

    print("\n📊 执行八卦代数评估...")
    assessments = assessor.assess_with_trigrams(code_analysis, context)

    print(f"\n📈 维度评估结果:")
    for dimension, assessment in assessments.items():
        status = "✅" if assessment.score >= 7.0 else "⚠️ " if assessment.score >= 6.0 else "❌"
        print(f"   {status} {dimension}: {assessment.score:.2f}/10 (权重: {assessment.weight:.3f})")

    # 寻找最优八卦组合
    print(f"\n🔍 寻找最优八卦组合...")
    upper, lower = assessor.find_optimal_trigram_pair(assessments)
    upper_info = assessor.TRIGRAMS_INFO[upper]
    lower_info = assessor.TRIGRAMS_INFO[lower]

    print(f"   上卦（宏观）: {upper_info.symbol} {upper_info.name} - {upper_info.dimension}")
    print(f"   下卦（微观）: {lower_info.symbol} {lower_info.name} - {lower_info.dimension}")

    # 生成六十四卦复合评估
    print(f"\n🔄 生成六十四卦复合评估...")
    hexagram_result = assessor.combine_trigrams(upper, lower, assessments)

    print(f"   卦序: {hexagram_result.hexagram_index:02o} ({hexagram_result.hexagram_index})")
    print(f"   二进制: {hexagram_result.upper_binary}-{hexagram_result.lower_binary}")
    print(f"   复合: {hexagram_result.combined_binary}")
    print(f"   总体质量: {hexagram_result.overall_quality:.2f}/10")

    print(f"\n📖 卦象解读:")
    print(f"   {hexagram_result.interpretation}")

    print(f"\n🎯 战略含义:")
    for implication in hexagram_result.strategic_implications:
        print(f"   • {implication}")

    # 生成演化建议
    print(f"\n💡 演化建议（向乾为天 ⚌ 发展）:")
    target_hexagram = HexagramResult(
        hexagram_index=0o77,  # 乾为天
        upper_trigram=EightTrigrams.QIAN,
        lower_trigram=EightTrigrams.QIAN,
        upper_binary="111",
        lower_binary="111",
        combined_binary="111111",
        interpretation="完美代码状态",
        overall_quality=9.5,
    )

    advice = assessor.generate_evolution_advice(assessments, target_hexagram)
    for item in advice[:5]:  # 显示前5条建议
        print(f"   {item}")

    # 显示八卦权重分布
    print(f"\n⚖️  八卦权重分布:")
    total_weight = sum(info.base_weight for info in assessor.TRIGRAMS_INFO.values())
    for trigram, info in assessor.TRIGRAMS_INFO.items():
        percentage = info.base_weight / total_weight * 100
        print(f"   {info.symbol} {info.name}: {percentage:.1f}%")

    print(f"\n🎉 演示完成！")
    print(f"   八卦代数评估为代码质量提供了文化和数学的双重视角")
