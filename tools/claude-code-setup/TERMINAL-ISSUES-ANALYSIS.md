# 5 个终端问题深度分析

> 分析时间：2026-04-24
> 分析范围：.zshrc 配置、Ollama 设置、Claude Code 别名、API 密钥、MCP/Skill 配置

---

## 问题 1：终端无法找到 `qwen2.5-claude` 命令

### 现象
```bash
frankie@Mac-mini ~ % qwen2.5-claude
zsh: command not found: qwen2.5-claude
```

### 根因
**`qwen2.5-claude` 是 Ollama 模型名称，不是 shell 可执行命令！**

用户混淆了"模型名称"和"启动命令"：
- `qwen2.5-claude` → Ollama 内部模型标识（类似 Docker image name）
- `claude-big` / `claude-small` → 启动 Claude Code 的 shell 别名

### 修复方案
必须通过别名启动，别名内部会设置 `ANTHROPIC_MODEL="qwen2.5-claude"`：

```bash
# ✅ 正确
claude-big
claude-small
claude-v2

# ❌ 错误
qwen2.5-claude  # 这不是命令！
```

---

## 问题 2：`claude-big` 仍使用旧模型 `gemma4-claude`

### 现象
启动后显示 `gemma4-claude · API Usage Billing`，而非新的 `qwen2.5-claude`

### 根因
`.zshrc` 第 227-228 行硬编码了旧模型：

```bash
# .zshrc 第 227-228 行（当前错误配置）
alias claude-small='... ANTHROPIC_MODEL="gemma4-claude" ...'
alias claude-big='... ANTHROPIC_MODEL="gemma4-claude" ...'
```

### 修复方案
编辑 `~/.zshrc`，将 `"gemma4-claude"` 改为 `"qwen2.5-claude"`：

```bash
# 第 227 行
alias claude-small='export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="qwen2.5-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🚀 [本地 Ollama] Qwen2.5-14B (32K ctx)" && command claude --bare'

# 第 228 行
alias claude-big='export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="qwen2.5-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🧠 [本地 Ollama] Qwen2.5-14B (32K ctx)" && command claude --bare'
```

然后运行 `source ~/.zshrc` 生效。

---

## 问题 3：`claude-dual-model-v2.sh` 命令找不到

### 现象
```bash
frankie@Mac-mini ~ % claude-dual-model-v2.sh
zsh: command not found: claude-dual-model-v2.sh
```

### 根因
1. 文件没有添加到 PATH 环境变量
2. 没有为其创建 alias
3. 用户直接输入文件名，但文件不在 PATH 中

### 修复方案
**方案 A：创建 alias（推荐）**

在 `~/.zshrc` 中添加：
```bash
alias claude-v2='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh'
alias claude-smart='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh'
```

**方案 B：添加到 PATH**
```bash
export PATH="/Users/frankie/claude-code-setup:$PATH"
```

---

## 问题 4：GitHub 访问失败（"我无法直接访问外部网站"）

### 现象
在 Claude Code 中输入"去 GitHub 分析 Claude-mem 项目"，模型回复无法访问外部网站。

### 根因分析

#### 4.1 模型能力问题（主因）
- 当前使用的是 `gemma4-claude`（8B Q4）模型
- 8B 模型**不会主动使用工具**（WebFetch）
- 模型缺乏复杂任务规划能力，无法分解"访问 GitHub → 获取内容 → 分析"的步骤

#### 4.2 MCP Server 配置问题（次因）
虽然 `ai-tools` MCP Server 已配置，但：
- 需要确认 MCP Server 进程是否在运行
- Claude Code 是否正确加载了 MCP tools

#### 4.3 正确的工作流程
Claude Code **本身不能浏览网页**，正确流程是：

```bash
# 方法 1：先克隆到本地，再分析
git clone https://github.com/xxx/Claude-mem.git ~/Claude-mem
claude-big
# 然后输入：分析 ~/Claude-mem 项目的架构

# 方法 2：使用 WebFetch 工具（需要模型支持工具调用）
# 在 Claude Code 中输入：
# "使用 WebFetch 工具获取 https://github.com/xxx/Claude-mem 的 README"
```

### 修复方案

**步骤 1：升级到 Qwen2.5-14B（会主动使用工具）**
```bash
# 确认模型已安装
ollama list | grep qwen2.5-claude

# 更新 .zshrc 别名指向新模型（见问题 2）
```

