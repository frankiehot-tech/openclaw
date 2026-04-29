# 代码库修复实施计划

**基于**: audit_results/codebase_audit_report_20260427.md
**开始日期**: 2026-04-27

## 执行路线

### Phase 1（P0：立即修复）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 1 | 轮换 API 密钥 + Git 历史清除 .env | pending | **需用户操作** |
| 2 | 修复 broken pyproject.toml（排除非法文件） | pending | 可自动化 |
| 3 | 修复 TruffleHog 配置 | pending | 可自动化 |
| 4 | 修复 136 处无效语法（Python 3.12 → 3.11 兼容） | pending | 可自动化 |
| 5 | 替换 26 处硬编码绝对路径 | pending | 可自动化 |
| 6 | 修复 169 处 `raise ... from` 缺失 (B904) | pending | 可自动化 |
| 7 | 修复 126 处未定义名称 (F821) | pending | 需逐文件分析 |
| 8 | ruff exclude 配置更新 | pending | 可自动化 |

### Phase 2（P1：重要修复）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 1 | 批量修复 2204 未使用导入 (F401) | pending | `ruff --fix` |
| 2 | 清理 2180 处 f-string 问题 (F541) | pending | `ruff --fix` |
| 3 | 清理 469 处未使用变量 (F841) | pending | `ruff --fix` |
| 4 | 123 处裸 except: → except Exception: | pending | 手动审核 |
| 5 | ruff format 全量格式化 | pending | `ruff format` |
| 6 | 更新 ruff exclude 包含 mini-agent 等 | pending | 可自动化 |
| 7 | 升级 GitHub Actions 版本 | pending | 可自动化 |
| 8 | pre-commit mypy 路径修复 | pending | 可自动化 |
| 9 | PEP 585/604 注解迁移 | pending | ruff --fix |
| 10 | 核心模块测试编写 | pending | 手动 |

### Phase 3（P2：持续改进）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 1 | 归档 queue_progress_monitoring_*.md | pending | 可自动化 |
| 2 | 补充 PR 模板 | pending | 可自动化 |
| 3 | 更新 CONTRIBUTING.md | pending | 手动 |
| 4 | mypy 配置收紧 | pending | 手动 |

## 执行顺序说明
- Phase 1 必须按顺序执行，因为后面的修复依赖前面的基础设施（broken pyproject.toml 阻塞 ruff 运行）
- Phase 2 在 Phase 1 完成后开始
- Phase 3 可在任何阶段并行
