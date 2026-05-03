"""
Audit Schema for Phase 1 - Phase 1 审计事件模型

定义 Phase 1 审计事件的数据结构，用于记录关键操作和决策。
与现有 guard / classifier 输出保持兼容。
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AuditEvent:
    """
    Phase 1 审计事件数据类

    Attributes:
        task_id (str): 任务唯一标识
        sample_id (str): 样本唯一标识（用于追踪）
        batch_id (str | None): 批次标识（可选）
        account_id (str): 账号ID
        platform_id (str): 平台ID
        page_state (str): 页面状态（Phase1PageState.value）
        action (str): 审计动作类型
        allowed (bool): 是否允许继续
        reason (str): 操作原因或决策说明
        evidence (list[str]): 判定证据列表
        metadata (dict[str, str]): 额外元数据
        timestamp (str): ISO格式时间戳（自动生成）
        event_id (str): 事件唯一标识（自动生成）
    """

    task_id: str
    sample_id: str
    batch_id: str | None = None
    account_id: str = ""
    platform_id: str = ""
    page_state: str = ""
    action: str = ""
    allowed: bool = False
    reason: str = ""
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    event_id: str = field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:12]}")

    def __post_init__(self):
        """初始化后处理"""
        # 确保 evidence 是列表类型
        if not isinstance(self.evidence, list):
            self.evidence = [str(self.evidence)]
        # 确保 metadata 是字典类型
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        # 确保 timestamp 是字符串
        if not isinstance(self.timestamp, str):
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, any]:
        """转换为字典格式（支持 JSON 序列化）"""
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "sample_id": self.sample_id,
            "batch_id": self.batch_id,
            "account_id": self.account_id,
            "platform_id": self.platform_id,
            "page_state": self.page_state,
            "action": self.action,
            "allowed": self.allowed,
            "reason": self.reason,
            "evidence": self.evidence,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, any]) -> "AuditEvent":
        """从字典创建实例"""
        # 处理可选字段
        return cls(**data)


# 支持的审计动作类型常量
class AuditAction:
    """审计动作类型常量"""

    LAUNCH_APP = "launch_app"
    ACCOUNT_SCOPE_CHECK = "account_scope_check"
    PAGE_STATE_CLASSIFIED = "page_state_classified"
    DRAFT_VALIDATED = "draft_validated"
    PRE_PUBLISH_GUARD_CHECKED = "pre_publish_guard_checked"
    HUMAN_CONFIRMATION_RECEIVED = "human_confirmation_received"
    PUBLISH_ACTION = "publish_action"
    PUBLISH_RESULT_VERIFIED = "publish_result_verified"

    @classmethod
    def all_actions(cls) -> list[str]:
        """获取所有支持的审计动作"""
        return [
            cls.LAUNCH_APP,
            cls.ACCOUNT_SCOPE_CHECK,
            cls.PAGE_STATE_CLASSIFIED,
            cls.DRAFT_VALIDATED,
            cls.PRE_PUBLISH_GUARD_CHECKED,
            cls.HUMAN_CONFIRMATION_RECEIVED,
            cls.PUBLISH_ACTION,
            cls.PUBLISH_RESULT_VERIFIED,
        ]


# 创建审计事件的工厂函数
def create_account_scope_audit_event(
    task_id: str,
    sample_id: str,
    account_id: str,
    platform_id: str,
    allowed: bool,
    reason: str,
    batch_id: str | None = None,
    evidence: list[str] | None = None,
) -> AuditEvent:
    """
    创建账号范围检查审计事件

    Args:
        task_id: 任务ID
        sample_id: 样本ID
        account_id: 账号ID
        platform_id: 平台ID
        allowed: 是否允许
        reason: 原因说明
        batch_id: 批次ID（可选）
        evidence: 证据列表（可选）
    """
    if evidence is None:
        evidence = []

    return AuditEvent(
        task_id=task_id,
        sample_id=sample_id,
        batch_id=batch_id,
        account_id=account_id,
        platform_id=platform_id,
        page_state="",  # 账号检查不涉及页面状态
        action=AuditAction.ACCOUNT_SCOPE_CHECK,
        allowed=allowed,
        reason=reason,
        evidence=evidence,
        metadata={"source": "account_scope_guard"},
    )


def create_page_state_classification_audit_event(
    task_id: str,
    sample_id: str,
    account_id: str,
    platform_id: str,
    page_state: str,
    allowed: bool,
    reason: str,
    batch_id: str | None = None,
    evidence: list[str] | None = None,
) -> AuditEvent:
    """
    创建页面状态分类审计事件

    Args:
        task_id: 任务ID
        sample_id: 样本ID
        account_id: 账号ID
        platform_id: 平台ID
        page_state: 页面状态
        allowed: 是否允许继续
        reason: 原因说明
        batch_id: 批次ID（可选）
        evidence: 证据列表（可选）
    """
    if evidence is None:
        evidence = []

    return AuditEvent(
        task_id=task_id,
        sample_id=sample_id,
        batch_id=batch_id,
        account_id=account_id,
        platform_id=platform_id,
        page_state=page_state,
        action=AuditAction.PAGE_STATE_CLASSIFIED,
        allowed=allowed,
        reason=reason,
        evidence=evidence,
        metadata={"source": "page_state_classifier"},
    )


def create_human_confirmation_audit_event(
    task_id: str,
    sample_id: str,
    account_id: str,
    platform_id: str,
    page_state: str,
    allowed: bool,
    reason: str,
    operator_id: str | None = None,
    batch_id: str | None = None,
    evidence: list[str] | None = None,
) -> AuditEvent:
    """
    创建人工确认审计事件

    Args:
        task_id: 任务ID
        sample_id: 样本ID
        account_id: 账号ID
        platform_id: 平台ID
        page_state: 页面状态
        allowed: 是否允许继续
        reason: 原因说明
        operator_id: 操作员ID（可选）
        batch_id: 批次ID（可选）
        evidence: 证据列表（可选）
    """
    if evidence is None:
        evidence = []

    metadata = {"source": "human_confirmation_guard"}
    if operator_id:
        metadata["operator_id"] = operator_id

    return AuditEvent(
        task_id=task_id,
        sample_id=sample_id,
        batch_id=batch_id,
        account_id=account_id,
        platform_id=platform_id,
        page_state=page_state,
        action=AuditAction.HUMAN_CONFIRMATION_RECEIVED,
        allowed=allowed,
        reason=reason,
        evidence=evidence,
        metadata=metadata,
    )


def create_publish_result_verification_audit_event(
    task_id: str,
    sample_id: str,
    account_id: str,
    platform_id: str,
    page_state: str,
    result: str,  # success / fail / safe_stop
    reason: str,
    taxonomy_class: str | None = None,
    sub_reason: str | None = None,
    batch_id: str | None = None,
    evidence: list[str] | None = None,
) -> AuditEvent:
    """
    创建发布结果核验审计事件

    Args:
        task_id: 任务ID
        sample_id: 样本ID
        account_id: 账号ID
        platform_id: 平台ID
        page_state: 页面状态
        result: 核验结果（success/fail/safe_stop）
        reason: 原因说明
        taxonomy_class: 分类标识（可选）
        sub_reason: 子原因（可选）
        batch_id: 批次ID（可选）
        evidence: 证据列表（可选）
    """
    if evidence is None:
        evidence = []

    # 根据结果确定 allowed
    # success: allowed=True; fail/safe_stop: allowed=False
    allowed = result == "success"

    metadata = {"source": "publish_result_verifier", "verification_result": result}
    if taxonomy_class:
        metadata["taxonomy_class"] = taxonomy_class
    if sub_reason:
        metadata["sub_reason"] = sub_reason

    return AuditEvent(
        task_id=task_id,
        sample_id=sample_id,
        batch_id=batch_id,
        account_id=account_id,
        platform_id=platform_id,
        page_state=page_state,
        action=AuditAction.PUBLISH_RESULT_VERIFIED,
        allowed=allowed,
        reason=reason,
        evidence=evidence,
        metadata=metadata,
    )
