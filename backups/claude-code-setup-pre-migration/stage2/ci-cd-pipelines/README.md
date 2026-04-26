# CI/CD流水线技能包

为AI Assistant提供完整的CI/CD流水线设计和生成能力，支持多种CI/CD平台和自动化工具。

## 🚀 快速开始

### 1. 技能激活
在AI Assistant会话中使用：
```
使用CI/CD设计技能
```

### 2. 描述你的需求
用自然语言描述你的项目需求：
- 项目类型 (Python、Node.js、React、Java等)
- CI/CD平台 (GitHub Actions、GitLab CI、Jenkins)
- 测试要求 (单元测试、集成测试、E2E测试)
- 部署环境 (开发、预生产、生产)
- 安全要求 (代码扫描、漏洞检查)

### 3. 自动生成配置
技能将根据需求自动生成：
- CI/CD配置文件
- 测试自动化配置
- 部署策略
- 安全扫描配置

## 📋 支持的CI/CD平台

### GitHub Actions
- **模板位置**: `github-actions/`
- **支持类型**: Python、Node.js、React、Java、Go、Docker
- **特性**: 工作流生成、缓存优化、环境管理

### GitLab CI/CD
- **模板位置**: `gitlab-ci/`
- **支持类型**: 多阶段管道、制品管理、环境部署
- **特性**: Docker集成、Kubernetes部署、变量管理

### Jenkins
- **模板位置**: `jenkins/`
- **支持类型**: 多分支管道、参数化构建、插件集成
- **特性**: 脚本化管道、凭证管理、分布式构建

## 🛠️ 核心功能

### 1. 流水线生成器
根据项目技术栈自动生成优化的CI/CD配置：
- 语言检测：Python、JavaScript/TypeScript、Java、Go等
- 框架检测：Django、Flask、React、Spring Boot等
- 构建工具检测：npm、yarn、pip、Maven、Gradle等

### 2. 测试自动化编排
集成全面的测试套件：
- **单元测试**: Jest、Pytest、JUnit、Mocha
- **集成测试**: Cypress、Playwright、Postman
- **端到端测试**: Selenium、TestCafe
- **性能测试**: k6、Artillery、Locust

### 3. 部署环境管理
多环境部署策略：
- **开发环境**: 自动部署到开发服务器
- **预生产环境**: 集成测试环境部署
- **生产环境**: 蓝绿部署、金丝雀发布、自动回滚
- **环境变量**: 安全的变量管理和密钥存储

### 4. 安全与合规
内置安全最佳实践：
- **代码安全扫描**: SAST工具集成
- **依赖漏洞检查**: SCA工具集成
- **容器安全扫描**: 镜像漏洞检查
- **合规性检查**: 安全策略验证

## 📁 目录结构

```
ci-cd-pipelines/
├── README.md                  # 本文档
├── ci-cd-designer.md         # CI/CD设计技能文档
├── github-actions/           # GitHub Actions模板
│   ├── python-ci.yml         # Python项目CI模板
│   ├── nodejs-ci.yml         # Node.js项目CI模板
│   ├── react-ci.yml          # React项目CI模板
│   ├── java-ci.yml           # Java项目CI模板
│   └── docker-ci.yml         # Docker镜像构建模板
├── gitlab-ci/                # GitLab CI模板
│   ├── python-gitlab-ci.yml  # Python项目配置
│   ├── nodejs-gitlab-ci.yml  # Node.js项目配置
│   ├── java-gitlab-ci.yml    # Java项目配置
│   └── kubernetes-gitlab-ci.yml # Kubernetes部署配置
├── jenkins/                  # Jenkins模板
│   ├── Jenkinsfile-python    # Python项目管道
│   ├── Jenkinsfile-nodejs    # Node.js项目管道
│   ├── Jenkinsfile-java      # Java项目管道
│   └── Jenkinsfile-docker    # Docker构建管道
├── test-automation/          # 测试自动化配置
│   ├── jest.config.js        # Jest测试配置
│   ├── pytest.ini            # Pytest配置
│   ├── cypress.config.js     # Cypress配置
│   └── k6-script.js          # k6性能测试脚本
├── deployment/               # 部署策略配置
│   ├── kubernetes/           # Kubernetes部署配置
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   ├── docker/              # Docker部署配置
│   │   ├── Dockerfile.template
│   │   └── docker-compose.yml
│   └── serverless/          # Serverless部署配置
│       ├── serverless.yml
│       └── aws-lambda.yml
└── examples/                # 使用示例
    ├── python-flask-app/    # Python Flask应用示例
    ├── react-nodejs-app/    # React + Node.js全栈示例
    └── java-spring-app/     # Java Spring Boot应用示例
```

