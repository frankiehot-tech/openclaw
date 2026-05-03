"""
数据质量契约 - 解决Manifest数据质量缺陷问题

基于深度审计发现：
1. 24%重复条目：优先执行队列中有28个重复ID（211个条目中160个唯一ID）
2. 数据不一致：重复条目可能导致任务重复执行、资源浪费、状态混乱
3. 完整性缺陷：某些字段可能缺失或不一致

此契约确保：
1. 数据唯一性：检测和消除重复条目
2. 数据完整性：验证必需字段的存在和格式
3. 数据一致性：确保跨manifest和队列文件的数据一致
4. 质量监控：提供持续的数据质量检查和报告

设计原则：
1. 契约先行：明确定义数据质量标准和验证规则
2. 渐进修复：支持多种去重策略，可根据场景选择
3. 完整性保证：验证必需字段和数据结构
4. 可追溯性：记录所有数据质量变更和修复操作

MAREF框架集成：符合三才六层模型的存储层要求
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .quality_item import DataQualityItem

logger = logging.getLogger(__name__)



class DataQualityContract:
    """
    数据质量契约管理器

    提供manifest数据质量分析、去重、修复等功能
    """

    # 必需字段定义（基于Athena队列系统）
    REQUIRED_FIELDS = ["id", "title", "entry_stage", "instruction_path"]

    # 字段格式规则（正则表达式）
    FIELD_FORMATS = {
        "id": r"^[a-zA-Z0-9_\-\.]+$",  # 允许字母、数字、下划线、连字符、点
        "entry_stage": r"^(build|review|plan|scan|test)$",  # 有效的入口阶段
    }

    def __init__(self, manifest_path: str | None = None):
        self.manifest_path = manifest_path
        self.items: list[DataQualityItem] = []
        self.duplicate_groups: dict[str, list[DataQualityItem]] = {}
        self.quality_report: dict[str, Any] = {}
        logger.info(f"DataQualityContract初始化: manifest_path={manifest_path}")

    def load_manifest(self, manifest_path: str | None = None) -> bool:
        """加载manifest文件"""
        if manifest_path:
            self.manifest_path = manifest_path

        if not self.manifest_path or not Path(self.manifest_path).exists():
            logger.error(f"Manifest文件不存在: {self.manifest_path}")
            return False

        try:
            with open(self.manifest_path, encoding="utf-8") as f:
                data = json.load(f)

            # 提取items列表
            if isinstance(data, dict) and "items" in data:
                raw_items = data["items"]
            elif isinstance(data, list):
                raw_items = data
            else:
                # 尝试其他结构
                raw_items = []
                for _key, value in data.items():
                    if isinstance(value, dict) and "id" in value:
                        raw_items.append(value)
                if not raw_items:
                    # 尝试其他结构
                    raw_items = list(data.values()) if isinstance(data, dict) else data

            # 创建DataQualityItem对象
            self.items = []
            for i, item in enumerate(raw_items):
                if isinstance(item, dict):
                    quality_item = DataQualityItem.from_json_item(item, i)
                    self.items.append(quality_item)

            logger.info(f"Manifest加载成功: {len(self.items)}个条目")
            return True

        except Exception as e:
            logger.error(f"加载manifest失败: {str(e)}")
            return False

    def analyze_duplicates(self) -> dict[str, Any]:
        """分析重复条目"""
        logger.info("开始分析重复条目...")

        # 按ID分组
        id_groups: dict[str, list[DataQualityItem]] = {}
        for item in self.items:
            if item.id not in id_groups:
                id_groups[item.id] = []
            id_groups[item.id].append(item)

        # 按哈希分组（更严格的重复检测）
        hash_groups: dict[str, list[DataQualityItem]] = {}
        for item in self.items:
            if item.hash not in hash_groups:
                hash_groups[item.hash] = []
            hash_groups[item.hash].append(item)

        # 识别重复
        duplicate_by_id = {id: items for id, items in id_groups.items() if len(items) > 1}
        duplicate_by_hash = {
            hash_val: items for hash_val, items in hash_groups.items() if len(items) > 1
        }

        # 更新条目的重复信息
        for item in self.items:
            # ID重复
            if item.id in duplicate_by_id:
                duplicate_items = duplicate_by_id[item.id]
                item.duplicate_count = len(duplicate_items)
                item.duplicate_indices = [self.items.index(di) for di in duplicate_items]

                if item.duplicate_count > 1:
                    item.add_issue(f"ID重复: 共有{item.duplicate_count}个相同ID的条目", "critical")

            # 哈希重复（即使ID不同，内容也可能重复）
            if item.hash in duplicate_by_hash:
                hash_items = duplicate_by_hash[item.hash]
                if len(hash_items) > 1:
                    # 检查是否已经添加了ID重复问题
                    duplicate_ids = [hi.id for hi in hash_items]
                    if len(set(duplicate_ids)) > 1:  # 不同ID但相同内容
                        item.add_issue(f"内容重复: 哈希相同但ID不同 {duplicate_ids}", "warning")

        # 生成重复分析报告
        duplicate_report = {
            "total_entries": len(self.items),
            "unique_ids": len(id_groups),
            "duplicate_ids_count": len(duplicate_by_id),
            "duplicate_hashes_count": len(duplicate_by_hash),
            "duplicate_by_id": {},
            "duplicate_by_hash": {},
            "duplicate_summary": {},
        }

        # 记录ID重复详情
        for dup_id, items in duplicate_by_id.items():
            duplicate_report["duplicate_by_id"][dup_id] = {
                "count": len(items),
                "indices": [self.items.index(item) for item in items],
                "titles": [item.data.get("title", "无标题")[:50] for item in items[:3]],
            }

        # 记录哈希重复详情
        for dup_hash, items in duplicate_by_hash.items():
            duplicate_report["duplicate_by_hash"][dup_hash] = {
                "count": len(items),
                "ids": [item.id for item in items],
                "indices": [self.items.index(item) for item in items],
            }

        # 生成摘要统计
        duplicate_report["duplicate_summary"] = {
            "total_duplicate_entries": sum(len(items) for items in duplicate_by_id.values()),
            "most_duplicated_id": (
                max(duplicate_by_id.items(), key=lambda x: len(x[1]))[0]
                if duplicate_by_id
                else None
            ),
            "max_duplicate_count": (
                max(len(items) for items in duplicate_by_id.values()) if duplicate_by_id else 0
            ),
            "duplicate_percentage": len(duplicate_by_id) / len(id_groups) * 100 if id_groups else 0,
        }

        logger.info(
            f"重复分析完成: {len(duplicate_by_id)}个重复ID，{len(duplicate_by_hash)}个重复哈希"
        )

        return duplicate_report

    def find_duplicates(
        self, items: list[dict[str, Any]] = None
    ) -> dict[str, list[dict[str, Any]]]:
        """
        查找重复条目（兼容性方法，用于测试脚本）

        参数：
        - items: 可选，要分析的条目列表。如果为None，使用已加载的条目

        返回：
        - 字典，键为重复ID，值为该ID对应的原始条目数据列表
        """
        # 如果提供了items，加载到契约中
        if items is not None:
            self.items.copy() if self.items else []
            self.items = []
            for i, item in enumerate(items):
                quality_item = DataQualityItem.from_json_item(item, i)
                self.items.append(quality_item)

        # 分析重复
        duplicate_report = self.analyze_duplicates()

        # 转换为测试脚本期望的格式：{id: [item1_data, item2_data, ...]}
        result = {}
        for dup_id, info in duplicate_report.get("duplicate_by_id", {}).items():
            # 获取该ID对应的所有DataQualityItem对象
            items_for_id = []
            for idx in info.get("indices", []):
                if idx < len(self.items):
                    items_for_id.append(self.items[idx].data)

            result[dup_id] = items_for_id

        return result

    def validate_data_integrity(self) -> dict[str, Any]:
        """验证数据完整性"""
        logger.info("开始验证数据完整性...")

        integrity_report = {
            "total_checked": len(self.items),
            "passed_validation": 0,
            "failed_validation": 0,
            "field_completeness": {},
            "validation_details": {},
        }

        # 统计字段完整性
        field_stats = {field: {"present": 0, "missing": 0} for field in self.REQUIRED_FIELDS}

        for i, item in enumerate(self.items):
            validation_result = {
                "item_id": item.id,
                "index": i,
                "passed": True,
                "issues": [],
                "field_validation": {},
            }

            # 验证必需字段
            for field in self.REQUIRED_FIELDS:
                field_present = field in item.data and item.data[field] not in [None, ""]
                validation_result["field_validation"][field] = field_present

                if field_present:
                    field_stats[field]["present"] += 1
                else:
                    field_stats[field]["missing"] += 1
                    item.add_issue(f"必需字段缺失: {field}", "critical")
                    validation_result["passed"] = False

            # 验证字段格式
            for field, pattern in self.FIELD_FORMATS.items():
                if field in item.data:
                    value = str(item.data[field])
                    if not re.match(pattern, value):
                        item.add_issue(f"字段格式无效: {field}={value[:50]}...", "warning")
                        validation_result["passed"] = False

            # 记录验证结果
            integrity_report["validation_details"][item.id] = validation_result

            if validation_result["passed"]:
                integrity_report["passed_validation"] += 1
            else:
                integrity_report["failed_validation"] += 1

        # 计算完整性百分比
        for field in self.REQUIRED_FIELDS:
            total = field_stats[field]["present"] + field_stats[field]["missing"]
            percentage = (field_stats[field]["present"] / total * 100) if total > 0 else 0
            integrity_report["field_completeness"][field] = {
                "present": field_stats[field]["present"],
                "missing": field_stats[field]["missing"],
                "percentage": percentage,
            }

        # 计算综合完整性得分（基于通过验证的比例）
        if integrity_report["total_checked"] > 0:
            completeness_score = (
                integrity_report["passed_validation"] / integrity_report["total_checked"]
            ) * 100
        else:
            completeness_score = 0.0

        # 添加测试脚本期望的字段（向后兼容）
        integrity_report["total_items"] = integrity_report["total_checked"]
        integrity_report["completeness_score"] = completeness_score

        logger.info(
            f"数据完整性验证完成: {integrity_report['passed_validation']}/{integrity_report['total_checked']} 通过, 得分: {completeness_score:.1f}"
        )

        return integrity_report

    def validate_completeness(self, items: list[dict[str, Any]] = None) -> dict[str, Any]:
        """
        验证数据完整性（兼容性方法，用于测试脚本）

        参数：
        - items: 可选，要验证的条目列表。如果为None，使用已加载的条目

        返回：
        - 完整性验证报告
        """
        # 如果提供了items，加载到契约中
        if items is not None:
            self.items.copy() if self.items else []
            self.items = []
            for i, item in enumerate(items):
                quality_item = DataQualityItem.from_json_item(item, i)
                self.items.append(quality_item)

        # 调用实际的完整性验证方法
        report = self.validate_data_integrity()

        # 确保返回的格式与测试脚本期望的一致
        # test_data_quality_contract.py期望的字段：
        # total_items, completeness_score, passed_validation, failed_validation, validation_details

        # 这些字段已经在validate_data_integrity中添加了，所以直接返回
        return report

    def calculate_quality_scores(self, items: list[dict[str, Any]] = None) -> dict[str, Any]:
        """
        计算条目的质量评分

        参数：
        - items: 可选，要评分的条目列表。如果为None，使用已加载的条目

        返回：
        - 质量评分报告，包含每个条目的评分和统计信息
        """
        # 如果提供了items，加载到契约中
        if items is not None:
            original_items = self.items.copy() if self.items else []
            self.items = []
            for i, item in enumerate(items):
                quality_item = DataQualityItem.from_json_item(item, i)
                self.items.append(quality_item)

        if not self.items:
            return {
                "total_scored": 0,
                "average_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0,
                "scores": {},
            }

        # 计算质量评分（基于完整性、重复情况等）
        # 首先分析重复和完整性
        self.analyze_duplicates()
        self.validate_data_integrity()

        # 计算每个条目的质量评分
        scores = {}
        total_score = 0.0
        max_score = 0.0
        min_score = 100.0

        for item in self.items:
            # 基础评分从DataQualityItem.quality_score获取
            base_score = item.quality_score

            # 根据重复情况调整
            if item.duplicate_count > 0:
                base_score *= 0.7  # 重复条目扣分

            # 根据完整性调整
            missing_fields = []
            for field in self.REQUIRED_FIELDS:
                if field not in item.data or item.data[field] in [None, ""]:
                    missing_fields.append(field)

            if missing_fields:
                base_score *= 1.0 - len(missing_fields) * 0.1

            # 确保评分在0-100之间
            final_score = max(0.0, min(100.0, base_score))
            item.quality_score = final_score

            scores[item.id] = {
                "score": final_score,
                "breakdown": {
                    "base": item.quality_score,
                    "duplicate_penalty": 0.7 if item.duplicate_count > 0 else 1.0,
                    "missing_fields": len(missing_fields),
                },
            }

            total_score += final_score
            max_score = max(max_score, final_score)
            min_score = min(min_score, final_score)

        avg_score = total_score / len(self.items) if self.items else 0.0

        # 恢复原始items（如果加载了临时数据）
        if items is not None:
            self.items = original_items

        return {
            "total_scored": len(self.items) if items is None else len(items),
            "average_score": avg_score,
            "max_score": max_score,
            "min_score": min_score,
            "scores": scores,
        }

    def deduplicate(
        self, items: list[dict[str, Any]] = None, strategy: str = "keep_first"
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        去重处理（兼容性方法，支持传入items参数）

        参数：
        - items: 可选，要去重的条目列表。如果为None，使用已加载的条目
        - strategy: 去重策略，默认为"keep_first"

        策略选项：
        - keep_first: 保留第一个出现的条目，删除后续重复
        - keep_last: 保留最后一个出现的条目，删除之前的重复
        - keep_most_complete: 保留字段最完整的条目
        - merge: 合并重复条目的字段（冲突时使用第一个的值）

        返回：
        - 去重后的条目列表
        - 去重报告
        """
        # 如果提供了items，加载到契约中
        if items is not None:
            self.items.copy() if self.items else []
            self.items = []
            for i, item in enumerate(items):
                quality_item = DataQualityItem.from_json_item(item, i)
                self.items.append(quality_item)

        logger.info(f"开始去重处理，策略: {strategy}")

        if not self.items:
            logger.warning("没有条目需要去重")
            return [], {"error": "没有条目需要去重"}

        # 重新分析重复（确保有最新数据）
        duplicate_report = self.analyze_duplicates()

        if duplicate_report["duplicate_ids_count"] == 0:
            logger.info("没有发现重复条目，无需去重")
            # 返回所有条目的原始数据
            deduplicated_items = [item.data for item in self.items]
            return deduplicated_items, {
                "message": "没有重复条目",
                "original_count": len(self.items),
            }

        # 按ID分组
        id_groups: dict[str, list[DataQualityItem]] = {}
        for item in self.items:
            if item.id not in id_groups:
                id_groups[item.id] = []
            id_groups[item.id].append(item)

        # 应用去重策略
        deduplicated_items = []
        deduplication_report = {
            "strategy": strategy,
            "total_before": len(self.items),
            "total_after": 0,
            "duplicates_removed": 0,
            "kept_entries": {},
            "removed_entries": {},
        }

        for item_id, items in id_groups.items():
            if len(items) == 1:
                # 唯一条目，直接保留
                deduplicated_items.append(items[0].data)
                deduplication_report["kept_entries"][item_id] = {
                    "count": 1,
                    "index": self.items.index(items[0]),
                    "reason": "unique",
                }
            else:
                # 重复条目，根据策略选择保留哪个
                selected_item, base_item = self._select_item_by_strategy(items, strategy)

                # 确定要移除的条目
                if strategy == "merge":
                    # 合并策略：所有原始条目都被移除，由合并后的新条目替代
                    removed_items = items  # 所有原始条目
                else:
                    # 其他策略：移除除选中条目外的所有重复条目
                    removed_items = [item for item in items if item != selected_item]

                # 添加保留的条目（使用selected_item的数据）
                deduplicated_items.append(selected_item.data)

                # 记录保留和删除的条目
                # 对于索引，使用base_item（对于merge策略）或selected_item（对于其他策略）
                # 因为selected_item在非merge策略中等于base_item
                kept_index = self.items.index(base_item)
                deduplication_report["kept_entries"][item_id] = {
                    "count": 1,
                    "index": kept_index,
                    "reason": strategy,
                    "selection_criteria": self._get_selection_criteria(selected_item, strategy),
                }

                deduplication_report["removed_entries"][item_id] = {
                    "count": len(removed_items),
                    "indices": [self.items.index(item) for item in removed_items],
                    "titles": [item.data.get("title", "无标题")[:50] for item in removed_items[:3]],
                }

                deduplication_report["duplicates_removed"] += len(removed_items)

        deduplication_report["total_after"] = len(deduplicated_items)

        logger.info(
            f"去重完成: {deduplication_report['total_before']} -> {deduplication_report['total_after']} 条目"
        )

        return deduplicated_items, deduplication_report

    def clean_duplicates(
        self, items: list[dict[str, Any]] = None, strategy: str = "keep_first"
    ) -> int:
        """
        清理重复条目（兼容性方法，用于测试脚本）

        参数：
        - items: 可选，要清理的条目列表。如果为None，使用已加载的条目
        - strategy: 去重策略，默认为"keep_first"

        返回：
        - 清理的重复条目数量
        """
        try:
            # 调用deduplicate方法
            deduplicated_items, deduplication_report = self.deduplicate(items, strategy)

            # 如果提供了items参数，我们需要重新创建self.items
            if items is not None:
                # 从deduplicated_items重新创建self.items
                self.items = []
                for i, item in enumerate(deduplicated_items):
                    quality_item = DataQualityItem.from_json_item(item, i)
                    self.items.append(quality_item)
            else:
                # 使用当前items，需要更新self.items以反映去重后的状态
                # 由于deduplicate方法不更新self.items，我们需要手动更新
                # 首先，重新分析重复以获取分组信息
                duplicate_report = self.analyze_duplicates()
                duplicate_by_id = duplicate_report.get("duplicate_by_id", {})

                # 如果没有重复，无需更新
                if not duplicate_by_id:
                    return deduplication_report.get("duplicates_removed", 0)

                # 创建新的items列表，只保留每个ID的第一个条目（根据策略）
                new_items = []
                processed_ids = set()

                for item in self.items:
                    if item.id not in processed_ids:
                        new_items.append(item)
                        processed_ids.add(item.id)

                # 更新self.items
                self.items = new_items

            # 返回清理的重复条目数量
            return deduplication_report.get("duplicates_removed", 0)
        except Exception as e:
            logger.error(f"清理重复条目失败: {str(e)}")
            return 0

    def _select_item_by_strategy(
        self, items: list[DataQualityItem], strategy: str
    ) -> tuple[DataQualityItem, DataQualityItem]:
        """根据策略选择要保留的条目"""
        if strategy == "keep_first":
            return (items[0], items[0])
        elif strategy == "keep_last":
            return (items[-1], items[-1])
        elif strategy == "keep_most_complete":
            # 选择字段最完整的条目
            most_complete = max(
                items,
                key=lambda item: sum(
                    1
                    for field in self.REQUIRED_FIELDS
                    if field in item.data and item.data[field] not in [None, ""]
                ),
            )
            return (most_complete, most_complete)
        elif strategy == "merge":
            # 合并策略：以第一个条目为基础，合并其他条目的字段
            base_item = items[0]
            merged_data = base_item.data.copy()

            for item in items[1:]:
                for key, value in item.data.items():
                    if key not in merged_data or merged_data[key] in [None, ""]:
                        merged_data[key] = value

            # 创建新的DataQualityItem表示合并后的条目
            # 使用base_item的第一个索引位置（因为duplicate_indices包含原始索引）
            base_index = base_item.duplicate_indices[0] if base_item.duplicate_indices else 0
            merged_item = DataQualityItem.from_json_item(merged_data, base_index)
            return (merged_item, base_item)
        else:
            # 默认使用keep_first
            return (items[0], items[0])

    def _get_selection_criteria(self, item: DataQualityItem, strategy: str) -> str:
        """获取选择条目的标准描述"""
        if strategy == "keep_first":
            return "保留第一个出现的条目"
        elif strategy == "keep_last":
            return "保留最后一个出现的条目"
        elif strategy == "keep_most_complete":
            present_fields = sum(
                1
                for field in self.REQUIRED_FIELDS
                if field in item.data and item.data[field] not in [None, ""]
            )
            return f"字段最完整（{present_fields}/{len(self.REQUIRED_FIELDS)}个必需字段）"
        elif strategy == "merge":
            return "合并所有重复条目的字段"
        else:
            return "未知策略"

    def generate_quality_report(self) -> dict[str, Any]:
        """生成完整的数据质量报告"""
        logger.info("生成数据质量报告...")

        # 执行所有分析
        duplicate_report = self.analyze_duplicates()
        integrity_report = self.validate_data_integrity()

        # 计算总体质量评分
        total_quality_score = 0.0
        for item in self.items:
            total_quality_score += item.quality_score

        avg_quality_score = total_quality_score / len(self.items) if len(self.items) > 0 else 0.0

        # 生成报告
        self.quality_report = {
            "report_generated_at": datetime.now().isoformat(),
            "manifest_path": self.manifest_path,
            "summary": {
                "total_entries": len(self.items),
                "average_quality_score": avg_quality_score,
                "duplicate_rate": duplicate_report["duplicate_summary"]["duplicate_percentage"],
                "integrity_score": (
                    integrity_report["passed_validation"] / integrity_report["total_checked"] * 100
                    if integrity_report["total_checked"] > 0
                    else 0.0
                ),
                "overall_quality": (
                    "GOOD"
                    if avg_quality_score >= 80
                    else "FAIR" if avg_quality_score >= 60 else "POOR"
                ),
            },
            "duplicate_analysis": duplicate_report,
            "integrity_analysis": integrity_report,
            "item_quality_scores": [
                {
                    "id": item.id,
                    "quality_score": item.quality_score,
                    "issues_count": len(item.issues),
                    "duplicate_count": item.duplicate_count,
                }
                for item in self.items[:20]  # 只显示前20个
            ],
            "recommendations": self._generate_recommendations(
                duplicate_report, integrity_report, avg_quality_score
            ),
        }

        logger.info(f"数据质量报告生成完成: 平均质量评分={avg_quality_score:.1f}")

        return self.quality_report

    def _generate_recommendations(
        self,
        duplicate_report: dict[str, Any],
        integrity_report: dict[str, Any],
        avg_quality_score: float,
    ) -> list[str]:
        """生成改进建议"""
        recommendations = []

        # 重复相关建议
        if duplicate_report["duplicate_ids_count"] > 0:
            dup_percentage = duplicate_report["duplicate_summary"]["duplicate_percentage"]
            recommendations.append(
                f"发现{duplicate_report['duplicate_ids_count']}个重复ID（{dup_percentage:.1f}%），建议使用deduplicate()进行去重"
            )

            max_dup = duplicate_report["duplicate_summary"]["max_duplicate_count"]
            if max_dup > 3:
                recommendations.append(f"部分ID重复{max_dup}次，需要检查任务生成逻辑")

        # 完整性相关建议
        for field, stats in integrity_report["field_completeness"].items():
            if stats["percentage"] < 100:
                recommendations.append(
                    f"字段'{field}'完整性{stats['percentage']:.1f}%，缺失{stats['missing']}个条目"
                )

        # 总体质量建议
        if avg_quality_score < 60:
            recommendations.append(
                f"总体质量评分较低（{avg_quality_score:.1f}），需要优先修复关键问题"
            )
        elif avg_quality_score < 80:
            recommendations.append(f"总体质量评分一般（{avg_quality_score:.1f}），建议进行优化")

        # 具体修复建议
        if duplicate_report["duplicate_ids_count"] > 0:
            recommendations.append(
                "修复步骤：1. 运行deduplicate()去重 2. 保存修复后的manifest 3. 验证修复效果"
            )

        return recommendations

    def save_deduplicated_manifest(self, output_path: str, strategy: str = "keep_first") -> bool:
        """保存去重后的manifest文件"""
        try:
            # 执行去重
            deduplicated_items, deduplication_report = self.deduplicate(strategy=strategy)
            logger.debug(f"去重完成: {len(deduplicated_items)}个条目")

            # 检查deduplicated_items中的数据类型
            for i, item in enumerate(deduplicated_items[:5]):
                if not isinstance(item, dict):
                    logger.warning(f"去重后条目{i}不是字典: {type(item)}")
                    if isinstance(item, str):
                        logger.warning(f"  字符串内容: {item[:100]}")

            # 构建完整的manifest结构
            manifest_data = {
                "items": deduplicated_items,
                "metadata": {
                    "deduplicated_at": datetime.now().isoformat(),
                    "original_count": len(self.items),
                    "deduplicated_count": len(deduplicated_items),
                    "strategy": strategy,
                    "contract_version": "1.0",
                },
            }

            # 保存文件
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)

            logger.info(f"去重后的manifest已保存: {output_path}")

            # 保存去重报告
            report_path = output_path.replace(".json", "_deduplication_report.json")

            # 检查deduplication_report中是否包含非JSON可序列化对象
            try:
                # 尝试序列化来检查
                json_str = json.dumps(deduplication_report, indent=2, ensure_ascii=False)
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(json_str)
            except Exception as json_error:
                logger.error(f"无法序列化去重报告: {json_error}")
                # 尝试清理报告中的非序列化数据
                cleaned_report = {}
                for key, value in deduplication_report.items():
                    try:
                        json.dumps({key: value})  # 测试可序列化
                        cleaned_report[key] = value
                    except (TypeError, ValueError, OverflowError):
                        cleaned_report[key] = str(value)

                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(cleaned_report, f, indent=2, ensure_ascii=False)
                logger.warning("已清理并保存去重报告")

            logger.info(f"去重报告已保存: {report_path}")

            return True

        except Exception as e:
            logger.error(f"保存去重manifest失败: {str(e)}")
            import traceback

            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            return False

    def print_summary_report(self):
        """打印摘要报告到控制台"""
        if not self.quality_report:
            self.generate_quality_report()

        report = self.quality_report
        summary = report["summary"]

        print("=" * 70)
        print("📊 Manifest数据质量分析报告")
        print("=" * 70)
        print(f"📋 文件路径: {report.get('manifest_path', '未指定')}")
        print(f"📈 总条目数: {summary['total_entries']}")
        print(f"⭐ 平均质量评分: {summary['average_quality_score']:.1f}/100")
        print(f"🔁 重复率: {summary['duplicate_rate']:.1f}%")
        print(f"✅ 完整性得分: {summary['integrity_score']:.1f}%")
        print(f"🏆 总体质量: {summary['overall_quality']}")
        print("-" * 70)

        # 重复详情
        dup_analysis = report.get("duplicate_analysis", {})
        if dup_analysis.get("duplicate_ids_count", 0) > 0:
            print("🔴 重复问题:")
            dup_summary = dup_analysis.get("duplicate_summary", {})
            print(f"   重复ID数量: {dup_analysis.get('duplicate_ids_count', 0)}")
            print(f"   最多重复次数: {dup_summary.get('max_duplicate_count', 0)}次")

            # 显示前5个重复ID
            dup_by_id = dup_analysis.get("duplicate_by_id", {})
            if dup_by_id:
                print("   前5个重复ID:")
                for i, (dup_id, info) in enumerate(list(dup_by_id.items())[:5]):
                    print(f"     {i+1}. {dup_id[:60]}... ({info.get('count', 0)}次重复)")

        # 完整性详情
        integrity = report.get("integrity_analysis", {})
        field_comp = integrity.get("field_completeness", {})
        if field_comp:
            print("🟡 完整性问题:")
            for field, stats in field_comp.items():
                if stats.get("percentage", 100) < 100:
                    print(
                        f"   字段 '{field}': {stats.get('percentage', 0):.1f}% (缺失{stats.get('missing', 0)}个)"
                    )

        # 建议
        recommendations = report.get("recommendations", [])
        if recommendations:
            print("💡 改进建议:")
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"   {i}. {rec}")

        print("=" * 70)

    def analyze_data_quality(self, items: list[dict[str, Any]] = None) -> dict[str, Any]:
        """
        分析数据质量（兼容性方法，用于测试脚本）

        参数：
        - items: 可选，要分析的条目列表。如果为None，使用已加载的条目

        返回：
        - 包含总体质量评分、重复率、完整性得分的字典
        """
        # 如果提供了items，加载到契约中
        if items is not None:
            self.items.copy() if self.items else []
            self.items = []
            for i, item in enumerate(items):
                quality_item = DataQualityItem.from_json_item(item, i)
                self.items.append(quality_item)

        # 生成质量报告
        quality_report = self.generate_quality_report()

        # 获取重复分析详情
        duplicate_report = quality_report.get("duplicate_analysis", {})
        duplicate_summary = duplicate_report.get("duplicate_summary", {})

        # 计算唯一ID数
        unique_ids = duplicate_report.get("unique_ids", 0)

        # 计算重复条目总数
        total_duplicate_entries = duplicate_summary.get("total_duplicate_entries", 0)

        # 转换为测试脚本期望的格式（向后兼容）
        return {
            "total_items": len(self.items),
            "unique_ids": unique_ids,
            "duplicate_items_count": total_duplicate_entries,
            "data_quality_score": quality_report["summary"]["average_quality_score"],
            # 保持原有字段以确保其他代码兼容
            "overall_quality_score": quality_report["summary"]["average_quality_score"],
            "duplicate_rate": quality_report["summary"]["duplicate_rate"],
            "completeness_score": quality_report["summary"]["integrity_score"],
        }

    def generate_detailed_report(self, items: list[dict[str, Any]] = None) -> dict[str, Any]:
        """
        生成详细的质量报告（兼容性方法，用于测试脚本）

        参数：
        - items: 可选，要分析的条目列表。如果为None，使用已加载的条目

        返回：
        - 包含summary、duplicate_details、quality_score_distribution、improvement_suggestions的详细报告
        """
        # 如果提供了items，加载到契约中
        if items is not None:
            self.items.copy() if self.items else []
            self.items = []
            for i, item in enumerate(items):
                quality_item = DataQualityItem.from_json_item(item, i)
                self.items.append(quality_item)

        # 生成质量报告
        quality_report = self.generate_quality_report()

        # 计算质量评分分布（按10分区间分组）
        quality_scores = [item.quality_score for item in self.items]
        score_distribution = {}
        for score in quality_scores:
            score_range = f"{int(score // 10 * 10)}-{int(score // 10 * 10 + 9)}"
            if score_range not in score_distribution:
                score_distribution[score_range] = 0
            score_distribution[score_range] += 1

        # 提取重复详情（转换为测试脚本期望的格式）
        duplicate_details = []
        dup_analysis = quality_report.get("duplicate_analysis", {})
        dup_by_id = dup_analysis.get("duplicate_by_id", {})

        for dup_id, info in dup_by_id.items():
            duplicate_details.append(
                {"id": dup_id, "count": info.get("count", 0), "indices": info.get("indices", [])}
            )

        # 提取改进建议
        improvement_suggestions = quality_report.get("recommendations", [])

        # 构建详细报告
        detailed_report = {
            "summary": {
                "total_items": quality_report["summary"]["total_entries"],
                "overall_quality_score": quality_report["summary"]["average_quality_score"],
                "duplicate_rate": quality_report["summary"]["duplicate_rate"],
                "completeness_score": quality_report["summary"]["integrity_score"],
            },
            "duplicate_details": duplicate_details,
            "quality_score_distribution": score_distribution,
            "improvement_suggestions": improvement_suggestions,
        }

        return detailed_report


