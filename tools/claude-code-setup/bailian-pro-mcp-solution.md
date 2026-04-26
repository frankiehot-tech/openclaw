# 方案 C：百炼 PRO + 自定义 MCP 服务器

## 架构概述

```
用户请求
   ↓
AI Assistant TUI
   ↓
┌─────────────────────────────────────┐
│  AI 推理层 (DashScope Adapter v2)     │
│  localhost:8080 → 百炼 PRO API        │
│  模型: Qwen3.6-Plus                   │
└─────────────────────────────────────┘
   ↓
┌─────────────────────────────────────┐
│  工具执行层 (MCP Server via stdio)   │
│  ai-tools-server.py              │
│  工具: Bash, Read, Write, Edit,      │
│        Glob, Grep, WebFetch           │
└─────────────────────────────────────┘
   ↓
实际执行
```

## 核心组件

### 1. DashScope 适配器 (dashscope-adapter.py)
- **作用**: 将 AI Assistant 的 LLM API 请求转换为百炼 OpenAI 兼容格式
- **位置**: `/Users/frankie/ai-code-setup/dashscope-adapter.py`
- **监听**: `http://localhost:8080`

### 2. MCP 工具服务器 (ai-tools-server.py)
- **作用**: 为 AI Assistant 提供完整工具执行能力
- **位置**: `/Users/frankie/ai-code-setup/stage1/mcp-servers/ai-tools-server.py`
- **协议**: MCP stdio (AI Assistant 自动启动)

### 3. AI Assistant 配置
- **全局设置**: `~/.ai/settings.json` - MCP 服务器配置
- **项目设置**: `~/.ai/settings.local.json` - 环境变量和权限

## 安装步骤

### 步骤 1：运行安装脚本
```bash
cd /Users/frankie/ai-code-setup
bash setup-mcp-tools.sh
```

### 步骤 2：添加环境变量到 ~/.zshrc
```bash
# 百炼 PRO + MCP 配置
export LLM_BASE_URL=http://localhost:8080
export LLM_MODEL=qwen3.6-plus
export DASHSCOPE_API_KEY=sk-8ab52e8a07e940bb8ac87d381dc3dd49
export DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export DASHSCOPE_TARGET_MODEL=qwen3.6-plus
```

### 步骤 3：应用配置
```bash
source ~/.zshrc
```

### 步骤 4：确保适配器运行
```bash
# 检查是否已在运行
lsof -ti:8080 || cd /Users/frankie/ai-code-setup && nohup python3 dashscope-adapter.py > /tmp/dashscope-adapter.log 2>&1 &
```

### 步骤 5：启动 AI Assistant
```bash
ai
```

## 可用工具

| 工具 | 描述 | 参数 |
|------|------|------|
| **Bash** | 执行 Bash 命令 | command, description, timeout |
| **Read** | 读取文件内容 | file_path, offset, limit |
| **Write** | 写入文件 | file_path, content |
| **Edit** | 编辑文件 | file_path, edits |
| **Glob** | 文件匹配查找 | pattern, path |
| **Grep** | 正则搜索 | pattern, path, output_mode, file_pattern |
| **WebFetch** | 获取网页内容 | url, max_length |

## 优势

| 特性 | 说明 |
|------|------|
| 💰 **成本** | 百炼 PRO 90,000次/月，约 599 CNY |
| 🛠️ **工具能力** | 通过 MCP 提供完整工具支持 |
| 🔄 **兼容性** | 支持 AI Assistant TUI 完整工作流 |
| 📦 **可扩展** | 轻松添加新工具到 MCP 服务器 |
| 🔒 **安全** | 本地执行，无外部工具调用 |

## 限制

| 限制 | 说明 |
|------|------|
| 🧠 **推理能力** | Qwen3.6-Plus 推理能力可能不如 AI 原生 |
| ⚡ **响应速度** | 经过适配器转换，延迟略高 |
| 🔧 **工具调用** | 模型需要学会调用 MCP 工具，可能需要引导 |

## 故障排除

### MCP 服务器未启动
```bash
# 手动测试
cd /Users/frankie/ai-code-setup/stage1/mcp-servers
python3 ai-tools-server.py
# 应看到 "🚀 AI Tools MCP Server 启动中..."
```

### 适配器未运行
```bash
# 重启适配器
lsof -ti:8080 | xargs kill 2>/dev/null
cd /Users/frankie/ai-code-setup && nohup python3 dashscope-adapter.py > /tmp/dashscope-adapter.log 2>&1 &
```

### AI Assistant 未识别工具
```bash
# 检查配置
cat ~/.ai/settings.json
# 应看到 "mcpServers" 配置
```

## 文件清单

| 文件 | 用途 |
|------|------|
| `dashscope-adapter.py` | DashScope API 适配器 |
| `stage1/mcp-servers/ai-tools-server.py` | MCP 工具服务器 |
| `setup-mcp-tools.sh` | 安装配置脚本 |
| `~/.ai/settings.json` | AI Assistant 全局配置 |
| `~/.ai/settings.local.json` | AI Assistant 项目配置 |
| `restart-adapter.sh` | 适配器重启脚本 |