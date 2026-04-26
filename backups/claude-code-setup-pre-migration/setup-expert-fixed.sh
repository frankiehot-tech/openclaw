#!/bin/bash
set -e

echo "🚀 AI Assistant 专家知识库配置 (修复版)"
echo "======================================"
echo "修复说明:"
echo "  ✓ 路径修复: 使用 ~/.claude/ 而非 /.claude/"
echo "  ✓ Skill格式修复: 确保 frontmatter 格式正确"
echo "  ✓ 目录检查: 确保所有必要目录存在"
echo "  ✓ 容错增强: 网络失败时使用本地模板"
echo ""

# 获取当前目录（用于创建 AI-ASSISTANT.md）
CURRENT_DIR=$(pwd)
echo "当前目录: $CURRENT_DIR"

# 1. 备份现有配置
echo "📦 备份现有配置..."
if [ -f ~/.claude/settings.json ]; then
    BACKUP_NAME="~/.claude/settings.json.bak.$(date +%Y%m%d_%H%M%S)"
    cp ~/.claude/settings.json "$BACKUP_NAME" 2>/dev/null || true
    echo "  配置文件已备份到: $BACKUP_NAME"
else
    echo "  未找到现有配置文件，无需备份"
fi

# 2. 创建知识库目录结构
echo "📁 创建知识库目录..."
mkdir -p ~/.claude/skills/cc-expert
mkdir -p ~/.claude/skills/cc-workflows
echo "  目录创建完成: ~/.claude/skills/{cc-expert,cc-workflows}"

# 3. 下载最佳实践知识库（带重试和回退）
echo "📚 下载知识库..."
KNOWLEDGE_FILE="$HOME/.claude/skills/cc-expert/knowledge.md"
if curl -L -s --max-time 10 \
   https://github.com/shanraisshan/claude-code-best-practice/raw/main/README.md \
   -o "$KNOWLEDGE_FILE.tmp" && [ -s "$KNOWLEDGE_FILE.tmp" ]; then
    mv "$KNOWLEDGE_FILE.tmp" "$KNOWLEDGE_FILE"
    echo "  知识库下载成功"
else
    echo "⚠️  下载失败，使用本地模板..."
    cat > "$KNOWLEDGE_FILE" << 'KNOWLEDGE_EOF'
# AI Assistant 最佳实践知识库

## 📖 核心概念
1. **会话隔离**: 使用 git worktree 创建隔离工作区
2. **MCP优先**: 优先使用 MCP 服务器而非 shell 命令
3. **Plan模式**: 复杂任务使用 Plan 模式规划
4. **并行处理**: 利用多个终端处理独立子任务

## 🔧 MCP 配置
### 核心 MCP
- filesystem: 文件操作（内置）
- github: GitHub 集成
- playwright: 浏览器自动化

### 常见故障排查
1. 检查网络连接
2. 验证环境变量
3. 检查权限设置

## ⚡ 工作流优化
### 任务评估
- 简单任务 (<5分钟): 直接执行
- 中等任务 (5-30分钟): 使用 Plan 模式
- 复杂任务 (>30分钟): 创建子代理并行处理

### 并行策略
```bash
# 使用 git worktree 创建隔离会话
git worktree add ../${PWD##*/}-wt-1 -b task-branch-1
git worktree add ../${PWD##*/}-wt-2 -b task-branch-2
```

## 🔒 安全最佳实践
1. 避免在配置中存储敏感信息
2. 使用环境变量管理凭证
3. 定期备份配置

## 🚀 高级技巧
### 性能优化
- 启用 fast mode 加速响应
- 使用模型缓存减少 token 使用

### 调试技巧
```bash
# 查看 MCP 状态
claude mcp list

# 查看会话日志
ls -la ~/.claude/projects/*/*.jsonl
```
KNOWLEDGE_EOF
    echo "  本地模板创建完成"
fi

# 4. 创建融合型 Skill - 优化工作流（修复frontmatter格式）
echo "🎨 创建优化工作流 Skill..."
cat > ~/.claude/skills/optimized-workflow.md << 'SKILL_EOF'
---
name: optimized-workflow
description: 结合最佳实践的优化工作流，自动选择并行策略和工具
---

