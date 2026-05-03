#!/usr/bin/env python3
"""
Benchmark Runner - 基准测试运行器

执行任务集并收集统计指标
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 配置日志
import logging

from autoglm_bridge.agent_loop import AgentLoop, reset_agent_loop
from vision.screen_analyzer import get_screen_analyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 路径配置
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
SCREENSHOTS_DIR = LOGS_DIR / "screenshots"
TASKS_FILE = BASE_DIR / "tests" / "benchmark_tasks.json"

# 确保目录存在
LOGS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def load_tasks(tasks_file: str = None) -> dict:
    """加载任务集"""
    tasks_file = tasks_file or str(TASKS_FILE)
    with open(tasks_file, encoding="utf-8") as f:
        return json.load(f)


def check_success_signal(
    screenshot_path: str, expected_signal: str, ocr_provider: str = "easyocr"
) -> tuple[bool, list[str]]:
    """
    检查成功信号

    Args:
        screenshot_path: 截图路径
        expected_signal: 期望的成功信号
        ocr_provider: OCR provider

    Returns:
        (是否成功, OCR 识别的文本列表)
    """
    if not screenshot_path or not os.path.exists(screenshot_path):
        return False, []

    try:
        analyzer = get_screen_analyzer(ocr_provider=ocr_provider, screen_size=(1080, 2640))

        # 分析屏幕
        analysis = analyzer.analyze_screen(screenshot_path, expected_targets=[])

        # 提取所有 OCR 文本
        ocr_texts = [block["text"] for block in analysis.ocr_blocks]

        # 检查是否包含成功信号
        expected_lower = expected_signal.lower()

        for text in ocr_texts:
            if expected_lower in text.lower():
                return True, ocr_texts

        # 检查备选信号
        alt_signals = {
            "设置": ["设置", "关于手机", "设置页面"],
            "返回": ["返回", "<"],
            "主屏幕": ["主屏幕", "主页", "桌面"],
            "浏览器": ["浏览器", "Chrome", "浏览器界面"],
            "搜索": ["搜索", "搜索框"],
            "滑动": ["滑动", "滚动"],
            "Wi-Fi": ["Wi-Fi", "WLAN", "无线网络"],
            "蓝牙": ["蓝牙", "Bluetooth"],
        }

        alt_list = alt_signals.get(expected_signal, [])
        for alt in alt_list:
            for text in ocr_texts:
                if alt.lower() in text.lower():
                    return True, ocr_texts

        return False, ocr_texts

    except Exception as e:
        logger.error(f"OCR 检查失败: {e}")
        return False, []


def run_single_task(
    agent: AgentLoop,
    task_config: dict,
    round_index: int,
    device_id: str,
    ocr_provider: str = "easyocr",
) -> dict:
    """
    执行单个任务

    Args:
        agent: Agent 循环实例
        task_config: 任务配置
        round_index: 轮次索引
        device_id: 设备ID
        ocr_provider: OCR provider

    Returns:
        执行结果
    """
    task_name = task_config["name"]
    task_text = task_config["task"]
    max_steps = task_config["max_steps"]
    expected_signal = task_config["expected_success_signal"]

    logger.info(f"=== 执行任务: {task_name} (轮次 {round_index + 1}) ===")

    start_time = time.time()

    # 重置 agent 状态
    reset_agent_loop()

    # 创建新的 agent 实例
    agent = AgentLoop(device_id=device_id, use_mock=(ocr_provider == "mock"), max_steps=max_steps)

    # 执行任务
    result = agent.run_task(task_text, max_steps=max_steps, device_id=device_id)

    duration = time.time() - start_time

    # 获取最终截图
    final_screenshot = None
    if result["steps"]:
        final_step = result["steps"][-1]
        final_screenshot = final_step.get("screenshot_path")

    # 检查成功信号
    success_signal_found = False
    ocr_texts = []

    if final_screenshot:
        success_signal_found, ocr_texts = check_success_signal(
            final_screenshot, expected_signal, ocr_provider
        )

    # 收集动作来源
    action_sources_used = []
    primary_action_source = "unknown"
    grounding_hit = False
    model_fallback_used = False

    for step in result["steps"]:
        action_source = step.get("model_output", {}).get("action_source", "model_inference")
        action_sources_used.append(action_source)

        if action_source == "ocr_grounding":
            grounding_hit = True
            primary_action_source = "ocr_grounding"
        elif action_source == "model_inference" and primary_action_source == "unknown":
            primary_action_source = "model_inference"

        if step.get("fallback_used"):
            model_fallback_used = True

    # 确定最终结果
    if success_signal_found:
        final_status = "success"
    elif result["total_steps"] > 0:
        final_status = "partial"
    else:
        final_status = "failed"

    # 收集失败信息
    final_error = None
    if final_status == "failed":
        for step in reversed(result["steps"]):
            if step.get("error"):
                final_error = step["error"]
                break

    return {
        "task": task_name,
        "task_text": task_text,
        "round_index": round_index,
        "status": final_status,
        "steps_executed": result["total_steps"],
        "action_sources_used": action_sources_used,
        "primary_action_source": primary_action_source,
        "ocr_blocks_count": len(ocr_texts),
        "grounding_hit": grounding_hit,
        "model_fallback_used": model_fallback_used,
        "success_signal_found": success_signal_found,
        "expected_signal": expected_signal,
        "ocr_texts": ocr_texts[:10],  # 只保留前 10 个
        "final_error": final_error,
        "duration_seconds": round(duration, 2),
        "screenshots": [
            s.get("screenshot_path") for s in result["steps"] if s.get("screenshot_path")
        ],
    }


def calculate_summary(results: list[dict]) -> dict:
    """
    计算统计摘要

    Args:
        results: 执行结果列表

    Returns:
        统计摘要
    """
    total = len(results)
    if total == 0:
        return {}

    # 成功统计
    success_count = sum(1 for r in results if r["status"] == "success")
    partial_count = sum(1 for r in results if r["status"] == "partial")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    # 按任务分组
    task_results = {}
    for r in results:
        task = r["task"]
        if task not in task_results:
            task_results[task] = []
        task_results[task].append(r)

    # 按任务统计
    task_stats = {}
    for task, task_runs in task_results.items():
        task_total = len(task_runs)
        task_success = sum(1 for r in task_runs if r["status"] == "success")
        task_partial = sum(1 for r in task_runs if r["status"] == "partial")
        task_failed = sum(1 for r in task_runs if r["status"] == "failed")

        task_stats[task] = {
            "total": task_total,
            "success": task_success,
            "partial": task_partial,
            "failed": task_failed,
            "success_rate": round(task_success / task_total * 100, 1) if task_total > 0 else 0,
        }

    # OCR grounding 命中率
    grounding_hits = sum(1 for r in results if r["grounding_hit"])
    grounding_hit_rate = round(grounding_hits / total * 100, 1) if total > 0 else 0

    # 模型回退率
    model_fallbacks = sum(1 for r in results if r["model_fallback_used"])
    model_fallback_rate = round(model_fallbacks / total * 100, 1) if total > 0 else 0

    # 按动作来源分组
    action_source_stats = {
        "ocr_grounding": {"total": 0, "success": 0},
        "model_inference": {"total": 0, "success": 0},
        "fallback": {"total": 0, "success": 0},
    }

    for r in results:
        source = r["primary_action_source"]
        if source in action_source_stats:
            action_source_stats[source]["total"] += 1
            if r["status"] == "success":
                action_source_stats[source]["success"] += 1

    # 计算各来源成功率
    for _source, stats in action_source_stats.items():
        if stats["total"] > 0:
            stats["success_rate"] = round(stats["success"] / stats["total"] * 100, 1)
        else:
            stats["success_rate"] = 0

    # 平均步数和时长
    avg_steps = sum(r["steps_executed"] for r in results) / total if total > 0 else 0
    avg_duration = sum(r["duration_seconds"] for r in results) / total if total > 0 else 0

    # 失败类型分布
    failure_types = {}
    for r in results:
        if r["status"] == "failed":
            error = r.get("final_error", "unknown")
            failure_types[error] = failure_types.get(error, 0) + 1

    return {
        "total_runs": total,
        "success_count": success_count,
        "partial_count": partial_count,
        "failed_count": failed_count,
        "success_rate": round(success_count / total * 100, 1) if total > 0 else 0,
        "task_stats": task_stats,
        "grounding_hit_rate": grounding_hit_rate,
        "model_fallback_rate": model_fallback_rate,
        "action_source_stats": action_source_stats,
        "avg_steps": round(avg_steps, 1),
        "avg_duration_seconds": round(avg_duration, 1),
        "failure_types": failure_types,
    }


def collect_failure_samples(results: list[dict], max_samples: int = 5) -> list[dict]:
    """
    收集失败案例样本

    Args:
        results: 执行结果
        max_samples: 每类最大样本数

    Returns:
        失败样本列表
    """
    samples = []

    for r in results:
        if r["status"] in ["failed", "partial"]:
            sample = {
                "task": r["task"],
                "round": r["round_index"],
                "status": r["status"],
                "steps_executed": r["steps_executed"],
                "primary_action_source": r["primary_action_source"],
                "grounding_hit": r["grounding_hit"],
                "expected_signal": r["expected_signal"],
                "success_signal_found": r["success_signal_found"],
                "final_error": r["final_error"],
                "ocr_texts": r.get("ocr_texts", [])[:5],
                "screenshots": r.get("screenshots", []),
            }
            samples.append(sample)

    return samples[: max_samples * 3]  # 限制总数


def generate_markdown_report(summary: dict, results: list[dict], config: dict) -> str:
    """
    生成 Markdown 报告

    Args:
        summary: 统计摘要
        results: 执行结果
        config: 配置信息

    Returns:
        Markdown 报告
    """
    report = []
    report.append("# 基准测试报告")
    report.append("")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y/%m/%d %H:%M')}")
    report.append("")

    # 测试环境
    report.append("## 测试环境")
    report.append("")
    report.append(f"- **设备**: {config.get('device', 'Samsung Galaxy Z Flip3')}")
    report.append(f"- **OCR Provider**: {config.get('ocr_provider', 'easyocr')}")
    report.append(f"- **测试模式**: {config.get('mode', 'real')}")
    report.append(f"- **测试轮次**: {config.get('rounds', 1)}")
    report.append(f"- **任务数**: {config.get('task_count', 0)}")
    report.append("")

    # 总体统计
    report.append("## 总体统计")
    report.append("")
    report.append("| 指标 | 值 |")
    report.append("|------|-----|")
    report.append(f"| 总执行次数 | {summary.get('total_runs', 0)} |")
    report.append(f"| 成功 | {summary.get('success_count', 0)} |")
    report.append(f"| 部分成功 | {summary.get('partial_count', 0)} |")
    report.append(f"| 失败 | {summary.get('failed_count', 0)} |")
    report.append(f"| 成功率 | {summary.get('success_rate', 0)}% |")
    report.append(f"| OCR 命中率 | {summary.get('grounding_hit_rate', 0)}% |")
    report.append(f"| 模型回退率 | {summary.get('model_fallback_rate', 0)}% |")
    report.append(f"| 平均步数 | {summary.get('avg_steps', 0)} |")
    report.append(f"| 平均时长 | {summary.get('avg_duration_seconds', 0)}s |")
    report.append("")

    # 按任务统计
    report.append("## 按任务统计")
    report.append("")
    report.append("| 任务 | 总数 | 成功 | 失败 | 成功率 |")
    report.append("|------|------|------|------|--------|")

    task_stats = summary.get("task_stats", {})
    for task, stats in task_stats.items():
        report.append(
            f"| {task} | {stats['total']} | {stats['success']} | {stats['failed']} | {stats['success_rate']}% |"
        )

    report.append("")

    # 按动作来源统计
    report.append("## 按动作来源统计")
    report.append("")
    report.append("| 动作来源 | 总数 | 成功 | 成功率 |")
    report.append("|---------|------|------|--------|")

    action_stats = summary.get("action_source_stats", {})
    for source, stats in action_stats.items():
        report.append(
            f"| {source} | {stats['total']} | {stats['success']} | {stats['success_rate']}% |"
        )

    report.append("")

    # 失败类型
    failure_types = summary.get("failure_types", {})
    if failure_types:
        report.append("## 失败类型分布")
        report.append("")
        for error, count in failure_types.items():
            report.append(f"- {error}: {count}")
        report.append("")

    return "\n".join(report)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="基准测试运行器")
    parser.add_argument("--device", default="zflip3", help="设备名称")
    parser.add_argument("--rounds", type=int, default=2, help="每个任务执行轮次")
    parser.add_argument("--mode", choices=["real", "mock"], default="real", help="测试模式")
    parser.add_argument("--tasks", help="任务列表，逗号分隔")
    parser.add_argument("--output", default="logs/benchmark_results.json", help="输出文件")
    parser.add_argument("--tasks-file", default=str(TASKS_FILE), help="任务集文件")

    args = parser.parse_args()

    # 加载任务集
    tasks_data = load_tasks(args.tasks_file)
    all_tasks = tasks_data.get("tasks", [])

    # 筛选任务
    if args.tasks:
        task_names = [t.strip() for t in args.tasks.split(",")]
        selected_tasks = [t for t in all_tasks if t["name"] in task_names]
    else:
        # 默认选择前 3 个任务（小规模验证）
        selected_tasks = all_tasks[:3]

    logger.info(f"选择任务: {[t['name'] for t in selected_tasks]}")

    # 设备ID
    device_id = os.environ.get("ADB_SERIAL", "R3CR80FKA0V")

    # OCR Provider
    ocr_provider = "mock" if args.mode == "mock" else "easyocr"

    # 配置
    config = {
        "device": "Samsung Galaxy Z Flip3",
        "device_id": device_id,
        "ocr_provider": ocr_provider,
        "mode": args.mode,
        "rounds": args.rounds,
        "task_count": len(selected_tasks),
        "tasks": [t["name"] for t in selected_tasks],
    }

    logger.info(f"测试配置: {config}")

    # 执行测试
    results = []

    for task_config in selected_tasks:
        for round_idx in range(args.rounds):
            result = run_single_task(
                agent=None,  # 会在函数内创建
                task_config=task_config,
                round_index=round_idx,
                device_id=device_id,
                ocr_provider=ocr_provider,
            )
            results.append(result)

            # 短暂休息，避免过快
            time.sleep(1)

    # 计算摘要
    summary = calculate_summary(results)

    # 收集失败样本
    failure_samples = collect_failure_samples(results)

    # 输出结果
    output_path = BASE_DIR / args.output
    output_path.parent.mkdir(exist_ok=True)

    output_data = {
        "config": config,
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "summary": summary,
        "failure_samples": failure_samples,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"结果已保存到: {output_path}")

    # 生成摘要文件
    summary_path = BASE_DIR / "logs" / "benchmark_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    logger.info(f"摘要已保存到: {summary_path}")

    # 生成失败样本
    failure_path = BASE_DIR / "logs" / "benchmark_failure_samples.json"
    with open(failure_path, "w", encoding="utf-8") as f:
        json.dump(failure_samples, f, ensure_ascii=False, indent=2)

    logger.info(f"失败样本已保存到: {failure_path}")

    # 生成 Markdown 报告
    report = generate_markdown_report(summary, results, config)
    report_path = BASE_DIR / "docs" / "benchmark_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"报告已保存到: {report_path}")

    # 打印摘要
    print("\n" + "=" * 50)
    print("基准测试完成")
    print("=" * 50)
    print(f"总执行: {summary.get('total_runs', 0)}")
    print(f"成功: {summary.get('success_count', 0)}")
    print(f"失败: {summary.get('failed_count', 0)}")
    print(f"成功率: {summary.get('success_rate', 0)}%")
    print(f"OCR 命中率: {summary.get('grounding_hit_rate', 0)}%")
    print(f"模型回退率: {summary.get('model_fallback_rate', 0)}%")
    print("=" * 50)


if __name__ == "__main__":
    main()
