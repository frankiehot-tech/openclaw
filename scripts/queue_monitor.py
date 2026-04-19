"""
队列监控系统
实时监控Athena队列状态和执行性能
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QueueMonitor:
    """队列监控器"""

    @staticmethod
    def load_config_from_file(config_path: str = None) -> Dict[str, Any]:
        """从配置文件加载配置"""
        default_config = {
            "monitoring_interval": 60,
            "performance_thresholds": {
                "cpu_percent": 80,
                "memory_percent": 85,
                "queue_age_minutes": 30,
                "error_count_threshold": 3,
                "queue_stuck_threshold_minutes": 60,
                "empty_queue_with_pending_threshold": 1,
            },
            "alert_channels": ["log", "console"],
            "alert_configs": {
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "smtp_username": "",
                    "smtp_password": "",
                    "sender_email": "",
                    "recipient_emails": [],
                },
                "slack": {"enabled": False, "webhook_url": ""},
                "webhook": {"enabled": False, "url": "", "headers": {}, "timeout": 10},
            },
        }

        if not config_path:
            return default_config

        config_path_obj = Path(config_path)
        if not config_path_obj.exists():
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            return default_config

        try:
            # 尝试加载YAML
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)

            # 深度合并配置
            config = default_config.copy()

            # 合并顶级配置
            for key, value in file_config.items():
                if key in config:
                    if isinstance(value, dict) and isinstance(config[key], dict):
                        # 字典合并
                        config[key].update(value)
                    else:
                        config[key] = value
                else:
                    config[key] = value

            logger.info(f"从配置文件加载配置: {config_path}")
            return config

        except ImportError:
            logger.warning("未安装PyYAML，无法加载YAML配置，使用默认配置")
            return default_config
        except Exception as e:
            logger.error(f"加载配置文件失败 {config_path}: {e}，使用默认配置")
            return default_config

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self.load_config_from_file()

        self.root_dir = Path(__file__).parent.parent
        self.queue_dir = self.root_dir / ".openclaw" / "plan_queue"
        self.monitoring_log = self.root_dir / "logs" / "queue_monitoring.jsonl"
        self.alert_log = self.root_dir / "logs" / "queue_alerts.jsonl"

        # 创建日志目录
        self.monitoring_log.parent.mkdir(parents=True, exist_ok=True)

        # 监控状态
        self.monitoring_state = {
            "start_time": datetime.now().isoformat(),
            "last_check": None,
            "total_checks": 0,
            "alerts_triggered": 0,
            "metrics_collected": 0,
        }

    def check_queue_status(self) -> Dict[str, Any]:
        """检查队列状态"""
        queue_status = {
            "timestamp": datetime.now().isoformat(),
            "queues": {},
            "system_resources": {},
            "runner_processes": {},
            "alerts": [],
        }

        # 1. 检查队列文件
        if self.queue_dir.exists():
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

            queue_status["queues"]["total_files"] = len(queue_files)
            queue_status["queues"]["filtered_out"] = len(all_queue_files) - len(queue_files)

            for queue_file in queue_files:
                try:
                    with open(queue_file, "r", encoding="utf-8") as f:
                        queue_data = json.load(f)

                    queue_name = queue_file.stem
                    # 提取队列状态信息
                    queue_status_val = queue_data.get("queue_status", "unknown")
                    pause_reason_val = queue_data.get("pause_reason", "")
                    current_item_id_val = queue_data.get("current_item_id", "")
                    counts_val = queue_data.get("counts", {})
                    updated_at_val = queue_data.get("updated_at", "")
                    items_val = queue_data.get("items", {})

                    # 处理items字段：可能是列表或字典
                    items_dict = {}
                    if isinstance(items_val, list):
                        # 将列表转换为字典，使用id作为键
                        for item in items_val:
                            item_id = item.get("id")
                            if item_id:
                                items_dict[item_id] = item
                    elif isinstance(items_val, dict):
                        items_dict = items_val
                    else:
                        logger.warning(f"队列 {queue_name} 的items字段格式未知: {type(items_val)}")
                        items_dict = {}

                    # 从items字段计算实际任务状态计数（避免counts字段过时）
                    actual_counts = {
                        "pending": 0,
                        "running": 0,
                        "completed": 0,
                        "failed": 0,
                        "manual_hold": 0,
                    }
                    for item_id, item_data in items_dict.items():
                        status = str(item_data.get("status", "") or "pending").strip().lower()
                        if status in actual_counts:
                            actual_counts[status] += 1
                        else:
                            # 未知状态，按pending处理
                            actual_counts["pending"] += 1

                    # 存储队列状态，使用实际计数
                    queue_status["queues"][queue_name] = {
                        "queue_status": queue_status_val,
                        "pause_reason": pause_reason_val,
                        "current_item_id": current_item_id_val,
                        "item_count": len(items_dict),
                        "pending_count": actual_counts["pending"],
                        "running_count": actual_counts["running"],
                        "completed_count": actual_counts["completed"],
                        "failed_count": actual_counts["failed"],
                        "manual_hold_count": actual_counts["manual_hold"],
                        "updated_at": updated_at_val,
                        "counts_source": "calculated_from_items",  # 标记计数来源
                    }

                    # 检查队列年龄（使用updated_at）
                    if updated_at_val:
                        try:
                            last_updated = datetime.fromisoformat(
                                updated_at_val.replace("Z", "+00:00")
                            )
                            # 正确处理时区：确保last_updated是aware UTC时间
                            if last_updated.tzinfo is not None:
                                last_updated_utc = last_updated.astimezone(timezone.utc)
                            else:
                                # naive datetime，假定为UTC
                                last_updated_utc = last_updated.replace(tzinfo=timezone.utc)
                            now_utc = datetime.now(timezone.utc)
                            age_minutes = (now_utc - last_updated_utc).total_seconds() / 60
                            # 根据alert_configuration.md优化：empty状态队列不触发陈旧告警
                            if (
                                age_minutes
                                > self.config["performance_thresholds"]["queue_age_minutes"]
                                and queue_status_val != "empty"
                            ):
                                alert = {
                                    "type": "stale_queue",
                                    "queue": queue_name,
                                    "age_minutes": age_minutes,
                                    "threshold": self.config["performance_thresholds"][
                                        "queue_age_minutes"
                                    ],
                                    "message": f"队列 {queue_name} 已 {age_minutes:.1f} 分钟未更新",
                                }
                                queue_status["alerts"].append(alert)
                        except ValueError as e:
                            logger.warning(f"解析队列更新时间失败 {queue_name}: {e}")

                    # 检测队列堵塞：状态为empty但有pending任务
                    if queue_status_val == "empty" and counts_val.get("pending", 0) > 0:
                        alert = {
                            "type": "queue_stuck_empty_with_pending",
                            "queue": queue_name,
                            "queue_status": queue_status_val,
                            "pending_count": counts_val.get("pending", 0),
                            "message": f"队列 {queue_name} 状态为empty但有{counts_val.get('pending', 0)}个pending任务",
                        }
                        queue_status["alerts"].append(alert)

                    # 检测队列状态异常：状态为running但当前任务为空
                    if queue_status_val == "running" and not current_item_id_val:
                        alert = {
                            "type": "queue_stuck_running_without_current",
                            "queue": queue_name,
                            "queue_status": queue_status_val,
                            "message": f"队列 {queue_name} 状态为running但当前任务为空",
                        }
                        queue_status["alerts"].append(alert)

                    # 检测队列长时间卡住：状态为running但更新时间过旧
                    if queue_status_val == "running" and updated_at_val:
                        try:
                            last_updated = datetime.fromisoformat(
                                updated_at_val.replace("Z", "+00:00")
                            )
                            # 正确处理时区：确保last_updated是aware UTC时间
                            if last_updated.tzinfo is not None:
                                last_updated_utc = last_updated.astimezone(timezone.utc)
                            else:
                                # naive datetime，假定为UTC
                                last_updated_utc = last_updated.replace(tzinfo=timezone.utc)
                            now_utc = datetime.now(timezone.utc)
                            age_minutes = (now_utc - last_updated_utc).total_seconds() / 60
                            if (
                                age_minutes
                                > self.config["performance_thresholds"][
                                    "queue_stuck_threshold_minutes"
                                ]
                            ):
                                alert = {
                                    "type": "queue_stuck_long_running",
                                    "queue": queue_name,
                                    "queue_status": queue_status_val,
                                    "age_minutes": age_minutes,
                                    "threshold": self.config["performance_thresholds"][
                                        "queue_stuck_threshold_minutes"
                                    ],
                                    "message": f"队列 {queue_name} 状态为running但已 {age_minutes:.1f} 分钟未更新",
                                }
                                queue_status["alerts"].append(alert)
                        except ValueError as e:
                            logger.warning(f"解析队列更新时间失败 {queue_name}: {e}")

                    # 检测队列被手动暂停
                    if pause_reason_val and pause_reason_val not in ["empty", ""]:
                        # 根据alert_configuration.md优化：empty状态队列不应触发手动暂停告警
                        alert = {
                            "type": "queue_manually_paused",
                            "queue": queue_name,
                            "pause_reason": pause_reason_val,
                            "message": f"队列 {queue_name} 被手动暂停: {pause_reason_val}",
                        }
                        queue_status["alerts"].append(alert)

                except Exception as e:
                    logger.error(f"读取队列文件失败 {queue_file}: {e}")
        else:
            queue_status["queues"]["error"] = "队列目录不存在"

        # 2. 检查系统资源
        try:
            queue_status["system_resources"] = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_available_gb": psutil.virtual_memory().available / (1024**3),
                "disk_usage_percent": psutil.disk_usage("/").percent,
            }

            # 检查资源阈值
            if (
                queue_status["system_resources"]["cpu_percent"]
                > self.config["performance_thresholds"]["cpu_percent"]
            ):
                alert = {
                    "type": "high_cpu",
                    "cpu_percent": queue_status["system_resources"]["cpu_percent"],
                    "threshold": self.config["performance_thresholds"]["cpu_percent"],
                    "message": f"CPU使用率过高: {queue_status['system_resources']['cpu_percent']}%",
                }
                queue_status["alerts"].append(alert)

            if (
                queue_status["system_resources"]["memory_percent"]
                > self.config["performance_thresholds"]["memory_percent"]
            ):
                alert = {
                    "type": "high_memory",
                    "memory_percent": queue_status["system_resources"]["memory_percent"],
                    "threshold": self.config["performance_thresholds"]["memory_percent"],
                    "message": f"内存使用率过高: {queue_status['system_resources']['memory_percent']}%",
                }
                queue_status["alerts"].append(alert)

        except Exception as e:
            logger.error(f"检查系统资源失败: {e}")
            queue_status["system_resources"]["error"] = str(e)

        # 3. 检查运行器进程
        try:
            runner_processes = []
            for proc in psutil.process_iter(
                ["pid", "name", "cmdline", "cpu_percent", "memory_percent"]
            ):
                try:
                    cmdline = proc.info["cmdline"]
                    if cmdline and any(
                        keyword in " ".join(cmdline) for keyword in ["athena", "codex", "runner"]
                    ):
                        runner_processes.append(
                            {
                                "pid": proc.info["pid"],
                                "name": proc.info["name"],
                                "cmdline": cmdline[:3] if cmdline else [],
                                "cpu_percent": proc.info["cpu_percent"],
                                "memory_percent": proc.info["memory_percent"],
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            queue_status["runner_processes"] = runner_processes

        except Exception as e:
            logger.error(f"检查运行器进程失败: {e}")
            queue_status["runner_processes"]["error"] = str(e)

        # 4. 检查Web API状态（可选）
        try:
            # 尝试连接Athena Web API（带认证）
            headers = {"X-OpenClaw-Token": "FxwdCOtBnl_e0wQJQ2107OUqWkPOBa67"}
            response = requests.get(
                "http://127.0.0.1:8080/api/athena/queues", headers=headers, timeout=5
            )
            queue_status["web_api_status"] = {
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
            }

            if response.status_code != 200:
                alert = {
                    "type": "web_api_error",
                    "status_code": response.status_code,
                    "message": f"Web API返回错误状态码: {response.status_code}",
                }
                queue_status["alerts"].append(alert)

        except requests.RequestException as e:
            queue_status["web_api_status"] = {"error": str(e)}
            alert = {"type": "web_api_unavailable", "message": f"Web API不可用: {e}"}
            queue_status["alerts"].append(alert)

        return queue_status

    def log_monitoring_data(self, queue_status: Dict[str, Any]):
        """记录监控数据"""
        try:
            # 简化日志条目
            log_entry = {
                "timestamp": queue_status["timestamp"],
                "queues_count": len(queue_status["queues"]) - 1,  # 排除total_files
                "system_resources": {
                    "cpu_percent": queue_status["system_resources"].get("cpu_percent"),
                    "memory_percent": queue_status["system_resources"].get("memory_percent"),
                },
                "alerts_count": len(queue_status["alerts"]),
                "alerts": [alert["type"] for alert in queue_status["alerts"]],
            }

            with open(self.monitoring_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            self.monitoring_state["metrics_collected"] += 1

        except Exception as e:
            logger.error(f"记录监控数据失败: {e}")

    def handle_alerts(self, queue_status: Dict[str, Any]):
        """处理告警"""
        if not queue_status["alerts"]:
            return

        for alert in queue_status["alerts"]:
            alert_message = f"🚨 告警 [{alert['type']}]: {alert['message']}"

            # 输出到控制台
            if "console" in self.config["alert_channels"]:
                print(alert_message)

            # 记录到日志
            if "log" in self.config["alert_channels"]:
                logger.warning(alert_message)

            # 写入告警文件
            if "file" in self.config["alert_channels"]:
                try:
                    alert_entry = {
                        "timestamp": queue_status["timestamp"],
                        "alert": alert,
                        "message": alert_message,
                    }
                    with open(self.alert_log, "a", encoding="utf-8") as f:
                        f.write(json.dumps(alert_entry, ensure_ascii=False) + "\n")
                except Exception as e:
                    logger.error(f"写入告警文件失败: {e}")

            # 发送邮件告警
            if "email" in self.config["alert_channels"]:
                self.send_email_alert(alert_message, alert)

            # 发送Slack告警
            if "slack" in self.config["alert_channels"]:
                self.send_slack_alert(alert_message, alert)

            # 发送Webhook告警
            if "webhook" in self.config["alert_channels"]:
                self.send_webhook_alert(alert_message, alert)

            self.monitoring_state["alerts_triggered"] += 1

    def send_email_alert(self, alert_message: str, alert: Dict[str, Any]):
        """发送邮件告警"""
        email_config = self.config["alert_configs"]["email"]
        if not email_config["enabled"]:
            return

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # 创建邮件
            msg = MIMEMultipart()
            msg["Subject"] = f"🚨 队列监控告警: {alert['type']}"
            msg["From"] = email_config["sender_email"]
            msg["To"] = ", ".join(email_config["recipient_emails"])

            # 获取修复建议
            fix_suggestion = self.get_fix_suggestion(alert)

            # 邮件正文
            body = f"""
