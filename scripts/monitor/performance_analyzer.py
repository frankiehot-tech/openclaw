"""
性能分析器
分析Open Code CLI执行性能，识别瓶颈
"""

import json
import logging
import statistics
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {
            "sample_size": 10,
            "timeout_seconds": 300,
            "analyze_categories": ["build", "review", "plan"],
            "output_dir": "performance_reports",
        }

        self.root_dir = Path(__file__).parent.parent
        self.output_dir = self.root_dir / self.config["output_dir"]
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 性能基准数据
        self.baseline_metrics = {
            "build_time_seconds": 1800,  # 30分钟
            "review_time_seconds": 1200,  # 20分钟
            "plan_time_seconds": 1500,  # 25分钟
            "success_rate": 0.85,  # 85%
            "stall_rate": 0.15,  # 15%
        }

    def analyze_opencode_execution(
        self, task_description: str, category: str = "build"
    ) -> dict[str, Any]:
        """分析Open Code CLI执行性能"""

        analysis = {
            "task_description": task_description[:200],
            "category": category,
            "start_time": datetime.now().isoformat(),
            "metrics": {},
            "bottlenecks": [],
            "recommendations": [],
        }

        try:
            # 记录开始时间
            start_time = time.time()

            # 执行Open Code CLI命令
            cmd = ["opencode", "@explorer", task_description]

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8"
            )

            # 监控执行过程
            output_lines = []
            last_output_time = time.time()
            stall_detected = False

            while True:
                # 检查超时
                elapsed = time.time() - start_time
                if elapsed > self.config["timeout_seconds"]:
                    process.terminate()
                    analysis["metrics"]["timeout"] = True
                    analysis["bottlenecks"].append("execution_timeout")
                    analysis["recommendations"].append("减少任务复杂度或增加超时时间")
                    break

                # 检查输出
                line = process.stdout.readline()
                if line:
                    output_lines.append(line.strip())
                    last_output_time = time.time()

                    # 检查stall
                    if len(output_lines) > 10:
                        # 分析输出模式
                        recent_output = output_lines[-10:]
                        if all(len(line) < 20 for line in recent_output):
                            stall_time = time.time() - last_output_time
                            if stall_time > 120:  # 2分钟无实质输出
                                stall_detected = True
                                analysis["bottlenecks"].append("output_stall")
                                analysis["recommendations"].append("优化任务描述，减少思考时间")
                elif process.poll() is not None:
                    # 进程结束
                    break
                else:
                    # 无输出，等待
                    time.sleep(0.1)

            # 记录结束时间
            end_time = time.time()
            execution_time = end_time - start_time

            # 收集指标
            analysis["metrics"].update(
                {
                    "execution_time_seconds": execution_time,
                    "output_line_count": len(output_lines),
                    "stall_detected": stall_detected,
                    "exit_code": process.returncode,
                    "success": process.returncode == 0,
                }
            )

            # 与基准比较
            baseline_key = f"{category}_time_seconds"
            if baseline_key in self.baseline_metrics:
                baseline = self.baseline_metrics[baseline_key]
                improvement = ((baseline - execution_time) / baseline) * 100
                analysis["metrics"]["improvement_vs_baseline_percent"] = improvement

                if improvement > 0:
                    analysis["recommendations"].append(f"执行时间比基准快{improvement:.1f}%")
                else:
                    analysis["recommendations"].append(
                        f"执行时间比基准慢{-improvement:.1f}%，需要优化"
                    )

            # 分析输出内容
            if output_lines:
                avg_line_length = statistics.mean([len(line) for line in output_lines if line])
                analysis["metrics"]["avg_output_line_length"] = avg_line_length

                # 检查错误模式
                error_keywords = ["错误", "失败", "error", "fail", "timeout", "超时"]
                error_lines = [
                    line
                    for line in output_lines
                    if any(kw in line.lower() for kw in error_keywords)
                ]
                if error_lines:
                    analysis["bottlenecks"].append("error_in_output")
                    analysis["recommendations"].append("修复任务描述中的问题")

        except Exception as e:
            analysis["error"] = str(e)
            analysis["success"] = False

        analysis["end_time"] = datetime.now().isoformat()
        return analysis

    def generate_performance_report(self, analyses: list[dict[str, Any]]) -> dict[str, Any]:
        """生成性能报告"""

        if not analyses:
            return {"error": "没有分析数据"}

        # 统计指标
        successful_analyses = [a for a in analyses if a.get("metrics", {}).get("success", False)]
        failed_analyses = [a for a in analyses if not a.get("metrics", {}).get("success", True)]

        # 计算平均执行时间
        exec_times = [
            a["metrics"].get("execution_time_seconds", 0)
            for a in successful_analyses
            if "execution_time_seconds" in a.get("metrics", {})
        ]

        avg_exec_time = statistics.mean(exec_times) if exec_times else 0

        # 成功率
        success_rate = len(successful_analyses) / len(analyses) if analyses else 0

        # 常见瓶颈
        all_bottlenecks = []
        for analysis in analyses:
            all_bottlenecks.extend(analysis.get("bottlenecks", []))

        bottleneck_counts = {}
        for bottleneck in all_bottlenecks:
            bottleneck_counts[bottleneck] = bottleneck_counts.get(bottleneck, 0) + 1

        # 常见建议
        all_recommendations = []
        for analysis in analyses:
            all_recommendations.extend(analysis.get("recommendations", []))

        recommendation_counts = {}
        for rec in all_recommendations:
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1

        # 生成报告
        report = {
            "report_generated": datetime.now().isoformat(),
            "summary": {
                "total_analyses": len(analyses),
                "successful_analyses": len(successful_analyses),
                "failed_analyses": len(failed_analyses),
                "success_rate": success_rate,
                "avg_execution_time_seconds": avg_exec_time,
            },
            "performance_metrics": {
                "vs_baseline_success_rate": success_rate - self.baseline_metrics["success_rate"],
                "vs_baseline_exec_time": (
                    self.baseline_metrics["build_time_seconds"] - avg_exec_time
                )
                / self.baseline_metrics["build_time_seconds"]
                * 100
                if avg_exec_time > 0
                else 0,
            },
            "bottleneck_analysis": bottleneck_counts,
            "recommendation_summary": recommendation_counts,
            "detailed_analyses": analyses,
        }

        return report

    def save_report(self, report: dict[str, Any], filename: str | None = None):
        """保存报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"

        report_path = self.output_dir / filename
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"性能报告已保存: {report_path}")
        return report_path


def analyze_sample_tasks():
    """分析样本任务性能"""
    analyzer = PerformanceAnalyzer()

    # 样本任务
    sample_tasks = [
        {"description": "分析系统架构复杂度", "category": "analysis"},
        {"description": "实现用户登录功能", "category": "build"},
        {"description": "编写API文档", "category": "documentation"},
    ]

    print("开始性能分析...")
    analyses = []

    for i, task in enumerate(sample_tasks, 1):
        print(f"\n分析任务 {i}/{len(sample_tasks)}: {task['description']}")

        analysis = analyzer.analyze_opencode_execution(task["description"], task["category"])

        analyses.append(analysis)

        # 显示简要结果
        if analysis.get("success"):
            exec_time = analysis["metrics"].get("execution_time_seconds", 0)
            print(f"  结果: ✅ 成功, 执行时间: {exec_time:.1f}秒")
        else:
            print("  结果: ❌ 失败")

    # 生成报告
    report = analyzer.generate_performance_report(analyses)

    # 保存报告
    report_path = analyzer.save_report(report)

    # 显示摘要
    print(f"\n{'=' * 60}")
    print("性能分析摘要")
    print(f"{'=' * 60}")
    print(f"分析任务数: {report['summary']['total_analyses']}")
    print(f"成功率: {report['summary']['success_rate'] * 100:.1f}%")
    print(f"平均执行时间: {report['summary']['avg_execution_time_seconds']:.1f}秒")

    if report["summary"]["success_rate"] > analyzer.baseline_metrics["success_rate"]:
        improvement = (
            report["summary"]["success_rate"] - analyzer.baseline_metrics["success_rate"]
        ) * 100
        print(f"✅ 成功率比基准高 {improvement:.1f}%")
    else:
        print("⚠️  成功率低于基准")

    if report["bottleneck_analysis"]:
        print("\n主要瓶颈:")
        for bottleneck, count in report["bottleneck_analysis"].items():
            print(f"  {bottleneck}: {count}次")

    if report["recommendation_summary"]:
        print("\n优化建议:")
        for recommendation, count in report["recommendation_summary"].items():
            if count > 1:
                print(f"  {recommendation} ({count}次)")

    print(f"\n详细报告: {report_path}")


if __name__ == "__main__":
    analyze_sample_tasks()
