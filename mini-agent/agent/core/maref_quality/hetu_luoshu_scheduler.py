#!/usr/bin/env python3
"""
河图洛书调度器
基于MAREF河图洛书模式的状态管理和任务调度系统

河图（Hetu）：10态状态管理（1-10数字布局）
洛书（Luoshu）：9态幻方任务调度（3x3幻方布局）
"""

import json
import time
import typing as t
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from pathlib import Path


class HetuState(IntEnum):
    """河图10态枚举"""

    INITIAL = 1  # 初始状态：评估待开始
    AST_PARSED = 2  # AST解析完成：代码结构已分析
    DIMENSION_ASSESSING = 3  # 维度评估中：各维度评估进行中
    TEST_RUNNING = 4  # 测试执行：运行测试用例
    RESULT_AGGREGATING = 5  # 结果聚合：汇总各维度分数
    STRATEGY_ANALYZING = 6  # 策略分析：成本-质量分析
    TREND_PREDICTING = 7  # 趋势预测：质量演化预测
    REPORT_GENERATING = 8  # 报告生成：可视化报告
    DECISION_SUPPORTING = 9  # 决策支持：优化建议生成
    COMPLETED = 10  # 完成状态：评估结束


class LuoshuPosition(Enum):
    """洛书9个位置枚举"""

    COMPLEXITY = "complexity"  # 位置(1,1)=4：复杂度评估
    CORRECTNESS = "correctness"  # 位置(1,2)=9：正确性评估
    STYLE = "style"  # 位置(1,3)=2：风格评估
    READABILITY = "readability"  # 位置(2,1)=3：可读性评估
    CENTER = "center"  # 位置(2,2)=5：中央调度器
    MAINTAINABILITY = "maintainability"  # 位置(2,3)=7：可维护性评估
    PERFORMANCE = "performance"  # 位置(3,1)=8：性能评估
    SECURITY = "security"  # 位置(3,2)=1：安全性评估
    RELIABILITY = "reliability"  # 位置(3,3)=6：可靠性评估


class AssessmentPriority(Enum):
    """评估优先级"""

    CRITICAL = "critical"  # 关键：立即执行，最高优先级
    HIGH = "high"  # 高：尽快执行
    MEDIUM = "medium"  # 中：正常调度
    LOW = "low"  # 低：后台执行
    BATCH = "batch"  # 批量：批量处理


@dataclass
class AssessmentTask:
    """评估任务定义"""

    task_id: str
    code: str
    task_type: str
    priority: AssessmentPriority
    context: dict = field(default_factory=dict)
    test_cases: t.Optional[list] = None
    created_at: datetime = field(default_factory=datetime.now)
    state: HetuState = field(default=HetuState.INITIAL)
    scheduled_positions: t.List[LuoshuPosition] = field(default_factory=list)
    result: t.Optional[dict] = None
    error: t.Optional[str] = None
    start_time: t.Optional[datetime] = None
    end_time: t.Optional[datetime] = None

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "priority": self.priority.value,
            "state": self.state.name,
            "state_value": self.state.value,
            "scheduled_positions": [pos.value for pos in self.scheduled_positions],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "has_result": self.result is not None,
            "has_error": self.error is not None,
            "context_keys": list(self.context.keys()),
        }


@dataclass
class AssessmentSchedule:
    """评估调度计划"""

    task_id: str
    next_state: HetuState
    execution_order: t.List[LuoshuPosition]
    estimated_duration: float  # 预计持续时间（秒）
    priority_boost: float = 1.0  # 优先级提升系数
    dependencies: t.List[str] = field(default_factory=list)
    start_after: t.Optional[datetime] = None


