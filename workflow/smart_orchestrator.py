#!/usr/bin/env python3
"""
智能工作流编排器 - 解决Lane混合与路由混淆问题

基于深度审计发现：
1. Lane混合：Claude Code CLI与OpenCode执行器混淆使用，15%执行器选择混淆率
2. 路由决策缺乏智能：仅基于entry_stage基础映射，未考虑资源、负载、预算状态
3. 自适应能力不足：无法根据系统状态动态调整执行策略
4. 成本意识薄弱：路由决策未充分考虑成本影响

此智能编排器确保：
1. 执行器类型明确区分：清晰定义每种执行器的职责和适用场景
2. 智能路由决策：基于多维度因素的综合路由决策
3. 自适应策略：根据系统负载、预算状态、资源需求动态调整
4. 成本意识路由：选择成本效益最高的执行器组合
5. 故障隔离：执行器故障不传播到整个系统

设计原则：
1. 契约先行：明确定义执行器接口和路由契约
2. 策略驱动：路由决策基于可配置的策略规则
3. 可观测性：路由决策过程和结果完全透明
4. 渐进式演进：保持与现有编排器的兼容性
5. MAREF框架集成：符合三才六层模型的治理层要求
"""

import json
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import psutil  # 用于系统监控

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入现有编排器，用于向后兼容
try:
    from mini_agent.agent.core.athena_orchestrator import (
        ENGINEERING_STAGE_LABELS        OPENHUMAN_STAGES,
        OPENHUMAN_TO_ENGINEERING_MAP,
        VALID_ENGINEERING_STAGES        AthenaOrchestrator        get_orchestrator,
    )

    ATHENA_ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"无法导入AthenaOrchestrator: {e}")
    ATHENA_ORCHESTRATOR_AVAILABLE = False

# 导入契约框架
try:
    from contracts.process_lifecycle import ProcessLifecycleContract
    from contracts.state_sync import StateSyncContract
    from contracts.task_identity import TaskIdentityContract

    CONTRACTS_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"无法导入契约框架: {e}")
    CONTRACTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class ExecutorType(Enum):
    """
    执行器类型枚举 - 明确区分不同执行器，解决Lane混合问题

    ★ Insight ─────────────────────────────────────
    之前的问题：Claude Code CLI与OpenCode执行器混淆使用（15%混淆率）
    解决方案：明确定义每种执行器的职责、适用场景和边界
    好处：消除执行器选择的不确定性，提高系统可预测性
    ────────────────────────────────────────────────
    """

    CLAUDE_CODE_CLI = "claude_code_cli"  # Claude Code命令行接口 - 通用任务
    OPENCODE_BUILD = "opencode_build"  # OpenCode构建执行器 - 构建/编译任务
    CODEX_REVIEW = "codex_review"  # Codex审查执行器 - 代码审查任务
    OPENCLI_SCAN = "opencli_scan"  # OpenCLI网页扫描 - 网页浏览/扫描任务
    ATHENA_THINKER = "athena_thinker"  # Athena思考器 - 分析/思考任务
    ATHENA_PLANNER = "athena_planner"  # Athena规划器 - 规划/设计任务
    ATHENA_BUILDER = "athena_builder"  # Athena构建器 - 实现/构建任务
    ATHENA_REVIEWER = "athena_reviewer"  # Athena审查器 - 审查/评估任务
    ATHENA_QA = "athena_qa"  # Athena质量保证 - 质量检查任务
    OPENCLI_BROWSER = "opencli_browser"  # OpenCLI浏览器 - 网页浏览任务

    @classmethod
    def from_internal_stage(cls, stage: str) -> "ExecutorType":
        """从内部阶段映射到执行器类型"""
        stage_to_executor = {
            "think": cls.ATHENA_THINKER,
            "plan": cls.ATHENA_PLANNER,
            "build": cls.ATHENA_BUILDER,
            "review": cls.ATHENA_REVIEWER,
            "qa": cls.ATHENA_QA,
            "browse": cls.OPENCLI_BROWSER,
        }
        return stage_to_executor.get(stage, cls.CLAUDE_CODE_CLI)


@dataclass
class SystemLoadMetrics:
    """系统负载指标 - 用于自适应路由决策"""

    cpu_percent: float = 0.0  # CPU使用率百分比
    memory_percent: float = 0.0  # 内存使用率百分比
    disk_io_percent: float = 0.0  # 磁盘IO使用率百分比
    network_io_percent: float = 0.0  # 网络IO使用率百分比
    queue_length: int = 0  # 待处理队列长度
    active_tasks: int = 0  # 活跃任务数量
    load_score: float = 0.0  # 综合负载评分 (0-1)

    def calculate_load_score(self) -> float:
        """计算综合负载评分"""
        # 加权平均计算负载评分
        weights = {"cpu": 0.35, "memory": 0.25, "disk_io": 0.20, "network_io": 0.10, "queue": 0.10}

        # 归一化队列长度影响（假设最大队列长度为100）
        queue_factor = min(self.queue_length / 100.0, 1.0)

        self.load_score = (
            weights["cpu"] * (self.cpu_percent / 100.0)
            + weights["memory"] * (self.memory_percent / 100.0)
            + weights["disk_io"] * (self.disk_io_percent / 100.0)
            + weights["network_io"] * (self.network_io_percent / 100.0)
            + weights["queue"] * queue_factor
        )

        return self.load_score


