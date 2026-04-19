#!/usr/bin/env python3
"""
预算化技能执行入口 - Athena/Open Human 最小预算化技能执行闭环核心

集成预算检查、成本估算、技能执行和结果返回，提供四级生存模式映射。
提供结构化请求/响应，支持 success / pending_approval / insufficient_budget 等状态。

设计原则：
- 最小闭环：先实现核心预算检查与执行接线，再逐步扩展
- 协议优先：定义清晰的执行协议，支持审计与扩展
- 模式映射：将四级生存模式映射到实际行为差异
"""

import json
import logging
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 导入现有模块
try:
    from .budget_engine import (
        BudgetCheckRequest,
        BudgetCheckResult,
        BudgetDecision,
        BudgetEngine,
        BudgetMode,
        get_budget_engine,
    )
    from .payment_contract import PaymentApprovalEngine, get_payment_engine
    from .revenue_ledger import RevenueLedger, get_revenue_ledger
    from .skill_cost_estimator import (
        CostEstimate,
        SkillCostEstimator,
        SkillCostRequest,
        get_cost_estimator,
    )
    from .skill_registry import SkillDefinition, SkillRegistry, get_registry
except ImportError as e:
    logger.error(f"导入现有模块失败: {e}")
    # 尝试绝对导入
    sys.path.insert(0, os.path.dirname(__file__))
    from budget_engine import (
        BudgetCheckRequest,
        BudgetCheckResult,
        BudgetDecision,
        BudgetEngine,
        BudgetMode,
        get_budget_engine,
    )
    from payment_contract import PaymentApprovalEngine, get_payment_engine
    from revenue_ledger import RevenueLedger, get_revenue_ledger
    from skill_cost_estimator import (
        CostEstimate,
        SkillCostEstimator,
        SkillCostRequest,
        get_cost_estimator,
    )
    from skill_registry import SkillDefinition, SkillRegistry, get_registry

# ==================== 枚举定义 ====================


class SkillExecutionStatus(Enum):
    """技能执行状态枚举"""

    SUCCESS = "success"  # 执行成功
    BUDGET_APPROVED = "budget_approved"  # 预算批准，执行中
    PENDING_APPROVAL = "pending_approval"  # 待审批（需要人工审批）
    INSUFFICIENT_BUDGET = "insufficient_budget"  # 预算不足
    REJECTED_PAUSED = "rejected_paused"  # 暂停模式拒绝
    BUDGET_CHECK_FAILED = "budget_check_failed"  # 预算检查失败
    SKILL_EXECUTION_FAILED = "skill_execution_failed"  # 技能执行失败
    COST_ESTIMATION_FAILED = "cost_estimation_failed"  # 成本估算失败
    SYSTEM_ERROR = "system_error"  # 系统错误


class ApprovalRequirement(Enum):
    """审批要求枚举"""

    NONE = "none"  # 无需审批
    BUDGET_THRESHOLD = "budget_threshold"  # 预算阈值审批
    HUMAN_GATE = "human_gate"  # 人工闸门审批
    PAYMENT_APPROVAL = "payment_approval"  # 支付审批


# ==================== 数据类定义 ====================


