#!/usr/bin/env python3
"""
三才评估引擎
基于MAREF三才六层模型的天、地、人三层评估架构

天层：宏观质量分析（质量趋势预测、质量策略制定、质量标准定义）
地层：中观维度聚合（任务级评估、维度级聚合）
人层：微观代码评估（代码级分析、AST解析、复杂度计算）
"""

import json
import typing as t
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# 导入现有质量评估组件
try:
    from agent.core.quality_assessment import (
        CodeQualityAssessment,
        CodeQualityAssessor,
        PythonASTAnalyzer,
        QualityDimension,
    )
    from agent.core.test_cases_library import TestCaseLibrary
except ImportError:
    # 回退到直接导入
    import os
    import sys

    project_root = "/Volumes/1TB-M2/openclaw"
    sys.path.insert(0, project_root)
    sys.path.insert(0, os.path.join(project_root, "mini-agent"))
    from agent.core.quality_assessment import (
        CodeQualityAssessment,
        CodeQualityAssessor,
        PythonASTAnalyzer,
        QualityDimension,
    )
    from agent.core.test_cases_library import TestCaseLibrary


class TalentLayer(Enum):
    """三才层级枚举"""

    HEAVEN = "heaven"  # 天层：宏观质量
    EARTH = "earth"  # 地层：中观维度
    HUMAN = "human"  # 人层：微观代码


class HeavenFunction(Enum):
    """天层功能枚举（对应爻、别、经）"""

    TREND_PREDICTION = "trend_prediction"  # 爻：质量趋势预测
    STRATEGY_FORMULATION = "strategy_formulation"  # 别：质量策略制定
    STANDARD_DEFINITION = "standard_definition"  # 经：质量标准定义


class EarthFunction(Enum):
    """地层功能枚举（对应天、地、人）"""

    TASK_ASSESSMENT = "task_assessment"  # 天：任务级评估
    DIMENSION_AGGREGATION = "dimension_aggregation"  # 地：维度级聚合
    CODE_LEVEL_ANALYSIS = "code_level_analysis"  # 人：代码级分析


@dataclass
class HumanLayerResult:
    """人层评估结果（微观代码级）"""

    ast_analysis: dict  # AST解析结果
    complexity_metrics: dict  # 复杂度指标
    function_count: int  # 函数数量
    class_count: int  # 类数量
    line_counts: dict  # 行数统计
    issues: t.List[str] = field(default_factory=list)  # 发现问题
    suggestions: t.List[str] = field(default_factory=list)  # 改进建议


@dataclass
class EarthLayerResult:
    """地层评估结果（中观维度级）"""

    dimension_scores: dict  # 各维度评分
    overall_score: float  # 总体评分
    dimension_issues: t.Dict[str, t.List[str]] = field(default_factory=dict)  # 各维度问题
    dimension_suggestions: t.Dict[str, t.List[str]] = field(default_factory=dict)  # 各维度建议
    task_context: dict = field(default_factory=dict)  # 任务上下文


@dataclass
class HeavenLayerResult:
    """天层评估结果（宏观质量）"""

    quality_trend: t.Dict[str, float]  # 质量趋势预测
    quality_strategy: dict  # 质量策略建议
    quality_standards: dict  # 质量标准定义
    cost_quality_ratio: float  # 成本质量比
    improvement_priority: t.List[str]  # 改进优先级
    strategic_recommendations: t.List[str] = field(default_factory=list)  # 战略建议


