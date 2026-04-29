#!/usr/bin/env python3
"""
错误率阈值告警器
基于《多Agent系统24小时压力测试问题修复实施方案》1.4节实现
监控系统错误率并设置告警阈值（>10%触发）
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ErrorRateAlerter:
    """错误率阈值告警器"""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {
            "error_rate_threshold": 0.10,  # 错误率阈值 10%
            "check_interval_minutes": 5,  # 检查间隔（分钟）
            "alert_channels": ["console", "log", "file"],
            "alert_cooldown_minutes": 30,  # 告警冷却时间（分钟）
            "queue_dir": "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue",
            "reports_dir": "/Volumes/1TB-M2/openclaw/scripts",
            "history_size": 100,  # 历史记录保留数量
        }

        self.root_dir = Path(__file__).parent.parent
        self.queue_dir = Path(self.config["queue_dir"])
        self.reports_dir = Path(self.config["reports_dir"])

        # 告警历史
        self.alert_history = []
        self.error_rate_history = []

        # 最后告警时间
        self.last_alert_time = None

        # 历史数据文件
        self.history_file = self.root_dir / "logs" / "error_rate_history.json"
        self.alerts_file = self.root_dir / "logs" / "error_rate_alerts.jsonl"

        # 创建日志目录
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载历史数据
        self.load_history()

    def load_history(self):
        """加载历史数据"""
        try:
            if self.history_file.exists():
                with open(self.history_file, encoding="utf-8") as f:
                    history_data = json.load(f)
                    self.error_rate_history = history_data.get("error_rate_history", [])
                    self.alert_history = history_data.get("alert_history", [])

                logger.info(f"加载历史数据: {len(self.error_rate_history)}个错误率记录")
        except Exception as e:
            logger.warning(f"加载历史数据失败: {e}")

    def save_history(self):
        """保存历史数据"""
        try:
            history_data = {
                "last_updated": datetime.now().isoformat(),
                "error_rate_history": self.error_rate_history[-self.config["history_size"] :],
                "alert_history": self.alert_history[-self.config["history_size"] :],
            }

            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"历史数据已保存: {len(self.error_rate_history)}个记录")
        except Exception as e:
            logger.error(f"保存历史数据失败: {e}")

    def count_tasks_in_queues(self) -> tuple[int, int, list[dict[str, Any]]]:
        """统计队列中的任务数量和错误数量"""
        total_tasks = 0
        error_tasks = 0
        queue_stats = []

        if not self.queue_dir.exists():
            logger.warning(f"队列目录不存在: {self.queue_dir}")
            return total_tasks, error_tasks, queue_stats

        # 查找所有队列文件
        queue_files = list(self.queue_dir.glob("*.json"))
        if not queue_files:
            logger.info("未找到队列文件")
            return total_tasks, error_tasks, queue_stats

        for queue_file in queue_files:
            try:
                with open(queue_file, encoding="utf-8") as f:
                    queue_data = json.load(f)

                queue_name = queue_file.stem
                items = queue_data.get("items", {})

                queue_task_count = len(items)
                queue_error_count = 0

                # 统计错误任务
                for _item_id, item in items.items():
                    status = item.get("status", "")
                    error = item.get("error", "")
                    summary = item.get("summary", "")

                    if status == "failed" or error or "error" in summary.lower():
                        queue_error_count += 1

                total_tasks += queue_task_count
                error_tasks += queue_error_count

                queue_error_rate = (
                    queue_error_count / queue_task_count if queue_task_count > 0 else 0.0
                )

                queue_stats.append(
                    {
                        "queue_name": queue_name,
                        "total_tasks": queue_task_count,
                        "error_tasks": queue_error_count,
                        "error_rate": queue_error_rate,
                        "queue_state": queue_data.get("state", "unknown"),
                        "pause_reason": queue_data.get("pause_reason", ""),
                    }
                )

            except Exception as e:
                logger.error(f"分析队列文件失败 {queue_file}: {e}")
                continue

        return total_tasks, error_tasks, queue_stats

    def calculate_error_rate(self) -> dict[str, Any]:
        """计算系统错误率"""
        current_time = datetime.now().isoformat()

        total_tasks, error_tasks, queue_stats = self.count_tasks_in_queues()

        # 计算错误率
        if total_tasks == 0:
            error_rate = 0.0
        else:
            error_rate = error_tasks / total_tasks

        # 构建错误率报告
        error_rate_report = {
            "timestamp": current_time,
            "total_tasks": total_tasks,
            "error_tasks": error_tasks,
            "error_rate": error_rate,
            "error_rate_percentage": error_rate * 100,
            "threshold": self.config["error_rate_threshold"],
            "threshold_percentage": self.config["error_rate_threshold"] * 100,
            "above_threshold": error_rate > self.config["error_rate_threshold"],
            "queue_statistics": queue_stats,
        }

        # 添加到历史记录
        self.error_rate_history.append(error_rate_report)

        # 检查是否需要告警
        if error_rate > self.config["error_rate_threshold"]:
            self.check_and_send_alert(error_rate_report)

        return error_rate_report

    def check_and_send_alert(self, error_rate_report: dict[str, Any]):
        """检查并发送告警"""
        current_time = datetime.now()

        # 检查告警冷却时间
        if self.last_alert_time:
            time_since_last_alert = (current_time - self.last_alert_time).total_seconds() / 60
            if time_since_last_alert < self.config["alert_cooldown_minutes"]:
                logger.debug(f"告警冷却中，距离上次告警 {time_since_last_alert:.1f} 分钟")
                return

        error_rate = error_rate_report["error_rate"]
        error_rate_percentage = error_rate_report["error_rate_percentage"]
        threshold_percentage = error_rate_report["threshold_percentage"]

        alert = {
            "type": "high_error_rate",
            "timestamp": current_time.isoformat(),
            "error_rate": error_rate,
            "error_rate_percentage": error_rate_percentage,
            "threshold": self.config["error_rate_threshold"],
            "threshold_percentage": threshold_percentage,
            "total_tasks": error_rate_report["total_tasks"],
            "error_tasks": error_rate_report["error_tasks"],
            "message": f"系统错误率过高: {error_rate_percentage:.2f}% > {threshold_percentage}%",
            "recommendation": self.generate_recommendation(error_rate_report),
        }

        # 添加到告警历史
        self.alert_history.append(alert)

        # 更新最后告警时间
        self.last_alert_time = current_time

        # 处理告警
        self.handle_alert(alert)

        # 记录告警到文件
        self.log_alert(alert)

    def generate_recommendation(self, error_rate_report: dict[str, Any]) -> str:
        """生成修复建议"""
        queue_stats = error_rate_report.get("queue_statistics", [])
        error_rate = error_rate_report["error_rate"]

        recommendations = []

        if error_rate > 0.3:
            recommendations.append("🚨 错误率超过30%，系统处于危险状态，需要立即修复")
        elif error_rate > 0.1:
            recommendations.append("⚠️ 错误率超过10%，系统稳定性受影响，需要优先处理")
        elif error_rate > 0.05:
            recommendations.append("🔔 错误率超过5%，系统需要优化和修复")

        # 分析队列级别的错误率
        high_error_queues = []
        for queue in queue_stats:
            if queue["error_rate"] > self.config["error_rate_threshold"]:
                high_error_queues.append(
                    {
                        "name": queue["queue_name"],
                        "error_rate": queue["error_rate"] * 100,
                        "error_tasks": queue["error_tasks"],
                        "total_tasks": queue["total_tasks"],
                    }
                )

        if high_error_queues:
            recommendations.append(f"高错误率队列: {len(high_error_queues)}个")
            for q in high_error_queues[:3]:  # 显示最多3个
                recommendations.append(
                    f"  - {q['name']}: {q['error_rate']:.1f}% ({q['error_tasks']}/{q['total_tasks']})"
                )

        # 通用建议
        recommendations.append("📊 建议运行错误分类分析器获取详细报告")
        recommendations.append("🔄 建议检查和修复错误任务")
        recommendations.append("⚡ 建议优化任务执行逻辑和资源分配")

        return "\n".join(recommendations)

    def handle_alert(self, alert: dict[str, Any]):
        """处理告警"""
        alert_message = f"🚨 错误率告警: {alert['message']}"

        # 控制台告警
        if "console" in self.config["alert_channels"]:
            print("\n" + "=" * 80)
            print(alert_message)
            print(f"错误任务: {alert['error_tasks']}/{alert['total_tasks']}")
            _first_line = alert["recommendation"].split("\n")[0]
            print(f"建议措施: {_first_line}")
            print("=" * 80 + "\n")

        # 日志告警
        if "log" in self.config["alert_channels"]:
            logger.warning(alert_message)

        # 文件告警
        if "file" in self.config["alert_channels"]:
            self.log_alert_to_file(alert)

    def log_alert(self, alert: dict[str, Any]):
        """记录告警到文件"""
        try:
            with open(self.alerts_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert, ensure_ascii=False) + "\n")

            logger.debug(f"告警已记录到文件: {self.alerts_file}")
        except Exception as e:
            logger.error(f"记录告警到文件失败: {e}")

    def log_alert_to_file(self, alert: dict[str, Any]):
        """记录详细告警到单独文件"""
        try:
            alert_dir = self.root_dir / "logs" / "alerts"
            alert_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_file = alert_dir / f"error_rate_alert_{timestamp}.json"

            with open(alert_file, "w", encoding="utf-8") as f:
                json.dump(alert, f, ensure_ascii=False, indent=2)

            logger.info(f"详细告警已保存: {alert_file}")
        except Exception as e:
            logger.error(f"保存详细告警失败: {e}")

    def generate_error_rate_report(self) -> str:
        """生成错误率报告"""
        if not self.error_rate_history:
            return "无错误率历史数据"

        latest_report = self.error_rate_history[-1]

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("系统错误率监控报告")
        report_lines.append("=" * 80)
        report_lines.append(f"生成时间: {latest_report['timestamp']}")
        report_lines.append(f"总任务数: {latest_report['total_tasks']}")
        report_lines.append(f"错误任务数: {latest_report['error_tasks']}")
        report_lines.append(f"错误率: {latest_report['error_rate_percentage']:.2f}%")
        report_lines.append(f"阈值: {latest_report['threshold_percentage']}%")
        report_lines.append(
            f"状态: {'超过阈值 ⚠️' if latest_report['above_threshold'] else '正常 ✅'}"
        )

        report_lines.append("\n📊 队列错误率分布:")
        report_lines.append("-" * 40)
        for queue in latest_report.get("queue_statistics", []):
            status_icon = "⚠️" if queue["error_rate"] > self.config["error_rate_threshold"] else "✅"
            report_lines.append(
                f"{status_icon} {queue['queue_name']}: {queue['error_tasks']}/{queue['total_tasks']} ({queue['error_rate'] * 100:.1f}%) - 状态: {queue['queue_state']}"
            )

        report_lines.append("\n📈 历史趋势:")
        report_lines.append("-" * 40)
        history_to_show = self.error_rate_history[-10:]  # 显示最近10个记录
        for _i, report in enumerate(history_to_show):
            timestamp = datetime.fromisoformat(report["timestamp"]).strftime("%H:%M:%S")
            error_rate = report["error_rate_percentage"]
            above_threshold = report["above_threshold"]
            indicator = "⚠️" if above_threshold else "✅"
            report_lines.append(
                f"  {indicator} {timestamp}: {error_rate:.2f}% ({report['error_tasks']}/{report['total_tasks']})"
            )

        # 如果有告警
        recent_alerts = self.alert_history[-5:]  # 最近5个告警
        if recent_alerts:
            report_lines.append("\n🚨 最近告警:")
            report_lines.append("-" * 40)
            for alert in recent_alerts:
                time_str = datetime.fromisoformat(alert["timestamp"]).strftime("%H:%M:%S")
                report_lines.append(f"  {time_str}: {alert['message']}")

        report_lines.append("\n💡 建议措施:")
        report_lines.append("-" * 40)
        if latest_report["above_threshold"]:
            recommendation = self.generate_recommendation(latest_report)
            for line in recommendation.split("\n"):
                report_lines.append(f"  {line}")
        else:
            report_lines.append("  ✅ 系统错误率正常，保持监控")

        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def print_dashboard(self):
        """打印错误率监控仪表板"""
        if not self.error_rate_history:
            print("无错误率数据")
            return

        latest_report = self.error_rate_history[-1]
        current_time = datetime.now()

        print("\n" + "=" * 80)
        print("系统错误率监控仪表板")
        print("=" * 80)
        print(f"更新时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总任务数: {latest_report['total_tasks']}")
        print(f"错误任务数: {latest_report['error_tasks']}")
        print(f"当前错误率: {latest_report['error_rate_percentage']:.2f}%")
        print(f"阈值: {latest_report['threshold_percentage']}%")

        status_icon = "⚠️" if latest_report["above_threshold"] else "✅"
        print(
            f"系统状态: {status_icon} {'超过阈值' if latest_report['above_threshold'] else '正常'}"
        )

        print("-" * 80)
        print("队列状态:")
        for queue in latest_report.get("queue_statistics", []):
            queue_error_rate = queue["error_rate"] * 100
            queue_status_icon = (
                "⚠️" if queue_error_rate > self.config["error_rate_threshold"] else "✅"
            )
            print(
                f"  {queue_status_icon} {queue['queue_name']}: {queue_error_rate:.1f}% ({queue['error_tasks']}/{queue['total_tasks']})"
            )

        print("-" * 80)
        print("最近检查:")
        history_to_show = self.error_rate_history[-3:]
        for report in history_to_show:
            timestamp = datetime.fromisoformat(report["timestamp"]).strftime("%H:%M:%S")
            error_rate = report["error_rate_percentage"]
            indicator = "⚠️" if report["above_threshold"] else "✅"
            print(f"  {indicator} {timestamp}: {error_rate:.2f}%")

        print("=" * 80)

    def run_check_cycle(self) -> dict[str, Any]:
        """运行一次检查周期"""
        logger.info("执行错误率检查...")

        try:
            error_rate_report = self.calculate_error_rate()

            # 每5次检查打印一次仪表板
            if len(self.error_rate_history) % 5 == 0:
                self.print_dashboard()

            # 定期保存历史数据
            if len(self.error_rate_history) % 10 == 0:
                self.save_history()

            return error_rate_report

        except Exception as e:
            logger.error(f"错误率检查失败: {e}")
            return None

    def run_continuous_monitoring(self):
        """运行持续监控"""
        logger.info("启动错误率阈值监控...")
        logger.info(f"检查间隔: {self.config['check_interval_minutes']}分钟")
        logger.info(f"错误率阈值: {self.config['error_rate_threshold'] * 100}%")

        try:
            while True:
                report = self.run_check_cycle()

                if report:
                    logger.info(
                        f"错误率: {report['error_rate_percentage']:.2f}% ({report['error_tasks']}/{report['total_tasks']})"
                    )

                # 等待下次检查
                time.sleep(self.config["check_interval_minutes"] * 60)

        except KeyboardInterrupt:
            logger.info("错误率监控停止")

            # 保存最终历史数据
            self.save_history()

            # 生成最终报告
            report_text = self.generate_error_rate_report()
            logger.info(f"最终监控报告:\n{report_text}")

        except Exception as e:
            logger.error(f"监控系统运行失败: {e}")


def main():
    """主函数"""
    print("=" * 80)
    print("错误率阈值告警系统")
    print("=" * 80)
    print("功能:")
    print("  1. 实时监控系统错误率")
    print("  2. 错误率阈值告警（>10%触发）")
    print("  3. 队列级别错误率分析")
    print("  4. 历史趋势分析和可视化")
    print("  5. 自动修复建议生成")
    print()
    print("配置:")
    print("  错误率阈值: 10%")
    print("  检查间隔: 5分钟")
    print("  告警冷却时间: 30分钟")
    print("  告警渠道: 控制台、日志、文件")
    print()

    alerter = ErrorRateAlerter()

    # 运行一次检查
    print("执行首次错误率检查...")
    error_rate_report = alerter.run_check_cycle()

    if error_rate_report:
        error_rate_percentage = error_rate_report["error_rate_percentage"]
        total_tasks = error_rate_report["total_tasks"]
        error_tasks = error_rate_report["error_tasks"]

        print("首次检查结果:")
        print(f"  总任务数: {total_tasks}")
        print(f"  错误任务数: {error_tasks}")
        print(f"  错误率: {error_rate_percentage:.2f}%")

        if error_rate_report["above_threshold"]:
            print("⚠️ 错误率超过阈值，建议采取措施")
        else:
            print("✅ 错误率正常")

    print()
    print("启动持续监控... (按Ctrl+C停止)")
    print("-" * 80)

    # 运行持续监控
    alerter.run_continuous_monitoring()


if __name__ == "__main__":
    main()
