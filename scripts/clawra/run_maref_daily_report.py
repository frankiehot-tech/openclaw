#!/usr/bin/env python3
"""
MAREF日报自动运行脚本
用于定时生成日报并发送预警通知

使用方式:
1. 直接运行: python run_maref_daily_report.py
2. 作为模块导入: from run_maref_daily_report import run_daily_report
3. 配置为cron任务: 0 9 * * * cd /path/to/scripts/clawra && python run_maref_daily_report.py

配置:
- 环境变量 MAREF_MODE: 'standalone' (默认，使用模拟数据) 或 'integration' (连接实际MAREF系统)
- 环境变量 OUTPUT_DIR: 指定日报输出目录，默认使用maref_daily_reporter中的配置
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置日志
log_dir = Path(__file__).parent / "logs"
try:
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "maref_daily_report.log"

    handlers = [logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")]
except Exception as e:
    print(f"警告: 无法创建日志文件 {log_file}: {e}")
    handlers = [logging.StreamHandler()]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers,
)
logger = logging.getLogger(__name__)

# 导入内存集成模块
try:
    from maref_memory_integration import (
        init_memory_manager,
        record_agent_action,
        record_agent_decision,
        record_cognitive_alignment_event,
        record_system_event,
        wrap_monitor_collect_metrics,
        wrap_state_manager_transition,
    )

    logger.info("内存集成模块导入成功")
except ImportError as e:
    logger.warning(f"无法导入内存集成模块: {e}")
    logger.warning("内存记录功能将不可用")

    # 创建虚拟函数以避免运行时错误
    def noop_memory_manager(*args, **kwargs):
        return type(
            "DummyMemoryManager",
            (),
            {"record_state_transition": lambda *args, **kwargs: "dummy_id"},
        )()

    init_memory_manager = lambda *args, **kwargs: noop_memory_manager()
    wrap_state_manager_transition = lambda sm, mm=None: sm
    wrap_monitor_collect_metrics = lambda m, mm=None: m
    record_system_event = lambda *args, **kwargs: "dummy_id"
    record_cognitive_alignment_event = lambda *args, **kwargs: "dummy_id"
    record_agent_action = lambda action_type=None: lambda func: func
    record_agent_decision = lambda decision_type=None: lambda func: func


def create_simulation_environment():
    """创建模拟环境（用于独立模式）"""
    logger.info("创建模拟MAREF环境")

    # 初始化内存管理器
    logger.info("初始化内存管理器...")
    memory_manager = init_memory_manager()

    try:
        # 尝试导入状态管理器
        from hexagram_state_manager import HexagramStateManager

        state_manager = HexagramStateManager("000000")

        # 包装状态管理器以支持内存记录
        logger.info("包装状态管理器...")
        state_manager = wrap_state_manager_transition(state_manager, memory_manager)

        # 模拟一些状态转换以生成数据（带内存记录）
        logger.info("执行模拟状态转换...")
        test_transitions = [
            ("000001", "coordinator", "系统初始化"),
            ("000011", "executor", "任务执行"),
            ("000010", "coordinator", "状态优化"),
            ("000000", "guardian", "安全回退"),
            ("000100", "explorer", "探索新状态"),
        ]

        for state, trigger_agent, reason in test_transitions:
            # 使用包装后的transition方法（支持内存记录）
            success = state_manager.transition(
                new_state=state,
                trigger_agent=trigger_agent,
                context={
                    "simulation": True,
                    "iteration": test_transitions.index((state, trigger_agent, reason)),
                },
                reason=reason,
            )
            if success:
                logger.debug(f"状态转换成功: 000000 → {state} by {trigger_agent}")
            else:
                logger.warning(f"状态转换失败: 000000 → {state}")
            time.sleep(0.1)  # 小延迟以确保时间戳不同

        logger.info(f"状态管理器初始化成功，当前卦象: {state_manager.get_hexagram_name()}")

    except ImportError as e:
        logger.warning(f"无法导入hexagram_state_manager: {e}")
        logger.warning("将使用空状态管理器，部分MAREF指标可能不可用")
        state_manager = None

    # 创建支持内存记录的模拟智能体
    class MockAgent:
        def __init__(self, agent_id, agent_type, health_score=0.9):
            self.agent_id = agent_id
            self.agent_type = agent_type
            self.health_score = health_score
            self.current_context = {"simulation": True, "agent_type": agent_type}

        def get_health_metrics(self):
            return {
                "agent_id": self.agent_id,
                "agent_type": str(self.agent_type),
                "status": "active",
                "health_score": self.health_score,
                "last_check": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
            }

        @record_agent_action(action_type="health_check")
        def perform_health_check(self):
            """执行健康检查"""
            logger.debug(f"{self.agent_id} 执行健康检查")
            return self.get_health_metrics()

        @record_agent_decision(decision_type="task_selection")
        def select_task(self, available_tasks):
            """选择任务"""
            logger.debug(f"{self.agent_id} 从 {len(available_tasks)} 个任务中选择")
            return available_tasks[0] if available_tasks else None

        @record_agent_action(action_type="report_generation")
        def generate_report(self, report_type):
            """生成报告"""
            logger.debug(f"{self.agent_id} 生成 {report_type} 报告")
            return {
                "report_type": report_type,
                "content": f"{self.agent_type} 报告",
                "timestamp": datetime.now().isoformat(),
            }

    # 8个核心智能体（基于MAREF架构）
    agents = {
        "coordinator": MockAgent("coordinator_001", "coordinator", 0.95),
        "memory": MockAgent("memory_001", "memory", 0.88),
        "executor": MockAgent("executor_001", "executor", 0.92),
        "critic": MockAgent("critic_001", "critic", 0.85),
        "explorer": MockAgent("explorer_001", "explorer", 0.90),
        "communicator": MockAgent("communicator_001", "communicator", 0.94),
        "guardian": MockAgent("guardian_001", "guardian", 0.96),
        "learner": MockAgent("learner_001", "learner", 0.87),
    }

    logger.info(f"创建了 {len(agents)} 个模拟智能体")

    # 记录一些示例系统事件
    logger.info("记录示例系统事件...")
    record_system_event(
        event_type="simulation_start",
        event_data={"agents": list(agents.keys()), "simulation_time": datetime.now().isoformat()},
        severity="info",
        source="simulation_runner",
    )

    # 记录示例认知对齐事件
    logger.info("记录示例认知对齐事件...")
    record_cognitive_alignment_event(
        alignment_type="initial_sync",
        involved_agents=["coordinator_001", "executor_001", "critic_001"],
        alignment_data={"purpose": "初始状态同步", "timestamp": datetime.now().isoformat()},
        alignment_result={"success": True, "aligned_agents": 3, "sync_time_ms": 150},
    )

    # 让智能体执行一些示例行动
    logger.info("执行示例智能体行动...")
    for agent_name, agent in agents.items():
        try:
            # 每个智能体执行健康检查
            agent.perform_health_check()

            # 模拟任务选择
            if agent_name in ["executor", "coordinator", "explorer"]:
                agent.select_task(["task_a", "task_b", "task_c"])

            # 生成报告
            if agent_name in ["memory", "critic", "guardian"]:
                agent.generate_report(f"{agent_name}_summary")

        except Exception as e:
            logger.debug(f"智能体 {agent_name} 示例行动执行失败（预期内）: {e}")

    logger.info("模拟环境创建完成，内存记录已初始化")
    return state_manager, agents


def create_integration_environment():
    """创建集成环境（连接实际MAREF系统）"""
    logger.info("创建MAREF集成环境")

    def get_current_state_from_db(db_path="/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"):
        """从内存数据库获取最新状态"""
        import json
        import os
        import sqlite3

        if not os.path.exists(db_path):
            logger.warning(f"内存数据库不存在: {db_path}")
            return None

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 查询最新的状态转换记录
            cursor.execute("""
                SELECT content_json, timestamp, source_agent
                FROM memory_entries
                WHERE entry_type = 'state_transition'
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            result = cursor.fetchone()
            conn.close()

            if result:
                content_json, timestamp, source_agent = result
                try:
                    content = json.loads(content_json)
                    to_state = content.get("to_state")
                    if to_state and len(to_state) == 6:  # 验证状态格式
                        logger.info(
                            f"从数据库获取状态: {to_state} (时间: {timestamp}, 触发者: {source_agent})"
                        )
                        return to_state
                    else:
                        logger.warning(f"数据库状态格式无效: {to_state}")
                except json.JSONDecodeError as e:
                    logger.warning(f"解析数据库内容JSON失败: {e}")
            else:
                logger.info("数据库中没有状态转换记录")

        except Exception as e:
            logger.warning(f"查询数据库失败: {e}")

        return None

    try:
        # 1. 初始化实际内存管理器
        from maref_memory_manager import MAREFMemoryManager

        memory_manager = MAREFMemoryManager()

        # 2. 连接实际状态管理器 - 尝试从运行中的MAREF系统获取当前状态
        from external.ROMA.hexagram_state_manager import HexagramStateManager

        # 优先级：数据库 > 环境变量 > 默认值
        current_state = None

        # 首先尝试从数据库获取
        db_state = get_current_state_from_db()
        if db_state:
            current_state = db_state
            logger.info(f"从内存数据库获取当前状态: {current_state}")
        else:
            # 尝试从环境变量获取
            import os

            env_state = os.environ.get("MAREF_CURRENT_STATE")
            if env_state:
                current_state = env_state
                logger.info(f"从环境变量获取当前状态: {current_state}")
            else:
                current_state = "000000"
                logger.info(f"使用默认状态: {current_state}")

        state_manager = HexagramStateManager(current_state)

        # 3. 实例化实际MAREF智能体
        from external.ROMA.communicator_agent import CommunicatorAgent
        from external.ROMA.explorer_agent import ExplorerAgent
        from external.ROMA.guardian_agent import GuardianAgent, SecurityLevel
        from external.ROMA.learner_agent import LearnerAgent

        agents = {
            "guardian": GuardianAgent(agent_id="guardian_001", security_level=SecurityLevel.MEDIUM),
            "communicator": CommunicatorAgent(agent_id="communicator_001"),
            "learner": LearnerAgent(agent_id="learner_001"),
            "explorer": ExplorerAgent(agent_id="explorer_001"),
            # ... 其他智能体（如果存在）
        }

        # 4. 包装组件以支持内存记录
        from maref_memory_integration import wrap_state_manager_transition

        state_manager = wrap_state_manager_transition(state_manager, memory_manager)

        logger.info("✅ 集成环境创建成功，连接实际MAREF系统")
        logger.info(f"   当前卦象: {state_manager.get_hexagram_name()}")
        logger.info(f"   已实例化智能体: {list(agents.keys())}")
        return state_manager, agents

    except Exception as e:
        logger.error(f"创建集成环境失败: {e}")
        logger.warning("回退到模拟模式")
        return create_simulation_environment()


