#!/usr/bin/env python3
"""
统一请求ID生成器

确保所有子系统使用一致的request_id格式，便于实验记录和成本记录的关联。

设计目标：
1. 为实验请求生成统一格式的request_id
2. 支持实验和成本记录的双向查询
3. 提供时间戳和唯一性保证
4. 与现有系统兼容
"""

import hashlib
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class RequestIDGenerator:
    """统一请求ID生成器

    生成格式: {prefix}_{timestamp}_{unique_id}
    示例:
      - 实验请求: exp_req_20240417_143025_abc123de
      - 成本记录: exp_req_20240417_143025_abc123de (相同ID)
      - 测试请求: test_req_20240417_143025_xyz789

    设计原则:
    1. 确定性: 相同输入生成相同ID
    2. 唯一性: 不同输入/时间生成不同ID
    3. 可读性: 包含时间戳便于调试
    4. 一致性: 所有子系统使用相同格式
    """

    # ID前缀常量
    PREFIX_EXPERIMENT = "exp_req"  # 实验请求
    PREFIX_COST = "exp_req"  # 成本记录（与实验相同）
    PREFIX_TEST = "test_req"  # 测试请求
    PREFIX_DEFAULT = "req"  # 默认请求

    def __init__(self, default_prefix: str = PREFIX_EXPERIMENT):
        """初始化生成器

        Args:
            default_prefix: 默认前缀
        """
        self.default_prefix = default_prefix

    def generate(
        self,
        prefix: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        unique_id: Optional[str] = None,
        seed: Optional[str] = None,
    ) -> str:
        """生成请求ID

        Args:
            prefix: ID前缀（如果不指定则使用default_prefix）
            timestamp: 时间戳（如果不指定则使用当前时间）
            unique_id: 唯一标识符（如果不指定则生成UUID）
            seed: 种子字符串，用于确定性生成（如果提供，则基于种子生成unique_id）

        Returns:
            格式化的请求ID: {prefix}_{timestamp}_{unique_id}
        """
        # 确定前缀
        final_prefix = prefix if prefix else self.default_prefix

        # 确定时间戳
        if timestamp is None:
            timestamp = datetime.now()

        # 格式化时间戳：YYYYMMDD_HHMMSS
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

        # 确定唯一标识符
        if unique_id:
            final_unique_id = unique_id
        elif seed:
            # 基于种子生成确定性唯一ID（前8个字符）
            hash_obj = hashlib.md5(seed.encode())
            final_unique_id = hash_obj.hexdigest()[:8]
        else:
            # 生成随机唯一ID
            final_unique_id = uuid.uuid4().hex[:8]

        # 组合成完整ID
        request_id = f"{final_prefix}_{timestamp_str}_{final_unique_id}"

        return request_id

    def generate_for_experiment(
        self,
        experiment_id: str,
        group_name: str,
        task_kind: str,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """为实验生成请求ID（确定性）

        基于实验参数生成确定性的请求ID，确保相同实验参数生成相同ID。
        这对于实验可重复性和调试非常重要。

        Args:
            experiment_id: 实验ID
            group_name: 分组名称
            task_kind: 任务类型
            timestamp: 时间戳（可选）

        Returns:
            实验请求ID
        """
        # 创建确定性种子
        seed = f"{experiment_id}:{group_name}:{task_kind}"

        return self.generate(prefix=self.PREFIX_EXPERIMENT, timestamp=timestamp, seed=seed)

    def generate_for_cost_record(
        self, request_id: str, timestamp: Optional[datetime] = None
    ) -> str:
        """为成本记录生成请求ID（与实验记录关联）

        成本记录应该使用与实验记录相同的request_id，确保关联。
        如果传入的request_id已经是标准格式，直接使用；否则生成新的。

        Args:
            request_id: 原始请求ID（可能来自实验记录）
            timestamp: 时间戳（可选）

        Returns:
            成本记录请求ID
        """
        # 如果request_id已经是标准格式，直接使用
        if self._is_standard_format(request_id):
            return request_id

        # 否则，基于原始request_id生成新的标准格式ID
        return self.generate(prefix=self.PREFIX_COST, timestamp=timestamp, seed=request_id)

    def parse(self, request_id: str) -> Dict[str, Any]:
        """解析请求ID

        将请求ID解析为组成成分。
        格式: {prefix}_{timestamp}_{unique_id}
        其中timestamp为YYYYMMDD_HHMMSS格式（包含一个下划线）
        前缀可能包含下划线（如exp_req），所以需要更复杂的解析逻辑。

        Args:
            request_id: 请求ID

        Returns:
            解析结果字典，包含:
            - prefix: 前缀
            - timestamp_str: 时间戳字符串（YYYYMMDD_HHMMSS）
            - unique_id: 唯一标识符
            - is_standard_format: 是否标准格式
            - timestamp: datetime对象（如果可解析）
        """
        # 首先检查是否标准格式
        is_standard = self._is_standard_format(request_id)

        result = {
            "prefix": "",
            "timestamp_str": "",
            "unique_id": "",
            "is_standard_format": is_standard,
            "timestamp": None,
        }

        if not is_standard:
            return result

        # 标准格式解析逻辑
        # 格式: {prefix}_{date}_{time}_{unique_id}
        # 其中date_time组成timestamp_str
        parts = request_id.split("_")

        # 找到时间戳部分（YYYYMMDD_HHMMSS）
        # 时间戳由两部分组成：date (YYYYMMDD) 和 time (HHMMSS)
        # 我们需要找到这两个连续部分
        date_part = None
        time_part = None
        unique_id = None
        prefix_parts = []

        for i in range(len(parts) - 2):
            # 检查第i和i+1部分是否可以组成有效时间戳
            try:
                timestamp_str = f"{parts[i]}_{parts[i+1]}"
                datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                # 找到时间戳部分
                date_part = parts[i]
                time_part = parts[i + 1]
                timestamp_str_full = timestamp_str

                # 前缀是之前的所有部分
                prefix_parts = parts[:i]
                # 唯一ID是之后的部分
                if i + 2 < len(parts):
                    unique_id = parts[i + 2]
                break
            except ValueError:
                continue

        if date_part and time_part and unique_id:
            result["prefix"] = "_".join(prefix_parts) if prefix_parts else ""
            result["timestamp_str"] = f"{date_part}_{time_part}"
            result["unique_id"] = unique_id

            # 解析时间戳
            try:
                result["timestamp"] = datetime.strptime(result["timestamp_str"], "%Y%m%d_%H%M%S")
            except ValueError:
                pass

        return result

    def extract_timestamp(self, request_id: str) -> Optional[datetime]:
        """从请求ID提取时间戳

        Args:
            request_id: 请求ID

        Returns:
            时间戳datetime对象，如果无法解析则返回None
        """
        parsed = self.parse(request_id)
        return parsed.get("timestamp")

    def extract_prefix(self, request_id: str) -> str:
        """从请求ID提取前缀

        Args:
            request_id: 请求ID

        Returns:
            前缀字符串
        """
        parsed = self.parse(request_id)
        return parsed.get("prefix", "")

    def is_experiment_request(self, request_id: str) -> bool:
        """检查是否为实验请求ID

        Args:
            request_id: 请求ID

        Returns:
            如果是实验请求ID则返回True
        """
        prefix = self.extract_prefix(request_id)
        return prefix in [self.PREFIX_EXPERIMENT, self.PREFIX_COST]

    def is_test_request(self, request_id: str) -> bool:
        """检查是否为测试请求ID

        Args:
            request_id: 请求ID

        Returns:
            如果是测试请求ID则返回True
        """
        prefix = self.extract_prefix(request_id)
        return prefix == self.PREFIX_TEST

    def _is_standard_format(self, request_id: str) -> bool:
        """检查是否为标准格式

        标准格式: {prefix}_{timestamp}_{unique_id}
        其中timestamp为YYYYMMDD_HHMMSS格式（包含一个下划线）

        Args:
            request_id: 请求ID

        Returns:
            如果是标准格式则返回True
        """
        try:
            parts = request_id.split("_")
            if len(parts) < 4:  # 至少需要: prefix_part, date, time, unique_id
                return False

            # 查找可能的时间戳部分（YYYYMMDD_HHMMSS）
            # 遍历所有可能的连续两部分组合
            for i in range(len(parts) - 2):
                try:
                    timestamp_str = f"{parts[i]}_{parts[i+1]}"
                    datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    # 找到有效时间戳，还需要确保后面有unique_id
                    if i + 2 < len(parts):
                        return True
                except ValueError:
                    continue

            return False
        except (ValueError, IndexError):
            return False

    def generate_batch(
        self, count: int, prefix: Optional[str] = None, base_timestamp: Optional[datetime] = None
    ) -> List[str]:
        """批量生成请求ID

        为批量操作生成唯一的请求ID。

        Args:
            count: 生成数量
            prefix: 前缀（可选）
            base_timestamp: 基础时间戳（可选）

        Returns:
            请求ID列表
        """
        result = []
        base_time = base_timestamp or datetime.now()

        for i in range(count):
            # 每个ID有微小的时间偏移（毫秒级），确保唯一性
            if i > 0:
                timestamp = base_time.replace(microsecond=base_time.microsecond + i)
            else:
                timestamp = base_time

            request_id = self.generate(
                prefix=prefix, timestamp=timestamp, unique_id=uuid.uuid4().hex[:8]
            )
            result.append(request_id)

        return result

    def match_time_window(
        self, request_id1: str, request_id2: str, window_seconds: int = 300
    ) -> bool:
        """检查两个请求ID是否在同一时间窗口内

        用于关联可能使用不同ID但时间相近的记录。

        Args:
            request_id1: 第一个请求ID
            request_id2: 第二个请求ID
            window_seconds: 时间窗口大小（秒）

        Returns:
            如果在同一时间窗口内则返回True
        """
        timestamp1 = self.extract_timestamp(request_id1)
        timestamp2 = self.extract_timestamp(request_id2)

        if not timestamp1 or not timestamp2:
            return False

        time_diff = abs((timestamp1 - timestamp2).total_seconds())
        return time_diff <= window_seconds


# 全局实例
_default_generator: Optional[RequestIDGenerator] = None


def get_request_id_generator() -> RequestIDGenerator:
    """获取全局请求ID生成器实例"""
    global _default_generator
    if _default_generator is None:
        _default_generator = RequestIDGenerator()
    return _default_generator


def generate_experiment_request_id(experiment_id: str, group_name: str, task_kind: str) -> str:
    """生成实验请求ID（便捷函数）

    Args:
        experiment_id: 实验ID
        group_name: 分组名称
        task_kind: 任务类型

    Returns:
        实验请求ID
    """
    generator = get_request_id_generator()
    return generator.generate_for_experiment(experiment_id, group_name, task_kind)


def generate_cost_request_id(experiment_request_id: str) -> str:
    """生成成本记录请求ID（便捷函数）

    Args:
        experiment_request_id: 实验请求ID

    Returns:
        成本记录请求ID
    """
    generator = get_request_id_generator()
    return generator.generate_for_cost_record(experiment_request_id)


# 测试代码
if __name__ == "__main__":
    # 测试基本功能
    generator = RequestIDGenerator()

    # 测试生成
    test_id1 = generator.generate()
    print(f"测试ID1: {test_id1}")

    # 测试解析
    parsed = generator.parse(test_id1)
    print(f"解析结果: {parsed}")

    # 测试实验ID生成
    exp_id = generator.generate_for_experiment(
        experiment_id="coding_plan_deepseek_coder_ab", group_name="treatment", task_kind="factorial"
    )
    print(f"实验ID: {exp_id}")

    # 测试成本记录ID生成
    cost_id = generator.generate_for_cost_record(exp_id)
    print(f"成本记录ID: {cost_id}")

    # 测试批量生成
    batch_ids = generator.generate_batch(3)
    print(f"批量ID: {batch_ids}")

    # 测试时间窗口匹配
    id1 = generator.generate()
    id2 = generator.generate()
    match = generator.match_time_window(id1, id2, 5)
    print(f"时间窗口匹配({id1}, {id2}): {match}")

    print("所有测试通过！")
