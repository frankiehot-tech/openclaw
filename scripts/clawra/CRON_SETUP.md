# MAREF日报定时任务配置

## 概述

本文档介绍如何配置MAREF日报系统的定时任务，实现每天自动生成报告并发送预警通知。

## 系统要求

- Python 3.8+
- 依赖包: `psutil` (可选，用于系统指标采集)
- 文件权限: 对输出目录 `/Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/015-mailbox` 有写权限

## 安装依赖

```bash
cd /Volumes/1TB-M2/openclaw/scripts/clawra
pip3 install psutil  # 可选，用于更准确的系统指标
```

## 手动测试

在配置cron之前，请先手动测试脚本是否正常工作：

```bash
cd /Volumes/1TB-M2/openclaw/scripts/clawra

# 使用Python直接运行
python3 run_maref_daily_report.py --verbose

# 或使用shell包装脚本
./run_maref_daily.sh
```

如果一切正常，将在输出目录生成 `maref-daily-YYYY-MM-DD.md` 文件。

## Cron配置

### 方案1：直接使用crontab

编辑当前用户的crontab：

```bash
crontab -e
```

添加以下行（每天上午9点运行）：

```cron
# MAREF日报生成 - 每天上午9点
0 9 * * * cd /Volumes/1TB-M2/openclaw/scripts/clawra && /usr/bin/python3 run_maref_daily_report.py >> /tmp/maref_cron.log 2>&1
```

或使用包装脚本：

```cron
# 使用包装脚本 - 每天上午9点
0 9 * * * /Volumes/1TB-M2/openclaw/scripts/clawra/run_maref_daily.sh >> /tmp/maref_cron_wrapper.log 2>&1
```

### 方案2：系统cron（需要root权限）

编辑系统cron文件：

```bash
sudo nano /etc/cron.d/maref-daily
```

添加以下内容（指定运行用户）：

```cron
# MAREF日报生成 - 每天上午9点，以frankie用户运行
0 9 * * * frankie cd /Volumes/1TB-M2/openclaw/scripts/clawra && /usr/bin/python3 run_maref_daily_report.py
```

### 方案3：使用launchd (macOS)

创建plist文件 `~/Library/LaunchAgents/com.athena.maref.daily.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.athena.maref.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Volumes/1TB-M2/openclaw/scripts/clawra/run_maref_daily_report.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/maref_daily.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/maref_daily_error.log</string>
    <key>WorkingDirectory</key>
    <string>/Volumes/1TB-M2/openclaw/scripts/clawra</string>
</dict>
</plist>
```

加载任务：

```bash
launchctl load ~/Library/LaunchAgents/com.athena.maref.daily.plist
```

## 运行模式配置

脚本支持两种运行模式：

1. **standalone (默认)**: 使用模拟数据，适合测试和开发
2. **integration**: 连接实际MAREF系统，需要配置实际智能体和状态管理器

通过环境变量配置模式：

```bash
# 在cron中设置环境变量
MAREF_MODE=standalone python3 run_maref_daily_report.py

# 或在包装脚本中修改export MAREF_MODE
```

## 通知渠道配置

预警通知支持多种渠道，通过配置文件启用：

1. 复制 `maref_notifier.py` 中的默认配置，创建配置文件
2. 配置企业微信、邮件、Slack等渠道
3. 在运行脚本时指定配置文件：

```bash
python3 run_maref_daily_report.py --config /path/to/notifier_config.json
```

## 日志和监控

### 日志位置

1. **脚本日志**: `logs/maref_daily_report.log`
2. **cron日志**: `/tmp/maref_cron.log` (根据cron配置)
3. **通知日志**: `/var/log/maref_notifications.log` (默认路径)
4. **成功/错误日志**: `maref_report_success.log`, `maref_report_errors.log`

### 监控日报生成状态

检查最近是否成功生成日报：

```bash
# 查看最近的成功记录
tail -n 5 /Volumes/1TB-M2/openclaw/scripts/clawra/maref_report_success.log

# 查看错误记录
tail -n 5 /Volumes/1TB-M2/openclaw/scripts/clawra/maref_report_errors.log

# 检查最新日报文件
ls -lt "/Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/015-mailbox"/maref-daily-*.md | head -5
```

## 集成到Athena工作流

### 作为独立服务运行

MAREF日报系统可以作为Athena的独立监控服务运行：

1. 将脚本部署到Athena服务器
2. 配置cron定时任务
3. 日报输出到共享目录 `/Volumes/1TB-M2/openclaw/Documents/Athena知识库/...`

### 与Athena现有系统集成

如需与Athena现有通知系统集成：

1. 修改 `maref_notifier.py` 中的 `send_to_athena_system()` 方法
2. 连接到Athena的API端点
3. 统一预警处理流程

### 扩展为实时监控

当前为每日批量报告，可扩展为实时监控：

1. 修改数据采集频率（调整cron间隔）
2. 实现实时预警（修改预警引擎阈值）
3. 集成到Athena仪表板（通过API提供数据）

## 故障排除

### 常见问题

1. **导入错误**: 确保Python路径正确，相关模块在正确位置
2. **权限错误**: 检查输出目录和日志目录的写权限
3. **通知失败**: 检查通知配置文件，网络连接
4. **状态管理器不可用**: 检查hexagram_state_manager模块路径

### 调试模式

启用详细日志：

```bash
python3 run_maref_daily_report.py --verbose
```

### 手动检查

如果cron任务失败，手动运行并检查错误：

```bash
cd /Volumes/1TB-M2/openclaw/scripts/clawra
python3 -c "from maref_daily_reporter import test_daily_reporter; test_daily_reporter()"
```

## 维护和更新

### 更新代码

从代码仓库更新MAREF日报模块：

```bash
cd /Volumes/1TB-M2/openclaw
git pull origin main  # 假设代码在git仓库中
```

### 备份配置

备份重要配置文件：
- 预警规则配置
- 通知渠道配置
- Cron配置

### 监控磁盘空间

日报文件每天生成，定期清理旧文件：

```bash
# 保留最近30天的日报
find "/Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/015-mailbox" -name "maref-daily-*.md" -mtime +30 -delete
```

## 联系方式

如有问题，请参考：
- MAREF工程实施方案文档
- 代码注释和文档
- Athena项目维护团队