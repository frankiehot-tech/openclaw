# ComfyUI 工作流深度审计报告

**审计日期**: 2026-04-27
**审计范围**: `/Volumes/1TB-M2/openclaw` 项目中所有 ComfyUI 相关代码、配置、工作流
**审计方法**: SAST (ruff) + 人工代码审查 + 运行时环境检查

---

## 一、执行摘要

### 总体评级: 🟡 原型可用，需重构 (5.5/10)

ComfyUI 集成的基础设施**已部署**（ComfyUI2 运行在 8188 端口，模型文件齐全），但自研代码与实际部署环境**严重脱节**：代码中硬编码的端口、路径与实际运行配置不一致，导致核心生成器无法连接到已运行的 ComfyUI 服务器。

### 关键数据

| 指标 | 值 |
|------|-----|
| 自研 Python 文件 | 9 个 |
| 代码总行数 | ~2,700 行 |
| ruff 检出问题 | 129 个 (111 可自动修复) |
| 硬编码绝对路径 | 3 处 (ComfyUI 模块内) |
| ComfyUI 工作区大小 | 41 GB |
| 输出图像大小 | 7.0 GB |
| 已安装模型 | 2 个 (v1-5-pruned 7.17GB + sdxl_lightning 6.46GB) |
| ComfyUI 服务器状态 | ✅ 运行中 (PID 40649, 端口 8188) |
| 自定义节点 | 1 个 (VideoHelperSuite) |

---

## 二、基础设施现状 (修正)

### 2.1 实际部署状态

| 组件 | 状态 | 路径/端口 |
|------|------|-----------|
| ComfyUI2 | ✅ 已安装 | `/Volumes/1TB-M2/openclaw/comfyui_workspace/ComfyUI2/` |
| ComfyUI 服务器 | ✅ 运行中 | `127.0.0.1:8188` (PID 40649) |
| 模型 v1-5-pruned | ✅ 存在 | `comfyui_workspace/models/checkpoints/` (7.17 GB) |
| 模型 sdxl_lightning | ✅ 存在 | `comfyui_workspace/models/checkpoints/` (6.46 GB) |
| 备份模型 | ⚠️ 冗余 | `sdxl_lightning_4step.safetensors.bak` (6.46 GB) |
| Wan2.1 视频模型 | ✅ 存在 | `ComfyUI2/models/diffusion_models/` |
| Python 依赖 | ✅ 满足 | requests 2.33.0, PIL, numpy 2.4.3 |
| 工作流 JSON | ✅ 2 个 | `athena_silicon_symbiosis.json`, `athena_social_media_v1.json` |
| 输出图像 | ✅ ~46 张 | `comfyui_workspace/output/` |

### 2.2 代码与部署的脱节

**这是本次审计发现的最核心问题**：

