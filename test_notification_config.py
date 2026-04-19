#!/usr/bin/env python3
"""
测试通知系统配置

这个脚本验证通知系统的配置加载和函数可用性，
不实际发送邮件或Slack消息。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

from monitor_queue_health import _filter_alerts_by_policy, _merge_env_vars_into_config


def test_config_merging():
    """测试环境变量合并到配置"""
    print("🔧 测试配置合并...")

    # 模拟配置
    config = {"email": {"smtp_server": "config.example.com"}, "slack": {}}  # 配置文件中已有的值

    # 设置测试环境变量
    os.environ["OPENCLAW_SMTP_SERVER"] = "env.example.com"  # 应被忽略（配置优先级高）
    os.environ["OPENCLAW_SMTP_PORT"] = "587"
    os.environ["OPENCLAW_SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/services/test"

    # 合并配置
    merged = _merge_env_vars_into_config(config)

    # 验证结果
    assert merged["email"]["smtp_server"] == "config.example.com", "配置优先级错误"
    assert merged["email"]["smtp_port"] == 587, "环境变量未正确转换"
    assert (
        merged["slack"]["webhook_url"] == "https://hooks.slack.com/services/test"
    ), "Slack配置未加载"

    print("✅ 配置合并测试通过")

    # 清理环境变量
    del os.environ["OPENCLAW_SMTP_SERVER"]
    del os.environ["OPENCLAW_SMTP_PORT"]
    del os.environ["OPENCLAW_SLACK_WEBHOOK_URL"]

    return True


def test_alert_filtering():
    """测试告警过滤策略"""
    print("🔧 测试告警过滤策略...")

    # 测试告警
    test_alerts = [
        {"level": "critical", "title": "测试严重告警", "message": "测试"},
        {"level": "warning", "title": "测试警告告警", "message": "测试"},
        {"level": "info", "title": "测试信息告警", "message": "测试"},
    ]

    # 测试配置
    config = {
        "notification_strategy": {
            "send_email_for": ["critical", "warning"],
            "working_hours_start": 9,
            "working_hours_end": 18,
            "after_hours_critical_only": True,
        }
    }

    # 模拟不同时间
    test_hours = [
        (10, True, 2),  # 工作时间10点，应过滤出2个告警（critical, warning）
        (20, True, 1),  # 非工作时间20点，只发送critical
        (10, False, 3),  # 如果策略允许所有级别，应过滤出3个
    ]

    for hour, is_critical_only, expected_count in test_hours:
        # 模拟当前时间
        original_datetime = datetime

        class MockDatetime:
            @property
            def now(self):
                class Now:
                    hour = hour

                return Now()

        # 临时替换datetime
        import monitor_queue_health

        original_now = monitor_queue_health.datetime.now
        monitor_queue_health.datetime.now = lambda: MockDatetime().now

        # 修改配置
        test_config = config.copy()
        if not is_critical_only:
            test_config["notification_strategy"]["send_email_for"] = ["critical", "warning", "info"]

        # 过滤告警
        filtered = _filter_alerts_by_policy(test_alerts, test_config)

        print(
            f"  时间{hour:02d}:00，策略critical_only={is_critical_only}，过滤后{len(filtered)}/{expected_count}"
        )
        assert (
            len(filtered) == expected_count
        ), f"过滤结果不正确：期望{expected_count}，实际{len(filtered)}"

        # 恢复datetime
        monitor_queue_health.datetime.now = original_now

    print("✅ 告警过滤测试通过")
    return True


def test_email_function_structure():
    """测试邮件函数结构（不实际发送）"""
    print("🔧 测试邮件函数结构...")

    try:
        from monitor_queue_health import _send_email_notification

        # 创建测试配置（缺少必要字段，应跳过发送）
        config = {"email": {"smtp_server": "test"}}  # 不完整配置

        # 这应该不会抛出异常，只是打印警告
        _send_email_notification([], config)

        print("✅ 邮件函数结构测试通过")
        return True
    except Exception as e:
        print(f"❌ 邮件函数结构测试失败: {e}")
        return False


def test_slack_function_structure():
    """测试Slack函数结构（不实际发送）"""
    print("🔧 测试Slack函数结构...")

    try:
        from monitor_queue_health import _send_slack_notification

        # 创建测试配置（缺少必要字段，应跳过发送）
        config = {"slack": {}}  # 不完整配置

        # 这应该不会抛出异常，只是打印警告
        _send_slack_notification([], config)

        print("✅ Slack函数结构测试通过")
        return True
    except Exception as e:
        print(f"❌ Slack函数结构测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始通知系统配置测试")
    print("=" * 50)

    tests = [
        test_config_merging,
        test_alert_filtering,
        test_email_function_structure,
        test_slack_function_structure,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            import traceback

            traceback.print_exc()
            results.append(False)

    print("\n" + "=" * 50)
    print("📊 测试结果摘要:")

    for i, (test, result) in enumerate(zip(tests, results), 1):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {i}. {test.__name__}: {status}")

    all_passed = all(results)
    if all_passed:
        print("\n🎉 所有测试通过！通知系统配置正确。")
        print("\n下一步:")
        print("  1. 填写 .env 文件中的实际凭据")
        print("  2. 运行 monitor_queue_health.py 测试实际通知")
        print(
            '  3. 或运行 python3 -c "from monitor_queue_health import send_notifications; '
            "send_notifications([{'level':'critical','title':'测试','message':'测试'}], "
            "'.openclaw/maref/config/config.yaml')\""
        )
    else:
        print(f"\n⚠️  {results.count(False)}/{len(results)} 个测试失败")
        print("  请检查 monitor_queue_health.py 中的实现")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
