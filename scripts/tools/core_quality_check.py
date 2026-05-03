#!/usr/bin/env python3
"""
核心代码质量检查脚本

根据next_phase_engineering_plan_20260419.md计划，专注于核心重构代码的质量检查。
只检查与64卦状态系统相关的核心文件和测试文件。
"""

import os
import subprocess
import sys

# 核心代码文件列表（重点关注64卦状态系统）
CORE_FILES = [
    "hetu_hexagram_adapter.py",
    "enhanced_hetu_luoshu_scheduler.py",
    "integrated_hexagram_state_manager.py",
    "quality_gate.py",
]

# 测试文件列表
TEST_FILES = [
    "test_hetu_hexagram_adapter.py",
    "test_integrated_hexagram_system.py",
    "test_email_notification.py",
]

# 所有要检查的文件
ALL_FILES = CORE_FILES + TEST_FILES


def check_file_exists(files: list[str]) -> list[str]:
    """检查文件是否存在，返回存在的文件列表"""
    existing_files = []
    for file in files:
        if os.path.exists(file):
            existing_files.append(file)
        else:
            print(f"⚠️  文件不存在: {file}")
    return existing_files


def run_check(tool: str, args: list[str], files: list[str]) -> dict:
    """运行质量检查工具"""
    # 使用虚拟环境中的工具
    venv_tool = f"./venv/bin/{tool}"
    cmd = [venv_tool] + args + files
    print(f"运行: {' '.join(cmd[:5])}...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip() if result.stdout else "",
            "stderr": result.stderr.strip() if result.stderr else "",
            "has_errors": result.returncode != 0,
        }
    except Exception as e:
        return {
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": str(e),
            "has_errors": True,
        }


def print_result(check_name: str, result: dict):
    """打印检查结果"""
    if result["success"]:
        print(f"  ✅ {check_name}: 通过")
    else:
        print(f"  ❌ {check_name}: 失败 (退出码: {result['exit_code']})")
        if result["stdout"]:
            print(f"    输出: {result['stdout'][:200]}...")
        if result["stderr"]:
            print(f"    错误: {result['stderr'][:200]}...")


def main():
    """主函数"""
    print("🔧 OpenClaw 核心代码质量检查")
    print("=" * 60)
    print(f"检查文件: {', '.join(ALL_FILES)}")
    print()

    # 检查文件是否存在
    existing_files = check_file_exists(ALL_FILES)
    if not existing_files:
        print("❌ 没有找到要检查的文件")
        return False

    print(f"✅ 找到 {len(existing_files)}/{len(ALL_FILES)} 个文件")
    print()

    # 分离核心文件和测试文件
    core_existing_files = [f for f in existing_files if f in CORE_FILES]
    test_existing_files = [f for f in existing_files if f in TEST_FILES]

    print(f"📋 核心文件: {len(core_existing_files)} 个")
    print(f"📋 测试文件: {len(test_existing_files)} 个")
    print()

    results = {}

    # 1. flake8 代码规范检查
    print("1. 🔍 运行flake8代码规范检查...")
    results["flake8"] = run_check(
        "flake8", ["--max-line-length=100", "--extend-ignore=E203,W503"], existing_files
    )
    print_result("flake8", results["flake8"])

    # 2. mypy 类型检查（只检查核心文件）
    print("\n2. 🔍 运行mypy类型检查（核心文件）...")
    results["mypy"] = run_check(
        "mypy",
        [
            "--ignore-missing-imports",
            "--strict",
            "--follow-imports=skip",
            "--exclude",
            "mini_agent",
            "--exclude",
            "mini_agent/.*",
            "--exclude",
            ".*/mini_agent/.*",
        ],
        core_existing_files,
    )
    print_result("mypy", results["mypy"])

    # 3. black 代码格式化检查
    print("\n3. 🔍 运行black代码格式化检查...")
    results["black"] = run_check("black", ["--check", "--line-length=100"], existing_files)
    print_result("black", results["black"])

    # 4. isort 导入排序检查
    print("\n4. 🔍 运行isort导入排序检查...")
    results["isort"] = run_check("isort", ["--check-only", "--profile", "black"], existing_files)
    print_result("isort", results["isort"])

    # 总结
    print("\n" + "=" * 60)
    print("📊 核心代码质量检查总结:")

    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)

    print(f"  通过: {passed}/{total} 个检查")

    if passed == total:
        print("✅ 所有核心代码质量检查通过！")
        return True
    else:
        print("⚠️  发现质量问题，需要修复。")
        print("\n建议修复步骤:")
        print("1. 运行 black [文件名] 修复格式化问题")
        print("2. 运行 isort [文件名] 修复导入排序问题")
        print("3. 根据flake8输出修复代码规范问题")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
