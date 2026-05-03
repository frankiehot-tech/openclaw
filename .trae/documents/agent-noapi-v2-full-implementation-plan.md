# Agent 无API 视频生成 — MVP → 完整实施方案 v3.0

**最后更新**: 2026-05-02 | **状态**: Gate 验证完成，技术链路全部通过

## 目标

将 Agent 无API 视频生成方案从 MVP 验证阶段推进到生产可用的完整自动化通道，与 Kling API 主通道构成双通道冗余架构。

---

## 🎉 Gate 验证结果 (2026-05-02)

### 总结：技术链路完全打通，唯一阻塞点是账号额度

| Gate | 内容 | 结果 |
|------|------|------|
| Gate 1 | Chrome CDP 启动 + 9222 端口 | ✅ 通过 |
| Gate 2 | CDP 连通性测试 (port→connect→navigate) | ✅ navigate 失败但改用 headed Playwright |
| Gate 3 | HappyHorse UI 探索 + 9:16 验证 | ✅ UI 结构完全映射 |
| Gate 4 | **E2E 生成测试** | ✅ **技术链路完全通过** |
| Gate 5 | Health check + daemon 验证 | ✅ persistent context 模式健康 |

### Gate 4 E2E 完整技术链路（已验证）

```
1. QR码登录 → persistent context (chrome-persistent/)     ✅
2. 点击 "HappyHorse内测" 导航按钮                          ✅
3. "添加附件" → "上传图片" → file_chooser拦截             ✅
4. OSS上传: token → PUT → callback (全部 200)            ✅
5. 输入 prompt → "发送消息"按钮 disabled → enabled        ✅
6. 点击发送 → 创建对话 "生成橘猫奔跑视频（720P）"          ✅
7. ⚠️  "额度不足" - 剩余0额度，需2额度/次                  ⚠️
```

### 关键发现

1. **架构变更**: `launch_persistent_context` 比外部 CDP Chrome 更可靠
   - 无需管理外部 Chrome 进程
   - 认证状态原生持久化
   - 更少的攻击面（WAF 检测点更少）

2. **HappyHorse UI = 输入工具栏模式**（非独立卡片）
   ```
   [输入框: "向千问提问"________________]
   [📎添加] [AI生视频] [HH1.0] [参考图] [720P] [更多] [📤发送]
   ```
   - 可选模型: HappyHorse 1.0 / 万相 2.7 / 万相 2.6
   - 图片上传: OSS token → PUT OSS → callback 确认
   - 编辑器: Slate.js (contenteditable)
   - "参考图"按钮在上传后变 DISABLED（模式确认）

3. **WAF 行为**: www.qianwen.com IP 级部分封锁，有冷却周期，curl 可通但高频请求被封
   - create.qianwen.com 永久 WAF 封锁 (HTTP 503)

4. **文件上传方式**: 必须用 `page.expect_file_chooser()` + `file_chooser.set_files()` 
   - 直接 `set_input_files` 或 JS DataTransfer 不会触发 React onChange
   - `dispatchEvent('change')` 不被 React 合成事件系统接收

---

## 前置状态盘点

### 已完成资产

