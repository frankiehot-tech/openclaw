# Claude Code 别名使用指南

## 问题诊断

您输入 `qwen2.5-claude` 报错 `command not found`，原因是：

**`qwen2.5-claude` 是 Ollama 模型名称，不是 shell 命令！**

正确的使用方式是通过 `claude-big`、`claude-small` 等别名来启动 Claude Code，这些别名内部会设置 `ANTHROPIC_MODEL="qwen2.5-claude"`。

---

## 当前别名状态（需要更新）

您的 `~/.zshrc` 中第 227-228 行仍然指向旧模型：

```bash
# ❌ 当前配置（错误）
alias claude-small='... ANTHROPIC_MODEL="gemma4-claude" ...'
alias claude-big='... ANTHROPIC_MODEL="gemma4-claude" ...'
```

---

## 修复步骤

### Step 1: 编辑 ~/.zshrc

```bash
nano ~/.zshrc
```

### Step 2: 找到第 227-228 行，替换为：

```bash
# ==================== Ollama 本地模型快捷别名 ====================
alias claude-local='/Users/frankie/claude-code-setup/claude-dual-model.sh local'
alias claude-ollama='/Users/frankie/claude-code-setup/claude-dual-model.sh local'

# 轻量任务 - 使用 Qwen2.5-14B 本地模型
alias claude-small='export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="qwen2.5-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🚀 [本地 Ollama] Qwen2.5-14B (32K ctx)" && command claude --bare'

# 大型任务 - 使用 Qwen2.5-14B 本地模型（同 small，提示语不同）
alias claude-big='export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="qwen2.5-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🧠 [本地 Ollama] Qwen2.5-14B (32K ctx)" && command claude --bare'

# 智能路由 - 自动选择本地或云端
alias claude-v2='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh'

# 云端模型别名
alias claude-cloud='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh cloud'
alias claude-deepseek='/Users/frankie/claude-code-setup/claude-dual-model.sh 1'
alias claude-backup='/Users/frankie/claude-code-setup/claude-dual-model.sh 2'
alias claude-qwen='/Users/frankie/claude-code-setup/claude-dual-model.sh 3'
alias claude-max='/Users/frankie/claude-code-setup/claude-dual-model.sh 5'

# 状态检查
alias ollama-status='ollama ps && echo "---" && echo "Active: $ANTHROPIC_MODEL"'
# ==================== Ollama 别名结束 ====================
```

### Step 3: 保存并生效

```bash
# 保存文件后，运行：
source ~/.zshrc
```

---

## 别名使用速查表

| 别名 | 功能 | 模型 | 成本 |
|------|------|------|------|
| `claude` | 主入口（自动路由） | 根据配置 | - |
| `claude-big` | 本地大模型 | Qwen2.5-14B | 免费 |
| `claude-small` | 本地轻量 | Qwen2.5-14B | 免费 |
| `claude-v2` | 智能路由 v2 | 自动选择 | - |
| `claude-cloud` | 强制云端 | Qwen-Max | 按量计费 |
| `claude-deepseek` | DeepSeek Chat | deepseek-chat | 按量计费 |
| `claude-backup` | DeepSeek Reasoner | deepseek-reasoner | 按量计费 |
| `claude-qwen` | 百炼 Qwen | qwen-plus | 按量计费 |
| `claude-max` | 百炼最强 | qwen-max | 按量计费 |
| `adapter-start` | 启动适配器 | - | - |
| `adapter-status` | 检查适配器 | - | - |
| `ollama-status` | 检查 Ollama | - | - |

---

## 使用示例

```bash
# 1. 启动本地模型（推荐日常使用）
claude-big

# 2. 启动智能路由（自动选择本地/云端）
claude-v2

# 3. 强制使用云端模型（复杂任务）
claude-cloud
# 或
claude-max

# 4. 检查当前运行的模型
ollama-status

# 5. 检查适配器状态
adapter-status
```

---

## 常见问题

### Q: 为什么 `qwen2.5-claude` 命令找不到？
A: 这是 Ollama 模型名称，不是 shell 命令。需要通过 `claude-big` 或 `claude-small` 别名来使用。

### Q: 如何直接测试模型？
A: 使用 Ollama 命令：
```bash
ollama run qwen2.5-claude "你的问题"
```

### Q: 如何切换回旧模型？
A: 修改 `~/.zshrc` 中的 `ANTHROPIC_MODEL` 为 `gemma4-claude`，然后 `source ~/.zshrc`。

### Q: claude-v2 和 claude 有什么区别？
A: 
- `claude`：原始脚本，手动选择模式（1-5）
- `claude-v2`：智能路由，自动根据任务复杂度选择本地或云端
