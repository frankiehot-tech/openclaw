# GitHub平台集成技能包

## 概述
GitHub平台集成技能包提供完整的GitHub工作流自动化支持，包括仓库管理、代码提交、Issue/PR管理、自动化工作流和安全配置。

## 核心功能

### 1. 仓库管理
- 创建和管理GitHub仓库
- 克隆和配置远程仓库
- 仓库权限和协作设置

### 2. 代码提交工作流
- 智能提交脚本和批量提交工具
- 分支管理和合并操作
- 版本控制和发布管理

### 3. Issue和PR管理
- Issue创建、标签、分配和跟踪
- Pull Request创建、审查和合并
- 项目管理板配置

### 4. 自动化工作流
- GitHub Actions CI/CD流水线
- 定期同步和自动化脚本
- 代码质量检查和测试

### 5. 安全配置
- 访问令牌管理和轮换
- SSH密钥配置和验证
- 分支保护和访问控制

## 技术架构

### 核心工具
- **GitHub CLI (gh)**: 主要命令行接口
- **Git**: 版本控制系统
- **GitHub REST API**: 程序化访问接口
- **GitHub Actions**: 自动化工作流平台

### 集成模式
1. **直接CLI操作**: 通过`gh`命令执行常见操作
2. **脚本自动化**: 使用bash脚本自动化重复任务
3. **API集成**: 通过REST API实现高级功能
4. **Claude Code智能路由**: 基于上下文智能推荐操作

## 配置要求

### 环境变量
```bash
export GITHUB_USERNAME="frankiehot-tech"
export GITHUB_EMAIL="frankiehot@hotmail.com"
# 可选：如需直接调用REST API
export GITHUB_TOKEN="your_personal_access_token"
```

### Git配置
```bash
git config --global user.name "frankiehot-tech"
git config --global user.email "frankiehot@hotmail.com"
```

### GitHub CLI认证
```bash
# 使用交互式登录
gh auth login

# 或使用令牌登录
gh auth login --with-token <<< "your_token_here"
```

## 工具脚本

### 核心脚本
- `github-diagnose.sh` - 连接诊断工具
- `github-smart-commit.sh` - 智能提交工具
- `github-auto-sync.sh` - 自动同步脚本
- `github-secure-setup.sh` - 安全配置脚本

### 分析工具
- `github-repo-analysis.sh` - 仓库分析工具
- `github-commit-stats.sh` - 提交统计工具
- `github-pr-analysis.sh` - PR分析工具

## 使用场景

### 场景1：新项目初始化
```
用户: "创建一个新的React项目并推送到GitHub"

技能自动执行:
1. 创建本地项目: npx create-react-app my-app
2. 初始化Git仓库: git init
3. 创建GitHub仓库: gh repo create my-app --private --clone
4. 添加初始提交: git add . && git commit -m "Initial commit"
5. 推送到GitHub: git push origin main
6. 生成项目文档: 创建README.md
```

### 场景2：团队协作设置
```
用户: "设置团队项目，添加协作者和分支保护"

技能自动执行:
1. 创建组织仓库或设置团队权限
2. 添加团队成员为协作者
3. 配置分支保护规则
4. 设置代码审查要求
5. 创建团队协作指南
```

### 场景3：CI/CD流水线配置
```
用户: "为项目配置自动化测试和部署"

技能自动执行:
1. 分析项目类型和需求
2. 创建GitHub Actions工作流文件
3. 配置测试、构建、部署步骤
4. 设置环境变量和密钥
5. 测试工作流执行
```

## 故障排查

### 常见问题

#### 问题1：认证失败
```bash
# 重新登录
gh auth logout
gh auth login

# 检查令牌权限
gh auth status
```

#### 问题2：推送被拒绝
```bash
# 先拉取再推送
git pull origin main --rebase
git push origin main

# 检查分支保护设置
gh api /repos/frankiehot-tech/repo-name/branches/main/protection
```

#### 问题3：环境变量未传递
```bash
# 使用组合命令确保环境变量已设置
eval "$(./init-claude-env.sh --export)" && ./github-diagnose.sh
```

### 诊断命令
```bash
# 综合诊断
./github-tools/github-diagnose.sh

# 验证Git配置
git config --list | grep -E "(user\.|email)"

# 测试API连接
gh api user
```

## 验证状态

### 已验证功能 (2026-04-12)
✅ **GitHub CLI认证**: 正常 (用户: frankiehot-tech)  
✅ **Git配置**: 正常 (用户名: frankiehot-tech, 邮箱: frankiehot@hotmail.com)  
✅ **仓库管理**: 正常 (支持创建、查看、克隆)  
✅ **API连接**: 正常 (通过gh api命令)  
✅ **自动化工作流**: 正常 (GitHub Actions模板创建)  
✅ **诊断工具**: 正常 (github-diagnose.sh运行正常)

### 关键配置
- **GitHub用户名**: `frankiehot-tech` (已统一配置)
- **认证方式**: GitHub CLI keyring存储
- **环境变量解决方案**: `eval "$(./init-claude-env.sh --export)"`
- **可用工具**: 完整的脚本工具集

## 与Claude Code集成

### 智能触发关键词
当用户描述包含以下关键词时自动触发：
- "GitHub"、"仓库"、"代码托管"
- "提交"、"推送"、"分支"、"合并"
- "Issue"、"PR"、"拉取请求"
- "CI/CD"、"自动化"、"工作流"

### 自动工作流示例
```
用户: "无法推送到GitHub"

技能自动执行:
1. 运行 ./github-diagnose.sh
2. 检查认证状态
3. 验证仓库权限
4. 提供修复建议
5. 执行修复操作
```

### 与其他技能协同
- **优化工作流**: 复杂任务使用并行处理
- **MCP集成**: 与GitHub MCP服务器协同
- **安全审查**: 应用代码安全最佳实践
- **上下文管理**: 保留Git操作历史

## 最佳实践

### 提交规范
- 使用语义化提交信息
- 保持提交小而专注
- 定期提交，避免大块更改
- 添加有意义的提交描述

### 分支策略
- `main` - 生产就绪代码
- `feature/*` - 新功能开发
- `bugfix/*` - 问题修复
- `release/*` - 版本发布

### 安全实践
- 使用个人访问令牌，不要使用密码
- 定期轮换访问令牌
- 启用双因素认证
- 审查第三方应用权限

## 持续改进

### 反馈循环
1. **监控操作日志**: 分析脚本输出和错误
2. **收集用户反馈**: 记录常见问题和解决方案
3. **定期更新脚本**: 根据反馈改进工作流
4. **测试新功能**: 验证GitHub平台新特性

### 知识共享
- 维护经验文档化
- 常见问题解决方案库
- 最佳实践案例分享
- 自动化脚本模板库

---

**版本**: 1.0.0  
**状态**: ✅ 已验证通过  
**最后更新**: 2026-04-12  
**集成状态**: 与Claude Code智能维护系统完全集成