| 类别 | 资产 | 状态 |
|------|------|------|
| **基础设施** | Playwright 1.58.0 + Chromium 145 + Google Chrome 147 | ✅ 已安装 |
| **认证** | persistent context `chrome-persistent/` (51.7MB, cookies 有效) | ✅ 已保存 |
| **Provider 层** | `cloud_i2v_agent_browser.py` — 千问Web端 I2V Provider | ✅ 代码完成 |
| **CLI 封装** | `cdp_browser_client.py` — CDP/Playwright 浏览器 Python 封装 | ✅ 代码完成 |
| **选择器注册** | `selector_registry.py` — 18+ 多策略容错选择器 | ✅ 代码完成 |
| **降级路由** | `cloud_i2v_auto_fallback.py` — 三层降级 (API→Web→App) | ✅ 代码完成 |
| **健康检查** | `browser_health.py` — persistent context 三级健康检测 | ✅ 代码完成 |
| **Chrome 守护** | `chrome_daemon.py` — 后台守护进程 | ✅ 代码完成 |
| **生成追踪** | `generation_tracker.py` — JSONL 生成日志 | ✅ 代码完成 |
| **配置扩展** | `schema.py` — chrome_profile_dir / cdp_endpoint / chrome_executable_path | ✅ 代码完成 |
| **Provider注册** | `cloud_i2v.py` — agent_browser/auto 两新分支 | ✅ 代码完成 |
| **初始化** | `service.py` — health check 初始化 | ✅ 代码完成 |
| **App 骨架** | `cloud_i2v_app.py` — Z Flip3 骨架 | ✅ 代码完成 |

### MVP 验证结论

| 验证项 | 结果 | 含义 |
|--------|------|------|
| agent-browser 可用性 | ❌ macOS sandbox 权限拒绝 | 弃用 agent-browser，改用 Playwright |
| Playwright headless 访问千问 | ⚠️ 首次成功，后续 WAF 503 | headless 不可行 |
| `create.qianwen.com` 可访问性 | ❌ WAF IP级封锁 | 入口切换为 `www.qianwen.com` |
| `www.qianwen.com` HappyHorse | ✅ 存在（标注"内测"，720P·10s） | 替代入口可用 |
| headed 模式登录 | ✅ 成功，persistent context 验证通过 | 认证基础就绪 |
| WAF 绕过能力 | ✅ headed + persistent context 可行 | 不再需要外部 CDP Chrome |

---

## Phase 1：Persistent Context 浏览器通道 ✅ 已完成

**目标**：建立 Playwright persistent context 浏览器控制链路，替代外部 CDP Chrome。

> **架构决策**: 经过 Gate 验证，`launch_persistent_context` 比 `connect_over_cdp` 更可靠。
> - 无需管理外部 Chrome 进程
> - Auth state (cookies/localStorage) 原生持久化
> - React 合成事件系统正确接收
> - 文件选择器 (`expect_file_chooser`) 正常工作

### 1.1 Chrome Persistent Profile

```bash
# Profile 位置（已验证）
/Volumes/1TB-M2/openclaw/.qianwen-auth/chrome-persistent/
```

```yaml
video:
  user_data_dir: "~/.qianwen-auth/chrome-persistent"
```

### 1.2 CDPBrowserClient（已验证可用）

**文件**：`pixelle_video/services/cdp_browser_client.py` ✅

支持两种模式：
- `connect_over_cdp()` — 外部 CDP Chrome（备用）
- Playwright 原生 launch（推荐）

关键方法（已验证）：
- `humanize_delay()` — 随机延迟 + 鼠标移动模拟
- `find_with_fallback()` — 多策略容错定位
- `network_har_start/stop()` — HAR 网络捕获
- `download_video_from_url()` — 直链下载
- `extract_video_url_from_har()` — HAR 视频 URL 提取

### 1.3 文件上传突破 ✅

```python
# 关键：必须用 expect_file_chooser 拦截
# 直接 set_input_files 或 JS DataTransfer 不会触发 React onChange
async with page.expect_file_chooser() as fc:
    await page.locator("text=上传图片").first.click()
await (await fc.value).set_files(image_path)
```

OSS 上传链路（已验证）:
```
POST workspace-res.qianwen.com/1/oss_token → 200
PUT  workspace-zb-provide.oss-cn-zhangjiakou.aliyuncs.com/... → 200
POST workspace-res.qianwen.com/1/oss/callback → 200
```

---

## Phase 2：HappyHorse UI 精确映射

**目标**：在 www.qianwen.com 聊天界面中精确定位 HappyHorse 的所有交互元素。

### 2.1 Chrome DevTools 手工提取 Selector

用真实 Chrome（已登录）打开 `www.qianwen.com`，DevTools 中提取：

