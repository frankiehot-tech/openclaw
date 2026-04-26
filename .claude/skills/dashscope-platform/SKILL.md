---
name: dashscope-platform
description: "阿里云百炼平台(DashScope)技能包 — API密钥管理、IP白名单配置、模型可用性检查、故障排查。能力：api_key_management, ip_whitelist, model_availability, dashscope_api, qwen_model, openai_compatible_api"
---

# 阿里云百炼平台(DashScope)

完整技能文档见: `docs/skills/dashscope-platform/SKILL.md`

## 快速参考

- **API 密钥验证**: 确保 DASHSCOPE_API_KEY 已配置且有效
- **IP 白名单**: 确认当前 IP (178.208.190.142) 在白名单中
- **模型可用性**: 检查 qwen3.6-plus 状态，必要时切换到备选模型
- **端点兼容**: 支持 OpenAI 兼容格式 (/chat/completions)
