---
name: maref-notification-audit
description: MAREF通知系统配置审计技能，映射Athena和Claude Code工作流
---

# MAREF通知系统配置审计技能

## 当前状态总结（2026-04-17）

### ✅ 成功完成部分
1. **QQ邮箱SMTP配置修复**
   - 16位授权码：`REDACTED_QQ_PASSWORD`
   - SMTP服务器：`smtp.qq.com:587` (TLS)
   - 发送者：`athenabot@qq.com`
   - **验证状态**：完全正常，可立即用于生产环境日报

2. **企业微信API基础验证**
   - CorpID：`ww02c09b741b716c32`
   - AgentId：`1000002`（老应用，需新建解决历史限制）
   - Secret：已验证有效，可获取access_token（7200秒有效期）
   - **验证状态**：API连通性正常，但受IP白名单限制

3. **自动化工具套件就绪**
   - `verify_wecom_credentials.py` - API直接验证工具
   - `test_notification_channels_final.py` - 多渠道测试工具
   - `wecom_final_solution.md` - 解决方案文档
   - `wecom_ip_whitelist_configurator.py` - 自动化配置尝试工具

### ⚠️ 待解决问题
1. **企业微信IP白名单限制**（errcode 60020）
   - 服务器IP：`124.240.115.101` 未在白名单中
   - **根本原因**：老应用有"先配置域名/回调URL才能编辑IP白名单"的历史限制
   - **解决方案**：新建企业微信应用绕过历史限制

## 映射到Athena和Claude Code

### Athena机器人平台映射
```
Athena命令模式：
- 状态查询：/notification_audit_status
- 邮件测试：/test_email_notification
- 企业微信测试：/test_wecom_api
- 解决方案获取：/get_wecom_solution
```

### Claude Code技能映射
```
Claude Code命令：
- /notification-audit-status - 查看当前配置状态
- /test-email-smtp - 测试QQ邮箱SMTP连接
- /test-wecom-api - 测试企业微信API连通性
- /create-wecom-app - 指导创建新企业微信应用
```

## 一键检查命令

### 环境检查
```bash
# 1. 检查.env关键配置
grep -E "SMTP_PASSWORD|WECOM_CORPID|WECOM_AGENTID" .env

# 2. 测试邮件系统
python3 test_notification_channels_final.py --email-only

# 3. 测试企业微信API基础
python3 verify_wecom_credentials.py --app-api-only
```

### 生产就绪检查清单
```bash
#!/bin/bash
# maref_notification_checklist.sh

echo "=== MAREF通知系统生产就绪检查 ==="
echo "1. 邮件SMTP配置: $(python3 -c "from verify_wecom_credentials import load_env_vars; env=load_env_vars(); print('✅' if env.get('SMTP_PASSWORD') else '❌')")"
echo "2. 企业微信CorpID: $(python3 -c "from verify_wecom_credentials import load_env_vars; env=load_env_vars(); print('✅' if env.get('WECOM_CORPID') else '❌')")"
echo "3. 企业微信AgentId: $(python3 -c "from verify_wecom_credentials import load_env_vars; env=load_env_vars(); print('✅' if env.get('WECOM_AGENTID') else '❌')")"
echo "4. IP白名单状态: $(curl -s "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=xxx" 2>&1 | grep -q '60020' && echo '❌ 待配置' || echo '✅ 正常')"
```

## 新建企业微信应用步骤（绕过历史限制）

### 极简操作流程
1. **导航到应用管理**：保持Safari打开（当前URL: `#/apps`）
2. **点击"创建应用"**：页面右上角或顶部按钮
3. **填写应用信息**：
   - 名称：`MAREF通知系统`
   - 介绍：`MAREF生产环境通知推送`
   - 可见范围：全员
4. **获取新凭据**：
   - 立即记录新AgentId
   - 立即复制新Secret（只显示一次）
5. **配置IP白名单**：
   - 进入新应用详情页
   - 找到"安全设置" → "企业可信IP"
   - 添加IP：`124.240.115.101`
   - 保存配置
6. **更新环境变量**：
   ```bash
   # 更新.env文件
   WECOM_AGENTID=新的AgentId
   WECOM_SECRET=新的Secret
   ```

### 环境变量更新模板
```env
# 邮件配置（已就绪）
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=athenabot@qq.com
SMTP_PASSWORD=REDACTED_QQ_PASSWORD

# 企业微信配置（需要更新）
WECOM_CORPID=ww02c09b741b716c32
WECOM_AGENTID=新AgentId
WECOM_SECRET=新Secret
```

## 故障排除指南

### 常见错误及解决
| 错误代码 | 含义 | 解决方案 |
|----------|------|----------|
| **60020** | IP不在白名单 | 新建应用或配置IP白名单 |
| **93000** | webhook URL无效 | 获取正确webhook key |
| **SMTP 535** | 授权失败 | 使用16位授权码，非登录密码 |

### 快速诊断命令
```bash
# 诊断邮件配置
python3 -c "
import smtplib
from verify_wecom_credentials import load_env_vars
env = load_env_vars()
try:
    server = smtplib.SMTP(env['SMTP_SERVER'], env.get('SMTP_PORT', 587))
    server.starttls()
    server.login(env['SMTP_USERNAME'], env['SMTP_PASSWORD'])
    print('✅ 邮件SMTP连接正常')
except Exception as e:
    print(f'❌ 邮件SMTP连接失败: {e}')
"

# 诊断企业微信API
python3 verify_wecom_credentials.py --quick-check
```

## 生产环境部署检查点

### 今日可立即启用
- ✅ **邮件通知**：处理cron任务日报
- ✅ **控制台输出**：调试信息
- ✅ **文件日志**：持久化记录
- ⚠️ **企业微信**：需新建应用配置IP白名单

### 监控设置建议
1. **明日报送监控**：观察2026-04-18 09:00的cron任务执行
2. **异常告警**：配置邮件通知失败告警
3. **性能监控**：使用maref_monitor定期收集指标

## 技能使用示例

### Athena调用示例
```
用户：检查通知系统状态
Athena：执行 /notification_audit_status
输出：
✅ 邮件系统：就绪 (athenabot@qq.com)
⚠️ 企业微信：IP白名单待配置 (errcode 60020)
📋 建议：新建企业微信应用绕过历史限制
```

### Claude Code调用示例
```
用户：/notification-audit-status
输出：
📊 MAREF通知系统审计报告
├── ✅ 邮件：SMTP连接正常
├── ⚠️ 企业微信：API连通但IP限制
├── 📁 文件日志：/Volumes/1TB-M2/openclaw/scripts/clawra/logs/
└── 🚀 推荐操作：运行 /create-wecom-app
```

## 更新记录
- **2026-04-17**：创建技能，邮件系统修复完成，企业微信IP白名单问题待解决
- **关键发现**：企业微信老应用有历史限制，新建应用是唯一解决方案