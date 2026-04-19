#!/usr/bin/env python3
"""
Parallel Build Gate - 并行构建门控

提供资源准入、隔离约束和调度摘要，用于安全并行构建。
与现有动态 worker 预算集成，确保并行任务不会超出系统容量。

设计原则：
- 真实指标：基于实际系统负载（CPU、内存、负载）做决策
- 安全隔离：确保并行任务有独立的工作目录和资源边界
- 解释性：提供清晰的决策原因，便于调度器理解
- 渐进增强：先实现最小可行门控，再逐步增加复杂规则
"""

import json
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

# 导入系统资源事实
try:
    from scripts.system_resource_facts import (
        dynamic_build_worker_budget,
        ollama_active_cpu_percent,
        system_free_memory_percent,
        system_load_average,
    )
except ImportError:
    # 回退：将scripts目录添加到路径并重试
    scripts_dir = Path(project_root) / "scripts"
    if scripts_dir.exists():
        sys.path.insert(0, str(scripts_dir.parent))
        from scripts.system_resource_facts import (
            dynamic_build_worker_budget,
            ollama_active_cpu_percent,
            system_free_memory_percent,
            system_load_average,
        )
    else:
        raise ImportError(f"Cannot find scripts directory: {scripts_dir}")


class AdmissionDecision(Enum):
    """准入决策"""

    APPROVED = "approved"  # 允许并行
    REJECTED = "rejected"  # 拒绝并行
    DEGRADED = "degraded"  # 降级（单 worker）
    MANUAL_HOLD = "manual_hold"  # 需要人工审批


class ResourceDimension(Enum):
    """资源维度"""

    CPU = "cpu"
    MEMORY = "memory"
    LOAD = "load"
    OLLAMA = "ollama"
    QUEUE_PRESSURE = "queue_pressure"


class IsolationConstraint(Enum):
    """隔离约束类型"""

    WORKDIR_ISOLATION = "workdir_isolation"
    FILE_WRITE_BOUNDARY = "file_write_boundary"
    RESOURCE_MUTEX = "resource_mutex"
    NETWORK_PORT = "network_port"


@dataclass
class ResourceCheck:
    """资源检查结果"""

    dimension: ResourceDimension
    value: float
    threshold: float
    passed: bool
    reason: str


@dataclass
class AdmissionResult:
    """准入检查结果"""

    decision: AdmissionDecision
    allowed_workers: int  # 允许的 worker 数量（1 或 2）
    reason: str
    resource_checks: List[ResourceCheck]
    suggested_action: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IsolationRule:
    """隔离规则"""

    constraint: IsolationConstraint
    parameters: Dict[str, Any]
    description: str


@dataclass
class SchedulingSummary:
    """调度摘要"""

    current_workers: int
    max_workers: int
    admission_result: AdmissionResult
    active_task_ids: List[str]
    resource_snapshot: Dict[str, Any]
    generated_at: float = field(default_factory=time.time)


