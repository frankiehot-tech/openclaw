"""
Test Draft Edit Navigator for Phase 2

测试 Phase 2 草稿编辑页导航器功能。
使用 pytest，确保不依赖真实设备。
符合测试要求：
1. dry_run 导航成功
2. current_package 不匹配时失败
3. 最终页面状态不是 DRAFT_EDIT 时不得判成功
4. UNKNOWN 时不得判成功
5. RISK_PROMPT 时不得判成功
6. 找不到编辑入口时失败
7. 返回结构完整
8. evidence 非空
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# 添加路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from athena.open_human.phase1.states.page_state_classifier import PageStateResult
from athena.open_human.phase2.navigation.draft_edit_navigator import (
    DraftEditNavigationResult,
    DraftEditNavigationResultCode,
    DraftEditNavigator,
    navigate_to_draft_edit,
)


class TestDraftEditNavigator:
    """测试草稿编辑页导航器"""

    def setup_method(self):
        """设置测试环境"""
        self.app_package = "com.example.app"
        self.navigator = DraftEditNavigator()
        # Mock 依赖组件
        self.navigator.classifier = MagicMock()
        self.navigator.device_client = None  # 确保不依赖真实设备
        self.navigator.screen_analyzer = None
        self.navigator.ocr_engine = None
        self.navigator.ui_grounding = None

    def test_dry_run_navigation_success(self):
        """测试 dry_run 导航成功 (要求1)"""
        vision_text = "创建 发帖 编辑"
        ui_anchors = ["创建", "发帖", "编辑"]

        result = self.navigator.navigate(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text=vision_text,
            ui_anchors=ui_anchors,
            dry_run=True,
        )

        # 验证成功
        assert result.success is True
        assert result.final_page_state == "draft_edit"
        assert result.result_code == DraftEditNavigationResultCode.SUCCESS
        assert "Mock" in result.reason or "dry-run" in result.reason.lower()

        # 验证证据非空 (要求8)
        assert len(result.evidence) > 0
        for ev in result.evidence:
            assert isinstance(ev, str)
            assert len(ev.strip()) > 0

        # 验证证据包含关键信息
        assert any("Dry run" in ev for ev in result.evidence)
        assert any("Mock" in ev for ev in result.evidence)

    def test_package_mismatch_failure(self):
        """测试 current_package 不匹配时失败 (要求2)"""
        vision_text = "创建 发帖 编辑"
        ui_anchors = ["创建", "发帖", "编辑"]

        result = self.navigator.navigate(
            app_package=self.app_package,
            current_package="com.other.app",  # 不同包名
            vision_text=vision_text,
            ui_anchors=ui_anchors,
            dry_run=False,
        )

        # 验证失败
        assert result.success is False
        assert result.result_code == DraftEditNavigationResultCode.PACKAGE_MISMATCH
        assert "Package mismatch" in result.reason
        assert "out_of_scope" in result.final_page_state

        # 验证证据包含包名信息
        assert len(result.evidence) > 0
        assert any("Package mismatch" in ev for ev in result.evidence)
        assert any(self.app_package in ev for ev in result.evidence)

    def test_state_not_draft_edit_failure(self):
        """测试最终页面状态不是 DRAFT_EDIT 时不得判成功 (要求3)"""
        vision_text = "创建 发帖"  # 没有编辑关键词
        ui_anchors = ["创建", "发帖"]

        # Mock 分类器返回 CREATE_ENTRY 而不是 DRAFT_EDIT
        mock_classifier_result = PageStateResult(
            page_state="create_entry", confidence=0.8, evidence=["关键词匹配: 创建/发帖"]
        )
        self.navigator.classifier.classify.return_value = mock_classifier_result

        # 设置导航器找到编辑入口但最终状态不是 DRAFT_EDIT
        with patch.object(self.navigator, "_find_draft_edit_entry", return_value=True):
            with patch.object(self.navigator, "_perform_navigation_action", return_value=True):
                # 第二次状态检查也返回 create_entry
                with patch.object(self.navigator, "_classify_current_state") as mock_classify:
                    mock_classify.return_value = PageStateResult(
                        page_state="create_entry",
                        confidence=0.7,
                        evidence=["关键词匹配: 创建/发帖"],
                    )

                    result = self.navigator.navigate(
                        app_package=self.app_package,
                        current_package=self.app_package,
                        vision_text=vision_text,
                        ui_anchors=ui_anchors,
                        dry_run=False,
                    )

        # 验证失败
        assert result.success is False
        assert result.result_code == DraftEditNavigationResultCode.STATE_NOT_DRAFT_EDIT
        assert "not DRAFT_EDIT" in result.reason
        assert result.final_page_state == "create_entry"

        # 验证证据
        assert len(result.evidence) > 0
        assert any("不是 DRAFT_EDIT" in ev or "not DRAFT_EDIT" in ev for ev in result.evidence)

    def test_unknown_page_failure(self):
        """测试 UNKNOWN 时不得判成功 (要求4)"""
        vision_text = "未知页面"
        ui_anchors = ["未知"]

        # Mock 分类器返回 UNKNOWN
        self.navigator.classifier.classify.return_value = PageStateResult(
            page_state="unknown", confidence=0.3, evidence=["无匹配关键词"]
        )

        result = self.navigator.navigate(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text=vision_text,
            ui_anchors=ui_anchors,
            dry_run=False,
        )

        # 验证失败
        assert result.success is False
        assert result.result_code == DraftEditNavigationResultCode.UNKNOWN_STATE
        assert "unknown" in result.reason.lower() or "UNKNOWN" in result.reason
        assert result.final_page_state == "unknown"

        # 验证证据
        assert len(result.evidence) > 0
        assert any("UNKNOWN" in ev or "unknown" in ev for ev in result.evidence)

    def test_risk_prompt_failure(self):
        """测试 RISK_PROMPT 时不得判成功 (要求5)"""
        vision_text = "风险警告 请注意"
        ui_anchors = ["风险", "警告"]

        # Mock 分类器返回 RISK_PROMPT
        self.navigator.classifier.classify.return_value = PageStateResult(
            page_state="risk_prompt", confidence=0.9, evidence=["关键词匹配: 风险/警告"]
        )

        result = self.navigator.navigate(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text=vision_text,
            ui_anchors=ui_anchors,
            dry_run=False,
        )

        # 验证失败
        assert result.success is False
        assert result.result_code == DraftEditNavigationResultCode.RISK_PROMPT_DETECTED
        assert "risk" in result.reason.lower() or "RISK" in result.reason
        assert result.final_page_state == "risk_prompt"

        # 验证证据
        assert len(result.evidence) > 0
        assert any("RISK" in ev or "risk" in ev for ev in result.evidence)

    def test_no_draft_edit_entry_found_failure(self):
        """测试找不到编辑入口时失败 (要求6)"""
        vision_text = "创建 发帖"  # 没有编辑入口关键词
        ui_anchors = ["创建", "发帖"]

        # Mock 分类器返回 CREATE_ENTRY
        self.navigator.classifier.classify.return_value = PageStateResult(
            page_state="create_entry", confidence=0.8, evidence=["关键词匹配: 创建/发帖"]
        )

        # 模拟找不到编辑入口
        with patch.object(self.navigator, "_find_draft_edit_entry", return_value=False):
            result = self.navigator.navigate(
                app_package=self.app_package,
                current_package=self.app_package,
                vision_text=vision_text,
                ui_anchors=ui_anchors,
                dry_run=False,
            )

        # 验证失败
        assert result.success is False
        assert result.result_code == DraftEditNavigationResultCode.NO_DRAFT_ENTRY_FOUND
        assert "No draft edit entry found" in result.reason or "未找到草稿编辑入口" in result.reason
        assert result.final_page_state == "create_entry"

        # 验证证据
        assert len(result.evidence) > 0
        assert any(
            "未找到草稿编辑入口" in ev or "No draft edit entry" in ev for ev in result.evidence
        )

    def test_result_structure_complete(self):
        """测试返回结构完整 (要求7)"""
        # 测试 DraftEditNavigationResult 结构
        result = DraftEditNavigationResult(
            success=True,
            final_page_state="draft_edit",
            reason="Test reason",
            evidence=["evidence1", "evidence2"],
            result_code=DraftEditNavigationResultCode.SUCCESS,
        )

        # 验证所有必需字段存在
        assert hasattr(result, "success")
        assert hasattr(result, "final_page_state")
        assert hasattr(result, "reason")
        assert hasattr(result, "evidence")
        assert hasattr(result, "result_code")

        # 验证字段类型
        assert isinstance(result.success, bool)
        assert isinstance(result.final_page_state, str)
        assert isinstance(result.reason, str)
        assert isinstance(result.evidence, list)
        assert isinstance(result.result_code, DraftEditNavigationResultCode)

        # 验证证据列表
        assert len(result.evidence) == 2
        for ev in result.evidence:
            assert isinstance(ev, str)

    def test_evidence_not_empty_in_success(self):
        """测试成功时证据非空"""
        vision_text = "创建 发帖 编辑"
        ui_anchors = ["创建", "发帖", "编辑"]

        result = self.navigator.navigate(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text=vision_text,
            ui_anchors=ui_anchors,
            dry_run=True,  # dry-run 模式总是返回成功
        )

        assert len(result.evidence) > 0
        for ev in result.evidence:
            assert isinstance(ev, str)
            assert len(ev.strip()) > 0

    def test_evidence_not_empty_in_failure(self):
        """测试失败时证据非空"""
        vision_text = "创建 发帖 编辑"
        ui_anchors = ["创建", "发帖", "编辑"]

        result = self.navigator.navigate(
            app_package=self.app_package,
            current_package="com.other.app",  # 包名不匹配导致失败
            vision_text=vision_text,
            ui_anchors=ui_anchors,
            dry_run=False,
        )

        assert len(result.evidence) > 0
        for ev in result.evidence:
            assert isinstance(ev, str)
            assert len(ev.strip()) > 0

    def test_already_at_draft_edit(self):
        """测试当前已经是 DRAFT_EDIT 状态时的处理"""
        vision_text = "编辑 草稿 保存"
        ui_anchors = ["编辑", "草稿", "保存"]

        # Mock 分类器返回 DRAFT_EDIT
        self.navigator.classifier.classify.return_value = PageStateResult(
            page_state="draft_edit", confidence=0.9, evidence=["关键词匹配: 编辑/草稿/保存"]
        )

        result = self.navigator.navigate(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text=vision_text,
            ui_anchors=ui_anchors,
            dry_run=False,
        )

        # 应该直接返回成功
        assert result.success is True
        assert result.final_page_state == "draft_edit"
        assert result.result_code == DraftEditNavigationResultCode.SUCCESS
        assert "Already at DRAFT_EDIT" in result.reason or "已经是 DRAFT_EDIT" in result.reason

    def test_out_of_scope_failure(self):
        """测试 OUT_OF_SCOPE 时不得判成功"""
        vision_text = "超出范围"
        ui_anchors = ["超出"]

        # Mock 分类器返回 OUT_OF_SCOPE
        self.navigator.classifier.classify.return_value = PageStateResult(
            page_state="out_of_scope", confidence=0.7, evidence=["关键词匹配: 超出/范围"]
        )

        result = self.navigator.navigate(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text=vision_text,
            ui_anchors=ui_anchors,
            dry_run=False,
        )

        # 验证失败
        assert result.success is False
        assert result.result_code == DraftEditNavigationResultCode.OUT_OF_SCOPE
        assert "out_of_scope" in result.final_page_state

    def test_navigation_action_failure(self):
        """测试导航动作执行失败"""
        vision_text = "创建 编辑按钮"
        ui_anchors = ["创建", "编辑"]

        # Mock 分类器返回 CREATE_ENTRY
        self.navigator.classifier.classify.return_value = PageStateResult(
            page_state="create_entry", confidence=0.8, evidence=["关键词匹配: 创建"]
        )

        # 模拟找到编辑入口但执行动作失败
        with patch.object(self.navigator, "_find_draft_edit_entry", return_value=True):
            with patch.object(self.navigator, "_perform_navigation_action", return_value=False):
                result = self.navigator.navigate(
                    app_package=self.app_package,
                    current_package=self.app_package,
                    vision_text=vision_text,
                    ui_anchors=ui_anchors,
                    dry_run=False,
                )

        # 验证失败
        assert result.success is False
        assert result.result_code == DraftEditNavigationResultCode.NAVIGATION_FAILED
        assert "Navigation action failed" in result.reason or "导航动作执行失败" in result.reason

    def test_exception_handling(self):
        """测试异常处理"""
        vision_text = "创建 发帖 编辑"
        ui_anchors = ["创建", "发帖", "编辑"]

        # Mock 分类器抛出异常
        self.navigator.classifier.classify.side_effect = Exception("Test exception")

        result = self.navigator.navigate(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text=vision_text,
            ui_anchors=ui_anchors,
            dry_run=False,
        )

        # 验证异常被捕获并返回失败
        assert result.success is False
        assert result.result_code == DraftEditNavigationResultCode.UNKNOWN_ERROR
        assert "Exception" in result.reason
        assert "Test exception" in result.reason

    def test_convenience_function(self):
        """测试便捷函数 navigate_to_draft_edit"""
        with patch(
            "athena.open_human.phase2.navigation.draft_edit_navigator.DraftEditNavigator"
        ) as MockNavigator:
            mock_instance = MagicMock()
            mock_instance.navigate.return_value = DraftEditNavigationResult(
                success=True,
                final_page_state="draft_edit",
                reason="Mocked",
                evidence=["test"],
                result_code=DraftEditNavigationResultCode.SUCCESS,
            )
            MockNavigator.return_value = mock_instance

            result = navigate_to_draft_edit(
                app_package=self.app_package,
                current_package=self.app_package,
                vision_text="test",
                ui_anchors=["test"],
                dry_run=True,
                device_id="test_device",
            )

            MockNavigator.assert_called_once_with(device_id="test_device")
            mock_instance.navigate.assert_called_once_with(
                self.app_package, self.app_package, "test", ["test"], True
            )
            assert result.success is True


if __name__ == "__main__":
    # 支持直接运行测试
    pytest.main([__file__, "-v"])
