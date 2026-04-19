#!/usr/bin/env python3
"""测试健康度计算器与监控系统的集成"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from datetime import datetime


def test_health_calculator_basic():
    """测试健康度计算器基础功能"""
    print("=== 测试健康度计算器基础功能 ===")

    from health_calculator import AgentHealthCalculator

    # 创建计算器
    calculator = AgentHealthCalculator()
    print("✅ 健康度计算器创建成功")

    # 测试优秀指标
    excellent_metrics = {
        "response_time": 0.05,
        "success_rate": 0.995,
        "resource_usage": 0.25,
        "availability": 0.999,
    }

    score = calculator.calculate_health(excellent_metrics)
    print(f"优秀指标健康度: {score:.3f} (期望 >0.9)")
    assert score > 0.9, f"优秀指标分数过低: {score}"

    # 测试一般指标
    average_metrics = {
        "response_time": 0.7,
        "success_rate": 0.92,
        "resource_usage": 0.65,
        "availability": 0.97,
    }

    score = calculator.calculate_health(average_metrics)
    print(f"一般指标健康度: {score:.3f} (期望 ~0.6-0.7)")
    assert 0.5 <= score <= 0.8, f"一般指标分数异常: {score}"

    # 测试差指标
    poor_metrics = {
        "response_time": 3.0,
        "success_rate": 0.75,
        "resource_usage": 0.95,
        "availability": 0.85,
    }

    score = calculator.calculate_health(poor_metrics)
    print(f"差指标健康度: {score:.3f} (期望 <0.4)")
    assert score < 0.4, f"差指标分数过高: {score}"

    print("✅ 健康度计算器基础测试通过")
    return True


def test_monitor_integration():
    """测试监控器集成"""
    print("\n=== 测试监控器集成 ===")

    from maref_monitor import MAREFMonitor

    # 模拟智能体类
    class TestAgent:
        def __init__(self, agent_id, agent_type, has_health_method=True):
            self.agent_id = agent_id
            self.agent_type = agent_type
            self.has_health_method = has_health_method

        def get_health_metrics(self):
            if not self.has_health_method:
                raise AttributeError("No get_health_metrics")
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "status": "active",
                "response_time": 0.3,
                "success_rate": 0.98,
                "resource_usage": 0.4,
                "availability": 0.995,
                "last_active": datetime.now().isoformat(),
            }

    class SimpleAgent:
        """没有get_health_metrics方法的智能体"""

        def __init__(self, agent_id, agent_type):
            self.agent_id = agent_id
            self.agent_type = agent_type

    # 创建智能体字典
    agents = {
        "advanced_agent": TestAgent("advanced_001", "advanced"),
        "simple_agent": SimpleAgent("simple_001", "simple"),
        "no_method_agent": TestAgent("no_method_001", "no_method", has_health_method=False),
    }

    # 创建监控器（无状态管理器）
    monitor = MAREFMonitor(agents=agents)
    print("✅ 监控器创建成功")

    # 检查健康度计算器是否初始化
    if monitor.health_calculator is None:
        print("⚠️  健康度计算器未初始化，检查导入问题")
    else:
        print("✅ 健康度计算器已初始化")

    # 收集智能体指标
    agent_metrics = monitor.collect_agent_metrics()
    print(f"收集到 {len(agent_metrics)} 个智能体指标")

    # 验证每个智能体的指标
    for agent_name, metrics in agent_metrics.items():
        print(f"\n  {agent_name}:")
        print(f"    状态: {metrics.get('status', 'unknown')}")
        print(f"    健康分数: {metrics.get('health_score', 'N/A')}")

        # 对于错误状态的智能体，可能没有health_score
        if metrics.get("status") == "error":
            print(f"    ⚠️  错误状态智能体，跳过健康分数验证")
            continue

        # 验证健康分数存在
        if "health_score" not in metrics:
            print(f"    ❌ 缺少health_score字段")
            return False

        # 验证健康分数在合理范围内
        score = metrics["health_score"]
        if not isinstance(score, (int, float)):
            print(f"    ❌ health_score不是数值: {type(score)}")
            return False

        if not 0.0 <= score <= 1.0:
            print(f"    ❌ health_score超出范围: {score}")
            return False

        # 对于advanced_agent，验证健康分数计算正确（应该是0.8）
        if agent_name == "advanced_agent":
            expected_score = 0.8  # 根据健康度计算器阈值
            if abs(score - expected_score) > 0.01:
                print(f"    ❌ advanced_agent健康分数异常: 期望~{expected_score}, 实际{score}")
                return False
            else:
                print(f"    ✅ advanced_agent健康分数正确: {score:.3f}")
        else:
            print(f"    ✅ 健康分数验证通过: {score:.3f}")

    print("✅ 监控器集成测试通过")
    return True


def test_health_score_calculation():
    """测试健康分数计算逻辑"""
    print("\n=== 测试健康分数计算逻辑 ===")

    from health_calculator import AgentHealthCalculator
    from maref_monitor import MAREFMonitor

    # 创建计算器用于验证
    calculator = AgentHealthCalculator()

    # 模拟带完整指标的智能体
    class MetricAgent:
        def __init__(self, agent_id):
            self.agent_id = agent_id
            self.agent_type = "metric_tester"

        def get_health_metrics(self):
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "response_time": 0.15,
                "success_rate": 0.97,
                "resource_usage": 0.35,
                "availability": 0.998,
                "status": "active",
            }

    # 创建监控器和智能体
    agent = MetricAgent("metric_test_001")
    monitor = MAREFMonitor(agents={"metric_agent": agent})

    # 收集指标
    metrics = monitor.collect_agent_metrics()
    agent_metrics = metrics.get("metric_agent", {})

    if not agent_metrics:
        print("❌ 未收集到智能体指标")
        return False

    # 验证健康分数
    monitor_score = agent_metrics.get("health_score", None)
    if monitor_score is None:
        print("❌ 监控器未计算健康分数")
        return False

    # 独立计算验证
    health_metrics = {
        "response_time": 0.15,
        "success_rate": 0.97,
        "resource_usage": 0.35,
        "availability": 0.998,
    }
    expected_score = calculator.calculate_health(health_metrics)

    print(f"监控器计算分数: {monitor_score:.3f}")
    print(f"独立计算分数: {expected_score:.3f}")

    # 允许微小误差
    if abs(monitor_score - expected_score) < 0.01:
        print("✅ 健康分数计算正确")
        return True
    else:
        print(f"❌ 分数不匹配: 差值 {abs(monitor_score - expected_score):.3f}")
        return False


def main():
    """主测试函数"""
    print("开始测试健康度计算器与监控系统集成")

    tests = [
        ("健康度计算器基础功能", test_health_calculator_basic),
        ("监控器集成", test_monitor_integration),
        ("健康分数计算逻辑", test_health_score_calculation),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*50}")
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ 测试 {test_name} 异常: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # 汇总结果
    print(f"\n{'='*50}")
    print("测试结果汇总:")
    all_passed = True
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not success:
            all_passed = False

    if all_passed:
        print("\n🎉 所有测试通过！健康度计算器集成成功")
    else:
        print("\n❌ 部分测试失败，请检查集成问题")
        sys.exit(1)


if __name__ == "__main__":
    main()
