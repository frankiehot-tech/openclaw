#!/usr/bin/env python3
"""
数据关联验证和修复工具

修复实验记录与成本记录之间的数据关联问题，确保所有实验记录都有有效的cost_record_id。

主要功能：
1. 诊断当前数据关联状态
2. 建立实验记录与成本记录的临时关联
3. 验证修复后的数据一致性
4. 生成详细的修复报告

使用方式：
python3 fix_data_association.py [--dry-run] [--fix] [--experiment EXPERIMENT_ID]

参数：
  --dry-run    只分析不修改（默认）
  --fix        执行修复操作
  --experiment  指定实验ID（默认：自动检测迁移相关实验）
"""

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 数据库路径
DB_PATH = "/Volumes/1TB-M2/openclaw/mini-agent/data/cost_tracking.db"


@dataclass
class AssociationReport:
    """关联修复报告"""

    # 基本信息
    timestamp: datetime
    experiment_id: str
    dry_run: bool

    # 统计信息
    total_experiment_records: int = 0
    total_cost_records: int = 0

    # 关联前状态
    pre_existing_associations: int = 0
    missing_associations: int = 0

    # 修复结果
    matched_by_exact_request_id: int = 0
    matched_by_time_window: int = 0
    matched_by_prefix: int = 0
    failed_matches: int = 0

    # 验证结果
    validation_passed: int = 0
    validation_failed: int = 0

    # 详细信息
    successful_matches: List[Dict] = None
    failed_matches_details: List[Dict] = None
    validation_errors: List[Dict] = None

    def __post_init__(self):
        if self.successful_matches is None:
            self.successful_matches = []
        if self.failed_matches_details is None:
            self.failed_matches_details = []
        if self.validation_errors is None:
            self.validation_errors = []

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result

    def print_summary(self):
        """打印摘要报告"""
        print("\n" + "=" * 80)
        print("数据关联修复报告")
        print("=" * 80)
        print(f"时间: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"实验ID: {self.experiment_id}")
        print(f"模式: {'干运行（只分析不修改）' if self.dry_run else '修复模式'}")

        print("\n📊 数据统计:")
        print(f"  实验记录总数: {self.total_experiment_records}")
        print(f"  成本记录总数: {self.total_cost_records}")

        print("\n🔗 关联前状态:")
        print(f"  已有关联: {self.pre_existing_associations}")
        print(f"  缺失关联: {self.missing_associations}")
        print(
            f"  关联率: {self.pre_existing_associations/max(1, self.total_experiment_records)*100:.1f}%"
        )

        if not self.dry_run:
            print("\n🔄 修复结果:")
            print(f"  精确request_id匹配: {self.matched_by_exact_request_id}")
            print(f"  时间窗口匹配: {self.matched_by_time_window}")
            print(f"  前缀匹配: {self.matched_by_prefix}")
            print(f"  匹配失败: {self.failed_matches}")

            print("\n✅ 验证结果:")
            print(f"  验证通过: {self.validation_passed}")
            print(f"  验证失败: {self.validation_failed}")
            if self.validation_failed > 0:
                print(f"  注意: {self.validation_failed} 个关联需要手动检查")

        # 计算修复后的关联率
        if self.dry_run:
            print("\n📈 预期修复效果:")
            expected_total = (
                self.pre_existing_associations
                + self.matched_by_exact_request_id
                + self.matched_by_time_window
                + self.matched_by_prefix
            )
            print(f"  预期总关联数: {expected_total}")
            print(f"  预期关联率: {expected_total/max(1, self.total_experiment_records)*100:.1f}%")
        else:
            total_associated = (
                self.pre_existing_associations
                + self.matched_by_exact_request_id
                + self.matched_by_time_window
                + self.matched_by_prefix
            )
            print(
                f"\n📈 修复后关联率: {total_associated/max(1, self.total_experiment_records)*100:.1f}%"
            )

        print("\n" + "=" * 80)


class DataAssociationFixer:
    """数据关联修复器"""

    def __init__(self, db_path: str, dry_run: bool = True):
        self.db_path = db_path
        self.dry_run = dry_run
        self.conn = None
        self.cursor = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            print(f"✅ 数据库连接成功: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def detect_migration_experiment(self) -> Optional[str]:
        """自动检测迁移相关实验"""
        try:
            # 查找包含'migration'或'deepseek'的实验ID
            self.cursor.execute("""
                SELECT DISTINCT experiment_id
                FROM experiment_records
                WHERE experiment_id LIKE '%migration%'
                   OR experiment_id LIKE '%deepseek%'
                LIMIT 1
            """)
            row = self.cursor.fetchone()
            if row:
                return row["experiment_id"]

            # 如果没有迁移实验，查找最新的实验
            self.cursor.execute("""
                SELECT experiment_id, MAX(recorded_at) as latest_time
                FROM experiment_records
                GROUP BY experiment_id
                ORDER BY latest_time DESC
                LIMIT 1
            """)
            row = self.cursor.fetchone()
            return row["experiment_id"] if row else None

        except Exception as e:
            print(f"❌ 检测实验失败: {e}")
            return None

    def analyze_current_state(self, experiment_id: str) -> Dict:
        """分析当前数据关联状态"""
        print(f"\n🔍 分析实验 '{experiment_id}' 的数据关联状态...")

        # 统计实验记录
        self.cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(cost_record_id) as with_cost_id,
                COUNT(*) - COUNT(cost_record_id) as without_cost_id
            FROM experiment_records
            WHERE experiment_id = ?
        """,
            (experiment_id,),
        )
        exp_stats = self.cursor.fetchone()

        # 统计成本记录
        self.cursor.execute("SELECT COUNT(*) as total FROM cost_records")
        cost_stats = self.cursor.fetchone()

        # 获取实验记录示例
        self.cursor.execute(
            """
            SELECT id, request_id, group_name, cost_record_id, recorded_at
            FROM experiment_records
            WHERE experiment_id = ?
            LIMIT 5
        """,
            (experiment_id,),
        )
        exp_samples = [dict(row) for row in self.cursor.fetchall()]

        # 获取成本记录示例
        self.cursor.execute("""
            SELECT id, request_id, provider_id, model_id, estimated_cost, timestamp
            FROM cost_records
            LIMIT 5
        """)
        cost_samples = [dict(row) for row in self.cursor.fetchall()]

        return {
            "experiment_stats": {
                "total": exp_stats["total"],
                "with_cost_id": exp_stats["with_cost_id"],
                "without_cost_id": exp_stats["without_cost_id"],
            },
            "cost_stats": {"total": cost_stats["total"]},
            "experiment_samples": exp_samples,
            "cost_samples": cost_samples,
        }

    def match_experiment_to_cost_records(self, experiment_id: str) -> List[Dict]:
        """匹配实验记录到成本记录"""
        print(f"\n🔄 匹配实验 '{experiment_id}' 的记录...")

        # 获取所有需要关联的实验记录
        self.cursor.execute(
            """
            SELECT id, request_id, group_name, recorded_at, cost_record_id
            FROM experiment_records
            WHERE experiment_id = ? AND (cost_record_id IS NULL OR cost_record_id = '')
        """,
            (experiment_id,),
        )
        exp_records = [dict(row) for row in self.cursor.fetchall()]

        matches = []

        for exp_record in exp_records:
            exp_id = exp_record["id"]
            exp_request_id = exp_record["request_id"]
            exp_recorded_at = (
                datetime.fromisoformat(exp_record["recorded_at"])
                if exp_record["recorded_at"]
                else None
            )

            match_result = self._find_best_cost_match(
                exp_request_id, exp_recorded_at, exp_record["group_name"]
            )

            if match_result:
                matches.append(
                    {
                        "experiment_id": exp_id,
                        "experiment_request_id": exp_request_id,
                        "cost_record_id": match_result["cost_id"],
                        "cost_request_id": match_result["cost_request_id"],
                        "match_type": match_result["match_type"],
                        "match_confidence": match_result["confidence"],
                        "provider": match_result["provider"],
                        "cost": match_result["estimated_cost"],
                    }
                )
            else:
                matches.append(
                    {
                        "experiment_id": exp_id,
                        "experiment_request_id": exp_request_id,
                        "cost_record_id": None,
                        "cost_request_id": None,
                        "match_type": "failed",
                        "match_confidence": 0.0,
                        "provider": None,
                        "cost": None,
                    }
                )

        return matches

    def _find_best_cost_match(
        self, exp_request_id: str, exp_timestamp: Optional[datetime], group_name: str
    ) -> Optional[Dict]:
        """寻找最佳成本记录匹配"""

        # 策略1：精确request_id匹配
        if exp_request_id:
            self.cursor.execute(
                """
                SELECT id, request_id, provider_id, estimated_cost, timestamp
                FROM cost_records
                WHERE request_id = ?
            """,
                (exp_request_id,),
            )
            exact_match = self.cursor.fetchone()
            if exact_match:
                return {
                    "cost_id": exact_match["id"],
                    "cost_request_id": exact_match["request_id"],
                    "match_type": "exact_request_id",
                    "confidence": 1.0,
                    "provider": exact_match["provider_id"],
                    "estimated_cost": exact_match["estimated_cost"],
                }

        # 策略2：时间窗口匹配（实验记录时间±10分钟）
        if exp_timestamp:
            time_start = (exp_timestamp - timedelta(minutes=10)).isoformat()
            time_end = (exp_timestamp + timedelta(minutes=10)).isoformat()

            # 根据分组推断可能的provider
            provider_hint = self._infer_provider_from_group(group_name)

            query = """
                SELECT id, request_id, provider_id, estimated_cost, timestamp
                FROM cost_records
                WHERE timestamp BETWEEN ? AND ?
            """
            params = [time_start, time_end]

            if provider_hint:
                query += " AND provider_id = ?"
                params.append(provider_hint)

            query += " ORDER BY ABS(strftime('%s', timestamp) - strftime('%s', ?)) LIMIT 1"
            params.append(exp_timestamp.isoformat())

            self.cursor.execute(query, params)
            time_match = self.cursor.fetchone()

            if time_match:
                # 计算时间差（秒）
                cost_time = datetime.fromisoformat(time_match["timestamp"])
                time_diff = abs((cost_time - exp_timestamp).total_seconds())
                confidence = max(0.0, 1.0 - (time_diff / 600.0))  # 600秒=10分钟

                return {
                    "cost_id": time_match["id"],
                    "cost_request_id": time_match["request_id"],
                    "match_type": "time_window",
                    "confidence": confidence,
                    "provider": time_match["provider_id"],
                    "estimated_cost": time_match["estimated_cost"],
                }

        # 策略3：前缀匹配（实验request_id可能包含exp_前缀）
        if exp_request_id and exp_request_id.startswith("exp_"):
            # 尝试查找包含相似ID的成本记录
            self.cursor.execute(
                """
                SELECT id, request_id, provider_id, estimated_cost, timestamp
                FROM cost_records
                WHERE request_id LIKE ? OR request_id LIKE ?
                LIMIT 1
            """,
                (f"%{exp_request_id[4:]}%", f"%{exp_request_id}%"),
            )

            prefix_match = self.cursor.fetchone()
            if prefix_match:
                return {
                    "cost_id": prefix_match["id"],
                    "cost_request_id": prefix_match["request_id"],
                    "match_type": "prefix",
                    "confidence": 0.5,
                    "provider": prefix_match["provider_id"],
                    "estimated_cost": prefix_match["estimated_cost"],
                }

        return None

    def _infer_provider_from_group(self, group_name: str) -> Optional[str]:
        """从实验分组推断provider"""
        group_mapping = {
            "control": "dashscope",
            "treatment": "deepseek",
            "original": "dashscope",
            "migrated": "deepseek",
        }
        return group_mapping.get(group_name.lower())

    def apply_fixes(self, matches: List[Dict], experiment_id: str) -> Tuple[int, int, int, int]:
        """应用修复"""
        if self.dry_run:
            print("🔍 干运行模式：只分析不修改")
            return 0, 0, 0, len([m for m in matches if m["cost_record_id"] is not None])

        print(f"\n🔧 应用修复到实验 '{experiment_id}'...")

        exact_count = 0
        time_count = 0
        prefix_count = 0
        failed_count = 0

        for match in matches:
            if match["cost_record_id"] is None:
                failed_count += 1
                continue

            # 更新实验记录的cost_record_id
            try:
                self.cursor.execute(
                    """
                    UPDATE experiment_records
                    SET cost_record_id = ?
                    WHERE id = ? AND experiment_id = ?
                """,
                    (match["cost_record_id"], match["experiment_id"], experiment_id),
                )

                # 统计匹配类型
                if match["match_type"] == "exact_request_id":
                    exact_count += 1
                elif match["match_type"] == "time_window":
                    time_count += 1
                elif match["match_type"] == "prefix":
                    prefix_count += 1

            except Exception as e:
                print(f"❌ 更新记录 {match['experiment_id']} 失败: {e}")
                failed_count += 1

        if not self.dry_run:
            self.conn.commit()
            print(f"✅ 修复已提交到数据库")

        return exact_count, time_count, prefix_count, failed_count

    def validate_fixes(self, experiment_id: str) -> Tuple[int, List[Dict]]:
        """验证修复结果"""
        print(f"\n✅ 验证实验 '{experiment_id}' 的修复结果...")

        # 获取所有实验记录
        self.cursor.execute(
            """
            SELECT e.id, e.request_id, e.cost_record_id, e.group_name,
                   c.id as cost_id, c.request_id as cost_request_id,
                   c.provider_id, c.estimated_cost, c.timestamp
            FROM experiment_records e
            LEFT JOIN cost_records c ON e.cost_record_id = c.id
            WHERE e.experiment_id = ?
            ORDER BY e.recorded_at
        """,
            (experiment_id,),
        )

        records = [dict(row) for row in self.cursor.fetchall()]

        passed = 0
        errors = []

        for record in records:
            cost_record_id = record["cost_record_id"]

            if not cost_record_id:
                errors.append(
                    {
                        "experiment_id": record["id"],
                        "error": "cost_record_id为空",
                        "details": "修复后仍然没有关联的成本记录",
                    }
                )
                continue

            # 检查关联的成本记录是否存在
            if not record["cost_id"]:
                errors.append(
                    {
                        "experiment_id": record["id"],
                        "cost_record_id": cost_record_id,
                        "error": "关联的成本记录不存在",
                        "details": f"成本记录ID '{cost_record_id}' 在cost_records表中不存在",
                    }
                )
                continue

            # 检查provider一致性（如果可能）
            expected_provider = self._infer_provider_from_group(record["group_name"])
            actual_provider = record["provider_id"]

            if expected_provider and actual_provider and expected_provider != actual_provider:
                errors.append(
                    {
                        "experiment_id": record["id"],
                        "error": "provider不匹配",
                        "details": f"分组 '{record['group_name']}' 期望provider '{expected_provider}', 但关联到 '{actual_provider}'",
                    }
                )
                continue

            passed += 1

        return passed, errors

    def generate_report(
        self,
        experiment_id: str,
        matches: List[Dict],
        exact_count: int,
        time_count: int,
        prefix_count: int,
        failed_count: int,
        passed_count: int,
        errors: List[Dict],
    ) -> AssociationReport:
        """生成修复报告"""

        # 重新统计实验记录总数
        self.cursor.execute(
            """
            SELECT COUNT(*) as total, COUNT(cost_record_id) as with_cost
            FROM experiment_records
            WHERE experiment_id = ?
        """,
            (experiment_id,),
        )
        stats = self.cursor.fetchone()

        # 统计成本记录总数
        self.cursor.execute("SELECT COUNT(*) as total FROM cost_records")
        cost_stats = self.cursor.fetchone()

        # 成功的匹配
        successful_matches = [m for m in matches if m["cost_record_id"] is not None]

        report = AssociationReport(
            timestamp=datetime.now(),
            experiment_id=experiment_id,
            dry_run=self.dry_run,
            total_experiment_records=stats["total"],
            total_cost_records=cost_stats["total"],
            pre_existing_associations=stats["with_cost"],
            missing_associations=stats["total"] - stats["with_cost"],
            matched_by_exact_request_id=exact_count,
            matched_by_time_window=time_count,
            matched_by_prefix=prefix_count,
            failed_matches=failed_count,
            validation_passed=passed_count,
            validation_failed=len(errors),
            successful_matches=successful_matches[:10],  # 只保存前10个成功的匹配
            failed_matches_details=[m for m in matches if m["cost_record_id"] is None][
                :10
            ],  # 前10个失败
            validation_errors=errors[:10],  # 前10个验证错误
        )

        return report

    def save_report(self, report: AssociationReport, output_file: str = None):
        """保存报告到文件"""
        if output_file is None:
            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            output_file = f"/Volumes/1TB-M2/openclaw/mini-agent/reports/data_association_report_{timestamp}.json"

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

            print(f"📄 报告已保存到: {output_file}")
            return output_file
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="修复实验记录与成本记录之间的数据关联问题")
    parser.add_argument("--dry-run", action="store_true", default=True, help="只分析不修改（默认）")
    parser.add_argument("--fix", action="store_true", help="执行修复操作")
    parser.add_argument("--experiment", type=str, help="指定实验ID（默认自动检测）")

    args = parser.parse_args()

    # 如果指定了--fix，则关闭dry-run
    if args.fix:
        args.dry_run = False

    print("🚀 数据关联修复工具启动")
    print(f"数据库: {DB_PATH}")
    print(f"模式: {'修复模式' if not args.dry_run else '干运行（只分析不修改）'}")

    fixer = DataAssociationFixer(DB_PATH, dry_run=args.dry_run)

    if not fixer.connect():
        sys.exit(1)

    try:
        # 1. 确定实验ID
        experiment_id = args.experiment
        if not experiment_id:
            experiment_id = fixer.detect_migration_experiment()

        if not experiment_id:
            print("❌ 未找到实验ID，请使用 --experiment 参数指定")
            sys.exit(1)

        print(f"📊 目标实验: {experiment_id}")

        # 2. 分析当前状态
        analysis = fixer.analyze_current_state(experiment_id)

        print(f"\n📈 分析结果:")
        print(f"  实验记录总数: {analysis['experiment_stats']['total']}")
        print(f"  已有成本关联: {analysis['experiment_stats']['with_cost_id']}")
        print(f"  缺失成本关联: {analysis['experiment_stats']['without_cost_id']}")
        print(f"  成本记录总数: {analysis['cost_stats']['total']}")

        # 3. 匹配实验记录到成本记录
        matches = fixer.match_experiment_to_cost_records(experiment_id)

        # 统计匹配结果
        total_matches = len(matches)
        successful_matches = len([m for m in matches if m["cost_record_id"] is not None])
        failed_matches = total_matches - successful_matches

        print(f"\n🔗 匹配结果:")
        print(f"  总匹配尝试: {total_matches}")
        print(f"  成功匹配: {successful_matches}")
        print(f"  匹配失败: {failed_matches}")

        if successful_matches > 0:
            match_types = {}
            for match in matches:
                if match["cost_record_id"]:
                    match_type = match["match_type"]
                    match_types[match_type] = match_types.get(match_type, 0) + 1

            print(f"  匹配类型分布:")
            for match_type, count in match_types.items():
                print(f"    - {match_type}: {count}")

        # 4. 应用修复（如果不是干运行）
        if not args.dry_run:
            exact_count, time_count, prefix_count, failed_count = fixer.apply_fixes(
                matches, experiment_id
            )
        else:
            # 干运行模式下，统计预期的匹配类型
            match_types = {}
            for match in matches:
                if match["cost_record_id"]:
                    match_type = match["match_type"]
                    match_types[match_type] = match_types.get(match_type, 0) + 1

            exact_count = match_types.get("exact_request_id", 0)
            time_count = match_types.get("time_window", 0)
            prefix_count = match_types.get("prefix", 0)
            failed_count = failed_matches

        # 5. 验证修复结果
        passed_count, errors = fixer.validate_fixes(experiment_id)

        # 6. 生成报告
        report = fixer.generate_report(
            experiment_id,
            matches,
            exact_count,
            time_count,
            prefix_count,
            failed_count,
            passed_count,
            errors,
        )

        # 7. 打印报告
        report.print_summary()

        # 8. 保存报告
        if not args.dry_run:
            report_file = fixer.save_report(report)

        if errors:
            print(f"\n⚠️  验证错误 ({len(errors)} 个):")
            for i, error in enumerate(errors[:5], 1):
                print(f"  {i}. {error['error']}: {error.get('details', '')}")
                if i >= 5 and len(errors) > 5:
                    print(f"  ... 还有 {len(errors) - 5} 个错误")
                    break

        print(f"\n✅ 数据关联{'验证' if args.dry_run else '修复'}完成")

    finally:
        fixer.close()


if __name__ == "__main__":
    main()
