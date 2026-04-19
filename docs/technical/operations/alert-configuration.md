# 监控告警配置文档

## 概述
本文档详细说明Athena队列系统的监控告警配置，包括告警规则、阈值设置、告警聚合、通知渠道和优化策略。

## 告警架构

### 告警系统组件

#### 1. 告警检测器 (Alert Detector)
- **位置**: `two_minute_queue_monitor.py` 中的告警检测逻辑
- **功能**: 定期检查监控指标，触发告警条件
- **检测频率**: 每2分钟（可配置）

#### 2. 告警处理器 (Alert Processor)
- **位置**: 监控仪表板的告警处理模块
- **功能**: 处理告警事件，包括聚合、升级、通知
- **处理能力**: 并发处理多个告警事件

#### 3. 告警存储器 (Alert Storage)
- **位置**: 监控系统的告警数据库
- **功能**: 存储告警历史，支持查询和分析
- **数据保留**: 30天（可配置）

#### 4. 通知分发器 (Notification Dispatcher)
- **位置**: 告警通知模块
- **功能**: 将告警分发到不同通知渠道
- **支持渠道**: 控制台、日志文件、仪表板

### 告警数据流
```
监控指标收集 → 告警规则检查 → 告警事件生成 → 
告警聚合处理 → 通知分发 → 告警状态跟踪 → 
告警解决确认 → 告警历史归档
```

## 告警规则配置

### 告警规则分类

#### 1. 即时告警 (Immediate Alerts)
立即触发的告警，需要立即处理：

| 告警名称 | 触发条件 | 严重程度 | 自动恢复 | 备注 |
|---------|---------|---------|---------|------|
| 队列依赖阻塞 | `queue_status = "dependency_blocked"` | 严重 | 否 | 队列完全停止 |
| 队列失败 | `queue_status = "failed"` | 严重 | 否 | 队列执行失败 |
| 队列手动暂停超时 | `queue_status = "manual_hold" AND duration > 1h` | 中等 | 否 | 需要人工干预 |
| 高CPU使用率 | `system_cpu > 90%` | 中等 | 是 | 可能影响性能 |
| 高内存使用率 | `system_memory > 90%` | 中等 | 是 | 可能内存泄漏 |
| 高磁盘使用率 | `disk_usage > 95%` | 严重 | 否 | 可能系统崩溃 |
| 任务连续失败 | `task_failure_count >= 3` | 中等 | 否 | 任务执行问题 |
| 任务执行超时 | `task_execution_time > 1h` | 中等 | 否 | 任务可能卡住 |
| 监控数据缺失 | `no_monitoring_data > 5min` | 中等 | 是 | 监控系统问题 |

#### 2. 阈值告警 (Threshold Alerts)
基于阈值的告警，可以容忍短暂波动：

| 告警名称 | 触发条件 | 持续时间 | 严重程度 |
|---------|---------|---------|---------|
| 中CPU使用率 | `system_cpu > 80%` | 5分钟 | 警告 |
| 中内存使用率 | `system_memory > 80%` | 5分钟 | 警告 |
| 队列空闲超时 | `queue_status = "empty" AND duration > 4h` | 连续 | 低 |
| 低任务成功率 | `task_success_rate < 90%` | 1小时 | 中等 |
| 高任务延迟 | `average_latency > 30min` | 1小时 | 中等 |

#### 3. 趋势告警 (Trend Alerts)
基于趋势变化的告警，检测潜在问题：

| 告警名称 | 触发条件 | 时间窗口 | 严重程度 |
|---------|---------|---------|---------|
| 内存泄漏检测 | `memory_usage_increase > 10% per hour` | 2小时 | 中等 |
| CPU使用率上升 | `cpu_usage_increase > 20% per hour` | 1小时 | 警告 |
| 错误率上升 | `error_rate_increase > 50% per hour` | 1小时 | 中等 |
| 吞吐量下降 | `throughput_decrease > 30% per hour` | 1小时 | 中等 |

