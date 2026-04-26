# CI/CD流水线技能包安装指南

## 🎯 概述

CI/CD流水线技能包为AI Assistant提供完整的CI/CD流水线设计和生成能力。本指南说明如何安装和使用该技能。

## 📦 安装方法

### 方法1: 手动安装

1. **复制技能文件到AI Assistant技能目录**
   ```bash
   # 创建技能目录 (如果不存在)
   mkdir -p ~/.claude/skills/
   
   # 复制CI/CD技能文件
   cp ci-cd-designer.md ~/.claude/skills/
   ```

2. **重启AI Assistant会话**
   关闭当前AI Assistant会话并重新打开，使新技能生效。

### 方法2: 使用安装脚本 (推荐)

```bash
# 进入CI/CD技能包目录
cd /Users/frankie/claude-code-setup/stage2/ci-cd-pipelines

# 运行安装脚本
./install.sh
```

## 🔧 验证安装

在AI Assistant会话中测试技能是否已加载：

```
可用技能: /ci-cd-designer
```

或者尝试使用技能：

```
为我的Python项目创建CI/CD流水线
```

## 🚀 使用方法

### 1. 激活技能

在AI Assistant会话中使用以下方式激活技能：

```
使用CI/CD设计技能
```

或直接使用技能命令：

```
/ci-cd-designer
```

### 2. 描述你的需求

用自然语言描述你的CI/CD需求：

- **项目类型**: Python、Node.js、React、Java、Go等
- **CI/CD平台**: GitHub Actions、GitLab CI、Jenkins
- **测试要求**: 单元测试、集成测试、E2E测试
- **部署需求**: Docker、Kubernetes、Serverless、云平台
- **安全要求**: 代码扫描、漏洞检查、合规性检查

### 3. 生成配置文件

技能将根据你的需求生成：

- CI/CD配置文件 (`.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`)
- 测试自动化配置 (`jest.config.js`, `pytest.ini`, `cypress.config.js`)
- 部署策略配置 (`deployment/kubernetes/`, `deployment/docker/`)
- 安全扫描配置

### 4. 自定义和优化

你可以进一步自定义生成的配置：

- 调整作业执行顺序
- 配置缓存策略优化构建时间
- 设置环境变量和密钥
- 配置通知和告警

## 📋 使用示例

### 示例1: 为Python Flask项目创建CI/CD

```
用户: "为我的Python Flask项目创建完整的CI/CD流水线"

技能将生成:
1. GitHub Actions工作流配置 (测试、构建、部署)
2. pytest测试配置和覆盖率报告
3. Docker镜像构建配置
4. 数据库迁移自动化
5. 安全扫描配置 (Bandit、Safety)
```

### 示例2: 配置React + Node.js全栈应用部署

```
用户: "为我的React前端和Node.js后端配置部署到Kubernetes"

技能将生成:
1. 前端和后端分离的CI配置
2. Docker多阶段构建配置
3. Kubernetes部署配置 (dev/staging/prod环境)
4. Ingress路由和负载均衡配置
5. 监控和健康检查配置
```

### 示例3: 实现蓝绿部署策略

```
用户: "为我的微服务应用实现蓝绿部署策略"

技能将生成:
1. 蓝绿部署工作流配置
2. 流量切换和健康检查配置
3. 自动回滚机制
4. 部署验证和监控配置
5. 数据库迁移策略
```

## 🔧 高级配置

### 自定义模板

你可以自定义技能使用的模板：

1. **修改现有模板**
   ```bash
   # 编辑GitHub Actions模板
   vim github-actions/python-ci.yml
   
   # 编辑Kubernetes部署模板
   vim deployment/kubernetes/dev/deployment.yaml
   ```

2. **添加新模板**
   ```bash
   # 创建新的项目类型模板
   cp github-actions/python-ci.yml github-actions/go-ci.yml
   
   # 修改新模板以适应Go项目需求
   ```

### 环境变量配置

技能支持通过环境变量自定义行为：

