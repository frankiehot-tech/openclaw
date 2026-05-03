# 103-四次深度审计 — 探索发现

**探索日期**: 2026-04-29
**探索范围**: 审计报告涉及的 15+ 核心文件 + CI/CD 配置 + 根级脚本

---

## P0 问题确认（全部验证）

### P0-1: CI pipefail 缺失 ✅ 确认
- `.github/workflows/ci.yml:53-54`: `2>&1 | head -200` 无 `set -o pipefail`
- `requirements.txt`: 无 `pytest-timeout` 依赖
- CI test job 始终返回绿色退出码

### P0-2: TruffleHog 语法错误 ✅ 确认
- `.github/workflows/ci.yml:88-93`: `extra_args` 包含 `2>&1 | head -50` 字面字符串
- 使用 `@main` (未固定版本)
- 无新分支保护

### P0-3: 无 `if __name__` 保护 ✅ 确认
- `reset_gene_audit_to_pending.py`: line 9-19 立即执行 shutil.copy2
- `retry_gene_audit_task.py`: line 12-13 立即读取 token 文件

### P0-4: task_orchestrator.py 死代码 ✅ 确认
- `governance/task_orchestrator.py:212`: `now.replace(tzinfo=None) - __import__("datetime").timedelta(hours=threshold_hours)` 孤立表达式
- `now` 变量在 line 211 赋值后从未被重新赋值，line 226 的 `now` 仍带 tzinfo

### P0-5: state_machine.py 字符串路径 ✅ 确认
- `agent_system/state/state_machine.py:17`: 整个 `os.path.join(...)` 被引号包裹为字面量
- line 20: `os.path.exists(os.path.dirname(STATE_LOG))` 操作在字面量 `"os.path.join..."` 上

---

## 架构分裂验证

### 双治理模块
| 指标 | agent_system/governance/ | governance/ |
|------|------------------------|------------|
| queue_manager.py | 119 行，只读查询 | 275 行，完整 CRUD + save/backup/fix |
| system_health.py | SelfHealing 类 (349 行) | QueueHealthMonitor + QueueProtector + SystemHealth (347 行) |
| 导入来源 | `agent_system/semantic/command_map.py` | CLI 和 scripts |

### command_map.py 不存在于预期路径
- 审计报告说 `command_map.py` 从 `agent_system.governance.*` 导入
- 实际文件在 `agent_system/semantic/command_map.py` — 语义层

---

## LICENSE 冲突确认

- `pyproject.toml:7`: `license = { text = "MIT" }`
- `LICENSE` 文件头: "GNU AFFERO GENERAL PUBLIC LICENSE Version 3"

---

## 环境与基础设施

| 发现 | 数据 |
|------|------|
| 根级 Python 脚本 | **40 个** `.py` 文件 |
| requirements.txt | 无 lock 文件，全部 `>=` |
| pyproject.toml | ruff/mypy/bandit scope 不全（跳过 governance/config/workflow/monitoring/agent_system） |
| documentation-quality.yml | 使用 Python 3.9 (EOL) |
| execution/ 目录 | 5 个 `__init__.py` + 空包，runner 实现在 `scripts/runner/` |
