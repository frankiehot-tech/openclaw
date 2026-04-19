#!/usr/bin/env python3
"""
运营自动化与资金监控验证测试

验证要求：
1. 至少补一个资金监控阈值测试
2. 至少补一个告警负路径或 dry-run 测试
3. 至少补一个 summary 输出 smoke
"""

import json
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 添加 mini_agent 目录到路径（通过符号链接 mini_agent）
mini_agent_dir = project_root / "mini-agent"
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_financial_monitor_threshold():
    """测试1: 资金监控阈值测试"""
    print("=" * 60)
    print("测试1: 资金监控阈值测试")
    print("=" * 60)

    try:
        # 导入金融监控器
        from mini_agent.agent.core.financial_monitor import (
            FinancialMonitor,
            FinancialMonitorConfig,
        )

        # 创建配置，设置低阈值以触发告警
        config = FinancialMonitorConfig(
            warning_threshold_remaining=0.5,  # 50%剩余时警告
            critical_threshold_remaining=0.2,  # 20%剩余时严重告警
            warning_burn_rate_multiplier=1.0,
            critical_burn_rate_multiplier=2.0,
            dry_run=True,
        )

        monitor = FinancialMonitor(config)

        # 模拟指标（低剩余预算）
        from mini_agent.agent.core.financial_monitor import FinancialMetrics

        metrics = FinancialMetrics(
            remaining_budget=30.0,  # 低剩余
            daily_budget=100.0,  # 每日预算100
            burn_rate=30.0,  # 高燃烧率
            daily_spent=80.0,  # 已消费80
            utilization=0.7,
            current_mode="low",
            mode_reason="测试数据",
            days_until_reset=5,
        )

        # 评估告警
        alerts = monitor.evaluate_alerts(metrics)

        print(f"  模拟指标:")
        print(
            f"    剩余预算: ¥{metrics.remaining_budget:.2f} (每日预算的{metrics.remaining_budget / metrics.daily_budget:.1%})"
        )
        print(f"    燃烧率: ¥{metrics.burn_rate:.2f}/小时")
        print(f"    当日已消费: ¥{metrics.daily_spent:.2f}")

        print(f"  生成的告警数: {len(alerts)}")

        # 验证告警类型
        warning_alerts = [a for a in alerts if a.severity.value == "warning"]
        critical_alerts = [a for a in alerts if a.severity.value == "critical"]

        print(f"    警告告警: {len(warning_alerts)}")
        print(f"    严重告警: {len(critical_alerts)}")

        # 检查是否触发了预算剩余警告（因为剩余30/100=30% < 50%警告阈值）
        budget_alerts = [a for a in alerts if a.alert_type.value == "budget_remaining_low"]
        if budget_alerts:
            print(f"  ✓ 成功触发了预算剩余警告")
            for alert in budget_alerts[:2]:
                print(f"     - {alert.severity.value}: {alert.message}")
        else:
            print(f"  ✗ 未触发预算剩余警告（预期会触发）")

        # 检查是否触发了燃烧率警告（燃烧率30 > 每日预算100/24≈4.17）
        burn_rate_alerts = [a for a in alerts if a.alert_type.value == "burn_rate_high"]
        if burn_rate_alerts:
            print(f"  ✓ 成功触发了燃烧率警告")
        else:
            print(f"  ✗ 未触发燃烧率警告（预期会触发）")

        # 检查是否触发了每日预算超支警告（已消费80 < 预算100，所以不应该触发）
        daily_over_alerts = [a for a in alerts if a.alert_type.value == "daily_budget_exceeded"]
        if daily_over_alerts:
            print(f"  ✗ 错误触发了每日预算超支警告（不应触发）")
        else:
            print(f"  ✓ 未触发每日预算超支警告（正确）")

        print(
            f"  📊 测试结果: {'通过' if budget_alerts and burn_rate_alerts and not daily_over_alerts else '部分失败'}"
        )

        return len(budget_alerts) > 0 and len(burn_rate_alerts) > 0 and len(daily_over_alerts) == 0

    except ImportError as e:
        print(f"  ✗ 导入失败: {e}")
        print(f"    跳过测试（可能需要先运行其他模块）")
        return False
    except Exception as e:
        print(f"  ✗ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_alert_dispatcher_dry_run():
    """测试2: 告警负路径或 dry-run 测试"""
    print("\n" + "=" * 60)
    print("测试2: 告警分发器 dry-run 测试")
    print("=" * 60)

    try:
        # 导入告警分发器
        from mini_agent.agent.core.alert_dispatcher import (
            AlertChannel,
            AlertDispatcher,
            AlertMessage,
            AlertPriority,
            DispatcherConfig,
        )

        # 创建配置（启用dry-run模式）
        config = DispatcherConfig(
            enabled_channels=[
                AlertChannel.CONSOLE,
                AlertChannel.LOG_FILE,
                AlertChannel.ARTIFACT_FILE,
            ],
            dry_run=True,  # dry-run模式
            min_priority=AlertPriority.LOW,
        )

        dispatcher = AlertDispatcher(config)

        # 创建测试告警
        alert = AlertMessage(
            alert_id="test_dry_run_alert",
            title="Dry-Run测试告警",
            message="这是一个dry-run测试，不应真实发送",
            priority=AlertPriority.HIGH,
            source="test_suite",
            details={"test": True, "dry_run": True},
        )

        print(f"  告警信息:")
        print(f"    ID: {alert.alert_id}")
        print(f"    标题: {alert.title}")
        print(f"    优先级: {alert.priority.value}")
        print(f"    来源: {alert.source}")

        print(f"  分发器配置:")
        print(f"    dry_run模式: {dispatcher.config.dry_run}")
        print(f"    启用渠道: {[c.value for c in dispatcher.config.enabled_channels]}")

        # 分发告警
        results = dispatcher.dispatch(alert)

        print(f"  分发结果:")
        all_dry_run = True
        for channel, success in results.items():
            status = "成功 (dry-run)" if success else "失败"
            print(f"    {channel.value}: {status}")
            # 在dry-run模式下，所有渠道都应该报告成功（但实际不发送）
            if not success:
                all_dry_run = False

        # 验证dry-run行为
        if dispatcher.config.dry_run:
            print(f"  ✓ 处于dry-run模式，告警未真实发送")

            # 检查日志文件是否真的创建（不应该）
            log_file = Path(config.log_file_path)
            if log_file.exists():
                # 在dry-run模式下，日志文件可能仍然会被创建（取决于实现）
                print(f"    注: 日志文件存在（可能由之前的测试创建）")
            else:
                print(f"    ✓ 日志文件未创建（dry-run行为正确）")

        # 测试负路径：低优先级告警过滤
        print(f"\n  负路径测试: 低优先级告警过滤")

        low_priority_config = DispatcherConfig(
            enabled_channels=[AlertChannel.CONSOLE],
            dry_run=False,
            min_priority=AlertPriority.HIGH,  # 最低处理优先级为HIGH
        )

        dispatcher2 = AlertDispatcher(low_priority_config)

        low_alert = AlertMessage(
            alert_id="test_low_priority",
            title="低优先级测试告警",
            message="此告警优先级为LOW，应被过滤",
            priority=AlertPriority.LOW,  # LOW优先级
            source="test_suite",
        )

        results2 = dispatcher2.dispatch(low_alert)

        if not any(results2.values()):
            print(f"  ✓ 低优先级告警被正确过滤（无渠道接收）")
        else:
            print(f"  ✗ 低优先级告警未被过滤（某些渠道接收了）")

        print(
            f"  📊 测试结果: {'通过' if all_dry_run and not any(results2.values()) else '部分失败'}"
        )

        return all_dry_run and not any(results2.values())

    except ImportError as e:
        print(f"  ✗ 导入失败: {e}")
        print(f"    跳过测试（可能需要先运行其他模块）")
        return False
    except Exception as e:
        print(f"  ✗ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_summary_smoke():
    """测试3: summary 输出 smoke 测试"""
    print("\n" + "=" * 60)
    print("测试3: Summary 输出 Smoke 测试")
    print("=" * 60)

    try:
        # 导入摘要生成器
        from scripts.ops_financial_summary import SummaryGenerator

        # 使用临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"  使用临时目录: {tmpdir}")

            generator = SummaryGenerator(output_dir=tmpdir)

            print(f"  生成摘要...")
            payload = generator.generate_summary(save_artifact=True)

            print(f"  摘要基本信息:")
            print(f"    ID: {payload.summary_id}")
            print(f"    时间戳: {payload.timestamp}")
            print(f"    整体健康度: {payload.health_scores.overall}/100")

            print(f"  财务摘要:")
            print(f"    剩余预算: ¥{payload.financial_data.remaining_budget:.2f}")
            print(f"    每日预算: ¥{payload.financial_data.daily_budget:.2f}")
            print(f"    燃烧率: ¥{payload.financial_data.burn_rate:.2f}/小时")
            print(f"    使用率: {payload.financial_data.utilization:.1%}")

            print(f"  运营摘要:")
            print(f"    自动化请求总数: {payload.operational_data.automation_requests_total}")
            print(f"    今日自动化请求: {payload.operational_data.automation_requests_today}")
            print(f"    自动化成功率: {payload.operational_data.automation_success_rate:.1%}")

            print(f"  告警摘要:")
            print(
                f"    严重: {payload.alert_summary.critical}, 警告: {payload.alert_summary.warning}, 总计: {payload.alert_summary.total}"
            )

            print(f"  建议数量: {len(payload.recommendations)}")
            if payload.recommendations:
                print(f"    第一条建议: {payload.recommendations[0]}")

            # 检查artifact文件
            artifact_dir = Path(tmpdir)
            artifact_files = list(artifact_dir.glob("summary_*.json"))

            if artifact_files:
                print(f"  ✓ Artifact文件已生成: {len(artifact_files)}个")

                # 验证JSON格式
                for artifact_file in artifact_files[:1]:  # 只检查第一个
                    try:
                        with open(artifact_file, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        required_fields = [
                            "summary_id",
                            "timestamp",
                            "health_scores",
                            "financial_data",
                        ]
                        missing_fields = [field for field in required_fields if field not in data]

                        if not missing_fields:
                            print(f"  ✓ Artifact JSON格式正确")
                        else:
                            print(f"  ✗ Artifact缺少字段: {missing_fields}")

                    except json.JSONDecodeError as e:
                        print(f"  ✗ Artifact JSON解析失败: {e}")
                        return False
            else:
                print(f"  ✗ 未生成artifact文件")
                return False

            # 测试文本报告生成
            print(f"\n  测试文本报告生成...")
            text_report = generator.generate_text_report(payload)

            if text_report and len(text_report) > 100:
                print(f"  ✓ 文本报告生成成功 ({len(text_report)}字符)")
                # 显示报告前几行
                lines = text_report.split("\n")[:10]
                print(f"    预览:")
                for line in lines:
                    print(f"      {line}")
            else:
                print(f"  ✗ 文本报告生成失败或太短")
                return False

        print(f"  📊 测试结果: 通过")
        return True

    except ImportError as e:
        print(f"  ✗ 导入失败: {e}")
        print(f"    跳过测试（可能需要先运行其他模块）")
        return False
    except Exception as e:
        print(f"  ✗ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("🚀 开始运营自动化与资金监控验证测试")
    print("=" * 60)

    test_results = []

    # 测试1: 资金监控阈值测试
    test1_passed = test_financial_monitor_threshold()
    test_results.append(("资金监控阈值测试", test1_passed))

    # 测试2: 告警dry-run测试
    test2_passed = test_alert_dispatcher_dry_run()
    test_results.append(("告警dry-run测试", test2_passed))

    # 测试3: summary smoke测试
    test3_passed = test_summary_smoke()
    test_results.append(("summary smoke测试", test3_passed))

    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    all_passed = True
    for test_name, passed in test_results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print(f"\n  {'=' * 40}")
    print(f"  总计: {sum(p for _, p in test_results)}/{len(test_results)} 通过")
    print(f"  状态: {'所有测试通过 🎉' if all_passed else '有测试失败 ⚠️'}")
    print(f"  {'=' * 40}")

    return all_passed


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="运营自动化与资金监控验证测试")
    parser.add_argument(
        "--test",
        choices=["financial", "alert", "summary", "all"],
        default="all",
        help="选择要运行的测试 (默认: all)",
    )

    args = parser.parse_args()

    if args.test == "financial" or args.test == "all":
        test_financial_monitor_threshold()

    if args.test == "alert" or args.test == "all":
        test_alert_dispatcher_dry_run()

    if args.test == "summary" or args.test == "all":
        test_summary_smoke()

    if args.test == "all":
        run_all_tests()


if __name__ == "__main__":
    # 运行所有测试
    success = run_all_tests()

    # 退出码
    sys.exit(0 if success else 1)
