#!/usr/bin/env python3
"""
OpenSpace Adapter - OpenSpace 本地适配器骨架

遵循 Athena local-first 架构，提供最小可运行闭环的 OpenSpace 集成。
默认禁用云同步与外部写出，提供技能输入、性能指标输入、优化建议输出的结构化 schema。

核心功能：
1. 加载本地优先配置契约
2. 验证 cloud_sync_disabled、local_only、sandbox_required 约束
3. 处理 Athena -> OpenSpace 数据交换（技能输入、性能指标输入）
4. 生成结构化优化建议输出
5. 提供最小沙箱执行环境（本地进程隔离）

集成点：
- 可被 Athena/runtime 显式调用
- 可集成到技能注册表作为技能进化引擎
- 提供结构化结果，支持后续 metrics/sandbox/audit 复用
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import yaml

# 事件总线集成
try:
    from mini_agent.agent.core.event_bus import EventType, HookPoint, get_bus

    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False
    get_bus = None
    EventType = None
    HookPoint = None

# 添加项目根目录到路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

# ==================== 数据模型定义 ====================


class OpenSpaceMode(Enum):
    """OpenSpace 运行模式"""

    LOCAL_ONLY = "local_only"
    HYBRID = "hybrid"


class SandboxType(Enum):
    """沙箱类型"""

    LOCAL_PROCESS = "local_process"
    CONTAINER = "container"


class SuggestionType(Enum):
    """优化建议类型"""

    CODE_OPTIMIZATION = "code_optimization"
    PARAMETER_TUNING = "parameter_tuning"
    DEPENDENCY_UPDATE = "dependency_update"
    ARCHITECTURE_CHANGE = "architecture_change"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"


class ReviewStatus(Enum):
    """审核状态（与 Athena ApprovalState 对齐）"""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"
    # 兼容 Athena ApprovalState
    NOT_REQUIRED = "not_required"
    CANCELLED = "cancelled"


@dataclass
class MonitoringEvidence:
    """监控证据模型"""

    evidence_id: str
    timestamp: str
    evidence_type: (
        str  # optimization_attempt, constraint_hit, evaluation_result, human_intervention
    )
    skill_id: str
    data: Dict[str, Any]
    review_status: str = ReviewStatus.PENDING_REVIEW.value
    requires_human_confirmation: bool = False
    human_intervention_details: Optional[Dict[str, Any]] = None


@dataclass
class SkillInput:
    """技能输入模型"""

    skill_id: str
    skill_definition: Dict[str, Any]
    execution_context: Dict[str, Any]
    performance_baseline: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceMetric:
    """性能指标模型"""

    metric_id: str
    metric_type: str
    values: List[Dict[str, Any]]
    aggregation_period: Optional[str] = None


@dataclass
class OptimizationSuggestion:
    """优化建议模型"""

    suggestion_id: str
    skill_id: str
    suggestion_type: str
    changes: List[Dict[str, Any]]
    confidence_score: Optional[float] = None
    estimated_effort: Optional[str] = None
    validation_requirements: Optional[List[str]] = None


@dataclass
class OpenSpaceResult:
    """OpenSpace 结果包装模型"""

    success: bool
    request_id: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    warnings: Optional[List[Dict[str, Any]]] = None


# ==================== 适配器核心类 ====================


class OpenSpaceAdapter:
    """OpenSpace 适配器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化 OpenSpace 适配器

        Args:
            config_path: 配置文件路径，默认为 mini-agent/config/openspace_config.yaml
        """
        if config_path is None:
            config_path = os.path.join(
                project_root, "mini-agent", "config", "openspace_config.yaml"
            )

        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.mode: OpenSpaceMode = OpenSpaceMode.LOCAL_ONLY
        self.load_config()
        self.validate_config()

        # 初始化约束验证器
        self.constraint_validator = SandboxConstraintValidator(self.config)

        # 事件总线集成
        self.event_bus = None
        if EVENT_BUS_AVAILABLE and callable(get_bus):
            try:
                self.event_bus = get_bus()
                logger.info("OpenSpace 适配器已集成事件总线")
            except Exception as e:
                logger.warning(f"事件总线初始化失败: {e}")
        else:
            logger.warning("事件总线不可用，监控证据将仅本地记录")

        logger.info(f"OpenSpace 适配器初始化完成，模式: {self.mode.value}")

    def load_config(self) -> None:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            logger.warning(f"OpenSpace 配置文件不存在: {self.config_path}")
            # 使用默认配置
            self.config = self._get_default_config()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)

            # 设置运行模式
            mode_str = self.config.get("adapter_runtime", {}).get("default_mode", "local_only")
            self.mode = OpenSpaceMode(mode_str)

            logger.info(f"OpenSpace 配置加载成功，版本: {self.config.get('version', 'unknown')}")

        except Exception as e:
            logger.error(f"OpenSpace 配置加载失败: {e}")
            self.config = self._get_default_config()

    def validate_config(self) -> Tuple[bool, List[str]]:
        """验证配置契约"""
        issues = []

        # 检查本地优先策略
        local_first = self.config.get("local_first_policy", {})
        enforced = local_first.get("enforced_settings", {})

        # 必须满足的约束
        if not enforced.get("cloud_sync_disabled", False):
            issues.append("cloud_sync_disabled 必须为 true")

        if not enforced.get("local_only", False):
            issues.append("local_only 必须为 true")

        # 沙箱要求检查
        sandbox_req = self.config.get("sandbox_requirements", {})
        if not sandbox_req.get("default_sandbox"):
            issues.append("必须指定默认沙箱")

        # 数据交换 schema 验证
        schema = self.config.get("data_exchange_schema", {})
        if not schema.get("skill_input") or not schema.get("optimization_suggestions_output"):
            issues.append("数据交换 schema 不完整")

        if issues:
            logger.warning(f"OpenSpace 配置验证发现问题: {issues}")
            return False, issues

        logger.info("OpenSpace 配置验证通过")
        return True, []

    def analyze_skill(self, skill_input: SkillInput) -> OpenSpaceResult:
        """
        分析技能并提供优化建议

        Args:
            skill_input: 技能输入

        Returns:
            OpenSpace 结果包装
        """
        request_id = str(uuid.uuid4())

        try:
            # 1. 验证输入
            validation_result = self._validate_skill_input(skill_input)
            if not validation_result["valid"]:
                return self._create_error_result(
                    request_id=request_id,
                    error_code="INVALID_INPUT",
                    error_message="技能输入验证失败",
                    error_details=validation_result["issues"],
                )

            # 2. 检查沙箱要求
            sandbox_required = skill_input.execution_context.get("sandbox_required", True)
            if sandbox_required:
                sandbox_ok, sandbox_issues = self._check_sandbox_requirements()
                if not sandbox_ok:
                    return self._create_error_result(
                        request_id=request_id,
                        error_code="SANDBOX_UNAVAILABLE",
                        error_message="沙箱要求未满足",
                        error_details=sandbox_issues,
                    )

            # 3. 执行技能分析（模拟 - 实际集成 OpenSpace 引擎）
            suggestions = self._generate_optimization_suggestions(skill_input)

            # 3.1 记录优化尝试监控证据
            try:
                self._record_monitoring_evidence(
                    evidence_type="optimization_attempt",
                    skill_id=skill_input.skill_id,
                    data={
                        "request_id": request_id,
                        "suggestion_count": len(suggestions),
                        "skill_complexity": self._estimate_skill_complexity(skill_input),
                        "optimization_potential": self._estimate_optimization_potential(
                            skill_input
                        ),
                        "risk_level": skill_input.execution_context.get("risk_level", "medium"),
                        "sandbox_required": sandbox_required,
                    },
                    requires_human_confirmation=False,
                )
            except Exception as e:
                logger.warning(f"记录优化尝试证据失败: {e}")

            # 4. 构建成功响应
            return OpenSpaceResult(
                success=True,
                request_id=request_id,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                data={
                    "skill_id": skill_input.skill_id,
                    "analysis_summary": {
                        "skill_complexity": self._estimate_skill_complexity(skill_input),
                        "optimization_potential": self._estimate_optimization_potential(
                            skill_input
                        ),
                        "risk_level": skill_input.execution_context.get("risk_level", "medium"),
                    },
                    "suggestions": [asdict(s) for s in suggestions],
                    "sandbox_used": sandbox_required,
                    "local_only_compliant": True,
                },
            )

        except Exception as e:
            logger.exception(f"技能分析失败: {e}")
            return self._create_error_result(
                request_id=request_id,
                error_code="ANALYSIS_FAILED",
                error_message=f"技能分析过程中发生错误: {str(e)}",
            )

    def submit_performance_metrics(self, metrics: List[PerformanceMetric]) -> OpenSpaceResult:
        """
        提交性能指标

        Args:
            metrics: 性能指标列表

        Returns:
            OpenSpace 结果包装
        """
        request_id = str(uuid.uuid4())

        try:
            # 1. 验证指标
            validated_metrics = []
            validation_issues = []

            for metric in metrics:
                if not metric.metric_id or not metric.metric_type or not metric.values:
                    validation_issues.append(f"指标验证失败: {metric.metric_id}")
                    continue
                validated_metrics.append(metric)

            if validation_issues:
                return self._create_error_result(
                    request_id=request_id,
                    error_code="INVALID_METRICS",
                    error_message="性能指标验证失败",
                    error_details=validation_issues,
                )

            # 2. 存储指标（本地存储，不发送到云端）
            storage_result = self._store_metrics_locally(validated_metrics)

            # 3. 分析指标趋势（模拟）
            trend_analysis = self._analyze_metric_trends(validated_metrics)

            # 4. 构建成功响应
            return OpenSpaceResult(
                success=True,
                request_id=request_id,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                data={
                    "metrics_received": len(validated_metrics),
                    "storage_location": storage_result.get("path", "local"),
                    "trend_analysis": trend_analysis,
                    "cloud_sync_disabled": True,
                },
            )

        except Exception as e:
            logger.exception(f"性能指标提交失败: {e}")
            return self._create_error_result(
                request_id=request_id,
                error_code="METRICS_SUBMISSION_FAILED",
                error_message=f"性能指标提交过程中发生错误: {str(e)}",
            )

    def get_optimization_suggestions(self, skill_id: str, limit: int = 5) -> OpenSpaceResult:
        """
        获取指定技能的优化建议

        Args:
            skill_id: 技能ID
            limit: 返回建议数量限制

        Returns:
            OpenSpace 结果包装
        """
        request_id = str(uuid.uuid4())

        try:
            # 1. 从本地存储加载历史建议（模拟）
            suggestions = self._load_suggestions_from_storage(skill_id, limit)

            # 2. 构建响应
            return OpenSpaceResult(
                success=True,
                request_id=request_id,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                data={
                    "skill_id": skill_id,
                    "suggestions": [asdict(s) for s in suggestions],
                    "total_count": len(suggestions),
                    "limit": limit,
                    "source": "local_storage",
                },
            )

        except Exception as e:
            logger.exception(f"获取优化建议失败: {e}")
            return self._create_error_result(
                request_id=request_id,
                error_code="SUGGESTIONS_FETCH_FAILED",
                error_message=f"获取优化建议过程中发生错误: {str(e)}",
            )

    # ==================== 私有方法 ====================

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "version": "1.0",
            "local_first_policy": {
                "enforced_settings": {
                    "cloud_sync_disabled": True,
                    "external_write_disabled": True,
                    "local_only": True,
                }
            },
            "sandbox_requirements": {"default_sandbox": "local_sandbox"},
            "adapter_runtime": {"default_mode": "local_only"},
        }

    def _validate_skill_input(self, skill_input: SkillInput) -> Dict[str, Any]:
        """验证技能输入"""
        issues = []

        # 检查必需字段
        if not skill_input.skill_id:
            issues.append("skill_id 不能为空")

        if not skill_input.skill_definition:
            issues.append("skill_definition 不能为空")

        if not skill_input.execution_context:
            issues.append("execution_context 不能为空")

        # 检查执行上下文中的风险等级
        risk_level = skill_input.execution_context.get("risk_level")
        if risk_level not in ["low", "medium", "high"]:
            issues.append(f"无效的风险等级: {risk_level}")

        return {"valid": len(issues) == 0, "issues": issues}

    def _check_sandbox_requirements(self) -> Tuple[bool, List[str]]:
        """检查沙箱要求"""
        issues = []

        # 检查本地沙箱是否可用
        try:
            # 简单检查：能否创建临时目录和执行基本命令
            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = os.path.join(tmpdir, "test.txt")
                with open(test_file, "w") as f:
                    f.write("sandbox test")

                # 检查能否执行命令
                result = subprocess.run(
                    ["echo", "sandbox check"], capture_output=True, text=True, timeout=5
                )

                if result.returncode != 0:
                    issues.append("沙箱命令执行失败")

        except Exception as e:
            issues.append(f"沙箱检查失败: {e}")

        return len(issues) == 0, issues

    def _generate_optimization_suggestions(
        self, skill_input: SkillInput
    ) -> List[OptimizationSuggestion]:
        """生成优化建议（模拟）"""
        suggestions = []

        # 基于技能定义生成示例建议
        skill_def = skill_input.skill_definition

        # 建议1：代码优化
        if skill_def.get("executable", False):
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    skill_id=skill_input.skill_id,
                    suggestion_type=SuggestionType.CODE_OPTIMIZATION.value,
                    changes=[
                        {
                            "component": "execution_logic",
                            "current_value": "单线程执行",
                            "suggested_value": "异步并发处理",
                            "rationale": "提高执行效率，减少等待时间",
                            "expected_impact": {"execution_time_reduction": "30-50%"},
                        }
                    ],
                    confidence_score=0.75,
                    estimated_effort="medium",
                    validation_requirements=["sandbox_test", "performance_benchmark"],
                )
            )

        # 建议2：参数调优
        if skill_def.get("arguments_schema"):
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    skill_id=skill_input.skill_id,
                    suggestion_type=SuggestionType.PARAMETER_TUNING.value,
                    changes=[
                        {
                            "component": "timeout_parameter",
                            "current_value": "30秒",
                            "suggested_value": "45秒",
                            "rationale": "当前超时设置可能导致长任务失败",
                            "expected_impact": {"success_rate_increase": "15%"},
                        }
                    ],
                    confidence_score=0.65,
                    estimated_effort="low",
                    validation_requirements=["sandbox_test"],
                )
            )

        # 限制建议数量
        return suggestions[:3]

    def _estimate_skill_complexity(self, skill_input: SkillInput) -> str:
        """评估技能复杂度"""
        deps_count = len(skill_input.skill_definition.get("dependencies", []))
        args_count = len(skill_input.skill_definition.get("arguments_schema", []))

        total = deps_count + args_count
        if total > 10:
            return "high"
        elif total > 5:
            return "medium"
        else:
            return "low"

    def _estimate_optimization_potential(self, skill_input: SkillInput) -> str:
        """评估优化潜力"""
        # 基于技能状态和性能基线评估
        status = skill_input.skill_definition.get("status", "unknown")
        if status == "executable_now":
            return "high"
        elif status == "gated":
            return "medium"
        else:
            return "low"

    def _store_metrics_locally(self, metrics: List[PerformanceMetric]) -> Dict[str, Any]:
        """本地存储指标"""
        storage_dir = os.path.join(project_root, "mini-agent", "logs", "openspace_metrics")
        os.makedirs(storage_dir, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"metrics_{timestamp}.json"
        filepath = os.path.join(storage_dir, filename)

        try:
            data = {
                "timestamp": timestamp,
                "metrics": [asdict(m) for m in metrics],
                "count": len(metrics),
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"性能指标已存储到: {filepath}")
            return {"success": True, "path": filepath, "count": len(metrics)}

        except Exception as e:
            logger.error(f"指标存储失败: {e}")
            return {"success": False, "error": str(e)}

    def _analyze_metric_trends(self, metrics: List[PerformanceMetric]) -> Dict[str, Any]:
        """分析指标趋势（模拟）"""
        if not metrics:
            return {"status": "no_metrics", "trend": "stable"}

        # 简单趋势分析
        metric_types = {}
        for metric in metrics:
            m_type = metric.metric_type
            if m_type not in metric_types:
                metric_types[m_type] = []
            metric_types[m_type].append(metric)

        trends = {}
        for m_type, m_list in metric_types.items():
            if len(m_list) >= 2:
                trends[m_type] = "analyzing"
            else:
                trends[m_type] = "insufficient_data"

        return {
            "status": "analyzed",
            "trends": trends,
            "metric_types_count": len(metric_types),
            "total_metrics": len(metrics),
        }

    def _load_suggestions_from_storage(
        self, skill_id: str, limit: int
    ) -> List[OptimizationSuggestion]:
        """从存储加载建议（模拟）"""
        # 这里模拟返回一些示例建议
        suggestions = []

        # 示例建议1
        suggestions.append(
            OptimizationSuggestion(
                suggestion_id=str(uuid.uuid4()),
                skill_id=skill_id,
                suggestion_type=SuggestionType.CODE_OPTIMIZATION.value,
                changes=[
                    {
                        "component": "error_handling",
                        "current_value": "基本异常捕获",
                        "suggested_value": "结构化错误处理和重试机制",
                        "rationale": "提高系统健壮性和用户体验",
                        "expected_impact": {"error_rate_reduction": "40%"},
                    }
                ],
                confidence_score=0.8,
                estimated_effort="low",
                validation_requirements=["sandbox_test"],
            )
        )

        # 示例建议2
        suggestions.append(
            OptimizationSuggestion(
                suggestion_id=str(uuid.uuid4()),
                skill_id=skill_id,
                suggestion_type=SuggestionType.DEPENDENCY_UPDATE.value,
                changes=[
                    {
                        "component": "python_dependencies",
                        "current_value": "requests==2.25.1",
                        "suggested_value": "requests==2.31.0",
                        "rationale": "更新到最新版本以修复安全漏洞",
                        "expected_impact": {"security_improvement": "high"},
                    }
                ],
                confidence_score=0.9,
                estimated_effort="low",
                validation_requirements=["security_review"],
            )
        )

        return suggestions[:limit]

    def check_evolution_permission(
        self,
        skill_input: SkillInput,
        available_metrics: List[PerformanceMetric],
    ) -> Tuple[bool, OpenSpaceResult]:
        """
        检查是否允许进行进化优化

        Args:
            skill_input: 技能输入
            available_metrics: 可用性能指标

        Returns:
            (是否允许, 错误结果（如果不允许）)
        """
        # 创建进化假设示例
        hypothesis = EvolutionHypothesis(
            hypothesis_id=str(uuid.uuid4()),
            skill_id=skill_input.skill_id,
            description="自动性能优化",
            expected_impact={"execution_time_reduction": "30%"},
        )
        hypothesis.add_metric_requirement("execution_time")
        hypothesis.add_metric_requirement("success_rate")

        # 检查进化约束
        valid, issues = self.constraint_validator.check_evolution_constraints(
            hypothesis, available_metrics
        )

        if not valid:
            # 记录约束命中监控证据
            try:
                self._record_monitoring_evidence(
                    evidence_type="constraint_hit",
                    skill_id=skill_input.skill_id,
                    data={
                        "hypothesis_id": hypothesis.hypothesis_id,
                        "issues": issues,
                        "available_metrics_count": len(available_metrics),
                        "constraint_type": "evolution_constraints",
                    },
                    requires_human_confirmation=True,  # 约束命中需要人工确认
                    human_intervention_details={
                        "reason": "进化约束验证失败",
                        "issues": issues,
                        "suggested_action": "检查性能指标或调整进化假设",
                    },
                    review_status=ReviewStatus.PENDING_REVIEW.value,
                )
            except Exception as e:
                logger.warning(f"记录约束命中证据失败: {e}")

            error_result = self.constraint_validator.enforce_fail_closed(issues)
            return False, error_result

        return True, OpenSpaceResult(
            success=True,
            request_id=str(uuid.uuid4()),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            data={"message": "进化优化允许", "hypothesis_id": hypothesis.hypothesis_id},
        )

    def _record_monitoring_evidence(
        self,
        evidence_type: str,
        skill_id: str,
        data: Dict[str, Any],
        requires_human_confirmation: bool = False,
        human_intervention_details: Optional[Dict[str, Any]] = None,
        review_status: str = ReviewStatus.PENDING_REVIEW.value,
    ) -> MonitoringEvidence:
        """记录监控证据"""
        evidence_id = f"evd_{uuid.uuid4().hex[:12]}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        evidence = MonitoringEvidence(
            evidence_id=evidence_id,
            timestamp=timestamp,
            evidence_type=evidence_type,
            skill_id=skill_id,
            data=data,
            review_status=review_status,
            requires_human_confirmation=requires_human_confirmation,
            human_intervention_details=human_intervention_details,
        )

        # 本地存储证据（模拟）
        self._store_evidence_locally(evidence)

        # 通过事件总线发出监控事件（如果可用）
        if self.event_bus:
            try:
                event_payload = {
                    "evidence_id": evidence_id,
                    "evidence_type": evidence_type,
                    "skill_id": skill_id,
                    "requires_human_confirmation": requires_human_confirmation,
                    "review_status": review_status,
                }
                event_scope = {
                    "skill_id": skill_id,
                    "component": "openspace_adapter",
                    "evidence_id": evidence_id,
                }
                event_evidence = [asdict(evidence)]

                self.event_bus.emit(
                    event_type=EventType.REVIEW if EventType else "review",
                    scope=event_scope,
                    payload=event_payload,
                    metadata={
                        "hook_point": (
                            HookPoint.ARTIFACT_WRITTEN.value if HookPoint else "artifact-written"
                        )
                    },
                    evidence=event_evidence,
                )
                logger.debug(f"监控证据已发送到事件总线: {evidence_id}")
            except Exception as e:
                logger.warning(f"发送监控证据到事件总线失败: {e}")

        logger.info(f"监控证据已记录: {evidence_type} for {skill_id}")
        return evidence

    def _store_evidence_locally(self, evidence: MonitoringEvidence) -> Dict[str, Any]:
        """本地存储证据"""
        storage_dir = os.path.join(project_root, "mini-agent", "logs", "openspace_evidence")
        os.makedirs(storage_dir, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"evidence_{evidence.evidence_type}_{timestamp}.json"
        filepath = os.path.join(storage_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(asdict(evidence), f, ensure_ascii=False, indent=2)
            return {"success": True, "path": filepath}
        except Exception as e:
            logger.error(f"证据存储失败: {e}")
            return {"success": False, "error": str(e)}

    def _update_review_status(
        self,
        evidence_id: str,
        review_status: str,
        reviewer: Optional[str] = None,
        comments: Optional[str] = None,
    ) -> bool:
        """更新审核状态（模拟）"""
        # 在实际实现中，这里会更新存储中的证据状态
        logger.info(
            f"审核状态更新: {evidence_id} -> {review_status} "
            f"(reviewer: {reviewer}, comments: {comments})"
        )

        # 发出审核状态变更事件
        if self.event_bus:
            try:
                self.event_bus.emit(
                    event_type=EventType.REVIEW if EventType else "review",
                    scope={
                        "evidence_id": evidence_id,
                        "component": "openspace_adapter",
                    },
                    payload={
                        "action": "review_status_update",
                        "evidence_id": evidence_id,
                        "old_status": "unknown",
                        "new_status": review_status,
                        "reviewer": reviewer,
                        "comments": comments,
                    },
                )
            except Exception as e:
                logger.warning(f"发送审核状态更新事件失败: {e}")

        return True

    def _create_error_result(
        self,
        request_id: str,
        error_code: str,
        error_message: str,
        error_details: Optional[List[str]] = None,
    ) -> OpenSpaceResult:
        """创建错误结果"""
        return OpenSpaceResult(
            success=False,
            request_id=request_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            error={
                "code": error_code,
                "message": error_message,
                "details": error_details or [],
            },
        )


# ==================== 进化循环骨架 ====================


class EvolutionHypothesis:
    """进化假设"""

    def __init__(
        self,
        hypothesis_id: str,
        skill_id: str,
        description: str,
        expected_impact: Dict[str, Any],
        confidence: float = 0.5,
    ):
        self.hypothesis_id = hypothesis_id
        self.skill_id = skill_id
        self.description = description
        self.expected_impact = expected_impact
        self.confidence = confidence
        self.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.status = "pending"  # pending, testing, validated, rejected
        self.metrics_requirements: List[str] = []

    def add_metric_requirement(self, metric_type: str):
        """添加指标要求"""
        self.metrics_requirements.append(metric_type)

    def validate_metrics(self, available_metrics: List[PerformanceMetric]) -> Tuple[bool, str]:
        """验证是否有足够指标支持此假设"""
        if not self.metrics_requirements:
            return True, "无指标要求"

        available_types = {m.metric_type for m in available_metrics}
        missing = set(self.metrics_requirements) - available_types
        if missing:
            return False, f"缺少指标类型: {missing}"
        return True, "指标满足要求"


class EvolutionModification:
    """进化修改"""

    def __init__(
        self,
        modification_id: str,
        hypothesis_id: str,
        skill_id: str,
        changes: List[Dict[str, Any]],
        implementation_plan: Dict[str, Any],
    ):
        self.modification_id = modification_id
        self.hypothesis_id = hypothesis_id
        self.skill_id = skill_id
        self.changes = changes
        self.implementation_plan = implementation_plan
        self.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.status = "pending"  # pending, implemented, rolled_back
        self.sandbox_required = True
        self.resource_limits: Dict[str, Any] = {}

    def set_resource_limits(self, cpu: str = "80%", memory: str = "2GB", disk: str = "10GB"):
        """设置资源限制"""
        self.resource_limits = {"cpu": cpu, "memory": memory, "disk": disk}


class EvolutionEvaluation:
    """进化评估"""

    def __init__(
        self,
        evaluation_id: str,
        modification_id: str,
        hypothesis_id: str,
        metrics_before: List[PerformanceMetric],
        metrics_after: List[PerformanceMetric],
    ):
        self.evaluation_id = evaluation_id
        self.modification_id = modification_id
        self.hypothesis_id = hypothesis_id
        self.metrics_before = metrics_before
        self.metrics_after = metrics_after
        self.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.impact_analysis: Dict[str, Any] = {}
        self.success: Optional[bool] = None
        self.conclusion: str = ""

    def analyze_impact(self) -> Dict[str, Any]:
        """分析修改影响"""
        if not self.metrics_before or not self.metrics_after:
            self.impact_analysis = {"status": "insufficient_data"}
            return self.impact_analysis

        # 简单对比：假设第一个指标类型
        before_values = [v["value"] for m in self.metrics_before for v in m.values if "value" in v]
        after_values = [v["value"] for m in self.metrics_after for v in m.values if "value" in v]

        if before_values and after_values:
            avg_before = sum(before_values) / len(before_values)
            avg_after = sum(after_values) / len(after_values)
            improvement = (avg_before - avg_after) / avg_before if avg_before != 0 else 0

            self.impact_analysis = {
                "avg_before": avg_before,
                "avg_after": avg_after,
                "improvement_percent": improvement * 100,
                "improvement_direction": (
                    "lower_is_better" if improvement > 0 else "higher_is_better"
                ),
            }

            # 简单成功判断：改进超过5%
            self.success = abs(improvement) > 0.05
            self.conclusion = (
                f"改进{'成功' if self.success else '未达阈值'} ({improvement * 100:.1f}%)"
            )
        else:
            self.impact_analysis = {"status": "no_numeric_values"}

        return self.impact_analysis


class EvolutionCycle:
    """进化循环管理器"""

    def __init__(self, adapter: OpenSpaceAdapter):
        self.adapter = adapter
        self.hypotheses: Dict[str, EvolutionHypothesis] = {}
        self.modifications: Dict[str, EvolutionModification] = {}
        self.evaluations: Dict[str, EvolutionEvaluation] = {}

    def create_hypothesis(
        self, skill_id: str, description: str, expected_impact: Dict[str, Any]
    ) -> EvolutionHypothesis:
        """创建进化假设"""
        hypothesis_id = str(uuid.uuid4())
        hypothesis = EvolutionHypothesis(hypothesis_id, skill_id, description, expected_impact)
        self.hypotheses[hypothesis_id] = hypothesis
        return hypothesis

    def propose_modification(
        self, hypothesis_id: str, skill_id: str, changes: List[Dict[str, Any]]
    ) -> EvolutionModification:
        """提出修改方案"""
        if hypothesis_id not in self.hypotheses:
            raise ValueError(f"假设不存在: {hypothesis_id}")

        modification_id = str(uuid.uuid4())
        implementation_plan = {
            "steps": ["validate_changes", "apply_in_sandbox", "collect_metrics"],
            "estimated_duration": "1h",
            "rollback_strategy": "auto_revert",
        }

        modification = EvolutionModification(
            modification_id, hypothesis_id, skill_id, changes, implementation_plan
        )
        self.modifications[modification_id] = modification
        return modification

    def evaluate_modification(
        self,
        modification_id: str,
        metrics_before: List[PerformanceMetric],
        metrics_after: List[PerformanceMetric],
    ) -> EvolutionEvaluation:
        """评估修改效果"""
        if modification_id not in self.modifications:
            raise ValueError(f"修改不存在: {modification_id}")

        modification = self.modifications[modification_id]
        evaluation_id = str(uuid.uuid4())

        evaluation = EvolutionEvaluation(
            evaluation_id,
            modification_id,
            modification.hypothesis_id,
            metrics_before,
            metrics_after,
        )
        evaluation.analyze_impact()

        # 记录评估结果监控证据
        try:
            skill_id = modification.skill_id
            self.adapter._record_monitoring_evidence(
                evidence_type="evaluation_result",
                skill_id=skill_id,
                data={
                    "evaluation_id": evaluation_id,
                    "modification_id": modification_id,
                    "hypothesis_id": modification.hypothesis_id,
                    "success": evaluation.success,
                    "impact_analysis": evaluation.impact_analysis,
                    "conclusion": evaluation.conclusion,
                    "metrics_before_count": len(metrics_before),
                    "metrics_after_count": len(metrics_after),
                },
                requires_human_confirmation=evaluation.success is False,  # 如果失败需要人工确认
                human_intervention_details=(
                    {
                        "success": evaluation.success,
                        "conclusion": evaluation.conclusion,
                        "action_required": (
                            "review_failed_modification" if evaluation.success is False else None
                        ),
                    }
                    if evaluation.success is False
                    else None
                ),
                review_status=(
                    ReviewStatus.PENDING_REVIEW.value
                    if evaluation.success is False
                    else ReviewStatus.APPROVED.value
                ),
            )
        except Exception as e:
            logger.warning(f"记录评估结果证据失败: {e}")

        self.evaluations[evaluation_id] = evaluation

        # 更新假设状态
        hypothesis = self.hypotheses.get(modification.hypothesis_id)
        if hypothesis and evaluation.success is not None:
            hypothesis.status = "validated" if evaluation.success else "rejected"

        return evaluation

    def validate_metrics_for_hypothesis(
        self, hypothesis_id: str, available_metrics: List[PerformanceMetric]
    ) -> Tuple[bool, str]:
        """验证假设的指标要求"""
        if hypothesis_id not in self.hypotheses:
            return False, f"假设不存在: {hypothesis_id}"

        hypothesis = self.hypotheses[hypothesis_id]
        return hypothesis.validate_metrics(available_metrics)


# ==================== 安全沙箱约束验证器 ====================


class SandboxConstraintValidator:
    """安全沙箱约束验证器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sandbox_config = config.get("sandbox_requirements", {})
        self.runtime_limits = config.get("adapter_runtime", {}).get("runtime_limits", {})

    def validate_resource_limits(self, requested_limits: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证资源限制是否在允许范围内"""
        issues = []

        # 获取配置中的限制
        default_sandbox = self.sandbox_config.get("sandbox_types", {}).get(
            self.sandbox_config.get("default_sandbox", "local_sandbox"), {}
        )
        config_limits = default_sandbox.get("resource_limits", {})

        # 检查CPU
        if "cpu" in requested_limits:
            requested_cpu = requested_limits["cpu"]
            config_cpu = config_limits.get("cpu_quota", "100%")
            # 简化验证：确保不超过配置
            if self._parse_cpu_percentage(requested_cpu) > self._parse_cpu_percentage(config_cpu):
                issues.append(f"CPU请求超过限制: {requested_cpu} > {config_cpu}")

        # 检查内存
        if "memory" in requested_limits:
            requested_mem = self._parse_memory(requested_limits["memory"])
            config_mem = self._parse_memory(config_limits.get("memory_limit", "2GB"))
            if requested_mem > config_mem:
                issues.append(
                    f"内存请求超过限制: {requested_limits['memory']} > {config_limits.get('memory_limit')}"
                )

        # 检查磁盘
        if "disk" in requested_limits:
            requested_disk = self._parse_memory(requested_limits["disk"])
            config_disk = self._parse_memory(config_limits.get("disk_quota", "10GB"))
            if requested_disk > config_disk:
                issues.append(
                    f"磁盘请求超过限制: {requested_limits['disk']} > {config_limits.get('disk_quota')}"
                )

        return len(issues) == 0, issues

    def validate_write_paths(self, requested_paths: List[str]) -> Tuple[bool, List[str]]:
        """验证写入路径是否在允许范围内"""
        issues = []
        allowed_writes = (
            self.config.get("local_first_policy", {})
            .get("external_write_disabled_detail", {})
            .get("allowed_local_writes", [])
        )

        # 简单路径检查：确保路径在项目范围内
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for path in requested_paths:
            abs_path = os.path.abspath(path)
            if not abs_path.startswith(project_root):
                issues.append(f"路径超出项目范围: {path}")

        return len(issues) == 0, issues

    def validate_external_access(self, requested_hosts: List[str]) -> Tuple[bool, List[str]]:
        """验证外部访问是否被允许"""
        issues = []
        allowed_hosts = (
            self.sandbox_config.get("sandbox_types", {})
            .get(self.sandbox_config.get("default_sandbox", "local_sandbox"), {})
            .get("allowed_hosts", ["127.0.0.1", "localhost"])
        )

        for host in requested_hosts:
            if host not in allowed_hosts and not any(
                host.startswith(prefix) for prefix in ["127.", "localhost", "::1"]
            ):
                issues.append(f"外部访问被禁止: {host}")

        return len(issues) == 0, issues

    def check_evolution_constraints(
        self,
        hypothesis: EvolutionHypothesis,
        available_metrics: List[PerformanceMetric],
    ) -> Tuple[bool, List[str]]:
        """检查进化约束：必须有足够指标"""
        issues = []

        # 约束1: 必须有性能指标输入
        if not available_metrics:
            issues.append("无性能指标输入，禁止进化优化")
            return False, issues

        # 约束2: 指标必须满足假设要求
        valid, reason = hypothesis.validate_metrics(available_metrics)
        if not valid:
            issues.append(f"指标不满足假设要求: {reason}")

        # 约束3: 指标必须足够新鲜（最近24小时内）
        # 延迟导入以避免循环依赖
        try:
            from .performance_metric_collector import PerformanceMetricCollector

            collector = PerformanceMetricCollector()
            summary = collector.get_metric_summary(available_metrics)
            recent_count = summary.get("recent_metrics_count", 0)
            if recent_count < 3:
                issues.append(f"最近24小时内的指标不足: {recent_count} < 3")
        except ImportError:
            # 如果采集器不可用，记录警告但继续
            logger.warning("PerformanceMetricCollector 不可用，跳过指标新鲜度检查")
            # 使用简单检查：至少需要3个指标
            if len(available_metrics) < 3:
                issues.append(f"指标数量不足: {len(available_metrics)} < 3")

        return len(issues) == 0, issues

    def enforce_fail_closed(self, issues: List[str]) -> OpenSpaceResult:
        """执行故障关闭：返回错误结果"""
        return OpenSpaceResult(
            success=False,
            request_id=str(uuid.uuid4()),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            error={
                "code": "SANDBOX_CONSTRAINT_VIOLATION",
                "message": "安全沙箱约束验证失败",
                "details": issues,
            },
        )

    # 辅助方法
    def _parse_cpu_percentage(self, cpu_str: str) -> float:
        """解析CPU百分比字符串"""
        if cpu_str.endswith("%"):
            return float(cpu_str[:-1]) / 100.0
        return float(cpu_str)

    def _parse_memory(self, memory_str: str) -> int:
        """解析内存字符串为字节数（简化）"""
        if memory_str.endswith("GB"):
            return int(float(memory_str[:-2]) * 1024 * 1024 * 1024)
        elif memory_str.endswith("MB"):
            return int(float(memory_str[:-2]) * 1024 * 1024)
        elif memory_str.endswith("KB"):
            return int(float(memory_str[:-2]) * 1024)
        else:
            return int(float(memory_str))


# ==================== 全局适配器实例 ====================

_adapter_instance: Optional[OpenSpaceAdapter] = None


def get_adapter() -> OpenSpaceAdapter:
    """获取全局适配器实例"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = OpenSpaceAdapter()
    return _adapter_instance


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=== OpenSpace Adapter 测试 ===")

    # 1. 初始化适配器
    adapter = OpenSpaceAdapter()
    print(f"1. 适配器初始化完成，模式: {adapter.mode.value}")

    # 2. 验证配置
    valid, issues = adapter.validate_config()
    print(f"2. 配置验证: {'通过' if valid else '失败'}")
    if issues:
        print(f"   问题: {issues}")

    # 3. 测试技能分析
    print("\n3. 测试技能分析:")
    skill_input = SkillInput(
        skill_id="test-skill-1",
        skill_definition={
            "name": "测试技能",
            "description": "一个测试技能",
            "category": "testing",
            "executable": True,
            "status": "executable_now",
            "dependencies": [],
            "arguments_schema": [],
            "gate_conditions": [],
        },
        execution_context={
            "task_id": "test-task-123",
            "risk_level": "medium",
            "sandbox_required": True,
        },
    )

    result = adapter.analyze_skill(skill_input)
    print(f"   成功: {result.success}")
    if result.success and result.data:
        print(f"   建议数量: {len(result.data.get('suggestions', []))}")
    else:
        print(f"   错误: {result.error}")

    # 4. 测试性能指标提交
    print("\n4. 测试性能指标提交:")
    metrics = [
        PerformanceMetric(
            metric_id="execution_time",
            metric_type="execution_time",
            values=[
                {"timestamp": "2026-04-03T10:00:00Z", "value": 1500},
                {"timestamp": "2026-04-03T10:05:00Z", "value": 1450},
            ],
        )
    ]

    result = adapter.submit_performance_metrics(metrics)
    print(f"   成功: {result.success}")
    if result.success and result.data:
        print(f"   接收指标数: {result.data.get('metrics_received', 0)}")

    # 5. 测试获取优化建议
    print("\n5. 测试获取优化建议:")
    result = adapter.get_optimization_suggestions("test-skill-1", limit=2)
    print(f"   成功: {result.success}")
    if result.success and result.data:
        print(f"   返回建议数: {len(result.data.get('suggestions', []))}")

    print("\n=== 测试完成 ===")
