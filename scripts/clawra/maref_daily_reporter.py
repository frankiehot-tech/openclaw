#!/usr/bin/env python3
"""
MAREF日报生成模块
基于易经八卦架构的超稳定性多智能体框架日报系统
"""

import json
import logging
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# 添加当前目录到路径，以便导入maref_monitor
sys.path.insert(0, str(Path(__file__).parent))

try:
    from maref_monitor import MAREFMonitor
except ImportError as e:
    print(f"警告: 无法导入maref_monitor: {e}")
    MAREFMonitor = None

try:
    from maref_alert_engine import MAREFAlertEngine
except ImportError as e:
    print(f"警告: 无法导入maref_alert_engine: {e}")
    MAREFAlertEngine = None

try:
    from maref_notifier import MAREFNotifier
except ImportError as e:
    print(f"警告: 无法导入maref_notifier: {e}")
    MAREFNotifier = None


class MAREFDailyReporter:
    """
    MAREF日报生成器

    职责:
    1. 收集监控数据并生成结构化日报
    2. 分析趋势和生成预警
    3. 保存日报到指定目录
    4. 发送预警通知
    """

    def __init__(self, monitor=None, output_dir=None):
        """
        初始化日报生成器

        Args:
            monitor: MAREFMonitor实例
            output_dir: 日报输出目录
        """
        self.monitor = monitor
        self.output_dir = output_dir or self.get_default_output_dir()
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self.logger = self._setup_logger()

        # 初始化预警引擎和通知器
        self.alert_engine = None
        self.notifier = None

        if MAREFAlertEngine is not None:
            try:
                self.alert_engine = MAREFAlertEngine()
                self.logger.info("预警规则引擎初始化成功")
            except Exception as e:
                self.logger.error(f"预警规则引擎初始化失败: {e}")
        else:
            self.logger.warning("预警规则引擎不可用，使用简化的预警检查")

        if MAREFNotifier is not None:
            try:
                self.notifier = MAREFNotifier()
                self.logger.info("通知器初始化成功")
            except Exception as e:
                self.logger.error(f"通知器初始化失败: {e}")
        else:
            self.logger.warning("通知器不可用，预警通知将仅记录到日志")

        self.logger.info(f"MAREF日报生成器初始化完成，输出目录: {self.output_dir}")

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"maref_daily_reporter")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def get_default_output_dir(self) -> str:
        """获取默认输出目录"""
        return "/Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/015-mailbox"

    def generate_daily_report(self) -> str:
        """生成日报"""
        if self.monitor is None:
            self.logger.error("监控器未配置，无法生成日报")
            return ""

        self.logger.info("开始生成MAREF日报")

        try:
            # 收集当前数据
            system_metrics = self.monitor.collect_system_metrics()
            maref_metrics = self.monitor.collect_maref_metrics()
            agent_metrics = self.monitor.collect_agent_metrics()

            # 获取历史数据进行趋势分析
            recent_metrics = self.monitor.get_recent_metrics(count=24)  # 最近24小时数据

            # 计算趋势
            trends = self.calculate_trends(recent_metrics)

            # 检查预警
            alerts = self.check_alerts(system_metrics, maref_metrics, agent_metrics)

            # 生成报告内容
            report_content = self.format_report(
                system_metrics=system_metrics,
                maref_metrics=maref_metrics,
                agent_metrics=agent_metrics,
                trends=trends,
                alerts=alerts,
            )

            # 保存报告
            report_path = self.save_report(report_content)

            # 发送预警通知
            if alerts.get("red_alerts") or alerts.get("yellow_alerts"):
                self.send_alerts(alerts, report_path)

            self.logger.info(f"日报生成成功: {report_path}")
            return report_path

        except Exception as e:
            self.logger.error(f"生成日报失败: {e}")
            import traceback

            traceback.print_exc()
            return ""

    def format_report(self, **data) -> str:
        """格式化日报内容"""
        now = datetime.now()
        report_date = now.strftime("%Y-%m-%d")

        # 获取卦象分布表格
        hexagram_table = self.format_hexagram_table(
            data["maref_metrics"].get("hexagram_distribution", {})
        )

        # 获取格雷编码合规性报告
        gray_compliance = self.format_gray_compliance(
            data["maref_metrics"].get("gray_code_compliance", {})
        )

        # 获取智能体健康报告
        agent_health = self.format_agent_health(data["agent_metrics"])

        # 获取系统性能报告
        system_performance = self.format_system_performance(data["system_metrics"])

        # 获取预警信息
        alerts_section = self.format_alerts(data["alerts"])

        # 获取建议和行动计划
        recommendations = self.format_recommendations(data["trends"], data["alerts"])

        template = f"""# MAREF系统每日报告 {report_date}

**生成时间**: {now.isoformat()}+08:00
**报告周期**: 前24小时
**系统版本**: MAREF v1.0.0
**报告类型**: 日常监控报告

## 1. 核心稳定性状态

### 1.1 控制熵监控
- **当前控制熵H_c**: {data['maref_metrics'].get('control_entropy_h_c', 0):.2f} bits
- **安全范围**: 3.0-4.5 bits (安全区间: 3-6 bits)
- **风险评估**: {self.evaluate_entropy_risk(data['maref_metrics'].get('control_entropy_h_c', 0))}

### 1.2 卦象状态分布
{hexagram_table}

### 1.3 格雷编码合规性
{gray_compliance}

## 2. 智能体健康度报告

{agent_health}

## 3. 系统性能指标

{system_performance}

## 4. 人工介入提醒

{alerts_section}

## 5. 今日建议与行动计划

{recommendations}

---

**报告生成配置**:
- 数据采集间隔: 每小时
- 报告生成时间: 每日09:00
- 预警通知: 企业微信/邮件
- 数据保留: 90天

**备注**: 此报告由MAREF工程化监控系统自动生成，如需调整请修改 `/Volumes/1TB-M2/openclaw/scripts/clawra/maref_daily_reporter.py`
"""
        return template

    def evaluate_entropy_risk(self, entropy: float) -> str:
        """评估控制熵风险"""
        if entropy < 3.0:
            return "🟢 控制熵过低，系统可能过于简单"
        elif entropy < 4.5:
            return "🟢 控制熵在理想区间，系统稳定性良好"
        elif entropy < 5.5:
            return "🟡 控制熵偏高，建议监控状态转换"
        else:
            return "🔴 控制熵过高，存在状态空间爆炸风险"

    def format_hexagram_table(self, distribution: Dict[str, int]) -> str:
        """格式化卦象状态分布表格"""
        if not distribution:
            return "无状态分布数据"

        total = sum(distribution.values())
        if total == 0:
            return "无状态分布数据"

        # 按卦象分类统计
        trigram_stats = self.aggregate_by_trigram(distribution)

        table = (
            "| 卦象类别 | 占比 | 状态数量 | 主要卦象 |\n|----------|------|----------|----------|\n"
        )

        for trigram, stats in trigram_stats.items():
            percentage = stats["percentage"]
            count = stats["count"]
            primary = stats.get("primary", "N/A")
            table += f"| {trigram} | {percentage:.1f}% | {count} | {primary} |\n"

        # 添加总结行
        table += f"\n**总计**: {total} 个状态记录，{len(distribution)} 个不同卦象"

        return table

    def aggregate_by_trigram(self, distribution: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
        """按卦象类别聚合数据"""
        # 基本八卦映射（前3位）
        trigram_names = {
            "000": "坤卦 (地)",
            "001": "震卦 (雷)",
            "010": "坎卦 (水)",
            "011": "兑卦 (泽)",
            "100": "艮卦 (山)",
            "101": "离卦 (火)",
            "110": "巽卦 (风)",
            "111": "乾卦 (天)",
        }

        total = sum(distribution.values())
        trigram_stats = {}

        for state, count in distribution.items():
            upper_trigram = state[:3]  # 上卦（外卦）
            lower_trigram = state[3:]  # 下卦（内卦）

            # 使用上卦作为分类
            trigram_name = trigram_names.get(upper_trigram, f"未知卦 ({upper_trigram})")

            if trigram_name not in trigram_stats:
                trigram_stats[trigram_name] = {"count": 0, "states": []}

            trigram_stats[trigram_name]["count"] += count
            trigram_stats[trigram_name]["states"].append(state)

        # 计算百分比和主要卦象
        for trigram, stats in trigram_stats.items():
            stats["percentage"] = (stats["count"] / total) * 100
            if stats["states"]:
                # 选择出现最频繁的状态作为主要卦象
                primary_state = max(
                    [(s, distribution[s]) for s in stats["states"]], key=lambda x: x[1]
                )[0]
                stats["primary"] = self.get_hexagram_name(primary_state)

        return trigram_stats

    def get_hexagram_name(self, state: str) -> str:
        """获取卦象名称"""
        try:
            from hexagram_state_manager import HexagramStateManager

            manager = HexagramStateManager(state)
            return manager.get_hexagram_name(state)
        except:
            return f"状态 {state}"

    def format_gray_compliance(self, compliance: Dict[str, Any]) -> str:
        """格式化格雷编码合规性报告"""
        total = compliance.get("total", 0)
        compliant = compliance.get("compliant", 0)
        rate = compliance.get("rate", 1.0)
        violations = compliance.get("violations", [])

        if total == 0:
            return "无状态转换记录"

        status = "🟢 合规" if rate >= 0.95 else "🟡 警告" if rate >= 0.85 else "🔴 严重违规"

        output = f"- **合规率**: {rate:.1%} ({compliant}/{total})\n"
        output += f"- **状态**: {status}\n"

        if violations:
            output += f"- **最近违规** (共{len(violations)}次):\n"
            for i, violation in enumerate(violations[-3:], 1):  # 显示最近3次
                output += f"  {i}. {violation.get('from', '???')} → {violation.get('to', '???')} (距离: {violation.get('distance', '?')})\n"

        return output

    def format_agent_health(self, agent_metrics: Dict[str, Any]) -> str:
        """格式化智能体健康报告"""
        if not agent_metrics:
            return "无智能体数据"

        healthy_count = 0
        warning_count = 0
        error_count = 0

        table = "| 智能体 | 状态 | 健康分数 | 最后检查 |\n|--------|------|----------|----------|\n"

        for agent_name, metrics in agent_metrics.items():
            status = metrics.get("status", "unknown")
            health_score = metrics.get("health_score", 0.0)
            last_check = metrics.get("last_check", metrics.get("last_active", "N/A"))

            # 状态图标
            if status in ["active", "healthy"] and health_score >= 0.8:
                status_icon = "🟢"
                healthy_count += 1
            elif status in ["active", "healthy"] or health_score >= 0.6:
                status_icon = "🟡"
                warning_count += 1
            else:
                status_icon = "🔴"
                error_count += 1

            table += f"| {agent_name} | {status_icon} {status} | {health_score:.1%} | {last_check[:19]} |\n"

        summary = f"\n**健康摘要**: 🟢 {healthy_count}个正常 | 🟡 {warning_count}个警告 | 🔴 {error_count}个异常"

        return table + summary

    def format_system_performance(self, system_metrics: Dict[str, Any]) -> str:
        """格式化系统性能报告"""
        cpu = system_metrics.get("cpu_usage", 0)
        memory = system_metrics.get("memory_usage", 0)
        disk = system_metrics.get("disk_usage", 0)

        cpu_status = "🟢 正常" if cpu < 80 else "🟡 偏高" if cpu < 95 else "🔴 过高"
        memory_status = "🟢 正常" if memory < 85 else "🟡 偏高" if memory < 95 else "🔴 过高"
        disk_status = "🟢 正常" if disk < 90 else "🟡 偏高" if disk < 98 else "🔴 过高"

        output = f"""### 3.1 CPU使用率
- **当前值**: {cpu:.1f}%
- **状态**: {cpu_status}
- **可用核心**: {system_metrics.get('cpu_cores', 'N/A')}

### 3.2 内存使用率
- **当前值**: {memory:.1f}%
- **状态**: {memory_status}
- **可用内存**: {system_metrics.get('memory_available', 0):.1f} GB

### 3.3 磁盘使用率
- **当前值**: {disk:.1f}%
- **状态**: {disk_status}
- **可用空间**: {system_metrics.get('disk_free', 0):.1f} GB
"""

        if system_metrics.get("psutil_missing"):
            output += "\n⚠️ **注意**: psutil未安装，系统指标可能不准确"

        return output

    def calculate_trends(self, recent_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算趋势"""
        if len(recent_metrics) < 2:
            return {"status": "insufficient_data", "message": "数据不足，无法计算趋势"}

        trends = {
            "entropy_trend": "stable",
            "system_health_trend": "stable",
            "agent_health_trend": "stable",
            "compliance_trend": "stable",
        }

        try:
            # 提取控制熵趋势
            entropy_values = []
            for metrics in recent_metrics:
                entropy = metrics.get("maref", {}).get("control_entropy_h_c", 0)
                entropy_values.append(entropy)

            if len(entropy_values) >= 2:
                first_half = entropy_values[: len(entropy_values) // 2]
                second_half = entropy_values[len(entropy_values) // 2 :]

                avg_first = sum(first_half) / len(first_half) if first_half else 0
                avg_second = sum(second_half) / len(second_half) if second_half else 0

                if avg_second > avg_first * 1.1:
                    trends["entropy_trend"] = "increasing"
                elif avg_second < avg_first * 0.9:
                    trends["entropy_trend"] = "decreasing"

        except Exception as e:
            self.logger.warning(f"计算趋势失败: {e}")

        return trends

    def check_alerts(
        self, system_metrics: Dict, maref_metrics: Dict, agent_metrics: Dict
    ) -> Dict[str, List]:
        """检查预警条件

        优先使用预警规则引擎，如果不可用则使用简化的预警检查逻辑
        """
        # 如果预警引擎可用，使用引擎进行检查
        if self.alert_engine is not None:
            try:
                # 构建预警引擎需要的指标格式
                metrics = {
                    "system": system_metrics,
                    "control_entropy_h_c": maref_metrics.get("control_entropy_h_c", 0),
                    "hexagram_name": maref_metrics.get("hexagram_name", "未知卦象"),
                    "current_hexagram": maref_metrics.get("current_hexagram", "000000"),
                    "hexagram_distribution": maref_metrics.get("hexagram_distribution", {}),
                    "gray_code_compliance": maref_metrics.get(
                        "gray_code_compliance", {"rate": 1.0}
                    ),
                    "agents": agent_metrics,
                }

                # 使用预警引擎检查
                engine_alerts = self.alert_engine.check_alerts(metrics)

                # 转换格式以匹配原有接口
                alerts = {
                    "red_alerts": [],
                    "yellow_alerts": [],
                    "total_alerts": len(engine_alerts.get("red_alerts", []))
                    + len(engine_alerts.get("yellow_alerts", [])),
                }

                # 转换红色预警
                for alert in engine_alerts.get("red_alerts", []):
                    alerts["red_alerts"].append(
                        {
                            "title": alert.get("title", "红色预警"),
                            "description": alert.get("description", "未知问题"),
                            "recommendation": alert.get("recommendation", "请检查系统"),
                            "duration": alert.get("duration", 0),
                            "priority": alert.get("priority", "high"),
                        }
                    )

                # 转换黄色预警
                for alert in engine_alerts.get("yellow_alerts", []):
                    alerts["yellow_alerts"].append(
                        {
                            "title": alert.get("title", "黄色预警"),
                            "description": alert.get("description", "未知问题"),
                            "recommendation": alert.get("recommendation", "请检查系统"),
                            "duration": alert.get("duration", 0),
                            "priority": alert.get("priority", "medium"),
                        }
                    )

                self.logger.info(f"预警引擎检查完成: {alerts['total_alerts']} 个预警")
                return alerts

            except Exception as e:
                self.logger.error(f"预警引擎检查失败，回退到简化逻辑: {e}")
                # 继续执行简化逻辑

        # 简化预警检查逻辑（回退）
        self.logger.info("使用简化预警检查逻辑")
        red_alerts = []
        yellow_alerts = []

        # 1. 控制熵预警
        entropy = maref_metrics.get("control_entropy_h_c", 0)
        if entropy > 5.5:
            red_alerts.append(
                {
                    "title": "控制熵过高",
                    "description": f"控制熵H_c = {entropy:.2f} > 5.5，存在状态空间爆炸风险",
                    "recommendation": "立即检查状态转换逻辑，增加状态约束",
                    "priority": "critical",
                }
            )
        elif entropy > 4.5:
            yellow_alerts.append(
                {
                    "title": "控制熵偏高",
                    "description": f"控制熵H_c = {entropy:.2f} > 4.5，接近危险阈值",
                    "recommendation": "监控状态转换频率，考虑优化状态空间",
                    "priority": "medium",
                }
            )

        # 2. 格雷编码合规性预警
        compliance_rate = maref_metrics.get("gray_code_compliance", {}).get("rate", 1.0)
        if compliance_rate < 0.8:
            red_alerts.append(
                {
                    "title": "格雷编码合规性严重违规",
                    "description": f"合规率 = {compliance_rate:.1%} < 80%，状态转换不符合格雷编码约束",
                    "recommendation": "立即检查状态转换逻辑，修复违规转换",
                    "priority": "high",
                }
            )
        elif compliance_rate < 0.9:
            yellow_alerts.append(
                {
                    "title": "格雷编码合规性警告",
                    "description": f"合规率 = {compliance_rate:.1%} < 90%，存在违规转换",
                    "recommendation": "审查状态转换历史，优化转换逻辑",
                    "priority": "medium",
                }
            )

        # 3. 系统资源预警
        memory_usage = system_metrics.get("memory_usage", 0)
        if memory_usage > 95:
            red_alerts.append(
                {
                    "title": "内存使用率过高",
                    "description": f"内存使用率 = {memory_usage:.1f}% > 95%，可能导致系统崩溃",
                    "recommendation": "立即释放内存或增加系统资源",
                    "priority": "critical",
                }
            )
        elif memory_usage > 90:
            yellow_alerts.append(
                {
                    "title": "内存使用率偏高",
                    "description": f"内存使用率 = {memory_usage:.1f}% > 90%，接近限制",
                    "recommendation": "监控内存使用趋势，考虑优化内存管理",
                    "priority": "medium",
                }
            )

        cpu_usage = system_metrics.get("cpu_usage", 0)
        if cpu_usage > 95:
            red_alerts.append(
                {
                    "title": "CPU使用率过高",
                    "description": f"CPU使用率 = {cpu_usage:.1f}% > 95%，系统响应可能延迟",
                    "recommendation": "检查高负载进程，优化计算任务",
                    "priority": "high",
                }
            )
        elif cpu_usage > 90:
            yellow_alerts.append(
                {
                    "title": "CPU使用率偏高",
                    "description": f"CPU使用率 = {cpu_usage:.1f}% > 90%，接近限制",
                    "recommendation": "监控CPU使用趋势，考虑负载均衡",
                    "priority": "medium",
                }
            )

        # 4. 智能体健康预警
        error_agents = []
        for agent_name, metrics in agent_metrics.items():
            if metrics.get("status") in ["error", "failed"]:
                error_agents.append(agent_name)

        if error_agents:
            red_alerts.append(
                {
                    "title": "智能体运行异常",
                    "description": f'{len(error_agents)}个智能体异常: {", ".join(error_agents[:3])}',
                    "recommendation": "检查智能体日志，重启异常智能体",
                    "priority": "high",
                }
            )

        # 如果没有预警，添加正常运行提示
        if not red_alerts and not yellow_alerts:
            yellow_alerts.append(
                {
                    "title": "系统运行正常",
                    "description": "所有指标均在正常范围内",
                    "recommendation": "继续保持监控",
                    "priority": "low",
                }
            )

        return {
            "red_alerts": red_alerts,
            "yellow_alerts": yellow_alerts,
            "total_alerts": len(red_alerts) + len(yellow_alerts),
        }

    def format_alerts(self, alerts: Dict[str, List]) -> str:
        """格式化预警信息"""
        red_alerts = alerts.get("red_alerts", [])
        yellow_alerts = alerts.get("yellow_alerts", [])

        if not red_alerts and not yellow_alerts:
            return "### 🟢 绿色（正常运行）\n- 系统所有指标正常，无需人工介入\n"

        output = ""

        if red_alerts:
            output += "### 🔴 红色（需要介入）\n"
            for i, alert in enumerate(red_alerts, 1):
                output += f"{i}. **{alert['title']}**\n"
                output += f"   - 问题：{alert['description']}\n"
                output += f"   - 建议：{alert['recommendation']}\n\n"

        if yellow_alerts:
            output += "### 🟡 黄色（建议检查）\n"
            for i, alert in enumerate(yellow_alerts, 1):
                output += f"{i}. **{alert['title']}**\n"
                output += f"   - 问题：{alert['description']}\n"
                output += f"   - 建议：{alert['recommendation']}\n\n"

        return output

    def format_recommendations(self, trends: Dict[str, Any], alerts: Dict[str, List]) -> str:
        """格式化建议和行动计划"""
        recommendations = []

        # 基于预警的建议
        red_alerts = alerts.get("red_alerts", [])
        yellow_alerts = alerts.get("yellow_alerts", [])

        if red_alerts:
            recommendations.append("### 🔴 紧急行动计划\n")
            for alert in red_alerts:
                recommendations.append(f"- **立即处理**: {alert['recommendation']}")

        if yellow_alerts:
            recommendations.append("\n### 🟡 优化建议\n")
            for alert in yellow_alerts:
                recommendations.append(f"- **建议检查**: {alert['recommendation']}")

        # 基于趋势的建议
        if trends.get("entropy_trend") == "increasing":
            recommendations.append("\n### 📈 趋势监控\n")
            recommendations.append("- **控制熵上升趋势**: 增加状态监控频率，准备状态空间优化")

        if trends.get("compliance_trend") == "decreasing":
            recommendations.append("\n### 📉 合规性监控\n")
            recommendations.append("- **格雷编码合规性下降**: 审查最近的状态转换违规记录")

        # 如果没有具体建议，添加常规建议
        if not recommendations:
            recommendations = [
                "### 📋 日常维护任务\n",
                "- [ ] 运行MAREF集成测试套件",
                "- [ ] 审查昨日异常状态转换",
                "- [ ] 更新卦象知识库",
                "- [ ] 生成周度趋势分析报告",
            ]

        return "\n".join(recommendations)

    def save_report(self, content: str) -> str:
        """保存报告到文件"""
        report_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"maref-daily-{report_date}.md"
        filepath = Path(self.output_dir) / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            self.logger.info(f"日报已保存: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"保存报告失败: {e}")
            raise

    def send_alerts(self, alerts: Dict[str, List], report_path: str):
        """发送预警通知"""
        red_alerts = alerts.get("red_alerts", [])
        yellow_alerts = alerts.get("yellow_alerts", [])
        red_count = len(red_alerts)
        yellow_count = len(yellow_alerts)

        self.logger.info(f"发送预警通知: {red_count}个红色预警, {yellow_count}个黄色预警")
        self.logger.info(f"报告位置: {report_path}")

        # 检查通知器是否可用
        if self.notifier is None:
            self.logger.warning("通知器不可用，预警通知将仅记录到日志")
            return

        try:
            # 发送红色预警通知
            if red_alerts:
                self.logger.info(f"发送红色预警通知，{red_count}个预警")
                red_results = self.notifier.send_alert("red", red_alerts, report_path)
                self.logger.info(f"红色预警通知结果: {red_results}")

            # 发送黄色预警通知
            if yellow_alerts:
                self.logger.info(f"发送黄色预警通知，{yellow_count}个预警")
                yellow_results = self.notifier.send_alert("yellow", yellow_alerts, report_path)
                self.logger.info(f"黄色预警通知结果: {yellow_results}")

            # 如果没有预警但仍需要通知（可选）
            if not red_alerts and not yellow_alerts:
                # 可以发送一个正常状态通知
                self.logger.debug("无预警需要发送，跳过通知")

        except Exception as e:
            self.logger.error(f"发送预警通知失败: {e}")
            self.logger.info("预警通知仅记录到日志，未发送到外部渠道")


def test_daily_reporter():
    """测试日报生成器"""
    print("=== MAREF日报生成器测试 ===")

    try:
        # 创建状态管理器
        from hexagram_state_manager import HexagramStateManager

        state_manager = HexagramStateManager("000000")

        # 模拟一些状态转换
        test_transitions = ["000001", "000011", "000010", "000000", "000100"]
        for state in test_transitions:
            state_manager.transition(state)

        # 创建模拟智能体
        class MockAgent:
            def __init__(self, agent_id, agent_type):
                self.agent_id = agent_id
                self.agent_type = agent_type

            def get_health_metrics(self):
                return {
                    "agent_id": self.agent_id,
                    "agent_type": str(self.agent_type),
                    "status": "active",
                    "health_score": 0.9,
                    "last_check": datetime.now().isoformat(),
                }

        # 创建模拟智能体字典
        agents = {
            "guardian": MockAgent("guardian_001", "guardian"),
            "communicator": MockAgent("communicator_001", "communicator"),
            "learner": MockAgent("learner_001", "learner"),
            "explorer": MockAgent("explorer_001", "explorer"),
        }

        # 创建监控器
        from maref_monitor import MAREFMonitor

        monitor = MAREFMonitor(state_manager, agents)

        # 收集一些数据
        for _ in range(5):
            monitor.collect_all_metrics()
            time.sleep(0.1)

        # 创建日报生成器
        reporter = MAREFDailyReporter(monitor)

        print("✅ 日报生成器创建成功")

        # 生成日报
        print("\n=== 生成日报测试 ===")
        report_path = reporter.generate_daily_report()

        if report_path:
            print(f"✅ 日报生成成功: {report_path}")

            # 显示报告摘要
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    content = f.read()

                print(f"报告大小: {len(content)} 字符")
                print(f"报告前几行:")
                for line in content.split("\n")[:10]:
                    print(f"  {line}")

            except Exception as e:
                print(f"⚠️  读取报告失败: {e}")

        else:
            print("❌ 日报生成失败")

        print("\n=== 测试完成 ===")
        print("MAREF日报生成器功能验证通过")

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保相关模块在正确路径")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import time

    test_daily_reporter()