@dataclass
class SkillExecutionRequest:
    """技能执行请求"""

    skill_id: str
    parameters: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None  # 包含 task_id, user_id, priority 等
    metadata: Optional[Dict[str, Any]] = None

    # 预算相关字段
    budget_check_required: bool = True
    cost_estimation_required: bool = True
    approval_required: bool = True  # 是否允许自动审批
    force_execution: bool = False  # 是否强制跳过预算检查

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class SkillExecutionResult:
    """技能执行结果"""

    status: SkillExecutionStatus
    skill_id: str
    task_id: Optional[str] = None

    # 预算相关字段
    budget_decision: Optional[str] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    remaining_budget: Optional[float] = None
    budget_mode: Optional[str] = None

    # 技能执行结果
    execution_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # 审批相关字段
    approval_required: bool = False
    approval_request_id: Optional[str] = None
    approval_gate_id: Optional[str] = None

    # 审计追踪
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = asdict(self)
        result["status"] = self.status.value
        if self.budget_decision:
            result["budget_decision"] = self.budget_decision
        if self.budget_mode:
            result["budget_mode"] = self.budget_mode
        return result

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def is_success(self) -> bool:
        """是否执行成功"""
        return self.status in [
            SkillExecutionStatus.SUCCESS,
            SkillExecutionStatus.BUDGET_APPROVED,
        ]

    def needs_approval(self) -> bool:
        """是否需要审批"""
        return self.status == SkillExecutionStatus.PENDING_APPROVAL

    def is_budget_rejected(self) -> bool:
        """是否因预算原因被拒绝"""
        return self.status in [
            SkillExecutionStatus.INSUFFICIENT_BUDGET,
            SkillExecutionStatus.REJECTED_PAUSED,
            SkillExecutionStatus.BUDGET_CHECK_FAILED,
        ]


@dataclass
class BudgetExecutionContext:
    """预算执行上下文"""

    request: SkillExecutionRequest
    budget_engine: BudgetEngine
    cost_estimator: SkillCostEstimator
    skill_registry: SkillRegistry
    payment_engine: PaymentApprovalEngine

    # 中间结果
    cost_estimate: Optional[CostEstimate] = None
    budget_check_result: Optional[BudgetCheckResult] = None
    skill_metadata: Optional[Dict[str, Any]] = None


# ==================== 核心执行引擎 ====================


