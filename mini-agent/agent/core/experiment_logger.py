#!/usr/bin/env python3
"""
实验日志记录器 - 记录详细的实验数据用于分析

基于实验路由器框架，记录完整的实验上下文：
1. 实验分配信息
2. 输入prompt和输出response
3. 执行时间和性能指标
4. 质量评分（如果可用）
5. 成本关联信息

设计目标：
- 与现有的成本跟踪系统集成
- 支持大规模实验数据收集（100+样本）
- 数据格式兼容统计分析需求
- 异步记录，避免阻塞主流程
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

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================


class ExperimentRecordStatus(Enum):
    """实验记录状态"""

    CREATED = "created"  # 已创建
    ASSIGNED = "assigned"  # 已分配实验
    EXECUTED = "executed"  # 已执行
    EVALUATED = "evaluated"  # 已评估
    COMPLETED = "completed"  # 已完成


class ExperimentDataQuality(Enum):
    """实验数据质量等级"""

    COMPLETE = "complete"  # 完整数据（输入+输出+成本+质量）
    PARTIAL = "partial"  # 部分数据（缺少某些字段）
    MINIMAL = "minimal"  # 最小数据（仅实验分配）
    INCOMPLETE = "incomplete"  # 数据不完整


# ==================== 数据类定义 ====================


@dataclass
class ExperimentRecord:
    """实验记录"""

    # 标识信息（无默认值的字段必须在前）
    experiment_id: str  # 实验ID
    request_id: str  # 请求ID
    group_name: str  # 实验分组（control/treatment）
    task_kind: str  # 任务类型

    # 带默认值的字段（必须在无默认值字段之后）
    id: str = ""  # 实验记录ID
    cost_record_id: Optional[str] = None  # 关联的成本记录ID
    assignment_metadata: Dict[str, Any] = field(default_factory=dict)  # 实验分配元数据

    # 输入输出信息
    input_prompt: Optional[str] = None  # 输入prompt（完整文本）
    output_response: Optional[str] = None  # 输出response（完整文本）
    input_summary: Optional[str] = None  # 输入摘要（如果完整文本过长）
    output_summary: Optional[str] = None  # 输出摘要（如果完整文本过长）

    # 性能指标
    execution_time: Optional[float] = None  # 执行时间（秒）
    tokens_used: Optional[Dict[str, int]] = None  # tokens使用量：{"input": 10, "output": 50}
    cost_info: Optional[Dict[str, Any]] = None  # 成本信息

    # 质量评估
    quality_score: Optional[float] = None  # 质量评分（0-10）
    quality_breakdown: Optional[Dict[str, float]] = None  # 质量分解评分
    quality_assessor: Optional[str] = None  # 质量评估器（human/auto）

    # 状态与元数据
    status: str = ExperimentRecordStatus.CREATED.value
    data_quality: str = ExperimentDataQuality.MINIMAL.value
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    recorded_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        # 转换datetime为字符串
        result["recorded_at"] = self.recorded_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentRecord":
        """从字典创建实例"""
        # 转换字符串为datetime
        data_copy = data.copy()
        if isinstance(data_copy.get("recorded_at"), str):
            data_copy["recorded_at"] = datetime.fromisoformat(data_copy["recorded_at"])

        # 只保留ExperimentRecord类期望的字段
        import inspect

        # 获取构造函数签名
        sig = inspect.signature(cls.__init__)
        # 参数名列表（排除self）
        param_names = list(sig.parameters.keys())[1:]

        # 过滤字典，只保留构造函数接受的参数
        filtered_data = {k: v for k, v in data_copy.items() if k in param_names}

        return cls(**filtered_data)

    def calculate_data_quality(self) -> str:
        """计算数据质量等级"""
        # 检查关键字段的存在性
        has_input = bool(self.input_prompt or self.input_summary)
        has_output = bool(self.output_response or self.output_summary)
        has_cost = bool(self.cost_info)
        has_execution_time = self.execution_time is not None

        # 质量评估
        has_quality_score = self.quality_score is not None

        if has_input and has_output and has_cost and has_execution_time and has_quality_score:
            return ExperimentDataQuality.COMPLETE.value
        elif has_input and has_output and has_cost:
            return ExperimentDataQuality.PARTIAL.value
        elif has_cost:
            return ExperimentDataQuality.MINIMAL.value
        else:
            return ExperimentDataQuality.INCOMPLETE.value

    def update_data_quality(self):
        """更新数据质量等级"""
        self.data_quality = self.calculate_data_quality()


@dataclass
class ExperimentSummary:
    """实验摘要统计"""

    experiment_id: str  # 实验ID
    period_start: date  # 统计周期开始
    period_end: date  # 统计周期结束

    # 样本统计
    total_samples: int  # 总样本数
    group_samples: Dict[str, int]  # 按分组样本数

    # 成本统计
    avg_cost_by_group: Dict[str, float]  # 按分组平均成本
    total_cost_by_group: Dict[str, float]  # 按分组总成本
    cost_savings_percentage: Optional[float]  # 成本节省百分比

    # 质量统计
    avg_quality_by_group: Dict[str, float]  # 按分组平均质量评分
    quality_difference: Optional[float]  # 质量差异（实验组-控制组）

    # 性能统计
    avg_execution_time_by_group: Dict[str, float]  # 按分组平均执行时间
    avg_tokens_by_group: Dict[str, Dict[str, float]]  # 按分组平均tokens使用量

    # 数据质量统计
    data_quality_distribution: Dict[str, int]  # 数据质量分布

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result["period_start"] = self.period_start.isoformat()
        result["period_end"] = self.period_end.isoformat()
        return result


# ==================== 存储后端 ====================


class ExperimentStorageBackend:
    """实验存储后端基类"""

    def __init__(self):
        pass

    def initialize(self):
        """初始化存储"""
        raise NotImplementedError

    def record_experiment(self, record: ExperimentRecord) -> bool:
        """记录实验数据"""
        raise NotImplementedError

    def get_experiment_records(
        self,
        experiment_id: Optional[str] = None,
        request_id: Optional[str] = None,
        group_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_data_quality: Optional[str] = None,
        limit: int = 1000,
    ) -> List[ExperimentRecord]:
        """获取实验记录"""
        raise NotImplementedError

    def get_experiment_summary(
        self, experiment_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> ExperimentSummary:
        """获取实验摘要"""
        raise NotImplementedError

    def cleanup(self, days_to_keep: int = 90):
        """清理旧数据"""
        raise NotImplementedError


class SQLiteExperimentStorageBackend(ExperimentStorageBackend):
    """SQLite实验存储后端"""

    def __init__(self, db_path: Optional[str] = None):
        super().__init__()
        if db_path is None:
            # 使用与成本跟踪相同的数据库
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
            logger.info(f"实验存储SQLite数据库连接已建立: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def initialize(self):
        """初始化数据库表"""
        try:
            cursor = self.conn.cursor()

            # 创建实验记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiment_records (
                    id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    cost_record_id TEXT,

                    -- 实验分配信息
                    group_name TEXT NOT NULL,
                    assignment_metadata TEXT,

                    -- 输入输出信息
                    task_kind TEXT NOT NULL,
                    input_prompt TEXT,
                    output_response TEXT,
                    input_summary TEXT,
                    output_summary TEXT,

                    -- 性能指标
                    execution_time REAL,
                    tokens_used TEXT,  -- JSON: {"input": 10, "output": 50}
                    cost_info TEXT,    -- JSON

                    -- 质量评估
                    quality_score REAL,
                    quality_breakdown TEXT,  -- JSON
                    quality_assessor TEXT,

                    -- 状态与元数据
                    status TEXT NOT NULL,
                    data_quality TEXT NOT NULL,
                    metadata TEXT,

                    -- 时间戳
                    recorded_at DATETIME NOT NULL,

                    -- 索引以提高查询性能
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_exp_id ON experiment_records (experiment_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_exp_group ON experiment_records (group_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_exp_request ON experiment_records (request_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_exp_task ON experiment_records (task_kind)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_exp_status ON experiment_records (status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_exp_quality ON experiment_records (data_quality)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_exp_recorded ON experiment_records (recorded_at)"
            )

            self.conn.commit()
            logger.info("实验记录数据库表初始化完成")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            self.conn.rollback()
            raise

    def record_experiment(self, record: ExperimentRecord) -> bool:
        """记录实验数据"""
        try:
            # 更新数据质量
            record.update_data_quality()

            cursor = self.conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO experiment_records
                (id, experiment_id, request_id, cost_record_id, group_name, assignment_metadata,
                 task_kind, input_prompt, output_response, input_summary, output_summary,
                 execution_time, tokens_used, cost_info, quality_score, quality_breakdown,
                 quality_assessor, status, data_quality, metadata, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.id,
                    record.experiment_id,
                    record.request_id,
                    record.cost_record_id,
                    record.group_name,
                    json.dumps(record.assignment_metadata) if record.assignment_metadata else None,
                    record.task_kind,
                    record.input_prompt,
                    record.output_response,
                    record.input_summary,
                    record.output_summary,
                    record.execution_time,
                    json.dumps(record.tokens_used) if record.tokens_used else None,
                    json.dumps(record.cost_info) if record.cost_info else None,
                    record.quality_score,
                    json.dumps(record.quality_breakdown) if record.quality_breakdown else None,
                    record.quality_assessor,
                    record.status,
                    record.data_quality,
                    json.dumps(record.metadata) if record.metadata else None,
                    record.recorded_at.isoformat(),
                ),
            )

            self.conn.commit()
            logger.info(f"实验记录已保存: {record.id} - {record.experiment_id}/{record.group_name}")
            return True

        except Exception as e:
            logger.error(f"保存实验记录失败: {e}")
            self.conn.rollback()
            return False

    def get_experiment_records(
        self,
        experiment_id: Optional[str] = None,
        request_id: Optional[str] = None,
        group_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_data_quality: Optional[str] = None,
        limit: int = 1000,
    ) -> List[ExperimentRecord]:
        """获取实验记录"""
        try:
            cursor = self.conn.cursor()

            # 构建查询条件
            query = "SELECT * FROM experiment_records WHERE 1=1"
            params = []

            if experiment_id:
                query += " AND experiment_id = ?"
                params.append(experiment_id)

            if request_id:
                query += " AND request_id = ?"
                params.append(request_id)

            if group_name:
                query += " AND group_name = ?"
                params.append(group_name)

            if start_date:
                query += " AND recorded_at >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND recorded_at < ?"
                params.append((end_date + timedelta(days=1)).isoformat())

            if min_data_quality:
                # 数据质量等级排序（从高到低）
                quality_order = ["complete", "partial", "minimal", "incomplete"]
                try:
                    min_index = quality_order.index(min_data_quality)
                    acceptable_qualities = quality_order[: min_index + 1]
                    placeholders = ",".join(["?"] * len(acceptable_qualities))
                    query += f" AND data_quality IN ({placeholders})"
                    params.extend(acceptable_qualities)
                except ValueError:
                    logger.warning(f"未知的数据质量等级: {min_data_quality}")

            query += " ORDER BY recorded_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            records = []
            for row in rows:
                # 解析JSON字段
                row_dict = dict(row)

                # 解析JSON字符串
                json_fields = [
                    "assignment_metadata",
                    "tokens_used",
                    "cost_info",
                    "quality_breakdown",
                    "metadata",
                ]
                for field in json_fields:
                    if row_dict.get(field):
                        try:
                            row_dict[field] = json.loads(row_dict[field])
                        except (json.JSONDecodeError, TypeError):
                            row_dict[field] = {}
                    else:
                        row_dict[field] = {}

                records.append(ExperimentRecord.from_dict(row_dict))

            return records

        except Exception as e:
            logger.error(f"获取实验记录失败: {e}")
            return []

    def get_experiment_summary(
        self, experiment_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> ExperimentSummary:
        """获取实验摘要"""
        try:
            records = self.get_experiment_records(
                experiment_id=experiment_id,
                start_date=start_date,
                end_date=end_date,
                min_data_quality="minimal",  # 至少需要最小数据质量
            )

            if not records:
                return None

            # 按分组统计
            group_samples = {}
            avg_cost_by_group = {}
            total_cost_by_group = {}
            avg_quality_by_group = {}
            avg_execution_time_by_group = {}
            avg_tokens_by_group = {}
            data_quality_distribution = {}

            # 初始化分组数据结构
            groups = set(record.group_name for record in records)
            for group in groups:
                group_samples[group] = 0
                avg_cost_by_group[group] = 0.0
                total_cost_by_group[group] = 0.0
                avg_quality_by_group[group] = 0.0
                avg_execution_time_by_group[group] = 0.0
                avg_tokens_by_group[group] = {"input": 0.0, "output": 0.0}

            # 统计总样本
            total_samples = len(records)

            # 数据质量分布
            quality_counts = {}

            # 汇总数据
            cost_records_by_group = {group: [] for group in groups}
            quality_scores_by_group = {group: [] for group in groups}
            execution_times_by_group = {group: [] for group in groups}
            tokens_by_group = {group: {"input": [], "output": []} for group in groups}

            for record in records:
                group = record.group_name
                group_samples[group] += 1

                # 数据质量统计
                quality_counts[record.data_quality] = quality_counts.get(record.data_quality, 0) + 1

                # 成本数据
                if record.cost_info and "estimated_cost" in record.cost_info:
                    cost = record.cost_info["estimated_cost"]
                    cost_records_by_group[group].append(cost)
                    total_cost_by_group[group] += cost

                # 质量评分
                if record.quality_score is not None:
                    quality_scores_by_group[group].append(record.quality_score)

                # 执行时间
                if record.execution_time is not None:
                    execution_times_by_group[group].append(record.execution_time)

                # Tokens使用量
                if record.tokens_used:
                    if "input" in record.tokens_used:
                        tokens_by_group[group]["input"].append(record.tokens_used["input"])
                    if "output" in record.tokens_used:
                        tokens_by_group[group]["output"].append(record.tokens_used["output"])

            # 计算平均值
            for group in groups:
                # 平均成本
                if cost_records_by_group[group]:
                    avg_cost_by_group[group] = sum(cost_records_by_group[group]) / len(
                        cost_records_by_group[group]
                    )
                    total_cost_by_group[group] = sum(cost_records_by_group[group])

                # 平均质量评分
                if quality_scores_by_group[group]:
                    avg_quality_by_group[group] = sum(quality_scores_by_group[group]) / len(
                        quality_scores_by_group[group]
                    )

                # 平均执行时间
                if execution_times_by_group[group]:
                    avg_execution_time_by_group[group] = sum(execution_times_by_group[group]) / len(
                        execution_times_by_group[group]
                    )

                # 平均tokens
                if tokens_by_group[group]["input"]:
                    avg_tokens_by_group[group]["input"] = sum(
                        tokens_by_group[group]["input"]
                    ) / len(tokens_by_group[group]["input"])
                if tokens_by_group[group]["output"]:
                    avg_tokens_by_group[group]["output"] = sum(
                        tokens_by_group[group]["output"]
                    ) / len(tokens_by_group[group]["output"])

            # 计算成本节省（如果有control和treatment分组）
            cost_savings_percentage = None
            quality_difference = None

            if "control" in groups and "treatment" in groups:
                if avg_cost_by_group["control"] > 0 and avg_cost_by_group["treatment"] > 0:
                    cost_savings_percentage = (
                        (avg_cost_by_group["control"] - avg_cost_by_group["treatment"])
                        / avg_cost_by_group["control"]
                        * 100
                    )

                if avg_quality_by_group["control"] > 0 and avg_quality_by_group["treatment"] > 0:
                    quality_difference = (
                        avg_quality_by_group["treatment"] - avg_quality_by_group["control"]
                    )

            # 确定统计周期
            if records:
                period_start = min(record.recorded_at.date() for record in records)
                period_end = max(record.recorded_at.date() for record in records)
            else:
                period_start = date.today()
                period_end = date.today()

            summary = ExperimentSummary(
                experiment_id=experiment_id,
                period_start=period_start,
                period_end=period_end,
                total_samples=total_samples,
                group_samples=group_samples,
                avg_cost_by_group=avg_cost_by_group,
                total_cost_by_group=total_cost_by_group,
                cost_savings_percentage=cost_savings_percentage,
                avg_quality_by_group=avg_quality_by_group,
                quality_difference=quality_difference,
                avg_execution_time_by_group=avg_execution_time_by_group,
                avg_tokens_by_group=avg_tokens_by_group,
                data_quality_distribution=quality_counts,
            )

            return summary

        except Exception as e:
            logger.error(f"获取实验摘要失败: {e}")
            return None

    def cleanup(self, days_to_keep: int = 90):
        """清理旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.isoformat()

            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM experiment_records WHERE recorded_at < ?", (cutoff_str,))

            deleted_count = cursor.rowcount
            self.conn.commit()

            logger.info(f"实验记录清理完成，删除了{deleted_count}条{days_to_keep}天前的记录")
            return deleted_count

        except Exception as e:
            logger.error(f"清理实验记录失败: {e}")
            self.conn.rollback()
            return 0


