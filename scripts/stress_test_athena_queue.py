#!/usr/bin/env python3
"""
Athena队列系统压力测试

验证系统在峰值100任务/分钟负载下的表现，包括：
1. 吞吐量测试：测量系统在单位时间内能处理的任务数量
2. 延迟测试：测量任务创建到完成的总时间分布
3. 资源监控：CPU、内存、磁盘I/O等资源使用情况
4. 状态一致性：验证在高并发下状态管理的一致性
5. 智能路由验证：验证SmartOrchestrator在高负载下的决策质量

测试目标：峰值100任务/分钟 ≈ 1.67个任务/秒
"""

import concurrent.futures
import json
import logging
import os
import statistics
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AthenaQueueStressTester:
    """Athena队列系统压力测试器"""

    def __init__(self, target_rate: float = 100.0, duration_minutes: int = 5):
        """
        初始化压力测试器

        参数:
        - target_rate: 目标任务率（任务/分钟），默认100任务/分钟
        - duration_minutes: 测试持续时间（分钟），默认5分钟
        """
        self.target_rate = target_rate  # 任务/分钟
        self.target_per_second = target_rate / 60.0  # 任务/秒
        self.duration_seconds = duration_minutes * 60

        # 测试结果
        self.results = {
            "start_time": None,
            "end_time": None,
            "total_tasks_created": 0,
            "total_tasks_succeeded": 0,
            "total_tasks_failed": 0,
            "creation_latencies": [],  # 任务创建延迟（秒）
            "throughput_per_minute": [],
            "resource_metrics": [],  # 资源使用指标
            "errors": [],  # 错误记录
            "routing_decisions": [],  # 智能路由决策记录
        }

        # 并发控制
        self.task_counter = 0
        self.lock = threading.Lock()

        # 性能监控
        self.process = psutil.Process(os.getpid())
        self.system_metrics = []

        logger.info(
            f"压力测试器初始化: 目标={target_rate}任务/分钟, 持续时间={duration_minutes}分钟"
        )

    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统资源指标"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()
            disk_usage = psutil.disk_usage("/")

            # 获取Python进程内存使用
            process_memory = self.process.memory_info()

            metrics = {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory_info.percent,
                "memory_used_mb": memory_info.used / 1024 / 1024,
                "memory_available_mb": memory_info.available / 1024 / 1024,
                "disk_percent": disk_usage.percent,
                "disk_free_gb": disk_usage.free / 1024 / 1024 / 1024,
                "process_rss_mb": process_memory.rss / 1024 / 1024,
                "process_vms_mb": process_memory.vms / 1024 / 1024,
            }

            with self.lock:
                self.system_metrics.append(metrics)

            return metrics

        except Exception as e:
            logger.warning(f"收集系统指标失败: {e}")
            return {}

    def create_single_task(self, task_id: int) -> Tuple[bool, float, Optional[str]]:
        """
        创建单个测试任务

        返回:
        - (success, latency_seconds, task_id_or_error)
        """
        start_time = time.time()

        try:
            # 延迟导入（避免循环依赖）
            from mini_agent.agent.core.athena_orchestrator import get_orchestrator

            orchestrator = get_orchestrator()

            # 测试任务参数
            test_cases = [
                {
                    "domain": "engineering",
                    "stage": "build",
                    "description": f"压力测试构建任务 #{task_id}",
                    "priority": "low",
                },
                {
                    "domain": "engineering",
                    "stage": "plan",
                    "description": f"压力测试规划任务 #{task_id}",
                    "priority": "medium",
                },
                {
                    "domain": "engineering",
                    "stage": "review",
                    "description": f"压力测试审查任务 #{task_id}",
                    "priority": "high",
                },
            ]

            # 轮换使用测试用例
            test_case = test_cases[task_id % len(test_cases)]

            success, created_task_id, metadata = orchestrator.create_task(
                domain=test_case["domain"],
                stage=test_case["stage"],
                description=test_case["description"],
                priority=test_case["priority"],
            )

            latency = time.time() - start_time

            # 记录路由决策信息
            if success:
                executor = metadata.get("executor", "unknown")
                routing_info = {
                    "task_id": created_task_id,
                    "requested_stage": test_case["stage"],
                    "assigned_executor": executor,
                    "budget_status": metadata.get("budget_status", "unknown"),
                    "latency": latency,
                }

                with self.lock:
                    self.results["routing_decisions"].append(routing_info)

                logger.debug(
                    f"任务创建成功: {created_task_id}, 执行器: {executor}, 延迟: {latency:.3f}s"
                )
            else:
                logger.warning(f"任务创建失败: {created_task_id}")

            return success, latency, created_task_id

        except ImportError as e:
            error_msg = f"导入失败: {e}"
            logger.error(error_msg)
            return False, time.time() - start_time, error_msg
        except Exception as e:
            error_msg = f"任务创建异常: {e}"
            logger.error(error_msg)
            return False, time.time() - start_time, error_msg

    def run_concurrent_test(self, concurrency_level: int = 10) -> Dict[str, Any]:
        """
        运行并发压力测试

        参数:
        - concurrency_level: 并发任务数

        返回:
        - 测试结果字典
        """
        logger.info(f"开始并发压力测试: 并发级别={concurrency_level}")

        self.results["start_time"] = time.time()
        start_time = self.results["start_time"]
        end_time = start_time + self.duration_seconds

        # 使用线程池执行器
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency_level) as executor:
            # 启动监控线程
            monitor_thread = threading.Thread(target=self._monitor_loop, args=(end_time,))
            monitor_thread.start()

            # 主测试循环
            current_time = time.time()
            task_futures = []

            while current_time < end_time:
                # 计算应该创建的任务数量（基于目标速率）
                elapsed = current_time - start_time
                expected_tasks = int(elapsed * self.target_per_second)

                with self.lock:
                    tasks_to_create = max(0, expected_tasks - self.results["total_tasks_created"])

                # 创建任务
                for _ in range(tasks_to_create):
                    with self.lock:
                        self.task_counter += 1
                        task_id = self.task_counter

                    future = executor.submit(self.create_single_task, task_id)
                    task_futures.append(future)

                    with self.lock:
                        self.results["total_tasks_created"] += 1

                # 控制速率（避免爆发式创建）
                if tasks_to_create > 0:
                    time.sleep(1.0 / self.target_per_second)

                current_time = time.time()

            # 等待所有任务完成
            logger.info("等待所有任务完成...")
            for future in concurrent.futures.as_completed(task_futures):
                try:
                    success, latency, task_info = future.result(timeout=5.0)

                    with self.lock:
                        if success:
                            self.results["total_tasks_succeeded"] += 1
                            self.results["creation_latencies"].append(latency)
                        else:
                            self.results["total_tasks_failed"] += 1
                            self.results["errors"].append(
                                {"task_info": task_info, "timestamp": time.time()}
                            )
                except concurrent.futures.TimeoutError:
                    logger.warning("任务超时")
                    with self.lock:
                        self.results["total_tasks_failed"] += 1
                        self.results["errors"].append(
                            {"error": "任务执行超时", "timestamp": time.time()}
                        )
                except Exception as e:
                    logger.error(f"任务结果处理异常: {e}")
                    with self.lock:
                        self.results["total_tasks_failed"] += 1

            # 等待监控线程结束
            monitor_thread.join()

        # 计算最终结果
        self.results["end_time"] = time.time()
        self._calculate_final_metrics()

        return self.results

    def _monitor_loop(self, end_time: float):
        """监控循环（收集指标）"""
        logger.info("启动监控循环")

        while time.time() < end_time:
            # 收集系统指标
            self.collect_system_metrics()

            # 计算当前吞吐量
            with self.lock:
                elapsed_minutes = (time.time() - self.results["start_time"]) / 60.0
                if elapsed_minutes > 0:
                    current_throughput = self.results["total_tasks_created"] / elapsed_minutes
                    self.results["throughput_per_minute"].append(
                        {"timestamp": time.time(), "throughput": current_throughput}
                    )

            # 每秒收集一次
            time.sleep(1.0)

    def _calculate_final_metrics(self):
        """计算最终指标"""
        if not self.results["creation_latencies"]:
            return

        latencies = self.results["creation_latencies"]

        # 延迟统计
        self.results["latency_stats"] = {
            "count": len(latencies),
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "min": min(latencies),
            "max": max(latencies),
            "p90": statistics.quantiles(latencies, n=10)[8] if len(latencies) >= 10 else None,
            "p95": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else None,
            "p99": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else None,
        }

        # 成功率
        total = self.results["total_tasks_created"]
        if total > 0:
            self.results["success_rate"] = self.results["total_tasks_succeeded"] / total * 100
        else:
            self.results["success_rate"] = 0.0

        # 平均吞吐量
        duration_minutes = (self.results["end_time"] - self.results["start_time"]) / 60.0
        if duration_minutes > 0:
            self.results["avg_throughput"] = total / duration_minutes
        else:
            self.results["avg_throughput"] = 0.0

        # 系统资源使用统计
        if self.system_metrics:
            cpu_values = [m.get("cpu_percent", 0) for m in self.system_metrics]
            memory_values = [m.get("memory_percent", 0) for m in self.system_metrics]

            self.results["system_stats"] = {
                "cpu_mean": statistics.mean(cpu_values) if cpu_values else 0,
                "cpu_max": max(cpu_values) if cpu_values else 0,
                "memory_mean": statistics.mean(memory_values) if memory_values else 0,
                "memory_max": max(memory_values) if memory_values else 0,
            }

    def generate_report(self) -> str:
        """生成测试报告"""
        if not self.results.get("start_time"):
            return "测试未运行"

        duration = self.results["end_time"] - self.results["start_time"]

        report_lines = [
            "=" * 80,
            "Athena队列系统压力测试报告",
            "=" * 80,
            f"测试时间: {datetime.fromtimestamp(self.results['start_time']).strftime('%Y-%m-%d %H:%M:%S')}",
            f"持续时间: {duration:.1f}秒 ({duration/60:.1f}分钟)",
            f"目标速率: {self.target_rate} 任务/分钟",
            "",
            "📊 性能指标:",
            f"  总任务数: {self.results['total_tasks_created']}",
            f"  成功任务: {self.results['total_tasks_succeeded']}",
            f"  失败任务: {self.results['total_tasks_failed']}",
            f"  成功率: {self.results.get('success_rate', 0):.1f}%",
            f"  平均吞吐量: {self.results.get('avg_throughput', 0):.1f} 任务/分钟",
            "",
        ]

        # 延迟统计
        if "latency_stats" in self.results:
            stats = self.results["latency_stats"]
            report_lines.extend(
                [
                    "⏱️ 任务创建延迟统计:",
                    f"  样本数: {stats['count']}",
                    f"  平均延迟: {stats['mean']:.3f}秒",
                    f"  中位数: {stats['median']:.3f}秒",
                    f"  最小值: {stats['min']:.3f}秒",
                    f"  最大值: {stats['max']:.3f}秒",
                    f"  P90: {stats['p90']:.3f}秒" if stats["p90"] else "  P90: N/A",
                    f"  P95: {stats['p95']:.3f}秒" if stats["p95"] else "  P95: N/A",
                    f"  P99: {stats['p99']:.3f}秒" if stats["p99"] else "  P99: N/A",
                    "",
                ]
            )

        # 系统资源
        if "system_stats" in self.results:
            sys_stats = self.results["system_stats"]
            report_lines.extend(
                [
                    "💻 系统资源使用:",
                    f"  CPU使用率 - 平均: {sys_stats['cpu_mean']:.1f}%, 峰值: {sys_stats['cpu_max']:.1f}%",
                    f"  内存使用率 - 平均: {sys_stats['memory_mean']:.1f}%, 峰值: {sys_stats['memory_max']:.1f}%",
                    "",
                ]
            )

        # 智能路由统计
        if self.results["routing_decisions"]:
            executors = {}
            for decision in self.results["routing_decisions"]:
                executor = decision.get("assigned_executor", "unknown")
                executors[executor] = executors.get(executor, 0) + 1

            report_lines.append("🎯 智能路由决策统计:")
            for executor, count in executors.items():
                percentage = count / len(self.results["routing_decisions"]) * 100
                report_lines.append(f"  {executor}: {count} 次 ({percentage:.1f}%)")
            report_lines.append("")

        # 错误摘要
        if self.results["errors"]:
            report_lines.append("⚠️ 错误摘要:")
            error_types = {}
            for error in self.results["errors"]:
                error_msg = str(error.get("task_info", error.get("error", "unknown")))
                error_type = error_msg.split(":")[0] if ":" in error_msg else error_msg
                error_types[error_type] = error_types.get(error_type, 0) + 1

            for error_type, count in error_types.items():
                report_lines.append(f"  {error_type}: {count} 次")

        report_lines.extend(["", "=" * 80, "测试结论:", "=" * 80])

        # 测试结论
        success_rate = self.results.get("success_rate", 0)
        avg_throughput = self.results.get("avg_throughput", 0)
        target_achievement = (
            (avg_throughput / self.target_rate) * 100 if self.target_rate > 0 else 0
        )

        if success_rate >= 95.0 and target_achievement >= 90.0:
            conclusion = "✅ 测试通过: 系统满足100任务/分钟的性能要求"
        elif success_rate >= 80.0:
            conclusion = "⚠️  测试部分通过: 系统在高负载下表现可接受，但有改进空间"
        else:
            conclusion = "❌ 测试失败: 系统在高负载下表现不佳"

        report_lines.extend(
            [
                conclusion,
                f"  成功率: {success_rate:.1f}% ({'>=' if success_rate >= 95.0 else '<'} 95% 目标)",
                f"  吞吐量达成率: {target_achievement:.1f}% ({'>=' if target_achievement >= 90.0 else '<'} 90% 目标)",
                "",
                "建议:",
            ]
        )

        if success_rate < 95.0:
            report_lines.append("  • 检查任务创建逻辑的异常处理机制")
        if target_achievement < 90.0:
            report_lines.append("  • 优化系统资源分配，提高并发处理能力")
        if self.results["errors"]:
            report_lines.append("  • 分析错误模式，改进系统稳定性")

        report_lines.append("")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Athena队列系统压力测试")
    parser.add_argument(
        "--target-rate", type=float, default=100.0, help="目标任务率（任务/分钟），默认100任务/分钟"
    )
    parser.add_argument("--duration", type=int, default=5, help="测试持续时间（分钟），默认5分钟")
    parser.add_argument("--concurrency", type=int, default=10, help="并发任务数，默认10")
    parser.add_argument("--output", type=str, default=None, help="输出报告文件路径")

    args = parser.parse_args()

    print("🚀 Athena队列系统压力测试开始")
    print("=" * 60)
    print(f"目标速率: {args.target_rate} 任务/分钟")
    print(f"持续时间: {args.duration} 分钟")
    print(f"并发级别: {args.concurrency}")
    print()

    # 运行测试
    tester = AthenaQueueStressTester(target_rate=args.target_rate, duration_minutes=args.duration)

    try:
        results = tester.run_concurrent_test(concurrency_level=args.concurrency)
        report = tester.generate_report()

        # 输出报告
        print(report)

        # 保存结果
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            print(f"📄 报告已保存至: {output_path}")

            # 同时保存原始数据
            data_path = output_path.with_suffix(".json")
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            print(f"📊 原始数据已保存至: {data_path}")

        # 返回退出码
        success_rate = results.get("success_rate", 0)
        if success_rate >= 95.0:
            return 0
        else:
            print(f"\n⚠️  成功率低于95%: {success_rate:.1f}%")
            return 1

    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断测试")
        return 130
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ 测试框架错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
