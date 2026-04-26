# 3 个问题深度分析

> 分析时间：2026-04-24
> 问题：
> 1. claude-big 无法访问 GitHub
> 2. claude-v2 没有输出
> 3. claude-cloud 命令不存在

---

## 问题 1：claude-big 无法访问 GitHub

### 现象
用户输入："去 GitHub 看一下 Claude-mem 这个项目"
模型回复：
- "似乎在当前目录下没有找到名为 claude-mem 的 GitHub 项目的本地文件"
- "我可以尝试通过浏览器导航到此项目页面来获取更多信息"
- "请告诉我是否需要我为您打开它？"

### 根因分析

#### 1.1 模型不会使用 WebFetch 工具
- Qwen2.5-14B 模型**没有针对 Claude Code 的工具调用训练**
- 模型不知道可以调用 `web_fetch` 工具获取网页内容
- 它把"去 GitHub 看"理解为"在本地文件系统查找"

#### 1.2 Claude Code 的 System Prompt 问题
Claude Code 启动时会发送一个复杂的 System Prompt，其中包含：
```
你可以使用以下工具：
- web_fetch: 获取网页内容
- bash: 执行命令
- read_file: 读取文件
...
```

**但 Qwen 模型**：
- 不理解 Claude 特定的工具格式
- 无法正确解析 `<tool_use>` 标签
- 不知道何时应该调用工具

#### 1.3 正确的 GitHub 访问方式
Claude Code 本身**不能直接浏览网页**，需要通过：
1. **WebFetch 工具**（模型需要主动调用）
2. **Bash 工具**（执行 curl/git clone）
3. **用户手动提供内容**

### 修复方案

**方案 A：手动克隆后分析（最可靠）**
```bash
# 1. 手动克隆项目
git clone https://github.com/xxx/Claude-mem.git ~/Claude-mem

# 2. 启动 Claude Code
claude-big

# 3. 在 Claude Code 中输入：
# "分析 ~/Claude-mem 项目的架构和功能"
```

**方案 B：使用 Bash 工具获取信息**
```bash
# 在 Claude Code 中输入：
# "使用 Bash 工具执行：curl -s https://api.github.com/repos/xxx/Claude-mem"
```

**方案 C：配置 MCP Server 的 WebFetch（需要模型支持）**
当前 Qwen2.5-14B 不支持，需要：
- 使用 Claude 官方模型（原生支持工具）
- 或使用经过工具调用训练的模型

---

## 问题 2：claude-v2 没有输出

### 现象
用户输入 `claude-v2`，终端没有任何输出。

### 根因分析

#### 2.1 检查 alias 配置
```bash
# ~/.zshrc 第 234 行
alias claude-v2="/Users/frankie/claude-code-setup/claude-dual-model-v2.sh auto"
```

配置看起来正确，但可能的问题：

#### 2.2 脚本执行问题
`claude-dual-model-v2.sh` 脚本逻辑：
```bash
choice="${1:-auto}"
shift 2>/dev/null || true

case "$choice" in
    auto|*)
        setup_smart_route "$*"
        ;;
esac
```

**问题**：`setup_smart_route` 函数需要用户输入作为参数，但直接运行 `claude-v2` 时没有输入内容。

```bash
setup_smart_route() {
    local user_input="${1:-}"
    local complexity=$(analyze_complexity "$user_input")
    # ...
}
```

当 `user_input` 为空时，`analyze_complexity` 返回 "light"，然后启动本地模型。

**但为什么没有任何输出？**

可能原因：
1. 脚本被挂起，等待输入
2. 输出被重定向或缓冲
3. 脚本执行出错但错误被抑制

#### 2.3 验证方法
```bash
# 测试 1：直接运行脚本，查看输出
bash -x /Users/frankie/claude-code-setup/claude-dual-model-v2.sh auto

# 测试 2：检查脚本是否有执行权限
ls -la /Users/frankie/claude-code-setup/claude-dual-model-v2.sh

# 测试 3：手动执行函数
source /Users/frankie/claude-code-setup/claude-dual-model-v2.sh
setup_smart_route "测试任务"
```