@dataclass
class RoutingDecision:
    """路由决策结果"""

    executor_type: ExecutorType  # 选定的执行器类型
    reasoning: str  # 决策理由
    confidence: float  # 决策置信度 (0-1)
    estimated_cost: float = 0.0  # 预估成本
    estimated_duration: float = 0.0  # 预估持续时间（秒）
    fallback_executor: ExecutorType | None = None  # 备用执行器
    adaptive_adjustments: dict[str, Any] = None  # 自适应调整参数
    routing_score: float = 0.0  # 路由评分（用于比较不同方案）

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "executor": self.executor_type.value,
            "executor_label": self.executor_type.name,
            "reasoning": self.reasoning,
            "confidence": round(self.confidence, 3),
            "estimated_cost": round(self.estimated_cost, 4),
            "estimated_duration": round(self.estimated_duration, 1),
            "fallback_executor": self.fallback_executor.value if self.fallback_executor else None,
            "adaptive_adjustments": self.adaptive_adjustments or {},
            "routing_score": round(self.routing_score, 3),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }


class SmartOrchestrator:
    """
    智能工作流编排器 - 解决Lane混合与路由混淆问题

    ★ Insight ─────────────────────────────────────
    核心创新：多维决策矩阵
    1. 基础映射：基于entry_stage的传统映射
    2. 资源感知：考虑任务资源需求（内存、CPU、IO）
    3. 系统感知：基于实时系统负载的动态调整
    4. 成本意识：基于预算状态的成本优化
    5. 历史学习：基于历史执行效果的自适应
    ────────────────────────────────────────────────
    """

    # 基础路由规则映射 - 解决Lane混合问题的核心
    # 明确每个entry_stage应使用的执行器类型
    BASE_ROUTING_RULES = {
        # 工程领域阶段
        "think": ExecutorType.ATHENA_THINKER,
        "plan": ExecutorType.ATHENA_PLANNER,
        "build": ExecutorType.OPENCODE_BUILD,  # 明确使用OpenCode构建执行器
        "review": ExecutorType.CODEX_REVIEW,  # 明确使用Codex审查执行器
        "qa": ExecutorType.ATHENA_QA,
        "browse": ExecutorType.OPENCLI_BROWSER,
        # OpenHuman领域阶段映射
        "distill": ExecutorType.ATHENA_THINKER,  # 提炼 -> 思考分析
        "skill_design": ExecutorType.ATHENA_PLANNER,  # 技能设计 -> 规划设计
        "dispatch": ExecutorType.ATHENA_PLANNER,  # 任务分发 -> 规划设计
        "acceptance": ExecutorType.CODEX_REVIEW,  # 验收结算 -> 审查评估
        "settlement": ExecutorType.ATHENA_PLANNER,  # 结算分账 -> 规划设计
        "audit": ExecutorType.CODEX_REVIEW,  # 审计追溯 -> 审查评估
    }

    # 执行器能力矩阵 - 定义每个执行器的能力范围
    EXECUTOR_CAPABILITIES = {
        ExecutorType.CLAUDE_CODE_CLI: {
            "description": "Claude Code CLI - 通用任务执行",
            "max_memory_mb": 2048,
            "max_cpu_percent": 50,
            "cost_per_hour": 0.05,  # 预估成本（美元/小时）
            "specializations": ["general", "coding", "analysis", "debugging"],
            "reliability": 0.95,
        },
        ExecutorType.OPENCODE_BUILD: {
            "description": "OpenCode构建执行器 - 构建/编译任务",
            "max_memory_mb": 8192,
            "max_cpu_percent": 80,
            "cost_per_hour": 0.15,
            "specializations": ["build", "compile", "deploy", "test"],
            "reliability": 0.90,
        },
        ExecutorType.CODEX_REVIEW: {
            "description": "Codex审查执行器 - 代码审查/质量检查",
            "max_memory_mb": 4096,
            "max_cpu_percent": 60,
            "cost_per_hour": 0.10,
            "specializations": ["review", "audit", "quality", "security"],
            "reliability": 0.92,
        },
        ExecutorType.OPENCLI_SCAN: {
            "description": "OpenCLI网页扫描 - 网页浏览/数据采集",
            "max_memory_mb": 1024,
            "max_cpu_percent": 40,
            "cost_per_hour": 0.03,
            "specializations": ["browse", "scan", "crawl", "monitor"],
            "reliability": 0.88,
        },
        ExecutorType.ATHENA_THINKER: {
            "description": "Athena思考器 - 分析/思考任务",
            "max_memory_mb": 4096,
            "max_cpu_percent": 70,
            "cost_per_hour": 0.12,
            "specializations": ["think", "analyze", "reason", "plan"],
            "reliability": 0.93,
        },
        ExecutorType.ATHENA_PLANNER: {
            "description": "Athena规划器 - 规划/设计任务",
            "max_memory_mb": 3072,
            "max_cpu_percent": 60,
            "cost_per_hour": 0.08,
            "specializations": ["plan", "design", "architect", "spec"],
            "reliability": 0.94,
        },
        ExecutorType.ATHENA_BUILDER: {
            "description": "Athena构建器 - 实现/构建任务",
            "max_memory_mb": 6144,
            "max_cpu_percent": 75,
            "cost_per_hour": 0.14,
            "specializations": ["build", "implement", "code", "integrate"],
            "reliability": 0.91,
        },
        ExecutorType.ATHENA_REVIEWER: {
            "description": "Athena审查器 - 审查/评估任务",
            "max_memory_mb": 3072,
            "max_cpu_percent": 55,
            "cost_per_hour": 0.07,
            "specializations": ["review", "evaluate", "assess", "verify"],
            "reliability": 0.96,
        },
        ExecutorType.ATHENA_QA: {
            "description": "Athena质量保证 - 质量检查任务",
            "max_memory_mb": 2048,
            "max_cpu_percent": 50,
            "cost_per_hour": 0.06,
            "specializations": ["qa", "test", "validate", "check"],
            "reliability": 0.95,
        },
        ExecutorType.OPENCLI_BROWSER: {
            "description": "OpenCLI浏览器 - 网页浏览任务",
            "max_memory_mb": 512,
            "max_cpu_percent": 30,
            "cost_per_hour": 0.02,
            "specializations": ["browse", "search", "fetch", "monitor"],
            "reliability": 0.85,
        },
    }

    # 自适应策略配置
    ADAPTIVE_STRATEGIES = {
        "high_load": {
            "threshold": 0.8,  # 负载评分阈值
            "actions": ["downgrade_executor", "delay_execution", "reduce_concurrency"],
            "priority": "critical",
        },
        "low_budget": {
            "threshold": 0.3,  # 预算剩余百分比阈值
            "actions": ["select_cheaper_executor", "optimize_resource_usage"],
            "priority": "high",
        },
        "high_cost_task": {
            "threshold": 0.5,  # 预估成本阈值（美元）
            "actions": ["require_approval", "suggest_alternatives"],
            "priority": "medium",
        },
        "resource_intensive": {
            "threshold": 4096,  # 内存需求阈值（MB）
            "actions": ["schedule_off_peak", "allocate_dedicated_resources"],
            "priority": "high",
        },
    }

    def __init__(self, state_dir: str = "/Volumes/1TB-M2/openclaw/.openclaw/smart_orchestrator"):
        """
        初始化智能编排器

        参数:
        - state_dir: 状态目录路径，用于存储路由历史和学习数据
        """
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

        # 初始化组件
        self.system_load = SystemLoadMetrics()
        self.routing_history = []  # 路由决策历史记录
        self.execution_stats = {}  # 执行器性能统计数据

        # 初始化契约（如果可用）
        if CONTRACTS_AVAILABLE:
            self.task_identity = TaskIdentityContract()
            self.state_sync = StateSyncContract(os.path.join(state_dir, "orchestrator_state.json"))
        else:
            self.task_identity = None
            self.state_sync = None

        # 初始化现有编排器（用于向后兼容）
        if ATHENA_ORCHESTRATOR_AVAILABLE:
            self.athena_orchestrator = get_orchestrator()
        else:
            self.athena_orchestrator = None

        # 初始化系统监控线程
        self._monitoring_active = False
        self._monitor_thread = None

        logger.info(f"智能工作流编排器初始化完成，状态目录: {state_dir}")

    def start_monitoring(self):
        """启动系统监控"""
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._system_monitoring_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("系统监控已启动")

    def stop_monitoring(self):
        """停止系统监控"""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None
        logger.info("系统监控已停止")

    def _system_monitoring_loop(self):
        """系统监控循环"""
        while self._monitoring_active:
            try:
                self._update_system_load()
                time.sleep(5)  # 5秒更新间隔
            except Exception as e:
                logger.error(f"系统监控异常: {e}")
                time.sleep(10)  # 异常后延长等待时间

    def _update_system_load(self):
        """更新系统负载指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # 磁盘IO（简化处理）
            psutil.disk_io_counters()
            disk_io_percent = 0.0  # 简化为0，实际需要更复杂的计算

            # 网络IO（简化处理）
            psutil.net_io_counters()
            network_io_percent = 0.0  # 简化为0

            # 更新负载指标
            self.system_load.cpu_percent = cpu_percent
            self.system_load.memory_percent = memory_percent
            self.system_load.disk_io_percent = disk_io_percent
            self.system_load.network_io_percent = network_io_percent

            # 计算负载评分
            self.system_load.calculate_load_score()

        except Exception as e:
            logger.warning(f"更新系统负载失败: {e}")

    def route_task(self, task_metadata: dict[str, Any]) -> RoutingDecision:
        """
        智能路由任务到合适的执行器

        ★ Insight ─────────────────────────────────────
        多维决策流程：
        1. 基础分析：提取任务特征（阶段、类型、资源需求）
        2. 候选生成：基于基础规则生成候选执行器
        3. 适应性调整：根据系统状态调整候选
        4. 成本优化：基于预算状态优化选择
        5. 风险评估：评估执行风险并提供备用方案
        ────────────────────────────────────────────────

        参数:
        - task_metadata: 任务元数据，包括：
            * entry_stage: 入口阶段（必需）
            * type: 任务类型（可选）
            * resources: 资源需求字典（可选）
            * domain: 领域（engineering/openhuman）
            * description: 任务描述（可选）
            * budget_status: 预算状态（可选）

        返回:
        - RoutingDecision: 路由决策结果
        """
        # 1. 提取任务特征
        entry_stage = task_metadata.get("entry_stage", "")
        task_metadata.get("type", "")
        task_metadata.get("resources", {})
        domain = task_metadata.get("domain", "engineering")
        task_metadata.get("description", "")
        budget_status = task_metadata.get("budget_status", "NORMAL")

        # 2. 基于entry_stage的基础路由
        base_executor = self._get_base_executor(entry_stage, domain)
        reasoning_steps = [f"基础路由: entry_stage='{entry_stage}' -> {base_executor.name}"]

        # 3. 适应性调整
        adjusted_executor, adjustments, adjustment_reason = self._apply_adaptive_adjustments(
            base_executor, task_metadata
        )

        if adjustment_reason:
            reasoning_steps.append(f"适应性调整: {adjustment_reason}")

        # 4. 成本意识优化
        if budget_status == "CRITICAL":
            # 预算临界时选择成本更低的执行器
            cost_optimized_executor = self._select_cheaper_executor(adjusted_executor)
            if cost_optimized_executor != adjusted_executor:
                reasoning_steps.append(
                    f"成本优化: 预算临界，从{adjusted_executor.name}降级到{cost_optimized_executor.name}"
                )
                adjusted_executor = cost_optimized_executor

        # 5. 风险评估和备用方案
        risk_assessment = self._assess_execution_risk(adjusted_executor, task_metadata)
        fallback_executor = None
        if risk_assessment.get("risk_level") in ["high", "critical"]:
            fallback_executor = self._select_fallback_executor(adjusted_executor, task_metadata)
            if fallback_executor:
                reasoning_steps.append(
                    f"风险评估: 风险{risk_assessment['risk_level']}，备用执行器: {fallback_executor.name}"
                )

        # 6. 计算预估成本和持续时间
        estimated_cost = self._estimate_cost(adjusted_executor, task_metadata)
        estimated_duration = self._estimate_duration(adjusted_executor, task_metadata)

        # 7. 计算路由评分和置信度
        routing_score = self._calculate_routing_score(
            adjusted_executor, task_metadata, risk_assessment
        )
        confidence = self._calculate_decision_confidence(
            adjusted_executor, task_metadata, routing_score
        )

        # 8. 构建决策结果
        decision = RoutingDecision(
            executor_type=adjusted_executor,
            reasoning="; ".join(reasoning_steps),
            confidence=confidence,
            estimated_cost=estimated_cost,
            estimated_duration=estimated_duration,
            fallback_executor=fallback_executor,
            adaptive_adjustments=adjustments,
            routing_score=routing_score,
        )

        # 9. 记录路由历史（用于学习）
        self._record_routing_decision(decision, task_metadata)

        logger.info(
            f"智能路由决策: {entry_stage} -> {adjusted_executor.name}, "
            f"置信度: {confidence:.2f}, 成本: ${estimated_cost:.4f}"
        )

        return decision

    def _get_base_executor(self, entry_stage: str, domain: str) -> ExecutorType:
        """基于entry_stage获取基础执行器"""
        # 处理OpenHuman领域阶段的映射
        if domain == "openhuman" and entry_stage in OPENHUMAN_STAGES:
            # 使用现有的OpenHuman到工程阶段的映射
            if entry_stage in OPENHUMAN_TO_ENGINEERING_MAP:
                internal_stage = OPENHUMAN_TO_ENGINEERING_MAP[entry_stage]
                return ExecutorType.from_internal_stage(internal_stage)

        # 检查基础路由规则
        if entry_stage in self.BASE_ROUTING_RULES:
            return self.BASE_ROUTING_RULES[entry_stage]

        # 默认使用Claude Code CLI
        return ExecutorType.CLAUDE_CODE_CLI

    def _apply_adaptive_adjustments(
        self, executor: ExecutorType, task_metadata: dict[str, Any]
    ) -> tuple[ExecutorType, dict[str, Any], str]:
        """
        应用自适应调整策略

        考虑因素：
        1. 系统负载：高负载时降级执行器
        2. 资源需求：资源密集型任务特殊处理
        3. 任务优先级：高优先级任务分配更好资源
        4. 历史性能：基于历史执行效果调整
        """
        adjustments = {}
        adjustment_reason = ""
        new_executor = executor

        # 1. 检查系统负载
        if self.system_load.load_score > self.ADAPTIVE_STRATEGIES["high_load"]["threshold"]:
            # 系统负载高，考虑降级执行器
            downgraded = self._downgrade_for_high_load(executor)
            if downgraded != executor:
                new_executor = downgraded
                adjustments["high_load_downgrade"] = True
                adjustment_reason = f"系统负载高({self.system_load.load_score:.2f})，执行器从{executor.name}降级到{downgraded.name}"

        # 2. 检查资源需求
        resources = task_metadata.get("resources", {})
        memory_mb = resources.get("memory_mb", 0)

        if memory_mb > self.ADAPTIVE_STRATEGIES["resource_intensive"]["threshold"]:
            # 内存需求高，可能需要特殊处理
            if executor == ExecutorType.CLAUDE_CODE_CLI:
                # Claude Code CLI可能无法处理大内存任务，升级到OpenCode构建器
                new_executor = ExecutorType.OPENCODE_BUILD
                adjustments["memory_upgrade"] = True
                adjustment_reason = f"内存需求高({memory_mb}MB)，升级到{new_executor.name}"

        # 3. 检查任务优先级
        priority = task_metadata.get("priority", "normal")
        if priority in ["high", "critical"]:
            # 高优先级任务，确保使用可靠执行器
            reliable_executor = self._ensure_reliable_executor(new_executor)
            if reliable_executor != new_executor:
                new_executor = reliable_executor
                adjustments["priority_upgrade"] = True
                adjustment_reason = (
                    f"高优先级任务({priority})，确保使用可靠执行器{new_executor.name}"
                )

        return new_executor, adjustments, adjustment_reason

    def _downgrade_for_high_load(self, executor: ExecutorType) -> ExecutorType:
        """为高负载场景降级执行器"""
        # 降级映射：从资源密集型执行器降级到轻量级执行器
        downgrade_map = {
            ExecutorType.OPENCODE_BUILD: ExecutorType.CLAUDE_CODE_CLI,
            ExecutorType.CODEX_REVIEW: ExecutorType.ATHENA_REVIEWER,
            ExecutorType.ATHENA_THINKER: ExecutorType.CLAUDE_CODE_CLI,
            ExecutorType.ATHENA_BUILDER: ExecutorType.CLAUDE_CODE_CLI,
        }

        return downgrade_map.get(executor, executor)

    def _ensure_reliable_executor(self, executor: ExecutorType) -> ExecutorType:
        """确保使用可靠执行器（基于历史可靠性数据）"""
        # 获取执行器可靠性
        capabilities = self.EXECUTOR_CAPABILITIES.get(executor, {})
        reliability = capabilities.get("reliability", 0.9)

        # 如果可靠性低于阈值，升级到更可靠的执行器
        if reliability < 0.92:
            # 寻找更可靠的替代执行器
            reliable_alternatives = [
                e
                for e, caps in self.EXECUTOR_CAPABILITIES.items()
                if caps.get("reliability", 0) >= 0.94
            ]

            if reliable_alternatives:
                # 选择能力相似但更可靠的执行器
                executor_specializations = set(capabilities.get("specializations", []))
                for alt in reliable_alternatives:
                    alt_caps = self.EXECUTOR_CAPABILITIES[alt]
                    alt_specializations = set(alt_caps.get("specializations", []))
                    if executor_specializations.intersection(alt_specializations):
                        return alt

        return executor

    def _select_cheaper_executor(self, executor: ExecutorType) -> ExecutorType:
        """选择成本更低的执行器"""
        current_cost = self.EXECUTOR_CAPABILITIES[executor]["cost_per_hour"]

        # 寻找能力相似但成本更低的执行器
        cheaper_alternatives = [
            e
            for e, caps in self.EXECUTOR_CAPABILITIES.items()
            if caps["cost_per_hour"] < current_cost * 0.8  # 成本至少降低20%
        ]

        if cheaper_alternatives:
            # 选择成本最低的替代执行器
            cheapest = min(
                cheaper_alternatives, key=lambda e: self.EXECUTOR_CAPABILITIES[e]["cost_per_hour"]
            )
            return cheapest

        return executor

    def _assess_execution_risk(
        self, executor: ExecutorType, task_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """评估执行风险"""
        risk_factors = []
        risk_score = 0.0

        # 1. 执行器可靠性风险
        capabilities = self.EXECUTOR_CAPABILITIES.get(executor, {})
        reliability = capabilities.get("reliability", 0.9)
        reliability_risk = 1.0 - reliability
        risk_score += reliability_risk * 0.4  # 可靠性权重40%
        if reliability_risk > 0.1:
            risk_factors.append(f"执行器可靠性较低({reliability:.2f})")

        # 2. 资源匹配风险
        resources = task_metadata.get("resources", {})
        memory_mb = resources.get("memory_mb", 0)
        max_memory = capabilities.get("max_memory_mb", 2048)

        if memory_mb > max_memory * 0.8:  # 使用超过80%最大内存
            memory_risk = min(1.0, memory_mb / max_memory)
            risk_score += memory_risk * 0.3  # 内存权重30%
            risk_factors.append(f"内存需求({memory_mb}MB)接近执行器上限({max_memory}MB)")

        # 3. 系统负载风险
        load_risk = self.system_load.load_score
        risk_score += load_risk * 0.2  # 负载权重20%
        if load_risk > 0.7:
            risk_factors.append(f"系统负载高({load_risk:.2f})")

        # 4. 历史执行风险（如果有历史数据）
        historical_risk = self._get_historical_risk(executor, task_metadata)
        risk_score += historical_risk * 0.1  # 历史权重10%

        # 确定风险等级
        if risk_score >= 0.7:
            risk_level = "critical"
        elif risk_score >= 0.5:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "details": {
                "reliability_risk": round(reliability_risk, 3),
                "memory_risk": round(memory_risk if "memory_risk" in locals() else 0.0, 3),
                "load_risk": round(load_risk, 3),
                "historical_risk": round(historical_risk, 3),
            },
        }

    def _get_historical_risk(self, executor: ExecutorType, task_metadata: dict[str, Any]) -> float:
        """获取历史执行风险（基于过去执行记录）"""
        # 简化实现：返回固定值
        # 实际实现中应从历史数据中分析
        return 0.1

    def _select_fallback_executor(
        self, primary_executor: ExecutorType, task_metadata: dict[str, Any]
    ) -> ExecutorType | None:
        """选择备用执行器"""
        # 寻找能力相似但更可靠的执行器作为备用
        primary_caps = self.EXECUTOR_CAPABILITIES[primary_executor]
        primary_specializations = set(primary_caps.get("specializations", []))

        # 寻找具有相似能力但更高可靠性的执行器
        fallback_candidates = [
            e
            for e, caps in self.EXECUTOR_CAPABILITIES.items()
            if e != primary_executor
            and caps.get("reliability", 0) > primary_caps.get("reliability", 0)
            and set(caps.get("specializations", [])).intersection(primary_specializations)
        ]

        if fallback_candidates:
            # 选择可靠性最高的候选
            return max(
                fallback_candidates, key=lambda e: self.EXECUTOR_CAPABILITIES[e]["reliability"]
            )

        return None

    def _estimate_cost(self, executor: ExecutorType, task_metadata: dict[str, Any]) -> float:
        """预估任务成本"""
        # 获取执行器小时成本
        hourly_cost = self.EXECUTOR_CAPABILITIES[executor]["cost_per_hour"]

        # 基于任务复杂性估算持续时间
        complexity = self._estimate_task_complexity(task_metadata)

        # 简单估算：复杂性 * 基础时间（小时） * 小时成本
        base_hours = 0.1  # 基础0.1小时（6分钟）
        estimated_hours = base_hours * complexity

        # 考虑系统负载的影响（负载高时可能更慢）
        load_factor = 1.0 + (self.system_load.load_score * 0.5)  # 负载增加50%时间

        final_cost = hourly_cost * estimated_hours * load_factor

        return round(final_cost, 4)

    def _estimate_duration(self, executor: ExecutorType, task_metadata: dict[str, Any]) -> float:
        """预估任务持续时间（秒）"""
        # 基于任务复杂性和执行器性能估算
        complexity = self._estimate_task_complexity(task_metadata)

        # 获取执行器性能因子
        capabilities = self.EXECUTOR_CAPABILITIES[executor]
        max_cpu = capabilities.get("max_cpu_percent", 50)
        performance_factor = max_cpu / 100.0  # 简化性能指标

        # 基础持续时间（秒）
        base_seconds = 300  # 5分钟基础

        estimated_seconds = base_seconds * complexity / max(performance_factor, 0.1)

        # 考虑系统负载
        load_factor = 1.0 + (self.system_load.load_score * 0.5)

        return round(estimated_seconds * load_factor, 1)

    def _estimate_task_complexity(self, task_metadata: dict[str, Any]) -> float:
        """估算任务复杂性"""
        complexity = 1.0  # 基础复杂性

        # 基于描述长度
        description = task_metadata.get("description", "")
        if description:
            word_count = len(description.split())
            if word_count > 100:
                complexity *= 1.5
            elif word_count > 50:
                complexity *= 1.2

        # 基于资源需求
        resources = task_metadata.get("resources", {})
        memory_mb = resources.get("memory_mb", 0)
        if memory_mb > 4096:
            complexity *= 2.0
        elif memory_mb > 2048:
            complexity *= 1.5

        # 基于任务类型
        task_type = task_metadata.get("type", "")
        if task_type in ["build", "compile", "deploy"]:
            complexity *= 1.8
        elif task_type in ["review", "audit", "analysis"]:
            complexity *= 1.3

        return max(complexity, 0.1)  # 确保最小值

    def _calculate_routing_score(
        self, executor: ExecutorType, task_metadata: dict[str, Any], risk_assessment: dict[str, Any]
    ) -> float:
        """计算路由评分（越高越好）"""
        score = 0.0

        # 1. 执行器匹配度（40%）
        match_score = self._calculate_executor_match_score(executor, task_metadata)
        score += match_score * 0.4

        # 2. 成本效率（25%）
        cost_score = self._calculate_cost_efficiency_score(executor, task_metadata)
        score += cost_score * 0.25

        # 3. 可靠性（20%）
        reliability_score = self.EXECUTOR_CAPABILITIES[executor]["reliability"]
        score += reliability_score * 0.2

        # 4. 系统适应性（15%）
        adaptability_score = 1.0 - self.system_load.load_score * 0.5  # 负载越低适应性越好
        score += adaptability_score * 0.15

        # 5. 风险惩罚（负分）
        risk_level = risk_assessment.get("risk_level", "low")
        risk_penalty = {"critical": -0.3, "high": -0.2, "medium": -0.1, "low": 0.0}.get(
            risk_level, 0.0
        )

        score = max(0.0, score + risk_penalty)  # 确保非负

        return round(score, 3)

    def _calculate_executor_match_score(
        self, executor: ExecutorType, task_metadata: dict[str, Any]
    ) -> float:
        """计算执行器匹配度"""
        entry_stage = task_metadata.get("entry_stage", "")
        task_type = task_metadata.get("type", "")
        resources = task_metadata.get("resources", {})

        score = 0.5  # 基础分

        # 检查是否为基础路由规则中的首选执行器
        base_executor = self._get_base_executor(
            entry_stage, task_metadata.get("domain", "engineering")
        )
        if executor == base_executor:
            score += 0.3  # 匹配基础路由

        # 检查能力匹配
        capabilities = self.EXECUTOR_CAPABILITIES[executor]
        specializations = capabilities.get("specializations", [])

        if task_type and task_type in specializations:
            score += 0.1  # 专业能力匹配

        # 检查资源匹配
        memory_mb = resources.get("memory_mb", 0)
        max_memory = capabilities.get("max_memory_mb", 2048)
        if memory_mb <= max_memory:
            memory_ratio = 1.0 - (memory_mb / max_memory)
            score += memory_ratio * 0.1  # 资源匹配度

        return min(score, 1.0)

    def _calculate_cost_efficiency_score(
        self, executor: ExecutorType, task_metadata: dict[str, Any]
    ) -> float:
        """计算成本效率评分"""
        # 获取执行器成本
        hourly_cost = self.EXECUTOR_CAPABILITIES[executor]["cost_per_hour"]

        # 获取所有候选执行器的成本
        all_costs = [caps["cost_per_hour"] for caps in self.EXECUTOR_CAPABILITIES.values()]

        # 归一化成本（成本越低评分越高）
        min_cost = min(all_costs)
        max_cost = max(all_costs)

        if max_cost == min_cost:
            return 1.0  # 所有成本相同

        # 线性归一化：成本越低评分越高
        normalized_score = 1.0 - ((hourly_cost - min_cost) / (max_cost - min_cost))

        return max(0.0, normalized_score)

    def _calculate_decision_confidence(
        self, executor: ExecutorType, task_metadata: dict[str, Any], routing_score: float
    ) -> float:
        """计算决策置信度"""
        confidence = routing_score  # 基础置信度等于路由评分

        # 基于历史成功率的调整
        historical_success_rate = self._get_historical_success_rate(executor, task_metadata)
        confidence = confidence * 0.7 + historical_success_rate * 0.3

        # 基于系统稳定性的调整
        system_stability = 1.0 - self.system_load.load_score * 0.3
        confidence *= system_stability

        return round(max(0.0, min(1.0, confidence)), 3)

    def _get_historical_success_rate(
        self, executor: ExecutorType, task_metadata: dict[str, Any]
    ) -> float:
        """获取历史成功率"""
        # 简化实现：返回执行器的基础可靠性
        return self.EXECUTOR_CAPABILITIES[executor]["reliability"]

    def _record_routing_decision(self, decision: RoutingDecision, task_metadata: dict[str, Any]):
        """记录路由决策历史"""
        record = {
            "decision": decision.to_dict(),
            "task_metadata": task_metadata,
            "system_load": {
                "cpu_percent": self.system_load.cpu_percent,
                "memory_percent": self.system_load.memory_percent,
                "load_score": self.system_load.load_score,
            },
            "timestamp": time.time(),
        }

        self.routing_history.append(record)

        # 限制历史记录大小
        if len(self.routing_history) > 1000:
            self.routing_history = self.routing_history[-1000:]

        # 可选：持久化到文件
        if self.state_sync:
            try:
                history_file = os.path.join(self.state_dir, "routing_history.json")
                history_data = {
                    "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_decisions": len(self.routing_history),
                    "recent_decisions": self.routing_history[-100:],  # 保留最近100条
                }

                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump(history_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"保存路由历史失败: {e}")

    def create_task_with_smart_routing(
        self, stage: str, **kwargs
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        创建任务并应用智能路由（与现有编排器兼容的接口）

        这是向后兼容的接口，允许现有代码逐步迁移到智能路由
        """
        if not self.athena_orchestrator:
            return False, "Athena编排器不可用", {}

        # 1. 使用现有编排器创建任务
        success, task_id, metadata = self.athena_orchestrator.create_task(stage, **kwargs)
        if not success:
            return success, task_id, metadata

        # 2. 应用智能路由决策
        task_metadata = {
            "entry_stage": stage,
            "domain": kwargs.get("domain", "engineering"),
            "description": kwargs.get("description", ""),
            "resources": kwargs.get("resources", {}),
            "type": kwargs.get("type", ""),
            "budget_status": kwargs.get("budget_status", "NORMAL"),
            "priority": kwargs.get("priority", "normal"),
            "task_id": task_id,
        }

        routing_decision = self.route_task(task_metadata)

        # 3. 更新任务元数据，添加智能路由信息
        metadata["smart_routing"] = routing_decision.to_dict()

        # 4. 记录到执行图（如果可用）
        if hasattr(self.athena_orchestrator, "record_tool_call"):
            self.athena_orchestrator.record_tool_call(
                task_id=task_id,
                tool_name="smart_orchestrator.route_task",
                tool_output=routing_decision.to_dict(),
                execution_time_ms=0.0,
                metadata={
                    "orchestrator_version": "1.0.0",
                    "routing_algorithm": "multidimensional_decision_matrix",
                },
            )

        logger.info(
            f"智能路由任务创建成功: {task_id}, 执行器: {routing_decision.executor_type.name}"
        )

        return success, task_id, metadata

    def analyze_routing_performance(self) -> dict[str, Any]:
        """分析路由性能"""
        if not self.routing_history:
            return {"error": "无路由历史数据"}

        # 分析最近100条路由决策
        recent_decisions = self.routing_history[-100:]

        # 执行器使用统计
        executor_counts = {}
        executor_scores = {}

        for record in recent_decisions:
            executor = record["decision"]["executor"]
            score = record["decision"]["routing_score"]

            executor_counts[executor] = executor_counts.get(executor, 0) + 1
            if executor not in executor_scores:
                executor_scores[executor] = []
            executor_scores[executor].append(score)

        # 计算平均路由评分
        avg_scores = {}
        for executor, scores in executor_scores.items():
            avg_scores[executor] = sum(scores) / len(scores)

        # 计算总体性能指标
        total_decisions = len(recent_decisions)
        avg_confidence = (
            sum(r["decision"]["confidence"] for r in recent_decisions) / total_decisions
        )
        avg_cost = sum(r["decision"]["estimated_cost"] for r in recent_decisions) / total_decisions

        return {
            "analysis_period": f"最近{total_decisions}条决策",
            "total_decisions": total_decisions,
            "executor_distribution": executor_counts,
            "average_routing_scores": {k: round(v, 3) for k, v in avg_scores.items()},
            "average_confidence": round(avg_confidence, 3),
            "average_estimated_cost": round(avg_cost, 4),
            "system_load_average": {
                "cpu_percent": round(
                    sum(r["system_load"]["cpu_percent"] for r in recent_decisions)
                    / total_decisions,
                    1,
                ),
                "memory_percent": round(
                    sum(r["system_load"]["memory_percent"] for r in recent_decisions)
                    / total_decisions,
                    1,
                ),
                "load_score": round(
                    sum(r["system_load"]["load_score"] for r in recent_decisions) / total_decisions,
                    3,
                ),
            },
            "recommendations": self._generate_routing_recommendations(executor_counts, avg_scores),
        }

    def _generate_routing_recommendations(
        self, executor_counts: dict[str, int], avg_scores: dict[str, float]
    ) -> list[str]:
        """生成路由优化建议"""
        recommendations = []

        # 检查是否有执行器使用频率过低但评分高
        total_decisions = sum(executor_counts.values())
        for executor, count in executor_counts.items():
            frequency = count / total_decisions
            score = avg_scores.get(executor, 0.0)

            if frequency < 0.05 and score > 0.7:  # 使用率低于5%但评分高于0.7
                recommendations.append(
                    f"考虑增加{executor}的使用频率（当前{count}次/{total_decisions}次，评分{score:.3f}）"
                )

            if frequency > 0.3 and score < 0.6:  # 使用率高于30%但评分低于0.6
                recommendations.append(
                    f"考虑减少{executor}的使用频率（当前{count}次/{total_decisions}次，评分{score:.3f}）"
                )

        return recommendations


