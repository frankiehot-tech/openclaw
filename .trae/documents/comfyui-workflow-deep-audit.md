# ComfyUI 工作流深度审计计划

## 审计范围

对 `/Volumes/1TB-M2/openclaw` 项目中所有 ComfyUI 相关代码、配置、工作流定义进行系统性深度审计，识别架构缺陷、代码质量问题、功能缺失和安全风险。

---

## 一、现状概要

### 1.1 文件分布

| 区域 | 文件数 | 说明 |
|------|--------|------|
| 自研核心模块 (`scripts/clawra/`) | 7 个 .py + 1 个 .backup | Athena 生成器、插件管理器、面板集成、LTX2.3 集成、迁移优化器 |
| 外部 CLI 工具 (`scripts/clawra/external/ROMA/CLI-Anything-Repo/`) | 10+ 个 .py | 第三方 ComfyUI CLI 客户端 |
| 配置引用 (`pyproject.toml`, `cleanup.sh`) | 2 | comfyui_workspace 排除规则 |
| 文档引用 | 4 | 审计报告中的技术组件描述 |

### 1.2 基础设施状态

- **ComfyUI 安装目录** (`/Volumes/1TB-M2/openclaw/ComfyUI`): **不存在**
- **ComfyUI 工作区** (`/Volumes/1TB-M2/openclaw/comfyui_workspace`): **不存在**
- **模型文件** (`v1-5-pruned.safetensors`): **不存在**
- **ComfyUI 服务器**: **未运行**（无进程监听 8188/8189）

### 1.3 功能成熟度

| 模块 | 状态 | 说明 |
|------|------|------|
| Athena 肖像生成 (txt2img) | 🟡 可运行但未验证 | 工作流结构正确，但依赖的服务器/模型不存在 |
| 漫画面板生成 | 🔴 纯模拟器 | `ComfyUIPanelsSimulator` 只生成灰色占位图 |
| LTX2.3 漫剧工作流 | 🔴 纯模拟器 | 节点类型是虚构的，无真实 ComfyUI 节点 |
| 插件管理器 | 🟡 部分可用 | 安装逻辑完整，但依赖不存在的 ComfyUI 目录 |
| 迁移优化器 | 🔴 无法运行 | `__init__` 中直接调用 `.stat()` 会崩溃 |

---

## 二、发现的问题清单

### 🔴 严重问题 (P0)

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| P0-1 | ComfyUI 安装目录和工作区均不存在 | `comfyui_plugin_manager.py:19-21`, `comfyui_athena_generator.py:46` | 所有脚本无法运行 |
| P0-2 | 端口不一致：自研用 8189，外部 CLI 用 8188 | `comfyui_athena_generator.py:33` vs `comfyui_backend.py:15` | 两套系统无法协同 |
| P0-3 | 迁移优化器 `__init__` 直接调用 `.stat()` 会崩溃 | `migrate_comfyui_to_external.py:41` | 模型文件不存在时 IndexError |
| P0-4 | 漫画面板和 LTX2.3 工作流均为占位符 | `comfyui_plugin_manager.py:406-422` | 高级功能完全不可用 |

### 🟡 中等问题 (P1)

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| P1-1 | 两套 API 客户端功能重叠，接口不兼容 | `comfyui_athena_generator.py` vs `comfyui_backend.py` | 维护成本高，行为不一致 |
| P1-2 | 备份文件残留 | `comfyui_athena_generator.py.backup` | 仓库污染 |
| P1-3 | 重复 `import time` | `comfyui_athena_generator.py:9,89` | 代码质量 |
| P1-4 | 工作流节点 ID 生成方式不一致 | generator 用 MD5 hash，plugin_manager 用硬编码 `0e31e40d_` | 调试困难 |
| P1-5 | 无独立 .json 工作流文件 | 所有工作流内嵌 Python | 无法被 ComfyUI Web UI 直接导入 |
| P1-6 | 硬编码模型文件大小 | `migrate_comfyui_to_external.py:52` | 脆弱性 |

### 🟢 轻微问题 (P2)

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| P2-1 | `sys.path.append` 动态修改导入路径 | 多个文件 | 隐式依赖 |
| P2-2 | `cleanup.sh` 排除 comfyui_workspace | `ops/deploy/cleanup.sh:88` | 大文件不会被清理 |
| P2-3 | `analyze_reference_images.py` 硬编码路径 | 引用 comfyui_workspace/output | 耦合 |
| P2-4 | 缺少类型注解和文档字符串 | 多个文件 | 可维护性 |

---

## 三、审计执行计划

### Phase 1: 代码质量审计 (只读)

**目标**: 对所有 ComfyUI 相关 Python 文件进行静态分析

1. 对 `scripts/clawra/comfyui_*.py` 运行 ruff check（当前被 pyproject.toml 排除）
2. 对 `scripts/clawra/comfyui_*.py` 运行 mypy 类型检查
3. 检查所有硬编码路径（绝对路径 `/Volumes/1TB-M2/...`）
4. 检查所有 `requests` 调用的错误处理是否完整
5. 检查工作流 JSON 结构是否符合 ComfyUI API 规范
6. 生成代码质量报告

### Phase 2: 架构审计 (只读)

**目标**: 评估 ComfyUI 集成的架构合理性

1. 绘制模块依赖关系图
2. 分析两套 API 客户端的重叠度和差异
3. 评估工作流定义方式的优缺点（内嵌 vs 外部 JSON）
4. 评估模拟器模式对项目进展的影响
5. 分析配置碎片化问题（端口、路径、API 封装）
6. 生成架构审计报告

### Phase 3: 可运行性审计 (只读)

**目标**: 评估当前代码在真实环境中的可运行性

1. 检查 ComfyUI 是否已安装（搜索系统路径）
2. 检查模型文件是否可用
3. 验证工作流 JSON 结构的正确性（用 CLI-Anything 的 `validate_workflow`）
4. 检查 Python 依赖是否满足（PIL, numpy, requests 等）
5. 评估从当前状态到可运行状态需要的最小步骤
6. 生成可运行性评估报告

### Phase 4: 安全审计 (只读)

**目标**: 识别安全风险

1. 检查 API 调用是否有认证机制
2. 检查是否有路径遍历风险（用户输入直接拼接到文件路径）
3. 检查子进程调用安全性（`subprocess` 使用方式）
4. 检查是否有敏感信息泄露（API key、路径信息）
5. 生成安全审计报告

### Phase 5: 生成综合审计报告 (只读)

**目标**: 汇总所有发现，给出优先级排序的改进建议

1. 汇总 Phase 1-4 的发现
2. 按严重程度排序所有问题
3. 给出短期修复建议（可立即执行的）
4. 给出中期重构建议（架构改进）
5. 给出长期演进建议（功能路线图）
6. 写入综合审计报告

---

## 四、预期产出

1. **代码质量报告** — ruff/mypy 扫描结果 + 人工审查发现
2. **架构审计报告** — 模块关系图 + 重叠分析 + 改进建议
3. **可运行性评估** — 当前状态 → 可运行状态的最小路径
4. **安全审计报告** — 风险清单 + 修复建议
5. **综合审计报告** — 汇总 + 优先级排序 + 行动计划

所有报告以文件形式写入 `docs/audit/2026-04/` 目录。

---

## 五、注意事项

- 本次审计为**只读操作**，不修改任何代码或配置
- 外部第三方代码 (`scripts/clawra/external/ROMA/`) 仅做参考分析，不纳入核心质量指标
- 审计重点关注**自研模块**的代码质量和架构合理性
- 所有发现将记录到 wiki 知识库以便后续会话参考