## 🔧 使用示例

### 示例1: 为Python项目创建CI/CD流水线
```
用户: "为我的Django项目创建完整的CI/CD流水线"

技能将生成:
1. GitHub Actions工作流配置
2. 单元测试和集成测试配置
3. Docker镜像构建配置
4. 数据库迁移自动化
5. 安全扫描配置
```

### 示例2: 配置Node.js React应用部署
```
用户: "为我的React前端和Node.js后端配置部署到Kubernetes"

技能将生成:
1. 前端和后端CI配置
2. Docker多阶段构建配置
3. Kubernetes部署配置 (dev/staging/prod)
4. Ingress路由配置
5. 健康检查和监控配置
```

### 示例3: 实现蓝绿部署策略
```
用户: "为我的微服务应用实现蓝绿部署策略"

技能将生成:
1. 蓝绿部署工作流配置
2. 流量切换配置
3. 自动回滚机制
4. 部署健康检查
5. 监控和告警配置
```

## 🔄 智能优化功能

### 构建性能优化
- **依赖缓存**: 自动配置依赖包缓存
- **增量构建**: 只构建变更的部分
- **并行执行**: 并行运行独立的任务

### 部署可靠性
- **健康检查**: 应用健康状态监控
- **就绪探针**: 确保应用完全启动
- **优雅关闭**: 处理关闭时的连接保持

### 成本优化
- **云资源优化**: 合理配置资源配额
- **闲置资源清理**: 自动清理测试环境资源
- **使用量监控**: 实时监控CI/CD成本

## 🛡️ 安全最佳实践

### 凭据安全
- **密钥管理**: 使用CI/CD平台的密钥管理
- **最小权限**: 遵循最小权限原则
- **临时令牌**: 使用短期访问令牌

### 代码安全
- **依赖漏洞扫描**: 自动扫描依赖包漏洞
- **代码安全扫描**: SAST工具集成
- **容器安全**: 镜像漏洞扫描

### 部署安全
- **分支保护**: 主分支保护规则
- **审批流程**: 生产环境部署审批
- **审计日志**: 完整的操作审计

## 📊 监控和报告

### 流水线指标
- **构建成功率**: 历史构建成功率统计
- **构建时间**: 平均构建时间跟踪
- **部署频率**: 部署频率统计

### 质量指标
- **测试覆盖率**: 代码测试覆盖率报告
- **代码质量**: 代码质量评分
- **安全评分**: 安全漏洞统计

### 性能指标
- **应用性能**: 应用响应时间监控
- **资源使用**: CPU/内存使用监控
- **成本分析**: CI/CD成本分析报告

## 🔍 故障排查

### 常见问题解决

#### 构建失败
1. **依赖安装失败**
   - 检查网络连接
   - 验证依赖源配置
   - 检查依赖版本兼容性

2. **测试失败**
   - 检查测试环境配置
   - 验证测试数据
   - 查看测试日志

3. **构建超时**
   - 优化构建步骤
   - 增加构建超时时间
   - 配置构建资源

#### 部署失败
1. **权限不足**
   - 检查部署凭据
   - 验证目标环境权限
   - 更新访问令牌

2. **资源不足**
   - 检查目标环境资源
   - 优化应用资源需求
   - 增加资源配额

3. **配置错误**
   - 验证部署配置
   - 检查环境变量
   - 查看部署日志

## 🚀 高级功能

### 1. 多环境部署
支持同时管理多个部署环境：
- **开发环境**: 用于日常开发和测试
- **预生产环境**: 用于集成测试和验证
- **生产环境**: 面向最终用户的生产环境

