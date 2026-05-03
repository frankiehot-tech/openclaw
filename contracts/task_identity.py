"""
任务身份契约 - 解决ID以'-'开头被argparse误识别的问题

基于深度审计发现：13个以'-'开头的任务ID（占6.74%）会被argparse误识别为选项参数。
此契约确保所有任务ID都符合命令行参数解析器的要求。

设计原则：
1. 契约先行：明确定义ID生成和转换的规则
2. 向后兼容：支持现有ID格式的规范化转换
3. 唯一性保证：内置冲突检测和重新生成机制
4. 元数据丰富：每个ID包含完整的生命周期追踪信息

MAREF框架集成：符合三才六层模型的标识层要求
"""

import hashlib
import logging
import random
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TaskIdentity:
    """
    任务身份契约 - 解决ID以'-'开头被argparse误识别问题

    属性：
    - id: 规范化ID，不以'-'或'+'开头，符合argparse位置参数要求
    - original_id: 原始ID（可能是以'-'开头的格式）
    - prefix: 任务前缀（如'agent', 'build', 'review'等）
    - timestamp: 时间戳（YYYYMMDD-HHMMSS格式）
    - sequence: 序列号（防止冲突）
    - metadata: 额外元数据（哈希值、来源等）
    """

    id: str  # 规范化ID，不以'-'开头
    original_id: str  # 原始ID
    prefix: str  # 任务前缀
    timestamp: str  # 时间戳
    sequence: int  # 序列号
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def generate(
        cls, prefix: str = "task", metadata: dict[str, Any] | None = None
    ) -> "TaskIdentity":
        """
        生成规范化任务ID，确保不以'-'开头

        参数：
        - prefix: 任务前缀，用于标识任务类型
        - metadata: 额外元数据

        返回：
        - TaskIdentity实例
        """
        # 1. 规范化前缀，移除可能导致argparse解析问题的字符
        safe_prefix = cls._normalize_prefix(prefix)

        # 2. 生成时间戳和序列号
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        sequence = random.randint(1000, 9999)  # 4位随机数

        # 3. 构造规范化ID（确保不以'-'开头）
        task_id = f"{safe_prefix}_{timestamp}_{sequence}"

        # 4. 构造原始ID格式（向后兼容格式）
        original_id = f"{prefix}-{timestamp}-{sequence}"

        # 5. 计算哈希值用于唯一性验证
        id_hash = hashlib.md5(task_id.encode()).hexdigest()[:8]

        # 6. 构建元数据
        if metadata is None:
            metadata = {}

        metadata.update(
            {
                "hash": id_hash,
                "generated_at": datetime.now().isoformat(),
                "source": "TaskIdentityContract",
                "argparse_safe": True,
                "version": "1.0",
            }
        )

        logger.info(f"生成规范化任务ID: {task_id} (原始ID: {original_id})")

        return cls(
            id=task_id,
            original_id=original_id,
            prefix=safe_prefix,
            timestamp=timestamp,
            sequence=sequence,
            metadata=metadata,
        )

    @classmethod
    def normalize(cls, raw_id: str) -> "TaskIdentity":
        """
        将原始ID（可能以'-'开头）转换为规范化ID

        参数：
        - raw_id: 原始任务ID，可能以'-'开头

        返回：
        - TaskIdentity实例

        示例：
        >>> TaskIdentity.normalize("-Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313")
        TaskIdentity(id="agent_engineering_plan_20260413_095313_task_20260413_095313", ...)
        """
        logger.debug(f"规范化原始ID: {raw_id}")

        # 1. 处理以'-'开头的ID（深度审计发现的主要问题）
        if raw_id.startswith("-"):
            # 移除开头的'-'，避免argparse误识别
            clean_id = raw_id[1:]
            logger.warning(f"检测到以'-'开头的ID: {raw_id} -> 移除前导'-'")
        else:
            clean_id = raw_id

        # 2. 替换特殊字符为下划线（确保ID仅包含字母、数字、下划线）
        # 注意：保留连字符'-'用于分割，但确保不以'-'开头
        safe_id = re.sub(r"[^\w\-]", "_", clean_id)

        # 3. 确保不以连字符开头（二次检查）
        if safe_id.startswith("-"):
            safe_id = "task_" + safe_id[1:]
            logger.warning(f"二次检查：ID仍以'-'开头，添加'task_'前缀: {safe_id}")

        # 4. 提取前缀（第一个下划线或连字符前的部分）
        prefix_match = re.match(r"^([a-zA-Z0-9_]+)[\-_]", safe_id)
        if prefix_match:
            prefix = prefix_match.group(1)
        else:
            # 如果没有明确的前缀，使用通用前缀
            prefix = "task"

        # 5. 尝试提取时间戳和序列号
        timestamp = ""
        sequence = 0

        # 查找时间戳模式：YYYYMMDD-HHMMSS 或类似格式
        timestamp_match = re.search(r"(\d{8}[-_]\d{6})", safe_id)
        if timestamp_match:
            timestamp = timestamp_match.group(1).replace("_", "-")

        # 查找序列号模式：末尾的数字
        seq_match = re.search(r"(\d{3,})$", safe_id)
        if seq_match:
            try:
                sequence = int(seq_match.group(1))
            except ValueError:
                sequence = 0

        # 6. 计算哈希值
        id_hash = hashlib.md5(safe_id.encode()).hexdigest()[:8]

        metadata = {
            "hash": id_hash,
            "normalized_at": datetime.now().isoformat(),
            "original_raw": raw_id,
            "argparse_safe": not raw_id.startswith("-"),
            "normalization_applied": raw_id.startswith("-"),
            "version": "1.0",
        }

        logger.info(f"规范化完成: {raw_id} -> {safe_id}")

        return cls(
            id=safe_id,
            original_id=raw_id,
            prefix=prefix,
            timestamp=timestamp,
            sequence=sequence,
            metadata=metadata,
        )

    @staticmethod
    def _normalize_prefix(prefix: str) -> str:
        """
        规范化前缀，确保安全用于命令行参数

        规则：
        1. 移除开头的'-'和'+'
        2. 特殊字符替换为下划线
        3. 转换为小写（可选，保持一致性）
        4. 限制长度
        """
        if not prefix:
            return "task"

        # 移除开头的'-'和'+'
        safe_prefix = re.sub(r"^[-\+]", "", prefix)

        # 替换特殊字符为下划线
        safe_prefix = re.sub(r"[^a-zA-Z0-9_]", "_", safe_prefix)

        # 确保不以数字开头（某些系统可能限制）
        if safe_prefix and safe_prefix[0].isdigit():
            safe_prefix = "t" + safe_prefix

        # 限制长度
        if len(safe_prefix) > 32:
            safe_prefix = safe_prefix[:32]

        return safe_prefix.lower()

    def is_argparse_safe(self) -> bool:
        """检查ID是否安全用于argparse（不以'-'开头）"""
        return not self.id.startswith("-") and not self.id.startswith("+")

    def validate(self) -> dict[str, Any]:
        """
        验证任务ID的合规性

        返回：
        - 验证结果字典，包含通过/失败状态和详细信息
        """
        validation_result = {"valid": True, "issues": [], "warnings": [], "checks": {}}

        # 检查1: 是否以'-'开头（argparse安全性）
        if self.id.startswith("-") or self.id.startswith("+"):
            validation_result["valid"] = False
            validation_result["issues"].append("ID以'-'或'+'开头，会被argparse误识别为选项参数")
            validation_result["checks"]["argparse_safe"] = False
        else:
            validation_result["checks"]["argparse_safe"] = True

        # 检查2: 仅包含允许的字符
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", self.id):
            validation_result["valid"] = False
            validation_result["issues"].append("ID包含不允许的特殊字符")
            validation_result["checks"]["charset_valid"] = False
        else:
            validation_result["checks"]["charset_valid"] = True

        # 检查3: 长度限制（不超过255字符）
        if len(self.id) > 255:
            validation_result["warnings"].append("ID长度超过255字符，可能在某些系统中被截断")
            validation_result["checks"]["length_ok"] = False
        else:
            validation_result["checks"]["length_ok"] = True

        # 检查4: 唯一性哈希验证
        expected_hash = hashlib.md5(self.id.encode()).hexdigest()[:8]
        if self.metadata.get("hash") != expected_hash:
            validation_result["warnings"].append("ID哈希值不匹配，可能被篡改")
            validation_result["checks"]["hash_valid"] = False
        else:
            validation_result["checks"]["hash_valid"] = True

        validation_result["checks"]["total"] = len(validation_result["checks"]) - 1
        validation_result["checks"]["passed"] = sum(
            1 for v in validation_result["checks"].values() if v is True
        )

        logger.debug(f"ID验证结果: {validation_result}")

        return validation_result

    def to_dict(self) -> dict[str, Any]:
        """转换为字典表示"""
        return {
            "id": self.id,
            "original_id": self.original_id,
            "prefix": self.prefix,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "metadata": self.metadata,
            "argparse_safe": self.is_argparse_safe(),
            "validation": self.validate(),
        }

    def __str__(self) -> str:
        """字符串表示（使用规范化ID）"""
        return self.id

    def __repr__(self) -> str:
        """详细表示"""
        return (
            f"TaskIdentity(id='{self.id}', original='{self.original_id}', prefix='{self.prefix}')"
        )


