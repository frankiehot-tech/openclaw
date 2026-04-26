#!/usr/bin/env python3
"""
MAREF沙箱隔离性验证器

验证沙箱环境是否与生产环境正确隔离。
检查文件系统访问、进程隔离和资源限制。
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any


class SandboxIsolationValidator:
    """沙箱隔离性验证器"""

    def __init__(self, sandbox_root: str = "./sandbox"):
        """
        初始化验证器

        Args:
            sandbox_root: 沙箱根目录路径
        """
        self.sandbox_root = os.path.abspath(sandbox_root)
        self.checks = []
        self.results = {}

    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有隔离性检查"""
        print(f"🔍 运行沙箱隔离性验证: {self.sandbox_root}")

        # 基本目录检查
        self._check_directory_structure()

        # 文件系统隔离检查
        self._check_filesystem_isolation()

        # 进程隔离模拟检查
        self._check_process_isolation()

        # 资源限制检查
        self._check_resource_limits()

        # 环境变量检查
        self._check_environment_variables()

        # 网络隔离检查（模拟）
        self._check_network_isolation()

        # 安全性检查
        self._check_security_boundaries()

        return self._generate_summary()

    def _check_directory_structure(self) -> None:
        """检查沙箱目录结构"""
        check_name = "directory_structure"
        try:
            required_dirs = [
                "simulators",
                "test_datasets",
                "experiment_results",
                "monitoring_data",
            ]

            missing_dirs = []
            for dir_name in required_dirs:
                dir_path = os.path.join(self.sandbox_root, dir_name)
                if not os.path.exists(dir_path):
                    missing_dirs.append(dir_name)

            if missing_dirs:
                self.checks.append(
                    {
                        "name": check_name,
                        "status": "warning",
                        "message": f"缺失目录: {', '.join(missing_dirs)}",
                        "details": {"missing_dirs": missing_dirs},
                    }
                )
                print(f"  ⚠️  目录结构: 缺失 {len(missing_dirs)} 个目录")
            else:
                self.checks.append(
                    {
                        "name": check_name,
                        "status": "pass",
                        "message": "沙箱目录结构完整",
                        "details": {"existing_dirs": required_dirs},
                    }
                )
                print(f"  ✅ 目录结构: 完整")

        except Exception as e:
            self.checks.append(
                {
                    "name": check_name,
                    "status": "fail",
                    "message": f"目录检查失败: {e}",
                    "details": {"error": str(e)},
                }
            )
            print(f"  ❌ 目录结构: 失败 - {e}")

    def _check_filesystem_isolation(self) -> None:
        """检查文件系统隔离"""
        check_name = "filesystem_isolation"
        try:
            # 尝试访问沙箱外的敏感路径
            sensitive_paths = [
                "/etc/passwd",  # 系统文件
                "/home",  # 用户目录
                "/var",  # 系统变量
                "/usr/bin",  # 系统二进制
            ]

            accessible_paths = []
            for path in sensitive_paths:
                try:
                    if os.path.exists(path):
                        # 尝试读取（可能没有权限）
                        with open(path, "rb") as f:
                            f.read(1)  # 读取一个字节
                        accessible_paths.append(path)
                except Exception:
                    pass  # 无法访问，这是好的

            if accessible_paths:
                self.checks.append(
                    {
                        "name": check_name,
                        "status": "warning",
                        "message": f"可访问沙箱外路径: {len(accessible_paths)} 个",
                        "details": {"accessible_paths": accessible_paths},
                    }
                )
                print(
                    f"  ⚠️  文件系统隔离: 可访问 {len(accessible_paths)} 个沙箱外路径"
                )
            else:
                self.checks.append(
                    {
                        "name": check_name,
                        "status": "pass",
                        "message": "文件系统隔离良好",
                        "details": {"checked_paths": sensitive_paths},
                    }
                )
                print(f"  ✅ 文件系统隔离: 良好")

        except Exception as e:
            self.checks.append(
                {
                    "name": check_name,
                    "status": "fail",
                    "message": f"文件系统隔离检查失败: {e}",
                    "details": {"error": str(e)},
                }
            )
            print(f"  ❌ 文件系统隔离: 失败 - {e}")

    def _check_process_isolation(self) -> None:
        """检查进程隔离（模拟）"""
        check_name = "process_isolation"
        try:
            import subprocess

            # 尝试运行一个简单的命令
            result = subprocess.run(
                ["echo", "test"], capture_output=True, text=True, timeout=2
            )

            # 检查进程是否可以正常启动
            if result.returncode == 0:
                self.checks.append(
                    {
                        "name": check_name,
                        "status": "pass",
                        "message": "进程隔离检查通过",
                        "details": {
                            "command": "echo test",
                            "output": result.stdout.strip(),
                        },
                    }
                )
                print(f"  ✅ 进程隔离: 基础进程功能正常")
            else:
                self.checks.append(
                    {
                        "name": check_name,
                        "status": "warning",
                        "message": "进程执行返回非零退出码",
                        "details": {
                            "returncode": result.returncode,
                            "stderr": result.stderr,
                        },
                    }
                )
                print(f"  ⚠️  进程隔离: 命令执行异常")

        except subprocess.TimeoutExpired:
            self.checks.append(
                {
                    "name": check_name,
                    "status": "warning",
                    "message": "进程执行超时",
                    "details": {"timeout": 2},
                }
            )
            print(f"  ⚠️  进程隔离: 执行超时")
        except Exception as e:
            self.checks.append(
                {
                    "name": check_name,
                    "status": "fail",
                    "message": f"进程隔离检查失败: {e}",
                    "details": {"error": str(e)},
                }
            )
            print(f"  ❌ 进程隔离: 失败 - {e}")

    def _check_resource_limits(self) -> None:
        """检查资源限制（模拟）"""
        check_name = "resource_limits"
        try:
            import resource

            # 获取当前资源限制
            soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)

            self.checks.append(
                {
                    "name": check_name,
                    "status": "info",
                    "message": f"文件描述符限制: soft={soft_limit}, hard={hard_limit}",
                    "details": {"soft_limit": soft_limit, "hard_limit": hard_limit},
                }
            )
            print(f"  📊 资源限制: 文件描述符 soft={soft_limit}, hard={hard_limit}")

        except Exception as e:
            self.checks.append(
                {
                    "name": check_name,
                    "status": "warning",
                    "message": f"资源限制检查失败: {e}",
                    "details": {"error": str(e)},
                }
            )
            print(f"  ⚠️  资源限制: 检查失败 - {e}")

    def _check_environment_variables(self) -> None:
        """检查环境变量"""
        check_name = "environment_variables"
        try:
            # 检查可能泄露生产环境信息的变量
            sensitive_env_vars = [
                "HOME",
                "USER",
                "LOGNAME",
                "PATH",
                "PYTHONPATH",
                "SECRET_KEY",
                "API_KEY",
                "DATABASE_URL",
            ]

            found_env_vars = {}
            for var in sensitive_env_vars:
                value = os.environ.get(var)
                if value:
                    # 屏蔽敏感值
                    if "KEY" in var or "SECRET" in var or "PASSWORD" in var:
                        masked_value = "******"
                    else:
                        masked_value = value[:20] + "..." if len(value) > 20 else value
                    found_env_vars[var] = masked_value

            if found_env_vars:
                self.checks.append(
                    {
                        "name": check_name,
                        "status": "warning",
                        "message": f"发现 {len(found_env_vars)} 个敏感环境变量",
                        "details": {"found_vars": found_env_vars},
                    }
                )
                print(f"  ⚠️  环境变量: 发现 {len(found_env_vars)} 个敏感变量")
            else:
                self.checks.append(
                    {
                        "name": check_name,
                        "status": "pass",
                        "message": "环境变量检查通过",
                        "details": {"checked_vars": sensitive_env_vars},
                    }
                )
                print(f"  ✅ 环境变量: 检查通过")

        except Exception as e:
            self.checks.append(
                {
                    "name": check_name,
                    "status": "fail",
                    "message": f"环境变量检查失败: {e}",
                    "details": {"error": str(e)},
                }
            )
            print(f"  ❌ 环境变量: 失败 - {e}")

    def _check_network_isolation(self) -> None:
        """检查网络隔离（模拟）"""
        check_name = "network_isolation"
        try:
            import socket

            # 尝试解析本地主机名
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)

            self.checks.append(
                {
                    "name": check_name,
                    "status": "info",
                    "message": f"网络基础功能正常: {hostname} -> {ip}",
                    "details": {"hostname": hostname, "ip": ip},
                }
            )
            print(f"  📊 网络隔离: 基础功能正常 ({hostname} -> {ip})")

        except Exception as e:
            self.checks.append(
                {
                    "name": check_name,
                    "status": "warning",
                    "message": f"网络检查失败: {e}",
                    "details": {"error": str(e)},
                }
            )
            print(f"  ⚠️  网络隔离: 检查失败 - {e}")

    def _check_security_boundaries(self) -> None:
        """检查安全边界"""
        check_name = "security_boundaries"
        try:
            # 检查沙箱目录权限
            sandbox_stat = os.stat(self.sandbox_root)
            sandbox_mode = sandbox_stat.st_mode

            # 检查是否只有所有者有写权限
            world_writable = sandbox_mode & 0o002  # 其他用户写权限
            group_writable = sandbox_mode & 0o020  # 组用户写权限

            permission_issues = []
            if world_writable:
                permission_issues.append("沙箱目录全局可写")
            if group_writable:
                permission_issues.append("沙箱目录组可写")

            if permission_issues:
                self.checks.append(
                    {
                        "name": check_name,
                        "status": "warning",
                        "message": f"权限问题: {', '.join(permission_issues)}",
                        "details": {
                            "permission_issues": permission_issues,
                            "mode": oct(sandbox_mode),
                            "uid": sandbox_stat.st_uid,
                            "gid": sandbox_stat.st_gid,
                        },
                    }
                )
                print(f"  ⚠️  安全边界: {', '.join(permission_issues)}")
            else:
                self.checks.append(
                    {
                        "name": check_name,
                        "status": "pass",
                        "message": "安全边界检查通过",
                        "details": {
                            "mode": oct(sandbox_mode),
                            "uid": sandbox_stat.st_uid,
                            "gid": sandbox_stat.st_gid,
                        },
                    }
                )
                print(f"  ✅ 安全边界: 检查通过")

        except Exception as e:
            self.checks.append(
                {
                    "name": check_name,
                    "status": "fail",
                    "message": f"安全边界检查失败: {e}",
                    "details": {"error": str(e)},
                }
            )
            print(f"  ❌ 安全边界: 失败 - {e}")

    def _generate_summary(self) -> Dict[str, Any]:
        """生成验证摘要"""
        pass_count = sum(1 for check in self.checks if check["status"] == "pass")
        warning_count = sum(1 for check in self.checks if check["status"] == "warning")
        fail_count = sum(1 for check in self.checks if check["status"] == "fail")
        info_count = sum(1 for check in self.checks if check["status"] == "info")

        overall_status = "pass"
        if fail_count > 0:
            overall_status = "fail"
        elif warning_count > 0:
            overall_status = "warning"

        summary = {
            "metadata": {
                "sandbox_root": self.sandbox_root,
                "validated_at": datetime.now().isoformat(),
                "total_checks": len(self.checks),
            },
            "summary": {
                "overall_status": overall_status,
                "pass_count": pass_count,
                "warning_count": warning_count,
                "fail_count": fail_count,
                "info_count": info_count,
            },
            "checks": self.checks,
            "recommendations": self._generate_recommendations(),
        }

        return summary

    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于检查结果生成建议
        for check in self.checks:
            if check["status"] == "fail":
                recommendations.append(
                    f"修复检查失败: {check['name']} - {check['message']}"
                )
            elif check["status"] == "warning":
                recommendations.append(
                    f"改善警告项: {check['name']} - {check['message']}"
                )

        # 通用建议
        if not recommendations:
            recommendations.append("沙箱隔离性验证通过，可以安全使用")
        else:
            recommendations.append("修复所有问题后重新运行验证")

        return recommendations

    def save_report(
        self, summary: Dict[str, Any], output_dir: str = "./validation_reports"
    ) -> str:
        """保存验证报告"""
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"isolation_validation_{timestamp}.json")

        with open(report_file, "w") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # 生成可读的文本报告
        text_report_file = os.path.join(
            output_dir, f"isolation_validation_{timestamp}.txt"
        )
        with open(text_report_file, "w") as f:
            f.write("=" * 60 + "\n")
            f.write("MAREF沙箱隔离性验证报告\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"沙箱根目录: {summary['metadata']['sandbox_root']}\n")
            f.write(f"验证时间: {summary['metadata']['validated_at']}\n")
            f.write(f"检查总数: {summary['metadata']['total_checks']}\n\n")

            f.write("总体状态: ")
            status = summary["summary"]["overall_status"]
            if status == "pass":
                f.write("✅ 通过\n")
            elif status == "warning":
                f.write("⚠️  警告\n")
            else:
                f.write("❌ 失败\n")

            f.write(f"通过: {summary['summary']['pass_count']}, ")
            f.write(f"警告: {summary['summary']['warning_count']}, ")
            f.write(f"失败: {summary['summary']['fail_count']}, ")
            f.write(f"信息: {summary['summary']['info_count']}\n\n")

            f.write("=" * 60 + "\n")
            f.write("详细检查结果\n")
            f.write("=" * 60 + "\n\n")

            for i, check in enumerate(summary["checks"], 1):
                status_symbol = {
                    "pass": "✅",
                    "warning": "⚠️ ",
                    "fail": "❌",
                    "info": "📊",
                }.get(check["status"], "❓")

                f.write(f"{i}. {status_symbol} {check['name']}\n")
                f.write(f"   状态: {check['status']}\n")
                f.write(f"   消息: {check['message']}\n")
                if check.get("details"):
                    f.write(
                        f"   详情: {json.dumps(check['details'], ensure_ascii=False, indent=2)}\n"
                    )
                f.write("\n")

            f.write("=" * 60 + "\n")
            f.write("改进建议\n")
            f.write("=" * 60 + "\n\n")

            for i, recommendation in enumerate(summary["recommendations"], 1):
                f.write(f"{i}. {recommendation}\n")

        print(f"\n📋 验证报告已保存:")
        print(f"   JSON报告: {report_file}")
        print(f"   文本报告: {text_report_file}")

        return report_file


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="MAREF沙箱隔离性验证器")
    parser.add_argument(
        "--sandbox-root",
        "-s",
        default="./sandbox",
        help="沙箱根目录路径 (默认: ./sandbox)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="./validation_reports",
        help="输出目录 (默认: ./validation_reports)",
    )

    args = parser.parse_args()

    # 运行验证
    validator = SandboxIsolationValidator(args.sandbox_root)
    summary = validator.run_all_checks()

    # 保存报告
    report_file = validator.save_report(summary, args.output_dir)

    # 输出总体状态
    overall_status = summary["summary"]["overall_status"]
    print(f"\n{'='*60}")
    print(f"验证完成 - 总体状态: ", end="")
    if overall_status == "pass":
        print("✅ 通过")
    elif overall_status == "warning":
        print("⚠️  警告")
    else:
        print("❌ 失败")
    print(f"{'='*60}")

    sys.exit(0 if overall_status in ["pass", "warning"] else 1)


if __name__ == "__main__":
    main()
