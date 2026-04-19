#!/usr/bin/env python3
"""
Athena Orchestrator - 任务编排核心

负责接受任务阶段（stage）并分派到对应的处理器。
支持通用工程阶段和 OpenHuman 领域阶段映射。
"""

import json
import logging
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入上下文预算模块
try:
    from .context_budget import (
        ConstraintSeverity,
        ConstraintType,
        check_context_health,
        get_budget_manager,
        handle_constraint_violation,
    )

    CONTEXT_BUDGET_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"无法导入上下文预算模块: {e}")
    CONTEXT_BUDGET_AVAILABLE = False

# 导入预算引擎模块（财务预算）
try:
    from .budget_engine import (
        BudgetCheckRequest,
        BudgetCheckResult,
        BudgetDecision,
        BudgetMode,
        get_budget_engine,
    )

    BUDGET_ENGINE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"无法导入预算引擎模块: {e}")
    BUDGET_ENGINE_AVAILABLE = False

# 导入预算化技能执行与模式映射
try:
    from .skill_execution_with_budget import (
        BudgetedSkillExecutionEngine,
        get_current_mode_behavior,
        map_budget_mode_to_behavior,
    )

    BUDGET_MODE_BEHAVIOR_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"无法导入预算模式行为映射模块: {e}")
    BUDGET_MODE_BEHAVIOR_AVAILABLE = False

# 任务目录定义
TASKS_DIR = Path(project_root) / ".openclaw" / "orchestrator" / "tasks"

# 导入智能工作流编排器（SmartOrchestrator） - 解决Lane混合与路由混淆问题
# 注意：为了避免循环导入，SmartOrchestrator的导入移到了_get_smart_executor方法内部
SMART_ORCHESTRATOR_AVAILABLE = False
smart_orchestrator = None

# 导入执行图集成模块（可选）
EXECUTION_INTEGRATION_AVAILABLE = False
get_integration = None
enable_integration = None

try:
    from .execution_integration import enable_integration as ei
    from .execution_integration import get_integration as gi

    get_integration = gi
    enable_integration = ei
    EXECUTION_INTEGRATION_AVAILABLE = True
    logging.getLogger(__name__).info("执行图集成模块可用")
except ImportError as e:
    logging.getLogger(__name__).warning(f"无法导入执行图集成模块: {e}")

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 导入 provider registry（延迟导入避免循环依赖）
def get_provider_registry():
    """延迟导入 provider registry"""
    try:
        from .provider_registry import get_registry

        return get_registry()
    except ImportError as e:
        logger.warning(f"无法导入 provider_registry: {e}")
        return None


def get_validation_engine():
    """延迟导入 validation engine"""
    try:
        from .openhuman_validation import get_validation_engine as get_engine

        return get_engine()
    except ImportError as e:
        logger.warning(f"无法导入 validation engine: {e}")
        return None


def get_chat_runtime():
    """延迟导入 chat runtime"""
    try:
        from .chat_runtime import get_runtime

        return get_runtime()
    except ImportError as e:
        logger.warning(f"无法导入 chat runtime: {e}")
        return None


class StageType(Enum):
    """阶段类型"""

    ENGINEERING = "engineering"
    OPENHUMAN = "openhuman"


class ApprovalState(Enum):
    """审批状态"""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class CostMode(Enum):
    """成本模式"""

    ACTUAL = "actual"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"
    FREE = "free"


# 合法的通用工程阶段
VALID_ENGINEERING_STAGES = {"think", "plan", "build", "review", "qa", "browse"}

# 阶段标签映射
ENGINEERING_STAGE_LABELS = {
    "think": "思考分析",
    "plan": "规划设计",
    "build": "构建实现",
    "review": "审查评估",
    "qa": "质量检查",
    "browse": "浏览探索",
}

# OpenHuman 领域阶段定义
OPENHUMAN_STAGES = {
    "distill": "提炼",
    "skill_design": "技能设计",
    "dispatch": "任务分发",
    "acceptance": "验收结算",
    "settlement": "结算分账",
    "audit": "审计追溯",
}

# OpenHuman 阶段到内部执行阶段的映射
# 采用降级映射策略：将 OpenHuman 阶段映射到最相近的通用工程阶段
OPENHUMAN_TO_ENGINEERING_MAP = {
    "distill": "think",  # 提炼 -> 思考分析
    "skill_design": "plan",  # 技能设计 -> 规划设计
    "dispatch": "plan",  # 任务分发 -> 规划设计
    "acceptance": "review",  # 验收结算 -> 审查评估
    "settlement": "plan",  # 结算分账 -> 规划设计（暂无业务引擎）
    "audit": "review",  # 审计追溯 -> 审查评估
}


@dataclass
class TaskMetadata:
    """任务元数据"""

    task_id: str
    stage: str  # 内部执行阶段（engineering stage）
    domain: str = "engineering"  # engineering, openhuman
    openhuman_stage: Optional[str] = None  # 原始 OpenHuman 阶段（如果 domain=openhuman）
    description: str = ""
    executor: str = "unknown"
    expected_output: str = ""
    status: str = "pending"
    created_at: str = ""
    updated_at: str = ""
    artifacts: List[str] = field(default_factory=list)

    # --- P0 新增字段 ---
    selected_provider: Optional[str] = None
    selected_model: Optional[str] = None
    estimated_tokens: int = 0
    estimated_cost: float = 0.0
    actual_tokens: int = 0
    actual_cost: float = 0.0
    cost_mode: str = CostMode.UNAVAILABLE.value
    approval_state: str = ApprovalState.NOT_REQUIRED.value
    approval_reason: str = ""
    approval_requested_at: Optional[str] = None
    approval_resolved_at: Optional[str] = None
    approval_resolved_by: Optional[str] = None
    dispatch_source: Optional[str] = None  # wecom, telegram, api, cli
    dispatch_thread_id: Optional[str] = None  # 消息线程ID、频道ID等
    # --- P0 新增字段结束 ---

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


