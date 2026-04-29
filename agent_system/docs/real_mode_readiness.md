# 真实模式就绪检查

本文档记录阶段 5 的完成状态和待办事项。

## 已完成项

### 1. 统一 real/mock 双模式接口
- [x] `model_client.py` 提供 `infer_action(task, screenshot_path, history, use_mock=True)` 接口
- [x] mock 模式使用现有规则
- [x] real 模式调用 OpenAI-compatible API
- [x] 统一返回格式：`{"action": "tap", "params": {...}, "reason": "...", "confidence": 0.9}`
- [x] Bridge 层解析、校验、清洗模型输出

### 2. 环境变量与配置模板
- [x] `.env.example` - 配置模板
- [x] `.gitignore` - 忽略敏感文件
- [x] `docs/configuration_real_mode.md` - 配置说明文档

### 3. 真实模型客户端实现
- [x] 支持 OpenAI-compatible chat/completions 风格
- [x] 从环境变量读取配置
- [x] 超时控制（默认 60s）
- [x] 异常处理
- [x] 请求/响应摘要日志（不暴露敏感 token）
- [x] `is_real_mode_configured()` 辅助函数
- [x] `get_runtime_mode()` 辅助函数
- [x] 配置不完整时返回明确错误

### 4. 提示词与输出约束
- [x] System prompt 设计
- [x] 输出格式约束写入文档
- [x] Bridge 层兼容处理（markdown、解释性文字等）

### 5. CLI 与接口切换
- [x] `run_athena.py` 默认 mock 模式
- [x] `--real` 显式启用真实模式
- [x] 配置缺失时给出明确提示
- [x] `--check-real-config` 配置验证命令

### 6. 文档与验证
- [x] `docs/configuration_real_mode.md` - 配置指南
- [x] `docs/real_mode_readiness.md` - 本文档

## 待用户填写项

1. **配置 API 密钥**
   ```bash
   cd /Volumes/1TB-M2/openclaw/agent_system
   cp .env.example .env
   # 编辑 .env 填写实际配置
   ```

2. **验证配置**
   ```bash
   python run_athena.py --check-real-config
   ```

## 切换步骤

### 从 Mock 切换到 Real

1. 复制并编辑 `.env` 文件
2. 设置 `AUTOGLM_USE_MOCK=false`
3. 填写 `AUTOGLM_API_KEY` 和 `AUTOGLM_BASE_URL`
4. 验证配置：`python run_athena.py --check-real-config`
5. 运行任务：`python run_athena.py "打开设置" --real`

### 从 Real 切换回 Mock

1. 设置 `AUTOGLM_USE_MOCK=true`
2. 或使用命令行：`python run_athena.py "打开设置" --mock`

## 首次真实验证建议任务

建议按以下顺序验证：

1. **低风险任务** - "打开设置"
2. **返回操作** - "返回上一级"
3. **主页操作** - "回到主屏幕"

**不要**在首次验证时执行：
- 发送消息
- 拨打电话
- 修改系统设置
- 访问敏感应用

## 风险说明

1. **API 成本** - 真实模式会产生 API 调用费用
2. **网络依赖** - 需要稳定的网络连接
3. **模型输出** - 模型可能产生意外动作
4. **设备状态** - 实际操作手机，建议先在测试环境验证

## 当前可确认能力

- ✅ Mock 模式完整可用
- ✅ 配置检查命令可用
- ✅ 真实模式代码已实现（未实际调用）
- ✅ 模式切换机制就绪

## 是否建议进入阶段 6

**是**，理由：
1. 阶段 5 已完成所有代码实现
2. Mock 模式已验证可用
3. 真实模式配置检查就绪
4. 阶段 6（最小任务验证）可以使用 Mock 模式进行
5. 用户可以随时配置真实 API 并切换