队列监控系统检测到告警：

告警类型: {alert['type']}
告警消息: {alert['message']}
告警时间: {alert.get('timestamp', datetime.now().isoformat())}

修复建议: {fix_suggestion}

详情请查看队列监控日志。
"""
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # 发送邮件
            with smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"]) as server:
                server.starttls()
                server.login(email_config["smtp_username"], email_config["smtp_password"])
                server.send_message(msg)

            logger.info(f"邮件告警已发送至 {email_config['recipient_emails']}")
        except Exception as e:
            logger.error(f"发送邮件告警失败: {e}")

    def send_slack_alert(self, alert_message: str, alert: Dict[str, Any]):
        """发送Slack告警"""
        slack_config = self.config["alert_configs"]["slack"]
        if not slack_config["enabled"] or not slack_config["webhook_url"]:
            return

        try:
            # 获取修复建议
            fix_suggestion = self.get_fix_suggestion(alert)

            payload = {
                "text": alert_message,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*🚨 队列监控告警*\n*类型:* {alert['type']}\n*消息:* {alert['message']}\n*时间:* {alert.get('timestamp', datetime.now().isoformat())}",
                        },
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*💡 修复建议:*\n{fix_suggestion}"},
                    },
                ],
            }

            response = requests.post(slack_config["webhook_url"], json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Slack告警已发送")
        except Exception as e:
            logger.error(f"发送Slack告警失败: {e}")

    def send_webhook_alert(self, alert_message: str, alert: Dict[str, Any]):
        """发送Webhook告警"""
        webhook_config = self.config["alert_configs"]["webhook"]
        if not webhook_config["enabled"] or not webhook_config["url"]:
            return

        try:
            # 添加修复建议到告警
            alert_with_fix = alert.copy()
            fix_suggestion = self.get_fix_suggestion(alert)
            if fix_suggestion:
                alert_with_fix["fix_suggestion"] = fix_suggestion

            payload = {
                "alert_type": alert["type"],
                "alert_message": alert["message"],
                "alert_timestamp": alert.get("timestamp", datetime.now().isoformat()),
                "monitoring_timestamp": datetime.now().isoformat(),
                "full_alert": alert_with_fix,
                "human_message": alert_message,
                "fix_suggestion": fix_suggestion,
            }

            headers = webhook_config.get("headers", {})
            timeout = webhook_config.get("timeout", 10)

            response = requests.post(
                webhook_config["url"], json=payload, headers=headers, timeout=timeout
            )
            response.raise_for_status()
            logger.info(f"Webhook告警已发送至 {webhook_config['url']}")
        except Exception as e:
            logger.error(f"发送Webhook告警失败: {e}")

    def get_fix_suggestion(self, alert: Dict[str, Any]) -> str:
        """获取告警的修复建议"""
        alert_type = alert.get("type", "")

        fix_suggestions = {
            "stale_queue": "检查队列运行器进程是否正常，尝试重启队列运行器: `python3 scripts/queue_monitor.py --once`",
            "queue_stuck_empty_with_pending": "队列状态异常，尝试手动重置队列状态或重新启动当前任务",
            "queue_stuck_running_without_current": "队列显示为运行中但没有当前任务，检查队列配置或手动设置当前任务",
            "queue_stuck_long_running": "队列长时间运行未更新，检查任务是否卡住，尝试手动干预或重启任务",
            "queue_manually_paused": "队列被手动暂停，检查pause_reason并决定是否恢复运行",
            "high_cpu": "CPU使用率过高，检查是否有异常进程，考虑优化任务调度或增加系统资源",
            "high_memory": "内存使用率过高，检查内存泄漏，考虑优化内存使用或增加系统内存",
            "web_api_error": "Web API访问错误，检查Athena Web服务器是否正常运行: `systemctl status athena-web`",
            "runner_process_missing": "队列运行器进程缺失，尝试重启运行器: `python3 scripts/athena_ai_plan_runner.py --daemon`",
        }

        # 特殊情况的详细建议
        if alert_type == "stale_queue":
            queue_name = alert.get("queue", "")
            age_minutes = alert.get("age_minutes", 0)
            if age_minutes > 1440:  # 超过24小时
                return f"队列 '{queue_name}' 已超过24小时未更新，可能需要手动检查队列文件或重新初始化队列"
            elif age_minutes > 240:  # 超过4小时
                return f"队列 '{queue_name}' 长时间未更新，建议检查队列运行器日志: `tail -f logs/queue_runner.log`"

        elif alert_type == "queue_stuck_empty_with_pending":
            pending_count = alert.get("pending_count", 0)
            if pending_count > 10:
                return f"有 {pending_count} 个任务等待处理但队列状态为空，建议检查队列配置并手动启动队列: `python3 scripts/fix_queue_state.py --queue-name {alert.get('queue', '')}`"

        elif alert_type == "high_cpu":
            cpu_percent = alert.get("cpu_percent", 0)
            if cpu_percent > 95:
                return "CPU使用率极高，立即检查是否有失控进程: `top -o cpu` 或 `htop`"

        return fix_suggestions.get(alert_type, "请检查相关系统日志以获取更多信息")

    def analyze_queue_patterns(self, queue_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析队列模式，检测异常行为"""
        patterns = []

        try:
            queues = queue_status.get("queues", {})

            # 移除total_files键
            queue_names = [name for name in queues.keys() if name != "total_files"]

            for queue_name in queue_names:
                queue_info = queues[queue_name]
                queue_status_val = queue_info.get("queue_status", "unknown")
                counts = {
                    "pending": queue_info.get("pending_count", 0),
                    "running": queue_info.get("running_count", 0),
                    "completed": queue_info.get("completed_count", 0),
                    "failed": queue_info.get("failed_count", 0),
                }
                updated_at = queue_info.get("updated_at", "")

                # 模式1: 高失败率
                total_tasks = sum(counts.values())
                if total_tasks > 0:
                    failure_rate = (counts["failed"] / total_tasks) * 100
                    if failure_rate > 20:  # 失败率超过20%
                        patterns.append(
                            {
                                "type": "high_failure_rate",
                                "queue": queue_name,
                                "failure_rate": round(failure_rate, 1),
                                "failed_count": counts["failed"],
                                "total_tasks": total_tasks,
                                "message": f"队列 '{queue_name}' 失败率过高: {failure_rate:.1f}% ({counts['failed']}/{total_tasks})",
                                "suggestion": "检查失败任务的具体错误，可能是系统配置或资源问题",
                            }
                        )

                # 模式2: 任务积压
                if counts["pending"] > 20 and counts["running"] == 0:
                    patterns.append(
                        {
                            "type": "task_backlog",
                            "queue": queue_name,
                            "pending_count": counts["pending"],
                            "message": f"队列 '{queue_name}' 有 {counts['pending']} 个任务积压但无运行中任务",
                            "suggestion": "检查队列运行器是否正常工作，可能需要增加并发或优化任务处理速度",
                        }
                    )

                # 模式3: 完成率低但运行时间长
                if queue_status_val == "running" and counts["running"] > 0 and updated_at:
                    try:
                        last_updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                        if last_updated.tzinfo is not None:
                            last_updated_utc = last_updated.astimezone(timezone.utc)
                        else:
                            last_updated_utc = last_updated.replace(tzinfo=timezone.utc)

                        now_utc = datetime.now(timezone.utc)
                        running_hours = (now_utc - last_updated_utc).total_seconds() / 3600

                        if running_hours > 2 and counts["completed"] == 0:
                            patterns.append(
                                {
                                    "type": "long_running_no_completion",
                                    "queue": queue_name,
                                    "running_hours": round(running_hours, 1),
                                    "message": f"队列 '{queue_name}' 已运行 {running_hours:.1f} 小时但无完成任务",
                                    "suggestion": "当前任务可能卡住，需要手动检查或重启任务",
                                }
                            )
                    except ValueError:
                        pass

                # 模式4: 资源使用与队列状态不匹配
                system_resources = queue_status.get("system_resources", {})
                cpu_percent = system_resources.get("cpu_percent", 0)
                memory_percent = system_resources.get("memory_percent", 0)

                if queue_status_val == "running" and cpu_percent < 5 and memory_percent < 10:
                    patterns.append(
                        {
                            "type": "low_resources_with_running_queue",
                            "queue": queue_name,
                            "cpu_percent": cpu_percent,
                            "memory_percent": memory_percent,
                            "message": f"队列 '{queue_name}' 状态为运行中但系统资源使用率很低 (CPU: {cpu_percent}%, 内存: {memory_percent}%)",
                            "suggestion": "队列可能实际上没有在处理任务，检查运行器进程状态",
                        }
                    )

            # 全局模式：多个队列同时异常
            stuck_queues = [
                name
                for name in queue_names
                if queues[name].get("queue_status") in ["empty", "paused"]
                and queues[name].get("pending_count", 0) > 0
            ]

            if len(stuck_queues) >= 2:
                patterns.append(
                    {
                        "type": "multiple_queues_stuck",
                        "queues": stuck_queues,
                        "count": len(stuck_queues),
                        "message": f"多个队列 ({', '.join(stuck_queues)}) 同时处于异常状态",
                        "suggestion": "可能是系统级问题，检查共享资源、数据库连接或网络服务",
                    }
                )

        except Exception as e:
            logger.error(f"分析队列模式失败: {e}")

        return patterns

    def generate_summary_report(self) -> Dict[str, Any]:
        """生成监控摘要报告"""
        report = {
            "monitoring_duration": (
                datetime.now() - datetime.fromisoformat(self.monitoring_state["start_time"])
            ).total_seconds(),
            "total_checks": self.monitoring_state["total_checks"],
            "alerts_triggered": self.monitoring_state["alerts_triggered"],
            "metrics_collected": self.monitoring_state["metrics_collected"],
            "timestamp": datetime.now().isoformat(),
        }

        return report

    def run_monitoring_loop(self):
        """运行监控循环"""
        logger.info("启动队列监控系统...")

        try:
            while True:
                self.monitoring_state["last_check"] = datetime.now().isoformat()
                self.monitoring_state["total_checks"] += 1

                # 检查队列状态
                queue_status = self.check_queue_status()

                # 记录监控数据
                self.log_monitoring_data(queue_status)

                # 处理告警
                self.handle_alerts(queue_status)

                # 定期打印状态
                if self.monitoring_state["total_checks"] % 10 == 0:
                    logger.info(
                        f"监控状态: {self.monitoring_state['total_checks']}次检查, "
                        f"{self.monitoring_state['alerts_triggered']}次告警"
                    )

                # 等待下次检查
                time.sleep(self.config["monitoring_interval"])

        except KeyboardInterrupt:
            logger.info("监控系统停止")

            # 生成最终报告
            final_report = self.generate_summary_report()
            logger.info(f"监控摘要: {json.dumps(final_report, indent=2)}")

        except Exception as e:
            logger.error(f"监控系统运行失败: {e}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Athena队列监控系统")
    parser.add_argument("--config", "-c", type=str, help="配置文件路径")
    parser.add_argument("--once", "-o", action="store_true", help="单次检查模式")
    parser.add_argument("--daemon", "-d", action="store_true", help="后台守护进程模式")
    parser.add_argument("--alert", "-a", action="store_true", help="启用告警测试")

    args = parser.parse_args()

    # 加载配置
    monitor = QueueMonitor(config=QueueMonitor.load_config_from_file(args.config))

    # 显示配置信息
    print("=" * 60)
    print("Athena队列监控系统")
    print("=" * 60)
    print(f"配置文件: {args.config or '默认配置'}")
    print(f"运行模式: {'单次检查' if args.once else '守护进程' if args.daemon else '默认'}")
    print()
    print("功能:")
    print("  1. 实时队列状态监控")
    print("  2. 系统资源监控")
    print("  3. 运行器进程监控")
    print("  4. 自动告警机制")
    print("  5. 性能指标收集")
    print()
    print("监控配置:")
    print(f"  监控间隔: {monitor.config['monitoring_interval']}秒")
    print(f"  CPU告警阈值: {monitor.config['performance_thresholds']['cpu_percent']}%")
    print(f"  内存告警阈值: {monitor.config['performance_thresholds']['memory_percent']}%")
    print()

    # 显示启用的告警通道
    alert_channels = monitor.config.get("alert_channels", ["console", "log"])
    print("告警通道:")
    for channel in ["console", "log", "email", "slack", "webhook"]:
        status = "✅ 启用" if channel in alert_channels else "❌ 禁用"
        print(f"  • {channel}: {status}")

    # 运行单次检查
    print("\n执行首次检查...")
    queue_status = monitor.check_queue_status()

    print(f"\n队列状态:")
    for queue_name, status in queue_status["queues"].items():
        if isinstance(status, dict) and queue_name != "total_files":
            print(
                f"  {queue_name}: {status.get('item_count', 0)}个任务, "
                f"队列状态: {status.get('queue_status', 'unknown')}, "
                f"pending: {status.get('pending_count', 0)}, "
                f"running: {status.get('running_count', 0)}, "
                f"completed: {status.get('completed_count', 0)}"
            )

    print(f"\n系统资源:")
    print(f"  CPU: {queue_status['system_resources'].get('cpu_percent', 'N/A')}%")
    print(f"  内存: {queue_status['system_resources'].get('memory_percent', 'N/A')}%")

    if queue_status["alerts"]:
        print(f"\n告警 ({len(queue_status['alerts'])}个):")
        for alert in queue_status["alerts"]:
            print(f"  ⚠️ {alert['message']}")
    else:
        print("\n✅ 无告警")

    # 处理告警
    monitor.handle_alerts(queue_status)

    # 运行模式选择
    if args.once or not args.daemon:
        print(f"\n✅ 单次检查完成")
        if not args.daemon:
            print(
                "💡 要启动持续监控，请使用 --daemon 参数: python3 scripts/queue_monitor.py --daemon --config your_config.yaml"
            )
    else:
        print(f"\n🚀 启动守护进程模式...")
        monitor.run_monitoring_loop()


if __name__ == "__main__":
    main()
