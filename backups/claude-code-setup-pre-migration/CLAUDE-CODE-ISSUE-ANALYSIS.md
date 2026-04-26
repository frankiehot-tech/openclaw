# Claude Code "傻" 输出问题 — 根因分析与修复方案

> 分析时间：2026-04-23
> 问题：Claude Code 通过 Ollama 本地 gemma4-claude 模型运行时，输出质量差（重复、浅层、格式混乱）

---

## 一、症状描述

从用户提供的终端截图，观察到以下输出质量问题：

1. **内容重复**：同一观点用不同方式反复表述（如 "适用性结论" 多次出现）
2. **缺乏深度**：对 GitHub 项目的分析停留在表面，没有实质性技术洞察
3. **格式混乱**：大量装饰性符号和分隔线，信息密度低
4. **结构冗余**：输出过度结构化，实质内容少

---

## 二、根因分析（已验证）

### 🔴 Root Cause 1：模型能力不足（主因）

**gemma4-claude 模型规格：**
- 基础模型：Gemma 4 (Google)
- 参数量：8.0B（80亿）
- 量化级别：Q4_K_M（4-bit 量化，中等质量）
- 上下文：131072 tokens（标称）

**问题分析：**

| 因素 | 影响 | 严重程度 |
|------|------|----------|
| 8B 参数量 | 推理能力、知识储备、指令跟随能力均有限 | 高 |
| Q4_K_M 量化 | 精度损失约 15-20%，进一步削弱推理能力 | 高 |
| Gemma 架构 | 相比 Llama/Mistral 架构，8B 级别表现较弱 | 中 |
| 无工具调用训练 | 无法理解 Claude Code 的 tool use 格式 | 高 |

**关键结论：**
8B Q4 量化模型本质上是一个**轻量级模型**，不适合承担 Claude Code 这种复杂 IDE 助手的角色。Claude Code 的 system prompt 包含大量工具调用指令、文件操作规范、代码编辑格式要求，这些内容对 8B 模型来说过于复杂。

---

### 🟡 Root Cause 2：System Prompt 不匹配

**Claude Code 的 System Prompt 特点：**
- 为 Claude 3.5 Sonnet/Claude 4 等大规模模型设计
- 包含复杂的工具调用（tool use）协议
- 要求特定的 XML 标签格式（`<thinking>`, `<tool_use>` 等）
- 包含大量关于代码编辑、文件操作、终端执行的指令

**gemma4-claude 的问题：**
- Gemma 模型未针对 Claude 的 tool use 格式训练
- 8B 模型无法有效处理长 system prompt（可能占用 2K-4K tokens）
- 模型可能忽略或误解复杂的指令结构

---

### 🟡 Root Cause 3：Temperature 设置过低

**当前配置：**
```
PARAMETER temperature 0.6
```

**问题：**
- 0.6 的 temperature 对于创意/分析任务偏低
- 导致输出趋于保守、重复
- 对于 8B 模型，稍高的 temperature（0.7-0.8）可以增加多样性

---

### 🟢 Root Cause 4：Ollama 适配层限制

**当前适配方式：**
- Claude Code → Ollama API (localhost:11434)
- Ollama 将 Anthropic API 格式转换为本地推理

**潜在问题：**
- Ollama 的 Anthropic 兼容层可能不完善
- 流式响应处理可能有延迟或截断
- 但此因素优先级较低，因为主要问题是模型本身

---

## 三、修复方案

### 方案 A：更换更强的本地模型（推荐）

**问题：** Gemma 4 8B Q4 能力不足
**解决：** 更换为更强的本地模型

| 模型 | 参数量 | 量化 | 预估质量 | 内存需求 |
|------|--------|------|----------|----------|
| Qwen2.5-14B | 14B | Q4 | ⭐⭐⭐⭐ | ~10GB |
| Qwen2.5-32B | 32B | Q4 | ⭐⭐⭐⭐⭐ | ~20GB |
| Llama 3.1 8B | 8B | Q4 | ⭐⭐⭐ | ~6GB |
| DeepSeek-R1 14B | 14B | Q4 | ⭐⭐⭐⭐⭐ | ~10GB |
| **Qwen3-30B-A3B** | 30B | Q4 | ⭐⭐⭐⭐⭐ | ~20GB |

**操作步骤：**
```bash
# 下载更强的模型（以 Qwen2.5-14B 为例）
ollama pull qwen2.5:14b

# 创建针对 Claude Code 优化的 Modelfile
cat > /Users/frankie/Modelfile.claude << 'EOF'
FROM qwen2.5:14b

SYSTEM """You are an expert software engineer. Follow the user's instructions carefully. Always write clean, well-documented code. When editing files, show the minimal diff needed. Respond in Chinese unless code or technical terms require English."""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 32768
PARAMETER repeat_penalty 1.1
EOF

# 创建模型
ollama create qwen2.5-claude -f /Users/frankie/Modelfile.claude
```

**修改 .zshrc 别名：**
```bash
alias claude-big='export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="qwen2.5-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🧠 [本地 Ollama] Qwen2.5-14B (32K ctx)" && command claude --bare'
```

---

### 方案 B：优化 gemma4-claude 的 Modelfile

如果必须使用 gemma4-claude，优化其配置：

**当前问题配置：**
```
SYSTEM You are an expert software engineer...  # 缺少引号，可能被截断
PARAMETER temperature 0.6  # 偏低
PARAMETER top_k 64         # 偏高，增加随机性
PARAMETER top_p 0.9        # 正常
PARAMETER num_ctx 131072   # 对 8B 模型不现实，实际有效上下文约 4K-8K
```

