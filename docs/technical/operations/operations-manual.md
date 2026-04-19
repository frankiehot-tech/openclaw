# Athena队列系统运维手册

## 系统概述
Athena队列系统是一个基于文件的智能任务队列管理系统，采用契约框架确保系统的可靠性和一致性。

## 核心组件

### 1. 队列运行器 (athena_ai_plan_runner.py)
- **位置**: `/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py`
- **功能**: 主队列处理引擎，负责任务调度、执行、监控
- **启动方式**: `python3 athena_ai_plan_runner.py --queue <队列文件>`

### 2. 智能工作流编排器 (smart_orchestrator.py)
- **位置**: `/Volumes/1TB-M2/openclaw/workflow/smart_orchestrator.py`
- **功能**: 智能路由任务到合适的执行器，支持自适应策略

### 3. 契约框架
- **TaskIdentityContract**: 任务身份规范化
- **ProcessLifecycleContract**: 进程生命周期管理
- **DataQualityContract**: 数据质量管理
- **StateSyncContract**: 状态同步管理

## 日常运维操作

### 队列状态检查
```bash
# 检查队列运行器状态
ps aux | grep athena_ai_plan_runner.py

# 检查队列文件状态
ls -la /Volumes/1TB-M2/openclaw/.openclaw/plan_queue/

# 查看队列运行日志
tail -f /Volumes/1TB-M2/openclaw/.openclaw/queue_runner.log
```

### 队列启动与停止
```bash
# 启动队列运行器
cd /Volumes/1TB-M2/openclaw/scripts
python3 athena_ai_plan_runner.py --queue <队列文件>

# 停止队列运行器
kill -TERM $(cat /Volumes/1TB-M2/openclaw/.openclaw/athena_ai_plan_runner.pid)
```

### 任务管理
```bash
# 查看队列中的任务
python3 scripts/check_queue_status.py --queue <队列文件>

# 手动拉起失败任务
# 通过Web界面或API调用
```

## 监控与告警

### 监控仪表板
- **URL**: `http://localhost:5002`
- **功能**: 队列状态、系统资源、告警信息可视化

### 关键监控指标
1. **队列健康状态**: 检查队列是否正常运行
2. **任务成功率**: 应保持在95%以上
3. **系统资源使用**: CPU < 80%, 内存 < 80%
4. **任务延迟**: P95延迟 < 5秒

### 告警配置
- **队列堵塞告警**: 队列状态长时间处于failed或manual_hold
- **资源告警**: CPU或内存使用率超过阈值
- **任务失败告警**: 连续任务失败超过阈值

## 故障处理

### 常见问题及解决方案

#### 1. 队列状态异常 (failed/manual_hold)
```bash
# 检查队列状态文件
cat /Volumes/1TB-M2/openclaw/.openclaw/plan_queue/<队列文件>.json | jq '.queue_status'

# 使用修复脚本
python3 scripts/fix_web_queue_mismatch.py
python3 scripts/final_queue_fix.py
```

#### 2. 进程崩溃或无响应
```bash
# 检查进程状态
ps aux | grep athena_ai_plan_runner.py

# 重启队列运行器
kill -TERM $(cat /Volumes/1TB-M2/openclaw/.openclaw/athena_ai_plan_runner.pid)
# 等待5秒后重新启动
```

#### 3. 状态不一致 (Web界面与队列文件)
```bash
# 运行状态同步检查
python3 scripts/check_state_consistency.py --all --repair
```

#### 4. 任务积压
```bash
# 检查积压任务数量
python3 scripts/check_queue_status.py --queue <队列文件>

# 临时增加并发数
# 修改配置或手动清理失败任务
```

### 紧急恢复流程
1. **停止问题队列**: 停止有问题的队列运行器
2. **备份数据**: 备份队列文件和配置
3. **运行诊断**: 使用诊断工具分析问题根源
4. **执行修复**: 根据诊断结果运行相应修复脚本
5. **验证恢复**: 验证系统恢复正常
6. **监控观察**: 持续监控确保稳定

## 备份与恢复

### 定期备份
- **队列文件备份**: 每日自动备份到`.openclaw/plan_queue.backup.*`
- **配置备份**: 配置更改时手动备份到`.openclaw/config/`
- **数据备份**: 重要数据定期备份

### 恢复流程
1. **停止服务**: 停止所有相关服务
2. **恢复备份**: 从备份恢复队列文件和配置
3. **验证数据**: 检查恢复的数据完整性
4. **启动服务**: 按顺序启动服务
5. **功能验证**: 验证系统功能正常

## 性能优化

### 系统参数调优
- **并发数调整**: 根据系统负载调整`max_concurrent_tasks`
- **心跳间隔**: 调整进程心跳检测间隔（当前30秒）
- **资源限制**: 设置任务资源使用限制

### 容量规划
- **峰值容量**: 100任务/分钟
- **建议负载**: 50-70任务/分钟（保持余量）
- **扩展建议**: 超过80%持续负载时考虑扩展

## 安全考虑

### 访问控制
- **API认证**: Web接口使用token认证
- **文件权限**: 队列文件仅允许授权用户访问
- **进程隔离**: 不同队列使用独立进程运行

### 审计日志
- **操作审计**: 记录所有关键运维操作
- **变更跟踪**: 跟踪配置和代码变更
- **安全审计**: 定期进行安全审计

## 联系与支持

### 内部支持
- **开发团队**: 系统架构和技术支持
- **运维团队**: 日常运维和故障处理

### 文档资源
- **部署计划**: `engineering_staged_deployment_plan.md`
- **任务计划**: `task_plan.md`
- **审计报告**: `athena_openhuman_engineering_audit_report.md`

---

**文档版本**: 1.0  
**最后更新**: 2026-04-17  
**维护团队**: Athena运维团队