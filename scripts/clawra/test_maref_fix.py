#!/usr/bin/env python3
"""
测试MAREF修复
"""

import os
import sys

# 添加路径
sys.path.append(os.path.dirname(__file__))

from clawra_production_system import (
    ClawraProductionSystem,
    ProductionSystemConfig,
    ProductionSystemMode,
)

# 创建配置
config = ProductionSystemConfig(
    mode=ProductionSystemMode.ENTERPRISE,
    enable_roma_maref=True,
    enable_kdenlive=False,
    enable_doubao_cli=False,
    enable_github_workflow=False,
    output_dir="./test_output",
    quality_preset="high",
)

print("创建生产系统...")
system = ClawraProductionSystem(config)

print("\n测试MAREF智能体监督部署...")
result = system.deploy_maref_agent_supervision(
    enable_guardian=True, enable_learner=True, enable_explorer=True, enable_communicator=True
)

print(f"\n部署结果: {result.get('deployed', False)}")
if result.get("deployed"):
    print("✅ MAREF智能体监督部署成功")
else:
    print(f"❌ MAREF智能体监督部署失败: {result.get('error', '未知错误')}")

# 清理
import shutil

if os.path.exists("./test_output"):
    shutil.rmtree("./test_output")
