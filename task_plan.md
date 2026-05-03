# 四次深度审计修复 — 工程实施方案

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**目标**: 基于 103-四次深度审计代码级深层问题报告，按优先级修复全部 P0-P2 问题，将系统从 5.0/10 提升至 8.0/10。

**架构原则**:
1. 先修 CI（验证能力）→ 再修 P0 代码（阻塞项）→ 架构整合 → 工程优化
2. 每步必须有验证手段（CI 绿色 / pytest 通过 / lint 无警告）
3. 不引入新功能，只修复既有问题
4. 先原子修复，再大重构

**技术栈**: Python 3.11+ · pytest · ruff · mypy · bandit · GitHub Actions

---

## Phase 1: CI 修复（1-2 小时，P0 优先级）

### Task 1.1: CI 添加 `set -o pipefail`

**文件**: `.github/workflows/ci.yml:53-54`

**问题**: `2>&1 | head -200` 中 pytest 失败退出码被管道吞没。

**Step 1**: 在 test job 的 `run` 步骤添加 `set -o pipefail`

```yaml
- run: set -o pipefail && pytest --tb=short --timeout=60 -x 2>&1 | head -200
- run: set -o pipefail && coverage run -m pytest --tb=short --timeout=60 2>&1 | tail -20
- run: set -o pipefail && coverage report -m 2>&1 | head -50
```

**Step 2**: 验证 — 无语法变更，仅语义加固

**Step 3**: Commit

### Task 1.2: 修复 `pytest-timeout` 依赖

**文件**: `requirements.txt:15`，`.github/workflows/ci.yml:53`

**问题**: `--timeout=60` 需要 `pytest-timeout` 包但未声明。

**选项 A（推荐）**: 移除 `--timeout` 标志，依赖 `pyproject.toml` 中已有的 `timeout = 300`
**选项 B**: 向 `requirements.txt` 添加 `pytest-timeout>=2.1.0`

**Step 1**: 选择方案。`pyproject.toml:98` 已有 `timeout = 300` (pytest.ini_options)，但安装的 `pytest` 无 timeout 插件也会忽略该配置。

推荐采用 **选项 B**：向 `requirements.txt` 添加 `pytest-timeout>=2.1.0`。

**Step 2**: Commit

### Task 1.3: 将 `-x` 替换为 `--maxfail=5`

**文件**: `.github/workflows/ci.yml:53-54`

**Step 1**: 修改

```yaml
- run: set -o pipefail && pytest --tb=short --timeout=60 --maxfail=5 2>&1 | head -200
- run: set -o pipefail && coverage run -m pytest --tb=short --timeout=60 2>&1 | tail -20
```

**Step 2**: Commit

### Task 1.4: 修复 TruffleHog 安全扫描

**文件**: `.github/workflows/ci.yml:88-93`

**问题**:
1. `@main` 未固定版本
2. `extra_args` 包含 shell 管道语法，被当字符串传给二进制
3. 新分支时 `github.event.before` 为全零 SHA

**Step 1**: 修复版本固定和 extra_args

```yaml
- uses: trufflesecurity/trufflehog@v3.82.0
  with:
    path: ./
    base: ${{ github.event.before }}
    head: ${{ github.event.after }}
    extra_args: --only-verified=false --json
```

**Step 2**: 处理新分支场景 — 添加条件判断

```yaml
- name: Secret Scan (trufflehog)
  if: github.event.before != '0000000000000000000000000000000000000000'
  ...
```

或使用 `trufflehog filesystem` 命令模式替代 action：

```yaml
- name: Secret Scan (trufflehog)
  run: |
    pip install trufflehog==3.82.0
    trufflehog filesystem --directory=. --only-verified=false --json 2>&1 | head -100 || true
```

**Step 3**: Commit

### Task 1.5: 扩展 lint/typecheck/security 覆盖范围

**文件**: `.github/workflows/ci.yml:23,36,67`

