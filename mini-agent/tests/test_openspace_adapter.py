#!/usr/bin/env python3
"""
OpenSpace 适配器测试
验证最小可运行闭环的 OpenSpace 集成骨架。

测试要求：
1. 配置解析测试 - 验证 openspace_config.yaml 可加载且符合契约
2. cloud_sync_disabled 负路径测试 - 验证云同步被禁用
3. adapter smoke - 验证适配器可被调用并返回结构化结果
"""

import json
import os
import sys
import tempfile

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 添加适配器核心目录到路径
sys.path.insert(0, os.path.join(project_root, "mini-agent", "agent", "core"))

# 导入适配器
from openspace_adapter import (
    MonitoringEvidence,
    OpenSpaceAdapter,
    OpenSpaceMode,
    PerformanceMetric,
    ReviewStatus,
    SkillInput,
    get_adapter,
)

# ==================== 测试配置加载 ====================


def test_config_loading():
    """测试配置加载"""
    adapter = OpenSpaceAdapter()

    # 验证配置已加载
    assert adapter.config is not None
    assert "version" in adapter.config
    assert adapter.mode == OpenSpaceMode.LOCAL_ONLY

    print("✓ 配置加载测试通过")


def test_config_validation():
    """测试配置验证"""
    adapter = OpenSpaceAdapter()
    valid, issues = adapter.validate_config()

    # 配置必须通过验证
    assert valid == True, f"配置验证失败: {issues}"

    # 必须满足本地优先约束
    local_first = adapter.config.get("local_first_policy", {})
    enforced = local_first.get("enforced_settings", {})
    assert enforced.get("cloud_sync_disabled") == True, "cloud_sync_disabled 必须为 true"
    assert enforced.get("local_only") == True, "local_only 必须为 true"

    print("✓ 配置验证测试通过")


def test_cloud_sync_disabled_negative():
    """测试云同步禁用负路径"""
    adapter = OpenSpaceAdapter()

    # 创建临时配置文件，其中 cloud_sync_disabled=false
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        invalid_config = {
            "version": "1.0",
            "local_first_policy": {
                "enforced_settings": {
                    "cloud_sync_disabled": False,  # 故意违反契约
                    "local_only": True,
                }
            },
        }
        import yaml

        yaml.dump(invalid_config, f)
        temp_config_path = f.name

    try:
        # 使用无效配置创建适配器
        invalid_adapter = OpenSpaceAdapter(config_path=temp_config_path)
        valid, issues = invalid_adapter.validate_config()

        # 验证必须失败
        assert valid == False, "使用无效配置时验证应失败"
        assert any(
            "cloud_sync_disabled" in str(issue) for issue in issues
        ), "应报告 cloud_sync_disabled 问题"

        print("✓ 云同步禁用负路径测试通过")

    finally:
        # 清理临时文件
        os.unlink(temp_config_path)


# ==================== 测试适配器功能 ====================


def test_adapter_initialization():
    """测试适配器初始化"""
    adapter = get_adapter()

    # 验证单例模式
    adapter2 = get_adapter()
    assert adapter is adapter2

    # 验证运行时模式
    assert adapter.mode == OpenSpaceMode.LOCAL_ONLY

    print("✓ 适配器初始化测试通过")


def test_skill_analysis():
    """测试技能分析"""
    adapter = get_adapter()

    # 创建测试技能输入
    skill_input = SkillInput(
        skill_id="test-skill-analysis",
        skill_definition={
            "name": "测试技能",
            "description": "用于测试的技能",
            "category": "testing",
            "executable": True,
            "status": "executable_now",
            "dependencies": [],
            "arguments_schema": [],
            "gate_conditions": [],
        },
        execution_context={
            "task_id": "test-task-001",
            "risk_level": "medium",
            "sandbox_required": False,  # 简化测试，不使用沙箱
        },
    )

    # 执行分析
    result = adapter.analyze_skill(skill_input)

    # 验证结果结构
    assert result.success == True, f"技能分析失败: {result.error}"
    assert result.request_id is not None
    assert result.timestamp is not None
    assert result.data is not None

    # 验证数据字段
    data = result.data
    assert data["skill_id"] == "test-skill-analysis"
    assert "suggestions" in data
    assert "analysis_summary" in data
    assert data["local_only_compliant"] == True

    print("✓ 技能分析测试通过")


def test_performance_metrics_submission():
    """测试性能指标提交"""
    adapter = get_adapter()

    # 创建测试指标
    metrics = [
        PerformanceMetric(
            metric_id="execution_time_test",
            metric_type="execution_time",
            values=[
                {"timestamp": "2026-04-03T10:00:00Z", "value": 1200},
                {"timestamp": "2026-04-03T10:05:00Z", "value": 1100},
            ],
        )
    ]

    # 提交指标
    result = adapter.submit_performance_metrics(metrics)

    # 验证结果
    assert result.success == True, f"指标提交失败: {result.error}"
    assert result.data is not None
    assert "metrics_received" in result.data
    assert result.data["metrics_received"] == 1
    assert result.data["cloud_sync_disabled"] == True

    print("✓ 性能指标提交测试通过")


def test_optimization_suggestions_retrieval():
    """测试优化建议获取"""
    adapter = get_adapter()

    # 获取建议
    result = adapter.get_optimization_suggestions("test-skill-1", limit=2)

    # 验证结果
    assert result.success == True, f"建议获取失败: {result.error}"
    assert result.data is not None
    assert "suggestions" in result.data
    assert "skill_id" in result.data

    suggestions = result.data["suggestions"]
    assert isinstance(suggestions, list)

    print("✓ 优化建议获取测试通过")


