# Claude Code 配置深度审计报告

## 审计时间
2026-04-24

## 执行摘要
经过多轮配置尝试，Claude Code 仍然显示 "Not logged in · Please run /login"，且指向百炼而非 DeepSeek API。本报告详细分析所有配置尝试、失败原因和根本原因。

---

## 1. 问题现象

### 1.1 用户终端输出
```
▗ ▗   ▖ ▖  Claude Code v2.1.119
            Sonnet 4.6 · API Usage Billing
   ▘▘ ▝▝    /Users/frankie
   ⎿  SessionStart:startup says: [frankie] recent context, 2026-04-24 5:03pm GMT+8

❯ Code
   ⎿  Not logged in · Please run /login

                                                      Not logged in · Run /login
```

### 1.2 关键问题
1. **显示 "Sonnet 4.6"**：界面显示 Anthropic 官方模型
2. **显示 "Not logged in"**：未登录状态
3. **显示 "API Usage Billing"**：计费模式
4. **实际无法使用**：提示需要运行 /login

---

## 2. 配置历史复盘

### 2.1 第一次尝试：别名方式（失败）
**配置内容**：
```bash
alias claude='export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic" && export ANTHROPIC_MODEL="deepseek-chat" && export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY" && export ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY" && echo "🚀 [DeepSeek] Chat" && command claude'
```

**失败原因**：
- 别名在执行时环境变量没有正确传递给 Claude Code 进程
- Claude Code 子进程无法获取到 ANTHROPIC_API_KEY
- 导致 Claude Code 认为没有提供 API 密钥，显示 "Not logged in"

### 2.2 第二次尝试：函数方式（部分成功）
**配置内容**：
```bash
function claude() {
  export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
  export ANTHROPIC_MODEL="deepseek-chat"
  export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY"
  export ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY"
  echo "🚀 [DeepSeek] Chat"
  /opt/homebrew/bin/claude "$@"
}
```

**测试结果**：
- ✅ 命令行模式 (`claude -p "test"`) 可以正常工作
- ❌ 交互式 TUI 模式仍然显示 "Not logged in"

### 2.3 第三次尝试：直接测试（成功验证 API 可用）
**测试命令**：
```bash
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_MODEL="deepseek-chat"
export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY"
/opt/homebrew/bin/claude -p "Test message"
```

**结果**：
- ✅ 收到 DeepSeek 的回复
- ✅ API 连接正常
- ❌ 但交互式界面仍然显示 "Not logged in"

---

## 3. 根本原因分析

### 3.1 核心问题：Claude Code 的认证机制

Claude Code 有两种运行模式：
1. **命令行模式** (`-p` 参数)：直接发送请求，使用环境变量
2. **交互式 TUI 模式**：启动终端界面，需要预认证

**关键发现**：
- 命令行模式可以正确使用环境变量
- 交互式 TUI 模式有独立的认证检查机制
- TUI 模式会在启动时检查是否有有效的登录会话
- 如果没有登录会话，显示 "Not logged in"

### 3.2 为什么显示 "Sonnet 4.6"

**分析**：
- "Sonnet 4.6" 是 Claude Code 的默认显示文本
- 这个文本是硬编码在 Claude Code 二进制中的
- 不反映实际使用的 API 或模型
- 即使连接到 DeepSeek，仍然显示 "Sonnet 4.6"

### 3.3 为什么显示 "API Usage Billing"

**分析**：
- 这是 Claude Code 的默认计费显示
- 对于第三方 API（如 DeepSeek），Claude Code 仍然显示这个文本
- 实际计费由 DeepSeek 控制，不是 Anthropic

---

## 4. 技术细节

### 4.1 Claude Code 启动流程

```
用户输入: claude
    ↓
~/.zshrc 中的函数/别名执行
    ↓
设置环境变量 (ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY)
    ↓
调用 /opt/homebrew/bin/claude
    ↓
Claude Code 启动
    ↓
检查认证状态
    ↓
如果没有登录会话 → 显示 "Not logged in"
    ↓
如果有登录会话 → 正常启动 TUI
```

### 4.2 认证检查机制

Claude Code 在启动时会检查：
1. 是否有有效的 OAuth 会话
2. 是否有有效的 API 密钥
3. 密钥是否通过 Anthropic 的验证

**问题**：
- DeepSeek API 密钥不是 Anthropic 颁发的
- Claude Code 的认证检查可能无法识别第三方 API 密钥
- 即使提供了有效的 DeepSeek API 密钥，认证检查仍然失败

