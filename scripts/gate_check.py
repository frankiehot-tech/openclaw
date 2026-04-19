#!/usr/bin/env python3
"""
OpenHuman MVP 稳定性门禁检查

检查健康数据完整性和阈值违规，阻止在数据缺失或超阈值时宣称MVP稳定。
实现最小负路径验证。
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Tuple

import yaml

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入稳定性收集器
try:
    from scripts.collect_stability_metrics import StabilityMetricsCollector
except ImportError:
    # 如果导入失败，添加当前目录到路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from collect_stability_metrics import StabilityMetricsCollector

logger = logging.getLogger(__name__)


class StabilityGate:
    """稳定性门禁检查器"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化门禁检查器"""
        self.collector = StabilityMetricsCollector(config_path)
        self.config = self.collector.config
        logger.info("稳定性门禁检查器初始化完成")

    def check_gate(self) -> Tuple[bool, Dict[str, Any]]:
        """
        执行门禁检查

        Returns:
            (通过与否, 详细结果)
        """
        # 收集指标和告警
        metrics = self.collector.collect_metrics()
        alerts = self.collector.evaluate_alerts(metrics)

        # 应用门禁规则
        gate_results = self._apply_gate_rules(metrics, alerts)

        # 生成总体结果
        passed = gate_results["overall_pass"]
        result = {
            "timestamp": datetime.now().isoformat(),
            "gate_id": f"stability_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "passed": passed,
            "gate_results": gate_results,
            "metric_count": len(metrics),
            "alert_count": len(alerts),
            "alerts_by_severity": {
                "P0": len([a for a in alerts if a.severity == 0]),
                "P1": len([a for a in alerts if a.severity == 1]),
                "P2": len([a for a in alerts if a.severity == 2]),
            },
            "mvp_stability_claim_allowed": passed,
            "recommended_action": "继续" if passed else "停止并调查",
        }

        return passed, result

    def _apply_gate_rules(self, metrics: List[Any], alerts: List[Any]) -> Dict[str, Any]:
        """应用门禁规则"""
        results = {
            "data_integrity_check": self._check_data_integrity(metrics),
            "threshold_violation_check": self._check_threshold_violations(alerts),
            "freshness_check": self._check_data_freshness(metrics),
            "critical_metric_presence_check": self._check_critical_metrics_presence(metrics),
            "overall_pass": False,
        }

        # 确定总体结果
        # 规则：所有检查都必须通过才能宣称MVP稳定
        all_passed = (
            results["data_integrity_check"]["passed"]
            and results["threshold_violation_check"]["passed"]
            and results["freshness_check"]["passed"]
            and results["critical_metric_presence_check"]["passed"]
        )

        results["overall_pass"] = all_passed
        return results

    def _check_data_integrity(self, metrics: List[Any]) -> Dict[str, Any]:
        """检查数据完整性"""
        # 查找数据完整性指标
        data_integrity_metric = next(
            (m for m in metrics if m.metric_type == "data_integrity"), None
        )

        if not data_integrity_metric:
            return {
                "passed": False,
                "reason": "未找到数据完整性指标",
                "details": "无法评估数据完整性",
                "severity": "P0",
            }

        integrity_score = data_integrity_metric.value
        context = data_integrity_metric.context

        # 检查关键文件缺失情况
        missing_files = []
        if "file_status" in context:
            for file_path, exists in context["file_status"].items():
                if not exists:
                    missing_files.append(file_path)

        # 应用门禁规则
        passed = integrity_score >= 0.8  # 至少80%的关键文件存在
        reason = ""

        if not passed:
            if integrity_score < 0.5:
                reason = f"关键数据源严重缺失（完整性评分: {integrity_score:.2f}）"
                severity = "P0"
            else:
                reason = f"数据源不完整（完整性评分: {integrity_score:.2f}）"
                severity = "P1"
        else:
            reason = f"数据完整性良好（评分: {integrity_score:.2f}）"
            severity = "none"

        return {
            "passed": passed,
            "reason": reason,
            "details": {
                "integrity_score": integrity_score,
                "missing_files": missing_files,
                "total_files": context.get("total_count", 0),
            },
            "severity": severity,
        }

    def _check_threshold_violations(self, alerts: List[Any]) -> Dict[str, Any]:
        """检查阈值违规"""
        # 检查是否有P0或P1告警
        p0_alerts = [a for a in alerts if a.severity == 0]
        p1_alerts = [a for a in alerts if a.severity == 1]

        # 门禁规则：不允许任何P0告警，最多允许1个P1告警
        passed = len(p0_alerts) == 0 and len(p1_alerts) <= 1

        if not passed:
            if p0_alerts:
                reason = f"存在 {len(p0_alerts)} 个P0（严重）告警"
                severity = "P0"
            else:
                reason = f"存在 {len(p1_alerts)} 个P1（警告）告警（最多允许1个）"
                severity = "P1"
        else:
            reason = f"阈值检查通过（P0: {len(p0_alerts)}, P1: {len(p1_alerts)}, P2: {len([a for a in alerts if a.severity == 2])}）"
            severity = "none"

        return {
            "passed": passed,
            "reason": reason,
            "details": {
                "p0_alerts": [{"metric": a.metric_id, "message": a.message} for a in p0_alerts],
                "p1_alerts": [{"metric": a.metric_id, "message": a.message} for a in p1_alerts],
                "total_alerts": len(alerts),
            },
            "severity": severity,
        }

    def _check_data_freshness(self, metrics: List[Any]) -> Dict[str, Any]:
        """检查数据新鲜度"""
        # 检查指标时间戳的新鲜度
        now = datetime.now()
        stale_metrics = []

        for metric in metrics:
            try:
                # 解析时间戳
                timestamp_str = metric.timestamp
                if "Z" in timestamp_str:
                    timestamp_str = timestamp_str.replace("Z", "+00:00")

                metric_time = datetime.fromisoformat(timestamp_str)
                age_hours = (now - metric_time).total_seconds() / 3600

                # 根据指标类型设置不同的新鲜度阈值
                max_age_hours = 24  # 默认24小时
                if metric.metric_type in ["response_time", "error_rate"]:
                    max_age_hours = 48  # 性能指标允许更旧
                elif metric.metric_type == "availability":
                    max_age_hours = 1  # 可用性指标需要非常新鲜

                if age_hours > max_age_hours:
                    stale_metrics.append(
                        {
                            "metric_id": metric.metric_id,
                            "age_hours": age_hours,
                            "max_allowed_hours": max_age_hours,
                        }
                    )
            except Exception as e:
                logger.warning(f"解析指标时间戳失败 {metric.metric_id}: {e}")
                stale_metrics.append({"metric_id": metric.metric_id, "error": str(e)})

        # 应用门禁规则：允许最多1个指标陈旧
        passed = len(stale_metrics) <= 1

        if not passed:
            reason = f"有 {len(stale_metrics)} 个指标数据陈旧"
            severity = "P1" if len(stale_metrics) <= 3 else "P0"
        else:
            reason = f"数据新鲜度检查通过（{len(stale_metrics)} 个陈旧指标）"
            severity = "none"

        return {
            "passed": passed,
            "reason": reason,
            "details": {"stale_metrics": stale_metrics, "total_metrics": len(metrics)},
            "severity": severity,
        }

    def _check_critical_metrics_presence(self, metrics: List[Any]) -> Dict[str, Any]:
        """检查关键指标是否存在"""
        # 定义关键指标类型
        critical_metric_types = ["availability", "response_time", "error_rate"]

        present_types = set(m.metric_type for m in metrics)
        missing_types = set(critical_metric_types) - present_types

        # 应用门禁规则：必须存在所有关键指标
        passed = len(missing_types) == 0

        if not passed:
            reason = f"缺少关键指标类型: {', '.join(missing_types)}"
            severity = "P0" if "availability" in missing_types else "P1"
        else:
            reason = "所有关键指标均存在"
            severity = "none"

        return {
            "passed": passed,
            "reason": reason,
            "details": {
                "critical_metric_types": critical_metric_types,
                "present_types": list(present_types),
                "missing_types": list(missing_types),
            },
            "severity": severity,
        }

    def enforce_gate(self, blocking: bool = True) -> bool:
        """
        强制执行门禁检查

        Args:
            blocking: 如果为True，检查失败时退出程序

        Returns:
            通过与否
        """
        passed, result = self.check_gate()

        # 输出结果
        self._print_gate_result(result)

        # 如果阻塞且未通过，退出程序
        if blocking and not passed:
            logger.error("稳定性门禁检查失败，阻止MVP稳定性声明")
            sys.exit(1)

        return passed

    def _print_gate_result(self, result: Dict[str, Any]) -> None:
        """打印门禁检查结果"""
        print("\n" + "=" * 60)
        print("OpenHuman MVP 稳定性门禁检查")
        print("=" * 60)

        print(f"\n检查时间: {result['timestamp']}")
        print(f"门禁ID: {result['gate_id']}")
        print(f"总体结果: {'✅ 通过' if result['passed'] else '❌ 失败'}")

        print("\n详细检查结果:")
        for check_name, check_result in result["gate_results"].items():
            if check_name == "overall_pass":
                continue

            status = "✅ 通过" if check_result["passed"] else "❌ 失败"
            print(f"  {check_name}: {status}")
            print(f"    原因: {check_result['reason']}")
            if "severity" in check_result and check_result["severity"] != "none":
                print(f"    严重等级: {check_result['severity']}")

        print(f"\n指标统计:")
        print(f"  总指标数: {result['metric_count']}")
        print(f"  总告警数: {result['alert_count']}")
        for severity, count in result["alerts_by_severity"].items():
            print(f"    {severity}告警: {count}")

        print(
            f"\nMVP稳定性声明: {'✅ 允许' if result['mvp_stability_claim_allowed'] else '❌ 阻止'}"
        )
        print(f"推荐操作: {result['recommended_action']}")

        print("\n" + "=" * 60)


# 兼容性导入
from datetime import datetime
from typing import Optional


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 解析命令行参数
    import argparse

    parser = argparse.ArgumentParser(description="OpenHuman MVP稳定性门禁检查")
    parser.add_argument("--non-blocking", action="store_true", help="非阻塞模式，失败时不退出")
    parser.add_argument("--output", type=str, help="输出JSON结果文件路径")
    parser.add_argument("--config", type=str, help="配置文件路径")

    args = parser.parse_args()

    # 初始化门禁检查器
    gate = StabilityGate(args.config)

    # 执行门禁检查
    passed = gate.enforce_gate(blocking=not args.non_blocking)

    # 如果需要，输出结果文件
    if args.output:
        _, result = gate.check_gate()
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n详细结果已保存: {args.output}")

    # 返回退出码
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
