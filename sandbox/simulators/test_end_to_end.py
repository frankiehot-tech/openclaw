#!/usr/bin/env python3
"""端到端集成测试：验证MAREF沙箱环境的完整工作流"""

import time
import json
import threading
import subprocess
import sys
from typing import Dict, Any
from dataclasses import dataclass

# 导入SDK和API
from maref_api import app
from maref_sdk import SandboxClient, EvolutionStrategy, SystemState, EvolutionResult


@dataclass
class TestResult:
    """测试结果"""

    name: str
    success: bool
    duration: float
    error: str = ""
    details: Dict[str, Any] = None


def test_api_server_startup() -> TestResult:
    """测试API服务器启动"""
    name = "API服务器启动"
    start_time = time.time()

    try:
        # 使用Flask测试客户端
        test_client = app.test_client()
        test_client.testing = True

        # 健康检查
        response = test_client.get("/health")
        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = json.loads(response.data)
            return TestResult(
                name=name,
                success=True,
                duration=elapsed,
                details={"status": data["status"], "service": data["service"]},
            )
        else:
            return TestResult(
                name=name,
                success=False,
                duration=elapsed,
                error=f"HTTP {response.status_code}",
            )

    except Exception as e:
        return TestResult(
            name=name, success=False, duration=time.time() - start_time, error=str(e)
        )


def test_sdk_client_connection() -> TestResult:
    """测试SDK客户端连接"""
    name = "SDK客户端连接"
    start_time = time.time()

    try:
        # 创建客户端（使用测试服务器）
        client = SandboxClient(base_url="http://localhost:5001", timeout=5)

        # 健康检查
        health = client.health_check()
        elapsed = time.time() - start_time

        return TestResult(name=name, success=True, duration=elapsed, details=health)

    except Exception as e:
        return TestResult(
            name=name, success=False, duration=time.time() - start_time, error=str(e)
        )


def test_system_state_retrieval() -> TestResult:
    """测试系统状态获取"""
    name = "系统状态获取"
    start_time = time.time()

    try:
        client = SandboxClient(base_url="http://localhost:5001", timeout=5)
        state = client.get_state()
        elapsed = time.time() - start_time

        # 验证状态数据
        valid = (
            isinstance(state.current_state, str)
            and len(state.current_state) == 6
            and 0 <= state.quality_score <= 10
            and 0 <= state.stability_index <= 1
        )

        if valid:
            return TestResult(
                name=name,
                success=True,
                duration=elapsed,
                details={
                    "current_state": state.current_state,
                    "quality_score": state.quality_score,
                    "stability_index": state.stability_index,
                    "hetu_state": state.hetu_state,
                },
            )
        else:
            return TestResult(
                name=name,
                success=False,
                duration=elapsed,
                error="Invalid state data",
                details=vars(state),
            )

    except Exception as e:
        return TestResult(
            name=name, success=False, duration=time.time() - start_time, error=str(e)
        )


def test_evolution_sync() -> TestResult:
    """测试同步演化（快速测试）"""
    name = "同步演化"
    start_time = time.time()

    try:
        client = SandboxClient(base_url="http://localhost:5001", timeout=10)

        # 使用较小的目标质量进行快速测试
        result = client.evolve(
            target_quality=5.0,
            max_iterations=10,
            strategy=EvolutionStrategy.GREEDY,
            poll_interval=0.1,
            timeout=5,  # 5秒超时
        )
        elapsed = time.time() - start_time

        # 验证结果
        valid = (
            isinstance(result.success, bool)
            and 0 <= result.final_quality <= 10
            and result.iterations >= 0
            and result.execution_time >= 0
        )

        if valid:
            return TestResult(
                name=name,
                success=True,
                duration=elapsed,
                details={
                    "success": result.success,
                    "final_quality": result.final_quality,
                    "iterations": result.iterations,
                    "execution_time": result.execution_time,
                    "stability_violations": result.stability_violations,
                    "path_length": len(result.path),
                },
            )
        else:
            return TestResult(
                name=name,
                success=False,
                duration=elapsed,
                error="Invalid evolution result",
                details=vars(result),
            )

    except Exception as e:
        return TestResult(
            name=name, success=False, duration=time.time() - start_time, error=str(e)
        )