class HetuStateManager:
    """河图状态管理器"""

    # 河图布局定义（数字位置关系）
    HETU_LAYOUT = {
        1: {"position": "bottom_center", "connections": [2, 8]},
        2: {"position": "top_right", "connections": [1, 3, 7]},
        3: {"position": "bottom_left", "connections": [2, 4, 6]},
        4: {"position": "left_middle", "connections": [3, 5, 9]},
        5: {"position": "center", "connections": [4, 6, 10]},
        6: {"position": "right_middle", "connections": [3, 5, 7]},
        7: {"position": "top_left", "connections": [2, 6, 8]},
        8: {"position": "middle_bottom", "connections": [1, 7, 9]},
        9: {"position": "right_top", "connections": [4, 8, 10]},
        10: {"position": "bottom_right", "connections": [5, 9]},
    }

    # 状态转移规则
    STATE_TRANSITIONS = {
        HetuState.INITIAL: [HetuState.AST_PARSED],
        HetuState.AST_PARSED: [HetuState.DIMENSION_ASSESSING, HetuState.TEST_RUNNING],
        HetuState.DIMENSION_ASSESSING: [HetuState.RESULT_AGGREGATING],
        HetuState.TEST_RUNNING: [HetuState.RESULT_AGGREGATING],
        HetuState.RESULT_AGGREGATING: [HetuState.STRATEGY_ANALYZING],
        HetuState.STRATEGY_ANALYZING: [HetuState.TREND_PREDICTING],
        HetuState.TREND_PREDICTING: [HetuState.REPORT_GENERATING],
        HetuState.REPORT_GENERATING: [HetuState.DECISION_SUPPORTING],
        HetuState.DECISION_SUPPORTING: [HetuState.COMPLETED],
        HetuState.COMPLETED: [],  # 最终状态
    }

    def __init__(self, state_file: t.Optional[str] = None):
        self.state_file = state_file
        self.state_history: t.Dict[str, t.List[HetuState]] = {}
        self.state_timestamps: t.Dict[str, t.List[datetime]] = {}

        # 加载持久化状态
        if state_file and Path(state_file).exists():
            self.load_states()

    def transition(self, task_id: str, current_state: HetuState, target_state: HetuState) -> bool:
        """状态转移"""
        # 验证转移是否允许
        if target_state not in self.STATE_TRANSITIONS.get(current_state, []):
            # 检查是否为错误恢复（回退到初始状态）
            if target_state == HetuState.INITIAL:
                print(f"⚠️  任务 {task_id}: 错误恢复，从 {current_state.name} 回退到 INITIAL")
                self._record_transition(task_id, current_state, HetuState.INITIAL)
                return True
            else:
                print(f"❌ 任务 {task_id}: 无效状态转移 {current_state.name} → {target_state.name}")
                return False

        # 执行转移
        self._record_transition(task_id, current_state, target_state)
        print(f"🔄 任务 {task_id}: 状态转移 {current_state.name} → {target_state.name}")
        return True

    def get_next_states(self, current_state: HetuState) -> t.List[HetuState]:
        """获取可能的下一状态"""
        return self.STATE_TRANSITIONS.get(current_state, [])

    def get_shortest_path(self, from_state: HetuState, to_state: HetuState) -> t.List[HetuState]:
        """获取最短路径（使用河图布局）"""
        # 简化实现：使用预定义路径
        predefined_paths = {
            (HetuState.INITIAL, HetuState.COMPLETED): [
                HetuState.INITIAL,
                HetuState.AST_PARSED,
                HetuState.DIMENSION_ASSESSING,
                HetuState.RESULT_AGGREGATING,
                HetuState.STRATEGY_ANALYZING,
                HetuState.REPORT_GENERATING,
                HetuState.COMPLETED,
            ],
            (HetuState.INITIAL, HetuState.REPORT_GENERATING): [
                HetuState.INITIAL,
                HetuState.AST_PARSED,
                HetuState.DIMENSION_ASSESSING,
                HetuState.RESULT_AGGREGATING,
                HetuState.REPORT_GENERATING,
            ],
        }

        # 查找预定义路径
        for (start, end), path in predefined_paths.items():
            if start == from_state and end == to_state:
                return path

        # 通用BFS搜索
        return self._bfs_search(from_state, to_state)

    def _record_transition(self, task_id: str, from_state: HetuState, to_state: HetuState):
        """记录状态转移"""
        if task_id not in self.state_history:
            self.state_history[task_id] = []
            self.state_timestamps[task_id] = []

        self.state_history[task_id].append(to_state)
        self.state_timestamps[task_id].append(datetime.now())

        # 持久化状态
        if self.state_file:
            self.save_states()

    def _bfs_search(self, start: HetuState, goal: HetuState) -> t.List[HetuState]:
        """广度优先搜索状态路径"""
        from collections import deque

        if start == goal:
            return [start]

        queue = deque([(start, [start])])
        visited = {start}

        while queue:
            current_state, path = queue.popleft()

            for next_state in self.STATE_TRANSITIONS.get(current_state, []):
                if next_state not in visited:
                    new_path = path + [next_state]

                    if next_state == goal:
                        return new_path

                    visited.add(next_state)
                    queue.append((next_state, new_path))

        # 如果没有找到路径，返回空列表
        return []

    def save_states(self):
        """保存状态到文件"""
        if not self.state_file:
            return

        data = {
            "state_history": {
                task_id: [state.value for state in states]
                for task_id, states in self.state_history.items()
            },
            "state_timestamps": {
                task_id: [ts.isoformat() for ts in timestamps]
                for task_id, timestamps in self.state_timestamps.items()
            },
        }

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_states(self):
        """从文件加载状态"""
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 加载状态历史
            for task_id, state_values in data.get("state_history", {}).items():
                self.state_history[task_id] = [HetuState(value) for value in state_values]

            # 加载时间戳
            for task_id, timestamp_strs in data.get("state_timestamps", {}).items():
                self.state_timestamps[task_id] = [
                    datetime.fromisoformat(ts) for ts in timestamp_strs
                ]

        except Exception as e:
            print(f"⚠️  加载状态失败: {e}")
            self.state_history = {}
            self.state_timestamps = {}