class TaskIdentityContract:
    """
    任务身份契约管理器

    提供批量操作、冲突检测、ID池管理等功能
    """

    def __init__(self):
        self.generated_ids = set()
        self.normalized_ids = {}
        logger.info("TaskIdentityContract初始化完成")

    def bulk_normalize(self, raw_ids: list[str]) -> dict[str, TaskIdentity]:
        """
        批量规范化原始ID

        参数：
        - raw_ids: 原始ID列表

        返回：
        - 字典：原始ID -> TaskIdentity映射
        """
        results = {}

        for raw_id in raw_ids:
            try:
                task_identity = TaskIdentity.normalize(raw_id)
                results[raw_id] = task_identity
                self.normalized_ids[raw_id] = task_identity
                logger.debug(f"批量规范化: {raw_id} -> {task_identity.id}")
            except Exception as e:
                logger.error(f"规范化失败 {raw_id}: {str(e)}")
                # 生成一个安全的替代ID
                safe_id = f"error_{hashlib.md5(raw_id.encode()).hexdigest()[:8]}"
                results[raw_id] = TaskIdentity(
                    id=safe_id,
                    original_id=raw_id,
                    prefix="error",
                    timestamp="",
                    sequence=0,
                    metadata={"error": str(e), "normalization_failed": True},
                )

        logger.info(f"批量规范化完成: {len(results)}个ID处理成功")
        return results

    def audit_existing_ids(self, raw_ids: list[str]) -> dict[str, Any]:
        """
        审计现有ID的问题

        参数：
        - raw_ids: 需要审计的原始ID列表

        返回：
        - 审计报告
        """
        audit_report = {
            "total_ids": len(raw_ids),
            "problematic_ids": [],
            "argparse_unsafe_count": 0,
            "normalization_needed_count": 0,
            "details": {},
        }

        for raw_id in raw_ids:
            # 检查是否以'-'开头
            if raw_id.startswith("-"):
                audit_report["argparse_unsafe_count"] += 1
                audit_report["problematic_ids"].append(
                    {"id": raw_id, "issue": "以'-'开头，会被argparse误识别", "severity": "HIGH"}
                )
                audit_report["details"][raw_id] = {
                    "argparse_safe": False,
                    "normalization_needed": True,
                }
            else:
                audit_report["details"][raw_id] = {
                    "argparse_safe": True,
                    "normalization_needed": False,
                }

        audit_report["normalization_needed_count"] = audit_report["argparse_unsafe_count"]
        audit_report["problematic_percentage"] = (
            audit_report["argparse_unsafe_count"] / audit_report["total_ids"] * 100
            if audit_report["total_ids"] > 0
            else 0
        )

        logger.info(f"ID审计完成: 发现{audit_report['argparse_unsafe_count']}个问题ID")
        return audit_report

    def generate_batch(self, count: int, prefix: str = "task") -> list[TaskIdentity]:
        """
        批量生成规范化ID

        参数：
        - count: 生成数量
        - prefix: 任务前缀

        返回：
        - TaskIdentity列表
        """
        results = []

        for i in range(count):
            # 生成ID，确保唯一性
            max_attempts = 10
            for attempt in range(max_attempts):
                task_id = TaskIdentity.generate(prefix)

                # 检查是否唯一
                if task_id.id not in self.generated_ids:
                    self.generated_ids.add(task_id.id)
                    results.append(task_id)
                    logger.debug(f"生成批量ID {i+1}/{count}: {task_id.id}")
                    break
                else:
                    logger.warning(
                        f"ID冲突: {task_id.id}，尝试重新生成 (尝试 {attempt+1}/{max_attempts})"
                    )

            else:
                # 达到最大尝试次数，使用UUID作为后备
                fallback_id = f"{prefix}_uuid_{uuid.uuid4().hex[:8]}"
                task_id = TaskIdentity(
                    id=fallback_id,
                    original_id=fallback_id,
                    prefix=prefix,
                    timestamp=datetime.now().strftime("%Y%m%d-%H%M%S"),
                    sequence=0,
                    metadata={"fallback": True, "reason": "max_attempts_exceeded"},
                )
                results.append(task_id)
                logger.warning(f"使用后备UUID ID: {fallback_id}")

        logger.info(f"批量生成完成: {len(results)}个ID")
        return results