### 2. 渐进式发布
支持多种发布策略：
- **金丝雀发布**: 逐步扩大流量
- **蓝绿部署**: 零停机时间切换
- **特性标志**: 控制功能启用

### 3. 跨平台支持
支持在不同CI/CD平台间迁移：
- **配置转换**: 将GitHub Actions配置转换为GitLab CI配置
- **最佳实践移植**: 跨平台最佳实践保持
- **平台特性利用**: 充分利用各平台特有功能

### 4. 智能推荐
基于AI的智能推荐：
- **配置优化建议**: 基于历史数据推荐优化
- **性能预测**: 预测构建和部署时间
- **成本分析**: 分析CI/CD成本并提出优化建议

## 📈 性能指标

| 指标 | 目标值 | 监控方法 |
|------|--------|----------|
| **构建成功率** | > 99% | CI/CD平台报告 |
| **平均构建时间** | < 10分钟 | 构建时间跟踪 |
| **测试覆盖率** | > 80% | 测试覆盖率报告 |
| **部署频率** | 每天多次 | 部署日志分析 |
| **平均恢复时间** | < 10分钟 | 故障恢复跟踪 |
| **安全漏洞数** | 0严重漏洞 | 安全扫描报告 |

## 🔗 集成生态

### 与云服务MCP集成
- **AWS集成**: CodePipeline、CodeBuild、ECS、EKS
- **Azure集成**: DevOps、Container Registry、Kubernetes
- **GCP集成**: Cloud Build、Artifact Registry、GKE
- **云原生工具**: Helm、Kustomize、ArgoCD、Flux

### 与监控系统集成
- **Prometheus集成**: 指标收集和监控
- **Grafana集成**: 可视化仪表板
- **ELK集成**: 日志收集和分析
- **告警集成**: Slack、Teams、Email通知

### 与开发工具集成
- **版本控制**: Git、GitHub、GitLab、Bitbucket
- **项目管理**: Jira、Trello、Asana
- **代码审查**: GitHub PR、GitLab MR、Gerrit
- **文档平台**: Confluence、Notion、ReadTheDocs

## 📚 学习资源

### 官方文档
- [GitHub Actions官方文档](https://docs.github.com/actions)
- [GitLab CI/CD官方文档](https://docs.gitlab.com/ee/ci/)
- [Jenkins官方文档](https://www.jenkins.io/doc/)
- [Docker最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

### 最佳实践指南
- [Google DevOps指南](https://cloud.google.com/architecture/devops)
- [AWS DevOps最佳实践](https://aws.amazon.com/devops/)
- [Microsoft DevOps实践](https://docs.microsoft.com/en-us/devops/)

### 社区资源
- [GitHub Actions社区工作流](https://github.com/actions/starter-workflows)
- [GitLab CI/CD模板](https://gitlab.com/gitlab-org/gitlab/-/tree/master/lib/gitlab/ci/templates)
- [Jenkins共享库](https://github.com/jenkinsci/pipeline-library)

## 🆕 版本历史

### v1.0.0 (2026-04-11)
- 初始版本发布
- 支持GitHub Actions、GitLab CI、Jenkins三大平台
- 提供Python、Node.js、React、Java项目模板
- 集成测试自动化、安全扫描、部署策略
- 完整的文档和示例

## 🤝 贡献指南

欢迎贡献代码、文档或想法！

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

### 开发环境设置
```bash
# 克隆仓库
git clone https://github.com/anthropics/claude-code-setup.git

# 进入CI/CD技能包目录
cd /Users/frankie/claude-code-setup/stage2/ci-cd-pipelines

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 代码规范
- 遵循项目的代码风格和规范
- 添加适当的文档和注释
- 包含测试用例
- 确保向后兼容性

## 📞 支持

- **GitHub Issues**: [问题跟踪](https://github.com/anthropics/claude-code-setup/issues)
- **文档**: [完整文档](https://github.com/anthropics/claude-code-setup/wiki)
- **讨论**: [社区论坛](https://github.com/anthropics/claude-code-setup/discussions)
- **邮件**: noreply@example.com

---

**提示**: 使用前请确保了解你的项目需求和安全要求。建议先在测试环境中验证生成的配置。