#!/usr/bin/env python3
"""
基因管理Agent队列设置脚本
生成配置文件和操作指南，避免直接修改系统文件
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def create_gene_management_config():
    """创建基因管理任务配置"""

    config = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "description": "Athena/Open Human基因管理Agent工程实施方案队列配置",
        "tasks": [
            {
                "id": "gene_mgmt_g0_infrastructure",
                "title": "OpenHuman-Athena-基因管理系统G0阶段基础设施搭建-VSCode执行指令",
                "instruction_path": "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md",
                "entry_stage": "build",
                "risk_level": "low",
                "unattended_allowed": True,
                "metadata": {
                    "priority": "S0",
                    "lane": "build_auto",
                    "epic": "gene_management",
                    "category": "infrastructure",
                    "rationale": "基因管理系统的基础设施搭建是后续演进的前提",
                    "phase": "G0",
                    "estimated_duration": "30分钟",
                },
            },
            {
                "id": "gene_mgmt_g1_cli_implementation",
                "title": "OpenHuman-Athena-基因管理系统G1阶段CLI命令实现-VSCode执行指令",
                "instruction_path": "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md",
                "entry_stage": "build",
                "risk_level": "low",
                "unattended_allowed": True,
                "metadata": {
                    "priority": "S0",
                    "lane": "build_auto",
                    "epic": "gene_management",
                    "category": "cli_implementation",
                    "rationale": "CLI命令是基因管理系统的主要操作界面",
                    "depends_on": ["gene_mgmt_g0_infrastructure"],
                    "phase": "G1",
                    "estimated_duration": "1小时",
                },
            },
            {
                "id": "gene_mgmt_g2_queue_integration",
                "title": "OpenHuman-Athena-基因管理系统G2阶段队列集成-VSCode执行指令",
                "instruction_path": "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md",
                "entry_stage": "build",
                "risk_level": "medium",
                "unattended_allowed": True,
                "metadata": {
                    "priority": "S1",
                    "lane": "build_auto",
                    "epic": "gene_management",
                    "category": "queue_integration",
                    "rationale": "队列集成确保基因管理系统与现有AI Plan工作流无缝对接",
                    "depends_on": ["gene_mgmt_g1_cli_implementation"],
                    "phase": "G2",
                    "estimated_duration": "45分钟",
                },
            },
            {
                "id": "gene_mgmt_audit",
                "title": "OpenHuman-Athena-基因管理系统实施审计-Codex审计指令",
                "instruction_path": "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md",
                "entry_stage": "review",
                "risk_level": "low",
                "unattended_allowed": False,
                "metadata": {
                    "priority": "R1",
                    "lane": "review_auto",
                    "epic": "gene_management",
                    "category": "implementation_audit",
                    "rationale": "审计基因管理系统实施效果",
                    "depends_on": ["gene_mgmt_g2_queue_integration"],
                    "phase": "Audit",
                    "estimated_duration": "30分钟",
                },
            },
        ],
    }

    return config


def create_queue_manifest(config):
    """创建队列清单文件"""

    manifest = {
        "queue_id": "openhuman_aiplan_gene_management_20260405",
        "name": "OpenHuman AIPlan 基因管理队列",
        "description": "基因管理系统实施的专用队列",
        "runner_mode": "opencode_build",
        "created_at": datetime.now().isoformat(),
        "items": config["tasks"],
    }

    return manifest


def create_setup_instructions(config, manifest):
    """创建设置操作指南"""

    instructions = f"""# 🧬 Athena/Open Human基因管理Agent队列设置指南

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📋 任务概述

将基因管理Agent工程实施方案编排进AI Plan任务队列，实现分阶段实施。

## 🎯 任务配置

### 构建任务 ({len([t for t in config['tasks'] if t['entry_stage'] == 'build'])}个)
"""

    for task in config["tasks"]:
        if task["entry_stage"] == "build":
            instructions += f"""
- **{task['title']}**
  - ID: `{task['id']}`
  - 优先级: {task['metadata']['priority']}
  - 阶段: {task['metadata']['phase']}
  - 预估时长: {task['metadata']['estimated_duration']}
  - 依赖: {', '.join(task['metadata'].get('depends_on', [])) or '无'}
"""

    instructions += f"""
### 审计任务 ({len([t for t in config['tasks'] if t['entry_stage'] == 'review'])}个)
"""

    for task in config["tasks"]:
        if task["entry_stage"] == "review":
            instructions += f"""
