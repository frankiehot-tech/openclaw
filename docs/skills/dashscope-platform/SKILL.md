# 阿里云百炼平台(DashScope)技能包

## 概述
阿里云百炼平台(DashScope)技能包提供完整的平台维护和故障排查支持，包括API密钥管理、IP白名单配置、模型可用性检查、API端点兼容性测试和故障诊断。

## 核心功能

### 1. API密钥管理
- API密钥验证和有效性检查
- 统一配置管理 (claude-config.sh)
- 密钥安全和轮换策略
- 多平台密钥协调

### 2. IP白名单安全配置
- 自动IP白名单配置脚本
- 安全组访问控制
- 网络访问策略管理
- 公网IP检测和更新

### 3. 模型可用性管理
- Qwen模型状态检查
- 替代模型推荐和迁移
- 套餐额度和使用情况监控
- 模型性能评估

### 4. API端点兼容性
- OpenAI兼容端点支持 (/chat/completions)
- 标准REST API管理功能
- Anthropic格式兼容性分析
- 端点可用性测试

### 5. 故障诊断和修复
- 完整诊断脚本 (dashscope-maintenance.sh)
- 分步故障排查流程
- 常见错误解决方案库
- 实时修复建议

### 6. 工作流别名系统
- 双模型切换 (DeepSeek vs Qwen)
- 专用工作流别名 (6个核心别名)
- 环境变量智能管理
- 跨平台协调

## 技术架构

### 核心组件
- **DashScope API**: 阿里云百炼平台核心API
- **OpenAI兼容端点**: `/compatible-mode/v1/chat/completions`
- **统一配置管理**: `claude-config.sh` 集中配置
- **诊断工具套件**: 完整的维护脚本集合

### 兼容性解决方案
由于DashScope不提供Anthropic格式API，采用以下解决方案：
1. **主要方案**: 使用OpenAI兼容端点调用Qwen模型
2. **替代工具**: `claude-qwen-alt.sh` 提供兼容接口
3. **双模型架构**: DeepSeek处理Anthropic格式，Qwen处理OpenAI格式
4. **智能路由**: 根据任务类型自动选择合适模型

## 配置要求

### 环境变量
```bash
export DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY}"
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY}"
export GITHUB_TOKEN="${GITHUB_TOKEN}"
```

### 关键配置
- **IP白名单**: 178.208.190.142 (已配置，永久有效)
- **主要模型**: Qwen3.6-Plus (Qwen3.6-Max不可用)
- **API兼容模式**: OpenAI格式 (`/chat/completions`)
- **套餐状态**: Qwen Coding Plan Pro (90,000次/月)

### 别名系统
```bash
alias claude="/Volumes/1TB-M2/openclaw/claude-code-setup/claude-dual-model.sh"
alias claude-max="/Volumes/1TB-M2/openclaw/claude-code-setup/claude-qwen-alt.sh -m qwen3.6-plus"
alias claude-dev="/Volumes/1TB-M2/openclaw/claude-code-setup/claude-dual-model.sh 2"
alias claude-fix="/Volumes/1TB-M2/openclaw/claude-code-setup/claude-dual-model.sh 1"
alias claude-zh="/Volumes/1TB-M2/openclaw/claude-code-setup/claude-qwen-alt.sh"
alias claude-init='eval "$(/Volumes/1TB-M2/openclaw/claude-code-setup/init-claude-env.sh --export)"'
```

## 工具脚本

### 核心维护脚本
- `dashscope-maintenance.sh` - 完整的平台维护
- `claude-config.sh` - 统一配置管理
- `aliyun-security-setup.sh` - IP白名单配置
- `setup-aliases.sh` - 别名系统配置

### 诊断工具
- `test-api-keys.sh` - API密钥验证
- `test-all-qwen-models.sh` - 模型可用性检查
- `test-qwen-openai.sh` - 端点兼容性测试
- `diagnose-qwen.sh` - Qwen专属诊断

### 替代方案工具
- `claude-qwen-alt.sh` - OpenAI兼容API调用Qwen
- `claude-dual-model.sh` - 双模型切换脚本
- `init-claude-env.sh` - 环境变量初始化

## 使用场景

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
用户: "Claude Code连接百炼失败，显示模型不可用"

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

## 故障排查

### 常见问题

#### 问题1：API密钥无效 (401)
```bash
# 验证密钥
./test-api-keys.sh

# 解决方案：
# 1. 检查密钥是否正确
# 2. 检查密钥是否过期
# 3. 检查IP是否在白名单中
```

#### 问题2：模型不可用 (404)
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

#### 问题3：Claude Code不兼容
```bash
# 测试端点兼容性
./test-qwen-openai.sh

# 解决方案：
# 使用替代脚本 claude-qwen-alt.sh
```

#### 问题4：IP白名单未配置
```bash
# 检查当前公网IP
curl -s ifconfig.me

# 运行安全配置脚本
./aliyun-security-setup.sh
```

