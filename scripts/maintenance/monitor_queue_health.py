#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py health 或 governance_cli.py queue protect
"""
队列健康度监控脚本 - 增强版监控仪表板
功能：采集队列关键指标，生成健康度报告，支持HTML仪表板，邮件/Slack告警通知
按照next_phase_engineering_plan_20260419.md行动项4创建，已增强业务指标监控

主要特性：
1. 队列健康度分析：计算健康度评分（0-100），基于任务状态分布
2. 业务指标监控：
   - 任务吞吐量（completion_rate_per_hour）：每小时完成的任务数
   - 平均处理时间（avg_execution_time）：任务从创建到完成的平均时间
   - 队列深度、错误率、处理速率等
3. 系统资源监控：CPU、内存、磁盘使用率
4. 告警通知：
   - 邮件通知：支持SMTP over TLS，兼容Gmail等
   - Slack通知：通过Incoming Webhooks发送
   - 告警级别：info/warning/critical
5. HTML仪表板：可视化展示监控数据
6. 历史数据存储：记录指标历史，支持趋势分析

告警规则（8个核心规则）：
1. 队列健康度低（<60分）：critical
2. 待处理任务过多（>50%）：critical
3. 队列深度过大（>200任务）：critical
4. 错误率过高（>5%）：critical
5. 任务处理停滞（处理速率为0且有pending任务）：warning
6. 任务吞吐量低（<1任务/小时且有pending任务）：warning
7. 平均处理时间极长（>2小时）：critical
8. 平均处理时间较长（>30分钟）：warning
9. CPU使用率高（>80%）：warning
10. 内存使用率高（>80%）：warning
11. 磁盘使用率高（>85%）：warning
12. 可用内存不足（<2GB）：critical

配置方式：
1. 配置文件：创建 monitoring_config.yaml（参考 monitoring_config.yaml.example）
2. 环境变量：使用 OPENCLAW_ 前缀的环境变量（详情见 _merge_env_vars_into_config 函数）
3. 默认值：无外部凭据时仅记录日志，不发送外部通知

使用方法：
python3 monitor_queue_health.py          # 单次运行
python3 monitor_queue_health.py --loop   # 循环监控模式（每5分钟检查一次）
python3 monitor_queue_health.py --config /path/to/config.yaml  # 指定配置文件
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import psutil

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config.paths import get_queue_file

    queue_file_path = get_queue_file("build_priority")
    if queue_file_path:
        BUILD_QUEUE = Path(queue_file_path)
        print(f"✅ 使用config.paths模块获取队列文件: {BUILD_QUEUE}")
    else:
        raise ImportError("无法获取队列文件路径")
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    BUILD_QUEUE = Path(
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    )

# 其他重要队列文件
OTHER_QUEUES = [
    Path(
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414_deduplicated.json"
    ),
    # 可以根据需要添加更多队列
]

# 历史数据存储（简单内存存储）
metrics_history = []
MAX_HISTORY_SIZE = 100


def load_queue_data(queue_path):
    """加载队列数据"""
    try:
        with open(queue_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载队列文件失败 {queue_path}: {e}")
        return None


def analyze_queue_health(queue_data, queue_name):
    """分析队列健康度"""
    if not queue_data or "items" not in queue_data:
        return None

    items = queue_data.get("items", {})
    total_tasks = len(items)

    # 统计状态
    status_counts = defaultdict(int)
    for _task_id, task in items.items():
        status = task.get("status", "unknown")
        status_counts[status] += 1

    # 计算处理速率（简单估算）
    completed_tasks = status_counts.get("completed", 0)

    # 分析任务元数据获取时间信息
    execution_times = []
    completion_times = []

    for _task_id, task in items.items():
        if task.get("status") == "completed":
            metadata = task.get("metadata", {})
            created = metadata.get("created")
            metadata.get("scan_time")
            updated_at = task.get("updated_at")

            # 尝试解析时间计算处理时长
            try:
                if created and updated_at:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    execution_time = (updated_dt - created_dt).total_seconds()
                    execution_times.append(execution_time)
                    completion_times.append(updated_dt)
            except Exception:
                pass

    # 计算平均处理时间
    avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

    # 计算处理速率（基于最近完成的任务）
    # 注意：将offset-aware时间转换为offset-naive以兼容datetime.now()
    recent_completions = [
        t for t in completion_times if datetime.now() - t.replace(tzinfo=None) < timedelta(hours=24)
    ]
    completion_rate = len(recent_completions) / 24.0 if recent_completions else 0  # 任务/小时

    return {
        "queue_name": queue_name,
        "total_tasks": total_tasks,
        "status_counts": dict(status_counts),
        "completed_tasks": completed_tasks,
        "pending_tasks": status_counts.get("pending", 0),
        "running_tasks": status_counts.get("running", 0),
        "failed_tasks": status_counts.get("failed", 0),
        "avg_execution_time": avg_execution_time,
        "completion_rate_per_hour": completion_rate,
        "health_score": calculate_health_score(status_counts, total_tasks, avg_execution_time),
        "timestamp": datetime.now().isoformat(),
    }


def calculate_health_score(status_counts, total_tasks, avg_execution_time):
    """计算队列健康度评分（0-100）"""
    if total_tasks == 0:
        return 100

    # 基础分
    score = 100

    # 扣分项
    pending_ratio = status_counts.get("pending", 0) / total_tasks
    if pending_ratio > 0.5:
        score -= 30
    elif pending_ratio > 0.3:
        score -= 20
    elif pending_ratio > 0.1:
        score -= 10

    failed_ratio = status_counts.get("failed", 0) / total_tasks
    if failed_ratio > 0.1:
        score -= 20
    elif failed_ratio > 0.05:
        score -= 10

    # 处理时间扣分（如果平均处理时间超过1小时）
    if avg_execution_time > 3600:  # 1小时
        score -= 15
    elif avg_execution_time > 1800:  # 30分钟
        score -= 10

    return max(0, min(100, score))


def collect_system_metrics():
    """收集系统资源指标"""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_available_gb": memory.available / (1024**3),
        "disk_percent": disk.percent,
        "disk_free_gb": disk.free / (1024**3),
        "timestamp": datetime.now().isoformat(),
    }


def _merge_env_vars_into_config(config):
    """
    将环境变量合并到配置字典中

    环境变量命名规范：
    OPENCLAW_SMTP_SERVER -> config['email']['smtp_server']
    OPENCLAW_SLACK_WEBHOOK_URL -> config['slack']['webhook_url']
    """
    import os

    # 确保配置字典结构
    if "email" not in config:
        config["email"] = {}
    if "slack" not in config:
        config["slack"] = {}

    # 邮件配置环境变量
    email_env_mapping = {
        "OPENCLAW_SMTP_SERVER": ("smtp_server", None),
        "OPENCLAW_SMTP_PORT": ("smtp_port", lambda x: int(x) if x else None),
        "OPENCLAW_EMAIL_USERNAME": ("username", None),
        "OPENCLAW_EMAIL_PASSWORD": ("password", None),
        "OPENCLAW_FROM_EMAIL": ("from_email", None),
        "OPENCLAW_TO_EMAILS": ("to_emails", lambda x: x.split(",") if x else []),
    }

    for env_var, (config_key, transformer) in email_env_mapping.items():
        env_value = os.getenv(env_var)
        if env_value:
            # 如果配置中已有值，则不覆盖（配置文件优先级更高）
            if not config["email"].get(config_key):
                try:
                    if transformer:
                        config["email"][config_key] = transformer(env_value)
                    else:
                        config["email"][config_key] = env_value
                except Exception as e:
                    print(f"⚠️  环境变量转换失败 {env_var}={env_value}: {e}")

    # Slack配置环境变量
    slack_env_mapping = {
        "OPENCLAW_SLACK_WEBHOOK_URL": ("webhook_url", None),
        "OPENCLAW_SLACK_CHANNEL": ("channel", None),
        "OPENCLAW_SLACK_USERNAME": ("username", None),
        "OPENCLAW_SLACK_ICON_EMOJI": ("icon_emoji", None),
    }

    for env_var, (config_key, transformer) in slack_env_mapping.items():
        env_value = os.getenv(env_var)
        if env_value and not config["slack"].get(config_key):
            try:
                if transformer:
                    config["slack"][config_key] = transformer(env_value)
                else:
                    config["slack"][config_key] = env_value
            except Exception as e:
                print(f"⚠️  环境变量转换失败 {env_var}={env_value}: {e}")

    # 通知策略环境变量
    if "notification_strategy" not in config:
        config["notification_strategy"] = {}

    strategy_mapping = {
        "OPENCLAW_NOTIFY_LEVELS": (
            "send_email_for",
            lambda x: x.split(",") if x else ["critical", "warning"],
        ),
        "OPENCLAW_WORKING_HOURS_START": ("working_hours_start", lambda x: int(x) if x else 9),
        "OPENCLAW_WORKING_HOURS_END": ("working_hours_end", lambda x: int(x) if x else 18),
        "OPENCLAW_AFTER_HOURS_CRITICAL_ONLY": (
            "after_hours_critical_only",
            lambda x: x.lower() == "true" if x else True,
        ),
    }

    for env_var, (config_key, transformer) in strategy_mapping.items():
        env_value = os.getenv(env_var)
        if env_value and config_key not in config["notification_strategy"]:
            try:
                config["notification_strategy"][config_key] = transformer(env_value)
            except Exception as e:
                print(f"⚠️  环境变量转换失败 {env_var}={env_value}: {e}")

    return config


def _filter_alerts_by_policy(alerts, config):
    """
    根据通知策略过滤告警

    考虑因素：
    1. 告警级别过滤（只发送特定级别的告警）
    2. 工作时间控制
    3. 非工作时间策略
    4. 发送频率控制（需要实现状态跟踪）
    """
    if not alerts:
        return []

    strategy = config.get("notification_strategy", {})
    current_hour = datetime.now().hour

    # 检查是否在工作时间
    working_hours_start = strategy.get("working_hours_start", 9)
    working_hours_end = strategy.get("working_hours_end", 18)
    is_working_hours = working_hours_start <= current_hour < working_hours_end

    # 确定允许的告警级别
    if is_working_hours:
        allowed_levels = strategy.get("send_email_for", ["critical", "warning"])
    else:
        # 非工作时间
        after_hours_critical_only = strategy.get("after_hours_critical_only", True)
        if after_hours_critical_only:
            allowed_levels = ["critical"]
        else:
            allowed_levels = strategy.get("send_email_for", ["critical", "warning"])

    # 过滤告警
    filtered_alerts = []
    for alert in alerts:
        alert_level = alert.get("level", "info")
        if alert_level in allowed_levels:
            filtered_alerts.append(alert)

    # 简单的发送频率控制（防止告警风暴）
    # 这里可以实现更复杂的频率控制，如相同告警去重、时间窗口限制等
    # 目前仅做基本过滤

    print(
        f"📊 通知策略: 工作时间{is_working_hours}, 允许级别{allowed_levels}, "
        f"过滤后告警{len(filtered_alerts)}/{len(alerts)}"
    )

    return filtered_alerts


def send_notifications(alerts, config_path=None):
    """
    发送告警通知

    参数:
        alerts: 告警列表
        config_path: 配置文件路径（可选）
    """
    if not alerts:
        return

    print(f"🔔 检测到 {len(alerts)} 个告警，准备发送通知...")

    # 加载配置（如果提供）
    config = {}
    if config_path and Path(config_path).exists():
        try:
            import yaml

            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception:
            pass

    # 从环境变量补充配置
    config = _merge_env_vars_into_config(config)

    # 记录告警到日志文件
    log_dir = Path(__file__).parent / ".openclaw" / "monitoring_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"alert_log_{datetime.now().strftime('%Y%m%d')}.json"
    alert_entry = {"timestamp": datetime.now().isoformat(), "alerts": alerts}

    try:
        # 读取现有日志
        existing_logs = []
        if log_file.exists():
            with open(log_file, encoding="utf-8") as f:
                existing_logs = json.load(f)
                if not isinstance(existing_logs, list):
                    existing_logs = [existing_logs]

        # 添加新告警
        existing_logs.append(alert_entry)

        # 保存日志（限制大小）
        if len(existing_logs) > 100:
            existing_logs = existing_logs[-100:]

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(existing_logs, f, indent=2, ensure_ascii=False)

        print(f"📝 告警已记录到: {log_file}")
    except Exception as e:
        print(f"⚠️  告警记录失败: {e}")

    # 检查是否需要发送外部通知
    notifications_enabled = config.get("notifications_enabled", False)
    if notifications_enabled:
        notification_channels = config.get("notification_channels", [])

        # 根据策略过滤告警
        filtered_alerts = _filter_alerts_by_policy(alerts, config)

        if not filtered_alerts:
            print("ℹ️  根据通知策略，无需发送外部通知")
            return

        # 邮件通知
        if "email" in notification_channels:
            _send_email_notification(filtered_alerts, config)

        # Slack通知
        if "slack" in notification_channels:
            _send_slack_notification(filtered_alerts, config)
    else:
        print("ℹ️  外部通知未启用，仅记录到日志文件")


def _send_email_notification(alerts, config):
    """
    发送邮件通知（实际实现）

    支持SMTP over TLS，兼容Gmail等现代邮件服务商
    使用应用专用密码而非账户密码以提高安全性
    """
    email_config = config.get("email", {})

    # 检查必要配置
    required_fields = [
        "smtp_server",
        "smtp_port",
        "username",
        "password",
        "from_email",
        "to_emails",
    ]
    missing_fields = [field for field in required_fields if not email_config.get(field)]

    if missing_fields:
        print(f"⚠️  邮件配置不完整，缺少字段: {missing_fields}")
        return

    try:
        import smtplib
        import socket
        from email.header import Header
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        # 准备邮件内容
        subject_prefix = email_config.get("subject_prefix", "[OpenClaw Alert] ")

        # 按告警级别分组
        critical_alerts = [a for a in alerts if a.get("level") == "critical"]
        warning_alerts = [a for a in alerts if a.get("level") == "warning"]
        info_alerts = [a for a in alerts if a.get("level") == "info"]

        # 构建邮件主题
        if critical_alerts:
            subject = f"{subject_prefix}CRITICAL: {len(critical_alerts)}个严重告警"
        elif warning_alerts:
            subject = f"{subject_prefix}WARNING: {len(warning_alerts)}个警告告警"
        else:
            subject = f"{subject_prefix}INFO: {len(info_alerts)}个信息告警"

        # 构建HTML邮件内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                         color: white; padding: 20px; border-radius: 5px; }}
                .alert-section {{ margin: 20px 0; }}
                .alert {{ padding: 15px; margin: 10px 0; border-left: 4px solid; border-radius: 3px; }}
                .critical {{ background-color: #fee; border-left-color: #e74c3c; }}
                .warning {{ background-color: #fef9e7; border-left-color: #f39c12; }}
                .info {{ background-color: #eaf2f8; border-left-color: #3498db; }}
                .alert-title {{ font-weight: bold; font-size: 16px; margin-bottom: 5px; }}
                .alert-message {{ font-size: 14px; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #777; text-align: center; }}
                .metric-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .metric-table th, .metric-table td {{ padding: 8px; border: 1px solid #ddd; text-align: left; }}
                .metric-table th {{ background-color: #f2f2f2; }}
                .timestamp {{ color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>OpenClaw 系统告警通知</h1>
                    <p>检测时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>

                <div class="alert-section">
                    <h2>告警摘要</h2>
                    <p>总计: {len(alerts)} 个告警 (严重: {len(critical_alerts)}, 警告: {len(warning_alerts)}, 信息: {len(info_alerts)})</p>
        """

        # 添加告警详情
        for alert in alerts:
            level_class = alert.get("level", "info")
            html_content += f"""
                    <div class="alert {level_class}">
                        <div class="alert-title">{alert.get("title", "未知告警")}</div>
                        <div class="alert-message">{alert.get("message", "无详细信息")}</div>
                        <div class="timestamp">级别: {level_class.upper()}</div>
                    </div>
            """

        # 添加建议操作
        html_content += """
                </div>

                <div class="alert-section">
                    <h2>建议操作</h2>
                    <ul>
                        <li>1. 登录OpenClaw监控仪表板查看详细状态</li>
                        <li>2. 检查相关队列和系统资源</li>
                        <li>3. 如有需要，调整任务调度策略</li>
                        <li>4. 验证系统备份和恢复机制</li>
                    </ul>
                </div>

                <div class="footer">
                    <p>此邮件由 OpenClaw 监控系统自动发送</p>
                    <p>如需调整通知设置，请更新配置文件</p>
                    <p>© 2026 OpenClaw - MAREF智能框架</p>
                </div>
            </div>
        </body>
        </html>
        """

        # 构建纯文本版本（备用）
        text_content = "OpenClaw 系统告警通知\n"
        text_content += f"检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        text_content += f"总计: {len(alerts)} 个告警\n"
        text_content += f"严重: {len(critical_alerts)}, 警告: {len(warning_alerts)}, 信息: {len(info_alerts)}\n\n"

        for i, alert in enumerate(alerts, 1):
            text_content += f"{i}. [{alert.get('level', 'info').upper()}] {alert.get('title')}: {alert.get('message')}\n"

        text_content += "\n建议操作:\n"
        text_content += "1. 登录OpenClaw监控仪表板查看详细状态\n"
        text_content += "2. 检查相关队列和系统资源\n"
        text_content += "3. 如有需要，调整任务调度策略\n"
        text_content += "4. 验证系统备份和恢复机制\n"

        # 创建邮件消息
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = email_config["from_email"]
        msg["To"] = ", ".join(email_config["to_emails"])
        msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

        # 添加纯文本和HTML版本
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # 发送邮件
        smtp_server = email_config["smtp_server"]
        smtp_port = int(email_config["smtp_port"])
        username = email_config["username"]
        password = email_config["password"]

        print(f"📧 正在连接邮件服务器 {smtp_server}:{smtp_port}...")

        # 设置连接超时
        socket.setdefaulttimeout(30)

        if email_config.get("enable_tls", True):
            # 使用TLS连接
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            server.starttls()  # 启用TLS加密
        else:
            # 普通连接（不推荐）
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)

        # 登录
        server.login(username, password)

        # 发送邮件
        server.send_message(msg)

        # 关闭连接
        server.quit()

        print(f"✅ 邮件通知发送成功，收件人: {email_config['to_emails']}")

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ 邮件认证失败: {e}")
        print("   请检查用户名和密码，对于Gmail可能需要使用应用专用密码")
    except smtplib.SMTPException as e:
        print(f"❌ 邮件发送失败: {e}")
    except TimeoutError as e:
        print(f"❌ 连接邮件服务器超时: {e}")
    except Exception as e:
        print(f"❌ 邮件通知发送失败，未知错误: {e}")
        import traceback

        print(traceback.format_exc())


