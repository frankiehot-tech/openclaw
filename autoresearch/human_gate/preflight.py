"""Human Gate pre-flight check — hard-coded human approval gate.

Runs BEFORE any P0 task starts in the consumption pipeline.
Integrates the existing HumanGate 3-layer architecture into a
CLI-based pre-flight approval checkpoint.

Usage:
    python -m autoresearch.human_gate.preflight --action deploy_to_production
    python -m autoresearch.human_gate.preflight --action modify_permissions --auto-reject

Exit codes:
    0 — Approved (task can proceed)
    2 — Requires human approval (Exit Code 2 protocol)
    1 — Error
"""

from __future__ import annotations

import argparse
import sys

from autoresearch.human_gate.gate import (
    EXIT_CODE_HUMAN_GATE,
    HIGH_RISK_ACTIONS,
    GateAction,
    HumanGate,
)

P0_TASK_ACTIONS = {
    "openhuman_human_gate_v2": "Human Gate v2 安全逻辑变更 (OpenHuman)",
    "openhuman_permissions": "权限矩阵修改 (OpenHuman)",
    "openhuman_budget": "Evolution Budget 超限 (OpenHuman)",
    "maref_tla": "TLA+ 安全属性定义 (MAREF)",
    "maref_redline": "七层红线变更 (MAREF)",
    "openclaw_men0_keys": "Men0 Protocol 安全密钥更新 (OpenClaw)",
    "athena_ff_highrisk": "Feature Flag 高危操作开放 (Athena)",
}


def format_p0_task_list() -> str:
    lines = ["已知 P0 阻断任务:"]
    for action_id, desc in P0_TASK_ACTIONS.items():
        lines.append(f"  {action_id}: {desc}")
    return "\n".join(lines)


def check_p0_task(action_id: str) -> bool:
    if action_id in P0_TASK_ACTIONS:
        return True
    return any(known in action_id for known in HIGH_RISK_ACTIONS)


def human_approve(action: str, auto_reject: bool = False) -> GateAction:
    desc = P0_TASK_ACTIONS.get(action, action)
    bar = "═" * 60
    print(f"\n╔{bar}╗")
    print("║  Human Gate v2 — 前置审批检查 (Pre-flight Check)          ║")
    print(f"╠{bar}╣")
    print(f"║  操作: {desc}")
    print("║  风险: P0 (同步阻断)")
    print(f"╚{bar}╝")

    if auto_reject:
        print("\n[Human Gate] auto-reject 模式：拒绝所有审批请求。")
        print("Exit Code 2 — 需要人工审批后才能继续。")
        return GateAction.REJECTED

    try:
        response = input("\n是否批准执行? [y/N/abort]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return GateAction.REJECTED

    if response == "abort":
        print("已中止。")
        return GateAction.REJECTED
    if response == "y" or response == "yes":
        print("已批准。")
        return GateAction.APPROVED
    print("未批准。")
    return GateAction.REJECTED


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Human Gate v2 pre-flight check — P0 task approval checkpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "已知 P0 任务:\n" + format_p0_task_list() + "\n\n"
            "退出码:\n  0 = 批准\n  2 = 需审批 (Exit Code 2)\n  1 = 错误"
        ),
    )
    parser.add_argument(
        "--action", "-a",
        help="P0任务操作标识 (如 openhuman_human_gate_v2, maref_tla)",
    )
    parser.add_argument(
        "--auto-reject",
        action="store_true",
        help="自动拒绝所有审批 (用于CI/CD非交互环境)",
    )
    parser.add_argument(
        "--list-p0",
        action="store_true",
        help="列出所有P0阻断任务然后退出",
    )
    parser.add_argument(
        "--storage",
        default=".openclaw/gate_requests",
        help="Gate请求存储路径 (默认: .openclaw/gate_requests)",
    )
    args = parser.parse_args()

    if args.list_p0:
        print(format_p0_task_list())
        sys.exit(0)

    if not args.action:
        parser.error("--action/-a is required (or use --list-p0 to see available actions)")

    if not check_p0_task(args.action):
        print(f"[Human Gate] {args.action} 不在 P0 阻断列表中，允许通过 (通过前检查)")
        if args.action not in HIGH_RISK_ACTIONS:
            sys.exit(0)

    gate = HumanGate(storage_path=args.storage)

    request_obj = gate.check_and_block(args.action, identity_id="workflow-consumer")
    if request_obj.status == GateAction.APPROVED:
        print(f"[Human Gate] {args.action} 无需审批 — 已自动通过。")
        sys.exit(0)

    decision = human_approve(args.action, auto_reject=args.auto_reject)

    if decision == GateAction.APPROVED:
        gate.human_approve(request_obj.request_id, reviewer_id="human-operator")
        print(f"[Human Gate] {args.action} 审批通过。继续执行。")
        sys.exit(0)
    else:
        gate.human_reject(
            request_obj.request_id,
            reviewer_id="human-operator",
            reason="pre-flight check rejected",
        )
        print(f"[Human Gate] {args.action} 审批被拒绝。Exit Code {EXIT_CODE_HUMAN_GATE}")
        sys.exit(EXIT_CODE_HUMAN_GATE)


if __name__ == "__main__":
    main()
