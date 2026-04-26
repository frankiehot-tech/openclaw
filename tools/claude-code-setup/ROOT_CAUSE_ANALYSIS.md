# Claude Code 配置失败根本原因分析

## 问题概述

经过多轮配置尝试，Claude Code 仍然显示：
- "Sonnet 4.6 · API Usage Billing"
- "Not logged in · Please run /login"

用户无法正常使用 DeepSeek API，配置多次失败。

---

## 配置历史复盘

### 尝试 1：别名方式（完全失败）

```bash
alias claude='export ANTHROPIC_BASE_URL="..." && export ANTHROPIC_API_KEY="..." && command claude'
```

**结果**：
- 环境变量未正确传递
- Claude Code 子进程看不到 API 密钥
- 显示 "Not logged in"

### 尝试 2：函数方式（部分成功）

```bash
function claude() {
  export ANTHROPIC_BASE_URL="..."
  export ANTHROPIC_API_KEY="..."
  /opt/homebrew/bin/claude "$@"
}
```

**结果**：
- ✅ 命令行模式 (`-p`) 可以工作
- ❌ 交互式 TUI 模式仍然显示 "Not logged in"

### 尝试 3：直接环境变量测试（验证 API 可用）

```bash
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_API_KEY="sk-a94b26e9a0a340ba81788a067872e79e"
claude -p "test"
```

**结果**：
- ✅ 收到 DeepSeek 回复
- ✅ API 连接正常
- ❌ TUI 模式仍然无法使用

---

## 根本原因分析

### 1. Claude Code 的双重架构

Claude Code 有两种完全不同的运行模式：

#### 模式 A：命令行模式 (`-p` 参数)
```
用户 → claude -p "message" → 直接发送 API 请求 → 返回结果
```
- 读取环境变量
- 不需要登录状态
- 可以正常使用第三方 API

#### 模式 B：交互式 TUI 模式
```
用户 → claude → 启动 TUI → 检查登录状态 → 显示界面
```
- 独立的认证检查机制
- 需要有效的登录会话
- 第三方 API 密钥无法通过认证

### 2. 认证检查机制

Claude Code TUI 启动时会执行：

```javascript
// 伪代码
if (!hasValidLoginSession()) {
  show "Not logged in · Please run /login"
  return
}
```

**检查内容**：
1. OAuth 会话是否存在
2. API 密钥是否有效
3. 密钥是否通过 Anthropic 验证

**问题**：
- DeepSeek API 密钥不是 Anthropic 颁发的
- 认证检查无法识别第三方 API
- 即使密钥有效，也被视为 "未登录"

### 3. 为什么显示 "Sonnet 4.6"

**原因**：
- "Sonnet 4.6" 是硬编码在 Claude Code 二进制中的默认文本
- 不反映实际使用的模型或 API
- 即使连接到 DeepSeek，仍然显示这个文本

### 4. 为什么显示 "API Usage Billing"

**原因**：
- 这是 Claude Code 的默认计费显示
- 对于第三方 API，仍然显示这个文本
- 实际计费由 DeepSeek 控制

---

## 技术细节

### Claude Code 启动流程

```
1. 用户输入: claude
2. ~/.zshrc 函数执行
3. 设置环境变量
4. 调用 /opt/homebrew/bin/claude
5. Claude Code 启动
6. 【关键】检查认证状态
7. 如果没有登录会话 → 显示 "Not logged in"
8. 如果有登录会话 → 正常启动 TUI
```

### 环境变量传递问题

**别名方式的问题**：
```bash
alias claude='export ... && command claude'
# export 在子 shell 中执行
# 环境变量可能丢失
```

**函数方式的改进**：
```bash
function claude() {
  export ...
  /opt/homebrew/bin/claude "$@"
}
# 在同一个 shell 中执行
# 环境变量正确传递
```

---

## 解决方案

### 方案 1：使用 --bare 模式（推荐）

**原理**：
- `--bare` 参数跳过所有认证检查
- 直接使用环境变量中的 API 配置
- 不需要登录状态

**配置**：
```bash
function claude() {
  export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
  export ANTHROPIC_MODEL="deepseek-chat"
  export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY"
  export ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY"
  echo "🚀 [DeepSeek] Chat"
  /opt/homebrew/bin/claude --bare "$@"
}
```

**优点**：
- 跳过认证检查
- 直接使用 DeepSeek API
- 不需要登录

**缺点**：
- 可能失去一些功能（OAuth、插件同步）

### 方案 2：使用命令行模式

**使用方式**：
```bash
claude -p "你的问题"
```

**优点**：
- 简单可靠
- 不受认证影响

**缺点**：
- 失去交互式体验

### 方案 3：使用替代工具

**推荐**：
- OpenCode：开源替代品
- Aider：支持多种模型
- Continue：VS Code 插件

---

## 测试验证

### 测试 --bare 模式

```bash
# 设置环境变量
export DEEPSEEK_API_KEY="sk-a94b26e9a0a340ba81788a067872e79e"
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_MODEL="deepseek-chat"
export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY"

# 测试命令行模式
/opt/homebrew/bin/claude --bare -p "Test message"

# 测试交互式模式
/opt/homebrew/bin/claude --bare
```

### 预期结果

- 命令行模式：正常收到 DeepSeek 回复
- 交互式模式：启动 TUI，不再显示 "Not logged in"

---

## 结论

### 问题总结

1. **根本原因**：Claude Code TUI 有独立的认证检查机制
2. **直接原因**：DeepSeek API 密钥无法通过 Anthropic 认证
3. **表现**：显示 "Not logged in · Please run /login"

### 解决方案

1. **短期**：使用 `--bare` 模式跳过认证检查
2. **长期**：考虑使用 OpenCode 等替代工具

### 建议

1. 测试 `--bare` 模式是否满足需求
2. 如果 `--bare` 不稳定，使用命令行模式
3. 评估是否需要完全切换到其他工具
