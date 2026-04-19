#!/usr/bin/env python3
"""
集成64卦状态系统测试

测试完整的河图洛书调度器+64卦状态系统集成工作流，
验证重构计划阶段3（集成和测试）的要求。
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_hetu_luoshu_scheduler import HexagramEnhancedLuoshuScheduler
from mini_agent.agent.core.maref_quality.hetu_luoshu_scheduler import AssessmentPriority


def test_complete_workflow():
    """测试完整工作流：从任务提交到完成"""
    print("=== 集成64卦状态系统测试 ===")
    print("测试目标：验证完整工作流和系统集成")

    # 创建临时状态文件
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        state_file = tmp.name

    try:
        # 1. 初始化调度器
        print("\n1. 🔧 初始化增强调度器...")
        scheduler = HexagramEnhancedLuoshuScheduler(state_file=state_file, max_concurrent=3)

        # 2. 提交多个任务
        print("\n2. 📤 提交测试任务...")
        tasks = []

        # 任务1: 算法任务
        fibonacci_code = """
def fibonacci(n):
    \"\"\"计算斐波那契数列\"\"\"
    if n <= 1:
        return n
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b
"""
        task1_id = scheduler.submit_task(
            code=fibonacci_code,
            task_type="algorithm",
            priority=AssessmentPriority.HIGH,
            context={"complexity": "medium", "test_coverage": 0.8},
        )
        tasks.append(task1_id)
        print(f"   任务1提交成功: {task1_id}")

        # 任务2: 数据处理任务
        data_process_code = """
def process_data(data_list):
    \"\"\"数据处理函数\"\"\"
    if not data_list:
        return []

    # 过滤无效数据
    filtered = [x for x in data_list if x is not None]

    # 计算统计信息
    if filtered:
        avg = sum(filtered) / len(filtered)
        return {
            "count": len(filtered),
            "average": avg,
            "min": min(filtered),
            "max": max(filtered)
        }
    return {"count": 0}
"""
        task2_id = scheduler.submit_task(
            code=data_process_code,
            task_type="data_processing",
            priority=AssessmentPriority.MEDIUM,
            context={"data_size": 1000},
        )
        tasks.append(task2_id)
        print(f"   任务2提交成功: {task2_id}")

        # 任务3: 简单工具函数
        utility_code = """
def format_size(size_bytes):
    \"\"\"格式化字节大小为人类可读格式\"\"\"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