**问题**: `ruff`, `mypy`, `bandit` 都跳过 `governance/`、`config/`、`src/`、`workflow/`、`monitoring/`。

**Step 1**: 修改 ruff 扫描范围

```yaml
- run: ruff check scripts/ athena/ execution/ ops/ governance/ config/ workflow/ monitoring/ agent_system/
- run: ruff format --check scripts/ athena/ execution/ ops/ governance/ config/ workflow/ monitoring/ agent_system/
```

**Step 2**: 修改 mypy 扫描范围

```yaml
- run: mypy scripts/ athena/ execution/ ops/ governance/ config/ workflow/ monitoring/ agent_system/ --ignore-missing-imports --show-error-codes
```

**Step 3**: 修改 bandit 扫描范围

```yaml
- run: bandit -r scripts/ athena/ execution/ ops/ governance/ config/ workflow/ monitoring/ agent_system/ -x .venv,.venv311,.venvs,venv,comfyui_workspace --skip B101,B404,B603,B607 -ll 2>&1 | head -100
```

**Step 4**: Commit

### Task 1.6: 升级 documentation-quality.yml Python 版本

**文件**: `.github/workflows/documentation-quality.yml:30`

**问题**: Python 3.9 已于 2025-10 EOL。

**Step 1**: 修改

```yaml
python-version: '3.11'
```

**Step 2**: Commit

### Task 1.7: CI 移除重复测试运行

**文件**: `.github/workflows/ci.yml:52-55`

**问题**: 测试在 line 53 和 line 54 运行两次。

**Step 1**: 合并为单次运行（保留 coverage 模式）

```yaml
- run: set -o pipefail && coverage run -m pytest --tb=short --timeout=60 --maxfail=5 2>&1 | tail -30
- run: set -o pipefail && coverage report -m 2>&1 | head -50
```

**Step 2**: Commit

---

## Phase 2: P0 代码修复（2-3 小时）

### Task 2.1: 为 `reset_gene_audit_to_pending.py` 添加 `if __name__` guard

**文件**: `reset_gene_audit_to_pending.py` (110 行)

**问题**: 脚本在 import 时即修改生产队列 JSON。

**Step 1**: 包裹所有执行代码：

```python
def main():
    # ... 全部原有代码缩进到 main() 中 ...
    pass

if __name__ == "__main__":
    main()
```

**Step 2**: 验证 — `python -c "import reset_gene_audit_to_pending"` 不应修改文件

**Step 3**: Commit

### Task 2.2: 为 `retry_gene_audit_task.py` 添加 `if __name__` guard

**文件**: `retry_gene_audit_task.py` (113 行)

**问题**: 脚本在 import 时即读取 auth token 并调用 HTTP API。

**Step 1**: 包裹所有执行代码：

```python
def main():
    # ... 全部原有代码缩进到 main() 中 ...
    pass

if __name__ == "__main__":
    main()
```

**Step 2**: 验证 — `python -c "import retry_gene_audit_task"` 不应代用 API

**Step 3**: Commit

### Task 2.3: 修复 `task_orchestrator.py:212` 死代码 Bug

**文件**: `governance/task_orchestrator.py:212`

**问题**: `now.replace(tzinfo=None) - __import__("datetime").timedelta(hours=threshold_hours)` 是孤立表达式，结果被丢弃。

**Step 1**: 将计算结果赋值回 `now`（或新的变量名）

```python
now = now.replace(tzinfo=None) - __import__("datetime").timedelta(hours=threshold_hours)
```

**Step 2**: 验证 — 运行相关测试：`pytest tests/ -k "zombie" -v`

**Step 3**: Commit

### Task 2.4: 修复 `state_machine.py:17` 字符串路径 Bug

**文件**: `agent_system/state/state_machine.py:17`

**问题**: `STATE_LOG` 是整个 `os.path.join(...)` 调用的字符串字面量。

**Step 1**: 移除引号

```python
STATE_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/state_machine.log')
```

