#!/usr/bin/env python3
"""
测试迁移监控器指标收集
"""

import os
import sys

sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")

from datetime import datetime

from agent.core.migration_monitor import MigrationMonitor


def main():
    db_path = "/Volumes/1TB-M2/openclaw/mini-agent/data/cost_tracking.db"

    monitor = MigrationMonitor(db_path=db_path, check_interval_minutes=15)

    # 收集当前指标
    metrics = monitor.collect_migration_metrics(
        experiment_id="coding_plan_deepseek_coder_ab", lookback_hours=24
    )

    if metrics:
        print("✅ 迁移指标收集成功")
        print(f"   时间戳: {metrics.timestamp}")
        print(f"   实验ID: {metrics.experiment_id}")
        print(f"   阶段: {metrics.phase_number}")
        print(f"   总请求数: {metrics.total_requests}")
        print(f"   DashScope请求: {metrics.dashscope_requests}")
        print(f"   DeepSeek请求: {metrics.deepseek_requests}")
        print(f"   DashScope成本: ${metrics.dashscope_cost:.6f}")
        print(f"   DeepSeek成本: ${metrics.deepseek_cost:.6f}")
        print(f"   成本节省: {metrics.cost_savings_percent:.1f}%")
        print(f"   DashScope质量: {metrics.dashscope_quality_avg:.3f}")
        print(f"   DeepSeek质量: {metrics.deepseek_quality_avg:.3f}")
        print(f"   质量一致性: {metrics.quality_consistency:.3f}")
        print(f"   DashScope错误率: {metrics.dashscope_error_rate:.3f}")
        print(f"   DeepSeek错误率: {metrics.deepseek_error_rate:.3f}")
        print(f"   错误率差异: {metrics.error_rate_diff:.3f}")
        print(f"   DashScope响应时间: {metrics.dashscope_response_time_avg:.3f}s")
        print(f"   DeepSeek响应时间: {metrics.deepseek_response_time_avg:.3f}s")
        print(f"   响应时间差异: {metrics.response_time_diff_percent:.1f}%")
    else:
        print("❌ 无法收集迁移指标")


if __name__ == "__main__":
    main()
