#!/usr/bin/env python3
"""检查MAREF内存数据库"""

import json
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(__file__))


def check_database():
    db_path = "/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"

    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return

    print(f"检查数据库: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print("\n=== 数据库表 ===")
        for table in tables:
            table_name = table[0]
            print(f"表: {table_name}")

            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()

            print(f"  列结构:")
            for col in columns:
                col_id, col_name, col_type, notnull, default_value, pk = col
                print(f"    {col_name} ({col_type}) {'PK' if pk else ''}")

            # 获取行数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"  行数: {count}")

            # 如果是memory_entries表，显示详细统计
            if table_name == "memory_entries":
                # 按类型统计
                cursor.execute(
                    "SELECT entry_type, COUNT(*) FROM memory_entries GROUP BY entry_type ORDER BY COUNT(*) DESC"
                )
                type_stats = cursor.fetchall()
                print(f"  条目类型统计:")
                for entry_type, type_count in type_stats:
                    print(f"    {entry_type}: {type_count}")

                # 显示最近状态转换记录
                cursor.execute("""
                    SELECT entry_id, entry_type, timestamp, source_agent, content_json
                    FROM memory_entries
                    WHERE entry_type = 'state_transition'
                    ORDER BY timestamp DESC
                    LIMIT 5
                """)
                state_transitions = cursor.fetchall()
                if state_transitions:
                    print(f"\n  最近5条状态转换记录:")
                    for row in state_transitions:
                        entry_id, entry_type, timestamp, source_agent, content_json = row
                        try:
                            content = json.loads(content_json)
                            from_state = content.get("from_state", "unknown")
                            to_state = content.get("to_state", "unknown")
                            reason = content.get("reason", "unknown")
                            hamming = content.get("hamming_distance", "N/A")
                            print(
                                f"    [{entry_id[:8]}...] {from_state}→{to_state} (汉明: {hamming})"
                            )
                            print(f"        触发者: {source_agent}, 时间: {timestamp}")
                            print(f"        原因: {reason}")
                        except:
                            print(
                                f"    [{entry_id[:8]}...] {entry_type} by {source_agent} at {timestamp}"
                            )

                # 显示最新一条状态转换作为当前状态
                cursor.execute("""
                    SELECT content_json, timestamp, source_agent
                    FROM memory_entries
                    WHERE entry_type = 'state_transition'
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                latest_state = cursor.fetchone()
                if latest_state:
                    content_json, timestamp, source_agent = latest_state
                    try:
                        content = json.loads(content_json)
                        to_state = content.get("to_state")
                        if to_state:
                            print(f"\n  ✅ 当前系统状态 (来自数据库): {to_state}")
                            print(f"     最后更新时间: {timestamp}")
                            print(f"     最后触发者: {source_agent}")
                    except:
                        pass

            print()

        conn.close()

    except Exception as e:
        print(f"检查数据库时出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_database()
