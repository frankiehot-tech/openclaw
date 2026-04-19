#!/usr/bin/env python3
"""
预算闭环验收脚本

验证预算耗尽暂停和恢复链路的关键流程：
1. 预算耗尽 → 暂停模式
2. 新任务被拒绝
3. 手动重置预算 → 恢复
4. 新任务被批准

此脚本作为最小验收测试，输出可被 artifact / review 消费的验收证据。
"""

import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 添加 mini-agent 目录到路径
mini_agent_dir = project_root / "mini-agent"
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_test_environment():
    """设置测试环境：创建临时数据库"""
    temp_dir = tempfile.mkdtemp(prefix="budget_acceptance_")
    db_path = Path(temp_dir) / "acceptance_test.db"

    # 导入预算引擎
    from mini_agent.agent.core.budget_engine import (
        BudgetConfig,
        BudgetEngine,
        BudgetResetPeriod,
    )

    # 使用小预算以便快速耗尽
    config = BudgetConfig(
        daily_budget=100.0,
        reset_period=BudgetResetPeriod.DAILY,
        normal_threshold=0.3,
        low_threshold=0.1,
        critical_threshold=0.02,
    )

    engine = BudgetEngine(db_path=db_path)
    engine.config = config  # 替换配置

    return engine, temp_dir, db_path


def run_acceptance_test() -> Dict[str, Any]:
    """
    运行验收测试

    Returns:
        包含测试结果和证据的字典
    """
    evidence = {
        "test_name": "budget_pause_resume_acceptance",
        "steps": [],
        "passed": False,
        "timestamp": None,
        "artifacts": {},
    }

    engine = None
    temp_dir = None

    try:
        import datetime

        evidence["timestamp"] = datetime.datetime.now().isoformat()

        # 步骤1: 设置测试环境
        logger.info("步骤1: 设置测试环境")
        engine, temp_dir, db_path = setup_test_environment()
        evidence["artifacts"]["db_path"] = str(db_path)
        evidence["steps"].append(
            {
                "step": 1,
                "action": "setup_test_environment",
                "result": "success",
                "details": {"db_path": str(db_path)},
            }
        )

        # 步骤2: 检查初始状态（应为正常模式）
        initial_state = engine.get_state()
        assert (
            initial_state.current_mode.value == "normal"
        ), f"初始模式应为normal，实际为{initial_state.current_mode.value}"
        logger.info(
            f"初始状态: 模式={initial_state.current_mode.value}, 预算={initial_state.period_budget:.2f}, 剩余={initial_state.remaining:.2f}"
        )
        evidence["steps"].append(
            {
                "step": 2,
                "action": "check_initial_state",
                "result": "success",
                "details": {
                    "mode": initial_state.current_mode.value,
                    "budget": initial_state.period_budget,
                    "remaining": initial_state.remaining,
                },
            }
        )

        # 步骤3: 模拟预算耗尽（消费99元，剩余1%）
        logger.info("步骤3: 模拟预算耗尽")
        engine.record_consumption("depletion_task", 99.0, "general", "耗尽预算")
        state_after_depletion = engine.get_state()
        logger.info(
            f"耗尽后状态: 模式={state_after_depletion.current_mode.value}, 剩余={state_after_depletion.remaining:.2f}, 使用率={state_after_depletion.utilization:.1%}"
        )

        # 验证已进入暂停模式（剩余1%，小于critical_threshold 2%）
        # 注意：阈值是2%，剩余1%应触发PAUSED模式
        assert (
            state_after_depletion.current_mode.value == "paused"
        ), f"预算耗尽后应进入paused模式，实际为{state_after_depletion.current_mode.value}"
        evidence["steps"].append(
            {
                "step": 3,
                "action": "deplete_budget",
                "result": "success",
                "details": {
                    "mode": state_after_depletion.current_mode.value,
                    "remaining": state_after_depletion.remaining,
                    "utilization": state_after_depletion.utilization,
                },
            }
        )

        # 步骤4: 验证新任务被拒绝
        logger.info("步骤4: 验证新任务被拒绝")
        from mini_agent.agent.core.budget_engine import BudgetCheckRequest

        request = BudgetCheckRequest(
            task_id="test_new_task",
            estimated_cost=0.5,
            task_type="general",
            is_essential=False,
            description="测试新任务",
        )
        result = engine.check_budget(request)
        logger.info(
            f"预算检查结果: 决定={result.decision.value}, 允许={result.allowed}, 原因={result.reason}"
        )

        assert (
            result.decision.value == "rejected_paused"
        ), f"暂停模式下新任务应被拒绝，实际决定为{result.decision.value}"
        assert result.allowed == False, "暂停模式下新任务不应被允许"
        evidence["steps"].append(
            {
                "step": 4,
                "action": "verify_task_rejection",
                "result": "success",
                "details": {
                    "decision": result.decision.value,
                    "allowed": result.allowed,
                    "reason": result.reason,
                },
            }
        )

        # 步骤5: 手动重置预算（恢复）
        logger.info("步骤5: 手动重置预算")
        reset_state = engine.reset_budget(new_budget=200.0, reset_consumed=True)
        logger.info(
            f"重置后状态: 模式={reset_state.current_mode.value}, 预算={reset_state.period_budget:.2f}, 剩余={reset_state.remaining:.2f}"
        )

        # 验证模式已恢复（应为正常模式，因为消费已重置）
        assert (
            reset_state.current_mode.value == "normal"
        ), f"重置预算后应恢复为normal模式，实际为{reset_state.current_mode.value}"
        evidence["steps"].append(
            {
                "step": 5,
                "action": "reset_budget",
                "result": "success",
                "details": {
                    "mode": reset_state.current_mode.value,
                    "budget": reset_state.period_budget,
                    "remaining": reset_state.remaining,
                },
            }
        )

        # 步骤6: 验证新任务被批准
        logger.info("步骤6: 验证新任务被批准")
        request2 = BudgetCheckRequest(
            task_id="test_recovered_task",
            estimated_cost=10.0,
            task_type="general",
            is_essential=False,
            description="恢复后测试任务",
        )
        result2 = engine.check_budget(request2)
        logger.info(
            f"恢复后预算检查结果: 决定={result2.decision.value}, 允许={result2.allowed}, 原因={result2.reason}"
        )

        assert (
            result2.decision.value == "approved"
        ), f"恢复后新任务应被批准，实际决定为{result2.decision.value}"
        assert result2.allowed == True, "恢复后新任务应被允许"
        evidence["steps"].append(
            {
                "step": 6,
                "action": "verify_task_approval",
                "result": "success",
                "details": {
                    "decision": result2.decision.value,
                    "allowed": result2.allowed,
                    "reason": result2.reason,
                },
            }
        )

        # 步骤7: 验证监控告警输出
        logger.info("步骤7: 验证监控告警输出")
        alerts = engine.get_alerts()
        assert "indicators" in alerts, "告警输出应包含indicators"
        assert "warnings" in alerts, "告警输出应包含warnings"
        assert "alerts" in alerts, "告警输出应包含alerts"

        logger.info(
            f"告警指标: 模式={alerts['indicators'].get('mode')}, 剩余预算={alerts['indicators'].get('budget_remaining')}"
        )
        evidence["steps"].append(
            {
                "step": 7,
                "action": "verify_alerts_output",
                "result": "success",
                "details": {
                    "has_indicators": True,
                    "has_warnings": True,
                    "has_alerts": True,
                    "mode": alerts["indicators"].get("mode"),
                },
            }
        )

        # 测试通过
        evidence["passed"] = True
        logger.info("✅ 验收测试通过！所有步骤验证成功。")

    except AssertionError as e:
        logger.error(f"❌ 验收测试失败: {e}")
        evidence["steps"].append(
            {
                "step": len(evidence["steps"]) + 1,
                "action": "assertion_failure",
                "result": "failure",
                "details": {"error": str(e)},
            }
        )
        evidence["passed"] = False
    except Exception as e:
        logger.error(f"❌ 验收测试异常: {e}", exc_info=True)
        evidence["steps"].append(
            {
                "step": len(evidence["steps"]) + 1,
                "action": "unexpected_error",
                "result": "error",
                "details": {"error": str(e)},
            }
        )
        evidence["passed"] = False
    finally:
        # 清理临时目录
        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"已清理临时目录: {temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")

    return evidence


