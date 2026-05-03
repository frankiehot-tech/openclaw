"""
Test Create Entry Navigator for Phase 2

测试 Phase 2 创建入口导航器功能。
使用 pytest，确保不依赖真实设备。
符合测试要求：
1. dry_run 导航成功
2. current_package 不匹配时失败
3. 最终页面状态不是 CREATE_ENTRY 时不得判成功
4. 找不到入口时失败
5. 返回结构完整
6. evidence 非空
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
from athena.open_human.phase2.navigation.create_entry_navigator import (
    CreateEntryNavigationResult,
    CreateEntryNavigator,
    NavigationResultCode,
    navigate_to_create_entry,
)


class TestCreateEntryNavigator:
    """测试创建入口导航器"""

    def setup_method(self):
        """设置测试环境"""
        self.app_package = "com.example.app"
        self.navigator = CreateEntryNavigator()
        # Mock 依赖组件
        self.navigator.classifier = MagicMock()
        self.navigator.device_client = None  # 确保不依赖真实设备
        self.navigator.screen_analyzer = None
        self.navigator.ocr_engine = None
        self.navigator.ui_grounding = None

    def test_dry_run_navigation_success(self):
        """测试 dry_run 导航成功 (要求1)"""
        vision_text = "首页 推荐 发现"
        ui_anchors = ["首页", "推荐", "发现"]

        result = self.navigator.navigate(
            app_package=self.app_package,
            current_package=self.app_package,
            vision_text=vision_text,
            ui_anchors=ui_anchors,
            dry_run=True,
        )

        # 验证成功
        assert result.success is True
        assert result.final_page_state == "create_entry"
        assert result.result_code == NavigationResultCode.SUCCESS
        assert "Mock" in result.reason or "dry-run" in result.reason.lower()

        # 验证证据非空 (要求6)
        assert len(result.evidence) > 0
        for ev in result.evidence:
            assert isinstance(ev, str)
            assert len(ev.strip()) > 0

        # 验证证据包含关键信息
        assert any("Dry run" in ev for ev in result.evidence)
        assert any("Mock" in ev for ev in result.evidence) or any(
            "Mock:" in ev for ev in result.evidence
        )

    def test_package_mismatch_failure(self):
        """测试 current_package 不匹配时失败 (要求2)"""
        vision_text = "首页 推荐 发现"
        ui_anchors = ["首页", "推荐", "发现"]

        result = self.navigator.navigate(
            app_package=self.app_package,
            current_package="com.other.app",  # 不同包名
            vision_text=vision_text,
            ui_anchors=ui_anchors,
            dry_run=False,
        )

        # 验证失败
        assert result.success is False
        assert result.result_code == NavigationResultCode.PACKAGE_MISMATCH
        assert "Package mismatch" in result.reason
        assert "out_of_scope" in result.final_page_state

        # 验证证据包含包名信息
        assert len(result.evidence) > 0
        assert any("Package mismatch" in ev for ev in result.evidence)
        assert any(self.app_package in ev for ev in result.evidence)

    def test_state_not_create_entry_failure(self):
        """测试最终页面状态不是 CREATE_ENTRY 时不得判成功 (要求3)"""
        vision_text = "首页 推荐 发现"  # 首页文本，不是创建入口
        ui_anchors = ["首页", "推荐", "发现"]

        # Mock 分类器返回 APP_HOME 而不是 CREATE_ENTRY
        mock_classifier_result = PageStateResult(
            page_state="app_home", confidence=0.8, evidence=["关键词匹配: home/首页/推荐"]
        )
        self.navigator.classifier.classify.return_value = mock_classifier_result

        # 设置导航器找到创建入口但最终状态不是 CREATE_ENTRY
        with patch.object(self.navigator, "_find_create_entry", return_value=True):
            with patch.object(self.navigator, "_perform_navigation_action", return_value=True):
                # 第二次状态检查也返回 app_home
                with patch.object(self.navigator, "_classify_current_state") as mock_classify:
                    mock_classify.return_value = PageStateResult(
                        page_state="app_home",
                        confidence=0.7,
                        evidence=["关键词匹配: home/首页/推荐"],
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
        assert result.result_code == NavigationResultCode.STATE_NOT_CREATE_ENTRY
        assert "not CREATE_ENTRY" in result.reason
        assert result.final_page_state == "app_home"

        # 验证证据
        assert len(result.evidence) > 0
        assert any("不是 CREATE_ENTRY" in ev or "not CREATE_ENTRY" in ev for ev in result.evidence)

    def test_no_create_entry_found_failure(self):
        """测试找不到入口时失败 (要求4)"""
        vision_text = "首页 推荐 发现"  # 没有创建入口关键词
        ui_anchors = ["首页", "推荐", "发现"]

        # Mock 分类器返回 APP_HOME
        self.navigator.classifier.classify.return_value = PageStateResult(
            page_state="app_home", confidence=0.8, evidence=["关键词匹配: home/首页/推荐"]
        )

        # 模拟找不到创建入口
        with patch.object(self.navigator, "_find_create_entry", return_value=False):
            result = self.navigator.navigate(
                app_package=self.app_package,
                current_package=self.app_package,
                vision_text=vision_text,
                ui_anchors=ui_anchors,
                dry_run=False,
            )

        # 验证失败
        assert result.success is False
        assert result.result_code == NavigationResultCode.NO_CREATE_ENTRY_FOUND
        assert "No create entry found" in result.reason or "未找到创建入口" in result.reason
        assert result.final_page_state == "app_home"

        # 验证证据
        assert len(result.evidence) > 0
        assert any("未找到创建入口" in ev or "No create entry" in ev for ev in result.evidence)

    def test_result_structure_complete(self):
        """测试返回结构完整 (要求5)"""
        # 测试 CreateEntryNavigationResult 结构
        result = CreateEntryNavigationResult(
            success=True,
            final_page_state="create_entry",
            reason="Test reason",
            evidence=["evidence1", "evidence2"],
            result_code=NavigationResultCode.SUCCESS,
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
        assert isinstance(result.result_code, NavigationResultCode)

        # 验证证据列表
        assert len(result.evidence) == 2
        for ev in result.evidence:
            assert isinstance(ev, str)

    def test_evidence_not_empty_in_success(self):
        """测试成功时证据非空"""
        vision_text = "首页 推荐 发现"
        ui_anchors = ["首页", "推荐", "发现"]

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
        vision_text = "首页 推荐 发现"
        ui_anchors = ["首页", "推荐", "发现"]

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

    def test_already_at_create_entry(self):
        """测试当前已经是 CREATE_ENTRY 状态时的处理"""
        vision_text = "创建 新建 发帖"
        ui_anchors = ["创建", "新建", "发帖"]

        # Mock 分类器返回 CREATE_ENTRY
        self.navigator.classifier.classify.return_value = PageStateResult(
            page_state="create_entry", confidence=0.9, evidence=["关键词匹配: 创建/发帖/新建"]
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
        assert result.final_page_state == "create_entry"
        assert result.result_code == NavigationResultCode.SUCCESS
        assert "Already at CREATE_ENTRY" in result.reason or "已经是 CREATE_ENTRY" in result.reason

    def test_navigation_action_failure(self):
        """测试导航动作执行失败"""
        vision_text = "首页 创建按钮"
        ui_anchors = ["首页", "创建"]

        # Mock 分类器返回 APP_HOME
        self.navigator.classifier.classify.return_value = PageStateResult(
            page_state="app_home", confidence=0.8, evidence=["关键词匹配: 首页"]
        )

        # 模拟找到创建入口但执行动作失败
        with patch.object(self.navigator, "_find_create_entry", return_value=True):
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
        assert result.result_code == NavigationResultCode.NAVIGATION_FAILED
        assert "Navigation action failed" in result.reason or "导航动作执行失败" in result.reason

    def test_exception_handling(self):
        """测试异常处理"""
        vision_text = "首页 推荐 发现"
        ui_anchors = ["首页", "推荐", "发现"]

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
        assert result.result_code == NavigationResultCode.UNKNOWN_ERROR
        assert "Exception" in result.reason
        assert "Test exception" in result.reason

    def test_convenience_function(self):
        """测试便捷函数 navigate_to_create_entry"""
        with patch(
            "athena.open_human.phase2.navigation.create_entry_navigator.CreateEntryNavigator"
        ) as MockNavigator:
            mock_instance = MagicMock()
            mock_instance.navigate.return_value = CreateEntryNavigationResult(
                success=True,
                final_page_state="create_entry",
                reason="Mocked",
                evidence=["test"],
                result_code=NavigationResultCode.SUCCESS,
            )
            MockNavigator.return_value = mock_instance

            result = navigate_to_create_entry(
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