class BudgetedSkillExecutionEngine:
    """预算化技能执行引擎"""

    def __init__(
        self,
        budget_engine: Optional[BudgetEngine] = None,
        cost_estimator: Optional[SkillCostEstimator] = None,
        skill_registry: Optional[SkillRegistry] = None,
        payment_engine: Optional[PaymentApprovalEngine] = None,
        revenue_ledger: Optional[RevenueLedger] = None,
    ):
        """
        初始化预算化技能执行引擎

        Args:
            budget_engine: 预算引擎实例
            cost_estimator: 成本估算器实例
            skill_registry: 技能注册表实例
            payment_engine: 支付审批引擎实例
            revenue_ledger: 收益账本实例
        """
        self.budget_engine = budget_engine or get_budget_engine()
        self.cost_estimator = cost_estimator or get_cost_estimator()
        self.skill_registry = skill_registry or get_registry()
        self.payment_engine = payment_engine or get_payment_engine()
        self.revenue_ledger = revenue_ledger or get_revenue_ledger()

        logger.info("预算化技能执行引擎初始化完成")

    def execute_skill_with_budget(self, request: SkillExecutionRequest) -> SkillExecutionResult:
        """
        执行技能（带预算检查）

        Args:
            request: 技能执行请求

        Returns:
            技能执行结果
        """
        # 初始化结果对象
        result = SkillExecutionResult(
            status=SkillExecutionStatus.SYSTEM_ERROR,
            skill_id=request.skill_id,
            task_id=request.context.get("task_id") if request.context else None,
            timestamp=self._get_timestamp(),
        )

        try:
            # 1. 验证技能是否存在
            skill = self.skill_registry.get_skill(request.skill_id)
            if not skill:
                result.status = SkillExecutionStatus.SYSTEM_ERROR
                result.error_message = f"技能不存在: {request.skill_id}"
                return result

            # 收集技能元数据
            skill_metadata = {
                "category": skill.category,
                "executable": skill.executable,
                "status": skill.status,
            }

            # 2. 成本估算
            cost_estimate = None
            if request.cost_estimation_required:
                cost_estimate = self._estimate_cost(request, skill_metadata)
                if not cost_estimate:
                    result.status = SkillExecutionStatus.COST_ESTIMATION_FAILED
                    result.error_message = "成本估算失败"
                    return result

                result.estimated_cost = cost_estimate.total

            # 3. 预算检查（如果不需要预算检查则跳过）
            if request.budget_check_required and not request.force_execution:
                budget_result = self._check_budget(request, cost_estimate, skill_metadata)
                if not budget_result:
                    result.status = SkillExecutionStatus.BUDGET_CHECK_FAILED
                    result.error_message = "预算检查失败"
                    return result

                result.budget_decision = budget_result.decision.value
                result.budget_mode = self.budget_engine.get_state().current_mode.value
                result.remaining_budget = self.budget_engine.get_state().remaining

                # 处理预算决策
                if not budget_result.allowed:
                    if budget_result.decision == BudgetDecision.REQUIRES_APPROVAL:
                        result.status = SkillExecutionStatus.PENDING_APPROVAL
                        result.approval_required = True
                        # 创建审批请求
                        approval_info = self._create_approval_request(
                            request, cost_estimate, budget_result
                        )
                        if approval_info:
                            result.approval_request_id = approval_info.get("request_id")
                            result.approval_gate_id = approval_info.get("gate_id")
                        return result
                    elif budget_result.decision == BudgetDecision.REJECTED_PAUSED:
                        result.status = SkillExecutionStatus.REJECTED_PAUSED
                        return result
                    else:  # REJECTED_INSUFFICIENT
                        result.status = SkillExecutionStatus.INSUFFICIENT_BUDGET
                        return result

                # 预算批准，继续执行
                result.status = SkillExecutionStatus.BUDGET_APPROVED

            # 4. 执行技能
            execution_result = self.skill_registry.execute_skill(
                skill_id=request.skill_id,
                args=request.parameters,
                context=request.context,
            )

            result.execution_result = execution_result

            # 5. 记录实际消费（如果执行成功且有成本估算）
            if execution_result.get("success") and cost_estimate:
                self._record_consumption(
                    request=request,
                    cost_estimate=cost_estimate,
                    execution_result=execution_result,
                    skill=skill,
                )
                # 更新实际成本（简化为估算成本）
                result.actual_cost = cost_estimate.total

            # 6. 设置最终状态
            if execution_result.get("success"):
                result.status = SkillExecutionStatus.SUCCESS
            else:
                result.status = SkillExecutionStatus.SKILL_EXECUTION_FAILED
                result.error_message = execution_result.get("error", "执行失败")
                result.error_details = execution_result

        except Exception as e:
            logger.error(f"技能执行过程中发生错误: {e}", exc_info=True)
            result.status = SkillExecutionStatus.SYSTEM_ERROR
            result.error_message = str(e)
            result.error_details = {"exception_type": type(e).__name__}

        return result

    def _estimate_cost(
        self, request: SkillExecutionRequest, skill_metadata: Dict[str, Any]
    ) -> Optional[CostEstimate]:
        """估算技能执行成本"""
        try:
            cost_request = SkillCostRequest(
                skill_id=request.skill_id,
                skill_metadata=skill_metadata,
                parameters=request.parameters,
                context=request.context,
            )
            return self.cost_estimator.estimate_cost(cost_request)
        except Exception as e:
            logger.error(f"成本估算失败: {e}")
            return None

    def _check_budget(
        self,
        request: SkillExecutionRequest,
        cost_estimate: Optional[CostEstimate],
        skill_metadata: Dict[str, Any],
    ) -> Optional[BudgetCheckResult]:
        """检查预算"""
        try:
            # 如果没有成本估算，使用默认成本
            estimated_cost = cost_estimate.total if cost_estimate else 10.0

            # 确定任务类型和必要性
            task_type = skill_metadata.get("category", "general")
            is_essential = (
                request.context.get("priority") == "critical" if request.context else False
            )

            # 创建预算检查请求
            budget_request = BudgetCheckRequest(
                task_id=request.context.get(
                    "task_id", f"skill_{request.skill_id}_{uuid.uuid4().hex[:8]}"
                ),
                estimated_cost=estimated_cost,
                task_type=task_type,
                is_essential=is_essential,
                description=f"技能执行: {request.skill_id}",
                metadata={
                    "skill_id": request.skill_id,
                    "skill_metadata": skill_metadata,
                    "parameters": request.parameters,
                },
            )

            return self.budget_engine.check_budget(budget_request)
        except Exception as e:
            logger.error(f"预算检查失败: {e}")
            return None

    def _create_approval_request(
        self,
        request: SkillExecutionRequest,
        cost_estimate: Optional[CostEstimate],
        budget_result: BudgetCheckResult,
    ) -> Optional[Dict[str, Any]]:
        """创建审批请求"""
        try:
            # 创建支付审批请求
            amount = cost_estimate.total if cost_estimate else 0.0
            success, req_id, payment_request = self.payment_engine.create_payment_request(
                amount=amount,
                description=f"技能执行审批: {request.skill_id}",
                task_id=request.context.get("task_id") if request.context else None,
                payment_type="task_payment",
                payer="system",
                payee="skill_executor",
                metadata={
                    "skill_id": request.skill_id,
                    "budget_decision": budget_result.decision.value,
                    "estimated_cost": amount,
                },
                auto_approve=False,  # 需要人工审批
            )

            if success and payment_request:
                return {
                    "request_id": req_id,
                    "payment_request": payment_request.to_dict(),
                    "gate_id": None,  # 可扩展为Human Gate
                }
        except Exception as e:
            logger.error(f"创建审批请求失败: {e}")

        return None

    def _record_consumption(
        self,
        request: SkillExecutionRequest,
        cost_estimate: CostEstimate,
        execution_result: Dict[str, Any],
        skill: Optional[SkillDefinition] = None,
    ):
        """记录实际消费和收益"""
        try:
            task_id = request.context.get("task_id", f"skill_{request.skill_id}")
            actual_cost = cost_estimate.total  # 简化：使用估算成本作为实际成本

            self.budget_engine.record_consumption(
                task_id=task_id,
                cost=actual_cost,
                task_type="skill_execution",
                description=f"技能执行: {request.skill_id}",
                metadata={
                    "skill_id": request.skill_id,
                    "execution_success": execution_result.get("success", False),
                    "cost_estimate": cost_estimate.to_dict(),
                },
            )
            logger.info(f"记录技能消费: {request.skill_id}, 成本: {actual_cost:.2f}")

            # 记录收益（如果技能有定价且执行成功）
            if skill and execution_result.get("success"):
                self._record_revenue(
                    request=request,
                    skill=skill,
                    cost_estimate=cost_estimate,
                    execution_result=execution_result,
                )
        except Exception as e:
            logger.error(f"记录消费失败: {e}")

    def _record_revenue(
        self,
        request: SkillExecutionRequest,
        skill: SkillDefinition,
        cost_estimate: CostEstimate,
        execution_result: Dict[str, Any],
    ):
        """记录收益分账"""
        try:
            # 只记录有定价模型的技能收益
            if skill.pricing_model == "free" or skill.base_price <= 0:
                logger.debug(f"技能 {skill.id} 定价免费或无价格，跳过收益记录")
                return

            # 计算收益金额（简化为基础价格）
            revenue_amount = skill.base_price

            # 记录收益到账本
            success, entry_id, entry = self.revenue_ledger.record_revenue(
                skill_id=skill.id,
                developer_id=skill.developer_id,
                amount=revenue_amount,
                split_config=skill.revenue_split,
                task_id=request.context.get("task_id") if request.context else None,
                metadata={
                    "skill_id": skill.id,
                    "pricing_model": skill.pricing_model,
                    "base_price": skill.base_price,
                    "contract_status": skill.contract_status,
                    "cost_estimate": (
                        cost_estimate.to_dict()
                        if hasattr(cost_estimate, "to_dict")
                        else str(cost_estimate)
                    ),
                    "execution_success": execution_result.get("success", False),
                },
            )

            if success:
                logger.info(
                    f"记录收益成功: {entry_id}, 技能: {skill.id}, 金额: {revenue_amount:.2f}"
                )
            else:
                logger.warning(f"记录收益失败: {entry_id}")

        except Exception as e:
            logger.error(f"记录收益失败: {e}")

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime

        return datetime.now().isoformat()

    def get_budget_state(self) -> Dict[str, Any]:
        """获取当前预算状态"""
        try:
            return self.budget_engine.get_structured_state()
        except Exception as e:
            logger.error(f"获取预算状态失败: {e}")
            return {}

    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "engine": "BudgetedSkillExecutionEngine",
            "components": {
                "budget_engine": self.budget_engine.__class__.__name__,
                "cost_estimator": self.cost_estimator.__class__.__name__,
                "skill_registry": self.skill_registry.__class__.__name__,
                "payment_engine": self.payment_engine.__class__.__name__,
            },
            "status": "operational",
        }


