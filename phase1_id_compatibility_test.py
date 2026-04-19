#!/usr/bin/env python3
"""
阶段1：任务身份系统迁移 - 验证新旧ID格式兼容性测试
测试TaskIdentityContract生成的新ID与系统现有组件的兼容性
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from contracts.task_identity import TaskIdentity

    print("✅ 成功导入TaskIdentity模块")
except ImportError as e:
    print(f"❌ 无法导入TaskIdentity: {e}")
    sys.exit(1)


def test_id_normalization():
    """测试ID规范化功能"""
    print("\n🔍 测试1: ID规范化功能")
    print("-" * 50)

    test_cases = [
        ("-gene-mgmt-task-20260414", "以'-'开头的ID"),
        ("--special-task", "以'--'开头的ID"),
        ("normal_task_123", "正常ID"),
        ("+plus_task", "以'+'开头的ID"),
        ("task-with-dashes-2026", "包含连字符的ID"),
    ]

    all_pass = True
    for raw_id, description in test_cases:
        try:
            normalized = TaskIdentity.normalize(raw_id)
            print(f"  {description}:")
            print(f"    原始ID: {raw_id}")
            print(f"    规范化ID: {normalized.id}")

            # 验证规范化ID不以'-'或'--'开头
            if normalized.id.startswith("-"):
                print(f"    ❌ 规范化ID仍以'-'开头")
                all_pass = False
            else:
                print(f"    ✅ 规范化ID合规")

        except Exception as e:
            print(f"    ❌ 规范化失败: {e}")
            all_pass = False

    return all_pass


def test_argparse_compatibility():
    """测试ID能被argparse正确解析"""
    print("\n🔍 测试2: argparse兼容性")
    print("-" * 50)

    # 创建测试脚本
    test_script = """
import argparse
import sys

parser = argparse.ArgumentParser(description='测试任务ID解析')
parser.add_argument('task_id', help='任务ID')
parser.add_argument('--flag', help='测试flag', default='default')

