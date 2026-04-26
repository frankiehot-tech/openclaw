# 云服务MCP框架 (Cloud Service MCP Framework)

为AI Assistant提供统一的云服务操作接口，支持AWS、Docker、Kubernetes、Serverless和云存储服务。

## 🚀 快速开始

### 安装

```bash
# 安装云服务MCP包
cd /Users/frankie/claude-code-setup/stage2/cloud-services/cloud-mcp
pip install -e .

# 或使用开发模式
pip install -e .
```

### 配置云服务凭据

```bash
# AWS凭据
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

# Kubernetes配置
export KUBECONFIG="~/.kube/config"

# Docker配置
export DOCKER_HOST="unix:///var/run/docker.sock"

# MinIO配置（可选）
export MINIO_ENDPOINT="http://localhost:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
```

### 启动MCP服务器

```bash
# 启动AWS MCP服务器
cloud-mcp-aws

# 启动Docker MCP服务器  
cloud-mcp-docker

# 启动Kubernetes MCP服务器
cloud-mcp-kubernetes

# 启动Serverless MCP服务器
cloud-mcp-serverless

# 启动云存储MCP服务器
cloud-mcp-storage
```

## 📋 支持的云服务

### 1. AWS云服务
- **EC2实例管理**: 启动、停止、列出实例
- **S3存储操作**: 桶管理、对象上传下载
- **RDS数据库管理**: 数据库实例操作
- **Lambda函数**: 函数部署、调用、管理
- **CloudFormation**: 堆栈部署和管理

### 2. Docker容器服务
- **容器管理**: 运行、停止、删除容器
- **镜像管理**: 构建、推送、拉取镜像
- **网络管理**: 创建、管理网络
- **卷管理**: 数据卷操作
- **Compose服务**: Docker Compose编排

### 3. Kubernetes集群服务
- **集群管理**: 节点、命名空间管理
- **部署管理**: 部署创建、伸缩、更新
- **服务发现**: 服务创建、端点管理
- **配置管理**: ConfigMap、Secret管理
- **日志查询**: Pod日志获取

### 4. Serverless框架
- **函数部署**: 无服务器函数部署
- **服务管理**: Serverless服务管理
- **函数调用**: 同步/异步函数调用
- **多提供商**: AWS Lambda、Azure Functions、Google Cloud Functions

### 5. 云存储服务
- **S3兼容存储**: AWS S3、MinIO
- **桶管理**: 创建、删除、列出存储桶
- **对象操作**: 上传、下载、删除对象
- **预签名URL**: 生成临时访问URL
- **跨域配置**: CORS策略管理

## 🛠️ 配置AI Assistant MCP服务器

在AI Assistant配置文件中添加MCP服务器：

```json
{
  "mcpServers": {
    "aws": {
      "command": "cloud-mcp-aws",
      "env": {
        "AWS_ACCESS_KEY_ID": "your-access-key",
        "AWS_SECRET_ACCESS_KEY": "your-secret-key"
      }
    },
    "docker": {
      "command": "cloud-mcp-docker"
    },
    "kubernetes": {
      "command": "cloud-mcp-kubernetes",
      "env": {
        "KUBECONFIG": "~/.kube/config"
      }
    },
    "serverless": {
      "command": "cloud-mcp-serverless"
    },
    "storage": {
      "command": "cloud-mcp-storage"
    }
  }
}
```

## 🔧 可用工具列表

### 通用工具
所有云服务都支持以下通用工具：

| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `list_resources` | 列出云服务资源 | `resource_type`, `filters` |
| `create_resource` | 创建云服务资源 | `resource_type`, `name`, `spec`, `tags` |
| `delete_resource` | 删除云服务资源 | `resource_type`, `resource_id`, `force` |
| `describe_resource` | 描述资源详情 | `resource_type`, `resource_id` |

### AWS特定工具
| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `aws_deploy_stack` | 部署CloudFormation堆栈 | `stack_name`, `template_body`, `parameters` |
| `aws_invoke_lambda` | 调用Lambda函数 | `function_name`, `payload`, `invocation_type` |
| `aws_upload_to_s3` | 上传文件到S3 | `bucket`, `key`, `file_path`, `content_type` |

### Docker特定工具
| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `docker_build_image` | 构建Docker镜像 | `dockerfile`, `image_name`, `build_args` |
| `docker_run_container` | 运行Docker容器 | `image`, `name`, `ports`, `environment` |
| `docker_compose_up` | 启动Docker Compose服务 | `compose_file`, `services` |

### Kubernetes特定工具
| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `k8s_apply_yaml` | 应用Kubernetes YAML配置 | `yaml_content`, `namespace` |
| `k8s_scale_deployment` | 伸缩Kubernetes部署 | `deployment`, `replicas`, `namespace` |
| `k8s_get_logs` | 获取Kubernetes Pod日志 | `pod`, `container`, `namespace`, `tail_lines` |

