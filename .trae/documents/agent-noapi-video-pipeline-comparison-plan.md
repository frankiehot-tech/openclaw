# Agent无API视频流水线 vs 当前Cloud I2V方案 — 对比分析与实施方案

## 一、方案概述

### 当前方案：Cloud I2V (Kling API via 302.ai)
- **路径**：Pixelle-Video → 302.ai 代理 → 可灵(Kling) 官方 API
- **核心**：通过付费 API 调用实现 Image-to-Video 生成
- **实现**：`CloudI2VService` + `KlingI2VProvider`，已完整集成到 Pixelle-Video 架构

### 新方案：Agent 无API (Browser/App 自动化)
- **路径**：Agent Browser → 千问创作Web端 (c.qianwen.com) → HappyHorse 视频生成
- **核心**：通过浏览器自动化操作 Web UI，绕过 API 限制
- **备用**：Z Flip3 Agent → 千问App端 → ADB 自动化
- **后期**：CLI-Anything → Kdenlive/Shotcut/FFmpeg

---

## 二、七维对比分析

### 2.1 视频质量

| 维度 | Cloud I2V (Kling API) | Agent 无API (HappyHorse Web) |
|------|----------------------|------------------------------|
| 分辨率 | 1080p (16:9固定) | 1080p (支持9:16竖屏) |
| 帧率 | 24fps 硬编码 | 24-30fps (Web端可能更高) |
| 时长 | 仅5s或10s | 可能支持更长时长 |
| 宽高比 | **仅16:9**（关键限制） | **支持9:16竖屏**（关键优势） |
| 模式 | std / pro | Web端可能有更多选项 |
| 动画质量 | V2.5 Turbo，质量稳定 | 依赖HappyHorse底层模型 |

**结论**：HappyHorse Web端在**竖屏9:16支持**上有显著优势，这是当前 Kling API 的硬伤。当前方案需要 `adapt_resolution(letterbox_blur)` 补偿，而 Web 端可能原生支持竖屏。

### 2.2 成本

| 维度 | Cloud I2V (Kling API) | Agent 无API (HappyHorse Web) |
|------|----------------------|------------------------------|
| 单条5s视频 | 0.3 PTC (std) / 0.5 PTC (pro) | **免费**（账号额度内） |
| 单条10s视频 | 0.6 PTC (std) / 1.0 PTC (pro) | **免费**（账号额度内） |
| 17分镜Athena视频 | ~5.1-10.0 PTC | **免费**（账号额度内） |
| 隐性成本 | 无 | Agent Browser token消耗 + 运行时间 |
| 规模化成本 | 线性增长 | 账号额度限制后需多号轮换 |

**结论**：小规模使用时，Agent 无API方案成本优势明显（免费）。但规模化后，多账号管理和 token 消耗可能抵消优势。

### 2.3 可靠性

| 维度 | Cloud I2V (Kling API) | Agent 无API (HappyHorse Web) |
|------|----------------------|------------------------------|
| API稳定性 | 高（标准REST API） | **低**（依赖DOM结构，改版即失效） |
| 认证稳定性 | API Key 长期有效 | 登录态可能过期，需定期维护 |
| 错误处理 | 标准HTTP状态码 | 需要视觉检测+DOM解析 |
| 重试机制 | 已实现（3次指数退避） | 需从零实现 |
| 并发支持 | Semaphore控制，可并行 | Web端排队，串行为主 |
| 速率限制 | 302.ai 代理层处理 | 千问账号每日额度限制 |

**结论**：Cloud I2V 在可靠性上**碾压** Agent 无API方案。API 是工程化系统的基石，浏览器自动化本质是"脆弱的 hack"。

### 2.4 灵活性

| 维度 | Cloud I2V (Kling API) | Agent 无API (HappyHorse Web) |
|------|----------------------|------------------------------|
| 输入方式 | 图片+文本提示词 | 图片+文本提示词+Web UI选项 |
| 输出格式 | MP4 | MP4（可能更多格式） |
| 参数控制 | cfg_scale, mode, duration | Web端所有可配置项 |
| 批量操作 | `generate_parallel()` | batch模式，但受限于排队 |
| 模型选择 | kling-v2-5-turbo | HappyHorse底层模型（可能不同） |
| 后处理集成 | 已集成到Pipeline | 需额外实现 |

**结论**：Agent 无API方案在**参数灵活性**上可能更优（可访问Web UI所有选项），但在**工程灵活性**上不如 API。

### 2.5 速度

| 维度 | Cloud I2V (Kling API) | Agent 无API (HappyHorse Web) |
|------|----------------------|------------------------------|
| 单条生成 | 30-120s（API处理） | 30-300s（Web端排队+生成） |
| 17分镜并行 | 3-5分钟（3并发） | **30-90分钟**（串行排队） |
| 提交开销 | HTTP请求（毫秒级） | 浏览器操作（秒级） |
| 下载开销 | httpx直接下载 | 浏览器下载/HAR拦截 |

