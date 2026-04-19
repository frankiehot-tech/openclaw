#!/usr/bin/env python3
"""
迁移监控器
监控分阶段迁移的进度、成本节省、质量指标和风险。

功能：
1. 实时监控迁移实验数据
2. 跟踪成本节省效果和质量一致性
3. 检测异常和风险信号
4. 生成迁移进度报告
5. 触发告警和自动回滚

版本: 1.0
创建日期: 2026-04-17
作者: Claude (AI助手)
"""

import json
import logging
import sqlite3
import statistics
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# 导入请求ID生成器
try:
    from agent.core.request_id_generator import (
        RequestIDGenerator,
        get_request_id_generator,
    )

    REQUEST_ID_GENERATOR_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("请求ID生成器不可用，将使用基本关联策略")
    REQUEST_ID_GENERATOR_AVAILABLE = False

logger = logging.getLogger(__name__)


class MigrationAlertLevel(Enum):
    """迁移告警等级"""

    INFO = "info"  # 信息性通知
    WARNING = "warning"  # 警告，需要关注
    CRITICAL = "critical"  # 严重，需要立即处理


class MigrationMetric(Enum):
    """迁移监控指标"""

    COST_SAVINGS = "cost_savings"  # 成本节省百分比
    QUALITY_CONSISTENCY = "quality_consistency"  # 质量一致性
    ERROR_RATE_DIFF = "error_rate_diff"  # 错误率差异
    REQUEST_VOLUME = "request_volume"  # 请求量
    RESPONSE_TIME = "response_time"  # 响应时间
    USER_SATISFACTION = "user_satisfaction"  # 用户满意度（代理指标）


@dataclass
class MigrationAlert:
    """迁移告警"""

    alert_id: str
    level: MigrationAlertLevel
    metric: MigrationMetric
    message: str
    value: float
    threshold: float
    timestamp: datetime
    experiment_id: str
    phase_number: int
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class MigrationMetrics:
    """迁移指标数据"""

    timestamp: datetime
    experiment_id: str
    phase_number: int

    # 成本指标
    total_requests: int
    dashscope_requests: int
    deepseek_requests: int
    dashscope_cost: float
    deepseek_cost: float
    cost_savings_percent: float

    # 质量指标
    dashscope_quality_avg: float
    deepseek_quality_avg: float
    quality_consistency: float  # 新/原provider质量比

    # 性能指标
    dashscope_error_rate: float
    deepseek_error_rate: float
    error_rate_diff: float

    dashscope_response_time_avg: float
    deepseek_response_time_avg: float
    response_time_diff_percent: float

    # 元数据
    monitoring_window_minutes: int = 60  # 监控窗口（分钟）


