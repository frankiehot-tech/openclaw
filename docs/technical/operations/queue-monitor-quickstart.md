# 队列监控系统快速启动指南

## 1. 安装依赖

```bash
# 安装基本依赖
pip3 install psutil requests

# 可选：安装YAML支持（如果需要配置文件）
pip3 install PyYAML
```

## 2. 配置文件

### 选项A：使用默认配置（控制台和日志告警）
直接运行监控脚本，无需配置文件：

```bash
python3 scripts/queue_monitor.py --once
```

### 选项B：使用配置文件
1. 复制示例配置文件：
   ```bash
   cp queue_monitor_config_example.yaml queue_monitor_config.yaml
   ```

2. 编辑配置文件：
   ```bash
   nano queue_monitor_config.yaml
   ```

3. 启用需要的告警渠道：
   - **邮件告警**：设置 `email.enabled: true`，配置SMTP信息
   - **Slack告警**：设置 `slack.enabled: true`，配置Webhook URL
   - **Webhook告警**：设置 `webhook.enabled: true`，配置URL和请求头

## 3. 运行监控

### 单次检查模式（测试）
```bash
# 使用默认配置
python3 scripts/queue_monitor.py --once

# 使用配置文件
python3 scripts/queue_monitor.py --once --config queue_monitor_config.yaml
```

### 守护进程模式（持续监控）
```bash
# 后台运行，使用配置文件
python3 scripts/queue_monitor.py --daemon --config queue_monitor_config.yaml
```

### 命令行选项
```bash
--config, -c  指定配置文件路径
--once, -o    单次检查模式
--daemon, -d  后台守护进程模式
--alert, -a   启用告警测试
```

## 4. 告警配置示例

### 邮件告警（Gmail）
```yaml
email:
  enabled: true
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  smtp_username: "your-email@gmail.com"
  smtp_password: "your-app-password"  # 使用Gmail应用专用密码
  sender_email: "your-email@gmail.com"
  recipient_emails:
    - "admin@example.com"
```

### Slack告警
```yaml
slack:
  enabled: true
  webhook_url: "https://hooks.slack.com/services/TXXXXX/BXXXXX/XXXXXX"
```

### Webhook告警
```yaml
webhook:
  enabled: true
  url: "https://your-webhook.example.com/alerts"
  headers:
    Authorization: "Bearer your-token-here"
    Content-Type: "application/json"
  timeout: 10
```

## 5. 监控内容

### 队列状态监控
- 队列运行状态（running, empty, paused, manual_hold）
- 任务统计（pending, running, completed, failed）
- 队列最后更新时间
- 队列卡住检测

### 系统资源监控
- CPU使用率
- 内存使用率
- 磁盘使用率
- 运行器进程状态

### 告警类型
- **stale_queue**: 队列长时间未更新
- **queue_stuck_empty_with_pending**: 队列空但有等待任务
- **high_cpu**: CPU使用率过高
- **high_memory**: 内存使用率过高
- **web_api_error**: Web API访问错误
- **runner_process_missing**: 队列运行器进程缺失

## 6. Web仪表板

启动Web监控仪表板：
```bash
python3 queue_monitor_dashboard.py
```

访问地址：http://127.0.0.1:5002

## 7. 故障排除

### 常见问题

**Q: 监控脚本无法找到队列文件**
A: 确保队列目录存在：`/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/`

**Q: 邮件告警发送失败**
A: 检查SMTP配置，确保使用应用专用密码（而非登录密码）

**Q: 监控脚本权限不足**
A: 确保有读取队列文件和系统信息的权限

**Q: 告警过于频繁**
A: 调整配置文件中的阈值或增加 `alert_cooldown_minutes`

### 日志文件
- 监控日志：`logs/queue_monitoring.jsonl`
- 告警日志：`logs/queue_alerts.jsonl`
- 系统日志：脚本控制台输出

## 8. 高级功能

### 队列模式分析
监控脚本会自动分析队列异常模式：
- 高失败率检测
- 任务积压检测
- 长时间运行无完成任务检测
- 资源使用与队列状态不匹配检测

### 智能修复建议
每个告警都会附带具体的修复建议，帮助快速解决问题。

### 自定义阈值
可以为不同队列设置独立的阈值配置。