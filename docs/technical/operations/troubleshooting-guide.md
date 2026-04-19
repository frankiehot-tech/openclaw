# 故障处理手册

## 概述
本文档提供Athena队列系统常见故障的诊断和修复指南，包括问题识别、根本原因分析、修复步骤和预防措施。

## 故障分类

### 1. 队列停滞故障
- **症状**: 队列状态长时间为`dependency_blocked`或`manual_hold`，无任务执行
- **影响**: 任务无法执行，系统吞吐量为零
- **优先级**: 高

### 2. 状态不一致故障
- **症状**: Web界面、队列文件、manifest状态显示不一致
- **影响**: 状态显示错误，可能导致错误决策
- **优先级**: 中

### 3. 依赖管理故障
- **症状**: 任务依赖无法满足，幽灵依赖，循环依赖
- **影响**: 任务无法启动，队列阻塞
- **优先级**: 高

### 4. 进程管理故障
- **症状**: 进程启动失败，僵尸进程，资源泄漏
- **影响**: 任务执行失败，资源浪费
- **优先级**: 中

### 5. 监控系统故障
- **症状**: 监控数据不更新，告警不触发，仪表板无法访问
- **影响**: 系统可观测性降低，问题发现延迟
- **优先级**: 中

## 故障诊断流程

### 通用诊断步骤
1. **症状确认**: 确认故障的具体表现
2. **数据收集**: 收集相关日志、状态文件和配置
3. **根本原因分析**: 分析数据识别根本原因
4. **修复方案制定**: 根据根本原因制定修复方案
5. **修复实施**: 实施修复措施
6. **验证测试**: 验证修复效果
7. **预防措施**: 制定预防措施防止复发

### 诊断工具

#### 内置诊断脚本
```bash
# 队列状态诊断
python3 scripts/diagnose_queue_status.py

# 依赖关系诊断
python3 scripts/diagnose_dependencies.py

# 进程状态诊断
python3 scripts/diagnose_processes.py

# 监控系统诊断
python3 scripts/diagnose_monitoring.py
```

#### 命令行工具
```bash
# 检查队列文件状态
python3 -c "import json; data=json.load(open('.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json')); print(json.dumps(data.get('queue_status'), indent=2))"

# 检查任务计数
python3 -c "import json; data=json.load(open('.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json')); print(json.dumps(data.get('counts'), indent=2))"

# 检查pending任务
python3 -c "import json; data=json.load(open('.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json')); items=data.get('items',{}); pending=[k for k,v in items.items() if v.get('status')=='pending']; print('Pending tasks:', len(pending)); print(pending[:10])"
```

## 常见故障处理

### 故障1: 队列状态持续为dependency_blocked

#### 症状
- 队列状态文件显示`"queue_status": "dependency_blocked"`
- 长时间无任务执行
- 监控系统生成队列阻塞告警

#### 诊断步骤
1. **检查pending任务**:
   ```bash
   python3 scripts/debug_runner_logic.py
   ```

2. **分析依赖关系**:
   - 检查pending任务的依赖关系
   - 识别缺失的依赖任务（幽灵依赖）
   - 检查依赖任务状态是否为completed

3. **检查队列运行器日志**:
   ```bash
   grep -i "dependency" /Volumes/1TB-M2/openclaw/logs/queue_runner.log
   ```

#### 常见原因
1. **幽灵依赖**: 任务依赖于不存在的任务
2. **状态不一致**: 依赖任务状态不是completed
3. **数据损坏**: 队列文件或manifest数据损坏

#### 修复方案

##### 方案A: 幽灵依赖修复
```bash
# 运行幽灵依赖移除脚本
python3 scripts/remove_ghost_dependencies.py
```

**脚本功能**:
1. 识别指向不存在任务的依赖关系
2. 从依赖列表中移除幽灵依赖
3. 更新队列metadata
4. 重新计算队列状态

##### 方案B: 依赖阻塞修复
```bash
# 运行依赖阻塞修复脚本
python3 scripts/fix_dependency_block.py
```

**脚本功能**:
1. 检查manifest中状态为completed但队列中状态为pending的任务
2. 更新这些任务状态为completed（如果依赖已满足）
3. 检查并修复缺失的依赖任务
4. 重新计算队列状态

