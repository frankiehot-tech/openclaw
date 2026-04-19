#!/usr/bin/env python3
"""
AI 编程工具提示词集成脚本 - 修复版本
将生成的 Agent 提示词文件集成到 Athena-Open Human 系统中
"""

import os
import shutil
from pathlib import Path

import yaml


def create_vscode_config(project_root):
    """创建 VS Code 配置文件"""
    vscode_dir = project_root / ".vscode"
    vscode_dir.mkdir(exist_ok=True)

    # 创建 .cursorrules 文件
    cursor_rules = """# Cursor/Trae 规则配置

## 项目特定规则
- 遵循 Athena-Open Human 项目的代码规范
- 优先使用项目中已有的技术栈
- 确保与现有架构模式兼容

## Agent 系统开发规则
- 使用 LangGraph 状态机设计多 Agent 协作
- 实现类型安全的跨 Agent 状态传递
- 遵循项目的错误处理和重试机制

## 代码生成约束
- 必须包含适当的错误处理
- 实现性能监控和日志记录
- 确保代码的可测试性和可维护性
"""

    with open(vscode_dir / ".cursorrules", "w", encoding="utf-8") as f:
        f.write(cursor_rules)

    # 创建 roo-code-prompt.md 文件
    roo_prompt = """# Roo Code 系统提示词 - Athena-Open Human

## 项目概述
这是一个基于 LangGraph 的多 Agent 系统，用于实现 AI 驱动的自动化工作流。

## 技术栈
- **Agent 框架**: LangGraph (状态机驱动的多 Agent 协作)
- **后端框架**: FastAPI + PostgreSQL + Redis
- **前端框架**: React + TypeScript + Tailwind CSS
- **任务队列**: Celery + Redis
- **监控体系**: Prometheus + Grafana

## 开发规范

### 代码风格
- 使用 TypeScript/Type Annotations 确保类型安全
- 遵循项目的代码结构和命名约定
- 实现适当的错误处理和日志记录

### Agent 开发
- 每个 Agent 必须实现清晰的输入输出接口
- 使用 TypedDict 定义状态类型
- 实现适当的重试和错误处理机制

### 性能优化
- 实现请求批处理机制
- 使用 Redis 缓存提升性能
- 监控系统性能和资源使用

## 响应格式要求

### 代码生成
```typescript
// 示例：Agent 接口定义
interface Agent {
  id: string;
  name: string;
  execute(state: State): Promise<State>;
  handleError(error: Error): Promise<State>;
}
```

### 架构设计
- 先分析需求的技术复杂度
- 提出 2-3 个架构方案
- 推荐最佳方案并说明理由
- 提供技术栈建议

## 约束条件
- 优先使用项目中已有的技术栈
- 确保与现有监控体系兼容
- 考虑分布式部署需求
- 确保代码的可测试性和可维护性
"""

    with open(vscode_dir / "roo-code-prompt.md", "w", encoding="utf-8") as f:
        f.write(roo_prompt)

    print("✅ VS Code 配置文件创建完成")


