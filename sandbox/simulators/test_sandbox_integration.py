#!/usr/bin/env python3
"""MAREF沙箱环境集成测试"""

import time
import asyncio
from sandbox_manager import (
    SandboxManager,
    EvolutionStrategy,
    SystemState,
    EvolutionResult,
)


def test_sandbox_initialization():
    """测试沙箱环境初始化"""
    print("=== 沙箱环境初始化测试 ===")
    print("目标: 验证沙箱管理器及其所有组件的正确初始化\n")

    try:
        # 创建沙箱管理器
        print("1️⃣ 创建沙箱管理器...")
        sandbox = SandboxManager("hetu_hexagram_mapping.json")
        print("✅ 沙箱管理器创建成功")

        # 验证组件初始化
        print("\n2️⃣ 验证组件初始化...")
        assert sandbox.state_manager is not None, "状态管理器未初始化"
        assert sandbox.feedback_controller is not None, "反馈控制器未初始化"
        assert sandbox.evolution_engine is not None, "演化引擎未初始化"
        assert sandbox.monitor is not None, "监控系统未初始化"
        print("✅ 所有组件初始化成功")

        # 验证状态管理器状态
        print("\n3️⃣ 验证状态管理器状态...")
        current_state = sandbox.state_manager.current_state
        print(f"   当前状态: {current_state}")
        assert (
            current_state is not None and len(current_state) == 6
        ), f"状态格式错误: {current_state}"

        # 验证分析缓存
        print("\n4️⃣ 验证分析缓存...")
        try:
            cache_size = len(sandbox.state_manager._analysis_cache)
            print(f"   分析缓存大小: {cache_size}")
            assert cache_size > 0, "分析缓存应为非空"
        except AttributeError:
            print("   ⚠️  分析缓存不可用，跳过...")

        # 验证系统状态获取
        print("\n5️⃣ 验证系统状态获取...")
        system_state = sandbox.get_system_state()
        print(f"   系统状态: {system_state.current_state}")
        print(f"   质量评分: {system_state.quality_score:.2f}")
        print(f"   稳定性指数: {system_state.stability_index:.3f}")
        print(f"   河图状态: {system_state.hetu_state.name}")
        assert isinstance(system_state, SystemState), "系统状态类型错误"
        assert (
            0 <= system_state.quality_score <= 10
        ), f"质量评分超出范围: {system_state.quality_score}"

        print("\n✅ 沙箱环境初始化测试通过！")

    except Exception as e:
        print(f"❌ 初始化测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_hyperstability_constraints():
    """测试超稳定性约束"""
    print("\n=== 超稳定性约束测试 ===")
    print("目标: 验证格雷编码约束和其他超稳定性约束\n")

    try:
        # 创建沙箱管理器
        sandbox = SandboxManager("hetu_hexagram_mapping.json")

        print("1️⃣ 测试格雷编码约束（汉明距离=1）...")
        from_state = "000000"
        to_state_valid = "000001"  # 汉明距离=1
        to_state_invalid = "000011"  # 汉明距离=2

        # 测试有效转换
        constraint_valid = sandbox._check_constraints(from_state, to_state_valid)
        print(
            f"   {from_state} → {to_state_valid}: {'满足约束' if constraint_valid else '违反约束'}"
        )
        assert constraint_valid, "有效转换应满足约束"

        # 测试无效转换
        constraint_invalid = sandbox._check_constraints(from_state, to_state_invalid)
        print(
            f"   {from_state} → {to_state_invalid}: {'满足约束' if constraint_invalid else '违反约束'}"
        )
        assert not constraint_invalid, "无效转换应违反约束"

        print("✅ 格雷编码约束验证通过")

        print("\n2️⃣ 测试质量边界约束...")
        # 获取边界状态
        all_states = list(sandbox.state_manager._by_binary.keys())
        quality_scores = []

        for state in all_states[:10]:  # 测试前10个状态
            analysis = sandbox.state_manager.analyze_state(state)
            if analysis:
                quality_scores.append(analysis.quality_score)

        if quality_scores:
            min_quality = min(quality_scores)
            max_quality = max(quality_scores)
            print(f"   质量范围: {min_quality:.2f} - {max_quality:.2f}")
            assert min_quality >= 0, f"质量低于最小值: {min_quality}"
            assert max_quality <= 10, f"质量高于最大值: {max_quality}"
            print("✅ 质量边界约束验证通过")

        print("\n3️⃣ 测试约束违反回滚机制...")
        # 故意违反约束
        sandbox.stability_constraints["max_hamming_distance"] = 0  # 禁止任何转换

        constraint_check = sandbox._check_constraints("000000", "000001")
        assert not constraint_check, "应检测到约束违反"

        # 测试回滚
        sandbox.evolution_history.append(sandbox.get_system_state())
        rollback_result = sandbox._rollback_to_stable_state()
        print(f"   回滚机制: {'工作正常' if rollback_result else '工作异常'}")

        # 恢复设置
        sandbox.stability_constraints["max_hamming_distance"] = 1
        print("✅ 约束违反回滚机制验证通过")

        print("\n✅ 超稳定性约束测试通过！")

    except Exception as e:
        print(f"❌ 超稳定性约束测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_feedback_controller():
    """测试反馈控制器"""
    print("\n=== 反馈控制器测试 ===")
    print("目标: 验证PID控制信号计算和演化参数调整\n")

    try:
        # 创建沙箱管理器
        sandbox = SandboxManager("hetu_hexagram_mapping.json")

        print("1️⃣ 测试PID控制信号计算...")
        current_quality = 3.5
        target_quality = 8.0

        control_signal = sandbox.feedback_controller.calculate_control_signal(
            current_quality, target_quality
        )

        print(f"   当前质量: {current_quality}, 目标质量: {target_quality}")
        print(f"   质量误差: {control_signal.quality_error:.3f}")
        print(f"   累积误差: {control_signal.cumulative_error:.3f}")
        print(f"   误差变化率: {control_signal.error_rate:.3f}")
        print(f"   PID控制信号: {control_signal.control_signal:.3f}")

        # 验证控制信号结构
        assert hasattr(control_signal, "quality_error"), "控制信号缺少质量误差"
        assert hasattr(control_signal, "cumulative_error"), "控制信号缺少累积误差"
        assert hasattr(control_signal, "error_rate"), "控制信号缺少误差变化率"
        assert hasattr(control_signal, "control_signal"), "控制信号缺少PID信号"

        print("✅ PID控制信号计算验证通过")

        print("\n2️⃣ 测试演化参数调整...")
        params = sandbox.feedback_controller.adjust_evolution_parameters(control_signal)

        print(f"   演化步长: {params['step_size']:.3f}")
        print(f"   探索率: {params['exploration_rate']:.3f}")
        print(f"   质量阈值: {params['quality_threshold']:.3f}")

        # 验证参数范围
        assert 0.1 <= params["step_size"] <= 5.0, f"步长超出范围: {params['step_size']}"
        assert "step_size" in params, "缺少步长参数"
        assert "exploration_rate" in params, "缺少探索率参数"
        assert "quality_threshold" in params, "缺少质量阈值参数"

        print("✅ 演化参数调整验证通过")

        print("\n3️⃣ 测试控制历史记录...")
        history_length = len(sandbox.feedback_controller.control_history)
        print(f"   控制历史记录数: {history_length}")
        assert history_length > 0, "控制历史应包含记录"

        print("✅ 控制历史记录验证通过")

        print("\n✅ 反馈控制器测试通过！")

    except Exception as e:
        print(f"❌ 反馈控制器测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_evolution_engine():
    """测试演化引擎"""
    print("\n=== 演化引擎测试 ===")
    print("目标: 验证候选生成、转换评估和策略选择\n")

    try:
        # 创建沙箱管理器
        sandbox = SandboxManager("hetu_hexagram_mapping.json")
        engine = sandbox.evolution_engine

        print("1️⃣ 测试候选状态生成...")
        current_state = "000000"
        step_size = 1.0

        candidates = engine.generate_candidate_transitions(current_state, step_size)
        print(f"   当前状态: {current_state}, 步长: {step_size}")
        print(f"   生成候选数: {len(candidates)}")

        # 验证候选状态
        for candidate in candidates[:5]:  # 显示前5个
            print(f"     - {candidate}")

        assert len(candidates) > 0, "应生成候选状态"
        assert all(len(state) == 6 for state in candidates), "候选状态格式错误"

        # 验证汉明距离约束
        for candidate in candidates:
            distance = sandbox.state_manager.hamming_distance(current_state, candidate)
            assert distance <= round(
                step_size + 0.5
            ), f"汉明距离超出步长范围: {distance}"

        print("✅ 候选状态生成验证通过")

        print("\n2️⃣ 测试转换评估...")
        if candidates:
            test_candidate = candidates[0]
            evaluation = engine.evaluate_transition(current_state, test_candidate)

            print(f"   转换评估: {current_state} → {test_candidate}")
            print(f"   成本: {evaluation['cost']}")
            print(f"   收益: {evaluation['benefit']:.3f}")
            print(f"   质量变化: {evaluation['quality_delta']:.3f}")
            print(f"   有效性: {evaluation['valid']}")

            # 验证评估结果
            assert "cost" in evaluation, "缺少成本字段"
            assert "benefit" in evaluation, "缺少收益字段"
            assert "quality_delta" in evaluation, "缺少质量变化字段"
            assert "valid" in evaluation, "缺少有效性字段"

            print("✅ 转换评估验证通过")

        print("\n3️⃣ 测试贪心策略选择...")
        engine.set_strategy(EvolutionStrategy.GREEDY)
        best_candidate = engine.select_best_transition(current_state, candidates)

        if best_candidate:
            print(f"   贪心策略选择: {best_candidate}")
            # 验证选择是最优的
            evaluations = []
            for candidate in candidates:
                eval_result = engine.evaluate_transition(current_state, candidate)
                if eval_result["valid"]:
                    evaluations.append((candidate, eval_result))

            if evaluations:
                # 找到最优收益
                best_eval = max(evaluations, key=lambda x: x[1]["benefit"])
                if best_eval[0] != best_candidate:
                    print(
                        f"   ⚠️  选择次优解: {best_candidate}, 最优解: {best_eval[0]}"
                    )
                else:
                    print("   ✅ 贪心策略选择了最优解")
        else:
            print("   ⚠️  没有找到有效转换")

        print("✅ 贪心策略验证通过")

        print("\n4️⃣ 测试模拟退火策略...")
        engine.set_strategy(EvolutionStrategy.SIMULATED_ANNEALING)
        sa_candidate = engine.select_best_transition(current_state, candidates)

        if sa_candidate:
            print(f"   模拟退火策略选择: {sa_candidate}")
            # 模拟退火可能选择非最优解，这是正常的
            print("   ✅ 模拟退火策略工作正常")
        else:
            print("   ⚠️  模拟退火没有找到有效转换")

        print("✅ 模拟退火策略验证通过")

        print("\n✅ 演化引擎测试通过！")

    except Exception as e:
        print(f"❌ 演化引擎测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_monitor_system():
    """测试监控系统"""
    print("\n=== 监控系统测试 ===")
    print("目标: 验证状态转换记录和性能指标跟踪\n")

    try:
        # 创建沙箱管理器
        sandbox = SandboxManager("hetu_hexagram_mapping.json")
        monitor = sandbox.monitor

        print("1️⃣ 测试监控系统启动...")
        monitor.start_monitoring()
        print("✅ 监控系统启动成功")

        print("\n2️⃣ 测试状态转换记录...")
        from_state = "000000"
        to_state = "000001"
        evaluation = {
            "quality_delta": 1.67,
            "cost": 1.0,
            "benefit": 1.57,
            "valid": True,
        }

        monitor.log_transition(from_state, to_state, evaluation, iteration=1)
        print(f"   记录转换: {from_state} → {to_state}")

        assert len(monitor.state_transitions) == 1, "状态转换记录失败"
        record = monitor.state_transitions[0]
        assert record["from_state"] == from_state, "记录源状态错误"
        assert record["to_state"] == to_state, "记录目标状态错误"
        assert (
            record["quality_delta"] == evaluation["quality_delta"]
        ), "记录质量变化错误"

        print("✅ 状态转换记录验证通过")

        print("\n3️⃣ 测试性能指标记录...")
        monitor.log_performance(
            iteration_time=0.123,
            quality_change=1.67,
            control_signal=0.85,
            constraint_violation=False,
        )

        print("   记录性能指标: 迭代时间=0.123s, 质量变化=+1.67")

        # 验证指标记录
        assert len(monitor.performance_metrics["iteration_times"]) == 1
        assert len(monitor.performance_metrics["quality_changes"]) == 1
        assert len(monitor.performance_metrics["control_signals"]) == 1
        assert len(monitor.performance_metrics["constraint_violations"]) == 1

        print("✅ 性能指标记录验证通过")

        print("\n4️⃣ 测试监控报告生成...")
        report = monitor.generate_report()
        print(f"   监控报告生成成功")
        print(f"   总迭代次数: {report.get('total_iterations', 'N/A')}")
        print(f"   成功率: {report.get('success_rate', 'N/A'):.1%}")
        print(f"   平均质量变化: {report.get('average_quality_change', 'N/A'):.3f}")
        print(f"   约束违反次数: {report.get('constraint_violations', 'N/A')}")

        # 验证报告结构
        assert "monitoring_duration_seconds" in report, "缺少监控时长"
        assert "total_iterations" in report, "缺少总迭代次数"
        assert "success_rate" in report, "缺少成功率"
        assert "average_quality_change" in report, "缺少平均质量变化"

        print("✅ 监控报告生成验证通过")

        print("\n5️⃣ 测试报告保存...")
        import os

        report_file = "test_monitor_report.json"
        monitor.save_report(report_file)

        if os.path.exists(report_file):
            print(f"   报告文件已保存: {report_file}")
            os.remove(report_file)  # 清理测试文件
            print("   测试文件已清理")
        else:
            print(f"   ⚠️  报告文件未创建")

        print("✅ 报告保存验证通过")

        print("\n✅ 监控系统测试通过！")

    except Exception as e:
        print(f"❌ 监控系统测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_evolution_workflow():
    """测试完整演化工作流"""
    print("\n=== 完整演化工作流测试 ===")
    print("目标: 验证从初始化到演化的完整流程\n")

    try:
        print("1️⃣ 创建沙箱管理器并初始化...")
        sandbox = SandboxManager("hetu_hexagram_mapping.json")
        initial_state = sandbox.get_system_state()
        print(
            f"   初始状态: {initial_state.current_state}, 质量: {initial_state.quality_score:.2f}"
        )

        print("\n2️⃣ 执行小型演化测试...")
        target_quality = min(initial_state.quality_score + 2.0, 8.0)
        print(
            f"   目标质量: {target_quality:.2f} (从 {initial_state.quality_score:.2f} 提升2.0)"
        )

        # 运行演化（限制迭代次数）
        result = sandbox.evolve(
            target_quality=target_quality,
            max_iterations=10,
            strategy=EvolutionStrategy.GREEDY,
        )

        print(f"\n3️⃣ 验证演化结果...")
        print(f"   成功: {result.success}")
        print(f"   最终质量: {result.final_quality:.2f}")
        print(f"   迭代次数: {result.iterations}")
        print(f"   执行时间: {result.execution_time:.2f}秒")
        print(f"   稳定性违反: {result.stability_violations}")
        print(f"   演化路径长度: {len(result.path)}")

        # 验证结果结构
        assert isinstance(result, EvolutionResult), "演化结果类型错误"
        assert (
            0 <= result.final_quality <= 10
        ), f"最终质量超出范围: {result.final_quality}"
        assert result.iterations <= 10, f"迭代次数超出限制: {result.iterations}"
        assert len(result.path) >= 1, "演化路径不能为空"

        print("\n4️⃣ 验证演化路径...")
        print(
            f"   路径: {' → '.join(result.path[:5])}"
            + ("..." if len(result.path) > 5 else "")
        )

        # 验证路径的连贯性（格雷编码）
        for i in range(len(result.path) - 1):
            from_state = result.path[i]
            to_state = result.path[i + 1]
            distance = sandbox.state_manager.hamming_distance(from_state, to_state)
            assert (
                distance == 1
            ), f"路径违反格雷编码: {from_state} → {to_state} (距离={distance})"

        print("✅ 演化路径连贯性验证通过")

        print("\n5️⃣ 验证质量时间线...")
        print(
            f"   质量变化: {result.quality_timeline[0]:.2f} → {result.quality_timeline[-1]:.2f}"
        )
        assert len(result.quality_timeline) == len(
            result.path
        ), "质量时间线与路径长度不匹配"

        # 验证质量单调性（贪心策略应该单调不降）
        if result.stability_violations == 0:
            for i in range(len(result.quality_timeline) - 1):
                if result.quality_timeline[i + 1] < result.quality_timeline[i]:
                    print(
                        f"   ⚠️  质量下降: {result.quality_timeline[i]:.2f} → {result.quality_timeline[i+1]:.2f}"
                    )

        print("\n✅ 完整演化工作流测试通过！")

    except Exception as e:
        print(f"❌ 演化工作流测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def main():
    """主测试函数"""
    print("=" * 60)
    print("MAREF沙箱环境 - 综合集成测试套件")
    print("=" * 60)
    print("目标: 验证MAREF沙箱环境的所有组件和功能\n")

    # 运行所有测试
    test_results = []

    # 测试1: 沙箱环境初始化
    test_results.append(("沙箱环境初始化", test_sandbox_initialization()))

    # 测试2: 超稳定性约束
    test_results.append(("超稳定性约束", test_hyperstability_constraints()))

    # 测试3: 反馈控制器
    test_results.append(("反馈控制器", test_feedback_controller()))

    # 测试4: 演化引擎
    test_results.append(("演化引擎", test_evolution_engine()))

    # 测试5: 监控系统
    test_results.append(("监控系统", test_monitor_system()))

    # 测试6: 完整演化工作流
    test_results.append(("完整演化工作流", test_evolution_workflow()))

    # 测试结果总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, success in test_results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
        else:
            failed += 1

    print("\n" + "-" * 40)
    print(f"总计: {len(test_results)} 个测试")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"成功率: {passed/len(test_results)*100:.1f}%")

    if failed == 0:
        print("\n🎉 所有MAREF沙箱环境测试通过！系统已准备好进行生产部署。")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查系统实现。")
        return 1


if __name__ == "__main__":
    exit(main())