##### 方案C: 最终队列修复
```bash
# 运行最终队列修复脚本
python3 scripts/final_queue_fix.py
```

**脚本功能**:
1. 直接检查并修复阻塞的依赖链
2. 如果依赖已满足，将任务标记为completed
3. 检查依赖链中的其他任务
4. 设置队列状态为running或empty

#### 验证步骤
1. **检查修复后状态**:
   ```bash
   python3 -c "import json; data=json.load(open('.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json')); print('Queue status:', data.get('queue_status'))"
   ```

2. **检查任务计数**:
   ```bash
   python3 -c "import json; data=json.load(open('.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json')); print('Counts:', json.dumps(data.get('counts'), indent=2))"
   ```

3. **启动队列运行器测试**:
   ```bash
   python3 scripts/athena_ai_plan_runner.py --test-queue
   ```

#### 预防措施
1. **依赖验证**: 在添加任务时验证依赖任务是否存在
2. **状态同步**: 确保manifest和队列状态定期同步
3. **监控告警**: 设置dependency_blocked即时告警
4. **定期审计**: 定期运行依赖关系审计脚本

### 故障2: 状态不一致（Web界面、队列文件、manifest）

#### 症状
- Web界面显示的状态与队列文件不一致
- manifest中任务状态与队列中状态不同
- 任务计数不匹配

#### 诊断步骤
1. **比较状态数据**:
   ```bash
   # 比较manifest和队列状态
   python3 scripts/compare_manifest_queue.py
   ```

2. **检查状态同步机制**:
   - 检查状态更新日志
   - 验证状态同步脚本是否正常运行
   - 检查并发更新冲突

#### 常见原因
1. **并发更新**: 多个进程同时更新状态导致冲突
2. **同步失败**: 状态同步脚本执行失败
3. **数据损坏**: 状态文件损坏或格式错误
4. **手动修改**: 手动修改状态文件导致不一致

#### 修复方案

##### 方案A: 状态同步修复 (推荐)
```bash
# 运行状态同步脚本 (基于24小时监控验证开发)
python3 scripts/sync_queue_manifest_status.py
```

**脚本功能**:
1. 比较manifest和队列文件状态，识别状态不一致的任务
2. 以manifest状态为主同步到队列文件，特别处理pending->failed/completed的状态同步
3. 自动调整队列计数(pending, failed, completed)
4. 如果pending=0且队列状态为no_consumer，自动更新为empty状态
5. 生成详细的状态同步报告

**应用场景**:
- Athena Web Desktop显示待执行任务但队列已清空
- Manifest中任务状态为failed/completed但队列中仍为pending
- 队列状态为no_consumer但实际无pending任务
- 任务计数不一致导致状态显示错误

##### 方案B: 手动状态修复
对于关键任务链，手动修复状态:
```bash
# 手动更新任务状态
python3 scripts/manual_state_fix.py --task openspace_local_adapter_boundary --status completed
```

##### 方案C: 幽灵依赖引起的状态不一致修复
```bash
# 如果状态不一致由幽灵依赖引起，先清理依赖
python3 scripts/remove_ghost_dependencies.py

# 再运行最终队列修复
python3 scripts/final_queue_fix.py
```

#### 验证步骤
1. **验证状态一致性**:
   ```bash
   python3 scripts/verify_state_consistency.py
   ```

2. **检查同步日志**:
   ```bash
   tail -f /Volumes/1TB-M2/openclaw/logs/state_sync.log
   ```

3. **验证no_consumer状态已解决**:
   ```bash
   # 检查队列状态是否从no_consumer更新为empty
   python3 -c "
   import json
   data = json.load(open('.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json'))
   print('队列状态:', data.get('queue_status'))
   print('pause_reason:', data.get('pause_reason', ''))
   "
   ```

4. **验证任务计数正确性**:
   ```bash
   # 检查pending任务数量是否为0
   python3 -c "
   import json
   data = json.load(open('.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json'))
   counts = data.get('counts', {})
   print('任务计数:', counts)
   print('是否有pending任务:', '是' if counts.get('pending', 0) > 0 else '否')
   "
   ```