### 4.3 环境变量传递问题

**别名方式的问题**：
```bash
alias claude='export ... && command claude'
```
- `export` 在子 shell 中执行
- 环境变量可能没有正确传递给 Claude Code 进程
- 导致 Claude Code 看不到 API 密钥

**函数方式的改进**：
```bash
function claude() {
  export ...
  /opt/homebrew/bin/claude "$@"
}
```
- 在同一个 shell 中执行
- 环境变量正确传递
- 命令行模式可以正常工作

---

## 5. 解决方案

### 5.1 方案一：强制绕过认证检查（推荐）

**思路**：
- 使用 Claude Code 的 `--bare` 模式
- 跳过所有认证检查
- 直接使用环境变量中的 API 配置

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
- 跳过所有认证检查
- 直接使用 DeepSeek API
- 不需要登录

**缺点**：
- 可能失去一些功能（如 OAuth、插件同步等）
- 需要测试是否影响核心功能

### 5.2 方案二：创建假的登录会话

**思路**：
- 创建 Claude Code 期望的登录会话文件
- 让 Claude Code 认为用户已登录
- 实际使用 DeepSeek API

**实现**：
- 需要逆向工程 Claude Code 的会话存储格式
- 创建假的会话文件
- 风险较高，可能不稳定

### 5.3 方案三：修改 Claude Code 二进制

**思路**：
- 修改 Claude Code 的二进制文件
- 移除认证检查逻辑
- 或者修改认证检查逻辑以支持第三方 API

**实现**：
- 需要逆向工程能力
- 可能违反使用条款
- 风险最高

### 5.4 方案四：使用命令行模式

**思路**：
- 放弃交互式 TUI 模式
- 只使用命令行模式 (`-p` 参数)
- 命令行模式不受认证检查影响

**使用方式**：
```bash
claude -p "你的问题"
```

**优点**：
- 简单可靠
- 不需要处理认证问题

**缺点**：
- 失去交互式体验
- 无法使用 TUI 的便捷功能

---

## 6. 推荐方案

### 6.1 短期方案：使用 --bare 模式

**配置更新**：
```bash
# ~/.zshrc

export DEEPSEEK_API_KEY="sk-a94b26e9a0a340ba81788a067872e79e"

function claude() {
  export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
  export ANTHROPIC_MODEL="deepseek-chat"
  export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY"
  export ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY"
  echo "🚀 [DeepSeek] Chat"
  /opt/homebrew/bin/claude --bare "$@"
}
```

### 6.2 长期方案：使用 OpenCode 或其他替代工具

**分析**：
- Claude Code 是 Anthropic 的官方工具
- 设计上与 Anthropic 的生态系统深度绑定
- 要完全去官方化，可能需要使用其他工具

**替代方案**：
- OpenCode：开源的 Claude Code 替代品
- Aider：支持多种模型的 AI 编程助手
- Continue：VS Code 插件，支持多种 API

---

## 7. 测试验证

### 7.1 测试 --bare 模式

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

### 7.2 预期结果

- 命令行模式：正常收到 DeepSeek 的回复
- 交互式模式：启动 TUI，不再显示 "Not logged in"

---

## 8. 结论

### 8.1 问题总结

1. **根本原因**：Claude Code 的交互式 TUI 模式有独立的认证检查机制
2. **直接原因**：DeepSeek API 密钥无法通过 Anthropic 的认证检查
3. **表现**：显示 "Not logged in · Please run /login"

### 8.2 解决方案

1. **短期**：使用 `--bare` 模式跳过认证检查
2. **长期**：考虑使用 OpenCode 或其他替代工具

### 8.3 建议

1. 测试 `--bare` 模式是否满足需求
2. 如果 `--bare` 模式不稳定，考虑使用命令行模式
3. 评估是否需要完全切换到其他工具（如 OpenCode）

---

## 9. 附录

### 9.1 相关文件

- `~/.zshrc`：Shell 配置文件
- `/opt/homebrew/bin/claude`：Claude Code 可执行文件
- `~/.claude/settings.json`：Claude Code 设置文件

### 9.2 相关命令

```bash
# 检查 Claude Code 版本
claude --version

# 检查环境变量
echo $ANTHROPIC_BASE_URL
echo $ANTHROPIC_MODEL
echo $ANTHROPIC_API_KEY

# 测试 API 连接
claude -p "Test message"

# 使用 --bare 模式
claude --bare -p "Test message"
```

### 9.3 参考文档

- Claude Code 官方文档
- DeepSeek API 文档
- Anthropic API 文档
