"""
Test MiniCPM Fallback - 测试 MiniCPM 回退机制

覆盖场景：
1. MiniCPM 不可用时 graceful fallback
2. MiniCPM 返回低置信时 fallback
3. MiniCPM 未找到目标时 fallback
"""

import os
import sys
import unittest
from unittest.mock import patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 设置测试环境变量
os.environ["VISION_USE_MINICPM"] = "true"
os.environ["MINICPM_MODE"] = "mock"

from vision.minicpm_client import MiniCPMResult
from vision.vision_router import VisionRouter


class TestMiniCPMFallback(unittest.TestCase):
    """测试 MiniCPM 回退机制"""

    def setUp(self):
        """测试前准备"""
        self.router = VisionRouter()

    def test_minicpm_unavailable_fallback(self):
        """测试 1: MiniCPM 不可用时回退到 OCR"""
        # 模拟 MiniCPM 不可用
        with patch("vision.vision_router.is_minicpm_available", return_value=False):
            # 有 OCR 结果
            ocr_result = {
                "text": "设置",
                "confidence": 0.7,
                "center": [540, 200],
                "element_type": "text",
            }

            decision = self.router.route_vision_analysis(
                "/fake/screen.png", "点击搜索", ocr_result=ocr_result, state_result=None
            )

            # 应该回退到 OCR
            self.assertFalse(decision.use_minicpm)
            self.assertEqual(decision.source, "ocr_grounding")

            print(f"✓ MiniCPM 不可用回退: source={decision.source}")

    def test_minicpm_disabled_fallback(self):
        """测试 2: MiniCPM 禁用时回退"""
        # 模拟 MiniCPM 禁用
        with patch("vision.vision_router.VISION_USE_MINICPM", False):
            decision = self.router.route_vision_analysis(
                "/fake/screen.png", "点击搜索", ocr_result=None, state_result=None
            )

            # 应该回退到 model inference
            self.assertFalse(decision.use_minicpm)
            self.assertEqual(decision.source, "model_inference")

            print(f"✓ MiniCPM 禁用回退: source={decision.source}")

    def test_minicpm_low_confidence_fallback(self):
        """测试 3: MiniCPM 低置信时回退"""
        # 模拟 MiniCPM 返回低置信
        low_conf_result = MiniCPMResult(
            page_type="unknown",
            target_found=True,
            target_type="button",
            target_label="按钮",
            bbox=[100, 100, 200, 200],
            center=[150, 150],
            confidence=0.5,  # 低置信
            suggested_action={"action": "tap", "params": {"x": 150, "y": 150}},
            reason="找到目标但置信度低",
        )

        with patch("vision.vision_router.get_minicpm_client") as mock_client:
            mock_client.return_value.analyze_screen.return_value = low_conf_result

            # 有更高置信的 OCR 结果
            ocr_result = {
                "text": "搜索",
                "confidence": 0.8,  # 更高
                "center": [540, 150],
                "element_type": "search_box",
            }

            decision = self.router.route_vision_analysis(
                "/fake/screen.png", "点击搜索", ocr_result=ocr_result, state_result=None
            )

            # 应该使用 OCR（置信度更高）
            self.assertFalse(decision.use_minicpm)
            self.assertEqual(decision.source, "ocr_grounding")

            print(f"✓ MiniCPM 低置信回退到 OCR: source={decision.source}")

    def test_minicpm_not_found_fallback(self):
        """测试 4: MiniCPM 未找到目标时回退"""
        # 模拟 MiniCPM 未找到目标
        not_found_result = MiniCPMResult(
            page_type="unknown",
            target_found=False,
            target_type="",
            target_label="",
            bbox=[],
            center=[],
            confidence=0.0,
            suggested_action={"action": "none", "params": {}},
            reason="未找到目标",
        )

        with patch("vision.vision_router.get_minicpm_client") as mock_client:
            mock_client.return_value.analyze_screen.return_value = not_found_result

            decision = self.router.route_vision_analysis(
                "/fake/screen.png", "点击搜索", ocr_result=None, state_result=None
            )

            # 应该回退到 model inference
            self.assertTrue(decision.use_minicpm)  # 调用了 MiniCPM
            self.assertEqual(decision.source, "fallback")

            print(f"✓ MiniCPM 未找到目标回退: source={decision.source}")

    def test_no_ocr_no_minicpm_fallback(self):
        """测试 5: 无 OCR 无 MiniCPM 时回退到 model inference"""
        # 任务不在白名单，MiniCPM 不启用
        decision = self.router.route_vision_analysis(
            "/fake/screen.png", "打开相机", ocr_result=None, state_result=None  # 不在白名单
        )

        # 回退到 model inference
        self.assertFalse(decision.use_minicpm)
        self.assertEqual(decision.source, "model_inference")

        print(f"✓ 无 OCR 无 MiniCPM 回退: source={decision.source}")