# ==================== 实验记录器主类 ====================


class ExperimentLogger:
    """实验记录器主类"""

    def __init__(self, storage_backend: Optional[ExperimentStorageBackend] = None):
        if storage_backend is None:
            storage_backend = SQLiteExperimentStorageBackend()
        self.storage = storage_backend

        # 导入实验路由器（延迟导入，避免循环依赖）
        self.experiment_router = None

    def _get_experiment_router(self):
        """获取实验路由器（延迟导入）"""
        if self.experiment_router is None:
            from .experiment_router import get_experiment_router

            self.experiment_router = get_experiment_router()
        return self.experiment_router

    def log_experiment_assignment(
        self,
        task_kind: str,
        request_id: str,
        assignment_metadata: Dict[str, Any],
        input_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """记录实验分配

        Args:
            task_kind: 任务类型
            request_id: 请求ID
            assignment_metadata: 实验分配元数据（来自实验路由器）
            input_context: 输入上下文（可选，包含prompt等信息）

        Returns:
            实验记录ID 或 None（如果记录失败）
        """
        try:
            # 从assignment_metadata提取实验信息
            experiment_id = assignment_metadata.get("experiment_id")
            group_name = assignment_metadata.get("group_name")

            if not experiment_id or not group_name:
                logger.warning("实验分配元数据缺少必要字段")
                return None

            # 创建实验记录
            record_id = f"exp_{request_id}"

            # 提取输入信息
            input_prompt = None
            input_summary = None
            if input_context:
                input_prompt = input_context.get("prompt")
                if input_prompt and len(input_prompt) > 1000:
                    input_summary = input_prompt[:500] + "..."
                elif input_prompt:
                    input_summary = input_prompt[:100]

            record = ExperimentRecord(
                id=record_id,
                experiment_id=experiment_id,
                request_id=request_id,
                cost_record_id=None,  # 将在执行后关联
                group_name=group_name,
                assignment_metadata=assignment_metadata,
                task_kind=task_kind,
                input_prompt=input_prompt,
                output_response=None,
                input_summary=input_summary,
                output_summary=None,
                execution_time=None,
                tokens_used=None,
                cost_info=None,
                quality_score=None,
                quality_breakdown=None,
                quality_assessor=None,
                status=ExperimentRecordStatus.ASSIGNED.value,
                metadata={
                    "input_context": input_context or {},
                    "recorded_at": datetime.now().isoformat(),
                },
            )

            # 保存记录
            success = self.storage.record_experiment(record)

            if success:
                logger.info(f"实验分配已记录: {record_id} - {experiment_id}/{group_name}")
                return record_id
            else:
                logger.error(f"实验分配记录失败: {record_id}")
                return None

        except Exception as e:
            logger.error(f"记录实验分配失败: {e}")
            return None

    def log_experiment_execution(
        self,
        request_id: str,
        execution_result: Dict[str, Any],
        cost_record_id: Optional[str] = None,
    ) -> bool:
        """记录实验执行结果

        Args:
            request_id: 请求ID
            execution_result: 执行结果，包含：
                - output_response: 输出响应
                - execution_time: 执行时间（秒）
                - tokens_used: tokens使用量 {"input": int, "output": int}
                - cost_info: 成本信息
                - metadata: 额外元数据
            cost_record_id: 关联的成本记录ID

        Returns:
            是否成功记录
        """
        try:
            # 首先查找现有的实验记录
            records = self.storage.get_experiment_records(request_id=request_id, limit=1)

            if not records:
                logger.warning(f"未找到请求ID对应的实验记录: {request_id}")
                return False

            record = records[0]

            # 更新记录字段
            record.output_response = execution_result.get("output_response")
            if record.output_response and len(record.output_response) > 1000:
                record.output_summary = record.output_response[:500] + "..."
            elif record.output_response:
                record.output_summary = record.output_response[:100]

            record.execution_time = execution_result.get("execution_time")
            record.tokens_used = execution_result.get("tokens_used")
            record.cost_info = execution_result.get("cost_info")

            # 确定成本记录ID（优先级：传入参数 > execution_result > 查询）
            final_cost_record_id = cost_record_id

            # 如果未传入cost_record_id，检查execution_result中是否有
            if not final_cost_record_id:
                final_cost_record_id = execution_result.get("cost_record_id")

            # 如果仍然没有，尝试查询数据库
            if not final_cost_record_id and record.cost_record_id is None:
                final_cost_record_id = self.query_cost_record_for_experiment(request_id)
                if final_cost_record_id:
                    logger.info(
                        f"通过查询找到关联的成本记录: {final_cost_record_id} for request_id: {request_id}"
                    )

            record.cost_record_id = final_cost_record_id

            # 更新状态
            if record.output_response or record.cost_info:
                record.status = ExperimentRecordStatus.EXECUTED.value

            # 更新元数据
            if "metadata" in execution_result:
                record.metadata.update(execution_result["metadata"])

            # 保存更新
            success = self.storage.record_experiment(record)

            if success:
                logger.info(f"实验执行已记录: {record.id} - 执行时间: {record.execution_time}s")
                return True
            else:
                logger.error(f"实验执行记录失败: {record.id}")
                return False

        except Exception as e:
            logger.error(f"记录实验执行失败: {e}")
            return False

    def query_cost_record_for_experiment(self, request_id: str) -> Optional[str]:
        """为实验记录查询关联的成本记录ID

        如果cost_record_id为空，尝试通过request_id在成本记录表中查找。
        支持多种匹配策略：
        1. 精确匹配request_id
        2. 前缀匹配（exp_req_...）
        3. 时间戳匹配（同时间窗口内的记录）

        Args:
            request_id: 实验记录的请求ID

        Returns:
            关联的成本记录ID，如果未找到则返回None
        """
        try:
            # 首先尝试精确匹配
            cursor = self.storage.conn.cursor()

            # 直接查询成本记录表
            cursor.execute(
                """
                SELECT id, request_id, timestamp
                FROM cost_records
                WHERE request_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """,
                (request_id,),
            )

            row = cursor.fetchone()
            if row:
                logger.debug(f"通过精确匹配找到成本记录: {row['id']} for request_id: {request_id}")
                return row["id"]

            # 如果精确匹配失败，尝试前缀匹配（实验request_id可能被包装或修改）
            # 实验request_id格式: exp_run_YYYYMMDD_HHMMSS_<batch>_<index>
            # 成本request_id格式: exp_req_YYYYMMDD_HHMMSS_<uuid>
            # 尝试匹配时间戳部分

            # 提取时间戳部分：YYYYMMDD_HHMMSS
            import re

            timestamp_match = re.search(r"(\d{8}_\d{6})", request_id)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)

                # 查找包含相同时间戳的成本记录
                cursor.execute(
                    """
                    SELECT id, request_id, timestamp
                    FROM cost_records
                    WHERE request_id LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """,
                    (f"%{timestamp_str}%",),
                )

                row = cursor.fetchone()
                if row:
                    logger.debug(
                        f"通过时间戳匹配找到成本记录: {row['id']} for timestamp: {timestamp_str}"
                    )
                    return row["id"]

            # 如果还是找不到，尝试时间窗口匹配
            # 首先获取实验记录的时间戳
            cursor.execute(
                """
                SELECT recorded_at
                FROM experiment_records
                WHERE request_id = ?
                LIMIT 1
            """,
                (request_id,),
            )

            exp_row = cursor.fetchone()
            if exp_row:
                exp_timestamp = exp_row["recorded_at"]

                # 查找5分钟时间窗口内的成本记录
                cursor.execute(
                    """
                    SELECT id, request_id, timestamp
                    FROM cost_records
                    WHERE timestamp BETWEEN datetime(?, '-5 minutes') AND datetime(?, '+5 minutes')
                    ORDER BY ABS(strftime('%s', timestamp) - strftime('%s', ?))
                    LIMIT 1
                """,
                    (exp_timestamp, exp_timestamp, exp_timestamp),
                )

                row = cursor.fetchone()
                if row:
                    logger.debug(
                        f"通过时间窗口匹配找到成本记录: {row['id']} (实验时间: {exp_timestamp})"
                    )
                    return row["id"]

            logger.warning(f"未找到与request_id '{request_id}' 关联的成本记录")
            return None

        except Exception as e:
            logger.error(f"查询成本记录失败: {e}")
            return None

    def log_experiment_quality(self, request_id: str, quality_assessment: Dict[str, Any]) -> bool:
        """记录实验质量评估

        Args:
            request_id: 请求ID
            quality_assessment: 质量评估结果，包含：
                - quality_score: 总体质量评分（0-10）
                - quality_breakdown: 分解评分 {"correctness": 9.0, "style": 8.5, ...}
                - quality_assessor: 评估器类型 ("human"/"auto"/"hybrid")
                - metadata: 额外元数据

        Returns:
            是否成功记录
        """
        try:
            # 首先查找现有的实验记录
            records = self.storage.get_experiment_records(request_id=request_id, limit=1)

            if not records:
                logger.warning(f"未找到请求ID对应的实验记录: {request_id}")
                return False

            record = records[0]

            # 更新质量评估字段
            record.quality_score = quality_assessment.get("quality_score")
            record.quality_breakdown = quality_assessment.get("quality_breakdown")
            record.quality_assessor = quality_assessment.get("quality_assessor", "auto")

            # 更新状态
            if record.quality_score is not None:
                record.status = ExperimentRecordStatus.EVALUATED.value

            # 更新元数据
            if "metadata" in quality_assessment:
                record.metadata.update(quality_assessment["metadata"])

            # 保存更新
            success = self.storage.record_experiment(record)

            if success:
                logger.info(f"实验质量已记录: {record.id} - 质量评分: {record.quality_score}")
                return True
            else:
                logger.error(f"实验质量记录失败: {record.id}")
                return False

        except Exception as e:
            logger.error(f"记录实验质量失败: {e}")
            return False

    def complete_experiment(self, request_id: str) -> bool:
        """标记实验完成

        Args:
            request_id: 请求ID

        Returns:
            是否成功更新
        """
        try:
            # 首先查找现有的实验记录
            records = self.storage.get_experiment_records(request_id=request_id, limit=1)

            if not records:
                logger.warning(f"未找到请求ID对应的实验记录: {request_id}")
                return False

            record = records[0]
            record.status = ExperimentRecordStatus.COMPLETED.value

            # 保存更新
            success = self.storage.record_experiment(record)

            if success:
                logger.info(f"实验标记为完成: {record.id}")
                return True
            else:
                logger.error(f"实验完成标记失败: {record.id}")
                return False

        except Exception as e:
            logger.error(f"标记实验完成失败: {e}")
            return False

    def get_experiment_status(self, experiment_id: str) -> Dict[str, Any]:
        """获取实验状态报告

        Returns:
            实验状态报告字典
        """
        try:
            # 获取实验摘要
            summary = self.storage.get_experiment_summary(experiment_id)

            if not summary:
                return {"error": f"未找到实验 {experiment_id} 的数据"}

            # 获取详细记录
            records = self.storage.get_experiment_records(experiment_id=experiment_id, limit=100)

            # 状态分布
            status_counts = {}
            for record in records:
                status_counts[record.status] = status_counts.get(record.status, 0) + 1

            # 数据质量分布
            quality_distribution = summary.data_quality_distribution

            report = {
                "experiment_id": experiment_id,
                "period_start": summary.period_start.isoformat(),
                "period_end": summary.period_end.isoformat(),
                "total_samples": summary.total_samples,
                "group_samples": summary.group_samples,
                "status_distribution": status_counts,
                "data_quality_distribution": quality_distribution,
                "cost_analysis": {
                    "avg_cost_by_group": summary.avg_cost_by_group,
                    "total_cost_by_group": summary.total_cost_by_group,
                    "cost_savings_percentage": summary.cost_savings_percentage,
                },
                "quality_analysis": {
                    "avg_quality_by_group": summary.avg_quality_by_group,
                    "quality_difference": summary.quality_difference,
                },
                "performance_analysis": {
                    "avg_execution_time_by_group": summary.avg_execution_time_by_group,
                    "avg_tokens_by_group": summary.avg_tokens_by_group,
                },
                "recommendations": [],
            }

            # 生成建议
            if summary.total_samples < 50:
                report["recommendations"].append(
                    {
                        "priority": "high",
                        "action": "扩大实验样本规模",
                        "reason": f"当前仅{summary.total_samples}个样本，需要至少50个样本进行初步分析",
                    }
                )

            if summary.cost_savings_percentage and summary.cost_savings_percentage > 20:
                report["recommendations"].append(
                    {
                        "priority": "medium",
                        "action": "考虑扩大实验组比例",
                        "reason": f"实验组成本降低{summary.cost_savings_percentage:.1f}%，效果显著",
                    }
                )

            if (
                "incomplete" in quality_distribution
                and quality_distribution["incomplete"] > summary.total_samples * 0.3
            ):
                report["recommendations"].append(
                    {
                        "priority": "high",
                        "action": "改善数据收集质量",
                        "reason": f"{quality_distribution['incomplete']}个样本数据不完整，影响分析可靠性",
                    }
                )

            return report

        except Exception as e:
            logger.error(f"获取实验状态失败: {e}")
            return {"error": str(e)}


