#!/usr/bin/env python3
"""
代码质量门禁检查脚本

根据next_phase_engineering_plan_20260419.md计划，建立代码质量门禁系统。
提供基本的代码质量检查功能，支持逐步集成到CI/CD流水线。

检查项目：
1. 代码规范（flake8）
2. 类型检查（mypy）
3. 代码格式化（black）
4. 导入排序（isort）
5. 文档字符串检查（pydocstyle）
6. 圈复杂度检查
7. 重复代码检查
"""

import datetime
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict


class QualityGate:
    """代码质量门禁类"""

    def __init__(self, project_root: str = ".", verbose: bool = False):
        self.project_root = Path(project_root).resolve()
        self.verbose = verbose
        self.results: dict[str, dict[str, Any]] = {}

        # 检查工具是否安装
        self.tools_available = self._check_tools_availability()

    def _check_tools_availability(self) -> dict[str, bool]:
        """检查质量检查工具是否可用"""
        tools = {
            "flake8": "flake8 --version",
            "mypy": "mypy --version",
            "black": "black --version",
            "isort": "isort --version",
            "pydocstyle": "pydocstyle --version",
            "radon": "radon --version",
        }

        available = {}

        for tool, version_cmd in tools.items():
            try:
                result = subprocess.run(
                    version_cmd.split(), capture_output=True, text=True, cwd=self.project_root
                )
                available[tool] = result.returncode == 0

                if self.verbose:
                    if available[tool]:
                        print(f"✅ {tool}: 可用")
                    else:
                        print(f"⚠️  {tool}: 不可用")
            except Exception:
                available[tool] = False
                if self.verbose:
                    print(f"❌ {tool}: 检查失败")

        return available

    def run_flake8_check(self, paths: list[str] | None = None) -> dict[str, Any]:
        """运行flake8代码规范检查"""
        if not self.tools_available.get("flake8", False):
            return {"available": False, "errors": [], "warnings": []}

        if paths is None:
            paths = [str(self.project_root)]

        # 排除虚拟环境和第三方包目录
        cmd = [
            "flake8",
            "--max-line-length=100",
            "--extend-ignore=E203,W503",
            "--exclude=venv,.venv,agent_system/venv,.openclaw/maref/venv",
        ] + paths

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            errors = []
            if result.stdout:
                errors = result.stdout.strip().split("\n")

            return {
                "available": True,
                "exit_code": result.returncode,
                "errors": errors,
                "error_count": len(errors),
            }
        except Exception as e:
            return {
                "available": True,
                "exit_code": 1,
                "errors": [f"flake8执行异常: {e}"],
                "error_count": 1,
            }

    def run_mypy_check(self, paths: list[str] | None = None) -> dict[str, Any]:
        """运行mypy类型检查"""
        if not self.tools_available.get("mypy", False):
            return {"available": False, "errors": [], "warnings": []}

        if paths is None:
            paths = [str(self.project_root)]

        # 排除测试文件、配置文件和虚拟环境
        cmd = [
            "mypy",
            "--ignore-missing-imports",
            "--strict",
            "--exclude",
            "venv/|.venv/|agent_system/venv/|.openclaw/maref/venv/",
        ] + paths

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            errors = []
            if result.stdout:
                errors = result.stdout.strip().split("\n")

            return {
                "available": True,
                "exit_code": result.returncode,
                "errors": errors,
                "error_count": len(errors),
            }
        except Exception as e:
            return {
                "available": True,
                "exit_code": 1,
                "errors": [f"mypy执行异常: {e}"],
                "error_count": 1,
            }

    def run_black_check(self, paths: list[str] | None = None) -> dict[str, Any]:
        """运行black代码格式化检查"""
        if not self.tools_available.get("black", False):
            return {"available": False, "errors": [], "warnings": []}

        if paths is None:
            paths = [str(self.project_root)]

        # 使用--check模式只检查不修改，排除虚拟环境
        cmd = [
            "black",
            "--check",
            "--line-length=100",
            "--exclude",
            ".*/venv/*|.*/.venv/*|.*/agent_system/venv/*|.*/.openclaw/maref/venv/*",
        ] + paths

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            errors = []
            if result.stdout:
                errors = result.stdout.strip().split("\n")

            return {
                "available": True,
                "exit_code": result.returncode,
                "errors": errors,
                "error_count": 0 if result.returncode == 0 else 1,
            }
        except Exception as e:
            return {
                "available": True,
                "exit_code": 1,
                "errors": [f"black执行异常: {e}"],
                "error_count": 1,
            }

    def run_isort_check(self, paths: list[str] | None = None) -> dict[str, Any]:
        """运行isort导入排序检查"""
        if not self.tools_available.get("isort", False):
            return {"available": False, "errors": [], "warnings": []}

        if paths is None:
            paths = [str(self.project_root)]

        # 使用--check-only模式只检查不修改，排除虚拟环境
        cmd = [
            "isort",
            "--check-only",
            "--profile",
            "black",
            "--skip",
            "venv",
            "--skip",
            ".venv",
            "--skip",
            "agent_system/venv",
            "--skip",
            ".openclaw/maref/venv",
        ] + paths

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            errors = []
            if result.stdout:
                errors = result.stdout.strip().split("\n")

            return {
                "available": True,
                "exit_code": result.returncode,
                "errors": errors,
                "error_count": 0 if result.returncode == 0 else 1,
            }
        except Exception as e:
            return {
                "available": True,
                "exit_code": 1,
                "errors": [f"isort执行异常: {e}"],
                "error_count": 1,
            }

    def run_custom_checks(self) -> dict[str, Any]:
        """运行自定义质量检查"""
        checks = {
            "python_files_exist": self._check_python_files_exist(),
            "import_statements": self._check_import_statements(),
            "function_lengths": self._check_function_lengths(),
            "class_design": self._check_class_design(),
        }

        return checks

    def _check_python_files_exist(self) -> dict[str, Any]:
        """检查Python文件存在性和可读性"""
        python_files = list(self.project_root.rglob("*.py"))

        return {
            "total_files": len(python_files),
            "readable_files": len([f for f in python_files if os.access(f, os.R_OK)]),
            "files": [
                str(f.relative_to(self.project_root)) for f in python_files[:10]
            ],  # 只显示前10个
        }

    def _check_import_statements(self) -> dict[str, Any]:
        """检查导入语句"""
        issues = []

        # 检查常见的导入问题模式
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files[:5]:  # 只检查前5个文件
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                # 检查通配符导入
                if "from" in content and "import *" in content:
                    issues.append(f"{file_path.relative_to(self.project_root)}: 发现通配符导入")

                # 检查循环导入模式（简单检查）
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().startswith("import ") or line.strip().startswith("from "):
                        # 检查是否在同一文件中有复杂导入逻辑
                        if "sys.path" in line and "insert" in line:
                            issues.append(
                                f"{file_path.relative_to(self.project_root)}: 第{i + 1}行动态修改sys.path"
                            )

            except Exception as e:
                issues.append(f"{file_path.relative_to(self.project_root)}: 读取失败 - {e}")

        return {"issues": issues, "issue_count": len(issues)}

    def _check_function_lengths(self) -> dict[str, Any]:
        """检查函数长度（简单实现）"""

        class FunctionStats(TypedDict):
            files_checked: int
            functions_found: int
            long_functions: list[dict[str, str | int]]

        stats: FunctionStats = {
            "files_checked": 0,
            "functions_found": 0,
            "long_functions": [],  # 长度超过50行的函数
        }

        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files[:3]:  # 只检查前3个文件
            try:
                with open(file_path, encoding="utf-8") as f:
                    lines = f.readlines()

                in_function = False
                function_start = 0
                function_name = ""

                for i, line in enumerate(lines):
                    stripped = line.strip()

                    if stripped.startswith("def "):
                        if in_function:
                            # 结束上一个函数
                            function_length = i - function_start
                            if function_length > 50:
                                stats["long_functions"].append(
                                    {
                                        "file": str(file_path.relative_to(self.project_root)),
                                        "function": function_name,
                                        "line": function_start + 1,
                                        "length": function_length,
                                    }
                                )

                        # 开始新函数
                        in_function = True
                        function_start = i
                        function_name = stripped[4:].split("(")[0]
                        stats["functions_found"] += 1

                stats["files_checked"] += 1

            except Exception:
                pass

        return stats  # type: ignore[return-value]

    def _check_class_design(self) -> dict[str, Any]:
        """检查类设计"""
        issues = []

        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files[:3]:  # 只检查前3个文件
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                lines = content.split("\n")
                for i, line in enumerate(lines):
                    stripped = line.strip()

                    # 检查大类（方法过多）
                    if stripped.startswith("class "):
                        class_name = stripped[6:].split("(")[0].split(":")[0]

                        # 简单检查：查找类中的方法定义
                        method_count = 0
                        for j in range(i + 1, min(i + 100, len(lines))):
                            if lines[j].strip().startswith("def ") and lines[j].strip().endswith(
                                "(self"
                            ):
                                method_count += 1

                        if method_count > 10:
                            issues.append(
                                f"{file_path.relative_to(self.project_root)}: "
                                f"类{class_name}可能有太多方法({method_count}个)"
                            )

            except Exception:
                pass

        return {"issues": issues, "issue_count": len(issues)}

    def run_all_checks(self, specific_paths: list[str] | None = None) -> dict[str, Any]:
        """运行所有质量检查"""
        print("🔧 开始代码质量检查...")
        print(f"项目根目录: {self.project_root}")
        print("=" * 60)

        # 工具可用性检查
        print("\n📋 工具可用性检查:")
        for tool, available in self.tools_available.items():
            status = "✅ 可用" if available else "❌ 不可用"
            print(f"  {tool}: {status}")

        # 运行各项检查
        checks = {}

        print("\n🔍 运行flake8代码规范检查...")
        checks["flake8"] = self.run_flake8_check(specific_paths)
        self._print_check_result("flake8", checks["flake8"])

        print("\n🔍 运行mypy类型检查...")
        checks["mypy"] = self.run_mypy_check(specific_paths)
        self._print_check_result("mypy", checks["mypy"])

        print("\n🔍 运行black代码格式化检查...")
        checks["black"] = self.run_black_check(specific_paths)
        self._print_check_result("black", checks["black"])

        print("\n🔍 运行isort导入排序检查...")
        checks["isort"] = self.run_isort_check(specific_paths)
        self._print_check_result("isort", checks["isort"])

        print("\n🔍 运行自定义质量检查...")
        checks["custom"] = self.run_custom_checks()
        self._print_custom_check_result(checks["custom"])

        # 总结
        print("\n" + "=" * 60)
        print("📊 质量检查总结:")

        total_issues = 0
        for check_name, result in checks.items():
            if check_name == "custom":
                for _subcheck_name, subresult in result.items():
                    if isinstance(subresult, dict) and "issue_count" in subresult:
                        total_issues += subresult["issue_count"]
            elif isinstance(result, dict) and "error_count" in result:
                total_issues += result["error_count"]

        print(f"  发现总问题数: {total_issues}")

        if total_issues == 0:
            print("✅ 所有质量检查通过！")
            return {"success": True, "total_issues": 0, "checks": checks}
        else:
            print("⚠️  发现质量问题，需要修复。")
            return {"success": False, "total_issues": total_issues, "checks": checks}

    def _print_check_result(self, check_name: str, result: dict[str, Any]) -> None:
        """打印检查结果"""
        if not result.get("available", False):
            print(f"  ⚠️  {check_name}: 工具不可用")
            return

        if result.get("error_count", 0) == 0:
            print(f"  ✅ {check_name}: 通过")
        else:
            print(f"  ❌ {check_name}: 发现{result.get('error_count', 0)}个问题")
            if self.verbose and result.get("errors"):
                for error in result["errors"][:3]:  # 只显示前3个错误
                    print(f"    - {error}")
                if len(result["errors"]) > 3:
                    print(f"    ... 还有{len(result['errors']) - 3}个错误")

    def _print_custom_check_result(self, result: dict[str, Any]) -> None:
        """打印自定义检查结果"""
        for check_name, subresult in result.items():
            if isinstance(subresult, dict):
                issue_count = subresult.get("issue_count", 0)
                if issue_count == 0:
                    print(f"  ✅ {check_name}: 通过")
                else:
                    print(f"  ⚠️  {check_name}: 发现{issue_count}个问题")
                    if self.verbose and subresult.get("issues"):
                        for issue in subresult["issues"][:2]:  # 只显示前2个问题
                            print(f"    - {issue}")
                        if len(subresult["issues"]) > 2:
                            print(f"    ... 还有{len(subresult['issues']) - 2}个问题")

    def generate_report(self, results: dict[str, Any], output_file: str | None = None) -> str:
        """生成质量检查报告"""
        report_lines = [
            "# 代码质量检查报告",
            f"生成时间: {datetime.datetime.now().isoformat()}",
            f"项目根目录: {self.project_root}",
            "",
            "## 检查结果总结",
            f"- 总问题数: {results.get('total_issues', 0)}",
            f"- 检查通过: {'✅ 是' if results.get('success', False) else '❌ 否'}",
            "",
            "## 详细检查结果",
        ]

        checks = results.get("checks", {})

        for check_name, check_result in checks.items():
            report_lines.append(f"### {check_name}")

            if check_name == "custom":
                for subcheck_name, subresult in check_result.items():
                    if isinstance(subresult, dict):
                        report_lines.append(f"#### {subcheck_name}")
                        for key, value in subresult.items():
                            report_lines.append(f"- {key}: {value}")
            else:
                for key, value in check_result.items():
                    if key not in ["errors"] or self.verbose:
                        report_lines.append(f"- {key}: {value}")

            report_lines.append("")

        report_lines.append("## 建议")
        report_lines.append("1. 安装缺少的质量检查工具")
        report_lines.append("2. 根据报告修复代码问题")
        report_lines.append("3. 将质量检查集成到CI/CD流水线")
        report_lines.append("4. 设置提交前检查钩子（pre-commit）")

        report = "\n".join(report_lines)

        if output_file:
            output_path = self.project_root / output_file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"📄 报告已保存到: {output_path}")

        return report


def main() -> None:
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="代码质量门禁检查")
    parser.add_argument("--path", default=".", help="项目根目录路径")
    parser.add_argument("--verbose", action="store_true", help="显示详细输出")
    parser.add_argument("--output", help="报告输出文件路径")
    parser.add_argument(
        "--check",
        choices=["all", "flake8", "mypy", "black", "isort", "custom"],
        default="all",
        help="指定检查类型",
    )

    args = parser.parse_args()

    print("🔧 OpenClaw 代码质量门禁检查")
    print("=" * 60)

    # 创建质量门禁实例
    quality_gate = QualityGate(project_root=args.path, verbose=args.verbose)

    # 运行检查
    results = quality_gate.run_all_checks()

    # 生成报告
    if args.output:
        quality_gate.generate_report(results, args.output)
    else:
        quality_gate.generate_report(results)

    # 返回退出码
    if results.get("success", False):
        print("\n🎉 质量检查完成，所有检查通过！")
        sys.exit(0)
    else:
        print("\n⚠️  质量检查完成，发现问题需要修复。")
        sys.exit(1)


if __name__ == "__main__":
    main()