"""
        task3_id = scheduler.submit_task(
            code=utility_code,
            task_type="utility",
            priority=AssessmentPriority.LOW,
            context={"performance": "high"},
        )
        tasks.append(task3_id)
        print(f"   任务3提交成功: {task3_id}")

        # 3. 执行任务
        print("\n3. ▶️  执行任务...")
        execution_results = {}

        for task_id in tasks:
            print(f"   执行任务 {task_id}...")
            success = scheduler.execute_task(task_id)
            execution_results[task_id] = success
            print(f"     结果: {'✅ 成功' if success else '❌ 失败'}")

        # 4. 检查任务状态
        print("\n4. 📊 检查任务状态...")
        for task_id in tasks:
            status = scheduler.get_task_status(task_id)
            if status:
                print(f"   任务 {task_id}:")
                print(f"     河图状态: {status.get('state', '未知')}")
                print(f"     卦象状态: {status.get('hexagram_state', '未知')}")
                print(f"     卦象名称: {status.get('hexagram_name', '未知')}")
                print(f"     质量评分: {status.get('quality_score', 0):.2f}/10")
                print(f"     激活维度: {len(status.get('active_dimensions', []))}个")
            else:
                print(f"   ❌ 无法获取任务 {task_id} 状态")

        # 5. 获取系统报告
        print("\n5. 📈 获取系统报告...")
        report = scheduler.get_system_report()

        print(f"   总任务数: {report.get('total_tasks', 0)}")
        print(f"   调度器状态: {report.get('scheduler_status', {}).get('status', '未知')}")

        hexagram_adapter = report.get("hexagram_adapter", {})
        print(f"   卦象适配器任务数: {hexagram_adapter.get('total_tasks', 0)}")

        hexagram_stats = report.get("hexagram_statistics", {})
        quality_scores = hexagram_stats.get("quality_scores", {})
        print(f"   平均质量评分: {quality_scores.get('average', 0):.2f}/10")

        # 6. 测试状态持久化
        print("\n6. 💾 测试状态持久化...")

        # 保存状态到新文件
        new_state_file = state_file + ".backup"
        scheduler.save_state(new_state_file)

        # 检查文件是否存在
        if os.path.exists(new_state_file):
            print(f"   状态文件已创建: {new_state_file}")

            # 检查文件内容
            with open(new_state_file, "r") as f:
                saved_state = json.load(f)

            if isinstance(saved_state, dict):
                print(f"   状态文件格式正确，包含 {len(saved_state)} 个键")
            else:
                print(f"   ⚠️ 状态文件格式不是字典")
        else:
            print(f"   ❌ 状态文件创建失败")

        # 7. 测试卦象分析功能
        print("\n7. 🔍 测试卦象分析功能...")
        for task_id in tasks[:2]:  # 只测试前两个任务
            analysis = scheduler.get_hexagram_analysis(task_id)
            if analysis:
                print(f"   任务 {task_id} 卦象分析:")
                print(f"     卦象编码: {analysis.hexagram_code}")
                print(f"     二进制表示: {analysis.binary_representation}")
                print(f"     河图状态: {analysis.hetu_state_name}")
                print(f"     语义描述: {analysis.semantic_description[:50]}...")
                print(f"     到完美状态距离: {analysis.evolution_distance_to_perfect}")
            else:
                print(f"   ⚠️ 无法获取任务 {task_id} 的卦象分析")

        # 8. 测试可视化功能
        print("\n8. 🗺️  测试卦象空间可视化...")
        visualization = scheduler.visualize_hexagram_space()

        # 检查可视化输出
        if visualization and len(visualization) > 100:
            print(f"   可视化输出长度: {len(visualization)} 字符")

            # 显示部分内容
            lines = visualization.split("\n")
            print("   部分输出预览:")
            for i, line in enumerate(lines[:10]):
                print(f"     {line}")
            print("   ...")
        else:
            print(f"   ⚠️ 可视化输出过短或为空")

        # 9. 验证执行结果
        print("\n9. ✅ 验证测试结果...")
        all_success = all(execution_results.values())

        if all_success:
            print(f"   ✅ 所有{len(tasks)}个任务执行成功")

            # 验证状态文件是否包含所有任务
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    adapter_state = json.load(f)

                saved_tasks = len(adapter_state.get("tasks", {}))
                print(f"   ✅ 状态文件保存了 {saved_tasks} 个任务")
            else:
                print(f"   ⚠️ 适配器状态文件不存在")
        else:
            failed_tasks = [tid for tid, success in execution_results.items() if not success]
            print(f"   ❌ {len(failed_tasks)}个任务失败: {failed_tasks}")

        print(f"\n🎉 集成测试完成!")
        return all_success

    finally:
        # 清理临时文件
        if os.path.exists(state_file):
            os.unlink(state_file)
        backup_file = state_file + ".backup"
        if os.path.exists(backup_file):
            os.unlink(backup_file)


def test_performance_benchmark():
    """性能基准测试：评估状态转移性能"""
    print("\n=== 性能基准测试 ===")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        state_file = tmp.name

    try:
        # 创建调度器
        scheduler = HexagramEnhancedLuoshuScheduler(state_file=state_file)

        # 创建测试代码
        test_code = "def test(): return 42"

        # 提交多个任务
        num_tasks = 10
        task_ids = []

        print(f"提交 {num_tasks} 个任务进行性能测试...")
        start_time = time.time()

        for i in range(num_tasks):
            task_id = scheduler.submit_task(
                code=test_code,
                task_type="performance_test",
                priority=AssessmentPriority.LOW,
                context={"test_id": i},
            )
            task_ids.append(task_id)

        submission_time = time.time() - start_time
        print(f"任务提交完成: {submission_time:.3f}秒")
        print(f"平均每个任务: {submission_time/num_tasks*1000:.1f}毫秒")

        # 执行任务
        print(f"\n执行 {num_tasks} 个任务...")
        start_time = time.time()

        success_count = 0
        for task_id in task_ids:
            if scheduler.execute_task(task_id):
                success_count += 1

        execution_time = time.time() - start_time
        print(f"任务执行完成: {execution_time:.3f}秒")
        print(f"平均每个任务: {execution_time/num_tasks*1000:.1f}毫秒")
        print(f"成功率: {success_count}/{num_tasks} ({success_count/num_tasks*100:.1f}%)")

        # 状态查询性能
        print(f"\n状态查询性能测试...")
        start_time = time.time()

        for task_id in task_ids:
            status = scheduler.get_task_status(task_id)

        query_time = time.time() - start_time
        print(f"状态查询完成: {query_time:.3f}秒")
        print(f"平均每个查询: {query_time/num_tasks*1000:.1f}毫秒")

        return success_count == num_tasks

    finally:
        if os.path.exists(state_file):
            os.unlink(state_file)


def test_backward_compatibility():
    """向后兼容性测试：验证API不变"""
    print("\n=== 向后兼容性测试 ===")

    # 测试API兼容性
    from hetu_hexagram_adapter import HetuToHexagramAdapter
    from integrated_hexagram_state_manager import HetuState

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        state_file = tmp.name

    try:
        # 创建适配器
        adapter = HetuToHexagramAdapter(state_file=state_file)

        # 测试核心API
        print("1. 测试河图状态枚举兼容性...")
        expected_states = [state.name for state in HetuState]
        print(f"   河图状态数: {len(expected_states)}")
        print(f"   状态列表: {', '.join(expected_states)}")

        # 测试状态转移API
        print("\n2. 测试状态转移API...")
        task_id = "compatibility_test"

        # 新任务从INITIAL到AST_PARSED
        success = adapter.transition(task_id, HetuState.INITIAL, HetuState.AST_PARSED)
        print(f"   状态转移结果: {'✅ 成功' if success else '❌ 失败'}")

        # 测试状态查询API
        print("\n3. 测试状态查询API...")
        hexagram_state = adapter.get_task_hexagram_state(task_id)
        hetu_state = adapter.get_task_hetu_state(task_id)

        print(f"   卦象状态: {hexagram_state}")
        print(f"   河图状态: {hetu_state.name if hetu_state else '无'}")

        # 测试分析API
        print("\n4. 测试状态分析API...")
        analysis = adapter.analyze_task_state(task_id)

        if analysis:
            print(f"   分析成功:")
            print(f"     卦象名称: {analysis.hexagram_name}")
            print(f"     质量评分: {analysis.quality_score:.2f}")
            print(f"     激活维度: {len(analysis.active_dimensions)}个")
        else:
            print(f"   ⚠️ 分析失败")

        # 测试报告API
        print("\n5. 测试系统报告API...")
        report = adapter.get_state_report()

        if isinstance(report, dict):
            print(f"   报告生成成功:")
            print(f"     总任务数: {report.get('total_tasks', 0)}")
            print(
                f"     卦象管理器状态: {'✅ 正常' if 'hexagram_manager' in report else '❌ 异常'}"
            )
        else:
            print(f"   ⚠️ 报告格式不正确")

        print("\n✅ 向后兼容性测试完成")
        return success and hexagram_state is not None and hetu_state is not None

    finally:
        if os.path.exists(state_file):
            os.unlink(state_file)


def main():
    """主测试函数"""
    print("🚀 开始64卦状态系统集成测试")
    print("=" * 60)

    # 运行所有测试
    tests = [
        ("完整工作流测试", test_complete_workflow),
        ("性能基准测试", test_performance_benchmark),
        ("向后兼容性测试", test_backward_compatibility),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n▶️  运行测试: {test_name}")
        print("-" * 40)

        try:
            success = test_func()
            results.append((test_name, success))

            if success:
                print(f"✅ {test_name}: 通过")
            else:
                print(f"❌ {test_name}: 失败")

        except Exception as e:
            print(f"💥 {test_name}: 异常 - {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # 总结
    print("\n" + "=" * 60)
    print("📋 测试总结:")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {test_name}: {status}")

    print(f"\n📊 总体结果: {passed}/{total} 个测试通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 所有集成测试通过！64卦状态系统集成验证成功。")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步调试。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
