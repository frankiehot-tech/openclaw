# Vision 模块集成文档

## 概述

Vision 模块为 Agent 控制链路提供视觉理解能力，包括：
- OCR 文本识别
- UI Grounding（文本到坐标映射）
- 屏幕分析

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Loop                              │
│  (autoglm_bridge/agent_loop.py)                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Screen Analyzer                            │
│  (vision/screen_analyzer.py)                                │
│  - 整合 OCR + Grounding                                      │
│  - 返回分析结果和建议动作                                     │
└──────────┬──────────────────────┬──────────────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐    ┌──────────────────┐
│   OCR Engine    │    │  UI Grounding   │
│ (ocr_engine.py) │    │(ui_grounding.py)│
│                  │    │                  │
│ - Mock Provider │    │ - Exact match   │
│ - EasyOCR       │    │ - Contains      │
│ - 可插拔架构    │    │ - Fuzzy match   │
└──────────────────┘    └──────────────────┘
```

## 核心组件

### 1. OCR Engine (`vision/ocr_engine.py`)

**Provider 架构：**
- `OCRProvider` - 抽象基类
- `MockOCRProvider` - Mock 实现（测试用）
- `PrimaryOCRProvider` - EasyOCR 实现（生产用）

**统一接口：**
```python
def extract_text(image_path: str) -> List[OCRResult]:
    """
    从图片中提取文字
    
    Returns:
        List[OCRResult], 每个包含:
        - text: 文本内容
        - bbox: [x1, y1, x2, y2]
        - confidence: 置信度 0.0-1.0
    """
```

### 2. UI Grounding (`vision/ui_grounding.py`)

**功能：**
- 文本匹配（exact / contains / fuzzy）
- bbox 转 tap 点（带安全边距）
- 候选排序

**统一接口：**
```python
def find_text_target(
    ocr_blocks: List[OCRResult],
    target_text: str,
    match_threshold: float = 0.75
) -> Optional[TextTarget]:
    """
    查找目标文本
    
    Returns:
        TextTarget 或 None，包含:
        - matched: 是否匹配
        - text: 匹配的文本
        - bbox: 边界框
        - center: (x, y) 中心点
        - confidence: 置信度
        - match_type: "exact" | "contains" | "fuzzy"
    """
```

### 3. Screen Analyzer (`vision/screen_analyzer.py`)

**功能：**
- 整合 OCR 和 Grounding
- 生成屏幕摘要
- 建议动作

**统一接口：**
```python
def analyze_screen(
    image_path: str,
    expected_targets: Optional[List[str]] = None
) -> ScreenAnalysis:
    """
    分析屏幕
    
    Returns:
        ScreenAnalysis，包含:
        - ocr_blocks: OCR 结果列表
        - ocr_blocks_count: 文本块数量
        - ocr_top_texts: 高置信文本
        - grounding_target: 匹配的目标
        - grounding_candidates: 候选列表
        - target_found: 是否找到目标
        - suggested_actions: 建议动作
        - screen_summary: 屏幕摘要
    """
```

## Agent Loop 集成

在 `agent_loop.py` 中，Vision 增强的决策流程：

```
run_step():
    │
    ├─> 截图
    │
    ├─> 尝试 OCR Grounding
    │   │
    │   ├─> 提取任务目标文本
    │   ├─> screen_analyzer.analyze_screen()
    │   ├─> 如果 target_found → 生成 tap 动作
    │   └─> action_source = "ocr_grounding"
    │
    └─> 如果 OCR 未命中 → model_client.infer_action()
        └─> action_source = "model_inference"
```

## 配置

在 `.env` 中配置：

```bash
# Vision / OCR 配置
VISION_USE_OCR=true
VISION_OCR_PROVIDER=mock  # mock | primary
VISION_TEXT_MATCH_THRESHOLD=0.75
VISION_MAX_CANDIDATES=5
VISION_SCREEN_WIDTH=1080
VISION_SCREEN_HEIGHT=2640
```

## Provider 对比

| 特性 | Mock Provider | EasyOCR Provider |
|------|---------------|------------------|
| 用途 | 测试/开发 | 生产环境 |
| 依赖 | 无 | easyocr |
| 速度 | 瞬时 | 较慢（首次加载） |
| 准确性 | 固定返回 | 真实识别 |
| 设备要求 | 无 | GPU 推荐 |

## 降级策略

1. **EasyOCR 不可用**：自动回退到 Mock
2. **OCR 结果为空**：生成空摘要，交给模型推理
3. **Grounding 未命中**：回退到模型推理
4. **截图失败**：跳过 OCR，直接模型推理

## 安装 EasyOCR

```bash
# 仅在我批准后执行
python3 -m pip install easyocr
```

注意：EasyOCR 首次运行会下载模型（约 150MB），需要网络连接。

## 测试

运行测试：
```bash
cd /Volumes/1TB-M2/openclaw/agent_system
python -m pytest tests/test_ocr_grounding.py -v
```

## 日志

Vision 模块日志写入：
- `logs/vision.log` - Vision 模块日志
- `logs/autoglm.log` - Agent Loop 日志
- `logs/pipeline.log` - 完整链路日志