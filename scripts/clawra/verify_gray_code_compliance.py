#!/usr/bin/env python3
"""
格雷编码合规性验证工具
从MAREF内存数据库读取所有状态转换记录，验证格雷编码合规性（汉明距离=1）
生成详细的合规性报告和趋势分析
"""

import json
import os
import sqlite3
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))


class GrayCodeComplianceVerifier:
    """格雷编码合规性验证器"""

    def __init__(self, db_path: str = None):
        """
        初始化验证器

        Args:
            db_path: 内存数据库路径，如果为None则使用默认路径
        """
        if db_path is None:
            # 默认数据库路径
            self.db_path = Path("/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db")
        else:
            self.db_path = Path(db_path)

        # 确保数据库存在
        if not self.db_path.exists():
            print(f"❌ 数据库不存在: {self.db_path}")
            print("请先运行MAREF系统生成状态转换记录")
            sys.exit(1)

        # 导入汉明距离计算函数
        try:
            from external.ROMA.hexagram_state_manager import HexagramStateManager

            self.state_manager_class = HexagramStateManager
        except ImportError:
            print("⚠️  无法导入HexagramStateManager，将使用备用汉明距离计算")
            self.state_manager_class = None

        print(f"✅ 格雷编码合规性验证器初始化完成")
        print(f"   数据库路径: {self.db_path}")
        print(f"   数据库大小: {self.db_path.stat().st_size / 1024:.1f} KB")

    def hamming_distance(self, state1: str, state2: str) -> int:
        """计算两个二进制状态的汉明距离"""
        if len(state1) != len(state2):
            raise ValueError(f"状态长度不一致: {len(state1)} != {len(state2)}")

        # 计算不同位的数量
        return sum(bit1 != bit2 for bit1, bit2 in zip(state1, state2))

    def get_state_transitions(self, limit: int = None) -> List[Dict[str, Any]]:
        """从数据库获取状态转换记录"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            query = """
            SELECT
                entry_id, entry_type, source_agent as agent_id, timestamp,
                json_extract(content_json, '$.from_state') as from_state,
                json_extract(content_json, '$.to_state') as to_state,
                json_extract(content_json, '$.transition_reason') as reason,
                content_json as content
            FROM memory_entries
            WHERE entry_type = 'state_transition'
            ORDER BY timestamp ASC
            """

            if limit:
                query += f" LIMIT {limit}"

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
                        "raw_content": json.loads(row["content"]) if row["content"] else {},
                    }
                )

            return transitions

        except sqlite3.Error as e:
            print(f"❌ 数据库查询失败: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def verify_transition_compliance(self, from_state: str, to_state: str) -> Dict[str, Any]:
        """验证单个状态转换的格雷编码合规性"""
        try:
            # 计算汉明距离
            distance = self.hamming_distance(from_state, to_state)

            # 验证状态格式
            if len(from_state) != 6 or len(to_state) != 6:
                return {
                    "from_state": from_state,
                    "to_state": to_state,
                    "distance": distance,
                    "compliant": False,
                    "error": f"状态长度错误: {len(from_state)}/{len(to_state)} (应该为6)",
                }

            # 验证二进制字符
            if not all(bit in "01" for bit in from_state + to_state):
                return {
                    "from_state": from_state,
                    "to_state": to_state,
                    "distance": distance,
                    "compliant": False,
                    "error": "状态包含非0/1字符",
                }

            # 检查合规性（汉明距离必须为1）
            compliant = distance == 1

            return {
                "from_state": from_state,
                "to_state": to_state,
                "distance": distance,
                "compliant": compliant,
                "error": None,
            }

        except Exception as e:
            return {
                "from_state": from_state,
                "to_state": to_state,
                "distance": -1,
                "compliant": False,
                "error": str(e),
            }

    def analyze_compliance_trend(
        self, transitions: List[Dict[str, Any]], window_size: int = 10
    ) -> List[Dict[str, Any]]:
        """分析合规性趋势（滑动窗口）"""
        if len(transitions) < 2:
            return []

        trends = []
        for i in range(0, len(transitions) - window_size + 1, window_size // 2):
            window = transitions[i : i + window_size]
            if len(window) < 2:
                continue

            compliant_count = sum(
                1 for t in window if t.get("verification", {}).get("compliant", False)
            )
            total_count = len(window)
            compliance_rate = compliant_count / total_count if total_count > 0 else 0

            trends.append(
                {
                    "window_start": i,
                    "window_end": i + len(window) - 1,
                    "start_time": window[0]["timestamp"],
                    "end_time": window[-1]["timestamp"],
                    "total_transitions": total_count,
                    "compliant_transitions": compliant_count,
                    "compliance_rate": compliance_rate,
                    "non_compliant_transitions": total_count - compliant_count,
                }
            )

        return trends

    def generate_detailed_report(self, transitions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成详细合规性报告"""
        if not transitions:
            return {
                "summary": {
                    "total_transitions": 0,
                    "compliant_transitions": 0,
                    "compliance_rate": 1.0,
                    "all_compliant": True,
                },
                "details": [],
            }

        # 验证每个转换
        verified_transitions = []
        for trans in transitions:
            verification = self.verify_transition_compliance(trans["from_state"], trans["to_state"])
            verified_transitions.append({**trans, "verification": verification})

        # 计算总体统计
        compliant_count = sum(1 for t in verified_transitions if t["verification"]["compliant"])
        total_count = len(verified_transitions)
        compliance_rate = compliant_count / total_count if total_count > 0 else 0

        # 找出非合规转换
        non_compliant = [
            {
                "entry_id": t["entry_id"],
                "timestamp": t["timestamp"],
                "agent_id": t["agent_id"],
                "from_state": t["from_state"],
                "to_state": t["to_state"],
                "distance": t["verification"]["distance"],
                "reason": t["reason"],
                "error": t["verification"]["error"],
            }
            for t in verified_transitions
            if not t["verification"]["compliant"]
        ]

        # 按智能体统计
        agent_stats = {}
        for trans in verified_transitions:
            agent_id = trans["agent_id"]
            if agent_id not in agent_stats:
                agent_stats[agent_id] = {"total": 0, "compliant": 0, "non_compliant": 0}

            agent_stats[agent_id]["total"] += 1
            if trans["verification"]["compliant"]:
                agent_stats[agent_id]["compliant"] += 1
            else:
                agent_stats[agent_id]["non_compliant"] += 1

        # 计算趋势
        trends = self.analyze_compliance_trend(verified_transitions)

        return {
            "summary": {
                "total_transitions": total_count,
                "compliant_transitions": compliant_count,
                "non_compliant_transitions": total_count - compliant_count,
                "compliance_rate": compliance_rate,
                "all_compliant": (total_count == compliant_count),
                "verification_timestamp": datetime.now().isoformat(),
            },
            "agent_statistics": agent_stats,
            "trend_analysis": trends,
            "non_compliant_transitions": non_compliant[-20:],  # 最近20个非合规转换
            "recent_compliant_transitions": [
                {
                    "timestamp": t["timestamp"],
                    "from_state": t["from_state"],
                    "to_state": t["to_state"],
                    "distance": t["verification"]["distance"],
                    "agent_id": t["agent_id"],
                }
                for t in verified_transitions[-10:]  # 最近10个转换
            ],
        }

    def print_report(self, report: Dict[str, Any], output_file: str = None):
        """打印和保存报告"""
        summary = report["summary"]

        print("\n" + "=" * 70)
        print("格雷编码合规性验证报告")
        print("=" * 70)

        print(f"\n📊 总体统计:")
        print(f"   总转换次数: {summary['total_transitions']}")
        print(f"   合规转换: {summary['compliant_transitions']}")
        print(f"   非合规转换: {summary['non_compliant_transitions']}")
        print(f"   合规率: {summary['compliance_rate']:.1%}")

        if summary["all_compliant"]:
            print(f"   ✅ 所有转换符合格雷编码要求")
        else:
            print(f"   ⚠️  存在{summary['non_compliant_transitions']}个非合规转换")

        # 按智能体统计
        if report.get("agent_statistics"):
            print(f"\n🤖 按智能体统计:")
            for agent_id, stats in report["agent_statistics"].items():
                rate = stats["compliant"] / stats["total"] if stats["total"] > 0 else 0
                status = "✅" if rate == 1.0 else "⚠️ " if rate >= 0.9 else "❌"
                print(f"   {status} {agent_id}: {stats['compliant']}/{stats['total']} ({rate:.1%})")

        # 趋势分析
        if report.get("trend_analysis"):
            print(f"\n📈 合规性趋势分析:")
            for trend in report["trend_analysis"][-3:]:  # 最近3个窗口
                print(
                    f"   窗口 {trend['window_start']}-{trend['window_end']}: "
                    f"{trend['compliance_rate']:.1%} "
                    f"({trend['compliant_transitions']}/{trend['total_transitions']})"
                )

        # 非合规转换详情
        non_compliant = report.get("non_compliant_transitions", [])
        if non_compliant:
            print(f"\n❌ 非合规转换详情 (最近{len(non_compliant)}个):")
            for i, trans in enumerate(non_compliant, 1):
                print(
                    f"   {i:2d}. {trans['timestamp'][:19]} "
                    f"{trans['agent_id']}: {trans['from_state']} → {trans['to_state']} "
                    f"(距离: {trans['distance']}, 原因: {trans['reason']})"
                )
                if trans.get("error"):
                    print(f"      错误: {trans['error']}")

        # 最近合规转换
        recent_compliant = report.get("recent_compliant_transitions", [])
        if recent_compliant:
            print(f"\n✅ 最近合规转换 ({len(recent_compliant)}个):")
            for trans in recent_compliant[-5:]:
                print(
                    f"   {trans['timestamp'][:19]} "
                    f"{trans['agent_id']}: {trans['from_state']} → {trans['to_state']} "
                    f"(距离: {trans['distance']})"
                )

        # 保存报告到文件
        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                print(f"\n📄 详细报告已保存到: {output_file}")

                # 同时保存文本摘要
                txt_file = output_file.replace(".json", ".txt")
                with open(txt_file, "w", encoding="utf-8") as f:
                    f.write("格雷编码合规性验证报告\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(f"生成时间: {datetime.now().isoformat()}\n")
                    f.write(f"数据库: {self.db_path}\n")
                    f.write(f"总转换次数: {summary['total_transitions']}\n")
                    f.write(f"合规转换: {summary['compliant_transitions']}\n")
                    f.write(f"非合规转换: {summary['non_compliant_transitions']}\n")
                    f.write(f"合规率: {summary['compliance_rate']:.1%}\n\n")

                    if non_compliant:
                        f.write("非合规转换:\n")
                        for trans in non_compliant:
                            f.write(
                                f"  {trans['timestamp']} {trans['agent_id']}: "
                                f"{trans['from_state']} → {trans['to_state']} "
                                f"(距离: {trans['distance']})\n"
                            )

                print(f"📝 文本摘要已保存到: {txt_file}")

            except Exception as e:
                print(f"❌ 保存报告失败: {e}")

    def run_verification(self, output_dir: str = None) -> Dict[str, Any]:
        """运行完整的格雷编码合规性验证"""
        print("\n🔍 开始格雷编码合规性验证")
        print(f"时间: {datetime.now().isoformat()}")

        # 获取状态转换记录
        transitions = self.get_state_transitions()
        print(f"从数据库读取到 {len(transitions)} 个状态转换记录")

        if not transitions:
            print("⚠️  没有状态转换记录，无法进行合规性验证")
            print("请确保MAREF系统已经运行并记录了状态转换")
            return {}

        # 生成报告
        report = self.generate_detailed_report(transitions)

        # 确定输出目录
        if output_dir is None:
            output_dir = Path.cwd() / "gray_code_reports"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(exist_ok=True)

        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"gray_code_compliance_report_{timestamp}.json"

        # 打印报告
        self.print_report(report, str(output_file))

        # 返回验证结果
        return report


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="格雷编码合规性验证工具")
    parser.add_argument("--db-path", help="内存数据库路径")
    parser.add_argument("--output-dir", help="报告输出目录")
    parser.add_argument("--limit", type=int, help="限制分析的转换数量")

    args = parser.parse_args()

    # 创建验证器
    verifier = GrayCodeComplianceVerifier(args.db_path)

    # 运行验证
    try:
        report = verifier.run_verification(args.output_dir)

        if report:
            summary = report.get("summary", {})
            if summary.get("all_compliant", False):
                print("\n🎉 所有状态转换符合格雷编码要求！")
                return 0
            else:
                print(f"\n⚠️  存在非合规转换，合规率: {summary.get('compliance_rate', 0):.1%}")
                return 1
        else:
            return 0

    except Exception as e:
        print(f"❌ 验证过程中出现异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
