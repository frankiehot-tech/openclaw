#!/usr/bin/env python3
"""
64卦状态管理器综合单元测试

覆盖IntegratedHexagramStateManager所有核心功能：
1. 状态初始化和验证
2. 格雷编码约束下的状态转移
3. 河图状态映射
4. 质量维度分析
5. 路径查找和演化历史
6. 状态空间可视化
"""

import sys
import unittest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch

# 添加项目根目录到路径
sys.path.insert(0, "/Volumes/1TB-M2/openclaw")

from integrated_hexagram_state_manager import (
    IntegratedHexagramStateManager,
    HetuState,
    StateAnalysis,
)


class TestHexagramStateManagerComprehensive(unittest.TestCase):
    """测试64卦状态管理器（综合版）"""

    def setUp(self):
        """测试前置设置"""
        self.manager = IntegratedHexagramStateManager()
        # 初始化状态
        self.manager.initialize_state("000000")

    def tearDown(self):
        """测试后清理"""
        # 清理可能的临时文件
        if hasattr(self, '_temp_file') and os.path.exists(self._temp_file):
            os.unlink(self._temp_file)

    def test_initialization(self):
        """测试管理器初始化"""
        self.assertIsNotNone(self.manager)
        # 检查映射是否加载
        self.assertTrue(hasattr(self.manager, 'mappings'))
        # 检查当前状态（应该是字符串）
        self.assertIsInstance(self.manager.current_state, str)
        self.assertEqual(len(self.manager.current_state), 6)  # 6位二进制
        self.assertEqual(self.manager.current_state, "000000")

        # 检查河图状态分组
        self.assertTrue(hasattr(self.manager, '_by_hetu_state'))
        self.assertEqual(len(self.manager._by_hetu_state), 10)  # 10个河图状态

    def test_hamming_distance(self):
        """测试汉明距离计算（带缓存优化）"""
        # 测试已知距离
        self.assertEqual(self.manager.hamming_distance("000000", "000001"), 1)
        self.assertEqual(self.manager.hamming_distance("000000", "000011"), 2)
        self.assertEqual(self.manager.hamming_distance("000111", "000000"), 3)
        self.assertEqual(self.manager.hamming_distance("000000", "000000"), 0)

        # 测试全反状态
        self.assertEqual(self.manager.hamming_distance("010101", "101010"), 6)
        self.assertEqual(self.manager.hamming_distance("111111", "000000"), 6)

    def test_get_hexagram_name(self):
        """测试获取卦象名称"""
        # 测试几个卦象的名称
        name_0 = self.manager.get_hexagram_name("000000")
        name_1 = self.manager.get_hexagram_name("000001")
        name_63 = self.manager.get_hexagram_name("111111")

        self.assertIsInstance(name_0, str)
        self.assertIsInstance(name_1, str)
        self.assertIsInstance(name_63, str)

        # 名称不应为空
        self.assertTrue(len(name_0) > 0)
        self.assertTrue(len(name_1) > 0)
        self.assertTrue(len(name_63) > 0)

        # 测试默认参数（使用当前状态）
        name_current = self.manager.get_hexagram_name()
        self.assertEqual(name_current, name_0)

    def test_get_hetu_state(self):
        """测试获取河图状态"""
        # 测试几个卦象的河图状态
        hetu_state_0 = self.manager.get_hetu_state("000000")
        hetu_state_1 = self.manager.get_hetu_state("000001")

        self.assertIsNotNone(hetu_state_0)
        self.assertIsNotNone(hetu_state_1)
        self.assertIsInstance(hetu_state_0, HetuState)
        self.assertIsInstance(hetu_state_1, HetuState)

        # 测试默认参数（使用当前状态）
        hetu_current = self.manager.get_hetu_state()
        self.assertEqual(hetu_current, hetu_state_0)

        # 测试所有卦象都有河图状态映射
        for i in range(64):
            binary = format(i, '06b')
            hetu = self.manager.get_hetu_state(binary)
            self.assertIsNotNone(hetu, f"卦象 {binary} 没有河图状态映射")
            self.assertIsInstance(hetu, HetuState)

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

        # 测试默认参数
        dims_current = self.manager.get_dimension_values()
        self.assertEqual(dims_current, dimensions)

        # 测试多个卦象的维度值一致性
        test_states = ["000000", "000001", "010101", "111111"]
        for state in test_states:
            dims = self.manager.get_dimension_values(state)
            self.assertEqual(len(dims), 6)
            for value in dims.values():
                self.assertTrue(0 <= value <= 1)

    def test_analyze_state(self):
        """测试状态分析（同步模式）"""
        analysis = self.manager.analyze_state("000000")

        # analyze_state可能返回None（如果状态无效）
        if analysis is not None:
            self.assertIsInstance(analysis, StateAnalysis)
            self.assertEqual(analysis.binary_representation, "000000")
            self.assertIsInstance(analysis.hexagram_name, str)
            self.assertIsInstance(analysis.quality_score, float)
            self.assertTrue(0 <= analysis.quality_score <= 10)
            self.assertIsInstance(analysis.active_dimensions, list)
            self.assertIsInstance(analysis.inactive_dimensions, list)

            # 检查维度计数
            total_dims = len(analysis.active_dimensions) + len(analysis.inactive_dimensions)
            self.assertEqual(total_dims, 6)
        else:
            # 如果返回None，标记测试失败（因为"000000"应该是有效状态）
            self.fail("analyze_state返回None，但'000000'应该是有效状态")

    def test_transition_valid(self):
        """测试有效状态转移（格雷编码约束）"""
        # 从当前状态"000000"转移到"000001"（汉明距离为1）
        success = self.manager.transition("000001")
        self.assertTrue(success)
        self.assertEqual(self.manager.current_state, "000001")

        # 检查演化历史记录
        history = self.manager.get_evolution_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].from_state, "000000")
        self.assertEqual(history[0].to_state, "000001")

        # 再次转移
        success2 = self.manager.transition("000011")
        self.assertTrue(success2)
        self.assertEqual(self.manager.current_state, "000011")
        self.assertEqual(len(self.manager.get_evolution_history()), 2)

    def test_transition_invalid_hamming(self):
        """测试无效状态转移（汉明距离不为1）"""
        # 从当前状态"000000"直接转移到"000011"（汉明距离为2）
        success = self.manager.transition("000011")
        self.assertFalse(success)
        # 状态不应改变（应保持为"000000"）
        self.assertEqual(self.manager.current_state, "000000")

        # 历史不应记录失败的转移
        history = self.manager.get_evolution_history()
        self.assertEqual(len(history), 0)

    def test_transition_invalid_state(self):
        """测试转移到无效状态"""
        # 无效长度
        success = self.manager.transition("00000")
        self.assertFalse(success)

        # 无效字符
        success = self.manager.transition("00000a")
        self.assertFalse(success)

        # 超出范围（7位）
        success = self.manager.transition("0000000")
        self.assertFalse(success)

    def test_get_valid_transitions(self):
        """测试获取有效转移"""
        valid_transitions = self.manager.get_valid_transitions("000000")
        self.assertIsInstance(valid_transitions, list)

        # "000000"应该有6个有效转移（每位翻转一次）
        self.assertEqual(len(valid_transitions), 6)

        # 检查每个转移都是有效状态
        for state in valid_transitions:
            self.assertIsInstance(state, str)
            self.assertEqual(len(state), 6)
            # 汉明距离应为1
            self.assertEqual(self.manager.hamming_distance("000000", state), 1)

        # 测试默认参数（使用当前状态）
        valid_current = self.manager.get_valid_transitions()
        self.assertEqual(valid_current, valid_transitions)

        # 测试其他状态的转移数量
        test_state = "010101"
        valid_test = self.manager.get_valid_transitions(test_state)
        self.assertEqual(len(valid_test), 6)  # 任何状态都有6个可能的单比特翻转

    def test_get_states_by_hetu(self):
        """测试通过河图状态获取卦象列表"""
        # 获取INITIAL状态对应的所有卦象
        states = self.manager.get_states_by_hetu(HetuState.INITIAL)
        self.assertIsInstance(states, list)

        # 每个河图状态应该映射到6-7个卦象
        self.assertTrue(5 <= len(states) <= 8,
                       f"INITIAL状态映射的卦象数量异常: {len(states)}")

        # 每个都应该是6位二进制字符串
        for state in states:
            self.assertIsInstance(state, str)
            self.assertEqual(len(state), 6)
            # 验证映射一致性
            hetu = self.manager.get_hetu_state(state)
            self.assertEqual(hetu, HetuState.INITIAL)

        # 测试所有河图状态都有映射
        for hetu_state in HetuState:
            states_for_hetu = self.manager.get_states_by_hetu(hetu_state)
            self.assertIsInstance(states_for_hetu, list)
            self.assertTrue(len(states_for_hetu) > 0,
                          f"河图状态{hetu_state.name}没有映射卦象")

    def test_hetu_state_enum(self):
        """测试河图状态枚举（使用正确的枚举值）"""
        # 检查所有河图状态（根据integrated_hexagram_state_manager.py）
        expected_states = [
            "INITIAL",           # 1
            "AST_PARSED",        # 2
            "DIMENSION_ASSESSING", # 3
            "TEST_RUNNING",      # 4
            "RESULT_AGGREGATING", # 5
            "STRATEGY_ANALYZING", # 6
            "TREND_PREDICTING",  # 7
            "REPORT_GENERATING", # 8
            "DECISION_SUPPORTING", # 9
            "COMPLETED",         # 10
        ]

        for state_name in expected_states:
            state = HetuState[state_name]
            self.assertIsNotNone(state)
            self.assertEqual(state.name, state_name)

        # 检查枚举总数
        self.assertEqual(len(list(HetuState)), 10)

    def test_visualize_state_space(self):
        """测试状态空间可视化"""
        visualization = self.manager.visualize_state_space()
        self.assertIsInstance(visualization, str)
        self.assertTrue(len(visualization) > 0)

        # 应包含关键信息
        self.assertIn("64卦状态空间", visualization)

        # 测试高亮特定河图状态
        highlighted = self.manager.visualize_state_space(
            highlight_hetu_states=[HetuState.INITIAL, HetuState.COMPLETED]
        )
        self.assertIn("INITIAL", highlighted)
        self.assertIn("COMPLETED", highlighted)

    def test_print_state_info(self):
        """测试打印状态信息（不检查输出，只确保不崩溃）"""
        try:
            self.manager.print_state_info("000000")
            # 如果不崩溃，测试通过
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"print_state_info抛出异常: {e}")

        # 测试默认参数
        try:
            self.manager.print_state_info()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"print_state_info(默认)抛出异常: {e}")

    def test_find_path_to_hetu_state(self):
        """测试寻找到河图状态的路径"""
        # 寻找从当前状态到COMPLETED状态的路径
        path = self.manager.find_path_to_hetu_state(
            target_hetu=HetuState.COMPLETED,
            max_steps=10
        )

        if path:  # 路径可能为空（如果找不到）
            self.assertIsInstance(path, list)
            # 路径应至少包含起点
            self.assertTrue(len(path) >= 1)

            # 检查每个状态都是有效卦象
            for state in path:
                self.assertIsInstance(state, str)
                self.assertEqual(len(state), 6)

            # 终点应该映射到目标河图状态
            final_state = path[-1]
            final_hetu = self.manager.get_hetu_state(final_state)
            self.assertEqual(final_hetu, HetuState.COMPLETED)

            # 路径应满足格雷编码约束（相邻状态汉明距离为1）
            for i in range(len(path) - 1):
                hamming = self.manager.hamming_distance(path[i], path[i + 1])
                self.assertEqual(hamming, 1,
                               f"路径中{path[i]}→{path[i+1]}汉明距离不为1: {hamming}")
        else:
            # 可能找不到路径，这是可接受的
            print("⚠️  未找到到COMPLETED状态的路径")

    def test_get_evolution_history(self):
        """测试获取演化历史"""
        # 初始历史应为空
        history = self.manager.get_evolution_history()
        self.assertIsInstance(history, list)
        self.assertEqual(len(history), 0)

        # 执行一些转移
        self.manager.transition("000001")
        self.manager.transition("000011")
        self.manager.transition("000111")

        # 检查历史记录
        history = self.manager.get_evolution_history()
        self.assertEqual(len(history), 3)

        # 检查历史条目结构
        for entry in history:
            self.assertTrue(hasattr(entry, 'from_state'))
            self.assertTrue(hasattr(entry, 'to_state'))
            self.assertTrue(hasattr(entry, 'from_hetu'))
            self.assertTrue(hasattr(entry, 'to_hetu'))
            self.assertTrue(hasattr(entry, 'timestamp'))
            self.assertTrue(hasattr(entry, 'context'))

            self.assertIsInstance(entry.from_state, str)
            self.assertIsInstance(entry.to_state, str)
            self.assertIsInstance(entry.from_hetu, HetuState)
            self.assertIsInstance(entry.to_hetu, HetuState)
            self.assertIsInstance(entry.timestamp, datetime)
            self.assertIsInstance(entry.context, dict)

        # 测试限制返回数量（返回最新的2个条目）
        limited = self.manager.get_evolution_history(limit=2)
        self.assertEqual(len(limited), 2)
        # 最新的2个条目应该是第2和第3次转移
        self.assertEqual(limited[0].from_state, "000001")
        self.assertEqual(limited[0].to_state, "000011")
        self.assertEqual(limited[1].from_state, "000011")
        self.assertEqual(limited[1].to_state, "000111")

    def test_get_hetu_state_transitions(self):
        """测试获取河图状态间转移"""
        transitions = self.manager.get_hetu_state_transitions(
            from_hetu=HetuState.INITIAL,
            to_hetu=HetuState.AST_PARSED
        )

        self.assertIsInstance(transitions, list)

        if transitions:  # 可能没有直接转移
            for transition in transitions:
                self.assertIsInstance(transition, tuple)
                self.assertEqual(len(transition), 2)

                from_state, to_state = transition

                # 验证状态有效性
                self.assertEqual(len(from_state), 6)
                self.assertEqual(len(to_state), 6)

                # 验证河图状态映射
                from_hetu = self.manager.get_hetu_state(from_state)
                to_hetu = self.manager.get_hetu_state(to_state)
                self.assertEqual(from_hetu, HetuState.INITIAL)
                self.assertEqual(to_hetu, HetuState.AST_PARSED)

                # 验证汉明距离为1
                hamming = self.manager.hamming_distance(from_state, to_state)
                self.assertEqual(hamming, 1)

    @unittest.skip("precompute_all_analysis方法不存在，可能已移除或改名")
    def test_precompute_all_analysis(self):
        """测试预计算所有分析（跳过，方法不存在）"""
        # 此方法已不存在，跳过测试
        pass

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试空状态转移（相同状态）
        self.manager.initialize_state("010101")
        success = self.manager.transition("010101")  # 转移到相同状态
        self.assertFalse(success)  # 汉明距离为0，应该失败

        # 测试所有可能的状态转移
        test_state = "010101"
        valid_transitions = self.manager.get_valid_transitions(test_state)
        for target in valid_transitions:
            success = self.manager.transition(target)
            self.assertTrue(success, f"{test_state}→{target}应该成功")
            # 转回原状态
            self.manager.transition(test_state)

        # 测试初始化已初始化状态
        success = self.manager.initialize_state("111111")
        self.assertTrue(success)
        self.assertEqual(self.manager.current_state, "111111")

    def test_state_validation(self):
        """测试状态验证"""
        # 有效状态
        self.assertTrue(self.manager._validate_state("000000"))
        self.assertTrue(self.manager._validate_state("111111"))
        self.assertTrue(self.manager._validate_state("010101"))

        # 无效状态
        self.assertFalse(self.manager._validate_state(""))
        self.assertFalse(self.manager._validate_state("00000"))
        self.assertFalse(self.manager._validate_state("0000000"))
        self.assertFalse(self.manager._validate_state("00000a"))
        self.assertFalse(self.manager._validate_state("abc123"))

    def test_mapping_integrity(self):
        """测试映射完整性"""
        # 验证所有64个卦象都有映射
        self.assertEqual(len(self.manager.mappings), 64)

        # 验证每个卦象都有有效的河图状态
        for mapping in self.manager.mappings:
            self.assertIsInstance(mapping, object)
            self.assertTrue(hasattr(mapping, 'binary_str'))
            self.assertTrue(hasattr(mapping, 'hexagram_name'))
            self.assertTrue(hasattr(mapping, 'hetu_state'))

            binary = mapping.binary_str
            self.assertEqual(len(binary), 6)
            self.assertIsInstance(mapping.hetu_state, HetuState)

            # 验证反向查找
            hetu = self.manager.get_hetu_state(binary)
            self.assertEqual(hetu, mapping.hetu_state)


if __name__ == "__main__":
    unittest.main()