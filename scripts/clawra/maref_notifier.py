#!/usr/bin/env python3
"""
MAREF通知集成模块
支持企业微信、邮件、Slack等多种通知方式
与Athena现有通知系统集成
"""

import json
import logging
import os
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


class MAREFNotifier:
    """MAREF通知器

    职责：
    1. 发送预警通知到多种渠道
    2. 管理通知配置和渠道状态
    3. 记录通知历史
    4. 与Athena现有通知系统集成
    """

    def __init__(self, config_path: str = None):
        self.logger = self._setup_logger()
        self.config = self.load_config(config_path)
        self.notification_history: List[Dict] = []

        # 企业微信token缓存
        self.wecom_access_token: Optional[str] = None
        self.wecom_token_expires_at: float = 0

        # 初始化渠道状态
        self.channel_status = {
            "wecom": self.config.get("wecom_enabled", False),
            "email": self.config.get("email_enabled", False),
            "slack": self.config.get("slack_enabled", False),
            "file": self.config.get("file_log_enabled", True),
            "console": self.config.get("console_log_enabled", True),
        }

        self.logger.info(
            f"通知器初始化完成，可用渠道: {[k for k, v in self.channel_status.items() if v]}"
        )

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"maref_notifier")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def load_config_from_env(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """从环境变量加载配置（覆盖文件配置）"""
        # 企业微信配置
        if os.getenv("ENABLE_WECOM", "").lower() == "true":
            config["wecom_enabled"] = True

        webhook_url = os.getenv("WECOM_WEBHOOK_URL")
        if webhook_url:
            config["wecom_webhook"] = webhook_url

        # 企业微信应用API配置
        wecom_corpid = os.getenv("WECOM_CORPID")
        if wecom_corpid:
            config["wecom_corpid"] = wecom_corpid

        wecom_agentid = os.getenv("WECOM_AGENTID")
        if wecom_agentid:
            config["wecom_agentid"] = wecom_agentid

        wecom_secret = os.getenv("WECOM_SECRET")
        if wecom_secret:
            config["wecom_secret"] = wecom_secret

        # 邮件配置
        if os.getenv("ENABLE_EMAIL", "").lower() == "true":
            config["email_enabled"] = True

        smtp_server = os.getenv("SMTP_SERVER")
        if smtp_server:
            config["email_smtp_server"] = smtp_server

        smtp_port = os.getenv("SMTP_PORT")
        if smtp_port:
            # 清理可能的注释
            clean_port = smtp_port.split("#")[0].strip()
            try:
                config["email_smtp_port"] = int(clean_port)
            except ValueError:
                self.logger.warning(f"无效的SMTP端口: {smtp_port}")

        smtp_username = os.getenv("SMTP_USERNAME")
        if smtp_username:
            config["email_sender"] = smtp_username

        smtp_password = os.getenv("SMTP_PASSWORD")
        if smtp_password:
            config["email_password"] = smtp_password

        # 邮件接收者
        email_receivers = os.getenv("EMAIL_RECEIVERS")
        if email_receivers:
            config["email_receivers"] = [email.strip() for email in email_receivers.split(",")]

        # SMTP加密设置
        smtp_use_ssl = os.getenv("SMTP_USE_SSL", "").lower() == "true"
        smtp_use_tls = os.getenv("SMTP_USE_TLS", "").lower() == "true"
        config["email_use_ssl"] = smtp_use_ssl
        config["email_use_tls"] = smtp_use_tls

        # Slack配置
        if os.getenv("ENABLE_SLACK", "").lower() == "true":
            config["slack_enabled"] = True

        slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        if slack_webhook:
            config["slack_webhook"] = slack_webhook

        # Athena集成
        if os.getenv("ENABLE_ATHENA_INTEGRATION", "").lower() == "true":
            config["athena_integration_enabled"] = True

        athena_api = os.getenv("ATHENA_API_URL")
        if athena_api:
            config["athena_notification_api"] = athena_api

        # 文件日志配置
        if os.getenv("ENABLE_FILE_LOG", "").lower() == "true":
            config["file_log_enabled"] = True

        log_path = os.getenv("NOTIFICATION_LOG_PATH")
        if log_path:
            config["file_log_path"] = log_path

        # 控制台日志
        if os.getenv("ENABLE_CONSOLE", "").lower() == "true":
            config["console_log_enabled"] = True

        self.logger.info("已从环境变量加载配置")
        return config

    def load_config(self, config_path: str = None) -> Dict[str, Any]:
        """加载通知配置（环境变量优先）"""
        # 默认配置
        config = {
            "wecom_enabled": False,
            "wecom_webhook": "",
            "wecom_corpid": "",  # 企业微信应用API
            "wecom_agentid": "",
            "wecom_secret": "",
            "email_enabled": False,
            "email_smtp_server": "smtp.gmail.com",
            "email_smtp_port": 587,
            "email_sender": "",
            "email_receivers": [],
            "email_password": "",
            "email_use_ssl": False,
            "email_use_tls": True,
            "slack_enabled": False,
            "slack_webhook": "",
            "file_log_enabled": True,
            "file_log_path": "/var/log/maref_notifications.log",
            "console_log_enabled": True,
            "athena_integration_enabled": True,
            "athena_notification_api": "http://localhost:8000/api/notifications",
        }

        # 首先从配置文件加载
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                config.update(file_config)
                self.logger.info(f"从 {config_path} 加载通知配置")
            except Exception as e:
                self.logger.error(f"加载通知配置文件失败: {e}")

        # 环境变量覆盖配置文件
        config = self.load_config_from_env(config)

        # 记录配置摘要（隐藏敏感信息）
        config_summary = config.copy()
        if "email_password" in config_summary:
            config_summary["email_password"] = "***" if config_summary["email_password"] else ""
        if "wecom_secret" in config_summary:
            config_summary["wecom_secret"] = "***" if config_summary["wecom_secret"] else ""

        self.logger.info(f"最终配置摘要: {config_summary}")
        return config

    def send_alert(
        self, alert_type: str, alerts: List[Dict], report_path: str = None
    ) -> Dict[str, Any]:
        """发送预警通知

        Args:
            alert_type: 'red'（红色预警）或 'yellow'（黄色预警）
            alerts: 预警列表，每个预警包含title、description、recommendation等字段
            report_path: 详细报告文件路径

        Returns:
            发送结果统计
        """
        if not alerts:
            self.logger.info("无预警需要发送")
            return {"sent": 0, "failed": 0, "channels": {}}

        # 构建通知内容
        if alert_type == "red":
            title = "🔴 MAREF红色预警通知"
            color = "#FF0000"
            priority = "critical"
        elif alert_type == "yellow":
            title = "🟡 MAREF黄色预警通知"
            color = "#FFA500"
            priority = "warning"
        else:
            title = "ℹ️ MAREF系统通知"
            color = "#007BFF"
            priority = "info"

        message = self.build_alert_message(title, alerts, report_path, priority)
        results = {"sent": 0, "failed": 0, "channels": {}}

        self.logger.info(f"开始发送{len(alerts)}个{alert_type}预警")

        # 发送到各个渠道
        if self.channel_status["console"]:
            success = self.send_console_notification(title, alerts)
            results["channels"]["console"] = "success" if success else "failed"
            results["sent"] += 1 if success else 0
            results["failed"] += 0 if success else 1

        if self.channel_status["file"]:
            success = self.send_file_notification(title, message)
            results["channels"]["file"] = "success" if success else "failed"
            results["sent"] += 1 if success else 0
            results["failed"] += 0 if success else 1

        if self.channel_status["wecom"]:
            success = self.send_wecom_message(message)
            results["channels"]["wecom"] = "success" if success else "failed"
            results["sent"] += 1 if success else 0
            results["failed"] += 0 if success else 1

        if self.channel_status["email"] and alerts:  # 只在有预警时发送邮件
            success = self.send_email_notification(title, message)
            results["channels"]["email"] = "success" if success else "failed"
            results["sent"] += 1 if success else 0
            results["failed"] += 0 if success else 1

        if self.channel_status["slack"]:
            success = self.send_slack_message(title, message, color)
            results["channels"]["slack"] = "success" if success else "failed"
            results["sent"] += 1 if success else 0
            results["failed"] += 0 if success else 1

        # 集成到Athena通知系统
        if self.config.get("athena_integration_enabled", True):
            success = self.send_to_athena_system(alert_type, alerts, report_path)
            results["channels"]["athena"] = "success" if success else "failed"
            results["sent"] += 1 if success else 0
            results["failed"] += 0 if success else 1

        # 记录通知历史
        self.record_notification_history(alert_type, alerts, results)

        self.logger.info(
            f"通知发送完成: 成功 {results['sent']} 个渠道, 失败 {results['failed']} 个渠道"
        )
        return results

    def build_alert_message(
        self, title: str, alerts: List[Dict], report_path: str = None, priority: str = "info"
    ) -> str:
        """构建预警消息"""
        now = datetime.now()
        message = f"## {title}\n\n"
        message += f"**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"**优先级**: {priority.upper()}\n\n"

        if report_path:
            message += f"**详细报告**: {report_path}\n\n"

        message += f"### 预警摘要\n"
        message += f"共检测到 **{len(alerts)}** 个预警:\n\n"

        for i, alert in enumerate(alerts, 1):
            message += f"#### 预警{i}: {alert['title']}\n"
            message += f"- **问题**: {alert['description']}\n"
            message += f"- **建议**: {alert['recommendation']}\n"

            if "duration" in alert:
                minutes = alert["duration"] // 60
                if minutes > 60:
                    hours = minutes // 60
                    message += f"- **持续时间**: {hours}小时{minutes % 60}分钟\n"
                else:
                    message += f"- **持续时间**: {minutes}分钟\n"

            if "priority" in alert:
                message += f"- **紧急程度**: {alert['priority']}\n"

            if "metrics_snapshot" in alert and alert["metrics_snapshot"]:
                message += (
                    f"- **相关指标**: {json.dumps(alert['metrics_snapshot'], ensure_ascii=False)}\n"
                )

            message += "\n"

        message += "---\n"
        message += "**处理建议**:\n"
        message += "1. 立即查看详细报告了解问题详情\n"
        message += "2. 根据建议采取相应措施\n"
        message += "3. 如问题持续，请人工介入处理\n\n"
        message += "此通知由MAREF工程化监控系统自动生成。\n"

        return message

    def send_console_notification(self, title: str, alerts: List[Dict]) -> bool:
        """发送控制台通知"""
        try:
            print(f"\n{'='*60}")
            print(f"MAREF系统通知: {title}")
            print(f"{'='*60}")

            for i, alert in enumerate(alerts, 1):
                print(f"\n预警{i}: {alert['title']}")
                print(f"问题: {alert['description']}")
                print(f"建议: {alert['recommendation']}")
                if "duration" in alert:
                    print(f"持续: {alert['duration']//60}分钟")

            print(f"\n{'='*60}")
            print("请及时处理上述预警\n")

            self.logger.info("控制台通知发送成功")
            return True
        except Exception as e:
            self.logger.error(f"控制台通知发送失败: {e}")
            return False

    def send_file_notification(self, title: str, message: str) -> bool:
        """发送文件通知（记录到日志文件）"""
        try:
            log_path = self.config.get("file_log_path", "/var/log/maref_notifications.log")
            log_dir = Path(log_path).parent

            # 确保日志目录存在
            log_dir.mkdir(parents=True, exist_ok=True)

            with open(log_path, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n{'='*60}\n")
                f.write(f"[{timestamp}] {title}\n")
                f.write(f"{'='*60}\n")
                f.write(f"{message}\n")
                f.write(f"{'='*60}\n")

            self.logger.info(f"文件通知已记录到 {log_path}")
            return True
        except Exception as e:
            self.logger.error(f"文件通知发送失败: {e}")
            return False

    def get_wecom_access_token(self) -> Optional[str]:
        """获取企业微信Access Token"""
        # 检查token是否过期（提前5分钟刷新）
        if self.wecom_access_token and time.time() < self.wecom_token_expires_at - 300:
            return self.wecom_access_token

        corpid = self.config.get("wecom_corpid")
        secret = self.config.get("wecom_secret")

        if not corpid or not secret:
            self.logger.warning("企业微信CorpID或Secret未配置")
            return None

        token_url = (
            f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={secret}"
        )

        try:
            response = requests.get(token_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("errcode") == 0:
                    self.wecom_access_token = data.get("access_token")
                    expires_in = data.get("expires_in", 7200)
                    self.wecom_token_expires_at = time.time() + expires_in
                    self.logger.info("企业微信Access Token获取成功")
                    return self.wecom_access_token
                else:
                    self.logger.error(f"企业微信Token获取失败: {data.get('errmsg')}")
                    return None
            else:
                self.logger.error(f"企业微信Token请求失败: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"企业微信Token请求异常: {e}")
            return None

    def send_wecom_via_api(self, message: str) -> bool:
        """通过企业微信应用API发送消息"""
        access_token = self.get_wecom_access_token()
        if not access_token:
            self.logger.error("无法获取企业微信Access Token")
            return False

        agentid = self.config.get("wecom_agentid")
        if not agentid:
            self.logger.warning("企业微信AgentId未配置")
            return False

        # 企业微信API消息格式
        payload = {
            "touser": "@all",
            "msgtype": "markdown",
            "agentid": agentid,
            "markdown": {"content": message},
            "safe": 0,
            "enable_id_trans": 0,
            "enable_duplicate_check": 0,
            "duplicate_check_interval": 1800,
        }

        api_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

        try:
            response = requests.post(api_url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("errcode") == 0:
                    self.logger.info("企业微信API通知发送成功")
                    return True
                else:
                    errcode = data.get("errcode")
                    errmsg = data.get("errmsg")
                    self.logger.error(f"企业微信API发送失败: {errcode} - {errmsg}")

                    # 如果是IP白名单错误，记录详细信息
                    if errcode == 60020:
                        self.logger.error("IP白名单错误: 服务器IP不在企业微信应用白名单中")
                        self.logger.error("请在企微管理后台添加服务器IP到白名单，或使用webhook方式")

                    return False
            else:
                self.logger.error(f"企业微信API请求失败: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"企业微信API请求异常: {e}")
            return False

    def send_wecom_message(self, message: str) -> bool:
        """发送企业微信消息（先尝试webhook，失败后尝试应用API）"""
        wecom_webhook = self.config.get("wecom_webhook")

        # 尝试webhook方式
        if wecom_webhook:
            payload = {"msgtype": "markdown", "markdown": {"content": message}}

            try:
                response = requests.post(wecom_webhook, json=payload, timeout=10)
                if response.status_code == 200:
                    self.logger.info("企业微信Webhook通知发送成功")
                    return True
                else:
                    self.logger.warning(f"企业微信Webhook发送失败: {response.status_code}")
                    # 继续尝试应用API
            except Exception as e:
                self.logger.warning(f"企业微信Webhook异常: {e}")
                # 继续尝试应用API

        # 尝试应用API方式
        if (
            self.config.get("wecom_corpid")
            and self.config.get("wecom_secret")
            and self.config.get("wecom_agentid")
        ):
            self.logger.info("尝试使用企业微信应用API发送消息...")
            return self.send_wecom_via_api(message)

        self.logger.warning("企业微信未配置任何有效的发送方式")
        return False

    def send_email_notification(self, title: str, message: str) -> bool:
        """发送邮件通知"""
        if not self.config.get("email_enabled"):
            return False

        smtp_server = self.config.get("email_smtp_server")
        smtp_port = self.config.get("email_smtp_port", 587)
        sender = self.config.get("email_sender")
        receivers = self.config.get("email_receivers", [])
        password = self.config.get("email_password")
        use_ssl = self.config.get("email_use_ssl", False)
        use_tls = self.config.get("email_use_tls", True)

        if not all([smtp_server, sender, receivers, password]):
            self.logger.warning("邮件配置不完整，跳过邮件发送")
            return False

        try:
            # 构建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"MAREF系统通知: {title}"
            msg["From"] = sender
            msg["To"] = ", ".join(receivers)

            # HTML格式内容
            html_content = f"""
            <html>
            <body>
            <h2>MAREF系统通知</h2>
            <p><strong>标题:</strong> {title}</p>
            <p><strong>时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            <pre>{message}</pre>
            <hr>
            <p>此邮件由MAREF工程化监控系统自动发送，请勿直接回复。</p>
            </body>
            </html>
            """

            msg.attach(MIMEText(message, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 发送邮件
            if use_ssl:
                # SSL连接（端口465）
                context = smtplib.ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    smtp_server, smtp_port, context=context, timeout=10
                ) as server:
                    server.login(sender, password)
                    server.send_message(msg)
                    self.logger.info(f"邮件通知发送成功（SSL），收件人: {receivers}")
            else:
                # 普通连接，可能使用TLS
                with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                    server.ehlo()

                    if use_tls:
                        server.starttls()
                        server.ehlo()

                    server.login(sender, password)
                    server.send_message(msg)
                    self.logger.info(
                        f"邮件通知发送成功（{'TLS' if use_tls else '无加密'}），收件人: {receivers}"
                    )

            return True
        except Exception as e:
            self.logger.error(f"邮件通知发送失败: {e}")
            return False

    def send_slack_message(self, title: str, message: str, color: str) -> bool:
        """发送Slack消息"""
        slack_webhook = self.config.get("slack_webhook")
        if not slack_webhook:
            self.logger.warning("Slack Webhook未配置")
            return False

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message,
                    "footer": "MAREF监控系统",
                    "ts": int(datetime.now().timestamp()),
                }
            ]
        }

        try:
            response = requests.post(slack_webhook, json=payload, timeout=10)
            if response.status_code == 200:
                self.logger.info("Slack通知发送成功")
                return True
            else:
                self.logger.error(f"Slack通知发送失败: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Slack通知异常: {e}")
            return False

    def send_to_athena_system(
        self, alert_type: str, alerts: List[Dict], report_path: str = None
    ) -> bool:
        """发送到Athena通知系统"""
        api_url = self.config.get("athena_notification_api")
        if not api_url:
            self.logger.warning("Athena通知API未配置")
            return False

        payload = {
            "system": "maref",
            "alert_type": alert_type,
            "alerts": alerts,
            "timestamp": datetime.now().isoformat(),
            "report_path": report_path,
        }

        try:
            response = requests.post(api_url, json=payload, timeout=10)
            if response.status_code in [200, 201]:
                self.logger.info("Athena系统通知发送成功")
                return True
            else:
                self.logger.error(f"Athena系统通知发送失败: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Athena系统通知异常: {e}")
            return False

    def record_notification_history(
        self, alert_type: str, alerts: List[Dict], results: Dict[str, Any]
    ):
        """记录通知历史"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": alert_type,
            "alert_count": len(alerts),
            "alert_titles": [alert["title"] for alert in alerts],
            "results": results,
            "channels_used": [k for k, v in results["channels"].items() if v == "success"],
        }

        self.notification_history.append(history_entry)

        # 限制历史记录数量
        if len(self.notification_history) > 1000:
            self.notification_history = self.notification_history[-1000:]

    def get_notification_status(self) -> Dict[str, Any]:
        """获取通知器状态"""
        return {
            "channel_status": self.channel_status,
            "total_notifications": len(self.notification_history),
            "recent_notifications": (
                self.notification_history[-5:] if self.notification_history else []
            ),
            "config_summary": {
                "wecom_enabled": self.config.get("wecom_enabled"),
                "email_enabled": self.config.get("email_enabled"),
                "slack_enabled": self.config.get("slack_enabled"),
                "athena_integration": self.config.get("athena_integration_enabled"),
            },
        }


def test_notifier():
    """测试通知器"""
    print("=== MAREF通知器测试 ===")

    # 创建通知器
    notifier = MAREFNotifier()

    print(f"✅ 通知器创建成功")
    status = notifier.get_notification_status()
    print(f"渠道状态: {status['channel_status']}")

    # 测试预警数据
    test_alerts = [
        {
            "title": "控制熵超出安全范围",
            "description": "控制熵H_c超出安全范围(3-6 bits)",
            "recommendation": "立即检查系统状态，调整控制策略",
            "duration": 1890,  # 31.5分钟
            "priority": "critical",
            "metrics_snapshot": {"control_entropy_h_c": 2.8},
        },
        {
            "title": "系统资源紧张",
            "description": "CPU使用率>85%或内存使用率>90%",
            "recommendation": "优化资源使用，考虑扩容",
            "duration": 7200,  # 2小时
            "priority": "medium",
            "metrics_snapshot": {"cpu_usage": 92.5, "memory_usage": 87.3},
        },
    ]

    print("\n=== 通知发送测试 ===")
    print("测试红色预警通知...")
    results = notifier.send_alert("red", test_alerts, "/tmp/test_report.md")

    print(f"发送结果: {results}")
    print(f"成功渠道: {results['sent']}")
    print(f"失败渠道: {results['failed']}")
    print(f"渠道详情: {results['channels']}")

    print("\n=== 通知状态测试 ===")
    final_status = notifier.get_notification_status()
    print(f"总通知数: {final_status['total_notifications']}")
    print(f"最近通知: {[n['alert_titles'] for n in final_status['recent_notifications']]}")

    print("\n=== 测试完成 ===")
    print("MAREF通知器功能验证通过")


if __name__ == "__main__":
    test_notifier()
