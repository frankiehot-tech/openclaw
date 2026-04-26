# MAREF沙箱环境

基于64卦状态系统的自适应演化沙箱环境，支持多种演化策略和实时监控。

## 功能特性

- **64卦状态系统**: 6位二进制表示64种状态，每个位对应质量维度
- **自适应演化**: 支持贪心策略、模拟退火、遗传算法、多目标优化
- **RESTful API**: 完整的HTTP API接口，支持状态查询、演化控制
- **Python SDK**: 官方Python客户端，简化集成开发
- **实时监控**: 状态转换跟踪、性能指标收集、约束违规检测
- **生产就绪**: Docker容器化、健康检查、日志记录、部署脚本

## 快速开始

### 使用Docker Compose（推荐）

```bash
# 克隆仓库
git clone <repository-url>
cd maref-sandbox

# 启动服务
docker-compose up -d

# 验证服务
curl http://localhost:5001/health
```

### 使用Python直接运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动API服务器
python maref_api.py

# 在新终端中运行SDK示例
python maref_sdk.py
```

### 使用部署脚本

```bash
# 给予执行权限
chmod +x deploy.sh

# 运行部署脚本
./deploy.sh
```

## API参考

### 健康检查
```http
GET /health
```

### 获取当前状态
```http
GET /sandbox/state
```

响应示例:
```json
{
  "current_state": "010101",
  "quality_score": 7.5,
  "stability_index": 0.85,
  "hetu_state": "AST_PARSED",
  "timestamp": 1776643414.674356
}
```

### 启动演化
```http
POST /sandbox/evolve
Content-Type: application/json

{
  "target_quality": 8.0,
  "max_iterations": 100,
  "strategy": "greedy"
}
```

### 获取任务状态
```http
GET /sandbox/tasks/{task_id}
```

### 重置沙箱
```http
POST /sandbox/reset
```

### 获取约束设置
```http
GET /sandbox/constraints
```

### 获取可用策略
```http
GET /sandbox/strategies
```

## Python SDK使用

```python
from maref_sdk import SandboxClient, EvolutionStrategy

# 创建客户端
client = SandboxClient(base_url="http://localhost:5001")

# 健康检查
health = client.health_check()
print(f"服务状态: {health['status']}")

# 获取当前状态
state = client.get_state()
print(f"当前状态: {state.current_state}, 质量: {state.quality_score:.2f}")

# 启动同步演化
result = client.evolve(
    target_quality=8.5,
    max_iterations=50,
    strategy=EvolutionStrategy.SIMULATED_ANNEALING,
    timeout=30
)
print(f"演化成功: {result.success}")
print(f"最终质量: {result.final_quality:.2f}")

# 启动异步演化
task_id = client.evolve_async(
    target_quality=7.0,
    max_iterations=30
)

# 等待任务完成
result = client.wait_for_task(task_id, timeout=60)
```

## 演化策略

### 1. 贪心策略 (Greedy)
选择立即质量提升最大的状态转换。

### 2. 模拟退火 (Simulated Annealing)
允许暂时质量下降以跳出局部最优解。

### 3. 遗传算法 (Genetic)
使用遗传算法优化多维度质量，支持种群进化。

### 4. 多目标优化 (Multi-Objective)
同时优化质量、稳定性和多样性三个目标。

## 系统架构

```
MAREF沙箱环境
├── API服务层 (Flask)
├── 业务逻辑层 (SandboxManager)
│   ├── 状态管理器 (IntegratedHexagramStateManager)
│   ├── 演化引擎 (EvolutionEngine)
│   ├── 反馈控制器 (PIDController)
│   └── 监控系统 (SandboxMonitor)
├── 数据访问层
│   ├── 卦象缓存 (HexagramCache)
│   └── 河图-卦象映射 (HetuHexagramAdapter)
└── 客户端SDK
```

## 生产部署

### Docker部署
```bash
# 构建镜像
docker build -t maref-sandbox:latest .

# 运行容器
docker run -d \
  --name maref-sandbox \
  -p 5001:5001 \
  -v $(pwd)/sandbox_monitor_report.json:/app/sandbox_monitor_report.json \
  --restart unless-stopped \
  maref-sandbox:latest
```

### Kubernetes部署
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: maref-sandbox
spec:
  replicas: 1
  selector:
    matchLabels:
      app: maref-sandbox
  template:
    metadata:
      labels:
        app: maref-sandbox
    spec:
      containers:
      - name: maref-sandbox
        image: maref-sandbox:latest
        ports:
        - containerPort: 5001
        volumeMounts:
        - name: config-volume
          mountPath: /app/sandbox_monitor_report.json
          subPath: sandbox_monitor_report.json
      volumes:
      - name: config-volume
        configMap:
          name: maref-config
```

### 监控指标
- **API响应时间**: 平均 < 0.5秒
- **演化性能**: 平均演化时间 < 2.0秒
- **系统稳定性**: 约束违规率 < 5%
- **服务质量**: 健康检查通过率 100%

## 开发指南

### 运行测试
```bash
# 单元测试
python -m pytest test_maref_api_unit.py -v

# 集成测试
python test_integration_system.py

# 端到端测试
python test_end_to_end.py

# 策略测试
python test_evolution_strategies.py
```

### 添加新演化策略
1. 在 `evolution_strategies.py` 中创建新策略类
2. 实现 `select_best_transition` 方法
3. 在 `sandbox_manager.py` 中注册策略
4. 在 `maref_api.py` 中更新策略列表
5. 编写测试用例

### 性能优化
- **卦象缓存**: 预计算汉明距离、最短路径
- **异步评估**: 后台执行质量评估
- **监控优化**: 限制历史数据大小

## 故障排除

### 常见问题

**Q: API服务无法启动**
```
A: 检查端口5001是否被占用，或修改maref_api.py中的端口号
```

**Q: 演化过程耗时过长**
```
A: 调整max_iterations参数，或选择更高效的策略（如贪心策略）
```

**Q: 状态转换被拒绝**
```
A: 检查约束设置，特别是max_hamming_distance和max_transition_rate
```

### 日志查看
```bash
# Docker容器日志
docker logs maref-sandbox

# 应用日志文件
tail -f maref_sandbox.log
```

## 技术支持

- **问题反馈**: [GitHub Issues](https://github.com/openclaw/maref/issues)
- **文档**: [项目Wiki](https://github.com/openclaw/maref/wiki)
- **API参考**: [在线文档](https://openclaw.github.io/maref/api/)

## 许可证

MIT License