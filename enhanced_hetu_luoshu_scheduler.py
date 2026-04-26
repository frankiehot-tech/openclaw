#!/usr/bin/env python3
"""
增强的河图洛书调度器（集成64卦状态）

此调度器继承自原有的HetuLuoshuScheduler，但使用HetuToHexagramAdapter
替代HetuStateManager，从而支持64卦状态空间和格雷编码转换。

特性：
1. 向后兼容：完全兼容原有的API接口
2. 状态丰富：河图10态扩展为64卦状态空间
3. 智能转换：基于汉明距离的状态转移优化
4. 增强分析：提供卦象级别的状态分析和质量评估
"""

import typing as t
from datetime import datetime

# 导入我们的适配器和状态管理器
from hetu_hexagram_adapter import HetuToHexagramAdapter

# 使用我们自己的HetuState（来自64卦状态系统）
from integrated_hexagram_state_manager import HetuState, StateAnalysis

# 导入原有的调度器组件
from mini_agent.agent.core.maref_quality.hetu_luoshu_scheduler import (
    AssessmentPriority,
    AssessmentSchedule,
    AssessmentTask,
    HetuLuoshuScheduler,
    LuoshuScheduler,
)


def convert_to_integrated_hetu_state(legacy_state: t.Any) -> HetuState:
    """将原有的HetuState转换为集成的HetuState枚举"""
    # 通过状态名称进行转换
    state_name = legacy_state.name if hasattr(legacy_state, "name") else str(legacy_state)

    try:
        return HetuState[state_name]
    except KeyError:
        # 如果找不到对应的状态，使用INITIAL作为默认
        return HetuState.INITIAL


def convert_from_integrated_hetu_state(integrated_state: HetuState) -> t.Any:
    """将集成的HetuState转换回原有的HetuState枚举"""
    # 我们需要获取mini_agent的HetuState，但为了避免循环导入，我们动态导入
    from mini_agent.agent.core.maref_quality.hetu_luoshu_scheduler import (
        HetuState as LegacyHetuState,
    )

    try:
        return LegacyHetuState[integrated_state.name]
    except (KeyError, AttributeError):
        # 如果转换失败，返回默认状态
        return LegacyHetuState.INITIAL


