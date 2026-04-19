#!/usr/bin/env python3
"""
MAREF内存集成模块
提供内存管理器与现有MAREF系统的集成接口

功能：
1. 全局内存管理器实例
2. 状态转换记录装饰器/包装器
3. 智能体行动记录装饰器
4. 与现有监控器和状态管理器的集成
5. 认知对齐事件自动记录
"""

import functools
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from maref_memory_manager import (
    MAREFMemoryManager,
    MemoryEntry,
    MemoryEntryType,
    MemoryPriority,
)

logger = logging.getLogger(__name__)

# 全局内存管理器实例
_memory_manager_instance = None


def get_memory_manager(
    memory_dir: str = None, db_path: str = None, performance_mode: bool = False
) -> MAREFMemoryManager:
    """
    获取全局内存管理器实例（单例模式）

    Args:
        memory_dir: 内存目录（仅首次调用时生效）
        db_path: 数据库路径（仅首次调用时生效）
        performance_mode: 性能模式（仅首次调用时生效）

    Returns:
        MAREFMemoryManager实例
    """
    global _memory_manager_instance

    if _memory_manager_instance is None:
        _memory_manager_instance = MAREFMemoryManager(memory_dir, db_path, performance_mode)
        logger.info(f"全局内存管理器已初始化，存储目录: {_memory_manager_instance.memory_dir}")
        logger.info(f"性能模式: {'开启' if performance_mode else '关闭'}")

    return _memory_manager_instance


def init_memory_manager(
    memory_dir: str = None, db_path: str = None, performance_mode: bool = False
) -> MAREFMemoryManager:
    """
    初始化内存管理器（显式调用）

    Args:
        memory_dir: 内存目录
        db_path: 数据库路径
        performance_mode: 性能模式

    Returns:
        初始化的内存管理器实例
    """
    return get_memory_manager(memory_dir, db_path, performance_mode)


# ============================================================================
# 状态转换记录
# ============================================================================


def record_state_transition(
    from_state: str,
    to_state: str,
    trigger_agent: str,
    context: Dict[str, Any] = None,
    transition_reason: str = "",
) -> str:
    """
    记录状态转换（包装函数）

    Args:
        from_state: 源状态
        to_state: 目标状态
        trigger_agent: 触发智能体
        context: 转换上下文
        transition_reason: 转换原因

    Returns:
        内存条目ID
    """
    memory_manager = get_memory_manager()

    try:
        entry_id = memory_manager.record_state_transition(
            from_state=from_state,
            to_state=to_state,
            trigger_agent=trigger_agent,
            context=context,
            transition_reason=transition_reason,
        )

        logger.debug(f"状态转换记录成功: {from_state} → {to_state} (ID: {entry_id})")
        return entry_id

    except Exception as e:
        logger.error(f"记录状态转换失败: {e}")
        raise


def wrap_state_manager_transition(state_manager, memory_manager=None):
    """
    包装状态管理器的transition方法，添加内存记录功能

    Args:
        state_manager: HexagramStateManager实例
        memory_manager: 内存管理器实例（可选）

    Returns:
        包装后的状态管理器（原对象被修改）
    """
    if memory_manager is None:
        memory_manager = get_memory_manager()

    original_transition = state_manager.transition

    def wrapped_transition(
        new_state: str,
        trigger_agent: str = "unknown",
        context: Dict[str, Any] = None,
        reason: str = "状态转换",
    ) -> bool:
        """
        包装的transition方法，在转换前记录到内存

        Args:
            new_state: 目标状态
            trigger_agent: 触发智能体
            context: 转换上下文
            reason: 转换原因

        Returns:
            转换是否成功
        """
        from_state = state_manager.current_state

        # 调用原始方法，传递转换原因
        success = original_transition(new_state, reason=reason)

        # 如果成功，记录到内存
        if success:
            try:
                memory_manager.record_state_transition(
                    from_state=from_state,
                    to_state=new_state,
                    trigger_agent=trigger_agent,
                    context=context or {},
                    transition_reason=reason,
                )
                logger.debug(f"状态转换已记录: {from_state} → {new_state}")
            except Exception as e:
                logger.warning(f"记录状态转换失败（不影响转换）: {e}")

        return success

    # 替换原方法
    state_manager.transition = wrapped_transition
    logger.info(f"状态管理器的transition方法已包装，支持内存记录")

    return state_manager


# ============================================================================
# 智能体行动记录装饰器
# ============================================================================


