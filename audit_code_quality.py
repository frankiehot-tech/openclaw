#!/usr/bin/env python3
"""
代码质量详细审计工具 - 阶段2

基于深度审计计划，对智能任务队列系统进行全面的代码质量审计：
1. 代码规范检查（PEP 8、类型注解）
2. 复杂度分析（圈复杂度、认知复杂度）
3. 测试覆盖率和质量评估
4. 依赖关系分析
5. 代码可维护性评估
"""

import ast
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config.paths import ROOT_DIR

    BASE_DIR = ROOT_DIR
    print(f"✅ 使用config.paths模块配置路径")
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    BASE_DIR = Path("/Volumes/1TB-M2/openclaw")

# 需要审计的核心文件列表
CORE_FILES = [
    "scripts/athena_ai_plan_runner.py",
    "scripts/queue_liveness_probe.py",
    "protect_all_queues.py",
    "monitor_queue.py",
    "queue_monitor_dashboard.py",
    "fix_problematic_task_ids.py",
    "fix_task_id_normalization.py",
    "fix_manifest_duplicates.py",
    "verify_p0_issues.py",
    "scripts/athena_queue_deep_audit.py",
]


class CodeQualityAuditor:
    """代码质量审计器"""

    def __init__(self, output_dir: Path = None):
        if output_dir is None:
            self.output_dir = BASE_DIR / "audit_results" / "code_quality"
        else:
            self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.results = {
            "summary": {},
            "file_analysis": {},
            "complexity_analysis": {},
            "quality_metrics": {},
            "issues": [],
        }

    def analyze_file_complexity(self, file_path: Path) -> Dict[str, Any]:
        """分析文件复杂度"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        analysis = {
            "file_path": str(file_path),
            "lines": len(content.splitlines()),
            "functions": 0,
            "classes": 0,
            "cyclomatic_complexity": 0,
            "cognitive_complexity": 0,
            "imports": 0,
            "comments": 0,
            "docstrings": 0,
        }

        try:
            tree = ast.parse(content)

            # 统计基本信息
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis["functions"] += 1
                elif isinstance(node, ast.ClassDef):
                    analysis["classes"] += 1
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    analysis["imports"] += 1

            # 计算注释比例
            comment_pattern = r"^\s*#"
            lines = content.splitlines()
            analysis["comments"] = sum(1 for line in lines if re.match(comment_pattern, line))

            # 计算文档字符串
            docstring_pattern = r"\"\"\"[\s\S]*?\"\"\"|\'\'\'[\s\S]*?\'\'\'"
            analysis["docstrings"] = len(re.findall(docstring_pattern, content, re.DOTALL))

            # 简单圈复杂度估算（基于决策点）
            decision_points = 0
            for node in ast.walk(tree):
                if isinstance(
                    node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Try, ast.ExceptHandler)
                ):
                    decision_points += 1
                elif isinstance(node, ast.BoolOp):
                    decision_points += len(node.values) - 1

            analysis["cyclomatic_complexity"] = decision_points + 1

            # 认知复杂度简化评估（基于嵌套深度）
            max_depth = 0
            current_depth = 0

            for node in ast.walk(tree):
                if isinstance(
                    node, (ast.FunctionDef, ast.ClassDef, ast.If, ast.While, ast.For, ast.Try)
                ):
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif isinstance(node, ast.Return):
                    # 函数结束，减少深度
                    if current_depth > 0:
                        current_depth -= 1

            analysis["cognitive_complexity"] = max_depth
            analysis["max_nesting_depth"] = max_depth

        except Exception as e:
            analysis["error"] = str(e)

        return analysis

    def check_code_style(self, file_path: Path) -> Dict[str, Any]:
        """检查代码风格"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        issues = []
        lines = content.splitlines()

        # 检查行长度
        for i, line in enumerate(lines, 1):
            if len(line) > 120:  # PEP 8建议79，放宽到120
                issues.append(
                    {
                        "line": i,
                        "type": "line_too_long",
                        "description": f"行长度{len(line)}字符超过120限制",
                        "severity": "low",
                    }
                )

        # 检查导入顺序
        import_section = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                import_section = True
            elif import_section and stripped and not stripped.startswith("#"):
                # 导入部分之后有非注释代码
                if not stripped.startswith(("import ", "from ")):
                    issues.append(
                        {
                            "line": i,
                            "type": "import_order",
                            "description": "导入语句应该分组并排序",
                            "severity": "low",
                        }
                    )
                    break

        # 检查类型注解
        function_pattern = r"def\s+(\w+)\s*\((.*?)\)\s*(->\s*[\w\[\],\s]+)?:"
        functions = re.findall(function_pattern, content, re.DOTALL)
        for func_name, params, return_type in functions:
            if not return_type:
                issues.append(
                    {
                        "type": "missing_type_hint",
                        "description": f"函数'{func_name}'缺少返回类型注解",
                        "severity": "medium",
                    }
                )

        # 检查异常处理
        try_pattern = r"try:"
        except_pattern = r"except\s+(.*?):"

        try_blocks = list(re.finditer(try_pattern, content))
        for try_match in try_blocks:
            # 检查try块后是否有except
            after_try = content[try_match.end() :]
            if not re.search(except_pattern, after_try):
                issues.append(
                    {
                        "type": "bare_try",
                        "description": "try块缺少对应的except子句",
                        "severity": "high",
                    }
                )

        return {
            "total_issues": len(issues),
            "issues_by_type": Counter(issue["type"] for issue in issues),
            "issues_by_severity": Counter(issue["severity"] for issue in issues),
            "detailed_issues": issues[:20],  # 只显示前20个详细问题
        }

    def analyze_dependencies(self, file_path: Path) -> Dict[str, Any]:
        """分析文件依赖关系"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        dependencies = {
            "imports": [],
            "local_imports": [],
            "external_imports": [],
            "standard_library": [],
        }

        try:
            tree = ast.parse(content)

            standard_lib_modules = {
                "os",
                "sys",
                "json",
                "re",
                "datetime",
                "time",
                "pathlib",
                "typing",
                "collections",
                "itertools",
                "math",
                "statistics",
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                        dependencies["imports"].append(module)

                        if module in standard_lib_modules:
                            dependencies["standard_library"].append(module)
                        elif "." in module and module.split(".")[0] in standard_lib_modules:
                            dependencies["standard_library"].append(module)
                        elif module.startswith("."):
                            dependencies["local_imports"].append(module)
                        else:
                            dependencies["external_imports"].append(module)

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    dependencies["imports"].append(module)

                    if module in standard_lib_modules:
                        dependencies["standard_library"].append(module)
                    elif "." in module and module.split(".")[0] in standard_lib_modules:
                        dependencies["standard_library"].append(module)
                    elif module.startswith("."):
                        dependencies["local_imports"].append(module)
                    else:
                        dependencies["external_imports"].append(module)

        except Exception as e:
            dependencies["error"] = str(e)

        # 去重
        for key in dependencies:
            if isinstance(dependencies[key], list):
                dependencies[key] = list(set(dependencies[key]))

        return dependencies

    def calculate_maintainability_index(self, file_analysis: Dict[str, Any]) -> float:
        """计算可维护性指数（简化版本）"""
        lines = file_analysis.get("lines", 1)
        complexity = file_analysis.get("cyclomatic_complexity", 1)
        comments = file_analysis.get("comments", 0)

        # Halstead Volume简化估算
        halstead_volume = lines * math.log(lines + 1, 2)

        # 可维护性指数公式（简化）
        # MI = 171 - 5.2 * ln(Halstead Volume) - 0.23 * Cyclomatic Complexity - 16.2 * ln(Lines)
        try:
            mi = (
                171
                - 5.2 * math.log(halstead_volume + 1)
                - 0.23 * complexity
                - 16.2 * math.log(lines + 1)
            )
            # 调整注释比例影响
            comment_ratio = comments / lines if lines > 0 else 0
            mi += 50 * comment_ratio  # 注释越多，可维护性越高

            # 限制在0-100之间
            mi = max(0, min(100, mi))
        except:
            mi = 50  # 默认值

        return round(mi, 2)

    def run_audit(self) -> Dict[str, Any]:
        """运行综合代码质量审计"""
        print("=" * 80)
        print("🔍 代码质量详细审计开始")
        print("=" * 80)

        total_files = 0
        total_issues = 0
        file_analyses = {}

        # 审计所有核心文件
        for file_path_str in CORE_FILES:
            file_path = BASE_DIR / file_path_str

            if not file_path.exists():
                print(f"   ⚠️  文件不存在: {file_path}")
                continue

            print(f"\n📄 分析文件: {file_path_str}")

            # 文件复杂度分析
            complexity = self.analyze_file_complexity(file_path)

            # 代码风格检查
            style_issues = self.check_code_style(file_path)

            # 依赖分析
            dependencies = self.analyze_dependencies(file_path)

            # 计算可维护性指数
            maintainability = self.calculate_maintainability_index(complexity)

            # 综合文件分析
            file_analysis = {
                "complexity": complexity,
                "style_issues": style_issues,
                "dependencies": dependencies,
                "maintainability_index": maintainability,
                "overall_quality": self.assess_quality_level(
                    maintainability, style_issues["total_issues"]
                ),
            }

            file_analyses[file_path_str] = file_analysis

            total_files += 1
            total_issues += style_issues["total_issues"]

            # 打印摘要
            print(f"   行数: {complexity['lines']}")
            print(f"   函数数: {complexity['functions']}")
            print(f"   圈复杂度: {complexity['cyclomatic_complexity']}")
            print(f"   可维护性指数: {maintainability}/100")
            print(f"   代码风格问题: {style_issues['total_issues']}")

        # 生成汇总统计
        summary = self.generate_summary(file_analyses, total_files, total_issues)

        # 保存结果
        self.results["summary"] = summary
        self.results["file_analysis"] = file_analyses
        self.results["quality_metrics"] = self.calculate_quality_metrics(file_analyses)

        self.save_results()

        return self.results

    def assess_quality_level(self, maintainability: float, issue_count: int) -> str:
        """评估代码质量等级"""
        if maintainability >= 80 and issue_count == 0:
            return "EXCELLENT"
        elif maintainability >= 70 and issue_count <= 5:
            return "GOOD"
        elif maintainability >= 60 and issue_count <= 10:
            return "FAIR"
        elif maintainability >= 50:
            return "NEEDS_IMPROVEMENT"
        else:
            return "POOR"

    def generate_summary(
        self, file_analyses: Dict, total_files: int, total_issues: int
    ) -> Dict[str, Any]:
        """生成审计摘要"""
        maintainability_scores = [fa["maintainability_index"] for fa in file_analyses.values()]
        complexity_scores = [
            fa["complexity"]["cyclomatic_complexity"] for fa in file_analyses.values()
        ]

        # 统计质量等级
        quality_counts = Counter(fa["overall_quality"] for fa in file_analyses.values())

        summary = {
            "total_files_audited": total_files,
            "total_lines_of_code": sum(fa["complexity"]["lines"] for fa in file_analyses.values()),
            "total_functions": sum(fa["complexity"]["functions"] for fa in file_analyses.values()),
            "total_issues": total_issues,
            "average_maintainability": round(
                (
                    sum(maintainability_scores) / len(maintainability_scores)
                    if maintainability_scores
                    else 0
                ),
                2,
            ),
            "average_complexity": round(
                sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0, 2
            ),
            "quality_distribution": dict(quality_counts),
            "files_needing_attention": [
                file_path
                for file_path, fa in file_analyses.items()
                if fa["overall_quality"] in ["NEEDS_IMPROVEMENT", "POOR"]
            ],
        }

        return summary

    def calculate_quality_metrics(self, file_analyses: Dict) -> Dict[str, Any]:
        """计算质量指标"""
        metrics = {
            "maintainability_metrics": {},
            "complexity_metrics": {},
            "dependencies_metrics": {},
        }

        # 可维护性指标
        maintainability_scores = [fa["maintainability_index"] for fa in file_analyses.values()]
        if maintainability_scores:
            metrics["maintainability_metrics"] = {
                "min": min(maintainability_scores),
                "max": max(maintainability_scores),
                "average": round(sum(maintainability_scores) / len(maintainability_scores), 2),
                "distribution": self.calculate_distribution(
                    maintainability_scores, [20, 40, 60, 80]
                ),
            }

        # 复杂度指标
        complexity_scores = [
            fa["complexity"]["cyclomatic_complexity"] for fa in file_analyses.values()
        ]
        if complexity_scores:
            metrics["complexity_metrics"] = {
                "min": min(complexity_scores),
                "max": max(complexity_scores),
                "average": round(sum(complexity_scores) / len(complexity_scores), 2),
                "high_complexity_files": [
                    file_path
                    for file_path, fa in file_analyses.items()
                    if fa["complexity"]["cyclomatic_complexity"] > 15
                ],
            }

        # 依赖指标
        external_deps = []
        for file_path, fa in file_analyses.items():
            external_deps.extend(fa["dependencies"].get("external_imports", []))

        metrics["dependencies_metrics"] = {
            "unique_external_dependencies": list(set(external_deps)),
            "external_dependency_count": len(set(external_deps)),
            "most_common_external_deps": Counter(external_deps).most_common(10),
        }

        return metrics

    def calculate_distribution(
        self, values: List[float], thresholds: List[float]
    ) -> Dict[str, int]:
        """计算值在阈值区间的分布"""
        distribution = {f"below_{thresholds[0]}": 0}
        for i in range(len(thresholds)):
            if i < len(thresholds) - 1:
                key = f"{thresholds[i]}-{thresholds[i+1]}"
            else:
                key = f"above_{thresholds[-1]}"
            distribution[key] = 0

        for value in values:
            placed = False
            for i, threshold in enumerate(thresholds):
                if value < threshold:
                    if i == 0:
                        distribution[f"below_{thresholds[0]}"] += 1
                    else:
                        distribution[f"{thresholds[i-1]}-{thresholds[i]}"] += 1
                    placed = True
                    break
            if not placed:
                distribution[f"above_{thresholds[-1]}"] += 1

        return distribution

    def save_results(self):
        """保存审计结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细结果
        detailed_path = self.output_dir / f"code_quality_audit_{timestamp}.json"
        with open(detailed_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        # 生成执行摘要
        summary_path = self.output_dir / f"code_quality_summary_{timestamp}.md"
        self.generate_executive_summary(summary_path)

        print(f"\n📋 详细审计结果保存到: {detailed_path}")
        print(f"📋 执行摘要保存到: {summary_path}")

    def generate_executive_summary(self, output_path: Path):
        """生成执行摘要"""
        summary = self.results["summary"]
        metrics = self.results["quality_metrics"]

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# 代码质量审计报告\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n\n")

            f.write(f"## 📊 审计摘要\n")
            f.write(f"- **审计文件总数**: {summary['total_files_audited']}\n")
            f.write(f"- **总代码行数**: {summary['total_lines_of_code']}\n")
            f.write(f"- **总函数数**: {summary['total_functions']}\n")
            f.write(f"- **发现的问题总数**: {summary['total_issues']}\n")
            f.write(f"- **平均可维护性指数**: {summary['average_maintainability']}/100\n")
            f.write(f"- **平均圈复杂度**: {summary['average_complexity']}\n\n")

            f.write(f"## 🏆 质量等级分布\n")
            for quality, count in summary["quality_distribution"].items():
                percentage = (count / summary["total_files_audited"]) * 100
                f.write(f"- **{quality}**: {count}个文件 ({percentage:.1f}%)\n")

            if summary["files_needing_attention"]:
                f.write(f"\n## ⚠️ 需要关注的文件\n")
                for file_path in summary["files_needing_attention"]:
                    f.write(f"- `{file_path}`\n")

            f.write(f"\n## 📈 关键指标\n")
            if metrics.get("maintainability_metrics"):
                mm = metrics["maintainability_metrics"]
                f.write(f"### 可维护性指标\n")
                f.write(f"- **最低分**: {mm['min']}/100\n")
                f.write(f"- **最高分**: {mm['max']}/100\n")
                f.write(f"- **平均分**: {mm['average']}/100\n")

            if metrics.get("complexity_metrics"):
                cm = metrics["complexity_metrics"]
                f.write(f"\n### 复杂度指标\n")
                f.write(f"- **平均圈复杂度**: {cm['average']}\n")
                if cm.get("high_complexity_files"):
                    f.write(
                        f"- **高复杂度文件** (圈复杂度>15): {len(cm['high_complexity_files'])}个\n"
                    )

            f.write(f"\n## 🛠️ 改进建议\n")
            f.write(f"1. **高复杂度文件重构**: 优先重构圈复杂度超过15的文件\n")
            f.write(f"2. **代码风格统一**: 解决发现的所有代码风格问题\n")
            f.write(f"3. **增加测试覆盖**: 为重点文件增加单元测试\n")
            f.write(f"4. **依赖管理优化**: 减少不必要的外部依赖\n")
            f.write(f"5. **文档完善**: 为复杂函数增加文档字符串\n")


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 智能任务队列系统代码质量详细审计")
    print("=" * 80)

    auditor = CodeQualityAuditor()
    results = auditor.run_audit()

    print("\n" + "=" * 80)
    print("✅ 代码质量审计完成")
    print("=" * 80)

    summary = results["summary"]
    print(f"\n📋 审计结果摘要:")
    print(f"   审计文件数: {summary['total_files_audited']}")
    print(f"   总代码行数: {summary['total_lines_of_code']}")
    print(f"   发现问题数: {summary['total_issues']}")
    print(f"   平均可维护性: {summary['average_maintainability']}/100")
    print(f"   平均复杂度: {summary['average_complexity']}")

    # 显示需要关注的文件
    if summary["files_needing_attention"]:
        print(f"\n⚠️  需要关注的文件:")
        for file_path in summary["files_needing_attention"]:
            print(f"   - {file_path}")


if __name__ == "__main__":
    main()