def create_cli_configs(project_root):
    """创建 CLI 工具配置文件"""

    # 创建 codex.md 文件
    codex_prompt = """# Codex CLI 提示词 - Athena-Open Human

## 项目上下文
你正在为 Athena-Open Human 多 Agent 系统开发代码。这是一个基于 LangGraph 的 AI 驱动自动化系统。

## 技术约束
- 使用 Python 3.8+ 和 TypeScript
- 遵循 FastAPI 和 React 最佳实践
- 实现类型安全的代码
- 包含适当的错误处理

## 代码生成模式

### Agent 开发模式
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    input_data: Dict[str, Any]
    intermediate_results: List[Dict[str, Any]]
    final_output: Any
    error: Optional[str]

class BaseAgent:
    async def execute(self, state: AgentState) -> AgentState:
        pass
    
    async def handle_error(self, error: Exception, state: AgentState) -> AgentState:
        pass
```

### API 开发模式
```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Athena-Open Human API")

class AgentRequest(BaseModel):
    agent_id: str
    input_data: Dict[str, Any]
    
@app.post("/agents/{agent_id}/execute")
async def execute_agent(agent_id: str, request: AgentRequest):
    try:
        agent = await get_agent(agent_id)
        result = await agent.execute(request.input_data)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 响应要求
- 生成类型安全的代码
- 包含适当的错误处理
- 遵循项目的代码规范
- 提供清晰的文档注释
"""

    with open(project_root / "codex.md", "w", encoding="utf-8") as f:
        f.write(codex_prompt)

    # 创建 CLAUDE.md 文件
    claude_prompt = """# Claude Code 提示词 - Athena-Open Human

## 系统概述
Athena-Open Human 是一个基于 LangGraph 的多 Agent 系统，用于实现 AI 驱动的自动化工作流。

## 核心架构原则

### 状态机驱动设计
- 使用 LangGraph 实现复杂工作流
- 确保类型安全的跨 Agent 状态传递
- 实现条件流转和重试机制

### 多 Agent 协作模式
- **Researcher Agent**: 关键词挖掘、竞品分析、Query 获取
- **Writer Agent**: 大纲生成、正文撰写、多版本输出  
- **Validator Agent**: GEO 评分、事实核查、SEO 检查
- **Publisher Agent**: 多平台发布、数据回流、索引提交

### 工具封装层设计
- 统一 CLI 工具封装（错误重试、超时控制、结果缓存）
- Redis 缓存机制提升性能
- 支持 serpapi、people-also-ask、readability 等工具

## 代码生成指南

### Python 代码要求
```python
from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    input_data: Dict[str, Any]
    intermediate_results: List[Dict[str, Any]]
    final_output: Any
    error: Optional[str]
    current_step: str

class AgentError(Exception):
    def __init__(self, message: str, agent_id: str):
        self.message = message
        self.agent_id = agent_id
        super().__init__(f"[{agent_id}] {message}")
```

### TypeScript 代码要求
```typescript
interface Agent {
  id: string;
  name: string;
  status: 'idle' | 'running' | 'error' | 'completed';
  
  execute(state: AgentState): Promise<AgentState>;
  handleError(error: Error, state: AgentState): Promise<AgentState>;
}

interface AgentState {
  inputData: Record<string, any>;
  intermediateResults: Array<Record<string, any>>;
  finalOutput?: any;
  error?: string;
  currentStep: string;
}
```

## 响应格式要求

### 架构设计响应
1. **需求分析**: 评估技术复杂度和业务需求
2. **方案对比**: 提供 2-3 个可行的架构方案
3. **推荐方案**: 选择最佳方案并说明理由
4. **技术建议**: 提供具体的技术栈和实施建议

### 代码实现响应
1. **接口设计**: 定义清晰的输入输出接口
2. **实现代码**: 提供完整的实现代码
3. **测试用例**: 包含基本的测试案例
4. **文档说明**: 提供使用说明和注意事项

## 约束条件
- 必须使用项目中已有的技术栈
- 确保与现有监控体系兼容
- 实现适当的性能优化
- 包含完整的安全考虑

## 质量保证
- 代码必须通过类型检查
- 包含适当的错误处理
- 实现性能监控点
- 提供清晰的日志记录
"""

    with open(project_root / "CLAUDE.md", "w", encoding="utf-8") as f:
        f.write(claude_prompt)

    print("✅ CLI 配置文件创建完成")


def create_openclaw_config(project_root):
    """创建 OpenClaw 多 Agent 系统配置"""

    openclaw_config = {
        "version": "1.0",
        "name": "Athena-Open Human Multi-Agent System",
        "description": "基于 LangGraph 的多 Agent 协作系统",
        "agents": {
            "architect": {
                "role": "系统架构师",
                "prompt_file": "architect_agent_prompt.md",
                "capabilities": ["系统架构设计", "技术选型评估", "性能优化"],
            },
            "frontend": {
                "role": "前端工程师",
                "prompt_file": "frontend_agent_prompt.md",
                "capabilities": ["UI/UX 设计", "组件化开发", "性能优化"],
            },
            "backend": {
                "role": "后端工程师",
                "prompt_file": "backend_agent_prompt.md",
                "capabilities": ["API 设计开发", "数据库设计", "安全认证"],
            },
        },
        "workflows": {
            "geo_content_generation": {
                "description": "GEO 内容生成工作流",
                "agents": ["researcher", "writer", "validator", "publisher"],
                "state_schema": "GeoState",
            },
            "system_architecture": {
                "description": "系统架构设计工作流",
                "agents": ["architect", "frontend", "backend"],
                "state_schema": "ArchitectureState",
            },
        },
        "tools": {
            "cli_wrappers": ["serpapi", "people-also-ask", "readability", "ollama-api"],
            "caching": {"enabled": True, "strategy": "redis", "ttl": 3600},
            "monitoring": {"enabled": True, "tools": ["prometheus", "grafana"]},
        },
    }

    with open(project_root / "openclaw.yaml", "w", encoding="utf-8") as f:
        yaml.dump(openclaw_config, f, allow_unicode=True, indent=2)

    print("✅ OpenClaw 配置文件创建完成")


