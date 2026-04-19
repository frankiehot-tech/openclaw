# OpenClaw 告警通知系统配置指南

## 概述

OpenClaw监控系统现在支持完整的邮件和Slack告警通知功能。本指南说明如何配置和使用这些功能。

## 已实现功能

1. **邮件通知**：支持SMTP over TLS，兼容Gmail等现代邮件服务商
2. **Slack通知**：通过Incoming Webhooks发送格式化消息
3. **通知策略**：工作时间控制、告警级别过滤、频率限制
4. **多配置源**：支持环境变量、配置文件、优先使用环境变量提高安全性
5. **详细日志**：所有通知记录到日志文件，支持审计

## 配置方法（三选一）

### 方法1：环境变量（推荐，最安全）

1. 编辑 `.env` 文件：
   ```bash
   # 邮件配置（Gmail示例）
   OPENCLAW_SMTP_SERVER=smtp.gmail.com
   OPENCLAW_SMTP_PORT=587
   OPENCLAW_EMAIL_USERNAME=your-email@gmail.com
   OPENCLAW_EMAIL_PASSWORD=your-app-specific-password  # 注意：使用应用专用密码
   OPENCLAW_FROM_EMAIL=your-email@gmail.com
   OPENCLAW_TO_EMAILS=recipient1@example.com,recipient2@example.com
   
   # Slack配置
   OPENCLAW_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXXX/XXXX/XXXX
   OPENCLAW_SLACK_CHANNEL=#alerts
   OPENCLAW_SLACK_USERNAME=OpenClaw Monitor
   OPENCLAW_SLACK_ICON_EMOJI=:warning:
   
   # 通知策略
   OPENCLAW_NOTIFY_LEVELS=critical,warning
   OPENCLAW_WORKING_HOURS_START=9
   OPENCLAW_WORKING_HOURS_END=18
   OPENCLAW_AFTER_HOURS_CRITICAL_ONLY=true
   ```

2. 启用环境变量：
   ```bash
   source .env
   ```

### 方法2：配置文件

1. 复制凭据模板：
   ```bash
   cp notification_credentials_template.yaml notification_credentials.yaml
   ```

2. 编辑 `notification_credentials.yaml`，填写实际凭据

3. 更新 `config.yaml` 启用通知：
   ```yaml
   notifications_enabled: true
   notification_channels: ["log", "console", "email", "slack"]
   ```

### 方法3：混合模式（环境变量+配置文件）

- 基本配置在 `config.yaml`
- 敏感凭据在环境变量中
- 系统自动合并配置源

## Gmail配置特别说明

对于Gmail，需要：

1. **启用两步验证**（推荐）
2. **生成应用专用密码**：
   - 访问 https://myaccount.google.com/apppasswords
   - 选择"邮件"应用和"其他"设备
   - 使用生成的16位密码作为 `OPENCLAW_EMAIL_PASSWORD`

## Slack配置说明

1. **创建Incoming Webhook**：
   - 访问 https://api.slack.com/apps
   - 创建新应用或选择现有应用
   - 启用"Incoming Webhooks"
   - 添加新Webhook到所需频道
   - 复制Webhook URL

2. **自定义外观**：可修改用户名、图标和消息格式

## 测试通知系统

### 测试1：快速功能测试
```bash
# 运行监控脚本（如果队列健康，不会触发告警）
python3 monitor_queue_health.py
```

### 测试2：手动触发告警测试
```bash
# 创建一个测试脚本 trigger_test_alerts.py
cat > test_alerts.py << 'EOF'
import sys
sys.path.insert(0, '.')
from monitor_queue_health import send_notifications

test_alerts = [
    {
        'level': 'critical',
        'title': '测试严重告警',
        'message': '这是一个测试严重告警，验证邮件和Slack通知功能'
    },
    {
        'level': 'warning', 
        'title': '测试警告告警',
        'message': '这是一个测试警告告警，验证通知策略'
    }
]

# 发送测试通知
send_notifications(test_alerts, '.openclaw/maref/config/config.yaml')
EOF

python3 test_alerts.py
```