### 告警规则配置文件

#### YAML配置格式
```yaml
alert_rules:
  immediate_alerts:
    - name: "queue_dependency_blocked"
      condition: "queue_status == 'dependency_blocked'"
      severity: "critical"
      auto_recovery: false
      notification_channels: ["console", "dashboard", "log"]
      escalation: "immediate"
      
    - name: "high_cpu_usage"
      condition: "system_cpu > 90"
      severity: "medium"
      auto_recovery: true
      notification_channels: ["console", "dashboard"]
      escalation: "after_15min"
      
  threshold_alerts:
    - name: "medium_cpu_usage"
      condition: "system_cpu > 80"
      duration: "5min"
      severity: "warning"
      notification_channels: ["dashboard"]
      
  trend_alerts:
    - name: "memory_leak_detected"
      condition: "memory_usage_increase > 10"
      time_window: "2h"
      severity: "medium"
      notification_channels: ["console", "dashboard", "email"]
```

#### JSON配置格式
```json
{
  "alert_rules": {
    "immediate_alerts": [
      {
        "name": "queue_dependency_blocked",
        "condition": "queue_status == 'dependency_blocked'",
        "severity": "critical",
        "auto_recovery": false,
        "notification_channels": ["console", "dashboard", "log"]
      }
    ],
    "threshold_alerts": [
      {
        "name": "medium_cpu_usage",
        "condition": "system_cpu > 80",
        "duration": "5min",
        "severity": "warning",
        "notification_channels": ["dashboard"]
      }
    ]
  }
}
```

## 告警聚合和降噪

### 告警聚合策略

#### 1. 时间聚合
- **相同告警合并窗口**: 5分钟
- **聚合规则**: 5分钟内相同的告警合并为一条
- **聚合效果**: 减少重复告警噪音

#### 2. 空间聚合
- **相关告警分组**: 相关告警分组显示
- **分组规则**: 相同组件、相同根本原因的告警分组
- **分组效果**: 提供更清晰的故障视图

#### 3. 层次聚合
- **告警层次结构**: 根因告警和衍生告警
- **聚合规则**: 显示根因告警，隐藏衍生告警
- **聚合效果**: 简化告警视图，聚焦根本问题

### 告警降噪配置

#### 告警抑制规则
```yaml
alert_suppression:
  # 基于时间的抑制
  time_based:
    - time_range: "00:00-06:00"  # 凌晨时段
      suppressed_alerts: ["low_severity_warnings"]
      reason: "维护时段"
      
  # 基于事件的抑制
  event_based:
    - when: "system_maintenance == true"
      suppressed_alerts: ["all_non_critical"]
      reason: "系统维护"
      
  # 基于条件的抑制
  condition_based:
    - when: "queue_status == 'empty'"
      suppressed_alerts: ["queue_idle_alert"]
      reason: "队列正常空闲状态"
```

#### 告警静默配置
```bash
# 临时静默告警
python3 scripts/silence_alerts.py \
  --alert-names "queue_idle_alert" \
  --duration "2h" \
  --reason "计划维护"

# 查看当前静默
python3 scripts/list_silenced_alerts.py

# 取消静默
python3 scripts/unsilence_alerts.py --alert-id "alert_123"
```

## 告警通知渠道

### 当前支持渠道

#### 1. 控制台输出 (Console)
- **格式**: 彩色文本输出，包含时间、严重程度、详细信息
- **配置**:
  ```yaml
  console_notification:
    enabled: true
    format: "colored_text"
    timestamp_format: "%Y-%m-%d %H:%M:%S"
    show_severity_colors: true
  ```

#### 2. 日志文件 (Log File)
- **文件路径**: `/Volumes/1TB-M2/openclaw/logs/alerts.log`
- **格式**: JSON格式，便于程序处理
- **配置**:
  ```yaml
  log_notification:
    enabled: true
    file_path: "/Volumes/1TB-M2/openclaw/logs/alerts.log"
    format: "json"
    max_size_mb: 100
    rotation_count: 5
  ```

