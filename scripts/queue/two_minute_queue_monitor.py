#!/usr/bin/env python3
"""
2分钟间隔队列监控检查器
每2分钟检查所有任务队列状态，自动拉起pending任务，记录问题并生成总结报告
"""

import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "two_minute_monitor.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class TwoMinuteQueueMonitor:
    """2分钟间隔队列监控器"""

    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.queue_dir = self.root_dir / ".openclaw" / "plan_queue"
        self.queues_config = self.root_dir / ".athena-auto-queue.json"

        # 日志文件
        self.check_log = self.root_dir / "logs" / "two_minute_checks.jsonl"
        self.problem_log = self.root_dir / "logs" / "queue_problems.jsonl"
        self.summary_report = self.root_dir / "logs" / "queue_summary_report.md"

        # 创建日志目录
        logs_dir = self.root_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # 监控状态
        self.monitoring_state = {
            "start_time": datetime.now().isoformat(),
            "total_checks": 0,
            "tasks_launched": 0,
            "problems_recorded": 0,
            "queues_completed": 0,
            "check_interval_seconds": 120,  # 2分钟
        }

        # Web API配置
        self.web_base_url = "http://127.0.0.1:8080"
        self.token_file = self.root_dir / ".openclaw" / "athena_web_desktop.token"
        self.auth_token = self._load_auth_token()

        # 队列完成跟踪
        self.completed_queues = set()
        self.queue_completion_history = {}

    def _load_auth_token(self) -> str:
        """加载Web API认证token"""
        if self.token_file.exists():
            try:
                token = self.token_file.read_text().strip()
                logger.info(f"加载认证token: {token[:10]}...")
                return token
            except Exception as e:
                logger.error(f"读取token文件失败: {e}")

        # 尝试从默认位置获取
        default_token = "FxwdCOtBnl_e0wQJQ2107OUqWkPOBa67"
        logger.info(f"使用默认token: {default_token[:10]}...")
        return default_token

    def get_queue_status(self) -> dict[str, Any]:
        """获取所有队列状态"""
        headers = {"X-OpenClaw-Token": self.auth_token}

        try:
            response = requests.get(
                f"{self.web_base_url}/api/athena/queues", headers=headers, timeout=5
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Web API返回错误状态码: {response.status_code}")
                return {"error": f"API返回{response.status_code}", "routes": []}

        except requests.RequestException as e:
            logger.error(f"Web API请求失败: {e}")
            return {"error": str(e), "routes": []}

    def check_individual_queue_files(self) -> dict[str, Any]:
        """直接检查队列文件状态"""
        queue_status = {"timestamp": datetime.now().isoformat(), "queues": {}}

        if self.queue_dir.exists():
            queue_files = list(self.queue_dir.glob("*.json"))

            for queue_file in queue_files:
                try:
                    with open(queue_file, encoding="utf-8") as f:
                        queue_data = json.load(f)

                    queue_name = queue_file.stem
                    queue_status_val = queue_data.get("queue_status", "unknown")
                    counts = queue_data.get("counts", {})

                    queue_status["queues"][queue_name] = {
                        "queue_status": queue_status_val,
                        "pending": counts.get("pending", 0),
                        "running": counts.get("running", 0),
                        "completed": counts.get("completed", 0),
                        "failed": counts.get("failed", 0),
                        "manual_hold": counts.get("manual_hold", 0),
                        "total_tasks": len(queue_data.get("items", {})),
                        "current_item_id": queue_data.get("current_item_id", ""),
                        "updated_at": queue_data.get("updated_at", ""),
                    }

                except Exception as e:
                    logger.error(f"读取队列文件失败 {queue_file}: {e}")
                    queue_status["queues"][queue_file.stem] = {"error": str(e)}

        return queue_status

    def auto_launch_pending_tasks(self, web_queue_data: dict[str, Any]) -> list[dict[str, Any]]:
        """自动拉起pending状态的任务"""
        launched_tasks = []

        if "routes" not in web_queue_data:
            logger.warning("Web API返回数据中没有routes字段")
            return launched_tasks

        headers = {"X-OpenClaw-Token": self.auth_token, "Content-Type": "application/json"}

        for route in web_queue_data["routes"]:
            route_id = route.get("route_id")
            queue_id = route.get("queue_id")
            queue_status = route.get("queue_status", "")

            # 检查队列状态，只在队列为running或failed且有pending任务时尝试拉起
            if queue_status not in ["running", "failed"]:
                continue

            items = route.get("items", [])
            pending_items = [item for item in items if item.get("status") == "pending"]

            if not pending_items:
                continue

            # 尝试拉起前3个pending任务（避免一次性拉起太多）
            for item in pending_items[:3]:
                task_id = item.get("id")

                if not task_id or not route_id:
                    continue

                # 尝试手动拉起API
                launch_url = (
                    f"{self.web_base_url}/api/athena/queues/items/{route_id}/{task_id}/launch"
                )

                try:
                    logger.info(f"尝试拉起任务: 队列={queue_id}, 路由={route_id}, 任务={task_id}")
                    response = requests.post(launch_url, headers=headers, timeout=10)

                    if response.status_code == 200:
                        logger.info(f"✅ 成功拉起任务 {task_id}")
                        launched_tasks.append(
                            {
                                "task_id": task_id,
                                "queue_id": queue_id,
                                "route_id": route_id,
                                "status": "launched",
                                "response": response.json() if response.text else {},
                            }
                        )
                        self.monitoring_state["tasks_launched"] += 1
                    else:
                        logger.warning(
                            f"❌ 拉起任务失败 {task_id}: {response.status_code} - {response.text}"
                        )
                        launched_tasks.append(
                            {
                                "task_id": task_id,
                                "queue_id": queue_id,
                                "route_id": route_id,
                                "status": "failed",
                                "error": f"HTTP {response.status_code}: {response.text[:100]}",
                            }
                        )

                except requests.RequestException as e:
                    logger.error(f"🚫 拉起任务请求异常 {task_id}: {e}")
                    launched_tasks.append(
                        {
                            "task_id": task_id,
                            "queue_id": queue_id,
                            "route_id": route_id,
                            "status": "error",
                            "error": str(e),
                        }
                    )

        return launched_tasks

    def record_problems(
        self,
        web_queue_data: dict[str, Any],
        file_queue_status: dict[str, Any],
        launched_tasks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """记录执行过程中的问题和错误"""
        problems = []

        # 1. 检查Web API错误
        if "error" in web_queue_data:
            problems.append(
                {
                    "type": "web_api_error",
                    "timestamp": datetime.now().isoformat(),
                    "error": web_queue_data["error"],
                    "severity": "high",
                    "action": "检查Web服务器状态",
                }
            )

        # 2. 检查队列状态不一致
        web_queues = {}
        if "routes" in web_queue_data:
            for route in web_queue_data["routes"]:
                web_queues[route.get("queue_id")] = {
                    "status": route.get("queue_status"),
                    "pending": sum(
                        1 for item in route.get("items", []) if item.get("status") == "pending"
                    ),
                    "running": sum(
                        1 for item in route.get("items", []) if item.get("status") == "running"
                    ),
                }

        file_queues = file_queue_status.get("queues", {})

        for queue_id, web_info in web_queues.items():
            # 查找对应的文件队列（通过queue_id匹配）
            file_info = None
            for file_queue_name, file_queue_data in file_queues.items():
                if queue_id in file_queue_name or file_queue_name in queue_id:
                    file_info = file_queue_data
                    break

            if file_info:
                # 检查pending计数差异
                web_pending = web_info.get("pending", 0)
                file_pending = file_info.get("pending", 0)

                if abs(web_pending - file_pending) > 5:  # 允许5个任务的差异
                    problems.append(
                        {
                            "type": "queue_count_mismatch",
                            "timestamp": datetime.now().isoformat(),
                            "queue_id": queue_id,
                            "web_pending": web_pending,
                            "file_pending": file_pending,
                            "difference": abs(web_pending - file_pending),
                            "severity": "medium",
                            "action": "同步队列状态",
                        }
                    )

        # 3. 记录拉起任务的结果
        failed_launches = [task for task in launched_tasks if task["status"] in ["failed", "error"]]
        if failed_launches:
            problems.append(
                {
                    "type": "task_launch_failures",
                    "timestamp": datetime.now().isoformat(),
                    "failed_count": len(failed_launches),
                    "tasks": failed_launches[:5],  # 只记录前5个
                    "severity": "medium",
                    "action": "检查任务配置和API权限",
                }
            )

        # 4. 检查队列长时间不更新
        for queue_name, queue_data in file_queues.items():
            updated_at_str = queue_data.get("updated_at", "")
            if updated_at_str:
                try:
                    last_updated = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    if last_updated.tzinfo is not None:
                        last_updated_utc = last_updated.astimezone(UTC)
                    else:
                        last_updated_utc = last_updated.replace(tzinfo=UTC)

                    now_utc = datetime.now(UTC)
                    age_minutes = (now_utc - last_updated_utc).total_seconds() / 60

                    # 优化：empty状态队列不触发陈旧告警，因为这是正常完成状态
                    queue_status = queue_data.get("queue_status", "")
                    if queue_status == "empty":
                        continue  # 跳过empty队列的陈旧检查

                    if age_minutes > 30:  # 30分钟未更新
                        problems.append(
                            {
                                "type": "stale_queue",
                                "timestamp": datetime.now().isoformat(),
                                "queue": queue_name,
                                "age_minutes": age_minutes,
                                "queue_status": queue_status,
                                "severity": "medium",
                                "action": "检查队列运行器进程",
                            }
                        )
                except ValueError:
                    pass

        # 保存问题到日志文件
        if problems:
            try:
                with open(self.problem_log, "a", encoding="utf-8") as f:
                    for problem in problems:
                        f.write(json.dumps(problem, ensure_ascii=False) + "\n")

                self.monitoring_state["problems_recorded"] += len(problems)
                logger.info(f"记录 {len(problems)} 个问题到日志")

            except Exception as e:
                logger.error(f"保存问题日志失败: {e}")

        return problems

    def check_queue_completion(self, file_queue_status: dict[str, Any]) -> list[str]:
        """检查队列是否完成（所有任务都是completed状态）"""
        newly_completed = []

        for queue_name, queue_data in file_queue_status.get("queues", {}).items():
            # 跳过已标记为完成的队列
            if queue_name in self.completed_queues:
                continue

            pending = queue_data.get("pending", 0)
            running = queue_data.get("running", 0)
            failed = queue_data.get("failed", 0)
            manual_hold = queue_data.get("manual_hold", 0)
            total_tasks = queue_data.get("total_tasks", 0)
            completed = queue_data.get("completed", 0)

            # 队列完成条件：没有pending/running/failed/manual_hold任务，且completed > 0
            if pending == 0 and running == 0 and failed == 0 and manual_hold == 0 and completed > 0:
                self.completed_queues.add(queue_name)
                newly_completed.append(queue_name)

                # 记录完成历史
                self.queue_completion_history[queue_name] = {
                    "completed_at": datetime.now().isoformat(),
                    "total_tasks": total_tasks,
                    "completed_tasks": completed,
                    "completion_rate": (completed / total_tasks * 100) if total_tasks > 0 else 100,
                }

                logger.info(f"🎉 队列完成: {queue_name} ({completed}/{total_tasks} 任务)")

        if newly_completed:
            self.monitoring_state["queues_completed"] += len(newly_completed)

        return newly_completed

    def generate_summary_report(self) -> str:
        """生成队列运行总结报告"""
        report_lines = [
            "# 任务队列运行总结报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"监控开始时间: {self.monitoring_state['start_time']}",
            "",
            "## 监控统计",
            f"- 总检查次数: {self.monitoring_state['total_checks']}",
            f"- 自动拉起任务数: {self.monitoring_state['tasks_launched']}",
            f"- 记录问题数: {self.monitoring_state['problems_recorded']}",
            f"- 已完成队列数: {self.monitoring_state['queues_completed']}",
            "",
            "## 队列完成情况",
        ]

        if self.queue_completion_history:
            for queue_name, history in self.queue_completion_history.items():
                report_lines.append(f"### {queue_name}")
                report_lines.append(f"- 完成时间: {history['completed_at']}")
                report_lines.append(f"- 总任务数: {history['total_tasks']}")
                report_lines.append(f"- 完成任务数: {history['completed_tasks']}")
                report_lines.append(f"- 完成率: {history['completion_rate']:.1f}%")
                report_lines.append("")
        else:
            report_lines.append("暂无已完成队列")
            report_lines.append("")

        # 生成规划调优建议
        report_lines.append("## 系统规划调优建议")

        # 基于监控数据生成建议
        if self.monitoring_state["problems_recorded"] > 10:
            report_lines.append("### 🔴 高优先级优化")
            report_lines.append(
                "1. **队列稳定性优化**: 系统存在较多问题，建议优先解决队列状态同步和任务拉起失败问题"
            )
            report_lines.append("2. **监控告警增强**: 建立实时告警机制，及时发现和处理队列异常")
            report_lines.append("3. **任务重试策略**: 为失败任务实现智能重试机制，提高系统容错性")
        elif self.monitoring_state["problems_recorded"] > 0:
            report_lines.append("### 🟡 中优先级优化")
            report_lines.append("1. **队列性能优化**: 优化任务调度算法，减少pending任务积压")
            report_lines.append("2. **资源监控**: 建立系统资源监控，确保队列运行器有足够资源")
            report_lines.append("3. **日志分析**: 定期分析问题日志，识别常见错误模式")
        else:
            report_lines.append("### 🟢 低优先级优化")
            report_lines.append("1. **系统扩展性**: 考虑支持多队列并发执行")
            report_lines.append("2. **用户体验**: 优化Web界面队列状态展示")
            report_lines.append("3. **自动化测试**: 增加队列系统的自动化测试覆盖")

        report_lines.append("")
        report_lines.append("## 详细建议实施计划")
        report_lines.append("### 短期（1-2周）")
        report_lines.append("1. 修复当前发现的问题")
        report_lines.append("2. 优化任务拉起成功率")
        report_lines.append("3. 建立基础监控告警")

        report_lines.append("")
        report_lines.append("### 中期（3-4周）")
        report_lines.append("1. 实现智能任务调度")
        report_lines.append("2. 建立性能基准测试")
        report_lines.append("3. 优化系统资源使用")

        report_lines.append("")
        report_lines.append("### 长期（1-2月）")
        report_lines.append("1. 实现分布式队列支持")
        report_lines.append("2. 建立机器学习驱动的优化")
        report_lines.append("3. 实现完整的DevOps流水线")

        report_content = "\n".join(report_lines)

        # 保存报告到文件
        try:
            with open(self.summary_report, "w", encoding="utf-8") as f:
                f.write(report_content)
            logger.info(f"总结报告已保存: {self.summary_report}")
        except Exception as e:
            logger.error(f"保存总结报告失败: {e}")

        return report_content

    def log_check_data(
        self,
        web_queue_data: dict[str, Any],
        file_queue_status: dict[str, Any],
        launched_tasks: list[dict[str, Any]],
        problems: list[dict[str, Any]],
        newly_completed: list[str],
    ):
        """记录检查数据"""
        check_entry = {
            "timestamp": datetime.now().isoformat(),
            "check_number": self.monitoring_state["total_checks"],
            "web_queues_count": len(web_queue_data.get("routes", [])),
            "file_queues_count": len(file_queue_status.get("queues", {})),
            "launched_tasks": len(launched_tasks),
            "problems_count": len(problems),
            "newly_completed_queues": newly_completed,
            "total_completed_queues": len(self.completed_queues),
            "monitoring_state": self.monitoring_state.copy(),
        }

        try:
            with open(self.check_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(check_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"记录检查数据失败: {e}")

    def run_check_cycle(self) -> dict[str, Any]:
        """运行一次完整的检查周期"""
        self.monitoring_state["total_checks"] += 1
        check_number = self.monitoring_state["total_checks"]

        logger.info(
            f"🔍 开始第 {check_number} 次检查 (间隔: {self.monitoring_state['check_interval_seconds']}秒)"
        )

        # 1. 获取队列状态
        logger.info("获取Web API队列状态...")
        web_queue_data = self.get_queue_status()

        logger.info("检查队列文件状态...")
        file_queue_status = self.check_individual_queue_files()

        # 2. 自动拉起pending任务
        logger.info("自动拉起pending任务...")
        launched_tasks = self.auto_launch_pending_tasks(web_queue_data)

        # 3. 记录问题和错误
        logger.info("记录执行问题...")
        problems = self.record_problems(web_queue_data, file_queue_status, launched_tasks)

        # 4. 检查队列完成情况
        logger.info("检查队列完成情况...")
        newly_completed = self.check_queue_completion(file_queue_status)

        # 5. 记录检查数据
        logger.info("记录检查数据...")
        self.log_check_data(
            web_queue_data, file_queue_status, launched_tasks, problems, newly_completed
        )

        # 显示本次检查摘要
        logger.info("📊 检查摘要:")
        logger.info(f"  • Web队列数: {len(web_queue_data.get('routes', []))}")
        logger.info(f"  • 文件队列数: {len(file_queue_status.get('queues', {}))}")
        logger.info(f"  • 拉起任务数: {len(launched_tasks)}")
        logger.info(f"  • 发现问题数: {len(problems)}")
        logger.info(
            f"  • 新完成队列: {len(newly_completed)} ({', '.join(newly_completed) if newly_completed else '无'})"
        )

        return {
            "web_queue_data": web_queue_data,
            "file_queue_status": file_queue_status,
            "launched_tasks": launched_tasks,
            "problems": problems,
            "newly_completed": newly_completed,
        }

    def run_continuous_monitoring(self, max_checks: int = None):
        """运行持续监控"""
        logger.info("🚀 启动2分钟间隔队列监控检查器")
        logger.info(f"开始时间: {self.monitoring_state['start_time']}")
        logger.info(f"检查间隔: {self.monitoring_state['check_interval_seconds']}秒")
        logger.info(f"最大检查次数: {max_checks or '无限制'}")
        logger.info("=" * 60)

        check_count = 0

        try:
            while True:
                if max_checks and check_count >= max_checks:
                    logger.info(f"达到最大检查次数 {max_checks}，停止监控")
                    break

                # 运行检查周期
                self.run_check_cycle()
                check_count += 1

                # 检查是否所有队列都已完成
                total_queues = len(self.check_individual_queue_files().get("queues", {}))
                if len(self.completed_queues) >= total_queues and total_queues > 0:
                    logger.info(f"🎉 所有 {total_queues} 个队列已完成!")
                    logger.info("生成最终总结报告...")
                    report = self.generate_summary_report()
                    logger.info(f"总结报告已生成: {self.summary_report}")
                    print("\n" + "=" * 60)
                    print("最终总结报告摘要:")
                    print("=" * 60)
                    for line in report.split("\n")[:20]:  # 只显示前20行
                        print(line)
                    print("=" * 60)
                    print(f"完整报告: {self.summary_report}")
                    break

                # 等待下次检查
                logger.info(
                    f"⏳ 等待 {self.monitoring_state['check_interval_seconds']} 秒后下次检查..."
                )
                time.sleep(self.monitoring_state["check_interval_seconds"])

        except KeyboardInterrupt:
            logger.info("监控被用户中断")
        except Exception as e:
            logger.error(f"监控运行失败: {e}")
        finally:
            # 生成最终报告
            logger.info("生成监控总结报告...")
            report = self.generate_summary_report()
            logger.info(f"监控总结报告已保存: {self.summary_report}")

            logger.info("=" * 60)
            logger.info("监控统计:")
            logger.info(f"  总检查次数: {self.monitoring_state['total_checks']}")
            logger.info(f"  自动拉起任务数: {self.monitoring_state['tasks_launched']}")
            logger.info(f"  记录问题数: {self.monitoring_state['problems_recorded']}")
            logger.info(f"  已完成队列数: {self.monitoring_state['queues_completed']}")
            logger.info("=" * 60)

    def run_once(self):
        """运行单次检查"""
        logger.info("运行单次队列检查...")
        result = self.run_check_cycle()

        # 显示简要报告
        print("\n" + "=" * 60)
        print("单次检查报告")
        print("=" * 60)
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"检查次数: {self.monitoring_state['total_checks']}")
        print()

        print("队列状态:")
        for queue_name, queue_data in result["file_queue_status"].get("queues", {}).items():
            print(f"  {queue_name}:")
            print(f"    状态: {queue_data.get('queue_status', 'unknown')}")
            print(f"    任务: {queue_data.get('total_tasks', 0)} 总数")
            print(
                f"          pending: {queue_data.get('pending', 0)}, running: {queue_data.get('running', 0)}"
            )
            print(
                f"          completed: {queue_data.get('completed', 0)}, failed: {queue_data.get('failed', 0)}"
            )

        print()
        print(f"自动拉起任务: {len(result['launched_tasks'])} 个")
        print(f"发现问题: {len(result['problems'])} 个")

        if result["newly_completed"]:
            print(f"新完成队列: {', '.join(result['newly_completed'])}")

        print("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="2分钟间隔队列监控检查器")
    parser.add_argument("--once", "-o", action="store_true", help="单次检查模式")
    parser.add_argument("--max-checks", "-m", type=int, default=None, help="最大检查次数")
    parser.add_argument("--interval", "-i", type=int, default=120, help="检查间隔秒数（默认120秒）")

    args = parser.parse_args()

    # 创建监控器
    monitor = TwoMinuteQueueMonitor()

    # 更新检查间隔
    if args.interval != 120:
        monitor.monitoring_state["check_interval_seconds"] = args.interval
        logger.info(f"设置检查间隔为 {args.interval} 秒")

    # 运行模式
    if args.once:
        monitor.run_once()
    else:
        monitor.run_continuous_monitoring(max_checks=args.max_checks)


if __name__ == "__main__":
    main()