def create_task_workspace(task_dir: Path) -> Dict[str, Path]:
    """
    为任务创建结构化工作目录并返回路径映射。

    Returns:
        dict with keys: workspace, inputs, outputs, evidence, checkpoints, trace
    """
    subdirs = {
        "workspace": task_dir / "workspace",
        "inputs": task_dir / "inputs",
        "outputs": task_dir / "outputs",
        "evidence": task_dir / "evidence",
        "checkpoints": task_dir / "checkpoints",
    }
    for subpath in subdirs.values():
        subpath.mkdir(parents=True, exist_ok=True)

    trace_path = task_dir / "trace.json"
    if not trace_path.exists():
        import time
        from datetime import datetime

        write_json(
            trace_path,
            {
                "task_id": task_dir.name,
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "version": "1.0",
                "events": [],
                "artifacts": [],
                "status_changes": [],
                "directories": {
                    key: str(path.relative_to(task_dir)) for key, path in subdirs.items()
                },
            },
        )

    return {**subdirs, "trace": trace_path}


def write_json(path: Path, payload: Any) -> None:
    """写入 JSON 文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    """读取 JSON 文件"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def update_trace_event(task_dir: Path, event_type: str, data: Dict[str, Any]) -> None:
    """在 trace.json 中追加一个事件记录"""
    trace_path = task_dir / "trace.json"
    if not trace_path.exists():
        return
    try:
        trace = read_json(trace_path, default={"events": []})
        if not isinstance(trace, dict):
            trace = {"events": []}
        events = trace.setdefault("events", [])
        from datetime import datetime

        events.append(
            {
                "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
                "type": event_type,
                "data": data,
            }
        )
        write_json(trace_path, trace)
    except Exception:
        pass


def update_trace_status_change(
    task_dir: Path, old_status: str, new_status: str, reason: str = ""
) -> None:
    """记录状态变化到 trace.json"""
    update_trace_event(
        task_dir,
        "status_change",
        {"old_status": old_status, "new_status": new_status, "reason": reason},
    )
    # 同时更新 trace 中的 status_changes 列表
    trace_path = task_dir / "trace.json"
    if not trace_path.exists():
        return
    try:
        trace = read_json(trace_path, default={"status_changes": []})
        if not isinstance(trace, dict):
            trace = {"status_changes": []}
        changes = trace.setdefault("status_changes", [])
        from datetime import datetime

        changes.append(
            {
                "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
            }
        )
        write_json(trace_path, trace)
    except Exception:
        pass


