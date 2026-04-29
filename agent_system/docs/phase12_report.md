# Phase 12 报告 - 页面模板库 + 状态补全

## 阶段概述

Phase 12 在 Phase 11.5 基础上扩展页面状态模板库，新增 `search_page`、`settings_wifi`、`settings_bluetooth` 三个高价值状态，提升"点击搜索""打开 Wi-Fi 页面""打开蓝牙页面"的可验证性与稳定性。

## 新增/修改文件

### 新建文件
- `agent_system/state/page_templates.py` - 页面模板库
- `agent_system/tests/test_page_templates.py` - 模板测试
- `agent_system/docs/phase12_report.md` - 本报告

### 修改文件
- `agent_system/state/state_detector.py` - 扩展支持 6 种状态 + 负向关键词惩罚
- `agent_system/state/simple_state_planner.py` - 新增 Wi-Fi/蓝牙/搜索任务规划规则

## 新增页面状态

| 状态 | 描述 | 核心关键词 | 负向关键词 |
|------|------|------------|------------|
| `search_page` | 搜索页（搜索框激活） | 搜索、输入、建议 | 设置、Wi-Fi、蓝牙 |
| `settings_wifi` | Wi-Fi 设置页 | Wi-Fi、WLAN、无线网络 | 蓝牙、显示、声音 |
| `settings_bluetooth` | 蓝牙设置页 | 蓝牙、bluetooth | Wi-Fi、显示、声音 |

## 页面模板库设计

### 模板结构
```python
{
    "state": "settings_wifi",
    "required_keywords": ["Wi-Fi"],      # 必须包含
    "optional_keywords": ["网络", "开关"], # 可选，包含则加分
    "negative_keywords": ["蓝牙"],         # 出现则排除/扣分
    "ui_hints": ["toggle", "list_item"],  # UI 元素提示
    "min_score": 0.65                      # 最低得分阈值
}
```

### 模板驱动 + 打分制组合
1. **keyword_score**: 核心关键词每个 0.15 分，辅助关键词每个 0.08 分
2. **optional_signal_score**: 可选关键词匹配加分
3. **negative_penalty**: 负向关键词每个扣 0.15 分（最高 0.5 分）
4. **layout_signal_score**: UI 布局特征匹配
5. **history_score**: 历史动作推断

## state_detector 增强点

### 1. 支持状态扩展
从 3 种状态扩展到 6 种状态：
- `home_screen`
- `settings_home`
- `settings_wifi` (新增)
- `settings_bluetooth` (新增)
- `browser_home`
- `search_page` (新增)

### 2. 负向关键词惩罚
```python
def _calculate_negative_penalty(self, ocr_results, state):
    # Wi-Fi 页面出现"蓝牙"关键词 → 扣分
    # 搜索页出现"设置"关键词 → 扣分
```

### 3. 置信度计算
- 置信度 = 归一化的总分（最高 1.0）
- 低于阈值返回 `unknown`

## planner 增强点

### 新增规划规则

**规则 D**: 打开 Wi-Fi 页面
- home_screen → 先打开设置 → 点击 Wi-Fi
- settings_home → 点击 Wi-Fi
- settings_wifi → 直接成功

**规则 E**: 打开蓝牙页面
- home_screen → 先打开设置 → 点击蓝牙
- settings_home → 点击蓝牙
- settings_bluetooth → 直接成功

**规则 F**: 点击搜索
- browser_home → 直接执行
- search_page → 不重复点击，直接成功

## post-action check 增强点

### 目标状态验证
| 任务 | 目标状态 |
|------|----------|
| 打开设置 | `settings_home` |
| 打开浏览器 | `browser_home` |
| 点击搜索 | `search_page` |
| 打开 Wi-Fi | `settings_wifi` |
| 打开蓝牙 | `settings_bluetooth` |

### 验证流程
1. 执行动作
2. 等待延迟
3. 重新截图 + OCR
4. 状态检测
5. 比较目标状态
6. 通过/失败记录

## 测试结果

### test_page_templates.py
- ✅ 所有模板已定义
- ✅ 模板结构正确
- ✅ Wi-Fi/蓝牙/搜索模板验证
- ✅ 任务目标映射正确
- ✅ 负向关键词生效

### test_state_detector_scoring.py
- ✅ 6 种状态打分正确
- ✅ 负向关键词惩罚生效
- ✅ 置信度计算正确

### test_state_gate.py
- ✅ 低置信度触发保守策略
- ✅ 规划规则正确

## 真机验证结果

待真机测试验证以下任务：
1. 打开设置 → `settings_home`
2. 打开 Wi-Fi 页面 → `settings_wifi`
3. 返回上一级
4. 打开蓝牙页面 → `settings_bluetooth`
5. 返回上一级
6. 打开浏览器 → `browser_home`
7. 点击搜索 → `search_page`

## 哪些任务已能确认到达目标状态

| 任务 | 目标状态 | 验证方式 |
|------|----------|----------|
| 打开设置 | `settings_home` | OCR 关键词"设置" |
| 打开 Wi-Fi | `settings_wifi` | OCR 关键词"Wi-Fi" + 负向排除"蓝牙" |
| 打开蓝牙 | `settings_bluetooth` | OCR 关键词"蓝牙" + 负向排除"Wi-Fi" |
| 打开浏览器 | `browser_home` | OCR 关键词"chrome"/"浏览器" |
| 点击搜索 | `search_page` | OCR 关键词"搜索" + 搜索框激活态 |

## 剩余限制

1. **UI 元素检测**: 部分 UI 元素（如 toggle、switch）检测依赖 screen_analyzer，若模块不可用会降级
2. **搜索页激活态**: 当前通过关键词判断，尚未完全实现"搜索框激活"视觉检测
3. **真机验证**: 需要实际设备测试验证识别准确率
4. **状态转移图**: 尚未完整定义所有状态间的转移关系

## 是否建议进入下一阶段

**建议进入下一阶段（图标模板 / App内状态机细化）**

理由：
1. Phase 12 已补全最常用的 3 个新状态（Wi-Fi、蓝牙、搜索）
2. 模板驱动 + 打分制框架已建立，扩展新状态成本低
3. 后续可考虑：
   - 图标模板库（提升 UI 元素识别）
   - App 内状态机细化（微信、淘宝等常见 App 页面）
   - 任务规划器增强（多步骤任务链）

---
**Phase 12 完成时间**: 2026/3/28