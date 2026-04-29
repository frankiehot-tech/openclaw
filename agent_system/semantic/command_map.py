"""
Command Map - 意图到系统治理函数的映射表

每个意图类型映射到一个或多个可执行的系统操作函数。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .intent_parser import IntentType, ParsedIntent

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 系统导入（延迟加载，避免循环依赖）
# ------------------------------------------------------------------

_GOVERNANCE_LOADED = False


def _ensure_governance():
    """延迟加载 governance 模块。"""
    global _GOVERNANCE_LOADED
    if _GOVERNANCE_LOADED:
        return
    import sys

    agent_system_path = str(Path(__file__).resolve().parents[1])
    if agent_system_path not in sys.path:
        sys.path.insert(0, agent_system_path)
    _GOVERNANCE_LOADED = True


# ------------------------------------------------------------------
# 命令处理函数
# ------------------------------------------------------------------


def _cmd_queue_health(intent: ParsedIntent) -> dict[str, Any]:
    """队列健康检查命令。"""
    _ensure_governance()
    from agent_system.governance.queue_manager import get_queue_manager
    from agent_system.governance.system_health import get_system_health

    qm = get_queue_manager()
    sh = get_system_health()

    queues = qm.get_all_queues()
    stalled = sh.detect_stalled_queues()

    return {
        "queues": queues,
        "stalled_queues": stalled,
        "stalled_count": len(stalled),
        "summary": f"Found {queues.get('total', 0)} queues, {len(stalled)} stalled",
    }


def _cmd_system_audit(intent: ParsedIntent) -> dict[str, Any]:
    """系统审计命令。"""
    _ensure_governance()
    from agent_system.governance.queue_manager import get_queue_manager
    from agent_system.governance.system_health import get_system_health

    qm = get_queue_manager()
    sh = get_system_health()

    queues = qm.get_all_queues()
    counts = qm.get_queue_counts()
    stalled = sh.detect_stalled_queues()
    heal_log = sh.get_heal_log()

    total_pending = sum(c.get("pending", 0) for c in counts.values())
    total_failed = sum(c.get("failed", 0) for c in counts.values())
    total_completed = sum(c.get("completed", 0) for c in counts.values())

    return {
        "queues": queues,
        "counts": counts,
        "stalled_queues": stalled,
        "heal_log_tail": heal_log[-10:],
        "summary": {
            "total_queues": queues.get("total", 0),
            "total_pending": total_pending,
            "total_failed": total_failed,
            "total_completed": total_completed,
            "stalled_queues": len(stalled),
        },
    }


def _cmd_status_report(intent: ParsedIntent) -> dict[str, Any]:
    """状态报告命令。"""
    _ensure_governance()
    from agent_system.governance.queue_manager import get_queue_manager
    from agent_system.governance.system_health import get_system_health

    qm = get_queue_manager()
    sh = get_system_health()

    stalled = sh.detect_stalled_queues()
    counts = qm.get_queue_counts()

    # 统计汇总
    total_pending = sum(c.get("pending", 0) for c in counts.values())
    total_running = sum(c.get("running", 0) for c in counts.values())
    total_completed = sum(c.get("completed", 0) for c in counts.values())
    total_failed = sum(c.get("failed", 0) for c in counts.values())

    return {
        "summary": {
            "pending": total_pending,
            "running": total_running,
            "completed": total_completed,
            "failed": total_failed,
            "stalled_queues": len(stalled),
            "overall_health": "healthy" if len(stalled) == 0 else "degraded",
        },
        "stalled_details": stalled,
        "queue_counts": counts,
    }


def _cmd_fix_issue(intent: ParsedIntent) -> dict[str, Any]:
    """修复问题命令。"""
    _ensure_governance()
    from agent_system.governance.system_health import get_system_health

    sh = get_system_health()
    stalled = sh.detect_stalled_queues()

    if intent.entities.get("queue_name"):
        # 只修复指定队列
        target = intent.entities["queue_name"]
        filtered = [q for q in stalled if q["queue_name"] == target]
    else:
        filtered = stalled

    if not filtered:
        return {
            "action": "fix_issue",
            "healed": False,
            "summary": "No stalled queues detected to fix",
            "results": [],
        }

    results = sh.auto_heal(filtered)
    healed = [r for r in results if r.get("success")]
    escalated = [r for r in results if r.get("action") == "escalate"]

    return {
        "action": "fix_issue",
        "healed": len(healed) > 0,
        "healed_count": len(healed),
        "escalated_count": len(escalated),
        "summary": f"Healed {len(healed)} queues, escalated {len(escalated)}",
        "results": results,
    }


def _cmd_deploy(intent: ParsedIntent) -> dict[str, Any]:
    """部署命令 stub。"""
    return {
        "action": "deploy",
        "healed": False,
        "summary": "Deploy command stub - requires manual execution via athena_ai_plan_runner",
        "note": "Deploy is a sensitive operation requiring explicit confirmation",
    }


def _cmd_autoresearch(intent: ParsedIntent) -> dict[str, Any]:
    """激活 AutoResearch 引擎。"""
    import sys
    from pathlib import Path

    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        from athena_autoresearch_engine import AutoResearchEngine

        engine = AutoResearchEngine(dry_run=True)
        result = engine.run_cycle()

        return {
            "action": "autoresearch",
            "healed": False,
            "cycle_id": result.cycle_id,
            "findings": len(result.findings),
            "recommendations": len(result.recommendations),
            "summary": result.summary,
            "recommendations_detail": [
                {
                    "id": r.id,
                    "title": r.title,
                    "risk": r.risk_level.value,
                    "confidence": r.confidence,
                    "requires_confirmation": r.requires_manual_confirmation,
                }
                for r in result.recommendations
            ],
        }
    except ImportError as e:
        return {
            "action": "autoresearch",
            "healed": False,
            "error": f"AutoResearch engine not available: {e}",
            "summary": "AutoResearch engine import failed",
        }


def _cmd_unknown(intent: ParsedIntent) -> dict[str, Any]:
    """未知命令处理。"""
    return {
        "action": "unknown",
        "healed": False,
        "available_commands": get_available_commands(),
        "summary": f"Unknown intent. Available commands: {', '.join(get_available_commands())}",
    }


# ------------------------------------------------------------------
# 主映射表
# ------------------------------------------------------------------

COMMAND_MAP: dict[IntentType, Callable[[ParsedIntent], dict[str, Any]]] = {
    IntentType.QUEUE_HEALTH: _cmd_queue_health,
    IntentType.SYSTEM_AUDIT: _cmd_system_audit,
    IntentType.STATUS_REPORT: _cmd_status_report,
    IntentType.FIX_ISSUE: _cmd_fix_issue,
    IntentType.DEPLOY: _cmd_deploy,
    IntentType.AUTORESEARCH: _cmd_autoresearch,
    IntentType.UNKNOWN: _cmd_unknown,
}


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def execute_intent(intent: ParsedIntent) -> dict[str, Any]:
    """根据解析后的意图执行对应的系统操作。

    Args:
        intent: parse_intent() 返回的 ParsedIntent

    Returns:
        执行结果 dict，包含 action, healed, summary 等字段
    """
    handler = COMMAND_MAP.get(intent.intent, _cmd_unknown)
    try:
        result = handler(intent)
        if "action" not in result:
            result["action"] = intent.intent.value
        if "healed" not in result:
            result["healed"] = result.get("action") != "unknown"
        return result
    except Exception as e:
        logger.error(f"Command execution failed for {intent.intent}: {e}", exc_info=True)
        return {
            "action": intent.intent.value,
            "healed": False,
            "error": str(e),
            "summary": f"Execution failed: {e}",
        }


def get_available_commands() -> list[str]:
    """获取所有可用命令名称列表。"""
    return [t.value for t in COMMAND_MAP if t != IntentType.UNKNOWN]
