---
name: ci-cd-designer
description: CI/CD流水线设计技能包 - GitHub Actions、GitLab CI、Jenkins配置生成、部署策略、测试自动化
---

# CI/CD流水线设计技能

为AI Assistant提供CI/CD流水线设计和生成能力，支持GitHub Actions、GitLab CI、Jenkins等多种CI/CD平台。

## 🎯 技能目标

通过自然语言交互，帮助用户：
1. **生成CI/CD配置**：根据项目需求自动生成流水线配置文件
2. **管理部署环境**：配置dev/staging/prod环境部署策略
3. **编排测试自动化**：集成单元测试、集成测试、E2E测试
4. **优化部署流程**：实现蓝绿部署、金丝雀发布、自动回滚

## 🛠️ 支持的CI/CD平台

### 1. GitHub Actions
- **工作流生成器**：生成.github/workflows/*.yml配置文件
- **事件触发器**：push、pull_request、schedule等
- **作业编排**：并行/串行作业、依赖管理
- **缓存优化**：依赖缓存、构建缓存配置
- **环境管理**：环境变量、密钥、部署保护

### 2. GitLab CI/CD
- **管道配置**：生成.gitlab-ci.yml配置文件
- **阶段定义**：build、test、deploy、cleanup
- **制品管理**：artifacts、cache、dependencies
- **环境变量**：project/group变量管理
- **Docker集成**：Kubernetes、容器注册表集成

### 3. Jenkins
- **管道脚本**：生成Jenkinsfile (Declarative/Scripted)
- **多分支管道**：分支策略、PR构建、标签构建
- **插件集成**：Blue Ocean、Docker、Kubernetes插件
- **参数化构建**：环境参数、构建参数
- **凭证管理**：密钥、证书、凭据安全存储

### 4. 通用功能
- **测试自动化**：Jest、Pytest、Cypress、Selenium配置
- **安全扫描**：代码安全扫描、依赖漏洞检查
- **性能测试**：负载测试、性能基准
- **质量门禁**：代码覆盖率、代码质量检查
- **通知集成**：Slack、Teams、Email通知

## 📋 使用示例

### 示例1: 为Python项目创建GitHub Actions工作流
```
用户: "为我的Python项目创建GitHub Actions工作流，支持测试、代码质量检查和安全扫描"

AI Assistant技能应生成:
- .github/workflows/ci.yml: CI流水线
- .github/workflows/cd.yml: CD流水线
- .github/workflows/security.yml: 安全扫描流水线
```

### 示例2: 配置多环境Kubernetes部署
```
用户: "为我的Node.js应用配置多环境Kubernetes部署，包括dev、staging、prod环境"

AI Assistant技能应生成:
- deployment/kubernetes/dev/
- deployment/kubernetes/staging/
- deployment/kubernetes/prod/
- 对应的Helm chart或Kustomize配置
```

### 示例3: 创建完整的测试自动化流水线
```
用户: "为我的React + Node.js全栈应用创建完整的测试自动化流水线"

AI Assistant技能应生成:
- 单元测试配置 (Jest/Vitest)
- 集成测试配置 (Cypress/Playwright)
- API测试配置 (Postman/Newman)
- 端到端测试配置
- 性能测试配置
```

## 🚀 快速开始

### 1. 激活技能
在AI Assistant会话中使用以下命令激活技能：
```
使用CI/CD设计技能
```

### 2. 描述你的需求
用自然语言描述你的CI/CD需求：
- 项目类型 (Python、Node.js、React、Java等)
- 需要的CI/CD平台 (GitHub Actions、GitLab CI、Jenkins)
- 测试要求 (单元测试、集成测试、E2E测试)
- 部署需求 (容器化、云平台、多环境)
- 安全要求 (代码扫描、依赖检查、漏洞扫描)

### 3. 生成配置文件
技能将根据需求生成：
- CI/CD配置文件
- 环境配置
- 部署脚本
- 测试配置
- 安全策略

### 4. 自定义和优化
你可以进一步自定义生成的配置：
- 调整作业执行顺序
- 配置缓存策略
- 优化构建时间
- 设置通知规则

## 🔧 配置模板

技能内置了多种配置模板，可根据项目类型自动选择：

### Python项目模板
- **CI流程**: 虚拟环境管理、依赖安装、单元测试、代码质量检查
- **部署策略**: Docker镜像构建、推送到容器注册表、Kubernetes部署
- **测试套件**: pytest单元测试、代码覆盖率、安全扫描

### Node.js项目模板
- **CI流程**: npm/yarn依赖安装、lint检查、单元测试、构建
- **部署策略**: 容器化部署、Serverless部署、静态站点部署
- **测试套件**: Jest单元测试、集成测试、端到端测试

### React/前端项目模板
- **CI流程**: 依赖安装、lint检查、单元测试、构建优化
- **部署策略**: 静态站点部署 (Vercel、Netlify、S3+CloudFront)
- **测试套件**: Jest/React Testing Library、Cypress E2E测试

### Java项目模板
- **CI流程**: Maven/Gradle构建、单元测试、集成测试、打包
- **部署策略**: JAR包部署、Docker容器部署、Kubernetes部署
- **测试套件**: JUnit测试、Mockito、Spring Boot测试

## 📁 生成的目录结构

```
项目根目录/
├── .github/workflows/
│   ├── ci.yml              # 持续集成工作流
│   ├── cd.yml              # 持续部署工作流
│   ├── security.yml        # 安全扫描工作流
│   └── dependabot.yml      # 依赖更新自动化
├── .gitlab-ci.yml          # GitLab CI/CD配置
├── Jenkinsfile             # Jenkins管道脚本
├── deployment/
│   ├── kubernetes/
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   └── terraform/          # 基础设施即代码
├── test-automation/
│   ├── unit-tests/
│   ├── integration-tests/
│   ├── e2e-tests/
│   └── performance-tests/
└── security/
    ├── code-scanning/
    └── dependency-check/
```

## 🔄 智能优化功能

### 1. 构建缓存优化
- 自动检测项目依赖管理器 (npm、yarn、pip、Maven、Gradle)
- 配置相应的缓存策略
- 避免重复安装依赖

### 2. 并行执行优化
- 分析测试依赖关系
- 配置并行测试执行
- 优化整体执行时间

### 3. 部署策略推荐
- 根据应用类型推荐部署策略
- 容器化 vs Serverless vs 传统部署
- 多区域/多云部署策略

### 4. 安全合规检查
- 自动集成安全扫描工具
- 配置合规性检查
- 生成安全报告

## 🛡️ 安全最佳实践

### 凭据管理
- **环境密钥**: 使用CI/CD平台的密钥管理功能
- **最小权限**: 遵循最小权限原则
- **临时凭据**: 使用临时访问令牌

### 安全扫描
- **代码扫描**: SAST (静态应用安全测试)
- **依赖扫描**: SCA (软件组成分析)
- **容器扫描**: 容器镜像漏洞扫描

### 访问控制
- **分支保护**: 主分支保护、代码审查要求
- **部署审批**: 生产环境部署需要人工审批
- **审计日志**: 记录所有部署操作

## 📊 监控和告警

### 流水线监控
- **执行状态**: 成功/失败率统计
- **执行时间**: 构建和部署时间跟踪
- **资源使用**: CPU/内存使用监控

### 告警配置
- **失败告警**: 流水线失败即时通知
- **性能告警**: 构建时间异常告警
- **安全告警**: 安全扫描发现问题告警

### 仪表板
- **CI/CD指标仪表板**
- **部署频率和质量报告**
- **团队效率分析**

## 🔍 故障排查

### 常见问题

#### 1. 构建失败
- **依赖安装失败**: 检查网络连接和依赖源配置
- **测试失败**: 检查测试环境和测试数据
- **构建超时**: 优化构建步骤和资源配置

#### 2. 部署失败
- **权限不足**: 检查部署凭据和权限
- **资源不足**: 检查目标环境资源可用性
- **配置错误**: 检查部署配置和参数

#### 3. 安全扫描失败
- **漏洞误报**: 配置漏洞排除规则
- **依赖版本**: 更新有漏洞的依赖版本
- **合规性要求**: 满足安全合规性要求

### 调试技巧
- **启用详细日志**: 在CI/CD配置中启用调试模式
- **本地复现**: 在本地环境中复现CI/CD问题
- **增量调试**: 逐步测试流水线步骤

## 📈 性能优化建议

### 构建性能优化
- **使用缓存**: 合理配置依赖缓存和构建缓存
- **并行执行**: 并行运行独立的任务
- **增量构建**: 只构建变更的部分

### 部署性能优化
- **镜像优化**: 使用多阶段构建减少镜像大小
- **部署策略**: 使用蓝绿部署减少停机时间
- **回滚机制**: 快速回滚减少故障影响时间

### 测试性能优化
- **测试分割**: 将测试分割到多个并行任务
- **测试选择**: 只运行受影响的测试
- **测试数据**: 使用轻量级测试数据

## 🤖 智能推荐系统

### 技术栈检测
- 自动检测项目技术栈 (编程语言、框架、构建工具)
- 推荐合适的CI/CD配置模板
- 建议最佳实践和安全配置

### 性能基准
- 与同类项目比较构建和部署性能
- 提供优化建议和配置调整
- 预测构建时间和资源需求

### 成本优化
- 优化云资源使用
- 减少不必要的构建和部署
- 建议成本节约措施

## 🔄 与云服务MCP集成

### AWS集成
- 自动配置AWS CodePipeline、CodeBuild、CodeDeploy
- 集成AWS ECR、ECS、EKS部署
- 使用AWS Secrets Manager管理密钥

### Kubernetes集成
- 自动生成Kubernetes部署配置
- 集成Helm chart或Kustomize
- 配置健康检查和就绪探针

### Docker集成
- 生成优化的Dockerfile
- 配置多阶段构建
- 集成容器注册表推送

## 📚 学习资源

### 官方文档
- [GitHub Actions文档](https://docs.github.com/actions)
- [GitLab CI/CD文档](https://docs.gitlab.com/ee/ci/)
- [Jenkins文档](https://www.jenkins.io/doc/)
- [Docker最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

### 最佳实践指南
- [CI/CD最佳实践](https://www.redhat.com/en/topics/devops/what-is-ci-cd)
- [安全DevOps指南](https://cloud.google.com/architecture/devops)
- [云原生CI/CD](https://www.cncf.io/projects/)

### 社区资源
- [CI/CD模板库](https://github.com/actions/starter-workflows)
- [Jenkins共享库](https://www.jenkins.io/doc/book/pipeline/shared-libraries/)
- [GitLab模板](https://gitlab.com/gitlab-org/gitlab/-/tree/master/lib/gitlab/ci/templates)

## 🆕 未来计划

### 即将支持的功能
- **AI优化流水线**: 使用机器学习优化构建和部署策略
- **跨平台同步**: 在不同CI/CD平台间同步配置
- **成本智能分析**: 实时分析CI/CD成本并提供优化建议
- **合规性自动化**: 自动满足GDPR、HIPAA等合规要求
- **团队协作增强**: 多人协作的CI/CD配置管理

### 平台扩展
- **CircleCI集成**: 支持CircleCI配置生成
- **Azure DevOps集成**: 支持Azure Pipelines配置
- **Travis CI集成**: 支持Travis CI配置
- **Spinnaker集成**: 支持Spinnaker部署编排

---

**提示**: 使用此技能前，请确保了解你的项目需求和目标部署环境。对于生产环境，建议进行充分的测试和验证。