**结论**：Cloud I2V 在**并行速度**上有数量级优势。Agent 无API方案受限于Web端排队机制，无法真正并行。

### 2.6 维护成本

| 维度 | Cloud I2V (Kling API) | Agent 无API (HappyHorse Web) |
|------|----------------------|------------------------------|
| 代码维护 | 低（标准API调用） | **高**（DOM选择器频繁失效） |
| 环境依赖 | httpx | Agent Browser + Chrome + 登录态 |
| 监控需求 | 低（标准错误码） | 高（需定期检测DOM变化） |
| 升级影响 | API版本控制 | Web改版可能导致全面失效 |
| 调试难度 | 低（日志清晰） | 高（浏览器状态难以复现） |

**结论**：Agent 无API方案的维护成本**远高于** API 方案。每次千问Web端改版都可能导致自动化脚本失效。

### 2.7 架构集成度

| 维度 | Cloud I2V (Kling API) | Agent 无API (HappyHorse Web) |
|------|----------------------|------------------------------|
| 与Pixelle-Video集成 | **已完整集成** | 需新建Provider |
| Pipeline兼容 | 已通过FrameProcessor集成 | 需适配层 |
| 配置管理 | 已纳入config.yaml | 需新增配置项 |
| 错误传播 | 标准异常链 | 需转换浏览器错误 |
| 进度报告 | 已实现 | 需从零实现 |

**结论**：Cloud I2V 已深度集成，Agent 无API方案需要大量适配工作。

---

## 三、综合评分

| 维度 | Cloud I2V | Agent 无API | 权重 |
|------|-----------|-------------|------|
| 视频质量 | 7/10 | 8/10 | 20% |
| 成本 | 5/10 | 9/10 | 15% |
| 可靠性 | 9/10 | 3/10 | 20% |
| 灵活性 | 6/10 | 8/10 | 10% |
| 速度 | 9/10 | 3/10 | 15% |
| 维护成本 | 9/10 | 3/10 | 10% |
| 架构集成 | 9/10 | 2/10 | 10% |
| **加权总分** | **7.7** | **5.0** | 100% |

---

## 四、可行性判断

### 结论：**可行，但应定位为补充通道，而非替代方案**

理由：
1. **Agent 无API方案的核心价值** = 零成本 + 竖屏原生支持
2. **Agent 无API方案的核心风险** = 极低可靠性 + 高维护成本
3. **最佳策略** = 双通道架构，API为主、Agent为辅

### 不建议替代的原因
- 当前 Cloud I2V 已完整集成，替换成本高且收益不明确
- 浏览器自动化在工程化系统中是反模式（anti-pattern）
- 并行能力受限，无法满足批量生产需求

### 建议补充的原因
- 竖屏9:16原生支持是真实需求（当前需letterbox补偿）
- 零成本对试错和迭代有价值
- 双通道提供冗余，API限流时可自动降级

---

## 五、实施方案：双通道 CloudI2V 架构

### 设计原则
- **API优先**：默认走 Kling API，保证可靠性和速度
- **Agent降级**：API失败/限流时自动切换到 Agent Browser
- **统一接口**：对上层调用者透明，通过 `CloudI2VProvider` 抽象切换
- **渐进集成**：先实现 MVP，再逐步完善

### Phase 1：Agent Browser Provider 基础实现（MVP）

**目标**：实现 `AgentBrowserI2VProvider`，作为 `CloudI2VProvider` 的新实现

#### 1.1 创建 Provider 文件

新建 `pixelle_video/services/cloud_i2v_agent_browser.py`：

```python
class AgentBrowserI2VProvider(CloudI2VProvider):
    """通过 Agent Browser 自动化千问Web端实现 I2V"""
    
    async def submit(self, task: CloudI2VTask) -> CloudI2VTask:
        # 1. 启动 agent-browser，加载认证状态
        # 2. 打开 c.qianwen.com
        # 3. 定位 HappyHorse 入口
        # 4. 上传图片 + 输入提示词
        # 5. 选择参数（宽高比、时长等）
        # 6. 点击生成
        # 7. 返回 task_id（用时间戳+序号模拟）
    
    async def poll(self, task_id: str) -> CloudI2VTask:
        # 1. 检测生成状态（视觉检测或DOM检测）
        # 2. 完成时获取下载链接
        # 3. 返回更新后的 task
    
    async def generate(self, task: CloudI2VTask) -> CloudI2VResult:
        # submit + poll 循环
        # 下载视频到本地
        # 返回 CloudI2VResult
```

#### 1.2 Agent Browser 命令封装

新建 `pixelle_video/services/agent_browser_client.py`：

