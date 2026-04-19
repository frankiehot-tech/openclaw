#!/usr/bin/env python3
"""
实验路由器 - 为任务类型提供实验分流功能

支持A/B测试、功能开关、实验配置等功能。
"""

import hashlib
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import yaml

# 配置日志
logger = logging.getLogger(__name__)


class ExperimentConfig:
    """实验配置"""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = None
        self.load_config()

    def load_config(self):
        """加载实验配置"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            logger.info(f"实验配置加载成功: {self.config_path}")
        except Exception as e:
            logger.error(f"加载实验配置失败: {e}")
            self.config = self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """创建默认配置"""
        return {"version": "1.0", "experiments": {}, "feature_flags": {}, "global_settings": {}}

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """获取实验配置"""
        if not self.config:
            return None
        return self.config.get("experiments", {}).get(experiment_id)

    def is_feature_enabled(self, feature_name: str) -> bool:
        """检查功能开关是否启用"""
        if not self.config:
            return False
        feature = self.config.get("feature_flags", {}).get(feature_name, {})
        return feature.get("enabled", False)


class ExperimentAssignment:
    """实验分配结果"""

    def __init__(self, experiment_id: str, group_name: str, metadata: Dict[str, Any]):
        self.experiment_id = experiment_id
        self.group_name = group_name
        self.metadata = metadata


class ExperimentRouter:
    """实验路由器"""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # 默认路径
            config_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "config",
            )
            config_path = os.path.join(config_dir, "experiments.yaml")

        self.config = ExperimentConfig(config_path)
        self.experiment_cache = {}

    def assign_to_experiment(
        self, task_kind: str, request_id: str, salt: str = "default"
    ) -> Optional[ExperimentAssignment]:
        """为请求分配实验分组

        Args:
            task_kind: 任务类型
            request_id: 请求ID（用于确定性哈希）
            salt: 随机化盐值

        Returns:
            实验分配结果或None（如果不参与任何实验）
        """
        # 检查是否有针对该任务类型的实验
        experiment_id = f"{task_kind}_experiment"
        experiment = self.config.get_experiment(experiment_id)

        if not experiment:
            # 尝试通用匹配
            for exp_id, exp_config in self.config.config.get("experiments", {}).items():
                if task_kind in exp_id or exp_id in task_kind:
                    experiment = exp_config
                    experiment_id = exp_id
                    break

        if not experiment or not experiment.get("enabled", False):
            return None

        # 检查实验时间范围
        start_date_str = experiment.get("start_date")
        end_date_str = experiment.get("end_date")

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                today = datetime.now().date()

                if today < start_date or today > end_date:
                    logger.debug(f"实验 {experiment_id} 不在有效期内")
                    return None
            except ValueError:
                logger.warning(f"实验 {experiment_id} 日期格式无效")

        # 基于哈希的分配
        design = experiment.get("design", {})
        groups = design.get("groups", [])
        allocation_method = design.get("randomization", "hash_based")
        experiment_salt = design.get("salt", "experiment")

        # 计算确定性哈希
        hash_input = f"{task_kind}:{request_id}:{experiment_salt}:{salt}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        hash_int = int(hash_value[:8], 16)  # 使用前8个字符作为整数

        # 分配分组
        cumulative_allocation = 0.0
        for group in groups:
            group_allocation = group.get("allocation", 0.0)
            cumulative_allocation += group_allocation

            # 归一化哈希值到0-1
            normalized_hash = (hash_int % 10000) / 10000.0

            if normalized_hash < cumulative_allocation:
                metadata = {
                    "experiment_id": experiment_id,
                    "group_name": group["name"],  # 添加group_name字段
                    "experiment_name": experiment.get("name", ""),
                    "hash_input": hash_input,
                    "hash_value": hash_value,
                    "normalized_hash": normalized_hash,
                    "allocation_method": allocation_method,
                    "assignment_timestamp": datetime.now().isoformat(),
                }

                logger.info(f"请求 {request_id} 分配到实验 {experiment_id} 分组 {group['name']}")
                return ExperimentAssignment(experiment_id, group["name"], metadata)

        # 如果分配失败，返回None
        logger.warning(f"请求 {request_id} 实验分配失败")
        return None

    def get_provider_for_experiment(
        self, task_kind: str, request_id: str, default_provider: str, default_model: str
    ) -> Tuple[str, str]:
        """获取实验分配后的provider和model

        Args:
            task_kind: 任务类型
            request_id: 请求ID
            default_provider: 默认provider
            default_model: 默认model

        Returns:
            (provider_id, model_id) 元组
        """
        assignment = self.assign_to_experiment(task_kind, request_id)

        if not assignment:
            return default_provider, default_model

        # 获取实验配置
        experiment = self.config.get_experiment(assignment.experiment_id)
        if not experiment:
            return default_provider, default_model

        # 查找分组配置
        design = experiment.get("design", {})
        groups = design.get("groups", [])

        for group in groups:
            if group.get("name") == assignment.group_name:
                provider = group.get("provider", default_provider)
                model = group.get("model", default_model)
                return provider, model

        return default_provider, default_model

    def record_experiment_result(
        self, assignment: ExperimentAssignment, result_data: Dict[str, Any]
    ) -> bool:
        """记录实验结果

        Args:
            assignment: 实验分配结果
            result_data: 结果数据

        Returns:
            是否成功记录
        """
        try:
            # 这里可以扩展为存储到数据库或文件
            logger.info(f"记录实验结果: {assignment.experiment_id}/{assignment.group_name}")
            logger.debug(f"结果数据: {result_data}")

            # 简单实现：记录到日志
            experiment_data = {
                "experiment_id": assignment.experiment_id,
                "group_name": assignment.group_name,
                "metadata": assignment.metadata,
                "result_data": result_data,
                "recorded_at": datetime.now().isoformat(),
            }

            # 可以在这里添加存储逻辑
            # 例如：存储到SQLite、JSON文件等

            return True
        except Exception as e:
            logger.error(f"记录实验结果失败: {e}")
            return False


# 全局实验路由器实例
_experiment_router_instance: Optional[ExperimentRouter] = None


def get_experiment_router() -> ExperimentRouter:
    """获取全局实验路由器实例"""
    global _experiment_router_instance
    if _experiment_router_instance is None:
        _experiment_router_instance = ExperimentRouter()
    return _experiment_router_instance


if __name__ == "__main__":
    # 测试代码
    import sys

    logging.basicConfig(level=logging.INFO)

    router = get_experiment_router()

    print("=== 实验路由器测试 ===")

    # 测试实验分配
    test_task_kind = "coding_plan"
    test_request_id = "test_request_123"

    assignment = router.assign_to_experiment(test_task_kind, test_request_id)

    if assignment:
        print(f"\n✅ 实验分配成功:")
        print(f"   实验ID: {assignment.experiment_id}")
        print(f"   分组: {assignment.group_name}")
        print(f"   元数据: {assignment.metadata}")

        # 测试获取provider
        provider, model = router.get_provider_for_experiment(
            test_task_kind, test_request_id, "dashscope", "qwen3.5-plus"
        )
        print(f"\n   Provider分配: {provider}/{model}")

        # 测试记录结果
        result_data = {"cost": 0.0015, "quality_score": 8.5, "success": True, "execution_time": 2.5}
        success = router.record_experiment_result(assignment, result_data)
        print(f"\n   {'✅' if success else '❌'} 结果记录: {'成功' if success else '失败'}")
    else:
        print(f"\n❌ 未分配到实验")

    print("\n✅ 实验路由器测试完成")