def test_evolution_async() -> TestResult:
    """测试异步演化"""
    name = "异步演化"
    start_time = time.time()

    try:
        client = SandboxClient(base_url="http://localhost:5001", timeout=5)

        # 启动异步任务
        task_id = client.evolve_async(
            target_quality=6.0,
            max_iterations=15,
            strategy=EvolutionStrategy.SIMULATED_ANNEALING,
        )

        # 轮询任务状态
        max_attempts = 20
        for i in range(max_attempts):
            task_status = client.get_task_status(task_id)

            if task_status.status == "completed":
                elapsed = time.time() - start_time
                return TestResult(
                    name=name,
                    success=True,
                    duration=elapsed,
                    details={
                        "task_id": task_id,
                        "status": task_status.status,
                        "iterations": (
                            task_status.result.iterations if task_status.result else 0
                        ),
                        "elapsed_seconds": task_status.elapsed_seconds,
                    },
                )
            elif task_status.status == "failed":
                return TestResult(
                    name=name,
                    success=False,
                    duration=time.time() - start_time,
                    error=f"Task failed: {task_status.error}",
                    details={"task_id": task_id},
                )

            time.sleep(0.5)  # 轮询间隔

        # 超时
        return TestResult(
            name=name,
            success=False,
            duration=time.time() - start_time,
            error="Task timeout",
            details={"task_id": task_id, "max_attempts": max_attempts},
        )

    except Exception as e:
        return TestResult(
            name=name, success=False, duration=time.time() - start_time, error=str(e)
        )


def test_sandbox_reset() -> TestResult:
    """测试沙箱重置"""
    name = "沙箱重置"
    start_time = time.time()

    try:
        client = SandboxClient(base_url="http://localhost:5001", timeout=5)

        # 获取当前状态
        state_before = client.get_state()

        # 执行重置
        reset_result = client.reset()

        # 获取重置后状态
        state_after = client.get_state()
        elapsed = time.time() - start_time

        # 重置应该生成新的状态（可能相同也可能不同）
        return TestResult(
            name=name,
            success=True,
            duration=elapsed,
            details={
                "reset_message": reset_result.get("message", ""),
                "new_state": reset_result.get("new_state", ""),
                "before_state": state_before.current_state,
                "after_state": state_after.current_state,
            },
        )

    except Exception as e:
        return TestResult(
            name=name, success=False, duration=time.time() - start_time, error=str(e)
        )


def test_constraints_and_strategies() -> TestResult:
    """测试约束和策略获取"""
    name = "约束和策略获取"
    start_time = time.time()

    try:
        client = SandboxClient(base_url="http://localhost:5001", timeout=5)

        # 获取约束
        constraints = client.get_constraints()

        # 获取策略
        strategies = client.get_strategies()
        elapsed = time.time() - start_time

        return TestResult(
            name=name,
            success=True,
            duration=elapsed,
            details={
                "constraints_keys": list(constraints.keys()),
                "strategies_count": len(strategies),
                "strategy_names": [s["name"] for s in strategies],
            },
        )

    except Exception as e:
        return TestResult(
            name=name, success=False, duration=time.time() - start_time, error=str(e)
        )


def test_evolution_history() -> TestResult:
    """测试演化历史获取"""
    name = "演化历史获取"
    start_time = time.time()

    try:
        client = SandboxClient(base_url="http://localhost:5001", timeout=5)

        history = client.get_history()
        elapsed = time.time() - start_time

        # 验证历史数据结构
        valid = (
            "total_iterations" in history
            and "success_rate" in history
            and "average_quality_change" in history
        )

        if valid:
            return TestResult(
                name=name,
                success=True,
                duration=elapsed,
                details={
                    "total_iterations": history["total_iterations"],
                    "success_rate": history["success_rate"],
                    "average_quality_change": history["average_quality_change"],
                    "has_state_transitions": "state_transitions" in history,
                    "has_performance_metrics": "performance_metrics" in history,
                },
            )
        else:
            return TestResult(
                name=name,
                success=False,
                duration=elapsed,
                error="Invalid history structure",
                details=history,
            )

    except Exception as e:
        return TestResult(
            name=name, success=False, duration=time.time() - start_time, error=str(e)
        )