class LuoshuScheduler:
    """洛书任务调度器"""

    # 洛书幻方定义（3x3矩阵）
    LUOSHU_MATRIX = [
        [4, 9, 2],  # 第一行：复杂度(4), 正确性(9), 风格(2)
        [3, 5, 7],  # 第二行：可读性(3), 中央调度器(5), 可维护性(7)
        [8, 1, 6],  # 第三行：性能(8), 安全性(1), 可靠性(6)
    ]

    # 位置映射：数字 -> 位置枚举
    POSITION_MAP = {
        1: LuoshuPosition.SECURITY,
        2: LuoshuPosition.STYLE,
        3: LuoshuPosition.READABILITY,
        4: LuoshuPosition.COMPLEXITY,
        5: LuoshuPosition.CENTER,
        6: LuoshuPosition.RELIABILITY,
        7: LuoshuPosition.MAINTAINABILITY,
        8: LuoshuPosition.PERFORMANCE,
        9: LuoshuPosition.CORRECTNESS,
    }

    # 任务类型到位置映射
    TASK_TYPE_POSITIONS = {
        "algorithm": [LuoshuPosition.CORRECTNESS, LuoshuPosition.COMPLEXITY],
        "string": [LuoshuPosition.READABILITY, LuoshuPosition.CORRECTNESS],
        "data_structure": [LuoshuPosition.MAINTAINABILITY, LuoshuPosition.COMPLEXITY],
        "math": [LuoshuPosition.CORRECTNESS, LuoshuPosition.RELIABILITY],
        "general": [LuoshuPosition.CENTER, LuoshuPosition.READABILITY],
    }

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.task_queue: t.List[AssessmentTask] = []
        self.running_tasks: t.Dict[str, AssessmentTask] = {}
        self.completed_tasks: t.List[AssessmentTask] = []
        self.position_load: t.Dict[LuoshuPosition, int] = {pos: 0 for pos in LuoshuPosition}

    def schedule_task(self, task: AssessmentTask) -> AssessmentSchedule:
        """调度任务"""
        # 确定任务需要的位置
        positions = self._determine_positions(task)

        # 计算执行顺序（基于洛书幻方路径）
        execution_order = self._calculate_luoshu_path(positions, task.priority)

        # 计算预计持续时间
        estimated_duration = self._estimate_duration(task, positions)

        # 确定下一个状态
        next_state = self._get_next_state(task.state)

        # 创建调度计划
        schedule = AssessmentSchedule(
            task_id=task.task_id,
            next_state=next_state,
            execution_order=execution_order,
            estimated_duration=estimated_duration,
            priority_boost=self._calculate_priority_boost(task.priority),
        )

        # 添加到队列
        self.task_queue.append(task)
        task.scheduled_positions = positions

        print(f"📅 任务 {task.task_id} 已调度:")
        print(f"   类型: {task.task_type}")
        print(f"   优先级: {task.priority.value}")
        print(f"   当前状态: {task.state.name}")
        print(f"   下一状态: {next_state.name}")
        print(f"   调度位置: {[pos.value for pos in positions]}")
        print(f"   预计时长: {estimated_duration:.1f}秒")

        return schedule

    def execute_schedule(self, schedule: AssessmentSchedule) -> bool:
        """执行调度计划"""
        # 查找任务
        task = next((t for t in self.task_queue if t.task_id == schedule.task_id), None)
        if not task:
            print(f"❌ 找不到任务: {schedule.task_id}")
            return False

        # 检查并发限制
        if len(self.running_tasks) >= self.max_concurrent:
            print(f"⏳ 并发限制达到，任务 {task.task_id} 等待中...")
            return False

        # 从队列移除
        self.task_queue.remove(task)

        # 更新任务状态
        task.start_time = datetime.now()
        # task.state 将在状态转移成功后更新
        self.running_tasks[task.task_id] = task

        # 更新位置负载
        for position in schedule.execution_order:
            self.position_load[position] += 1

        print(f"🚀 开始执行任务 {task.task_id}")
        print(f"   当前状态: {task.state.name} -> {schedule.next_state.name}")
        print(f"   执行顺序: {[pos.value for pos in schedule.execution_order]}")

        return True

    def complete_task(
        self, task_id: str, result: t.Optional[dict] = None, error: t.Optional[str] = None
    ):
        """完成任务"""
        if task_id not in self.running_tasks:
            print(f"❌ 找不到运行中的任务: {task_id}")
            return

        task = self.running_tasks[task_id]

        # 更新任务信息
        task.end_time = datetime.now()
        task.state = HetuState.COMPLETED
        task.result = result
        task.error = error

        # 从运行中移除
        del self.running_tasks[task_id]

        # 添加到已完成列表
        self.completed_tasks.append(task)

        # 减少位置负载
        for position in task.scheduled_positions:
            self.position_load[position] = max(0, self.position_load[position] - 1)

        status = "✅ 成功" if not error else "❌ 失败"
        duration = (task.end_time - task.start_time).total_seconds() if task.start_time else 0
        print(f"{status} 任务 {task_id} 完成，耗时 {duration:.1f}秒")

    def get_system_status(self) -> dict:
        """获取系统状态"""
        return {
            "queue_length": len(self.task_queue),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "position_load": {pos.value: load for pos, load in self.position_load.items()},
            "max_concurrent": self.max_concurrent,
            "throughput": (
                len(self.completed_tasks) / 3600 if self.completed_tasks else 0
            ),  # 任务/小时
        }

    def _determine_positions(self, task: AssessmentTask) -> t.List[LuoshuPosition]:
        """确定任务需要的位置"""
        # 基于任务类型
        base_positions = self.TASK_TYPE_POSITIONS.get(
            task.task_type, self.TASK_TYPE_POSITIONS["general"]
        )

        # 基于优先级添加额外位置
        extra_positions = []
        if task.priority == AssessmentPriority.CRITICAL:
            extra_positions.append(LuoshuPosition.CENTER)  # 中央调度器直接参与
        elif task.priority == AssessmentPriority.HIGH:
            # 高优先级任务添加可靠性检查
            extra_positions.append(LuoshuPosition.RELIABILITY)

        # 合并位置，去重
        all_positions = list(set(base_positions + extra_positions))

        # 确保包含中央调度器（用于协调）
        if LuoshuPosition.CENTER not in all_positions:
            all_positions.append(LuoshuPosition.CENTER)

        return all_positions

    def _calculate_luoshu_path(
        self, positions: t.List[LuoshuPosition], priority: AssessmentPriority
    ) -> t.List[LuoshuPosition]:
        """计算洛书幻方路径"""
        if not positions:
            return []

        # 将位置转换为数字
        position_to_number = {v: k for k, v in self.POSITION_MAP.items()}
        numbers = [position_to_number[pos] for pos in positions if pos in position_to_number]

        if not numbers:
            return positions  # 返回原始位置

        # 确保包含5（中央调度器）
        if 5 not in numbers:
            numbers.append(5)

        # 根据幻方计算最优路径
        path_numbers = self._find_optimal_path(numbers)

        # 转换回位置
        return [self.POSITION_MAP[num] for num in path_numbers if num in self.POSITION_MAP]

    def _find_optimal_path(self, numbers: t.List[int]) -> t.List[int]:
        """在洛书幻方中寻找最优路径"""
        # 简化的路径查找：优先对角线，然后行，然后列

        # 获取所有数字的坐标
        positions = {}
        for i in range(3):
            for j in range(3):
                num = self.LUOSHU_MATRIX[i][j]
                if num in numbers:
                    positions[num] = (i, j)

        if not positions:
            return []

        # 从中央开始（如果存在）
        start_num = 5 if 5 in positions else list(positions.keys())[0]
        path = [start_num]
        visited = {start_num}

        # 贪心算法：每次选择最近的位置
        while len(visited) < len(positions):
            current_pos = positions[path[-1]]
            closest_num = None
            closest_distance = float("inf")

            for num, pos in positions.items():
                if num in visited:
                    continue

                # 计算曼哈顿距离
                distance = abs(pos[0] - current_pos[0]) + abs(pos[1] - current_pos[1])
                if distance < closest_distance:
                    closest_distance = distance
                    closest_num = num

            if closest_num:
                path.append(closest_num)
                visited.add(closest_num)
            else:
                break

        return path

    def _estimate_duration(self, task: AssessmentTask, positions: t.List[LuoshuPosition]) -> float:
        """估计任务持续时间"""
        # 基础时间（秒）
        base_times = {
            LuoshuPosition.COMPLEXITY: 2.0,
            LuoshuPosition.CORRECTNESS: 5.0,
            LuoshuPosition.STYLE: 1.0,
            LuoshuPosition.READABILITY: 2.0,
            LuoshuPosition.MAINTAINABILITY: 3.0,
            LuoshuPosition.PERFORMANCE: 4.0,
            LuoshuPosition.SECURITY: 3.0,
            LuoshuPosition.RELIABILITY: 2.0,
            LuoshuPosition.CENTER: 0.5,  # 协调时间
        }

        # 计算总时间
        total_time = sum(base_times.get(pos, 1.0) for pos in positions)

        # 根据优先级调整
        priority_multiplier = {
            AssessmentPriority.CRITICAL: 0.7,  # 更快执行
            AssessmentPriority.HIGH: 0.8,
            AssessmentPriority.MEDIUM: 1.0,
            AssessmentPriority.LOW: 1.2,
            AssessmentPriority.BATCH: 1.5,  # 批量处理可能更慢
        }

        total_time *= priority_multiplier.get(task.priority, 1.0)

        # 根据代码长度调整
        code_length = len(task.code)
        if code_length > 1000:
            total_time *= 1.5
        elif code_length > 5000:
            total_time *= 2.0

        return total_time

    def _calculate_priority_boost(self, priority: AssessmentPriority) -> float:
        """计算优先级提升系数"""
        boosts = {
            AssessmentPriority.CRITICAL: 2.0,
            AssessmentPriority.HIGH: 1.5,
            AssessmentPriority.MEDIUM: 1.0,
            AssessmentPriority.LOW: 0.7,
            AssessmentPriority.BATCH: 0.5,
        }
        return boosts.get(priority, 1.0)

    def _get_next_state(self, current_state: HetuState) -> HetuState:
        """获取下一个合法状态"""
        # 状态转移规则映射（从HetuStateManager复制简化版）
        state_transitions = {
            HetuState.INITIAL: HetuState.AST_PARSED,
            HetuState.AST_PARSED: HetuState.DIMENSION_ASSESSING,
            HetuState.DIMENSION_ASSESSING: HetuState.RESULT_AGGREGATING,
            HetuState.TEST_RUNNING: HetuState.RESULT_AGGREGATING,
            HetuState.RESULT_AGGREGATING: HetuState.STRATEGY_ANALYZING,
            HetuState.STRATEGY_ANALYZING: HetuState.TREND_PREDICTING,
            HetuState.TREND_PREDICTING: HetuState.REPORT_GENERATING,
            HetuState.REPORT_GENERATING: HetuState.DECISION_SUPPORTING,
            HetuState.DECISION_SUPPORTING: HetuState.COMPLETED,
            HetuState.COMPLETED: HetuState.COMPLETED,  # 最终状态
        }

        # 返回下一个状态，如果没有定义则保持当前状态
        return state_transitions.get(current_state, current_state)


