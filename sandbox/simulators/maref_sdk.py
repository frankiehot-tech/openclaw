#!/usr/bin/env python3
"""MAREF沙箱环境Python SDK"""

import json
import time
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


@dataclass
class SystemState:
    """系统状态数据类"""

    current_state: str
    quality_score: float
    stability_index: float
    hetu_state: str
    timestamp: float


@dataclass
class EvolutionResult:
    """演化结果数据类"""

    success: bool
    final_quality: float
    iterations: int
    execution_time: float
    stability_violations: int
    path: List[str]
    quality_timeline: List[float]
    control_signals: List[float]


@dataclass
class TaskStatus:
    """任务状态数据类"""

    task_id: str
    status: str  # running, completed, failed
    params: Dict[str, Any]
    elapsed_seconds: float
    result: Optional[EvolutionResult] = None
    error: Optional[str] = None


class EvolutionStrategy(str, Enum):
    """演化策略枚举"""

    GREEDY = "greedy"
    SIMULATED_ANNEALING = "simulated_annealing"
    GENETIC = "genetic"
    MULTI_OBJECTIVE = "multi_objective"


class SandboxClient:
    """MAREF沙箱环境客户端"""

    def __init__(self, base_url: str = "http://localhost:5001", timeout: int = 30):
        """
        初始化沙箱客户端

        Args:
            base_url: API服务基础URL
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        response = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_state(self) -> SystemState:
        """获取当前系统状态"""
        response = self.session.get(
            f"{self.base_url}/sandbox/state", timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        return SystemState(
            current_state=data["current_state"],
            quality_score=data["quality_score"],
            stability_index=data["stability_index"],
            hetu_state=data["hetu_state"],
            timestamp=data["timestamp"],
        )

    def get_history(self) -> Dict[str, Any]:
        """获取演化历史"""
        response = self.session.get(
            f"{self.base_url}/sandbox/history", timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def evolve(
        self,
        target_quality: float = 8.0,
        max_iterations: int = 100,
        strategy: EvolutionStrategy = EvolutionStrategy.GREEDY,
        poll_interval: float = 1.0,
        timeout: Optional[float] = None,
    ) -> EvolutionResult:
        """
        启动演化过程并等待完成

        Args:
            target_quality: 目标质量 (0-10)
            max_iterations: 最大迭代次数
            strategy: 演化策略
            poll_interval: 轮询间隔（秒）
            timeout: 总超时时间（秒），None表示无超时

        Returns:
            EvolutionResult: 演化结果

        Raises:
            TimeoutError: 超时
            RuntimeError: 演化失败
        """
        # 启动演化任务
        response = self.session.post(
            f"{self.base_url}/sandbox/evolve",
            json={
                "target_quality": target_quality,
                "max_iterations": max_iterations,
                "strategy": strategy.value,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        task_data = response.json()
        task_id = task_data["task_id"]

        # 轮询任务状态
        start_time = time.time()
        while True:
            # 检查超时
            if timeout is not None and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Evolution timeout after {timeout} seconds")

            # 获取任务状态
            task_status = self.get_task_status(task_id)

            if task_status.status == "completed":
                if task_status.result is None:
                    raise RuntimeError("Task completed but no result available")
                return task_status.result

            elif task_status.status == "failed":
                raise RuntimeError(f"Evolution failed: {task_status.error}")

            # 任务仍在运行，等待后继续轮询
            time.sleep(poll_interval)

    def evolve_async(
        self,
        target_quality: float = 8.0,
        max_iterations: int = 100,
        strategy: EvolutionStrategy = EvolutionStrategy.GREEDY,
    ) -> str:
        """
        异步启动演化过程（立即返回任务ID）

        Args:
            target_quality: 目标质量 (0-10)
            max_iterations: 最大迭代次数
            strategy: 演化策略

        Returns:
            str: 任务ID
        """
        response = self.session.post(
            f"{self.base_url}/sandbox/evolve",
            json={
                "target_quality": target_quality,
                "max_iterations": max_iterations,
                "strategy": strategy.value,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["task_id"]

    def get_task_status(self, task_id: str) -> TaskStatus:
        """获取任务状态"""
        response = self.session.get(
            f"{self.base_url}/sandbox/tasks/{task_id}", timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # 解析演化结果（如果存在）
        result = None
        if data["status"] == "completed" and "result" in data:
            result_data = data["result"]
            result = EvolutionResult(
                success=result_data["success"],
                final_quality=result_data["final_quality"],
                iterations=result_data["iterations"],
                execution_time=result_data["execution_time"],
                stability_violations=result_data["stability_violations"],
                path=result_data["path"],
                quality_timeline=result_data["quality_timeline"],
                control_signals=result_data.get("control_signals", []),
            )

        return TaskStatus(
            task_id=task_id,
            status=data["status"],
            params=data["params"],
            elapsed_seconds=data.get("elapsed_seconds", 0),
            result=result,
            error=data.get("error"),
        )

    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出所有任务"""
        response = self.session.get(
            f"{self.base_url}/sandbox/tasks", timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        return data["tasks"][:limit]

    def reset(self) -> Dict[str, Any]:
        """重置沙箱状态"""
        response = self.session.post(
            f"{self.base_url}/sandbox/reset", timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_constraints(self) -> Dict[str, Any]:
        """获取约束设置"""
        response = self.session.get(
            f"{self.base_url}/sandbox/constraints", timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_strategies(self) -> List[Dict[str, Any]]:
        """获取可用演化策略"""
        response = self.session.get(
            f"{self.base_url}/sandbox/strategies", timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()["available_strategies"]

    def wait_for_task(
        self, task_id: str, poll_interval: float = 1.0, timeout: Optional[float] = None
    ) -> EvolutionResult:
        """
        等待任务完成

        Args:
            task_id: 任务ID
            poll_interval: 轮询间隔（秒）
            timeout: 总超时时间（秒）

        Returns:
            EvolutionResult: 演化结果

        Raises:
            TimeoutError: 超时
            RuntimeError: 任务失败
        """
        start_time = time.time()
        while True:
            # 检查超时
            if timeout is not None and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Task timeout after {timeout} seconds")

            task_status = self.get_task_status(task_id)

            if task_status.status == "completed":
                if task_status.result is None:
                    raise RuntimeError("Task completed but no result available")
                return task_status.result

            elif task_status.status == "failed":
                raise RuntimeError(f"Task failed: {task_status.error}")

            time.sleep(poll_interval)


# 使用示例
if __name__ == "__main__":
    # 创建客户端
    client = SandboxClient()

    # 健康检查
    health = client.health_check()
    print(f"服务状态: {health['status']}")

    # 获取当前状态
    state = client.get_state()
    print(f"当前状态: {state.current_state}, 质量: {state.quality_score:.2f}")

    # 启动演化（同步）
    try:
        print("启动同步演化...")
        result = client.evolve(
            target_quality=8.5,
            max_iterations=50,
            strategy=EvolutionStrategy.SIMULATED_ANNEALING,
            timeout=30,
        )
        print(f"演化成功: {result.success}")
        print(f"最终质量: {result.final_quality:.2f}")
        print(f"迭代次数: {result.iterations}")
        print(f"路径长度: {len(result.path)}")
    except Exception as e:
        print(f"演化失败: {e}")

    # 启动演化（异步）
    print("\n启动异步演化...")
    task_id = client.evolve_async(
        target_quality=7.0, max_iterations=30, strategy=EvolutionStrategy.GREEDY
    )
    print(f"任务ID: {task_id}")

    # 轮询任务状态
    for i in range(5):
        time.sleep(1)
        status = client.get_task_status(task_id)
        print(f"任务状态: {status.status}, 运行时间: {status.elapsed_seconds:.1f}秒")
        if status.status == "completed":
            break

    # 列出所有任务
    tasks = client.list_tasks(limit=5)
    print(f"\n最近任务 ({len(tasks)} 个):")
    for task in tasks:
        print(f"  {task['task_id']}: {task['status']}")

    # 获取约束设置
    constraints = client.get_constraints()
    print(f"\n约束设置:")
    for key, value in constraints.items():
        print(f"  {key}: {value}")