| 代码中的配置 | 实际部署 | 影响 |
|-------------|---------|------|
| 端口 `8189` ([comfyui_athena_generator.py:33](file:///Volumes/1TB-M2/openclaw/scripts/clawra/comfyui_athena_generator.py#L33)) | 端口 `8188` (start_comfyui.sh) | ❌ 连接失败 |
| ComfyUI 目录 `/Volumes/1TB-M2/openclaw/ComfyUI` ([plugin_manager.py:19](file:///Volumes/1TB-M2/openclaw/scripts/clawra/comfyui_plugin_manager.py#L19)) | 实际在 `comfyui_workspace/ComfyUI2/` | ❌ 路径不存在 |
| 工作区 `comfyui_workspace` 不存在假设 ([初始审计结论](file:///Volumes/1TB-M2/openclaw/.trae/documents/comfyui-workflow-deep-audit.md)) | 工作区存在且 41GB | ✅ 实际可用 |
| 默认模型 `v1-5-pruned.safetensors` | ✅ 存在于 `comfyui_workspace/models/checkpoints/` | ✅ 匹配 |
| start_comfyui.sh 使用 SDXL-Lightning | 代码默认使用 v1-5-pruned | ⚠️ 不一致 |

---

## 三、代码质量审计 (Phase 1)

### 3.1 ruff 扫描结果

**总计 129 个问题**，分布：

| 规则 | 数量 | 严重度 | 说明 |
|------|------|--------|------|
| UP006 | 41 | 低 | 使用 `list` 替代 `List` (PEP 585) |
| F541 | 39 | 低 | f-string 无占位符 |
| F401 | 15 | 中 | 未使用的 import |
| UP045 | 13 | 低 | 使用 `X \| None` 替代 `Optional[X]` |
| UP035 | 10 | 低 | 废弃的 import 路径 |
| E722 | 3 | 高 | 裸 except |
| B905 | 2 | 中 | zip() 缺少 strict 参数 |
| UP015 | 2 | 低 | 不必要的文件打开模式 |
| B007 | 1 | 低 | 未使用的循环变量 |
| C401 | 1 | 低 | 不必要的生成器 set |
| SIM114 | 1 | 低 | 相同条件的 if 可合并 |
| SIM118 | 1 | 低 | 使用 `key in dict` 替代 `key in dict.keys()` |

**111 个可自动修复** (`ruff check --fix`)。

### 3.2 按文件分布

| 文件 | 问题数 | 主要问题 |
|------|--------|----------|
| ltx23_workflow_integration.py | ~55 | F541, E722, UP006, UP045, B007, B905 |
| migrate_comfyui_to_external.py | ~40 | F541, F401, UP015 |
| comfyui_plugin_manager.py | ~15 | F401, UP006 |
| comfyui_panels_integration.py | ~10 | UP006, UP035 |
| comfyui_athena_generator.py | ~5 | UP006, UP035 |
| test_comfyui_athena.py | ~4 | F401, SIM118 |

### 3.3 硬编码路径

ComfyUI 模块内的硬编码绝对路径：

| 文件 | 行号 | 路径 |
|------|------|------|
| [comfyui_athena_generator.py](file:///Volumes/1TB-M2/openclaw/scripts/clawra/comfyui_athena_generator.py#L46) | 46 | `/Volumes/1TB-M2/openclaw/comfyui_workspace` |
| [comfyui_plugin_manager.py](file:///Volumes/1TB-M2/openclaw/scripts/clawra/comfyui_plugin_manager.py#L19) | 19 | `/Volumes/1TB-M2/openclaw/ComfyUI` |
| [comfyui_plugin_manager.py](file:///Volumes/1TB-M2/openclaw/scripts/clawra/comfyui_plugin_manager.py#L21) | 21 | `/Volumes/1TB-M2/openclaw/comfyui_workspace` |
| [ltx23_workflow_integration.py](file:///Volumes/1TB-M2/openclaw/scripts/clawra/ltx23_workflow_integration.py#L91) | 91 | `/Volumes/1TB-M2/openclaw/comfyui_workspace/output/ltx23_videos` |
| [comfyui_panels_integration.py](file:///Volumes/1TB-M2/openclaw/scripts/clawra/comfyui_panels_integration.py#L199) | 199 | `/Volumes/1TB-M2/openclaw/comfyui_workspace/output/comic_pages` |
| [check_comfyui_images.py](file:///Volumes/1TB-M2/openclaw/scripts/clawra/check_comfyui_images.py#L13) | 13 | `/Volumes/1TB-M2/openclaw/comfyui_workspace/output` |
| [generate_athena_full.py](file:///Volumes/1TB-M2/openclaw/scripts/clawra/generate_athena_full.py#L40) | 40 | `/Volumes/1TB-M2/openclaw/comfyui_workspace/output` |
| [migrate_comfyui_to_external.py](file:///Volumes/1TB-M2/openclaw/scripts/clawra/migrate_comfyui_to_external.py#L22) | 22-24 | `/Volumes/1TB-M2/openclaw/ComfyUI` + `comfyui_workspace` |

### 3.4 错误处理问题

- **21 处裸 `except Exception`**：所有 ComfyUI 模块的错误处理都使用宽泛的 `except Exception`，吞没了具体错误类型
- **3 处裸 `except:`**（[ltx23_workflow_integration.py:291](file:///Volumes/1TB-M2/openclaw/scripts/clawra/ltx23_workflow_integration.py#L291), [327](file:///Volumes/1TB-M2/openclaw/scripts/clawra/ltx23_workflow_integration.py#L327)）：最危险的错误处理模式
- **无重试机制**：`queue_prompt()` 和 `wait_for_completion()` 失败后直接返回，无重试逻辑
- **无超时配置统一**：各方法使用不同的硬编码超时值（10s, 30s, 60s, 300s）

### 3.5 工作流 JSON 验证

| 工作流文件 | 格式 | ComfyUI API 兼容 |
|-----------|------|------------------|
| `athena_silicon_symbiosis.json` | ❌ 参数描述格式 | ❌ 不是 API 格式的工作流 |
| `athena_social_media_v1.json` | ❌ 业务编排格式 | ❌ 不是 API 格式的工作流 |

两个 JSON 文件都是**参数描述/业务编排格式**，不是 ComfyUI API 可直接执行的节点图格式。代码中的 `create_athena_workflow()` 方法构建的才是正确的 API 格式。

---

## 四、架构审计 (Phase 2)

### 4.1 模块依赖关系

```
comfyui_athena_generator.py  ←── comfyui_panels_integration.py
       ↑                              ↑
       │                              │
       └── test_comfyui_athena.py     └── ltx23_workflow_integration.py
       └── generate_athena_full.py
       └── check_comfyui_images.py (独立)

comfyui_plugin_manager.py (独立，无被依赖)
migrate_comfyui_to_external.py (独立，无被依赖)

external/ROMA/CLI-Anything-Repo/comfyui/ (完全独立)
```

### 4.2 两套 API 客户端对比

| 维度 | 自研 (ComfyUIAthenaGenerator) | 外部 (cli-anything-comfyui) |
|------|------|------|
| 默认端口 | 8189 | 8188 |
| 错误处理 | print + return None | raise RuntimeError |
| API 方法数 | 7 | 4 (通用) |
| 工作流验证 | ❌ 无 | ✅ validate_workflow() |
| 模型发现 | ✅ get_available_checkpoints() | ✅ 更完整 |
| 图像下载 | ✅ stream download | ✅ raw bytes |
| 队列管理 | ✅ wait_for_completion() | ✅ 更完整 |
| 类型安全 | 部分 | 更完整 |
| 测试覆盖 | 1 个测试文件 | 2 个测试文件 (853行) |

### 4.3 配置碎片化

**端口配置分散在 5 个位置**：

1. `comfyui_athena_generator.py:33` → `8189`
2. `comfyui_panels_integration.py:362` → `8189`
3. `ltx23_workflow_integration.py:88` → `8189`
4. `comfyui_backend.py:15` → `8188`
5. `start_comfyui.sh:47` → `8188` ← **实际运行端口**
6. `config.yaml:16` → `8188` ← **Pixelle 配置**

**路径配置分散在 8+ 个位置**，无统一配置文件。

### 4.4 模拟器问题

| 模拟器 | 文件 | 实际功能 |
|--------|------|----------|
| ComfyUIPanelsSimulator | comfyui_panels_integration.py | 生成灰色占位图 + 文字水印 |
| LTX23WorkflowIntegrator | ltx23_workflow_integration.py | 虚构节点 + 占位图 + ffmpeg 拼接 |
| integrate_with_comfyui() | comfyui_panels_integration.py:362 | 仅检查服务器状态，不实际注册节点 |

**影响**：漫画面板和 LTX2.3 漫剧功能完全不可用，但代码结构已搭好，替换为真实实现时改动量可控。

---

## 五、可运行性审计 (Phase 3)

### 5.1 最小修复路径

从当前状态到可运行状态，需要修复的最小步骤：

**Step 1: 修复端口 (1 处改动)**
- [comfyui_athena_generator.py:33](file:///Volumes/1TB-M2/openclaw/scripts/clawra/comfyui_athena_generator.py#L33): `8189` → `8188`

**Step 2: 修复 ComfyUI 目录路径 (1 处改动)**
- [comfyui_plugin_manager.py:19](file:///Volumes/1TB-M2/openclaw/scripts/clawra/comfyui_plugin_manager.py#L19): `ComfyUI` → `comfyui_workspace/ComfyUI2`

**Step 3: 修复迁移优化器崩溃 (1 处改动)**
- [migrate_comfyui_to_external.py:41](file:///Volumes/1TB-M2/openclaw/scripts/clawra/migrate_comfyui_to_external.py#L41): 添加 `exists()` 检查后再调用 `.stat()`

**修复后预期**：`ComfyUIAthenaGenerator` 可成功连接到运行中的 ComfyUI 服务器并生成图像。

### 5.2 已知运行时问题

1. **ComfyUI 启动冲突**：日志显示 `OSError: [Errno 48] address already in use`，说明有多个 ComfyUI 实例尝试启动
2. **模型冗余**：`sdxl_lightning_4step.safetensors.bak` 占用 6.46 GB，应清理
3. **输出目录膨胀**：7.0 GB 输出图像无自动清理机制
4. **ComfyUI2 使用 Python 3.14**：与项目 .venv311 (Python 3.11) 不一致

---

## 六、安全审计 (Phase 4)

### 6.1 风险清单

| # | 风险 | 严重度 | 位置 | 说明 |
|---|------|--------|------|------|
| S1 | 路径遍历 | 🟡 中 | [comfyui_athena_generator.py:326](file:///Volumes/1TB-M2/openclaw/scripts/clawra/comfyui_athena_generator.py#L326) | `filename` 参数直接拼接到 URL，可能被利用访问任意文件 |
| S2 | Git 仓库 URL 注入 | 🟢 低 | [comfyui_plugin_manager.py:188](file:///Volumes/1TB-M2/openclaw/scripts/clawra/comfyui_plugin_manager.py#L188) | `repo_url` 传入 `git clone`，但使用列表形式，命令注入风险低 |
| S3 | 无 API 认证 | 🟡 中 | 全部 | ComfyUI 服务器无认证，局域网内任何人可访问 |
| S4 | pip install 任意依赖 | 🟡 中 | [comfyui_plugin_manager.py:194](file:///Volumes/1TB-M2/openclaw/scripts/clawra/comfyui_plugin_manager.py#L194) | 安装插件时自动执行 `pip install -r requirements.txt` |
| S5 | 敏感路径泄露 | 🟢 低 | 多处 | 硬编码绝对路径暴露了文件系统结构 |

### 6.2 安全建议

1. **S1**: 对 `filename` 参数进行路径清洗，拒绝包含 `..` 或绝对路径的输入
2. **S3**: ComfyUI 绑定 `127.0.0.1` 已限制为本地访问，风险可控
3. **S4**: 添加依赖白名单或用户确认机制

---

## 七、完整问题清单 (按优先级)

### 🔴 P0 — 阻断性问题

| # | 问题 | 修复工作量 | 影响 |
|---|------|-----------|------|
| P0-1 | 端口不一致：代码用 8189，服务器用 8188 | 1 行 | 核心生成器无法连接 |
| P0-2 | ComfyUI 目录路径错误：代码指向 `/ComfyUI`，实际在 `comfyui_workspace/ComfyUI2` | 1 行 | 插件管理器无法工作 |
| P0-3 | 迁移优化器 `__init__` 崩溃：直接调用 `.stat()` | 3 行 | 脚本无法启动 |

### 🟡 P1 — 重要问题

| # | 问题 | 修复工作量 | 影响 |
|---|------|-----------|------|
| P1-1 | 两套 API 客户端重叠 | 重构 | 维护成本高 |
| P1-2 | 配置碎片化（端口/路径散落 8+ 处） | 中 | 难以维护 |
| P1-3 | 漫画面板/LTX2.3 为模拟器 | 大 | 高级功能不可用 |
| P1-4 | 工作流 JSON 不是 API 格式 | 中 | 无法被 ComfyUI Web UI 导入 |
| P1-5 | 备份文件残留 (.backup) | 1 行 | 仓库污染 |
| P1-6 | 冗余模型文件 (.bak 6.46GB) | 1 命令 | 磁盘浪费 |
| P1-7 | 129 个 ruff 问题 | 自动 | 代码质量 |

### 🟢 P2 — 改进建议

| # | 问题 | 修复工作量 | 影响 |
|---|------|-----------|------|
| P2-1 | 无统一配置文件 | 中 | 可维护性 |
| P2-2 | 无重试机制 | 小 | 可靠性 |
| P2-3 | 路径遍历风险 | 小 | 安全性 |
| P2-4 | 输出目录无自动清理 | 小 | 磁盘管理 |
| P2-5 | `sys.path.append` 动态导入 | 小 | 代码规范 |
| P2-6 | 缺少类型注解 | 中 | 可维护性 |

---

## 八、行动计划

### 短期 (1-2 小时，立即可执行)

1. **修复端口不一致**：将 `comfyui_athena_generator.py:33` 的 `8189` 改为 `8188`
2. **修复 ComfyUI 目录路径**：将 `comfyui_plugin_manager.py:19` 的路径改为 `comfyui_workspace/ComfyUI2`
3. **修复迁移优化器崩溃**：添加 `exists()` 检查
4. **删除备份文件**：`rm comfyui_athena_generator.py.backup`
5. **清理冗余模型**：`rm comfyui_workspace/models/checkpoints/sdxl_lightning_4step.safetensors.bak` (释放 6.46 GB)
6. **运行 ruff --fix**：自动修复 111 个代码风格问题

### 中期 (1-2 天)

1. **统一配置**：创建 `comfyui_config.py` 集中管理端口、路径、超时等配置
2. **合并 API 客户端**：以外部 CLI-Anything 的 `comfyui_backend.py` 为底层，自研生成器调用它
3. **创建 API 格式的工作流 JSON**：将 `create_athena_workflow()` 的输出保存为可导入的 JSON
4. **添加重试机制**：对 `queue_prompt()` 和 `wait_for_completion()` 添加指数退避重试
5. **修复路径遍历**：对 `download_image()` 的 `filename` 参数进行清洗

### 长期 (1-2 周)

1. **替换模拟器为真实实现**：对接 comfyui_panels 插件和 LTX2.3 工作流
2. **添加输出目录自动清理**：基于时间/大小的自动清理策略
3. **添加 ComfyUI 健康检查**：定期检查服务器状态和模型可用性
4. **完善测试覆盖**：添加 mock 测试，不依赖运行中的 ComfyUI 服务器
5. **添加 CI 集成**：将 ComfyUI 模块纳入 ruff/mypy 检查范围

---

## 九、附录

### A. 文件清单

| 文件 | 行数 | 功能 | 可运行 |
|------|------|------|--------|
| comfyui_athena_generator.py | 515 | 核心生成器 | ❌ 端口错误 |
| comfyui_plugin_manager.py | 479 | 插件管理 | ❌ 路径错误 |
| comfyui_panels_integration.py | 463 | 漫画面板模拟 | ⚠️ 仅占位图 |
| ltx23_workflow_integration.py | 607 | LTX2.3 漫剧模拟 | ⚠️ 仅占位图 |
| migrate_comfyui_to_external.py | 736 | 迁移优化器 | ❌ 崩溃 |
| check_comfyui_images.py | 134 | 图像质量检查 | ✅ |
| test_comfyui_athena.py | 152 | 生成器测试 | ❌ 端口错误 |
| generate_athena_full.py | 56 | 完整生成测试 | ❌ 端口错误 |
| analyze_reference_images.py | ~100 | 参考图分析 | ✅ |

### B. ComfyUI 服务器信息

- **版本**: ComfyUI2 (从 `~/AI-Video-Studio/ComfyUI2` 复制)
- **运行端口**: 8188
- **运行模式**: `--lowvram --force-fp16 --disable-xformers`
- **Python 环境**: `comfyui_workspace/ai_studio_env/` (Python 3.14)
- **自定义节点**: ComfyUI-VideoHelperSuite
- **PID 文件**: `comfyui_workspace/comfyui.pid`

### C. 工作流模板

1. **athena_silicon_symbiosis.json** — 参数描述格式，含 3 个变体（战斗/未来/思考形态）
2. **athena_social_media_v1.json** — 业务编排格式，含 Discord 发布配置

### D. 磁盘使用

| 目录 | 大小 | 说明 |
|------|------|------|
| comfyui_workspace/ | 41 GB | 总计 |
| comfyui_workspace/output/ | 7.0 GB | 生成图像 |
| models/checkpoints/ | ~20 GB | 模型文件 (含冗余 .bak) |
| ComfyUI2/ | ~14 GB | ComfyUI 安装 + Wan2.1 模型 |
