#!/usr/bin/env python3
"""
河图状态到64卦适配器（重构第三阶段）

此适配器提供河图10态与64卦状态系统之间的双向映射，
保持与现有HetuStateManager的API兼容性，同时支持格雷编码转换。

设计目标：
1. 向后兼容：现有代码无需修改即可使用
2. 透明升级：无缝替换原有的HetuStateManager
3. 状态丰富：将10态状态扩展为64卦状态空间
4. 智能转换：基于汉明距离和语义相似度的状态转换
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from integrated_hexagram_state_manager import (
    HetuState,
    IntegratedHexagramStateManager,
    StateAnalysis,
)


@dataclass
class TaskStateRecord:
    """任务状态记录"""

    task_id: str
    current_hexagram: str  # 当前卦象状态（6位二进制）
    state_history: List[str] = field(default_factory=list)  # 卦象状态历史
    hetu_history: List[HetuState] = field(default_factory=list)  # 河图状态历史
    timestamps: List[datetime] = field(default_factory=list)  # 状态变更时间
    metadata: Dict[str, Any] = field(default_factory=dict)  # 任务元数据


class HetuToHexagramAdapter:
    """河图状态到64卦的适配器（保持API兼容）"""

    def __init__(
        self,
        mapping_file_path: str = "hetu_hexagram_mapping.json",
        state_file: Optional[str] = None,
    ):
        """
        初始化适配器

        Args:
            mapping_file_path: 河图-卦象映射文件路径
            state_file: 状态持久化文件路径（与HetuStateManager兼容）
        """
        self.hexagram_manager = IntegratedHexagramStateManager(mapping_file_path)
        self.state_file = state_file

        # 任务状态存储（task_id -> TaskStateRecord）
        self.task_states: Dict[str, TaskStateRecord] = {}

        # 河图状态到卦象集合的快速映射
        self.hetu_to_hexagrams = self._build_hetu_mapping()

        # 加载持久化状态
        if state_file and os.path.exists(state_file):
            self.load_states()

        print("🔌 河图到64卦适配器初始化完成")
        print(f"   映射文件: {mapping_file_path}")
        print(f"   状态文件: {state_file or '内存模式'}")

    def _build_hetu_mapping(self) -> Dict[HetuState, Set[str]]:
        """构建河图状态到卦象集合的映射"""
        mapping = {}
        for state in HetuState:
            hexagrams = self.hexagram_manager.get_states_by_hetu(state)
            mapping[state] = set(hexagrams)
        return mapping

    def _select_nearest_hexagram(
        self, current_hexagram: str, target_hexagrams: Set[str]
    ) -> str:
        """
        选择与当前卦象汉明距离最近的目标卦象

        Args:
            current_hexagram: 当前卦象状态
            target_hexagrams: 目标卦象集合

        Returns:
            最近的目标卦象
        """
        if not target_hexagrams:
            return current_hexagram  # 无目标卦象，保持当前状态

        # 计算到所有目标卦象的汉明距离
        distances = []
        for target in target_hexagrams:
            distance = self.hexagram_manager.hamming_distance(current_hexagram, target)
            distances.append((distance, target))

        # 选择最小距离的卦象
        distances.sort()
        return distances[0][1]

    def transition(
        self, task_id: str, current_state: HetuState, target_state: HetuState
    ) -> bool:
        """
        执行河图状态转移（兼容HetuStateManager接口）

        Args:
            task_id: 任务ID
            current_state: 当前河图状态
            target_state: 目标河图状态

        Returns:
            转移是否成功
        """
        # 获取或初始化任务状态记录
        if task_id not in self.task_states:
            # 新任务：初始化为该河图状态的第一个卦象
            target_hexagrams = self.hetu_to_hexagrams.get(current_state, set())
            if not target_hexagrams:
                print(f"❌ 任务 {task_id}: 无效初始河图状态 {current_state.name}")
                return False

            initial_hexagram = next(iter(target_hexagrams))

            # 如果目标状态与初始状态相同，记录初始状态到历史
            # 否则，先不记录初始状态，等转换完成后再记录目标状态
            if target_state == current_state:
                self.task_states[task_id] = TaskStateRecord(
                    task_id=task_id,
                    current_hexagram=initial_hexagram,
                    state_history=[initial_hexagram],
                    hetu_history=[current_state],
                    timestamps=[datetime.now()],
                )
                print(
                    f"📝 任务 {task_id}: 初始化卦象状态 {initial_hexagram} ({current_state.name})"
                )
                return True
            else:
                # 目标状态不同，先不记录初始状态到历史
                # 转换完成后再记录目标状态
                self.task_states[task_id] = TaskStateRecord(
                    task_id=task_id,
                    current_hexagram=initial_hexagram,
                    state_history=[],  # 先不记录初始状态
                    hetu_history=[],  # 先不记录河图状态
                    timestamps=[],
                )
                print(
                    f"📝 任务 {task_id}: 创建任务，初始卦象 {initial_hexagram}，等待转换到 {target_state.name}"
                )

        task_record = self.task_states[task_id]
        current_hexagram = task_record.current_hexagram

        # 验证当前河图状态是否与卦象匹配
        current_hexagram_hetu = self.hexagram_manager.get_hetu_state(current_hexagram)
        if current_hexagram_hetu is None or current_hexagram_hetu != current_state:
            hetu_name = (
                current_hexagram_hetu.name if current_hexagram_hetu else "unknown"
            )
            print(
                f"⚠️  任务 {task_id}: 卦象{current_hexagram}的河图状态{hetu_name} "
                f"与请求的当前状态{current_state.name}不匹配，自动修正"
            )

        # 获取目标河图状态对应的卦象集合
        target_hexagrams = self.hetu_to_hexagrams.get(target_state, set())
        if not target_hexagrams:
            print(f"❌ 任务 {task_id}: 无效目标河图状态 {target_state.name}")
            return False

        # 选择最近的目标卦象
        target_hexagram = self._select_nearest_hexagram(
            current_hexagram, target_hexagrams
        )

        # 计算汉明距离
        distance = self.hexagram_manager.hamming_distance(
            current_hexagram, target_hexagram
        )

        # 执行卦象转换（必须满足格雷编码约束）
        if distance == 1:
            # 直接转换
            success = self._execute_hexagram_transition(
                task_id, current_hexagram, target_hexagram, target_state
            )
        else:
            # 需要多步转换：寻找路径
            path = self._find_hexagram_path(current_hexagram, target_hexagram)
            if not path:
                print(
                    f"❌ 任务 {task_id}: 无法找到从 {current_hexagram} 到 {target_hexagram} 的路径"
                )
                return False

            success = True
            # 对于多步转换，只记录最终状态到历史
            # 中间步骤只更新卦象管理器状态
            for i in range(1, len(path)):
                step_hexagram = path[i]
                step_hetu = self.hexagram_manager.get_hetu_state(step_hexagram)

                if step_hetu is None:
                    print(f"❌ 任务 {task_id}: 卦象 {step_hexagram} 无效")
                    success = False
                    break

                if i == len(path) - 1:
                    # 最终步骤：记录到历史
                    step_success = self._execute_hexagram_transition(
                        task_id, path[i - 1], step_hexagram, step_hetu
                    )
                else:
                    # 中间步骤：只更新卦象管理器状态，不记录历史
                    task_record = self.task_states[task_id]
                    task_record.current_hexagram = step_hexagram
                    # 更新卦象管理器状态
                    self.hexagram_manager.current_state = step_hexagram
                    step_success = True

                if not step_success:
                    success = False
                    break

        # 持久化状态
        if success and self.state_file:
            self.save_states()

        return success

    def _execute_hexagram_transition(
        self, task_id: str, from_hexagram: str, to_hexagram: str, target_hetu: HetuState
    ) -> bool:
        """执行单个卦象转换"""
        task_record = self.task_states[task_id]

        # 更新任务状态记录
        task_record.current_hexagram = to_hexagram
        task_record.state_history.append(to_hexagram)
        task_record.hetu_history.append(target_hetu)
        task_record.timestamps.append(datetime.now())

        # 在卦象管理器中记录转换（用于全局分析）
        # 注意：卦象管理器只跟踪单个当前状态，我们将其设置为最新转换
        self.hexagram_manager.current_state = to_hexagram

        from_name = self.hexagram_manager.get_hexagram_name(from_hexagram)
        to_name = self.hexagram_manager.get_hexagram_name(to_hexagram)

        print(
            f"🔄 任务 {task_id}: 卦象转换 {from_hexagram} ({from_name}) → {to_hexagram} ({to_name})"
        )
        from_hetu = self.hexagram_manager.get_hetu_state(from_hexagram)
        print(
            f"   河图状态: {from_hetu.name if from_hetu else 'unknown'} → "
            f"{target_hetu.name}"
        )
        print(
            f"   汉明距离: {self.hexagram_manager.hamming_distance(from_hexagram, to_hexagram)}"
        )

        return True

    def _find_hexagram_path(
        self, from_hexagram: str, to_hexagram: str, max_steps: int = 10
    ) -> List[str]:
        """查找卦象之间的转换路径（优先使用缓存）"""
        # Phase 22优化: 优先使用缓存路径
        try:
            # 尝试从缓存获取路径
            cached_path = self.hexagram_manager.cache_manager.find_path(
                from_hexagram, to_hexagram
            )
            if cached_path:
                # 检查路径长度是否在max_steps限制内
                if len(cached_path) - 1 <= max_steps:
                    return cached_path
                # 路径太长，回退到BFS搜索更短路径
        except Exception as e:
            print(f"⚠️  缓存路径查找失败，回退到BFS: {e}")
            # 继续执行BFS

        # 缓存未命中或路径太长，使用BFS搜索
        return self._find_hexagram_path_bfs(from_hexagram, to_hexagram, max_steps)

    def _find_hexagram_path_bfs(
        self, from_hexagram: str, to_hexagram: str, max_steps: int = 10
    ) -> List[str]:
        """BFS搜索卦象转换路径（回退实现）"""
        from collections import deque

        if from_hexagram == to_hexagram:
            return [from_hexagram]

        queue = deque([(from_hexagram, [from_hexagram])])
        visited = {from_hexagram}

        while queue:
            current, path = queue.popleft()

            if len(path) > max_steps:
                continue

            # 生成所有可能的下一步状态（只改变1位）
            for i in range(6):
                bits = list(current)
                bits[i] = "1" if bits[i] == "0" else "0"
                next_state = "".join(bits)

                # 检查是否为有效状态
                if not self.hexagram_manager._validate_state(next_state):
                    continue

                if next_state == to_hexagram:
                    return path + [next_state]

                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [next_state]))

        return []

    def get_next_states(self, current_state: HetuState) -> List[HetuState]:
        """
        获取可能的下一河图状态（兼容HetuStateManager接口）

        Args:
            current_state: 当前河图状态

        Returns:
            可能的下一状态列表
        """
        # 简化实现：返回按值排序的后续状态
        all_states = list(HetuState)
        current_index = all_states.index(current_state)

        if current_index >= len(all_states) - 1:
            return []  # 最终状态

        # 返回当前状态之后的状态
        return all_states[current_index + 1 :]

    def get_shortest_path(
        self, from_state: HetuState, to_state: HetuState
    ) -> List[HetuState]:
        """
        获取河图状态之间的最短路径（兼容HetuStateManager接口）

        Args:
            from_state: 起始河图状态
            to_state: 目标河图状态

        Returns:
            最短路径（河图状态列表）
        """
        # 简化实现：返回从起始到目标的所有中间状态
        all_states = list(HetuState)

        try:
            from_index = all_states.index(from_state)
            to_index = all_states.index(to_state)
        except ValueError:
            return []

        if from_index > to_index:
            return []  # 不能向后退

        return all_states[from_index : to_index + 1]

    def get_task_hexagram_state(self, task_id: str) -> Optional[str]:
        """获取任务的当前卦象状态"""
        if task_id not in self.task_states:
            return None
        return self.task_states[task_id].current_hexagram

    def get_task_hetu_state(self, task_id: str) -> Optional[HetuState]:
        """获取任务的当前河图状态"""
        hexagram = self.get_task_hexagram_state(task_id)
        if hexagram is None:
            return None
        return self.hexagram_manager.get_hetu_state(hexagram)

    def analyze_task_state(self, task_id: str) -> Optional[StateAnalysis]:
        """分析任务状态"""
        hexagram = self.get_task_hexagram_state(task_id)
        if hexagram is None:
            return None
        return self.hexagram_manager.analyze_state(hexagram)

    def save_states(self) -> None:
        """保存状态到文件（兼容HetuStateManager接口）"""
        if not self.state_file:
            return

        data: Dict[str, Any] = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "description": "河图-64卦适配器状态文件",
            "task_states": {},
        }

        for task_id, record in self.task_states.items():
            data["task_states"][task_id] = {
                "current_hexagram": record.current_hexagram,
                "state_history": record.state_history,
                "hetu_history": [state.value for state in record.hetu_history],
                "timestamps": [ts.isoformat() for ts in record.timestamps],
                "metadata": record.metadata,
            }

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 适配器状态已保存到: {self.state_file}")

    def load_states(self) -> None:
        """从文件加载状态（兼容HetuStateManager接口）"""
        if self.state_file is None:
            return

        # 检查文件是否存在且不为空
        if not os.path.exists(self.state_file):
            print(f"📂 状态文件不存在: {self.state_file}")
            return

        try:
            # 检查文件是否为空
            if os.path.getsize(self.state_file) == 0:
                print(f"📂 状态文件为空: {self.state_file}，跳过加载")
                return

            with open(self.state_file, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # 如果文件只有空白字符，跳过加载
            if not content:
                print(f"📂 状态文件只包含空白字符: {self.state_file}，跳过加载")
                return

            data = json.loads(content)

            # 清空现有状态
            self.task_states.clear()

            # 加载任务状态
            for task_id, state_data in data.get("task_states", {}).items():
                hetu_history = [
                    HetuState(value) for value in state_data.get("hetu_history", [])
                ]
                timestamps = [
                    datetime.fromisoformat(ts)
                    for ts in state_data.get("timestamps", [])
                ]

                record = TaskStateRecord(
                    task_id=task_id,
                    current_hexagram=state_data.get("current_hexagram", "000000"),
                    state_history=state_data.get("state_history", []),
                    hetu_history=hetu_history,
                    timestamps=timestamps,
                    metadata=state_data.get("metadata", {}),
                )

                self.task_states[task_id] = record

            print(f"📂 从 {self.state_file} 加载了 {len(self.task_states)} 个任务状态")

        except json.JSONDecodeError as e:
            print(f"⚠️  状态文件JSON格式错误: {e}")
            print(f"   文件路径: {self.state_file}")
            # 保持空状态，不抛出异常
            self.task_states = {}
        except Exception as e:
            print(f"⚠️  加载适配器状态失败: {e}")
            self.task_states = {}

    def get_state_report(self) -> Dict[str, Any]:
        """获取状态报告"""
        return {
            "total_tasks": len(self.task_states),
            "hexagram_manager": {
                "total_mappings": len(self.hexagram_manager.mappings),
                "current_state": self.hexagram_manager.current_state,
                "state_history_count": len(self.hexagram_manager.state_history),
            },
            "task_summary": {
                task_id: {
                    "current_hexagram": record.current_hexagram,
                    "current_hetu": (
                        hetu_state.name
                        if (
                            hetu_state := self.hexagram_manager.get_hetu_state(
                                record.current_hexagram
                            )
                        )
                        else "unknown"
                    ),
                    "history_length": len(record.state_history),
                    "last_update": (
                        record.timestamps[-1].isoformat() if record.timestamps else None
                    ),
                }
                for task_id, record in self.task_states.items()
            },
        }


def test_adapter() -> None:
    """测试适配器功能"""
    print("=== 河图到64卦适配器测试 ===")

    try:
        # 创建适配器
        adapter = HetuToHexagramAdapter()

        # 测试1: 新任务状态转移
        print("\n🔧 测试1: 新任务状态转移...")
        task_id = "test_task_001"

        success = adapter.transition(task_id, HetuState.INITIAL, HetuState.AST_PARSED)
        print(f"   转移结果: {'成功' if success else '失败'}")

        if success:
            hexagram = adapter.get_task_hexagram_state(task_id)
            hetu = adapter.get_task_hetu_state(task_id)
            print(f"   当前卦象: {hexagram}")
            print(f"   当前河图: {hetu.name if hetu else '无'}")

        # 测试2: 继续状态转移
        print("\n🔄 测试2: 继续状态转移...")
        success = adapter.transition(task_id, HetuState.AST_PARSED, HetuState.COMPLETED)
        print(f"   转移结果: {'成功' if success else '失败'}")

        if success:
            analysis = adapter.analyze_task_state(task_id)
            if analysis:
                print(f"   当前卦象: {analysis.hexagram_name}")
                print(f"   质量评分: {analysis.quality_score:.2f}/10")
                print(f"   激活维度: {len(analysis.active_dimensions)}个")

        # 测试3: 状态报告
        print("\n📊 测试3: 状态报告...")
        report = adapter.get_state_report()
        print(f"   总任务数: {report['total_tasks']}")
        print(f"   卦象映射数: {report['hexagram_manager']['total_mappings']}")

        # 测试4: 保存和加载状态
        print("\n💾 测试4: 状态持久化...")
        test_state_file = "/tmp/hetu_hexagram_adapter_test.json"
        adapter.state_file = test_state_file
        adapter.save_states()

        # 创建新适配器并加载状态
        adapter2 = HetuToHexagramAdapter(state_file=test_state_file)
        report2 = adapter2.get_state_report()
        print(f"   加载后任务数: {report2['total_tasks']}")

        # 清理测试文件
        if os.path.exists(test_state_file):
            os.remove(test_state_file)

        print("\n🎉 适配器测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_adapter()
