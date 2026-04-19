# Athena队列系统部署指南

## 部署概述
本文档提供Athena队列系统的完整部署指南，包括环境准备、配置、部署、验证和监控。

## 部署前提条件

### 硬件要求
- **CPU**: 4核或以上
- **内存**: 8GB或以上  
- **存储**: 50GB可用空间
- **网络**: 稳定的网络连接

### 软件要求
- **操作系统**: macOS 10.15+, Linux Ubuntu 20.04+
- **Python**: 3.8或以上
- **依赖包**: 参见`requirements.txt`

### 权限要求
- 对部署目录的读写权限
- 网络访问权限（API调用）
- 进程管理权限

## 部署环境准备

### 1. 代码获取
```bash
# 假设代码已克隆到本地
cd /Volumes/1TB-M2/openclaw
```

### 2. 依赖安装
```bash
# 安装Python依赖
pip3 install -r requirements.txt

# 如果requirements.txt不存在，安装核心依赖
pip3 install psutil flask json5 pyyaml
```

### 3. 目录结构准备
```bash
# 创建必要的目录
mkdir -p .openclaw/plan_queue
mkdir -p .openclaw/config
mkdir -p .openclaw/orchestrator
mkdir -p logs
```

## 配置管理

### 基础配置
创建配置文件`.evo/config.yaml`:
```yaml
# 基因管理系统配置
version: 0.1
system: athena_openhuman

# 基因管理设置
gene_management:
  auto_proposal: true
  auto_review: false
  max_gene_depth: 10

# 审核设置
review:
  required_approvals: 1
  auto_escalate_hours: 24

# 执行设置
execution:
  max_concurrent_tasks: 3
  timeout_minutes: 120
```

### 监控配置
创建监控配置文件`queue_monitor_config.yaml`:
```yaml
monitoring:
  enabled: true
  check_interval: 300  # 5分钟
  alert_channels:
    - console
    - log
  
  thresholds:
    queue_stale_minutes: 60
    cpu_warning: 80
    memory_warning: 80
    
  web_dashboard:
    enabled: true
    port: 5002
    host: 0.0.0.0
```

## 系统部署步骤

### 阶段1: 基础服务部署

#### 1.1 启动队列运行器
```bash
cd /Volumes/1TB-M2/openclaw/scripts

# 启动默认队列
python3 athena_ai_plan_runner.py --queue ../.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json

# 或使用后台模式
nohup python3 athena_ai_plan_runner.py --queue <队列文件> > queue_runner.log 2>&1 &
```

#### 1.2 启动Web界面
```bash
# 启动Athena Web Desktop
python3 athena_web_desktop_compat.py &

# 验证Web界面
curl http://localhost:5000/api/athena/queues
```

#### 1.3 启动监控仪表板
```bash
# 启动队列监控仪表板
python3 queue_monitor_dashboard.py &

# 验证仪表板
curl http://localhost:5002/api/status
```

### 阶段2: 契约框架验证

#### 2.1 验证契约框架加载
```bash
# 运行契约框架验证脚本
python3 scripts/verify_contract_framework.py
```

#### 2.2 验证状态同步
```bash
# 验证状态一致性
python3 scripts/check_state_consistency.py --all
```

### 阶段3: 智能工作流验证

#### 3.1 验证智能路由
```bash
# 测试智能路由决策
python3 scripts/test_smart_orchestrator.py
```

#### 3.2 验证执行器映射
```bash
# 验证执行器类型映射
python3 scripts/verify_executor_mapping.py
```

## 部署验证

### 功能验证清单

#### 1. 队列功能验证
- [ ] 队列运行器正常启动
- [ ] 任务可以成功创建
- [ ] 任务状态正确更新
- [ ] 失败任务正确处理

#### 2. Web界面验证
- [ ] Web界面可访问
- [ ] 队列状态正确显示
- [ ] 手动拉起功能正常
- [ ] 认证机制工作正常

#### 3. 监控系统验证
- [ ] 监控仪表板可访问
- [ ] 队列状态监控正常
- [ ] 系统资源监控正常
- [ ] 告警功能正常

#### 4. 契约框架验证
- [ ] TaskIdentityContract工作正常
- [ ] ProcessLifecycleContract工作正常  
- [ ] DataQualityContract工作正常
- [ ] StateSyncContract工作正常

### 性能验证
```bash
# 运行压力测试
python3 scripts/stress_test_athena_queue.py --rate 10 --duration 2

# 验证性能指标
python3 scripts/performance_comparison_report.py
```

### 可靠性验证
```bash
# 运行故障注入测试
python3 scripts/fault_injection_test_fixed.py

# 验证恢复能力
python3 scripts/test_recovery_capability.py
```