# ==================== 四级生存模式映射 ====================


def map_budget_mode_to_behavior(budget_mode: BudgetMode) -> Dict[str, Any]:
    """
    将四级生存模式映射到 Athena/Codex/OpenCode 行为差异

    Args:
        budget_mode: 预算模式

    Returns:
        行为配置字典
    """
    behavior_map = {
        BudgetMode.NORMAL: {
            "description": "正常模式：预算充足，全功能运行",
            "agent_behavior": {
                "allow_non_essential_tasks": True,
                "max_tokens_per_request": 32000,
                "allow_external_calls": True,
                "require_approval_threshold": 100.0,
                "degradation_level": "none",
                "suggested_actions": ["全功能执行", "允许探索性任务"],
            },
            "athena_specific": {
                "enable_autoresearch": True,
                "enable_skill_evolution": True,
                "allow_speculative_execution": True,
            },
        },
        BudgetMode.LOW: {
            "description": "低预算模式：限制非必要任务，降级处理",
            "agent_behavior": {
                "allow_non_essential_tasks": False,
                "max_tokens_per_request": 16000,
                "allow_external_calls": True,
                "require_approval_threshold": 50.0,
                "degradation_level": "moderate",
                "suggested_actions": ["聚焦核心任务", "优化token使用", "限制外部调用"],
            },
            "athena_specific": {
                "enable_autoresearch": False,
                "enable_skill_evolution": False,
                "allow_speculative_execution": False,
            },
        },
        BudgetMode.CRITICAL: {
            "description": "临界模式：仅允许核心任务，需要人工审批",
            "agent_behavior": {
                "allow_non_essential_tasks": False,
                "max_tokens_per_request": 8000,
                "allow_external_calls": False,
                "require_approval_threshold": 10.0,
                "degradation_level": "high",
                "suggested_actions": [
                    "仅执行关键任务",
                    "使用最小上下文",
                    "等待人工审批",
                ],
            },
            "athena_specific": {
                "enable_autoresearch": False,
                "enable_skill_evolution": False,
                "allow_speculative_execution": False,
                "require_human_approval": True,
            },
        },
        BudgetMode.PAUSED: {
            "description": "暂停模式：停止所有新任务，仅处理维护任务",
            "agent_behavior": {
                "allow_non_essential_tasks": False,
                "max_tokens_per_request": 2000,
                "allow_external_calls": False,
                "require_approval_threshold": 0.0,
                "degradation_level": "extreme",
                "suggested_actions": ["停止新任务", "仅处理维护任务", "等待预算重置"],
            },
            "athena_specific": {
                "enable_autoresearch": False,
                "enable_skill_evolution": False,
                "allow_speculative_execution": False,
                "require_human_approval": True,
                "maintenance_only": True,
            },
        },
    }

    return behavior_map.get(budget_mode, behavior_map[BudgetMode.NORMAL])


