#!/usr/bin/env python3
"""
运营/资金摘要生成器 - 最小运营/资金summary骨架

输出一份当前系统可复用的 dashboard payload 或 summary artifact。
集成运营自动化状态和资金监控状态，供 AIplan / 审计链复用。
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== 数据类定义 ====================


@dataclass
class SummaryHealthScore:
    """健康评分"""

    financial: int = 100  # 财务健康度 (0-100)
    operational: int = 100  # 运营健康度 (0-100)
    automation: int = 100  # 自动化健康度 (0-100)
    overall: int = 100  # 整体健康度 (0-100)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SummaryAlertSummary:
    """告警摘要"""

    critical: int = 0
    warning: int = 0
    info: int = 0
    total: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SummaryFinancialData:
    """财务数据摘要"""

    remaining_budget: float = 0.0
    daily_budget: float = 0.0
    burn_rate: float = 0.0
    utilization: float = 0.0
    current_mode: str = "normal"
    days_until_reset: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SummaryOperationalData:
    """运营数据摘要"""

    automation_requests_total: int = 0
    automation_requests_today: int = 0
    automation_success_rate: float = 1.0
    last_automation_time: str | None = None
    active_automation_contracts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SummaryDashboardPayload:
    """仪表板负载"""

    # 元数据
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    summary_id: str = ""
    version: str = "1.0"

    # 健康评分
    health_scores: SummaryHealthScore = field(default_factory=SummaryHealthScore)

    # 告警摘要
    alert_summary: SummaryAlertSummary = field(default_factory=SummaryAlertSummary)

    # 财务摘要
    financial_data: SummaryFinancialData = field(default_factory=SummaryFinancialData)

    # 运营摘要
    operational_data: SummaryOperationalData = field(default_factory=SummaryOperationalData)

    # 关键指标
    key_metrics: dict[str, Any] = field(default_factory=dict)

    # 建议
    recommendations: list[str] = field(default_factory=list)

    # 链接到详细数据
    detailed_reports: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["health_scores"] = self.health_scores.to_dict()
        result["alert_summary"] = self.alert_summary.to_dict()
        result["financial_data"] = self.financial_data.to_dict()
        result["operational_data"] = self.operational_data.to_dict()
        return result

    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# 需要导入field装饰器
from dataclasses import field

# ==================== 摘要生成引擎 ====================


class SummaryGenerator:
    """摘要生成引擎"""

    def __init__(self, output_dir: str | None = None):
        self.output_dir = Path(output_dir) if output_dir else Path("workspace/summary_artifacts")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"摘要生成器初始化完成，输出目录: {self.output_dir}")

    def _get_financial_monitor(self):
        """获取金融监控器"""
        try:
            # 尝试从mini-agent导入
            from mini_agent.agent.core.financial_monitor import get_financial_monitor

            return get_financial_monitor()
        except ImportError:
            logger.warning("金融监控器不可用，使用模拟数据")
            return None

    def _get_automation_engine(self):
        """获取自动化引擎"""
        try:
            # 尝试从scripts导入
            from scripts.ops_automation_contract import get_automation_engine

            return get_automation_engine()
        except ImportError:
            logger.warning("自动化引擎不可用，使用模拟数据")
            return None

    def _get_alert_dispatcher(self):
        """获取告警分发器"""
        try:
            from mini_agent.agent.core.alert_dispatcher import get_alert_dispatcher

            return get_alert_dispatcher()
        except ImportError:
            logger.warning("告警分发器不可用")
            return None

    def _collect_financial_data(self) -> SummaryFinancialData:
        """收集财务数据"""
        monitor = self._get_financial_monitor()

        if monitor:
            try:
                dashboard = monitor.get_dashboard_payload()
                financial = dashboard["financial_summary"]

                return SummaryFinancialData(
                    remaining_budget=financial["budget"]["remaining"],
                    daily_budget=financial["budget"]["daily"],
                    burn_rate=financial["spending"]["burn_rate"],
                    utilization=financial["utilization"],
                    current_mode=financial["mode"],
                    days_until_reset=financial["days_until_reset"],
                )
            except Exception as e:
                logger.error(f"收集财务数据失败: {e}")

        # 模拟数据
        return SummaryFinancialData(
            remaining_budget=150.0,
            daily_budget=100.0,
            burn_rate=5.2,
            utilization=0.4,
            current_mode="normal",
            days_until_reset=3,
        )

    def _collect_operational_data(self) -> SummaryOperationalData:
        """收集运营数据"""
        engine = self._get_automation_engine()

        if engine:
            try:
                summary = engine.get_summary()
                stats = summary["statistics"]

                # 计算今日请求数（简化：假设所有请求都是今天的）
                today = datetime.now().date().isoformat()
                today_requests = 0
                for request in summary.get("recent_requests", []):
                    if request.get("created_at", "").startswith(today):
                        today_requests += 1

                # 计算成功率
                total_results = stats["total_results"]
                if total_results > 0:
                    success_count = len(
                        [
                            r
                            for r in engine.results.values()
                            if r.status.value in ["executed", "dry_run"]
                        ]
                    )
                    success_rate = success_count / total_results
                else:
                    success_rate = 1.0

                # 获取最后执行时间
                last_time = None
                if engine.results:
                    last_result = max(engine.results.values(), key=lambda r: r.executed_at)
                    last_time = last_result.executed_at

                return SummaryOperationalData(
                    automation_requests_total=stats["total_requests"],
                    automation_requests_today=today_requests,
                    automation_success_rate=success_rate,
                    last_automation_time=last_time,
                    active_automation_contracts=1,  # 简化
                )
            except Exception as e:
                logger.error(f"收集运营数据失败: {e}")

        # 模拟数据
        return SummaryOperationalData(
            automation_requests_total=5,
            automation_requests_today=2,
            automation_success_rate=0.8,
            last_automation_time=datetime.now().isoformat(),
            active_automation_contracts=1,
        )

    def _collect_alert_summary(self) -> SummaryAlertSummary:
        """收集告警摘要"""
        dispatcher = self._get_alert_dispatcher()
        monitor = self._get_financial_monitor()

        critical = warning = info = 0

        # 从金融监控器获取告警
        if monitor:
            try:
                dashboard = monitor.get_dashboard_payload()
                alert_summary = dashboard["alerts_summary"]
                critical = alert_summary["critical"]
                warning = alert_summary["warning"]
                info = alert_summary["info"]
            except Exception as e:
                logger.warning(f"从金融监控器获取告警摘要失败: {e}")

        # 从告警分发器获取状态（如果有）
        if dispatcher:
            try:
                dispatcher.get_status()
                # 告警分发器没有告警计数，跳过
                pass
            except Exception as e:
                logger.warning(f"从告警分发器获取状态失败: {e}")

        return SummaryAlertSummary(
            critical=critical,
            warning=warning,
            info=info,
            total=critical + warning + info,
        )

    def _calculate_health_scores(
        self,
        financial_data: SummaryFinancialData,
        operational_data: SummaryOperationalData,
        alert_summary: SummaryAlertSummary,
    ) -> SummaryHealthScore:
        """计算健康评分"""
        # 财务健康度 (0-100)
        financial_score = 100

        if financial_data.current_mode == "paused":
            financial_score = 10
        elif financial_data.current_mode == "critical":
            financial_score = 30
        elif financial_data.current_mode == "low":
            financial_score = 60
        elif financial_data.utilization > 0.9:
            financial_score = 40
        elif financial_data.utilization > 0.7:
            financial_score = 70
        elif financial_data.utilization > 0.5:
            financial_score = 85

        # 运营健康度 (0-100)
        operational_score = 100

        if operational_data.automation_success_rate < 0.5:
            operational_score = 30
        elif operational_data.automation_success_rate < 0.8:
            operational_score = 60
        elif operational_data.automation_success_rate < 0.95:
            operational_score = 80

        # 自动化健康度 (0-100)
        automation_score = 100

        if operational_data.last_automation_time:
            last_time = datetime.fromisoformat(operational_data.last_automation_time)
            hours_since_last = (datetime.now() - last_time).total_seconds() / 3600

            if hours_since_last > 48:
                automation_score = 20
            elif hours_since_last > 24:
                automation_score = 50
            elif hours_since_last > 12:
                automation_score = 80

        # 整体健康度 (加权平均)
        overall_score = int(
            financial_score * 0.4 + operational_score * 0.3 + automation_score * 0.3
        )

        # 根据告警调整
        if alert_summary.critical > 0:
            overall_score = min(overall_score, 30)
        elif alert_summary.warning > 0:
            overall_score = min(overall_score, 70)

        return SummaryHealthScore(
            financial=financial_score,
            operational=operational_score,
            automation=automation_score,
            overall=overall_score,
        )

    def _generate_recommendations(
        self,
        health_scores: SummaryHealthScore,
        financial_data: SummaryFinancialData,
        operational_data: SummaryOperationalData,
        alert_summary: SummaryAlertSummary,
    ) -> list[str]:
        """生成建议"""
        recommendations = []

        # 基于健康评分
        if health_scores.overall < 50:
            recommendations.append("系统健康度较低，建议全面检查")

        if health_scores.financial < 50:
            recommendations.append("财务健康度低，检查预算状态")

        if health_scores.operational < 50:
            recommendations.append("运营健康度低，检查自动化执行成功率")

        if health_scores.automation < 50:
            recommendations.append("自动化健康度低，检查自动化活动频率")

        # 基于财务数据
        if financial_data.current_mode == "paused":
            recommendations.append("预算已暂停，需要手动重置或等待周期重置")
        elif financial_data.current_mode == "critical":
            recommendations.append("预算临界，仅执行核心任务")
        elif financial_data.utilization > 0.8:
            recommendations.append("预算使用率高，准备暂停非必要任务")

        # 基于运营数据
        if operational_data.automation_success_rate < 0.7:
            recommendations.append(
                f"自动化成功率较低 ({operational_data.automation_success_rate:.0%})，检查错误原因"
            )

        # 基于告警
        if alert_summary.critical > 0:
            recommendations.append(f"有{alert_summary.critical}个严重告警需要立即处理")
        if alert_summary.warning > 0:
            recommendations.append(f"有{alert_summary.warning}个警告需要关注")

        # 默认建议
        if not recommendations:
            recommendations.append("系统运行正常，保持监控")

        return recommendations

    def generate_summary(self, save_artifact: bool = True) -> SummaryDashboardPayload:
        """生成摘要"""
        logger.info("开始生成运营/资金摘要")

        # 收集数据
        financial_data = self._collect_financial_data()
        operational_data = self._collect_operational_data()
        alert_summary = self._collect_alert_summary()

        # 计算健康评分
        health_scores = self._calculate_health_scores(
            financial_data, operational_data, alert_summary
        )

        # 生成建议
        recommendations = self._generate_recommendations(
            health_scores, financial_data, operational_data, alert_summary
        )

        # 构建关键指标
        key_metrics = {
            "budget_remaining_ratio": financial_data.remaining_budget
            / max(financial_data.daily_budget, 1),
            "automation_volume_today": operational_data.automation_requests_today,
            "alert_critical_ratio": alert_summary.critical / max(alert_summary.total, 1),
            "burn_rate_vs_budget": financial_data.burn_rate
            / max(financial_data.daily_budget / 24, 0.01),
        }

        # 构建详细报告链接
        detailed_reports = {
            "financial_dashboard": "workspace/automation_evidence/",  # 简化
            "alert_logs": "logs/alerts.log",
            "automation_evidence": "workspace/automation_evidence/",
        }

        # 创建摘要ID
        summary_id = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 构建负载
        payload = SummaryDashboardPayload(
            summary_id=summary_id,
            health_scores=health_scores,
            alert_summary=alert_summary,
            financial_data=financial_data,
            operational_data=operational_data,
            key_metrics=key_metrics,
            recommendations=recommendations,
            detailed_reports=detailed_reports,
        )

        # 保存artifact（如果请求）
        if save_artifact:
            self._save_artifact(payload)

        logger.info(f"摘要生成完成: {summary_id}, 整体健康度: {health_scores.overall}")

        return payload

    def _save_artifact(self, payload: SummaryDashboardPayload):
        """保存artifact文件"""
        try:
            # 创建文件名
            filename = f"summary_{payload.summary_id}.json"
            artifact_file = self.output_dir / filename

            # 保存JSON
            with open(artifact_file, "w", encoding="utf-8") as f:
                f.write(payload.to_json(indent=2))

            logger.info(f"摘要artifact已保存: {artifact_file}")

            # 同时保存一个最新版本的引用
            latest_file = self.output_dir / "summary_latest.json"
            with open(latest_file, "w", encoding="utf-8") as f:
                f.write(payload.to_json(indent=2))

            return str(artifact_file)

        except Exception as e:
            logger.error(f"保存摘要artifact失败: {e}")
            return None

    def generate_text_report(self, payload: SummaryDashboardPayload) -> str:
        """生成文本报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("📊 运营/资金摘要报告")
        lines.append("=" * 60)
        lines.append(f"📅 生成时间: {payload.timestamp}")
        lines.append(f"🆔 摘要ID: {payload.summary_id}")
        lines.append("")

        # 健康评分
        lines.append("🏥 健康评分:")
        lines.append(f"  整体: {payload.health_scores.overall}/100")
        lines.append(f"  财务: {payload.health_scores.financial}/100")
        lines.append(f"  运营: {payload.health_scores.operational}/100")
        lines.append(f"  自动化: {payload.health_scores.automation}/100")
        lines.append("")

        # 财务摘要
        lines.append("💰 财务摘要:")
        lines.append(f"  剩余预算: ¥{payload.financial_data.remaining_budget:.2f}")
        lines.append(f"  每日预算: ¥{payload.financial_data.daily_budget:.2f}")
        lines.append(f"  燃烧率: ¥{payload.financial_data.burn_rate:.2f}/小时")
        lines.append(f"  使用率: {payload.financial_data.utilization:.1%}")
        lines.append(f"  当前模式: {payload.financial_data.current_mode}")
        lines.append(f"  距离重置: {payload.financial_data.days_until_reset}天")
        lines.append("")

        # 运营摘要
        lines.append("⚙️ 运营摘要:")
        lines.append(f"  自动化请求总数: {payload.operational_data.automation_requests_total}")
        lines.append(f"  今日自动化请求: {payload.operational_data.automation_requests_today}")
        lines.append(f"  自动化成功率: {payload.operational_data.automation_success_rate:.1%}")
        if payload.operational_data.last_automation_time:
            last_time = datetime.fromisoformat(payload.operational_data.last_automation_time)
            hours_ago = (datetime.now() - last_time).total_seconds() / 3600
            lines.append(f"  最后自动化执行: {hours_ago:.1f}小时前")
        lines.append("")

        # 告警摘要
        lines.append("🚨 告警摘要:")
        lines.append(
            f"  严重: {payload.alert_summary.critical} | 警告: {payload.alert_summary.warning} | 信息: {payload.alert_summary.info}"
        )
        lines.append(f"  总计: {payload.alert_summary.total}")
        lines.append("")

        # 建议
        lines.append("💡 建议:")
        for i, rec in enumerate(payload.recommendations, 1):
            lines.append(f"  {i}. {rec}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


# ==================== 全局实例 ====================

_summary_generator_instance: SummaryGenerator | None = None


def get_summary_generator() -> SummaryGenerator:
    """获取全局摘要生成器实例"""
    global _summary_generator_instance
    if _summary_generator_instance is None:
        _summary_generator_instance = SummaryGenerator()
    return _summary_generator_instance


# ==================== 命令行接口 ====================


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="运营/资金摘要生成器")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="保存artifact文件",
    )
    parser.add_argument(
        "--output-dir",
        help="artifact输出目录",
    )

    args = parser.parse_args()

    # 创建生成器
    generator = SummaryGenerator(output_dir=args.output_dir)

    # 生成摘要
    payload = generator.generate_summary(save_artifact=args.save)

    # 输出
    if args.format == "json":
        print(payload.to_json(indent=2))
    else:  # text
        report = generator.generate_text_report(payload)
        print(report)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=== 运营/资金摘要生成器测试 ===")

    # 创建生成器
    generator = SummaryGenerator()

    print("\n1. 测试摘要生成:")
    payload = generator.generate_summary(save_artifact=False)
    print(f"   摘要ID: {payload.summary_id}")
    print(f"   生成时间: {payload.timestamp}")
    print(f"   整体健康度: {payload.health_scores.overall}/100")

    print("\n2. 测试文本报告:")
    report = generator.generate_text_report(payload)
    print(report[:500] + "...")  # 只显示前500字符

    print("\n3. 测试artifact保存:")
    artifact_path = generator._save_artifact(payload)
    if artifact_path:
        print(f"   Artifact已保存: {artifact_path}")
    else:
        print("   Artifact保存失败")

    print("\n=== 测试完成 ===")
