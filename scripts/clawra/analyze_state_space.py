#!/usr/bin/env python3
"""
状态空间分析工具
分析MAREF内存数据库中的状态转换记录，评估状态空间覆盖情况
"""

import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path


def get_state_transitions(db_path):
    """从数据库获取所有状态转换记录"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        query = """
        SELECT
            entry_id, entry_type, source_agent as agent_id, timestamp,
            json_extract(content_json, '$.from_state') as from_state,
            json_extract(content_json, '$.to_state') as to_state,
            json_extract(content_json, '$.transition_reason') as reason
        FROM memory_entries
        WHERE entry_type = 'state_transition'
        ORDER BY timestamp ASC
        """

        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        transitions = []
        for row in rows:
            transitions.append(
                {
                    "entry_id": row["entry_id"],
                    "agent_id": row["agent_id"],
                    "timestamp": row["timestamp"],
                    "from_state": row["from_state"],
                    "to_state": row["to_state"],
                    "reason": row["reason"] if row["reason"] else "未知",
                }
            )

        return transitions

    except sqlite3.Error as e:
        print(f"❌ 数据库查询失败: {e}")
        return []
    finally:
        if conn:
            conn.close()


def analyze_state_space(transitions):
    """分析状态空间覆盖情况"""
    if not transitions:
        return {
            "total_transitions": 0,
            "unique_states": set(),
            "state_frequency": {},
            "state_transitions": {},
            "coverage_analysis": {},
        }

    # 收集所有状态
    all_states = []
    for trans in transitions:
        if trans["from_state"]:
            all_states.append(trans["from_state"])
        if trans["to_state"]:
            all_states.append(trans["to_state"])

    # 统计状态频率
    state_counter = Counter(all_states)
    unique_states = set(all_states)

    # 统计状态转换对
    transition_pairs = []
    for trans in transitions:
        if trans["from_state"] and trans["to_state"]:
            pair = f"{trans['from_state']}→{trans['to_state']}"
            transition_pairs.append(pair)

    transition_counter = Counter(transition_pairs)

    # 计算状态空间覆盖率
    # 64卦总状态数: 2^6 = 64
    total_possible_states = 64
    coverage_percentage = len(unique_states) / total_possible_states * 100

    # 分析状态分布
    state_distribution = {
        "most_common_states": state_counter.most_common(10),
        "least_common_states": state_counter.most_common()[-5:] if len(state_counter) > 5 else [],
        "state_diversity": len(unique_states),
    }

    # 分析转换模式
    transition_analysis = {
        "most_common_transitions": transition_counter.most_common(10),
        "total_unique_transitions": len(transition_counter),
        "transition_diversity": (
            len(transition_counter) / len(transitions) * 100 if transitions else 0
        ),
    }

    return {
        "total_transitions": len(transitions),
        "unique_states": unique_states,
        "state_frequency": dict(state_counter),
        "state_transitions": dict(transition_counter),
        "coverage_analysis": {
            "total_possible_states": total_possible_states,
            "covered_states": len(unique_states),
            "coverage_percentage": coverage_percentage,
            "remaining_states": total_possible_states - len(unique_states),
        },
        "state_distribution": state_distribution,
        "transition_analysis": transition_analysis,
    }


def print_report(analysis, db_path):
    """打印状态空间分析报告"""
    print("\n" + "=" * 70)
    print("MAREF状态空间覆盖分析报告")
    print("=" * 70)

    print(f"\n📊 总体统计:")
    print(f"   数据库路径: {db_path}")
    print(f"   总转换次数: {analysis['total_transitions']}")
    print(f"   唯一状态数: {analysis['coverage_analysis']['covered_states']}")
    print(f"   64卦总状态: {analysis['coverage_analysis']['total_possible_states']}")
    print(f"   状态空间覆盖率: {analysis['coverage_analysis']['coverage_percentage']:.1f}%")
    print(f"   剩余未覆盖状态: {analysis['coverage_analysis']['remaining_states']}")

    if analysis["state_distribution"]["most_common_states"]:
        print(f"\n🏆 最常访问状态 (前10):")
        for state, count in analysis["state_distribution"]["most_common_states"]:
            percentage = (
                count / sum(analysis["state_frequency"].values()) * 100
                if sum(analysis["state_frequency"].values()) > 0
                else 0
            )
            print(f"   {state}: {count}次 ({percentage:.1f}%)")

    if analysis["transition_analysis"]["most_common_transitions"]:
        print(f"\n🔄 最常发生转换 (前10):")
        for transition_str, count in analysis["transition_analysis"]["most_common_transitions"]:
            from_state, to_state = transition_str.split("→")
            print(f"   {from_state} → {to_state}: {count}次")

    print(f"\n📈 状态多样性分析:")
    print(f"   状态多样性指数: {analysis['state_distribution']['state_diversity']}")
    print(f"   转换多样性: {analysis['transition_analysis']['transition_diversity']:.1f}%")

    # 状态覆盖建议
    print(f"\n🎯 状态空间覆盖建议:")
    coverage = analysis["coverage_analysis"]["coverage_percentage"]
    if coverage < 25:
        print(f"   ⚠️  状态空间覆盖率较低 ({coverage:.1f}%)，建议增加测试场景覆盖更多卦象")
    elif coverage < 50:
        print(f"   📊 状态空间覆盖率中等 ({coverage:.1f}%)，可以进一步扩展")
    elif coverage < 75:
        print(f"   ✅ 状态空间覆盖率良好 ({coverage:.1f}%)")
    else:
        print(f"   🎉 状态空间覆盖率优秀 ({coverage:.1f}%)")

    # 生成具体建议
    if analysis["coverage_analysis"]["remaining_states"] > 0:
        print(f"   建议优先覆盖以下类型状态:")
        print(f"   1. 与常用状态汉明距离为1的相邻状态")
        print(f"   2. 状态空间中分布均匀的代表性卦象")
        print(f"   3. 包含特定模式的状态（如交替01、全0、全1等）")


def main():
    """主函数"""
    # 数据库路径
    db_path = Path("/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db")

    if not db_path.exists():
        print(f"❌ 数据库不存在: {db_path}")
        print("请先运行MAREF系统生成状态转换记录")
        return 1

    print(f"🔍 开始状态空间分析")
    print(f"时间: 2026-04-14")
    print(f"数据库: {db_path}")
    print(f"数据库大小: {db_path.stat().st_size / 1024:.1f} KB")

    # 获取状态转换记录
    transitions = get_state_transitions(db_path)
    print(f"从数据库读取到 {len(transitions)} 个状态转换记录")

    if not transitions:
        print("⚠️  没有状态转换记录，无法进行分析")
        return 0

    # 分析状态空间
    analysis = analyze_state_space(transitions)

    # 打印报告
    print_report(analysis, db_path)

    # 保存详细报告
    output_file = Path.cwd() / "state_space_analysis_report.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            # 转换集合为列表以便JSON序列化
            analysis_json = analysis.copy()
            analysis_json["unique_states"] = list(analysis["unique_states"])
            json.dump(analysis_json, f, ensure_ascii=False, indent=2)

        print(f"\n📄 详细报告已保存到: {output_file}")

    except Exception as e:
        print(f"❌ 保存报告失败: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
