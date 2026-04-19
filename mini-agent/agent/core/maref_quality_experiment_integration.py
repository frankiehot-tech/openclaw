#!/usr/bin/env python3
"""
MAREF质量评估与实验框架集成模块

将MAREF质量评估体系集成到实验框架中，实现：
1. 自动化评估实验记录的代码质量
2. 存储详细的MAREF评估结果
3. 支持质量-成本综合分析
4. 提供优化建议和决策支持

设计原则：
- 向后兼容：保持现有quality_score字段，同时扩展存储MAREF详细结果
- 性能优化：支持异步评估和批量处理
- 灵活性：支持实时评估和离线评估两种模式
"""

import json
import logging
import os
import sys
import typing as t
from dataclasses import asdict, dataclass, field
from datetime import datetime

# 添加项目根目录到路径
project_root = "/Volumes/1TB-M2/openclaw"
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "mini-agent"))

# 导入依赖组件
from agent.core.experiment_logger import ExperimentLogger, get_experiment_logger
from agent.core.maref_quality_integration import (
    MarefQualityEvaluator,
    MarefQualityResult,
    get_maref_quality_evaluator,
)

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class MarefExperimentQualityResult:
    """实验质量评估结果（MAREF扩展）"""

    # 基础质量信息（与现有实验记录兼容）
    quality_score: float  # 总体质量评分（0-10）
    quality_breakdown: t.Dict[str, float]  # 维度分解评分
    quality_assessor: str = "maref"  # 评估器类型

    # MAREF详细结果
    maref_result: t.Optional[MarefQualityResult] = None  # 完整MAREF结果
    maref_summary: t.Dict[str, t.Any] = field(default_factory=dict)  # MAREF摘要

    # 关联信息
    request_id: t.Optional[str] = None
    experiment_id: t.Optional[str] = None
    assessed_at: datetime = field(default_factory=datetime.now)

    # 元数据
    metadata: t.Dict[str, t.Any] = field(default_factory=dict)

    def to_experiment_format(self) -> t.Dict[str, t.Any]:
        """转换为实验记录器期望的格式"""
        result = {
            "quality_score": self.quality_score,
            "quality_breakdown": self.quality_breakdown,
            "quality_assessor": self.quality_assessor,
            "metadata": self.metadata.copy(),
        }

        # 添加MAREF详细结果到元数据
        if self.maref_result:
            result["metadata"]["maref_result"] = self.maref_result.to_dict()
            result["metadata"]["maref_summary"] = self.maref_summary

        # 添加评估时间
        result["metadata"]["assessed_at"] = self.assessed_at.isoformat()

        return result

    @classmethod
    def from_maref_result(
        cls,
        maref_result: MarefQualityResult,
        request_id: t.Optional[str] = None,
        experiment_id: t.Optional[str] = None,
        context: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> "MarefExperimentQualityResult":
        """从MAREF结果创建实验质量评估结果"""

        # 提取质量分解（从八卦评分或三才评估）
        quality_breakdown = {}

        # 优先使用八卦评分
        if maref_result.trigram_scores:
            for dim_name, score_info in maref_result.trigram_scores.items():
                quality_breakdown[dim_name] = score_info.get("score", 0.0)

        # 如果没有八卦评分，使用三才评估结果
        elif maref_result.quality_breakdown:
            quality_breakdown = maref_result.quality_breakdown

        # 创建MAREF摘要
        maref_summary = {
            "overall_score": maref_result.overall_score,
            "hexagram_index": (
                maref_result.hexagram_result.hexagram_index
                if maref_result.hexagram_result
                else None
            ),
            "gray_state_code": (
                maref_result.gray_state_analysis.state_code
                if maref_result.gray_state_analysis
                else None
            ),
            "improvement_suggestions": maref_result.improvement_suggestions[:5],  # 前5个建议
        }

        return cls(
            quality_score=maref_result.overall_score,
            quality_breakdown=quality_breakdown,
            quality_assessor="maref",
            maref_result=maref_result,
            maref_summary=maref_summary,
            request_id=request_id,
            experiment_id=experiment_id,
            assessed_at=datetime.now(),
            metadata={"context": context or {}, "maref_version": "1.0"},
        )


class MarefExperimentQualityAssessor:
    """MAREF实验质量评估器"""

    def __init__(
        self,
        experiment_logger: t.Optional[ExperimentLogger] = None,
        maref_evaluator: t.Optional[MarefQualityEvaluator] = None,
        enable_advanced_features: bool = True,
    ):
        """初始化评估器"""

        self.experiment_logger = experiment_logger or get_experiment_logger()
        self.maref_evaluator = maref_evaluator or get_maref_quality_evaluator(
            enable_advanced_features=enable_advanced_features
        )

        logger.info("🔧 MAREF实验质量评估器初始化完成")

    def _parse_cost_info(
        self, cost_info: t.Optional[t.Union[str, t.Dict[str, t.Any]]]
    ) -> t.Optional[t.Dict[str, t.Any]]:
        """解析成本信息，支持字符串JSON和字典两种格式"""
        if not cost_info:
            return None

        if isinstance(cost_info, dict):
            return cost_info
        elif isinstance(cost_info, str):
            try:
                return json.loads(cost_info)
            except json.JSONDecodeError:
                logger.warning(f"成本信息JSON解析失败: {cost_info[:100]}")
                return None
        else:
            logger.warning(f"未知的成本信息类型: {type(cost_info)}")
            return None

    def assess_experiment_by_request_id(
        self, request_id: str, context: t.Optional[t.Dict[str, t.Any]] = None
    ) -> t.Optional[MarefExperimentQualityResult]:
        """通过请求ID评估实验质量"""

        try:
            # 1. 获取实验记录
            records = self.experiment_logger.storage.get_experiment_records(
                request_id=request_id, limit=1
            )

            if not records:
                logger.warning(f"未找到请求ID对应的实验记录: {request_id}")
                return None

            record = records[0]

            # 2. 检查是否有输出响应
            if not record.output_response:
                logger.warning(f"实验记录无输出响应: {request_id}")
                return None

            # 3. 提取代码进行评估
            code_to_assess = record.output_response

            # 4. 准备评估上下文
            assessment_context = {
                "experiment_id": record.experiment_id,
                "request_id": record.request_id,
                "task_kind": record.task_kind,
                "group_name": record.group_name,
                "provider": self._extract_provider_from_metadata(record.metadata),
                "cost_info": self._parse_cost_info(record.cost_info),
                "execution_time": record.execution_time,
            }

            # 合并传入的上下文
            if context:
                assessment_context.update(context)

            # 5. 使用MAREF评估器评估代码质量
            logger.info(f"开始MAREF质量评估: {request_id}")
            maref_result = self.maref_evaluator.assess_code_quality(
                code=code_to_assess, context=assessment_context
            )

            # 6. 创建实验质量评估结果
            experiment_quality_result = MarefExperimentQualityResult.from_maref_result(
                maref_result=maref_result,
                request_id=request_id,
                experiment_id=record.experiment_id,
                context=assessment_context,
            )

            logger.info(
                f"MAREF质量评估完成: {request_id} - 评分: {maref_result.overall_score:.2f}/10"
            )

            return experiment_quality_result

        except Exception as e:
            logger.error(f"评估实验质量失败: {request_id} - {e}")
            return None

    def assess_and_record_experiment_quality(
        self, request_id: str, context: t.Optional[t.Dict[str, t.Any]] = None
    ) -> bool:
        """评估实验质量并记录到数据库"""

        try:
            # 1. 评估质量
            quality_result = self.assess_experiment_by_request_id(
                request_id=request_id, context=context
            )

            if not quality_result:
                return False

            # 2. 转换为实验记录器格式
            quality_assessment = quality_result.to_experiment_format()

            # 3. 记录到数据库
            success = self.experiment_logger.log_experiment_quality(
                request_id=request_id, quality_assessment=quality_assessment
            )

            if success:
                logger.info(f"实验质量已记录到数据库: {request_id}")
            else:
                logger.error(f"实验质量记录失败: {request_id}")

            return success

        except Exception as e:
            logger.error(f"评估和记录实验质量失败: {request_id} - {e}")
            return False

    def batch_assess_experiments(
        self,
        experiment_id: str,
        limit: t.Optional[int] = None,
        group_filter: t.Optional[t.List[str]] = None,
        skip_assessed: bool = True,
    ) -> t.Dict[str, t.Any]:
        """批量评估实验记录"""

        try:
            # 1. 获取实验记录（支持多个组名）
            records = []
            if group_filter and isinstance(group_filter, list):
                # 分别查询每个组名
                for group_name in group_filter:
                    group_records = self.experiment_logger.storage.get_experiment_records(
                        experiment_id=experiment_id, group_name=group_name, limit=limit
                    )
                    records.extend(group_records)
                logger.info(f"从 {len(group_filter)} 个组获取到 {len(records)} 个实验记录")
            else:
                # 查询所有组或不指定组名
                records = self.experiment_logger.storage.get_experiment_records(
                    experiment_id=experiment_id,
                    group_name=(
                        group_filter[0]
                        if group_filter
                        and isinstance(group_filter, list)
                        and len(group_filter) == 1
                        else None
                    ),
                    limit=limit,
                )
                logger.info(f"获取到 {len(records)} 个实验记录")

            # 2. 过滤已评估的记录
            if skip_assessed:
                records_to_assess = [
                    r for r in records if not r.quality_score or r.quality_assessor != "maref"
                ]
                logger.info(f"过滤后需要评估的记录: {len(records_to_assess)} 个")
            else:
                records_to_assess = records

            # 3. 批量评估
            results = {
                "total_records": len(records),
                "records_to_assess": len(records_to_assess),
                "assessed": 0,
                "failed": 0,
                "results": [],
            }

            for record in records_to_assess:
                try:
                    if not record.output_response:
                        logger.warning(f"跳过无输出响应的记录: {record.id}")
                        continue

                    # 评估质量
                    quality_result = self.assess_experiment_by_request_id(
                        request_id=record.request_id, context={"batch_assessment": True}
                    )

                    if quality_result:
                        # 记录到数据库
                        quality_assessment = quality_result.to_experiment_format()
                        success = self.experiment_logger.log_experiment_quality(
                            request_id=record.request_id, quality_assessment=quality_assessment
                        )

                        if success:
                            results["assessed"] += 1
                            results["results"].append(
                                {
                                    "request_id": record.request_id,
                                    "quality_score": quality_result.quality_score,
                                    "success": True,
                                }
                            )
                        else:
                            results["failed"] += 1
                    else:
                        results["failed"] += 1

                except Exception as e:
                    logger.error(f"批量评估失败: {record.request_id} - {e}")
                    results["failed"] += 1

            logger.info(f"批量评估完成: 成功 {results['assessed']}, 失败 {results['failed']}")
            return results

        except Exception as e:
            logger.error(f"批量评估失败: {e}")
            return {"error": str(e)}

    def generate_quality_cost_report(
        self, experiment_id: str, group_names: t.Optional[t.List[str]] = None
    ) -> t.Dict[str, t.Any]:
        """生成质量-成本综合分析报告"""

        try:
            # 1. 获取实验记录（支持多个组名）
            records = []
            groups_to_query = group_names or ["control", "treatment"]
            if isinstance(groups_to_query, list):
                # 分别查询每个组名
                for group_name in groups_to_query:
                    group_records = self.experiment_logger.storage.get_experiment_records(
                        experiment_id=experiment_id, group_name=group_name
                    )
                    records.extend(group_records)
                logger.info(
                    f"从 {len(groups_to_query)} 个组获取到 {len(records)} 个实验记录用于分析"
                )
            else:
                # 单个组名查询
                records = self.experiment_logger.storage.get_experiment_records(
                    experiment_id=experiment_id, group_name=groups_to_query
                )
                logger.info(f"获取到 {len(records)} 个实验记录用于分析")

            logger.info(f"获取到 {len(records)} 个实验记录用于分析")

            # 2. 按组统计
            groups = {}
            for record in records:
                group_name = record.group_name
                if group_name not in groups:
                    groups[group_name] = {
                        "records": [],
                        "quality_scores": [],
                        "costs": [],
                        "quality_cost_ratios": [],
                    }

                groups[group_name]["records"].append(record)

                # 质量评分
                if record.quality_score is not None:
                    groups[group_name]["quality_scores"].append(record.quality_score)

                # 成本信息
                cost = self._extract_cost_from_record(record)
                if cost is not None:
                    groups[group_name]["costs"].append(cost)

                    # 计算质量-成本比（QCR）
                    if record.quality_score is not None and cost > 0:
                        qcr = record.quality_score / cost
                        groups[group_name]["quality_cost_ratios"].append(qcr)

            # 3. 计算统计指标
            report = {
                "experiment_id": experiment_id,
                "analysis_time": datetime.now().isoformat(),
                "groups": {},
                "comparison": {},
                "recommendations": [],
            }

            for group_name, group_data in groups.items():
                quality_scores = group_data["quality_scores"]
                costs = group_data["costs"]
                quality_cost_ratios = group_data["quality_cost_ratios"]

                # 基本统计
                group_stats = {
                    "record_count": len(group_data["records"]),
                    "quality_score": {
                        "mean": self._mean(quality_scores) if quality_scores else 0,
                        "std": self._std(quality_scores) if len(quality_scores) > 1 else 0,
                        "min": min(quality_scores) if quality_scores else 0,
                        "max": max(quality_scores) if quality_scores else 0,
                        "count": len(quality_scores),
                    },
                    "cost": {
                        "mean": self._mean(costs) if costs else 0,
                        "std": self._std(costs) if len(costs) > 1 else 0,
                        "min": min(costs) if costs else 0,
                        "max": max(costs) if costs else 0,
                        "total": sum(costs) if costs else 0,
                        "count": len(costs),
                    },
                    "quality_cost_ratio": {
                        "mean": self._mean(quality_cost_ratios) if quality_cost_ratios else 0,
                        "std": (
                            self._std(quality_cost_ratios) if len(quality_cost_ratios) > 1 else 0
                        ),
                        "min": min(quality_cost_ratios) if quality_cost_ratios else 0,
                        "max": max(quality_cost_ratios) if quality_cost_ratios else 0,
                        "count": len(quality_cost_ratios),
                    },
                }

                report["groups"][group_name] = group_stats

            # 4. 组间比较
            if "control" in report["groups"] and "treatment" in report["groups"]:
                control_stats = report["groups"]["control"]
                treatment_stats = report["groups"]["treatment"]

                # 质量差异
                quality_diff = (
                    treatment_stats["quality_score"]["mean"]
                    - control_stats["quality_score"]["mean"]
                )
                quality_percent_change = (
                    (quality_diff / control_stats["quality_score"]["mean"] * 100)
                    if control_stats["quality_score"]["mean"] != 0
                    else 0
                )

                # 成本差异
                cost_diff = treatment_stats["cost"]["mean"] - control_stats["cost"]["mean"]
                cost_percent_change = (
                    (cost_diff / control_stats["cost"]["mean"] * 100)
                    if control_stats["cost"]["mean"] != 0
                    else 0
                )

                # QCR差异
                qcr_diff = (
                    treatment_stats["quality_cost_ratio"]["mean"]
                    - control_stats["quality_cost_ratio"]["mean"]
                )
                qcr_percent_change = (
                    (qcr_diff / control_stats["quality_cost_ratio"]["mean"] * 100)
                    if control_stats["quality_cost_ratio"]["mean"] != 0
                    else 0
                )

                report["comparison"] = {
                    "quality_difference": {
                        "absolute": quality_diff,
                        "percent": quality_percent_change,
                        "interpretation": self._interpret_difference(quality_diff, "质量"),
                    },
                    "cost_difference": {
                        "absolute": cost_diff,
                        "percent": cost_percent_change,
                        "interpretation": self._interpret_difference(cost_diff, "成本"),
                    },
                    "quality_cost_ratio_difference": {
                        "absolute": qcr_diff,
                        "percent": qcr_percent_change,
                        "interpretation": self._interpret_difference(qcr_diff, "质量成本比"),
                    },
                }

                # 5. 生成建议
                recommendations = []

                # 成本节省建议
                if cost_diff < 0 and quality_diff >= 0:
                    recommendations.append(
                        {
                            "type": "cost_saving",
                            "message": f"实验组在质量不变的情况下节省了 {-cost_percent_change:.1f}% 的成本",
                            "confidence": "high",
                            "action": "考虑切换到实验组设置",
                        }
                    )
                elif cost_diff < 0 and quality_diff < 0:
                    quality_loss_percent = -quality_percent_change
                    cost_saving_percent = -cost_percent_change
                    tradeoff_ratio = (
                        quality_loss_percent / cost_saving_percent
                        if cost_saving_percent != 0
                        else float("inf")
                    )

                    recommendations.append(
                        {
                            "type": "tradeoff",
                            "message": f"实验组节省了 {cost_saving_percent:.1f}% 的成本，但质量下降了 {quality_loss_percent:.1f}%",
                            "tradeoff_ratio": tradeoff_ratio,
                            "confidence": "medium",
                            "action": f"每节省1%成本，质量损失{tradeoff_ratio:.2f}%，根据业务需求权衡",
                        }
                    )

                # 质量提升建议
                elif quality_diff > 0 and cost_diff <= 0:
                    recommendations.append(
                        {
                            "type": "quality_improvement",
                            "message": f"实验组在成本不变的情况下提升了 {quality_percent_change:.1f}% 的质量",
                            "confidence": "high",
                            "action": "强烈建议切换到实验组设置",
                        }
                    )

                # QCR分析
                if qcr_diff > 0:
                    recommendations.append(
                        {
                            "type": "efficiency",
                            "message": f"实验组的质量成本比（QCR）提升了 {qcr_percent_change:.1f}%，效率更高",
                            "confidence": "high",
                            "action": "实验组提供了更好的性价比",
                        }
                    )

                report["recommendations"] = recommendations

            logger.info(f"质量-成本分析报告生成完成: {experiment_id}")
            return report

        except Exception as e:
            logger.error(f"生成质量-成本报告失败: {e}")
            return {"error": str(e)}

    def _extract_provider_from_metadata(self, metadata: t.Optional[str]) -> t.Optional[str]:
        """从元数据提取provider信息"""
        if not metadata:
            return None

        try:
            meta_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
            return meta_dict.get("provider")
        except:
            return None

    def _extract_cost_from_record(self, record) -> t.Optional[float]:
        """从实验记录提取成本"""
        try:
            if record.cost_info:
                # cost_info可能是字符串（JSON）或字典（已解析）
                if isinstance(record.cost_info, str):
                    try:
                        cost_info = json.loads(record.cost_info)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"无法解析cost_info JSON字符串: {record.cost_info[:100] if len(str(record.cost_info)) > 100 else record.cost_info}"
                        )
                        return None
                else:
                    cost_info = record.cost_info

                # 提取成本，支持多个字段名
                cost = None
                if isinstance(cost_info, dict):
                    cost = (
                        cost_info.get("estimated_cost")
                        or cost_info.get("cost")
                        or cost_info.get("total_cost")
                    )

                if cost is not None:
                    # 检查货币单位，如果不是USD，可能需要转换
                    # 暂时直接返回，假设所有货币单位一致
                    return float(cost)
                else:
                    logger.debug(f"cost_info中没有找到成本字段: {cost_info.keys()}")
                    return None

        except Exception as e:
            logger.warning(f"提取成本信息失败: {e}")
            pass

        # 尝试从metadata中提取
        try:
            if record.metadata:
                meta_dict = (
                    json.loads(record.metadata)
                    if isinstance(record.metadata, str)
                    else record.metadata
                )
                cost = meta_dict.get("cost") or meta_dict.get("estimated_cost")
                if cost is not None:
                    return float(cost)
        except Exception as e:
            logger.debug(f"从metadata提取成本失败: {e}")
            pass

        return None

    def _mean(self, values: t.List[float]) -> float:
        """计算平均值"""
        return sum(values) / len(values) if values else 0.0

    def _std(self, values: t.List[float]) -> float:
        """计算标准差"""
        if len(values) < 2:
            return 0.0

        mean = self._mean(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance**0.5

    def _interpret_difference(self, diff: float, metric_name: str) -> str:
        """解释差异"""
        if diff > 0:
            return f"{metric_name}提升"
        elif diff < 0:
            return f"{metric_name}降低"
        else:
            return f"{metric_name}无变化"


# 全局实例
_maref_experiment_assessor = None


def get_maref_experiment_assessor(
    experiment_logger: t.Optional[ExperimentLogger] = None,
    maref_evaluator: t.Optional[MarefQualityEvaluator] = None,
    enable_advanced_features: bool = True,
) -> MarefExperimentQualityAssessor:
    """获取全局MAREF实验质量评估器实例"""
    global _maref_experiment_assessor

    if _maref_experiment_assessor is None:
        _maref_experiment_assessor = MarefExperimentQualityAssessor(
            experiment_logger=experiment_logger,
            maref_evaluator=maref_evaluator,
            enable_advanced_features=enable_advanced_features,
        )

    return _maref_experiment_assessor


# 使用示例
if __name__ == "__main__":
    print("🚀 MAREF实验质量评估集成演示")
    print("=" * 60)

    # 创建评估器
    assessor = get_maref_experiment_assessor()

    print("1. 获取实验记录示例")
    print("2. 评估单个实验质量")
    print("3. 批量评估实验")
    print("4. 生成质量-成本报告")
    print()

    choice = input("请选择演示项目 (1-4): ")

    if choice == "1":
        # 演示获取实验记录
        print("\n📋 可用实验ID:")
        print("  - coding_plan_deepseek_coder_ab")
        print("  - (从数据库查询更多)")

    elif choice == "2":
        # 演示评估单个实验
        request_id = input("请输入请求ID: ")
        if request_id:
            print(f"\n🔍 评估实验: {request_id}")
            result = assessor.assess_and_record_experiment_quality(request_id)
            if result:
                print("✅ 评估完成并已记录到数据库")
            else:
                print("❌ 评估失败")

    elif choice == "3":
        # 演示批量评估
        experiment_id = (
            input("请输入实验ID (默认: coding_plan_deepseek_coder_ab): ")
            or "coding_plan_deepseek_coder_ab"
        )
        limit = input("请输入评估数量限制 (默认: 10): ")
        limit = int(limit) if limit else 10

        print(f"\n📊 批量评估实验: {experiment_id}")
        results = assessor.batch_assess_experiments(experiment_id=experiment_id, limit=limit)

        print(f"  总计记录: {results.get('total_records', 0)}")
        print(f"  评估成功: {results.get('assessed', 0)}")
        print(f"  评估失败: {results.get('failed', 0)}")

        if results.get("results"):
            print("\n  评估结果示例:")
            for i, r in enumerate(results["results"][:3]):
                print(f"    {i+1}. {r['request_id']}: {r['quality_score']:.2f}/10")

    elif choice == "4":
        # 演示质量-成本报告
        experiment_id = (
            input("请输入实验ID (默认: coding_plan_deepseek_coder_ab): ")
            or "coding_plan_deepseek_coder_ab"
        )

        print(f"\n📈 生成质量-成本报告: {experiment_id}")
        report = assessor.generate_quality_cost_report(experiment_id)

        if "error" in report:
            print(f"❌ 生成报告失败: {report['error']}")
        else:
            print(f"✅ 报告生成完成")
            print(f"   分析时间: {report['analysis_time']}")

            if "groups" in report:
                for group_name, stats in report["groups"].items():
                    print(f"\n   {group_name.upper()}组:")
                    print(f"     记录数: {stats['record_count']}")
                    print(f"     平均质量: {stats['quality_score']['mean']:.2f}")
                    print(f"     平均成本: {stats['cost']['mean']:.4f}")
                    print(f"     平均QCR: {stats['quality_cost_ratio']['mean']:.2f}")

            if "comparison" in report and report["comparison"]:
                print(f"\n   📊 组间比较:")
                comp = report["comparison"]
                if "quality_difference" in comp:
                    qd = comp["quality_difference"]
                    print(
                        f"     质量差异: {qd['absolute']:.2f} ({qd['percent']:.1f}%) - {qd['interpretation']}"
                    )

                if "cost_difference" in comp:
                    cd = comp["cost_difference"]
                    print(
                        f"     成本差异: {cd['absolute']:.4f} ({cd['percent']:.1f}%) - {cd['interpretation']}"
                    )

            if "recommendations" in report and report["recommendations"]:
                print(f"\n   💡 优化建议:")
                for i, rec in enumerate(report["recommendations"][:3]):
                    print(f"     {i+1}. {rec['message']}")
                    print(f"        行动: {rec['action']}")

    print("\n🎉 演示完成！")