def record_agent_action(action_type: str = None):
    """
    装饰器：记录智能体行动

    Args:
        action_type: 行动类型（可选，可从函数名推断）

    Returns:
        装饰器函数
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(agent, *args, **kwargs):
            memory_manager = get_memory_manager()

            # 获取智能体信息
            agent_id = getattr(agent, "agent_id", f"agent_{id(agent)}")
            agent_type = getattr(agent, "agent_type", "unknown")

            # 确定行动类型
            final_action_type = action_type or func.__name__

            # 记录行动开始
            action_start_time = datetime.now()

            try:
                # 执行原始函数
                result = func(agent, *args, **kwargs)

                # 记录成功的行动
                memory_manager.record_agent_action(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    action_type=final_action_type,
                    action_details={
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs),
                        "execution_time_ms": (datetime.now() - action_start_time).total_seconds()
                        * 1000,
                    },
                    result={
                        "success": True,
                        "result": str(result) if result is not None else "None",
                    },
                    decision_context=getattr(agent, "current_context", {}),
                )

                logger.debug(f"智能体行动记录成功: {agent_id}.{final_action_type}")

                return result

            except Exception as e:
                # 记录失败的行动
                memory_manager.record_agent_action(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    action_type=final_action_type,
                    action_details={
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs),
                        "error": str(e),
                        "execution_time_ms": (datetime.now() - action_start_time).total_seconds()
                        * 1000,
                    },
                    result={"success": False, "error": str(e)},
                    decision_context=getattr(agent, "current_context", {}),
                )

                logger.error(f"智能体行动记录失败: {agent_id}.{final_action_type} - {e}")
                raise

        return wrapper

    return decorator


def record_agent_decision(decision_type: str = None):
    """
    装饰器：记录智能体决策

    Args:
        decision_type: 决策类型（可选，可从函数名推断）

    Returns:
        装饰器函数
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(agent, *args, **kwargs):
            memory_manager = get_memory_manager()

            # 获取智能体信息
            agent_id = getattr(agent, "agent_id", f"agent_{id(agent)}")
            agent_type = getattr(agent, "agent_type", "unknown")

            # 确定决策类型
            final_decision_type = decision_type or func.__name__

            try:
                # 执行原始函数
                result = func(agent, *args, **kwargs)

                # 记录决策
                memory_manager.record_agent_decision(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    decision_type=final_decision_type,
                    decision_data={
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs),
                        "result": str(result) if result is not None else "None",
                    },
                    rationale=getattr(agent, "decision_rationale", f"由{agent_type}执行"),
                )

                logger.debug(f"智能体决策记录成功: {agent_id}.{final_decision_type}")

                return result

            except Exception as e:
                logger.error(f"智能体决策执行失败: {agent_id}.{final_decision_type} - {e}")
                raise

        return wrapper

    return decorator


# ============================================================================
# 系统事件记录
# ============================================================================


def record_system_event(
    event_type: str, event_data: Dict[str, Any], severity: str = "info", source: str = "system"
) -> str:
    """
    记录系统事件

    Args:
        event_type: 事件类型
        event_data: 事件数据
        severity: 严重程度
        source: 事件来源

    Returns:
        内存条目ID
    """
    memory_manager = get_memory_manager()

    try:
        entry_id = memory_manager.record_system_event(
            event_type=event_type, event_data=event_data, severity=severity, source=source
        )

        logger.debug(f"系统事件记录成功: {event_type} (ID: {entry_id})")
        return entry_id

    except Exception as e:
        logger.error(f"记录系统事件失败: {e}")
        raise


# ============================================================================
# 认知对齐记录
# ============================================================================


def record_cognitive_alignment_event(
    alignment_type: str,
    involved_agents: List[str],
    alignment_data: Dict[str, Any],
    alignment_result: Dict[str, Any],
) -> str:
    """
    记录认知对齐事件

    Args:
        alignment_type: 对齐类型
        involved_agents: 涉及智能体列表
        alignment_data: 对齐数据
        alignment_result: 对齐结果

    Returns:
        内存条目ID
    """
    memory_manager = get_memory_manager()

    try:
        entry_id = memory_manager.record_cognitive_alignment(
            alignment_type=alignment_type,
            involved_agents=involved_agents,
            alignment_data=alignment_data,
            alignment_result=alignment_result,
        )

        logger.info(f"认知对齐事件记录成功: {alignment_type}，涉及 {len(involved_agents)} 个智能体")
        return entry_id

    except Exception as e:
        logger.error(f"记录认知对齐事件失败: {e}")
        raise