def analyze_manifest_quality(manifest_path: str) -> DataQualityContract:
    """
    快速分析manifest质量的实用函数

    参数：
    - manifest_path: manifest文件路径

    返回：
    - 包含完整分析结果的DataQualityContract实例
    """
    contract = DataQualityContract(manifest_path)

    if contract.load_manifest():
        contract.generate_quality_report()
        contract.print_summary_report()
    else:
        print(f"❌ 无法加载manifest文件: {manifest_path}")

    return contract


def deduplicate_manifest(input_path: str, output_path: str, strategy: str = "keep_first") -> bool:
    """
    快速去重manifest的实用函数

    参数：
    - input_path: 输入manifest文件路径
    - output_path: 输出manifest文件路径
    - strategy: 去重策略（默认keep_first）

    返回：
    - 是否成功
    """
    contract = DataQualityContract(input_path)

    if not contract.load_manifest():
        print(f"❌ 无法加载输入文件: {input_path}")
        return False

    # 生成质量报告
    report = contract.generate_quality_report()
    dup_count = report["duplicate_analysis"]["duplicate_ids_count"]

    if dup_count == 0:
        print("ℹ️  没有发现重复条目，无需去重")
        return True

    print(f"🔧 发现{dup_count}个重复ID，开始去重（策略: {strategy})...")

    success = contract.save_deduplicated_manifest(output_path, strategy)

    if success:
        print(f"✅ 去重完成: {output_path}")

        # 加载并验证去重后的文件
        verify_contract = DataQualityContract(output_path)
        if verify_contract.load_manifest():
            verify_report = verify_contract.generate_quality_report()
            new_dup_count = verify_report["duplicate_analysis"]["duplicate_ids_count"]

            if new_dup_count == 0:
                print("✅ 验证通过: 去重后没有重复条目")
            else:
                print(f"⚠️  警告: 去重后仍有{new_dup_count}个重复条目")

        return True
    else:
        print("❌ 去重失败")
        return False


