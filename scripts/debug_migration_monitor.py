#!/usr/bin/env python3
"""
调试迁移监控器的匹配逻辑
"""

import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_matching_logic():
    """测试匹配逻辑"""
    db_path = "/Volumes/1TB-M2/openclaw/mini-agent/data/cost_tracking.db"

    if not os.path.exists(db_path):
        logger.error(f"数据库不存在: {db_path}")
        return

    # 检查请求ID生成器是否可用
    try:
        from agent.core.request_id_generator import (
            RequestIDGenerator,
            get_request_id_generator,
        )

        REQUEST_ID_GENERATOR_AVAILABLE = True
        logger.info("✅ 请求ID生成器可用")
    except ImportError as e:
        logger.error(f"❌ 请求ID生成器导入失败: {e}")
        REQUEST_ID_GENERATOR_AVAILABLE = False
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取实验记录
    cursor.execute("""
        SELECT id, request_id, recorded_at, cost_record_id
        FROM experiment_records
        WHERE experiment_id = 'coding_plan_deepseek_coder_ab'
        LIMIT 5
    """)
    exp_records = cursor.fetchall()

    logger.info(f"获取到 {len(exp_records)} 条实验记录")

    # 获取成本记录（按时间排序）
    cursor.execute(
        "SELECT id, request_id, timestamp FROM cost_records ORDER BY timestamp DESC LIMIT 15"
    )
    cost_records = cursor.fetchall()
    logger.info(f"获取到 {len(cost_records)} 条成本记录")

    # 统计不同格式
    standard_format = 0
    non_standard_format = 0
    generator = get_request_id_generator()

    for cost in cost_records:
        rid = cost["request_id"]
        parsed = generator.parse(rid)
        if parsed.get("is_standard_format", False):
            standard_format += 1
        else:
            non_standard_format += 1

    logger.info(f"标准格式成本记录: {standard_format}, 非标准格式: {non_standard_format}")

    # 测试RequestIDGenerator
    generator = get_request_id_generator()

    # 测试解析
    for exp in exp_records:
        rid = exp["request_id"]
        parsed = generator.parse(rid)
        logger.info(f"实验记录ID解析: {rid}")
        logger.info(f"  标准格式: {parsed['is_standard_format']}")
        logger.info(f"  前缀: {parsed['prefix']}")
        logger.info(f"  时间戳: {parsed['timestamp_str']}")

    for cost in cost_records:
        rid = cost["request_id"]
        parsed = generator.parse(rid)
        logger.info(f"成本记录ID解析: {rid}")
        logger.info(f"  标准格式: {parsed['is_standard_format']}")
        logger.info(f"  前缀: {parsed['prefix']}")
        logger.info(f"  时间戳: {parsed['timestamp_str']}")

    # 测试时间窗口匹配
    logger.info("\n=== 测试时间窗口匹配 ===")
    for exp in exp_records:
        exp_rid = exp["request_id"]
        exp_time = exp["recorded_at"]

        for cost in cost_records:
            cost_rid = cost["request_id"]
            cost_time = cost["timestamp"]

            # 计算时间差
            if exp_time and cost_time:
                try:
                    exp_dt = datetime.fromisoformat(exp_time.replace("Z", "+00:00"))
                    cost_dt = datetime.fromisoformat(cost_time.replace("Z", "+00:00"))
                    time_diff = abs((exp_dt - cost_dt).total_seconds())

                    # 检查是否在2小时内
                    if time_diff <= 7200:  # 2小时
                        logger.info(f"时间窗口匹配: {exp_rid} ({exp_dt}) 与 {cost_rid} ({cost_dt})")
                        logger.info(f"  时间差: {time_diff}秒 ({time_diff/60:.1f}分钟)")

                        # 检查RequestIDGenerator的match_time_window方法
                        match = generator.match_time_window(exp_rid, cost_rid, 7200)
                        logger.info(f"  generator.match_time_window: {match}")
                except Exception as e:
                    logger.warning(f"时间解析错误: {e}")

    # 测试前缀匹配逻辑
    logger.info("\n=== 测试前缀匹配逻辑 ===")
    for exp in exp_records:
        exp_rid = exp["request_id"]
        parsed = generator.parse(exp_rid)
        if parsed.get("is_standard_format", False):
            parts = exp_rid.split("_")
            if len(parts) >= 3:
                prefix_timestamp = f"{parts[0]}_{parts[1]}"
                logger.info(f"实验记录 {exp_rid} -> 前缀部分: {prefix_timestamp}")

    for cost in cost_records:
        cost_rid = cost["request_id"]
        parsed = generator.parse(cost_rid)
        if parsed.get("is_standard_format", False):
            parts = cost_rid.split("_")
            if len(parts) >= 3:
                cost_prefix = f"{parts[0]}_{parts[1]}"
                logger.info(f"成本记录 {cost_rid} -> 前缀部分: {cost_prefix}")

    conn.close()


if __name__ == "__main__":
    test_matching_logic()