class HetuLuoshuScheduler:
    """河图洛书调度器主类"""

    def __init__(self, state_file: t.Optional[str] = None, max_concurrent: int = 5):
        self.state_manager = HetuStateManager(state_file)
        self.luoshu_scheduler = LuoshuScheduler(max_concurrent)
        self.tasks: t.Dict[str, AssessmentTask] = {}
        self.task_schedules: t.Dict[str, AssessmentSchedule] = {}

    def submit_task(
        self,
        code: str,
        task_type: str = "general",
        priority: AssessmentPriority = AssessmentPriority.MEDIUM,
        context: t.Optional[dict] = None,
        test_cases: t.Optional[list] = None,
    ) -> str:
        """提交评估任务"""
        # 生成任务ID
        import hashlib

        task_id = f"task_{hashlib.md5(f'{code}{task_type}{datetime.now().isoformat()}'.encode()).hexdigest()[:8]}"

        # 创建任务
        task = AssessmentTask(
            task_id=task_id,
            code=code,
            task_type=task_type,
            priority=priority,
            context=context or {},
            test_cases=test_cases,
        )

        # 存储任务
        self.tasks[task_id] = task

        # 调度任务
        schedule = self.luoshu_scheduler.schedule_task(task)
        self.task_schedules[task_id] = schedule

        print(f"📤 任务提交成功: {task_id}")
        print(f"   调度ID: {schedule.task_id}")
        print(f"   下一个状态: {schedule.next_state.name}")

        return task_id

    def execute_task(self, task_id: str) -> bool:
        """执行任务"""
        if task_id not in self.tasks:
            print(f"❌ 找不到任务: {task_id}")
            return False

        task = self.tasks[task_id]

        # 获取调度计划（从存储中获取）
        if task_id not in self.task_schedules:
            print(f"⚠️  任务 {task_id} 没有调度计划，重新调度")
            schedule = self.luoshu_scheduler.schedule_task(task)
            self.task_schedules[task_id] = schedule
        else:
            schedule = self.task_schedules[task_id]

        if not schedule:
            print(f"❌ 无法获取调度计划: {task_id}")
            return False

        # 执行调度
        if not self.luoshu_scheduler.execute_schedule(schedule):
            return False

        # 更新状态
        self.state_manager.transition(task_id, task.state, schedule.next_state)
        task.state = schedule.next_state

        return True

    def get_task_status(self, task_id: str) -> t.Optional[dict]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]

        return {
            "task_id": task.task_id,
            "state": task.state.name,
            "state_value": task.state.value,
            "priority": task.priority.value,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "start_time": task.start_time.isoformat() if task.start_time else None,
            "end_time": task.end_time.isoformat() if task.end_time else None,
            "has_result": task.result is not None,
            "has_error": task.error is not None,
            "in_queue": task in self.luoshu_scheduler.task_queue,
            "is_running": task_id in self.luoshu_scheduler.running_tasks,
            "is_completed": task in self.luoshu_scheduler.completed_tasks,
        }

    def get_system_report(self) -> dict:
        """获取系统报告"""
        status = self.luoshu_scheduler.get_system_status()

        return {
            "scheduler_status": status,
            "total_tasks": len(self.tasks),
            "state_manager": {
                "tracked_tasks": len(self.state_manager.state_history),
                "state_file": self.state_manager.state_file,
            },
            "timestamp": datetime.now().isoformat(),
        }

    def save_state(self, filepath: str):
        """保存系统状态"""
        data = {
            "tasks": {task_id: task.to_dict() for task_id, task in self.tasks.items()},
            "scheduler_status": self.luoshu_scheduler.get_system_status(),
            "saved_at": datetime.now().isoformat(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 系统状态已保存到: {filepath}")


# 使用示例
if __name__ == "__main__":
    print("🚀 河图洛书调度器演示")
    print("=" * 60)

    # 创建调度器
    scheduler = HetuLuoshuScheduler(state_file="/tmp/hetu_luoshu_state.json", max_concurrent=3)

    # 示例代码
    sample_codes = [
        (
            """
def fibonacci(n):
    \"\"\"计算斐波那契数列\"\"\"
    if n <= 1:
        return n
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b
""",
            "algorithm",
            AssessmentPriority.HIGH,
        ),
        (
            """
def validate_email(email):
    \"\"\"验证邮箱格式\"\"\"
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
""",
            "string",
            AssessmentPriority.MEDIUM,
        ),
        (
            """
class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        if not self.is_empty():
            return self.items.pop()
        return None

    def is_empty(self):
        return len(self.items) == 0
""",
            "data_structure",
            AssessmentPriority.LOW,
        ),
    ]

    # 提交任务
    task_ids = []
    for i, (code, task_type, priority) in enumerate(sample_codes):
        task_id = scheduler.submit_task(
            code=code, task_type=task_type, priority=priority, context={"sample_index": i + 1}
        )
        task_ids.append(task_id)

    print(f"\n📋 已提交 {len(task_ids)} 个任务")

    # 执行任务
    print("\n▶️  开始执行任务...")
    for task_id in task_ids:
        if scheduler.execute_task(task_id):
            print(f"  任务 {task_id} 开始执行")
        else:
            print(f"  任务 {task_id} 执行失败或等待中")

    # 获取系统状态
    print("\n📊 系统状态报告:")
    report = scheduler.get_system_report()
    print(f"  总任务数: {report['total_tasks']}")
    print(f"  队列中: {report['scheduler_status']['queue_length']}")
    print(f"  运行中: {report['scheduler_status']['running_tasks']}")
    print(f"  已完成: {report['scheduler_status']['completed_tasks']}")

    # 保存状态
    scheduler.save_state("/tmp/hetu_luoshu_demo_state.json")

    print("\n🎉 演示完成！")
    print("提示: 在实际系统中，需要集成评估引擎来实际执行代码评估")