# ==================== 全局实例 ====================


_experiment_logger_instance: Optional[ExperimentLogger] = None


def get_experiment_logger() -> ExperimentLogger:
    """获取全局实验记录器实例"""
    global _experiment_logger_instance
    if _experiment_logger_instance is None:
        _experiment_logger_instance = ExperimentLogger()
    return _experiment_logger_instance


# ==================== 命令行接口 ====================


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="实验记录器命令行接口")
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # 状态检查命令
    status_parser = subparsers.add_parser("status", help="检查实验状态")
    status_parser.add_argument("--experiment-id", required=True, help="实验ID")

    # 数据导出命令
    export_parser = subparsers.add_parser("export", help="导出实验数据")
    export_parser.add_argument("--experiment-id", required=True, help="实验ID")
    export_parser.add_argument("--output", default="experiment_data.json", help="输出文件路径")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json", help="输出格式")

    # 清理命令
    cleanup_parser = subparsers.add_parser("cleanup", help="清理旧数据")
    cleanup_parser.add_argument("--days", type=int, default=90, help="保留天数")

    args = parser.parse_args()

    logger = get_experiment_logger()

    if args.command == "status":
        status = logger.get_experiment_status(args.experiment_id)
        print(json.dumps(status, indent=2, ensure_ascii=False))

    elif args.command == "export":
        records = logger.storage.get_experiment_records(
            experiment_id=args.experiment_id, limit=1000
        )

        if args.format == "json":
            data = [record.to_dict() for record in records]
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"导出完成: {len(data)} 条记录 -> {args.output}")

        elif args.format == "csv":
            import csv

            # 简化为CSV格式
            with open(args.output, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                # 写入标题行
                writer.writerow(
                    [
                        "id",
                        "experiment_id",
                        "group_name",
                        "task_kind",
                        "input_summary",
                        "output_summary",
                        "execution_time",
                        "quality_score",
                        "recorded_at",
                    ]
                )
                # 写入数据行
                for record in records:
                    writer.writerow(
                        [
                            record.id,
                            record.experiment_id,
                            record.group_name,
                            record.task_kind,
                            record.input_summary or "",
                            record.output_summary or "",
                            record.execution_time or 0,
                            record.quality_score or 0,
                            record.recorded_at.isoformat(),
                        ]
                    )
            print(f"导出完成: {len(records)} 条记录 -> {args.output}")

    elif args.command == "cleanup":
        deleted = logger.storage.cleanup(args.days)
        print(f"清理完成，删除了 {deleted} 条{args.days}天前的记录")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
