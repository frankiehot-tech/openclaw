#!/usr/bin/env python3
"""测试所有MAREF组件的导入功能"""

import os
import sys
import traceback

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))


def test_component(name, import_statement, check_attr=None):
    """测试单个组件导入"""
    try:
        exec(import_statement, globals())
        if check_attr:
            # 检查特定属性是否存在
            if check_attr in globals():
                print(f"✅ {name}: 导入成功 ({check_attr} 存在)")
                return True
            else:
                print(f"⚠️ {name}: 导入成功但 {check_attr} 不存在")
                return False
        else:
            print(f"✅ {name}: 导入成功")
            return True
    except Exception as e:
        print(f"❌ {name}: 导入失败 - {e}")
        # 打印更详细的错误信息（可选）
        # traceback.print_exc()
        return False


print("=== MAREF组件导入测试 ===\n")

# 测试核心MAREF组件
components = [
    (
        "maref_memory_manager",
        "from maref_memory_manager import MAREFMemoryManager",
        "MAREFMemoryManager",
    ),
    (
        "coding_audit_system",
        "from coding_audit_system import CodingAuditSystem",
        "CodingAuditSystem",
    ),
    (
        "maref_memory_integration",
        "from maref_memory_integration import init_memory_manager",
        "init_memory_manager",
    ),
    ("maref_alert_engine", "from maref_alert_engine import AlertEngine", "AlertEngine"),
    ("maref_daily_reporter", "from maref_daily_reporter import DailyReporter", "DailyReporter"),
    ("maref_monitor", "from maref_monitor import MAREFMonitor", "MAREFMonitor"),
    ("maref_notifier", "from maref_notifier import Notifier", "Notifier"),
    (
        "maref_roma_integration",
        "from maref_roma_integration import ExtendedAgentType",
        "ExtendedAgentType",
    ),
]

success_count = 0
total_count = len(components)

for name, import_stmt, check_attr in components:
    if test_component(name, import_stmt, check_attr):
        success_count += 1

print(f"\n=== MAREF智能体导入测试 ===\n")

# 测试MAREF智能体（需要从external/ROMA导入）
agents = [
    ("guardian_agent", "from guardian_agent import GuardianAgent", "GuardianAgent"),
    ("communicator_agent", "from communicator_agent import CommunicatorAgent", "CommunicatorAgent"),
    ("learner_agent", "from learner_agent import LearnerAgent", "LearnerAgent"),
    ("explorer_agent", "from explorer_agent import ExplorerAgent", "ExplorerAgent"),
    ("maref_agent_type", "from maref_agent_type import MAREFAgentType", "MAREFAgentType"),
]

for name, import_stmt, check_attr in agents:
    if test_component(name, import_stmt, check_attr):
        success_count += 1
    total_count += 1

print(f"\n=== 测试结果 ===\n")
print(f"成功导入: {success_count}/{total_count} 个组件")
print(f"成功率: {success_count/total_count*100:.1f}%")

if success_count == total_count:
    print("🎉 所有组件导入成功！")
else:
    print("⚠️  部分组件导入失败，需要进一步检查")

# 测试clawra_production_system中的ROMA_MAREF_AVAILABLE标志
print(f"\n=== 生产系统集成状态 ===\n")
try:
    import clawra_production_system

    print(f"ROMA_MAREF_AVAILABLE = {clawra_production_system.ROMA_MAREF_AVAILABLE}")
    print(f"KDENLIVE_AVAILABLE = {clawra_production_system.KDENLIVE_AVAILABLE}")
    print(f"DOUBAO_CLI_AVAILABLE = {clawra_production_system.DOUBAO_CLI_AVAILABLE}")
except Exception as e:
    print(f"❌ 导入clawra_production_system失败: {e}")
