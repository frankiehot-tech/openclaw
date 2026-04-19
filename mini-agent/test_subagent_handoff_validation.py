#!/usr/bin/env python3
"""
测试 SubAgent 交接结构化产出验证
验证产出是否符合角色产出契约
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from agent.core.sub_agent_bus import AgentRole, SubAgentBus
from agent.core.subagent_registry import SubAgentRole, get_registry


def test_output_schema_validation():
    """测试产出契约验证"""
    print("=== SubAgent 产出契约验证测试 ===")

    registry = get_registry()

    # 测试用例：角色 -> 有效产出数据
    positive_test_cases = [
        # 规划者
        (
            SubAgentRole.PLANNER.value,
            {
                "plan": "实现新的用户认证系统",
                "tasks": [
                    {"id": "task1", "description": "设计数据库表结构"},
                    {"id": "task2", "description": "实现认证API端点"},
                ],
                "dependencies": [{"from": "task2", "to": "task1"}],
                "acceptance_criteria": ["支持OAuth2", "支持多因素认证"],
                "estimated_time": 40,
                "risks": ["第三方服务不可用", "安全漏洞"],
            },
        ),
        # 最小有效数据
        (
            SubAgentRole.PLANNER.value,
            {
                "plan": "测试计划",
                "tasks": [],
            },
        ),
        # 研究者
        (
            SubAgentRole.RESEARCHER.value,
            {
                "research_topic": "最新前端框架比较",
                "findings": ["React 18 支持并发渲染", "Vue 3 性能提升 40%"],
                "sources": ["官方文档", "基准测试报告"],
                "confidence_score": 0.8,
                "recommendations": ["推荐 React 用于大型应用", "推荐 Vue 用于快速原型"],
            },
        ),
        (
            SubAgentRole.RESEARCHER.value,
            {
                "research_topic": "简单研究",
                "findings": ["发现1", "发现2"],
            },
        ),
        # 构建者
        (
            SubAgentRole.BUILD_WORKER.value,
            {
                "component": "用户认证模块",
                "build_status": "成功",
                "artifacts": ["auth_service.js", "auth_middleware.js"],
                "tests_passed": True,
                "code_coverage": 0.85,
                "warnings": ["未使用的变量"],
            },
        ),
        (
            SubAgentRole.BUILD_WORKER.value,
            {
                "component": "测试组件",
                "build_status": "进行中",
            },
        ),
        # 审查者
        (
            SubAgentRole.REVIEWER.value,
            {
                "review_target": "用户认证模块代码审查",
                "review_status": "完成",
                "findings": ["代码风格不一致", "缺少错误处理"],
                "issues_found": 5,
                "critical_issues": 1,
                "recommendations": ["添加输入验证", "改进错误消息"],
                "approval": True,
            },
        ),
        (
            SubAgentRole.REVIEWER.value,
            {
                "review_target": "简单审查",
                "review_status": "通过",
            },
        ),
        # 验证者
        (
            SubAgentRole.VALIDATOR.value,
            {
                "validation_target": "用户认证模块验收测试",
                "validation_status": "通过",
                "test_cases": 20,
                "passed_cases": 20,
                "coverage": 0.95,
                "passed": True,
                "failures": [],
                "evidence": ["test_report.md", "coverage_report.html"],
            },
        ),
        (
            SubAgentRole.VALIDATOR.value,
            {
                "validation_target": "简单验证",
                "validation_status": "失败",
                "passed": False,
            },
        ),
    ]

    print(f"\n1. 执行 {len(positive_test_cases)} 个正面测试用例（有效数据）")

    positive_passed = 0
    positive_failed = []

    for role_id, output_data in positive_test_cases:
        valid, errors = registry.validate_output_schema(role_id, output_data)

        print(f"\n  测试: {role_id}")
        print(f"    数据: {list(output_data.keys())}")
        print(f"    有效: {valid}")

        if valid:
            print(f"    ✅ 产出验证通过")
            positive_passed += 1
        else:
            print(f"    ❌ 产出验证失败: {errors}")
            positive_failed.append((role_id, output_data, errors))

    # 负面测试：缺少必需字段
    print(f"\n2. 执行负面测试用例（无效数据）")

    negative_test_cases = [
        # 规划者缺少必需字段
        (
            SubAgentRole.PLANNER.value,
            {
                "plan": "只有计划，没有任务"
                # 缺少 "tasks"
            },
            "缺少必需字段: tasks",
        ),
        # 研究者缺少必需字段
        (
            SubAgentRole.RESEARCHER.value,
            {
                "findings": ["发现1"]
                # 缺少 "research_topic"
            },
            "缺少必需字段: research_topic",
        ),
        # 构建者缺少必需字段
        (
            SubAgentRole.BUILD_WORKER.value,
            {
                "component": "测试组件"
                # 缺少 "build_status"
            },
            "缺少必需字段: build_status",
        ),
        # 空数据
        (SubAgentRole.REVIEWER.value, {}, "缺少必需字段: review_target"),
        # 角色不存在
        ("nonexistent_role", {"test": "data"}, "角色不存在: nonexistent_role"),
    ]

    negative_passed = 0
    negative_failed = []

    for role_id, output_data, expected_error in negative_test_cases:
        valid, errors = registry.validate_output_schema(role_id, output_data)

        print(f"\n  测试: {role_id} (负面)")
        print(f"    数据: {list(output_data.keys())}")
        print(f"    有效: {valid}")
        print(f"    错误: {errors}")

        if not valid and errors:
            # 检查是否包含预期错误
            error_match = False
            for error in errors:
                if expected_error in error:
                    error_match = True
                    break

            if error_match:
                print(f"    ✅ 正确拒绝无效产出")
                negative_passed += 1
            else:
                print(f"    ❌ 错误不匹配，预期包含: {expected_error}")
                negative_failed.append((role_id, output_data, errors, expected_error))
        else:
            print(f"    ❌ 无效产出未被拒绝")
            negative_failed.append((role_id, output_data, errors, expected_error))

    # 结果汇总
    print(f"\n" + "=" * 60)
    print(f"正面测试: 通过 {positive_passed}/{len(positive_test_cases)}")
    print(f"负面测试: 通过 {negative_passed}/{len(negative_test_cases)}")

    all_failed = positive_failed + negative_failed

    if all_failed:
        print(f"\n❌ 失败的测试用例:")
        for test_case in all_failed:
            if len(test_case) == 3:
                role_id, output_data, errors = test_case
                print(f"  - {role_id}: {errors}")
            else:
                role_id, output_data, errors, expected_error = test_case
                print(f"  - {role_id}: 预期 '{expected_error}'，实际 {errors}")
        raise AssertionError(f"{len(all_failed)} 个产出验证测试失败")
    else:
        print(f"\n✅ 所有产出契约验证测试通过！")
        return True


def test_subagent_bus_integration():
    """测试 SubAgentBus 集成验证"""
    print(f"\n=== SubAgentBus 集成验证测试 ===")

    # 创建 SubAgentBus 实例
    bus = SubAgentBus(max_workers=1)

    # 测试工具边界检查集成
    print(f"\n1. 测试工具边界检查集成")

    # 规划者尝试使用 bash 工具（应被拒绝）
    print(f"   测试规划者使用 bash 工具:")
    guardrail_result = bus.check_tool_guardrail(AgentRole.PLANNER, "bash")
    allowed = guardrail_result.get("allowed", True)

    if not allowed:
        print(f"    ✅ SubAgentBus 正确拒绝规划者使用 bash")
    else:
        print(f"    ❌ SubAgentBus 未拒绝规划者使用 bash")
        raise AssertionError("SubAgentBus 工具边界检查失败")

    # 构建者尝试使用 bash 工具（应允许）
    print(f"\n   测试构建者使用 bash 工具:")
    guardrail_result = bus.check_tool_guardrail(AgentRole.BUILD_WORKER, "bash")
    allowed = guardrail_result.get("allowed", False)

    if allowed:
        print(f"    ✅ SubAgentBus 正确允许构建者使用 bash")
    else:
        print(f"    ❌ SubAgentBus 未允许构建者使用 bash")
        raise AssertionError("SubAgentBus 工具边界检查失败（构建者）")

    # 测试产出验证集成
    print(f"\n2. 测试产出验证集成")

    # 有效产出数据
    valid_output = {
        "plan": "测试计划",
        "tasks": [{"id": "task1", "description": "测试任务"}],
    }

    valid, errors = bus.validate_output_schema(AgentRole.PLANNER, valid_output)

    if valid:
        print(f"    ✅ SubAgentBus 正确验证有效产出")
    else:
        print(f"    ❌ SubAgentBus 错误拒绝有效产出: {errors}")
        raise AssertionError("SubAgentBus 产出验证失败（有效数据）")

    # 无效产出数据（缺少必需字段）
    invalid_output = {
        "plan": "测试计划",
        # 缺少 "tasks"
    }

    valid, errors = bus.validate_output_schema(AgentRole.PLANNER, invalid_output)

    if not valid and errors:
        print(f"    ✅ SubAgentBus 正确拒绝无效产出: {errors}")
    else:
        print(f"    ❌ SubAgentBus 未拒绝无效产出")
        raise AssertionError("SubAgentBus 产出验证失败（无效数据）")

    # 测试角色映射
    print(f"\n3. 测试角色映射功能")

    registry = get_registry()

    stage_role_mapping = [
        ("plan", "planner"),
        ("build", "build_worker"),
        ("review", "reviewer"),
        ("think", "researcher"),
        ("qa", "validator"),
        ("browse", "researcher"),
        ("unknown", None),  # 不支持阶段
    ]

    for stage, expected_role in stage_role_mapping:
        mapped_role = registry.map_stage_to_role(stage)

        print(f"   阶段 '{stage}' -> 角色 '{mapped_role}'")

        if mapped_role == expected_role:
            print(f"      ✅ 映射正确")
        else:
            print(f"      ❌ 映射错误，预期 '{expected_role}'")
            raise AssertionError(f"阶段映射错误: {stage}")

    print(f"\n✅ SubAgentBus 集成验证测试通过")
    return True


def test_handoff_chain():
    """测试交接链条验证"""
    print(f"\n=== 交接链条验证测试 ===")

    registry = get_registry()

    # 模拟一个简单的交接链条：规划者 -> 研究者 -> 构建者 -> 审查者 -> 验证者
    handoff_chain = [
        (SubAgentRole.PLANNER.value, "planner_output.json"),
        (SubAgentRole.RESEARCHER.value, "research_output.json"),
        (SubAgentRole.BUILD_WORKER.value, "build_output.json"),
        (SubAgentRole.REVIEWER.value, "review_output.json"),
        (SubAgentRole.VALIDATOR.value, "validation_output.json"),
    ]

    print(f"\n模拟交接链条: {' -> '.join(role for role, _ in handoff_chain)}")

    # 验证每个角色都有对应的产出契约
    for role_id, _ in handoff_chain:
        role_def = registry.get_role(role_id)
        if not role_def:
            print(f"❌ 角色 {role_id} 不存在于注册表中")
            raise AssertionError(f"角色 {role_id} 不存在")

        required_fields = role_def.required_output_fields
        print(f"  {role_id}: 必需字段 {required_fields}")

        # 检查必需字段非空
        if not required_fields:
            print(f"  ⚠ 角色 {role_id} 没有必需字段定义")

    # 模拟一个完整的交接场景
    print(f"\n模拟完整交接场景:")

    # 1. 规划者产出
    planner_output = {
        "plan": "实现新功能",
        "tasks": [{"id": "research", "description": "研究相关技术"}],
    }

    # 2. 研究者产出（基于规划者任务）
    researcher_output = {
        "research_topic": "相关技术研究",
        "findings": ["技术A适合此场景", "技术B有性能优势"],
    }

    # 3. 构建者产出（基于研究者发现）
    build_output = {
        "component": "新功能模块",
        "build_status": "成功",
    }

    # 验证每个产出
    test_outputs = [
        (SubAgentRole.PLANNER.value, planner_output),
        (SubAgentRole.RESEARCHER.value, researcher_output),
        (SubAgentRole.BUILD_WORKER.value, build_output),
    ]

    for role_id, output in test_outputs:
        valid, errors = registry.validate_output_schema(role_id, output)
        print(f"  {role_id}: {'✅ 有效' if valid else '❌ 无效'}")
        if errors:
            print(f"    错误: {errors}")

    print(f"\n✅ 交接链条验证测试完成")
    return True


def main():
    """主测试函数"""
    print("开始 SubAgent 交接结构化产出验证测试")
    print("=" * 60)

    try:
        test_output_schema_validation()
        test_subagent_bus_integration()
        test_handoff_chain()

        print("\n" + "=" * 60)
        print("🎉 所有交接验证测试通过！")
        print("\n验证结果：")
        print("1. 产出契约验证：有效数据通过，无效数据被拒绝")
        print("2. SubAgentBus 集成：工具边界检查和产出验证集成正常")
        print("3. 角色映射：工程阶段正确映射到子代理角色")
        print("4. 交接链条：角色间交接链条定义完整")

        return 0
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
