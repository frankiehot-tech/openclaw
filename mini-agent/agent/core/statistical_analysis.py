#!/usr/bin/env python3
"""
统计显著性分析模块 - 用于分析实验结果的统计显著性

基于收集的实验样本数据（105个样本），进行：
1. 成本差异的t检验
2. 效应量计算（Cohen's d）
3. 置信区间计算
4. 统计功效分析
5. 样本量需求计算

为迁移决策提供数据驱动的统计支持。
"""

import json
import logging
import math
import sqlite3
import statistics
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

# 导入科学计算库
try:
    import numpy as np
    import scipy.stats as stats

    SCIENTIFIC_AVAILABLE = True
except ImportError:
    SCIENTIFIC_AVAILABLE = False
    import warnings

    warnings.warn("numpy/scipy not available, using built-in statistics for basic analysis")

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 数据库路径（与实验日志记录器使用相同的数据库）
PROJECT_ROOT = "/Volumes/1TB-M2/openclaw"
DB_PATH = f"{PROJECT_ROOT}/mini-agent/data/cost_tracking.db"


@dataclass
class StatisticalTestResult:
    """统计测试结果"""

    # 样本信息
    control_sample_size: int
    treatment_sample_size: int
    total_sample_size: int

    # 描述性统计
    control_mean: float
    treatment_mean: float
    control_std: float
    treatment_std: float
    control_se: float  # 标准误差
    treatment_se: float

    # 差异统计
    mean_difference: float
    percent_reduction: float

    # 显著性检验结果
    t_statistic: Optional[float] = None
    p_value: Optional[float] = None
    degrees_of_freedom: Optional[float] = None

    # 效应量
    cohens_d: Optional[float] = None
    effect_size_magnitude: Optional[str] = None  # small/medium/large

    # 置信区间
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    confidence_level: float = 0.95

    # 功效分析
    statistical_power: Optional[float] = None
    required_sample_size: Optional[int] = None  # 达到80%功效所需样本量

    # 决策支持
    statistically_significant: bool = False
    effect_size_meaningful: bool = False
    recommendation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        # 格式化浮点数
        for key, value in result.items():
            if isinstance(value, float):
                result[key] = round(value, 6)
        return result

    def to_summary_string(self) -> str:
        """生成摘要字符串"""
        lines = []
        lines.append("=" * 60)
        lines.append("📊 统计显著性分析结果")
        lines.append("=" * 60)

        lines.append(f"样本统计:")
        lines.append(f"  控制组样本量: {self.control_sample_size}")
        lines.append(f"  实验组样本量: {self.treatment_sample_size}")
        lines.append(f"  总样本量: {self.total_sample_size}")

        lines.append(f"\n描述性统计:")
        lines.append(f"  控制组平均成本: ¥{self.control_mean:.6f} (±¥{self.control_std:.6f})")
        lines.append(f"  实验组平均成本: ¥{self.treatment_mean:.6f} (±¥{self.treatment_std:.6f})")
        lines.append(f"  平均差异: ¥{self.mean_difference:.6f}")
        lines.append(f"  成本降低百分比: {self.percent_reduction:.2f}%")

        lines.append(f"\n显著性检验:")
        lines.append(f"  t统计量: {self.t_statistic:.4f}")
        lines.append(f"  p值: {self.p_value:.6f}")
        lines.append(f"  自由度: {self.degrees_of_freedom:.1f}")
        lines.append(
            f"  统计显著性: {'✅ 是' if self.statistically_significant else '❌ 否'} (p < 0.05)"
        )

        if self.cohens_d is not None:
            lines.append(f"\n效应量:")
            lines.append(f"  Cohen's d: {self.cohens_d:.3f}")
            lines.append(f"  效应量大小: {self.effect_size_magnitude}")
            lines.append(
                f"  效应量是否有意义: {'✅ 是' if self.effect_size_meaningful else '❌ 否'}"
            )

        if self.ci_lower is not None and self.ci_upper is not None:
            lines.append(f"\n置信区间 ({self.confidence_level*100:.0f}%):")
            lines.append(f"  成本差异CI: [¥{self.ci_lower:.6f}, ¥{self.ci_upper:.6f}]")
            percent_ci_lower = (
                (self.ci_lower / self.control_mean * 100) if self.control_mean != 0 else 0
            )
            percent_ci_upper = (
                (self.ci_upper / self.control_mean * 100) if self.control_mean != 0 else 0
            )
            lines.append(f"  百分比CI: [{percent_ci_lower:.1f}%, {percent_ci_upper:.1f}%]")

        if self.statistical_power is not None:
            lines.append(f"\n统计功效分析:")
            lines.append(f"  当前功效: {self.statistical_power:.3f}")
            if self.required_sample_size is not None:
                lines.append(f"  达到80%功效所需样本量: {self.required_sample_size}")

        if self.recommendation:
            lines.append(f"\n决策建议:")
            lines.append(f"  {self.recommendation}")

        lines.append("=" * 60)
        return "\n".join(lines)


