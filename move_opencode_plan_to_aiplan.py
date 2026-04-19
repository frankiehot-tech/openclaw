#!/usr/bin/env python3
"""
OpenCode CLI优化方案文件移动和队列更新脚本
将方案移动到AIplan目录并更新队列配置
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


def create_move_instructions():
    """创建文件移动操作指南"""
    
    instructions = """# 📁 OpenCode CLI优化方案文件移动操作指南

## 🎯 目标
将OpenCode CLI优化方案移动到指定的AIplan目录，并保持目录结构的规范性。

## 📊 当前文件位置
- **源文件**: `/Volumes/1TB-M2/openclaw/OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md`
- **目标目录**: `/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/`

## 🔧 手动执行步骤

### 步骤1: 复制文件到AIplan目录
```bash
# 复制OpenCode CLI优化方案到AIplan目录
cp "/Volumes/1TB-M2/openclaw/OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md" \
   "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md"
```

### 步骤2: 验证文件复制成功
```bash
# 检查文件是否复制成功
ls -la "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md"
```

### 步骤3: 更新队列配置中的文件路径
需要修改以下文件中的`instruction_path`字段：

1. **队列状态文件**: `/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json`
   - 将 `opencode_cli_optimization` 项的 `instruction_path` 更新为新路径

2. **队列配置文件**: `/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/OpenHuman-AIPlan-自动策划队列.queue.json`
   - 添加新的OpenCode CLI优化任务项

### 步骤4: 更新队列状态文件
编辑文件: `/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json`

找到 `opencode_cli_optimization` 项，更新 `instruction_path`:
```json
"instruction_path": "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md"
```

### 步骤5: 更新队列配置文件
编辑文件: `/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/OpenHuman-AIPlan-自动策划队列.queue.json`

在 `items` 数组中添加新的任务项（放在第一位，优先级S0）:
```json
{
  "id": "opencode_cli_optimization",
  "title": "OpenHuman-OpenCode-CLI-优化与Athena深度集成方案",
  "instruction_path": "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md",
  "entry_stage": "build",
  "risk_level": "medium",
  "unattended_allowed": true,
  "targets": [],
  "metadata": {
    "priority": "S0",
    "lane": "plan_auto",
    "epic": "execution_foundation",
    "category": "opencode_integration",
    "rationale": "这是当前最高优先级的任务，需要立即优化OpenCode CLI执行能力并修复队列连续执行问题。",
    "depends_on": [],
    "autostart": true,
    "generated_by": "opencode_optimization_plan"
  }
}
```

## 📋 验证步骤

### 验证1: 文件位置正确
```bash
# 检查文件是否在正确位置
ls -la "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/" | grep OpenCode
```

### 验证2: 队列配置正确
```bash
# 检查队列状态文件
cat "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json" | grep opencode_cli_optimization -A 5 -B 5
```

### 验证3: 队列运行正常
访问: http://127.0.0.1:8080
检查OpenCode CLI优化任务是否在队列中显示

## 🎯 预期结果

### 文件结构
```
/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/
├── OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md  # 新增
├── completed/                                          # 已完成方案
└── OpenHuman-AIPlan-自动策划队列.queue.json           # 已更新
```

### 队列状态
- ✅ OpenCode CLI优化任务在队列第一位
- ✅ 任务状态: pending → running
- ✅ 文件路径指向正确的AIplan目录
- ✅ 队列连续执行功能正常

## 🔧 自动化脚本（如果权限允许）

如果后续权限允许，可以使用以下自动化脚本：

```python
#!/usr/bin/env python3
import shutil
import json

# 1. 复制文件
shutil.copy2(
    "/Volumes/1TB-M2/openclaw/OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md",
    "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md"
)

# 2. 更新队列配置
# ... 队列配置更新代码
```

## 📞 技术支持
如果遇到任何问题，请检查：
1. 文件权限是否正确
2. 目录路径是否存在
3. JSON格式是否正确
4. 队列运行器是否正常运行
"""
    
    return instructions

def create_queue_update_script():
    """创建队列更新脚本"""
    
    script_content = """#!/usr/bin/env python3