def get_current_mode_behavior() -> Dict[str, Any]:
    """获取当前预算模式对应的行为配置"""
    try:
        budget_engine = get_budget_engine()
        current_mode = budget_engine.get_state().current_mode
        return map_budget_mode_to_behavior(current_mode)
    except Exception as e:
        logger.error(f"获取当前模式行为失败: {e}")
        return map_budget_mode_to_behavior(BudgetMode.NORMAL)


# ==================== 全局单例实例 ====================

_execution_engine_instance: Optional[BudgetedSkillExecutionEngine] = None


def get_execution_engine() -> BudgetedSkillExecutionEngine:
    """获取全局预算化技能执行引擎实例"""
    global _execution_engine_instance
    if _execution_engine_instance is None:
        _execution_engine_instance = BudgetedSkillExecutionEngine()
    return _execution_engine_instance


# ==================== 简化接口函数 ====================


def execute_skill(
    skill_id: str,
    parameters: Optional[Dict] = None,
    context: Optional[Dict] = None,
    **kwargs,
) -> SkillExecutionResult:
    """
    简化接口：执行技能（带预算检查）

    Args:
        skill_id: 技能ID
        parameters: 技能参数
        context: 执行上下文
        **kwargs: 其他参数（传递到 SkillExecutionRequest）

    Returns:
        技能执行结果
    """
    request = SkillExecutionRequest(
        skill_id=skill_id,
        parameters=parameters,
        context=context,
        metadata=kwargs.get("metadata"),
        budget_check_required=kwargs.get("budget_check_required", True),
        cost_estimation_required=kwargs.get("cost_estimation_required", True),
        approval_required=kwargs.get("approval_required", True),
        force_execution=kwargs.get("force_execution", False),
    )

    engine = get_execution_engine()
    return engine.execute_skill_with_budget(request)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=== Budgeted Skill Execution 测试 ===")

    engine = BudgetedSkillExecutionEngine()

    print("\n1. 获取当前预算状态:")
    budget_state = engine.get_budget_state()
    if budget_state:
        print(f"   模式: {budget_state.get('budget_state', {}).get('current_mode', 'unknown')}")
        print(f"   剩余预算: {budget_state.get('budget_state', {}).get('remaining', 0):.2f}")

    print("\n2. 获取当前模式行为映射:")
    behavior = get_current_mode_behavior()
    print(f"   描述: {behavior.get('description')}")
    print(f"   Agent行为: {behavior.get('agent_behavior', {}).get('degradation_level')}")

    print("\n3. 测试预算充足执行:")
    result1 = execute_skill(
        skill_id="openhuman-skill-matcher",
        parameters={
            "profile_skills": ["Python", "React"],
            "required_skills": ["Python", "AWS"],
        },
        context={"task_id": "test_task_1", "priority": "normal"},
        budget_check_required=True,
        force_execution=False,
    )
    print(f"   状态: {result1.status.value}")
    print(f"   预算决策: {result1.budget_decision}")
    print(f"   是否成功: {result1.is_success()}")

    print("\n4. 测试高成本技能（可能触发审批或拒绝）:")
    # 临时增加成本以触发阈值
    cost_estimator = get_cost_estimator()
    cost_estimator.update_base_cost("opencli-scanner", 200.0)

    result2 = execute_skill(
        skill_id="opencli-scanner",
        parameters={"url": "https://example.com", "scan_type": "structure"},
        context={"task_id": "test_task_2", "priority": "normal"},
    )
    print(f"   状态: {result2.status.value}")
    print(f"   是否需要审批: {result2.needs_approval()}")
    print(f"   是否预算拒绝: {result2.is_budget_rejected()}")

    # 恢复成本
    cost_estimator.update_base_cost("opencli-scanner", 8.0)

    print("\n5. 测试强制执行（跳过预算检查）:")
    result3 = execute_skill(
        skill_id="openhuman-skill-matcher",
        parameters={"profile_skills": ["Python"], "required_skills": ["Python"]},
        context={"task_id": "test_task_3"},
        budget_check_required=False,
    )
    print(f"   状态: {result3.status.value}")
    print(
        f"   执行结果: {result3.execution_result.get('success', False) if result3.execution_result else 'N/A'}"
    )

    print("\n=== 测试完成 ===")