```bash
# 设置默认CI/CD平台
export DEFAULT_CICD_PLATFORM="github-actions"

# 设置默认测试框架
export DEFAULT_TEST_FRAMEWORK="jest"

# 设置部署目标
export DEFAULT_DEPLOYMENT_TARGET="kubernetes"
```

### 技能参数

你可以在使用技能时传递参数：

```
/ci-cd-designer --platform=gitlab-ci --language=python --deployment=docker
```

支持的参数：
- `--platform`: ci/cd平台 (github-actions, gitlab-ci, jenkins)
- `--language`: 编程语言 (python, nodejs, java, go, react)
- `--deployment`: 部署目标 (docker, kubernetes, serverless, cloud-run)
- `--tests`: 测试类型 (unit, integration, e2e, performance)
- `--security`: 安全扫描级别 (basic, standard, strict)

## 🔄 更新技能

### 手动更新

```bash
# 拉取最新代码
cd /Users/frankie/claude-code-setup
git pull origin main

# 重新安装技能
cd stage2/ci-cd-pipelines
./install.sh
```

### 自动更新

配置自动更新脚本 `update-skills.sh`:

```bash
#!/bin/bash
# 自动更新所有技能
SKILLS_DIR="$HOME/.claude/skills"
SETUP_DIR="/Users/frankie/claude-code-setup"

echo "更新CI/CD技能包..."
cp "$SETUP_DIR/stage2/ci-cd-pipelines/ci-cd-designer.md" "$SKILLS_DIR/"

echo "技能更新完成!"
```

## 🛠️ 故障排除

### 常见问题

#### 1. 技能未加载
**症状**: 在AI Assistant中看不到`/ci-cd-designer`命令
**解决方案**:
```bash
# 检查技能文件位置
ls -la ~/.claude/skills/ci-cd-designer.md

# 检查文件权限
chmod 644 ~/.claude/skills/ci-cd-designer.md

# 重启AI Assistant会话
```

#### 2. 模板文件找不到
**症状**: 技能运行时报错找不到模板文件
**解决方案**:
```bash
# 确保模板目录存在
ls -la /Users/frankie/claude-code-setup/stage2/ci-cd-pipelines/

# 设置正确的模板路径
export CICD_TEMPLATE_PATH="/Users/frankie/claude-code-setup/stage2/ci-cd-pipelines"
```

#### 3. 生成的配置有问题
**症状**: 生成的配置文件语法错误或不完整
**解决方案**:
- 检查模板文件语法
- 验证环境变量设置
- 查看技能运行日志
- 手动测试生成的配置

### 调试技能

启用详细日志模式：

```bash
# 设置调试环境变量
export AI_DEBUG=1
export CICD_VERBOSE=1

# 运行技能并查看详细输出
```

## 📚 相关资源

- [AI Assistant官方文档](https://docs.example.com/claude/code)
- [GitHub Actions文档](https://docs.github.com/actions)
- [GitLab CI/CD文档](https://docs.gitlab.com/ee/ci/)
- [Jenkins文档](https://www.jenkins.io/doc/)
- [Kubernetes部署最佳实践](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

## 🤝 支持

### 获取帮助

- **GitHub Issues**: [问题跟踪](https://github.com/anthropics/claude-code-setup/issues)
- **文档**: [完整文档](https://github.com/anthropics/claude-code-setup/wiki)
- **讨论**: [社区论坛](https://github.com/anthropics/claude-code-setup/discussions)

### 报告问题

报告问题时请提供：

1. **问题描述**: 详细描述问题和复现步骤
2. **环境信息**: AI Assistant版本、操作系统、技能版本
3. **日志输出**: 错误日志和调试信息
4. **期望结果**: 你期望的行为是什么

## 🆕 版本历史

### v1.0.0 (2026-04-12)
- 初始版本发布
- 支持GitHub Actions、GitLab CI、Jenkins三大平台
- 提供完整的模板库和示例
- 详细的安装和使用文档

---

**提示**: 使用技能前，建议先在测试项目中验证生成的配置。对于生产环境，请确保进行充分的安全审查和测试。