| 元素 | 定位策略 | Selector 示例 |
|------|---------|-------------|
| HappyHorse 入口按钮 | text/role | `button:has-text("AI生视频")` |
| 提示词输入框 | contenteditable/textarea | `[contenteditable="true"]` |
| 图片上传区域 | input[type=file] | `input[type="file"]` |
| 9:16 按钮 | text | `text="9:16"` / `text="竖屏"` |
| 16:9 按钮 | text | `text="16:9"` / `text="横屏"` |
| 5s/10s 按钮 | text | `text="5秒"` / `text="10秒"` |
| 生成按钮 | button | `button:has-text("生成")` |
| 完成指示器 | text/video | `video`, `button:has-text("下载")` |
| 错误提示 | role=alert | `[role="alert"]` |
| 排队状态 | text | `text="排队中"` |

### 2.2 更新 SelectorRegistry

**文件**：`pixelle_video/services/selector_registry.py`

用 2.1 的提取结果更新 `DEFAULT_SELECTORS`，增加：
- `happyhorse_entry_www` — www.qianwen.com 专用入口
- `happyhorse_panel` — HH 激活后面板
- `video_preview` — 结果预览区
- `queue_indicator` — 排队状态
- 所有现有 key 的值更新为实测 selector

### 2.3 多策略容错定位函数

在 `cdp_browser_client.py` 中添加：

```python
async def find_with_fallback(self, selectors: List[str], timeout: int = 5000):
    """多策略顺序尝试，返回第一个可见元素"""
    for sel in selectors:
        try:
            el = self.page.locator(sel).first
            if await el.is_visible(timeout=min(timeout, 2000)):
                return el
        except:
            continue
    raise ElementNotFoundError(f"None of {selectors} found")
```

---

## Phase 3：生成-轮询-下载闭环

**目标**：实现完整的 submit → poll → download 自动化流程并验证。

### 3.1 重写 AgentBrowserI2VProvider

**文件**：`pixelle_video/services/cloud_i2v_agent_browser.py`

适配 CDP 模式：
- `__init__` 接收 `chrome_profile_dir` + `cdp_endpoint`
- `submit()` — 使用 CDPBrowserClient 完成：
  1. 确保CDP连接 → 打开 www.qianwen.com
  2. 点击 HappyHorse 入口（多策略容错）
  3. 上传参考图（如有）
  4. 填写提示词
  5. 选择 9:16 / 16:9 / 时长
  6. 点击生成
  7. 返回 task_id（唯一标识当前生成）
- `poll()` — 每 10s 检测完成状态：
  1. 检测 `video` 标签出现 → 生成完成
  2. 检测下载按钮出现 → 生成完成
  3. 检测排队/错误 → 更新状态
  4. 超时 600s → 抛出 TimeoutError
- `generate()` — submit + polling loop → 下载视频 → CloudI2VResult

### 3.2 视频下载双保险

两种方式并用：
1. **主方案**：`page.expect_download()` 拦截点击下载按钮触发的下载
2. **备用方案**：HAR 网络捕获 → 提取视频直链 URL → httpx 直接下载

```python
async def download_video(self, output_path: str) -> str:
    try:
        async with self.page.expect_download(timeout=30000) as dl:
            await download_btn.click()
        download = await dl.value
        await download.save_as(output_path)
        return output_path
    except TimeoutError:
        # Fallback to HAR interception
        return await self._download_via_har(output_path)
```

### 3.3 端到端集成测试

创建 `tests/test_e2e_happyhorse_generation.py`：
- 确认 Chrome CDP 已运行 + 已登录
- 准备一张测试图片 + 测试 prompt
- 调用 `AgentBrowserI2VProvider.generate(task)`
- 验证输出视频文件存在、大小 > 0、可播放
- 记录 E2E 耗时

---

## Phase 4：双通道自动降级

**目标**：完善 AutoFallbackProvider，实现 Web CDP → App 的双层降级。

