# OpenHuman AIAG Skill

## 概述
AIAG (AI Authentication Gateway) 身份网关 - 基于 OpenHuman 协议的认证与授权服务组件

## 功能模块

### 1. OTP 验证 (One-Time Password)
- 生成 6 位数字验证码
- 有效期 5 分钟
- 短信/邮件发送支持

### 2. 身份认证
- 用户名密码验证
- OAuth 2.0 第三方登录
- JWT Token 签发

### 3. 权限管理
- RBAC 角色权限模型
- Skill-Matcher 集成
- 地理位置感知授权

## 集成接口

```python
from openhuman_aiag import AIAGateway

# 初始化网关
gateway = AIAGateway(
    skill_matcher_endpoint="http://localhost:8080",
    otp_ttl=300,
    jwt_secret="your-secret-key"
)

# OTP 发送
result = gateway.send_otp(user_id="user123", channel="sms")

# 验证 OTP
is_valid = gateway.verify_otp(user_id="user123", otp_code="123456")

# 技能匹配认证
auth_result = gateway.authenticate_with_skill_match(
    user_id="user123",
    required_skills=["python", "docker"],
    location="上海"
)

# JWT Token 签发
token = gateway.issue_token(user_id="user123", roles=["developer"])
```

## 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| skill_matcher_endpoint | str | - | Skill-Matcher 服务地址 |
| otp_ttl | int | 300 | OTP 有效期(秒) |
| jwt_secret | str | - | JWT 签名密钥 |
| jwt_expiry | int | 3600 | Token 有效期(秒) |

## 安全特性

- OTP 加密传输
- 请求频率限制 (10 req/min)
- IP 黑名单过滤
- 审计日志记录

## 状态

- **版本**: v1.0 (MVP-3)
- **状态**: 逆向补全 (Generator Pattern)
- **最后更新**: 2026-03-25