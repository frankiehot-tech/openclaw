#!/usr/bin/env python3
"""
测试迁移监控器修复后的匹配逻辑
"""

import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")

# 设置日志
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_find_matching_cost_records():
    """测试_find_matching_cost_records方法"""
    db_path = "/Volumes/1TB-M2/openclaw/mini-agent/data/cost_tracking.db"

    if not os.path.exists(db_path):
        logger.error(f"数据库不存在: {db_path}")
        return

    # 导入迁移监控器
    try:
        from agent.core.migration_monitor import MigrationMonitor
        from agent.core.request_id_generator import get_request_id_generator

        logger.info("✅ 迁移监控器和请求ID生成器可用")
    except ImportError as e:
        logger.error(f"❌ 导入失败: {e}")
        return

    # 创建监控器实例
    monitor = MigrationMonitor(db_path=db_path, check_interval_minutes=15)

    # 连接到数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取实验记录
    cursor.execute("""
        SELECT id, request_id, recorded_at, cost_record_id, group_name
        FROM experiment_records
        WHERE experiment_id = 'coding_plan_deepseek_coder_ab'
        ORDER BY recorded_at DESC
        LIMIT 10
    """)
    exp_records = cursor.fetchall()

    logger.info(f"获取到 {len(exp_records)} 条实验记录")

    # 获取成本记录
    cursor.execute("""
        SELECT id, request_id, timestamp, provider_id, estimated_cost
        FROM cost_records
        WHERE request_id NOT LIKE 'test_%'
          AND request_id NOT LIKE 'integration_test_%'
        ORDER BY timestamp DESC
        LIMIT 15
    """)
    cost_records = cursor.fetchall()
    logger.info(f"获取到 {len(cost_records)} 条成本记录")

    # 打印示例ID
    if exp_records and cost_records:
        logger.info(f"示例实验记录ID: {exp_records[0]['request_id']}")
        logger.info(f"示例成本记录ID: {cost_records[0]['request_id']}")

    # 测试RequestIDGenerator
    generator = get_request_id_generator()

    # 解析示例ID
    for i, exp in enumerate(exp_records[:2]):
        rid = exp["request_id"]
        parsed = generator.parse(rid)
        logger.info(f"实验记录{i+1}: {rid}")
        logger.info(f"  标准格式: {parsed['is_standard_format']}")
        logger.info(f"  时间戳字符串: {parsed.get('timestamp_str', 'N/A')}")
        logger.info(f"  时间戳对象: {parsed.get('timestamp', 'N/A')}")

    for i, cost in enumerate(cost_records[:2]):
        rid = cost["request_id"]
        parsed = generator.parse(rid)
        logger.info(f"成本记录{i+1}: {rid}")
        logger.info(f"  标准格式: {parsed['is_standard_format']}")
        logger.info(f"  时间戳字符串: {parsed.get('timestamp_str', 'N/A')}")
        logger.info(f"  时间戳对象: {parsed.get('timestamp', 'N/A')}")

    # 测试时间窗口匹配
    logger.info("\n=== 测试generator.match_time_window ===")
    if exp_records and cost_records:
        exp_rid = exp_records[0]["request_id"]
        cost_rid = cost_records[0]["request_id"]

        for window in [300, 1800, 3600, 7200]:  # 5分钟, 30分钟, 1小时, 2小时
            match = generator.match_time_window(exp_rid, cost_rid, window)
            logger.info(f"窗口{window}秒: {'匹配' if match else '不匹配'}")

    # 调用_find_matching_cost_records方法
    logger.info("\n=== 测试_find_matching_cost_records方法 ===")
    try:
        # 注意：需要传递lookback_hours参数
        cost_matches = monitor._find_matching_cost_records(cursor, exp_records, lookback_hours=24)

        logger.info(f"匹配结果: {len(cost_matches)}/{len(exp_records)} 个实验记录匹配成功")

        if cost_matches:
            # 统计匹配类型
            match_types = {}
            for exp_id, match_info in cost_matches.items():
                match_type = match_info.get("match_type", "unknown")
                match_types[match_type] = match_types.get(match_type, 0) + 1

            for match_type, count in match_types.items():
                logger.info(f"  {match_type}: {count} 个匹配")

            # 显示前几个匹配
            for i, (exp_id, match_info) in enumerate(list(cost_matches.items())[:3]):
                logger.info(f"匹配{i+1}: {exp_id} -> {match_info}")
        else:
            logger.warning("没有找到任何匹配")

    except Exception as e:
        logger.error(f"_find_matching_cost_records方法失败: {e}")
        import traceback

        traceback.print_exc()

    conn.close()
    logger.info("测试完成")


if __name__ == "__main__":
    test_find_matching_cost_records()
