#!/usr/bin/env python3
"""
Budget Engine - 财务预算引擎

负责管理财务预算、四级生存模式、预算心跳和与任务执行的接线。
与现有的 provider 成本估算集成，提供基于真实成本的预算控制。

设计原则：
- 本地优先：使用 SQLite 作为状态存储，不依赖外部服务
- 最小闭环：先实现核心预算判定，再逐步扩展
- 协议优先：提供清晰的接口供其他模块调用
"""

import json
import logging
import os
import sqlite3
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== 枚举定义 ====================


class BudgetMode(Enum):
    """四级生存模式"""

    NORMAL = "normal"  # 正常模式：预算充足，全功能运行
    LOW = "low"  # 低预算模式：限制非必要任务，降级处理
    CRITICAL = "critical"  # 临界模式：仅允许核心任务，需要人工审批
    PAUSED = "paused"  # 暂停模式：停止所有新任务，仅处理维护任务


class BudgetDecision(Enum):
    """预算判定结果"""

    APPROVED = "approved"  # 批准执行
    APPROVED_WITH_DEGRADATION = "approved_with_degradation"  # 降级批准
    REJECTED_INSUFFICIENT = "rejected_insufficient"  # 预算不足拒绝
    REJECTED_PAUSED = "rejected_paused"  # 暂停模式拒绝
    REQUIRES_APPROVAL = "requires_approval"  # 需要人工审批