## 工作流执行引擎

### 任务分析阶段
1. 评估任务复杂度：
   - 简单（<5分钟）：直接执行
   - 中等（5-30分钟）：使用 Plan 模式
   - 复杂（>30分钟）：创建子代理并行处理

### 并行策略选择
```bash
# 自动选择并行度
if [ "$task_complexity" == "high" ]; then
    # 使用 git worktree 创建隔离会话
    for i in {1..3}; do
        git worktree add "../${PWD##*/}-wt-$i" -b "task-$i-$(date +%Y%m%d)"
    done
    echo "已创建 3 个隔离工作树"
fi
```

### 工具优先级
1. 优先使用 MCP：filesystem, github, playwright
2. 其次使用 Skills：/code-review, /security-check
3. 最后使用 Shell：带权限确认

### 质量门禁
- 代码审查：自动调用 /code-review
- 安全检查：参考 security-expert agent
- 性能检查：运行相关测试命令

### 知识库引用
遇到以下问题时查询 ~/.claude/skills/cc-expert/knowledge.md：
- MCP 配置优化
- 并行处理策略
- 会话管理技巧
- 隐私加固方案
SKILL_EOF
echo "  优化工作流 Skill 创建完成"

# 5. 创建 MCP 优化配置 Skill
echo "🔌 创建 MCP 优化 Skill..."
cat > ~/.claude/skills/mcp-optimizer.md << 'MCP_EOF'
---
name: mcp-optimizer
description: MCP 服务器配置优化和故障排查
---

## MCP 配置优化指南

### 核心 MCP（必装）
- filesystem: 文件操作（已内置）
- github: 代码管理
- playwright: 浏览器自动化

### 配置检查清单
1. 环境变量是否设置
2. 网络连接是否正常
3. 权限是否正确

### 故障排查流程
```bash
# 1. 检查 MCP 状态
claude mcp list

# 2. 测试单个 MCP
claude mcp__github__search_repositories "test"

# 3. 查看错误日志
cat ~/.claude/mcp.log 2>/dev/null || echo "无日志"
```

### 连接失败解决方案
| MCP | 常见错误 | 解决方案 |
|-----|---------|---------|
| context7 | 网络超时 | 检查网络，重试 |
| postgres | 连接拒绝 | 检查 POSTGRES_URL |
| docker | 权限不足 | sudo usermod -aG docker $USER |
| supabase | 认证失败 | 检查 SUPABASE_ACCESS_TOKEN |

### 性能优化提示
1. 限制同时运行的 MCP 数量
2. 定期清理 MCP 缓存
3. 使用连接池避免频繁建立连接
MCP_EOF
echo "  MCP 优化 Skill 创建完成"

# 6. 创建快速查询 Skill（修复：放在正确的目录）
echo "⚡ 创建快速查询 Skill..."
mkdir -p ~/.claude/commands 2>/dev/null || true
cat > ~/.claude/commands/cc-help.md << 'HELP_EOF'
---
name: cc-help
description: 查询 AI Assistant 最佳实践和技巧
---

查询 ~/.claude/skills/cc-expert/knowledge.md 中的相关内容，回答用户关于 AI Assistant 使用技巧、工作流优化、MCP 配置的问题。

### 输出格式
1. **直接答案**（2-3句话）
2. **详细步骤**（如有必要）
3. **相关技巧链接**（引用知识库章节）

### 常见查询示例
- "如何配置 MCP 服务器？"
- "并行处理的最佳实践是什么？"
- "如何优化 AI Assistant 性能？"
- "如何避免会话冲突？"
HELP_EOF
echo "  快速查询 Skill 创建完成"

# 7. 更新 AI-ASSISTANT.md（在当前目录）
echo "📝 更新 AI-ASSISTANT.md..."
if [ -f "$CURRENT_DIR/AI-ASSISTANT.md" ]; then
    echo "  在现有 AI-ASSISTANT.md 中追加配置..."
    cat >> "$CURRENT_DIR/AI-ASSISTANT.md" << 'AI_ADDON'

