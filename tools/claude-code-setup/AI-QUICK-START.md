# AI Assistant 快速使用指南

## 🚀 快速开始

### 1. 环境变量设置（必须）

**选项A：在终端中持久化设置（推荐）**
```bash
# 在你的终端中运行（不是AI Assistant的Bash工具）
eval "$(/Users/frankie/claude-code-setup/init-claude-env.sh --export)"
```

**选项B：在AI Assistant中一次性设置**
```bash
# 在AI Assistant的Bash工具中使用组合命令
eval "$(./init-claude-env.sh --export)" && ./github-tools/github-diagnose.sh
```

### 2. 验证设置
```bash
# 运行综合验证
./validate-setup.sh

# 或分别验证
./github-tools/github-diagnose.sh
./dashscope-maintenance.sh --report
```

### 3. 使用别名（需要先 source ~/.zshrc）
```bash
# 重新加载zsh配置
source ~/.zshrc

# 使用别名
claude          # 交互选择所有模型
claude-dual     # 同上
claude-max      # Qwen最强性能 (qwen3.6-plus)
claude-dev      # DeepSeek R1新功能开发
claude-fix      # DeepSeek Chat Bug修复
claude-zh       # Qwen中文项目处理
claude-qwen     # 专用Qwen模型调用
claude-init     # 初始化环境变量（解决GitHub环境变量问题）
```

## 🔧 核心工作流

### GitHub工作流
```bash
# 诊断GitHub连接
eval "$(./init-claude-env.sh --export)" && ./github-tools/github-diagnose.sh

# 智能提交（使用模板）
./github-tools/github-smart-commit.sh "提交信息"

# 查看GitHub仓库
gh repo list
```

### 百炼平台工作流
```bash
# 完整维护检查
./dashscope-maintenance.sh --all

# 快速报告
./dashscope-maintenance.sh --report

# 测试Qwen模型
./claude-qwen-alt.sh -m qwen3.6-plus "你好"
```

### 双模型切换
```bash
# 交互式选择模型
./claude-dual-model.sh

# 专用模型调用
./claude-dual-model.sh 1    # DeepSeek
./claude-dual-model.sh 2    # Qwen
```

## ⚡ 常用命令速查

### 配置管理
```bash
# 检查当前配置
./claude-config.sh check

# 初始化环境（一次性）
./init-claude-env.sh

# 导出环境变量命令
./init-claude-env.sh --export
```

### 诊断工具
```bash
# GitHub诊断
./github-tools/github-diagnose.sh

# 百炼平台诊断
./dashscope-maintenance.sh --all

# 综合验证
./validate-setup.sh
```

### API测试
```bash
# 测试GitHub API
gh api user

# 测试百炼平台API
curl -s -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  https://dashscope.aliyuncs.com/api/v1/models | jq '.output.total'

# 测试DeepSeek API
curl -s -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"你好"}]}' \
  https://api.deepseek.com/chat/completions | jq '.choices[0].message.content'
```

## 🛠️ 故障排除

### 问题1: 环境变量未设置
**症状**: GitHub诊断工具报告"GITHUB_TOKEN未设置"
**解决方案**:
```bash
# 方法1: 使用组合命令
eval "$(./init-claude-env.sh --export)" && ./github-tools/github-diagnose.sh

# 方法2: 使用claude-init别名（需先source ~/.zshrc）
claude-init && ./github-tools/github-diagnose.sh

# 方法3: 在终端中持久化设置后重新启动AI Assistant
# 1. 在终端运行: eval "$(./init-claude-env.sh --export)"
# 2. 从同一终端启动AI Assistant
```

### 问题2: 别名不可用
**症状**: 命令"claude"未找到
**解决方案**:
```bash
# 重新加载zsh配置
source ~/.zshrc

# 或检查别名定义
grep "alias claude" ~/.zshrc
```

### 问题3: Qwen模型不可用
**症状**: "qwen3.6-max"模型不存在
**解决方案**: 使用qwen3.6-plus作为替代
```bash
claude-max        # 自动使用qwen3.6-plus
./claude-qwen-alt.sh -m qwen3.6-plus "你的问题"
```

### 问题4: SSH连接失败
**症状**: SSH连接测试失败
**解决方案**: 使用HTTPS协议（GitHub CLI使用HTTPS，工作正常）
```bash
# GitHub CLI使用HTTPS，无需SSH
gh auth status
```

## 📁 文件结构

```
claude-code-setup/
├── CLAUDE.md                    # 项目配置指南
├── CLAUDE-QUICK-START.md       # 本快速指南
├── SKILLS-IMPLEMENTATION-REPORT.md # 实施报告
├── init-claude-env.sh          # 环境初始化
├── validate-setup.sh           # 综合验证
├── claude-config.sh            # 配置管理
├── claude-dual-model.sh        # 双模型切换
├── claude-qwen-alt.sh          # Qwen模型调用
├── claude-dev.sh               # 开发工作流
├── claude-fix.sh               # 修复工作流
├── claude-zh.sh                # 中文工作流
├── github-tools/               # GitHub工具集
│   ├── github-diagnose.sh      # 诊断工具
│   └── github-smart-commit.sh  # 智能提交
└── dashscope-maintenance.sh    # 百炼平台维护
```

## 🎯 最佳实践

1. **开始新会话时**: 先运行 `eval "$(./init-claude-env.sh --export)"`
2. **使用GitHub工具时**: 使用组合命令确保环境变量已设置
3. **定期维护**: 每周运行一次 `./validate-setup.sh`
4. **备份配置**: 重要变更前备份 `~/.zshrc` 和 `~/.profile`
5. **安全注意**: API密钥已配置，无需额外设置

## 📞 支持

### 文档位置
- **技能包**: `~/.claude/skills/` (github-integration.md, bailian-platform.md)
- **记忆文件**: `~/.claude/projects/-Users-frankie/memory/`
- **项目文档**: `/Users/frankie/claude-code-setup/`

### 调试命令
```bash
# 检查环境变量
env | grep -E "(GITHUB|DASHSCOPE|DEEPSEEK|CLAUDE)"

# 检查Git配置
git config --global --list

# 检查GitHub CLI状态
gh auth status

# 检查脚本权限
ls -la /Users/frankie/claude-code-setup/*.sh
```

---

**生成时间**: 2026年4月12日  
**状态**: ✅ 所有技能包已成功配置并验证

> 💡 **提示**: 将此指南保存在易访问的位置，或添加到AI Assistant的上下文记忆中以便快速参考。