def generate_acceptance_report(evidence: Dict[str, Any]) -> str:
    """生成验收报告"""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("预算闭环验收测试报告")
    report_lines.append("=" * 80)
    report_lines.append(f"测试名称: {evidence.get('test_name', 'unknown')}")
    report_lines.append(f"测试时间: {evidence.get('timestamp', 'unknown')}")
    report_lines.append(f"测试结果: {'✅ 通过' if evidence.get('passed') else '❌ 失败'}")
    report_lines.append("")

    report_lines.append("测试步骤详情:")
    for step in evidence.get("steps", []):
        result_symbol = "✅" if step.get("result") == "success" else "❌"
        report_lines.append(f"  步骤{step.get('step')}: {step.get('action')} {result_symbol}")
        if step.get("details"):
            for key, value in step.get("details", {}).items():
                report_lines.append(f"    {key}: {value}")

    report_lines.append("")
    report_lines.append("验收证据摘要:")
    report_lines.append(f"  总步骤数: {len(evidence.get('steps', []))}")
    passed_steps = sum(1 for s in evidence.get("steps", []) if s.get("result") == "success")
    report_lines.append(f"  通过步骤: {passed_steps}")
    report_lines.append(f"  失败步骤: {len(evidence.get('steps', [])) - passed_steps}")

    if evidence.get("artifacts"):
        report_lines.append("")
        report_lines.append("生成工件:")
        for key, value in evidence.get("artifacts", {}).items():
            report_lines.append(f"  {key}: {value}")

    report_lines.append("=" * 80)
    return "\n".join(report_lines)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="预算闭环验收测试")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--save-report", type=str, help="保存报告到文件路径")

    args = parser.parse_args()

    logger.info("开始运行预算闭环验收测试...")
    evidence = run_acceptance_test()

    # 生成报告
    if args.output == "json":
        report = json.dumps(evidence, ensure_ascii=False, indent=2)
    else:
        report = generate_acceptance_report(evidence)

    # 输出报告
    print(report)

    # 保存报告（如果指定）
    if args.save_report:
        with open(args.save_report, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"报告已保存到: {args.save_report}")

    # 退出码：测试通过为0，失败为1
    sys.exit(0 if evidence.get("passed") else 1)


if __name__ == "__main__":
    main()