@dataclass
class ThreeTalentResult:
    """三才评估完整结果"""

    human_result: HumanLayerResult  # 人层结果
    earth_result: EarthLayerResult  # 地层结果
    heaven_result: HeavenLayerResult  # 天层结果
    timestamp: datetime = field(default_factory=datetime.now)
    task_id: t.Optional[str] = None
    code_hash: t.Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "code_hash": self.code_hash,
            "timestamp": self.timestamp.isoformat(),
            "human_layer": {
                "ast_analysis": self.human_result.ast_analysis,
                "complexity_metrics": self.human_result.complexity_metrics,
                "function_count": self.human_result.function_count,
                "class_count": self.human_result.class_count,
                "line_counts": self.human_result.line_counts,
                "issues": self.human_result.issues,
                "suggestions": self.human_result.suggestions,
            },
            "earth_layer": {
                "dimension_scores": self.earth_result.dimension_scores,
                "overall_score": self.earth_result.overall_score,
                "dimension_issues": self.earth_result.dimension_issues,
                "dimension_suggestions": self.earth_result.dimension_suggestions,
                "task_context": self.earth_result.task_context,
            },
            "heaven_layer": {
                "quality_trend": self.heaven_result.quality_trend,
                "quality_strategy": self.heaven_result.quality_strategy,
                "quality_standards": self.heaven_result.quality_standards,
                "cost_quality_ratio": self.heaven_result.cost_quality_ratio,
                "improvement_priority": self.heaven_result.improvement_priority,
                "strategic_recommendations": self.heaven_result.strategic_recommendations,
            },
        }

    def save_to_json(self, filepath: t.Union[str, Path]):
        """保存为JSON文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


class HumanLayerAssessor:
    """人层评估器（微观代码级）"""

    def __init__(self):
        self.ast_analyzer = PythonASTAnalyzer()
        self.quality_assessor = CodeQualityAssessor()

    def assess_code(self, code: str, language: str = "python") -> HumanLayerResult:
        """评估代码（微观层面）"""
        # AST分析
        ast_analysis = self.ast_analyzer.analyze(code)

        if not ast_analysis["valid"]:
            # 无效代码，返回基础结果
            return HumanLayerResult(
                ast_analysis=ast_analysis,
                complexity_metrics={"cyclomatic_complexity": 0, "cognitive_complexity": 0},
                function_count=0,
                class_count=0,
                line_counts={"total": 0, "code": 0, "comment": 0, "blank": 0},
                issues=[
                    (
                        "代码语法无效: " + ast_analysis["issues"][0]
                        if ast_analysis["issues"]
                        else "代码语法无效"
                    )
                ],
                suggestions=["修复语法错误"],
            )

        # 提取复杂度指标
        complexity_metrics = ast_analysis.get("complexity_metrics", {})

        # 提取函数和类数量
        function_count = len(ast_analysis.get("functions", []))
        class_count = len(ast_analysis.get("classes", []))

        # 行数统计
        line_counts = ast_analysis.get(
            "line_count", {"total": 0, "code": 0, "comment": 0, "blank": 0}
        )

        # 基础问题检测
        issues = []
        suggestions = []

        if function_count == 0 and class_count == 0:
            issues.append("代码缺少可执行函数或类")
            suggestions.append("添加至少一个函数或类")

        if line_counts.get("total", 0) > 500:
            issues.append("代码文件过长，考虑拆分")
            suggestions.append("将代码拆分为多个模块")

        return HumanLayerResult(
            ast_analysis=ast_analysis,
            complexity_metrics=complexity_metrics,
            function_count=function_count,
            class_count=class_count,
            line_counts=line_counts,
            issues=issues,
            suggestions=suggestions,
        )


class EarthLayerAssessor:
    """地层评估器（中观维度级）"""

    def __init__(self):
        self.quality_assessor = CodeQualityAssessor()
        self.test_case_library = TestCaseLibrary()

    def aggregate_dimensions(
        self, human_result: HumanLayerResult, code: str = "", test_cases: t.Optional[list] = None
    ) -> EarthLayerResult:
        """聚合各维度评分（中观层面）"""
        if not code and not test_cases:
            # 如果没有代码，返回基础维度评分
            dimension_scores = {
                QualityDimension.CORRECTNESS.value: 5.0,
                QualityDimension.COMPLEXITY.value: 5.0,
                QualityDimension.STYLE.value: 5.0,
                QualityDimension.READABILITY.value: 5.0,
                QualityDimension.MAINTAINABILITY.value: 5.0,
            }

            return EarthLayerResult(
                dimension_scores=dimension_scores,
                overall_score=5.0,
                dimension_issues={},
                dimension_suggestions={},
            )

        # 使用现有质量评估器
        assessment = self.quality_assessor.assess_code_quality(code, test_cases=test_cases)

        # 提取维度评分
        dimension_scores = {}
        dimension_issues = {}
        dimension_suggestions = {}

        for dim_score in assessment.dimension_scores.values():
            dimension_scores[dim_score.dimension] = dim_score.score
            dimension_issues[dim_score.dimension] = dim_score.issues
            dimension_suggestions[dim_score.dimension] = dim_score.suggestions

        # 构建任务上下文
        task_context = {
            "code_length": human_result.line_counts.get("total", 0),
            "function_count": human_result.function_count,
            "class_count": human_result.class_count,
            "complexity": human_result.complexity_metrics.get("cyclomatic_complexity", 0),
        }

        return EarthLayerResult(
            dimension_scores=dimension_scores,
            overall_score=assessment.overall_score,
            dimension_issues=dimension_issues,
            dimension_suggestions=dimension_suggestions,
            task_context=task_context,
        )


class HeavenLayerAssessor:
    """天层评估器（宏观质量）"""

    def __init__(self, historical_data: t.Optional[dict] = None):
        self.historical_data = historical_data or {}

    def analyze_macro(self, earth_result: EarthLayerResult, context: dict) -> HeavenLayerResult:
        """宏观质量分析（天层面）"""

        # 质量趋势预测
        quality_trend = self._predict_quality_trend(earth_result, context)

        # 质量策略制定
        quality_strategy = self._formulate_quality_strategy(earth_result, context)

        # 质量标准定义
        quality_standards = self._define_quality_standards(earth_result, context)

        # 成本质量比计算（如果有成本数据）
        cost_quality_ratio = self._calculate_cost_quality_ratio(earth_result, context)

        # 改进优先级
        improvement_priority = self._determine_improvement_priority(earth_result)

        return HeavenLayerResult(
            quality_trend=quality_trend,
            quality_strategy=quality_strategy,
            quality_standards=quality_standards,
            cost_quality_ratio=cost_quality_ratio,
            improvement_priority=improvement_priority,
            strategic_recommendations=self._generate_strategic_recommendations(earth_result),
        )

    def _predict_quality_trend(
        self, earth_result: EarthLayerResult, context: dict
    ) -> t.Dict[str, float]:
        """预测质量趋势"""
        # 简化的趋势预测：基于当前评分和历史数据
        current_score = earth_result.overall_score

        # 如果没有历史数据，返回平稳预测
        if not self.historical_data:
            return {"next_week": current_score, "next_month": current_score, "trend": "stable"}

        # 简单线性外推（实际应用中应该使用更复杂的模型）
        historical_scores = list(self.historical_data.values())
        if len(historical_scores) >= 2:
            recent_trend = historical_scores[-1] - historical_scores[-2]
            next_week = current_score + recent_trend
            next_month = current_score + recent_trend * 4
        else:
            next_week = current_score
            next_month = current_score

        return {
            "next_week": max(0, min(10, next_week)),
            "next_month": max(0, min(10, next_month)),
            "trend": (
                "improving"
                if next_week > current_score
                else "declining" if next_week < current_score else "stable"
            ),
        }

    def _formulate_quality_strategy(self, earth_result: EarthLayerResult, context: dict) -> dict:
        """制定质量策略"""
        dimension_scores = earth_result.dimension_scores

        # 识别最弱维度
        weakest_dimension = min(dimension_scores.items(), key=lambda x: x[1])
        strongest_dimension = max(dimension_scores.items(), key=lambda x: x[1])

        # 根据弱点制定策略
        strategies = {
            "focus_area": weakest_dimension[0],
            "leverage_area": strongest_dimension[0],
            "priority": (
                "correctness"
                if weakest_dimension[0] == QualityDimension.CORRECTNESS.value
                else "maintainability"
            ),
            "effort_distribution": self._calculate_effort_distribution(dimension_scores),
        }

        return strategies

    def _define_quality_standards(self, earth_result: EarthLayerResult, context: dict) -> dict:
        """定义质量标准"""
        task_type = context.get("task_type", "general")
        difficulty = context.get("difficulty", "medium")

        # 根据任务类型和难度定义标准
        standards = {
            "minimum_score": {
                "beginner": 6.0,
                "easy": 7.0,
                "medium": 7.5,
                "hard": 8.0,
                "expert": 8.5,
            }.get(difficulty, 7.0),
            "dimension_thresholds": {
                QualityDimension.CORRECTNESS.value: 8.0,
                QualityDimension.COMPLEXITY.value: 7.0,
                QualityDimension.STYLE.value: 7.5,
                QualityDimension.READABILITY.value: 7.5,
                QualityDimension.MAINTAINABILITY.value: 7.0,
            },
            "task_specific_requirements": self._get_task_specific_requirements(task_type),
        }

        return standards

    def _calculate_cost_quality_ratio(self, earth_result: EarthLayerResult, context: dict) -> float:
        """计算成本质量比"""
        cost = context.get("cost", 0)
        quality_score = earth_result.overall_score

        if cost <= 0 or quality_score <= 0:
            return 0.0

        # 成本质量比 = 质量得分 / 成本（归一化）
        # 这里假设成本单位是token数或API调用次数
        normalized_cost = cost / 1000.0  # 每1000 tokens
        return quality_score / (normalized_cost + 0.1)  # 避免除零

    def _determine_improvement_priority(self, earth_result: EarthLayerResult) -> t.List[str]:
        """确定改进优先级"""
        dimension_scores = earth_result.dimension_scores

        # 按评分排序，最低分优先
        sorted_dimensions = sorted(dimension_scores.items(), key=lambda x: x[1])

        # 返回维度名称列表
        return [dim[0] for dim in sorted_dimensions]

    def _generate_strategic_recommendations(self, earth_result: EarthLayerResult) -> t.List[str]:
        """生成战略建议"""
        recommendations = []

        overall_score = earth_result.overall_score

        if overall_score >= 8.0:
            recommendations.append("质量优秀，保持当前开发实践")
            recommendations.append("考虑分享最佳实践给团队其他成员")
        elif overall_score >= 7.0:
            recommendations.append("质量良好，有改进空间")
            recommendations.append("重点关注最弱维度的改进")
        elif overall_score >= 6.0:
            recommendations.append("质量达标，需要系统性改进")
            recommendations.append("建议实施代码审查和质量门禁")
        else:
            recommendations.append("质量不达标，需要立即改进")
            recommendations.append("建议进行专项质量培训和代码重构")

        # 添加维度特定建议
        for dim, score in earth_result.dimension_scores.items():
            if score < 6.0:
                recommendations.append(f"{dim}维度严重不足，需要重点关注")

        return recommendations

    def _calculate_effort_distribution(self, dimension_scores: dict) -> dict:
        """计算改进努力分配"""
        total_score = sum(dimension_scores.values())
        if total_score == 0:
            return {dim: 1.0 / len(dimension_scores) for dim in dimension_scores}

        # 低分维度获得更多努力分配
        normalized_scores = {dim: 10 - score for dim, score in dimension_scores.items()}
        total_normalized = sum(normalized_scores.values())

        return {dim: score / total_normalized for dim, score in normalized_scores.items()}

    def _get_task_specific_requirements(self, task_type: str) -> dict:
        """获取任务特定要求"""
        requirements = {
            "algorithm": {"complexity_threshold": 7.0, "correctness_priority": "high"},
            "string": {"readability_threshold": 8.0, "edge_case_coverage": "high"},
            "data_structure": {"maintainability_threshold": 7.5, "memory_efficiency": "medium"},
            "math": {"correctness_threshold": 9.0, "numerical_stability": "high"},
        }

        return requirements.get(task_type, {"general_requirements": "满足基本质量维度标准"})


class ThreeTalentAssessmentEngine:
    """三才评估引擎主类"""

    def __init__(self, historical_data_path: t.Optional[str] = None):
        self.human_assessor = HumanLayerAssessor()
        self.earth_assessor = EarthLayerAssessor()

        # 加载历史数据
        historical_data = {}
        if historical_data_path and Path(historical_data_path).exists():
            try:
                with open(historical_data_path, "r", encoding="utf-8") as f:
                    historical_data = json.load(f)
            except:
                historical_data = {}

        self.heaven_assessor = HeavenLayerAssessor(historical_data)

    def assess(
        self,
        code: str,
        context: t.Optional[dict] = None,
        test_cases: t.Optional[list] = None,
        task_id: t.Optional[str] = None,
    ) -> ThreeTalentResult:
        """执行三才评估"""
        context = context or {}

        # 1. 人层评估：微观代码分析
        print("🧑 执行人层评估（微观代码级）...")
        human_result = self.human_assessor.assess_code(code)

        # 2. 地层评估：中观维度聚合
        print("🌍 执行地层评估（中观维度级）...")
        earth_result = self.earth_assessor.aggregate_dimensions(human_result, code, test_cases)

        # 3. 天层评估：宏观质量分析
        print("☁️  执行天层评估（宏观质量级）...")
        heaven_result = self.heaven_assessor.analyze_macro(earth_result, context)

        # 计算代码哈希（用于追踪）
        import hashlib

        code_hash = hashlib.md5(code.encode("utf-8")).hexdigest()[:8]

        return ThreeTalentResult(
            human_result=human_result,
            earth_result=earth_result,
            heaven_result=heaven_result,
            task_id=task_id,
            code_hash=code_hash,
        )

    def assess_from_file(
        self, filepath: str, context: t.Optional[dict] = None, task_id: t.Optional[str] = None
    ) -> ThreeTalentResult:
        """从文件评估代码"""
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()

        return self.assess(code, context, task_id=task_id)

    def batch_assess(
        self, code_samples: t.List[t.Tuple[str, dict]], output_dir: t.Union[str, Path]
    ) -> t.List[ThreeTalentResult]:
        """批量评估多个代码样本"""
        results = []
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, (code, context) in enumerate(code_samples):
            print(f"\n🔍 评估样本 {i+1}/{len(code_samples)}...")

            try:
                result = self.assess(code, context, task_id=f"sample_{i+1}")
                results.append(result)

                # 保存单个结果
                result_file = output_dir / f"assessment_{i+1}.json"
                result.save_to_json(result_file)
                print(f"  结果已保存到: {result_file}")

            except Exception as e:
                print(f"  评估失败: {e}")
                # 创建错误结果
                error_result = ThreeTalentResult(
                    human_result=HumanLayerResult(
                        ast_analysis={"valid": False, "issues": [str(e)]},
                        complexity_metrics={},
                        function_count=0,
                        class_count=0,
                        line_counts={"total": 0, "code": 0, "comment": 0, "blank": 0},
                        issues=[f"评估失败: {e}"],
                        suggestions=["检查代码语法和结构"],
                    ),
                    earth_result=EarthLayerResult(
                        dimension_scores={},
                        overall_score=0.0,
                        dimension_issues={},
                        dimension_suggestions={},
                    ),
                    heaven_result=HeavenLayerResult(
                        quality_trend={},
                        quality_strategy={},
                        quality_standards={},
                        cost_quality_ratio=0.0,
                        improvement_priority=[],
                        strategic_recommendations=["评估过程出现错误，请检查输入"],
                    ),
                    task_id=f"sample_{i+1}_error",
                )
                results.append(error_result)

        # 保存汇总报告
        summary = {
            "total_samples": len(code_samples),
            "successful_assessments": len([r for r in results if r.earth_result.overall_score > 0]),
            "average_score": (
                sum(r.earth_result.overall_score for r in results) / len(results) if results else 0
            ),
            "assessment_time": datetime.now().isoformat(),
        }

        summary_file = output_dir / "assessment_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n📊 批量评估完成！汇总报告: {summary_file}")
        return results


# 使用示例
if __name__ == "__main__":
    # 示例代码
    sample_code = """
