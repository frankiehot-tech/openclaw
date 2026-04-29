# Pipeline Validation - 链路验证文档

## 测试目标

验证 Athena → AutoGLM Bridge → ADB → Samsung Galaxy Z Flip3 的完整控制链路可用性。

## 测试范围

### 目标
- [x] 验证任务路由正确（Athena → task_router）
- [x] 验证模型推理可用（mock 模式）
- [x] 验证动作执行器正确（action_executor → adb_client）
- [x] 验证日志记录完整
- [x] 验证无设备时优雅报错

### 非目标
- ❌ 不测试真实模型 API
- ❌ 不执行敏感操作（危险点击）
- ❌ 不测试复杂多步任务
- ❌ 不测试真实设备 UI 识别

---

## Mock 执行动作规则

当前阶段使用关键词匹配返回固定动作，不涉及真实 UI 理解。

### 动作映射表

| 任务关键词 | 返回动作 | 参数 | 说明 |
|-----------|---------|------|------|
| 设置 / settings | tap | x=540, y=1400 | 点击设置图标位置 |
| 返回 / back | back | - | 执行返回键 |
| 主页 / home | home | - | 执行主页键 |
| 滑动 / swipe | swipe | x1=540,y1=2000 → x2=540,y2=500 | 向上滑动 |
| 搜索 / search | tap | x=540, y=300 | 点击搜索框 |
| 输入 / input | input_text | text="test" | 输入文本 |
| 默认 | 随机 | - | 从预设动作中随机选择 |

### 统一输出格式

```json
{
  "action": "tap",
  "params": {
    "x": 540,
    "y": 1400
  },
  "reason": "点击设置图标",
  "confidence": 0.92
}
```

### 旧格式兼容

支持旧格式自动转换：
```json
{"action": "tap", "x": 500, "y": 1200, "reasoning": "..."}
```
→ 转换为 →
```json
{"action": "tap", "params": {"x": 500, "y": 1200}, "reason": "...", "confidence": 0.9}
```

---

## 测试环境

- **Python**: 3.x
- **ADB**: 已安装
- **设备**: Samsung Galaxy Z Flip3 (可选)
- **日志目录**: `/Volumes/1TB-M2/openclaw/agent_system/logs/`

### 日志文件

| 文件 | 用途 |
|------|------|
| `logs/device.log` | 设备控制层日志 |
| `logs/autoglm.log` | AutoGLM Bridge 日志 |
| `logs/athena.log` | Athena 接入层日志 |
| `logs/pipeline.log` | 链路测试日志 |
| `logs/full_pipeline.log` | 完整链路日志 |

---

## 测试命令

### 运行完整测试套件

```bash
cd /Volumes/1TB-M2/openclaw/agent_system
python tests/test_pipeline_mock.py
```

### 运行单个测试

```bash
# 测试任务路由
python -c "
from athena_adapter.task_router import TaskRouter
r = TaskRouter()
print(r.route('打开设置', 'zflip3'))
"

# 测试模型客户端
python -c "
from autoglm_bridge.model_client import ModelClient
c = ModelClient(use_mock=True)
print(c.infer_action('打开设置', None, []))
"

# 测试动作执行器
python -c "
from autoglm_bridge.action_executor import ActionExecutor
e = ActionExecutor()
print(e.validate_action({'action': 'tap', 'params': {'x': 540, 'y': 1200}}))
"
```

### 检查设备

```bash
# 使用脚本
bash agent_system/scripts/check_device.sh

# 或直接使用 adb
adb devices
```

---

## 测试任务

### 最小安全任务

| 任务 | 风险 | 说明 |
|------|------|------|
| 打开设置 | 低 | 模拟点击设置图标 |
| 返回上一级 | 低 | 执行系统返回键 |
| 回到主屏幕 | 低 | 执行系统主页键 |
| 向上滑动 | 低 | 模拟滑动操作 |

### 不允许的任务（当前阶段）

- ❌ 打开浏览器
- ❌ 发送短信
- ❌ 拨打电话
- ❌ 访问敏感应用

---

## 成功标准

1. **Task Router**: 所有测试任务能正确路由
2. **Model Client (Mock)**: 所有任务返回有效动作
3. **Action Executor**: 动作校验通过
4. **Pipeline**: 完整链路执行无报错
5. **日志**: 所有操作记录到对应日志文件

---

## 失败场景

| 场景 | 预期行为 |
|------|----------|
| 无设备 | 优雅报错，日志记录 |
| 无效任务 | Task Router 拒绝 |
| 无效动作 | Action Executor 校验失败 |
| API 错误 | 捕获异常，返回错误信息 |

---

## 后续进入真实模型模式前还缺什么

1. **真实 API 配置**: 需要配置 API_KEY, BASE_URL, MODEL
2. **UI 理解能力**: 当前 mock 不理解真实 UI，需要 AutoGLM
3. **多步任务**: 当前只支持单步执行
4. **状态检测**: 需要识别当前屏幕内容
5. **错误恢复**: 需要更完善的错误处理和重试机制

---

## 测试报告

### 测试环境
- OS: macOS
- Python: 3.x
- ADB: 已安装
- 设备: Samsung Galaxy Z Flip3 (R3CR80FKA0V)

### 测试命令
```bash
cd /Volumes/1TB-M2/openclaw/agent_system
python3 tests/test_pipeline_mock.py
```

### 测试结果
| 测试项 | 状态 | 说明 |
|--------|------|------|
| Task Router | ✅ 通过 | 所有任务正确路由 |
| Model Client (Mock) | ✅ 通过 | 所有任务返回有效动作 |
| Action Executor | ✅ 通过 | 动作校验通过 |
| Pipeline | ✅ 通过 | 完整链路执行无报错 |
| 无设备行为 | ✅ 通过 | 优雅报错，日志记录 |
| 设备在线 | ✅ 通过 | 发现设备 R3CR80FKA0V |

### 实际执行的任务
| 任务 | 动作 | 结果 |
|------|------|------|
| 打开设置 | tap (540, 1400) | ✅ 成功 |
| 返回上一级 | back | ✅ 成功 |
| 回到主屏幕 | back | ✅ 成功 |
| 向上滑动 | swipe (540,2000→540,500) | ✅ 成功 |

### 日志位置
- `logs/device.log`
- `logs/autoglm.log`
- `logs/athena.log`
- `logs/pipeline.log`
- `logs/full_pipeline.log`
- `logs/screenshots/` (截图)

### 发现的问题
无

### 修复记录
无

### 进入真实模式前还缺什么
1. 真实 API 配置 (API_KEY, BASE_URL, MODEL)
2. UI 理解能力 (AutoGLM)
3. 多步任务支持
4. 状态检测
5. 错误恢复机制
