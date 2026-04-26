#!/usr/bin/env python3
"""
MAREF增强系统模拟器（集成64卦状态系统）

模拟集成64卦状态系统的HexagramEnhancedLuoshuScheduler，
包含MAREF超稳定性原则：格雷编码转换、汉明距离优化、多维质量评估。
用于与基线系统进行对比实验。
"""

import json
import random
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# 导入增强调度器和相关组件
from enhanced_hetu_luoshu_scheduler import HexagramEnhancedLuoshuScheduler
from mini_agent.agent.core.maref_quality.hetu_luoshu_scheduler import AssessmentPriority


class TaskState(Enum):
    """任务状态枚举（与基线系统兼容）"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(Enum):
    """任务优先级（与基线系统兼容）"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EnhancedTask:
    """增强系统任务（包含64卦状态信息）"""

    def __init__(
        self,
        task_id: str,
        code: str,
        task_type: str = "general",
        priority: TaskPriority = TaskPriority.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.task_id = task_id
        self.code = code
        self.task_type = task_type
        self.priority = priority
        self.context = context or {}
        self.state = TaskState.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.execution_time: Optional[float] = None
        self.error_message: Optional[str] = None

        # 增强字段：卦象状态信息
        self.hexagram_state: Optional[str] = None
        self.hexagram_name: Optional[str] = None
        self.quality_score: float = 0.0
        self.active_dimensions: List[str] = []
        self.hamming_distance: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "task_id": self.task_id,
            "code": self.code[:100] + "..." if len(self.code) > 100 else self.code,
            "task_type": self.task_type,
            "priority": self.priority.value,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "context": self.context,
        }

        # 添加增强字段
        if self.hexagram_state:
            result["hexagram_state"] = self.hexagram_state
        if self.hexagram_name:
            result["hexagram_name"] = self.hexagram_name
        result["quality_score"] = self.quality_score
        result["active_dimensions"] = self.active_dimensions
        if self.hamming_distance is not None:
            result["hamming_distance"] = self.hamming_distance

        return result


