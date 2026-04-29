#!/usr/bin/env python3
"""
运营自动化契约 - 最小运营自动化骨架

定义内容生成、发布、监控或报告的自动化入口，优先 dry-run / local-first / evidence-first。
提供与预算监控和告警集成的接口。

设计原则：
- 默认 dry-run 或可禁用，避免越界
- 本地优先，输出证据文件
- 与现有预算监控统一口径
- 提供后续 GitHub Actions / 社区机器人接线的正式入口
"""

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== 枚举定义 ====================


class AutomationAction(Enum):
    """自动化动作类型"""

    CONTENT_GENERATION = "content_generation"
    PUBLISH = "publish"
    MONITORING = "monitoring"
    REPORTING = "reporting"
    CUSTOM = "custom"


class AutomationStatus(Enum):
    """自动化执行状态"""

    PENDING = "pending"
    DRY_RUN = "dry_run"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AutomationSeverity(Enum):
    """自动化告警严重级别"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ==================== 数据类定义 ====================


@dataclass
class AutomationRequest:
    """自动化请求"""

    request_id: str
    action: AutomationAction
    payload: dict[str, Any]

    # 配置选项
    dry_run: bool = True
    require_budget_check: bool = True
    budget_check_threshold: float = 10.0  # 预算检查阈值（元）

    # 元数据
    description: str = ""
    created_by: str = "system"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["action"] = self.action.value
        return result


@dataclass
class AutomationResult:
    """自动化执行结果"""

    request_id: str
    status: AutomationStatus
    output: dict[str, Any]

    # 执行详情
    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    execution_time_ms: int = 0
    evidence_path: str | None = None  # 证据文件路径

    # 告警与错误
    alerts: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # 预算信息
    budget_checked: bool = False
    budget_check_result: dict[str, Any] | None = None
    actual_cost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result


@dataclass
class AutomationContract:
    """自动化契约 - 定义自动化执行的规则和边界"""

    # 契约标识
    contract_id: str
    name: str
    version: str = "1.0"

    # 允许的动作
    allowed_actions: list[AutomationAction] = field(default_factory=list)

    # 边界限制
    max_cost_per_action: float = 50.0
    max_actions_per_day: int = 10
    require_human_confirmation_above: float = 100.0

    # 证据要求
    require_evidence: bool = True
    evidence_dir: str = "workspace/automation_evidence"

    # 集成配置
    integrate_with_budget: bool = True
    integrate_with_alerts: bool = True

    # 状态
    enabled: bool = True
    last_executed: str | None = None
    execution_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["allowed_actions"] = [a.value for a in self.allowed_actions]
        return result


# ==================== 核心自动化引擎 ====================


class AutomationEngine:
    """最小自动化引擎"""

    def __init__(self, contract: AutomationContract | None = None):
        self.contract = contract or self._create_default_contract()
        self.requests: dict[str, AutomationRequest] = {}
        self.results: dict[str, AutomationResult] = {}

        # 确保证据目录存在
        self.evidence_dir = Path(self.contract.evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"自动化引擎初始化完成，契约: {self.contract.name}")

    def _create_default_contract(self) -> AutomationContract:
        """创建默认契约"""
        return AutomationContract(
            contract_id="default_automation_contract",
            name="默认运营自动化契约",
            allowed_actions=[
                AutomationAction.CONTENT_GENERATION,
                AutomationAction.PUBLISH,
                AutomationAction.MONITORING,
                AutomationAction.REPORTING,
            ],
            evidence_dir="workspace/automation_evidence",
        )

    def create_request(
        self,
        action: AutomationAction,
        payload: dict[str, Any],
        dry_run: bool = True,
        description: str = "",
        **kwargs,
    ) -> tuple[bool, str, AutomationRequest | None]:
        """创建自动化请求"""
        try:
            # 检查契约是否允许此动作
            if action not in self.contract.allowed_actions:
                return False, f"契约不允许此动作: {action.value}", None

            # 生成请求ID
            request_id = f"auto_req_{uuid.uuid4().hex[:12]}"

            # 创建请求对象
            request = AutomationRequest(
                request_id=request_id,
                action=action,
                payload=payload,
                dry_run=dry_run,
                description=description,
                **kwargs,
            )

            # 存储请求
            self.requests[request_id] = request

            logger.info(f"创建自动化请求: {request_id}, 动作: {action.value}, dry_run: {dry_run}")

            return True, request_id, request

        except Exception as e:
            logger.error(f"创建自动化请求失败: {e}")
            return False, str(e), None

    def _check_budget(self, request: AutomationRequest) -> dict[str, Any] | None:
        """检查预算（如果启用）"""
        if not request.require_budget_check:
            return None

        try:
            # 尝试导入预算引擎
            from mini_agent.agent.core.budget_engine import (
                BudgetCheckRequest,
                get_budget_engine,
            )

            engine = get_budget_engine()

            # 创建预算检查请求
            budget_request = BudgetCheckRequest(
                task_id=request.request_id,
                estimated_cost=request.budget_check_threshold,
                task_type=f"automation_{request.action.value}",
                description=request.description,
                metadata=request.metadata,
            )

            result = engine.check_budget(budget_request)
            return result.to_dict()

        except ImportError:
            logger.warning("预算引擎不可用，跳过预算检查")
            return None
        except Exception as e:
            logger.warning(f"预算检查失败: {e}")
            return None

    def _execute_content_generation(self, request: AutomationRequest) -> dict[str, Any]:
        """执行内容生成（dry-run）"""
        if request.dry_run:
            return {
                "dry_run": True,
                "action": "content_generation",
                "generated_content_preview": f"[DRY-RUN] 内容生成预览: {request.description}",
                "estimated_tokens": 500,
                "estimated_cost": 0.02,
            }
        else:
            # 实际内容生成逻辑（占位）
            return {
                "dry_run": False,
                "action": "content_generation",
                "status": "simulated_execution",
                "note": "真实内容生成需要实现具体逻辑",
            }

    def _execute_publish(self, request: AutomationRequest) -> dict[str, Any]:
        """执行发布（dry-run）"""
        if request.dry_run:
            return {
                "dry_run": True,
                "action": "publish",
                "platform": request.payload.get("platform", "unknown"),
                "content_preview": request.payload.get("content", "")[:100] + "...",
                "would_publish": True,
                "audience_estimate": request.payload.get("audience", "default"),
            }
        else:
            return {
                "dry_run": False,
                "action": "publish",
                "status": "simulated_execution",
                "note": "真实发布需要实现平台API集成",
            }

    def _execute_monitoring(self, request: AutomationRequest) -> dict[str, Any]:
        """执行监控（dry-run）"""
        if request.dry_run:
            return {
                "dry_run": True,
                "action": "monitoring",
                "metrics_checked": ["budget", "performance", "system_health"],
                "alerts_generated": 0,
                "check_timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "dry_run": False,
                "action": "monitoring",
                "status": "simulated_execution",
                "note": "真实监控需要实现指标收集和告警",
            }

    def _execute_reporting(self, request: AutomationRequest) -> dict[str, Any]:
        """执行报告（dry-run）"""
        if request.dry_run:
            return {
                "dry_run": True,
                "action": "reporting",
                "report_type": request.payload.get("report_type", "daily_summary"),
                "sections": ["budget", "operations", "alerts"],
                "would_generate_file": True,
                "estimated_pages": 3,
            }
        else:
            return {
                "dry_run": False,
                "action": "reporting",
                "status": "simulated_execution",
                "note": "真实报告需要实现模板和数据填充",
            }

    def _save_evidence(self, request: AutomationRequest, result: AutomationResult) -> str:
        """保存执行证据到文件"""
        evidence_data = {
            "request": request.to_dict(),
            "result": result.to_dict(),
            "contract": self.contract.to_dict(),
            "saved_at": datetime.now().isoformat(),
        }

        evidence_file = self.evidence_dir / f"evidence_{request.request_id}.json"

        try:
            with open(evidence_file, "w", encoding="utf-8") as f:
                json.dump(evidence_data, f, ensure_ascii=False, indent=2)

            logger.info(f"证据文件已保存: {evidence_file}")
            return str(evidence_file)

        except Exception as e:
            logger.warning(f"保存证据文件失败: {e}")
            return ""

    def execute_request(self, request_id: str) -> tuple[bool, str, AutomationResult | None]:
        """执行自动化请求"""
        if request_id not in self.requests:
            return False, f"请求不存在: {request_id}", None

        request = self.requests[request_id]
        start_time = datetime.now()

        logger.info(
            f"执行自动化请求: {request_id}, 动作: {request.action.value}, dry_run: {request.dry_run}"
        )

        # 1. 检查预算
        budget_result = None
        if request.require_budget_check and self.contract.integrate_with_budget:
            budget_result = self._check_budget(request)

        # 2. 执行动作
        try:
            if request.action == AutomationAction.CONTENT_GENERATION:
                output = self._execute_content_generation(request)
            elif request.action == AutomationAction.PUBLISH:
                output = self._execute_publish(request)
            elif request.action == AutomationAction.MONITORING:
                output = self._execute_monitoring(request)
            elif request.action == AutomationAction.REPORTING:
                output = self._execute_reporting(request)
            else:
                output = {"error": f"未知动作: {request.action}"}

            # 3. 计算执行时间
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 4. 确定状态
            status = AutomationStatus.DRY_RUN if request.dry_run else AutomationStatus.EXECUTED

            # 5. 创建结果
            result = AutomationResult(
                request_id=request_id,
                status=status,
                output=output,
                execution_time_ms=execution_time_ms,
                budget_checked=budget_result is not None,
                budget_check_result=budget_result,
                actual_cost=float(output.get("estimated_cost", 0.0)),
            )

            # 6. 保存证据
            if self.contract.require_evidence:
                evidence_path = self._save_evidence(request, result)
                result.evidence_path = evidence_path

            # 7. 更新契约状态
            self.contract.last_executed = datetime.now().isoformat()
            self.contract.execution_count += 1

            # 8. 存储结果
            self.results[request_id] = result

            logger.info(
                f"自动化请求执行完成: {request_id}, 状态: {result.status.value}, 耗时: {execution_time_ms}ms"
            )

            return True, "执行成功", result

        except Exception as e:
            logger.error(f"自动化请求执行失败: {e}", exc_info=True)

            # 创建失败结果
            result = AutomationResult(
                request_id=request_id,
                status=AutomationStatus.FAILED,
                output={"error": str(e)},
                errors=[str(e)],
                budget_checked=budget_result is not None,
                budget_check_result=budget_result,
            )

            self.results[request_id] = result
            return False, str(e), result

    def get_summary(self) -> dict[str, Any]:
        """获取运营自动化摘要"""
        return {
            "contract": self.contract.to_dict(),
            "statistics": {
                "total_requests": len(self.requests),
                "total_results": len(self.results),
                "by_status": {
                    status.value: len([r for r in self.results.values() if r.status == status])
                    for status in AutomationStatus
                },
                "by_action": {
                    action.value: len([r for r in self.requests.values() if r.action == action])
                    for action in AutomationAction
                },
            },
            "recent_requests": [request.to_dict() for request in list(self.requests.values())[-5:]],
            "recent_results": [result.to_dict() for result in list(self.results.values())[-5:]],
            "evidence_dir": str(self.evidence_dir),
            "engine_status": "active",
        }


# ==================== 全局实例 ====================

_automation_engine_instance: AutomationEngine | None = None


def get_automation_engine() -> AutomationEngine:
    """获取全局自动化引擎实例"""
    global _automation_engine_instance
    if _automation_engine_instance is None:
        _automation_engine_instance = AutomationEngine()
    return _automation_engine_instance


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=== 运营自动化契约测试 ===")

    # 创建引擎
    engine = AutomationEngine()

    print("\n1. 测试内容生成（dry-run）:")
    success, req_id, request = engine.create_request(
        action=AutomationAction.CONTENT_GENERATION,
        payload={"topic": "AI运营自动化", "length": "medium"},
        description="测试内容生成",
        dry_run=True,
    )

    if success and request:
        success_exec, msg, result = engine.execute_request(req_id)
        print(f"   请求ID: {req_id}")
        print(f"   执行成功: {success_exec}, 消息: {msg}")
        if result:
            print(f"   状态: {result.status.value}")
            print(f"   输出: {json.dumps(result.output, ensure_ascii=False, indent=2)[:200]}...")

    print("\n2. 测试发布（dry-run）:")
    success, req_id2, request2 = engine.create_request(
        action=AutomationAction.PUBLISH,
        payload={"platform": "twitter", "content": "测试推文内容"},
        description="测试社交媒体发布",
        dry_run=True,
    )

    if success and request2:
        success_exec, msg, result = engine.execute_request(req_id2)
        print(f"   请求ID: {req_id2}")
        print(f"   执行成功: {success_exec}, 消息: {msg}")

    print("\n3. 测试摘要生成:")
    summary = engine.get_summary()
    print(f"   契约: {summary['contract']['name']}")
    print(f"   总请求数: {summary['statistics']['total_requests']}")
    print(f"   总结果数: {summary['statistics']['total_results']}")

    print("\n=== 测试完成 ===")
