#!/usr/bin/env python3
"""
河图到64卦适配器单元测试
测试HetuToHexagramAdapter的API兼容性和功能
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hetu_hexagram_adapter import HetuToHexagramAdapter, TaskStateRecord  # noqa: E402
from integrated_hexagram_state_manager import HetuState  # noqa: E402


class TestHetuToHexagramAdapter(unittest.TestCase):
    """河图到64卦适配器测试类"""

    def setUp(self):
        """测试前置设置"""
        # 使用临时映射文件（复制项目中的映射文件）
        self.mapping_file = "hetu_hexagram_mapping.json"
        self.assertTrue(os.path.exists(self.mapping_file), f"映射文件不存在: {self.mapping_file}")

        # 创建临时状态文件
        self.temp_state_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name

        # 创建适配器实例
        self.adapter = HetuToHexagramAdapter(
            mapping_file_path=self.mapping_file, state_file=self.temp_state_file
        )

    def tearDown(self):
        """测试后清理"""
        # 删除临时状态文件
        if os.path.exists(self.temp_state_file):
            os.unlink(self.temp_state_file)

    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.adapter.hexagram_manager)
        self.assertEqual(self.adapter.state_file, self.temp_state_file)
        self.assertEqual(len(self.adapter.hetu_to_hexagrams), 10)  # 10个河图状态

        # 测试每个河图状态都有对应的卦象集合
        for state in HetuState:
            hexagrams = self.adapter.hetu_to_hexagrams.get(state)
            self.assertIsNotNone(hexagrams)
            self.assertGreater(len(hexagrams), 0)

    def test_new_task_transition(self):
        """测试新任务状态转移"""
        task_id = "test_task_001"

        # 新任务从INITIAL到AST_PARSED
        success = self.adapter.transition(task_id, HetuState.INITIAL, HetuState.AST_PARSED)
        self.assertTrue(success)

        # 验证任务状态已创建
        self.assertIn(task_id, self.adapter.task_states)
        record = self.adapter.task_states[task_id]
        self.assertEqual(record.task_id, task_id)
        self.assertEqual(len(record.state_history), 1)
        self.assertEqual(len(record.hetu_history), 1)
        self.assertEqual(record.hetu_history[0], HetuState.AST_PARSED)  # 记录目标状态，不是起始状态

        # 验证当前卦象状态
        hexagram = self.adapter.get_task_hexagram_state(task_id)
        self.assertIsNotNone(hexagram)
        self.assertEqual(len(hexagram), 6)  # 6位二进制

    def test_continuation_transition(self):
        """测试连续状态转移"""
        task_id = "test_task_002"

        # 第一步：INITIAL -> AST_PARSED
        success = self.adapter.transition(task_id, HetuState.INITIAL, HetuState.AST_PARSED)
        self.assertTrue(success)

        # 第二步：AST_PARSED -> COMPLETED
        success = self.adapter.transition(task_id, HetuState.AST_PARSED, HetuState.COMPLETED)
        self.assertTrue(success)

        # 验证状态记录
        record = self.adapter.task_states[task_id]
        self.assertEqual(len(record.state_history), 2)  # 两个卦象状态
        self.assertEqual(len(record.hetu_history), 2)  # 两个河图状态
        self.assertEqual(record.hetu_history[0], HetuState.AST_PARSED)  # 第一次转换的目标状态
        self.assertEqual(record.hetu_history[1], HetuState.COMPLETED)  # 第二次转换的目标状态

        # 验证当前河图状态
        current_hetu = self.adapter.get_task_hetu_state(task_id)
        self.assertEqual(current_hetu, HetuState.COMPLETED)

    def test_get_next_states(self):
        """测试获取可能的下一状态（兼容API）"""
        # 从INITIAL开始
        next_states = self.adapter.get_next_states(HetuState.INITIAL)
        self.assertGreater(len(next_states), 0)

        # 验证状态顺序（应该按值排序）
        for i in range(len(next_states) - 1):
            self.assertLess(next_states[i].value, next_states[i + 1].value)

        # 最终状态应该没有下一状态
        next_states = self.adapter.get_next_states(HetuState.COMPLETED)
        self.assertEqual(len(next_states), 0)

    def test_get_shortest_path(self):
        """测试获取最短路径（兼容API）"""
        # 从INITIAL到COMPLETED
        path = self.adapter.get_shortest_path(HetuState.INITIAL, HetuState.COMPLETED)
        self.assertGreater(len(path), 0)

        # 验证路径起点和终点
        self.assertEqual(path[0], HetuState.INITIAL)
        self.assertEqual(path[-1], HetuState.COMPLETED)

        # 验证路径顺序
        for i in range(len(path) - 1):
            self.assertLess(path[i].value, path[i + 1].value)

        # 无效路径（反向）
        path = self.adapter.get_shortest_path(HetuState.COMPLETED, HetuState.INITIAL)
        self.assertEqual(len(path), 0)

    def test_task_state_queries(self):
        """测试任务状态查询"""
        task_id = "test_task_003"

        # 初始状态
        self.adapter.transition(task_id, HetuState.INITIAL, HetuState.INITIAL)

        # 获取卦象状态
        hexagram = self.adapter.get_task_hexagram_state(task_id)
        self.assertIsNotNone(hexagram)

        # 获取河图状态
        hetu = self.adapter.get_task_hetu_state(task_id)
        self.assertEqual(hetu, HetuState.INITIAL)

        # 不存在的任务
        self.assertIsNone(self.adapter.get_task_hexagram_state("nonexistent"))
        self.assertIsNone(self.adapter.get_task_hetu_state("nonexistent"))

    def test_state_analysis(self):
        """测试状态分析"""
        task_id = "test_task_004"

        # 创建任务并转移状态
        self.adapter.transition(task_id, HetuState.INITIAL, HetuState.AST_PARSED)

        # 分析状态
        analysis = self.adapter.analyze_task_state(task_id)
        self.assertIsNotNone(analysis)

        # 验证分析结果结构
        self.assertIsNotNone(analysis.hexagram_name)
        self.assertIsNotNone(analysis.binary_representation)
        self.assertIsInstance(analysis.quality_score, float)
        self.assertIsInstance(analysis.active_dimensions, list)
        self.assertIsInstance(analysis.inactive_dimensions, list)

        # 质量评分应该在0-10之间
        self.assertGreaterEqual(analysis.quality_score, 0)
        self.assertLessEqual(analysis.quality_score, 10)

    def test_state_persistence(self):
        """测试状态持久化"""
        task_id = "test_task_005"

        # 创建一些状态
        self.adapter.transition(task_id, HetuState.INITIAL, HetuState.AST_PARSED)
        self.adapter.transition(task_id, HetuState.AST_PARSED, HetuState.COMPLETED)

        # 保存状态
        self.adapter.save_states()
        self.assertTrue(os.path.exists(self.temp_state_file))

        # 创建新的适配器实例并加载状态
        new_adapter = HetuToHexagramAdapter(
            mapping_file_path=self.mapping_file, state_file=self.temp_state_file
        )

        # 验证状态已加载
        self.assertIn(task_id, new_adapter.task_states)
        record = new_adapter.task_states[task_id]

        # 验证状态历史
        self.assertEqual(len(record.state_history), 2)
        self.assertEqual(len(record.hetu_history), 2)

        # 验证当前状态
        current_hetu = new_adapter.get_task_hetu_state(task_id)
        self.assertEqual(current_hetu, HetuState.COMPLETED)

    def test_state_report(self):
        """测试状态报告"""
        task_id = "test_task_006"

        # 创建任务
        self.adapter.transition(task_id, HetuState.INITIAL, HetuState.AST_PARSED)

        # 获取状态报告
        report = self.adapter.get_state_report()
        self.assertIsInstance(report, dict)

        # 验证报告结构
        self.assertIn("total_tasks", report)
        self.assertIn("hexagram_manager", report)
        self.assertIn("task_summary", report)

        # 验证任务摘要
        self.assertIn(task_id, report["task_summary"])
        task_info = report["task_summary"][task_id]
        self.assertIn("current_hexagram", task_info)
        self.assertIn("current_hetu", task_info)
        self.assertIn("history_length", task_info)

    def test_select_nearest_hexagram(self):
        """测试选择最近卦象（内部方法）"""
        # 测试汉明距离计算
        current = "000000"
        targets = {"000001", "000010", "000100"}

        nearest = self.adapter._select_nearest_hexagram(current, targets)
        self.assertIn(nearest, targets)

        # 所有目标的汉明距离都是1，应该选择第一个（集合无序）
        # 这里只验证返回的是有效状态
        self.assertEqual(len(nearest), 6)

        # 空目标集合
        nearest = self.adapter._select_nearest_hexagram(current, set())
        self.assertEqual(nearest, current)

    def test_find_hexagram_path(self):
        """测试查找卦象路径（内部方法）"""
        # 简单的路径查找
        path = self.adapter._find_hexagram_path("000000", "000001", max_steps=5)
        self.assertEqual(len(path), 2)
        self.assertEqual(path[0], "000000")
        self.assertEqual(path[1], "000001")

        # 更复杂的路径（需要多步）
        path = self.adapter._find_hexagram_path("000000", "000011", max_steps=5)
        self.assertGreaterEqual(len(path), 2)

        # 路径不存在（超出最大步数）
        path = self.adapter._find_hexagram_path("000000", "111111", max_steps=3)
        self.assertEqual(len(path), 0)


class TestTaskStateRecord(unittest.TestCase):
    """任务状态记录测试"""

    def test_record_creation(self):
        """测试记录创建"""
        task_id = "test_record_001"
        hexagram = "000111"
        hetu_state = HetuState.AST_PARSED
        timestamp = datetime.now()

        record = TaskStateRecord(
            task_id=task_id,
            current_hexagram=hexagram,
            state_history=[hexagram],
            hetu_history=[hetu_state],
            timestamps=[timestamp],
            metadata={"test": True},
        )

        self.assertEqual(record.task_id, task_id)
        self.assertEqual(record.current_hexagram, hexagram)
        self.assertEqual(len(record.state_history), 1)
        self.assertEqual(len(record.hetu_history), 1)
        self.assertEqual(record.hetu_history[0], hetu_state)
        self.assertEqual(record.metadata["test"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