### Serverless特定工具
| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `serverless_deploy` | 部署Serverless应用 | `service_name`, `provider`, `functions`, `resources` |
| `serverless_invoke` | 调用Serverless函数 | `function`, `data`, `path`, `method` |

### 云存储特定工具
| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `storage_list_buckets` | 列出存储桶 | `prefix` |
| `storage_list_objects` | 列出存储对象 | `bucket`, `prefix`, `delimiter` |
| `storage_presigned_url` | 生成预签名URL | `bucket`, `key`, `expires_in`, `method` |

## 📖 使用示例

### 示例1: 列出AWS EC2实例
```python
# 通过AI Assistant调用
result = await client.call_tool("aws", "list_resources", {
    "resource_type": "ec2_instances",
    "filters": {"instance-state-name": "running"}
})
```

### 示例2: 构建Docker镜像
```python
result = await client.call_tool("docker", "docker_build_image", {
    "dockerfile": "FROM nginx:alpine\nCOPY . /usr/share/nginx/html",
    "image_name": "my-webapp:latest"
})
```

### 示例3: 部署到Kubernetes
```python
result = await client.call_tool("kubernetes", "k8s_apply_yaml", {
    "yaml_content": """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
""",
    "namespace": "default"
})
```

### 示例4: 部署Serverless函数
```python
result = await client.call_tool("serverless", "serverless_deploy", {
    "service_name": "my-api",
    "provider": "aws",
    "functions": {
        "hello": {
            "handler": "handler.hello",
            "events": [{"http": {"path": "hello", "method": "get"}}]
        }
    }
})
```

### 示例5: 上传文件到云存储
```python
result = await client.call_tool("storage", "storage_list_buckets", {})

# 上传文件
result = await client.call_tool("storage", "create_resource", {
    "resource_type": "object",
    "name": "data/backup.zip",
    "spec": {
        "bucket": "my-backup-bucket",
        "file_path": "/local/path/backup.zip"
    }
})
```

## 🔒 安全考虑

### 凭据管理
- 凭据存储在内存中，不落盘
- 支持环境变量、配置文件、IAM角色多种认证方式
- 凭据传输使用Base64编码（生产环境应使用强加密）

### 权限控制
- 遵循最小权限原则
- 支持细粒度的资源操作权限
- 所有操作都有详细审计日志

### 网络安全
- 支持TLS/SSL加密通信
- 验证服务端证书
- 防止中间人攻击

## 🐛 故障排查

### 常见问题

1. **MCP服务器启动失败**
   ```
   # 检查依赖是否安装
   pip install -r requirements.txt
   
   # 检查Python版本
   python --version  # 需要Python 3.8+
   ```

2. **认证失败**
   ```
   # 检查环境变量
   echo $AWS_ACCESS_KEY_ID
   echo $KUBECONFIG
   
   # 检查配置文件
   ls ~/.aws/credentials
   ls ~/.kube/config
   ```

3. **连接超时**
   ```
   # 检查网络连接
   ping api.aws.amazon.com
   
   # 检查防火墙设置
   # 确保443端口开放
   ```

4. **权限不足**
   ```
   # 检查IAM权限
   # 确保用户有足够权限执行操作
   
   # 检查kubeconfig权限
   kubectl auth can-i create deployments
   ```

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 启动MCP服务器
cloud-mcp-aws --verbose
```

## 📊 性能指标

| 操作类型 | 预期延迟 (P95) | 备注 |
|---------|---------------|------|
| AWS API调用 | < 500ms | 取决于AWS服务响应 |
| Docker容器操作 | < 200ms | 本地操作 |
| Kubernetes部署 | < 2s | 小型应用 |
| Serverless部署 | < 30s | 函数打包上传 |
| 存储操作 | < 100ms | 小文件上传下载 |

## 🔄 版本历史

### v1.0.0 (2026-04-11)
- 初始版本发布
- 支持AWS、Docker、Kubernetes、Serverless、Storage五大云服务
- 统一的工具接口和错误处理
- 完整的文档和示例

## 🤝 贡献指南

1. Fork仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/anthropics/claude-code-setup.git

# 安装开发依赖
pip install -r requirements.txt
pip install -e .

# 运行测试
pytest tests/
```

### 代码规范
- 使用Black代码格式化
- 使用mypy类型检查
- 遵循PEP 8规范
- 添加类型注解

## 📄 许可证

MIT License - 详见LICENSE文件

## 📞 支持

- GitHub Issues: [问题跟踪](https://github.com/anthropics/claude-code-setup/issues)
- 文档: [完整文档](https://github.com/anthropics/claude-code-setup/wiki)
- 邮件: noreply@example.com

## 🙏 致谢

感谢AI Assistant团队和所有贡献者的支持！

---

**提示**: 使用前请确保已配置正确的云服务凭据，并了解相关云服务费用。