class BudgetResetPeriod(Enum):
    """预算重置周期"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ==================== 数据类定义 ====================


@dataclass
class BudgetConfig:
    """预算配置"""

    daily_budget: float = 100.0  # 每日预算（元）
    weekly_budget: float = 700.0  # 每周预算（元）
    monthly_budget: float = 3000.0  # 每月预算（元）
    reset_period: BudgetResetPeriod = BudgetResetPeriod.DAILY

    # 模式阈值（基于剩余预算百分比）
    normal_threshold: float = 0.3  # 30% 以下进入低模式
    low_threshold: float = 0.1  # 10% 以下进入临界模式
    critical_threshold: float = 0.02  # 2% 以下进入暂停模式

    # 降级策略
    degradation_rules: Dict[str, Any] = field(
        default_factory=lambda: {
            "low_mode": {
                "allow_non_essential": False,
                "max_cost_per_task": 5.0,
                "require_approval_above": 2.0,
            },
            "critical_mode": {
                "allow_non_essential": False,
                "max_cost_per_task": 1.0,
                "require_approval_above": 0.5,
                "allowed_task_types": ["maintenance", "critical_fix"],
            },
            "paused_mode": {
                "allow_new_tasks": False,
                "allowed_task_types": ["budget_reset", "system_maintenance"],
            },
        }
    )

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = asdict(self)
        result["reset_period"] = self.reset_period.value
        return result


@dataclass
class BudgetState:
    """预算状态"""

    date: str  # YYYY-MM-DD
    period_start: str  # 周期开始日期
    period_end: str  # 周期结束日期

    # 预算数据
    period_budget: float = 0.0
    consumed: float = 0.0
    remaining: float = 0.0
    burn_rate: float = 0.0  # 消费速率（元/小时）

    # 模式状态
    current_mode: BudgetMode = BudgetMode.NORMAL
    mode_reason: str = ""

    # 统计信息
    tasks_approved: int = 0
    tasks_rejected: int = 0
    tasks_degraded: int = 0
    total_cost: float = 0.0

    # 时间信息
    last_updated: str = ""
    next_reset: str = ""

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = asdict(self)
        result["current_mode"] = self.current_mode.value
        return result

    @property
    def utilization(self) -> float:
        """预算使用率（0.0-1.0）"""
        if self.period_budget <= 0:
            return 0.0
        return min(1.0, self.consumed / self.period_budget)


@dataclass
class BudgetCheckRequest:
    """预算检查请求"""

    task_id: str
    estimated_cost: float
    task_type: str = "general"
    is_essential: bool = False
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetCheckResult:
    """预算检查结果"""

    decision: BudgetDecision
    allowed: bool
    reason: str
    suggested_mode: Optional[BudgetMode] = None
    max_allowed_cost: Optional[float] = None
    requires_approval: bool = False
    degradation_suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = asdict(self)
        result["decision"] = self.decision.value
        if self.suggested_mode:
            result["suggested_mode"] = self.suggested_mode.value
        return result


# ==================== 核心引擎类 ====================


class BudgetEngine:
    """预算引擎"""

    def __init__(self, db_path: Optional[Path] = None, config_path: Optional[Path] = None):
        """
        初始化预算引擎

        Args:
            db_path: SQLite 数据库路径
            config_path: 配置文件路径
        """
        # 设置数据库路径
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "budget.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path

        # 加载配置
        self.config = self._load_config(config_path)

        # 初始化数据库
        self._init_database()

        # 加载或创建当前状态
        self.state = self._load_or_create_state()

        logger.info(
            f"预算引擎初始化完成，模式: {self.state.current_mode.value}, 剩余预算: {self.state.remaining:.2f}"
        )

    def _load_config(self, config_path: Optional[Path]) -> BudgetConfig:
        """加载配置"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "budget_config.yaml"

        if config_path.exists():
            try:
                import yaml

                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
                # 转换 reset_period 字符串为枚举
                if "reset_period" in config_data:
                    config_data["reset_period"] = BudgetResetPeriod(config_data["reset_period"])
                return BudgetConfig(**config_data)
            except Exception as e:
                logger.warning(f"无法加载预算配置 {config_path}: {e}")

        # 返回默认配置
        return BudgetConfig()

    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 创建预算状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budget_state (
                    date TEXT PRIMARY KEY,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    period_budget REAL NOT NULL,
                    consumed REAL NOT NULL DEFAULT 0.0,
                    remaining REAL NOT NULL,
                    burn_rate REAL NOT NULL DEFAULT 0.0,
                    current_mode TEXT NOT NULL,
                    mode_reason TEXT,
                    tasks_approved INTEGER NOT NULL DEFAULT 0,
                    tasks_rejected INTEGER NOT NULL DEFAULT 0,
                    tasks_degraded INTEGER NOT NULL DEFAULT 0,
                    total_cost REAL NOT NULL DEFAULT 0.0,
                    last_updated TEXT NOT NULL,
                    next_reset TEXT NOT NULL,
                    raw_data TEXT NOT NULL
                )
            """)

            # 创建消费记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consumption_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    cost REAL NOT NULL,
                    task_type TEXT NOT NULL,
                    description TEXT,
                    budget_state_before TEXT NOT NULL,
                    budget_state_after TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            # 创建模式变更记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mode_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    from_mode TEXT NOT NULL,
                    to_mode TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            conn.commit()

    def _load_or_create_state(self) -> BudgetState:
        """加载或创建当前预算状态"""
        today = date.today().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT raw_data FROM budget_state WHERE date = ?", (today,))
            row = cursor.fetchone()

            if row:
                # 加载现有状态
                try:
                    state_data = json.loads(row[0])
                    # 转换字符串为枚举
                    state_data["current_mode"] = BudgetMode(state_data["current_mode"])
                    return BudgetState(**state_data)
                except Exception as e:
                    logger.warning(f"无法解析存储的状态数据: {e}")

            # 创建新状态
            return self._create_new_state(today)

    def _create_new_state(self, for_date: str) -> BudgetState:
        """创建新的预算状态"""
        # 计算周期
        period_start, period_end, period_budget = self._calculate_period(for_date)

        state = BudgetState(
            date=for_date,
            period_start=period_start,
            period_end=period_end,
            period_budget=period_budget,
            consumed=0.0,
            remaining=period_budget,
            burn_rate=0.0,
            current_mode=BudgetMode.NORMAL,
            mode_reason="初始状态",
            tasks_approved=0,
            tasks_rejected=0,
            tasks_degraded=0,
            total_cost=0.0,
            last_updated=datetime.now().isoformat(),
            next_reset=period_end,
        )

        # 保存到数据库
        self._save_state(state)

        # 记录模式变更
        self._record_mode_transition(
            from_mode=None,
            to_mode=state.current_mode,
            reason="初始状态创建",
            trigger="system_init",
            state_date=state.date,
        )

        return state

    def _calculate_period(self, for_date: str) -> Tuple[str, str, float]:
        """计算预算周期"""
        today = date.fromisoformat(for_date)

        if self.config.reset_period == BudgetResetPeriod.DAILY:
            period_start = today.isoformat()
            period_end = today.isoformat()
            budget = self.config.daily_budget

        elif self.config.reset_period == BudgetResetPeriod.WEEKLY:
            # 周一开始
            weekday = today.weekday()  # 0 = Monday
            period_start = (today - timedelta(days=weekday)).isoformat()
            period_end = (today + timedelta(days=6 - weekday)).isoformat()
            budget = self.config.weekly_budget

        else:  # MONTHLY
            # 月第一天
            period_start = date(today.year, today.month, 1).isoformat()
            # 月最后一天
            if today.month == 12:
                next_month = date(today.year + 1, 1, 1)
            else:
                next_month = date(today.year, today.month + 1, 1)
            period_end = (next_month - timedelta(days=1)).isoformat()
            budget = self.config.monthly_budget

        return period_start, period_end, budget

    def _save_state(self, state: BudgetState):
        """保存状态到数据库"""
        state.last_updated = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 准备数据
            state_dict = state.to_dict()
            raw_data = json.dumps(state_dict, ensure_ascii=False)

            cursor.execute(
                """
                INSERT OR REPLACE INTO budget_state 
                (date, period_start, period_end, period_budget, consumed, remaining,
                 burn_rate, current_mode, mode_reason, tasks_approved, tasks_rejected,
                 tasks_degraded, total_cost, last_updated, next_reset, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    state.date,
                    state.period_start,
                    state.period_end,
                    state.period_budget,
                    state.consumed,
                    state.remaining,
                    state.burn_rate,
                    state.current_mode.value,
                    state.mode_reason,
                    state.tasks_approved,
                    state.tasks_rejected,
                    state.tasks_degraded,
                    state.total_cost,
                    state.last_updated,
                    state.next_reset,
                    raw_data,
                ),
            )

            conn.commit()

    def _record_consumption(
        self,
        task_id: str,
        cost: float,
        task_type: str,
        description: str,
        metadata: Dict,
    ):
        """记录消费"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 保存当前状态（消费前）
            state_before = json.dumps(self.state.to_dict(), ensure_ascii=False)

            # 更新状态
            self.state.consumed += cost
            self.state.remaining = max(0, self.state.period_budget - self.state.consumed)
            self.state.total_cost += cost
            self.state.tasks_approved += 1

            # 保存更新后的状态
            self._save_state(self.state)
            state_after = json.dumps(self.state.to_dict(), ensure_ascii=False)

            # 插入消费记录
            cursor.execute(
                """
                INSERT INTO consumption_records
                (task_id, date, timestamp, cost, task_type, description,
                 budget_state_before, budget_state_after, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    task_id,
                    self.state.date,
                    datetime.now().isoformat(),
                    cost,
                    task_type,
                    description,
                    state_before,
                    state_after,
                    json.dumps(metadata, ensure_ascii=False) if metadata else "{}",
                ),
            )

            conn.commit()

    def _record_mode_transition(
        self,
        from_mode: Optional[BudgetMode],
        to_mode: BudgetMode,
        reason: str,
        trigger: str,
        metadata: Optional[Dict] = None,
        state_date: Optional[str] = None,
    ):
        """记录模式变更"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 使用提供的state_date，否则使用self.state.date
            date_to_use = state_date if state_date is not None else self.state.date

            cursor.execute(
                """
                INSERT INTO mode_transitions
                (date, timestamp, from_mode, to_mode, reason, trigger, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    date_to_use,
                    datetime.now().isoformat(),
                    from_mode.value if from_mode else "none",
                    to_mode.value,
                    reason,
                    trigger,
                    json.dumps(metadata, ensure_ascii=False) if metadata else "{}",
                ),
            )

            conn.commit()

    def _update_mode(self, new_mode: BudgetMode, reason: str, trigger: str):
        """更新模式并记录变更"""
        if self.state.current_mode == new_mode:
            return

        old_mode = self.state.current_mode
        self.state.current_mode = new_mode
        self.state.mode_reason = reason

        logger.info(f"预算模式变更: {old_mode.value} -> {new_mode.value}, 原因: {reason}")

        # 记录变更
        self._record_mode_transition(
            from_mode=old_mode, to_mode=new_mode, reason=reason, trigger=trigger
        )

        # 保存状态
        self._save_state(self.state)

    def _evaluate_mode(self) -> BudgetMode:
        """基于当前状态评估应处的模式"""
        utilization = self.state.utilization
        remaining_ratio = 1.0 - utilization

        if remaining_ratio <= self.config.critical_threshold:
            return BudgetMode.PAUSED
        elif remaining_ratio <= self.config.low_threshold:
            return BudgetMode.CRITICAL
        elif remaining_ratio <= self.config.normal_threshold:
            return BudgetMode.LOW
        else:
            return BudgetMode.NORMAL

    def check_budget(self, request: BudgetCheckRequest) -> BudgetCheckResult:
        """
        检查预算

        Args:
            request: 预算检查请求

        Returns:
            预算检查结果
        """
        # 检查是否需要重置（跨天）
        self._check_reset()

        # 评估当前模式
        target_mode = self._evaluate_mode()
        if target_mode != self.state.current_mode:
            self._update_mode(
                target_mode,
                f"预算使用率 {self.state.utilization:.1%} 触发模式变更",
                "auto_evaluation",
            )

        # 基于模式进行判定
        if self.state.current_mode == BudgetMode.PAUSED:
            return self._handle_paused_mode(request)
        elif self.state.current_mode == BudgetMode.CRITICAL:
            return self._handle_critical_mode(request)
        elif self.state.current_mode == BudgetMode.LOW:
            return self._handle_low_mode(request)
        else:  # NORMAL
            return self._handle_normal_mode(request)

    def _handle_normal_mode(self, request: BudgetCheckRequest) -> BudgetCheckResult:
        """正常模式处理"""
        # 检查预算是否足够
        if request.estimated_cost > self.state.remaining:
            return BudgetCheckResult(
                decision=BudgetDecision.REJECTED_INSUFFICIENT,
                allowed=False,
                reason=f"预算不足：请求 {request.estimated_cost:.2f}，剩余 {self.state.remaining:.2f}",
                suggested_mode=self._evaluate_mode(),
            )

        # 正常批准
        return BudgetCheckResult(
            decision=BudgetDecision.APPROVED,
            allowed=True,
            reason=f"预算充足，批准执行",
            suggested_mode=self.state.current_mode,
        )

    def _handle_low_mode(self, request: BudgetCheckRequest) -> BudgetCheckResult:
        """低预算模式处理"""
        rules = self.config.degradation_rules["low_mode"]

        # 检查是否非必要任务
        if not request.is_essential and not rules["allow_non_essential"]:
            return BudgetCheckResult(
                decision=BudgetDecision.REJECTED_INSUFFICIENT,
                allowed=False,
                reason="低预算模式下不允许非必要任务",
                suggested_mode=self.state.current_mode,
            )

        # 检查单任务成本限制
        max_cost = rules["max_cost_per_task"]
        if request.estimated_cost > max_cost:
            return BudgetCheckResult(
                decision=BudgetDecision.REJECTED_INSUFFICIENT,
                allowed=False,
                reason=f"低预算模式下单任务成本不能超过 {max_cost:.2f}",
                suggested_mode=self.state.current_mode,
            )

        # 检查是否需要审批
        require_approval = request.estimated_cost > rules["require_approval_above"]

        if require_approval:
            return BudgetCheckResult(
                decision=BudgetDecision.REQUIRES_APPROVAL,
                allowed=False,  # 需要人工批准后才允许
                reason=f"任务成本 {request.estimated_cost:.2f} 超过审批阈值 {rules['require_approval_above']:.2f}",
                suggested_mode=self.state.current_mode,
                requires_approval=True,
            )

        # 降级批准
        return BudgetCheckResult(
            decision=BudgetDecision.APPROVED_WITH_DEGRADATION,
            allowed=True,
            reason="低预算模式下批准执行，可能有功能降级",
            suggested_mode=self.state.current_mode,
            degradation_suggestions=["限制非必要功能", "降低输出质量", "缩短执行时间"],
        )

    def _handle_critical_mode(self, request: BudgetCheckRequest) -> BudgetCheckResult:
        """临界模式处理"""
        rules = self.config.degradation_rules["critical_mode"]

        # 检查任务类型
        allowed_types = rules.get("allowed_task_types", [])
        if request.task_type not in allowed_types and not request.is_essential:
            return BudgetCheckResult(
                decision=BudgetDecision.REJECTED_INSUFFICIENT,
                allowed=False,
                reason=f"临界模式下仅允许 {allowed_types} 类型任务",
                suggested_mode=self.state.current_mode,
            )

        # 检查单任务成本限制
        max_cost = rules["max_cost_per_task"]
        if request.estimated_cost > max_cost:
            return BudgetCheckResult(
                decision=BudgetDecision.REJECTED_INSUFFICIENT,
                allowed=False,
                reason=f"临界模式下单任务成本不能超过 {max_cost:.2f}",
                suggested_mode=self.state.current_mode,
            )

        # 检查是否需要审批
        require_approval = request.estimated_cost > rules["require_approval_above"]

        if require_approval or not request.is_essential:
            return BudgetCheckResult(
                decision=BudgetDecision.REQUIRES_APPROVAL,
                allowed=False,
                reason="临界模式下需要人工审批",
                suggested_mode=self.state.current_mode,
                requires_approval=True,
            )

        # 严格降级批准
        return BudgetCheckResult(
            decision=BudgetDecision.APPROVED_WITH_DEGRADATION,
            allowed=True,
            reason="临界模式下批准核心任务执行",
            suggested_mode=self.state.current_mode,
            degradation_suggestions=["最小功能集", "最简输出", "严格时间限制"],
        )

    def _handle_paused_mode(self, request: BudgetCheckRequest) -> BudgetCheckResult:
        """暂停模式处理"""
        rules = self.config.degradation_rules["paused_mode"]

        # 检查是否允许新任务
        if not rules["allow_new_tasks"]:
            return BudgetCheckResult(
                decision=BudgetDecision.REJECTED_PAUSED,
                allowed=False,
                reason="暂停模式下不允许新任务",
                suggested_mode=self.state.current_mode,
            )

        # 检查任务类型
        allowed_types = rules.get("allowed_task_types", [])
        if request.task_type not in allowed_types:
            return BudgetCheckResult(
                decision=BudgetDecision.REJECTED_PAUSED,
                allowed=False,
                reason=f"暂停模式下仅允许 {allowed_types} 类型任务",
                suggested_mode=self.state.current_mode,
            )

        # 需要人工审批
        return BudgetCheckResult(
            decision=BudgetDecision.REQUIRES_APPROVAL,
            allowed=False,
            reason="暂停模式下需要人工审批",
            suggested_mode=self.state.current_mode,
            requires_approval=True,
        )

    def record_consumption(
        self,
        task_id: str,
        cost: float,
        task_type: str = "general",
        description: str = "",
        metadata: Optional[Dict] = None,
    ):
        """
        记录实际消费

        Args:
            task_id: 任务ID
            cost: 实际成本
            task_type: 任务类型
            description: 任务描述
            metadata: 元数据
        """
        if metadata is None:
            metadata = {}

        self._record_consumption(task_id, cost, task_type, description, metadata)

        # 重新评估模式
        target_mode = self._evaluate_mode()
        if target_mode != self.state.current_mode:
            self._update_mode(
                target_mode,
                f"消费记录后预算使用率 {self.state.utilization:.1%} 触发模式变更",
                "consumption_record",
            )

    def get_state(self) -> BudgetState:
        """获取当前预算状态"""
        self._check_reset()  # 确保状态是最新的
        return self.state

    def get_structured_state(self) -> Dict[str, Any]:
        """获取结构化状态（用于心跳）"""
        self._check_reset()

        return {
            "budget_state": self.state.to_dict(),
            "config": self.config.to_dict(),
            "health": {
                "utilization": self.state.utilization,
                "mode": self.state.current_mode.value,
                "days_until_reset": self._days_until_reset(),
                "burn_rate_trend": self._calculate_burn_rate_trend(),
                "recommendation": self._get_recommendation(),
            },
            "statistics": {
                "tasks_approved": self.state.tasks_approved,
                "tasks_rejected": self.state.tasks_rejected,
                "tasks_degraded": self.state.tasks_degraded,
                "total_cost": self.state.total_cost,
                "avg_cost_per_task": self._calculate_avg_cost(),
            },
        }

    def _check_reset(self):
        """检查是否需要重置预算"""
        today = date.today().isoformat()

        if today != self.state.date:
            logger.info(f"检测到日期变更 {self.state.date} -> {today}，重置预算状态")
            self.state = self._create_new_state(today)

    def _days_until_reset(self) -> int:
        """计算距离下次重置还有多少天"""
        try:
            reset_date = date.fromisoformat(self.state.next_reset)
            today = date.today()
            return max(0, (reset_date - today).days)
        except:
            return 0

    def _calculate_burn_rate_trend(self) -> float:
        """计算消费速率趋势（最近3小时平均）"""
        # 简化实现：返回当前 burn_rate
        return self.state.burn_rate

    def _calculate_avg_cost(self) -> float:
        """计算平均任务成本"""
        total_tasks = (
            self.state.tasks_approved + self.state.tasks_rejected + self.state.tasks_degraded
        )
        if total_tasks == 0:
            return 0.0
        return self.state.total_cost / total_tasks

    def _get_recommendation(self) -> str:
        """获取建议"""
        utilization = self.state.utilization

        if utilization >= 0.9:
            return "预算即将耗尽，建议暂停非必要任务"
        elif utilization >= 0.7:
            return "预算使用率较高，建议优化任务成本"
        elif utilization >= 0.5:
            return "预算使用率适中，保持当前节奏"
        else:
            return "预算充足，可正常执行任务"

    def reset_budget(
        self, new_budget: Optional[float] = None, reset_consumed: bool = True
    ) -> BudgetState:
        """
        手动重置预算

        Args:
            new_budget: 新的周期预算（如为None则使用当前配置预算）
            reset_consumed: 是否重置消费记录（True则消费归零）

        Returns:
            重置后的预算状态
        """
        # 检查是否需要创建新日期状态（如果日期已变更）
        self._check_reset()

        # 计算新的周期预算
        if new_budget is not None:
            self.state.period_budget = new_budget

        # 重置消费记录
        if reset_consumed:
            self.state.consumed = 0.0
            self.state.total_cost = 0.0
            self.state.tasks_approved = 0
            self.state.tasks_rejected = 0
            self.state.tasks_degraded = 0

        # 重新计算剩余预算
        self.state.remaining = max(0, self.state.period_budget - self.state.consumed)

        # 重新评估模式
        target_mode = self._evaluate_mode()
        if target_mode != self.state.current_mode:
            self._update_mode(
                target_mode,
                f"手动重置预算后预算使用率 {self.state.utilization:.1%} 触发模式变更",
                "manual_reset",
            )

        # 保存状态
        self._save_state(self.state)

        logger.info(
            f"预算已重置: 周期预算={self.state.period_budget:.2f}, 消费={self.state.consumed:.2f}, 模式={self.state.current_mode.value}"
        )
        return self.state

    def get_alerts(self) -> Dict[str, Any]:
        """
        获取预算告警

        Returns:
            结构化告警信息，包含预算剩余、burn rate、模式三类指标及警告
        """
        self._check_reset()

        alerts = {
            "indicators": {
                "budget_remaining": self.state.remaining,
                "budget_utilization": self.state.utilization,
                "burn_rate": self.state.burn_rate,
                "mode": self.state.current_mode.value,
                "days_until_reset": self._days_until_reset(),
            },
            "warnings": [],
            "alerts": [],
            "recommendations": [],
        }

        # 根据模式和使用率生成警告
        if self.state.current_mode == BudgetMode.PAUSED:
            alerts["alerts"].append(
                {
                    "level": "critical",
                    "code": "BUDGET_PAUSED",
                    "message": "预算已耗尽，系统进入暂停模式",
                    "action": "需要手动重置预算或等待周期重置",
                    "details": {
                        "remaining_budget": self.state.remaining,
                        "utilization": self.state.utilization,
                    },
                }
            )
        elif self.state.current_mode == BudgetMode.CRITICAL:
            alerts["alerts"].append(
                {
                    "level": "warning",
                    "code": "BUDGET_CRITICAL",
                    "message": "预算临界，仅允许核心任务",
                    "action": "考虑增加预算或暂停非必要任务",
                    "details": {
                        "remaining_budget": self.state.remaining,
                        "utilization": self.state.utilization,
                    },
                }
            )
        elif self.state.current_mode == BudgetMode.LOW:
            alerts["warnings"].append(
                {
                    "level": "warning",
                    "code": "BUDGET_LOW",
                    "message": "预算较低，已启用降级模式",
                    "action": "监控预算使用，优化任务成本",
                    "details": {
                        "remaining_budget": self.state.remaining,
                        "utilization": self.state.utilization,
                    },
                }
            )

        # 使用率警告
        if self.state.utilization >= 0.9:
            alerts["warnings"].append(
                {
                    "level": "warning",
                    "code": "HIGH_UTILIZATION",
                    "message": f"预算使用率高达 {self.state.utilization:.1%}",
                    "action": "准备暂停非必要任务",
                }
            )
        elif self.state.utilization >= 0.7:
            alerts["warnings"].append(
                {
                    "level": "info",
                    "code": "ELEVATED_UTILIZATION",
                    "message": f"预算使用率 {self.state.utilization:.1%}",
                    "action": "监控预算消耗",
                }
            )

        # 燃烧率警告（简化：如果burn_rate > 周期预算/24，则每小时消耗超过每日预算的1/24）
        if self.state.burn_rate > 0 and self.state.period_budget > 0:
            hourly_budget = self.state.period_budget / 24
            if self.state.burn_rate > hourly_budget * 2:
                alerts["warnings"].append(
                    {
                        "level": "warning",
                        "code": "HIGH_BURN_RATE",
                        "message": f"消费速率较高: {self.state.burn_rate:.2f}/小时",
                        "action": "检查任务成本，优化资源使用",
                    }
                )

        # 添加建议
        alerts["recommendations"].append(self._get_recommendation())

        return alerts

    def heartbeat(self) -> Dict[str, Any]:
        """预算心跳检查"""
        return self.get_structured_state()


