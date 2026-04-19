# 监控配置指南

## 概述
本文档详细介绍Athena队列系统的监控配置，包括监控组件、告警规则、仪表板使用和运维实践。

## 监控架构

### 监控组件

#### 1. 监控仪表板 (Queue Monitor Dashboard)
- **文件**: `queue_monitor_dashboard.py`
- **端口**: 5002
- **功能**: 
  - 实时显示队列状态和任务进度
  - 提供API接口获取监控数据
  - 显示告警和历史趋势
- **启动命令**: `python3 queue_monitor_dashboard.py`
- **访问地址**: http://localhost:5002

#### 2. 监控守护进程 (Two-Minute Queue Monitor)
- **文件**: `scripts/two_minute_queue_monitor.py`
- **运行频率**: 每2分钟
- **功能**:
  - 检查队列状态变化
  - 生成即时告警
  - 收集性能指标
- **进程管理**: 作为守护进程持续运行

#### 3. 队列监控器 (Queue Monitor Daemon)
- **文件**: `scripts/queue_monitor.py`
- **启动命令**: `python3 scripts/queue_monitor.py --daemon --config scripts/queue_monitor_config.yaml`
- **功能**:
  - 持续监控队列状态
  - 执行自定义监控检查
  - 与外部监控系统集成

### 监控配置

#### 监控计划配置
**文件**: `24_hour_monitoring_plan.json`
```json
{
  "duration_hours": 24,
  "monitoring_checks": [
    {"check": "队列状态监控", "frequency": "每2分钟", "metric": "queue_status"},
    {"check": "任务执行进度", "frequency": "每5分钟", "metric": "progress_percent"},
    {"check": "系统资源使用", "frequency": "每10分钟", "metric": "cpu_memory_disk"},
    {"check": "依赖阻塞检测", "frequency": "每15分钟", "metric": "dependency_blocks"},
    {"check": "错误率监控", "frequency": "每30分钟", "metric": "error_rate"},
    {"check": "吞吐量统计", "frequency": "每小时", "metric": "tasks_per_hour"}
  ]
}
```

#### 监控配置文件
**文件**: `scripts/queue_monitor_config.yaml`
包含详细的监控规则和阈值配置。

### 监控指标

#### 队列状态指标
1. **queue_status**: 队列当前状态 (running, dependency_blocked, empty, failed, manual_hold)
2. **status_counts**: 任务状态分布 (pending, running, completed, failed, manual_hold)
3. **current_item_id**: 当前正在执行的任务ID
4. **pause_reason**: 队列暂停原因

#### 任务执行指标
1. **progress_percent**: 任务执行进度百分比
2. **execution_time**: 任务执行时间
3. **error_count**: 任务错误计数
4. **retry_count**: 任务重试次数

#### 系统资源指标
1. **cpu_usage**: CPU使用率百分比
2. **memory_usage**: 内存使用量 (MB)
3. **disk_usage**: 磁盘使用率
4. **process_count**: 相关进程数量

#### 性能指标
1. **throughput**: 每小时处理的任务数量
2. **success_rate**: 任务成功率
3. **average_latency**: 平均任务延迟
4. **dependency_resolution_time**: 依赖解析时间

## 告警配置

### 告警规则

#### 即时告警 (Immediate Alerts)
当以下条件触发时立即发送告警：

1. **队列状态告警**:
   - `queue_status = "dependency_blocked"` - 队列因依赖阻塞停止
   - `queue_status = "failed"` - 队列整体失败
   - `queue_status = "manual_hold"` 超过1小时 - 手动暂停时间过长

2. **系统资源告警**:
   - `system_cpu > 90%` - CPU使用率超过90%
   - `system_memory > 90%` - 内存使用率超过90%
   - `disk_usage > 95%` - 磁盘使用率超过95%

3. **任务执行告警**:
   - 单个任务失败超过3次
   - 任务执行时间超过1小时
   - 任务进度长时间无变化 (30分钟)

#### 阈值配置
```yaml
alert_thresholds:
  cpu_usage: 90  # CPU使用率阈值(%)
  memory_usage: 90  # 内存使用率阈值(%)
  disk_usage: 95  # 磁盘使用率阈值(%)
  queue_blocked_hours: 1  # 队列阻塞小时数阈值
  task_failure_count: 3  # 任务失败次数阈值
  task_timeout_hours: 1  # 任务超时小时数阈值
```