class ExperimentStatistician:
    """实验统计学家 - 分析实验结果的统计显著性"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = None

    def connect(self) -> sqlite3.Connection:
        """连接到数据库"""
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def get_experiment_cost_data(
        self, experiment_id: str = "coding_plan_deepseek_coder_ab"
    ) -> Tuple[List[float], List[float]]:
        """
        获取实验的成本数据

        Args:
            experiment_id: 实验ID

        Returns:
            (control_costs, treatment_costs) 元组
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = """
        SELECT
            group_name,
            cost_info
        FROM experiment_records
        WHERE experiment_id = ?
          AND cost_info IS NOT NULL
          AND cost_info != ''
          AND group_name IN ('control', 'treatment')
          AND status != 'created'
        ORDER BY recorded_at
        """

        cursor.execute(query, (experiment_id,))
        rows = cursor.fetchall()

        control_costs = []
        treatment_costs = []

        for row in rows:
            try:
                cost_info = json.loads(row["cost_info"])
                # 尝试提取estimated_cost字段
                estimated_cost = cost_info.get("estimated_cost")
                if estimated_cost is None:
                    # 尝试从nested结构提取
                    if isinstance(cost_info, dict):
                        for key in ["cost", "total_cost", "amount"]:
                            if key in cost_info:
                                estimated_cost = cost_info[key]
                                break

                if estimated_cost is not None and isinstance(estimated_cost, (int, float)):
                    if row["group_name"] == "control":
                        control_costs.append(float(estimated_cost))
                    else:
                        treatment_costs.append(float(estimated_cost))

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"解析成本信息失败: {e}")
                continue

        logger.info(
            f"获取到 {len(control_costs)} 个控制组样本和 {len(treatment_costs)} 个实验组样本"
        )
        return control_costs, treatment_costs

    def get_experiment_quality_data(
        self, experiment_id: str = "coding_plan_deepseek_coder_ab"
    ) -> Tuple[List[float], List[float]]:
        """
        获取实验的质量评分数据

        Args:
            experiment_id: 实验ID

        Returns:
            (control_quality, treatment_quality) 元组
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = """
        SELECT
            group_name,
            quality_score
        FROM experiment_records
        WHERE experiment_id = ?
          AND quality_score IS NOT NULL
          AND group_name IN ('control', 'treatment')
          AND status != 'created'
        ORDER BY recorded_at
        """

        cursor.execute(query, (experiment_id,))
        rows = cursor.fetchall()

        control_quality = []
        treatment_quality = []

        for row in rows:
            quality_score = row["quality_score"]
            if quality_score is not None:
                score = float(quality_score)
                if row["group_name"] == "control":
                    control_quality.append(score)
                else:
                    treatment_quality.append(score)

        logger.info(
            f"获取到 {len(control_quality)} 个控制组质量评分和 {len(treatment_quality)} 个实验组质量评分"
        )
        return control_quality, treatment_quality

    def calculate_descriptive_statistics(self, data: List[float]) -> Dict[str, float]:
        """计算描述性统计"""
        if not data:
            return {"mean": 0, "std": 0, "se": 0, "min": 0, "max": 0, "median": 0}

        mean = statistics.mean(data) if len(data) > 0 else 0
        std = statistics.stdev(data) if len(data) > 1 else 0
        se = std / math.sqrt(len(data)) if len(data) > 0 else 0
        min_val = min(data) if data else 0
        max_val = max(data) if data else 0
        median = statistics.median(data) if data else 0

        return {
            "mean": mean,
            "std": std,
            "se": se,
            "min": min_val,
            "max": max_val,
            "median": median,
            "sample_size": len(data),
        }

    def perform_t_test(
        self, control_data: List[float], treatment_data: List[float]
    ) -> Dict[str, Any]:
        """执行t检验"""
        if not control_data or not treatment_data:
            logger.warning("数据不足，无法执行t检验")
            return {"t_statistic": None, "p_value": None, "degrees_of_freedom": None}

        # 使用scipy.stats进行t检验（如果可用）
        if SCIENTIFIC_AVAILABLE and len(control_data) > 1 and len(treatment_data) > 1:
            try:
                t_stat, p_value = stats.ttest_ind(control_data, treatment_data, equal_var=False)
                # 计算自由度（Welch-Satterthwaite公式）
                n1, n2 = len(control_data), len(treatment_data)
                s1, s2 = np.std(control_data, ddof=1), np.std(treatment_data, ddof=1)

                # 避免除零错误
                if s1 == 0 and s2 == 0:
                    df = n1 + n2 - 2
                elif s1 == 0 or s2 == 0:
                    df = n1 + n2 - 2  # 退化为标准t检验
                else:
                    v1 = s1**2 / n1
                    v2 = s2**2 / n2
                    df = (v1 + v2) ** 2 / (v1**2 / (n1 - 1) + v2**2 / (n2 - 1))

                return {
                    "t_statistic": float(t_stat),
                    "p_value": float(p_value),
                    "degrees_of_freedom": float(df),
                }
            except Exception as e:
                logger.error(f"scipy t检验失败: {e}")

        # 备选方案：使用标准库的近似计算
        if len(control_data) > 1 and len(treatment_data) > 1:
            # 计算均值差异的标准误差
            control_stats = self.calculate_descriptive_statistics(control_data)
            treatment_stats = self.calculate_descriptive_statistics(treatment_data)

            mean_diff = control_stats["mean"] - treatment_stats["mean"]
            se_diff = math.sqrt(control_stats["se"] ** 2 + treatment_stats["se"] ** 2)

            if se_diff > 0:
                t_stat = mean_diff / se_diff
                # 近似自由度
                df = len(control_data) + len(treatment_data) - 2
                # 近似p值（使用t分布）
                try:
                    if SCIENTIFIC_AVAILABLE:
                        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))
                    else:
                        # 非常粗略的近似
                        p_value = 2 * (1 - 0.5)  # 占位符
                except:
                    p_value = None

                return {"t_statistic": t_stat, "p_value": p_value, "degrees_of_freedom": df}

        return {"t_statistic": None, "p_value": None, "degrees_of_freedom": None}

    def calculate_cohens_d(self, control_data: List[float], treatment_data: List[float]) -> float:
        """计算Cohen's d效应量"""
        if not control_data or not treatment_data:
            return 0.0

        control_mean = statistics.mean(control_data) if control_data else 0
        treatment_mean = statistics.mean(treatment_data) if treatment_data else 0

        # 合并标准差
        if len(control_data) > 1 and len(treatment_data) > 1:
            control_var = statistics.variance(control_data) if len(control_data) > 1 else 0
            treatment_var = statistics.variance(treatment_data) if len(treatment_data) > 1 else 0

            n1, n2 = len(control_data), len(treatment_data)
            pooled_std = math.sqrt(
                ((n1 - 1) * control_var + (n2 - 1) * treatment_var) / (n1 + n2 - 2)
            )
        else:
            pooled_std = 0

        if pooled_std > 0:
            cohens_d = (control_mean - treatment_mean) / pooled_std
        else:
            cohens_d = 0

        return cohens_d

    def get_effect_size_magnitude(self, cohens_d: float) -> str:
        """获取效应量大小描述"""
        abs_d = abs(cohens_d)
        if abs_d < 0.2:
            return "很小"
        elif abs_d < 0.5:
            return "小"
        elif abs_d < 0.8:
            return "中"
        else:
            return "大"

    def calculate_confidence_interval(
        self,
        mean_diff: float,
        se_diff: float,
        confidence_level: float = 0.95,
        df: Optional[float] = None,
    ) -> Tuple[float, float]:
        """计算置信区间"""
        if se_diff == 0:
            return (mean_diff, mean_diff)

        if SCIENTIFIC_AVAILABLE and df is not None:
            # 使用t分布
            t_critical = stats.t.ppf((1 + confidence_level) / 2, df)
        else:
            # 使用正态分布近似
            from scipy.stats import norm

            t_critical = norm.ppf((1 + confidence_level) / 2)

        margin_of_error = t_critical * se_diff
        ci_lower = mean_diff - margin_of_error
        ci_upper = mean_diff + margin_of_error

        return (ci_lower, ci_upper)

    def calculate_statistical_power(
        self, control_data: List[float], treatment_data: List[float], alpha: float = 0.05
    ) -> float:
        """计算统计功效"""
        if not control_data or not treatment_data:
            return 0.0

        if SCIENTIFIC_AVAILABLE:
            try:
                n1, n2 = len(control_data), len(treatment_data)
                effect_size = self.calculate_cohens_d(control_data, treatment_data)

                # 使用统计功效计算
                from statsmodels.stats.power import TTestIndPower

                # 创建功效分析实例
                analysis = TTestIndPower()
                power = analysis.solve_power(
                    effect_size=abs(effect_size),
                    nobs1=n1,
                    alpha=alpha,
                    ratio=n2 / n1 if n1 > 0 else 1,
                    alternative="two-sided",
                )

                return float(power)
            except ImportError:
                logger.warning("statsmodels not available, using approximation for power")
            except Exception as e:
                logger.error(f"功效计算失败: {e}")

        # 近似功效计算
        n1, n2 = len(control_data), len(treatment_data)
        total_n = n1 + n2
        if total_n >= 100:
            return 0.8  # 假设100+样本有80%功效
        elif total_n >= 50:
            return 0.7
        elif total_n >= 30:
            return 0.6
        else:
            return 0.5

    def calculate_required_sample_size(
        self,
        control_data: List[float],
        treatment_data: List[float],
        desired_power: float = 0.8,
        alpha: float = 0.05,
    ) -> int:
        """计算达到期望功效所需的样本量"""
        if not control_data:
            return 0

        if SCIENTIFIC_AVAILABLE:
            try:
                effect_size = self.calculate_cohens_d(control_data, treatment_data)

                from statsmodels.stats.power import TTestIndPower

                analysis = TTestIndPower()

                required_n = analysis.solve_power(
                    effect_size=abs(effect_size),
                    power=desired_power,
                    alpha=alpha,
                    ratio=1.0,  # 平衡设计
                    alternative="two-sided",
                )

                # 向上取整，每组样本量
                return int(math.ceil(required_n))
            except ImportError:
                logger.warning("statsmodels not available, cannot calculate required sample size")
            except Exception as e:
                logger.error(f"样本量计算失败: {e}")

        # 近似计算
        effect_size = self.calculate_cohens_d(control_data, treatment_data)
        abs_effect = abs(effect_size)

        if abs_effect >= 0.8:  # 大效应
            return 25
        elif abs_effect >= 0.5:  # 中等效应
            return 65
        elif abs_effect >= 0.2:  # 小效应
            return 200
        else:  # 很小效应
            return 800

    def analyze_experiment(
        self, experiment_id: str = "coding_plan_deepseek_coder_ab"
    ) -> StatisticalTestResult:
        """
        分析实验的统计显著性

        Args:
            experiment_id: 实验ID

        Returns:
            StatisticalTestResult对象
        """
        logger.info(f"开始分析实验: {experiment_id}")

        # 获取成本数据
        control_costs, treatment_costs = self.get_experiment_cost_data(experiment_id)

        if not control_costs or not treatment_costs:
            logger.error(f"实验 {experiment_id} 缺少成本数据")
            return StatisticalTestResult(
                control_sample_size=0,
                treatment_sample_size=0,
                total_sample_size=0,
                control_mean=0,
                treatment_mean=0,
                control_std=0,
                treatment_std=0,
                control_se=0,
                treatment_se=0,
                mean_difference=0,
                percent_reduction=0,
                recommendation="❌ 实验数据不足，无法进行统计显著性分析",
            )

        # 计算描述性统计
        control_stats = self.calculate_descriptive_statistics(control_costs)
        treatment_stats = self.calculate_descriptive_statistics(treatment_costs)

        # 计算差异
        mean_difference = control_stats["mean"] - treatment_stats["mean"]
        percent_reduction = (
            (mean_difference / control_stats["mean"] * 100) if control_stats["mean"] > 0 else 0
        )

        # 执行t检验
        t_test_results = self.perform_t_test(control_costs, treatment_costs)

        # 计算效应量
        cohens_d = self.calculate_cohens_d(control_costs, treatment_costs)
        effect_size_magnitude = self.get_effect_size_magnitude(cohens_d)

        # 计算置信区间
        mean_diff_se = math.sqrt(control_stats["se"] ** 2 + treatment_stats["se"] ** 2)
        ci_lower, ci_upper = self.calculate_confidence_interval(
            mean_difference, mean_diff_se, df=t_test_results.get("degrees_of_freedom")
        )

        # 计算统计功效
        statistical_power = self.calculate_statistical_power(control_costs, treatment_costs)

        # 计算所需样本量
        required_sample_size = self.calculate_required_sample_size(control_costs, treatment_costs)

        # 检查统计显著性
        p_value = t_test_results.get("p_value")
        statistically_significant = p_value is not None and p_value < 0.05

        # 检查效应量是否有意义（Cohen's d > 0.2）
        effect_size_meaningful = abs(cohens_d) >= 0.2

        # 生成决策建议
        recommendation = self._generate_recommendation(
            statistically_significant,
            effect_size_meaningful,
            percent_reduction,
            len(control_costs) + len(treatment_costs),
            required_sample_size,
        )

        # 创建结果对象
        result = StatisticalTestResult(
            control_sample_size=len(control_costs),
            treatment_sample_size=len(treatment_costs),
            total_sample_size=len(control_costs) + len(treatment_costs),
            control_mean=control_stats["mean"],
            treatment_mean=treatment_stats["mean"],
            control_std=control_stats["std"],
            treatment_std=treatment_stats["std"],
            control_se=control_stats["se"],
            treatment_se=treatment_stats["se"],
            mean_difference=mean_difference,
            percent_reduction=percent_reduction,
            t_statistic=t_test_results.get("t_statistic"),
            p_value=p_value,
            degrees_of_freedom=t_test_results.get("degrees_of_freedom"),
            cohens_d=cohens_d,
            effect_size_magnitude=effect_size_magnitude,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            statistical_power=statistical_power,
            required_sample_size=required_sample_size,
            statistically_significant=statistically_significant,
            effect_size_meaningful=effect_size_meaningful,
            recommendation=recommendation,
        )

        logger.info(f"实验分析完成: {experiment_id}")
        return result

    def _generate_recommendation(
        self,
        statistically_significant: bool,
        effect_size_meaningful: bool,
        percent_reduction: float,
        current_sample_size: int,
        required_sample_size: int,
    ) -> str:
        """生成决策建议"""
        recommendations = []

        if statistically_significant:
            recommendations.append("✅ 统计显著：成本差异不是随机产生的，可以可靠地归因于实验干预")
        else:
            recommendations.append(
                "⚠️ 统计不显著：成本差异可能是随机变化，需要更多样本或更大的效应量"
            )

        if effect_size_meaningful:
            recommendations.append("✅ 效应量有意义：成本降低具有实际意义，不仅仅是统计显著")
        else:
            recommendations.append("⚠️ 效应量较小：虽然可能有统计显著性，但实际节省可能有限")

        if percent_reduction > 0:
            recommendations.append(f"✅ 成本降低：实验组平均成本降低 {percent_reduction:.1f}%")
        else:
            recommendations.append("⚠️ 未观察到成本降低：实验组成本高于或等于控制组")

        if current_sample_size < required_sample_size:
            recommendations.append(
                f"📊 样本量不足：当前 {current_sample_size} 个样本，需要 {required_sample_size} 个样本以达到80%统计功效"
            )
        else:
            recommendations.append(
                f"📊 样本量充足：当前 {current_sample_size} 个样本已超过所需 {required_sample_size} 个样本"
            )

        # 总体建议
        if statistically_significant and effect_size_meaningful and percent_reduction > 10:
            recommendations.append(
                "🎯 **建议迁移**：实验显示显著且有意义成本节省，可以安全迁移更多任务到DeepSeek"
            )
        elif statistically_significant and percent_reduction > 0:
            recommendations.append(
                "🟡 **建议谨慎迁移**：成本降低统计显著但效应量较小，建议分阶段迁移并监控质量"
            )
        else:
            recommendations.append(
                "🔴 **建议继续实验**：未达到统计显著性标准，需要更多数据才能做出迁移决策"
            )

        return "\n".join(recommendations)

    def analyze_quality_comparison(
        self, experiment_id: str = "coding_plan_deepseek_coder_ab"
    ) -> Dict[str, Any]:
        """分析质量评分比较"""
        logger.info(f"开始分析质量评分: {experiment_id}")

        control_quality, treatment_quality = self.get_experiment_quality_data(experiment_id)

        if not control_quality or not treatment_quality:
            logger.warning(f"实验 {experiment_id} 缺少质量评分数据")
            return {"has_quality_data": False, "message": "缺少质量评分数据"}

        # 计算描述性统计
        control_stats = self.calculate_descriptive_statistics(control_quality)
        treatment_stats = self.calculate_descriptive_statistics(treatment_quality)

        # 计算差异
        mean_difference = treatment_stats["mean"] - control_stats["mean"]  # 正值表示质量提高
        percent_change = (
            (mean_difference / control_stats["mean"] * 100) if control_stats["mean"] > 0 else 0
        )

        # 执行t检验
        t_test_results = self.perform_t_test(control_quality, treatment_quality)

        # 计算效应量
        cohens_d = self.calculate_cohens_d(control_quality, treatment_quality)
        effect_size_magnitude = self.get_effect_size_magnitude(cohens_d)

        # 检查统计显著性
        p_value = t_test_results.get("p_value")
        statistically_significant = p_value is not None and p_value < 0.05

        # 质量评估建议
        quality_assessment = "未知"
        if statistically_significant:
            if mean_difference > 0:
                quality_assessment = "实验组质量显著优于控制组"
            elif mean_difference < 0:
                quality_assessment = "控制组质量显著优于实验组"
            else:
                quality_assessment = "质量无显著差异"
        else:
            quality_assessment = "质量无显著差异"

        return {
            "has_quality_data": True,
            "control_stats": control_stats,
            "treatment_stats": treatment_stats,
            "mean_difference": mean_difference,
            "percent_change": percent_change,
            "t_statistic": t_test_results.get("t_statistic"),
            "p_value": p_value,
            "statistically_significant": statistically_significant,
            "cohens_d": cohens_d,
            "effect_size_magnitude": effect_size_magnitude,
            "quality_assessment": quality_assessment,
            "recommendation": self._generate_quality_recommendation(
                statistically_significant, mean_difference, percent_change
            ),
        }

    def _generate_quality_recommendation(
        self, statistically_significant: bool, mean_difference: float, percent_change: float
    ) -> str:
        """生成质量评估建议"""
        if not statistically_significant:
            return "质量无显著差异，可以认为DeepSeek和DashScope在质量上表现相当"

        if mean_difference > 0:
            if percent_change > 10:
                return f"✅ 质量显著提高：DeepSeek质量比DashScope高{percent_change:.1f}%，迁移不会损害质量"
            else:
                return f"🟡 质量轻微提高：DeepSeek质量略高({percent_change:.1f}%)，迁移风险较低"
        else:
            if percent_change < -10:
                return f"🔴 质量显著下降：DeepSeek质量比DashScope低{-percent_change:.1f}%，需要仔细评估是否迁移"
            else:
                return (
                    f"🟡 质量轻微下降：DeepSeek质量略低({-percent_change:.1f}%)，可以接受但需要监控"
                )

    def generate_comprehensive_report(
        self, experiment_id: str = "coding_plan_deepseek_coder_ab"
    ) -> Dict[str, Any]:
        """生成综合分析报告"""
        logger.info(f"生成综合分析报告: {experiment_id}")

        # 成本分析
        cost_result = self.analyze_experiment(experiment_id)

        # 质量分析
        quality_result = self.analyze_quality_comparison(experiment_id)

        # 生成总体建议
        overall_recommendation = self._generate_overall_recommendation(cost_result, quality_result)

        report = {
            "experiment_id": experiment_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "cost_analysis": cost_result.to_dict(),
            "quality_analysis": quality_result,
            "overall_recommendation": overall_recommendation,
            "summary": self._generate_summary(cost_result, quality_result),
        }

        return report

    def _generate_overall_recommendation(
        self, cost_result: StatisticalTestResult, quality_result: Dict[str, Any]
    ) -> str:
        """生成总体迁移建议"""
        cost_significant = cost_result.statistically_significant
        cost_saving = cost_result.percent_reduction
        cost_meaningful = cost_result.effect_size_meaningful

        has_quality_data = quality_result.get("has_quality_data", False)
        quality_significant = quality_result.get("statistically_significant", False)
        quality_difference = quality_result.get("mean_difference", 0)

        # 基于成本和质量决策
        if cost_significant and cost_meaningful and cost_saving > 10:
            if has_quality_data:
                if quality_difference >= 0:  # 质量持平或更好
                    return "🎯 **强烈建议迁移**：显著成本节省且质量不下降，立即开始全面迁移"
                elif quality_difference > -5:  # 质量轻微下降但可接受
                    return "🟡 **建议迁移但监控质量**：显著成本节省，质量轻微下降，分阶段迁移并密切监控质量"
                else:  # 质量显著下降
                    return "🔴 **建议评估质量影响**：成本节省显著但质量下降明显，需要权衡成本节省和质量损失"
            else:
                return "🟡 **建议迁移但需要质量评估**：显著成本节省，但缺乏质量数据，建议先评估质量再决定迁移范围"
        elif cost_significant and cost_saving > 0:
            return "🟡 **建议谨慎迁移**：统计显著但效应量较小，建议分阶段迁移并收集更多数据"
        else:
            return "🔴 **建议继续实验**：未达到统计显著性标准，需要更多样本或重新设计实验"

    def _generate_summary(
        self, cost_result: StatisticalTestResult, quality_result: Dict[str, Any]
    ) -> str:
        """生成报告摘要"""
        lines = []

        lines.append(f"实验分析摘要:")
        lines.append(f"  总样本量: {cost_result.total_sample_size}")
        lines.append(f"  成本降低: {cost_result.percent_reduction:.1f}%")
        lines.append(f"  统计显著性: {'是' if cost_result.statistically_significant else '否'}")
        lines.append(
            f"  效应量: {cost_result.effect_size_magnitude} (Cohen's d = {cost_result.cohens_d:.3f})"
        )

        if quality_result.get("has_quality_data"):
            lines.append(f"  质量差异: {quality_result.get('percent_change', 0):.1f}%")
            lines.append(
                f"  质量显著性: {'是' if quality_result.get('statistically_significant') else '否'}"
            )

        lines.append(f"  统计功效: {cost_result.statistical_power:.3f}")
        lines.append(f"  所需样本量: {cost_result.required_sample_size}")

        return "\n".join(lines)

    def print_report(self, experiment_id: str = "coding_plan_deepseek_coder_ab"):
        """打印分析报告"""
        report = self.generate_comprehensive_report(experiment_id)

        print("=" * 70)
        print("📊 实验统计显著性综合分析报告")
        print("=" * 70)
        print(f"实验ID: {report['experiment_id']}")
        print(f"分析时间: {report['analysis_timestamp']}")
        print()

        # 成本分析结果
        cost_result = StatisticalTestResult(**report["cost_analysis"])
        print(cost_result.to_summary_string())

        print()

        # 质量分析结果
        quality_result = report["quality_analysis"]
        if quality_result["has_quality_data"]:
            print("🧪 质量评分分析")
            print("-" * 40)
            print(
                f"控制组平均质量: {quality_result['control_stats']['mean']:.2f} (±{quality_result['control_stats']['std']:.2f})"
            )
            print(
                f"实验组平均质量: {quality_result['treatment_stats']['mean']:.2f} (±{quality_result['treatment_stats']['std']:.2f})"
            )
            print(
                f"质量差异: {quality_result['mean_difference']:.2f} ({quality_result['percent_change']:.1f}%)"
            )
            print(f"p值: {quality_result['p_value']:.4f}")
            print(
                f"统计显著性: {'✅ 是' if quality_result['statistically_significant'] else '❌ 否'}"
            )
            print(
                f"Cohen's d: {quality_result['cohens_d']:.3f} ({quality_result['effect_size_magnitude']})"
            )
            print(f"质量评估: {quality_result['quality_assessment']}")
            print(f"建议: {quality_result['recommendation']}")
        else:
            print("⚠️ 没有可用的质量评分数据")

        print()

        # 总体建议
        print("🎯 总体迁移建议")
        print("-" * 40)
        print(report["overall_recommendation"])

        print()
        print("📋 摘要")
        print("-" * 40)
        print(report["summary"])

        print()
        print("=" * 70)
        print("✅ 分析完成")
        print("=" * 70)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="实验统计显著性分析")
    parser.add_argument(
        "--experiment-id",
        default="coding_plan_deepseek_coder_ab",
        help="实验ID (默认: coding_plan_deepseek_coder_ab)",
    )
    parser.add_argument("--db-path", default=DB_PATH, help=f"数据库路径 (默认: {DB_PATH})")
    parser.add_argument(
        "--output",
        choices=["text", "json", "summary"],
        default="text",
        help="输出格式 (默认: text)",
    )

    args = parser.parse_args()

    # 创建统计学家实例
    statistician = ExperimentStatistician(db_path=args.db_path)

    if args.output == "json":
        report = statistician.generate_comprehensive_report(args.experiment_id)
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif args.output == "summary":
        result = statistician.analyze_experiment(args.experiment_id)
        print(result.to_summary_string())
    else:
        statistician.print_report(args.experiment_id)


if __name__ == "__main__":
    main()
