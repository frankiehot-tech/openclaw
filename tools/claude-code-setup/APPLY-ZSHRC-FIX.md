# ~/.zshrc 修复指南

由于安全限制，我无法直接编辑您主目录下的 `~/.zshrc` 文件。请按照以下步骤手动修复：

---

## 修复内容

### 1. 修复 `claude-big` 和 `claude-small` 别名（指向新模型）
### 2. 添加 `claude-v2` 智能路由别名
### 3. 添加 Ollama 模型管理别名

---

## 操作步骤

### Step 1: 打开 ~/.zshrc

```bash
nano ~/.zshrc
```

### Step 2: 找到第 224-231 行

找到以下内容：
```bash
# ==================== Ollama 本地模型快捷别名 ====================
alias claude-local='/Users/frankie/claude-code-setup/claude-dual-model.sh local'
alias claude-ollama='/Users/frankie/claude-code-setup/claude-dual-model.sh local'
alias claude-small='export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="gemma4-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🚀 Gemma 4 E4B (128K ctx)" && command claude --bare'
alias claude-big='export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="gemma4-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🧠 Gemma 4 E4B (本地大模型)" && command claude --bare'
alias claude-ollama-big='/Users/frankie/claude-code-setup/claude-dual-model.sh local-big'
alias ollama-status='ollama ps && echo "---" && echo "Active: $ANTHROPIC_MODEL"'
# ==================== Ollama 别名结束 ====================
```

### Step 3: 替换为以下内容

```bash
# ==================== Ollama 本地模型快捷别名 ====================
alias claude-local='/Users/frankie/claude-code-setup/claude-dual-model.sh local'
alias claude-ollama='/Users/frankie/claude-code-setup/claude-dual-model.sh local'

# 轻量任务 - 使用 Qwen2.5-14B 本地模型（已修复）
alias claude-small='export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="qwen2.5-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🚀 [本地 Ollama] Qwen2.5-14B (32K ctx)" && command claude --bare'

# 大型任务 - 使用 Qwen2.5-14B 本地模型（已修复）
alias claude-big='export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="qwen2.5-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🧠 [本地 Ollama] Qwen2.5-14B (32K ctx)" && command claude --bare'

# 智能路由 v2（新增）
alias claude-v2='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh'
alias claude-smart='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh'

# Ollama 模型管理（新增）
alias ollama-current='echo "当前模型: $(ollama ps | grep -v NAME | awk '"'"'{print $1}'"'"')"'
alias ollama-qwen='ollama run qwen2.5-claude'
alias ollama-gemma='ollama run gemma4-claude'
alias ollama-stop='ollama stop qwen2.5-claude 2>/dev/null; ollama stop gemma4-claude 2>/dev/null; echo "所有模型已停止"'
alias ollama-info='ollama list'

alias claude-ollama-big='/Users/frankie/claude-code-setup/claude-dual-model.sh local-big'
alias ollama-status='ollama ps && echo "---" && echo "Active: $ANTHROPIC_MODEL"'
# ==================== Ollama 别名结束 ====================
```

### Step 4: 保存并退出

- 按 `Ctrl+O` 保存
- 按 `Enter` 确认
- 按 `Ctrl+X` 退出

### Step 5: 使配置生效

```bash
source ~/.zshrc
```

---

## 验证修复

```bash
# 1. 验证 claude-big 使用新模型
claude-big
# 应显示：🧠 [本地 Ollama] Qwen2.5-14B (32K ctx)

# 2. 验证 claude-v2 别名
claude-v2
# 应显示智能路由菜单

# 3. 验证 Ollama 管理
ollama-current
# 应显示当前运行的模型
```

---

## 一键修复脚本（备用方案）

如果您熟悉命令行，可以运行以下脚本自动修复：

```bash
# 下载修复脚本
curl -o /tmp/fix-zshrc.sh https://raw.githubusercontent.com/your-repo/fix-zshrc.sh

# 或者手动创建修复脚本
cat > /tmp/fix-zshrc.sh << 'SCRIPT'
#!/bin/bash
# 备份原文件
cp ~/.zshrc ~/.zshrc.backup.$(date +%Y%m%d_%H%M%S)

# 使用 sed 替换关键行
sed -i '' 's/ANTHROPIC_MODEL="gemma4-claude"/ANTHROPIC_MODEL="qwen2.5-claude"/g' ~/.zshrc
sed -i '' 's/echo "🚀 Gemma 4 E4B (128K ctx)"/echo "🚀 [本地 Ollama] Qwen2.5-14B (32K ctx)"/g' ~/.zshrc
sed -i '' 's/echo "🧠 Gemma 4 E4B (本地大模型)"/echo "🧠 [本地 Ollama] Qwen2.5-14B (32K ctx)"/g' ~/.zshrc

echo "✅ ~/.zshrc 已修复"
echo "请运行: source ~/.zshrc"
SCRIPT

chmod +x /tmp/fix-zshrc.sh
/tmp/fix-zshrc.sh
```

---

## 修复对比

| 别名 | 修复前 | 修复后 |
|------|--------|--------|
| `claude-big` | gemma4-claude (8B) | **qwen2.5-claude (14B)** |
| `claude-small` | gemma4-claude (8B) | **qwen2.5-claude (14B)** |
| `claude-v2` | 不存在 | **智能路由** |
| `ollama-current` | 不存在 | **显示当前模型** |
| `ollama-stop` | 不存在 | **停止所有模型** |
