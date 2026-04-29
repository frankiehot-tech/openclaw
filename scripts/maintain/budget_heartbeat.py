#!/usr/bin/env python3
"""
预算心跳脚本

提供预算状态的定时检查或手动调用入口。
输出结构化 budget state 供其他系统消费。

使用方式：
1. 手动运行：python budget_heartbeat.py
2. 定时任务：cron 或 systemd timer
3. 集成调用：作为模块导入使用
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 添加 mini-agent 目录到路径（通过符号链接 mini_agent）
mini_agent_dir = project_root / "mini-agent"
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_heartbeat(
    output_format: str = "json",
    alert_on_critical: bool = True,
    include_alerts: bool = False,
) -> dict[str, Any]:
    """
    运行预算心跳检查

    Args:
        output_format: 输出格式 json/text
        alert_on_critical: 是否在临界状态时发出警告
        include_alerts: 是否包含结构化告警输出

    Returns:
        预算状态字典，可选包含告警
    """
    try:
        # 导入预算引擎
        from mini_agent.agent.core.budget_engine import get_budget_engine

        engine = get_budget_engine()
        state = engine.get_structured_state()

        # 获取告警（如果请求）
        alerts = None
        if include_alerts:
            alerts = engine.get_alerts()

        # 检查是否需要警告
        if alert_on_critical:
            mode = state["budget_state"]["current_mode"]
            utilization = state["health"]["utilization"]
            remaining = state["budget_state"]["remaining"]

            if mode in ["critical", "paused"]:
                logger.warning(
                    f"⚠️ 预算状态异常: 模式={mode}, 使用率={utilization:.1%}, 剩余={remaining:.2f}"
                )
            elif mode == "low" and utilization > 0.8:
                logger.warning(
                    f"⚠️ 预算使用率较高: 模式={mode}, 使用率={utilization:.1%}, 剩余={remaining:.2f}"
                )

        # 根据格式输出
        if output_format == "text":
            _print_text_summary(state, alerts)
        else:  # json
            output_data = state
            if include_alerts:
                output_data = {**state, "alerts": alerts}
            print(json.dumps(output_data, ensure_ascii=False, indent=2))

        # 返回数据
        if include_alerts:
            return {**state, "alerts": alerts}
        else:
            return state

    except ImportError as e:
        logger.error(f"无法导入预算引擎: {e}")
        if include_alerts:
            return {
                "error": "budget_engine_not_available",
                "message": str(e),
                "alerts": {
                    "error": "budget_engine_not_available",
                    "message": str(e),
                    "indicators": {},
                    "warnings": [],
                    "alerts": [],
                    "recommendations": [],
                },
            }
        else:
            return {"error": "budget_engine_not_available", "message": str(e)}
    except Exception as e:
        logger.error(f"预算心跳检查失败: {e}", exc_info=True)
        if include_alerts:
            return {
                "error": "heartbeat_failed",
                "message": str(e),
                "alerts": {
                    "error": "heartbeat_failed",
                    "message": str(e),
                    "indicators": {},
                    "warnings": [],
                    "alerts": [],
                    "recommendations": [],
                },
            }
        else:
            return {"error": "heartbeat_failed", "message": str(e)}


def _print_text_summary(state: dict, alerts: dict[str, Any] | None = None):
    """打印文本摘要"""
    budget = state["budget_state"]
    health = state["health"]
    stats = state["statistics"]

    print("=" * 60)
    print("📊 预算心跳检查报告")
    print("=" * 60)
    print(f"📅 日期: {budget['date']}")
    print(f"💰 周期预算: ¥{budget['period_budget']:.2f}")
    print(f"💸 已消费: ¥{budget['consumed']:.2f}")
    print(f"✅ 剩余预算: ¥{budget['remaining']:.2f}")
    print(f"📈 使用率: {health['utilization']:.1%}")
    print("")
    print(f"🔧 当前模式: {budget['current_mode'].upper()}")
    print(f"📝 模式原因: {budget['mode_reason']}")
    print(f"⏰ 下次重置: {budget['next_reset']} ({health['days_until_reset']}天后)")
    print("")
    print("📊 任务统计:")
    print(
        f"  批准: {stats['tasks_approved']} | 拒绝: {stats['tasks_rejected']} | 降级: {stats['tasks_degraded']}"
    )
    print(f"  总成本: ¥{stats['total_cost']:.2f} | 平均成本: ¥{stats['avg_cost_per_task']:.2f}")
    print("")
    print(f"💡 建议: {health['recommendation']}")

    # 打印告警（如果提供）
    if alerts and (alerts.get("warnings") or alerts.get("alerts")):
        print("")
        print("🚨 告警与警告:")
        for alert in alerts.get("alerts", []):
            print(f"  🔴 {alert.get('level', '').upper()}: {alert.get('message', '')}")
            if alert.get("action"):
                print(f"     建议: {alert.get('action')}")
        for warning in alerts.get("warnings", []):
            print(f"  🟡 {warning.get('level', '').upper()}: {warning.get('message', '')}")
            if warning.get("action"):
                print(f"     建议: {warning.get('action')}")

    print("=" * 60)


def check_budget_for_task(task_id: str, estimated_cost: float, **kwargs) -> dict:
    """
    为特定任务检查预算（预检入口）

    Args:
        task_id: 任务ID
        estimated_cost: 预估成本
        **kwargs: 其他参数（task_type, is_essential, description等）

    Returns:
        预算检查结果
    """
    try:
        from mini_agent.agent.core.budget_engine import (
            BudgetCheckRequest,
            BudgetCheckResult,
            get_budget_engine,
        )

        engine = get_budget_engine()

        # 创建请求
        request = BudgetCheckRequest(task_id=task_id, estimated_cost=estimated_cost, **kwargs)

        # 执行检查
        result: BudgetCheckResult = engine.check_budget(request)

        # 记录日志
        if result.allowed:
            logger.info(f"任务 {task_id} 预算检查通过: {result.decision.value}")
        else:
            logger.warning(
                f"任务 {task_id} 预算检查未通过: {result.decision.value} - {result.reason}"
            )

        return result.to_dict()

    except ImportError as e:
        logger.error(f"无法导入预算引擎: {e}")
        return {
            "allowed": True,  # 故障时默认允许（优雅降级）
            "decision": "engine_unavailable",
            "reason": f"预算引擎不可用: {e}",
            "engine_available": False,
        }
    except Exception as e:
        logger.error(f"任务预算检查失败: {e}", exc_info=True)
        return {
            "allowed": True,  # 故障时默认允许
            "decision": "check_failed",
            "reason": f"预算检查失败: {e}",
            "engine_available": True,
            "error": str(e),
        }


def record_task_consumption(task_id: str, actual_cost: float, **kwargs) -> bool:
    """
    记录任务实际消费

    Args:
        task_id: 任务ID
        actual_cost: 实际成本
        **kwargs: 其他参数（task_type, description, metadata等）

    Returns:
        是否成功记录
    """
    try:
        from mini_agent.agent.core.budget_engine import get_budget_engine

        engine = get_budget_engine()
        engine.record_consumption(task_id=task_id, cost=actual_cost, **kwargs)

        logger.info(f"任务 {task_id} 消费记录成功: ¥{actual_cost:.2f}")
        return True

    except Exception as e:
        logger.error(f"记录任务消费失败: {e}", exc_info=True)
        return False


def get_budget_alerts() -> dict[str, Any]:
    """
    获取结构化预算告警

    Returns:
        包含指标和告警的结构化字典
    """
    try:
        from mini_agent.agent.core.budget_engine import get_budget_engine

        engine = get_budget_engine()
        alerts = engine.get_alerts()

        return alerts

    except ImportError as e:
        logger.error(f"无法导入预算引擎: {e}")
        return {
            "error": "budget_engine_not_available",
            "message": str(e),
            "indicators": {},
            "warnings": [],
            "alerts": [],
            "recommendations": [],
        }
    except Exception as e:
        logger.error(f"获取预算告警失败: {e}", exc_info=True)
        return {
            "error": "alerts_failed",
            "message": str(e),
            "indicators": {},
            "warnings": [],
            "alerts": [],
            "recommendations": [],
        }


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="预算心跳检查")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument("--quiet", action="store_true", help="安静模式，不输出警告")
    parser.add_argument("--alerts", action="store_true", help="包含结构化告警输出")
    parser.add_argument(
        "--check-task",
        nargs=3,
        metavar=("TASK_ID", "ESTIMATED_COST", "TASK_TYPE"),
        help="检查特定任务预算: TASK_ID ESTIMATED_COST TASK_TYPE",
    )
    parser.add_argument(
        "--record-consumption",
        nargs=3,
        metavar=("TASK_ID", "ACTUAL_COST", "TASK_TYPE"),
        help="记录任务消费: TASK_ID ACTUAL_COST TASK_TYPE",
    )

    args = parser.parse_args()

    if args.check_task:
        # 检查任务预算
        task_id, cost_str, task_type = args.check_task
        try:
            estimated_cost = float(cost_str)
        except ValueError:
            print(f"错误: 预估成本必须是数字: {cost_str}")
            sys.exit(1)

        result = check_budget_for_task(
            task_id=task_id, estimated_cost=estimated_cost, task_type=task_type
        )

        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("任务预算检查结果:")
            print(f"  任务ID: {task_id}")
            print(f"  预估成本: ¥{estimated_cost:.2f}")
            print(f"  任务类型: {task_type}")
            print(f"  允许执行: {result.get('allowed', False)}")
            print(f"  决定: {result.get('decision', 'unknown')}")
            print(f"  原因: {result.get('reason', '')}")
            if result.get("requires_approval", False):
                print("  ⚠️ 需要人工审批")

    elif args.record_consumption:
        # 记录消费
        task_id, cost_str, task_type = args.record_consumption
        try:
            actual_cost = float(cost_str)
        except ValueError:
            print(f"错误: 实际成本必须是数字: {cost_str}")
            sys.exit(1)

        success = record_task_consumption(
            task_id=task_id, actual_cost=actual_cost, task_type=task_type
        )

        print(f"消费记录{'成功' if success else '失败'}: 任务 {task_id}, 成本 ¥{actual_cost:.2f}")

    else:
        # 运行心跳检查
        run_heartbeat(
            output_format=args.format,
            alert_on_critical=not args.quiet,
            include_alerts=args.alerts,
        )


if __name__ == "__main__":
    main()
