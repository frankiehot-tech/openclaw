#!/usr/bin/env python3
"""
Execution Graph 状态机与工具协议接线测试

满足任务验证要求：
1. 至少补一个 execution graph 或状态机解析测试
2. 至少补一个 tool result protocol 负路径测试
3. 至少补一个 handoff / orchestration smoke，验证新协议可以被当前执行链消费
"""

import os
import sys
import time
import unittest

# 添加项目根目录到路径
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.core.execution_graph import (
    ExecutionGraph,
    ExecutionGraphManager,
    ExecutionNode,
    ExecutionNodeType,
    ExecutionState,
    ToolResultProtocol,
    get_execution_graph_manager,
)
from agent.core.execution_integration import (
    ExecutionIntegration,
    get_integration,
)


class TestExecutionGraphProtocol(unittest.TestCase):
    """执行图协议测试"""

    def test_execution_node_type_mapping(self):
        """测试执行节点类型映射"""
        # 测试阶段到节点类型的映射
        self.assertEqual(ExecutionNodeType.from_stage("think"), ExecutionNodeType.UNDERSTAND)
        self.assertEqual(ExecutionNodeType.from_stage("plan"), ExecutionNodeType.UNDERSTAND)
        self.assertEqual(ExecutionNodeType.from_stage("build"), ExecutionNodeType.EXECUTE)
        self.assertEqual(ExecutionNodeType.from_stage("review"), ExecutionNodeType.VERIFY)
        self.assertEqual(ExecutionNodeType.from_stage("qa"), ExecutionNodeType.VERIFY)
        self.assertEqual(ExecutionNodeType.from_stage("browse"), ExecutionNodeType.GATHER)
        self.assertEqual(
            ExecutionNodeType.from_stage("unknown"),
            ExecutionNodeType.EXECUTE,  # 默认
        )

    def test_state_machine_final_states(self):
        """测试状态机最终状态"""
        # 检查最终状态
        final_states = ExecutionState.final_states()
        self.assertIn(ExecutionState.COMPLETED, final_states)
        self.assertIn(ExecutionState.FAILED, final_states)
        self.assertIn(ExecutionState.CANCELLED, final_states)
        self.assertNotIn(ExecutionState.PENDING, final_states)
        self.assertNotIn(ExecutionState.RUNNING, final_states)

        # 测试 is_final 方法
        self.assertTrue(ExecutionState.is_final(ExecutionState.COMPLETED))
        self.assertTrue(ExecutionState.is_final(ExecutionState.FAILED))
        self.assertFalse(ExecutionState.is_final(ExecutionState.PENDING))
        self.assertFalse(ExecutionState.is_final(ExecutionState.RUNNING))

    def test_state_transitions(self):
        """测试状态转移"""
        node = ExecutionNode(
            node_id="test_node",
            node_type=ExecutionNodeType.EXECUTE,
            description="测试节点",
        )

        # 初始状态应为 PENDING
        self.assertEqual(node.state, ExecutionState.PENDING)

        # 转移到 RUNNING
        success = node.transition_state(ExecutionState.RUNNING, "开始执行")
        self.assertTrue(success)
        self.assertEqual(node.state, ExecutionState.RUNNING)
        self.assertIsNotNone(node.started_at)

        # 转移到 COMPLETED
        success = node.transition_state(ExecutionState.COMPLETED, "执行完成")
        self.assertTrue(success)
        self.assertEqual(node.state, ExecutionState.COMPLETED)
        self.assertIsNotNone(node.completed_at)

        # 检查状态历史
        self.assertEqual(len(node.state_history), 2)
        self.assertEqual(node.state_history[0][1], ExecutionState.PENDING)
        self.assertEqual(node.state_history[1][1], ExecutionState.RUNNING)

    def test_tool_result_protocol_success(self):
        """测试工具结果协议 - 成功路径"""
        result = ToolResultProtocol.success(
            data={"file": "test.py", "lines": 100},
            tool_name="write_file",
            execution_time_ms=150.5,
            author="test",
            version="1.0",
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(result.tool_name, "write_file")
        self.assertEqual(result.execution_time_ms, 150.5)
        self.assertEqual(result.data["file"], "test.py")
        self.assertEqual(result.metadata.get("author"), "test")
        self.assertEqual(result.metadata.get("version"), "1.0")
        self.assertIsNone(result.error_context)

    def test_tool_result_protocol_error(self):
        """测试工具结果协议 - 负路径（错误）"""
        result = ToolResultProtocol.error(
            error_message="文件写入失败",
            error_type="io_error",
            tool_name="write_file",
            execution_time_ms=50.0,
            file_path="/tmp/test.py",
            retry_count=3,
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.tool_name, "write_file")
        self.assertEqual(result.execution_time_ms, 50.0)
        self.assertIsNotNone(result.error_context)
        self.assertEqual(result.error_context["error_message"], "文件写入失败")
        self.assertEqual(result.error_context["error_type"], "io_error")
        self.assertEqual(result.error_context["file_path"], "/tmp/test.py")
        self.assertEqual(result.error_context["retry_count"], 3)

    def test_execution_graph_manager(self):
        """测试执行图管理器"""
        manager = ExecutionGraphManager()

        # 创建图
        success, graph_id, graph_data = manager.create_graph_from_task(
            task_id="test_task",
            stage="build",
            description="测试任务",
        )

        self.assertTrue(success)
        self.assertIsNotNone(graph_id)
        self.assertIn("nodes", graph_data)
        self.assertEqual(len(graph_data["nodes"]), 1)

        # 获取图
        graph = manager.get_graph(graph_id)
        self.assertIsNotNone(graph)
        self.assertEqual(graph.graph_id, graph_id)

        # 获取就绪节点
        ready_nodes = manager.get_ready_nodes_for_graph(graph_id)
        self.assertEqual(len(ready_nodes), 1)

        # 更新工具结果
        tool_result = ToolResultProtocol.success(
            data={"result": "success"},
            tool_name="test_tool",
            execution_time_ms=100.0,
        )

        node_id = "node_test_task"
        success = manager.update_node_with_tool_result(node_id, tool_result)
        self.assertTrue(success)

        # 检查节点状态
        node = graph.nodes.get(node_id)
        self.assertIsNotNone(node)
        self.assertEqual(len(node.tool_results), 1)
        self.assertEqual(node.tool_results[0].tool_name, "test_tool")


class TestExecutionIntegration(unittest.TestCase):
    """执行集成测试"""

    def setUp(self):
        self.integration = ExecutionIntegration()

    def test_task_registration(self):
        """测试任务注册集成"""
        success, message, graph_id = self.integration.register_task(
            task_id="test_integration_task",
            stage="plan",
            domain="engineering",
            description="集成测试任务",
        )

        self.assertTrue(success)
        self.assertIsNotNone(graph_id)
        self.assertIn("注册成功", message)

    def test_state_update_integration(self):
        """测试状态更新集成"""
        # 先注册任务
        self.integration.register_task(
            task_id="test_state_task",
            stage="build",
            description="状态测试任务",
        )

        # 更新状态
        success = self.integration.update_task_state(
            task_id="test_state_task",
            new_state="running",
            reason="测试状态更新",
        )

        self.assertTrue(success)

    def test_tool_call_recording(self):
        """测试工具调用记录"""
        # 先注册任务
        self.integration.register_task(
            task_id="test_tool_task",
            stage="build",
            description="工具测试任务",
        )

        # 记录成功工具调用
        success = self.integration.record_tool_call(
            task_id="test_tool_task",
            tool_name="write_file",
            tool_output={"file": "test.py", "lines": 50},
            execution_time_ms=200.0,
            author="test",
        )

        self.assertTrue(success)

        # 记录失败工具调用
        success = self.integration.record_tool_call(
            task_id="test_tool_task",
            tool_name="read_file",
            tool_output=None,
            execution_time_ms=50.0,
            error="文件不存在",
        )

        self.assertTrue(success)

        # 获取上下文验证
        context = self.integration.get_task_execution_context("test_tool_task")
        self.assertIsNotNone(context)
        self.assertGreaterEqual(context["tool_call_count"], 2)

    def test_handoff_validation(self):
        """测试 handoff 验证（orchestration smoke）"""
        # 注册任务并设置状态
        self.integration.register_task(
            task_id="test_handoff_task",
            stage="review",
            description="Handoff 测试任务",
        )

        self.integration.update_task_state(
            task_id="test_handoff_task",
            new_state="running",
            reason="准备测试 handoff",
        )

        # 验证 handoff
        should_handoff, reason, decision = self.integration.validate_handoff(
            task_id="test_handoff_task",
            handoff_type="runtime",
        )

        # 运行中的任务应该允许 handoff
        self.assertTrue(should_handoff)
        self.assertIsNotNone(reason)
        self.assertIn("state_machine_based", decision)

        # 将任务标记为失败，handoff 应该被拒绝
        self.integration.update_task_state(
            task_id="test_handoff_task",
            new_state="failed",
            reason="模拟失败",
        )

        should_handoff, reason, decision = self.integration.validate_handoff(
            task_id="test_handoff_task",
            handoff_type="runtime",
        )

        self.assertFalse(should_handoff)
        self.assertIn("任务状态为 failed", reason)

    def test_wrap_tool_result(self):
        """测试工具结果包装"""
        # 成功结果
        success_result = self.integration.wrap_tool_result(
            tool_name="test_tool",
            tool_output={"result": "success", "data": [1, 2, 3]},
            execution_time_ms=100.0,
            custom_field="value",
        )

        self.assertEqual(success_result.status, "success")
        self.assertEqual(success_result.tool_name, "test_tool")
        self.assertEqual(success_result.data["result"], "success")
        self.assertEqual(success_result.metadata.get("custom_field"), "value")

        # 错误结果（通过 error 参数）
        error_result = self.integration.wrap_tool_result(
            tool_name="test_tool",
            tool_output=None,
            execution_time_ms=50.0,
            error="执行失败",
            error_code="E001",
        )

        self.assertEqual(error_result.status, "error")
        self.assertEqual(error_result.tool_name, "test_tool")
        self.assertEqual(error_result.error_context["error_message"], "执行失败")

        # 错误结果（通过工具输出中的 error 字段）
        error_result2 = self.integration.wrap_tool_result(
            tool_name="test_tool",
            tool_output={"error": "内部错误", "error_type": "validation"},
            execution_time_ms=30.0,
        )

        self.assertEqual(error_result2.status, "error")
        self.assertEqual(error_result2.error_context["error_message"], "内部错误")
        self.assertEqual(error_result2.error_context["error_type"], "validation")


class TestOrchestratorIntegration(unittest.TestCase):
    """编排器集成测试（smoke test）"""

    def test_orchestrator_with_execution_graph(self):
        """
        编排器与执行图集成冒烟测试

        验证新协议可以被当前执行链消费
        """
        try:
            from agent.core.athena_orchestrator import AthenaOrchestrator

            # 创建编排器实例
            orchestrator = AthenaOrchestrator()

            # 创建任务（应该自动注册到执行图）
            success, task_id, metadata = orchestrator.create_task(
                stage="build",
                domain="engineering",
                description="冒烟测试任务",
            )

            self.assertTrue(success)
            self.assertIsNotNone(task_id)

            # 更新任务状态（应该同步到执行图）
            success = orchestrator.update_task_status(
                task_id=task_id,
                status="running",
                reason="冒烟测试",
            )

            self.assertTrue(success)

            # 记录工具调用（如果方法存在）
            if hasattr(orchestrator, "record_tool_call"):
                success = orchestrator.record_tool_call(
                    task_id=task_id,
                    tool_name="test_tool",
                    tool_output={"result": "ok"},
                    execution_time_ms=150.0,
                )

                self.assertTrue(success)

            # 验证任务可以获取
            task = orchestrator.get_task(task_id)
            self.assertIsNotNone(task)
            self.assertEqual(task["task_id"], task_id)

            print(f"✅ 编排器集成冒烟测试通过: 任务 {task_id}")

        except ImportError as e:
            self.skipTest(f"无法导入编排器: {e}")
        except Exception as e:
            self.fail(f"编排器集成冒烟测试失败: {e}")


if __name__ == "__main__":
    # 运行测试
    print("=== 执行图状态机与工具协议接线测试 ===")

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestExecutionGraphProtocol))
    suite.addTests(loader.loadTestsFromTestCase(TestExecutionIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestOrchestratorIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出总结
    print(f"\n测试总结:")
    print(f"  运行测试: {result.testsRun}")
    print(f"  失败: {len(result.failures)}")
    print(f"  错误: {len(result.errors)}")
    print(f"  跳过: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n✅ 所有测试通过!")
        sys.exit(0)
    else:
        print("\n❌ 测试失败!")
        sys.exit(1)
