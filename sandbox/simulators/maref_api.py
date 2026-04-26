#!/usr/bin/env python3
"""MAREF沙箱环境RESTful API服务"""

import json
import threading
import time
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS

# 导入沙箱管理器
from sandbox_manager import (
    SandboxManager,
    EvolutionStrategy,
    SystemState,
    EvolutionResult,
)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局沙箱管理器实例（单例模式）
_sandbox_instance: Optional[SandboxManager] = None
_sandbox_lock = threading.Lock()

# 演化任务状态跟踪
_evolution_tasks: Dict[str, Dict[str, Any]] = {}
_task_id_counter = 0
_task_lock = threading.Lock()


def get_sandbox() -> SandboxManager:
    """获取或创建沙箱管理器实例（懒加载）"""
    global _sandbox_instance
    with _sandbox_lock:
        if _sandbox_instance is None:
            print("初始化沙箱管理器...")
            _sandbox_instance = SandboxManager("hetu_hexagram_mapping.json")
            print(
                f"沙箱管理器初始化完成，当前状态: {_sandbox_instance.get_system_state().current_state}"
            )
        return _sandbox_instance


def _execute_evolution(task_id: str, params: Dict[str, Any]) -> None:
    """在后台线程中执行演化任务"""
    try:
        sandbox = get_sandbox()

        # 解析参数
        target_quality = params.get("target_quality", 8.0)
        max_iterations = params.get("max_iterations", 100)
        strategy_name = params.get("strategy", "greedy")

        # 映射策略名称
        strategy_map = {
            "greedy": EvolutionStrategy.GREEDY,
            "simulated_annealing": EvolutionStrategy.SIMULATED_ANNEALING,
            "genetic": EvolutionStrategy.GENETIC,  # 未来支持
        }
        strategy = strategy_map.get(strategy_name, EvolutionStrategy.GREEDY)

        # 执行演化
        start_time = time.time()
        result = sandbox.evolve(
            target_quality=target_quality,
            max_iterations=max_iterations,
            strategy=strategy,
        )
        execution_time = time.time() - start_time

        # 更新任务状态
        with _task_lock:
            _evolution_tasks[task_id]["status"] = "completed"
            _evolution_tasks[task_id]["result"] = {
                "success": result.success,
                "final_quality": float(result.final_quality),
                "iterations": result.iterations,
                "execution_time": float(execution_time),
                "stability_violations": result.stability_violations,
                "path": result.path,
                "quality_timeline": [float(q) for q in result.quality_timeline],
                "control_signals": (
                    [float(c) for c in result.control_signals]
                    if hasattr(result, "control_signals")
                    else []
                ),
            }
            _evolution_tasks[task_id]["completed_at"] = time.time()

    except Exception as e:
        with _task_lock:
            _evolution_tasks[task_id]["status"] = "failed"
            _evolution_tasks[task_id]["error"] = str(e)
            _evolution_tasks[task_id]["completed_at"] = time.time()


@app.route("/health", methods=["GET"])
def health_check():
    """健康检查端点"""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "maref-sandbox-api",
            "version": "1.0.0",
        }
    )


