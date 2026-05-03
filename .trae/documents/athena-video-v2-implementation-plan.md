# Athena 自我介绍视频 V2 — 实施计划

## 现状回顾

基于上一轮会话的审计，五个维度的问题已诊断完毕，旧修复计划已存在于 `athena-video-v2-fix-plan.md`。本计划是**可执行版本**，聚焦于具体代码改动和验证步骤。

### 已确认的 Bug 位置

| Bug | 位置 | 现状 |
|-----|------|------|
| TTS `voice_id` 参数名错配 | `asset_based.py:585` 传 `voice_id=`，但 `TTSService.__call__()` 只接受 `voice=` | **未修复** |
| `-shortest` 截断 | 已在 `video.py` 的 `merge_audio_video()` 中通过 `auto_adjust_duration` 修复 | ✅ 已修复 |
| `stream_loop` 暴力循环 | `merge_audio_video()` 的 `pad_strategy` 只有 `"freeze"` 和 `"black"`，缺少 `"loop"` | **未修复** |
| 转场缺失 | `video.py` 的 `concat_videos()` 只有硬切，无 xfade | **未修复** |
| 分辨率暴力拉伸 | `overlay_image_on_video()` 有 `contain` 模式但无 letterbox+模糊背景 | **未修复** |
| 云端 I2V | 无 `CloudI2VService`，无 Kling/Seedance 适配器 | **未实现** |

---

## 实施步骤（按优先级排序）

### Phase 1：Bug 修复 + 视频合成增强（P1，无外部依赖）

#### 1.1 修复 TTS `voice_id` 参数名错配

**改动文件**：
- `pixelle_video/pipelines/asset_based.py` — 将 `voice_id=config.voice_id` 改为 `voice=config.voice_id`
- `pixelle_video/services/tts_service.py` — 在 `__call__()` 签名中添加 `voice_id` 兼容参数
- `pixelle_video/services/frame_processor.py` — 同上，`_step_generate_audio()` 已正确传 `voice=`，无需改动

**具体改动**：

1. `tts_service.py` — `__call__()` 添加 `voice_id` 兼容参数：
```python
async def __call__(
    self,
    text: str,
    ...
    voice: Optional[str] = None,
    voice_id: Optional[str] = None,  # 兼容旧参数
    speed: Optional[float] = None,
    ...
) -> str:
    if voice_id and not voice:
        voice = voice_id
        logger.warning("'voice_id' is deprecated, use 'voice' instead")
    # 后续逻辑使用 voice
```

2. `asset_based.py:585` — 改为传 `voice=`：
```python
await self.core.tts(
    text=narration_text,
    output_path=str(audio_path),
    voice=config.voice_id,  # 修复：voice_id → voice
    speed=config.tts_speed
)
```

**验证**：调用 `core.tts(text="测试", voice_id="zh-CN-XiaoxiaoNeural")` 应输出女声。

#### 1.2 VideoService 添加转场效果

**改动文件**：`pixelle_video/services/video.py`

**新增方法**：`concat_videos_with_transitions()`

```python
def concat_videos_with_transitions(
    self,
    videos: List[str],
    output: str,
    transition: Literal["fade", "dissolve", "wipeleft", "cut"] = "dissolve",
    duration: float = 0.5,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.2,
    bgm_mode: Literal["once", "loop"] = "loop"
) -> str:
```

**实现思路**：
- 使用 ffmpeg `xfade` 滤镜链
- 对于 N 个视频，需要 N-1 个 xfade 滤镜
- 每个转场的 offset = 前一个视频时长 - 累计转场时长
- `cut` 模式回退到现有 `concat_videos()` 的 demuxer 方法
- 音频使用 `acrossfade` 滤镜同步过渡

**ffmpeg 命令模板**（3 段视频为例）：
```
ffmpeg -i v1.mp4 -i v2.mp4 -i v3.mp4 \
  -filter_complex \
  "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=4.5[x1]; \
   [x1][2:v]xfade=transition=fade:duration=0.5:offset=9.0[v]; \
   [0:a][1:a]acrossfade=d=0.5[a1]; \
   [a1][2:a]acrossfade=d=0.5[a]" \
  -map "[v]" -map "[a]" output.mp4
```