class HexagramEnhancedLuoshuScheduler(HetuLuoshuScheduler):  # type: ignore[misc]
    """增强的河图洛书调度器（集成64卦状态）"""

    def __init__(
        self,
        mapping_file_path: str = "hetu_hexagram_mapping.json",
        state_file: t.Optional[str] = None,
        max_concurrent: int = 5,
    ):
        """
        初始化增强调度器

        Args:
            mapping_file_path: 河图-卦象映射文件路径
            state_file: 状态持久化文件路径
            max_concurrent: 最大并发任务数
        """
        # 使用适配器替代原有的状态管理器
        self.hexagram_adapter = HetuToHexagramAdapter(
            mapping_file_path=mapping_file_path, state_file=state_file
        )

        # 初始化父类（但跳过父类的state_manager初始化）
        # 我们手动创建luoshu_scheduler和任务存储
        self.luoshu_scheduler = LuoshuScheduler(max_concurrent)
        self.tasks: t.Dict[str, AssessmentTask] = {}
        self.task_schedules: t.Dict[str, AssessmentSchedule] = {}

        # 状态文件路径
        self.state_file = state_file

        print("🚀 增强河图洛书调度器初始化完成")
        print(
            f"   使用64卦状态空间（{len(self.hexagram_adapter.hexagram_manager.mappings)}个卦象）"
        )
        print(f"   最大并发数: {max_concurrent}")

    def submit_task(
        self,
        code: str,
        task_type: str = "general",
        priority: AssessmentPriority = AssessmentPriority.MEDIUM,
        context: t.Optional[t.Dict[str, t.Any]] = None,
        test_cases: t.Optional[t.List[t.Any]] = None,
    ) -> str:
        """提交评估任务（增强版）"""
        # 调用父类方法创建任务
        task_id: str = super().submit_task(code, task_type, priority, context, test_cases)

        # 使用适配器初始化任务状态（初始化为INITIAL状态）
        self.hexagram_adapter.transition(task_id, HetuState.INITIAL, HetuState.INITIAL)

        # 增强任务状态报告
        hexagram_state = self.hexagram_adapter.get_task_hexagram_state(task_id)
        hexagram_name = self.hexagram_adapter.hexagram_manager.get_hexagram_name(hexagram_state)

        print(f"   初始卦象: {hexagram_state} ({hexagram_name})")
        hetu_state = self.hexagram_adapter.hexagram_manager.get_hetu_state(hexagram_state)
        if hetu_state:
            print(f"   状态详情: {hetu_state.name}")
        else:
            print("   状态详情: 未知")

        return task_id

    def execute_task(self, task_id: str) -> bool:
        """执行任务（增强版，使用卦象状态转移）"""
        if task_id not in self.tasks:
            print(f"❌ 找不到任务: {task_id}")
            return False

        task = self.tasks[task_id]

        # 获取调度计划
        if task_id not in self.task_schedules:
            print(f"⚠️  任务 {task_id} 没有调度计划，重新调度")
            schedule = self.luoshu_scheduler.schedule_task(task)
            self.task_schedules[task_id] = schedule
        else:
            schedule = self.task_schedules[task_id]

        if not schedule:
            print(f"❌ 无法获取调度计划: {task_id}")
            return False

        # 使用适配器进行状态转移（转换状态枚举）
        current_hetu_state = convert_to_integrated_hetu_state(task.state)
        target_hetu_state = convert_to_integrated_hetu_state(schedule.next_state)

        print(f"📊 任务 {task_id} 状态转移:")
        print(f"   当前河图状态: {current_hetu_state.name}")
        print(f"   目标河图状态: {target_hetu_state.name}")

        # 获取当前卦象状态
        current_hexagram = self.hexagram_adapter.get_task_hexagram_state(task_id)
        if current_hexagram:
            hexagram_name = self.hexagram_adapter.hexagram_manager.get_hexagram_name(
                current_hexagram
            )
            print(f"   当前卦象: {current_hexagram} ({hexagram_name})")

        # 执行状态转移
        success = self.hexagram_adapter.transition(task_id, current_hetu_state, target_hetu_state)

        if not success:
            print(f"❌ 任务 {task_id}: 状态转移失败")
            return False

        # 执行调度
        if not self.luoshu_scheduler.execute_schedule(schedule):
            print(f"❌ 任务 {task_id}: 调度执行失败")
            return False

        # 更新任务的河图状态（转换回原有格式）
        task.state = convert_from_integrated_hetu_state(target_hetu_state)

        # 获取转移后的卦象状态
        new_hexagram = self.hexagram_adapter.get_task_hexagram_state(task_id)
        if new_hexagram and new_hexagram != current_hexagram:
            new_hexagram_name = self.hexagram_adapter.hexagram_manager.get_hexagram_name(
                new_hexagram
            )
            print(f"   新卦象: {new_hexagram} ({new_hexagram_name})")

            # 分析新状态的质量
            analysis = self.hexagram_adapter.analyze_task_state(task_id)
            if analysis:
                print(f"   质量评分: {analysis.quality_score:.2f}/10")
                print(f"   激活维度: {len(analysis.active_dimensions)}个")

        return True

    def get_task_status(self, task_id: str) -> t.Optional[t.Dict[str, t.Any]]:
        """获取任务状态（增强版，包含卦象信息）"""
        base_status = super().get_task_status(task_id)
        if base_status is None:
            return None

        # 添加卦象信息
        hexagram_state = self.hexagram_adapter.get_task_hexagram_state(task_id)
        if hexagram_state:
            analysis = self.hexagram_adapter.analyze_task_state(task_id)
            if analysis:
                base_status.update(
                    {
                        "hexagram_state": hexagram_state,
                        "hexagram_name": analysis.hexagram_name,
                        "hexagram_code": analysis.hexagram_code,
                        "quality_score": analysis.quality_score,
                        "active_dimensions": analysis.active_dimensions,
                        "inactive_dimensions": analysis.inactive_dimensions,
                        "evolution_distance_to_perfect": analysis.evolution_distance_to_perfect,
                    }
                )

        return base_status  # type: ignore[no-any-return]

    def get_hexagram_analysis(self, task_id: str) -> t.Optional[StateAnalysis]:
        """获取任务的卦象分析"""
        return self.hexagram_adapter.analyze_task_state(task_id)

    def get_system_report(self) -> t.Dict[str, t.Any]:
        """获取系统报告（增强版，包含卦象统计）"""
        # 获取调度器状态
        status = self.luoshu_scheduler.get_system_status()

        # 构建基本报告（不依赖父类的state_manager）
        base_report = {
            "scheduler_status": status,
            "total_tasks": len(self.tasks),
            "timestamp": datetime.now().isoformat(),
        }

        # 添加卦象统计
        hexagram_stats = self._collect_hexagram_statistics()

        # 添加适配器信息
        base_report["hexagram_adapter"] = {
            "total_tasks": len(self.hexagram_adapter.task_states),
            "state_file": self.hexagram_adapter.state_file,
            "hexagram_manager": {
                "total_mappings": len(self.hexagram_adapter.hexagram_manager.mappings),
                "current_global_state": self.hexagram_adapter.hexagram_manager.current_state,
                "state_history_count": len(self.hexagram_adapter.hexagram_manager.state_history),
            },
        }

        # 添加卦象统计
        base_report["hexagram_statistics"] = hexagram_stats

        return base_report

    def _collect_hexagram_statistics(self) -> t.Dict[str, t.Any]:
        """收集卦象统计信息"""
        stats: t.Dict[str, t.Any] = {
            "hexagram_distribution": {},
            "quality_scores": {},
            "dimension_activation": {},
        }

        # 收集所有任务的卦象分布
        hexagram_counts: t.Dict[str, int] = {}
        total_quality: float = 0.0
        task_count = 0

        dimension_counts: t.Dict[str, int] = {
            "correctness": 0,
            "complexity": 0,
            "style": 0,
            "readability": 0,
            "maintainability": 0,
            "cost_efficiency": 0,
        }

        for task_id in self.tasks:
            analysis = self.hexagram_adapter.analyze_task_state(task_id)
            if analysis:
                # 卦象分布
                hexagram_name = analysis.hexagram_name
                hexagram_counts[hexagram_name] = hexagram_counts.get(hexagram_name, 0) + 1

                # 质量评分
                total_quality += analysis.quality_score
                task_count += 1

                # 维度激活统计
                for dim in analysis.active_dimensions:
                    dimension_counts[dim] = dimension_counts.get(dim, 0) + 1

        stats["hexagram_distribution"] = hexagram_counts
        stats["quality_scores"] = {
            "average": total_quality / task_count if task_count > 0 else 0,
            "total_tasks": task_count,
            "total_quality": total_quality,
        }
        stats["dimension_activation"] = dimension_counts

        return stats

    def visualize_hexagram_space(self) -> str:
        """可视化卦象状态空间（文本表示）"""
        # 获取适配器的卦象管理器
        hexagram_manager = self.hexagram_adapter.hexagram_manager

        # 使用卦象管理器的可视化功能
        highlight_states = [
            HetuState.INITIAL,
            HetuState.COMPLETED,
            HetuState.STRATEGY_ANALYZING,
        ]

        visualization = hexagram_manager.visualize_state_space(
            highlight_hetu_states=highlight_states
        )

        # 添加任务相关的统计
        lines = visualization.split("\n")

        # 在适当位置插入任务统计
        task_stats_idx = -1
        for i, line in enumerate(lines):
            if "状态历史统计:" in line:
                task_stats_idx = i
                break

        if task_stats_idx > 0:
            # 添加任务统计
            task_stats = [
                "",
                "📋 任务卦象统计:",
                f"   总任务数: {len(self.tasks)}",
                f"   已跟踪状态任务: {len(self.hexagram_adapter.task_states)}",
            ]

            # 合并行
            lines = lines[:task_stats_idx] + task_stats + lines[task_stats_idx:]

        return "\n".join(lines)

    def save_state(self, filepath: str) -> None:
        """保存系统状态（增强版，包含卦象状态）"""
        # 保存适配器状态
        if self.hexagram_adapter.state_file:
            self.hexagram_adapter.save_states()

        # 调用父类保存基本状态
        super().save_state(filepath)

        print("💾 增强系统状态已保存（包含64卦状态）")


