# MAREF通知系统配置指南

## 概述

MAREF通知系统用于发送系统预警和日报通知到多种渠道，包括邮件、企业微信、Slack等。本文档提供完整的配置和使用指南。

## 系统架构

```
MAREF日报生成器 → 预警检查 → MAREF通知器 → 渠道分发
                                     ├── 控制台 (Console)
                                     ├── 文件日志 (File)
                                     ├── 邮件 (Email)
                                     ├── 企业微信 (WeCom)
                                     ├── Slack
                                     └── Athena系统集成
```

## 配置方式

### 1. 配置文件位置
- **主要配置文件**: `config/notifier_config.json`
- **生产环境配置**: `config/production_config.py` (包含告警配置)

### 2. 配置参数说明

#### 基础配置
```json
{
  "file_log_enabled": true,
  "file_log_path": "/Volumes/1TB-M2/openclaw/scripts/clawra/logs/maref_notifications.log",
  "console_log_enabled": true
}
```

#### 邮件配置 (Gmail示例)
```json
{
  "email_enabled": true,
  "email_smtp_server": "smtp.gmail.com",
  "email_smtp_port": 587,
  "email_sender": "your.email@gmail.com",
  "email_receivers": ["recipient1@example.com", "recipient2@example.com"],
  "email_password": "your_app_password_here"
}
```

**注意**: 对于Gmail，需要使用[应用专用密码](https://support.google.com/accounts/answer/185833)，而非常规密码。

#### 企业微信配置
```json
{
  "wecom_enabled": true,
  "wecom_webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
}
```

#### Slack配置
```json
{
  "slack_enabled": true,
  "slack_webhook": "https://hooks.slack.com/services/YOUR/WEBHOOK/PATH"
}
```

### 3. 完整配置示例
```json
{
  "wecom_enabled": false,
  "wecom_webhook": "",
  "email_enabled": true,
  "email_smtp_server": "smtp.gmail.com",
  "email_smtp_port": 587,
  "email_sender": "maref.monitor@example.com",
  "email_receivers": ["devops@example.com", "oncall@example.com"],
  "email_password": "your_app_password_here",
  "slack_enabled": false,
  "slack_webhook": "",
  "file_log_enabled": true,
  "file_log_path": "/Volumes/1TB-M2/openclaw/scripts/clawra/logs/maref_notifications.log",
  "console_log_enabled": true,
  "athena_integration_enabled": true,
  "athena_notification_api": "http://localhost:8000/api/notifications"
}
```

## 集成与使用

### 1. 日报系统中的通知
```python
# maref_daily_reporter.py 中的通知调用
if alerts.get('red_alerts') or alerts.get('yellow_alerts'):
    self.send_alerts(alerts, report_path)
```

### 2. 通知触发条件
- **红色预警**: 控制熵异常、格雷编码违规率高、系统崩溃等
- **黄色预警**: 性能下降、资源警告、智能体健康度下降等
- **正常日报**: 不触发外部通知（仅记录到文件）

### 3. 手动测试通知系统
```bash
# 运行完整测试
python3 test_notifier_config.py

# 测试特定功能
python3 -c "
import sys
sys.path.insert(0, '.')
from maref_notifier import MAREFNotifier

notifier = MAREFNotifier('config/notifier_config.json')
status = notifier.get_notification_status()
print(f'渠道状态: {status[\"channel_status\"]}')
print(f'配置摘要: {status[\"config_summary\"]}')
"
```

## 故障排除

### 常见问题

#### 1. 邮件发送失败
- **症状**: 邮件渠道启用但发送失败
- **检查项**:
  1. SMTP服务器和端口是否正确
  2. 邮箱密码是否为应用专用密码
  3. 发件邮箱是否启用了SMTP
  4. 网络连接是否正常

#### 2. 文件日志权限问题
- **症状**: `Permission denied` 错误
- **解决方案**:
```bash
# 确保日志目录存在且可写
mkdir -p /Volumes/1TB-M2/openclaw/scripts/clawra/logs
touch /Volumes/1TB-M2/openclaw/scripts/clawra/logs/maref_notifications.log
chmod 666 /Volumes/1TB-M2/openclaw/scripts/clawra/logs/maref_notifications.log
```

#### 3. 配置不生效
- **症状**: 修改配置文件后通知器仍使用默认配置
- **检查项**:
  1. 配置文件路径是否正确
  2. JSON格式是否有效（无语法错误）
  3. 是否重启了相关服务

### 诊断命令
```bash
# 检查当前配置
python3 -c "
import json
with open('config/notifier_config.json') as f:
    config = json.load(f)
print('当前配置:')
for key, value in config.items():
    if 'password' not in key.lower():
        print(f'  {key}: {value}')
"

# 检查通知器状态
python3 -c "
import sys
sys.path.insert(0, '.')
from maref_notifier import MAREFNotifier
n = MAREFNotifier('config/notifier_config.json')
status = n.get_notification_status()
print('渠道状态:', status['channel_status'])
print('总通知数:', status['total_notifications'])
"
```

## 生产环境最佳实践

### 1. 安全建议
- 将邮箱密码等敏感信息存储在环境变量中，而非配置文件中
- 使用应用专用密码而非常规账户密码
- 定期轮换凭据

### 2. 监控建议
- 监控通知日志文件大小，避免磁盘空间问题
- 设置通知失败告警
- 定期测试通知渠道可用性

### 3. 备份建议
- 定期备份通知配置文件
- 记录通知历史用于审计

## 与生产配置的集成

### 配置一致性
生产配置 `config/production_config.py` 中的告警配置应与通知器配置保持一致：

```python
# production_config.py 中的相关配置
ALERT_CONFIG = {
    "notification_channels": ["log", "email", "webhook"],
    "notification_settings": {
        "email_recipients": ["devops@example.com", "oncall@example.com"],
        "webhook_url": "https://alerts.example.com/hook",
        "repeat_interval_minutes": 30
    },
    # ... 其他配置
}
```

### 配置同步脚本
可以创建配置同步脚本确保一致性：

```python
#!/usr/bin/env python3
"""同步生产配置到通知器配置"""
import json
import sys
sys.path.insert(0, '.')
from config.production_config import ALERT_CONFIG

# 读取现有通知配置
with open('config/notifier_config.json', 'r') as f:
    notifier_config = json.load(f)

# 同步邮件收件人
if 'email_recipients' in ALERT_CONFIG.get('notification_settings', {}):
    notifier_config['email_receivers'] = ALERT_CONFIG['notification_settings']['email_recipients']

# 保存更新后的配置
with open('config/notifier_config.json', 'w') as f:
    json.dump(notifier_config, f, indent=2)

print("配置同步完成")
```

## 版本历史
- **v1.0** (2026-04-17): 初始版本，基于MAREF v1.0生产部署
- **v1.1** (计划): 添加配置同步和凭据管理功能

---
**文档版本**: v1.0  
**最后更新**: 2026年4月17日  
**适用版本**: MAREF v1.0+  
**负责人**: MAREF运维团队