def fibonacci(n):
    \"\"\"计算斐波那契数列\"\"\"
    if n <= 1:
        return n
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b

def is_prime(n):
    \"\"\"判断是否为质数\"\"\"
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True
"""

    # 创建评估引擎
    engine = ThreeTalentAssessmentEngine()

    # 评估上下文
    context = {"task_type": "algorithm", "difficulty": "medium", "cost": 150}  # 假设成本（tokens）

    # 执行评估
    print("🚀 开始三才评估...")
    result = engine.assess(sample_code, context, task_id="demo_fibonacci")

    # 打印结果摘要
    print("\n" + "=" * 60)
    print("📋 三才评估结果摘要")
    print("=" * 60)

    print(f"\n🌍 地层总体评分: {result.earth_result.overall_score:.2f}/10")

    print("\n📊 维度评分:")
    for dim, score in result.earth_result.dimension_scores.items():
        print(f"  {dim}: {score:.2f}")

    print(f"\n☁️  成本质量比: {result.heaven_result.cost_quality_ratio:.2f}")

    print("\n🎯 改进优先级:")
    for i, dim in enumerate(result.heaven_result.improvement_priority[:3], 1):
        print(f"  {i}. {dim}")

    print("\n💡 战略建议:")
    for rec in result.heaven_result.strategic_recommendations[:3]:
        print(f"  • {rec}")

    # 保存结果
    result.save_to_json("/tmp/three_talent_assessment_demo.json")
    print(f"\n💾 结果已保存到: /tmp/three_talent_assessment_demo.json")