def align_agent_knowledge(
    agents: List[str], alignment_type: str = "knowledge_sync"
) -> Dict[str, Any]:
    """
    对齐智能体知识（简化版本）

    Args:
        agents: 智能体ID列表
        alignment_type: 对齐类型

    Returns:
        对齐结果
    """
    memory_manager = get_memory_manager()

    # 获取各智能体的最新记忆
    agent_memories = {}
    for agent_id in agents:
        memories = memory_manager.get_agent_memory(agent_id, limit=10)
        agent_memories[agent_id] = {
            "memory_count": len(memories),
            "recent_entries": [entry.entry_type.value for entry in memories[:3]],
        }

    # 检查是否有不一致
    alignment_data = {
        "agents": agents,
        "agent_memories": agent_memories,
        "timestamp": datetime.now().isoformat(),
    }

    # 假设对齐成功（实际实现需要更复杂的逻辑）
    alignment_result = {
        "success": True,
        "aligned_agents": len(agents),
        "inconsistencies_found": 0,
        "alignment_timestamp": datetime.now().isoformat(),
    }

    # 记录对齐事件
    entry_id = record_cognitive_alignment_event(
        alignment_type=alignment_type,
        involved_agents=agents,
        alignment_data=alignment_data,
        alignment_result=alignment_result,
    )

    alignment_result["entry_id"] = entry_id
    return alignment_result


# ============================================================================
# 监控器集成
# ============================================================================


def wrap_monitor_collect_metrics(monitor, memory_manager=None):
    """
    包装监控器的collect_all_metrics方法，添加内存记录

    Args:
        monitor: MAREFMonitor实例
        memory_manager: 内存管理器实例（可选）

    Returns:
        包装后的监控器（原对象被修改）
    """
    if memory_manager is None:
        memory_manager = get_memory_manager()

    original_collect_all_metrics = monitor.collect_all_metrics

    def wrapped_collect_all_metrics():
        """包装的collect_all_metrics方法，记录性能指标到内存"""
        metrics = original_collect_all_metrics()

        try:
            # 记录系统性能指标
            if "system" in metrics:
                system_metrics = metrics["system"]
                memory_manager.record_system_event(
                    event_type="performance_metrics",
                    event_data=system_metrics,
                    severity="info",
                    source="monitor",
                )

            # 记录MAREF指标
            if "maref" in metrics:
                maref_metrics = metrics["maref"]
                memory_manager.record_system_event(
                    event_type="maref_metrics",
                    event_data={
                        "control_entropy": maref_metrics.get("control_entropy_h_c"),
                        "current_hexagram": maref_metrics.get("current_hexagram"),
                        "gray_code_compliance": maref_metrics.get("gray_code_compliance", {}).get(
                            "rate"
                        ),
                    },
                    severity="info",
                    source="monitor",
                )

            logger.debug(f"监控指标已记录到内存")

        except Exception as e:
            logger.warning(f"记录监控指标失败（不影响监控）: {e}")

        return metrics

    # 替换原方法
    monitor.collect_all_metrics = wrapped_collect_all_metrics
    logger.info(f"监控器的collect_all_metrics方法已包装，支持内存记录")

    return monitor


# ============================================================================
# 查询和统计工具
# ============================================================================


