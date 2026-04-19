#!/usr/bin/env python3
"""
Payment Contract - 支付审批契约

定义支付请求契约、审批状态流转和 Human Gate 协议。
与预算引擎集成，提供小额自动批准/大额人工审批分流。
"""

import json
import logging
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== 枚举定义 ====================


class PaymentApprovalDecision(Enum):
    """支付审批决策"""

    AUTO_APPROVED = "auto_approved"  # 自动批准
    REQUIRES_APPROVAL = "requires_approval"  # 需要人工审批
    REJECTED = "rejected"  # 拒绝
    PENDING = "pending"  # 审批中
    APPROVED = "approved"  # 人工批准
    CANCELLED = "cancelled"  # 取消


class PaymentStatus(Enum):
    """支付状态"""

    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    APPROVAL_PENDING = "approval_pending"  # 审批中
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class PaymentType(Enum):
    """支付类型"""

    TASK_PAYMENT = "task_payment"  # 任务支付
    REFUND = "refund"  # 退款
    SETTLEMENT = "settlement"  # 结算
    MAINTENANCE_FEE = "maintenance_fee"  # 维护费
    OTHER = "other"  # 其他


# ==================== 数据类定义 ====================


@dataclass
class PaymentRequest:
    """支付请求"""

    request_id: str  # 请求唯一ID
    task_id: Optional[str] = None  # 关联的任务ID
    amount: float = 0.0  # 支付金额（元）
    currency: str = "CNY"  # 货币
    payment_type: str = PaymentType.TASK_PAYMENT.value  # 支付类型
    description: str = ""  # 支付描述
    payer: str = "system"  # 付款方
    payee: str = ""  # 收款方
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    # 审批相关字段
    requires_approval: bool = False  # 是否需要审批
    approval_threshold: float = 100.0  # 审批阈值（元），超过此金额需要人工审批
    auto_approve: bool = True  # 是否允许自动审批

    # 时间戳
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class PaymentApproval:
    """支付审批"""

    approval_id: str  # 审批唯一ID
    request_id: str  # 关联的支付请求ID
    decision: str = PaymentApprovalDecision.PENDING.value  # 审批决策
    approver: Optional[str] = None  # 审批人
    reason: str = ""  # 审批理由
    comments: str = ""  # 审批备注

    # 时间戳
    requested_at: str = ""
    decided_at: Optional[str] = None
    expires_at: Optional[str] = None

    # 证据与审计
    evidence: Dict[str, Any] = field(default_factory=dict)  # 审批证据
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)  # 审计追踪

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class PaymentResult:
    """支付结果"""

    request_id: str  # 支付请求ID
    status: str = PaymentStatus.DRAFT.value  # 支付状态
    transaction_id: Optional[str] = None  # 交易ID（如果有）

    # 财务信息
    amount: float = 0.0
    currency: str = "CNY"
    fee: float = 0.0  # 手续费
    net_amount: float = 0.0  # 净额

    # 时间戳
    processed_at: Optional[str] = None
    completed_at: Optional[str] = None

    # 结果详情
    success: bool = False  # 是否成功
    error_message: Optional[str] = None  # 错误信息
    provider_response: Optional[Dict[str, Any]] = None  # 支付提供商响应

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class HumanGateRequest:
    """Human Gate 请求协议"""

    gate_id: str  # 闸门唯一ID
    request_type: str = "payment_approval"  # 请求类型
    payload: Dict[str, Any] = field(default_factory=dict)  # 请求负载

    # 状态
    status: str = "pending"  # pending, approved, rejected, cancelled
    priority: str = "normal"  # low, normal, high, critical

    # 人工干预信息
    human_assignee: Optional[str] = None  # 人工处理人
    human_notes: str = ""  # 人工备注

    # 时间戳
    created_at: str = ""
    updated_at: str = ""
    resolved_at: Optional[str] = None

    # 审计追踪
    audit_log: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ==================== 支付审批引擎 ====================


