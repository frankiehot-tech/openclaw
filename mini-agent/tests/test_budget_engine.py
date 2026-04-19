#!/usr/bin/env python3
"""
预算引擎测试

测试 budget state 和 mode transition 功能。
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 添加 mini-agent 目录到路径
mini_agent_dir = project_root / "mini-agent"
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))

from mini_agent.agent.core.budget_engine import (
    BudgetCheckRequest,
    BudgetConfig,
    BudgetDecision,
    BudgetEngine,
    BudgetMode,
    BudgetResetPeriod,
    BudgetState,
)


class TestBudgetEngine:
    """预算引擎测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        # 创建临时目录用于测试数据库
        self.temp_dir = tempfile.mkdtemp(prefix="budget_test_")
        self.db_path = Path(self.temp_dir) / "test_budget.db"

        # 创建测试配置
        self.config = BudgetConfig(
            daily_budget=100.0,
            weekly_budget=700.0,
            monthly_budget=3000.0,
            reset_period=BudgetResetPeriod.DAILY,
            normal_threshold=0.3,
            low_threshold=0.1,
            critical_threshold=0.02,
        )

        # 初始化引擎
        self.engine = BudgetEngine(db_path=self.db_path)
        # 替换配置为测试配置
        self.engine.config = self.config

    def teardown_method(self):
        """每个测试方法后执行"""
        # 清理临时目录
        if hasattr(self, "temp_dir") and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_initial_state(self):
        """测试初始状态"""
        state = self.engine.get_state()

        assert state.date == date.today().isoformat()
        assert state.period_budget == self.config.daily_budget
        assert state.consumed == 0.0
        assert state.remaining == self.config.daily_budget
        assert state.current_mode == BudgetMode.NORMAL
        assert state.tasks_approved == 0
        assert state.tasks_rejected == 0
        assert state.tasks_degraded == 0

    def test_budget_check_normal_mode(self):
        """测试正常模式下的预算检查"""
        # 正常模式，预算充足
        request = BudgetCheckRequest(
            task_id="test_task_1",
            estimated_cost=10.0,
            task_type="general",
            description="测试任务",
        )

        result = self.engine.check_budget(request)

        assert result.decision == BudgetDecision.APPROVED
        assert result.allowed == True
        assert "预算充足" in result.reason

        # 预算不足
        request2 = BudgetCheckRequest(
            task_id="test_task_2",
            estimated_cost=200.0,  # 超过每日预算100
            task_type="general",
            description="高成本任务",
        )

        result2 = self.engine.check_budget(request2)

        assert result2.decision == BudgetDecision.REJECTED_INSUFFICIENT
        assert result2.allowed == False
        assert "预算不足" in result2.reason

    def test_mode_transitions(self):
        """测试模式转换"""
        state = self.engine.get_state()

        # 初始应为正常模式
        assert state.current_mode == BudgetMode.NORMAL

        # 消费70元，使用率70%，应仍为正常模式（阈值30%）
        self.engine.record_consumption("test_1", 70.0, "general", "消费测试")
        state = self.engine.get_state()
        assert state.current_mode == BudgetMode.NORMAL

        # 再消费25元，总消费95元，使用率95%，剩余5%，应进入低模式（阈值10%）
        self.engine.record_consumption("test_2", 25.0, "general", "更多消费")
        state = self.engine.get_state()
        # 使用率95%，剩余5%，低于low_threshold(10%)，应进入CRITICAL模式
        # 实际上，根据阈值：remaining_ratio=0.05 <= low_threshold(0.1) -> CRITICAL
        # 但critical_threshold是0.02，所以是CRITICAL不是LOW
        # 让我检查逻辑：remaining_ratio <= critical_threshold(0.02) -> PAUSED
        # remaining_ratio <= low_threshold(0.1) -> CRITICAL
        # remaining_ratio <= normal_threshold(0.3) -> LOW
        # 所以95%使用率，剩余5% -> CRITICAL
        assert state.current_mode == BudgetMode.CRITICAL

        # 再消费3元，总消费98元，剩余2%，应进入暂停模式
        self.engine.record_consumption("test_3", 3.0, "general", "临界消费")
        state = self.engine.get_state()
        # 剩余2%，等于critical_threshold(0.02)，应进入PAUSED
        assert state.current_mode == BudgetMode.PAUSED

    def test_low_mode_degradation(self):
        """测试低模式下的降级行为"""
        # 先消费到低模式
        self.engine.record_consumption("setup", 80.0, "general", "设置低模式")

        # 检查非必要任务
        request = BudgetCheckRequest(
            task_id="test_non_essential",
            estimated_cost=3.0,
            task_type="general",
            is_essential=False,
            description="非必要任务",
        )

        result = self.engine.check_budget(request)

        # 低模式下非必要任务应被拒绝
        assert result.decision == BudgetDecision.REJECTED_INSUFFICIENT
        assert result.allowed == False

        # 检查必要任务但成本过高
        request2 = BudgetCheckRequest(
            task_id="test_essential_high_cost",
            estimated_cost=8.0,  # 超过max_cost_per_task(5.0)
            task_type="maintenance",
            is_essential=True,
            description="必要但高成本",
        )

        result2 = self.engine.check_budget(request2)
        assert result2.decision == BudgetDecision.REJECTED_INSUFFICIENT
        assert result2.allowed == False

        # 检查需要审批的任务
        request3 = BudgetCheckRequest(
            task_id="test_approval_needed",
            estimated_cost=3.0,  # 超过require_approval_above(2.0)
            task_type="maintenance",
            is_essential=True,
            description="需要审批",
        )

        result3 = self.engine.check_budget(request3)
        assert result3.decision == BudgetDecision.REQUIRES_APPROVAL
        assert result3.allowed == False
        assert result3.requires_approval == True

    def test_critical_mode_restrictions(self):
        """测试临界模式限制"""
        # 先消费到临界模式
        self.engine.record_consumption("setup", 95.0, "general", "设置临界模式")

        # 检查非允许类型的任务
        request = BudgetCheckRequest(
            task_id="test_wrong_type",
            estimated_cost=0.5,
            task_type="general",  # 不在allowed_task_types中
            is_essential=False,
            description="错误类型",
        )

        result = self.engine.check_budget(request)
        assert result.decision == BudgetDecision.REJECTED_INSUFFICIENT
        assert result.allowed == False

        # 检查允许类型但需要审批
        request2 = BudgetCheckRequest(
            task_id="test_allowed_type",
            estimated_cost=0.3,
            task_type="maintenance",  # 在allowed_task_types中
            is_essential=True,
            description="允许类型",
        )

        result2 = self.engine.check_budget(request2)
        # 临界模式下，即使必要任务也可能需要审批
        # 根据配置，require_approval_above是0.5，0.3不需要审批
        # 但is_essential=True，应该允许
        assert result2.decision == BudgetDecision.APPROVED_WITH_DEGRADATION
        assert result2.allowed == True
        assert len(result2.degradation_suggestions) > 0

    def test_paused_mode_blocking(self):
        """测试暂停模式阻塞"""
        # 先消费到暂停模式
        self.engine.record_consumption("setup", 99.0, "general", "设置暂停模式")

        # 检查任何新任务
        request = BudgetCheckRequest(
            task_id="test_new_task",
            estimated_cost=0.1,
            task_type="general",
            is_essential=True,
            description="新任务",
        )

        result = self.engine.check_budget(request)
        assert result.decision == BudgetDecision.REJECTED_PAUSED
        assert result.allowed == False

        # 检查允许的任务类型（预算重置）
        request2 = BudgetCheckRequest(
            task_id="test_budget_reset",
            estimated_cost=0.0,
            task_type="budget_reset",  # 在allowed_task_types中
            is_essential=True,
            description="预算重置",
        )

        result2 = self.engine.check_budget(request2)
        # 暂停模式下，allow_new_tasks=false，但allowed_task_types中的任务需要审批
        assert result2.decision == BudgetDecision.REQUIRES_APPROVAL
        assert result2.allowed == False

    def test_structured_state(self):
        """测试结构化状态输出"""
        state = self.engine.get_structured_state()

        assert "budget_state" in state
        assert "config" in state
        assert "health" in state
        assert "statistics" in state

        budget_state = state["budget_state"]
        assert budget_state["date"] == date.today().isoformat()
        assert budget_state["current_mode"] == BudgetMode.NORMAL.value

        health = state["health"]
        assert "utilization" in health
        assert "mode" in health
        assert "days_until_reset" in health
        assert "recommendation" in health

    def test_heartbeat(self):
        """测试心跳功能"""
        heartbeat = self.engine.heartbeat()

        # 心跳应返回结构化状态
        assert "budget_state" in heartbeat
        assert "health" in heartbeat

        # 初始状态应为正常
        assert heartbeat["budget_state"]["current_mode"] == BudgetMode.NORMAL.value
        assert heartbeat["health"]["utilization"] == 0.0

    def test_daily_reset(self):
        """测试每日重置"""
        # 记录一些消费
        self.engine.record_consumption("test_1", 50.0, "general", "测试消费")

        state_before = self.engine.get_state()
        assert state_before.consumed == 50.0

        # 模拟日期变更（通过直接修改state.date）
        # 注意：这测试了内部逻辑，实际使用中日期变更会自动触发重置
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.engine.state.date = tomorrow

        # 触发重置检查
        self.engine._check_reset()

        state_after = self.engine.get_state()
        assert state_after.date == tomorrow
        assert state_after.consumed == 0.0
        assert state_after.remaining == self.config.daily_budget
        assert state_after.current_mode == BudgetMode.NORMAL

    def test_reset_budget(self):
        """测试手动重置预算"""
        # 先记录一些消费
        self.engine.record_consumption("test_consumption", 50.0, "general", "测试消费")
        state_before = self.engine.get_state()
        assert state_before.consumed == 50.0

        # 手动重置预算（不重置消费）
        reset_state = self.engine.reset_budget(new_budget=150.0, reset_consumed=False)
        assert reset_state.period_budget == 150.0
        assert reset_state.consumed == 50.0  # 消费未重置
        assert reset_state.remaining == 100.0

        # 重置消费
        reset_state2 = self.engine.reset_budget(reset_consumed=True)
        assert reset_state2.consumed == 0.0
        assert reset_state2.remaining == reset_state2.period_budget
        assert reset_state2.current_mode == BudgetMode.NORMAL

    def test_get_alerts(self):
        """测试告警输出"""
        # 正常模式下的告警
        alerts = self.engine.get_alerts()
        assert "indicators" in alerts
        assert "warnings" in alerts
        assert "alerts" in alerts
        assert "recommendations" in alerts

        indicators = alerts["indicators"]
        assert "budget_remaining" in indicators
        assert "budget_utilization" in indicators
        assert "burn_rate" in indicators
        assert "mode" in indicators

        # 消费到暂停模式并检查告警
        self.engine.record_consumption("deplete", 99.0, "general", "耗尽预算")
        alerts2 = self.engine.get_alerts()
        assert len(alerts2["alerts"]) > 0  # 应有暂停告警
        assert any(alert.get("code") == "BUDGET_PAUSED" for alert in alerts2["alerts"])


