#!/usr/bin/env python3
"""
金融监控器适配器 - 基于审计报告第二阶段优化建议

为成本监控系统提供金融监控器集成支持。
作为CostTracker和FinancialMonitor/BudgetEngine之间的桥梁，
负责数据格式转换、同步逻辑和错误处理。

设计特点：
1. 双向适配：支持成本数据→预算引擎和预算状态→成本报告的双向数据流
2. 异步处理：避免阻塞主要API调用流程
3. 错误隔离：单个记录同步失败不影响整体系统
4. 监控集成：与现有金融监控器和预算引擎无缝集成
"""

import logging
import os
import queue
import sys
import threading
import time
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 尝试导入所需组件
try:
    from .budget_engine import BudgetCheckRequest, BudgetEngine, get_budget_engine
    from .cost_tracker import CostRecord, CostSummary, CostTracker
    from .financial_monitor import (
        FinancialMetrics,
        FinancialMonitor,
        get_financial_monitor,
    )

    HAS_DEPENDENCIES = True
except ImportError as e:
    logger.warning(f"导入依赖失败，适配器将以降级模式运行: {e}")
    HAS_DEPENDENCIES = False


# ==================== 适配器核心类 ====================


class FinancialMonitorAdapter:
    """金融监控器适配器"""

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        """
        初始化适配器

        Args:
            cost_tracker: CostTracker实例，如果为None则尝试自动获取
        """
        self.cost_tracker = cost_tracker
        self._sync_queue = queue.Queue(maxsize=1000)  # 同步队列，避免阻塞
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._is_running = False

        # 延迟初始化组件
        self._budget_engine = None
        self._financial_monitor = None
        self._component_available = HAS_DEPENDENCIES

        # 统计信息
        self.stats = {
            "total_records_synced": 0,
            "failed_syncs": 0,
            "last_sync_time": None,
            "avg_sync_latency_ms": 0.0,
            "queue_size": 0,
        }

        logger.info("金融监控器适配器初始化完成")

    def _get_budget_engine(self) -> Optional[BudgetEngine]:
        """获取预算引擎实例（延迟初始化）"""
        if self._budget_engine is None and HAS_DEPENDENCIES:
            try:
                self._budget_engine = get_budget_engine()
                logger.info("预算引擎连接成功")
            except Exception as e:
                logger.error(f"获取预算引擎失败: {e}")
                self._budget_engine = None

        return self._budget_engine

    def _get_financial_monitor(self) -> Optional[FinancialMonitor]:
        """获取金融监控器实例（延迟初始化）"""
        if self._financial_monitor is None and HAS_DEPENDENCIES:
            try:
                self._financial_monitor = get_financial_monitor()
                logger.info("金融监控器连接成功")
            except Exception as e:
                logger.error(f"获取金融监控器失败: {e}")
                self._financial_monitor = None

        return self._financial_monitor

    def _get_cost_tracker(self) -> Optional[CostTracker]:
        """获取成本追踪器实例"""
        if self.cost_tracker is None and HAS_DEPENDENCIES:
            try:
                # 尝试从cost_tracker模块获取
                from .cost_tracker import get_cost_tracker

                self.cost_tracker = get_cost_tracker()
                logger.info("成本追踪器连接成功")
            except Exception as e:
                logger.error(f"获取成本追踪器失败: {e}")
                self.cost_tracker = None

        return self.cost_tracker

    def cost_record_to_budget_consumption(self, record: CostRecord) -> Dict[str, Any]:
        """
        将CostRecord转换为预算消费记录格式

        Args:
            record: 成本记录

        Returns:
            预算消费记录字典
        """
        # 使用请求ID或生成唯一任务ID
        task_id = record.request_id or record.id

        # 确定任务类型
        if record.task_kind:
            task_type = record.task_kind
        elif record.provider_id == "deepseek":
            task_type = "deepseek_api"
        elif record.provider_id == "dashscope":
            task_type = "dashscope_api"
        else:
            task_type = "general"

        # 构建任务描述
        description = f"{record.provider_id}/{record.model_id}: {record.input_tokens}+{record.output_tokens} tokens"

        # 构建元数据
        metadata = {
            "cost_record_id": record.id,
            "provider": record.provider_id,
            "model": record.model_id,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "estimated_tokens": record.estimated_tokens,
            "timestamp": record.timestamp.isoformat(),
            "recorded_at": record.recorded_at.isoformat(),
            "cost_source": "cost_tracker",
        }

        return {
            "task_id": task_id,
            "cost": record.estimated_cost,
            "task_type": task_type,
            "description": description,
            "metadata": metadata,
        }

    def sync_cost_record(self, record: CostRecord, async_mode: bool = True) -> bool:
        """
        同步单个成本记录到预算引擎和金融监控器

        Args:
            record: 成本记录
            async_mode: 是否异步处理（默认True）

        Returns:
            同步是否成功
        """
        if not self._component_available:
            logger.debug("组件不可用，跳过成本记录同步")
            return False

        if async_mode:
            # 异步处理：放入队列
            try:
                self._sync_queue.put(record, block=False)
                self.stats["queue_size"] = self._sync_queue.qsize()
                logger.debug(f"成本记录已加入同步队列: {record.id}")
                return True
            except queue.Full:
                logger.warning(f"同步队列已满，丢弃成本记录: {record.id}")
                return False
        else:
            # 同步处理：立即执行
            return self._process_cost_record_sync(record)

    def _process_cost_record_sync(self, record: CostRecord) -> bool:
        """同步处理单个成本记录"""
        start_time = time.time()
        success = False

        try:
            # 转换为预算消费格式
            consumption_data = self.cost_record_to_budget_consumption(record)

            # 同步到预算引擎
            budget_engine = self._get_budget_engine()
            if budget_engine:
                budget_engine.record_consumption(
                    task_id=consumption_data["task_id"],
                    cost=consumption_data["cost"],
                    task_type=consumption_data["task_type"],
                    description=consumption_data["description"],
                    metadata=consumption_data["metadata"],
                )
                logger.debug(f"成本记录已同步到预算引擎: {record.id}")

            # 触发金融监控器更新
            financial_monitor = self._get_financial_monitor()
            if financial_monitor:
                # 金融监控器会自动从预算引擎获取最新状态
                # 这里我们可以触发一次监控周期
                try:
                    financial_monitor.run_monitoring_cycle()
                    logger.debug(f"已触发金融监控器更新")
                except Exception as e:
                    logger.warning(f"触发金融监控器更新失败: {e}")

            success = True
            self.stats["total_records_synced"] += 1

        except Exception as e:
            logger.error(f"同步成本记录失败: {record.id} - {e}")
            self.stats["failed_syncs"] += 1
            success = False

        # 更新统计信息
        latency_ms = (time.time() - start_time) * 1000
        if self.stats["avg_sync_latency_ms"] == 0:
            self.stats["avg_sync_latency_ms"] = latency_ms
        else:
            # 简单指数移动平均
            self.stats["avg_sync_latency_ms"] = (
                0.9 * self.stats["avg_sync_latency_ms"] + 0.1 * latency_ms
            )

        self.stats["last_sync_time"] = datetime.now().isoformat()
        self.stats["queue_size"] = self._sync_queue.qsize()

        return success

    def _worker_loop(self):
        """工作线程循环，处理异步同步请求"""
        logger.info("金融监控器适配器工作线程启动")

        while not self._stop_event.is_set():
            try:
                # 从队列获取记录，带超时以允许检查停止事件
                try:
                    record = self._sync_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # 处理记录
                self._process_cost_record_sync(record)

                # 标记任务完成
                self._sync_queue.task_done()

            except Exception as e:
                logger.error(f"工作线程处理异常: {e}")

        logger.info("金融监控器适配器工作线程停止")

    def start(self):
        """启动适配器（启动工作线程）"""
        if self._is_running:
            logger.warning("适配器已经在运行")
            return

        if not self._component_available:
            logger.warning("组件不可用，适配器无法启动")
            return

        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._worker_loop, name="FinancialMonitorAdapter-Worker", daemon=True
        )
        self._worker_thread.start()
        self._is_running = True

        logger.info("金融监控器适配器已启动")

    def stop(self):
        """停止适配器"""
        if not self._is_running:
            return

        self._stop_event.set()

        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
            if self._worker_thread.is_alive():
                logger.warning("工作线程未在超时时间内停止")

        self._is_running = False
        logger.info("金融监控器适配器已停止")

    def sync_historical_costs(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        同步历史成本数据到预算引擎

        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 最大记录数
            batch_size: 批处理大小

        Returns:
            同步结果统计
        """
        if not self._component_available:
            return {"success": False, "error": "组件不可用", "records_synced": 0}

        cost_tracker = self._get_cost_tracker()
        if not cost_tracker:
            return {"success": False, "error": "成本追踪器不可用", "records_synced": 0}

        try:
            # 获取历史记录
            records = cost_tracker.get_records(
                start_date=start_date, end_date=end_date, limit=limit
            )

            total_records = len(records)
            successful_syncs = 0
            failed_syncs = 0

            logger.info(f"开始同步历史成本数据: {total_records} 条记录")

            # 分批处理
            for i in range(0, total_records, batch_size):
                batch = records[i : i + batch_size]

                for record in batch:
                    success = self._process_cost_record_sync(record)
                    if success:
                        successful_syncs += 1
                    else:
                        failed_syncs += 1

                logger.info(
                    f"已处理批次 {i//batch_size + 1}: {successful_syncs} 成功, {failed_syncs} 失败"
                )

            # 触发金融监控器完整更新
            financial_monitor = self._get_financial_monitor()
            if financial_monitor:
                financial_monitor.run_monitoring_cycle()
                logger.info("已触发金融监控器完整更新")

            return {
                "success": True,
                "total_records": total_records,
                "records_synced": successful_syncs,
                "failed_syncs": failed_syncs,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            }

        except Exception as e:
            logger.error(f"同步历史成本数据失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "records_synced": 0,
            }

    def get_financial_dashboard_data(self) -> Dict[str, Any]:
        """
        获取金融仪表板数据（集成成本数据和预算状态）

        Returns:
            集成金融仪表板数据
        """
        result = {
            "success": False,
            "data": {},
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source": "financial_monitor_adapter",
            },
        }

        try:
            # 获取金融监控器数据
            financial_monitor = self._get_financial_monitor()
            if financial_monitor:
                dashboard_data = financial_monitor.get_dashboard_payload()
                result["data"]["financial_monitor"] = dashboard_data
            else:
                result["data"]["financial_monitor"] = {"error": "金融监控器不可用"}

            # 获取成本摘要数据
            cost_tracker = self._get_cost_tracker()
            if cost_tracker:
                # 获取今日成本摘要
                today = date.today()
                cost_summary = cost_tracker.get_summary(start_date=today, end_date=today)
                result["data"]["cost_summary_today"] = {
                    "total_cost": cost_summary.total_cost,
                    "total_requests": cost_summary.total_requests,
                    "total_input_tokens": cost_summary.total_input_tokens,
                    "total_output_tokens": cost_summary.total_output_tokens,
                    "by_provider": cost_summary.by_provider,
                    "by_model": cost_summary.by_model,
                    "by_task_kind": cost_summary.by_task_kind,
                }
            else:
                result["data"]["cost_summary_today"] = {"error": "成本追踪器不可用"}

            # 添加适配器统计信息
            result["data"]["adapter_stats"] = self.stats.copy()

            result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"获取金融仪表板数据失败: {e}")

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取适配器统计信息"""
        stats = self.stats.copy()
        stats.update(
            {
                "is_running": self._is_running,
                "queue_size": self._sync_queue.qsize(),
                "component_available": self._component_available,
                "budget_engine_available": self._budget_engine is not None,
                "financial_monitor_available": self._financial_monitor is not None,
                "cost_tracker_available": self.cost_tracker is not None,
            }
        )
        return stats


# ==================== 全局实例管理 ====================


_financial_monitor_adapter_instance: Optional[FinancialMonitorAdapter] = None


def get_financial_monitor_adapter() -> FinancialMonitorAdapter:
    """获取全局金融监控器适配器实例"""
    global _financial_monitor_adapter_instance
    if _financial_monitor_adapter_instance is None:
        _financial_monitor_adapter_instance = FinancialMonitorAdapter()
    return _financial_monitor_adapter_instance


def start_financial_monitor_adapter() -> bool:
    """启动全局金融监控器适配器"""
    try:
        adapter = get_financial_monitor_adapter()
        adapter.start()
        return True
    except Exception as e:
        logger.error(f"启动金融监控器适配器失败: {e}")
        return False


def stop_financial_monitor_adapter() -> bool:
    """停止全局金融监控器适配器"""
    global _financial_monitor_adapter_instance
    try:
        if _financial_monitor_adapter_instance is not None:
            _financial_monitor_adapter_instance.stop()
            return True
        return False
    except Exception as e:
        logger.error(f"停止金融监控器适配器失败: {e}")
        return False


# ==================== 测试函数 ====================


def test_financial_monitor_adapter():
    """测试金融监控器适配器"""
    print("=== 测试金融监控器适配器 ===")

    # 测试基础功能
    print("\n1. 测试适配器初始化:")
    adapter = FinancialMonitorAdapter()
    print(f"   适配器初始化: {'成功' if adapter._component_available else '降级模式'}")

    # 测试数据转换
    print("\n2. 测试数据转换功能:")
    from datetime import datetime

    test_record = type(
        "CostRecord",
        (),
        {
            "id": "test_001",
            "request_id": "req_001",
            "timestamp": datetime.now(),
            "recorded_at": datetime.now(),
            "provider_id": "deepseek",
            "model_id": "deepseek-chat",
            "task_kind": "testing",
            "input_tokens": 100,
            "output_tokens": 50,
            "estimated_cost": 0.0015,
            "estimated_tokens": False,
        },
    )()

    consumption_data = adapter.cost_record_to_budget_consumption(test_record)
    print(f"   成本记录转换: {consumption_data['task_id']} - ¥{consumption_data['cost']:.6f}")
    print(f"   任务类型: {consumption_data['task_type']}")
    print(f"   描述: {consumption_data['description']}")

    # 测试统计信息
    print("\n3. 测试统计信息:")
    stats = adapter.get_stats()
    print(f"   组件可用性: {stats['component_available']}")
    print(f"   运行状态: {stats['is_running']}")
    print(f"   队列大小: {stats['queue_size']}")

    # 测试同步功能（模拟）
    print("\n4. 测试同步功能:")
    if adapter._component_available:
        try:
            # 尝试获取组件，但不实际同步
            budget_engine = adapter._get_budget_engine()
            financial_monitor = adapter._get_financial_monitor()
            print(f"   预算引擎: {'可用' if budget_engine else '不可用'}")
            print(f"   金融监控器: {'可用' if financial_monitor else '不可用'}")

            # 测试异步同步
            success = adapter.sync_cost_record(test_record, async_mode=True)
            print(f"   异步同步: {'成功加入队列' if success else '失败'}")
            print(f"   当前队列大小: {adapter._sync_queue.qsize()}")

            # 清空队列（测试环境）
            while not adapter._sync_queue.empty():
                adapter._sync_queue.get()
                adapter._sync_queue.task_done()

        except Exception as e:
            print(f"   同步测试异常: {e}")
    else:
        print("   组件不可用，跳过同步测试")

    print("\n5. 测试仪表板数据:")
    dashboard_data = adapter.get_financial_dashboard_data()
    print(f"   仪表板数据获取: {'成功' if dashboard_data['success'] else '失败'}")
    if dashboard_data["success"]:
        print(f"   数据源: {list(dashboard_data['data'].keys())}")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_financial_monitor_adapter()