class PaymentApprovalEngine:
    """支付审批引擎"""

    def __init__(self, approval_threshold: float = 100.0, audit_dir: Optional[str] = None):
        """
        初始化支付审批引擎

        Args:
            approval_threshold: 审批阈值（元），超过此金额需要人工审批
            audit_dir: 审计日志目录，默认为 workspace/payment_audit
        """
        self.approval_threshold = approval_threshold

        # 设置审计目录
        if audit_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            self.audit_dir = project_root / "workspace" / "payment_audit"
        else:
            self.audit_dir = Path(audit_dir)

        self.audit_dir.mkdir(parents=True, exist_ok=True)

        self.requests: Dict[str, PaymentRequest] = {}
        self.approvals: Dict[str, PaymentApproval] = {}
        self.results: Dict[str, PaymentResult] = {}

        logger.info(
            f"支付审批引擎初始化完成，审批阈值: {approval_threshold}，审计目录: {self.audit_dir}"
        )

    def _save_audit(self, request_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """
        保存审计记录到文件

        Args:
            request_id: 支付请求ID
            event_type: 事件类型
            data: 事件数据
        """
        try:
            audit_file = self.audit_dir / f"payment_{request_id}.json"

            # 读取现有审计记录或创建新记录
            audit_data = {}
            if audit_file.exists():
                try:
                    audit_data = json.loads(audit_file.read_text(encoding="utf-8"))
                except Exception:
                    audit_data = {}

            # 确保 events 列表存在
            if "events" not in audit_data:
                audit_data["events"] = []

            # 添加新事件
            audit_data["events"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "event_type": event_type,
                    "data": data,
                }
            )

            # 更新元数据
            audit_data["request_id"] = request_id
            audit_data["last_updated"] = datetime.now().isoformat()
            audit_data["event_count"] = len(audit_data["events"])

            # 写入文件
            audit_file.write_text(
                json.dumps(audit_data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            logger.debug(f"审计记录已保存: {audit_file}")

        except Exception as e:
            logger.warning(f"保存审计记录失败: {e}")

    def create_payment_request(
        self,
        amount: float,
        description: str,
        task_id: Optional[str] = None,
        payment_type: str = PaymentType.TASK_PAYMENT.value,
        payer: str = "system",
        payee: str = "",
        metadata: Optional[Dict] = None,
        auto_approve: bool = True,
        approval_threshold: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[PaymentRequest]]:
        """
        创建支付请求

        Returns:
            (success, request_id_or_error, payment_request)
        """
        try:
            # 验证金额
            if amount <= 0:
                return False, "支付金额必须为正数", None

            # 生成请求ID
            request_id = f"pay_req_{uuid.uuid4().hex[:12]}"

            # 确定审批阈值
            threshold = (
                approval_threshold if approval_threshold is not None else self.approval_threshold
            )

            # 确定是否需要审批
            requires_approval = amount > threshold

            # 创建请求对象
            request = PaymentRequest(
                request_id=request_id,
                task_id=task_id,
                amount=amount,
                currency="CNY",
                payment_type=payment_type,
                description=description,
                payer=payer,
                payee=payee,
                metadata=metadata or {},
                requires_approval=requires_approval,
                approval_threshold=threshold,
                auto_approve=auto_approve,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )

            # 存储请求
            self.requests[request_id] = request

            logger.info(
                f"创建支付请求: {request_id}, 金额: {amount}, 需要审批: {requires_approval}"
            )

            # 保存审计记录
            self._save_audit(
                request_id=request_id,
                event_type="payment_request_created",
                data={
                    "amount": amount,
                    "description": description,
                    "requires_approval": requires_approval,
                    "approval_threshold": threshold,
                    "auto_approve": auto_approve,
                    "metadata": metadata or {},
                },
            )

            return True, request_id, request

        except Exception as e:
            logger.error(f"创建支付请求失败: {e}")
            return False, str(e), None

    def evaluate_payment_request(self, request_id: str) -> PaymentApprovalDecision:
        """
        评估支付请求，返回审批决策

        Returns:
            支付审批决策
        """
        if request_id not in self.requests:
            return PaymentApprovalDecision.REJECTED

        request = self.requests[request_id]

        # 检查是否超过审批阈值
        if request.amount > request.approval_threshold:
            # 需要人工审批
            logger.info(
                f"支付请求 {request_id} 金额 {request.amount} 超过阈值 {request.approval_threshold}，需要人工审批"
            )
            return PaymentApprovalDecision.REQUIRES_APPROVAL

        # 检查是否允许自动审批
        if not request.auto_approve:
            logger.info(f"支付请求 {request_id} 不允许自动审批，需要人工审批")
            return PaymentApprovalDecision.REQUIRES_APPROVAL

        # 自动批准
        logger.info(f"支付请求 {request_id} 金额 {request.amount} 在阈值内，自动批准")
        return PaymentApprovalDecision.AUTO_APPROVED

    def create_approval_request(
        self, request_id: str, approver: Optional[str] = None
    ) -> Tuple[bool, str, Optional[PaymentApproval]]:
        """
        创建审批请求

        Returns:
            (success, approval_id_or_error, payment_approval)
        """
        if request_id not in self.requests:
            return False, f"支付请求不存在: {request_id}", None

        # 生成审批ID
        approval_id = f"pay_app_{uuid.uuid4().hex[:12]}"

        # 创建审批对象
        approval = PaymentApproval(
            approval_id=approval_id,
            request_id=request_id,
            decision=PaymentApprovalDecision.PENDING.value,
            approver=approver,
            reason="等待人工审批",
            requested_at=datetime.now().isoformat(),
            expires_at=(
                (datetime.now() + timedelta(days=7)).isoformat()
                if hasattr(__import__("datetime"), "timedelta")
                else None
            ),
            evidence={
                "request_amount": self.requests[request_id].amount,
                "request_description": self.requests[request_id].description,
                "evaluated_at": datetime.now().isoformat(),
            },
        )

        # 存储审批
        self.approvals[approval_id] = approval

        logger.info(f"创建审批请求: {approval_id} 用于支付请求 {request_id}")

        return True, approval_id, approval

    def approve_payment(
        self,
        request_id: str,
        approver: str = "system",
        reason: str = "",
        comments: str = "",
    ) -> Tuple[bool, str]:
        """
        批准支付

        Returns:
            (success, message)
        """
        if request_id not in self.requests:
            return False, f"支付请求不存在: {request_id}"

        # 查找关联的审批
        approval = None
        for app in self.approvals.values():
            if app.request_id == request_id:
                approval = app
                break

        # 更新请求状态
        request = self.requests[request_id]
        request.updated_at = datetime.now().isoformat()

        # 更新审批状态
        if approval:
            approval.decision = PaymentApprovalDecision.APPROVED.value
            approval.approver = approver
            approval.reason = reason if reason else "已批准"
            approval.comments = comments
            approval.decided_at = datetime.now().isoformat()
            approval.audit_trail.append(
                {
                    "action": "approve",
                    "actor": approver,
                    "timestamp": datetime.now().isoformat(),
                    "reason": reason,
                }
            )

        # 创建支付结果
        result = PaymentResult(
            request_id=request_id,
            status=PaymentStatus.APPROVED.value,
            amount=request.amount,
            currency=request.currency,
            success=True,
            processed_at=datetime.now().isoformat(),
        )
        self.results[request_id] = result

        logger.info(f"支付请求 {request_id} 已批准，批准人: {approver}")

        # 保存审计记录
        self._save_audit(
            request_id=request_id,
            event_type="payment_approved",
            data={
                "approver": approver,
                "reason": reason,
                "comments": comments,
                "amount": request.amount,
                "approval_exists": approval is not None,
            },
        )

        return True, "支付已批准"

    def reject_payment(
        self,
        request_id: str,
        approver: str = "system",
        reason: str = "",
        comments: str = "",
    ) -> Tuple[bool, str]:
        """
        拒绝支付

        Returns:
            (success, message)
        """
        if request_id not in self.requests:
            return False, f"支付请求不存在: {request_id}"

        # 查找关联的审批
        approval = None
        for app in self.approvals.values():
            if app.request_id == request_id:
                approval = app
                break

        # 更新请求状态
        request = self.requests[request_id]
        request.updated_at = datetime.now().isoformat()

        # 更新审批状态
        if approval:
            approval.decision = PaymentApprovalDecision.REJECTED.value
            approval.approver = approver
            approval.reason = reason if reason else "已拒绝"
            approval.comments = comments
            approval.decided_at = datetime.now().isoformat()
            approval.audit_trail.append(
                {
                    "action": "reject",
                    "actor": approver,
                    "timestamp": datetime.now().isoformat(),
                    "reason": reason,
                }
            )

        # 创建支付结果
        result = PaymentResult(
            request_id=request_id,
            status=PaymentStatus.REJECTED.value,
            amount=request.amount,
            currency=request.currency,
            success=False,
            error_message=reason,
            processed_at=datetime.now().isoformat(),
        )
        self.results[request_id] = result

        logger.info(f"支付请求 {request_id} 已拒绝，拒绝人: {approver}, 原因: {reason}")

        # 保存审计记录
        self._save_audit(
            request_id=request_id,
            event_type="payment_rejected",
            data={
                "approver": approver,
                "reason": reason,
                "comments": comments,
                "amount": request.amount,
                "approval_exists": approval is not None,
            },
        )

        return True, "支付已拒绝"

    def get_payment_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取支付状态概览"""
        if request_id not in self.requests:
            return None

        request = self.requests[request_id]
        result = self.results.get(request_id)

        # 查找关联的审批
        approval = None
        for app in self.approvals.values():
            if app.request_id == request_id:
                approval = app
                break

        return {
            "request": request.to_dict(),
            "approval": approval.to_dict() if approval else None,
            "result": result.to_dict() if result else None,
            "summary": {
                "amount": request.amount,
                "status": result.status if result else "pending",
                "requires_approval": request.requires_approval,
                "decision": approval.decision if approval else "pending",
            },
        }


# ==================== Human Gate 协议 ====================


class HumanGateProtocol:
    """Human Gate 协议"""

    def __init__(self):
        self.gates: Dict[str, HumanGateRequest] = {}
        logger.info("Human Gate 协议初始化完成")

    def create_gate_request(
        self,
        request_type: str,
        payload: Dict[str, Any],
        priority: str = "normal",
        human_assignee: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[HumanGateRequest]]:
        """
        创建 Human Gate 请求

        Returns:
            (success, gate_id_or_error, human_gate_request)
        """
        try:
            gate_id = f"gate_{uuid.uuid4().hex[:12]}"

            gate = HumanGateRequest(
                gate_id=gate_id,
                request_type=request_type,
                payload=payload,
                priority=priority,
                human_assignee=human_assignee,
                status="pending",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                audit_log=[
                    {
                        "action": "create",
                        "timestamp": datetime.now().isoformat(),
                        "actor": "system",
                    }
                ],
            )

            self.gates[gate_id] = gate

            logger.info(
                f"创建 Human Gate 请求: {gate_id}, 类型: {request_type}, 优先级: {priority}"
            )

            return True, gate_id, gate

        except Exception as e:
            logger.error(f"创建 Human Gate 请求失败: {e}")
            return False, str(e), None

    def approve_gate(
        self,
        gate_id: str,
        approver: str,
        notes: str = "",
        metadata: Optional[Dict] = None,
    ) -> Tuple[bool, str]:
        """批准 Human Gate 请求"""
        if gate_id not in self.gates:
            return False, f"Human Gate 请求不存在: {gate_id}"

        gate = self.gates[gate_id]
        gate.status = "approved"
        gate.human_notes = notes
        gate.resolved_at = datetime.now().isoformat()
        gate.updated_at = datetime.now().isoformat()
        gate.audit_log.append(
            {
                "action": "approve",
                "actor": approver,
                "timestamp": datetime.now().isoformat(),
                "notes": notes,
                "metadata": metadata or {},
            }
        )

        logger.info(f"Human Gate 请求 {gate_id} 已批准，批准人: {approver}")

        return True, "Human Gate 请求已批准"

    def reject_gate(
        self,
        gate_id: str,
        approver: str,
        reason: str = "",
        metadata: Optional[Dict] = None,
    ) -> Tuple[bool, str]:
        """拒绝 Human Gate 请求"""
        if gate_id not in self.gates:
            return False, f"Human Gate 请求不存在: {gate_id}"

        gate = self.gates[gate_id]
        gate.status = "rejected"
        gate.human_notes = reason
        gate.resolved_at = datetime.now().isoformat()
        gate.updated_at = datetime.now().isoformat()
        gate.audit_log.append(
            {
                "action": "reject",
                "actor": approver,
                "timestamp": datetime.now().isoformat(),
                "reason": reason,
                "metadata": metadata or {},
            }
        )

        logger.info(f"Human Gate 请求 {gate_id} 已拒绝，拒绝人: {approver}, 原因: {reason}")

        return True, "Human Gate 请求已拒绝"

    def get_gate_status(self, gate_id: str) -> Optional[Dict[str, Any]]:
        """获取 Human Gate 请求状态"""
        if gate_id not in self.gates:
            return None

        gate = self.gates[gate_id]
        return gate.to_dict()


# ==================== 全局实例 ====================

_payment_engine_instance: Optional[PaymentApprovalEngine] = None
_human_gate_instance: Optional[HumanGateProtocol] = None


def get_payment_engine(approval_threshold: float = 100.0) -> PaymentApprovalEngine:
    """获取全局支付审批引擎实例"""
    global _payment_engine_instance
    if _payment_engine_instance is None:
        _payment_engine_instance = PaymentApprovalEngine(approval_threshold)
    return _payment_engine_instance


def get_human_gate() -> HumanGateProtocol:
    """获取全局 Human Gate 协议实例"""
    global _human_gate_instance
    if _human_gate_instance is None:
        _human_gate_instance = HumanGateProtocol()
    return _human_gate_instance


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=== Payment Contract 测试 ===")

    # 测试支付审批引擎
    engine = PaymentApprovalEngine(approval_threshold=50.0)

    print("\n1. 测试小额支付（自动批准）:")
    success, req_id, request = engine.create_payment_request(
        amount=30.0,
        description="测试小额支付",
        task_id="task_123",
        auto_approve=True,
    )

    if success and request:
        decision = engine.evaluate_payment_request(req_id)
        print(f"   请求ID: {req_id}, 金额: {request.amount}, 决策: {decision.value}")

        if decision == PaymentApprovalDecision.AUTO_APPROVED:
            engine.approve_payment(req_id, approver="system", reason="自动批准")
            print("   已自动批准")

    print("\n2. 测试大额支付（需要人工审批）:")
    success, req_id2, request2 = engine.create_payment_request(
        amount=150.0,
        description="测试大额支付",
        task_id="task_456",
        auto_approve=True,
    )

    if success and request2:
        decision = engine.evaluate_payment_request(req_id2)
        print(f"   请求ID: {req_id2}, 金额: {request2.amount}, 决策: {decision.value}")

        if decision == PaymentApprovalDecision.REQUIRES_APPROVAL:
            success2, app_id, approval = engine.create_approval_request(
                req_id2, approver="human_user"
            )
            if success2 and approval:
                print(f"   已创建审批请求: {app_id}")

    print("\n3. 测试 Human Gate 协议:")
    gate = HumanGateProtocol()
    success, gate_id, gate_req = gate.create_gate_request(
        request_type="payment_approval",
        payload={"request_id": req_id2, "amount": 150.0},
        priority="high",
        human_assignee="admin",
    )

    if success and gate_req:
        print(f"   Gate ID: {gate_id}, 状态: {gate_req.status}")

        # 模拟人工批准
        gate.approve_gate(gate_id, approver="admin", notes="同意支付")
        status = gate.get_gate_status(gate_id)
        if status:
            print(f"   批准后状态: {status['status']}")

    print("\n=== 测试完成 ===")