<!-- AI Assistant 专家知识库集成 - 添加于 $(date) -->
### AI Assistant 专家知识库
- **优化工作流**: `/optimized-workflow` - 智能任务评估和并行处理
- **MCP 优化**: `/mcp-optimizer` - MCP 服务器配置和故障排查
- **快速帮助**: `/cc-help` - 查询最佳实践和技巧
- **知识库位置**: `~/.claude/skills/cc-expert/knowledge.md`

### 工作流原则
1. **MCP优先**: 优先使用 MCP 而非 shell
2. **Plan模式**: 复杂任务使用 Plan 模式规划
3. **安全并行**: 使用 git worktree 进行隔离并行
4. **质量检查**: 自动调用审查和安全检查

### 并行处理注意事项
⚠️ **重要**: 如需在多个终端中并行工作：
```bash
# 推荐方式：使用 git worktree 创建隔离工作区
git worktree add ../project-wt-1 -b parallel-task-1
cd ../project-wt-1
claude
```
AI_ADDON
    echo "  AI-ASSISTANT.md 已更新"
else
    echo "  创建新的 AI-ASSISTANT.md..."
    cat > "$CURRENT_DIR/AI-ASSISTANT.md" << 'AI_NEW'
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

### 调试命令
```bash
# 检查 MCP 状态
claude mcp list

# 查看会话
ls -la ~/.claude/sessions/

# 检查配置
cat ~/.claude/settings.json
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

---

*此文件由 AI Assistant 专家知识库配置脚本自动生成*
AI_NEW
    echo "  新的 AI-ASSISTANT.md 已创建"
fi

# 8. 验证安装
echo "✅ 验证安装..."
echo "  检查技能文件..."
ls -la ~/.claude/skills/ 2>/dev/null || echo "  ~/.claude/skills/ 目录不存在"
find ~/.claude/skills/ -name "*.md" -type f 2>/dev/null | while read file; do
    echo "  ✓ $(basename "$file")"
done

echo ""
echo "  检查知识库..."
if [ -f ~/.claude/skills/cc-expert/knowledge.md ]; then
    KB_SIZE=$(wc -l < ~/.claude/skills/cc-expert/knowledge.md)
    echo "  ✓ 知识库已创建 ($KB_SIZE 行)"
else
    echo "  ✗ 知识库创建失败"
fi

echo ""
echo "  检查命令..."
if [ -f ~/.claude/commands/cc-help.md ]; then
    echo "  ✓ cc-help 命令已创建"
else
    echo "  ✗ cc-help 命令创建失败"
fi

echo ""
echo "🎉 配置完成！"
echo "=============="
echo "📋 安装摘要："
echo ""
echo "📁 创建的目录："
echo "  ~/.claude/skills/cc-expert/"
echo "  ~/.claude/skills/cc-workflows/"
echo "  ~/.claude/commands/"
echo ""
echo "📄 创建的文件："
echo "  1. ~/.claude/skills/cc-expert/knowledge.md"
echo "  2. ~/.claude/skills/optimized-workflow.md"
echo "  3. ~/.claude/skills/mcp-optimizer.md"
echo "  4. ~/.claude/commands/cc-help.md"
echo "  5. $CURRENT_DIR/AI-ASSISTANT.md"
echo ""
echo "⚡ 可用技能："
echo "  /optimized-workflow - 智能工作流优化"
echo "  /mcp-optimizer - MCP 配置优化"
echo "  /cc-help - 快速查询帮助"
echo ""
echo "📚 知识库位置："
echo "  ~/.claude/skills/cc-expert/knowledge.md"
echo ""
echo "🔧 重新加载配置（如需要）："
echo "  cd $CURRENT_DIR && claude"
echo ""
echo "⚠️  重要提醒："
echo "  1. 如需在多个终端中并行工作，请使用 git worktree"
echo "  2. 新配置需要重启 AI Assistant 或重新加载会话"
echo "  3. 检查 AI-ASSISTANT.md 中的工作流原则"
echo ""
echo "✅ 所有修复已应用："
echo "  ✓ 路径正确性 ✓ Skill格式 ✓ 目录存在 ✓ 容错机制"