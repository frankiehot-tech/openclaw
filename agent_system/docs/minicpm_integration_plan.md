# MiniCPM 集成计划 - Phase 13

## 概述

本文档描述 MiniCPM 作为"视觉增强工具层"的集成方案。

> **设备约束**：本阶段及后续所有视觉增强相关开发，默认基于 **Samsung Galaxy Z Flip3** (1080x2640) 进行调优和验证。

## 为什么 MiniCPM 只是视觉增强层

### 1. 定位明确
- **不是主脑**: MiniCPM 不控制 ADB，不直接执行动作
- **不是替代 OCR**: 先 OCR-first，MiniCPM-second
- **只是工具层**: 补强 OCR 不足和复杂 UI 理解

### 2. 与现有组件的关系

```
┌─────────────────────────────────────────────────────────────┐
│                        Athena / AutoGLM                      │
│                      (主脑 - 决策与控制)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    agent_loop / action_executor              │
│                    (执行层 - 动作执行)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Vision Router                           │
│                   (路由层 - 决策用谁)                          │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │   OCR Engine    │    │   MiniCPM       │                 │
│  │  (文字识别强)    │    │  (图像理解强)    │                 │
│  └────────┬────────┘    └────────┬────────┘                 │
│           │                       │                           │
│           └───────────┬───────────┘                           │
│                       ▼                                       │
│              Vision Analysis Result                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    State Machine / Detector                  │
│                      (状态检测)                               │
└─────────────────────────────────────────────────────────────┘
```

### 3. MiniCPM 的职责

| 职责 | 说明 |
|------|------|
| 复杂 UI 识别 | 搜索框、列表项、弹窗等 OCR 难以识别的元素 |
| 页面类型推断 | 根据视觉特征判断当前页面类型 |
| 目标定位 | 提供高置信度的点击坐标 |
| 上下文理解 | 结合任务理解屏幕内容 |

### 4. MiniCPM 不做的事情

| 不做 | 原因 |
|------|------|
| 直接控制 ADB | 保持与现有架构的一致性 |
| 替换 OCR | OCR 对文字识别更准确更快 |
| 决策动作 | 由 agent_loop 统一决策 |
| 全量任务处理 | 只处理指定任务，避免风险 |

## 当前阶段：只接复杂 UI 场景

### 启用 MiniCPM 的任务（Phase 13）

1. **点击搜索** - 搜索框是复杂 UI，OCR 难以正确定位
2. **打开 Wi-Fi 页面** - 需要理解设置列表结构
3. **打开蓝牙页面** - 需要理解设置列表结构

### 不启用 MiniCPM 的任务

- 其他任务默认走原 OCR / model 流程
- 避免对现有稳定流程造成影响

## 决策规则

### Vision Router 决策流程

```
开始
  │
  ▼
是否启用 MiniCPM? ──No──► 使用 OCR/原有流程
  │
  Yes
  ▼
任务是否在白名单? ──No──► 使用 OCR/原有流程
  │
  Yes
  ▼
MiniCPM 是否可用? ──No──► 使用 OCR/原有流程
  │
  Yes
  ▼
OCR 高置信度? ──Yes──► 使用 OCR 结果
  │
  No
  ▼
调用 MiniCPM
  │
  ▼
MiniCPM 高置信? ──Yes──► 使用 MiniCPM 结果
  │
  No
  ▼
比较 OCR vs MiniCPM 置信度
  │
  ▼
选择更高置信度 / 回退到 model inference
```

### 置信度阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `OCR_HIGH_CONFIDENCE_THRESHOLD` | 0.85 | OCR 高于此值不调用 MiniCPM |
| `MINICPM_CONFIDENCE_THRESHOLD` | 0.70 | MiniCPM 高于此值使用其结果 |

## 配置项

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VISION_USE_MINICPM` | false | 是否启用 MiniCPM |
| `MINICPM_MODE` | mock | 运行模式: mock/remote/local_api |
| `MINICPM_BASE_URL` | - | API 基础 URL |
| `MINICPM_MODEL` | MiniCPM-V | 模型名称 |
| `MINICPM_TIMEOUT` | 60 | 请求超时（秒） |
| `MINICPM_CONFIDENCE_THRESHOLD` | 0.70 | MiniCPM 置信度阈值 |
| `OCR_HIGH_CONFIDENCE_THRESHOLD` | 0.85 | OCR 高置信度阈值 |

## 数据流

### 输入

```python
{
    "image_path": "/path/to/screenshot.png",
    "task": "点击搜索",
    "ocr_result": {...},  # 可选
    "state_result": {...}  # 可选
}
```

### 输出

```python
{
    "use_minicpm": True,
    "decision_reason": "默认使用 MiniCPM 增强",
    "source": "minicpm_vision",
    "grounding_target": {
        "text": "搜索",
        "bbox": [450, 100, 630, 180],
        "center": [540, 140],
        "confidence": 0.86,
        "element_type": "search_box",
        "source": "minicpm_vision"
    },
    "suggested_action": {
        "action": "tap",
        "params": {"x": 540, "y": 140},
        "reason": "检测到顶部搜索框",
        "confidence": 0.86,
        "source": "minicpm_vision"
    },
    "minicpm_result": {...},
    "minicpm_page_type": "browser_home",
    "minicpm_target_type": "search_box",
    "minicpm_confidence": 0.86
}
```

## 后续阶段计划

### Phase 14（可选）

- 扩大 MiniCPM 启用任务范围
- 接入真实 MiniCPM 模型
- 优化 prompt 和响应解析

### Phase 15（可选）

- MiniCPM 作为 fallback 层
- 处理更多复杂 UI 场景
- 性能优化

## 风险控制

1. **默认不启用**: `VISION_USE_MINICPM=false`
2. **任务白名单**: 只处理指定任务
3. **Mock 模式优先**: 开发阶段使用 mock
4. **Graceful Fallback**: MiniCPM 不可用时回退到原有流程
5. **置信度保护**: 低置信度结果不被直接使用