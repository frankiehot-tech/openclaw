# Python项目CI/CD示例

这个示例展示了如何使用AI Assistant的CI/CD技能包为Python项目配置完整的CI/CD流水线。

## 🎯 项目概述

这是一个简单的Python Flask Web应用，包含：
- RESTful API端点
- 数据库集成 (PostgreSQL)
- 单元测试和集成测试
- 代码质量检查
- 安全扫描

## 📁 项目结构

```
python-app/
├── .github/workflows/           # GitHub Actions工作流
│   └── ci.yml                   # CI/CD流水线配置
├── src/                         # 源代码目录
│   ├── app.py                   # Flask应用主文件
│   ├── models.py                # 数据模型
│   ├── routes.py                # API路由
│   └── utils.py                 # 工具函数
├── tests/                       # 测试目录
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   └── conftest.py              # 测试配置
├── requirements.txt             # Python依赖
├── pyproject.toml              # 项目配置
├── Dockerfile                   # Docker镜像配置
├── docker-compose.yml           # 本地开发环境
└── README.md                    # 项目文档
```

## 🚀 快速开始

### 1. 本地开发

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行应用
python src/app.py

# 运行测试
pytest tests/
```

### 2. 使用Docker运行

```bash
# 构建镜像
docker build -t python-app:latest .

# 运行容器
docker run -p 5000:5000 python-app:latest
```

### 3. 使用Docker Compose运行完整环境

```bash
# 启动所有服务 (应用 + 数据库 + Redis)
docker-compose up
```

## 🔧 CI/CD配置

### GitHub Actions工作流

本项目使用GitHub Actions进行CI/CD，包含以下阶段：

1. **代码质量检查**
   - 代码格式化 (black)
   - 代码检查 (flake8)
   - 类型检查 (mypy)

2. **单元测试**
   - 使用pytest运行测试
   - 生成覆盖率报告
   - 上传测试结果

3. **集成测试**
   - 使用Testcontainers运行数据库测试
   - API端点测试

4. **安全扫描**
   - 依赖漏洞检查
   - 代码安全分析

5. **构建和打包**
   - 构建Docker镜像
   - 推送到容器注册表

6. **部署**
   - 部署到开发环境 (自动)
   - 部署到生产环境 (手动审批)

### 手动触发部署

```bash
# 触发开发环境部署
git push origin develop

# 触发生产环境部署 (需要审批)
git push origin main
```

## 📊 监控和日志

### 应用监控

- **健康检查**: `GET /health`
- **指标端点**: `GET /metrics` (Prometheus格式)
- **就绪检查**: `GET /ready`

### 日志配置

应用配置了结构化日志 (JSON格式)，包含：
- 请求ID跟踪
- 用户上下文
- 性能指标

## 🔐 安全配置

### 安全最佳实践

1. **依赖安全**
   - 使用requirements.txt固定版本
   - 定期运行`pip-audit`检查漏洞
   - 使用Snyk进行持续安全扫描

2. **应用安全**
   - 输入验证和清理
   - SQL注入防护
   - XSS防护
   - CORS配置

3. **容器安全**
   - 使用非root用户运行
   - 只读文件系统
   - 最小化基础镜像

## 📈 性能优化

### 应用性能

- 数据库连接池
- Redis缓存
- GZIP压缩
- 静态文件CDN

### 构建优化

- 多阶段Docker构建
- 构建缓存利用
- 并行测试执行

## 🤝 贡献指南

### 开发流程

1. 从`develop`分支创建功能分支
2. 开发完成后创建Pull Request
3. CI流水线自动运行测试和检查
4. 代码审查通过后合并到`develop`
5. 定期从`develop`合并到`main`进行发布

### 代码规范

- 遵循PEP 8代码风格
- 使用类型注解
- 编写单元测试
- 更新文档

## 📚 相关资源

- [Flask官方文档](https://flask.palletsprojects.com/)
- [Pytest文档](https://docs.pytest.org/)
- [Docker官方文档](https://docs.docker.com/)
- [GitHub Actions文档](https://docs.github.com/actions)
- [Kubernetes文档](https://kubernetes.io/docs/)

## 🆘 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查环境变量配置
   - 验证网络连接
   - 检查数据库服务状态

2. **测试失败**
   - 检查依赖版本
   - 验证测试数据
   - 查看测试日志

3. **构建失败**
   - 检查Dockerfile语法
   - 验证基础镜像可用性
   - 查看构建日志

### 获取帮助

- 查看应用日志: `docker logs <container_id>`
- 检查服务状态: `docker-compose ps`
- 调试API: 使用Postman或curl测试端点