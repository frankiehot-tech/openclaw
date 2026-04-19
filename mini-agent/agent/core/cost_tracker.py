#!/usr/bin/env python3
"""
成本跟踪系统 - 基于审计报告第二阶段优化建议

跟踪所有LLM API请求的成本，提供实时监控、聚合分析和告警功能。
集成provider_registry的成本估算功能，实现统一成本管理。

设计原则：
1. 最小依赖：基于现有provider_registry，不引入新的外部依赖
2. 数据持久化：SQLite轻量存储，易于调试和迁移
3. 异步友好：支持异步记录，避免阻塞主流程
4. 可审计：完整记录每次请求的上下文和成本估算

架构参考：
/Volumes/1TB-M2/openclaw/mini-agent/cost_monitoring_design.md
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
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from .financial_monitor import FinancialMonitor, get_financial_monitor

# 导入现有组件
from .provider_registry import ProviderRegistry, get_registry

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================


class CostRecordStatus(Enum):
    """成本记录状态"""

    RECORDED = "recorded"  # 已记录
    ESTIMATED = "estimated"  # 已估算（当无准确tokens时）
    VERIFIED = "verified"  # 已验证（与实际成本匹配）
    DISPUTED = "disputed"  # 有争议（估算与实际不符）
    SKIPPED = "skipped"  # 跳过（免费服务等）


class StorageBackendType(Enum):
    """存储后端类型"""

    SQLITE = "sqlite"  # SQLite数据库（默认）
    JSON_FILE = "json"  # JSON文件（用于调试）
    MEMORY = "memory"  # 内存存储（仅测试）
    POSTGRESQL = "postgresql"  # PostgreSQL（生产环境）


# ==================== 数据类定义 ====================


@dataclass
class CostRecord:
    """成本记录"""

    # 标识信息
    id: str  # 记录ID（建议使用UUID或请求ID）
    request_id: Optional[str]  # 原始请求ID（如果可用）

    # 时间信息
    timestamp: datetime  # 请求时间戳
    recorded_at: datetime  # 记录时间戳

    # 服务信息
    provider_id: str  # provider ID（如"deepseek"、"dashscope"）
    model_id: str  # 模型ID（如"deepseek-chat"、"qwen3.5-plus"）
    task_kind: Optional[str]  # 任务类型（如"debug"、"testing"、"general"）

    # 使用量信息
    input_tokens: int  # 输入tokens数量
    output_tokens: int  # 输出tokens数量
    estimated_cost: float  # 估算成本（元）
    estimated_tokens: bool = False  # tokens是否为估算值

    # 成本信息
    actual_cost: Optional[float] = None  # 实际成本（如从账单获取）
    cost_mode: str = "estimated"  # 成本模式（estimated/actual/verified）

    # 状态与元数据
    status: str = CostRecordStatus.RECORDED.value
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        # 转换datetime为字符串
        result["timestamp"] = self.timestamp.isoformat()
        result["recorded_at"] = self.recorded_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostRecord":
        """从字典创建实例"""
        # 转换字符串为datetime
        data_copy = data.copy()
        if isinstance(data_copy.get("timestamp"), str):
            data_copy["timestamp"] = datetime.fromisoformat(data_copy["timestamp"])
        if isinstance(data_copy.get("recorded_at"), str):
            data_copy["recorded_at"] = datetime.fromisoformat(data_copy["recorded_at"])

        # 只保留CostRecord类期望的字段
        import inspect

        # 获取构造函数签名
        sig = inspect.signature(cls.__init__)
        # 参数名列表（排除self）
        param_names = list(sig.parameters.keys())[1:]

        # 过滤字典，只保留构造函数接受的参数
        filtered_data = {k: v for k, v in data_copy.items() if k in param_names}

        return cls(**filtered_data)


@dataclass
class CostSummary:
    """成本摘要"""

    period_start: date  # 统计周期开始日期
    period_end: date  # 统计周期结束日期

    # 汇总指标
    total_cost: float  # 总成本
    total_requests: int  # 总请求数
    total_input_tokens: int  # 总输入tokens
    total_output_tokens: int  # 总输出tokens

    # 按维度分解
    by_provider: Dict[str, float]  # 按provider分解成本
    by_model: Dict[str, float]  # 按模型分解成本
    by_task_kind: Dict[str, float]  # 按任务类型分解成本

    # 趋势指标
    avg_cost_per_request: float  # 平均每次请求成本
    avg_tokens_per_request: float  # 平均每次请求tokens
    cost_per_1k_tokens: float  # 每千tokens平均成本

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result["period_start"] = self.period_start.isoformat()
        result["period_end"] = self.period_end.isoformat()
        return result


# ==================== 存储后端基类 ====================


class StorageBackend:
    """存储后端基类"""

    def __init__(self):
        pass

    def initialize(self):
        """初始化存储"""
        raise NotImplementedError

    def record_cost(self, record: CostRecord) -> bool:
        """记录成本"""
        raise NotImplementedError

    def get_records(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        provider_id: Optional[str] = None,
        model_id: Optional[str] = None,
        task_kind: Optional[str] = None,
        limit: int = 1000,
    ) -> List[CostRecord]:
        """获取成本记录"""
        raise NotImplementedError

    def get_summary(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> CostSummary:
        """获取成本摘要"""
        raise NotImplementedError

    def cleanup(self, days_to_keep: int = 90):
        """清理旧数据"""
        raise NotImplementedError


class SQLiteStorageBackend(StorageBackend):
    """SQLite存储后端"""

    def __init__(self, db_path: Optional[str] = None):
        super().__init__()
        if db_path is None:
            # 默认路径：项目根目录下的data/cost_tracking.db
            db_dir = os.path.join(project_root, "data")
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = os.path.join(db_dir, "cost_tracking.db")
        else:
            self.db_path = db_path

        self.conn = None
        self._initialize_connection()
        self.initialize()

    def _initialize_connection(self):
        """初始化数据库连接"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # 支持字典式访问
            logger.info(f"SQLite数据库连接已建立: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def initialize(self):
        """初始化数据库表"""
        try:
            cursor = self.conn.cursor()

            # 创建成本记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cost_records (
                    id TEXT PRIMARY KEY,
                    request_id TEXT,
                    timestamp DATETIME NOT NULL,
                    recorded_at DATETIME NOT NULL,
                    provider_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    task_kind TEXT,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    estimated_tokens BOOLEAN NOT NULL DEFAULT 0,
                    estimated_cost REAL NOT NULL,
                    actual_cost REAL,
                    cost_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT,

                    -- 索引以提高查询性能
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON cost_records (timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_provider ON cost_records (provider_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_kind ON cost_records (task_kind)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON cost_records (status)")

            self.conn.commit()
            logger.info("数据库表初始化完成")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            self.conn.rollback()
            raise

    def record_cost(self, record: CostRecord) -> bool:
        """记录成本"""
        try:
            cursor = self.conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO cost_records
                (id, request_id, timestamp, recorded_at, provider_id, model_id, task_kind,
                 input_tokens, output_tokens, estimated_tokens, estimated_cost, actual_cost,
                 cost_mode, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.id,
                    record.request_id,
                    record.timestamp.isoformat(),
                    record.recorded_at.isoformat(),
                    record.provider_id,
                    record.model_id,
                    record.task_kind,
                    record.input_tokens,
                    record.output_tokens,
                    1 if record.estimated_tokens else 0,
                    record.estimated_cost,
                    record.actual_cost,
                    record.cost_mode,
                    record.status,
                    json.dumps(record.metadata) if record.metadata else None,
                ),
            )

            self.conn.commit()
            logger.debug(
                f"成本记录已保存: {record.id} - {record.provider_id}/{record.model_id} - ¥{record.estimated_cost:.6f}"
            )
            return True

        except Exception as e:
            logger.error(f"保存成本记录失败: {e}")
            self.conn.rollback()
            return False

    def get_records(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        provider_id: Optional[str] = None,
        model_id: Optional[str] = None,
        task_kind: Optional[str] = None,
        limit: int = 1000,
    ) -> List[CostRecord]:
        """获取成本记录"""
        try:
            cursor = self.conn.cursor()

            # 构建查询条件
            query = "SELECT * FROM cost_records WHERE 1=1"
            params = []

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND timestamp < ?"
                params.append((end_date + timedelta(days=1)).isoformat())

            if provider_id:
                query += " AND provider_id = ?"
                params.append(provider_id)

            if model_id:
                query += " AND model_id = ?"
                params.append(model_id)

            if task_kind:
                query += " AND task_kind = ?"
                params.append(task_kind)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # 转换为CostRecord对象
            records = []
            for row in rows:
                record_data = dict(row)

                # 处理metadata JSON
                if record_data.get("metadata"):
                    record_data["metadata"] = json.loads(record_data["metadata"])
                else:
                    record_data["metadata"] = {}

                # 处理布尔值
                record_data["estimated_tokens"] = bool(record_data.get("estimated_tokens", 0))

                records.append(CostRecord.from_dict(record_data))

            return records

        except Exception as e:
            logger.error(f"获取成本记录失败: {e}")
            return []

    def get_summary(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> CostSummary:
        """获取成本摘要"""
        try:
            cursor = self.conn.cursor()

            # 构建日期条件
            date_condition = "WHERE 1=1"
            params = []

            if start_date:
                date_condition += " AND timestamp >= ?"
                params.append(start_date.isoformat())

            if end_date:
                date_condition += " AND timestamp < ?"
                params.append((end_date + timedelta(days=1)).isoformat())

            # 1. 基本统计
            cursor.execute(
                f"""
                SELECT
                    COUNT(*) as total_requests,
                    SUM(estimated_cost) as total_cost,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    AVG(estimated_cost) as avg_cost_per_request,
                    AVG(input_tokens + output_tokens) as avg_tokens_per_request
                FROM cost_records
                {date_condition}
            """,
                params,
            )

            basic_stats = dict(cursor.fetchone())

            # 处理None值（当没有记录时）
            for key in basic_stats:
                if basic_stats[key] is None:
                    basic_stats[key] = 0.0 if "cost" in key or "avg" in key else 0

            # 2. 按provider统计
            cursor.execute(
                f"""
                SELECT
                    provider_id,
                    SUM(estimated_cost) as provider_cost,
                    COUNT(*) as request_count
                FROM cost_records
                {date_condition}
                GROUP BY provider_id
                ORDER BY provider_cost DESC
            """,
                params,
            )

            by_provider = {}
            for row in cursor.fetchall():
                by_provider[row["provider_id"]] = row["provider_cost"] or 0.0

            # 3. 按模型统计
            cursor.execute(
                f"""
                SELECT
                    model_id,
                    SUM(estimated_cost) as model_cost
                FROM cost_records
                {date_condition}
                GROUP BY model_id
                ORDER BY model_cost DESC
            """,
                params,
            )

            by_model = {}
            for row in cursor.fetchall():
                by_model[row["model_id"]] = row["model_cost"] or 0.0

            # 4. 按任务类型统计
            cursor.execute(
                f"""
                SELECT
                    task_kind,
                    SUM(estimated_cost) as task_cost
                FROM cost_records
                {date_condition} AND task_kind IS NOT NULL
                GROUP BY task_kind
                ORDER BY task_cost DESC
            """,
                params,
            )

            by_task_kind = {}
            for row in cursor.fetchall():
                by_task_kind[row["task_kind"]] = row["task_cost"] or 0.0

            # 计算每千tokens成本
            total_tokens = basic_stats.get("total_input_tokens", 0) + basic_stats.get(
                "total_output_tokens", 0
            )
            cost_per_1k_tokens = 0.0
            if total_tokens > 0:
                cost_per_1k_tokens = (basic_stats.get("total_cost", 0.0) / total_tokens) * 1000.0

            # 设置默认日期范围
            if not start_date:
                start_date = date.today() - timedelta(days=30)
            if not end_date:
                end_date = date.today()

            return CostSummary(
                period_start=start_date,
                period_end=end_date,
                total_cost=basic_stats.get("total_cost", 0.0),
                total_requests=basic_stats.get("total_requests", 0),
                total_input_tokens=basic_stats.get("total_input_tokens", 0),
                total_output_tokens=basic_stats.get("total_output_tokens", 0),
                by_provider=by_provider,
                by_model=by_model,
                by_task_kind=by_task_kind,
                avg_cost_per_request=basic_stats.get("avg_cost_per_request", 0.0),
                avg_tokens_per_request=basic_stats.get("avg_tokens_per_request", 0.0),
                cost_per_1k_tokens=cost_per_1k_tokens,
            )

        except Exception as e:
            logger.error(f"获取成本摘要失败: {e}")
            # 返回空摘要
            today = date.today()
            return CostSummary(
                period_start=today,
                period_end=today,
                total_cost=0.0,
                total_requests=0,
                total_input_tokens=0,
                total_output_tokens=0,
                by_provider={},
                by_model={},
                by_task_kind={},
                avg_cost_per_request=0.0,
                avg_tokens_per_request=0.0,
                cost_per_1k_tokens=0.0,
            )

    def cleanup(self, days_to_keep: int = 90):
        """清理旧数据"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).date()

            cursor = self.conn.cursor()
            cursor.execute(
                "DELETE FROM cost_records WHERE date(timestamp) < ?", (cutoff_date.isoformat(),)
            )

            deleted_count = cursor.rowcount
            self.conn.commit()

            logger.info(f"清理了 {deleted_count} 条 {cutoff_date} 之前的旧记录")
            return deleted_count

        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            self.conn.rollback()
            return 0

    def __del__(self):
        """析构函数，关闭数据库连接"""
        if self.conn:
            self.conn.close()


# ==================== 核心成本跟踪器 ====================


class CostTracker:
    """成本跟踪器"""

    def __init__(self, storage_backend: str = "sqlite", config: Optional[Dict[str, Any]] = None):
        """
        初始化成本跟踪器

        Args:
            storage_backend: 存储后端类型（sqlite/json/memory）
            config: 配置参数
        """
        self.config = config or {}

        # 初始化provider registry
        self.registry = get_registry()

        # 初始化存储后端
        self.storage = self._create_storage_backend(storage_backend)
        self.storage.initialize()

        # 初始化金融监控器（可选）
        self.financial_monitor = None
        try:
            self.financial_monitor = get_financial_monitor()
        except Exception:
            logger.warning("金融监控器不可用，跳过集成")

        # 初始化预算引擎（可选）
        self.budget_engine = None
        try:
            from .budget_engine import get_budget_engine

            self.budget_engine = get_budget_engine()
        except Exception:
            logger.warning("预算引擎不可用，跳过集成")

        # 初始化金融监控器适配器（可选）
        self.financial_monitor_adapter = None
        try:
            from .financial_monitor_adapter import (
                get_financial_monitor_adapter,
                start_financial_monitor_adapter,
            )

            self.financial_monitor_adapter = get_financial_monitor_adapter()
            # 尝试启动适配器（如果未启动）
            try:
                start_financial_monitor_adapter()
            except Exception:
                logger.debug("金融监控器适配器已启动或无法启动")
        except Exception as e:
            logger.warning(f"金融监控器适配器不可用，跳过集成: {e}")

        logger.info(f"成本跟踪器初始化完成，存储后端: {storage_backend}")

    def _create_storage_backend(self, backend_type: str) -> StorageBackend:
        """创建存储后端"""
        if backend_type == "sqlite":
            db_path = self.config.get("db_path")
            return SQLiteStorageBackend(db_path)
        elif backend_type == "json":
            # JSON文件存储（简化实现）
            from .cost_tracker_json_storage import JSONStorageBackend

            file_path = self.config.get("file_path", "cost_records.json")
            return JSONStorageBackend(file_path)
        elif backend_type == "memory":
            # 内存存储（测试用）
            from .cost_tracker_memory_storage import MemoryStorageBackend

            return MemoryStorageBackend()
        else:
            raise ValueError(f"不支持的存储后端类型: {backend_type}")

    def record_request(
        self,
        request_id: Optional[str] = None,
        provider_id: str = "",
        model_id: str = "",
        task_kind: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_tokens: bool = False,
        cost_estimation: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录API请求成本

        Args:
            request_id: 请求ID（可选）
            provider_id: provider ID
            model_id: 模型ID
            task_kind: 任务类型
            input_tokens: 输入tokens
            output_tokens: 输出tokens
            estimated_tokens: tokens是否为估算值
            cost_estimation: 预计算的成本估算（可选）
            metadata: 额外元数据

        Returns:
            记录ID
        """
        try:
            # 生成记录ID
            record_id = request_id or f"cost_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

            # 估算成本（如果未提供）
            if cost_estimation is None:
                cost_estimation = self.registry.estimate_cost(
                    provider_id, model_id, input_tokens, output_tokens
                )

            # 创建成本记录
            record = CostRecord(
                id=record_id,
                request_id=request_id,
                timestamp=datetime.now(),
                recorded_at=datetime.now(),
                provider_id=provider_id,
                model_id=model_id,
                task_kind=task_kind,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_tokens=estimated_tokens,
                estimated_cost=cost_estimation.get("estimated_cost", 0.0),
                actual_cost=None,  # 后续可以从账单更新
                cost_mode=cost_estimation.get("cost_mode", "estimated"),
                status=CostRecordStatus.RECORDED.value,
                metadata=metadata or {},
            )

            # 保存记录
            success = self.storage.record_cost(record)
            if success:
                logger.info(
                    f"成本记录成功: {provider_id}/{model_id} - "
                    f"{input_tokens}+{output_tokens} tokens = ¥{record.estimated_cost:.6f}"
                )

                # 可选：通知金融监控器
                if self.financial_monitor and record.estimated_cost > 0:
                    self._notify_financial_monitor(record)

                return record_id
            else:
                logger.warning(f"成本记录保存失败: {record_id}")
                return ""

        except Exception as e:
            logger.error(f"记录成本失败: {e}")
            return ""

    def sync_cost_to_budget_engine(self, record: CostRecord) -> bool:
        """
        同步成本记录到预算引擎

        这个方法提供了显式的成本数据同步接口，可以由外部代码调用。
        也可以用于重新同步历史数据或修复丢失的同步。

        Args:
            record: 成本记录

        Returns:
            是否同步成功
        """
        if not self.budget_engine:
            logger.warning("预算引擎不可用，无法同步成本数据")
            return False

        try:
            # 构建任务描述
            task_desc = f"{record.provider_id}/{record.model_id}"
            if record.task_kind:
                task_desc += f" ({record.task_kind})"

            # 记录消费到预算引擎
            self.budget_engine.record_consumption(
                task_id=record.id,
                cost=record.estimated_cost,
                task_type="llm_api_call",
                description=f"LLM API调用: {task_desc} - {record.input_tokens}+{record.output_tokens} tokens",
                metadata={
                    "provider_id": record.provider_id,
                    "model_id": record.model_id,
                    "task_kind": record.task_kind,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "estimated_tokens": record.estimated_tokens,
                    "request_id": record.request_id,
                    "cost_mode": record.cost_mode,
                    "status": record.status,
                    "timestamp": record.timestamp.isoformat(),
                    "sync_source": "cost_tracker",
                    "sync_time": datetime.now().isoformat(),
                },
            )

            logger.info(f"成本记录已同步到预算引擎: {record.id} - ¥{record.estimated_cost:.6f}")
            return True

        except Exception as e:
            logger.error(f"同步成本记录到预算引擎失败: {e}")
            return False

    def sync_historical_costs(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        同步历史成本记录到预算引擎

        用于批量同步指定时间段内的成本数据到预算引擎。
        适用于初始数据迁移或修复丢失的同步。

        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            同步结果统计
        """
        if not self.budget_engine:
            logger.warning("预算引擎不可用，无法同步历史成本数据")
            return {"success": False, "reason": "预算引擎不可用"}

        try:
            # 获取指定时间段的成本记录
            records = self.storage.get_records(
                start_date=start_date, end_date=end_date, limit=10000  # 最多同步10000条记录
            )

            if not records:
                logger.info("指定时间段内没有成本记录需要同步")
                return {
                    "success": True,
                    "total_records": 0,
                    "synced_records": 0,
                    "failed_records": 0,
                    "total_cost": 0.0,
                    "message": "没有成本记录需要同步",
                }

            logger.info(f"开始同步历史成本数据: {len(records)} 条记录")

            # 统计信息
            synced_count = 0
            failed_count = 0
            total_cost = 0.0

            # 逐条同步
            for i, record in enumerate(records):
                try:
                    success = self.sync_cost_to_budget_engine(record)
                    if success:
                        synced_count += 1
                        total_cost += record.estimated_cost
                        # 避免日志过多，每100条记录打印一次进度
                        if (i + 1) % 100 == 0:
                            logger.info(f"同步进度: {i + 1}/{len(records)}")
                    else:
                        failed_count += 1
                        logger.warning(f"同步记录失败: {record.id}")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"同步记录异常: {record.id} - {e}")

            # 生成结果
            result = {
                "success": True,
                "total_records": len(records),
                "synced_records": synced_count,
                "failed_records": failed_count,
                "total_cost": total_cost,
                "sync_rate": f"{synced_count}/{len(records)} ({synced_count/len(records)*100:.1f}%)",
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "sync_timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"历史成本数据同步完成: "
                f"总共{len(records)}条记录, "
                f"成功{synced_count}条, "
                f"失败{failed_count}条, "
                f"总成本¥{total_cost:.6f}"
            )

            return result

        except Exception as e:
            logger.error(f"同步历史成本数据失败: {e}")
            return {"success": False, "reason": str(e)}

    def _notify_financial_monitor(self, record: CostRecord):
        """
        通知金融监控器和预算引擎，记录成本消费

        支持异步记录，避免阻塞主流程。优先使用金融监控器适配器，
        如果适配器不可用，回退到直接预算引擎集成。
        """
        try:
            # 优先使用金融监控器适配器（异步、可靠）
            if self.financial_monitor_adapter:
                try:
                    # 使用适配器同步成本记录（异步模式）
                    success = self.financial_monitor_adapter.sync_cost_record(
                        record, async_mode=True
                    )
                    if success:
                        logger.debug(
                            f"成本记录已提交到金融监控器适配器: {record.id} - ¥{record.estimated_cost:.6f}"
                        )
                    else:
                        logger.warning(f"成本记录提交到适配器失败，将尝试回退方法: {record.id}")
                        # 回退到直接同步
                        self._notify_financial_monitor_fallback(record)
                    return True
                except Exception as e:
                    logger.warning(f"使用适配器同步失败，将回退: {e}")
                    return self._notify_financial_monitor_fallback(record)
            else:
                # 适配器不可用，使用回退方法
                return self._notify_financial_monitor_fallback(record)

        except Exception as e:
            logger.error(f"通知金融监控器过程中出错: {e}")
            return False

    def _notify_financial_monitor_fallback(self, record: CostRecord) -> bool:
        """
        回退方法：直接通知预算引擎和金融监控器

        当适配器不可用时使用。
        """
        try:
            # 优先记录到预算引擎（如果有）
            if self.budget_engine:
                try:
                    # 构建任务描述
                    task_desc = f"{record.provider_id}/{record.model_id}"
                    if record.task_kind:
                        task_desc += f" ({record.task_kind})"

                    # 记录消费到预算引擎
                    self.budget_engine.record_consumption(
                        task_id=record.id,
                        cost=record.estimated_cost,
                        task_type="llm_api_call",
                        description=f"LLM API调用: {task_desc} - {record.input_tokens}+{record.output_tokens} tokens",
                        metadata={
                            "provider_id": record.provider_id,
                            "model_id": record.model_id,
                            "task_kind": record.task_kind,
                            "input_tokens": record.input_tokens,
                            "output_tokens": record.output_tokens,
                            "estimated_tokens": record.estimated_tokens,
                            "request_id": record.request_id,
                            "cost_mode": record.cost_mode,
                            "status": record.status,
                            "timestamp": record.timestamp.isoformat(),
                        },
                    )

                    logger.debug(
                        f"已记录消费到预算引擎: {record.id} - ¥{record.estimated_cost:.6f}"
                    )
                    return True

                except Exception as e:
                    logger.warning(f"记录消费到预算引擎失败: {e}")

            # 如果预算引擎不可用，尝试通知金融监控器（如有）
            if self.financial_monitor:
                try:
                    # 金融监控器目前没有直接的消费记录接口，只能记录日志
                    # 未来可以与金融监控器集成，更新实时消费数据
                    logger.debug(
                        f"通知金融监控器: 成本记录 {record.id} - ¥{record.estimated_cost:.6f}"
                    )
                    return True
                except Exception as e:
                    logger.debug(f"通知金融监控器失败（可忽略）: {e}")

            return False
        except Exception as e:
            logger.error(f"回退方法通知金融监控器失败: {e}")
            return False

            return True

        except Exception as e:
            logger.error(f"通知金融监控器/预算引擎失败: {e}")
            return False

    def get_daily_summary(self, date_str: Optional[str] = None) -> CostSummary:
        """获取每日成本摘要"""
        try:
            if date_str:
                target_date = date.fromisoformat(date_str)
            else:
                target_date = date.today()

            return self.storage.get_summary(target_date, target_date)

        except Exception as e:
            logger.error(f"获取每日摘要失败: {e}")
            today = date.today()
            return CostSummary(
                period_start=today,
                period_end=today,
                total_cost=0.0,
                total_requests=0,
                total_input_tokens=0,
                total_output_tokens=0,
                by_provider={},
                by_model={},
                by_task_kind={},
                avg_cost_per_request=0.0,
                avg_tokens_per_request=0.0,
                cost_per_1k_tokens=0.0,
            )

    def get_provider_breakdown(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """按provider分解成本"""
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)

            summary = self.storage.get_summary(start, end)

            # 计算百分比
            breakdown = {}
            for provider_id, cost in summary.by_provider.items():
                percentage = (cost / summary.total_cost * 100) if summary.total_cost > 0 else 0
                breakdown[provider_id] = {
                    "cost": round(cost, 6),
                    "percentage": round(percentage, 2),
                    "requests": self._count_requests_by_provider(start, end, provider_id),
                }

            return {
                "period": {"start": start.isoformat(), "end": end.isoformat()},
                "total_cost": round(summary.total_cost, 6),
                "breakdown": breakdown,
                "recommendations": self._generate_provider_recommendations(breakdown),
            }

        except Exception as e:
            logger.error(f"获取provider分解失败: {e}")
            return {"error": str(e)}

    def _count_requests_by_provider(
        self, start_date: date, end_date: date, provider_id: str
    ) -> int:
        """统计指定provider的请求数"""
        records = self.storage.get_records(
            start_date, end_date, provider_id=provider_id, limit=10000
        )
        return len(records)

    def _generate_provider_recommendations(self, breakdown: Dict[str, Any]) -> List[str]:
        """生成provider优化建议"""
        recommendations = []

        # 分析成本分布
        providers = list(breakdown.keys())
        if len(providers) < 2:
            return ["单provider使用，无对比数据"]

        # 找出最高成本和最低成本provider
        sorted_providers = sorted(breakdown.items(), key=lambda x: x[1]["cost"], reverse=True)

        highest = sorted_providers[0]  # 最高成本
        lowest = sorted_providers[-1]  # 最低成本

        # 计算潜在节省
        if highest[1]["cost"] > 0 and lowest[1]["cost"] < highest[1]["cost"]:
            cost_ratio = lowest[1]["cost"] / highest[1]["cost"] if highest[1]["cost"] > 0 else 0
            potential_savings = highest[1]["cost"] * (1 - cost_ratio)

            if potential_savings > 0.01:  # 节省超过0.01元
                recommendations.append(
                    f"考虑将部分{highest[0]}任务迁移到{lowest[0]}，"
                    f"潜在节省约¥{potential_savings:.4f}/天"
                )

        # 检查是否所有debug/testing任务都使用低成本provider
        # （未来扩展：结合task_kind分析）

        return recommendations

    def get_task_kind_analysis(self, period: str = "daily") -> Dict[str, Any]:
        """按任务类型分析成本"""
        try:
            # 确定日期范围
            end_date = date.today()
            if period == "daily":
                start_date = end_date
            elif period == "weekly":
                start_date = end_date - timedelta(days=7)
            elif period == "monthly":
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=1)  # 默认昨天

            summary = self.storage.get_summary(start_date, end_date)

            return {
                "period": {
                    "type": period,
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "total_cost": round(summary.total_cost, 6),
                "task_kind_breakdown": summary.by_task_kind,
                "recommendations": self._generate_task_kind_recommendations(summary),
            }

        except Exception as e:
            logger.error(f"获取任务类型分析失败: {e}")
            return {"error": str(e)}

    def _generate_task_kind_recommendations(self, summary: CostSummary) -> List[str]:
        """生成任务类型优化建议"""
        recommendations = []

        # 分析任务类型成本分布
        if not summary.by_task_kind:
            return ["无任务类型数据，请确保记录时包含task_kind字段"]

        # 找出成本最高的任务类型
        sorted_tasks = sorted(summary.by_task_kind.items(), key=lambda x: x[1], reverse=True)

        if sorted_tasks:
            highest_task = sorted_tasks[0]
            recommendations.append(
                f"成本最高的任务类型: {highest_task[0]} (¥{highest_task[1]:.4f}，"
                f"占总成本{highest_task[1]/summary.total_cost*100:.1f}%)"
            )

        # 检查debug/testing任务是否确实使用了低成本provider
        # （未来扩展：需要关联provider数据）

        return recommendations

    def get_records(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        provider_id: Optional[str] = None,
        model_id: Optional[str] = None,
        task_kind: Optional[str] = None,
        limit: int = 1000,
    ) -> List[CostRecord]:
        """获取成本记录（代理方法）"""
        return self.storage.get_records(
            start_date=start_date,
            end_date=end_date,
            provider_id=provider_id,
            model_id=model_id,
            task_kind=task_kind,
            limit=limit,
        )

    def get_summary(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> CostSummary:
        """获取成本摘要（代理方法）"""
        return self.storage.get_summary(start_date, end_date)

    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """清理旧数据"""
        return self.storage.cleanup(days_to_keep)

    def export_data(self, export_path: str, format: str = "json") -> bool:
        """导出数据"""
        try:
            # 获取所有记录（最近10000条）
            records = self.storage.get_records(limit=10000)

            if format == "json":
                data = {
                    "export_time": datetime.now().isoformat(),
                    "record_count": len(records),
                    "records": [record.to_dict() for record in records],
                }

                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                logger.info(f"数据已导出到 {export_path}: {len(records)} 条记录")
                return True
            else:
                logger.error(f"不支持的导出格式: {format}")
                return False

        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            return False

    def sync_historical_costs_to_financial_monitor(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        同步历史成本数据到金融监控器适配器

        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 最大记录数
            batch_size: 批处理大小

        Returns:
            同步结果统计
        """
        if not self.financial_monitor_adapter:
            logger.warning("金融监控器适配器不可用，无法同步历史数据")
            return {"success": False, "error": "金融监控器适配器不可用", "records_synced": 0}

        try:
            # 使用适配器的同步方法
            result = self.financial_monitor_adapter.sync_historical_costs(
                start_date=start_date, end_date=end_date, limit=limit, batch_size=batch_size
            )

            logger.info(f"历史成本数据同步完成: {result.get('records_synced', 0)} 条记录成功")
            return result

        except Exception as e:
            logger.error(f"同步历史成本数据失败: {e}")
            return {"success": False, "error": str(e), "records_synced": 0}

    def get_financial_dashboard_data(self) -> Dict[str, Any]:
        """
        获取金融仪表板数据

        返回集成的金融监控器、成本跟踪和适配器数据
        """
        if not self.financial_monitor_adapter:
            return {
                "success": False,
                "error": "金融监控器适配器不可用",
                "data": {
                    "cost_tracker_only": {
                        "total_records": len(self.get_records(limit=1)),
                        "available": True,
                    }
                },
            }

        try:
            # 使用适配器的仪表板数据方法
            dashboard_data = self.financial_monitor_adapter.get_financial_dashboard_data()
            return dashboard_data

        except Exception as e:
            logger.error(f"获取金融仪表板数据失败: {e}")
            return {"success": False, "error": str(e), "data": {}}


# ==================== 全局实例 ====================


_cost_tracker_instance: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """获取全局成本跟踪器实例"""
    global _cost_tracker_instance
    if _cost_tracker_instance is None:
        _cost_tracker_instance = CostTracker()
    return _cost_tracker_instance


# ==================== 命令行接口 ====================


def main():
    """命令行入口点"""
    import argparse

    parser = argparse.ArgumentParser(description="成本跟踪系统命令行工具")
    parser.add_argument("--today", action="store_true", help="查看今日成本")
    parser.add_argument("--provider-breakdown", action="store_true", help="provider成本分解")
    parser.add_argument("--period", type=str, default="week", help="分析周期: day/week/month")
    parser.add_argument("--task-analysis", action="store_true", help="任务类型分析")
    parser.add_argument("--trend", action="store_true", help="成本趋势")
    parser.add_argument("--days", type=int, default=30, help="趋势分析天数")
    parser.add_argument("--export", type=str, help="导出数据到文件")
    parser.add_argument("--cleanup", type=int, help="清理N天前的旧数据")

    args = parser.parse_args()

    # 初始化成本跟踪器
    tracker = get_cost_tracker()

    if args.today:
        # 今日成本
        summary = tracker.get_daily_summary()
        print(f"📊 今日成本摘要 ({summary.period_start})")
        print(f"   总成本: ¥{summary.total_cost:.6f}")
        print(f"   总请求: {summary.total_requests}")
        print(f"   总tokens: {summary.total_input_tokens + summary.total_output_tokens:,}")
        print(f"   每千tokens成本: ¥{summary.cost_per_1k_tokens:.6f}")

        if summary.by_provider:
            print(f"\n按provider分解:")
            for provider, cost in summary.by_provider.items():
                percentage = (cost / summary.total_cost * 100) if summary.total_cost > 0 else 0
                print(f"   • {provider}: ¥{cost:.6f} ({percentage:.1f}%)")

    elif args.provider_breakdown:
        # provider分解
        if args.period == "day":
            start_date = date.today().isoformat()
            end_date = start_date
        elif args.period == "week":
            start_date = (date.today() - timedelta(days=7)).isoformat()
            end_date = date.today().isoformat()
        elif args.period == "month":
            start_date = (date.today() - timedelta(days=30)).isoformat()
            end_date = date.today().isoformat()
        else:
            start_date = (date.today() - timedelta(days=7)).isoformat()
            end_date = date.today().isoformat()

        result = tracker.get_provider_breakdown(start_date, end_date)

        if "error" in result:
            print(f"❌ 错误: {result['error']}")
            return

        print(f"📊 Provider成本分解 ({result['period']['start']} 到 {result['period']['end']})")
        print(f"总成本: ¥{result['total_cost']:.6f}")
        print("\n分解详情:")
        for provider, data in result["breakdown"].items():
            print(f"   • {provider}:")
            print(f"     成本: ¥{data['cost']:.6f} ({data['percentage']}%)")
            print(f"     请求数: {data['requests']}")

        if result.get("recommendations"):
            print(f"\n💡 优化建议:")
            for rec in result["recommendations"]:
                print(f"   • {rec}")

    elif args.task_analysis:
        # 任务类型分析
        result = tracker.get_task_kind_analysis(args.period)

        if "error" in result:
            print(f"❌ 错误: {result['error']}")
            return

        print(
            f"📊 任务类型分析 ({result['period']['type']}，{result['period']['start']} 到 {result['period']['end']})"
        )
        print(f"总成本: ¥{result['total_cost']:.6f}")

        if result["task_kind_breakdown"]:
            print("\n按任务类型分解:")
            for task_kind, cost in result["task_kind_breakdown"].items():
                percentage = (cost / result["total_cost"] * 100) if result["total_cost"] > 0 else 0
                print(f"   • {task_kind}: ¥{cost:.6f} ({percentage:.1f}%)")

        if result.get("recommendations"):
            print(f"\n💡 优化建议:")
            for rec in result["recommendations"]:
                print(f"   • {rec}")

    elif args.trend:
        # 成本趋势（简化实现）
        print("📈 成本趋势分析")
        print("（基础版本，未来可增强为可视化图表）")

        # 获取最近N天的每日摘要
        trends = []
        for i in range(args.days - 1, -1, -1):
            target_date = date.today() - timedelta(days=i)
            summary = tracker.get_daily_summary(target_date.isoformat())

            trends.append(
                {
                    "date": target_date.isoformat(),
                    "cost": summary.total_cost,
                    "requests": summary.total_requests,
                }
            )

        # 显示趋势
        print(f"\n最近{args.days}天成本趋势:")
        for trend in trends[-10:]:  # 显示最近10天
            print(f"   {trend['date']}: ¥{trend['cost']:.6f} ({trend['requests']}请求)")

        # 计算统计
        total_cost = sum(t["cost"] for t in trends)
        avg_daily_cost = total_cost / args.days if args.days > 0 else 0
        print(f"\n统计:")
        print(f"   总成本: ¥{total_cost:.6f} ({args.days}天)")
        print(f"   日均成本: ¥{avg_daily_cost:.6f}")

    elif args.export:
        # 导出数据
        success = tracker.export_data(args.export, "json")
        if success:
            print(f"✅ 数据已导出到 {args.export}")
        else:
            print(f"❌ 导出失败")

    elif args.cleanup:
        # 清理旧数据
        deleted = tracker.cleanup_old_data(args.cleanup)
        print(f"✅ 清理了 {deleted} 条 {args.cleanup} 天前的旧记录")

    else:
        # 默认显示帮助
        parser.print_help()


if __name__ == "__main__":
    main()