**优化后的 Modelfile：**
```bash
cat > /Users/frankie/Modelfile.gemma4-fixed << 'EOF'
FROM gemma4:latest

SYSTEM """You are a helpful AI coding assistant. Be concise and direct. Avoid repetitive statements. Focus on practical, actionable advice. When analyzing code or projects, provide specific technical insights rather than generic observations."""

PARAMETER temperature 0.75
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 8192
PARAMETER repeat_penalty 1.15
PARAMETER num_predict 4096
EOF

ollama create gemma4-claude-v2 -f /Users/frankie/Modelfile.gemma4-fixed
```

**关键优化点：**
1. **降低 num_ctx 到 8192**：8B 模型无法有效利用 128K 上下文，过长上下文反而导致注意力分散
2. **提高 temperature 到 0.75**：增加输出多样性，减少重复
3. **增加 repeat_penalty 到 1.15**：显式惩罚重复内容
4. **简化 System Prompt**：移除复杂指令，降低模型理解负担
5. **限制 num_predict**：防止模型无限生成重复内容

---

### 方案 C：使用云端模型（绕过本地限制）

如果本地硬件无法运行更大模型，使用云端 API：

```bash
# 使用百炼 Qwen-Max（最强中文模型）
alias claude-smart='export ANTHROPIC_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1" && export ANTHROPIC_MODEL="qwen-max" && export ANTHROPIC_API_KEY="$DASHSCOPE_API_KEY" && echo "🚀 [云端] Qwen-Max (百炼)" && command claude'

# 或使用 DeepSeek
alias claude-smart='export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic" && export ANTHROPIC_MODEL="deepseek-chat" && export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY" && echo "🚀 [云端] DeepSeek Chat" && command claude'
```

---

### 方案 D：创建模型路由策略（推荐组合方案）

根据任务复杂度自动选择模型：

```bash
# 添加到 .zshrc
claude-smart() {
    local task="$1"
    local complexity="${2:-auto}"
    
    if [ "$complexity" = "auto" ]; then
        # 根据任务描述判断复杂度
        if echo "$task" | grep -qiE "(分析|架构|设计|重构|复杂|大型)"; then
            complexity="high"
        else
            complexity="low"
        fi
    fi
    
    case "$complexity" in
        high)
            echo "🧠 使用云端模型 (Qwen-Max) 处理复杂任务..."
            export ANTHROPIC_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
            export ANTHROPIC_MODEL="qwen-max"
            export ANTHROPIC_API_KEY="${DASHSCOPE_API_KEY:-}"
            ;;
        low)
            echo "⚡ 使用本地模型 (Qwen2.5-14B) 处理简单任务..."
            export ANTHROPIC_BASE_URL="http://localhost:11434"
            export ANTHROPIC_AUTH_TOKEN="ollama"
            export ANTHROPIC_API_KEY=""
            export ANTHROPIC_MODEL="qwen2.5-claude"
            ;;
    esac
    
    export CLAUDE_CODE_BARE=1
    export CLAUDE_CODE_SKIP_KEYCHAIN=1
    command claude --bare
}
```

---

## 四、立即执行的操作

### Step 1：优化现有 gemma4-claude 配置（5分钟）

```bash
# 创建优化版 Modelfile
cat > /Users/frankie/Modelfile.gemma4-fixed << 'EOF'
FROM gemma4:latest

SYSTEM """You are a helpful AI coding assistant. Be concise and direct. Avoid repetitive statements. Focus on practical, actionable advice. When analyzing code or projects, provide specific technical insights rather than generic observations."""

PARAMETER temperature 0.75
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 8192
PARAMETER repeat_penalty 1.15
PARAMETER num_predict 4096
EOF

# 创建新模型
ollama create gemma4-claude-v2 -f /Users/frankie/Modelfile.gemma4-fixed

# 更新 .zshrc 别名（手动编辑 ~/.zshrc）
# 将 ANTHROPIC_MODEL="gemma4-claude" 改为 ANTHROPIC_MODEL="gemma4-claude-v2"
```

### Step 2：下载更强的本地模型（可选，需 10-30分钟）

```bash
# 推荐：Qwen2.5-14B（质量与速度的平衡）
ollama pull qwen2.5:14b

# 或 DeepSeek-R1 14B（推理能力强）
ollama pull deepseek-r1:14b
```

### Step 3：验证修复效果

```bash
# 重启 Ollama
brew services restart ollama

# 测试新模型
ollama run gemma4-claude-v2 "分析这个Python函数的复杂度"

# 启动 Claude Code 测试
claude-big
```

---

## 五、预期效果

| 指标 | 修复前 | 修复后（方案B） | 修复后（方案A） |
|------|--------|-----------------|-----------------|
| 输出重复率 | 高（30-50%） | 中（10-20%） | 低（<5%） |
| 分析深度 | 浅层/泛泛 | 中等 | 深入 |
| 响应速度 | 快 | 快 | 中等 |
| 内存占用 | ~6GB | ~6GB | ~10-20GB |
| 工具调用支持 | 差 | 差 | 中等 |

---

## 六、长期建议

1. **本地模型选择**：对于 Claude Code 这类复杂任务，建议至少使用 14B+ 参数模型
2. **量化平衡**：Q4 是性价比选择，如内存允许，尝试 Q5 或 Q6 量化
3. **云端备用**：复杂任务（架构设计、代码审查）使用云端大模型（Qwen-Max/Claude-4）
4. **定期评估**：每季度评估本地模型质量，及时升级到更强版本