### 诊断命令
```bash
# 完整诊断
./dashscope-maintenance.sh --all

# 分步诊断
./dashscope-maintenance.sh --api-key    # API密钥验证
./dashscope-maintenance.sh --models     # 模型可用性
./dashscope-maintenance.sh --endpoints  # 端点兼容性
./dashscope-maintenance.sh --ip         # IP白名单
./dashscope-maintenance.sh --test       # 模型推理测试
./dashscope-maintenance.sh --usage      # 账户使用情况
```

## 验证状态

### 已验证功能 (2026-04-12)
✅ **API密钥验证**: 正常 (DashScope密钥有效)  
✅ **IP白名单配置**: 正常 (IP: 178.208.190.142 已配置)  
✅ **模型可用性**: Qwen3.6-Plus可用，Qwen3.6-Max不可用  
✅ **API端点兼容性**: OpenAI兼容端点正常工作  
✅ **双模型切换**: DeepSeek和Qwen工作流正常  
✅ **诊断工具**: 完整的维护脚本套件  

### 关键配置状态
- **IP白名单**: ✅ 已配置并生效 (阿里云控制台验证)
- **主要模型**: Qwen3.6-Plus (Qwen3.6-Max的替代方案)
- **API兼容性**: OpenAI格式 (`/chat/completions`) 正常工作
- **套餐状态**: Qwen Coding Plan Pro (90,000次/月)
- **安全配置**: 公网IP白名单，专有网络默认拒绝

## 与Claude Code集成

### 智能触发关键词
当用户描述包含以下关键词时自动触发：
- "百炼"、"DashScope"、"阿里云AI"
- "API密钥"、"认证失败"、"401错误"
- "IP白名单"、"安全组"、"网络访问"
- "模型不可用"、"Qwen"、"端点兼容"
- "维护"、"诊断"、"故障排查"

### 自动工作流示例
```
用户: "API密钥无效，无法访问百炼平台"

技能自动执行:
1. 运行 ./test-api-keys.sh
2. 检查IP白名单状态
3. 验证模型可用性
4. 检查端点兼容性
5. 提供具体修复步骤
```

### 与其他技能协同
- **GitHub技能包**: 协同管理配置文件和脚本
- **gstack集成**: 应用安全审查和质量门禁
- **MCP服务器**: 与文件系统、GitHub MCP协同
- **优化工作流**: 复杂维护任务并行处理

## 最佳实践

### 配置管理
- 使用统一的 `claude-config.sh` 管理所有API密钥
- 环境变量优先于硬编码配置
- 定期备份重要配置
- 版本控制配置文件

### 安全策略
- 始终启用IP白名单，仅允许必要IP访问
- 定期轮换API密钥 (建议每3-6个月)
- 监控异常访问模式和API调用
- 最小权限原则配置访问密钥

### 故障预防
- 设置定期维护任务 (cron: 每日报告，每周完整检查)
- 监控套餐额度使用情况 (避免超额)
- 保持工具和脚本更新 (关注API变更)
- 准备备用方案应对服务中断

### 性能优化
- 选择合适的模型 (Qwen3.6-Plus平衡性能与成本)
- 使用批处理减少API调用次数
- 缓存常用响应结果 (如模型列表)
- 合理设置超时和重试策略

### 版本兼容
- 定期测试端点兼容性 (每月至少一次)
- 关注阿里云API更新公告
- 准备替代方案应对API变更
- 保持向后兼容性支持

## 持续改进

### 反馈循环
1. **监控运行日志**: 分析维护脚本输出和错误
2. **收集用户反馈**: 记录常见问题和解决方案
3. **定期更新脚本**: 根据反馈改进维护流程
4. **测试新功能**: 验证阿里云平台新特性

### 知识共享
- 维护经验文档化 (技能包、最佳实践)
- 常见问题解决方案库 (故障排除指南)
- 最佳实践案例分享 (配置模板)
- 自动化脚本模板库 (可复用组件)

### 监控和维护计划
```bash
# 每日检查 (添加到crontab)
0 9 * * * /Volumes/1TB-M2/openclaw/claude-code-setup/dashscope-maintenance.sh --report >> ~/dashscope-maintenance.log

# 每周完整检查
0 9 * * 1 /Volumes/1TB-M2/openclaw/claude-code-setup/dashscope-maintenance.sh --all >> ~/dashscope-maintenance-full.log
```

### 关键监控指标
1. **API可用性**: 每日验证端点响应时间和状态
2. **模型状态**: 检查关键模型可用性和响应质量
3. **使用量**: 监控套餐额度使用情况和剩余次数
4. **IP白名单**: 确认当前公网IP在允许列表中
5. **密钥有效期**: 检查API密钥过期时间和轮换计划

---

**版本**: 1.0.0  
**状态**: ✅ 已验证通过  
**最后更新**: 2026-04-12  
**集成状态**: 与Claude Code智能维护系统完全集成  
**维护策略**: 每日报告 + 每周完整检查  

**💡 提示**: 此技能已集成到Claude Code的智能维护系统中，可根据百炼平台状态自动推荐和执行相应的维护操作。定期运行 `./dashscope-maintenance.sh --report` 可保持平台健康状态。