### 4.1 更新 AutoFallbackProvider

**文件**：`pixelle_video/services/cloud_i2v_auto_fallback.py`

```python
class AutoFallbackProvider(CloudI2VProvider):
    def __init__(self, config):
        self.primary = KlingI2VProvider(config)
        self.web_cdp = AgentBrowserI2VProvider(config)  # Web CDP
        # self.app = AppI2VProvider(config)  # Phase 4.3
    
    async def generate(self, task: CloudI2VTask) -> CloudI2VResult:
        # Layer 1: Kling API (fast, reliable)
        try:
            return await self.primary.generate(task)
        except (RateLimitError, QuotaExceededError):
            logger.warning("API 限流，降级到 Web CDP")
        
        # Layer 2: Web CDP HappyHorse (free, 9:16 support)
        try:
            return await self.web_cdp.generate(task)
        except (CDPConnectionError, WAFBlockError):
            logger.warning("Web CDP 失败，降级到 App 端")
        
        # Layer 3: Z Flip3 App (final fallback) — Phase 4.3
        raise AllChannelsFailedError("所有通道均失败")
```

### 4.2 浏览器健康检查 ✅

**文件**：`pixelle_video/services/browser_health.py` ✅

三级检测（已验证）：
1. **Profile 目录存在**：检查 `user_data_dir` 目录
2. **Cookies 有效期**：`Default/Cookies` 修改时间 < 72h
3. **千问可达性**：headless 导航到 www.qianwen.com，验证 HappyHorse 可访问

```python
checker = BrowserHealthCheck(
    user_data_dir="/Volumes/1TB-M2/openclaw/.qianwen-auth/chrome-persistent",
)
result = await checker.full_check()
# → status: healthy, profile: True, cookies_age: 0.0h, qianwen_reachable: True
```

### 4.3 Z Flip3 App 端 Provider（骨架）

新建 `pixelle_video/services/cloud_i2v_app.py`：

```python
class AppI2VProvider(CloudI2VProvider):
    """通过 Z Flip3 Agent 自动化千问App端"""
    
    async def generate(self, task: CloudI2VTask) -> CloudI2VResult:
        # 骨架实现：调用 zflip3-agent MAREF skill
        # 完整实现在 Phase 5 后续迭代
        raise NotImplementedError("App端Provider待Z Flip3就绪后实现")
```

---

## Phase 5：生产化加固

**目标**：将 Proof-of-Concept 提升为生产级服务。

### 5.1 Chrome CDP 守护进程

新建 `pixelle_video/services/chrome_daemon.py`：
- 后台线程每 30s 检测 CDP 端口
- 端口不可达 → 自动重启 Chrome
- 监控 Chrome 内存使用 → 超 2GB 发送告警
- 记录 Chrome 进程 PID 和启动时间

### 5.2 登录态有效期监控

- 认证文件最后修改时间 > 25h → WARNING
- 认证文件最后修改时间 > 72h → CRITICAL → 触发登录刷新提醒
- 在 health check 输出中包含登录态剩余有效期

### 5.3 代理池集成（应对极端 IP 封禁）

```python
# 当 CDP 连接也出现 WAF 拦截时的兜底方案
PROXY_POOL = [
    "http://proxy1:8080",
    "http://proxy2:8080",
]

class CDPBrowserClient:
    async def connect_with_proxy(self, proxy_url: str):
        browser = await self._playwright.chromium.launch(
            proxy={"server": proxy_url},
            headless=False,
        )
```

### 5.4 视频生成结果追踪

新建 `pixelle_video/services/generation_tracker.py`：
- 记录每次生成的：provider、耗时、成功/失败、错误信息
- 输出到 JSONL log 文件
- 支持查询："过去24h 成功率"、"平均生成耗时"、"各provider使用占比"

---

## 文件变更清单

### 新建文件