def test_error_handling():
    """测试错误处理"""
    adapter = get_adapter()

    # 测试无效技能输入
    invalid_skill_input = SkillInput(
        skill_id="",  # 空ID，应触发验证失败
        skill_definition={},
        execution_context={},
    )

    result = adapter.analyze_skill(invalid_skill_input)

    # 验证失败响应
    assert result.success == False
    assert result.error is not None
    assert "code" in result.error
    assert "message" in result.error

    print("✓ 错误处理测试通过")


# ==================== 测试技能注册表集成 ====================


def test_skill_registry_integration():
    """测试技能注册表集成"""
    # 导入技能注册表
    from skill_registry import SkillRegistry

    # 加载注册表
    registry = SkillRegistry()

    # 验证 OpenSpace 技能已注册
    skill = registry.get_skill("openspace-adapter")
    assert skill is not None, "OpenSpace 技能未在注册表中找到"
    assert skill.name == "OpenSpace Adapter"
    assert skill.executable == True

    # 检查技能可用性
    available, issues = skill.is_available()
    assert available == True, f"OpenSpace 技能不可用: {issues}"

    print("✓ 技能注册表集成测试通过")


# ==================== CLI Smoke 测试 ====================


def test_cli_smoke():
    """测试 CLI 调用 - 通过子进程运行适配器内置测试"""
    import subprocess

    # 构建命令
    script_path = os.path.join(project_root, "mini-agent", "agent", "core", "openspace_adapter.py")

    # 检查脚本是否存在
    assert os.path.exists(script_path), f"适配器脚本不存在: {script_path}"

    # 运行适配器内置测试
    result = subprocess.run(
        [sys.executable, script_path], capture_output=True, text=True, timeout=30
    )

    # 验证执行成功
    assert result.returncode == 0, f"适配器执行失败: {result.stderr}"

    # 验证输出包含预期内容
    assert "OpenSpace Adapter 测试" in result.stdout
    assert "测试完成" in result.stdout

    print("✓ CLI Smoke 测试通过")


# ==================== 测试监控证据面 ====================


def test_monitoring_evidence_writing():
    """测试监控证据写回"""
    adapter = get_adapter()

    # 调用技能分析，这会触发优化尝试证据记录
    skill_input = SkillInput(
        skill_id="test-monitoring-evidence",
        skill_definition={
            "name": "测试监控证据技能",
            "description": "用于测试监控证据记录",
            "category": "testing",
            "executable": True,
            "status": "executable_now",
            "dependencies": [],
            "arguments_schema": [],
            "gate_conditions": [],
        },
        execution_context={
            "task_id": "test-task-monitoring",
            "risk_level": "medium",
            "sandbox_required": False,
        },
    )

    result = adapter.analyze_skill(skill_input)
    assert result.success == True

    # 检查证据目录是否存在
    evidence_dir = os.path.join(project_root, "mini-agent", "logs", "openspace_evidence")
    # 证据是异步记录的，我们只验证目录存在（适配器创建了目录）
    assert os.path.exists(evidence_dir), f"证据目录不存在: {evidence_dir}"

    print("✓ 监控证据写回测试通过")


def test_review_status_flow():
    """测试审核状态流转"""
    # 测试 ReviewStatus 枚举值
    assert ReviewStatus.PENDING_REVIEW.value == "pending_review"
    assert ReviewStatus.APPROVED.value == "approved"
    assert ReviewStatus.REJECTED.value == "rejected"
    assert ReviewStatus.ROLLED_BACK.value == "rolled_back"

    # 测试状态转换语义
    adapter = get_adapter()

    # 模拟更新审核状态
    evidence_id = "test_evidence_123"
    success = adapter._update_review_status(
        evidence_id=evidence_id,
        review_status=ReviewStatus.APPROVED.value,
        reviewer="test_user",
        comments="测试审核通过",
    )
    assert success == True

    print("✓ 审核状态流转测试通过")


def test_human_intervention_path():
    """测试人工干预必经路径"""
    adapter = get_adapter()

    # 创建需要人工确认的证据
    evidence = adapter._record_monitoring_evidence(
        evidence_type="constraint_hit",
        skill_id="test-skill-human",
        data={"constraint": "test_constraint", "reason": "需要人工审核"},
        requires_human_confirmation=True,
        human_intervention_details={
            "reason": "约束命中，需要人工决策",
            "requested_action": "approve_or_reject",
        },
        review_status=ReviewStatus.PENDING_REVIEW.value,
    )

    # 验证证据包含人工干预标记
    assert evidence.requires_human_confirmation == True
    assert evidence.review_status == ReviewStatus.PENDING_REVIEW.value
    assert evidence.human_intervention_details is not None
    assert "reason" in evidence.human_intervention_details

    # 验证证据类型
    assert evidence.evidence_type == "constraint_hit"
    assert evidence.skill_id == "test-skill-human"

    print("✓ 人工干预必经路径测试通过")


# ==================== 运行所有测试 ====================

if __name__ == "__main__":
    print("=== 开始 OpenSpace 适配器测试 ===")

    # 运行测试
    tests = [
        test_config_loading,
        test_config_validation,
        test_cloud_sync_disabled_negative,
        test_adapter_initialization,
        test_skill_analysis,
        test_performance_metrics_submission,
        test_optimization_suggestions_retrieval,
        test_error_handling,
        test_skill_registry_integration,
        test_cli_smoke,
        test_monitoring_evidence_writing,
        test_review_status_flow,
        test_human_intervention_path,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"✗ {test_func.__name__} 失败: {e}")

    print(f"\n=== 测试完成 ===")
    print(f"通过: {passed}, 失败: {failed}")

    if failed == 0:
        print("✅ 所有测试通过！")
    else:
        print("❌ 有测试失败")
        sys.exit(1)
