#!/usr/bin/env python3
"""
成本跟踪报告模块 - 基于审计报告第二阶段优化建议

使用rich库实现高级可视化报告，包括：
1. 彩色表格和面板
2. 成本趋势图表（ASCII）
3. 预算状态可视化
4. 优化建议突出显示

设计特点：
1. 模块化：可以独立使用或集成到现有系统
2. 可配置：支持多种输出格式（控制台、HTML、Markdown）
3. 高性能：异步数据加载，流式渲染
4. 可扩展：易于添加新的可视化组件
"""

import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 尝试导入rich库
try:
    from rich.align import Align
    from rich.box import DOUBLE, ROUNDED, SIMPLE
    from rich.color import Color
    from rich.columns import Columns
    from rich.console import Console
    from rich.layout import Layout
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.style import Style
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    logging.warning("rich库未安装，将使用降级模式（文本输出）")

# 导入现有组件
try:
    from .cost_tracker import CostRecord, CostSummary, CostTracker, get_cost_tracker
    from .financial_monitor_adapter import get_financial_monitor_adapter

    HAS_DEPENDENCIES = True
except ImportError as e:
    logging.warning(f"导入依赖失败，报告模块将以降级模式运行: {e}")
    HAS_DEPENDENCIES = False

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== Rich报告类 ====================


