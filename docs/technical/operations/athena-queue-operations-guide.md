# Athena队列系统运维指南

## 概述

本文档提供Athena队列系统的运维指南，包括系统架构、监控配置、故障处理和告警配置。本指南基于新架构（智能工作流契约框架）部署后的生产环境经验编写。

## 系统架构

### 组件概览
```
Athena队列系统
├── 智能工作流契约框架 (Smart Workflow Contract Framework)
│   ├── 任务身份契约 (Task Identity Contract)
│   ├── 进程生命周期契约 (Process Lifecycle Contract)
│   ├── 状态同步契约 (State Sync Contract)
│   └── 数据质量契约 (Data Quality Contract)
├── 智能工作流编排器 (Smart Orchestrator)
│   ├── 任务路由器 (Task Router)
│   ├── 执行器适配层 (Executor Adapter)
│   └── 状态机 (State Machine)
├── 队列运行器 (Queue Runner)
├── 监控系统 (Monitoring System)
│   ├── 队列监控仪表板 (Queue Monitor Dashboard)
│   ├── 实时告警系统 (Real-time Alerting)
│   └── 性能指标收集器 (Metrics Collector)
└── 运维工具集 (Operations Toolset)
```

### 核心契约框架

#### 任务身份契约
- **目的**: 解决任务ID以`-`开头被argparse误识别为flag参数的问题
- **实现**: `TaskIdentityContract.generate()`生成规范化ID，不以`-`开头
- **关键功能**: ID规范化、反规范化、argparse兼容性保证

#### 进程生命周期契约
- **目的**: 解决先标记running再启动进程的问题，确保进程可靠性
- **实现**: `ProcessContract.spawn()`先启动进程，成功后再返回状态
- **关键功能**: 进程启动验证、秒级健康监控、僵尸进程检测

#### 状态同步契约
- **目的**: 确保Web界面、队列文件、manifest状态一致性
- **实现**: `StateSyncContract.atomic_update()`事务性状态更新
- **关键功能**: 原子性更新、乐观锁、状态合并

#### 数据质量契约
- **目的**: 解决manifest重复条目和数据完整性问题
- **实现**: 数据验证、去重、完整性检查
- **关键功能**: 唯一性验证、引用完整性、数据清理

### 智能工作流编排器

#### 执行器路由规则
| 任务类型 | 执行器 | 说明 |
|----------|--------|------|
| build | OPENCODE_BUILD | OpenCode构建执行器 |
| review | CODEX_REVIEW | Codex审查执行器 |
| plan | CLAUDE_CODE_CLI | Claude Code命令行接口 |
| scan | OPENCLI_SCAN | OpenCLI网页扫描 |

#### 自适应策略
- **系统负载感知**: 高负载时自动降级到轻量级执行器
- **预算状态感知**: 预算临界时选择成本更低的执行器
- **资源需求感知**: 大内存任务路由到专用执行器

## 监控配置

### 24小时监控验证计划

监控计划文件: `24_hour_monitoring_plan.json`

#### 监控检查项
| 检查项目 | 频率 | 指标 | 告警阈值 |
|----------|------|------|----------|
| 队列状态监控 | 每2分钟 | queue_status | dependency_blocked, failed |
| 任务执行进度 | 每5分钟 | progress_percent | 进度停滞>30分钟 |
| 系统资源使用 | 每10分钟 | cpu_memory_disk | CPU>90%, 内存>90%, 磁盘>85% |
| 依赖阻塞检测 | 每15分钟 | dependency_blocks | 阻塞>1小时 |
| 错误率监控 | 每30分钟 | error_rate | 错误率>10% |
| 吞吐量统计 | 每小时 | tasks_per_hour | 吞吐量下降>50% |

#### 验证标准
1. 队列状态保持running至少95%的时间
2. 任务执行成功率>90%
3. 无长时间依赖阻塞(>1小时)
4. 系统资源使用稳定(无内存泄漏)
5. 监控告警准确率>95%

### 监控仪表板

访问地址: http://localhost:5002/

