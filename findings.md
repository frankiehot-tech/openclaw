# Findings & Decisions — Phase 2

## Requirements
- 建立 GitHub Actions CI 流水线（lint→typecheck→test→security）
- 配置日志轮转（164MB build_worker.log）
- 清理 74 个备份文件 + 60 个监控报告
- 集成安全扫描（bandit, pip-audit, truffleHog）
- 拆分 3 个核心大文件（4868+2062+2051 行）
- scripts/ 目录按职责拆分
- 清理 fix_*.py 脚本
- Plan B 可回滚方案

## Research Findings

### 代码库当前状态
- 74 个备份文件（`*.backup*` x64 + `backup*` x10）
- 60 个 `queue_progress_monitoring_*.md` 报告
- 39 个 `fix_*.py` 在根目录
- 164MB 日志文件: `logs/athena_ai_plan_build_worker.log`
- CI/CD: 仅有 1 个 workflow（文档质量检查）
- 无 pyproject.toml, 无 pre-commit hooks, 无项目级 pytest/mypy/flake8 配置
- GitHub 仓库: `frankiehot-tech/openclaw.git` (private)
- `execution/` 和 `ops/` 目录已存在但内容极少（Phase 1 骨架）

### 大文件依赖分析（待深入）

#### athena_ai_plan_runner.py (4868 行)
- 位于 `scripts/athena_ai_plan_runner.py`
- 审计建议拆分为: `runner/queue_manager.py`, `runner/build_worker.py`, `runner/budget_controller.py`, `runner/preflight_gate.py`, `runner/memory_writer.py`
- 已有备份副本: `.backup`, `.backup.original`, `.backup_p0_*`, `.backup_preflight_fix`

#### rebuild_aiplan_priority_queues.py (2062 行)
- 位于 `scripts/rebuild_aiplan_priority_queues.py`
- 队列优先级重建逻辑

#### athena_web_desktop_compat.py (2051 行)
- 位于 `scripts/athena_web_desktop_compat.py`
- Web/Desktop 兼容层，8080 端口服务

### macOS 日志轮转方案
- macOS 使用 `newsyslog` 替代 Linux 的 `logrotate`
- 配置文件: `/etc/newsyslog.d/openclaw.conf`
- 语法: `logfilename [owner:group] mode count size when flags`

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 使用 ruff 替代 flake8 | ruff 速度快 10-100x，兼容 flake8 规则，单个工具替代 flake8+isort+pyupgrade |
| 日志轮转用 macOS newsyslog | macOS native，无需额外依赖 |
| 所有变更在 feature branch | git 回滚保证 Plan B |
| pyproject.toml 统一工具配置 | Python 生态标准做法 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| smart_outline 无法解析 3 个大文件 | 改用 Read 分段读取分析 |

## Resources
- openclaw GitHub: https://github.com/frankiehot-tech/openclaw.git
- ruff docs: https://docs.astral.sh/ruff/
- newsyslog man: `man newsyslog`
- Audit report: `audit_results/comprehensive_audit_report_20260424.md`

---

*Update this file after every 2 view/browser/search operations*