#### 3. 监控仪表板 (Dashboard)
- **显示位置**: 仪表板告警面板
- **功能**: 实时显示，历史查询，告警管理
- **配置**:
  ```yaml
  dashboard_notification:
    enabled: true
    realtime_updates: true
    historical_view: true
    alert_management: true
  ```

### 计划支持渠道

#### 1. 电子邮件通知
```yaml
email_notification:
  enabled: false  # 计划功能
  smtp_server: "smtp.example.com"
  smtp_port: 587
  sender: "alerts@example.com"
  recipients: ["team@example.com", "oncall@example.com"]
  subject_template: "[{severity}] {alert_name} - {timestamp}"
```

#### 2. Slack通知
```yaml
slack_notification:
  enabled: false  # 计划功能
  webhook_url: "https://hooks.slack.com/services/..."
  channel: "#alerts"
  username: "Athena Alert Bot"
  icon_emoji: ":warning:"
```

#### 3. Webhook通知
```yaml
webhook_notification:
  enabled: false  # 计划功能
  endpoints:
    - url: "https://api.pagerduty.com/v2/..."
      headers: {"Authorization": "Bearer ..."}
      format: "pagerduty"
    - url: "https://api.opsgenie.com/v2/..."
      headers: {"Authorization": "GenieKey ..."}
      format: "opsgenie"
```

## 告警升级和值班管理

### 告警升级策略

#### 升级时间线
```
触发告警 → 15分钟未确认 → 升级到值班人员 → 
30分钟未解决 → 升级到团队负责人 → 
1小时未解决 → 升级到技术总监
```

#### 升级规则配置
```yaml
escalation_rules:
  - stage: "initial"
    timeout: "15min"
    notify: ["oncall_primary"]
    
  - stage: "secondary"
    timeout: "30min"
    notify: ["oncall_secondary", "team_lead"]
    
  - stage: "tertiary"
    timeout: "1h"
    notify: ["tech_director", "all_team_leads"]
```

### 值班管理

#### 值班表配置
```yaml
oncall_schedule:
  primary:
    - name: "张三"
      email: "zhangsan@example.com"
      phone: "+86-13800138000"
      shift: "2026-04-17 09:00 to 2026-04-18 09:00"
  secondary:
    - name: "李四"
      email: "lisi@example.com"
      phone: "+86-13900139000"
      shift: "2026-04-17 09:00 to 2026-04-18 09:00"
```

#### 值班交接
- **交接时间**: 每天09:00
- **交接内容**: 未解决告警、进行中事项、特别注意事项
- **交接方式**: 书面交接 + 口头沟通

## 告警测试和验证

### 告警测试方法

#### 1. 单元测试
```python
# 测试告警规则逻辑
def test_dependency_blocked_alert():
    # 模拟dependency_blocked状态
    test_state = {"queue_status": "dependency_blocked"}
    alerts = alert_detector.check_alerts(test_state)
    assert "queue_dependency_blocked" in alerts
```

#### 2. 集成测试
```bash
# 测试完整告警流程
python3 scripts/test_alert_pipeline.py \
  --test-case "dependency_blocked" \
  --verify-notification \
  --verify-escalation
```

#### 3. 端到端测试
```bash
# 模拟真实场景测试
./scripts/run_alert_e2e_test.sh \
  --scenario "queue_stall" \
  --duration "1h" \
  --validate-all-channels
```

### 告警验证指标

#### 准确性指标
1. **告警准确率**: `正确告警数 / 总告警数`，目标 >95%
2. **误报率**: `误报告警数 / 总告警数`，目标 <5%
3. **漏报率**: `漏报事件数 / 总事件数`，目标 <1%

#### 及时性指标
1. **检测延迟**: 从事件发生到告警触发的时间，目标 <2分钟
2. **通知延迟**: 从告警触发到通知送达的时间，目标 <1分钟
3. **确认延迟**: 从告警通知到人工确认的时间，目标 <15分钟

