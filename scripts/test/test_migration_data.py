#!/usr/bin/env python3
"""
测试迁移数据查询
"""

import sqlite3


def main():
    db_path = "/Volumes/1TB-M2/openclaw/mini-agent/data/cost_tracking.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 查看实验记录
    print("=== 实验记录表数据 ===")
    cursor.execute(
        "SELECT experiment_id, group_name, COUNT(*) as count FROM experiment_records GROUP BY experiment_id, group_name"
    )
    for row in cursor.fetchall():
        print(f"实验: {row['experiment_id']}, 分组: {row['group_name']}, 数量: {row['count']}")

    # 查看具体的实验数据
    print("\n=== coding_plan_deepseek_coder_ab 实验数据 ===")
    cursor.execute("""
        SELECT
            group_name,
            COUNT(*) as request_count,
            AVG(quality_score) as avg_quality,
            AVG(execution_time) as avg_execution_time
        FROM experiment_records
        WHERE experiment_id = 'coding_plan_deepseek_coder_ab'
        GROUP BY group_name
    """)
    for row in cursor.fetchall():
        print(f"分组: {row['group_name']}")
        print(f"  请求数: {row['request_count']}")
        print(f"  平均质量分: {row['avg_quality']}")
        print(f"  平均执行时间: {row['avg_execution_time']}")

    # 查看成本记录关联
    print("\n=== 成本记录关联 ===")
    cursor.execute("""
        SELECT
            e.group_name,
            COUNT(e.id) as exp_count,
            COUNT(c.id) as cost_count,
            SUM(c.estimated_cost) as total_cost
        FROM experiment_records e
        LEFT JOIN cost_records c ON e.cost_record_id = c.id
        WHERE e.experiment_id = 'coding_plan_deepseek_coder_ab'
        GROUP BY e.group_name
    """)
    for row in cursor.fetchall():
        print(f"分组: {row['group_name']}")
        print(f"  实验记录数: {row['exp_count']}")
        print(f"  成本记录数: {row['cost_count']}")
        print(f"  总成本: {row['total_cost']}")

    # 查看具体的成本记录
    print("\n=== 成本记录详情 ===")
    cursor.execute("SELECT * FROM cost_records LIMIT 3")
    rows = cursor.fetchall()
    if rows:
        print(f"成本记录列名: {rows[0].keys()}")
        for i, row in enumerate(rows):
            print(f"\n记录 {i + 1}:")
            for key in row:
                print(f"  {key}: {row[key]}")
    else:
        print("无成本记录")

    conn.close()


if __name__ == "__main__":
    main()
