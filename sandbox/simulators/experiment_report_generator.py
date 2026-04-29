#!/usr/bin/env python3
"""
MAREF沙箱实验报告生成器

基于实验控制器结果生成格式化的实验报告。
支持Markdown、HTML和JSON格式输出。
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class ExperimentReportGenerator:
    """实验报告生成器"""

    def __init__(self, experiment_data: Dict[str, Any]):
        """
        初始化报告生成器

        Args:
            experiment_data: 实验数据（来自experiment_controller.py）
        """
        self.experiment_data = experiment_data
        self.report_sections = []

    def generate_markdown_report(self) -> str:
        """生成Markdown格式报告"""
        report_lines = []

        # 标题
        report_lines.append("# MAREF沙箱实验报告")
        report_lines.append("")

        # 元数据
        metadata = self.experiment_data.get("metadata", {})
        report_lines.append("## 实验信息")
        report_lines.append("")
        report_lines.append(f"- **实验ID**: {metadata.get('experiment_id', 'N/A')}")
        report_lines.append(f"- **实验类型**: {metadata.get('experiment_type', 'N/A')}")
        report_lines.append(f"- **开始时间**: {metadata.get('start_time', 'N/A')}")
        report_lines.append(f"- **结束时间**: {metadata.get('end_time', 'N/A')}")
        report_lines.append(f"- **数据集大小**: {metadata.get('dataset_size', 'N/A')}")
        report_lines.append(
            f"- **并发级别**: {metadata.get('concurrency_level', 'N/A')}"
        )
        report_lines.append("")

        # 实验配置
        config = self.experiment_data.get("config", {})
        if config:
            report_lines.append("## 实验配置")
            report_lines.append("")
            for key, value in config.items():
                if isinstance(value, dict):
                    report_lines.append(f"- **{key}**:")
                    for subkey, subvalue in value.items():
                        report_lines.append(f"  - {subkey}: {subvalue}")
                else:
                    report_lines.append(f"- **{key}**: {value}")
            report_lines.append("")

        # 结果摘要
        results = self.experiment_data.get("results", {})
        if results:
            report_lines.append("## 结果摘要")
            report_lines.append("")

            # 总体性能
            performance = results.get("performance", {})
            if performance:
                report_lines.append("### 总体性能")
                report_lines.append("")
                report_lines.append(
                    f"- **总任务数**: {performance.get('total_tasks', 0)}"
                )
                report_lines.append(
                    f"- **成功任务数**: {performance.get('successful_tasks', 0)}"
                )
                report_lines.append(
                    f"- **成功率**: {performance.get('success_rate', 0):.1%}"
                )
                report_lines.append(
                    f"- **平均延迟**: {performance.get('avg_latency', 0):.3f}秒"
                )
                report_lines.append(
                    f"- **总耗时**: {performance.get('total_duration', 0):.2f}秒"
                )
                report_lines.append(
                    f"- **吞吐量**: {performance.get('throughput', 0):.2f}任务/秒"
                )
                report_lines.append("")

            # 系统对比
            comparison = results.get("comparison", {})
            if comparison:
                report_lines.append("### 系统对比")
                report_lines.append("")
                baseline = comparison.get("baseline", {})
                enhanced = comparison.get("enhanced", {})

                report_lines.append("| 指标 | 基线系统 | 增强系统 | 改进 |")
                report_lines.append("|------|----------|----------|------|")

                metrics_to_compare = [
                    (
                        "成功率",
                        "success_rate",
                        "{:.1%}",
                        "{:.1%}",
                        lambda b, e: (
                            f"+{(e-b)*100:.1f}%" if e > b else f"{(e-b)*100:.1f}%"
                        ),
                    ),
                    (
                        "平均延迟(秒)",
                        "avg_latency",
                        "{:.3f}",
                        "{:.3f}",
                        lambda b, e: (
                            f"{(b-e)/b*100:.1f}%" if e < b else f"-{(e-b)/b*100:.1f}%"
                        ),
                    ),
                    (
                        "吞吐量(任务/秒)",
                        "throughput",
                        "{:.2f}",
                        "{:.2f}",
                        lambda b, e: (
                            f"+{(e-b)/b*100:.1f}%" if e > b else f"{(e-b)/b*100:.1f}%"
                        ),
                    ),
                ]

                for name, key, b_fmt, e_fmt, calc_improvement in metrics_to_compare:
                    b_val = baseline.get(key, 0)
                    e_val = enhanced.get(key, 0)
                    improvement = calc_improvement(b_val, e_val)
                    report_lines.append(
                        f"| {name} | {b_fmt.format(b_val)} | {e_fmt.format(e_val)} | {improvement} |"
                    )

                report_lines.append("")

            # 质量评估
            quality = results.get("quality_assessment", {})
            if quality:
                report_lines.append("### 质量评估")
                report_lines.append("")
                for dimension, score in quality.items():
                    if isinstance(score, (int, float)):
                        # 创建简单的进度条
                        bar_length = 20
                        filled = int(score * bar_length)
                        bar = "█" * filled + "░" * (bar_length - filled)
                        report_lines.append(f"- **{dimension}**: {bar} {score:.1%}")
                report_lines.append("")

            # 监控数据摘要
            monitoring = results.get("monitoring_data", {})
            if monitoring:
                report_lines.append("### 监控数据")
                report_lines.append("")
                report_lines.append(
                    f"- **收集间隔**: {monitoring.get('collection_interval', 'N/A')}秒"
                )
                report_lines.append(
                    f"- **数据点数量**: {monitoring.get('data_point_count', 0)}"
                )
                report_lines.append(
                    f"- **告警数量**: {monitoring.get('alert_count', 0)}"
                )
                report_lines.append("")

        # 详细结果
        detailed_results = self.experiment_data.get("detailed_results", {})
        if detailed_results:
            report_lines.append("## 详细结果")
            report_lines.append("")

            # 任务级结果
            tasks = detailed_results.get("task_results", [])
            if tasks and len(tasks) > 0:
                report_lines.append(f"### 任务级结果 (抽样{min(5, len(tasks))}个)")
                report_lines.append("")
                for i, task in enumerate(tasks[:5]):
                    report_lines.append(f"#### 任务 {i+1}")
                    report_lines.append(f"- **ID**: {task.get('task_id', 'N/A')}")
                    report_lines.append(f"- **类型**: {task.get('task_type', 'N/A')}")
                    report_lines.append(f"- **状态**: {task.get('status', 'N/A')}")
                    report_lines.append(f"- **耗时**: {task.get('duration', 0):.3f}秒")
                    if task.get("error"):
                        report_lines.append(f"- **错误**: {task.get('error')}")
                    report_lines.append("")

        # 结论与建议
        report_lines.append("## 结论与建议")
        report_lines.append("")

        # 自动生成结论
        success_rate = results.get("performance", {}).get("success_rate", 0)
        avg_latency = results.get("performance", {}).get("avg_latency", 0)

        if success_rate >= 0.95:
            report_lines.append("✅ **实验成功**: 系统表现优秀，满足生产要求。")
        elif success_rate >= 0.85:
            report_lines.append("⚠️ **实验基本成功**: 系统表现良好，但仍有改进空间。")
        else:
            report_lines.append("❌ **实验失败**: 系统表现未达到预期，需要进一步优化。")

        report_lines.append("")

        # 基于结果的建议
        suggestions = []
        if success_rate < 0.9:
            suggestions.append("提高任务成功率和稳定性")
        if avg_latency > 1.0:
            suggestions.append("优化系统延迟，减少处理时间")

        if suggestions:
            report_lines.append("### 改进建议")
            report_lines.append("")
            for i, suggestion in enumerate(suggestions, 1):
                report_lines.append(f"{i}. {suggestion}")
            report_lines.append("")

        # 附录
        report_lines.append("## 附录")
        report_lines.append("")
        report_lines.append("- **原始数据文件**: 实验控制器生成的JSON文件")
        report_lines.append("- **监控数据**: 实时收集的系统和应用指标")
        report_lines.append("- **实验日志**: 详细的执行日志和错误信息")
        report_lines.append("")
        report_lines.append(f"*报告生成时间: {datetime.now().isoformat()}*")

        return "\n".join(report_lines)

    def save_report(self, output_path: str, format: str = "markdown") -> str:
        """
        保存报告到文件

        Args:
            output_path: 输出文件路径
            format: 报告格式 ("markdown", "html", "json")

        Returns:
            保存的文件路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if format == "markdown":
            content = self.generate_markdown_report()
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        elif format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.experiment_data, f, indent=2, ensure_ascii=False)
        elif format == "html":
            # 简单的HTML报告（可扩展）
            markdown = self.generate_markdown_report()
            html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MAREF沙箱实验报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        h3 {{ color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f8f9fa; }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        .success {{ color: #27ae60; }}
        .warning {{ color: #f39c12; }}
        .error {{ color: #e74c3c; }}
        .progress-bar {{ background-color: #ecf0f1; border-radius: 3px; height: 20px; margin: 5px 0; }}
        .progress-fill {{ background-color: #3498db; height: 100%; border-radius: 3px; }}
        pre {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div id="content">
        {markdown.replace(chr(10), '<br>').replace('# ', '<h1>').replace('## ', '<h2>').replace('### ', '<h3>')}
    </div>
</body>
</html>"""
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
        else:
            raise ValueError(f"不支持的格式: {format}")

        return output_path


def load_experiment_data(file_path: str) -> Dict[str, Any]:
    """从JSON文件加载实验数据"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """主函数 - 命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="MAREF沙箱实验报告生成器")
    parser.add_argument("--input", "-i", required=True, help="实验数据JSON文件路径")
    parser.add_argument(
        "--output",
        "-o",
        default="./experiment_report.md",
        help="输出报告文件路径 (默认: ./experiment_report.md)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["markdown", "html", "json"],
        default="markdown",
        help="报告格式 (默认: markdown)",
    )

    args = parser.parse_args()

    # 加载数据
    print(f"📂 加载实验数据: {args.input}")
    experiment_data = load_experiment_data(args.input)

    # 生成报告
    print(f"📝 生成{args.format}报告...")
    generator = ExperimentReportGenerator(experiment_data)
    output_path = generator.save_report(args.output, args.format)

    print(f"✅ 报告已保存: {output_path}")
    print(
        f"   实验类型: {experiment_data.get('metadata', {}).get('experiment_type', 'N/A')}"
    )
    print(
        f"   任务数量: {experiment_data.get('results', {}).get('performance', {}).get('total_tasks', 0)}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
