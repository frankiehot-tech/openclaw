#!/usr/bin/env python3
"""
调试成本记录关联问题
"""

import sqlite3


def main():
    db_path = "/Volumes/1TB-M2/openclaw/mini-agent/data/cost_tracking.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=== 实验记录中的cost_record_id统计 ===")
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(cost_record_id) as with_cost_id,
            COUNT(*) - COUNT(cost_record_id) as without_cost_id
        FROM experiment_records
    """)
    row = cursor.fetchone()
    print(f"总实验记录: {row['total']}")
    print(f"有cost_record_id: {row['with_cost_id']}")
    print(f"无cost_record_id: {row['without_cost_id']}")

    print("\n=== 实验记录示例（查看cost_record_id） ===")
    cursor.execute("""
        SELECT id, experiment_id, group_name, cost_record_id
        FROM experiment_records
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(
            f"ID: {row['id']}, 实验: {row['experiment_id']}, 分组: {row['group_name']}, 成本ID: {row['cost_record_id']}"
        )

    print("\n=== 成本记录示例 ===")
    cursor.execute("SELECT id, provider_id, estimated_cost FROM cost_records LIMIT 5")
    for row in cursor.fetchall():
        print(f"成本ID: {row['id']}, provider: {row['provider_id']}, 成本: {row['estimated_cost']}")

    # 检查实验记录是否有对应的成本记录
    print("\n=== 实验记录与成本记录匹配情况 ===")
    cursor.execute("""
        SELECT
            e.id as exp_id,
            e.cost_record_id,
            c.id as cost_id,
            c.provider_id,
            c.estimated_cost
        FROM experiment_records e
        LEFT JOIN cost_records c ON e.cost_record_id = c.id
        WHERE e.experiment_id = 'coding_plan_deepseek_coder_ab'
        LIMIT 10
    """)
    matched = 0
    total = 0
    for row in cursor.fetchall():
        total += 1
        if row["cost_id"]:
            matched += 1
            print(
                f"匹配: 实验ID={row['exp_id']}, 成本ID={row['cost_id']}, provider={row['provider_id']}, 成本={row['estimated_cost']}"
            )
        else:
            print(f"不匹配: 实验ID={row['exp_id']}, 成本ID={row['cost_record_id'] or 'NULL'}")

    print(f"\n匹配率: {matched}/{total} ({matched/max(1,total)*100:.1f}%)")

    conn.close()


if __name__ == "__main__":
    main()
