"""
Test Page State Classifier for Phase 1

测试 Phase 1 页面状态分类器功能。
"""

import os
import sys
import unittest

# 添加路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from athena.open_human.phase1.states.page_state_classifier import (
    PageStateClassifier,
    PageStateResult,
    classify_page_state,
)
from athena.open_human.phase1.states.page_state_schema import Phase1PageState


class TestPageStateClassifier(unittest.TestCase):
    """测试页面状态分类器"""

    def setUp(self):
        """设置测试环境"""
        self.classifier = PageStateClassifier()
        self.app_package = "com.example.app"

    def test_draft_edit_recognition(self):
        """测试识别 DRAFT_EDIT 状态"""
        result = self.classifier.classify(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text="请输入标题和正文内容，这里是草稿编辑页面",
            ui_anchors=["标题", "正文", "保存草稿"],
        )

        self.assertEqual(result.page_state, Phase1PageState.DRAFT_EDIT.value)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertGreater(len(result.evidence), 0)

    def test_pre_publish_review_recognition(self):
        """测试识别 PRE_PUBLISH_REVIEW 状态"""
        result = self.classifier.classify(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text="发布前确认，请检查内容是否正确",
            ui_anchors=["确认发布", "预览", "发布"],
        )

        self.assertEqual(result.page_state, Phase1PageState.PRE_PUBLISH_REVIEW.value)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertGreater(len(result.evidence), 0)

    def test_risk_prompt_recognition(self):
        """测试识别 RISK_PROMPT 状态"""
        result = self.classifier.classify(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text="风险提示：检测到异常操作，请稍后再试",
            ui_anchors=["安全验证", "风险提示"],
        )

        self.assertEqual(result.page_state, Phase1PageState.RISK_PROMPT.value)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertGreater(len(result.evidence), 0)

    def test_out_of_scope_when_package_mismatch(self):
        """测试包名不匹配时输出 OUT_OF_SCOPE"""
        result = self.classifier.classify(
            app_package=self.app_package,
            current_package="com.other.app",  # 不同的包名
            vision_text="任何文本内容",
            ui_anchors=["任何锚点"],
        )

        self.assertEqual(result.page_state, Phase1PageState.OUT_OF_SCOPE.value)
        self.assertEqual(result.confidence, 1.0)  # 包名不匹配置信度应为 1.0
        self.assertIn("package_mismatch", result.evidence[0])

    def test_login_required_recognition(self):
        """测试识别 LOGIN_REQUIRED 状态"""
        result = self.classifier.classify(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text="请登录您的账号，输入手机号和验证码",
            ui_anchors=["登录", "手机号", "验证码"],
        )

        self.assertEqual(result.page_state, Phase1PageState.LOGIN_REQUIRED.value)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertGreater(len(result.evidence), 0)

    def test_unknown_when_no_keywords(self):
        """测试未命中任何关键词时输出 UNKNOWN 或 APP_HOME"""
        result = self.classifier.classify(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text="这是一些随机文本，没有特定关键词",
            ui_anchors=["随机锚点"],
        )

        # 可能是 UNKNOWN 或 APP_HOME，取决于文本长度
        self.assertIn(
            result.page_state, [Phase1PageState.UNKNOWN.value, Phase1PageState.APP_HOME.value]
        )
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_publish_success_recognition(self):
        """测试识别 PUBLISH_SUCCESS 状态"""
        result = self.classifier.classify(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text="发布成功！您的内容已发布",
            ui_anchors=["发布成功", "已发布"],
        )

        self.assertEqual(result.page_state, Phase1PageState.PUBLISH_SUCCESS.value)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertGreater(len(result.evidence), 0)

    def test_publish_failure_recognition(self):
        """测试识别 PUBLISH_FAILURE 状态"""
        result = self.classifier.classify(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text="发布失败，网络异常请重试",
            ui_anchors=["发布失败", "网络异常"],
        )

        self.assertEqual(result.page_state, Phase1PageState.PUBLISH_FAILURE.value)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertGreater(len(result.evidence), 0)

    def test_create_entry_recognition(self):
        """测试识别 CREATE_ENTRY 状态"""
        result = self.classifier.classify(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text="创建新帖子，发布内容",
            ui_anchors=["创建", "发帖"],
        )

        self.assertEqual(result.page_state, Phase1PageState.CREATE_ENTRY.value)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertGreater(len(result.evidence), 0)

    def test_account_home_recognition(self):
        """测试识别 ACCOUNT_HOME 状态"""
        result = self.classifier.classify(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text="我的主页，草稿箱，作品列表",
            ui_anchors=["我的", "主页", "草稿箱"],
        )

        self.assertEqual(result.page_state, Phase1PageState.ACCOUNT_HOME.value)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertGreater(len(result.evidence), 0)

    def test_convenience_function(self):
        """测试便捷函数 classify_page_state"""
        result = classify_page_state(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text="标题请输入内容草稿",
            ui_anchors=["标题", "草稿"],
        )

        self.assertEqual(result.page_state, Phase1PageState.DRAFT_EDIT.value)
        self.assertIsInstance(result, PageStateResult)

    def test_priority_resolution(self):
        """测试状态优先级解决冲突"""
        # 同时包含高风险状态和普通状态的文本
        result = self.classifier.classify(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text="风险提示异常操作 标题正文草稿",  # 包含 RISK_PROMPT 和 DRAFT_EDIT 关键词
            ui_anchors=[],
        )

        # RISK_PROMPT 优先级 (80) 高于 DRAFT_EDIT (50)，应返回 RISK_PROMPT
        self.assertEqual(result.page_state, Phase1PageState.RISK_PROMPT.value)

    def test_confidence_range(self):
        """测试置信度始终在 0~1 范围内"""
        test_cases = [
            ("登录手机号验证码", ["登录"], Phase1PageState.LOGIN_REQUIRED),
            ("风险提示安全验证", ["风险"], Phase1PageState.RISK_PROMPT),
            ("发布成功已发布", ["成功"], Phase1PageState.PUBLISH_SUCCESS),
            ("发布失败网络异常", ["失败"], Phase1PageState.PUBLISH_FAILURE),
            ("发布前确认预览", ["预览"], Phase1PageState.PRE_PUBLISH_REVIEW),
            ("标题正文草稿", ["草稿"], Phase1PageState.DRAFT_EDIT),
        ]

        for vision_text, ui_anchors, expected_state in test_cases:
            with self.subTest(vision_text=vision_text):
                result = self.classifier.classify(
                    app_package=self.app_package,
                    current_package=self.app_package,
                    vision_text=vision_text,
                    ui_anchors=ui_anchors,
                )

                self.assertEqual(result.page_state, expected_state.value)
                self.assertGreaterEqual(result.confidence, 0.0)
                self.assertLessEqual(result.confidence, 1.0)
                self.assertGreater(len(result.evidence), 0)


if __name__ == "__main__":
    unittest.main()
