#!/usr/bin/env python3
"""
Sub-Agent Bus - 最小并发委派与结果合成总线

支持有限角色、有限并发和结果合成，让串行脚本开始向可控并行演进。

核心概念：
1. 最小代理角色：researcher, builder, reviewer, operator
2. 最小委派协议：输入、输出、状态、错误回传
3. 并发上限：budget/worker count/merge 策略
4. 结果合成链路：至少一条合成流水线

设计原则：
- 最小可运行闭环优先
- 基于当前工作区真实结构
- 可控并发，不允许无界并发
- 明确的责任边界
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import sys
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .subagent_registry import get_registry

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 导入 subagent registry
try:
    from .subagent_registry import get_registry as get_subagent_registry
except ImportError as e:
    logger.warning(f"无法导入 subagent_registry: {e}")
    get_subagent_registry = None


class AgentRole(Enum):
    """最小代理角色"""

    PLANNER = "planner"  # 规划制定
    RESEARCHER = "researcher"  # 研究分析
    BUILDER = "builder"  # 构建实现（兼容）
    BUILD_WORKER = "build_worker"  # 构建执行
    REVIEWER = "reviewer"  # 审查评估
    VALIDATOR = "validator"  # 验证验收
    OPERATOR = "operator"  # 运维执行


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"  # 待处理
    DISPATCHED = "dispatched"  # 已委派
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 取消


class ConcurrencyBudget(Enum):
    """并发预算级别"""

    LOW = "low"  # 低并发 (1 worker)
    MEDIUM = "medium"  # 中并发 (2-3 workers)
    HIGH = "high"  # 高并发 (4-5 workers, 硬上限)


@dataclass
class TaskInput:
    """任务输入协议"""

    task_id: str
    role: AgentRole
    payload: Dict[str, Any]  # 任务负载
    context: Dict[str, Any] = field(default_factory=dict)  # 执行上下文
    dependencies: List[str] = field(default_factory=list)  # 依赖任务ID
    timeout_seconds: int = 300  # 超时时间（秒）
    priority: int = 0  # 优先级（数值越大优先级越高）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class TaskOutput:
    """任务输出协议"""

    task_id: str
    role: AgentRole
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None  # 执行结果
    error: Optional[str] = None  # 错误信息
    artifacts: List[str] = field(default_factory=list)  # 产出物路径
    execution_time_ms: float = 0.0  # 执行时间（毫秒）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 输出元数据


@dataclass
class DelegationRequest:
    """委派请求"""

    request_id: str
    tasks: List[TaskInput]  # 要委派的任务列表
    concurrency_budget: ConcurrencyBudget = ConcurrencyBudget.MEDIUM
    merge_strategy: str = "sequential"  # 合并策略: sequential, parallel, dependency_aware
    callback_url: Optional[str] = None  # 回调URL（可选）
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DelegationResponse:
    """委派响应"""

    request_id: str
    delegation_id: str
    accepted_tasks: List[str]  # 已接受的任务ID列表
    rejected_tasks: List[Tuple[str, str]] = field(default_factory=list)  # (task_id, reason)
    estimated_completion_time_seconds: float = 0.0
    concurrency_limit: int = 1
    worker_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DelegationStatus:
    """委派状态"""

    delegation_id: str
    request_id: str
    status: TaskStatus
    progress_percent: float = 0.0
    completed_tasks: int = 0
    total_tasks: int = 0
    task_statuses: Dict[str, TaskStatus] = field(default_factory=dict)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class MergeResult:
    """合并结果"""

    delegation_id: str
    request_id: str
    status: TaskStatus
    merged_output: Dict[str, Any]  # 合并后的输出
    individual_outputs: Dict[str, TaskOutput]  # 各任务原始输出
    merge_strategy: str
    merge_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


class SubAgentBus:
    """Sub-Agent Bus 核心"""

    def __init__(self, max_workers: int = 3):
        """
        初始化 Sub-Agent Bus

        Args:
            max_workers: 最大工作线程数（硬上限）
        """
        self.max_workers = max(max_workers, 1)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.active_tasks: Dict[str, Future] = {}
        self.task_registry: Dict[str, TaskInput] = {}
        self.output_registry: Dict[str, TaskOutput] = {}
        self.delegation_registry: Dict[str, DelegationStatus] = {}
        # 初始化 subagent registry
        self.subagent_registry = get_registry()
        self.merge_strategies = {
            "sequential": self._merge_sequential,
            "parallel": self._merge_parallel,
            "dependency_aware": self._merge_dependency_aware,
        }
        self.agent_handlers = {
            AgentRole.PLANNER: self._handle_planner_task,
            AgentRole.RESEARCHER: self._handle_researcher_task,
            AgentRole.BUILDER: self._handle_builder_task,
            AgentRole.BUILD_WORKER: self._handle_build_worker_task,
            AgentRole.REVIEWER: self._handle_reviewer_task,
            AgentRole.VALIDATOR: self._handle_validator_task,
            AgentRole.OPERATOR: self._handle_operator_task,
        }
        logger.info(f"SubAgentBus 初始化完成，最大 workers: {self.max_workers}")

    def check_tool_guardrail(self, role: AgentRole, tool_name: str) -> Dict[str, Any]:
        """
        检查工具在指定角色下是否允许使用

        Args:
            role: 代理角色
            tool_name: 工具名称

        Returns:
            dict with keys: allowed, decision, reason, policy_violations
        """
        if not self.subagent_registry:
            return {
                "allowed": True,
                "decision": "allow",
                "reason": "SubAgent Registry 未加载，默认允许",
                "policy_violations": [],
                "role_id": role.value,
                "tool_name": tool_name,
            }

        # 使用 registry 检查工具边界
        return self.subagent_registry.check_tool_guardrail(role.value, tool_name)

    def validate_output_schema(
        self, role: AgentRole, output_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        验证产出是否符合角色产出契约

        Args:
            role: 代理角色
            output_data: 产出数据

        Returns:
            (valid, errors)
        """
        if not self.subagent_registry:
            return True, []

        # 使用 registry 验证产出契约
        return self.subagent_registry.validate_output_schema(role.value, output_data)

    def delegate(self, request: DelegationRequest) -> DelegationResponse:
        """
        委派任务

        Args:
            request: 委派请求

        Returns:
            委派响应
        """
        logger.info(f"收到委派请求: {request.request_id}, 任务数: {len(request.tasks)}")

        # 1. 计算并发预算
        concurrency_limit = self._calculate_concurrency_limit(request.concurrency_budget)
        worker_count = min(concurrency_limit, len(request.tasks))

        # 2. 检查并接受任务
        accepted_tasks = []
        rejected_tasks = []

        for task_input in request.tasks:
            # 检查任务ID唯一性
            if task_input.task_id in self.task_registry:
                rejected_tasks.append((task_input.task_id, "任务ID已存在"))
                continue

            # 检查角色是否支持
            if task_input.role not in self.agent_handlers:
                rejected_tasks.append((task_input.task_id, f"不支持的代理角色: {task_input.role}"))
                continue

            accepted_tasks.append(task_input.task_id)
            self.task_registry[task_input.task_id] = task_input

        # 3. 生成委派ID
        delegation_id = f"delegation_{uuid.uuid4().hex[:8]}"

        # 4. 创建委派状态
        delegation_status = DelegationStatus(
            delegation_id=delegation_id,
            request_id=request.request_id,
            status=TaskStatus.PENDING,
            total_tasks=len(accepted_tasks),
            task_statuses={task_id: TaskStatus.PENDING for task_id in accepted_tasks},
            start_time=time.time(),
        )
        self.delegation_registry[delegation_id] = delegation_status

        # 5. 异步执行任务（非阻塞）
        if accepted_tasks:
            threading.Thread(
                target=self._execute_delegation,
                args=(
                    delegation_id,
                    accepted_tasks,
                    worker_count,
                    request.merge_strategy,
                ),
                daemon=True,
            ).start()

        # 6. 返回响应
        response = DelegationResponse(
            request_id=request.request_id,
            delegation_id=delegation_id,
            accepted_tasks=accepted_tasks,
            rejected_tasks=rejected_tasks,
            estimated_completion_time_seconds=self._estimate_completion_time(
                accepted_tasks, worker_count
            ),
            concurrency_limit=concurrency_limit,
            worker_count=worker_count,
            metadata={"merge_strategy": request.merge_strategy},
        )

        logger.info(
            f"委派已接受: {delegation_id}, 接受任务: {len(accepted_tasks)}, 拒绝任务: {len(rejected_tasks)}"
        )
        return response

    def get_status(self, delegation_id: str) -> Optional[DelegationStatus]:
        """获取委派状态"""
        return self.delegation_registry.get(delegation_id)

    def get_task_output(self, task_id: str) -> Optional[TaskOutput]:
        """获取任务输出"""
        return self.output_registry.get(task_id)

    def shutdown(self):
        """关闭总线"""
        self.executor.shutdown(wait=True)
        logger.info("SubAgentBus 已关闭")

    def _calculate_concurrency_limit(self, budget: ConcurrencyBudget) -> int:
        """计算并发限制"""
        budget_limits = {
            ConcurrencyBudget.LOW: 1,
            ConcurrencyBudget.MEDIUM: min(3, self.max_workers),
            ConcurrencyBudget.HIGH: min(5, self.max_workers),
        }
        return budget_limits.get(budget, 1)

    def _estimate_completion_time(self, task_ids: List[str], worker_count: int) -> float:
        """估算完成时间"""
        if not task_ids:
            return 0.0

        # 简单估算：每个任务平均30秒，考虑并发
        avg_task_time = 30.0  # 秒
        total_tasks = len(task_ids)

        if worker_count <= 0:
            return avg_task_time * total_tasks

        # 考虑并发效应的简单估算
        effective_workers = min(worker_count, total_tasks)
        estimated_time = (total_tasks / effective_workers) * avg_task_time

        # 增加10%的缓冲
        return estimated_time * 1.1

    def _execute_delegation(
        self,
        delegation_id: str,
        task_ids: List[str],
        worker_count: int,
        merge_strategy: str,
    ):
        """执行委派（内部方法）"""
        delegation = self.delegation_registry.get(delegation_id)
        if not delegation:
            logger.error(f"委派不存在: {delegation_id}")
            return

        # 更新状态为已委派
        delegation.status = TaskStatus.DISPATCHED
        logger.info(
            f"开始执行委派: {delegation_id}, 任务数: {len(task_ids)}, workers: {worker_count}"
        )

        try:
            # 1. 准备任务执行
            futures = {}

            # 2. 提交任务到线程池（限制并发）
            for i, task_id in enumerate(task_ids):
                task_input = self.task_registry.get(task_id)
                if not task_input:
                    logger.warning(f"任务不存在: {task_id}")
                    delegation.task_statuses[task_id] = TaskStatus.FAILED
                    continue

                # 检查依赖是否完成（最小实现：暂时忽略依赖）
                # TODO: 实现依赖等待机制
                if task_input.dependencies:
                    logger.info(
                        f"任务 {task_id} 有依赖: {task_input.dependencies}，在最小实现中忽略"
                    )

                # 提交任务执行
                future = self.executor.submit(self._execute_single_task, task_input, delegation_id)
                futures[task_id] = future

                # 更新任务状态
                delegation.task_statuses[task_id] = TaskStatus.RUNNING

                # 简单并发控制：等待一些任务完成后再提交更多
                if len(futures) >= worker_count:
                    # 等待任意一个任务完成
                    self._wait_for_any_completion(futures, delegation)

            # 3. 等待所有任务完成
            self._wait_for_all_completion(futures, delegation)

            # 4. 合并结果
            merge_result = self._merge_results(delegation_id, task_ids, merge_strategy)

            # 5. 更新最终状态
            delegation.status = merge_result.status
            delegation.end_time = time.time()
            delegation.progress_percent = 100.0

            logger.info(f"委派完成: {delegation_id}, 合并结果状态: {merge_result.status}")

        except Exception as e:
            logger.error(f"委派执行失败: {delegation_id}, 错误: {e}", exc_info=True)
            delegation.status = TaskStatus.FAILED
            delegation.errors.append(str(e))
            delegation.end_time = time.time()

    def _execute_single_task(self, task_input: TaskInput, delegation_id: str) -> TaskOutput:
        """执行单个任务"""
        task_id = task_input.task_id
        start_time = time.time()

        logger.info(f"开始执行任务: {task_id}, 角色: {task_input.role.value}")

        try:
            # 获取对应的处理器
            handler = self.agent_handlers.get(task_input.role)
            if not handler:
                raise ValueError(f"未找到角色处理器: {task_input.role}")

            # 1. 工具边界检查（如果任务负载包含工具调用）
            tool_calls = task_input.payload.get("tool_calls", [])
            if tool_calls:
                for tool_call in tool_calls:
                    tool_name = tool_call.get("tool")
                    if tool_name:
                        guardrail_result = self.check_tool_guardrail(task_input.role, tool_name)
                        if not guardrail_result.get("allowed", False):
                            raise ValueError(
                                f"工具使用被拒绝: {tool_name}, 原因: {guardrail_result.get('reason', '未知')}"
                            )

            # 2. 执行任务
            result = handler(task_input)

            # 3. 输出模式验证
            valid, errors = self.validate_output_schema(task_input.role, result)
            if not valid:
                logger.warning(f"任务 {task_id} 产出不符合契约: {errors}")
                # 仍然返回结果，但标记验证失败（在元数据中记录）
                validation_failed = True
            else:
                validation_failed = False

            # 构建输出
            output = TaskOutput(
                task_id=task_id,
                role=task_input.role,
                status=TaskStatus.COMPLETED,
                result=result,
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={
                    "delegation_id": delegation_id,
                    "executed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "validation_passed": not validation_failed,
                    "validation_errors": errors if validation_failed else [],
                },
            )

            logger.info(f"任务完成: {task_id}, 执行时间: {output.execution_time_ms:.2f}ms")
            return output

        except Exception as e:
            logger.error(f"任务执行失败: {task_id}, 错误: {e}", exc_info=True)

            output = TaskOutput(
                task_id=task_id,
                role=task_input.role,
                status=TaskStatus.FAILED,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={
                    "delegation_id": delegation_id,
                    "executed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "error_type": type(e).__name__,
                },
            )
            return output

    def _handle_planner_task(self, task_input: TaskInput) -> Dict[str, Any]:
        """处理规划者任务"""
        # 最小实现：模拟规划制定
        payload = task_input.payload
        topic = payload.get("topic", "未知主题")

        # 模拟规划工作
        time.sleep(1)  # 模拟处理时间

        return {
            "plan": f"关于 {topic} 的详细实施计划",
            "tasks": [
                "任务1: 需求分析与澄清",
                "任务2: 技术方案设计",
                "任务3: 资源规划与分配",
                "任务4: 风险评估与应对",
            ],
            "dependencies": ["任务1", "任务2"],
            "acceptance_criteria": [
                "方案设计通过评审",
                "资源分配合理可行",
                "风险评估完整且应对措施有效",
            ],
            "estimated_time": 8.5,
            "risks": ["技术风险: 新技术引入", "资源风险: 人力资源不足"],
        }

    def _handle_researcher_task(self, task_input: TaskInput) -> Dict[str, Any]:
        """处理研究员任务"""
        # 最小实现：模拟研究分析
        payload = task_input.payload
        topic = payload.get("topic", "未知主题")

        # 模拟研究工作
        time.sleep(1)  # 模拟处理时间

        return {
            "research_topic": topic,
            "findings": [
                f"关于 {topic} 的初步分析完成",
                "已识别关键模式 3 个",
                "建议下一步行动: 详细设计",
            ],
            "sources": ["内部知识库", "公开文档"],
            "confidence_score": 0.85,
            "recommendations": ["进行详细设计", "收集更多数据"],
        }

    def _handle_builder_task(self, task_input: TaskInput) -> Dict[str, Any]:
        """处理构建者任务"""
        # 最小实现：模拟构建工作
        payload = task_input.payload
        component = payload.get("component", "未知组件")

        # 模拟构建工作
        time.sleep(2)  # 模拟处理时间

        return {
            "component": component,
            "build_status": "success",
            "artifacts": [
                f"{component}_v1.0.py",
                f"{component}_test.py",
                f"{component}_docs.md",
            ],
            "tests_passed": True,
            "code_coverage": 0.78,
            "warnings": ["lint 警告: 第 42 行过长"],
        }

    def _handle_build_worker_task(self, task_input: TaskInput) -> Dict[str, Any]:
        """处理构建工作者任务"""
        # 最小实现：模拟构建工作
        payload = task_input.payload
        component = payload.get("component", "未知组件")

        # 模拟构建工作
        time.sleep(2)  # 模拟处理时间

        return {
            "component": component,
            "build_status": "success",
            "artifacts": [
                f"{component}_v1.0.py",
                f"{component}_test.py",
                f"{component}_docs.md",
            ],
            "tests_passed": True,
            "code_coverage": 0.78,
            "warnings": ["lint 警告: 第 42 行过长"],
        }

    def _handle_reviewer_task(self, task_input: TaskInput) -> Dict[str, Any]:
        """处理审查者任务"""
        # 最小实现：模拟审查工作
        payload = task_input.payload
        target = payload.get("target", "未知目标")

        # 模拟审查工作
        time.sleep(1.5)  # 模拟处理时间

        return {
            "review_target": target,
            "review_status": "completed",
            "findings": [
                "代码质量: 良好",
                "安全审查: 通过",
                "性能建议: 优化数据库查询",
            ],
            "issues_found": 2,
            "critical_issues": 0,
            "recommendations": ["优化缓存策略", "添加错误处理"],
            "approval": True,
        }

    def _handle_validator_task(self, task_input: TaskInput) -> Dict[str, Any]:
        """处理验证者任务"""
        # 最小实现：模拟验证工作
        payload = task_input.payload
        target = payload.get("target", "未知目标")

        # 模拟验证工作
        time.sleep(1.5)  # 模拟处理时间

        return {
            "validation_target": target,
            "validation_status": "passed",
            "metrics": {
                "execution_time_ms": 1500,
                "test_cases": 10,
                "passed_cases": 10,
                "coverage": 0.95,
            },
            "passed": True,
            "failures": [],
            "evidence": [f"{target}_validation_report.md"],
        }

    def _handle_operator_task(self, task_input: TaskInput) -> Dict[str, Any]:
        """处理运维者任务"""
        # 最小实现：模拟运维工作
        payload = task_input.payload
        operation = payload.get("operation", "未知操作")

        # 模拟运维工作
        time.sleep(0.5)  # 模拟处理时间

        return {
            "operation": operation,
            "status": "executed",
            "output": f"操作 {operation} 已成功执行",
            "metrics": {
                "execution_time_ms": 500,
                "resources_used": "低",
                "success_rate": 1.0,
            },
            "logs": [f"开始执行: {operation}", f"执行完成: {operation}", "状态: 成功"],
        }

    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """检查依赖是否满足"""
        if not dependencies:
            return True

        for dep_id in dependencies:
            output = self.output_registry.get(dep_id)
            if not output or output.status != TaskStatus.COMPLETED:
                return False

        return True

    def _wait_for_any_completion(self, futures: Dict[str, Future], delegation: DelegationStatus):
        """等待任意任务完成"""
        if not futures:
            return

        # 使用 concurrent.futures.wait 等待任意任务完成
        done, not_done = concurrent.futures.wait(
            futures.values(),
            timeout=1.0,  # 超时1秒检查
            return_when=concurrent.futures.FIRST_COMPLETED,
        )

        # 处理已完成的任务
        for future in done:
            try:
                task_output = future.result()
                self._process_task_completion(task_output, delegation)
            except Exception as e:
                logger.error(f"任务结果处理失败: {e}")

    def _wait_for_all_completion(self, futures: Dict[str, Future], delegation: DelegationStatus):
        """等待所有任务完成"""
        for task_id, future in futures.items():
            try:
                task_output = future.result(timeout=300)  # 5分钟超时
                self._process_task_completion(task_output, delegation)
            except Exception as e:
                logger.error(f"任务执行失败: {task_id}, 错误: {e}")

                # 创建失败输出
                task_input = self.task_registry.get(task_id)
                role = task_input.role if task_input else AgentRole.BUILDER

                failed_output = TaskOutput(
                    task_id=task_id,
                    role=role,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    execution_time_ms=0.0,
                    metadata={"error_type": type(e).__name__},
                )
                self._process_task_completion(failed_output, delegation)

    def _process_task_completion(self, task_output: TaskOutput, delegation: DelegationStatus):
        """处理任务完成"""
        task_id = task_output.task_id

        # 注册输出
        self.output_registry[task_id] = task_output

        # 获取之前的状态
        previous_status = delegation.task_statuses.get(task_id, TaskStatus.PENDING)
        current_status = task_output.status

        # 更新委派状态
        delegation.task_statuses[task_id] = current_status

        # 只有当任务从非最终状态变为最终状态时才增加计数
        final_states = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
        if previous_status not in final_states and current_status in final_states:
            delegation.completed_tasks += 1

        # 计算进度
        if delegation.total_tasks > 0:
            delegation.progress_percent = (
                delegation.completed_tasks / delegation.total_tasks
            ) * 100

        logger.info(
            f"任务完成处理: {task_id}, 状态: {current_status.value}, 进度: {delegation.progress_percent:.1f}%"
        )

        # 如果任务失败，记录错误
        if current_status == TaskStatus.FAILED and task_output.error:
            delegation.errors.append(f"{task_id}: {task_output.error}")

    def _merge_results(self, delegation_id: str, task_ids: List[str], strategy: str) -> MergeResult:
        """合并结果"""
        start_time = time.time()

        logger.info(f"开始合并结果: {delegation_id}, 策略: {strategy}")

        # 收集所有输出
        individual_outputs = {}
        completed_outputs = {}

        for task_id in task_ids:
            output = self.output_registry.get(task_id)
            if output:
                individual_outputs[task_id] = output
                if output.status == TaskStatus.COMPLETED:
                    completed_outputs[task_id] = output

        # 获取合并函数
        merge_func = self.merge_strategies.get(strategy, self._merge_sequential)

        # 执行合并
        merged_output = merge_func(completed_outputs)

        # 确定整体状态
        all_completed = all(
            output.status == TaskStatus.COMPLETED for output in individual_outputs.values()
        )
        any_failed = any(
            output.status == TaskStatus.FAILED for output in individual_outputs.values()
        )

        if all_completed:
            overall_status = TaskStatus.COMPLETED
        elif any_failed:
            overall_status = TaskStatus.FAILED
        else:
            overall_status = TaskStatus.RUNNING

        # 构建合并结果
        merge_result = MergeResult(
            delegation_id=delegation_id,
            request_id=self.delegation_registry[delegation_id].request_id,
            status=overall_status,
            merged_output=merged_output,
            individual_outputs=individual_outputs,
            merge_strategy=strategy,
            merge_time_ms=(time.time() - start_time) * 1000,
        )

        logger.info(f"结果合并完成: {delegation_id}, 状态: {overall_status.value}")
        return merge_result

    def _merge_sequential(self, outputs: Dict[str, TaskOutput]) -> Dict[str, Any]:
        """顺序合并策略（默认）"""
        merged = {
            "strategy": "sequential",
            "total_tasks": len(outputs),
            "completed_tasks": len(outputs),
            "results_by_role": {},
            "summary": {},
            "timeline": [],
        }

        # 按角色分组
        for task_id, output in outputs.items():
            role = output.role.value
            if role not in merged["results_by_role"]:
                merged["results_by_role"][role] = []

            result_entry = {
                "task_id": task_id,
                "result": output.result,
                "execution_time_ms": output.execution_time_ms,
                "status": output.status.value,
            }
            merged["results_by_role"][role].append(result_entry)

            # 添加到时间线
            merged["timeline"].append(
                {
                    "task_id": task_id,
                    "role": role,
                    "execution_time_ms": output.execution_time_ms,
                    "status": output.status.value,
                }
            )

        # 生成摘要
        merged["summary"] = {
            "roles_used": list(merged["results_by_role"].keys()),
            "total_execution_time_ms": sum(output.execution_time_ms for output in outputs.values()),
            "success_rate": len(outputs) / len(outputs) if outputs else 0.0,
        }

        return merged

    def _merge_parallel(self, outputs: Dict[str, TaskOutput]) -> Dict[str, Any]:
        """并行合并策略"""
        # 对于并行策略，我们更关注并发执行统计
        merged = self._merge_sequential(outputs)
        merged["strategy"] = "parallel"

        # 添加并发统计
        if outputs:
            execution_times = [output.execution_time_ms for output in outputs.values()]
            merged["concurrency_stats"] = {
                "max_concurrent_tasks": len(outputs),  # 在这个简单实现中
                "avg_execution_time_ms": sum(execution_times) / len(execution_times),
                "total_wall_time_ms": max(execution_times) if execution_times else 0,
            }

        return merged

    def _merge_dependency_aware(self, outputs: Dict[str, TaskOutput]) -> Dict[str, Any]:
        """依赖感知合并策略"""
        merged = self._merge_sequential(outputs)
        merged["strategy"] = "dependency_aware"

        # 在这个最小实现中，依赖信息来自任务输入
        # 实际实现中会使用更复杂的依赖解析
        dependency_chains = []

        for task_id, output in outputs.items():
            task_input = self.task_registry.get(task_id)
            if task_input and task_input.dependencies:
                dependency_chains.append(
                    {
                        "task_id": task_id,
                        "dependencies": task_input.dependencies,
                        "role": output.role.value,
                    }
                )

        merged["dependency_chains"] = dependency_chains
        merged["has_dependencies"] = bool(dependency_chains)

        return merged


