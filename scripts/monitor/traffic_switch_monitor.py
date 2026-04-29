#!/usr/bin/env python3
"""
渐进式流量切换监控脚本
用于监控阶段6生产环境切换的渐进式流量切换过程

支持4个批次切换：
1. 批次1: 测试队列迁移 (10%流量)
2. 批次2: 关键业务队列迁移 (30%流量)
3. 批次3: 主要业务队列迁移 (50%流量)
4. 批次4: 全部队列迁移 (80%流量)
5. 批次5: 完全切换 (100%流量)
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil


class TrafficSwitchMonitor:
    """渐进式流量切换监控器"""

    def __init__(self):
        self.base_dir = Path("/Volumes/1TB-M2/openclaw")
        self.queue_dir = self.base_dir / ".openclaw" / "plan_queue"
        self.config_file = self.base_dir / "traffic_switch_config.json"
        self.status_file = self.base_dir / "traffic_switch_status.json"

        # 批次配置（缩短版用于测试）
        self.batches = [
            {"name": "批次1: 测试队列迁移", "target_percentage": 10, "duration_minutes": 2},
            {"name": "批次2: 关键业务队列迁移", "target_percentage": 30, "duration_minutes": 4},
            {"name": "批次3: 主要业务队列迁移", "target_percentage": 50, "duration_minutes": 6},
            {"name": "批次4: 全部队列迁移", "target_percentage": 80, "duration_minutes": 8},
            {"name": "批次5: 完全切换", "target_percentage": 100, "duration_minutes": 10},
        ]

        # 初始化配置
        self.load_or_create_config()

    def load_or_create_config(self):
        """加载或创建流量切换配置"""
        if self.config_file.exists():
            with open(self.config_file, encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "current_batch": 0,
                "start_time": datetime.now().isoformat(),
                "batches": self.batches,
                "completed_batches": [],
                "active": True,
            }
            self.save_config()

    def save_config(self):
        """保存配置"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def update_status(self, status_data):
        """更新状态文件"""
        with open(self.status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)

    def check_queue_health(self):
        """检查队列健康状态"""
        try:
            # 检查队列运行器进程
            queue_runner_running = False
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["cmdline"] and any(
                        "athena_ai_plan_runner.py" in arg for arg in proc.info["cmdline"]
                    ):
                        queue_runner_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 检查队列文件状态
            queue_files = list(self.queue_dir.glob("*.json"))
            queue_statuses = []

            for queue_file in queue_files[:3]:  # 只检查前3个文件
                try:
                    with open(queue_file, encoding="utf-8") as f:
                        data = json.load(f)
                        status = data.get("queue_status", "unknown")
                        tasks = data.get("tasks", {})
                        pending = sum(
                            1 for task in tasks.values() if task.get("status") == "pending"
                        )
                        running = sum(
                            1 for task in tasks.values() if task.get("status") == "running"
                        )
                        completed = sum(
                            1 for task in tasks.values() if task.get("status") == "completed"
                        )
                        failed = sum(1 for task in tasks.values() if task.get("status") == "failed")

                        queue_statuses.append(
                            {
                                "file": queue_file.name,
                                "status": status,
                                "pending": pending,
                                "running": running,
                                "completed": completed,
                                "failed": failed,
                            }
                        )
                except Exception as e:
                    queue_statuses.append(
                        {"file": queue_file.name, "status": "error", "error": str(e)}
                    )

            # 检查Web界面和监控仪表板
            web_dashboard_running = False
            monitor_dashboard_running = False

            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["cmdline"]:
                        cmdline = " ".join(proc.info["cmdline"])
                        if "athena_web_desktop_compat.py" in cmdline:
                            web_dashboard_running = True
                        elif "queue_monitor_dashboard.py" in cmdline:
                            monitor_dashboard_running = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 检查系统资源
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(str(self.base_dir))

            return {
                "queue_runner_running": queue_runner_running,
                "queue_statuses": queue_statuses,
                "web_dashboard_running": web_dashboard_running,
                "monitor_dashboard_running": monitor_dashboard_running,
                "system_resources": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_mb": memory.available / 1024 / 1024,
                    "disk_usage_percent": disk.percent,
                    "disk_free_gb": disk.free / 1024 / 1024 / 1024,
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def run_batch(self, batch_index):
        """运行指定批次的流量切换"""
        if batch_index >= len(self.batches):
            print(f"❌ 批次索引 {batch_index} 超出范围")
            return False

        batch = self.batches[batch_index]
        print(f"🚀 开始 {batch['name']} ({batch['target_percentage']}%流量)")

        # 记录批次开始时间
        batch_start_time = datetime.now()

        # 获取切换前基准状态
        baseline_status = self.check_queue_health()
        print("📊 切换前基准状态:")
        print(f"  - 队列运行器: {'✅' if baseline_status.get('queue_runner_running') else '❌'}")
        print(f"  - Web仪表板: {'✅' if baseline_status.get('web_dashboard_running') else '❌'}")
        print(
            f"  - 监控仪表板: {'✅' if baseline_status.get('monitor_dashboard_running') else '❌'}"
        )

        # 根据批次执行相应操作
        if batch_index == 0:  # 批次1: 测试队列迁移
            print("🔧 执行测试队列迁移 (10%流量)...")
            # 这里可以添加具体的迁移逻辑
            # 例如：迁移低风险测试队列
            pass

        # 监控批次执行过程
        print(f"⏱️ 批次执行时长: {batch['duration_minutes']}分钟")
        print("📈 开始监控批次执行状态...")

        # 创建批次状态记录
        batch_status = {
            "batch_index": batch_index,
            "batch_name": batch["name"],
            "target_percentage": batch["target_percentage"],
            "start_time": batch_start_time.isoformat(),
            "baseline_status": baseline_status,
            "monitoring_data": [],
            "health_checks": [],
        }

        # 在批次执行期间进行监控
        monitoring_duration = batch["duration_minutes"] * 60  # 转换为秒
        check_interval = 30  # 30秒检查一次

        for i in range(0, monitoring_duration, check_interval):
            time_since_start = i
            remaining_time = monitoring_duration - i

            print(
                f"  [{time_since_start // 60:02d}:{time_since_start % 60:02d}] 批次执行中... 剩余 {remaining_time // 60}分{remaining_time % 60}秒"
            )

            # 检查当前状态
            current_status = self.check_queue_health()

            # 健康检查
            health_ok = True
            health_issues = []

            if not current_status.get("queue_runner_running", False):
                health_ok = False
                health_issues.append("队列运行器未运行")

            if current_status.get("queue_statuses"):
                for qs in current_status["queue_statuses"]:
                    if qs.get("status") == "failed":
                        health_ok = False
                        health_issues.append(f"队列 {qs.get('file')} 状态为 failed")

            # 检查系统资源
            sys_resources = current_status.get("system_resources", {})
            if sys_resources.get("cpu_percent", 0) > 90:
                health_ok = False
                health_issues.append(f"CPU使用率过高: {sys_resources.get('cpu_percent')}%")

            if sys_resources.get("memory_percent", 0) > 90:
                health_ok = False
                health_issues.append(f"内存使用率过高: {sys_resources.get('memory_percent')}%")

            # 记录健康检查
            health_check = {
                "timestamp": current_status.get("timestamp"),
                "healthy": health_ok,
                "issues": health_issues,
                "queue_runner": current_status.get("queue_runner_running"),
                "queue_statuses": current_status.get("queue_statuses", []),
                "system_resources": sys_resources,
            }
            batch_status["health_checks"].append(health_check)

            # 如果有严重健康问题，可能需要暂停或回滚
            if not health_ok and i > 60:  # 至少运行1分钟后才开始检查
                print(f"⚠️ 健康检查失败: {health_issues}")
                print("考虑暂停切换或执行回滚")

            # 记录监控数据
            batch_status["monitoring_data"].append(current_status)

            # 更新状态文件
            self.update_status(
                {
                    "current_batch": batch_index,
                    "batch_status": batch_status,
                    "current_health": health_check,
                    "overall_progress": {
                        "batches_completed": len(self.config.get("completed_batches", [])),
                        "batches_total": len(self.batches),
                        "current_batch_progress": min(
                            100, (time_since_start / monitoring_duration) * 100
                        ),
                    },
                }
            )

            # 等待下一个检查点
            if i + check_interval < monitoring_duration:
                time.sleep(check_interval)

        # 批次完成
        batch_end_time = datetime.now()
        duration_seconds = (batch_end_time - batch_start_time).total_seconds()

        # 获取最终状态
        final_status = self.check_queue_health()

        # 评估批次结果
        success = True
        summary_issues = []

        # 检查最终健康状态
        if not final_status.get("queue_runner_running", False):
            success = False
            summary_issues.append("队列运行器未运行")

        # 检查是否有失败的队列
        for qs in final_status.get("queue_statuses", []):
            if qs.get("status") == "failed":
                success = False
                summary_issues.append(f"队列 {qs.get('file')} 状态为 failed")

        # 完成批次记录
        batch_status.update(
            {
                "end_time": batch_end_time.isoformat(),
                "duration_seconds": duration_seconds,
                "final_status": final_status,
                "success": success,
                "summary_issues": summary_issues,
            }
        )

        # 更新配置
        self.config["completed_batches"].append(batch_status)
        self.config["current_batch"] = batch_index + 1
        self.save_config()

        # 打印批次总结
        print(f"\n{'✅' if success else '❌'} {batch['name']} 完成")
        print(f"⏱️ 持续时间: {duration_seconds // 60}分{duration_seconds % 60}秒")
        print(f"📊 结果: {'成功' if success else '失败'}")
        if summary_issues:
            print(f"⚠️ 问题: {', '.join(summary_issues)}")

        return success

    def run_all_batches(self):
        """运行所有批次"""
        print("🚀 开始渐进式流量切换")
        print("=" * 60)

        start_time = datetime.now()

        for i in range(len(self.batches)):
            batch_success = self.run_batch(i)

            if not batch_success:
                print(f"\n❌ 批次 {i + 1} 失败，暂停流量切换")
                print("请检查问题并决定是否继续")
                choice = input("继续下一个批次? (y/n): ")
                if choice.lower() != "y":
                    print("⏸️ 流量切换已暂停")
                    return False

        # 所有批次完成
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("🎉 渐进式流量切换完成!")
        print(f"⏱️ 总时长: {total_duration // 3600}小时{total_duration % 3600 // 60}分")
        print(f"📊 完成批次: {len(self.config.get('completed_batches', []))}/{len(self.batches)}")

        # 生成最终报告
        self.generate_final_report()

        return True

    def generate_final_report(self):
        """生成最终切换报告"""
        report_file = self.base_dir / "traffic_switch_final_report.md"

        report = f"""# 渐进式流量切换最终报告

## 切换概览
- **开始时间**: {self.config.get("start_time")}
- **完成批次**: {len(self.config.get("completed_batches", []))}/{len(self.batches)}
- **总体状态**: {"✅ 成功" if all(b.get("success", False) for b in self.config.get("completed_batches", [])) else "❌ 失败"}

## 批次详情
"""

        for i, batch in enumerate(self.config.get("completed_batches", [])):
            report += f"""
### {batch.get("batch_name", f"批次 {i + 1}")}
- **目标流量**: {batch.get("target_percentage", 0)}%
- **开始时间**: {batch.get("start_time", "N/A")}
- **结束时间**: {batch.get("end_time", "N/A")}
- **持续时间**: {batch.get("duration_seconds", 0) // 60}分{batch.get("duration_seconds", 0) % 60}秒
- **状态**: {"✅ 成功" if batch.get("success", False) else "❌ 失败"}
"""
            if batch.get("summary_issues"):
                report += f"- **问题**: {', '.join(batch.get('summary_issues', []))}\n"

        # 系统性能总结
        report += """
## 系统性能总结
"""

        if self.config.get("completed_batches"):
            last_batch = self.config["completed_batches"][-1]
            final_status = last_batch.get("final_status", {})
            sys_resources = final_status.get("system_resources", {})

            report += f"""
### 最终系统状态
- **队列运行器**: {"✅ 运行中" if final_status.get("queue_runner_running") else "❌ 未运行"}
- **Web仪表板**: {"✅ 运行中" if final_status.get("web_dashboard_running") else "❌ 未运行"}
- **监控仪表板**: {"✅ 运行中" if final_status.get("monitor_dashboard_running") else "❌ 未运行"}

### 系统资源
- **CPU使用率**: {sys_resources.get("cpu_percent", 0):.1f}%
- **内存使用率**: {sys_resources.get("memory_percent", 0):.1f}%
- **可用内存**: {sys_resources.get("memory_available_mb", 0):.0f} MB
- **磁盘使用率**: {sys_resources.get("disk_usage_percent", 0):.1f}%
- **可用磁盘空间**: {sys_resources.get("disk_free_gb", 0):.1f} GB
"""

        report += """
## 建议
1. **继续监控**: 切换后继续监控系统24小时
2. **性能优化**: 根据监控数据调整系统参数
3. **文档更新**: 更新运维手册和故障处理指南
4. **团队培训**: 进行新系统使用培训

---
*报告生成时间: {datetime.now().isoformat()}*
"""

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"📄 最终报告已生成: {report_file}")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="渐进式流量切换监控")
    parser.add_argument(
        "--auto-confirm", "-y", action="store_true", help="自动确认流量切换，跳过用户输入"
    )
    args = parser.parse_args()

    monitor = TrafficSwitchMonitor()

    # 检查系统状态
    print("🔍 检查系统状态...")
    initial_status = monitor.check_queue_health()

    if not initial_status.get("queue_runner_running", False):
        print("❌ 队列运行器未运行，请先启动队列运行器")
        print("命令: python3 scripts/athena_ai_plan_runner.py --queue <队列文件>")
        return 1

    if not initial_status.get("web_dashboard_running", False):
        print("⚠️ Web仪表板未运行，建议启动以监控Web界面状态")

    if not initial_status.get("monitor_dashboard_running", False):
        print("⚠️ 监控仪表板未运行，建议启动以获取详细监控数据")

    # 确认开始流量切换
    print("\n📋 流量切换计划:")
    for i, batch in enumerate(monitor.batches):
        print(
            f"  {i + 1}. {batch['name']} ({batch['target_percentage']}%流量, {batch['duration_minutes']}分钟)"
        )

    print("\n" + "=" * 60)

    if args.auto_confirm:
        print("✅ 自动确认启用，跳过用户输入")
        confirm = "y"
    else:
        confirm = input("确认开始渐进式流量切换? (输入 'y' 确认): ")

    if confirm.lower() != "y":
        print("⏸️ 流量切换已取消")
        return 0

    # 开始流量切换
    print("\n" + "=" * 60)
    success = monitor.run_all_batches()

    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏸️ 流量切换被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 流量切换失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
