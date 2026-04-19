#!/usr/bin/env python3
"""系统进程监控脚本 - P0优先级修复"""

import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path

import psutil
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/Volumes/1TB-M2/openclaw/logs/process_monitor.log"),
        logging.StreamHandler(),
    ],
)


class ProcessMonitor:
    """进程监控器"""

    def __init__(self):
        self.critical_processes = [
            {
                "name": "claude-code-router",
                "expected_cmd": "claude-code-router",
                "health_check": "http://127.0.0.1:3000/health",
                "restart_command": "ccr start",
                "max_restart_attempts": 3,
                "port": 3000,
            },
            {
                "name": "athena-ai-plan-runner",
                "expected_cmd": "athena_ai_plan_runner",
                "health_check": "process_running",
                "restart_command": "启动队列运行器命令",
                "max_restart_attempts": 3,
                "port": None,
            },
            {
                "name": "athena-web-desktop",
                "expected_cmd": "athena_web_desktop",
                "health_check": "web_interface_check",
                "restart_command": "启动Web桌面命令",
                "max_restart_attempts": 3,
                "port": 8080,
            },
        ]

        self.monitor_log = Path("/Volumes/1TB-M2/openclaw/logs/process_monitor.jsonl")
        self.alert_log = Path("/Volumes/1TB-M2/openclaw/logs/alerts.log")

        # 创建日志目录
        self.monitor_log.parent.mkdir(parents=True, exist_ok=True)
        self.alert_log.parent.mkdir(parents=True, exist_ok=True)

        # 进程状态统计
        self.process_stats = {}
        for proc in self.critical_processes:
            self.process_stats[proc["name"]] = {
                "total_checks": 0,
                "healthy_checks": 0,
                "unhealthy_checks": 0,
                "last_restart_attempt": None,
                "restart_count": 0,
            }

    def find_process_by_command(self, expected_cmd):
        """根据命令查找进程"""
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
                if expected_cmd in cmdline:
                    return proc.info
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def check_http_health(self, url):
        """检查HTTP服务健康状态"""
        try:
            response = requests.get(url, timeout=5)
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds(),
                "status_code": response.status_code,
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "error": str(e),
                "response_time": None,
                "status_code": None,
            }

    def check_process_running(self, process_config):
        """检查进程是否运行"""
        process_info = self.find_process_by_command(process_config["expected_cmd"])

        if not process_info:
            return {"status": "not_found", "message": f"进程 {process_config['name']} 未找到"}

        return {"status": "running", "pid": process_info["pid"], "message": "进程运行中"}

    def check_process_health(self, process_config):
        """检查进程健康状态"""
        # 首先检查进程是否运行
        process_status = self.check_process_running(process_config)

        if process_status["status"] != "running":
            return process_status

        # 根据健康检查类型进行进一步检查
        health_check_type = process_config["health_check"]

        if health_check_type.startswith("http"):
            # HTTP健康检查
            health_result = self.check_http_health(health_check_type)

            if health_result["status"] == "healthy":
                return {
                    "status": "healthy",
                    "pid": process_status["pid"],
                    "message": "进程运行正常",
                    "response_time": health_result["response_time"],
                }
            else:
                return {
                    "status": "unhealthy",
                    "pid": process_status["pid"],
                    "message": f"健康检查失败: {health_result.get('error', '未知错误')}",
                    "response_time": health_result["response_time"],
                }
        else:
            # 简单的进程运行检查
            return {"status": "healthy", "pid": process_status["pid"], "message": "进程运行正常"}

    def restart_process(self, process_config):
        """重启进程"""
        process_name = process_config["name"]
        restart_command = process_config["restart_command"]

        logging.info(f"尝试重启进程: {process_name}")

        try:
            # 停止可能存在的进程
            subprocess.run(
                ["pkill", "-f", process_config["expected_cmd"]], capture_output=True, timeout=10
            )
            time.sleep(2)

            # 启动新进程
            result = subprocess.run(
                restart_command.split(), capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                logging.info(f"进程 {process_name} 重启成功")
                return True
            else:
                logging.error(f"进程 {process_name} 重启失败: {result.stderr}")
                return False

        except Exception as e:
            logging.error(f"重启进程 {process_name} 时发生错误: {str(e)}")
            return False

    def trigger_alert(self, process_name, health_status, severity="warning"):
        """触发告警"""
        alert_message = f"{severity.upper()} - 进程 {process_name}: {health_status['message']}"

        # 记录到告警日志
        alert_entry = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "process": process_name,
            "message": health_status["message"],
            "status": health_status["status"],
        }

        with open(self.alert_log, "a") as f:
            f.write(json.dumps(alert_entry) + "\n")

        # 根据严重程度输出不同颜色的日志
        if severity == "critical":
            logging.critical(alert_message)
        elif severity == "warning":
            logging.warning(alert_message)
        else:
            logging.info(alert_message)

    def monitor_all_processes(self):
        """监控所有关键进程"""
        results = {}

        for process_config in self.critical_processes:
            process_name = process_config["name"]

            # 更新统计
            self.process_stats[process_name]["total_checks"] += 1

            # 检查进程健康状态
            health_status = self.check_process_health(process_config)
            results[process_name] = health_status

            # 记录状态日志
            self.log_status(process_name, health_status)

            # 处理异常情况
            if health_status["status"] != "healthy":
                self.process_stats[process_name]["unhealthy_checks"] += 1

                # 确定告警级别
                if health_status["status"] == "not_found":
                    severity = "critical"
                else:
                    severity = "warning"

                # 触发告警
                self.trigger_alert(process_name, health_status, severity)

                # 尝试自动重启（仅在严重情况下）
                if severity == "critical":
                    self.attempt_auto_restart(process_config, health_status)
            else:
                self.process_stats[process_name]["healthy_checks"] += 1

        return results

    def attempt_auto_restart(self, process_config, health_status):
        """尝试自动重启"""
        process_name = process_config["name"]
        max_attempts = process_config["max_restart_attempts"]

        # 检查重启次数限制
        current_stats = self.process_stats[process_name]

        if current_stats["restart_count"] < max_attempts and (
            not current_stats["last_restart_attempt"]
            or (datetime.now() - current_stats["last_restart_attempt"]).total_seconds() > 300
        ):  # 5分钟冷却

            logging.info(f"尝试自动重启进程: {process_name}")

            if self.restart_process(process_config):
                current_stats["restart_count"] += 1
                current_stats["last_restart_attempt"] = datetime.now()
                logging.info(f"进程 {process_name} 自动重启成功")
            else:
                logging.error(f"进程 {process_name} 自动重启失败")
        else:
            logging.warning(f"已达到重启次数限制或冷却期，跳过自动重启: {process_name}")

    def log_status(self, process_name, health_status):
        """记录状态日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "process": process_name,
            "status": health_status["status"],
            "message": health_status["message"],
            "pid": health_status.get("pid"),
            "response_time": health_status.get("response_time"),
        }

        with open(self.monitor_log, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def generate_report(self):
        """生成监控报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "process_stats": {},
            "overall_health": "healthy",
        }

        unhealthy_count = 0

        for process_name, stats in self.process_stats.items():
            health_percentage = (stats["healthy_checks"] / max(1, stats["total_checks"])) * 100

            report["process_stats"][process_name] = {
                "health_percentage": round(health_percentage, 2),
                "total_checks": stats["total_checks"],
                "healthy_checks": stats["healthy_checks"],
                "unhealthy_checks": stats["unhealthy_checks"],
                "restart_count": stats["restart_count"],
                "status": "healthy" if health_percentage > 95 else "unhealthy",
            }

            if health_percentage <= 95:
                unhealthy_count += 1

        # 确定整体健康状态
        if unhealthy_count == 0:
            report["overall_health"] = "excellent"
        elif unhealthy_count <= 1:
            report["overall_health"] = "good"
        else:
            report["overall_health"] = "poor"

        return report


# 使用示例
if __name__ == "__main__":
    monitor = ProcessMonitor()

    logging.info("🚀 系统进程监控启动...")
    logging.info(f"监控的关键进程: {[p['name'] for p in monitor.critical_processes]}")

    check_count = 0

    while True:
        check_count += 1

        try:
            logging.info(f"🔍 第 {check_count} 次检查系统进程状态...")

            # 监控所有进程
            results = monitor.monitor_all_processes()

            # 输出简要状态
            for process_name, status in results.items():
                logging.info(f"  {process_name}: {status['status']} - {status['message']}")

            # 每10次检查生成一次报告
            if check_count % 10 == 0:
                report = monitor.generate_report()
                logging.info(f"📊 监控报告: 整体健康度 - {report['overall_health']}")

                # 保存详细报告
                report_file = Path(
                    f"/Volumes/1TB-M2/openclaw/logs/monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                with open(report_file, "w") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)

                logging.info(f"报告已保存: {report_file}")

            # 每30秒检查一次
            time.sleep(30)

        except KeyboardInterrupt:
            logging.info("监控服务被用户中断")
            break
        except Exception as e:
            logging.error(f"监控过程中发生错误: {str(e)}")
            time.sleep(60)  # 错误后等待1分钟再继续
