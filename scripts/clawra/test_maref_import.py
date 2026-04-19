#!/usr/bin/env python3
"""测试MAREF导入功能"""

import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))

try:
    # 尝试导入clawra_production_system中的标志
    import clawra_production_system

    print(f"ROMA_MAREF_AVAILABLE = {clawra_production_system.ROMA_MAREF_AVAILABLE}")

    # 尝试导入maref_roma_integration中的类
    from maref_roma_integration import (
        ExtendedAgentType,
        GrayCodeConverter,
        HybridAgentFactory,
        MarefAgentAdapter,
        MarefRomaIntegration,
    )

    print("✅ MAREF类导入成功")

    # 检查智能体可用性
    try:
        from maref_roma_integration import MAREF_AGENTS_AVAILABLE

        print(f"MAREF_AGENTS_AVAILABLE = {MAREF_AGENTS_AVAILABLE}")
    except ImportError:
        print("⚠️ MAREF_AGENTS_AVAILABLE 标志未定义")

except ImportError as e:
    print(f"❌ 导入失败: {e}")
    import traceback

    traceback.print_exc()
