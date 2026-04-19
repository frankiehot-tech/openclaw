#!/usr/bin/env python3
"""
Runtime Handoff - 复杂任务接管中间层

负责识别复杂任务并将其切换到 runtime agent 处理。
保持控制面（Bridge + Orchestrator）不变，仅新增 handoff 层。
"""

import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class HandoffRequest:
    """Handoff 请求"""

    task_id: str
    domain: str  # engineering, openhuman
    stage: str  # 内部执行阶段
    openhuman_stage: Optional[str] = None  # 原始 OpenHuman 阶段（如果 domain=openhuman）
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    workspace: Optional[str] = None  # 工作空间路径
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandoffResult:
    """Handoff 结果"""

    success: bool
    handoff_performed: bool  # 是否实际执行了 handoff
    message: str = ""
    runtime_result: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class RuntimeHandoff:
    """Runtime Handoff 管理器"""

    def __init__(self):
        self.complex_stage_patterns = self._load_complex_patterns()
        logger.info("RuntimeHandoff 初始化完成")

    def _load_complex_patterns(self) -> Dict[str, List[str]]:
        """加载复杂任务模式"""
        # 定义哪些阶段被认为是复杂任务，需要 handoff
        patterns = {
            # OpenHuman 阶段全部视为复杂（因为业务执行器未实现）
            "openhuman": [
                "distill",
                "skill_design",
                "dispatch",
                "acceptance",
                "settlement",
                "audit",
            ],
            # 工程阶段：build 阶段可能复杂，但暂时不 handoff
            "engineering": [],  # 暂时为空，保持简单
        }
        return patterns

    def should_handoff(self, request: HandoffRequest) -> Tuple[bool, str]:
        """
        判断是否应该 handoff

        Returns:
            (should_handoff, reason)
        """
        domain = request.domain
        stage = request.stage

        # 1. OpenHuman 领域任务：全部视为复杂
        if domain == "openhuman":
            openhuman_stage = request.openhuman_stage
            if openhuman_stage in self.complex_stage_patterns.get("openhuman", []):
                return (
                    True,
                    f"OpenHuman 阶段 '{openhuman_stage}' 需要 runtime agent 处理",
                )

        # 2. 工程领域：build 阶段可能复杂，但根据要求保持简单
        # 暂时不 handoff 工程任务

        # 3. 其他条件：可以基于描述长度、关键词等扩展
        # 例如：描述超过 200 字符的任务可能复杂
        if len(request.description) > 200:
            return True, "任务描述较长，可能复杂，需要 runtime agent 处理"

        # 默认不 handoff
        return False, "任务简单，无需 handoff"

    def perform_handoff(self, request: HandoffRequest) -> HandoffResult:
        """
        执行 handoff

        Args:
            request: Handoff 请求

        Returns:
            HandoffResult
        """
        start_time = time.time()

        try:
            # 1. 判断是否需要 handoff
            should_handoff, reason = self.should_handoff(request)

            if not should_handoff:
                return HandoffResult(
                    success=True,
                    handoff_performed=False,
                    message="任务未 handoff，由原流程处理",
                    task_id=request.task_id,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    details={"reason": reason},
                )

            logger.info(f"执行 handoff: 任务 {request.task_id}, 原因: {reason}")

            # 2. 调用 runtime agent（最小实现）
            runtime_result = self._call_runtime_agent(request)

            # 3. 返回结果
            return HandoffResult(
                success=True,
                handoff_performed=True,
                message=f"任务已 handoff 到 runtime agent: {reason}",
                runtime_result=runtime_result,
                task_id=request.task_id,
                execution_time_ms=(time.time() - start_time) * 1000,
                details={
                    "reason": reason,
                    "domain": request.domain,
                    "stage": request.stage,
                    "openhuman_stage": request.openhuman_stage,
                },
            )

        except Exception as e:
            logger.error(f"Handoff 执行失败: {e}", exc_info=True)
            return HandoffResult(
                success=False,
                handoff_performed=False,
                message="Handoff 执行失败",
                task_id=request.task_id,
                execution_time_ms=(time.time() - start_time) * 1000,
                error=str(e),
                details={"exception": type(e).__name__},
            )

    def _call_runtime_agent(self, request: HandoffRequest) -> Dict[str, Any]:
        """
        调用 runtime agent（最小实现）

        实际实现中，这里会调用真正的 runtime agent 系统。
        当前返回模拟结果，保持最小可运行闭环。
        """
        # 模拟 runtime agent 处理
        # 在实际系统中，这里会：
        # 1. 创建 runtime agent 实例
        # 2. 加载任务上下文
        # 3. 执行任务
        # 4. 返回结构化结果

        # 当前返回模拟结果
        runtime_result = {
            "runtime_agent": "athena_runtime_agent_v1",
            "task_id": request.task_id,
            "status": "executed",
            "output": {
                "summary": f"已处理 {request.domain} 任务: {request.description[:50]}...",
                "artifacts": [
                    {
                        "type": "analysis",
                        "path": f"/runtime/artifacts/{request.task_id}/analysis.json",
                    },
                    {
                        "type": "execution_log",
                        "path": f"/runtime/artifacts/{request.task_id}/log.txt",
                    },
                ],
                "metrics": {
                    "processing_time_ms": 1234,
                    "tokens_used": 456,
                    "complexity_score": 0.8,
                },
            },
            "handoff_metadata": {
                "handoff_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "handoff_reason": "OpenHuman 阶段需要业务执行器",
                "runtime_version": "1.0-minimal",
            },
        }

        logger.info(f"Runtime agent 模拟执行完成: {request.task_id}")
        return runtime_result

    def create_handoff_request_from_task(
        self,
        task_metadata: Dict[str, Any],
        context: Dict[str, Any],
        workspace: Optional[str] = None,
    ) -> HandoffRequest:
        """从任务元数据创建 Handoff 请求"""
        return HandoffRequest(
            task_id=task_metadata.get("task_id", "unknown"),
            domain=task_metadata.get("domain", "engineering"),
            stage=task_metadata.get("stage", "plan"),
            openhuman_stage=task_metadata.get("openhuman_stage"),
            description=task_metadata.get("description", ""),
            context=context,
            workspace=workspace,
            metadata=task_metadata,
        )