#### 仪表板功能
- **实时队列状态**: 显示所有队列状态、任务计数、最后更新时间
- **系统资源监控**: CPU、内存、磁盘使用率实时显示
- **告警中心**: 实时显示队列停滞、依赖阻塞、任务失败等告警
- **历史趋势**: 展示CPU、内存、告警数量的历史趋势图表
- **自动刷新**: 每30秒自动刷新数据，支持手动刷新

#### API端点
- **状态接口**: `GET /api/status` - 获取当前系统状态
- **历史数据**: `GET /api/history` - 获取历史监控数据
- **健康检查**: `GET /api/health` - 系统健康检查

### 告警配置

#### 即时告警 (Immediate Alerts)
- `queue_status=dependency_blocked` - 队列依赖阻塞
- `queue_status=failed` - 队列失败
- `system_cpu>90%` - 系统CPU使用率超过90%
- `system_memory>90%` - 系统内存使用率超过90%
- `dependency_blocks>1h` - 依赖阻塞超过1小时

#### 告警渠道配置
```yaml
# 邮件告警配置 (示例)
email_alerts:
  enabled: true
  smtp_server: smtp.gmail.com
  smtp_port: 587
  username: ${EMAIL_USER}
  password: ${EMAIL_PASSWORD}
  recipients:
    - ops-team@example.com
    - oncall@example.com

# Slack Webhook配置 (示例)
slack_alerts:
  enabled: true
  webhook_url: ${SLACK_WEBHOOK_URL}
  channel: "#alerts"
  username: "Athena Monitor"

# Webhook配置 (示例)
webhook_alerts:
  enabled: true
  endpoints:
    - url: https://ops.example.com/api/alerts
      headers:
        Authorization: "Bearer ${API_TOKEN}"
```

#### 告警聚合与抑制
- **相同告警聚合**: 相同类型的告警在10分钟内聚合为一条
- **告警升级**: 持续未解决的告警30分钟后升级（邮件→短信→电话）
- **维护窗口**: 配置维护窗口抑制非关键告警
- **值班表集成**: 与值班系统集成，自动路由给当前值班人员

## 故障处理指南

### 常见故障场景

#### 1. 队列停滞 (Queue Stuck)

**症状**: 
- queue_status保持dependency_blocked超过30分钟
- 无任务执行进度
- 队列运行器日志显示依赖阻塞

**诊断步骤**:
1. 检查监控仪表板确认队列状态
2. 查看队列文件: `openhuman_aiplan_build_priority_20260328.json`
3. 分析pending任务的依赖关系:
   ```bash
   python3 analyze_queue_dependencies.py /Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json
   ```
4. 检查依赖任务在其他队列中的状态

**修复方案**:
1. 移除已在其他队列中完成的依赖引用:
   ```bash
   python3 quick_fix_queue_stall.py
   ```
2. 强制更新队列状态:
   ```bash
   python3 final_queue_fix_and_monitor.py
   ```
3. 重启队列运行器:
   ```bash
   python3 restart_runner_with_fix.py
   ```

#### 2. 进程启动失败

**症状**:
- 任务状态为running但无实际进程
- 进程监控显示进程不存在
- 系统资源使用异常低

**诊断步骤**:
1. 检查进程生命周期契约日志
2. 验证`ProcessContract.spawn()`的返回值
3. 检查系统资源限制（ulimit、内存限制）

**修复方案**:
1. 清理僵尸任务:
   ```bash
   python3 scripts/cleanup_stale_tasks.py
   ```
2. 调整资源限制
3. 重启队列运行器

#### 3. 状态不一致

**症状**:
- Web界面显示的状态与队列文件不一致
- 任务在Web界面显示完成，但在队列文件中仍为pending
- Manifest数据与队列状态不匹配

**诊断步骤**:
1. 使用状态同步契约验证一致性:
   ```python
   from contracts.state_sync import StateSyncContract
   contract = StateSyncContract("queue_file_path")
   state = contract.get_consistent_state()
   ```
2. 检查状态更新时间戳
3. 验证原子性更新日志

