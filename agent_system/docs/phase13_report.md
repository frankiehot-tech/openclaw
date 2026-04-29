# Phase 13 阶段报告：MiniCPM 视觉增强层集成

## 阶段概述

完成 MiniCPM 作为"视觉增强工具层"的最小接入骨架，实现 OCR-first, MiniCPM-second 的路由决策机制。

> **设备约束**：本阶段及后续所有视觉增强相关开发，默认基于 **Samsung Galaxy Z Flip3** (1080x2640) 进行调优和验证。

## 新建/修改文件

### 新建文件

| 文件 | 说明 |
|------|------|
| `vision/minicpm_client.py` | MiniCPM 客户端，支持 mock/remote/local_api 三种模式 |
| `vision/vision_router.py` | 视觉路由决策器，实现 MiniCPM 启用决策逻辑 |
| `docs/minicpm_integration_plan.md` | MiniCPM 集成计划文档 |
| `tests/test_minicpm_router.py` | 路由决策测试（16 个测试用例） |
| `tests/test_minicpm_fallback.py` | 回退机制测试（10 个测试用例） |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `.env.example` | 新增 MiniCPM 相关配置项 |

## MiniCPM 在系统中的职责

### 定位
- **不是主脑**: 不控制 ADB，不直接执行动作
- **不是替代 OCR**: 先 OCR-first，MiniCPM-second
- **只是工具层**: 补强 OCR 不足和复杂 UI 理解

### 职责范围

| 职责 | 说明 |
|------|------|
| 复杂 UI 识别 | 搜索框、列表项、弹窗等 OCR 难以识别的元素 |
| 页面类型推断 | 根据视觉特征判断当前页面类型 |
| 目标定位 | 提供高置信度的点击坐标 |
| 上下文理解 | 结合任务理解屏幕内容 |

## vision_router 决策规则

### 决策流程

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

## 新增配置项

```bash
# MiniCPM Vision 配置（阶段 13 新增）

# 是否启用 MiniCPM 视觉增强（true/false）
VISION_USE_MINICPM=false

# MiniCPM 运行模式: mock/remote/local_api
MINICPM_MODE=mock

# MiniCPM API 基础 URL
MINICPM_BASE_URL=

# MiniCPM 模型名称
MINICPM_MODEL=MiniCPM-V

# MiniCPM 请求超时（秒）
MINICPM_TIMEOUT=60

# MiniCPM 置信度阈值
MINICPM_CONFIDENCE_THRESHOLD=0.70

# OCR 高置信度阈值
OCR_HIGH_CONFIDENCE_THRESHOLD=0.85
```

## 当前启用 MiniCPM 的任务

仅对以下任务启用 MiniCPM 增强（Phase 13）：

| 任务 | 说明 |
|------|------|
| 点击搜索 | 搜索框是复杂 UI，OCR 难以正确定位 |
| 打开 Wi-Fi 页面 | 需要理解设置列表结构 |
| 打开蓝牙页面 | 需要理解设置列表结构 |

其他任务默认仍走原 OCR / model 流程。

## 测试结果

### Router 测试（test_minicpm_router.py）

```
✓ 16 个测试全部通过
✓ OCR 高置信命中时不调用 MiniCPM
✓ OCR 低置信 + 复杂 UI 时调用 MiniCPM
✓ OCR miss 时调用 MiniCPM
✓ 任务不在白名单不调用 MiniCPM
✓ MiniCPM 未启用时不调用
✓ MiniCPM 不可用时不调用
✓ 点击搜索任务使用 MiniCPM
✓ 打开 Wi-Fi 页面使用 MiniCPM
✓ 打开蓝牙页面使用 MiniCPM
✓ MiniCPM 结果可转为 action
✓ MiniCPM 结果可转为 grounding
✓ 上下文字段正确添加
✓ 决策可序列化
```

### Fallback 测试（test_minicpm_fallback.py）

```
✓ 10/10 测试全部通过
✓ MiniCPM 不可用时回退到 OCR
✓ MiniCPM 禁用时回退到 model inference
✓ MiniCPM 低置信时回退到 OCR
✓ MiniCPM 未找到目标时回退
✓ 无 OCR 无 MiniCPM 时回退到 model inference
✓ MiniCPM 超时回退
✓ MiniCPM 错误回退
✓ 置信度阈值保护
✓ 回退决策结构完整
✓ 回退时保留 OCR 上下文
```

## 还没接真实 MiniCPM 的部分

### 当前状态
- ✅ Mock 模式已完成并测试通过
- ✅ 客户端接口已定义
- ✅ 路由决策已实现
- ❌ 真实 MiniCPM 模型推理未接入

### 待接入
1. **真实模型推理**: 需要配置 `MINICPM_BASE_URL` 和 `MINICPM_MODEL`
2. **Prompt 优化**: 针对复杂 UI 场景的 prompt 调优
3. **响应解析**: 真实 API 响应格式适配

## 下一步建议

### Phase 14（可选）
1. 扩大 MiniCPM 启用任务范围
2. 接入真实 MiniCPM 模型
3. 优化 prompt 和响应解析

### Phase 15（可选）
1. MiniCPM 作为 fallback 层
2. 处理更多复杂 UI 场景
3. 性能优化

### 风险控制
- ✅ 默认不启用: `VISION_USE_MINICPM=false`
- ✅ 任务白名单: 只处理指定任务
- ✅ Mock 模式优先: 开发阶段使用 mock
- ✅ Graceful Fallback: MiniCPM 不可用时回退到原有流程
- ✅ 置信度保护: 低置信度结果不被直接使用