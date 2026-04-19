#!/usr/bin/env python3
"""测试集成环境修复"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

import logging

logging.basicConfig(level=logging.INFO)

from run_maref_daily_report import create_integration_environment

print("=== 测试集成环境修复 ===")
try:
    state_manager, agents = create_integration_environment()
    print(f"✅ 集成环境创建成功")
    print(f"   状态管理器类型: {type(state_manager)}")
    print(f"   智能体数量: {len(agents)}")
    print(f"   智能体键: {list(agents.keys())}")

    # 检查是否是实际MAREF智能体
    from external.ROMA.communicator_agent import CommunicatorAgent
    from external.ROMA.explorer_agent import ExplorerAgent
    from external.ROMA.guardian_agent import GuardianAgent
    from external.ROMA.learner_agent import LearnerAgent

    actual_maref_agents = 0
    for name, agent in agents.items():
        if name == "guardian" and isinstance(agent, GuardianAgent):
            print(f"   {name}: ✅ 实际GuardianAgent")
            actual_maref_agents += 1
        elif name == "communicator" and isinstance(agent, CommunicatorAgent):
            print(f"   {name}: ✅ 实际CommunicatorAgent")
            actual_maref_agents += 1
        elif name == "learner" and isinstance(agent, LearnerAgent):
            print(f"   {name}: ✅ 实际LearnerAgent")
            actual_maref_agents += 1
        elif name == "explorer" and isinstance(agent, ExplorerAgent):
            print(f"   {name}: ✅ 实际ExplorerAgent")
            actual_maref_agents += 1
        else:
            print(f"   {name}: ❌ 不是实际MAREF智能体 (类型: {type(agent).__name__})")

    print(f"\n实际MAREF智能体数量: {actual_maref_agents}/{len(agents)}")

except Exception as e:
    print(f"❌ 集成环境创建失败: {e}")
    import traceback

    traceback.print_exc()
