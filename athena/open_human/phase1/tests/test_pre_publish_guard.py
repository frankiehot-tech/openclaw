"""
Test Pre-Publish Guard for Phase 1

测试发布前守卫功能。
使用 unittest 框架。
"""

import os
import sys
import unittest

# 添加路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from athena.open_human.phase1.guards.human_confirmation_guard import (
    ConfirmationDecision,
    HumanConfirmationGuard,
    HumanConfirmationResult,
    request_human_confirmation,
)
from athena.open_human.phase1.guards.pre_publish_guard import (
    PrePublishGuard,
    PrePublishGuardResult,
    check_pre_publish_conditions,
)
from athena.open_human.phase1.states.page_state_schema import Phase1PageState


class TestPrePublishGuard(unittest.TestCase):
    """测试发布前守卫"""

    def setUp(self):
        """设置测试环境"""
        self.guard = PrePublishGuard()
        self.page_state_pre_publish = Phase1PageState.PRE_PUBLISH_REVIEW.value
        self.page_state_draft_edit = Phase1PageState.DRAFT_EDIT.value
        self.page_state_other = Phase1PageState.APP_HOME.value

    def test_block_when_page_state_not_pre_publish(self):
        """测试页面不是 PRE_PUBLISH_REVIEW 时阻止放行"""
        # 页面状态是草稿编辑，不应放行
        result = self.guard.check(
            account_scope_ok=True, page_state=self.page_state_draft_edit, draft_valid=True
        )

        self.assertFalse(result.allowed)
        self.assertIn("页面状态不是发布前确认状态", result.reason)
        self.assertFalse(result.requires_human_confirmation)

    def test_block_when_draft_invalid(self):
        """测试 draft_valid=False 时阻止放行"""
        result = self.guard.check(
            account_scope_ok=True, page_state=self.page_state_pre_publish, draft_valid=False
        )

        self.assertFalse(result.allowed)
        self.assertIn("草稿验证未通过", result.reason)
        self.assertFalse(result.requires_human_confirmation)

    def test_block_when_account_scope_false(self):
        """测试 account_scope_ok=False 时阻止放行"""
        result = self.guard.check(
            account_scope_ok=False, page_state=self.page_state_pre_publish, draft_valid=True
        )

        self.assertFalse(result.allowed)
        self.assertIn("账号范围检查未通过", result.reason)
        self.assertFalse(result.requires_human_confirmation)

    def test_allow_when_all_conditions_met_with_human_confirmation(self):
        """测试三项都满足时，allowed=True 且 requires_human_confirmation=True"""
        result = self.guard.check(
            account_scope_ok=True, page_state=self.page_state_pre_publish, draft_valid=True
        )

        self.assertTrue(result.allowed)
        self.assertIn("满足所有发布前条件", result.reason)
        self.assertTrue(result.requires_human_confirmation)  # 必须为 True

    def test_various_invalid_page_states(self):
        """测试各种无效页面状态"""
        invalid_states = [
            Phase1PageState.DRAFT_EDIT.value,
            Phase1PageState.APP_HOME.value,
            Phase1PageState.ACCOUNT_HOME.value,
            Phase1PageState.CREATE_ENTRY.value,
            Phase1PageState.LOGIN_REQUIRED.value,
            Phase1PageState.RISK_PROMPT.value,
            Phase1PageState.PUBLISH_SUCCESS.value,
            Phase1PageState.PUBLISH_FAILURE.value,
            Phase1PageState.OUT_OF_SCOPE.value,
            Phase1PageState.UNKNOWN.value,
        ]

        for state in invalid_states:
            with self.subTest(page_state=state):
                result = self.guard.check(account_scope_ok=True, page_state=state, draft_valid=True)

                if state == Phase1PageState.PRE_PUBLISH_REVIEW.value:
                    # 只有 PRE_PUBLISH_REVIEW 应该通过
                    self.assertTrue(result.allowed)
                else:
                    self.assertFalse(result.allowed)
                    self.assertIn("页面状态不是发布前确认状态", result.reason)

    def test_convenience_function(self):
        """测试便捷函数 check_pre_publish_conditions"""
        result = check_pre_publish_conditions(
            account_scope_ok=True, page_state=self.page_state_pre_publish, draft_valid=True
        )

        self.assertIsInstance(result, PrePublishGuardResult)
        self.assertTrue(result.allowed)
        self.assertTrue(result.requires_human_confirmation)


