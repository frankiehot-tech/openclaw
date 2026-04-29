#!/usr/bin/env python3
"""
文档质量报告生成器
集成所有文档质量检查工具，生成综合质量报告
"""

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class DocumentQualityReportGenerator:
    """文档质量报告生成器"""

    def __init__(self, docs_dir="docs/"):
        self.docs_dir = Path(docs_dir)
        self.quality_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "files": {},
            "issues_by_category": defaultdict(list),
            "metrics": {},
            "recommendations": [],
        }

    def run_format_check(self):
        """运行格式检查"""
        print("🔍 运行文档格式检查...")

        try:
            # 通过子进程调用格式检查工具
            cmd = [
                sys.executable,
                "scripts/validate_document_format.py",
                "--directory",
                str(self.docs_dir),
                "--output",
                "/tmp/format_report.md",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

            if result.returncode == 0:
                print("  ✅ 格式检查完成")
            else:
                print(f"  ⚠️  格式检查发现问题 (退出码: {result.returncode})")

            # 解析输出获取统计数据
            self.quality_data["metrics"]["format_check"] = {
                "exit_code": result.returncode,
                "output_summary": self._extract_summary_from_output(result.stdout),
            }

        except Exception as e:
            print(f"  ❌ 格式检查失败: {e}")
            self.quality_data["metrics"]["format_check"] = {"error": str(e), "exit_code": -1}

    def run_link_check(self):
        """运行链接检查"""
        print("🔗 运行文档链接检查...")

        try:
            cmd = [
                sys.executable,
                "scripts/check_document_links.py",
                "--directory",
                str(self.docs_dir),
                "--verbose",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

            # 分析输出统计无效链接数量
            broken_links_count = 0
            for line in result.stdout.split("\n"):
                if "无效链接" in line or "broken link" in line.lower():
                    # 尝试提取数字
                    import re

                    match = re.search(r"(\d+)\s*个", line)
                    if match:
                        broken_links_count = int(match.group(1))
                        break

            self.quality_data["metrics"]["link_check"] = {
                "exit_code": result.returncode,
                "broken_links": broken_links_count,
                "output_summary": self._extract_summary_from_output(result.stdout),
            }

            if broken_links_count == 0:
                print("  ✅ 所有链接有效")
            else:
                print(f"  ⚠️  发现 {broken_links_count} 个无效链接")

        except Exception as e:
            print(f"  ❌ 链接检查失败: {e}")
            self.quality_data["metrics"]["link_check"] = {"error": str(e), "exit_code": -1}

    def run_completeness_check(self):
        """运行完整性检查"""
        print("📝 运行文档完整性检查...")

        try:
            cmd = [
                sys.executable,
                "scripts/check_document_completeness.py",
                "--directory",
                str(self.docs_dir),
                "--metrics",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

            # 尝试从输出中提取JSON格式的指标数据
            metrics_data = {}
            try:
                # 查找JSON输出部分
                lines = result.stdout.split("\n")
                in_json = False
                json_content = []

                for line in lines:
                    if "指标数据:" in line or "📊" in line:
                        in_json = True
                        continue
                    if in_json and line.strip():
                        json_content.append(line)

                if json_content:
                    json_str = "\n".join(json_content)
                    metrics_data = json.loads(json_str)

            except json.JSONDecodeError:
                # 如果无法解析JSON，使用简单统计
                pass

            self.quality_data["metrics"]["completeness_check"] = {
                "exit_code": result.returncode,
                "metrics": metrics_data,
                "output_summary": self._extract_summary_from_output(result.stdout),
            }

            if result.returncode == 0:
                print("  ✅ 完整性检查完成")
            else:
                print("  ⚠️  完整性检查发现问题")

        except Exception as e:
            print(f"  ❌ 完整性检查失败: {e}")
            self.quality_data["metrics"]["completeness_check"] = {"error": str(e), "exit_code": -1}

    def run_readability_analysis(self):
        """运行可读性分析"""
        print("📊 运行文档可读性分析...")

        try:
            cmd = [
                sys.executable,
                "scripts/analyze_document_readability.py",
                "--directory",
                str(self.docs_dir),
                "--json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

            # 尝试解析JSON输出
            readability_data = {}
            try:
                # 查找JSON输出
                json_start = result.stdout.find("{")
                json_end = result.stdout.rfind("}") + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = result.stdout[json_start:json_end]
                    readability_data = json.loads(json_str)

            except (json.JSONDecodeError, ValueError):
                # 如果无法解析JSON，使用简单统计
                pass

            self.quality_data["metrics"]["readability_analysis"] = {
                "exit_code": result.returncode,
                "data": readability_data,
                "output_summary": self._extract_summary_from_output(result.stdout),
            }

            if result.returncode == 0:
                print("  ✅ 可读性分析完成")
            else:
                print("  ⚠️  可读性分析发现问题")

        except Exception as e:
            print(f"  ❌ 可读性分析失败: {e}")
            self.quality_data["metrics"]["readability_analysis"] = {
                "error": str(e),
                "exit_code": -1,
            }

    def _extract_summary_from_output(self, output):
        """从工具输出中提取摘要信息"""
        summary = {}
        lines = output.split("\n")

        # 查找关键摘要行
        for line in lines:
            if "通过:" in line or "passed:" in line.lower():
                summary["pass_info"] = line.strip()
            elif "失败:" in line or "failed:" in line.lower():
                summary["fail_info"] = line.strip()
            elif "问题:" in line or "issues:" in line.lower():
                summary["issues_info"] = line.strip()
            elif "找到" in line and "个" in line and ("文件" in line or "链接" in line):
                summary["count_info"] = line.strip()

        return summary

    def analyze_individual_files(self):
        """分析单个文件的质量"""
        print("📄 分析单个文件质量...")

        # 查找所有Markdown文件
        md_files = list(self.docs_dir.rglob("*.md"))
        print(f"  找到 {len(md_files)} 个Markdown文件")

        sample_files = md_files[:10]  # 分析前10个文件作为样本
        file_metrics = {}

        for i, md_file in enumerate(sample_files):
            rel_path = md_file.relative_to(self.docs_dir)
            print(f"  分析文件 {i + 1}/{len(sample_files)}: {rel_path}")

            # 计算文件基本指标
            try:
                with open(md_file, encoding="utf-8") as f:
                    content = f.read()

                lines = content.split("\n")

                # 基本统计
                file_metric = {
                    "line_count": len(lines),
                    "char_count": len(content),
                    "has_title": any(line.startswith("# ") for line in lines),
                    "has_metadata": any(
                        "最后更新" in line or "Last updated" in line for line in lines
                    ),
                    "has_links": "[" in content and "](" in content,
                    "has_code_blocks": "```" in content,
                    "has_tables": "|" in content and "-" in content,
                }

                # 计算非空行数
                non_empty_lines = [line for line in lines if line.strip()]
                file_metric["non_empty_line_count"] = len(non_empty_lines)

                file_metrics[str(rel_path)] = file_metric

            except Exception as e:
                print(f"    读取文件失败: {e}")

        self.quality_data["files"] = file_metrics

    def generate_summary(self):
        """生成综合摘要"""
        print("📈 生成综合质量摘要...")

        summary = {
            "total_files_analyzed": len(self.quality_data.get("files", {})),
            "checks_performed": list(self.quality_data.get("metrics", {}).keys()),
            "overall_status": "pending",
        }

        # 检查各工具结果
        check_results = []
        for check_name, check_data in self.quality_data.get("metrics", {}).items():
            exit_code = check_data.get("exit_code", -1)
            status = "✅ 通过" if exit_code == 0 else "⚠️  警告" if exit_code > 0 else "❌ 失败"
            check_results.append({"check": check_name, "status": status, "exit_code": exit_code})

        summary["check_results"] = check_results

        # 计算整体状态
        passed_checks = sum(1 for r in check_results if r["exit_code"] == 0)
        total_checks = len(check_results)

        if total_checks == 0:
            summary["overall_status"] = "❌ 无检查结果"
        elif passed_checks == total_checks:
            summary["overall_status"] = "✅ 优秀"
        elif passed_checks >= total_checks * 0.7:
            summary["overall_status"] = "⚠️  良好"
        else:
            summary["overall_status"] = "❌ 需改进"

        summary["passed_checks"] = passed_checks
        summary["total_checks"] = total_checks
        summary["pass_rate"] = (
            round(passed_checks / total_checks * 100, 1) if total_checks > 0 else 0
        )

        self.quality_data["summary"] = summary

    def generate_recommendations(self):
        """生成改进建议"""
        recommendations = []
        metrics = self.quality_data.get("metrics", {})

        # 基于链接检查结果的建议
        link_check = metrics.get("link_check", {})
        broken_links = link_check.get("broken_links", 0)
        if broken_links > 0:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "链接质量",
                    "action": f"修复 {broken_links} 个无效链接",
                    "details": "运行 python3 scripts/check_document_links.py --directory docs/ --repair 生成修复建议",
                }
            )

        # 基于格式检查结果的建议
        format_check = metrics.get("format_check", {})
        if format_check.get("exit_code", 0) > 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "格式规范",
                    "action": "修复文档格式问题",
                    "details": "运行 python3 scripts/validate_document_format.py --directory docs/ --strict 查看详细问题",
                }
            )

        # 基于完整性检查结果的建议
        completeness_check = metrics.get("completeness_check", {})
        completeness_metrics = completeness_check.get("metrics", {})
        avg_score = completeness_metrics.get("avg_completeness_score", 0)

        if avg_score < 70:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "文档完整性",
                    "action": "提升文档完整性分数",
                    "details": f"当前平均完整性分数 {avg_score:.1f}/100，建议补充元数据和结构",
                }
            )

        # 基于可读性分析结果的建议
        readability_analysis = metrics.get("readability_analysis", {})
        readability_data = readability_analysis.get("data", {})

        if readability_data:
            avg_readability = readability_data.get("avg_readability_score", 0)
            if avg_readability < 60:
                recommendations.append(
                    {
                        "priority": "low",
                        "category": "可读性",
                        "action": "改善文档可读性",
                        "details": f"当前平均可读性分数 {avg_readability:.1f}/100，建议简化句子结构，减少技术术语密度",
                    }
                )

        # 基于文件分析的建议
        files = self.quality_data.get("files", {})
        files_without_title = sum(1 for f in files.values() if not f.get("has_title", False))
        files_without_metadata = sum(1 for f in files.values() if not f.get("has_metadata", False))

        if files_without_title > 0:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "文档结构",
                    "action": f"为 {files_without_title} 个文档添加标题",
                    "details": "每个Markdown文档应以# 标题开头",
                }
            )

        if files_without_metadata > 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "文档元数据",
                    "action": f"为 {files_without_metadata} 个文档添加最后更新日期",
                    "details": '建议在文档末尾添加"最后更新: YYYY-MM-DD"元数据',
                }
            )

        self.quality_data["recommendations"] = recommendations

    def generate_report(self):
        """生成完整质量报告"""
        print("\n" + "=" * 80)
        print("📊 文档质量综合报告")
        print("=" * 80)

        summary = self.quality_data.get("summary", {})

        print("\n📈 摘要:")
        print(f"  整体状态: {summary.get('overall_status', '未知')}")
        print(
            f"  检查通过率: {summary.get('pass_rate', 0)}% ({summary.get('passed_checks', 0)}/{summary.get('total_checks', 0)})"
        )
        print(f"  分析时间: {self.quality_data.get('timestamp', '未知')}")

        print("\n🔍 检查结果:")
        for check_result in summary.get("check_results", []):
            print(
                f"  {check_result['check']}: {check_result['status']} (退出码: {check_result['exit_code']})"
            )

        print(f"\n💡 改进建议 ({len(self.quality_data.get('recommendations', []))} 个):")
        for i, rec in enumerate(self.quality_data.get("recommendations", []), 1):
            print(f"  {i}. [{rec['priority'].upper()}] {rec['category']}: {rec['action']}")

        print(f"\n📄 文件样本分析 ({len(self.quality_data.get('files', {}))} 个文件):")
        files = self.quality_data.get("files", {})
        if files:
            for file_path, metrics in list(files.items())[:5]:  # 显示前5个文件
                print(
                    f"  - {file_path}: {metrics.get('line_count', 0)} 行, 标题: {'有' if metrics.get('has_title') else '无'}, 元数据: {'有' if metrics.get('has_metadata') else '无'}"
                )

        print("\n" + "=" * 80)

    def save_report(self, output_file):
        """保存报告到文件"""
        print(f"\n💾 保存报告到: {output_file}")

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.quality_data, f, indent=2, ensure_ascii=False)
            print("  ✅ 报告保存成功")
        except Exception as e:
            print(f"  ❌ 保存报告失败: {e}")

    def run_all_checks(self):
        """运行所有检查"""
        print("🚀 开始文档质量综合检查")
        print(f"📁 检查目录: {self.docs_dir}")

        # 运行所有检查工具
        self.run_format_check()
        self.run_link_check()
        self.run_completeness_check()
        self.run_readability_analysis()

        # 分析文件样本
        self.analyze_individual_files()

        # 生成报告
        self.generate_summary()
        self.generate_recommendations()
        self.generate_report()

        return self.quality_data


def main():
    parser = argparse.ArgumentParser(description="生成文档质量综合报告")
    parser.add_argument("--directory", "-d", default="docs/", help="文档目录 (默认: docs/)")
    parser.add_argument(
        "--output",
        "-o",
        default="quality_report.json",
        help="输出报告文件 (默认: quality_report.json)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    # 检查目录是否存在
    if not os.path.exists(args.directory):
        print(f"❌ 目录不存在: {args.directory}")
        sys.exit(1)

    # 创建报告生成器
    generator = DocumentQualityReportGenerator(docs_dir=args.directory)

    # 运行所有检查
    quality_data = generator.run_all_checks()

    # 保存报告
    generator.save_report(args.output)

    # 根据整体状态返回退出码
    summary = quality_data.get("summary", {})
    overall_status = summary.get("overall_status", "")

    if "优秀" in overall_status or "良好" in overall_status:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