def _send_slack_notification(alerts, config):
    """
    发送Slack通知（实际实现）

    使用Slack Incoming Webhooks发送消息
    支持格式化消息和交互式元素
    """
    slack_config = config.get("slack", {})

    # 检查必要配置
    webhook_url = slack_config.get("webhook_url")
    if not webhook_url:
        print("⚠️  Slack配置不完整，缺少webhook_url")
        return

    try:
        # 尝试导入requests库
        try:
            import requests

        except ImportError:
            print("⚠️  requests库未安装，无法发送Slack通知")
            print("    请运行: pip install requests")
            return

        # 准备Slack消息
        channel = slack_config.get("channel", "#alerts")
        username = slack_config.get("username", "OpenClaw Monitor")
        icon_emoji = slack_config.get("icon_emoji", ":warning:")

        # 按告警级别分组
        critical_alerts = [a for a in alerts if a.get("level") == "critical"]
        warning_alerts = [a for a in alerts if a.get("level") == "warning"]
        info_alerts = [a for a in alerts if a.get("level") == "info"]

        # 确定消息颜色（Slack附件颜色）
        if critical_alerts:
            color = "#FF0000"  # 红色
            status = "严重告警"
        elif warning_alerts:
            color = "#FFA500"  # 橙色
            status = "警告告警"
        else:
            color = "#3498DB"  # 蓝色
            status = "信息通知"

        # 构建Slack消息格式
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 构建主消息文本
        text = f"🚨 *OpenClaw {status}*\n"
        text += f"检测时间: {timestamp}\n"
        text += f"总计: {len(alerts)} 个告警 (严重: {len(critical_alerts)}, 警告: {len(warning_alerts)}, 信息: {len(info_alerts)})"

        # 构建附件（详细告警列表）
        attachments = []

        # 告警详情附件
        alert_fields = []
        for _i, alert in enumerate(alerts[:10], 1):  # 最多显示10个告警
            level_emoji = (
                "🔴"
                if alert.get("level") == "critical"
                else "🟠"
                if alert.get("level") == "warning"
                else "🔵"
            )
            alert_fields.append(
                {
                    "title": f"{level_emoji} {alert.get('title', '未知告警')}",
                    "value": alert.get("message", "无详细信息"),
                    "short": False,
                }
            )

        if len(alerts) > 10:
            alert_fields.append(
                {
                    "title": "更多告警",
                    "value": f"还有 {len(alerts) - 10} 个告警未显示",
                    "short": False,
                }
            )

        # 建议操作
        suggested_actions = {
            "title": "建议操作",
            "value": "1. 登录OpenClaw监控仪表板查看详细状态\n"
            "2. 检查相关队列和系统资源\n"
            "3. 如有需要，调整任务调度策略\n"
            "4. 验证系统备份和恢复机制",
            "short": False,
        }

        alert_attachment = {
            "color": color,
            "title": "告警详情",
            "fields": alert_fields,
            "footer": "OpenClaw 监控系统",
            "ts": int(datetime.now().timestamp()),
        }

        action_attachment = {
            "color": color,
            "title": "快速操作",
            "fields": [suggested_actions],
            "footer": "点击链接查看详细监控",
            "actions": [
                {
                    "type": "button",
                    "text": "查看监控仪表板",
                    "url": "file:///Volumes/1TB-M2/openclaw/monitoring_dashboard.html",
                    "style": "primary",
                }
            ],
        }

        attachments.append(alert_attachment)
        if slack_config.get("include_suggested_actions", True):
            attachments.append(action_attachment)

        # 构建完整消息
        slack_message = {
            "channel": channel,
            "username": username,
            "icon_emoji": icon_emoji,
            "text": text,
            "attachments": attachments,
            "mrkdwn": True,
        }

        # 发送请求
        print(f"💬 正在发送Slack通知到 {channel}...")
        response = requests.post(
            webhook_url,
            json=slack_message,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # 检查响应
        if response.status_code == 200:
            print("✅ Slack通知发送成功")
        else:
            print(f"❌ Slack通知发送失败，状态码: {response.status_code}")
            print(f"   响应: {response.text}")

    except requests.exceptions.Timeout as e:
        print(f"❌ Slack请求超时: {e}")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接Slack失败: {e}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Slack请求异常: {e}")
    except Exception as e:
        print(f"❌ Slack通知发送失败，未知错误: {e}")
        import traceback

        print(traceback.format_exc())


def generate_html_dashboard(queue_metrics, system_metrics, history_data):
    """生成HTML仪表板"""
    html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw 队列健康度监控</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #f5f7fa; color: #333; line-height: 1.6; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 2rem; border-radius: 10px; margin-bottom: 2rem; }
        h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .subtitle { opacity: 0.9; font-size: 1.1rem; }
        .timestamp { margin-top: 1rem; font-size: 0.9rem; opacity: 0.8; }
        .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                         gap: 1.5rem; margin-bottom: 2rem; }
        .card { background: white; border-radius: 10px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .card-header { display: flex; justify-content: space-between; align-items: center;
                      margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #f0f0f0; }
        .card-title { font-size: 1.2rem; font-weight: 600; color: #2d3748; }
        .health-score { font-size: 2rem; font-weight: bold; }
        .health-good { color: #10b981; }
        .health-warning { color: #f59e0b; }
        .health-critical { color: #ef4444; }
        .metric-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
        .metric { text-align: center; }
        .metric-value { font-size: 1.5rem; font-weight: bold; color: #4f46e5; }
        .metric-label { font-size: 0.9rem; color: #6b7280; margin-top: 0.25rem; }
        .status-badges { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1rem; }
        .badge { padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; font-weight: 500; }
        .badge-pending { background: #fef3c7; color: #92400e; }
        .badge-running { background: #dbeafe; color: #1e40af; }
        .badge-completed { background: #d1fae5; color: #065f46; }
        .badge-failed { background: #fee2e2; color: #991b1b; }
        .system-metrics { margin-top: 2rem; }
        .alert-section { margin-top: 2rem; }
        .alert { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 1rem; margin-bottom: 1rem;
                border-radius: 0 5px 5px 0; }
        .alert-critical { background: #fee2e2; border-left-color: #ef4444; }
        .history-chart { height: 200px; margin-top: 1rem; }
        footer { text-align: center; margin-top: 3rem; color: #6b7280; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 OpenClaw 队列健康度监控</h1>
            <div class="subtitle">实时队列状态、系统资源和性能指标</div>
            <div class="timestamp">最后更新: {{timestamp}}</div>
        </header>

        <div class="dashboard-grid">
            <!-- 队列健康度卡片 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🏗️ {{queue_name}} 队列健康度</div>
                    <div class="health-score {{health_class}}">{{health_score}}/100</div>
                </div>

                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-value">{{total_tasks}}</div>
                        <div class="metric-label">总任务数</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{{pending_tasks}}</div>
                        <div class="metric-label">待处理</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{{running_tasks}}</div>
                        <div class="metric-label">进行中</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{{completed_tasks}}</div>
                        <div class="metric-label">已完成</div>
                    </div>
                </div>

                <div class="status-badges">
                    {% for status, count in status_counts.items() %}
                    <div class="badge badge-{{status}}">{{status}}: {{count}}</div>
                    {% endfor %}
                </div>

                <div style="margin-top: 1rem;">
                    <div>⏱️ 平均处理时间: {{avg_execution_time_formatted}}</div>
                    <div>📈 处理速率: {{completion_rate_per_hour_rounded}} 任务/小时</div>
                </div>
            </div>

            <!-- 系统资源卡片 -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🖥️ 系统资源</div>
                </div>

                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-value">{{cpu_percent}}%</div>
                        <div class="metric-label">CPU使用率</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{{memory_percent}}%</div>
                        <div class="metric-label">内存使用率</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{{memory_available_gb_rounded}} GB</div>
                        <div class="metric-label">可用内存</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{{disk_percent}}%</div>
                        <div class="metric-label">磁盘使用率</div>
                    </div>
                </div>

                <div style="margin-top: 1rem;">
                    <div>💾 磁盘剩余: {{disk_free_gb_rounded}} GB</div>
                </div>
            </div>
        </div>

        <!-- 告警部分 -->
        <div class="alert-section">
            <h2>⚠️ 系统告警</h2>
            {% for alert in alerts %}
            <div class="alert {{'alert-critical' if alert.level == 'critical' else ''}}">
                <strong>{{alert.title}}</strong>: {{alert.message}}
            </div>
            {% else %}
            <div style="padding: 1rem; background: #d1fae5; border-radius: 5px;">
                ✅ 所有系统运行正常，无告警
            </div>
            {% endfor %}
        </div>

        <!-- 历史趋势（简化） -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">📈 健康度趋势（最近{{history_count}}次检测）</div>
            </div>
            <div class="history-chart">
                <!-- 简单的文本图表 -->
                <pre>{{history_chart}}</pre>
            </div>
        </div>

        <footer>
            <p>OpenClaw 监控系统 | 版本: 基础监控 v1.0 | 数据更新频率: 5分钟</p>
            <p>根据 next_phase_engineering_plan_20260419.md 行动项4创建</p>
        </footer>
    </div>

    <script>
        // 自动刷新页面（每5分钟）
        setTimeout(function() {
            location.reload();
        }, 300000); // 5分钟

        // 简单的健康度颜色更新
        document.addEventListener('DOMContentLoaded', function() {
            const healthScore = document.querySelector('.health-score');
            const score = parseInt(healthScore.textContent);
            if (score >= 80) {
                healthScore.classList.add('health-good');
            } else if (score >= 60) {
                healthScore.classList.add('health-warning');
            } else {
                healthScore.classList.add('health-critical');
            }
        });
    </script>
</body>
</html>
    """

    # 准备模板数据
    if queue_metrics:
        queue_metrics["health_class"] = (
            "health-good"
            if queue_metrics["health_score"] >= 80
            else "health-warning"
            if queue_metrics["health_score"] >= 60
            else "health-critical"
        )

        # 格式化平均处理时间
        avg_seconds = queue_metrics["avg_execution_time"]
        if avg_seconds < 60:
            queue_metrics["avg_execution_time_formatted"] = f"{avg_seconds:.1f}秒"
        elif avg_seconds < 3600:
            queue_metrics["avg_execution_time_formatted"] = f"{avg_seconds / 60:.1f}分钟"
        else:
            queue_metrics["avg_execution_time_formatted"] = f"{avg_seconds / 3600:.1f}小时"
    else:
        queue_metrics = {
            "queue_name": "未知队列",
            "health_score": 0,
            "health_class": "health-critical",
            "total_tasks": 0,
            "pending_tasks": 0,
            "running_tasks": 0,
            "completed_tasks": 0,
            "status_counts": {},
            "avg_execution_time_formatted": "0秒",
            "completion_rate_per_hour": 0,
        }

    # 生成告警
    alerts = []
    if queue_metrics["health_score"] < 60:
        alerts.append(
            {
                "level": "critical",
                "title": "队列健康度低",
                "message": f"队列健康度评分仅{queue_metrics['health_score']}，需要立即关注",
            }
        )

    if queue_metrics["pending_tasks"] > queue_metrics["total_tasks"] * 0.5:
        alerts.append(
            {
                "level": "critical",
                "title": "待处理任务过多",
                "message": f"待处理任务占比超过50% ({queue_metrics['pending_tasks']}/{queue_metrics['total_tasks']})",
            }
        )

    if system_metrics["cpu_percent"] > 80:
        alerts.append(
            {
                "level": "warning",
                "title": "CPU使用率高",
                "message": f"CPU使用率超过80% ({system_metrics['cpu_percent']}%)",
            }
        )

    # 根据计划添加更多告警规则
    # 1. 队列深度>200
    if queue_metrics["total_tasks"] > 200:
        alerts.append(
            {
                "level": "critical",
                "title": "队列深度过大",
                "message": f"队列深度超过200个任务 ({queue_metrics['total_tasks']})",
            }
        )

    # 2. 错误率>5%（基于failed_tasks）
    if queue_metrics.get("failed_tasks", 0) > 0:
        error_rate = queue_metrics["failed_tasks"] / queue_metrics["total_tasks"]
        if error_rate > 0.05:
            alerts.append(
                {
                    "level": "critical",
                    "title": "错误率过高",
                    "message": f"任务错误率超过5% ({error_rate * 100:.1f}%，{queue_metrics['failed_tasks']}/{queue_metrics['total_tasks']})",
                }
            )

    # 3. 内存使用率>80%
    if system_metrics["memory_percent"] > 80:
        alerts.append(
            {
                "level": "warning",
                "title": "内存使用率高",
                "message": f"内存使用率超过80% ({system_metrics['memory_percent']}%)",
            }
        )

    # 4. 磁盘使用率>85%
    if system_metrics["disk_percent"] > 85:
        alerts.append(
            {
                "level": "warning",
                "title": "磁盘使用率高",
                "message": f"磁盘使用率超过85% ({system_metrics['disk_percent']}%)",
            }
        )

    # 5. 可用内存过低（<2GB）
    if system_metrics["memory_available_gb"] < 2:
        alerts.append(
            {
                "level": "critical",
                "title": "可用内存不足",
                "message": f"可用内存不足2GB ({system_metrics['memory_available_gb']:.1f} GB)",
            }
        )

    # 6. 长时间没有任务完成（处理速率为0且pending>0）
    if queue_metrics["completion_rate_per_hour"] == 0 and queue_metrics["pending_tasks"] > 0:
        alerts.append(
            {
                "level": "warning",
                "title": "任务处理停滞",
                "message": f"处理速率为0，但有{queue_metrics['pending_tasks']}个待处理任务",
            }
        )

    # 7. 任务吞吐量过低（每小时完成率<1且有待处理任务）
    if queue_metrics["completion_rate_per_hour"] < 1.0 and queue_metrics["pending_tasks"] > 0:
        alerts.append(
            {
                "level": "warning",
                "title": "任务吞吐量低",
                "message": f"任务吞吐量仅为{queue_metrics['completion_rate_per_hour']:.1f}任务/小时，处理速度过慢",
            }
        )

    # 8. 平均处理时间过长
    avg_seconds = queue_metrics["avg_execution_time"]
    if avg_seconds > 7200:  # 超过2小时
        alerts.append(
            {
                "level": "critical",
                "title": "平均处理时间极长",
                "message": f"平均处理时间超过2小时 ({avg_seconds / 3600:.1f}小时)，需要优化",
            }
        )
    elif avg_seconds > 1800:  # 超过30分钟
        alerts.append(
            {
                "level": "warning",
                "title": "平均处理时间较长",
                "message": f"平均处理时间超过30分钟 ({avg_seconds / 60:.1f}分钟)，建议检查",
            }
        )

    # 发送通知
    config_path = Path(__file__).parent / ".openclaw" / "maref" / "config" / "config.yaml"
    send_notifications(alerts, str(config_path) if config_path.exists() else None)

    # 添加四舍五入变量用于模板
    system_metrics["memory_available_gb_rounded"] = round(
        system_metrics.get("memory_available_gb", 0), 1
    )
    system_metrics["disk_free_gb_rounded"] = round(system_metrics.get("disk_free_gb", 0), 1)
    queue_metrics["completion_rate_per_hour_rounded"] = round(
        queue_metrics.get("completion_rate_per_hour", 0), 2
    )

    # 生成简单文本图表
    history_scores = [h.get("health_score", 0) for h in history_data[-10:]]
    history_chart = ""
    for score in history_scores:
        bars = int(score / 5)  # 每5分一个字符
        history_chart += f"{score:3d} | {'█' * bars}{'░' * (20 - bars)}\n"

    # 渲染模板
    html = html_template
    for key, value in queue_metrics.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))

    for key, value in system_metrics.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))

    html = html.replace("{{timestamp}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    html = html.replace("{{alerts}}", "")  # 简化处理，实际应该使用模板引擎
    html = html.replace("{{history_count}}", str(len(history_data)))
    html = html.replace("{{history_chart}}", history_chart)

    # 简单替换告警部分
    if alerts:
        alert_html = ""
        for alert in alerts:
            alert_class = "alert-critical" if alert["level"] == "critical" else "alert"
            alert_html += f'<div class="alert {alert_class}"><strong>{alert["title"]}</strong>: {alert["message"]}</div>'
        html = html.replace("{% for alert in alerts %}", "")
        html = html.replace("{% else %}", "")
        html = html.replace("{% endfor %}", "")
        html = html.replace(
            html[
                html.find("{% for alert in alerts %}") : html.find("{% endfor %}")
                + len("{% endfor %}")
            ],
            alert_html,
        )

    return html


def save_metrics_to_history(queue_metrics, system_metrics):
    """保存指标到历史记录"""
    metrics_record = {
        "timestamp": datetime.now().isoformat(),
        "queue": queue_metrics,
        "system": system_metrics,
    }

    metrics_history.append(metrics_record)
    if len(metrics_history) > MAX_HISTORY_SIZE:
        metrics_history.pop(0)

    # 保存到文件
    history_file = Path(__file__).parent / ".openclaw" / "monitoring_history.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(metrics_history[-50:], f, indent=2, ensure_ascii=False)
    except Exception:
        pass  # 历史记录保存失败不影响主要功能


def run_monitoring_cycle(config_path=None):
    """运行一次监控周期"""
    print("🔍 OpenClaw 队列健康度监控脚本 - 基础监控仪表板")
    print("=" * 60)

    # 检查队列文件
    if not BUILD_QUEUE.exists():
        print(f"❌ 主队列文件不存在: {BUILD_QUEUE}")
        return False

    print(f"📊 监控队列: {BUILD_QUEUE.name}")

    # 加载队列数据
    queue_data = load_queue_data(BUILD_QUEUE)
    if not queue_data:
        print("❌ 无法加载队列数据")
        return False

    # 分析队列健康度
    print("📈 分析队列健康度...")
    queue_metrics = analyze_queue_health(queue_data, BUILD_QUEUE.name)

    if not queue_metrics:
        print("❌ 队列健康度分析失败")
        return False

    # 收集系统指标
    print("🖥️  收集系统资源指标...")
    system_metrics = collect_system_metrics()

    # 保存到历史记录
    save_metrics_to_history(queue_metrics, system_metrics)

    # 生成HTML仪表板
    print("🖨️  生成HTML仪表板...")
    html_content = generate_html_dashboard(queue_metrics, system_metrics, metrics_history)

    # 保存HTML文件
    html_file = Path(__file__).parent / "monitoring_dashboard.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ HTML仪表板已保存: {html_file}")

    # 打印摘要
    print("\n📋 监控摘要:")
    print(f"   队列: {queue_metrics['queue_name']}")
    print(f"   健康度: {queue_metrics['health_score']}/100")
    print(
        f"   任务状态: 总计{queue_metrics['total_tasks']}, 待处理{queue_metrics['pending_tasks']}, 进行中{queue_metrics['running_tasks']}, 已完成{queue_metrics['completed_tasks']}"
    )
    print(f"   处理速率: {queue_metrics['completion_rate_per_hour']:.2f} 任务/小时")
    print(
        f"   系统资源: CPU {system_metrics['cpu_percent']}%, 内存 {system_metrics['memory_percent']}%"
    )

    # 生成建议
    print("\n🎯 建议:")
    if queue_metrics["health_score"] < 70:
        print("   ⚠️  队列健康度较低，需要关注")
    if queue_metrics["pending_tasks"] > 0:
        print("   🔧 有待处理任务，考虑启动任务处理器")
    if system_metrics["cpu_percent"] > 80:
        print("   💻 CPU使用率较高，考虑优化资源分配")

    print("\n🏁 监控周期完成")
    return True


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="OpenClaw队列健康度监控")
    parser.add_argument("--loop", action="store_true", help="循环监控模式（每5分钟检查一次）")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--interval", type=int, default=300, help="循环间隔秒数（默认300秒=5分钟）")

    args = parser.parse_args()

    if args.loop:
        print("🔄 启动循环监控模式")
        print(f"   检查间隔: {args.interval}秒")
        print("   按Ctrl+C退出循环监控")
        print("=" * 60)

        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                print(
                    f"\n📅 监控周期 #{cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print("-" * 40)

                success = run_monitoring_cycle(args.config)

                if not success:
                    print("⚠️  监控周期执行失败，继续下一个周期")

                print(f"\n⏰ 等待 {args.interval} 秒后执行下一次检查...")
                time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\n\n🛑 用户中断，退出循环监控模式")
            print(f"   总共执行了 {cycle_count} 个监控周期")
    else:
        # 单次运行模式
        run_monitoring_cycle(args.config)

    # 检查队列文件
    if not BUILD_QUEUE.exists():
        print(f"❌ 主队列文件不存在: {BUILD_QUEUE}")
        return

    print(f"📊 监控队列: {BUILD_QUEUE.name}")

    # 加载队列数据
    queue_data = load_queue_data(BUILD_QUEUE)
    if not queue_data:
        print("❌ 无法加载队列数据")
        return

    # 分析队列健康度
    print("📈 分析队列健康度...")
    queue_metrics = analyze_queue_health(queue_data, BUILD_QUEUE.name)

    if not queue_metrics:
        print("❌ 队列健康度分析失败")
        return

    # 收集系统指标
    print("🖥️  收集系统资源指标...")
    system_metrics = collect_system_metrics()

    # 保存到历史记录
    save_metrics_to_history(queue_metrics, system_metrics)

    # 生成HTML仪表板
    print("🖨️  生成HTML仪表板...")
    html_content = generate_html_dashboard(queue_metrics, system_metrics, metrics_history)

    # 保存HTML文件
    html_file = Path(__file__).parent / "monitoring_dashboard.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ HTML仪表板已保存: {html_file}")

    # 打印摘要
    print("\n📋 监控摘要:")
    print(f"   队列: {queue_metrics['queue_name']}")
    print(f"   健康度: {queue_metrics['health_score']}/100")
    print(
        f"   任务状态: 总计{queue_metrics['total_tasks']}, 待处理{queue_metrics['pending_tasks']}, 进行中{queue_metrics['running_tasks']}, 已完成{queue_metrics['completed_tasks']}"
    )
    print(f"   处理速率: {queue_metrics['completion_rate_per_hour']:.2f} 任务/小时")
    print(
        f"   系统资源: CPU {system_metrics['cpu_percent']}%, 内存 {system_metrics['memory_percent']}%"
    )

    # 生成建议
    print("\n🎯 建议:")
    if queue_metrics["health_score"] < 70:
        print("   ⚠️  队列健康度较低，需要关注")
    if queue_metrics["pending_tasks"] > 0:
        print("   🔧 有待处理任务，考虑启动任务处理器")
    if system_metrics["cpu_percent"] > 80:
        print("   💻 CPU使用率较高，考虑优化资源分配")

    print("\n🏁 监控完成")
    print("下一步:")
    print(f"  1. 打开 {html_file} 查看仪表板")
    print("  2. 设置定时任务定期运行此脚本")
    print("  3. 配置告警通知（邮件/Slack）")
    print("  4. 扩展监控指标和可视化")


if __name__ == "__main__":
    main()
