---
name: bailian-platform
description: 阿里云百炼平台维护技能包 - API配置、安全设置、模型管理、故障排查
---

# 阿里云百炼平台维护技能包

## 🎯 核心功能

提供完整的阿里云百炼平台维护和故障排查支持，包括：
- 🔑 API密钥验证和配置管理
- 🛡️ IP白名单安全配置
- 🤖 模型可用性检查和管理
- 🔌 API端点兼容性测试
- 🐛 常见故障诊断和修复
- 📊 账号使用情况监控
- 🔄 替代方案集成（OpenAI兼容API）

## 🚀 快速开始

### 1. 环境准备
```bash
# 安装必要工具
brew install jq curl

# 配置环境变量（添加到 ~/.zshrc）
export DASHSCOPE_API_KEY="sk-8ab52e8a07e940bb8ac87d381dc3dd49"
export DEEPSEEK_API_KEY="sk-546c574d2dea4cf3b22dea8bc3708197"
export ALIYUN_API_KEY="sk-921103e3b7bb4d4bb1d97308c43c71fc"

# 启用工作流别名
source ~/.zshrc
```

### 2. 运行完整维护检查
```bash
./dashscope-maintenance.sh --all
```

### 3. 验证配置
```bash
./claude-config.sh check
```

## 🛠️ 维护功能详解

### 1. API密钥管理

#### 密钥验证
```bash
# 验证百炼API密钥
curl -s -X GET "https://dashscope.aliyuncs.com/api/v1/models" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -o /dev/null -w "HTTP状态码: %{http_code}\n"

# 验证DeepSeek API密钥
curl -s -X GET "https://api.deepseek.com/v1/v1/models" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -o /dev/null -w "HTTP状态码: %{http_code}\n"
```

#### 密钥配置策略
```bash
# 统一配置文件：claude-config.sh
cat > /Users/frankie/claude-code-setup/claude-config.sh << 'EOF'
#!/bin/bash
# AI Assistant 配置文件
# 统一管理 DeepSeek 和阿里云 API 配置

# 默认配置
DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-sk-8ab52e8a07e940bb8ac87d381dc3dd49}"
DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}"
ALIYUN_API_KEY="${ALIYUN_API_KEY:-sk-921103e3b7bb4d4bb1d97308c43c71fc}"

# DeepSeek 配置
DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
DEEPSEEK_CHAT_MODEL="deepseek-chat"
DEEPSEEK_REASONER_MODEL="deepseek-reasoner"

# 阿里云 DashScope 配置
DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com"
DASHSCOPE_COMPATIBLE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_MODEL_QWEN_MAX="qwen3.6-max"  # 注意：可能不可用
DASHSCOPE_MODEL_QWEN_PLUS="qwen3.6-plus"
DASHSCOPE_MODEL_QWEN_FLASH="qwen3.5-flash"
DASHSCOPE_MODEL_QWEN_PLUS_OLD="qwen3.5-plus"

# 导出配置函数
export_config() {
    local model_type="$1"
    case $model_type in
        "deepseek-chat")
            export LLM_BASE_URL="$DEEPSEEK_BASE_URL"
            export LLM_MODEL="$DEEPSEEK_CHAT_MODEL"
            export LLM_AUTH_TOKEN="${DEEPSEEK_API_KEY:-$ALIYUN_API_KEY}"
            ;;
        "deepseek-reasoner")
            export LLM_BASE_URL="$DEEPSEEK_BASE_URL"
            export LLM_MODEL="$DEEPSEEK_REASONER_MODEL"
            export LLM_AUTH_TOKEN="${DEEPSEEK_API_KEY:-$ALIYUN_API_KEY}"
            ;;
        "qwen3.6-plus")
            export LLM_BASE_URL="$DASHSCOPE_COMPATIBLE_URL"
            export LLM_MODEL="qwen3.6-plus"
            export LLM_AUTH_TOKEN="$DASHSCOPE_API_KEY"
            ;;
        *)
            echo "未知模型类型: $model_type"
            return 1
            ;;
    esac
    export AI_MODE_BARE=1
    export AI_SKIP_KEYCHAIN=1
}
EOF
```

### 2. IP白名单安全配置

#### 自动配置脚本
```bash
# 运行安全配置脚本
./aliyun-security-setup.sh

# 手动检查IP白名单
echo "当前公网IP: $(curl -s ifconfig.me)"
echo "请登录阿里云控制台配置："
echo "https://yundun.console.aliyun.com/?p=scnew#/sc/whitelist/ip"
```

