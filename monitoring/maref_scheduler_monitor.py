#!/usr/bin/env python3
"""
MAREF河图洛书调度器监控脚本
监控调度器运行状态、任务状态和系统健康度
"""

import argparse
import datetime
import json
import sys
import time
from pathlib import Path

# 添加mini-agent路径以便导入调度器
sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")
from agent.core.maref_quality.hetu_luoshu_scheduler import (
    HetuLuoshuScheduler,
)


class MarefSchedulerMonitor:
    """MAREF调度器监控器"""

    def __init__(self, state_file_path: str, log_dir: str = None):
        """
        初始化监控器

        Args:
            state_file_path: 状态文件路径
            log_dir: 日志目录，默认使用监控目录下的logs
        """
        self.state_file_path = Path(state_file_path)
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent / "logs"
        self.log_dir.mkdir(exist_ok=True)

        # 日志文件
        self.status_log = self.log_dir / "scheduler_status.log"
        self.metrics_log = self.log_dir / "scheduler_metrics.log"

        # 指标历史
        self.metrics_history = []

        print("📊 MAREF调度器监控器初始化完成")
        print(f"   状态文件: {self.state_file_path}")
        print(f"   日志目录: {self.log_dir}")

    def check_state_file(self) -> dict:
        """检查状态文件状态"""
        result = {
            "file_exists": self.state_file_path.exists(),
            "file_size": 0,
            "last_modified": None,
            "is_valid_json": False,
            "state_data": None,
        }

        if result["file_exists"]:
            result["file_size"] = self.state_file_path.stat().st_size
            result["last_modified"] = datetime.datetime.fromtimestamp(
                self.state_file_path.stat().st_mtime
            ).isoformat()

            # 尝试读取和解析JSON
            try:
                with open(self.state_file_path, encoding="utf-8") as f:
                    data = json.load(f)
                result["is_valid_json"] = True
                result["state_data"] = data
            except Exception as e:
                result["error"] = str(e)

        return result

    def load_and_analyze_state(self) -> dict:
        """加载和分析状态数据"""
        if not self.state_file_path.exists():
            return {"error": "状态文件不存在"}

        try:
            with open(self.state_file_path, encoding="utf-8") as f:
                data = json.load(f)

            analysis = {
                "total_tasks": len(data.get("tasks", {})),
                "task_states": {},
                "scheduler_status": data.get("scheduler_status", {}),
                "saved_at": data.get("saved_at"),
                "task_distribution": {},
            }

            # 分析任务状态分布
            task_states = {}
            for _task_id, task_info in data.get("tasks", {}).items():
                state = task_info.get("state", "UNKNOWN")
                task_states[state] = task_states.get(state, 0) + 1

                # 按优先级统计
                priority = task_info.get("priority", "MEDIUM")
                if priority not in analysis["task_distribution"]:
                    analysis["task_distribution"][priority] = {"total": 0, "by_state": {}}
                analysis["task_distribution"][priority]["total"] += 1
                analysis["task_distribution"][priority]["by_state"][state] = (
                    analysis["task_distribution"][priority]["by_state"].get(state, 0) + 1
                )

            analysis["task_states"] = task_states

            return analysis

        except Exception as e:
            return {"error": f"状态分析失败: {str(e)}"}

    def create_scheduler_instance(self) -> HetuLuoshuScheduler:
        """创建调度器实例（用于测试和监控）"""
        scheduler = HetuLuoshuScheduler(state_file=str(self.state_file_path), max_concurrent=5)
        return scheduler

    def get_live_status(self, scheduler: HetuLuoshuScheduler) -> dict:
        """获取实时系统状态"""
        try:
            report = scheduler.get_system_report()

            live_status = {
                "timestamp": datetime.datetime.now().isoformat(),
                "total_tasks": report["total_tasks"],
                "queue_length": report["scheduler_status"]["queue_length"],
                "running_tasks": report["scheduler_status"]["running_tasks"],
                "completed_tasks": report["scheduler_status"]["completed_tasks"],
                "position_load": report["scheduler_status"]["position_load"],
                "max_concurrent": report["scheduler_status"]["max_concurrent"],
                "throughput": report["scheduler_status"]["throughput"],
                "state_manager": {
                    "tracked_tasks": report["state_manager"]["tracked_tasks"],
                    "state_file": report["state_manager"]["state_file"],
                },
            }

            return live_status
        except Exception as e:
            return {"error": f"获取实时状态失败: {str(e)}"}

    def check_system_health(self, scheduler: HetuLuoshuScheduler) -> dict:
        """检查系统健康度"""
        health = {
            "timestamp": datetime.datetime.now().isoformat(),
            "overall_status": "UNKNOWN",
            "checks": [],
            "issues": [],
        }

        # 检查1: 状态文件可访问性
        file_check = self.check_state_file()
        health["checks"].append(
            {
                "name": "状态文件检查",
                "status": (
                    "PASS" if file_check["file_exists"] and file_check["is_valid_json"] else "FAIL"
                ),
                "details": file_check,
            }
        )

        if not file_check["file_exists"]:
            health["issues"].append("状态文件不存在")

        # 检查2: 调度器队列状态
        try:
            report = scheduler.get_system_report()
            queue_ratio = report["scheduler_status"]["queue_length"] / max(
                report["scheduler_status"]["max_concurrent"], 1
            )

            queue_status = "PASS"
            if queue_ratio > 2.0:
                queue_status = "WARNING"
                health["issues"].append(
                    f"队列长度过高: {report['scheduler_status']['queue_length']}"
                )
            elif queue_ratio > 5.0:
                queue_status = "FAIL"
                health["issues"].append(
                    f"队列严重阻塞: {report['scheduler_status']['queue_length']}"
                )

            health["checks"].append(
                {
                    "name": "队列状态检查",
                    "status": queue_status,
                    "details": {
                        "queue_length": report["scheduler_status"]["queue_length"],
                        "max_concurrent": report["scheduler_status"]["max_concurrent"],
                        "ratio": queue_ratio,
                    },
                }
            )
        except Exception as e:
            health["checks"].append(
                {"name": "队列状态检查", "status": "ERROR", "details": {"error": str(e)}}
            )
            health["issues"].append(f"队列状态检查失败: {str(e)}")

        # 检查3: 位置负载均衡
        try:
            position_load = report["scheduler_status"]["position_load"]
            overloaded_positions = [
                pos for pos, load in position_load.items() if load > 3  # 假设每个位置最大并发为3
            ]

            load_status = "PASS"
            if overloaded_positions:
                load_status = "WARNING"
                health["issues"].append(f"位置负载过高: {overloaded_positions}")

            health["checks"].append(
                {
                    "name": "位置负载检查",
                    "status": load_status,
                    "details": {"position_load": position_load, "overloaded": overloaded_positions},
                }
            )
        except Exception as e:
            health["checks"].append(
                {"name": "位置负载检查", "status": "ERROR", "details": {"error": str(e)}}
            )

        # 总体状态
        if any(check["status"] == "FAIL" for check in health["checks"]):
            health["overall_status"] = "FAIL"
        elif any(check["status"] == "WARNING" for check in health["checks"]):
            health["overall_status"] = "WARNING"
        elif all(check["status"] == "PASS" for check in health["checks"]):
            health["overall_status"] = "PASS"
        else:
            health["overall_status"] = "UNKNOWN"

        return health

    def log_status(self, status_type: str, data: dict):
        """记录状态到日志文件"""
        timestamp = datetime.datetime.now().isoformat()
        log_entry = {"timestamp": timestamp, "type": status_type, "data": data}

        # 写入状态日志
        with open(self.status_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # 如果是指标数据，记录到指标日志
        if status_type == "metrics":
            self.metrics_history.append(log_entry)
            if len(self.metrics_history) > 1000:  # 保留最近1000条记录
                self.metrics_history = self.metrics_history[-1000:]

    def generate_report(self, hours: int = 24) -> dict:
        """生成监控报告"""
        if not self.status_log.exists():
            return {"error": "状态日志文件不存在"}

        try:
            # 读取最近N小时的日志
            cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
            recent_entries = []

            with open(self.status_log, encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.datetime.fromisoformat(entry["timestamp"])
                        if entry_time >= cutoff_time:
                            recent_entries.append(entry)
                    except:
                        continue

            # 分析日志
            report = {
                "report_period_hours": hours,
                "total_entries": len(recent_entries),
                "entry_types": {},
                "health_trend": [],
                "issues_summary": [],
            }

            # 统计条目类型
            for entry in recent_entries:
                entry_type = entry["type"]
                report["entry_types"][entry_type] = report["entry_types"].get(entry_type, 0) + 1

            # 提取健康趋势
            health_entries = [e for e in recent_entries if e["type"] == "health"]
            for entry in health_entries[-10:]:  # 最近10次健康检查
                health_data = entry["data"]
                report["health_trend"].append(
                    {
                        "timestamp": entry["timestamp"],
                        "overall_status": health_data["overall_status"],
                        "issue_count": len(health_data.get("issues", [])),
                    }
                )

            # 汇总问题
            all_issues = []
            for entry in recent_entries:
                if "data" in entry and "issues" in entry["data"]:
                    for issue in entry["data"]["issues"]:
                        all_issues.append({"timestamp": entry["timestamp"], "issue": issue})

            # 按问题类型分组
            issue_groups = {}
            for issue_item in all_issues:
                issue_text = issue_item["issue"]
                if issue_text not in issue_groups:
                    issue_groups[issue_text] = {
                        "count": 0,
                        "first_seen": issue_item["timestamp"],
                        "last_seen": issue_item["timestamp"],
                    }
                issue_groups[issue_text]["count"] += 1
                issue_groups[issue_text]["last_seen"] = issue_item["timestamp"]

            report["issues_summary"] = [
                {
                    "issue": issue,
                    "count": info["count"],
                    "first_seen": info["first_seen"],
                    "last_seen": info["last_seen"],
                }
                for issue, info in issue_groups.items()
            ]

            return report

        except Exception as e:
            return {"error": f"生成报告失败: {str(e)}"}

    def run_monitoring_cycle(self, interval_seconds: int = 60):
        """运行监控循环"""
        print(f"🔍 启动监控循环，间隔 {interval_seconds} 秒")
        print("按 Ctrl+C 停止监控")

        cycle_count = 0

        try:
            while True:
                cycle_count += 1
                print(f"\n📈 监控周期 #{cycle_count} - {datetime.datetime.now().isoformat()}")

                # 创建调度器实例
                scheduler = self.create_scheduler_instance()

                # 检查状态文件
                print("📁 检查状态文件...")
                file_status = self.check_state_file()
                self.log_status("file_check", file_status)

                if file_status["file_exists"]:
                    print(f"   存在: 是，大小: {file_status['file_size']} 字节")
                    print(f"   最后修改: {file_status['last_modified']}")
                    print(f"   JSON有效: {file_status['is_valid_json']}")
                else:
                    print("   存在: 否")

                # 分析状态数据
                print("📊 分析状态数据...")
                state_analysis = self.load_and_analyze_state()
                self.log_status("state_analysis", state_analysis)

                if "error" not in state_analysis:
                    print(f"   总任务数: {state_analysis['total_tasks']}")
                    print(f"   任务状态分布: {state_analysis['task_states']}")

                # 获取实时状态
                print("⚡ 获取实时状态...")
                live_status = self.get_live_status(scheduler)
                self.log_status("live_status", live_status)

                if "error" not in live_status:
                    print(f"   队列中: {live_status['queue_length']}")
                    print(f"   运行中: {live_status['running_tasks']}")
                    print(f"   已完成: {live_status['completed_tasks']}")
                    print(f"   吞吐量: {live_status['throughput']:.2f} 任务/小时")

                # 检查系统健康度
                print("🏥 检查系统健康度...")
                health_status = self.check_system_health(scheduler)
                self.log_status("health", health_status)

                print(f"   总体状态: {health_status['overall_status']}")
                if health_status["issues"]:
                    print(f"   发现问题: {len(health_status['issues'])} 个")
                    for i, issue in enumerate(health_status["issues"], 1):
                        print(f"     {i}. {issue}")

                # 记录指标
                metrics = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "file_status": file_status,
                    "state_analysis": state_analysis,
                    "live_status": live_status,
                    "health_status": health_status,
                }
                self.log_status("metrics", metrics)

                print(f"✅ 监控周期 #{cycle_count} 完成")

                # 等待下一个周期
                if interval_seconds > 0:
                    time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n🛑 监控循环被用户中断")
        except Exception as e:
            print(f"\n❌ 监控循环出错: {str(e)}")
            import traceback

            traceback.print_exc()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MAREF调度器监控系统")
    parser.add_argument(
        "--state-file",
        default="/tmp/hetu_luoshu_state.json",
        help="状态文件路径 (默认: /tmp/hetu_luoshu_state.json)",
    )
    parser.add_argument("--log-dir", help="日志目录路径")
    parser.add_argument("--check", action="store_true", help="单次检查")
    parser.add_argument("--monitor", action="store_true", help="持续监控")
    parser.add_argument("--interval", type=int, default=60, help="监控间隔秒数 (默认: 60)")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--hours", type=int, default=24, help="报告覆盖小时数 (默认: 24)")

    args = parser.parse_args()

    # 创建监控器
    monitor = MarefSchedulerMonitor(args.state_file, args.log_dir)

    if args.check:
        # 单次检查
        print("🔍 执行单次检查")

        # 检查状态文件
        file_status = monitor.check_state_file()
        print("📁 状态文件检查:")
        print(f"   存在: {file_status['file_exists']}")
        if file_status["file_exists"]:
            print(f"   大小: {file_status['file_size']} 字节")
            print(f"   最后修改: {file_status['last_modified']}")
            print(f"   JSON有效: {file_status['is_valid_json']}")

        # 分析状态
        state_analysis = monitor.load_and_analyze_state()
        print("\n📊 状态分析:")
        if "error" in state_analysis:
            print(f"   错误: {state_analysis['error']}")
        else:
            print(f"   总任务数: {state_analysis['total_tasks']}")
            print(f"   任务状态分布: {state_analysis['task_states']}")

        # 创建调度器并检查健康度
        scheduler = monitor.create_scheduler_instance()
        health = monitor.check_system_health(scheduler)
        print("\n🏥 系统健康度:")
        print(f"   总体状态: {health['overall_status']}")
        for check in health["checks"]:
            print(f"   {check['name']}: {check['status']}")

    elif args.monitor:
        # 持续监控
        monitor.run_monitoring_cycle(args.interval)

    elif args.report:
        # 生成报告
        print("📋 生成监控报告")
        report = monitor.generate_report(args.hours)

        if "error" in report:
            print(f"❌ 错误: {report['error']}")
        else:
            print(f"📅 报告周期: {report['report_period_hours']} 小时")
            print(f"📈 总日志条目: {report['total_entries']}")
            print("📊 条目类型分布:")
            for entry_type, count in report["entry_types"].items():
                print(f"   {entry_type}: {count}")

            print("\n📉 健康趋势 (最近10次):")
            for trend in report["health_trend"]:
                print(
                    f"   {trend['timestamp']}: {trend['overall_status']} (问题数: {trend['issue_count']})"
                )

            if report["issues_summary"]:
                print("\n⚠️  问题汇总:")
                for issue_summary in report["issues_summary"]:
                    print(f"   '{issue_summary['issue']}'")
                    print(f"       出现次数: {issue_summary['count']}")
                    print(f"       首次出现: {issue_summary['first_seen']}")
                    print(f"       最后出现: {issue_summary['last_seen']}")
            else:
                print("\n✅ 报告期内未发现问题")

    else:
        # 默认：单次检查
        parser.print_help()


if __name__ == "__main__":
    main()
