#!/usr/bin/env python3
"""
Claw Analyzer v0.1 - Claude Code 架构考古分析工具
基于AutoResearch方法论的多维度逆向工程分析
"""

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class ClawAnalyzer:
    """Claude Code 架构分析器"""

    def __init__(self, codebase_path: str):
        self.codebase_path = Path(codebase_path)
        self.analysis_results = {}

    def analyze_codebase_structure(self) -> Dict[str, Any]:
        """分析代码库基础结构"""

        print("🔍 分析代码库基础结构...")

        structure = {
            "total_files": 0,
            "total_lines": 0,
            "file_types": {},
            "directory_structure": {},
            "largest_files": [],
        }

        # 使用scc进行代码度量分析
        try:
            result = subprocess.run(
                ["scc", "--by-file", "--format", "json", str(self.codebase_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                scc_data = json.loads(result.stdout)
                structure["total_files"] = len(scc_data)
                structure["total_lines"] = sum(file["Lines"] for file in scc_data)

                # 分析文件类型分布
                for file in scc_data:
                    file_type = file["Language"]
                    structure["file_types"][file_type] = (
                        structure["file_types"].get(file_type, 0) + 1
                    )

                # 找出最大的文件
                structure["largest_files"] = sorted(
                    scc_data, key=lambda x: x["Lines"], reverse=True
                )[:10]

        except Exception as e:
            print(f"❌ SCC分析失败: {e}")

        return structure

    def extract_feature_flags(self) -> Dict[str, List[str]]:
        """提取特性标志系统"""

        print("🔍 提取特性标志系统...")

        feature_flags = {
            "bun_bundle": [],
            "macro_patterns": [],
            "proactive_flags": [],
            "voice_flags": [],
        }

        # 搜索bun:bundle模式
        bun_pattern = re.compile(r"bun:bundle\s*[\"\']([^\"\']+)[\"\']")
        macro_pattern = re.compile(r"MACRO\.[A-Z_]+")
        proactive_pattern = re.compile(r"PROACTIVE|proactive", re.IGNORECASE)
        voice_pattern = re.compile(r"VOICE|voice", re.IGNORECASE)

        for file_path in self.codebase_path.rglob("*.ts"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 匹配各种特性标志
                bun_matches = bun_pattern.findall(content)
                macro_matches = macro_pattern.findall(content)
                proactive_matches = proactive_pattern.findall(content)
                voice_matches = voice_pattern.findall(content)

                if bun_matches:
                    feature_flags["bun_bundle"].extend(
                        [
                            f"{file_path.relative_to(self.codebase_path)}: {match}"
                            for match in bun_matches
                        ]
                    )

                if macro_matches:
                    feature_flags["macro_patterns"].extend(
                        [
                            f"{file_path.relative_to(self.codebase_path)}: {match}"
                            for match in macro_matches
                        ]
                    )

                if proactive_matches:
                    feature_flags["proactive_flags"].extend(
                        [
                            f"{file_path.relative_to(self.codebase_path)}: {match}"
                            for match in proactive_matches
                        ]
                    )

                if voice_matches:
                    feature_flags["voice_flags"].extend(
                        [
                            f"{file_path.relative_to(self.codebase_path)}: {match}"
                            for match in voice_matches
                        ]
                    )

            except Exception as e:
                print(f"❌ 分析文件失败 {file_path}: {e}")

        return feature_flags

    def identify_hidden_subsystems(self) -> Dict[str, Any]:
        """识别隐藏子系统"""

        print("🔍 识别隐藏子系统...")

        subsystems = {
            "kairos_system": [],
            "buddy_system": [],
            "undercover_mode": [],
            "anti_distillation": [],
        }

        # 搜索子系统相关关键词
        kairos_pattern = re.compile(r"KAIROS|kairos|梦境|dream", re.IGNORECASE)
        buddy_pattern = re.compile(r"BUDDY|buddy|抽卡|养成", re.IGNORECASE)
        undercover_pattern = re.compile(r"UNDERCOVER|undercover|伪装|身份", re.IGNORECASE)
        anti_distill_pattern = re.compile(r"ANTI.?DISTILL|anti.?distill|反蒸馏", re.IGNORECASE)

        for file_path in self.codebase_path.rglob("*.ts"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                relative_path = str(file_path.relative_to(self.codebase_path))

                if kairos_pattern.search(content):
                    subsystems["kairos_system"].append(relative_path)

                if buddy_pattern.search(content):
                    subsystems["buddy_system"].append(relative_path)

                if undercover_pattern.search(content):
                    subsystems["undercover_mode"].append(relative_path)

                if anti_distill_pattern.search(content):
                    subsystems["anti_distillation"].append(relative_path)

            except Exception as e:
                print(f"❌ 分析文件失败 {file_path}: {e}")

        return subsystems

    def analyze_query_engine_complexity(self) -> Dict[str, Any]:
        """分析QueryEngine复杂度"""

        print("🔍 分析QueryEngine复杂度...")

        query_engine_analysis = {
            "total_files": 0,
            "total_lines": 0,
            "error_handling_ratio": 0.0,
            "complexity_metrics": {},
        }

        # 搜索QueryEngine相关文件
        query_engine_files = []
        for file_path in self.codebase_path.rglob("*query*"):
            if file_path.suffix in [".ts", ".js"]:
                query_engine_files.append(file_path)

        query_engine_analysis["total_files"] = len(query_engine_files)

        # 分析每个文件
        total_error_lines = 0
        total_code_lines = 0

        error_patterns = [
            re.compile(r"try\s*\{"),
            re.compile(r"catch\s*\("),
            re.compile(r"throw\s+"),
            re.compile(r"error|exception", re.IGNORECASE),
        ]

        for file_path in query_engine_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                file_lines = len(lines)
                total_code_lines += file_lines

                error_lines = 0
                for line in lines:
                    for pattern in error_patterns:
                        if pattern.search(line):
                            error_lines += 1
                            break

                total_error_lines += error_lines

            except Exception as e:
                print(f"❌ 分析QueryEngine文件失败 {file_path}: {e}")

        if total_code_lines > 0:
            query_engine_analysis["error_handling_ratio"] = total_error_lines / total_code_lines

        query_engine_analysis["total_lines"] = total_code_lines

        return query_engine_analysis

    def generate_architecture_report(self) -> Dict[str, Any]:
        """生成架构分析报告"""

        print("📊 生成架构分析报告...")

        report = {
            "metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "codebase_path": str(self.codebase_path),
                "analyzer_version": "v0.1",
            },
            "codebase_structure": self.analyze_codebase_structure(),
            "feature_flags": self.extract_feature_flags(),
            "hidden_subsystems": self.identify_hidden_subsystems(),
            "query_engine_analysis": self.analyze_query_engine_complexity(),
            "key_findings": {},
            "recommendations": [],
        }

        # 生成关键发现
        self._generate_key_findings(report)

        # 生成建议
        self._generate_recommendations(report)

        return report

    def _generate_key_findings(self, report: Dict[str, Any]):
        """生成关键发现"""

        findings = report["key_findings"]

        # 基于分析结果生成发现
        structure = report["codebase_structure"]
        query_engine = report["query_engine_analysis"]

        findings["defensive_programming_ratio"] = query_engine.get("error_handling_ratio", 0)
        findings["total_codebase_size"] = structure.get("total_lines", 0)
        findings["file_type_distribution"] = structure.get("file_types", {})

        # 隐藏子系统发现
        subsystems = report["hidden_subsystems"]
        findings["hidden_subsystem_count"] = sum(len(v) for v in subsystems.values())

        # 特性标志发现
        feature_flags = report["feature_flags"]
        findings["feature_flag_count"] = sum(len(v) for v in feature_flags.values())

    def _generate_recommendations(self, report: Dict[str, Any]):
        """生成建议"""

        recommendations = report["recommendations"]
        findings = report["key_findings"]

        # 基于发现生成建议
        if findings.get("defensive_programming_ratio", 0) > 0.5:
            recommendations.append(
                "QueryEngine中错误处理代码占比过高，建议重构为更简洁的错误处理策略"
            )

        if findings.get("hidden_subsystem_count", 0) > 0:
            recommendations.append("发现多个隐藏子系统，建议进行深度机制分析")

        if findings.get("feature_flag_count", 0) > 0:
            recommendations.append("特性标志系统复杂，建议建立统一的特性管理策略")


def main():
    """主函数"""

    # 假设的代码库路径（实际使用时需要替换）
    codebase_path = "/path/to/claude-code-leaked"

    # 检查代码库是否存在
    if not os.path.exists(codebase_path):
        print("⚠️ 代码库路径不存在，使用模拟分析模式")
        # 这里可以添加模拟分析逻辑
        return

    # 创建分析器
    analyzer = ClawAnalyzer(codebase_path)

    # 执行分析
    report = analyzer.generate_architecture_report()

    # 保存报告
    report_path = "/Volumes/1TB-M2/openclaw/claude_code_architecture_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"✅ 架构分析报告已保存: {report_path}")

    # 打印摘要
    print("\n📋 分析摘要:")
    print(f"   代码库大小: {report['codebase_structure']['total_lines']} 行")
    print(f"   文件数量: {report['codebase_structure']['total_files']} 个")
    print(
        f"   QueryEngine错误处理比例: {report['query_engine_analysis']['error_handling_ratio']:.2%}"
    )
    print(f"   隐藏子系统数量: {report['key_findings']['hidden_subsystem_count']}")
    print(f"   特性标志数量: {report['key_findings']['feature_flag_count']}")


if __name__ == "__main__":
    main()