class MigrationMonitor:
    """迁移监控器"""

    def __init__(self, db_path: str, check_interval_minutes: int = 15):
        """
        初始化迁移监控器

        Args:
            db_path: 成本跟踪数据库路径
            check_interval_minutes: 检查间隔（分钟）
        """
        self.db_path = db_path
        self.check_interval = check_interval_minutes
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.alerts: List[MigrationAlert] = []
        self.metrics_history: List[MigrationMetrics] = []

        # 告警阈值配置
        self.alert_thresholds = {
            MigrationMetric.COST_SAVINGS: {
                "warning": {"min": 0.5, "max": 0.7},  # 50-70%节省为警告
                "critical": {"min": 0.0, "max": 0.5},  # 低于50%为严重
            },
            MigrationMetric.QUALITY_CONSISTENCY: {
                "warning": {"min": 0.85, "max": 0.9},  # 85-90%一致性为警告
                "critical": {"min": 0.0, "max": 0.85},  # 低于85%为严重
            },
            MigrationMetric.ERROR_RATE_DIFF: {
                "warning": {"min": 0.02, "max": 0.05},  # 2-5%差异为警告
                "critical": {"min": 0.05, "max": 1.0},  # 高于5%为严重
            },
            MigrationMetric.RESPONSE_TIME: {
                "warning": {"min": 1.2, "max": 1.5},  # 20-50%增加为警告
                "critical": {"min": 1.5, "max": 10.0},  # 高于50%为严重
            },
        }

    def start_monitoring(self) -> bool:
        """启动监控"""
        if self.running:
            logger.warning("监控器已在运行")
            return False

        logger.info(f"启动迁移监控器，检查间隔: {self.check_interval}分钟")
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        return True

    def stop_monitoring(self) -> bool:
        """停止监控"""
        logger.info("停止迁移监控器")
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=30)
        return True

    def _monitoring_loop(self) -> None:
        """监控循环"""
        while self.running:
            try:
                # 1. 收集当前迁移指标
                current_metrics = self.collect_migration_metrics()
                if current_metrics:
                    self.metrics_history.append(current_metrics)

                    # 2. 检查告警条件
                    self._check_alerts(current_metrics)

                    # 3. 生成监控报告
                    if len(self.metrics_history) % 4 == 0:  # 每4次检查生成报告
                        self._generate_monitoring_report()

                    # 4. 保存状态
                    self._save_monitoring_state()

                # 等待下一个检查周期
                time.sleep(self.check_interval * 60)

            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(60)  # 出错后等待1分钟

    def collect_migration_metrics(
        self, experiment_id: str = None, lookback_hours: int = 24
    ) -> Optional[MigrationMetrics]:
        """收集迁移指标

        Args:
            experiment_id: 实验ID，如果为None则自动检测迁移实验
            lookback_hours: 回溯时间（小时）
        """
        """收集迁移指标"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 计算时间范围
            lookback_minutes = lookback_hours * 60
            since_time = datetime.now() - timedelta(minutes=lookback_minutes)

            # 自动检测迁移实验ID
            if experiment_id is None:
                # 查找包含"migration"或"deepseek"的实验
                cursor.execute("""
                    SELECT DISTINCT experiment_id
                    FROM experiment_records
                    WHERE experiment_id LIKE '%migration%'
                       OR experiment_id LIKE '%deepseek%'
                    LIMIT 1
                """)
                result = cursor.fetchone()
                if result:
                    experiment_id = result["experiment_id"]
                    logger.info(f"自动检测到迁移实验: {experiment_id}")
                else:
                    # 使用现有的实验
                    experiment_id = "coding_plan_deepseek_coder_ab"
                    logger.info(f"使用默认实验: {experiment_id}")

            logger.info(
                f"收集迁移指标: experiment_id={experiment_id}, lookback={lookback_hours}小时"
            )

            # 查询迁移实验相关的指标数据
            # 从experiment_records表中获取质量、性能指标
            # 从cost_records表中获取成本数据（使用增强关联）
            query = """
            SELECT
                e.group_name as provider_id,
                e.request_id as request_id,
                COUNT(*) as request_count,

                -- 从cost_records获取成本数据（如果通过cost_record_id关联成功）
                COALESCE(SUM(c.estimated_cost), 0.0) as direct_cost,

                -- 质量指标
                AVG(e.quality_score) as avg_quality,

                -- 错误计数（quality_score为NULL或0视为错误）
                SUM(CASE WHEN e.quality_score IS NULL OR e.quality_score <= 0 THEN 1 ELSE 0 END) as error_count,

                -- 执行时间（响应时间代理）
                AVG(e.execution_time) as avg_response_time,

                -- 用于诊断：统计有多少记录有cost_record_id
                SUM(CASE WHEN e.cost_record_id IS NOT NULL THEN 1 ELSE 0 END) as records_with_cost_id,
                SUM(CASE WHEN e.cost_record_id IS NULL THEN 1 ELSE 0 END) as records_without_cost_id

            FROM experiment_records e
            LEFT JOIN cost_records c ON e.cost_record_id = c.id

            WHERE e.experiment_id = ?
              AND e.recorded_at >= ?
              AND e.task_kind = 'coding_plan'
              AND e.status = 'completed'

            GROUP BY e.group_name
            """

            # 首先查询实验记录（不聚合）
            exp_query = """
            SELECT
                id,
                group_name,
                request_id,
                quality_score,
                execution_time,
                cost_record_id,
                recorded_at
            FROM experiment_records
            WHERE experiment_id = ?
              AND recorded_at >= ?
              AND task_kind = 'coding_plan'
              AND status = 'completed'
            ORDER BY recorded_at
            """
            cursor.execute(exp_query, (experiment_id, since_time.isoformat()))
            exp_rows = cursor.fetchall()

            if not exp_rows:
                logger.warning(f"在最近{lookback_hours}小时内未找到迁移实验数据")
                # 记录一下表中有哪些实验数据
                debug_query = "SELECT DISTINCT experiment_id, group_name FROM experiment_records WHERE recorded_at >= ? LIMIT 5"
                cursor.execute(debug_query, (since_time.isoformat(),))
                debug_rows = cursor.fetchall()
                logger.info(f"可用的实验数据: {debug_rows}")
                conn.close()
                return None

            logger.info(f"找到 {len(exp_rows)} 个实验记录")

            # 诊断：统计cost_record_id情况
            records_with_cost_id = sum(1 for r in exp_rows if r["cost_record_id"])
            records_without_cost_id = len(exp_rows) - records_with_cost_id
            logger.info(
                f"成本记录关联情况: {records_with_cost_id} 个有cost_record_id, {records_without_cost_id} 个无cost_record_id"
            )

            # 实验分组名到provider的映射
            group_to_provider = {
                # 迁移实验分组
                "original": "dashscope",  # original组对应DashScope
                "migrated": "deepseek",  # migrated组对应DeepSeek
                # A/B实验分组
                "control": "dashscope",  # control组对应DashScope
                "treatment": "deepseek",  # treatment组对应DeepSeek
            }

            # 尝试匹配成本记录
            cost_matches = {}
            if records_without_cost_id > 0 and REQUEST_ID_GENERATOR_AVAILABLE:
                logger.info(
                    f"尝试为 {records_without_cost_id} 个无cost_record_id的记录匹配成本记录..."
                )
                cost_matches = self._find_matching_cost_records(cursor, exp_rows, lookback_hours)
                if cost_matches:
                    logger.info(f"成功匹配 {len(cost_matches)} 个成本记录")
                else:
                    logger.warning("无法匹配任何成本记录")

            # 初始化指标
            metrics = {
                "dashscope": {
                    "requests": 0,
                    "cost": 0.0,
                    "quality_sum": 0.0,
                    "errors": 0,
                    "response_time_sum": 0.0,
                },
                "deepseek": {
                    "requests": 0,
                    "cost": 0.0,
                    "quality_sum": 0.0,
                    "errors": 0,
                    "response_time_sum": 0.0,
                },
            }

            # 处理每个实验记录
            for record in exp_rows:
                group_name = record["group_name"]
                provider = group_to_provider.get(group_name)
                if provider not in metrics:
                    logger.warning(f"未知的实验分组: {group_name}")
                    continue

                # 增加请求计数
                metrics[provider]["requests"] += 1

                # 质量评分
                quality = record["quality_score"] or 0.0
                metrics[provider]["quality_sum"] += quality
                if quality <= 0:
                    metrics[provider]["errors"] += 1

                # 响应时间
                exec_time = record["execution_time"] or 0.0
                metrics[provider]["response_time_sum"] += exec_time

                # 成本数据
                cost = 0.0
                request_id = record["request_id"]

                # 首先检查是否有直接的cost_record_id关联
                cost_record_id = record["cost_record_id"]
                if cost_record_id:
                    # 查询成本记录
                    cost_query = "SELECT estimated_cost FROM cost_records WHERE id = ?"
                    cursor.execute(cost_query, (cost_record_id,))
                    cost_row = cursor.fetchone()
                    if cost_row:
                        cost = cost_row["estimated_cost"] or 0.0

                # 如果没有通过cost_record_id找到成本，尝试通过request_id匹配
                elif request_id and request_id in cost_matches:
                    cost = cost_matches[request_id].get("estimated_cost", 0.0)
                    # 可选：更新experiment_records表中的cost_record_id（如果需要）
                    # 这里暂时只记录日志
                    logger.debug(f"通过request_id匹配找到成本: {request_id} -> {cost}")

                metrics[provider]["cost"] += cost

            # 计算平均值
            for provider in metrics:
                req = metrics[provider]["requests"]
                if req > 0:
                    metrics[provider]["quality_avg"] = metrics[provider]["quality_sum"] / req
                    metrics[provider]["response_time_avg"] = (
                        metrics[provider]["response_time_sum"] / req
                    )
                else:
                    metrics[provider]["quality_avg"] = 0.0
                    metrics[provider]["response_time_avg"] = 0.0

            total_requests = metrics["dashscope"]["requests"] + metrics["deepseek"]["requests"]

            # 调试日志：查看收集到的数据
            logger.info(f"收集到的数据:")
            logger.info(
                f"  DashScope: {metrics['dashscope']['requests']} 请求, 成本: {metrics['dashscope']['cost']:.4f}, 质量: {metrics['dashscope']['quality_avg']:.3f}"
            )
            logger.info(
                f"  DeepSeek: {metrics['deepseek']['requests']} 请求, 成本: {metrics['deepseek']['cost']:.4f}, 质量: {metrics['deepseek']['quality_avg']:.3f}"
            )
            logger.info(f"总请求数: {total_requests}")
            logger.info(
                f"成本匹配统计: {len(cost_matches)}/{records_without_cost_id} 个无cost_record_id的记录匹配成功"
            )

            # 计算指标
            ds = metrics["dashscope"]
            dk = metrics["deepseek"]

            # 成本节省百分比
            if ds["requests"] > 0 and dk["requests"] > 0:
                ds_avg_cost = ds["cost"] / ds["requests"] if ds["cost"] > 0 else 0.0
                dk_avg_cost = dk["cost"] / dk["requests"] if dk["cost"] > 0 else 0.0
                if ds_avg_cost > 0:
                    cost_savings = (ds_avg_cost - dk_avg_cost) / ds_avg_cost
                else:
                    cost_savings = 0.0
            else:
                cost_savings = 0.0

            # 质量一致性
            if ds["quality_avg"] > 0:
                quality_consistency = dk["quality_avg"] / ds["quality_avg"]
            else:
                quality_consistency = 1.0 if dk["quality_avg"] > 0 else 0.0

            # 错误率差异
            ds_error_rate = ds["errors"] / ds["requests"] if ds["requests"] > 0 else 0.0
            dk_error_rate = dk["errors"] / dk["requests"] if dk["requests"] > 0 else 0.0
            error_rate_diff = dk_error_rate - ds_error_rate

            # 响应时间差异百分比
            if ds["response_time_avg"] > 0:
                response_time_diff = (dk["response_time_avg"] - ds["response_time_avg"]) / ds[
                    "response_time_avg"
                ]
            else:
                response_time_diff = 0.0

            conn.close()

            return MigrationMetrics(
                timestamp=datetime.now(),
                experiment_id=experiment_id,
                phase_number=1,  # 当前为第一阶段
                total_requests=total_requests,
                dashscope_requests=ds["requests"],
                deepseek_requests=dk["requests"],
                dashscope_cost=ds["cost"],
                deepseek_cost=dk["cost"],
                cost_savings_percent=cost_savings * 100,
                dashscope_quality_avg=ds["quality_avg"],
                deepseek_quality_avg=dk["quality_avg"],
                quality_consistency=quality_consistency,
                dashscope_error_rate=ds_error_rate,
                deepseek_error_rate=dk_error_rate,
                error_rate_diff=error_rate_diff,
                dashscope_response_time_avg=ds["response_time_avg"],
                deepseek_response_time_avg=dk["response_time_avg"],
                response_time_diff_percent=response_time_diff * 100,
                monitoring_window_minutes=lookback_minutes,
            )

        except Exception as e:
            logger.error(f"收集迁移指标失败: {e}")
            return None

    def _find_matching_cost_records(
        self, cursor: sqlite3.Cursor, experiment_records: List[sqlite3.Row], lookback_hours: int
    ) -> Dict[str, Dict[str, Any]]:
        """为实验记录查找匹配的成本记录

        使用多层fallback策略：
        1. 直接通过cost_record_id匹配（如果可用）
        2. 通过request_id精确匹配
        3. 通过request_id前缀匹配（标准格式）
        4. 通过时间窗口匹配

        Args:
            cursor: 数据库游标
            experiment_records: 实验记录列表
            lookback_hours: 回溯时间

        Returns:
            映射字典: experiment_id -> 成本记录信息
        """
        cost_matches = {}
        matched_cost_ids = set()  # 跟踪已匹配的成本记录ID，避免重复分配

        if not REQUEST_ID_GENERATOR_AVAILABLE:
            logger.warning("请求ID生成器不可用，跳过成本记录匹配")
            return cost_matches

        try:
            generator = get_request_id_generator()

            # 收集所有需要匹配的request_id
            exp_request_ids = []
            for record in experiment_records:
                try:
                    request_id = record["request_id"]
                    if request_id:
                        exp_request_ids.append(request_id)
                except (KeyError, IndexError):
                    # 如果request_id字段不存在，跳过
                    continue

            if not exp_request_ids:
                logger.debug("实验记录中没有request_id")
                return cost_matches

            logger.info(f"尝试为 {len(exp_request_ids)} 个实验记录匹配成本记录")

            # 策略1: 直接request_id精确匹配
            placeholders = ",".join(["?"] * len(exp_request_ids))
            query1 = f"""
                SELECT id, request_id, provider_id, estimated_cost, timestamp
                FROM cost_records
                WHERE request_id IN ({placeholders})
            """
            cursor.execute(query1, exp_request_ids)
            direct_matches = cursor.fetchall()

            for match in direct_matches:
                cost_matches[match["request_id"]] = {
                    "cost_record_id": match["id"],
                    "estimated_cost": match["estimated_cost"],
                    "provider_id": match["provider_id"],
                    "match_type": "direct_request_id",
                    "timestamp": match["timestamp"],
                }
                matched_cost_ids.add(match["id"])

            # 策略2: 时间戳匹配（对于标准格式的request_id）
            # 提取时间戳部分（如20240417_143025）进行匹配
            timestamp_matches = {}
            for request_id in exp_request_ids:
                # 使用parse方法检查是否为标准格式并提取时间戳
                parsed = generator.parse(request_id)
                logger.debug(
                    f"解析请求ID {request_id}: 标准格式={parsed.get('is_standard_format', False)}, 时间戳字符串={parsed.get('timestamp_str', 'N/A')}"
                )
                if parsed.get("is_standard_format", False) and parsed.get("timestamp_str"):
                    timestamp_str = parsed["timestamp_str"]
                    timestamp_matches[request_id] = {
                        "timestamp_str": timestamp_str,
                        "timestamp": parsed.get("timestamp"),
                    }

            logger.info(f"时间戳匹配: 找到 {len(timestamp_matches)} 个标准格式的实验记录")
            if timestamp_matches:
                # 查找成本记录中时间戳相近的条目
                # 使用120分钟时间窗口进行匹配（2小时）
                time_window_minutes = 120

                for exp_request_id, exp_info in timestamp_matches.items():
                    logger.debug(
                        f"处理实验记录 {exp_request_id}, 时间戳: {exp_info['timestamp_str']}"
                    )
                    if exp_request_id in cost_matches:
                        logger.debug(f"  已通过直接匹配找到，跳过")
                        continue  # 已经通过直接匹配找到

                    if not exp_info["timestamp"]:
                        logger.debug(f"  无法解析时间戳，跳过")
                        continue  # 无法解析时间戳

                    # 查找时间窗口内的成本记录，排除已匹配的成本记录
                    exp_time = exp_info["timestamp"]

                    # 构建排除条件
                    exclude_condition = ""
                    exclude_params = []
                    if matched_cost_ids:
                        placeholders = ",".join(["?"] * len(matched_cost_ids))
                        exclude_condition = f" AND id NOT IN ({placeholders})"
                        exclude_params = list(matched_cost_ids)

                    time_query = f"""
                        SELECT id, request_id, provider_id, estimated_cost, timestamp
                        FROM cost_records
                        WHERE datetime(timestamp) BETWEEN datetime(?, ?) AND datetime(?, ?)
                        {exclude_condition}
                        ORDER BY ABS(strftime('%s', timestamp) - strftime('%s', ?))
                        LIMIT 1
                    """
                    cursor.execute(
                        time_query,
                        (
                            exp_time.isoformat(),
                            f"-{time_window_minutes} minutes",
                            exp_time.isoformat(),
                            f"+{time_window_minutes} minutes",
                            *exclude_params,
                            exp_time.isoformat(),
                        ),
                    )
                    time_match = cursor.fetchone()
                    logger.debug(f"  查询结果: {'找到匹配' if time_match else '无匹配'}")

                    if time_match:
                        # 验证时间戳是否确实相近（使用更精确的检查）
                        try:
                            match_time_str = datetime.fromisoformat(
                                time_match["timestamp"].replace("Z", "+00:00")
                            )
                            time_diff = abs((exp_time - match_time_str).total_seconds())
                            if time_diff <= time_window_minutes * 60:  # 确保在窗口内
                                cost_matches[exp_request_id] = {
                                    "cost_record_id": time_match["id"],
                                    "estimated_cost": time_match["estimated_cost"],
                                    "provider_id": time_match["provider_id"],
                                    "match_type": "timestamp_match",
                                    "timestamp": time_match["timestamp"],
                                }
                                logger.debug(
                                    f"时间戳匹配: {exp_request_id} ({exp_time}) -> {time_match['request_id']} ({match_time_str}), 时间差: {time_diff:.0f}秒"
                                )
                                matched_cost_ids.add(time_match["id"])
                        except Exception as e:
                            logger.debug(f"时间戳匹配时间解析错误: {e}")

            # 策略3: 时间窗口匹配（如果前两种策略都没有匹配到）
            # 查找最近X小时内的成本记录，按时间戳相近匹配
            if len(cost_matches) < len(exp_request_ids) / 2:  # 如果匹配率低于50%
                logger.info("尝试时间窗口匹配...")
                # 计算时间窗口（由于实验记录和成本记录时间不匹配，扩大窗口）
                time_window_minutes = 120  # 2小时窗口

                for record in experiment_records:
                    try:
                        record_id = record["id"]
                        record_request_id = record["request_id"]
                        record_time = record["recorded_at"]
                    except (KeyError, IndexError):
                        continue

                    if not record_time or record_request_id in cost_matches:
                        continue

                    # 查找时间窗口内的成本记录，排除已匹配的成本记录
                    # 构建排除条件
                    exclude_condition = ""
                    exclude_params = []
                    if matched_cost_ids:
                        placeholders = ",".join(["?"] * len(matched_cost_ids))
                        exclude_condition = f" AND id NOT IN ({placeholders})"
                        exclude_params = list(matched_cost_ids)

                    time_query = f"""
                        SELECT id, request_id, provider_id, estimated_cost, timestamp
                        FROM cost_records
                        WHERE datetime(timestamp) BETWEEN datetime(?, ?) AND datetime(?, ?)
                        {exclude_condition}
                        ORDER BY ABS(strftime('%s', timestamp) - strftime('%s', ?))
                        LIMIT 1
                    """
                    cursor.execute(
                        time_query,
                        (
                            record_time,
                            f"-{time_window_minutes} minutes",
                            record_time,
                            f"+{time_window_minutes} minutes",
                            *exclude_params,
                            record_time,
                        ),
                    )
                    time_match = cursor.fetchone()

                    if time_match:
                        cost_matches[record_request_id] = {
                            "cost_record_id": time_match["id"],
                            "estimated_cost": time_match["estimated_cost"],
                            "provider_id": time_match["provider_id"],
                            "match_type": "time_window",
                            "timestamp": time_match["timestamp"],
                        }
                        matched_cost_ids.add(time_match["id"])

            logger.info(
                f"成本记录匹配完成: {len(cost_matches)}/{len(exp_request_ids)} 个实验记录匹配成功"
            )
            for match_type in ["direct_request_id", "timestamp_match", "time_window"]:
                count = sum(
                    1 for match in cost_matches.values() if match.get("match_type") == match_type
                )
                if count > 0:
                    logger.info(f"  - {match_type}: {count} 个匹配")

        except Exception as e:
            logger.error(f"查找匹配成本记录失败: {e}")

        return cost_matches

    def _check_alerts(self, metrics: MigrationMetrics) -> None:
        """检查告警条件"""
        # 1. 成本节省告警
        cost_savings = metrics.cost_savings_percent / 100.0  # 转换为0-1
        self._check_metric_alert(
            metrics,
            MigrationMetric.COST_SAVINGS,
            cost_savings,
            f"成本节省: {metrics.cost_savings_percent:.1f}%",
        )

        # 2. 质量一致性告警
        quality_consistency = metrics.quality_consistency
        self._check_metric_alert(
            metrics,
            MigrationMetric.QUALITY_CONSISTENCY,
            quality_consistency,
            f"质量一致性: {quality_consistency:.3f}",
        )

        # 3. 错误率差异告警
        error_rate_diff = metrics.error_rate_diff
        self._check_metric_alert(
            metrics,
            MigrationMetric.ERROR_RATE_DIFF,
            error_rate_diff,
            f"错误率差异: {error_rate_diff:.4f}",
        )

        # 4. 响应时间差异告警
        response_time_ratio = 1.0 + (metrics.response_time_diff_percent / 100.0)
        self._check_metric_alert(
            metrics,
            MigrationMetric.RESPONSE_TIME,
            response_time_ratio,
            f"响应时间差异: {metrics.response_time_diff_percent:.1f}%",
        )

    def _check_metric_alert(
        self, metrics: MigrationMetrics, metric: MigrationMetric, value: float, description: str
    ) -> None:
        """检查特定指标的告警"""
        thresholds = self.alert_thresholds.get(metric)
        if not thresholds:
            return

        alert_level = None
        alert_message = ""

        # 检查严重告警条件
        crit_thresh = thresholds.get("critical")
        if crit_thresh and crit_thresh["min"] <= value <= crit_thresh["max"]:
            alert_level = MigrationAlertLevel.CRITICAL
            alert_message = f"严重: {description} 超出临界阈值"

        # 检查警告条件（如果不满足严重条件）
        if not alert_level:
            warn_thresh = thresholds.get("warning")
            if warn_thresh and warn_thresh["min"] <= value <= warn_thresh["max"]:
                alert_level = MigrationAlertLevel.WARNING
                alert_message = f"警告: {description} 超出警告阈值"

        # 创建告警
        if alert_level:
            alert_id = f"{metric.value}_{int(time.time())}"
            alert = MigrationAlert(
                alert_id=alert_id,
                level=alert_level,
                metric=metric,
                message=alert_message,
                value=value,
                threshold=(
                    crit_thresh["max"]
                    if alert_level == MigrationAlertLevel.CRITICAL
                    else warn_thresh["max"]
                ),
                timestamp=datetime.now(),
                experiment_id=metrics.experiment_id,
                phase_number=metrics.phase_number,
            )
            self.alerts.append(alert)
            self._notify_alert(alert)

    def _notify_alert(self, alert: MigrationAlert) -> None:
        """通知告警"""
        # 这里可以集成到现有的告警系统（如FinancialMonitor）
        # 目前先记录日志

        if alert.level == MigrationAlertLevel.CRITICAL:
            logger.critical(f"🚨 迁移严重告警: {alert.message}")
            logger.critical(
                f"   指标: {alert.metric.value}, 值: {alert.value:.4f}, 阈值: {alert.threshold:.4f}"
            )
            logger.critical(f"   实验: {alert.experiment_id}, 阶段: {alert.phase_number}")

            # 严重告警可能需要自动触发回滚
            self._check_auto_rollback(alert)

        elif alert.level == MigrationAlertLevel.WARNING:
            logger.warning(f"⚠️ 迁移警告: {alert.message}")
            logger.warning(
                f"   指标: {alert.metric.value}, 值: {alert.value:.4f}, 阈值: {alert.threshold:.4f}"
            )

        else:
            logger.info(f"ℹ️ 迁移信息: {alert.message}")

    def _check_auto_rollback(self, alert: MigrationAlert) -> None:
        """检查是否需要自动回滚"""
        # 自动回滚条件：
        # 1. 质量一致性 < 0.8 (低于80%)
        # 2. 错误率差异 > 0.1 (10%)
        # 3. 连续3个严重告警

        if alert.metric == MigrationMetric.QUALITY_CONSISTENCY and alert.value < 0.8:
            logger.critical(f"质量一致性低于80%，考虑自动回滚: {alert.value:.3f}")
            # 这里可以触发回滚逻辑

        elif alert.metric == MigrationMetric.ERROR_RATE_DIFF and alert.value > 0.1:
            logger.critical(f"错误率差异超过10%，考虑自动回滚: {alert.value:.4f}")
            # 这里可以触发回滚逻辑

        # 检查连续严重告警
        recent_critical = [
            a
            for a in self.alerts[-10:]
            if a.level == MigrationAlertLevel.CRITICAL and not a.resolved
        ]
        if len(recent_critical) >= 3:
            logger.critical(f"连续{len(recent_critical)}个严重告警，考虑自动回滚")

    def _generate_monitoring_report(self) -> str:
        """生成监控报告"""
        if not self.metrics_history:
            return "无监控数据"

        # 使用最近的数据
        recent_metrics = self.metrics_history[-1]
        alert_count = len([a for a in self.alerts if not a.resolved])

        report = {
            "report_type": "migration_monitoring_report",
            "timestamp": datetime.now().isoformat(),
            "experiment_id": recent_metrics.experiment_id,
            "phase_number": recent_metrics.phase_number,
            "monitoring_window": f"{recent_metrics.monitoring_window_minutes}分钟",
            "metrics": {
                "total_requests": recent_metrics.total_requests,
                "migration_percentage": recent_metrics.deepseek_requests
                / max(1, recent_metrics.total_requests),
                "cost_savings_percent": recent_metrics.cost_savings_percent,
                "quality_consistency": recent_metrics.quality_consistency,
                "error_rate_diff": recent_metrics.error_rate_diff,
                "response_time_diff_percent": recent_metrics.response_time_diff_percent,
            },
            "alerts": {
                "total_alerts": len(self.alerts),
                "active_alerts": alert_count,
                "critical_alerts": len(
                    [
                        a
                        for a in self.alerts
                        if a.level == MigrationAlertLevel.CRITICAL and not a.resolved
                    ]
                ),
                "warning_alerts": len(
                    [
                        a
                        for a in self.alerts
                        if a.level == MigrationAlertLevel.WARNING and not a.resolved
                    ]
                ),
            },
            "status_summary": self._generate_status_summary(recent_metrics),
            "recommendations": self._generate_recommendations(recent_metrics),
        }

        # 保存报告
        report_file = f"/Volumes/1TB-M2/openclaw/mini-agent/reports/migration_monitoring_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"迁移监控报告已生成: {report_file}")
        return report_file

    def _generate_status_summary(self, metrics: MigrationMetrics) -> str:
        """生成状态摘要"""
        status = "正常"

        if metrics.cost_savings_percent < 50:
            status = "成本节省不足"
        elif metrics.quality_consistency < 0.85:
            status = "质量下降"
        elif metrics.error_rate_diff > 0.05:
            status = "错误率偏高"
        elif abs(metrics.response_time_diff_percent) > 50:
            status = "性能下降"

        return status

    def _generate_recommendations(self, metrics: MigrationMetrics) -> List[str]:
        """生成建议"""
        recommendations = []

        # 成本节省建议
        if metrics.cost_savings_percent < 70:
            recommendations.append(
                f"成本节省({metrics.cost_savings_percent:.1f}%)低于目标70%，建议分析DeepSeek使用模式"
            )

        # 质量建议
        if metrics.quality_consistency < 0.9:
            recommendations.append(
                f"质量一致性({metrics.quality_consistency:.3f})低于目标0.9，建议检查DeepSeek输出质量"
            )

        # 错误率建议
        if metrics.error_rate_diff > 0.02:
            recommendations.append(
                f"错误率差异({metrics.error_rate_diff:.4f})高于目标0.02，建议检查DeepSeek错误模式"
            )

        # 性能建议
        if metrics.response_time_diff_percent > 20:
            recommendations.append(
                f"响应时间增加({metrics.response_time_diff_percent:.1f}%)，建议优化DeepSeek调用"
            )

        if not recommendations:
            recommendations.append("迁移进展顺利，继续保持当前策略")

        return recommendations

    def _save_monitoring_state(self) -> None:
        """保存监控状态"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "alerts": [asdict(a) for a in self.alerts[-50:]],  # 保留最近50个告警
            "metrics_count": len(self.metrics_history),
            "last_metrics": asdict(self.metrics_history[-1]) if self.metrics_history else None,
        }

        state_file = "/Volumes/1TB-M2/openclaw/mini-agent/data/migration_monitor_state.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False, default=str)

    def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        if not self.metrics_history:
            return {"status": "no_data", "message": "无监控数据"}

        recent = self.metrics_history[-1]
        active_alerts = [a for a in self.alerts if not a.resolved]

        return {
            "status": "monitoring_active",
            "experiment_id": recent.experiment_id,
            "phase": recent.phase_number,
            "migration_percentage": recent.deepseek_requests / max(1, recent.total_requests),
            "cost_savings_percent": recent.cost_savings_percent,
            "quality_consistency": recent.quality_consistency,
            "active_alerts": len(active_alerts),
            "last_check": recent.timestamp.isoformat(),
            "monitoring_window": f"{recent.monitoring_window_minutes}分钟",
        }