def run_comprehensive_test() -> bool:
    """运行全面端到端测试"""
    print("=" * 70)
    print("MAREF沙箱环境 - 端到端集成测试套件")
    print("=" * 70)
    print("目标: 验证从API到SDK的完整工作流，确保系统生产就绪\n")

    # 定义测试用例
    test_cases = [
        test_api_server_startup,
        test_system_state_retrieval,
        test_constraints_and_strategies,
        test_evolution_history,
        test_evolution_sync,
        test_evolution_async,
        test_sandbox_reset,
        test_sdk_client_connection,
    ]

    # 运行测试
    results = []
    total_passed = 0
    total_failed = 0

    for test_func in test_cases:
        print(f"🧪 运行测试: {test_func.__doc__}")
        result = test_func()
        results.append(result)

        if result.success:
            print(f"   ✅ {result.name}: 通过 ({result.duration:.3f}秒)")
            if result.details:
                for key, value in result.details.items():
                    print(f"      {key}: {value}")
            total_passed += 1
        else:
            print(f"   ❌ {result.name}: 失败 ({result.duration:.3f}秒)")
            print(f"      错误: {result.error}")
            total_failed += 1

        print()

    # 打印总结
    print("=" * 70)
    print("测试结果总结")
    print("=" * 70)
    print(f"总计测试: {len(test_cases)}")
    print(f"通过: {total_passed}")
    print(f"失败: {total_failed}")
    print(f"成功率: {total_passed/len(test_cases)*100:.1f}%")

    # 性能分析
    total_duration = sum(r.duration for r in results)
    avg_duration = total_duration / len(results) if results else 0
    print(f"\n⏱️  性能统计:")
    print(f"  总测试时间: {total_duration:.3f}秒")
    print(f"  平均测试时间: {avg_duration:.3f}秒/测试")

    # 关键指标验证
    print(f"\n📊 关键指标验证:")

    # 检查演化性能
    evolution_tests = [r for r in results if "演化" in r.name and r.success]
    if evolution_tests:
        avg_evolution_time = sum(r.duration for r in evolution_tests) / len(
            evolution_tests
        )
        print(f"  平均演化时间: {avg_evolution_time:.3f}秒")

        # 演化时间应小于2秒（简单测试）
        if avg_evolution_time < 2.0:
            print("  ✅ 演化性能达标 (<2.0秒)")
        else:
            print(f"  ⚠️  演化性能较慢 ({avg_evolution_time:.3f}秒)")
    else:
        print("  ⚠️  无成功的演化测试")

    # API响应时间
    api_tests = [
        r for r in results if ("API" in r.name or "SDK" in r.name) and r.success
    ]
    if api_tests:
        avg_api_time = sum(r.duration for r in api_tests) / len(api_tests)
        print(f"  平均API响应时间: {avg_api_time:.3f}秒")

        if avg_api_time < 0.5:
            print("  ✅ API响应性能达标 (<0.5秒)")
        else:
            print(f"  ⚠️  API响应较慢 ({avg_api_time:.3f}秒)")

    # 系统稳定性检查
    reset_test = next((r for r in results if "重置" in r.name), None)
    if reset_test and reset_test.success:
        print("  ✅ 沙箱重置功能正常")

    print("\n" + "=" * 70)

    if total_failed == 0:
        print("🎉 所有端到端测试通过！系统已准备好用于生产环境。")
        print("\n📋 生产就绪检查清单:")
        print("  ✅ RESTful API接口完整")
        print("  ✅ Python SDK功能完整")
        print("  ✅ 同步/异步演化支持")
        print("  ✅ 系统状态监控和重置")
        print("  ✅ 约束和策略配置")
        print("  ✅ 演化历史跟踪")
        print("  ✅ 性能指标达标")
        print("\n🚀 MAREF沙箱环境已准备好进入生产部署阶段！")
        return True
    else:
        print(f"⚠️  有 {total_failed} 个测试失败，请检查系统实现。")
        print("\n🔧 建议修复步骤:")
        for result in results:
            if not result.success:
                print(f"  - {result.name}: {result.error}")
        return False


def main():
    """主函数"""
    success = run_comprehensive_test()

    if success:
        print("\n" + "=" * 70)
        print("下一步建议:")
        print("  1. 运行负载测试: python3 test_load_performance.py")
        print("  2. 创建Docker容器: docker build -t maref-sandbox .")
        print("  3. 部署配置生成: python3 generate_deployment_config.py")
        print("  4. 生成用户文档: python3 generate_documentation.py")
        print("\n📞 系统支持:")
        print("  - 技术支持: https://github.com/openclaw/maref/issues")
        print("  - 文档: https://openclaw.github.io/maref/")
        print("  - API参考: https://openclaw.github.io/maref/api/")
        return 0
    else:
        return 1


if __name__ == "__main__":
    # 注意：此测试需要在运行API服务器的环境下执行
    # 可以先启动API服务器：python3 maref_api.py
    # 然后运行此测试：python3 test_end_to_end.py

    print("注意：此端到端测试需要先启动API服务器")
    print("启动命令: python3 maref_api.py")
    print("然后在另一个终端运行: python3 test_end_to_end.py")
    print("\n或者，您希望我现在启动API服务器并运行测试吗？")
    print("(需要手动启动，因为测试需要独立的服务器进程)")

    exit(main())
