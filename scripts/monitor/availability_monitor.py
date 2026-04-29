#!/usr/bin/env python3
"""
系统可用性实时监控
实现多Agent系统24小时压力测试问题修复实施方案中的1.4基础监控增强要求
提供实时系统可用性监控和历史数据分析
"""

import json
import logging
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AvailabilityMonitor:
    """系统可用性监控器"""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {
            "monitoring_interval": 30,  # 监控间隔(秒)
            "availability_threshold": 0.999,  # 可用性阈值99.9%
            "component_weights": {
                "runner_availability": 0.4,  # 运行器进程可用性权重
                "queue_availability": 0.3,  # 队列可用性权重
                "web_api_availability": 0.2,  # Web API可用性权重
                "heartbeat_availability": 0.1,  # 心跳可用性权重
            },
            "history_size": 1000,  # 历史数据保留数量
            "dashboard_refresh_interval": 5,  # 仪表板刷新间隔(秒)
            "alert_channels": ["log", "console", "file"],
        }

        self.root_dir = Path(__file__).parent.parent
        self.queue_dir = self.root_dir / ".openclaw" / "plan_queue"
        self.availability_log = self.root_dir / "logs" / "availability_metrics.jsonl"
        self.availability_history_file = self.root_dir / "logs" / "availability_history.json"

        # 创建日志目录
        self.availability_log.parent.mkdir(parents=True, exist_ok=True)

        # 历史数据存储
        self.availability_history = deque(maxlen=self.config["history_size"])
        self.component_history = {
            "runner_availability": deque(maxlen=self.config["history_size"]),
            "queue_availability": deque(maxlen=self.config["history_size"]),
            "web_api_availability": deque(maxlen=self.config["history_size"]),
            "heartbeat_availability": deque(maxlen=self.config["history_size"]),
        }

        # 监控状态
        self.monitoring_state = {
            "start_time": datetime.now().isoformat(),
            "last_check_time": None,
            "total_checks": 0,
            "availability_below_threshold_count": 0,
            "current_availability": 1.0,
            "current_status": "healthy",
        }

        # 仪表板数据
        self.dashboard_data = {
            "last_update": None,
            "current_availability": 1.0,
            "component_status": {},
            "recent_history": [],
            "alerts": [],
        }

        # 加载历史数据
        self.load_history_data()

    def load_history_data(self):
        """加载历史数据"""
        try:
            if self.availability_history_file.exists():
                with open(self.availability_history_file, encoding="utf-8") as f:
                    history_data = json.load(f)

                # 加载总可用性历史
                if "availability_history" in history_data:
                    for item in history_data["availability_history"][
                        -self.config["history_size"] :
                    ]:
                        self.availability_history.append(item)

                # 加载组件历史
                for component in self.component_history:
                    if component in history_data:
                        for item in history_data[component][-self.config["history_size"] :]:
                            self.component_history[component].append(item)

                logger.info(f"加载历史数据: {len(self.availability_history)}个可用性记录")
        except Exception as e:
            logger.warning(f"加载历史数据失败: {e}")

    def save_history_data(self):
        """保存历史数据"""
        try:
            history_data = {
                "last_saved": datetime.now().isoformat(),
                "availability_history": list(self.availability_history),
                **{
                    component: list(history)
                    for component, history in self.component_history.items()
                },
            }

            with open(self.availability_history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"历史数据已保存: {len(self.availability_history)}个记录")
        except Exception as e:
            logger.error(f"保存历史数据失败: {e}")

    def check_runner_availability(self) -> tuple[float, dict[str, Any]]:
        """检查运行器进程可用性"""
        try:
            runner_count = 0
            runner_details = []

            for proc in psutil.process_iter(
                ["pid", "name", "cmdline", "cpu_percent", "memory_percent"]
            ):
                try:
                    cmdline = proc.info["cmdline"]
                    if cmdline:
                        cmdline_str = " ".join(cmdline).lower()
                        if any(keyword in cmdline_str for keyword in ["athena", "codex", "runner"]):
                            runner_count += 1
                            runner_details.append(
                                {
                                    "pid": proc.info["pid"],
                                    "name": proc.info["name"],
                                    "cpu_percent": proc.info["cpu_percent"],
                                    "memory_percent": proc.info["memory_percent"],
                                }
                            )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 可用性计算：至少有一个运行器进程为100%，否则为0%
            availability = 1.0 if runner_count > 0 else 0.0

            component_status = {
                "availability": availability,
                "runner_count": runner_count,
                "runners": runner_details,
                "status": "healthy" if runner_count > 0 else "unhealthy",
                "message": (
                    f"找到 {runner_count} 个运行器进程" if runner_count > 0 else "未找到运行器进程"
                ),
            }

            return availability, component_status

        except Exception as e:
            logger.error(f"检查运行器进程失败: {e}")
            return 0.0, {"availability": 0.0, "error": str(e), "status": "error"}

    def check_queue_availability(self) -> tuple[float, dict[str, Any]]:
        """检查队列可用性"""
        try:
            if not self.queue_dir.exists():
                return 0.0, {"availability": 0.0, "error": "队列目录不存在", "status": "error"}

            # 只读取主队列文件，忽略备份、报告等文件
            all_queue_files = list(self.queue_dir.glob("*.json"))
            # 过滤条件：不包含 backup、dedup、report、monitor_backup 等关键词
            exclude_keywords = [
                "backup",
                "dedup",
                "report",
                "monitor_backup",
                "batch_reset",
                "manual_hold_fix",
                "dependency_fix",
                "queue_status_fix",
                "athena_enterprise_fix",
            ]
            queue_files = []
            for f in all_queue_files:
                fname = f.name
                # 排除包含排除关键词的文件
                if any(keyword in fname.lower() for keyword in exclude_keywords):
                    continue
                # 排除以 .backup 结尾的文件
                if fname.endswith(".backup"):
                    continue
                # 排除重复和报告文件
                if "deduplication_report" in fname or "_deduplicated" in fname:
                    continue
                queue_files.append(f)
            if not queue_files:
                return 1.0, {
                    "availability": 1.0,
                    "queue_count": 0,
                    "status": "healthy",
                    "message": "队列目录为空（无队列文件）",
                }

            healthy_queues = 0
            total_queues = len(queue_files)
            queue_details = []

            for queue_file in queue_files:
                try:
                    with open(queue_file, encoding="utf-8") as f:
                        queue_data = json.load(f)

                    queue_name = queue_file.stem
                    # 从queue_status字段获取状态，如果不存在则尝试state字段
                    queue_state = queue_data.get("queue_status", queue_data.get("state", "unknown"))
                    pause_reason = queue_data.get("pause_reason", "")

                    # 判断队列状态是否健康
                    # running, idle, paused_by_user, empty 视为健康
                    # dependency_blocked, error 视为不健康
                    is_healthy = queue_state in ["running", "idle", "paused_by_user", "empty"]

                    if is_healthy:
                        healthy_queues += 1

                    queue_details.append(
                        {
                            "name": queue_name,
                            "state": queue_state,
                            "pause_reason": pause_reason,
                            "healthy": is_healthy,
                            "item_count": len(queue_data.get("items", {})),
                            "last_updated": queue_data.get("updated_at"),
                        }
                    )

                except Exception as e:
                    logger.error(f"读取队列文件失败 {queue_file}: {e}")
                    queue_details.append(
                        {
                            "name": queue_file.stem,
                            "error": str(e),
                            "healthy": False,
                        }
                    )

            # 可用性计算：健康队列比例
            availability = healthy_queues / total_queues if total_queues > 0 else 1.0

            component_status = {
                "availability": availability,
                "total_queues": total_queues,
                "healthy_queues": healthy_queues,
                "queue_details": queue_details,
                "status": (
                    "healthy"
                    if availability >= 0.9
                    else "degraded"
                    if availability >= 0.5
                    else "unhealthy"
                ),
                "message": f"{healthy_queues}/{total_queues} 个队列健康",
            }

            return availability, component_status

        except Exception as e:
            logger.error(f"检查队列可用性失败: {e}")
            return 0.0, {"availability": 0.0, "error": str(e), "status": "error"}

    def check_web_api_availability(self) -> tuple[float, dict[str, Any]]:
        """检查Web API可用性"""
        try:
            # 尝试连接Athena Web API
            start_time = time.time()
            response = requests.get("http://127.0.0.1:8080/api/athena/queues", timeout=10)
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒

            # 判断响应状态
            is_available = response.status_code == 200
            availability = 1.0 if is_available else 0.0

            component_status = {
                "availability": availability,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "status": "healthy" if is_available else "unhealthy",
                "message": (
                    f"Web API响应正常 ({response.status_code}, {response_time:.1f}ms)"
                    if is_available
                    else f"Web API返回错误状态码: {response.status_code}"
                ),
            }

            return availability, component_status

        except requests.Timeout:
            component_status = {
                "availability": 0.0,
                "error": "请求超时",
                "response_time_ms": 10000,  # 10秒超时
                "status": "unhealthy",
                "message": "Web API请求超时",
            }
            return 0.0, component_status

        except requests.RequestException as e:
            component_status = {
                "availability": 0.0,
                "error": str(e),
                "status": "unhealthy",
                "message": f"Web API不可用: {e}",
            }
            return 0.0, component_status

        except Exception as e:
            logger.error(f"检查Web API可用性失败: {e}")
            return 0.0, {"availability": 0.0, "error": str(e), "status": "error"}

    def check_heartbeat_availability(self) -> tuple[float, dict[str, Any]]:
        """检查心跳可用性"""
        try:
            if not self.queue_dir.exists():
                return 1.0, {
                    "availability": 1.0,
                    "stale_count": 0,
                    "status": "healthy",
                    "message": "队列目录不存在，跳过心跳检查",
                }

            current_time = datetime.now()
            stale_threshold = 300  # 5分钟
            stale_tasks = []
            total_tasks = 0

            for queue_file in self.queue_dir.glob("*.json"):
                try:
                    with open(queue_file, encoding="utf-8") as f:
                        queue_data = json.load(f)

                    items = queue_data.get("items", {})
                    for item_id, item in items.items():
                        if not isinstance(item, dict):
                            continue

                        total_tasks += 1
                        heartbeat_at = item.get("runner_heartbeat_at")
                        status = item.get("status", "")

                        if heartbeat_at and status in ["running", "pending"]:
                            try:
                                heartbeat_time = datetime.fromisoformat(
                                    heartbeat_at.replace("Z", "+00:00")
                                )
                                age_seconds = (current_time - heartbeat_time).total_seconds()

                                if age_seconds > stale_threshold:
                                    stale_tasks.append(
                                        {
                                            "queue": queue_file.stem,
                                            "task_id": item_id,
                                            "status": status,
                                            "heartbeat_age_seconds": age_seconds,
                                        }
                                    )
                            except (ValueError, TypeError) as e:
                                logger.warning(f"解析心跳时间失败 {item_id}: {e}")

                except Exception as e:
                    logger.error(f"检查心跳失败 {queue_file}: {e}")

            # 可用性计算：无陈旧心跳为100%，有陈旧心跳根据比例计算
            stale_count = len(stale_tasks)
            if total_tasks == 0:
                availability = 1.0
            else:
                availability = 1.0 - (stale_count / total_tasks)

            component_status = {
                "availability": availability,
                "total_tasks": total_tasks,
                "stale_count": stale_count,
                "stale_tasks": stale_tasks,
                "status": (
                    "healthy"
                    if stale_count == 0
                    else "degraded"
                    if stale_count <= 3
                    else "unhealthy"
                ),
                "message": (
                    f"发现 {stale_count}/{total_tasks} 个陈旧心跳"
                    if stale_count > 0
                    else "所有心跳正常"
                ),
            }

            return availability, component_status

        except Exception as e:
            logger.error(f"检查心跳可用性失败: {e}")
            return 0.0, {"availability": 0.0, "error": str(e), "status": "error"}

    def calculate_overall_availability(self, component_availabilities: dict[str, float]) -> float:
        """计算整体可用性"""
        total_weight = 0.0
        weighted_sum = 0.0

        for component, availability in component_availabilities.items():
            weight = self.config["component_weights"].get(component, 0.0)
            weighted_sum += availability * weight
            total_weight += weight

        # 如果权重总和不为1，进行归一化
        if total_weight > 0:
            overall_availability = weighted_sum / total_weight
        else:
            overall_availability = sum(component_availabilities.values()) / len(
                component_availabilities
            )

        return overall_availability

    def check_system_availability(self) -> dict[str, Any]:
        """检查系统可用性"""
        self.monitoring_state["last_check_time"] = datetime.now().isoformat()
        self.monitoring_state["total_checks"] += 1

        availability_report = {
            "timestamp": datetime.now().isoformat(),
            "components": {},
            "overall_availability": 0.0,
            "status": "unknown",
            "alerts": [],
        }

        # 检查各组件可用性
        component_checks = {
            "runner_availability": self.check_runner_availability,
            "queue_availability": self.check_queue_availability,
            "web_api_availability": self.check_web_api_availability,
            "heartbeat_availability": self.check_heartbeat_availability,
        }

        component_availabilities = {}

        for component_name, check_func in component_checks.items():
            try:
                availability, component_status = check_func()
                component_availabilities[component_name] = availability
                availability_report["components"][component_name] = component_status
            except Exception as e:
                logger.error(f"检查组件 {component_name} 失败: {e}")
                component_availabilities[component_name] = 0.0
                availability_report["components"][component_name] = {
                    "availability": 0.0,
                    "error": str(e),
                    "status": "error",
                }

        # 计算整体可用性
        overall_availability = self.calculate_overall_availability(component_availabilities)
        availability_report["overall_availability"] = overall_availability

        # 判断系统状态
        if overall_availability >= self.config["availability_threshold"]:
            availability_report["status"] = "healthy"
        elif overall_availability >= 0.8:
            availability_report["status"] = "degraded"
        else:
            availability_report["status"] = "unhealthy"

        # 检查是否需要告警
        if overall_availability < self.config["availability_threshold"]:
            alert = {
                "type": "low_availability",
                "overall_availability": overall_availability,
                "threshold": self.config["availability_threshold"],
                "message": f"系统可用性过低: {overall_availability:.3%} < {self.config['availability_threshold']:.1%}",
                "timestamp": availability_report["timestamp"],
            }
            availability_report["alerts"].append(alert)
            self.monitoring_state["availability_below_threshold_count"] += 1

            # 输出告警
            self.handle_alerts([alert])

        # 更新监控状态
        self.monitoring_state["current_availability"] = overall_availability
        self.monitoring_state["current_status"] = availability_report["status"]

        # 保存到历史数据
        history_entry = {
            "timestamp": availability_report["timestamp"],
            "overall_availability": overall_availability,
            "component_availabilities": component_availabilities,
            "status": availability_report["status"],
        }
        self.availability_history.append(history_entry)

        # 保存组件历史
        for component, availability in component_availabilities.items():
            self.component_history[component].append(
                {
                    "timestamp": availability_report["timestamp"],
                    "availability": availability,
                }
            )

        # 更新仪表板数据
        self.update_dashboard(availability_report)

        # 定期保存历史数据
        if self.monitoring_state["total_checks"] % 10 == 0:
            self.save_history_data()

        # 记录到日志文件
        self.log_availability_metrics(availability_report)

        return availability_report

    def log_availability_metrics(self, availability_report: dict[str, Any]):
        """记录可用性指标到日志文件"""
        try:
            log_entry = {
                "timestamp": availability_report["timestamp"],
                "overall_availability": availability_report["overall_availability"],
                "status": availability_report["status"],
                "component_summary": {
                    component: {"availability": status["availability"], "status": status["status"]}
                    for component, status in availability_report["components"].items()
                },
                "alerts_count": len(availability_report["alerts"]),
            }

            with open(self.availability_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        except Exception as e:
            logger.error(f"记录可用性指标失败: {e}")

    def update_dashboard(self, availability_report: dict[str, Any]):
        """更新仪表板数据"""
        self.dashboard_data = {
            "last_update": availability_report["timestamp"],
            "current_availability": availability_report["overall_availability"],
            "component_status": {
                component: {
                    "availability": status["availability"],
                    "status": status["status"],
                    "message": status.get("message", ""),
                }
                for component, status in availability_report["components"].items()
            },
            "recent_history": list(self.availability_history)[-20:],  # 最近20个记录
            "alerts": availability_report["alerts"],
            "system_status": availability_report["status"],
        }

    def handle_alerts(self, alerts: list[dict[str, Any]]):
        """处理告警"""
        for alert in alerts:
            alert_message = f"🚨 可用性告警 [{alert['type']}]: {alert['message']}"

            if "console" in self.config["alert_channels"]:
                print(alert_message)

            if "log" in self.config["alert_channels"]:
                logger.warning(alert_message)

            # 文件告警（保存到单独文件）
            if "file" in self.config["alert_channels"]:
                try:
                    alert_file = self.root_dir / "logs" / "availability_alerts.jsonl"
                    alert_file.parent.mkdir(parents=True, exist_ok=True)

                    with open(alert_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(alert, ensure_ascii=False) + "\n")
                except Exception as e:
                    logger.error(f"保存告警到文件失败: {e}")

    def print_dashboard(self):
        """打印实时仪表板"""
        if not self.dashboard_data["last_update"]:
            print("仪表板数据尚未更新")
            return

        last_update = datetime.fromisoformat(self.dashboard_data["last_update"])
        current_availability = self.dashboard_data["current_availability"]
        system_status = self.dashboard_data["system_status"]

        print("\n" + "=" * 80)
        print("系统可用性实时监控仪表板")
        print("=" * 80)
        print(f"最后更新: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"当前可用性: {current_availability:.3%}")
        print(f"系统状态: {system_status.upper()}")
        print(f"阈值: {self.config['availability_threshold']:.1%}")
        print("-" * 80)

        # 组件状态
        print("组件状态:")
        for component, status in self.dashboard_data["component_status"].items():
            component_name = component.replace("_", " ").title()
            availability = status["availability"]
            comp_status = status["status"]
            message = status["message"]

            status_icon = (
                "✅" if comp_status == "healthy" else "⚠️" if comp_status == "degraded" else "❌"
            )
            print(f"  {status_icon} {component_name}: {availability:.1%} - {comp_status}")
            if message:
                print(f"     {message}")

        print("-" * 80)

        # 近期历史（最近5个点）
        recent_history = self.dashboard_data["recent_history"][-5:]
        if recent_history:
            print("近期可用性历史:")
            for entry in recent_history:
                timestamp = datetime.fromisoformat(entry["timestamp"])
                availability = entry["overall_availability"]
                status = entry["status"]
                print(f"  {timestamp.strftime('%H:%M:%S')}: {availability:.3%} ({status})")

        # 告警
        if self.dashboard_data["alerts"]:
            print(f"\n当前告警 ({len(self.dashboard_data['alerts'])}个):")
            for alert in self.dashboard_data["alerts"]:
                print(f"  ⚠️ {alert['message']}")

        print("=" * 80)

    def get_availability_statistics(self) -> dict[str, Any]:
        """获取可用性统计信息"""
        if not self.availability_history:
            return {"error": "无可用历史数据"}

        availabilities = [entry["overall_availability"] for entry in self.availability_history]

        statistics = {
            "total_checks": len(self.availability_history),
            "average_availability": sum(availabilities) / len(availabilities),
            "minimum_availability": min(availabilities),
            "maximum_availability": max(availabilities),
            "availability_below_threshold_count": self.monitoring_state[
                "availability_below_threshold_count"
            ],
            "availability_below_threshold_percentage": (
                self.monitoring_state["availability_below_threshold_count"]
                / len(self.availability_history)
                if self.availability_history
                else 0
            ),
            "monitoring_start_time": self.monitoring_state["start_time"],
            "last_check_time": self.monitoring_state["last_check_time"],
        }

        return statistics

    def run_monitoring_cycle(self):
        """运行监控周期"""
        logger.info(f"执行可用性检查 #{self.monitoring_state['total_checks'] + 1}")

        try:
            availability_report = self.check_system_availability()

            # 每5次检查打印一次摘要
            if self.monitoring_state["total_checks"] % 5 == 0:
                self.print_dashboard()

            return availability_report

        except Exception as e:
            logger.error(f"可用性检查失败: {e}")
            return None

    def run_continuous_monitoring(self):
        """运行持续监控"""
        logger.info("启动系统可用性实时监控...")
        logger.info(f"监控间隔: {self.config['monitoring_interval']}秒")
        logger.info(f"可用性阈值: {self.config['availability_threshold']:.1%}")

        try:
            while True:
                self.run_monitoring_cycle()
                time.sleep(self.config["monitoring_interval"])

        except KeyboardInterrupt:
            logger.info("系统可用性监控停止")

            # 保存最终历史数据
            self.save_history_data()

            # 打印统计信息
            stats = self.get_availability_statistics()
            logger.info(f"监控统计: {json.dumps(stats, indent=2)}")

        except Exception as e:
            logger.error(f"监控系统运行失败: {e}")


def main():
    """主函数"""
    monitor = AvailabilityMonitor()

    print("=" * 80)
    print("系统可用性实时监控系统")
    print("=" * 80)
    print("功能:")
    print("  1. 实时系统可用性监控")
    print("  2. 四组件可用性分析:")
    print("     - 运行器进程可用性 (权重: 40%)")
    print("     - 队列状态可用性 (权重: 30%)")
    print("     - Web API可用性 (权重: 20%)")
    print("     - 心跳健康可用性 (权重: 10%)")
    print("  3. 实时仪表板展示")
    print("  4. 历史数据分析")
    print("  5. 可用性告警机制")
    print()
    print("配置:")
    print(f"  监控间隔: {monitor.config['monitoring_interval']}秒")
    print(f"  可用性阈值: {monitor.config['availability_threshold']:.1%}")
    print(f"  仪表板刷新间隔: {monitor.config['dashboard_refresh_interval']}秒")
    print()

    # 运行一次检查
    print("执行首次可用性检查...")
    availability_report = monitor.run_monitoring_cycle()

    if availability_report:
        print(
            f"✅ 首次检查完成: 可用性 {availability_report['overall_availability']:.3%}, 状态: {availability_report['status']}"
        )
    else:
        print("❌ 首次检查失败")

    print()
    print("启动持续监控... (按Ctrl+C停止)")
    print("-" * 80)

    # 运行持续监控
    monitor.run_continuous_monitoring()


if __name__ == "__main__":
    main()