# 全局 handoff 实例
_handoff_instance: Optional[RuntimeHandoff] = None


def get_handoff() -> RuntimeHandoff:
    """获取全局 handoff 实例"""
    global _handoff_instance
    if _handoff_instance is None:
        _handoff_instance = RuntimeHandoff()
    return _handoff_instance


if __name__ == "__main__":
    # 测试代码
    print("=== Runtime Handoff 测试 ===")

    handoff = RuntimeHandoff()

    # 测试用例
    test_cases = [
        {
            "name": "OpenHuman distill 任务",
            "request": HandoffRequest(
                task_id="task_000001",
                domain="openhuman",
                stage="think",  # 内部映射阶段
                openhuman_stage="distill",
                description="把这个经验提炼成 Skill",
                context={"user": "test_user"},
                workspace="/tmp/test_workspace",
            ),
        },
        {
            "name": "OpenHuman dispatch 任务",
            "request": HandoffRequest(
                task_id="task_000002",
                domain="openhuman",
                stage="plan",
                openhuman_stage="dispatch",
                description="为 offline_survey 发布任务并筛人",
                context={"user": "test_user"},
            ),
        },
        {
            "name": "普通工程任务",
            "request": HandoffRequest(
                task_id="task_000003",
                domain="engineering",
                stage="plan",
                description="设计一个新技能模板",
                context={},
            ),
        },
        {
            "name": "长描述任务",
            "request": HandoffRequest(
                task_id="task_000004",
                domain="engineering",
                stage="plan",
                description="这是一个非常长的描述，超过200字符。" * 10,  # 约 300 字符
                context={},
            ),
        },
    ]

    for test in test_cases:
        print(f"\n{'=' * 60}")
        print(f"测试: {test['name']}")
        print(f"任务ID: {test['request'].task_id}")
        print(f"领域: {test['request'].domain}, 阶段: {test['request'].stage}")
        if test["request"].openhuman_stage:
            print(f"OpenHuman阶段: {test['request'].openhuman_stage}")

        # 判断是否需要 handoff
        should_handoff, reason = handoff.should_handoff(test["request"])
        print(f"是否需要 handoff: {should_handoff}")
        print(f"原因: {reason}")

        # 执行 handoff
        result = handoff.perform_handoff(test["request"])
        print(f"执行结果: 成功={result.success}, handoff执行={result.handoff_performed}")
        print(f"消息: {result.message}")
        if result.error:
            print(f"错误: {result.error}")

        if result.handoff_performed and result.runtime_result:
            print(f"Runtime 结果状态: {result.runtime_result.get('status', 'unknown')}")

    print(f"\n{'=' * 60}")
    print("✅ Runtime Handoff 测试完成")
