# Kubernetes部署配置

这个目录包含Python Flask应用的Kubernetes部署配置文件。

## 目录结构

```
k8s/
├── staging/              # 预生产环境配置
│   ├── deployment.yaml   # 部署和服务配置
│   └── config.yaml       # ConfigMap和Secret配置
├── production/           # 生产环境配置
│   ├── deployment.yaml   # 部署和服务配置
│   └── config.yaml       # ConfigMap和Secret配置
├── namespace.yaml        # 命名空间定义
└── README.md            # 本文件
```

## 部署步骤

### 1. 创建命名空间

```bash
# 应用所有命名空间配置
kubectl apply -f namespace.yaml
```

### 2. 部署到Staging环境

```bash
# 切换到staging目录
cd k8s/staging

# 应用ConfigMap和Secret
kubectl apply -f config.yaml

# 应用Deployment和Service
kubectl apply -f deployment.yaml

# 检查部署状态
kubectl -n staging get all
kubectl -n staging get pods
kubectl -n staging logs -f deployment/python-app
```

### 3. 部署到Production环境

```bash
# 切换到production目录
cd k8s/production

# 先更新Secret中的实际值
# 注意：production/config.yaml中的Secret值是base64编码的示例
# 实际使用时应该替换为真实值

# 应用ConfigMap和Secret
kubectl apply -f config.yaml

# 应用Deployment和Service
kubectl apply -f deployment.yaml

# 检查部署状态
kubectl -n production get all
kubectl -n production get pods
kubectl -n production logs -f deployment/python-app
```

## 配置说明

### Secret管理

生产环境的Secret应该使用安全的密钥管理方案：

1. **本地加密**：使用Sealed Secrets或SOPS
2. **云服务**：使用AWS Secrets Manager、GCP Secret Manager、Azure Key Vault
3. **外部存储**：使用Hashicorp Vault

示例使用Sealed Secrets：

```bash
# 创建SealedSecret
kubectl create secret generic app-secrets \
  --from-literal=database-url="postgresql://user:pass@host:5432/db" \
  --dry-run=client -o yaml \
  | kubeseal --format yaml --cert my-cert.pem \
  > sealed-secret.yaml
```

### 配置更新

更新配置后重新部署：

```bash
# 更新ConfigMap
kubectl -n staging apply -f config.yaml

# 重启Deployment以应用新配置
kubectl -n staging rollout restart deployment/python-app

# 查看更新状态
kubectl -n staging rollout status deployment/python-app
```

### 回滚部署

如果部署出现问题，可以回滚到上一个版本：

```bash
# 查看部署历史
kubectl -n staging rollout history deployment/python-app

# 回滚到上一个版本
kubectl -n staging rollout undo deployment/python-app

# 回滚到特定版本
kubectl -n staging rollout undo deployment/python-app --to-revision=2
```

## 监控和日志

### 监控配置

部署包含Prometheus监控注解：

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "5000"
  prometheus.io/path: "/metrics"
```

### 日志收集

建议配置集中式日志收集：

1. **Fluentd**：作为DaemonSet运行
2. **Loki**：轻量级日志聚合
3. **ELK Stack**：Elasticsearch, Logstash, Kibana

### 健康检查

应用配置了三种健康检查：

1. **Startup Probe**：应用启动检查
2. **Liveness Probe**：应用存活检查
3. **Readiness Probe**：应用就绪检查

## 自动扩缩容

配置了Horizontal Pod Autoscaler（HPA），基于CPU、内存使用率和自定义指标自动扩缩容。

### 查看HPA状态

```bash
kubectl -n staging get hpa
kubectl -n staging describe hpa python-app-hpa
```

### 自定义指标

如果需要基于自定义指标扩缩容，需要安装Metrics Server和Prometheus Adapter：

```bash
# 安装Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 安装Prometheus Adapter
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus-adapter prometheus-community/prometheus-adapter
```

## 网络策略

### Ingress配置

生产环境配置了Ingress资源，需要安装Ingress控制器：

```bash
# 安装NGINX Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

# 安装Cert-Manager用于TLS证书
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

### 服务网格

如果需要服务网格功能，可以配置Istio：

```yaml
annotations:
  sidecar.istio.io/inject: "true"
```

## 安全最佳实践

### Pod安全

1. **非root用户**：使用`runAsNonRoot: true`和`runAsUser: 1000`
2. **只读根文件系统**：使用`readOnlyRootFilesystem: true`
3. **权限降级**：使用`capabilities.drop: ["ALL"]`
4. **资源限制**：设置CPU和内存限制

### 网络策略

限制Pod间的网络访问：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: python-app-network-policy
spec:
  podSelector:
    matchLabels:
      app: python-app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 5000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
```

## 故障排除

### 常见问题

1. **镜像拉取失败**：检查镜像标签和拉取密钥
2. **健康检查失败**：检查应用是否正常运行
3. **资源不足**：检查节点资源和资源限制
4. **配置错误**：检查ConfigMap和Secret值

### 调试命令

```bash
# 查看Pod详情
kubectl describe pod <pod-name>

# 查看Pod日志
kubectl logs <pod-name>

# 进入Pod调试
kubectl exec -it <pod-name> -- /bin/sh

# 查看事件
kubectl get events --sort-by='.lastTimestamp'

# 查看资源使用
kubectl top pods
kubectl top nodes
```

## 持续部署

可以将这些配置集成到CI/CD流水线中：

```yaml
# GitHub Actions示例
- name: Deploy to Kubernetes
  run: |
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/${{ env.K8S_ENV }}/config.yaml
    kubectl apply -f k8s/${{ env.K8S_ENV }}/deployment.yaml
    kubectl rollout status deployment/python-app -n ${{ env.K8S_ENV }}
```