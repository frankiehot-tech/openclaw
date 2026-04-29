# Athena 接入层设计文档

## 概述

Athena 接入层是 Athena Agent 与 AutoGLM Bridge 之间的桥梁，确保：
1. Athena 不能直接访问 ADB 或设备控制层
2. 所有手机操作必须通过 AutoGLM Bridge 统一决策
3. 任务路由标准化

## 架构约束

### 调用链

```
Athena → task_router → athena_interface → agent_loop → action_executor → device_control → ADB → 手机
```

### 为什么 Athena 不能直接调用 ADB

1. **安全隔离**：防止 Athena 绕过决策层直接操作设备
2. **统一决策**：所有动作必须经过 AutoGLM 理解 UI 后决策
3. **可审计性**：所有操作都有完整的日志记录
4. **可测试性**：可以轻松 mock 整个链路进行测试

### 禁止的导入

Athena 接入层**禁止**直接导入：
- `device_control.adb_client`
- `device_control.screen_capture`
- 任何直接执行 ADB 命令的模块

## 模块职责

### 1. task_router.py - 任务路由

**职责**：验证输入并转换为统一协议格式

**核心函数**：
- `route(task, device, context)` - 路由任务
- `validate_task(task)` - 验证任务
- `validate_device(device)` - 验证设备

**输入协议**：
```json
{
  "task": "打开设置",
  "device": "zflip3",
  "context": ""
}
```

**输出协议**：
```json
{
  "task": "打开设置",
  "context": "",
  "device": "zflip3",
  "priority": 5,
  "constraints": {}
}
```

### 2. athena_interface.py - Athena 接口

**职责**：统一入口，调用 Bridge 执行任务

**核心函数**：
- `run_task(task, device, context, max_steps, use_mock)` - 执行任务

**输出协议**：
```json
{
  "success": true,
  "task": "打开设置",
  "device": "zflip3",
  "status": "success",
  "steps_executed": 3,
  "history": [],
  "error": null
}
```

### 3. run_athena.py - CLI 工具

**职责**：提供命令行接口测试

**用法**：
```bash
# Mock 模式（默认）
python run_athena.py "打开设置"

# 指定设备
python run_athena.py "打开设置" --device zflip3

# 指定最大步数
python run_athena.py "打开设置" --max-steps 3

# 真实模式
python run_athena.py "打开设置" --real

# 详细输出
python run_athena.py "打开设置" --verbose

# 检查真实模式配置
python run_athena.py --check-real-config
```

## Mock 模式测试

### 本地测试

```bash
# 测试基本任务
python run_athena.py "打开设置"
python run_athena.py "返回主页"
python run_athena.py "向上滑动"

# 测试参数
python run_athena.py "打开设置" --max-steps 5 --verbose
```

### 预期输出

```json
{
  "success": true,
  "task": "打开设置",
  "device": "zflip3",
  "status": "success",
  "steps_executed": 3,
  "final_result": "completed",
  "history": [
    {
      "step": 1,
      "action": "tap",
      "result": "success"
    }
  ]
}
```

## Real 模式切换

### 配置步骤

1. 复制 `.env.example` 为 `.env`
2. 填写配置：
   ```
   AUTOGLM_API_KEY=your_api_key
   AUTOGLM_BASE_URL=https://api.example.com
   AUTOGLM_MODEL=gpt-4
   AUTOGLM_USE_MOCK=false
   ```

3. 检查配置：
   ```bash
   python run_athena.py --check-real-config
   ```

4. 使用真实模式：
   ```bash
   python run_athena.py "打开设置" --real
   ```

## 日志

### logs/athena.log
- 任务路由日志
- 接口调用日志
- 错误信息

### logs/autoglm.log
- 模型推理日志
- 动作执行日志

### logs/pipeline.log
- 完整流水线日志
- 任务开始/结束
- 每一步执行

## 当前限制

1. **Mock 模式**：基于关键词的简单匹配
2. **设备支持**：目前只支持 zflip3/zfold3/emulator
3. **任务长度**：最大 1000 字符

## 后续扩展

1. **多设备支持**：扩展 validate_device 支持更多设备
2. **任务拆解**：支持复杂任务自动拆分为子任务
3. **状态机**：基于 UI 状态图谱的更智能路由
4. **权限控制**：基于角色的访问控制