#### 告警聚合
- **相同告警合并**: 5分钟内相同类型的告警合并为一条
- **告警升级**: 同一告警持续1小时未解决，升级为紧急告警
- **告警抑制**: 维护期间可以临时抑制告警

### 告警通知渠道

#### 当前支持的渠道
1. **控制台输出**: 所有告警在控制台显示
2. **日志文件**: 告警记录到监控日志文件
3. **仪表板显示**: 实时在监控仪表板显示告警

#### 计划支持的渠道
1. **电子邮件通知**: 发送告警邮件到指定邮箱
2. **Slack通知**: 发送告警到Slack频道
3. **Webhook通知**: 通过Webhook发送告警到外部系统

### 告警验证和测试

#### 告警测试方法
1. **手动触发测试**:
   ```bash
   # 模拟队列阻塞
   python3 scripts/test_alerts.py --test dependency_blocked
   
   # 模拟高CPU使用率
   python3 scripts/test_alerts.py --test high_cpu
   ```

2. **自动测试套件**:
   - 定期运行告警测试确保告警系统正常工作
   - 测试所有告警规则和通知渠道

#### 告警准确性验证
1. **误报率监控**: 统计告警误报率，目标<5%
2. **漏报率监控**: 统计重要事件漏报率，目标<1%
3. **响应时间监控**: 告警生成到通知的时间，目标<1分钟

## 监控仪表板使用指南

### 仪表板界面

#### 主界面
1. **队列状态面板**: 显示当前队列状态和任务分布
2. **系统资源面板**: 显示CPU、内存、磁盘使用情况
3. **告警面板**: 显示当前活跃告警和历史告警
4. **性能趋势面板**: 显示关键指标的历史趋势

#### API接口
1. **状态接口**: `GET /api/status` - 获取队列状态
2. **告警接口**: `GET /api/alerts` - 获取告警列表
3. **指标接口**: `GET /api/metrics` - 获取性能指标
4. **历史接口**: `GET /api/history` - 获取历史数据

### 仪表板配置

#### 启动参数
```bash
# 启动监控仪表板
python3 queue_monitor_dashboard.py \
  --port 5002 \
  --log-level INFO \
  --data-dir ./monitoring_data \
  --refresh-interval 30
```

#### 环境变量配置
```bash
export MONITORING_PORT=5002
export MONITORING_LOG_LEVEL=INFO
export MONITORING_DATA_RETENTION_DAYS=30
export MONITORING_ALERT_ENABLED=true
```

### 仪表板维护

#### 数据管理
1. **数据保留策略**: 监控数据保留30天
2. **数据清理**: 自动清理过期数据
3. **数据备份**: 定期备份重要监控数据

#### 性能优化
1. **缓存机制**: 缓存频繁访问的数据
2. **数据聚合**: 对历史数据进行聚合减少存储
3. **查询优化**: 优化数据库查询性能

## 监控运维实践

### 日常监控任务

#### 1. 监控系统健康检查
```bash
# 检查监控进程状态
./scripts/check_monitoring_health.sh

# 检查监控数据收集
./scripts/check_monitoring_data.sh

# 检查告警系统
./scripts/check_alert_system.sh
```

#### 2. 监控数据审核
- **每日审核**: 检查前一天的监控数据和告警
- **每周审核**: 分析监控趋势和性能变化
- **每月审核**: 评估监控系统效果和改进需求

#### 3. 监控配置维护
- **配置版本控制**: 监控配置使用Git管理
- **配置变更审核**: 所有配置变更需要审核
- **配置回滚机制**: 支持快速回滚到之前版本

### 监控系统故障处理

#### 常见故障及处理
1. **监控进程崩溃**:
   - 症状: 仪表板无法访问，无监控数据
   - 处理: 重启监控进程，检查日志

2. **数据收集失败**:
   - 症状: 监控数据缺失或过时
   - 处理: 检查数据收集脚本，修复配置

3. **告警系统失效**:
   - 症状: 无告警或告警延迟
   - 处理: 检查告警规则，测试告警渠道

#### 故障恢复流程
1. **识别故障**: 通过健康检查或用户报告识别故障
2. **诊断原因**: 检查日志、配置和系统状态
3. **实施修复**: 应用修复措施
4. **验证恢复**: 验证监控系统恢复正常
5. **记录故障**: 记录故障详情和处理过程