**步骤 2：验证 MCP Server 运行状态**
```bash
# 检查 ai-tools MCP Server 是否可执行
python3 /Users/frankie/claude-code-setup/stage1/mcp-servers/ai-tools-server.py --help

# 检查 Claude Code 是否正确加载 MCP
# 在 Claude Code 中输入：你有什么工具可用？
```

**步骤 3：使用正确的 GitHub 分析流程**
```bash
# 手动克隆项目
git clone https://github.com/xxx/Claude-mem.git

# 在 Claude Code 中分析本地代码
claude-big
# 输入：分析 Claude-mem 项目的架构和功能
```

---

## 问题 5：Ollama 配置与模型加载问题

### 现象
Ollama 配置复杂，用户不清楚当前加载的是哪个模型，以及如何切换。

### 根因
`.zshrc` 中有大量 Ollama 环境变量，但缺乏清晰的文档和快捷命令。

### 当前配置分析

```bash
# Ollama M4 优化配置（.zshrc 第 10-20 行）
export OLLAMA_HOST="0.0.0.0:11434"        # 允许本地所有服务访问
export OLLAMA_ORIGINS="*"                  # 允许浏览器插件跨域
export OLLAMA_MAX_LOADED_MODELS=1          # M4 24G 只能稳定跑 1 个大模型
export OLLAMA_NUM_PARALLEL=2               # 最多 2 个并发请求
export OLLAMA_MAX_VRAM=6000000000          # 限制 6GB VRAM
export OLLAMA_MODELS="/Volumes/1TB-M2/ollama-models"  # 模型存储在外置硬盘
export OLLAMA_DEBUG=1                      # 开启日志
export OLLAMA_KEEP_ALIVE="-1"              # 模型常驻内存
```

**关键限制**：
- `OLLAMA_MAX_LOADED_MODELS=1`：只能同时加载 1 个模型
- `OLLAMA_KEEP_ALIVE="-1"`：模型常驻内存，切换模型需要手动卸载

### 修复方案

**添加模型管理别名：**

```bash
# 添加到 ~/.zshrc

# 查看当前运行的模型
alias ollama-current='echo "当前模型: $(ollama ps | grep -v NAME | awk '"'"'{print $1}'"'"')"'

# 切换到 Qwen2.5-14B
alias ollama-qwen='ollama run qwen2.5-claude'

# 切换到 Gemma 4
alias ollama-gemma='ollama run gemma4-claude'

# 停止所有模型（释放内存）
alias ollama-stop='ollama stop qwen2.5-claude 2>/dev/null; ollama stop gemma4-claude 2>/dev/null; echo "所有模型已停止"'

# 查看模型详情
alias ollama-info='ollama list'
```

---

## 综合修复清单

### 必须立即修复（高优先级）

| # | 问题 | 操作 | 验证 |
|---|------|------|------|
| 1 | claude-big 指向旧模型 | 编辑 ~/.zshrc 第 228 行 | 运行 `claude-big` 应显示 "Qwen2.5-14B" |
| 2 | claude-small 指向旧模型 | 编辑 ~/.zshrc 第 227 行 | 运行 `claude-small` 应显示 "Qwen2.5-14B" |
| 3 | 缺少 claude-v2 别名 | 在 ~/.zshrc 添加 alias | 运行 `claude-v2` 应启动智能路由 |

### 建议修复（中优先级）

| # | 问题 | 操作 | 验证 |
|---|------|------|------|
| 4 | GitHub 访问流程不清 | 使用 git clone + 本地分析 | 能成功分析 GitHub 项目 |
| 5 | Ollama 模型切换不便 | 添加 ollama-* 别名 | `ollama-current` 显示当前模型 |
| 6 | MCP Server 状态不明 | 检查 ai-tools-server.py 运行状态 | Claude Code 能列出可用工具 |

---

## 修复后的 ~/.zshrc 关键段落

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

---

## 验证步骤

修复后，依次运行以下命令验证：

```bash
# 1. 使配置生效
source ~/.zshrc

# 2. 验证模型切换
ollama-current          # 应显示当前模型

# 3. 验证新别名
claude-big              # 应显示 "Qwen2.5-14B"
# 在 Claude Code 中输入：
# "使用 WebFetch 获取 https://github.com/anthropics/claude-code 的信息"

# 4. 验证智能路由
claude-v2               # 应显示智能路由菜单

# 5. 验证云端别名
claude-max              # 应启动百炼 Qwen-Max
```
