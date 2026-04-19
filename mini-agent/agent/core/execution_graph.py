#!/usr/bin/env python3
"""
Execution Graph 状态机与工具协议接线

建立最小 execution graph 结构、状态机协议和工具结果标准协议。
与现有 orchestrator、sub-agent bus 和 task 模型对齐。

设计原则：
- 最小可运行闭环优先
- 复用现有数据结构，不重复发明
- 明确状态流转与恢复入口
- 工具结果统一 schema
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
from typing import Any, Dict, List, Optional, Set, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ExecutionNodeType(Enum):
    """
    执行图节点类型
    映射到 understand / gather / execute / verify 四类节点或阶段
    """

    UNDERSTAND = "understand"  # 理解分析阶段
    GATHER = "gather"  # 收集信息阶段
    EXECUTE = "execute"  # 执行实现阶段
    VERIFY = "verify"  # 验证验收阶段

    @classmethod
    def from_stage(cls, stage: str) -> "ExecutionNodeType":
        """
        从现有阶段字符串映射到节点类型

        现有阶段: think, plan, build, review, qa, browse
        映射关系:
        - think -> UNDERSTAND
        - plan -> UNDERSTAND (规划也是理解)
        - build -> EXECUTE
        - review -> VERIFY
        - qa -> VERIFY
        - browse -> GATHER
        """
        mapping = {
            "think": cls.UNDERSTAND,
            "plan": cls.UNDERSTAND,
            "build": cls.EXECUTE,
            "review": cls.VERIFY,
            "qa": cls.VERIFY,
            "browse": cls.GATHER,
        }
        return mapping.get(stage, cls.EXECUTE)


class ExecutionState(Enum):
    """
    执行状态机关键状态
    至少定义 pending / running / verifying / completed / failed
    """

    PENDING = "pending"  # 待处理
    READY = "ready"  # 就绪（依赖满足）
    RUNNING = "running"  # 执行中
    VERIFYING = "verifying"  # 验证中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 取消
    PAUSED = "paused"  # 暂停（可恢复）

    @classmethod
    def final_states(cls) -> Set["ExecutionState"]:
        """最终状态集合"""
        return {cls.COMPLETED, cls.FAILED, cls.CANCELLED}

    @classmethod
    def is_final(cls, state: "ExecutionState") -> bool:
        """检查是否为最终状态"""
        return state in cls.final_states()


@dataclass
class ToolResultProtocol:
    """
    工具结果标准协议
    统一工具调用返回的结构，包含 status / data / metadata / error_context
    """

    status: str  # success, error, partial, cancelled
    data: Optional[Dict[str, Any]] = None  # 主要结果数据
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    error_context: Optional[Dict[str, Any]] = None  # 错误上下文（如果有）
    execution_time_ms: float = 0.0  # 执行时间（毫秒）
    tool_name: Optional[str] = None  # 工具名称
    tool_version: Optional[str] = None  # 工具版本

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "status": self.status,
            "data": self.data,
            "metadata": self.metadata,
            "execution_time_ms": self.execution_time_ms,
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
        }
        if self.error_context:
            result["error_context"] = self.error_context
        return result

    @classmethod
    def success(
        cls,
        data: Dict[str, Any],
        tool_name: str,
        execution_time_ms: float = 0.0,
        **metadata,
    ) -> "ToolResultProtocol":
        """创建成功结果"""
        return cls(
            status="success",
            data=data,
            metadata=metadata,
            execution_time_ms=execution_time_ms,
            tool_name=tool_name,
        )

    @classmethod
    def error(
        cls,
        error_message: str,
        error_type: str = "tool_error",
        tool_name: str = "unknown",
        execution_time_ms: float = 0.0,
        **error_context,
    ) -> "ToolResultProtocol":
        """创建错误结果"""
        return cls(
            status="error",
            metadata={},
            error_context={
                "error_message": error_message,
                "error_type": error_type,
                **error_context,
            },
            execution_time_ms=execution_time_ms,
            tool_name=tool_name,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolResultProtocol":
        """从字典创建"""
        return cls(
            status=data.get("status", "unknown"),
            data=data.get("data"),
            metadata=data.get("metadata", {}),
            error_context=data.get("error_context"),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            tool_name=data.get("tool_name"),
            tool_version=data.get("tool_version"),
        )


@dataclass
class ExecutionNode:
    """
    执行图节点
    对应一个任务或阶段，包含状态、输入、输出、依赖关系
    """

    node_id: str
    node_type: ExecutionNodeType
    state: ExecutionState = ExecutionState.PENDING
    stage: Optional[str] = None  # 原始阶段（如 think, build）
    domain: str = "engineering"  # engineering, openhuman

    # 任务信息
    task_id: Optional[str] = None  # 关联的任务ID（如果存在）
    description: str = ""
    expected_output: str = ""

    # 依赖关系
    dependencies: List[str] = field(default_factory=list)  # 依赖的节点ID
    dependants: List[str] = field(default_factory=list)  # 依赖此节点的节点ID

    # 输入输出
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    tool_results: List[ToolResultProtocol] = field(default_factory=list)

    # 元数据
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 状态机上下文
    state_history: List[Tuple[float, ExecutionState, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "state": self.state.value,
            "stage": self.stage,
            "domain": self.domain,
            "task_id": self.task_id,
            "description": self.description,
            "expected_output": self.expected_output,
            "dependencies": self.dependencies,
            "dependants": self.dependants,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "tool_results": [tr.to_dict() for tr in self.tool_results],
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
            "state_history": [
                (ts, state.value, reason) for ts, state, reason in self.state_history
            ],
        }

    def transition_state(
        self,
        new_state: ExecutionState,
        reason: str = "",
        timestamp: Optional[float] = None,
    ) -> bool:
        """
        状态转移

        返回是否成功转移
        """
        if timestamp is None:
            timestamp = time.time()

        # 记录状态历史
        self.state_history.append((timestamp, self.state, reason))

        # 更新状态和时间戳
        old_state = self.state
        self.state = new_state

        # 更新时间戳
        if new_state == ExecutionState.RUNNING and self.started_at is None:
            self.started_at = timestamp
        elif new_state in ExecutionState.final_states() and self.completed_at is None:
            self.completed_at = timestamp

        logger.debug(
            f"节点 {self.node_id} 状态转移: {old_state.value} -> {new_state.value}, 原因: {reason}"
        )
        return True

    def add_tool_result(self, result: ToolResultProtocol) -> None:
        """添加工具结果"""
        self.tool_results.append(result)

        # 根据工具结果更新节点状态（简单逻辑）
        if result.status == "error":
            self.transition_state(ExecutionState.FAILED, f"工具失败: {result.tool_name}")

    def is_ready(self) -> bool:
        """检查节点是否就绪（依赖满足且状态为 PENDING 或 READY）"""
        if self.state not in [ExecutionState.PENDING, ExecutionState.READY]:
            return False

        # 检查依赖是否都完成
        # 注意：依赖检查由 ExecutionGraph 管理
        return True

    def get_execution_time(self) -> float:
        """获取执行时间（秒）"""
        if self.started_at is None:
            return 0.0
        if self.completed_at is None:
            return time.time() - self.started_at
        return self.completed_at - self.started_at


@dataclass
class ExecutionGraph:
    """
    执行图
    管理节点、依赖关系和状态流转
    """

    graph_id: str
    nodes: Dict[str, ExecutionNode] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)  # (from, to)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: ExecutionNode) -> None:
        """添加节点"""
        if node.node_id in self.nodes:
            raise ValueError(f"节点已存在: {node.node_id}")
        self.nodes[node.node_id] = node

    def add_edge(self, from_node_id: str, to_node_id: str) -> None:
        """添加边（依赖关系）"""
        if from_node_id not in self.nodes:
            raise ValueError(f"源节点不存在: {from_node_id}")
        if to_node_id not in self.nodes:
            raise ValueError(f"目标节点不存在: {to_node_id}")

        self.edges.append((from_node_id, to_node_id))

        # 更新节点的依赖关系
        self.nodes[to_node_id].dependencies.append(from_node_id)
        self.nodes[from_node_id].dependants.append(to_node_id)

    def get_ready_nodes(self) -> List[ExecutionNode]:
        """获取就绪节点（依赖已满足且状态为 PENDING/READY）"""
        ready_nodes = []

        for node in self.nodes.values():
            if node.state in [ExecutionState.PENDING, ExecutionState.READY]:
                # 检查所有依赖是否完成
                dependencies_met = True
                for dep_id in node.dependencies:
                    dep_node = self.nodes.get(dep_id)
                    if not dep_node or dep_node.state != ExecutionState.COMPLETED:
                        dependencies_met = False
                        break

                if dependencies_met:
                    if node.state != ExecutionState.READY:
                        node.transition_state(ExecutionState.READY, "依赖已满足")
                    ready_nodes.append(node)

        return ready_nodes

    def transition_node_state(
        self, node_id: str, new_state: ExecutionState, reason: str = ""
    ) -> bool:
        """转移节点状态"""
        if node_id not in self.nodes:
            logger.warning(f"节点不存在: {node_id}")
            return False

        node = self.nodes[node_id]
        return node.transition_state(new_state, reason)

    def get_node_state(self, node_id: str) -> Optional[ExecutionState]:
        """获取节点状态"""
        node = self.nodes.get(node_id)
        return node.state if node else None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "graph_id": self.graph_id,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "edges": self.edges,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    def get_progress(self) -> Tuple[int, int, float]:
        """
        获取执行进度

        返回: (已完成节点数, 总节点数, 进度百分比)
        """
        total_nodes = len(self.nodes)
        if total_nodes == 0:
            return 0, 0, 0.0

        completed_nodes = sum(
            1 for node in self.nodes.values() if node.state == ExecutionState.COMPLETED
        )

        progress_percent = (completed_nodes / total_nodes) * 100
        return completed_nodes, total_nodes, progress_percent


class ExecutionGraphManager:
    """
    执行图管理器
    与现有 orchestrator 和 sub-agent bus 集成
    """

    def __init__(self):
        self.graphs: Dict[str, ExecutionGraph] = {}
        self.node_to_graph: Dict[str, str] = {}  # 节点ID -> 图ID

    def create_graph_from_task(
        self,
        task_id: str,
        stage: str,
        domain: str = "engineering",
        description: str = "",
        **task_metadata,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        从任务创建执行图

        根据阶段类型创建相应的执行图节点
        """
        try:
            # 生成图ID
            graph_id = f"graph_{uuid.uuid4().hex[:8]}"

            # 确定节点类型
            node_type = ExecutionNodeType.from_stage(stage)

            # 创建根节点
            root_node = ExecutionNode(
                node_id=f"node_{task_id}",
                node_type=node_type,
                stage=stage,
                domain=domain,
                task_id=task_id,
                description=description,
                expected_output=self._get_expected_output_for_stage(stage),
                metadata=task_metadata,
            )

            # 创建图
            graph = ExecutionGraph(
                graph_id=graph_id,
                metadata={
                    "source_task_id": task_id,
                    "domain": domain,
                    "stage": stage,
                    "created_from": "task",
                },
            )
            graph.add_node(root_node)

            # 注册
            self.graphs[graph_id] = graph
            self.node_to_graph[root_node.node_id] = graph_id

            logger.info(
                f"创建执行图: {graph_id}, 任务: {task_id}, 阶段: {stage}, 节点类型: {node_type.value}"
            )

            return True, graph_id, graph.to_dict()

        except Exception as e:
            logger.error(f"创建执行图失败: {e}", exc_info=True)
            return False, str(e), {}

    def _get_expected_output_for_stage(self, stage: str) -> str:
        """获取阶段的预期产出"""
        outputs = {
            "think": "分析报告",
            "plan": "设计方案",
            "build": "实现代码",
            "review": "审查意见",
            "qa": "质量报告",
            "browse": "浏览结果",
        }
        return outputs.get(stage, "未知产出")

    def get_graph(self, graph_id: str) -> Optional[ExecutionGraph]:
        """获取执行图"""
        return self.graphs.get(graph_id)

    def update_node_with_tool_result(
        self, node_id: str, tool_result: ToolResultProtocol, update_state: bool = True
    ) -> bool:
        """
        使用工具结果更新节点

        如果 update_state 为 True，会根据工具结果状态自动更新节点状态
        """
        graph_id = self.node_to_graph.get(node_id)
        if not graph_id:
            logger.warning(f"节点未找到: {node_id}")
            return False

        graph = self.graphs.get(graph_id)
        if not graph:
            logger.warning(f"图未找到: {graph_id}")
            return False

        node = graph.nodes.get(node_id)
        if not node:
            logger.warning(f"图中节点未找到: {node_id}")
            return False

        # 添加工具结果
        node.add_tool_result(tool_result)

        # 自动状态更新
        if update_state and tool_result.status == "success":
            # 如果节点正在运行且工具成功，标记为完成
            if node.state == ExecutionState.RUNNING:
                node.transition_state(ExecutionState.COMPLETED, "工具执行成功")
        elif update_state and tool_result.status == "error":
            # 工具失败，节点标记为失败
            node.transition_state(ExecutionState.FAILED, f"工具失败: {tool_result.tool_name}")

        logger.info(
            f"节点 {node_id} 更新工具结果: {tool_result.tool_name}, 状态: {tool_result.status}"
        )
        return True

    def get_ready_nodes_for_graph(self, graph_id: str) -> List[ExecutionNode]:
        """获取图中就绪节点"""
        graph = self.graphs.get(graph_id)
        if not graph:
            return []
        return graph.get_ready_nodes()

    def create_subgraph_for_delegation(
        self,
        delegation_id: str,
        task_inputs: List[Any],  # 期望是 TaskInput 对象或类似结构
        merge_strategy: str = "dependency_aware",
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        为委派任务创建子图

        将委派中的多个任务映射为执行图的子节点
        """
        try:
            # 生成子图ID
            subgraph_id = f"subgraph_{uuid.uuid4().hex[:8]}"

            # 创建子图
            subgraph = ExecutionGraph(
                graph_id=subgraph_id,
                metadata={
                    "delegation_id": delegation_id,
                    "merge_strategy": merge_strategy,
                    "task_count": len(task_inputs),
                    "created_from": "delegation",
                },
            )

            # 为每个任务输入创建节点
            node_mapping = {}
            for task_input in task_inputs:
                # 提取任务信息
                task_id = getattr(task_input, "task_id", f"task_{uuid.uuid4().hex[:8]}")
                role = getattr(task_input, "role", None)

                # 根据角色确定节点类型
                if role:
                    role_str = role.value if hasattr(role, "value") else str(role)
                    node_type = self._map_role_to_node_type(role_str)
                else:
                    role_str = "unknown"
                    node_type = ExecutionNodeType.EXECUTE

                # 创建节点
                node = ExecutionNode(
                    node_id=f"node_{task_id}",
                    node_type=node_type,
                    description=getattr(task_input, "description", f"委派任务: {task_id}"),
                    metadata={
                        "delegation_id": delegation_id,
                        "role": role_str if role else "unknown",
                        "original_task_id": task_id,
                    },
                )

                subgraph.add_node(node)
                node_mapping[task_id] = node.node_id

            # 添加依赖边
            for task_input in task_inputs:
                task_id = getattr(task_input, "task_id", "")
                if not task_id:
                    continue

                dependencies = getattr(task_input, "dependencies", [])
                from_node_id = node_mapping.get(task_id)
                if from_node_id:
                    for dep_id in dependencies:
                        to_node_id = node_mapping.get(dep_id)
                        if to_node_id:
                            subgraph.add_edge(to_node_id, from_node_id)  # 依赖方向: dep -> task

            # 注册
            self.graphs[subgraph_id] = subgraph
            for node_id in node_mapping.values():
                self.node_to_graph[node_id] = subgraph_id

            logger.info(
                f"创建委派子图: {subgraph_id}, 委派ID: {delegation_id}, 任务数: {len(task_inputs)}"
            )

            return True, subgraph_id, subgraph.to_dict()

        except Exception as e:
            logger.error(f"创建委派子图失败: {e}", exc_info=True)
            return False, str(e), {}

    def _map_role_to_node_type(self, role: str) -> ExecutionNodeType:
        """映射角色到节点类型"""
        mapping = {
            "researcher": ExecutionNodeType.GATHER,
            "planner": ExecutionNodeType.UNDERSTAND,
            "builder": ExecutionNodeType.EXECUTE,
            "build_worker": ExecutionNodeType.EXECUTE,
            "reviewer": ExecutionNodeType.VERIFY,
            "validator": ExecutionNodeType.VERIFY,
            "operator": ExecutionNodeType.EXECUTE,
        }
        return mapping.get(role.lower(), ExecutionNodeType.EXECUTE)


# 全局管理器实例
_graph_manager_instance: Optional[ExecutionGraphManager] = None


def get_execution_graph_manager() -> ExecutionGraphManager:
    """获取全局执行图管理器实例"""
    global _graph_manager_instance
    if _graph_manager_instance is None:
        _graph_manager_instance = ExecutionGraphManager()
    return _graph_manager_instance


if __name__ == "__main__":
    # 测试代码
    print("=== Execution Graph 测试 ===")

    # 创建管理器
    manager = ExecutionGraphManager()

    # 测试从任务创建图
    print("\n1. 测试从任务创建执行图:")
    success, graph_id, graph_data = manager.create_graph_from_task(
        task_id="test_task_001",
        stage="build",
        domain="engineering",
        description="测试构建任务",
    )
    print(f"   成功: {success}, 图ID: {graph_id}")
    print(f"   节点数: {len(graph_data.get('nodes', {}))}")

    # 测试工具结果协议
    print("\n2. 测试工具结果协议:")
    tool_result = ToolResultProtocol.success(
        data={"file_created": "test.py", "lines": 42},
        tool_name="write_file",
        execution_time_ms=150.5,
        file_size=1024,
    )
    print(f"   工具结果状态: {tool_result.status}")
    print(f"   数据: {tool_result.data}")
    print(f"   执行时间: {tool_result.execution_time_ms}ms")

    # 测试错误结果
    error_result = ToolResultProtocol.error(
        error_message="文件写入失败",
        error_type="io_error",
        tool_name="write_file",
        execution_time_ms=50.0,
        file_path="/tmp/test.py",
    )
    print(f"   错误结果状态: {error_result.status}")
    print(
        f"   错误信息: {error_result.error_context.get('error_message') if error_result.error_context else '无'}"
    )

    # 测试状态机
    print("\n3. 测试状态机:")
    node = ExecutionNode(
        node_id="test_node",
        node_type=ExecutionNodeType.EXECUTE,
        description="测试节点",
    )
    print(f"   初始状态: {node.state.value}")
    node.transition_state(ExecutionState.RUNNING, "开始执行")
    print(f"   运行状态: {node.state.value}")
    node.transition_state(ExecutionState.COMPLETED, "执行完成")
    print(f"   完成状态: {node.state.value}")
    print(f"   状态历史: {len(node.state_history)} 条记录")

    print("\n✅ Execution Graph 测试完成")