class TestHumanConfirmationGuard(unittest.TestCase):
    """测试人工确认守卫"""

    def setUp(self):
        """设置测试环境"""
        self.guard = HumanConfirmationGuard(simulation_mode=True)
        self.task_id = "test_task_123"
        self.account_id = "test_account_456"
        self.page_state = Phase1PageState.PRE_PUBLISH_REVIEW.value
        self.draft_summary = {"title": "测试标题", "body": "测试正文内容", "tags": ["测试", "标签"]}

    def test_continue_decision_confirmed_true(self):
        """测试 continue -> confirmed=True"""
        result = self.guard.request_confirmation(
            task_id=self.task_id,
            account_id=self.account_id,
            page_state=self.page_state,
            draft_summary=self.draft_summary,
        )

        self.assertEqual(result.decision, ConfirmationDecision.CONTINUE.value)
        self.assertTrue(result.confirmed)
        self.assertIsNotNone(result.operator_id)
        self.assertIn("Phase 1 模拟模式", result.reason)

    def test_cancel_decision_confirmed_false(self):
        """测试 cancel -> confirmed=False"""
        result = self.guard.simulate_cancel(
            task_id=self.task_id,
            account_id=self.account_id,
            page_state=self.page_state,
            draft_summary=self.draft_summary,
        )

        self.assertEqual(result.decision, ConfirmationDecision.CANCEL.value)
        self.assertFalse(result.confirmed)
        self.assertIn("模拟取消", result.reason)

    def test_timeout_decision_confirmed_false(self):
        """测试 timeout -> confirmed=False"""
        result = self.guard.simulate_timeout(
            task_id=self.task_id,
            account_id=self.account_id,
            page_state=self.page_state,
            draft_summary=self.draft_summary,
        )

        self.assertEqual(result.decision, ConfirmationDecision.TIMEOUT.value)
        self.assertFalse(result.confirmed)
        self.assertIsNone(result.operator_id)
        self.assertIn("模拟超时", result.reason)

    def test_not_confirmed_cannot_proceed(self):
        """测试未确认时不能被视为可直接发布"""
        # cancel 结果
        cancel_result = self.guard.simulate_cancel(
            task_id=self.task_id,
            account_id=self.account_id,
            page_state=self.page_state,
            draft_summary=self.draft_summary,
        )

        self.assertFalse(cancel_result.confirmed)
        # confirmed=False 时绝不允许默认继续
        # 在实际流程中，应该检查 confirmed=True 才允许继续

        # timeout 结果
        timeout_result = self.guard.simulate_timeout(
            task_id=self.task_id,
            account_id=self.account_id,
            page_state=self.page_state,
            draft_summary=self.draft_summary,
        )

        self.assertFalse(timeout_result.confirmed)

    def test_real_mode_not_implemented(self):
        """测试真实模式未实现抛出异常"""
        guard = HumanConfirmationGuard(simulation_mode=False)

        with self.assertRaises(NotImplementedError) as context:
            guard.request_confirmation(
                task_id=self.task_id,
                account_id=self.account_id,
                page_state=self.page_state,
                draft_summary=self.draft_summary,
            )

        self.assertIn("真实人工确认接口在 Phase 2+ 实现", str(context.exception))

    def test_convenience_function(self):
        """测试便捷函数 request_human_confirmation"""
        result = request_human_confirmation(
            task_id=self.task_id,
            account_id=self.account_id,
            page_state=self.page_state,
            draft_summary=self.draft_summary,
            simulation_mode=True,
        )

        self.assertIsInstance(result, HumanConfirmationResult)
        self.assertEqual(result.decision, ConfirmationDecision.CONTINUE.value)
        self.assertTrue(result.confirmed)

    def test_decision_enum_values(self):
        """测试决策枚举值"""
        self.assertEqual(ConfirmationDecision.CONTINUE.value, "continue")
        self.assertEqual(ConfirmationDecision.CANCEL.value, "cancel")
        self.assertEqual(ConfirmationDecision.TIMEOUT.value, "timeout")


def test_integration_workflow():
    """集成测试：模拟完整发布前工作流"""
    # 1. 检查发布前条件
    pre_publish_result = check_pre_publish_conditions(
        account_scope_ok=True, page_state=Phase1PageState.PRE_PUBLISH_REVIEW.value, draft_valid=True
    )

    assert pre_publish_result.allowed
    assert pre_publish_result.requires_human_confirmation

    # 2. 如果通过，请求人工确认
    if pre_publish_result.allowed and pre_publish_result.requires_human_confirmation:
        human_result = request_human_confirmation(
            task_id="test_integration_task",
            account_id="test_account",
            page_state=Phase1PageState.PRE_PUBLISH_REVIEW.value,
            draft_summary={"title": "集成测试", "body": "测试内容"},
            simulation_mode=True,
        )

        # 3. 验证只有 confirmed=True 且 decision=continue 才能继续
        can_proceed = (
            human_result.decision == ConfirmationDecision.CONTINUE.value
            and human_result.confirmed
        )

        # Phase 1 模拟模式下应该可以通过
        assert can_proceed
        assert human_result.confirmed


if __name__ == "__main__":
    # 支持直接运行测试
    import unittest

    # 由于使用了 pytest 特性，推荐使用 pytest 运行
    print("请使用 pytest 运行测试: pytest test_pre_publish_guard.py")