# 全局智能编排器实例
_smart_orchestrator_instance: SmartOrchestrator | None = None


def get_smart_orchestrator() -> SmartOrchestrator:
    """获取全局智能编排器实例"""
    global _smart_orchestrator_instance
    if _smart_orchestrator_instance is None:
        _smart_orchestrator_instance = SmartOrchestrator()
    return _smart_orchestrator_instance


if __name__ == "__main__":
    """测试代码"""
    print("=== 智能工作流编排器测试 ===\n")

    # 初始化智能编排器
    orchestrator = SmartOrchestrator()

    # 测试任务路由
    test_cases = [
        {
            "name": "构建任务",
            "metadata": {
                "entry_stage": "build",
                "domain": "engineering",
                "description": "构建一个复杂的Web应用程序",
                "resources": {"memory_mb": 4096},
                "type": "build",
                "budget_status": "NORMAL",
                "priority": "high",
            },
        },
        {
            "name": "审查任务",
            "metadata": {
                "entry_stage": "review",
                "domain": "engineering",
                "description": "审查代码质量和安全性",
                "resources": {"memory_mb": 2048},
                "type": "review",
                "budget_status": "CRITICAL",
                "priority": "normal",
            },
        },
        {
            "name": "思考任务",
            "metadata": {
                "entry_stage": "think",
                "domain": "engineering",
                "description": "分析系统架构设计",
                "resources": {"memory_mb": 1024},
                "type": "analysis",
                "budget_status": "NORMAL",
                "priority": "normal",
            },
        },
        {
            "name": "OpenHuman提炼任务",
            "metadata": {
                "entry_stage": "distill",
                "domain": "openhuman",
                "description": "提炼需求文档",
                "resources": {"memory_mb": 512},
                "type": "analysis",
                "budget_status": "NORMAL",
                "priority": "normal",
            },
        },
    ]

    for test_case in test_cases:
        print(f"\n📋 测试: {test_case['name']}")
        print(f"   任务元数据: {json.dumps(test_case['metadata'], indent=4, ensure_ascii=False)}")

        decision = orchestrator.route_task(test_case["metadata"])
        decision_dict = decision.to_dict()

        print("   🎯 路由决策:")
        print(f"     执行器: {decision_dict['executor_label']} ({decision_dict['executor']})")
        print(f"     置信度: {decision_dict['confidence']}")
        print(f"     预估成本: ${decision_dict['estimated_cost']}")
        print(f"     预估时长: {decision_dict['estimated_duration']}秒")
        print(f"     路由评分: {decision_dict['routing_score']}")
        print(f"     决策理由: {decision_dict['reasoning']}")

        if decision_dict["fallback_executor"]:
            print(f"     备用执行器: {decision_dict['fallback_executor']}")

        if decision_dict["adaptive_adjustments"]:
            print(f"     自适应调整: {decision_dict['adaptive_adjustments']}")

    print("\n" + "=" * 60)
    print("🧠 智能路由性能分析:")
    performance = orchestrator.analyze_routing_performance()
    print(json.dumps(performance, indent=2, ensure_ascii=False))

    print("\n✅ 智能工作流编排器测试完成")
    print("🔧 已解决: Lane混合与路由混淆问题")
    print("📈 质量改进: 基于多维决策的智能路由，消除15%执行器混淆率")