### 修复方案

**修复 1：添加默认行为（无输入时提示）**
```bash
# 在脚本开头添加
if [ -z "$1" ]; then
    echo "=========================================="
    echo "  Claude Code - 智能模型路由系统 v2"
    echo "=========================================="
    echo ""
    echo "用法:"
    echo "  claude-v2 local    # 强制本地模式"
    echo "  claude-v2 cloud    # 强制云端模式"
    echo "  claude-v2 auto     # 自动选择（默认）"
    echo ""
    echo "请输入任务描述，或选择模式："
    read -r user_input
    set -- "auto" "$user_input"
fi
```

**修复 2：简化启动流程**
```bash
# 修改 claude-v2 alias，直接启动交互式选择
alias claude-v2='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh interactive'
```

---

## 问题 3：claude-cloud 命令不存在

### 现象
```bash
frankie@Mac-mini ~ % claude-cloud
zsh: command not found: claude-cloud
```

### 根因分析

检查 `~/.zshrc`，发现：
```bash
# 只有这些 alias
alias claude-v2="..."
alias claude-smart="..."

# 没有 claude-cloud alias！
```

**问题**：之前计划添加 `claude-cloud` alias，但实际没有添加到 `.zshrc`。

### 修复方案

在 `~/.zshrc` 中添加：
```bash
# 强制云端模式
alias claude-cloud='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh cloud'
alias claude-deepseek='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh 1'
alias claude-backup='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh 2'
alias claude-qwen='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh 3'
alias claude-max='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh 5'
```

---

## 综合修复步骤

### Step 1：修复 ~/.zshrc

```bash
# 编辑 ~/.zshrc
nano ~/.zshrc
```

找到第 233-243 行，替换为：
```bash
# ==================== 智能路由 v2（新增）====================
alias claude-v2='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh'
alias claude-smart='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh'

# 强制云端模式（新增）
alias claude-cloud='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh cloud'
alias claude-deepseek='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh 1'
alias claude-backup='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh 2'
alias claude-qwen='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh 3'
alias claude-max='/Users/frankie/claude-code-setup/claude-dual-model-v2.sh 5'

# Ollama 模型管理（新增）
alias ollama-current='echo "当前模型: $(ollama ps | grep -v NAME | awk '"'"'{print $1}'"'"')"'
alias ollama-qwen='ollama run qwen2.5-claude'
alias ollama-gemma='ollama run gemma4-claude'
alias ollama-stop='ollama stop qwen2.5-claude 2>/dev/null; ollama stop gemma4-claude 2>/dev/null; echo "所有模型已停止"'
alias ollama-info='ollama list'
# ==================== 新增别名结束 ====================
```

### Step 2：修复 claude-dual-model-v2.sh

```bash
# 在脚本开头添加交互式提示
choice="${1:-}"

# 如果没有参数，显示交互式菜单
if [ -z "$choice" ]; then
    echo "=========================================="
    echo "  Claude Code - 智能模型路由系统 v2"
    echo "=========================================="
    echo ""
    echo "请选择模式:"
    echo "  1. local  - 本地模型 (Qwen2.5-14B)"
    echo "  2. cloud  - 云端模型 (Qwen-Max)"
    echo "  3. auto   - 自动选择"
    echo ""
    read -r choice
fi

shift 2>/dev/null || true
```

### Step 3：使配置生效

```bash
source ~/.zshrc
```

---

## 验证修复

```bash
# 1. 验证 claude-v2（交互式）
claude-v2
# 应显示菜单，等待用户选择

# 2. 验证 claude-cloud
claude-cloud
# 应显示：🎯 云端: Qwen-Max (百炼)

# 3. 验证 GitHub 访问（手动方式）
git clone https://github.com/anthropics/claude-code.git /tmp/claude-code
claude-big
# 输入：分析 /tmp/claude-code 项目的架构
```