**Step 2**: 验证 — `python -c "from agent_system.state.state_machine import STATE_LOG; print(STATE_LOG)"` 应输出有效路径

**Step 3**: Commit

---

## Phase 3: 架构整合（4-6 小时）

### Task 3.1: 统一治理模块

**文件**: `agent_system/governance/` → 改为从 `governance/` 导入

**问题**: `agent_system/governance/` 是 120 行 stub，`governance/` 是 275+ 行完整实现。语义层通过 `agent_system.governance.*` 引用 stub。

**Step 1**: 检查哪些文件导入 `agent_system.governance`

```bash
rg "from agent_system\.governance import|from agent_system import governance|import agent_system\.governance"
```

**Step 2**: 修改 `agent_system/semantic/command_map.py` 中的导入路径

```python
# 修改前
from agent_system.governance.queue_manager import QueueManager
from agent_system.governance.system_health import SelfHealing

# 修改后
from governance.queue_manager import QueueManager
from governance.system_health import SelfHealing
```

**Step 3**: 删除 `agent_system/governance/` 目录（或保留 `__init__.py` 作为 re-export 桥接）

**Step 4**: 运行 CI lint/typecheck 验证：`ruff check agent_system/semantic/ governance/`

**Step 5**: Commit

### Task 3.2: 为共享队列写入添加原子写入

**文件**:
- `governance/task_orchestrator.py:49-53` → `_save()`
- `governance/system_health.py:265` → `_protect_one()`
- `governance/repair_tools.py:47-51` → `_save_json()`
- `agent_system/governance/queue_manager.py` (stub)

**参考**: `governance/queue_manager.py` 中正确的 `save_queue()` 实现（`tmp.with_suffix(".tmp")` + `os.replace()`）

**Step 1**: 创建共享工具函数

新建 `governance/_utils.py` 或添加到 `governance/queue_manager.py`：

```python
def atomic_write_json(path: Path, data: Any) -> None:
    """原子写入 JSON 文件：先写临时文件，再原子替换。"""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    tmp.replace(path)
```

**Step 2**: 替换所有 3 个位置的直接写入

**Step 3**: 验证 — `pytest tests/ -v`

**Step 4**: Commit

### Task 3.3: 为队列读写添加文件锁

**文件**: `governance/queue_manager.py`, `governance/task_orchestrator.py`, `governance/system_health.py`, `governance/repair_tools.py`

**Step 1**: 在 `_utils.py` 中添加锁上下文管理器

```python
import fcntl

class FileLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.fd = None

    def __enter__(self):
        self.fd = self.lock_path.open("w")
        fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *args):
        fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
        self.fd.close()
```

**Step 2**: 在队列读取前获取锁，写入后释放

**Step 3**: 验证 — 并发读写测试

**Step 4**: Commit

### Task 3.4: 解决 LICENSE 冲突

**文件**: `pyproject.toml:7`, `LICENSE`, `README.md`

**问题**: `pyproject.toml` 声明 MIT，但 `LICENSE` 文件是 AGPL-3.0。

**决策**: 需要与项目拥有者确认。**暂时统一为 `AGPL-3.0`**（LICENSE 文件的实体法版本）。

**Step 1**: 修改 `pyproject.toml`

```toml
license = { text = "AGPL-3.0" }
```

**Step 2**: Commit

### Task 3.5: 将 contracts 集成到执行流程（数据质量门禁）

**文件**: `contracts/data_quality.py` + 执行入口

**问题**: DataQualityContract (1,206 行) 从未被自动调用。

**Step 1**: 在 `governance/task_orchestrator.py` 的任务完成回调中添加数据质量检查

```python
from contracts.data_quality import DataQualityContract

def _check_data_quality(self, queue_path: Path) -> bool:
    contract = DataQualityContract()
    result = contract.validate(str(queue_path))
    if not result["passed"]:
        logger.warning(f"Data quality check failed for {queue_path}: {result['errors']}")
        return False
    return True
```

**Step 2**: 在 `task_orchestrator.py` 的 `process_task()` 或类似方法中调用

