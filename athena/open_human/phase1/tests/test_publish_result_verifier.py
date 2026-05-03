"""
Test Publish Result Verifier for Phase 1

测试发布结果核验器功能。
"""

import os
import sys
import unittest

# 添加路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from athena.open_human.phase1.states.page_state_schema import Phase1PageState
from athena.open_human.phase1.verification.publish_result_verifier import (
    PublishResultVerifier,
    PublishVerificationResult,
    VerificationResult,
    verify_publish_result,
)


class TestPublishResultVerifier(unittest.TestCase):
    """测试发布结果核验器"""

    def setUp(self):
        """设置测试环境"""
        self.verifier = PublishResultVerifier()
        self.vision_text = "这是一个测试页面"
        self.ui_anchors = ["按钮1", "按钮2"]

    def test_publish_success_to_success(self):
        """测试 PUBLISH_SUCCESS -> success"""
        result = self.verifier.verify(
            page_state=Phase1PageState.PUBLISH_SUCCESS.value,
            vision_text="发布成功，内容已发送",
            ui_anchors=["发布成功", "返回首页"],
        )

        self.assertEqual(result.result, VerificationResult.SUCCESS.value)
        self.assertEqual(result.page_state, Phase1PageState.PUBLISH_SUCCESS.value)
        self.assertGreater(len(result.evidence), 0)
        self.assertIsNone(result.taxonomy_class)
        self.assertIsNone(result.sub_reason)

    def test_publish_failure_to_fail(self):
        """测试 PUBLISH_FAILURE -> fail"""
        result = self.verifier.verify(
            page_state=Phase1PageState.PUBLISH_FAILURE.value,
            vision_text="发布失败，网络异常",
            ui_anchors=["发布失败", "重试"],
        )

        self.assertEqual(result.result, VerificationResult.FAIL.value)
        self.assertEqual(result.page_state, Phase1PageState.PUBLISH_FAILURE.value)
        self.assertEqual(result.taxonomy_class, "action_failed")
        self.assertEqual(result.sub_reason, "publish_failure_page")
        self.assertGreater(len(result.evidence), 0)

    def test_risk_prompt_to_safe_stop(self):
        """测试 RISK_PROMPT -> safe_stop"""
        result = self.verifier.verify(
            page_state=Phase1PageState.RISK_PROMPT.value,
            vision_text="风险提示：操作异常",
            ui_anchors=["风险提示", "取消"],
        )

        self.assertEqual(result.result, VerificationResult.SAFE_STOP.value)
        self.assertEqual(result.page_state, Phase1PageState.RISK_PROMPT.value)
        self.assertEqual(result.taxonomy_class, "unsafe_to_continue")
        self.assertEqual(result.sub_reason, "risk_prompt_detected")
        self.assertGreater(len(result.evidence), 0)

    def test_unknown_with_risk_keywords_to_safe_stop(self):
        """测试 UNKNOWN + 风险关键词 -> safe_stop"""
        result = self.verifier.verify(
            page_state=Phase1PageState.UNKNOWN.value,
            vision_text="当前页面显示风险提示，请稍后再试",
            ui_anchors=["风险提示", "安全验证"],
        )

        self.assertEqual(result.result, VerificationResult.SAFE_STOP.value)
        self.assertEqual(result.page_state, Phase1PageState.UNKNOWN.value)
        self.assertEqual(result.taxonomy_class, "unsafe_to_continue")
        self.assertEqual(result.sub_reason, "unknown_sensitive_page")
        self.assertGreater(len(result.evidence), 0)
        # 证据应包含检测到的关键词
        self.assertIn("UNKNOWN 状态检测到高风险关键词", " ".join(result.evidence))

    def test_unknown_without_keywords_to_safe_stop(self):
        """测试 UNKNOWN 且无明显成功信号 -> 不得判 success"""
        result = self.verifier.verify(
            page_state=Phase1PageState.UNKNOWN.value,
            vision_text="普通页面内容",
            ui_anchors=["普通按钮"],
        )

        # UNKNOWN 状态必须判为 safe_stop，不能是 success
        self.assertEqual(result.result, VerificationResult.SAFE_STOP.value)
        self.assertEqual(result.page_state, Phase1PageState.UNKNOWN.value)
        self.assertEqual(result.taxonomy_class, "unsafe_to_continue")
        self.assertIn(
            "unknown", result.sub_reason.lower()
        )  # sub_reason 应包含 unknown（不区分大小写）
        self.assertGreater(len(result.evidence), 0)

    def test_unknown_with_success_keywords_still_safe_stop(self):
        """测试 UNKNOWN + 成功关键词 -> 仍判 safe_stop (保守策略)"""
        result = self.verifier.verify(
            page_state=Phase1PageState.UNKNOWN.value,
            vision_text="发布成功，操作完成",
            ui_anchors=["成功", "完成"],
        )

        # 即使有成功关键词，UNKNOWN 状态也不能判为 success
        self.assertEqual(result.result, VerificationResult.SAFE_STOP.value)
        self.assertEqual(result.page_state, Phase1PageState.UNKNOWN.value)
        self.assertEqual(result.taxonomy_class, "unsafe_to_continue")
        self.assertIn("unknown", result.sub_reason.lower())
        self.assertGreater(len(result.evidence), 0)
        # 证据应提及成功关键词但不判 success
        evidence_text = " ".join(result.evidence)
        self.assertIn("成功关键词", evidence_text)
        self.assertIn("不允许判为 success", evidence_text)

    def test_other_page_state_to_safe_stop(self):
        """测试其他页面状态 -> safe_stop (保守策略)"""
        other_states = [
            Phase1PageState.DRAFT_EDIT.value,
            Phase1PageState.APP_HOME.value,
            Phase1PageState.ACCOUNT_HOME.value,
            Phase1PageState.CREATE_ENTRY.value,
            Phase1PageState.PRE_PUBLISH_REVIEW.value,
            Phase1PageState.LOGIN_REQUIRED.value,
            Phase1PageState.OUT_OF_SCOPE.value,
        ]

        for state in other_states:
            with self.subTest(page_state=state):
                result = self.verifier.verify(
                    page_state=state, vision_text="页面内容", ui_anchors=["按钮"]
                )

                self.assertEqual(result.result, VerificationResult.SAFE_STOP.value)
                self.assertEqual(result.page_state, state)
                self.assertEqual(result.taxonomy_class, "unsafe_to_continue")
                self.assertEqual(result.sub_reason, "non_result_page_state")
                self.assertGreater(len(result.evidence), 0)

    def test_fail_and_safe_stop_have_taxonomy_class(self):
        """测试 fail 和 safe_stop 时 taxonomy_class 不为空"""
        # fail 情况
        fail_result = self.verifier.verify(
            page_state=Phase1PageState.PUBLISH_FAILURE.value, vision_text="发布失败", ui_anchors=[]
        )
        self.assertIsNotNone(fail_result.taxonomy_class)
        self.assertIsNotNone(fail_result.sub_reason)

        # safe_stop 情况
        safe_stop_result = self.verifier.verify(
            page_state=Phase1PageState.RISK_PROMPT.value, vision_text="风险提示", ui_anchors=[]
        )
        self.assertIsNotNone(safe_stop_result.taxonomy_class)
        self.assertIsNotNone(safe_stop_result.sub_reason)

    def test_evidence_not_empty(self):
        """测试证据非空"""
        test_cases = [
            (Phase1PageState.PUBLISH_SUCCESS.value, "发布成功"),
            (Phase1PageState.PUBLISH_FAILURE.value, "发布失败"),
            (Phase1PageState.RISK_PROMPT.value, "风险提示"),
            (Phase1PageState.UNKNOWN.value, "未知页面"),
        ]

        for page_state, vision_text in test_cases:
            with self.subTest(page_state=page_state):
                result = self.verifier.verify(
                    page_state=page_state, vision_text=vision_text, ui_anchors=["测试"]
                )
                self.assertGreater(len(result.evidence), 0)
                # 证据不能是空列表或空字符串
                for evidence_item in result.evidence:
                    self.assertIsInstance(evidence_item, str)
                    self.assertGreater(len(evidence_item.strip()), 0)

    def test_invalid_page_state_raises_error(self):
        """测试无效页面状态抛出异常"""
        with self.assertRaises(ValueError):
            self.verifier.verify(page_state="INVALID_STATE", vision_text="测试", ui_anchors=[])

    def test_convenience_function(self):
        """测试便捷函数 verify_publish_result"""
        result = verify_publish_result(
            page_state=Phase1PageState.PUBLISH_SUCCESS.value,
            vision_text="发布成功",
            ui_anchors=["成功"],
        )

        self.assertIsInstance(result, PublishVerificationResult)
        self.assertEqual(result.result, VerificationResult.SUCCESS.value)
        self.assertEqual(result.page_state, Phase1PageState.PUBLISH_SUCCESS.value)


if __name__ == "__main__":
    # 支持直接运行测试
    unittest.main()