@app.route("/sandbox/state", methods=["GET"])
def get_state():
    """获取当前系统状态"""
    try:
        sandbox = get_sandbox()
        system_state = sandbox.get_system_state()

        return jsonify(
            {
                "current_state": system_state.current_state,
                "quality_score": float(system_state.quality_score),
                "stability_index": float(system_state.stability_index),
                "hetu_state": system_state.hetu_state.name,
                "timestamp": time.time(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sandbox/history", methods=["GET"])
def get_history():
    """获取演化历史"""
    try:
        sandbox = get_sandbox()
        monitor = sandbox.monitor

        # 从监控系统获取历史数据
        report = monitor.generate_report()

        return jsonify(
            {
                "total_iterations": report.get("total_iterations", 0),
                "success_rate": report.get("success_rate", 0.0),
                "average_quality_change": report.get("average_quality_change", 0.0),
                "constraint_violations": report.get("constraint_violations", 0),
                "state_transitions": monitor.state_transitions[-50:],  # 最近50次转换
                "performance_metrics": {
                    "iteration_times": monitor.performance_metrics["iteration_times"][
                        -50:
                    ],
                    "quality_changes": monitor.performance_metrics["quality_changes"][
                        -50:
                    ],
                    "control_signals": monitor.performance_metrics["control_signals"][
                        -50:
                    ],
                },
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sandbox/evolve", methods=["POST"])
def evolve():
    """启动演化过程"""
    try:
        # 解析请求参数
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON data"}), 400

        target_quality = data.get("target_quality", 8.0)
        max_iterations = data.get("max_iterations", 100)
        strategy = data.get("strategy", "greedy")

        # 参数验证
        if not (0 <= target_quality <= 10):
            return jsonify({"error": "target_quality must be between 0 and 10"}), 400
        if max_iterations <= 0:
            return jsonify({"error": "max_iterations must be positive"}), 400
        if strategy not in ["greedy", "simulated_annealing"]:
            return (
                jsonify(
                    {"error": "strategy must be 'greedy' or 'simulated_annealing'"}
                ),
                400,
            )

        # 创建任务
        with _task_lock:
            global _task_id_counter
            task_id = f"task_{_task_id_counter:06d}"
            _task_id_counter += 1

            _evolution_tasks[task_id] = {
                "status": "running",
                "params": {
                    "target_quality": target_quality,
                    "max_iterations": max_iterations,
                    "strategy": strategy,
                },
                "created_at": time.time(),
                "started_at": time.time(),
                "result": None,
                "error": None,
            }

        # 在后台线程中执行演化
        thread = threading.Thread(
            target=_execute_evolution,
            args=(task_id, _evolution_tasks[task_id]["params"]),
            daemon=True,
        )
        thread.start()

        return jsonify(
            {
                "task_id": task_id,
                "status": "started",
                "message": "Evolution task started in background",
                "params": _evolution_tasks[task_id]["params"],
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sandbox/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """获取任务状态"""
    with _task_lock:
        if task_id not in _evolution_tasks:
            return jsonify({"error": "Task not found"}), 404

        task_info = _evolution_tasks[task_id].copy()

        # 计算运行时间
        current_time = time.time()
        if task_info["status"] == "running":
            elapsed = current_time - task_info["started_at"]
            task_info["elapsed_seconds"] = elapsed
        elif "completed_at" in task_info:
            elapsed = task_info["completed_at"] - task_info["started_at"]
            task_info["elapsed_seconds"] = elapsed

        # 清理敏感信息
        if "params" in task_info and "result" in task_info:
            # 只返回基本信息
            response = {
                "task_id": task_id,
                "status": task_info["status"],
                "params": task_info["params"],
                "created_at": task_info["created_at"],
                "elapsed_seconds": task_info.get("elapsed_seconds", 0),
            }

            if task_info["status"] == "completed":
                response["result"] = task_info["result"]
            elif task_info["status"] == "failed":
                response["error"] = task_info.get("error", "Unknown error")

            return jsonify(response)
        else:
            return jsonify(task_info)


@app.route("/sandbox/tasks", methods=["GET"])
def list_tasks():
    """列出所有任务"""
    with _task_lock:
        tasks = []
        for task_id, task_info in _evolution_tasks.items():
            tasks.append(
                {
                    "task_id": task_id,
                    "status": task_info["status"],
                    "params": task_info["params"],
                    "created_at": task_info["created_at"],
                }
            )

        return jsonify(
            {
                "total_tasks": len(tasks),
                "tasks": sorted(tasks, key=lambda x: x["created_at"], reverse=True)[
                    :50
                ],  # 最近50个任务
            }
        )


@app.route("/sandbox/reset", methods=["POST"])
def reset_sandbox():
    """重置沙箱状态"""
    try:
        global _sandbox_instance
        with _sandbox_lock:
            # 创建新的沙箱实例
            _sandbox_instance = SandboxManager("hetu_hexagram_mapping.json")

            # 清空任务历史（可选）
            with _task_lock:
                _evolution_tasks.clear()

            return jsonify(
                {
                    "message": "Sandbox reset successfully",
                    "new_state": _sandbox_instance.get_system_state().current_state,
                }
            )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sandbox/constraints", methods=["GET"])
def get_constraints():
    """获取当前约束设置"""
    try:
        sandbox = get_sandbox()
        return jsonify(sandbox.stability_constraints)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sandbox/strategies", methods=["GET"])
def get_strategies():
    """获取可用演化策略"""
    return jsonify(
        {
            "available_strategies": [
                {
                    "name": "greedy",
                    "description": "贪心策略：选择立即质量提升最大的转换",
                    "parameters": [],
                },
                {
                    "name": "simulated_annealing",
                    "description": "模拟退火：允许暂时质量下降以跳出局部最优",
                    "parameters": [],
                },
                {
                    "name": "genetic",
                    "description": "遗传算法：使用遗传算法优化多维度质量",
                    "parameters": [],
                },
                {
                    "name": "multi_objective",
                    "description": "多目标优化：同时优化质量、稳定性和多样性",
                    "parameters": [],
                },
            ]
        }
    )


if __name__ == "__main__":
    print("=" * 60)
    print("MAREF沙箱环境API服务")
    print("=" * 60)
    print("API端点:")
    print("  GET  /health                    - 健康检查")
    print("  GET  /sandbox/state             - 获取当前系统状态")
    print("  GET  /sandbox/history           - 获取演化历史")
    print("  POST /sandbox/evolve            - 启动演化过程")
    print("  GET  /sandbox/tasks/<task_id>   - 获取任务状态")
    print("  GET  /sandbox/tasks             - 列出所有任务")
    print("  POST /sandbox/reset             - 重置沙箱状态")
    print("  GET  /sandbox/constraints       - 获取约束设置")
    print("  GET  /sandbox/strategies        - 获取可用策略")
    print("\n启动服务器...")

    # 启动Flask应用
    app.run(host="0.0.0.0", port=5001, debug=True)
