#!/usr/bin/env python3
"""MAREF沙箱环境API测试套件"""

import sys
import time
import subprocess
import threading
import requests
import json
from typing import Optional

# 导入SDK进行测试
from maref_sdk import (
    SandboxClient,
    SystemState,
    EvolutionResult,
    TaskStatus,
    EvolutionStrategy,
)


class TestAPIServer:
    """API服务器测试工具类"""

    def __init__(self, host="localhost", port=5001):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.process: Optional[subprocess.Popen] = None

    def start(self):
        """启动API服务器"""
        print(f"启动API服务器: {self.base_url}")

        # 启动Flask服务器作为子进程
        cmd = [sys.executable, "maref_api.py"]
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # 等待服务器启动
        for _ in range(30):  # 最多等待30秒
            try:
                response = requests.get(f"{self.base_url}/health", timeout=1)
                if response.status_code == 200:
                    print("API服务器启动成功")
                    return True
            except requests.exceptions.ConnectionError:
                time.sleep(1)

        print("API服务器启动超时")
        return False

    def stop(self):
        """停止API服务器"""
        if self.process:
            print("停止API服务器")
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None


def test_health_endpoint():
    """测试健康检查端点"""
    print("=== 测试健康检查端点 ===")

    try:
        # 创建客户端
        client = SandboxClient()

        # 调用健康检查
        health = client.health_check()

        # 验证响应
        assert health["status"] == "healthy", f"健康状态异常: {health}"
        assert "timestamp" in health, "缺少时间戳字段"
        assert (
            health["service"] == "maref-sandbox-api"
        ), f"服务名称错误: {health['service']}"

        print(f"✅ 健康检查成功: {health['status']}")
        return True

    except Exception as e:
        print(f"❌ 健康检查测试失败: {e}")
        return False


def test_state_endpoint():
    """测试状态获取端点"""
    print("\n=== 测试状态获取端点 ===")

    try:
        client = SandboxClient()

        # 获取当前状态
        state = client.get_state()

        # 验证SystemState数据结构
        assert isinstance(state, SystemState), f"状态类型错误: {type(state)}"
        assert len(state.current_state) == 6, f"状态长度错误: {state.current_state}"
        assert 0 <= state.quality_score <= 10, f"质量评分超范围: {state.quality_score}"
        assert (
            0 <= state.stability_index <= 1
        ), f"稳定性指数超范围: {state.stability_index}"
        assert state.timestamp > 0, f"时间戳无效: {state.timestamp}"

        print(
            f"✅ 状态获取成功: {state.current_state}, 质量: {state.quality_score:.2f}"
        )
        return True

    except Exception as e:
        print(f"❌ 状态获取测试失败: {e}")
        return False


def test_history_endpoint():
    """测试历史获取端点"""
    print("\n=== 测试历史获取端点 ===")

    try:
        client = SandboxClient()

        # 获取历史数据
        history = client.get_history()

        # 验证历史数据结构
        assert "total_iterations" in history, "缺少总迭代次数"
        assert "success_rate" in history, "缺少成功率"
        assert "average_quality_change" in history, "缺少平均质量变化"
        assert "constraint_violations" in history, "缺少约束违反次数"
        assert "state_transitions" in history, "缺少状态转换记录"
        assert "performance_metrics" in history, "缺少性能指标"

        # 验证性能指标结构
        metrics = history["performance_metrics"]
        assert "iteration_times" in metrics, "缺少迭代时间"
        assert "quality_changes" in metrics, "缺少质量变化"
        assert "control_signals" in metrics, "缺少控制信号"

        print(
            f"✅ 历史获取成功: {history['total_iterations']} 次迭代, 成功率: {history['success_rate']:.1%}"
        )
        return True

    except Exception as e:
        print(f"❌ 历史获取测试失败: {e}")
        return False


def test_async_evolution():
    """测试异步演化端点"""
    print("\n=== 测试异步演化端点 ===")

    try:
        client = SandboxClient()

        # 启动异步演化
        task_id = client.evolve_async(
            target_quality=7.5, max_iterations=20, strategy=EvolutionStrategy.GREEDY
        )

        print(f"异步演化任务已启动，任务ID: {task_id}")

        # 检查任务状态
        for i in range(10):  # 最多等待10秒
            time.sleep(1)
            status = client.get_task_status(task_id)
            print(
                f"  轮询 {i+1}: 状态={status.status}, 运行时间={status.elapsed_seconds:.1f}s"
            )

            if status.status == "completed":
                print(f"✅ 异步演化完成: 最终质量={status.result.final_quality:.2f}")
                assert status.result is not None, "完成的任务缺少结果"
                assert isinstance(status.result, EvolutionResult), "结果类型错误"
                return True
            elif status.status == "failed":
                print(f"❌ 异步演化失败: {status.error}")
                return False

        print("❌ 异步演化超时")
        return False

    except Exception as e:
        print(f"❌ 异步演化测试失败: {e}")
        return False