## 生产环境切换

### 渐进式迁移策略

#### 批次1: 测试队列迁移 (10%流量)
- 迁移低风险测试队列
- 验证基础功能
- 监控24小时

#### 批次2: 关键业务队列迁移 (30%流量)
- 迁移部分关键队列
- A/B对比验证
- 性能基准对比

#### 批次3: 主要业务队列迁移 (50%流量)
- 迁移主要业务队列
- 全面功能验证
- 性能压力测试

#### 批次4: 全部队列迁移 (80%流量)
- 迁移剩余队列
- 最终验证
- 准备完全切换

#### 批次5: 完全切换 (100%流量)
- 关闭旧系统
- 全面监控
- 部署后优化

### 切换检查清单
- [ ] 质量门禁检查通过
- [ ] 备份和回滚机制验证
- [ ] 监控系统就绪
- [ ] 运维团队就绪
- [ ] 沟通计划就绪

## 监控与维护

### 部署后监控
- **前24小时**: 密集监控，15分钟检查一次
- **第一周**: 每日性能分析，错误率监控
- **长期**: 定期健康检查，容量规划

### 关键监控指标
1. **系统可用性**: 99.9% uptime
2. **任务成功率**: >95%
3. **响应时间**: P95 < 5秒
4. **资源使用**: CPU < 80%, 内存 < 80%

### 告警响应流程
1. **告警触发**: 监控系统检测到异常
2. **初步诊断**: 自动或手动诊断问题
3. **影响评估**: 评估影响范围和严重程度
4. **修复执行**: 执行修复措施
5. **恢复验证**: 验证系统恢复正常
6. **事后分析**: 分析根本原因，防止再次发生

## 故障处理与回滚

### 常见部署问题

#### 1. 部署失败
- **症状**: 服务无法启动
- **原因**: 依赖缺失、配置错误、权限问题
- **解决**: 检查日志，修复问题，重新部署

#### 2. 性能下降
- **症状**: 响应时间增加，吞吐量下降
- **原因**: 资源配置不足，代码问题，外部依赖
- **解决**: 性能分析，资源调整，代码优化

#### 3. 功能异常
- **症状**: 某些功能不正常
- **原因**: 配置错误，数据问题，逻辑错误
- **解决**: 功能测试，配置检查，数据修复

### 回滚流程
1. **决策点**: 确定需要回滚的情况
2. **停止新系统**: 停止新部署的服务
3. **恢复备份**: 从备份恢复数据和配置
4. **启动旧系统**: 启动稳定版本的系统
5. **验证恢复**: 验证系统功能恢复正常
6. **分析原因**: 分析部署失败的根本原因

## 文档与培训

### 文档更新
- 更新系统架构图
- 更新API文档
- 更新故障处理指南
- 更新性能调优指南

### 团队培训
- 运维团队培训
- 开发团队培训
- 用户培训（如适用）

## 附录

### 部署脚本示例
```bash
#!/bin/bash
# deploy_athena.sh

echo "开始部署Athena队列系统..."

# 1. 停止现有服务
echo "停止现有服务..."
pkill -f athena_ai_plan_runner.py
pkill -f athena_web_desktop_compat.py
pkill -f queue_monitor_dashboard.py

# 2. 备份当前状态
echo "备份当前状态..."
backup_dir="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $backup_dir
cp -r .openclaw/plan_queue $backup_dir/
cp -r .openclaw/config $backup_dir/

# 3. 部署新代码
echo "部署新代码..."
# 假设代码已经更新

# 4. 启动服务
echo "启动服务..."
cd scripts
nohup python3 athena_ai_plan_runner.py --queue ../.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json > ../queue_runner.log 2>&1 &
nohup python3 athena_web_desktop_compat.py > ../web_desktop.log 2>&1 &
nohup python3 queue_monitor_dashboard.py > ../monitor_dashboard.log 2>&1 &

echo "部署完成，请验证服务状态..."
```

### 验证脚本示例
```bash
#!/bin/bash
# verify_deployment.sh

echo "验证Athena队列系统部署..."

# 检查服务进程
echo "1. 检查服务进程..."
ps aux | grep -E "(athena_ai_plan_runner|athena_web_desktop|queue_monitor)" | grep -v grep

# 检查端口监听
echo "2. 检查端口监听..."
netstat -an | grep -E "(5000|5002)" | grep LISTEN

# 检查API端点
echo "3. 检查API端点..."
curl -s http://localhost:5000/api/athena/queues | head -5
curl -s http://localhost:5002/api/status | head -5

echo "验证完成..."
```

---

**文档版本**: 1.0  
**最后更新**: 2026-04-17  
**适用环境**: 生产环境  
**维护团队**: Athena部署团队