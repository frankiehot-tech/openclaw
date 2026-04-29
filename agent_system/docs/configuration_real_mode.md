# 真实模式配置指南

本文档说明如何配置和使用真实 AutoGLM 模式。

## 环境变量说明

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `AUTOGLM_API_KEY` | 是 | - | API 密钥 |
| `AUTOGLM_BASE_URL` | 是 | - | API 基础 URL |
| `AUTOGLM_MODEL` | 否 | gpt-4 | 模型名称 |
| `AUTOGLM_TIMEOUT` | 否 | 60 | 请求超时（秒） |
| `AUTOGLM_USE_MOCK` | 否 | true | 是否使用 Mock 模式 |
| `ADB_SERIAL` | 否 | - | 设备序列号 |
| `LOG_LEVEL` | 否 | INFO | 日志级别 |

## 配置步骤

### 1. 复制配置模板

```bash
cd /Volumes/1TB-M2/openclaw/agent_system
cp .env.example .env
```

### 2. 编辑 .env 文件

填写实际配置：

```bash
# 示例配置
AUTOGLM_API_KEY=sk-xxxxx
AUTOGLM_BASE_URL=https://api.openai.com/v1
AUTOGLM_MODEL=gpt-4
AUTOGLM_USE_MOCK=false
```

### 3. 验证配置

```bash
python run_athena.py --check-real-config
```

## 切换模式

### 从 Mock 切换到 Real

1. 编辑 `.env` 文件，设置：
   ```
   AUTOGLM_USE_MOCK=false
   AUTOGLM_API_KEY=your_api_key
   AUTOGLM_BASE_URL=your_base_url
   ```

2. 验证配置：
   ```bash
   python run_athena.py --check-real-config
   ```

3. 运行任务：
   ```bash
   python run_athena.py "打开设置" --real
   ```

### 从 Real 切换回 Mock

1. 编辑 `.env` 文件，设置：
   ```
   AUTOGLM_USE_MOCK=true
   ```

2. 或使用命令行参数：
   ```bash
   python run_athena.py "打开设置" --mock
   ```

## System Prompt 约束

真实模式下，模型会收到以下 system prompt：

```
你是一个手机控制助手。根据当前屏幕截图和任务描述，输出下一步操作。

输出格式要求（必须严格遵循）：
```json
{
  "action": "tap|swipe|input_text|back|home",
  "params": {
    "x": 500,
    "y": 1200
  },
  "reason": "操作原因",
  "confidence": 0.9
}
```

动作说明：
- tap: 点击，params 需要 x, y 坐标
- swipe: 滑动，params 需要 x1, y1, x2, y2
- input_text: 输入文本，params 需要 text
- back: 返回键
- home: 主页键

只输出 JSON，不要输出其他解释文字。
```

## 输出格式兼容

Bridge 层会处理以下情况：

1. **纯 JSON**: `{"action": "tap", ...}`
2. **Markdown 包裹**: ```json {"action": "tap", ...} ```
3. **包含解释**: `根据屏幕分析，应该点击设置图标 {"action": "tap", ...}`

如果解析失败，会返回错误动作并记录日志。

## 故障排查

### 配置检查失败

```bash
$ python run_athena.py --check-real-config

配置状态:
  API_KEY: ✗ 未检测到
  BASE_URL: ✗ 未检测到
  MODEL: ✓ gpt-4
  当前模式: mock
```

### API 调用失败

检查日志文件：`logs/autoglm.log`

常见错误：
- `401`: API 密钥无效
- `404`: BASE_URL 错误
- `timeout`: 请求超时
- `connection`: 网络连接问题

## 安全注意事项

1. **不要提交 .env 文件** - 已在 .gitignore 中排除
2. **不要在日志中暴露 API Key** - 已做脱敏处理
3. **生产环境使用最小权限 API Key**