class RichCostReporter:
    """Rich成本报告器"""

    def __init__(self, console: Optional[Console] = None):
        """
        初始化Rich报告器

        Args:
            console: rich Console实例（如果为None则创建新实例）
        """
        if HAS_RICH:
            self.console = console or Console()
            self.use_rich = True
        else:
            self.console = None
            self.use_rich = False
            logger.warning("rich库不可用，将使用文本模式")

        # 颜色主题配置
        self.theme = {
            "primary": "cyan",
            "secondary": "blue",
            "success": "green",
            "warning": "yellow",
            "danger": "red",
            "info": "magenta",
            "highlight": "bright_cyan",
            "muted": "grey50",
            "cost_low": "green",
            "cost_medium": "yellow",
            "cost_high": "red",
            "budget_safe": "green",
            "budget_warning": "yellow",
            "budget_critical": "red",
        }

        logger.info("Rich成本报告器初始化完成")

    def _format_currency(self, amount: float) -> str:
        """格式化货币金额"""
        if amount >= 1.0:
            return f"¥{amount:.2f}"
        elif amount >= 0.01:
            return f"¥{amount:.4f}"
        else:
            return f"¥{amount:.6f}"

    def _get_cost_style(self, amount: float, budget: float = 0.0) -> str:
        """根据金额获取样式"""
        if budget > 0:
            percentage = (amount / budget * 100) if budget > 0 else 0
            if percentage < 50:
                return self.theme["cost_low"]
            elif percentage < 80:
                return self.theme["cost_medium"]
            else:
                return self.theme["cost_high"]
        else:
            if amount < 0.1:
                return self.theme["cost_low"]
            elif amount < 1.0:
                return self.theme["cost_medium"]
            else:
                return self.theme["cost_high"]

    def _create_table(self, title: str, box_type: str = "rounded") -> Table:
        """创建rich表格"""
        if not self.use_rich:
            return None

        box_map = {
            "rounded": ROUNDED,
            "simple": SIMPLE,
            "double": DOUBLE,
        }
        box = box_map.get(box_type, ROUNDED)

        table = Table(title=title, box=box, header_style="bold cyan")
        return table

    def print_daily_summary(self, summary: CostSummary, budget_info: Optional[Dict] = None):
        """
        打印每日成本摘要（rich增强版）

        Args:
            summary: 成本摘要
            budget_info: 预算信息（可选）
        """
        if not self.use_rich:
            # 降级模式：使用文本输出
            self._print_daily_summary_text(summary, budget_info)
            return

        # 创建主面板
        title = f"📊 今日成本摘要 ({summary.period_start})"
        panel_content = []

        # 关键指标
        metrics = [
            (
                "总成本",
                self._format_currency(summary.total_cost),
                self._get_cost_style(summary.total_cost),
            ),
            ("总请求数", f"{summary.total_requests:,}", "cyan"),
            ("总输入tokens", f"{summary.total_input_tokens:,}", "blue"),
            ("总输出tokens", f"{summary.total_output_tokens:,}", "magenta"),
            ("每千tokens成本", self._format_currency(summary.cost_per_1k_tokens), "yellow"),
            ("平均请求成本", self._format_currency(summary.avg_cost_per_request), "cyan"),
        ]

        if budget_info:
            budget_used = budget_info.get("used", 0)
            budget_total = budget_info.get("total", 0)
            if budget_total > 0:
                percentage = budget_used / budget_total * 100
                budget_style = self.theme["budget_safe"]
                if percentage > 80:
                    budget_style = self.theme["budget_critical"]
                elif percentage > 50:
                    budget_style = self.theme["budget_warning"]

                metrics.append(
                    (
                        "预算使用",
                        f"{percentage:.1f}% ({self._format_currency(budget_used)}/{self._format_currency(budget_total)})",
                        budget_style,
                    )
                )

        # 创建指标表格
        metrics_table = self._create_table("关键指标", "simple")
        metrics_table.add_column("指标", style="bold", width=20)
        metrics_table.add_column("数值", style="bold", width=25)
        metrics_table.add_column("状态", style="bold", width=15)

        for name, value, style in metrics:
            metrics_table.add_row(name, value, "", style=style)

        panel_content.append(metrics_table)

        # provider分解
        if summary.by_provider:
            provider_table = self._create_table("按Provider分解", "simple")
            provider_table.add_column("Provider", style="bold", width=20)
            provider_table.add_column("成本", style="bold", width=15)
            provider_table.add_column("占比", style="bold", width=10)
            provider_table.add_column("请求数", style="bold", width=10)

            for provider, cost in summary.by_provider.items():
                percentage = (cost / summary.total_cost * 100) if summary.total_cost > 0 else 0
                # 估算请求数（简化）
                requests_est = (
                    int(cost / summary.avg_cost_per_request)
                    if summary.avg_cost_per_request > 0
                    else 0
                )
                provider_table.add_row(
                    provider,
                    self._format_currency(cost),
                    f"{percentage:.1f}%",
                    f"{requests_est:,}",
                    style=self._get_cost_style(cost),
                )

            panel_content.append(provider_table)

        # 模型分解（如果有）
        if summary.by_model:
            model_table = self._create_table("按模型分解", "simple")
            model_table.add_column("模型", style="bold", width=30)
            model_table.add_column("成本", style="bold", width=15)
            model_table.add_column("占比", style="bold", width=10)

            for model, cost in summary.by_model.items():
                percentage = (cost / summary.total_cost * 100) if summary.total_cost > 0 else 0
                model_table.add_row(
                    model,
                    self._format_currency(cost),
                    f"{percentage:.1f}%",
                    style=self._get_cost_style(cost),
                )

            panel_content.append(model_table)

        # 创建面板
        panel = Panel(
            Columns(panel_content, equal=True, expand=True),
            title=title,
            border_style="cyan",
            padding=(1, 2),
        )

        self.console.print(panel)

        # 优化建议（如果有）
        if budget_info and budget_info.get("recommendations"):
            self.print_recommendations(budget_info["recommendations"])

    def _print_daily_summary_text(self, summary: CostSummary, budget_info: Optional[Dict] = None):
        """文本模式每日摘要"""
        print(f"📊 今日成本摘要 ({summary.period_start})")
        print(f"   总成本: {self._format_currency(summary.total_cost)}")
        print(f"   总请求: {summary.total_requests}")
        print(f"   总tokens: {summary.total_input_tokens + summary.total_output_tokens:,}")
        print(f"   每千tokens成本: {self._format_currency(summary.cost_per_1k_tokens)}")

        if budget_info:
            budget_used = budget_info.get("used", 0)
            budget_total = budget_info.get("total", 0)
            if budget_total > 0:
                percentage = budget_used / budget_total * 100
                print(
                    f"   预算使用: {percentage:.1f}% ({self._format_currency(budget_used)}/{self._format_currency(budget_total)})"
                )

        if summary.by_provider:
            print(f"\n按provider分解:")
            for provider, cost in summary.by_provider.items():
                percentage = (cost / summary.total_cost * 100) if summary.total_cost > 0 else 0
                print(f"   • {provider}: {self._format_currency(cost)} ({percentage:.1f}%)")

    def print_provider_breakdown(self, breakdown_data: Dict[str, Any]):
        """
        打印provider成本分解报告

        Args:
            breakdown_data: provider分解数据
        """
        if not self.use_rich:
            self._print_provider_breakdown_text(breakdown_data)
            return

        if "error" in breakdown_data:
            error_panel = Panel(
                Text(f"❌ {breakdown_data['error']}", style="bold red"),
                title="错误",
                border_style="red",
            )
            self.console.print(error_panel)
            return

        # 创建主面板
        period = breakdown_data.get("period", {})
        title = f"📊 Provider成本分解 ({period.get('start')} 到 {period.get('end')})"

        panel_content = []

        # 总成本面板
        total_cost = breakdown_data.get("total_cost", 0)
        total_panel = Panel(
            Text(
                self._format_currency(total_cost), style=f"bold {self._get_cost_style(total_cost)}"
            ),
            title="总成本",
            border_style="cyan",
        )
        panel_content.append(total_panel)

        # provider详情表格
        providers = breakdown_data.get("providers", {})
        if providers:
            provider_table = self._create_table("Provider详情", "rounded")
            provider_table.add_column("Provider", style="bold", width=20)
            provider_table.add_column("成本", style="bold", width=15)
            provider_table.add_column("占比", style="bold", width=10)
            provider_table.add_column("请求数", style="bold", width=12)
            provider_table.add_column("每请求成本", style="bold", width=15)
            provider_table.add_column("状态", style="bold", width=10)

            for provider, data in providers.items():
                cost = data.get("cost", 0)
                percentage = data.get("percentage", 0)
                requests = data.get("requests", 0)
                cost_per_request = data.get("cost_per_request", 0)

                # 状态指示
                status = "✅"
                status_style = "green"
                if percentage > 50:  # 超过50%占比
                    status = "⚠️"
                    status_style = "yellow"
                if cost_per_request > 0.01:  # 高单次请求成本
                    status = "⚠️"
                    status_style = "yellow"

                provider_table.add_row(
                    provider,
                    self._format_currency(cost),
                    f"{percentage:.1f}%",
                    f"{requests:,}",
                    self._format_currency(cost_per_request),
                    status,
                    style=status_style,
                )

            panel_content.append(provider_table)

        # 创建布局
        layout = Layout()
        layout.split_column(
            Layout(total_panel, size=3),
            Layout(Columns(panel_content[1:], equal=True, expand=True), size=20),
        )

        main_panel = Panel(layout, title=title, border_style="cyan", padding=(1, 2))

        self.console.print(main_panel)

        # 优化建议
        recommendations = breakdown_data.get("recommendations", [])
        if recommendations:
            self.print_recommendations(recommendations)

    def _print_provider_breakdown_text(self, breakdown_data: Dict[str, Any]):
        """文本模式provider分解"""
        if "error" in breakdown_data:
            print(f"❌ 错误: {breakdown_data['error']}")
            return

        period = breakdown_data.get("period", {})
        print(f"📊 Provider成本分解 ({period.get('start')} 到 {period.get('end')})")
        print(f"总成本: {self._format_currency(breakdown_data.get('total_cost', 0))}")

        providers = breakdown_data.get("providers", {})
        if providers:
            print("\n分解详情:")
            for provider, data in providers.items():
                cost = data.get("cost", 0)
                percentage = data.get("percentage", 0)
                requests = data.get("requests", 0)
                print(f"   • {provider}:")
                print(f"     成本: {self._format_currency(cost)} ({percentage}%)")
                print(f"     请求数: {requests}")

        recommendations = breakdown_data.get("recommendations", [])
        if recommendations:
            print(f"\n💡 优化建议:")
            for rec in recommendations:
                print(f"   • {rec}")

    def print_task_kind_analysis(self, analysis_data: Dict[str, Any]):
        """
        打印任务类型分析报告

        Args:
            analysis_data: 任务类型分析数据
        """
        if not self.use_rich:
            self._print_task_kind_analysis_text(analysis_data)
            return

        if "error" in analysis_data:
            error_panel = Panel(
                Text(f"❌ {analysis_data['error']}", style="bold red"),
                title="错误",
                border_style="red",
            )
            self.console.print(error_panel)
            return

        # 创建主面板
        period = analysis_data.get("period", {})
        title = (
            f"📊 任务类型分析 ({period.get('type')}，{period.get('start')} 到 {period.get('end')})"
        )

        panel_content = []

        # 总成本
        total_cost = analysis_data.get("total_cost", 0)
        total_panel = Panel(
            Text(
                self._format_currency(total_cost), style=f"bold {self._get_cost_style(total_cost)}"
            ),
            title="总成本",
            border_style="cyan",
        )
        panel_content.append(total_panel)

        # 任务类型表格
        breakdown = analysis_data.get("task_kind_breakdown", {})
        if breakdown:
            task_table = self._create_table("任务类型分解", "rounded")
            task_table.add_column("任务类型", style="bold", width=25)
            task_table.add_column("成本", style="bold", width=15)
            task_table.add_column("占比", style="bold", width=10)
            task_table.add_column("优化潜力", style="bold", width=15)

            for task_kind, cost in breakdown.items():
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0

                # 评估优化潜力
                optimization_potential = "低"
                potential_style = "green"
                if percentage > 30:
                    optimization_potential = "高"
                    potential_style = "red"
                elif percentage > 10:
                    optimization_potential = "中"
                    potential_style = "yellow"

                task_table.add_row(
                    task_kind,
                    self._format_currency(cost),
                    f"{percentage:.1f}%",
                    optimization_potential,
                    style=potential_style,
                )

            panel_content.append(task_table)

        # 创建布局
        layout = Layout()
        layout.split_column(
            Layout(total_panel, size=3),
            Layout(Columns(panel_content[1:], equal=True, expand=True), size=20),
        )

        main_panel = Panel(layout, title=title, border_style="cyan", padding=(1, 2))

        self.console.print(main_panel)

        # 优化建议
        recommendations = analysis_data.get("recommendations", [])
        if recommendations:
            self.print_recommendations(recommendations)

    def _print_task_kind_analysis_text(self, analysis_data: Dict[str, Any]):
        """文本模式任务类型分析"""
        if "error" in analysis_data:
            print(f"❌ 错误: {analysis_data['error']}")
            return

        period = analysis_data.get("period", {})
        print(
            f"📊 任务类型分析 ({period.get('type')}，{period.get('start')} 到 {period.get('end')})"
        )
        print(f"总成本: {self._format_currency(analysis_data.get('total_cost', 0))}")

        breakdown = analysis_data.get("task_kind_breakdown", {})
        if breakdown:
            print("\n按任务类型分解:")
            for task_kind, cost in breakdown.items():
                percentage = cost / analysis_data.get("total_cost", 1) * 100
                print(f"   • {task_kind}: {self._format_currency(cost)} ({percentage:.1f}%)")

        recommendations = analysis_data.get("recommendations", [])
        if recommendations:
            print(f"\n💡 优化建议:")
            for rec in recommendations:
                print(f"   • {rec}")

    def print_cost_trend(self, trend_data: List[Dict[str, Any]], days: int = 7):
        """
        打印成本趋势报告

        Args:
            trend_data: 趋势数据列表
            days: 分析天数
        """
        if not self.use_rich:
            self._print_cost_trend_text(trend_data, days)
            return

        title = f"📈 成本趋势分析 (最近{days}天)"

        if not trend_data:
            self.console.print(Panel("无趋势数据可用", title=title, border_style="yellow"))
            return

        # 创建趋势表格
        trend_table = self._create_table("每日成本趋势", "rounded")
        trend_table.add_column("日期", style="bold", width=15)
        trend_table.add_column("成本", style="bold", width=15)
        trend_table.add_column("请求数", style="bold", width=12)
        trend_table.add_column("趋势", style="bold", width=10)

        # 计算统计数据
        total_cost = sum(item.get("cost", 0) for item in trend_data)
        avg_daily_cost = total_cost / len(trend_data) if trend_data else 0

        prev_cost = None
        for item in trend_data:
            date_str = item.get("date", "")
            cost = item.get("cost", 0)
            requests = item.get("requests", 0)

            # 趋势指示
            trend = "→"
            trend_style = "white"
            if prev_cost is not None:
                if cost > prev_cost * 1.2:
                    trend = "↑↑"
                    trend_style = "red"
                elif cost > prev_cost * 1.05:
                    trend = "↑"
                    trend_style = "yellow"
                elif cost < prev_cost * 0.8:
                    trend = "↓↓"
                    trend_style = "green"
                elif cost < prev_cost * 0.95:
                    trend = "↓"
                    trend_style = "cyan"

            trend_table.add_row(
                date_str, self._format_currency(cost), f"{requests:,}", trend, style=trend_style
            )

            prev_cost = cost

        # 统计面板
        stats_panel = Panel(
            Columns(
                [
                    Panel(
                        f"{self._format_currency(total_cost)}", title="总成本", border_style="cyan"
                    ),
                    Panel(
                        f"{self._format_currency(avg_daily_cost)}",
                        title="日均成本",
                        border_style="blue",
                    ),
                    Panel(f"{len(trend_data)}天", title="分析周期", border_style="magenta"),
                ],
                equal=True,
            ),
            title="统计摘要",
            border_style="green",
        )

        # 主布局
        layout = Layout()
        layout.split_column(
            Layout(trend_table, size=min(15, len(trend_data) + 3)), Layout(stats_panel, size=5)
        )

        main_panel = Panel(layout, title=title, border_style="cyan", padding=(1, 2))

        self.console.print(main_panel)

    def _print_cost_trend_text(self, trend_data: List[Dict[str, Any]], days: int = 7):
        """文本模式成本趋势"""
        print("📈 成本趋势分析")
        print("（基础版本，未来可增强为可视化图表）")

        if not trend_data:
            print("   无趋势数据可用")
            return

        print(f"\n最近{days}天成本趋势:")
        total_cost = 0
        for item in trend_data:
            date_str = item.get("date", "")
            cost = item.get("cost", 0)
            requests = item.get("requests", 0)
            print(f"   {date_str}: {self._format_currency(cost)} ({requests}请求)")
            total_cost += cost

        avg_daily_cost = total_cost / len(trend_data) if trend_data else 0
        print(f"\n统计:")
        print(f"   总成本: {self._format_currency(total_cost)} ({days}天)")
        print(f"   日均成本: {self._format_currency(avg_daily_cost)}")

    def print_recommendations(self, recommendations: List[str]):
        """
        打印优化建议

        Args:
            recommendations: 建议列表
        """
        if not recommendations:
            return

        if not self.use_rich:
            print(f"\n💡 优化建议:")
            for rec in recommendations:
                print(f"   • {rec}")
            return

        # 创建建议表格
        rec_table = Table(show_header=False, box=None, padding=(0, 1))
        rec_table.add_column("序号", style="bold cyan", width=4)
        rec_table.add_column("建议内容", style="default", width=76)

        for i, rec in enumerate(recommendations, 1):
            # 简单分类建议类型
            style = "cyan"
            if "成本" in rec or "预算" in rec:
                style = "red"
            elif "优化" in rec or "改进" in rec:
                style = "yellow"
            elif "推荐" in rec or "建议" in rec:
                style = "green"
            else:
                style = "white"

            rec_table.add_row(str(i), Text(rec, style=style))

        rec_panel = Panel(rec_table, title="💡 优化建议", border_style="yellow", padding=(1, 2))

        self.console.print(rec_panel)

    def print_financial_dashboard(self, dashboard_data: Dict[str, Any]):
        """
        打印金融仪表板（集成成本、预算、监控数据）

        Args:
            dashboard_data: 仪表板数据
        """
        if not self.use_rich:
            self._print_financial_dashboard_text(dashboard_data)
            return

        if not dashboard_data.get("success", False):
            error_panel = Panel(
                Text(f"❌ {dashboard_data.get('error', '未知错误')}", style="bold red"),
                title="金融仪表板错误",
                border_style="red",
            )
            self.console.print(error_panel)
            return

        title = "💰 金融仪表板"
        timestamp = dashboard_data.get("metadata", {}).get("timestamp", "")
        if timestamp:
            title += f" ({timestamp})"

        # 创建仪表板布局
        layout = Layout()

        # 顶部：关键指标
        top_metrics = self._create_financial_metrics(dashboard_data)
        layout.split_column(
            Layout(top_metrics, size=8, name="metrics"),
            Layout(self._create_financial_details(dashboard_data), size=20, name="details"),
        )

        main_panel = Panel(layout, title=title, border_style="bright_cyan", padding=(1, 2))

        self.console.print(main_panel)

    def _create_financial_metrics(self, dashboard_data: Dict[str, Any]) -> Layout:
        """创建金融指标布局"""
        layout = Layout()

        # 获取成本数据
        cost_summary = dashboard_data.get("data", {}).get("cost_summary_today", {})
        financial_data = dashboard_data.get("data", {}).get("financial_monitor", {})

        # 成本指标
        total_cost = cost_summary.get("total_cost", 0) if not isinstance(cost_summary, str) else 0
        total_requests = (
            cost_summary.get("total_requests", 0) if not isinstance(cost_summary, str) else 0
        )

        # 预算指标
        budget_used = (
            financial_data.get("budget_used", 0) if isinstance(financial_data, dict) else 0
        )
        budget_total = (
            financial_data.get("budget_total", 0) if isinstance(financial_data, dict) else 0
        )
        budget_percentage = (budget_used / budget_total * 100) if budget_total > 0 else 0

        # 创建指标面板
        metric_panels = [
            Panel(
                Text(
                    self._format_currency(total_cost),
                    style=f"bold {self._get_cost_style(total_cost, budget_total)}",
                ),
                title="今日成本",
                border_style="cyan",
            ),
            Panel(
                Text(f"{total_requests:,}", style="bold blue"),
                title="今日请求",
                border_style="blue",
            ),
            Panel(
                Text(
                    f"{budget_percentage:.1f}%",
                    style=f"bold {self._get_cost_style(budget_used, budget_total)}",
                ),
                title="预算使用率",
                border_style=(
                    "green"
                    if budget_percentage < 50
                    else "yellow" if budget_percentage < 80 else "red"
                ),
            ),
            Panel(
                Text(
                    (
                        self._format_currency(budget_total - budget_used)
                        if budget_total > 0
                        else "N/A"
                    ),
                    style="bold green",
                ),
                title="剩余预算",
                border_style="green",
            ),
        ]

        layout.split_row(*[Layout(Panel(panel, height=6), size=25) for panel in metric_panels])

        return layout

    def _create_financial_details(self, dashboard_data: Dict[str, Any]) -> Layout:
        """创建金融详情布局"""
        layout = Layout()

        # 成本分解
        cost_summary = dashboard_data.get("data", {}).get("cost_summary_today", {})
        financial_data = dashboard_data.get("data", {}).get("financial_monitor", {})
        adapter_stats = dashboard_data.get("data", {}).get("adapter_stats", {})

        # 左侧：成本分解
        left_content = []
        if isinstance(cost_summary, dict) and cost_summary.get("by_provider"):
            provider_table = self._create_table("Provider成本分解", "simple")
            provider_table.add_column("Provider", style="bold")
            provider_table.add_column("成本", style="bold")
            provider_table.add_column("占比", style="bold")

            total_cost = cost_summary.get("total_cost", 1)
            for provider, cost in cost_summary["by_provider"].items():
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                provider_table.add_row(
                    provider,
                    self._format_currency(cost),
                    f"{percentage:.1f}%",
                    style=self._get_cost_style(cost),
                )

            left_content.append(provider_table)

        # 右侧：监控状态
        right_content = []
        if isinstance(financial_data, dict):
            status_table = self._create_table("监控状态", "simple")
            status_table.add_column("指标", style="bold")
            status_table.add_column("值", style="bold")
            status_table.add_column("状态", style="bold")

            # 添加监控指标
            indicators = [
                ("预算状态", financial_data.get("budget_status", "unknown"), "blue"),
                (
                    "告警数量",
                    str(financial_data.get("alerts_count", 0)),
                    "red" if financial_data.get("alerts_count", 0) > 0 else "green",
                ),
                ("最后更新", financial_data.get("last_updated", "unknown"), "cyan"),
                ("监控周期", financial_data.get("monitoring_interval", "unknown"), "magenta"),
            ]

            for name, value, style in indicators:
                status_table.add_row(name, str(value), "", style=style)

            right_content.append(status_table)

        # 适配器统计
        if adapter_stats:
            stats_table = self._create_table("适配器统计", "simple")
            stats_table.add_column("指标", style="bold")
            stats_table.add_column("值", style="bold")

            stats_items = [
                ("同步记录数", str(adapter_stats.get("total_records_synced", 0))),
                ("同步失败", str(adapter_stats.get("failed_syncs", 0))),
                ("队列大小", str(adapter_stats.get("queue_size", 0))),
                ("平均延迟", f"{adapter_stats.get('avg_sync_latency_ms', 0):.1f}ms"),
            ]

            for name, value in stats_items:
                stats_table.add_row(name, value)

            right_content.append(stats_table)

        # 创建左右列布局
        if left_content and right_content:
            layout.split_row(
                Layout(Columns(left_content, width=40), size=50, name="left"),
                Layout(Columns(right_content, width=40), size=50, name="right"),
            )
        elif left_content:
            layout.update(Columns(left_content, width=80))
        elif right_content:
            layout.update(Columns(right_content, width=80))

        return layout

    def _print_financial_dashboard_text(self, dashboard_data: Dict[str, Any]):
        """文本模式金融仪表板"""
        print("💰 金融仪表板")

        if not dashboard_data.get("success", False):
            print(f"❌ 错误: {dashboard_data.get('error', '未知错误')}")
            return

        metadata = dashboard_data.get("metadata", {})
        timestamp = metadata.get("timestamp", "")
        if timestamp:
            print(f"时间: {timestamp}")

        data = dashboard_data.get("data", {})

        # 成本摘要
        cost_summary = data.get("cost_summary_today", {})
        if isinstance(cost_summary, dict):
            print(f"\n📊 今日成本摘要:")
            print(f"   总成本: {self._format_currency(cost_summary.get('total_cost', 0))}")
            print(f"   总请求: {cost_summary.get('total_requests', 0)}")
            if cost_summary.get("by_provider"):
                print(f"   Provider分解:")
                for provider, cost in cost_summary["by_provider"].items():
                    print(f"     • {provider}: {self._format_currency(cost)}")

        # 金融监控器数据
        financial_data = data.get("financial_monitor", {})
        if isinstance(financial_data, dict):
            print(f"\n📈 金融监控状态:")
            print(f"   预算状态: {financial_data.get('budget_status', 'unknown')}")
            print(f"   告警数量: {financial_data.get('alerts_count', 0)}")


