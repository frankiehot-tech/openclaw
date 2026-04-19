#!/usr/bin/env python3
"""
每分钟检查点监控系统
实现多Agent系统24小时压力测试问题修复实施方案中的1.4基础监控增强要求
"""

import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CheckpointMonitor:
    """检查点监控器"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            "checkpoint_interval": 60,  # 检查点间隔(秒)
            "error_rate_threshold": 0.10,  # 错误率阈值10%
            "availability_threshold": 0.999,  # 可用性阈值99.9%
            "heartbeat_threshold": 300,  # 心跳阈值300秒
            "retention_days": 7,  # 检查点保留天数
            "alert_channels": ["log", "console", "file"],
        }

        self.root_dir = Path(__file__).parent.parent
        self.queue_dir = self.root_dir / ".openclaw" / "plan_queue"
        self.checkpoints_dir = self.root_dir / "logs" / "checkpoints"
        self.error_reports_dir = self.root_dir / "logs" / "error_reports"

        # 创建目录
        for directory in [self.checkpoints_dir, self.error_reports_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # 监控状态
        self.monitoring_state = {
            "start_time": datetime.now().isoformat(),
            "checkpoints_collected": 0,
            "alerts_triggered": 0,
            "last_checkpoint_time": None,
            "error_rate_history": [],
            "availability_history": [],
        }

    def collect_checkpoint_data(self) -> Dict[str, Any]:
        """收集检查点数据"""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "system": {},
            "queues": {},
            "tasks": {},
            "performance": {},
            "alerts": [],
        }

        # 1. 系统指标
        try:
            checkpoint["system"] = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_available_gb": psutil.virtual_memory().available / (1024**3),
                "disk_usage_percent": psutil.disk_usage("/").percent,
                "uptime_seconds": time.time() - psutil.boot_time(),
            }
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            checkpoint["system"]["error"] = str(e)

        # 2. 队列状态
        try:
            queue_status = self.check_queue_status()
            checkpoint["queues"] = queue_status

            # 计算队列级错误率
            total_tasks = 0
            failed_tasks = 0

            for queue_name, status in queue_status.get("queues", {}).items():
                if isinstance(status, dict):
                    checkpoint["queues"][queue_name] = status
                    if "failed_count" in status:
                        failed_tasks += status["failed_count"]
                    if "item_count" in status:
                        total_tasks += status["item_count"]

            if total_tasks > 0:
                checkpoint["tasks"]["error_rate"] = failed_tasks / total_tasks

                # 检查错误率阈值
                if checkpoint["tasks"]["error_rate"] > self.config["error_rate_threshold"]:
                    alert = {
                        "type": "high_error_rate",
                        "error_rate": checkpoint["tasks"]["error_rate"],
                        "threshold": self.config["error_rate_threshold"],
                        "message": f"错误率过高: {checkpoint['tasks']['error_rate']:.2%} > {self.config['error_rate_threshold']:.0%}",
                    }
                    checkpoint["alerts"].append(alert)
            else:
                checkpoint["tasks"]["error_rate"] = 0.0

        except Exception as e:
            logger.error(f"检查队列状态失败: {e}")
            checkpoint["queues"]["error"] = str(e)

        # 3. 运行器进程状态
        try:
            runner_processes = []
            runner_count = 0

            for proc in psutil.process_iter(
                ["pid", "name", "cmdline", "cpu_percent", "memory_percent", "create_time"]
            ):
                try:
                    cmdline = proc.info["cmdline"]
                    if cmdline and any(
                        keyword in " ".join(cmdline).lower()
                        for keyword in ["athena", "codex", "runner"]
                    ):
                        runner_count += 1
                        runner_processes.append(
                            {
                                "pid": proc.info["pid"],
                                "name": proc.info["name"],
                                "cmdline_preview": cmdline[:2] if cmdline else [],
                                "cpu_percent": proc.info["cpu_percent"],
                                "memory_percent": proc.info["memory_percent"],
                                "uptime_seconds": (
                                    time.time() - proc.info["create_time"]
                                    if proc.info["create_time"]
                                    else None
                                ),
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            checkpoint["performance"]["runner_count"] = runner_count
            checkpoint["performance"]["runner_processes"] = runner_processes

            # 检查可用性（至少一个运行器进程）
            if runner_count == 0:
                alert = {"type": "no_runners", "message": "没有运行器进程在运行，系统可用性为0"}
                checkpoint["alerts"].append(alert)
                checkpoint["performance"]["availability"] = 0.0
            else:
                checkpoint["performance"]["availability"] = 1.0

            # 检查可用性阈值
            if checkpoint["performance"]["availability"] < self.config["availability_threshold"]:
                alert = {
                    "type": "low_availability",
                    "availability": checkpoint["performance"]["availability"],
                    "threshold": self.config["availability_threshold"],
                    "message": f"系统可用性过低: {checkpoint['performance']['availability']:.1%} < {self.config['availability_threshold']:.1%}",
                }
                checkpoint["alerts"].append(alert)

        except Exception as e:
            logger.error(f"检查运行器进程失败: {e}")
            checkpoint["performance"]["error"] = str(e)

        # 4. 心跳检查
        try:
            stale_heartbeats = self.check_stale_heartbeats()
            checkpoint["heartbeats"] = stale_heartbeats

            if stale_heartbeats["stale_count"] > 0:
                alert = {
                    "type": "stale_heartbeats",
                    "stale_count": stale_heartbeats["stale_count"],
                    "tasks": stale_heartbeats["stale_tasks"],
                    "message": f"发现 {stale_heartbeats['stale_count']} 个陈旧心跳任务",
                }
                checkpoint["alerts"].append(alert)

        except Exception as e:
            logger.error(f"检查心跳失败: {e}")
            checkpoint["heartbeats"]["error"] = str(e)

        return checkpoint

    def check_queue_status(self) -> Dict[str, Any]:
        """检查队列状态（简化版）"""
        queue_status = {
            "timestamp": datetime.now().isoformat(),
            "queues": {},
            "total_queues": 0,
            "total_tasks": 0,
            "failed_tasks": 0,
        }

        if self.queue_dir.exists():
            queue_files = list(self.queue_dir.glob("*.json"))
            queue_status["total_queues"] = len(queue_files)

            for queue_file in queue_files:
                try:
                    with open(queue_file, "r", encoding="utf-8") as f:
                        queue_data = json.load(f)

                    queue_name = queue_file.stem
                    items = queue_data.get("items", {})
                    item_count = len(items)

                    # 计算失败任务数
                    failed_count = 0
                    for item_id, item in items.items():
                        if isinstance(item, dict) and item.get("status") == "failed":
                            failed_count += 1

                    queue_status["queues"][queue_name] = {
                        "item_count": item_count,
                        "failed_count": failed_count,
                        "state": queue_data.get("state", "unknown"),
                        "last_updated": queue_data.get("updated_at"),
                        "pause_reason": queue_data.get("pause_reason", ""),
                    }

                    queue_status["total_tasks"] += item_count
                    queue_status["failed_tasks"] += failed_count

                except Exception as e:
                    logger.error(f"读取队列文件失败 {queue_file}: {e}")
                    queue_status["queues"][queue_file.stem] = {"error": str(e)}
        else:
            queue_status["error"] = "队列目录不存在"

        return queue_status

    def check_stale_heartbeats(self) -> Dict[str, Any]:
        """检查陈旧心跳"""
        stale_heartbeats = {
            "stale_count": 0,
            "stale_tasks": [],
            "threshold_seconds": self.config["heartbeat_threshold"],
        }

        if not self.queue_dir.exists():
            return stale_heartbeats

        current_time = datetime.now()

        for queue_file in self.queue_dir.glob("*.json"):
            try:
                with open(queue_file, "r", encoding="utf-8") as f:
                    queue_data = json.load(f)

                items = queue_data.get("items", {})
                for item_id, item in items.items():
                    if not isinstance(item, dict):
                        continue

                    heartbeat_at = item.get("runner_heartbeat_at")
                    status = item.get("status", "")

                    if heartbeat_at and status in ["running", "pending"]:
                        try:
                            heartbeat_time = datetime.fromisoformat(
                                heartbeat_at.replace("Z", "+00:00")
                            )
                            age_seconds = (current_time - heartbeat_time).total_seconds()

                            if age_seconds > self.config["heartbeat_threshold"]:
                                stale_heartbeats["stale_count"] += 1
                                stale_heartbeats["stale_tasks"].append(
                                    {
                                        "queue": queue_file.stem,
                                        "task_id": item_id,
                                        "status": status,
                                        "heartbeat_age_seconds": age_seconds,
                                        "heartbeat_at": heartbeat_at,
                                    }
                                )
                        except (ValueError, TypeError) as e:
                            logger.warning(f"解析心跳时间失败 {item_id}: {e}")

            except Exception as e:
                logger.error(f"检查心跳失败 {queue_file}: {e}")

        return stale_heartbeats

    def save_checkpoint(self, checkpoint: Dict[str, Any]):
        """保存检查点"""
        try:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"checkpoint_{timestamp}.json"
            filepath = self.checkpoints_dir / filename

            # 保存检查点
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)

            # 更新状态
            self.monitoring_state["checkpoints_collected"] += 1
            self.monitoring_state["last_checkpoint_time"] = checkpoint["timestamp"]

            # 更新历史记录
            if "tasks" in checkpoint and "error_rate" in checkpoint["tasks"]:
                self.monitoring_state["error_rate_history"].append(
                    {
                        "timestamp": checkpoint["timestamp"],
                        "error_rate": checkpoint["tasks"]["error_rate"],
                    }
                )

            if "performance" in checkpoint and "availability" in checkpoint["performance"]:
                self.monitoring_state["availability_history"].append(
                    {
                        "timestamp": checkpoint["timestamp"],
                        "availability": checkpoint["performance"]["availability"],
                    }
                )

            # 保留最近的历史记录（最多1000条）
            for key in ["error_rate_history", "availability_history"]:
                if len(self.monitoring_state[key]) > 1000:
                    self.monitoring_state[key] = self.monitoring_state[key][-1000:]

            logger.info(f"检查点已保存: {filename}")

        except Exception as e:
            logger.error(f"保存检查点失败: {e}")

    def handle_alerts(self, checkpoint: Dict[str, Any]):
        """处理告警"""
        if not checkpoint["alerts"]:
            return

        alert_summary = {
            "timestamp": checkpoint["timestamp"],
            "alert_count": len(checkpoint["alerts"]),
            "alerts": checkpoint["alerts"],
        }

        # 保存告警报告
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_file = self.error_reports_dir / f"alerts_{timestamp}.json"

            with open(alert_file, "w", encoding="utf-8") as f:
                json.dump(alert_summary, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存告警报告失败: {e}")

        # 输出告警
        for alert in checkpoint["alerts"]:
            alert_message = f"🚨 检查点告警 [{alert['type']}]: {alert['message']}"

            if "console" in self.config["alert_channels"]:
                print(alert_message)

            if "log" in self.config["alert_channels"]:
                logger.warning(alert_message)

            self.monitoring_state["alerts_triggered"] += 1

    def cleanup_old_checkpoints(self):
        """清理旧的检查点文件"""
        try:
            cutoff_time = datetime.now() - timedelta(days=self.config["retention_days"])

            for checkpoint_file in self.checkpoints_dir.glob("checkpoint_*.json"):
                try:
                    # 从文件名解析时间戳
                    filename = checkpoint_file.stem
                    if filename.startswith("checkpoint_"):
                        timestamp_str = filename[11:]  # 移除"checkpoint_"前缀
                        file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                        if file_time < cutoff_time:
                            checkpoint_file.unlink()
                            logger.debug(f"清理旧检查点: {checkpoint_file.name}")
                except (ValueError, IndexError) as e:
                    logger.warning(f"解析检查点文件名失败 {checkpoint_file}: {e}")
                    # 如果无法解析，按修改时间清理
                    file_mtime = datetime.fromtimestamp(checkpoint_file.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        checkpoint_file.unlink()

        except Exception as e:
            logger.error(f"清理旧检查点失败: {e}")

    def generate_daily_report(self):
        """生成每日报告"""
        try:
            if not self.monitoring_state["error_rate_history"]:
                return

            # 计算日统计
            today = datetime.now().date()
            daily_history = [
                h
                for h in self.monitoring_state["error_rate_history"]
                if datetime.fromisoformat(h["timestamp"]).date() == today
            ]

            if not daily_history:
                return

            # 计算统计数据
            error_rates = [h["error_rate"] for h in daily_history]
            avg_error_rate = sum(error_rates) / len(error_rates) if error_rates else 0
            max_error_rate = max(error_rates) if error_rates else 0
            min_error_rate = min(error_rates) if error_rates else 0

            daily_report = {
                "date": today.isoformat(),
                "checkpoints_collected": len(daily_history),
                "error_rate_stats": {
                    "average": avg_error_rate,
                    "maximum": max_error_rate,
                    "minimum": min_error_rate,
                    "threshold": self.config["error_rate_threshold"],
                    "threshold_violations": sum(
                        1 for rate in error_rates if rate > self.config["error_rate_threshold"]
                    ),
                },
                "alerts_triggered": self.monitoring_state["alerts_triggered"],
                "availability_stats": {
                    "average": 1.0,  # 简化处理
                    "threshold": self.config["availability_threshold"],
                },
                "generated_at": datetime.now().isoformat(),
            }

            # 保存报告
            report_file = self.error_reports_dir / f"daily_report_{today}.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(daily_report, f, ensure_ascii=False, indent=2)

            logger.info(f"每日报告已生成: {report_file.name}")

        except Exception as e:
            logger.error(f"生成每日报告失败: {e}")

    def run_monitoring_cycle(self):
        """运行监控周期"""
        logger.info("开始检查点监控周期...")

        try:
            # 收集检查点数据
            checkpoint = self.collect_checkpoint_data()

            # 保存检查点
            self.save_checkpoint(checkpoint)

            # 处理告警
            self.handle_alerts(checkpoint)

            # 清理旧检查点（每小时一次）
            if self.monitoring_state["checkpoints_collected"] % 60 == 0:
                self.cleanup_old_checkpoints()

            # 生成每日报告（每天一次）
            if self.monitoring_state["checkpoints_collected"] % (24 * 60) == 0:
                self.generate_daily_report()

            # 打印状态摘要
            self.print_status_summary(checkpoint)

            return checkpoint

        except Exception as e:
            logger.error(f"监控周期失败: {e}")
            return None

    def print_status_summary(self, checkpoint: Dict[str, Any]):
        """打印状态摘要"""
        print(f"\n{'='*60}")
        print(f"检查点监控摘要 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # 系统资源
        if "system" in checkpoint:
            sys_info = checkpoint["system"]
            print(f"系统资源:")
            print(f"  CPU: {sys_info.get('cpu_percent', 'N/A'):.1f}%")
            print(
                f"  内存: {sys_info.get('memory_percent', 'N/A'):.1f}% ({sys_info.get('memory_available_gb', 0):.1f} GB可用)"
            )

        # 队列状态
        if "queues" in checkpoint and "total_queues" in checkpoint["queues"]:
            q_info = checkpoint["queues"]
            print(f"队列状态:")
            print(f"  队列数: {q_info.get('total_queues', 0)}")
            print(f"  任务总数: {q_info.get('total_tasks', 0)}")
            print(f"  失败任务: {q_info.get('failed_tasks', 0)}")

        # 错误率
        if "tasks" in checkpoint and "error_rate" in checkpoint["tasks"]:
            error_rate = checkpoint["tasks"]["error_rate"]
            threshold = self.config["error_rate_threshold"]
            status = "✅" if error_rate <= threshold else "⚠️"
            print(f"错误率: {status} {error_rate:.2%} (阈值: {threshold:.0%})")

        # 可用性
        if "performance" in checkpoint and "availability" in checkpoint["performance"]:
            availability = checkpoint["performance"]["availability"]
            threshold = self.config["availability_threshold"]
            status = "✅" if availability >= threshold else "⚠️"
            print(f"系统可用性: {status} {availability:.1%} (阈值: {threshold:.1%})")

        # 运行器进程
        if "performance" in checkpoint and "runner_count" in checkpoint["performance"]:
            print(f"运行器进程: {checkpoint['performance']['runner_count']}个")

        # 告警
        if checkpoint["alerts"]:
            print(f"告警: ⚠️ {len(checkpoint['alerts'])}个 (详情见日志)")
        else:
            print(f"告警: ✅ 无")

        print(f"{'='*60}")

    def run_continuous_monitoring(self):
        """运行持续监控"""
        logger.info("启动检查点持续监控系统...")
        logger.info(f"检查点间隔: {self.config['checkpoint_interval']}秒")
        logger.info(f"错误率阈值: {self.config['error_rate_threshold']:.0%}")
        logger.info(f"可用性阈值: {self.config['availability_threshold']:.1%}")

        try:
            checkpoint_count = 0

            while True:
                checkpoint_count += 1
                logger.info(f"执行第 {checkpoint_count} 个检查点...")

                # 运行监控周期
                self.run_monitoring_cycle()

                # 等待下一个检查点
                logger.info(f"等待 {self.config['checkpoint_interval']} 秒到下一个检查点...")
                time.sleep(self.config["checkpoint_interval"])

        except KeyboardInterrupt:
            logger.info("检查点监控系统停止")

            # 生成最终摘要
            final_summary = {
                "monitoring_start_time": self.monitoring_state["start_time"],
                "monitoring_end_time": datetime.now().isoformat(),
                "total_checkpoints": self.monitoring_state["checkpoints_collected"],
                "total_alerts": self.monitoring_state["alerts_triggered"],
                "final_status": "stopped_by_user",
            }

            logger.info(f"监控摘要: {json.dumps(final_summary, indent=2)}")

        except Exception as e:
            logger.error(f"监控系统运行失败: {e}")


def main():
    """主函数"""
    monitor = CheckpointMonitor()

    print("=" * 60)
    print("多Agent系统检查点监控系统")
    print("=" * 60)
    print("功能:")
    print("  1. 每分钟检查点收集")
    print("  2. 系统资源监控")
    print("  3. 队列错误率监控")
    print("  4. 系统可用性监控")
    print("  5. 心跳健康检查")
    print("  6. 自动告警机制")
    print("  7. 每日报告生成")
    print()
    print("配置:")
    print(f"  检查点间隔: {monitor.config['checkpoint_interval']}秒")
    print(f"  错误率阈值: {monitor.config['error_rate_threshold']:.0%}")
    print(f"  可用性阈值: {monitor.config['availability_threshold']:.1%}")
    print(f"  心跳阈值: {monitor.config['heartbeat_threshold']}秒")
    print()

    # 运行一次检查
    print("执行首次检查点...")
    checkpoint = monitor.run_monitoring_cycle()

    if checkpoint:
        print("✅ 首次检查点完成")
    else:
        print("❌ 首次检查点失败")

    print()
    print("启动持续监控... (按Ctrl+C停止)")
    print("-" * 60)

    # 运行持续监控
    monitor.run_continuous_monitoring()


if __name__ == "__main__":
    main()