#### 安全配置要点
1. **启用白名单**：在「允许通过 AccessKey 访问的来源网络地址」中启用
2. **添加公网IP**：添加当前IP到白名单，设置为永久有效
3. **拒绝专有网络**：按策略默认拒绝，仅允许指定公网IP访问
4. **定期更新**：动态IP用户需要定期更新白名单

### 3. 模型可用性管理

#### 模型状态检查
```bash
# 检查所有Qwen模型
./test-all-qwen-models.sh

# 检查特定模型
curl -s -X GET "https://dashscope.aliyuncs.com/api/v1/models" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" | \
  jq '.output.models[] | select(.model | contains("qwen")) | {model: .model, name: .name, provider: .provider}'
```

#### 已知问题解决方案
- **Qwen3.6-Max不可用**：使用Qwen3.6-Plus作为替代
- **LLM格式不支持**：使用OpenAI兼容API端点（/chat/completions）
- **套餐额度限制**：Qwen Coding Plan Pro提供90,000次/月调用

### 4. API端点兼容性

#### 可用端点测试
```bash
# 测试OpenAI兼容端点
curl -s -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.6-plus",
    "messages": [{"role": "user", "content": "test"}],
    "temperature": 0.7
  }' | jq '.'

# 测试标准端点
curl -s -X GET "https://dashscope.aliyuncs.com/api/v1/models" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" | jq '.'
```

#### 兼容性总结
| 端点类型 | 状态 | 用途 | 替代方案 |
|---------|------|------|----------|
| OpenAI兼容 | ✅ 可用 | Qwen模型调用 | 主要使用 |
| LLM兼容 | ❌ 不可用 | AI Assistant直接连接 | 不可用 |
| 标准REST | ✅ 可用 | 模型列表、账户信息 | 管理功能 |

### 5. 故障排查流程

#### 诊断矩阵
```bash
# 完整诊断脚本
./dashscope-maintenance.sh --all

# 分步诊断
./dashscope-maintenance.sh --api-key    # API密钥验证
./dashscope-maintenance.sh --models     # 模型可用性
./dashscope-maintenance.sh --endpoints  # 端点兼容性
./dashscope-maintenance.sh --ip         # IP白名单
./dashscope-maintenance.sh --test       # 模型推理测试
./dashscope-maintenance.sh --usage      # 账户使用情况
```

#### 常见错误及解决方案

**错误1：API密钥无效 (401)**
```bash
# 验证密钥
./test-api-keys.sh

# 解决方案：
# 1. 检查密钥是否正确
# 2. 检查密钥是否过期
# 3. 检查IP是否在白名单中
```

**错误2：模型不可用 (404)**
```bash
# 检查模型列表
curl -s -X GET "https://dashscope.aliyuncs.com/api/v1/models" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" | \
  jq '.output.models[].model'

# 解决方案：
# 1. 使用可用的替代模型（如qwen3.6-plus替代qwen3.6-max）
# 2. 检查套餐是否包含该模型
```

**错误3：AI Assistant不兼容**
```bash
# 测试端点兼容性
./test-qwen-openai.sh

# 解决方案：
# 使用替代脚本 claude-qwen-alt.sh
```

### 6. 工作流别名系统

#### 6个核心别名
```bash
# 核心别名
alias claude='/Users/frankie/claude-code-setup/claude-dual-model.sh'      # 交互选择所有模型
alias claude-dual='/Users/frankie/claude-code-setup/claude-dual-model.sh' # 同claude

# 专用工作流
alias claude-max='/Users/frankie/claude-code-setup/claude-qwen-alt.sh -m qwen3.6-plus'  # Qwen最强性能
alias claude-dev='/Users/frankie/claude-code-setup/claude-dual-model.sh 2'              # DeepSeek R1新功能开发
alias claude-fix='/Users/frankie/claude-code-setup/claude-dual-model.sh 1'              # DeepSeek Chat Bug修复
alias claude-zh='/Users/frankie/claude-code-setup/claude-qwen-alt.sh'                   # Qwen中文项目

# 备用别名
alias claude-qwen='/Users/frankie/claude-code-setup/claude-qwen-alt.sh'
alias claude-deepseek='/Users/frankie/claude-code-setup/claude-dual-model.sh 1'
```

#### 别名安装脚本
```bash
# 运行别名配置
./setup-aliases.sh

# 选择自动安装选项
# 或手动复制到 ~/.zshrc
```

## 📊 监控和维护计划

### 定期检查任务
```bash
# 每日检查（添加到crontab）
0 9 * * * /Users/frankie/claude-code-setup/dashscope-maintenance.sh --report >> ~/dashscope-maintenance.log

# 每周完整检查
0 9 * * 1 /Users/frankie/claude-code-setup/dashscope-maintenance.sh --all >> ~/dashscope-maintenance-full.log
```

