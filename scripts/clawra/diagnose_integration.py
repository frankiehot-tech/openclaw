#!/usr/bin/env python3
"""诊断集成环境问题"""

import logging
import os
import sys

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(__file__))

# 测试每个导入
print("=== 测试关键导入 ===")

try:
    from maref_memory_manager import MAREFMemoryManager

    print("✅ MAREFMemoryManager 可导入")
except ImportError as e:
    print(f"❌ MAREFMemoryManager 导入失败: {e}")

try:
    from external.ROMA.hexagram_state_manager import HexagramStateManager

    print("✅ HexagramStateManager 可导入")
    # 测试创建实例（实际MAREF系统可能使用不同方式获取当前状态）
    try:
        # 创建实例而不是调用不存在的get_current_state()类方法
        state_manager = HexagramStateManager("000000")
        current_state = state_manager.current_state
        print(f"✅ HexagramStateManager实例创建成功，当前状态: {current_state}")
        # 测试get_hexagram_name方法
        try:
            hexagram_name = state_manager.get_hexagram_name()
            print(f"✅ 卦象名称获取成功: {hexagram_name}")
        except Exception as e:
            print(f"❌ get_hexagram_name()失败: {e}")
    except Exception as e:
        print(f"❌ HexagramStateManager实例创建失败: {e}")
except ImportError as e:
    print(f"❌ HexagramStateManager 导入失败: {e}")

# 测试智能体导入
agents_to_test = [
    ("GuardianAgent", "external.ROMA.guardian_agent", "GuardianAgent"),
    ("CommunicatorAgent", "external.ROMA.communicator_agent", "CommunicatorAgent"),
    ("LearnerAgent", "external.ROMA.learner_agent", "LearnerAgent"),
    ("ExplorerAgent", "external.ROMA.explorer_agent", "ExplorerAgent"),
]

print("\n=== 测试MAREF智能体导入 ===")
for name, module, class_name in agents_to_test:
    try:
        exec(f"from {module} import {class_name}")
        print(f"✅ {name} 可导入")
    except ImportError as e:
        print(f"❌ {name} 导入失败: {e}")

print("\n=== 测试集成环境创建 ===")
# 直接测试create_integration_environment，捕获详细异常
from run_maref_daily_report import create_integration_environment

try:
    result = create_integration_environment()
    print(f"✅ 集成环境创建成功，返回类型: {type(result)}")
    if isinstance(result, tuple) and len(result) == 2:
        state_manager, agents = result
        print(f"   状态管理器: {type(state_manager)}")
        print(f"   智能体数量: {len(agents)}")
        print(f"   智能体键: {list(agents.keys())}")
        for key, agent in agents.items():
            print(f"     {key}: {type(agent)}")
            # 检查是否是实际智能体
            try:
                from external.ROMA.communicator_agent import CommunicatorAgent
                from external.ROMA.explorer_agent import ExplorerAgent
                from external.ROMA.guardian_agent import GuardianAgent
                from external.ROMA.learner_agent import LearnerAgent

                if key == "guardian" and isinstance(agent, GuardianAgent):
                    print(f"       -> 实际GuardianAgent")
                elif key == "communicator" and isinstance(agent, CommunicatorAgent):
                    print(f"       -> 实际CommunicatorAgent")
                elif key == "learner" and isinstance(agent, LearnerAgent):
                    print(f"       -> 实际LearnerAgent")
                elif key == "explorer" and isinstance(agent, ExplorerAgent):
                    print(f"       -> 实际ExplorerAgent")
                else:
                    print(f"       -> 不是实际MAREF智能体")
            except:
                pass
    else:
        print(f"   返回值不是期望的元组: {result}")
except Exception as e:
    print(f"❌ 集成环境创建失败: {e}")
    import traceback

    traceback.print_exc()