class ParallelBuildGate:
    """并行构建门控"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化并行构建门控

        Args:
            config_path: 配置文件路径（可选）
        """
        self.config = self._load_config(config_path)

        # 资源阈值配置（可从环境变量覆盖）
        self.thresholds = {
            "min_free_memory_percent": int(
                os.getenv("PARALLEL_BUILD_MIN_FREE_MEMORY_PERCENT", "35")
            ),
            "max_load_per_core": float(os.getenv("PARALLEL_BUILD_MAX_LOAD_PER_CORE", "0.6")),
            "max_load_absolute": float(os.getenv("PARALLEL_BUILD_MAX_LOAD_ABSOLUTE", "6.0")),
            "ollama_busy_cpu_percent": float(
                os.getenv("PARALLEL_BUILD_OLLAMA_BUSY_CPU_PERCENT", "35")
            ),
            "max_queue_pressure": int(os.getenv("PARALLEL_BUILD_MAX_QUEUE_PRESSURE", "5")),
        }

        # 隔离约束配置
        self.isolation_rules = self._load_isolation_rules()

        # 状态跟踪
        self.active_tasks: Set[str] = set()
        self.task_workspaces: Dict[str, Path] = {}
        self.lock = threading.RLock()

        # 最后决策缓存（防抖动），按 requested_workers 缓存
        self.last_decisions: Dict[int, AdmissionResult] = {}
        self.last_decision_times: Dict[int, float] = {}
        self.decision_cache_ttl = 5  # 秒

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """加载配置文件"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "parallel_build_gate.yaml"

        if config_path.exists():
            try:
                import yaml

                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception:
                pass

        # 返回空配置
        return {}

    def _load_isolation_rules(self) -> List[IsolationRule]:
        """加载隔离规则"""
        rules = [
            IsolationRule(
                constraint=IsolationConstraint.WORKDIR_ISOLATION,
                parameters={
                    "base_dir": "/Volumes/1TB-M2/openclaw/.openclaw/orchestrator/tasks",
                    "prefix_template": "{task_id}",
                    "subdirs": [
                        "workspace",
                        "inputs",
                        "outputs",
                        "evidence",
                        "checkpoints",
                    ],
                },
                description="每个任务必须有独立的工作目录，防止文件覆盖",
            ),
            IsolationRule(
                constraint=IsolationConstraint.FILE_WRITE_BOUNDARY,
                parameters={
                    "allowed_prefixes": ["/Volumes/1TB-M2/openclaw/"],
                    "restricted_prefixes": [
                        "/Volumes/1TB-M2/openclaw/.git/",
                        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/",
                        "/Volumes/1TB-M2/openclaw/mini-agent/config/",
                    ],
                    "readonly_prefixes": [],
                },
                description="任务写入必须限定在允许的目录范围内，保护关键文件",
            ),
            IsolationRule(
                constraint=IsolationConstraint.RESOURCE_MUTEX,
                parameters={
                    "mutex_resources": ["opencode", "codex", "ollama"],
                    "check_interval": 30,
                },
                description="互斥资源检查，防止同一资源被多个任务同时使用",
            ),
        ]

        # 从配置合并
        config_rules = self.config.get("isolation_rules", [])
        for rule_config in config_rules:
            try:
                rule = IsolationRule(
                    constraint=IsolationConstraint(rule_config["constraint"]),
                    parameters=rule_config.get("parameters", {}),
                    description=rule_config.get("description", ""),
                )
                rules.append(rule)
            except Exception:
                pass

        return rules

    def check_admission(self, requested_workers: int = 2) -> AdmissionResult:
        """
        检查并行构建准入

        Args:
            requested_workers: 请求的 worker 数量（默认为2）

        Returns:
            准入检查结果
        """
        # 检查缓存
        with self.lock:
            current_time = time.time()
            last_decision = self.last_decisions.get(requested_workers)
            last_decision_time = self.last_decision_times.get(requested_workers, 0)
            if last_decision and current_time - last_decision_time < self.decision_cache_ttl:
                return last_decision

        # 获取动态 worker 预算（现有逻辑）
        budget, telemetry = dynamic_build_worker_budget(
            max_build_workers=requested_workers,
            second_build_min_free_memory_percent=self.thresholds["min_free_memory_percent"],
            max_build_load_per_core=self.thresholds["max_load_per_core"],
            max_build_load_absolute=self.thresholds["max_load_absolute"],
            ollama_busy_cpu_percent=self.thresholds["ollama_busy_cpu_percent"],
        )

        # 执行详细资源检查
        resource_checks = self._perform_resource_checks(telemetry)

        # 确定决策
        if budget >= requested_workers:
            decision = AdmissionDecision.APPROVED
            reason = telemetry.get("reason", "资源充足，允许并行构建")
            allowed_workers = requested_workers
            suggested_action = "可正常启动并行任务"
        elif budget >= 1:
            decision = AdmissionDecision.DEGRADED
            reason = telemetry.get("reason", "资源有限，降级为单 worker")
            allowed_workers = 1
            suggested_action = "建议单任务执行或等待资源释放"
        else:
            decision = AdmissionDecision.REJECTED
            reason = telemetry.get("reason", "资源不足，拒绝构建")
            allowed_workers = 0
            suggested_action = "等待系统资源恢复或人工干预"

        # 检查队列压力
        queue_pressure = self._check_queue_pressure()
        if queue_pressure and decision == AdmissionDecision.APPROVED:
            if queue_pressure["pressure_level"] == "high":
                decision = AdmissionDecision.DEGRADED
                reason = f"{reason}；队列压力过高，降级为单 worker"
                allowed_workers = 1
                suggested_action = "队列压力过高，建议单任务执行"

        # 构建结果
        result = AdmissionResult(
            decision=decision,
            allowed_workers=allowed_workers,
            reason=reason,
            resource_checks=resource_checks,
            suggested_action=suggested_action,
            metadata={
                "telemetry": telemetry,
                "queue_pressure": queue_pressure,
                "thresholds": self.thresholds,
            },
        )

        # 更新缓存
        with self.lock:
            self.last_decisions[requested_workers] = result
            self.last_decision_times[requested_workers] = time.time()

        return result

    def _perform_resource_checks(self, telemetry: Dict[str, Any]) -> List[ResourceCheck]:
        """执行详细资源检查"""
        checks = []

        # 内存检查
        free_memory = telemetry.get("free_memory_percent")
        if free_memory is not None:
            threshold = self.thresholds["min_free_memory_percent"]
            passed = free_memory >= threshold
            checks.append(
                ResourceCheck(
                    dimension=ResourceDimension.MEMORY,
                    value=free_memory,
                    threshold=threshold,
                    passed=passed,
                    reason=f"可用内存 {free_memory}% {'≥' if passed else '<'} 阈值 {threshold}%",
                )
            )

        # 负载检查
        load_1m = telemetry.get("load_average_1m")
        if load_1m is not None:
            cpu_count = telemetry.get("cpu_count", 1)
            max_load = min(
                self.thresholds["max_load_absolute"],
                cpu_count * self.thresholds["max_load_per_core"],
            )
            passed = load_1m <= max_load
            checks.append(
                ResourceCheck(
                    dimension=ResourceDimension.LOAD,
                    value=load_1m,
                    threshold=max_load,
                    passed=passed,
                    reason=f"1分钟负载 {load_1m:.2f} {'≤' if passed else '>'} 阈值 {max_load:.2f}",
                )
            )

        # Ollama CPU 检查
        ollama_cpu = telemetry.get("ollama_cpu_percent", 0)
        threshold = self.thresholds["ollama_busy_cpu_percent"]
        passed = ollama_cpu < threshold
        checks.append(
            ResourceCheck(
                dimension=ResourceDimension.OLLAMA,
                value=ollama_cpu,
                threshold=threshold,
                passed=passed,
                reason=f"Ollama CPU 使用率 {ollama_cpu:.1f}% {'<' if passed else '≥'} 阈值 {threshold:.1f}%",
            )
        )

        return checks

    def _check_queue_pressure(self) -> Optional[Dict[str, Any]]:
        """检查队列压力"""
        # 获取活跃任务数量
        with self.lock:
            active_count = len(self.active_tasks)

        # 简单压力等级
        pressure_level = "low"
        if active_count >= self.thresholds["max_queue_pressure"]:
            pressure_level = "high"
        elif active_count >= self.thresholds["max_queue_pressure"] // 2:
            pressure_level = "medium"

        return {
            "active_tasks": active_count,
            "max_queue_pressure": self.thresholds["max_queue_pressure"],
            "pressure_level": pressure_level,
            "description": f"活跃任务数 {active_count}/{self.thresholds['max_queue_pressure']}",
        }

    def register_task(self, task_id: str, workspace_dir: Optional[Path] = None) -> bool:
        """
        注册新任务

        Args:
            task_id: 任务ID
            workspace_dir: 任务工作目录（可选）

        Returns:
            是否注册成功
        """
        with self.lock:
            if task_id in self.active_tasks:
                return False

            self.active_tasks.add(task_id)
            if workspace_dir:
                self.task_workspaces[task_id] = workspace_dir

            return True

    def unregister_task(self, task_id: str) -> bool:
        """
        注销任务

        Args:
            task_id: 任务ID

        Returns:
            是否注销成功
        """
        with self.lock:
            if task_id not in self.active_tasks:
                return False

            self.active_tasks.remove(task_id)
            self.task_workspaces.pop(task_id, None)
            return True

    def get_isolation_constraints(self, task_id: str) -> List[IsolationRule]:
        """
        获取任务隔离约束

        Args:
            task_id: 任务ID

        Returns:
            隔离规则列表
        """
        # 返回所有规则，可根据任务特定需求过滤
        return self.isolation_rules

    def validate_isolation(self, task_id: str, proposed_paths: List[str]) -> Tuple[bool, List[str]]:
        """
        验证隔离约束

        Args:
            task_id: 任务ID
            proposed_paths: 计划访问的路径列表

        Returns:
            (是否通过, 违规列表)
        """
        violations = []

        with self.lock:
            # 检查工作目录隔离
            task_workspace = self.task_workspaces.get(task_id)
            if task_workspace:
                for path_str in proposed_paths:
                    path = Path(path_str)
                    # 确保路径在任务工作目录内，或至少不在其他任务的工作目录内
                    for other_id, other_workspace in self.task_workspaces.items():
                        if other_id == task_id:
                            continue
                        try:
                            if path.is_relative_to(other_workspace):
                                violations.append(
                                    f"路径 {path} 位于其他任务 {other_id} 的工作目录内"
                                )
                        except ValueError:
                            pass

            # 检查文件写入边界
            file_boundary_rule = next(
                (
                    rule
                    for rule in self.isolation_rules
                    if rule.constraint == IsolationConstraint.FILE_WRITE_BOUNDARY
                ),
                None,
            )
            if file_boundary_rule:
                allowed_prefixes = file_boundary_rule.parameters.get("allowed_prefixes", [])
                restricted_prefixes = file_boundary_rule.parameters.get("restricted_prefixes", [])
                readonly_prefixes = file_boundary_rule.parameters.get("readonly_prefixes", [])

                for path_str in proposed_paths:
                    path = Path(path_str).resolve()
                    path_str_abs = str(path)

                    # 豁免：路径在任务自己的工作空间内
                    if task_workspace and path.is_relative_to(task_workspace):
                        continue

                    # 检查是否在允许的前缀内
                    if allowed_prefixes:
                        allowed = any(
                            path_str_abs.startswith(prefix) for prefix in allowed_prefixes
                        )
                        if not allowed:
                            violations.append(f"路径 {path_str_abs} 不在允许的写入目录范围内")

                    # 检查是否在受限前缀内
                    for restricted in restricted_prefixes:
                        if path_str_abs.startswith(restricted):
                            violations.append(f"路径 {path_str_abs} 位于受限制的目录 {restricted}")

                    # 检查是否在只读前缀内
                    for readonly in readonly_prefixes:
                        if path_str_abs.startswith(readonly):
                            violations.append(f"路径 {path_str_abs} 位于只读目录 {readonly}")

        return len(violations) == 0, violations

    def generate_scheduling_summary(self) -> SchedulingSummary:
        """
        生成调度摘要

        Returns:
            调度摘要
        """
        # 获取准入决策
        admission_result = self.check_admission()

        # 获取资源快照
        resource_snapshot = {
            "free_memory_percent": system_free_memory_percent(),
            "load_average": system_load_average(),
            "ollama_cpu_percent": ollama_active_cpu_percent(),
            "active_tasks": list(self.active_tasks),
            "timestamp": time.time(),
        }

        # 构建摘要
        summary = SchedulingSummary(
            current_workers=admission_result.allowed_workers,
            max_workers=2,  # 当前系统最大支持2个worker
            admission_result=admission_result,
            active_task_ids=list(self.active_tasks),
            resource_snapshot=resource_snapshot,
        )

        return summary

    def get_parallel_safety_status(self) -> Dict[str, Any]:
        """
        获取并行安全状态

        Returns:
            结构化状态信息
        """
        admission_result = self.check_admission()
        summary = self.generate_scheduling_summary()

        return {
            "admission": {
                "decision": admission_result.decision.value,
                "allowed_workers": admission_result.allowed_workers,
                "reason": admission_result.reason,
                "suggested_action": admission_result.suggested_action,
            },
            "isolation": {
                "active_tasks_count": len(self.active_tasks),
                "registered_tasks": list(self.active_tasks),
                "rules_count": len(self.isolation_rules),
            },
            "resources": summary.resource_snapshot,
            "summary": {
                "current_workers": summary.current_workers,
                "max_workers": summary.max_workers,
                "generated_at": summary.generated_at,
            },
            "thresholds": self.thresholds,
        }


# 全局门控实例
_global_gate: Optional[ParallelBuildGate] = None


def get_global_gate() -> ParallelBuildGate:
    """获取全局并行构建门控实例"""
    global _global_gate
    if _global_gate is None:
        _global_gate = ParallelBuildGate()
    return _global_gate


def check_parallel_admission(requested_workers: int = 2) -> Dict[str, Any]:
    """
    检查并行准入（便捷函数）

    Args:
        requested_workers: 请求的worker数量

    Returns:
        结构化准入结果
    """
    gate = get_global_gate()
    result = gate.check_admission(requested_workers)

    return {
        "decision": result.decision.value,
        "allowed_workers": result.allowed_workers,
        "reason": result.reason,
        "suggested_action": result.suggested_action,
        "resource_checks": [
            {
                "dimension": check.dimension.value,
                "value": check.value,
                "threshold": check.threshold,
                "passed": check.passed,
                "reason": check.reason,
            }
            for check in result.resource_checks
        ],
        "metadata": result.metadata,
    }


def get_scheduling_summary() -> Dict[str, Any]:
    """
    获取调度摘要（便捷函数）

    Returns:
        结构化调度摘要
    """
    gate = get_global_gate()
    summary = gate.generate_scheduling_summary()

    return {
        "current_workers": summary.current_workers,
        "max_workers": summary.max_workers,
        "admission_result": {
            "decision": summary.admission_result.decision.value,
            "allowed_workers": summary.admission_result.allowed_workers,
            "reason": summary.admission_result.reason,
        },
        "active_task_ids": summary.active_task_ids,
        "resource_snapshot": summary.resource_snapshot,
        "generated_at": summary.generated_at,
    }


if __name__ == "__main__":
    # 简单命令行测试
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        summary = get_scheduling_summary()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        admission = check_parallel_admission()
        print(json.dumps(admission, ensure_ascii=False, indent=2))
