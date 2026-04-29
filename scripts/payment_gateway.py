#!/usr/bin/env python3
"""
Payment Gateway - 支付审批接口与 Human Gate 接线

提供最小支付审批接口，集成支付契约和 Human Gate 协议。
支持小额自动批准/大额人工审批分流，与 Athena 任务执行链集成。
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入支付契约
try:
    from mini_agent.agent.core.payment_contract import (
        PaymentApprovalDecision,
        PaymentType,
        get_human_gate,
        get_payment_engine,
    )

    PAYMENT_CONTRACT_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"无法导入支付契约模块: {e}")
    PAYMENT_CONTRACT_AVAILABLE = False

# 导入预算引擎（可选）
try:
    from mini_agent.agent.core.budget_engine import (
        BudgetCheckRequest,
        get_budget_engine,
    )

    BUDGET_ENGINE_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"无法导入预算引擎模块: {e}")
    BUDGET_ENGINE_AVAILABLE = False

# 导入编排器（可选）
try:
    from mini_agent.agent.core.athena_orchestrator import get_orchestrator

    ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"无法导入编排器模块: {e}")
    ORCHESTRATOR_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== 支付网关核心 ====================


class PaymentGateway:
    """支付网关"""

    def __init__(self, approval_threshold: float = 100.0):
        """
        初始化支付网关

        Args:
            approval_threshold: 审批阈值（元），超过此金额需要人工审批
        """
        self.approval_threshold = approval_threshold

        # 初始化支付引擎
        if PAYMENT_CONTRACT_AVAILABLE:
            self.payment_engine = get_payment_engine(approval_threshold)
            self.human_gate = get_human_gate()
        else:
            self.payment_engine = None
            self.human_gate = None

        # 初始化预算引擎（如果可用）
        if BUDGET_ENGINE_AVAILABLE:
            self.budget_engine = get_budget_engine()
        else:
            self.budget_engine = None

        # 初始化编排器（如果可用）
        if ORCHESTRATOR_AVAILABLE:
            self.orchestrator = get_orchestrator()
        else:
            self.orchestrator = None

        logger.info(f"支付网关初始化完成，审批阈值: {approval_threshold}")

    def submit_payment_request(
        self,
        amount: float,
        description: str,
        task_id: str | None = None,
        payment_type: str = PaymentType.TASK_PAYMENT.value,
        payer: str = "system",
        payee: str = "",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """
        提交支付请求

        Returns:
            支付请求响应
        """
        if not self.payment_engine:
            return {
                "success": False,
                "error": "支付引擎不可用",
                "error_type": "payment_engine_unavailable",
            }

        try:
            # 1. 创建支付请求
            success, request_id, request = self.payment_engine.create_payment_request(
                amount=amount,
                description=description,
                task_id=task_id,
                payment_type=payment_type,
                payer=payer,
                payee=payee,
                metadata=metadata or {},
                auto_approve=True,
                approval_threshold=self.approval_threshold,
            )

            if not success or not request:
                return {
                    "success": False,
                    "error": f"创建支付请求失败: {request_id}",
                    "error_type": "create_request_failed",
                }

            # 2. 评估支付请求（自动/人工审批决策）
            decision = self.payment_engine.evaluate_payment_request(request_id)

            # 3. 根据决策处理
            if decision == PaymentApprovalDecision.AUTO_APPROVED:
                # 自动批准
                self.payment_engine.approve_payment(
                    request_id,
                    approver="system",
                    reason=f"金额 {amount} 低于审批阈值 {self.approval_threshold}，自动批准",
                )

                return {
                    "success": True,
                    "request_id": request_id,
                    "decision": decision.value,
                    "status": "auto_approved",
                    "message": "支付请求已自动批准",
                    "amount": amount,
                    "requires_human_approval": False,
                    "human_gate_id": None,
                }

            elif decision == PaymentApprovalDecision.REQUIRES_APPROVAL:
                # 需要人工审批
                # 创建审批请求
                success, approval_id, approval = self.payment_engine.create_approval_request(
                    request_id, approver=None
                )

                # 创建 Human Gate 请求
                if self.human_gate and success:
                    gate_success, gate_id, gate_request = self.human_gate.create_gate_request(
                        request_type="payment_approval",
                        payload={
                            "payment_request_id": request_id,
                            "amount": amount,
                            "description": description,
                            "task_id": task_id,
                            "approval_id": approval_id,
                        },
                        priority="high" if amount > 500.0 else "normal",
                        human_assignee="admin",
                    )

                    if gate_success:
                        logger.info(
                            f"支付请求 {request_id} 需要人工审批，已创建 Human Gate: {gate_id}"
                        )

                        return {
                            "success": True,
                            "request_id": request_id,
                            "decision": decision.value,
                            "status": "pending_human_approval",
                            "message": "支付请求需要人工审批",
                            "amount": amount,
                            "requires_human_approval": True,
                            "human_gate_id": gate_id,
                            "approval_id": approval_id,
                        }

                # Human Gate 不可用或创建失败，返回基本响应
                return {
                    "success": True,
                    "request_id": request_id,
                    "decision": decision.value,
                    "status": "pending_human_approval",
                    "message": "支付请求需要人工审批",
                    "amount": amount,
                    "requires_human_approval": True,
                    "human_gate_id": None,
                    "approval_id": approval_id if success else None,
                }

            else:
                # 拒绝
                return {
                    "success": False,
                    "request_id": request_id,
                    "decision": decision.value,
                    "status": "rejected",
                    "message": "支付请求被拒绝",
                    "amount": amount,
                    "requires_human_approval": False,
                }

        except Exception as e:
            logger.error(f"提交支付请求失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def approve_payment_request(
        self,
        request_id: str,
        approver: str = "admin",
        reason: str = "",
        comments: str = "",
    ) -> dict[str, Any]:
        """
        批准支付请求

        Returns:
            批准响应
        """
        if not self.payment_engine:
            return {
                "success": False,
                "error": "支付引擎不可用",
                "error_type": "payment_engine_unavailable",
            }

        try:
            success, message = self.payment_engine.approve_payment(
                request_id, approver=approver, reason=reason, comments=comments
            )

            if success:
                # 更新关联的 Human Gate 状态（如果存在）
                if self.human_gate:
                    # 查找关联的 gate
                    # 这里简化实现：在实际系统中需要维护 request_id 到 gate_id 的映射
                    pass

                return {
                    "success": True,
                    "message": message,
                    "request_id": request_id,
                    "status": "approved",
                }
            else:
                return {
                    "success": False,
                    "error": message,
                    "request_id": request_id,
                    "status": "approval_failed",
                }

        except Exception as e:
            logger.error(f"批准支付请求失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def reject_payment_request(
        self,
        request_id: str,
        approver: str = "admin",
        reason: str = "",
        comments: str = "",
    ) -> dict[str, Any]:
        """
        拒绝支付请求

        Returns:
            拒绝响应
        """
        if not self.payment_engine:
            return {
                "success": False,
                "error": "支付引擎不可用",
                "error_type": "payment_engine_unavailable",
            }

        try:
            success, message = self.payment_engine.reject_payment(
                request_id, approver=approver, reason=reason, comments=comments
            )

            if success:
                return {
                    "success": True,
                    "message": message,
                    "request_id": request_id,
                    "status": "rejected",
                }
            else:
                return {
                    "success": False,
                    "error": message,
                    "request_id": request_id,
                    "status": "rejection_failed",
                }

        except Exception as e:
            logger.error(f"拒绝支付请求失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def get_payment_status(self, request_id: str) -> dict[str, Any]:
        """
        获取支付状态

        Returns:
            支付状态响应
        """
        if not self.payment_engine:
            return {
                "success": False,
                "error": "支付引擎不可用",
                "error_type": "payment_engine_unavailable",
            }

        try:
            status = self.payment_engine.get_payment_status(request_id)

            if status:
                return {
                    "success": True,
                    "status": status,
                    "request_id": request_id,
                }
            else:
                return {
                    "success": False,
                    "error": f"支付请求不存在: {request_id}",
                    "request_id": request_id,
                }

        except Exception as e:
            logger.error(f"获取支付状态失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def check_budget_before_payment(
        self,
        amount: float,
        task_id: str,
        task_type: str = "general",
        is_essential: bool = False,
        description: str = "",
    ) -> dict[str, Any]:
        """
        支付前预算检查（如果预算引擎可用）

        Returns:
            预算检查响应
        """
        if not self.budget_engine:
            return {
                "success": True,  # 预算引擎不可用时默认通过
                "budget_check_available": False,
                "message": "预算引擎不可用，跳过预算检查",
                "recommendation": "proceed_with_caution",
            }

        try:
            request = BudgetCheckRequest(
                task_id=task_id or f"payment_precheck_{hash(str(amount))}",
                estimated_cost=amount,
                task_type=task_type,
                is_essential=is_essential,
                description=description[:100] if description else "",
                metadata={"payment_check": True, "amount": amount},
            )

            result = self.budget_engine.check_budget(request)

            return {
                "success": result.allowed,
                "budget_check_available": True,
                "decision": result.decision.value,
                "allowed": result.allowed,
                "reason": result.reason,
                "requires_approval": result.requires_approval,
                "recommendation": "proceed" if result.allowed else "reject",
                "budget_result": result.to_dict(),
            }

        except Exception as e:
            logger.warning(f"预算检查失败: {e}")
            return {
                "success": True,  # 检查失败时默认通过
                "budget_check_available": False,
                "error": str(e),
                "message": "预算检查失败，继续支付处理",
                "recommendation": "proceed_with_caution",
            }

    def process_payment_with_budget_check(
        self, amount: float, description: str, task_id: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """
        带预算检查的支付处理

        Returns:
            支付处理响应
        """
        # 1. 预算检查
        budget_check = self.check_budget_before_payment(
            amount=amount,
            task_id=task_id or f"payment_{hash(str(amount))}",
            task_type="payment",
            is_essential=False,
            description=description,
        )

        # 2. 如果预算检查不通过且不允许继续，则返回
        if not budget_check["success"] and not budget_check.get("allowed", True):
            return {
                "success": False,
                "error": "预算检查不通过",
                "budget_check": budget_check,
                "payment_processed": False,
            }

        # 3. 提交支付请求
        payment_response = self.submit_payment_request(
            amount=amount, description=description, task_id=task_id, **kwargs
        )

        # 4. 合并响应
        response = {
            **payment_response,
            "budget_check": budget_check,
            "payment_processed": payment_response.get("success", False),
        }

        return response


# ==================== CLI 接口 ====================


def main():
    """命令行接口主函数"""
    parser = argparse.ArgumentParser(description="支付审批接口与 Human Gate 接线")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # submit 命令
    submit_parser = subparsers.add_parser("submit", help="提交支付请求")
    submit_parser.add_argument("--amount", type=float, required=True, help="支付金额（元）")
    submit_parser.add_argument("--description", type=str, required=True, help="支付描述")
    submit_parser.add_argument("--task-id", type=str, help="关联的任务ID")
    submit_parser.add_argument(
        "--payment-type",
        type=str,
        default="task_payment",
        choices=[t.value for t in PaymentType],
        help="支付类型",
    )
    submit_parser.add_argument("--payer", type=str, default="system", help="付款方")
    submit_parser.add_argument("--payee", type=str, default="", help="收款方")
    submit_parser.add_argument("--threshold", type=float, default=100.0, help="审批阈值（元）")

    # approve 命令
    approve_parser = subparsers.add_parser("approve", help="批准支付请求")
    approve_parser.add_argument("--request-id", type=str, required=True, help="支付请求ID")
    approve_parser.add_argument("--approver", type=str, default="admin", help="审批人")
    approve_parser.add_argument("--reason", type=str, default="", help="审批理由")
    approve_parser.add_argument("--comments", type=str, default="", help="审批备注")

    # reject 命令
    reject_parser = subparsers.add_parser("reject", help="拒绝支付请求")
    reject_parser.add_argument("--request-id", type=str, required=True, help="支付请求ID")
    reject_parser.add_argument("--approver", type=str, default="admin", help="审批人")
    reject_parser.add_argument("--reason", type=str, default="", help="拒绝理由")
    reject_parser.add_argument("--comments", type=str, default="", help="拒绝备注")

    # status 命令
    status_parser = subparsers.add_parser("status", help="获取支付状态")
    status_parser.add_argument("--request-id", type=str, required=True, help="支付请求ID")

    # test 命令
    test_parser = subparsers.add_parser("test", help="运行测试用例")
    test_parser.add_argument("--threshold", type=float, default=100.0, help="审批阈值（元）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 初始化支付网关
    threshold = getattr(args, "threshold", 100.0)
    gateway = PaymentGateway(approval_threshold=threshold)

    # 处理命令
    if args.command == "submit":
        response = gateway.submit_payment_request(
            amount=args.amount,
            description=args.description,
            task_id=args.task_id,
            payment_type=args.payment_type,
            payer=args.payer,
            payee=args.payee,
        )
        print(json.dumps(response, ensure_ascii=False, indent=2))

    elif args.command == "approve":
        response = gateway.approve_payment_request(
            request_id=args.request_id,
            approver=args.approver,
            reason=args.reason,
            comments=args.comments,
        )
        print(json.dumps(response, ensure_ascii=False, indent=2))

    elif args.command == "reject":
        response = gateway.reject_payment_request(
            request_id=args.request_id,
            approver=args.approver,
            reason=args.reason,
            comments=args.comments,
        )
        print(json.dumps(response, ensure_ascii=False, indent=2))

    elif args.command == "status":
        response = gateway.get_payment_status(args.request_id)
        print(json.dumps(response, ensure_ascii=False, indent=2))

    elif args.command == "test":
        run_tests(threshold)

    else:
        parser.print_help()


def run_tests(threshold: float = 100.0):
    """运行测试用例"""
    print("=== 支付网关测试 ===")

    gateway = PaymentGateway(approval_threshold=threshold)

    print(f"\n1. 测试小额支付（< {threshold} 元，应自动批准）:")
    response = gateway.submit_payment_request(
        amount=threshold - 10.0,
        description="测试小额支付",
        task_id="test_task_001",
    )
    print(f"   响应: {json.dumps(response, ensure_ascii=False, indent=2)}")

    print(f"\n2. 测试大额支付（> {threshold} 元，应需要人工审批）:")
    response = gateway.submit_payment_request(
        amount=threshold + 50.0,
        description="测试大额支付",
        task_id="test_task_002",
    )
    print(f"   响应: {json.dumps(response, ensure_ascii=False, indent=2)}")

    print("\n3. 测试负路径（非法金额）:")
    response = gateway.submit_payment_request(
        amount=-10.0,
        description="测试非法金额",
        task_id="test_task_003",
    )
    print(f"   响应: {json.dumps(response, ensure_ascii=False, indent=2)}")

    print("\n4. 测试预算检查（如果预算引擎可用）:")
    budget_check = gateway.check_budget_before_payment(
        amount=200.0,
        task_id="test_task_004",
        description="测试预算检查",
    )
    print(f"   预算检查结果: {json.dumps(budget_check, ensure_ascii=False, indent=2)}")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    main()