def initialize_monitor(state_manager, agents):
    """初始化监控器"""
    try:
        from maref_monitor import MAREFMonitor

        monitor = MAREFMonitor(state_manager, agents)

        # 包装监控器以支持内存记录
        monitor = wrap_monitor_collect_metrics(monitor)

        logger.info("监控器初始化成功（已启用内存记录）")
        return monitor
    except ImportError as e:
        logger.error(f"无法导入MAREFMonitor: {e}")
        raise
    except Exception as e:
        logger.error(f"初始化监控器失败: {e}")
        raise


def run_daily_report(mode="standalone", output_dir=None):
    """
    运行日报生成

    Args:
        mode: 运行模式 ('standalone' 或 'integration')
        output_dir: 指定输出目录，默认使用maref_daily_reporter中的配置

    Returns:
        report_path: 生成的日报文件路径，失败时返回None
    """
    start_time = datetime.now()
    logger.info(f"开始运行MAREF日报生成 ({mode}模式)")

    try:
        # 创建环境
        if mode == "integration":
            state_manager, agents = create_integration_environment()
        else:  # standalone 或其他
            state_manager, agents = create_simulation_environment()

        # 初始化监控器
        monitor = initialize_monitor(state_manager, agents)

        # 收集一些历史数据（模拟数据采集）
        logger.info("收集监控数据...")
        for i in range(3):  # 收集3次数据点
            monitor.collect_all_metrics()
            logger.debug(f"数据收集 {i+1}/3 完成")

        # 初始化日报生成器
        from maref_daily_reporter import MAREFDailyReporter

        reporter_args = {"monitor": monitor}
        if output_dir:
            reporter_args["output_dir"] = output_dir

        reporter = MAREFDailyReporter(**reporter_args)

        # 生成日报
        logger.info("生成日报...")
        report_path = reporter.generate_daily_report()

        if report_path:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 日报生成成功: {report_path}")
            logger.info(f"⏱️  总耗时: {elapsed:.2f}秒")

            # 记录成功到单独日志
            success_log = f"{datetime.now().isoformat()}: 日报生成成功 - {report_path}"
            success_log_path = Path(__file__).parent / "maref_report_success.log"
            try:
                with open(success_log_path, "a", encoding="utf-8") as f:
                    f.write(success_log + "\n")
            except:
                pass  # 忽略日志写入失败

            return report_path
        else:
            logger.error("❌ 日报生成失败")
            return None

    except Exception as e:
        logger.error(f"运行日报生成失败: {e}", exc_info=True)

        # 记录错误到单独日志
        error_log = f"{datetime.now().isoformat()}: 日报生成失败 - {str(e)}"
        error_log_path = Path(__file__).parent / "maref_report_errors.log"
        try:
            with open(error_log_path, "a", encoding="utf-8") as f:
                f.write(error_log + "\n")
        except:
            pass  # 忽略日志写入失败

        return None


def main():
    """命令行入口点"""
    parser = argparse.ArgumentParser(description="MAREF日报自动生成脚本")
    parser.add_argument(
        "--mode",
        choices=["standalone", "integration"],
        default=os.getenv("MAREF_MODE", "standalone"),
        help="运行模式: standalone(模拟数据) 或 integration(连接实际系统)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("MAREF_OUTPUT_DIR"),
        help="日报输出目录，默认使用maref_daily_reporter中的配置",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="启用详细日志输出")

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 运行日报生成
    report_path = run_daily_report(mode=args.mode, output_dir=args.output_dir)

    # 返回退出码
    if report_path:
        sys.exit(0)  # 成功
    else:
        sys.exit(1)  # 失败


if __name__ == "__main__":
    main()
