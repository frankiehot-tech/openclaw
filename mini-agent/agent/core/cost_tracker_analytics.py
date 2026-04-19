#!/usr/bin/env python3
"""
成本跟踪分析模块 - 基于审计报告第二阶段优化建议

为成本监控系统提供高级聚合分析功能，包括：
1. 趋势分析和异常检测
2. 优化建议引擎
3. 成本预测和预算规划
4. 跨维度聚合分析（provider、模型、任务类型）

设计特点：
1. 数据驱动：基于历史成本数据生成洞察
2. 实时分析：支持实时数据流分析
3. 可配置：可调整分析敏感度和阈值
4. 可扩展：易于添加新的分析算法
"""

import json
import logging
import math
import os
import statistics
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入现有组件
try:
    from .cost_tracker import CostRecord, CostSummary, CostTracker, get_cost_tracker
    from .financial_monitor_adapter import get_financial_monitor_adapter

    HAS_DEPENDENCIES = True
except ImportError as e:
    logging.warning(f"导入依赖失败，分析模块将以降级模式运行: {e}")
    HAS_DEPENDENCIES = False

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== 分析引擎核心类 ====================


class CostAnalyticsEngine:
    """成本分析引擎"""

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        """
        初始化分析引擎

        Args:
            cost_tracker: CostTracker实例（如果为None则尝试自动获取）
        """
        self.cost_tracker = cost_tracker or self._get_cost_tracker()
        self._analysis_cache = {}
        self._cache_ttl = 300  # 缓存5分钟

        # 分析配置
        self.config = {
            "trend_window_days": 30,
            "anomaly_threshold_sigma": 3.0,
            "optimization_threshold_percentage": 10.0,  # 优化潜力阈值
            "budget_alert_threshold": 0.8,  # 预算告警阈值（80%）
            "cost_reduction_target": 0.2,  # 成本降低目标（20%）
        }

        logger.info("成本分析引擎初始化完成")

    def _get_cost_tracker(self) -> Optional[CostTracker]:
        """获取成本追踪器实例"""
        if not HAS_DEPENDENCIES:
            return None

        try:
            from .cost_tracker import get_cost_tracker

            return get_cost_tracker()
        except Exception as e:
            logger.error(f"获取成本追踪器失败: {e}")
            return None

    def get_trend_analysis(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        granularity: str = "daily",
    ) -> Dict[str, Any]:
        """
        获取成本趋势分析

        Args:
            start_date: 开始日期（默认30天前）
            end_date: 结束日期（默认今天）
            granularity: 粒度（"daily"、"weekly"、"monthly"）

        Returns:
            趋势分析结果
        """
        if not self.cost_tracker:
            return {"success": False, "error": "成本追踪器不可用"}

        try:
            # 设置默认日期范围
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=self.config["trend_window_days"])

            # 获取记录
            records = self.cost_tracker.get_records(
                start_date=start_date, end_date=end_date, limit=10000
            )

            if not records:
                return {
                    "success": True,
                    "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                    "granularity": granularity,
                    "trends": [],
                    "statistics": {
                        "total_cost": 0.0,
                        "avg_daily_cost": 0.0,
                        "cost_change_percentage": 0.0,
                        "volatility": 0.0,
                    },
                    "insights": ["无足够数据进行趋势分析"],
                }

            # 按粒度聚合数据
            aggregated_data = self._aggregate_by_granularity(records, granularity)

            # 计算统计信息
            costs = [item["cost"] for item in aggregated_data]
            total_cost = sum(costs)
            avg_cost = statistics.mean(costs) if costs else 0.0

            # 计算成本变化（第一半 vs 第二半）
            half_point = len(costs) // 2
            first_half = costs[:half_point] if half_point > 0 else []
            second_half = costs[half_point:] if half_point > 0 else []

            avg_first = statistics.mean(first_half) if first_half else 0.0
            avg_second = statistics.mean(second_half) if second_half else 0.0

            cost_change_percentage = 0.0
            if avg_first > 0:
                cost_change_percentage = (avg_second - avg_first) / avg_first * 100

            # 计算波动率（标准差）
            volatility = statistics.stdev(costs) if len(costs) > 1 else 0.0

            # 检测异常点
            anomalies = self._detect_anomalies(costs, aggregated_data)

            # 生成洞察
            insights = self._generate_trend_insights(
                costs, cost_change_percentage, volatility, anomalies
            )

            return {
                "success": True,
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "granularity": granularity,
                "trends": aggregated_data,
                "statistics": {
                    "total_cost": total_cost,
                    "avg_daily_cost": avg_cost,
                    "cost_change_percentage": cost_change_percentage,
                    "volatility": volatility,
                    "anomaly_count": len(anomalies),
                },
                "anomalies": anomalies,
                "insights": insights,
            }

        except Exception as e:
            logger.error(f"趋势分析失败: {e}")
            return {"success": False, "error": str(e)}

    def _aggregate_by_granularity(
        self, records: List[CostRecord], granularity: str
    ) -> List[Dict[str, Any]]:
        """按粒度聚合数据"""
        if granularity == "daily":
            return self._aggregate_daily(records)
        elif granularity == "weekly":
            return self._aggregate_weekly(records)
        elif granularity == "monthly":
            return self._aggregate_monthly(records)
        else:
            logger.warning(f"未知粒度: {granularity}，使用daily")
            return self._aggregate_daily(records)

    def _aggregate_daily(self, records: List[CostRecord]) -> List[Dict[str, Any]]:
        """按日聚合"""
        daily_data = defaultdict(lambda: {"cost": 0.0, "requests": 0, "tokens": 0})

        for record in records:
            day_key = record.timestamp.date().isoformat()
            daily_data[day_key]["cost"] += record.estimated_cost
            daily_data[day_key]["requests"] += 1
            daily_data[day_key]["tokens"] += record.input_tokens + record.output_tokens

        # 转换为排序列表
        sorted_days = sorted(daily_data.keys())
        result = []
        for day in sorted_days:
            data = daily_data[day]
            result.append(
                {
                    "date": day,
                    "cost": data["cost"],
                    "requests": data["requests"],
                    "tokens": data["tokens"],
                    "cost_per_request": (
                        data["cost"] / data["requests"] if data["requests"] > 0 else 0.0
                    ),
                    "cost_per_token": data["cost"] / data["tokens"] if data["tokens"] > 0 else 0.0,
                }
            )

        return result

    def _aggregate_weekly(self, records: List[CostRecord]) -> List[Dict[str, Any]]:
        """按周聚合"""
        weekly_data = defaultdict(lambda: {"cost": 0.0, "requests": 0, "tokens": 0})

        for record in records:
            # 计算周号（年份-周号）
            year, week, _ = record.timestamp.isocalendar()
            week_key = f"{year}-W{week:02d}"
            weekly_data[week_key]["cost"] += record.estimated_cost
            weekly_data[week_key]["requests"] += 1
            weekly_data[week_key]["tokens"] += record.input_tokens + record.output_tokens

        sorted_weeks = sorted(weekly_data.keys())
        result = []
        for week in sorted_weeks:
            data = weekly_data[week]
            result.append(
                {
                    "period": week,
                    "cost": data["cost"],
                    "requests": data["requests"],
                    "tokens": data["tokens"],
                    "cost_per_request": (
                        data["cost"] / data["requests"] if data["requests"] > 0 else 0.0
                    ),
                    "cost_per_token": data["cost"] / data["tokens"] if data["tokens"] > 0 else 0.0,
                }
            )

        return result

    def _aggregate_monthly(self, records: List[CostRecord]) -> List[Dict[str, Any]]:
        """按月聚合"""
        monthly_data = defaultdict(lambda: {"cost": 0.0, "requests": 0, "tokens": 0})

        for record in records:
            month_key = record.timestamp.strftime("%Y-%m")
            monthly_data[month_key]["cost"] += record.estimated_cost
            monthly_data[month_key]["requests"] += 1
            monthly_data[month_key]["tokens"] += record.input_tokens + record.output_tokens

        sorted_months = sorted(monthly_data.keys())
        result = []
        for month in sorted_months:
            data = monthly_data[month]
            result.append(
                {
                    "period": month,
                    "cost": data["cost"],
                    "requests": data["requests"],
                    "tokens": data["tokens"],
                    "cost_per_request": (
                        data["cost"] / data["requests"] if data["requests"] > 0 else 0.0
                    ),
                    "cost_per_token": data["cost"] / data["tokens"] if data["tokens"] > 0 else 0.0,
                }
            )

        return result

    def _detect_anomalies(
        self, costs: List[float], data_points: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """检测异常点"""
        if len(costs) < 3:
            return []

        try:
            mean = statistics.mean(costs)
            stdev = statistics.stdev(costs) if len(costs) > 1 else 0.0
            threshold = self.config["anomaly_threshold_sigma"]

            anomalies = []
            for i, (cost, data_point) in enumerate(zip(costs, data_points)):
                if stdev > 0:
                    z_score = abs(cost - mean) / stdev
                    if z_score > threshold:
                        anomalies.append(
                            {
                                "index": i,
                                "date": data_point.get("date") or data_point.get("period"),
                                "cost": cost,
                                "z_score": z_score,
                                "deviation_percentage": (
                                    ((cost - mean) / mean * 100) if mean > 0 else 0.0
                                ),
                            }
                        )

            return anomalies
        except Exception as e:
            logger.warning(f"异常检测失败: {e}")
            return []

    def _generate_trend_insights(
        self,
        costs: List[float],
        change_percentage: float,
        volatility: float,
        anomalies: List[Dict[str, Any]],
    ) -> List[str]:
        """生成趋势洞察"""
        insights = []

        if not costs:
            insights.append("无足够数据进行趋势分析")
            return insights

        # 成本变化洞察
        if abs(change_percentage) > 20:
            direction = "上升" if change_percentage > 0 else "下降"
            insights.append(f"成本显著{direction} {abs(change_percentage):.1f}%，建议关注原因")
        elif abs(change_percentage) > 10:
            direction = "上升" if change_percentage > 0 else "下降"
            insights.append(f"成本轻微{direction} {abs(change_percentage):.1f}%")

        # 波动性洞察
        avg_cost = statistics.mean(costs) if costs else 0.0
        if avg_cost > 0:
            volatility_percentage = volatility / avg_cost * 100
            if volatility_percentage > 50:
                insights.append(f"成本波动性高 ({volatility_percentage:.1f}%)，可能存在不稳定因素")
            elif volatility_percentage > 30:
                insights.append(f"成本波动性中等 ({volatility_percentage:.1f}%)")

        # 异常点洞察
        if anomalies:
            insights.append(f"检测到 {len(anomalies)} 个异常点，建议检查对应日期的使用情况")

        # 成本水平洞察
        if avg_cost > 1.0:
            insights.append("日均成本较高（>¥1），建议进行成本优化审查")
        elif avg_cost < 0.1:
            insights.append("成本控制良好，日均成本较低")

        return insights

    def get_provider_comparison(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        获取provider对比分析

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            provider对比分析结果
        """
        if not self.cost_tracker:
            return {"success": False, "error": "成本追踪器不可用"}

        try:
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=30)

            # 获取摘要数据
            summary = self.cost_tracker.get_summary(start_date=start_date, end_date=end_date)

            if not summary.by_provider:
                return {
                    "success": True,
                    "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                    "total_cost": summary.total_cost,
                    "total_requests": summary.total_requests,
                    "providers": {},
                    "comparison": {},
                    "recommendations": ["无provider数据进行对比分析"],
                }

            # 获取详细记录以计算更多指标
            records = self.cost_tracker.get_records(
                start_date=start_date, end_date=end_date, limit=5000
            )

            # 按provider分组
            provider_data = defaultdict(
                lambda: {
                    "cost": 0.0,
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "records": [],
                }
            )

            for record in records:
                provider_data[record.provider_id]["cost"] += record.estimated_cost
                provider_data[record.provider_id]["requests"] += 1
                provider_data[record.provider_id]["input_tokens"] += record.input_tokens
                provider_data[record.provider_id]["output_tokens"] += record.output_tokens
                provider_data[record.provider_id]["records"].append(record)

            total_cost = summary.total_cost
            total_requests = summary.total_requests

            # 构建对比数据
            comparison_data = {}
            for provider, data in provider_data.items():
                cost = data["cost"]
                requests = data["requests"]
                total_tokens = data["input_tokens"] + data["output_tokens"]

                cost_per_request = cost / requests if requests > 0 else 0.0
                cost_per_token = cost / total_tokens if total_tokens > 0 else 0.0
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0.0

                comparison_data[provider] = {
                    "cost": cost,
                    "requests": requests,
                    "input_tokens": data["input_tokens"],
                    "output_tokens": data["output_tokens"],
                    "total_tokens": total_tokens,
                    "cost_per_request": cost_per_request,
                    "cost_per_token": cost_per_token,
                    "percentage": percentage,
                    "avg_input_tokens": data["input_tokens"] / requests if requests > 0 else 0,
                    "avg_output_tokens": data["output_tokens"] / requests if requests > 0 else 0,
                }

            # 生成优化建议
            recommendations = self._generate_provider_recommendations(comparison_data)

            return {
                "success": True,
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "total_cost": total_cost,
                "total_requests": total_requests,
                "providers": comparison_data,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"provider对比分析失败: {e}")
            return {"success": False, "error": str(e)}

    def _generate_provider_recommendations(
        self, provider_data: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """生成provider优化建议"""
        recommendations = []

        if len(provider_data) < 2:
            return ["需要至少2个provider的数据进行对比分析"]

        # 找出成本最高的provider
        sorted_providers = sorted(
            provider_data.items(), key=lambda x: x[1]["cost_per_request"], reverse=True
        )

        if len(sorted_providers) >= 2:
            expensive_provider, expensive_data = sorted_providers[0]
            cheap_provider, cheap_data = sorted_providers[-1]

            expensive_cost_per_req = expensive_data["cost_per_request"]
            cheap_cost_per_req = cheap_data["cost_per_request"]

            if expensive_cost_per_req > 0 and cheap_cost_per_req > 0:
                ratio = expensive_cost_per_req / cheap_cost_per_req
                if ratio > 1.5:  # 成本高50%以上
                    savings_potential = expensive_data["cost"] * 0.3  # 假设可迁移30%
                    recommendations.append(
                        f"{expensive_provider}的单次请求成本是{cheap_provider}的{ratio:.1f}倍"
                    )
                    recommendations.append(
                        f"考虑将部分{expensive_provider}任务迁移到{cheap_provider}，"
                        f"预计可节省¥{savings_potential:.4f}"
                    )

        # 检查成本占比
        total_cost = sum(data["cost"] for data in provider_data.values())
        for provider, data in provider_data.items():
            percentage = data["percentage"]
            if percentage > 70:
                recommendations.append(f"{provider}占总成本{percentage:.1f}%，存在供应商依赖风险")

        return recommendations

    def get_task_kind_analysis(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        获取任务类型分析

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            任务类型分析结果
        """
        if not self.cost_tracker:
            return {"success": False, "error": "成本追踪器不可用"}

        try:
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=30)

            # 获取记录
            records = self.cost_tracker.get_records(
                start_date=start_date, end_date=end_date, limit=5000
            )

            # 按任务类型分组
            task_kind_data = defaultdict(
                lambda: {
                    "cost": 0.0,
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "providers": defaultdict(float),
                }
            )

            unknown_count = 0
            for record in records:
                task_kind = record.task_kind or "unknown"
                if task_kind == "unknown":
                    unknown_count += 1

                data = task_kind_data[task_kind]
                data["cost"] += record.estimated_cost
                data["requests"] += 1
                data["input_tokens"] += record.input_tokens
                data["output_tokens"] += record.output_tokens
                data["providers"][record.provider_id] += record.estimated_cost

            total_cost = sum(data["cost"] for data in task_kind_data.values())
            total_requests = sum(data["requests"] for data in task_kind_data.values())

            # 计算详细指标
            analysis_data = {}
            for task_kind, data in task_kind_data.items():
                cost = data["cost"]
                requests = data["requests"]
                total_tokens = data["input_tokens"] + data["output_tokens"]

                analysis_data[task_kind] = {
                    "cost": cost,
                    "requests": requests,
                    "percentage": (cost / total_cost * 100) if total_cost > 0 else 0.0,
                    "cost_per_request": cost / requests if requests > 0 else 0.0,
                    "avg_tokens_per_request": total_tokens / requests if requests > 0 else 0,
                    "providers": dict(data["providers"]),
                    "provider_distribution": {
                        provider: (cost_part / cost * 100) if cost > 0 else 0.0
                        for provider, cost_part in data["providers"].items()
                    },
                }

            # 生成优化建议
            recommendations = self._generate_task_kind_recommendations(analysis_data, total_cost)

            result = {
                "success": True,
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "total_cost": total_cost,
                "total_requests": total_requests,
                "unknown_task_count": unknown_count,
                "task_kind_analysis": analysis_data,
                "recommendations": recommendations,
            }

            if unknown_count > 0:
                result["warning"] = f"发现{unknown_count}个未知任务类型的记录，建议完善任务类型标记"

            return result

        except Exception as e:
            logger.error(f"任务类型分析失败: {e}")
            return {"success": False, "error": str(e)}

    def _generate_task_kind_recommendations(
        self, task_kind_data: Dict[str, Dict[str, Any]], total_cost: float
    ) -> List[str]:
        """生成任务类型优化建议"""
        recommendations = []

        if not task_kind_data:
            return ["无任务类型数据进行分析"]

        # 按成本排序
        sorted_tasks = sorted(task_kind_data.items(), key=lambda x: x[1]["cost"], reverse=True)

        # 识别高成本任务类型
        high_cost_threshold = total_cost * 0.3  # 占总成本30%以上
        for task_kind, data in sorted_tasks:
            cost = data["cost"]
            percentage = data["percentage"]

            if percentage > 30:
                recommendations.append(
                    f"'{task_kind}'任务占总成本{percentage:.1f}%，建议优先优化此任务类型"
                )
            elif percentage > 10:
                # 检查是否有成本较高的provider
                providers = data.get("providers", {})
                if providers:
                    expensive_provider = max(providers.items(), key=lambda x: x[1])[0]
                    cheap_provider = min(providers.items(), key=lambda x: x[1])[0]
                    if providers[expensive_provider] > providers[cheap_provider] * 2:
                        recommendations.append(
                            f"'{task_kind}'任务中，{expensive_provider}成本较高，"
                            f"考虑迁移到{cheap_provider}"
                        )

        # 识别低效任务（高单次请求成本）
        for task_kind, data in sorted_tasks:
            cost_per_request = data["cost_per_request"]
            if cost_per_request > 0.01:  # 单次请求成本 > ¥0.01
                recommendations.append(
                    f"'{task_kind}'任务单次请求成本较高(¥{cost_per_request:.4f})，"
                    f"建议优化请求效率"
                )

        return recommendations

    def get_cost_optimization_plan(
        self, target_reduction_percentage: float = 20.0
    ) -> Dict[str, Any]:
        """
        获取成本优化计划

        Args:
            target_reduction_percentage: 目标降低百分比

        Returns:
            成本优化计划
        """
        if not self.cost_tracker:
            return {"success": False, "error": "成本追踪器不可用"}

        try:
            # 获取最近30天数据
            end_date = date.today()
            start_date = end_date - timedelta(days=30)

            # 获取各项分析
            provider_analysis = self.get_provider_comparison(start_date, end_date)
            task_kind_analysis = self.get_task_kind_analysis(start_date, end_date)

            if not provider_analysis.get("success") or not task_kind_analysis.get("success"):
                return {"success": False, "error": "分析数据获取失败"}

            # 计算当前成本
            current_monthly_cost = provider_analysis["total_cost"]

            # 生成优化措施
            optimization_measures = self._generate_optimization_measures(
                provider_analysis, task_kind_analysis, target_reduction_percentage
            )

            # 计算预期节省
            estimated_savings = sum(
                measure.get("estimated_savings", 0) for measure in optimization_measures
            )

            target_reduction = current_monthly_cost * (target_reduction_percentage / 100)
            achievement_percentage = (
                (estimated_savings / target_reduction * 100) if target_reduction > 0 else 0.0
            )

            return {
                "success": True,
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "current_monthly_cost": current_monthly_cost,
                "target_reduction_percentage": target_reduction_percentage,
                "target_reduction_amount": target_reduction,
                "estimated_savings": estimated_savings,
                "achievement_percentage": achievement_percentage,
                "optimization_measures": optimization_measures,
                "implementation_priority": self._prioritize_measures(optimization_measures),
            }

        except Exception as e:
            logger.error(f"成本优化计划生成失败: {e}")
            return {"success": False, "error": str(e)}

    def _generate_optimization_measures(
        self,
        provider_analysis: Dict[str, Any],
        task_kind_analysis: Dict[str, Any],
        target_reduction: float,
    ) -> List[Dict[str, Any]]:
        """生成优化措施"""
        measures = []

        # 基于provider对比的优化
        provider_data = provider_analysis.get("providers", {})
        if len(provider_data) >= 2:
            # 找出成本差异最大的两个provider
            providers = list(provider_data.items())
            providers.sort(key=lambda x: x[1]["cost_per_request"], reverse=True)

            expensive_provider, expensive_data = providers[0]
            cheap_provider, cheap_data = providers[-1]

            expensive_cost = expensive_data["cost"]
            expensive_per_request = expensive_data["cost_per_request"]
            cheap_per_request = cheap_data["cost_per_request"]

            if expensive_per_request > cheap_per_request * 1.2:  # 成本高20%以上
                # 假设可以迁移30%的任务
                migratable_percentage = 0.3
                estimated_savings = (
                    expensive_cost
                    * migratable_percentage
                    * (1 - cheap_per_request / expensive_per_request)
                )

                measures.append(
                    {
                        "type": "provider_migration",
                        "description": f"将{expensive_provider}的{migratable_percentage*100:.0f}%任务迁移到{cheap_provider}",
                        "rationale": f"{expensive_provider}单次请求成本是{cheap_provider}的{expensive_per_request/cheap_per_request:.1f}倍",
                        "estimated_savings": estimated_savings,
                        "implementation_effort": "medium",
                        "timeframe": "2-4 weeks",
                    }
                )

        # 基于任务类型的优化
        task_data = task_kind_analysis.get("task_kind_analysis", {})
        for task_kind, data in task_data.items():
            cost = data["cost"]
            percentage = data["percentage"]

            if percentage > 20:  # 占总成本20%以上
                # 假设可以优化20%的成本
                optimization_percentage = 0.2
                estimated_savings = cost * optimization_percentage

                measures.append(
                    {
                        "type": "task_optimization",
                        "description": f"优化'{task_kind}'任务类型，目标降低{optimization_percentage*100:.0f}%成本",
                        "rationale": f"'{task_kind}'任务占总成本{percentage:.1f}%，优化潜力大",
                        "estimated_savings": estimated_savings,
                        "implementation_effort": "high",
                        "timeframe": "4-8 weeks",
                    }
                )

        return measures

    def _prioritize_measures(self, measures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对优化措施进行优先级排序"""
        if not measures:
            return []

        # 计算ROI（节省/努力程度）
        effort_score = {"low": 1.0, "medium": 2.0, "high": 3.0}

        prioritized = []
        for measure in measures:
            savings = measure.get("estimated_savings", 0)
            effort = measure.get("implementation_effort", "medium")
            roi = (
                savings / effort_score.get(effort, 2.0) if effort_score.get(effort, 2.0) > 0 else 0
            )

            prioritized.append(
                {**measure, "roi": roi, "priority_score": savings * 0.7 + roi * 0.3}  # 加权得分
            )

        # 按优先级排序
        prioritized.sort(key=lambda x: x["priority_score"], reverse=True)

        # 添加优先级等级
        for i, measure in enumerate(prioritized):
            if i == 0:
                measure["priority"] = "P0 (最高)"
            elif i < 3:
                measure["priority"] = "P1 (高)"
            elif i < 6:
                measure["priority"] = "P2 (中)"
            else:
                measure["priority"] = "P3 (低)"

        return prioritized

    def get_health_score(self) -> Dict[str, Any]:
        """
        获取成本健康度评分

        Returns:
            健康度评分结果
        """
        if not self.cost_tracker:
            return {"success": False, "error": "成本追踪器不可用"}

        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)

            # 获取各项分析
            provider_analysis = self.get_provider_comparison(start_date, end_date)
            task_kind_analysis = self.get_task_kind_analysis(start_date, end_date)
            trend_analysis = self.get_trend_analysis(start_date, end_date, "weekly")

            scores = {}

            # 1. 成本控制评分（0-100）
            if provider_analysis.get("success"):
                provider_data = provider_analysis.get("providers", {})
                if provider_data:
                    # 检查是否有provider成本异常高
                    cost_per_request_values = [
                        data["cost_per_request"] for data in provider_data.values()
                    ]
                    avg_cost_per_request = (
                        statistics.mean(cost_per_request_values) if cost_per_request_values else 0.0
                    )

                    # 评分逻辑：单次请求成本越低越好
                    if avg_cost_per_request < 0.001:
                        scores["cost_efficiency"] = 90
                    elif avg_cost_per_request < 0.005:
                        scores["cost_efficiency"] = 75
                    elif avg_cost_per_request < 0.01:
                        scores["cost_efficiency"] = 60
                    else:
                        scores["cost_efficiency"] = 40
                else:
                    scores["cost_efficiency"] = 50  # 中性分数

            # 2. 供应商多样性评分
            if provider_analysis.get("success"):
                provider_data = provider_analysis.get("providers", {})
                provider_count = len(provider_data)
                if provider_count >= 3:
                    scores["provider_diversity"] = 90
                elif provider_count == 2:
                    scores["provider_diversity"] = 70
                elif provider_count == 1:
                    scores["provider_diversity"] = 40
                else:
                    scores["provider_diversity"] = 0

            # 3. 趋势稳定性评分
            if trend_analysis.get("success"):
                volatility = trend_analysis["statistics"].get("volatility", 0.0)
                avg_cost = trend_analysis["statistics"].get("avg_daily_cost", 0.0)

                if avg_cost > 0:
                    volatility_percentage = volatility / avg_cost * 100
                    if volatility_percentage < 20:
                        scores["trend_stability"] = 85
                    elif volatility_percentage < 40:
                        scores["trend_stability"] = 65
                    elif volatility_percentage < 60:
                        scores["trend_stability"] = 45
                    else:
                        scores["trend_stability"] = 25
                else:
                    scores["trend_stability"] = 70  # 无成本时视为稳定

            # 4. 数据完整性评分
            if task_kind_analysis.get("success"):
                unknown_count = task_kind_analysis.get("unknown_task_count", 0)
                total_requests = task_kind_analysis.get("total_requests", 1)

                unknown_percentage = (
                    (unknown_count / total_requests * 100) if total_requests > 0 else 0
                )
                if unknown_percentage < 10:
                    scores["data_completeness"] = 90
                elif unknown_percentage < 30:
                    scores["data_completeness"] = 70
                elif unknown_percentage < 50:
                    scores["data_completeness"] = 50
                else:
                    scores["data_completeness"] = 30

            # 计算总分
            if scores:
                total_score = sum(scores.values()) / len(scores)
                grade = (
                    "A"
                    if total_score >= 80
                    else "B" if total_score >= 65 else "C" if total_score >= 50 else "D"
                )
            else:
                total_score = 50
                grade = "C"

            return {
                "success": True,
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "overall_score": total_score,
                "grade": grade,
                "category_scores": scores,
                "recommendations": self._generate_health_recommendations(scores, total_score),
            }

        except Exception as e:
            logger.error(f"健康度评分失败: {e}")
            return {"success": False, "error": str(e)}

    def _generate_health_recommendations(
        self, scores: Dict[str, int], overall_score: float
    ) -> List[str]:
        """生成健康度改进建议"""
        recommendations = []

        # 检查各维度分数
        if scores.get("cost_efficiency", 100) < 60:
            recommendations.append(
                "成本效率较低，建议优化provider使用策略，优先选择成本效益高的模型"
            )

        if scores.get("provider_diversity", 100) < 50:
            recommendations.append("供应商多样性不足，存在供应商锁定风险，建议引入更多备选provider")

        if scores.get("trend_stability", 100) < 50:
            recommendations.append("成本趋势波动较大，建议分析波动原因并建立成本稳定机制")

        if scores.get("data_completeness", 100) < 60:
            recommendations.append("数据完整性有待提高，建议完善任务类型标记和数据收集")

        # 总体建议
        if overall_score >= 80:
            recommendations.append("成本健康度良好，继续保持当前优化策略")
        elif overall_score >= 65:
            recommendations.append("成本健康度中等，建议实施1-2项关键优化措施")
        elif overall_score >= 50:
            recommendations.append("成本健康度需要改进，建议制定全面的成本优化计划")
        else:
            recommendations.append("成本健康度较差，建议立即进行成本审计和优化")

        return recommendations


# ==================== 全局实例管理 ====================


_cost_analytics_engine_instance: Optional[CostAnalyticsEngine] = None


def get_cost_analytics_engine() -> CostAnalyticsEngine:
    """获取全局成本分析引擎实例"""
    global _cost_analytics_engine_instance
    if _cost_analytics_engine_instance is None:
        _cost_analytics_engine_instance = CostAnalyticsEngine()
    return _cost_analytics_engine_instance


# ==================== 测试函数 ====================


def test_cost_analytics():
    """测试成本分析功能"""
    print("=== 测试成本分析功能 ===\n")

    engine = CostAnalyticsEngine()

    # 测试1：趋势分析
    print("1. 测试趋势分析:")
    trend_analysis = engine.get_trend_analysis(granularity="daily")
    if trend_analysis["success"]:
        print(f"   周期: {trend_analysis['period']['start']} 到 {trend_analysis['period']['end']}")
        print(f"   总成本: ¥{trend_analysis['statistics']['total_cost']:.4f}")
        print(f"   成本变化: {trend_analysis['statistics']['cost_change_percentage']:.1f}%")
        print(f"   异常点: {trend_analysis['statistics'].get('anomaly_count', 0)}个")
        if trend_analysis.get("insights"):
            print(f"   洞察: {trend_analysis['insights'][0]}")
    else:
        print(f"   失败: {trend_analysis.get('error')}")

    # 测试2：provider对比分析
    print("\n2. 测试provider对比分析:")
    provider_analysis = engine.get_provider_comparison()
    if provider_analysis["success"]:
        print(f"   provider数量: {len(provider_analysis['providers'])}")
        for provider, data in provider_analysis["providers"].items():
            print(f"   - {provider}: ¥{data['cost']:.4f} ({data['percentage']:.1f}%)")
        if provider_analysis.get("recommendations"):
            print(f"   建议: {provider_analysis['recommendations'][0]}")
    else:
        print(f"   失败: {provider_analysis.get('error')}")

    # 测试3：任务类型分析
    print("\n3. 测试任务类型分析:")
    task_analysis = engine.get_task_kind_analysis()
    if task_analysis["success"]:
        print(f"   任务类型数量: {len(task_analysis['task_kind_analysis'])}")
        for task_kind, data in task_analysis["task_kind_analysis"].items():
            print(f"   - '{task_kind}': ¥{data['cost']:.4f} ({data['percentage']:.1f}%)")
    else:
        print(f"   失败: {task_analysis.get('error')}")

    # 测试4：成本优化计划
    print("\n4. 测试成本优化计划:")
    optimization_plan = engine.get_cost_optimization_plan(target_reduction_percentage=20.0)
    if optimization_plan["success"]:
        print(f"   当前月成本: ¥{optimization_plan['current_monthly_cost']:.4f}")
        print(f"   目标节省: ¥{optimization_plan['target_reduction_amount']:.4f}")
        print(f"   预计节省: ¥{optimization_plan['estimated_savings']:.4f}")
        print(f"   达成率: {optimization_plan['achievement_percentage']:.1f}%")
        print(f"   优化措施数量: {len(optimization_plan['optimization_measures'])}")
    else:
        print(f"   失败: {optimization_plan.get('error')}")

    # 测试5：健康度评分
    print("\n5. 测试健康度评分:")
    health_score = engine.get_health_score()
    if health_score["success"]:
        print(f"   总体评分: {health_score['overall_score']:.1f}/100 ({health_score['grade']})")
        for category, score in health_score["category_scores"].items():
            print(f"   - {category}: {score}/100")
        if health_score.get("recommendations"):
            print(f"   建议: {health_score['recommendations'][0]}")
    else:
        print(f"   失败: {health_score.get('error')}")

    print("\n✅ 成本分析功能测试完成")


if __name__ == "__main__":
    test_cost_analytics()