**关键细节**：
- 需要先 probe 每段视频获取时长来计算 offset
- 处理无音频轨道的视频（生成静音轨道）
- 转场时长不能超过最短视频时长的一半

**验证**：用 3 段 2 秒测试视频 + fade 转场，确认输出平滑过渡。

#### 1.3 VideoService 添加 loop pad_strategy

**改动文件**：`pixelle_video/services/video.py`

**改动方法**：`merge_audio_video()` 的 `pad_strategy` 新增 `"loop"` 选项

**实现思路**：
- 当 `pad_strategy == "loop"` 时，使用 `-stream_loop -1` 循环输入视频
- 截取到音频时长
- 在循环接缝处添加 0.3 秒交叉淡入淡出避免跳帧

```python
if pad_strategy == "loop":
    looped = self._loop_video(video, audio_duration, crossfade=0.3)
    video = looped
    video_duration = audio_duration
```

**新增私有方法**：`_loop_video(video, target_duration, crossfade=0.3)`

```python
def _loop_video(self, video: str, target_duration: float, crossfade: float = 0.3) -> str:
    """循环视频到目标时长，接缝处交叉淡入淡出"""
    output = self._get_unique_temp_path("looped", os.path.basename(video))
    
    # 使用 ffmpeg -stream_loop + -t 截取
    cmd = [
        'ffmpeg',
        '-stream_loop', '-1',
        '-i', video,
        '-t', str(target_duration),
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
        '-an',  # 先去掉音频，后续由 merge_audio_video 添加
        '-y', output
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output
```

**验证**：2 秒视频 + 10 秒音频 → 输出 10 秒循环视频，无黑帧。

#### 1.4 分辨率适配：letterbox + 模糊背景

**改动文件**：`pixelle_video/services/video.py`

**新增方法**：`adapt_resolution()`

```python
def adapt_resolution(
    self,
    video: str,
    output: str,
    target_width: int = 1080,
    target_height: int = 1920,
    mode: Literal["letterbox_blur", "letterbox_solid", "cover", "stretch"] = "letterbox_blur",
    bg_color: str = "#000000",
    blur_sigma: float = 20.0
) -> str:
```

**letterbox_blur 模式实现**（推荐）：
```
ffmpeg -i input.mp4 \
  -filter_complex \
  "[0:v]scale=1080:608,boxblur=20[bg]; \
   [0:v]scale=1080:608[fg]; \
   [bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2" \
  -s 1080x1920 output.mp4
```

更精确的实现：
1. 将原视频缩放到目标宽度（保持宽高比），计算缩放后高度
2. 创建模糊背景层：原视频放大到目标尺寸 + 高斯模糊
3. 将缩放后的前景居中叠加到模糊背景上

**验证**：832×480 横屏 → 1080×1920 竖屏，无裁剪无变形，上下有模糊填充。

---

### Phase 2：云端 I2V 集成（P0，核心质量提升）

#### 2.1 创建 CloudI2VService 基类

**新文件**：`pixelle_video/services/cloud_i2v.py`

```python
from dataclasses import dataclass
from typing import Optional, Literal
from abc import ABC, abstractmethod

@dataclass
class CloudI2VResult:
    video_url: str
    duration: float
    width: int
    height: int
    fps: float
    cost: float  # 花费金额（元）

class CloudI2VProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        image_path: str,
        prompt: str,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        ...
    ) -> CloudI2VResult: ...

    @abstractmethod
    async def submit(self, ...) -> str: ...

    @abstractmethod
    async def poll(self, task_id: str) -> CloudI2VResult: ...

class CloudI2VService:
    def __init__(self, config: dict):
        self.provider = self._create_provider(config)

    async def generate(self, **kwargs) -> CloudI2VResult:
        return await self.provider.generate(**kwargs)

    async def submit(self, **kwargs) -> str:
        return await self.provider.submit(**kwargs)

    async def poll(self, task_id: str) -> CloudI2VResult:
        return await self.provider.poll(task_id)

    async def generate_parallel(self, tasks: list[dict]) -> list[CloudI2VResult]:
        """并行提交多个 I2V 任务"""
        import asyncio
        task_ids = await asyncio.gather(*[self.submit(**t) for t in tasks])
        results = await asyncio.gather(*[self.poll(tid) for tid in task_ids])
        return results
```

