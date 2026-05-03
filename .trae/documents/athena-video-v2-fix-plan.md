# Athena 自我介绍视频 V2 — 五维度修复计划

## 问题根因总结

| 层面 | 根因 |
|------|------|
| 技术选型 | Mac M4 上硬跑 14B Q4 I2V，硬件-模型错配，19 小时产出近静止画面 |
| 工作流设计 | 2 秒微动视频暴力循环填充 60 秒，违背 I2V 工具设计意图 |
| 工程实现 | TTS 参数错配、-shortest 截断、stream_loop 循环、分辨率暴力拉伸 |
| 艺术指导 | 无分镜脚本、无镜头语言、无转场、音画不同步 |
| 工程规范 | 无版本控制、无中间校验、硬编码路径、无容错 |

---

## 修复策略：云端 I2V + 本地合成

**核心决策**：放弃本地 14B I2V（19 小时/近静止），改用 **Seedance 2.0 云端 API**（15 元/15 秒视频，1 元/秒），本地只做 TTS + 合成。

### 为什么选 Seedance 2.0 而非 Kling？

| 指标 | Seedance 2.0 | Kling 3.0 Pro | 本地 14B Q4 |
|------|-------------|---------------|-------------|
| 单场景 5s 视频 | ~5 元 | ~$0.5 (~3.5 元) | 0 元 + 4 小时电费 |
| 画质 | 720p 24fps | 1080p | 480p 16fps |
| 动画幅度 | 大幅动作 | 大幅动作 | 微动 |
| 原生音频 | ✅ 支持 | ✅ 支持 | ❌ |
| API 可用性 | 火山引擎（企业认证） | 多平台代理 | N/A |
| 并发 | 10 任务 | 1-2 任务 | 1 任务 |

**短期方案**：先用 Kling API（通过 302.ai 代理，0.3 PTC/次，无需企业认证），验证流程。
**中期方案**：接入 Seedance 2.0 火山引擎 API（需企业认证）。

---

## 实施步骤

### Phase 1：架构重构（解决工程规范 + 合成逻辑 Bug）

#### 1.1 扩展 MediaService 支持 I2V 参数
- **文件**：`pixelle_video/services/media.py`
- **改动**：在 `__call__` 方法签名中添加 `image: Optional[str] = None` 参数
- **逻辑**：当 `image` 不为 None 时，通过 `**params` 透传给 ComfyKit，确保 I2V 工作流的 `$image.image!` 变量正确绑定
- **验证**：单元测试确认 `image` 参数能正确传入 workflow_params

#### 1.2 扩展 FrameProcessor 支持 I2V
- **文件**：`pixelle_video/services/frame_processor.py`
- **改动**：在 `_step_generate_media` 中，当 `frame.image_path` 存在且 `media_type == "video"` 时，将 `image=frame.image_path` 传给 `self.core.media()`
- **逻辑**：让 AssetBasedPipeline 的图片素材能走 I2V 工作流动起来

#### 1.3 修复 TTS 参数名对齐
- **文件**：`pixelle_video/services/tts_service.py` + `pixelle_video/service.py`
- **改动**：统一参数名为 `voice`，在 `service.py` 的 `tts()` 方法中添加 `voice_id` → `voice` 的兼容映射
- **验证**：传入 `voice_id` 和 `voice` 都能正确设置语音

#### 1.4 VideoService 添加转场效果
- **文件**：`pixelle_video/services/video.py`
- **改动**：新增 `concat_videos_with_transitions()` 方法
- **支持的转场**：
  - `fade`（淡入淡出，默认 0.5 秒）
  - `dissolve`（交叉溶解，默认 0.5 秒）
  - `cut`（硬切，兼容现有行为）
- **实现**：使用 ffmpeg `xfade` 滤镜
- **验证**：3 段测试视频 + fade 转场，确认过渡平滑

#### 1.5 VideoService 修复 I2V 视频合成逻辑
- **文件**：`pixelle_video/services/video.py`
- **改动**：`merge_audio_video()` 的 `pad_strategy` 新增 `"loop"` 选项
- **逻辑**：当视频短于音频时，循环播放视频（而非冻结帧或黑屏），并添加交叉淡入淡出避免跳帧
- **验证**：2 秒视频 + 10 秒音频 → 输出 10 秒循环视频