# 实用函数
def fix_argparse_id(raw_id: str) -> str:
    """
    快速修复函数：将可能被argparse误识别的ID转换为安全格式

    参数：
    - raw_id: 原始ID

    返回：
    - 安全的ID字符串
    """
    if raw_id.startswith("-"):
        # 简单修复：添加'task_'前缀
        return "task_" + raw_id[1:]
    return raw_id


def validate_id_for_argparse(task_id: str) -> bool:
    """
    检查ID是否安全用于argparse

    参数：
    - task_id: 要检查的ID

    返回：
    - True如果安全，False如果不安全
    """
    return not task_id.startswith("-") and not task_id.startswith("+")


if __name__ == "__main__":
    # 示例用法
    print("=== TaskIdentityContract 测试 ===")

    # 1. 生成规范化ID
    task1 = TaskIdentity.generate("agent")
    print(f"1. 生成规范化ID: {task1.id}")
    print(f"   原始ID格式: {task1.original_id}")
    print(f"   验证结果: {task1.validate()}")

    # 2. 规范化有问题的ID
    problematic_id = "-Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313"
    task2 = TaskIdentity.normalize(problematic_id)
    print(f"\n2. 规范化问题ID: {problematic_id}")
    print(f"   规范化结果: {task2.id}")
    print(f"   argparse安全: {task2.is_argparse_safe()}")

    # 3. 批量操作
    contract = TaskIdentityContract()
    raw_ids = [
        "-engineering-plan-20260413-095917-task-20260413-095917",
        "safe_task_20240416_123456_7890",
        "-another-problematic-id",
    ]

    print("\n3. 批量审计:")
    audit = contract.audit_existing_ids(raw_ids)
    print(f"   审计结果: {audit['argparse_unsafe_count']}/{audit['total_ids']} 个问题ID")

    print("\n4. 快速修复示例:")
    fixed = fix_argparse_id("-problem-id-123")
    print("   修复前: -problem-id-123")
    print(f"   修复后: {fixed}")

    print("\n=== 测试完成 ===")
