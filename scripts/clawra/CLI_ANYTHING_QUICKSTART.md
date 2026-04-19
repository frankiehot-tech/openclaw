# CLI-Anything 快速启动指南

## 问题概述
1. **QQ邮箱**：SMTP密码不是16位授权码，邮件发送失败
2. **企业微信**：Webhook端点错误 + IP白名单限制

## 立即解决QQ邮箱问题

### 方法1：交互式解决（推荐）
```bash
# 运行交互式工具
python3 qqmail_authcode_resolver.py interactive
```

**步骤**：
1. 工具将打开Safari并显示操作指南
2. 按照浏览器中的指导获取16位授权码
3. 在对话框中输入授权码
4. 工具自动更新配置并测试连接

### 方法2：分步操作
```bash
# 1. 查看详细指南
python3 qqmail_authcode_resolver.py guide

# 2. 手动获取授权码后更新配置
python3 qqmail_authcode_resolver.py update --auth-code 你的16位授权码

# 3. 测试SMTP连接
python3 qqmail_authcode_resolver.py test-smtp
```

## 企业微信问题诊断

### 了解当前问题
```bash
# 查看完整诊断
python3 wecom_cli_prototype.py diagnose

# 单独测试webhook
python3 wecom_cli_prototype.py test-webhook

# 单独测试应用API
python3 wecom_cli_prototype.py test-api

# 获取服务器IP
python3 wecom_cli_prototype.py server-ip
```

### 问题确认
1. ✅ **Access Token获取成功**：CorpID、AgentId、Secret正确
2. ❌ **IP白名单错误**：服务器IP `124.240.115.101` 不在白名单中
3. ❌ **Webhook端点错误**：`http://127.0.0.1:18789/wecom/webhook` 不是webhook接收器

## 企业微信解决方案选择

### 方案A：Webhook转发器（推荐短期方案）
**优点**：快速，不依赖外部变更
**操作**：需要开发简单的HTTP转发服务

### 方案B：IP白名单自动化（CLI-Anything方案）
**优点**：解决根本问题
**操作**：通过浏览器自动化添加IP到白名单

### 方案C：企业微信机器人webhook
**优点**：配置简单
**缺点**：功能有限

## 完整系统测试

### 更新QQ邮箱后测试
```bash
python3 test_notification_channels_final.py
```

**预期结果**：
- ✅ 邮件SMTP测试通过
- ✅ 控制台日志正常
- ✅ 文件日志正常
- ❌ 企业微信测试失败（预期中）
- ✅ 通知器集成测试部分通过

## 紧急应对措施

### 如果急需通知功能
1. **立即启用**：控制台日志 + 文件日志（已正常工作）
2. **今天完成**：QQ邮箱授权码配置
3. **临时方案**：使用邮件通知作为主要渠道

### 企业微信临时方案
```bash
# 手动添加IP白名单步骤：
1. 登录 https://work.weixin.qq.com
2. 进入应用管理，找到应用ID: 1000002
3. 添加服务器IP: 124.240.115.101 到白名单
4. 保存配置，等待5-10分钟生效
```

## 后续开发选项

### 如需CLI-Anything自动化开发
1. **Safari权限配置**：
   - 打开 Safari → 偏好设置 → 高级
   - 勾选"允许JavaScript来自Apple事件"

2. **技术验证**：
   ```bash
   python3 qqmail_cli_prototype.py test
   ```

3. **开发参考**：
   - `external/ROMA/cli_anything_doubao_validation.md` - 验证报告
   - `external/ROMA/doubao_cli_prototype.py` - 豆包原型代码

## 关键文件说明

| 文件 | 用途 |
|------|------|
| `qqmail_authcode_resolver.py` | QQ邮箱授权码问题解决工具 |
| `wecom_cli_prototype.py` | 企业微信诊断和解决方案工具 |
| `qqmail_cli_prototype.py` | 浏览器自动化原型 |
| `cli_anything_solution_summary.md` | 完整解决方案文档 |
| `.env` | 环境变量配置文件（需更新） |

## 紧急联系人/下一步

1. **立即执行**：`python3 qqmail_authcode_resolver.py interactive`
2. **决策需求**：选择企业微信解决方案（A/B/C）
3. **验证目标**：今天内恢复邮件通知功能
4. **监控计划**：明天9点观察日报系统是否自动执行

## 故障排除

### QQ邮箱工具问题
```bash
# 如果交互式工具失败，手动操作：
1. 手动获取16位授权码
2. 编辑 `.env` 文件，更新 SMTP_PASSWORD
3. 运行测试确认：python3 test_notification_channels_final.py
```

### 权限问题
```bash
# 如果AppleScript权限错误
1. 系统偏好设置 → 安全性与隐私 → 隐私
2. 添加终端或iTerm到自动化权限
```

### 网络问题
```bash
# 如果API测试失败
1. 检查网络连接
2. 暂时跳过企业微信测试，先解决QQ邮箱
```

---
**最后更新**：2026-04-17  
**状态**：QQ邮箱工具就绪，企业微信方案待选择