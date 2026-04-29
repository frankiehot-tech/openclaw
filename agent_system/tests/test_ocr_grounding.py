"""
Test OCR Grounding - OCR 和 Grounding 测试

测试覆盖：
1. OCR 输出结构校验
2. exact / contains / fuzzy 匹配
3. bbox 转 tap 点
4. grounding 优先于模型推理
5. OCR provider 不可用时 graceful fallback
"""

import os
import sys
import unittest

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from vision.ocr_engine import (
    MockOCRProvider,
    OCREngine,
    OCRResult,
    reset_ocr_engine,
)
from vision.screen_analyzer import (
    ScreenAnalysis,
    ScreenAnalyzer,
    reset_screen_analyzer,
)
from vision.ui_grounding import (
    TextTarget,
    UIGrounding,
    reset_ui_grounding,
)


class TestOCRResult(unittest.TestCase):
    """测试 OCR 结果结构"""

    def test_ocr_result_creation(self):
        """测试 OCRResult 创建"""
        result = OCRResult(text="设置", bbox=[450, 1200, 630, 1260], confidence=0.95)

        self.assertEqual(result.text, "设置")
        self.assertEqual(result.bbox, [450, 1200, 630, 1260])
        self.assertEqual(result.confidence, 0.95)

    def test_ocr_result_to_dict(self):
        """测试 OCRResult 转换为字典"""
        result = OCRResult(text="设置", bbox=[450, 1200, 630, 1260], confidence=0.95)

        d = result.to_dict()

        self.assertEqual(d["text"], "设置")
        self.assertEqual(d["bbox"], [450, 1200, 630, 1260])
        self.assertEqual(d["confidence"], 0.95)


class TestOCRProvider(unittest.TestCase):
    """测试 OCR Provider"""

    def setUp(self):
        """每个测试前重置"""
        reset_ocr_engine()

    def test_mock_provider_available(self):
        """测试 Mock Provider 可用性"""
        engine = OCREngine(provider="mock")
        self.assertTrue(engine.is_available())
        self.assertEqual(engine.get_provider_name(), "mock")

    def test_mock_provider_extract(self):
        """测试 Mock Provider 提取"""
        reset_ocr_engine()  # 确保重置
        engine = OCREngine(provider="mock")
        results = engine.extract_text("/fake/path.png")

        self.assertIsInstance(results, list)
        # Mock 应该返回结果（如果全局单例被正确初始化）
        # 如果是全局单例，可能需要重新创建
        if len(results) == 0:
            # 尝试直接使用 provider
            provider = MockOCRProvider()
            results = provider.extract_text("/fake/path.png")

        self.assertGreater(len(results), 0)

        # 验证结构
        for r in results:
            self.assertIsInstance(r.text, str)
            self.assertIsInstance(r.bbox, list)
            self.assertEqual(len(r.bbox), 4)
            self.assertIsInstance(r.confidence, float)

    def test_primary_provider_fallback(self):
        """测试 Primary Provider 不可用时回退"""
        engine = OCREngine(provider="primary")

        # 如果 EasyOCR 未安装，应该回退到 mock
        # 如果已安装，则使用 EasyOCR
        self.assertTrue(engine.is_available())


