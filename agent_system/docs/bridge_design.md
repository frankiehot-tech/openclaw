# AutoGLM Bridge 设计文档

## 概述

AutoGLM Bridge 是 Athena Agent 与设备控制层之间的桥梁，负责：
1. 接收 Athena 的任务请求
2. 通过模型（Mock/Real）推理下一步动作
3. 执行动作并记录历史
4. 返回执行结果

## 架构

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Athena    │────▶│  AutoGLM Bridge │────▶│  Device Control  │────▶│   Z Flip3   │
│   (入口)    │     │  (决策与控制)   │     │     (ADB)        │     │   (设备)    │
└─────────────┘     └─────────────────┘     └──────────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
              ┌─────▼─────┐ ┌────▼──────┐
              │ model_    │ │ action_   │
              │ client    │ │ executor  │
              └───────────┘ └───────────┘
                    │             │
              ┌─────▼─────┐ ┌────▼──────┐
              │ (Mock/    │ │ (白名单    │
              │  Real)    │ │  校验)    │
              └───────────┘ └───────────┘
                    │
              ┌─────▼──────┐
              │  memory    │
              │ (历史记录) │
              └───────────┘
```

## 模块职责

### 1. agent_loop.py - 核心控制循环

**职责**：管理任务的完整执行流程

**核心函数**：
- `run_step(task, history, device_id)` - 执行单步
- `run_task(task, max_steps, device_id)` - 执行完整任务

**流程**：
```
1. 截图 (capture_screen)
2. 模型推理 (model_client.infer_action)
3. 执行动作 (action_executor.execute)
4. 记录历史 (memory.add_step)
5. 循环检测 (memory.is_loop_detected)
```

### 2. model_client.py - 模型客户端

**职责**：封装模型 API 调用，支持 Mock/Real 模式

**核心函数**：
- `infer_action(task, screenshot_path, history, use_mock)` - 推理动作

**Mock 模式**：
- 默认启用
- 基于任务关键词返回合理的模拟动作
- 不消耗真实 API

**Real 模式**：
- 需要配置 API_KEY 和 BASE_URL
- 调用真实的 AutoGLM / OpenAI 兼容 API

### 3. action_executor.py - 动作执行器

**职责**：将模型输出映射到 ADB 命令

**核心函数**：
- `validate_action(action)` - 动作白名单校验
- `execute(action)` - 执行动作
- `execute_with_retry(action, max_retries)` - 带重试的执行

**白名单动作**：
- `tap` - 点击
- `swipe` - 滑动
- `input_text` - 输入文本
- `back` - 返回
- `home` - 主页

### 4. memory.py - 历史记录

**职责**：记录每一步执行的信息

**核心函数**：
- `start_task(task)` - 开始新任务
- `add_step(...)` - 添加步骤记录
- `get_history()` - 获取历史
- `is_loop_detected(action, threshold)` - 循环检测

**记录字段**：
- step - 步骤编号
- task - 任务描述
- screenshot_path - 截图路径
- model_output - 模型输出
- executed_action - 执行的动作
- timestamp - 时间戳
- result - 结果 (pending/success/failed)
- error - 错误信息

## 调用关系

### Athena → Bridge

```python
from agent_system.autoglm_bridge import get_agent_loop

# 创建 Agent 循环
agent = get_agent_loop(device_id=None, use_mock=True, max_steps=5)

# 执行任务
result = agent.run_task("打开设置")
```

### Bridge → Device Control

```python
from agent_system.device_control import ADBClient, capture_screen

# 截图
screenshot = capture_screen(device_id)

# 执行动作
adb = ADBClient(device_id)
adb.tap(500, 1200)
```

## 单步执行流程

```
┌─────────────────────────────────────────┐
│           1. 截图阶段                    │
│  capture_screen(device_id)               │
│  → 返回截图路径                         │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│           2. 推理阶段                    │
│  model_client.infer_action(              │
│      task, screenshot, history           │
│  )                                      │
│  → 返回动作 JSON                        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│           3. 校验阶段                    │
│  action_executor.validate_action()      │
│  → 白名单校验 + 坐标校验                 │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│           4. 执行阶段                     │
│  action_executor.execute()              │
│  → 调用 ADB 执行动作                     │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│           5. 记录阶段                    │
│  memory.add_step(...)                   │
│  → 记录到历史 + 循环检测                │
└─────────────────────────────────────────┘
```

## Mock 模式与 Real 模式切换

### 方式 1：初始化时指定

```python
# Mock 模式（默认）
agent = get_agent_loop(use_mock=True)

# Real 模式
agent = get_agent_loop(use_mock=False)
```

### 方式 2：运行时切换

```python
agent = get_agent_loop()
agent.set_mock_mode(True)   # 切换到 Mock
agent.set_mock_mode(False)  # 切换到 Real
```

### 方式 3：单次调用覆盖

```python
# 这次调用使用 Real 模式
result = model_client.infer_action(
    task="打开设置",
    screenshot_path=None,
    history=[],
    use_mock=False  # 覆盖默认设置
)
```

## 日志

### logs/autoglm.log
- 模块内部日志
- 推理过程
- 执行结果

### logs/pipeline.log
- 流水线日志
- 任务开始/结束
- 每一步的执行

## 当前限制

1. **Mock 模式**：基于关键词的简单匹配，不具备真正的 UI 理解能力
2. **Real 模式**：尚未实现真实的 API 调用
3. **循环检测**：仅基于动作类型，未考虑坐标
4. **错误恢复**：重试机制较简单

## 后续扩展点

1. **Real 模式**：接入真实的 AutoGLM API
2. **多模态输入**：支持 Base64 编码的图片直接传给模型
3. **更丰富的动作**：支持 long press、text selection 等
4. **任务拆解**：支持将复杂任务拆分为子任务
5. **状态机**：基于 UI 状态图谱的更智能决策
6. **多设备**：支持同时控制多台设备