def test_budget_config_serialization():
    """测试预算配置序列化"""
    config = BudgetConfig(daily_budget=200.0, reset_period=BudgetResetPeriod.WEEKLY)

    config_dict = config.to_dict()

    assert config_dict["daily_budget"] == 200.0
    assert config_dict["reset_period"] == "weekly"
    assert "degradation_rules" in config_dict


def test_budget_state_serialization():
    """测试预算状态序列化"""
    state = BudgetState(
        date="2026-04-03",
        period_start="2026-04-03",
        period_end="2026-04-03",
        period_budget=100.0,
        consumed=30.0,
        remaining=70.0,
        burn_rate=5.0,
        current_mode=BudgetMode.NORMAL,
        mode_reason="正常状态",
        tasks_approved=5,
        tasks_rejected=2,
        tasks_degraded=1,
        total_cost=30.0,
        last_updated="2026-04-03T10:00:00",
        next_reset="2026-04-04",
    )

    state_dict = state.to_dict()

    assert state_dict["date"] == "2026-04-03"
    assert state_dict["current_mode"] == "normal"
    assert state_dict["consumed"] == 30.0
    assert state_dict["remaining"] == 70.0
    assert state_dict["utilization"] == 0.3


if __name__ == "__main__":
    """运行所有测试"""
    import pytest

    # 切换到测试目录
    os.chdir(Path(__file__).parent)

    # 运行测试
    pytest.main([__file__, "-v"])
