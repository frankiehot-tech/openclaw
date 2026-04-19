#!/usr/bin/env python3
"""
MAREF自动化测试套件
运行所有MAREF组件测试并生成综合报告

测试覆盖：
1. 64卦状态管理器测试
2. 健康度计算器集成测试
3. 内存管理器测试
4. 监控器测试
5. 内存集成测试
6. 生产系统集成测试
"""

import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))


class MAREFTestRunner:
    """MAREF测试运行器"""

    def __init__(self, output_dir=None):
        self.test_results = []
        self.start_time = None
        self.end_time = None

        # 设置输出目录
        if output_dir is None:
            self.output_dir = Path.cwd() / "test_reports"
        else:
            self.output_dir = Path(output_dir)

        # 创建输出目录
        self.output_dir.mkdir(exist_ok=True)

        # 报告文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_file = self.output_dir / f"maref_test_report_{timestamp}.json"
        self.summary_file = self.output_dir / f"maref_test_summary_{timestamp}.txt"

    def run_test_module(self, module_name, test_func, description):
        """运行单个测试模块"""
        print(f"\n{'='*60}")
        print(f"运行测试: {description}")
        print(f"{'='*60}")

        start_time = time.time()
        result = {
            "module": module_name,
            "description": description,
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "status": "pending",
        }

        try:
            success = test_func()
            result["status"] = "passed" if success else "failed"
            result["success"] = success
            if success:
                print(f"✅ {description}: 通过")
            else:
                print(f"❌ {description}: 失败")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            print(f"💥 {description}: 异常 - {e}")

        end_time = time.time()
        result["end_time"] = datetime.fromtimestamp(end_time).isoformat()
        result["duration_seconds"] = round(end_time - start_time, 3)

        self.test_results.append(result)
        return result

    def run_state_transition_tests(self):
        """运行状态转换测试"""
        from test_state_transition_scenarios import main as run_state_tests

        def wrapper():
            try:
                run_state_tests()
                return True
            except SystemExit as e:
                # test_state_transition_scenarios.py在失败时调用sys.exit(1)
                return e.code == 0
            except Exception:
                return False

        return self.run_test_module("test_state_transition_scenarios", wrapper, "状态转换测试场景")

    def run_health_integration_tests(self):
        """运行健康度集成测试"""
        from test_health_integration import main as run_health_tests

        def wrapper():
            try:
                run_health_tests()
                return True
            except SystemExit as e:
                return e.code == 0
            except Exception:
                return False

        return self.run_test_module("test_health_integration", wrapper, "健康度计算器集成测试")

    def run_memory_integration_tests(self):
        """运行内存集成测试"""
        try:
            from maref_memory_integration import test_memory_integration
        except ImportError:
            print("⚠️  maref_memory_integration测试不可用")
            return {
                "module": "maref_memory_integration",
                "description": "内存集成测试",
                "status": "skipped",
                "reason": "模块不可用",
            }

        def wrapper():
            try:
                test_memory_integration()
                return True
            except Exception:
                return False

        return self.run_test_module("maref_memory_integration", wrapper, "内存集成测试")

    def run_monitor_tests(self):
        """运行监控器测试"""
        try:
            from maref_monitor import test_maref_monitor
        except ImportError:
            print("⚠️  maref_monitor测试不可用")
            return {
                "module": "maref_monitor",
                "description": "监控器测试",
                "status": "skipped",
                "reason": "模块不可用",
            }

        def wrapper():
            try:
                test_maref_monitor()
                return True
            except Exception:
                return False

        return self.run_test_module("maref_monitor", wrapper, "监控器测试")

    def run_memory_manager_tests(self):
        """运行内存管理器测试"""
        try:
            from maref_memory_manager import test_memory_manager
        except ImportError:
            print("⚠️  maref_memory_manager测试不可用")
            return {
                "module": "maref_memory_manager",
                "description": "内存管理器测试",
                "status": "skipped",
                "reason": "模块不可用",
            }

        def wrapper():
            try:
                test_memory_manager()
                return True
            except Exception:
                return False

        return self.run_test_module("maref_memory_manager", wrapper, "内存管理器测试")

    def run_health_calculator_tests(self):
        """运行健康度计算器测试"""
        try:
            from health_calculator import test_health_calculator
        except ImportError:
            print("⚠️  health_calculator测试不可用")
            return {
                "module": "health_calculator",
                "description": "健康度计算器测试",
                "status": "skipped",
                "reason": "模块不可用",
            }

        def wrapper():
            try:
                test_health_calculator()
                return True
            except Exception:
                return False

        return self.run_test_module("health_calculator", wrapper, "健康度计算器测试")

    def run_production_system_tests(self):
        """运行生产系统测试"""
        try:
            from test_maref_fix import test_maref_fix

            return self.run_test_module("test_maref_fix", test_maref_fix, "生产系统集成测试")
        except ImportError:
            # 尝试运行test_maref_fix.py作为脚本
            def wrapper():
                try:
                    result = subprocess.run(
                        [sys.executable, "test_maref_fix.py"],
                        capture_output=True,
                        text=True,
                        cwd=os.path.dirname(__file__),
                    )
                    return result.returncode == 0
                except Exception:
                    return False

            return self.run_test_module("test_maref_fix", wrapper, "生产系统集成测试")

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行MAREF自动化测试套件")
        print(f"时间: {datetime.now().isoformat()}")
        print(f"报告目录: {self.output_dir}")

        self.start_time = time.time()

        # 运行所有测试
        tests = [
            ("状态转换", self.run_state_transition_tests),
            ("健康度计算器", self.run_health_calculator_tests),
            ("健康度集成", self.run_health_integration_tests),
            ("内存管理器", self.run_memory_manager_tests),
            ("内存集成", self.run_memory_integration_tests),
            ("监控器", self.run_monitor_tests),
            ("生产系统", self.run_production_system_tests),
        ]

        for test_name, test_func in tests:
            test_func()

        self.end_time = time.time()

        # 生成报告
        self.generate_report()

        # 打印摘要
        self.print_summary()

        # 保存报告
        self.save_reports()

        # 返回总体结果
        return self.all_tests_passed()

    def all_tests_passed(self):
        """检查是否所有测试都通过"""
        passed = 0
        failed = 0
        errors = 0
        skipped = 0

        for result in self.test_results:
            if result.get("status") == "passed":
                passed += 1
            elif result.get("status") == "failed":
                failed += 1
            elif result.get("status") == "error":
                errors += 1
            elif result.get("status") == "skipped":
                skipped += 1

        total = passed + failed + errors
        return failed == 0 and errors == 0

    def generate_report(self):
        """生成测试报告"""
        total_duration = self.end_time - self.start_time if self.end_time else 0

        self.report = {
            "test_run": {
                "start_time": (
                    datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None
                ),
                "end_time": (
                    datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None
                ),
                "total_duration_seconds": round(total_duration, 3),
                "test_count": len(self.test_results),
            },
            "test_results": self.test_results,
            "summary": self.generate_summary_dict(),
        }

    def generate_summary_dict(self):
        """生成摘要字典"""
        passed = sum(1 for r in self.test_results if r.get("status") == "passed")
        failed = sum(1 for r in self.test_results if r.get("status") == "failed")
        errors = sum(1 for r in self.test_results if r.get("status") == "error")
        skipped = sum(1 for r in self.test_results if r.get("status") == "skipped")

        total = passed + failed + errors

        return {
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "total": total,
            "success_rate": passed / total if total > 0 else 0,
            "all_passed": failed == 0 and errors == 0,
        }

    def print_summary(self):
        """打印测试摘要"""
        summary = self.generate_summary_dict()

        print(f"\n{'='*60}")
        print("MAREF测试套件完成")
        print(f"{'='*60}")

        print(f"\n📊 测试结果摘要:")
        print(f"   通过: {summary['passed']}")
        print(f"   失败: {summary['failed']}")
        print(f"   错误: {summary['errors']}")
        print(f"   跳过: {summary['skipped']}")
        print(f"   总计: {summary['total']}")
        print(f"   成功率: {summary['success_rate']:.1%}")

        print(f"\n⏱️  执行时间:")
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            print(f"   开始: {datetime.fromtimestamp(self.start_time).isoformat()}")
            print(f"   结束: {datetime.fromtimestamp(self.end_time).isoformat()}")
            print(f"   耗时: {duration:.2f} 秒")

        print(f"\n📋 详细结果:")
        for i, result in enumerate(self.test_results, 1):
            status_icon = (
                "✅"
                if result.get("status") == "passed"
                else (
                    "❌"
                    if result.get("status") == "failed"
                    else (
                        "💥"
                        if result.get("status") == "error"
                        else "⚠️ " if result.get("status") == "skipped" else "❓"
                    )
                )
            )

            duration = result.get("duration_seconds", "N/A")
            if isinstance(duration, (int, float)):
                duration = f"{duration:.2f}s"

            print(
                f"   {i:2d}. {status_icon} {result['description']:<20} {result.get('status', 'unknown'):<10} {duration}"
            )

        if summary["all_passed"]:
            print(f"\n🎉 所有测试通过！MAREF系统运行正常")
        else:
            print(f"\n⚠️  部分测试失败，需要检查")

    def save_reports(self):
        """保存报告到文件"""
        # 保存JSON报告
        with open(self.report_file, "w", encoding="utf-8") as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)

        # 保存文本摘要
        with open(self.summary_file, "w", encoding="utf-8") as f:
            f.write(f"MAREF测试套件报告\n")
            f.write(f"生成时间: {datetime.now().isoformat()}\n")
            f.write(f"=" * 60 + "\n\n")

            summary = self.generate_summary_dict()
            f.write(f"测试结果摘要:\n")
            f.write(f"  通过: {summary['passed']}\n")
            f.write(f"  失败: {summary['failed']}\n")
            f.write(f"  错误: {summary['errors']}\n")
            f.write(f"  跳过: {summary['skipped']}\n")
            f.write(f"  总计: {summary['total']}\n")
            f.write(f"  成功率: {summary['success_rate']:.1%}\n\n")

            f.write(f"详细结果:\n")
            for i, result in enumerate(self.test_results, 1):
                status_icon = (
                    "✅"
                    if result.get("status") == "passed"
                    else (
                        "❌"
                        if result.get("status") == "failed"
                        else (
                            "💥"
                            if result.get("status") == "error"
                            else "⚠️ " if result.get("status") == "skipped" else "❓"
                        )
                    )
                )

                duration = result.get("duration_seconds", "N/A")
                if isinstance(duration, (int, float)):
                    duration = f"{duration:.2f}s"

                f.write(
                    f"  {i:2d}. {status_icon} {result['description']:<20} {result.get('status', 'unknown'):<10} {duration}\n"
                )

            f.write(f"\n")
            if summary["all_passed"]:
                f.write("🎉 所有测试通过！MAREF系统运行正常\n")
            else:
                f.write("⚠️  部分测试失败，需要检查\n")

        print(f"\n📄 报告已保存:")
        print(f"   JSON报告: {self.report_file}")
        print(f"   文本摘要: {self.summary_file}")


def main():
    """主函数"""
    runner = MAREFTestRunner()

    try:
        all_passed = runner.run_all_tests()

        if all_passed:
            print("\n✨ MAREF自动化测试套件执行完成，所有测试通过")
            return 0
        else:
            print("\n❌ MAREF自动化测试套件执行完成，部分测试失败")
            return 1

    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
        return 130
    except Exception as e:
        print(f"\n💥 测试运行器异常: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
