#!/usr/bin/env python3
"""
内存存储后端 - 基于审计报告第二阶段优化建议

为成本监控系统提供内存存储支持，主要用于测试、调试和短期运行场景。
支持数据导出到JSON文件，线程安全设计。

设计特点：
1. 零开销：所有操作都在内存中，无需磁盘I/O
2. 线程安全：支持多线程环境下的并发访问
3. 数据导出：可随时将内存数据导出到JSON文件
4. 快速迭代：适用于开发和测试阶段
"""

import json
import logging
import os
import sys
import threading
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入现有组件
from .cost_tracker import CostRecord, CostRecordStatus, CostSummary, StorageBackend

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MemoryStorageBackend(StorageBackend):
    """内存存储后端"""

    def __init__(self, max_records: int = 10000):
        """
        初始化内存存储后端

        Args:
            max_records: 最大记录数限制，超过时自动清理旧数据
        """
        super().__init__()

        self.max_records = max_records
        self._data_lock = threading.RLock()  # 可重入锁，支持嵌套调用
        self._records: List[Dict[str, Any]] = []
        self._metadata = {
            "created_at": datetime.now().isoformat(),
            "last_updated": None,
            "total_records_added": 0,
            "total_cost": 0.0,
            "last_record_id": None,
        }

        logger.info(f"内存存储后端已初始化 (最大记录数: {max_records})")

    def _acquire_lock(self):
        """获取锁（支持上下文管理器）"""
        return self._data_lock

    def _ensure_capacity(self):
        """确保不超过最大记录数限制"""
        with self._acquire_lock():
            if len(self._records) > self.max_records:
                # 移除最旧的记录
                records_to_remove = len(self._records) - self.max_records
                removed = self._records[:records_to_remove]
                self._records = self._records[records_to_remove:]

                # 重新计算元数据
                self._recalculate_metadata()

                logger.debug(f"容量控制: 移除了 {len(removed)} 条旧记录")

    def _recalculate_metadata(self):
        """重新计算元数据"""
        with self._acquire_lock():
            total_cost = 0.0
            last_record_id = None

            for record in self._records:
                total_cost += record.get("estimated_cost", 0.0)
                last_record_id = record.get("id")

            self._metadata["total_cost"] = total_cost
            self._metadata["last_record_id"] = last_record_id
            self._metadata["last_updated"] = datetime.now().isoformat()

    def initialize(self):
        """初始化存储（内存存储无需特殊初始化）"""
        pass

    def record_cost(self, record: CostRecord) -> bool:
        """记录成本"""
        with self._acquire_lock():
            try:
                # 转换为字典
                record_dict = record.to_dict()

                # 检查是否已存在（基于ID）
                existing_idx = -1
                for i, existing_record in enumerate(self._records):
                    if existing_record.get("id") == record.id:
                        existing_idx = i
                        break

                if existing_idx >= 0:
                    # 更新现有记录
                    old_record = self._records[existing_idx]
                    self._records[existing_idx] = record_dict
                    logger.debug(f"更新现有记录: {record.id}")

                    # 更新元数据（考虑成本变化）
                    old_cost = old_record.get("estimated_cost", 0.0)
                    new_cost = record.estimated_cost
                    self._metadata["total_cost"] += new_cost - old_cost

                else:
                    # 添加新记录
                    self._records.append(record_dict)
                    self._metadata["total_records_added"] += 1
                    self._metadata["total_cost"] += record.estimated_cost
                    logger.debug(f"添加新记录: {record.id}")

                # 更新最后记录ID和更新时间
                self._metadata["last_record_id"] = record.id
                self._metadata["last_updated"] = datetime.now().isoformat()

                # 确保不超过容量限制
                self._ensure_capacity()

                return True

            except Exception as e:
                logger.error(f"记录成本失败: {e}")
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
        with self._acquire_lock():
            try:
                filtered_records = []

                for record_data in self._records:
                    # 转换为CostRecord对象进行过滤
                    try:
                        record = CostRecord.from_dict(record_data)
                    except Exception as e:
                        logger.warning(f"解析记录失败，跳过: {e}")
                        continue

                    # 时间过滤
                    if start_date and record.timestamp.date() < start_date:
                        continue
                    if end_date and record.timestamp.date() > end_date:
                        continue

                    # provider过滤
                    if provider_id and record.provider_id != provider_id:
                        continue

                    # 模型过滤
                    if model_id and record.model_id != model_id:
                        continue

                    # 任务类型过滤
                    if task_kind and record.task_kind != task_kind:
                        continue

                    filtered_records.append(record)

                    # 限制数量
                    if len(filtered_records) >= limit:
                        break

                return filtered_records

            except Exception as e:
                logger.error(f"获取记录失败: {e}")
                return []

    def get_summary(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> CostSummary:
        """获取成本摘要"""
        with self._acquire_lock():
            try:
                # 获取过滤后的记录
                records = self.get_records(start_date, end_date, limit=10000)

                if not records:
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

                # 计算统计信息
                total_cost = 0.0
                total_input_tokens = 0
                total_output_tokens = 0
                by_provider: Dict[str, float] = {}
                by_model: Dict[str, float] = {}
                by_task_kind: Dict[str, float] = {}

                earliest_date = min(r.timestamp.date() for r in records)
                latest_date = max(r.timestamp.date() for r in records)

                for record in records:
                    total_cost += record.estimated_cost
                    total_input_tokens += record.input_tokens
                    total_output_tokens += record.output_tokens

                    # provider统计
                    if record.provider_id not in by_provider:
                        by_provider[record.provider_id] = 0.0
                    by_provider[record.provider_id] += record.estimated_cost

                    # 模型统计
                    model_key = f"{record.provider_id}/{record.model_id}"
                    if model_key not in by_model:
                        by_model[model_key] = 0.0
                    by_model[model_key] += record.estimated_cost

                    # 任务类型统计
                    if record.task_kind:
                        if record.task_kind not in by_task_kind:
                            by_task_kind[record.task_kind] = 0.0
                        by_task_kind[record.task_kind] += record.estimated_cost

                total_requests = len(records)
                total_tokens = total_input_tokens + total_output_tokens

                # 计算平均值
                avg_cost_per_request = total_cost / total_requests if total_requests > 0 else 0.0
                avg_tokens_per_request = (
                    total_tokens / total_requests if total_requests > 0 else 0.0
                )
                cost_per_1k_tokens = (total_cost / total_tokens * 1000) if total_tokens > 0 else 0.0

                return CostSummary(
                    period_start=earliest_date,
                    period_end=latest_date,
                    total_cost=total_cost,
                    total_requests=total_requests,
                    total_input_tokens=total_input_tokens,
                    total_output_tokens=total_output_tokens,
                    by_provider=by_provider,
                    by_model=by_model,
                    by_task_kind=by_task_kind,
                    avg_cost_per_request=avg_cost_per_request,
                    avg_tokens_per_request=avg_tokens_per_request,
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
        with self._acquire_lock():
            try:
                cutoff_date = datetime.now().date() - timedelta(days=days_to_keep)

                # 过滤出需要保留的记录
                records_to_keep = []
                records_removed = 0

                for record_data in self._records:
                    try:
                        record = CostRecord.from_dict(record_data)
                        if record.timestamp.date() >= cutoff_date:
                            records_to_keep.append(record_data)
                        else:
                            records_removed += 1
                    except Exception as e:
                        logger.warning(f"解析记录失败，保留: {e}")
                        records_to_keep.append(record_data)

                # 更新数据
                self._records = records_to_keep

                # 重新计算元数据
                self._recalculate_metadata()

                logger.info(
                    f"清理完成: 移除了 {records_removed} 条旧记录，保留了 {len(records_to_keep)} 条记录"
                )
                return True

            except Exception as e:
                logger.error(f"清理数据失败: {e}")
                return False

    def export_to_json(self, file_path: str, compress: bool = False) -> bool:
        """
        导出数据到JSON文件

        Args:
            file_path: 导出文件路径
            compress: 是否启用gzip压缩

        Returns:
            是否导出成功
        """
        with self._acquire_lock():
            try:
                export_data = {
                    "version": "1.0",
                    "exported_at": datetime.now().isoformat(),
                    "source": "memory_storage",
                    "records": self._records.copy(),
                    "metadata": self._metadata.copy(),
                }

                if compress:
                    import gzip

                    with gzip.open(file_path, "wt", encoding="utf-8") as f:
                        json.dump(export_data, f, ensure_ascii=False, indent=2)
                else:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(export_data, f, ensure_ascii=False, indent=2)

                logger.info(
                    f"数据已导出到: {file_path} (压缩: {compress}, 记录数: {len(self._records)})"
                )
                return True

            except Exception as e:
                logger.error(f"导出数据失败: {e}")
                return False

    def import_from_json(self, file_path: str, merge: bool = True) -> bool:
        """
        从JSON文件导入数据

        Args:
            file_path: 导入文件路径
            merge: 是否合并现有数据（True=合并，False=替换）

        Returns:
            是否导入成功
        """
        with self._acquire_lock():
            try:
                # 读取数据
                if file_path.endswith(".gz"):
                    import gzip

                    with gzip.open(file_path, "rt", encoding="utf-8") as f:
                        import_data = json.load(f)
                else:
                    with open(file_path, "r", encoding="utf-8") as f:
                        import_data = json.load(f)

                # 验证数据格式
                if "records" not in import_data:
                    logger.error(f"导入文件格式无效: 缺少records字段")
                    return False

                records_to_import = import_data.get("records", [])

                if not merge:
                    # 替换现有数据
                    self._records = records_to_import
                else:
                    # 合并数据（避免重复）
                    existing_ids = {r.get("id") for r in self._records if r.get("id")}
                    for record in records_to_import:
                        record_id = record.get("id")
                        if record_id and record_id not in existing_ids:
                            self._records.append(record)
                            existing_ids.add(record_id)

                # 重新计算元数据
                self._recalculate_metadata()

                # 确保不超过容量限制
                self._ensure_capacity()

                logger.info(
                    f"数据导入完成: 从 {file_path} 导入了 {len(records_to_import)} 条记录 (合并模式: {merge})"
                )
                return True

            except Exception as e:
                logger.error(f"导入数据失败: {e}")
                return False

    def clear(self) -> bool:
        """清空所有数据"""
        with self._acquire_lock():
            try:
                record_count = len(self._records)
                self._records.clear()
                self._metadata = {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": None,
                    "total_records_added": 0,
                    "total_cost": 0.0,
                    "last_record_id": None,
                }

                logger.info(f"数据已清空: 移除了 {record_count} 条记录")
                return True

            except Exception as e:
                logger.error(f"清空数据失败: {e}")
                return False

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        with self._acquire_lock():
            return {
                "record_count": len(self._records),
                "max_records": self.max_records,
                "metadata": self._metadata.copy(),
                "estimated_memory_usage": len(json.dumps(self._records)),  # 近似内存使用
            }


# 测试函数
def test_memory_storage():
    """测试内存存储后端"""
    print("=== 测试内存存储后端 ===")

    # 测试基础功能
    print(f"1. 测试基础功能")
    backend = MemoryStorageBackend(max_records=5)  # 设置小容量以便测试容量控制

    # 创建测试记录
    from datetime import datetime, timedelta

    test_records = []

    for i in range(3):
        record = CostRecord(
            id=f"test_{i:03d}",
            request_id=f"req_{i:03d}",
            timestamp=datetime.now() - timedelta(days=i),
            recorded_at=datetime.now(),
            provider_id="deepseek" if i % 2 == 0 else "dashscope",
            model_id="deepseek-chat" if i % 2 == 0 else "qwen3.5-plus",
            task_kind="testing",
            input_tokens=100 * (i + 1),
            output_tokens=50 * (i + 1),
            estimated_cost=0.001 * (i + 1),
            estimated_tokens=False,
        )
        test_records.append(record)

    # 测试记录成本
    print(f"2. 记录测试成本")
    for record in test_records:
        success = backend.record_cost(record)
        print(f"   记录 {record.id}: {'成功' if success else '失败'}")

    # 测试获取记录
    print(f"3. 获取所有记录")
    records = backend.get_records()
    print(f"   获取到 {len(records)} 条记录")

    # 测试过滤功能
    print(f"4. 测试过滤功能")
    deepseek_records = backend.get_records(provider_id="deepseek")
    print(f"   DeepSeek记录: {len(deepseek_records)} 条")

    # 测试获取摘要
    print(f"5. 获取成本摘要")
    summary = backend.get_summary()
    print(f"   总成本: ¥{summary.total_cost:.6f}")
    print(f"   总请求数: {summary.total_requests}")
    print(f"   按provider: {summary.by_provider}")

    # 测试容量控制
    print(f"6. 测试容量控制")
    # 添加更多记录以触发容量控制
    for i in range(3, 7):
        record = CostRecord(
            id=f"overflow_{i:03d}",
            request_id=f"req_{i:03d}",
            timestamp=datetime.now(),
            recorded_at=datetime.now(),
            provider_id="test",
            model_id="test-model",
            task_kind="overflow_test",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.001,
            estimated_tokens=False,
        )
        backend.record_cost(record)

    final_records = backend.get_records()
    print(f"   最终记录数: {len(final_records)} (最大容量: 5)")

    # 测试导出功能
    print(f"7. 测试导出导入功能")
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        export_file = f.name

    try:
        # 导出
        export_success = backend.export_to_json(export_file)
        print(f"   导出: {'成功' if export_success else '失败'}")

        # 创建新后端并导入
        new_backend = MemoryStorageBackend()
        import_success = new_backend.import_from_json(export_file)
        print(f"   导入: {'成功' if import_success else '失败'}")
        print(f"   导入后记录数: {len(new_backend.get_records())}")

        # 测试统计信息
        print(f"8. 测试统计信息")
        stats = backend.get_stats()
        print(f"   记录数: {stats['record_count']}")
        print(f"   总成本: ¥{stats['metadata']['total_cost']:.6f}")

        print(f"测试完成!")

    finally:
        # 清理临时文件
        import os

        if os.path.exists(export_file):
            os.unlink(export_file)
            print(f"已清理临时文件: {export_file}")


if __name__ == "__main__":
    test_memory_storage()