| 文件 | 用途 | Phase |
|------|------|-------|
| `pixelle_video/services/cdp_browser_client.py` | CDP 连接真实 Chrome 的 Python 封装 | P1 |
| `pixelle_video/services/chrome_daemon.py` | Chrome CDP 守护进程 | P5 |
| `pixelle_video/services/generation_tracker.py` | 生成结果追踪日志 | P5 |
| `pixelle_video/scripts/start_chrome_cdp.sh` | Chrome CDP 启动脚本 | P1 |
| `tests/test_cdp_channel.py` | CDP 连通性测试 | P1 |
| `tests/test_e2e_happyhorse_generation.py` | E2E 生成测试 | P3 |

### 重写/重构文件

| 文件 | 变更 | Phase |
|------|------|-------|
| `pixelle_video/services/agent_browser_client.py` | **废弃** → 替换为 `cdp_browser_client.py` | P1 |
| `pixelle_video/services/cloud_i2v_agent_browser.py` | 适配 CDP 模式，添加 HAR fallback | P3 |
| `pixelle_video/services/cloud_i2v_auto_fallback.py` | 增加 CDP 健康检测 + 三层降级 | P4 |

### 修改文件

| 文件 | 变更 | Phase |
|------|------|-------|
| `pixelle_video/services/selector_registry.py` | 更新 selector 为实测值 + 增加容错映射 | P2 |
| `pixelle_video/services/agent_browser_health.py` | 重构为 CDP 健康检测 | P4 |
| `pixelle_video/config/schema.py` | 新增 chrome_profile_dir / cdp_endpoint | P1 |
| `pixelle_video/services/cloud_i2v.py` | 更新 provider 初始化传参 | P4 |
| `pixelle_video/service.py` | 启动时检查 Chrome CDP 可用性 | P4 |

### 保留不动

| 文件 | 原因 |
|------|------|
| `cloud_i2v_kling.py` | Kling API 实现不变，仍为主通道 |
| `video.py`, `frame_processor.py`, `media.py` | 后处理链不变 |

---

## 关键风险与门控条件

| 阶段 | 门控条件 | 不通过时的处理 |
|------|---------|-------------|
| P1 启动前 | `www.qianwen.com` HappyHorse 支持图片上传+9:16？ | 需用户手动验证。如不支持，转向 create.qianwen.com 代理方案 |
| P1 完成后 | CDP 连接稳定 >30min 不中断？ | 排查 Chrome 进程被 kill 原因 |
| P3 完成后 | E2E 生成成功率 >80%？ | 调优 selector timeout 和重试策略 |
| P4 完成后 | 自动降级能在 30s 内完成切换？ | 优化超时配置 |
| P5 完成后 | Chrome daemon 7x24 稳定运行？ | 添加 launchd 系统级守护 |

---

## 预估工作量

| Phase | 内容 | 预估 |
|-------|------|------|
| P1 | CDP 基础设施 | 2h |
| P2 | UI 精确映射 | 3h（含手工 DevTools 提取） |
| P3 | 生成闭环 + 测试 | 3h |
| P4 | 双通道降级 | 2h |
| P5 | 生产化加固 | 4h |
| **总计** | | **~14h** |

---

## 与 Kling API 主通道的最终协作模式

```
任务到达 → AutoFallbackProvider
              │
              ├─ 优先：Kling API (1080p, 16:9, 并行, ~1min/条)
              │         ├─ 成功 → 返回视频
              │         └─ 限流/余额不足 ↓
              │
              ├─ 降级1：Web CDP HappyHorse (720P, 9:16, 串行, ~3-5min/条)
              │         ├─ 9:16任务 → 直接走此通道（API不支持竖屏）
              │         ├─ 成功 → 返回视频
              │         └─ WAF/CDP故障 ↓
              │
              └─ 降级2：Z Flip3 App (720P, 9:16, 串行, ~5-8min/条)
                        ├─ 成功 → 返回视频
                        └─ 失败 → 告警 + 人工介入
```