```python
class AgentBrowserClient:
    """Agent Browser CLI 的 Python 封装"""
    
    def __init__(self, state_path: str, download_dir: str):
        self.state_path = state_path
        self.download_dir = download_dir
    
    async def run(self, *cmds) -> dict:
        """执行 agent-browser 命令并解析 JSON 输出"""
    
    async def open_page(self, url: str) -> dict:
        """打开页面并恢复认证状态"""
    
    async def snapshot(self) -> dict:
        """获取页面交互元素快照"""
    
    async def click(self, ref: str) -> dict:
        """点击指定元素"""
    
    async def fill(self, ref: str, text: str) -> dict:
        """填写文本"""
    
    async def upload_file(self, ref: str, file_path: str) -> dict:
        """上传文件"""
    
    async def wait_for_text(self, text: str, timeout: int = 300) -> dict:
        """等待指定文本出现"""
    
    async def download_video(self, ref: str) -> str:
        """下载视频到本地"""
    
    async def batch(self, *cmds) -> dict:
        """批量执行命令"""
```

#### 1.3 配置扩展

在 `schema.py` 中扩展配置：

```python
class VideoSubConfig(BaseModel):
    cloud_i2v_provider: Optional[str] = Field(
        default=None,
        description="Cloud I2V provider: kling/agent_browser/auto"
    )
    agent_browser_state_path: Optional[str] = Field(
        default="~/.agent-states/qianwen-auth.state",
        description="Agent Browser 认证状态文件路径"
    )
    agent_browser_download_dir: Optional[str] = Field(
        default=None,
        description="Agent Browser 视频下载目录"
    )
    agent_browser_fallback: bool = Field(
        default=True,
        description="API失败时自动降级到 Agent Browser"
    )
```

#### 1.4 Provider 注册

在 `cloud_i2v.py` 的 `_init_provider()` 中注册新 Provider：

```python
def _init_provider(self, config: dict):
    provider = config.get("cloud_i2v_provider", "kling")
    if provider == "kling":
        return KlingI2VProvider(config)
    elif provider == "agent_browser":
        return AgentBrowserI2VProvider(config)
    elif provider == "auto":
        return AutoFallbackProvider(config)  # 新增：自动降级
```

### Phase 2：自动降级机制

**目标**：实现 `AutoFallbackProvider`，API优先 + Agent降级

```python
class AutoFallbackProvider(CloudI2VProvider):
    """自动降级：Kling API → Agent Browser"""
    
    def __init__(self, config: dict):
        self.primary = KlingI2VProvider(config)
        self.fallback = AgentBrowserI2VProvider(config)
        self.fallback_enabled = config.get("agent_browser_fallback", True)
    
    async def generate(self, task: CloudI2VTask) -> CloudI2VResult:
        try:
            result = await self.primary.generate(task)
            return result
        except (RateLimitError, QuotaExceededError, APIError) as e:
            if self.fallback_enabled:
                logger.warning(f"API failed: {e}, falling back to Agent Browser")
                return await self.fallback.generate(task)
            raise
```

### Phase 3：Z Flip3 App端备用通道

**目标**：复用现有 `agent_system/device_control/` 实现 App 端自动化

新建 `pixelle_video/services/cloud_i2v_app.py`：

```python
class AppI2VProvider(CloudI2VProvider):
    """通过 Z Flip3 Agent 自动化千问App端实现 I2V"""
    
    def __init__(self, config: dict):
        from agent_system.device_control import ADBClient, ScreenCapture
        self.adb = ADBClient(device_id="zflip3")
        self.screen = ScreenCapture(self.adb)
        # 复用 DeepSeek Vision 做UI状态识别
    
    async def submit(self, task: CloudI2VTask) -> CloudI2VTask:
        # 1. adb shell am start 千问App
        # 2. 截图 → Vision 识别 HappyHorse 入口
        # 3. tap 进入
        # 4. input_text 提示词
        # 5. tap 选择参数
        # 6. tap 生成
    
    async def poll(self, task_id: str) -> CloudI2VTask:
        # 循环截图 → Vision 检测进度条/完成状态
    
    async def generate(self, task: CloudI2VTask) -> CloudI2VResult:
        # submit + poll + adb pull 下载
```

### Phase 4：坚固化与监控

#### 4.1 DOM 选择器热修复机制

```python
class SelectorRegistry:
    """千问Web端选择器注册表，支持热更新"""
    
    selectors = {
        "happyhorse_entry": {"strategy": "text", "value": "视频生成"},
        "prompt_input": {"strategy": "role", "value": "textbox"},
        "generate_button": {"strategy": "text", "value": "生成"},
        "download_button": {"strategy": "text", "value": "下载"},
        "aspect_ratio_9_16": {"strategy": "text", "value": "9:16"},
    }
    
    @classmethod
    def update(cls, key: str, selector: dict):
        """热更新选择器，无需重启服务"""
```

