"""
Pre-Publish Guard for Phase 1 - 发布前守卫

检查是否满足进入发布前人工确认的条件。
严格遵循 Phase 1 硬边界：只允许在 PRE_PUBLISH_REVIEW 状态下进入人工确认。
不允许默认进入发布动作，必须经过人工确认。
"""

from dataclasses import dataclass

from athena.open_human.phase1.states.page_state_schema import Phase1PageState


@dataclass
class PrePublishGuardResult:
    """发布前守卫检查结果"""

    allowed: bool
    reason: str
    requires_human_confirmation: bool

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "requires_human_confirmation": self.requires_human_confirmation,
        }


class PrePublishGuard:
    """发布前守卫"""

    def check(
        self, account_scope_ok: bool, page_state: str, draft_valid: bool
    ) -> PrePublishGuardResult:
        """
        检查是否满足进入发布前人工确认的条件

        Args:
            account_scope_ok: 账号范围检查是否通过
            page_state: 页面状态字符串（应与 Phase1PageState 枚举值匹配）
            draft_valid: 草稿验证是否通过

        Returns:
            PrePublishGuardResult: 检查结果
        """
        # 规则1: 账号范围必须通过
        if not account_scope_ok:
            return PrePublishGuardResult(
                allowed=False,
                reason="账号范围检查未通过，不允许进入发布前状态",
                requires_human_confirmation=False,
            )

        # 规则2: 页面状态必须是 PRE_PUBLISH_REVIEW
        if page_state != Phase1PageState.PRE_PUBLISH_REVIEW.value:
            return PrePublishGuardResult(
                allowed=False,
                reason=f"页面状态不是发布前确认状态: '{page_state}' != '{Phase1PageState.PRE_PUBLISH_REVIEW.value}'",
                requires_human_confirmation=False,
            )

        # 规则3: 草稿验证必须通过
        if not draft_valid:
            return PrePublishGuardResult(
                allowed=False,
                reason="草稿验证未通过，不允许进入发布前状态",
                requires_human_confirmation=False,
            )

        # 所有规则通过，但必须要求人工确认
        return PrePublishGuardResult(
            allowed=True,
            reason="满足所有发布前条件，可以进入人工确认环节",
            requires_human_confirmation=True,  # 严格写死：必须要求人工确认
        )


# 便捷函数
def check_pre_publish_conditions(
    account_scope_ok: bool, page_state: str, draft_valid: bool
) -> PrePublishGuardResult:
    """
    便捷函数：检查发布前条件

    Args:
        account_scope_ok: 账号范围检查是否通过
        page_state: 页面状态字符串
        draft_valid: 草稿验证是否通过

    Returns:
        PrePublishGuardResult: 检查结果
    """
    guard = PrePublishGuard()
    return guard.check(account_scope_ok, page_state, draft_valid)