def test_sync_evolution():
    """测试同步演化端点"""
    print("\n=== 测试同步演化端点 ===")

    try:
        client = SandboxClient()

        # 启动同步演化（带超时）
        result = client.evolve(
            target_quality=7.0,
            max_iterations=15,
            strategy=EvolutionStrategy.SIMULATED_ANNEALING,
            timeout=30,
        )

        # 验证演化结果
        assert isinstance(result, EvolutionResult), f"演化结果类型错误: {type(result)}"
        assert (
            0 <= result.final_quality <= 10
        ), f"最终质量超范围: {result.final_quality}"
        assert result.iterations <= 15, f"迭代次数超限: {result.iterations}"
        assert result.execution_time > 0, f"执行时间为负: {result.execution_time}"
        assert len(result.path) >= 1, f"路径为空: {result.path}"
        assert len(result.quality_timeline) == len(
            result.path
        ), "质量时间线与路径长度不匹配"

        print(
            f"✅ 同步演化成功: 最终质量={result.final_quality:.2f}, 迭代次数={result.iterations}"
        )
        return True

    except TimeoutError as e:
        print(f"❌ 同步演化超时: {e}")
        return False
    except Exception as e:
        print(f"❌ 同步演化测试失败: {e}")
        return False


def test_task_management():
    """测试任务管理端点"""
    print("\n=== 测试任务管理端点 ===")

    try:
        client = SandboxClient()

        # 启动多个异步任务
        task_ids = []
        for i in range(3):
            task_id = client.evolve_async(
                target_quality=6.0 + i * 0.5,
                max_iterations=10,
                strategy=EvolutionStrategy.GREEDY,
            )
            task_ids.append(task_id)
            print(f"  启动任务 {i+1}: {task_id}")

        # 获取任务列表
        tasks = client.list_tasks(limit=5)

        # 验证任务列表结构
        assert isinstance(tasks, list), f"任务列表类型错误: {type(tasks)}"
        assert len(tasks) > 0, "任务列表为空"

        for task in tasks:
            assert "task_id" in task, "任务缺少ID"
            assert "status" in task, "任务缺少状态"
            assert "params" in task, "任务缺少参数"
            assert "created_at" in task, "任务缺少创建时间"

        # 检查特定任务状态
        for task_id in task_ids[:2]:  # 只检查前两个任务
            status = client.get_task_status(task_id)
            assert (
                status.task_id == task_id
            ), f"任务ID不匹配: {status.task_id} != {task_id}"
            assert status.status in [
                "running",
                "completed",
                "failed",
            ], f"无效状态: {status.status}"

            if status.status == "completed":
                assert status.result is not None, "完成的任务缺少结果"

        print(f"✅ 任务管理测试成功: 共{len(tasks)}个任务")
        return True

    except Exception as e:
        print(f"❌ 任务管理测试失败: {e}")
        return False


def test_reset_endpoint():
    """测试重置端点"""
    print("\n=== 测试重置端点 ===")

    try:
        client = SandboxClient()

        # 获取重置前的状态
        before_reset = client.get_state()

        # 执行重置
        reset_result = client.reset()

        # 验证重置响应
        assert "message" in reset_result, "重置响应缺少消息"
        assert "new_state" in reset_result, "重置响应缺少新状态"

        # 获取重置后的状态
        after_reset = client.get_state()

        print(f"✅ 重置成功: {reset_result['message']}")
        print(f"   重置前状态: {before_reset.current_state}")
        print(f"   重置后状态: {after_reset.current_state}")
        print(f"   新状态: {reset_result['new_state']}")

        # 注意：由于沙箱初始化是随机的，状态可能相同也可能不同
        return True

    except Exception as e:
        print(f"❌ 重置测试失败: {e}")
        return False


def test_constraints_endpoint():
    """测试约束获取端点"""
    print("\n=== 测试约束获取端点 ===")

    try:
        client = SandboxClient()

        # 获取约束设置
        constraints = client.get_constraints()

        # 验证约束结构
        assert isinstance(constraints, dict), f"约束类型错误: {type(constraints)}"
        assert "max_hamming_distance" in constraints, "缺少汉明距离约束"
        assert "min_quality" in constraints, "缺少最小质量约束"
        assert "max_quality" in constraints, "缺少最大质量约束"
        assert "max_iterations_per_second" in constraints, "缺少每秒最大迭代次数约束"
        assert "rollback_on_violation" in constraints, "缺少违反约束时自动回滚设置"

        # 验证约束值范围
        assert (
            constraints["max_hamming_distance"] == 1
        ), f"汉明距离应为1: {constraints['max_hamming_distance']}"
        assert (
            constraints["min_quality"] >= 0
        ), f"最小质量应为非负: {constraints['min_quality']}"
        assert (
            constraints["max_quality"] <= 10
        ), f"最大质量应≤10: {constraints['max_quality']}"
        assert (
            constraints["max_iterations_per_second"] > 0
        ), f"每秒最大迭代次数应为正数: {constraints['max_iterations_per_second']}"
        assert isinstance(
            constraints["rollback_on_violation"], bool
        ), f"回滚设置应为布尔值: {constraints['rollback_on_violation']}"

        print(f"✅ 约束获取成功:")
        for key, value in constraints.items():
            print(f"   {key}: {value}")

        return True

    except Exception as e:
        print(f"❌ 约束获取测试失败: {e}")
        return False