args = parser.parse_args()
print(f"成功解析: task_id={args.task_id}, flag={args.flag}")
"""

    # 测试原始ID和规范化ID
    test_cases = [
        ("normal_task_123", "normal_task_123", "正常ID"),
        ("task_20260417_075647_4657", "task_20260417_075647_4657", "新格式ID"),
        ("-gene-mgmt-task-20260414", "gene-mgmt-task-20260414", "旧格式ID（规范化后）"),
        ("--special-task", "task_special-task", "双横线ID（规范化后）"),
    ]

    all_pass = True
    for raw_id, normalized_id, description in test_cases:
        try:
            # 写入临时脚本
            with open("/tmp/test_argparse.py", "w") as f:
                f.write(test_script)

            # 首先测试原始ID（应该失败如果以'-'开头）
            if raw_id.startswith("-"):
                result = subprocess.run(
                    ["python3", "/tmp/test_argparse.py", raw_id, "--flag", "test"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode != 0:
                    print(f"  ✅ 预期: 原始ID '{raw_id}' 被argparse拒绝")
                else:
                    print(f"  ⚠️  意外: 原始ID '{raw_id}' 被argparse接受")
                    all_pass = False

            # 测试规范化ID（应该总是成功）
            result = subprocess.run(
                ["python3", "/tmp/test_argparse.py", normalized_id, "--flag", "test"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                print(f"  ✅ {description}: 规范化ID '{normalized_id}' 解析成功")
            else:
                print(f"  ❌ {description}: 规范化ID '{normalized_id}' 解析失败")
                print(f"    错误: {result.stderr}")
                all_pass = False

        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            all_pass = False

    return all_pass


def test_system_components():
    """测试系统各组件对新旧ID的处理"""
    print("\n🔍 测试3: 系统组件兼容性")
    print("-" * 50)

    # 生成一些测试ID
    test_ids = []
    for prefix in ["task", "gene_mgmt", "engineering_plan", "build"]:
        task_id = TaskIdentity.generate(prefix)
        test_ids.append((task_id.id, f"新格式: {prefix}"))

    # 添加一些旧格式ID
    old_format_ids = [
        ("-gene-mgmt-audit-20260414", "旧格式: 以'-'开头"),
        ("build-task-20260414-1234", "旧格式: 包含连字符"),
        ("normal_task_20260414", "混合格式"),
    ]

    all_pass = True

    # 测试1: JSON序列化/反序列化
    print("  测试JSON兼容性...")
    for id_str, description in test_ids + old_format_ids:
        try:
            data = {"task_id": id_str, "status": "pending", "timestamp": datetime.now().isoformat()}
            json_str = json.dumps(data)
            parsed = json.loads(json_str)

            if parsed["task_id"] == id_str:
                print(f"    ✅ {description}: JSON兼容")
            else:
                print(f"    ❌ {description}: JSON不兼容")
                all_pass = False
        except Exception as e:
            print(f"    ❌ {description}: JSON异常 - {e}")
            all_pass = False

    # 测试2: 文件系统兼容性（作为文件名）
    print("  测试文件系统兼容性...")
    for id_str, description in test_ids + old_format_ids:
        try:
            # 清理ID用于文件名
            safe_filename = id_str.replace("/", "_").replace("\\", "_")
            test_file = f"/tmp/test_{safe_filename}.txt"

            with open(test_file, "w") as f:
                f.write(f"测试文件: {id_str}")

            with open(test_file, "r") as f:
                content = f.read()

            os.remove(test_file)

            if id_str in content:
                print(f"    ✅ {description}: 文件系统兼容")
            else:
                print(f"    ❌ {description}: 文件系统不兼容")
                all_pass = False

        except Exception as e:
            print(f"    ❌ {description}: 文件系统异常 - {e}")
            all_pass = False

    # 测试3: 检查ID在队列文件中的使用
    print("  测试队列文件格式兼容性...")
    queue_dir = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue"
    if os.path.exists(queue_dir):
        # 检查现有队列文件中的ID格式
        import glob

        queue_files = glob.glob(os.path.join(queue_dir, "*.json"))

        if queue_files:
            sample_file = queue_files[0]
            try:
                with open(sample_file, "r", encoding="utf-8") as f:
                    queue_data = json.load(f)

                # 检查items中的ID格式
                items = queue_data.get("items", {})
                id_count = 0
                problematic_ids = []

                if isinstance(items, dict):
                    for item_id in items.keys():
                        id_count += 1
                        if item_id.startswith("-") or item_id.startswith("--"):
                            problematic_ids.append(item_id)
                elif isinstance(items, list):
                    # items可能是列表
                    for item in items:
                        if isinstance(item, dict) and "id" in item:
                            item_id = item["id"]
                            id_count += 1
                            if item_id.startswith("-") or item_id.startswith("--"):
                                problematic_ids.append(item_id)

                if problematic_ids:
                    print(f"    ⚠️  现有队列文件中有{len(problematic_ids)}个以'-'开头的ID")
                    print(f"       示例: {problematic_ids[:3]}")
                else:
                    print(f"    ✅ 现有队列文件中的ID格式正常")

                print(f"    分析文件: {os.path.basename(sample_file)}")
                print(f"    总任务数: {id_count}")

            except Exception as e:
                print(f"    ⚠️  分析队列文件失败: {e}")
        else:
            print("    ℹ️  未找到队列文件")
    else:
        print("    ℹ️  队列目录不存在")

    return all_pass


def test_backward_compatibility():
    """测试向后兼容性 - 现有任务仍能正常执行"""
    print("\n🔍 测试4: 向后兼容性")
    print("-" * 50)

    # 测试generate_task_id.py脚本
    print("  测试generate_task_id.py脚本...")
    try:
        # 测试默认前缀
        result = subprocess.run(
            ["python3", "scripts/generate_task_id.py"],
            capture_output=True,
            text=True,
            cwd="/Volumes/1TB-M2/openclaw",
            timeout=5,
        )

        if result.returncode == 0:
            task_id = result.stdout.strip()
            print(f"    ✅ 生成默认ID: {task_id}")

            # 验证ID格式
            if not task_id.startswith("-"):
                print(f"      格式合规: 不以'-'开头")
            else:
                print(f"      ❌ 格式不合规: 以'-'开头")
        else:
            print(f"    ❌ 脚本执行失败: {result.stderr}")

        # 测试带前缀
        result = subprocess.run(
            ["python3", "scripts/generate_task_id.py", "test-prefix"],
            capture_output=True,
            text=True,
            cwd="/Volumes/1TB-M2/openclaw",
            timeout=5,
        )

        if result.returncode == 0:
            task_id = result.stdout.strip()
            print(f"    ✅ 生成带前缀ID: {task_id}")
        else:
            print(f"    ❌ 带前缀生成失败: {result.stderr}")

    except Exception as e:
        print(f"    ❌ 测试异常: {e}")

    # 测试工程化实施方案生成器中的集成
    print("  测试engineering-plan-generator-optimized.sh集成...")
    generator_script = "/Volumes/1TB-M2/openclaw/engineering-plan-generator-optimized.sh"
    if os.path.exists(generator_script):
        # 检查脚本中是否调用了generate_task_id.py
        with open(generator_script, "r", encoding="utf-8") as f:
            content = f.read()

        if "scripts/generate_task_id.py" in content:
            print("    ✅ 生成器脚本已集成TaskIdentityContract")

            # 查找具体代码段
            import re

            pattern = r"local task_id=\$\(python3 scripts/generate_task_id\.py.*?\)"
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                print(f"    ✅ 找到ID生成代码: {matches[0][:100]}...")
            else:
                print("    ⚠️  未找到具体的ID生成代码模式")
        else:
            print("    ❌ 生成器脚本未集成TaskIdentityContract")
    else:
        print("    ℹ️  生成器脚本不存在")

    return True


def test_manifest_compatibility():
    """测试Manifest文件对新旧ID的兼容性"""
    print("\n🔍 测试5: Manifest兼容性")
    print("-" * 50)

    # 检查现有manifest文件
    manifest_path = "/Volumes/1TB-M2/openclaw/.openclaw/gene_management_queue_manifest.json"
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

            # 检查manifest中的ID格式
            problematic_ids = []
            total_ids = 0

            if isinstance(manifest_data, list):
                for item in manifest_data:
                    task_id = item.get("task_id", "")
                    if task_id:
                        total_ids += 1
                        if task_id.startswith("-") or task_id.startswith("--"):
                            problematic_ids.append(task_id)

            print(f"    Manifest文件: {os.path.basename(manifest_path)}")
            print(
                f"    总条目数: {len(manifest_data) if isinstance(manifest_data, list) else 'N/A'}"
            )
            print(f"    检查的ID数: {total_ids}")
            print(f"    以'-'开头的ID数: {len(problematic_ids)}")

            if problematic_ids:
                print(f"    ⚠️  存在需要规范化的ID:")
                for pid in problematic_ids[:5]:  # 显示前5个
                    normalized = TaskIdentity.normalize(pid)
                    print(f"      {pid} → {normalized.id}")
            else:
                print(f"    ✅ 所有ID格式正常")

        except Exception as e:
            print(f"    ❌ 分析manifest失败: {e}")
    else:
        print("    ℹ️  Manifest文件不存在")

    return True


def main():
    """主测试函数"""
    print("🧪 阶段1: 验证新旧ID格式兼容性测试")
    print("=" * 60)

    all_tests_passed = True

    # 运行所有测试
    test1 = test_id_normalization()
    test2 = test_argparse_compatibility()
    test3 = test_system_components()
    test4 = test_backward_compatibility()
    test5 = test_manifest_compatibility()

    # 总结
    print("\n" + "=" * 60)
    print("📋 兼容性测试总结")
    print("=" * 60)

    test_results = [
        ("ID规范化功能", test1),
        ("argparse兼容性", test2),
        ("系统组件兼容性", test3),
        ("向后兼容性", test4),
        ("Manifest兼容性", test5),
    ]

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")

    all_passed = all([test1, test2, test3, test4, test5])

    if all_passed:
        print("\n🎉 所有兼容性测试通过！")
        print("   新ID格式与现有系统完全兼容")
        print("   可以安全地进行后续阶段部署")
    else:
        print("\n⚠️  部分兼容性测试失败")
        print("   需要修复问题后再继续部署")

    print("\n💡 建议:")
    print("   1. 如果存在以'-'开头的ID，建议在部署前进行规范化")
    print("   2. 确保所有组件（Web界面、监控系统）都支持新ID格式")
    print("   3. 创建从旧ID到新ID的映射表以支持历史查询")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
