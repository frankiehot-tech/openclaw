#!/usr/bin/env python3
"""
调试匹配逻辑，重点关注标准格式记录
"""

import logging
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_standard_format_matching():
    """测试标准格式记录匹配"""
    db_path = "/Volumes/1TB-M2/openclaw/mini-agent/data/cost_tracking.db"

    if not os.path.exists(db_path):
        logger.error(f"数据库不存在: {db_path}")
        return

    from agent.core.request_id_generator import get_request_id_generator

    generator = get_request_id_generator()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取标准格式的实验记录
    cursor.execute("""
        SELECT id, request_id, recorded_at, cost_record_id
        FROM experiment_records
        WHERE experiment_id = 'coding_plan_deepseek_coder_ab'
        ORDER BY recorded_at DESC
        LIMIT 10
    """)
    exp_records = cursor.fetchall()

    # 获取标准格式的成本记录
    cursor.execute("""
        SELECT id, request_id, timestamp, provider_id, estimated_cost
        FROM cost_records
        WHERE request_id NOT LIKE 'test_%'
          AND request_id NOT LIKE 'integration_test_%'
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    cost_records = cursor.fetchall()

    logger.info(f"获取到 {len(exp_records)} 条实验记录，{len(cost_records)} 条成本记录")

    # 测试匹配策略
    logger.info("\n=== 测试直接request_id匹配 ===")
    for exp in exp_records:
        exp_rid = exp["request_id"]
        for cost in cost_records:
            cost_rid = cost["request_id"]
            if exp_rid == cost_rid:
                logger.info(f"直接匹配: {exp_rid} == {cost_rid}")

    logger.info("\n=== 测试前缀匹配 ===")
    for exp in exp_records:
        exp_rid = exp["request_id"]
        exp_parsed = generator.parse(exp_rid)
        if exp_parsed.get("is_standard_format", False):
            exp_parts = exp_rid.split("_")
            if len(exp_parts) >= 3:
                exp_prefix = f"{exp_parts[0]}_{exp_parts[1]}"

                for cost in cost_records:
                    cost_rid = cost["request_id"]
                    cost_parsed = generator.parse(cost_rid)
                    if cost_parsed.get("is_standard_format", False):
                        cost_parts = cost_rid.split("_")
                        if len(cost_parts) >= 3:
                            cost_prefix = f"{cost_parts[0]}_{cost_parts[1]}"
                            if exp_prefix == cost_prefix:
                                logger.info(
                                    f"前缀匹配: {exp_rid} ({exp_prefix}) == {cost_rid} ({cost_prefix})"
                                )

    logger.info("\n=== 测试时间窗口匹配（使用generator.match_time_window）===")
    for exp in exp_records[:3]:  # 只测试前3条
        exp_rid = exp["request_id"]
        exp_time = exp["recorded_at"]

        for cost in cost_records[:3]:
            cost_rid = cost["request_id"]
            cost_time = cost["timestamp"]

            # 使用generator.match_time_window
            match = generator.match_time_window(exp_rid, cost_rid, 7200)  # 2小时窗口
            logger.info(f"时间窗口匹配: {exp_rid} 与 {cost_rid} = {match}")

            if match:
                # 计算实际时间差
                try:
                    exp_dt = datetime.fromisoformat(exp_time.replace("Z", "+00:00"))
                    cost_dt = datetime.fromisoformat(cost_time.replace("Z", "+00:00"))
                    time_diff = abs((exp_dt - cost_dt).total_seconds())
                    logger.info(f"  时间差: {time_diff}秒 ({time_diff / 60:.1f}分钟)")
                except Exception as e:
                    logger.warning(f"时间解析错误: {e}")

    logger.info("\n=== 模拟迁移监控器匹配逻辑 ===")
    # 模拟_find_matching_cost_records中的逻辑
    exp_request_ids = [exp["request_id"] for exp in exp_records if exp["request_id"]]

    # 策略1: 直接匹配
    placeholders = ",".join(["?"] * len(exp_request_ids))
    query1 = f"""
        SELECT id, request_id, provider_id, estimated_cost, timestamp
        FROM cost_records
        WHERE request_id IN ({placeholders})
    """
    cursor.execute(query1, exp_request_ids)
    direct_matches = cursor.fetchall()
    logger.info(f"直接匹配结果: {len(direct_matches)} 条")

    # 策略2: 前缀匹配
    prefix_matches = {}
    for request_id in exp_request_ids:
        parsed = generator.parse(request_id)
        if parsed.get("is_standard_format", False):
            parts = request_id.split("_")
            if len(parts) >= 3:
                prefix_timestamp = f"{parts[0]}_{parts[1]}"
                prefix_matches[prefix_timestamp] = request_id

    logger.info(f"可进行前缀匹配的实验记录: {len(prefix_matches)} 条")

    if prefix_matches:
        cursor.execute(
            "SELECT id, request_id, provider_id, estimated_cost, timestamp FROM cost_records"
        )
        all_costs = cursor.fetchall()

        prefix_match_count = 0
        for cost_record in all_costs:
            cost_request_id = cost_record["request_id"]
            parsed = generator.parse(cost_request_id)
            if parsed.get("is_standard_format", False):
                cost_parts = cost_request_id.split("_")
                if len(cost_parts) >= 3:
                    cost_prefix = f"{cost_parts[0]}_{cost_parts[1]}"
                    if cost_prefix in prefix_matches:
                        prefix_match_count += 1

        logger.info(f"前缀匹配结果: {prefix_match_count} 条")

    conn.close()


if __name__ == "__main__":
    test_standard_format_matching()
