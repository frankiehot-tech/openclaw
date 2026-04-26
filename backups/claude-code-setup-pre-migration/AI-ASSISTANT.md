# AI Assistant 项目配置

<!-- 由专家知识库配置脚本生成于 $(date) -->

## 专家知识库集成

### 可用技能
- **优化工作流**: `/optimized-workflow` - 智能任务评估和并行处理
- **MCP 优化**: `/mcp-optimizer` - MCP 服务器配置和故障排查
- **快速帮助**: `/cc-help` - 查询最佳实践和技巧

### 知识库位置
`~/.claude/skills/cc-expert/knowledge.md`

## 核心工作流原则

### 1. MCP 优先原则
- 优先使用 MCP 服务器而非 shell 命令
- 核心 MCP: filesystem, github, playwright

### 2. 智能任务评估
- **简单任务** (<5分钟): 直接执行
- **中等任务** (5-30分钟): 使用 Plan 模式
- **复杂任务** (>30分钟): 创建子代理并行处理

### 3. 安全并行处理
- 使用 `git worktree` 创建物理隔离工作区
- 避免多个会话访问相同文件
- 每个并行任务使用独立分支

### 4. 质量门禁
- 代码自动审查
- 安全检查
- 性能测试

## 配置说明

### 全局配置位置
- `~/.claude/settings.json` - 全局设置
- `~/.claude/settings.local.json` - 本地覆盖

### 技能目录
- `~/.claude/skills/` - 自定义技能
- `~/.claude/commands/` - 快速命令

## 故障排查

### 常见问题
1. **MCP 连接失败**: 检查网络和环境变量
2. **会话冲突**: 使用 git worktree 隔离
3. **权限问题**: 检查 ~/.claude/ 目录权限
4. **环境变量传递问题**: 在`.zshrc`中设置的环境变量可能不传递到bash子进程

### 环境变量解决方案
**重要**: 需要在你的终端（不是AI Assistant的Bash工具）中运行这些命令，以使环境变量在shell会话中持久化。

```bash
# 最佳方案: 在终端中设置所有环境变量（使它们在当前shell会话中持久化）
eval "$(/Users/frankie/claude-code-setup/init-claude-env.sh --export)"

# 验证环境变量已设置
echo "GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}..."

# 验证GitHub连接
/Users/frankie/claude-code-setup/github-tools/github-diagnose.sh

# 验证百炼平台连接
/Users/frankie/claude-code-setup/dashscope-maintenance.sh --report
```

**替代方案**: 如果无法在终端中运行，可以在运行任何GitHub工具前先设置环境变量：
```bash
# 方法1: 一次性设置并运行诊断
eval "$(/Users/frankie/claude-code-setup/init-claude-env.sh --export)" && /Users/frankie/claude-code-setup/github-tools/github-diagnose.sh

# 方法2: 使用claude-init别名（需先source ~/.zshrc）
claude-init && /Users/frankie/claude-code-setup/github-tools/github-diagnose.sh
```

### 调试命令
```bash
# 检查 MCP 状态
claude mcp list

# 查看会话
ls -la ~/.claude/sessions/

# 检查配置
cat ~/.claude/settings.json

# 检查环境变量
echo "GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}..."
echo "DASHSCOPE_API_KEY: ${DASHSCOPE_API_KEY:0:10}..."
```

## 最佳实践

### 会话管理
- 不同任务使用不同工作目录
- 长时间运行任务使用 nohup
- 定期清理旧会话文件

### 性能优化
- 启用 fast mode 提高响应速度
- 使用缓存减少重复计算
- 合理设置并行度

## 上下文管理策略

### 自动压缩配置
已通过环境变量配置自动压缩：
- `AI_AUTOCOMPACT_PCT_OVERRIDE=60` - 60% 使用率时自动压缩
- `AI_AUTO_COMPACT_WINDOW=120000` - 限制压缩窗口大小

### 压缩指令
当进行上下文压缩时，始终保留：
- 修改过的文件列表
- 测试命令及其结果
- API 设计决策
- 安全相关变更
- 当前任务进度

### 使用习惯
1. **每45-60分钟**或**完成一个主要任务**后运行 `/compact`
2. **切换任务**时运行 `/clear`
3. **随时**用 `/context` 检查上下文使用情况
4. **临时查询**用 `/btw` 避免污染上下文历史

### 最佳实践
- 遵循 **60% 规则**：在上下文使用率达到60%时主动压缩
- 使用 **`Esc + Esc` 或 `/rewind`** 回退到检查点
- **避免代理"笨区"**：手动控制压缩时机，不要等到90%+

---

*此文件由 AI Assistant 专家知识库配置脚本自动生成*