def create_integration_guide(project_root):
    """创建集成指南"""

    guide = """# Athena-Open Human 提示词系统集成指南

## 🚀 快速开始

### 1. 初始化系统
```bash
cd /Volumes/1TB-M2/openclaw
./install.sh
```

### 2. 运行集成脚本
```bash
python3 scripts/integrate_prompts_fixed.py
```

### 3. 配置开发工具

#### VS Code + Roo Code
1. 安装 Roo Code 扩展: https://marketplace.visualstudio.com/items?itemName=RooVeterinaryInc.roo-cline
2. 设置 → Roo Code: Custom System Prompt → 选择 `.vscode/roo-code-prompt.md`

#### Codex CLI
```bash
cd /Volumes/1TB-M2/openclaw
codex  # 自动读取 codex.md
```

#### Claude Code  
```bash
cd /Volumes/1TB-M2/openclaw
claude  # 自动读取 CLAUDE.md
```

## 📁 文件结构

```
/Volumes/1TB-M2/openclaw/
├── .vscode/
│   ├── .cursorrules          # Cursor/Trae 规则
│   └── roo-code-prompt.md    # Roo Code 提示词
├── scripts/
│   ├── extract-patterns.py   # 模式提取脚本
│   └── integrate_prompts_fixed.py   # 集成脚本
├── agent_prompts/
│   ├── architect_agent_prompt.md
│   ├── frontend_agent_prompt.md
│   └── backend_agent_prompt.md
├── codex.md                  # Codex CLI 提示词
├── CLAUDE.md                 # Claude Code 提示词
├── openclaw.yaml            # OpenClaw 多 Agent 配置
└── INTEGRATION_GUIDE.md     # 集成指南
```

## 🏗️ 多 Agent 工作流

### GEO 内容生成工作流
```yaml
用户需求: "生成关于 AI 编程工具的 SEO 文章"
    │
    ▼
┌──────────────┐
│ Researcher    │ → 关键词研究、竞品分析
│   Agent       │
└──────────────┘
    │
    ▼
┌──────────────┐
│ Writer       │ → 大纲生成、正文撰写
│   Agent       │
└──────────────┘
    │
    ▼
┌──────────────┐
│ Validator    │ → GEO 评分、事实核查
│   Agent       │
└──────────────┘
    │
    ▼
┌──────────────┐
│ Publisher    │ → 多平台发布、索引提交
│   Agent       │
└──────────────┘
```

## 🔧 工具配置

### VS Code 配置
在 `.vscode/settings.json` 中添加:
```json
{
  "rooCode.customSystemPrompt": "${workspaceFolder}/.vscode/roo-code-prompt.md",
  "files.associations": {
    "*.md": "markdown"
  }
}
```

## 📊 监控和指标

### 业务指标
- 内容生成成功率
- 平均质量分数  
- 发布成功率
- 用户满意度

### 技术指标
- Agent 执行时间
- 工具调用成功率
- 缓存命中率
- 系统可用性

## 🚨 故障排除

### 常见问题

**Q: Roo Code 不读取提示词文件**
A: 检查 VS Code 设置中的 `rooCode.customSystemPrompt` 路径是否正确

**Q: Codex CLI 报错**
A: 确保 `codex.md` 文件存在且格式正确

**Q: 多 Agent 协作失败**
A: 检查 `openclaw.yaml` 配置文件的语法和路径

## 🔄 更新和维护

### 定期更新提示词
```bash
# 重新提取模式
python3 scripts/extract-patterns.py

# 重新集成配置
python3 scripts/integrate_prompts_fixed.py
```

## 📞 支持

如有问题，请参考项目文档或联系开发团队获取支持。
"""

    with open(project_root / "INTEGRATION_GUIDE.md", "w", encoding="utf-8") as f:
        f.write(guide)

    print("✅ 集成指南创建完成")


def main():
    """主函数"""
    project_root = Path("/Volumes/1TB-M2/openclaw")

    print("🚀 开始集成 Athena-Open Human 提示词系统...")

    # 创建必要的目录
    (project_root / "agent_prompts").mkdir(exist_ok=True)
    (project_root / "patterns").mkdir(exist_ok=True)

    # 执行集成步骤
    create_vscode_config(project_root)
    create_cli_configs(project_root)
    create_openclaw_config(project_root)
    create_integration_guide(project_root)

    # 移动 Agent 提示词文件到专用目录
    prompt_files = {
        "architect": "architect_agent_prompt.md",
        "frontend": "frontend_agent_prompt.md",
        "backend": "backend_agent_prompt.md",
    }

    for agent_type, filename in prompt_files.items():
        source_file = project_root / filename
        target_file = project_root / "agent_prompts" / filename
        if source_file.exists():
            shutil.move(str(source_file), str(target_file))
            print(f"✅ 移动 {filename} 到 agent_prompts/")

    print("\n🎉 集成完成！")
    print("📋 下一步操作:")
    print("1. 配置你的开发工具使用相应的提示词文件")
    print("2. 开始使用多 Agent 系统进行开发")
    print("3. 参考 INTEGRATION_GUIDE.md 获取详细指南")


if __name__ == "__main__":
    main()