#### 1.6 分辨率适配策略
- **文件**：`pixelle_video/services/frame_processor.py` + `video.py`
- **改动**：横屏素材适配竖屏时，使用 **letterbox + 动态粒子/渐变填充** 而非暴力裁剪
- **实现**：
  - 计算缩放比例使视频宽度 = 1080，高度按比例缩放
  - 上下空白区域填充动态渐变背景（从视频主色调提取）
  - 或使用模糊放大的原视频作为背景层
- **验证**：832×480 横屏 → 1080×1920 竖屏，无裁剪无变形

---

### Phase 2：云端 I2V 集成（解决视频质量 + 效率问题）

#### 2.1 创建 CloudI2VService
- **新文件**：`pixelle_video/services/cloud_i2v.py`
- **接口设计**：
  ```python
  class CloudI2VService:
      async def generate(self, image_path, prompt, duration=5, ...) -> CloudI2VResult:
          """提交 I2V 任务并等待结果"""
      async def submit(self, image_path, prompt, ...) -> str:
          """提交任务，返回 task_id"""
      async def poll(self, task_id) -> CloudI2VResult:
          """轮询任务状态"""
  ```
- **支持的后端**：
  - `kling`：通过 302.ai 代理 API（短期，无需企业认证）
  - `seedance`：火山引擎 API（中期，需企业认证）
  - `local`：本地 ComfyUI I2V（后备方案）

#### 2.2 Kling API 适配器
- **新文件**：`pixelle_video/services/cloud_i2v/kling.py`
- **API**：302.ai 代理 `https://api.302.ai/klingai/m2v_15_img2video`
- **流程**：提交图片 + prompt → 轮询状态 → 下载视频
- **价格**：0.3 PTC/次（约 0.3 元/5 秒视频）
- **并发**：支持同时提交多个任务

#### 2.3 配置扩展
- **文件**：`pixelle_video/config/schema.py`
- **新增字段**：
  ```python
  class VideoSubConfig(BaseModel):
      cloud_i2v_provider: Optional[str] = Field(default=None, description="Cloud I2V provider: kling/seedance/local")
      cloud_i2v_api_key: Optional[str] = Field(default=None, description="Cloud I2V API key")
      cloud_i2v_base_url: Optional[str] = Field(default=None, description="Cloud I2V API base URL")
  ```

#### 2.4 并行化 I2V 任务
- **改动**：在生成脚本中，5 个场景的 I2V 任务**并行提交**到云端
- **预期**：5 个 5 秒视频同时生成，总耗时从 19 小时降到 **2-5 分钟**

---

### Phase 3：分镜重构（解决叙事节奏问题）

#### 3.1 从 5 场景改为 20+ 分镜
- **原则**：每个分镜 2-3 秒，避免循环重复
- **分镜设计**：

| # | 分镜 | 时长 | 画面描述 | 运镜 |
|---|------|------|----------|------|
| 1 | 混沌虚空 | 3s | 深空星云缓慢旋转，光点汇聚 | 缓慢推入 |
| 2 | 光芒凝聚 | 2s | 金色光柱从虚空中射出 | 仰角固定 |
| 3 | Athena 诞生 | 3s | 猫头鹰剪影从光芒中浮现 | 正面特写 |
| 4 | 展翅 | 2s | 猫头鹰展开翅膀，金色粒子飞散 | 侧面跟拍 |
| 5 | 名字浮现 | 3s | "ATHENA" 文字在光幕上显现 | 俯角 |
| 6 | 女神降临 | 2s | 战争女神从数字粒子中凝聚 | 低角度仰拍 |
| 7 | 举起盾牌 | 3s | 盾牌上的逻辑图案发光 | 手部特写 |
| 8 | 投掷长矛 | 2s | 光矛划过天际 | 跟随运动 |
| 9 | 数字大脑 | 3s | 神经网络脉冲发光 | 环绕旋转 |
| 10 | 决策流 | 2s | 数据流在节点间高速流动 | 快速推入 |
| 11 | 工作流编排 | 3s | 多个模块自动连接组合 | 鸟瞰 |
| 12 | 精准执行 | 2s | 光标精准点击目标 | 第一人称 |
| 13 | 开源代码 | 3s | 代码树有机生长 | 缓慢拉远 |
| 14 | 协作网络 | 2s | 多人同时编辑，光标交织 | 分屏 |
| 15 | 透明信念 | 3s | 源代码逐行展开，逻辑清晰 | 横滚 |
| 16 | 共同成长 | 2s | 树苗长成大树 | 延时摄影 |
| 17 | 数字黎明 | 3s | 地平线金色光线扩散 | 缓慢升起 |
| 18 | 光桥连接 | 2s | 浮岛间光桥逐一亮起 | 横向摇镜 |
| 19 | 邀请同行 | 3s | Athena 伸出手，光粒子飞向观众 | 正面特写 |
| 20 | Athena 标志 | 2s | 猫头鹰标志 + "ATHENA" 文字 | 固定 |