def test_strategies_endpoint():
    """测试策略获取端点"""
    print("\n=== 测试策略获取端点 ===")

    try:
        client = SandboxClient()

        # 获取可用策略
        strategies = client.get_strategies()

        # 验证策略结构
        assert isinstance(strategies, list), f"策略列表类型错误: {type(strategies)}"
        assert len(strategies) >= 2, f"至少应有2种策略: {len(strategies)}"

        # 验证策略信息
        strategy_names = [s["name"] for s in strategies]
        assert "greedy" in strategy_names, "缺少贪心策略"
        assert "simulated_annealing" in strategy_names, "缺少模拟退火策略"

        for strategy in strategies:
            assert "name" in strategy, "策略缺少名称"
            assert "description" in strategy, "策略缺少描述"
            assert "parameters" in strategy, "策略缺少参数列表"

        print(f"✅ 策略获取成功: 共{len(strategies)}种策略")
        for strategy in strategies:
            print(f"   - {strategy['name']}: {strategy['description']}")

        return True

    except Exception as e:
        print(f"❌ 策略获取测试失败: {e}")
        return False


def test_sdk_client_comprehensive():
    """测试SDK客户端的综合功能"""
    print("\n=== 测试SDK客户端综合功能 ===")

    try:
        # 测试客户端初始化
        client = SandboxClient(base_url="http://localhost:5001", timeout=10)
        assert (
            client.base_url == "http://localhost:5001"
        ), f"基础URL错误: {client.base_url}"
        assert client.timeout == 10, f"超时设置错误: {client.timeout}"

        # 测试健康检查
        health = client.health_check()
        assert health["status"] == "healthy", "健康检查失败"

        # 测试状态获取
        state = client.get_state()
        assert isinstance(state, SystemState), "状态获取失败"

        # 测试等待任务功能
        task_id = client.evolve_async(target_quality=6.5, max_iterations=5)

        try:
            # 使用短超时测试等待功能
            result = client.wait_for_task(task_id, poll_interval=0.5, timeout=5)
            print(f"✅ 任务等待功能测试: 任务完成，最终质量={result.final_quality:.2f}")
        except TimeoutError:
            print("⚠️  任务等待超时（预期内，因为任务可能未完成）")

        # 测试错误处理
        try:
            # 测试无效任务ID
            invalid_status = client.get_task_status("invalid_task_id")
            print(f"❌ 应抛出异常但未抛出: {invalid_status}")
            return False
        except requests.exceptions.HTTPError:
            print("✅ 无效任务ID错误处理正常")

        print("✅ SDK客户端综合测试通过")
        return True

    except Exception as e:
        print(f"❌ SDK客户端综合测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("MAREF沙箱环境API测试套件")
    print("=" * 60)
    print("目标: 验证RESTful API服务和Python SDK的功能正确性\n")

    # 创建API服务器实例
    server = TestAPIServer()

    # 启动服务器
    if not server.start():
        print("❌ API服务器启动失败，无法继续测试")
        return 1

    # 等待服务器完全启动
    time.sleep(2)

    # 运行所有测试
    test_results = []

    # 基础端点测试
    test_results.append(("健康检查端点", test_health_endpoint()))
    test_results.append(("状态获取端点", test_state_endpoint()))
    test_results.append(("历史获取端点", test_history_endpoint()))
    test_results.append(("约束获取端点", test_constraints_endpoint()))
    test_results.append(("策略获取端点", test_strategies_endpoint()))

    # 演化功能测试
    test_results.append(("异步演化端点", test_async_evolution()))
    test_results.append(("同步演化端点", test_sync_evolution()))
    test_results.append(("任务管理端点", test_task_management()))

    # 其他功能测试
    test_results.append(("重置端点", test_reset_endpoint()))
    test_results.append(("SDK客户端综合功能", test_sdk_client_comprehensive()))

    # 停止服务器
    server.stop()

    # 测试结果总结
    print("\n" + "=" * 60)
    print("API测试结果总结")
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
    print(f"总计: {len(test_results)} 个API测试")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"成功率: {passed/len(test_results)*100:.1f}%")

    if failed == 0:
        print("\n🎉 所有API测试通过！RESTful API服务和Python SDK功能正常。")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个API测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit(main())
