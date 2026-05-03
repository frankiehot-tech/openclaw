"""
Human Confirmation Guard for Phase 1 - 人工确认守卫

处理发布前的人工确认请求。
严格遵循 Phase 1 硬边界：必须经过人工确认才能继续发布动作。
提供模拟接口，在 Phase 1 返回预设结果。
"""

from dataclasses import dataclass
from enum import StrEnum


class ConfirmationDecision(StrEnum):
    """人工确认决策枚举"""

    CONTINUE = "continue"
    CANCEL = "cancel"
    TIMEOUT = "timeout"


@dataclass
class HumanConfirmationResult:
    """人工确认结果"""

    decision: str  # continue / cancel / timeout
    confirmed: bool
    operator_id: str | None
    reason: str

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "decision": self.decision,
            "confirmed": self.confirmed,
            "operator_id": self.operator_id,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HumanConfirmationResult":
        """从字典创建实例"""
        return cls(**data)


class HumanConfirmationGuard:
    """人工确认守卫"""

    def __init__(self, simulation_mode: bool = True):
        """
        初始化人工确认守卫

        Args:
            simulation_mode: 是否启用模拟模式（Phase 1 默认为 True）
        """
        self.simulation_mode = simulation_mode

    def request_confirmation(
        self, task_id: str, account_id: str, page_state: str, draft_summary: dict
    ) -> HumanConfirmationResult:
        """
        请求人工确认

        Args:
            task_id: 任务ID
            account_id: 账号ID
            page_state: 页面状态字符串
            draft_summary: 草稿摘要字典

        Returns:
            HumanConfirmationResult: 人工确认结果

        Phase 1 规则：
        1. decision=continue 才允许进入"可执行发布动作"状态
        2. cancel -> 当前任务以 cancelled/停止路径结束
        3. timeout -> 当前任务必须走 safe_stop 路径
        4. confirmed=False 时绝不允许默认继续
        5. 本模块在 Phase 1 返回模拟结果
        """
        if self.simulation_mode:
            # Phase 1 模拟模式：固定返回 continue 决策以测试流程
            return self._get_simulation_result(task_id, account_id, page_state, draft_summary)
        else:
            # 真实模式（Phase 2+ 实现）：实际调用人工确认接口
            # 暂不实现，抛出异常提示需要实现真实接口
            raise NotImplementedError("真实人工确认接口在 Phase 2+ 实现，请启用 simulation_mode")

    def _get_simulation_result(
        self, task_id: str, account_id: str, page_state: str, draft_summary: dict
    ) -> HumanConfirmationResult:
        """
        获取模拟结果（Phase 1 专用）

        Phase 1 规则实现：
        - 模拟人工确认结果为 continue（允许测试流程）
        - 确认标识为 True
        - 提供模拟操作员ID
        """
        # Phase 1 模拟：总是返回继续（用于测试流程）
        # 在实际部署时，这里会替换为真实的人工确认逻辑
        return HumanConfirmationResult(
            decision=ConfirmationDecision.CONTINUE.value,
            confirmed=True,
            operator_id="simulated_operator_phase1",
            reason="Phase 1 模拟模式：固定返回继续确认以测试发布流程",
        )

    def simulate_cancel(
        self, task_id: str, account_id: str, page_state: str, draft_summary: dict
    ) -> HumanConfirmationResult:
        """
        模拟取消决策（用于测试）

        Returns:
            HumanConfirmationResult: 模拟取消结果
        """
        return HumanConfirmationResult(
            decision=ConfirmationDecision.CANCEL.value,
            confirmed=False,
            operator_id="simulated_operator_phase1",
            reason=f"模拟取消：任务 {task_id} 被操作员取消",
        )

    def simulate_timeout(
        self, task_id: str, account_id: str, page_state: str, draft_summary: dict
    ) -> HumanConfirmationResult:
        """
        模拟超时决策（用于测试）

        Returns:
            HumanConfirmationResult: 模拟超时结果
        """
        return HumanConfirmationResult(
            decision=ConfirmationDecision.TIMEOUT.value,
            confirmed=False,
            operator_id=None,
            reason=f"模拟超时：任务 {task_id} 确认请求超时",
        )


# 便捷函数
def request_human_confirmation(
    task_id: str,
    account_id: str,
    page_state: str,
    draft_summary: dict,
    simulation_mode: bool = True,
) -> HumanConfirmationResult:
    """
    便捷函数：请求人工确认

    Args:
        task_id: 任务ID
        account_id: 账号ID
        page_state: 页面状态字符串
        draft_summary: 草稿摘要字典
        simulation_mode: 是否启用模拟模式

    Returns:
        HumanConfirmationResult: 人工确认结果
    """
    guard = HumanConfirmationGuard(simulation_mode=simulation_mode)
    return guard.request_confirmation(task_id, account_id, page_state, draft_summary)