# 全局总线实例
_bus_instance: Optional[SubAgentBus] = None


def get_bus(max_workers: int = 3) -> SubAgentBus:
    """获取全局 Sub-Agent Bus 实例"""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = SubAgentBus(max_workers=max_workers)
    return _bus_instance


if __name__ == "__main__":
    # 测试代码
    print("=== Sub-Agent Bus 测试 ===")

    # 创建总线实例
    bus = SubAgentBus(max_workers=2)

    # 创建测试任务
    tasks = [
        TaskInput(
            task_id="research_1",
            role=AgentRole.RESEARCHER,
            payload={"topic": "sub-agent 架构设计"},
            context={"priority": "high"},
            timeout_seconds=60,
        ),
        TaskInput(
            task_id="build_1",
            role=AgentRole.BUILDER,
            payload={"component": "sub_agent_bus"},
            dependencies=["research_1"],
            timeout_seconds=120,
        ),
        TaskInput(
            task_id="review_1",
            role=AgentRole.REVIEWER,
            payload={"target": "sub_agent_bus 实现"},
            dependencies=["build_1"],
            timeout_seconds=90,
        ),
        TaskInput(
            task_id="operate_1",
            role=AgentRole.OPERATOR,
            payload={"operation": "部署测试"},
            dependencies=["review_1"],
            timeout_seconds=30,
        ),
    ]

    # 创建委派请求
    request = DelegationRequest(
        request_id="test_request_001",
        tasks=tasks,
        concurrency_budget=ConcurrencyBudget.MEDIUM,
        merge_strategy="dependency_aware",
        metadata={"test": True, "description": "集成测试"},
    )

    # 执行委派
    print(f"\n1. 委派任务...")
    response = bus.delegate(request)
    print(f"   委派ID: {response.delegation_id}")
    print(f"   接受任务: {len(response.accepted_tasks)}")
    print(f"   拒绝任务: {len(response.rejected_tasks)}")
    print(f"   并发限制: {response.concurrency_limit}")
    print(f"   Worker数量: {response.worker_count}")

    # 轮询状态
    print(f"\n2. 轮询状态...")
    for i in range(10):
        status = bus.get_status(response.delegation_id)
        if status:
            print(
                f"   轮询 {i + 1}: 状态={status.status.value}, 进度={status.progress_percent:.1f}%, "
                f"完成={status.completed_tasks}/{status.total_tasks}"
            )

            if status.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break
        time.sleep(1)

    # 获取任务输出
    print(f"\n3. 获取任务输出...")
    for task_id in response.accepted_tasks:
        output = bus.get_task_output(task_id)
        if output:
            print(
                f"   任务 {task_id}: 状态={output.status.value}, "
                f"时间={output.execution_time_ms:.2f}ms"
            )
            if output.error:
                print(f"     错误: {output.error}")

    # 关闭总线
    bus.shutdown()

    print(f"\n✅ Sub-Agent Bus 测试完成")
