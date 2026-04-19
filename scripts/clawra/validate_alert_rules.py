#!/usr/bin/env python3
"""
告警规则验证脚本
验证告警阈值设置是否合理
"""

import sys
from pathlib import Path


def validate_alert_thresholds():
    """验证告警阈值设置"""
    # 加载配置
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from config.performance_baseline import PERFORMANCE_BASELINE
        from config.production_config import ALERT_CONFIG, PERFORMANCE_THRESHOLDS
    except ImportError as e:
        print(f"❌ 无法加载配置: {e}")
        return False

    print("=== 告警规则验证 ===\n")

    # 1. 检查告警规则配置
    print("1. 告警规则检查:")
    red_rules = ALERT_CONFIG.get("red_rules", [])
    yellow_rules = ALERT_CONFIG.get("yellow_rules", [])

    print(
        f"  红色规则 ({len(red_rules)}个): {', '.join(red_rules[:5])}{'...' if len(red_rules) > 5 else ''}"
    )
    print(
        f"  黄色规则 ({len(yellow_rules)}个): {', '.join(yellow_rules[:5])}{'...' if len(yellow_rules) > 5 else ''}"
    )

    # 2. 检查阈值配置
    thresholds = ALERT_CONFIG.get("thresholds", {})
    if not thresholds:
        print("❌ 未找到阈值配置")
        return False

    print(f"\n2. 阈值配置检查:")
    required_thresholds = [
        "cpu_usage_yellow",
        "cpu_usage_red",
        "memory_usage_yellow",
        "memory_usage_red",
        "agent_health_yellow",
        "agent_health_red",
    ]

    missing = [t for t in required_thresholds if t not in thresholds]
    if missing:
        print(f"  ❌ 缺少必要阈值: {', '.join(missing)}")
    else:
        print(f"  ✅ 所有必要阈值已配置")

    # 3. 验证阈值逻辑
    print(f"\n3. 阈值逻辑验证:")
    issues = []

    # 检查黄色阈值应低于红色阈值
    if "cpu_usage_yellow" in thresholds and "cpu_usage_red" in thresholds:
        if thresholds["cpu_usage_yellow"] >= thresholds["cpu_usage_red"]:
            issues.append("CPU使用率黄色阈值应低于红色阈值")

    if "memory_usage_yellow" in thresholds and "memory_usage_red" in thresholds:
        if thresholds["memory_usage_yellow"] >= thresholds["memory_usage_red"]:
            issues.append("内存使用率黄色阈值应低于红色阈值")

    if "agent_health_yellow" in thresholds and "agent_health_red" in thresholds:
        if thresholds["agent_health_yellow"] <= thresholds["agent_health_red"]:
            issues.append("智能体健康度黄色阈值应高于红色阈值")

    # 检查阈值是否基于基线
    baseline = PERFORMANCE_BASELINE.get("performance_thresholds", {})
    if baseline:
        print(f"  基线参考阈值: {baseline}")
        # 这里可以添加更多基于基线的验证

    if issues:
        print(f"  ⚠️  发现问题:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print(f"  ✅ 阈值逻辑正确")

    # 4. 检查通知配置
    print(f"\n4. 通知配置检查:")
    notification_channels = ALERT_CONFIG.get("notification_channels", [])
    notification_settings = ALERT_CONFIG.get("notification_settings", {})

    print(f"  通知渠道: {', '.join(notification_channels)}")
    if "email" in notification_channels and not notification_settings.get("email_recipients"):
        print(f"  ⚠️  邮件通知已启用但未配置收件人")
    if "webhook" in notification_channels and not notification_settings.get("webhook_url"):
        print(f"  ⚠️  Webhook通知已启用但未配置URL")

    # 5. 输出阈值详情
    print(f"\n5. 关键阈值详情:")
    print(
        f"  CPU使用率: 黄色>{thresholds.get('cpu_usage_yellow', 'N/A')}%, 红色>{thresholds.get('cpu_usage_red', 'N/A')}%"
    )
    print(
        f"  内存使用率: 黄色>{thresholds.get('memory_usage_yellow', 'N/A')}%, 红色>{thresholds.get('memory_usage_red', 'N/A')}%"
    )
    print(
        f"  智能体健康度: 黄色<{thresholds.get('agent_health_yellow', 'N/A')}, 红色<{thresholds.get('agent_health_red', 'N/A')}"
    )

    return len(issues) == 0


def main():
    try:
        success = validate_alert_thresholds()
        if success:
            print(f"\n✅ 告警规则验证通过")
            return 0
        else:
            print(f"\n❌ 告警规则验证未通过")
            return 1
    except Exception as e:
        print(f"❌ 验证过程中出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
