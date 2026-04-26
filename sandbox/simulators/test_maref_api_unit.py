#!/usr/bin/env python3
"""MAREF沙箱环境API单元测试（使用Flask测试客户端）"""

import sys
import time
import json
from unittest.mock import patch, MagicMock

# 添加当前目录到Python路径
sys.path.insert(0, ".")

from maref_api import app, get_sandbox, _evolution_tasks, _task_lock, _sandbox_instance
from sandbox_manager import (
    SandboxManager,
    EvolutionStrategy,
    SystemState,
    EvolutionResult,
)
from integrated_hexagram_state_manager import HetuState


class TestMAREFAPI:
    """MAREF API单元测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建测试客户端
        self.client = app.test_client()
        app.testing = True

        # 重置全局状态
        with _task_lock:
            _evolution_tasks.clear()

        global _sandbox_instance
        _sandbox_instance = None

    def test_health_endpoint(self):
        """测试健康检查端点"""
        response = self.client.get("/health")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "maref-sandbox-api"
        assert data["version"] == "1.0.0"

    def test_get_state_endpoint(self):
        """测试状态获取端点"""
        # 模拟沙箱管理器
        mock_sandbox = MagicMock()
        mock_state = SystemState(
            current_state="010101",
            quality_score=7.5,
            stability_index=0.85,
            hetu_state=HetuState.AST_PARSED,
            active_dimensions=[True, False, True, False, True, False],
            timestamp=time.time(),
        )
        mock_sandbox.get_system_state.return_value = mock_state

        with patch("maref_api.get_sandbox", return_value=mock_sandbox):
            response = self.client.get("/sandbox/state")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["current_state"] == "010101"
            assert data["quality_score"] == 7.5
            assert data["stability_index"] == 0.85
            assert data["hetu_state"] == "AST_PARSED"
            assert "timestamp" in data

    def test_get_history_endpoint(self):
        """测试历史获取端点"""
        mock_sandbox = MagicMock()
        mock_monitor = MagicMock()
        mock_sandbox.monitor = mock_monitor

        mock_monitor.generate_report.return_value = {
            "total_iterations": 100,
            "success_rate": 0.85,
            "average_quality_change": 0.5,
            "constraint_violations": 3,
        }
        mock_monitor.state_transitions = [
            {"from_state": "000000", "to_state": "000001", "quality_delta": 1.5}
        ]
        mock_monitor.performance_metrics = {
            "iteration_times": [0.1, 0.2, 0.15],
            "quality_changes": [1.5, 0.5, -0.2],
            "control_signals": [0.8, 0.6, 0.9],
            "constraint_violations": [False, False, True],
        }

        with patch("maref_api.get_sandbox", return_value=mock_sandbox):
            response = self.client.get("/sandbox/history")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["total_iterations"] == 100
            assert data["success_rate"] == 0.85
            assert data["average_quality_change"] == 0.5
            assert data["constraint_violations"] == 3
            assert len(data["state_transitions"]) == 1
            assert "performance_metrics" in data

    def test_evolve_endpoint_valid_request(self):
        """测试演化端点（有效请求）"""
        response = self.client.post(
            "/sandbox/evolve",
            json={"target_quality": 8.0, "max_iterations": 50, "strategy": "greedy"},
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "task_id" in data
        assert data["status"] == "started"
        assert data["message"] == "Evolution task started in background"
        assert "params" in data

        # 验证任务已创建
        task_id = data["task_id"]
        with _task_lock:
            assert task_id in _evolution_tasks
            assert _evolution_tasks[task_id]["status"] == "running"

    def test_evolve_endpoint_invalid_parameters(self):
        """测试演化端点（无效参数）"""
        # 目标质量超出范围
        response = self.client.post("/sandbox/evolve", json={"target_quality": 15.0})
        assert response.status_code == 400

        # 最大迭代次数为负
        response = self.client.post("/sandbox/evolve", json={"max_iterations": -5})
        assert response.status_code == 400

        # 无效策略
        response = self.client.post(
            "/sandbox/evolve", json={"strategy": "invalid_strategy"}
        )
        assert response.status_code == 400

    def test_get_task_status_endpoint(self):
        """测试任务状态端点"""
        # 先创建任务
        response = self.client.post("/sandbox/evolve", json={"target_quality": 7.5})
        assert response.status_code == 200
        task_id = json.loads(response.data)["task_id"]

        # 获取任务状态
        response = self.client.get(f"/sandbox/tasks/{task_id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["task_id"] == task_id
        assert data["status"] == "running"
        assert "params" in data
        assert "created_at" in data
        assert "elapsed_seconds" in data

    def test_get_task_status_not_found(self):
        """测试任务状态端点（任务不存在）"""
        response = self.client.get("/sandbox/tasks/invalid_task_id")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data

    def test_list_tasks_endpoint(self):
        """测试任务列表端点"""
        # 创建几个任务
        for i in range(3):
            response = self.client.post(
                "/sandbox/evolve", json={"target_quality": 6.0 + i}
            )
            assert response.status_code == 200

        # 获取任务列表
        response = self.client.get("/sandbox/tasks")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "total_tasks" in data
        assert "tasks" in data
        assert len(data["tasks"]) <= 50  # 最多返回50个

    def test_reset_endpoint(self):
        """测试重置端点"""
        # 模拟沙箱管理器
        mock_sandbox = MagicMock()
        mock_state = SystemState(
            current_state="101010",
            quality_score=5.0,
            stability_index=0.5,
            hetu_state=HetuState.INITIAL,
            active_dimensions=[False, True, False, True, False, True],
            timestamp=time.time(),
        )
        mock_sandbox.get_system_state.return_value = mock_state

        with patch("maref_api.SandboxManager", return_value=mock_sandbox):
            response = self.client.post("/sandbox/reset")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["message"] == "Sandbox reset successfully"
            assert data["new_state"] == "101010"

            # 验证任务历史已清空
            with _task_lock:
                assert len(_evolution_tasks) == 0

    def test_get_constraints_endpoint(self):
        """测试约束获取端点"""
        mock_sandbox = MagicMock()
        mock_sandbox.stability_constraints = {
            "max_hamming_distance": 1,
            "max_quality_drop": 0.5,
            "max_transition_rate": 10.0,
        }

        with patch("maref_api.get_sandbox", return_value=mock_sandbox):
            response = self.client.get("/sandbox/constraints")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["max_hamming_distance"] == 1
            assert data["max_quality_drop"] == 0.5
            assert data["max_transition_rate"] == 10.0

    def test_get_strategies_endpoint(self):
        """测试策略获取端点"""
        response = self.client.get("/sandbox/strategies")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "available_strategies" in data

        strategies = data["available_strategies"]
        assert len(strategies) >= 2

        # 验证策略信息
        strategy_names = [s["name"] for s in strategies]
        assert "greedy" in strategy_names
        assert "simulated_annealing" in strategy_names

        for strategy in strategies:
            assert "name" in strategy
            assert "description" in strategy
            assert "parameters" in strategy

    def test_evolve_execution_simulation(self):
        """测试演化执行模拟"""
        # 创建任务
        response = self.client.post("/sandbox/evolve", json={"target_quality": 8.0})
        assert response.status_code == 200

        task_data = json.loads(response.data)
        task_id = task_data["task_id"]

        # 模拟演化完成
        with _task_lock:
            _evolution_tasks[task_id]["status"] = "completed"
            _evolution_tasks[task_id]["result"] = {
                "success": True,
                "final_quality": 8.5,
                "iterations": 25,
                "execution_time": 3.14,
                "stability_violations": 0,
                "path": ["000000", "000001", "000011"],
                "quality_timeline": [5.0, 6.5, 8.5],
                "control_signals": [0.5, 0.7, 0.9],
            }
            _evolution_tasks[task_id]["completed_at"] = time.time()

        # 获取任务状态
        response = self.client.get(f"/sandbox/tasks/{task_id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "completed"
        assert "result" in data

        result = data["result"]
        assert result["success"] == True
        assert result["final_quality"] == 8.5
        assert result["iterations"] == 25
        assert result["execution_time"] == 3.14

    def test_evolve_execution_failure(self):
        """测试演化执行失败"""
        # 创建任务
        response = self.client.post("/sandbox/evolve", json={"target_quality": 8.0})
        assert response.status_code == 200

        task_data = json.loads(response.data)
        task_id = task_data["task_id"]

        # 模拟演化失败
        with _task_lock:
            _evolution_tasks[task_id]["status"] = "failed"
            _evolution_tasks[task_id]["error"] = "模拟演化失败"
            _evolution_tasks[task_id]["completed_at"] = time.time()

        # 获取任务状态
        response = self.client.get(f"/sandbox/tasks/{task_id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "failed"
        assert "error" in data
        assert data["error"] == "模拟演化失败"


def run_all_tests():
    """运行所有单元测试"""
    import pytest
    import os

    # 使用pytest运行测试
    test_file = __file__
    return os.system(f"python -m pytest {test_file} -v")


if __name__ == "__main__":
    # 简单运行所有测试方法
    test_class = TestMAREFAPI()

    test_methods = [method for method in dir(test_class) if method.startswith("test_")]

    print("=" * 60)
    print("MAREF API单元测试套件")
    print("=" * 60)

    passed = 0
    failed = 0

    for method_name in test_methods:
        test_class.setup_method()
        method = getattr(test_class, method_name)

        try:
            method()
            print(f"✅ {method_name}: 通过")
            passed += 1
        except Exception as e:
            print(f"❌ {method_name}: 失败 - {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"总计: {len(test_methods)} 个测试")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"成功率: {passed/len(test_methods)*100:.1f}%")

    if failed == 0:
        print("\n🎉 所有单元测试通过！")
        sys.exit(0)
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        sys.exit(1)
