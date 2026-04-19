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
