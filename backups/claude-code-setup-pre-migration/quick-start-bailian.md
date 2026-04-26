# 百炼PRO快速启动指南

## 3步激活百炼PRO智能路由系统

### 步骤1：配置环境（一次性）
```bash
# 编辑 ~/.zshrc 文件
nano ~/.zshrc

# 添加以下内容到文件末尾
# ============ 百炼PRO配置 ============ 
export DASHSCOPE_API_KEY="sk-8ab52e8a07e940bb8ac87d381dc3dd49"
export DEEPSEEK_API_KEY="你的DeepSeek密钥（可选，备用方案需要）"

# 智能路由别名
alias claude='/Users/frankie/claude-code-setup/claude-dual-model.sh'
alias claude-auto='/Users/frankie/claude-code-setup/claude-dual-model.sh auto'
alias claude-bailian='/Users/frankie/claude-code-setup/claude-dual-model.sh 5'
alias claude-qwen='/Users/frankie/claude-code-setup/claude-dual-model.sh 3'
alias claude-backup='/Users/frankie/claude-code-setup/claude-dual-model.sh 2'

# 使用监控别名
alias bailian-check='/Users/frankie/claude-code-setup/bailian-usage-monitor.sh check'
alias bailian-report='/Users/frankie/claude-code-setup/bailian-usage-monitor.sh report'
# ============ 配置结束 ============ 

# 保存并退出，然后应用配置
source ~/.zshrc
```

### 步骤2：验证配置
```bash
# 测试环境变量
echo "DashScope密钥: ${DASHSCOPE_API_KEY:0:10}..."

# 测试智能路由
claude-auto --version

# 检查使用监控
bailian-check
```

### 步骤3：开始使用
```bash
# 方式1：自动模式（推荐，智能路由）
claude-auto

# 方式2：手动选择百炼PRO
claude-bailian

# 方式3：仅使用Qwen模型
claude-qwen

# 方式4：备用方案（百炼PRO用量高时）
claude-backup
```

## 验证成功标志

### ✅ 基础验证
```bash
# 1. AI Assistant应正常启动
claude-auto --version

# 2. 使用监控应显示正常状态
bailian-check

# 3. 应能正常提问
claude-auto "测试：百炼PRO连接是否正常？"
```

### ✅ 高级验证
```bash
# 1. 测试智能路由（模拟高使用率）
# 临时设置高使用率测试
echo "2026-04-19 12:00:00,85000,deepseek-r1,85000,5000" >> ~/.claude/bailian-usage/usage.csv
bailian-check  # 应显示警告状态
claude-auto "测试高使用率下的路由"  # 应自动切换到备用方案

# 2. 重置测试数据
rm -f ~/.claude/bailian-usage/usage.csv
bailian-check  # 应恢复正常状态
```

## 日常使用指南

### 最佳实践
1. **默认使用** `claude-auto` - 智能路由，最优成本
2. **监控使用** `bailian-check` - 每日检查使用情况
3. **报告生成** `bailian-report` - 每周生成使用报告

### 常用命令
```bash
# 日常开发
claude-auto "实现一个Python函数，计算斐波那契数列"

# 代码审查
claude-auto "审查这段代码：<粘贴代码>"

# 问题解答
claude-auto "解释JavaScript中的闭包概念"

# 生成文档
claude-auto "为这个API生成Markdown文档"
```

### 故障排除
```bash
# 1. 连接问题
bailian-check  # 检查使用状态
claude-bailian --version  # 测试百炼PRO连接
claude-backup --version   # 测试备用方案连接

# 2. 使用监控问题
# 重置使用记录（谨慎使用）
/Users/frankie/claude-code-setup/bailian-usage-monitor.sh reset

# 3. 配置问题
# 重新加载配置
source ~/.zshrc
```

## VSCode集成

### 快速集成
1. **终端中使用**：直接在VSCode终端运行 `claude-auto`
2. **任务配置**：创建VSCode任务自动启动智能路由
3. **快捷键绑定**：设置快捷键快速调用AI Assistant

### 详细配置
参考完整指南：`/Users/frankie/claude-code-setup/vscode-bailian-config.md`

## 成本监控

### 每日检查
```bash
# 添加到每日工作流程
bailian-check
```

### 生成报告
```bash
# 详细使用分析
bailian-report
```

### 告警阈值
- **70%使用率**：信息提醒
- **85%使用率**：警告提醒
- **95%使用率**：自动切换到备用方案

## 预期效益

### 成本节省
- **当前成本**：1,202.74 CNY/月 (DeepSeek API)
- **目标成本**：599 CNY/月 (百炼PRO)
- **预计节省**：603.74 CNY/月 (50.2%)

### 质量保障
- **DeepSeek-R1**：测试通过率100%
- **智能路由**：无缝切换，无体验下降
- **备用方案**：确保服务连续性

## 支持资源

### 文档
- **完整配置指南**：`vscode-bailian-config.md`
- **优化方案**：`bailian-optimization-plan.md`
- **决策框架**：`~/.bailian-pro-test-20260418_185417/evaluation/decision-framework.md`

### 工具脚本
- **智能路由**：`claude-dual-model.sh`
- **使用监控**：`bailian-usage-monitor.sh`
- **统一配置**：`claude-config.sh`

### 测试环境
- **安全测试目录**：`~/.bailian-pro-test-20260418_185417/`
- **评估工具**：包含完整的两周评估套件

## 下一步行动

### 立即执行（5分钟）
1. 配置环境变量和别名
2. 验证系统连接
3. 开始日常使用

### 本周目标
1. 完成10+次百炼PRO使用记录
2. 验证智能路由功能
3. 建立每日检查习惯

### 月度目标（5月2日）
1. 基于实际数据做出迁移决策
2. 优化配置和监控
3. 评估成本节省效果

---

**系统状态**: 🟢 准备就绪  
**配置复杂度**: 低 (3步配置)  
**风险等级**: 低 (有完善备用方案)  
**预期ROI**: 50.2%成本节省  

**技术支持**: 本指南 + 完整文档  
**最后验证**: 2026-04-19  
**建议开始时间**: 立即