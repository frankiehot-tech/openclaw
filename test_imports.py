#!/usr/bin/env python3
"""
测试所有契约模块的导入
"""

import sys

sys.path.insert(0, "/Volumes/1TB-M2/openclaw")

print("🧪 测试契约模块导入")
print("=" * 60)

# 测试1: TaskIdentityContract
try:
    from contracts.task_identity import TaskIdentity, TaskIdentityContract

    print("✅ contracts.task_identity 导入成功")
except Exception as e:
    print(f"❌ contracts.task_identity 导入失败: {e}")

# 测试2: ProcessLifecycleContract
try:
    from contracts.process_lifecycle import ProcessContract, ProcessLifecycleContract

    print("✅ contracts.process_lifecycle 导入成功")
except Exception as e:
    print(f"❌ contracts.process_lifecycle 导入失败: {e}")

# 测试3: DataQualityContract (从data_quality模块)
try:
    from contracts.data_quality import DataQualityContract

    print("✅ contracts.data_quality 导入成功")
except Exception as e:
    print(f"❌ contracts.data_quality 导入失败: {e}")

# 测试4: DataQualityContract (从contracts包)
try:
    from contracts import DataQualityContract

    print("✅ from contracts import DataQualityContract 导入成功")
except Exception as e:
    print(f"❌ from contracts import DataQualityContract 导入失败: {e}")

# 测试5: StateSyncContract
try:
    from contracts.state_sync import StateSyncContract

    print("✅ contracts.state_sync 导入成功")
except Exception as e:
    print(f"❌ contracts.state_sync 导入失败: {e}")

# 测试6: SmartOrchestrator
try:
    from workflow.smart_orchestrator import SmartOrchestrator

    print("✅ workflow.smart_orchestrator 导入成功")
except Exception as e:
    print(f"❌ workflow.smart_orchestrator 导入失败: {e}")

# 测试7: AthenaOrchestrator
try:
    from mini_agent.agent.core.athena_orchestrator import AthenaOrchestrator

    print("✅ mini_agent.agent.core.athena_orchestrator 导入成功")
except Exception as e:
    print(f"❌ mini_agent.agent.core.athena_orchestrator 导入失败: {e}")

print("=" * 60)
print("导入测试完成")