#### 有效性指标
1. **告警解决率**: `已解决告警数 / 总告警数`，目标 >90%
2. **平均解决时间**: 从告警触发到解决的平均时间，目标 <30分钟
3. **重复告警率**: `重复告警数 / 总告警数`，目标 <10%

## 告警优化和调优

### 基于24小时监控验证的优化

#### 发现的问题
1. **空队列误报**: 队列状态为empty时产生陈旧队列告警
2. **幽灵依赖告警**: 需要更精准的依赖阻塞检测
3. **资源使用告警阈值**: 需要根据实际负载调整阈值
4. **no_consumer状态误报**: 队列状态为no_consumer时触发手动暂停告警，但可能只是状态同步问题
5. **陈旧队列告警范围过广**: 备份队列和历史队列被误判为陈旧队列
6. **手动暂停告警误判**: empty状态队列被标记为手动暂停

#### 优化措施

##### 1. 空队列告警优化
```yaml
# 优化前
queue_idle_alert:
  condition: "queue_status == 'empty' AND duration > 1h"
  
# 优化后
queue_idle_alert:
  condition: "queue_status == 'empty' AND duration > 4h AND has_pending_tasks"
  # 只有有空闲任务但队列空置4小时才告警
```

##### 2. 依赖阻塞告警优化
```yaml
# 优化前
dependency_blocked_alert:
  condition: "queue_status == 'dependency_blocked'"
  
# 优化后
dependency_blocked_alert:
  condition: "queue_status == 'dependency_blocked' AND duration > 15min"
  # 短暂依赖阻塞不告警，持续15分钟才告警
```

##### 3. 资源告警阈值优化
```yaml
# 基于实际负载调整阈值
cpu_usage_alert:
  condition: "system_cpu > ${dynamic_threshold}"
  
# 动态阈值计算
dynamic_threshold:
  base: 90  # 基础阈值
  adjustment: 
    - when: "time_range == '00:00-06:00'"
      adjustment: -10  # 夜间降低阈值
    - when: "has_critical_tasks"
      adjustment: +5   # 关键任务时提高阈值
```

##### 4. no_consumer状态告警优化
```yaml
# 优化前
no_consumer_alert:
  condition: "queue_status == 'no_consumer'"
  
# 优化后 - 考虑状态同步问题
no_consumer_alert:
  condition: "queue_status == 'no_consumer' AND duration > 10min"
  # 给状态同步脚本执行时间，避免立即告警
  
# 状态同步检查规则
no_consumer_state_sync_check:
  condition: "queue_status == 'no_consumer'"
  action: "run_state_sync_script"  # 自动触发状态同步脚本
  delay_before_alert: "5min"  # 同步脚本执行后再评估
```

##### 5. 陈旧队列告警优化
```yaml
# 优化前 - 所有队列都检查陈旧状态
stale_queue_alert:
  condition: "last_update_age > 2h"
  
# 优化后 - 排除备份和历史队列
stale_queue_alert:
  condition: "last_update_age > 2h AND queue_name NOT LIKE '%backup%' AND queue_name NOT LIKE '%history%' AND queue_name NOT LIKE '%.backup.%'"
  # 排除名称包含backup或history的队列
  exclude_patterns: ["*backup*", "*history*", "*archive*"]
```

##### 6. 手动暂停告警优化
```yaml
# 优化前 - empty队列可能误判为手动暂停
queue_manually_paused_alert:
  condition: "queue_status == 'manual_hold'"
  
# 优化后 - empty队列不应触发手动暂停告警
queue_manually_paused_alert:
  condition: "queue_status == 'manual_hold' AND queue_status != 'empty'"
  # 确保empty状态队列不触发手动暂停告警
  
# 增加empty状态队列的专门规则
queue_empty_state_rule:
  condition: "queue_status == 'empty'"
  action: "suppress_manual_hold_alerts"  # 抑制手动暂停告警
```

