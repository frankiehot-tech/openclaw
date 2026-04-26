# Claude Code 无输出问题修复报告

## 问题复盘

### 原始问题
Claude Code 启动后没有输出响应。

### 根本原因分析

经过详细排查，发现以下 **3 个核心问题**：

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| 1 | **适配器流式响应 bug** | Claude Code 使用流式 (SSE) 模式接收响应，但旧适配器无法正确处理流式，导致超时/无输出 | ✅ 已修复 |
| 2 | **适配器硬编码模型** | 旧适配器始终使用 `qwen3.6-plus`，忽略请求中的模型参数，无法切换其他模型 | ✅ 已修复 |
| 3 | **SSE 格式不匹配** | 旧适配器手动模拟 SSE 事件格式有误，Claude Code 无法正确解析 | ✅ 已修复 |

### 诊断过程

```
1. 检查适配器状态 → ✅ 正常 (端口 8080 监听中)
2. 测试非流式 API  → ✅ 正常 (返回 "OK")
3. 测试流式 API     → ❌ 超时 (30 秒无响应)
4. 检查日志文件    → ❌ 发现 ConnectionResetError
5. 直连百炼 API    → ✅ 正常 (qwen-max 可用)
6. 检查适配器代码  → ❌ 发现流式模拟 bug + 硬编码模型
```

## 修复方案

### 1. 重写适配器 (v3)

**文件**: `dashscope-adapter.py`

**主要改进**:

| 改进项 | 旧版本 (v2) | 新版本 (v3) |
|--------|-------------|-------------|
| 流式处理 | 手动模拟 SSE 事件 | 真实流式调用百炼 API 并转发 |
| 模型切换 | 硬编码 `qwen3.6-plus` | 动态从请求中提取模型名 |
| 支持模型 | 仅 1 个 | 7 个: qwen-max, qwen-plus, qwen-turbo, qwen-coder-plus, qwen-long, qwen3-235B-A22B, qwen3.6-plus |
| SSE 格式 | 手动拼接 | 标准 SSE 事件格式 |

### 2. 更新配置

**文件**: `~/.claude/settings.local.json`

```json
{
  "anthropic": {
    "baseUrl": "http://localhost:8080",
    "model": "qwen-max",
    "apiKey": "sk-921103e3b7bb4d4bb1d97308c43c71fc"
  },
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:8080",
    "ANTHROPIC_MODEL": "qwen-max"
  }
}
```

### 3. 创建诊断工具

**文件**: `diagnose-and-fix.sh`

功能：
- 检查适配器运行状态
- 测试直连百炼 API
- 测试适配器非流式/流式响应
- 测试所有可用模型
- 检查 Claude Code 配置
- 检查 MCP Server

## 百炼 Pro 可用模型验证

| 模型 | 状态 | 说明 |
|------|------|------|
| **qwen-max** | ✅ 可用 | 最强推理能力，推荐用于 Claude Code |
| **qwen-plus** | ✅ 可用 | 平衡性能与成本 |
| **qwen-turbo** | ✅ 可用 | 快速响应，适合简单任务 |
| **qwen-coder-plus** | ✅ 可用 | 代码专项优化 |
| **qwen-long** | ✅ 可用 | 长上下文支持 |
| qwen3-235B-A22B | ✅ 可用 | 开源大模型 |
| qwen3.6-plus | ✅ 可用 | 原默认模型 |

## 使用方法

### 启动 Claude Code

```bash
# 1. 确保适配器运行
lsof -ti:8080 || cd /Users/frankie/claude-code-setup && nohup python3 dashscope-adapter.py > /tmp/dashscope-adapter-v3.log 2>&1 &

# 2. 启动 Claude Code
claude
```

### 运行诊断

```bash
bash diagnose-and-fix.sh
```

### 重启适配器

```bash
bash restart-adapter.sh
```

### 切换模型

编辑 `~/.claude/settings.local.json`，修改 `ANTHROPIC_MODEL` 为任意可用模型：
- `qwen-max` (推荐)
- `qwen-plus`
- `qwen-coder-plus`
- `qwen-turbo`

## 文件清单

| 文件 | 说明 |
|------|------|
| `dashscope-adapter.py` | 适配器 v3（已修复流式+模型切换） |
| `diagnose-and-fix.sh` | 诊断和验证脚本 |
| `restart-adapter.sh` | 适配器重启脚本 |
| `~/.claude/settings.local.json` | Claude Code 配置（已更新模型） |
| `fix-summary-report.md` | 本修复报告 |