#### 3.2 素材分配策略
- 5 张 Gemini 图片作为 **关键帧**（分镜 3, 6, 9, 13, 17）
- 其余分镜用 **云端 I2V 从关键帧衍生**，或用 **t2v 文生视频**
- 每个分镜独立生成 2-3 秒视频，**不循环**

#### 3.3 转场设计
- 场景内分镜：`dissolve`（0.3 秒交叉溶解）
- 大场景切换：`fade`（0.5 秒淡入淡出）
- 动作衔接：`cut`（硬切，配合运动方向）

---

### Phase 4：音画同步增强

#### 4.1 Lip Sync（口型同步）
- **节点**：`KlingLipSyncAudioToVideoNode`（已安装在 ComfyUI 中）
- **要求**：需要 Comfy Org API key
- **备选**：Wav2Lip（需安装 ComfyUI-Wav2Lip 插件）
- **应用场景**：Athena 正面特写分镜（#3, #6, #19）

#### 4.2 音频驱动的微动作
- **方案**：对非口型场景，使用音频振幅驱动画面微动
- **实现**：提取音频 RMS 能量 → 映射到缩放/亮度微调
- **效果**：旁白说话时画面轻微脉动，静默时画面静止

#### 4.3 女声配音优化
- **语音**：`zh-CN-XiaoxiaoNeural`（晓晓，温柔女声）
- **语速**：0.9（略慢，增强故事感）
- **情感**：添加 SSML 标记控制语调和停顿
- **分段**：按分镜拆分旁白，每段 2-3 秒

---

### Phase 5：工程规范修复

#### 5.1 中间产物校验
- 在每个分镜生成后检查：视频时长 ≥ 预期时长 × 0.8
- 在 TTS 生成后检查：音频时长 > 0
- 在合成后检查：最终视频时长 ≈ 所有分镜时长之和

#### 5.2 容错与重试
- 云端 API 调用失败：自动重试 3 次，间隔 5/15/45 秒
- ComfyUI 任务超时：30 分钟未完成则标记失败
- 失败分镜降级：t2v → 静态图 + Ken Burns

#### 5.3 配置化
- 所有路径改为相对路径或从 config.yaml 读取
- I2V 提示词模板化，支持从 YAML 配置
- 分镜脚本独立为 JSON/YAML 文件

#### 5.4 日志与调试
- 移除所有 `2>/dev/null`，改为 `stderr` 日志
- 关键步骤输出耗时统计
- 保留中间产物（不自动清理），便于调试

---

## 执行优先级

| 优先级 | Phase | 预期效果 | 依赖 |
|--------|-------|----------|------|
| P0 | Phase 2（云端 I2V） | 视频质量从"近静止"跃升到"真正动画"，耗时从 19h 降到 5min | 无 |
| P0 | Phase 3（分镜重构） | 消除循环重复，叙事节奏专业级 | Phase 2 |
| P1 | Phase 1.3-1.5（Bug 修复） | 消除 TTS/合成/转场 Bug | 无 |
| P1 | Phase 1.6（分辨率适配） | 消除暴力拉伸 | 无 |
| P2 | Phase 4（音画同步） | 口型/微动作增强沉浸感 | Phase 2 |
| P2 | Phase 1.1-1.2（架构扩展） | 让 Pipeline 原生支持 I2V | Phase 2 |
| P3 | Phase 5（工程规范） | 长期可维护性 | Phase 1+2 |

---

## 预期产出

| 指标 | V1（当前） | V2（目标） |
|------|-----------|-----------|
| 视频时长 | 61s | 55-65s |
| 分镜数 | 5 | 20 |
| 单分镜时长 | 2s 循环 5-7 次 | 2-3s 无循环 |
| 画质 | 480p→1080p 暴力拉伸 | 720p 原生 + letterbox |
| 帧率 | 16fps 假 30fps | 24fps 原生 |
| 动画幅度 | 微动（粒子飘） | 大幅动作（展翅/投矛/生长） |
| 转场 | 硬切 | dissolve + fade |
| 配音 | 女声（修复后） | 女声 + SSML 情感控制 |
| 总生成时间 | 19 小时 | 10-15 分钟 |
| 总成本 | 0 元 + 电费 | ~15-25 元（云端 API） |