**修复方案**:
1. 强制状态同步:
   ```bash
   python3 scripts/force_state_sync.py
   ```
2. 清理状态缓存
3. 重启Web界面服务

#### 4. 系统资源不足

**症状**:
- 监控仪表板显示CPU/内存/磁盘使用率高
- 任务执行缓慢或失败
- 系统响应延迟

**诊断步骤**:
1. 检查监控仪表板的系统资源部分
2. 分析资源使用趋势
3. 识别资源密集型任务

**修复方案**:
1. 调整并行任务限制
2. 优化资源密集型任务的资源配置
3. 增加系统资源或横向扩展
4. 实施任务优先级调度

### 紧急恢复流程

#### 场景: 队列完全停滞，影响业务

**步骤1: 诊断**
1. 访问监控仪表板确认问题范围
2. 检查队列运行器进程是否存活
3. 查看系统资源使用情况

**步骤2: 临时恢复**
1. 使用快速修复脚本:
   ```bash
   python3 quick_fix_queue_stall.py
   python3 final_queue_fix_and_monitor.py
   ```
2. 重启队列运行器:
   ```bash
   python3 restart_runner_with_fix.py
   ```
3. 验证队列状态恢复

**步骤3: 根本原因分析**
1. 收集监控数据、日志、队列文件
2. 分析问题模式（依赖阻塞、资源不足、状态不一致）
3. 制定长期解决方案

**步骤4: 预防措施**
1. 优化监控告警阈值
2. 增强系统自愈能力
3. 更新运维文档

## 运维工具集

### 诊断工具

#### 队列分析工具
```bash
# 分析队列依赖关系
python3 analyze_queue_dependencies.py <队列文件路径>

# 快速修复队列停滞
python3 quick_fix_queue_stall.py

# 最终队列修复与监控启动
python3 final_queue_fix_and_monitor.py

# 重启队列运行器并修复状态
python3 restart_runner_with_fix.py
```

#### 系统检查工具
```bash
# 检查队列运行器状态
ps aux | grep athena_ai_plan_runner

# 检查监控仪表板状态
curl http://localhost:5002/api/health

# 检查系统资源
python3 scripts/system_resource_facts.py --json
```

#### 数据清理工具
```bash
# 清理僵尸任务
python3 scripts/cleanup_stale_tasks.py

# 清理manifest重复条目
python3 scripts/cleanup_manifest_duplicates.py

# 强制状态同步
python3 scripts/force_state_sync.py
```

### 自动化脚本

#### 每日健康检查
```bash
#!/bin/bash
# daily_health_check.sh

echo "=== Athena队列系统每日健康检查 ==="
echo "检查时间: $(date)"

# 1. 检查队列运行器
echo "1. 检查队列运行器..."
ps aux | grep -q athena_ai_plan_runner
if [ $? -eq 0 ]; then
    echo "   ✅ 队列运行器正在运行"
else
    echo "   ❌ 队列运行器未运行"
fi

# 2. 检查监控仪表板
echo "2. 检查监控仪表板..."
curl -s http://localhost:5002/api/health > /dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ 监控仪表板正常"
else
    echo "   ❌ 监控仪表板异常"
fi

# 3. 检查系统资源
echo "3. 检查系统资源..."
python3 scripts/system_resource_facts.py --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
cpu = data.get('cpu_percent', 0)
mem = data.get('memory_percent', 0)
disk = data.get('disk_usage', 0)

print(f'   CPU使用率: {cpu:.1f}%', end=' ')
print('✅' if cpu < 80 else '⚠️')

print(f'   内存使用率: {mem:.1f}%', end=' ')
print('✅' if mem < 80 else '⚠️')

print(f'   磁盘使用率: {disk:.1f}%', end=' ')
print('✅' if disk < 85 else '⚠️')
"

echo "=== 健康检查完成 ==="
```