5. **验证Athena Web Desktop显示**:
   - 访问 http://localhost:8080 查看Web界面
   - 确认无待执行任务显示
   - 确认任务状态与队列状态一致

#### no_consumer状态处理指南
**症状**:
- 队列状态为`no_consumer`
- 队列运行器运行中但无消费者进程
- 有pending任务但未执行

**根本原因**:
1. 队列运行器检测到pending任务但未启动worker进程
2. 状态不一致：manifest中任务状态为failed/completed但队列中为pending
3. 消费者进程启动失败或配置错误

**处理流程**:
1. **检查状态不一致**: 运行`sync_queue_manifest_status.py`同步状态
2. **验证消费者进程**: 检查队列运行器日志，确认worker进程状态
3. **检查资源配置**: 验证系统资源是否充足（内存、CPU）
4. **重启队列运行器**: 如果必要，重启队列运行器进程
5. **监控验证**: 观察状态更新后的队列行为

**预防措施**:
1. **定期状态同步**: 设置定时任务定期运行状态同步脚本
2. **消费者健康检查**: 监控消费者进程健康状态
3. **资源监控**: 确保系统资源充足，避免资源不足导致进程启动失败
4. **错误重试机制**: 实现消费者进程启动失败时的自动重试机制

#### 预防措施
1. **原子性更新**: 实现状态原子性更新机制
2. **状态锁**: 更新状态时加锁防止并发冲突
3. **定期同步**: 定期自动同步manifest和队列状态
4. **变更审计**: 记录所有状态变更操作

### 故障3: 进程启动失败或僵尸进程

#### 症状
- 任务状态为running但实际进程不存在
- 系统中有僵尸进程占用资源
- 进程启动失败错误日志

#### 诊断步骤
1. **检查进程状态**:
   ```bash
   # 检查与队列相关的进程
   ps aux | grep -E "(athena|build|worker)" | grep -v grep
   ```

2. **检查进程日志**:
   ```bash
   grep -i "spawn\|process\|worker" /Volumes/1TB-M2/openclaw/logs/queue_runner.log
   ```

3. **检查僵尸进程**:
   ```bash
   ps aux | grep defunct | grep -v grep
   ```

#### 常见原因
1. **进程启动时序问题**: 先标记状态为running再启动进程，进程启动失败后状态不一致
2. **资源不足**: 内存、CPU、文件描述符不足导致进程启动失败
3. **权限问题**: 进程执行权限不足
4. **配置错误**: 进程启动命令或环境配置错误

#### 修复方案

##### 方案A: 清理僵尸进程
```bash
# 运行僵尸进程清理脚本
python3 scripts/cleanup_zombie_processes.py
```

**脚本功能**:
1. 识别僵尸进程和孤儿进程
2. 安全终止这些进程
3. 更新相关任务状态
4. 生成清理报告

##### 方案B: 进程启动修复
```bash
# 运行进程启动修复脚本
python3 scripts/fix_process_startup.py
```

**脚本功能**:
1. 检查状态为running但无对应进程的任务
2. 重新启动这些任务的进程
3. 或者将这些任务状态重置为pending/failed
4. 优化进程启动时序

#### 验证步骤
1. **验证进程状态**:
   ```bash
   python3 scripts/verify_process_state.py
   ```

2. **检查资源使用**:
   ```bash
   top -n 1 | grep -E "(PID|%CPU|%MEM|python)"
   ```

#### 预防措施
1. **进程启动契约**: 先启动进程，成功后再更新状态
2. **资源监控**: 监控系统资源，预防资源不足
3. **进程健康检查**: 定期检查进程健康状态
4. **自动清理机制**: 自动检测和清理僵尸进程

### 故障4: 监控系统故障

#### 症状
- 监控仪表板无法访问
- 监控数据不更新
- 告警不触发或误报
- 监控进程崩溃

#### 诊断步骤
1. **检查监控进程**:
   ```bash
   ps aux | grep -E "(monitor|dashboard)" | grep -v grep
   ```

2. **检查监控端口**:
   ```bash
   lsof -i :5002
   ```