# ==================== 全局单例实例 ====================

_budget_engine_instance: Optional[BudgetEngine] = None


def get_budget_engine() -> BudgetEngine:
    """获取全局预算引擎实例"""
    global _budget_engine_instance
    if _budget_engine_instance is None:
        _budget_engine_instance = BudgetEngine()
    return _budget_engine_instance


if __name__ == "__main__":
    # 测试代码
    print("=== Budget Engine 测试 ===")

    engine = BudgetEngine()

    print("\n1. 初始状态:")
    state = engine.get_state()
    print(f"   模式: {state.current_mode.value}")
    print(f"   预算: {state.period_budget:.2f}")
    print(f"   已消费: {state.consumed:.2f}")
    print(f"   剩余: {state.remaining:.2f}")

    print("\n2. 测试预算检查:")
    requests = [
        BudgetCheckRequest(
            task_id="test_1",
            estimated_cost=10.0,
            task_type="general",
            description="普通任务测试",
        ),
        BudgetCheckRequest(
            task_id="test_2",
            estimated_cost=50.0,
            task_type="maintenance",
            is_essential=True,
            description="维护任务测试",
        ),
        BudgetCheckRequest(
            task_id="test_3",
            estimated_cost=200.0,
            task_type="general",
            description="高成本任务测试",
        ),
    ]

    for req in requests:
        result = engine.check_budget(req)
        print(f"   任务: {req.task_id}, 成本: {req.estimated_cost:.2f}")
        print(f"     决定: {result.decision.value}, 允许: {result.allowed}, 原因: {result.reason}")

    print("\n3. 测试消费记录:")
    engine.record_consumption(
        task_id="test_consumption",
        cost=15.5,
        task_type="general",
        description="测试消费",
    )

    state = engine.get_state()
    print(f"   更新后已消费: {state.consumed:.2f}")
    print(f"   更新后剩余: {state.remaining:.2f}")

    print("\n4. 测试心跳:")
    heartbeat = engine.heartbeat()
    print(f"   结构化状态已生成，包含 {len(heartbeat)} 个部分")

    print("\n=== 测试完成 ===")
