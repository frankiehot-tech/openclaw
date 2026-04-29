"""
Test MiniCPM Router - 测试视觉路由决策

覆盖场景：
1. OCR 高置信命中时不调用 MiniCPM
2. OCR miss 时调用 MiniCPM
3. MiniCPM 返回 target 后可转为 action
4. 仅指定任务启用 MiniCPM
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 设置测试环境变量
os.environ["VISION_USE_MINICPM"] = "true"
os.environ["MINICPM_MODE"] = "mock"

from vision.minicpm_client import MiniCPMClient, MiniCPMResult
from vision.vision_router import (
    MINICPM_ENABLED_TASKS,
    VisionRouteDecision,
    VisionRouter,
    get_vision_router,
    route_vision_analysis,
    should_use_minicpm,
)


class TestMiniCPMRouter(unittest.TestCase):
    """测试 MiniCPM 路由决策"""

    def setUp(self):
        """测试前准备"""
        self.router = VisionRouter()

    def test_ocr_high_confidence_no_minicpm(self):
        """测试 1: OCR 高置信命中时不调用 MiniCPM"""
        # OCR 高置信结果 - 使用白名单中的任务
        ocr_result = {
            "text": "搜索",
            "confidence": 0.9,
            "center": [540, 200],
            "element_type": "search_box",
        }

        # 判断是否使用 MiniCPM - 使用白名单中的任务
        should_use, reason = self.router.should_use_minicpm("点击搜索", ocr_result)

        self.assertFalse(should_use)
        self.assertIn("OCR 高置信度命中", reason)

        print(f"✓ OCR 高置信: should_use={should_use}, reason={reason}")

    def test_ocr_low_confidence_with_minicpm(self):
        """测试 2: OCR 低置信时调用 MiniCPM"""
        # OCR 低置信结果
        ocr_result = {
            "text": "搜索",
            "confidence": 0.5,
            "center": [540, 150],
            "element_type": "search_box",
        }

        # 判断是否使用 MiniCPM
        should_use, reason = self.router.should_use_minicpm("点击搜索", ocr_result)

        self.assertTrue(should_use)
        self.assertIn("复杂 UI", reason)

        print(f"✓ OCR 低置信 + 复杂 UI: should_use={should_use}, reason={reason}")

    def test_ocr_miss_calls_minicpm(self):
        """测试 3: OCR 未命中时调用 MiniCPM"""
        # 无 OCR 结果
        ocr_result = None

        # 判断是否使用 MiniCPM
        should_use, reason = self.router.should_use_minicpm("点击搜索", ocr_result)

        self.assertTrue(should_use)

        print(f"✓ OCR miss: should_use={should_use}, reason={reason}")

    def test_task_not_in_whitelist(self):
        """测试 4: 任务不在白名单不调用 MiniCPM"""
        # 不在白名单的任务
        should_use, reason = self.router.should_use_minicpm("打开相机", None)  # 不在白名单

        self.assertFalse(should_use)
        self.assertIn("不在 MiniCPM 启用列表", reason)

        print(f"✓ 任务不在白名单: should_use={should_use}, reason={reason}")

    def test_minicpm_disabled(self):
        """测试 5: MiniCPM 未启用时不调用"""
        # 临时禁用 MiniCPM
        with patch("vision.vision_router.VISION_USE_MINICPM", False):
            should_use, reason = self.router.should_use_minicpm("点击搜索", None)

            self.assertFalse(should_use)
            self.assertIn("未启用", reason)

        print("✓ MiniCPM 未启用时不调用")

    def test_minicpm_unavailable(self):
        """测试 6: MiniCPM 不可用时不调用"""
        # 临时设置 MiniCPM 不可用
        with patch("vision.vision_router.is_minicpm_available", return_value=False):
            should_use, reason = self.router.should_use_minicpm("点击搜索", None)

            self.assertFalse(should_use)
            self.assertIn("不可用", reason)

        print("✓ MiniCPM 不可用时不调用")


class TestMiniCPMRouterFullFlow(unittest.TestCase):
    """测试完整路由流程"""

    def setUp(self):
        """测试前准备"""
        self.router = VisionRouter()

    def test_click_search_task(self):
        """测试 7: 点击搜索任务使用 MiniCPM"""
        decision = self.router.route_vision_analysis(
            "/fake/screen.png", "点击搜索", ocr_result=None, state_result=None
        )

        self.assertTrue(decision.use_minicpm)
        self.assertEqual(decision.source, "minicpm_vision")
        self.assertIsNotNone(decision.minicpm_result)
        self.assertEqual(decision.minicpm_result.target_type, "search_box")

        print(f"✓ 点击搜索: use_minicpm={decision.use_minicpm}, source={decision.source}")
        print(f"  target_type={decision.minicpm_result.target_type}")

    def test_open_wifi_page(self):
        """测试 8: 打开 Wi-Fi 页面使用 MiniCPM"""
        decision = self.router.route_vision_analysis(
            "/fake/screen.png", "打开Wi-Fi页面", ocr_result=None, state_result=None
        )

        self.assertTrue(decision.use_minicpm)
        self.assertEqual(decision.source, "minicpm_vision")
        self.assertIsNotNone(decision.minicpm_result)

        print(f"✓ 打开Wi-Fi页面: use_minicpm={decision.use_minicpm}")
        print(f"  target_label={decision.minicpm_result.target_label}")

    def test_open_bluetooth_page(self):
        """测试 9: 打开蓝牙页面使用 MiniCPM"""
        decision = self.router.route_vision_analysis(
            "/fake/screen.png", "打开蓝牙页面", ocr_result=None, state_result=None
        )

        self.assertTrue(decision.use_minicpm)
        self.assertEqual(decision.source, "minicpm_vision")
        self.assertIsNotNone(decision.minicpm_result)

        print(f"✓ 打开蓝牙页面: use_minicpm={decision.use_minicpm}")
        print(f"  target_label={decision.minicpm_result.target_label}")

    def test_ocr_high_confidence_uses_ocr(self):
        """测试 10: OCR 高置信时使用 OCR 结果"""
        ocr_result = {
            "text": "设置",
            "confidence": 0.9,
            "center": [540, 200],
            "element_type": "text",
        }

        decision = self.router.route_vision_analysis(
            "/fake/screen.png",
            "打开设置",  # 不在 MiniCPM 白名单
            ocr_result=ocr_result,
            state_result=None,
        )

        self.assertFalse(decision.use_minicpm)
        self.assertEqual(decision.source, "ocr_grounding")

        print(f"✓ OCR 高置信使用 OCR: source={decision.source}")

    def test_minicpm_result_to_action(self):
        """测试 11: MiniCPM 结果可转为 action"""
        decision = self.router.route_vision_analysis(
            "/fake/screen.png", "点击搜索", ocr_result=None, state_result=None
        )

        # 检查 suggested_action
        self.assertIsNotNone(decision.suggested_action)
        self.assertEqual(decision.suggested_action["action"], "tap")
        self.assertIn("x", decision.suggested_action["params"])
        self.assertIn("y", decision.suggested_action["params"])

        print(f"✓ MiniCPM 结果转 action: {decision.suggested_action}")

    def test_minicpm_result_to_grounding(self):
        """测试 12: MiniCPM 结果可转为 grounding"""
        decision = self.router.route_vision_analysis(
            "/fake/screen.png", "点击搜索", ocr_result=None, state_result=None
        )

        # 检查 grounding_target
        self.assertIsNotNone(decision.grounding_target)
        self.assertEqual(decision.grounding_target["source"], "minicpm_vision")
        self.assertIn("center", decision.grounding_target)

        print(f"✓ MiniCPM 结果转 grounding: source={decision.grounding_target['source']}")


class TestVisionRouterContext(unittest.TestCase):
    """测试路由上下文"""

    def setUp(self):
        """测试前准备"""
        self.router = VisionRouter()

    def test_add_to_context(self):
        """测试 13: 决策结果添加到上下文"""
        decision = self.router.route_vision_analysis(
            "/fake/screen.png", "点击搜索", ocr_result=None, state_result=None
        )

        context = {}
        context = decision.add_to_context(context)

        # 检查新增字段
        self.assertIn("vision_route", context)
        self.assertIn("minicpm_used", context)
        self.assertIn("action_source", context)
        self.assertIn("minicpm_page_type", context)
        self.assertIn("minicpm_target_type", context)
        self.assertIn("minicpm_confidence", context)

        print(f"✓ 上下文字段: {list(context.keys())}")

    def test_decision_to_dict(self):
        """测试 14: 决策可序列化为字典"""
        decision = self.router.route_vision_analysis(
            "/fake/screen.png", "点击搜索", ocr_result=None, state_result=None
        )

        decision_dict = decision.to_dict()

        self.assertIsInstance(decision_dict, dict)
        self.assertIn("use_minicpm", decision_dict)
        self.assertIn("source", decision_dict)

        print(f"✓ 决策序列化: keys={list(decision_dict.keys())}")


class TestMiniCPMEnabledTasks(unittest.TestCase):
    """测试 MiniCPM 启用任务列表"""

    def test_enabled_tasks(self):
        """测试 15: 验证启用任务列表"""
        expected_tasks = {
            "点击搜索",
            "打开Wi-Fi页面",
            "打开Wi-Fi",
            "打开蓝牙页面",
            "打开蓝牙",
            "搜索",
            "search",
        }

        self.assertEqual(MINICPM_ENABLED_TASKS, expected_tasks)

        print(f"✓ 启用任务列表: {MINICPM_ENABLED_TASKS}")

    def test_task_matching(self):
        """测试 16: 任务匹配逻辑"""
        router = VisionRouter()

        # 精确匹配
        self.assertTrue(router._is_minicpm_enabled_task("点击搜索"))

        # 模糊匹配
        self.assertTrue(router._is_minicpm_enabled_task("打开Wi-Fi"))
        self.assertTrue(router._is_minicpm_enabled_task("打开蓝牙"))

        # 不匹配
        self.assertFalse(router._is_minicpm_enabled_task("打开相机"))

        print("✓ 任务匹配逻辑正确")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("MiniCPM Router 测试")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMiniCPMRouter))
    suite.addTests(loader.loadTestsFromTestCase(TestMiniCPMRouterFullFlow))
    suite.addTests(loader.loadTestsFromTestCase(TestVisionRouterContext))
    suite.addTests(loader.loadTestsFromTestCase(TestMiniCPMEnabledTasks))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印总结
    print("\n" + "=" * 60)
    print(
        f"测试结果: {result.testsRun} 个测试, {len(result.failures)} 失败, {len(result.errors)} 错误"
    )
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