### 测试3：验证环境变量配置
```bash
# 检查环境变量是否生效
python3 -c "
import os
print('邮件服务器:', os.getenv('OPENCLAW_SMTP_SERVER', '未设置'))
print('Slack Webhook:', '已设置' if os.getenv('OPENCLAW_SLACK_WEBHOOK_URL') else '未设置')
"
```

## 通知策略详解

### 告警级别
- **critical**（严重）：系统关键问题，立即处理
- **warning**（警告）：需要注意的问题，尽快处理  
- **info**（信息）：一般性信息，选择性通知

### 工作时间控制
- **默认工作时间**: 9:00-18:00
- **非工作时间**: 只发送严重告警（可配置）

### 频率限制
- 相同告警最小间隔：5分钟（邮件）、10分钟（Slack）
- 每小时最大告警数：20（防止告警风暴）

## 故障排除

### 邮件发送失败
```
❌ 邮件认证失败
```
- 检查用户名密码是否正确
- Gmail用户：是否使用应用专用密码
- 是否启用SMTP over TLS

### Slack发送失败
```
❌ Slack请求失败
```
- 检查Webhook URL是否正确
- 检查网络连接
- 验证Slack应用权限

### 没有收到通知
```
ℹ️ 根据通知策略，无需发送外部通知
```
- 检查告警级别是否匹配策略
- 检查是否在工作时间
- 检查 `notifications_enabled` 设置

## 监控和审计

### 日志位置
```
.openclaw/monitoring_logs/alert_log_YYYYMMDD.json
```

### 日志内容
- 所有告警记录（包括未发送的）
- 发送时间和渠道
- 配置摘要（脱敏）

### 查看日志
```bash
# 查看今日告警日志
ls -la .openclaw/monitoring_logs/
cat .openclaw/monitoring_logs/alert_log_$(date +%Y%m%d).json
```

## 高级配置

### 自定义邮件模板
编辑 `monitor_queue_health.py` 中的 `_send_email_notification` 函数，修改HTML模板。

### 自定义Slack消息
编辑 `monitor_queue_health.py` 中的 `_send_slack_notification` 函数，修改消息格式。

### 添加新通知渠道
1. 在 `config.yaml` 中添加新渠道
2. 在 `monitor_queue_health.py` 中实现发送函数
3. 在 `send_notifications` 函数中添加调用

## 性能考虑

- **异步发送**：当前为同步发送，可能阻塞监控脚本
- **连接池**：未实现连接复用，每次发送新建连接
- **错误重试**：失败后不重试，防止雪崩

如需生产级使用，建议：
1. 实现异步任务队列
2. 添加连接池和重试机制
3. 集成专业监控系统（如Prometheus Alertmanager）

## 安全最佳实践

1. **永不提交凭据**：确保 `.env` 和 `notification_credentials.yaml` 在 `.gitignore` 中
2. **使用环境变量**：生产环境推荐使用环境变量或密钥管理服务
3. **定期轮换密码**：定期更新邮件应用密码和Slack Webhook
4. **访问控制**：限制可接收告警的人员和频道

---

## 更新日志

### 2026-04-19
- ✅ 实现完整邮件通知功能（SMTP over TLS）
- ✅ 实现完整Slack通知功能（Webhook集成）
- ✅ 添加环境变量支持
- ✅ 添加通知策略管理
- ✅ 创建配置指南文档

### 下一步
1. 填写实际凭据进行测试
2. 集成到CI/CD流水线
3. 添加仪表板交互式告警
4. 实现多语言支持

---

**相关文件**：
- `monitor_queue_health.py` - 主监控脚本
- `.env` - 环境变量配置模板
- `notification_credentials_template.yaml` - 凭据配置文件模板
- `config.yaml` - MAREF主配置文件
- `NOTIFICATION_SETUP_GUIDE.md` - 本配置指南