def test_enhanced_scheduler() -> None:
    """测试增强调度器"""
    print("=== 增强河图洛书调度器测试 ===")

    try:
        # 创建增强调度器
        scheduler = HexagramEnhancedLuoshuScheduler(
            state_file="/tmp/enhanced_hetu_luoshu_test.json", max_concurrent=2
        )

        # 测试1: 提交任务
        print("\n📤 测试1: 提交任务...")
        sample_code = """
def fibonacci(n):
    \"\"\"计算斐波那契数列\"\"\"
    if n <= 1:
        return n
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b
"""

        task_id = scheduler.submit_task(
            code=sample_code,
            task_type="algorithm",
            priority=AssessmentPriority.HIGH,
            context={"test": True},
        )

        print(f"   任务ID: {task_id}")

        # 测试2: 执行任务
        print("\n▶️  测试2: 执行任务...")
        success = scheduler.execute_task(task_id)
        print(f"   执行结果: {'成功' if success else '失败'}")

        # 测试3: 获取任务状态
        print("\n📊 测试3: 获取任务状态...")
        status = scheduler.get_task_status(task_id)
        if status:
            print(f"   任务状态: {status.get('state', '未知')}")
            print(f"   卦象状态: {status.get('hexagram_state', '未知')}")
            print(f"   质量评分: {status.get('quality_score', 0):.2f}/10")

        # 测试4: 获取系统报告
        print("\n📈 测试4: 获取系统报告...")
        report = scheduler.get_system_report()
        print(f"   总任务数: {report['total_tasks']}")
        print(f"   卦象适配器任务数: {report['hexagram_adapter']['total_tasks']}")

        # 测试5: 可视化卦象空间
        print("\n🗺️  测试5: 可视化卦象空间...")
        visualization = scheduler.visualize_hexagram_space()
        # 只显示部分可视化内容
        lines = visualization.split("\n")
        for i, line in enumerate(lines[:30]):  # 只显示前30行
            print(line)

        print("\n... (可视化内容截断) ...")

        # 测试6: 保存状态
        print("\n💾 测试6: 保存系统状态...")
        scheduler.save_state("/tmp/enhanced_scheduler_state.json")

        # 清理测试文件
        import os

        test_files = [
            "/tmp/enhanced_hetu_luoshu_test.json",
            "/tmp/enhanced_scheduler_state.json",
        ]
        for file in test_files:
            if os.path.exists(file):
                os.remove(file)

        print("\n🎉 增强调度器测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_enhanced_scheduler()