### 关键监控指标
1. **API可用性**：每日验证端点响应
2. **模型状态**：检查关键模型可用性
3. **使用量**：监控套餐额度使用情况
4. **IP白名单**：确认当前IP在列表中
5. **密钥有效期**：检查密钥是否过期

## 🔧 集成到AI Assistant工作流

### 智能识别维护需求
当用户描述包含以下关键词时自动触发：
- "百炼"、"DashScope"、"阿里云AI"
- "API密钥"、"认证失败"、"401错误"
- "IP白名单"、"安全组"、"网络访问"
- "模型不可用"、"Qwen"、"端点兼容"
- "维护"、"诊断"、"故障排查"

### 自动执行维护步骤
```bash
# 示例：用户报告"API密钥无效"
1. 运行 ./test-api-keys.sh
2. 检查IP白名单状态
3. 验证模型可用性
4. 提供修复建议
```

### 与现有技能协同
- **优化工作流**：复杂维护任务使用并行诊断
- **上下文管理**：保留维护历史和配置变更
- **MCP集成**：与GitHub、文件系统MCP协同管理配置
- **gstack集成**：应用安全审查和质量门禁

## 🚀 使用场景示例

### 场景1：新环境配置
```
用户: "新电脑上配置百炼平台访问"

技能自动执行:
1. 检查并安装必要工具 (jq, curl)
2. 配置环境变量和API密钥
3. 运行IP白名单配置脚本
4. 验证所有端点连接
5. 设置工作流别名
6. 生成配置报告
```

### 场景2：故障诊断
```
用户: "AI Assistant连接百炼失败，显示模型不可用"

技能自动执行:
1. 运行完整诊断: ./dashscope-maintenance.sh --all
2. 检查API密钥有效性
3. 验证IP白名单配置
4. 测试模型可用性
5. 检查端点兼容性
6. 提供具体修复方案
```

### 场景3：安全加固
```
用户: "加强百炼平台的安全配置"

技能自动执行:
1. 运行安全配置脚本: ./aliyun-security-setup.sh
2. 检查当前白名单配置
3. 推荐安全最佳实践
4. 设置定期监控任务
5. 生成安全配置报告
```

### 场景4：模型迁移
```
用户: "Qwen3.6-Max不可用，需要迁移到替代方案"

技能自动执行:
1. 确认Qwen3.6-Max状态
2. 推荐Qwen3.6-Plus作为替代
3. 更新所有相关脚本和别名
4. 测试替代方案可用性
5. 提供迁移指南
```

## 📁 工具文件说明

### 核心维护脚本
- `dashscope-maintenance.sh` - 完整的百炼账号维护脚本
- `claude-config.sh` - 统一配置管理
- `aliyun-security-setup.sh` - IP白名单配置
- `setup-aliases.sh` - 工作流别名配置

### 诊断工具
- `test-api-keys.sh` - API密钥验证
- `test-all-qwen-models.sh` - 模型可用性检查
- `test-qwen-openai.sh` - 端点兼容性测试
- `diagnose-qwen.sh` - Qwen专属诊断

### 替代方案
- `claude-qwen-alt.sh` - OpenAI兼容API调用Qwen
- `claude-dual-model.sh` - 双模型切换脚本
- `claude-zh.sh` - 中文项目工作流
- `claude-max.sh` - Qwen最强性能工作流

## 📝 最佳实践指南

### 1. 配置管理
- 使用统一的 `claude-config.sh` 管理所有API密钥
- 环境变量优先于硬编码配置
- 定期备份重要配置

### 2. 安全策略
- 始终启用IP白名单，仅允许必要IP访问
- 定期轮换API密钥
- 监控异常访问模式

### 3. 故障预防
- 设置定期维护任务（cron）
- 监控套餐额度使用情况
- 保持工具和脚本更新

### 4. 性能优化
- 选择合适的模型（Qwen3.6-Plus平衡性能与成本）
- 使用批处理减少API调用次数
- 缓存常用响应结果

### 5. 版本兼容
- 定期测试端点兼容性
- 关注阿里云API更新公告
- 准备替代方案应对API变更

## 🔄 持续改进

### 反馈循环
1. **监控运行日志**：分析维护脚本输出
2. **收集用户反馈**：记录常见问题和解决方案
3. **定期更新脚本**：根据反馈改进维护流程
4. **测试新功能**：验证阿里云平台新特性

### 知识共享
- 维护经验文档化
- 常见问题解决方案库
- 最佳实践案例分享

---

**💡 提示**: 此技能已集成到AI Assistant的智能维护系统中，可根据百炼平台状态自动推荐和执行相应的维护操作。定期运行 `./dashscope-maintenance.sh --report` 可保持平台健康状态。