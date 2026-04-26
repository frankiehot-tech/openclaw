#!/usr/bin/env python3
"""
基线系统模拟器（传统任务队列调度器）

模拟现有的HetuLuoshuScheduler，但不使用64卦状态系统。
用于与增强系统进行对比实验。
"""

import json
import random
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TaskState(Enum):
    """任务状态枚举（简化版本）"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(Enum):
    """任务优先级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BaselineTask:
    """基线系统任务"""

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

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
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


class BaselineScheduler:
    """基线系统调度器"""

    def __init__(self, max_concurrent: int = 5, failure_rate: float = 0.05):
        """
        初始化基线调度器

        Args:
            max_concurrent: 最大并发任务数
            failure_rate: 任务失败率（用于模拟真实环境）
        """
        self.max_concurrent = max_concurrent
        self.failure_rate = failure_rate

        # 任务存储
        self.tasks: Dict[str, BaselineTask] = {}
        self.running_tasks: Dict[str, BaselineTask] = {}

        # 统计信息
        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "throughput_tasks_per_minute": 0.0,
        }

        # 状态历史
        self.state_history: List[Dict[str, Any]] = []

        print(f"🚀 基线系统模拟器初始化完成")
        print(f"   最大并发数: {max_concurrent}")
        print(f"   模拟失败率: {failure_rate*100:.1f}%")

    def submit_task(
        self,
        code: str,
        task_type: str = "general",
        priority: TaskPriority = TaskPriority.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """提交新任务"""
        task_id = f"baseline_{self.stats['total_submitted']:06d}"

        task = BaselineTask(
            task_id=task_id,
            code=code,
            task_type=task_type,
            priority=priority,
            context=context,
        )

        self.tasks[task_id] = task
        self.stats["total_submitted"] += 1

        # 记录状态变更
        self._record_state_change(task_id, "submitted")

        print(f"📤 基线系统: 任务 {task_id} 已提交 ({task_type}, {priority.value})")
        return task_id

    def execute_task(self, task_id: str) -> bool:
        """执行任务"""
        if task_id not in self.tasks:
            print(f"❌ 基线系统: 找不到任务 {task_id}")
            return False

        task = self.tasks[task_id]

        # 检查并发限制
        if len(self.running_tasks) >= self.max_concurrent:
            print(f"⏳ 基线系统: 并发限制达到，任务 {task_id} 等待中")
            # 在真实系统中这里会等待，模拟器中我们直接执行
            # 但为了模拟真实行为，我们随机决定是否继续执行

        # 更新任务状态
        task.state = TaskState.RUNNING
        task.started_at = datetime.now()
        self.running_tasks[task_id] = task

        # 记录状态变更
        self._record_state_change(task_id, "started")

        print(f"▶️  基线系统: 开始执行任务 {task_id}")

        # 模拟执行时间（基于代码复杂度和优先级）
        execution_time = self._calculate_execution_time(task)

        # 模拟失败（基于配置的失败率）
        should_fail = random.random() < self.failure_rate

        if should_fail:
            # 任务失败
            task.state = TaskState.FAILED
            task.error_message = "模拟失败: 随机失败注入"
            task.completed_at = datetime.now()
            task.execution_time = execution_time

            self.stats["total_failed"] += 1
            self.stats["total_execution_time"] += execution_time

            # 从运行中移除
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

            # 记录状态变更
            self._record_state_change(task_id, "failed", error=task.error_message)

            print(f"❌ 基线系统: 任务 {task_id} 执行失败 ({execution_time:.3f}秒)")
            return False
        else:
            # 任务成功
            task.state = TaskState.COMPLETED
            task.completed_at = datetime.now()
            task.execution_time = execution_time

            self.stats["total_completed"] += 1
            self.stats["total_execution_time"] += execution_time

            # 更新平均执行时间
            if self.stats["total_completed"] > 0:
                self.stats["average_execution_time"] = (
                    self.stats["total_execution_time"] / self.stats["total_completed"]
                )

            # 更新吞吐量（最近10个任务）
            recent_tasks = [
                t
                for t in self.tasks.values()
                if t.completed_at and (datetime.now() - t.completed_at).seconds < 60
            ]
            if recent_tasks:
                self.stats["throughput_tasks_per_minute"] = len(recent_tasks)

            # 从运行中移除
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

            # 记录状态变更
            self._record_state_change(
                task_id, "completed", execution_time=execution_time
            )

            print(f"✅ 基线系统: 任务 {task_id} 执行完成 ({execution_time:.3f}秒)")
            return True

    def _calculate_execution_time(self, task: BaselineTask) -> float:
        """计算模拟执行时间"""
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

        # 添加随机性（±20%）
        random_factor = random.uniform(0.8, 1.2)

        execution_time = (
            base_time
            * complexity_factor
            * type_factor
            * priority_factor
            * random_factor
        )

        # 模拟实际执行延迟
        time.sleep(execution_time * 0.1)  # 只sleep实际时间的10%以加速测试

        return execution_time

    def _record_state_change(self, task_id: str, event: str, **kwargs) -> None:
        """记录状态变更历史"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "event": event,
            "running_tasks": len(self.running_tasks),
            "total_tasks": len(self.tasks),
            **kwargs,
        }
        self.state_history.append(record)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]
        return task.to_dict()

    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            **self.stats,
            "current_running": len(self.running_tasks),
            "total_pending": sum(
                1 for t in self.tasks.values() if t.state == TaskState.PENDING
            ),
            "total_running": sum(
                1 for t in self.tasks.values() if t.state == TaskState.RUNNING
            ),
            "total_completed_tasks": sum(
                1 for t in self.tasks.values() if t.state == TaskState.COMPLETED
            ),
            "total_failed_tasks": sum(
                1 for t in self.tasks.values() if t.state == TaskState.FAILED
            ),
            "state_history_count": len(self.state_history),
            "timestamp": datetime.now().isoformat(),
        }

    def simulate_external_interference(self, interference_type: str) -> bool:
        """模拟外部干扰"""
        print(f"⚡ 基线系统: 模拟外部干扰 - {interference_type}")

        if interference_type == "resource_pressure":
            # 模拟资源压力
            time.sleep(0.5)  # 增加处理延迟
            return True

        elif interference_type == "partial_failure":
            # 模拟部分任务失败
            if self.running_tasks:
                task_id = random.choice(list(self.running_tasks.keys()))
                task = self.tasks[task_id]
                task.state = TaskState.FAILED
                task.error_message = f"模拟外部干扰失败: {interference_type}"
                task.completed_at = datetime.now()

                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

                self.stats["total_failed"] += 1
                print(f"   ⚠️ 任务 {task_id} 因外部干扰失败")
                return True

        elif interference_type == "state_corruption":
            # 模拟状态损坏（随机改变一个任务状态）
            if self.tasks:
                task_id = random.choice(list(self.tasks.keys()))
                task = self.tasks[task_id]
                old_state = task.state.value

                # 随机设置到错误状态
                possible_states = [s for s in TaskState if s != task.state]
                if possible_states:
                    task.state = random.choice(possible_states)
                    print(
                        f"   ⚠️ 任务 {task_id} 状态损坏: {old_state} -> {task.state.value}"
                    )
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
        }
        print("🔄 基线系统: 统计信息已重置")


def test_baseline_simulator():
    """测试基线模拟器"""
    print("=== 基线系统模拟器测试 ===")

    scheduler = BaselineScheduler(max_concurrent=3, failure_rate=0.1)

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

    # 测试外部干扰
    print("\n⚡ 测试外部干扰...")
    scheduler.simulate_external_interference("partial_failure")

    print("\n🎉 基线模拟器测试完成！")
    return True


if __name__ == "__main__":
    test_baseline_simulator()
