---
type: pattern
created: 2026-04-24
updated: 2026-04-24
tags: [patterns, best-practices, traps]
---

# 模式与最佳实践

---

## 知识管理模式

### KM-001: 会话结束蒸馏

**问题**: 每次会话产生大量上下文，下次会话重新加载成本高。

**方案**: 会话结束时，Agent 自动：
1. 总结关键发现 → `wiki/sessions/YYYY-MM-DD.md`
2. 检查是否有新知识需要追加到主页面
3. 更新 INDEX.md
4. 追加到 LOG.md

**验证**: 下次会话开始时，检查 session 摘要是否可用。

### KM-002: Index-First 查找

**问题**: wiki 页面增多后，不知道从哪里找起。

**方案**: 始终从 INDEX.md 开始 → 根据语义查找表找到相关页面 → 读页面 → 跟 [[wikilinks]]。

**例外**: 当搜索意图很明确时（如"查 DECISIONS.md"），直接读。

### KM-003: 阈值触发写入

**条件**: 当以下任一触发时写入 wiki：
- 同一主题出现 ≥ 2 次
- 用户说"记住"
- 做了架构决策
- 修复了反复出现的 bug
- 识别到可复用的模式

---

## 项目工作模式

### WP-001: 自动修复链 (Auto-Fix Chain)

**问题**: 队列任务卡住、导入失败等常见故障需要人工干预。

**方案**: 自动修复链：
1. 检测异常（探针/心跳）
2. 定位根因（日志分析）
3. 执行修复（桥接器脚本）
4. Smoke 验证（自动化测试）
5. 状态回写（更新队列状态）

**关键**: 修复必须是幂等的（同一故障不重复入队）。

**相关文件**: `scripts/fix_*.py`、`scripts/monitor*.py`

### WP-002: 路径漂移检测与纠正

**问题**: AI plan 文档中引用不存在的路径（常见的反模式）。

**方案**: 执行任何 AI plan 前：
1. 读取说明文档中的路径引用
2. 检查路径是否真实存在
3. 如果路径不存在，在工作区搜索最相近的替代路径
4. 在结果中诚实说明路径漂移

**陷阱**: 路径漂移经常发生在 `queue_item_id` 引用的说明文档路径。检查时优先搜索 `completed/` 目录。

### WP-003: Build Runner 脚本模式兼容

**问题**: `athena_ai_plan_runner.py` 在脚本模式（`python script.py`）下会因相对导入崩溃。

**方案**: 所有 Athena 脚本需要兼容两种启动模式：
1. **模块模式**：`python -m scripts.athena_ai_plan_runner`
2. **脚本模式**：`python scripts/athena_ai_plan_runner.py`

在脚本模式下：
- 向 `sys.path` 注入 `scripts_dir`
- 使用 `from openclaw_roots import ...` 兜底导入
- 使用 `dynamic_build_worker_budget()` 新参数签名

**测试**: 每次修改后同时测试两种启动模式。

### WP-004: 多 Agent 协作模式

**问题**: 单个 Agent 能力有限，复杂任务需要分工。

**方案**: 主 Agent → Subagent Registry → 子 Agent：
1. 主 Agent 分析任务，拆分子任务
2. 通过 Subagent Registry 注册子 Agent
3. 子 Agent 独立执行
4. 结果汇总回主 Agent

**适用场景**: 大型重构、并行代码审查、多维度调试。

### WP-005: 预算感知执行

**问题**: API token 有限，不加控制会耗尽预算。

**方案**: 四级生存模式：
- 每个操作前检查当前预算模式
- 低预算模式限制 token 消耗操作
- 关键模式仅允许只读操作
- 暂停模式停止所有操作

**集成**: 在 build runner 中集成 `dynamic_build_worker_budget()`。

---

## 常见陷阱

### TRAP-001: 临时修复变成永久状态

**现象**: 为快速恢复服务做了临时修复（如修改启动脚本、重定向路径），之后没有跟进根本解决方案。

**案例**: Athena Web Desktop 启动脚本被修改为指向临时路径，后续升级时被覆盖。

**预防**: 临时修复必须附带 TODO 注释和 Issue 跟踪。

### TRAP-002: 相对导入在脚本模式下失败

**现象**: `python -m` 可正常运行，`python script.py` 报 ImportError。

**根因**: Python 的 `-m` 模式与 `script` 模式的 `sys.path` 不同。

**修复**: 见 WP-003。

### TRAP-003: Service Worker 缓存旧版本

**现象**: TenacitOS 更新后页面显示旧内容。

**根因**: Service Worker 缓存了旧 HTML/JS。

**修复**: 清除 Service Worker 缓存或在构建时更新 Service Worker 版本号。

### TRAP-004: 任务文档路径与实际不符

**现象**: AI plan 的 `说明文档` 字段指向不存在路径。

**根因**: 路径在计划阶段确定，但在执行前文件可能被移动。

**预防**: 执行前验证路径 + 诚实报告路径漂移。
