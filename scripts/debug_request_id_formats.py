#!/usr/bin/env python3
"""
调试实验记录和成本记录的request_id格式
"""

import sqlite3
from datetime import datetime


def main():
    db_path = "/Volumes/1TB-M2/openclaw/mini-agent/data/cost_tracking.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=== 实验记录request_id格式 ===")
    cursor.execute("""
        SELECT request_id, COUNT(*) as count
        FROM experiment_records
        WHERE experiment_id = 'coding_plan_deepseek_coder_ab'
        GROUP BY request_id
        ORDER BY recorded_at DESC
        LIMIT 10
    """)

    exp_formats = {}
    for row in cursor.fetchall():
        request_id = row["request_id"]
        if request_id:
            # 分析格式
            parts = request_id.split("_")
            exp_formats[request_id] = {"parts": parts, "count": row["count"], "length": len(parts)}

    print(f"找到 {len(exp_formats)} 种不同的request_id格式")
    for rid, info in list(exp_formats.items())[:5]:
        print(f"  '{rid}'")
        print(f"    分割: {info['parts']} ({info['length']} 部分)")
        print(f"    出现次数: {info['count']}")

    print("\n=== 成本记录request_id格式 ===")
    cursor.execute("""
        SELECT request_id, COUNT(*) as count
        FROM cost_records
        GROUP BY request_id
        ORDER BY timestamp DESC
        LIMIT 10
    """)

    cost_formats = {}
    for row in cursor.fetchall():
        request_id = row["request_id"]
        if request_id:
            parts = request_id.split("_")
            cost_formats[request_id] = {"parts": parts, "count": row["count"], "length": len(parts)}

    print(f"找到 {len(cost_formats)} 种不同的request_id格式")
    for rid, info in list(cost_formats.items())[:5]:
        print(f"  '{rid}'")
        print(f"    分割: {info['parts']} ({info['length']} 部分)")
        print(f"    出现次数: {info['count']}")

    print("\n=== 格式对比分析 ===")

    # 尝试使用RequestIDGenerator解析
    try:
        from agent.core.request_id_generator import RequestIDGenerator

        generator = RequestIDGenerator()

        print("实验记录request_id解析:")
        for rid in list(exp_formats.keys())[:3]:
            parsed = generator.parse(rid)
            print(f"  '{rid}' -> 标准格式: {parsed['is_standard_format']}")
            if parsed["is_standard_format"]:
                print(f"    前缀: {parsed['prefix']}")
                print(f"    时间戳: {parsed['timestamp_str']}")
                print(f"    唯一ID: {parsed['unique_id']}")

        print("\n成本记录request_id解析:")
        for rid in list(cost_formats.keys())[:3]:
            parsed = generator.parse(rid)
            print(f"  '{rid}' -> 标准格式: {parsed['is_standard_format']}")
            if parsed["is_standard_format"]:
                print(f"    前缀: {parsed['prefix']}")
                print(f"    时间戳: {parsed['timestamp_str']}")
                print(f"    唯一ID: {parsed['unique_id']}")

    except ImportError as e:
        print(f"无法导入RequestIDGenerator: {e}")

    print("\n=== 时间窗口分析 ===")

    # 检查实验记录和成本记录的时间范围
    cursor.execute("""
        SELECT
            MIN(recorded_at) as exp_min,
            MAX(recorded_at) as exp_max,
            COUNT(*) as exp_count
        FROM experiment_records
        WHERE experiment_id = 'coding_plan_deepseek_coder_ab'
    """)
    exp_time = cursor.fetchone()
    print(f"实验记录时间范围: {exp_time['exp_min']} 到 {exp_time['exp_max']}")
    print(f"实验记录数量: {exp_time['exp_count']}")

    cursor.execute("""
        SELECT
            MIN(timestamp) as cost_min,
            MAX(timestamp) as cost_max,
            COUNT(*) as cost_count
        FROM cost_records
    """)
    cost_time = cursor.fetchone()
    print(f"成本记录时间范围: {cost_time['cost_min']} 到 {cost_time['cost_max']}")
    print(f"成本记录数量: {cost_time['cost_count']}")

    conn.close()


if __name__ == "__main__":
    main()
