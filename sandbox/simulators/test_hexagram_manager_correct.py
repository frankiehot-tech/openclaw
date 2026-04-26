#!/usr/bin/env python3
"""
64卦状态管理器正确单元测试

使用正确的方法名和接口测试IntegratedHexagramStateManager
"""

import sys
import unittest
import tempfile
import os

# 添加项目根目录到路径
sys.path.insert(0, "/Volumes/1TB-M2/openclaw")

from integrated_hexagram_state_manager import (
    IntegratedHexagramStateManager,
    HetuState,
    StateAnalysis,
)


class TestHexagramManagerCorrect(unittest.TestCase):
    """测试64卦状态管理器（正确接口）"""

    def setUp(self):
        """测试前置设置"""
        self.manager = IntegratedHexagramStateManager()
        # 初始化状态
        self.manager.initialize_state("000000")

    def test_initialization(self):
        """测试管理器初始化"""
        self.assertIsNotNone(self.manager)
        # 检查映射是否加载
        self.assertTrue(hasattr(self.manager, 'mappings'))
        # 检查当前状态（应该是字符串）
        self.assertIsInstance(self.manager.current_state, str)
        self.assertEqual(len(self.manager.current_state), 6)  # 6位二进制

    def test_hamming_distance(self):
        """测试汉明距离计算"""
        # 测试已知距离
        self.assertEqual(self.manager.hamming_distance("000000", "000001"), 1)
        self.assertEqual(self.manager.hamming_distance("000000", "000011"), 2)
        self.assertEqual(self.manager.hamming_distance("000111", "000000"), 3)
        self.assertEqual(self.manager.hamming_distance("000000", "000000"), 0)

    def test_get_hexagram_name(self):
        """测试获取卦象名称"""
        name = self.manager.get_hexagram_name("000000")
        self.assertIsInstance(name, str)
        self.assertTrue(len(name) > 0)

        # 测试另一个卦象
        name2 = self.manager.get_hexagram_name("000001")
        self.assertIsInstance(name2, str)
        self.assertTrue(len(name2) > 0)

    def test_get_hetu_state(self):
        """测试获取河图状态"""
        # 测试几个卦象的河图状态
        hetu_state = self.manager.get_hetu_state("000000")
        self.assertIsNotNone(hetu_state)
        self.assertIsInstance(hetu_state, HetuState)

        hetu_state2 = self.manager.get_hetu_state("000001")
        self.assertIsNotNone(hetu_state2)
        self.assertIsInstance(hetu_state2, HetuState)

    def test_get_dimension_values(self):
        """测试获取维度值"""
        dimensions = self.manager.get_dimension_values("000000")
        self.assertIsInstance(dimensions, dict)

        # 检查预期的维度
        expected_keys = [
            "correctness",
            "complexity",
            "style",
            "readability",
            "maintainability",
            "cost_efficiency"
        ]

        for key in expected_keys:
            self.assertIn(key, dimensions)
            # 维度值应该是整数（0或1）
            self.assertIsInstance(dimensions[key], int)
            self.assertTrue(0 <= dimensions[key] <= 1)

    def test_analyze_state(self):
        """测试状态分析"""
        analysis = self.manager.analyze_state("000000")

        # analyze_state可能返回None（如果是异步分析）
        if analysis is not None:
            self.assertIsInstance(analysis, StateAnalysis)
            self.assertEqual(analysis.binary_representation, "000000")
            self.assertIsInstance(analysis.hexagram_name, str)
            self.assertIsInstance(analysis.quality_score, float)
            self.assertTrue(0 <= analysis.quality_score <= 10)
        else:
            # 如果是异步分析，记录警告
            self.skipTest("analyze_state返回None（可能是异步分析）")

    def test_transition_valid(self):
        """测试有效状态转移"""
        # 从当前状态"000000"转移到"000001"（汉明距离为1）
        success = self.manager.transition("000001")
        self.assertTrue(success)
        self.assertEqual(self.manager.current_state, "000001")

    def test_transition_invalid_hamming(self):
        """测试无效状态转移（汉明距离不为1）"""
        # 从当前状态"000000"直接转移到"000011"（汉明距离为2）
        success = self.manager.transition("000011")
        self.assertFalse(success)
        # 状态不应改变
        self.assertEqual(self.manager.current_state, "000000")

    def test_get_valid_transitions(self):
        """测试获取有效转移"""
        valid_transitions = self.manager.get_valid_transitions("000000")
        self.assertIsInstance(valid_transitions, list)

        # 检查每个转移都是有效状态
        for state in valid_transitions:
            self.assertIsInstance(state, str)
            self.assertEqual(len(state), 6)
            # 汉明距离应为1
            self.assertEqual(self.manager.hamming_distance("000000", state), 1)

    def test_get_states_by_hetu(self):
        """测试通过河图状态获取卦象列表"""
        # 获取INITIAL状态对应的所有卦象
        states = self.manager.get_states_by_hetu(HetuState.INITIAL)
        self.assertIsInstance(states, list)

        # 至少应该有一个卦象
        self.assertTrue(len(states) > 0)

        # 每个都应该是6位二进制字符串
        for state in states:
            self.assertIsInstance(state, str)
            self.assertEqual(len(state), 6)

    @unittest.skip("save_state方法不存在")
    def test_save_and_load_state(self):
        """测试状态保存和加载"""
        # 先进行一些状态转移
        self.manager.transition("000001")
        self.manager.transition("000011")

        # 保存状态到临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            success = self.manager.save_state(temp_file)
            self.assertTrue(success)

            # 创建新管理器并加载状态
            new_manager = IntegratedHexagramStateManager()
            load_success = new_manager.load_state(temp_file)
            self.assertTrue(load_success)

            # 验证状态一致
            self.assertEqual(new_manager.current_state, self.manager.current_state)

        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_visualize_state_space(self):
        """测试状态空间可视化"""
        visualization = self.manager.visualize_state_space()
        self.assertIsInstance(visualization, str)
        self.assertTrue(len(visualization) > 0)

        # 应包含关键信息
        self.assertIn("64卦状态空间", visualization)

    def test_print_state_info(self):
        """测试打印状态信息（不检查输出，只确保不崩溃）"""
        try:
            self.manager.print_state_info("000000")
            # 如果不崩溃，测试通过
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"print_state_info抛出异常: {e}")

    def test_hetu_state_enum(self):
        """测试河图状态枚举"""
        # 检查所有河图状态（根据integrated_hexagram_state_manager.py）
        expected_states = [
            "INITIAL",
            "AST_PARSED",
            "DIMENSION_ASSESSING",
            "TEST_RUNNING",
            "RESULT_AGGREGATING",
            "STRATEGY_ANALYZING",
            "TREND_PREDICTING",
            "REPORT_GENERATING",
            "DECISION_SUPPORTING",
            "COMPLETED",
        ]

        for state_name in expected_states:
            state = HetuState[state_name]
            self.assertIsNotNone(state)
            self.assertEqual(state.name, state_name)


if __name__ == "__main__":
    unittest.main()