3. **检查监控日志**:
   ```bash
   tail -f /Volumes/1TB-M2/openclaw/logs/monitoring.log
   ```

#### 常见原因
1. **进程崩溃**: 监控进程异常退出
2. **端口冲突**: 监控端口被其他进程占用
3. **配置错误**: 监控配置文件错误
4. **资源不足**: 监控系统资源不足

#### 修复方案

##### 方案A: 重启监控系统
```bash
# 停止监控进程
pkill -f "queue_monitor_dashboard.py"
pkill -f "two_minute_queue_monitor.py"

# 重启监控系统
python3 queue_monitor_dashboard.py &
python3 scripts/two_minute_queue_monitor.py &
```

##### 方案B: 监控配置修复
```bash
# 验证监控配置
python3 scripts/validate_monitoring_config.py

# 修复配置问题
python3 scripts/fix_monitoring_config.py
```

#### 验证步骤
1. **验证仪表板访问**:
   ```bash
   curl -s http://localhost:5002/api/status | jq .
   ```

2. **验证数据收集**:
   ```bash
   python3 scripts/check_monitoring_data.py
   ```

3. **测试告警系统**:
   ```bash
   python3 scripts/test_alert_system.py
   ```

#### 预防措施
1. **进程监控**: 监控监控进程本身
2. **自动重启**: 监控进程崩溃时自动重启
3. **配置管理**: 版本控制监控配置
4. **容量规划**: 监控系统资源使用，及时扩容

## 修复脚本库

### 核心修复脚本

#### 1. `remove_ghost_dependencies.py`
**用途**: 移除指向不存在任务的依赖关系
**使用场景**: 队列因幽灵依赖阻塞
**命令**:
```bash
python3 scripts/remove_ghost_dependencies.py
```
**输出**: 移除的幽灵依赖列表和修复后的状态

#### 2. `fix_dependency_block.py`
**用途**: 修复依赖阻塞问题
**使用场景**: 任务依赖未满足导致队列阻塞
**命令**:
```bash
python3 scripts/fix_dependency_block.py
```
**输出**: 修复的任务列表和新的队列状态

#### 3. `final_queue_fix.py`
**用途**: 最终队列修复，直接修复阻塞的依赖链
**使用场景**: 复杂依赖链阻塞，其他修复方法无效
**命令**:
```bash
python3 scripts/final_queue_fix.py
```
**输出**: 修复的依赖链和最终队列状态

#### 4. `sync_queue_manifest_status.py`
**用途**: 同步manifest和队列状态，解决Athena Web Desktop显示待执行任务问题
**使用场景**: 
- Athena Web Desktop显示待执行任务但队列已清空
- Manifest中任务状态为failed/completed但队列中仍为pending
- 队列状态为no_consumer但实际无pending任务
- 任务计数不一致导致状态显示错误

**命令**:
```bash
python3 scripts/sync_queue_manifest_status.py
```

**脚本功能**:
1. 从manifest构建任务状态映射
2. 识别队列中状态不一致的任务
3. 同步pending->failed/completed的状态变更
4. 自动调整队列计数(pending, failed, completed)
5. 如果pending=0且队列状态为no_consumer，自动更新为empty状态
6. 生成详细的状态同步报告

**输出**: 
- 同步的任务数量和类型统计
- 更新前后的计数对比
- 队列状态变更情况
- 修复建议和后续步骤

**验证方法**:
```bash
# 检查同步结果
python3 -c "
import json
data = json.load(open('.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json'))
print('队列状态:', data.get('queue_status'))
counts = data.get('counts', {})
print('任务计数:', counts)
print('是否有pending任务:', '是' if counts.get('pending', 0) > 0 else '否')
"
```

#### 5. `cleanup_zombie_processes.py`
**用途**: 清理僵尸进程和孤儿进程
**使用场景**: 进程管理故障，资源泄漏
**命令**:
```bash
python3 scripts/cleanup_zombie_processes.py
```
**输出**: 清理的进程列表和资源释放情况

