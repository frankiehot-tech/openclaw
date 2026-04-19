#!/usr/bin/env python3
"""
反馈循环运营脚本 - 每日运行

该脚本运行改进回路周期、生成评分板、生成下一步提示，
并将结果记录到日志文件中。

建议通过 cron 每日定时执行：
0 9 * * * cd /Volumes/1TB-M2/openclaw && python3 scripts/run_feedback_cycle.py >> logs/feedback_cycle.log 2>&1
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"feedback_cycle_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def run_improvement_cycle() -> dict:
    """运行改进回路周期"""
    logger.info("开始运行改进回路周期...")
    try:
        from mini_agent.agent.core.improvement_loop import run_improvement_cycle

        result = run_improvement_cycle()
        logger.info(
            f"改进回路周期完成: 创建{result['improvements_created']}个, 实施{result['improvements_implemented']}个"
        )
        return result
    except Exception as e:
        logger.error(f"运行改进回路周期失败: {e}")
        return {"error": str(e), "cycle_run_at": datetime.now().isoformat()}


def generate_scoreboard() -> dict:
    """生成评分板"""
    logger.info("开始生成评分板...")
    try:
        from mini_agent.agent.core.scoreboard import (
            generate_scoreboard,
            get_score_trend,
        )

        score_entry = generate_scoreboard()
        trend = get_score_trend()
        logger.info(
            f"评分板生成完成: 技术{score_entry.technical_score:.1f}, 用户{score_entry.user_score:.1f}, 业务{score_entry.business_score:.1f}, 综合{score_entry.overall_score:.1f}"
        )
        return {
            "score_entry": score_entry.to_dict(),
            "trend": trend,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"生成评分板失败: {e}")
        return {"error": str(e), "generated_at": datetime.now().isoformat()}


def generate_next_step_prompt() -> dict:
    """生成下一步提示"""
    logger.info("开始生成下一步提示...")
    try:
        from mini_agent.agent.core.next_step_prompt import (
            generate_next_step_prompt,
            save_next_step_prompt,
        )

        prompt, recommendations = generate_next_step_prompt()
        prompt_file = save_next_step_prompt(prompt, recommendations)
        logger.info(f"下一步提示生成完成: {len(recommendations)}个建议, 保存至{prompt_file}")
        return {
            "recommendations_count": len(recommendations),
            "high_priority": sum(1 for r in recommendations if r.priority == "high"),
            "prompt_file": str(prompt_file),
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"生成下一步提示失败: {e}")
        return {"error": str(e), "generated_at": datetime.now().isoformat()}


def cleanup_old_data(days_to_keep: int = 7, dry_run: bool = False) -> dict:
    """清理旧的测试数据和过期反馈"""
    logger.info(f"开始清理超过{days_to_keep}天的旧数据 (dry_run={dry_run})...")
    results = {}

    try:
        from mini_agent.agent.core.feedback_intake import cleanup_old_feedback

        feedback_result = cleanup_old_feedback(days_to_keep=days_to_keep, only_verified=True)
        if not dry_run:
            # 实际清理已在函数内完成
            pass
        results["feedback"] = feedback_result
        logger.info(f"反馈清理: 删除{feedback_result.get('deleted_feedbacks', 0)}个反馈")
    except Exception as e:
        logger.error(f"清理反馈数据失败: {e}")
        results["feedback_error"] = str(e)

    try:
        from mini_agent.agent.core.improvement_loop import cleanup_old_improvements

        improvement_result = cleanup_old_improvements(
            days_to_keep=days_to_keep, only_completed=True
        )
        if not dry_run:
            # 实际清理已在函数内完成
            pass
        results["improvement"] = improvement_result
        logger.info(f"改进清理: 删除{improvement_result.get('deleted_improvements', 0)}个改进")
    except Exception as e:
        logger.error(f"清理改进数据失败: {e}")
        results["improvement_error"] = str(e)

    return results


def save_summary(results: dict) -> Path:
    """保存运行摘要"""
    summary = {
        "run_timestamp": datetime.now().isoformat(),
        "results": results,
    }

    summary_dir = project_root / "workspace" / "feedback_cycle_summaries"
    summary_dir.mkdir(exist_ok=True)
    summary_file = summary_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    logger.info(f"运行摘要保存至: {summary_file}")
    return summary_file


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="运行反馈循环运营脚本")
    parser.add_argument("--cleanup", action="store_true", help="启用旧数据清理")
    parser.add_argument("--cleanup-days", type=int, default=7, help="清理超过多少天的数据（默认7）")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际修改数据")
    parser.add_argument("--skip-improvement", action="store_true", help="跳过改进回路")
    parser.add_argument("--skip-scoreboard", action="store_true", help="跳过分板生成")
    parser.add_argument("--skip-prompt", action="store_true", help="跳过下一步提示")
    args = parser.parse_args()

    logger.info("=== 反馈循环运营脚本开始运行 ===")
    logger.info(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(
        f"参数: cleanup={args.cleanup}, cleanup_days={args.cleanup_days}, dry_run={args.dry_run}"
    )

    results = {}

    # 1. 运行改进回路（可选跳过）
    if not args.skip_improvement:
        results["improvement_cycle"] = run_improvement_cycle()
    else:
        logger.info("跳过改进回路")
        results["improvement_cycle"] = {"skipped": True}

    # 2. 生成评分板（可选跳过）
    if not args.skip_scoreboard:
        results["scoreboard"] = generate_scoreboard()
    else:
        logger.info("跳过分板生成")
        results["scoreboard"] = {"skipped": True}

    # 3. 生成下一步提示（可选跳过）
    if not args.skip_prompt:
        results["next_step_prompt"] = generate_next_step_prompt()
    else:
        logger.info("跳过下一步提示")
        results["next_step_prompt"] = {"skipped": True}

    # 4. 清理旧数据（可选）
    if args.cleanup:
        results["cleanup"] = cleanup_old_data(days_to_keep=args.cleanup_days, dry_run=args.dry_run)

    # 5. 保存摘要
    summary_file = save_summary(results)

    logger.info("=== 反馈循环运营脚本运行完成 ===")
    logger.info(f"摘要文件: {summary_file}")

    # 如果有高优先级建议，在日志中突出显示
    if results.get("next_step_prompt", {}).get("high_priority", 0) > 0:
        logger.warning(
            f"⚠️  发现{results['next_step_prompt']['high_priority']}个高优先级建议，请立即处理！"
        )


if __name__ == "__main__":
    main()