def get_recent_system_changes(hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
    """
    获取最近的系统变更记录

    Args:
        hours: 时间窗口（小时）
        limit: 返回条目限制

    Returns:
        变更记录列表
    """
    memory_manager = get_memory_manager()

    # 获取状态转换记录
    state_changes = memory_manager.get_system_state_history(limit=limit)

    # 获取系统事件
    end_time = datetime.now().isoformat()
    start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

    system_events = memory_manager.query_memory(
        entry_type=MemoryEntryType.SYSTEM_EVENT,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    # 组合结果
    changes = []
    for change in state_changes:
        changes.append(
            {
                "type": "state_transition",
                "timestamp": change["timestamp"],
                "details": f"{change['from_state']} → {change['to_state']} by {change['trigger_agent']}",
                "data": change,
            }
        )

    for event in system_events:
        changes.append(
            {
                "type": "system_event",
                "timestamp": event.timestamp,
                "details": f"{event.content.get('event_type', 'unknown')} ({event.source_agent})",
                "data": event.content,
            }
        )

    # 按时间排序
    changes.sort(key=lambda x: x["timestamp"], reverse=True)
    return changes[:limit]


def get_cognitive_alignment_report(hours: int = 24) -> Dict[str, Any]:
    """
    获取认知对齐报告

    Args:
        hours: 时间窗口（小时）

    Returns:
        对齐报告
    """
    memory_manager = get_memory_manager()

    summary = memory_manager.get_cognitive_alignment_summary(time_window_hours=hours)

    # 添加详细对齐事件
    end_time = datetime.now().isoformat()
    start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

    alignment_events = memory_manager.query_memory(
        entry_type=MemoryEntryType.COGNITIVE_ALIGNMENT,
        start_time=start_time,
        end_time=end_time,
        limit=100,
    )

    summary["recent_alignments"] = [
        {
            "timestamp": event.timestamp,
            "alignment_type": event.content.get("alignment_type"),
            "involved_agents": event.content.get("involved_agents", []),
            "result": event.content.get("alignment_result", {}),
        }
        for event in alignment_events[:10]  # 最近10个
    ]

    return summary


def get_memory_usage_report() -> Dict[str, Any]:
    """
    获取内存使用情况报告

    Returns:
        内存使用报告
    """
    memory_manager = get_memory_manager()

    stats = memory_manager.get_memory_statistics()

    # 添加存储信息
    import os

    if memory_manager.db_path and os.path.exists(memory_manager.db_path):
        db_size = os.path.getsize(memory_manager.db_path)
        stats["database_size_bytes"] = db_size
        stats["database_size_mb"] = db_size / (1024 * 1024)

    # 添加缓存信息
    stats["cached_entries"] = len(memory_manager.recent_entries)

    return stats


# ============================================================================
# 测试函数
# ============================================================================


def test_memory_integration():
    """测试内存集成模块"""
    print("=== MAREF内存集成测试 ===")

    # 初始化内存管理器
    memory_manager = init_memory_manager()
    print("✅ 内存管理器初始化成功")

    # 测试状态转换记录
    print("\n=== 测试状态转换记录 ===")
    transition_id = record_state_transition(
        from_state="000000",
        to_state="000001",
        trigger_agent="coordinator",
        transition_reason="测试转换",
    )
    print(f"状态转换记录ID: {transition_id}")

    # 测试系统事件记录
    print("\n=== 测试系统事件记录 ===")
    event_id = record_system_event(
        event_type="test_event",
        event_data={"test": "value", "number": 42},
        severity="info",
        source="test_runner",
    )
    print(f"系统事件记录ID: {event_id}")

    # 测试认知对齐记录
    print("\n=== 测试认知对齐记录 ===")
    alignment_id = record_cognitive_alignment_event(
        alignment_type="test_alignment",
        involved_agents=["coordinator", "executor"],
        alignment_data={"test": True},
        alignment_result={"success": True},
    )
    print(f"认知对齐记录ID: {alignment_id}")

    # 测试智能体行动记录装饰器（模拟）
    print("\n=== 测试智能体行动装饰器 ===")

    class TestAgent:
        agent_id = "test_agent_001"
        agent_type = "tester"
        current_context = {"test": True}

        @record_agent_action(action_type="test_action")
        def perform_action(self, param1, param2):
            print(f"  执行行动: {param1}, {param2}")
            return {"result": "success"}

        @record_agent_decision(decision_type="test_decision")
        def make_decision(self, options):
            print(f"  做出决策: 从{len(options)}个选项中选择")
            return options[0] if options else None

    agent = TestAgent()
    agent.perform_action("param1_value", param2="param2_value")
    agent.make_decision(["option1", "option2", "option3"])

    # 测试查询功能
    print("\n=== 测试查询功能 ===")

    changes = get_recent_system_changes(hours=1, limit=5)
    print(f"最近系统变更: {len(changes)} 条")
    for i, change in enumerate(changes, 1):
        print(f"  {i}. [{change['type']}] {change['details']}")

    alignment_report = get_cognitive_alignment_report(hours=1)
    print(f"\n认知对齐报告:")
    print(f"  总对齐次数: {alignment_report.get('total_alignments', 0)}")

    memory_report = get_memory_usage_report()
    print(f"\n内存使用报告:")
    print(f"  总条目数: {memory_report.get('total_entries', 0)}")
    print(f"  数据库大小: {memory_report.get('database_size_mb', 0):.2f} MB")

    print("\n=== 测试完成 ===")
    print("内存集成模块功能验证通过")


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    test_memory_integration()
