#!/usr/bin/env python3
"""
集成64卦状态管理器单元测试
使用unittest框架，便于CI/CD集成
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integrated_hexagram_state_manager import (
    HetuState,
    IntegratedHexagramStateManager,
    StateAnalysis,
    StateEvolution,
)


class TestIntegratedHexagramStateManager(unittest.TestCase):
    """集成64卦状态管理器测试类"""

    def setUp(self):
        """测试前置设置"""
        # 使用项目中的映射文件
        mapping_file = "hetu_hexagram_mapping.json"
        self.assertTrue(os.path.exists(mapping_file), f"映射文件不存在: {mapping_file}")
        self.manager = IntegratedHexagramStateManager(mapping_file)

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(len(self.manager.mappings), 64)
        self.assertEqual(len(self.manager.DIMENSIONS), 6)
        self.assertIn("correctness", self.manager.DIMENSIONS)
        self.assertIsNone(self.manager.current_state)  # 初始时未设置当前状态

    def test_initialize_state(self):
        """测试状态初始化"""
        # 有效状态
        self.assertTrue(self.manager.initialize_state("000000"))
        self.assertEqual(self.manager.current_state, "000000")
        self.assertEqual(self.manager.get_hexagram_name(), "坤 (Kun)")

        # 无效状态
        self.assertFalse(self.manager.initialize_state("999999"))

    def test_validate_state(self):
        """测试状态验证"""
        self.assertTrue(self.manager._validate_state("000000"))
        self.assertTrue(self.manager._validate_state("111111"))
        self.assertFalse(self.manager._validate_state("00000"))  # 长度不足
        self.assertFalse(self.manager._validate_state("0000000"))  # 长度过长
        self.assertFalse(self.manager._validate_state("222222"))  # 非法字符

    def test_hamming_distance(self):
        """测试汉明距离计算"""
        self.assertEqual(self.manager.hamming_distance("000000", "000000"), 0)
        self.assertEqual(self.manager.hamming_distance("000000", "000001"), 1)
        self.assertEqual(self.manager.hamming_distance("000000", "111111"), 6)

        # 测试长度不一致的情况
        with self.assertRaises(ValueError):
            self.manager.hamming_distance("000", "0000")

    def test_get_valid_transitions(self):
        """测试获取有效转换"""
        self.manager.initialize_state("000000")
        transitions = self.manager.get_valid_transitions()

        # 应该有多个有效转换（每个位翻转一次）
        self.assertGreater(len(transitions), 0)

        # 所有转换都应该是有效状态
        for state in transitions:
            self.assertTrue(self.manager._validate_state(state))

        # 每个转换的汉明距离应该为1
        for state in transitions:
            self.assertEqual(self.manager.hamming_distance("000000", state), 1)

    def test_state_transition(self):
        """测试状态转换（格雷编码约束）"""
        self.manager.initialize_state("000000")

        # 有效转换（汉明距离=1）
        valid_target = "000001"  # 坤 -> 剥
        self.assertTrue(self.manager.transition(valid_target, "测试转换"))
        self.assertEqual(self.manager.current_state, valid_target)

        # 无效转换（汉明距离>1）
        self.manager.initialize_state("000000")
        invalid_target = "000011"  # 汉明距离=2
        self.assertFalse(self.manager.transition(invalid_target, "无效转换"))
        self.assertEqual(self.manager.current_state, "000000")  # 应该保持不变

    def test_get_hexagram_name(self):
        """测试获取卦象名称"""
        self.manager.initialize_state("000000")
        self.assertEqual(self.manager.get_hexagram_name(), "坤 (Kun)")
        self.assertEqual(self.manager.get_hexagram_name("111111"), "乾 (Qian)")
        self.assertEqual(self.manager.get_hexagram_name("invalid"), "未知卦象")

    def test_get_hetu_state(self):
        """测试获取河图状态"""
        # 测试几个已知映射
        # 坤卦 (000000) 应该映射到 INITIAL
        self.manager.initialize_state("000000")
        hetu = self.manager.get_hetu_state()
        self.assertEqual(hetu, HetuState.INITIAL)

        # 乾卦 (111111) 应该映射到 COMPLETED
        hetu = self.manager.get_hetu_state("111111")
        self.assertEqual(hetu, HetuState.COMPLETED)

    def test_get_dimension_values(self):
        """测试获取维度值"""
        self.manager.initialize_state("000000")
        dims = self.manager.get_dimension_values()
        self.assertEqual(len(dims), 6)

        # 坤卦应该是全0（所有维度未激活）
        for val in dims.values():
            self.assertEqual(val, 0)

        # 乾卦应该是全1（所有维度激活）
        dims = self.manager.get_dimension_values("111111")
        for val in dims.values():
            self.assertEqual(val, 1)

    def test_analyze_state(self):
        """测试状态分析"""
        # 测试坤卦（全0）
        analysis = self.manager.analyze_state("000000")
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.hexagram_name, "坤 (Kun)")
        self.assertEqual(analysis.quality_score, 0.0)  # 无激活维度
        self.assertEqual(len(analysis.active_dimensions), 0)
        self.assertEqual(len(analysis.inactive_dimensions), 6)
        self.assertEqual(analysis.evolution_distance_to_perfect, 6)  # 到乾卦距离6

        # 测试乾卦（全1）
        analysis = self.manager.analyze_state("111111")
        self.assertEqual(analysis.quality_score, 10.0)  # 全激活
        self.assertEqual(len(analysis.active_dimensions), 6)
        self.assertEqual(analysis.evolution_distance_to_perfect, 0)  # 完美状态

    def test_get_states_by_hetu(self):
        """测试按河图状态获取卦象"""
        # 每个河图状态应该有6-7个卦象
        states = self.manager.get_states_by_hetu(HetuState.INITIAL)
        self.assertGreaterEqual(len(states), 6)
        self.assertLessEqual(len(states), 7)

        # 所有状态都应该是有效的
        for state in states:
            self.assertTrue(self.manager._validate_state(state))

    def test_find_path_to_hetu_state(self):
        """测试查找河图状态路径"""
        self.manager.initialize_state("000000")

        # 从INITIAL到COMPLETED应该能找到路径
        path = self.manager.find_path_to_hetu_state(HetuState.COMPLETED, max_steps=10)
        self.assertGreater(len(path), 0)

        # 路径的第一个状态应该是初始状态
        self.assertEqual(path[0], "000000")

        # 路径的最后一个状态应该在COMPLETED河图状态中
        final_states = self.manager.get_states_by_hetu(HetuState.COMPLETED)
        self.assertIn(path[-1], final_states)

    def test_evolution_history(self):
        """测试演化历史记录"""
        self.manager.initialize_state("000000")

        # 初始时历史为空
        self.assertEqual(len(self.manager.get_evolution_history()), 0)

        # 执行转换后历史增加
        self.manager.transition("000001", "测试转换")
        history = self.manager.get_evolution_history()
        self.assertEqual(len(history), 1)

        evolution = history[0]
        self.assertEqual(evolution.from_state, "000000")
        self.assertEqual(evolution.to_state, "000001")
        self.assertEqual(evolution.hamming_distance, 1)

    def test_visualize_state_space(self):
        """测试状态空间可视化（不验证内容，只验证函数不抛出异常）"""
        visualization = self.manager.visualize_state_space(
            highlight_hetu_states=[HetuState.INITIAL, HetuState.COMPLETED]
        )
        self.assertIsInstance(visualization, str)
        self.assertGreater(len(visualization), 0)

    def test_load_mappings_error_handling(self):
        """测试映射文件错误处理"""
        # 测试文件不存在的情况
        with self.assertRaises(FileNotFoundError):
            IntegratedHexagramStateManager("non_existent_file.json")

        # 创建一个包含未知河图状态的测试映射文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            invalid_mapping = {
                "mappings": [
                    {
                        "hexagram_code": 0,
                        "binary": "000000",
                        "hexagram_name": "Test Hexagram",
                        "dimension_values": {"correctness": 0, "complexity": 0, "style": 0, "readability": 0, "maintainability": 0, "cost_efficiency": 0},
                        "hetu_state": "UNKNOWN_STATE",
                        "hetu_state_value": 99,
                        "semantic_description": "Test description"
                    }
                ]
            }
            json.dump(invalid_mapping, f)
            temp_file = f.name

        try:
            # 测试未知河图状态的情况
            with self.assertRaises(ValueError):
                IntegratedHexagramStateManager(temp_file)
        finally:
            # 清理临时文件
            os.unlink(temp_file)

    def test_transition_context_and_changed_dimension(self):
        """测试状态转换的上下文和维度变化检测"""
        self.manager.initialize_state("000000")

        # 测试带上下文参数的转换
        context = {"reason": "测试上下文", "user": "test_user"}
        target_state = "000001"  # 翻转第一位

        self.assertTrue(self.manager.transition(target_state, "测试转换", context))

        # 验证演化历史中包含了上下文
        history = self.manager.get_evolution_history()
        self.assertEqual(len(history), 1)
        evolution = history[0]
        self.assertEqual(evolution.context, context)

        # 验证维度变化检测
        self.assertIsNotNone(evolution.changed_dimension)
        self.assertIn(evolution.changed_dimension, self.manager.DIMENSIONS)

    def test_get_hetu_state_transitions(self):
        """测试河图状态间转换查找"""
        self.manager.initialize_state("000000")

        # 获取INITIAL到AST_PARSED之间的可能转换
        transitions = self.manager.get_hetu_state_transitions(
            HetuState.INITIAL, HetuState.AST_PARSED
        )

        # 应该有一些转换
        self.assertGreater(len(transitions), 0)

        # 验证每个转换都是有效的
        for from_state, to_state in transitions:
            self.assertTrue(self.manager._validate_state(from_state))
            self.assertTrue(self.manager._validate_state(to_state))
            self.assertEqual(self.manager.hamming_distance(from_state, to_state), 1)

            # 验证河图状态
            from_hetu = self.manager.get_hetu_state(from_state)
            to_hetu = self.manager.get_hetu_state(to_state)
            self.assertEqual(from_hetu, HetuState.INITIAL)
            self.assertEqual(to_hetu, HetuState.AST_PARSED)

    def test_find_path_edge_cases(self):
        """测试路径查找边界条件"""
        self.manager.initialize_state("000000")

        # 测试路径不存在的情况（目标河图状态没有卦象）
        # 创建一个临时的假河图状态（不在枚举中）
        fake_state_value = 99
        fake_state = HetuState(fake_state_value) if fake_state_value in [s.value for s in HetuState] else None

        if fake_state:
            path = self.manager.find_path_to_hetu_state(fake_state, max_steps=3)
            self.assertEqual(len(path), 0)  # 应该找不到路径

        # 测试步数限制
        path = self.manager.find_path_to_hetu_state(HetuState.COMPLETED, max_steps=2)
        if path:
            # 如果有路径，应该不超过max_steps步
            self.assertLessEqual(len(path), 2 + 1)  # 路径包括起始状态
        else:
            # 2步内可能找不到路径，这是正常的
            pass

        # 测试当前状态为None的情况
        manager2 = IntegratedHexagramStateManager("hetu_hexagram_mapping.json")
        # 不初始化状态
        path = manager2.find_path_to_hetu_state(HetuState.COMPLETED)
        self.assertEqual(len(path), 0)  # 应该返回空列表

    def test_analyze_state_partial_activation(self):
        """测试部分激活维度的状态分析"""
        # 找到一个部分激活维度的卦象（既有0又有1）
        # 遍历卦象，找到第一个不是全0也不是全1的卦象
        found = False
        for binary_state in self.manager._by_binary.keys():
            dim_values = self.manager.get_dimension_values(binary_state)
            if 0 in dim_values.values() and 1 in dim_values.values():
                # 部分激活的卦象
                analysis = self.manager.analyze_state(binary_state)
                self.assertIsNotNone(analysis)

                # 质量评分应该在0-10之间
                self.assertGreaterEqual(analysis.quality_score, 0)
                self.assertLessEqual(analysis.quality_score, 10)

                # 激活维度数应该在1-5之间
                active_count = len(analysis.active_dimensions)
                self.assertGreaterEqual(active_count, 1)
                self.assertLessEqual(active_count, 5)

                # 非激活维度数应该在1-5之间
                inactive_count = len(analysis.inactive_dimensions)
                self.assertGreaterEqual(inactive_count, 1)
                self.assertLessEqual(inactive_count, 5)

                # 两者之和应为6
                self.assertEqual(active_count + inactive_count, 6)

                found = True
                break

        self.assertTrue(found, "未找到部分激活维度的卦象")

    def test_methods_with_none_state(self):
        """测试状态为None时的各种方法"""
        # 创建一个新的管理器，不初始化状态
        manager2 = IntegratedHexagramStateManager("hetu_hexagram_mapping.json")

        # 测试get_hexagram_name(None)
        name = manager2.get_hexagram_name()
        self.assertEqual(name, "未初始化")

        # 测试get_hetu_state(None)
        hetu = manager2.get_hetu_state()
        self.assertIsNone(hetu)

        # 测试get_dimension_values(None)
        dims = manager2.get_dimension_values()
        self.assertEqual(dims, {})

        # 测试analyze_state(None)
        analysis = manager2.analyze_state()
        self.assertIsNone(analysis)

        # 测试get_valid_transitions(None)
        transitions = manager2.get_valid_transitions()
        self.assertEqual(transitions, [])

    def test_print_state_info(self):
        """测试打印状态信息"""
        self.manager.initialize_state("000000")

        # 重定向标准输出以捕获打印内容
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            self.manager.print_state_info()
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        # 验证输出包含关键信息
        self.assertIn("状态分析", output)
        self.assertIn("坤", output)
        self.assertIn("二进制", output)
        self.assertIn("质量评分", output)

    def test_evolution_history_limits(self):
        """测试演化历史限制"""
        self.manager.initialize_state("000000")

        # 执行多次转换以创建历史
        states_to_try = ["000001", "000011", "000111", "001111"]
        for i, state in enumerate(states_to_try):
            if self.manager._validate_state(state):
                self.manager.transition(state, f"转换{i}")

        # 测试获取有限历史
        history = self.manager.get_evolution_history(limit=2)
        self.assertLessEqual(len(history), 2)

        # 如果历史长度大于2，应该返回最后2个
        if len(self.manager.state_history) > 2:
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0], self.manager.state_history[-2])
            self.assertEqual(history[1], self.manager.state_history[-1])


class TestHetuStateEnum(unittest.TestCase):
    """河图状态枚举测试"""

    def test_enum_values(self):
        """测试枚举值"""
        self.assertEqual(HetuState.INITIAL.value, 1)
        self.assertEqual(HetuState.AST_PARSED.value, 2)
        self.assertEqual(HetuState.COMPLETED.value, 10)

    def test_enum_names(self):
        """测试枚举名称"""
        self.assertEqual(HetuState.INITIAL.name, "INITIAL")
        self.assertEqual(HetuState.AST_PARSED.name, "AST_PARSED")
        self.assertEqual(HetuState.COMPLETED.name, "COMPLETED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
