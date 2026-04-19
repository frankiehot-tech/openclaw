#!/usr/bin/env python3
"""GSD V2 环境准备检查脚本"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class GSDV2EnvironmentChecker:
    """GSD V2 环境检查器"""

    def __init__(self):
        self.base_dir = Path("/Volumes/1TB-M2/openclaw")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "overall_status": "pending",
            "recommendations": [],
        }

    def check_claude_code_router(self):
        """检查Claude Code Router状态"""
        try:
            # 检查服务状态
            result = subprocess.run(["ccr", "status"], capture_output=True, text=True)

            if "Running" in result.stdout:
                self.results["checks"]["claude_code_router"] = {
                    "status": "healthy",
                    "details": "服务正常运行",
                }
            else:
                self.results["checks"]["claude_code_router"] = {
                    "status": "not_running",
                    "details": "服务未运行，需要启动",
                }
                self.results["recommendations"].append("启动Claude Code Router: ccr start")

        except Exception as e:
            self.results["checks"]["claude_code_router"] = {
                "status": "error",
                "details": f"检查失败: {str(e)}",
            }

    def check_aiplan_system(self):
        """检查AIplan系统状态"""
        try:
            # 检查AIplan相关目录和文件
            aiplan_dirs = [".openclaw/plan_queue", "workspace", "scripts"]

            missing_dirs = []
            for dir_path in aiplan_dirs:
                if not (self.base_dir / dir_path).exists():
                    missing_dirs.append(dir_path)

            if not missing_dirs:
                self.results["checks"]["aiplan_system"] = {
                    "status": "healthy",
                    "details": "AIplan系统目录结构完整",
                }
            else:
                self.results["checks"]["aiplan_system"] = {
                    "status": "incomplete",
                    "details": f"缺失目录: {', '.join(missing_dirs)}",
                }
                self.results["recommendations"].append("创建缺失的AIplan目录结构")

        except Exception as e:
            self.results["checks"]["aiplan_system"] = {
                "status": "error",
                "details": f"检查失败: {str(e)}",
            }

    def check_python_environment(self):
        """检查Python环境"""
        try:
            # 检查Python版本和关键包
            python_version = sys.version_info
            required_packages = ["psutil", "requests", "pyyaml"]

            missing_packages = []
            for package in required_packages:
                try:
                    __import__(package)
                except ImportError:
                    missing_packages.append(package)

            if python_version >= (3, 8) and not missing_packages:
                self.results["checks"]["python_environment"] = {
                    "status": "healthy",
                    "details": f"Python {python_version.major}.{python_version.minor} 环境正常",
                }
            else:
                details = []
                if python_version < (3, 8):
                    details.append("Python版本需要3.8+")
                if missing_packages:
                    details.append(f"缺失包: {', '.join(missing_packages)}")

                self.results["checks"]["python_environment"] = {
                    "status": "needs_improvement",
                    "details": "; ".join(details),
                }
                self.results["recommendations"].append("安装缺失的Python包")

        except Exception as e:
            self.results["checks"]["python_environment"] = {
                "status": "error",
                "details": f"检查失败: {str(e)}",
            }

    def check_file_permissions(self):
        """检查文件权限"""
        try:
            critical_paths = ["scripts", ".openclaw", "workspace"]

            permission_issues = []
            for path in critical_paths:
                full_path = self.base_dir / path
                if full_path.exists():
                    # 检查读写权限
                    if not os.access(full_path, os.R_OK | os.W_OK):
                        permission_issues.append(path)

            if not permission_issues:
                self.results["checks"]["file_permissions"] = {
                    "status": "healthy",
                    "details": "关键目录权限正常",
                }
            else:
                self.results["checks"]["file_permissions"] = {
                    "status": "needs_fix",
                    "details": f"权限问题: {', '.join(permission_issues)}",
                }
                self.results["recommendations"].append("修复文件权限问题")

        except Exception as e:
            self.results["checks"]["file_permissions"] = {
                "status": "error",
                "details": f"检查失败: {str(e)}",
            }

    def run_all_checks(self):
        """运行所有环境检查"""
        print("🔍 开始GSD V2环境检查...")

        checks = [
            ("Claude Code Router", self.check_claude_code_router),
            ("AIplan系统", self.check_aiplan_system),
            ("Python环境", self.check_python_environment),
            ("文件权限", self.check_file_permissions),
        ]

        for check_name, check_func in checks:
            print(f"🧪 检查: {check_name}")
            check_func()

        # 评估总体状态
        status_counts = {}
        for check_result in self.results["checks"].values():
            status = check_result["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        if status_counts.get("error", 0) > 0:
            self.results["overall_status"] = "critical"
        elif status_counts.get("needs_fix", 0) > 0 or status_counts.get("not_running", 0) > 0:
            self.results["overall_status"] = "needs_attention"
        elif status_counts.get("needs_improvement", 0) > 0:
            self.results["overall_status"] = "acceptable"
        else:
            self.results["overall_status"] = "ready"

        return self.results

    def generate_report(self):
        """生成环境检查报告"""
        report = f"""# GSD V2 环境检查报告

**检查时间**: {self.results['timestamp']}
**总体状态**: {self.results['overall_status'].upper()}

## 📊 检查结果汇总

"""

        # 添加检查结果
        for check_name, check_result in self.results["checks"].items():
            status_emoji = {
                "healthy": "✅",
                "acceptable": "⚠️",
                "needs_improvement": "🔄",
                "needs_fix": "🔧",
                "not_running": "🚫",
                "error": "❌",
            }.get(check_result["status"], "❓")

            report += f"{status_emoji} **{check_name.replace('_', ' ').title()}**: {check_result['details']}\n\n"

        # 添加建议
        if self.results["recommendations"]:
            report += "## 💡 建议行动\n\n"
            for rec in self.results["recommendations"]:
                report += f"- {rec}\n"

        # 添加下一步行动
        next_actions = {
            "critical": "立即解决关键问题",
            "needs_attention": "处理需要关注的问题",
            "acceptable": "可以开始实施，但建议优化",
            "ready": "环境准备就绪，可以开始实施",
        }

        report += (
            f"\n## 🚀 下一步行动\n\n{next_actions.get(self.results['overall_status'], '未知状态')}"
        )

        return report


def main():
    """主函数"""
    checker = GSDV2EnvironmentChecker()
    results = checker.run_all_checks()

    # 生成并保存报告
    report = checker.generate_report()

    # 输出到控制台
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    # 保存到文件
    report_dir = Path("/Volumes/1TB-M2/openclaw/workspace/gsd_v2_preparation")
    report_dir.mkdir(parents=True, exist_ok=True)

    report_file = report_dir / "environment_check_report.md"
    with open(report_file, "w") as f:
        f.write(report)

    print(f"\n📁 详细报告已保存到: {report_file}")

    # 返回退出码
    if results["overall_status"] in ["critical", "needs_attention"]:
        return 1
    else:
        return 0


if __name__ == "__main__":
    exit(main())