"""
OpenCode CLI优化方案队列配置更新脚本
更新队列状态文件和配置文件中的文件路径
"""

import json
import os
from datetime import datetime

def update_queue_state_file():
    """更新队列状态文件中的文件路径"""
    
    queue_state_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    
    if not os.path.exists(queue_state_file):
        print(f"❌ 队列状态文件不存在: {queue_state_file}")
        return False
    
    try:
        # 加载队列状态
        with open(queue_state_file, 'r', encoding='utf-8') as f:
            queue_state = json.load(f)
        
        # 更新OpenCode CLI优化任务的instruction_path
        items = queue_state.get('items', {})
        if 'opencode_cli_optimization' in items:
            items['opencode_cli_optimization']['instruction_path'] = \
                "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/OpenHuman-OpenCode-CLI-优化与Athena深度集成方案.md"
            
            print("✅ 队列状态文件中的文件路径已更新")
        else:
            print("⚠️ 队列状态文件中未找到OpenCode CLI优化任务")
        
        # 保存更新
        with open(queue_state_file, 'w', encoding='utf-8') as f:
            json.dump(queue_state, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        print(f"❌ 更新队列状态文件失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 OpenCode CLI优化方案队列配置更新工具")
    
    if update_queue_state_file():
        print("✅ 队列配置更新完成")
    else:
        print("❌ 队列配置更新失败")

if __name__ == "__main__":
    main()
"""
    
    script_path = "/Volumes/1TB-M2/openclaw/update_queue_config.py"
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # 设置执行权限
        os.chmod(script_path, 0o755)
        
        print(f"✅ 队列更新脚本已创建: {script_path}")
        return script_path
        
    except Exception as e:
        print(f"❌ 创建队列更新脚本失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("📁 OpenCode CLI优化方案文件移动和队列更新工具")
    print("=" * 60)
    
    # 创建操作指南
    instructions = create_move_instructions()
    instructions_file = "/Volumes/1TB-M2/openclaw/opencode_plan_move_instructions.md"
    
    try:
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write(instructions)
        
        print(f"✅ 操作指南已创建: {instructions_file}")
        
    except Exception as e:
        print(f"❌ 创建操作指南失败: {e}")
        return
    
    # 创建队列更新脚本
    script_path = create_queue_update_script()
    
    print("\n🎯 下一步操作:")
    print("1. 手动执行文件复制操作（见操作指南）")
    print("2. 运行队列更新脚本: python3 update_queue_config.py")
    print("3. 验证队列状态和文件位置")
    
    print(f"\n📋 详细操作指南见: {instructions_file}")

if __name__ == "__main__":
    main()
"""
    
    script_path = "/Volumes/1TB-M2/openclaw/move_opencode_plan_to_aiplan.py"
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # 设置执行权限
        os.chmod(script_path, 0o755)
        
        print(f"✅ 文件移动工具已创建: {script_path}")
        return script_path
        
    except Exception as e:
        print(f"❌ 创建文件移动工具失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("📁 OpenCode CLI优化方案文件移动和队列更新工具")
    print("=" * 60)
    
    # 创建操作指南
    instructions = create_move_instructions()
    instructions_file = "/Volumes/1TB-M2/openclaw/opencode_plan_move_instructions.md"
    
    try:
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write(instructions)
        
        print(f"✅ 操作指南已创建: {instructions_file}")
        
    except Exception as e:
        print(f"❌ 创建操作指南失败: {e}")
        return
    
    # 创建队列更新脚本
    script_path = create_queue_update_script()
    
    print("\n🎯 下一步操作:")
    print("1. 手动执行文件复制操作（见操作指南）")
    print("2. 运行队列更新脚本: python3 update_queue_config.py")
    print("3. 验证队列状态和文件位置")
    
    print(f"\n📋 详细操作指南见: {instructions_file}")

if __name__ == "__main__":
    main()