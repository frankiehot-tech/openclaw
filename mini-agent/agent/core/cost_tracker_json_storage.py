#!/usr/bin/env python3
"""
JSON文件存储后端 - 基于审计报告第二阶段优化建议

为成本监控系统提供JSON文件存储支持，适用于调试和简单场景。
支持数据压缩、备份和恢复机制。

设计特点：
1. 轻量级：无需数据库服务器
2. 可读性：JSON格式易于人工检查和调试
3. 数据安全：自动备份和版本控制
4. 性能优化：批量写入和缓存机制
"""

import gzip
import json
import logging
import os
import shutil
import sys
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
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


class JSONStorageBackend(StorageBackend):
    """JSON文件存储后端"""

    def __init__(self, file_path: Optional[str] = None, compress: bool = False):
        """
        初始化JSON存储后端

        Args:
            file_path: JSON文件路径，如果为None则使用默认路径
            compress: 是否启用gzip压缩
        """
        super().__init__()

        if file_path is None:
            # 默认路径：项目根目录下的data/cost_tracking.json
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.file_path = os.path.join(data_dir, "cost_tracking.json")
        else:
            self.file_path = file_path

        self.compress = compress
        self._data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": None,
            "records": [],
            "metadata": {"total_records": 0, "total_cost": 0.0, "last_record_id": None},
        }

        # 备份配置
        self.backup_dir = os.path.join(os.path.dirname(self.file_path), "backups")
        self.max_backups = 10  # 最大备份数量

        self._load_data()
        logger.info(f"JSON存储后端已初始化: {self.file_path} (压缩: {self.compress})")

    def _get_actual_file_path(self) -> str:
        """获取实际文件路径（考虑压缩）"""
        if self.compress:
            return self.file_path + ".gz"
        return self.file_path

    def _load_data(self):
        """从JSON文件加载数据"""
        actual_path = self._get_actual_file_path()

        try:
            if os.path.exists(actual_path):
                if self.compress:
                    with gzip.open(actual_path, "rt", encoding="utf-8") as f:
                        loaded_data = json.load(f)
                else:
                    with open(actual_path, "r", encoding="utf-8") as f:
                        loaded_data = json.load(f)

                # 数据验证和迁移
                self._data = self._validate_and_migrate_data(loaded_data)
                logger.info(f"从 {actual_path} 加载了 {len(self._data['records'])} 条记录")
            else:
                logger.info(f"文件不存在，使用空数据: {actual_path}")
                self._save_data()  # 创建初始文件

        except Exception as e:
            logger.error(f"加载JSON数据失败: {e}")
            # 尝试恢复备份
            if not self._restore_from_backup():
                logger.warning("无法从备份恢复，使用空数据")
                # 重新初始化数据为空
                self._data = {
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "last_updated": None,
                    "records": [],
                    "metadata": {"total_records": 0, "total_cost": 0.0, "last_record_id": None},
                }
                self._save_data()  # 创建初始文件

    def _save_data(self):
        """保存数据到JSON文件"""
        actual_path = self._get_actual_file_path()

        try:
            # 更新元数据
            self._data["last_updated"] = datetime.now().isoformat()
            self._data["metadata"]["total_records"] = len(self._data["records"])

            # 计算总成本
            total_cost = 0.0
            for record_data in self._data["records"]:
                total_cost += record_data.get("estimated_cost", 0.0)
            self._data["metadata"]["total_cost"] = total_cost

            # 创建备份
            self._create_backup()

            # 保存数据
            if self.compress:
                with gzip.open(actual_path, "wt", encoding="utf-8") as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
            else:
                with open(actual_path, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)

            logger.debug(f"数据已保存到 {actual_path} ({len(self._data['records'])} 条记录)")

        except Exception as e:
            logger.error(f"保存JSON数据失败: {e}")
            raise

    def _validate_and_migrate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据格式并执行必要的迁移"""
        if "version" not in data:
            # 旧格式，迁移到新格式
            logger.info("检测到旧格式数据，执行迁移")
            data = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "last_updated": data.get("last_updated", datetime.now().isoformat()),
                "records": data.get("records", []),
                "metadata": data.get(
                    "metadata",
                    {
                        "total_records": len(data.get("records", [])),
                        "total_cost": 0.0,
                        "last_record_id": None,
                    },
                ),
            }

        # 确保所有必要字段都存在
        if "records" not in data:
            data["records"] = []
        if "metadata" not in data:
            data["metadata"] = {
                "total_records": len(data.get("records", [])),
                "total_cost": 0.0,
                "last_record_id": None,
            }

        return data

    def _create_backup(self):
        """创建数据备份"""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)

            # 备份文件名包含时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"cost_tracking_backup_{timestamp}.json"
            if self.compress:
                backup_name += ".gz"

            backup_path = os.path.join(self.backup_dir, backup_name)

            # 复制文件
            actual_path = self._get_actual_file_path()
            if os.path.exists(actual_path):
                shutil.copy2(actual_path, backup_path)
                logger.debug(f"创建备份: {backup_path}")

            # 清理旧备份
            self._cleanup_old_backups()

        except Exception as e:
            logger.error(f"创建备份失败: {e}")

    def _cleanup_old_backups(self):
        """清理旧备份，只保留最新的N个"""
        try:
            if not os.path.exists(self.backup_dir):
                return

            backup_files = []
            for f in os.listdir(self.backup_dir):
                if f.startswith("cost_tracking_backup_") and (
                    f.endswith(".json") or f.endswith(".json.gz")
                ):
                    file_path = os.path.join(self.backup_dir, f)
                    backup_files.append((file_path, os.path.getmtime(file_path)))

            # 按修改时间排序（从旧到新）
            backup_files.sort(key=lambda x: x[1])

            # 删除多余的备份
            while len(backup_files) > self.max_backups:
                oldest_file = backup_files.pop(0)[0]
                os.remove(oldest_file)
                logger.debug(f"删除旧备份: {oldest_file}")

        except Exception as e:
            logger.error(f"清理备份失败: {e}")

    def _restore_from_backup(self) -> bool:
        """从备份恢复数据"""
        try:
            if not os.path.exists(self.backup_dir):
                return False

            # 查找最新的备份
            backup_files = []
            for f in os.listdir(self.backup_dir):
                if f.startswith("cost_tracking_backup_") and (
                    f.endswith(".json") or f.endswith(".json.gz")
                ):
                    file_path = os.path.join(self.backup_dir, f)
                    backup_files.append((file_path, os.path.getmtime(file_path)))

            if not backup_files:
                return False

            # 使用最新的备份
            backup_files.sort(key=lambda x: x[1], reverse=True)
            latest_backup = backup_files[0][0]

            # 恢复数据
            actual_path = self._get_actual_file_path()
            shutil.copy2(latest_backup, actual_path)

            # 重新加载
            self._load_data()

            logger.info(f"从备份恢复成功: {latest_backup}")
            return True

        except Exception as e:
            logger.error(f"从备份恢复失败: {e}")
            return False

    def initialize(self):
        """初始化存储"""
        # JSON存储不需要特殊的初始化，在__init__中已经处理
        pass

    def record_cost(self, record: CostRecord) -> bool:
        """记录成本"""
        try:
            # 转换为字典
            record_dict = record.to_dict()

            # 检查是否已存在（基于ID）
            existing_idx = -1
            for i, existing_record in enumerate(self._data["records"]):
                if existing_record.get("id") == record.id:
                    existing_idx = i
                    break

            if existing_idx >= 0:
                # 更新现有记录
                self._data["records"][existing_idx] = record_dict
                logger.debug(f"更新现有记录: {record.id}")
            else:
                # 添加新记录
                self._data["records"].append(record_dict)
                logger.debug(f"添加新记录: {record.id}")

            # 更新最后记录ID
            self._data["metadata"]["last_record_id"] = record.id

            # 保存到文件
            self._save_data()

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
        try:
            filtered_records = []

            for record_data in self._data["records"]:
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
            avg_tokens_per_request = total_tokens / total_requests if total_requests > 0 else 0.0
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
        try:
            cutoff_date = datetime.now().date() - timedelta(days=days_to_keep)

            # 过滤出需要保留的记录
            records_to_keep = []
            records_removed = 0

            for record_data in self._data["records"]:
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
            self._data["records"] = records_to_keep

            # 保存
            self._save_data()

            logger.info(
                f"清理完成: 移除了 {records_removed} 条旧记录，保留了 {len(records_to_keep)} 条记录"
            )
            return True

        except Exception as e:
            logger.error(f"清理数据失败: {e}")
            return False


# 测试函数
def test_json_storage():
    """测试JSON存储后端"""
    import tempfile

    print("=== 测试JSON存储后端 ===")

    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_file = f.name

    try:
        # 测试不压缩
        print(f"1. 测试不压缩模式")
        backend = JSONStorageBackend(file_path=temp_file, compress=False)

        # 创建测试记录
        from datetime import datetime

        test_record = CostRecord(
            id="test_001",
            request_id="req_001",
            timestamp=datetime.now(),
            recorded_at=datetime.now(),
            provider_id="deepseek",
            model_id="deepseek-chat",
            task_kind="testing",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.0015,  # 1.5分
            estimated_tokens=False,
        )

        # 测试记录成本
        print(f"2. 记录测试成本")
        success = backend.record_cost(test_record)
        print(f"   记录结果: {'成功' if success else '失败'}")

        # 测试获取记录
        print(f"3. 获取记录")
        records = backend.get_records()
        print(f"   获取到 {len(records)} 条记录")

        if records:
            record = records[0]
            print(
                f"   第一条记录: {record.provider_id}/{record.model_id} - ¥{record.estimated_cost:.6f}"
            )

        # 测试获取摘要
        print(f"4. 获取成本摘要")
        summary = backend.get_summary()
        print(f"   总成本: ¥{summary.total_cost:.6f}")
        print(f"   总请求数: {summary.total_requests}")
        print(f"   按provider: {summary.by_provider}")

        # 测试清理（不移除，因为日期很近）
        print(f"5. 测试清理功能")
        success = backend.cleanup(days_to_keep=1)
        print(f"   清理结果: {'成功' if success else '失败'}")

        print(f"测试完成!")

    finally:
        # 清理临时文件
        import os

        if os.path.exists(temp_file):
            os.unlink(temp_file)
            print(f"已清理临时文件: {temp_file}")


if __name__ == "__main__":
    test_json_storage()