#### 2.2 Kling API 适配器

**新文件**：`pixelle_video/services/cloud_i2v_kling.py`

**API 信息**：
- 代理：302.ai（`https://api.302.ai/klingai/m2v_15_img2video`）
- 认证：Bearer token（302.ai API key）
- 流程：POST 提交 → 轮询 GET 状态 → 下载视频 URL
- 价格：~0.3 PTC/次（5 秒视频）
- 并发：支持多任务

**关键实现**：
```python
class KlingI2VProvider(CloudI2VProvider):
    BASE_URL = "https://api.302.ai/klingai"

    async def submit(self, image_path, prompt, duration=5, ...):
        # 1. 读取图片并 base64 编码
        # 2. POST /m2v_15_img2video
        # 3. 返回 task_id

    async def poll(self, task_id):
        # 1. GET /task/{task_id}
        # 2. 检查状态：processing / completed / failed
        # 3. completed 时返回视频 URL

    async def generate(self, **kwargs):
        task_id = await self.submit(**kwargs)
        while True:
            result = await self.poll(task_id)
            if result: return result
            await asyncio.sleep(3)
```

#### 2.3 配置扩展

**改动文件**：`pixelle_video/config/schema.py`

在 `VideoSubConfig` 中添加：
```python
cloud_i2v_provider: Optional[str] = Field(
    default=None,
    description="Cloud I2V provider: kling/seedance/local"
)
cloud_i2v_api_key: Optional[str] = Field(
    default=None,
    description="Cloud I2V API key"
)
cloud_i2v_base_url: Optional[str] = Field(
    default=None,
    description="Cloud I2V API base URL (optional override)"
)
```

**改动文件**：`pixelle_video/service.py`

在 `PixelleVideoCore.initialize()` 中初始化 `CloudI2VService`：
```python
from pixelle_video.services.cloud_i2v import CloudI2VService
self.cloud_i2v = CloudI2VService(self.config) if self.config.get("comfyui", {}).get("video", {}).get("cloud_i2v_provider") else None
```

#### 2.4 FrameProcessor 集成 CloudI2V

**改动文件**：`pixelle_video/services/frame_processor.py`

在 `_step_generate_media()` 中，当 `frame.image_path` 存在且 `core.cloud_i2v` 可用时，优先使用云端 I2V：

```python
if frame.image_path and self.core.cloud_i2v:
    result = await self.core.cloud_i2v.generate(
        image_path=frame.image_path,
        prompt=prompt_text,
        duration=frame.duration or 5.0
    )
    # 下载视频到本地
    local_path = await self._download_media(result.video_url, ...)
    frame.video_path = local_path
    frame.media_type = "video"
```

---

### Phase 3：分镜重构 + 生成脚本（P0）

#### 3.1 设计 20 分镜脚本

**新文件**：`scripts/athena_storyboard.json`

基于旧计划的 20 分镜设计，但调整为实际可执行版本：
- 5 张 Gemini 图片作为关键帧（分镜 1, 6, 11, 16, 20）
- 其余分镜从关键帧衍生（I2V）
- 每个分镜 2-3 秒，总时长 ~55 秒
- 转场：场景内 dissolve(0.3s)，大场景切换 fade(0.5s)

#### 3.2 创建 Athena V2 生成脚本

**新文件**：`scripts/gen_athena_v2.py`

