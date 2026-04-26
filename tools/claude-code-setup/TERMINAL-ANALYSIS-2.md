# 2 个终端问题深度分析与修复

> 分析时间：2026-04-24
> 问题：claude-big/claude-v2 指向同一模型 + 输出质量问题

---

## 问题 1：claude-big 和 claude-v2 指向同一模型

### 现象
- `claude-big` → 启动本地 Qwen2.5-14B
- `claude-v2` → 启动本地 Qwen2.5-14B（默认 auto 模式，轻量任务也走本地）
- 两者实际使用同一模型，没有区分度

### 根因分析

**`claude-big` 别名配置：**
```bash
alias claude-big='... ANTHROPIC_MODEL="qwen2.5-claude" ...'
```
- 直接设置环境变量，启动 Claude Code
- 固定使用本地 Qwen2.5-14B

**`claude-v2` 别名配置：**
```bash
alias claude-v2='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh'
```
- 调用智能路由脚本
- 默认 `auto` 模式，根据任务复杂度选择
- **但轻量任务也指向 `qwen2.5-claude`**（本地模型）

**结论**：两者都指向同一本地模型，没有实现"分层路由"的设计目标。

### 修复方案

**重新定义别名分工：**

| 别名 | 用途 | 模型 | 场景 |
|------|------|------|------|
| `claude-big` | 本地大模型 | Qwen2.5-14B | 日常编码、轻量任务 |
| `claude-v2` | 智能路由 | 自动选择 | 根据任务复杂度自动切换 |
| `claude-cloud` | 强制云端 | Qwen-Max | 复杂任务、深度分析 |

**修复 claude-v2 脚本：**
- 默认 `auto` 模式应更智能地判断任务类型
- 添加 `claude-v2 local` 和 `claude-v2 cloud` 子命令

---

## 问题 2：输出质量问题

### 现象
- 模型输出重复、浅层、格式混乱
- 即使升级到 Qwen2.5-14B，问题仍存在

### 根因分析

#### 2.1 System Prompt 问题
当前 Modelfile 的 System Prompt：
```
You are an expert software engineer. Follow the user's instructions carefully...
```

**问题**：
- 过于简单，没有针对 Claude Code 场景优化
- 缺少"避免重复"、"结构化输出"等关键指令
- 没有定义工具使用规范

#### 2.2 Claude Code 与本地模型兼容性问题
- Claude Code 为 Anthropic Claude 模型设计
- Qwen2.5 是不同架构，对 Claude Code 的 system prompt 理解可能不准确
- 工具调用（tool use）格式可能不兼容

#### 2.3 参数配置问题
当前参数：
```
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 32768
PARAMETER repeat_penalty 1.1
```

**问题**：
- `repeat_penalty 1.1` 可能不够高（建议 1.15-1.2）
- `num_ctx 32768` 对 14B 模型可能过大（建议 8192-16384）
- 缺少 `num_predict` 限制（防止无限生成）

### 修复方案

**优化 Modelfile：**
```bash
FROM qwen2.5:14b

SYSTEM """You are an expert software engineer. 

CRITICAL RULES:
1. NEVER repeat the same information multiple times
2. Be concise and direct - avoid filler words
3. Use structured formats (bullet points, code blocks) for clarity
4. When analyzing code, provide specific technical details, not generic observations
5. If you don't know something, say so directly
6. Always respond in Chinese unless code or technical terms require English

CODE STYLE:
- Write clean, well-documented code
- Show minimal diff when editing files
- Use meaningful variable names"""

PARAMETER temperature 0.75
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 16384
PARAMETER repeat_penalty 1.2
PARAMETER num_predict 4096
```

---

## 综合修复步骤

### Step 1：修复 claude-v2 脚本（添加云端强制模式）

编辑 `claude-dual-model-v2.sh`，修改 alias：

```bash
# 在 ~/.zshrc 中修改 claude-v2 别名
alias claude-v2='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh auto'
alias claude-cloud='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh cloud'
```

### Step 2：重新创建优化模型

```bash
# 删除旧模型
ollama rm qwen2.5-claude

# 创建新模型（使用优化配置）
cat > /Users/frankie/Modelfile.qwen-claude-v2 << 'EOF'
FROM qwen2.5:14b

SYSTEM """You are an expert software engineer. 

CRITICAL RULES:
1. NEVER repeat the same information multiple times
2. Be concise and direct - avoid filler words
3. Use structured formats (bullet points, code blocks) for clarity
4. When analyzing code, provide specific technical details, not generic observations
5. If you don't know something, say so directly
6. Always respond in Chinese unless code or technical terms require English

CODE STYLE:
- Write clean, well-documented code
- Show minimal diff when editing files
- Use meaningful variable names"""

PARAMETER temperature 0.75
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 16384
PARAMETER repeat_penalty 1.2
PARAMETER num_predict 4096
EOF

ollama create qwen2.5-claude -f /Users/frankie/Modelfile.qwen-claude-v2
```

### Step 3：更新 ~/.zshrc 别名

```bash
# 本地模型（固定）
alias claude-big='export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="qwen2.5-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🧠 [本地 Ollama] Qwen2.5-14B (16K ctx)" && command claude --bare'

# 智能路由（自动选择）
alias claude-v2='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh auto'

# 强制云端
alias claude-cloud='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh cloud'
```

---

## 验证修复

```bash
# 1. 验证模型重新创建
ollama list | grep qwen2.5-claude

# 2. 验证本地模式
claude-big
# 应显示：🧠 [本地 Ollama] Qwen2.5-14B (16K ctx)

# 3. 验证智能路由
claude-v2
# 应显示任务复杂度分析，然后选择本地或云端

# 4. 验证云端模式
claude-cloud
# 应显示：🎯 云端: Qwen-Max (百炼)

# 5. 测试输出质量
# 在 Claude Code 中输入：
# "分析这个 Python 函数的复杂度：def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)"
# 应得到：无重复、有深度、结构化的回答
```