**Step 3**: 验证 — 运行现有测试不受影响

**Step 4**: Commit

---

## Phase 4: 工程优化（本月，按优先级）

### Task 4.1: 根级脚本迁移（40 个脚本）

**文件**: `*.py`（根目录 40 个）

**Step 1**: 分类脚本

```bash
# 查看所有根级 Python 脚本
ls -1 *.py | grep -vE '^(setup|conf|__init__)' | sort
```

**Step 2**: 将确定不再需要的 DEPRECATED 脚本移至 `archive/` 目录

**Step 3**: 将仍可能使用的脚本移入 `scripts/hotfix/` 并添加 `if __name__` guard

**Step 4**: 更新根 `.gitignore` 排除不追踪的临时脚本

### Task 4.2: 拆分 DataQualityContract God Object

**文件**: `contracts/data_quality.py` (1,206 行，25 个方法)

**Step 1**: 按职责拆分
- `DuplicateAnalyzer` — 去重相关方法
- `SchemaValidator` — 模式验证
- `QualityReporter` — 报告生成
- `DataQualityContract` 保留为门面（facade）或删除

**Step 2**: 确保旧导入路径仍可工作（re-export）

### Task 4.3: 统一 JSON 加载工具函数

**文件**: `repair_tools._load_json()`, `task_orchestrator._load()`, `system_health._load_json()`

**Step 1**: 在 `_utils.py` 中创建统一函数

```python
def load_json_safe(path: Path) -> dict[str, Any] | None:
    """Safe JSON loading, returns None on missing/corrupt."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
```

**Step 2**: 替换 4 处重复实现

### Task 4.4: 统一日志系统 + 替换 print()

**Step 1**: 创建结构化日志配置 `config/logging_setup.py`

```python
import logging
import json
from datetime import UTC, datetime

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })
```

**Step 2**: 标记需要替换 `print()` 的关键路径（治理模块优先）

### Task 4.5: 清理虚拟环境

```bash
# 保留 .venv (最完整)，删除其他
trash .venv311
trash venv/
trash agent_system/venv/
trash .venvs/
```

### Task 4.6: 添加依赖 lock 文件

```bash
pip freeze > requirements-lock.txt
```

### Task 4.7: 日志轮转清理

```bash
# 手动清理超大的日志
: > logs/athena_ai_plan_build_worker.log
: > scripts/runner.log

# 检查 logrotate 状态
logrotate -f /etc/logrotate.d/openclaw
```

### Task 4.8: 清理 `.DS_Store` 和 `__pycache__`

```bash
find . -name '.DS_Store' -delete 2>/dev/null
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null
```

### Task 4.9: 为 contracts 和 semantic 层编写基础测试

**文件**: `tests/test_contracts.py`, `tests/test_semantic.py`

**目标**: 从 0.33% 测试代码比提升至 >1%

---

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| CI 修复后首次运行大量失败 | 高 | 中 | 先本地运行 `pytest` 验证，分步提交 |
| governance 模块统一导致语义层断裂 | 中 | 高 | 先 grep 全库导入路径，改一步测一步 |
| 文件锁跨平台问题 (macOS vs Linux) | 中 | 低 | `fcntl.flock` 在 macOS/Linux 均支持 |
| LICENSE 统一选择错误 | 低 | 中 | 需要与项目 owner 确认后再提交 |

## 验证清单

- [ ] Phase 1: `set -o pipefail` 添加后，CI 测试失败能正确报告非零退出码
- [ ] Phase 1: TruffleHog 能在 CI 中正常执行（非语法错误）
- [ ] Phase 2: `python -c "import reset_gene_audit_to_pending"` 不产生副作用
- [ ] Phase 2: `python -c "from agent_system.state.state_machine import STATE_LOG; print(STATE_LOG)"` 输出有效路径
- [ ] Phase 3: `ruff check governance/` 通过
- [ ] Phase 3: 所有现有测试通过: `pytest tests/ -v`
