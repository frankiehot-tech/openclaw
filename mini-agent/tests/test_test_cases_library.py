#!/usr/bin/env python3
"""
测试用例库测试
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
project_root = "/Volumes/1TB-M2/openclaw"
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "mini-agent"))

from agent.core.test_cases_library import (
    DifficultyLevel,
    ProgrammingTask,
    TaskCategory,
    TestCase,
    TestCaseLibrary,
    get_test_case_library,
)


def test_library_initialization():
    """测试库初始化"""
    print("🧪 测试库初始化...")

    library = TestCaseLibrary()
    assert library is not None
    assert len(library.tasks) > 0
    print(f"  ✅ 库初始化成功，包含 {len(library.tasks)} 个任务")

    # 验证全局实例
    global_library = get_test_case_library()
    assert global_library is not None
    assert global_library is get_test_case_library()  # 单例模式
    print("  ✅ 全局单例模式正确")

    return True


def test_task_structure():
    """测试任务结构"""
    print("\n🧪 测试任务结构...")

    library = TestCaseLibrary()

    for task in library.tasks:
        # 基本字段检查
        assert task.id, f"任务缺少ID: {task.title}"
        assert task.title, f"任务缺少标题: {task.id}"
        assert task.prompt, f"任务缺少提示: {task.id}"
        assert task.reference_solution, f"任务缺少参考解决方案: {task.id}"
        assert isinstance(task.category, TaskCategory), f"任务类别类型错误: {task.id}"
        assert isinstance(task.difficulty, DifficultyLevel), f"任务难度类型错误: {task.id}"

        # 参考解决方案长度检查
        assert len(task.reference_solution) > 50, f"参考解决方案太短: {task.id}"

    print(f"  ✅ 所有 {len(library.tasks)} 个任务结构正确")
    return True


def test_task_categories():
    """测试任务类别分布"""
    print("\n🧪 测试任务类别分布...")

    library = TestCaseLibrary()

    category_counts = {}
    for task in library.tasks:
        cat = task.category.value
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print(f"  类别分布:")
    for cat, count in sorted(category_counts.items()):
        print(f"    {cat}: {count}个任务")

    # 验证至少有3个不同类别
    assert len(category_counts) >= 3, f"类别数量不足: {len(category_counts)}"

    # 验证主要类别存在
    expected_categories = ["algorithm", "string", "data_structure", "math"]
    for cat in expected_categories:
        if cat in category_counts:
            print(f"  ✅ 类别 '{cat}' 存在: {category_counts[cat]}个任务")

    print("  ✅ 类别分布合理")
    return True


def test_difficulty_levels():
    """测试难度级别"""
    print("\n🧪 测试难度级别...")

    library = TestCaseLibrary()

    difficulty_counts = {}
    for task in library.tasks:
        diff = task.difficulty.value
        difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

    print(f"  难度分布:")
    for diff in sorted(difficulty_counts.keys()):
        level_name = {1: "初学者", 2: "容易", 3: "中等", 4: "高级", 5: "专家"}.get(
            diff, f"等级{diff}"
        )
        print(f"    {level_name}: {difficulty_counts[diff]}个任务")

    # 验证难度范围在1-5之间
    for diff in difficulty_counts.keys():
        assert 1 <= diff <= 5, f"难度值超出范围: {diff}"

    # 验证至少包含3种不同难度
    assert len(difficulty_counts) >= 3, f"难度级别数量不足: {len(difficulty_counts)}"

    print("  ✅ 难度分布合理")
    return True


def test_export_functionality():
    """测试导出功能"""
    print("\n🧪 测试导出功能...")

    library = TestCaseLibrary()

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        json_file = tmp.name

    try:
        # 测试导出
        success = library.export_to_json(json_file)
        assert success, "导出失败"

        # 验证导出文件
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "tasks" in data
        assert "total_tasks" in data
        assert data["total_tasks"] == len(library.tasks)

        # 验证任务数据
        for task_data in data["tasks"]:
            assert "id" in task_data
            assert "title" in task_data
            assert "category" in task_data
            assert "difficulty" in task_data
            assert "reference_solution" in task_data

        print(f"  ✅ 导出功能正常，导出 {data['total_tasks']} 个任务")
        return True

    finally:
        # 清理临时文件
        if os.path.exists(json_file):
            os.unlink(json_file)


def test_get_task_methods():
    """测试获取任务方法"""
    print("\n🧪 测试获取任务方法...")

    library = TestCaseLibrary()

    # 测试按ID获取
    task = library.get_task("fibonacci")
    assert task is not None
    assert task.id == "fibonacci"
    assert "斐波那契" in task.title or "fibonacci" in task.title.lower()
    print("  ✅ 按ID获取任务成功")

    # 测试按类别获取
    algorithm_tasks = library.get_tasks_by_category(TaskCategory.ALGORITHM)
    assert len(algorithm_tasks) > 0
    for task in algorithm_tasks:
        assert task.category == TaskCategory.ALGORITHM
    print(f"  ✅ 按类别获取成功: {len(algorithm_tasks)} 个算法任务")

    # 测试按难度获取
    beginner_tasks = library.get_tasks_by_difficulty(DifficultyLevel.BEGINNER)
    for task in beginner_tasks:
        assert task.difficulty == DifficultyLevel.BEGINNER
    print(f"  ✅ 按难度获取成功: {len(beginner_tasks)} 个初学者任务")

    # 测试获取所有任务
    all_tasks = library.get_all_tasks()
    assert len(all_tasks) == len(library.tasks)
    print(f"  ✅ 获取所有任务成功: {len(all_tasks)} 个任务")

    return True


def main():
    """主测试函数"""
    print("🔍 测试用例库测试套件")
    print("=" * 60)

    test_results = []

    try:
        test_results.append(("库初始化", test_library_initialization()))
        test_results.append(("任务结构", test_task_structure()))
        test_results.append(("任务类别", test_task_categories()))
        test_results.append(("难度级别", test_difficulty_levels()))
        test_results.append(("导出功能", test_export_functionality()))
        test_results.append(("获取方法", test_get_task_methods()))

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # 打印测试结果摘要
    print("\n" + "=" * 60)
    print("📋 测试结果摘要:")

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")

    print(f"\n   总体: {passed}/{total} 个测试通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过！测试用例库功能正常。")

        # 打印库摘要
        print("\n📊 测试用例库摘要:")
        library = get_test_case_library()
        library.print_summary()

        return 0
    else:
        print("\n⚠️  部分测试失败，请检查问题。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