#### 4.2 健康检查与告警

```python
class AgentBrowserHealthCheck:
    """定期检测 Agent Browser 通道健康状态"""
    
    async def check_auth_state(self) -> bool:
        """检测认证状态是否有效"""
    
    async def check_dom_compatibility(self) -> bool:
        """检测关键DOM选择器是否仍然有效"""
    
    async def full_e2e_test(self) -> bool:
        """端到端测试：生成一条5s视频"""
```

#### 4.3 生成结果缓存与去重

```python
class VideoGenerationCache:
    """相同 prompt 的生成结果缓存"""
    
    async def get(self, image_hash: str, prompt: str) -> Optional[str]:
        """检查是否已有相同输入的生成结果"""
    
    async def put(self, image_hash: str, prompt: str, video_path: str):
        """缓存生成结果"""
```

---

## 六、文件变更清单

### 新建文件
| 文件 | 用途 |
|------|------|
| `pixelle_video/services/agent_browser_client.py` | Agent Browser CLI 封装 |
| `pixelle_video/services/cloud_i2v_agent_browser.py` | Web端 I2V Provider |
| `pixelle_video/services/cloud_i2v_app.py` | App端 I2V Provider (Phase 3) |
| `pixelle_video/services/cloud_i2v_auto_fallback.py` | 自动降级 Provider |
| `pixelle_video/services/selector_registry.py` | DOM选择器热更新 |
| `pixelle_video/services/agent_browser_health.py` | 健康检查 |

### 修改文件
| 文件 | 变更 |
|------|------|
| `pixelle_video/services/cloud_i2v.py` | `_init_provider()` 注册新 Provider |
| `pixelle_video/config/schema.py` | 扩展 VideoSubConfig 配置项 |
| `pixelle_video/service.py` | 传递新配置到 CloudI2VService |
| `scripts/gen_athena_v2.py` | 支持 `provider="auto"` 模式 |

---

## 七、风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| 千问Web端改版导致DOM失效 | 高 | 高 | SelectorRegistry热更新 + Skyvern视觉兜底 |
| Agent Browser项目停止维护 | 中 | 高 | 备选Browser Use (78K stars) |
| 登录态频繁过期 | 中 | 中 | 定期刷新 + 异常时通知人工 |
| Web端排队严重 | 中 | 中 | 自动降级回API通道 |
| Agent Browser安装复杂 | 低 | 中 | Docker化部署 |
| 并行生成受限 | 确定 | 中 | 串行+缓存，API通道负责并行 |

---

## 八、实施优先级建议

| 阶段 | 任务 | 前置条件 | 优先级 |
|------|------|---------|--------|
| **MVP** | 安装 Agent Browser，手动验证千问Web端自动化可行性 | Mac mini M4 环境 | P0 |
| **P1** | 实现 `AgentBrowserI2VProvider` + `AgentBrowserClient` | MVP验证通过 | P1 |
| **P2** | 实现 `AutoFallbackProvider`（API优先+Agent降级） | P1完成 | P1 |
| **P3** | Z Flip3 App端 Provider | P1完成 + Z Flip3可用 | P2 |
| **P4** | 坚固化（选择器热更新、健康检查、缓存） | P2完成 | P2 |

### MVP 验证清单（在写代码之前必须先验证）

1. [ ] Mac mini M4 上安装 Agent Browser
2. [ ] 人工登录千问创作Web端，保存认证状态
3. [ ] 用 batch 模式完成一次完整的视频生成流程
4. [ ] 验证竖屏9:16选项是否可用
5. [ ] 验证视频下载方式（直链/HAR拦截）
6. [ ] 测量单条生成的端到端耗时
7. [ ] 测试认证状态的有效期

---

## 九、最终建议

### 短期（1-2周）
1. **先完成 MVP 验证**：确认 Agent Browser 能否可靠地自动化千问Web端
2. **如果 MVP 通过**：实现 P1（AgentBrowserI2VProvider），作为竖屏生成的专用通道
3. **保持 Kling API 为默认通道**：只在需要竖屏或API限流时切换

### 中期（1个月）
4. 实现 AutoFallbackProvider，构建双通道冗余
5. 实现 Z Flip3 App端作为第三通道
6. 完善监控和告警

### 长期
7. 关注 Kling API 是否开放竖屏9:16支持（一旦支持，Agent Browser 的核心优势消失）
8. 关注千问是否开放 HappyHorse API（一旦开放，Agent Browser 方案可退役）

**核心判断**：Agent 无API方案是一个**有价值的补充通道**，特别在竖屏生成和零成本试错方面。但它**不应替代** API 方案，因为可靠性差距太大。最佳策略是双通道架构，API为主、Agent为辅。