### 监控系统优化

#### 性能优化
1. **数据存储优化**: 使用更高效的数据存储格式
2. **查询优化**: 优化监控数据查询性能
3. **告警计算优化**: 优化告警规则计算性能

#### 功能增强
1. **自定义监控**: 支持用户自定义监控指标
2. **预测性监控**: 基于历史数据的预测性告警
3. **自动化修复**: 监控系统自动触发修复动作

## 监控验证和测试

### 24小时监控验证计划

#### 验证目标
1. **监控系统准确性**: 验证监控数据准确反映系统状态
2. **告警系统可靠性**: 验证告警及时准确触发
3. **系统稳定性**: 验证监控系统24小时稳定运行

#### 验证步骤
1. **初始状态检查**: 检查监控系统初始状态
2. **监控检查执行**: 按照监控计划执行检查
3. **告警测试**: 测试各种告警场景
4. **性能验证**: 验证监控系统性能表现
5. **结果分析**: 分析验证结果，提出改进建议

#### 验证指标
1. **监控数据准确性**: >95%
2. **告警准确率**: >95%
3. **系统可用性**: >99.9%
4. **数据收集完整性**: >98%

### 监控测试套件

#### 单元测试
```bash
# 运行监控单元测试
python3 -m pytest tests/monitoring/test_queue_monitor.py
python3 -m pytest tests/monitoring/test_alert_system.py
```

#### 集成测试
```bash
# 运行监控集成测试
./scripts/run_monitoring_integration_tests.sh
```

#### 端到端测试
```bash
# 运行监控端到端测试
./scripts/run_monitoring_e2e_tests.sh
```

## 最佳实践

### 监控配置最佳实践
1. **分级告警**: 根据严重程度分级告警
2. **智能聚合**: 相关告警智能聚合减少噪音
3. **上下文信息**: 告警包含足够的上下文信息
4. **自动化响应**: 常见问题自动化响应

### 监控运维最佳实践
1. **定期审查**: 定期审查监控配置和告警规则
2. **容量规划**: 基于监控数据进行容量规划
3. **持续改进**: 基于监控反馈持续改进系统
4. **知识共享**: 监控经验和知识团队共享

### 监控系统安全最佳实践
1. **访问控制**: 控制监控数据访问权限
2. **数据加密**: 敏感监控数据加密存储
3. **审计日志**: 记录监控系统访问和操作
4. **安全更新**: 定期更新监控系统安全补丁

## 故障排除指南

### 常见问题

#### 1. 监控仪表板无法访问
- **可能原因**: 端口冲突、进程崩溃、权限问题
- **解决方法**: 
  1. 检查端口5002是否被占用 `lsof -i :5002`
  2. 重启监控仪表板进程
  3. 检查日志文件中的错误信息

#### 2. 监控数据不更新
- **可能原因**: 数据收集进程停止、配置错误、存储问题
- **解决方法**:
  1. 检查数据收集进程状态
  2. 验证监控配置文件
  3. 检查存储空间和权限

#### 3. 告警不触发
- **可能原因**: 告警规则配置错误、告警系统故障、阈值设置不当
- **解决方法**:
  1. 测试告警规则
  2. 检查告警系统日志
  3. 验证告警阈值设置

#### 4. 监控系统性能问题
- **可能原因**: 数据量过大、查询优化不足、资源不足
- **解决方法**:
  1. 优化数据存储和查询
  2. 增加系统资源
  3. 实施数据归档策略

### 诊断工具

#### 内置诊断工具
```bash
# 监控系统诊断
python3 scripts/diagnose_monitoring.py

# 告警系统诊断
python3 scripts/diagnose_alerts.py

# 性能诊断
python3 scripts/diagnose_performance.py
```

#### 外部诊断工具
1. **系统监控工具**: htop, iostat, vmstat
2. **网络诊断工具**: netstat, curl, telnet
3. **日志分析工具**: grep, awk, jq

### 故障恢复检查清单
- [ ] 确认监控系统所有组件运行正常
- [ ] 验证监控数据收集正常
- [ ] 测试告警系统功能正常
- [ ] 检查监控仪表板可访问
- [ ] 验证历史数据完整性
- [ ] 确认监控配置正确
- [ ] 检查系统资源使用正常

---

*文档版本: 1.1*
*最后更新: 2026-04-18*
*维护者: Athena监控团队*