def add_trace_artifact(
    task_dir: Path,
    artifact_type: str,
    path: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """向 trace.json 添加产物记录"""
    update_trace_event(
        task_dir,
        "artifact_added",
        {"artifact_type": artifact_type, "path": path, "metadata": metadata or {}},
    )
    trace_path = task_dir / "trace.json"
    if not trace_path.exists():
        return
    try:
        trace = read_json(trace_path, default={"artifacts": []})
        if not isinstance(trace, dict):
            trace = {"artifacts": []}
        artifacts = trace.setdefault("artifacts", [])
        from datetime import datetime

        artifacts.append(
            {
                "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
                "artifact_type": artifact_type,
                "path": path,
                "metadata": metadata or {},
            }
        )
        write_json(trace_path, trace)
    except Exception:
        pass


class AthenaOrchestrator:
    """Athena 编排器"""

    def __init__(self):
        self.tasks: Dict[str, TaskMetadata] = {}
        self.task_counter = 0
        self.BUDGET_ENGINE_AVAILABLE = BUDGET_ENGINE_AVAILABLE

    def create_task(self, stage: str, **kwargs) -> Tuple[bool, str, Dict]:
        """
        创建任务

        Args:
            stage: 请求的阶段（可能是 engineering stage 或 openhuman stage）
            **kwargs: 额外参数，包括 domain, description, dispatch_source, dispatch_thread_id 等

        Returns:
            (success, task_id_or_error, metadata)
        """
        try:
            # 确定领域和内部阶段
            domain = kwargs.get("domain", "engineering")
            description = kwargs.get("description", "")
            dispatch_source = kwargs.get("dispatch_source")
            dispatch_thread_id = kwargs.get("dispatch_thread_id")

            # 如果是 OpenHuman 领域，进行阶段映射
            if domain == "openhuman":
                openhuman_stage = stage
                if openhuman_stage not in OPENHUMAN_STAGES:
                    return False, f"无效的 OpenHuman 阶段: {openhuman_stage}", {}

                # 映射到内部执行阶段
                if openhuman_stage not in OPENHUMAN_TO_ENGINEERING_MAP:
                    return False, f"未配置 OpenHuman 阶段映射: {openhuman_stage}", {}

                internal_stage = OPENHUMAN_TO_ENGINEERING_MAP[openhuman_stage]

                # 验证内部阶段合法性
                if internal_stage not in VALID_ENGINEERING_STAGES:
                    return False, f"内部映射阶段非法: {internal_stage}", {}

            else:
                # 工程领域，直接验证阶段
                if stage not in VALID_ENGINEERING_STAGES:
                    return (
                        False,
                        f"非法 stage: {stage} (仅支持: {sorted(VALID_ENGINEERING_STAGES)})",
                        {},
                    )

                internal_stage = stage
                openhuman_stage = None

            # 1. 选择 provider/model（通过 chat runtime 单一事实源）
            registry = get_provider_registry()
            chat_runtime = get_chat_runtime()
            selected_provider = None
            selected_model = None

            # 优先使用 chat runtime 进行选择
            if chat_runtime:
                try:
                    # 根据任务类型选择 provider/model
                    task_kind = "general"
                    if domain == "openhuman":
                        task_kind = "openhuman"
                    elif internal_stage in ["think", "plan"]:
                        task_kind = "coding_plan"

                    selected_provider, selected_model = chat_runtime.select_provider_for_task(
                        task_kind=task_kind, domain=domain
                    )
                    logger.info(
                        f"Chat runtime 选择 provider: {selected_provider}, model: {selected_model}"
                    )
                except Exception as e:
                    logger.warning(f"Chat runtime 选择失败: {e}，回退到 registry")
                    chat_runtime = None

            # 如果 chat runtime 不可用或失败，使用 registry
            if not chat_runtime and registry:
                try:
                    task_kind = "general"
                    if domain == "openhuman":
                        task_kind = "openhuman"
                    elif internal_stage in ["think", "plan"]:
                        task_kind = "coding_plan"

                    selected_provider, selected_model = registry.resolve_provider_for_task(
                        task_kind
                    )
                except Exception as e:
                    logger.warning(f"Registry 选择失败: {e}")

            # 最终 fallback
            if not selected_provider or not selected_model:
                selected_provider = "dashscope"
                selected_model = "qwen3.5-plus"
                logger.warning(f"使用最终 fallback: {selected_provider}/{selected_model}")

            # 2. 估算成本（初始估算为0，实际执行时更新）
            estimated_tokens = 0
            estimated_cost = 0.0
            cost_mode = CostMode.UNAVAILABLE.value
            if registry:
                try:
                    # 根据描述长度简单估算
                    estimated_input_tokens = len(description) // 4  # 粗略估算
                    estimated_output_tokens = 500  # 默认输出
                    cost_est = registry.estimate_cost(
                        selected_provider,
                        selected_model,
                        estimated_input_tokens,
                        estimated_output_tokens,
                    )
                    estimated_tokens = cost_est.get("estimated_tokens", 0)
                    estimated_cost = cost_est.get("estimated_cost", 0.0)
                    cost_mode = cost_est.get("cost_mode", CostMode.UNAVAILABLE.value)
                except Exception as e:
                    logger.warning(f"成本估算失败: {e}")

            # 2.5 检查预算（如果预算引擎可用）
            budget_check_passed = True
            budget_check_reason = "预算引擎不可用，跳过检查"
            budget_status = "NORMAL"  # 默认预算状态
            if BUDGET_ENGINE_AVAILABLE and estimated_cost > 0:
                try:
                    # 在函数内导入以避免循环依赖
                    from .budget_engine import BudgetCheckRequest, get_budget_engine

                    engine = get_budget_engine()

                    # 确定任务是否为核心任务
                    is_essential = False
                    if domain == "openhuman":
                        # OpenHuman 领域的关键任务可能是核心的
                        if openhuman_stage in ["acceptance", "audit", "settlement"]:
                            is_essential = True
                    elif internal_stage in ["qa", "review"]:
                        # 质量和审查任务可能是核心的
                        is_essential = True

                    # 使用临时任务ID进行预算检查
                    temp_task_id = f"precheck_temp_{self.task_counter + 1:06d}"

                    request = BudgetCheckRequest(
                        task_id=temp_task_id,
                        estimated_cost=estimated_cost,
                        task_type=internal_stage,
                        is_essential=is_essential,
                        description=description[:100] if description else "",
                        metadata={
                            "domain": domain,
                            "openhuman_stage": openhuman_stage,
                            "provider": selected_provider,
                            "model": selected_model,
                        },
                    )

                    result = engine.check_budget(request)
                    budget_check_passed = result.allowed
                    budget_check_reason = result.reason

                    # 确定预算状态（用于智能路由）
                    if result.decision.value == "approved":
                        budget_status = "NORMAL"
                    elif result.decision.value == "requires_approval":
                        budget_status = "WARNING"
                    elif result.decision.value in ["rejected", "insufficient"]:
                        budget_status = "CRITICAL"
                    else:
                        budget_status = "NORMAL"

                    if not budget_check_passed:
                        logger.warning(f"预算检查未通过: {result.decision.value} - {result.reason}")

                        # 如果是因为需要审批，可以继续创建任务但标记为需要审批
                        if result.decision.value == "requires_approval":
                            # 预算检查要求人工审批，与现有审批系统集成
                            logger.info(f"预算检查要求人工审批，任务将继续创建但需要审批")
                            # 这里可以设置特殊的审批标记，或者依赖现有的审批系统
                            # 我们暂时只记录日志，不阻止任务创建
                            budget_check_passed = True  # 允许创建，但后续需要审批
                        else:
                            # 预算不足或被拒绝，阻止任务创建
                            return False, f"预算检查失败: {result.reason}", {}

                except Exception as e:
                    logger.warning(f"预算检查失败: {e}")
                    # 预算检查失败时，允许任务继续创建（优雅降级）
                    budget_check_passed = True
                    budget_check_reason = f"预算检查异常: {e}"
                    # 预算检查失败时使用默认状态
                    budget_status = "NORMAL"

            # 3. 检查审批要求
            approval_state = ApprovalState.NOT_REQUIRED.value
            approval_reason = ""
            approval_requested_at = None
            if registry:
                try:
                    approval_check = registry.check_approval_required(description, internal_stage)
                    if approval_check.get("hitl_required", False):
                        approval_state = ApprovalState.PENDING.value
                        approval_reason = approval_check.get("reason", "需要人工审批")
                        approval_requested_at = self._current_timestamp()
                    else:
                        approval_state = ApprovalState.NOT_REQUIRED.value
                        approval_reason = approval_check.get("reason", "自动批准")
                except Exception as e:
                    logger.warning(f"审批检查失败: {e}")

            # 4. 生成任务ID
            self.task_counter += 1
            task_id = f"task_{self.task_counter:06d}"

            # 4.5 智能路由决策 - 解决Lane混合与路由混淆问题
            # 使用已确定的预算状态（在预算检查部分已设置budget_status变量）

            # 调用智能路由方法（集成SmartOrchestrator）
            smart_executor = self._get_smart_executor(
                stage=internal_stage,
                domain=domain,
                description=description,
                resources={},  # TODO: 从kwargs中提取资源需求
                budget_status=budget_status,
            )

            # 5. 创建任务元数据
            metadata = TaskMetadata(
                task_id=task_id,
                domain=domain,
                stage=internal_stage,
                openhuman_stage=openhuman_stage,
                description=description,
                executor=smart_executor,  # 使用智能路由决策的执行器
                expected_output=self._get_expected_output(internal_stage),
                status="created",
                created_at=self._current_timestamp(),
                updated_at=self._current_timestamp(),
                # --- P0 新增字段 ---
                selected_provider=selected_provider,
                selected_model=selected_model,
                estimated_tokens=estimated_tokens,
                estimated_cost=estimated_cost,
                cost_mode=cost_mode,
                approval_state=approval_state,
                approval_reason=approval_reason,
                approval_requested_at=approval_requested_at,
                dispatch_source=dispatch_source,
                dispatch_thread_id=dispatch_thread_id,
            )

            self.tasks[task_id] = metadata

            # 创建任务工作目录和 trace
            try:
                task_dir = TASKS_DIR / task_id
                workspace_paths = create_task_workspace(task_dir)
                update_trace_status_change(
                    task_dir, "pending", "created", "task directory initialized"
                )
                logger.info(f"任务工作目录已创建: {task_dir}")
                # 将目录路径添加到元数据中
                metadata.artifacts.append(str(task_dir))
            except Exception as e:
                logger.warning(f"创建任务工作目录失败: {e}，但任务已创建")

            logger.info(
                f"创建任务: {task_id}, 领域: {domain}, 原始阶段: {stage}, 内部阶段: {internal_stage}, "
                f"provider: {selected_provider}, model: {selected_model}, "
                f"approval: {approval_state}"
            )

            # 注册到执行图（如果集成可用）
            if EXECUTION_INTEGRATION_AVAILABLE and get_integration:
                try:
                    integration = get_integration()
                    success, message, graph_id = integration.register_task(
                        task_id=task_id,
                        stage=internal_stage,
                        domain=domain,
                        description=description,
                        openhuman_stage=openhuman_stage,
                        selected_provider=selected_provider,
                        selected_model=selected_model,
                        approval_state=approval_state,
                    )
                    if success:
                        logger.debug(f"任务注册到执行图: {task_id} -> {graph_id}")
                    else:
                        logger.debug(f"任务执行图注册失败: {message}")
                except Exception as e:
                    logger.warning(f"执行图注册异常: {e}")

            return True, task_id, metadata.to_dict()

        except Exception as e:
            logger.error(f"创建任务失败: {e}", exc_info=True)
            return False, str(e), {}

    def _get_executor_for_stage(self, stage: str) -> str:
        """根据阶段获取执行器"""
        executors = {
            "think": "athena_thinker",
            "plan": "athena_planner",
            "build": "athena_builder",
            "review": "athena_reviewer",
            "qa": "athena_qa",
            "browse": "opencli_browser",
        }
        return executors.get(stage, "unknown")

    def _get_smart_executor(
        self,
        stage: str,
        domain: str,
        description: str = "",
        resources: Dict[str, Any] = None,
        budget_status: str = "NORMAL",
    ) -> str:
        """
        智能路由方法 - 集成SmartOrchestrator的多维度决策

        ★ Insight ─────────────────────────────────────
        此方法解决15%执行器混淆率问题。通过SmartOrchestrator的route_task方法，
        基于多维度因素（系统负载、资源需求、预算状态）进行智能路由决策。
        当SmartOrchestrator不可用时，优雅降级到基础路由逻辑。

        注意：为了避免循环导入，SmartOrchestrator在方法内部延迟导入。
        ────────────────────────────────────────────────

        参数:
        - stage: 任务阶段 (think, plan, build, review, qa, browse)
        - domain: 任务领域 (engineering, openhuman)
        - description: 任务描述
        - resources: 资源需求字典
        - budget_status: 预算状态 (NORMAL, WARNING, CRITICAL)

        返回:
        - executor_name: 执行器名称字符串
        """
        # 延迟导入SmartOrchestrator（避免循环导入）
        try:
            from workflow.smart_orchestrator import SmartOrchestrator

            # 使用模块级变量缓存实例（避免重复创建）
            global SMART_ORCHESTRATOR_AVAILABLE, smart_orchestrator

            if smart_orchestrator is None:
                smart_orchestrator = SmartOrchestrator()
                SMART_ORCHESTRATOR_AVAILABLE = True
                logger.info("智能工作流编排器 (SmartOrchestrator) 已加载并初始化")

        except ImportError as e:
            logger.debug(f"无法导入SmartOrchestrator: {e}，使用基础路由")
            SMART_ORCHESTRATOR_AVAILABLE = False
            return self._get_executor_for_stage(stage)
        except Exception as e:
            logger.warning(f"SmartOrchestrator初始化失败: {e}，使用基础路由")
            SMART_ORCHESTRATOR_AVAILABLE = False
            return self._get_executor_for_stage(stage)

        try:
            # 构建任务元数据，匹配SmartOrchestrator.route_task接口
            task_metadata = {
                "entry_stage": stage,
                "domain": domain,
                "description": description,
                "resources": resources or {},
                "budget_status": budget_status,
                "type": "task",  # 默认类型
            }

            # 调用智能路由
            routing_decision = smart_orchestrator.route_task(task_metadata)

            # 从RoutingDecision中获取执行器名称
            executor_name = routing_decision.executor_type.value

            # 记录智能路由决策细节（用于调试和监控）
            logger.info(
                f"智能路由决策: {stage} -> {executor_name}, "
                f"置信度: {routing_decision.confidence:.2f}, "
                f"理由: {routing_decision.reasoning[:100]}..."
            )

            return executor_name

        except Exception as e:
            logger.warning(f"智能路由失败: {e}，回退到基础路由")
            # 优雅降级：使用基础路由逻辑
            return self._get_executor_for_stage(stage)

    def _get_expected_output(self, stage: str) -> str:
        """根据阶段获取预期产出"""
        outputs = {
            "think": "分析报告",
            "plan": "设计方案",
            "build": "实现代码",
            "review": "审查意见",
            "qa": "质量报告",
            "browse": "浏览结果",
        }
        return outputs.get(stage, "未知产出")

    def _current_timestamp(self) -> str:
        """获取当前时间戳"""
        import time

        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务信息"""
        if task_id in self.tasks:
            return self.tasks[task_id].to_dict()
        return None

    def list_tasks(self, domain: Optional[str] = None) -> List[Dict]:
        """列出任务"""
        tasks = []
        for task in self.tasks.values():
            if domain is None or task.domain == domain:
                tasks.append(task.to_dict())
        return tasks

    def update_task_status(self, task_id: str, status: str, reason: str = "") -> bool:
        """更新任务状态"""
        if task_id not in self.tasks:
            return False

        old_status = self.tasks[task_id].status
        self.tasks[task_id].status = status
        self.tasks[task_id].updated_at = self._current_timestamp()

        # 更新 trace
        try:
            task_dir = TASKS_DIR / task_id
            if task_dir.exists():
                update_trace_status_change(task_dir, old_status, status, reason)
        except Exception as e:
            logger.warning(f"更新 trace 状态失败: {e}")

        # 同步到执行图（如果集成可用）
        if EXECUTION_INTEGRATION_AVAILABLE and get_integration:
            try:
                integration = get_integration()
                integration.update_task_state(
                    task_id=task_id,
                    new_state=status,
                    reason=reason,
                    metadata={"old_status": old_status},
                )
            except Exception as e:
                logger.warning(f"执行图状态同步失败: {e}")

        return True

    def add_artifact(self, task_id: str, artifact_path: str, artifact_type: str = "output") -> bool:
        """添加产物"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task.artifacts.append(artifact_path)
        task.updated_at = self._current_timestamp()

        # 如果任务目录存在，将产物复制到相应子目录并更新 trace
        try:
            task_dir = TASKS_DIR / task_id
            if task_dir.exists():
                import shutil
                from pathlib import Path

                src_path = Path(artifact_path)
                if src_path.exists():
                    # 根据 artifact_type 决定目标子目录
                    if artifact_type == "evidence":
                        dest_dir = task_dir / "evidence"
                    elif artifact_type == "checkpoint":
                        dest_dir = task_dir / "checkpoints"
                    elif artifact_type == "input":
                        dest_dir = task_dir / "inputs"
                    else:  # output 或其他
                        dest_dir = task_dir / "outputs"
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_path = dest_dir / src_path.name
                    # 如果目标文件已存在，添加后缀
                    counter = 1
                    while dest_path.exists():
                        stem = src_path.stem
                        suffix = src_path.suffix
                        dest_path = dest_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                    shutil.copy2(src_path, dest_path)
                    # 更新 trace
                    add_trace_artifact(
                        task_dir, artifact_type, str(dest_path.relative_to(task_dir))
                    )
                    logger.info(f"产物已复制到任务目录: {dest_path}")
        except Exception as e:
            logger.warning(f"复制产物到任务目录失败: {e}")

        return True

    # --- P0 新增审批方法 ---
    def approve_task(self, task_id: str, approved_by: str = "system") -> Tuple[bool, str]:
        """批准任务"""
        if task_id not in self.tasks:
            return False, f"任务不存在: {task_id}"

        task = self.tasks[task_id]

        if task.approval_state != ApprovalState.PENDING.value:
            return False, f"任务当前状态为 {task.approval_state}，无需审批"

        task.approval_state = ApprovalState.APPROVED.value
        task.approval_resolved_at = self._current_timestamp()
        task.approval_resolved_by = approved_by
        task.updated_at = self._current_timestamp()

        logger.info(f"任务 {task_id} 已批准，批准人: {approved_by}")
        return True, "任务已批准"

    def reject_task(
        self, task_id: str, reason: str = "", rejected_by: str = "system"
    ) -> Tuple[bool, str]:
        """拒绝任务"""
        if task_id not in self.tasks:
            return False, f"任务不存在: {task_id}"

        task = self.tasks[task_id]

        if task.approval_state != ApprovalState.PENDING.value:
            return False, f"任务当前状态为 {task.approval_state}，无需审批"

        task.approval_state = ApprovalState.REJECTED.value
        task.approval_reason = reason if reason else "已拒绝"
        task.approval_resolved_at = self._current_timestamp()
        task.approval_resolved_by = rejected_by
        task.status = "rejected"
        task.updated_at = self._current_timestamp()

        logger.info(f"任务 {task_id} 已拒绝，拒绝人: {rejected_by}, 原因: {reason}")
        return True, "任务已拒绝"

    def interrupt_task(
        self, task_id: str, reason: str = "", interrupted_by: str = "system"
    ) -> Tuple[bool, str]:
        """中断任务（强制停止）"""
        if task_id not in self.tasks:
            return False, f"任务不存在: {task_id}"

        task = self.tasks[task_id]

        # 无论审批状态如何都可以中断
        task.approval_state = ApprovalState.CANCELLED.value
        task.approval_reason = reason if reason else "已中断"
        task.approval_resolved_at = self._current_timestamp()
        task.approval_resolved_by = interrupted_by
        task.status = "interrupted"
        task.updated_at = self._current_timestamp()

        logger.info(f"任务 {task_id} 已中断，中断人: {interrupted_by}, 原因: {reason}")
        return True, "任务已中断"

    def update_cost(
        self,
        task_id: str,
        actual_tokens: int,
        actual_cost: float,
        cost_mode: str = CostMode.ACTUAL.value,
    ) -> bool:
        """更新实际成本"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task.actual_tokens = actual_tokens
        task.actual_cost = actual_cost
        task.cost_mode = cost_mode
        task.updated_at = self._current_timestamp()

        logger.info(f"任务 {task_id} 成本更新: {actual_tokens} tokens, {actual_cost} 成本")

        # 记录到预算引擎（如果可用）
        if BUDGET_ENGINE_AVAILABLE and actual_cost > 0:
            try:
                from .budget_engine import get_budget_engine

                engine = get_budget_engine()

                # 确定任务类型
                task_type = task.openhuman_stage if task.openhuman_stage else task.stage

                engine.record_consumption(
                    task_id=task_id,
                    cost=actual_cost,
                    task_type=task_type,
                    description=task.description[:100] if task.description else "",
                    metadata={
                        "domain": task.domain,
                        "stage": task.stage,
                        "openhuman_stage": task.openhuman_stage,
                        "provider": task.selected_provider,
                        "model": task.selected_model,
                        "tokens": actual_tokens,
                    },
                )
                logger.debug(f"任务 {task_id} 消费已记录到预算引擎")
            except Exception as e:
                logger.warning(f"记录消费到预算引擎失败: {e}")

        return True

    def validate_acceptance(
        self,
        task_id: str,
        evidence_data: Dict[str, Any],
        artifact_paths: Optional[List[str]] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        执行验收验证

        Args:
            task_id: 任务ID
            evidence_data: 证据数据字典
            artifact_paths: 产物路径列表

        Returns:
            (success, message, validation_result)
        """
        if task_id not in self.tasks:
            return False, f"任务不存在: {task_id}", {}

        task = self.tasks[task_id]

        # 获取阶段配置
        stage_registry = self._get_stage_registry()
        stage_info = None
        if stage_registry and task.openhuman_stage:
            stage_info = stage_registry.get_stage_info(task.openhuman_stage)

        # 导入验证引擎
        engine = get_validation_engine()
        if not engine:
            return False, "验证引擎不可用", {}

        # 构建证据包
        from .openhuman_validation import EvidenceBundle

        evidence_bundle = EvidenceBundle(
            task_id=task_id,
            stage=task.openhuman_stage or task.stage,
            artifact_paths=artifact_paths or [],
            required_fields=stage_info.get("evidence_requirements", []) if stage_info else [],
            evidence_data=evidence_data,
        )

        # 执行验证
        validation_result = engine.validate(
            task_id=task_id,
            stage=task.openhuman_stage or task.stage,
            evidence_bundle=evidence_bundle,
            stage_config=stage_info,
        )

        # 根据验证结果更新任务状态
        if validation_result.decision == "pass":
            self.update_task_status(task_id, "accepted")
        elif validation_result.decision == "hitl":
            self.update_task_status(task_id, "pending_hitl")
        elif validation_result.decision == "needs_revision":
            self.update_task_status(task_id, "needs_revision")
        elif validation_result.decision == "fail":
            self.update_task_status(task_id, "validation_failed")

        return True, "验证完成", validation_result.to_dict()

    def get_budget_mode_behavior(self) -> Dict[str, Any]:
        """
        获取当前预算模式对应的行为配置

        Returns:
            行为配置字典，包含 agent_behavior 和 athena_specific 配置
        """
        try:
            # 局部导入，避免循环依赖
            from .skill_execution_with_budget import get_current_mode_behavior

            return get_current_mode_behavior()
        except ImportError as e:
            logger.warning(f"无法导入预算模式行为映射模块: {e}")
        except Exception as e:
            logger.warning(f"获取预算模式行为失败: {e}")

        # 返回安全默认值（正常模式）
        return {
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
        }

    def check_tool_guardrail(
        self,
        task_id: str,
        tool_name: str,
        tool_type: str = "general",
    ) -> Dict[str, Any]:
        """
        检查工具调用是否允许（前置授权检查）

        Args:
            task_id: 任务ID
            tool_name: 工具名称
            tool_type: 工具类型 (general, skill, software, etc.)

        Returns:
            dict with keys: allowed, decision, reason, hitl_required,
                           policy_violations, stage_info, task_info
        """
        if task_id not in self.tasks:
            return {
                "allowed": False,
                "decision": "reject",
                "reason": f"任务不存在: {task_id}",
                "hitl_required": False,
                "policy_violations": ["task_not_found"],
                "stage_info": None,
                "task_info": None,
            }

        task = self.tasks[task_id]

        # 获取阶段注册表
        stage_registry = self._get_stage_registry()
        if not stage_registry:
            logger.warning("阶段注册表不可用，跳过 guardrail 检查")
            return {
                "allowed": True,
                "decision": "allow",
                "reason": "阶段注册表不可用，默认允许",
                "hitl_required": False,
                "policy_violations": [],
                "stage_info": None,
                "task_info": task.to_dict(),
            }

        # 确定阶段ID：优先使用 openhuman_stage，否则使用内部 stage
        stage_id = task.openhuman_stage if task.openhuman_stage else task.stage

        # 检查是否为 OpenHuman 阶段
        if task.domain == "openhuman" and task.openhuman_stage:
            # 获取阶段配置
            stage_info = stage_registry.get_stage_info(stage_id)

            # 尝试使用验证引擎的 pre_tool_guardrail（集成 validation_rule_set）
            validation_engine = get_validation_engine()
            guardrail_result = None

            if (
                validation_engine
                and stage_info
                and not isinstance(stage_info, dict)
                and hasattr(stage_info, "to_dict")
            ):
                stage_config = stage_info.to_dict()
                guardrail_result = validation_engine.pre_tool_guardrail(
                    stage_id=stage_id,
                    tool_name=tool_name,
                    stage_config=stage_config,
                )
            elif validation_engine and stage_info and isinstance(stage_info, dict):
                # stage_info 已经是字典
                guardrail_result = validation_engine.pre_tool_guardrail(
                    stage_id=stage_id,
                    tool_name=tool_name,
                    stage_config=stage_info,
                )

            # 如果验证引擎不可用或返回空，使用阶段注册表的 guardrail 检查
            if not guardrail_result:
                guardrail_result = stage_registry.check_tool_guardrail(stage_id, tool_name)

            # 添加审计信息
            guardrail_result["task_id"] = task_id
            guardrail_result["tool_name"] = tool_name
            guardrail_result["tool_type"] = tool_type
            guardrail_result["stage_id"] = stage_id
            guardrail_result["domain"] = task.domain
            guardrail_result["validation_engine_used"] = (
                "validation_engine" in locals() and validation_engine is not None
            )

            # 记录审计事件
            try:
                task_dir = TASKS_DIR / task_id
                if task_dir.exists():
                    update_trace_event(
                        task_dir,
                        "tool_guardrail_check",
                        {
                            "timestamp": self._current_timestamp(),
                            "tool_name": tool_name,
                            "tool_type": tool_type,
                            "stage_id": stage_id,
                            "guardrail_result": guardrail_result,
                        },
                    )
            except Exception as e:
                logger.warning(f"记录 guardrail 审计事件失败: {e}")

            return guardrail_result
        else:
            # 工程领域阶段：目前默认允许，但可以添加特定规则
            logger.debug(f"工程领域任务 {task_id} 使用工具 {tool_name}，默认允许")
            return {
                "allowed": True,
                "decision": "allow",
                "reason": "工程领域阶段默认允许",
                "hitl_required": False,
                "policy_violations": [],
                "stage_info": None,
                "task_info": task.to_dict(),
                "task_id": task_id,
                "tool_name": tool_name,
                "tool_type": tool_type,
                "stage_id": stage_id,
                "domain": task.domain,
            }

    def _get_stage_registry(self):
        """获取阶段注册表（延迟导入）"""
        try:
            from .openhuman_stage_registry import get_registry

            return get_registry()
        except ImportError:
            return None

    # --- P1 Sub-Agent Bus 集成 ---
    def delegate_concurrent_tasks(
        self,
        task_descriptions: List[Dict[str, Any]],
        concurrency_budget: str = "medium",
        merge_strategy: str = "dependency_aware",
    ) -> Dict[str, Any]:
        """
        委派并发任务到 Sub-Agent Bus

        Args:
            task_descriptions: 任务描述列表，每个包含:
                - role: researcher/builder/reviewer/operator
                - payload: 任务负载数据
                - description: 任务描述
                - dependencies: 依赖任务ID列表（可选）
                - timeout_seconds: 超时时间（可选）
                - priority: 优先级（可选）
            concurrency_budget: 并发预算 low/medium/high
            merge_strategy: 合并策略 sequential/parallel/dependency_aware

        Returns:
            委派响应
        """
        try:
            # 根据预算模式调整并发预算
            behavior = self.get_budget_mode_behavior()
            agent_behavior = behavior.get("agent_behavior", {})
            if agent_behavior.get("degradation_level") in ["high", "extreme"]:
                # 降级模式下降低并发预算
                if concurrency_budget == "high":
                    concurrency_budget = "medium"
                elif concurrency_budget == "medium":
                    concurrency_budget = "low"

            # 延迟导入避免循环依赖
            from .sub_agent_bus import (
                AgentRole,
                ConcurrencyBudget,
                DelegationRequest,
                TaskInput,
                get_bus,
            )

            # 转换预算字符串为枚举
            budget_map = {
                "low": ConcurrencyBudget.LOW,
                "medium": ConcurrencyBudget.MEDIUM,
                "high": ConcurrencyBudget.HIGH,
            }
            budget = budget_map.get(concurrency_budget.lower(), ConcurrencyBudget.MEDIUM)

            # 创建任务输入
            tasks = []
            for i, desc in enumerate(task_descriptions):
                task_id = desc.get("task_id", f"orchestrator_task_{uuid.uuid4().hex[:8]}")

                # 转换角色字符串为枚举
                role_str = desc.get("role", "builder").lower()
                role_map = {
                    "researcher": AgentRole.RESEARCHER,
                    "builder": AgentRole.BUILDER,
                    "reviewer": AgentRole.REVIEWER,
                    "operator": AgentRole.OPERATOR,
                }
                role = role_map.get(role_str, AgentRole.BUILDER)

                task_input = TaskInput(
                    task_id=task_id,
                    role=role,
                    payload=desc.get("payload", {}),
                    context=desc.get("context", {}),
                    dependencies=desc.get("dependencies", []),
                    timeout_seconds=desc.get("timeout_seconds", 300),
                    priority=desc.get("priority", 0),
                    metadata={
                        "description": desc.get("description", ""),
                        "source": "athena_orchestrator",
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
                tasks.append(task_input)

            # 创建委派请求
            request_id = f"orchestrator_request_{uuid.uuid4().hex[:8]}"
            request = DelegationRequest(
                request_id=request_id,
                tasks=tasks,
                concurrency_budget=budget,
                merge_strategy=merge_strategy,
                metadata={
                    "orchestrator_task_count": len(tasks),
                    "timestamp": time.time(),
                },
            )

            # 获取总线并委派
            bus = get_bus(max_workers=3)
            response = bus.delegate(request)

            # 转换为字典返回
            return {
                "success": True,
                "delegation_id": response.delegation_id,
                "request_id": response.request_id,
                "accepted_tasks": response.accepted_tasks,
                "rejected_tasks": response.rejected_tasks,
                "concurrency_limit": response.concurrency_limit,
                "worker_count": response.worker_count,
                "estimated_completion_seconds": response.estimated_completion_time_seconds,
                "merge_strategy": merge_strategy,
            }

        except Exception as e:
            logging.getLogger(__name__).error(f"委派并发任务失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def get_delegation_status(self, delegation_id: str) -> Optional[Dict[str, Any]]:
        """获取委派状态"""
        try:
            from .sub_agent_bus import get_bus

            bus = get_bus()
            status = bus.get_status(delegation_id)
            if not status:
                return None

            # 转换为字典
            return {
                "delegation_id": status.delegation_id,
                "request_id": status.request_id,
                "status": status.status.value,
                "progress_percent": status.progress_percent,
                "completed_tasks": status.completed_tasks,
                "total_tasks": status.total_tasks,
                "task_statuses": {
                    task_id: status.value for task_id, status in status.task_statuses.items()
                },
                "start_time": status.start_time,
                "end_time": status.end_time,
                "errors": status.errors,
            }
        except Exception as e:
            logging.getLogger(__name__).error(f"获取委派状态失败: {e}", exc_info=True)
            return None

    def get_task_output(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务输出"""
        try:
            from .sub_agent_bus import get_bus

            bus = get_bus()
            output = bus.get_task_output(task_id)
            if not output:
                return None

            # 转换为字典
            return {
                "task_id": output.task_id,
                "role": output.role.value,
                "status": output.status.value,
                "result": output.result,
                "error": output.error,
                "artifacts": output.artifacts,
                "execution_time_ms": output.execution_time_ms,
                "metadata": output.metadata,
            }
        except Exception as e:
            logging.getLogger(__name__).error(f"获取任务输出失败: {e}", exc_info=True)
            return None

    def record_tool_call(
        self,
        task_id: str,
        tool_name: str,
        tool_output: Any,
        execution_time_ms: float = 0.0,
        error: Optional[str] = None,
        **metadata,
    ) -> bool:
        """
        记录工具调用到执行图

        这是工具结果协议接线点
        """
        if task_id not in self.tasks:
            return False

        # 同步到执行图（如果集成可用）
        if EXECUTION_INTEGRATION_AVAILABLE and get_integration:
            try:
                integration = get_integration()
                success = integration.record_tool_call(
                    task_id=task_id,
                    tool_name=tool_name,
                    tool_output=tool_output,
                    execution_time_ms=execution_time_ms,
                    error=error,
                    **metadata,
                )
                if success:
                    logger.debug(f"工具调用记录到执行图: {task_id}, {tool_name}")
                return success
            except Exception as e:
                logger.warning(f"执行图工具调用记录失败: {e}")
                return False

        return True  # 如果集成不可用，仍返回成功（向后兼容）


# 全局编排器实例
_orchestrator_instance: Optional[AthenaOrchestrator] = None


def get_orchestrator() -> AthenaOrchestrator:
    """获取全局编排器实例"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AthenaOrchestrator()
    return _orchestrator_instance


if __name__ == "__main__":
    # 测试代码
    print("=== Athena Orchestrator 测试 ===")

    orchestrator = AthenaOrchestrator()

    # 测试工程阶段
    print("\n1. 测试工程阶段:")
    success, task_id, metadata = orchestrator.create_task(
        stage="plan", domain="engineering", description="测试规划任务"
    )
    print(f"  成功: {success}, 任务ID: {task_id}")
    print(f"  元数据: {json.dumps(metadata, indent=2, ensure_ascii=False)}")

    # 测试 OpenHuman 阶段映射
    print("\n2. 测试 OpenHuman 阶段映射:")
    test_cases = [
        ("distill", "提炼"),
        ("skill_design", "技能设计"),
        ("dispatch", "任务分发"),
        ("acceptance", "验收结算"),
        ("settlement", "结算分账"),
        ("audit", "审计追溯"),
    ]

    for stage, label in test_cases:
        success, task_id, metadata = orchestrator.create_task(
            stage=stage, domain="openhuman", description=f"测试 {label} 任务"
        )
        print(f"  {stage} ({label}): 成功={success}, 任务ID={task_id}")
        if success:
            print(
                f"    内部阶段: {metadata.get('stage')}, OpenHuman阶段: {metadata.get('openhuman_stage')}"
            )

    # 测试非法阶段
    print("\n3. 测试非法阶段:")
    success, error, _ = orchestrator.create_task(
        stage="invalid_stage", domain="engineering", description="非法阶段测试"
    )
    print(f"  非法工程阶段: 成功={success}, 错误={error}")

    success, error, _ = orchestrator.create_task(
        stage="invalid_openhuman",
        domain="openhuman",
        description="非法OpenHuman阶段测试",
    )
    print(f"  非法OpenHuman阶段: 成功={success}, 错误={error}")

    print("\n4. 测试任务列表:")
    tasks = orchestrator.list_tasks()
    print(f"  总任务数: {len(tasks)}")
    for task in tasks:
        print(f"    {task['task_id']}: {task['domain']}/{task['stage']} - {task['description']}")