class TestMiniCPMGracefulDegradation(unittest.TestCase):
    """测试 MiniCPM 优雅降级"""

    def setUp(self):
        """测试前准备"""
        self.router = VisionRouter()

    def test_minicpm_timeout_fallback(self):
        """测试 6: MiniCPM 超时回退"""
        # 模拟 MiniCPM 超时返回空结果
        timeout_result = MiniCPMResult(
            page_type="unknown",
            target_found=False,
            target_type="",
            target_label="",
            bbox=[],
            center=[],
            confidence=0.0,
            suggested_action={"action": "none", "params": {}},
            reason="分析失败: timeout",
        )

        with patch("vision.vision_router.get_minicpm_client") as mock_client:
            mock_client.return_value.analyze_screen.return_value = timeout_result

            # 有 OCR 结果作为后备
            ocr_result = {
                "text": "搜索",
                "confidence": 0.6,
                "center": [540, 150],
                "element_type": "search_box",
            }

            decision = self.router.route_vision_analysis(
                "/fake/screen.png", "点击搜索", ocr_result=ocr_result, state_result=None
            )

            # MiniCPM 失败（未找到目标），回退到 fallback
            # 注意：当 MiniCPM target_found=False 时，无论 OCR 是否有结果都返回 fallback
            self.assertEqual(decision.source, "fallback")

            print(f"✓ MiniCPM 超时回退: source={decision.source}")

    def test_minicpm_error_fallback(self):
        """测试 7: MiniCPM 错误回退"""
        # 模拟 MiniCPM 异常
        with patch("vision.vision_router.get_minicpm_client") as mock_client:
            mock_client.return_value.analyze_screen.side_effect = Exception("API Error")

            # 有 OCR 结果
            ocr_result = {
                "text": "搜索",
                "confidence": 0.6,
                "center": [540, 150],
                "element_type": "search_box",
            }

            decision = self.router.route_vision_analysis(
                "/fake/screen.png", "点击搜索", ocr_result=ocr_result, state_result=None
            )

            # MiniCPM 异常时，回退到 fallback（不是 ocr_grounding）
            # 因为异常发生在 MiniCPM 调用阶段，还没到比较置信度的逻辑
            self.assertEqual(decision.source, "fallback")

            print(f"✓ MiniCPM 错误回退: source={decision.source}")

    def test_confidence_threshold_protection(self):
        """测试 8: 置信度阈值保护"""
        # 模拟低于阈值的 MiniCPM 结果
        low_result = MiniCPMResult(
            page_type="browser_home",
            target_found=True,
            target_type="search_box",
            target_label="搜索",
            bbox=[450, 100, 630, 180],
            center=[540, 140],
            confidence=0.65,  # 低于阈值 0.70
            suggested_action={"action": "tap", "params": {"x": 540, "y": 140}},
            reason="找到搜索框",
        )

        with patch("vision.vision_router.get_minicpm_client") as mock_client:
            mock_client.return_value.analyze_screen.return_value = low_result

            # 无 OCR 结果
            decision = self.router.route_vision_analysis(
                "/fake/screen.png", "点击搜索", ocr_result=None, state_result=None
            )

            # MiniCPM 置信度低于阈值，但无其他选择
            # 应该使用 MiniCPM 但标记为低置信
            self.assertTrue(decision.use_minicpm)
            self.assertIn("低置信", decision.decision_reason)

            print(f"✓ 置信度阈值保护: confidence={low_result.confidence}, threshold=0.70")


class TestMiniCPMFallbackDecision(unittest.TestCase):
    """测试回退决策逻辑"""

    def setUp(self):
        """测试前准备"""
        self.router = VisionRouter()

    def test_fallback_decision_structure(self):
        """测试 9: 回退决策结构"""
        decision = self.router.route_vision_analysis(
            "/fake/screen.png", "打开相机", ocr_result=None, state_result=None  # 不在白名单
        )

        # 检查决策结构完整性
        self.assertIn("use_minicpm", decision.to_dict())
        self.assertIn("decision_reason", decision.to_dict())
        self.assertIn("source", decision.to_dict())

        print(f"✓ 回退决策结构: {decision.to_dict().keys()}")

    def test_fallback_with_ocr_context(self):
        """测试 10: 回退时保留 OCR 上下文"""
        ocr_result = {
            "text": "设置",
            "confidence": 0.7,
            "center": [540, 200],
            "element_type": "text",
        }

        # MiniCPM 不可用
        with patch("vision.vision_router.is_minicpm_available", return_value=False):
            decision = self.router.route_vision_analysis(
                "/fake/screen.png", "打开设置", ocr_result=ocr_result, state_result=None
            )

            # 检查 OCR 置信度保留
            self.assertEqual(decision.ocr_confidence, 0.7)

            print(f"✓ 回退保留 OCR 上下文: ocr_confidence={decision.ocr_confidence}")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("MiniCPM Fallback 测试")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMiniCPMFallback))
    suite.addTests(loader.loadTestsFromTestCase(TestMiniCPMGracefulDegradation))
    suite.addTests(loader.loadTestsFromTestCase(TestMiniCPMFallbackDecision))

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