```python
async def main():
    async with PixelleVideoCore() as core:
        # 1. 加载分镜脚本
        storyboard = load_storyboard("scripts/athena_storyboard.json")

        # 2. 并行生成所有 I2V 视频
        i2v_tasks = [...]
        videos = await core.cloud_i2v.generate_parallel(i2v_tasks)

        # 3. 并行生成所有 TTS 音频
        audio_tasks = [...]
        audios = await asyncio.gather(*[core.tts(**t) for t in audio_tasks])

        # 4. 合成每个分镜（视频 + 音频）
        segments = []
        for video, audio in zip(videos, audios):
            segment = core.video.merge_audio_video(
                video, audio, output, pad_strategy="loop"
            )
            segments.append(segment)

        # 5. 分辨率适配（横屏 → 竖屏 letterbox）
        adapted = []
        for seg in segments:
            adapted_seg = core.video.adapt_resolution(
                seg, output, mode="letterbox_blur"
            )
            adapted.append(adapted_seg)

        # 6. 带转场拼接
        core.video.concat_videos_with_transitions(
            adapted, final_output, transition="dissolve", duration=0.3
        )
```

---

### Phase 4：工程规范修复（P2）

#### 4.1 中间产物校验

在 `gen_athena_v2.py` 中添加校验函数：
```python
def validate_segment(video_path, expected_duration, tolerance=0.2):
    actual = get_duration(video_path)
    assert actual >= expected_duration * (1 - tolerance), \
        f"Segment too short: {actual:.2f}s < {expected_duration:.2f}s"
```

#### 4.2 容错与重试

在 `CloudI2VProvider` 中添加重试逻辑：
```python
async def generate_with_retry(self, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return await self.generate(**kwargs)
        except Exception as e:
            wait = 5 * (3 ** attempt)  # 5s, 15s, 45s
            logger.warning(f"Retry {attempt+1}/{max_retries} after {wait}s: {e}")
            await asyncio.sleep(wait)
    raise RuntimeError(f"Failed after {max_retries} retries")
```

#### 4.3 配置化

- 所有路径改为从 config 或环境变量读取
- 分镜脚本独立为 JSON 文件
- I2V 提示词模板化

#### 4.4 日志改进

- 移除 `capture_stderr=True` 中的静默，关键步骤输出 stderr
- 每个步骤输出耗时统计

---

## 执行顺序

| 步骤 | Phase | 内容 | 依赖 | 预计改动量 |
|------|-------|------|------|-----------|
| 1 | 1.1 | 修复 TTS voice_id 错配 | 无 | ~15 行 |
| 2 | 1.2 | 添加转场效果 | 无 | ~80 行 |
| 3 | 1.3 | 添加 loop pad_strategy | 无 | ~40 行 |
| 4 | 1.4 | 添加分辨率适配 | 无 | ~60 行 |
| 5 | 2.1 | 创建 CloudI2VService 基类 | 无 | ~80 行 |
| 6 | 2.2 | Kling API 适配器 | 2.1 | ~120 行 |
| 7 | 2.3 | 配置扩展 | 2.1 | ~20 行 |
| 8 | 2.4 | FrameProcessor 集成 | 2.1+2.2 | ~30 行 |
| 9 | 3.1 | 设计分镜脚本 | 无 | JSON 文件 |
| 10 | 3.2 | 创建生成脚本 | 1+2 全部 | ~150 行 |
| 11 | 4 | 工程规范修复 | 1+2 | 分散在各文件 |

## 验证计划

每个步骤完成后立即验证：

1. **Phase 1 验证**：用现有 5 张 Athena 图片 + 本地 TTS 生成视频，确认：
   - 女声配音正常
   - 场景间有 dissolve 转场
   - 短视频循环填充正常
   - 横屏素材 letterbox 适配正常

2. **Phase 2 验证**：用 1 张图片调用 Kling API，确认：
   - 返回 5 秒高质量动画视频
   - 并行提交 2 个任务均成功

3. **Phase 3 验证**：执行完整生成脚本，确认：
   - 20 个分镜全部生成
   - 总时长 50-60 秒
   - 无循环重复
   - 转场平滑

## 风险与降级

| 风险 | 降级方案 |
|------|---------|
| Kling API 不可用 | 改用 Seedance 或本地 I2V |
| 302.ai 代理不稳定 | 直连 Kling 官方 API |
| 云端 I2V 质量不达预期 | 增加提示词优化 + 多次生成选优 |
| 横屏转竖屏 letterbox 效果差 | 改用 cover 模式 + 手动裁剪构图 |
