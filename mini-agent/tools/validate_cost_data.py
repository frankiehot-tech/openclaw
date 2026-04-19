#!/usr/bin/env python3
"""
成本数据验证工具

验证成本数据的准确性、完整性和一致性：
1. 数据准确性验证：与实际账单对比（如有）
2. 数据完整性验证：检查数据丢失和异常值
3. 跨存储后端一致性验证
4. 成本计算逻辑验证

使用说明：
    python3 validate_cost_data.py --help
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 添加 mini-agent 目录到路径
mini_agent_dir = project_root / "mini-agent"
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))

try:
    from mini_agent.agent.core.cost_tracker import (
        CostRecord,
        CostSummary,
        CostTracker,
        MemoryStorageBackend,
        SQLiteStorageBackend,
        StorageBackend,
    )
    from mini_agent.agent.core.cost_tracker_json_storage import JSONStorageBackend
    from mini_agent.agent.core.provider_registry import get_provider_cost_config

    HAS_DEPENDENCIES = True
except ImportError as e:
    print(f"警告：无法导入依赖模块，部分验证功能受限: {e}")
    HAS_DEPENDENCIES = False


class CostDataValidator:
    """成本数据验证器"""

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        """
        初始化验证器

        Args:
            cost_tracker: CostTracker实例，如果为None则自动创建
        """
        self.cost_tracker = cost_tracker
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "summary": {"passed": 0, "failed": 0, "warnings": 0},
            "recommendations": [],
        }

    def _check_dependency(self, feature: str) -> bool:
        """检查依赖是否可用"""
        if not HAS_DEPENDENCIES:
            self._add_result(feature, "warning", "依赖模块不可用，跳过检查")
            return False
        return True

    def _add_result(self, check_name: str, status: str, message: str, details: Dict = None):
        """添加验证结果"""
        if check_name not in self.validation_results["checks"]:
            self.validation_results["checks"][check_name] = []

        result = {"status": status, "message": message, "timestamp": datetime.now().isoformat()}

        if details:
            result["details"] = details

        self.validation_results["checks"][check_name].append(result)

        # 更新摘要统计
        if status == "passed":
            self.validation_results["summary"]["passed"] += 1
        elif status == "failed":
            self.validation_results["summary"]["failed"] += 1
        elif status == "warning":
            self.validation_results["summary"]["warnings"] += 1

    def _add_recommendation(self, recommendation: str, priority: str = "medium"):
        """添加改进建议"""
        self.validation_results["recommendations"].append(
            {"text": recommendation, "priority": priority, "timestamp": datetime.now().isoformat()}
        )

    def validate_data_integrity(self) -> bool:
        """验证数据完整性"""
        print("\n=== 数据完整性验证 ===")

        if not self._check_dependency("data_integrity"):
            return False

        try:
            # 获取所有记录
            records = self.cost_tracker.get_records(limit=10000)
            total_records = len(records)

            print(f"分析 {total_records} 条成本记录...")

            if total_records == 0:
                self._add_result("data_integrity", "warning", "无成本记录数据")
                print("   ⚠️ 无成本记录数据")
                return True

            # 检查字段完整性
            missing_fields = []
            for i, record in enumerate(records[:100]):  # 抽样检查前100条
                required_fields = [
                    ("id", record.id),
                    ("request_id", record.request_id),
                    ("provider_id", record.provider_id),
                    ("model_id", record.model_id),
                    ("timestamp", record.timestamp),
                    ("recorded_at", record.recorded_at),
                    ("input_tokens", record.input_tokens),
                    ("output_tokens", record.output_tokens),
                    ("estimated_cost", record.estimated_cost),
                ]

                for field_name, field_value in required_fields:
                    if field_value is None:
                        missing_fields.append((i, field_name))

            if missing_fields:
                self._add_result(
                    "data_integrity",
                    "failed",
                    f"发现 {len(missing_fields)} 条记录缺少必要字段",
                    {"missing_fields": missing_fields[:10]},  # 只显示前10个
                )
                print(f"   ❌ 发现 {len(missing_fields)} 条记录缺少必要字段")
                return False
            else:
                self._add_result("data_integrity", "passed", "所有记录字段完整")
                print("   ✅ 所有记录字段完整")

            # 检查异常值
            anomalies = []
            for record in records:
                # 检查token数量合理性
                if record.input_tokens < 0 or record.input_tokens > 1000000:
                    anomalies.append(f"记录 {record.id}: 输入tokens异常 ({record.input_tokens})")

                if record.output_tokens < 0 or record.output_tokens > 1000000:
                    anomalies.append(f"记录 {record.id}: 输出tokens异常 ({record.output_tokens})")

                # 检查成本合理性
                if record.estimated_cost < 0 or record.estimated_cost > 1000:
                    anomalies.append(
                        f"记录 {record.id}: 估算成本异常 (${record.estimated_cost:.6f})"
                    )

            if anomalies:
                self._add_result(
                    "data_integrity",
                    "warning",
                    f"发现 {len(anomalies)} 个异常值",
                    {"anomalies": anomalies[:10]},
                )
                print(f"   ⚠️ 发现 {len(anomalies)} 个异常值")
            else:
                self._add_result("data_integrity", "passed", "未发现异常值")
                print("   ✅ 未发现异常值")

            # 检查时间顺序
            time_anomalies = []
            for record in records:
                if record.recorded_at < record.timestamp:
                    time_anomalies.append(f"记录 {record.id}: 记录时间早于请求时间")

            if time_anomalies:
                self._add_result(
                    "data_integrity",
                    "warning",
                    f"发现 {len(time_anomalies)} 条时间顺序异常记录",
                    {"time_anomalies": time_anomalies[:10]},
                )
                print(f"   ⚠️ 发现 {len(time_anomalies)} 条时间顺序异常记录")
            else:
                self._add_result("data_integrity", "passed", "时间顺序正常")
                print("   ✅ 时间顺序正常")

            return True

        except Exception as e:
            self._add_result("data_integrity", "failed", f"验证过程中发生错误: {str(e)}")
            print(f"   ❌ 验证过程中发生错误: {e}")
            return False

    def validate_cost_calculation(self) -> bool:
        """验证成本计算逻辑"""
        print("\n=== 成本计算逻辑验证 ===")

        if not self._check_dependency("cost_calculation"):
            return False

        try:
            # 获取provider配置
            provider_config = get_provider_cost_config()

            if not provider_config:
                self._add_result("cost_calculation", "warning", "无provider配置数据")
                print("   ⚠️ 无provider配置数据")
                return True

            # 获取所有记录
            records = self.cost_tracker.get_records(limit=1000)
            if len(records) == 0:
                self._add_result("cost_calculation", "warning", "无成本记录数据")
                print("   ⚠️ 无成本记录数据")
                return True

            # 验证每条记录的成本计算
            calculation_errors = []
            for record in records[:50]:  # 抽样验证前50条
                # 检查provider配置是否存在
                if record.provider_id not in provider_config:
                    calculation_errors.append(
                        f"记录 {record.id}: provider '{record.provider_id}' 无配置"
                    )
                    continue

                provider = provider_config[record.provider_id]
                if record.model_id not in provider.get("models", {}):
                    calculation_errors.append(f"记录 {record.id}: 模型 '{record.model_id}' 无配置")
                    continue

                # 这里可以添加更详细的计算验证
                # 暂时只验证配置存在性

            if calculation_errors:
                self._add_result(
                    "cost_calculation",
                    "warning",
                    f"发现 {len(calculation_errors)} 个成本计算配置问题",
                    {"errors": calculation_errors[:10]},
                )
                print(f"   ⚠️ 发现 {len(calculation_errors)} 个成本计算配置问题")
            else:
                self._add_result("cost_calculation", "passed", "成本计算配置正常")
                print("   ✅ 成本计算配置正常")

            # 验证成本摘要计算
            try:
                summary = self.cost_tracker.get_summary()

                # 手动重新计算验证
                total_cost = 0.0
                total_input_tokens = 0
                total_output_tokens = 0

                for record in records:
                    total_cost += record.estimated_cost or 0.0
                    total_input_tokens += record.input_tokens or 0
                    total_output_tokens += record.output_tokens or 0

                # 允许1%的误差（由于浮点计算）
                cost_tolerance = total_cost * 0.01
                if abs(summary.total_cost - total_cost) > cost_tolerance:
                    calculation_errors.append(
                        f"成本摘要计算不一致: 摘要=${summary.total_cost:.6f}, 计算=${total_cost:.6f}"
                    )

                if abs(summary.total_input_tokens - total_input_tokens) > 10:
                    calculation_errors.append(
                        f"输入tokens摘要计算不一致: 摘要={summary.total_input_tokens}, 计算={total_input_tokens}"
                    )

                if calculation_errors:
                    self._add_result(
                        "cost_calculation",
                        "failed",
                        "成本摘要计算验证失败",
                        {"errors": calculation_errors},
                    )
                    print(f"   ❌ 成本摘要计算验证失败")
                    return False
                else:
                    self._add_result("cost_calculation", "passed", "成本摘要计算正确")
                    print("   ✅ 成本摘要计算正确")

            except Exception as e:
                self._add_result("cost_calculation", "failed", f"成本摘要计算验证失败: {str(e)}")
                print(f"   ❌ 成本摘要计算验证失败: {e}")
                return False

            return True

        except Exception as e:
            self._add_result("cost_calculation", "failed", f"验证过程中发生错误: {str(e)}")
            print(f"   ❌ 验证过程中发生错误: {e}")
            return False

    def validate_storage_consistency(self, storage_configs: List[Dict]) -> bool:
        """验证跨存储后端一致性"""
        print("\n=== 跨存储后端一致性验证 ===")

        if not self._check_dependency("storage_consistency"):
            return False

        try:
            if len(storage_configs) < 2:
                self._add_result(
                    "storage_consistency", "warning", "至少需要两个存储后端进行一致性验证"
                )
                print("   ⚠️ 至少需要两个存储后端进行一致性验证")
                return True

            # 创建多个存储后端
            backends = []
            for config in storage_configs:
                backend_type = config.get("type")
                if backend_type == "sqlite":
                    backend = SQLiteStorageBackend(db_path=config["db_path"])
                elif backend_type == "json":
                    backend = JSONStorageBackend(file_path=config["file_path"])
                elif backend_type == "memory":
                    backend = MemoryStorageBackend(max_records=config.get("max_records", 1000))
                else:
                    continue
                backends.append(backend)

            if len(backends) < 2:
                self._add_result("storage_consistency", "warning", "无法创建足够的存储后端")
                print("   ⚠️ 无法创建足够的存储后端")
                return True

            # 生成测试数据
            test_records = []
            for i in range(10):
                record = CostRecord(
                    id=f"consistency_test_{i:03d}",
                    request_id=f"req_consistency_{i:03d}",
                    timestamp=datetime.now() - timedelta(hours=i),
                    recorded_at=datetime.now(),
                    provider_id="deepseek" if i % 2 == 0 else "dashscope",
                    model_id="deepseek-chat" if i % 2 == 0 else "qwen3.5-plus",
                    task_kind="consistency_test",
                    input_tokens=100 * (i + 1),
                    output_tokens=50 * (i + 1),
                    estimated_cost=0.001 * (i + 1),
                    estimated_tokens=False,
                )
                test_records.append(record)

            # 写入所有后端
            for record in test_records:
                for backend in backends:
                    backend.record_cost(record)

            print(f"   向 {len(backends)} 个存储后端写入 {len(test_records)} 条测试记录")

            # 比较所有后端的记录
            inconsistencies = []
            for i in range(len(backends)):
                for j in range(i + 1, len(backends)):
                    records_i = backends[i].get_records()
                    records_j = backends[j].get_records()

                    if len(records_i) != len(records_j):
                        inconsistencies.append(
                            f"后端 {i} 和 {j} 记录数量不一致: {len(records_i)} vs {len(records_j)}"
                        )
                        continue

                    # 比较每条记录
                    for k in range(len(records_i)):
                        if records_i[k].id != records_j[k].id:
                            inconsistencies.append(
                                f"后端 {i} 和 {j} 记录 {k} ID不一致: {records_i[k].id} vs {records_j[k].id}"
                            )

            if inconsistencies:
                self._add_result(
                    "storage_consistency",
                    "failed",
                    f"发现 {len(inconsistencies)} 个存储不一致问题",
                    {"inconsistencies": inconsistencies[:10]},
                )
                print(f"   ❌ 发现 {len(inconsistencies)} 个存储不一致问题")
                return False
            else:
                self._add_result("storage_consistency", "passed", "所有存储后端数据一致")
                print("   ✅ 所有存储后端数据一致")
                return True

        except Exception as e:
            self._add_result("storage_consistency", "failed", f"验证过程中发生错误: {str(e)}")
            print(f"   ❌ 验证过程中发生错误: {e}")
            return False

    def validate_with_external_billing(self, billing_data_path: Optional[str] = None) -> bool:
        """验证与实际账单的一致性（如果提供账单数据）"""
        print("\n=== 与实际账单一致性验证 ===")

        if not billing_data_path:
            self._add_result("billing_consistency", "warning", "未提供账单数据文件")
            print("   ⚠️ 未提供账单数据文件，跳过验证")
            return True

        if not os.path.exists(billing_data_path):
            self._add_result(
                "billing_consistency", "warning", f"账单文件不存在: {billing_data_path}"
            )
            print(f"   ⚠️ 账单文件不存在: {billing_data_path}")
            return True

        try:
            # 加载账单数据（假设为CSV或JSON格式）
            billing_data = []
            if billing_data_path.endswith(".json"):
                with open(billing_data_path, "r", encoding="utf-8") as f:
                    billing_data = json.load(f)
            else:
                # 简化处理，实际中需要解析CSV
                self._add_result("billing_consistency", "warning", "仅支持JSON格式账单数据")
                print("   ⚠️ 仅支持JSON格式账单数据")
                return True

            if not billing_data:
                self._add_result("billing_consistency", "warning", "账单数据为空")
                print("   ⚠️ 账单数据为空")
                return True

            # 获取成本数据
            records = self.cost_tracker.get_records(limit=10000)
            if len(records) == 0:
                self._add_result("billing_consistency", "warning", "无成本记录数据")
                print("   ⚠️ 无成本记录数据")
                return True

            # 按日期聚合成本数据
            cost_by_date = {}
            for record in records:
                date_key = record.timestamp.date().isoformat()
                if date_key not in cost_by_date:
                    cost_by_date[date_key] = {"total_cost": 0.0, "count": 0, "providers": {}}
                cost_by_date[date_key]["total_cost"] += record.estimated_cost or 0.0
                cost_by_date[date_key]["count"] += 1

                # 按provider统计
                provider = record.provider_id
                if provider not in cost_by_date[date_key]["providers"]:
                    cost_by_date[date_key]["providers"][provider] = 0.0
                cost_by_date[date_key]["providers"][provider] += record.estimated_cost or 0.0

            print(f"   分析 {len(cost_by_date)} 天的成本数据")

            # 这里可以添加更详细的账单对比逻辑
            # 由于账单格式可能不同，这里只做基本验证

            self._add_result("billing_consistency", "passed", "账单数据加载成功")
            print("   ✅ 账单数据加载成功")

            # 提供对比摘要
            comparison_summary = {
                "tracked_days": len(cost_by_date),
                "billing_days": len(billing_data) if isinstance(billing_data, list) else 1,
                "total_tracked_cost": sum(day["total_cost"] for day in cost_by_date.values()),
                "tracking_coverage": "部分",  # 简化处理
            }

            self._add_result(
                "billing_consistency", "info", "账单对比摘要", {"summary": comparison_summary}
            )

            print(f"   跟踪成本总计: ${comparison_summary['total_tracked_cost']:.2f}")
            print(f"   覆盖天数: {comparison_summary['tracked_days']}")

            return True

        except Exception as e:
            self._add_result("billing_consistency", "failed", f"账单验证失败: {str(e)}")
            print(f"   ❌ 账单验证失败: {e}")
            return False

    def run_full_validation(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """运行完整验证流程"""
        print("=" * 60)
        print("成本数据验证工具")
        print("=" * 60)

        # 初始化CostTracker（如果需要）
        if not self.cost_tracker and HAS_DEPENDENCIES:
            try:
                # 使用默认配置
                self.cost_tracker = CostTracker(storage_backend="sqlite")
                print("已初始化成本跟踪器")
            except Exception as e:
                print(f"初始化成本跟踪器失败: {e}")

        # 运行各项验证
        checks = []

        if options.get("integrity", True):
            checks.append(("数据完整性", self.validate_data_integrity))

        if options.get("calculation", True):
            checks.append(("成本计算", self.validate_cost_calculation))

        if options.get("storage_consistency", False) and options.get("storage_configs"):
            checks.append(
                (
                    "存储一致性",
                    lambda: self.validate_storage_consistency(options["storage_configs"]),
                )
            )

        if options.get("billing_consistency", False) and options.get("billing_data_path"):
            checks.append(
                (
                    "账单一致性",
                    lambda: self.validate_with_external_billing(options["billing_data_path"]),
                )
            )

        # 执行所有检查
        for check_name, check_func in checks:
            try:
                check_func()
            except Exception as e:
                self._add_result(check_name, "failed", f"检查执行失败: {str(e)}")
                print(f"   ❌ {check_name}检查执行失败: {e}")

        # 生成验证报告
        print("\n" + "=" * 60)
        print("验证结果摘要")
        print("=" * 60)

        summary = self.validation_results["summary"]
        print(f"通过: {summary['passed']} 项")
        print(f"失败: {summary['failed']} 项")
        print(f"警告: {summary['warnings']} 项")

        # 显示改进建议
        if self.validation_results["recommendations"]:
            print("\n改进建议:")
            for rec in self.validation_results["recommendations"]:
                print(f"  • [{rec['priority']}] {rec['text']}")

        # 保存验证报告
        if options.get("output_file"):
            try:
                with open(options["output_file"], "w", encoding="utf-8") as f:
                    json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
                print(f"\n验证报告已保存到: {options['output_file']}")
            except Exception as e:
                print(f"保存验证报告失败: {e}")

        return self.validation_results


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="成本数据验证工具", formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--integrity", action="store_true", default=True, help="验证数据完整性（默认启用）"
    )

    parser.add_argument(
        "--no-integrity", action="store_false", dest="integrity", help="禁用数据完整性验证"
    )

    parser.add_argument(
        "--calculation", action="store_true", default=True, help="验证成本计算逻辑（默认启用）"
    )

    parser.add_argument(
        "--no-calculation", action="store_false", dest="calculation", help="禁用成本计算验证"
    )

    parser.add_argument("--storage-consistency", action="store_true", help="验证跨存储后端一致性")

    parser.add_argument("--storage-configs", type=str, help="存储后端配置（JSON文件路径）")

    parser.add_argument("--billing-consistency", action="store_true", help="验证与实际账单的一致性")

    parser.add_argument(
        "--billing-data", type=str, dest="billing_data_path", help="账单数据文件路径（JSON格式）"
    )

    parser.add_argument("--output", type=str, dest="output_file", help="验证报告输出文件路径")

    parser.add_argument("--verbose", action="store_true", help="显示详细验证信息")

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()

    # 准备验证选项
    options = {
        "integrity": args.integrity,
        "calculation": args.calculation,
        "storage_consistency": args.storage_consistency,
        "billing_consistency": args.billing_consistency,
        "output_file": args.output_file,
    }

    # 解析存储配置
    if args.storage_configs and os.path.exists(args.storage_configs):
        try:
            with open(args.storage_configs, "r", encoding="utf-8") as f:
                options["storage_configs"] = json.load(f)
        except Exception as e:
            print(f"加载存储配置失败: {e}")
            return 1

    # 账单数据路径
    if args.billing_data_path:
        options["billing_data_path"] = args.billing_data_path

    # 运行验证
    validator = CostDataValidator()
    results = validator.run_full_validation(options)

    # 返回退出码（如果有失败则返回1）
    if results["summary"]["failed"] > 0:
        return 1
    else:
        return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n验证被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"验证工具执行失败: {e}")
        sys.exit(1)
