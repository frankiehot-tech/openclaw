# 基准测试计划 (Benchmark Plan)

## 概述

本计划定义了针对 Agent 控制系统的基准测试方案，用于量化任务成功率、OCR 命中率、grounding 命中率等指标。

## 测试环境

- **设备**: Samsung Galaxy Z Flip3
- **分辨率**: 1080 x 2640
- **OCR Provider**: EasyOCR (primary) / Mock
- **测试模式**: real / mock

## 任务集定义

### 任务列表

| 任务名 | 类别 | 最大步数 | 成功信号 | 风险等级 | 优先级 |
|--------|------|----------|----------|----------|--------|
| 打开设置 | navigation | 5 | 设置 | low | high |
| 返回上一级 | navigation | 3 | 返回 | low | high |
| 回到主屏幕 | navigation | 3 | 主屏幕 | low | high |
| 打开浏览器 | app_launch | 5 | 浏览器 | low | medium |
| 点击搜索 | interaction | 3 | 搜索 | low | medium |
| 向上滑动 | gesture | 3 | 滑动 | low | medium |
| 打开WiFi页面 | navigation | 5 | Wi-Fi | low | medium |
| 打开蓝牙页面 | navigation | 5 | 蓝牙 | low | medium |

## 成功判定原则

### 判定逻辑

1. **最终页面 OCR 文本检查**: 执行任务后，对最终屏幕进行 OCR 识别
2. **成功信号匹配**: 检查 OCR 结果中是否包含 `expected_success_signal`
3. **历史 action_source 分析**: 检查执行过程中是否使用了有效的动作源

### 判定结果

- **success**: 成功信号出现，且执行了有效动作
- **partial**: 执行了动作但未检测到成功信号
- **failed**: 执行失败或超时

### 任务成功信号

| 任务 | 成功信号 | 备选信号 |
|------|----------|----------|
| 打开设置 | 设置、关于手机 | 设置页面 |
| 返回上一级 | 返回 | < |
| 回到主屏幕 | 主屏幕、主页 | 桌面 |
| 打开浏览器 | 浏览器、Chrome | 浏览器界面 |
| 点击搜索 | 搜索 | 搜索框 |
| 向上滑动 | 滑动成功 | 页面滚动 |
| 打开WiFi页面 | Wi-Fi、WLAN | 无线网络 |
| 打开蓝牙页面 | 蓝牙 | Bluetooth |

## 风险等级

所有任务均为 **low** 风险等级：
- 不涉及支付、登录、发送消息
- 不涉及内容删除
- 只读操作或系统导航

## 动作来源策略

### 优先 OCR 命中的任务
- 打开设置
- 返回上一级
- 打开 Wi-Fi 页面
- 打开蓝牙页面

### 允许模型回退的任务
- 打开浏览器
- 点击搜索
- 向上滑动
- 回到主屏幕

### 允许的 action_source
- `ocr_grounding`: OCR 识别 + 文本匹配
- `model_inference`: 模型推理
- `fallback`: 降级处理

## 测试轮次建议

### 小规模验证 (子任务 8)
- 任务数: 3
- 轮次: 2
- 总执行: 6 次

### 全量测试 (推荐)
- 任务数: 8
- 轮次: 3
- 总执行: 24 次

## 成本控制策略

### API 限流

1. **连续成功降频**: 连续 3 次 OCR grounding 成功后，下一次允许更多模型回退尝试
2. **错误阈值**: 连续 5 次 API 错误自动终止测试
3. **超时限制**: 单次任务执行不超过 60 秒

### 成本估算

| 模式 | 每次任务预估 API 调用 | 8 任务 x 3 轮 |
|------|----------------------|---------------|
| real (OCR 命中) | 1-2 次 | ~50 次 |
| real (模型回退) | 3-5 次 | ~150 次 |
| mock | 0 次 | 0 次 |

### 建议

- 先跑 mock 模式验证流程
- 再跑 real 模式小规模测试
- 全量测试建议分批执行

## 输出文件

- `logs/benchmark_results.json` - 每次执行详情
- `logs/benchmark_summary.json` - 统计摘要
- `logs/benchmark_failure_samples.json` - 失败样本
- `docs/benchmark_report.md` - Markdown 报告

## 运行命令

### 小规模验证
```bash
cd /Volumes/1TB-M2/openclaw/agent_system
python -m tests.run_benchmark --device zflip3 --rounds 2 --mode real --tasks "打开设置,返回上一级,回到主屏幕"
```

### 全量测试
```bash
cd /Volumes/1TB-M2/openclaw/agent_system
python -m tests.run_benchmark --device zflip3 --rounds 3 --mode real
```

### Mock 模式
```bash
cd /Volumes/1TB-M2/openclaw/agent_system
python -m tests.run_benchmark --device zflip3 --rounds 3 --mode mock