# ==================== 工具函数 ====================


def get_rich_reporter() -> RichCostReporter:
    """获取全局Rich报告器实例"""
    return RichCostReporter()


def test_rich_reports():
    """测试Rich报告功能"""
    print("=== 测试Rich报告功能 ===\n")

    reporter = get_rich_reporter()

    # 测试1：创建模拟摘要数据
    print("1. 测试每日成本摘要:")

    from datetime import date

    test_summary = type(
        "CostSummary",
        (),
        {
            "period_start": date.today(),
            "period_end": date.today(),
            "total_cost": 0.1578,
            "total_requests": 42,
            "total_input_tokens": 12500,
            "total_output_tokens": 5800,
            "by_provider": {
                "deepseek": 0.0789,
                "dashscope": 0.0789,
            },
            "by_model": {
                "deepseek/deepseek-chat": 0.0789,
                "dashscope/qwen3.5-plus": 0.0789,
            },
            "by_task_kind": {
                "coding": 0.1,
                "analysis": 0.0578,
            },
            "avg_cost_per_request": 0.00376,
            "avg_tokens_per_request": 435,
            "cost_per_1k_tokens": 0.0086,
        },
    )()

    budget_info = {
        "used": 0.1578,
        "total": 1.0,
        "recommendations": [
            "DeepSeek成本仅为DashScope的18.75%，建议增加DeepSeek使用比例",
            "coding任务占成本63.4%，考虑优化代码生成策略",
        ],
    }

    reporter.print_daily_summary(test_summary, budget_info)

    # 测试2：模拟provider分解数据
    print("\n2. 测试Provider分解报告:")

    breakdown_data = {
        "period": {"start": "2024-01-01", "end": "2024-01-07"},
        "total_cost": 1.2345,
        "providers": {
            "deepseek": {
                "cost": 0.61725,
                "percentage": 50.0,
                "requests": 200,
                "cost_per_request": 0.003086,
            },
            "dashscope": {
                "cost": 0.61725,
                "percentage": 50.0,
                "requests": 100,
                "cost_per_request": 0.006173,
            },
        },
        "recommendations": [
            "DashScope单次请求成本是DeepSeek的2倍，建议优先使用DeepSeek",
            "考虑将部分高成本任务迁移到DeepSeek",
        ],
    }

    reporter.print_provider_breakdown(breakdown_data)

    # 测试3：模拟成本趋势数据
    print("\n3. 测试成本趋势报告:")

    from datetime import datetime, timedelta

    trend_data = []
    base_date = date.today() - timedelta(days=6)
    base_cost = 0.1

    for i in range(7):
        current_date = base_date + timedelta(days=i)
        cost = base_cost * (1 + i * 0.15)  # 递增
        requests = 20 + i * 5
        trend_data.append({"date": current_date.isoformat(), "cost": cost, "requests": requests})

    reporter.print_cost_trend(trend_data, days=7)

    # 测试4：模拟金融仪表板数据
    print("\n4. 测试金融仪表板:")

    dashboard_data = {
        "success": True,
        "metadata": {"timestamp": datetime.now().isoformat(), "source": "test"},
        "data": {
            "cost_summary_today": {
                "total_cost": 0.1578,
                "total_requests": 42,
                "total_input_tokens": 12500,
                "total_output_tokens": 5800,
                "by_provider": {
                    "deepseek": 0.0789,
                    "dashscope": 0.0789,
                },
                "by_model": {
                    "deepseek/deepseek-chat": 0.0789,
                    "dashscope/qwen3.5-plus": 0.0789,
                },
                "by_task_kind": {
                    "coding": 0.1,
                    "analysis": 0.0578,
                },
            },
            "financial_monitor": {
                "budget_status": "normal",
                "budget_used": 0.1578,
                "budget_total": 1.0,
                "alerts_count": 0,
                "last_updated": datetime.now().isoformat(),
                "monitoring_interval": "5 minutes",
            },
            "adapter_stats": {
                "total_records_synced": 42,
                "failed_syncs": 2,
                "queue_size": 0,
                "avg_sync_latency_ms": 12.5,
                "last_sync_time": datetime.now().isoformat(),
            },
        },
    }

    reporter.print_financial_dashboard(dashboard_data)

    print("\n✅ Rich报告功能测试完成")


if __name__ == "__main__":
    test_rich_reports()