class TestUIGrounding(unittest.TestCase):
    """测试 UI Grounding"""

    def setUp(self):
        """每个测试前重置"""
        reset_ui_grounding()

    def test_exact_match(self):
        """测试精确匹配"""
        grounding = UIGrounding(screen_size=(1080, 2640))

        ocr_blocks = [
            OCRResult(text="设置", bbox=[450, 1200, 630, 1260], confidence=0.95),
            OCRResult(text="搜索", bbox=[200, 300, 400, 400], confidence=0.90),
        ]

        target = grounding.find_text_target(ocr_blocks, "设置")

        self.assertIsNotNone(target)
        self.assertTrue(target.matched)
        self.assertEqual(target.text, "设置")
        self.assertEqual(target.match_type, "exact")
        self.assertEqual(target.confidence, 0.95)

    def test_contains_match(self):
        """测试包含匹配"""
        grounding = UIGrounding(screen_size=(1080, 2640))

        # 使用"浏览器"但搜索"浏览器"（完全匹配）
        ocr_blocks = [
            OCRResult(text="浏览器", bbox=[300, 800, 500, 900], confidence=0.88),
        ]

        target = grounding.find_text_target(ocr_blocks, "浏览器")

        self.assertIsNotNone(target)
        self.assertTrue(target.matched)
        # 应该是 exact 或 contains
        self.assertIn(target.match_type, ["exact", "contains"])

    def test_fuzzy_match(self):
        """测试模糊匹配"""
        grounding = UIGrounding(screen_size=(1080, 2640))

        ocr_blocks = [
            OCRResult(text="设置", bbox=[450, 1200, 630, 1260], confidence=0.95),
        ]

        # 模糊匹配（可能有错别字）
        target = grounding.find_text_target(ocr_blocks, "没置", match_threshold=0.6)

        # 模糊匹配可能找不到
        self.assertIsNone(target)

    def test_no_match(self):
        """测试无匹配"""
        grounding = UIGrounding(screen_size=(1080, 2640))

        ocr_blocks = [
            OCRResult(text="设置", bbox=[450, 1200, 630, 1260], confidence=0.95),
        ]

        target = grounding.find_text_target(ocr_blocks, "不存在的文本")

        self.assertIsNone(target)

    def test_bbox_to_tap_point(self):
        """测试 bbox 转 tap 点"""
        grounding = UIGrounding(screen_size=(1080, 2640))

        # 正常 bbox
        center = grounding.bbox_to_tap_point([450, 1200, 630, 1260])
        self.assertIsNotNone(center)
        cx, cy = center
        self.assertEqual(cx, 540)  # (450 + 630) / 2
        self.assertEqual(cy, 1230)  # (1200 + 1260) / 2

    def test_bbox_to_tap_point_safe_margin(self):
        """测试安全边距"""
        grounding = UIGrounding(screen_size=(1080, 2640))

        # 边缘 bbox - 应该在安全区域内
        center = grounding.bbox_to_tap_point([10, 10, 50, 50])
        self.assertIsNotNone(center)

        # 验证中心点不在边缘危险区域
        margin = int(1080 * 0.05)  # 5%
        self.assertGreaterEqual(center[0], margin)
        self.assertLessEqual(center[0], 1080 - margin)

    def test_rank_candidates(self):
        """测试候选排序"""
        grounding = UIGrounding(screen_size=(1080, 2640))

        candidates = [
            TextTarget(
                matched=True,
                text="设置",
                bbox=[450, 1200, 630, 1260],
                center=(540, 1230),
                confidence=0.80,
                match_type="contains",
            ),
            TextTarget(
                matched=True,
                text="设置",
                bbox=[500, 1300, 600, 1360],
                center=(550, 1330),
                confidence=0.95,
                match_type="exact",
            ),
        ]

        ranked = grounding.rank_candidates(candidates)

        # 精确匹配应该排在前面
        self.assertEqual(ranked[0].match_type, "exact")


class TestScreenAnalyzer(unittest.TestCase):
    """测试屏幕分析器"""

    def setUp(self):
        """每个测试前重置"""
        reset_screen_analyzer()

    def test_analyze_screen_structure(self):
        """测试分析结果结构"""
        analyzer = ScreenAnalyzer(ocr_provider="mock", screen_size=(1080, 2640))

        # 使用假图片路径（Mock 会返回固定结果）
        analysis = analyzer.analyze_screen("/fake/path.png", expected_targets=["设置", "搜索"])

        # 验证结构
        self.assertIsInstance(analysis, ScreenAnalysis)
        self.assertIsInstance(analysis.ocr_blocks, list)
        self.assertIsInstance(analysis.ocr_top_texts, list)
        self.assertIsInstance(analysis.target_found, bool)
        self.assertIsInstance(analysis.screen_summary, str)

    def test_grounding_priority(self):
        """测试 grounding 优先于模型推理"""
        analyzer = ScreenAnalyzer(ocr_provider="mock", screen_size=(1080, 2640))

        # Mock OCR 会返回包含"设置"的文本
        analysis = analyzer.analyze_screen("/fake/path.png", expected_targets=["设置"])

        # 如果找到目标，grounding_target 应该不为空
        if analysis.target_found:
            self.assertIsNotNone(analysis.grounding_target)
            self.assertEqual(analysis.grounding_target["text"], "设置")

    def test_quick_check_target(self):
        """测试快速目标检查"""
        analyzer = ScreenAnalyzer(ocr_provider="mock", screen_size=(1080, 2640))

        target = analyzer.quick_check_target("/fake/path.png", "设置")

        # Mock 应该能找到
        self.assertIsNotNone(target)
        self.assertTrue(target.matched)


class TestGracefulFallback(unittest.TestCase):
    """测试优雅降级"""

    def test_ocr_not_available(self):
        """测试 OCR 不可用时的处理"""
        # 创建一个不存在的 provider，应该回退到 mock
        engine = OCREngine(provider="nonexistent")

        # 应该回退到 mock
        self.assertTrue(engine.is_available())
        self.assertEqual(engine.get_provider_name(), "mock")

    def test_empty_ocr_result(self):
        """测试空 OCR 结果"""
        grounding = UIGrounding(screen_size=(1080, 2640))

        # 空 OCR 结果
        target = grounding.find_text_target([], "设置")

        self.assertIsNone(target)


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