- **{task['title']}**
  - ID: `{task['id']}`
  - 优先级: {task['metadata']['priority']}
  - 阶段: {task['metadata']['phase']}
  - 预估时长: {task['metadata']['estimated_duration']}
"""

    instructions += """
## 🔧 手动设置步骤

### 步骤1: 创建队列清单文件

在AI Plan目录创建队列清单文件:

```bash
# 创建队列清单文件
echo '{"queue_id":"openhuman_aiplan_gene_management_20260405","name":"OpenHuman AIPlan 基因管理队列","description":"基因管理系统实施的专用队列","runner_mode":"opencode_build","created_at":"2026-04-05T00:00:00","items":[' > "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/OpenHuman-AIPlan-基因管理队列.queue.json"
```

### 步骤2: 添加任务项

将以下JSON内容添加到队列文件中:

```json
{
  "id": "gene_mgmt_g0_infrastructure",
  "title": "OpenHuman-Athena-基因管理系统G0阶段基础设施搭建-VSCode执行指令",
  "instruction_path": "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md",
  "entry_stage": "build",
  "risk_level": "low",
  "unattended_allowed": true,
  "metadata": {
    "priority": "S0",
    "lane": "build_auto",
    "epic": "gene_management",
    "category": "infrastructure",
    "rationale": "基因管理系统的基础设施搭建是后续演进的前提",
    "phase": "G0",
    "estimated_duration": "30分钟"
  }
}
```

### 步骤3: 更新队列状态

更新队列状态文件:

```bash
# 更新队列状态
echo '{"queue_id":"openhuman_aiplan_gene_management_20260405","name":"OpenHuman AIPlan 基因管理队列","queue_status":"running","current_item_id":"gene_mgmt_g0_infrastructure"}' > "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
```

## 🚀 执行顺序

任务将按以下顺序自动执行:

1. **G0阶段**: 基础设施搭建 (30分钟)
2. **G1阶段**: CLI命令实现 (1小时)  
3. **G2阶段**: 队列系统集成 (45分钟)
4. **审计阶段**: 实施效果审计 (30分钟)

## 📊 监控方式

- **Web界面**: http://127.0.0.1:8080
- **队列状态**: 查看基因管理队列执行进度
- **日志文件**: `/Volumes/1TB-M2/openclaw/logs/`

## 🔍 验证方法

执行完成后，验证以下内容:

1. ✅ 基因序列基础设施创建完成
2. ✅ CLI命令框架实现完成  
3. ✅ 队列系统集成配置就绪
4. ✅ 审计报告生成

## 📝 配置文件位置

- **任务配置**: `/Volumes/1TB-M2/openclaw/scripts/gene_management_config.json`
- **队列清单**: `/Volumes/1TB-M2/openclaw/scripts/gene_management_queue_manifest.json`
- **执行指令**: `/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md`

---

**注意**: 由于权限限制，需要手动执行上述步骤完成队列编排。
"""

    return instructions


def main():
    """主函数"""

    print("=" * 60)
    print("🧬 基因管理Agent队列设置脚本")
    print("=" * 60)

    # 创建配置
    config = create_gene_management_config()

    # 创建队列清单
    manifest = create_queue_manifest(config)

    # 创建操作指南
    instructions = create_setup_instructions(config, manifest)

    # 保存配置文件
    config_path = Path("scripts/gene_management_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # 保存队列清单
    manifest_path = Path("scripts/gene_management_queue_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # 保存操作指南
    instructions_path = Path("scripts/gene_management_queue_setup_guide.md")
    with open(instructions_path, "w", encoding="utf-8") as f:
        f.write(instructions)

    print("✅ 配置文件生成完成:")
    print(f"   📄 任务配置: {config_path}")
    print(f"   📄 队列清单: {manifest_path}")
    print(f"   📄 操作指南: {instructions_path}")

    print("\n📊 任务配置摘要:")
    print(f"   🔧 构建任务: {len([t for t in config['tasks'] if t['entry_stage'] == 'build'])}个")
    print(f"   🔍 审计任务: {len([t for t in config['tasks'] if t['entry_stage'] == 'review'])}个")
    print(f"   ⏱️  总预估时长: 2小时45分钟")

    print("\n🎯 下一步操作:")
    print("   1. 查看操作指南: scripts/gene_management_queue_setup_guide.md")
    print("   2. 按照指南手动设置队列")
    print("   3. 监控任务执行进度")

    print("\n" + "=" * 60)
    print("🚀 基因管理Agent队列设置准备就绪!")
    print("=" * 60)


if __name__ == "__main__":
    main()