def main():
    """主函数：启动迁移监控器"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("=" * 80)
    print("DeepSeek迁移监控器")
    print("=" * 80)

    # 数据库路径
    db_path = "/Volumes/1TB-M2/openclaw/mini-agent/data/cost_tracking.db"

    # 创建监控器
    monitor = MigrationMonitor(db_path=db_path, check_interval_minutes=15)

    # 立即进行一次检查
    print("🔄 收集初始迁移指标...")
    initial_metrics = monitor.collect_migration_metrics()

    if initial_metrics:
        print("✅ 初始指标收集成功:")
        print(f"   总请求数: {initial_metrics.total_requests}")
        print(
            f"   迁移比例: {initial_metrics.deepseek_requests / max(1, initial_metrics.total_requests):.1%}"
        )
        print(f"   成本节省: {initial_metrics.cost_savings_percent:.1f}%")
        print(f"   质量一致性: {initial_metrics.quality_consistency:.3f}")
    else:
        print("⚠️  未找到迁移数据，监控器将继续运行等待数据")

    # 启动监控
    print("\n🚀 启动迁移监控器...")
    monitor.start_monitoring()

    print("\n📊 监控器已启动，每15分钟检查一次")
    print("📈 监控指标:")
    print("   - 成本节省百分比 (目标: >70%)")
    print("   - 质量一致性 (目标: >0.9)")
    print("   - 错误率差异 (目标: <0.02)")
    print("   - 响应时间差异 (目标: <20%)")
    print("\n📋 告警将记录到日志中")
    print("💾 监控报告将保存到 reports/ 目录")

    try:
        # 保持主线程运行
        while True:
            time.sleep(60)
            # 每5分钟打印一次状态
            if int(time.time()) % 300 == 0:
                status = monitor.get_current_status()
                print(f"\n📊 当前状态: {status}")

    except KeyboardInterrupt:
        print("\n🛑 收到中断信号，停止监控器...")
        monitor.stop_monitoring()
        print("✅ 监控器已停止")


if __name__ == "__main__":
    main()
