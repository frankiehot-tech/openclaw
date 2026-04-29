# 阶段 8：Vision 增强（OCR + UI Grounding）

## 阶段目标

为 Agent 控制链路添加视觉理解能力，实现：
1. OCR 文本识别 - 从截图中提取 UI 文本
2. UI Grounding - 将任务目标映射到屏幕坐标
3. 混合决策 - OCR Grounding 优先，失败时回退到模型推理

## 新增文件

### 1. vision/__init__.py
Vision 模块初始化

### 2. vision/ocr_engine.py
OCR 引擎封装：
- `OCREngine` 基类
- `MockOCREngine` - Mock 实现（测试用）
- `EasyOCREngine` - EasyOCR 实现（生产用）
- `get_ocr_engine()` - 工厂函数

### 3. vision/ui_grounding.py
UI Grounding 模块：
- `UIGrounding` - 文本到坐标映射
- 模糊匹配算法
- 候选排序

### 4. vision/screen_analyzer.py
屏幕分析器：
- `ScreenAnalyzer` - 整合 OCR + Grounding
- `analyze_screen()` - 分析截图，返回目标位置
- `get_screen_analyzer()` - 工厂函数

## 核心代码说明

### Agent Loop 增强

在 `agent_loop.py` 中新增：

```python
def _extract_target_from_task(self, task: str) -> List[str]:
    """从任务中提取可能的目标文本"""
    # 常见目标关键词
    keywords = ["设置", "搜索", "浏览器", ...]
    ...

def _try_ocr_grounding(
    self,
    screenshot_path: str,
    task: str
) -> Optional[Dict]:
    """尝试使用 OCR grounding 生成动作"""
    # 1. 提取任务中的目标文本
    target_texts = self._extract_target_from_task(task)
    
    # 2. 使用 screen analyzer 分析截图
    analyzer = get_screen_analyzer(ocr_provider="mock")
    analysis = analyzer.analyze_screen(screenshot_path, expected_targets)
    
    # 3. 如果找到目标，返回动作
    if analysis.target_found:
        return {
            "action": "tap",
            "x": center[0],
            "y": center[1],
            "action_source": "ocr_grounding",
            ...
        }
    return None
```

### 决策流程

```
run_step():
    │
    ├─> 截图
    │
    ├─> 尝试 OCR Grounding（use_vision=True）
    │   │
    │   ├─> 提取任务目标文本
    │   ├─> OCR 识别屏幕文本
    │   ├─> 模糊匹配目标
    │   └─> 如果命中 → 返回 tap 动作
    │
    └─> 如果 OCR 未命中 → 模型推理
```

### Memory 增强

在 `memory.py` 的 `StepRecord` 中新增字段：

```python
@dataclass
class StepRecord:
    # ... 原有字段 ...
    
    # OCR/Grounding 字段
    action_source: Optional[str] = None  # ocr_grounding/model_inference/fallback
    ocr_blocks_count: int = 0  # OCR 文本块数量
    ocr_top_texts: List[str] = []  # 高置信文本列表
    grounding_target: Optional[str] = None  # grounding 目标文本
    grounding_candidates: List[str] = []  # grounding 候选列表
    screen_summary: str = ""  # 屏幕摘要
```

## 配置项

在 `.env` 中新增：

```bash
# Vision / OCR 配置
VISION_USE_OCR=true
VISION_OCR_PROVIDER=mock  # mock 或 primary
VISION_TEXT_MATCH_THRESHOLD=0.75
VISION_MAX_CANDIDATES=5
VISION_SCREEN_WIDTH=1080
VISION_SCREEN_HEIGHT=2640
```

## 当前能力

1. **OCR 文本识别** - 从截图中提取 UI 文本（Mock 实现）
2. **UI Grounding** - 将目标文本映射到屏幕坐标
3. **混合决策** - OCR 优先，失败时回退到模型推理
4. **历史记录增强** - 记录动作来源、OCR 结果等

## 风险

1. **Mock OCR 限制** - 当前使用 Mock，无法真正识别屏幕文本
2. **EasyOCR 依赖** - 生产环境需要安装 easyocr
3. **模糊匹配精度** - 文本匹配可能不准确
4. **坐标偏移** - 不同设备分辨率需要适配

## 下一步

1. 安装 EasyOCR：`pip install easyocr`
2. 在真机上测试 OCR 识别
3. 优化模糊匹配算法
4. 添加更多 UI 元素类型（图标、按钮区域）

## 是否继续

请确认是否继续到下一阶段。