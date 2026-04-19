#!/usr/bin/env python3
"""
Execution Integration - 执行图状态机与工具协议接线

将 execution graph、state machine 和 tool result protocol 集成到现有系统。
提供桥接函数，与 orchestrator、sub-agent bus 和 runtime handoff 对齐。

设计原则：
- 最小侵入性：不修改现有核心逻辑
- 协议优先：确保新协议可以被当前执行链消费
- 向后兼容：现有任务继续工作，可选启用新协议
"""

import json
import logging
import os
import sys
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple, Union

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入执行图协议
from .execution_graph import (
    ExecutionGraphManager,
    ExecutionNodeType,
    ExecutionState,
    ToolResultProtocol,
    get_execution_graph_manager,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ExecutionIntegration:
    """
    执行集成管理器

    负责将现有任务、工具调用和状态更新桥接到执行图协议
    """

    def __init__(self):
        self.graph_manager = get_execution_graph_manager()
        self.enabled = True  # 默认启用
        logger.info("Execution Integration 初始化完成")

    def register_task(
        self,
        task_id: str,
        stage: str,
        domain: str = "engineering",
        description: str = "",
        **metadata,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        注册任务到执行图系统

        返回: (成功, 消息, 图ID)
        """
        if not self.enabled:
            return False, "执行图集成未启用", None

        try:
            success, graph_id, graph_data = self.graph_manager.create_graph_from_task(
                task_id=task_id,
                stage=stage,
                domain=domain,
                description=description,
                **metadata,
            )

            if success:
                logger.info(f"任务注册到执行图: {task_id} -> {graph_id}")
                return True, "注册成功", graph_id
            else:
                logger.warning(f"任务注册失败: {task_id}, 错误: {graph_id}")
                return False, graph_id, None  # 注意: graph_id 实际上是错误消息

        except Exception as e:
            logger.error(f"任务注册异常: {task_id}, 错误: {e}", exc_info=True)
            return False, str(e), None

    def update_task_state(
        self,
        task_id: str,
        new_state: str,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        更新任务状态（桥接到执行图状态机）

        将自由字符串状态映射到正式状态机状态
        """
        if not self.enabled:
            return False

        # 查找任务关联的图
        # 简单实现：假设节点ID为 f"node_{task_id}"
        node_id = f"node_{task_id}"

        # 映射字符串状态到 ExecutionState
        state_mapping = {
            "pending": ExecutionState.PENDING,
            "created": ExecutionState.PENDING,
            "ready": ExecutionState.READY,
            "running": ExecutionState.RUNNING,
            "verifying": ExecutionState.VERIFYING,
            "completed": ExecutionState.COMPLETED,
            "accepted": ExecutionState.COMPLETED,
            "failed": ExecutionState.FAILED,
            "validation_failed": ExecutionState.FAILED,
            "cancelled": ExecutionState.CANCELLED,
            "interrupted": ExecutionState.CANCELLED,
            "rejected": ExecutionState.CANCELLED,
            "pending_hitl": ExecutionState.PAUSED,
            "needs_revision": ExecutionState.PAUSED,
        }

        execution_state = state_mapping.get(new_state.lower())
        if not execution_state:
            logger.warning(f"未知状态映射: {new_state}，使用 PENDING")
            execution_state = ExecutionState.PENDING

        # 更新节点状态
        try:
            # 通过图管理器更新节点状态
            # 首先需要找到包含该节点的图
            # 简化：假设节点ID到图的映射已存在
            graph_id = self.graph_manager.node_to_graph.get(node_id)
            if not graph_id:
                logger.debug(f"节点未注册到任何图: {node_id}")
                return False

            success = self.graph_manager.graphs[graph_id].transition_node_state(
                node_id, execution_state, reason
            )

            if success:
                logger.debug(
                    f"任务状态更新: {task_id} -> {execution_state.value} (原始: {new_state})"
                )

            return success

        except Exception as e:
            logger.error(f"更新任务状态失败: {task_id}, 错误: {e}", exc_info=True)
            return False

    def wrap_tool_result(
        self,
        tool_name: str,
        tool_output: Any,
        execution_time_ms: float = 0.0,
        error: Optional[str] = None,
        **metadata,
    ) -> ToolResultProtocol:
        """
        包装工具结果为标准协议

        将各种格式的工具输出统一为 ToolResultProtocol
        """
        if error or (isinstance(tool_output, dict) and "error" in tool_output):
            # 错误结果
            error_msg = error or tool_output.get("error", "工具执行失败")
            error_type = (
                tool_output.get("error_type", "tool_error")
                if isinstance(tool_output, dict)
                else "tool_error"
            )

            return ToolResultProtocol.error(
                error_message=error_msg,
                error_type=error_type,
                tool_name=tool_name,
                execution_time_ms=execution_time_ms,
                **metadata,
            )
        else:
            # 成功结果
            # 标准化输出格式
            if isinstance(tool_output, dict):
                data = tool_output
            elif tool_output is None:
                data = {"result": "success"}
            else:
                data = {"result": tool_output}

            return ToolResultProtocol.success(
                data=data,
                tool_name=tool_name,
                execution_time_ms=execution_time_ms,
                **metadata,
            )

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

        这是主要接线点：将工具调用结果注册到关联的任务节点
        """
        if not self.enabled:
            return False

        # 包装工具结果
        tool_result = self.wrap_tool_result(
            tool_name=tool_name,
            tool_output=tool_output,
            execution_time_ms=execution_time_ms,
            error=error,
            **metadata,
        )

        # 查找关联节点
        node_id = f"node_{task_id}"

        # 更新节点
        success = self.graph_manager.update_node_with_tool_result(
            node_id=node_id, tool_result=tool_result, update_state=True
        )

        if success:
            logger.debug(
                f"工具调用记录: 任务 {task_id}, 工具 {tool_name}, 状态 {tool_result.status}"
            )
        else:
            logger.warning(f"工具调用记录失败: 任务 {task_id}, 工具 {tool_name}")

        return success

    def get_task_execution_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务执行上下文（用于 handoff / orchestration）

        返回包含执行图状态、进度和工具历史的上下文
        """
        if not self.enabled:
            return None

        node_id = f"node_{task_id}"
        graph_id = self.graph_manager.node_to_graph.get(node_id)
        if not graph_id:
            return None

        graph = self.graph_manager.graphs.get(graph_id)
        if not graph:
            return None

        node = graph.nodes.get(node_id)
        if not node:
            return None

        # 构建执行上下文
        completed_nodes, total_nodes, progress = graph.get_progress()

        context = {
            "task_id": task_id,
            "node_id": node_id,
            "graph_id": graph_id,
            "state": node.state.value,
            "node_type": node.node_type.value,
            "stage": node.stage,
            "domain": node.domain,
            "progress": {
                "completed_nodes": completed_nodes,
                "total_nodes": total_nodes,
                "percentage": progress,
            },
            "execution_time": node.get_execution_time(),
            "tool_call_count": len(node.tool_results),
            "recent_tool_results": [
                {
                    "tool_name": tr.tool_name,
                    "status": tr.status,
                    "timestamp": tr.metadata.get("timestamp", 0),
                }
                for tr in node.tool_results[-5:]  # 最近5个
            ],
            "state_history": [
                {
                    "timestamp": ts,
                    "state": state.value,
                    "reason": reason,
                }
                for ts, state, reason in node.state_history[-10:]  # 最近10个状态变更
            ],
            "dependencies": {
                "upstream": node.dependencies,
                "downstream": node.dependants,
            },
        }

        return context

    def create_delegation_subgraph(
        self,
        delegation_id: str,
        task_inputs: List[Any],
        merge_strategy: str = "dependency_aware",
    ) -> Tuple[bool, str, Optional[str]]:
        """
        为委派任务创建执行子图

        与 sub-agent bus 集成
        """
        if not self.enabled:
            return False, "执行图集成未启用", None

        try:
            success, subgraph_id, subgraph_data = self.graph_manager.create_subgraph_for_delegation(
                delegation_id=delegation_id,
                task_inputs=task_inputs,
                merge_strategy=merge_strategy,
            )

            if success:
                logger.info(f"创建委派子图: {delegation_id} -> {subgraph_id}")
                return True, "子图创建成功", subgraph_id
            else:
                logger.warning(f"创建委派子图失败: {delegation_id}, 错误: {subgraph_id}")
                return False, subgraph_id, None

        except Exception as e:
            logger.error(f"创建委派子图异常: {delegation_id}, 错误: {e}", exc_info=True)
            return False, str(e), None

    def validate_handoff(
        self, task_id: str, handoff_type: str = "runtime"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        验证 handoff 是否应该执行（基于执行图状态）

        这是协议接线点：基于正式状态机决定是否 handoff
        """
        if not self.enabled:
            return True, "执行图集成未启用，默认允许", {}

        context = self.get_task_execution_context(task_id)
        if not context:
            return True, "任务未注册到执行图，默认允许", {}

        state = context["state"]

        # 基于状态机的 handoff 决策
        handoff_decision = {
            "should_handoff": False,
            "reason": "",
            "alternative_action": "",
            "state_machine_based": True,
        }

        # 状态机规则
        if state in ["failed", "cancelled"]:
            handoff_decision.update(
                {
                    "should_handoff": False,
                    "reason": f"任务状态为 {state}，不允许 handoff",
                    "alternative_action": "abort_or_retry",
                }
            )
        elif state == "completed":
            handoff_decision.update(
                {
                    "should_handoff": False,
                    "reason": "任务已完成，不需要 handoff",
                    "alternative_action": "proceed_to_next_stage",
                }
            )
        elif state == "verifying":
            handoff_decision.update(
                {
                    "should_handoff": handoff_type == "validation",
                    "reason": "任务正在验证中",
                    "alternative_action": "continue_verification",
                }
            )
        else:
            # 其他状态（pending, ready, running）允许 handoff
            handoff_decision.update(
                {
                    "should_handoff": True,
                    "reason": f"任务状态为 {state}，允许 handoff",
                    "alternative_action": "proceed_with_handoff",
                }
            )

        # 添加上下文信息
        handoff_decision["execution_context"] = context

        return (
            handoff_decision["should_handoff"],
            handoff_decision["reason"],
            handoff_decision,
        )


# 全局集成实例
_integration_instance: Optional[ExecutionIntegration] = None


def get_integration() -> ExecutionIntegration:
    """获取全局执行集成实例"""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = ExecutionIntegration()
    return _integration_instance


def enable_integration(enabled: bool = True) -> None:
    """启用或禁用执行图集成"""
    integration = get_integration()
    integration.enabled = enabled
    logger.info(f"执行图集成 {'启用' if enabled else '禁用'}")


# 便捷函数
def register_task_to_graph(
    task_id: str,
    stage: str,
    domain: str = "engineering",
    description: str = "",
    **metadata,
) -> Tuple[bool, str, Optional[str]]:
    """便捷函数：注册任务到执行图"""
    return get_integration().register_task(task_id, stage, domain, description, **metadata)


def record_tool_call_for_task(
    task_id: str,
    tool_name: str,
    tool_output: Any,
    execution_time_ms: float = 0.0,
    error: Optional[str] = None,
    **metadata,
) -> bool:
    """便捷函数：记录工具调用到任务"""
    return get_integration().record_tool_call(
        task_id, tool_name, tool_output, execution_time_ms, error, **metadata
    )


if __name__ == "__main__":
    # 测试代码
    print("=== Execution Integration 测试 ===")

    # 获取集成实例
    integration = ExecutionIntegration()

    # 测试任务注册
    print("\n1. 测试任务注册:")
    success, message, graph_id = integration.register_task(
        task_id="test_integration_001",
        stage="build",
        description="集成测试任务",
    )
    print(f"   成功: {success}, 消息: {message}, 图ID: {graph_id}")

    # 测试状态更新
    print("\n2. 测试状态更新:")
    success = integration.update_task_state(
        task_id="test_integration_001", new_state="running", reason="测试状态更新"
    )
    print(f"   状态更新成功: {success}")

    # 测试工具调用记录
    print("\n3. 测试工具调用记录:")
    success = integration.record_tool_call(
        task_id="test_integration_001",
        tool_name="write_file",
        tool_output={"file_created": "test.py", "lines": 100},
        execution_time_ms=200.5,
        author="integration_test",
    )
    print(f"   工具调用记录成功: {success}")

    # 测试执行上下文
    print("\n4. 测试执行上下文:")
    context = integration.get_task_execution_context("test_integration_001")
    if context:
        print(f"   任务状态: {context['state']}")
        print(f"   进度: {context['progress']['percentage']:.1f}%")
        print(f"   工具调用次数: {context['tool_call_count']}")

    # 测试 handoff 验证
    print("\n5. 测试 handoff 验证:")
    should_handoff, reason, decision = integration.validate_handoff(
        task_id="test_integration_001", handoff_type="runtime"
    )
    print(f"   Should handoff: {should_handoff}")
    print(f"   原因: {reason}")
    print(f"   决策详情: {decision.get('alternative_action')}")

    print("\n✅ Execution Integration 测试完成")
