#!/usr/bin/env python3
"""测试集成环境创建"""

import logging
import os
import sys

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))

# 导入必要的模块
try:
    from run_maref_daily_report import (
        create_integration_environment,
        create_simulation_environment,
    )

    logger.info("导入成功")
except ImportError as e:
    logger.error(f"导入失败: {e}")
    sys.exit(1)

# 测试集成环境
logger.info("=== 测试集成环境 ===")
try:
    state_manager, agents = create_integration_environment()
    logger.info(f"✅ 集成环境创建成功")
    logger.info(f"  状态管理器: {type(state_manager).__name__}")
    logger.info(f"  智能体数量: {len(agents)}")
    logger.info(f"  智能体类型: {list(agents.keys())}")

    # 检查智能体是否是实际的MAREF智能体
    from external.ROMA.communicator_agent import CommunicatorAgent
    from external.ROMA.explorer_agent import ExplorerAgent
    from external.ROMA.guardian_agent import GuardianAgent
    from external.ROMA.learner_agent import LearnerAgent

    for agent_name, agent in agents.items():
        if agent_name == "guardian":
            assert isinstance(agent, GuardianAgent), f"guardian agent 不是 GuardianAgent 类型"
            logger.info(f"  {agent_name}: 实际GuardianAgent")
        elif agent_name == "communicator":
            assert isinstance(
                agent, CommunicatorAgent
            ), f"communicator agent 不是 CommunicatorAgent 类型"
            logger.info(f"  {agent_name}: 实际CommunicatorAgent")
        elif agent_name == "learner":
            assert isinstance(agent, LearnerAgent), f"learner agent 不是 LearnerAgent 类型"
            logger.info(f"  {agent_name}: 实际LearnerAgent")
        elif agent_name == "explorer":
            assert isinstance(agent, ExplorerAgent), f"explorer agent 不是 ExplorerAgent 类型"
            logger.info(f"  {agent_name}: 实际ExplorerAgent")
        else:
            logger.info(f"  {agent_name}: {type(agent).__name__}")

except Exception as e:
    logger.error(f"❌ 集成环境创建失败: {e}")
    import traceback

    traceback.print_exc()

# 测试模拟环境作为对比
logger.info("\n=== 测试模拟环境 ===")
try:
    state_manager, agents = create_simulation_environment()
    logger.info(f"✅ 模拟环境创建成功")
    logger.info(f"  状态管理器: {type(state_manager).__name__ if state_manager else 'None'}")
    logger.info(f"  智能体数量: {len(agents)}")
    logger.info(f"  智能体类型: {list(agents.keys())}")

    # 检查智能体是否是模拟智能体
    for agent_name, agent in agents.items():
        logger.info(f"  {agent_name}: {type(agent).__name__}")

except Exception as e:
    logger.error(f"❌ 模拟环境创建失败: {e}")
    import traceback

    traceback.print_exc()

logger.info("\n=== 测试完成 ===")