#### 队列状态报告
```bash
#!/bin/bash
# queue_status_report.sh

echo "=== 队列状态报告 ==="
echo "生成时间: $(date)"
echo ""

# 分析所有队列文件
for queue_file in /Volumes/1TB-M2/openclaw/.openclaw/plan_queue/*.json; do
    queue_name=$(basename "$queue_file")
    echo "队列: $queue_name"
    
    python3 -c "
import json, sys
try:
    with open('$queue_file', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    status = data.get('queue_status', 'unknown')
    pause_reason = data.get('pause_reason', '')
    counts = data.get('counts', {})
    
    pending = counts.get('pending', 0)
    running = counts.get('running', 0)
    completed = counts.get('completed', 0)
    failed = counts.get('failed', 0)
    
    print(f'  状态: {status}', end=' ')
    if status == 'running':
        print('✅')
    elif status == 'dependency_blocked':
        print('🔴')
    else:
        print('⚠️')
    
    if pause_reason:
        print(f'  暂停原因: {pause_reason}')
    
    print(f'  任务: pending={pending}, running={running}, completed={completed}, failed={failed}')
    
    # 如果有pending任务，显示前3个
    if pending > 0:
        items = data.get('items', {})
        pending_tasks = [(tid, task.get('summary', '')[0:50]) 
                        for tid, task in items.items() 
                        if task.get('status') == 'pending'][:3]
        if pending_tasks:
            print(f'  PENDING任务(前3个):')
            for tid, summary in pending_tasks:
                print(f'    - {tid}: {summary}')
    
except Exception as e:
    print(f'  读取失败: {e}')
"
    echo ""
done
```

## 性能优化建议

### 队列性能调优

#### 并行度优化
- **当前配置**: 并行任务限制未完全实现
- **建议**: 根据系统资源动态调整并行度
- **实现**: 在智能工作流编排器中添加资源感知调度

#### 依赖管理优化
- **问题**: 跨队列依赖导致阻塞
- **建议**: 实现依赖任务自动发现和状态同步
- **实现**: 增强依赖分析工具，自动修复跨队列依赖

#### 状态管理优化
- **问题**: 状态分散在多处，一致性维护复杂
- **建议**: 统一状态存储，减少同步点
- **实现**: 使用单一事实源的状态存储

### 监控优化

#### 告警优化
- **当前**: 基础阈值告警
- **建议**: 添加预测性告警和异常检测
- **实现**: 基于历史数据的机器学习异常检测

#### 仪表板优化
- **当前**: 基础监控仪表板
- **建议**: 添加业务指标和SLO监控
- **实现**: 扩展监控API，添加业务相关指标

#### 日志优化
- **当前**: 分散的日志文件
- **建议**: 集中化日志收集和分析
- **实现**: 集成ELK栈或类似日志管理系统

## 附录

### 配置文件位置
- **队列文件**: `/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/`
- **监控配置**: `24_hour_monitoring_plan.json`
- **契约框架**: `/Volumes/1TB-M2/openclaw/contracts/`
- **工作流引擎**: `/Volumes/1TB-M2/openclaw/workflow/`
- **运维脚本**: `/Volumes/1TB-M2/openclaw/scripts/`

### 关键脚本说明
| 脚本 | 用途 | 执行频率 |
|------|------|----------|
| `athena_ai_plan_runner.py` | 队列运行器主程序 | 持续运行 |
| `queue_monitor_dashboard.py` | 监控仪表板 | 持续运行 |
| `quick_fix_queue_stall.py` | 快速修复队列停滞 | 按需 |
| `final_queue_fix_and_monitor.py` | 最终修复与监控启动 | 按需 |
| `restart_runner_with_fix.py` | 重启运行器并修复状态 | 按需 |
| `analyze_queue_dependencies.py` | 分析队列依赖关系 | 按需 |

### 联系信息
- **运维团队**: ops-team@example.com
- **值班电话**: +1-xxx-xxx-xxxx
- **紧急联系人**: 张三 (138-xxxx-xxxx)
- **知识库**: https://wiki.example.com/athena-queue

---

*文档版本: 1.0.0*
*最后更新: 2026-04-17*
*下次评审: 2026-07-17*