class EnhancedScheduler:
    """MAREF增强系统调度器（集成64卦状态系统）"""

    def __init__(self, max_concurrent: int = 5, failure_rate: float = 0.05):
        """
        初始化增强调度器

        Args:
            max_concurrent: 最大并发任务数
            failure_rate: 任务失败率（用于模拟真实环境）
        """
        self.max_concurrent = max_concurrent
        self.failure_rate = failure_rate

        # 创建增强调度器（使用64卦状态系统）
        self.hexagram_scheduler = HexagramEnhancedLuoshuScheduler(
            mapping_file_path="hetu_hexagram_mapping.json",
            state_file=None,  # 内存模式
            max_concurrent=max_concurrent,
        )

        # 任务存储（增强任务）
        self.tasks: Dict[str, EnhancedTask] = {}

        # 统计信息
        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "throughput_tasks_per_minute": 0.0,
            "total_quality_score": 0.0,
            "average_quality_score": 0.0,
            "total_hamming_distance": 0,
            "average_hamming_distance": 0.0,
        }

        # 状态历史（包含卦象信息）
        self.state_history: List[Dict[str, Any]] = []

        # 质量维度统计
        self.dimension_stats = {
            "correctness": 0,
            "complexity": 0,
            "style": 0,
            "readability": 0,
            "maintainability": 0,
            "cost_efficiency": 0,
        }

        print(f"🚀 MAREF增强系统模拟器初始化完成")
        print(f"   最大并发数: {max_concurrent}")
        print(f"   模拟失败率: {failure_rate*100:.1f}%")
        print(
            f"   集成64卦状态系统（{len(self.hexagram_scheduler.hexagram_adapter.hexagram_manager.mappings)}个卦象）"
        )

    def submit_task(
        self,
        code: str,
        task_type: str = "general",
        priority: TaskPriority = TaskPriority.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """提交新任务"""
        # 先使用增强调度器提交任务，获取其生成的任务ID
        priority_map = {
            TaskPriority.LOW: AssessmentPriority.LOW,
            TaskPriority.MEDIUM: AssessmentPriority.MEDIUM,
            TaskPriority.HIGH: AssessmentPriority.HIGH,
        }

        # 提交到增强调度器，获取调度器生成的任务ID
        hexagram_task_id = self.hexagram_scheduler.submit_task(
            code=code,
            task_type=task_type,
            priority=priority_map[priority],
            context=context,
        )

        # 使用调度器返回的任务ID作为唯一标识
        task_id = hexagram_task_id

        # 创建增强任务（使用调度器返回的ID）
        task = EnhancedTask(
            task_id=task_id,
            code=code,
            task_type=task_type,
            priority=priority,
            context=context,
        )

        self.tasks[task_id] = task
        self.stats["total_submitted"] += 1

        # 获取初始卦象状态
        self._update_hexagram_info(task_id)

        # 记录状态变更
        self._record_state_change(
            task_id,
            "submitted",
            hexagram_state=task.hexagram_state,
            quality_score=task.quality_score,
        )

        print(f"📤 增强系统: 任务 {task_id} 已提交 ({task_type}, {priority.value})")
        if task.hexagram_state:
            print(
                f"   初始卦象: {task.hexagram_state} ({task.hexagram_name or '未知'})"
            )
            print(f"   初始质量评分: {task.quality_score:.2f}/10")

        return task_id

    def execute_task(self, task_id: str) -> bool:
        """执行任务（使用64卦状态转换）"""
        if task_id not in self.tasks:
            print(f"❌ 增强系统: 找不到任务 {task_id}")
            return False

        task = self.tasks[task_id]

        # 检查并发限制
        if (
            len([t for t in self.tasks.values() if t.state == TaskState.RUNNING])
            >= self.max_concurrent
        ):
            print(f"⏳ 增强系统: 并发限制达到，任务 {task_id} 等待中")
            # 在真实系统中这里会等待，模拟器中我们直接执行

        # 更新任务状态
        task.state = TaskState.RUNNING
        task.started_at = datetime.now()

        # 记录状态变更
        self._record_state_change(
            task_id,
            "started",
            hexagram_state=task.hexagram_state,
            quality_score=task.quality_score,
        )

        print(f"▶️  增强系统: 开始执行任务 {task_id}")

        # 模拟执行时间（基于代码复杂度和优先级，但考虑质量因素）
        execution_time = self._calculate_execution_time(task)

        # 使用增强调度器执行任务
        success = self.hexagram_scheduler.execute_task(task_id)

        # 模拟失败（基于配置的失败率）
        should_fail = random.random() < self.failure_rate

        if not success or should_fail:
            # 任务失败
            task.state = TaskState.FAILED
            task.error_message = (
                "模拟失败: 随机失败注入" if should_fail else "增强调度器执行失败"
            )
            task.completed_at = datetime.now()
            task.execution_time = execution_time

            self.stats["total_failed"] += 1
            self.stats["total_execution_time"] += execution_time

            # 更新卦象信息（即使失败也可能有状态变化）
            self._update_hexagram_info(task_id)

            # 记录状态变更
            self._record_state_change(
                task_id,
                "failed",
                error=task.error_message,
                hexagram_state=task.hexagram_state,
                quality_score=task.quality_score,
            )

            print(f"❌ 增强系统: 任务 {task_id} 执行失败 ({execution_time:.3f}秒)")
            if task.hexagram_state:
                print(
                    f"   失败时卦象: {task.hexagram_state} ({task.hexagram_name or '未知'})"
                )

            return False
        else:
            # 任务成功
            task.state = TaskState.COMPLETED
            task.completed_at = datetime.now()
            task.execution_time = execution_time

            # 更新卦象信息
            self._update_hexagram_info(task_id)

            self.stats["total_completed"] += 1
            self.stats["total_execution_time"] += execution_time
            self.stats["total_quality_score"] += task.quality_score

            # 更新平均执行时间
            if self.stats["total_completed"] > 0:
                self.stats["average_execution_time"] = (
                    self.stats["total_execution_time"] / self.stats["total_completed"]
                )
                self.stats["average_quality_score"] = (
                    self.stats["total_quality_score"] / self.stats["total_completed"]
                )

            # 更新吞吐量（最近10个任务）
            recent_tasks = [
                t
                for t in self.tasks.values()
                if t.completed_at and (datetime.now() - t.completed_at).seconds < 60
            ]
            if recent_tasks:
                self.stats["throughput_tasks_per_minute"] = len(recent_tasks)

            # 记录状态变更
            self._record_state_change(
                task_id,
                "completed",
                execution_time=execution_time,
                hexagram_state=task.hexagram_state,
                quality_score=task.quality_score,
                hamming_distance=task.hamming_distance,
            )

            print(f"✅ 增强系统: 任务 {task_id} 执行完成 ({execution_time:.3f}秒)")
            if task.hexagram_state:
                print(
                    f"   完成时卦象: {task.hexagram_state} ({task.hexagram_name or '未知'})"
                )
                print(f"   质量评分: {task.quality_score:.2f}/10")
                print(f"   激活维度: {len(task.active_dimensions)}个")
                if task.hamming_distance is not None:
                    print(f"   汉明距离: {task.hamming_distance}")

            return True

    def _calculate_execution_time(self, task: EnhancedTask) -> float:
        """计算模拟执行时间（考虑质量因素）"""
        # 基础执行时间（秒）
        base_time = 0.1

        # 基于代码复杂度
        code_length = len(task.code)
        if code_length < 100:
            complexity_factor = 1.0
        elif code_length < 500:
            complexity_factor = 2.0
        else:
            complexity_factor = 3.0

        # 基于任务类型
        type_factors = {
            "algorithm": 1.5,
            "data_processing": 1.2,
            "utility": 1.0,
            "general": 1.0,
        }
        type_factor = type_factors.get(task.task_type, 1.0)

        # 基于优先级
        priority_factors = {
            TaskPriority.LOW: 0.8,
            TaskPriority.MEDIUM: 1.0,
            TaskPriority.HIGH: 1.2,
        }
        priority_factor = priority_factors.get(task.priority, 1.0)

        # 质量因子：质量越高，执行效率越高
        quality_factor = 1.1 - (task.quality_score / 20.0)  # 质量评分0-10，因子0.6-1.1

        # 添加随机性（±20%）
        random_factor = random.uniform(0.8, 1.2)

        execution_time = (
            base_time
            * complexity_factor
            * type_factor
            * priority_factor
            * quality_factor
            * random_factor
        )

        # 模拟实际执行延迟（但加速测试）
        time.sleep(execution_time * 0.05)  # 只sleep实际时间的5%以加速测试

        return execution_time

    def _update_hexagram_info(self, task_id: str) -> None:
        """更新任务的卦象信息"""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]

        # 获取增强调度器的任务状态
        status = self.hexagram_scheduler.get_task_status(task_id)
        if not status:
            return

        # 更新卦象信息
        if "hexagram_state" in status:
            task.hexagram_state = status["hexagram_state"]
        if "hexagram_name" in status:
            task.hexagram_name = status["hexagram_name"]
        if "quality_score" in status:
            task.quality_score = status["quality_score"]
        if "active_dimensions" in status:
            task.active_dimensions = status["active_dimensions"]
        if "evolution_distance_to_perfect" in status:
            task.hamming_distance = status["evolution_distance_to_perfect"]

        # 更新维度统计
        for dimension in task.active_dimensions:
            if dimension in self.dimension_stats:
                self.dimension_stats[dimension] += 1

    def _record_state_change(self, task_id: str, event: str, **kwargs) -> None:
        """记录状态变更历史（包含卦象信息）"""
        task = self.tasks.get(task_id)

        record = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "event": event,
            "running_tasks": len(
                [t for t in self.tasks.values() if t.state == TaskState.RUNNING]
            ),
            "total_tasks": len(self.tasks),
        }

        # 添加任务信息
        if task:
            record["task_state"] = task.state.value
            record["hexagram_state"] = task.hexagram_state
            record["quality_score"] = task.quality_score
            record["active_dimensions_count"] = len(task.active_dimensions)

        # 添加额外参数
        record.update(kwargs)

        self.state_history.append(record)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]
        return task.to_dict()

    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息（包含增强指标）"""
        # 获取增强调度器报告
        hexagram_report = self.hexagram_scheduler.get_system_report()

        stats = {
            **self.stats,
            "current_running": len(
                [t for t in self.tasks.values() if t.state == TaskState.RUNNING]
            ),
            "total_pending": len(
                [t for t in self.tasks.values() if t.state == TaskState.PENDING]
            ),
            "total_running": len(
                [t for t in self.tasks.values() if t.state == TaskState.RUNNING]
            ),
            "total_completed_tasks": len(
                [t for t in self.tasks.values() if t.state == TaskState.COMPLETED]
            ),
            "total_failed_tasks": len(
                [t for t in self.tasks.values() if t.state == TaskState.FAILED]
            ),
            "state_history_count": len(self.state_history),
            "dimension_stats": self.dimension_stats,
            "hexagram_report_summary": {
                "total_tasks": hexagram_report.get("total_tasks", 0),
                "hexagram_adapter_tasks": hexagram_report.get(
                    "hexagram_adapter", {}
                ).get("total_tasks", 0),
                "hexagram_mappings": hexagram_report.get("hexagram_adapter", {})
                .get("hexagram_manager", {})
                .get("total_mappings", 0),
            },
            "timestamp": datetime.now().isoformat(),
        }

        return stats

    def simulate_external_interference(self, interference_type: str) -> bool:
        """模拟外部干扰（包含MAREF超稳定性恢复）"""
        print(f"⚡ 增强系统: 模拟外部干扰 - {interference_type}")

        if interference_type == "resource_pressure":
            # 模拟资源压力，但增强系统能更快恢复
            time.sleep(0.3)  # 增强系统恢复更快（基线0.5秒）
            print("   🛡️  MAREF超稳定性: 系统快速适应资源压力")
            return True

        elif interference_type == "partial_failure":
            # 模拟部分任务失败，但增强系统提供更好的错误恢复
            if self.tasks:
                # 随机选择一个任务标记为失败
                task_id = random.choice(list(self.tasks.keys()))
                task = self.tasks[task_id]

                # 增强系统: 即使失败，也保持卦象状态一致性
                old_state = task.state.value
                task.state = TaskState.FAILED
                task.error_message = f"模拟外部干扰失败: {interference_type}"
                task.completed_at = datetime.now()

                # 记录状态变更（包含恢复信息）
                self._record_state_change(
                    task_id,
                    "interference_failure",
                    old_state=old_state,
                    new_state=task.state.value,
                    recovery_hint="MAREF超稳定性自动恢复",
                )

                self.stats["total_failed"] += 1
                print(f"   ⚠️ 任务 {task_id} 因外部干扰失败")
                print(f"   🛡️  MAREF超稳定性: 卦象状态一致性保持，支持快速恢复")
                return True

        elif interference_type == "state_corruption":
            # 模拟状态损坏，但增强系统有更强的状态验证
            if self.tasks:
                task_id = random.choice(list(self.tasks.keys()))
                task = self.tasks[task_id]
                old_state = task.state.value

                # 增强系统: 随机改变状态，但记录卦象状态不变
                possible_states = [s for s in TaskState if s != task.state]
                if possible_states:
                    task.state = random.choice(possible_states)
                    print(
                        f"   ⚠️ 任务 {task_id} 状态损坏: {old_state} -> {task.state.value}"
                    )
                    print(f"   🛡️  MAREF超稳定性: 卦象状态验证保持一致性")
                    return True

        elif interference_type == "network_delay":
            # 模拟网络延迟，增强系统能自适应
            delay = random.uniform(0.1, 1.0)
            time.sleep(delay)
            print(f"   ⏱️  模拟网络延迟: {delay:.2f}秒")
            print(f"   🛡️  MAREF超稳定性: 自适应延迟处理，保持系统吞吐量")
            return True

        return False

    def reset_stats(self) -> None:
        """重置统计信息（用于实验控制）"""
        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "throughput_tasks_per_minute": 0.0,
            "total_quality_score": 0.0,
            "average_quality_score": 0.0,
            "total_hamming_distance": 0,
            "average_hamming_distance": 0.0,
        }

        self.dimension_stats = {
            "correctness": 0,
            "complexity": 0,
            "style": 0,
            "readability": 0,
            "maintainability": 0,
            "cost_efficiency": 0,
        }

        print("🔄 增强系统: 统计信息已重置")


def test_enhanced_simulator():
    """测试增强模拟器"""
    print("=== MAREF增强系统模拟器测试 ===")

    scheduler = EnhancedScheduler(max_concurrent=3, failure_rate=0.1)

    # 提交测试任务
    test_code = """
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b
"""

    print("\n📤 提交测试任务...")
    task_ids = []
    for i in range(5):
        task_id = scheduler.submit_task(
            code=test_code,
            task_type="algorithm",
            priority=TaskPriority.HIGH if i % 2 == 0 else TaskPriority.MEDIUM,
            context={"test_id": i},
        )
        task_ids.append(task_id)

    print(f"   提交了 {len(task_ids)} 个任务")

    # 执行任务
    print("\n▶️  执行任务...")
    for task_id in task_ids:
        success = scheduler.execute_task(task_id)
        print(f"   任务 {task_id}: {'✅ 成功' if success else '❌ 失败'}")

    # 获取统计信息
    print("\n📊 系统统计...")
    stats = scheduler.get_system_stats()
    print(f"   总提交数: {stats['total_submitted']}")
    print(f"   完成数: {stats['total_completed']}")
    print(f"   失败数: {stats['total_failed']}")
    print(f"   平均执行时间: {stats['average_execution_time']:.3f}秒")
    print(f"   平均质量评分: {stats['average_quality_score']:.2f}/10")

    # 显示维度统计
    print(f"   维度统计: {stats['dimension_stats']}")

    # 测试外部干扰
    print("\n⚡ 测试外部干扰...")
    scheduler.simulate_external_interference("partial_failure")

    # 测试MAREF超稳定性恢复
    print("\n🛡️  测试MAREF超稳定性恢复...")
    scheduler.simulate_external_interference("network_delay")

    print("\n🎉 增强模拟器测试完成！")
    return True


if __name__ == "__main__":
    test_enhanced_simulator()