### 告警规则版本管理

#### 版本控制策略
```yaml
alert_config_versioning:
  current_version: "1.2.0"
  version_format: "major.minor.patch"
  changelog:
    "1.2.0":
      date: "2026-04-17"
      changes:
        - "优化空队列告警规则"
        - "增加动态阈值支持"
        - "修复幽灵依赖检测"
  rollback_support: true
```

#### 配置变更流程
1. **变更申请**: 提交告警规则变更申请
2. **影响分析**: 分析变更对现有告警的影响
3. **测试验证**: 在测试环境验证变更效果
4. **评审批准**: 变更评审委员会批准
5. **分阶段部署**: 分阶段部署到生产环境
6. **效果监控**: 监控变更后的告警效果

## 告警分析和报告

### 告警分析报告

#### 日报
- **时间范围**: 前24小时
- **内容**: 告警统计、趋势分析、重点问题
- **分发**: 运维团队、技术负责人

#### 周报
- **时间范围**: 前7天
- **内容**: 告警趋势、根本原因分析、改进建议
- **分发**: 管理团队、所有技术团队

#### 月报
- **时间范围**: 前30天
- **内容**: 长期趋势、系统性改进、容量规划
- **分发**: 高管团队、所有相关部门

### 告警分析指标

#### 告警趋势分析
```sql
-- 告警数量趋势
SELECT date_trunc('hour', timestamp) as hour,
       COUNT(*) as alert_count,
       AVG(resolution_time_minutes) as avg_resolution_time
FROM alerts
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour;
```

#### 告警根本原因分析
```sql
-- 告警根本原因分布
SELECT root_cause,
       COUNT(*) as count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM alerts
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY root_cause
ORDER BY count DESC;
```

## 告警系统维护

### 日常维护任务

#### 1. 告警系统健康检查
```bash
# 每日健康检查
./scripts/check_alert_system_health.sh

# 检查项包括:
# - 告警检测器状态
# - 通知渠道可用性
# - 告警存储状态
# - 性能指标
```

#### 2. 告警规则审核
- **频率**: 每周一次
- **内容**: 审核告警规则效果，优化规则
- **输出**: 告警规则优化建议

#### 3. 告警数据清理
```bash
# 清理过期告警数据
python3 scripts/cleanup_alert_data.py \
  --retention-days 30 \
  --dry-run false
```

### 故障处理

#### 告警系统故障处理
1. **检测故障**: 通过健康检查或用户报告
2. **诊断原因**: 检查日志、配置、依赖服务
3. **实施修复**: 修复问题或回滚到稳定版本
4. **验证恢复**: 验证告警系统恢复正常
5. **记录故障**: 记录故障详情和处理过程

#### 紧急恢复措施
```bash
# 紧急情况下重启告警系统
./scripts/emergency_restart_alert_system.sh

# 临时禁用非关键告警
python3 scripts/disable_non_critical_alerts.py --duration "2h"
```

## 最佳实践

### 告警配置最佳实践
1. **分级告警**: 根据业务影响分级配置告警
2. **智能聚合**: 减少告警噪音，提高告警质量
3. **上下文丰富**: 告警包含足够的诊断信息
4. **自动化响应**: 配置自动化响应常见告警

### 告警管理最佳实践
1. **定期评审**: 定期评审告警规则和效果
2. **持续优化**: 基于反馈持续优化告警配置
3. **知识共享**: 告警处理经验和团队共享
4. **容量规划**: 基于告警趋势进行容量规划

### 告警响应最佳实践
1. **明确职责**: 明确告警响应职责和流程
2. **快速响应**: 建立快速响应机制
3. **根本原因分析**: 重视告警根本原因分析
4. **预防措施**: 基于告警分析制定预防措施

---

*文档版本: 1.1*
*最后更新: 2026-04-17*
*维护者: Athena监控团队*