#### 6. `fix_process_startup.py`
**用途**: 修复进程启动问题
**使用场景**: 进程启动失败，状态不一致
**命令**:
```bash
python3 scripts/fix_process_startup.py
```
**输出**: 修复的进程启动问题和优化建议

### 诊断脚本

#### 1. `debug_runner_logic.py`
**用途**: 调试运行器逻辑，分析状态重置原因
**命令**:
```bash
python3 scripts/debug_runner_logic.py
```

#### 2. `diagnose_queue_status.py`
**用途**: 诊断队列状态问题
**命令**:
```bash
python3 scripts/diagnose_queue_status.py
```

#### 3. `compare_manifest_queue.py`
**用途**: 比较manifest和队列状态
**命令**:
```bash
python3 scripts/compare_manifest_queue.py
```

## 故障处理流程

### 紧急故障处理流程
```
发现故障 → 初步诊断 → 实施修复 → 验证修复 → 文档记录
```

### 复杂故障处理流程
```
发现故障 → 数据收集 → 根本原因分析 → 修复方案制定 → 
实施修复 → 验证测试 → 预防措施制定 → 知识分享
```

### 故障升级流程
```
一线支持 → 二线专家 → 开发团队 → 架构团队
```

## 故障预防策略

### 1. 主动监控
- **健康检查**: 定期系统健康检查
- **性能监控**: 关键性能指标监控
- **容量规划**: 基于监控数据的容量规划

### 2. 定期维护
- **系统审计**: 定期系统配置和数据审计
- **依赖清理**: 定期清理无效依赖
- **状态同步**: 定期同步系统状态

### 3. 自动化修复
- **自愈机制**: 常见故障自动修复
- **预警系统**: 故障发生前预警
- **备份恢复**: 自动化备份和恢复

### 4. 知识管理
- **故障库**: 建立故障案例库
- **最佳实践**: 总结故障处理最佳实践
- **培训材料**: 基于故障案例的培训材料

## 故障处理检查清单

### 通用检查清单
- [ ] 确认故障现象和影响范围
- [ ] 收集相关日志和状态数据
- [ ] 识别故障根本原因
- [ ] 制定修复方案和回滚计划
- [ ] 实施修复措施
- [ ] 验证修复效果
- [ ] 更新故障文档
- [ ] 制定预防措施

### 队列停滞检查清单
- [ ] 检查队列状态文件
- [ ] 检查pending任务和依赖
- [ ] 识别幽灵依赖
- [ ] 检查依赖任务状态
- [ ] 运行相应修复脚本
- [ ] 验证队列状态恢复
- [ ] 检查监控告警

### 状态不一致检查清单
- [ ] 比较manifest和队列状态
- [ ] 检查状态同步日志
- [ ] 识别不一致的任务
- [ ] 运行状态同步脚本
- [ ] 验证状态一致性
- [ ] 检查并发更新冲突

### 进程故障检查清单
- [ ] 检查进程状态
- [ ] 识别僵尸进程
- [ ] 检查进程启动日志
- [ ] 检查系统资源
- [ ] 运行进程清理脚本
- [ ] 验证进程状态恢复
- [ ] 优化进程启动时序

### 监控故障检查清单
- [ ] 检查监控进程状态
- [ ] 检查监控端口
- [ ] 检查监控日志
- [ ] 验证监控数据收集
- [ ] 测试告警系统
- [ ] 重启监控进程
- [ ] 验证监控恢复

## 故障复盘和改进

### 故障复盘模板
```
故障标题: [故障描述]
发生时间: [YYYY-MM-DD HH:MM]
发现方式: [监控告警/用户报告/系统检查]
影响范围: [受影响的系统和用户]
处理时长: [从发现到恢复的时间]
根本原因: [故障的根本原因]
处理过程: [详细的处理步骤]
改进措施: [防止复发的措施]
责任人: [负责实施改进措施]
完成时间: [改进措施预计完成时间]
```

### 持续改进
1. **故障分析**: 定期分析故障模式和趋势
2. **流程优化**: 优化故障处理流程
3. **工具改进**: 改进诊断和修复工具
4. **培训提升**: 基于故障案例的团队培训

---

*文档版本: 1.0*
*最后更新: 2026-04-17*
*维护者: Athena运维团队*