if __name__ == "__main__":
    # 示例用法
    print("=== DataQualityContract 测试 ===")

    # 1. 测试分析功能
    print("\n1. 测试数据质量分析:")
    test_manifest = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"

    if Path(test_manifest).exists():
        contract = analyze_manifest_quality(test_manifest)
    else:
        print(f"   测试文件不存在: {test_manifest}")
        print("   使用模拟数据测试...")

        # 创建模拟manifest进行测试
        sample_manifest = {
            "items": [
                {
                    "id": "task_1",
                    "title": "任务1",
                    "entry_stage": "build",
                    "instruction_path": "/path/1",
                },
                {
                    "id": "task_1",
                    "title": "任务1重复",
                    "entry_stage": "build",
                    "instruction_path": "/path/1",
                },  # 重复
                {
                    "id": "task_2",
                    "title": "任务2",
                    "entry_stage": "review",
                    "instruction_path": "/path/2",
                },
                {
                    "id": "task_3",
                    "title": "",
                    "entry_stage": "plan",
                    "instruction_path": "/path/3",
                },  # 标题缺失
                {
                    "id": "task-4",
                    "title": "任务4",
                    "entry_stage": "invalid",
                    "instruction_path": "/path/4",
                },  # 无效阶段
            ]
        }

        # 保存模拟文件
        test_file = "/tmp/test_manifest.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(sample_manifest, f, indent=2)

        contract = analyze_manifest_quality(test_file)

    print("\n=== 测试完成 ===")
