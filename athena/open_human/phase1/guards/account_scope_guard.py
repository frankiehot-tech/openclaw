"""
Account Scope Guard - 账号范围守卫

检查请求的账号和平台是否在授权范围内，确保 Phase 1 只操作唯一授权账号。
严格遵循硬边界：不做自动注册、不做验证码处理、不操作未授权账号。
"""

from dataclasses import dataclass


@dataclass
class AccountScopeCheckResult:
    """账号范围检查结果"""

    allowed: bool
    reason: str
    account_id: str
    platform_id: str

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "account_id": self.account_id,
            "platform_id": self.platform_id,
        }


class AccountScopeGuard:
    """账号范围守卫"""

    def check(
        self, requested_account_id: str, requested_platform_id: str, authorized_account_config: dict
    ) -> AccountScopeCheckResult:
        """
        检查账号和平台是否在授权范围内

        Args:
            requested_account_id: 请求操作的账号ID
            requested_platform_id: 请求操作的平台ID
            authorized_account_config: 授权账号配置字典

        Returns:
            AccountScopeCheckResult: 检查结果
        """
        # 提取授权账号配置字段
        authorized_account_id = authorized_account_config.get("account_id")
        authorized_platform_id = authorized_account_config.get("platform_id")
        allowed_for_phase1 = authorized_account_config.get("allowed_for_phase1", False)

        # 规则1: requested_account_id 必须等于授权账号配置中的 account_id
        if requested_account_id != authorized_account_id:
            return AccountScopeCheckResult(
                allowed=False,
                reason=f"账号ID不匹配: 请求的 '{requested_account_id}' 不等于授权的 '{authorized_account_id}'",
                account_id=requested_account_id,
                platform_id=requested_platform_id,
            )

        # 规则2: requested_platform_id 必须等于授权账号配置中的 platform_id
        if requested_platform_id != authorized_platform_id:
            return AccountScopeCheckResult(
                allowed=False,
                reason=f"平台ID不匹配: 请求的 '{requested_platform_id}' 不等于授权的 '{authorized_platform_id}'",
                account_id=requested_account_id,
                platform_id=requested_platform_id,
            )

        # 规则3: allowed_for_phase1 必须为 true
        if not allowed_for_phase1:
            return AccountScopeCheckResult(
                allowed=False,
                reason=f"账号 '{authorized_account_id}' 未授权用于 Phase 1 (allowed_for_phase1=false)",
                account_id=requested_account_id,
                platform_id=requested_platform_id,
            )

        # 所有规则通过
        return AccountScopeCheckResult(
            allowed=True,
            reason="账号和平台在授权范围内，允许 Phase 1 操作",
            account_id=requested_account_id,
            platform_id=requested_platform_id,
        )


# 便捷函数
def check_account_scope(
    requested_account_id: str, requested_platform_id: str, authorized_account_config: dict
) -> AccountScopeCheckResult:
    """
    便捷函数：检查账号范围

    Args:
        requested_account_id: 请求操作的账号ID
        requested_platform_id: 请求操作的平台ID
        authorized_account_config: 授权账号配置字典

    Returns:
        AccountScopeCheckResult: 检查结果
    """
    guard = AccountScopeGuard()
    return guard.check(requested_account_id, requested_platform_id, authorized_account_config)
