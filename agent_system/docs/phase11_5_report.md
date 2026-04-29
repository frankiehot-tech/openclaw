# Phase 11.5 报告：状态识别强化（最小高收益版）

## 概述

Phase 11.5 是对 Phase 11-lite 状态识别系统的增强，主要解决真机验证中 `current_state` 大量返回 `unknown` 的问题。

## 1. 为什么旧版 state_detector 容易返回 unknown

### 问题根源

1. **单点匹配机制**：旧版 state_detector 使用简单的关键词匹配，只要 OCR 文本中没有命中预定义的关键词，就直接返回 `unknown`

2. **缺乏置信度概念**：没有对状态判断进行量化评估，无法区分"确定"和"不确定"

3. **无历史信号利用**：不考虑上一步执行的动作对当前状态的影响

4. **无多维信号融合**：只依赖 OCR 文本，忽略了 UI 布局、元素分布等视觉信息

### 表现

- 大量任务初始状态为 `unknown`
- 系统依赖保守 fallback，而不是真正的状态驱动
- 状态规划（state_planner）无法有效工作

## 2. 新版打分制状态识别如何工作

### 核心设计

新版 `state_detector.py` 采用**多维打分制**，对每个候选状态分别计算得分：

```json
{
  "state": "settings_home",
  "confidence": 0.82,
  "signals": ["设置", "Wi-Fi", "蓝牙"],
  "score_breakdown": {
    "keyword_score": 0.5,
    "layout_score": 0.2,
    "history_score": 0.1,
    "ocr_density_score": 0.02
  }
}
```

### 打分维度

1. **keyword_score**：关键词组合匹配（权重最高）
   - `settings_home`: ["设置", "Wi-Fi", "蓝牙", "通用", "显示"]
   - `browser_home`: ["浏览器", "Google", "搜索", "地址"]
   - `home_screen`: ["应用", "图标", "桌面"]

2. **layout_score**：布局信号
   - 主屏幕：图标网格分布均匀
   - 设置页：垂直列表项明显
   - 浏览器页：顶部搜索/地址栏明显

3. **history_score**：历史动作信号
   - 如果上一步执行"打开设置"，当前更可能是 `settings_home`
   - 如果上一步执行"打开浏览器"，当前更可能是 `browser_home`

4. **ocr_density_score**：OCR 文本密度信号

### 阈值门控

- 最高分 >= 0.65：返回对应状态
- 最高分 < 0.65：返回 `unknown`，触发保守策略

## 3. state gate 如何在低置信度时启用保守策略

### 设计

在 `simple_state_planner.py` 中实现：

```python
STATE_CONFIDENCE_THRESHOLD = float(os.environ.get("STATE_CONFIDENCE_THRESHOLD", "0.65"))
```

### 策略

| 置信度 | 策略 |
|--------|------|
| >= 0.65 | 使用状态规划（direct_execute） |
| < 0.65 | 使用保守策略（go_home_first） |

### 日志记录

- `state_gate_used`: true/false
- `state_gate_reason`: "low_confidence" / "high_confidence"

## 4. post-action state check 如何形成闭环

### 实现位置

`agent_loop.py` 中的 `run_task` 方法

### 流程

1. **任务执行前**：检测初始状态，记录 `current_state` 和 `state_confidence`

2. **执行动作**：执行任务中的动作

3. **动作后验证**（Phase 11.5 新增）：
   - 等待 0.5 秒让页面稳定
   - 重新截图
   - 重新调用 `detect_page_state`
   - 比较 `post_action_state` 与 `target_state`

4. **验证结果**：
   - 通过：记录 `post_action_state_check_passed = true`
   - 失败：记录 `post_action_state_check_failed = true`

### 目标状态映射

| 任务关键词 | 目标状态 |
|------------|----------|
| 打开设置 | settings_home |
| 打开浏览器 | browser_home |
| 点击搜索 | browser_home |
| 搜索 | browser_home |

### 记录字段

- `post_action_state`: 动作执行后的页面状态
- `post_action_state_confidence`: 动作执行后的状态置信度
- `post_action_state_check_passed`: 验证是否通过
- `post_action_state_check_failed`: 验证是否失败
- `target_state`: 目标状态

## 5. 当前支持的目标状态验证

| 状态 | 关键词 | 验证支持 |
|------|--------|----------|
| settings_home | 打开设置 | ✅ |
| browser_home | 打开浏览器、点击搜索、搜索 | ✅ |
| home_screen | 主页、桌面 | ✅ (隐式) |

## 6. 配置项

在 `.env` 或 `.env.example` 中：

```bash
# Phase 11.5 配置
STATE_CONFIDENCE_THRESHOLD=0.65
STATE_USE_HISTORY_SIGNAL=true
STATE_ENABLE_POST_ACTION_CHECK=true
```

## 7. 真机验证任务与结果

### 验证任务

1. **打开设置**
2. **打开浏览器**
3. **点击搜索**

### 预期输出

每个任务记录：
- 初始状态（initial_state）
- 初始置信度（initial_confidence）
- 是否触发 state gate
- 执行动作
- 执行后状态（post_action_state）
- 执行后置信度（post_action_confidence）
- post-action state check 是否通过
- 最终是否成功

### 验证目标

至少证明以下一项：
- 有任务的 post-action state check 明确通过
- unknown 状态下系统会走更稳的保守策略

## 8. 剩余限制

1. **状态数量有限**：目前只支持 3 种状态（home_screen, settings_home, browser_home）

2. **OCR 依赖**：仍然依赖 OCR 文本识别，OCR 失败会导致状态检测失败

3. **无图标识别**：没有使用图标模型来辅助状态判断

4. **无页面模板库**：没有基于模板的页面匹配

5. **修正动作未完全实现**：post-action check 失败后只记录日志，未实现自动修正

## 9. 建议后续阶段

### 方案 A：完整状态机
- 扩展状态数量（10-20 个常见状态）
- 实现完整的状态转换图
- 支持更多目标状态验证

### 方案 B：图标模型
- 引入图标识别模型
- 不依赖 OCR 文本，通过图标判断状态
- 提高状态检测鲁棒性

### 方案 C：页面模板库
- 建立常见页面模板库
- 使用模板匹配进行状态识别
- 提高识别准确率

## 10. 文件变更清单

| 文件 | 变更 |
|------|------|
| `state/state_detector.py` | 已实现打分制（Phase 11-lite） |
| `state/simple_state_planner.py` | 已实现 state gate（Phase 11-lite） |
| `autoglm_bridge/memory.py` | 新增 post-action 字段 |
| `autoglm_bridge/agent_loop.py` | 新增 post-action state check |
| `.env.example` | 已包含配置项 |
| `tests/test_state_detector_scoring.py` | 已存在 |
| `tests/test_state_gate.py` | 已存在 |
| `tests/test_post_action_state_check.py` | 已存在 |
| `docs/phase11_5_report.md` | 本文档 |

---

**Phase 11.5 状态**：✅ 完成核心功能实现